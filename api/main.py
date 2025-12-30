"""
Kiwi-Master API Server
Transport-only layer between frontend and backend.

This API does NOT compute or infer anything. It strictly calls backend
functions and returns results verbatim.
"""

import sys
from pathlib import Path

# Add backend to Python path and set absolute CWD to project root
backend_path = Path(__file__).parent.parent / "backend"
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

# CRITICAL: Force CWD to project root so "config/" and "backend/" paths resolve correctly
# regardless of where this script is run from.
import os
os.chdir(project_root)

# Load environment variables (API keys, etc.)
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import sheets, chat, voice

app = FastAPI(
    title="Kiwi-Master API",
    description="Transport-only API for deterministic analytics engine",
    version="1.0.0"
)

# CORS configuration for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],  # Frontend URLs
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(sheets.router, prefix="/api/sheets", tags=["sheets"])
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
app.include_router(voice.router, prefix="/api/voice", tags=["voice"])


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "status": "ok",
        "service": "Kiwi-Master API",
        "version": "1.0.0",
        "philosophy": "Backend decides truth → API transports truth → Frontend observes truth"
    }


@app.post("/api/session/reset")
async def reset_session():
    """
    Reset session by clearing dataset state.
    Forces full rebuild on next connect.
    """
    from core_engine import reset_session
    return reset_session()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
