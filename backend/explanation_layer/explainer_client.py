import os
import json
import yaml
import threading
import google.generativeai as genai
from pathlib import Path
from explanation_layer.explanation_prompt import EXPLANATION_SYSTEM_PROMPT
from dotenv import load_dotenv
from utils.permanent_memory import format_memory_for_prompt

# Load environment variables
load_dotenv()

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

    config_path = Path("config/settings.yaml")
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
    
    model_name = config.get("model", "gemini-2.0-flash-exp")
    temperature = config.get("temperature", 0.0)
    
    generation_config = {
        "temperature": temperature,
    }
    
    # Load and inject permanent memory into system prompt
    memory_constraints = format_memory_for_prompt()
    system_prompt = EXPLANATION_SYSTEM_PROMPT + memory_constraints
    
    model = genai.GenerativeModel(
        model_name=model_name,
        generation_config=generation_config,
        system_instruction=system_prompt
    )
    
    return model


def explain_results(result_df, query_plan=None, original_question=None):
    """
    Generate a natural language explanation of query results using LLM.
    
    Args:
        result_df: DataFrame containing query results
        query_plan: Optional dict containing the query plan (for context)
        original_question: Optional string containing the user's original question
    
    Returns:    
        str: Natural language explanation of the results
    """
    # Detect the language of the original question first
    question_language = "English"  # Default
    if original_question:
        try:
            from langdetect import detect
            import re
            # Check for Tamil characters
            tamil_pattern = re.compile(r'[\u0B80-\u0BFF]')
            if tamil_pattern.search(original_question):
                question_language = "Tamil"
            else:
                detected = detect(original_question)
                if detected == 'ta':
                    question_language = "Tamil"
        except:
            pass
    
    if result_df.empty:
        # Provide helpful message in the detected language
        if question_language == "Tamil":
            return "கோரப்பட்ட தகவல் கிடைக்கவில்லை. பெயர் சரியாக உள்ளதா என்று சரிபார்க்கவும்."
        else:
            return "No data found for the requested criteria. Please check if the name or value is spelled correctly."
    
    # Build context for the LLM
    context = {
        "row_count": len(result_df),
        "columns": list(result_df.columns),
        "data_sample": result_df.head(10).to_dict('records')  # Show up to 10 rows
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
    
    # Build the prompt for the LLM
    prompt = f"""Given the following query results, generate a concise, natural language explanation.

Context:
{json.dumps(context, indent=2, default=str)}
"""
    
    if original_question:
        prompt += f"\nOriginal Question: {original_question}\n"
        prompt += f"Question Language: {question_language}\n"
    
    prompt += f"""
Instructions:
1. **IMPORTANT: Respond in {question_language} language**
2. Be concise and direct.
3. Use digits for numbers (e.g., 15,000) for all languages. Do not write them out in words.
4. If this is an aggregation query (AVG, SUM, MIN, MAX, COUNT), state the result clearly using the correct aggregation type.
5. For MIN/MAX queries, also mention which row(s) had that value.
6. For multiple rows, provide a brief summary and list key data points.
7. Use the exact aggregation function name from the context (e.g., "minimum" for MIN, "average" for AVG).
8. Format numbers with commas (e.g., "15,000").
9. Do not add any English translation unless explicitly requested.
10. **For comparison queries**: Use the analysis object to explain the difference between periods. Include the direction (increased/decreased), percentage change, and actual values. Use emojis like 📈 for increase, 📉 for decrease.
11. **For percentage queries**: Clearly state the percentage value and what it represents (e.g., "Top 10 items contribute 65% of total sales").
12. **For trend queries**: Describe the trend direction (increasing/decreasing/stable), mention the overall change, and use appropriate emojis (📈📉➡️).

Generate the explanation:"""
    
    try:
        # Get singleton LLM (saves 2-4s per query)
        model = get_explainer_model()

        # Generate explanation
        response = model.generate_content(prompt)
        explanation = response.text.strip()
        
        return explanation
        
    except Exception as e:
        # Fallback to simple explanation if LLM fails
        print(f"Warning: LLM explanation failed ({e}), using fallback")
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

        if direction == "increased":
            return f"{emoji} Sales increased from {value_a:,.0f} ({period_a}) to {value_b:,.0f} ({period_b}) - a {abs(pct_change):.1f}% increase"
        elif direction == "decreased":
            return f"{emoji} Sales decreased from {value_a:,.0f} ({period_a}) to {value_b:,.0f} ({period_b}) - a {abs(pct_change):.1f}% decrease"
        else:
            return f"Sales remained stable between {period_a} ({value_a:,.0f}) and {period_b} ({value_b:,.0f})"

    elif query_type == "percentage":
        percentage = analysis.get("percentage", 0)
        numerator = analysis.get("numerator_value", 0)
        denominator = analysis.get("denominator_value", 0)
        return f"The selected items contribute {percentage:.1f}% of the total ({numerator:,.0f} out of {denominator:,.0f})"

    elif query_type == "trend":
        direction = analysis.get("direction", "unknown")
        emoji = analysis.get("direction_emoji", "")
        pct_change = analysis.get("percentage_change")
        start_val = analysis.get("start_value", 0)
        end_val = analysis.get("end_value", 0)

        if direction == "increasing":
            return f"{emoji} Sales are trending upward - from {start_val:,.0f} to {end_val:,.0f} ({pct_change:.1f}% total change)"
        elif direction == "decreasing":
            return f"{emoji} Sales are trending downward - from {start_val:,.0f} to {end_val:,.0f} ({pct_change:.1f}% total change)"
        else:
            return f"{emoji} Sales are relatively stable - from {start_val:,.0f} to {end_val:,.0f}"

    return "Analysis completed but no specific insights available."
