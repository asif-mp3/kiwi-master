"""
LLM-based Table Selector - Uses LLM reasoning to select the right table(s).

This is a PURE LLM approach - no hardcoded rules or keywords.
The LLM understands the question semantics and table contents to make decisions.

Key advantages:
1. No hardcoded weights - works with any schema
2. Understands question intent, not just keywords
3. Can reason about table relationships
4. Provides explanation for debugging
"""

import os
import json
import threading
from typing import Dict, List, Any, Optional, Tuple
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Singleton model for table selection (separate from planner)
_selector_model = None
_selector_model_lock = threading.Lock()


def get_selector_model():
    """
    Get or create singleton Gemini model for table selection.
    Uses a fast model (gemini-2.0-flash) for low latency.
    """
    global _selector_model

    if _selector_model is not None:
        return _selector_model

    with _selector_model_lock:
        if _selector_model is not None:
            return _selector_model

        import google.generativeai as genai

        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in environment")

        genai.configure(api_key=api_key)

        # Use fast model for table selection
        _selector_model = genai.GenerativeModel(
            model_name="gemini-2.0-flash",
            generation_config={
                "temperature": 0.0,  # Deterministic
                "response_mime_type": "application/json",
                "max_output_tokens": 500,
            },
            system_instruction=TABLE_SELECTOR_PROMPT
        )

        return _selector_model


TABLE_SELECTOR_PROMPT = """You are an expert database table selector. Your job is to analyze a user's question and select the BEST table from the available tables to answer it.

## How to Select the Right Table

1. **Understand the Question Intent**:
   - What is the user asking for? (count, percentage, comparison, list, lookup)
   - What entity are they asking about? (branches, transactions, sales, employees)
   - What dimensions/filters are mentioned? (payment mode, location, date, category)

2. **Match Question to Table**:
   - Look at table NAMES - they often indicate what data they contain
   - Look at COLUMNS - ensure the table has the columns needed to answer
   - Look at SAMPLE VALUES - ensure the table contains the specific values mentioned
   - Look at ROW COUNT - for "how many" questions, need tables with complete data

3. **Critical Rules**:
   - For "how many X" questions: Select the table with MOST rows that has X data. NEVER use "Top_N" tables.
   - For "percentage" questions: Need a table with the breakdown dimension (e.g., Payment_Mode column for UPI %)
   - For "show all" questions: Need the detailed transaction-level table
   - Tables marked as "PARTIAL DATA" or "Top N only" do NOT have complete data

4. **Validate Your Choice**:
   - Does this table have the column needed for filtering? (e.g., State column for "Tamil Nadu")
   - Does this table have the metric column? (e.g., Sales, Revenue, Amount)
   - Does this table contain the specific values mentioned? (e.g., "UPI" in Payment_Mode values)

## Output Format
Return JSON with these fields:
{
  "selected_table": "exact_table_name",
  "confidence": 0.0-1.0,
  "reason": "why this table is best for this question",
  "alternative": "second_best_table or null"
}

IMPORTANT: Output ONLY valid JSON, no other text."""


def build_rich_table_context(profiles: Dict[str, Dict]) -> str:
    """
    Build a rich context string describing all tables for the LLM.
    Includes table names, columns, sample values, and row counts.
    """
    if not profiles:
        return "No tables available."

    lines = ["# Available Tables\n"]

    for table_name, profile in profiles.items():
        row_count = profile.get('row_count', 0)
        table_type = profile.get('table_type', 'unknown')

        # Check if this is a partial data table
        name_lower = table_name.lower()
        is_partial = any(x in name_lower for x in ['top_', 'top20', 'top10', 'summary'])
        partial_note = " [PARTIAL DATA - Top N only, NOT for counting]" if is_partial else ""

        lines.append(f"## {table_name}{partial_note}")
        lines.append(f"- Rows: {row_count}")
        lines.append(f"- Type: {table_type}")

        # Add semantic summary if available
        if profile.get('semantic_summary'):
            lines.append(f"- Summary: {profile['semantic_summary']}")

        # Add columns with their roles and sample values
        columns = profile.get('columns', {})
        if columns:
            lines.append("- Columns:")
            for col_name, col_info in list(columns.items())[:15]:  # Limit columns shown
                role = col_info.get('role', 'unknown')
                unique_values = col_info.get('unique_values', [])

                col_desc = f"  - {col_name} [{role}]"
                if unique_values and role == 'dimension':
                    # Show sample values for dimensions
                    sample = ', '.join(str(v) for v in unique_values[:5])
                    col_desc += f" (values: {sample})"
                lines.append(col_desc)

        lines.append("")  # Blank line between tables

    return "\n".join(lines)


def select_table_with_llm(
    question: str,
    table_context: str,
    timeout_seconds: int = 10,
    verbose: bool = True
) -> Dict[str, Any]:
    """
    Use LLM to select the best table for a question.
    This is the PRIMARY selection method - pure LLM reasoning.
    """
    import concurrent.futures
    import time

    if verbose:
        print("\n" + "="*60)
        print("🤖 LLM TABLE SELECTOR")
        print("="*60)
        print(f"📝 Question: {question}")
        print(f"\n📊 Tables provided to LLM:")
        # Show summary of tables
        for line in table_context.split('\n'):
            if line.startswith('## '):
                print(f"   {line[3:]}")

    try:
        start_time = time.time()
        model = get_selector_model()

        prompt = f"""# Question
{question}

# Available Tables
{table_context}

Analyze the question and select the BEST table to answer it. Consider:
1. What data does the question need?
2. Which table has that data?
3. Is the data complete (check row count and partial data warnings)?

Output JSON only."""

        if verbose:
            print(f"\n⏳ Calling LLM...")

        # Call with timeout
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(model.generate_content, prompt)
            try:
                response = future.result(timeout=timeout_seconds)
            except concurrent.futures.TimeoutError:
                if verbose:
                    print(f"❌ LLM TIMEOUT after {timeout_seconds}s")
                return {
                    "selected_table": None,
                    "confidence": 0.0,
                    "reason": "LLM timeout",
                    "alternative": None,
                    "error": "timeout"
                }

        elapsed = time.time() - start_time

        # Parse JSON response
        response_text = response.text.strip()

        # Remove markdown if present
        if response_text.startswith("```"):
            lines = response_text.split("\n")
            response_text = "\n".join(lines[1:-1])
            if response_text.startswith("json"):
                response_text = response_text[4:].strip()

        result = json.loads(response_text)

        if verbose:
            print(f"✅ LLM responded in {elapsed:.2f}s")
            print(f"\n🎯 LLM DECISION:")
            print(f"   Table: {result.get('selected_table')}")
            print(f"   Confidence: {result.get('confidence', 0):.0%}")
            print(f"   Reason: {result.get('reason', 'N/A')}")
            if result.get('alternative'):
                print(f"   Alternative: {result.get('alternative')}")
            print("="*60)

        return result

    except Exception as e:
        if verbose:
            print(f"❌ LLM ERROR: {str(e)}")
        return {
            "selected_table": None,
            "confidence": 0.0,
            "reason": f"LLM error: {str(e)}",
            "alternative": None,
            "error": str(e)
        }


def select_table_hybrid(
    question: str,
    profiles: Dict[str, Dict],
    entities: Dict[str, Any] = None,
    use_llm: bool = True,
    llm_timeout: int = 10,
    verbose: bool = True
) -> Tuple[Optional[str], float, str]:
    """
    LLM-first table selection. No hardcoded rules.

    The LLM analyzes the question and table metadata to select the best table.

    Args:
        question: User's question
        profiles: Dict of table_name -> profile
        entities: Pre-extracted entities (optional, passed to LLM as hints)
        use_llm: Whether to use LLM (set False for testing)
        llm_timeout: Max seconds for LLM call
        verbose: Print detailed logs

    Returns:
        Tuple of (table_name, confidence, reason)
    """
    if not profiles:
        return (None, 0.0, "No tables available")

    if verbose:
        print(f"\n📊 Available Tables ({len(profiles)}):")
        for name, prof in profiles.items():
            row_count = prof.get('row_count', 0)
            print(f"   • {name} ({row_count} rows)")

    # Build rich context for LLM
    table_context = build_rich_table_context(profiles)

    # Use LLM for selection
    if use_llm:
        llm_result = select_table_with_llm(question, table_context, llm_timeout, verbose=verbose)

        if llm_result.get("selected_table") and not llm_result.get("error"):
            selected = llm_result["selected_table"]

            # Validate table exists (exact or case-insensitive match)
            if selected in profiles:
                return (
                    selected,
                    llm_result.get("confidence", 0.7),
                    llm_result.get("reason", "LLM selection")
                )

            # Try case-insensitive match
            for table_name in profiles.keys():
                if table_name.lower() == selected.lower():
                    return (
                        table_name,
                        llm_result.get("confidence", 0.7),
                        llm_result.get("reason", "LLM selection")
                    )

            if verbose:
                print(f"⚠️  LLM selected '{selected}' but table not found in profiles")

    # Fallback: return table with most rows
    if profiles:
        sorted_tables = sorted(
            profiles.items(),
            key=lambda x: x[1].get('row_count', 0),
            reverse=True
        )
        if verbose:
            print(f"⚠️  Fallback: using largest table {sorted_tables[0][0]}")
        return (sorted_tables[0][0], 0.3, "Fallback: largest table")

    return (None, 0.0, "No tables available")


def invalidate_selector_model():
    """Invalidate cached selector model (call when config changes)."""
    global _selector_model
    with _selector_model_lock:
        _selector_model = None
