import os
import json
import yaml
import threading
import google.generativeai as genai
from pathlib import Path
from explanation_layer.explanation_prompt import EXPLANATION_SYSTEM_PROMPT

# Backend directory for relative paths
_BACKEND_DIR = Path(__file__).parent.parent
from dotenv import load_dotenv
from utils.permanent_memory import format_memory_for_prompt

# Load environment variables
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
# Saves 2-4 seconds per query by reusing model
# ============================================
_explainer_model = None
_explainer_model_lock = threading.Lock()
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


def get_explainer_model():
    """
    Get or create singleton Gemini model instance for explanations.
    Thread-safe with double-checked locking pattern.

    Returns:
        GenerativeModel: Reusable Gemini model instance
    """
    global _explainer_model

    # Fast path - model already exists
    if _explainer_model is not None:
        return _explainer_model

    # Slow path - need to create model (thread-safe)
    with _explainer_model_lock:
        # Double-check after acquiring lock
        if _explainer_model is not None:
            return _explainer_model

        config = load_config()
        _explainer_model = initialize_gemini_client(config)
        return _explainer_model


def invalidate_explainer_model():
    """
    Invalidate the cached model (e.g., when memory/config changes).
    Call this when permanent memory is updated.
    """
    global _explainer_model, _config_cache
    with _explainer_model_lock:
        _explainer_model = None
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

    model_name = config.get("model", "gemini-2.0-flash")
    temperature = config.get("temperature", 0.0)

    # Limit output tokens for faster response (explanations are short)
    max_tokens = config.get("explainer_max_tokens", 300)

    generation_config = {
        "temperature": temperature,
        "max_output_tokens": max_tokens,
    }

    # Load and inject permanent memory into system prompt
    memory_constraints = format_memory_for_prompt()
    system_prompt = EXPLANATION_SYSTEM_PROMPT + memory_constraints

    # Create base model without system_instruction (for compatibility with 0.3.x)
    base_model = genai.GenerativeModel(
        model_name=model_name,
        generation_config=generation_config,
    )

    # Wrap with our compatible model that handles system prompts
    return CompatibleGenerativeModel(base_model, system_prompt)


def _format_number_indian(value, use_word=True):
    """
    Format a number in Indian style (crores, lakhs, thousands).

    Args:
        value: The numeric value to format
        use_word: If True, use words like "crores", "lakhs". If False, use Indian comma format.

    Examples:
        12500000 -> "1.25 crores" or "1,25,00,000"
        550000 -> "5.5 lakhs" or "5,50,000"
        45000 -> "45 thousand" or "45,000"
    """
    if not isinstance(value, (int, float)):
        return str(value)

    abs_value = abs(value)
    sign = "-" if value < 0 else ""

    if use_word:
        if abs_value >= 10000000:  # 1 crore = 1,00,00,000
            crores = abs_value / 10000000
            if crores >= 10:
                return f"{sign}about {crores:.0f} crores"
            else:
                return f"{sign}about {crores:.1f} crores"
        elif abs_value >= 100000:  # 1 lakh = 1,00,000
            lakhs = abs_value / 100000
            if lakhs >= 10:
                return f"{sign}about {lakhs:.0f} lakhs"
            else:
                return f"{sign}about {lakhs:.1f} lakhs"
        elif abs_value >= 1000:
            thousands = abs_value / 1000
            return f"{sign}around {thousands:.0f} thousand"
        elif isinstance(value, float):
            return f"{sign}{abs_value:.2f}"
        else:
            return f"{sign}{int(abs_value)}"
    else:
        # Indian comma format: 1,23,45,678
        return _format_indian_commas(value)


def _format_indian_commas(value):
    """Format number with Indian comma style (1,23,45,678)."""
    if not isinstance(value, (int, float)):
        return str(value)

    is_negative = value < 0
    value = abs(value)

    if isinstance(value, float):
        integer_part = int(value)
        decimal_part = value - integer_part
        if decimal_part > 0:
            decimal_str = f".{int(decimal_part * 100):02d}"
        else:
            decimal_str = ""
    else:
        integer_part = value
        decimal_str = ""

    # Convert to string and apply Indian comma grouping
    s = str(integer_part)
    if len(s) <= 3:
        result = s
    else:
        # First group of 3 from right, then groups of 2
        result = s[-3:]
        s = s[:-3]
        while s:
            result = s[-2:] + "," + result
            s = s[:-2]

    return ("-" if is_negative else "") + result + decimal_str


def _format_number_natural(value):
    """Format a number in natural speech format (Indian style - crores, lakhs, thousands)."""
    return _format_number_indian(value, use_word=True)


def _is_simple_aggregation(result_df, query_plan):
    """Check if this is a simple aggregation that can skip LLM."""
    if result_df is None or len(result_df) == 0:
        return False
    if len(result_df) > 1:
        return False  # Multiple rows need LLM for explanation

    # Check if it's a simple aggregation query
    if query_plan:
        agg_func = query_plan.get("aggregation_function")
        query_type = query_plan.get("query_type")
        if agg_func in ["SUM", "AVG", "COUNT", "MAX", "MIN"]:
            return True
        if query_type in ["aggregation", "count"]:
            return True

    return False


def explain_results(result_df, query_plan=None, original_question=None, raw_user_message=None, user_name=None):
    """
    Generate a natural language explanation of query results using LLM.

    Args:
        result_df: DataFrame containing query results
        query_plan: Optional dict containing the query plan (for context)
        original_question: Optional string containing the processed/translated question
        raw_user_message: Optional string - the user's ORIGINAL message (preserves emotional tone)
        user_name: Optional string - session name from "Call me X" for personalized responses

    Returns:
        str: Natural language explanation of the results
    """
    import time
    _start = time.time()

    # Detect the language of the original question first
    question_language = "English"  # Default
    if original_question:
        try:
            from langdetect import detect
            from langdetect.lang_detect_exception import LangDetectException
            import re
            # Check for Tamil characters
            tamil_pattern = re.compile(r'[\u0B80-\u0BFF]')
            if tamil_pattern.search(original_question):
                question_language = "Tamil"
            else:
                detected = detect(original_question)
                if detected == 'ta':
                    question_language = "Tamil"
        except (ImportError, Exception):
            pass  # Language detection is optional
    
    if result_df.empty:
        # Provide helpful message in Thara's charming personality
        # NOTE: Pure Tamil for Tamil responses, pure English for English responses
        # This ensures proper TTS pronunciation (no Tanglish mixing)
        if question_language == "Tamil":
            no_data_responses = [
                "ஹ்ம்ம், இதற்கு தகவல் கிடைக்கவில்லை! வேறு விதமாக கேட்கலாமா?",
                "அச்சச்சோ! இதற்கு எந்த தகவலும் இல்லை போல. வேறு தேதி அல்லது பெயர் முயற்சிக்கலாமா?",
                "ஓ! இதற்கு ஒன்றும் கிடைக்கவில்லை. வேறு வழியில் தேடலாமா?",
                "அட! இந்த தேடலுக்கு தகவல் இல்லை. வேறு எதாவது முயற்சிக்கலாமா?",
            ]
        else:
            no_data_responses = [
                "Hmm, I couldn't find any data for that! Want to try a different filter or spelling?",
                "Oops! Looks like there's no data matching that. Maybe try a different date range or check the spelling?",
                "Aww, nothing came up for that search! Let's try tweaking the criteria - what do you think?",
                "No luck with that one! The data might be under a different name - want me to help you explore?",
            ]
        import random
        return random.choice(no_data_responses)
    
    # Build context for the LLM
    context = {
        "row_count": len(result_df),
        "columns": list(result_df.columns),
        "data_sample": result_df.head(5).to_dict('records')  # Show up to 5 rows (reduced for speed)
    }
    
    # Add query plan context if available
    if query_plan:
        context["query_type"] = query_plan.get("query_type")
        context["table"] = query_plan.get("table")  # Add table/sheet name
        context["aggregation_function"] = query_plan.get("aggregation_function")
        context["aggregation_column"] = query_plan.get("aggregation_column")
        context["filters"] = query_plan.get("filters", [])
        context["subset_filters"] = query_plan.get("subset_filters", [])
    
    # Add aggregation metadata if present (from executor)
    if hasattr(result_df, 'attrs'):
        if 'aggregation_function' in result_df.attrs:
            context["aggregation_function"] = result_df.attrs['aggregation_function']
        if 'aggregation_column' in result_df.attrs:
            context["aggregation_column"] = result_df.attrs['aggregation_column']
        # Add advanced query analysis if present
        if result_df.attrs.get('is_advanced_query'):
            context["is_advanced_query"] = True
            context["analysis"] = result_df.attrs.get('analysis', {})
            context["calculation_result"] = result_df.attrs.get('calculation_result')
        
        # Add multi-step query metadata if present (cross-table queries)
        if result_df.attrs.get('is_multi_step'):
            context["is_multi_step"] = True
            context["analysis"] = result_df.attrs.get('analysis', {})
            context["steps_executed"] = result_df.attrs.get('steps_executed', [])
            context["variables"] = result_df.attrs.get('variables', {})
    
    # Build the prompt for the LLM
    prompt = f"""Given the following query results, generate a concise, natural language explanation.

Context:
{json.dumps(context, indent=2, default=str)}
"""
    
    if original_question:
        prompt += f"\nProcessed Question: {original_question}\n"
        prompt += f"Question Language: {question_language}\n"

    # Include original message for emotion detection (CRITICAL for empathetic responses)
    if raw_user_message:
        prompt += f"\n**User's Original Message (check for emotions!):** {raw_user_message}\n"

    # Build name instruction for personalization
    name_instruction = ""
    if user_name:
        name_instruction = f"""
4. **CRITICAL - Use the user's name "{user_name}"**: Start warmly with their name like:
   - "Okay {user_name}, so..."
   - "Alright {user_name}, looking at this..."
   - "Hmm {user_name}, here's what I see..."
   - "So {user_name},"
   - "Yeah {user_name}, the data shows..."
   Make it feel like you're talking to a friend. ALWAYS include their name in the opener!
"""

    prompt += f"""
Instructions:
1. **Respond in {question_language} language**
2. **USE INDIAN NUMBER SYSTEM** (CRITICAL for TTS):
   - 1,25,00,000 (1.25 crores) -> "about 1.25 crores"
   - 62,89,508 -> "about 63 lakhs"
   - 11,00,000 -> "about 11 lakhs"
   - 5,70,000 -> "about 5.7 lakhs"
   - 45,000 -> "around 45 thousand"
   - 12.47% -> "about 12 percent"
   - Round to 1-2 significant digits. Nobody says exact decimals in conversation.
3. **Be casual & crispy**: Start with "So...", "Looking at this...", "Alright..."
{name_instruction}5. **2-3 sentences MAX**: One key insight + one supporting detail
6. **Sound human**: Use contractions (it's, that's), natural pauses, confident endings

**INDIAN NUMBER SYSTEM RULES:**
- 1 Crore = 1,00,00,000 (10 million)
- 1 Lakh = 1,00,000 (100 thousand)
- Crores: round to 1-2 decimals -> 1,25,00,000 = "about 1.25 crores"
- Lakhs: round to 1 decimal -> 62,89,508 = "about 63 lakhs"
- Thousands: round to nearest thousand -> 45,678 = "around 46 thousand"
- Percentages: round to whole number -> 12.47% = "about 12 percent"

BAD (robotic): "six million two hundred eighty nine thousand five hundred eight"
GOOD (natural): "about 63 lakhs"

**For TREND data:**
- Overall direction first: "Sales are pretty stable" or "There's a clear upward trend"
- Peak/low with rounded values: "peaked around 4.6 lakhs"
- Keep it to 2-3 sentences

**For AGGREGATION (sum, avg, count):**
- Direct answer: "Total sales is about 12.5 lakhs"

**For COMPARISON:**
- Lead with winner: "Tamil Nadu's on top with about 4.2 lakhs"
- Relative language: "almost double", "slightly ahead"

**For EXTREMA (max, min, top N):**
- Direct: "Velachery leads with around 85 thousand"

**For SUMMARY/OVERVIEW questions:**
- Give the big picture first: "Overall, business looks healthy..."
- Mention 2-3 key metrics with rounded values
- Highlight any standout category/area
- Keep it under 3-4 sentences

**For IMPACT/CORRELATION questions:**
- State the relationship: "Sales has a stronger impact on profit than cost"
- Explain why briefly: "Higher sales directly boost margins"
- Suggest actionable insight if relevant

**AVOID (CRITICAL):**
- DON'T spell out large numbers word by word (sounds robotic)
- DON'T list every data point
- DON'T be verbose
- DON'T add filler ("Great question", "I'd be happy to help")

Generate a crispy, TTS-friendly response:"""
    
    try:
        # Get singleton LLM (saves 2-4s per query)
        model = get_explainer_model()

        # Generate explanation
        response = model.generate_content(prompt)
        explanation = response.text.strip()

        elapsed = (time.time() - _start) * 1000
        print(f"[YES] LLM Explanation generated [{elapsed:.0f}ms]")
        return explanation

    except Exception as e:
        # Fallback to simple explanation if LLM fails
        elapsed = (time.time() - _start) * 1000
        print(f"[WARN] LLM explanation failed ({e}), using fallback [{elapsed:.0f}ms]")
        return _fallback_explanation(result_df, context)


def _fallback_explanation(result_df, context):
    """
    Simple fallback explanation when LLM is unavailable.
    This is much simpler and just presents the data.
    """
    # Handle advanced query types first
    if context.get("is_advanced_query"):
        return _fallback_advanced_explanation(context)

    if result_df.empty:
        return "No data is available for the requested criteria."

    # Check for aggregation
    agg_func = context.get("aggregation_function")
    agg_col = context.get("aggregation_column")
    
    if agg_func and agg_col and agg_col in result_df.columns:
        values = result_df[agg_col].dropna()
        
        if len(values) == 0:
            return f"No valid values found in '{agg_col}' column"
        
        # Calculate based on aggregation function
        if agg_func == "AVG":
            result = values.mean()
            func_name = "average"
        elif agg_func == "SUM":
            result = values.sum()
            func_name = "total"
        elif agg_func == "COUNT":
            result = len(values)
            func_name = "count"
        elif agg_func == "MAX":
            result = values.max()
            func_name = "maximum"
        elif agg_func == "MIN":
            result = values.min()
            func_name = "minimum"
        else:
            result = values.mean()
            func_name = "result"
        
        # Format result
        if isinstance(result, float):
            formatted_result = f"{result:.2f}"
        else:
            formatted_result = str(result)
        
        explanation = f"The {func_name} is {formatted_result}"
        
        # Add breakdown for MIN/MAX
        if agg_func in ["MIN", "MAX"]:
            matching_rows = result_df[result_df[agg_col] == result]
            if len(matching_rows) > 0:
                explanation += f"\n\nThis value appears in {len(matching_rows)} row(s)"
        
        return explanation
    
    # For non-aggregation queries
    row_count = len(result_df)
    
    if row_count == 1:
        # Single row result
        parts = []
        for col in result_df.columns:
            value = result_df[col].iloc[0]
            parts.append(f"{col} = {value}")
        return ", ".join(parts)
    else:
        # Multiple rows
        return f"Found {row_count} results with columns: {', '.join(result_df.columns)}"


def _fallback_advanced_explanation(context):
    """
    Fallback explanation for advanced query types (comparison, percentage, trend).
    """
    analysis = context.get("analysis", {})
    query_type = context.get("query_type")

    if "error" in analysis:
        return f"Could not complete the analysis: {analysis['error']}"

    if query_type == "comparison":
        period_a = analysis.get("period_a_label", "Period A")
        period_b = analysis.get("period_b_label", "Period B")
        value_a = analysis.get("period_a_value", 0)
        value_b = analysis.get("period_b_value", 0)
        direction = analysis.get("direction", "changed")
        emoji = analysis.get("direction_emoji", "")
        pct_change = analysis.get("percentage_change")

        # Use Indian number formatting
        formatted_a = _format_number_indian(value_a)
        formatted_b = _format_number_indian(value_b)

        if direction == "increased":
            return f"{emoji} Sales increased from {formatted_a} ({period_a}) to {formatted_b} ({period_b}) - a {abs(pct_change):.0f}% increase"
        elif direction == "decreased":
            return f"{emoji} Sales decreased from {formatted_a} ({period_a}) to {formatted_b} ({period_b}) - a {abs(pct_change):.0f}% decrease"
        else:
            return f"Sales remained stable between {period_a} ({formatted_a}) and {period_b} ({formatted_b})"

    elif query_type == "percentage":
        percentage = analysis.get("percentage", 0)
        numerator = analysis.get("numerator_value", 0)
        denominator = analysis.get("denominator_value", 0)
        formatted_num = _format_number_indian(numerator)
        formatted_den = _format_number_indian(denominator)
        return f"The selected items contribute about {percentage:.0f}% of the total ({formatted_num} out of {formatted_den})"

    elif query_type == "trend":
        direction = analysis.get("direction", "unknown")
        emoji = analysis.get("direction_emoji", "")
        pct_change = analysis.get("percentage_change")
        start_val = analysis.get("start_value", 0)
        end_val = analysis.get("end_value", 0)
        max_date = analysis.get("max_date")
        min_date = analysis.get("min_date")
        max_value = analysis.get("max_value", 0)
        has_spike = analysis.get("has_unusual_spike", False)

        # Use Indian number formatting
        formatted_start = _format_number_indian(start_val)
        formatted_end = _format_number_indian(end_val)
        formatted_max = _format_number_indian(max_value)

        # Check if this is a spike/anomaly query
        spike_info = ""
        if max_date and max_value:
            spike_info = f" The highest point was in {max_date} at {formatted_max}."
            if has_spike:
                spike_info = f" There was an unusual spike in {max_date} reaching {formatted_max}!"

        if direction == "increasing":
            return f"{emoji} Sales are trending upward - from {formatted_start} to {formatted_end} ({pct_change:.0f}% total change).{spike_info}"
        elif direction == "decreasing":
            return f"{emoji} Sales are trending downward - from {formatted_start} to {formatted_end} ({pct_change:.0f}% total change).{spike_info}"
        else:
            return f"{emoji} Sales are relatively stable - from {formatted_start} to {formatted_end}.{spike_info}"

    return "Analysis completed but no specific insights available."


def generate_off_topic_response(user_message: str, is_tamil: bool = False) -> str:
    """
    Generate an LLM response for off-topic/non-data queries OR unclear messages.

    Uses the LLM to create natural, charming responses that gently redirect
    the user back to data queries while engaging with their message.

    CRITICAL: This function handles BOTH:
    1. Clear off-topic messages (weather, jokes, personal questions)
    2. Unclear/noisy messages that couldn't be understood

    The LLM should NEVER say "I didn't catch that" - instead, respond
    conversationally and ask what data they want to explore.

    Args:
        user_message: The user's message (could be off-topic or unclear)
        is_tamil: Whether the user is speaking Tamil

    Returns:
        str: LLM-generated charming, conversational response
    """
    import time
    _start = time.time()

    language_instruction = "Tamil (use Tamil script with some English words naturally mixed in - Tanglish style)" if is_tamil else "English"

    prompt = f"""You are Thara, a charming, warm, and delightful personal data assistant.

**YOUR IDENTITY:**
- Your name is Thara
- You are a friendly AI data assistant
- You help users explore their spreadsheet data (sales, trends, profits, etc.)
- You speak both English and Tamil naturally

**YOUR PERSONALITY:**
- Warm, friendly, natural - like chatting with a smart friend
- Confident but not arrogant
- Brief and to the point - no lengthy responses
- Naturally curious about what data they want to explore

**USER'S MESSAGE:** "{user_message}"

**RESPOND BASED ON WHAT THEY SAID:**

For GREETINGS (hi, hello, hey):
- Greet back warmly, ask what they'd like to explore
- "Hey! Great to see you! What would you like to look at today?"

For IDENTITY questions (what's your name, who are you):
- Introduce yourself briefly
- "I'm Thara, your data assistant! What can I help you find?"

For CAPABILITY questions (what can you do, what questions can I ask):
- Explain briefly what you can do with examples
- "You can ask me things like: What were total sales last month? Show me top 5 products. Compare Chennai vs Bangalore. Which branch has highest profit?"

For PERSONAL questions (how are you, did you eat):
- Answer naturally, then redirect to data
- "Doing great! What data would you like me to look up?"

For UNCLEAR/GIBBERISH:
- Just be friendly and ask what they want
- "Hey! I'm ready - what would you like to know?"

**RULES:**
1. Keep it SHORT - 1-2 sentences max
2. Always end by asking what data they want OR offering to help
3. Be NATURAL - vary your responses, don't sound scripted
4. Respond in {language_instruction}
5. NEVER say "I didn't catch that" or "I don't understand"
6. NEVER repeat the same phrase patterns

Generate a natural, conversational response:"""

    try:
        model = get_explainer_model()
        response = model.generate_content(prompt)
        result = response.text.strip()

        elapsed = (time.time() - _start) * 1000
        print(f"[YES] Off-topic LLM response generated [{elapsed:.0f}ms]")
        return result

    except Exception as e:
        # Fallback to simple response if LLM fails
        elapsed = (time.time() - _start) * 1000
        print(f"[WARN] Off-topic LLM failed ({e}), using fallback [{elapsed:.0f}ms]")

        if is_tamil:
            return "Haha interesting! Naan data expert - sales, trends pathi kelu! Enna paakanum?"
        else:
            return "Haha, that's fun! But my superpower is data - ask me about sales, trends, or insights!"
