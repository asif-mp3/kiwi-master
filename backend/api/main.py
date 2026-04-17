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
from fastapi.responses import Response, StreamingResponse, JSONResponse
import tempfile
import os
import time
from collections import defaultdict
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
from utils.logger import get_logger, setup_logging

setup_logging()
logger = get_logger("api")

# ── Sentry Error Tracking ────────────────────────────────────────────────────
SENTRY_DSN = os.getenv("SENTRY_DSN")
if SENTRY_DSN:
    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.starlette import StarletteIntegration

        sentry_sdk.init(
            dsn=SENTRY_DSN,
            integrations=[FastApiIntegration(), StarletteIntegration()],
            traces_sample_rate=float(os.getenv("SENTRY_TRACES_RATE", "0.1")),
            environment=os.getenv("ENVIRONMENT", "production"),
            send_default_pii=False,
        )
        logger.info("Sentry error tracking initialized")
    except ImportError:
        logger.warning("sentry-sdk not installed — error tracking disabled")
    except Exception as e:
        logger.warning("Sentry init failed: %s", e)

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
# Global Exception Handler
# =============================================================================

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch-all handler to prevent raw 500 errors from leaking to clients."""
    logger.error(
        "Unhandled exception on %s %s: %s",
        request.method, request.url.path, exc,
        exc_info=True,
    )
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "An internal error occurred. Please try again.",
        },
    )


# =============================================================================
# Rate Limiting Middleware
# =============================================================================

class _RateLimitState:
    """Simple in-memory sliding-window rate limiter (per IP)."""

    def __init__(self, max_requests: int = 60, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window = window_seconds
        self._hits: dict[str, list[float]] = defaultdict(list)

    def is_allowed(self, key: str) -> bool:
        now = time.time()
        window_start = now - self.window
        # Prune old entries
        self._hits[key] = [t for t in self._hits[key] if t > window_start]
        if len(self._hits[key]) >= self.max_requests:
            return False
        self._hits[key].append(now)
        return True


_rate_limiter = _RateLimitState(
    max_requests=int(os.getenv("RATE_LIMIT_RPM", "60")),
    window_seconds=60,
)

# Paths exempt from rate limiting
_RATE_LIMIT_EXEMPT = {"/", "/api/health", "/api/auth/check"}


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    """Enforce per-IP rate limiting on non-exempt endpoints."""
    if request.url.path not in _RATE_LIMIT_EXEMPT:
        client_ip = request.client.host if request.client else "unknown"
        if not _rate_limiter.is_allowed(client_ip):
            logger.warning("Rate limit exceeded for %s on %s", client_ip, request.url.path)
            return JSONResponse(
                status_code=429,
                content={"success": False, "error": "Too many requests. Please slow down."},
                headers={"Retry-After": "60"},
            )
    return await call_next(request)


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
        logger.warning("SKIP_AUTH=true ignored - only allowed in development environment!")
        logger.warning("Set ENVIRONMENT=development to enable auth bypass.")
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
        logger.error("Token verification error: %s", e)
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
            logger.debug("%s %s - Body: %s", request.method, request.url.path, log_body)
        except (json.JSONDecodeError, UnicodeDecodeError):
            logger.debug("%s %s - Body: (binary data)", request.method, request.url.path)

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
    # Google
    "docs.google.com",
    "drive.google.com",
    "sheets.googleapis.com",
    "www.googleapis.com",
    # Dropbox
    "www.dropbox.com",
    "dropbox.com",
    "dl.dropboxusercontent.com",
    # OneDrive / SharePoint
    "onedrive.live.com",
    "1drv.ms",
    "sharepoint.com",
    "api.onedrive.com",
    # Direct file URLs (common hosting)
    "raw.githubusercontent.com",
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
                detail=f"Domain not allowed: {hostname}. Supported: Google Sheets/Drive, Dropbox, OneDrive, SharePoint."
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
        logger.info("load-dataset for URL: %s (append=%s)", request.url, request.append)

        # Validate URL
        if not request.url or not request.url.strip():
            raise HTTPException(status_code=400, detail="URL is required")

        # Get user ID for OAuth credentials
        user_id = user.get("id") if user else None

        result = load_dataset_service(request.url, user_id=user_id, append=request.append)

        if not result.get('success'):
            error_msg = result.get('error', 'Failed to load dataset')
            logger.error("Load failed: %s", error_msg)
            # Return proper HTTP status code for failures
            raise HTTPException(status_code=422, detail=error_msg)

        return result
    except HTTPException:
        raise  # Re-raise HTTPExceptions as-is
    except Exception as e:
        logger.error("Exception in load_dataset: %s", e, exc_info=True)
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
        logger.info("load-source for URL: %s (append=%s)", request.url, request.append)

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
            logger.error("Load source failed: %s", error_msg)
            raise HTTPException(status_code=422, detail=error_msg)

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Exception in load_source: %s", e, exc_info=True)
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
        logger.info("upload-file: %s (append=%s)", file.filename, append)

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

        logger.debug("Saved upload to: %s", temp_path)

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
                logger.info("Replace mode: deleting existing tables and profiles...")

                # Get all existing tables from DuckDB
                existing_tables = [row[0] for row in conn.execute("SHOW TABLES").fetchall()]

                # Drop all existing tables
                for old_table in existing_tables:
                    try:
                        conn.execute(f'DROP TABLE IF EXISTS "{old_table}"')
                        logger.debug("Dropped table: %s", old_table)
                    except Exception as drop_err:
                        logger.warning("Could not drop %s: %s", old_table, drop_err)

                # Clear all profiles
                profile_store.clear_profiles()
                logger.info("Cleared %d existing tables and profiles", len(existing_tables))

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
                        logger.warning("Could not profile %s: %s", full_table_name, profile_err)

            logger.info("Loaded %d tables with %d records", len(loaded_tables), total_records)

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
            logger.info("Updated app_state: %d tables, %d records", len(loaded_tables), total_records)

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
        logger.error("Exception in upload_file: %s", e, exc_info=True)
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
        logger.info("sync-folder for URL: %s", request.url)

        if not request.url or not request.url.strip():
            raise HTTPException(status_code=400, detail="Folder URL is required")

        # SSRF Prevention: Validate URL domain
        validate_url_for_ssrf(request.url)

        # Sync the folder
        result = sync_drive_folder(request.url, replace=not request.append)

        if not result.get('success'):
            error_msg = result.get('error', 'Failed to sync folder')
            logger.error("Sync failed: %s", error_msg)
            raise HTTPException(status_code=422, detail=error_msg)

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Exception in sync_folder: %s", e, exc_info=True)
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
                logger.debug("Could not get demo mode config: %s", e)
                pass

            # Build lightweight profile summaries for frontend visualization
            table_profiles_summary = []
            for table_name, profile in profiles.items():
                columns = profile.get('columns', {})
                metrics = [c for c, info in columns.items() if info.get('role') == 'metric']
                dimensions = [c for c, info in columns.items() if info.get('role') == 'dimension']
                date_cols = [c for c, info in columns.items() if info.get('role') == 'date']
                identifiers = [c for c, info in columns.items() if info.get('role') == 'identifier']
                table_profiles_summary.append({
                    "name": table_name,
                    "table_type": profile.get('table_type', 'unknown'),
                    "row_count": profile.get('row_count', 0),
                    "column_count": profile.get('column_count', len(columns)),
                    "metrics": metrics,
                    "dimensions": dimensions,
                    "date_columns": date_cols,
                    "identifiers": identifiers,
                    "date_range": profile.get('date_range') if profile.get('date_range', {}).get('min') else None,
                    "granularity": profile.get('granularity', 'unknown'),
                    "data_quality_score": round(profile.get('data_quality_score', 0), 2),
                })

            # Detect source type for UI display
            source_type = "demo" if is_demo_mode else "unknown"
            try:
                from data_sources.source_registry import SourceRegistry
                registry = SourceRegistry()
                sources = registry.list_sources()
                if sources:
                    source_type = sources[0].connector_type
            except Exception:
                pass

            return {
                "loaded": True,
                "demo_mode": is_demo_mode,
                "total_tables": len(profiles),
                "tables": list(profiles.keys()),
                "original_sheets": app_state.original_sheet_names,
                "total_records": app_state.total_records,
                "detected_tables": app_state.detected_tables,
                "loaded_spreadsheets": app_state.loaded_spreadsheet_ids,
                "drive_folder_url": drive_folder_url,
                "smart_suggestions": app_state.get_smart_suggestions(),
                "table_profiles_summary": table_profiles_summary,
                "source_type": source_type,
            }
        return {
            "loaded": False,
            "demo_mode": False,
            "loading_status": app_state.loading_status,
            "startup_error": app_state.startup_error,
            "default_source_url": app_state.default_source_url,
        }
    except Exception as e:
        logger.error("Error checking dataset status: %s", e)
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

        logger.info("POST /api/query - text: %s...", request.text[:50])
        logger.debug("Query: %s...", request.text[:80])

        # Pass conversation_id and user_name if provided
        conversation_id = getattr(request, 'conversation_id', None)
        user_name = getattr(request, 'user_name', None)
        result = process_query_service(request.text, conversation_id, user_name)

        if result.get('success'):
            logger.info("Query success - Table: %s, Confidence: %.0f%%",
                        result.get('table_used'), (result.get('routing_confidence', 0) * 100))
        else:
            error_msg = result.get('error', 'Query processing failed')
            logger.warning("Query failed: %s", error_msg)
            # Note: Query failures (no data found, etc.) return 200 with success=false
            # This is intentional - the client request was valid, just no data matched

        # DEBUG: Add server identifier to help trace which backend is responding
        result['debug_server'] = 'hf-space-thara-backend-v2'
        result['debug_data_count'] = len(result.get('data') or [])
        return result
    except HTTPException:
        raise  # Re-raise HTTPExceptions as-is
    except Exception as e:
        # Log full query context for debugging
        logger.error("QUERY ERROR - text: %s, conversation_id: %s, exception: %s",
                     request.text, getattr(request, 'conversation_id', 'N/A'), e,
                     exc_info=True)
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
        logger.error("Exception in transcribe_audio: %s", e, exc_info=True)
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

        logger.info("TTS with voice %s: %s...", voice_id, text[:50])
        audio_bytes = text_to_speech(text, voice_id=voice_id)
        logger.debug("Generated %d bytes of audio", len(audio_bytes))

        return Response(
            content=audio_bytes,
            media_type="audio/mpeg",
            headers={"Content-Disposition": "attachment; filename=speech.mp3"}
        )
    except Exception as e:
        logger.error("Exception in text_to_speech: %s", e, exc_info=True)
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

        logger.info("TTS STREAM with voice %s: %s...", voice_id, text[:50])

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
        logger.error("Exception in text_to_speech_stream: %s", e, exc_info=True)
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
        logger.warning("ADMIN_USERNAME or ADMIN_PASSWORD not set in environment!")
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
        logger.error("Sheets Auth check error: %s", e)
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
        logger.error("Sheets Auth OAuth URL error: %s", e, exc_info=True)
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
            logger.error("Sheets Auth OAuth error: %s - %s", error, error_description)
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
            logger.error("Sheets Auth token exchange failed: %s", error_msg)
            raise HTTPException(status_code=400, detail=error_msg)

        return result
    except HTTPException:
        raise
    except ValueError as e:
        # Handle specific validation errors
        logger.error("Sheets Auth validation error: %s", e)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Sheets Auth callback error: %s", e, exc_info=True)
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
        logger.error("Sheets Auth revoke error: %s", e)
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
        logger.error("Exception in start_onboarding: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/onboarding/input")
async def process_onboarding_input(request: dict):
    """Process user input during onboarding."""
    try:
        user_input = request.get("input", "")
        return process_onboarding_input_service(user_input)
    except Exception as e:
        logger.error("Exception in process_onboarding_input: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Debug/Admin Endpoints
# =============================================================================

@app.get("/api/debug/routing")
async def debug_routing(question: str, user: dict = Depends(require_auth)):
    """
    Debug endpoint to see how a question would be routed.
    Shows table selection reasoning. Requires authentication.
    """
    try:
        return get_routing_debug_service(question)
    except Exception as e:
        logger.error("Exception in debug_routing: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/debug/profiles")
async def debug_profiles(user: dict = Depends(require_auth)):
    """
    Get all table profiles for inspection.
    Shows how tables are profiled for routing. Requires authentication.
    """
    try:
        return get_table_profiles_service()
    except Exception as e:
        logger.error("Exception in debug_profiles: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/context/clear")
async def clear_context(request: dict = None):
    """Clear conversation context."""
    try:
        conversation_id = request.get("conversation_id") if request else None
        return clear_context_service(conversation_id)
    except Exception as e:
        logger.error("Exception in clear_context: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Loading Progress (SSE) & Default Source Management
# =============================================================================

@app.get("/api/loading-progress")
async def loading_progress():
    """
    Server-Sent Events endpoint for real-time loading progress.
    Frontend subscribes to this to show a loading overlay with progress bar.
    """
    import asyncio
    import json

    from api.services import app_state

    async def event_stream():
        while True:
            status = app_state.loading_status
            yield f"data: {json.dumps(status)}\n\n"
            if status.get("complete") or status.get("phase") == "error":
                break
            await asyncio.sleep(0.5)

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.post("/api/reset-to-default")
async def reset_to_default(user: dict = Depends(require_auth)):
    """
    Reset data to default Drive folder source.
    Used when user disconnects all sources and wants to go back to demo data.
    """
    try:
        from api.services import app_state

        drive_folder_url = os.getenv("DEFAULT_DRIVE_FOLDER_URL", "").strip()
        if not drive_folder_url:
            raise HTTPException(status_code=400, detail="No default data source configured")

        app_state.update_loading_status("connecting", "Resetting to default data source...", 5)
        result = sync_drive_folder(drive_folder_url, replace=True)

        if result.get("success"):
            app_state.default_source_url = drive_folder_url
            app_state.is_default_source = True
            app_state.startup_error = None
            app_state.update_loading_status("ready", "Default data restored!", 100, complete=True)
            return {"success": True, **result}
        else:
            error = result.get("error", "Failed to sync default folder")
            app_state.update_loading_status("error", error, 0, error=error)
            raise HTTPException(status_code=422, detail=error)

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Exception in reset_to_default: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Lifecycle Events
# =============================================================================

@app.on_event("startup")
async def startup_event():
    """Initialize resources on startup"""
    logger.info("---")
    logger.info("Kiwi-RAG API v2.0 - Starting up...")
    logger.info("---")
    logger.info("Features: Intelligent Routing, Self-Healing, Thara Personality, Conversation Context, Tamil Support")
    logger.info("Endpoints: /api/load-dataset, /api/query, /api/transcribe, /api/text-to-speech, /api/onboarding/start, /api/debug/routing, /api/debug/profiles, /api/health")
    logger.info("CORS: %s...", ', '.join(ALLOWED_ORIGINS[:2]))
    logger.info("Auth: %s", 'DISABLED (dev mode)' if _is_skip_auth_allowed() else 'ENABLED')

    from api.services import app_state

    # Validate configuration and API keys
    try:
        from utils.config_loader import print_startup_validation, validate_api_keys
        print_startup_validation()

        # Phase 6: Validate Gemini API key at startup
        api_keys = validate_api_keys()
        app_state.gemini_available = api_keys.get("GEMINI_API_KEY", False)
        if app_state.gemini_available:
            logger.info("Gemini API: AVAILABLE")
        else:
            logger.warning("Gemini API: NOT AVAILABLE - LLM features disabled")
    except Exception as e:
        logger.warning("Config validation error: %s", e)

    # Pre-load spreadsheet_id from config to enable caching
    try:
        from utils.config_loader import get_config
        config = get_config()
        spreadsheet_id = config.google_sheets.spreadsheet_id
        if spreadsheet_id:
            app_state.current_spreadsheet_id = spreadsheet_id
            logger.info("Spreadsheet ID: %s... (from config)", spreadsheet_id[:25])
            logger.info("Cache: 300s TTL enabled")
        else:
            logger.warning("No spreadsheet_id in config - cache disabled")
    except Exception as e:
        logger.warning("Could not pre-load spreadsheet_id: %s", e)

    # === DEFAULT DATA SOURCE: Auto-load from env var or demo_mode config ===
    try:
        from utils.config_loader import get_config
        config = get_config()

        # Priority 1: DEFAULT_DRIVE_FOLDER_URL environment variable
        drive_folder_url = os.getenv("DEFAULT_DRIVE_FOLDER_URL", "").strip()

        # Priority 2: demo_mode.drive_folder_url in settings.yaml
        demo_mode = config.google_sheets.demo_mode
        if not drive_folder_url and demo_mode and demo_mode.enabled:
            drive_folder_url = getattr(demo_mode, 'drive_folder_url', None) or ""

        if drive_folder_url:
            app_state.default_source_url = drive_folder_url
            app_state.is_default_source = True
            logger.info("[DEFAULT SOURCE] Folder: %s...", drive_folder_url[:60])

            # Emit loading status for SSE
            app_state.update_loading_status("connecting", "Connecting to default data source...", 5)

            try:
                from data_sources.connectors.gdrive_folder_connector import GoogleDriveFolderConnector
                connector = GoogleDriveFolderConnector(drive_folder_url)

                if not app_state.data_loaded or connector.has_changes():
                    app_state.update_loading_status("fetching", "Syncing from Google Drive folder...", 15)
                    result = sync_drive_folder(drive_folder_url, replace=True)

                    if result.get('success'):
                        files = result.get('files_loaded', [])
                        stats = result.get('stats', {})
                        tables = stats.get('totalTables', 0)
                        records = stats.get('totalRecords', 0)
                        logger.info("[DEFAULT SOURCE] Loaded %d files: %s", len(files), ', '.join(files))
                        logger.info("[DEFAULT SOURCE] Total: %d tables, %d records", tables, records)
                        app_state.startup_error = None
                        app_state.update_loading_status(
                            "ready", f"Ready! {tables} tables loaded.",
                            100, tables_found=tables, total_tables=tables,
                            tables_profiled=tables, complete=True
                        )
                    else:
                        error_msg = result.get('error', 'Unknown error')
                        logger.error("[DEFAULT SOURCE] Failed: %s", error_msg)
                        app_state.startup_error = error_msg
                        app_state.update_loading_status("error", error_msg, 0, error=error_msg)
                else:
                    logger.info("[DEFAULT SOURCE] No changes detected - using cached data")
                    app_state.update_loading_status(
                        "ready", "Data loaded from cache.",
                        100, complete=True
                    )

            except Exception as e:
                error_msg = str(e)
                logger.error("[DEFAULT SOURCE] Error: %s", e, exc_info=True)
                app_state.startup_error = error_msg
                app_state.update_loading_status("error", error_msg, 0, error=error_msg)

        # Fallback to legacy spreadsheet IDs
        elif demo_mode and demo_mode.enabled:
            auto_load_ids = getattr(demo_mode, 'auto_load_spreadsheets', [])
            if auto_load_ids:
                app_state.update_loading_status("connecting", "Auto-loading spreadsheets...", 5)
                logger.info("[DEMO MODE] Auto-loading spreadsheets...")
                for idx, sheet_id in enumerate(auto_load_ids, 1):
                    try:
                        sheets_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}"
                        progress = 5 + int((idx / len(auto_load_ids)) * 90)
                        app_state.update_loading_status(
                            "fetching", f"Loading spreadsheet {idx}/{len(auto_load_ids)}...",
                            progress
                        )
                        result = load_dataset_service(sheets_url, user_id=None, append=(idx > 1))

                        if result.get('success'):
                            stats = result.get('stats', {})
                            tables = stats.get('totalTables', 0) if stats else 0
                            logger.info("[DEMO MODE] [%d/%d] Loaded %d tables", idx, len(auto_load_ids), tables)
                        else:
                            logger.error("[DEMO MODE] [%d/%d] Failed: %s", idx, len(auto_load_ids), result.get('error', 'Unknown'))
                    except Exception as e:
                        logger.error("[DEMO MODE] [%d/%d] Error: %s", idx, len(auto_load_ids), e)

                app_state.update_loading_status("ready", "Auto-load complete!", 100, complete=True)
                logger.info("[DEMO MODE] Auto-load complete!")
    except Exception as e:
        logger.warning("Default source auto-load failed: %s", e, exc_info=True)
        app_state.startup_error = str(e)

    # Ensure snapshots directory exists (prevents confusing DuckDB errors)
    snapshots_dir = _BACKEND_DIR / "data_sources" / "snapshots"
    snapshots_dir.mkdir(parents=True, exist_ok=True)
    logger.info("Snapshots dir: OK")
    logger.info("---")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup resources on shutdown"""
    logger.info("Kiwi-RAG API shutting down...")


if __name__ == "__main__":
    import uvicorn
    host = os.getenv("BACKEND_HOST", "0.0.0.0")
    port = int(os.getenv("BACKEND_PORT", os.getenv("PORT", "8000")))
    uvicorn.run(app, host=host, port=port)
