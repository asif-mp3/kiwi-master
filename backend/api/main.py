"""
FastAPI application for Kiwi-RAG backend.
Exposes REST endpoints for the Next.js frontend.

Updated with:
- OAuth authentication middleware
- New onboarding endpoints
- Debug/routing endpoints
- Conversation context management
"""

# CRITICAL: Force UTF-8 encoding for stdout/stderr
# This prevents UnicodeEncodeError when printing non-ASCII characters (like emojis, ₹, Tamil text)
# MUST run BEFORE any imports that might print
import sys
import io
import os

# Set environment variables first
os.environ['PYTHONIOENCODING'] = 'utf-8'
os.environ['PYTHONLEGACYWINDOWSSTDIO'] = '0'

# Create a safe print function that handles encoding errors
_original_print = print
def _safe_print(*args, **kwargs):
    """Print function that handles Unicode encoding errors gracefully."""
    try:
        # Convert any problematic characters
        safe_args = []
        for arg in args:
            if isinstance(arg, str):
                # Replace any characters that can't be encoded
                safe_args.append(arg.encode('utf-8', errors='replace').decode('utf-8'))
            else:
                safe_args.append(arg)
        _original_print(*safe_args, **kwargs)
    except UnicodeEncodeError:
        # Last resort: encode and decode with replacement
        try:
            safe_args = [str(arg).encode('ascii', errors='replace').decode('ascii') for arg in args]
            _original_print(*safe_args, **kwargs)
        except Exception:
            pass  # Silently fail rather than crash
    except Exception:
        pass  # Silently fail rather than crash

# Replace the built-in print globally
import builtins
builtins.print = _safe_print

# Also try to reconfigure stdout/stderr
def _setup_utf8_output():
    """Wrap stdout/stderr with UTF-8 encoding to handle any Unicode characters."""
    try:
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        elif hasattr(sys.stdout, 'buffer'):
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)
    except Exception:
        pass
    try:
        if hasattr(sys.stderr, 'reconfigure'):
            sys.stderr.reconfigure(encoding='utf-8', errors='replace')
        elif hasattr(sys.stderr, 'buffer'):
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace', line_buffering=True)
    except Exception:
        pass

_setup_utf8_output()

from fastapi import FastAPI, UploadFile, File, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, StreamingResponse
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
    load_dataset_from_source,
    sync_drive_folder,
    process_query_service,
    transcribe_audio_service,
    start_onboarding_service,
    process_onboarding_input_service,
    get_routing_debug_service,
    get_table_profiles_service,
    clear_context_service
)

# Backend directory for relative paths (works in containers)
_BACKEND_DIR = Path(__file__).parent.parent

# Create FastAPI app
app = FastAPI(
    title="Kiwi-RAG API",
    description="AI-Powered Google Sheets Analytics API with Thara Personality",
    version="2.0.0"
)

# Configure CORS for frontend
ALLOWED_ORIGINS = [
    # Local development
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3001",
    # Production (Vercel)
    "https://thara-ai.vercel.app",
    "https://www.thara-ai.vercel.app",
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
        print("[WARN]  WARNING: SKIP_AUTH=true ignored - only allowed in development environment!")
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
        return {"id": "dev-user", "email": "dev@thara.ai", "name": "Developer"}

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
        snapshot_path = _BACKEND_DIR / "data_sources" / "snapshots" / "latest.duckdb"
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
# URL Validation (SSRF Prevention)
# =============================================================================

# Allowlist of domains that can be fetched
ALLOWED_URL_DOMAINS = [
    "docs.google.com",
    "drive.google.com",
    "sheets.googleapis.com",
    "www.googleapis.com",
]


def validate_url_for_ssrf(url: str) -> bool:
    """
    Validate URL against SSRF attacks.
    Only allows specific trusted domains.

    Returns True if URL is safe, raises HTTPException otherwise.
    """
    if not url:
        return False

    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)

        # Must be http or https
        if parsed.scheme not in ("http", "https"):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid URL scheme: {parsed.scheme}. Only http/https allowed."
            )

        # Check against allowlist
        hostname = parsed.hostname or ""
        hostname_lower = hostname.lower()

        # Check if hostname matches allowed domains
        is_allowed = any(
            hostname_lower == domain or hostname_lower.endswith(f".{domain}")
            for domain in ALLOWED_URL_DOMAINS
        )

        if not is_allowed:
            raise HTTPException(
                status_code=400,
                detail=f"Domain not allowed: {hostname}. Only Google Sheets/Drive URLs are supported."
            )

        # Block internal/private IPs
        import ipaddress
        try:
            ip = ipaddress.ip_address(hostname)
            if ip.is_private or ip.is_loopback or ip.is_reserved:
                raise HTTPException(
                    status_code=400,
                    detail="Access to internal/private addresses is not allowed."
                )
        except ValueError:
            pass  # Not an IP address, that's fine

        return True

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid URL: {str(e)}")


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


def is_local_path(path: str) -> bool:
    """Check if a path is a local filesystem path (not a remote URL)."""
    if not path:
        return False
    path = path.strip()
    # file:// URLs
    if path.startswith('file://'):
        return True
    # Windows absolute paths: C:\, D:\, etc.
    if len(path) >= 2 and path[1] == ':':
        return True
    # Unix absolute paths
    if path.startswith('/'):
        return True
    # Home directory paths
    if path.startswith('~'):
        return True
    return False


@app.post("/api/load-source", response_model=LoadDataResponse)
async def load_source(request: LoadDataRequest, user: dict = Depends(require_auth)):
    """
    NEW: Load data from any supported source (CSV, Excel, Google Drive, or Google Sheets).

    Supported sources:
    - Google Sheets: https://docs.google.com/spreadsheets/d/...
    - CSV files: https://example.com/data.csv or local paths
    - Excel files: https://example.com/data.xlsx or local paths
    - Google Drive files: https://drive.google.com/file/d/...
    - Local files: C:\\path\\file.csv, /path/file.csv, ~/file.csv

    For Google Sheets URLs, this automatically uses the existing code path.
    For other sources, it uses the new connector system.

    ADDITIVE: Does not modify existing /api/load-dataset functionality.
    """
    try:
        print(f"[API] load-source for URL: {request.url} (append={request.append})")

        # Validate URL
        if not request.url or not request.url.strip():
            raise HTTPException(status_code=400, detail="URL is required")

        # SSRF Prevention: Only validate remote URLs
        # Local paths have their own security via LocalConnector.ALLOWED_BASE_DIRS
        if not is_local_path(request.url):
            validate_url_for_ssrf(request.url)

        # Get user ID for OAuth credentials (used for Google Sheets)
        user_id = user.get("id") if user else None

        # Use new universal loader (routes to existing code for Google Sheets)
        result = load_dataset_from_source(request.url, user_id=user_id, append=request.append)

        if not result.get('success'):
            error_msg = result.get('error', 'Failed to load data source')
            print(f"[API] Load failed: {error_msg}")
            raise HTTPException(status_code=422, detail=error_msg)

        return result

    except HTTPException:
        raise
    except Exception as e:
        print(f"[API] Exception in load_source: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/upload-file", response_model=LoadDataResponse)
async def upload_file(
    file: UploadFile = File(...),
    append: bool = False,
    user: dict = Depends(require_auth)
):
    """
    Upload a local file (CSV, Excel, PDF) directly.

    This endpoint handles file uploads from the frontend when users want to
    add local files. The file is saved to a temp location and processed.

    Args:
        file: The uploaded file
        append: If true, append to existing data. Default: false (replace)

    Returns:
        LoadDataResponse with success status and loaded table info
    """
    import tempfile
    import shutil

    try:
        print(f"[API] upload-file: {file.filename} (append={append})")

        # Validate file type
        if not file.filename:
            raise HTTPException(status_code=400, detail="Filename is required")

        filename_lower = file.filename.lower()
        allowed_extensions = ['.csv', '.xlsx', '.xls', '.xlsm', '.pdf']

        if not any(filename_lower.endswith(ext) for ext in allowed_extensions):
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type. Allowed: {', '.join(allowed_extensions)}"
            )

        # Save to temp file
        suffix = os.path.splitext(file.filename)[1]
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            shutil.copyfileobj(file.file, tmp)
            temp_path = tmp.name

        print(f"[API] Saved upload to: {temp_path}")

        try:
            # Process file directly based on extension
            # (bypass LocalConnector security check for temp files)
            tables = {}
            ext = suffix.lower()

            if ext == '.csv':
                from data_sources.connectors.csv_connector import CSVConnector
                connector = CSVConnector(temp_path)
                tables = connector.fetch_tables()
            elif ext in ('.xlsx', '.xls', '.xlsm'):
                from data_sources.connectors.excel_connector import ExcelConnector
                connector = ExcelConnector(temp_path)
                tables = connector.fetch_tables()
            elif ext == '.pdf':
                from data_sources.connectors.pdf_connector import PDFConnector
                connector = PDFConnector(temp_path)
                tables = connector.fetch_tables()
            else:
                raise HTTPException(status_code=400, detail=f"Unsupported file type: {ext}")

            if not tables:
                raise HTTPException(status_code=422, detail="No data found in file")

            # Load tables into DuckDB directly
            from analytics_engine.duckdb_manager import DuckDBManager
            from schema_intelligence.data_profiler import DataProfiler
            from api.services import app_state  # Use shared singleton

            db = DuckDBManager()
            conn = db.get_connection()
            profiler = DataProfiler()
            profile_store = app_state.profile_store  # USE SHARED INSTANCE (not local)

            # If not appending, DELETE all existing data first
            if not append:
                print("[API] Replace mode: deleting existing tables and profiles...")

                # Get all existing tables from DuckDB
                existing_tables = [row[0] for row in conn.execute("SHOW TABLES").fetchall()]

                # Drop all existing tables
                for old_table in existing_tables:
                    try:
                        conn.execute(f'DROP TABLE IF EXISTS "{old_table}"')
                        print(f"[API] Dropped table: {old_table}")
                    except Exception as drop_err:
                        print(f"[API] Warning: Could not drop {old_table}: {drop_err}")

                # Clear all profiles
                profile_store.clear_profiles()
                print(f"[API] Cleared {len(existing_tables)} existing tables and profiles")

            total_records = 0
            loaded_tables = []

            for table_name, dfs in tables.items():
                for i, df in enumerate(dfs):
                    # Generate unique table name
                    safe_name = table_name.replace(' ', '_').replace('-', '_')
                    safe_name = ''.join(c for c in safe_name if c.isalnum() or c == '_')
                    full_table_name = f"{safe_name}_{i}" if len(dfs) > 1 else safe_name

                    # Load into DuckDB
                    conn.execute(f'DROP TABLE IF EXISTS "{full_table_name}"')
                    conn.execute(f'CREATE TABLE "{full_table_name}" AS SELECT * FROM df')

                    total_records += len(df)
                    loaded_tables.append(full_table_name)

                    # Profile the table (args: table_name, df)
                    try:
                        profile = profiler.profile_table(full_table_name, df)
                        profile_store.set_profile(full_table_name, profile)
                    except Exception as profile_err:
                        print(f"[API] Warning: Could not profile {full_table_name}: {profile_err}")

            print(f"[API] Loaded {len(loaded_tables)} tables with {total_records} records")

            # Save profiles to disk (using shared instance)
            profile_store.save_profiles()

            # Update app_state metadata DIRECTLY (no need to reload from disk)
            sheet_names = list(tables.keys())
            detected_tables = []
            for table_name in loaded_tables:
                detected_tables.append({
                    "table_id": table_name,
                    "title": table_name,
                    "sheet_name": table_name,
                    "source_id": f"upload#{table_name}",
                    "sheet_hash": "",
                    "row_range": (0, 0),
                    "col_range": (0, 0),
                    "total_rows": 0
                })

            # Update app_state with new metadata
            app_state.total_records = int(total_records)
            app_state.detected_tables = detected_tables
            app_state.original_sheet_names = sheet_names
            app_state.data_loaded = True
            print(f"[API] Updated app_state: {len(loaded_tables)} tables, {total_records} records")

            return {
                "success": True,
                "stats": {
                    "totalTables": len(loaded_tables),
                    "totalRecords": int(total_records),
                    "sheetCount": len(sheet_names),
                    "sheets": sheet_names,
                    "detectedTables": detected_tables,
                    "profiledTables": len(loaded_tables)
                }
            }

        finally:
            # Clean up temp file
            try:
                os.unlink(temp_path)
            except Exception:
                pass

    except HTTPException:
        raise
    except Exception as e:
        print(f"[API] Exception in upload_file: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/sync-folder")
async def sync_folder_endpoint(request: LoadDataRequest, user: dict = Depends(require_auth)):
    """
    Sync all CSV/Excel files from a Google Drive folder.

    Usage:
        POST /api/sync-folder
        {"url": "https://drive.google.com/drive/folders/ABC123"}

    The folder must be shared with "Anyone with link" permission.
    All CSV and Excel files in the folder will be loaded.

    Query params:
        append: If true, append to existing data. Default: false (replace)
    """
    try:
        print(f"[API] sync-folder for URL: {request.url}")

        if not request.url or not request.url.strip():
            raise HTTPException(status_code=400, detail="Folder URL is required")

        # SSRF Prevention: Validate URL domain
        validate_url_for_ssrf(request.url)

        # Sync the folder
        result = sync_drive_folder(request.url, replace=not request.append)

        if not result.get('success'):
            error_msg = result.get('error', 'Failed to sync folder')
            print(f"[API] Sync failed: {error_msg}")
            raise HTTPException(status_code=422, detail=error_msg)

        return result

    except HTTPException:
        raise
    except Exception as e:
        print(f"[API] Exception in sync_folder: {str(e)}")
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

            # Get drive folder URL from settings if in demo mode
            drive_folder_url = None
            is_demo_mode = False
            try:
                from utils.config_loader import get_config
                config = get_config()
                # Config is a dataclass, use attribute access not .get()
                demo_mode_config = config.google_sheets.demo_mode
                if demo_mode_config and demo_mode_config.enabled:
                    is_demo_mode = True
                    drive_folder_url = demo_mode_config.drive_folder_url
            except Exception as e:
                print(f"[API] Could not get demo mode config: {e}")
                pass

            return {
                "loaded": True,
                "demo_mode": is_demo_mode,
                "total_tables": len(profiles),
                "tables": list(profiles.keys()),  # DuckDB table names (for reference)
                # Rich metadata for UI display
                "original_sheets": app_state.original_sheet_names,
                "total_records": app_state.total_records,
                "detected_tables": app_state.detected_tables,
                "loaded_spreadsheets": app_state.loaded_spreadsheet_ids,
                "drive_folder_url": drive_folder_url
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

        print(f"[API] POST /api/query - Body: {{'text': '{request.text[:50]}...'}}")
        print(f"[API] Query: {request.text[:80]}...")

        # Pass conversation_id and user_name if provided
        conversation_id = getattr(request, 'conversation_id', None)
        user_name = getattr(request, 'user_name', None)
        result = process_query_service(request.text, conversation_id, user_name)

        if result.get('success'):
            print(f"[API] Query success - Table: {result.get('table_used')}, "
                  f"Confidence: {result.get('routing_confidence', 0):.0%}")
        else:
            error_msg = result.get('error', 'Query processing failed')
            print(f"[API] Query failed: {error_msg}")
            # Note: Query failures (no data found, etc.) return 200 with success=false
            # This is intentional - the client request was valid, just no data matched

        # DEBUG: Add server identifier to help trace which backend is responding
        result['debug_server'] = 'hf-space-thara-backend-v2'
        result['debug_data_count'] = len(result.get('data') or [])
        return result
    except HTTPException:
        raise  # Re-raise HTTPExceptions as-is
    except Exception as e:
        import traceback
        # Log full query context for debugging
        print(f"[API] ===== QUERY ERROR =====")
        print(f"[API] Query text: {request.text}")
        print(f"[API] Conversation ID: {getattr(request, 'conversation_id', 'N/A')}")
        print(f"[API] Exception: {str(e)}")
        print(f"[API] Traceback:")
        traceback.print_exc()
        print(f"[API] =========================")
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


@app.post("/api/text-to-speech/stream")
async def text_to_speech_stream_endpoint(request: dict, user: dict = Depends(require_auth)):
    """
    Convert text to speech with STREAMING output.
    First audio chunk arrives in ~200-500ms instead of waiting 2-4s.
    Enables immediate playback while audio is still being generated.
    """
    try:
        from utils.voice_utils import text_to_speech_streaming, get_default_voice_id

        text = request.get("text", "")
        voice_id = request.get("voice_id") or get_default_voice_id()

        if not text:
            raise HTTPException(status_code=400, detail="Text is required")

        print(f"[API] TTS STREAM with voice {voice_id}: {text[:50]}...")

        def generate():
            for chunk in text_to_speech_streaming(text, voice_id=voice_id):
                yield chunk

        return StreamingResponse(
            generate(),
            media_type="audio/mpeg",
            headers={
                "Content-Disposition": "attachment; filename=speech.mp3",
                "Transfer-Encoding": "chunked"
            }
        )
    except Exception as e:
        print(f"[API] Exception in text_to_speech_stream: {str(e)}")
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
    Credentials are read from environment variables:
    - ADMIN_USERNAME (required)
    - ADMIN_PASSWORD (required)
    """
    username = request.get("username", "")
    password = request.get("password", "")

    # Admin credentials from environment variables (NEVER hardcode these)
    admin_username = os.getenv("ADMIN_USERNAME")
    admin_password = os.getenv("ADMIN_PASSWORD")

    if not admin_username or not admin_password:
        print("[Auth] WARNING: ADMIN_USERNAME or ADMIN_PASSWORD not set in environment!")
        raise HTTPException(status_code=500, detail="Server authentication not configured")

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
                status_code=503,  # Service Unavailable
                detail="Google Sheets OAuth is not configured on this server. Contact the administrator."
            )

        # Get user from auth
        user = await verify_auth_token(request)
        user_id = user.get("id", "dev-user") if user else "dev-user"

        url = get_gsheet_oauth_url(user_id)

        if not url:
            raise HTTPException(
                status_code=500,
                detail="Failed to generate authorization URL. Please try again."
            )

        return {"url": url, "user_id": user_id}
    except HTTPException:
        raise
    except Exception as e:
        print(f"[Sheets Auth] OAuth URL error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail="Failed to start Google Sheets authorization. Please try again later."
        )


@app.post("/api/auth/sheets/callback")
async def sheets_oauth_callback(request: dict, req: Request):
    """Handle Google Sheets OAuth callback."""
    try:
        from utils.gsheet_oauth import exchange_code_for_tokens

        code = request.get("code")
        error = request.get("error")

        # Handle OAuth error responses (user denied access, etc.)
        if error:
            error_description = request.get("error_description", "Unknown error")
            print(f"[Sheets Auth] OAuth error: {error} - {error_description}")
            raise HTTPException(
                status_code=400,
                detail=f"Authorization failed: {error_description}"
            )

        if not code:
            raise HTTPException(status_code=400, detail="Authorization code required")

        # Get user from auth
        user = await verify_auth_token(req)
        user_id = user.get("id", "dev-user") if user else "dev-user"

        result = exchange_code_for_tokens(code, user_id)

        # Check if token exchange was successful
        if not result.get("success", False):
            error_msg = result.get("error", "Token exchange failed")
            print(f"[Sheets Auth] Token exchange failed: {error_msg}")
            raise HTTPException(status_code=400, detail=error_msg)

        return result
    except HTTPException:
        raise
    except ValueError as e:
        # Handle specific validation errors
        print(f"[Sheets Auth] Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"[Sheets Auth] Callback error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail="Failed to complete Google Sheets authorization. Please try again."
        )


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
        print(f"  [WARN]  Config validation error: {e}")

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

    # === DEMO MODE: Auto-load from Google Drive folder on startup ===
    try:
        from utils.config_loader import get_config
        from api.services import load_dataset_service, sync_drive_folder, app_state
        config = get_config()

        # Check if demo_mode is configured in settings.yaml
        demo_mode = config.google_sheets.demo_mode

        if demo_mode and demo_mode.enabled:
            # Check for Google Drive folder URL first (new plug-and-play mode)
            drive_folder_url = getattr(demo_mode, 'drive_folder_url', None)

            if drive_folder_url:
                print()
                print("  [DEMO MODE] Checking Google Drive folder...")
                print(f"    Folder: {drive_folder_url[:60]}...")
                try:
                    # Check if folder has changes before syncing
                    from data_sources.connectors.gdrive_folder_connector import GoogleDriveFolderConnector
                    connector = GoogleDriveFolderConnector(drive_folder_url)

                    # Only sync if data not loaded OR folder has changes
                    if not app_state.data_loaded or connector.has_changes():
                        print("  [DEMO MODE] Syncing from Google Drive folder...")
                        result = sync_drive_folder(drive_folder_url, replace=True)

                        if result.get('success'):
                            files = result.get('files_loaded', [])
                            stats = result.get('stats', {})
                            tables = stats.get('totalTables', 0)
                            records = stats.get('totalRecords', 0)
                            print(f"    [OK] Loaded {len(files)} files: {', '.join(files)}")
                            print(f"    [OK] Total: {tables} tables, {records:,} records")
                        else:
                            print(f"    [FAIL] Failed: {result.get('error', 'Unknown error')}")
                    else:
                        print("    [OK] No changes detected - using cached data")

                except Exception as e:
                    print(f"    [FAIL] Error syncing folder: {e}")
                    import traceback
                    traceback.print_exc()

                print("  [DEMO MODE] Folder sync complete!")
                print()

            # Fallback to legacy spreadsheet IDs if no folder URL
            else:
                auto_load_ids = getattr(demo_mode, 'auto_load_spreadsheets', [])

                if auto_load_ids:
                    print()
                    print("  [DEMO MODE] Auto-loading spreadsheets...")
                    for idx, sheet_id in enumerate(auto_load_ids, 1):
                        try:
                            sheets_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}"
                            print(f"    [{idx}/{len(auto_load_ids)}] Loading {sheet_id[:20]}...")
                            result = load_dataset_service(sheets_url, user_id=None, append=(idx > 1))

                            if result.get('success'):
                                stats = result.get('stats', {})
                                tables = stats.get('totalTables', 0) if stats else 0
                                sheets = stats.get('sheetCount', 0) if stats else 0
                                print(f"    [{idx}/{len(auto_load_ids)}] [OK] Loaded {tables} tables from {sheets} sheets")
                            else:
                                print(f"    [{idx}/{len(auto_load_ids)}] [FAIL] Failed: {result.get('error', 'Unknown error')}")
                        except Exception as e:
                            print(f"    [{idx}/{len(auto_load_ids)}] [FAIL] Error: {e}")

                    print("  [DEMO MODE] Auto-load complete!")
                    print()
    except Exception as e:
        print(f"  WARNING: Demo mode auto-load failed: {e}")
        import traceback
        traceback.print_exc()

    # Ensure snapshots directory exists (prevents confusing DuckDB errors)
    snapshots_dir = _BACKEND_DIR / "data_sources" / "snapshots"
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
