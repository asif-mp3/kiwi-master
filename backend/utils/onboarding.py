"""
Onboarding Manager - Manages user onboarding flow for Kiwi.
Handles first-time user experience with Thara personality.
"""

from typing import Optional, Dict, Any, List
from enum import Enum
from utils.personality import TharaPersonality
from utils.permanent_memory import load_memory, update_memory


class OnboardingState(Enum):
    """States in the onboarding flow"""
    INIT = "init"                      # Initial state
    AWAITING_NAME = "awaiting_name"    # Asked for name, waiting for response
    AWAITING_LANGUAGE = "awaiting_language"  # Asked for language preference
    DATA_LOADING = "data_loading"      # Data is being loaded
    COMPLETE = "complete"              # Onboarding done


class OnboardingManager:
    """
    Manages user onboarding flow.

    Flow:
    1. Greet user, introduce Thara
    2. Ask for name preference
    3. (Optional) Ask for language preference
    4. Confirm and summarize available data
    5. Ready for queries

    The manager maintains state to handle the conversation flow.
    """

    def __init__(self):
        self.personality = TharaPersonality()
        self.state = OnboardingState.INIT
        self._pending_name = None

    def start_onboarding(self) -> Dict[str, Any]:
        """
        Start onboarding flow.

        Returns:
            Dict with:
            - message: Response to show user
            - state: Current onboarding state
            - awaiting: What input we're waiting for (or None)
            - is_complete: Whether onboarding is done
        """
        # Check if we already know the user
        memory = load_memory()
        user_name = memory.get('user_preferences', {}).get('address_as')

        if user_name:
            # Returning user - welcome back
            self.personality.set_name(user_name)
            self.state = OnboardingState.COMPLETE

            # Check language preference
            language = memory.get('user_preferences', {}).get('language', 'en')
            self.personality.set_language(language)

            return {
                'message': f"Welcome back, {user_name}! How can I help you today?",
                'state': 'complete',
                'awaiting': None,
                'is_complete': True,
                'user_name': user_name
            }

        # New user - start onboarding
        self.state = OnboardingState.AWAITING_NAME

        return {
            'message': self.personality.get_intro(),
            'state': 'awaiting_name',
            'awaiting': 'name',
            'is_complete': False
        }

    def process_input(self, user_input: str) -> Dict[str, Any]:
        """
        Process user input during onboarding.

        Args:
            user_input: The user's response

        Returns:
            Dict with response and state info
        """
        if self.state == OnboardingState.AWAITING_NAME:
            return self._process_name(user_input)
        elif self.state == OnboardingState.AWAITING_LANGUAGE:
            return self._process_language(user_input)
        else:
            # Already complete or in wrong state
            return {
                'message': "I'm ready to help! What would you like to know?",
                'state': 'complete',
                'awaiting': None,
                'is_complete': True
            }

    def _process_name(self, name: str) -> Dict[str, Any]:
        """
        Process user's name response.
        """
        # Clean up name
        name = name.strip()

        # Handle common responses
        if name.lower() in ['sir', 'madam', 'boss']:
            display_name = name.capitalize()
        elif name.lower() in ['skip', 'no', 'none', "don't", 'nothing', 'friend', 'there', 'user']:
            # User doesn't want to share name - don't store a placeholder
            display_name = ""
        else:
            # Capitalize first letter of each word
            display_name = ' '.join(word.capitalize() for word in name.split())

        # Only store in memory if we have an actual name
        if display_name:
            update_memory('user_preferences', 'address_as', display_name)
            self.personality.set_name(display_name)

        self.state = OnboardingState.COMPLETE

        # Generate appropriate confirmation message
        if display_name:
            message = self.personality.get_name_confirmation(display_name)
        else:
            message = "No problem! I'm Thara, ready to help you explore your data. Just ask me anything!"

        return {
            'message': message,
            'state': 'complete',
            'awaiting': None,
            'is_complete': True,
            'user_name': display_name if display_name else None
        }

    def _process_language(self, language: str) -> Dict[str, Any]:
        """
        Process language preference.
        """
        lang = language.lower().strip()

        if lang in ['tamil', 'ta', 'தமிழ்']:
            lang_code = 'ta'
        else:
            lang_code = 'en'

        # Store in memory
        update_memory('user_preferences', 'language', lang_code)

        self.personality.set_language(lang_code)
        self.state = OnboardingState.COMPLETE

        return {
            'message': self.personality.get_name_confirmation(self.personality.user_name),
            'state': 'complete',
            'awaiting': None,
            'is_complete': True,
            'language': lang_code
        }

    def get_data_summary(self, profiles: Dict[str, Any]) -> str:
        """
        Generate summary of available data after dataset is connected.

        Args:
            profiles: Dictionary of table profiles from ProfileStore
        """
        table_count = len(profiles)

        # Extract unique months from profiles
        months = set()
        for name, profile in profiles.items():
            month = profile.get('date_range', {}).get('month')
            if month:
                months.add(month)

            # Also check table name for month keywords
            name_lower = name.lower()
            month_names = ['january', 'february', 'march', 'april', 'may', 'june',
                          'july', 'august', 'september', 'october', 'november', 'december']
            for m in month_names:
                if m in name_lower:
                    months.add(m.capitalize())

        return self.personality.get_data_ready_message(
            table_count=table_count,
            months=list(months) if months else None
        )

    def is_onboarding_complete(self) -> bool:
        """Check if onboarding is done"""
        return self.state == OnboardingState.COMPLETE

    def is_awaiting_input(self) -> bool:
        """Check if we're waiting for user input during onboarding"""
        return self.state in [OnboardingState.AWAITING_NAME, OnboardingState.AWAITING_LANGUAGE]

    def get_state(self) -> str:
        """Get current state as string"""
        return self.state.value

    def reset(self):
        """Reset onboarding state (for testing)"""
        self.state = OnboardingState.INIT
        self._pending_name = None

    def skip_onboarding(self, user_name: str = "User"):
        """
        Skip onboarding and set defaults (for testing or CLI use).
        """
        self.personality.set_name(user_name)
        self.state = OnboardingState.COMPLETE
        update_memory('user_preferences', 'address_as', user_name)


class OnboardingDetector:
    """
    Detects if a message is related to onboarding.
    """

    # Name-related patterns
    NAME_PATTERNS = [
        "my name is", "call me", "i am", "i'm", "address me as",
        "you can call me", "name's", "just call me"
    ]

    # Language-related patterns
    LANGUAGE_PATTERNS = [
        "speak in tamil", "talk in tamil", "tamil please",
        "தமிழில்", "தமிழ்", "english please", "speak english"
    ]

    @classmethod
    def is_name_statement(cls, text: str) -> bool:
        """Check if text is stating a name"""
        text_lower = text.lower()
        return any(pattern in text_lower for pattern in cls.NAME_PATTERNS)

    @classmethod
    def extract_name(cls, text: str) -> Optional[str]:
        """Extract name from a name statement"""
        text_lower = text.lower()

        for pattern in cls.NAME_PATTERNS:
            if pattern in text_lower:
                # Get text after the pattern
                idx = text_lower.find(pattern)
                after = text[idx + len(pattern):].strip()

                # Clean up - remove punctuation and take first few words
                import re
                after = re.sub(r'[.,!?]', '', after)
                words = after.split()

                if words:
                    # Take up to 3 words (for names like "John Smith Jr")
                    name = ' '.join(words[:3])
                    return name.strip()

        # If no pattern matched but text is short, might just be the name
        if len(text.split()) <= 3:
            import re
            name = re.sub(r'[.,!?]', '', text)
            return name.strip()

        return None

    @classmethod
    def is_language_preference(cls, text: str) -> bool:
        """Check if text is stating language preference"""
        text_lower = text.lower()
        return any(pattern in text_lower for pattern in cls.LANGUAGE_PATTERNS)

    @classmethod
    def extract_language(cls, text: str) -> str:
        """Extract language preference"""
        text_lower = text.lower()

        if any(t in text_lower for t in ['tamil', 'தமிழ்', 'ta']):
            return 'ta'
        return 'en'


def get_user_name() -> Optional[str]:
    """
    Utility function to get stored user name.
    """
    memory = load_memory()
    return memory.get('user_preferences', {}).get('address_as')


def set_user_name(name: str) -> bool:
    """
    Utility function to set user name.
    """
    return update_memory('user_preferences', 'address_as', name)


def get_user_language() -> str:
    """
    Utility function to get stored language preference.
    """
    memory = load_memory()
    return memory.get('user_preferences', {}).get('language', 'en')


def set_user_language(language: str) -> bool:
    """
    Utility function to set language preference.
    """
    return update_memory('user_preferences', 'language', language)
