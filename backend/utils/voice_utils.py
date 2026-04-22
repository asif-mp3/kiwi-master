"""
Voice utilities — TTS and STT provider abstraction.

Active provider: ElevenLabs
Murf AI code is preserved below but commented out.

To switch providers, update get_tts_provider() and get_stt_provider().
"""

import os
import re
import time
import requests
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Iterator
from dotenv import load_dotenv
from utils.logger import get_logger
from utils.tts_cache import get_cached_tts_audio, cache_tts_audio

load_dotenv()
logger = get_logger("voice_utils")


# ============================================
# VOICE CONFIGURATION
# ============================================

def get_voice_config() -> dict:
    """Load voice configuration from settings.yaml."""
    import yaml
    config_path = Path(__file__).parent.parent / "config" / "settings.yaml"
    with open(config_path) as f:
        cfg = yaml.safe_load(f)
    return cfg.get("voice", {})


def get_default_voice_id() -> str:
    return get_voice_config().get("default_voice_id", "pNInz6obpgDQGcFmaJgB")


# ============================================
# TTS PROVIDER ABSTRACTION
# ============================================

class TTSProvider(ABC):
    @abstractmethod
    def generate_speech(self, text: str, voice_id: str) -> bytes:
        """Return MP3 audio bytes for the given text."""

    def generate_speech_stream(self, text: str, voice_id: str) -> Iterator[bytes]:
        """Yield MP3 chunks. Default: single chunk from generate_speech."""
        yield self.generate_speech(text, voice_id)


class STTProvider(ABC):
    @abstractmethod
    def transcribe(self, audio_file_path: str, language: Optional[str] = None) -> str:
        """Transcribe audio file to text."""


# ============================================
# ELEVENLABS PROVIDER (active)
# ============================================

class ElevenLabsTTSProvider(TTSProvider):
    """ElevenLabs TTS."""

    def __init__(self, api_key: str):
        from elevenlabs.client import ElevenLabs
        self._client = ElevenLabs(api_key=api_key)

    def generate_speech(self, text: str, voice_id: str) -> bytes:
        start = time.time()
        model_id = "eleven_flash_v2_5"
        audio_stream = self._client.text_to_speech.convert(
            voice_id=voice_id,
            text=text,
            model_id=model_id,
            output_format="mp3_44100_128",
        )
        audio_bytes = b"".join(chunk for chunk in audio_stream if chunk)
        elapsed = int((time.time() - start) * 1000)
        logger.info("ElevenLabs TTS: %d bytes [%dms]", len(audio_bytes), elapsed)
        return audio_bytes

    def generate_speech_stream(self, text: str, voice_id: str) -> Iterator[bytes]:
        model_id = "eleven_flash_v2_5"
        audio_stream = self._client.text_to_speech.convert(
            voice_id=voice_id,
            text=text,
            model_id=model_id,
            output_format="mp3_44100_128",
        )
        for chunk in audio_stream:
            if chunk:
                yield chunk


class ElevenLabsSTTProvider(STTProvider):
    """ElevenLabs STT (Scribe v2)."""

    def __init__(self, api_key: str):
        from elevenlabs.client import ElevenLabs
        self._client = ElevenLabs(api_key=api_key)

    def transcribe(self, audio_file_path: str, language: Optional[str] = None) -> str:
        with open(audio_file_path, 'rb') as f:
            kwargs = {"file": f, "model_id": "scribe_v1"}
            if language:
                kwargs["language_code"] = language
            result = self._client.speech_to_text.convert(**kwargs)
        return result.text if hasattr(result, 'text') else str(result)


# ============================================
# MURF AI PROVIDER (DISABLED — kept for reference)
# ============================================

# class MurfTTSProvider(TTSProvider):
#     API_URL = "https://api.murf.ai/v1/speech/generate"
#
#     def __init__(self, api_key: str):
#         self._api_key = api_key
#
#     def generate_speech(self, text: str, voice_id: str) -> bytes:
#         payload = {
#             "voiceId": voice_id, "text": text, "style": "Conversational",
#             "modelVersion": "GEN2", "format": "MP3", "encodeAsBase64": False,
#         }
#         resp = requests.post(self.API_URL, json=payload,
#             headers={"api-key": self._api_key, "Content-Type": "application/json"},
#             timeout=get_voice_config().get("request_timeout_seconds", 10))
#         if not resp.ok:
#             raise RuntimeError(f"Murf TTS error {resp.status_code}: {resp.text[:200]}")
#         audio_url = resp.json().get("audioFile")
#         return requests.get(audio_url, timeout=15).content


# ============================================
# PROVIDER FACTORY
# ============================================

_tts_provider: Optional[TTSProvider] = None
_stt_provider: Optional[STTProvider] = None


def get_tts_provider() -> TTSProvider:
    global _tts_provider
    if _tts_provider is not None:
        return _tts_provider
    el_key = os.getenv("ELEVENLABS_API_KEY", "").strip()
    if el_key:
        _tts_provider = ElevenLabsTTSProvider(el_key)
        logger.info("TTS provider: ElevenLabs")
        return _tts_provider
    raise RuntimeError("No TTS provider configured. Set ELEVENLABS_API_KEY in .env")


def get_stt_provider() -> STTProvider:
    global _stt_provider
    if _stt_provider is not None:
        return _stt_provider
    el_key = os.getenv("ELEVENLABS_API_KEY", "").strip()
    if el_key:
        _stt_provider = ElevenLabsSTTProvider(el_key)
        return _stt_provider
    raise RuntimeError("STT not configured. Set ELEVENLABS_API_KEY in .env")


# ============================================
# TEXT PREPROCESSING
# ============================================

def _preprocess_for_tts(text: str) -> str:
    text = re.sub(r'\bThara\b', 'Tara', text, flags=re.IGNORECASE)
    return text


def _get_voice_id_for_text(text: str, requested_voice_id: Optional[str]) -> str:
    """Pick voice ID based on text language and config."""
    if requested_voice_id:
        return requested_voice_id
    config = get_voice_config()
    tamil_pattern = re.compile(r'[\u0B80-\u0BFF]')
    has_tamil = bool(tamil_pattern.search(text))
    return config.get("tamil_voice_id", config.get("default_voice_id", "en-US-marcus")) if has_tamil \
        else config.get("default_voice_id", "en-US-marcus")


# ============================================
# PUBLIC API (unchanged contract for main.py)
# ============================================

def text_to_speech(text: str, voice_id: Optional[str] = None) -> bytes:
    """
    Convert text to speech. Returns MP3 bytes.
    Checks cache first for instant repeated playback.
    """
    start = time.time()
    processed = _preprocess_for_tts(text)
    voice_id = _get_voice_id_for_text(processed, voice_id)

    hit, cached = get_cached_tts_audio(processed, voice_id)
    if hit and cached:
        logger.info("TTS CACHE HIT: %d bytes [%dms]", len(cached), int((time.time() - start) * 1000))
        return cached

    provider = get_tts_provider()
    audio = provider.generate_speech(processed, voice_id)
    cache_tts_audio(processed, voice_id, audio)
    logger.info("TTS: %d bytes [%dms]", len(audio), int((time.time() - start) * 1000))
    return audio


def text_to_speech_streaming(text: str, voice_id: Optional[str] = None) -> Iterator[bytes]:
    """
    Stream TTS audio chunks. Checks cache first.
    """
    start = time.time()
    processed = _preprocess_for_tts(text)
    voice_id = _get_voice_id_for_text(processed, voice_id)

    hit, cached = get_cached_tts_audio(processed, voice_id)
    if hit and cached:
        logger.info("TTS STREAM CACHE HIT: %d bytes [%dms]", len(cached), int((time.time() - start) * 1000))
        chunk_size = 8192
        for i in range(0, len(cached), chunk_size):
            yield cached[i:i + chunk_size]
        return

    provider = get_tts_provider()
    all_chunks = []
    first_chunk_logged = False
    for chunk in provider.generate_speech_stream(processed, voice_id):
        if chunk:
            if not first_chunk_logged:
                logger.info("TTS STREAM: First chunk [%dms]", int((time.time() - start) * 1000))
                first_chunk_logged = True
            all_chunks.append(chunk)
            yield chunk

    if all_chunks:
        complete = b"".join(all_chunks)
        cache_tts_audio(processed, voice_id, complete)
        logger.info("TTS STREAM: Complete %d bytes [%dms]", len(complete), int((time.time() - start) * 1000))


def transcribe_audio(audio_file_path: str, language: Optional[str] = None) -> str:
    """
    Transcribe audio to text.
    Currently raises RuntimeError — configure a STT provider first.
    """
    provider = get_stt_provider()  # raises RuntimeError if none configured
    return provider.transcribe(audio_file_path, language)
