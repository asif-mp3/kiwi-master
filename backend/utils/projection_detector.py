"""
Projection Intent Detector for Thara AI

Detects when users are asking for projections/forecasts based on previous trend data.
Uses pattern matching (no LLM) for speed (~1-5ms).

Examples:
- "If this trend continues, what will January sales be?"
- "Based on this, project next month"
- "இந்த போக்கு தொடர்ந்தால், ஜனவரி விற்பனை என்னவாக இருக்கும்?"
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import re


class ProjectionType(Enum):
    """Types of projections user can request"""
    FUTURE_VALUE = "future_value"       # "What will January sales be?"
    CONTINUATION = "continuation"        # "If this trend continues..."
    GOAL_BASED = "goal_based"           # "When will we hit 10 lakhs?"
    COMPARISON_BASED = "comparison"      # "Based on this comparison, project..."


@dataclass
class ProjectionIntent:
    """Detected projection intent from user message"""
    projection_type: ProjectionType
    confidence: float  # 0.0 to 1.0

    # Target period for projection
    target_period: Optional[str] = None       # "January", "next_month", "Q1"
    target_period_count: int = 1              # How many periods ahead (1, 2, 3...)

    # For goal-based projections
    target_value: Optional[float] = None      # "When will we hit 10 lakhs?"

    # Context requirements
    requires_trend_context: bool = True       # Needs previous trend data
    requires_comparison_context: bool = False # Needs previous comparison data

    # Raw detection data
    raw_patterns_matched: List[str] = field(default_factory=list)
    detected_at: datetime = field(default_factory=datetime.now)


# Pattern categories for projection detection
PROJECTION_PATTERNS = {
    # Explicit continuation patterns
    'continuation_explicit': [
        # "if this/the/that trend continues"
        r'\b(if|assuming|suppose|supposing)\s+(this|the|that|same)\s+(trend|pattern|growth|decline|rate|pace)\s+(continues|keeps|maintains|persists|holds)\b',
        # "at this rate", "at this pace", "going forward"
        r'\b(at\s+this\s+rate|at\s+this\s+pace|going\s+forward|moving\s+forward)\b',
        # "based on this/the trend/pattern/data" followed by comma or action word
        r'\b(based\s+on|using|from)\s+(this|the|that|current)\s+(trend|pattern|data|growth|analysis)\b',
        # "if the same continues"
        r'\b(if|assuming)\s+(the\s+)?(same|this|current)\s+(continues|trend\s+continues)\b',
        # Simple "project", "forecast", "predict", "extrapolate" with month/next
        r'\b(extrapolat|project|forecast|predict|estimat)\w*\s+(for|the|next|future|january|february|march|april|may|june|july|august|september|october|november|december)\b',
        # === NEW PATTERNS FOR BETTER MATCHING ===
        # "estimate next month's sales", "project next quarter's revenue"
        r'\b(estimate|project|forecast|predict)\s+(next\s+month|next\s+quarter|next\s+year|next\s+week)\s*\'?s?\s*(sales|revenue|profit|value)?\b',
        # "based on this trend, estimate/project/what will..."
        r'\bbased\s+on\s+(this|the)\s+(trend|data|pattern),?\s*(estimate|project|predict|what\s+will)\b',
        # "same trend continues, what" or "trend continues what will"
        r'\b(trend|pattern|rate)\s+(continues|persists),?\s*(what|estimate|project|predict)\b',
        # "if the trend/pattern continues, [month/next month]"
        r'\b(if|assuming)\s+(this|the)\s+(trend|pattern)\s+(continues|holds).*?(next\s+month|january|february|march|april|may|june|july|august|september|october|november|december)\b',
        # === PATTERNS FOR RESOLVED REFERENCES (e.g., "if Sarees continues this pattern") ===
        # "if [item] continues this/the pattern" - after top reference is resolved
        r'\b(if|assuming)\s+\w+\s+(continues|keeps)\s+(this|the|that)\s+(pattern|trend|rate|growth)\b',
        # "[item] continues this pattern, what will"
        r'\b\w+\s+(continues|keeps)\s+(this|the)\s+(pattern|trend).*(what|expected|project|estimate)\b',
        # "continues this pattern" + expected/projected
        r'\bcontinues\s+this\s+(pattern|trend).*(expected|projected|estimated|forecast)\b',
        # "what is the expected sales next month" with context
        r'\bwhat\s+(is|are)\s+(the\s+)?(expected|projected|estimated)\s+(sales|revenue|profit)\s+(for\s+)?(next\s+month|next\s+quarter|january|february|march|april|may|june|july|august|september|october|november|december)\b',
    ],

    # Future value questions
    'future_value': [
        # "what will be the sales/revenue/profit"
        r'\b(what\s+will|what\'ll|what\s+would|what\s+could)\s+(be\s+)?(the\s+)?(\w+\s+)?(sales|revenue|profit|value|amount)\b',
        # "what will sales/revenue be"
        r'\b(what\s+will|what\'ll|what\s+would)\s+(sales|revenue|profit|the\s+value)\s+be\b',
        # "how much will we/it/sales have/be/reach"
        r'\b(how\s+much|what)\s+(will|would|could)\s+(we|it|sales|revenue|profit)\s+(be|have|reach|hit)\b',
        # "estimate/predict/forecast for [month]"
        r'\b(estimate|predict|forecast|project)\s+(for\s+)?(the\s+)?(january|february|march|april|may|june|july|august|september|october|november|december|next\s+month|next\s+quarter|next\s+year)\b',
        # "what can we expect"
        r'\b(what)\s+(can|could|should)\s+(we|i)\s+expect\b',
        # "projected sales for"
        r'\b(projected|expected|estimated|forecasted)\s+(sales|revenue|profit|value)\s+(for|in)\b',
    ],

    # Goal-based projections
    'goal_based': [
        # "when will we hit/reach/cross X"
        r'\b(when\s+will|when\'ll|when\s+would)\s+(we|sales|it|revenue)\s+(hit|reach|cross|exceed|get\s+to)\s+(\d+)\b',
        # "how long to reach/hit"
        r'\b(how\s+long|how\s+many\s+(months|weeks|days|quarters))\s+(to|until|before|till)\s+(reach|hit|cross|get\s+to)\b',
        # "will we hit X by Y"
        r'\b(will|can|could)\s+(we|sales|it)\s+(hit|reach|cross)\s+(\d+)\s+(by|before|in)\b',
    ],

    # Comparison-based projections
    'comparison_based': [
        # "based on this comparison/difference, project/what will"
        r'\b(based\s+on|from|using)\s+(this|the)\s*(comparison|difference|change|growth|increase|decrease)?\s*,?\s*(project|what\s+will|estimate|predict)\b',
        # "if this difference/change continues"
        r'\b(if|assuming)\s+(this|the)\s+(difference|change|growth|increase|decrease)\s+(continues|persists)\b',
        # "at this growth rate"
        r'\b(at|with)\s+(this|the|same)\s+(growth|increase|decrease)\s+rate\b',
    ],

    # Tamil projection patterns
    'tamil_projection': [
        # இந்த போக்கு தொடர்ந்தால் - if this trend continues
        r'(இந்த|அந்த|இதே)\s*(போக்கு|வளர்ச்சி|pattern|trend)\s*(தொடர்ந்தால்|நீடித்தால்)',
        # என்னவாக இருக்கும் - what will it be
        r'(என்னவாக|எவ்வளவாக)\s*(இருக்கும்|வரும்)',
        # கணிக்க, முன்கணிப்பு - predict, forecast
        r'(கணிக்க|முன்கணிப்பு|கணிப்பு|எதிர்பார்க்கலாம்)',
        # அடுத்த மாதம் - next month
        r'(அடுத்த|வரும்|எதிர்வரும்)\s*(மாதம்|மாத|quarter|வாரம்)',
        # projected - project செய்
        r'(project|forecast|predict)\s*(செய்|பண்ணு)',
        # estimate பண்ணு, மதிப்பிடு
        r'(estimate|மதிப்பிடு|மதிப்பீடு)',
    ],

    # Simple projection triggers (lower confidence)
    'simple_triggers': [
        # Just "next month/quarter" with context
        r'\b(next\s+month|next\s+quarter|next\s+year)\s*(sales|revenue|profit|value)?\s*\??\s*$',
        # "for january/february..." as follow-up
        r'^(for\s+)?(january|february|march|april|may|june|july|august|september|october|november|december)\s*\??\s*$',
        # "and next month?"
        r'\b(and|what\s+about)\s+(next\s+month|next\s+quarter|january|february|march|april|may|june|july|august|september|october|november|december)\s*\?',
    ],
}

# Month mapping for target period extraction
MONTHS = {
    'january': 1, 'jan': 1,
    'february': 2, 'feb': 2,
    'march': 3, 'mar': 3,
    'april': 4, 'apr': 4,
    'may': 5,
    'june': 6, 'jun': 6,
    'july': 7, 'jul': 7,
    'august': 8, 'aug': 8,
    'september': 9, 'sep': 9, 'sept': 9,
    'october': 10, 'oct': 10,
    'november': 11, 'nov': 11,
    'december': 12, 'dec': 12,
}

# Tamil months
TAMIL_MONTHS = {
    'ஜனவரி': 1, 'பிப்ரவரி': 2, 'மார்ச்': 3,
    'ஏப்ரல்': 4, 'மே': 5, 'ஜூன்': 6,
    'ஜூலை': 7, 'ஆகஸ்ட்': 8, 'செப்டம்பர்': 9,
    'அக்டோபர்': 10, 'நவம்பர்': 11, 'டிசம்பர்': 12,
}


class ProjectionIntentDetector:
    """
    Detects projection intent from user messages.
    Uses pattern matching (no LLM) for speed.
    """

    def __init__(self):
        self._compiled_patterns = self._compile_patterns()

    def _compile_patterns(self) -> Dict[str, List[re.Pattern]]:
        """Compile regex patterns for performance"""
        compiled = {}
        for category, patterns in PROJECTION_PATTERNS.items():
            compiled[category] = [
                re.compile(p, re.IGNORECASE | re.UNICODE)
                for p in patterns
            ]
        return compiled

    def detect(
        self,
        question: str,
        previous_turn: Optional[Any] = None
    ) -> Optional[ProjectionIntent]:
        """
        Detect if message contains projection intent.

        Args:
            question: User's current message
            previous_turn: The last QueryTurn (must have trend/comparison data)

        Returns:
            ProjectionIntent if detected, None otherwise
        """
        if not question or not question.strip():
            return None

        # Projection only makes sense with previous context
        if previous_turn is None:
            return None

        # Check if previous turn has trend/comparison data
        if not self._has_projectable_context(previous_turn):
            return None

        question_clean = question.strip()
        question_lower = question_clean.lower()

        # CRITICAL: Exclude explicit comparison queries from projection detection
        # These should be handled by the comparison query type, not projection
        comparison_exclusion_patterns = [
            r'\bcompare\b.*\b(between|and|vs|versus)\b.*\b(november|december|january|february|march|april|may|june|july|august|september|october)\b',
            r'\bcompare\s+(revenue|sales|profit)\b',
            r'\b(november|december)\s*(vs|versus|and)\s*(december|november)\b',
            r'\bbetween\s+(november|december|january|february|march|april|may|june|july|august|september|october)\s+(and|&)\s+(november|december|january|february|march|april|may|june|july|august|september|october)\b',
        ]
        for pattern in comparison_exclusion_patterns:
            if re.search(pattern, question_lower):
                return None  # This is a comparison query, not a projection

        # Try pattern matching
        intent = self._detect_with_patterns(question_lower, question_clean, previous_turn)

        return intent

    def _has_projectable_context(self, previous_turn: Any) -> bool:
        """Check if previous turn has data suitable for projection"""
        if not previous_turn:
            return False

        # Check query plan for trend/comparison type
        query_plan = getattr(previous_turn, 'query_plan', {}) or {}
        query_type = query_plan.get('query_type', '')

        if query_type in ['trend', 'comparison']:
            return True

        # Check for trend analysis in query plan
        if query_plan.get('trend'):
            return True

        # Check result_values for trend analysis data
        result_values = getattr(previous_turn, 'result_values', {}) or {}
        if any(key in result_values for key in ['slope', 'percentage_change', 'direction', 'trend_direction']):
            return True

        # Check if there's analysis data stored
        analysis = query_plan.get('analysis', {})
        if analysis and any(key in analysis for key in ['slope', 'direction', 'percentage_change']):
            return True

        # ALSO accept rank/aggregation queries that have dimension values
        # (User might be asking about projection for top item - we'll guide them)
        if query_type in ['rank', 'extrema_lookup', 'aggregation_on_subset']:
            # Check if result_values has any dimension columns (category, state, etc.)
            dimension_patterns = ['category', 'state', 'branch', 'product', 'region', 'area', 'employee', 'item']
            for col_name in result_values.keys():
                if any(pattern in col_name.lower() for pattern in dimension_patterns):
                    return True

        return False

    def _has_actual_trend_data(self, previous_turn: Any) -> bool:
        """Check if previous turn has ACTUAL trend data (not just rank results)"""
        if not previous_turn:
            return False

        query_plan = getattr(previous_turn, 'query_plan', {}) or {}
        query_type = query_plan.get('query_type', '')

        # Only trend/comparison have actual trend data
        if query_type in ['trend', 'comparison']:
            return True

        if query_plan.get('trend'):
            return True

        # Check for trend analysis keys
        result_values = getattr(previous_turn, 'result_values', {}) or {}
        if any(key in result_values for key in ['slope', 'percentage_change', 'direction', 'trend_direction']):
            return True

        analysis = query_plan.get('analysis', {})
        if analysis and any(key in analysis for key in ['slope', 'direction', 'percentage_change']):
            return True

        return False

    def _detect_with_patterns(
        self,
        question_lower: str,
        question_original: str,
        previous_turn: Any
    ) -> Optional[ProjectionIntent]:
        """Fast pattern matching for projection detection"""

        matched_categories = []
        all_matches = []

        for category, patterns in self._compiled_patterns.items():
            for pattern in patterns:
                match = pattern.search(question_lower)
                if match:
                    matched_categories.append(category)
                    all_matches.append((category, match, pattern.pattern))
                    break  # One match per category is enough

        if not matched_categories:
            return None

        # Determine projection type based on matched categories
        projection_type, requires_comparison = self._determine_projection_type(matched_categories)

        # Extract target period
        target_period, period_count = self._extract_target_period(question_lower, question_original, previous_turn)

        # Extract target value for goal-based projections
        target_value = None
        if projection_type == ProjectionType.GOAL_BASED:
            target_value = self._extract_target_value(question_lower)

        # Calculate confidence based on match quality
        confidence = self._calculate_confidence(matched_categories, all_matches)

        return ProjectionIntent(
            projection_type=projection_type,
            confidence=confidence,
            target_period=target_period,
            target_period_count=period_count,
            target_value=target_value,
            requires_trend_context=not requires_comparison,
            requires_comparison_context=requires_comparison,
            raw_patterns_matched=[m[2] for m in all_matches]
        )

    def _determine_projection_type(self, matched_categories: List[str]) -> Tuple[ProjectionType, bool]:
        """Determine projection type from matched categories"""
        requires_comparison = False

        if 'goal_based' in matched_categories:
            return ProjectionType.GOAL_BASED, False

        if 'comparison_based' in matched_categories:
            requires_comparison = True
            return ProjectionType.COMPARISON_BASED, True

        if any('continuation' in cat for cat in matched_categories):
            return ProjectionType.CONTINUATION, False

        if any('future_value' in cat for cat in matched_categories):
            return ProjectionType.FUTURE_VALUE, False

        if 'tamil_projection' in matched_categories:
            return ProjectionType.CONTINUATION, False

        if 'simple_triggers' in matched_categories:
            return ProjectionType.FUTURE_VALUE, False

        # Default
        return ProjectionType.CONTINUATION, False

    def _extract_target_period(
        self,
        question_lower: str,
        question_original: str,
        previous_turn: Any
    ) -> Tuple[Optional[str], int]:
        """Extract the target period for projection"""

        # Check for explicit month names (English)
        for month_name, month_num in MONTHS.items():
            if month_name in question_lower:
                return month_name.capitalize(), 1

        # Check for Tamil month names
        for tamil_month, month_num in TAMIL_MONTHS.items():
            if tamil_month in question_original:
                # Return English equivalent for consistency
                eng_month = [k for k, v in MONTHS.items() if v == month_num and len(k) > 3][0]
                return eng_month.capitalize(), 1

        # Check for relative references
        if 'next month' in question_lower or 'அடுத்த மாதம்' in question_original:
            return 'next_month', 1

        if 'next quarter' in question_lower or 'அடுத்த காலாண்டு' in question_original:
            return 'next_quarter', 3

        if 'next year' in question_lower or 'அடுத்த ஆண்டு' in question_original:
            return 'next_year', 12

        # Check for "next N months"
        match = re.search(r'next\s+(\d+)\s+months?', question_lower)
        if match:
            count = int(match.group(1))
            return f'next_{count}_months', count

        # Check for "in N months"
        match = re.search(r'in\s+(\d+)\s+months?', question_lower)
        if match:
            count = int(match.group(1))
            return f'in_{count}_months', count

        # Default: next period based on previous query's time unit
        return 'next_period', 1

    def _extract_target_value(self, question_lower: str) -> Optional[float]:
        """Extract target value for goal-based projections"""

        # Match patterns like "10 lakhs", "5 crores", "1.5 lakhs"
        lakh_match = re.search(r'(\d+(?:\.\d+)?)\s*lakhs?', question_lower)
        if lakh_match:
            return float(lakh_match.group(1)) * 100000

        crore_match = re.search(r'(\d+(?:\.\d+)?)\s*crores?', question_lower)
        if crore_match:
            return float(crore_match.group(1)) * 10000000

        # Tamil equivalents
        lakh_tamil = re.search(r'(\d+(?:\.\d+)?)\s*(லட்சம்|லட்ச)', question_lower)
        if lakh_tamil:
            return float(lakh_tamil.group(1)) * 100000

        crore_tamil = re.search(r'(\d+(?:\.\d+)?)\s*(கோடி)', question_lower)
        if crore_tamil:
            return float(crore_tamil.group(1)) * 10000000

        # Plain large number (4+ digits)
        num_match = re.search(r'(\d{4,})', question_lower)
        if num_match:
            return float(num_match.group(1))

        return None

    def _calculate_confidence(
        self,
        matched_categories: List[str],
        all_matches: List[Tuple]
    ) -> float:
        """Calculate confidence score based on match quality"""

        # Base confidence by category type
        category_weights = {
            'continuation_explicit': 0.85,
            'future_value': 0.80,
            'goal_based': 0.85,
            'comparison_based': 0.80,
            'tamil_projection': 0.80,
            'simple_triggers': 0.60,
        }

        # Get highest weight from matched categories
        max_weight = max(
            category_weights.get(cat, 0.5)
            for cat in matched_categories
        )

        # Bonus for multiple category matches
        if len(matched_categories) >= 2:
            max_weight = min(0.95, max_weight + 0.10)

        return max_weight


# Singleton instance
_detector_instance: Optional[ProjectionIntentDetector] = None


def get_projection_detector() -> ProjectionIntentDetector:
    """Get or create the singleton detector instance"""
    global _detector_instance
    if _detector_instance is None:
        _detector_instance = ProjectionIntentDetector()
    return _detector_instance


def detect_projection_intent(
    question: str,
    previous_turn: Any = None
) -> Optional[ProjectionIntent]:
    """
    Convenience function for detecting projection intent.

    Args:
        question: User's current message
        previous_turn: The last QueryTurn from conversation context

    Returns:
        ProjectionIntent if detected, None otherwise
    """
    detector = get_projection_detector()
    return detector.detect(question, previous_turn)
