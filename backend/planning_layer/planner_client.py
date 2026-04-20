import os
import json
import yaml
import time
import threading
import concurrent.futures
from pathlib import Path
from planning_layer.planner_prompt import PLANNER_SYSTEM_PROMPT
from dotenv import load_dotenv
from utils.logger import get_logger
from utils import gemini_client

logger = get_logger("planner")

# Backend directory for relative paths
_BACKEND_DIR = Path(__file__).parent.parent
from utils.permanent_memory import format_memory_for_prompt

# Load environment variables from .env file
load_dotenv()


# ============================================
# CACHED SYSTEM PROMPT (includes permanent memory)
# ============================================
_system_prompt_cache = None
_system_prompt_lock = threading.Lock()
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


def _get_system_prompt():
    """
    Get cached system prompt with permanent memory injection.
    Thread-safe with double-checked locking pattern.
    """
    global _system_prompt_cache

    if _system_prompt_cache is not None:
        return _system_prompt_cache

    with _system_prompt_lock:
        if _system_prompt_cache is not None:
            return _system_prompt_cache

        memory_constraints = format_memory_for_prompt()
        _system_prompt_cache = PLANNER_SYSTEM_PROMPT + memory_constraints
        return _system_prompt_cache


def invalidate_planner_model():
    """
    Invalidate the cached system prompt (e.g., when memory/config changes).
    Call this when permanent memory is updated.
    """
    global _system_prompt_cache, _config_cache
    with _system_prompt_lock:
        _system_prompt_cache = None
        _config_cache = None


# ============================================
# ADAPTIVE MODEL SELECTION FOR LATENCY
# Simple queries: gemini-2.5-flash (2-3x faster)
# Complex queries: gemini-2.5-flash (more accurate)
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
    Get appropriate model name and token limit based on query complexity.

    Args:
        complexity: 'simple' or 'complex'
        config: LLM configuration

    Returns:
        tuple: (model_name, max_tokens)
    """
    if complexity == 'simple':
        return "gemini-2.5-flash", 1000
    else:
        return config.get("model", "gemini-2.5-flash"), config.get("planner_max_tokens", 1500)


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
            logger.debug("Compound question detected - LLM returned %s plans, using first", len(parsed))
            return parsed[0]

        return parsed
    except json.JSONDecodeError as e:
        # Try to repair truncated JSON (common with token limits)
        logger.warning("JSON parse failed, attempting repair...")
        try:
            repaired = _repair_truncated_json(text)
            parsed = json.loads(repaired)
            logger.info("JSON repair successful")

            if isinstance(parsed, list) and len(parsed) > 0:
                return parsed[0]
            return parsed
        except json.JSONDecodeError:
            # Repair failed, raise original error
            raise ValueError(f"Failed to parse JSON from LLM response: {e}\nResponse: {text}")


def call_llm_with_timeout(
    prompt: str,
    model_name: str,
    gen_config: dict,
    timeout_seconds: int = 60,
) -> str:
    """Call Gemini via HTTP with a timeout. Returns response text."""
    def _call():
        return gemini_client.generate_content(
            model=model_name,
            contents=prompt,
            system_instruction=gen_config.get("system_instruction"),
            temperature=gen_config.get("temperature", 0.7),
            max_output_tokens=gen_config.get("max_output_tokens", 1500),
            response_mime_type=gen_config.get("response_mime_type"),
            timeout=timeout_seconds,
        )

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(_call)
        try:
            return future.result(timeout=timeout_seconds + 5)
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
    model_name, max_tokens = get_model_for_complexity(complexity, config)
    logger.debug("Query complexity: %s -> using %s", complexity, model_name)

    # Build generation config with system prompt
    system_prompt = _get_system_prompt()
    gen_config = {
        "system_instruction": system_prompt,
        "temperature": config.get("temperature", 0.0),
        "response_mime_type": "application/json",
        "max_output_tokens": max_tokens,
    }

    # Format schema context
    schema_text = format_schema_context(schema_context)
    
    # Build entity hints if available
    entity_hints = ""
    if entities:
        hint_parts = []
        if entities.get('location'):
            location = entities['location']
            location_lower = location.lower()
            # Heuristic: multi-word locations with state-like suffixes are states
            # Single-word locations are likely cities/branches
            state_suffixes = ['pradesh', 'nadu', 'bengal', 'kashmir', 'garh', 'khand', 'land']
            word_count = len(location.split())
            if word_count >= 2 or any(kw in location_lower for kw in state_suffixes):
                hint_parts.append(f"- Filter by STATE: {location} - Use the 'State' column for this filter")
            else:
                hint_parts.append(f"- Filter by CITY/BRANCH (NOT State column!): {location} - Use columns like 'Branch', 'Branch_Name', 'City', 'Area Name', 'Area', 'Location' for this filter")
        if entities.get('category'):
            hint_parts.append(f"- Filter by category: {entities['category']}")
        if entities.get('month'):
            hint_parts.append(f"- Time context: {entities['month']}")
        if entities.get('metric'):
            hint_parts.append(f"- Metric focus: {entities['metric']}")
        if entities.get('cross_table_intent'):
            hint_parts.append("- User wants data ACROSS multiple time periods (trend analysis)")
        # Handle "today", "yesterday" etc. - convert to actual dates
        if entities.get('time_period'):
            from datetime import datetime, timedelta
            time_period = entities['time_period'].lower()
            now = datetime.now()

            if time_period == 'today':
                date_str = now.strftime('%Y-%m-%d')
                next_date_str = (now + timedelta(days=1)).strftime('%Y-%m-%d')
                hint_parts.append(f"- **TODAY ({date_str})**: MUST filter Date >= '{date_str}' AND Date < '{next_date_str}'")
            elif time_period == 'yesterday':
                yesterday = now - timedelta(days=1)
                date_str = yesterday.strftime('%Y-%m-%d')
                next_date_str = now.strftime('%Y-%m-%d')
                hint_parts.append(f"- **YESTERDAY ({date_str})**: MUST filter Date >= '{date_str}' AND Date < '{next_date_str}'")
            elif time_period == 'this_week':
                # Start of week (Monday)
                start_of_week = now - timedelta(days=now.weekday())
                hint_parts.append(f"- **THIS WEEK**: Filter Date >= '{start_of_week.strftime('%Y-%m-%d')}'")
            elif time_period == 'last_week':
                start_of_last_week = now - timedelta(days=now.weekday() + 7)
                end_of_last_week = start_of_last_week + timedelta(days=7)
                hint_parts.append(f"- **LAST WEEK**: Filter Date >= '{start_of_last_week.strftime('%Y-%m-%d')}' AND Date < '{end_of_last_week.strftime('%Y-%m-%d')}'")

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
                    hint_parts.append(f"- **SPECIFIC DATE**: {month_name} {day} -> MUST filter: Date >= '{date_str}' AND Date < '{next_date_str}'")
                except ValueError:
                    # Invalid date (e.g., Feb 30), skip date hint
                    pass
            elif day:
                # Only day specified, use with month context
                hint_parts.append(f"- **SPECIFIC DAY**: Day {day} of the month -> Apply date filter for day {day}")
        # Handle negation/exclusion: "except Tamil Nadu", "excluding Dairy"
        if entities.get('negation'):
            neg = entities['negation']
            if neg.get('type') == 'exclude' and neg.get('value'):
                excl_val = neg['value']
                hint_parts.append(f"- **EXCLUSION**: User wants to EXCLUDE '{excl_val}'. Use operator '!=' in subset_filters for the matching column (e.g., State != '{excl_val}' or Category != '{excl_val}')")

        if hint_parts:
            entity_hints = "\n**Extracted Entities (use these for filters):**\n" + "\n".join(hint_parts) + "\n"

        # CRITICAL: Add multi-domain query hints for cross-table execution
        if entities and entities.get('multi_domain_query'):
            multi_domain = entities['multi_domain_query']
            var = multi_domain.get('intermediate_variable', 'target_date')
            cross_table_hint = f"""
**CROSS-TABLE QUERY DETECTED - USE multi_step QUERY TYPE!**
This query requires data from MULTIPLE TABLES. Look at the schema above to identify:
- Step 1: Find the {var} from the relevant table (set output_variable: '{var}', extract_column: usually 'Date')
- Step 2: Use ${{{var}}} in filters to query another table
Use the tables listed in the schema context - don't assume table names.
"""
            entity_hints = entity_hints + cross_table_hint

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
            response = call_llm_with_timeout(user_prompt, model_name, gen_config, timeout_seconds)

            # call_llm_with_timeout returns str directly
            response_text = response if isinstance(response, str) else response.text

            # Parse JSON
            plan = parse_json_response(response_text)

            # Basic structure check (detailed validation happens in validator)
            if not isinstance(plan, dict):
                raise ValueError(f"LLM response is not a JSON object: {type(plan)}")

            if "query_type" not in plan:
                raise ValueError("LLM response missing required field: query_type")

            # multi_step queries don't have a root "table" - each step has its own table
            query_type = plan.get("query_type")
            if query_type == "multi_step":
                # Validate steps array for multi_step queries
                if "steps" not in plan or not isinstance(plan.get("steps"), list) or len(plan.get("steps", [])) == 0:
                    raise ValueError("multi_step query_type requires a non-empty 'steps' array")
                # Validate each step has a table
                for i, step in enumerate(plan.get("steps", [])):
                    if not isinstance(step, dict):
                        raise ValueError(f"Step {i+1} must be a dictionary")
                    if "table" not in step:
                        raise ValueError(f"Step {i+1} missing required field: table")
            else:
                # Standard queries require root-level table
                if "table" not in plan:
                    raise ValueError("LLM response missing required field: table")

            # === TYPE VALIDATION ===
            # Ensure critical fields have correct types to prevent downstream errors
            if not isinstance(plan.get("query_type"), str):
                raise ValueError(f"query_type must be a string, got: {type(plan.get('query_type'))}")

            # Only validate root table for non-multi_step queries
            if query_type != "multi_step" and not isinstance(plan.get("table"), str):
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
            logger.info("LLM Planning generated [%dms]", int(elapsed))
            return plan

        except TimeoutError as e:
            last_error = e
            logger.warning("Attempt %s/%s timed out", attempt + 1, max_retries)
            if attempt < max_retries - 1:
                wait = 0.5 * (2 ** attempt)  # 0.5s, 1s, 2s
                logger.info("Retrying in %.1fs...", wait)
                time.sleep(wait)
                continue
            else:
                raise TimeoutError(f"LLM request timed out after {max_retries} attempts")

        except json.JSONDecodeError as e:
            last_error = e
            if attempt < max_retries - 1:
                wait = 0.5 * (2 ** attempt)
                logger.info("JSON parse failed, retrying in %.1fs...", wait)
                time.sleep(wait)
                continue
            else:
                raise ValueError(f"Failed to parse valid JSON after {max_retries} attempts: {e}")

        except Exception as e:
            last_error = e
            error_msg = str(e).lower()
            if attempt < max_retries - 1:
                # Longer backoff for rate limits (429 / resource_exhausted)
                if "429" in error_msg or "resource_exhausted" in error_msg or "quota" in error_msg:
                    wait = 2.0 * (2 ** attempt)  # 2s, 4s, 8s
                    logger.warning("Rate limit hit, backing off %.1fs (attempt %d/%d)", wait, attempt + 1, max_retries)
                else:
                    wait = 0.5 * (2 ** attempt)  # 0.5s, 1s, 2s
                    logger.info("Error, retrying in %.1fs...", wait)
                time.sleep(wait)
                continue
            else:
                raise ValueError(f"Failed to generate plan after {max_retries} attempts: {e}")
    
    # Should never reach here, but just in case
    raise ValueError(f"Failed to generate plan: {last_error}")
