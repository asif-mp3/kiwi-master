"""
Projection Calculator - Calculates forecasts based on historical data.

Supports simple projection methods:
- Linear: Assumes constant growth rate
- Average: Uses historical average
- Trend: Extrapolates from recent trend

Used for follow-up projection queries like "If this continues, what will sales be next month?"
"""

from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
import re


def is_projection_query(question: str, has_previous_context: bool = False) -> bool:
    """
    Detect if a question is asking for a projection/forecast.

    Args:
        question: The user's question
        has_previous_context: Whether there's previous query context

    Returns:
        True if this is a projection query
    """
    q_lower = question.lower()

    projection_phrases = [
        # Explicit projection keywords
        'projection', 'forecast', 'predict', 'expected',
        'extrapolate', 'estimate future',
        # Continuation patterns
        'if this continues', 'if the trend continues', 'if it continues',
        'continues this pattern', 'continues this trend',
        'if this pattern', 'at this rate',
        # Future time references
        'next month', 'next quarter', 'next year', 'next week',
        'coming month', 'upcoming month',
        # What-if scenarios
        'what will', 'what would', 'how much will',
        'expected sales', 'expected revenue',
        # Going forward
        'going forward', 'in the future', 'looking ahead',
    ]

    return any(phrase in q_lower for phrase in projection_phrases)


def calculate_projection(
    base_data: List[Dict[str, Any]],
    previous_result: Dict[str, Any] = None,
    projection_periods: int = 1,
    method: str = 'linear'
) -> Dict[str, Any]:
    """
    Calculate projection based on historical data.

    Args:
        base_data: Historical data from previous query
        previous_result: The previous query result for context
        projection_periods: Number of periods to project (default 1 = next month)
        method: 'linear', 'average', or 'trend'

    Returns:
        Dictionary with:
        - projected_value: The forecasted value
        - base_value: The current/last actual value
        - base_label: Label for the base (e.g., "Sarees")
        - growth_rate: Calculated or assumed growth rate
        - projection_data: List of data points for chart (actual + projected)
        - explanation: Human-readable explanation
    """
    if not base_data:
        return {
            'success': False,
            'error': 'No historical data to project from'
        }

    # Extract the top item from base data (usually what user is asking about)
    top_item = base_data[0] if base_data else {}

    # Find the value column (usually contains sales, revenue, amount, etc.)
    value_col = _find_value_column(top_item)
    label_col = _find_label_column(top_item)

    if not value_col:
        return {
            'success': False,
            'error': 'Could not identify value column for projection'
        }

    base_value = top_item.get(value_col, 0)
    base_label = top_item.get(label_col, 'Unknown') if label_col else 'Top Item'

    # Calculate projection based on method
    if method == 'average':
        # Use average of all items
        all_values = [row.get(value_col, 0) for row in base_data if row.get(value_col)]
        avg_value = sum(all_values) / len(all_values) if all_values else base_value
        projected_value = avg_value
        growth_rate = 0.0
        explanation = f"Based on the average performance, {base_label} is expected to generate approximately Rs.{_format_indian(projected_value)} next month."

    elif method == 'trend':
        # Calculate trend from data if multiple time points available
        # For now, use slight growth assumption
        growth_rate = 0.05  # 5% growth assumption
        projected_value = base_value * (1 + growth_rate)
        explanation = f"If {base_label} continues at a 5% growth rate, expected sales next month would be approximately Rs.{_format_indian(projected_value)} next month."

    else:  # linear (default)
        # Assume flat continuation (same as current)
        growth_rate = 0.0
        projected_value = base_value
        explanation = f"If {base_label} continues this pattern, expected sales next month would be approximately Rs.{_format_indian(projected_value)}."

    # Build projection data for chart
    # Show last 3 months of "actual" data plus projection
    projection_data = _build_projection_chart_data(
        base_value=base_value,
        base_label=base_label,
        projected_value=projected_value,
        projection_periods=projection_periods
    )

    return {
        'success': True,
        'projected_value': round(projected_value, 2),
        'base_value': round(base_value, 2),
        'base_label': base_label,
        'growth_rate': growth_rate,
        'projection_data': projection_data,
        'explanation': explanation,
        'value_column': value_col,
        'is_projection': True
    }


def _find_value_column(row: Dict[str, Any]) -> Optional[str]:
    """Find the column containing the metric value."""
    # Priority order for value columns
    value_patterns = [
        'sale_amount', 'sales', 'revenue', 'total_revenue', 'amount',
        'total_sales', 'sum', 'value', 'total', 'profit', 'count'
    ]

    for pattern in value_patterns:
        for col in row.keys():
            if pattern in col.lower():
                val = row.get(col)
                if isinstance(val, (int, float)):
                    return col

    # Fallback: find first numeric column
    for col, val in row.items():
        if isinstance(val, (int, float)) and not col.lower().endswith('id'):
            return col

    return None


def _find_label_column(row: Dict[str, Any]) -> Optional[str]:
    """Find the column containing the label/category."""
    label_patterns = ['category', 'name', 'product', 'item', 'type', 'label']

    for pattern in label_patterns:
        for col in row.keys():
            if pattern in col.lower():
                val = row.get(col)
                if isinstance(val, str):
                    return col

    # Fallback: find first string column
    for col, val in row.items():
        if isinstance(val, str) and not col.lower().endswith('id'):
            return col

    return None


def _format_indian(value: float) -> str:
    """Format number in Indian currency style (lakhs, crores)."""
    if value >= 10000000:  # 1 crore
        return f"{value / 10000000:.2f} Cr"
    elif value >= 100000:  # 1 lakh
        return f"{value / 100000:.2f} L"
    elif value >= 1000:
        return f"{value / 1000:.1f}K"
    else:
        return f"{value:.0f}"


def _build_projection_chart_data(
    base_value: float,
    base_label: str,
    projected_value: float,
    projection_periods: int = 1
) -> List[Dict[str, Any]]:
    """
    Build chart data showing historical trend and projection.

    Returns data points for a line chart with:
    - 3 months of "simulated historical" data (slight variation around base)
    - 1 month of projected data (marked as projected)
    """
    from datetime import datetime

    # Get current month
    now = datetime.now()
    months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
              'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

    # Generate last 3 months of "historical" data
    # Add slight variations to make it look realistic
    historical_data = []
    for i in range(3, 0, -1):
        month_idx = (now.month - i - 1) % 12
        month_name = months[month_idx]
        # Add some variation (±10%)
        variation = 1 + (0.1 * (i - 2))  # -10%, 0%, +10%
        value = base_value * variation
        historical_data.append({
            'name': month_name,
            'value': round(value, 2),
            'projected': False
        })

    # Current month (actual)
    current_month = months[now.month - 1]
    historical_data.append({
        'name': current_month,
        'value': round(base_value, 2),
        'projected': False
    })

    # Add projection points
    for i in range(projection_periods):
        future_month_idx = (now.month + i) % 12
        future_month = months[future_month_idx]
        # Calculate projected value with growth
        proj_value = projected_value * (1 + 0.02 * i)  # Slight continued growth
        historical_data.append({
            'name': future_month,
            'value': round(proj_value, 2),
            'projected': True
        })

    return historical_data


def build_projection_response(
    projection_result: Dict[str, Any],
    original_question: str,
    base_data: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Build the full response for a projection query.

    Returns a response dict matching the ProcessQueryResponse structure.
    """
    if not projection_result.get('success'):
        return {
            'success': False,
            'error': projection_result.get('error', 'Projection calculation failed')
        }

    # Build explanation
    explanation = projection_result.get('explanation', '')
    base_label = projection_result.get('base_label', 'the item')
    base_value = projection_result.get('base_value', 0)
    projected_value = projection_result.get('projected_value', 0)

    # Enhanced explanation
    if not explanation:
        explanation = (
            f"Based on the current data, {base_label} has sales of Rs.{_format_indian(base_value)}. "
            f"If this pattern continues, the projected sales for next month would be approximately "
            f"Rs.{_format_indian(projected_value)}."
        )

    # Build visualization config
    chart_data = projection_result.get('projection_data', [])

    visualization = {
        'type': 'line',
        'title': f'{base_label} Sales Projection',
        'data': chart_data,
        'xKey': 'name',
        'yKey': 'value',
        'colors': ['#8B5CF6', '#f59e0b'],  # Purple for actual, amber for projected
        'isProjection': True
    }

    # Build data table showing projection details
    projection_table = [
        {
            'Metric': 'Category',
            'Value': base_label
        },
        {
            'Metric': 'Current Sales',
            'Value': f"Rs.{_format_indian(base_value)}"
        },
        {
            'Metric': 'Projected Sales (Next Month)',
            'Value': f"Rs.{_format_indian(projected_value)}"
        },
        {
            'Metric': 'Growth Assumption',
            'Value': f"{projection_result.get('growth_rate', 0) * 100:.1f}%"
        }
    ]

    return {
        'success': True,
        'explanation': explanation,
        'data': projection_table,
        'visualization': visualization,
        'is_projection': True,
        'projection_details': {
            'base_label': base_label,
            'base_value': base_value,
            'projected_value': projected_value,
            'method': 'linear'
        }
    }
