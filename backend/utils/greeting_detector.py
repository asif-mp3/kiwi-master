"""
Greeting & Conversational Intent Detector

Detects:
1. Casual greetings (hi, hello, vanakkam)
2. Capability questions (what can you do?)
3. Mic checks (can you hear me?)
4. Help requests (help me, I need help)

Returns dynamic responses using LLM for natural conversation.
"""

import time
import random
import re
from datetime import datetime
from typing import Tuple, Optional, Dict

# Greeting patterns with categories (case-insensitive)
GREETING_CATEGORIES = {
    'casual': [
        r'\b(hi|hello|hey|hola|yo)\b',
        r'^(hi|hello|hey)$',
        r'^(hi|hello),?\s+thara$',
    ],
    'phatic': [  # Mic checks and connectivity capability checks
        r'\b(can|could)\s+you\s+(hear|listen)\s+(to\s+)?me\b',
        r'\b(are\s+you)\s+(there|listening|online|ready)\b',
        r'\b(testing)\s+(1|one)\s*,?\s*(2|two)\s*,?\s*(3|three)\b',
        r'\b(mic|microphone)\s+(check|test)\b',
        # Tamil Mic Checks
        r'கேக்குதா',  # Kekudha (Can you hear?)
        r'கேட்குதா',  # Ketkudha (Can you hear?)
        r'பேசுறது\s+கேக்குதா',  # Pesuradhu kekudha
        r'பேசுறது\s+கேட்குதா',  # Pesuradhu ketkudha
        r'கேட்கிறதா',  # Ketkiradha (Formal: Is it audible?)
    ],
    'capability': [  # Questions about what Thara can do
        r'\b(what)\s+(can|could)\s+you\s+(do|help)\b',
        r'\b(what)\s+(are)\s+(your|you)\s+(capabilities|features|abilities)\b',
        r'\b(how)\s+(can|could)\s+you\s+help\b',
        r'\b(what)\s+(do)\s+you\s+(do|offer)\b',
        r'\b(tell)\s+(me)\s+(about)\s+(yourself|you)\b',
        r'\b(who)\s+(are)\s+you\b',
        r'\b(introduce)\s+(yourself)\b',
        # Tamil capability questions
        r'என்னெல்லாம்\s+பண்ண\s+முடியும்',  # What all can you do?
        r'என்ன\s+பண்ண\s+முடியும்',  # What can you do?
        r'என்ன\s+செய்ய\s+முடியும்',  # What can you do? (formal)
        r'உங்களால்\s+என்ன\s+செய்ய\s+முடியும்',  # What can you do?
        r'எப்படி\s+உதவ\s+முடியும்',  # How can you help?
        r'நீங்கள்\s+யார்',  # Who are you?
        r'உன்னைப்\s+பற்றி\s+சொல்லு',  # Tell me about yourself
    ],
    'formal': [
        r'\b(good\s+(morning|afternoon|evening|day))\b',
        r'\b(greetings)\b',
        r'\b(welcome)\b',
    ],
    'cultural': [
        r'\b(namaste|namaskar|नमस्ते)\b',  # Hindi
        r'\b(vanakkam|வணக்கம்|vanakam)\b',  # Tamil
        r'\b(salaam|salam|सलाम|assalamu\s+alaikum)\b',  # Arabic/Urdu
        r'\b(bonjour|bon\s+jour)\b',  # French
        r'\b(konnichiwa|こんにちは)\b',  # Japanese
        r'\b(ni\s+hao|你好)\b',  # Chinese
    ],
    'casual_question': [
        r'\b(what\'?s\s+up|whats\s+up|wassup|sup)\b',
        r'\b(how\s+(are\s+you|r\s+u|are\s+ya))\b',
        r'\b(how\'?s\s+it\s+going)\b',
    ],
    'time_based': [
        r'\b(good\s+morning)\b',
        r'\b(good\s+afternoon)\b',
        r'\b(good\s+evening)\b',
        r'\b(good\s+night)\b',
    ],
    'help': [  # Help requests
        r'\b(help)\s*(me)?\b',
        r'\b(i)\s+(need|want)\s+help\b',
        r'\b(assist)\s+(me)\b',
        # Tamil help
        r'உதவி\s+வேண்டும்',  # I need help
        r'உதவுங்கள்',  # Help me
    ],
    'schema_inquiry': [  # Questions about data structure/schema
        # Basic "what is sheet X" patterns
        r'\b(what)\s+(is|are)\s+(sheet|table|the)\s+',
        r'\b(what)\s+(is|are)\s+(?:in\s+)?(?:the\s+)?(sheet|table)',  # "what is in sheet 1"
        r'\b(what)\s+(is|are)\s+(present|available|there)\s+(in\s+)?(the\s+)?(sheet|table)',  # "what is present in sheet"
        r'\b(what)\s+(does)\s+(sheet|table)\s*\w*\s*(contain|have)\b',  # "what does sheet 1 contain"
        r'\b(what)\s+(can\s+i\s+find|is\s+there)\s+(in\s+)?(the\s+)?(sheet|table)',  # "what can I find in sheet"
        # "What's in" patterns - including data/dataset
        r'\b(what\'?s|what\s+is)\s+(in|inside)\s+(the\s+)?(sheet|table|data|dataset)',  # "what's in the data"
        r'\b(contents?|structure)\s+(of)\s+(the\s+)?(sheet|table)',  # "contents of sheet 1"
        # Describe/explain patterns
        r'\b(describe|explain)\s+(the\s+)?(sheet|table|data)\b',
        r'\b(describe|explain)\s+(the\s+)?(\w+\s+)?(table|sheet)\b',  # "describe the sales table"
        # Column/field patterns
        r'\b(columns?|fields?)\s+(in|of)\s+',
        r'\b(what)\s+(columns?|fields?)\s+(exist|are\s+(?:there|available|in))',  # "what columns exist"
        r'\b(what)\s+(columns?|fields?|data)\s+(does|do|is|are)',
        # Tell/show about patterns - including "my tables"
        r'\b(tell|show)\s+(me\s+)?(about)\s+(?:the\s+)?(?:my\s+)?(sheets?|tables?|data)',  # "tell me about my tables"
        r'\b(tell|show)\s+(me\s+)?(about)\s+(the\s+)?(\w+\s+)?(table|sheet)\b',  # "tell me about the inventory table"
        # Direct "show me sheet X" pattern
        r'\b(show|tell)\s+(me\s+)?(the\s+)?(sheet|table)\s+(\w+|\d+)',  # "show me sheet one"
        # List/show all patterns
        r'\b(what)\s+(tables?|sheets?)\s+(do\s+i\s+have|are\s+available)',
        r'\b(list)\s+(all\s+)?(tables?|sheets?|columns?)',
        r'\b(show)\s+(all\s+)?(columns?|fields?)',  # "show all columns"
        r'\b(describe|show(\s+me)?)\s+.+\s+(in\s+detail)',  # "describe X in detail" or "show me X in detail"
        r'\b(what)\s+(data|info|information)\s+(do\s+i\s+have|is\s+available)',  # "what data do I have"
        # "How many" - only for schema objects (NOT metrics)
        r'\b(how\s+many)\s+(sheets?|tables?|columns?)',  # "how many sheets"
        # Sheet reference catch-all
        r'sheet\s+\w+',  # Catch-all for "sheet X" where X is any word (one, two, four, etc.)
        # Tamil schema inquiry patterns
        r'என்ன\s+(தரவு|டேட்டா|அட்டவணை)',  # What data/table
        r'எந்த\s+(columns|fields|தரவு)',  # Which columns/fields/data
        r'(sheet|table)\s+பற்றி',  # About sheet/table
        r'ஷீட்.*என்னெல்லாம்',  # sheet...what all (in any order)
        r'என்னெல்லாம்.*ஷீட்',  # what all...sheet
        r'ஷீட்.*இருக்கின்றது',  # sheet...is there
        r'ஷீட்.*இருக்கிறது',   # sheet...is there
        r'ஷீட்.*உள்ளது',       # sheet...exists
        r'எத்தனை\s*(ஷீட்|sheet|table|அட்டவணை)',  # how many sheets/tables
        r'(ஷீட்|sheet|table|அட்டவணை)\s*எத்தனை',  # sheets/tables how many
        r'உன்னிடம்.*ஷீட்',    # you have...sheet
        r'உன்னிடம்.*அட்டவணை',  # you have...table
        r'என்ன\s+அட்டவணை',    # what table
        r'அட்டவணை\s+என்ன',    # table what
    ]
}

# Dynamic response templates by category
# Note: These are fallback templates. LLM-generated responses are preferred.
RESPONSE_TEMPLATES = {
    'casual': [
        "Hi! I'm Thara, your analytics assistant. What would you like to know about your data?",
        "Hello! I'm Thara. Ready to help you analyze your sheets. What can I do for you?",
        "Hey! Thara here. How can I assist you with your data today?",
    ],
    'phatic': [  # Responses to mic checks
        "Yes, I can hear you clearly! I'm ready to help with your data analysis. What's on your mind?",
        "Loud and clear! I'm listening. Ask me anything about your spreadsheet.",
        "I'm here and I can hear you perfectly. How can I assist you today?",
    ],
    'tamil_phatic': [  # Tamil responses to "Can you hear me?"
        "ஆம், நீங்கள் பேசுவது எனக்கு நன்றாகக் கேட்கிறது. நான் தாரா, உங்கள் டேட்டா அசிஸ்டன்ட். சொல்லுங்கள்.",
        "கேட்கிறது! நான் உங்கள் தாரா. உங்கள் அட்டவணை பற்றி என்ன தெரிந்துகொள்ள வேண்டும்?",
        "தெளிவாகக் கேட்கிறது. நான் உதவி செய்யத் தயார். என்ன கேள்வி இருக்கிறது?"
    ],
    'capability': [  # Responses to "what can you do?"
        "I'm Thara, your AI data analyst! I can help you explore your spreadsheet data - just ask me questions like 'What were the total sales last month?' or 'Show me the top products by revenue'. I understand both English and Tamil!",
        "Great question! I can analyze your Google Sheets data, answer questions about sales, revenue, products, and trends. Just ask naturally - like talking to a colleague who knows your data inside out.",
    ],
    'tamil_capability': [  # Tamil responses to capability questions
        "நான் தாரா, உங்கள் AI டேட்டா அனலிஸ்ட்! உங்கள் Google Sheets தரவை ஆய்வு செய்ய உதவுவேன். 'கடந்த மாத மொத்த விற்பனை என்ன?' அல்லது 'டாப் ப்ராடக்ட்ஸ் காட்டு' என்று கேளுங்கள். தமிழிலும் ஆங்கிலத்திலும் புரியும்!",
        "நல்ல கேள்வி! நான் உங்கள் ஸ்ப்ரெட்ஷீட் டேட்டாவை அலசுவேன் - sales, revenue, products பற்றி கேளுங்கள். சாதாரணமாக பேசுவது போல் கேளுங்கள், புரிந்துக்கொள்வேன்!",
    ],
    'help': [  # Responses to help requests
        "I'm here to help! You can ask me about your spreadsheet data - things like sales figures, product performance, trends over time. What would you like to know?",
        "Happy to help! Try asking questions like 'What were the sales in November?' or 'Show me top 5 products'. I'll analyze your data and give you insights.",
    ],
    'tamil_help': [  # Tamil help responses
        "உதவ தயாராக இருக்கிறேன்! உங்கள் டேட்டா பற்றி கேளுங்கள் - sales, products, trends என்னவேணும்னாலும். என்ன தெரிஞ்சுக்கணும்?",
        "சொல்லுங்கள்! 'நவம்பர் sales என்ன?' அல்லது 'டாப் 5 products காட்டு' மாதிரி கேளுங்கள். டேட்டாவை அலசி பதில் சொல்றேன்.",
    ],
    'formal': [
        "Good day! I'm Thara, your analytics assistant. How may I help you with your spreadsheet today?",
        "Greetings! I'm Thara. I'm here to help you analyze your data. What would you like to explore?",
    ],
    'welcome': [
        "Thank you! I'm ready to help you analyze your data. Where should we start?",
        "Glad to be here! How can I assist you with your spreadsheet today?",
    ],
    'namaste': [
        "Namaste! I'm Thara, your analytics assistant. How can I help you today?",
        "Namaste! I'm Thara. Ready to help you with your data analysis. What can I do for you?",
    ],
    'vanakkam': [
        "வணக்கம்! நான் தாரா, உங்கள் டேட்டா அசிஸ்டன்ட். உங்களுக்கு என்ன கேள்வி கேட்க வேண்டும்?",
        "வணக்கம்! நான் தாரா. உங்கள் தரவை ஆய்வு செய்ய நான் தயாராக இருக்கிறேன். சொல்லுங்கள்.",
        "வணக்கம்! நான் உங்கள் தாரா பேசுறேன். இன்னைக்கு உங்களுக்கு எப்படி உதவலாம்?",
        "வணக்கம்! வாங்க, டேட்டாவை அலசுவோம். உங்களுக்கு என்ன தகவல் வேண்டும்?"
    ],
    'salaam': [
        "Salaam! I'm Thara, your analytics assistant. How may I assist you with your sheets?",
        "Salaam! I'm Thara. Ready to help you analyze your data. What can I do for you?",
    ],
    'bonjour': [
        "Bonjour! I'm Thara, your analytics assistant. How can I help you today?",
        "Bonjour! I'm Thara. Ready to help you with your data. What can I do for you?",
    ],
    'konnichiwa': [
        "Konnichiwa! I'm Thara, your analytics assistant. How can I help you today?",
        "Konnichiwa! I'm Thara. Ready to help you analyze your sheets. What can I do for you?",
    ],
    'nihao': [
        "Ni hao! I'm Thara, your analytics assistant. How can I help you today?",
        "Ni hao! I'm Thara. Ready to help you with your data. What can I do for you?",
    ],
    'casual_question': [
        "I'm doing great, thanks for asking! I'm Thara, and I'm here to help you analyze your data. What would you like to know?",
        "All good here! I'm Thara, your analytics assistant. Ready to dive into your sheets. What can I help you with?",
    ],
    'morning': [
        "Good morning! I'm Thara, your analytics assistant. Ready to start the day with some data insights?",
        "Morning! I'm Thara. Let's make today productive. What would you like to analyze?",
    ],
    'afternoon': [
        "Good afternoon! I'm Thara, your analytics assistant. How can I help you with your data today?",
        "Afternoon! I'm Thara. Ready to help you explore your sheets. What can I do for you?",
    ],
    'evening': [
        "Good evening! I'm Thara, your analytics assistant. How can I assist you with your data tonight?",
        "Evening! I'm Thara. Let's analyze your data. What would you like to know?",
    ],
    'night': [
        "Good night! I'm Thara, your analytics assistant. Working late? How can I help with your data?",
        "Hello! I'm Thara. Burning the midnight oil? Let me help you with your sheets. What do you need?",
    ],
    'tamil_generic': [
        "சொல்லுங்கள், நான் கேட்கிறேன். நான் தாரா, உங்க டேட்டா அசிஸ்டன்ட்.",
        "நான் இருக்கிறேன். உங்கள் டேட்டாவில் என்ன சந்தேகம்?",
        "நான் ரெடி! என்ன கேள்வி கேட்கணும்?",
        "வாங்க பேசலாம். நான் உங்கள் தாரா. எப்படி உதவட்டும்?"
    ]
}


def is_greeting(text: str) -> bool:
    """
    Check if the input is a casual greeting or conversational intent.

    Args:
        text: User input text

    Returns:
        True if it's a greeting/conversational, False if it's a data query
    """
    if not text or len(text.strip()) == 0:
        return False

    text_lower = text.lower().strip()

    # PRIORITY 1: Check capability questions FIRST (before query keyword check)
    # These should ALWAYS be treated as conversational, not data queries
    for pattern in GREETING_CATEGORIES.get('capability', []):
        if re.search(pattern, text_lower, re.IGNORECASE):
            return True

    # PRIORITY 2: Check help requests
    for pattern in GREETING_CATEGORIES.get('help', []):
        if re.search(pattern, text_lower, re.IGNORECASE):
            # But exclude "help me find sales" type queries
            data_keywords = ['sales', 'revenue', 'profit', 'total', 'count', 'data', 'table']
            if not any(kw in text_lower for kw in data_keywords):
                return True

    # PRIORITY 3: Check for name/memory intent patterns
    # "Hey, call me Asif!" should NOT be a greeting - it's a name instruction
    name_patterns = [
        r'\bcall\s+me\b', r'\bmy\s+name\s+is\b', r'\bi\s+am\b', r"\bi'm\b",
        r'\baddress\s+me\s+as\b', r'\byou\s+can\s+call\s+me\b', r"\bname's\b",
        r'\bjust\s+call\s+me\b', r'\bremember\s+(?:me|my|that)\b'
    ]
    has_name_intent = any(re.search(p, text_lower, re.IGNORECASE) for p in name_patterns)
    if has_name_intent:
        return False  # Let memory intent handler process this

    # Check against other greeting patterns
    for category, patterns in GREETING_CATEGORIES.items():
        if category in ['capability', 'help', 'schema_inquiry']:
            continue  # Already checked above (schema_inquiry handled separately)
        for pattern in patterns:
            if re.search(pattern, text_lower, re.IGNORECASE):
                # Make sure it's not part of a longer question
                # e.g., "Hi, what is the total sales?" should not be treated as just a greeting

                # Allow longer matches for phatic/capability phrases
                word_limit = 10 if category in ['phatic', 'capability'] else 5

                if len(text_lower.split()) <= word_limit:
                    return True

    # Check for generic Tamil conversational text
    if re.search(r'[\u0B80-\u0BFF]', text_lower):
        words = text_lower.split()

        # Check for Tamil name patterns - NOT a greeting, it's a name instruction
        tamil_name_keywords = [
            'என் பேரு',      # my name is
            'என் பெயர்',    # my name is (formal)
            'நான்',         # I am (when followed by name)
            'என்னை கூப்பிடு',  # call me
        ]
        if any(kw in text_lower for kw in tamil_name_keywords):
            return False  # Let memory intent handler process this

        # Data query keywords - these mean it's NOT a greeting
        data_keywords = ['sales', 'revenue', 'profit', 'total', 'count', 'list', 'show',
                        'gross', 'net', 'order', 'product', 'category', 'month', 'date',
                        'sheet', 'table', 'column', 'data']

        # Tamil data/schema query keywords - these mean it's NOT a greeting
        tamil_data_keywords = [
            'எவ்வளவு',    # how much
            'மொத்தம்',    # total
            'விற்பனை',    # sales
            'லாபம்',      # profit
            'ஷீட்',       # sheet (transliteration)
            'அட்டவணை',    # table
            'என்னெல்லாம்', # what all
            'எத்தனை',     # how many
            'எந்த',       # which
            'என்ன',       # what
            'எங்கே',      # where
            'எப்படி',     # how
            'காட்டு',     # show
            'பட்டியல்',   # list
            'தரவு',       # data
            'டேட்டா',     # data (transliteration)
            'columns',
            'rows',
            'இருக்கின்றது', # is there / exists
            'இருக்கிறது',  # is there / exists
            'உள்ளது',     # is there / exists
        ]

        is_data_query = any(keyword in text_lower for keyword in data_keywords + tamil_data_keywords)

        # If it's short and not a data query, treat as conversational
        # But be more conservative - only treat as greeting if VERY short (<=4 words)
        # and no question-indicating patterns
        if len(words) <= 4 and not re.search(r'\d', text_lower) and not is_data_query:
            # Additional check: if it ends with ? or has question patterns, it's likely a query
            if not text.strip().endswith('?') and not re.search(r'\?|என்ன|எத்தனை|எவ்வளவு|எந்த|எங்கே|எப்படி', text_lower):
                return True

    return False


def is_capability_question(text: str) -> bool:
    """
    Check if the input is asking about Thara's capabilities.

    Args:
        text: User input text

    Returns:
        True if it's a capability question
    """
    if not text:
        return False

    text_lower = text.lower().strip()

    for pattern in GREETING_CATEGORIES.get('capability', []):
        if re.search(pattern, text_lower, re.IGNORECASE):
            return True

    return False


def detect_schema_inquiry(text: str) -> Optional[Dict]:
    """
    Detect if question is asking about data structure/schema.

    Args:
        text: User input text

    Returns:
        Dict with 'type', 'table', and 'detailed' keys if schema inquiry detected, else None.
        - type: 'schema_inquiry'
        - table: extracted table reference (or None for general "what tables do I have")
        - detailed: True if user wants detailed info (all columns, full description)
    """
    if not text:
        return None

    q_lower = text.lower().strip()

    # Patterns that clearly indicate a DATA query (not schema inquiry)
    # Be specific - don't block valid schema inquiries like "how many tables"
    data_query_patterns = [
        r'\b(what|show)\s+(is|are|was|were)\s+(the\s+)?(total|sum|average)',
        # "how many/much" - only for business metrics, NOT for schema objects
        r'\b(how\s+many|how\s+much)\s+(?:of\s+)?(revenue|sales|profit|orders|units|items|products|customers)',
        r'\b(total|sum|average|count)\s+(of|for)\s+',
        r'\b(sales|revenue|profit)\s+(in|for|during|of)\s+',
        r'\bஎவ்வளவு\b',  # Tamil: how much
        r'\bமொத்தம்\b',  # Tamil: total
        # "what is the X value/sales/amount" - asking for data, not schema
        r'\b(what)\s+(is|are|was|were)\s+(the\s+)?\w+\s+(value|sales|amount|total|profit|revenue)',
        # Month-based queries are data queries (e.g., "what is the October value")
        r'\b(what)\s+(is|are|was|were)\s+(the\s+)?(january|february|march|april|may|june|july|august|september|october|november|december)',
        # Location-based queries are data queries
        r'\b(what)\s+(is|are|was|were)\s+(the\s+)?\w+\s+(for|in)\s+',
        # "show me X sales/data for Y"
        r'\b(show|get|find)\s+(me\s+)?\w+\s+(sales|data|value|profit)',
    ]
    for pattern in data_query_patterns:
        if re.search(pattern, q_lower, re.IGNORECASE):
            return None

    # Check for schema inquiry patterns
    for pattern in GREETING_CATEGORIES.get('schema_inquiry', []):
        if re.search(pattern, q_lower, re.IGNORECASE):
            # Extract table/sheet reference
            table_name = _extract_table_reference(q_lower)

            # Check if user wants detailed info
            detailed_patterns = [
                r'\ball\s+(columns?|fields?)\b',
                r'\bin\s+detail\b',
                r'\bfull\s+(details?|description|info)\b',
                r'\bshow\s+(me\s+)?everything\b',
                r'\bcomplete\s+(list|info|details?)\b',
            ]
            is_detailed = any(re.search(p, q_lower, re.IGNORECASE) for p in detailed_patterns)

            return {'type': 'schema_inquiry', 'table': table_name, 'detailed': is_detailed}

    return None


def _extract_table_reference(text: str) -> Optional[str]:
    """
    Extract table/sheet reference from text.

    Examples:
        "what is sheet 1" → "sheet 1"
        "what is present in sheet four" → "sheet 4"
        "describe the sales table" → "sales"
        "tell me about Pincode sales" → "Pincode sales"
        "what tables do I have" → None (general query)
        "ஷீட் த்ரீயில் என்ன உள்ளது" → "sheet 3"
    """
    # Word to number mapping (English + Tamil transliterations + Tamil numerals)
    word_to_num = {
        # English words
        'one': '1', 'two': '2', 'three': '3', 'four': '4', 'five': '5',
        'six': '6', 'seven': '7', 'eight': '8', 'nine': '9', 'ten': '10',
        'first': '1', 'second': '2', 'third': '3', 'fourth': '4', 'fifth': '5',
        '1st': '1', '2nd': '2', '3rd': '3', '4th': '4', '5th': '5',
        # Tamil transliterations (Tanglish)
        'ஒன்று': '1', 'இரண்டு': '2', 'மூன்று': '3', 'நான்கு': '4', 'ஐந்து': '5',
        'ஆறு': '6', 'ஏழு': '7', 'எட்டு': '8', 'ஒன்பது': '9', 'பத்து': '10',
        # Tanglish transliterations
        'ஒன்': '1', 'டூ': '2', 'த்ரீ': '3', 'ஃபோர்': '4', 'ஃபைவ்': '5',
        'சிக்ஸ்': '6', 'செவன்': '7', 'எய்ட்': '8', 'நைன்': '9', 'டென்': '10',
        # Common variations
        'முதல்': '1', 'இரண்டாவது': '2', 'மூன்றாவது': '3',
    }

    # Pattern: "sheet N" or "sheet_N" (numeric)
    sheet_match = re.search(r'sheet\s*[_]?\s*(\d+)', text, re.IGNORECASE)
    if sheet_match:
        return f"sheet {sheet_match.group(1)}"

    # Pattern: Tamil "ஷீட் N" with number words
    # Match ஷீட் followed by a number word (with optional suffix like யில், ல், இல்)
    tamil_sheet_match = re.search(r'ஷீட்\s*(\w+?)(?:யில்|ல்|இல்|ில்)?\s', text)
    if tamil_sheet_match:
        word = tamil_sheet_match.group(1)
        if word in word_to_num:
            return f"sheet {word_to_num[word]}"
        # Also check if word ends with suffix and strip it
        for suffix in ['யில்', 'ல்', 'இல்', 'ில்', 'ன்', 'யின்']:
            if word.endswith(suffix):
                base_word = word[:-len(suffix)]
                if base_word in word_to_num:
                    return f"sheet {word_to_num[base_word]}"

    # Pattern: "sheet [word number]" - e.g., "sheet four", "sheet one"
    sheet_word_match = re.search(r'sheet\s+(\w+)', text, re.IGNORECASE)
    if sheet_word_match:
        word = sheet_word_match.group(1).lower()
        if word in word_to_num:
            return f"sheet {word_to_num[word]}"
        # Could be a named sheet like "sheet Sales" - return as-is
        if word not in ['the', 'a', 'is', 'are', 'in', 'of', 'that', 'this']:
            return f"sheet {word}"

    # Pattern: "the [name] table" - e.g., "describe the sales table"
    the_table_match = re.search(r'\bthe\s+(\w+(?:\s+\w+)?)\s+table\b', text, re.IGNORECASE)
    if the_table_match:
        name = the_table_match.group(1).strip()
        if name.lower() not in ['my', 'this', 'that', 'what']:
            return name

    # Pattern: "[name] table"
    table_match = re.search(r'(\w+(?:\s+\w+)?)\s+table\b', text, re.IGNORECASE)
    if table_match:
        name = table_match.group(1).strip()
        if name.lower() not in ['the', 'a', 'my', 'this', 'that', 'what']:
            return name

    # Pattern: "table [name]"
    table_match2 = re.search(r'\btable\s+(\w+(?:\s+\w+)?)', text, re.IGNORECASE)
    if table_match2:
        name = table_match2.group(1).strip()
        if name.lower() not in ['is', 'are', 'does', 'do', 'in', 'of']:
            return name

    # Pattern: "about [name]" - extract the thing being asked about
    about_match = re.search(r'\babout\s+(?:the\s+)?(\w+(?:\s+\w+){0,2})', text, re.IGNORECASE)
    if about_match:
        name = about_match.group(1).strip()
        # Filter out generic words
        if name.lower() not in ['data', 'my', 'the', 'this', 'sheet', 'table', 'columns', 'fields']:
            return name

    # No specific table mentioned - general schema inquiry
    return None


def _detect_greeting_category(text: str) -> str:
    """
    Detect which category of greeting/conversational intent was used.

    Args:
        text: User input text

    Returns:
        Category name or 'casual' as default
    """
    text_lower = text.lower().strip()
    has_tamil = bool(re.search(r'[\u0B80-\u0BFF]', text_lower))

    # PRIORITY 1: Check capability questions first
    for pattern in GREETING_CATEGORIES.get('capability', []):
        if re.search(pattern, text_lower, re.IGNORECASE):
            return 'tamil_capability' if has_tamil else 'capability'

    # PRIORITY 2: Check help requests
    for pattern in GREETING_CATEGORIES.get('help', []):
        if re.search(pattern, text_lower, re.IGNORECASE):
            return 'tamil_help' if has_tamil else 'help'

    # Check time-based greetings
    if re.search(r'\b(good\s+morning)\b', text_lower):
        return 'morning'
    elif re.search(r'\b(good\s+afternoon)\b', text_lower):
        return 'afternoon'
    elif re.search(r'\b(good\s+evening)\b', text_lower):
        return 'evening'
    elif re.search(r'\b(good\s+night)\b', text_lower):
        return 'night'

    # Check phatic (mic check) greetings
    for pattern in GREETING_CATEGORIES.get('phatic', []):
        if re.search(pattern, text_lower, re.IGNORECASE):
            if has_tamil or any(t in text_lower for t in ['கேக்குதா', 'கேட்குதா', 'கேட்கிறதா']):
                return 'tamil_phatic'
            return 'phatic'

    # Check welcome
    if re.search(r'\b(welcome)\b', text_lower):
        return 'welcome'

    # Check for specific cultural greetings
    if re.search(r'\b(namaste|namaskar|नमस्ते)\b', text_lower):
        return 'namaste'
    elif re.search(r'\b(vanakkam|வணக்கம்|vanakam)\b', text_lower):
        return 'vanakkam'
    elif re.search(r'\b(salaam|salam|सलाम|assalamu\s+alaikum)\b', text_lower):
        return 'salaam'
    elif re.search(r'\b(bonjour|bon\s+jour)\b', text_lower):
        return 'bonjour'
    elif re.search(r'\b(konnichiwa|こんにちは)\b', text_lower):
        return 'konnichiwa'
    elif re.search(r'\b(ni\s+hao|你好)\b', text_lower):
        return 'nihao'

    # Check for generic Tamil conversational text
    if has_tamil:
        words = text_lower.split()
        if len(words) > 4:
            return 'casual'  # Let it fall through to RAG pipeline

        # Check for numbers which usually indicate a data query
        if re.search(r'\d', text_lower):
            return 'casual'

        # Data/schema query keywords - NOT conversational
        data_keywords = [
            'sales', 'revenue', 'profit', 'total', 'count', 'list', 'show',
            'sheet', 'table', 'column', 'data',
            'எவ்வளவு', 'மொத்தம்', 'விற்பனை', 'லாபம்',
            'ஷீட்', 'அட்டவணை', 'என்னெல்லாம்', 'எத்தனை',
            'என்ன', 'எந்த', 'எங்கே', 'எப்படி', 'காட்டு',
            'இருக்கின்றது', 'இருக்கிறது', 'உள்ளது', 'உன்னிடம்'
        ]
        if any(keyword in text_lower for keyword in data_keywords):
            return 'casual'

        # If it ends with ? or has question patterns, it's likely a query
        if text.strip().endswith('?'):
            return 'casual'

        return 'tamil_generic'

    # Check other categories
    for category, patterns in GREETING_CATEGORIES.items():
        if category in ['time_based', 'cultural', 'phatic', 'capability', 'help']:
            continue  # Already handled above
        for pattern in patterns:
            if re.search(pattern, text_lower, re.IGNORECASE):
                return category

    return 'casual'  # Default


def get_greeting_response(user_input: str = "") -> str:
    """
    Get a dynamic greeting response based on the type of greeting.
    
    Args:
        user_input: The user's greeting text (optional, for context)
        
    Returns:
        Greeting message
    """
    # Add a small delay to make it feel more natural (1-2 seconds)
    delay = random.uniform(1.0, 2.0)
    time.sleep(delay)
    
    # Detect greeting category
    category = _detect_greeting_category(user_input) if user_input else 'casual'
    
    # Get appropriate response template
    # Default to casual if category not found or list is empty
    templates = RESPONSE_TEMPLATES.get(category, RESPONSE_TEMPLATES['casual'])
    if not templates: # Safety check
        templates = RESPONSE_TEMPLATES['casual']
    
    # Randomly select a response from the category
    response = random.choice(templates)
    
    return response
