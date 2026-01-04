import os
import json
import yaml
import threading
import concurrent.futures
import google.generativeai as genai
from pathlib import Path
from planning_layer.planner_prompt import PLANNER_SYSTEM_PROMPT
from dotenv import load_dotenv
from utils.permanent_memory import format_memory_for_prompt

# Load environment variables from .env file
load_dotenv()

# ============================================
# SINGLETON PATTERN FOR LLM CLIENT
# Saves 4-9 seconds per query by reusing model
# ============================================
_planner_model = None
_planner_model_lock = threading.Lock()
_config_cache = None


def load_config():
    """Load LLM configuration from settings.yaml with caching"""
    global _config_cache
    if _config_cache is not None:
        return _config_cache

    config_path = Path("config/settings.yaml")
    with open(config_path) as f:
        config = yaml.safe_load(f)
    _config_cache = config.get("llm", {})
    return _config_cache


def get_planner_model():
    """
    Get or create singleton Gemini model instance.
    Thread-safe with double-checked locking pattern.

    Returns:
        GenerativeModel: Reusable Gemini model instance
    """
    global _planner_model

    # Fast path - model already exists
    if _planner_model is not None:
        return _planner_model

    # Slow path - need to create model (thread-safe)
    with _planner_model_lock:
        # Double-check after acquiring lock
        if _planner_model is not None:
            return _planner_model

        config = load_config()
        _planner_model = initialize_gemini_client(config)
        return _planner_model


def invalidate_planner_model():
    """
    Invalidate the cached model (e.g., when memory/config changes).
    Call this when permanent memory is updated.
    """
    global _planner_model, _config_cache
    with _planner_model_lock:
        _planner_model = None
        _config_cache = None


def initialize_gemini_client(config):
    """Initialize Gemini API client with configuration and memory injection"""
    api_key_env = config.get("api_key_env", "GEMINI_API_KEY")
    api_key = os.getenv(api_key_env)
    
    if not api_key:
        raise ValueError(
            f"Gemini API key not found. Please set the {api_key_env} environment variable."
        )
    
    genai.configure(api_key=api_key)
    
    model_name = config.get("model", "gemini-2.5-pro")
    temperature = config.get("temperature", 0.0)
    
    generation_config = {
        "temperature": temperature,
        "response_mime_type": "application/json",
    }
    
    # Load and inject permanent memory into system prompt
    memory_constraints = format_memory_for_prompt()
    system_prompt = PLANNER_SYSTEM_PROMPT + memory_constraints
    
    model = genai.GenerativeModel(
        model_name=model_name,
        generation_config=generation_config,
        system_instruction=system_prompt
    )
    
    return model


def format_schema_context(schema_context) -> str:
    """
    Format schema context for LLM prompt.

    Args:
        schema_context: Can be:
            - str: Already formatted schema text (from table router)
            - list: List of dicts with 'text' key (legacy format from vector store)
    """
    if not schema_context:
        return "No schema context available."

    # If already a string, return as-is (from table router)
    if isinstance(schema_context, str):
        return f"Available Schema:\n\n{schema_context}"

    # Legacy format: list of dicts with 'text' key
    formatted = "Available Schema:\n\n"

    for item in schema_context:
        if isinstance(item, dict):
            formatted += f"- {item.get('text', '')}\n"
        else:
            formatted += f"- {item}\n"

    return formatted


def parse_json_response(response_text: str) -> dict:
    """Parse JSON from LLM response, handling potential formatting issues"""
    # Remove markdown code blocks if present
    text = response_text.strip()
    if text.startswith("```"):
        # Extract content between code blocks
        lines = text.split("\n")
        text = "\n".join(lines[1:-1]) if len(lines) > 2 else text
        if text.startswith("json"):
            text = text[4:].strip()

    # Parse JSON
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse JSON from LLM response: {e}\nResponse: {text}")


def call_llm_with_timeout(model, prompt: str, timeout_seconds: int = 60):
    """
    Call LLM with a timeout to prevent hanging.

    Args:
        model: The Gemini model instance
        prompt: The prompt to send
        timeout_seconds: Maximum time to wait (default 60s from config)

    Returns:
        The model response

    Raises:
        TimeoutError: If the call takes longer than timeout_seconds
        Exception: Any error from the model
    """
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(model.generate_content, prompt)
        try:
            return future.result(timeout=timeout_seconds)
        except concurrent.futures.TimeoutError:
            raise TimeoutError(f"LLM request timed out after {timeout_seconds} seconds")


def generate_plan(question: str, schema_context: list, max_retries: int = None) -> dict:
    """
    Generate query plan using Gemini LLM.
    
    Args:
        question: User's natural language question
        schema_context: List of schema documents from ChromaDB retrieval
        max_retries: Maximum number of retry attempts (defaults to config value)
    
    Returns:
        dict: Query plan matching plan_schema.json
    
    Raises:
        ValueError: If API key is missing, JSON parsing fails, or max retries exceeded
    
    CRITICAL: This function ONLY proposes intent. It does NOT:
    - Execute queries
    - Validate plans (done by plan_validator.py)
    - Generate SQL (done by sql_compiler.py)
    - Access data (done by executor.py)
    """
    
    # Load configuration
    config = load_config()
    if max_retries is None:
        max_retries = config.get("max_retries", 3)

    # Get singleton Gemini client (saves 4-9s per query)
    model = get_planner_model()
    
    # Format schema context
    schema_text = format_schema_context(schema_context)
    
    # Build user prompt
    user_prompt = f"""{schema_text}

User Question: {question}

Output the query plan as JSON:"""
    
    # Get timeout from config
    timeout_seconds = config.get("request_timeout_seconds", 60)

    # Retry logic for API failures
    last_error = None
    for attempt in range(max_retries):
        try:
            # Call Gemini API with timeout protection
            response = call_llm_with_timeout(model, user_prompt, timeout_seconds)

            # Extract text from response
            response_text = response.text

            # Parse JSON
            plan = parse_json_response(response_text)

            # Basic structure check (detailed validation happens in validator)
            if not isinstance(plan, dict):
                raise ValueError(f"LLM response is not a JSON object: {type(plan)}")

            if "query_type" not in plan:
                raise ValueError("LLM response missing required field: query_type")

            if "table" not in plan:
                raise ValueError("LLM response missing required field: table")

            # === TYPE VALIDATION ===
            # Ensure critical fields have correct types to prevent downstream errors
            if not isinstance(plan.get("query_type"), str):
                raise ValueError(f"query_type must be a string, got: {type(plan.get('query_type'))}")

            if not isinstance(plan.get("table"), str):
                raise ValueError(f"table must be a string, got: {type(plan.get('table'))}")

            # Optional field type validation
            if "metrics" in plan and not isinstance(plan.get("metrics"), list):
                raise ValueError(f"metrics must be a list, got: {type(plan.get('metrics'))}")

            if "group_by" in plan and not isinstance(plan.get("group_by"), list):
                raise ValueError(f"group_by must be a list, got: {type(plan.get('group_by'))}")

            if "filters" in plan and not isinstance(plan.get("filters"), list):
                raise ValueError(f"filters must be a list, got: {type(plan.get('filters'))}")

            if "order_by" in plan and plan.get("order_by") is not None:
                if not isinstance(plan.get("order_by"), list):
                    raise ValueError(f"order_by must be a list, got: {type(plan.get('order_by'))}")

            return plan

        except TimeoutError as e:
            last_error = e
            print(f"[Planner] Attempt {attempt + 1}/{max_retries} timed out")
            if attempt < max_retries - 1:
                continue  # Retry
            else:
                raise TimeoutError(f"LLM request timed out after {max_retries} attempts")

        except json.JSONDecodeError as e:
            last_error = e
            if attempt < max_retries - 1:
                continue  # Retry
            else:
                raise ValueError(f"Failed to parse valid JSON after {max_retries} attempts: {e}")

        except Exception as e:
            last_error = e
            if attempt < max_retries - 1:
                continue  # Retry
            else:
                raise ValueError(f"Failed to generate plan after {max_retries} attempts: {e}")
    
    # Should never reach here, but just in case
    raise ValueError(f"Failed to generate plan: {last_error}")
