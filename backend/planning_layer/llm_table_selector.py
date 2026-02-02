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


# Singleton model for table selection (separate from planner)
_selector_model = None
_selector_model_lock = threading.Lock()


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

3. **Critical Rules for TOTALS/SUMS/COUNTS**:
   **RULE #1: For "total", "sum", "count", "all", "how many" - ALWAYS use the table with HIGHEST ROW COUNT**
   - If one table has 5000+ rows and another has <50 rows, USE THE HIGH ROW COUNT TABLE
   - A table with only a few rows CANNOT contain raw transaction data - it's pre-aggregated!
   - HIGH row count (1000+) = individual records/transactions = USE FOR TOTALS
   - LOW row count (<50) = already summarized/grouped data = NEVER use for raw totals

4. **Row Count Guide**:
   - 5000+ rows = Transaction-level raw data → BEST for totals/counts
   - 100-500 rows = Branch/item level data → Good for breakdowns
   - 10-50 rows = Category/monthly summaries → Use only for summary questions
   - 3-10 rows = Quarterly/annual summaries → NEVER use for "total" or "all" questions

5. **CRITICAL: Time-Filtered Queries**:
   **RULE #2: For queries with TIME FILTERS, ALWAYS use TRANSACTIONAL tables with Date column**
   - Keywords: "last month", "last 3 months", "yesterday", "this week", "November", "October", etc.
   - Summary tables (10-50 rows) have PRE-AGGREGATED data - they CANNOT be filtered by date!
   - Example: "category-wise sales for last 3 months" → MUST use Daily_Sales_Transactions (has Date column)
   - Example: "sales in November" → MUST use table with Date column, NOT a summary table
   - If question mentions ANY time period, use the HIGH ROW COUNT table with Date column
   - A Monthly_Category_Summary table shows ALL-TIME data, not filterable by date

6. **CRITICAL: TREND Queries (time-series analysis)**:
   **RULE #3: For "trend", "over time", "growing", "declining", "pattern", "காலப்போக்கில்" - MUST use tables with ACTUAL Date column**
   - TREND analysis REQUIRES a table with a Date/DateTime column containing temporal data
   - Tables like SKU_Performance, Category_Summary do NOT have Date columns - NEVER use for trends
   - Tables like Daily_Sales_Transactions, Sales_Transactions HAVE Date columns - USE THESE for trends
   - Example: "Is profit stable over time?" → Use table with Date column (Daily_Transactions, NOT SKU_Performance)
   - Example: "Which state has declining trend?" → Use table with Date AND State columns
   - The table MUST have sufficient rows (100+) to show a meaningful trend over time
   - A SKU_ID or Transaction_ID is NOT a date column - don't confuse them!

6. **Other Rules**:
   - For "how many X" questions: Select the table with MOST rows that has X data
   - For "percentage" questions: Need a table with the breakdown dimension
   - For "show all" questions: Need the detailed transaction-level table

7. **Validate Your Choice**:
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

        api_key = (os.getenv("GEMINI_API_KEY") or "").strip()
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in environment")

        genai.configure(api_key=api_key)

        # Create base model without system_instruction (for compatibility with 0.3.x)
        base_model = genai.GenerativeModel(
            model_name="gemini-2.0-flash",
            generation_config={
                "temperature": 0.0,  # Deterministic
                "response_mime_type": "application/json",
                "max_output_tokens": 500,
            },
        )

        # Wrap with our compatible model that handles system prompts
        _selector_model = CompatibleGenerativeModel(base_model, TABLE_SELECTOR_PROMPT)

        return _selector_model


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

        # Check if this is a partial data or aggregated table
        name_lower = table_name.lower()
        is_partial = any(x in name_lower for x in ['top_', 'top20', 'top10'])
        is_aggregated = any(x in name_lower for x in ['summary', 'quarterly', 'monthly', 'yearly', 'performance', 'overview'])
        is_transaction = any(x in name_lower for x in ['transaction', 'daily', 'detail', 'raw', 'order', 'sale'])

        # Add appropriate note
        if is_partial:
            note = " [PARTIAL DATA - Top N only, NOT for totals]"
        elif is_aggregated:
            note = " [AGGREGATED/SUMMARY - Pre-computed, NOT for raw totals]"
        elif is_transaction and row_count > 100:
            note = " [TRANSACTION-LEVEL - Use for totals/counts]"
        else:
            note = ""

        lines.append(f"## {table_name}{note}")
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

    # Fallback: use semantic similarity scoring based on question keywords
    if profiles:
        # Try to find best table using keyword matching
        best_table, best_score = _semantic_fallback_selection(question, profiles, verbose)
        if best_table:
            return (best_table, max(0.4, min(0.6, best_score / 100)), f"Semantic fallback: keyword match")

        # Last resort: return table with most rows
        sorted_tables = sorted(
            profiles.items(),
            key=lambda x: x[1].get('row_count', 0),
            reverse=True
        )
        if verbose:
            print(f"⚠️  Fallback: using largest table {sorted_tables[0][0]}")
        return (sorted_tables[0][0], 0.3, "Fallback: largest table")

    return (None, 0.0, "No tables available")


def _semantic_fallback_selection(
    question: str,
    profiles: Dict[str, Dict],
    verbose: bool = True
) -> Tuple[Optional[str], int]:
    """
    Semantic similarity fallback when LLM fails.
    Uses keyword matching between question and table metadata.

    Returns: (table_name, score) or (None, 0)
    """
    import re

    question_lower = question.lower()

    # Extract keywords from question (words 3+ chars, not stopwords)
    stopwords = {'the', 'what', 'which', 'how', 'many', 'much', 'for', 'are', 'has', 'have',
                 'does', 'did', 'was', 'were', 'been', 'being', 'show', 'tell', 'give', 'can',
                 'could', 'would', 'should', 'will', 'from', 'into', 'with', 'about', 'above',
                 'below', 'between', 'during', 'before', 'after', 'and', 'but', 'not', 'all'}

    question_words = set(
        word for word in re.findall(r'\b[a-z]{3,}\b', question_lower)
        if word not in stopwords
    )

    # Check for time-related keywords (important for table selection)
    time_keywords = {'trend', 'over', 'time', 'growing', 'declining', 'pattern', 'month',
                     'year', 'week', 'daily', 'monthly', 'yearly', 'history', 'historical'}
    needs_date_column = bool(question_words & time_keywords)

    # Score each table
    table_scores = []

    for table_name, profile in profiles.items():
        score = 0
        table_lower = table_name.lower().replace('_', ' ')

        # 1. Table name keyword matches (+30 per match)
        table_words = set(table_lower.split())
        name_matches = question_words & table_words
        score += len(name_matches) * 30

        # 2. Column name matches (+15 per match)
        columns = profile.get('columns', {})
        column_names_lower = [col.lower() for col in columns.keys()]
        for q_word in question_words:
            for col_name in column_names_lower:
                if q_word in col_name or col_name in q_word:
                    score += 15
                    break

        # 3. Check for date column if needed (+40 bonus)
        if needs_date_column:
            has_date_col = any(
                info.get('role') == 'date' or
                any(d in col.lower() for d in ['date', 'datetime', 'timestamp'])
                for col, info in columns.items()
            )
            if has_date_col:
                score += 40
            else:
                score -= 20  # Penalty for no date column when time analysis needed

        # 4. Row count bonus for aggregate questions
        row_count = profile.get('row_count', 0)
        aggregate_keywords = {'total', 'sum', 'count', 'all', 'average', 'mean'}
        if question_words & aggregate_keywords:
            if row_count >= 1000:
                score += 25  # Prefer larger tables for totals
            elif row_count < 50:
                score -= 15  # Penalty for small tables on aggregate queries

        # 5. Sample value matches (+20 per match)
        for col, info in columns.items():
            unique_values = info.get('unique_values', [])
            for val in unique_values[:10]:  # Check first 10 values
                val_lower = str(val).lower()
                if val_lower in question_lower:
                    score += 20
                    break

        if score > 0:
            table_scores.append((table_name, score))

    if not table_scores:
        return (None, 0)

    # Sort by score descending
    table_scores.sort(key=lambda x: x[1], reverse=True)

    if verbose:
        print(f"📊 Semantic fallback scores:")
        for t, s in table_scores[:3]:
            print(f"   • {t}: {s}")

    return table_scores[0]
