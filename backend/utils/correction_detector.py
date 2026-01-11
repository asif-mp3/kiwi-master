"""
Correction Intent Detector - Detects when users want to correct previous query results.

Supports:
1. Table corrections: "No, use the sales table", "Check the other table"
2. Filter corrections: "I meant September not October"
3. Metric corrections: "Show profit, not revenue"
4. Negation: "That's wrong", "Incorrect"
5. Revert: "Never mind, go back to original"

Uses hybrid approach:
- Fast regex pattern matching for common patterns
- LLM fallback for ambiguous cases
"""

import re
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime


class CorrectionType(Enum):
    """Types of corrections a user can make"""
    TABLE = "table"           # "No, use the sales table"
    FILTER = "filter"         # "No, I meant September not October"
    METRIC = "metric"         # "No, show profit not revenue"
    NEGATION = "negation"     # "That's wrong", "Incorrect"
    REVERT = "revert"         # "Actually never mind, go back"
    MULTIPLE = "multiple"     # Multiple aspects corrected at once


@dataclass
class CorrectionIntent:
    """Detected correction intent from user message"""
    correction_type: CorrectionType
    confidence: float  # 0.0 to 1.0

    # Table correction fields
    table_hint: Optional[str] = None          # Partial table name: "sales", "summary"
    explicit_table: Optional[str] = None      # Exact table name if mentioned
    table_type_hint: Optional[str] = None     # Table type: "summary", "transactional", "category"

    # Filter correction fields
    filter_corrections: List[Dict[str, Any]] = field(default_factory=list)
    # Each: {"field": "month", "old_value": "October", "new_value": "September"}

    # Metric correction fields
    metric_corrections: List[Dict[str, Any]] = field(default_factory=list)
    # Each: {"old_metric": "revenue", "new_metric": "profit"}

    # For revert corrections
    revert_to_turn: Optional[int] = None  # -1 for "original", or turn index

    # Raw detection data
    raw_patterns_matched: List[str] = field(default_factory=list)
    detected_at: datetime = field(default_factory=datetime.now)


# ============================================================================
# CORRECTION PATTERNS - Organized by type
# ============================================================================

CORRECTION_PATTERNS = {
    # TABLE CORRECTIONS - User wants a different data source
    'table_explicit': [
        # "use the sales table", "check the branch table", "check in branch details table"
        r'\b(use|check|look\s+at|switch\s+to|try)\s+(the\s+|in\s+|in\s+the\s+)?([a-zA-Z_\s]+?)\s+(table|sheet|data)\b',
        # "from the sales table", "in the branch sheet"
        r'\b(from|in)\s+(the\s+)?([a-zA-Z_\s]+?)\s+(table|sheet)\b',
        # "not this table, the sales one"
        r'\bnot\s+(this|that)\s+(table|one|sheet),?\s*(the\s+)?([a-zA-Z_]+)',
        # "the daily table" (standalone mention)
        r'\bthe\s+([a-zA-Z_\s]+?)\s+(table|sheet)\b',
        # "X table" pattern - "branch details table", "sales table"
        r'\b([a-zA-Z_]+(?:\s+[a-zA-Z_]+)?)\s+(table|sheet)\s*$',
    ],

    'table_type_hint': [
        # "use the summary table", "check the raw data"
        r'\b(use|check|show|give)\s+(the\s+)?(summary|detailed|raw|transaction|transactional|category|daily|monthly|aggregate)\s*(table|data|one|sheet)?\b',
        # "the summary one", "the detailed version"
        r'\b(the\s+)?(summary|detailed|raw|transaction|transactional|category|daily|monthly|aggregate)\s*(table|one|version|data)?\b',
        # "other table", "another table", "different table"
        r'\b(the\s+)?(other|another|different)\s+(table|one|sheet|data)\b',
        # "not this table", "not this one"
        r'\bnot\s+(this|that)\s+(table|one|sheet),?\s*(the\s+)?(other|another)?\b',
    ],

    # FILTER CORRECTIONS - User wants different filter values
    'filter_replacement': [
        # "I meant September not October", "no I meant Chennai"
        r'\b(no|not),?\s*(i\s+)?(meant|want|wanted|need|said)\s+([a-zA-Z0-9_]+)\s*(,|\s)*(not|instead\s+of|rather\s+than)?\s*([a-zA-Z0-9_]+)?\b',
        # "actually for Tamil Nadu not Karnataka"
        r'\bactually\s+(for|in|of)\s+([a-zA-Z0-9_\s]+)\s*(not|instead\s+of)\s+([a-zA-Z0-9_\s]+)\b',
        # "September not October", "Chennai instead of Bangalore"
        r'\b([a-zA-Z0-9_]+)\s+(not|instead\s+of|rather\s+than)\s+([a-zA-Z0-9_]+)\b',
        # "change October to September", "replace Karnataka with Tamil Nadu"
        r'\b(change|replace|switch)\s+([a-zA-Z0-9_]+)\s+(to|with)\s+([a-zA-Z0-9_]+)\b',
        # "for September" (short form when context is clear)
        r'^(for|in)\s+([a-zA-Z0-9_]+)$',
    ],

    # METRIC CORRECTIONS - User wants different metrics
    'metric_replacement': [
        # "show profit not revenue", "give me orders not sales"
        r'\b(show|give|want|display)\s+(me\s+)?([a-zA-Z_]+)\s*(,|\s)*(not|instead\s+of)\s+([a-zA-Z_]+)\b',
        # "I wanted profit not revenue"
        r'\bi\s+(wanted|asked\s+for|meant|need)\s+([a-zA-Z_]+)\s*(not|instead\s+of)\s+([a-zA-Z_]+)\b',
        # "profit not revenue" (direct swap)
        r'^([a-zA-Z_]+)\s+(not|instead\s+of)\s+([a-zA-Z_]+)$',
        # "no, profit" (short correction)
        r'^no,?\s+([a-zA-Z_]+)$',
        # "check based on profit instead", "based on profit", "by profit instead"
        r'\b(check|show|get)\s+(based\s+on|by)\s+([a-zA-Z_]+)\s*(instead)?\b',
        r'\b(based\s+on|by)\s+([a-zA-Z_]+)\s+(instead)\b',
        # "profit instead", "X instead" at end
        r'\b([a-zA-Z_]+)\s+instead\s*$',
    ],

    # NEGATION - General dissatisfaction without specific correction
    'negation': [
        # "that's wrong", "this is incorrect"
        r'\b(that\'?s|this\s+is|it\'?s)\s+(wrong|incorrect|not\s+right|not\s+correct|not\s+what)\b',
        # "wrong", "incorrect" (standalone)
        r'^(wrong|incorrect|no)$',
        # "not what I asked", "not what I wanted"
        r'\bnot\s+what\s+i\s+(asked|wanted|meant|need)\b',
        # "try again", "check again"
        r'\b(try|check|look)\s+again\b',
        # "that doesn't look right"
        r'\b(doesn\'?t|does\s+not)\s+(look|seem)\s+(right|correct)\b',
    ],

    # REVERT - Undo previous correction
    'revert': [
        # "never mind", "actually never mind"
        r'\b(actually\s+)?never\s*mind\b',
        # "go back to original", "go back to previous"
        r'\bgo\s+back\s+(to\s+)?(the\s+)?(original|previous|before|first)\b',
        # "undo that", "undo the correction"
        r'\bundo\s+(that|this|the\s+correction|it)?\b',
        # "revert", "cancel"
        r'^(revert|cancel)$',
        # "the first one was right"
        r'\b(the\s+)?(first|original)\s+(one|answer|result)\s+(was|is)\s+(right|correct|better)\b',
    ],

    # TAMIL PATTERNS
    'tamil_table': [
        # வேற table (different table)
        r'(வேற|வேறு|இன்னொரு|அந்த|மற்ற)\s*(table|அட்டவணை|sheet|ஷீட்|டேட்டா)',
        # இது வேண்டாம் (don't want this)
        r'(இது\s+வேண்டாம்|இல்ல|வேண்டாம்)',
        # summary/detail in Tamil context
        r'(சுருக்கம்|விரிவாக|தினசரி|மாதாந்திர)\s*(table|டேட்டா)?',
    ],

    'tamil_filter': [
        # "October இல்ல, September" (not October, September)
        r'([a-zA-Z0-9_]+)\s+(இல்ல|வேண்டாம்|அல்ல),?\s*([a-zA-Z0-9_]+)',
        # "நான் சொன்னது September" (I said September)
        r'நான்\s+(சொன்னது|கேட்டது|வேண்டியது)\s+([a-zA-Z0-9_]+)',
        # "September மாதம்" (September month)
        r'([a-zA-Z]+)\s+மாதம்',
    ],

    'tamil_negation': [
        # தவறு (wrong), சரியில்ல (not correct)
        r'(தவறு|சரியில்ல|சரியில்லை|தப்பு)',
        # நான் கேட்டது இது இல்ல (this is not what I asked)
        r'நான்\s+(கேட்டது|வேண்டியது)\s+இது\s+(இல்ல|அல்ல)',
        # மறுபடி (again)
        r'(மறுபடி|திரும்ப)\s*(பாரு|செய்)',
    ],

    'tamil_revert': [
        # பரவாயில்ல (never mind)
        r'(பரவாயில்ல|பரவால்ல|விடு)',
        # முந்தைய (previous)
        r'(முந்தைய|முதல்)\s*(ஒன்று|பதில்)',
    ],
}

# Known metrics for detection
KNOWN_METRICS = {
    'revenue', 'sales', 'profit', 'orders', 'units', 'quantity', 'amount',
    'cost', 'margin', 'growth', 'count', 'total', 'average', 'avg', 'sum',
    'max', 'min', 'discount', 'tax', 'price', 'value', 'volume'
}

# Known months for detection
KNOWN_MONTHS = {
    'january', 'february', 'march', 'april', 'may', 'june',
    'july', 'august', 'september', 'october', 'november', 'december',
    'jan', 'feb', 'mar', 'apr', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec'
}

# Table type keywords mapping
TABLE_TYPE_KEYWORDS = {
    'raw': 'transactional',
    'detail': 'transactional',
    'detailed': 'transactional',
    'transaction': 'transactional',
    'transactional': 'transactional',
    'daily': 'transactional',
    'individual': 'transactional',
    'summary': 'summary',
    'aggregate': 'summary',
    'aggregated': 'summary',
    'total': 'summary',
    'totals': 'summary',
    'monthly': 'summary',
    'overall': 'summary',
    'category': 'category',
    'breakdown': 'category',
    'by_category': 'category',
}


class CorrectionIntentDetector:
    """
    Detects correction intent from user messages.

    Uses a hybrid approach:
    1. Fast regex pattern matching for common patterns
    2. LLM fallback for ambiguous cases (optional)
    """

    def __init__(self):
        self._known_tables: List[str] = []
        self._known_locations: set = set()
        self._known_categories: set = set()
        # Compile patterns for performance
        self._compiled_patterns = self._compile_patterns()

    def _compile_patterns(self) -> Dict[str, List[re.Pattern]]:
        """Compile all regex patterns for performance"""
        compiled = {}
        for category, patterns in CORRECTION_PATTERNS.items():
            compiled[category] = [re.compile(p, re.IGNORECASE) for p in patterns]
        return compiled

    def refresh_from_profiles(self, profile_store) -> None:
        """Learn known values from table profiles for better detection"""
        if profile_store is None:
            return

        try:
            # Get all table names
            self._known_tables = profile_store.get_table_names() or []

            # Extract locations and categories from profiles
            for table_name in self._known_tables:
                profile = profile_store.get_profile(table_name)
                if not profile:
                    continue

                columns = profile.get('columns', {})
                for col_name, col_info in columns.items():
                    role = col_info.get('role', '')
                    unique_values = col_info.get('unique_values', [])

                    if role == 'dimension':
                        col_lower = col_name.lower()
                        if any(loc in col_lower for loc in ['state', 'city', 'region', 'area', 'location']):
                            self._known_locations.update(str(v).lower() for v in unique_values if v)
                        elif any(cat in col_lower for cat in ['category', 'type', 'product']):
                            self._known_categories.update(str(v).lower() for v in unique_values if v)
        except Exception as e:
            print(f"Warning: Could not refresh correction detector from profiles: {e}")

    def detect(self, question: str, previous_turn: Optional[Any] = None) -> Optional[CorrectionIntent]:
        """
        Detect if message contains correction intent.

        Args:
            question: User's current message
            previous_turn: The last QueryTurn (context for correction)

        Returns:
            CorrectionIntent if correction detected, None otherwise
        """
        if not question or not question.strip():
            return None

        # Only detect corrections if there's previous context
        if previous_turn is None:
            return None

        question_clean = question.strip()

        # Try fast pattern matching first
        intent = self._detect_with_patterns(question_clean, previous_turn)

        if intent:
            return intent

        # No pattern match - check for implicit corrections
        intent = self._detect_implicit_correction(question_clean, previous_turn)

        return intent

    def _detect_with_patterns(self, question: str, previous_turn: Any) -> Optional[CorrectionIntent]:
        """Fast path: regex pattern matching"""

        matched_categories = []
        all_matches = []

        # Check each category
        for category, patterns in self._compiled_patterns.items():
            for pattern in patterns:
                match = pattern.search(question)
                if match:
                    matched_categories.append(category)
                    all_matches.append((category, match))
                    break  # One match per category is enough

        if not matched_categories:
            return None

        # Determine correction type based on matched categories
        if any('revert' in cat for cat in matched_categories):
            return self._build_revert_intent(question, all_matches)

        if any('negation' in cat for cat in matched_categories) and len(matched_categories) == 1:
            return self._build_negation_intent(question, all_matches)

        # Check for table corrections
        table_matches = [m for cat, m in all_matches if 'table' in cat]
        if table_matches:
            return self._build_table_intent(question, table_matches, previous_turn)

        # Check for filter corrections
        filter_matches = [m for cat, m in all_matches if 'filter' in cat]
        if filter_matches:
            return self._build_filter_intent(question, filter_matches, previous_turn)

        # Check for metric corrections
        metric_matches = [m for cat, m in all_matches if 'metric' in cat]
        if metric_matches:
            return self._build_metric_intent(question, metric_matches, previous_turn)

        # Tamil patterns
        tamil_table = [m for cat, m in all_matches if cat == 'tamil_table']
        if tamil_table:
            return self._build_table_intent(question, tamil_table, previous_turn, is_tamil=True)

        tamil_filter = [m for cat, m in all_matches if cat == 'tamil_filter']
        if tamil_filter:
            return self._build_filter_intent(question, tamil_filter, previous_turn, is_tamil=True)

        tamil_negation = [m for cat, m in all_matches if cat == 'tamil_negation']
        if tamil_negation:
            return self._build_negation_intent(question, all_matches)

        tamil_revert = [m for cat, m in all_matches if cat == 'tamil_revert']
        if tamil_revert:
            return self._build_revert_intent(question, all_matches)

        return None

    def _detect_implicit_correction(self, question: str, previous_turn: Any) -> Optional[CorrectionIntent]:
        """Detect implicit corrections that don't match explicit patterns"""

        q_lower = question.lower().strip()
        words = q_lower.split()

        # Very short responses starting with "no" might be corrections
        if len(words) <= 3 and words[0] in ['no', 'nope', 'not']:
            # Check if the rest could be a month, location, or metric
            rest = ' '.join(words[1:]) if len(words) > 1 else ''

            if rest in KNOWN_MONTHS:
                return CorrectionIntent(
                    correction_type=CorrectionType.FILTER,
                    confidence=0.7,
                    filter_corrections=[{
                        'field': 'month',
                        'old_value': None,  # Will be inferred from previous turn
                        'new_value': rest.capitalize()
                    }],
                    raw_patterns_matched=['implicit_month_correction']
                )

            if rest in KNOWN_METRICS:
                return CorrectionIntent(
                    correction_type=CorrectionType.METRIC,
                    confidence=0.7,
                    metric_corrections=[{
                        'old_metric': None,  # Will be inferred
                        'new_metric': rest
                    }],
                    raw_patterns_matched=['implicit_metric_correction']
                )

            if rest and (rest in self._known_locations or rest in self._known_categories):
                return CorrectionIntent(
                    correction_type=CorrectionType.FILTER,
                    confidence=0.6,
                    filter_corrections=[{
                        'field': 'inferred',
                        'old_value': None,
                        'new_value': rest
                    }],
                    raw_patterns_matched=['implicit_value_correction']
                )

        return None

    def _build_table_intent(
        self,
        question: str,
        matches: List[re.Match],
        previous_turn: Any,
        is_tamil: bool = False
    ) -> CorrectionIntent:
        """Build a table correction intent from matches"""

        q_lower = question.lower()

        # Check for explicit table name
        explicit_table = None
        table_hint = None
        table_type_hint = None

        # Words to skip when extracting table names
        skip_words = {'use', 'check', 'look', 'at', 'switch', 'to', 'try', 'the', 'in',
                      'from', 'table', 'sheet', 'data', 'not', 'this', 'that', 'other', 'another'}

        for match in matches:
            groups = match.groups()
            for g in groups:
                if g:
                    g_lower = g.lower().strip()

                    # Skip common words
                    if g_lower in skip_words:
                        continue

                    # Check if it's a known table (fuzzy match)
                    for known_table in self._known_tables:
                        known_lower = known_table.lower().replace('_', ' ')
                        # Match "branch details" with "Branch_Details_Table1"
                        if g_lower.replace('_', ' ') in known_lower or known_lower in g_lower.replace('_', ' '):
                            explicit_table = known_table
                            break
                        # Also try partial word matching
                        g_words = set(g_lower.replace('_', ' ').split())
                        known_words = set(known_lower.split())
                        if g_words and g_words.issubset(known_words):
                            explicit_table = known_table
                            break

                    # Check if it's a table type keyword
                    if g_lower in TABLE_TYPE_KEYWORDS:
                        table_type_hint = TABLE_TYPE_KEYWORDS[g_lower]
                    elif not explicit_table and g_lower not in skip_words:
                        table_hint = g_lower

        # Check for type hints in the full question
        if not table_type_hint:
            for keyword, ttype in TABLE_TYPE_KEYWORDS.items():
                if keyword in q_lower:
                    table_type_hint = ttype
                    break

        # Check for "other" / "another" / "different" patterns
        if any(word in q_lower for word in ['other', 'another', 'different', 'வேற', 'இன்னொரு']):
            if not table_type_hint:
                table_type_hint = 'other'  # Special marker for "pick something different"

        confidence = 0.9 if explicit_table else (0.8 if table_type_hint else 0.7)

        return CorrectionIntent(
            correction_type=CorrectionType.TABLE,
            confidence=confidence,
            explicit_table=explicit_table,
            table_hint=table_hint,
            table_type_hint=table_type_hint,
            raw_patterns_matched=[str(m.re.pattern) for m in matches]
        )

    def _build_filter_intent(
        self,
        question: str,
        matches: List[re.Match],
        previous_turn: Any,
        is_tamil: bool = False
    ) -> CorrectionIntent:
        """Build a filter correction intent from matches"""

        filter_corrections = []

        for match in matches:
            groups = [g for g in match.groups() if g]

            # Try to identify old and new values
            old_value = None
            new_value = None
            field = None

            for g in groups:
                g_clean = g.strip().lower()

                # Skip connector words
                if g_clean in ['not', 'instead', 'of', 'rather', 'than', 'for', 'in', 'to', 'with',
                              'i', 'meant', 'want', 'wanted', 'need', 'said', 'no', 'actually',
                              'change', 'replace', 'switch', 'இல்ல', 'வேண்டாம்', 'நான்', 'சொன்னது']:
                    continue

                # Check if it's a month
                if g_clean in KNOWN_MONTHS:
                    if new_value is None:
                        new_value = g.strip().capitalize()
                    else:
                        old_value = new_value
                        new_value = g.strip().capitalize()
                    field = 'month'
                    continue

                # Check if it's a known location
                if g_clean in self._known_locations:
                    if new_value is None:
                        new_value = g.strip()
                    else:
                        old_value = new_value
                        new_value = g.strip()
                    field = 'location'
                    continue

                # Check if it's a known category
                if g_clean in self._known_categories:
                    if new_value is None:
                        new_value = g.strip()
                    else:
                        old_value = new_value
                        new_value = g.strip()
                    field = 'category'
                    continue

                # Generic value
                if new_value is None:
                    new_value = g.strip()
                elif old_value is None:
                    old_value = new_value
                    new_value = g.strip()

            if new_value:
                # Try to infer old value from previous turn
                if old_value is None and previous_turn and hasattr(previous_turn, 'entities'):
                    prev_entities = previous_turn.entities or {}
                    if field == 'month' and prev_entities.get('month'):
                        old_value = prev_entities['month']
                    elif field == 'location' and prev_entities.get('location'):
                        old_value = prev_entities['location']
                    elif field == 'category' and prev_entities.get('category'):
                        old_value = prev_entities['category']

                filter_corrections.append({
                    'field': field or 'inferred',
                    'old_value': old_value,
                    'new_value': new_value
                })

        return CorrectionIntent(
            correction_type=CorrectionType.FILTER,
            confidence=0.8 if filter_corrections else 0.5,
            filter_corrections=filter_corrections,
            raw_patterns_matched=[str(m.re.pattern) for m in matches]
        )

    def _build_metric_intent(
        self,
        question: str,
        matches: List[re.Match],
        previous_turn: Any
    ) -> CorrectionIntent:
        """Build a metric correction intent from matches"""

        metric_corrections = []

        for match in matches:
            groups = [g for g in match.groups() if g]

            old_metric = None
            new_metric = None

            for g in groups:
                g_clean = g.strip().lower()

                # Skip connector words
                if g_clean in ['not', 'instead', 'of', 'rather', 'than', 'show', 'give', 'me',
                              'want', 'wanted', 'asked', 'for', 'i', 'need', 'display', 'no',
                              'check', 'based', 'on', 'by', 'based on', 'get']:
                    continue

                # Check if it's a known metric
                if g_clean in KNOWN_METRICS:
                    if new_metric is None:
                        new_metric = g_clean
                    else:
                        old_metric = new_metric
                        new_metric = g_clean

            if new_metric:
                # Try to infer old metric from previous turn
                if old_metric is None and previous_turn and hasattr(previous_turn, 'entities'):
                    prev_entities = previous_turn.entities or {}
                    if prev_entities.get('metric'):
                        old_metric = prev_entities['metric']

                metric_corrections.append({
                    'old_metric': old_metric,
                    'new_metric': new_metric
                })

        return CorrectionIntent(
            correction_type=CorrectionType.METRIC,
            confidence=0.8 if metric_corrections else 0.5,
            metric_corrections=metric_corrections,
            raw_patterns_matched=[str(m.re.pattern) for m in matches]
        )

    def _build_negation_intent(self, question: str, all_matches: List[Tuple]) -> CorrectionIntent:
        """Build a negation intent (general dissatisfaction)"""
        return CorrectionIntent(
            correction_type=CorrectionType.NEGATION,
            confidence=0.7,
            raw_patterns_matched=[str(m.re.pattern) for cat, m in all_matches]
        )

    def _build_revert_intent(self, question: str, all_matches: List[Tuple]) -> CorrectionIntent:
        """Build a revert intent"""
        return CorrectionIntent(
            correction_type=CorrectionType.REVERT,
            confidence=0.9,
            revert_to_turn=-1,  # -1 means go back to original
            raw_patterns_matched=[str(m.re.pattern) for cat, m in all_matches]
        )

    def detect_with_llm(
        self,
        question: str,
        previous_turn: Any,
        llm_client: Any = None
    ) -> Optional[CorrectionIntent]:
        """
        LLM-based detection for ambiguous cases.

        This is a fallback when pattern matching is uncertain.
        Currently a placeholder - implement with actual LLM call if needed.
        """
        # This would call the LLM with a structured prompt
        # For now, return None to indicate no detection
        return None


# Singleton instance for reuse
_detector_instance: Optional[CorrectionIntentDetector] = None


def get_correction_detector() -> CorrectionIntentDetector:
    """Get or create the singleton detector instance"""
    global _detector_instance
    if _detector_instance is None:
        _detector_instance = CorrectionIntentDetector()
    return _detector_instance


def detect_correction_intent(question: str, previous_turn: Any = None) -> Optional[CorrectionIntent]:
    """Convenience function for detecting correction intent"""
    detector = get_correction_detector()
    return detector.detect(question, previous_turn)
