"""
Translation utilities using Gemini Flash for Tamil <-> English translation.
"""

import time
from google.genai import types
from typing import Optional
from utils.logger import get_logger
from utils.config_loader import get_llm_config, get_genai_client

logger = get_logger("translation")


def translate_to_english(text: str) -> str:
    """
    Translates Tamil text to English for RAG processing.
    """
    try:
        start = time.time()
        client = get_genai_client()
        response = client.models.generate_content(
            model=get_llm_config().model,
            contents=f"""Translate the following Tamil query to English strictly for data analysis.

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
        logger.info("Translation (Tamil -> English): %s -> %s [%dms]", text, english_text, elapsed)
        return english_text
    except Exception as e:
        logger.error("Translation Error (to English): %s", e)
        return text  # Fallback to original


def translate_to_tamil(text: str) -> str:
    """
    Translates English answer to Tamil for user response.
    """
    try:
        start = time.time()
        client = get_genai_client()
        response = client.models.generate_content(
            model=get_llm_config().model,
            contents=f"Translate to Tamil. STRICT RULE: Convert ALL numbers to Tamil words (e.g. 6450 -> ஆறாயிரத்து நானூற்று ஐம்பது). NO DIGITS ALLOWED.\n\nText: {text}",
        )
        tamil_text = response.text.strip()
        elapsed = (time.time() - start) * 1000
        logger.info("Translation (English -> Tamil): %s -> %s [%dms]", text, tamil_text, elapsed)
        return tamil_text
    except Exception as e:
        logger.error("Translation Error (to Tamil): %s", e)
        return text  # Fallback to original
