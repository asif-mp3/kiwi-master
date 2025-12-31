"""
Voice utilities for ElevenLabs integration.
Provides speech-to-text and text-to-speech functionality.
"""

import os
from elevenlabs.client import ElevenLabs
import tempfile
from pathlib import Path
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Get API key from environment
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")

def transcribe_audio(audio_file_path: str) -> str:
    """
    Transcribe audio file to text using ElevenLabs Scribe v2.
    Latest and most accurate model for transcription.
    
    Args:
        audio_file_path: Path to audio file
        
    Returns:
        Transcribed text
    """
    try:
        client = ElevenLabs(api_key=ELEVENLABS_API_KEY)
        
        print(f"🎤 STT: Using Scribe v2 model for accurate transcription...")
        
        # Use Scribe v2 - latest available model
        with open(audio_file_path, 'rb') as audio_file:
            result = client.speech_to_text.convert(
                file=audio_file,
                model_id="scribe_v2",  # Latest available model
                language_code="en"  # English
            )
        
        # Extract text from result
        if hasattr(result, 'text'):
            transcribed_text = result.text
        elif isinstance(result, dict):
            transcribed_text = result.get('text', str(result))
        else:
            transcribed_text = str(result)
        
        print(f"✅ STT: Transcribed {len(transcribed_text)} characters")
        return transcribed_text
            
    except Exception as e:
        error_msg = f"Transcription failed: {str(e)}"
        print(f"❌ STT Error: {error_msg}")
        raise Exception(error_msg)

def text_to_speech(text: str, voice_id: str = "AoUGsFgc3Skx8oW3rd42") -> bytes:
    """
    Convert text to speech using ElevenLabs with user's preferred voice.
    Uses Turbo v2.5 for fastest, lowest-latency playback.
    Supports Tamil and English.
    
    Args:
        text: Text to convert to speech
        voice_id: ElevenLabs voice ID (default: OUBMjq0LvBjb07bhwD3H - User's preferred voice)
        
    Returns:
        Audio bytes (MP3 format)
    """
    try:
        from elevenlabs.client import ElevenLabs
        import re
        
        # Initialize ElevenLabs client
        client = ElevenLabs(api_key=ELEVENLABS_API_KEY)
        
        # Detect if text contains Tamil characters
        tamil_pattern = re.compile(r'[\u0B80-\u0BFF]')
        has_tamil = bool(tamil_pattern.search(text))
        
        print(f"🔊 TTS: Using voice ID {voice_id}")
        
        # Select model based on language for best balance of speed vs accuracy
        if has_tamil:
            # Multilingual v2 is significantly better at Tamil pronunciation than Turbo
            model_id = "eleven_multilingual_v2"
            print("🔊 TTS: Detected Tamil text - Switching to High-Accuracy Model (Multilingual v2)")
        else:
            # Turbo v2.5 is fastest for English
            model_id = "eleven_turbo_v2_5" 
            print("🔊 TTS: English text - Using Low-Latency Model (Turbo v2.5)")
        
        # Generate audio
        audio_stream = client.text_to_speech.convert(
            voice_id=voice_id,
            text=text,
            model_id=model_id,
            output_format="mp3_44100_128", 
        )
        
        # Collect audio chunks
        audio_bytes = b""
        for chunk in audio_stream:
            if chunk:
                audio_bytes += chunk
        
        print(f"✅ TTS: Generated {len(audio_bytes)} bytes")
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
