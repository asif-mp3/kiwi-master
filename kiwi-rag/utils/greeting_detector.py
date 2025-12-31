"""
Greeting Detector

Detects casual greetings and returns appropriate responses.
Prevents unnecessary sheet queries for simple greetings.
Enhanced with dynamic responses based on greeting type.
"""

import time
import random
import re
from datetime import datetime

# Greeting patterns with categories (case-insensitive)
GREETING_CATEGORIES = {
    'casual': [
        r'\b(hi|hello|hey|hola|yo)\b',
        r'^(hi|hello|hey)$',
        r'^(hi|hello),?\s+kiwi$',
    ],
    'phatic': [ # Mic checks and connectivity capability checks
        r'\b(can|could)\s+you\s+(hear|listen)\s+(to\s+)?me\b',
        r'\b(are\s+you)\s+(there|listening|online|ready)\b',
        r'\b(testing)\s+(1|one)\s*,?\s*(2|two)\s*,?\s*(3|three)\b',
        r'\b(mic|microphone)\s+(check|test)\b',
        # Tamil Mic Checks
        r'கேக்குதா', # Kekudha (Can you hear?)
        r'கேட்குதா', # Ketkudha (Can you hear?)
        r'பேசுறது\s+கேக்குதா', # Pesuradhu kekudha
        r'பேசுறது\s+கேட்குதா', # Pesuradhu ketkudha
        r'கேட்கிறதா', # Ketkiradha (Formal: Is it audible?)
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
    ]
}

# Dynamic response templates by category
RESPONSE_TEMPLATES = {
    'casual': [
        "Hi there! I'm Kiwi, your analytics assistant. What would you like to know about your data?",
        "Hello! I'm Kiwi. Ready to help you analyze your sheets. What can I do for you?",
        "Hey! Kiwi here. How can I assist you with your data today?",
    ],
    'phatic': [ # Responses to mic checks
        "Yes, I can hear you clearly! I'm ready to help with your data analysis. What's on your mind?",
        "Loud and clear! I'm listening. Ask me anything about your spreadsheet.",
        "I'm here and I can hear you perfectly. How can I assist you today?",
    ],
    'tamil_phatic': [ # Tamil responses to "Can you hear me?"
        "ஆம், நீங்கள் பேசுவது எனக்கு நன்றாகக் கேட்கிறது. நான் கிவி, உங்கள் டேட்டா அசிஸ்டன்ட். சொல்லுங்கள்.",
        "கேட்கிறது! நான் உங்கள் கிவி. உங்கள் அட்டவணை பற்றி என்ன தெரிந்துகொள்ள வேண்டும்?",
        "தெளிவாகக் கேட்கிறது. நான் உதவி செய்யத் தயார். என்ன கேள்வி இருக்கிறது?"
    ],
    'formal': [
        "Good day! I'm Kiwi, your analytics assistant. How may I help you with your spreadsheet today?",
        "Greetings! I'm Kiwi. I'm here to help you analyze your data. What would you like to explore?",
    ],
    'welcome': [
        "Thank you! I'm ready to help you analyze your data. Where should we start?",
        "Glad to be here! How can I assist you with your spreadsheet today?",
    ],
    'namaste': [
        "Namaste! I'm Kiwi, your analytics assistant. How can I help you today?",
        "Namaste! I'm Kiwi. Ready to help you with your data analysis. What can I do for you?",
    ],
    'vanakkam': [
        "வணக்கம்! நான் கிவி, உங்கள் டேட்டா அசிஸ்டன்ட். உங்களுக்கு என்ன கேள்வி கேட்க வேண்டும்?",
        "வணக்கம்! நான் கிவி. உங்கள் தரவை ஆய்வு செய்ய நான் தயாராக இருக்கிறேன். சொல்லுங்கள்.",
        "வணக்கம்! நான் உங்கள் கிவி பேசுறேன். இன்னைக்கு உங்களுக்கு எப்படி உதவலாம்?",
        "வணக்கம்! வாங்க, டேட்டாவை அலசுவோம். உங்களுக்கு என்ன தகவல் வேண்டும்?"
    ],
    'salaam': [
        "Salaam! I'm Kiwi, your analytics assistant. How may I assist you with your sheets?",
        "Salaam! I'm Kiwi. Ready to help you analyze your data. What can I do for you?",
    ],
    'bonjour': [
        "Bonjour! I'm Kiwi, your analytics assistant. How can I help you today?",
        "Bonjour! I'm Kiwi. Ready to help you with your data. What can I do for you?",
    ],
    'konnichiwa': [
        "Konnichiwa! I'm Kiwi, your analytics assistant. How can I help you today?",
        "Konnichiwa! I'm Kiwi. Ready to help you analyze your sheets. What can I do for you?",
    ],
    'nihao': [
        "Ni hao! I'm Kiwi, your analytics assistant. How can I help you today?",
        "Ni hao! I'm Kiwi. Ready to help you with your data. What can I do for you?",
    ],
    'casual_question': [
        "I'm doing great, thanks for asking! I'm Kiwi, and I'm here to help you analyze your data. What would you like to know?",
        "All good here! I'm Kiwi, your analytics assistant. Ready to dive into your sheets. What can I help you with?",
    ],
    'morning': [
        "Good morning! I'm Kiwi, your analytics assistant. Ready to start the day with some data insights?",
        "Morning! I'm Kiwi. Let's make today productive. What would you like to analyze?",
    ],
    'afternoon': [
        "Good afternoon! I'm Kiwi, your analytics assistant. How can I help you with your data today?",
        "Afternoon! I'm Kiwi. Ready to help you explore your sheets. What can I do for you?",
    ],
    'evening': [
        "Good evening! I'm Kiwi, your analytics assistant. How can I assist you with your data tonight?",
        "Evening! I'm Kiwi. Let's analyze your data. What would you like to know?",
    ],
    'night': [
        "Good night! I'm Kiwi, your analytics assistant. Working late? How can I help with your data?",
        "Hello! I'm Kiwi. Burning the midnight oil? Let me help you with your sheets. What do you need?",
    ],
    'tamil_generic': [
        "சொல்லுங்கள், நான் கேட்கிறேன். நான் கிவி, உங்க டேட்டா அசிஸ்டன்ட்.",
        "நான் இருக்கிறேன். உங்கள் டேட்டாவில் என்ன சந்தேகம்?",
        "நான் ரெடி! என்ன கேள்வி கேட்கணும்?",
        "வாங்க பேசலாம். நான் உங்கள் கிவி. எப்படி உதவட்டும்?"
    ]
}


def is_greeting(text: str) -> bool:
    """
    Check if the input is a casual greeting.
    
    Args:
        text: User input text
        
    Returns:
        True if it's a greeting, False otherwise
    """
    if not text or len(text.strip()) == 0:
        return False
    
    text_lower = text.lower().strip()
    
    # Check against all patterns
    for category, patterns in GREETING_CATEGORIES.items():
        for pattern in patterns:
            if re.search(pattern, text_lower, re.IGNORECASE):
                # Make sure it's not part of a longer question
                # e.g., "Hi, what is the total sales?" should not be treated as just a greeting
                
                # Allow longer matches for phatic phrases like "can you hear me"
                word_limit = 10 if category == 'phatic' else 5
                
                if len(text_lower.split()) <= word_limit: 
                    return True
                    
    # Also check for generic Tamil text that is short
    if re.search(r'[\u0B80-\u0BFF]', text_lower):
        if len(text_lower.split()) <= 10: # Allow reasonable length Tamil casual talk
            return True
    
    return False


def _detect_greeting_category(text: str) -> str:
    """
    Detect which category of greeting was used.
    
    Args:
        text: User input text
        
    Returns:
        Category name or 'casual' as default
    """
    text_lower = text.lower().strip()
    
    # Check time-based greetings first for specific responses
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
            # Check if it's Tamil text (contains Tamil specific patterns)
            if re.search(r'[\u0B80-\u0BFF]', text_lower) or any(t in text_lower for t in ['கேக்குதா', 'கேட்குதா', 'கேட்கிறதா']):
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
        
    # Check for generic Tamil text (if not caught by specific greetings)
    # Tamil Unicode range: \u0B80-\u0BFF
    if re.search(r'[\u0B80-\u0BFF]', text_lower):
        return 'tamil_generic'
    
    # Check other categories
    for category, patterns in GREETING_CATEGORIES.items():
        if category in ['time_based', 'cultural', 'phatic']:
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
