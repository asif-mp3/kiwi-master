"""
Gemini HTTP Client — direct REST API calls, no SDK.

Replaces the google-genai SDK to avoid GOOGLE_API_KEY auto-detection conflicts.
Uses GEMINI_API_KEY exclusively.
"""

import os
import time
import requests
from utils.logger import get_logger

logger = get_logger("gemini_client")

_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"


def _get_api_key() -> str:
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if not key:
        raise ValueError("GEMINI_API_KEY not set in environment")
    return key


def generate_content(
    model: str,
    contents: "str | list",
    system_instruction: str = None,
    temperature: float = 0.7,
    max_output_tokens: int = 600,
    response_mime_type: str = None,
    timeout: int = 60,
) -> str:
    """
    Call Gemini REST API and return the response text.

    Args:
        model: Model name, e.g. 'gemini-2.5-flash'
        contents: User prompt (str) or full contents list
        system_instruction: Optional system prompt
        temperature: Generation temperature
        max_output_tokens: Max tokens in response
        response_mime_type: E.g. 'application/json' to force JSON output
        timeout: HTTP request timeout in seconds

    Returns:
        Response text string
    """
    api_key = _get_api_key()
    url = f"{_BASE_URL}/{model}:generateContent"

    # Build contents list
    if isinstance(contents, str):
        contents_list = [{"role": "user", "parts": [{"text": contents}]}]
    else:
        contents_list = contents

    body: dict = {"contents": contents_list}

    if system_instruction:
        body["system_instruction"] = {"parts": [{"text": system_instruction}]}

    gen_config: dict = {
        "temperature": temperature,
        "maxOutputTokens": max_output_tokens,
        # Disable thinking mode — prevents tokens being consumed by internal CoT
        # before any actual response is generated (critical for gemini-2.5-flash)
        "thinkingConfig": {"thinkingBudget": 0},
    }
    if response_mime_type:
        gen_config["responseMimeType"] = response_mime_type
    body["generationConfig"] = gen_config

    start = time.time()
    resp = requests.post(
        url,
        params={"key": api_key},
        json=body,
        timeout=timeout,
    )

    if not resp.ok:
        raise RuntimeError(
            f"Gemini API error {resp.status_code}: {resp.text[:300]}"
        )

    data = resp.json()
    elapsed = int((time.time() - start) * 1000)
    logger.debug("Gemini %s responded in %dms", model, elapsed)

    try:
        candidate = data["candidates"][0]
        finish_reason = candidate.get("finishReason", "")
        parts = candidate.get("content", {}).get("parts", [])
        if not parts:
            if finish_reason == "MAX_TOKENS":
                raise RuntimeError(
                    f"Gemini used all {max_output_tokens} tokens before producing output "
                    f"(thinking consumed them). Increase max_output_tokens."
                )
            raise RuntimeError(f"Gemini returned empty response. finishReason={finish_reason}")
        return parts[0]["text"]
    except (KeyError, IndexError) as e:
        raise RuntimeError(f"Unexpected Gemini response structure: {data}") from e


def generate_content_stream(
    model: str,
    contents: "str | list",
    system_instruction: str = None,
    temperature: float = 0.7,
    max_output_tokens: int = 600,
    timeout: int = 60,
):
    """
    Call Gemini REST API and yield text tokens via SSE.
    """
    import json
    api_key = _get_api_key()
    url = f"{_BASE_URL}/{model}:streamGenerateContent?alt=sse&key={api_key}"

    if isinstance(contents, str):
        contents_list = [{"role": "user", "parts": [{"text": contents}]}]
    else:
        contents_list = contents

    body: dict = {"contents": contents_list}
    if system_instruction:
        body["system_instruction"] = {"parts": [{"text": system_instruction}]}

    body["generationConfig"] = {
        "temperature": temperature,
        "maxOutputTokens": max_output_tokens,
        "thinkingConfig": {"thinkingBudget": 0},
    }

    start = time.time()
    resp = requests.post(url, json=body, timeout=timeout, stream=True)

    if not resp.ok:
        raise RuntimeError(f"Gemini streaming error {resp.status_code}: {resp.text[:300]}")

    elapsed = int((time.time() - start) * 1000)
    logger.debug("Gemini %s stream connected in %dms", model, elapsed)

    for line in resp.iter_lines():
        if line:
            decoded_line = line.decode('utf-8')
            if decoded_line.startswith('data: '):
                data_str = decoded_line[6:]
                if data_str.strip() == '[DONE]':
                    break
                try:
                    data = json.loads(data_str)
                    candidate = data["candidates"][0]
                    parts = candidate.get("content", {}).get("parts", [])
                    if parts and "text" in parts[0]:
                        yield parts[0]["text"]
                except Exception:
                    pass
