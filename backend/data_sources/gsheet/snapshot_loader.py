import duckdb
import os
import json
from pathlib import Path
from typing import Dict, List, Any
from data_sources.gsheet.connector import fetch_sheets_with_tables
from utils.sql_utils import quote_identifier
from utils.logger import get_logger

logger = get_logger("gsheet.snapshot_loader")

DB_PATH = "data_sources/snapshots/latest.duckdb"
TABLE_METADATA_FILE = "data_sources/snapshots/table_metadata.json"


def sanitize_table_name(name: str, index: int = 0) -> str:
    """
    Sanitize string to be a valid, clean DuckDB table name.
    1. Replace non-word chars (space, -, etc.) with underscore
       IMPORTANT: Preserves Unicode letters (Tamil, Chinese, etc.)
    2. Remove multiple underscores
    3. Strip leading/trailing underscores
    4. Prefix with 'T_' if name starts with a digit (SQL identifiers can't start with digits)
    5. Fallback to Table_{index} if result is empty

    Args:
        name: Original table/sheet name
        index: Fallback index if name becomes empty after sanitization
    """
    import re
    # Replace non-word chars with _ (preserves Unicode letters via \w)
    # In Python 3, \w matches Unicode letters by default
    clean = re.sub(r'[^\w]', '_', str(name), flags=re.UNICODE)
    # Collapse multiple _
    clean = re.sub(r'_+', '_', clean)
    # Strip leading/trailing underscores
    result = clean.strip('_')

    # Fallback if nothing left (e.g., name was all punctuation)
    if not result:
        return f"Table_{index}" if index > 0 else "Table_1"

    # Prefix with 'T_' if name starts with a digit (SQL identifiers can't start with digits)
    if result and result[0].isdigit():
        result = f"T_{result}"

    return result


def load_table_metadata() -> Dict[str, Dict[str, Any]]:
    """
    Load table metadata from disk.
    
    Returns:
        Dict mapping table_name to metadata:
        {
            "Sales_Table1": {
                "source_id": "1mRcD...#Sales",
                "sheet_name": "Sales",
                "table_index": 1,
                "row_count": 150,
                "created_at": "2025-12-30T12:50:09+05:30"
            },
            ...
        }
    """
    if not Path(TABLE_METADATA_FILE).exists():
        return {}
    
    try:
        with open(TABLE_METADATA_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.warning("Could not load table metadata: %s", e)
        return {}


def save_table_metadata(metadata: Dict[str, Dict[str, Any]]):
    """Persist table metadata to disk"""
    try:
        Path(TABLE_METADATA_FILE).parent.mkdir(parents=True, exist_ok=True)
        with open(TABLE_METADATA_FILE, 'w') as f:
            json.dump(metadata, f, indent=2)
    except Exception as e:
        logger.warning("Could not save table metadata: %s", e)


def delete_tables_by_source_id(source_id: str, conn=None):
    """
    Delete all DuckDB tables associated with a given source_id.
    
    This is used for atomic sheet-level rebuilds: when a sheet changes,
    ALL tables derived from that sheet are deleted before rebuilding.
    
    Args:
        source_id: Source identifier (spreadsheet_id#sheet_name)
        conn: Optional DuckDB connection (creates new one if None)
    
    Returns:
        Number of tables deleted
    """
    close_conn = False
    if conn is None:
        conn = duckdb.connect(DB_PATH)
        close_conn = True
    
    try:
        # Load table metadata to find tables with this source_id
        metadata = load_table_metadata()
        
        tables_to_delete = []
        for table_name, table_meta in metadata.items():
            if table_meta.get('source_id') == source_id:
                tables_to_delete.append(table_name)
        
        # Delete each table
        for table_name in tables_to_delete:
            try:
                quoted_table = quote_identifier(table_name)
                conn.execute(f"DROP TABLE IF EXISTS {quoted_table}")
                logger.info("Deleted table: %s", table_name)
                
                # Remove from metadata
                del metadata[table_name]
            except Exception as e:
                logger.warning("Error deleting table %s: %s", table_name, e)
        
        # Save updated metadata
        if tables_to_delete:
            save_table_metadata(metadata)
        
        return len(tables_to_delete)
        
    finally:
        if close_conn:
            conn.close()


def drop_all_tables(conn):
    """Drop all tables in DuckDB database"""
    try:
        # Get list of all tables
        tables_result = conn.execute("SHOW TABLES").fetchall()
        tables = [row[0] for row in tables_result]
        
        # Drop each table
        for table in tables:
            quoted_table = quote_identifier(table)
            conn.execute(f"DROP TABLE IF EXISTS {quoted_table}")
            logger.info("Dropped table: %s", table)
        
        return len(tables)
    except Exception as e:
        logger.warning("Error dropping tables: %s", e)
        return 0


def reset_duckdb_snapshot():
    """Delete and recreate DuckDB snapshot file for clean state"""
    try:
        # Ensure parent directory exists (critical for container deployments)
        Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)

        if Path(DB_PATH).exists():
            os.remove(DB_PATH)
            logger.info("Deleted old DuckDB file: %s", DB_PATH)

        # Create new empty database
        conn = duckdb.connect(DB_PATH)
        conn.close()
        logger.info("Created fresh DuckDB file: %s", DB_PATH)
        
        # Clear table metadata
        save_table_metadata({})
        
    except Exception as e:
        logger.warning("Error resetting DuckDB: %s", e)


def load_snapshot(sheets_with_tables=None, full_reset=False, changed_sheets=None):
    """
    Load Google Sheets data into DuckDB with multi-table detection.

    SHEET-LEVEL REBUILD LOGIC:
    - If full_reset=True: Delete all tables and rebuild everything
    - If changed_sheets provided: Delete only tables from changed sheets, rebuild those sheets
    - Otherwise: Incremental refresh (drop and recreate all tables)

    Args:
        sheets_with_tables: Pre-fetched sheets with detected tables.
                           Dict[sheet_name, List[table_info]].
                           If None, will fetch from Google Sheets.
        full_reset: If True, perform full reset (drop all tables, recreate DB).
        changed_sheets: List of sheet names that changed (for incremental rebuild).
                       If provided, only these sheets will be rebuilt.
    """
    from datetime import datetime

    # Use pre-fetched sheets if provided, otherwise fetch
    if sheets_with_tables is None:
        sheets_with_tables = fetch_sheets_with_tables()

    # Load existing table metadata
    table_metadata = load_table_metadata()

    conn = None  # Initialize connection variable for proper cleanup

    try:
        if full_reset:
            logger.info("Performing FULL RESET...")

            # Drop all tables and recreate DB file
            reset_duckdb_snapshot()
            table_metadata = {}

            # Connect to fresh database
            conn = duckdb.connect(DB_PATH)

            # Rebuild all sheets
            sheets_to_rebuild = sorted(sheets_with_tables.keys())

        elif changed_sheets:
            logger.info("Performing INCREMENTAL REBUILD for %d sheet(s)...", len(changed_sheets))

            # Connect to existing database
            conn = duckdb.connect(DB_PATH)

            # Delete tables from changed sheets
            for sheet_name in changed_sheets:
                # Get source_id for this sheet
                if sheet_name in sheets_with_tables and sheets_with_tables[sheet_name]:
                    source_id = sheets_with_tables[sheet_name][0].get('source_id')
                    if source_id:
                        logger.info("Deleting tables from sheet '%s' (source_id: %s)...", sheet_name, source_id)
                        deleted_count = delete_tables_by_source_id(source_id, conn)
                        logger.info("Deleted %d table(s)", deleted_count)

            # Rebuild only changed sheets
            sheets_to_rebuild = changed_sheets

        else:
            # Legacy incremental refresh (rebuild all)
            logger.info("Performing LEGACY INCREMENTAL REFRESH...")
            conn = duckdb.connect(DB_PATH)
            sheets_to_rebuild = sorted(sheets_with_tables.keys())

        # Track used names to ensure uniqueness per snapshot load
        # Map: base_name -> count
        name_counts = {}

        # Load tables from sheets to rebuild
        for sheet_name in sheets_to_rebuild:
            if sheet_name not in sheets_with_tables:
                continue

            tables = sheets_with_tables[sheet_name]

            for idx, table_info in enumerate(tables, 1):
                # Determine base name
                if 'title' in table_info and table_info['title']:
                    # Use semantic title (pass idx for fallback if title sanitizes to empty)
                    base_name = sanitize_table_name(table_info['title'], idx)
                else:
                    # Fallback to SheetName_TableN
                    sheet_base = sanitize_table_name(sheet_name, idx)
                    base_name = f"{sheet_base}_Table{idx}"

                # Calculate unique final name
                if base_name in name_counts:
                    name_counts[base_name] += 1
                    final_name = f"{base_name}_{name_counts[base_name]}"
                else:
                    name_counts[base_name] = 1
                    # Special case: if base_name came from a title, use it directly for the first occurrence
                    final_name = base_name

                quoted_table = quote_identifier(final_name)

                # Get the dataframe for this table
                df = table_info['dataframe']

                # Drop table if it exists (for incremental refresh)
                conn.execute(f"DROP TABLE IF EXISTS {quoted_table}")

                # Create table in DuckDB
                conn.execute(f"CREATE TABLE {quoted_table} AS SELECT * FROM df")
                logger.info("Created table: %s (%d rows, %d cols)", final_name, len(df), len(df.columns))

                # Store the final table name in table_info for later use
                table_info['duckdb_table_name'] = final_name

                # Update table metadata
                table_metadata[final_name] = {
                    "source_id": table_info.get('source_id'),
                    "sheet_name": table_info.get('sheet_name'),
                    "table_index": idx,
                    "row_count": len(df),
                    "created_at": datetime.now().isoformat()
                }

    finally:
        # Always close the connection to prevent leaks
        if conn is not None:
            conn.close()

    # Save updated table metadata
    save_table_metadata(table_metadata)

    if full_reset:
        logger.info("Full reset complete")
    elif changed_sheets:
        logger.info("Incremental rebuild complete (%d sheet(s) rebuilt)", len(changed_sheets))
    else:
        logger.info("Legacy incremental refresh complete")

    # Log table statistics (use context manager for auto-cleanup)
    logger.info("Table Statistics:")

    try:
        conn = duckdb.connect(DB_PATH)

        for sheet_name in sorted(sheets_to_rebuild):
            if sheet_name not in sheets_with_tables:
                continue

            tables = sheets_with_tables[sheet_name]
            for idx, table_info in enumerate(tables, 1):
                final_name = table_info.get('duckdb_table_name')
                if not final_name:
                    continue

                quoted_table = quote_identifier(final_name)

                try:
                    row_count = conn.execute(f"SELECT COUNT(*) FROM {quoted_table}").fetchone()[0]
                    col_info = conn.execute(f"DESCRIBE {quoted_table}").fetchdf()

                    # Count column types
                    type_counts = col_info['column_type'].value_counts().to_dict()
                    type_summary = ", ".join([f"{count} {dtype}" for dtype, count in type_counts.items()])

                    # Show table lineage
                    row_range = table_info.get('row_range', (0, 0))
                    # Provide 1-based index for user friendliness
                    r_start = row_range[0] + 1
                    r_end = row_range[1]
                    logger.info("%s: %s rows, %d cols (%s)", final_name, f"{row_count:,}", len(col_info), type_summary)
                    logger.debug("  Source: %s rows %d-%d", sheet_name, r_start, r_end)

                except Exception as e:
                    logger.warning("Error reading stats for %s: %s", final_name, e)
    finally:
        # Always close the stats connection
        if conn is not None:
            conn.close()

    # Mark as synced after successful load
    from data_sources.gsheet.change_detector import mark_synced
    mark_synced(sheets_with_tables)
