"""
Centralized conversation templates for Thara AI.
Consolidates all conversation patterns, openings, and response templates.
"""

# =============================================================================
# CONVERSATION STARTERS - Organized by EMOTION/SENTIMENT
# =============================================================================

# English starters by emotion
CONVERSATION_STARTERS_ENGLISH = {
    "casual": [
        # Normal, everyday questions
        "Hmm {name}, let me check that...",
        "Okay {name}, let me see...",
        "Alright {name}, give me a moment...",
        "Let's see here {name}...",
        "Let me check the data {name}...",
    ],
    "urgent": [
        # Quick, time-sensitive questions with urgency indicators
        "Sure thing {name}, let me check...",
        "Got it {name}, checking now...",
        "On it {name}, one sec...",
        "Yep {name}, let me look...",
        "Right away {name}, checking...",
    ],
    "thoughtful": [
        # Complex, analytical, comparison questions
        "Hmm {name}, let me think about this...",
        "Okay {name}, looking into this...",
        "Let me dig into that {name}...",
        "Alright {name}, checking the details...",
        "Interesting question {name}, analyzing...",
    ],
    "curious": [
        # Exploratory, "how", "why", "what if" questions
        "Oh {name}, let me look that up...",
        "Ooh interesting {name}, checking now...",
        "Ah {name}, let me pull that data...",
        "Oh okay {name}, one sec...",
        "Hmm, interesting {name}, let me explore...",
    ]
}

# Tamil starters by emotion
CONVERSATION_STARTERS_TAMIL = {
    "casual": [
        # Normal, everyday questions
        "ம்ம் {name}, பார்க்கலாம்...",
        "சரி {name}, பார்க்குறேன்...",
        "ஓகே {name}, ஒரு நிமிஷம்...",
        "ஆஹா {name}, செக் பண்ணலாம்...",
        "சரி சரி {name}, செக்கிங்...",
    ],
    "urgent": [
        # Quick, time-sensitive questions
        "கண்டிப்பா {name}, செக் பண்ணுறேன்...",
        "ஷூர் {name}, பார்க்குறேன்...",
        "ஓகே டண் {name}, ஒரு செக்...",
        "ஆமா {name}, பார்க்கலாம்...",
        "ஆஹா {name}, இப்போவே எடுத்துடலாம்...",
    ],
    "thoughtful": [
        # Complex, analytical questions
        "ம்ம் {name}, நல்லா செக் பண்ணுறேன்...",
        "சரி {name}, டீடெயில்ஸ் பார்க்குறேன்...",
        "ஓகே {name}, கொஞ்சம் வெயிட் பண்ணுங்க...",
        "ஆஹா {name}, ப்ராப்பர்லி செக் பண்ணலாம்...",
        "ம்ம் {name}, டேட்டா பார்த்திட்டு இருக்கேன்...",
    ],
    "curious": [
        # Exploratory, interested questions
        "ஓ சரி {name}, இதோ பார்க்குறேன்...",
        "ஓஹோ அப்படியா {name}, இருங்க பார்த்துட்டு சொல்றேன்...",
        "ஆஹா {name}, இதோ செக் பண்ணுறேன்...",
        "ஓஹோ {name}, இன்டெரஸ்டிங் ஆ இருக்கு...",
        "ஓஹோ {name}, நல்ல கேள்வி - பார்க்குறேன்...",
    ]
}

# =============================================================================
# RESPONSE OPENINGS BY SENTIMENT
# =============================================================================

# Positive response openings (good news, high numbers, improvements)
POSITIVE_OPENINGS_ENGLISH = [
    "Good news, {name}!",
    "Great results here, {name}:",
    "{name}, the numbers look strong:",
    "Here's some positive news, {name}:",
    "{name}, this is looking good:",
    "Excellent results, {name}:",
    "{name}, here's what I found - and it's good:"
]

POSITIVE_OPENINGS_TAMIL = [
    "குட் நியூஸ் {name}!",
    "{name}, நம்பர்ஸ் நல்லா இருக்கு:",
    "{name}, பாசிடிவ் ரிசல்ட்ஸ்:",
    "நல்ல ரிசல்ட்ஸ் {name}:",
    "{name}, இது குட் ஆ இருக்கு:",
    "க்ரேட் ரிசல்ட்ஸ் {name}:"
]

# Neutral response openings (just presenting data)
NEUTRAL_OPENINGS_ENGLISH = [
    "Here's what I found, {name}:",
    "{name}, here are the results:",
    "Looking at the data, {name}:",
    "Here's the breakdown, {name}:",
    "{name}, I've pulled the numbers:",
    "Based on the data, {name}:",
    "{name}, here's what the data shows:"
]

NEUTRAL_OPENINGS_TAMIL = [
    "சரி {name}, இதோ ரிசல்ட்ஸ்:",
    "{name}, இதோ டேட்டா:",
    "{name}, செக் பண்ணிட்டேன் - இதோ:",
    "{name}, டேட்டா பார்த்தேன்:",
    "{name}, இதோ பாருங்க:",
    "{name}, ரிசல்ட்ஸ் இதோ:"
]

# Concern/Negative response openings (low numbers, declines)
CONCERN_OPENINGS_ENGLISH = [
    "{name}, here's something worth noting:",
    "{name}, I noticed something that may need attention:",
    "Just a heads up, {name}:",
    "{name}, here's an area to watch:",
    "{name}, the data shows something to consider:",
    "Worth mentioning, {name}:"
]

CONCERN_OPENINGS_TAMIL = [
    "{name}, ஒரு விஷயம் சொல்லணும்:",
    "{name}, இத நோட் பண்ணுங்க:",
    "{name}, ஒரு ஹெட்ஸ் அப்:",
    "{name}, இத பாருங்க:",
    "{name}, அட்டென்ஷன் குடுக்கணும்:",
    "{name}, இத கன்சிடர் பண்ணுங்க:"
]

# =============================================================================
# GREETINGS
# =============================================================================

GREETINGS_ENGLISH = [
    "Hi there! I'm Thara, your data assistant. How can I help you today?",
    "Hello! I'm Thara. I'm here to help you explore your data. What would you like to know?",
    "Hi! I'm Thara - ready to help you find the insights you need. What can I do for you?",
    "Hello! Thara here. Let me know what data you'd like to explore.",
    "Hi there! I'm Thara, happy to assist with your data questions. What's on your mind?",
    "Hello! I'm Thara. Ready to help you get the most from your data."
]

GREETINGS_TAMIL = [
    "வணக்கம்! நான் தாரா - உங்க டேட்டா அசிஸ்டன்ட். என்ன ஹெல்ப் வேணும்?",
    "ஹலோ! நான் தாரா. உங்க டேட்டா கேள்விகளுக்கு ஹெல்ப் பண்ண ரெடி.",
    "ஹாய்! தாரா இதோ - உங்க டேட்டா எக்ஸ்ப்ளோர் பண்ண ஹெல்ப் பண்றேன். என்ன வேணும்?",
    "வணக்கம்! தாரா ரெடி - சொல்லுங்க என்ன பாக்கணும்.",
    "ஹலோ! நான் தாரா - உங்க டேட்டா அசிஸ்டன்ட். என்ன ஹெல்ப் பண்ணணும்?",
    "ஹாய்! தாரா இதோ - ரெடி டு ஹெல்ப். என்ன வேணும்?"
]

# =============================================================================
# FOLLOW-UP SUGGESTIONS
# =============================================================================

FOLLOWUP_SUGGESTIONS_ENGLISH = [
    "Would you like me to dig deeper into this?",
    "Want me to compare this with another time period?",
    "I can show you the trend if you're interested.",
    "Would you like to explore a specific category?",
    "Let me know if you'd like more details.",
    "I can break this down further if needed.",
    "There's more to explore here if you'd like.",
    "Would you like to see this from a different angle?"
]

FOLLOWUP_SUGGESTIONS_TAMIL = [
    "இன்னும் டீடெயில் ஆ பாக்கணுமா?",
    "வேற டைம் பீரியட் காம்பேர் பண்ணலாமா?",
    "ட்ரெண்ட் பாக்கணும் னா சொல்லுங்க.",
    "வேற கேடகரி எக்ஸ்ப்ளோர் பண்ணலாமா?",
    "வேற என்ன வேணும்?",
    "இன்னும் டீடெயில் வேணும் னா சொல்லுங்க.",
    "வேற கேள்விகள் இருந்தா கேளு."
]

# =============================================================================
# ACKNOWLEDGMENTS
# =============================================================================

ACKNOWLEDGMENTS_ENGLISH = [
    "Got it! Let me check.",
    "On it!",
    "Sure, one moment.",
    "Good question. Let me look...",
    "Absolutely, checking now.",
    "Interesting question. Let me see...",
    "Sure thing, checking now..."
]

ACKNOWLEDGMENTS_TAMIL = [
    "சரி, செக் பண்ணுறேன்.",
    "ஓகே, இப்போ பார்க்குறேன்.",
    "குட் கேஸ்சன். பார்க்குறேன்...",
    "ஷூர், ஒரு மொமென்ட்.",
    "ஓகே, செக்கிங் நௌ.",
    "சரி, பார்க்குறேன்..."
]

# =============================================================================
# COMPARISON PROMPTS
# =============================================================================

COMPARISON_PROMPTS_ENGLISH = [
    "Would you like to compare with {period}?",
    "Want to see how {period} compares?",
    "I can show you {period} for comparison."
]

COMPARISON_PROMPTS_TAMIL = [
    "{period}-ஓட காம்பேர் பண்ணலாமா?",
    "{period} பாக்கணும் னா சொல்லுங்க.",
    "{period} காம்பரிசன் வேணுமா?"
]

# =============================================================================
# ERROR RESPONSE TEMPLATES
# =============================================================================

ERROR_TEMPLATES = {
    "no_data": {
        "english": [
            "{name}, I couldn't find any data for that. Try a different filter or check the spelling.",
            "{name}, no data matches that criteria. Perhaps try a different date range?",
            "{name}, that search came up empty. Could you rephrase or try different keywords?"
        ],
        "tamil": [
            "{name}, அந்த டேட்டா கிடைக்கல. ஸ்பெல்லிங் செக் பண்ணுங்க ஆர் வேற ஃபில்டர் ட்ரை பண்ணுங்க.",
            "{name}, இதுக்கு டேட்டா இல்ல. வேற டேட்ஸ் ஆர் ஃபில்டர் ட்ரை பண்ணுங்க.",
            "{name}, நத்திங் ஃபவுண்ட். டிஃபெரன்ட் கேஸ்சன் ட்ரை பண்ணுங்க."
        ]
    },
    "ambiguous": {
        "english": [
            "{name}, I need a bit more clarity. Could you be more specific?",
            "{name}, there are a few ways to interpret that. Could you clarify?",
            "{name}, I want to make sure I understand correctly. Can you rephrase that?"
        ],
        "tamil": [
            "{name}, கொஞ்சம் க்ளியர் ஆ சொல்லுங்க. புரியல.",
            "{name}, இத வேற விதமா அர்த்தம் பண்ணலாம். கொஞ்சம் க்ளாரிஃபை பண்ணுங்க.",
            "{name}, சரி ஆ புரிஞ்சுக்கணும். ஒரு வாட்டி ரிபீட் பண்ணுங்க?"
        ]
    },
    "connection_error": {
        "english": [
            "{name}, I'm having trouble connecting to the data. Let me try again.",
            "{name}, connection issue. Give me a moment to reconnect.",
            "{name}, looks like a temporary connection problem. One sec..."
        ],
        "tamil": [
            "{name}, டேட்டா கனெக்ட் பண்ண முடியல. மறுபடியும் ட்ரை பண்றேன்.",
            "{name}, கனெக்ஷன் ப்ராப்ளம். வெயிட் பண்ணுங்க.",
            "{name}, டெம்பரரி இஷ்யூ. ஒரு நிமிஷம்..."
        ]
    }
}

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def detect_question_emotion(question: str) -> str:
    """
    Detect the emotion/sentiment of a user's question to choose appropriate starter.

    Returns one of: "casual", "urgent", "thoughtful", "curious"
    """
    question_lower = question.lower()

    # URGENT indicators - quick, immediate, now, ASAP, immediately
    urgent_keywords = [
        "quick", "quickly", "asap", "urgent", "immediately", "right now", "now",
        "fast", "hurry", "சீக்கிரம்", "உடனே", "இப்போவே", "அவசரம்"
    ]

    # CURIOUS indicators - exploratory, "what if", "how about", "can you show"
    # Check BEFORE thoughtful because some overlap
    curious_keywords = [
        "what if", "how about", "can you show", "could you show", "would you",
        "explore", "look at", "check out", "interesting", "curious",
        "என்ன ஆகும்", "எப்படி", "காட்டு", "பார்க்கலாமா", "இன்டெரஸ்டிங்"
    ]

    # THOUGHTFUL indicators - comparison, analysis, complex
    thoughtful_keywords = [
        "compare", "comparison", "vs", "versus", "better", "worse", "why", "reason",
        "analyze", "analysis", "trend", "pattern", "difference", "between",
        "காம்பேர்", "எந்த", "ஏன்", "என்ன காரணம்", "டிஃபரன்ஸ்", "வித்தியாசம்"
    ]

    # Check for emotion indicators (order matters!)
    for keyword in urgent_keywords:
        if keyword in question_lower:
            return "urgent"

    for keyword in curious_keywords:
        if keyword in question_lower:
            return "curious"

    for keyword in thoughtful_keywords:
        if keyword in question_lower:
            return "thoughtful"

    # Default to casual for normal questions
    return "casual"


def get_conversation_starter(language: str = "english", emotion: str = "casual") -> list:
    """
    Get conversation starters for specified language and emotion.

    Args:
        language: "english" or "tamil"
        emotion: "casual", "urgent", "thoughtful", or "curious"

    Returns:
        List of starter templates matching the emotion
    """
    lang_key = "tamil" if language.lower() in ["tamil", "ta"] else "english"
    starters_dict = CONVERSATION_STARTERS_TAMIL if lang_key == "tamil" else CONVERSATION_STARTERS_ENGLISH

    # Get starters for this emotion, fallback to casual if emotion not found
    return starters_dict.get(emotion, starters_dict["casual"])


def get_response_opening(sentiment: str = "neutral", language: str = "english") -> list:
    """Get response openings based on sentiment and language."""
    lang_key = "tamil" if language.lower() in ["tamil", "ta"] else "english"

    if sentiment == "positive":
        return POSITIVE_OPENINGS_TAMIL if lang_key == "tamil" else POSITIVE_OPENINGS_ENGLISH
    elif sentiment in ["negative", "concern"]:
        return CONCERN_OPENINGS_TAMIL if lang_key == "tamil" else CONCERN_OPENINGS_ENGLISH
    else:  # neutral
        return NEUTRAL_OPENINGS_TAMIL if lang_key == "tamil" else NEUTRAL_OPENINGS_ENGLISH


def get_error_template(error_type: str, language: str = "english") -> list:
    """Get error message templates for specified error type and language."""
    lang_key = "tamil" if language.lower() in ["tamil", "ta"] else "english"
    return ERROR_TEMPLATES.get(error_type, ERROR_TEMPLATES["no_data"])[lang_key]
