"""
Advanced Query Executor for complex query types.

Handles:
- comparison: Compare two periods/values and calculate difference/change
- percentage: Calculate percentage contribution
- trend: Analyze trends over time (up/down/stable)
"""

from typing import Dict, Any, List, Optional, Tuple
import duckdb
from datetime import datetime
import statistics
import re


def execute_advanced_query(
    plan: Dict[str, Any],
    conn: duckdb.DuckDBPyConnection
) -> Dict[str, Any]:
    """
    Execute advanced query types that require multi-step processing.

    Args:
        plan: Query plan with query_type in ['comparison', 'percentage', 'trend']
        conn: DuckDB connection

    Returns:
        Dict with 'data', 'calculation_result', and 'analysis' keys
    """
    query_type = plan.get("query_type")

    if query_type == "comparison":
        return execute_comparison(plan, conn)
    elif query_type == "percentage":
        return execute_percentage(plan, conn)
    elif query_type == "trend":
        return execute_trend(plan, conn)
    else:
        raise ValueError(f"Unknown advanced query type: {query_type}")


def execute_comparison(
    plan: Dict[str, Any],
    conn: duckdb.DuckDBPyConnection
) -> Dict[str, Any]:
    """
    Execute comparison query - compare two periods/values.

    Example question: "How did August sales compare to December?"
    """
    comparison = plan.get("comparison", {})
    period_a = comparison.get("period_a", {})
    period_b = comparison.get("period_b", {})
    compare_type = comparison.get("compare_type", "difference")

    # Execute query for period A
    value_a = _get_aggregated_value(
        conn,
        period_a.get("table", plan.get("table")),
        period_a.get("column"),
        period_a.get("filters", []),
        period_a.get("aggregation", "SUM")
    )

    # Execute query for period B
    value_b = _get_aggregated_value(
        conn,
        period_b.get("table", plan.get("table")),
        period_b.get("column"),
        period_b.get("filters", []),
        period_b.get("aggregation", "SUM")
    )

    # Calculate comparison
    if value_a is None or value_b is None:
        # Provide specific error about which data is missing
        missing_info = []
        if value_a is None:
            missing_info.append(f"{period_a.get('label', 'Period A')} ({period_a.get('column', 'unknown column')})")
        if value_b is None:
            missing_info.append(f"{period_b.get('label', 'Period B')} ({period_b.get('column', 'unknown column')})")

        error_msg = f"Couldn't find data for: {', '.join(missing_info)}. The column might not exist or have NULL values."
        print(f"[Comparison] {error_msg}")

        return {
            "data": [],
            "calculation_result": None,
            "analysis": {
                "error": error_msg,
                "period_a_value": value_a,
                "period_a_column": period_a.get('column'),
                "period_b_value": value_b,
                "period_b_column": period_b.get('column')
            }
        }

    result = _calculate_comparison(value_a, value_b, compare_type)

    # Determine direction
    if value_b > value_a:
        direction = "increased"
        direction_emoji = "📈"
    elif value_b < value_a:
        direction = "decreased"
        direction_emoji = "📉"
    else:
        direction = "unchanged"
        direction_emoji = "➡️"

    return {
        "data": [
            {period_a.get("label", "Period A"): value_a},
            {period_b.get("label", "Period B"): value_b}
        ],
        "calculation_result": result,
        "analysis": {
            "period_a_label": period_a.get("label", "Period A"),
            "period_a_value": value_a,
            "period_b_label": period_b.get("label", "Period B"),
            "period_b_value": value_b,
            "difference": value_b - value_a,
            "percentage_change": ((value_b - value_a) / value_a * 100) if value_a != 0 else None,
            "direction": direction,
            "direction_emoji": direction_emoji,
            "compare_type": compare_type
        }
    }


def execute_percentage(
    plan: Dict[str, Any],
    conn: duckdb.DuckDBPyConnection
) -> Dict[str, Any]:
    """
    Execute percentage query - calculate percentage contribution.

    Example question: "What percentage of sales comes from top 10 items?"
    """
    percentage = plan.get("percentage", {})
    numerator = percentage.get("numerator", {})
    denominator = percentage.get("denominator", {})
    table = plan.get("table")

    # Get numerator value (e.g., top 10 items sales)
    numerator_value = _get_aggregated_value(
        conn,
        table,
        numerator.get("column"),
        numerator.get("filters", []),
        numerator.get("aggregation", "SUM"),
        order_by=numerator.get("order_by"),
        limit=numerator.get("limit")
    )

    # Get denominator value (e.g., total sales)
    denominator_value = _get_aggregated_value(
        conn,
        table,
        denominator.get("column"),
        denominator.get("filters", []),
        denominator.get("aggregation", "SUM")
    )

    if numerator_value is None or denominator_value is None or denominator_value == 0:
        return {
            "data": [],
            "calculation_result": None,
            "analysis": {
                "error": "Oops! Couldn't calculate the percentage - missing data or the total is zero. Try different criteria?",
                "numerator": numerator_value,
                "denominator": denominator_value
            }
        }

    percentage_value = (numerator_value / denominator_value) * 100

    return {
        "data": [
            {"numerator": numerator_value, "denominator": denominator_value}
        ],
        "calculation_result": percentage_value,
        "analysis": {
            "numerator_value": numerator_value,
            "denominator_value": denominator_value,
            "percentage": round(percentage_value, 2),
            "percentage_formatted": f"{percentage_value:.1f}%"
        }
    }


def execute_trend(
    plan: Dict[str, Any],
    conn: duckdb.DuckDBPyConnection
) -> Dict[str, Any]:
    """
    Execute trend query - analyze patterns over time.

    Example question: "How are daily sales trending this month?"
    Handles both date columns and text-based quarter columns (e.g., "Q3 2025").
    Supports filters for specific time periods or locations.
    Supports group_by to analyze trends separately for each group (e.g., by State).
    """
    trend = plan.get("trend", {})
    table = plan.get("table")
    date_column = trend.get("date_column")
    value_column = trend.get("value_column")
    aggregation = trend.get("aggregation", "SUM")
    analysis_type = trend.get("analysis_type", "direction")
    filters = plan.get("filters", [])
    group_by = trend.get("group_by")  # Optional: dimension to group trend analysis by

    # VALIDATION: Check if date_column looks like an actual date column (not an ID column)
    if date_column:
        date_col_lower = date_column.lower()
        # ID columns should NOT be used for trend analysis
        invalid_patterns = ['_id', 'id_', 'sku_', 'transaction_', 'order_id', 'item_id', 'product_id', 'customer_id']
        if any(pattern in date_col_lower for pattern in invalid_patterns):
            print(f"  ⚠️ WARNING: '{date_column}' looks like an ID column, not a date column!")
            return {
                "data": [],
                "calculation_result": None,
                "analysis": {
                    "error": f"The column '{date_column}' appears to be an ID column, not a date column. Trend analysis requires a Date/DateTime column. Please try a different query or check your data.",
                    "suggestion": "Try asking about sales trend using a table with actual date data."
                }
            }

    # If group_by is specified, delegate to grouped trend analysis
    if group_by:
        return execute_grouped_trend(plan, conn)

    # Get time series data
    quoted_table = f'"{table}"' if ' ' in table or '-' in table or table[0].isdigit() else table
    quoted_date = f'"{date_column}"' if date_column and (' ' in date_column or '-' in date_column) else date_column
    quoted_value = f'"{value_column}"' if value_column and (' ' in value_column or '-' in value_column) else value_column

    # Build filter clause from plan filters
    filter_conditions = [f"{quoted_date} IS NOT NULL", f"{quoted_value} IS NOT NULL"]
    for f in filters:
        col = f.get("column", "")
        op = f.get("operator", "=")
        val = f.get("value")

        # Quote column name if needed
        quoted_col = f'"{col}"' if col and (' ' in col or '-' in col) else col

        if val is not None:
            if isinstance(val, str):
                filter_conditions.append(f"{quoted_col} {op} '{val}'")
            else:
                filter_conditions.append(f"{quoted_col} {op} {val}")

    where_clause = " AND ".join(filter_conditions)

    if filters:
        print(f"  📋 Applying {len(filters)} filter(s) to trend query")

    # Check if date_column is a text-based quarter column (e.g., "Q3 2025")
    is_quarter = _is_quarter_column(conn, table, date_column)

    if is_quarter:
        # Sort quarters chronologically: extract year and quarter number
        # "Q3 2025" -> year=2025, quarter=3
        sql = f"""
            SELECT {quoted_date} as date, {aggregation}({quoted_value}) as value
            FROM {quoted_table}
            WHERE {where_clause}
            GROUP BY {quoted_date}
            ORDER BY
                CAST(REGEXP_EXTRACT({quoted_date}, '(\\d{{4}})', 1) AS INTEGER),
                CAST(REGEXP_EXTRACT({quoted_date}, 'Q(\\d)', 1) AS INTEGER)
        """
        print(f"  📅 Quarter column detected - using chronological sort")
    else:
        sql = f"""
            SELECT {quoted_date} as date, {aggregation}({quoted_value}) as value
            FROM {quoted_table}
            WHERE {where_clause}
            GROUP BY {quoted_date}
            ORDER BY {quoted_date}
        """

    try:
        result = conn.execute(sql).fetchall()
        if not result:
            return {
                "data": [],
                "calculation_result": None,
                "analysis": {"error": "Hmm, no data found for the trend! Try a different date range or filter?"}
            }

        # Filter both arrays together to ensure alignment (avoid index mismatch if NULLs exist)
        filtered_data = [(row[0], row[1]) for row in result if row[1] is not None]
        dates = [r[0] for r in filtered_data]
        values = [r[1] for r in filtered_data]

        if len(values) < 2:
            return {
                "data": [{"date": str(d), "value": v} for d, v in result],
                "calculation_result": None,
                "analysis": {"error": "Aww, not quite enough data points to show a trend! Need at least 2 periods."}
            }

        # Check for constant values (no variance)
        unique_values = set(values)
        if len(unique_values) == 1:
            constant_value = values[0]
            first_period = str(dates[0])
            last_period = str(dates[-1])
            time_unit = _detect_time_unit_from_column(date_column)
            return {
                "data": [{"date": str(d), "value": v} for d, v in result],
                "calculation_result": 0,
                "analysis": {
                    "direction": "stable",
                    "direction_emoji": "➡️",
                    "confidence": "high",
                    "start_value": constant_value,
                    "end_value": constant_value,
                    "min_value": constant_value,
                    "max_value": constant_value,
                    "avg_value": constant_value,
                    "data_points": len(values),
                    "total_change": 0,
                    "percentage_change": 0,
                    "is_constant": True,
                    "message": f"Value has been constant at {constant_value} from {first_period} to {last_period}",
                    # Additional fields for projection support
                    "slope": 0,
                    "normalized_slope": 0,
                    "values": values[-12:],
                    "time_unit": time_unit
                }
            }

        # Analyze trend
        trend_analysis = _analyze_trend(values)

        # Detect time unit from column name for projection support
        time_unit = _detect_time_unit_from_column(date_column)

        return {
            "data": [{"date": str(d), "value": v} for d, v in result],
            "calculation_result": trend_analysis["slope"],
            "analysis": {
                "direction": trend_analysis["direction"],
                "direction_emoji": trend_analysis["emoji"],
                "confidence": trend_analysis["confidence"],
                "start_value": values[0],
                "end_value": values[-1],
                "min_value": min(values),
                "max_value": max(values),
                "avg_value": statistics.mean(values),
                "data_points": len(values),
                "total_change": values[-1] - values[0],
                "percentage_change": ((values[-1] - values[0]) / values[0] * 100) if values[0] != 0 else None,
                # Additional fields for projection support
                "slope": trend_analysis["slope"],
                "normalized_slope": trend_analysis.get("normalized_slope", 0),
                "values": values[-12:],  # Store last 12 data points for projection calculations
                "time_unit": time_unit
            }
        }

    except Exception as e:
        return {
            "data": [],
            "calculation_result": None,
            "analysis": {"error": f"Oops! Something went wrong with the trend analysis. ({str(e)})"}
        }


def _is_quarter_column(
    conn: duckdb.DuckDBPyConnection,
    table: str,
    column: str
) -> bool:
    """
    Check if column contains quarter-formatted text like 'Q3 2025'.
    Returns True if values match pattern Q[1-4] YYYY.
    """
    if not table or not column:
        return False

    try:
        quoted_table = f'"{table}"' if ' ' in table or '-' in table or (table and table[0].isdigit()) else table
        quoted_col = f'"{column}"' if ' ' in column or '-' in column else column

        sql = f"SELECT DISTINCT {quoted_col} FROM {quoted_table} WHERE {quoted_col} IS NOT NULL LIMIT 10"
        result = conn.execute(sql).fetchall()

        if not result:
            return False

        # Check if values match quarter pattern like "Q1 2025", "Q2 2024", etc.
        pattern = r'^Q[1-4]\s+\d{4}$'
        matches = 0
        for row in result:
            if row[0] and re.match(pattern, str(row[0]).strip()):
                matches += 1

        # If most values match the pattern, it's a quarter column
        return matches >= len(result) * 0.8  # 80% threshold

    except Exception as e:
        print(f"  ⚠️ Error checking quarter column: {e}")
        return False


def _get_aggregated_value(
    conn: duckdb.DuckDBPyConnection,
    table: str,
    column: str,
    filters: List[Dict],
    aggregation: str = "SUM",
    order_by: Optional[List] = None,
    limit: Optional[int] = None
) -> Optional[float]:
    """Execute a simple aggregation query and return the value."""
    if not table or not column:
        return None

    # Quote identifiers
    quoted_table = f'"{table}"' if ' ' in table or '-' in table or (table and table[0].isdigit()) else table
    quoted_column = f'"{column}"' if ' ' in column or '-' in column else column

    # Build WHERE clause with proper AND/OR logic
    # Group filters by column - same column filters use OR, different columns use AND
    filters_by_column = {}
    for f in filters:
        col = f.get("column", "")
        if col not in filters_by_column:
            filters_by_column[col] = []
        filters_by_column[col].append(f)

    # Build conditions with proper AND/OR logic
    conditions = []
    for col, col_filters in filters_by_column.items():
        quoted_col = f'"{col}"' if ' ' in col or '-' in col else col

        if len(col_filters) > 1:
            # Multiple filters for same column
            # Use AND for range operators (>=, <=, >, <) - needed for date ranges
            # Use OR for equality/LIKE operators - needed for "Category = A OR Category = B"
            parts = []
            operators = [f.get("operator", "=") for f in col_filters]
            range_operators = {'>=', '<=', '>', '<'}

            for f in col_filters:
                op = f.get("operator", "=")
                val = f.get("value")
                if isinstance(val, str):
                    parts.append(f"{quoted_col} {op} '{val}'")
                else:
                    parts.append(f"{quoted_col} {op} {val}")

            # If ALL operators are range operators, use AND (for date ranges like >= and <)
            # Otherwise use OR (for value matching like Category = A OR Category = B)
            if all(op in range_operators for op in operators):
                conditions.append(f"({' AND '.join(parts)})")
            else:
                conditions.append(f"({' OR '.join(parts)})")
        else:
            # Single filter for this column
            f = col_filters[0]
            op = f.get("operator", "=")
            val = f.get("value")
            if isinstance(val, str):
                conditions.append(f"{quoted_col} {op} '{val}'")
            else:
                conditions.append(f"{quoted_col} {op} {val}")

    where_clause = " AND ".join(conditions) if conditions else "1=1"

    # Build query
    if limit and order_by:
        # Subquery for top N
        order_col = order_by[0][0] if order_by else column
        order_dir = order_by[0][1] if order_by and len(order_by[0]) > 1 else "DESC"
        quoted_order = f'"{order_col}"' if ' ' in order_col or '-' in order_col else order_col

        sql = f"""
            SELECT {aggregation}({quoted_column}) as result
            FROM (
                SELECT {quoted_column}
                FROM {quoted_table}
                WHERE {where_clause}
                ORDER BY {quoted_order} {order_dir}
                LIMIT {limit}
            ) sub
        """
    else:
        sql = f"""
            SELECT {aggregation}({quoted_column}) as result
            FROM {quoted_table}
            WHERE {where_clause}
        """

    try:
        result = conn.execute(sql).fetchone()
        return result[0] if result else None
    except Exception as e:
        # Log detailed error for debugging - likely column doesn't exist
        print(f"[AdvancedExecutor] Error in aggregation for column '{column}' in table '{table}': {e}")
        print(f"[AdvancedExecutor] SQL attempted: {sql[:200]}...")
        return None


def _calculate_comparison(value_a: float, value_b: float, compare_type: str) -> float:
    """Calculate comparison result based on type."""
    if compare_type == "difference":
        return value_b - value_a
    elif compare_type == "percentage_change":
        if value_a == 0:
            return None
        return ((value_b - value_a) / value_a) * 100
    elif compare_type == "ratio":
        if value_a == 0:
            return None
        return value_b / value_a
    else:
        return value_b - value_a


def _detect_time_unit_from_column(column_name: str) -> str:
    """
    Detect time unit from column name for projection support.

    Args:
        column_name: Name of the date/time column

    Returns:
        Time unit string: "month", "week", "day", "quarter", "year"
    """
    if not column_name:
        return "month"

    col_lower = column_name.lower()

    if 'month' in col_lower:
        return 'month'
    elif 'week' in col_lower:
        return 'week'
    elif 'day' in col_lower or 'date' in col_lower:
        return 'day'
    elif 'quarter' in col_lower or col_lower.startswith('q'):
        return 'quarter'
    elif 'year' in col_lower:
        return 'year'

    # Default to month as most common in business data
    return 'month'


def _analyze_trend(values: List[float]) -> Dict[str, Any]:
    """
    Analyze trend direction from a list of values.
    Uses simple linear regression slope.
    """
    n = len(values)
    if n < 2:
        return {"direction": "unknown", "emoji": "❓", "slope": 0, "confidence": 0}

    # Calculate simple linear regression
    x_mean = (n - 1) / 2
    y_mean = statistics.mean(values)

    numerator = sum((i - x_mean) * (values[i] - y_mean) for i in range(n))
    denominator = sum((i - x_mean) ** 2 for i in range(n))

    slope = numerator / denominator if denominator != 0 else 0

    # Normalize slope by mean to get percentage change per period
    normalized_slope = (slope / y_mean * 100) if y_mean != 0 else 0

    # Determine direction and confidence
    if abs(normalized_slope) < 1:  # Less than 1% change per period
        direction = "stable"
        emoji = "➡️"
        confidence = "high" if abs(normalized_slope) < 0.5 else "medium"
    elif normalized_slope > 0:
        direction = "increasing"
        emoji = "📈"
        confidence = "high" if normalized_slope > 5 else "medium" if normalized_slope > 2 else "low"
    else:
        direction = "decreasing"
        emoji = "📉"
        confidence = "high" if normalized_slope < -5 else "medium" if normalized_slope < -2 else "low"

    return {
        "direction": direction,
        "emoji": emoji,
        "slope": round(slope, 2),
        "normalized_slope": round(normalized_slope, 2),
        "confidence": confidence
    }


def execute_grouped_trend(
    plan: Dict[str, Any],
    conn: duckdb.DuckDBPyConnection
) -> Dict[str, Any]:
    """
    Execute grouped trend query - analyze trends separately for each group.

    Example question: "Which state has declining sales trend?"
    Returns trend analysis for each group with direction (increasing/decreasing/stable).
    """
    trend = plan.get("trend", {})
    table = plan.get("table")
    date_column = trend.get("date_column")
    value_column = trend.get("value_column")
    aggregation = trend.get("aggregation", "SUM")
    group_by = trend.get("group_by")
    filters = plan.get("filters", [])

    if not group_by:
        return {"data": [], "analysis": {"error": "group_by is required for grouped trend analysis"}}

    # VALIDATION: Check if date_column looks like an actual date column (not an ID column)
    if date_column:
        date_col_lower = date_column.lower()
        invalid_patterns = ['_id', 'id_', 'sku_', 'transaction_', 'order_id', 'item_id', 'product_id', 'customer_id']
        if any(pattern in date_col_lower for pattern in invalid_patterns):
            print(f"  ⚠️ WARNING: '{date_column}' looks like an ID column, not a date column!")
            return {
                "data": [],
                "calculation_result": None,
                "analysis": {
                    "error": f"The column '{date_column}' appears to be an ID column, not a date column. Trend analysis requires a Date/DateTime column.",
                    "suggestion": "Try asking about trends using a table with actual date data."
                }
            }

    # Quote identifiers
    quoted_table = f'"{table}"' if table and (' ' in table or '-' in table or table[0].isdigit()) else table
    quoted_date = f'"{date_column}"' if date_column and (' ' in date_column or '-' in date_column) else date_column
    quoted_value = f'"{value_column}"' if value_column and (' ' in value_column or '-' in value_column) else value_column
    quoted_group = f'"{group_by}"' if group_by and (' ' in group_by or '-' in group_by) else group_by

    # Build filter clause
    filter_conditions = [f"{quoted_date} IS NOT NULL", f"{quoted_value} IS NOT NULL", f"{quoted_group} IS NOT NULL"]
    for f in filters:
        col = f.get("column", "")
        op = f.get("operator", "=")
        val = f.get("value")
        quoted_col = f'"{col}"' if col and (' ' in col or '-' in col) else col
        if val is not None:
            if isinstance(val, str):
                filter_conditions.append(f"{quoted_col} {op} '{val}'")
            else:
                filter_conditions.append(f"{quoted_col} {op} {val}")

    where_clause = " AND ".join(filter_conditions)

    # First, get all distinct groups
    groups_sql = f"""
        SELECT DISTINCT {quoted_group} as group_name
        FROM {quoted_table}
        WHERE {quoted_group} IS NOT NULL
        ORDER BY {quoted_group}
    """

    try:
        groups_result = conn.execute(groups_sql).fetchall()
        if not groups_result:
            return {"data": [], "analysis": {"error": f"No groups found for {group_by}"}}

        groups = [row[0] for row in groups_result if row[0]]
        print(f"  📊 Analyzing trend for {len(groups)} {group_by} groups")

        # Analyze trend for each group
        group_trends = []
        increasing_groups = []
        decreasing_groups = []
        stable_groups = []

        for group_name in groups:
            # Get time series data for this group
            # Use TRY_CAST to handle VARCHAR date columns
            sql = f"""
                SELECT TRY_CAST({quoted_date} AS DATE) as date, {aggregation}({quoted_value}) as value
                FROM {quoted_table}
                WHERE {where_clause} AND {quoted_group} = '{_sanitize_string_value(group_name)}'
                GROUP BY TRY_CAST({quoted_date} AS DATE)
                ORDER BY TRY_CAST({quoted_date} AS DATE)
            """

            result = conn.execute(sql).fetchall()
            if not result or len(result) < 2:
                # Not enough data points for this group
                continue

            # Filter out None values
            filtered_data = [(row[0], row[1]) for row in result if row[0] is not None and row[1] is not None]
            if len(filtered_data) < 2:
                continue

            values = [r[1] for r in filtered_data]

            # Analyze trend for this group
            trend_analysis = _analyze_trend(values)

            group_info = {
                "group": group_name,
                "direction": trend_analysis["direction"],
                "direction_emoji": trend_analysis["emoji"],
                "slope": trend_analysis["slope"],
                "normalized_slope": trend_analysis["normalized_slope"],
                "confidence": trend_analysis["confidence"],
                "start_value": values[0],
                "end_value": values[-1],
                "data_points": len(values),
                "percentage_change": ((values[-1] - values[0]) / values[0] * 100) if values[0] != 0 else 0
            }
            group_trends.append(group_info)

            # Categorize by direction
            if trend_analysis["direction"] == "increasing":
                increasing_groups.append(group_name)
            elif trend_analysis["direction"] == "decreasing":
                decreasing_groups.append(group_name)
            else:
                stable_groups.append(group_name)

        if not group_trends:
            return {"data": [], "analysis": {"error": f"Not enough data to analyze trends by {group_by}"}}

        # Sort groups by slope (most declining first for "which is declining" questions)
        group_trends.sort(key=lambda x: x["normalized_slope"])

        return {
            "data": group_trends,
            "calculation_result": len(decreasing_groups),
            "analysis": {
                "group_by": group_by,
                "total_groups": len(groups),
                "analyzed_groups": len(group_trends),
                "increasing_groups": increasing_groups,
                "decreasing_groups": decreasing_groups,
                "stable_groups": stable_groups,
                "increasing_count": len(increasing_groups),
                "decreasing_count": len(decreasing_groups),
                "stable_count": len(stable_groups),
                "most_declining": group_trends[0] if group_trends else None,
                "most_growing": group_trends[-1] if group_trends else None
            }
        }

    except Exception as e:
        print(f"[GroupedTrend] Error: {e}")
        return {"data": [], "analysis": {"error": f"Error analyzing grouped trend: {str(e)}"}}


def _sanitize_string_value(value: str) -> str:
    """Sanitize a string value for SQL by escaping single quotes."""
    if not isinstance(value, str):
        return str(value)
    return value.replace("'", "''")


