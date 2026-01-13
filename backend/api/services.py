"""
Service layer for API endpoints.
Integrates all new components for bulletproof query handling.

New Architecture:
1. Intelligent Table Routing (replaces top_k=50 schema dump)
2. Entity Extraction for smart filtering
3. Query Context for follow-up support
4. Self-Healing Execution
5. Thara Personality
"""

import sys
from pathlib import Path
import re
from typing import Dict, Any, Optional, List
from concurrent.futures import ThreadPoolExecutor, as_completed

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Core imports
from schema_intelligence.profile_store import ProfileStore
from schema_intelligence.data_profiler import DataProfiler
from planning_layer.table_router import TableRouter, RoutingResult
from planning_layer.entity_extractor import EntityExtractor
from planning_layer.planner_client import generate_plan
from validation_layer.plan_validator import validate_plan
from execution_layer.executor import execute_plan
from execution_layer.query_healer import QueryHealer, QueryExecutionError
from execution_layer.sql_compiler import compile_sql
from explanation_layer.explainer_client import explain_results
from data_sources.gsheet.connector import fetch_sheets_with_tables
from utils.translation import translate_to_english, translate_to_tamil
from data_sources.gsheet.change_detector import needs_refresh
from data_sources.gsheet.snapshot_loader import load_snapshot
from schema_intelligence.chromadb_client import SchemaVectorStore
from utils.voice_utils import transcribe_audio
from utils.memory_detector import detect_memory_intent
from utils.permanent_memory import update_memory, load_memory
from utils.greeting_detector import is_greeting, get_greeting_response, detect_schema_inquiry, is_non_query_conversational, get_non_query_response, is_date_context_statement, get_date_context_response
from explanation_layer.explainer_client import generate_off_topic_response
from utils.query_context import QueryContext, QueryTurn, ConversationManager, PendingClarification, PendingCorrection
from utils.personality import TharaPersonality
from utils.onboarding import OnboardingManager, get_user_name
from utils.query_cache import get_query_cache, cache_query_result, get_cached_query_result, invalidate_spreadsheet_cache
from utils.config_loader import get_config
from analytics_engine.duckdb_manager import DuckDBManager
import yaml
import numpy as np
import math


def _resolve_top_references(question: str, previous_turn) -> str:
    """
    Resolve "top X" references in question using previous query's result_values.

    Examples:
    - "top category" → "Sarees" (if Sarees was top in previous rank query)
    - "best performing state" → "West Bengal" (if WB was top)
    - "highest selling product" → "Product ABC" (if ABC was top)

    This prevents the LLM from misinterpreting what "top" refers to.
    """
    if not previous_turn:
        return question

    result_values = getattr(previous_turn, 'result_values', {}) or {}
    if not result_values:
        return question

    # Patterns for "top X" references
    top_patterns = [
        # (pattern, dimension_keywords)
        (r'\b(top|best|highest|leading|first)\s+(category|categories)', ['category', 'product_category']),
        (r'\b(top|best|highest|leading|first)\s+(product|item|products|items)', ['product', 'item', 'product_name']),
        (r'\b(top|best|highest|leading|first)\s+(state|states)', ['state', 'state_name']),
        (r'\b(top|best|highest|leading|first)\s+(branch|branches|store|stores)', ['branch', 'store', 'branch_name']),
        (r'\b(top|best|highest|leading|first)\s+(region|regions|area|areas)', ['region', 'area']),
        (r'\b(top|best|highest|leading|first)\s+(employee|employees|person|salesperson)', ['employee', 'salesperson', 'employee_name']),
        (r'\b(top|best|highest|leading|first)\s+(seller|sellers)', ['category', 'product', 'item']),
        (r'\b(top|best|highest|leading|first)\s+(performing|one)', ['category', 'product', 'state', 'branch', 'employee']),
    ]

    for pattern, dimension_keys in top_patterns:
        # Use IGNORECASE flag so match indices work on original question
        match = re.search(pattern, question, re.IGNORECASE)
        if match:
            # Find the matching dimension in result_values
            for dim_key in dimension_keys:
                for col_name, col_value in result_values.items():
                    if dim_key in col_name.lower():
                        # Replace the "top X" reference with actual value
                        matched_text = match.group(0)
                        if col_value and isinstance(col_value, str):
                            # Replace pattern with actual value in original question
                            new_question = question[:match.start()] + col_value + question[match.end():]
                            print(f"    [Top Reference Resolved] '{matched_text}' → '{col_value}'")
                            return new_question

    return question


def _extract_result_values(result, plan: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract key result values from a query result for pronoun resolution in follow-ups.

    For extrema_lookup/rank queries, extracts the "winning" value so "that state",
    "that branch", etc. can be resolved in follow-up questions.

    Example:
    - Query: "Which state has highest revenue?"
    - Result: [{"State": "West Bengal", "Revenue": 1780000}]
    - Extracted: {"State": "West Bengal", "Revenue": 1780000}

    Next query: "In that state, which branch..."
    → "that state" resolves to "West Bengal"
    """
    if result is None or not hasattr(result, '__len__') or len(result) == 0:
        return {}

    query_type = plan.get('query_type', '')
    result_values = {}

    try:
        # For extrema_lookup or rank with limit 1, extract the top result
        if query_type in ['extrema_lookup', 'rank', 'filter', 'lookup']:
            if hasattr(result, 'iloc'):
                first_row = result.iloc[0]
            elif hasattr(result, '__getitem__'):
                first_row = result[0] if isinstance(result, list) else result
            else:
                return {}

            # Extract dimension columns (likely what user will reference)
            # Priority: State, Branch, Area, Category, then other dimensions
            priority_patterns = [
                'state', 'branch', 'area', 'region', 'location', 'city',
                'category', 'product', 'item', 'name', 'department'
            ]

            if hasattr(first_row, 'items'):
                # Dict-like row
                for col, val in first_row.items():
                    col_lower = str(col).lower()
                    # Include dimension columns
                    for pattern in priority_patterns:
                        if pattern in col_lower:
                            result_values[col] = val
                            break
                    # Also include the metric column (for context)
                    if any(m in col_lower for m in ['revenue', 'sales', 'profit', 'total', 'amount', 'value']):
                        result_values[col] = val
            elif hasattr(first_row, 'index'):
                # Pandas Series
                for col in first_row.index:
                    col_lower = str(col).lower()
                    for pattern in priority_patterns:
                        if pattern in col_lower:
                            result_values[col] = first_row[col]
                            break
                    if any(m in col_lower for m in ['revenue', 'sales', 'profit', 'total', 'amount', 'value']):
                        result_values[col] = first_row[col]

    except Exception as e:
        print(f"  Warning: Could not extract result values: {e}")

    return result_values


def _sanitize_for_json(data):
    """
    Convert numpy/pandas types to native Python types for JSON serialization.
    Pydantic/FastAPI can't serialize numpy.float64, numpy.int64, pandas.Timestamp, etc.
    Also handles NaN/Inf which aren't valid JSON.
    """
    if data is None:
        return None
    if isinstance(data, dict):
        return {k: _sanitize_for_json(v) for k, v in data.items()}
    if isinstance(data, list):
        return [_sanitize_for_json(item) for item in data]
    # Handle numpy integer types
    if isinstance(data, (np.integer,)):
        return int(data)
    # Handle numpy float types (check for NaN/Inf)
    if isinstance(data, (np.floating,)):
        val = float(data)
        if math.isnan(val) or math.isinf(val):
            return None
        return val
    # Handle native float NaN/Inf
    if isinstance(data, float):
        if math.isnan(data) or math.isinf(data):
            return None
        return data
    if isinstance(data, np.ndarray):
        return _sanitize_for_json(data.tolist())
    if isinstance(data, np.bool_):
        return bool(data)
    # Handle pandas Timestamp
    if hasattr(data, 'isoformat'):
        return data.isoformat()
    # Handle pandas NA/NaT
    if str(type(data).__name__) in ('NAType', 'NaTType') or str(data) in ('NA', 'NaT', '<NA>'):
        return None
    # Generic numpy scalar with .item() method
    if hasattr(data, 'item'):
        return _sanitize_for_json(data.item())
    return data


class AppState:
    """
    Application state management with lazy component initialization.

    Heavy components (vector_store, profile_store, table_router, query_healer)
    are lazily initialized on first access to save startup time.
    """

    def __init__(self):
        # State flags
        self.data_loaded: bool = False
        self.current_spreadsheet_id: Optional[str] = None
        self.loaded_spreadsheet_ids: List[str] = []  # Track all loaded spreadsheets for multi-sheet support
        self._user_name_loaded: bool = False
        self.last_sync_time: Optional[str] = None  # ISO format timestamp of last sync

        # Dataset metadata for display (populated during load)
        self.detected_tables: List[Dict[str, Any]] = []  # Stores DetectedTable info for UI
        self.original_sheet_names: List[str] = []  # Original sheet names without prefixes
        self.total_records: int = 0  # Total records across all tables

        # Lazy-initialized heavy components (use underscore prefix)
        self._vector_store: Optional[SchemaVectorStore] = None
        self._profile_store: Optional[ProfileStore] = None
        self._table_router: Optional[TableRouter] = None
        self._query_healer: Optional[QueryHealer] = None
        self._correction_detector = None  # Lazy-initialized

        # Light components - initialize immediately (cheap)
        self.conversation_manager: ConversationManager = ConversationManager()
        self.personality: TharaPersonality = TharaPersonality()
        self.onboarding: OnboardingManager = OnboardingManager()
        self.entity_extractor: EntityExtractor = EntityExtractor()

        # Check if data already exists in DuckDB (persists across restarts)
        self._check_existing_data()

    def _check_existing_data(self):
        """
        Check if DuckDB already has data from a previous session.
        This prevents reloading data after backend restarts.

        Checks:
        1. DuckDB file exists with tables
        2. Profile file exists with profiles
        """
        try:
            from analytics_engine.duckdb_manager import DuckDBManager
            from pathlib import Path

            db_path = Path("data_sources/snapshots/latest.duckdb")
            profiles_path = Path("data_sources/table_profiles.json")

            # Check DuckDB has data
            has_duckdb_data = False
            if db_path.exists() and db_path.stat().st_size > 0:
                db = DuckDBManager()
                tables = db.list_tables()
                if tables and len(tables) > 0:
                    has_duckdb_data = True

            # Check profiles exist
            has_profiles = profiles_path.exists() and profiles_path.stat().st_size > 100

            # Only mark as loaded if BOTH exist
            if has_duckdb_data and has_profiles:
                self.data_loaded = True
                print(f"  ✓ Found existing data (DuckDB + profiles) - no reload needed")
        except Exception as e:
            # Silently fail - will load data normally
            pass

    @property
    def vector_store(self) -> SchemaVectorStore:
        """Lazy-load vector store on first access"""
        if self._vector_store is None:
            self._vector_store = SchemaVectorStore()
        return self._vector_store

    @vector_store.setter
    def vector_store(self, value):
        self._vector_store = value

    @property
    def profile_store(self) -> ProfileStore:
        """Lazy-load profile store on first access"""
        if self._profile_store is None:
            self._profile_store = ProfileStore()
        return self._profile_store

    @profile_store.setter
    def profile_store(self, value):
        self._profile_store = value

    @property
    def table_router(self) -> TableRouter:
        """Lazy-load table router on first access"""
        if self._table_router is None:
            self._table_router = TableRouter(self.profile_store)
        return self._table_router

    @table_router.setter
    def table_router(self, value):
        self._table_router = value

    @property
    def query_healer(self) -> QueryHealer:
        """Lazy-load query healer on first access"""
        if self._query_healer is None:
            self._query_healer = QueryHealer(profile_store=self.profile_store)
        return self._query_healer

    @query_healer.setter
    def query_healer(self, value):
        self._query_healer = value

    @property
    def correction_detector(self):
        """Lazy-load correction intent detector on first access"""
        if self._correction_detector is None:
            from utils.correction_detector import CorrectionIntentDetector
            self._correction_detector = CorrectionIntentDetector()
            # Refresh with known values from profiles
            if self._profile_store is not None:
                self._correction_detector.refresh_from_profiles(self._profile_store)
        return self._correction_detector

    @correction_detector.setter
    def correction_detector(self, value):
        self._correction_detector = value

    def initialize(self):
        """
        Initialize components that need explicit setup.
        Heavy components are now lazy-loaded, so this just loads user preferences.
        """
        # Load user preferences (cheap operation)
        if not self._user_name_loaded:
            user_name = get_user_name()
            if user_name:
                self.personality.set_name(user_name)
            self._user_name_loaded = True

        return self

    def initialize_vector_store(self):
        """Initialize vector store if not already done (for backwards compatibility)"""
        return self.vector_store


# Singleton instance
app_state = AppState()


def extract_spreadsheet_id(url: str) -> Optional[str]:
    """Extract spreadsheet ID from Google Sheets URL"""
    pattern = r'/spreadsheets/d/([a-zA-Z0-9-_]+)'
    match = re.search(pattern, url)
    if match:
        return match.group(1)
    if re.match(r'^[a-zA-Z0-9-_]+$', url):
        return url
    return None


def load_dataset_service(url: str, user_id: str = None, append: bool = False) -> Dict[str, Any]:
    """
    Load data from Google Sheets with profiling.
    Now includes table profiling for intelligent routing.

    MULTI-SPREADSHEET SUPPORT:
    - When append=False (default): Clears existing data, loads fresh
    - When append=True: Adds to existing data without clearing

    Args:
        url: Google Sheets URL or ID
        user_id: Optional user ID for OAuth credentials
        append: If True, append to existing data instead of replacing
    """
    try:
        print(f"[Dataset] Starting load for URL: {url} (append={append})")

        spreadsheet_id = extract_spreadsheet_id(url)
        if not spreadsheet_id:
            return {
                'success': False,
                'error': 'Invalid Google Sheets URL or ID'
            }

        # Check if this spreadsheet is already loaded (when appending)
        if append and spreadsheet_id in app_state.loaded_spreadsheet_ids:
            print(f"[Dataset] Spreadsheet {spreadsheet_id} already loaded, skipping")
            return {
                'success': True,
                'message': 'Spreadsheet already loaded',
                'stats': None
            }

        # Set current user for OAuth credentials
        if user_id:
            from data_sources.gsheet.connector import set_current_user
            set_current_user(user_id)
            print(f"[Dataset] Using credentials for user: {user_id}")

        print(f"[Dataset] Extracted spreadsheet ID: {spreadsheet_id}")

        # Update config with new spreadsheet ID (for backward compatibility)
        config_path = project_root / "config" / "settings.yaml"
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)

        config['google_sheets']['spreadsheet_id'] = spreadsheet_id

        with open(config_path, 'w') as f:
            yaml.dump(config, f)

        # Initialize all components
        app_state.initialize()
        store = app_state.vector_store

        # Fetch sheets with multi-table detection (pass spreadsheet_id directly)
        print(f"[Dataset] Fetching sheets with tables from {spreadsheet_id[:20]}...")
        sheets_with_tables = fetch_sheets_with_tables(spreadsheet_id)
        print(f"[Dataset] Fetched {len(sheets_with_tables)} sheets")

        # Add spreadsheet prefix to sheet names to avoid collisions across spreadsheets
        # Format: "SpreadsheetName_SheetName" where SpreadsheetName is first 10 chars of ID
        spreadsheet_prefix = spreadsheet_id[:10]
        prefixed_sheets_with_tables = {}
        for sheet_name, tables in sheets_with_tables.items():
            # Prefix sheet name for uniqueness across spreadsheets
            prefixed_sheet_name = f"{spreadsheet_prefix}_{sheet_name}"
            # Update table info with prefixed sheet name
            for table in tables:
                table['sheet_name'] = prefixed_sheet_name
                table['original_sheet_name'] = sheet_name  # Keep original for display
                table['spreadsheet_id'] = spreadsheet_id
            prefixed_sheets_with_tables[prefixed_sheet_name] = tables

        # OPTIMIZATION: Populate sheet cache so first query doesn't re-fetch
        from data_sources.gsheet.connector import get_sheet_cache
        sheet_cache = get_sheet_cache()
        sheet_cache.set_cached_data(spreadsheet_id, sheets_with_tables)
        print(f"[Dataset] Populated sheet cache for 300s TTL")

        if append and app_state.data_loaded:
            # APPEND MODE: Don't clear existing data
            print(f"[Dataset] APPEND MODE: Adding to existing data...")
            # Load snapshot in append mode (full_reset=False)
            load_snapshot(prefixed_sheets_with_tables, full_reset=False, changed_sheets=list(prefixed_sheets_with_tables.keys()))
            print(f"[Dataset] Appended {len(prefixed_sheets_with_tables)} sheets to existing snapshot")
            # Rebuild vector store incrementally
            store.rebuild()
        else:
            # REPLACE MODE: Clear and rebuild
            if not append:
                app_state.data_loaded = False
                app_state.loaded_spreadsheet_ids = []  # Reset list
                app_state.detected_tables = []  # Reset detected tables
                app_state.original_sheet_names = []  # Reset sheet names
                app_state.total_records = 0  # Reset record count
                print(f"[Dataset] REPLACE MODE: Clearing existing data...")

            # Clear and rebuild vector store
            print(f"[Dataset] Clearing vector store...")
            store.clear_collection()
            print(f"[Dataset] Loading snapshot...")
            load_snapshot(prefixed_sheets_with_tables, full_reset=True)
            print(f"[Dataset] Rebuilding vector store...")
            store.rebuild()

        # === Profile tables for intelligent routing ===
        print(f"[Dataset] Profiling tables for intelligent routing...")
        profiler = DataProfiler()
        db = DuckDBManager()
        tables = db.list_tables()

        if not append:
            # Clear old profiles only in replace mode
            app_state.profile_store.clear_profiles()
            print(f"  [Profile] Cleared old profiles")

        profile_count = 0
        profile_errors = []

        def profile_single_table(table_name: str):
            """Profile a single table - designed for parallel execution"""
            try:
                # Each thread gets its own DuckDB connection for thread safety
                thread_db = DuckDBManager()
                df = thread_db.query(f'SELECT * FROM "{table_name}" LIMIT 10000')
                profile = profiler.profile_table(table_name, df)
                return table_name, profile, None
            except Exception as e:
                return table_name, None, str(e)

        # Parallelize table profiling with 5 workers (5x speedup)
        print(f"  [Profile] Starting parallel profiling with 5 workers...")
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {executor.submit(profile_single_table, t): t for t in tables}
            for future in as_completed(futures):
                table_name, profile, error = future.result()
                if profile:
                    app_state.profile_store.set_profile(table_name, profile)
                    profile_count += 1
                    print(f"  [Profile] {table_name}: {profile.get('table_type', 'unknown')}, "
                          f"{profile.get('row_count', 0)} rows")
                else:
                    profile_errors.append(f"{table_name}: {error}")
                    print(f"  [Profile] Warning: Could not profile {table_name}: {error}")

        # Save profiles to disk
        app_state.profile_store.save_profiles()
        print(f"[Dataset] Profiled {profile_count} tables")

        # Refresh entity extractor with learned values from profiles
        app_state.entity_extractor.refresh_from_profiles(app_state.profile_store)

        # Build response - gather all sheets across all loaded spreadsheets
        total_tables = sum(len(tbls) for tbls in prefixed_sheets_with_tables.values())
        total_records = 0
        detected_tables = []

        for sheet_name, tables_list in prefixed_sheets_with_tables.items():
            for table in tables_list:
                df = table.get('dataframe')
                actual_rows = len(df) if df is not None else 0
                # Ensure all column names are strings (some tables have numeric headers)
                actual_columns = [str(col) for col in df.columns] if df is not None else []

                detected_tables.append({
                    'table_id': table.get('table_id', ''),
                    'title': table.get('title', ''),
                    'sheet_name': table.get('original_sheet_name', sheet_name),  # Use original for display
                    'source_id': table.get('source_id', ''),
                    'sheet_hash': table.get('sheet_hash', ''),
                    'row_range': table.get('row_range', [0, 0]),
                    'col_range': table.get('col_range', [0, 0]),
                    'total_rows': actual_rows,
                    'columns': actual_columns,
                    'preview_data': [],
                    'spreadsheet_id': table.get('spreadsheet_id', spreadsheet_id)
                })
                total_records += actual_rows

        app_state.data_loaded = True
        app_state.current_spreadsheet_id = spreadsheet_id

        # Track this spreadsheet in loaded list
        if spreadsheet_id not in app_state.loaded_spreadsheet_ids:
            app_state.loaded_spreadsheet_ids.append(spreadsheet_id)

        # Store detected tables metadata for UI (append mode merges, replace mode replaces)
        original_sheets = list(set(
            t.get('original_sheet_name', t.get('sheet_name', ''))
            for tables_list in prefixed_sheets_with_tables.values()
            for t in tables_list
        ))
        if append:
            # Merge with existing data
            app_state.detected_tables.extend(detected_tables)
            app_state.original_sheet_names.extend([s for s in original_sheets if s not in app_state.original_sheet_names])
            app_state.total_records += total_records
        else:
            # Replace mode - set fresh
            app_state.detected_tables = detected_tables
            app_state.original_sheet_names = original_sheets
            app_state.total_records = total_records

        # Record sync time for change detection
        from datetime import datetime
        app_state.last_sync_time = datetime.now().isoformat()
        print(f"[Dataset] Sync time recorded: {app_state.last_sync_time}")

        # Invalidate query cache for this spreadsheet (data has changed)
        invalidate_spreadsheet_cache(spreadsheet_id)
        print(f"[Cache] Invalidated query cache for new dataset")

        # Get data summary from onboarding
        profiles = app_state.profile_store.get_all_profiles()
        data_summary = app_state.onboarding.get_data_summary(profiles)

        print(f"[Dataset] Successfully loaded: {total_tables} tables, {total_records} records")
        print(f"[Dataset] Total loaded spreadsheets: {len(app_state.loaded_spreadsheet_ids)}")

        return {
            'success': True,
            'stats': {
                'totalTables': total_tables,
                'totalRecords': total_records,
                'sheetCount': len(prefixed_sheets_with_tables),
                'sheets': [t.get('original_sheet_name', k) for k, tables_list in prefixed_sheets_with_tables.items() for t in tables_list[:1]] or list(prefixed_sheets_with_tables.keys()),
                'detectedTables': detected_tables,
                'profiledTables': profile_count,
                'loadedSpreadsheets': app_state.loaded_spreadsheet_ids
            },
            'data_summary': data_summary
        }

    except Exception as e:
        print(f"[Dataset] Exception: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            'success': False,
            'error': str(e)
        }


def check_and_refresh_data() -> bool:
    """
    Automatically check for data changes and refresh if needed.
    Returns True if data was refreshed.

    OPTIMIZATION: Session-based caching.
    If data already loaded in this session, skip entirely.
    User must explicitly sync to reload data.
    """
    try:
        # FAST PATH: If data already loaded in session, skip entirely
        # This ensures data loads ONCE after sync, never again until explicit re-sync
        if app_state.data_loaded:
            print("  ✓ Data already loaded in session - skipping refresh check")
            return False

        from data_sources.gsheet.connector import get_sheet_cache

        # Secondary check: If sheet cache is still valid (saves 10-25s)
        cache = get_sheet_cache()

        # Get spreadsheet_id from app_state or fallback to config
        spreadsheet_id = app_state.current_spreadsheet_id
        if not spreadsheet_id:
            try:
                config = get_config()
                spreadsheet_id = config.google_sheets.spreadsheet_id  # Typed config access
                if spreadsheet_id:
                    app_state.current_spreadsheet_id = spreadsheet_id  # Cache for future use
                    print(f"  [Cache] Loaded spreadsheet_id from config: {spreadsheet_id[:20]}...")
            except Exception as e:
                print(f"  [Cache] Failed to load from config: {e}")
                spreadsheet_id = ""

        # Debug: Show cache status
        print(f"  [Cache] Using spreadsheet_id: '{spreadsheet_id[:20] if spreadsheet_id else 'EMPTY'}...'")

        if not spreadsheet_id:
            print("  [Cache] WARNING: No spreadsheet_id set, cannot use cache")
        elif cache.is_valid(spreadsheet_id):
            print("  ✓ Sheet cache valid, skipping download")
            return False  # No refresh needed, cache is fresh
        else:
            print("  [Cache] Cache miss or expired, will fetch sheets")

        # SLOW PATH: Cache expired or missing - fetch and check for changes
        sheets_with_tables = fetch_sheets_with_tables()

        # Store in cache for future queries
        if spreadsheet_id:
            cache.set_cached_data(spreadsheet_id, sheets_with_tables)
            print(f"  [Cache] Stored sheets data in cache for 300s")

        needs_refresh_flag, full_reset, changed_sheets = needs_refresh(sheets_with_tables)

        if needs_refresh_flag:
            store = app_state.initialize_vector_store()

            if full_reset:
                store.clear_collection()
                load_snapshot(sheets_with_tables, full_reset=True)
                store.rebuild()
            else:
                source_ids = []
                for sheet_name in changed_sheets:
                    if sheet_name in sheets_with_tables and sheets_with_tables[sheet_name]:
                        source_id = sheets_with_tables[sheet_name][0].get('source_id')
                        if source_id:
                            source_ids.append(source_id)

                load_snapshot(sheets_with_tables, full_reset=False, changed_sheets=changed_sheets)

                if source_ids:
                    store.rebuild(source_ids=source_ids)
                else:
                    store.rebuild()

            # Re-profile changed tables
            _reprofile_tables(changed_sheets, sheets_with_tables)

            return True

        return False

    except Exception as e:
        print(f"[Refresh] Error: {e}")
        return False


def _reprofile_tables(changed_sheets: List[str], sheets_with_tables: Dict):
    """Re-profile tables after data refresh - uses parallel execution"""
    try:
        profiler = DataProfiler()

        # Collect all table names to reprofile
        table_names_to_reprofile = []
        for sheet_name in changed_sheets:
            tables = sheets_with_tables.get(sheet_name, [])
            for table in tables:
                table_name = table.get('title', table.get('table_id', ''))
                if table_name:
                    table_names_to_reprofile.append(table_name)

        if not table_names_to_reprofile:
            return

        def reprofile_single_table(table_name: str):
            """Reprofile a single table - thread-safe"""
            try:
                thread_db = DuckDBManager()
                df = thread_db.query(f'SELECT * FROM "{table_name}" LIMIT 10000')
                profile = profiler.profile_table(table_name, df)
                return table_name, profile, None
            except Exception as e:
                return table_name, None, str(e)

        # Parallelize reprofiling with 5 workers
        print(f"  [Reprofile] Starting parallel reprofiling of {len(table_names_to_reprofile)} tables...")
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {executor.submit(reprofile_single_table, t): t for t in table_names_to_reprofile}
            for future in as_completed(futures):
                table_name, profile, error = future.result()
                if profile:
                    app_state.profile_store.set_profile(table_name, profile)
                else:
                    print(f"  [Reprofile] Warning: Could not reprofile {table_name}: {error}")

        app_state.profile_store.save_profiles()

        # Refresh entity extractor with learned values from profiles
        app_state.entity_extractor.refresh_from_profiles(app_state.profile_store)
    except Exception as e:
        print(f"[Reprofile] Error: {e}")


# ============================================================================
# PROJECTION HANDLERS - Handle projection/forecast queries
# ============================================================================

def _handle_projection(
    projection_intent,
    previous_turn,
    question: str,
    ctx,
    app_state,
    is_tamil: bool
) -> Optional[Dict[str, Any]]:
    """
    Handle projection requests using previous trend/comparison context.

    Args:
        projection_intent: Detected ProjectionIntent
        previous_turn: Previous QueryTurn with trend data
        question: Original user question
        ctx: QueryContext
        app_state: AppState
        is_tamil: Whether response should be in Tamil

    Returns:
        Response dict with projected value and explanation
    """
    from analytics_engine.projection_calculator import (
        get_projection_calculator,
        extract_trend_context,
    )
    from utils.projection_detector import ProjectionType

    print("    [Projection Handler]")

    # Extract trend context from previous turn
    trend_context = extract_trend_context(previous_turn)

    if not trend_context:
        print("      ! No trend context available in previous turn")

        # Check if this was a rank query - provide more specific guidance
        query_plan = getattr(previous_turn, 'query_plan', {}) or {}
        query_type = query_plan.get('query_type', '')
        result_values = getattr(previous_turn, 'result_values', {}) or {}

        # Try to extract what item user is asking about
        item_name = None
        item_type = None
        dimension_map = {
            'category': 'Category', 'product_category': 'Category',
            'product': 'Product', 'item': 'Product',
            'state': 'State', 'branch': 'Branch',
            'region': 'Region', 'area': 'Area',
            'employee': 'Employee'
        }

        for col_name, col_value in result_values.items():
            col_lower = col_name.lower()
            for pattern, label in dimension_map.items():
                if pattern in col_lower and isinstance(col_value, str):
                    item_name = col_value
                    item_type = label.lower()
                    break
            if item_name:
                break

        if query_type in ['rank', 'extrema_lookup', 'aggregation_on_subset'] and item_name:
            # User is asking about a specific item from rank query
            print(f"      → Previous was rank query with top item: {item_name}")

            # Check if user is referring to "top item" / "leading category" pattern
            leading_patterns_ta = ['முன்னணி', 'முதல்', 'டாப்', 'அதிகமான', 'best', 'top', 'highest']
            is_referring_to_top = any(p in question.lower() for p in leading_patterns_ta)

            if is_tamil:
                if is_referring_to_top:
                    message = (
                        f"ஓ, நீங்கள் முன்னணி {item_type or 'item'} '{item_name}' பற்றி கேட்கிறீர்கள்! "
                        f"அதன் போக்கை முதலில் பார்க்கணும். "
                        f"இப்படி கேளுங்க: '{item_name} மாதவாரி விற்பனை போக்கு காட்டு'"
                    )
                else:
                    message = (
                        f"'{item_name}' பற்றிய போக்கு தகவல் இல்லை. "
                        f"போக்கை பார்க்க, '{item_name} மாதவாரி விற்பனை போக்கை காட்டு' என்று கேளுங்கள்."
                    )
            else:
                if is_referring_to_top:
                    message = (
                        f"Oh, you're asking about the top {item_type or 'item'} '{item_name}'! "
                        f"To project its future, I need to see its trend first. "
                        f"Try asking: 'Show me the monthly sales trend for {item_name}'"
                    )
                else:
                    message = (
                        f"I don't have trend data for {item_name} yet. "
                        f"To project, first ask: 'Show me the sales trend for {item_name} across months'"
                    )
        else:
            message = (
                "முந்தைய கேள்வியில் போக்கு தகவல் இல்லை. முதலில் ஒரு போக்கு கேள்வி கேளுங்கள், எ.கா.: 'மாதவாரியான விற்பனை போக்கை காட்டு'"
                if is_tamil else
                "I don't have trend data from your previous question. "
                "Please ask a trend question first, like 'Show me the sales trend across months'."
            )

        return {
            'success': True,
            'explanation': message,
            'data': None,
            'is_projection': True,
            'projection_failed': True,
            'error_type': 'no_trend_context'
        }

    print(f"      Trend context extracted:")
    print(f"        Direction: {trend_context.direction}")
    print(f"        Slope: {trend_context.slope:.2f}")
    print(f"        End value: {trend_context.end_value:.2f}")
    print(f"        Data points: {trend_context.data_points}")

    # Calculate projection
    calculator = get_projection_calculator()
    result = calculator.calculate(
        trend_context=trend_context,
        target_period=projection_intent.target_period or 'next_period',
        periods_ahead=projection_intent.target_period_count,
        target_value=projection_intent.target_value
    )

    print(f"      Projection calculated:")
    print(f"        Projected value: {result.projected_value:.2f}")
    print(f"        Confidence: {result.confidence_level.value} ({result.confidence_score:.0%})")
    print(f"        Method: {result.method_used.value}")

    # Generate natural language explanation
    explanation = _generate_projection_explanation(
        result=result,
        trend_context=trend_context,
        projection_intent=projection_intent,
        is_tamil=is_tamil
    )

    # Store projection turn in context for potential follow-ups
    from utils.query_context import QueryTurn
    projection_turn = QueryTurn(
        question=question,
        resolved_question=question,
        entities=previous_turn.entities.copy() if previous_turn.entities else {},
        table_used=previous_turn.table_used or '',
        filters_applied=previous_turn.filters_applied if previous_turn.filters_applied else [],
        result_summary=f"Projection: {result.projected_value:.0f} ({result.confidence_level.value} confidence)",
        was_followup=True,
        confidence=result.confidence_score,
        result_values={
            'projected_value': result.projected_value,
            'confidence_level': result.confidence_level.value,
            'confidence_score': result.confidence_score,
            'base_value': result.base_value,
            'expected_change': result.expected_change,
            'expected_change_percent': result.expected_change_percent,
            'projection_period': result.projection_period,
            'method_used': result.method_used.value
        },
        query_plan={
            'query_type': 'projection',
            'projection': {
                'type': projection_intent.projection_type.value,
                'target_period': result.projection_period,
                'periods_ahead': result.periods_ahead
            },
            'analysis': {
                'direction': trend_context.direction,
                'slope': trend_context.slope,
                'normalized_slope': trend_context.normalized_slope,
                'end_value': trend_context.end_value,
                'values': trend_context.values
            }
        }
    )
    ctx.add_turn(projection_turn)

    # Build response
    return {
        'success': True,
        'explanation': explanation,
        'data': [{
            'period': result.projection_period,
            'projected_value': result.projected_value,
            'confidence': result.confidence_level.value,
            'confidence_score': result.confidence_score,
            'range_low': result.range_low,
            'range_high': result.range_high,
            'base_value': result.base_value,
            'expected_change': result.expected_change,
            'expected_change_percent': result.expected_change_percent
        }],
        'is_projection': True,
        'projection_details': {
            'method': result.method_used.value,
            'confidence_score': result.confidence_score,
            'confidence_level': result.confidence_level.value,
            'periods_ahead': result.periods_ahead,
            'trend_direction': trend_context.direction,
            'trend_slope': trend_context.slope
        }
    }


def _generate_projection_explanation(
    result,
    trend_context,
    projection_intent,
    is_tamil: bool
) -> str:
    """
    Generate natural language explanation for projection.

    Uses Indian number formatting (lakhs/crores) and is TTS-friendly.
    """
    from explanation_layer.explainer_client import _format_number_indian

    # Format numbers for natural speech
    projected = _format_number_indian(result.projected_value)
    base = _format_number_indian(result.base_value)
    change = _format_number_indian(abs(result.expected_change))
    change_pct = abs(result.expected_change_percent)

    # Confidence qualifiers
    conf_level = result.confidence_level.value
    if conf_level == 'high':
        conf_en = "Based on the strong trend"
        conf_ta = "வலுவான போக்கின் அடிப்படையில்"
    elif conf_level == 'medium':
        conf_en = "Based on current trends"
        conf_ta = "தற்போதைய போக்கின் அடிப்படையில்"
    else:
        conf_en = "With some uncertainty"
        conf_ta = "சில நிச்சயமின்மையுடன்"

    # Direction words
    if result.expected_change > 0:
        dir_en = "up"
        dir_ta = "அதிகரிப்பு"
    elif result.expected_change < 0:
        dir_en = "down"
        dir_ta = "குறைவு"
    else:
        dir_en = "stable"
        dir_ta = "மாற்றமில்லாமல்"

    # Format period name for natural speech
    period = result.projection_period
    if period:
        period = period.replace('_', ' ').replace('next ', 'next ')
        # Capitalize first letter of each word
        period = ' '.join(word.capitalize() for word in period.split())

    if is_tamil:
        explanation = f"{conf_ta}, {period} விற்பனை சுமார் {projected} ஆக இருக்கும் என்று எதிர்பார்க்கப்படுகிறது."

        if result.expected_change != 0:
            if result.expected_change > 0:
                explanation += f" இது தற்போதைய {base} இலிருந்து சுமார் {change} ({change_pct:.0f}%) {dir_ta}."
            else:
                explanation += f" இது தற்போதைய {base} இலிருந்து சுமார் {change} ({change_pct:.0f}%) {dir_ta}."
        else:
            explanation += " போக்கு நிலையானதாக இருப்பதால், மதிப்பு மாறாமல் இருக்கும்."

        # Add confidence range for lower confidence
        if conf_level == 'low':
            range_low = _format_number_indian(result.range_low)
            range_high = _format_number_indian(result.range_high)
            explanation += f" மதிப்பு {range_low} முதல் {range_high} வரை இருக்கலாம்."

    else:
        explanation = f"{conf_en}, {period} sales would be around {projected}."

        if result.expected_change != 0:
            explanation += f" That's about {change} ({change_pct:.0f}%) {dir_en} from current."
        else:
            explanation += " The stable trend suggests values will remain similar."

        # Add confidence range for lower confidence
        if conf_level == 'low':
            range_low = _format_number_indian(result.range_low)
            range_high = _format_number_indian(result.range_high)
            explanation += f" It could range from {range_low} to {range_high}."

    return explanation


# ============================================================================
# CORRECTION HANDLERS - Handle user corrections to previous queries
# ============================================================================

def _handle_correction(
    correction_intent,
    previous_turn,
    question: str,
    ctx,
    app_state,
    is_tamil: bool
) -> Optional[Dict[str, Any]]:
    """
    Route correction to appropriate handler based on correction type.
    """
    from utils.correction_detector import CorrectionType

    correction_type = correction_intent.correction_type

    if correction_type == CorrectionType.TABLE:
        return _handle_table_correction(correction_intent, previous_turn, question, ctx, app_state, is_tamil)

    elif correction_type == CorrectionType.FILTER:
        return _handle_filter_correction(correction_intent, previous_turn, question, ctx, app_state, is_tamil)

    elif correction_type == CorrectionType.FILTER_REMOVE:
        return _handle_filter_removal(correction_intent, previous_turn, question, ctx, app_state, is_tamil)

    elif correction_type == CorrectionType.METRIC:
        return _handle_metric_correction(correction_intent, previous_turn, question, ctx, app_state, is_tamil)

    elif correction_type == CorrectionType.NEGATION:
        return _handle_negation(correction_intent, previous_turn, question, ctx, app_state, is_tamil)

    elif correction_type == CorrectionType.REVERT:
        return _handle_revert(correction_intent, previous_turn, question, ctx, app_state, is_tamil)

    elif correction_type == CorrectionType.MULTIPLE:
        return _handle_multiple_corrections(correction_intent, previous_turn, question, ctx, app_state, is_tamil)

    return None


def _handle_table_correction(
    correction_intent,
    previous_turn,
    question: str,
    ctx,
    app_state,
    is_tamil: bool
) -> Optional[Dict[str, Any]]:
    """
    Handle table correction requests - FULLY AUTOMATIC (no user prompts).

    Strategies:
    1. Explicit table name mentioned -> use it directly
    2. Table type hint (summary/raw/category) -> auto-select best matching type
    3. Ambiguous ("other table") -> auto-select using smart logic
    """
    print("    [Table Correction Handler]")

    # Get profile store for table lookups
    profile_store = app_state.profile_store

    # Case 1: Explicit table name mentioned
    if correction_intent.explicit_table:
        explicit_table = correction_intent.explicit_table
        print(f"      Explicit table: {explicit_table}")

        # Verify table exists
        if profile_store.get_profile(explicit_table):
            return _re_execute_with_table(
                previous_turn=previous_turn,
                forced_table=explicit_table,
                ctx=ctx,
                app_state=app_state,
                is_tamil=is_tamil,
                correction_type="table",
                correction_message=question  # Pass angry message for emotional response
            )
        else:
            print(f"      ! Table '{explicit_table}' not found")
            # Try fuzzy match
            all_tables = profile_store.get_table_names() or []
            for table in all_tables:
                if explicit_table.lower() in table.lower():
                    print(f"      → Fuzzy match: {table}")
                    return _re_execute_with_table(
                        previous_turn=previous_turn,
                        forced_table=table,
                        ctx=ctx,
                        app_state=app_state,
                        is_tamil=is_tamil,
                        correction_type="table",
                        correction_message=question  # Pass angry message for emotional response
                    )

    # Case 2: Table type hint or ambiguous correction
    # Auto-select the best alternative table
    selected_table = _auto_select_alternative_table(
        previous_table=previous_turn.table_used,
        alternatives=previous_turn.routing_alternatives or [],
        correction_text=question,
        profile_store=profile_store,
        table_type_hint=correction_intent.table_type_hint
    )

    if selected_table:
        print(f"      Auto-selected table: {selected_table}")
        return _re_execute_with_table(
            previous_turn=previous_turn,
            forced_table=selected_table,
            ctx=ctx,
            app_state=app_state,
            is_tamil=is_tamil,
            correction_type="table",
            correction_message=question  # Pass angry message for emotional response
        )

    # Fallback: Re-route the original query
    print("      ! No suitable alternative found, re-routing query")
    return None  # Continue normal pipeline to re-route


def _auto_select_alternative_table(
    previous_table: str,
    alternatives: List[tuple],
    correction_text: str,
    profile_store,
    table_type_hint: Optional[str] = None
) -> Optional[str]:
    """
    Automatically select the best alternative table without asking user.

    Priority:
    1. If correction mentions keywords (raw, summary, detail) -> match table type
    2. Pick table type opposite to previous (summary -> transactional)
    3. Pick highest-scored alternative that isn't the previous table
    """
    # Get previous table type
    prev_profile = profile_store.get_profile(previous_table) if previous_table else {}
    prev_type = prev_profile.get('table_type', 'unknown') if prev_profile else 'unknown'

    # Check for type hints in correction text
    type_keywords = {
        'raw': 'transactional',
        'detail': 'transactional',
        'detailed': 'transactional',
        'transaction': 'transactional',
        'daily': 'transactional',
        'individual': 'transactional',
        'summary': 'summary',
        'aggregate': 'summary',
        'aggregated': 'summary',
        'total': 'summary',
        'totals': 'summary',
        'monthly': 'summary',
        'overall': 'summary',
        'category': 'category',
        'breakdown': 'category',
    }

    target_type = table_type_hint  # Use provided hint first

    # Check for keywords in correction text
    if not target_type:
        correction_lower = correction_text.lower()
        for keyword, table_type in type_keywords.items():
            if keyword in correction_lower:
                target_type = table_type
                print(f"      Detected keyword '{keyword}' -> target type: {table_type}")
                break

    # If no explicit hint, prefer opposite type
    if not target_type or target_type == 'other':
        type_opposites = {
            'summary': 'transactional',
            'transactional': 'summary',
            'aggregate': 'transactional',
            'category': 'transactional',
            'unknown': 'transactional'  # Default to transactional for more detail
        }
        target_type = type_opposites.get(prev_type, 'transactional')
        print(f"      Previous type '{prev_type}' -> target opposite: {target_type}")

    # Score and select best alternative
    best_table = None
    best_score = -1

    # First try alternatives from routing
    if alternatives:
        for item in alternatives:
            # Handle both tuple (table_name, score) and just table_name
            if isinstance(item, tuple):
                table_name, score = item
            else:
                table_name = item
                score = 30  # Default score

            if table_name == previous_table:
                continue  # Skip previous table

            profile = profile_store.get_profile(table_name)
            if not profile:
                continue

            table_type = profile.get('table_type', 'unknown')

            # Boost score if type matches target
            adjusted_score = score
            if target_type and table_type == target_type:
                adjusted_score += 20
                print(f"      Boosted {table_name} (type={table_type} matches target)")

            if adjusted_score > best_score:
                best_score = adjusted_score
                best_table = table_name

    # If no good alternative from routing, search all tables
    if not best_table:
        all_tables = profile_store.get_table_names() or []
        for table_name in all_tables:
            if table_name == previous_table:
                continue

            profile = profile_store.get_profile(table_name)
            if not profile:
                continue

            table_type = profile.get('table_type', 'unknown')

            # Score based on type match
            score = 30 if table_type == target_type else 10

            if score > best_score:
                best_score = score
                best_table = table_name

    return best_table


def _handle_filter_correction(
    correction_intent,
    previous_turn,
    question: str,
    ctx,
    app_state,
    is_tamil: bool
) -> Optional[Dict[str, Any]]:
    """
    Handle filter correction requests.

    Process:
    1. Parse old_value -> new_value from correction
    2. Update entities from previous turn
    3. Re-run query with corrected entities and modified question text
    """
    print("    [Filter Correction Handler]")

    # Get entities from previous turn
    corrected_entities = (previous_turn.entities or {}).copy()
    old_values = {}

    # Apply filter corrections
    for correction in (correction_intent.filter_corrections or []):
        field = correction.get('field')
        old_value = correction.get('old_value')
        new_value = correction.get('new_value')

        if not new_value:
            continue

        # Map field name to entity key
        field_mapping = {
            'month': 'month',
            'location': 'location',
            'category': 'category',
            'state': 'location',
            'city': 'location',
            'area': 'location',
            'region': 'location',
            'inferred': None  # Will try to infer
        }

        entity_key = field_mapping.get(field, field)

        # If field is inferred, try to determine it
        if entity_key is None or field == 'inferred':
            # Check what the new value looks like
            new_lower = new_value.lower()
            months = ['january', 'february', 'march', 'april', 'may', 'june',
                     'july', 'august', 'september', 'october', 'november', 'december',
                     'jan', 'feb', 'mar', 'apr', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec']
            if new_lower in months:
                entity_key = 'month'
                new_value = new_value.capitalize()
            else:
                # Try to match with previous turn's entities
                for key, prev_value in corrected_entities.items():
                    if key in ['month', 'location', 'category', 'metric']:
                        entity_key = key
                        break
                if not entity_key:
                    entity_key = 'location'  # Default assumption

        print(f"      Correcting {entity_key}: {old_value} -> {new_value}")
        # Store old value for question text replacement
        # If old_value not explicitly provided, get it from previous turn's entities
        if old_value:
            old_values[entity_key] = old_value
        elif previous_turn.entities and previous_turn.entities.get(entity_key):
            # Use the previous turn's entity value as old_value for text replacement
            old_values[entity_key] = previous_turn.entities[entity_key]
            print(f"      Using previous entity as old_value: {old_values[entity_key]}")
        corrected_entities[entity_key] = new_value

    # Re-execute with corrected entities and old values for text replacement
    # Pass user's correction message for emotional intelligence (apologies, etc.)
    return _re_execute_with_entities(
        previous_turn=previous_turn,
        corrected_entities=corrected_entities,
        ctx=ctx,
        app_state=app_state,
        is_tamil=is_tamil,
        correction_type="filter",
        old_values=old_values,
        user_correction_message=question  # Pass user's angry message for empathy
    )


def _handle_filter_removal(
    correction_intent,
    previous_turn,
    question: str,
    ctx,
    app_state,
    is_tamil: bool
) -> Optional[Dict[str, Any]]:
    """
    Handle filter removal requests (e.g., "consider all months", "don't limit to November").

    CRITICAL: This function preserves the original query plan structure (query_type, aggregation, etc.)
    and only removes the date-related filters. This ensures "highest selling day for UPI" stays as
    an extrema_lookup query even when removing the month filter, instead of becoming a trend analysis.

    Process:
    1. Get filter_removals list from correction_intent
    2. Get the ORIGINAL query_plan from previous turn (preserves query_type, aggregation, etc.)
    3. Remove date-related filters from subset_filters in the plan
    4. Re-execute with the MODIFIED PLAN (not regenerated from scratch)
    """
    import copy
    import time
    print("    [Filter Removal Handler - Preserving Query Structure]")

    # Get filters to remove
    filter_removals = correction_intent.filter_removals or []
    print(f"      Filters to remove: {filter_removals}")

    # Get the ORIGINAL query plan from previous turn
    original_plan = previous_turn.query_plan
    if not original_plan:
        print("      WARNING: No original query_plan found, falling back to re-execution")
        # Fallback to entity-based re-execution if no plan stored
        corrected_entities = (previous_turn.entities or {}).copy()
        for filter_name in filter_removals:
            filter_to_entity_mapping = {
                'month': ['month', 'specific_date', 'date_range', 'time_period'],
                'date': ['month', 'specific_date', 'date_range', 'time_period'],
                'category': ['category'],
                'location': ['location', 'state', 'city', 'branch'],
            }
            for entity_key in filter_to_entity_mapping.get(filter_name, [filter_name]):
                if entity_key in corrected_entities:
                    corrected_entities.pop(entity_key)
        return _re_execute_with_entities(
            previous_turn=previous_turn,
            corrected_entities=corrected_entities,
            ctx=ctx,
            app_state=app_state,
            is_tamil=is_tamil,
            correction_type="filter_removal",
            old_values={},
            user_correction_message=question
        )

    # Deep copy the plan to avoid modifying the original
    modified_plan = copy.deepcopy(original_plan)
    removed_filters = []

    # Define which columns are date-related
    date_related_columns = ['Date', 'date', 'month', 'Month', 'year', 'Year', 'time', 'Time',
                           'created_at', 'updated_at', 'timestamp', 'Timestamp']

    # Remove date-related filters from subset_filters
    if 'subset_filters' in modified_plan and modified_plan['subset_filters']:
        original_filters = modified_plan['subset_filters']
        new_filters = []

        for f in original_filters:
            column = f.get('column', '')
            # Check if this filter is date-related (should be removed)
            is_date_filter = any(dc.lower() in column.lower() for dc in date_related_columns)

            if is_date_filter and any(fr in ['month', 'date', 'time', 'year'] for fr in filter_removals):
                removed_filters.append(f"  {column} {f.get('operator')} {f.get('value')}")
                print(f"      Removed filter: {column} {f.get('operator')} {f.get('value')}")
            else:
                new_filters.append(f)

        modified_plan['subset_filters'] = new_filters
        print(f"      Filters kept: {len(new_filters)}, Removed: {len(removed_filters)}")

    # Also remove from filters array if present
    if 'filters' in modified_plan and modified_plan['filters']:
        original_filters = modified_plan['filters']
        new_filters = []

        for f in original_filters:
            column = f.get('column', '')
            is_date_filter = any(dc.lower() in column.lower() for dc in date_related_columns)

            if is_date_filter and any(fr in ['month', 'date', 'time', 'year'] for fr in filter_removals):
                removed_filters.append(f"  {column} {f.get('operator')} {f.get('value')}")
                print(f"      Removed filter from 'filters': {column}")
            else:
                new_filters.append(f)

        modified_plan['filters'] = new_filters

    print(f"      Query type preserved: {modified_plan.get('query_type')}")
    print(f"      Modified plan subset_filters: {modified_plan.get('subset_filters')}")

    # Execute with the modified plan directly (skip planner!)
    return _execute_with_modified_plan(
        modified_plan=modified_plan,
        original_question=previous_turn.question,
        original_entities=previous_turn.entities or {},
        ctx=ctx,
        app_state=app_state,
        is_tamil=is_tamil,
        correction_type="filter_removal",
        user_correction_message=question
    )


def _execute_with_modified_plan(
    modified_plan: Dict[str, Any],
    original_question: str,
    original_entities: Dict[str, Any],
    ctx,
    app_state,
    is_tamil: bool,
    correction_type: str,
    user_correction_message: str = None
) -> Dict[str, Any]:
    """
    Execute a query using a pre-built (modified) plan, skipping the planner.

    This is used for filter removal corrections where we need to preserve
    the original query structure (query_type, aggregation, etc.) but remove
    specific filters.
    """
    import time
    from execution_layer.executor import execute_plan, ADVANCED_QUERY_TYPES
    from execution_layer.sql_compiler import compile_sql
    from explanation_layer.explainer_client import explain_results
    from utils.query_context import QueryTurn
    import copy

    step_start = time.time()
    table = modified_plan.get('table')

    try:
        print("\n[EXECUTE] Running with MODIFIED plan (preserving query structure)...")
        print(f"  Table: {table}")
        print(f"  Query type: {modified_plan.get('query_type')}")
        print(f"  Original question: {(original_question or '')[:80]}...")

        # Step 1: Execute SQL with modified plan
        print("  [Step 1/2] Executing query with modified plan...")
        query_type = modified_plan.get('query_type')

        if query_type in ADVANCED_QUERY_TYPES:
            print(f"    → Advanced query type: {query_type}")
            result = execute_plan(modified_plan)
            final_sql = f"[Advanced {query_type} query - see analysis]"
            # Handle analysis from advanced queries
            if hasattr(result, 'attrs') and 'analysis' in result.attrs:
                analysis = result.attrs['analysis']
                modified_plan['analysis'] = analysis if isinstance(analysis, dict) else {}
            elif isinstance(result, dict) and 'analysis' in result:
                modified_plan['analysis'] = result.get('analysis', {})
        else:
            sql = compile_sql(modified_plan)
            print(f"    → SQL: {sql[:150]}...")
            result, final_sql = app_state.query_healer.execute_with_healing(sql, modified_plan)

        print(f"    ✓ Query executed ({time.time() - step_start:.2f}s)")

        # Check for empty results
        no_results = False
        row_count = len(result) if result is not None and hasattr(result, '__len__') else 0
        if result is None or row_count == 0:
            no_results = True
            print(f"    ! Query returned 0 rows")
        else:
            print(f"    ✓ Query returned {row_count} rows")

        # Step 2: Generate explanation
        print("  [Step 2/2] Generating explanation (LLM call)...")
        step_start = time.time()
        emotional_message = user_correction_message if user_correction_message else original_question
        explanation = explain_results(
            result,
            query_plan=modified_plan,
            original_question=original_question,
            raw_user_message=emotional_message
        )
        print(f"    ✓ Explanation generated ({time.time() - step_start:.2f}s)")

        # NOTE: explain_results() already handles empty results - no double response needed

        # Translate if Tamil
        if is_tamil:
            from utils.translation import translate_to_tamil
            explanation = translate_to_tamil(explanation)

        # Extract result values for context
        result_values = _extract_result_values(result, modified_plan) if result is not None else {}
        if result_values:
            print(f"  ✓ Extracted result values for context: {result_values}")

        # Update entities by removing date-related ones
        corrected_entities = original_entities.copy()
        for key in ['month', 'specific_date', 'date_range', 'time_period']:
            corrected_entities.pop(key, None)

        # Store turn in context
        stored_plan = copy.deepcopy(modified_plan)
        turn = QueryTurn(
            question=original_question,
            resolved_question=original_question,
            entities=corrected_entities,
            table_used=table,
            filters_applied=modified_plan.get('filters', []),
            result_summary=f"{row_count} rows returned",
            sql_executed=final_sql,
            was_followup=False,
            confidence=1.0,
            result_values=result_values,
            query_plan=stored_plan,
            routing_alternatives=[],
            was_correction=True,
            corrected_from_turn=len(ctx.turns) - 1 if ctx.turns else None,
            correction_type=correction_type
        )
        ctx.add_turn(turn)

        # Build response
        data_list = None
        if result is not None and hasattr(result, 'to_dict'):
            data_list = _sanitize_for_json(result.to_dict('records'))

        print("\n[SUCCESS] Query completed with modified plan (filter removal)!")
        print("=" * 60 + "\n")

        response = {
            'success': True,
            'explanation': explanation,
            'data': data_list,
            'plan': modified_plan,
            'table_used': table,
            'routing_confidence': 1.0,
            'was_followup': False,
            'was_correction': True,
            'correction_type': correction_type,
            'entities_extracted': {k: v for k, v in corrected_entities.items() if v and k != 'raw_question'},
            'data_refreshed': False,
            'no_results': no_results
        }
        return _sanitize_for_json(response)

    except Exception as e:
        import traceback
        error_str = str(e)
        error_trace = traceback.format_exc()
        print(f"\n[ERROR] Failed to execute with modified plan: {error_str}")
        print(f"  Traceback:\n{error_trace}")

        return {
            'success': False,
            'error': f"Error executing query: {error_str[:100]}",
            'error_type': 'execution_error'
        }


def _handle_metric_correction(
    correction_intent,
    previous_turn,
    question: str,
    ctx,
    app_state,
    is_tamil: bool
) -> Optional[Dict[str, Any]]:
    """
    Handle metric correction requests.

    Process:
    1. Parse old_metric -> new_metric from correction
    2. Update entities with new metric
    3. Re-execute query with modified question text
    """
    print("    [Metric Correction Handler]")

    # Get entities from previous turn
    corrected_entities = (previous_turn.entities or {}).copy()
    old_values = {}

    # Apply metric corrections
    for correction in (correction_intent.metric_corrections or []):
        old_metric = correction.get('old_metric')
        new_metric = correction.get('new_metric')

        if new_metric:
            print(f"      Correcting metric: {old_metric} -> {new_metric}")
            # Store old metric for question text replacement
            # If old_metric not explicitly provided, get it from previous turn's entities
            if old_metric:
                old_values['metric'] = old_metric
            elif previous_turn.entities and previous_turn.entities.get('metric'):
                old_values['metric'] = previous_turn.entities['metric']
                print(f"      Using previous entity as old_metric: {old_values['metric']}")
            corrected_entities['metric'] = new_metric

    # Re-execute with corrected entities and old values for text replacement
    # Pass user's correction message for emotional intelligence
    return _re_execute_with_entities(
        previous_turn=previous_turn,
        corrected_entities=corrected_entities,
        ctx=ctx,
        app_state=app_state,
        is_tamil=is_tamil,
        correction_type="metric",
        old_values=old_values,
        user_correction_message=question  # Pass for empathy
    )


def _handle_negation(
    correction_intent,
    previous_turn,
    question: str,
    ctx,
    app_state,
    is_tamil: bool
) -> Optional[Dict[str, Any]]:
    """
    Handle general negation ("that's wrong", "incorrect") with smart auto-resolution.

    Strategies (in order):
    1. If previous query had low confidence (< 0.6) -> try next best table
    2. If previous query returned 0 results -> relax filters
    3. If previous query had multiple alternatives -> try next alternative
    4. ONLY if no auto-resolution possible -> Ask for clarification
    """
    print("    [Negation Handler - Smart Auto-Resolution]")

    # Strategy 1: Low confidence -> try alternative table
    if previous_turn.confidence < 0.6 and previous_turn.routing_alternatives:
        print(f"      Previous confidence was low ({previous_turn.confidence:.0%}), trying alternative table")
        selected_table = _auto_select_alternative_table(
            previous_table=previous_turn.table_used,
            alternatives=previous_turn.routing_alternatives,
            correction_text=question,
            profile_store=app_state.profile_store,
            table_type_hint=None
        )
        if selected_table:
            return _re_execute_with_table(
                previous_turn=previous_turn,
                forced_table=selected_table,
                ctx=ctx,
                app_state=app_state,
                is_tamil=is_tamil,
                correction_type="negation_table",
                correction_message=question  # Pass angry message for emotional response
            )

    # Strategy 2: Zero results -> try relaxing filters or different table
    result_summary = previous_turn.result_summary or ""
    if "0 rows" in result_summary or "no data" in result_summary.lower():
        print("      Previous query returned no results, trying alternative approach")
        # Try alternative table first
        if previous_turn.routing_alternatives:
            selected_table = _auto_select_alternative_table(
                previous_table=previous_turn.table_used,
                alternatives=previous_turn.routing_alternatives,
                correction_text="",
                profile_store=app_state.profile_store,
                table_type_hint=None
            )
            if selected_table:
                return _re_execute_with_table(
                    previous_turn=previous_turn,
                    forced_table=selected_table,
                    ctx=ctx,
                    app_state=app_state,
                    is_tamil=is_tamil,
                    correction_type="negation_empty",
                    correction_message=question  # Pass angry message for emotional response
                )

    # Strategy 3: Has alternatives -> try next one
    if previous_turn.routing_alternatives:
        selected_table = _auto_select_alternative_table(
            previous_table=previous_turn.table_used,
            alternatives=previous_turn.routing_alternatives,
            correction_text=question,
            profile_store=app_state.profile_store,
            table_type_hint=None
        )
        if selected_table:
            print(f"      Trying alternative table: {selected_table}")
            return _re_execute_with_table(
                previous_turn=previous_turn,
                forced_table=selected_table,
                ctx=ctx,
                app_state=app_state,
                is_tamil=is_tamil,
                correction_type="negation_alternative",
                correction_message=question  # Pass angry message for emotional response
            )

    # Strategy 4: Ask for clarification (last resort)
    print("      No auto-resolution possible, asking for clarification")
    ctx.set_pending_correction_state(
        original_question=question,
        correction_type="negation",
        is_tamil=is_tamil
    )

    if is_tamil:
        message = """என்ன தவறு என்று என்னால் புரிந்துகொள்ள முடியவில்லை. தயவுசெய்து குறிப்பிடுங்கள்:
- வேறு table வேண்டும் என்றால் "summary table பாரு" போன்று சொல்லுங்கள்
- filter மாற்ற வேண்டும் என்றால் "September மாதம்" போன்று சொல்லுங்கள்
- வேறு metric வேண்டும் என்றால் "profit காட்டு" போன்று சொல்லுங்கள்"""
    else:
        message = """I'm not sure what to correct. Could you be more specific?
- For a different table, say something like "use the summary table"
- For a different filter, say "for September" or "in Tamil Nadu"
- For a different metric, say "show profit instead" """

    return {
        'success': True,
        'explanation': message,
        'data': None,
        'needs_clarification': True,
        'is_correction_flow': True
    }


def _handle_revert(
    correction_intent,
    previous_turn,
    question: str,
    ctx,
    app_state,
    is_tamil: bool
) -> Optional[Dict[str, Any]]:
    """
    Handle revert requests ("never mind", "go back to original").

    Process:
    1. Find the original turn before any corrections in the chain
    2. Re-execute with original parameters
    """
    print("    [Revert Handler]")

    # Find original turn before corrections
    original_turn = ctx.find_original_turn(previous_turn)

    if original_turn and original_turn != previous_turn:
        print(f"      Reverting to original query: {original_turn.question[:50]}...")

        # Re-execute original query
        return _re_execute_turn(
            turn=original_turn,
            ctx=ctx,
            app_state=app_state,
            is_tamil=is_tamil,
            mark_as_revert=True
        )
    else:
        # No original to revert to
        if is_tamil:
            message = "திரும்பிப் போக எதுவும் இல்லை. புதிய கேள்வி கேளுங்கள்."
        else:
            message = "There's nothing to revert to. This was the original query. Please ask a new question."

        return {
            'success': True,
            'explanation': message,
            'data': None
        }


def _handle_multiple_corrections(
    correction_intent,
    previous_turn,
    question: str,
    ctx,
    app_state,
    is_tamil: bool
) -> Optional[Dict[str, Any]]:
    """
    Handle multiple corrections in one message.

    Apply corrections in order: table -> filter -> metric
    """
    print("    [Multiple Corrections Handler]")

    corrected_entities = (previous_turn.entities or {}).copy()
    old_values = {}
    table_to_use = previous_turn.table_used

    # Apply filter corrections
    for correction in (correction_intent.filter_corrections or []):
        field = correction.get('field', 'inferred')
        old_value = correction.get('old_value')
        new_value = correction.get('new_value')
        if new_value:
            if field == 'inferred':
                field = 'location'  # Default
            if old_value:
                old_values[field] = old_value
            corrected_entities[field] = new_value
            print(f"      Applied filter correction: {field}={new_value}")

    # Apply metric corrections
    for correction in (correction_intent.metric_corrections or []):
        old_metric = correction.get('old_metric')
        new_metric = correction.get('new_metric')
        if new_metric:
            if old_metric:
                old_values['metric'] = old_metric
            corrected_entities['metric'] = new_metric
            print(f"      Applied metric correction: metric={new_metric}")

    # Apply table correction (if present)
    if correction_intent.explicit_table or correction_intent.table_type_hint:
        if correction_intent.explicit_table:
            table_to_use = correction_intent.explicit_table
        else:
            table_to_use = _auto_select_alternative_table(
                previous_table=previous_turn.table_used,
                alternatives=previous_turn.routing_alternatives or [],
                correction_text=question,
                profile_store=app_state.profile_store,
                table_type_hint=correction_intent.table_type_hint
            ) or previous_turn.table_used
        print(f"      Applied table correction: {table_to_use}")

    # Re-execute with all corrections
    # Pass user's correction message for emotional intelligence
    return _re_execute_with_corrections(
        previous_turn=previous_turn,
        corrected_entities=corrected_entities,
        forced_table=table_to_use,
        ctx=ctx,
        app_state=app_state,
        is_tamil=is_tamil,
        correction_type="multiple",
        old_values=old_values,
        user_correction_message=question  # Pass for empathy
    )


def _handle_pending_correction_response(
    user_response: str,
    pending_correction,
    ctx,
    app_state,
    is_tamil: bool
) -> Optional[Dict[str, Any]]:
    """
    Handle user's response to a correction clarification request.
    This is called when user was asked "what should I correct?"
    """
    print("    [Pending Correction Response Handler]")

    # Get the turn being corrected
    previous_turn = ctx.get_turn_by_index(pending_correction.previous_turn_index)
    if not previous_turn:
        return None

    # Try to detect what the user wants to correct from their response
    correction_detector = app_state.correction_detector
    correction_intent = correction_detector.detect(user_response, previous_turn)

    if correction_intent:
        print(f"      Detected correction type from response: {correction_intent.correction_type.value}")
        return _handle_correction(
            correction_intent=correction_intent,
            previous_turn=previous_turn,
            question=user_response,
            ctx=ctx,
            app_state=app_state,
            is_tamil=is_tamil
        )

    return None


def _re_execute_with_table(
    previous_turn,
    forced_table: str,
    ctx,
    app_state,
    is_tamil: bool,
    correction_type: str,
    correction_message: str = None  # The angry/emotional correction message
) -> Dict[str, Any]:
    """
    Re-execute the original query with a different table.

    Args:
        correction_message: The user's correction message (e.g., "NO! I WANT CATEGORY NOT BRANCH")
                          Used for emotional intelligence - LLM should apologize for mistakes.
    """
    print(f"      [Re-executing with table: {forced_table}]")

    # Get original question
    original_question = previous_turn.resolved_question or previous_turn.question
    entities = (previous_turn.entities or {}).copy()

    # Execute with forced table
    # Pass correction_message for emotional response, NOT the old question
    result = _execute_with_forced_table(
        original_question=previous_turn.question,
        processing_query=original_question,
        entities=entities,
        forced_table=forced_table,
        is_tamil=is_tamil,
        ctx=ctx,
        app_state=app_state,
        correction_message=correction_message  # For emotional intelligence
    )

    # Mark this as a correction turn
    if result.get('success') and ctx.turns:
        last_turn = ctx.turns[-1]
        last_turn.was_correction = True
        last_turn.corrected_from_turn = len(ctx.turns) - 2  # Previous turn
        last_turn.correction_type = correction_type

    return result


def _re_execute_with_entities(
    previous_turn,
    corrected_entities: Dict[str, Any],
    ctx,
    app_state,
    is_tamil: bool,
    correction_type: str,
    old_values: Dict[str, Any] = None,
    user_correction_message: str = None  # The user's angry/correction message for empathy
) -> Dict[str, Any]:
    """
    Re-execute the original query with corrected entities.

    Args:
        old_values: Optional dict containing old values for text replacement
                    e.g., {'metric': 'revenue'} when correcting to 'profit'
        user_correction_message: The user's raw correction message (e.g., "No! check Bangalore!")
                                 Passed to explainer for emotional intelligence
    """
    import re
    print(f"      [Re-executing with corrected entities]")

    # Get original question and table
    original_question = previous_turn.resolved_question or previous_turn.question
    processing_query = original_question
    table = previous_turn.table_used

    # For METRIC corrections, we need to modify the question text
    # because the LLM planner uses the question text to understand intent
    if correction_type == "metric" and corrected_entities.get('metric'):
        new_metric = corrected_entities['metric']
        old_metric = None

        # Try to get old metric from old_values or previous turn entities
        if old_values and old_values.get('metric'):
            old_metric = old_values['metric']
        elif previous_turn.entities and previous_turn.entities.get('metric'):
            old_metric = previous_turn.entities['metric']

        if old_metric and old_metric.lower() != new_metric.lower():
            # Replace old metric with new metric in question text
            print(f"      Replacing '{old_metric}' -> '{new_metric}' in question text")
            processing_query = re.sub(
                rf'\b{re.escape(old_metric)}\b',
                new_metric,
                processing_query,
                flags=re.IGNORECASE
            )
        else:
            # No old metric found - try to find common metric words and replace
            # Look for known metric patterns in the question
            common_metrics = ['revenue', 'profit', 'sales', 'cost', 'margin', 'income', 'expense', 'total', 'amount', 'quantity', 'count']
            for metric in common_metrics:
                if metric.lower() != new_metric.lower() and re.search(rf'\b{metric}\b', processing_query, re.IGNORECASE):
                    print(f"      Found metric '{metric}' in question, replacing with '{new_metric}'")
                    processing_query = re.sub(
                        rf'\b{metric}\b',
                        new_metric,
                        processing_query,
                        flags=re.IGNORECASE
                    )
                    break

        print(f"      Modified question: {processing_query}")

    # For FILTER corrections, also replace old filter values with new ones
    if correction_type == "filter" and old_values:
        for field, old_val in old_values.items():
            new_val = corrected_entities.get(field)
            if old_val and new_val and str(old_val).lower() != str(new_val).lower():
                print(f"      Replacing filter '{old_val}' -> '{new_val}' in question text")
                processing_query = re.sub(
                    rf'\b{re.escape(str(old_val))}\b',
                    str(new_val),
                    processing_query,
                    flags=re.IGNORECASE
                )
        print(f"      Modified question: {processing_query}")

    # Execute with corrected entities and modified question
    result = _execute_with_forced_table(
        original_question=previous_turn.question,
        processing_query=processing_query,
        entities=corrected_entities,
        forced_table=table,
        is_tamil=is_tamil,
        ctx=ctx,
        app_state=app_state,
        correction_message=user_correction_message  # Pass for emotional intelligence
    )

    # Mark this as a correction turn
    if result.get('success') and ctx.turns:
        last_turn = ctx.turns[-1]
        last_turn.was_correction = True
        last_turn.corrected_from_turn = len(ctx.turns) - 2
        last_turn.correction_type = correction_type

    return result


def _re_execute_with_corrections(
    previous_turn,
    corrected_entities: Dict[str, Any],
    forced_table: str,
    ctx,
    app_state,
    is_tamil: bool,
    correction_type: str,
    old_values: Dict[str, Any] = None,
    user_correction_message: str = None  # User's angry message for empathy
) -> Dict[str, Any]:
    """
    Re-execute with both entity and table corrections.
    """
    import re
    print(f"      [Re-executing with table={forced_table} and corrected entities]")

    original_question = previous_turn.resolved_question or previous_turn.question
    processing_query = original_question

    # Apply text replacements for metric/filter corrections
    if old_values:
        for field, old_val in old_values.items():
            new_val = corrected_entities.get(field)
            if old_val and new_val and str(old_val).lower() != str(new_val).lower():
                print(f"      Replacing '{old_val}' -> '{new_val}' in question text")
                processing_query = re.sub(
                    rf'\b{re.escape(str(old_val))}\b',
                    str(new_val),
                    processing_query,
                    flags=re.IGNORECASE
                )

    result = _execute_with_forced_table(
        original_question=previous_turn.question,
        processing_query=processing_query,
        entities=corrected_entities,
        forced_table=forced_table,
        is_tamil=is_tamil,
        ctx=ctx,
        app_state=app_state,
        correction_message=user_correction_message  # Pass for emotional intelligence
    )

    if result.get('success') and ctx.turns:
        last_turn = ctx.turns[-1]
        last_turn.was_correction = True
        last_turn.corrected_from_turn = len(ctx.turns) - 2
        last_turn.correction_type = correction_type

    return result


def _re_execute_turn(
    turn,
    ctx,
    app_state,
    is_tamil: bool,
    mark_as_revert: bool = False
) -> Dict[str, Any]:
    """
    Re-execute a specific turn (used for revert).
    """
    print(f"      [Re-executing turn: {turn.question[:50]}...]")

    result = _execute_with_forced_table(
        original_question=turn.question,
        processing_query=turn.resolved_question or turn.question,
        entities=turn.entities or {},
        forced_table=turn.table_used,
        is_tamil=is_tamil,
        ctx=ctx,
        app_state=app_state
    )

    if result.get('success') and ctx.turns and mark_as_revert:
        last_turn = ctx.turns[-1]
        last_turn.was_correction = True
        last_turn.correction_type = "revert"

    return result


def _execute_with_forced_table(
    original_question: str,
    processing_query: str,
    entities: Dict[str, Any],
    forced_table: str,
    is_tamil: bool,
    ctx: 'QueryContext',
    app_state: 'AppState',
    correction_message: str = None  # The emotional correction message for empathetic response
) -> Dict[str, Any]:
    """
    Execute a query with a specific table (after user clarification).

    This function is called when the user has responded to a clarification
    request and we need to resume the query with their selected table.

    Args:
        correction_message: The user's emotional correction (e.g., "NO! I WANT CATEGORY")
                          If provided, used for emotional intelligence instead of original_question.
    """
    import time
    step_start = time.time()

    try:
        print("\n[EXECUTE] Running with forced table...")
        print(f"  Table: {forced_table}")
        print(f"  Original question: {(original_question or '')[:80]}...")
        print(f"  Processing query: {(processing_query or '')[:80]}...")

        # Step 1: Get schema
        print("  [Step 1/5] Getting table schema...")
        schema_context = app_state.table_router.get_table_schema(forced_table)
        print(f"    ✓ Schema retrieved ({time.time() - step_start:.2f}s)")

        # Step 2: Generate plan
        print("  [Step 2/5] Generating query plan (LLM call)...")
        step_start = time.time()
        from planning_layer.planner_client import generate_plan
        from validation_layer.plan_validator import validate_plan
        from execution_layer.sql_compiler import compile_sql
        from execution_layer.executor import execute_plan, ADVANCED_QUERY_TYPES

        plan = generate_plan(processing_query, schema_context, entities=entities)
        print(f"    ✓ Plan generated ({time.time() - step_start:.2f}s)")

        # Step 3: Validate plan
        print("  [Step 3/5] Validating plan...")
        step_start = time.time()
        validate_plan(plan)
        print(f"    ✓ Plan validated ({time.time() - step_start:.2f}s)")

        # Override table in plan if needed
        plan['table'] = forced_table

        print(f"  ✓ Plan generated for table: {plan.get('table')}")

        # Step 4: Execute SQL
        print("  [Step 4/5] Executing query...")
        step_start = time.time()
        query_type = plan.get('query_type')
        if query_type in ADVANCED_QUERY_TYPES:
            print(f"    → Advanced query type: {query_type}")
            result = execute_plan(plan)
            final_sql = f"[Advanced {query_type} query - see analysis]"
            # CRITICAL: Store analysis in plan for projection support
            # Advanced queries return DataFrames with analysis in attrs
            if hasattr(result, 'attrs') and 'analysis' in result.attrs:
                analysis = result.attrs['analysis']
                plan['analysis'] = analysis if isinstance(analysis, dict) else {}
                if plan['analysis']:
                    print(f"    → Stored analysis in plan for projection: {list(plan['analysis'].keys())}")
            elif isinstance(result, dict) and 'analysis' in result:
                plan['analysis'] = result.get('analysis', {})
        else:
            sql = compile_sql(plan)
            print(f"    → SQL: {sql[:100]}...")
            result, final_sql = app_state.query_healer.execute_with_healing(sql, plan)
        print(f"    ✓ Query executed ({time.time() - step_start:.2f}s)")

        # Check for empty results
        no_results = False
        row_count = len(result) if result is not None and hasattr(result, '__len__') else 0
        if result is None or row_count == 0:
            no_results = True
            print(f"    ! Query returned 0 rows")
        else:
            print(f"    ✓ Query returned {row_count} rows")

        # Step 5: Generate explanation
        print("  [Step 5/5] Generating explanation (LLM call)...")
        step_start = time.time()
        from explanation_layer.explainer_client import explain_results
        # Use correction_message (angry message) for emotion detection if available
        # Otherwise fall back to original_question
        emotional_message = correction_message if correction_message else original_question
        explanation = explain_results(
            result,
            query_plan=plan,
            original_question=processing_query,
            raw_user_message=emotional_message  # Correction message or original for emotion
        )
        print(f"    ✓ Explanation generated ({time.time() - step_start:.2f}s)")

        # NOTE: explain_results() already handles empty results - no double response needed

        # Translate if Tamil
        if is_tamil:
            from utils.translation import translate_to_tamil
            explanation = translate_to_tamil(explanation)

        # Update context
        from utils.query_context import QueryTurn
        import copy
        # Extract key result values for pronoun resolution
        result_values = _extract_result_values(result, plan) if result is not None else {}
        if result_values:
            print(f"  ✓ Extracted result values for context: {result_values}")

        # Make a deep copy of plan to preserve analysis for projection follow-ups
        stored_plan = copy.deepcopy(plan)

        # Debug: Verify analysis is in stored_plan
        if stored_plan.get('analysis'):
            print(f"  ✓ Plan analysis preserved for projection: {list(stored_plan['analysis'].keys())}")

        turn = QueryTurn(
            question=original_question,
            resolved_question=processing_query,
            entities=entities,
            table_used=forced_table,
            filters_applied=plan.get('filters', []),
            result_summary=f"{row_count} rows returned",
            sql_executed=final_sql,
            was_followup=False,
            confidence=1.0,  # High confidence since user chose
            result_values=result_values,  # For "that state", "that branch" resolution
            query_plan=stored_plan,  # Use deep copy to preserve analysis
            routing_alternatives=[]  # No alternatives when forced
        )
        ctx.add_turn(turn)

        # Build response - sanitize numpy types for JSON serialization
        data_list = None
        if result is not None and hasattr(result, 'to_dict'):
            data_list = _sanitize_for_json(result.to_dict('records'))

        print("\n[SUCCESS] Query completed with forced table!")
        print("=" * 60 + "\n")

        # Sanitize entire response to handle numpy types in plan, entities, etc.
        response = {
            'success': True,
            'explanation': explanation,
            'data': data_list,
            'plan': plan,
            'table_used': forced_table,
            'routing_confidence': 1.0,
            'was_followup': False,
            'was_clarification_response': True,
            'entities_extracted': {k: v for k, v in entities.items() if v and k != 'raw_question'},
            'data_refreshed': False,
            'no_results': no_results
        }
        return _sanitize_for_json(response)

    except Exception as e:
        import traceback
        error_str = str(e)
        error_trace = traceback.format_exc()
        print(f"\n[ERROR] Failed to execute with forced table: {error_str}")
        print(f"  Traceback:\n{error_trace}")

        # Determine error type for better user messaging
        error_lower = error_str.lower()
        if 'timeout' in error_lower or 'timed out' in error_lower:
            user_msg = "The request took too long. Please try again."
            error_type = 'timeout_error'
        elif 'connection' in error_lower or 'network' in error_lower:
            user_msg = "Connection issue. Please check your internet and try again."
            error_type = 'connection_error'
        elif 'json' in error_lower or 'parse' in error_lower:
            user_msg = "I had trouble understanding the response. Please try rephrasing your question."
            error_type = 'parse_error'
        elif 'table' in error_lower and 'not found' in error_lower:
            user_msg = f"Could not find the selected table. Please try again."
            error_type = 'table_not_found'
        else:
            user_msg = f"Something went wrong: {error_str[:100]}"
            error_type = 'execution_error'

        return {
            'success': False,
            'error': error_str,
            'explanation': user_msg,
            'error_type': error_type
        }


def _generate_clarification_message(
    candidates: List[str],
    entities: Dict[str, Any],
    is_tamil: bool,
    profile_store: ProfileStore
) -> str:
    """
    Generate a user-friendly clarification message when multiple tables could match.

    Args:
        candidates: List of table names to choose from
        entities: Extracted entities (month, metric, etc.)
        is_tamil: Whether to respond in Tamil
        profile_store: For getting table descriptions

    Returns:
        Formatted clarification message
    """
    # Build context string from entities
    context_parts = []
    if entities.get('month'):
        context_parts.append(entities['month'])
    if entities.get('metric'):
        context_parts.append(entities['metric'])
    if entities.get('category'):
        context_parts.append(entities['category'])
    context_str = " ".join(context_parts) if context_parts else "your query"

    # Generate clean options - just table names
    options = []
    for i, table_name in enumerate(candidates[:3], 1):  # Max 3 options
        display_name = table_name.replace('_', ' ').replace('-', ' ')
        options.append(f"{i}. {display_name}")

    options_text = "\n".join(options)

    if is_tamil:
        # Tamil clarification message - crispy
        message = f"""எந்த அட்டவணை?

{options_text}

எண்ணை சொல்லுங்கள்."""
    else:
        # English clarification message - crispy
        message = f"""Which table?

{options_text}

Say the number."""

    return message


def process_query_service(question: str, conversation_id: str = None) -> Dict[str, Any]:
    """
    Process a user query with intelligent routing and healing.

    New Pipeline:
    1. Check for pending clarification (resume from saved state)
    2. Greeting/Memory detection (fast path)
    3. Translation layer (Tamil support)
    4. Context check (follow-up detection)
    5. Entity extraction
    6. Intelligent table routing (NOT top_k=50!)
       - If needs_clarification: save state, ask user
    7. Planning with focused schema
    8. Self-healing execution
    9. Personality-enhanced explanation
    """
    import time as _time
    _query_start = _time.time()
    _timings = {}

    def _log_timing(step_name: str, step_start: float):
        """Log timing for a step and update cumulative total."""
        elapsed = (_time.time() - step_start) * 1000
        cumulative = (_time.time() - _query_start) * 1000
        _timings[step_name] = elapsed
        print(f"  ⏱️  {step_name}: {elapsed:.0f}ms (total: {cumulative:.0f}ms)")

    try:
        # === FLOW LOGGING START ===
        print("\n" + "=" * 60)
        print(f"[QUERY] New query received: \"{question[:80]}{'...' if len(question) > 80 else ''}\"")
        print("=" * 60)

        # Initialize components
        _step_start = _time.time()
        print("\n[STEP 0/8] INITIALIZING...")
        app_state.initialize()
        print("  ✓ App state initialized")
        _log_timing("initialization", _step_start)

        # Get conversation context FIRST (needed for clarification check)
        ctx = app_state.conversation_manager.get_context(conversation_id)
        print(f"  ✓ Context loaded (conversation: {conversation_id or 'default'})")

        # === VALIDATE INPUT ===
        # Reject empty, too short, or obvious noise (transcription artifacts)
        # BUT: Allow short inputs (like "1", "2", "3") if there's a pending clarification
        question_clean = question.strip()
        has_pending = ctx.has_pending_clarification()

        if not question_clean:
            print("  ✗ Empty input detected")
            print("=" * 60 + "\n")
            return {
                'success': False,
                'error': 'Empty or invalid input',
                'explanation': "I didn't catch that. Could you please ask again?",
                'error_type': 'invalid_input'
            }

        # Allow short inputs (1-2 chars) ONLY when clarification is pending OR it's a greeting
        # Short greetings like "Hi", "Hey", "Yo" should be allowed through
        short_greetings = ['hi', 'hey', 'yo', 'ok', 'no', 'yes', 'ya', 'na']
        is_short_greeting = question_clean.lower() in short_greetings

        if len(question_clean) < 3 and not has_pending and not is_short_greeting:
            print("  ✗ Input too short (no pending clarification)")
            print("=" * 60 + "\n")
            return {
                'success': False,
                'error': 'Empty or invalid input',
                'explanation': "I didn't catch that. Could you please ask again?",
                'error_type': 'invalid_input'
            }

        # Detect transcription noise patterns
        noise_patterns = ['[mouse clicking]', '[inaudible]', '[silence]', '[background noise]',
                         '[music]', '[noise]', '[click]', '[static]']
        if any(noise in question_clean.lower() for noise in noise_patterns):
            print(f"  ✗ Transcription noise detected: {question_clean[:50]}")
            print("=" * 60 + "\n")
            return {
                'success': False,
                'error': 'Transcription noise detected',
                'explanation': "I couldn't understand the audio. Please try speaking clearly.",
                'error_type': 'transcription_noise'
            }

        # === TABLE CLARIFICATION FEATURE REMOVED ===
        # Clear any stale pending clarification from before this change
        if ctx.has_pending_clarification():
            ctx.clear_pending_clarification()
            print("  ✓ Cleared stale pending clarification (feature disabled)")

        # NOTE: Removed hardcoded "Freshggies" STT correction
        # The system should work with any business name via ProfileStore dynamic learning

        # === CHECK FOR PENDING CORRECTION CLARIFICATION ===
        if ctx.has_pending_correction_state():
            print("\n[STEP 0.6a/9] CHECKING PENDING CORRECTION...")
            pending_correction = ctx.get_pending_correction_state()
            # User was asked what to correct - process their response
            correction_response = _handle_pending_correction_response(
                user_response=question,
                pending_correction=pending_correction,
                ctx=ctx,
                app_state=app_state,
                is_tamil=bool(re.search(r'[\u0B80-\u0BFF]', question))
            )
            if correction_response:
                ctx.clear_pending_correction_state()
                return correction_response
            else:
                # Couldn't match response, clear and continue as normal query
                ctx.clear_pending_correction_state()
                print("  ✗ Could not match correction response, treating as new query")

        # === CHECK FOR CORRECTION INTENT ===
        # Only check if there's previous context to correct
        if ctx.turns:
            _step_start = _time.time()
            print("\n[STEP 0.6b/9] CORRECTION INTENT DETECTION...")
            previous_turn = ctx.get_last_turn()
            correction_intent = app_state.correction_detector.detect(question, previous_turn)

            if correction_intent:
                print(f"  ✓ Correction detected: {correction_intent.correction_type.value}")
                print(f"    Confidence: {correction_intent.confidence:.0%}")
                _log_timing("correction_detection", _step_start)

                # Detect Tamil
                is_tamil = bool(re.search(r'[\u0B80-\u0BFF]', question))

                # Handle the correction
                correction_result = _handle_correction(
                    correction_intent=correction_intent,
                    previous_turn=previous_turn,
                    question=question,
                    ctx=ctx,
                    app_state=app_state,
                    is_tamil=is_tamil
                )
                if correction_result:
                    return correction_result
            else:
                print("  ✗ No correction intent detected")
            _log_timing("correction_detection", _step_start)

        # === RESOLVE TOP REFERENCES (NEW STEP 0.65) ===
        # Replace "top category", "best seller", etc. with actual values from previous results
        if ctx.turns:
            previous_turn = ctx.get_last_turn()
            resolved_question = _resolve_top_references(question, previous_turn)
            if resolved_question != question:
                print(f"\n[STEP 0.65/9] TOP REFERENCE RESOLUTION...")
                print(f"  ✓ Resolved: '{question[:50]}...' → '{resolved_question[:50]}...'")
                question = resolved_question  # Use resolved question for rest of pipeline

        # === CHECK FOR PROJECTION INTENT (NEW STEP 0.7) ===
        if ctx.turns:
            _step_start = _time.time()
            print("\n[STEP 0.7/9] PROJECTION INTENT DETECTION...")
            previous_turn = ctx.get_last_turn()

            from utils.projection_detector import detect_projection_intent
            projection_intent = detect_projection_intent(question, previous_turn)

            if projection_intent:
                print(f"  ✓ Projection intent detected: {projection_intent.projection_type.value}")
                print(f"    Target period: {projection_intent.target_period}")
                print(f"    Confidence: {projection_intent.confidence:.0%}")
                _log_timing("projection_detection", _step_start)

                # Detect Tamil
                is_tamil = bool(re.search(r'[\u0B80-\u0BFF]', question))

                # Handle the projection
                projection_result = _handle_projection(
                    projection_intent=projection_intent,
                    previous_turn=previous_turn,
                    question=question,
                    ctx=ctx,
                    app_state=app_state,
                    is_tamil=is_tamil
                )
                if projection_result:
                    _total_time = (_time.time() - _query_start) * 1000
                    print(f"\n  ⏱️  TIMING SUMMARY (PROJECTION):")
                    for step, ms in _timings.items():
                        print(f"      {step}: {ms:.0f}ms")
                    print(f"      TOTAL: {_total_time:.0f}ms ({_total_time/1000:.2f}s)")
                    print("=" * 60 + "\n")
                    return projection_result
            else:
                print("  ✗ No projection intent detected")
            _log_timing("projection_detection", _step_start)

        # === FAST PATH: Greetings & Conversational ===
        # ALL conversational responses now use LLM for natural, contextual replies
        _step_start = _time.time()
        print("\n[STEP 1/8] GREETING/CONVERSATIONAL DETECTION...")
        is_tamil_text = bool(re.search(r'[\u0B80-\u0BFF]', question))

        if is_greeting(question) or is_non_query_conversational(question):
            greeting_type = "greeting" if is_greeting(question) else "conversational"
            print(f"  ✓ {greeting_type.title()} detected - generating LLM response")

            # Use LLM for ALL conversational responses (natural, not hardcoded)
            response = generate_off_topic_response(question, is_tamil=is_tamil_text)

            _log_timing("conversational_detection", _step_start)
            _total_time = (_time.time() - _query_start) * 1000
            print("  → Returning LLM-generated conversational response")
            print(f"\n  ⏱️  TIMING SUMMARY (CONVERSATIONAL PATH):")
            for step, ms in _timings.items():
                print(f"      {step}: {ms:.0f}ms")
            print(f"      TOTAL: {_total_time:.0f}ms ({_total_time/1000:.2f}s)")
            print("=" * 60 + "\n")
            return {
                'success': True,
                'explanation': response,
                'data': None,
                'plan': None,
                'schema_context': [],
                'data_refreshed': False,
                'is_greeting': True,
                'is_conversational': True
            }
        print("  ✗ Not conversational (likely a data query)")
        _log_timing("conversational_detection", _step_start)

        # === FAST PATH: Date Context Detection (BEFORE Memory) ===
        _step_start = _time.time()
        print("\n[STEP 1.8/8] DATE CONTEXT DETECTION...")
        is_date_ctx, date_info = is_date_context_statement(question)
        if is_date_ctx:
            print(f"  ✓ Date context detected: {date_info}")
            # Store date context in conversation for subsequent queries
            if date_info:
                ctx.set_date_context(date_info)
            is_tamil = bool(re.search(r'[\u0B80-\u0BFF]', question))
            response = get_date_context_response(date_info, is_tamil=is_tamil)
            _log_timing("date_context", _step_start)
            print("  → Returning date context acknowledgment")
            print("=" * 60 + "\n")
            return {
                'success': True,
                'explanation': response,
                'data': None,
                'plan': None,
                'schema_context': [],
                'data_refreshed': False,
                'is_date_context': True,
                'date_info': date_info
            }
        print("  ✗ Not a date context statement")
        _log_timing("date_context", _step_start)

        # === FAST PATH: Memory Intent ===
        _step_start = _time.time()
        print("\n[STEP 2/8] MEMORY INTENT DETECTION...")
        memory_result = detect_memory_intent(question)
        if memory_result and memory_result.get("has_memory_intent"):
            print(f"  ✓ Memory intent detected!")
            category = memory_result["category"]
            key = memory_result["key"]
            value = memory_result["value"]
            print(f"    Category: {category}, Key: {key}, Value: {value}")

            # Update personality if storing name
            if key == "address_as":
                app_state.personality.set_name(value)
                ctx.set_user_name(value)
                print(f"  ✓ User name set to: {value}")

            success = update_memory(category, key, value)

            if success:
                print("  ✓ Memory saved successfully")

                # CRITICAL: Invalidate cached LLM models so they pick up the new memory
                # The planner and explainer cache system prompts with user name
                from planning_layer.planner_client import invalidate_planner_model
                from explanation_layer.explainer_client import invalidate_explainer_model
                invalidate_planner_model()
                invalidate_explainer_model()
                print("  ✓ LLM model caches invalidated (will reload with new name)")
                print("  → Returning memory confirmation")
                print("=" * 60 + "\n")

                # Generate personalized response with data availability
                if key == "address_as":
                    # Get data availability info
                    if app_state.profile_store:
                        profiles = app_state.profile_store.get_all_profiles()
                        table_count = len(profiles)
                        # Extract months from profiles
                        months = set()
                        for name, profile in profiles.items():
                            month = profile.get('date_range', {}).get('month')
                            if month:
                                months.add(month)
                            # Also check table name for month keywords
                            name_lower = name.lower()
                            for m in ['august', 'september', 'october', 'november', 'december',
                                      'january', 'february', 'march', 'april', 'may', 'june', 'july']:
                                if m in name_lower:
                                    months.add(m.capitalize())

                        if table_count > 0 and months:
                            month_str = ", ".join(sorted(months))
                            explanation = f"Great to meet you, {value}! I have access to {table_count} data tables covering {month_str}. What would you like to know?"
                        elif table_count > 0:
                            explanation = f"Great to meet you, {value}! I have access to {table_count} data tables. What would you like to know?"
                        else:
                            explanation = f"Great to meet you, {value}! Please connect a dataset so I can help you explore your data."
                    else:
                        explanation = f"Great to meet you, {value}! Please connect a dataset so I can help you explore your data."
                else:
                    explanation = "Got it! I'll remember that."

                return {
                    'success': True,
                    'explanation': explanation,
                    'data': None,
                    'plan': None,
                    'schema_context': [],
                    'data_refreshed': False,
                    'is_memory_storage': True
                }
        else:
            print("  ✗ No memory intent")
        _log_timing("memory_detection", _step_start)

        # === FAST PATH: Schema Inquiry ===
        _step_start = _time.time()
        # Handles questions like "what is sheet 1", "describe the data", "what tables do I have"
        # Uses template-based responses - NO LLM (prevents hallucination)
        print("\n[STEP 3/8] SCHEMA INQUIRY DETECTION...")
        schema_intent = detect_schema_inquiry(question)
        if schema_intent:
            print(f"  ✓ Schema inquiry detected: {schema_intent}")
            table_ref = schema_intent.get('table')
            is_detailed = schema_intent.get('detailed', False)

            # Get user language preference
            is_tamil = bool(re.search(r'[\u0B80-\u0BFF]', question))
            language = 'ta' if is_tamil else 'en'

            # Generate response from profile store (template-based, no LLM)
            if app_state.profile_store:
                if is_detailed and table_ref:
                    # User wants detailed info (e.g., "show all columns", "describe in detail")
                    response = app_state.profile_store.format_detailed_profile(
                        table_name=table_ref,
                        language=language
                    )
                else:
                    # Brief summary with offer to show more
                    response = app_state.profile_store.format_profile_for_user(
                        table_name=table_ref,
                        language=language
                    )
            else:
                response = "No data loaded yet. Please connect a dataset first."

            # Personalize if we have user name
            user_name = get_user_name()
            if user_name and user_name.lower() not in ["there", "user", "friend", ""]:
                if language == 'ta':
                    response = f"{user_name}, {response}"
                else:
                    response = f"{user_name}, here's what I found:\n\n{response}"

            print("  → Returning schema info response")
            _log_timing("schema_inquiry", _step_start)
            print("=" * 60 + "\n")
            return {
                'success': True,
                'explanation': response,
                'data': None,
                'plan': None,
                'schema_context': [],
                'data_refreshed': False,
                'is_schema_inquiry': True
            }
        else:
            print("  ✗ Not a schema inquiry")
        _log_timing("schema_inquiry", _step_start)

        # === TRANSLATION LAYER (PRE-PROCESS) ===
        _step_start = _time.time()
        print("\n[STEP 4/8] TRANSLATION LAYER...")
        processing_query = question
        is_tamil = bool(re.search(r'[\u0B80-\u0BFF]', question))

        if is_tamil:
            print(f"  ✓ Tamil detected in input")
            print(f"    Original: {question[:50]}...")
            processing_query = translate_to_english(question)
            print(f"    Translated: {processing_query[:50]}...")
            ctx.set_language('ta')
        else:
            print("  ✗ No translation needed (English)")
        _log_timing("translation", _step_start)

        # === CONTEXT DETECTION ===
        _step_start = _time.time()
        print("\n[STEP 5/8] CONTEXT & ENTITY EXTRACTION...")
        is_followup = ctx.is_followup(processing_query)
        if is_followup:
            print(f"  ✓ Follow-up question detected")
        else:
            print("  ✗ Not a follow-up (new query)")

        # === ENTITY EXTRACTION ===
        entities = app_state.entity_extractor.extract(processing_query)
        entity_summary = app_state.entity_extractor.get_entities_summary(entities)
        print(f"  ✓ Entities extracted: {entity_summary}")

        # Merge with previous context if follow-up
        if is_followup:
            entities = ctx.merge_entities(entities)
            print(f"  ✓ Merged with context (follow-up): {app_state.entity_extractor.get_entities_summary(entities)}")
        _log_timing("entity_extraction", _step_start)

        # === CHECK FOR DATA CHANGES (INVALIDATE STALE CACHE) ===
        _step_start = _time.time()
        print("\n[STEP 6/8] CACHE & DATA CHECK...")
        # If data was refreshed mid-session, invalidate cache to avoid stale answers
        # Fallback to config if app_state doesn't have it (e.g., after server restart)
        spreadsheet_id = app_state.current_spreadsheet_id
        if not spreadsheet_id:
            try:
                config = get_config()
                spreadsheet_id = config.google_sheets.spreadsheet_id  # Typed config access
                if spreadsheet_id:
                    app_state.current_spreadsheet_id = spreadsheet_id  # Cache it for future use
            except (AttributeError, KeyError, FileNotFoundError):
                spreadsheet_id = ""
        data_was_refreshed = check_and_refresh_data()
        if data_was_refreshed:
            print(f"  ! Data was refreshed - invalidating stale cache")
            invalidate_spreadsheet_cache(spreadsheet_id)

        # === CHECK CACHE (CACHING FLOW FROM ARCHITECTURE) ===
        # Generate cache key: Hash(ORIGINAL question + spreadsheet_id)
        # Use original question (before translation) to avoid cache collisions
        # when different Tamil queries translate to similar English
        cache_hit, cached_result = get_cached_query_result(question, spreadsheet_id)

        if cache_hit and cached_result and isinstance(cached_result, dict):
            print(f"  ✓ CACHE HIT - returning cached result")
            print("=" * 60 + "\n")
            # Return cached response (still personalize it)
            cached_explanation = cached_result.get('explanation', '')
            if is_tamil:
                cached_explanation = translate_to_tamil(cached_explanation)

            return {
                'success': True,
                'explanation': cached_explanation,
                'data': cached_result.get('data'),
                'plan': cached_result.get('plan'),
                'table_used': cached_result.get('table_used'),
                'routing_confidence': cached_result.get('routing_confidence'),
                'was_followup': is_followup,
                'entities_extracted': cached_result.get('entities_extracted', {}),
                'data_refreshed': data_was_refreshed,  # Inform if data changed since last cache
                'from_cache': True,
                'no_results': cached_result.get('no_results', False)
            }
        else:
            print("  ✗ Cache miss - proceeding with full query")
        _log_timing("cache_check", _step_start)

        # === CHECK DATA LOADED ===
        profiles = app_state.profile_store.get_all_profiles() if app_state.profile_store else {}
        print(f"  ✓ {len(profiles)} table profiles loaded")
        if not profiles:
            return {
                'success': False,
                'error': 'No data loaded',
                'explanation': app_state.personality.handle_error('no_data',
                    "I don't have any data loaded yet. Please connect a Google Sheet first."),
                'error_type': 'no_data'
            }

        # === INTELLIGENT TABLE ROUTING ===
        _step_start = _time.time()
        print("\n[STEP 7/8] TABLE ROUTING & PLANNING...")
        # This is the CORE FIX - no more top_k=50 schema dump!
        previous_context = {
            'entities': ctx.active_entities,
            'table': ctx.active_table
        } if is_followup else None

        routing_result = app_state.table_router.route(processing_query, previous_context)

        # Unpack routing result
        best_table = routing_result.table
        routing_entities = routing_result.entities
        confidence = routing_result.confidence

        print(f"  ✓ Router result: {best_table} (confidence: {confidence:.0%})")
        _log_timing("table_routing", _step_start)

        # === CRITICAL: CHECK FOR LOW-CONFIDENCE NON-DATA QUERIES ===
        # If confidence is very low AND query doesn't have clear data intent,
        # use LLM for conversational response instead of asking for table selection
        if confidence < 0.25 and routing_result.needs_clarification:
            # Check if query has any data keywords
            data_keywords = [
                'sales', 'revenue', 'profit', 'total', 'sum', 'average', 'count',
                'show', 'list', 'get', 'find', 'compare', 'trend', 'top', 'bottom',
                'maximum', 'minimum', 'highest', 'lowest', 'branch', 'category',
                'month', 'year', 'date', 'order', 'transaction', 'payment',
                # Tamil keywords
                'விற்பனை', 'மொத்தம்', 'எவ்வளவு', 'எத்தனை', 'காட்டு', 'சேல்ஸ்'
            ]
            query_lower = processing_query.lower()
            has_data_intent = any(kw in query_lower for kw in data_keywords)

            if not has_data_intent:
                # No data intent + very low confidence = unclear/conversational message
                # Route to LLM for a friendly response instead of table selection
                print(f"  ! Very low confidence ({confidence:.0%}) with no data intent - using LLM response")
                is_tamil_text = bool(re.search(r'[\u0B80-\u0BFF]', question))
                response = generate_off_topic_response(question, is_tamil=is_tamil_text)

                _total_time = (_time.time() - _query_start) * 1000
                print("  → Returning conversational LLM response (low confidence path)")
                print(f"\n  ⏱️  TIMING SUMMARY (LOW CONFIDENCE CONVERSATIONAL):")
                for step, ms in _timings.items():
                    print(f"      {step}: {ms:.0f}ms")
                print(f"      TOTAL: {_total_time:.0f}ms ({_total_time/1000:.2f}s)")
                print("=" * 60 + "\n")

                return {
                    'success': True,
                    'explanation': response,
                    'data': None,
                    'plan': None,
                    'schema_context': [],
                    'data_refreshed': False,
                    'is_conversational': True
                }

        # === TABLE CLARIFICATION DISABLED ===
        # Instead of asking "Which table?", just pick the best candidate automatically.
        # User can correct via "check from X table" if wrong.
        if routing_result.needs_clarification:
            print(f"  ! AMBIGUITY DETECTED - auto-selecting best candidate (clarification disabled)")
            candidates = routing_result.get_clarification_options()
            if candidates:
                best_table = candidates[0]  # Pick first (best scored) candidate
                print(f"  → Auto-selected table: {best_table}")

        # === SCHEMA CONTEXT GENERATION ===
        if best_table and routing_result.is_confident:
            # High confidence - use single table schema
            schema_context = app_state.table_router.get_table_schema(best_table)
            print(f"  ✓ Using focused schema for: {best_table}")
        elif routing_result.should_fallback:
            # Very low confidence - use top 5 candidate tables
            schema_context = app_state.table_router.get_fallback_schema(processing_query, top_k=5)
            print(f"  ! Very low confidence - using fallback schema (top 5 candidates)")
        else:
            # Medium confidence - use the best match
            schema_context = app_state.table_router.get_table_schema(best_table)
            print(f"  ✓ Using best match schema for: {best_table} (medium confidence)")

        # Add previous context to schema if follow-up
        if is_followup:
            context_prompt = ctx.get_context_prompt()
            if context_prompt:
                schema_context = f"{context_prompt}\n\n---\n\n{schema_context}"

        # === PLANNING ===
        _step_start = _time.time()
        print("  → Generating query plan via LLM...")
        plan = generate_plan(processing_query, schema_context, entities=entities)
        validate_plan(plan)
        _log_timing("llm_planning", _step_start)
        print(f"  ✓ Plan generated:")
        print(f"    Query type: {plan.get('query_type', 'unknown')}")
        print(f"    Table: {plan.get('table', 'unknown')}")
        print(f"    Metrics: {plan.get('metrics', [])}")
        print(f"    Filters: {plan.get('filters', [])}")

        # === EXECUTION WITH HEALING ===
        _step_start = _time.time()
        print("\n[STEP 8/8] QUERY EXECUTION...")
        try:
            # Import at function level to avoid circular imports
            from execution_layer.executor import ADVANCED_QUERY_TYPES
            
            query_type = plan.get('query_type')
            
            # Route advanced query types to specialized executor (comparison, percentage, trend)
            if query_type in ADVANCED_QUERY_TYPES:
                print(f"  → Executing advanced query type: {query_type}")
                from execution_layer.executor import execute_plan
                result = execute_plan(plan)
                final_sql = f"[Advanced {query_type} query - see analysis]"
                print(f"  ✓ Advanced query completed")

                # CRITICAL: For projection support, merge analysis from result back into plan
                # Advanced queries return DataFrames with analysis in attrs
                # We need 'analysis' in plan for projection follow-ups
                if hasattr(result, 'attrs') and 'analysis' in result.attrs:
                    analysis = result.attrs['analysis']
                    plan['analysis'] = analysis if isinstance(analysis, dict) else {}
                    if plan['analysis']:
                        print(f"    → Stored analysis in plan for projection: {list(plan['analysis'].keys())}")
                    else:
                        print(f"    ! Analysis was empty or invalid")
                elif isinstance(result, dict) and 'analysis' in result:
                    plan['analysis'] = result.get('analysis', {})
                    print(f"    → Stored analysis in plan for projection support: {list(plan['analysis'].keys())}")
                else:
                    print(f"    ! No analysis found in result (type: {type(result).__name__})")
            else:
                # Standard query execution with healing
                sql = compile_sql(plan)
                print(f"  ✓ SQL compiled: {sql[:100]}{'...' if len(sql) > 100 else ''}")
                print("  → Executing with self-healing...")
                result, final_sql = app_state.query_healer.execute_with_healing(sql, plan)

            # Add healing info to debug
            healing_history = app_state.query_healer.get_healing_history()
            if healing_history:
                print(f"  ! Applied {len(healing_history)} healing fix(es)")

        except QueryExecutionError as e:
            # All healing attempts failed
            print(f"  ✗ EXECUTION FAILED after all healing attempts")
            print(f"    Error: {str(e)[:100]}")
            print("=" * 60 + "\n")
            error_msg = app_state.personality.handle_error('general', str(e))
            return {
                'success': False,
                'error': str(e),
                'explanation': error_msg,
                'healing_attempts': [
                    {
                        'attempt': a.attempt_number,
                        'fix_type': a.fix_type,
                        'error': a.error[:100]
                    } for a in e.attempts
                ]
            }

        # === DETECT EMPTY RESULTS ===
        no_results = False
        row_count = len(result) if result is not None and hasattr(result, '__len__') else 0
        if result is None or row_count == 0:
            no_results = True
            print(f"  ! Query returned 0 rows")
        else:
            print(f"  ✓ Query returned {row_count} rows")
        _log_timing("sql_execution", _step_start)

        # === EXPLANATION WITH PERSONALITY ===
        _step_start = _time.time()
        print("\n[RESPONSE] Generating explanation...")
        explanation = explain_results(
            result,
            query_plan=plan,
            original_question=processing_query,
            raw_user_message=question  # Original message with emotional tone
        )

        # NOTE: explain_results() already handles empty results with friendly messages
        # No need to append additional no_data_hint - that caused DOUBLE responses

        # Determine sentiment based on result
        sentiment = 'neutral'
        if result is not None and len(result) > 0:
            # Could add more sophisticated sentiment detection here
            sentiment = 'positive' if len(result) > 0 else 'neutral'
        elif no_results:
            sentiment = 'neutral'  # Empty results - inform but don't alarm

        # NOTE: Personality prefix REMOVED - LLM already generates crisp responses
        # The explain_results() function handles response formatting
        # Adding personality.format_response() caused double greetings like "Looking good, Viswa!"
        _log_timing("llm_explanation", _step_start)

        # === TRANSLATION (POST-PROCESS) ===
        _step_start = _time.time()
        if is_tamil:
            print("  → Translating response to Tamil...")
            explanation = translate_to_tamil(explanation)
            print("  ✓ Response translated")
            _log_timing("translation_response", _step_start)
        else:
            _log_timing("translation_response", _step_start)

        # === UPDATE CONTEXT ===
        # Extract key result values for pronoun resolution in follow-ups
        # e.g., "that state" → "West Bengal" from previous query result
        result_values = _extract_result_values(result, plan)
        if result_values:
            print(f"  ✓ Extracted result values for context: {result_values}")

        # Make a deep copy of plan to preserve analysis for projection follow-ups
        # (reference passing could cause issues if plan is modified elsewhere)
        import copy
        stored_plan = copy.deepcopy(plan)

        # Debug: Verify analysis is in stored_plan
        if stored_plan.get('analysis'):
            print(f"  ✓ Plan analysis preserved for projection: {list(stored_plan['analysis'].keys())}")

        turn = QueryTurn(
            question=question,
            resolved_question=processing_query,
            entities=entities,
            table_used=plan.get('table', best_table or ''),
            filters_applied=plan.get('filters', []) + plan.get('subset_filters', []),
            result_summary=f"{len(result)} rows returned" if result is not None else "No data",
            sql_executed=final_sql if 'final_sql' in dir() else None,
            was_followup=is_followup,
            confidence=confidence,
            result_values=result_values,  # For "that state", "that branch" resolution
            # Store routing info for correction handlers
            query_plan=stored_plan,  # Use deep copy to preserve analysis
            routing_alternatives=routing_result.alternatives if 'routing_result' in dir() and routing_result else []
        )
        ctx.add_turn(turn)

        # === BUILD RESPONSE ===
        _total_time = (_time.time() - _query_start) * 1000
        print("\n[SUCCESS] Query completed successfully!")
        print(f"  Table: {plan.get('table', best_table)}")
        print(f"  Rows: {row_count}")
        print(f"  Confidence: {confidence:.0%}")
        print(f"\n  ⏱️  TIMING SUMMARY:")
        for step, ms in _timings.items():
            print(f"      {step}: {ms:.0f}ms")
        print(f"      ────────────────────")
        print(f"      TOTAL: {_total_time:.0f}ms ({_total_time/1000:.2f}s)")
        print("=" * 60 + "\n")

        # Sanitize numpy types for JSON serialization
        data_list = None
        if result is not None and hasattr(result, 'to_dict'):
            data_list = _sanitize_for_json(result.to_dict('records'))

        response = {
            'success': True,
            'explanation': explanation,
            'data': data_list,
            'plan': plan,
            'table_used': plan.get('table', best_table),
            'routing_confidence': confidence,
            'was_followup': is_followup,
            'entities_extracted': {k: v for k, v in entities.items()
                                  if v and k not in ['raw_question']},
            'data_refreshed': data_was_refreshed,  # True if data was refreshed before this query
            'no_results': no_results  # Flag for empty result set
        }

        # Sanitize entire response to handle numpy types in plan, entities, etc.
        response = _sanitize_for_json(response)

        # === CACHE RESULT (CACHING FLOW FROM ARCHITECTURE) ===
        # Store for 5 minutes (configurable via settings.yaml)
        # Use ORIGINAL question (before translation) to match GET key
        try:
            cache_query_result(
                question,  # Use original question, not processing_query
                spreadsheet_id,
                response
                # Don't include table_name/filters - they're not available at GET time
            )
            print(f"[Cache] Stored result for: {question[:50]}...")
        except Exception as cache_err:
            print(f"[Cache] Warning: Could not cache result: {cache_err}")

        return response

    except ValueError as e:
        # Planning/validation errors (LLM response issues)
        error_str = str(e).lower()
        print(f"\n[ERROR] ValueError in query processing:")
        print(f"  {e}")
        print("=" * 60 + "\n")

        if 'timeout' in error_str or 'timed out' in error_str:
            error_msg = app_state.personality.handle_error('general',
                "Request took too long. Please try again or simplify your question.")
        elif 'json' in error_str or 'parse' in error_str:
            error_msg = app_state.personality.handle_error('general',
                "I had trouble understanding how to answer that. Could you rephrase?")
        elif 'table' in error_str:
            error_msg = app_state.personality.handle_error('table_not_found')
        elif 'column' in error_str or 'metric' in error_str:
            error_msg = app_state.personality.handle_error('column_not_found')
        else:
            error_msg = app_state.personality.handle_error('general',
                "I couldn't process that query. Please try rephrasing.")

        return {
            'success': False,
            'error': str(e),
            'explanation': error_msg,
            'error_type': 'validation_error'
        }

    except ConnectionError as e:
        # Network/API connection errors
        print(f"\n[ERROR] ConnectionError:")
        print(f"  {e}")
        print("=" * 60 + "\n")
        error_msg = app_state.personality.handle_error('connection')
        return {
            'success': False,
            'error': str(e),
            'explanation': error_msg,
            'error_type': 'connection_error'
        }

    except TimeoutError as e:
        # Explicit timeout errors
        print(f"\n[ERROR] TimeoutError:")
        print(f"  {e}")
        print("=" * 60 + "\n")
        error_msg = app_state.personality.handle_error('general',
            "The request took too long. Please try a simpler question or try again later.")
        return {
            'success': False,
            'error': str(e),
            'explanation': error_msg,
            'error_type': 'timeout_error'
        }

    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"\n[ERROR] Unexpected exception:")
        print(f"  Type: {type(e).__name__}")
        print(f"  Message: {str(e)}")
        print(f"  Traceback:\n{error_trace}")
        print("=" * 60 + "\n")

        # Check if it's a known error pattern
        error_str = str(e).lower()
        if 'no data' in error_str or 'empty' in error_str:
            error_msg = app_state.personality.handle_error('no_data')
        elif 'ambiguous' in error_str:
            error_msg = app_state.personality.handle_error('ambiguous')
        elif 'table' in error_str and ('not found' in error_str or 'does not exist' in error_str):
            error_msg = app_state.personality.handle_error('table_not_found')
        elif 'connection' in error_str or 'timeout' in error_str:
            error_msg = app_state.personality.handle_error('connection')
        elif 'json' in error_str or 'parse' in error_str or 'decode' in error_str:
            error_msg = app_state.personality.handle_error('general',
                "I had trouble understanding how to answer that. Please try rephrasing your question.")
        elif 'column' in error_str or 'metric' in error_str:
            error_msg = app_state.personality.handle_error('column_not_found')
        else:
            # Truly generic error - provide more specific message
            short_error = str(e)[:150] if len(str(e)) > 150 else str(e)
            error_msg = app_state.personality.handle_error('general',
                f"Something went wrong: {short_error}. Try rephrasing your question.")

        return {
            'success': False,
            'error': str(e),
            'explanation': error_msg,
            'error_type': 'unknown_error'
        }


def transcribe_audio_service(audio_file_path: str) -> Dict[str, Any]:
    """
    Transcribe audio file to text.
    """
    try:
        transcribed_text = transcribe_audio(audio_file_path)
        return {
            'success': True,
            'text': transcribed_text
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


def start_onboarding_service() -> Dict[str, Any]:
    """
    Start or continue onboarding flow.
    """
    app_state.initialize()
    return app_state.onboarding.start_onboarding()


def process_onboarding_input_service(user_input: str) -> Dict[str, Any]:
    """
    Process input during onboarding.
    """
    app_state.initialize()
    return app_state.onboarding.process_input(user_input)


def get_routing_debug_service(question: str) -> Dict[str, Any]:
    """
    Debug endpoint to see how a question would be routed.
    Useful for troubleshooting.
    """
    app_state.initialize()

    explanation = app_state.table_router.explain_routing(question)
    debug = app_state.table_router.get_routing_debug()

    return {
        'explanation': explanation,
        'debug': debug
    }


def get_table_profiles_service() -> Dict[str, Any]:
    """
    Get all table profiles for debugging/inspection.
    """
    app_state.initialize()

    profiles = app_state.profile_store.get_all_profiles()

    return {
        'success': True,
        'profile_count': len(profiles),
        'profiles': {
            name: {
                'table_type': p.get('table_type'),
                'granularity': p.get('granularity'),
                'row_count': p.get('row_count'),
                'date_range': p.get('date_range'),
                'columns': list(p.get('columns', {}).keys())[:10],  # First 10 columns
                'data_quality_score': p.get('data_quality_score')
            }
            for name, p in profiles.items()
        }
    }


def clear_context_service(conversation_id: str = None) -> Dict[str, Any]:
    """
    Clear conversation context.
    """
    app_state.conversation_manager.clear_context(conversation_id)
    return {'success': True, 'message': 'Context cleared'}


