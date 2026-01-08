"""
Thara Personality - The friendly AI assistant personality for Thara.ai.
Like Jarvis, but for data analytics. Warm, engaging, and helpful.
"""

import random
from typing import Optional, Dict, Any, List
from datetime import datetime


class TharaPersonality:
    """
    Thara - The AI assistant personality.
    Adds warmth, engagement, and personality to responses.

    Thara is:
    - Friendly and warm (like a helpful colleague)
    - Professional yet approachable
    - Proactive with insights and suggestions
    - Remembers user preferences
    - Speaks naturally, not robotically
    """

    # Greetings for first interaction
    GREETINGS = [
        "Hi there! I'm Thara, your AI assistant for data analytics.",
        "Hello! I'm Thara, ready to help you explore your data.",
        "Hey! Thara here, your personal data companion.",
        "Welcome! I'm Thara, and I'm here to make data analysis easy for you."
    ]

    # Positive response openings (good news, high numbers, improvements)
    POSITIVE_OPENINGS = [
        "Great news, {name}!",
        "Good stuff, {name}!",
        "Here's something nice, {name}:",
        "{name}, you'll like this:",
        "Looking good, {name}!",
        "Excellent, {name}!",
        "{name}, here's a positive update:"
    ]

    # Neutral response openings (just presenting data)
    NEUTRAL_OPENINGS = [
        "Here's what I found, {name}:",
        "{name}, let me share what I found:",
        "Based on the data, {name}:",
        "Here are the numbers, {name}:",
        "{name}, here's the breakdown:",
        "I looked into that, {name}. Here's what I see:",
        "Let me show you, {name}:"
    ]

    # Negative/Concerning response openings (low numbers, declines)
    CONCERN_OPENINGS = [
        "Hmm, {name}, I noticed something:",
        "{name}, this might need attention:",
        "Worth noting, {name}:",
        "{name}, heads up on this:",
        "Something to consider, {name}:",
        "I should mention, {name}:"
    ]

    # Follow-up suggestions
    FOLLOW_UP_SUGGESTIONS = [
        "Would you like me to break this down further?",
        "Shall I compare this to another period?",
        "Want to see the trend over time?",
        "Should I look at a specific category?",
        "Any other questions about this data?",
        "Would you like more details on any of this?",
        "I can dig deeper if you'd like.",
        "Should I show you a different view of this?"
    ]

    # Comparison prompts
    COMPARISON_PROMPTS = [
        "How about comparing to {period}?",
        "Want to see how this compares to {period}?",
        "Should I show you {period} for comparison?"
    ]

    # Acknowledgments for understood requests
    ACKNOWLEDGMENTS = [
        "Got it!",
        "Sure thing!",
        "On it!",
        "Absolutely!",
        "Right away!",
        "Let me check that for you.",
        "Good question, let me look."
    ]

    # Tamil equivalents (for bilingual support)
    TAMIL_GREETINGS = [
        "வணக்கம்! நான் தாரா, உங்கள் AI உதவியாளர்.",
        "ஹலோ! தாரா இங்கே, உங்களுக்கு உதவ தயார்."
    ]

    def __init__(self, user_name: Optional[str] = None, language: str = 'en'):
        # Don't use placeholder names like "there" - just use empty if not set
        self.user_name = user_name if user_name and user_name.lower() != "there" else ""
        self.language = language  # 'en' or 'ta'
        self._response_count = 0
        self._last_sentiment = 'neutral'

    def set_name(self, name: str):
        """Set user's name for personalization"""
        # Reject placeholder names
        if name and name.lower() not in ["there", "user", "friend"]:
            self.user_name = name
        else:
            self.user_name = ""

    def set_language(self, language: str):
        """Set language preference"""
        if language in ['en', 'ta', 'english', 'tamil']:
            self.language = 'ta' if language in ['ta', 'tamil'] else 'en'

    def get_intro(self) -> str:
        """Get introduction message for new user"""
        if self.language == 'ta':
            return (
                "வணக்கம்! நான் தாரா, உங்கள் AI தனிப்பட்ட உதவியாளர். "
                "உங்களை எப்படி அழைக்கலாம்?"
            )
        return (
            "Hi! I'm Thara, your AI private assistant. "
            "How may I address you?"
        )

    def get_name_confirmation(self, name: str) -> str:
        """Confirm user's name"""
        self.user_name = name
        if self.language == 'ta':
            return (
                f"உங்களை சந்தித்ததில் மகிழ்ச்சி, {name}! "
                f"உங்கள் தரவை ஆராய்வதற்கு நான் இங்கே இருக்கிறேன். "
                f"என்னிடம் எதையும் கேளுங்கள்!"
            )
        return (
            f"Great to meet you, {name}! "
            f"I'm here to help you explore your data. "
            f"Just ask me anything!"
        )

    def get_data_ready_message(self, table_count: int, months: List[str] = None) -> str:
        """
        Message when data is loaded and ready.
        """
        name = self.user_name

        if months and len(months) > 0:
            month_str = ", ".join(sorted(months))
            if self.language == 'ta':
                return (
                    f"அருமை, {name}! {table_count} தரவு அட்டவணைகளை ஏற்றியுள்ளேன். "
                    f"மாதங்கள்: {month_str}. என்ன தெரிந்து கொள்ள விரும்புகிறீர்கள்?"
                )
            return (
                f"Perfect, {name}! I have access to {table_count} data tables "
                f"covering {month_str}. What would you like to know?"
            )
        else:
            if self.language == 'ta':
                return (
                    f"அருமை, {name}! {table_count} தரவு அட்டவணைகளை ஏற்றியுள்ளேன். "
                    f"என்ன தெரிந்து கொள்ள விரும்புகிறீர்கள்?"
                )
            return (
                f"Perfect, {name}! I have access to {table_count} data tables. "
                f"What would you like to know?"
            )

    def format_response(self, result: str, sentiment: str = 'neutral',
                       add_followup: bool = True) -> str:
        """
        Format response with personality.

        Args:
            result: The actual data/answer content
            sentiment: 'positive', 'negative', 'concern', or 'neutral'
            add_followup: Whether to add a follow-up suggestion
        """
        name = self.user_name
        self._response_count += 1
        self._last_sentiment = sentiment

        # Select opening based on sentiment
        if sentiment == 'positive':
            opening = random.choice(self.POSITIVE_OPENINGS)
        elif sentiment in ['negative', 'concern']:
            opening = random.choice(self.CONCERN_OPENINGS)
        else:
            opening = random.choice(self.NEUTRAL_OPENINGS)

        # Format with name if available, otherwise remove the name placeholder
        if name:
            opening = opening.format(name=name)
        else:
            # Remove ", {name}" or "{name}," patterns gracefully
            opening = opening.replace(", {name}", "").replace("{name}, ", "").replace("{name}", "")

        # Combine opening with result
        response = f"{opening} {result}"

        # Add follow-up suggestion occasionally (not every time)
        if add_followup and self._response_count % 3 == 0:
            response = self.add_follow_up(response)

        return response

    def add_follow_up(self, response: str, suggestion_type: str = None) -> str:
        """Add a follow-up suggestion to response"""
        if suggestion_type == 'comparison':
            # Get a comparison-specific suggestion
            periods = ['last month', 'the same period last year', 'the previous week']
            suggestion = random.choice(self.COMPARISON_PROMPTS).format(
                period=random.choice(periods)
            )
        else:
            suggestion = random.choice(self.FOLLOW_UP_SUGGESTIONS)

        return f"{response}\n\n{suggestion}"

    def get_acknowledgment(self) -> str:
        """Get a quick acknowledgment for processing"""
        return random.choice(self.ACKNOWLEDGMENTS)

    def handle_error(self, error_type: str, details: str = None) -> str:
        """Generate friendly error message"""
        name = self.user_name

        # Helper to format name in message
        def with_name(msg_with_name: str, msg_without_name: str) -> str:
            return msg_with_name if name else msg_without_name

        if error_type == 'no_data':
            if self.language == 'ta':
                if name:
                    return f"ஹ்ம், {name}, அந்த தகவலை கண்டுபிடிக்க முடியவில்லை. வேறு விதமாக கேட்கலாமா?"
                return "ஹ்ம், அந்த தகவலை கண்டுபிடிக்க முடியவில்லை. வேறு விதமாக கேட்கலாமா?"
            if name:
                return f"Hmm, {name}, I couldn't find any data matching that. Could you try rephrasing or being more specific?"
            return "Hmm, I couldn't find any data matching that. Could you try rephrasing or being more specific?"

        elif error_type == 'ambiguous':
            if self.language == 'ta':
                if name:
                    return f"{name}, பல சாத்தியமான பதில்களை கண்டேன். எதைக் குறிப்பிடுகிறீர்கள் என்று தெளிவுபடுத்த முடியுமா?"
                return "பல சாத்தியமான பதில்களை கண்டேன். எதைக் குறிப்பிடுகிறீர்கள் என்று தெளிவுபடுத்த முடியுமா?"
            if name:
                return f"{name}, I found multiple possible matches. Could you clarify which one you mean?"
            return "I found multiple possible matches. Could you clarify which one you mean?"

        elif error_type == 'table_not_found':
            if name:
                return f"I couldn't find that specific table, {name}. Let me show you what tables are available..."
            return "I couldn't find that specific table. Let me show you what tables are available..."

        elif error_type == 'column_not_found':
            if name:
                return f"That metric or column doesn't seem to be available, {name}. Would you like to see what data I can access?"
            return "That metric or column doesn't seem to be available. Would you like to see what data I can access?"

        elif error_type == 'connection':
            if name:
                return f"I'm having trouble connecting to the data, {name}. Please check the data source connection and try again."
            return "I'm having trouble connecting to the data. Please check the data source connection and try again."

        elif error_type == 'general' and details:
            # Use provided details message for general errors
            if name:
                return f"{name}, {details}"
            return details

        else:
            if self.language == 'ta':
                if name:
                    return f"மன்னிக்கவும் {name}, ஒரு சிக்கல் ஏற்பட்டது. மீண்டும் முயற்சிக்கலாமா?"
                return "மன்னிக்கவும், ஒரு சிக்கல் ஏற்பட்டது. மீண்டும் முயற்சிக்கலாமா?"
            if name:
                return f"Sorry {name}, I ran into an issue. Let's try that again - could you rephrase your question?"
            return "Sorry, I ran into an issue. Let's try that again - could you rephrase your question?"

    def format_number(self, value: float, metric_type: str = None) -> str:
        """
        Format numbers in a friendly, readable way.
        """
        if value is None:
            return "N/A"

        # Determine format based on metric type or value
        if metric_type in ['currency', 'sales', 'revenue', 'profit', 'amount']:
            # Indian numbering with rupee symbol
            return self._format_indian_currency(value)
        elif metric_type in ['percentage', 'margin', 'rate']:
            return f"{value:.1f}%"
        elif metric_type in ['count', 'orders', 'quantity']:
            return f"{int(value):,}"
        else:
            # Default formatting
            if abs(value) >= 10000000:  # 1 crore
                return f"{value/10000000:.2f} Cr"
            elif abs(value) >= 100000:  # 1 lakh
                return f"{value/100000:.2f} L"
            elif abs(value) >= 1000:
                return f"{value/1000:.1f}K"
            elif isinstance(value, float):
                return f"{value:,.2f}"
            else:
                return f"{int(value):,}"

    def _format_indian_currency(self, value: float) -> str:
        """Format value in Indian currency style"""
        if abs(value) >= 10000000:  # 1 crore
            return f"₹{value/10000000:.2f} Cr"
        elif abs(value) >= 100000:  # 1 lakh
            return f"₹{value/100000:.2f} L"
        elif abs(value) >= 1000:
            return f"₹{value:,.0f}"
        else:
            return f"₹{value:,.2f}"

    def get_insight(self, current: float, previous: float = None,
                   metric_name: str = None) -> str:
        """
        Generate insight comparing current to previous value.
        """
        if previous is None or previous == 0:
            return ""

        change = ((current - previous) / previous) * 100
        direction = "up" if change > 0 else "down"
        abs_change = abs(change)

        if abs_change < 1:
            return "That's about the same as before."
        elif abs_change < 5:
            return f"That's slightly {direction} ({abs_change:.1f}%)."
        elif abs_change < 20:
            return f"That's {direction} {abs_change:.1f}% from before."
        else:
            intensity = "significantly" if abs_change < 50 else "dramatically"
            return f"That's {intensity} {direction} - {abs_change:.1f}% change!"

    def get_proactive_insight(self, data: Dict[str, Any]) -> Optional[str]:
        """
        Generate proactive insights based on data patterns.
        Returns None if no notable insight.
        """
        # This could be enhanced with more sophisticated analysis
        insights = []

        # Check for trends
        if 'trend' in data:
            trend = data['trend']
            if trend == 'up':
                insights.append("I notice an upward trend here.")
            elif trend == 'down':
                insights.append("There seems to be a declining trend.")

        # Check for anomalies
        if 'anomaly' in data and data['anomaly']:
            insights.append("This value looks unusual compared to the pattern.")

        # Check for records
        if 'is_highest' in data and data['is_highest']:
            insights.append("This is actually the highest value in the dataset!")
        elif 'is_lowest' in data and data['is_lowest']:
            insights.append("This is the lowest value I'm seeing.")

        if insights:
            return " ".join(insights)
        return None

    def get_goodbye(self) -> str:
        """Get a friendly goodbye message"""
        name = self.user_name
        if self.language == 'ta':
            return f"மீண்டும் சந்திப்போம், {name}! எப்போது வேண்டுமானாலும் கேளுங்கள்."
        return f"Talk to you later, {name}! Feel free to ask anytime."

    def get_help_message(self) -> str:
        """Get help/guidance message"""
        name = self.user_name
        return f"""
{name}, here are some things you can ask me:

**Sales & Revenue:**
- "What were the total sales in November?"
- "Show me gross sales by category"
- "Compare October and November sales"

**Specific Queries:**
- "What were the dhoti sales in Chennai?"
- "Show me top 5 products by quantity"
- "What's the average order value?"

**Trends & Analysis:**
- "How did sales trend last month?"
- "What's the profit margin?"
- "Show me the breakdown by location"

Just ask naturally - I'll understand!
"""
