import os
import json
import yaml
import threading
import concurrent.futures
import google.generativeai as genai
from pathlib import Path
from planning_layer.planner_prompt import PLANNER_SYSTEM_PROMPT
from dotenv import load_dotenv

# Backend directory for relative paths
_BACKEND_DIR = Path(__file__).parent.parent
from utils.permanent_memory import format_memory_for_prompt

# Load environment variables from .env file
load_dotenv()


# ============================================
# BACKWARD-COMPATIBLE MODEL WRAPPER
# Works with google-generativeai 0.3.x (no system_instruction)
# ============================================
class CompatibleGenerativeModel:
    """
    Wrapper for GenerativeModel that supports system prompts
    on older versions of google-generativeai (< 0.4.0).
    """
    def __init__(self, model, system_prompt: str):
        self._model = model
        self._system_prompt = system_prompt

    def generate_content(self, prompt, **kwargs):
        """Prepend system prompt to user message."""
        full_prompt = f"{self._system_prompt}\n\n---\n\nUser Query:\n{prompt}"
        return self._model.generate_content(full_prompt, **kwargs)

    def __getattr__(self, name):
        """Forward other attributes to underlying model."""
        return getattr(self._model, name)


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

    config_path = _BACKEND_DIR / "config" / "settings.yaml"
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
    
    # Output tokens for query plans - comparison queries need more tokens
    # due to complex JSON with multiple period definitions and filters
    max_tokens = config.get("planner_max_tokens", 1500)

    generation_config = {
        "temperature": temperature,
        "response_mime_type": "application/json",
        "max_output_tokens": max_tokens,
    }

    # Load and inject permanent memory into system prompt
    memory_constraints = format_memory_for_prompt()
    system_prompt = PLANNER_SYSTEM_PROMPT + memory_constraints

    # Create base model without system_instruction (for compatibility with 0.3.x)
    base_model = genai.GenerativeModel(
        model_name=model_name,
        generation_config=generation_config,
    )

    # Wrap with our compatible model that handles system prompts
    return CompatibleGenerativeModel(base_model, system_prompt)


# ============================================
# ADAPTIVE MODEL SELECTION FOR LATENCY
# Simple queries: gemini-2.0-flash (2-3x faster)
# Complex queries: gemini-2.5-pro (more accurate)
# ============================================

def estimate_query_complexity(question: str, entities: dict = None) -> str:
    """
    Estimate query complexity to select appropriate model.

    Returns:
        'simple': Basic aggregation, lookup, count queries (~70% of queries)
        'complex': Multi-table, trend analysis, complex comparisons
    """
    q_lower = question.lower()

    # Complex query patterns (need powerful model)
    complex_patterns = [
        'compare', 'versus', 'vs', 'trend', 'over time',
        'correlation', 'impact', 'why', 'how does',
        'month over month', 'year over year', 'yoy', 'mom',
        'projection', 'forecast', 'predict',
        'between', 'from', 'and', 'across all',
        'breakdown by', 'grouped by multiple'
    ]

    # Check for complex patterns
    for pattern in complex_patterns:
        if pattern in q_lower:
            return 'complex'

    # Check entities for complexity signals
    if entities:
        if entities.get('cross_table_intent'):
            return 'complex'
        if entities.get('comparison') and entities.get('multi_period'):
            return 'complex'
        if entities.get('trend_intent'):
            return 'complex'
    
    # Simple queries (use fast model)
    return 'simple'


def get_model_for_complexity(complexity: str, config: dict):
    """
    Get appropriate model based on query complexity.
    Creates a new model instance (not singleton) for adaptive selection.

    Args:
        complexity: 'simple' or 'complex'
        config: LLM configuration

    Returns:
        tuple: (model, model_name)
    """
    api_key = os.getenv(config.get("api_key_env", "GEMINI_API_KEY"))
    genai.configure(api_key=api_key)
    temperature = config.get("temperature", 0.0)

    if complexity == 'simple':
        # Fast model for simple queries (2-3x faster)
        model_name = "gemini-2.0-flash"
        max_tokens = 1000
    else:
        # Powerful model for complex queries
        model_name = config.get("model", "gemini-2.5-pro")
        max_tokens = config.get("planner_max_tokens", 1500)

    generation_config = {
        "temperature": temperature,
        "response_mime_type": "application/json",
        "max_output_tokens": max_tokens,
    }

    # Load memory constraints
    memory_constraints = format_memory_for_prompt()
    system_prompt = PLANNER_SYSTEM_PROMPT + memory_constraints

    # Create base model without system_instruction (for compatibility with 0.3.x)
    base_model = genai.GenerativeModel(
        model_name=model_name,
        generation_config=generation_config,
    )

    # Wrap with our compatible model that handles system prompts
    model = CompatibleGenerativeModel(base_model, system_prompt)

    return model, model_name


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


def _repair_truncated_json(text: str) -> str:
    """
    Attempt to repair truncated JSON from LLM responses.
    Common issues: unterminated strings, missing closing brackets.
    """
    # Count brackets to determine what's missing
    open_braces = text.count('{')
    close_braces = text.count('}')
    open_brackets = text.count('[')
    close_brackets = text.count(']')

    # Check for unterminated string (odd number of unescaped quotes)
    # Simple heuristic: if JSON ends mid-string, close it
    if text.rstrip().endswith('"'):
        pass  # String is closed
    else:
        # Check if we're in the middle of a string value
        last_quote = text.rfind('"')
        if last_quote > 0:
            # Check what comes before the last quote
            before_quote = text[:last_quote].rstrip()
            if before_quote.endswith(':') or before_quote.endswith(','):
                # We're likely in an unterminated string value
                text = text + '"'

    # Add missing closing brackets
    text = text + ']' * (open_brackets - close_brackets)
    text = text + '}' * (open_braces - close_braces)

    return text


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
        parsed = json.loads(text)

        # Handle compound questions - LLM may return a list of plans
        # e.g., "Which category sold the most AND which has highest profit"
        # Take the first plan to answer the primary question
        if isinstance(parsed, list) and len(parsed) > 0:
            print(f"  [Planner] Compound question detected - LLM returned {len(parsed)} plans, using first")
            return parsed[0]

        return parsed
    except json.JSONDecodeError as e:
        # Try to repair truncated JSON (common with token limits)
        print(f"  [Planner] JSON parse failed, attempting repair...")
        try:
            repaired = _repair_truncated_json(text)
            parsed = json.loads(repaired)
            print(f"  [Planner] JSON repair successful!")

            if isinstance(parsed, list) and len(parsed) > 0:
                return parsed[0]
            return parsed
        except json.JSONDecodeError:
            # Repair failed, raise original error
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


def generate_plan(question: str, schema_context: list, max_retries: int = None, entities: dict = None) -> dict:
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
    import time
    _start = time.time()

    # Load configuration
    config = load_config()
    if max_retries is None:
        max_retries = config.get("max_retries", 3)

    # ADAPTIVE MODEL SELECTION: Use faster model for simple queries
    complexity = estimate_query_complexity(question, entities)
    model, model_name = get_model_for_complexity(complexity, config)
    print(f"  [Planner] Query complexity: {complexity} → using {model_name}")

    # Format schema context
    schema_text = format_schema_context(schema_context)
    
    # Build entity hints if available
    entity_hints = ""
    if entities:
        hint_parts = []
        if entities.get('location'):
            location = entities['location']
            # Determine if it's a city or state to help LLM choose correct column
            known_cities = {
                'chennai', 'bangalore', 'mumbai', 'delhi', 'hyderabad', 'kolkata',
                'pune', 'ahmedabad', 'jaipur', 'lucknow', 'kanpur', 'nagpur',
                'indore', 'thane', 'bhopal', 'visakhapatnam', 'coimbatore', 'madurai',
                'kochi', 'patna', 'jodhpur', 'surat', 'vadodara', 'rajkot',
                'velachery', 'adyar', 'anna nagar', 't nagar', 'tambaram', 'koyambedu',
                'nungambakkam', 'mylapore', 'triplicane', 'egmore', 'kodambakkam'
            }
            known_states = {
                'tamil nadu', 'karnataka', 'maharashtra', 'kerala', 'andhra pradesh',
                'telangana', 'west bengal', 'gujarat', 'rajasthan', 'uttar pradesh',
                'madhya pradesh', 'bihar', 'odisha', 'punjab', 'haryana', 'jharkhand',
                'chhattisgarh', 'assam', 'goa', 'uttarakhand', 'himachal pradesh'
            }

            location_lower = location.lower()
            if location_lower in known_cities:
                hint_parts.append(f"- Filter by CITY/BRANCH (NOT State column!): {location} - Use columns like 'Branch', 'Branch_Name', 'City', 'Area Name', 'Area', 'Location' for this filter")
            elif location_lower in known_states:
                hint_parts.append(f"- Filter by STATE: {location} - Use the 'State' column for this filter")
            else:
                # Check if it looks like a state (contains 'pradesh', 'nadu', etc.)
                if any(kw in location_lower for kw in ['pradesh', 'nadu', 'bengal', 'kashmir']):
                    hint_parts.append(f"- Filter by STATE: {location} - Use the 'State' column")
                else:
                    hint_parts.append(f"- Filter by location/area: {location} - Try 'Branch', 'City', 'Area Name', or 'State' column based on what exists")
        if entities.get('category'):
            hint_parts.append(f"- Filter by category: {entities['category']}")
        if entities.get('month'):
            hint_parts.append(f"- Time context: {entities['month']}")
        if entities.get('metric'):
            hint_parts.append(f"- Metric focus: {entities['metric']}")
        if entities.get('cross_table_intent'):
            hint_parts.append("- User wants data ACROSS multiple time periods (trend analysis)")
        # CRITICAL: Pass specific date for date filtering (Tamil dates like "இருபத்தி நான்காம் தேதி")
        if entities.get('date_specific'):
            from datetime import datetime, timedelta
            date_info = entities['date_specific']
            day = date_info.get('day')
            month = date_info.get('month')
            if day and month:
                # Convert to ISO format for filtering
                year = date_info.get('year', 2025)  # Default to 2025
                try:
                    # Use datetime for proper date arithmetic (handles month boundaries)
                    date_obj = datetime(year, month, day)
                    next_date_obj = date_obj + timedelta(days=1)
                    date_str = date_obj.strftime('%Y-%m-%d')
                    next_date_str = next_date_obj.strftime('%Y-%m-%d')
                    month_name = date_obj.strftime('%B')  # Full month name
                    hint_parts.append(f"- **SPECIFIC DATE**: {month_name} {day} → MUST filter: Date >= '{date_str}' AND Date < '{next_date_str}'")
                except ValueError:
                    # Invalid date (e.g., Feb 30), skip date hint
                    pass
            elif day:
                # Only day specified, use with month context
                hint_parts.append(f"- **SPECIFIC DAY**: Day {day} of the month → Apply date filter for day {day}")
        if hint_parts:
            entity_hints = "\n**Extracted Entities (use these for filters):**\n" + "\n".join(hint_parts) + "\n"

    # Build user prompt
    user_prompt = f"""{schema_text}
{entity_hints}
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

            elapsed = (time.time() - _start) * 1000
            print(f"✅ LLM Planning generated [{elapsed:.0f}ms]")
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
