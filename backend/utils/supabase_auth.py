"""
Supabase Authentication Module
Handles user authentication with Google OAuth.

Supports both:
- Streamlit UI (legacy)
- FastAPI backend (new)
"""

import os
from typing import Optional, Dict, Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
ENABLE_AUTH = os.getenv("ENABLE_AUTH", "false").lower() == "true"
OAUTH_REDIRECT_URL = os.getenv("OAUTH_REDIRECT_URL", "http://localhost:3000/auth/callback")

# Lazy-loaded client
_supabase_client = None


def get_supabase_client():
    """Get or create Supabase client (singleton)"""
    global _supabase_client

    if _supabase_client is None:
        if not SUPABASE_URL or not SUPABASE_ANON_KEY:
            raise ValueError("Supabase credentials not configured. Set SUPABASE_URL and SUPABASE_ANON_KEY environment variables.")

        from supabase import create_client
        _supabase_client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

    return _supabase_client


def check_auth_enabled() -> bool:
    """Check if authentication is enabled"""
    if not SUPABASE_URL or not SUPABASE_ANON_KEY:
        return False
    return ENABLE_AUTH


# =============================================================================
# FastAPI / REST API Functions
# =============================================================================

def verify_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Verify JWT token from Supabase.

    Args:
        token: Bearer token (with or without 'Bearer ' prefix)

    Returns:
        User info dict if valid, None if invalid
    """
    if not check_auth_enabled():
        return {"id": "anonymous", "email": "anonymous@local", "name": "Anonymous"}

    try:
        client = get_supabase_client()

        # Remove 'Bearer ' prefix if present
        if token.startswith('Bearer '):
            token = token[7:]

        # Verify token and get user
        user_response = client.auth.get_user(token)

        if user_response and user_response.user:
            user = user_response.user
            return {
                'id': user.id,
                'email': user.email,
                'name': user.user_metadata.get('full_name') or user.user_metadata.get('name', 'User'),
                'avatar_url': user.user_metadata.get('avatar_url') or user.user_metadata.get('picture'),
                'metadata': user.user_metadata
            }

        return None

    except Exception as e:
        print(f"[Auth] Token verification failed: {e}")
        return None


def get_google_oauth_url() -> str:
    """
    Get Google OAuth URL for login.

    Returns:
        OAuth authorization URL
    """
    if not check_auth_enabled():
        raise ValueError("Authentication is not enabled")

    try:
        client = get_supabase_client()

        response = client.auth.sign_in_with_oauth({
            "provider": "google",
            "options": {
                "redirect_to": OAUTH_REDIRECT_URL
            }
        })

        return response.url

    except Exception as e:
        print(f"[Auth] Failed to get OAuth URL: {e}")
        raise


def handle_oauth_callback(code: str) -> Dict[str, Any]:
    """
    Handle OAuth callback and exchange code for tokens.

    Args:
        code: Authorization code from OAuth callback

    Returns:
        Dict with access_token, refresh_token, and user info
    """
    if not check_auth_enabled():
        raise ValueError("Authentication is not enabled")

    try:
        client = get_supabase_client()

        # Exchange code for session
        response = client.auth.exchange_code_for_session({"auth_code": code})

        if response and response.session:
            session = response.session
            user = response.user

            return {
                'access_token': session.access_token,
                'refresh_token': session.refresh_token,
                'expires_in': session.expires_in,
                'token_type': 'Bearer',
                'user': {
                    'id': user.id,
                    'email': user.email,
                    'name': user.user_metadata.get('full_name') or user.user_metadata.get('name', 'User'),
                    'avatar_url': user.user_metadata.get('avatar_url') or user.user_metadata.get('picture'),
                }
            }

        raise ValueError("Failed to exchange code for session")

    except Exception as e:
        print(f"[Auth] OAuth callback failed: {e}")
        raise


def refresh_access_token(refresh_token: str) -> Dict[str, Any]:
    """
    Refresh an expired access token.

    Args:
        refresh_token: Refresh token from previous auth

    Returns:
        Dict with new access_token and refresh_token
    """
    if not check_auth_enabled():
        raise ValueError("Authentication is not enabled")

    try:
        client = get_supabase_client()

        response = client.auth.refresh_session(refresh_token)

        if response and response.session:
            session = response.session
            return {
                'access_token': session.access_token,
                'refresh_token': session.refresh_token,
                'expires_in': session.expires_in,
                'token_type': 'Bearer'
            }

        raise ValueError("Failed to refresh token")

    except Exception as e:
        print(f"[Auth] Token refresh failed: {e}")
        raise


def sign_out(access_token: str) -> bool:
    """
    Sign out user and invalidate token.

    Args:
        access_token: User's access token

    Returns:
        True if successful
    """
    try:
        client = get_supabase_client()
        client.auth.sign_out()
        return True
    except Exception as e:
        print(f"[Auth] Sign out failed: {e}")
        return False


# =============================================================================
# User Profile Functions
# =============================================================================

def get_user_profile(user_id: str) -> Optional[Dict[str, Any]]:
    """
    Get user profile from database.

    Args:
        user_id: User's UUID

    Returns:
        Profile dict or None
    """
    try:
        client = get_supabase_client()
        response = client.table('user_profiles').select('*').eq('id', user_id).execute()

        if response.data and len(response.data) > 0:
            return response.data[0]
        return None

    except Exception as e:
        print(f"[Auth] Failed to get user profile: {e}")
        return None


def create_user_profile(user_id: str, email: str, name: str = None,
                       avatar_url: str = None) -> Optional[Dict[str, Any]]:
    """
    Create user profile in database.

    Args:
        user_id: User's UUID
        email: User's email
        name: User's display name
        avatar_url: User's avatar URL

    Returns:
        Created profile dict or None
    """
    try:
        client = get_supabase_client()

        profile_data = {
            'id': user_id,
            'email': email,
            'full_name': name or 'User',
            'avatar_url': avatar_url,
            'preferences': {}
        }

        response = client.table('user_profiles').insert(profile_data).execute()

        if response.data:
            return response.data[0]
        return None

    except Exception as e:
        print(f"[Auth] Failed to create user profile: {e}")
        return None


def update_user_profile(user_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Update user profile.

    Args:
        user_id: User's UUID
        updates: Dict of fields to update

    Returns:
        Updated profile dict or None
    """
    try:
        client = get_supabase_client()

        response = client.table('user_profiles').update(updates).eq('id', user_id).execute()

        if response.data:
            return response.data[0]
        return None

    except Exception as e:
        print(f"[Auth] Failed to update user profile: {e}")
        return None


# =============================================================================
# Streamlit-Specific Functions (Legacy Support)
# =============================================================================

def init_streamlit_auth():
    """Initialize authentication for Streamlit app"""
    try:
        import streamlit as st

        if 'auth_initialized' not in st.session_state:
            st.session_state.auth_initialized = True
            st.session_state.authenticated = False
            st.session_state.user = None
            st.session_state.user_profile = None

    except ImportError:
        pass  # Streamlit not available


def get_streamlit_supabase_client():
    """Get Supabase client with Streamlit caching"""
    try:
        import streamlit as st

        @st.cache_resource
        def _get_client():
            return get_supabase_client()

        return _get_client()

    except ImportError:
        return get_supabase_client()


def streamlit_logout():
    """Logout user in Streamlit context"""
    try:
        import streamlit as st

        try:
            client = get_supabase_client()
            client.auth.sign_out()
        except:
            pass

        st.session_state.authenticated = False
        st.session_state.user = None
        st.session_state.user_profile = None

        if 'messages' in st.session_state:
            st.session_state.messages = []

        st.rerun()

    except ImportError:
        pass


def get_streamlit_user_id() -> Optional[str]:
    """Get current user ID in Streamlit context"""
    try:
        import streamlit as st
        if st.session_state.get('authenticated') and st.session_state.get('user'):
            return st.session_state.user.id
    except ImportError:
        pass
    return None


def get_streamlit_user_email() -> Optional[str]:
    """Get current user email in Streamlit context"""
    try:
        import streamlit as st
        if st.session_state.get('authenticated') and st.session_state.get('user'):
            return st.session_state.user.email
    except ImportError:
        pass
    return None


def get_streamlit_user_name() -> Optional[str]:
    """Get current user name in Streamlit context"""
    try:
        import streamlit as st
        if st.session_state.get('user_profile'):
            return st.session_state.user_profile.get('full_name', 'User')
        elif st.session_state.get('user'):
            return st.session_state.user.user_metadata.get('name', 'User')
    except ImportError:
        pass
    return 'User'


def get_streamlit_user_avatar() -> Optional[str]:
    """Get current user avatar URL in Streamlit context"""
    try:
        import streamlit as st
        if st.session_state.get('user_profile'):
            return st.session_state.user_profile.get('avatar_url')
        elif st.session_state.get('user'):
            return st.session_state.user.user_metadata.get('picture')
    except ImportError:
        pass
    return None


# Legacy aliases for Streamlit compatibility
def init_auth_state():
    """Legacy alias for init_streamlit_auth"""
    init_streamlit_auth()


def logout():
    """Legacy alias for streamlit_logout"""
    streamlit_logout()


def get_user_id():
    """Legacy alias for get_streamlit_user_id"""
    return get_streamlit_user_id()


def get_user_email():
    """Legacy alias for get_streamlit_user_email"""
    return get_streamlit_user_email()


def get_user_name():
    """Legacy alias for get_streamlit_user_name"""
    return get_streamlit_user_name()


def get_user_avatar():
    """Legacy alias for get_streamlit_user_avatar"""
    return get_streamlit_user_avatar()
