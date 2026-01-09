"""
Voice utilities for ElevenLabs integration.
Provides speech-to-text and text-to-speech functionality.
"""

import os
import yaml
from elevenlabs.client import ElevenLabs
import tempfile
from pathlib import Path
from dotenv import load_dotenv
from typing import Optional

# Load environment variables
load_dotenv()

# Get API key from environment
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")

# ============================================
# VOICE CONFIGURATION LOADER
# ============================================
_voice_config_cache = None


def get_voice_config() -> dict:
    """
    Load voice configuration from settings.yaml with caching.

    Returns:
        dict with keys: default_voice_id, tamil_voice_id, request_timeout_seconds
    """
    global _voice_config_cache
    if _voice_config_cache is not None:
        return _voice_config_cache

    config_path = Path("config/settings.yaml")
    if config_path.exists():
        with open(config_path) as f:
            config = yaml.safe_load(f)
        voice_config = config.get("voice", {})

        # Validate required voice config fields
        if not voice_config.get("default_voice_id"):
            raise ValueError(
                "Missing 'voice.default_voice_id' in config/settings.yaml. "
                "Please configure an ElevenLabs voice ID."
            )
        if not voice_config.get("tamil_voice_id"):
            # Fall back to default voice if Tamil not configured
            voice_config["tamil_voice_id"] = voice_config["default_voice_id"]
            print("⚠️ voice.tamil_voice_id not configured, using default_voice_id")

        _voice_config_cache = voice_config
    else:
        raise FileNotFoundError(
            "Voice config not found: config/settings.yaml does not exist. "
            "Please create it with voice.default_voice_id and voice.tamil_voice_id."
        )

    return _voice_config_cache


def get_default_voice_id() -> str:
    """Get the default voice ID from config."""
    voice_config = get_voice_config()
    # No fallback - config validation ensures this exists
    return voice_config["default_voice_id"]

def transcribe_audio(audio_file_path: str, language: Optional[str] = None) -> str:
    """
    Transcribe audio file to text using ElevenLabs Scribe v2.
    Latest and most accurate model for transcription.

    Args:
        audio_file_path: Path to audio file
        language: Language code (e.g., 'en', 'ta'). If None, uses auto-detection.

    Returns:
        Transcribed text
    """
    import time
    _start = time.time()

    try:
        client = ElevenLabs(api_key=ELEVENLABS_API_KEY)

        # Get language from config if not specified
        if language is None:
            voice_config = get_voice_config()
            language = voice_config.get("stt_language")  # None means auto-detect

        if language:
            print(f"🎤 STT: Using Scribe v2 with language={language}")
        else:
            print(f"🎤 STT: Using Scribe v2 with auto language detection")

        # Use Scribe v2 - latest available model
        with open(audio_file_path, 'rb') as audio_file:
            # Build kwargs - only include language_code if specified
            stt_kwargs = {
                "file": audio_file,
                "model_id": "scribe_v2"
            }
            if language:
                stt_kwargs["language_code"] = language

            result = client.speech_to_text.convert(**stt_kwargs)

        # Extract text from result
        if hasattr(result, 'text'):
            transcribed_text = result.text
        elif isinstance(result, dict):
            transcribed_text = result.get('text', str(result))
        else:
            transcribed_text = str(result)

        elapsed = (time.time() - _start) * 1000
        print(f"✅ STT: Transcribed [{elapsed:.0f}ms]: \"{transcribed_text}\"")
        return transcribed_text

    except Exception as e:
        elapsed = (time.time() - _start) * 1000
        error_msg = f"Transcription failed: {str(e)}"
        print(f"❌ STT Error: {error_msg} [{elapsed:.0f}ms]")
        raise Exception(error_msg)

def _preprocess_for_tts(text: str) -> str:
    """
    Preprocess text for better TTS pronunciation.

    Fixes common pronunciation issues:
    - "Thara" -> "Tara" (prevents "Thaaraa" pronunciation)
    - Tamil "தாரா" kept as-is (multilingual model handles it)
    """
    import re

    # Fix English "Thara" pronunciation (ElevenLabs says "Thaaraa")
    # Replace with "Tara" which sounds closer to intended pronunciation
    text = re.sub(r'\bThara\b', 'Tara', text, flags=re.IGNORECASE)

    return text


def text_to_speech(text: str, voice_id: Optional[str] = None) -> bytes:
    """
    Convert text to speech using ElevenLabs with user's preferred voice.
    Uses Turbo v2.5 for fastest, lowest-latency playback.
    Supports Tamil and English.
    CACHES audio for instant replay.

    Args:
        text: Text to convert to speech
        voice_id: ElevenLabs voice ID. If None, uses config default.

    Returns:
        Audio bytes (MP3 format)
    """
    import time
    start_time = time.time()

    try:
        from elevenlabs.client import ElevenLabs
        import re
        from utils.tts_cache import get_cached_tts_audio, cache_tts_audio

        # Preprocess text for better pronunciation
        processed_text = _preprocess_for_tts(text)

        # Detect if text contains Tamil characters
        tamil_pattern = re.compile(r'[\u0B80-\u0BFF]')
        has_tamil = bool(tamil_pattern.search(processed_text))

        # Get voice ID from config if not provided
        voice_config = get_voice_config()
        if voice_id is None:
            if has_tamil:
                voice_id = voice_config["tamil_voice_id"]
            else:
                voice_id = voice_config["default_voice_id"]

        # CHECK CACHE FIRST - instant playback for repeated audio
        hit, cached_audio = get_cached_tts_audio(processed_text, voice_id)
        if hit and cached_audio:
            elapsed = (time.time() - start_time) * 1000
            print(f"⚡ TTS CACHE HIT: {len(cached_audio)} bytes [{elapsed:.0f}ms]")
            return cached_audio

        print(f"🔊 TTS: Using voice ID {voice_id}")

        # Initialize ElevenLabs client
        client = ElevenLabs(api_key=ELEVENLABS_API_KEY)

        # Select model based on language for best balance of speed vs accuracy
        if has_tamil:
            model_id = "eleven_multilingual_v2"
            print("🔊 TTS: Detected Tamil text - Multilingual v2")
        else:
            model_id = "eleven_turbo_v2_5"
            print("🔊 TTS: English text - Turbo v2.5 (fastest)")

        # Generate audio - use standard MP3 format for browser compatibility
        audio_stream = client.text_to_speech.convert(
            voice_id=voice_id,
            text=processed_text,
            model_id=model_id,
            output_format="mp3_44100_128",
        )

        # Collect audio chunks
        audio_bytes = b""
        for chunk in audio_stream:
            if chunk:
                audio_bytes += chunk

        # CACHE for future instant playback
        cache_tts_audio(processed_text, voice_id, audio_bytes)

        elapsed = (time.time() - start_time) * 1000
        print(f"✅ TTS: Generated {len(audio_bytes)} bytes [{elapsed:.0f}ms]")
        return audio_bytes

    except Exception as e:
        error_msg = f"ElevenLabs TTS failed: {str(e)}"
        print(f"❌ TTS Error: {error_msg}")
        raise Exception(error_msg)


def save_audio_temp(audio_bytes: bytes) -> str:
    """
    Save audio bytes to a temporary file.
    
    Args:
        audio_bytes: Audio data
        
    Returns:
        Path to temporary audio file
    """
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
    temp_file.write(audio_bytes)
    temp_file.close()
    return temp_file.name
