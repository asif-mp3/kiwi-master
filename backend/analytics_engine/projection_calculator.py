"""
Projection Calculator for Thara AI

Calculates projections/forecasts using multiple methods:
- Linear Regression (simple extrapolation)
- Moving Average with Momentum
- Exponential Smoothing (Holt method)
- Momentum (for limited data)
- Hybrid (weighted average of methods)

Includes confidence scoring based on:
- Data consistency (variance)
- Number of data points
- Trend strength
- Projection distance
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
import statistics
import math


class ProjectionMethod(Enum):
    """Methods for calculating projections"""
    LINEAR_REGRESSION = "linear_regression"
    MOVING_AVERAGE = "moving_average"
    EXPONENTIAL_SMOOTHING = "exponential_smoothing"
    MOMENTUM = "momentum"
    HYBRID = "hybrid"


class ConfidenceLevel(Enum):
    """Confidence levels for projections"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class TrendContext:
    """Context extracted from previous trend query"""
    direction: str              # "increasing", "decreasing", "stable"
    slope: float               # Rate of change per period
    normalized_slope: float    # Percentage change per period
    start_value: float
    end_value: float
    percentage_change: float
    data_points: int
    min_value: float
    max_value: float
    avg_value: float
    confidence: str            # From trend analysis ("high", "medium", "low")
    time_unit: str             # "month", "week", "day", "quarter"
    values: List[float]        # Historical values for advanced methods


@dataclass
class ProjectionResult:
    """Result of a projection calculation"""
    projected_value: float
    confidence_level: ConfidenceLevel
    confidence_score: float         # 0.0 to 1.0
    method_used: ProjectionMethod
    projection_period: str          # "January", "next_month", etc.
    periods_ahead: int

    # Additional context for explanation
    base_value: float              # Starting point for projection
    expected_change: float         # Projected change from base
    expected_change_percent: float
    range_low: float               # Confidence interval low
    range_high: float              # Confidence interval high

    # Method-specific details
    method_details: Dict[str, Any] = field(default_factory=dict)

    # For goal-based projections
    periods_to_goal: Optional[int] = None
    goal_reachable: Optional[bool] = None


class ProjectionCalculator:
    """
    Calculate projections using multiple methods.
    Selects best method based on data characteristics.
    """

    def __init__(self):
        # Minimum data points for each method
        self.min_points = {
            ProjectionMethod.LINEAR_REGRESSION: 3,
            ProjectionMethod.MOVING_AVERAGE: 4,
            ProjectionMethod.EXPONENTIAL_SMOOTHING: 5,
            ProjectionMethod.MOMENTUM: 2,
        }

    def calculate(
        self,
        trend_context: TrendContext,
        target_period: str,
        periods_ahead: int = 1,
        target_value: Optional[float] = None
    ) -> ProjectionResult:
        """
        Calculate projection based on trend context.

        Args:
            trend_context: Extracted trend data from previous query
            target_period: Human-readable target period ("January", "next_month")
            periods_ahead: Number of periods to project
            target_value: For goal-based projections, the target to reach

        Returns:
            ProjectionResult with projected value and confidence
        """

        # Select best method based on data
        method = self._select_method(trend_context)

        # Calculate projection
        if method == ProjectionMethod.LINEAR_REGRESSION:
            result = self._linear_regression_projection(
                trend_context, target_period, periods_ahead
            )
        elif method == ProjectionMethod.MOVING_AVERAGE:
            result = self._moving_average_projection(
                trend_context, target_period, periods_ahead
            )
        elif method == ProjectionMethod.EXPONENTIAL_SMOOTHING:
            result = self._exponential_smoothing_projection(
                trend_context, target_period, periods_ahead
            )
        elif method == ProjectionMethod.MOMENTUM:
            result = self._momentum_projection(
                trend_context, target_period, periods_ahead
            )
        else:
            result = self._hybrid_projection(
                trend_context, target_period, periods_ahead
            )

        # Add goal analysis if target_value provided
        if target_value is not None:
            result = self._add_goal_analysis(result, trend_context, target_value)

        return result

    def _select_method(self, context: TrendContext) -> ProjectionMethod:
        """Select best projection method based on data characteristics"""

        n_points = context.data_points

        # Not enough data - use simple momentum
        if n_points < 3:
            return ProjectionMethod.MOMENTUM

        # Check for consistency (variance) if we have values
        if context.values and len(context.values) >= 3:
            try:
                cv = statistics.stdev(context.values) / context.avg_value if context.avg_value != 0 else 0
            except statistics.StatisticsError:
                cv = 0

            # High consistency (low CV) - linear regression works well
            if cv < 0.15:
                return ProjectionMethod.LINEAR_REGRESSION

            # Medium consistency - use moving average
            if cv < 0.30:
                return ProjectionMethod.MOVING_AVERAGE

            # High volatility - use exponential smoothing if enough data
            if n_points >= 5:
                return ProjectionMethod.EXPONENTIAL_SMOOTHING

        # Default to linear regression for moderate data
        if n_points >= 4:
            return ProjectionMethod.HYBRID

        return ProjectionMethod.LINEAR_REGRESSION

    def _linear_regression_projection(
        self,
        context: TrendContext,
        target_period: str,
        periods_ahead: int
    ) -> ProjectionResult:
        """Simple linear regression extrapolation"""

        # Project using slope
        projected_value = context.end_value + (context.slope * periods_ahead)

        # Ensure non-negative for typical business metrics
        projected_value = max(0, projected_value)

        expected_change = projected_value - context.end_value

        # Calculate confidence based on trend strength and consistency
        confidence_score = self._calculate_confidence(
            context, ProjectionMethod.LINEAR_REGRESSION, periods_ahead
        )
        confidence_level = self._score_to_level(confidence_score)

        # Confidence interval (rough estimate: +/- based on volatility)
        if context.values and len(context.values) >= 2:
            try:
                std_dev = statistics.stdev(context.values)
                margin = std_dev * 1.5 * math.sqrt(periods_ahead)
            except statistics.StatisticsError:
                margin = abs(expected_change * 0.5)
        else:
            margin = abs(expected_change * 0.5)

        range_low = max(0, projected_value - margin)
        range_high = projected_value + margin

        return ProjectionResult(
            projected_value=projected_value,
            confidence_level=confidence_level,
            confidence_score=confidence_score,
            method_used=ProjectionMethod.LINEAR_REGRESSION,
            projection_period=target_period,
            periods_ahead=periods_ahead,
            base_value=context.end_value,
            expected_change=expected_change,
            expected_change_percent=(expected_change / context.end_value * 100)
                                    if context.end_value != 0 else 0,
            range_low=range_low,
            range_high=range_high,
            method_details={
                'slope': context.slope,
                'normalized_slope': context.normalized_slope,
                'trend_direction': context.direction
            }
        )

    def _moving_average_projection(
        self,
        context: TrendContext,
        target_period: str,
        periods_ahead: int
    ) -> ProjectionResult:
        """Moving average with momentum adjustment"""

        if not context.values or len(context.values) < 3:
            # Fall back to linear
            return self._linear_regression_projection(
                context, target_period, periods_ahead
            )

        # Calculate recent moving average (last 3 periods)
        window_size = min(3, len(context.values))
        recent_avg = sum(context.values[-window_size:]) / window_size

        # Calculate momentum (average period-over-period change)
        changes = [
            context.values[i] - context.values[i-1]
            for i in range(1, len(context.values))
        ]
        avg_change = sum(changes) / len(changes) if changes else 0

        # Project with momentum
        projected_value = recent_avg + (avg_change * periods_ahead)
        projected_value = max(0, projected_value)

        expected_change = projected_value - context.end_value

        confidence_score = self._calculate_confidence(
            context, ProjectionMethod.MOVING_AVERAGE, periods_ahead
        )
        confidence_level = self._score_to_level(confidence_score)

        # Wider confidence interval for MA
        if len(changes) >= 2:
            try:
                change_std = statistics.stdev(changes)
                margin = change_std * 2 * math.sqrt(periods_ahead)
            except statistics.StatisticsError:
                margin = abs(expected_change * 0.6)
        else:
            margin = abs(expected_change * 0.6)

        range_low = max(0, projected_value - margin)
        range_high = projected_value + margin

        return ProjectionResult(
            projected_value=projected_value,
            confidence_level=confidence_level,
            confidence_score=confidence_score,
            method_used=ProjectionMethod.MOVING_AVERAGE,
            projection_period=target_period,
            periods_ahead=periods_ahead,
            base_value=context.end_value,
            expected_change=expected_change,
            expected_change_percent=(expected_change / context.end_value * 100)
                                    if context.end_value != 0 else 0,
            range_low=range_low,
            range_high=range_high,
            method_details={
                'moving_average': recent_avg,
                'avg_change': avg_change,
                'window_size': window_size
            }
        )

    def _exponential_smoothing_projection(
        self,
        context: TrendContext,
        target_period: str,
        periods_ahead: int
    ) -> ProjectionResult:
        """Exponential smoothing (simple Holt method)"""

        if not context.values or len(context.values) < 4:
            return self._linear_regression_projection(
                context, target_period, periods_ahead
            )

        # Simple exponential smoothing parameters
        alpha = 0.3  # Level smoothing
        beta = 0.1   # Trend smoothing

        values = context.values

        # Initialize
        level = values[0]
        trend = (values[1] - values[0]) if len(values) > 1 else 0

        # Fit
        for i in range(1, len(values)):
            prev_level = level
            level = alpha * values[i] + (1 - alpha) * (level + trend)
            trend = beta * (level - prev_level) + (1 - beta) * trend

        # Forecast
        projected_value = level + (trend * periods_ahead)
        projected_value = max(0, projected_value)

        expected_change = projected_value - context.end_value

        confidence_score = self._calculate_confidence(
            context, ProjectionMethod.EXPONENTIAL_SMOOTHING, periods_ahead
        )
        confidence_level = self._score_to_level(confidence_score)

        # Calculate residuals for confidence interval
        fitted_values = []
        fit_level = values[0]
        fit_trend = (values[1] - values[0]) if len(values) > 1 else 0
        for i in range(len(values)):
            fitted_values.append(fit_level + fit_trend)
            if i < len(values) - 1:
                prev_level = fit_level
                fit_level = alpha * values[i] + (1 - alpha) * (fit_level + fit_trend)
                fit_trend = beta * (fit_level - prev_level) + (1 - beta) * fit_trend

        residuals = [abs(values[i] - fitted_values[i]) for i in range(len(values))]
        if residuals:
            margin = sum(residuals) / len(residuals) * 2 * math.sqrt(periods_ahead)
        else:
            margin = abs(expected_change * 0.5)

        range_low = max(0, projected_value - margin)
        range_high = projected_value + margin

        return ProjectionResult(
            projected_value=projected_value,
            confidence_level=confidence_level,
            confidence_score=confidence_score,
            method_used=ProjectionMethod.EXPONENTIAL_SMOOTHING,
            projection_period=target_period,
            periods_ahead=periods_ahead,
            base_value=context.end_value,
            expected_change=expected_change,
            expected_change_percent=(expected_change / context.end_value * 100)
                                    if context.end_value != 0 else 0,
            range_low=range_low,
            range_high=range_high,
            method_details={
                'final_level': level,
                'final_trend': trend,
                'alpha': alpha,
                'beta': beta
            }
        )

    def _momentum_projection(
        self,
        context: TrendContext,
        target_period: str,
        periods_ahead: int
    ) -> ProjectionResult:
        """Simple momentum-based projection (for limited data)"""

        # Use the percentage change as momentum
        if context.percentage_change and context.data_points > 1:
            per_period_change = context.percentage_change / (context.data_points - 1)
            expected_change_pct = per_period_change * periods_ahead
            expected_change = context.end_value * (expected_change_pct / 100)
        else:
            expected_change = context.slope * periods_ahead

        projected_value = context.end_value + expected_change
        projected_value = max(0, projected_value)

        # Lower confidence for simple momentum
        confidence_score = min(0.6, self._calculate_confidence(
            context, ProjectionMethod.MOMENTUM, periods_ahead
        ))
        confidence_level = self._score_to_level(confidence_score)

        margin = abs(expected_change * 0.7)
        range_low = max(0, projected_value - margin)
        range_high = projected_value + margin

        return ProjectionResult(
            projected_value=projected_value,
            confidence_level=confidence_level,
            confidence_score=confidence_score,
            method_used=ProjectionMethod.MOMENTUM,
            projection_period=target_period,
            periods_ahead=periods_ahead,
            base_value=context.end_value,
            expected_change=expected_change,
            expected_change_percent=(expected_change / context.end_value * 100)
                                    if context.end_value != 0 else 0,
            range_low=range_low,
            range_high=range_high,
            method_details={
                'momentum_pct': context.percentage_change,
                'data_points': context.data_points
            }
        )

    def _hybrid_projection(
        self,
        context: TrendContext,
        target_period: str,
        periods_ahead: int
    ) -> ProjectionResult:
        """Weighted average of multiple methods"""

        results = []
        weights = []

        # Get linear regression result
        if context.data_points >= 3:
            lr_result = self._linear_regression_projection(
                context, target_period, periods_ahead
            )
            results.append(lr_result.projected_value)
            weights.append(lr_result.confidence_score)

        # Get moving average result
        if context.values and len(context.values) >= 3:
            ma_result = self._moving_average_projection(
                context, target_period, periods_ahead
            )
            results.append(ma_result.projected_value)
            weights.append(ma_result.confidence_score * 0.9)  # Slightly lower weight

        # Get exponential smoothing if enough data
        if context.values and len(context.values) >= 5:
            es_result = self._exponential_smoothing_projection(
                context, target_period, periods_ahead
            )
            results.append(es_result.projected_value)
            weights.append(es_result.confidence_score * 0.95)

        # Calculate weighted average
        if results and weights:
            total_weight = sum(weights)
            projected_value = sum(r * w for r, w in zip(results, weights)) / total_weight
            confidence_score = sum(weights) / len(weights)
        else:
            # Fall back to momentum
            return self._momentum_projection(context, target_period, periods_ahead)

        projected_value = max(0, projected_value)
        expected_change = projected_value - context.end_value
        confidence_level = self._score_to_level(confidence_score)

        # Tighter confidence interval for hybrid (consensus)
        margin = abs(expected_change * 0.4)
        range_low = max(0, projected_value - margin)
        range_high = projected_value + margin

        return ProjectionResult(
            projected_value=projected_value,
            confidence_level=confidence_level,
            confidence_score=confidence_score,
            method_used=ProjectionMethod.HYBRID,
            projection_period=target_period,
            periods_ahead=periods_ahead,
            base_value=context.end_value,
            expected_change=expected_change,
            expected_change_percent=(expected_change / context.end_value * 100)
                                    if context.end_value != 0 else 0,
            range_low=range_low,
            range_high=range_high,
            method_details={
                'methods_combined': len(results),
                'weights': weights,
                'individual_projections': results
            }
        )

    def _calculate_confidence(
        self,
        context: TrendContext,
        method: ProjectionMethod,
        periods_ahead: int
    ) -> float:
        """Calculate confidence score for projection"""

        score = 0.5  # Base score

        # More data points = higher confidence
        if context.data_points >= 8:
            score += 0.15
        elif context.data_points >= 6:
            score += 0.12
        elif context.data_points >= 4:
            score += 0.08
        elif context.data_points >= 3:
            score += 0.05

        # Consistent trend from previous analysis = higher confidence
        if context.confidence == 'high':
            score += 0.15
        elif context.confidence == 'medium':
            score += 0.08
        else:
            score += 0.02

        # Fewer periods ahead = higher confidence
        if periods_ahead == 1:
            score += 0.10
        elif periods_ahead == 2:
            score += 0.05
        elif periods_ahead == 3:
            score += 0.02
        elif periods_ahead >= 4:
            score -= 0.05  # Reduce confidence for distant projections
        if periods_ahead >= 6:
            score -= 0.10

        # Strong trend direction = higher confidence
        if abs(context.normalized_slope) > 10:  # >10% per period
            score += 0.10
        elif abs(context.normalized_slope) > 5:  # >5% per period
            score += 0.07
        elif abs(context.normalized_slope) > 2:
            score += 0.04

        # Data consistency (if we have values)
        if context.values and len(context.values) >= 3:
            try:
                cv = statistics.stdev(context.values) / context.avg_value if context.avg_value != 0 else 1
                if cv < 0.1:  # Very consistent
                    score += 0.10
                elif cv < 0.2:
                    score += 0.05
                elif cv > 0.5:  # Very volatile
                    score -= 0.10
            except statistics.StatisticsError:
                pass

        # Method-specific adjustments
        if method == ProjectionMethod.EXPONENTIAL_SMOOTHING:
            score += 0.03  # ES is more robust
        elif method == ProjectionMethod.HYBRID:
            score += 0.05  # Consensus is more reliable
        elif method == ProjectionMethod.MOMENTUM:
            score -= 0.05  # Simple method, less reliable

        return min(0.95, max(0.25, score))  # Clamp to 0.25-0.95

    def _score_to_level(self, score: float) -> ConfidenceLevel:
        """Convert confidence score to level"""
        if score >= 0.75:
            return ConfidenceLevel.HIGH
        elif score >= 0.55:
            return ConfidenceLevel.MEDIUM
        else:
            return ConfidenceLevel.LOW

    def _add_goal_analysis(
        self,
        result: ProjectionResult,
        context: TrendContext,
        target_value: float
    ) -> ProjectionResult:
        """Add goal-based analysis to projection result"""

        if context.slope == 0:
            result.periods_to_goal = None
            result.goal_reachable = False
            return result

        # Calculate periods to reach target
        value_diff = target_value - context.end_value

        # Check if we're moving toward or away from goal
        if (context.slope > 0 and value_diff > 0) or (context.slope < 0 and value_diff < 0):
            # Moving toward goal
            periods_needed = abs(value_diff / context.slope) if context.slope != 0 else float('inf')
            result.periods_to_goal = max(1, round(periods_needed))
            result.goal_reachable = periods_needed > 0 and periods_needed < 24  # Within 2 years
        else:
            # Moving away from goal
            result.periods_to_goal = None
            result.goal_reachable = False

        return result


def extract_trend_context(previous_turn: Any) -> Optional[TrendContext]:
    """
    Extract trend context from a previous QueryTurn.

    Args:
        previous_turn: QueryTurn with trend/comparison data

    Returns:
        TrendContext if extractable, None otherwise
    """
    if not previous_turn:
        print("    [extract_trend_context] No previous_turn provided")
        return None

    query_plan = getattr(previous_turn, 'query_plan', {}) or {}
    result_values = getattr(previous_turn, 'result_values', {}) or {}

    # Debug output to trace the issue
    query_type = query_plan.get('query_type', 'unknown')
    print(f"    [extract_trend_context] Previous query_type: {query_type}")
    print(f"    [extract_trend_context] query_plan keys: {list(query_plan.keys())}")

    # Try to get analysis from query_plan
    analysis = query_plan.get('analysis', {}) or {}
    print(f"    [extract_trend_context] analysis keys: {list(analysis.keys()) if analysis else 'empty'}")

    # If no analysis but was a trend query, log warning
    if query_type == 'trend' and not analysis:
        print(f"    [extract_trend_context] WARNING: Trend query but no analysis found!")

    # Also check result_values (some data might be stored there)
    if not analysis:
        analysis = result_values

    # Try to extract required fields
    direction = (
        analysis.get('direction') or
        analysis.get('trend_direction') or
        result_values.get('direction') or
        'unknown'
    )

    slope = float(
        analysis.get('slope') or
        result_values.get('slope') or
        0
    )

    normalized_slope = float(
        analysis.get('normalized_slope') or
        result_values.get('normalized_slope') or
        0
    )

    print(f"    [extract_trend_context] direction={direction}, slope={slope}, normalized_slope={normalized_slope}")

    # If no trend data available, return None
    if direction == 'unknown' and slope == 0 and normalized_slope == 0:
        print("    [extract_trend_context] All values are default - returning None")
        return None

    # Extract values array
    values = (
        analysis.get('values') or
        result_values.get('values') or
        []
    )

    # Convert values to float list if needed
    if values and isinstance(values[0], dict):
        # Extract value from dict format [{"date": x, "value": y}, ...]
        values = [float(v.get('value', 0)) for v in values if v.get('value') is not None]
    elif values:
        values = [float(v) for v in values if v is not None]

    # Get other fields with defaults
    start_value = float(analysis.get('start_value') or (values[0] if values else 0))
    end_value = float(analysis.get('end_value') or (values[-1] if values else 0))

    return TrendContext(
        direction=direction,
        slope=slope,
        normalized_slope=normalized_slope,
        start_value=start_value,
        end_value=end_value,
        percentage_change=float(analysis.get('percentage_change') or 0),
        data_points=int(analysis.get('data_points') or len(values) or 2),
        min_value=float(analysis.get('min_value') or (min(values) if values else 0)),
        max_value=float(analysis.get('max_value') or (max(values) if values else 0)),
        avg_value=float(analysis.get('avg_value') or (sum(values)/len(values) if values else 0)),
        confidence=str(analysis.get('confidence') or 'medium'),
        time_unit=_detect_time_unit(query_plan),
        values=values
    )


def _detect_time_unit(query_plan: Dict) -> str:
    """Detect time unit from query plan"""
    trend_config = query_plan.get('trend', {})
    date_column = str(trend_config.get('date_column', '')).lower()

    # Also check the analysis for stored time_unit
    analysis = query_plan.get('analysis', {})
    if analysis.get('time_unit'):
        return analysis.get('time_unit')

    if 'month' in date_column:
        return 'month'
    elif 'week' in date_column:
        return 'week'
    elif 'day' in date_column or 'date' in date_column:
        return 'day'
    elif 'quarter' in date_column or date_column.startswith('q'):
        return 'quarter'
    elif 'year' in date_column:
        return 'year'

    return 'month'  # Default assumption


# Singleton calculator instance
_calculator_instance: Optional[ProjectionCalculator] = None


def get_projection_calculator() -> ProjectionCalculator:
    """Get or create singleton calculator"""
    global _calculator_instance
    if _calculator_instance is None:
        _calculator_instance = ProjectionCalculator()
    return _calculator_instance
