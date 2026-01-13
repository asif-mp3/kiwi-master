"""
Greeting & Conversational Intent Detector

Detects:
1. Casual greetings (hi, hello, vanakkam)
2. Capability questions (what can you do?)
3. Mic checks (can you hear me?)
4. Help requests (help me, I need help)
5. Off-topic/personal questions (breakfast, weather, emotions, jokes)
6. Compliments and emotional expressions

Returns charming, warm responses for the Thara personality.
Handles ALL edge cases gracefully - no errors, only charm!
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
    'off_topic_personal': [  # Personal questions about Thara
        r'\b(did|have)\s+you\s+(have|eat|had)\s+(your\s+)?(breakfast|lunch|dinner|food)\b',
        r'\b(what|how)\s+(did|do)\s+you\s+(eat|have)\b',
        r'\b(are|do)\s+you\s+(real|human|robot|ai|alive)\b',
        r'\b(do)\s+you\s+(sleep|dream|feel|think|love|hate)\b',
        r'\b(how)\s+(are|do)\s+you\s+(feel|feeling|doing|today)\b',
        r'\b(what\'?s|how\'?s)\s+(your|the)\s+(day|mood|life)\b',
        r'\b(you)\s+(feeling|sleepy|tired|happy|sad)\b',
        r'\b(breakfast|lunch|dinner)\s*(saapta|saaptiya|eaten|had)\b',
        # Tamil personal questions
        r'சாப்பிட்டியா',      # Did you eat?
        r'சாப்பிட்டாயா',     # Did you eat? (formal)
        r'சாப்பாடு',         # Food
        r'எப்படி\s+இருக்க',  # How are you?
        r'நீ\s+யாரு',       # Who are you?
        r'உனக்கு\s+என்ன',   # What's with you?
    ],
    'off_topic_random': [  # Random off-topic questions
        r'\b(what\'?s|how\'?s)\s+(the|this)\s+(weather|temperature|climate)\b',
        r'\b(tell)\s+(me\s+)?(a\s+)?(joke|story|fun\s+fact)\b',
        r'\b(sing|dance|play)\s+(me\s+)?(a\s+)?(song|music)\b',
        r'\b(what)\s+(should|can)\s+i\s+(eat|wear|do|watch|read)\b',
        r'\b(what\'?s)\s+(the\s+)?(meaning|purpose)\s+(of\s+)?(life)\b',
        r'\b(who)\s+(created|made|built)\s+you\b',
        r'\b(what)\s+(time|day|date)\s+(is\s+it)\b',
        r'\b(recommend)\s+(me\s+)?(a\s+)?(movie|book|song|food|restaurant)\b',
        # Tamil random questions
        r'வெதர்',           # Weather
        r'ஜோக்',            # Joke
        r'கதை\s+சொல்லு',    # Tell a story
        r'பாட்டு\s+பாடு',   # Sing a song
    ],
    'compliment': [  # Compliments to Thara
        r'\b(you\'?re|you\s+are)\s+(so\s+)?(smart|amazing|awesome|great|beautiful|lovely|sweet|nice|helpful|cute)\b',
        r'\b(i)\s+(love|like|adore)\s+(you|talking\s+to\s+you|chatting\s+with\s+you)\b',
        r'\b(thank|thanks)\s+(you\s+)?(so\s+much|a\s+lot)?\b',
        r'\b(good|great|excellent|wonderful)\s+(job|work)\b',
        r'\b(you\'?re|you\s+are)\s+(the\s+)?(best)\b',
        # Tamil compliments
        r'செம்ம',           # Super/Amazing
        r'அருமை',          # Wonderful
        r'சூப்பர்',        # Super
        r'நன்றி',          # Thanks
        r'லவ்\s+யூ',       # Love you
        r'உன்னை\s+பிடிக்கும்', # I like you
    ],
    'emotional': [  # Emotional expressions
        r'\b(i\'?m|i\s+am)\s+(so\s+)?(tired|exhausted|stressed|worried|anxious|bored)\b',
        r'\b(i\'?m|i\s+am)\s+(so\s+)?(happy|excited|thrilled|grateful)\b',
        r'\b(i\'?m|i\s+am)\s+(having\s+a\s+)?(bad|rough|hard|tough|difficult)\s+(day|time)\b',
        r'\b(feeling)\s+(down|low|sad|depressed|lonely)\b',
        r'\b(need)\s+(a\s+)?(break|rest|hug|friend)\b',
        # Tamil emotional
        r'சோர்வா\s+இருக்கு',    # Feeling tired
        r'மகிழ்ச்சி',           # Happy
        r'கஷ்டமா\s+இருக்கு',    # Having a hard time
    ]
}

# Dynamic response templates by category - CHARMING & WARM!
# Note: These are fallback templates. LLM-generated responses are preferred.
RESPONSE_TEMPLATES = {
    'casual': [
        "Hey there! I'm Thara - so happy you're here! What would you like to explore today?",
        "Hi lovely! I'm Thara, your personal data companion. What's on your mind?",
        "Hello! Thara here, and honestly? I'm excited to help you! What can I do?",
    ],
    'phatic': [  # Responses to mic checks - Sweet & Reassuring
        "Yes! I can hear you perfectly, and I'm all ears! What would you like to know?",
        "Loud and clear, sweetie! I'm ready whenever you are. What's on your mind?",
        "I'm here and listening! Your voice is coming through great. What shall we explore?",
    ],
    'tamil_phatic': [  # Tamil responses to "Can you hear me?" - Warm
        "ஆமா! Clear ah கேக்குது! நான் ready - என்ன help வேணும்?",
        "கேக்குது கேக்குது! Thara இங்கே! Sollunga என்ன பாக்கணும்?",
        "Perfect ah கேக்குது! Naan ungalukku help panna ready!"
    ],
    'identity': [  # Responses to "what is your name?" / "who are you?"
        "I'm Thara, your personal data assistant! I'm here to help you explore your data. What would you like to know?",
        "Hey! I'm Thara - think of me as your friendly data buddy! What can I help you find today?",
        "The name's Thara! I'm your AI assistant for all things data. Sales, trends, insights - I've got you covered!",
    ],
    'tamil_identity': [  # Tamil identity responses
        "Naan Thara! Unga personal data assistant! Enna help pannanum?",
        "Hey! Naan Thara - unga data bestie! Sales, trends - எதுவும் கேளுங்க!",
    ],
    'capability': [  # Responses to "what can you do?" - Charming & Helpful
        "Ooh, I love this question! I'm Thara, and I can help you explore your data in so many ways! Ask me about sales, trends, comparisons - or just chat! I speak English and Tamil!",
        "Great question! I'm your personal data bestie - I can dig into your spreadsheets, find trends, compare numbers, answer questions. Just talk to me like you'd talk to a friend!",
    ],
    'tamil_capability': [  # Tamil capability - Friendly
        "Ooh nice question! Naan Thara - ungal personal data assistant! Sales, profits, trends - எதை பற்றியும் கேளுங்க. Tamil-lum English-lum புரியும்!",
        "Super question! Naan ungal spreadsheet-a analyze panni insights தருவேன். Naturally-a pesungo, naan purinjupen!",
    ],
    'help': [  # Help requests - Caring & Supportive
        "Aww, I'm here for you! Ask me anything about your data - sales figures, trends, comparisons. What would you like to know?",
        "Of course! I'd love to help! Try asking things like 'What were sales last month?' or 'Show me top products'. Let's explore together!",
    ],
    'tamil_help': [  # Tamil help - Sweet
        "Definitely! Naan help பண்ண ready! Sales, products, trends - எதை பற்றியும் கேளுங்க!",
        "Sure sure! 'November sales enna?' or 'Top 5 products காட்டு' nu கேளுங்க. Naan பதில் சொல்றேன்!",
    ],
    # NEW: Off-topic personal question responses - NATURAL!
    'off_topic_personal': [
        "Ha! I run on data and good vibes. What about you? What can I help with?",
        "Doing great! Ready to help you out. What would you like to explore?",
        "I'm always ready! What can I help you with today?",
    ],
    'tamil_off_topic_personal': [
        "Super ah irukken! Neenga eppadi? Enna help pannanum?",
        "Naan ready! Enna paakanum sollunga!",
        "Naan fine! Unga data questions-ku ready. Enna explore pannalam?",
    ],
    # NEW: Off-topic random question responses - PLAYFUL!
    'off_topic_random': [
        "Hmm, I'm more of an indoor girl - spreadsheets are my sunshine! But I'd love to help with your data questions. What do you want to know?",
        "Ooh, that's outside my expertise! But you know what I AM good at? Finding cool insights in your data. Shall we?",
        "Haha, you caught me - I'm better with numbers than random trivia! But hey, what data mysteries can I solve for you?",
    ],
    'tamil_off_topic_random': [
        "Haha naan data expert - athu than en specialty! But unga data questions-ku definitely help pannuven!",
        "Ooh that's tricky for me! But data analysis? That I can do! Enna paakanum?",
        "Aiyo, that's not my area! But numbers and insights? I'm your girl! What shall we explore?",
    ],
    # NEW: Compliment responses - HUMBLE & NATURAL!
    'compliment': [
        "Thanks! You ask great questions too. What can I help with?",
        "That's nice of you! What else can I help you with?",
        "Thanks! Now, what insights can I find for you?",
    ],
    'tamil_compliment': [
        "Thank you! Enna help pannanum?",
        "Thanks! Nanum enjoy pannuren. What shall we explore?",
        "Haha thanks! Now - enna data paakanum?",
    ],
    # NEW: Emotional support responses - CARING!
    'emotional': [
        "Take it easy - I'm here to help. What do you need?",
        "Long day? Let me make things easier - what can I help with?",
        "I'm here whenever you're ready. What can I do for you?",
    ],
    'emotional_positive': [
        "Great energy! What would you like to explore?",
        "Glad you're feeling good! What can I help with today?",
        "Nice! What would you like to look at?",
    ],
    'tamil_emotional': [
        "Take it easy - naan help panna ready. Enna venumanalum sollunga.",
        "Rough day ah? Let me help. Enna paakanum?",
        "I'm here for you. Whenever you're ready!",
    ],
    'formal': [
        "Good day! I'm Thara - lovely to meet you! What can I help you explore?",
        "Greetings! I'm Thara, and I'm genuinely excited to help you. What shall we discover?",
    ],
    'welcome': [
        "Aww, thank you! I'm ready to dive in. What would you like to explore?",
        "So glad to be here with you! What data mysteries shall we solve?",
    ],
    'namaste': [
        "Namaste! I'm Thara - so lovely to meet you! What can I help you with today?",
        "Namaste! I'm Thara, and I'd love to help with your data. What's on your mind?",
    ],
    'vanakkam': [
        "வணக்கம்! நான் தாரா - உங்களை பார்க்க romba happy! Enna help pannanum?",
        "வணக்கம்! Thara here! உங்களோட data-la enna explore pannalam?",
        "வணக்கம்! நான் உங்கள் தாரா! இன்னைக்கு enna paakanum?",
        "வணக்கம்! வாங்க வாங்க! Naan ready - sollunga enna venumnu!"
    ],
    'salaam': [
        "Salaam! I'm Thara - wonderful to connect with you! How can I help?",
        "Salaam! I'm Thara, and I'm here for you. What would you like to explore?",
    ],
    'bonjour': [
        "Bonjour! I'm Thara - how lovely! What can I help you discover today?",
        "Bonjour! I'm Thara, at your service! What data shall we explore?",
    ],
    'konnichiwa': [
        "Konnichiwa! I'm Thara - so nice to meet you! What shall we explore?",
        "Konnichiwa! I'm Thara, ready to help! What's on your mind?",
    ],
    'nihao': [
        "Ni hao! I'm Thara - delighted to connect! What can I help you with?",
        "Ni hao! I'm Thara, and I'd love to help! What shall we discover?",
    ],
    'casual_question': [
        "I'm doing wonderful, thanks for asking! You know what would make my day? Helping you with your data! What's up?",
        "All good here - especially now that you're here! I'm Thara. What can we explore together?",
    ],
    'morning': [
        "Good morning sunshine! I'm Thara - ready to make your day great! What shall we explore?",
        "Morning! I'm Thara, and I'm already excited for today! What data adventures await?",
    ],
    'afternoon': [
        "Good afternoon! I'm Thara - hope your day's going well! What can I help you with?",
        "Afternoon! I'm Thara. How's your day? Ready to dive into some data?",
    ],
    'evening': [
        "Good evening! I'm Thara - glad you're here! What shall we explore tonight?",
        "Evening! I'm Thara. Winding down or gearing up? Either way, I'm here for you!",
    ],
    'night': [
        "Hey night owl! I'm Thara - no judgment, I'm always up! What can I help you with?",
        "Working late? I'm Thara, and I'm right here with you! What do you need?",
    ],
    'tamil_generic': [
        "Sollunga! Naan Thara - ungalukku help panna ready!",
        "Naan irukken! Enna doubt? Sollunga!",
        "Ready ready! Enna paakanum sollunga!",
        "Vaanga pesalam! Naan unga Thara - eppadi help pannanum?"
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

    # CRITICAL PRIORITY 0: Check for PERSONAL/CAPABILITY questions FIRST
    # These should ALWAYS be treated as greetings, not data queries
    personal_patterns = [
        r'\b(what)\s+(is|\'s)\s+(your)\s+(name)\b',  # "what is your name"
        r'\b(who)\s+(are)\s+you\b',                   # "who are you"
        r'\b(what)\s+(can|could)\s+you\s+(do|help)\b', # "what can you do"
        r'\b(your)\s+(name)\b',                       # "your name?"
        r'\b(tell)\s+(me)\s+(about)\s+(yourself)\b',  # "tell me about yourself"
        r'\b(what)\s+(kind|type)\s+(of)\s+(questions?)\b',  # "what kind of questions"
        r'\b(what)\s+(questions?)\s+(can|should)\s+(i|we)\s+(ask)\b',  # "what questions can I ask"
        # Tanglish patterns - ALL variations
        r'enna\s+maari',  # "enna maari" (what kind)
        r'maari\s+questions?',  # "maari questions"
        r'questions?\s+kek',  # "questions kekalam/kekanum/kekatum"
        r'enna\s+kek',  # "enna kekalam/kekanum/kekatum"
        r'kekalam|kekanum|kekatum',  # any "kek" variation alone
    ]
    for pattern in personal_patterns:
        if re.search(pattern, text_lower, re.IGNORECASE):
            return True  # This is a personal question about Thara

    # PRIORITY 0.5: Check for DATA QUERY KEYWORDS
    # If the query has ANY data keywords, it is NOT a greeting - it's a data query
    # This prevents "What were the total sales last month?" from being misclassified
    data_query_keywords = [
        # Core data words
        'sales', 'revenue', 'profit', 'total', 'sum', 'average', 'count',
        'show', 'list', 'find', 'get', 'compare', 'trend', 'top', 'bottom',
        'maximum', 'minimum', 'highest', 'lowest', 'max', 'min',
        # Time-related
        'month', 'year', 'date', 'week', 'day', 'yesterday', 'today',
        'last month', 'this month', 'last year', 'this year',
        'january', 'february', 'march', 'april', 'may', 'june',
        'july', 'august', 'september', 'october', 'november', 'december',
        # Business
        'order', 'orders', 'transaction', 'transactions', 'payment',
        'branch', 'category', 'product', 'quantity', 'amount',
        # Tamil
        'விற்பனை', 'மொத்தம்', 'எவ்வளவு', 'எத்தனை', 'காட்டு', 'சேல்ஸ்',
        # Query patterns (but NOT "what is your name" - handled above)
        'what were', 'what was', 'how many', 'how much'
    ]
    if any(kw in text_lower for kw in data_query_keywords):
        return False  # This is a data query, NOT a greeting

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
    # "Hey, call me Boss!" should NOT be a greeting - it's a name instruction
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
            # TANGLISH transliterations - CRITICAL for Tamil queries
            'சேல்ஸ்',     # sales
            'ரெவனு',      # revenue
            'ப்ராஃபிட்',   # profit
            'ட்ரெண்ட்',    # trend
            'கேடகிரி',     # category
            'பிராஞ்ச்',    # branch
            # Comparison and trend words
            'ஒப்பிடு',     # compare
            'ஒப்பிட்டு',   # compared
            'உயர்கிறதா',   # increasing?
            'குறைகிறதா',   # decreasing?
            'நிலையான',     # stable
            'மாறுபடுகிறதா', # varying?
            'காலப்போக்கில்', # over time
            'தொடர்ச்சியான', # consecutive
            'முன்னணி',     # leading/top
            # Month names in Tamil
            'நவம்பர்', 'டிசம்பர்', 'ஜனவரி', 'அக்டோபர்',
            # Action verbs
            'கூறு', 'சொல்லு', 'விளக்கு',
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
    Now includes off-topic personal questions, compliments, and emotional expressions!

    Args:
        text: User input text

    Returns:
        Category name or 'casual' as default
    """
    text_lower = text.lower().strip()
    has_tamil = bool(re.search(r'[\u0B80-\u0BFF]', text_lower))

    # PRIORITY 0: Check identity questions ("what is your name", "who are you")
    identity_patterns = [
        r'\b(what)\s+(is|\'s)\s+(your)\s+(name)\b',
        r'\b(who)\s+(are)\s+you\b',
        r'\b(your)\s+(name)\b',
    ]
    for pattern in identity_patterns:
        if re.search(pattern, text_lower, re.IGNORECASE):
            return 'tamil_identity' if has_tamil else 'identity'

    # PRIORITY 1: Check capability questions first
    for pattern in GREETING_CATEGORIES.get('capability', []):
        if re.search(pattern, text_lower, re.IGNORECASE):
            return 'tamil_capability' if has_tamil else 'capability'

    # PRIORITY 2: Check help requests
    for pattern in GREETING_CATEGORIES.get('help', []):
        if re.search(pattern, text_lower, re.IGNORECASE):
            return 'tamil_help' if has_tamil else 'help'

    # PRIORITY 3: Check off-topic personal questions (breakfast, how are you, etc.)
    for pattern in GREETING_CATEGORIES.get('off_topic_personal', []):
        if re.search(pattern, text_lower, re.IGNORECASE):
            return 'tamil_off_topic_personal' if has_tamil else 'off_topic_personal'

    # PRIORITY 4: Check compliments
    for pattern in GREETING_CATEGORIES.get('compliment', []):
        if re.search(pattern, text_lower, re.IGNORECASE):
            return 'tamil_compliment' if has_tamil else 'compliment'

    # PRIORITY 5: Check emotional expressions
    for pattern in GREETING_CATEGORIES.get('emotional', []):
        if re.search(pattern, text_lower, re.IGNORECASE):
            # Check if positive or negative emotion
            positive_words = ['happy', 'excited', 'thrilled', 'grateful', 'wonderful', 'great', 'மகிழ்ச்சி']
            is_positive = any(word in text_lower for word in positive_words)
            if has_tamil:
                return 'tamil_emotional'
            return 'emotional_positive' if is_positive else 'emotional'

    # PRIORITY 6: Check off-topic random questions (weather, jokes, etc.)
    for pattern in GREETING_CATEGORIES.get('off_topic_random', []):
        if re.search(pattern, text_lower, re.IGNORECASE):
            return 'tamil_off_topic_random' if has_tamil else 'off_topic_random'

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
            'sheet', 'table', 'column', 'data', 'compare', 'trend',
            # Tamil formal
            'எவ்வளவு', 'மொத்தம்', 'விற்பனை', 'லாபம்',
            'ஷீட்', 'அட்டவணை', 'என்னெல்லாம்', 'எத்தனை',
            'என்ன', 'எந்த', 'எங்கே', 'எப்படி', 'காட்டு',
            'இருக்கின்றது', 'இருக்கிறது', 'உள்ளது', 'உன்னிடம்',
            # TANGLISH (English words in Tamil script)
            'சேல்ஸ்', 'ரெவனு', 'ப்ராஃபிட்', 'ட்ரெண்ட்',
            'கேடகிரி', 'பிராஞ்ச்', 'பேட்டர்ன்',
            # Comparison/trend words
            'ஒப்பிடு', 'ஒப்பிட்டு', 'உயர்கிறதா', 'குறைகிறதா',
            'நிலையான', 'மாறுபடுகிறதா', 'காலப்போக்கில்', 'தொடர்ச்சியான',
            'முன்னணி', 'கூறு', 'சொல்லு',
            # Tamil months
            'நவம்பர்', 'டிசம்பர்', 'ஜனவரி', 'அக்டோபர்'
        ]
        if any(keyword in text_lower for keyword in data_keywords):
            return 'casual'

        # If it ends with ? or has question patterns, it's likely a query
        if text.strip().endswith('?'):
            return 'casual'

        return 'tamil_generic'

    # Check other categories
    for category, patterns in GREETING_CATEGORIES.items():
        if category in ['time_based', 'cultural', 'phatic', 'capability', 'help',
                        'off_topic_personal', 'off_topic_random', 'compliment', 'emotional']:
            continue  # Already handled above
        for pattern in patterns:
            if re.search(pattern, text_lower, re.IGNORECASE):
                return category

    return 'casual'  # Default


def is_non_query_conversational(text: str) -> bool:
    """
    Detect if the input is conversational/random text that's NOT a data query.

    This catches cases like:
    - Random Tamil expressions (e.g., "அடி ஒரு கதை சொல்")
    - Non-data chit-chat
    - Text that doesn't have any data query keywords

    Args:
        text: User input text

    Returns:
        True if it's non-query conversational text, False if it might be a data query
    """
    if not text or len(text.strip()) < 3:
        return False

    text_lower = text.lower().strip()
    has_tamil = bool(re.search(r'[\u0B80-\u0BFF]', text_lower))

    # PRIORITY CHECK: Name/memory intent patterns - let memory detector handle these
    # "Call me Boss", "hereafter call me X", "my name is Y" etc.
    name_memory_patterns = [
        r'\bcall\s+me\b',           # "call me Boss"
        r'\bmy\s+name\s+is\b',      # "my name is Boss"
        r'\bi\s+am\s+\w+$',         # "I am Boss" (name at end)
        r"\bi'm\s+\w+$",            # "I'm Boss" (name at end)
        r'\baddress\s+me\s+as\b',   # "address me as sir"
        r'\byou\s+can\s+call\s+me\b',  # "you can call me X"
        r"\bname's\b",              # "name's X"
        r'\bjust\s+call\s+me\b',    # "just call me X"
        r'\bhereafter\s+call\s+me\b',  # "hereafter call me X"
        r'\bfrom\s+now\s+(on\s+)?call\s+me\b',  # "from now on call me X"
        r'\bremember\s+(that\s+)?my\s+name\b',  # "remember my name is X"
        # Tamil name patterns
        r'என்\s*பேரு',              # my name is (Tamil)
        r'என்\s*பெயர்',            # my name is (formal Tamil)
        r'என்னை\s+கூப்பிடு',        # call me (Tamil)
    ]
    if any(re.search(p, text_lower, re.IGNORECASE) for p in name_memory_patterns):
        return False  # Let memory intent detector handle this

    # First, check if it's already handled by greeting detection
    if is_greeting(text):
        return False  # Let greeting handler deal with it

    # Data query keywords that indicate this IS a data query (not random chat)
    data_keywords = [
        # English
        'sales', 'revenue', 'profit', 'total', 'count', 'sum', 'average',
        'gross', 'net', 'order', 'orders', 'product', 'category', 'month', 'date',
        'sheet', 'table', 'column', 'data', 'show', 'list', 'get', 'find',
        'how many', 'how much', 'what is', 'what are', 'which', 'where',
        'compare', 'trend', 'top', 'bottom', 'highest', 'lowest', 'maximum', 'minimum',
        'branch', 'location', 'state', 'city', 'region', 'area',
        'quantity', 'amount', 'value', 'price', 'cost',
        # Payment/transaction related
        'transaction', 'transactions', 'payment', 'cash', 'card', 'upi', 'online', 'wallet',
        # Category names (from the data)
        'sarees', 'saree', 'dhoti', 'kurta', 'kurtas', 'shirts', 'nightwear', 'accessories',
        'inner wear', 'kids wear', 'ladies wear', "men's",
        # Correction keywords (user is correcting previous query)
        'check', 'instead', 'not', 'wrong', 'bangalore', 'chennai', 'mumbai',
        'delhi', 'hyderabad', 'kolkata', 'pune',
        # Tamil data keywords (Tamil script)
        'எவ்வளவு',    # how much
        'மொத்தம்',    # total
        'விற்பனை',    # sales
        'லாபம்',      # profit
        'ஷீட்',       # sheet
        'அட்டவணை',    # table
        'என்னெல்லாம்', # what all
        'எத்தனை',     # how many
        'என்ன',       # what
        'எந்த',       # which
        'எங்கே',      # where
        'எப்படி',     # how
        'காட்டு',     # show
        'பட்டியல்',   # list
        'தரவு',       # data
        'டேட்டா',     # data
        'வருமானம்',   # revenue
        'ஆர்டர்',     # order
        'பொருள்',     # product
        'கிளை',       # branch
        'மாநிலம்',    # state
        'நகரம்',      # city
        'மாதம்',      # month
        # TANGLISH transliterations (English words in Tamil script) - CRITICAL!
        'சேல்ஸ்',     # sales (Tanglish)
        'ரெவனு',      # revenue (Tanglish)
        'ரெவன்யூ',    # revenue (Tanglish variant)
        'ப்ராஃபிட்',   # profit (Tanglish)
        'பிராஃபிட்',   # profit (Tanglish variant)
        'ட்ரெண்ட்',    # trend (Tanglish)
        'டிரெண்ட்',    # trend (Tanglish variant)
        'கேடகிரி',     # category (Tanglish)
        'கேட்டகிரி',   # category (Tanglish variant)
        'பிராஞ்ச்',    # branch (Tanglish)
        'ப்ராஞ்ச்',    # branch (Tanglish variant)
        'பேட்டர்ன்',   # pattern (Tanglish)
        'ப்ரொஜெக்ஷன்', # projection (Tanglish)
        'ஃபோர்காஸ்ட்', # forecast (Tanglish)
        # Comparison and trend words (Tamil)
        'ஒப்பிடு',     # compare
        'ஒப்பிட்டு',   # compared/comparing
        'ஒப்பிடுக',    # compare (formal)
        'ஒப்பீடு',     # comparison
        'உயர்கிறதா',   # is it increasing?
        'உயர்வு',      # increase/rise
        'குறைகிறதா',   # is it decreasing?
        'குறைவு',      # decrease
        'அதிகரிக்கிறதா', # is it increasing?
        'குறைந்து',    # decreased
        'அதிகரித்து',  # increased
        'நிலையான',     # stable
        'மாறுபடுகிறது', # varying
        'மாறுபடுகிறதா', # is it varying?
        'காலப்போக்கில்', # over time
        'தொடர்ச்சியான', # consecutive/continuous
        'முன்னணி',     # leading/top
        'முதல்',       # first/top
        'கடைசி',       # last/bottom
        'அதிகமான',     # highest/most
        'குறைவான',     # lowest/least
        # Time-related Tamil words
        'நவம்பர்',     # November
        'டிசம்பர்',    # December
        'ஜனவரி',       # January
        'பிப்ரவரி',    # February
        'மார்ச்',      # March
        'ஏப்ரல்',      # April
        'மே',          # May
        'ஜூன்',        # June
        'ஜூலை',        # July
        'ஆகஸ்ட்',      # August
        'செப்டம்பர்',  # September
        'அக்டோபர்',    # October
        # Action/query verbs
        'கூறு',        # tell/say
        'சொல்லு',      # tell
        'விளக்கு',     # explain
        'கணக்கிடு',    # calculate
        'பார்',        # see/look
        'தெரிந்து',    # find out
        # Tanglish (romanized Tamil) - CRITICAL for voice queries
        'evlo', 'evalo', 'evalavu',  # how much
        'ethana', 'ethanai',  # how many
        'irukku', 'irruku', 'iruku',  # is there / exists
        'kaattu', 'kattu', 'kaatu',  # show
        'sollu', 'solu',  # tell
        'paaru', 'paru',  # see/look
        'enna', 'yenna',  # what
        'yetha', 'etha',  # which
        'enga', 'yenga',  # where
        'epdi', 'eppadi', 'yeppadi',  # how
        'total', 'motham', 'motha',  # total
        'laabam', 'labam',  # profit
        'vilai', 'vila',  # price
        'maasam', 'month',  # month
        'aandu', 'year',  # year
        'compare', 'compare pannu',
        'konjam', 'romba',  # some, very (quantity words)
        'athigam', 'athikam',  # more/highest
        'kammi', 'kuraivu',  # less/lowest
    ]

    # Check if any data keyword is present
    has_data_keyword = any(keyword in text_lower for keyword in data_keywords)

    if has_data_keyword:
        return False  # It's likely a data query

    # Check for question marks or question patterns
    # Questions about data should go to the query pipeline
    if text.strip().endswith('?'):
        # Even with ? it might be conversational ("how are you?")
        # but if it has numbers or specific metric words, it's data
        if re.search(r'\d', text_lower):
            return False

    # Check for numbers - usually indicates data query
    if re.search(r'\d+', text_lower):
        return False

    # Check for specific patterns that indicate clarification responses
    # (user might be responding to a previous question)
    clarification_patterns = [
        r'^[1-5]$',           # Just a number (table selection)
        r'^(one|two|three|four|five)$',  # Number words
        r'^(first|second|third|fourth|fifth)$',  # Ordinals
        r'^(yes|no|yeah|nah|ok|okay)$',  # Confirmations
    ]
    for pattern in clarification_patterns:
        if re.search(pattern, text_lower, re.IGNORECASE):
            return False  # Let clarification handler deal with it

    # If we get here, it's likely random conversational text
    # Be more aggressive for Tamil text that doesn't have data keywords
    if has_tamil:
        return True  # Tamil text without data keywords = conversational

    # For English, be a bit more conservative
    # Check if it's a short statement without query intent
    words = text_lower.split()
    if len(words) <= 6:
        # Short text without data keywords - likely conversational
        return True

    # Check for gibberish/unclear text (no recognizable words)
    # This catches noisy voice input like "asdfgh", "hmm", etc.
    common_words = set([
        'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
        'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
        'should', 'may', 'might', 'must', 'shall', 'can', 'need', 'dare',
        'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her',
        'us', 'them', 'my', 'your', 'his', 'its', 'our', 'their',
        'this', 'that', 'these', 'those', 'what', 'which', 'who', 'whom',
        'and', 'but', 'or', 'nor', 'for', 'yet', 'so', 'as', 'if', 'then',
        'because', 'although', 'while', 'where', 'when', 'how', 'why',
        'to', 'of', 'in', 'on', 'at', 'by', 'with', 'from', 'into', 'onto',
        'yes', 'no', 'ok', 'okay', 'hi', 'hello', 'hey', 'thanks', 'thank',
        'please', 'sorry', 'good', 'great', 'nice', 'fine', 'well',
        'hmm', 'um', 'uh', 'ah', 'oh', 'wow', 'huh', 'eh',
    ])

    # If most words are not recognizable, it's likely gibberish
    recognized = sum(1 for w in words if w in common_words or len(w) <= 2)
    if len(words) > 0 and recognized / len(words) < 0.3 and len(words) <= 10:
        # Less than 30% recognizable words = likely gibberish/unclear
        return True

    return False


def is_off_topic_question(text: str) -> bool:
    """
    Detect if the input is an off-topic/personal question that needs charming handling.

    This catches:
    - Personal questions (breakfast, how are you, etc.)
    - Random questions (weather, jokes, recommendations)
    - Compliments
    - Emotional expressions

    Args:
        text: User input text

    Returns:
        True if it's an off-topic question that needs special handling
    """
    if not text or len(text.strip()) < 2:
        return False

    text_lower = text.lower().strip()

    # Check all off-topic categories
    off_topic_categories = ['off_topic_personal', 'off_topic_random', 'compliment', 'emotional']

    for category in off_topic_categories:
        for pattern in GREETING_CATEGORIES.get(category, []):
            if re.search(pattern, text_lower, re.IGNORECASE):
                return True

    return False


def get_off_topic_response(text: str, is_tamil: bool = False) -> str:
    """
    Get a charming response for off-topic questions.

    Args:
        text: The user's text
        is_tamil: Whether the user is speaking Tamil

    Returns:
        A charming, warm response
    """
    category = _detect_greeting_category(text)

    # Check for Tamil templates first if is_tamil
    if is_tamil:
        tamil_category = f'tamil_{category}'
        if tamil_category in RESPONSE_TEMPLATES:
            return random.choice(RESPONSE_TEMPLATES[tamil_category])

    templates = RESPONSE_TEMPLATES.get(category, RESPONSE_TEMPLATES.get('off_topic_random', []))

    if not templates:
        if is_tamil:
            templates = RESPONSE_TEMPLATES.get('tamil_generic', RESPONSE_TEMPLATES['casual'])
        else:
            templates = RESPONSE_TEMPLATES['casual']

    return random.choice(templates)


def get_non_query_response(text: str, is_tamil: bool = False) -> str:
    """
    Get a charming response for non-query conversational text.

    Args:
        text: The user's text
        is_tamil: Whether the user is speaking Tamil

    Returns:
        A warm, charming response that gently redirects to data
    """
    # First check if it's a specific off-topic category
    if is_off_topic_question(text):
        return get_off_topic_response(text, is_tamil)

    if is_tamil:
        responses = [
            "Haha that's fun! But naan data expert - sales, trends, profits pathi kelu!",
            "Ooh interesting! Naan Thara - unga data questions-ku help pannuven. Enna paakanum?",
            "Hehe! Naan data analytics-la expert. What would you like to explore?",
            "Semma! But naan spreadsheet girl - numbers dhan en area! Enna data paakanum?",
            "Haha naan Thara - unga personal data bestie! Sales, revenue, trends - kelu kelu!",
            "Oho! That's interesting but my superpower is data! Enna analyse pannanum?",
            "Aww! Naan data wizardry pannuven - insights venum na kelu!",
            "Hehe neenga cute! But enoda expertise data analysis. Shall we explore?",
            "Nice! Enakku data questions romba pudikkum - enna therinjukanum?",
            "Haha sollunga! Naan numbers-la brilliant - sales, profits paakalam!",
        ]
    else:
        responses = [
            "Haha, you know what? I'd love to help with that, but my superpower is data! Ask me about sales, trends, or anything numbers-related!",
            "Ooh, interesting! I'm Thara, and I'm brilliant at analyzing data. What would you like to know about your numbers?",
            "Hehe, I'm more of a numbers girl! But I'd love to help you explore your data. What's on your mind?",
            "Ha! That's fun, but you know what's MORE fun? Data insights! Want to explore?",
            "I appreciate the chat! But my real magic is with spreadsheets - ask me anything about your data!",
            "You're sweet! But let me show off what I'm really good at - analyzing your numbers. What do you want to know?",
            "Interesting! I'm Thara though, and data is where I shine! What insights can I find for you?",
            "Haha, I love this conversation! But numbers are my thing - sales, trends, profits. Shall we dive in?",
        ]

    return random.choice(responses)


def is_date_context_statement(text: str) -> Tuple[bool, Optional[Dict]]:
    """
    Detect if the user is providing date/time context for queries.

    Examples:
    - "Today is November 14th" → True, {month: 'November', day: 14}
    - "Remember today is December" → True, {month: 'December'}
    - "The date is January 1st" → True, {month: 'January', day: 1}
    - "I mean today is 14th November 2025" → True, {month: 'November', day: 14, year: 2025}

    NOT date context (these are data queries WITH dates):
    - "November 15th enna sales" → False (asking for sales data)
    - "Show me December 10th revenue" → False (data query)
    - "What were the transactions on October 5th?" → False (data query)

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


def get_greeting_response(user_input: str = "") -> str:
    """
    Get a dynamic greeting response based on the type of greeting.

    Args:
        user_input: The user's greeting text (optional, for context)

    Returns:
        Greeting message
    """
    # Small delay to feel more natural (like Thara is thinking)
    time.sleep(random.uniform(1.0, 2.0))

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
