"""
Visualization Helper - Determines chart type and formats data for frontend charts.

Maps query types to appropriate visualizations:
- comparison → bar chart
- trend → line chart
- percentage → pie/donut chart
- aggregation_on_subset → bar chart
- rank → horizontal bar chart
- metric (single value) → no chart (just number)
- list/filter/lookup → table (no chart)
"""

from typing import Dict, Any, List, Optional
import pandas as pd


def determine_visualization(
    query_plan: Dict[str, Any],
    result_data: List[Dict],
    entities: Dict[str, Any] = None
) -> Optional[Dict[str, Any]]:
    """
    Determine the appropriate visualization for query results.

    Args:
        query_plan: The executed query plan with query_type
        result_data: List of result dictionaries
        entities: Extracted entities from the question

    Returns:
        Visualization config dict or None if table is more appropriate
        {
            "type": "bar" | "line" | "pie" | "horizontal_bar",
            "title": str,
            "data": [...],  # Formatted for Recharts
            "xKey": str,    # X-axis data key
            "yKey": str,    # Y-axis data key (or list for multi-series)
            "colors": [...]  # Chart colors
        }
    """
    if not result_data or len(result_data) == 0:
        return None

    query_type = query_plan.get('query_type', '')

    # Query types that are better as tables
    table_only_types = ['lookup', 'filter', 'list']
    if query_type in table_only_types:
        return None

    # Single row results - no chart needed
    if len(result_data) == 1 and query_type == 'metric':
        return None

    # Need at least 2 data points for meaningful visualization
    if len(result_data) < 2:
        return None

    # Determine chart type based on query_type
    chart_config = _get_chart_config(query_type, query_plan, result_data, entities)

    return chart_config


def _get_chart_config(
    query_type: str,
    plan: Dict[str, Any],
    data: List[Dict],
    entities: Dict[str, Any] = None
) -> Optional[Dict[str, Any]]:
    """Get chart configuration based on query type."""

    # Get column names from data
    if not data:
        return None
    columns = list(data[0].keys())

    # Identify dimension (x-axis) and metric (y-axis) columns
    dimension_col = _find_dimension_column(columns, plan)
    metric_col = _find_metric_column(columns, plan)

    if not dimension_col or not metric_col:
        return None

    # Default colors (purple theme to match Thara.ai)
    colors = ['#8B5CF6', '#A78BFA', '#7C3AED', '#6D28D9', '#5B21B6', '#4C1D95']

    # Comparison queries → Bar chart
    if query_type == 'comparison':
        return {
            'type': 'bar',
            'title': _generate_title(plan, entities),
            'data': _format_chart_data(data, dimension_col, metric_col),
            'xKey': 'name',
            'yKey': 'value',
            'colors': colors
        }

    # Trend queries → Line chart
    elif query_type == 'trend':
        return {
            'type': 'line',
            'title': _generate_title(plan, entities),
            'data': _format_chart_data(data, dimension_col, metric_col),
            'xKey': 'name',
            'yKey': 'value',
            'colors': colors
        }

    # Percentage queries → Pie chart
    elif query_type == 'percentage':
        return {
            'type': 'pie',
            'title': _generate_title(plan, entities),
            'data': _format_pie_data(data, dimension_col, metric_col),
            'colors': colors
        }

    # Rank queries → Horizontal bar chart
    elif query_type == 'rank':
        return {
            'type': 'horizontal_bar',
            'title': _generate_title(plan, entities),
            'data': _format_chart_data(data, dimension_col, metric_col),
            'xKey': 'name',
            'yKey': 'value',
            'colors': colors
        }

    # Aggregation on subset → Bar chart
    elif query_type == 'aggregation_on_subset':
        return {
            'type': 'bar',
            'title': _generate_title(plan, entities),
            'data': _format_chart_data(data, dimension_col, metric_col),
            'xKey': 'name',
            'yKey': 'value',
            'colors': colors
        }

    # Extrema lookup with multiple results → Bar chart
    elif query_type == 'extrema_lookup' and len(data) > 1:
        return {
            'type': 'bar',
            'title': _generate_title(plan, entities),
            'data': _format_chart_data(data, dimension_col, metric_col),
            'xKey': 'name',
            'yKey': 'value',
            'colors': colors
        }

    # Metric with grouping → Bar chart
    elif query_type == 'metric' and plan.get('group_by'):
        return {
            'type': 'bar',
            'title': _generate_title(plan, entities),
            'data': _format_chart_data(data, dimension_col, metric_col),
            'xKey': 'name',
            'yKey': 'value',
            'colors': colors
        }

    return None


def _find_dimension_column(columns: List[str], plan: Dict[str, Any]) -> Optional[str]:
    """Find the dimension column (category/x-axis)."""
    # Check group_by first
    group_by = plan.get('group_by', [])
    if group_by:
        return group_by[0] if isinstance(group_by, list) else group_by

    # Common dimension patterns
    dimension_patterns = [
        'month', 'date', 'day', 'year', 'period', 'time',
        'category', 'type', 'group', 'segment',
        'location', 'city', 'state', 'region', 'area', 'branch',
        'product', 'item', 'name', 'department'
    ]

    for col in columns:
        col_lower = col.lower()
        for pattern in dimension_patterns:
            if pattern in col_lower:
                return col

    # Return first non-numeric column
    return columns[0] if columns else None


def _find_metric_column(columns: List[str], plan: Dict[str, Any]) -> Optional[str]:
    """Find the metric column (value/y-axis)."""
    # Check metrics from plan
    metrics = plan.get('metrics', [])
    if metrics:
        metric = metrics[0] if isinstance(metrics, list) else metrics
        # Find matching column
        for col in columns:
            if metric.lower() in col.lower():
                return col

    # Common metric patterns
    metric_patterns = [
        'total', 'sum', 'count', 'amount', 'value',
        'sales', 'revenue', 'profit', 'quantity',
        'average', 'avg', 'max', 'min'
    ]

    for col in columns:
        col_lower = col.lower()
        for pattern in metric_patterns:
            if pattern in col_lower:
                return col

    # Return last column (often the metric)
    return columns[-1] if len(columns) > 1 else None


def _format_chart_data(
    data: List[Dict],
    dimension_col: str,
    metric_col: str
) -> List[Dict]:
    """Format data for Recharts bar/line charts."""
    formatted = []
    for row in data:
        name = row.get(dimension_col, '')
        value = row.get(metric_col, 0)

        # Handle numeric conversion
        if isinstance(value, str):
            try:
                value = float(value.replace(',', ''))
            except:
                value = 0

        formatted.append({
            'name': str(name),
            'value': round(value, 2) if isinstance(value, float) else value
        })

    return formatted


def _format_pie_data(
    data: List[Dict],
    dimension_col: str,
    metric_col: str
) -> List[Dict]:
    """Format data for Recharts pie chart."""
    formatted = []
    for row in data:
        name = row.get(dimension_col, '')
        value = row.get(metric_col, 0)

        # Handle numeric conversion
        if isinstance(value, str):
            try:
                value = float(value.replace(',', ''))
            except:
                value = 0

        formatted.append({
            'name': str(name),
            'value': round(value, 2) if isinstance(value, float) else value
        })

    return formatted


def _generate_title(plan: Dict[str, Any], entities: Dict[str, Any] = None) -> str:
    """Generate a descriptive title for the chart."""
    query_type = plan.get('query_type', '')
    metrics = plan.get('metrics', [])
    group_by = plan.get('group_by', [])

    metric_name = metrics[0] if metrics else 'Value'
    dimension = group_by[0] if group_by else ''

    # Build title based on query type
    if query_type == 'comparison':
        return f"{metric_name} Comparison"
    elif query_type == 'trend':
        return f"{metric_name} Trend"
    elif query_type == 'percentage':
        return f"{metric_name} Distribution"
    elif query_type == 'rank':
        return f"Top {dimension} by {metric_name}"
    else:
        if dimension:
            return f"{metric_name} by {dimension}"
        return f"{metric_name}"
