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

        # 5. Question that doesn't have a verb/action
        action_words = ['show', 'what', 'how', 'give', 'tell', 'list', 'get',
                       'find', 'calculate', 'total', 'sum', 'count', 'average']
        if not any(word in q_lower for word in action_words):
            # No action word - might be a follow-up with just filter change
            return True

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

    def get_context_prompt(self) -> str:
        """
        Generate context prompt for LLM.
        Provides previous query context for follow-up understanding.
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
        self.last_activity = datetime.now()

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

        # 3. Substring match on table names
        for candidate in candidates:
            # Check if user's response contains key part of table name
            candidate_lower = candidate.lower()
            # Remove common prefixes/suffixes for matching
            clean_candidate = candidate_lower.replace('_', ' ').replace('-', ' ')

            if response_lower in clean_candidate:
                return candidate

            # Also check if table name contains user's response
            if any(word in clean_candidate for word in response_lower.split()):
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
