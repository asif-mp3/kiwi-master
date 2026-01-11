import json
import re
from jsonschema import validate, ValidationError
from analytics_engine.metric_registry import MetricRegistry
from analytics_engine.duckdb_manager import DuckDBManager
from utils.sql_utils import quote_identifier


def normalize_date_format_in_value(value: str) -> str:
    """
    Convert date values from DD/MM/YYYY to ISO format (YYYY-MM-DD).
    This handles common date format issues from LLM output.

    Examples:
        "%15/11/2025%" -> "%2025-11-15%"
        "15/11/2025" -> "2025-11-15"
        "%01/03/2024%" -> "%2024-03-01%"
    """
    if not isinstance(value, str):
        return value

    # Pattern to match DD/MM/YYYY or D/M/YYYY format (with optional surrounding wildcards)
    # Captures the wildcards separately to preserve them
    pattern = r'(%?)(\d{1,2})/(\d{1,2})/(\d{4})(%?)'

    def replace_date(match):
        prefix = match.group(1)  # Leading %
        day = match.group(2).zfill(2)  # DD
        month = match.group(3).zfill(2)  # MM
        year = match.group(4)  # YYYY
        suffix = match.group(5)  # Trailing %

        # Validate it's a reasonable date
        try:
            d = int(day)
            m = int(month)
            if 1 <= d <= 31 and 1 <= m <= 12:
                # Convert to ISO format: YYYY-MM-DD
                return f"{prefix}{year}-{month}-{day}{suffix}"
        except ValueError:
            pass

        # Return original if not a valid date
        return match.group(0)

    return re.sub(pattern, replace_date, value)


def normalize_date_formats_in_plan(plan: dict) -> dict:
    """
    Normalize date formats in filter values from DD/MM/YYYY to ISO format.
    This is a safety net for when the LLM generates wrong date formats.
    """
    # Normalize filters
    for filter_item in plan.get("filters", []):
        if "value" in filter_item and isinstance(filter_item["value"], str):
            original = filter_item["value"]
            normalized = normalize_date_format_in_value(original)
            if original != normalized:
                print(f"  [Validator] Normalized date format: '{original}' -> '{normalized}'")
                filter_item["value"] = normalized

    # Normalize subset_filters
    for filter_item in plan.get("subset_filters", []):
        if "value" in filter_item and isinstance(filter_item["value"], str):
            original = filter_item["value"]
            normalized = normalize_date_format_in_value(original)
            if original != normalized:
                print(f"  [Validator] Normalized date format: '{original}' -> '{normalized}'")
                filter_item["value"] = normalized

    return plan


def get_table_schema(table_name: str) -> dict:
    """
    Get schema information for a table from DuckDB.
    Returns dict with column names and their types.
    """
    db = DuckDBManager()
    try:
        # Get column information
        quoted_table = quote_identifier(table_name)
        result = db.conn.execute(f"DESCRIBE {quoted_table}").fetchdf()
        schema = {}
        for _, row in result.iterrows():
            schema[row['column_name']] = row['column_type']
        return schema
    except Exception as e:
        raise ValueError(f"Table '{table_name}' does not exist in database: {e}")


def validate_table_exists(table_name: str):
    """Validate that table exists in DuckDB"""
    db = DuckDBManager()
    tables = db.list_tables()
    if table_name not in tables:
        raise ValueError(f"Table '{table_name}' does not exist. Available tables: {tables}")


def normalize_column_names(plan: dict, table_name: str) -> dict:
    """
    Normalize column names in plan to match actual database column names (case-insensitive).
    Returns updated plan with corrected column names.
    """
    table_schema = get_table_schema(table_name)
    column_map = {col.lower(): col for col in table_schema.keys()}
    
    # Normalize select_columns
    if "select_columns" in plan and plan["select_columns"] is not None and plan["select_columns"] != ["*"]:
        plan["select_columns"] = [
            column_map.get(col.lower(), col) for col in plan["select_columns"]
        ]
    
    # Normalize filters
    if "filters" in plan:
        for f in plan["filters"]:
            if "column" in f:
                f["column"] = column_map.get(f["column"].lower(), f["column"])
    
    # Normalize group_by
    if "group_by" in plan:
        plan["group_by"] = [
            column_map.get(col.lower(), col) for col in plan["group_by"]
        ]
    
    # Normalize order_by
    if "order_by" in plan:
        plan["order_by"] = [
            [column_map.get(col[0].lower(), col[0]), col[1]] for col in plan["order_by"]
        ]
    
    return plan


def validate_columns_exist(columns: list, table_name: str):
    """
    Validate that all columns exist in the specified table.
    Performs case-insensitive matching.
    """
    if not columns:
        return
    
    # Allow wildcard
    if columns == ["*"]:
        return

    table_schema = get_table_schema(table_name)
    available_columns = list(table_schema.keys())

    # Create case-insensitive lookup
    column_map = {col.lower(): col for col in available_columns}

    for column in columns:
        column_lower = column.lower()

        # 1. Exact match (case-insensitive)
        if column_lower in column_map:
            continue

        # 2. Partial/fuzzy match - LLM might use shortened column names
        # e.g., "Homemade Powders" should match "Homemade Powders, Pastes & Pickles"
        found = False
        for actual_col in available_columns:
            actual_lower = actual_col.lower()
            # Check if LLM column is contained in actual column or vice versa
            if column_lower in actual_lower or actual_lower in column_lower:
                found = True
                break

        if not found:
            # 3. Try fuzzy matching for typos (80% similarity)
            from difflib import SequenceMatcher
            for actual_col in available_columns:
                ratio = SequenceMatcher(None, column_lower, actual_col.lower()).ratio()
                if ratio >= 0.8:
                    found = True
                    break

        if not found:
            raise ValueError(
                f"Column '{column}' does not exist in table '{table_name}'. "
                f"Available columns: {available_columns}"
            )



def validate_metric_table_mapping(metrics: list, table_name: str, plan: dict = None):
    """
    Validate that metrics are used with their correct base table.

    IMPORTANT: This function is lenient to handle LLM confusion between metrics and columns.
    - If metric is actually a column name in the table, allow it (LLM put column in wrong field)
    - If metric is similar to a column name (fuzzy match), map it to the column
    - If no metrics are registered, skip validation entirely
    - Only raise error for truly invalid metrics that aren't columns either

    Returns: List of corrected metrics (may be modified from input)
    """
    if not metrics:
        return metrics

    registry = MetricRegistry()

    # Get table columns for fallback check (LLM might confuse columns with metrics)
    try:
        table_schema = get_table_schema(table_name)
        column_names = list(table_schema.keys())
        column_names_lower = [col.lower() for col in column_names]
    except Exception:
        column_names = []
        column_names_lower = []

    corrected_metrics = []
    columns_to_add = []  # Metrics that should be moved to select_columns

    for metric in metrics:
        metric_lower = metric.lower()

        # FIRST: Check if this "metric" is actually a column name (exact match)
        if metric_lower in column_names_lower:
            # It's a column name - move to select_columns instead
            idx = column_names_lower.index(metric_lower)
            columns_to_add.append(column_names[idx])
            continue

        # SECOND: Try fuzzy matching to find similar column names
        # e.g., "Total_Revenue" might match "Sale_Amount" or "Revenue"
        from difflib import SequenceMatcher
        best_match = None
        best_ratio = 0

        # Semantic mappings for common business terms
        semantic_map = {
            'revenue': ['sale', 'sales', 'amount', 'income', 'total'],
            'sales': ['sale', 'revenue', 'amount', 'total'],
            'profit': ['profit', 'margin', 'earnings', 'net'],
            'cost': ['cost', 'expense', 'amount'],
            'total': ['sum', 'amount', 'total', 'gross'],
            'quantity': ['qty', 'quantity', 'count', 'units'],
            'price': ['price', 'rate', 'unit_price', 'amount'],
        }

        # Also check for keyword-based matching
        metric_keywords = set(metric_lower.replace('_', ' ').split())

        for actual_col in column_names:
            actual_lower = actual_col.lower()
            actual_keywords = set(actual_lower.replace('_', ' ').split())

            # Check string similarity
            ratio = SequenceMatcher(None, metric_lower, actual_lower).ratio()
            if ratio > best_ratio and ratio >= 0.5:
                best_ratio = ratio
                best_match = actual_col

            # Check keyword overlap
            common_keywords = metric_keywords & actual_keywords
            if common_keywords:
                if ratio > 0.3:
                    best_match = actual_col
                    best_ratio = max(ratio, 0.6)

            # Check semantic similarity (e.g., "revenue" semantically matches "sale_amount")
            for metric_kw in metric_keywords:
                if metric_kw in semantic_map:
                    for semantic_match in semantic_map[metric_kw]:
                        if semantic_match in actual_lower:
                            best_match = actual_col
                            best_ratio = max(best_ratio, 0.7)
                            break

        if best_match and best_ratio >= 0.5:
            # Found a similar column - use it instead of the invalid metric
            columns_to_add.append(best_match)
            continue

        # THIRD: Check if it's a registered metric
        if registry.is_valid_metric(metric):
            # Valid registered metric - validate table mapping
            metric_def = registry.get_metric(metric)
            expected_table = metric_def.get("base_table")

            if expected_table and expected_table != table_name:
                raise ValueError(
                    f"Metric '{metric}' can only be used with table '{expected_table}', "
                    f"not '{table_name}'"
                )
            corrected_metrics.append(metric)
            continue

        # If no metrics are defined in the registry, be lenient
        if not registry.metrics:
            # No registry - just use wildcard to get all columns
            columns_to_add.append("*")
            continue

        # FOURTH: Not found anywhere - be lenient and use wildcard instead of erroring
        # This prevents query failures for vague questions like "are we meeting our targets?"
        print(f"  [Validator] Warning: Metric '{metric}' not found, using all columns instead")
        columns_to_add.append("*")
        continue

    # Move column-like metrics to select_columns
    if columns_to_add and plan is not None:
        existing_cols = plan.get("select_columns") or []
        for col in columns_to_add:
            if col not in existing_cols:
                existing_cols.append(col)
        plan["select_columns"] = existing_cols

    return corrected_metrics


def validate_filter_values(filters: list, table_name: str):
    """Validate that filter values match column types"""
    if not filters:
        return
    
    table_schema = get_table_schema(table_name)
    
    for f in filters:
        column = f.get("column")
        value = f.get("value")
        operator = f.get("operator")
        
        # Validate column exists
        if column not in table_schema:
            raise ValueError(
                f"Filter column '{column}' does not exist in table '{table_name}'"
            )
        
        # Validate operator
        allowed_ops = ["=", ">", "<", ">=", "<=", "!=", "LIKE"]
        if operator not in allowed_ops:
            raise ValueError(f"Unsafe operator: {operator}. Allowed: {allowed_ops}")
        
        # Basic type validation
        col_type = table_schema[column].upper()

        # Numeric columns should have numeric values (unless using LIKE)
        if any(t in col_type for t in ["INT", "FLOAT", "DOUBLE", "DECIMAL", "NUMERIC"]):
            if operator != "LIKE":
                # Allow string numbers - try to convert them
                if isinstance(value, str):
                    try:
                        float(value)  # Validate it's convertible to number
                    except ValueError:
                        raise ValueError(
                            f"Column '{column}' is numeric ({col_type}) but filter value '{value}' cannot be converted to a number"
                        )
                elif not isinstance(value, (int, float)):
                    raise ValueError(
                        f"Column '{column}' is numeric ({col_type}) but filter value is {type(value).__name__}"
                    )

        # LIKE operator should only be used with string values
        if operator == "LIKE" and not isinstance(value, str):
            raise ValueError(
                f"LIKE operator requires string value, got {type(value).__name__}"
            )


def validate_no_unknown_keys(plan: dict):
    """Reject plans with unexpected keys"""
    allowed_keys = {
        "query_type", "table", "metrics", "select_columns",
        "filters", "group_by", "order_by", "limit",
        "aggregation_function", "aggregation_column",
        "subset_filters", "subset_order_by", "subset_limit",
        # Advanced query type keys (comparison, percentage, trend)
        "comparison", "percentage", "trend",
        # Date period grouping (MONTH, YEAR, WEEK, etc.)
        "date_grouping"
    }
    
    unknown_keys = set(plan.keys()) - allowed_keys
    if unknown_keys:
        raise ValueError(f"Plan contains unknown keys: {unknown_keys}")


def validate_plan(plan: dict, schema_path="planning_layer/plan_schema.json"):
    """
    Validates planner output against schema and registry.
    Enforces query type-specific rules.
    
    CRITICAL: This is the authoritative validation layer.
    All LLM output MUST pass through this validator.
    """
    
    # Normalize plan before validation (handle None values)
    # Convert None to appropriate defaults for ALL fields
    
    # Handle array fields
    if plan.get("select_columns") is None:
        plan["select_columns"] = []
    
    if plan.get("metrics") is None:
        plan["metrics"] = []

    # --- CRITICAL FIX: Handle LLM confusion between metrics and select_columns ---
    # For non-metric query types (lookup, filter, list, etc.), if LLM put column names
    # in "metrics" instead of "select_columns", move them automatically.
    # This prevents errors like "Lookup queries cannot use aggregation metrics"
    query_type = plan.get("query_type", "metric")
    if query_type in ["lookup", "filter", "list", "extrema_lookup", "rank"]:
        metrics_to_move = plan.get("metrics", [])
        if metrics_to_move:
            # Move metrics to select_columns
            existing_cols = plan.get("select_columns") or []
            plan["select_columns"] = existing_cols + metrics_to_move
            plan["metrics"] = []  # Clear metrics for non-metric queries

    if plan.get("filters") is None:
        plan["filters"] = []
    
    if plan.get("group_by") is None:
        plan["group_by"] = []
    
    if plan.get("order_by") is None:
        plan["order_by"] = []
    
    if plan.get("subset_filters") is None:
        plan["subset_filters"] = []
    
    if plan.get("subset_order_by") is None:
        plan["subset_order_by"] = []
    
    # Handle numeric fields
    if plan.get("limit") is None:
        # Set default limit based on query type
        query_type = plan.get("query_type", "metric")
        if query_type in ["lookup", "extrema_lookup"]:
            plan["limit"] = 1
        else:
            plan["limit"] = 100
    
    # Handle string fields - convert None to empty string
    if plan.get("aggregation_column") is None:
        plan["aggregation_column"] = ""
    
    if plan.get("aggregation_function") is None:
        plan["aggregation_function"] = ""
    
    # Recursively handle None in filter values
    for filter_item in plan.get("filters", []):
        if filter_item.get("value") is None:
            filter_item["value"] = ""
    
    for filter_item in plan.get("subset_filters", []):
        if filter_item.get("value") is None:
            filter_item["value"] = ""

    # Load JSON schema
    with open(schema_path) as f:
        schema = json.load(f)

    # 1. Validate JSON structure
    try:
        validate(instance=plan, schema=schema)
    except ValidationError as e:
        raise ValueError(f"Plan schema violation: {e.message}")
    
    # 2. Reject unknown keys
    validate_no_unknown_keys(plan)
    
    # 3. Validate table exists
    table = plan.get("table")
    validate_table_exists(table)
    
    # 4. Normalize column names (case-insensitive matching)
    plan = normalize_column_names(plan, table)

    # 4b. Normalize date formats in filter values (DD/MM/YYYY -> YYYY-MM-DD)
    plan = normalize_date_formats_in_plan(plan)

    # 5. Validate columns exist
    select_columns = plan.get("select_columns", [])
    validate_columns_exist(select_columns, table)
    
    # 5. Validate filter columns and values
    filters = plan.get("filters", [])
    validate_filter_values(filters, table)
    
    # 6. Validate group_by columns exist
    group_by = plan.get("group_by", [])
    validate_columns_exist(group_by, table)
    
    # 7. Validate order_by columns exist
    order_by = plan.get("order_by", [])
    if order_by:
        order_columns = [col[0] for col in order_by]
        validate_columns_exist(order_columns, table)

    query_type = plan.get("query_type")
    
    # 8. Type-specific validation
    if query_type == "metric":
        # Validate metrics exist and match table
        metrics = plan.get("metrics", [])
        if not metrics:
            raise ValueError("Metric queries must specify at least one metric")

        # Validate and possibly correct metrics (LLM might use wrong column names)
        # This may move column-like metrics to select_columns
        corrected_metrics = validate_metric_table_mapping(metrics, table, plan)
        plan["metrics"] = corrected_metrics  # Update with corrected metrics

        # If all metrics were moved to select_columns, change query type to "list"
        # This prevents SQL compiler from trying to look up non-existent metrics
        if not corrected_metrics and plan.get("select_columns"):
            plan["query_type"] = "list"
            print(f"  [Validator] Converted 'metric' to 'list' (metrics were column names)")
    
    elif query_type == "lookup":
        # Lookup queries cannot use metrics - move to select_columns if present
        if plan.get("metrics"):
            metrics = plan.get("metrics", [])
            select_cols = plan.get("select_columns", [])
            for m in metrics:
                if m not in select_cols:
                    select_cols.append(m)
            plan["select_columns"] = select_cols
            plan["metrics"] = []
            print(f"  [Validator] Moved metrics to select_columns for lookup query")

        # Auto-fix: Set LIMIT 1 for lookup queries
        if plan.get("limit") != 1:
            plan["limit"] = 1
            print(f"  [Validator] Auto-set limit=1 for lookup query")

        # Must have filters - if not, try to use "*" as wildcard
        if not plan.get("filters"):
            print(f"  [Validator] Warning: Lookup query without filters, may return first row")
    
    elif query_type == "filter":
        # Filter queries cannot use metrics
        if plan.get("metrics"):
            raise ValueError("Filter queries cannot use aggregation metrics")

        # Must have filters - if missing, convert to 'list' query as fallback
        # This handles complex queries like "employees above average" that can't be expressed as filters
        if not plan.get("filters"):
            print(f"  [Validator] Warning: Filter query without filters - converting to 'list' query")
            plan["query_type"] = "list"
            # Continue validation as list query (no special requirements)
    
    elif query_type == "extrema_lookup":
        # Extrema lookup must have order_by
        if not plan.get("order_by"):
            raise ValueError("Extrema lookup queries must have order_by")
        
        # Must have LIMIT 1
        if plan.get("limit") != 1:
            raise ValueError("Extrema lookup queries must have LIMIT 1")
    
    elif query_type == "rank":
        # Rank queries must have order_by
        if not plan.get("order_by"):
            raise ValueError("Rank queries must have order_by")

        # Validate date_grouping if present
        date_grouping = plan.get("date_grouping")
        if date_grouping:
            allowed_groupings = ["MONTH", "YEAR", "WEEK", "QUARTER", "DAY"]
            if date_grouping.upper() not in allowed_groupings:
                raise ValueError(f"Invalid date_grouping: {date_grouping}. Allowed: {allowed_groupings}")
    
    elif query_type == "list":
        # List queries are simple, no special validation needed
        pass
    
    elif query_type == "aggregation_on_subset":
        # Aggregation on subset must have aggregation_function and aggregation_column
        if not plan.get("aggregation_function"):
            raise ValueError("Aggregation on subset queries must have aggregation_function")
        
        if not plan.get("aggregation_column"):
            raise ValueError("Aggregation on subset queries must have aggregation_column")
        
        # Validate aggregation function
        allowed_functions = ["AVG", "SUM", "COUNT", "MAX", "MIN"]
        if plan["aggregation_function"] not in allowed_functions:
            raise ValueError(f"Invalid aggregation function: {plan['aggregation_function']}. Allowed: {allowed_functions}")
        
        # Validate aggregation column exists
        agg_column = plan["aggregation_column"]
        validate_columns_exist([agg_column], table)
        
        # Validate subset_order_by if present
        subset_order_by = plan.get("subset_order_by", [])
        if subset_order_by:
            subset_order_columns = [col[0] for col in subset_order_by]
            validate_columns_exist(subset_order_columns, table)
        
        # Validate subset_filters if present
        subset_filters = plan.get("subset_filters", [])
        if subset_filters:
            validate_filter_values(subset_filters, table)

    elif query_type == "comparison":
        # Comparison queries require the comparison config object
        comparison_config = plan.get("comparison")
        if not comparison_config:
            raise ValueError("Comparison queries must have a 'comparison' configuration")
        
        # Validate required nested structure
        if not comparison_config.get("period_a") or not comparison_config.get("period_b"):
            raise ValueError("Comparison queries must specify both 'period_a' and 'period_b'")

    elif query_type == "percentage":
        # Percentage queries require the percentage config object
        percentage_config = plan.get("percentage")
        if not percentage_config:
            raise ValueError("Percentage queries must have a 'percentage' configuration")
        
        # Validate required nested structure
        if not percentage_config.get("numerator") or not percentage_config.get("denominator"):
            raise ValueError("Percentage queries must specify both 'numerator' and 'denominator'")

    elif query_type == "trend":
        # Trend queries require the trend config object
        trend_config = plan.get("trend")
        if not trend_config:
            raise ValueError("Trend queries must have a 'trend' configuration")
        
        # Validate required fields
        if not trend_config.get("date_column") or not trend_config.get("value_column"):
            raise ValueError("Trend queries must specify 'date_column' and 'value_column'")

    return True
