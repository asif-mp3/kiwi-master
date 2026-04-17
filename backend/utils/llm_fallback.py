"""
Gemini LLM fallback — used when the structured query pipeline fails.
Sends the question to Gemini Flash as a general-purpose LLM with schema context.
"""
import os
from typing import List, Optional

from utils.logger import get_logger
from utils.config_loader import get_llm_config

logger = get_logger("llm_fallback")


def get_schema_summary(profile_store) -> str:
    """Generate a compact schema summary for LLM fallback context."""
    try:
        profiles = profile_store.get_all_profiles()
        parts = []
        for name, profile in list(profiles.items())[:10]:
            cols = list(profile.get('columns', {}).keys())[:8]
            row_count = profile.get('total_rows', '?')
            parts.append(f"- {name} ({row_count} rows): {', '.join(cols)}")
        return "\n".join(parts) if parts else "No tables loaded."
    except Exception:
        return "Schema information unavailable."


def gemini_general_fallback(
    question: str,
    available_tables: List[str],
    schema_summary: str,
    user_name: str = "Boss",
    routed_table: Optional[str] = None,
) -> str:
    """
    Use Gemini as a general LLM when the structured query pipeline fails.
    Provides a helpful response with table/column suggestions.

    Returns:
        A natural language response from Gemini.
    """
    try:
        from google.genai import types
        from utils.config_loader import get_genai_client

        try:
            client = get_genai_client()
        except ValueError:
            return ""

        table_context = ""
        if routed_table:
            table_context = f"\nThe system identified '{routed_table}' as the most relevant table but couldn't build a query."

        prompt = f"""You are Thara, a friendly data assistant who speaks in a natural Tamil-English (Tanglish) style.
The user asked a question but the structured query system couldn't handle it. Help them.

Available data tables: {', '.join(available_tables[:15])}
Schema overview:
{schema_summary}
{table_context}

User question: {question}

Rules:
- Address the user as "{user_name}"
- If the question is about data in the tables, explain what tables/columns are available and suggest a SPECIFIC rephrased question they could ask
- If the question is too complex for a single query, suggest breaking it into simpler steps
- If it's a general knowledge question unrelated to the data, answer briefly then redirect
- Keep Thara's friendly personality — mix Tamil and English naturally
- Be concise (2-4 sentences max)
- NEVER make up data numbers — only describe what data is available
- Do NOT ask questions back — give a helpful statement"""

        response = client.models.generate_content(
            model=get_llm_config().model,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.7,
                max_output_tokens=200,
            ),
        )
        return response.text.strip()

    except Exception as e:
        logger.warning("Gemini fallback failed: %s", e)
        return ""
