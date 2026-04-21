"""Dataset loading, syncing, and refresh services."""
import re
import time
import traceback
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

from utils.logger import get_logger
from api.services.app_state import app_state
from data_sources.connector_factory import ConnectorFactory
from data_sources.gsheet.connector import fetch_sheets_with_tables
from data_sources.gsheet.change_detector import needs_refresh
from data_sources.gsheet.snapshot_loader import load_snapshot
from analytics_engine.duckdb_manager import DuckDBManager, reset_shared_conn
from schema_intelligence.data_profiler import DataProfiler

# Project root for config file access
project_root = Path(__file__).parent.parent.parent  # api/services/ -> api/ -> backend/

logger = get_logger("dataset")

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
        logger.info("Starting load for URL: %s (append=%s)", url, append)

        spreadsheet_id = extract_spreadsheet_id(url)
        if not spreadsheet_id:
            return {
                'success': False,
                'error': 'Invalid Google Sheets URL or ID'
            }

        # Check if this spreadsheet is already loaded (when appending)
        if append and spreadsheet_id in app_state.loaded_spreadsheet_ids:
            logger.info("Spreadsheet %s already loaded, skipping", spreadsheet_id)
            return {
                'success': True,
                'message': 'Spreadsheet already loaded',
                'stats': None
            }

        # Set current user for OAuth credentials
        if user_id:
            from data_sources.gsheet.connector import set_current_user
            set_current_user(user_id)
            logger.info("Using credentials for user: %s", user_id)

        logger.info("Extracted spreadsheet ID: %s", spreadsheet_id)

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
        logger.info("Fetching sheets with tables from %s...", spreadsheet_id[:20])
        sheets_with_tables = fetch_sheets_with_tables(spreadsheet_id)
        logger.info("Fetched %d sheets", len(sheets_with_tables))

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
        logger.info("Populated sheet cache for 300s TTL")

        if append and app_state.data_loaded:
            # APPEND MODE: Don't clear existing data
            logger.info("APPEND MODE: Adding to existing data...")
            # Load snapshot in append mode (full_reset=False)
            load_snapshot(prefixed_sheets_with_tables, full_reset=False, changed_sheets=list(prefixed_sheets_with_tables.keys()))
            reset_shared_conn()  # Refresh shared DuckDB conn after write
            logger.info("Appended %d sheets to existing snapshot", len(prefixed_sheets_with_tables))
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
                app_state.is_default_source = False  # Phase 1: User replaced default
                logger.info("REPLACE MODE: Clearing existing data...")

            # Clear and rebuild vector store
            logger.info("Clearing vector store...")
            store.clear_collection()
            logger.info("Loading snapshot...")
            load_snapshot(prefixed_sheets_with_tables, full_reset=True)
            reset_shared_conn()  # Refresh shared DuckDB conn after write
            logger.info("Rebuilding vector store...")
            store.rebuild()

        # === Profile tables for intelligent routing ===
        logger.info("Profiling tables for intelligent routing...")
        profiler = DataProfiler()
        db = DuckDBManager()
        tables = db.list_tables()

        if not append:
            # Clear old profiles only in replace mode
            app_state.profile_store.clear_profiles()
            logger.info("Cleared old profiles")

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
        logger.info("Starting parallel profiling with 5 workers...")
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {executor.submit(profile_single_table, t): t for t in tables}
            for future in as_completed(futures):
                table_name, profile, error = future.result()
                if profile:
                    app_state.profile_store.set_profile(table_name, profile)
                    profile_count += 1
                    logger.info("Profile %s: %s, %d rows", table_name, profile.get('table_type', 'unknown'), profile.get('row_count', 0))
                else:
                    profile_errors.append(f"{table_name}: {error}")
                    logger.warning("Could not profile %s: %s", table_name, error)

        # Save profiles to disk
        app_state.profile_store.save_profiles()
        if hasattr(app_state, 'table_router') and app_state.table_router:
            app_state.table_router.invalidate_table_context_cache()
        logger.info("Profiled %d tables", profile_count)

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
        logger.info("Sync time recorded: %s", app_state.last_sync_time)

        # Get data summary from onboarding
        profiles = app_state.profile_store.get_all_profiles()
        data_summary = app_state.onboarding.get_data_summary(profiles)

        logger.info("Successfully loaded: %d tables, %d records", total_tables, total_records)
        logger.info("Total loaded spreadsheets: %d", len(app_state.loaded_spreadsheet_ids))

        return {
            'success': True,
            'stats': {
                'totalTables': total_tables,
                'totalRecords': total_records,
                'sheetCount': len(prefixed_sheets_with_tables),
                'sheets': [t.get('original_sheet_name', k) for k, tables_list in prefixed_sheets_with_tables.items() for t in tables_list[:1]] or list(prefixed_sheets_with_tables.keys()),
                'detectedTables': detected_tables,
                'profiledTables': profile_count,
                'loadedSpreadsheets': app_state.loaded_spreadsheet_ids,
                'profileErrors': profile_errors if profile_errors else None
            },
            'data_summary': data_summary
        }

    except Exception as e:
        logger.error("Dataset load exception: %s", e, exc_info=True)
        return {
            'success': False,
            'error': str(e)
        }


def load_dataset_from_source(url: str, user_id: str = None, append: bool = False) -> Dict[str, Any]:
    """
    NEW: Load data from any supported source (CSV, Excel, Drive, Sheets).
    Falls back to existing Google Sheets flow for spreadsheet URLs.

    This is ADDITIVE code - does not modify existing load_dataset_service.

    Args:
        url: Data source URL (Google Sheets, CSV, Excel, or Google Drive)
        user_id: Optional user ID for OAuth credentials
        append: If True, append to existing data instead of replacing
    """
    from data_sources.connector_factory import ConnectorFactory, is_google_sheets_url

    # SAFETY: Google Sheets URLs use EXISTING code path (unchanged)
    if is_google_sheets_url(url):
        logger.info("Google Sheets URL detected, using existing code path")
        return load_dataset_service(url, user_id, append)

    try:
        logger.info("Loading from new connector: %s", url)

        # Create appropriate connector for this URL
        connector = ConnectorFactory.create(url)
        source_name = connector.get_source_name()

        # Fetch tables (same format as fetch_sheets_with_tables)
        sheets_with_tables = connector.fetch_tables()

        if not sheets_with_tables:
            return {
                'success': False,
                'error': 'No data found in the source'
            }

        logger.info("Fetched %d sheets/files", len(sheets_with_tables))

        # From here, use EXISTING pipeline functions (unchanged)
        app_state.initialize()
        store = app_state.vector_store

        # Prepare sheets with table structure (matching existing format)
        prefixed_sheets_with_tables = {}
        source_prefix = source_name[:10].replace(' ', '_')

        for sheet_name, tables in sheets_with_tables.items():
            prefixed_sheet_name = f"{source_prefix}_{sheet_name}"
            table_list = []

            for idx, df in enumerate(tables):
                table_info = {
                    'table_id': f"{prefixed_sheet_name}_t{idx}",
                    'title': sheet_name,
                    'sheet_name': prefixed_sheet_name,
                    'original_sheet_name': sheet_name,
                    'source_id': source_prefix,
                    'dataframe': df,
                    'row_range': [0, len(df)],
                    'col_range': [0, len(df.columns)]
                }
                table_list.append(table_info)

            prefixed_sheets_with_tables[prefixed_sheet_name] = table_list

        # Use existing load_snapshot (unchanged)
        if append and app_state.data_loaded:
            logger.info("Source APPEND MODE: Adding to existing data...")
            load_snapshot(prefixed_sheets_with_tables, full_reset=False,
                         changed_sheets=list(prefixed_sheets_with_tables.keys()))
            reset_shared_conn()
            store.rebuild()
        else:
            if not append:
                app_state.data_loaded = False
                app_state.loaded_spreadsheet_ids = []
                app_state.detected_tables = []
                app_state.original_sheet_names = []
                app_state.total_records = 0
                app_state.is_default_source = False  # Phase 1: User replaced default
                logger.info("Source REPLACE MODE: Clearing existing data...")

            store.clear_collection()
            load_snapshot(prefixed_sheets_with_tables, full_reset=True)
            reset_shared_conn()
            store.rebuild()

        # Profile tables using existing profiler (unchanged)
        logger.info("Source profiling tables...")
        profiler = DataProfiler()
        db = DuckDBManager()
        tables = db.list_tables()

        if not append:
            app_state.profile_store.clear_profiles()

        profile_count = 0
        for table_name in tables:
            try:
                df = db.query(f'SELECT * FROM "{table_name}" LIMIT 10000')
                profile = profiler.profile_table(table_name, df)
                app_state.profile_store.set_profile(table_name, profile)
                profile_count += 1
            except Exception as e:
                logger.warning("Source: could not profile %s: %s", table_name, e)

        app_state.profile_store.save_profiles()
        if hasattr(app_state, 'table_router') and app_state.table_router:
            app_state.table_router.invalidate_table_context_cache()
        app_state.entity_extractor.refresh_from_profiles(app_state.profile_store)

        # Build response
        total_tables = sum(len(tbls) for tbls in prefixed_sheets_with_tables.values())
        total_records = 0
        detected_tables = []

        for sheet_name, tables_list in prefixed_sheets_with_tables.items():
            for table in tables_list:
                df = table.get('dataframe')
                actual_rows = len(df) if df is not None else 0
                actual_columns = [str(col) for col in df.columns] if df is not None else []

                detected_tables.append({
                    'table_id': table.get('table_id', ''),
                    'title': table.get('title', ''),
                    'sheet_name': table.get('original_sheet_name', sheet_name),
                    'source_id': table.get('source_id', ''),
                    'total_rows': actual_rows,
                    'columns': actual_columns
                })
                total_records += actual_rows

        app_state.data_loaded = True
        app_state.detected_tables = detected_tables if not append else app_state.detected_tables + detected_tables
        app_state.total_records = total_records if not append else app_state.total_records + total_records

        logger.info("Source successfully loaded: %d tables, %d records", total_tables, total_records)

        return {
            'success': True,
            'stats': {
                'totalTables': total_tables,
                'totalRecords': total_records,
                'sheetCount': len(prefixed_sheets_with_tables),
                'sheets': list(sheets_with_tables.keys()),
                'detectedTables': detected_tables,
                'profiledTables': profile_count,
                'sourceType': 'external'
            }
        }

    except Exception as e:
        logger.error("Source exception: %s", e, exc_info=True)
        return {
            'success': False,
            'error': str(e)
        }


def sync_drive_folder(folder_url: str, replace: bool = True) -> Dict[str, Any]:
    """
    Sync all CSV/Excel files from a Google Drive folder.

    Args:
        folder_url: Google Drive folder URL
        replace: If True, replace existing data. If False, append.

    Returns:
        Dict with success status and loaded file info
    """
    from data_sources.connectors.gdrive_folder_connector import GoogleDriveFolderConnector

    try:
        logger.info("FolderSync starting sync from: %s", folder_url)
        app_state.update_loading_status("connecting", "Connecting to Google Drive...", 5)

        # Validate URL
        if not GoogleDriveFolderConnector.can_handle(folder_url):
            app_state.update_loading_status("error", "Invalid Google Drive folder URL", 0, error="Invalid URL")
            return {
                'success': False,
                'error': 'Invalid Google Drive folder URL'
            }

        # Create connector and list files
        connector = GoogleDriveFolderConnector(folder_url)
        app_state.update_loading_status("fetching", "Listing files in folder...", 10)
        files = connector.list_files()

        if not files:
            app_state.update_loading_status("error", "No files found in folder", 0, error="No files found")
            return {
                'success': False,
                'error': 'No files found in folder. Make sure the folder is shared publicly.'
            }

        logger.info("FolderSync found %d files in folder", len(files))
        app_state.update_loading_status("fetching", f"Found {len(files)} files, loading data...", 20, tables_found=len(files))

        # Fetch all tables from the folder
        sheets_with_tables = connector.fetch_tables()

        if not sheets_with_tables:
            app_state.update_loading_status("error", "No data could be loaded", 0, error="No data in files")
            return {
                'success': False,
                'error': 'No data could be loaded from the files'
            }

        # Initialize app state
        app_state.initialize()
        store = app_state.vector_store

        # Prepare sheets with table structure
        prefixed_sheets_with_tables = {}
        source_prefix = "drive"

        for sheet_name, tables in sheets_with_tables.items():
            prefixed_sheet_name = f"{source_prefix}_{sheet_name}"
            table_list = []

            for idx, df in enumerate(tables):
                table_info = {
                    'table_id': f"{prefixed_sheet_name}_t{idx}".replace(' ', '_').lower(),
                    'title': sheet_name,
                    'sheet_name': prefixed_sheet_name,
                    'original_sheet_name': sheet_name,
                    'source_id': source_prefix,
                    'dataframe': df,
                    'row_range': [0, len(df)],
                    'col_range': [0, len(df.columns)]
                }
                table_list.append(table_info)

            prefixed_sheets_with_tables[prefixed_sheet_name] = table_list

        total_tables = sum(len(tbls) for tbls in prefixed_sheets_with_tables.values())
        app_state.update_loading_status("fetching", f"Loading {total_tables} tables into database...", 30, tables_found=total_tables, total_tables=total_tables)

        # Load into DuckDB
        if replace:
            app_state.data_loaded = False
            app_state.loaded_spreadsheet_ids = []
            app_state.detected_tables = []
            app_state.original_sheet_names = []
            app_state.total_records = 0
            # Phase 1: Clear default source flag when user replaces
            app_state.is_default_source = False
            logger.info("FolderSync REPLACE MODE: Clearing existing data...")
            store.clear_collection()
            load_snapshot(prefixed_sheets_with_tables, full_reset=True)
            reset_shared_conn()
        else:
            logger.info("FolderSync APPEND MODE: Adding to existing data...")
            load_snapshot(prefixed_sheets_with_tables, full_reset=False,
                         changed_sheets=list(prefixed_sheets_with_tables.keys()))
            reset_shared_conn()

        store.rebuild()

        # Profile tables with progress tracking
        logger.info("FolderSync profiling tables...")
        profiler = DataProfiler()
        db = DuckDBManager()
        tables = db.list_tables()

        if replace:
            app_state.profile_store.clear_profiles()

        profile_count = 0
        for i, table_name in enumerate(tables):
            progress = 40 + int((i / max(len(tables), 1)) * 55)
            app_state.update_loading_status(
                "profiling", f"Analyzing table {i+1} of {len(tables)}...",
                progress, tables_found=total_tables, tables_profiled=i,
                total_tables=len(tables)
            )
            try:
                df = db.query(f'SELECT * FROM "{table_name}" LIMIT 10000')
                profile = profiler.profile_table(table_name, df)
                app_state.profile_store.set_profile(table_name, profile)
                profile_count += 1
            except Exception as e:
                logger.warning("FolderSync could not profile %s: %s", table_name, e)

        app_state.profile_store.save_profiles()
        if hasattr(app_state, 'table_router') and app_state.table_router:
            app_state.table_router.invalidate_table_context_cache()
        app_state.entity_extractor.refresh_from_profiles(app_state.profile_store)

        # Build response
        total_records = 0
        detected_tables = []

        for sheet_name, tables_list in prefixed_sheets_with_tables.items():
            for table in tables_list:
                df = table.get('dataframe')
                actual_rows = len(df) if df is not None else 0
                actual_columns = [str(col) for col in df.columns] if df is not None else []

                detected_tables.append({
                    'table_id': table.get('table_id', ''),
                    'title': table.get('title', ''),
                    'sheet_name': table.get('original_sheet_name', sheet_name),
                    'source_id': table.get('source_id', ''),
                    'total_rows': actual_rows,
                    'columns': actual_columns
                })
                total_records += actual_rows

        app_state.data_loaded = True
        app_state.detected_tables = detected_tables
        app_state.total_records = total_records
        app_state.original_sheet_names = list(sheets_with_tables.keys())

        logger.info("FolderSync successfully synced: %d files, %d tables, %d records", len(files), total_tables, total_records)

        app_state.update_loading_status(
            "ready", f"Ready! {total_tables} tables, {total_records:,} records loaded.",
            100, tables_found=total_tables, tables_profiled=profile_count,
            total_tables=total_tables, complete=True
        )

        return {
            'success': True,
            'files_found': len(files),
            'files_loaded': [f.get('name') for f in files],
            'stats': {
                'totalTables': total_tables,
                'totalRecords': total_records,
                'sheetCount': len(prefixed_sheets_with_tables),
                'sheets': list(sheets_with_tables.keys()),
                'detectedTables': detected_tables,
                'profiledTables': profile_count,
                'sourceType': 'drive_folder'
            }
        }

    except Exception as e:
        logger.error("FolderSync exception: %s", e, exc_info=True)
        app_state.update_loading_status("error", str(e), 0, error=str(e))
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
            logger.info("Data already loaded in session - skipping refresh check")
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
                    logger.debug("Loaded spreadsheet_id from config: %s...", spreadsheet_id[:20])
            except Exception as e:
                logger.warning("Cache failed to load from config: %s", e)
                spreadsheet_id = ""

        # Debug: Show cache status
        logger.debug("Using spreadsheet_id: '%s...'", spreadsheet_id[:20] if spreadsheet_id else 'EMPTY')

        if not spreadsheet_id:
            logger.warning("No spreadsheet_id set, cannot use cache")
        elif cache.is_valid(spreadsheet_id):
            logger.info("Sheet cache valid, skipping download")
            return False  # No refresh needed, cache is fresh
        else:
            logger.debug("Cache miss or expired, will fetch sheets")

        # SLOW PATH: Cache expired or missing - fetch and check for changes
        sheets_with_tables = fetch_sheets_with_tables()

        # Store in cache for future queries
        if spreadsheet_id:
            cache.set_cached_data(spreadsheet_id, sheets_with_tables)
            logger.debug("Stored sheets data in cache for 300s")

        needs_refresh_flag, full_reset, changed_sheets = needs_refresh(sheets_with_tables)

        if needs_refresh_flag:
            store = app_state.initialize_vector_store()

            if full_reset:
                store.clear_collection()
                load_snapshot(sheets_with_tables, full_reset=True)
                reset_shared_conn()
                store.rebuild()
            else:
                source_ids = []
                for sheet_name in changed_sheets:
                    if sheet_name in sheets_with_tables and sheets_with_tables[sheet_name]:
                        source_id = sheets_with_tables[sheet_name][0].get('source_id')
                        if source_id:
                            source_ids.append(source_id)

                load_snapshot(sheets_with_tables, full_reset=False, changed_sheets=changed_sheets)
                reset_shared_conn()

                if source_ids:
                    store.rebuild(source_ids=source_ids)
                else:
                    store.rebuild()

            # Re-profile changed tables
            _reprofile_tables(changed_sheets, sheets_with_tables)

            return True

        return False

    except Exception as e:
        logger.error("Refresh error: %s", e, exc_info=True)
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
        logger.info("Starting parallel reprofiling of %d tables...", len(table_names_to_reprofile))
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {executor.submit(reprofile_single_table, t): t for t in table_names_to_reprofile}
            for future in as_completed(futures):
                table_name, profile, error = future.result()
                if profile:
                    app_state.profile_store.set_profile(table_name, profile)
                else:
                    logger.warning("Could not reprofile %s: %s", table_name, error)

        app_state.profile_store.save_profiles()
        if hasattr(app_state, 'table_router') and app_state.table_router:
            app_state.table_router.invalidate_table_context_cache()

        # Refresh entity extractor with learned values from profiles
        app_state.entity_extractor.refresh_from_profiles(app_state.profile_store)
    except Exception as e:
        logger.error("Reprofile error: %s", e, exc_info=True)
