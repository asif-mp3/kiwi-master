"""
Sync Manager - Auto-Sync Orchestration for Data Sources

Manages automatic synchronization of connected data sources:
- Hash-based change detection
- Polling-based sync scheduling
- Failure isolation (old data preserved on error)
- Atomic table swaps in DuckDB

This module provides the core sync logic. For background scheduling,
see sync_scheduler.py.
"""

import hashlib
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Any
import pandas as pd

from data_sources.connector_factory import ConnectorFactory
from data_sources.source_registry import (
    SourceRegistry, SourceState, TableStats,
    generate_source_id, get_registry
)


@dataclass
class SyncResult:
    """Result of a sync operation."""
    source_id: str
    changed: bool
    success: bool
    tables_updated: int = 0
    rows_updated: int = 0
    error: Optional[str] = None
    duration_ms: int = 0

    def to_dict(self) -> Dict:
        return {
            "source_id": self.source_id,
            "changed": self.changed,
            "success": self.success,
            "tables_updated": self.tables_updated,
            "rows_updated": self.rows_updated,
            "error": self.error,
            "duration_ms": self.duration_ms
        }


def compute_data_hash(tables: Dict[str, List[pd.DataFrame]]) -> str:
    """
    Compute hash of table data for change detection.

    Uses a combination of:
    - Column names and dtypes
    - Row count
    - Sample of actual data (first/last rows)

    This is faster than hashing all data while still detecting
    meaningful changes.

    Args:
        tables: Dict of table names to DataFrames

    Returns:
        SHA256 hash string
    """
    hash_parts = []

    for name, dfs in sorted(tables.items()):
        for i, df in enumerate(dfs):
            # Include table name
            hash_parts.append(f"table:{name}:{i}")

            # Include schema (columns and types)
            schema = [(str(col), str(df[col].dtype)) for col in df.columns]
            hash_parts.append(f"schema:{schema}")

            # Include row count
            hash_parts.append(f"rows:{len(df)}")

            # Include sample data (first and last 5 rows)
            if len(df) > 0:
                # First rows
                first_rows = df.head(5).to_string()
                hash_parts.append(f"first:{first_rows}")

                # Last rows
                last_rows = df.tail(5).to_string()
                hash_parts.append(f"last:{last_rows}")

    combined = "\n".join(hash_parts)
    return hashlib.sha256(combined.encode()).hexdigest()


def compute_table_stats(name: str, df: pd.DataFrame) -> TableStats:
    """
    Compute statistics for a single table.

    Args:
        name: Table name
        df: DataFrame

    Returns:
        TableStats object
    """
    schema_str = str([(col, str(df[col].dtype)) for col in df.columns])
    schema_hash = hashlib.sha256(schema_str.encode()).hexdigest()[:16]

    now = datetime.now().isoformat()

    return TableStats(
        name=name,
        row_count=len(df),
        column_count=len(df.columns),
        last_schema_hash=schema_hash,
        created_at=now,
        updated_at=now
    )


class SyncManager:
    """
    Manages source registration and synchronization.

    Responsibilities:
    - Register new sources for tracking
    - Check for changes via hash comparison
    - Trigger sync when changes detected
    - Handle failures gracefully (preserve old data)
    """

    def __init__(self, registry: Optional[SourceRegistry] = None):
        """
        Initialize SyncManager.

        Args:
            registry: Optional SourceRegistry instance.
                     If None, uses the global singleton.
        """
        self.registry = registry or get_registry()

    def register_source(
        self,
        url: str,
        auth_identity: str = "",
        sync_interval: int = 300,
        credentials: Optional[Dict] = None,
        display_name: Optional[str] = None
    ) -> SourceState:
        """
        Register a new data source for tracking and sync.

        Args:
            url: Source URL
            auth_identity: User/service account identifier for source ID
            sync_interval: Sync interval in seconds (default 5 minutes)
            credentials: Optional credentials dict
            display_name: Optional display name

        Returns:
            Created SourceState
        """
        # Generate source ID
        source_id = generate_source_id(url, auth_identity)

        # Check if already registered
        existing = self.registry.get(source_id)
        if existing:
            print(f"[SyncManager] Source already registered: {source_id}")
            return existing

        # Detect connector type
        connector = ConnectorFactory.create(url, credentials)
        connector_type = connector.__class__.__name__.replace('Connector', '').lower()

        # Create initial state
        state = SourceState(
            source_id=source_id,
            url=url,
            connector_type=connector_type,
            status="active",
            auth_mode=getattr(connector, 'auth_mode', 'anonymous'),
            sync_interval=sync_interval,
            display_name=display_name or ""
        )

        # Save credentials reference if provided
        if credentials:
            # TODO: Encrypt and store credentials
            state.credentials_ref = f"cred_{source_id[:8]}"

        # Register with registry
        self.registry.create(state)

        print(f"[SyncManager] Registered source: {source_id} ({connector_type})")
        return state

    def unregister_source(self, source_id: str) -> bool:
        """
        Unregister a source (stop tracking).

        Args:
            source_id: Source ID to unregister

        Returns:
            True if unregistered, False if not found
        """
        return self.registry.delete(source_id)

    def sync_source(
        self,
        source_id: str,
        force: bool = False,
        load_to_db: bool = True
    ) -> SyncResult:
        """
        Sync a registered source.

        Process:
        1. Fetch new data from source
        2. Compute hash for change detection
        3. If changed (or force=True), update stored data
        4. Update registry state

        On failure, old data is preserved (failure isolation).

        Args:
            source_id: Source ID to sync
            force: If True, sync even if hash unchanged
            load_to_db: If True, load data into DuckDB

        Returns:
            SyncResult with operation details
        """
        start_time = time.time()

        source = self.registry.get(source_id)
        if not source:
            return SyncResult(
                source_id=source_id,
                changed=False,
                success=False,
                error="Source not found"
            )

        # Mark as syncing
        self.registry.mark_syncing(source_id)

        try:
            # Create connector
            connector = ConnectorFactory.create(source.url)

            # Fetch new data
            print(f"[SyncManager] Fetching data for {source_id}...")
            tables = connector.fetch_tables()

            if not tables:
                print(f"[SyncManager] No tables returned for {source_id}")
                self.registry.mark_success(source_id, "", 0, 0)
                return SyncResult(
                    source_id=source_id,
                    changed=False,
                    success=True,
                    duration_ms=int((time.time() - start_time) * 1000)
                )

            # Compute hash
            new_hash = compute_data_hash(tables)

            # Check if changed
            if not force and new_hash == source.last_hash:
                print(f"[SyncManager] No changes detected for {source_id}")
                return SyncResult(
                    source_id=source_id,
                    changed=False,
                    success=True,
                    duration_ms=int((time.time() - start_time) * 1000)
                )

            # Load to DuckDB if requested
            if load_to_db:
                self._load_to_duckdb(source_id, tables)

            # Compute stats
            total_rows = 0
            table_stats = {}
            for name, dfs in tables.items():
                for i, df in enumerate(dfs):
                    total_rows += len(df)
                    table_name = f"{name}_{i}" if len(dfs) > 1 else name
                    table_stats[table_name] = compute_table_stats(table_name, df)

            # Update registry
            self.registry.mark_success(
                source_id,
                new_hash,
                row_count=total_rows,
                table_count=len(table_stats),
                tables=table_stats
            )

            duration_ms = int((time.time() - start_time) * 1000)
            print(f"[SyncManager] Sync complete for {source_id}: {len(table_stats)} tables, {total_rows} rows ({duration_ms}ms)")

            return SyncResult(
                source_id=source_id,
                changed=True,
                success=True,
                tables_updated=len(table_stats),
                rows_updated=total_rows,
                duration_ms=duration_ms
            )

        except Exception as e:
            # Mark as error but preserve old data
            error_msg = str(e)
            self.registry.mark_error(source_id, error_msg)

            duration_ms = int((time.time() - start_time) * 1000)
            print(f"[SyncManager] Sync failed for {source_id}: {error_msg}")

            return SyncResult(
                source_id=source_id,
                changed=False,
                success=False,
                error=error_msg,
                duration_ms=duration_ms
            )

    def _load_to_duckdb(self, source_id: str, tables: Dict[str, List[pd.DataFrame]]) -> None:
        """
        Load tables into DuckDB with atomic swap.

        Uses temp tables and atomic rename to ensure
        old data is available until new data is fully loaded.

        Args:
            source_id: Source ID for table naming
            tables: Dict of table names to DataFrames
        """
        try:
            # Import here to avoid circular dependency
            from data_sources.gsheet.snapshot_loader import load_snapshot

            # Flatten the tables dict for the loader
            flat_tables = {}
            for name, dfs in tables.items():
                for i, df in enumerate(dfs):
                    table_name = f"{name}_{i}" if len(dfs) > 1 else name
                    flat_tables[table_name] = df

            # Load using existing snapshot loader
            # This handles the DuckDB loading
            load_snapshot(flat_tables, source_id=source_id)

            print(f"[SyncManager] Loaded {len(flat_tables)} tables to DuckDB")

        except Exception as e:
            print(f"[SyncManager] Error loading to DuckDB: {e}")
            raise

    def sync_all(self, force: bool = False) -> List[SyncResult]:
        """
        Sync all registered sources.

        Args:
            force: If True, sync all sources regardless of hash

        Returns:
            List of SyncResults
        """
        results = []
        sources = self.registry.get_all()

        print(f"[SyncManager] Syncing {len(sources)} sources...")

        for source in sources:
            result = self.sync_source(source.source_id, force=force)
            results.append(result)

        return results

    def sync_due_sources(self) -> List[SyncResult]:
        """
        Sync all sources that are due based on their schedule.

        Returns:
            List of SyncResults for sources that were synced
        """
        results = []
        due_sources = self.registry.get_sources_due_for_sync()

        if due_sources:
            print(f"[SyncManager] {len(due_sources)} sources due for sync")

            for source in due_sources:
                result = self.sync_source(source.source_id)
                results.append(result)

        return results

    def get_source_status(self, source_id: str) -> Optional[Dict]:
        """
        Get status of a specific source.

        Args:
            source_id: Source ID

        Returns:
            Status dict or None if not found
        """
        source = self.registry.get(source_id)
        if not source:
            return None

        return {
            "source_id": source.source_id,
            "url": source.url,
            "connector_type": source.connector_type,
            "status": source.status,
            "last_sync": source.last_sync,
            "last_error": source.last_error,
            "row_count": source.row_count,
            "table_count": source.table_count,
            "sync_interval": source.sync_interval,
            "next_sync": source.next_sync
        }

    def get_all_sources(self) -> List[Dict]:
        """
        Get list of all registered sources.

        Returns:
            List of source status dicts
        """
        sources = self.registry.get_all()
        return [
            {
                "source_id": s.source_id,
                "url": s.url,
                "display_name": s.display_name or s.url[:50],
                "connector_type": s.connector_type,
                "status": s.status,
                "last_sync": s.last_sync,
                "row_count": s.row_count,
                "table_count": s.table_count
            }
            for s in sources
        ]

    def get_health(self) -> Dict[str, Any]:
        """
        Get health summary for all sources.

        Returns:
            Health summary dict
        """
        return self.registry.get_health_summary()


# Singleton instance
_sync_manager: Optional[SyncManager] = None


def get_sync_manager() -> SyncManager:
    """Get the singleton SyncManager instance."""
    global _sync_manager
    if _sync_manager is None:
        _sync_manager = SyncManager()
    return _sync_manager
