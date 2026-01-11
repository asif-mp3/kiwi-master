"""
Semantic Summarizer - Generates natural language descriptions of tables.

This module creates semantic summaries that help the LLM understand:
1. What data each table contains
2. What questions each table can answer
3. Key columns and their purposes

Summaries are generated ONCE during profiling (not during queries) for low latency.
"""

import os
from typing import Dict, List, Any, Optional
from pathlib import Path


def generate_table_summary_rule_based(
    table_name: str,
    profile: Dict[str, Any]
) -> str:
    """
    Generate a semantic summary using rule-based logic (fast, no LLM call).

    This is the PRIMARY method - fast and deterministic.
    Use generate_table_summary_llm() for more nuanced summaries if needed.

    Args:
        table_name: Name of the table
        profile: Table profile from DataProfiler

    Returns:
        str: Natural language summary of the table
    """
    columns = profile.get('columns', {})
    table_type = profile.get('table_type', 'unknown')
    granularity = profile.get('granularity', 'unknown')
    date_range = profile.get('date_range', {})
    row_count = profile.get('row_count', 0)

    # Extract column roles
    metrics = []
    dimensions = []
    identifiers = []
    date_cols = []

    for col_name, col_info in columns.items():
        role = col_info.get('role', '')
        if role == 'metric':
            metrics.append(col_name)
        elif role == 'dimension':
            # Include sample values for dimensions
            sample_values = col_info.get('unique_values', [])[:3]
            if sample_values:
                dimensions.append(f"{col_name} (e.g., {', '.join(str(v) for v in sample_values)})")
            else:
                dimensions.append(col_name)
        elif role == 'identifier':
            identifiers.append(col_name)
        elif role == 'date':
            date_cols.append(col_name)

    # Build "Contains" section
    contains_parts = []

    # Add table type context
    if table_type == 'transactional':
        contains_parts.append("Individual transaction records")
    elif table_type == 'summary':
        contains_parts.append("Aggregated summary data")
    elif table_type == 'category_breakdown':
        contains_parts.append("Data broken down by category")
    elif table_type == 'pivot':
        contains_parts.append("Pivoted time-series data")
    elif table_type == 'item_level':
        contains_parts.append("Product/item-level data")

    # Add dimension info
    if dimensions:
        dim_list = ', '.join(dimensions[:3])
        contains_parts.append(f"with dimensions: {dim_list}")

    # Add metric info
    if metrics:
        metric_list = ', '.join(metrics[:4])
        contains_parts.append(f"metrics: {metric_list}")

    # Add date info
    if date_cols:
        contains_parts.append(f"date column: {date_cols[0]}")
        if date_range.get('month'):
            contains_parts.append(f"covers {date_range['month']}")
        elif date_range.get('min') and date_range.get('max'):
            min_date = date_range['min'][:10] if date_range['min'] else ''
            max_date = date_range['max'][:10] if date_range['max'] else ''
            if min_date and max_date:
                contains_parts.append(f"date range: {min_date} to {max_date}")

    contains = '. '.join(contains_parts) if contains_parts else f"Data table with {row_count} rows"

    # Build "Use for" section based on structure
    use_cases = []

    # Dimension-based use cases
    for col_name, col_info in columns.items():
        if col_info.get('role') == 'dimension':
            col_lower = col_name.lower()
            if any(loc in col_lower for loc in ['area', 'zone', 'region', 'pincode', 'city', 'location', 'branch', 'state']):
                use_cases.append("location/area-based analysis")
            elif any(cat in col_lower for cat in ['category', 'type', 'segment', 'group']):
                use_cases.append("category breakdown")
            elif any(pay in col_lower for pay in ['payment', 'mode', 'method']):
                use_cases.append("payment mode analysis")
            elif any(emp in col_lower for emp in ['department', 'designation', 'team']):
                use_cases.append("department/team analysis")

    # Metric-based use cases
    for metric in metrics[:3]:
        metric_lower = metric.lower()
        if 'sales' in metric_lower or 'revenue' in metric_lower:
            use_cases.append("sales/revenue queries")
        elif 'profit' in metric_lower:
            use_cases.append("profit analysis")
        elif 'order' in metric_lower or 'transaction' in metric_lower:
            use_cases.append("transaction counts")
        elif 'quantity' in metric_lower or 'qty' in metric_lower:
            use_cases.append("quantity metrics")
        elif 'hour' in metric_lower or 'attendance' in metric_lower:
            use_cases.append("attendance/hours tracking")
        elif 'salary' in metric_lower or 'wage' in metric_lower:
            use_cases.append("salary/compensation queries")

    # Time-based use cases
    if granularity == 'daily':
        use_cases.append("daily trends")
    elif granularity == 'monthly':
        use_cases.append("monthly comparisons")
    elif granularity == 'monthly_pivot':
        use_cases.append("month-over-month comparisons")

    # Identifier-based use cases
    if identifiers:
        id_lower = ' '.join(identifiers).lower()
        if 'employee' in id_lower or 'emp' in id_lower or 'staff' in id_lower:
            use_cases.append("individual employee lookup")
        elif 'customer' in id_lower:
            use_cases.append("customer lookup")
        elif 'product' in id_lower or 'item' in id_lower:
            use_cases.append("product/item lookup")

    # Deduplicate and format
    use_cases = list(dict.fromkeys(use_cases))[:5]  # Keep unique, limit to 5
    use_for = ', '.join(use_cases) if use_cases else "general data queries"

    return f"Contains: {contains}. Use for: {use_for}."


def generate_table_summary_llm(
    table_name: str,
    profile: Dict[str, Any],
    use_cache: bool = True
) -> str:
    """
    Generate a semantic summary using LLM (more nuanced but slower).

    This is called ONCE during profiling, not during queries.
    Results are cached in the profile.

    Args:
        table_name: Name of the table
        profile: Table profile from DataProfiler
        use_cache: If True, return cached summary if available

    Returns:
        str: Natural language summary of the table
    """
    # Check cache first
    if use_cache and profile.get('semantic_summary'):
        return profile['semantic_summary']

    # Try LLM-based generation
    try:
        import google.generativeai as genai
        from dotenv import load_dotenv

        load_dotenv()
        api_key = os.getenv("GEMINI_API_KEY")

        if not api_key:
            # Fall back to rule-based
            return generate_table_summary_rule_based(table_name, profile)

        genai.configure(api_key=api_key)

        # Build compact column description
        columns = profile.get('columns', {})
        col_descriptions = []
        for col_name, col_info in list(columns.items())[:15]:  # Limit columns
            role = col_info.get('role', 'unknown')
            sample = col_info.get('unique_values', col_info.get('sample_values', []))[:2]
            sample_str = f" (e.g., {', '.join(str(v) for v in sample)})" if sample else ""
            col_descriptions.append(f"{col_name} [{role}]{sample_str}")

        prompt = f"""Analyze this database table and write a 2-sentence summary.

Table: {table_name}
Type: {profile.get('table_type', 'unknown')}
Rows: {profile.get('row_count', 0)}
Columns: {'; '.join(col_descriptions)}
Date Range: {profile.get('date_range', {})}

Write exactly 2 sentences:
1. "Contains: [what data is stored]"
2. "Use for: [types of questions this answers]"

Be specific about the dimensions (like payment modes, areas, categories) and metrics available.
Output ONLY the 2 sentences, nothing else."""

        model = genai.GenerativeModel(
            model_name="gemini-2.0-flash",  # Fast model for summaries
            generation_config={
                "temperature": 0.1,
                "max_output_tokens": 150,
            }
        )

        response = model.generate_content(prompt)
        summary = response.text.strip()

        # Validate response format
        if "Contains:" in summary and "Use for:" in summary:
            return summary
        else:
            # Fall back to rule-based if LLM response is malformed
            return generate_table_summary_rule_based(table_name, profile)

    except Exception as e:
        print(f"  Warning: LLM summary generation failed for {table_name}: {e}")
        return generate_table_summary_rule_based(table_name, profile)


def build_compact_table_context(profiles: Dict[str, Dict]) -> str:
    """
    Build a compact context of all tables for LLM table selection.

    This is designed to fit many tables in limited context while preserving
    the semantic information needed for accurate table selection.

    Args:
        profiles: Dict of table_name -> profile

    Returns:
        str: Compact table context for LLM prompt
    """
    if not profiles:
        return "No tables available."

    lines = ["## Available Tables\n"]
    lines.append("**IMPORTANT**: Tables named 'Top_*' or '*_Summary' contain PARTIAL data only.")
    lines.append("For COUNT questions ('how many'), prefer tables with complete data (higher row counts).\n")

    # Sort tables: complete data tables first, then partial/summary tables
    complete_tables = []
    partial_tables = []

    for table_name, profile in profiles.items():
        name_lower = table_name.lower()
        is_partial = any(x in name_lower for x in ['top_', 'top20', 'top10', 'summary', 'calculation'])
        if is_partial:
            partial_tables.append((table_name, profile))
        else:
            complete_tables.append((table_name, profile))

    # Add complete data tables first
    if complete_tables:
        lines.append("### Complete Data Tables (use for COUNT questions)")
        for table_name, profile in complete_tables:
            _add_table_entry(lines, table_name, profile)

    # Then add partial/summary tables
    if partial_tables:
        lines.append("\n### Partial/Summary Tables (DO NOT use for COUNT questions)")
        for table_name, profile in partial_tables:
            _add_table_entry(lines, table_name, profile, is_partial=True)

    return "\n".join(lines)


def _add_table_entry(lines: List[str], table_name: str, profile: Dict, is_partial: bool = False):
    """Helper to add a table entry to the context."""
    # Get or generate summary
    summary = profile.get('semantic_summary')
    if not summary:
        summary = generate_table_summary_rule_based(table_name, profile)

    # Get key columns with dimension values
    columns = profile.get('columns', {})
    key_cols = []
    dimension_values = []

    for col_name, col_info in columns.items():
        role = col_info.get('role', '')
        if role in ['metric', 'dimension', 'date']:
            key_cols.append(col_name)

        # Capture dimension values for context
        if role == 'dimension':
            values = col_info.get('unique_values', [])[:3]
            if values:
                dimension_values.append(f"{col_name}: {', '.join(str(v) for v in values)}")

    key_cols = key_cols[:8]  # Limit to 8 key columns

    # Format table entry
    row_count = profile.get('row_count', 0)
    partial_warning = " [PARTIAL DATA - Top N only]" if is_partial else ""
    lines.append(f"**{table_name}** ({row_count} rows){partial_warning}")
    lines.append(f"  {summary}")
    if key_cols:
        lines.append(f"  Key columns: {', '.join(key_cols)}")
    if dimension_values:
        lines.append(f"  Sample dimension values: {'; '.join(dimension_values[:3])}")
    lines.append("")


def get_table_for_question_hint(
    question: str,
    profiles: Dict[str, Dict]
) -> Optional[str]:
    """
    Quick rule-based hint for which table might answer a question.

    This is a FAST first-pass filter, not a replacement for LLM selection.
    Returns the most likely table name or None if uncertain.

    Args:
        question: User's question
        profiles: Dict of table_name -> profile

    Returns:
        Optional[str]: Table name hint or None
    """
    q_lower = question.lower()

    best_match = None
    best_score = 0

    for table_name, profile in profiles.items():
        score = 0
        columns = profile.get('columns', {})

        # Check for dimension matches
        for col_name, col_info in columns.items():
            if col_info.get('role') != 'dimension':
                continue

            col_lower = col_name.lower()

            # Payment mode questions
            if any(kw in q_lower for kw in ['payment', 'upi', 'cash', 'card', 'mode']):
                if 'payment' in col_lower or 'mode' in col_lower:
                    score += 50
                    # Check if values match
                    values = col_info.get('unique_values', [])
                    values_lower = [str(v).lower() for v in values]
                    if any(v in q_lower for v in values_lower):
                        score += 30

            # Location questions
            if any(kw in q_lower for kw in ['area', 'location', 'branch', 'state', 'city', 'zone']):
                if any(loc in col_lower for loc in ['area', 'location', 'branch', 'state', 'city', 'zone']):
                    score += 50

            # Category questions
            if any(kw in q_lower for kw in ['category', 'type', 'product']):
                if 'category' in col_lower or 'type' in col_lower:
                    score += 40

        # Check table name relevance
        table_lower = table_name.lower()
        if any(kw in table_lower for kw in q_lower.split() if len(kw) > 3):
            score += 20

        if score > best_score:
            best_score = score
            best_match = table_name

    # Only return if reasonably confident
    return best_match if best_score >= 40 else None
