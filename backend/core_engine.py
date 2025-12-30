"""
Core engine for kiwi-master backend.

CRITICAL: This module does NOT reimplement logic from run_query.py.
It calls the exact same functions that run_query.py uses, ensuring
parity by construction, not just by testing.

This module provides thin wrappers for API integration:
1. connect_sheet() - Emits execution stages during sheet loading
2. process_query() - Wraps query execution in API-friendly format
3. get_dataset_metadata() - Reads pre-computed metadata only
"""

import json
from pathlib import Path
from typing import Iterator, Dict, Any
from dataclasses import dataclass

# Import existing functions from run_query.py's imports
from data_sources.gsheet.connector import fetch_sheets_with_tables
from data_sources.gsheet.change_detector import needs_refresh
from data_sources.gsheet.snapshot_loader import load_snapshot
from schema_intelligence.chromadb_client import SchemaVectorStore
from schema_intelligence.hybrid_retriever import retrieve_schema
from planning_layer.planner_client import generate_plan
from validation_layer.plan_validator import validate_plan
from execution_layer.executor import execute_plan
from explanation_layer.explainer_client import explain_results
from utils.greeting_detector import is_greeting, get_greeting_response
from utils.memory_detector import detect_memory_intent
from utils.permanent_memory import update_memory


@dataclass
class StageUpdate:
    """Execution stage update for streaming to frontend."""
    stage: str
    message: str = ""
    error: str = ""


def connect_sheet(sheet_url: str = None) -> Iterator[StageUpdate]:
    """
    Connect to Google Sheet and prepare dataset for querying.
    
    CRITICAL: This calls existing backend functions, no reimplementation.
    
    Yields execution stages:
    - VALIDATING_URL
    - FETCHING_SHEET
    - DETECTING_TABLES
    - NORMALIZING_DATA
    - LOADING_DUCKDB
    - BUILDING_SCHEMA
    - EMBEDDING_CHROMA
    - FINALIZING
    - READY
    
    Args:
        sheet_url: Google Sheet URL (currently managed via config file)
    
    Yields:
        StageUpdate: Execution stage updates
    """
    try:
        yield StageUpdate(stage="VALIDATING_URL", message="Validating Google Sheet URL")
        
        # TODO: Add URL validation if sheet_url is provided
        # For now, uses config/settings.yaml
        
        yield StageUpdate(stage="FETCHING_SHEET", message="Fetching sheets from Google Sheets")
        
        # EXISTING FUNCTION: Same as run_query.py line 56
        sheets_with_tables = fetch_sheets_with_tables()
        
        yield StageUpdate(stage="DETECTING_TABLES", message="Detecting tables within sheets")
        # Already done in fetch_sheets_with_tables()
        
        yield StageUpdate(stage="NORMALIZING_DATA", message="Normalizing data and inferring types")
        # Already done in fetch_sheets_with_tables()
        
        yield StageUpdate(stage="LOADING_DUCKDB", message="Checking for data changes")
        
        # EXISTING FUNCTION: Same as run_query.py line 60
        needs_refresh_flag, full_reset, changed_sheets = needs_refresh(sheets_with_tables)
        
        # Initialize schema store
        # EXISTING CLASS: Same as run_query.py line 63
        store = SchemaVectorStore()
        
        if needs_refresh_flag:
            if full_reset:
                yield StageUpdate(
                    stage="LOADING_DUCKDB", 
                    message="Performing full reset (spreadsheet changed or first run)"
                )
                
                # Clear ChromaDB
                store.clear_collection()
                
                # EXISTING FUNCTION: Same as run_query.py line 75
                load_snapshot(sheets_with_tables, full_reset=True)
                
                yield StageUpdate(stage="BUILDING_SCHEMA", message="Building schema metadata")
                # Already done in load_snapshot()
                
                yield StageUpdate(stage="EMBEDDING_CHROMA", message="Building schema embeddings")
                
                # EXISTING FUNCTION: Same as run_query.py line 79
                store.rebuild()
                
            else:
                yield StageUpdate(
                    stage="LOADING_DUCKDB",
                    message=f"Incremental rebuild for {len(changed_sheets)} changed sheet(s)"
                )
                
                # Get source_ids for changed sheets
                source_ids = []
                for sheet_name in changed_sheets:
                    if sheet_name in sheets_with_tables and sheets_with_tables[sheet_name]:
                        source_id = sheets_with_tables[sheet_name][0].get('source_id')
                        if source_id:
                            source_ids.append(source_id)
                
                # EXISTING FUNCTION: Same as run_query.py line 96
                load_snapshot(sheets_with_tables, full_reset=False, changed_sheets=changed_sheets)
                
                yield StageUpdate(stage="BUILDING_SCHEMA", message="Updating schema metadata")
                # Already done in load_snapshot()
                
                yield StageUpdate(stage="EMBEDDING_CHROMA", message="Updating schema embeddings")
                
                # EXISTING FUNCTION: Same as run_query.py line 101
                if source_ids:
                    store.rebuild(source_ids=source_ids)
                else:
                    store.rebuild()
        else:
            yield StageUpdate(stage="LOADING_DUCKDB", message="No changes detected, using cached data")
        
        yield StageUpdate(stage="FINALIZING", message="Dataset ready for querying")
        
        yield StageUpdate(stage="READY", message="Ready")
        
    except Exception as e:
        yield StageUpdate(stage="ERROR", error=str(e))
        raise


def process_query(question: str) -> Dict[str, Any]:
    """
    Process a natural language query and return results.
    
    CRITICAL: This calls the exact same functions as run_query.py (lines 115-176).
    No reimplementation, ensuring parity by construction.
    
    Args:
        question: Natural language question
    
    Returns:
        dict with:
        - answer: Natural language explanation
        - query_plan: Structured query plan
        - result_data: Query results as dict
        - schema_context: Retrieved schema metadata
        - metadata: Additional metadata (source sheet, execution time, etc.)
    """
    import time
    start_time = time.time()
    
    # Check for greetings FIRST (same as run_query.py line 26)
    if is_greeting(question):
        greeting_response = get_greeting_response(question)
        return {
            "answer": greeting_response,
            "query_plan": None,
            "result_data": None,
            "schema_context": None,
            "metadata": {
                "is_greeting": True,
                "execution_time": time.time() - start_time
            }
        }
    
    # Check for memory intent BEFORE processing (same as run_query.py line 36)
    memory_result = detect_memory_intent(question)
    if memory_result and memory_result.get("has_memory_intent"):
        category = memory_result["category"]
        key = memory_result["key"]
        value = memory_result["value"]
        
        success = update_memory(category, key, value)
        
        if success:
            return {
                "answer": f"Got it. I'll remember that.",
                "query_plan": None,
                "result_data": None,
                "schema_context": None,
                "metadata": {
                    "is_memory": True,
                    "memory_stored": True,
                    "execution_time": time.time() - start_time
                }
            }
        else:
            return {
                "answer": "Failed to store memory",
                "query_plan": None,
                "result_data": None,
                "schema_context": None,
                "metadata": {
                    "is_memory": True,
                    "memory_stored": False,
                    "execution_time": time.time() - start_time
                }
            }
    
    # EXISTING FUNCTION: Same as run_query.py line 116
    schema_context = retrieve_schema(question)
    
    # EXISTING FUNCTION: Same as run_query.py line 123
    plan = generate_plan(question, schema_context)
    
    # EXISTING FUNCTION: Same as run_query.py line 124
    validate_plan(plan)
    
    # EXISTING FUNCTION: Same as run_query.py line 131
    result = execute_plan(plan)
    
    # Fallback for empty lookup/filter results (same as run_query.py lines 134-164)
    if result.empty and plan["query_type"] in ["lookup", "filter"]:
        # Try alternative tables
        alternative_tables = []
        for item in schema_context:
            meta = item.get("metadata", {})
            if meta.get("type") == "table":
                table_name = meta.get("table")
                if table_name and table_name != plan["table"]:
                    alternative_tables.append(table_name)
        
        for alt_table in alternative_tables:
            try:
                alt_plan = plan.copy()
                alt_plan["table"] = alt_table
                
                validate_plan(alt_plan)
                alt_result = execute_plan(alt_plan)
                
                if not alt_result.empty:
                    result = alt_result
                    plan = alt_plan
                    break
            except Exception:
                continue
    
    # EXISTING FUNCTION: Same as run_query.py line 171
    explanation = explain_results(result, query_plan=plan, original_question=question)
    
    # Extract source sheet from result
    source_sheet = plan.get("table", "Unknown")
    
    return {
        "answer": explanation,
        "query_plan": plan,
        "result_data": result.to_dict(orient="records") if not result.empty else [],
        "schema_context": [{"text": item["text"], "metadata": item["metadata"]} for item in schema_context],
        "metadata": {
            "source_sheet": source_sheet,
            "execution_time": time.time() - start_time,
            "row_count": len(result)
        }
    }


def get_dataset_metadata() -> Dict[str, Any]:
    """
    Get dataset metadata for inspection.
    
    CRITICAL: This is METADATA-ONLY with ZERO computation.
    - Reads from data_sources/snapshots/table_metadata.json (pre-computed)
    - Reads from data_sources/snapshots/sheet_state.json (pre-computed)
    
    FORBIDDEN:
    - NO SQL execution
    - NO DuckDB queries
    - NO schema recomputation
    - NO LLM calls
    - NO dynamic count derivation
    
    Returns:
        dict with:
        - spreadsheet_name: Name of the spreadsheet
        - last_sync: Last sync timestamp
        - sheets: List of sheets with table metadata
    """
    from data_sources.gsheet.snapshot_loader import load_table_metadata
    from data_sources.gsheet.change_detector import load_sheet_state
    import yaml
    
    # Read pre-computed table metadata
    table_metadata = load_table_metadata()
    
    # Read sheet state (includes spreadsheet ID and sheet hashes)
    sheet_state = load_sheet_state()
    
    # Get spreadsheet name from config
    with open("config/settings.yaml") as f:
        config = yaml.safe_load(f)
    spreadsheet_id = config["google_sheets"].get("spreadsheet_id", "Unknown")
    
    # Get last sync time from sheet state
    last_sync = sheet_state.get("last_checked", "Unknown")
    
    # Group tables by sheet
    sheets_dict = {}
    for table_name, table_info in table_metadata.items():
        sheet_name = table_info.get("sheet_name", "Unknown")
        
        if sheet_name not in sheets_dict:
            sheets_dict[sheet_name] = {
                "sheet_name": sheet_name,
                "tables": []
            }
        
        # Get column count from DuckDB metadata (pre-computed during ingestion)
        column_count = table_info.get("column_count", 0)
        columns = table_info.get("columns", [])
        
        sheets_dict[sheet_name]["tables"].append({
            "table_name": table_name,
            "row_count": table_info.get("row_count", 0),
            "column_count": column_count,
            "columns": columns,
            "source_id": table_info.get("source_id", "")
        })
    
    return {
        "spreadsheet_name": spreadsheet_id,
        "last_sync": last_sync,
        "sheets": list(sheets_dict.values())
    }


def reset_session():
    """
    Reset the session by clearing dataset state.
    Triggers full rebuild on next connect.
    """
    from data_sources.gsheet.change_detector import clear_sheet_state
    
    # Clear sheet state to force full rebuild on next connect
    clear_sheet_state()
    
    return {"status": "reset"}
