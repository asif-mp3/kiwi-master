"""
Translation utilities using Gemini Flash for Tamil <-> English translation.
"""

import os
import time
import google.generativeai as genai
from typing import Optional

# Configure Gemini - try both env var names for compatibility
api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
if api_key:
    genai.configure(api_key=api_key)

model = genai.GenerativeModel('gemini-2.0-flash')  # Fast model for low-latency translation


def translate_to_english(text: str) -> str:
    """
    Translates Tamil text to English for RAG processing.
    """
    try:
        start = time.time()
        response = model.generate_content(
            f"""Translate the following Tamil query to English strictly for data analysis.

RULES:
1. Map months to their English names (e.g., 'டிசம்பர்' -> 'December')
2. Do not add specific dates (like '25') unless explicitly in the text
3. IMPORTANT - Location hierarchy context:
   - If asking "in [State X], which state/மாநிலம்..." → translate as "which branch/district in [State X]..."
   - Because you cannot have a state inside another state, so the user means sub-units (branch/district)
   - Example: "தமிழ்நாட்டில் எந்த மாநிலம்" should become "which branch in Tamil Nadu" NOT "which state in Tamil Nadu"
   - Similarly: "கர்நாடகாவில் எந்த மாநிலம்" → "which branch/district in Karnataka"
4. Prepositions like "இல்" (in) attached to a location name indicate a FILTER, not a target
   - "தமிழ்நாட்டில்" (in Tamil Nadu) = filter by Tamil Nadu
   - "சென்னையில்" (in Chennai) = filter by Chennai

Output ONLY the English translation, no explanations.

Text: {text}"""
        )
        english_text = response.text.strip()
        elapsed = (time.time() - start) * 1000
        print(f"🔄 Translation (Tamil -> English): {text} -> {english_text} [{elapsed:.0f}ms]")
        return english_text
    except Exception as e:
        print(f"❌ Translation Error (to English): {e}")
        return text  # Fallback to original


def translate_to_tamil(text: str) -> str:
    """
    Translates English answer to Tamil for user response.
    """
    try:
        start = time.time()
        response = model.generate_content(
            f"Translate to Tamil. STRICT RULE: Convert ALL numbers to Tamil words (e.g. 6450 -> ஆறாயிரத்து நானூற்று ஐம்பது). NO DIGITS ALLOWED.\n\nText: {text}"
        )
        tamil_text = response.text.strip()
        elapsed = (time.time() - start) * 1000
        print(f"🔄 Translation (English -> Tamil): {text} -> {tamil_text} [{elapsed:.0f}ms]")
        return tamil_text
    except Exception as e:
        print(f"❌ Translation Error (to Tamil): {e}")
        return text  # Fallback to original
