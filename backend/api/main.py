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
from fastapi.responses import Response
import tempfile
import os
from pathlib import Path
from typing import Optional

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
    # Also allow without trailing slash if present, or vice versa
    if FRONTEND_URL.endswith("/"):
        ALLOWED_ORIGINS.append(FRONTEND_URL.rstrip("/"))
    else:
        ALLOWED_ORIGINS.append(FRONTEND_URL + "/")

# Allow Vercel preview deployments (useful for testing)
VERCEL_URL = os.getenv("VERCEL_URL")
if VERCEL_URL:
    ALLOWED_ORIGINS.append(f"https://{VERCEL_URL}")

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

def _is_dev_environment() -> bool:
    """Check if running in development environment."""
    env = os.getenv("ENVIRONMENT", os.getenv("NODE_ENV", "production")).lower()
    return env in ("development", "dev", "local", "test")


def _is_skip_auth_allowed() -> bool:
    """
    Check if SKIP_AUTH is allowed.
    Only permits auth bypass in development environments for security.
    """
    skip_auth = os.getenv("SKIP_AUTH", "false").lower() == "true"
    if skip_auth and not _is_dev_environment():
        print("⚠️  WARNING: SKIP_AUTH=true ignored - only allowed in development environment!")
        print("    Set ENVIRONMENT=development to enable auth bypass.")
        return False
    return skip_auth


async def verify_auth_token(request: Request) -> Optional[dict]:
    """
    Verify authentication token from request headers.
    Returns user info if valid, None if invalid.
    """
    # Check for bypass (development mode only - set SKIP_AUTH=true explicitly)
    if _is_skip_auth_allowed():
        return {"id": "dev-user", "email": "dev@localhost", "name": "Developer"}

    auth_header = request.headers.get("Authorization")
    if not auth_header:
        return None

    try:
        # Extract token from Bearer header
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
            # For simple admin auth, just verify token is present and valid format (64 char hex)
            if len(token) == 64 and all(c in '0123456789abcdef' for c in token):
                return {"id": "admin-user", "email": "admin@thara.ai", "name": "Admin"}
        return None
    except Exception as e:
        print(f"[Auth] Token verification error: {e}")
        return None


async def require_auth(request: Request):
    """Dependency that requires authentication"""
    # Skip auth for certain endpoints
    if request.url.path in ["/", "/api/auth/check", "/api/auth/login"]:
        return None

    user = await verify_auth_token(request)
    if user is None and not _is_skip_auth_allowed():
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
        except (json.JSONDecodeError, UnicodeDecodeError):
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
    """Basic health check endpoint"""
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


@app.get("/api/health")
async def health_check():
    """
    Comprehensive health check endpoint.
    Returns detailed status of all dependencies.
    """
    from datetime import datetime

    health = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "2.0.0",
        "checks": {}
    }

    # Check config
    try:
        from utils.config_loader import get_config, validate_api_keys
        config = get_config()
        health["checks"]["config"] = {"status": "ok"}

        # Check API keys
        api_keys = validate_api_keys()
        missing_keys = [k for k, v in api_keys.items() if not v]
        if missing_keys:
            health["checks"]["api_keys"] = {
                "status": "warning",
                "missing": missing_keys
            }
        else:
            health["checks"]["api_keys"] = {"status": "ok"}

    except Exception as e:
        health["checks"]["config"] = {"status": "error", "message": str(e)}
        health["status"] = "degraded"

    # Check data loaded
    try:
        from api.services import app_state
        if app_state.data_loaded:
            health["checks"]["data"] = {
                "status": "ok",
                "loaded": True,
                "tables": len(app_state.profile_store.get_all_profiles()) if app_state.profile_store else 0
            }
        else:
            health["checks"]["data"] = {"status": "warning", "loaded": False}
    except Exception as e:
        health["checks"]["data"] = {"status": "error", "message": str(e)}

    # Check DuckDB
    try:
        from pathlib import Path
        snapshot_path = Path("data_sources/snapshots/latest.duckdb")
        health["checks"]["duckdb"] = {
            "status": "ok" if snapshot_path.exists() else "warning",
            "snapshot_exists": snapshot_path.exists()
        }
    except Exception as e:
        health["checks"]["duckdb"] = {"status": "error", "message": str(e)}

    # Overall status
    statuses = [c.get("status") for c in health["checks"].values()]
    if "error" in statuses:
        health["status"] = "unhealthy"
    elif "warning" in statuses:
        health["status"] = "degraded"

    return health


# =============================================================================
# Core Endpoints
# =============================================================================

@app.post("/api/load-dataset", response_model=LoadDataResponse)
async def load_dataset(request: LoadDataRequest, user: dict = Depends(require_auth)):
    """
    Load a Google Sheets dataset with automatic profiling.
    Now includes table profiling for intelligent routing.

    MULTI-SPREADSHEET SUPPORT:
    - Set append=False (default) to replace existing data
    - Set append=True to add to existing data (merge multiple spreadsheets)

    Uses OAuth credentials if user has authorized Google Sheets,
    otherwise falls back to service account.
    """
    try:
        print(f"[API] load-dataset for URL: {request.url} (append={request.append})")

        # Validate URL
        if not request.url or not request.url.strip():
            raise HTTPException(status_code=400, detail="URL is required")

        # Get user ID for OAuth credentials
        user_id = user.get("id") if user else None

        result = load_dataset_service(request.url, user_id=user_id, append=request.append)

        if not result.get('success'):
            error_msg = result.get('error', 'Failed to load dataset')
            print(f"[API] Load failed: {error_msg}")
            # Return proper HTTP status code for failures
            raise HTTPException(status_code=422, detail=error_msg)

        return result
    except HTTPException:
        raise  # Re-raise HTTPExceptions as-is
    except Exception as e:
        print(f"[API] Exception in load_dataset: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/dataset-status")
async def get_dataset_status():
    """
    Check if dataset is already loaded (for demo mode).
    Frontend uses this to skip the connection dialog when data is pre-loaded.
    Returns rich metadata for UI display.
    """
    try:
        from api.services import app_state

        if app_state.data_loaded and app_state.profile_store:
            profiles = app_state.profile_store.get_all_profiles()
            return {
                "loaded": True,
                "demo_mode": True,
                "total_tables": len(profiles),
                "tables": list(profiles.keys()),  # DuckDB table names (for reference)
                # Rich metadata for UI display
                "original_sheets": app_state.original_sheet_names,
                "total_records": app_state.total_records,
                "detected_tables": app_state.detected_tables,
                "loaded_spreadsheets": app_state.loaded_spreadsheet_ids
            }
        return {"loaded": False, "demo_mode": False}
    except Exception as e:
        print(f"[API] Error checking dataset status: {e}")
        return {"loaded": False, "demo_mode": False, "error": str(e)}


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
        # Validate query text
        if not request.text or not request.text.strip():
            raise HTTPException(status_code=400, detail="Query text is required")

        print(f"[API] Query: {request.text[:80]}...")

        # Pass conversation_id if provided
        conversation_id = getattr(request, 'conversation_id', None)
        result = process_query_service(request.text, conversation_id)

        if result.get('success'):
            print(f"[API] Query success - Table: {result.get('table_used')}, "
                  f"Confidence: {result.get('routing_confidence', 0):.0%}")
        else:
            error_msg = result.get('error', 'Query processing failed')
            print(f"[API] Query failed: {error_msg}")
            # Note: Query failures (no data found, etc.) return 200 with success=false
            # This is intentional - the client request was valid, just no data matched

        return result
    except HTTPException:
        raise  # Re-raise HTTPExceptions as-is
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
        except OSError:
            pass  # File cleanup is non-critical

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
    Authenticate admin user with username/password.
    Single admin credentials: HelloThara / MyBizEmpire@2026
    """
    username = request.get("username", "")
    password = request.get("password", "")

    # Admin credentials
    admin_username = "HelloThara"
    admin_password = "MyBizEmpire@2026"

    if username == admin_username and password == admin_password:
        # Generate a simple token for session management
        import hashlib
        import time
        token_data = f"{username}:{time.time()}"
        access_token = hashlib.sha256(token_data.encode()).hexdigest()

        return {
            "success": True,
            "user": {
                "id": "admin-user",
                "name": "Admin",
                "email": "admin@thara.ai"
            },
            "access_token": access_token,
            "message": "Login successful"
        }
    else:
        raise HTTPException(status_code=401, detail="Invalid username or password")


@app.get("/api/auth/check", response_model=AuthResponse)
async def check_auth(request: Request):
    """Check authentication status."""
    user = await verify_auth_token(request)

    if _is_skip_auth_allowed():
        return {"authenticated": True, "user": {"name": "Developer"}}

    return {
        "authenticated": user is not None,
        "user": user
    }




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
    print("  - Thara Personality")
    print("  - Conversation Context")
    print("  - Tamil Language Support")
    print()
    print("  Endpoints:")
    print("  - POST /api/load-dataset    (with profiling)")
    print("  - POST /api/query           (with healing)")
    print("  - POST /api/transcribe")
    print("  - POST /api/text-to-speech")
    print("  - GET  /api/onboarding/start")
    print("  - GET  /api/debug/routing")
    print("  - GET  /api/debug/profiles")
    print("  - GET  /api/health          (health check)")
    print()
    print(f"  CORS: {', '.join(ALLOWED_ORIGINS[:2])}...")
    print(f"  Auth: {'DISABLED (dev mode)' if _is_skip_auth_allowed() else 'ENABLED'}")

    # Validate configuration and API keys
    try:
        from utils.config_loader import print_startup_validation
        print_startup_validation()
    except Exception as e:
        print(f"  ⚠️  Config validation error: {e}")

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

    # === DEMO MODE: Auto-load hardcoded sheets on startup ===
    try:
        from utils.config_loader import get_config
        from api.services import load_dataset_service, app_state
        config = get_config()

        # Check if demo_mode is configured in settings.yaml
        demo_mode = config.google_sheets.demo_mode

        if demo_mode and demo_mode.enabled:
            auto_load_ids = demo_mode.auto_load_spreadsheets

            if auto_load_ids:
                print()
                print("  [DEMO MODE] Auto-loading spreadsheets...")
                for idx, sheet_id in enumerate(auto_load_ids, 1):
                    try:
                        sheets_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}"
                        print(f"    [{idx}/{len(auto_load_ids)}] Loading {sheet_id[:20]}...")
                        # Use append=True for subsequent spreadsheets (idx > 1)
                        # This merges data from multiple spreadsheets
                        result = load_dataset_service(sheets_url, user_id=None, append=(idx > 1))

                        if result.get('success'):
                            stats = result.get('stats', {})
                            tables = stats.get('totalTables', 0) if stats else 0
                            sheets = stats.get('sheetCount', 0) if stats else 0
                            print(f"    [{idx}/{len(auto_load_ids)}] ✓ Loaded {tables} tables from {sheets} sheets")
                        else:
                            print(f"    [{idx}/{len(auto_load_ids)}] ✗ Failed: {result.get('error', 'Unknown error')}")
                    except Exception as e:
                        print(f"    [{idx}/{len(auto_load_ids)}] ✗ Error: {e}")

                print("  [DEMO MODE] Auto-load complete!")
                print()
    except Exception as e:
        print(f"  WARNING: Demo mode auto-load failed: {e}")

    # Ensure snapshots directory exists (prevents confusing DuckDB errors)
    from pathlib import Path
    snapshots_dir = Path("data_sources/snapshots")
    snapshots_dir.mkdir(parents=True, exist_ok=True)
    print(f"  Snapshots dir: OK")

    print()
    print("=" * 60)


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup resources on shutdown"""
    print("[API] Kiwi-RAG API shutting down...")


if __name__ == "__main__":
    import uvicorn
    host = os.getenv("BACKEND_HOST", "0.0.0.0")
    port = int(os.getenv("BACKEND_PORT", os.getenv("PORT", "8000")))
    uvicorn.run(app, host=host, port=port)
