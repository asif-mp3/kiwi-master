"""
Language detection helper — script-range based for fast, deterministic detection.
"""
import re

TAMIL_RANGE = re.compile(r'[\u0B80-\u0BFF]')
HINDI_RANGE = re.compile(r'[\u0900-\u097F]')


def detect_language(text: str) -> str:
    """Return 'ta' (Tamil), 'hi' (Hindi/Devanagari), or 'en' (default)."""
    if not text:
        return 'en'
    if TAMIL_RANGE.search(text):
        return 'ta'
    if HINDI_RANGE.search(text):
        return 'hi'
    return 'en'


def has_tamil(text: str) -> bool:
    return bool(TAMIL_RANGE.search(text or ''))


def has_hindi(text: str) -> bool:
    return bool(HINDI_RANGE.search(text or ''))


def has_non_latin(text: str) -> bool:
    """True if text contains Tamil or Hindi script."""
    return has_tamil(text) or has_hindi(text)
