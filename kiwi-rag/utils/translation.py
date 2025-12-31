
import os
import google.generativeai as genai
from typing import Optional

# Configure Gemini
api_key = os.getenv("GOOGLE_API_KEY")
if api_key:
    genai.configure(api_key=api_key)

model = genai.GenerativeModel('gemini-1.5-flash')

def translate_to_english(text: str) -> str:
    """
    Translates Tamil text to English for RAG processing.
    """
    try:
        response = model.generate_content(
            f"Translate the following Tamil query to English strictly for data analysis. Map months to their English names (e.g., 'டிசம்பர்' -> 'December'). Do not add specific dates (like '25') unless explicitly lying in the text. Output ONLY the English translation.\n\nText: {text}"
        )
        english_text = response.text.strip()
        print(f"🔄 Translation (Tamil -> English): {text} -> {english_text}")
        return english_text
    except Exception as e:
        print(f"❌ Translation Error (to English): {e}")
        return text  # Fallback to original

def translate_to_tamil(text: str) -> str:
    """
    Translates English answer to Tamil for user response.
    """
    try:
        response = model.generate_content(
            f"Translate to Tamil. STRICT RULE: Convert ALL numbers to Tamil words (e.g. 6450 -> ஆறாயிரத்து நானூற்று ஐம்பது). NO DIGITS ALLOWED.\n\nText: {text}"
        )
        tamil_text = response.text.strip()
        print(f"🔄 Translation (English -> Tamil): {text} -> {tamil_text}")
        return tamil_text
    except Exception as e:
        print(f"❌ Translation Error (to Tamil): {e}")
        return text  # Fallback to original
