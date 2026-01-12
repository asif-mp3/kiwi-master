import re
from typing import Any, List, Dict, Union
from analytics_engine.metric_registry import MetricRegistry
from utils.sql_utils import quote_identifier


# =============================================================================
# SQL Input Validation & Sanitization
# =============================================================================

# Patterns that indicate SQL injection attempts
SQL_INJECTION_PATTERNS = [
    r';\s*(DROP|DELETE|TRUNCATE|ALTER|CREATE|INSERT|UPDATE)\s',  # Statement chaining
    r'--\s*$',  # SQL comment at end
    r'/\*.*\*/',  # Block comments
    r'\bUNION\s+(ALL\s+)?SELECT\b',  # UNION injection
    r'\bEXEC(UTE)?\s*\(',  # Execute calls
    r'\bxp_\w+',  # SQL Server extended procedures
    r'\bWAITFOR\s+DELAY\b',  # Time-based attacks
    r'\bBENCHMARK\s*\(',  # MySQL time-based
    r'\bSLEEP\s*\(',  # Sleep-based attacks
    r'0x[0-9a-fA-F]+',  # Hex-encoded payloads
]

SQL_INJECTION_REGEX = re.compile('|'.join(SQL_INJECTION_PATTERNS), re.IGNORECASE)


def _validate_value(value: Any, context: str = "value") -> None:
    """
    Validate a value for SQL injection patterns.
    Raises ValueError if suspicious patterns are detected.
    """
    if value is None:
        return

    if isinstance(value, (int, float, bool)):
        return  # Numeric types are safe

    if isinstance(value, str):
        # Check for SQL injection patterns
        if SQL_INJECTION_REGEX.search(value):
            raise ValueError(f"Invalid {context}: contains potentially unsafe SQL patterns")

        # Check for excessive length (potential buffer overflow)
        if len(value) > 10000:
            raise ValueError(f"Invalid {context}: value too long (max 10000 characters)")


def _sanitize_string(value: str) -> str:
    """
    Sanitize a string value for SQL.
    Escapes single quotes and removes null bytes.
    """
    if not isinstance(value, str):
        return str(value)

    # Remove null bytes (potential attack vector)
    value = value.replace('\x00', '')

    # Escape single quotes (SQL standard escaping)
    value = value.replace("'", "''")

    return value


def _validate_filter(f: Dict) -> None:
    """Validate a filter dictionary."""
    if not isinstance(f, dict):
        raise ValueError(f"Invalid filter: expected dict, got {type(f).__name__}")

    required_keys = ["column", "operator", "value"]
    for key in required_keys:
        if key not in f:
            raise ValueError(f"Invalid filter: missing required key '{key}'")

    # Validate column name (alphanumeric, underscores, spaces allowed)
    column = f["column"]
    if not isinstance(column, str) or not column.strip():
        raise ValueError("Invalid filter: column must be a non-empty string")
    if not re.match(r'^[\w\s\-\.]+$', column, re.UNICODE):
        raise ValueError(f"Invalid filter: column name '{column}' contains invalid characters")

    # Validate operator
    allowed_operators = ["=", "!=", "<", ">", "<=", ">=", "LIKE", "IN", "NOT IN", "IS", "IS NOT"]
    operator = f["operator"].upper()
    if operator not in allowed_operators:
        raise ValueError(f"Invalid filter: operator '{operator}' not allowed")

    # Validate value
    _validate_value(f["value"], context="filter value")


def compile_sql(plan: dict) -> str:
    """
    Converts a validated query plan into SQL.
    Deterministic. Template-based. Safe.
    """
    
    query_type = plan.get("query_type", "metric")
    
    if query_type == "lookup":
        return _compile_lookup(plan)
    elif query_type == "filter":
        return _compile_filter(plan)
    elif query_type == "metric":
        return _compile_metric(plan)
    elif query_type == "extrema_lookup":
        return _compile_extrema_lookup(plan)
    elif query_type == "rank":
        return _compile_rank(plan)
    elif query_type == "list":
        return _compile_list(plan)
    elif query_type == "aggregation_on_subset":
        return _compile_aggregation_on_subset(plan)
    else:
        raise ValueError(f"Unknown query type: {query_type}")


def _compile_lookup(plan):
    """Compile row lookup query"""
    table = quote_identifier(plan["table"])
    columns = plan.get("select_columns", ["*"])

    # Default to all columns if empty
    if not columns:
        columns = ["*"]

    # Handle case where columns might be string "*" instead of list ["*"]
    if columns == "*" or columns == ["*"]:
        quoted_columns = "*"
    else:
        # Ensure columns is a list
        if isinstance(columns, str):
            columns = [columns]
        quoted_columns = ", ".join([quote_identifier(col) for col in columns])

    where = _build_where_clause(plan["filters"])
    limit = plan.get("limit", 1)

    return f"SELECT {quoted_columns} FROM {table} {where} LIMIT {limit}".strip()


def _compile_filter(plan):
    """Compile filter query"""
    table = quote_identifier(plan["table"])
    columns = plan.get("select_columns", ["*"])

    # Handle case where columns might be string "*" instead of list ["*"]
    if columns == "*" or columns == ["*"] or not columns:
        columns = "*"
    else:
        # Ensure columns is a list
        if isinstance(columns, str):
            columns = [columns]
        columns = ", ".join([quote_identifier(col) for col in columns])
    
    where = _build_where_clause(plan["filters"])
    limit = plan.get("limit", 100)
    
    return f"SELECT {columns} FROM {table} {where} LIMIT {limit}".strip()



def _build_where_clause(filters):
    """
    Build WHERE clause from filters.
    Handles both numeric and text values with proper escaping.
    Uses flexible matching for names to handle spelling variations.
    Includes SQL injection validation for security.
    """
    if not filters:
        return ""

    conditions = []
    for f in filters:
        # Validate filter structure and values
        _validate_filter(f)

        column = quote_identifier(f["column"])
        operator = f["operator"]
        value = f["value"]

        # Handle None values
        if value is None:
            if operator in ("=", "IS"):
                conditions.append(f"{column} IS NULL")
            elif operator in ("!=", "IS NOT"):
                conditions.append(f"{column} IS NOT NULL")
            continue

        # Handle different value types
        if isinstance(value, str):
            if operator == "LIKE":
                # Case-insensitive LIKE - cast to VARCHAR for timestamp columns
                # First, normalize the value by removing apostrophes and special chars
                # This fixes translation issues like "ladies' wear" vs "Ladies Wear"
                normalized_value = value.replace("'", "").replace("'", "").replace("`", "")
                safe_value = _sanitize_string(normalized_value)

                # For name matching, try to be more flexible
                # Extract the core part of the search term (remove % wildcards)
                search_term = safe_value.strip('%')

                # If it's a name search (common patterns), use flexible matching
                # This helps with variations like "Meenakshi" vs "Meenakchi"
                if len(search_term) >= 4:  # Only for meaningful search terms
                    # Try multiple patterns:
                    # 1. Original pattern
                    # 2. Pattern with common variations (ksh -> kch, sh -> ch, etc.)
                    patterns = [safe_value]

                    # Add variation patterns for common Tamil name spellings
                    if 'ksh' in search_term.lower():
                        patterns.append(safe_value.replace('ksh', 'kch').replace('Ksh', 'Kch'))
                        patterns.append(safe_value.replace('ksh', 'kchi').replace('Ksh', 'Kchi'))
                    if 'sh' in search_term.lower():
                        patterns.append(safe_value.replace('sh', 'ch').replace('Sh', 'Ch'))

                    # Create OR condition for all patterns
                    pattern_conditions = [
                        f"LOWER(CAST({column} AS VARCHAR)) LIKE LOWER('{pattern}')"
                        for pattern in patterns
                    ]
                    conditions.append(f"({' OR '.join(pattern_conditions)})")
                else:
                    # For short terms, use original pattern
                    conditions.append(f"LOWER(CAST({column} AS VARCHAR)) LIKE LOWER('{safe_value}')")
            else:
                # Use actual operator (=, >=, <=, !=, etc.) for string comparisons
                safe_value = _sanitize_string(value)

                # Check if this looks like a date value (ISO format: YYYY-MM-DD)
                # For date comparisons, don't cast column to VARCHAR - compare directly
                is_date_value = bool(re.match(r'^\d{4}-\d{2}-\d{2}$', value))

                if is_date_value and operator in ('>=', '<=', '>', '<', '='):
                    # Date comparison - compare directly without casting
                    # DuckDB handles string dates well with datetime columns
                    conditions.append(f"{column} {operator} '{safe_value}'")
                else:
                    # Non-date string - cast column to VARCHAR for safety
                    conditions.append(f"CAST({column} AS VARCHAR) {operator} '{safe_value}'")
        elif isinstance(value, (int, float)):
            # Numeric value - safe to use directly
            conditions.append(f"{column} {operator} {value}")
        elif isinstance(value, bool):
            # Boolean value
            conditions.append(f"{column} {operator} {str(value).upper()}")
        else:
            # Unsupported type - convert to string safely
            safe_value = _sanitize_string(str(value))
            conditions.append(f"CAST({column} AS VARCHAR) {operator} '{safe_value}'")

    return "WHERE " + " AND ".join(conditions) if conditions else ""


def _compile_metric(plan):
    """Compile metric-based aggregation query"""
    registry = MetricRegistry()

    metric_sql = []
    base_table = None

    for metric in plan.get("metrics", []):
        metric_def = registry.get_metric(metric)
        metric_sql.append(f"{metric_def['sql']} AS {metric}")

        if base_table is None:
            base_table = metric_def["base_table"]

    select_clause = ", ".join(metric_sql)

    group_by_clause = ""
    if plan.get("group_by"):
        group_by_clause = " GROUP BY " + ", ".join(plan["group_by"])
        select_clause += ", " + ", ".join(plan["group_by"])

    where_clause = _build_where_clause(plan.get("filters", []))

    sql = f"""
        SELECT {select_clause}
        FROM {base_table}
        {where_clause}
        {group_by_clause}
    """

    return sql.strip()


def _compile_extrema_lookup(plan):
    """Compile extrema lookup query (min/max with ordering)"""
    table = quote_identifier(plan["table"])
    select_cols = plan.get("select_columns", ["*"])

    # Handle case where select_cols might be string "*" instead of list ["*"]
    if select_cols == "*" or select_cols == ["*"] or not select_cols:
        columns = "*"
    else:
        # Ensure select_cols is a list
        if isinstance(select_cols, str):
            select_cols = [select_cols]
        columns = ", ".join([quote_identifier(col) for col in select_cols])

    order_by = plan.get("order_by", [])
    limit = plan.get("limit", 1)
    
    # Build WHERE clause if filters exist
    where_clause = _build_where_clause(plan.get("filters", []))
    
    order_clause = ""
    if order_by:
        order_parts = [f"{quote_identifier(col)} {direction}" for col, direction in order_by]
        order_clause = "ORDER BY " + ", ".join(order_parts)
    
    return f"SELECT {columns} FROM {table} {where_clause} {order_clause} LIMIT {limit}".strip()


def _compile_rank(plan):
    """Compile rank query (ordered list, with optional GROUP BY for aggregation)"""
    table = quote_identifier(plan["table"])

    group_by = plan.get("group_by", [])
    metrics = plan.get("metrics", [])
    order_by = plan.get("order_by", [])
    limit = plan.get("limit", 100)

    # Check for date_grouping (MONTH, YEAR, WEEK, etc.)
    date_grouping = plan.get("date_grouping", "").upper()

    # Get aggregation function from plan (COUNT, SUM, AVG, etc.)
    # Default varies based on context
    agg_func = plan.get("aggregation_function", "").upper()

    # Build WHERE clause if filters exist
    where_clause = _build_where_clause(plan.get("filters", []))

    # If we have group_by, we need to aggregate
    if group_by:
        # Build SELECT with grouped columns + aggregated metrics
        # Handle date_grouping for time period extraction (MONTH, YEAR, etc.)
        select_parts = []
        group_by_parts = []

        for col in group_by:
            quoted_col = quote_identifier(col)
            if date_grouping and col.lower() in ('date', 'datetime', 'timestamp', 'created_at', 'order_date', 'transaction_date'):
                # Use DATE_TRUNC to extract time period
                # DuckDB DATE_TRUNC returns a date, we also extract readable format
                if date_grouping == "MONTH":
                    select_parts.append(f"DATE_TRUNC('month', {quoted_col}) AS month")
                    group_by_parts.append(f"DATE_TRUNC('month', {quoted_col})")
                elif date_grouping == "YEAR":
                    select_parts.append(f"DATE_TRUNC('year', {quoted_col}) AS year")
                    group_by_parts.append(f"DATE_TRUNC('year', {quoted_col})")
                elif date_grouping == "WEEK":
                    select_parts.append(f"DATE_TRUNC('week', {quoted_col}) AS week")
                    group_by_parts.append(f"DATE_TRUNC('week', {quoted_col})")
                elif date_grouping == "QUARTER":
                    select_parts.append(f"DATE_TRUNC('quarter', {quoted_col}) AS quarter")
                    group_by_parts.append(f"DATE_TRUNC('quarter', {quoted_col})")
                else:
                    # Default: just use the column as-is
                    select_parts.append(quoted_col)
                    group_by_parts.append(quoted_col)
            else:
                select_parts.append(quoted_col)
                group_by_parts.append(quoted_col)

        # Check if this is a COUNT query - ONLY use COUNT when explicitly requested
        # REMOVED dangerous heuristic that assumed ID columns meant COUNT
        # This caused "Top employees by sales" to use COUNT instead of SUM
        is_count_query = agg_func == "COUNT"
        is_count_distinct_query = agg_func == "COUNT_DISTINCT"

        # Add aggregated metrics
        if metrics:
            for metric in metrics:
                quoted_metric = quote_identifier(metric)
                if is_count_distinct_query:
                    # COUNT(DISTINCT column) for unique item counts
                    select_parts.append(f"COUNT(DISTINCT {quoted_metric}) AS unique_{metric}")
                elif is_count_query or agg_func == "COUNT":
                    select_parts.append(f"COUNT(*) AS {quoted_metric}")
                elif agg_func and agg_func in ("SUM", "AVG", "MIN", "MAX"):
                    select_parts.append(f"{agg_func}({quoted_metric}) AS {quoted_metric}")
                else:
                    select_parts.append(f"SUM({quoted_metric}) AS {quoted_metric}")

        # If no explicit metrics but order_by has a column not in group_by
        if not metrics:
            for col, _ in order_by:
                if col not in group_by:
                    # For count queries or ID columns, use COUNT(*)
                    if is_count_distinct_query:
                        # COUNT(DISTINCT column) for unique item counts
                        quoted_col = quote_identifier(col)
                        select_parts.append(f"COUNT(DISTINCT {quoted_col}) AS unique_count")
                        # Update order_by to use "unique_count" instead of the original column
                        order_by = [("unique_count", direction) for _, direction in order_by]
                    elif is_count_query:
                        select_parts.append(f"COUNT(*) AS count")
                        # Update order_by to use "count" instead of the original column
                        order_by = [("count", direction) for _, direction in order_by]
                    else:
                        quoted_col = quote_identifier(col)
                        if agg_func and agg_func in ("SUM", "AVG", "MIN", "MAX", "COUNT"):
                            select_parts.append(f"{agg_func}({quoted_col}) AS {quoted_col}")
                        else:
                            select_parts.append(f"SUM({quoted_col}) AS {quoted_col}")
                    break  # Only need one aggregation

        columns = ", ".join(select_parts)

        # Build GROUP BY clause - use group_by_parts which handles date_grouping
        group_clause = "GROUP BY " + ", ".join(group_by_parts)

        # Build ORDER BY clause (use the aggregated column name)
        # For date_grouping, update order_by to use the alias (month, year, etc.)
        order_clause = ""
        if order_by:
            order_parts = []
            for col, direction in order_by:
                # If ordering by a date column with date_grouping, use the alias
                if date_grouping and col.lower() in ('date', 'datetime', 'timestamp', 'created_at', 'order_date', 'transaction_date'):
                    alias = date_grouping.lower()  # month, year, week, quarter
                    order_parts.append(f"{alias} {direction}")
                else:
                    order_parts.append(f"{quote_identifier(col)} {direction}")
            order_clause = "ORDER BY " + ", ".join(order_parts)

        return f"SELECT {columns} FROM {table} {where_clause} {group_clause} {order_clause} LIMIT {limit}".strip()

    # No group_by - simple rank query
    select_columns = plan.get("select_columns", ["*"])
    # Handle case where select_columns might be string "*" instead of list ["*"]
    if select_columns == "*" or select_columns == ["*"] or not select_columns:
        columns = "*"
    else:
        # Ensure select_columns is a list
        if isinstance(select_columns, str):
            select_columns = [select_columns]
        columns = ", ".join([quote_identifier(col) for col in select_columns])

    order_clause = ""
    if order_by:
        order_parts = [f"{quote_identifier(col)} {direction}" for col, direction in order_by]
        order_clause = "ORDER BY " + ", ".join(order_parts)

    return f"SELECT {columns} FROM {table} {where_clause} {order_clause} LIMIT {limit}".strip()


def _compile_list(plan):
    """Compile list/show all query"""
    table = quote_identifier(plan["table"])

    select_columns = plan.get("select_columns", ["*"])

    # Handle case where select_columns might be string "*" instead of list ["*"]
    if select_columns == "*" or select_columns == ["*"] or not select_columns:
        columns = "*"
    else:
        # Ensure select_columns is a list
        if isinstance(select_columns, str):
            select_columns = [select_columns]
        columns = ", ".join([quote_identifier(col) for col in select_columns])

    limit = plan.get("limit", 100)

    return f"SELECT {columns} FROM {table} LIMIT {limit}".strip()


def _compile_aggregation_on_subset(plan):
    """Compile aggregation on subset query (e.g., AVG of first 5 items)"""
    table = quote_identifier(plan["table"])
    aggregation_function = plan["aggregation_function"]
    aggregation_column = quote_identifier(plan["aggregation_column"])
    
    # Build the subquery to get the subset
    subset_filters = plan.get("subset_filters", [])
    subset_order_by = plan.get("subset_order_by", [])
    subset_limit = plan.get("subset_limit")
    
    
    # Note: subset_limit can be None when aggregating ALL matching data
    # Only use LIMIT when a specific number is requested
    
    # Get all columns we want to show in the breakdown
    # Include aggregation column, order columns, and common identifier columns
    subquery_columns = [aggregation_column]
    
    # Add ordering columns
    for col, _ in subset_order_by:
        quoted_col = quote_identifier(col)
        if quoted_col not in subquery_columns:
            subquery_columns.append(quoted_col)
    
    # Try to add common identifier columns (like name, id, etc.)
    # We'll select * from the subset to get all columns for the breakdown
    
    # Build WHERE clause for subset
    where_clause = _build_where_clause(subset_filters)
    
    # Build ORDER BY clause for subset
    order_clause = ""
    if subset_order_by:
        order_parts = [f"{quote_identifier(col)} {direction}" for col, direction in subset_order_by]
        order_clause = "ORDER BY " + ", ".join(order_parts)
    
    # Build LIMIT clause
    limit_clause = ""
    if subset_limit is not None:
        limit_clause = f"LIMIT {subset_limit}"
    
    # Build SQL with subquery that calculates the aggregation in the database
    # The outer query calculates the aggregation on the subset
    # The inner query (subquery) gets the subset of rows
    sql = f"""
SELECT 
    {aggregation_function}({aggregation_column}) as result,
    COUNT(*) as row_count,
    MIN({aggregation_column}) as min_value,
    MAX({aggregation_column}) as max_value
FROM (
    SELECT *
    FROM {table}
    {where_clause}
    {order_clause}
    {limit_clause}
) subset
    """
    
    return sql.strip()
