"""
Google Sheets OAuth Module
Handles OAuth 2.0 authentication for Google Sheets access.

This allows users to authorize access to their own Google Sheets
without requiring a service account.
"""

import os
import json
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GSHEET_OAUTH_REDIRECT_URL = os.getenv(
    "GSHEET_OAUTH_REDIRECT_URL",
    "https://thara-ai.vercel.app/auth/sheets-callback"
)

# Token storage directory
TOKEN_STORAGE_DIR = Path(__file__).parent.parent / "credentials" / "user_tokens"

# Google Sheets scopes
GSHEET_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/drive.readonly"
]


def ensure_token_dir():
    """Ensure token storage directory exists"""
    TOKEN_STORAGE_DIR.mkdir(parents=True, exist_ok=True)


def get_token_path(user_id: str) -> Path:
    """Get token file path for a user"""
    ensure_token_dir()
    # Sanitize user_id for filesystem
    safe_id = "".join(c for c in user_id if c.isalnum() or c in "-_")
    return TOKEN_STORAGE_DIR / f"{safe_id}_sheets_token.json"


def check_gsheet_oauth_configured() -> bool:
    """Check if Google Sheets OAuth is configured"""
    return bool(GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET)


def get_gsheet_oauth_url(user_id: str, state: str = None) -> str:
    """
    Get Google OAuth URL for Sheets access.

    Args:
        user_id: User's ID (from Supabase auth)
        state: Optional state parameter for CSRF protection

    Returns:
        OAuth authorization URL
    """
    if not check_gsheet_oauth_configured():
        raise ValueError(
            "Google Sheets OAuth not configured. "
            "Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET environment variables."
        )

    from urllib.parse import urlencode

    # Build OAuth URL
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": GSHEET_OAUTH_REDIRECT_URL,
        "response_type": "code",
        "scope": " ".join(GSHEET_SCOPES),
        "access_type": "offline",  # Request refresh token
        "prompt": "consent",  # Always show consent screen to get refresh token
        "state": state or user_id  # Use user_id as state if not provided
    }

    base_url = "https://accounts.google.com/o/oauth2/v2/auth"
    return f"{base_url}?{urlencode(params)}"


def exchange_code_for_tokens(code: str, user_id: str) -> Dict[str, Any]:
    """
    Exchange authorization code for access and refresh tokens.

    Args:
        code: Authorization code from OAuth callback
        user_id: User's ID to associate tokens with

    Returns:
        Token response with access_token, refresh_token, etc.
    """
    if not check_gsheet_oauth_configured():
        raise ValueError("Google Sheets OAuth not configured")

    import requests

    token_url = "https://oauth2.googleapis.com/token"

    response = requests.post(token_url, data={
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": GSHEET_OAUTH_REDIRECT_URL
    })

    if response.status_code != 200:
        error = response.json()
        raise ValueError(f"Token exchange failed: {error.get('error_description', error)}")

    token_data = response.json()

    # Calculate expiry time
    expires_in = token_data.get("expires_in", 3600)
    expiry_time = datetime.utcnow() + timedelta(seconds=expires_in)

    # Store tokens
    stored_data = {
        "access_token": token_data["access_token"],
        "refresh_token": token_data.get("refresh_token"),
        "token_type": token_data.get("token_type", "Bearer"),
        "expires_at": expiry_time.isoformat(),
        "scope": token_data.get("scope", ""),
        "created_at": datetime.utcnow().isoformat(),
        "user_id": user_id
    }

    save_user_tokens(user_id, stored_data)

    return {
        "success": True,
        "message": "Google Sheets access authorized",
        "expires_in": expires_in
    }


def refresh_access_token(user_id: str) -> Optional[str]:
    """
    Refresh an expired access token.

    Args:
        user_id: User's ID

    Returns:
        New access token or None if refresh failed
    """
    tokens = load_user_tokens(user_id)
    if not tokens or not tokens.get("refresh_token"):
        return None

    if not check_gsheet_oauth_configured():
        return None

    import requests

    token_url = "https://oauth2.googleapis.com/token"

    response = requests.post(token_url, data={
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "refresh_token": tokens["refresh_token"],
        "grant_type": "refresh_token"
    })

    if response.status_code != 200:
        print(f"[GSheet OAuth] Token refresh failed: {response.text}")
        return None

    token_data = response.json()

    # Update stored tokens
    expires_in = token_data.get("expires_in", 3600)
    expiry_time = datetime.utcnow() + timedelta(seconds=expires_in)

    tokens["access_token"] = token_data["access_token"]
    tokens["expires_at"] = expiry_time.isoformat()

    # Refresh token might be rotated
    if "refresh_token" in token_data:
        tokens["refresh_token"] = token_data["refresh_token"]

    save_user_tokens(user_id, tokens)

    return token_data["access_token"]


def save_user_tokens(user_id: str, tokens: Dict[str, Any]):
    """Save user's OAuth tokens to file"""
    token_path = get_token_path(user_id)

    with open(token_path, 'w') as f:
        json.dump(tokens, f, indent=2)

    print(f"[GSheet OAuth] Saved tokens for user: {user_id}")


def load_user_tokens(user_id: str) -> Optional[Dict[str, Any]]:
    """Load user's OAuth tokens from file"""
    token_path = get_token_path(user_id)

    if not token_path.exists():
        return None

    try:
        with open(token_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"[GSheet OAuth] Error loading tokens: {e}")
        return None


def get_valid_access_token(user_id: str) -> Optional[str]:
    """
    Get a valid access token for the user, refreshing if needed.

    Args:
        user_id: User's ID

    Returns:
        Valid access token or None if not available
    """
    tokens = load_user_tokens(user_id)
    if not tokens:
        return None

    # Check if token is expired
    expires_at = tokens.get("expires_at")
    if expires_at:
        expiry_time = datetime.fromisoformat(expires_at)
        # Refresh if expiring in next 5 minutes
        if datetime.utcnow() >= expiry_time - timedelta(minutes=5):
            print(f"[GSheet OAuth] Token expired/expiring, refreshing...")
            return refresh_access_token(user_id)

    return tokens.get("access_token")


def has_sheets_access(user_id: str) -> bool:
    """Check if user has authorized Google Sheets access"""
    return get_valid_access_token(user_id) is not None


def revoke_access(user_id: str) -> bool:
    """
    Revoke user's Google Sheets access.

    Args:
        user_id: User's ID

    Returns:
        True if revoked successfully
    """
    tokens = load_user_tokens(user_id)
    if not tokens:
        return True  # Nothing to revoke

    access_token = tokens.get("access_token")

    if access_token:
        import requests
        try:
            # Revoke token with Google
            requests.post(
                "https://oauth2.googleapis.com/revoke",
                params={"token": access_token}
            )
        except Exception as e:
            print(f"[GSheet OAuth] Error revoking token: {e}")

    # Remove token file
    token_path = get_token_path(user_id)
    if token_path.exists():
        token_path.unlink()

    print(f"[GSheet OAuth] Revoked access for user: {user_id}")
    return True


def get_gspread_credentials(user_id: str):
    """
    Get gspread-compatible credentials from user's OAuth token.

    Args:
        user_id: User's ID

    Returns:
        google.oauth2.credentials.Credentials object for gspread
    """
    access_token = get_valid_access_token(user_id)
    if not access_token:
        raise ValueError("No valid access token. User needs to authorize Google Sheets access.")

    tokens = load_user_tokens(user_id)

    from google.oauth2.credentials import Credentials

    credentials = Credentials(
        token=access_token,
        refresh_token=tokens.get("refresh_token"),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        scopes=GSHEET_SCOPES
    )

    return credentials
