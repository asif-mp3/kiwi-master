"""
Thara Personality - A professional, friendly assistant for Thara.ai.
Warm and approachable while maintaining professionalism - helpful, knowledgeable, and genuinely supportive.
"""

import random
from typing import Optional, Dict, Any, List
from datetime import datetime


class TharaPersonality:
    """
    Thara - A professional, friendly data assistant.
    Adds warmth and genuine helpfulness to every interaction.

    Thara is:
    - Professional and friendly (approachable yet business-appropriate)
    - Warm and supportive (genuinely helpful without being overly casual)
    - Brilliant with data (knowledgeable, delivers with confidence)
    - Emotionally intelligent (responds appropriately to user's tone)
    - Natural and conversational (never robotic, always genuine)
    - Handles questions gracefully (data questions and general queries)
    """

    # Greetings for first interaction - professional and friendly
    GREETINGS = [
        "Hi there! I'm Thara, your data assistant. How can I help you today?",
        "Hello! I'm Thara. I'm here to help you explore your data. What would you like to know?",
        "Hi! I'm Thara - ready to help you find the insights you need. What can I do for you?",
        "Hello! Thara here. Let me know what data you'd like to explore.",
        "Hi there! I'm Thara, happy to assist with your data questions. What's on your mind?",
        "Hello! I'm Thara. Ready to help you get the most from your data."
    ]

    # Positive response openings (good news, high numbers, improvements) - Professional & Positive
    POSITIVE_OPENINGS = [
        "Good news, {name}!",
        "Great results here, {name}:",
        "{name}, the numbers look strong:",
        "Here's some positive news, {name}:",
        "{name}, this is looking good:",
        "Excellent results, {name}:",
        "{name}, here's what I found - and it's good:"
    ]

    # Neutral response openings (just presenting data) - Professional & Clear
    NEUTRAL_OPENINGS = [
        "Here's what I found, {name}:",
        "{name}, here are the results:",
        "Looking at the data, {name}:",
        "Here's the breakdown, {name}:",
        "{name}, I've pulled the numbers:",
        "Based on the data, {name}:",
        "{name}, here's what the data shows:"
    ]

    # Negative/Concerning response openings (low numbers, declines) - Professional & Supportive
    CONCERN_OPENINGS = [
        "{name}, here's something worth noting:",
        "{name}, I noticed something that may need attention:",
        "Just a heads up, {name}:",
        "{name}, here's an area to watch:",
        "{name}, the data shows something to consider:",
        "Worth mentioning, {name}:"
    ]

    # Follow-up suggestions - Helpful & Professional
    FOLLOW_UP_SUGGESTIONS = [
        "Would you like me to dig deeper into this?",
        "Want me to compare this with another time period?",
        "I can show you the trend if you're interested.",
        "Would you like to explore a specific category?",
        "Let me know if you'd like more details.",
        "I can break this down further if needed.",
        "There's more to explore here if you'd like.",
        "Would you like to see this from a different angle?"
    ]

    # Comparison prompts - Professional
    COMPARISON_PROMPTS = [
        "Would you like to compare with {period}?",
        "Want to see how {period} compares?",
        "I can show you {period} for comparison."
    ]

    # Acknowledgments for understood requests - Professional & Friendly
    ACKNOWLEDGMENTS = [
        "Got it! Let me check.",
        "On it!",
        "Sure, one moment.",
        "Good question. Let me look...",
        "Absolutely, checking now.",
        "Interesting question. Let me see...",
        "Sure thing, checking now..."
    ]

    # Tamil equivalents (for bilingual support) - Professional & Friendly
    TAMIL_GREETINGS = [
        "வணக்கம்! நான் தாரா - உங்க data assistant. என்ன help வேணும்?",
        "Hello! நான் தாரா. உங்க data questions-க்கு help பண்ண ready.",
        "Hi! Thara here - unga data explore panna help pannuren. Enna venum?",
        "வணக்கம்! Thara ready - sollunga enna paakanum.",
        "Hello! Naan Thara - unga data assistant. Enna help pannanum?",
        "Hi! Thara here - ready to help. Enna venum?"
    ]

    # Tamil positive openings - Professional & Positive
    TAMIL_POSITIVE_OPENINGS = [
        "Good news {name}!",
        "{name}, numbers nalla irukku:",
        "{name}, positive results:",
        "Nalla results {name}:",
        "{name}, idhu good ah irukku:",
        "Great results {name}:"
    ]

    # Tamil neutral openings - Professional & Clear
    TAMIL_NEUTRAL_OPENINGS = [
        "Seri {name}, idho results:",
        "{name}, idho data:",
        "{name}, check panniten - idho:",
        "{name}, data paarthen:",
        "{name}, idho parunga:",
        "{name}, results idho:"
    ]

    # Tamil concern openings - Professional & Supportive
    TAMIL_CONCERN_OPENINGS = [
        "{name}, oru vishayam sollanam:",
        "{name}, idha note pannunga:",
        "{name}, oru heads up:",
        "{name}, idha parunga:",
        "{name}, attention kudukanum:",
        "{name}, idha consider pannunga:"
    ]

    # Tamil follow-up suggestions - Helpful & Professional
    TAMIL_FOLLOW_UP_SUGGESTIONS = [
        "Innum detail ah paakanum?",
        "Vera time period compare pannalama?",
        "Trend paakkanum na sollunga.",
        "Vera category explore pannalama?",
        "Vera enna venum?",
        "Innum detail venum na sollunga.",
        "Vera questions irundha kelu."
    ]

    # Tamil acknowledgments - Professional & Friendly
    TAMIL_ACKNOWLEDGMENTS = [
        "Seri, check pannuren.",
        "Okay, ipo paakuren.",
        "Good question. Paakuren...",
        "Sure, one moment.",
        "Okay, checking now.",
        "Seri, paakuren..."
    ]

    # Conversational/Warm openings - Natural, human-like flow
    CONVERSATIONAL_OPENINGS = [
        "Ohh okay {name}, so...",
        "Hmm let me see... {name},",
        "Ah right, so {name}...",
        "Yeah so {name},",
        "Okay {name}, looking at this...",
        "So {name}, here's what I see...",
        "Alright {name}, checking...",
        "Hmm {name}, interesting..."
    ]

    # Tamil Conversational openings - Warm and natural
    TAMIL_CONVERSATIONAL_OPENINGS = [
        "Seri {name}, paakalam...",
        "Ah okay {name}...",
        "Hmm seri {name}...",
        "Okay {name}, idho parunga...",
        "Seri seri {name}...",
        "Hmm {name}, paakuren...",
        "Okay {name}, checking..."
    ]

    # Name confirmation responses - Warm and friendly
    NAME_CONFIRMATIONS = [
        "Got it {name}! So what would you like to explore?",
        "Ohh okay {name}! What can I help you with?",
        "Alright {name}! Ready when you are.",
        "Sure thing {name}! What do you want to know?",
        "{name} it is! What can I do for you?"
    ]

    # Tamil name confirmations
    TAMIL_NAME_CONFIRMATIONS = [
        "Seri {name}! Enna paakanum?",
        "Okay {name}! Enna help venum?",
        "Alright {name}! Sollunga enna venum.",
        "{name}, noted! Enna explore pannalam?"
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
        """Get introduction message for new user - professional and friendly"""
        if self.language == 'ta':
            return (
                "வணக்கம்! நான் தாரா - உங்க data assistant. "
                "உங்க name என்னன்னு சொல்லுங்க please?"
            )
        return (
            "Hi there! I'm Thara, your data assistant. "
            "What should I call you?"
        )

    def get_name_confirmation(self, name: str) -> str:
        """Confirm user's name - professional and friendly"""
        self.user_name = name
        if self.language == 'ta':
            return (
                f"Thanks {name}! "
                f"நான் உங்க data explore பண்ண help பண்றேன். "
                f"என்ன வேணும்னாலும் கேளுங்க!"
            )
        return (
            f"Great to meet you, {name}! "
            f"I'm here to help you explore your data and find the insights you need. "
            f"What would you like to know?"
        )

    def get_data_ready_message(self, table_count: int, months: List[str] = None) -> str:
        """
        Message when data is loaded and ready - professional and informative.
        """
        name = self.user_name

        if months and len(months) > 0:
            month_str = ", ".join(sorted(months))
            if self.language == 'ta':
                return (
                    f"{name}, {table_count} data tables ready ah irukku. "
                    f"Months: {month_str}. Enna paakanum?"
                )
            return (
                f"{name}, I've loaded {table_count} data tables "
                f"covering {month_str}. What would you like to explore?"
            )
        else:
            if self.language == 'ta':
                return (
                    f"{name}, {table_count} data tables ready. "
                    f"Enna paakanum?"
                )
            return (
                f"{name}, I have access to {table_count} data tables. "
                f"What would you like to know?"
            )

    def format_response(self, result: str, sentiment: str = 'neutral',
                       add_followup: bool = True, conversational: bool = False) -> str:
        """
        Format response with personality.

        Args:
            result: The actual data/answer content
            sentiment: 'positive', 'negative', 'concern', or 'neutral'
            add_followup: Whether to add a follow-up suggestion
            conversational: Force conversational/warm opening style
        """
        name = self.user_name
        self._response_count += 1
        self._last_sentiment = sentiment

        # 40% chance to use conversational opening for natural flow (when name is set)
        use_conversational = conversational or (name and random.random() < 0.4)

        # Select opening based on style, sentiment AND language
        if use_conversational:
            # Use warm, conversational openings
            if self.language == 'ta':
                opening = random.choice(self.TAMIL_CONVERSATIONAL_OPENINGS)
            else:
                opening = random.choice(self.CONVERSATIONAL_OPENINGS)
        elif self.language == 'ta':
            # Use Tamil/Tanglish openings
            if sentiment == 'positive':
                opening = random.choice(self.TAMIL_POSITIVE_OPENINGS)
            elif sentiment in ['negative', 'concern']:
                opening = random.choice(self.TAMIL_CONCERN_OPENINGS)
            else:
                opening = random.choice(self.TAMIL_NEUTRAL_OPENINGS)
        else:
            # Use English openings
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
            # Use Tamil follow-ups if language is Tamil
            if self.language == 'ta':
                suggestion = random.choice(self.TAMIL_FOLLOW_UP_SUGGESTIONS)
            else:
                suggestion = random.choice(self.FOLLOW_UP_SUGGESTIONS)

        return f"{response}\n\n{suggestion}"

    def get_acknowledgment(self) -> str:
        """Get a quick acknowledgment for processing"""
        if self.language == 'ta':
            return random.choice(self.TAMIL_ACKNOWLEDGMENTS)
        return random.choice(self.ACKNOWLEDGMENTS)

    def handle_error(self, error_type: str, details: str = None) -> str:
        """Generate professional, helpful error messages"""
        name = self.user_name
        name_part = f" {name}" if name else ""

        if error_type == 'no_data':
            responses_ta = [
                f"{name_part}, andha data kidaikala. Spelling check pannunga or vera filter try pannunga.",
                f"{name_part}, idhukku data illa. Vera dates or filter try pannunga.",
                f"{name_part}, nothing found. Different question try pannunga."
            ]
            responses_en = [
                f"{name_part}, I couldn't find any data for that. Try a different filter or check the spelling.",
                f"{name_part}, no data matches that criteria. Perhaps try a different date range?",
                f"{name_part}, that search came up empty. Could you rephrase or try different keywords?"
            ]
            return random.choice(responses_ta if self.language == 'ta' else responses_en)

        elif error_type == 'ambiguous':
            responses_ta = [
                f"{name_part}, pala options kidaichadhu. Which one-nu clarify pannunga please.",
                f"{name_part}, multiple matches irukku. Konjam specific ah solla mudiyuma?"
            ]
            responses_en = [
                f"{name_part}, I found multiple possibilities. Which one did you mean?",
                f"{name_part}, a few things match that. Can you be more specific?",
                f"{name_part}, there are multiple options. Could you help narrow it down?"
            ]
            return random.choice(responses_ta if self.language == 'ta' else responses_en)

        elif error_type == 'table_not_found':
            responses = [
                f"{name_part}, I can't find that table. Let me show you what's available.",
                f"{name_part}, that table isn't available. Would you like to see the available options?",
                f"{name_part}, no such table found. I can show you what we have."
            ]
            return random.choice(responses)

        elif error_type == 'column_not_found':
            responses = [
                f"{name_part}, that column or metric isn't available. Want to see what I can show you?",
                f"{name_part}, I don't have that specific data. Shall I show you what's available?",
                f"{name_part}, can't find that one. I can show you the available metrics."
            ]
            return random.choice(responses)

        elif error_type == 'connection':
            responses_ta = [
                f"{name_part}, data connection-la problem. Reconnect panni try pannunga.",
                f"{name_part}, data source reach panna mudiyala. Please check the connection."
            ]
            responses_en = [
                f"{name_part}, having trouble reaching the data. Please check the connection.",
                f"{name_part}, can't connect to the data source right now. Try reconnecting?",
                f"{name_part}, the data connection seems to be down. Could you check if it's working?"
            ]
            return random.choice(responses_ta if self.language == 'ta' else responses_en)

        elif error_type == 'general' and details:
            # Use provided details message for general errors
            if name:
                return f"{name}, {details}"
            return details

        else:
            # Tamil responses
            responses_ta = [
                f"{name_part}, oru problem irukku. Mendum try pannunga.",
                f"{name_part}, etho thappu nadhandhadhu. Innonru murai try pannunga.",
                f"{name_part}, oru issue irukku. Vera vidhamaa kelunga."
            ]
            # English responses
            responses_en = [
                f"{name_part}, something went wrong. Would you like to try again?",
                f"{name_part}, ran into an issue. Could you rephrase that?",
                f"{name_part}, that didn't work as expected. Let's try a different approach."
            ]
            return random.choice(responses_ta if self.language == 'ta' else responses_en)

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
            return f"Rs.{value/10000000:.2f} Cr"
        elif abs(value) >= 100000:  # 1 lakh
            return f"Rs.{value/100000:.2f} L"
        elif abs(value) >= 1000:
            return f"Rs.{value:,.0f}"
        else:
            return f"Rs.{value:,.2f}"

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
        """Get a professional goodbye message"""
        name = self.user_name
        if self.language == 'ta':
            return f"Bye {name}! Eppo venum na vaanga."
        return f"Goodbye, {name}! Feel free to come back anytime you need help."

    def get_help_message(self) -> str:
        """Get help/guidance message - professional and informative"""
        name = self.user_name
        name_str = f"{name}, " if name else ""
        return f"""
{name_str}here's what I can help you with:

**Sales & Revenue:**
- "What were total sales in November?"
- "Show me sales by category"
- "Compare October vs November"

**Specific Queries:**
- "Dhoti sales in Chennai?"
- "Top 5 products by quantity?"
- "Average order value?"

**Analysis:**
- "Show me the sales trend"
- "What's the profit margin?"
- "Break it down by location"

Feel free to ask in your own words - I'll understand.
"""
