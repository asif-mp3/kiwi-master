"""
Chat router - Query processing endpoint.
"""

import sys
from pathlib import Path

# Add backend to Python path
backend_path = Path(__file__).parent.parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, List, Any, Optional

router = APIRouter()


class QueryRequest(BaseModel):
    """Request model for POST /chat/query"""
    question: str


class QueryResponse(BaseModel):
    """Response model for POST /chat/query"""
    answer: str
    query_plan: Optional[Dict[str, Any]]
    result_data: Optional[List[Dict[str, Any]]] = None
    schema_context: Optional[List[Dict[str, Any]]]
    metadata: Dict[str, Any]


@router.post("/query", response_model=QueryResponse)
async def process_query(request: QueryRequest):
    """
    Process a natural language query.
    
    This endpoint calls backend.core_engine.process_query()
    which calls the exact same functions as run_query.py.
    
    Returns backend response verbatim with:
    - answer: Natural language explanation
    - query_plan: Structured query plan
    - result_data: Query results
    - schema_context: Retrieved schema metadata
    - metadata: Execution metadata (source_sheet, execution_time, etc.)
    """
    from core_engine import process_query
    import traceback
    
    try:
        result = process_query(request.question)
        return QueryResponse(**result)
    except Exception as e:
        # Log full traceback to server console
        print(f"ERROR processing query: {str(e)}")
        traceback.print_exc()
        
        # Return detailed error to client
        raise HTTPException(
            status_code=500,
            detail={
                "error": str(e),
                "traceback": traceback.format_exc(),
                "stage": "query_processing",
                "hint": "Check if dataset is loaded and question is valid"
            }
        )
