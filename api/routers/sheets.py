"""
Sheets router - Dataset connection and inspection endpoints.
"""

import sys
from pathlib import Path

# Add backend to Python path
backend_path = Path(__file__).parent.parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any
import json
import asyncio

router = APIRouter()


class ConnectRequest(BaseModel):
    """Request model for POST /sheets/connect"""
    sheet_url: Optional[str] = None  # Currently uses config file


@router.post("/connect")
async def connect_sheet(request: ConnectRequest):
    """
    Connect to Google Sheet and load dataset.
    
    Returns Server-Sent Events (SSE) stream with execution stages:
    - VALIDATING_URL
    - FETCHING_SHEET
    - DETECTING_TABLES
    - NORMALIZING_DATA
    - LOADING_DUCKDB
    - BUILDING_SCHEMA
    - EMBEDDING_CHROMA
    - FINALIZING
    - READY
    
    Stream format:
    data: {"stage": "VALIDATING_URL", "message": "...", "error": ""}
    """
    from core_engine import connect_sheet
    
    async def event_generator():
        try:
            # Run connect_sheet in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            
            def sync_connect():
                """Run synchronous connect_sheet generator."""
                for stage_update in connect_sheet(request.sheet_url):
                    return stage_update
            
            # Stream stages
            for stage_update in connect_sheet(request.sheet_url):
                data = {
                    "stage": stage_update.stage,
                    "message": stage_update.message,
                    "error": stage_update.error
                }
                yield f"data: {json.dumps(data)}\n\n"
                
                # Small delay to ensure frontend receives updates
                await asyncio.sleep(0.1)
                
        except Exception as e:
            error_data = {
                "stage": "ERROR",
                "message": "",
                "error": str(e)
            }
            yield f"data: {json.dumps(error_data)}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


@router.get("/status")
async def get_status():
    """
    Get current dataset connection status.
    
    Returns:
        {
            "status": "NO_DATASET" | "LOADING" | "READY" | "ERROR",
            "current_stage": str (if loading)
        }
    """
    # TODO: Implement state tracking in backend
    # For now, we assume ready if metadata exists
    from core_engine import get_dataset_metadata
    
    try:
        metadata = get_dataset_metadata()
        if metadata.get("sheets"):
            return {
                "status": "READY",
                "current_stage": None
            }
        else:
            return {
                "status": "NO_DATASET",
                "current_stage": None
            }
    except Exception as e:
        return {
            "status": "ERROR",
            "current_stage": None,
            "error": str(e)
        }


@router.get("/summary")
async def get_summary():
    """
    Get dataset summary for inspection.
    
    CRITICAL: This is METADATA-ONLY with ZERO computation.
    - Reads from pre-computed files
    - NO SQL execution
    - NO DuckDB queries
    - NO LLM calls
    
    Returns:
        {
            "spreadsheet_name": str,
            "last_sync": timestamp,
            "sheets": [
                {
                    "sheet_name": str,
                    "tables": [
                        {
                            "table_name": str,
                            "row_count": int,
                            "column_count": int,
                            "columns": [str],
                            "source_id": str
                        }
                    ]
                }
            ]
        }
    """
    from core_engine import get_dataset_metadata
    
    try:
        metadata = get_dataset_metadata()
        return metadata
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail="No dataset loaded. Please connect a sheet first."
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve dataset metadata: {str(e)}"
        )
