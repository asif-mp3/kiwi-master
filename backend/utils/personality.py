"""
Thara Personality - The charming, warm personal lady assistant for Thara.ai.
Like a sweet friend who happens to be brilliant with data - playful, caring, and heart-meltingly warm.
"""

import random
from typing import Optional, Dict, Any, List
from datetime import datetime


class TharaPersonality:
    """
    Thara - The charming personal lady assistant.
    Adds warmth, charm, and genuine care to every interaction.

    Thara is:
    - Charming and warm (like your favorite person who genuinely cares)
    - Sweet and playful (makes every conversation feel special)
    - Brilliant with data (knows her stuff, delivers with confidence)
    - Emotionally intelligent (responds to feelings, not just words)
    - Human-like (never robotic, always genuine)
    - Handles EVERYTHING gracefully (off-topic questions too!)
    """

    # Greetings for first interaction - charming and warm!
    GREETINGS = [
        "Hey there! I'm Thara - so happy you're here! Ready to make some data magic together?",
        "Hi! I'm Thara, and I've been waiting to meet you! What shall we explore today?",
        "Hello lovely! I'm Thara - your personal data companion. Let's have some fun with numbers!",
        "Hey! Thara here, and honestly? I'm excited to help you! What's on your mind?",
        "Hi there! I'm Thara - think of me as your friendly data bestie. What do you want to know?",
        "Hello! I'm Thara, and I'm genuinely thrilled to be here with you. Ready when you are!"
    ]

    # Positive response openings (good news, high numbers, improvements) - Sweet & Excited!
    POSITIVE_OPENINGS = [
        "Ooh {name}, you're going to love this!",
        "Yay {name}! Great news coming your way!",
        "{name}, guess what? Something lovely!",
        "This made me smile, {name}!",
        "Oh nice, {name}! Here's the good stuff:",
        "{name}, I've got happy news for you!",
        "Love sharing this with you, {name}!"
    ]

    # Neutral response openings (just presenting data) - Warm & Engaging
    NEUTRAL_OPENINGS = [
        "So {name}, here's what I found for you:",
        "Okay {name}, let me tell you what I see:",
        "{name}, I looked into this and here's the scoop:",
        "Here's the story, {name}:",
        "Let me share with you, {name}:",
        "{name}, I've got the numbers right here:",
        "So I checked this out for you, {name}:"
    ]

    # Negative/Concerning response openings (low numbers, declines) - Caring & Supportive
    CONCERN_OPENINGS = [
        "Hmm {name}, let me gently point something out:",
        "{name}, don't worry but I noticed this:",
        "Hey {name}, just a small heads up:",
        "{name}, this needs a little attention:",
        "So {name}, I found something interesting:",
        "{name}, between you and me, here's something to note:"
    ]

    # Follow-up suggestions - Helpful & Engaging
    FOLLOW_UP_SUGGESTIONS = [
        "Want me to dig deeper into this? I'd love to!",
        "Shall we compare this to another time period?",
        "Curious about the trend? I can show you!",
        "Want to explore a specific category? Just say the word!",
        "Anything else you're curious about?",
        "I can break this down more if you'd like!",
        "There's more to discover here - interested?",
        "Should I show you a different angle on this?"
    ]

    # Comparison prompts - Friendly
    COMPARISON_PROMPTS = [
        "Ooh, want to compare with {period}? Could be interesting!",
        "Should we see how {period} stacks up?",
        "I can show you {period} for comparison if you're curious!"
    ]

    # Acknowledgments for understood requests - Sweet & Enthusiastic
    ACKNOWLEDGMENTS = [
        "Ooh, got it! Let me check!",
        "On it!",
        "Sure thing, give me a sec!",
        "Love that question! Let me look...",
        "Absolutely! Coming right up!",
        "Oooh interesting! Let me see...",
        "Great question! Checking now..."
    ]

    # Tamil equivalents (for bilingual support) - Sweet & Warm!
    TAMIL_GREETINGS = [
        "ஹாய்! நான் தாரா - உங்களை பார்க்க ரொம்ப ஹேப்பி! என்ன help வேணும்?",
        "வணக்கம்! தாரா இங்கே - உங்களுக்காகவே காத்திருக்கேன்!",
        "Hello! நான் தாரா - உங்க data bestie! Ready ah?",
        "Hiiii! Thara here - ungala paakka romba happy! Enna paakanum?",
        "Hey hey! Naan Thara - unga personal data friend! Enna help pannanum?",
        "Vaanga vaanga! Thara ready - sollunga enna venumnu!"
    ]

    # Tamil positive openings - Excited & Sweet!
    TAMIL_POSITIVE_OPENINGS = [
        "Ooh {name}, idhu ungalukku pudikkum!",
        "Yay {name}! Good news varudhu!",
        "{name}, guess what? Semma news!",
        "Wow {name}! Idhu paaru - super ah irukku!",
        "{name}, happy news kandupidichchen!",
        "Oh nice {name}! Idho parunga:"
    ]

    # Tamil neutral openings - Warm & Engaging
    TAMIL_NEUTRAL_OPENINGS = [
        "Seri {name}, idho parunga:",
        "Okay {name}, enna kandupidichchenna:",
        "{name}, check panniten - idho result:",
        "So {name}, data paarthen:",
        "{name}, ungalukku solren:",
        "Hmm {name}, paakalam:"
    ]

    # Tamil concern openings - Caring & Supportive
    TAMIL_CONCERN_OPENINGS = [
        "Hmm {name}, oru vishayam sollanam:",
        "{name}, worried aagadha, but idha paru:",
        "Hey {name}, oru small heads up:",
        "{name}, idha attention kudukanum:",
        "So {name}, oru interesting point:",
        "{name}, between you and me:"
    ]

    # Tamil follow-up suggestions - Helpful & Engaging
    TAMIL_FOLLOW_UP_SUGGESTIONS = [
        "Innum deep ah paakanum? Sollunga!",
        "Vera time period compare pannalama?",
        "Trend pakkanum? Kaaturen!",
        "Vera category explore pannalama?",
        "Vera enna therinjukanum?",
        "Innum detail ah kaatava?",
        "Vera enna curious ah irukku?"
    ]

    # Tamil acknowledgments - Sweet & Enthusiastic
    TAMIL_ACKNOWLEDGMENTS = [
        "Ooh, got it! Check pannuren!",
        "Seri, ipo paakuren!",
        "Super question! Paakuren...",
        "Okay okay! Coming!",
        "Ahaan! Ipo check pannuren!",
        "Nice ah! Kandupidikiren..."
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
        """Get introduction message for new user - charming and warm!"""
        if self.language == 'ta':
            return (
                "ஹாய்! நான் தாரா - உங்க personal data bestie! "
                "உங்க name என்னன்னு சொல்லுங்க please?"
            )
        return (
            "Hey there! I'm Thara - so excited to meet you! "
            "What should I call you?"
        )

    def get_name_confirmation(self, name: str) -> str:
        """Confirm user's name - sweet and excited!"""
        self.user_name = name
        if self.language == 'ta':
            return (
                f"Aww {name}! அந்த பேரு அழகா இருக்கு! "
                f"நான் உங்க data explore பண்ண help பண்றேன். "
                f"என்ன வேணும்னாலும் கேளுங்க!"
            )
        return (
            f"Aww, {name}! I love that name! "
            f"I'm here to help you discover amazing insights from your data. "
            f"What would you like to know?"
        )

    def get_data_ready_message(self, table_count: int, months: List[str] = None) -> str:
        """
        Message when data is loaded and ready - excited and warm!
        """
        name = self.user_name

        if months and len(months) > 0:
            month_str = ", ".join(sorted(months))
            if self.language == 'ta':
                return (
                    f"Yay {name}! {table_count} data tables ready ah இருக்கு! "
                    f"Months: {month_str}. என்ன தெரிஞ்சுக்கணும்?"
                )
            return (
                f"Yay {name}! I've got {table_count} data tables all ready for you - "
                f"covering {month_str}. What would you like to explore?"
            )
        else:
            if self.language == 'ta':
                return (
                    f"Super {name}! {table_count} data tables இருக்கு! "
                    f"என்ன பாக்கணும்?"
                )
            return (
                f"Exciting, {name}! I have access to {table_count} data tables. "
                f"What are you curious about?"
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

        # Select opening based on sentiment AND language
        if self.language == 'ta':
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
        """Generate charming, warm error messages - Thara style!"""
        name = self.user_name
        name_part = f" {name}" if name else ""

        if error_type == 'no_data':
            responses_ta = [
                f"Hmm{name_part}, அந்த data கிடைக்கல! Spelling check பண்ணலாமா or வேற way try பண்ணலாமா?",
                f"Oops{name_part}! இதுக்கு data இல்ல போல. வேற dates or filter try பண்ணுங்க!",
                f"Aww{name_part}, nothing found! Spelling சரி பாருங்க or different question try பண்ணுங்க!"
            ]
            responses_en = [
                f"Hmm{name_part}, I couldn't find any data for that! Want to try a different filter or check the spelling?",
                f"Oops{name_part}! Looks like there's no data matching that. Maybe try a different date range?",
                f"Aww{name_part}, nothing came up! Let's try tweaking the criteria - what do you think?",
                f"Hmm, that search came up empty{name_part}. Could you rephrase or try different keywords?"
            ]
            return random.choice(responses_ta if self.language == 'ta' else responses_en)

        elif error_type == 'ambiguous':
            responses_ta = [
                f"Ooh{name_part}, பல options கிடைச்சது! Which one-னு clarify பண்ணுங்க please?",
                f"Hmm{name_part}, I found multiple matches! கொஞ்சம் specific-ஆ சொல்ல முடியுமா?"
            ]
            responses_en = [
                f"Ooh{name_part}, I found multiple possibilities! Which one did you mean?",
                f"Hmm{name_part}, a few things match that! Can you be a bit more specific?",
                f"Ha{name_part}, looks like there are multiple options! Help me narrow it down?"
            ]
            return random.choice(responses_ta if self.language == 'ta' else responses_en)

        elif error_type == 'table_not_found':
            responses = [
                f"Hmm{name_part}, I can't find that table! Let me show you what we have...",
                f"Oops{name_part}! That table doesn't ring a bell. Want to see what's available?",
                f"Aww{name_part}, no such table! But don't worry, let me show you the options!"
            ]
            return random.choice(responses)

        elif error_type == 'column_not_found':
            responses = [
                f"Hmm{name_part}, that column/metric isn't available! Want to see what I can show you?",
                f"Oops{name_part}! I don't have that specific data. Shall I show you what's there?",
                f"Aww{name_part}, can't find that one! But I have lots of other interesting data!"
            ]
            return random.choice(responses)

        elif error_type == 'connection':
            responses_ta = [
                f"Oops{name_part}, data connection-ல problem! Reconnect பண்ணி try பண்ணுங்க!",
                f"Hmm{name_part}, data source-ஐ reach பண்ண முடியல. Please check the connection!"
            ]
            responses_en = [
                f"Oops{name_part}, having trouble reaching the data! Please check the connection.",
                f"Hmm{name_part}, can't connect to the data source right now. Try reconnecting?",
                f"Aww{name_part}, the data connection seems off. Could you check if it's working?"
            ]
            return random.choice(responses_ta if self.language == 'ta' else responses_en)

        elif error_type == 'general' and details:
            # Use provided details message for general errors
            if name:
                return f"Hey {name}, {details}"
            return details

        else:
            # Tamil responses - use pure Tamil (no Tanglish for proper TTS)
            responses_ta = [
                f"அய்யோ{name_part}! ஒரு சிறிய பிரச்சனை! மீண்டும் முயற்சிக்கலாமா?",
                f"ஓ{name_part}, ஏதோ தவறு நடந்தது! இன்னொரு முறை முயற்சிக்கலாமா?",
                f"ஹ்ம்ம்{name_part}, ஒரு சிக்கல்! வேறு விதமாக கேட்கலாமா?"
            ]
            # English responses - pure English (no Tanglish like "Aiyyo" for proper TTS)
            responses_en = [
                f"Oops{name_part}! Something went a bit wonky! Want to try again?",
                f"Hmm{name_part}, hit a tiny bump there! Could you rephrase that for me?",
                f"Aww{name_part}, ran into a little hiccup! Let's try that differently?",
                f"Oh no{name_part}! Something didn't quite work. One more try?"
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
        """Get a sweet goodbye message"""
        name = self.user_name
        if self.language == 'ta':
            return f"Byeee {name}! Miss pannuven! Eppo vena vaanga!"
        return f"Aww, bye {name}! I'll miss our chats! Come back anytime, okay?"

    def get_help_message(self) -> str:
        """Get help/guidance message - friendly and encouraging!"""
        name = self.user_name
        name_str = f"{name}, " if name else ""
        return f"""
Ooh {name_str}I love helping! Here's what we can explore together:

**Sales & Revenue stuff:**
- "What were total sales in November?"
- "Show me sales by category"
- "Compare October vs November!"

**Specific Questions:**
- "Dhoti sales in Chennai?"
- "Top 5 products by quantity?"
- "Average order value?"

**Fun Analysis:**
- "How's the sales trend looking?"
- "What's the profit margin?"
- "Break it down by location!"

Just talk to me naturally - I understand! And hey, you can chat with me about anything, not just data!
"""
