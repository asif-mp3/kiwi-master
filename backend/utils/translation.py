"""
Translation utilities using Gemini Flash for Tamil <-> English translation.
"""

import os
import time
import google.generativeai as genai
from typing import Optional

# Configure Gemini - try both env var names for compatibility (strip whitespace from HF Spaces)
api_key = (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or "").strip()
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

CRITICAL RULES:
1. **Business terminology** (DO NOT confuse these!):
   - "சேல்ஸ்" / "விற்பனை" = "sales" (NOT "rails", "seals", or "cells")
   - "லாபம்" / "ப்ராபிட்" = "profit"
   - "வருமானம்" / "ரெவின்யூ" = "revenue"
   - Double-check: If user says "சேல்ஸ்", output MUST be "sales"

2. **Comparison queries** (preserve comparison structure!):
   - "X-ல அதிகமா இருக்கா இல்ல Y-ல அதிகமா இருக்கா" = "Is it higher in X or higher in Y"
   - "X-விட Y எவ்ளோ" = "How much is Y compared to X" or "Compare X vs Y"
   - "எது அதிகம்" / "எது சிறந்தது" = "which is higher" / "which is better"
   - Keep comparison structure intact (don't lose the "or" / "vs" / "compared to")

3. **Months** - Map to English names:
   - 'டிசம்பர்' -> 'December', 'ஜனவரி' -> 'January', etc.
   - Do NOT add specific dates (like '25') unless explicitly in the text

4. **Location hierarchy context**:
   - If asking "in [State X], which state/மாநிலம்..." -> translate as "which branch/district in [State X]..."
   - Because you cannot have a state inside another state, so the user means sub-units
   - Example: "தமிழ்நாட்டில் எந்த மாநிலம்" -> "which branch in Tamil Nadu"

5. **Prepositions** like "இல்" (in) attached to a location = FILTER:
   - "தமிழ்நாட்டில்" (in Tamil Nadu) = filter by Tamil Nadu
   - "சென்னையில்" (in Chennai) = filter by Chennai

EXAMPLES:
- "சென்னையில சேல்ஸ் அதிகமா இருக்கா இல்ல பெங்களூருல சேல்ஸ் அதிகமா இருக்கா?"
  → "Is sales higher in Chennai or is sales higher in Bangalore?"

- "பெங்களூருவிட சென்னை எவ்ளோ நல்லா போயிட்டுருக்கு சேல்ஸு?"
  → "How much better is Chennai sales compared to Bangalore?" or "Compare Chennai vs Bangalore sales"

- "டிசம்பரில சென்னையில எவ்வளவு சேல்ஸ்?"
  → "How much sales in Chennai in December?"

Output ONLY the English translation, no explanations.

Text: {text}"""
        )
        english_text = response.text.strip()
        elapsed = (time.time() - start) * 1000
        print(f"[TRANSLATE] Translation (Tamil -> English): {text} -> {english_text} [{elapsed:.0f}ms]")
        return english_text
    except Exception as e:
        print(f"[NO] Translation Error (to English): {e}")
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
        print(f"[TRANSLATE] Translation (English -> Tamil): {text} -> {tamil_text} [{elapsed:.0f}ms]")
        return tamil_text
    except Exception as e:
        print(f"[NO] Translation Error (to Tamil): {e}")
        return text  # Fallback to original
