"""
FastAPI application for Kiwi-RAG backend.
Exposes REST endpoints for the Next.js frontend.
"""

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import tempfile
import os
from pathlib import Path

from api.models import (
    LoadDataRequest,
    LoadDataResponse,
    QueryRequest,
    ProcessQueryResponse,
    TranscribeResponse,
    AuthResponse
)
from api.services import (
    load_dataset_service,
    process_query_service,
    transcribe_audio_service
)

# Create FastAPI app
app = FastAPI(
    title="Kiwi-RAG API",
    description="AI-Powered Google Sheets Analytics API",
    version="1.0.0"
)

# Configure CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Next.js dev server
        "http://127.0.0.1:3000",
        "http://localhost:3001",  # Next.js dev server (alternate port)
        "http://127.0.0.1:3001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "ok",
        "message": "Kiwi-RAG API is running",
        "version": "1.0.0"
    }


@app.post("/api/load-dataset", response_model=LoadDataResponse)
async def load_dataset(request: LoadDataRequest):
    """
    Load a Google Sheets dataset.
    
    Frontend equivalent: api.loadDataset(url)
    Backend equivalent: load_sheets_data(spreadsheet_id)
    """
    try:
        print(f"📥 Received load-dataset request for URL: {request.url}")
        result = load_dataset_service(request.url)
        print(f"✅ Load dataset result: success={result.get('success')}")
        if not result.get('success'):
            print(f"❌ Error: {result.get('error')}")
        return result
    except Exception as e:
        print(f"❌ Exception in load_dataset: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/query", response_model=ProcessQueryResponse)
async def process_query(request: QueryRequest):
    """
    Process a user query.
    
    Frontend equivalent: api.sendMessage(text)
    Backend equivalent: process_query(question)
    """
    try:
        print(f"📥 Received query request: {request.text[:50]}...")
        result = process_query_service(request.text)
        print(f"✅ Query result: success={result.get('success')}")
        if not result.get('success'):
            print(f"❌ Error: {result.get('error')}")
        return result
    except Exception as e:
        print(f"❌ Exception in process_query: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# Add middleware to log all requests
from fastapi import Request as FastAPIRequest
import json

@app.middleware("http")
async def log_requests(request: FastAPIRequest, call_next):
    """Log all incoming requests for debugging"""
    if request.method == "POST":
        body = await request.body()
        try:
            body_json = json.loads(body.decode())
            print(f"📨 {request.method} {request.url.path} - Body: {body_json}")
        except:
            print(f"📨 {request.method} {request.url.path} - Body: (binary data)")
        
        # Re-create request with body for downstream processing
        from starlette.requests import Request
        async def receive():
            return {"type": "http.request", "body": body}
        request = Request(request.scope, receive)
    
    response = await call_next(request)
    return response


@app.post("/api/transcribe", response_model=TranscribeResponse)
async def transcribe_audio(audio: UploadFile = File(...)):
    """
    Transcribe audio to text.
    
    Frontend equivalent: api.transcribeAudio(audioBlob)
    Backend equivalent: transcribe_audio(audio_path)
    """
    try:
        # Save uploaded file to temp location
        with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as tmp_file:
            content = await audio.read()
            tmp_file.write(content)
            tmp_path = tmp_file.name
        
        # Transcribe
        result = transcribe_audio_service(tmp_path)
        
        # Clean up temp file
        try:
            os.unlink(tmp_path)
        except:
            pass
        
        return result
    except Exception as e:
        print(f"❌ Exception in transcribe_audio: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/text-to-speech")
async def text_to_speech_endpoint(request: dict):
    """
    Convert text to speech using ElevenLabs with Rachel voice.
    
    Args:
        request: {"text": "text to speak", "voice_id": "optional_voice_id"}
    
    Returns:
        Audio file (MP3)
    """
    try:
        from utils.voice_utils import text_to_speech
        from fastapi.responses import Response
        
        text = request.get("text", "")
        voice_id = request.get("voice_id", "OUBMjq0LvBjb07bhwD3H")  # User's preferred voice
        
        if not text:
            raise HTTPException(status_code=400, detail="Text is required")
        
        print(f"🔊 Converting text to speech with voice {voice_id}: {text[:50]}...")
        audio_bytes = text_to_speech(text, voice_id=voice_id)
        print(f"✅ Generated {len(audio_bytes)} bytes of audio")
        
        return Response(
            content=audio_bytes,
            media_type="audio/mpeg",
            headers={
                "Content-Disposition": "attachment; filename=speech.mp3"
            }
        )
    except Exception as e:
        print(f"❌ Exception in text_to_speech: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/auth/check", response_model=AuthResponse)
async def check_auth():
    """
    Check authentication status.
    
    Frontend equivalent: api.checkAuth()
    Status: DISABLED - Always returns true per user requirements
    """
    return {"authenticated": True}


@app.on_event("startup")
async def startup_event():
    """Initialize resources on startup"""
    print("🥝 Kiwi-RAG API starting up...")
    print("✓ CORS enabled for http://localhost:3000")
    print("✓ Endpoints ready:")
    print("  - POST /api/load-dataset")
    print("  - POST /api/query")
    print("  - POST /api/transcribe")
    print("  - GET  /api/auth/check")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup resources on shutdown"""
    print("🥝 Kiwi-RAG API shutting down...")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
