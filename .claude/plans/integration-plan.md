# Thara.ai Full-Stack Integration Review & Fix Plan

## Executive Summary

After thorough review, the application has **CRITICAL INTEGRATION ISSUES** that prevent it from working as a full-stack app:

| Area | Status | Issue |
|------|--------|-------|
| API Endpoints | ✅ Complete | All 15+ endpoints implemented |
| Frontend-Backend Matching | ✅ Complete | All called endpoints exist |
| CORS | ✅ Configured | Localhost origins allowed |
| **Auth Headers** | ✅ FIXED | Frontend now sends Authorization headers |
| **OAuth Field Mismatch** | ✅ FIXED | Frontend handles both `url` and `auth_url` |
| Environment Variables | ✅ Documented | See .env file |
| Token Refresh | ❌ Missing | No refresh mechanism (optional) |
| Error Handling | ✅ FIXED | 401 handling added to frontend |
| **Google Sheets OAuth** | ✅ IMPLEMENTED | Users can authorize their own sheets |

---

# GOOGLE SHEETS OAUTH IMPLEMENTATION (NEW)

## Overview

Users can now authorize access to their own Google Sheets without:
- Sharing sheets with a service account email
- Making sheets publicly accessible

The system falls back to service account if OAuth is not configured or user hasn't authorized.

## New Files Created

### Backend:
- `backend/utils/gsheet_oauth.py` - OAuth token management, credential helpers
- `backend/credentials/user_tokens/` - Directory for storing user OAuth tokens

### Frontend:
- `frontend/src/app/auth/sheets-callback/page.tsx` - OAuth callback handler

## New API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/auth/sheets/check` | GET | Check if user has authorized Sheets |
| `/api/auth/sheets` | GET | Get Google OAuth URL for Sheets |
| `/api/auth/sheets/callback` | POST | Exchange code for tokens |
| `/api/auth/sheets/revoke` | POST | Revoke Sheets access |

## Environment Variables Required

Add to `backend/.env`:

```env
# Google Sheets OAuth (from Google Cloud Console)
GOOGLE_CLIENT_ID=your_client_id_here
GOOGLE_CLIENT_SECRET=your_client_secret_here
GSHEET_OAUTH_REDIRECT_URL=http://localhost:3000/auth/sheets-callback
```

## Setup Instructions

1. Go to https://console.cloud.google.com/
2. Create or select a project
3. Enable "Google Sheets API" and "Google Drive API"
4. Go to APIs & Services → Credentials
5. Create OAuth 2.0 Client ID (Web application)
6. Add authorized redirect URI: `http://localhost:3000/auth/sheets-callback`
7. Copy Client ID and Client Secret to `.env`

## How It Works

1. User opens DatasetConnection modal
2. Frontend checks `/api/auth/sheets/check` to see if user has authorized
3. If not authorized, shows "Authorize" button
4. User clicks Authorize → redirected to Google OAuth
5. After approval → redirected to `/auth/sheets-callback`
6. Callback page exchanges code for tokens via backend
7. Tokens stored in `backend/credentials/user_tokens/{user_id}_sheets_token.json`
8. Future sheet loads use user's OAuth tokens instead of service account

---

# PART 1: CRITICAL FIXES (Code Changes) - COMPLETED ✅

## Fix 1: Add Authorization Headers to All API Requests ✅

**File:** `frontend/src/services/api.ts`

**Status:** IMPLEMENTED

Added `getAuthHeaders()` helper and applied to all API methods.

---

## Fix 2: OAuth URL Field Name Mismatch ✅

**File:** `frontend/src/components/auth/GoogleAuthButton.tsx`

**Status:** IMPLEMENTED

Now handles both `data.url` and `data.auth_url` for compatibility.

---

## Fix 3: Add 401 Error Handling with Redirect ✅

**File:** `frontend/src/services/api.ts`

**Status:** IMPLEMENTED

Added `handleResponse()` wrapper that clears tokens and redirects on 401.

---

## Fix 4: Token Refresh Mechanism (Optional)

**Problem:** Access tokens expire, no refresh logic exists

**Solution:** Add token refresh in api.ts or create useAuth hook

---

# PART 2: WHAT YOU NEED TO DO (Manual Setup)

## Step 1: Backend Environment Variables

Create/update `backend/.env` with:

```env
# ============================================
# REQUIRED API KEYS
# ============================================

# Gemini API Key (for LLM planning/explanation)
GEMINI_API_KEY=your_gemini_api_key_here

# Google API Key (for translation services)
GOOGLE_API_KEY=your_google_api_key_here

# ElevenLabs API Key (for voice TTS/STT)
ELEVENLABS_API_KEY=your_elevenlabs_api_key_here

# ============================================
# SUPABASE CONFIGURATION (for Google OAuth)
# ============================================

SUPABASE_URL=https://YOUR_PROJECT.supabase.co
SUPABASE_ANON_KEY=eyJhbGc...YOUR_ANON_KEY...

# ============================================
# AUTH SETTINGS
# ============================================

# Set to "false" to ENABLE authentication (default is "true" = skip auth)
SKIP_AUTH=false

# Set to "true" to enable Supabase auth
ENABLE_AUTH=true

# OAuth redirect URL (must match Supabase settings)
OAUTH_REDIRECT_URL=http://localhost:3000/auth/callback

# Frontend URL for CORS (optional, localhost already allowed)
FRONTEND_URL=http://localhost:3000
```

---

## Step 2: Supabase Dashboard Configuration

### 2.1 Create Supabase Project
1. Go to https://supabase.com and create new project
2. Note your **Project URL** and **anon/public key** (Settings → API)

### 2.2 Enable Google OAuth Provider
1. Go to **Authentication** → **Providers** → **Google**
2. Toggle **Enable Google provider**
3. You need Google OAuth credentials:

### 2.3 Create Google OAuth Credentials
1. Go to https://console.cloud.google.com/
2. Create or select a project
3. Go to **APIs & Services** → **Credentials**
4. Click **Create Credentials** → **OAuth client ID**
5. Choose **Web application**
6. Add **Authorized redirect URIs**:
   - `https://YOUR_PROJECT.supabase.co/auth/v1/callback`
7. Copy **Client ID** and **Client Secret**

### 2.4 Add Google Credentials to Supabase
1. Back in Supabase → Authentication → Providers → Google
2. Paste your **Client ID** and **Client Secret**
3. Save

### 2.5 Configure Redirect URLs in Supabase
1. Go to **Authentication** → **URL Configuration**
2. Set **Site URL**: `http://localhost:3000`
3. Add to **Redirect URLs**: `http://localhost:3000/auth/callback`

### 2.6 Run Database Schema (Optional - for user profiles)
1. Go to **SQL Editor** in Supabase
2. Copy contents of `backend/supabase_schema.sql`
3. Run it to create user_profiles table and triggers

---

## Step 3: Frontend Environment Variables

The file `frontend/.env.local` already exists. Verify it contains:

```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
NEXT_PUBLIC_ELEVENLABS_VOICE_ID=OUBMjq0LvBjb07bhwD3H
NEXT_PUBLIC_APP_NAME=Thara.ai
```

---

## Step 4: Google Sheets Service Account

For dataset loading to work:

1. Go to Google Cloud Console → IAM & Admin → Service Accounts
2. Create a service account (or use existing)
3. Download JSON key file
4. Save as `backend/credentials/service_account.json`
5. Share your Google Sheet with the service account email

---

# PART 3: API ENDPOINTS REFERENCE

## All Available Backend Routes

| Endpoint | Method | Auth Required | Purpose |
|----------|--------|--------------|---------|
| `/` | GET | No | Health check |
| `/api/load-dataset` | POST | Yes* | Load Google Sheet |
| `/api/query` | POST | Yes* | Process user question |
| `/api/transcribe` | POST | Yes* | Audio → Text |
| `/api/text-to-speech` | POST | Yes* | Text → Audio |
| `/api/auth/check` | GET | No | Check auth status |
| `/api/auth/google` | GET | No | Get OAuth URL |
| `/api/auth/callback` | POST | No | Exchange OAuth code |
| `/api/onboarding/start` | GET | No | Onboarding flow |
| `/api/onboarding/input` | POST | No | Onboarding input |
| `/api/debug/routing` | GET | No | Debug routing |
| `/api/debug/profiles` | GET | No | Debug profiles |
| `/api/context/clear` | POST | No | Clear context |

*Auth bypassed if `SKIP_AUTH=true` (default)

---

# PART 4: TESTING CHECKLIST

After making fixes and configuration:

### Auth Flow Test
- [ ] Click "Continue with Google" → redirects to Google
- [ ] After Google login → returns to `/auth/callback`
- [ ] Callback page shows success and redirects to app
- [ ] LocalStorage has `thara_access_token`
- [ ] API calls include Authorization header (check Network tab)

### Core Features Test
- [ ] Connect Google Sheet → loads successfully
- [ ] Type a question → gets response with data
- [ ] Click mic → records audio
- [ ] Audio plays response (TTS works)
- [ ] Purple theme shows correctly

### Error Handling Test
- [ ] Clear localStorage → redirects to login
- [ ] Invalid token → 401 → redirect to login

---

# PART 5: PREVIOUS PLAN (Completed Phases)

## Phase 1: Backend Model Fixes ✅

## Phase 2: Frontend Brand Rename (Kiwi → Thara.ai) ✅

## Phase 3: Remove Hardcoded Values ✅

## Phase 4: API Layer Cleanup ✅

## Phase 5: Component Refactoring ✅

## Phase 6: Full Google OAuth Implementation ✅

## Phase 7: Purple/Violet Color Theme ✅

---

## Testing Checklist

- [ ] App loads with "Thara.ai" branding and purple theme
- [ ] Google OAuth login works end-to-end
- [ ] Dataset connection modal works
- [ ] Voice recording starts/stops correctly
- [ ] TTS playback works with ElevenLabs
- [ ] Chat messages persist across refresh
- [ ] Follow-up questions work (context preserved)
- [ ] No "Kiwi" text anywhere in UI
- [ ] No hardcoded credentials in code
- [ ] Mobile responsive layout works
- [ ] Tamil language support still works
