"""
Memory Intent Detector

Uses Gemini AI to detect when user wants to store permanent memory.
Language-agnostic: works in English, Tamil, Hindi, and any language.

CRITICAL RULES:
- Only detect EXPLICIT memory instructions
- Never trigger on casual mentions or questions
- Extract and normalize instructions
- Semantic detection, not keyword-based
"""

import os
import google.generativeai as genai
from dotenv import load_dotenv
from typing import Optional, Dict, Any
import json

load_dotenv()

# Detection prompt
MEMORY_DETECTION_PROMPT = """You are a memory intent detector for a conversational AI system.

Your ONLY job is to detect if the user is explicitly instructing the system to remember something permanently.

## Detection Rules

TRIGGER memory detection when user:
- Says "call me [name]" (even without "remember")
- Uses phrases like "from now on", "always", "address me as", "hereafter"
- Introduces themselves with "my name is [human name]", "I am [human name]"
- Gives permanent instructions about preferences or identity

Examples that MUST trigger:
- "Call me Boss" -> address_as: "Boss" (MOST COMMON PATTERN - just name!)
- "Call me madam" -> address_as: "madam"
- "Hereafter call me Boss" -> address_as: "Boss"
- "From now on call me boss" -> address_as: "boss"
- "You can call me Raj" -> address_as: "Raj"
- "Just call me sir" -> address_as: "sir"
- "Your name is Thara"
- "From now on, address me as sir"
- "My name is Boss" -> address_as: "Boss"
- "I am Priya" -> address_as: "Priya"
- "I'm John" -> address_as: "John"
- "என் பேரு Boss" (Tamil: "My name is Boss") -> address_as: "Boss"
- "Enna Boss nu koopdu" (Tamil: "Call me Boss") -> address_as: "Boss"
- "Inime enna madam nu dhan koopduva, nyabagam vechiko" (Tamil)
- "Yaad rakhna, mujhe sir bulana" (Hindi)
- "Mera naam Rahul hai" (Hindi: "My name is Rahul") -> address_as: "Rahul"

DO NOT trigger on (CRITICAL - these are NOT memory intents):
- DATE CONTEXT: "Today is November 14th", "Remember today is December", "The date is January 1st"
  -> These are providing temporal context for queries, NOT asking you to remember a name!
- Questions: "What is madam?"
- Casual mentions: "Tell me about Thara fruit"
- Temporary context: "For this query, use..."
- Polite requests without permanence: "Can you help me?"
- Time/date statements: Anything with dates, months, years, "today", "yesterday", "this month"

IMPORTANT: If the text contains date-related words (January, February, March, April, May, June, July, August, September, October, November, December, today, yesterday, tomorrow, date, month, year), it is NEVER a name introduction - it's a date context statement. Return has_memory_intent: false.

## Output Format

You must output ONLY valid JSON:

If memory intent detected:
{
  "has_memory_intent": true,
  "category": "user_preferences" | "bot_identity",
  "key": "address_as" | "name",
  "value": "extracted_value",
  "confidence": 0.0-1.0
}

If NO memory intent:
{
  "has_memory_intent": false
}

## Normalization Rules

- "Call me Boss" -> category: "user_preferences", key: "address_as", value: "Boss"
- "Call me madam" -> category: "user_preferences", key: "address_as", value: "madam"
- "Hereafter call me sir" -> category: "user_preferences", key: "address_as", value: "sir"
- "You can call me boss" -> category: "user_preferences", key: "address_as", value: "boss"
- "Your name is Thara" -> category: "bot_identity", key: "name", value: "Thara"
- "Address me as sir" -> category: "user_preferences", key: "address_as", value: "sir"
- "My name is Boss" -> category: "user_preferences", key: "address_as", value: "Boss"
- "I am Priya" -> category: "user_preferences", key: "address_as", value: "Priya"
- "I'm John" -> category: "user_preferences", key: "address_as", value: "John"
- "என் பேரு Boss" -> category: "user_preferences", key: "address_as", value: "Boss"
- "Enna Boss nu koopdu" -> category: "user_preferences", key: "address_as", value: "Boss"

Extract ONLY the name/value, not the full sentence. Preserve the original name (including Tamil/non-Latin names).

Output ONLY JSON. No explanations."""


def detect_memory_intent(question: str) -> Optional[Dict[str, Any]]:
    """
    Detect if user question contains memory storage intent.

    Args:
        question: User's question/statement

    Returns:
        Dict with detection result, or None if detection fails
        {
            "has_memory_intent": bool,
            "category": str,  # if has_memory_intent
            "key": str,       # if has_memory_intent
            "value": str,     # if has_memory_intent
            "confidence": float  # if has_memory_intent
        }
    """
    # QUICK PATTERN CHECK: Skip Gemini call for obvious data queries
    # This saves ~1 second for 95%+ of queries
    q_lower = question.lower()

    # Data query keywords - definitely NOT memory intents
    data_keywords = [
        'show', 'list', 'total', 'how many', 'what is', 'who worked',
        'sales', 'attendance', 'employee', 'average', 'sum', 'count',
        'highest', 'lowest', 'peak', 'maximum', 'minimum', 'compare',
        'trend', 'month', 'january', 'february', 'march', 'april', 'may',
        'june', 'july', 'august', 'september', 'october', 'november', 'december',
        'காட்டு', 'மொத்தம்', 'எத்தனை', 'யார்'  # Tamil: show, total, how many, who
    ]

    # Memory keywords - might be memory intents (need LLM to verify)
    memory_keywords = ['call me', 'my name', 'i am', "i'm", 'address me', 'from now on',
                       'என் பேரு', 'enna', 'koopdu']  # Tamil patterns

    # If query has data keywords and NO memory keywords, skip Gemini
    has_data_keyword = any(kw in q_lower for kw in data_keywords)
    has_memory_keyword = any(kw in q_lower for kw in memory_keywords)

    if has_data_keyword and not has_memory_keyword:
        return {"has_memory_intent": False}

    # Short queries without memory patterns - skip
    if len(question) < 15 and not has_memory_keyword:
        return {"has_memory_intent": False}

    try:
        # Get API key (strip whitespace from HF Spaces)
        api_key = (os.getenv("GEMINI_API_KEY") or "").strip()
        if not api_key:
            print("Warning: GEMINI_API_KEY not found, memory detection disabled")
            return {"has_memory_intent": False}
        
        # Configure Gemini
        genai.configure(api_key=api_key)

        # Create model with JSON output (no system_instruction for compatibility with 0.3.x)
        model = genai.GenerativeModel(
            model_name="gemini-2.0-flash",  # Fast model for detection
            generation_config={
                "temperature": 0.0,
                "response_mime_type": "application/json"
            },
        )

        # Build prompt with system instruction prepended (for compatibility)
        full_prompt = f"{MEMORY_DETECTION_PROMPT}\n\n---\n\nUser input: {question}\n\nDetect memory intent and output JSON:"

        # Call API
        response = model.generate_content(full_prompt)
        
        # Parse JSON response
        result = json.loads(response.text)
        
        # Validate structure
        if not isinstance(result, dict):
            return {"has_memory_intent": False}
        
        if not result.get("has_memory_intent", False):
            return {"has_memory_intent": False}
        
        # Validate required fields for positive detection
        required_fields = ["category", "key", "value"]
        if not all(field in result for field in required_fields):
            print(f"Warning: Incomplete memory detection result: {result}")
            return {"has_memory_intent": False}
        
        # Validate category
        if result["category"] not in ["user_preferences", "bot_identity"]:
            print(f"Warning: Invalid category: {result['category']}")
            return {"has_memory_intent": False}
        
        return result
        
    except json.JSONDecodeError as e:
        print(f"Warning: Failed to parse memory detection JSON: {e}")
        return {"has_memory_intent": False}
    except Exception as e:
        print(f"Warning: Memory detection failed: {e}")
        return {"has_memory_intent": False}


def extract_memory_instruction(question: str) -> Optional[Dict[str, str]]:
    """
    Extract and normalize memory instruction from user question.
    
    This is a convenience wrapper around detect_memory_intent.
    
    Args:
        question: User's question/statement
        
    Returns:
        Dict with normalized instruction, or None if no memory intent
        {
            "category": "user_preferences" | "bot_identity",
            "key": "address_as" | "name",
            "value": "extracted_value"
        }
    """
    result = detect_memory_intent(question)
    
    if not result or not result.get("has_memory_intent"):
        return None
    
    return {
        "category": result["category"],
        "key": result["key"],
        "value": result["value"]
    }
