"""
Visualization Helper - Determines chart type and formats data for frontend charts.

Maps query types to appropriate visualizations:
- comparison → bar chart
- trend → line chart
- percentage → pie/donut chart
- rank → horizontal bar chart
- metric (single value) → no chart (just number)
- list/filter/lookup → table (no chart)
"""

from typing import Dict, Any, List, Optional


def determine_visualization(
    query_plan: Dict[str, Any],
    result_data: List[Dict],
    entities: Dict[str, Any] = None
) -> Optional[Dict[str, Any]]:
    """
    Determine the appropriate visualization for query results.
    Returns None if visualization is not appropriate or data is invalid.
    """
    if not result_data or len(result_data) == 0:
        return None

    query_type = query_plan.get('query_type', '')

    # Query types that are better as tables only
    table_only_types = ['lookup', 'filter', 'list']
    if query_type in table_only_types:
        return None

    # Single row results - no chart needed (just show the number)
    if len(result_data) == 1:
        return None

    # Need at least 2 data points for meaningful visualization
    if len(result_data) < 2:
        return None

    # Try to build chart config
    chart_config = _build_chart_config(query_type, query_plan, result_data, entities)

    return chart_config


def _build_chart_config(
    query_type: str,
    plan: Dict[str, Any],
    data: List[Dict],
    entities: Dict[str, Any] = None
) -> Optional[Dict[str, Any]]:
    """Build chart configuration with smart label detection."""

    if not data:
        return None

    columns = list(data[0].keys())
    print(f"[Viz] Query type: {query_type}, Columns: {columns}, Rows: {len(data)}")

    # Special handling for comparison queries where label IS the key
    # Data format: [{"August": 9700000}, {"December": 10000000}]
    if query_type == 'comparison' and len(data) >= 2:
        chart_data = _handle_comparison_data(data, plan)
        if chart_data:
            colors = ['#8B5CF6', '#A78BFA', '#7C3AED', '#6D28D9', '#5B21B6', '#4C1D95']
            return {
                'type': 'bar',
                'title': _generate_title(plan, query_type),
                'data': chart_data,
                'xKey': 'name',
                'yKey': 'value',
                'colors': colors
            }

    # Find the best dimension and metric columns
    dimension_col, metric_col = _detect_columns(columns, data, plan)

    # Try to extract labels from plan/entities if dimension column is missing/invalid
    labels = None
    if not dimension_col:
        labels = _extract_labels_from_context(plan, entities, len(data))
        print(f"[Viz] No dimension column found, extracted labels: {labels}")

    # Must have metric column
    if not metric_col:
        print(f"[Viz] SKIP - No valid metric column found")
        return None

    # Must have either dimension column OR extracted labels
    if not dimension_col and not labels:
        print(f"[Viz] SKIP - No dimension column and no labels extractable")
        return None

    # Format the chart data
    chart_data = _format_data(data, dimension_col, metric_col, labels)

    # Validate the formatted data
    if not chart_data or len(chart_data) < 2:
        print(f"[Viz] SKIP - Formatted data invalid or too small")
        return None

    # Check all data points have valid names and values
    for point in chart_data:
        if not point.get('name') or point['name'] in ['', 'None', 'null']:
            print(f"[Viz] SKIP - Data point has invalid name: {point}")
            return None
        if point.get('value') is None:
            print(f"[Viz] SKIP - Data point has null value: {point}")
            return None

    print(f"[Viz] SUCCESS - Chart data: {chart_data}")

    # Purple theme colors
    colors = ['#8B5CF6', '#A78BFA', '#7C3AED', '#6D28D9', '#5B21B6', '#4C1D95']

    # Determine chart type
    chart_type = _get_chart_type(query_type, plan)
    title = _generate_title(plan, query_type)

    return {
        'type': chart_type,
        'title': title,
        'data': chart_data,
        'xKey': 'name',
        'yKey': 'value',
        'colors': colors
    }


def _handle_comparison_data(data: List[Dict], plan: Dict[str, Any]) -> Optional[List[Dict]]:
    """Handle special comparison data format where label is the key."""

    chart_data = []

    # Try to get labels from analysis
    analysis = plan.get('analysis', {})
    labels = []
    if analysis:
        period_a = analysis.get('period_a_label')
        period_b = analysis.get('period_b_label')
        if period_a and period_b:
            labels = [period_a, period_b]
            values = [analysis.get('period_a_value', 0), analysis.get('period_b_value', 0)]
            for label, value in zip(labels, values):
                if value is not None:
                    chart_data.append({
                        'name': str(label),
                        'value': round(value, 2) if isinstance(value, float) else value
                    })
            if len(chart_data) >= 2:
                print(f"[Viz] Comparison from analysis: {chart_data}")
                return chart_data

    # Try extracting from data rows where format is {"Label": value}
    for row in data:
        if len(row) == 1:
            # Single key-value pair: {"August": 9700000}
            for label, value in row.items():
                if value is not None and isinstance(value, (int, float)):
                    chart_data.append({
                        'name': str(label),
                        'value': round(value, 2) if isinstance(value, float) else value
                    })

    if len(chart_data) >= 2:
        print(f"[Viz] Comparison from single-key rows: {chart_data}")
        return chart_data

    return None


def _detect_columns(columns: List[str], data: List[Dict], plan: Dict[str, Any]):
    """Detect the dimension (label) and metric (value) columns."""

    dimension_col = None
    metric_col = None

    # Check each column's data type
    string_cols = []
    numeric_cols = []

    for col in columns:
        col_type = _analyze_column(col, data)
        if col_type == 'string':
            string_cols.append(col)
        elif col_type == 'numeric':
            numeric_cols.append(col)

    print(f"[Viz] String cols: {string_cols}, Numeric cols: {numeric_cols}")

    # Dimension = first valid string column (preferring group_by from plan)
    group_by = plan.get('group_by', [])
    if group_by:
        group_col = group_by[0] if isinstance(group_by, list) else group_by
        if group_col in string_cols:
            dimension_col = group_col

    if not dimension_col and string_cols:
        dimension_col = string_cols[0]

    # Metric = first numeric column (preferring ones with SUM/AVG/etc in name)
    agg_patterns = ['sum', 'avg', 'count', 'total', 'max', 'min', 'sales', 'revenue', 'profit', 'amount']
    for col in numeric_cols:
        col_lower = col.lower()
        for pattern in agg_patterns:
            if pattern in col_lower:
                metric_col = col
                break
        if metric_col:
            break

    if not metric_col and numeric_cols:
        metric_col = numeric_cols[0]

    return dimension_col, metric_col


def _analyze_column(col_name: str, data: List[Dict]) -> str:
    """Analyze a column's data type across all rows. Returns 'string', 'numeric', or 'invalid'."""

    if not data:
        return 'invalid'

    all_numeric = True
    all_string = True
    has_valid_values = False

    for row in data:
        value = row.get(col_name)

        # Skip None/null values
        if value is None or str(value) == 'None':
            all_string = False  # None is not a valid string label
            continue

        has_valid_values = True

        # Check if numeric
        if isinstance(value, (int, float)):
            all_string = False
        elif isinstance(value, str):
            try:
                float(value.replace(',', ''))
                all_string = False  # It's a numeric string
            except ValueError:
                all_numeric = False  # It's a real string
        else:
            all_numeric = False
            all_string = False

    if not has_valid_values:
        return 'invalid'

    if all_string:
        return 'string'
    elif all_numeric:
        return 'numeric'
    else:
        return 'invalid'


def _extract_labels_from_context(plan: Dict[str, Any], entities: Dict[str, Any], num_rows: int) -> Optional[List[str]]:
    """Try to extract category labels from plan filters or entities."""

    labels = []

    # Check subset_filters (often contains comparison items)
    subset_filters = plan.get('subset_filters', [])
    for f in subset_filters:
        if isinstance(f, dict):
            val = f.get('value') or f.get('values')
            if isinstance(val, list):
                labels.extend([str(v) for v in val])
            elif val:
                labels.append(str(val))

    # Check regular filters
    filters = plan.get('filters', [])
    for f in filters:
        if isinstance(f, dict):
            val = f.get('value') or f.get('values')
            if isinstance(val, list):
                labels.extend([str(v) for v in val])
            elif val:
                labels.append(str(val))

    # Check entities for comparison items - expanded list of keys
    if entities:
        entity_keys = [
            'comparison_items', 'items', 'categories', 'products',
            'month', 'months', 'time_periods', 'periods', 'dates',
            'locations', 'branches', 'cities', 'regions', 'areas',
            'payment_modes', 'payment_types', 'types'
        ]
        for key in entity_keys:
            if key in entities and entities[key]:
                items = entities[key]
                if isinstance(items, list):
                    labels.extend([str(i) for i in items])
                elif items:
                    labels.append(str(items))

    # Check for analysis metadata that might contain period labels
    analysis = plan.get('analysis', {})
    if analysis:
        period_a = analysis.get('period_a_label')
        period_b = analysis.get('period_b_label')
        if period_a and period_b:
            labels = [str(period_a), str(period_b)]

    # Remove duplicates while preserving order
    seen = set()
    unique_labels = []
    for label in labels:
        if label and label not in seen and label != 'None':
            seen.add(label)
            unique_labels.append(label)

    print(f"[Viz] Extracted labels: {unique_labels} (need {num_rows})")

    # Must have exactly the right number of labels
    if len(unique_labels) == num_rows:
        return unique_labels

    # If we have 2 rows and no labels, return None - don't show chart
    return None


def _format_data(
    data: List[Dict],
    dimension_col: Optional[str],
    metric_col: str,
    labels: Optional[List[str]] = None
) -> List[Dict]:
    """Format data for Recharts."""

    formatted = []

    for i, row in enumerate(data):
        # Get the label
        if dimension_col:
            name = row.get(dimension_col, '')
        elif labels and i < len(labels):
            name = labels[i]
        else:
            name = f"Item {i + 1}"

        # Get the value
        value = row.get(metric_col, 0)

        # Convert to number if needed
        if isinstance(value, str):
            try:
                value = float(value.replace(',', ''))
            except:
                value = 0

        # Round floats
        if isinstance(value, float):
            value = round(value, 2)

        formatted.append({
            'name': str(name) if name else f"Item {i + 1}",
            'value': value
        })

    return formatted


def _get_chart_type(query_type: str, plan: Dict[str, Any]) -> str:
    """Determine the best chart type for the query."""

    type_map = {
        'comparison': 'bar',
        'trend': 'line',
        'percentage': 'pie',
        'rank': 'horizontal_bar',
        'aggregation_on_subset': 'bar',
        'extrema_lookup': 'bar',
    }

    return type_map.get(query_type, 'bar')


def _generate_title(plan: Dict[str, Any], query_type: str) -> str:
    """Generate a clean title for the chart."""

    metrics = plan.get('metrics', [])
    metric_name = metrics[0] if metrics else 'Value'

    # Clean up metric name (remove SUM(), AVG(), etc.)
    metric_name = metric_name.replace('SUM(', '').replace('AVG(', '').replace('COUNT(', '')
    metric_name = metric_name.replace(')', '').replace('_', ' ').title()

    type_labels = {
        'comparison': 'Comparison',
        'trend': 'Trend',
        'percentage': 'Distribution',
        'rank': 'Ranking',
    }

    suffix = type_labels.get(query_type, '')

    if suffix:
        return f"{metric_name} {suffix}"
    return metric_name
