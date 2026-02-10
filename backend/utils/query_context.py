"""
Query Context Manager - Maintains context across conversation turns.
Enables follow-up questions like "How about Chennai?" or "Compare to November"
Also handles table disambiguation/clarification flow.
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
import json


@dataclass
class PendingClarification:
    """State saved when awaiting user clarification for ambiguous table selection."""
    original_question: str
    translated_question: str  # English version if Tamil
    candidates: List[str]  # Table names user can choose from
    entities: Dict[str, Any]  # Extracted entities to reuse
    is_tamil: bool = False
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class PendingCorrection:
    """
    State saved when processing a correction that needs clarification.
    Used only for NEGATION cases where user says "that's wrong" without specifics.
    Table corrections are auto-resolved without asking user.
    """
    original_question: str              # The correction message (e.g., "that's wrong")
    previous_turn_index: int            # Index of the turn being corrected
    correction_type: str                # Type from CorrectionType enum
    entities: Dict[str, Any]            # Entities from the original query
    is_tamil: bool = False
    awaiting_clarification: bool = True  # Waiting for user to specify what to correct
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class QueryTurn:
    """Represents a single query turn in conversation"""
    question: str
    resolved_question: str  # After entity merging and translation
    entities: Dict[str, Any]
    table_used: str
    filters_applied: List[Dict]
    result_summary: str
    sql_executed: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    was_followup: bool = False
    confidence: float = 0.0
    # Store actual result values for pronoun resolution
    # e.g., {"state": "West Bengal", "revenue": 1780000}
    result_values: Dict[str, Any] = field(default_factory=dict)
    # Correction tracking fields
    was_correction: bool = False                    # This turn was a correction of a previous turn
    corrected_from_turn: Optional[int] = None       # Index of the turn that was corrected
    correction_type: Optional[str] = None           # Type of correction: "table", "filter", "metric"
    # Store query plan and alternatives for re-execution during corrections
    query_plan: Optional[Dict[str, Any]] = field(default_factory=dict)
    routing_alternatives: List[tuple] = field(default_factory=list)  # [(table_name, score), ...]


class QueryContext:
    """
    Maintains context across conversation turns.
    Enables natural follow-up questions and conversation flow.

    Features:
    - Track previous queries and results
    - Merge entities from follow-up questions with previous context
    - Store user preferences (name, language, etc.)
    - Support conversation summary for context management
    """

    MAX_TURNS = 20  # Keep last N turns to prevent memory bloat

    def __init__(self, conversation_id: str = None):
        self.conversation_id = conversation_id or self._generate_id()
        self.turns: List[QueryTurn] = []
        self.user_name: Optional[str] = None
        self.user_language: str = 'en'  # 'en' or 'ta' for Tamil
        self.active_table: Optional[str] = None
        self.active_entities: Dict[str, Any] = {}
        self.created_at: datetime = datetime.now()
        self.last_activity: datetime = datetime.now()
        # Clarification state for table disambiguation
        self.pending_clarification: Optional[PendingClarification] = None
        # Correction state for negation clarification (only for "that's wrong" without specifics)
        self.pending_correction: Optional[PendingCorrection] = None
        # Date context for time-based queries (e.g., "today is November 14th")
        self.date_context: Optional[Dict[str, Any]] = None

    def _generate_id(self) -> str:
        """Generate unique conversation ID"""
        import uuid
        return str(uuid.uuid4())[:8]

    def add_turn(self, turn: QueryTurn):
        """Add a completed query turn to conversation history"""
        self.turns.append(turn)
        self.active_table = turn.table_used
        self.active_entities = turn.entities.copy()
        self.last_activity = datetime.now()

        # Trim old turns if needed
        if len(self.turns) > self.MAX_TURNS:
            self.turns = self.turns[-self.MAX_TURNS:]

    def is_followup(self, question: str) -> bool:
        """
        Detect if question is a follow-up to previous query.

        Follow-up indicators:
        1. Explicit phrases ("how about", "what about", "and for")
        2. Very short questions (1-3 words)
        3. Question that only specifies a new filter value
        4. Pronouns referring to previous context ("it", "that", "those")
        """
        if not self.turns:
            return False

        q_lower = question.lower().strip()

        # 1. Explicit follow-up phrases
        followup_phrases = [
            'how about', 'what about', 'and for', 'also for',
            'same for', 'now for', 'compare to', 'versus', 'vs',
            'and what', 'now show', 'also show', 'but for',
            'instead of', 'rather than', 'as opposed to',
            'what if', 'how does', 'can you also', 'show me also',
            'and', 'but', 'also', 'too'
        ]

        if any(q_lower.startswith(phrase) for phrase in followup_phrases):
            return True

        if any(phrase in q_lower for phrase in followup_phrases[:12]):  # Main phrases
            return True

        # 2. Very short questions are likely follow-ups
        word_count = len(question.split())
        if word_count <= 3:
            return True

        # 3. Questions starting with location/month only
        # e.g., "Chennai?", "November?", "Bangalore"
        if word_count <= 2:
            # These are very likely follow-ups
            return True

        # 4. Pronoun references
        pronouns = ['it', 'that', 'this', 'those', 'these', 'them']
        words = q_lower.split()
        if any(w in pronouns for w in words[:3]):  # Check first 3 words
            return True

        # 5. Check if query is about a DIFFERENT topic/metric - NOT a follow-up
        # This prevents "Category wise profit margin paaru" from being treated as
        # a follow-up to "Kids Wear November vs December compare pannu"
        if self.turns:
            prev_turn = self.turns[-1]
            prev_entities = prev_turn.entities or {}
            prev_question = prev_turn.question.lower() if prev_turn.question else ""

            # FRESH QUERY SIGNALS - these indicate user wants a NEW query, not continuation
            # "Monthly overall summary kaattu" should NOT carry over "profit margin" context
            fresh_query_patterns = [
                'summary', 'overview', 'overall', 'full report', 'complete',
                'all data', 'entire', 'whole', 'everything',
                'முழு', 'முழுமையான', 'அனைத்து',  # Tamil: full, complete, all
                'kaattu', 'காட்டு', 'show me all', 'list all',
                'monthly', 'weekly', 'daily', 'yearly', 'quarterly',  # Time-based summaries
                'performance', 'report', 'analytics', 'dashboard',
                'sollu', 'சொல்லு'  # Tamil: tell me
            ]

            # If query asks for summary/overview, treat as FRESH query
            # This covers: monthly summary, quarterly performance, overall report, etc.
            is_fresh_query = any(pattern in q_lower for pattern in fresh_query_patterns)

            # Check if time period is DIFFERENT from previous
            time_period_changed = (
                ('monthly' in q_lower and 'monthly' not in prev_question) or
                ('quarterly' in q_lower and 'quarterly' not in prev_question) or
                ('weekly' in q_lower and 'weekly' not in prev_question) or
                ('yearly' in q_lower and 'yearly' not in prev_question) or
                ('daily' in q_lower and 'daily' not in prev_question)
            )

            prev_was_specific = bool(
                'profit' in prev_question or 'margin' in prev_question or
                'compare' in prev_question or 'vs' in prev_question or
                prev_entities.get('metric') or prev_entities.get('comparison') or
                prev_entities.get('category')  # Also reset if previous had category filter
            )

            # Fresh query OR different time period = NEW query, not follow-up
            if is_fresh_query and (prev_was_specific or time_period_changed):
                # User wants fresh summary, not continuation of specific analysis
                # CRITICAL: Clear active entities to prevent context bleed
                self._clear_metric_context()
                return False

            # Even if prev wasn't specific, a fresh query with different intent is NEW
            if is_fresh_query and self.turns:
                # Clear context anyway for any fresh query pattern
                self._clear_metric_context()
                return False

            # Metric keywords - different metrics = different query intent
            metric_keywords = {
                'profit_margin': ['profit margin', 'profit', 'margin', 'லாபம்', 'லாப'],
                'revenue': ['revenue', 'sales', 'total sales', 'வருவாய்', 'விற்பனை'],
                'cost': ['cost', 'expense', 'spending', 'செலவு'],
                'comparison': ['compare', 'comparison', 'vs', 'versus', 'ஒப்பிடு', 'compare pannu'],
                'growth': ['growth', 'trend', 'increase', 'decrease', 'வளர்ச்சி'],
                'count': ['count', 'how many', 'number of', 'எத்தனை']
            }

            # Detect metric in new query
            new_metrics = set()
            for metric, keywords in metric_keywords.items():
                if any(kw in q_lower for kw in keywords):
                    new_metrics.add(metric)

            # Detect metric in previous query
            prev_metrics = set()
            for metric, keywords in metric_keywords.items():
                if any(kw in prev_question for kw in keywords):
                    prev_metrics.add(metric)

            # If new query has a different PRIMARY metric, it's NOT a follow-up
            # e.g., "profit margin" vs "comparison" are clearly different intents
            if new_metrics and prev_metrics and not new_metrics.intersection(prev_metrics):
                # Different metrics detected - this is a NEW query
                return False

            # Check for aggregation patterns - "X wise" means aggregate by X, not filter
            aggregation_patterns = [
                'category wise', 'categorywise', 'product wise', 'productwise',
                'month wise', 'monthwise', 'state wise', 'statewise',
                'area wise', 'areawise', 'branch wise', 'branchwise',
                'வகை வாரியாக', 'மாதம் வாரியாக'  # Tamil: category-wise, month-wise
            ]

            # If new query asks for aggregation and previous had a specific filter, it's NEW
            is_aggregation_query = any(pattern in q_lower for pattern in aggregation_patterns)
            prev_had_specific_filter = bool(
                prev_entities.get('category') or
                prev_entities.get('location') or
                prev_entities.get('month')
            )

            if is_aggregation_query and prev_had_specific_filter:
                # User wants a breakdown, not a continuation of filtered query
                return False

            # Check for dimension shift (category, location, time)
            dimension_keywords = {
                'category': ['category', 'categories', 'product', 'products', 'item', 'items'],
                'location': ['location', 'area', 'branch', 'city', 'state', 'zone', 'region'],
                'time': ['month', 'year', 'week', 'day', 'date', 'january', 'february',
                         'march', 'april', 'may', 'june', 'july', 'august',
                         'september', 'october', 'november', 'december']
            }

            # Detect ALL dimensions in new query (don't break on first match)
            new_dimensions = set()
            for dim, keywords in dimension_keywords.items():
                if any(kw in q_lower for kw in keywords):
                    new_dimensions.add(dim)

            # If query mentions a new dimension AND has new metrics, it's definitely new
            prev_dimension = None
            if prev_entities.get('location'):
                prev_dimension = 'location'
            elif prev_entities.get('category'):
                prev_dimension = 'category'
            elif prev_entities.get('month'):
                prev_dimension = 'time'

            # New query with different focus dimension and no follow-up phrases
            if (new_dimensions and prev_dimension and
                prev_dimension not in new_dimensions and
                not any(phrase in q_lower for phrase in ['same', 'also', 'too', 'as well', 'and'])):
                return False

            # Entity lookup queries are NEW queries - don't inherit location context
            # "Who worked on X", "Which employee", "Find person" should search ALL locations
            entity_lookup_keywords = ['who', 'which employee', 'find person', 'search for', 'locate',
                                      'யார்', 'எந்த ஊழியர்']  # Tamil: who, which employee
            is_entity_lookup = any(kw in q_lower for kw in entity_lookup_keywords)
            if is_entity_lookup and self.active_entities.get('location'):
                # User asking about a person - don't inherit location from previous query
                print(f"    [QueryContext] Entity lookup detected - clearing location inheritance")
                if 'location' in self.active_entities:
                    del self.active_entities['location']
                return False

        return False

    def merge_entities(self, new_entities: Dict[str, Any]) -> Dict[str, Any]:
        """
        Merge new entities with previous context.
        New values override old, but old values are kept if new is None/empty.
        """
        if not self.active_entities:
            return new_entities

        merged = {}

        # Keys that should be inherited from previous context
        inheritable_keys = ['month', 'metric', 'category', 'location', 'aggregation', 'date_specific']

        # CRITICAL: Don't inherit location for entity lookup queries
        # This prevents "Rajesh Kumar" query from inheriting "Bangalore" from previous query
        q_lower = new_entities.get('raw_question', '').lower()
        entity_lookup_keywords = ['who', 'which employee', 'find', 'search', 'யார்', 'எந்த']
        is_entity_lookup = any(kw in q_lower for kw in entity_lookup_keywords)
        if is_entity_lookup:
            inheritable_keys = [k for k in inheritable_keys if k != 'location']
            print(f"    [QueryContext] Entity lookup - skipping location inheritance")

        for key in inheritable_keys:
            new_val = new_entities.get(key)
            prev_val = self.active_entities.get(key)

            # New value takes precedence if set and not empty
            if new_val is not None and new_val != '':
                merged[key] = new_val
            elif prev_val is not None and prev_val != '':
                merged[key] = prev_val

        # Always use new values for these (don't inherit)
        merged['comparison'] = new_entities.get('comparison', False)
        merged['time_period'] = new_entities.get('time_period')
        merged['explicit_table'] = new_entities.get('explicit_table')
        merged['raw_question'] = new_entities.get('raw_question')

        return merged

    def set_date_context(self, date_info: Dict[str, Any]):
        """
        Set date context for subsequent queries.

        Args:
            date_info: Dict with month, day, year info
                       e.g., {'month': 'November', 'day': 14, 'year': 2025}
        """
        self.date_context = date_info
        self.last_activity = datetime.now()
        print(f"    [QueryContext] Date context set: {date_info}")

    def get_date_context(self) -> Optional[Dict[str, Any]]:
        """Get current date context if set."""
        return self.date_context

    def clear_date_context(self):
        """Clear date context."""
        self.date_context = None

    def get_context_prompt(self) -> str:
        """
        Generate context prompt for LLM.
        Provides previous query context for follow-up understanding.

        CRITICAL for pronoun resolution:
        - If user asks "Which state has highest profit?" -> Answer: "West Bengal"
        - Then user asks "In that state, which branch..." -> "that state" = West Bengal
        - We include result_values so LLM can resolve "that", "this", "in that"
        """
        if not self.turns:
            return ""

        last_turn = self.turns[-1]

        context_parts = [
            "## Previous Query Context",
            f"Table used: {last_turn.table_used}",
            f"Question: {last_turn.question}",
            f"Result: {last_turn.result_summary}"
        ]

        # CRITICAL: Add result values for pronoun resolution
        # This allows "that state", "that branch", "in that region" to be resolved
        if last_turn.result_values:
            result_parts = []
            for key, value in last_turn.result_values.items():
                if value is not None:
                    result_parts.append(f"{key}={value}")
            if result_parts:
                context_parts.append(f"**Answer values (for 'that/this' resolution):** {', '.join(result_parts)}")
                # Add explicit pronoun mapping hints
                for key, value in last_turn.result_values.items():
                    key_lower = key.lower()
                    if 'state' in key_lower:
                        context_parts.append(f"  -> 'that state' or 'in that state' refers to: {value}")
                    elif 'branch' in key_lower:
                        context_parts.append(f"  -> 'that branch' or 'in that branch' refers to: {value}")
                    elif 'area' in key_lower or 'region' in key_lower or 'location' in key_lower:
                        context_parts.append(f"  -> 'that area/region' refers to: {value}")
                    elif 'category' in key_lower:
                        context_parts.append(f"  -> 'that category' refers to: {value}")

        # Add filters
        if last_turn.filters_applied:
            filters_str = ", ".join([
                f"{f.get('column', 'unknown')}={f.get('value', 'unknown')}"
                for f in last_turn.filters_applied
            ])
            context_parts.append(f"Filters applied: {filters_str}")

        # Add entities
        if last_turn.entities:
            entities_str = ", ".join([
                f"{k}={v}" for k, v in last_turn.entities.items()
                if v and k not in ['raw_question', 'comparison']
            ])
            if entities_str:
                context_parts.append(f"Entities: {entities_str}")

        return "\n".join(context_parts)

    def get_recent_context(self, num_turns: int = 3) -> str:
        """
        Get context from recent turns (not just the last one).
        Useful for more complex follow-ups.
        """
        if not self.turns:
            return ""

        recent = self.turns[-num_turns:]
        context_parts = ["## Conversation History"]

        for i, turn in enumerate(recent, 1):
            context_parts.append(f"\n### Turn {i}:")
            context_parts.append(f"Q: {turn.question}")
            context_parts.append(f"Table: {turn.table_used}")
            context_parts.append(f"Result: {turn.result_summary}")

        return "\n".join(context_parts)

    def get_active_filters(self) -> List[Dict]:
        """Get filters from the last query"""
        if not self.turns:
            return []
        return self.turns[-1].filters_applied.copy()

    def get_active_table(self) -> Optional[str]:
        """Get the table used in the last query"""
        return self.active_table

    def clear(self):
        """Clear context (start new conversation)"""
        self.turns = []
        self.active_table = None
        self.active_entities = {}
        self.pending_clarification = None
        self.pending_correction = None
        self.last_activity = datetime.now()

    def _clear_metric_context(self):
        """
        Clear metric-specific context when a fresh query is detected.
        This prevents context bleed like "profit margin" carrying over to "overall summary".

        Called internally by is_followup() when fresh query signals are detected.
        Does NOT clear location context (user might still want same location).
        """
        if self.active_entities:
            # Clear metric-related fields that shouldn't carry over to fresh queries
            keys_to_clear = ['metric', 'comparison', 'category', 'aggregation']
            for key in keys_to_clear:
                if key in self.active_entities:
                    del self.active_entities[key]
            print(f"    [QueryContext] Cleared metric context for fresh query")

    # ===== CLARIFICATION STATE MANAGEMENT =====

    def set_pending_clarification(
        self,
        original_question: str,
        translated_question: str,
        candidates: List[str],
        entities: Dict[str, Any],
        is_tamil: bool = False
    ):
        """
        Save state when we need to ask user for table clarification.

        Args:
            original_question: User's original question
            translated_question: English version (same if English input)
            candidates: List of table names to choose from
            entities: Extracted entities to reuse when user responds
            is_tamil: Whether the original was in Tamil
        """
        self.pending_clarification = PendingClarification(
            original_question=original_question,
            translated_question=translated_question,
            candidates=candidates,
            entities=entities,
            is_tamil=is_tamil
        )
        self.last_activity = datetime.now()

    def has_pending_clarification(self) -> bool:
        """Check if we're awaiting user's table selection."""
        return self.pending_clarification is not None

    def get_pending_clarification(self) -> Optional[PendingClarification]:
        """Get the pending clarification state."""
        return self.pending_clarification

    def clear_pending_clarification(self):
        """Clear clarification state after user responds."""
        self.pending_clarification = None

    def match_clarification_response(self, user_response: str) -> Optional[str]:
        """
        Try to match user's response to one of the pending clarification options.

        Args:
            user_response: User's response (e.g., "item sales", "1", "first one")

        Returns:
            Matched table name, or None if no match
        """
        if not self.pending_clarification:
            return None

        candidates = self.pending_clarification.candidates
        response_lower = user_response.lower().strip()

        # Month name mappings (full -> abbreviation and vice versa)
        month_mappings = {
            'january': ['jan', '01', '1'], 'jan': ['january', '01', '1'],
            'february': ['feb', '02', '2'], 'feb': ['february', '02', '2'],
            'march': ['mar', '03', '3'], 'mar': ['march', '03', '3'],
            'april': ['apr', '04', '4'], 'apr': ['april', '04', '4'],
            'may': ['05', '5'],
            'june': ['jun', '06', '6'], 'jun': ['june', '06', '6'],
            'july': ['jul', '07', '7'], 'jul': ['july', '07', '7'],
            'august': ['aug', '08', '8'], 'aug': ['august', '08', '8'],
            'september': ['sep', 'sept', '09', '9'], 'sep': ['september', '09', '9'], 'sept': ['september', '09', '9'],
            'october': ['oct', '10'], 'oct': ['october', '10'],
            'november': ['nov', '11'], 'nov': ['november', '11'],
            'december': ['dec', '12'], 'dec': ['december', '12']
        }

        # Date format mappings (ordinal -> numeric)
        date_mappings = {
            '1st': ['01', '1'], '2nd': ['02', '2'], '3rd': ['03', '3'], '4th': ['04', '4'],
            '5th': ['05', '5'], '6th': ['06', '6'], '7th': ['07', '7'], '8th': ['08', '8'],
            '9th': ['09', '9'], '10th': ['10'], '11th': ['11'], '12th': ['12'],
            '13th': ['13'], '14th': ['14'], '15th': ['15'], '16th': ['16'],
            '17th': ['17'], '18th': ['18'], '19th': ['19'], '20th': ['20'],
            '21st': ['21'], '22nd': ['22'], '23rd': ['23'], '24th': ['24'],
            '25th': ['25'], '26th': ['26'], '27th': ['27'], '28th': ['28'],
            '29th': ['29'], '30th': ['30'], '31st': ['31']
        }

        def expand_terms(text: str) -> set:
            """Expand month names and dates to include variations"""
            words = set(text.lower().split())
            expanded = set(words)
            for word in words:
                # Expand months
                if word in month_mappings:
                    expanded.update(month_mappings[word])
                # Expand ordinal dates
                if word in date_mappings:
                    expanded.update(date_mappings[word])
                # Also try to match plain numbers to ordinals
                if word.isdigit():
                    num = int(word)
                    if 1 <= num <= 31:
                        expanded.add(f"{num:02d}")  # Zero-padded
            return expanded

        # 1. Direct number match (1, 2, 3, etc.)
        if response_lower.isdigit():
            idx = int(response_lower) - 1  # 1-based to 0-based
            if 0 <= idx < len(candidates):
                return candidates[idx]

        # 2. Ordinal match (first, second, third)
        ordinals = {
            'first': 0, 'second': 1, 'third': 2, 'fourth': 3, 'fifth': 4,
            '1st': 0, '2nd': 1, '3rd': 2, '4th': 3, '5th': 4,
            'one': 0, 'two': 1, 'three': 2, 'four': 3, 'five': 4,
            # Tamil ordinals
            'முதல்': 0, 'இரண்டாவது': 1, 'மூன்றாவது': 2,
            'ஒன்று': 0, 'இரண்டு': 1, 'மூன்று': 2
        }
        for ordinal, idx in ordinals.items():
            if ordinal in response_lower:
                if idx < len(candidates):
                    return candidates[idx]

        # 3. Substring match on table names (ONLY for meaningful words)
        # Skip common words that could cause false matches
        skip_words = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been',
                      'what', 'who', 'how', 'where', 'when', 'why', 'which',
                      'your', 'you', 'my', 'me', 'i', 'we', 'they', 'it',
                      'do', 'does', 'did', 'can', 'could', 'will', 'would',
                      'to', 'of', 'in', 'on', 'at', 'for', 'with', 'by',
                      'today', 'name', 'hello', 'hi', 'hey', 'thanks'}

        for candidate in candidates:
            # Check if user's response contains key part of table name
            candidate_lower = candidate.lower()
            # Remove common prefixes/suffixes for matching
            clean_candidate = candidate_lower.replace('_', ' ').replace('-', ' ')
            candidate_words = set(clean_candidate.split())

            if response_lower in clean_candidate:
                return candidate

            # FIXED: Check for WHOLE WORD matches only (not substrings)
            # And skip common words that could cause false positives
            response_words = [w for w in response_lower.split() if w not in skip_words and len(w) > 2]
            if response_words and any(word in candidate_words for word in response_words):
                return candidate

        # 4. Enhanced keyword matching with month/date expansion
        response_expanded = expand_terms(response_lower)
        best_match = None
        best_score = 0

        for candidate in candidates:
            candidate_clean = candidate.lower().replace('_', ' ').replace('-', ' ')
            candidate_expanded = expand_terms(candidate_clean)

            # Score based on overlapping expanded terms
            overlap = response_expanded & candidate_expanded
            # Filter out common words
            overlap = {w for w in overlap if w not in {'the', 'a', 'an', 'for', 'in', 'on', 'at', 'to', 'what', 'about', 'specifically'}}
            score = len(overlap)

            if score > best_score:
                best_score = score
                best_match = candidate

        if best_score > 0:
            return best_match

        return None

    # ===== CORRECTION STATE MANAGEMENT =====
    # Used only for NEGATION cases where user says "that's wrong" without specifics
    # Table/Filter/Metric corrections are auto-resolved without user prompts

    def set_pending_correction_state(
        self,
        original_question: str,
        correction_type: str,
        is_tamil: bool = False
    ):
        """
        Save state when we need to ask user for correction clarification.
        Only used for NEGATION cases ("that's wrong" without specifics).

        Args:
            original_question: User's correction message
            correction_type: Type of correction (usually "negation")
            is_tamil: Whether the original was in Tamil
        """
        if not self.turns:
            return

        previous_turn = self.turns[-1]
        self.pending_correction = PendingCorrection(
            original_question=original_question,
            previous_turn_index=len(self.turns) - 1,
            correction_type=correction_type,
            entities=previous_turn.entities.copy() if previous_turn.entities else {},
            is_tamil=is_tamil,
            awaiting_clarification=True
        )
        self.last_activity = datetime.now()

    def has_pending_correction_state(self) -> bool:
        """Check if we're awaiting user's correction clarification."""
        return self.pending_correction is not None

    def get_pending_correction_state(self) -> Optional[PendingCorrection]:
        """Get the pending correction state."""
        return self.pending_correction

    def clear_pending_correction_state(self):
        """Clear correction state after resolution."""
        self.pending_correction = None

    def find_original_turn(self, current_turn: Optional[QueryTurn] = None) -> Optional[QueryTurn]:
        """
        Find the original turn before any corrections in a chain.

        If a user makes multiple corrections in sequence, this traverses back
        to find the original query before any corrections were made.

        Args:
            current_turn: The turn to trace back from (default: last turn)

        Returns:
            The original turn before corrections, or None if no turns exist
        """
        if not self.turns:
            return None

        if current_turn is None:
            current_turn = self.turns[-1]

        # If this turn wasn't a correction, it's the original
        if not current_turn.was_correction:
            return current_turn

        # Traverse back through correction chain
        turn_index = current_turn.corrected_from_turn
        visited = set()  # Prevent infinite loops

        while turn_index is not None and turn_index >= 0 and turn_index not in visited:
            visited.add(turn_index)
            if turn_index < len(self.turns):
                turn = self.turns[turn_index]
                if not turn.was_correction:
                    return turn
                turn_index = turn.corrected_from_turn
            else:
                break

        # Fallback to first turn
        return self.turns[0] if self.turns else None

    def get_turn_by_index(self, index: int) -> Optional[QueryTurn]:
        """Get a turn by its index in the conversation history."""
        if 0 <= index < len(self.turns):
            return self.turns[index]
        return None

    def get_last_turn(self) -> Optional[QueryTurn]:
        """Get the most recent turn."""
        return self.turns[-1] if self.turns else None

    def set_user_name(self, name: str):
        """Store user's name for personalization"""
        self.user_name = name

    def get_user_name(self) -> Optional[str]:
        """Get user's name"""
        return self.user_name

    def set_language(self, language: str):
        """Set user's preferred language ('en' or 'ta')"""
        if language in ['en', 'ta', 'tamil', 'english']:
            self.user_language = 'ta' if language in ['ta', 'tamil'] else 'en'

    def get_language(self) -> str:
        """Get user's preferred language"""
        return self.user_language

    def to_dict(self) -> Dict[str, Any]:
        """Serialize context to dictionary (for storage/transmission)"""
        result = {
            'conversation_id': self.conversation_id,
            'user_name': self.user_name,
            'user_language': self.user_language,
            'active_table': self.active_table,
            'active_entities': self.active_entities,
            'turn_count': len(self.turns),
            'created_at': self.created_at.isoformat(),
            'last_activity': self.last_activity.isoformat(),
            'recent_questions': [t.question for t in self.turns[-5:]],
            'has_pending_clarification': self.pending_clarification is not None
        }
        if self.pending_clarification:
            result['pending_clarification'] = {
                'original_question': self.pending_clarification.original_question,
                'translated_question': self.pending_clarification.translated_question,
                'candidates': self.pending_clarification.candidates,
                'entities': self.pending_clarification.entities,
                'is_tamil': self.pending_clarification.is_tamil
            }
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'QueryContext':
        """Deserialize context from dictionary"""
        ctx = cls(conversation_id=data.get('conversation_id'))
        ctx.user_name = data.get('user_name')
        ctx.user_language = data.get('user_language', 'en')
        ctx.active_table = data.get('active_table')
        ctx.active_entities = data.get('active_entities', {})
        # Restore pending clarification if present
        if data.get('pending_clarification'):
            pc = data['pending_clarification']
            ctx.pending_clarification = PendingClarification(
                original_question=pc.get('original_question', ''),
                translated_question=pc.get('translated_question', ''),
                candidates=pc.get('candidates', []),
                entities=pc.get('entities', {}),
                is_tamil=pc.get('is_tamil', False)
            )
        return ctx

    def get_summary(self) -> str:
        """Get summary of conversation for debugging"""
        lines = [
            f"Conversation ID: {self.conversation_id}",
            f"User: {self.user_name or 'Unknown'}",
            f"Language: {self.user_language}",
            f"Turns: {len(self.turns)}",
            f"Active table: {self.active_table or 'None'}",
            f"Last activity: {self.last_activity.strftime('%H:%M:%S')}"
        ]

        if self.active_entities:
            entities_str = ", ".join([
                f"{k}={v}" for k, v in self.active_entities.items()
                if v and k not in ['raw_question']
            ])
            lines.append(f"Active entities: {entities_str}")

        return "\n".join(lines)


class ConversationManager:
    """
    Manages multiple conversation contexts (for multi-user scenarios).
    """

    def __init__(self):
        self._contexts: Dict[str, QueryContext] = {}
        self._default_context: Optional[QueryContext] = None

    def get_context(self, conversation_id: str = None) -> QueryContext:
        """Get or create context for a conversation"""
        if conversation_id is None:
            # Return default context (single user mode)
            if self._default_context is None:
                self._default_context = QueryContext()
            return self._default_context

        if conversation_id not in self._contexts:
            self._contexts[conversation_id] = QueryContext(conversation_id)

        return self._contexts[conversation_id]

    def clear_context(self, conversation_id: str = None):
        """Clear a specific conversation context"""
        if conversation_id is None:
            if self._default_context:
                self._default_context.clear()
        elif conversation_id in self._contexts:
            self._contexts[conversation_id].clear()

    def remove_context(self, conversation_id: str):
        """Remove a conversation context entirely"""
        if conversation_id in self._contexts:
            del self._contexts[conversation_id]

    def get_all_conversation_ids(self) -> List[str]:
        """Get all active conversation IDs"""
        return list(self._contexts.keys())

    def cleanup_old_contexts(self, max_age_hours: int = 24):
        """Remove contexts older than specified hours"""
        from datetime import timedelta
        cutoff = datetime.now() - timedelta(hours=max_age_hours)

        to_remove = []
        for conv_id, ctx in self._contexts.items():
            if ctx.last_activity < cutoff:
                to_remove.append(conv_id)

        for conv_id in to_remove:
            del self._contexts[conv_id]

        return len(to_remove)
