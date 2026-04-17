"""Query utility functions - metric extraction, result values, JSON sanitization."""
import re
import math
import numpy as np
import pandas as pd
from typing import Dict, Any, Optional, List

from utils.logger import get_logger

logger = get_logger("query_utils")

def _extract_metric_name_from_result(previous_turn) -> str:
    """
    Extract human-readable metric name from previous query turn.
    Works with ANY dataset by examining result columns and query plan.
    """
    if not previous_turn:
        return "value"

    # Priority 1: Check query plan for aggregation column
    query_plan = getattr(previous_turn, 'query_plan', None) or {}
    agg_col = query_plan.get('aggregation_column') or query_plan.get('metrics', [None])[0] if query_plan.get('metrics') else None
    if agg_col:
        return _humanize_metric(agg_col)

    # Priority 2: Check result_data for value columns
    result_data = getattr(previous_turn, 'result_data', None) or []
    if result_data and isinstance(result_data, list) and len(result_data) > 0:
        first_row = result_data[0] if isinstance(result_data[0], dict) else {}
        for col in first_row.keys():
            col_lower = col.lower()
            # Skip internal/identifier columns
            if col_lower in ('name', 'id', 'category', 'date', 'month', 'year', 'row_count'):
                continue
            # Likely a value column
            if any(kw in col_lower for kw in ['value', 'amount', 'total', 'count', 'sum', 'avg', 'revenue', 'sales', 'profit', 'quantity']):
                return _humanize_metric(col)
            # First numeric-looking column
            if isinstance(first_row.get(col), (int, float)):
                return _humanize_metric(col)

    # Priority 3: Table name as context
    table_used = getattr(previous_turn, 'table_used', '')
    if table_used:
        # Extract meaningful part
        clean = table_used.replace('Dataset_', '').replace('_', ' ')
        return f"{clean} value"

    return "value"


def _humanize_metric(name: str) -> str:
    """Convert column/metric name to human-readable format."""
    if not name:
        return "value"
    # Remove common prefixes/suffixes and clean up
    clean = name.replace('_', ' ').replace('-', ' ')
    # Capitalize each word
    return ' '.join(word.capitalize() for word in clean.split()).lower()


def _resolve_top_references(question: str, previous_turn) -> str:
    """
    Resolve "top X" references in question using previous query's result_values.

    Examples:
    - "top category" -> "Sarees" (if Sarees was top in previous rank query)
    - "best performing state" -> "West Bengal" (if WB was top)
    - "highest selling product" -> "Product ABC" (if ABC was top)

    This prevents the LLM from misinterpreting what "top" refers to.
    """
    if not previous_turn:
        return question

    result_values = getattr(previous_turn, 'result_values', {}) or {}
    if not result_values:
        return question

    # Patterns for "top X" references
    top_patterns = [
        # (pattern, dimension_keywords)
        (r'\b(top|best|highest|leading|first)\s+(category|categories)', ['category', 'product_category']),
        (r'\b(top|best|highest|leading|first)\s+(product|item|products|items)', ['product', 'item', 'product_name']),
        (r'\b(top|best|highest|leading|first)\s+(state|states)', ['state', 'state_name']),
        (r'\b(top|best|highest|leading|first)\s+(branch|branches|store|stores)', ['branch', 'store', 'branch_name']),
        (r'\b(top|best|highest|leading|first)\s+(region|regions|area|areas)', ['region', 'area']),
        (r'\b(top|best|highest|leading|first)\s+(employee|employees|person|salesperson)', ['employee', 'salesperson', 'employee_name']),
        (r'\b(top|best|highest|leading|first)\s+(seller|sellers)', ['category', 'product', 'item']),
        (r'\b(top|best|highest|leading|first)\s+(performing|one)', ['category', 'product', 'state', 'branch', 'employee']),
    ]

    for pattern, dimension_keys in top_patterns:
        # Use IGNORECASE flag so match indices work on original question
        match = re.search(pattern, question, re.IGNORECASE)
        if match:
            # Find the matching dimension in result_values
            for dim_key in dimension_keys:
                for col_name, col_value in result_values.items():
                    if dim_key in col_name.lower():
                        # Replace the "top X" reference with actual value
                        matched_text = match.group(0)
                        if col_value and isinstance(col_value, str):
                            # Replace pattern with actual value in original question
                            new_question = question[:match.start()] + col_value + question[match.end():]
                            logger.debug("Top reference resolved: '%s' -> '%s'", matched_text, col_value)
                            return new_question

    return question


def _extract_result_values(result, plan: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract key result values from a query result for pronoun resolution in follow-ups.

    For extrema_lookup/rank queries, extracts the "winning" value so "that state",
    "that branch", etc. can be resolved in follow-up questions.

    Example:
    - Query: "Which state has highest revenue?"
    - Result: [{"State": "West Bengal", "Revenue": 1780000}]
    - Extracted: {"State": "West Bengal", "Revenue": 1780000}

    Next query: "In that state, which branch..."
    -> "that state" resolves to "West Bengal"
    """
    if result is None or not hasattr(result, '__len__') or len(result) == 0:
        return {}

    query_type = plan.get('query_type', '')
    result_values = {}

    try:
        # For extrema_lookup or rank with limit 1, extract the top result
        if query_type in ['extrema_lookup', 'rank', 'filter', 'lookup']:
            if hasattr(result, 'iloc'):
                first_row = result.iloc[0]
            elif hasattr(result, '__getitem__'):
                first_row = result[0] if isinstance(result, list) else result
            else:
                return {}

            # Extract dimension columns (likely what user will reference)
            # Priority: State, Branch, Area, Category, then other dimensions
            priority_patterns = [
                'state', 'branch', 'area', 'region', 'location', 'city',
                'category', 'product', 'item', 'name', 'department'
            ]

            if hasattr(first_row, 'items'):
                # Dict-like row
                for col, val in first_row.items():
                    col_lower = str(col).lower()
                    # Include dimension columns
                    for pattern in priority_patterns:
                        if pattern in col_lower:
                            result_values[col] = val
                            break
                    # Also include the metric column (for context)
                    if any(m in col_lower for m in ['revenue', 'sales', 'profit', 'total', 'amount', 'value']):
                        result_values[col] = val
            elif hasattr(first_row, 'index'):
                # Pandas Series
                for col in first_row.index:
                    col_lower = str(col).lower()
                    for pattern in priority_patterns:
                        if pattern in col_lower:
                            result_values[col] = first_row[col]
                            break
                    if any(m in col_lower for m in ['revenue', 'sales', 'profit', 'total', 'amount', 'value']):
                        result_values[col] = first_row[col]

    except Exception as e:
        logger.warning("Could not extract result values: %s", e)

    return result_values


def _sanitize_for_json(data):
    """
    Convert numpy/pandas types to native Python types for JSON serialization.
    Pydantic/FastAPI can't serialize numpy.float64, numpy.int64, pandas.Timestamp, etc.
    Also handles NaN/Inf which aren't valid JSON.
    """
    if data is None:
        return None
    if isinstance(data, dict):
        return {k: _sanitize_for_json(v) for k, v in data.items()}
    if isinstance(data, list):
        return [_sanitize_for_json(item) for item in data]
    # Handle numpy integer types
    if isinstance(data, (np.integer,)):
        return int(data)
    # Handle numpy float types (check for NaN/Inf)
    if isinstance(data, (np.floating,)):
        val = float(data)
        if math.isnan(val) or math.isinf(val):
            return None
        return val
    # Handle native float NaN/Inf
    if isinstance(data, float):
        if math.isnan(data) or math.isinf(data):
            return None
        return data
    if isinstance(data, np.ndarray):
        return _sanitize_for_json(data.tolist())
    if isinstance(data, np.bool_):
        return bool(data)
    # Handle pandas Timestamp
    if hasattr(data, 'isoformat'):
        return data.isoformat()
    # Handle pandas NA/NaT
    if str(type(data).__name__) in ('NAType', 'NaTType') or str(data) in ('NA', 'NaT', '<NA>'):
        return None
    # Generic numpy scalar with .item() method
    if hasattr(data, 'item'):
        return _sanitize_for_json(data.item())
    return data
