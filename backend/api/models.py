"""
Pydantic models for API request/response validation.
These models match the TypeScript types in the frontend (src/lib/types.ts).
"""

from typing import List, Optional, Any, Literal
from pydantic import BaseModel, Field


# ============================================================================
# Query Plan Models (matches planning_layer/plan_schema.json)
# ============================================================================

class FilterModel(BaseModel):
    """Filter condition for query plan"""
    column: str
    operator: Literal['=', '>', '<', '>=', '<=', '!=', 'LIKE']
    value: Any


class OrderByModel(BaseModel):
    """Order by clause for query plan"""
    column: str
    direction: Literal['ASC', 'DESC']


class QueryPlan(BaseModel):
    """Query plan schema matching frontend QueryPlan interface"""
    query_type: Literal['metric', 'lookup', 'filter', 'extrema_lookup', 'rank', 'list', 'aggregation_on_subset', 'comparison', 'percentage', 'trend']
    table: str
    select_columns: Optional[List[str]] = None
    metrics: Optional[List[str]] = None
    filters: Optional[List[FilterModel]] = None
    group_by: Optional[List[str]] = None
    order_by: Optional[List[Any]] = None  # Changed to Any to support flexible formats
    limit: Optional[int] = None
    aggregation_function: Optional[str] = None
    aggregation_column: Optional[str] = None
    subset_filters: Optional[List[Any]] = None
    subset_order_by: Optional[List[Any]] = None
    subset_limit: Optional[int] = None
    # Advanced query type configs
    comparison: Optional[dict] = None  # For comparison queries
    percentage: Optional[dict] = None  # For percentage queries
    trend: Optional[dict] = None  # For trend queries


# ============================================================================
# Detected Table Models (matches data_sources/gsheet/connector.py)
# ============================================================================

class DetectedTable(BaseModel):
    """Detected table metadata matching frontend DetectedTable interface"""
    table_id: str
    title: Optional[str] = None
    sheet_name: str
    source_id: str  # spreadsheet_id#sheet_name
    sheet_hash: str
    row_range: tuple[int, int]
    col_range: tuple[int, int]
    total_rows: Optional[int] = None
    columns: Optional[List[str]] = None
    preview_data: Optional[List[Any]] = None


# ============================================================================
# API Request/Response Models
# ============================================================================

class LoadDataRequest(BaseModel):
    """Request to load a Google Sheets dataset"""
    url: str = Field(..., description="Google Sheets URL or spreadsheet ID")


class DatasetStats(BaseModel):
    """Dataset statistics"""
    totalTables: int
    totalRecords: int
    sheetCount: int
    sheets: List[str]
    detectedTables: List[DetectedTable]
    profiledTables: Optional[int] = None  # Number of tables profiled for intelligent routing


class LoadDataResponse(BaseModel):
    """Response from loading dataset"""
    success: bool
    stats: Optional[DatasetStats] = None
    error: Optional[str] = None
    data_summary: Optional[str] = None  # Summary message from Thara personality


class QueryRequest(BaseModel):
    """Request to process a user query"""
    text: str = Field(..., description="User question text")
    conversation_id: Optional[str] = None  # For follow-up context tracking


class SchemaContext(BaseModel):
    """Schema context item"""
    text: str


class ProcessQueryResponse(BaseModel):
    """Response from processing a query"""
    success: bool
    explanation: Optional[str] = None
    data: Optional[List[dict]] = None  # Array of objects for table visualization
    plan: Optional[QueryPlan] = None
    schema_context: Optional[List[SchemaContext]] = None
    data_refreshed: Optional[bool] = False
    error: Optional[str] = None
    is_greeting: Optional[bool] = False
    is_memory_storage: Optional[bool] = False
    # New fields for intelligent routing
    table_used: Optional[str] = None  # Which table was selected
    routing_confidence: Optional[float] = None  # 0.0-1.0 confidence score
    was_followup: Optional[bool] = False  # Whether this was a follow-up question
    entities_extracted: Optional[dict] = None  # Extracted entities (month, metric, etc.)
    healing_attempts: Optional[List[dict]] = None  # Self-healing attempt history


class TranscribeResponse(BaseModel):
    """Response from audio transcription"""
    success: bool
    text: Optional[str] = None
    error: Optional[str] = None


class AuthResponse(BaseModel):
    """Response from authentication check"""
    authenticated: bool
    user: Optional[dict] = None  # User info if authenticated


class OnboardingResponse(BaseModel):
    """Response from onboarding endpoints"""
    message: str
    state: str
    awaiting: Optional[str] = None
    is_complete: bool
    user_name: Optional[str] = None
    language: Optional[str] = None


class RoutingDebugResponse(BaseModel):
    """Response from routing debug endpoint"""
    explanation: str
    debug: dict


class TableProfilesResponse(BaseModel):
    """Response from table profiles endpoint"""
    success: bool
    profile_count: int
    profiles: dict
