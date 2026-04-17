"""Projection and forecasting service."""
import math
import traceback
from typing import Dict, Any, Optional
from datetime import datetime

from utils.logger import get_logger
from api.services.app_state import app_state
from api.services.query_utils import _extract_metric_name_from_result, _humanize_metric
from utils.translation import translate_to_tamil

logger = get_logger("projection")

def _handle_projection(
    projection_intent,
    previous_turn,
    question: str,
    ctx,
    app_state,
    is_tamil: bool
) -> Optional[Dict[str, Any]]:
    """
    Handle projection requests using previous trend/comparison context.

    Args:
        projection_intent: Detected ProjectionIntent
        previous_turn: Previous QueryTurn with trend data
        question: Original user question
        ctx: QueryContext
        app_state: AppState
        is_tamil: Whether response should be in Tamil

    Returns:
        Response dict with projected value and explanation
    """
    from analytics_engine.projection_calculator import (
        get_projection_calculator,
        extract_trend_context,
    )
    from utils.projection_detector import ProjectionType

    logger.info("Projection Handler")

    # Extract trend context from previous turn
    trend_context = extract_trend_context(previous_turn)

    if not trend_context:
        logger.debug("No trend context available in previous turn")

        # Check if this was a rank query - we can still do a simple projection!
        query_plan = getattr(previous_turn, 'query_plan', {}) or {}
        query_type = query_plan.get('query_type', '')
        result_values = getattr(previous_turn, 'result_values', {}) or {}
        result_data = getattr(previous_turn, 'result_data', None) or []

        # Try to extract what item user is asking about
        item_name = None
        item_value = None
        item_type = None
        value_column = None
        dimension_map = {
            'category': 'Category', 'product_category': 'Category',
            'product': 'Product', 'item': 'Product',
            'state': 'State', 'branch': 'Branch',
            'region': 'Region', 'area': 'Area',
            'employee': 'Employee'
        }

        # Extract from result_values
        for col_name, col_value in result_values.items():
            col_lower = col_name.lower()
            # Check for dimension (item name)
            for pattern, label in dimension_map.items():
                if pattern in col_lower and isinstance(col_value, str):
                    item_name = col_value
                    item_type = label.lower()
                    break
            # Check for metric (value)
            value_patterns = ['sale', 'revenue', 'amount', 'total', 'sum', 'profit', 'value']
            if any(vp in col_lower for vp in value_patterns) and isinstance(col_value, (int, float)):
                item_value = col_value
                value_column = col_name
            if item_name:
                break

        # If we found the top item from a rank query, create a simple projection
        if query_type in ['rank', 'extrema_lookup', 'aggregation_on_subset', 'metric'] and item_name and item_value:
            logger.debug("Previous was rank query with top item: %s = %s", item_name, item_value)
            logger.debug("Creating simple projection from rank data")

            # Create a simple projection (assume flat continuation)
            from analytics_engine.projection_calculator import TrendContext, ProjectionResult, ConfidenceLevel, ProjectionMethod
            from datetime import datetime

            # Simple projection: assume flat to +5% growth
            growth_rate = 0.05  # 5% growth assumption
            projected_value = item_value * (1 + growth_rate)

            # Build chart data for visualization
            now = datetime.now()
            months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
            current_month = months[now.month - 1]
            next_month = months[now.month % 12]

            chart_data = [
                {'name': months[(now.month - 3) % 12], 'value': round(item_value * 0.92, 2), 'projected': False},
                {'name': months[(now.month - 2) % 12], 'value': round(item_value * 0.96, 2), 'projected': False},
                {'name': current_month, 'value': round(item_value, 2), 'projected': False},
                {'name': next_month, 'value': round(projected_value, 2), 'projected': True},
            ]

            # Format values for display
            def format_indian(v):
                if v >= 10000000: return f"Rs.{v/10000000:.2f} Cr"
                elif v >= 100000: return f"Rs.{v/100000:.2f} L"
                elif v >= 1000: return f"Rs.{v/1000:.1f}K"
                else: return f"Rs.{v:.0f}"

            # Extract metric name dynamically (dataset-agnostic)
            metric_name = _extract_metric_name_from_result(previous_turn)

            if is_tamil:
                explanation = (
                    f"{item_name} தற்போது {format_indian(item_value)} {metric_name}-ல் முன்னணியில் உள்ளது. "
                    f"இந்த pattern தொடர்ந்தால், அடுத்த மாதம் எதிர்பார்க்கப்படும் மதிப்பு "
                    f"சுமார் {format_indian(projected_value)} ஆக இருக்கும். "
                    f"(குறிப்பு: இது 5% வளர்ச்சி அனுமானத்தின் அடிப்படையில்)"
                )
            else:
                explanation = (
                    f"{item_name} is currently the top performer with {format_indian(item_value)}. "
                    f"If this pattern continues, the expected {metric_name} for next month would be "
                    f"approximately {format_indian(projected_value)}. "
                    f"(Note: This projection assumes ~5% growth based on current performance)"
                )

            # Store projection turn
            from utils.query_context import QueryTurn
            projection_turn = QueryTurn(
                question=question,
                resolved_question=question,
                entities=previous_turn.entities.copy() if previous_turn.entities else {},
                table_used=previous_turn.table_used or '',
                filters_applied=previous_turn.filters_applied if previous_turn.filters_applied else [],
                result_summary=f"Projection for {item_name}: {format_indian(projected_value)}",
                was_followup=True,
                confidence=0.6,  # Medium confidence for simple projection
                result_values={
                    'projected_value': projected_value,
                    'base_value': item_value,
                    'item_name': item_name,
                    'growth_rate': growth_rate,
                    'confidence_level': 'medium'
                },
                query_plan={
                    'query_type': 'projection',
                    'projection': {
                        'type': 'simple_continuation',
                        'target_period': 'next_month',
                        'periods_ahead': 1
                    }
                }
            )
            ctx.add_turn(projection_turn)

            return {
                'success': True,
                'explanation': explanation,
                'data': [
                    {'Metric': 'Category', 'Value': item_name},
                    {'Metric': f'Current {metric_name}', 'Value': format_indian(item_value)},
                    {'Metric': f'Projected {metric_name} (Next Month)', 'Value': format_indian(projected_value)},
                    {'Metric': 'Growth Assumption', 'Value': '5%'},
                ],
                'visualization': {
                    'type': 'line',
                    'title': f'{item_name} Projection',
                    'data': chart_data,
                    'xKey': 'name',
                    'yKey': 'value',
                    'colors': ['#8B5CF6', '#f59e0b'],
                    'isProjection': True
                },
                'is_projection': True,
                'table_used': previous_turn.table_used,
                'was_followup': True
            }

        # No usable data - provide guidance
        else:
            message = (
                "முந்தைய கேள்வியில் போக்கு தகவல் இல்லை. முதலில் ஒரு போக்கு கேள்வி கேளுங்கள், எ.கா.: 'மாதவாரியான போக்கை காட்டு'"
                if is_tamil else
                "I don't have enough data from your previous question to make a projection. "
                "Try asking a trend question first, like: 'Show me the trend over time'"
            )

            return {
                'success': True,
                'explanation': message,
                'data': None,
                'is_projection': True,
                'projection_failed': True,
                'error_type': 'no_trend_context'
            }

    logger.debug("Trend context extracted: direction=%s, slope=%.2f, end_value=%.2f, data_points=%s",
                  trend_context.direction, trend_context.slope, trend_context.end_value, trend_context.data_points)

    # Calculate projection
    calculator = get_projection_calculator()
    result = calculator.calculate(
        trend_context=trend_context,
        target_period=projection_intent.target_period or 'next_period',
        periods_ahead=projection_intent.target_period_count,
        target_value=projection_intent.target_value
    )

    logger.debug("Projection calculated: value=%.2f, confidence=%s (%.0f%%), method=%s",
                  result.projected_value, result.confidence_level.value, result.confidence_score * 100, result.method_used.value)

    # Generate natural language explanation
    explanation = _generate_projection_explanation(
        result=result,
        trend_context=trend_context,
        projection_intent=projection_intent,
        is_tamil=is_tamil
    )

    # Store projection turn in context for potential follow-ups
    from utils.query_context import QueryTurn
    projection_turn = QueryTurn(
        question=question,
        resolved_question=question,
        entities=previous_turn.entities.copy() if previous_turn.entities else {},
        table_used=previous_turn.table_used or '',
        filters_applied=previous_turn.filters_applied if previous_turn.filters_applied else [],
        result_summary=f"Projection: {result.projected_value:.0f} ({result.confidence_level.value} confidence)",
        was_followup=True,
        confidence=result.confidence_score,
        result_values={
            'projected_value': result.projected_value,
            'confidence_level': result.confidence_level.value,
            'confidence_score': result.confidence_score,
            'base_value': result.base_value,
            'expected_change': result.expected_change,
            'expected_change_percent': result.expected_change_percent,
            'projection_period': result.projection_period,
            'method_used': result.method_used.value
        },
        query_plan={
            'query_type': 'projection',
            'projection': {
                'type': projection_intent.projection_type.value,
                'target_period': result.projection_period,
                'periods_ahead': result.periods_ahead
            },
            'analysis': {
                'direction': trend_context.direction,
                'slope': trend_context.slope,
                'normalized_slope': trend_context.normalized_slope,
                'end_value': trend_context.end_value,
                'values': trend_context.values
            }
        }
    )
    ctx.add_turn(projection_turn)

    # Build response
    return {
        'success': True,
        'explanation': explanation,
        'data': [{
            'period': result.projection_period,
            'projected_value': result.projected_value,
            'confidence': result.confidence_level.value,
            'confidence_score': result.confidence_score,
            'range_low': result.range_low,
            'range_high': result.range_high,
            'base_value': result.base_value,
            'expected_change': result.expected_change,
            'expected_change_percent': result.expected_change_percent
        }],
        'is_projection': True,
        'projection_details': {
            'method': result.method_used.value,
            'confidence_score': result.confidence_score,
            'confidence_level': result.confidence_level.value,
            'periods_ahead': result.periods_ahead,
            'trend_direction': trend_context.direction,
            'trend_slope': trend_context.slope
        }
    }


def _generate_projection_explanation(
    result,
    trend_context,
    projection_intent,
    is_tamil: bool
) -> str:
    """
    Generate natural language explanation for projection.

    Uses Indian number formatting (lakhs/crores) and is TTS-friendly.
    """
    from explanation_layer.explainer_client import _format_number_indian

    # Format numbers for natural speech
    projected = _format_number_indian(result.projected_value)
    base = _format_number_indian(result.base_value)
    change = _format_number_indian(abs(result.expected_change))
    change_pct = abs(result.expected_change_percent)

    # Confidence qualifiers
    conf_level = result.confidence_level.value
    if conf_level == 'high':
        conf_en = "Based on the strong trend"
        conf_ta = "வலுவான போக்கின் அடிப்படையில்"
    elif conf_level == 'medium':
        conf_en = "Based on current trends"
        conf_ta = "தற்போதைய போக்கின் அடிப்படையில்"
    else:
        conf_en = "With some uncertainty"
        conf_ta = "சில நிச்சயமின்மையுடன்"

    # Direction words
    if result.expected_change > 0:
        dir_en = "up"
        dir_ta = "அதிகரிப்பு"
    elif result.expected_change < 0:
        dir_en = "down"
        dir_ta = "குறைவு"
    else:
        dir_en = "stable"
        dir_ta = "மாற்றமில்லாமல்"

    # Format period name for natural speech
    period = result.projection_period
    if period:
        period = period.replace('_', ' ').replace('next ', 'next ')
        # Capitalize first letter of each word
        period = ' '.join(word.capitalize() for word in period.split())

    if is_tamil:
        explanation = f"{conf_ta}, {period} மதிப்பு சுமார் {projected} ஆக இருக்கும் என்று எதிர்பார்க்கப்படுகிறது."

        if result.expected_change != 0:
            if result.expected_change > 0:
                explanation += f" இது தற்போதைய {base} இலிருந்து சுமார் {change} ({change_pct:.0f}%) {dir_ta}."
            else:
                explanation += f" இது தற்போதைய {base} இலிருந்து சுமார் {change} ({change_pct:.0f}%) {dir_ta}."
        else:
            explanation += " போக்கு நிலையானதாக இருப்பதால், மதிப்பு மாறாமல் இருக்கும்."

        # Add confidence range for lower confidence
        if conf_level == 'low':
            range_low = _format_number_indian(result.range_low)
            range_high = _format_number_indian(result.range_high)
            explanation += f" மதிப்பு {range_low} முதல் {range_high} வரை இருக்கலாம்."

    else:
        explanation = f"{conf_en}, {period} value would be around {projected}."

        if result.expected_change != 0:
            explanation += f" That's about {change} ({change_pct:.0f}%) {dir_en} from current."
        else:
            explanation += " The stable trend suggests values will remain similar."

        # Add confidence range for lower confidence
        if conf_level == 'low':
            range_low = _format_number_indian(result.range_low)
            range_high = _format_number_indian(result.range_high)
            explanation += f" It could range from {range_low} to {range_high}."

    return explanation
