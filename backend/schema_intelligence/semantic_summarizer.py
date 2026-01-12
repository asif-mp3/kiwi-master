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


