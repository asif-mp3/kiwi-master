"""
Voice router - Transport layer for audio processing.

Proxies requests to ElevenLabs AI services.
Current Config:
- TTS: ElevenLabs (eleven_multilingual_v2)
- STT: ElevenLabs Scribe (scribe_v1)
"""

from fastapi import APIRouter, Form, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
import os
import shutil
import tempfile
from elevenlabs.client import ElevenLabs

router = APIRouter()

def get_elevenlabs_client():
    api_key = os.getenv("ELEVENLABS_API_KEY")
    if not api_key:
        print("❌ ELEVENLABS_API_KEY is missing in env")
        raise HTTPException(status_code=500, detail="ELEVENLABS_API_KEY not configured")
    
    # Log disguised key for debugging
    masked_key = f"{api_key[:4]}...{api_key[-4:]}" if len(api_key) > 8 else "***"
    print(f"✅ Using ElevenLabs API Key: {masked_key}")
    
    return ElevenLabs(api_key=api_key)

@router.post("/transcribe")
async def transcribe_audio(audio: UploadFile = File(...)):
    """
    Transcribe audio file to text using ElevenLabs Scribe.
    """
    client = get_elevenlabs_client()
    
    # Save temp file
    # Scribe likely needs a file path or file-like object with a name
    suffix = os.path.splitext(audio.filename)[1] if audio.filename else ".webm"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_audio:
        shutil.copyfileobj(audio.file, temp_audio)
        temp_path = temp_audio.name

    try:
        # Open the file and send to ElevenLabs Scribe
        with open(temp_path, "rb") as audio_file:
            transcription = client.speech_to_text.convert(
                file=audio_file,
                model_id="scribe_v1"
            )
        
        return {
            "success": True,
            "text": transcription.text,
            "language": transcription.language_code or "en"
        }
    except Exception as e:
        print(f"STT Error: {e}")
        return {
            "success": False,
            "message": str(e), # Frontend expects 'message' for error toast
            "error": str(e),
            "text": ""
        }
    finally:
        # Cleanup
        if os.path.exists(temp_path):
            os.unlink(temp_path)

@router.post("/synthesize")
async def synthesize_speech(
    text: str = Form(...),
    voice_id: str = Form("JBFqnCBsd6RMkjVDRZzb") 
):
    """
    Convert text to speech using ElevenLabs.
    Returns streaming audio response.
    """
    client = get_elevenlabs_client()

    try:
        audio_stream = client.generate(
            text=text,
            voice=voice_id,
            model="eleven_multilingual_v2",
            stream=True
        )
        
        return StreamingResponse(
            audio_stream,
            media_type="audio/mpeg"
        )
    except Exception as e:
        print(f"TTS Error: {e}")
        error_msg = str(e)
        if "401" in error_msg or "unusual activity" in error_msg.lower():
             raise HTTPException(status_code=401, detail={"message": "ElevenLabs API Key Invalid/Blocked", "cause": error_msg})
        raise HTTPException(status_code=500, detail=str(e))
