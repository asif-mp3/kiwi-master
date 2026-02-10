"""
Visualization Helper - Determines chart type and formats data for frontend charts.

Maps query types to appropriate visualizations:
- comparison -> bar chart
- trend -> line chart
- percentage -> pie/donut chart
- rank -> horizontal bar chart
- projection -> line chart with dotted forecast line
- metric (single value) -> no chart (just number)
- list/filter/lookup -> table (no chart)
"""

from typing import Dict, Any, List, Optional


def _humanize_column_name(col_name: str) -> str:
    """Convert column name to human-readable title."""
    # Remove common prefixes/suffixes
    name = col_name.replace('_', ' ').replace('-', ' ')
    # Capitalize words
    name = ' '.join(word.capitalize() for word in name.split())
    # Handle common abbreviations
    abbreviations = {
        'Amt': 'Amount',
        'Qty': 'Quantity',
        'Pct': 'Percentage',
        'Avg': 'Average',
        'Tot': 'Total',
    }
    for abbrev, full in abbreviations.items():
        name = name.replace(abbrev, full)
    return name


def _build_supporting_text(row: dict, primary_col: str, query_type: str = '') -> str:
    """
    Build user-friendly supporting text for metric card.

    For aggregations (SUM, AVG, etc.), no supporting text needed - the value speaks for itself.
    Only add context when it provides meaningful insight to the user.
    """
    # For simple aggregations, no supporting text needed
    # Technical details like "from X records" or "range: min-max" are confusing
    if query_type in ['metric', 'aggregation_on_subset', 'extrema_lookup']:
        return ""

    # For percentage queries, might want to show what it's a percentage of
    if query_type == 'percentage':
        if 'numerator' in row and 'denominator' in row:
            try:
                num = int(row['numerator'])
                denom = int(row['denominator'])
                return f"{num:,} out of {denom:,}"
            except (ValueError, TypeError):
                pass

    return ""


# Keywords that indicate a projection/forecast query
PROJECTION_KEYWORDS = [
    'projection', 'forecast', 'predict', 'expected',
    'next month', 'next quarter', 'next year',
    'if continues', 'will be', 'going forward',
    'extrapolate', 'estimate', 'future'
]


def _is_projection_query(plan: Dict[str, Any], entities: Dict[str, Any] = None) -> bool:
    """Detect if this is a projection/forecast query."""
    # Check query type
    query_type = plan.get('query_type', '')
    if query_type in ['projection', 'forecast']:
        return True

    # Check for projection flag in plan
    if plan.get('is_projection') or plan.get('projection'):
        return True

    # Check analysis metadata
    analysis = plan.get('analysis', {})
    if analysis.get('is_projection') or analysis.get('forecast'):
        return True

    # Check raw question for projection keywords
    raw_question = ''
    if entities:
        raw_question = entities.get('raw_question', '').lower()
    if any(kw in raw_question for kw in PROJECTION_KEYWORDS):
        return True

    return False


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
    table_only_types = ['lookup', 'filter', 'list', 'multi_step']
    if query_type in table_only_types:
        return None

    # Single row results - use metric card for aggregation queries
    if len(result_data) == 1:
        # These query types benefit from a metric card display
        metric_card_types = {'metric', 'aggregation_on_subset', 'extrema_lookup', 'percentage'}

        if query_type in metric_card_types:
            row = result_data[0]
            # Find the primary value column (exclude supporting columns)
            exclude_cols = {'row_count', 'min_value', 'max_value', 'count', 'numerator', 'denominator'}
            all_cols = [c for c in row.keys() if c.lower() not in exclude_cols]

            # Priority 1: Use aggregation_column from plan if available
            agg_col = query_plan.get('aggregation_column')
            if agg_col and agg_col in row:
                value_col = agg_col
                value = row.get(value_col, 0)
            else:
                # Priority 2: Find the first NUMERIC column (not text like "Category")
                value_col = None
                value = None
                for col in all_cols:
                    col_value = row.get(col)
                    if isinstance(col_value, (int, float)) and col_value is not None:
                        value_col = col
                        value = col_value
                        break

                # Priority 3: Fall back to first column if no numeric found
                if value_col is None and all_cols:
                    value_col = all_cols[0]
                    value = row.get(value_col, 0)

            if value_col:
                # Determine if this is a percentage
                is_percentage = query_type == 'percentage' or 'percent' in value_col.lower()

                print(f"[Viz] Metric card: {value_col} = {value}, is_percentage={is_percentage}")

                return {
                    'type': 'metric_card',
                    'title': _humanize_column_name(value_col),
                    'data': {
                        'value': value,
                        'is_percentage': is_percentage,
                        'supporting_text': _build_supporting_text(row, value_col, query_type)
                    }
                }
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

    # Special handling for trend queries from advanced executor
    # Data format: [{"date": "2025-01-01", "value": 123}, ...]
    if query_type == 'trend' and len(data) >= 2:
        if 'date' in columns and 'value' in columns:
            chart_data = []
            for row in data:
                date_val = row.get('date', '')
                value = row.get('value', 0)
                # Format date for display
                name = str(date_val) if date_val else 'Unknown'
                chart_data.append({'name': name, 'value': value})

            if len(chart_data) >= 2:
                colors = ['#8B5CF6', '#A78BFA', '#7C3AED', '#6D28D9', '#5B21B6', '#4C1D95']
                print(f"[Viz] SUCCESS - Trend chart data: {len(chart_data)} points")
                return {
                    'type': 'line',
                    'title': _generate_title(plan, query_type),
                    'data': chart_data,
                    'xKey': 'name',
                    'yKey': 'value',
                    'colors': colors
                }

    # Special handling for grouped trend queries
    # Data format: [{"group": "State A", "direction": "increasing", "slope": 0.5, ...}, ...]
    if query_type == 'trend' and len(data) >= 2:
        if 'group' in columns and 'slope' in columns:
            chart_data = []
            for row in data:
                group_name = row.get('group', '')
                slope = row.get('slope', 0) or row.get('normalized_slope', 0)
                chart_data.append({'name': str(group_name), 'value': slope})

            if len(chart_data) >= 2:
                colors = ['#8B5CF6', '#A78BFA', '#7C3AED', '#6D28D9', '#5B21B6', '#4C1D95']
                print(f"[Viz] SUCCESS - Grouped trend chart: {len(chart_data)} groups")
                return {
                    'type': 'horizontal_bar',
                    'title': 'Trend by ' + plan.get('trend', {}).get('group_by', 'Group'),
                    'data': chart_data,
                    'xKey': 'name',
                    'yKey': 'value',
                    'colors': colors
                }

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

    # Check if this is a projection query
    is_projection = _is_projection_query(plan, entities)

    # Determine chart type (projections always use line charts)
    chart_type = 'line' if is_projection else _get_chart_type(query_type, plan)
    title = _generate_title(plan, query_type)

    # For projection queries, mark projected data points
    if is_projection:
        chart_data = _mark_projection_data(chart_data, plan, entities)
        title = f"{title} (Projection)" if 'Projection' not in title else title

    return {
        'type': chart_type,
        'title': title,
        'data': chart_data,
        'xKey': 'name',
        'yKey': 'value',
        'colors': colors,
        'isProjection': is_projection
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
    from datetime import datetime, date

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
        elif isinstance(value, (datetime, date)):
            # Datetime objects are treated as string labels (will be converted to string for display)
            all_numeric = False
        else:
            # Try to check if it's a pandas Timestamp or similar
            type_name = type(value).__name__.lower()
            if 'timestamp' in type_name or 'datetime' in type_name or 'date' in type_name:
                all_numeric = False  # Treat as string label
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
    from datetime import datetime, date

    formatted = []

    for i, row in enumerate(data):
        # Get the label
        if dimension_col:
            name = row.get(dimension_col, '')
        elif labels and i < len(labels):
            name = labels[i]
        else:
            name = f"Item {i + 1}"

        # Convert datetime/date objects to readable strings
        if isinstance(name, (datetime, date)):
            name = name.strftime('%b %Y') if hasattr(name, 'strftime') else str(name)
        elif hasattr(name, '__class__') and 'timestamp' in name.__class__.__name__.lower():
            # Handle pandas Timestamp
            try:
                name = name.strftime('%b %Y')
            except:
                name = str(name)

        # Get the value
        value = row.get(metric_col, 0)

        # Convert to number if needed
        if isinstance(value, str):
            try:
                value = float(value.replace(',', ''))
            except (ValueError, AttributeError):
                value = 0  # Default to 0 if conversion fails

        # Round floats
        if isinstance(value, float):
            value = round(value, 2)

        formatted.append({
            'name': str(name) if name else f"Item {i + 1}",
            'value': value
        })

    return formatted


def _mark_projection_data(
    chart_data: List[Dict],
    plan: Dict[str, Any],
    entities: Dict[str, Any] = None
) -> List[Dict]:
    """
    Mark projected data points in the chart data.

    For projection queries, determines which data points are actual historical data
    vs projected/forecasted data and marks them accordingly.

    The frontend will render projected points with dotted lines.
    """
    if not chart_data or len(chart_data) < 2:
        return chart_data

    # Check analysis for explicit projection boundary
    analysis = plan.get('analysis', {})
    projection_start_index = analysis.get('projection_start_index')
    actual_count = analysis.get('actual_data_count')

    if projection_start_index is not None:
        # Use explicit boundary from analysis
        split_index = projection_start_index
    elif actual_count is not None:
        # Use actual data count from analysis
        split_index = actual_count
    else:
        # Default: assume last 30% is projected (typical forecast pattern)
        # Or if only 2-3 points, the last one is projected
        if len(chart_data) <= 3:
            split_index = len(chart_data) - 1
        else:
            split_index = int(len(chart_data) * 0.7)

    # Mark projected data points
    marked_data = []
    for i, point in enumerate(chart_data):
        new_point = point.copy()
        new_point['projected'] = i >= split_index
        marked_data.append(new_point)

    projected_count = len([p for p in marked_data if p.get('projected')])
    print(f"[Viz] Marked {projected_count}/{len(marked_data)} points as projected (split at index {split_index})")

    return marked_data


def _get_chart_type(query_type: str, plan: Dict[str, Any]) -> str:
    """Determine the best chart type for the query."""

    type_map = {
        'comparison': 'bar',
        'trend': 'line',
        'percentage': 'pie',
        'rank': 'horizontal_bar',
        'aggregation_on_subset': 'bar',
        'extrema_lookup': 'bar',
        'projection': 'line',  # Projections always use line charts
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
