"""
FastAPI application for Kiwi-RAG backend.
Exposes REST endpoints for the Next.js frontend.

Updated with:
- OAuth authentication middleware
- New onboarding endpoints
- Debug/routing endpoints
- Conversation context management
"""

from fastapi import FastAPI, UploadFile, File, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, StreamingResponse
import tempfile
import os
import asyncio
import json
from pathlib import Path
from typing import Optional
from pydantic import BaseModel

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
    transcribe_audio_service,
    start_onboarding_service,
    process_onboarding_input_service,
    get_routing_debug_service,
    get_table_profiles_service,
    clear_context_service
)

# Create FastAPI app
app = FastAPI(
    title="Kiwi-RAG API",
    description="AI-Powered Google Sheets Analytics API with Thara Personality",
    version="2.0.0"
)

# Configure CORS for frontend
ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3001",
]

# Add production frontend URL from environment
FRONTEND_URL = os.getenv("FRONTEND_URL")
if FRONTEND_URL:
    ALLOWED_ORIGINS.append(FRONTEND_URL)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# Authentication Middleware
# =============================================================================

async def verify_auth_token(request: Request) -> Optional[dict]:
    """
    Verify authentication token from request headers.
    Returns user info if valid, None if invalid.
    """
    # Check for bypass (development mode only - set SKIP_AUTH=true explicitly)
    if os.getenv("SKIP_AUTH", "false").lower() == "true":
        return {"id": "dev-user", "email": "dev@localhost", "name": "Developer"}

    auth_header = request.headers.get("Authorization")
    if not auth_header:
        return None

    try:
        from utils.supabase_auth import verify_token
        return verify_token(auth_header)
    except Exception as e:
        print(f"[Auth] Token verification error: {e}")
        return None


async def require_auth(request: Request):
    """Dependency that requires authentication"""
    # Skip auth for certain endpoints
    if request.url.path in ["/", "/api/auth/check", "/api/auth/google", "/api/auth/callback"]:
        return None

    user = await verify_auth_token(request)
    if user is None and os.getenv("SKIP_AUTH", "false").lower() != "true":
        raise HTTPException(status_code=401, detail="Authentication required")

    return user


# =============================================================================
# Request Logging Middleware
# =============================================================================

@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests for debugging"""
    import json

    if request.method == "POST":
        body = await request.body()
        try:
            body_json = json.loads(body.decode())
            # Truncate long values for logging
            log_body = {k: (v[:100] + "..." if isinstance(v, str) and len(v) > 100 else v)
                       for k, v in body_json.items()}
            print(f"[API] {request.method} {request.url.path} - Body: {log_body}")
        except:
            print(f"[API] {request.method} {request.url.path} - Body: (binary data)")

        # Re-create request with body for downstream processing
        from starlette.requests import Request as StarletteRequest
        async def receive():
            return {"type": "http.request", "body": body}
        request = StarletteRequest(request.scope, receive)

    response = await call_next(request)
    return response


# =============================================================================
# Health Check
# =============================================================================

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "ok",
        "message": "Kiwi-RAG API is running",
        "version": "2.0.0",
        "features": [
            "intelligent_routing",
            "query_healing",
            "thara_personality",
            "conversation_context",
            "tamil_support"
        ]
    }


# =============================================================================
# Core Endpoints
# =============================================================================

@app.post("/api/load-dataset", response_model=LoadDataResponse)
async def load_dataset(request: LoadDataRequest, user: dict = Depends(require_auth)):
    """
    Load a Google Sheets dataset with automatic profiling.
    Now includes table profiling for intelligent routing.

    Uses OAuth credentials if user has authorized Google Sheets,
    otherwise falls back to service account.
    """
    try:
        print(f"[API] load-dataset for URL: {request.url}")

        # Get user ID for OAuth credentials
        user_id = user.get("id") if user else None

        result = load_dataset_service(request.url, user_id=user_id)

        if not result.get('success'):
            print(f"[API] Load failed: {result.get('error')}")

        return result
    except Exception as e:
        print(f"[API] Exception in load_dataset: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/query", response_model=ProcessQueryResponse)
async def process_query(request: QueryRequest, user: dict = Depends(require_auth)):
    """
    Process a user query with intelligent routing and healing.

    New features:
    - Intelligent table routing (no more top_k=50!)
    - Self-healing execution
    - Follow-up context support
    - Thara personality in responses
    """
    try:
        print(f"[API] Query: {request.text[:80]}...")

        # Pass conversation_id if provided
        conversation_id = getattr(request, 'conversation_id', None)
        result = process_query_service(request.text, conversation_id)

        if result.get('success'):
            print(f"[API] Query success - Table: {result.get('table_used')}, "
                  f"Confidence: {result.get('routing_confidence', 0):.0%}")
        else:
            print(f"[API] Query failed: {result.get('error')}")

        return result
    except Exception as e:
        print(f"[API] Exception in process_query: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/transcribe", response_model=TranscribeResponse)
async def transcribe_audio(audio: UploadFile = File(...), user: dict = Depends(require_auth)):
    """Transcribe audio to text."""
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as tmp_file:
            content = await audio.read()
            tmp_file.write(content)
            tmp_path = tmp_file.name

        result = transcribe_audio_service(tmp_path)

        try:
            os.unlink(tmp_path)
        except:
            pass

        return result
    except Exception as e:
        print(f"[API] Exception in transcribe_audio: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/text-to-speech")
async def text_to_speech_endpoint(request: dict, user: dict = Depends(require_auth)):
    """Convert text to speech using ElevenLabs."""
    try:
        from utils.voice_utils import text_to_speech, get_default_voice_id

        text = request.get("text", "")
        # Use provided voice_id or fall back to config default
        voice_id = request.get("voice_id") or get_default_voice_id()

        if not text:
            raise HTTPException(status_code=400, detail="Text is required")

        print(f"[API] TTS with voice {voice_id}: {text[:50]}...")
        audio_bytes = text_to_speech(text, voice_id=voice_id)
        print(f"[API] Generated {len(audio_bytes)} bytes of audio")

        return Response(
            content=audio_bytes,
            media_type="audio/mpeg",
            headers={"Content-Disposition": "attachment; filename=speech.mp3"}
        )
    except Exception as e:
        print(f"[API] Exception in text_to_speech: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Authentication Endpoints
# =============================================================================

@app.post("/api/auth/login")
async def login(request: dict):
    """
    Authenticate user with username/password.
    Demo mode allows admin/admin123 (configurable via env).
    """
    username = request.get("username", "")
    password = request.get("password", "")

    # Get demo credentials from environment (more secure than hardcoded)
    demo_username = os.getenv("DEMO_USERNAME", "admin")
    demo_password = os.getenv("DEMO_PASSWORD", "admin123")

    if username == demo_username and password == demo_password:
        return {
            "success": True,
            "user": {
                "name": username,
                "email": f"{username}@thara.ai"
            },
            "message": "Login successful"
        }
    else:
        raise HTTPException(status_code=401, detail="Invalid username or password")


@app.get("/api/auth/check", response_model=AuthResponse)
async def check_auth(request: Request):
    """Check authentication status."""
    user = await verify_auth_token(request)

    if os.getenv("SKIP_AUTH", "false").lower() == "true":
        return {"authenticated": True, "user": {"name": "Developer"}}

    return {
        "authenticated": user is not None,
        "user": user
    }


@app.get("/api/auth/google")
async def google_login():
    """Get Google OAuth URL for login."""
    try:
        from utils.supabase_auth import get_google_oauth_url
        url = get_google_oauth_url()
        return {"url": url}
    except Exception as e:
        print(f"[Auth] Google OAuth error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/auth/callback")
async def auth_callback(request: dict):
    """Handle OAuth callback and return tokens."""
    try:
        from utils.supabase_auth import handle_oauth_callback
        code = request.get("code")
        if not code:
            raise HTTPException(status_code=400, detail="Authorization code required")
        return handle_oauth_callback(code)
    except Exception as e:
        print(f"[Auth] Callback error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Google Sheets OAuth Endpoints
# =============================================================================

@app.get("/api/auth/sheets/check")
async def check_sheets_auth(request: Request):
    """Check if user has authorized Google Sheets access."""
    try:
        from utils.gsheet_oauth import has_sheets_access, check_gsheet_oauth_configured

        # Check if OAuth is configured
        if not check_gsheet_oauth_configured():
            return {
                "configured": False,
                "authorized": False,
                "message": "Google Sheets OAuth not configured on server"
            }

        # Get user from auth
        user = await verify_auth_token(request)
        user_id = user.get("id", "dev-user") if user else "dev-user"

        has_access = has_sheets_access(user_id)

        return {
            "configured": True,
            "authorized": has_access,
            "user_id": user_id
        }
    except Exception as e:
        print(f"[Sheets Auth] Check error: {e}")
        return {
            "configured": False,
            "authorized": False,
            "error": str(e)
        }


@app.get("/api/auth/sheets")
async def get_sheets_oauth_url(request: Request):
    """Get Google OAuth URL for Sheets access."""
    try:
        from utils.gsheet_oauth import get_gsheet_oauth_url, check_gsheet_oauth_configured

        if not check_gsheet_oauth_configured():
            raise HTTPException(
                status_code=500,
                detail="Google Sheets OAuth not configured. Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET."
            )

        # Get user from auth
        user = await verify_auth_token(request)
        user_id = user.get("id", "dev-user") if user else "dev-user"

        url = get_gsheet_oauth_url(user_id)
        return {"url": url}
    except HTTPException:
        raise
    except Exception as e:
        print(f"[Sheets Auth] OAuth URL error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/auth/sheets/callback")
async def sheets_oauth_callback(request: dict, req: Request):
    """Handle Google Sheets OAuth callback."""
    try:
        from utils.gsheet_oauth import exchange_code_for_tokens

        code = request.get("code")
        if not code:
            raise HTTPException(status_code=400, detail="Authorization code required")

        # Get user from auth
        user = await verify_auth_token(req)
        user_id = user.get("id", "dev-user") if user else "dev-user"

        result = exchange_code_for_tokens(code, user_id)
        return result
    except HTTPException:
        raise
    except Exception as e:
        print(f"[Sheets Auth] Callback error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/auth/sheets/revoke")
async def revoke_sheets_access(request: Request):
    """Revoke user's Google Sheets access."""
    try:
        from utils.gsheet_oauth import revoke_access

        # Get user from auth
        user = await verify_auth_token(request)
        user_id = user.get("id", "dev-user") if user else "dev-user"

        success = revoke_access(user_id)
        return {"success": success, "message": "Google Sheets access revoked"}
    except Exception as e:
        print(f"[Sheets Auth] Revoke error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Onboarding Endpoints
# =============================================================================

@app.get("/api/onboarding/start")
async def start_onboarding():
    """Start or continue onboarding flow."""
    try:
        return start_onboarding_service()
    except Exception as e:
        print(f"[API] Exception in start_onboarding: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/onboarding/input")
async def process_onboarding_input(request: dict):
    """Process user input during onboarding."""
    try:
        user_input = request.get("input", "")
        return process_onboarding_input_service(user_input)
    except Exception as e:
        print(f"[API] Exception in process_onboarding_input: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Debug/Admin Endpoints
# =============================================================================

@app.get("/api/debug/routing")
async def debug_routing(question: str):
    """
    Debug endpoint to see how a question would be routed.
    Shows table selection reasoning.
    """
    try:
        return get_routing_debug_service(question)
    except Exception as e:
        print(f"[API] Exception in debug_routing: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/debug/profiles")
async def debug_profiles():
    """
    Get all table profiles for inspection.
    Shows how tables are profiled for routing.
    """
    try:
        return get_table_profiles_service()
    except Exception as e:
        print(f"[API] Exception in debug_profiles: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/context/clear")
async def clear_context(request: dict = None):
    """Clear conversation context."""
    try:
        conversation_id = request.get("conversation_id") if request else None
        return clear_context_service(conversation_id)
    except Exception as e:
        print(f"[API] Exception in clear_context: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Real-time Sheet Update Endpoints (Webhook + SSE)
# =============================================================================

class SheetUpdateRequest(BaseModel):
    """Request model for sheet update webhook."""
    spreadsheetId: str
    sheetName: Optional[str] = None
    updatedAt: Optional[str] = None


@app.post("/api/sheet-update")
async def sheet_update_webhook(request: SheetUpdateRequest):
    """
    Webhook endpoint for Google Apps Script notifications.
    
    Called when sheet data changes - queues async refresh.
    Returns immediately (no blocking).
    """
    try:
        from utils.webhook_handler import get_webhook_handler
        
        handler = get_webhook_handler()
        queued = handler.queue_update(
            spreadsheet_id=request.spreadsheetId,
            sheet_name=request.sheetName
        )
        
        print(f"[Webhook] Received update for {request.sheetName or 'all sheets'}")
        
        return {
            "success": True,
            "queued": queued,
            "message": "Update queued for processing"
        }
    except Exception as e:
        print(f"[Webhook] Error: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@app.get("/api/events/data-refresh")
async def data_refresh_events():
    """
    Server-Sent Events (SSE) endpoint for real-time data refresh notifications.
    
    Frontend connects here to receive instant updates when sheet data changes.
    """
    from utils.webhook_handler import get_webhook_handler
    
    handler = get_webhook_handler()
    sub_queue = handler.subscribe()
    
    async def event_generator():
        try:
            # Send initial heartbeat (SSE format: "data: ...\n\n")
            yield "data: " + json.dumps({'type': 'connected'}) + "\n\n"
            
            while True:
                try:
                    # Wait for events with timeout (for heartbeat)
                    event = await asyncio.wait_for(
                        sub_queue.get(),
                        timeout=30.0
                    )
                    yield "data: " + json.dumps(event) + "\n\n"
                except asyncio.TimeoutError:
                    # Send heartbeat to keep connection alive
                    yield "data: " + json.dumps({'type': 'heartbeat'}) + "\n\n"
        except asyncio.CancelledError:
            handler.unsubscribe(sub_queue)
            raise
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable nginx buffering
        }
    )


@app.get("/api/refresh-status")
async def get_refresh_status():
    """Get the last refresh timestamp and status."""
    try:
        from utils.webhook_handler import get_webhook_handler
        
        handler = get_webhook_handler()
        last_refresh = handler.get_last_refresh()
        
        return {
            "success": True,
            "last_refresh": last_refresh,
            "has_pending_updates": False  # Could check dirty sheets here
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


# =============================================================================
# Lifecycle Events
# =============================================================================

@app.on_event("startup")
async def startup_event():
    """Initialize resources on startup"""
    print("=" * 60)
    print("  Kiwi-RAG API v2.0 - Starting up...")
    print("=" * 60)
    print()
    print("  New Features:")
    print("  - Intelligent Table Routing (no more top_k=50!)")
    print("  - Self-Healing Query Execution")
    print("  - Real-time Sheet Updates (webhook + SSE)")
    print("  - Thara Personality")
    print("  - Conversation Context")
    print("  - Tamil Language Support")
    print()
    print("  Endpoints:")
    print("  - POST /api/load-dataset       (with profiling)")
    print("  - POST /api/query              (with healing)")
    print("  - POST /api/sheet-update       (webhook receiver)")
    print("  - GET  /api/events/data-refresh (SSE stream)")
    print("  - POST /api/transcribe")
    print("  - POST /api/text-to-speech")
    print("  - GET  /api/onboarding/start")
    print("  - GET  /api/debug/routing")
    print("  - GET  /api/debug/profiles")
    print()
    print(f"  CORS: {', '.join(ALLOWED_ORIGINS[:2])}...")
    print(f"  Auth: {'DISABLED (dev mode)' if os.getenv('SKIP_AUTH', 'false').lower() == 'true' else 'ENABLED'}")
    print()

    # Pre-load spreadsheet_id from config to enable caching
    try:
        from utils.config_loader import get_config
        from api.services import app_state
        config = get_config()
        spreadsheet_id = config.google_sheets.spreadsheet_id
        if spreadsheet_id:
            app_state.current_spreadsheet_id = spreadsheet_id
            print(f"  Spreadsheet ID: {spreadsheet_id[:25]}... (from config)")
            print(f"  Cache: 300s TTL enabled")
        else:
            print("  WARNING: No spreadsheet_id in config - cache disabled")
    except Exception as e:
        print(f"  WARNING: Could not pre-load spreadsheet_id: {e}")

    # Ensure snapshots directory exists (prevents confusing DuckDB errors)
    from pathlib import Path
    snapshots_dir = Path("data_sources/snapshots")
    snapshots_dir.mkdir(parents=True, exist_ok=True)
    print(f"  Snapshots dir: OK")
    
    # Start webhook handler background worker
    try:
        from utils.webhook_handler import get_webhook_handler
        handler = get_webhook_handler()
        handler.start_worker()
        print(f"  Webhook handler: OK (background worker started)")
    except Exception as e:
        print(f"  WARNING: Webhook handler failed to start: {e}")

    print()
    print("=" * 60)


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup resources on shutdown"""
    print("[API] Kiwi-RAG API shutting down...")
    
    # Stop webhook handler background worker
    try:
        from utils.webhook_handler import get_webhook_handler
        handler = get_webhook_handler()
        handler.stop_worker()
        print("[API] Webhook handler stopped")
    except Exception as e:
        print(f"[API] Warning: Error stopping webhook handler: {e}")


if __name__ == "__main__":
    import uvicorn
    host = os.getenv("BACKEND_HOST", "0.0.0.0")
    port = int(os.getenv("BACKEND_PORT", os.getenv("PORT", "8000")))
    uvicorn.run(app, host=host, port=port)
