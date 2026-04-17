"""
Greeting & Conversational Intent Detector

Detects:
1. Casual greetings (hi, hello, vanakkam)
2. Capability questions (what can you do?)
3. Mic checks (can you hear me?)
4. Help requests (help me, I need help)
5. Schema inquiries (what is sheet 1, describe the table)
6. Date context statements (today is November 14th)

Complex cases (Tanglish greetings, off-topic questions, random Tamil text, compliments,
emotional expressions) are handled by the routing layer — if no table matches,
LLM responds naturally via generate_off_topic_response().
"""

import random
import re
from typing import Tuple, Optional, Dict

# Greeting patterns with categories (case-insensitive)
GREETING_CATEGORIES = {
    'casual': [
        r'\b(hi|hello|hey|hola|yo)\b',
        r'\bhii+\b',  # "hii", "hiii" etc. (common Tanglish/informal spelling)
        r'^(hi|hello|hey)$',
        r'^(hi|hello),?\s+thara$',
    ],
    'phatic': [  # Mic checks and connectivity capability checks
        r'\b(can|could)\s+you\s+(hear|listen)\s+(to\s+)?me\b',
        r'\bhear\s+me\b',  # Simple "hear me"
        r'\b(you)\s+(hear|hearing)\s+me\b',  # "you hear me"
        r'\b(are\s+you)\s+(there|listening|online|ready)\b',
        r'\b(you)\s+there\b',  # "you there?"
        r'\b(testing)\s+(1|one)\s*,?\s*(2|two)\s*,?\s*(3|three)\b',
        r'\b(mic|microphone)\s+(check|test)\b',
        r'^(test|testing)$',  # Just "test" or "testing"
        # Tamil Mic Checks
        r'கேக்குதா',  # Kekudha (Can you hear?)
        r'கேட்குதா',  # Ketkudha (Can you hear?)
        r'பேசுறது\s+கேக்குதா',  # Pesuradhu kekudha
        r'பேசுறது\s+கேட்குதா',  # Pesuradhu ketkudha
        r'கேட்கிறதா',  # Ketkiradha (Formal: Is it audible?)
        r'நான்\s+பேசுறது',  # Naan pesuradhu (What I'm speaking)
        r'கேக்குது',  # Kekudhu
    ],
    'capability': [  # Questions about what Thara can do
        r'\b(what)\s+(can|could)\s+you\s+(do|help)\b',
        r'\b(what)\s+(are)\s+(your|you)\s+(capabilities|features|abilities)\b',
        r'\b(how)\s+(can|could)\s+you\s+help\b',
        r'\b(what)\s+(do)\s+you\s+(do|offer)\b',
        r'\b(tell)\s+(me)\s+(about)\s+(yourself|you)\b',
        r'\b(who)\s+(are)\s+you\b',
        r'\b(introduce)\s+(yourself)\b',
        r'\b(what)\s+(is|\'s)\s+(your)\s+(name)\b',  # "what is your name" / "what's your name"
        r'\b(your)\s+(name)\b',  # "your name?"
        r'\b(what)\s+(kind|type)\s+(of)\s+(questions?)\b',  # "what kind of questions"
        r'\b(what)\s+(questions?)\s+(can|should)\s+(i|we)\s+(ask)\b',  # "what questions can I ask"
        # Tamil capability questions
        r'என்னெல்லாம்\s+பண்ண\s+முடியும்',  # What all can you do?
        r'என்ன\s+பண்ண\s+முடியும்',  # What can you do?
        r'என்ன\s+செய்ய\s+முடியும்',  # What can you do? (formal)
        r'உங்களால்\s+என்ன\s+செய்ய\s+முடியும்',  # What can you do?
        r'எப்படி\s+உதவ\s+முடியும்',  # How can you help?
        r'நீங்கள்\s+யார்',  # Who are you?
        r'உன்னைப்\s+பற்றி\s+சொல்லு',  # Tell me about yourself
        # Tanglish capability questions
        r'enna\s+maari\s+questions?',  # "enna maari questions" (what kind of questions)
        r'enna\s+questions?\s+kekalam',  # "enna questions kekalam" (what questions can I ask)
        r'enna\s+kekalam',  # "enna kekalam" (what can I ask)
        r'enna\s+kekanum',  # "enna kekanum" (what should I ask)
        r'questions?\s+enna\s+kekalam',  # "questions enna kekalam"
    ],
    'formal': [
        r'\b(good\s+(morning|afternoon|evening|day))\b',
        r'\b(greetings)\b',
        r'\b(welcome)\b',
    ],
    'cultural': [
        r'\b(namaste|namaskar|नमस्ते)\b',  # Hindi
        r'\b(vanakkam|vanakam)\b',  # Tamil (Latin script)
        r'(வணக்கம்)',  # Tamil script (no \b — virama breaks word boundary)
        r'\b(salaam|salam|सलाम|assalamu\s+alaikum)\b',  # Arabic/Urdu
        r'\b(bonjour|bon\s+jour)\b',  # French
        r'\b(konnichiwa|こんにちは)\b',  # Japanese
        r'\b(ni\s+hao|你好)\b',  # Chinese
    ],
    'casual_question': [
        r'\b(what\'?s\s+up|whats\s+up|wassup|sup)\b',
        r'\b(how\s+(are\s+you|r\s+u|are\s+ya))\b',
        r'\b(how\'?s\s+it\s+going)\b',
        # NOTE: Tanglish patterns (epdi iruka, nalla irukkiya) REMOVED.
        # Routing handles them — if no table matches, LLM responds naturally.
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
        # Basic "what is sheet X" patterns - MUST include sheet/table number or name
        r'\b(what)\s+(is|are)\s+(sheet|table)\s+(\d+|\w+)',  # "what is sheet 1" or "what is table sales"
        r'\b(what)\s+(is|are)\s+the\s+(sheet|table|data|dataset)\b',  # "what is the sheet" (general)
        r'\b(what)\s+(is|are)\s+(?:in\s+)?(?:the\s+)?(sheet|table)\s*\d+',  # "what is in sheet 1"
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
    ],
}


def is_greeting(text: str) -> bool:
    """
    Check if the input is an obvious greeting or conversational intent.

    SIMPLIFIED: Only catches clear-cut greetings (hi, hello, good morning, etc.)
    and capability questions (who are you, what can you do).

    Complex cases (Tanglish greetings, off-topic questions, random Tamil text)
    are handled by the routing layer — if no table matches, LLM responds naturally.
    This eliminates the need for maintaining 1000+ regex patterns.

    Args:
        text: User input text

    Returns:
        True if it's an obvious greeting, False otherwise
    """
    if not text or len(text.strip()) == 0:
        return False

    text_lower = text.lower().strip()
    words = text_lower.split()

    # Long text is unlikely to be a bare greeting — let routing handle it
    if len(words) > 8:
        return False

    # Skip if it has obvious data keywords (word-level match, not substring)
    _data_words = {
        'sales', 'revenue', 'profit', 'total', 'count', 'sum', 'average',
        'show', 'list', 'find', 'compare', 'trend', 'hours', 'amount',
        'sheet', 'table', 'column', 'data', 'report', 'month', 'year',
        'attendance', 'salary', 'payroll', 'branch', 'category', 'product',
    }
    if set(words) & _data_words:
        return False

    # Skip name/memory intents — let memory handler process these
    if re.search(r'\bcall\s+me\b|\bmy\s+name\s+is\b|\bjust\s+call\s+me\b', text_lower):
        return False

    # Check against clear-cut greeting categories only
    # NOTE: schema_inquiry is NOT checked here (has dedicated detect_schema_inquiry()).
    _greeting_categories = [
        'casual', 'formal', 'cultural', 'phatic', 'capability',
        'casual_question', 'time_based', 'help',
    ]
    for category in _greeting_categories:
        for pattern in GREETING_CATEGORIES.get(category, []):
            if re.search(pattern, text_lower, re.IGNORECASE):
                # Allow longer text for phatic/capability (mic checks, "what can you do")
                word_limit = 10 if category in ['phatic', 'capability'] else 6
                if len(words) <= word_limit:
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
        # Aggregation queries - asking for max/min/most/least are DATA queries, not schema
        r'\b(maximum|minimum|max|min|most|least|highest|lowest)\s+(number|count|amount|value)',
        r'\b(which|what)\s+\w+\s+(has|have)\s+(the\s+)?(maximum|minimum|max|min|most|least|highest|lowest)',
        # "state/category with maximum/most" type queries
        r'\bwith\s+(the\s+)?(maximum|minimum|max|min|most|least|highest|lowest)\b',
        # "has the maximum/most employees/sales" type queries
        r'\bhas\s+(the\s+)?(maximum|minimum|max|min|most|least|highest|lowest)\s+(number|count|employees|sales|profit)',
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
        "what is sheet 1" -> "sheet 1"
        "what is present in sheet four" -> "sheet 4"
        "describe the sales table" -> "sales"
        "tell me about Pincode sales" -> "Pincode sales"
        "what tables do I have" -> None (general query)
        "ஷீட் த்ரீயில் என்ன உள்ளது" -> "sheet 3"
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


def is_date_context_statement(text: str) -> Tuple[bool, Optional[Dict]]:
    """
    Detect if the user is providing date/time context for queries.

    Examples:
    - "Today is November 14th" -> True, {month: 'November', day: 14}
    - "Remember today is December" -> True, {month: 'December'}
    - "The date is January 1st" -> True, {month: 'January', day: 1}
    - "I mean today is 14th November 2025" -> True, {month: 'November', day: 14, year: 2025}

    NOT date context (these are data queries WITH dates):
    - "November 15th enna sales" -> False (asking for sales data)
    - "Show me December 10th revenue" -> False (data query)
    - "What were the transactions on October 5th?" -> False (data query)

    Args:
        text: User input text

    Returns:
        Tuple of (is_date_context, extracted_date_info)
    """
    if not text or len(text.strip()) < 5:
        return False, None

    text_lower = text.lower().strip()

    # CRITICAL: First check if this contains DATA QUERY keywords
    # If it does, it's NOT a date context statement - it's a data query with a date filter
    data_query_keywords = [
        # English data keywords
        'sales', 'revenue', 'profit', 'total', 'count', 'sum', 'average',
        'transactions', 'orders', 'cost', 'quantity', 'amount', 'show',
        'what', 'how many', 'how much', 'get', 'find', 'list', 'give',
        'compare', 'trend', 'branch', 'category', 'state', 'payment',
        # Tanglish data keywords
        'enna', 'evlo', 'ethana', 'kaattu', 'sollu', 'paaru', 'paru',
        'irukku', 'irruku', 'koodu', 'total', 'motham',
        # Tamil script
        'என்ன', 'எவ்வளவு', 'எத்தனை', 'காட்டு', 'சொல்லு',
    ]

    # If any data keyword is present, this is a DATA QUERY, not date context
    if any(keyword in text_lower for keyword in data_query_keywords):
        return False, None

    # Date context patterns (only match if NO data keywords present)
    date_context_patterns = [
        r'\b(today|yesterday|tomorrow)\s+(is|was|will\s+be)\s+',
        r'\b(the\s+)?(date|day)\s+(is|was)\s+',
        r'\b(it\'?s|it\s+is)\s+(\d{1,2}(st|nd|rd|th)?\s+)?(january|february|march|april|may|june|july|august|september|october|november|december)',
        r'\b(remember|note|know)\s+(that\s+)?(today|the\s+date)',
        r'\b(i\s+mean|actually)\s+(today|the\s+date)\s+(is|was)',
        r'\b(\d{1,2})(st|nd|rd|th)?\s+(of\s+)?(january|february|march|april|may|june|july|august|september|october|november|december)',
        r'\b(january|february|march|april|may|june|july|august|september|october|november|december)\s+(\d{1,2})(st|nd|rd|th)?',
    ]

    is_date_context = any(re.search(pattern, text_lower, re.IGNORECASE) for pattern in date_context_patterns)

    if not is_date_context:
        return False, None

    # Extract date info
    date_info = {}

    # Extract month
    months = ['january', 'february', 'march', 'april', 'may', 'june',
              'july', 'august', 'september', 'october', 'november', 'december']
    for month in months:
        if month in text_lower:
            date_info['month'] = month.capitalize()
            break

    # Extract day
    day_match = re.search(r'\b(\d{1,2})(st|nd|rd|th)?\b', text_lower)
    if day_match:
        day = int(day_match.group(1))
        if 1 <= day <= 31:
            date_info['day'] = day

    # Extract year
    year_match = re.search(r'\b(20\d{2})\b', text_lower)
    if year_match:
        date_info['year'] = int(year_match.group(1))

    return True, date_info if date_info else None


def get_date_context_response(date_info: Optional[Dict], is_tamil: bool = False) -> str:
    """
    Get a charming response acknowledging date context.

    Args:
        date_info: Extracted date information
        is_tamil: Whether to respond in Tamil

    Returns:
        Acknowledgment response
    """
    if date_info:
        month = date_info.get('month', '')
        day = date_info.get('day', '')

        if month and day:
            date_str = f"{month} {day}"
        elif month:
            date_str = month
        else:
            date_str = "that date"

        if is_tamil:
            responses = [
                f"Got it! {date_str} ah? Naan remember pannikitten. Enna paakanum?",
                f"Okay {date_str}! Noted. What would you like to know about your data?",
                f"Super! {date_str} context-la paakalam. Enna query irukku?",
            ]
        else:
            responses = [
                f"Got it! So we're looking at {date_str}. What would you like to know?",
                f"Okay, {date_str} - noted! Now, what can I help you find?",
                f"Perfect, I'll keep {date_str} in mind. What would you like to explore?",
            ]
    else:
        if is_tamil:
            responses = [
                "Okay, date context noted! Enna help pannanum?",
                "Got it! Now enna paakanum?",
            ]
        else:
            responses = [
                "Got it! What would you like to know about your data?",
                "Noted! Now, what can I help you with?",
            ]

    return random.choice(responses)
