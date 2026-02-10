"""
Source Registry - State Management for Connected Data Sources

Manages the state of all connected data sources including:
- Source metadata (URL, connector type, auth)
- Health metrics (status, errors, sync times)
- Data metrics (row counts, table counts)
- Schema tracking for change detection

State is persisted to JSON for durability across restarts.
"""

import json
import hashlib
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from urllib.parse import urlparse, parse_qs


# Path to registry state file
_MODULE_DIR = Path(__file__).parent
REGISTRY_PATH = _MODULE_DIR / "source_registry.json"


@dataclass
class TableStats:
    """Statistics for a single table within a source."""
    name: str
    row_count: int = 0
    column_count: int = 0
    last_schema_hash: str = ""
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> "TableStats":
        return cls(**data)


@dataclass
class SourceState:
    """Complete state for a connected data source."""
    source_id: str              # hash(url + auth_identity)
    url: str                    # Original URL
    connector_type: str         # "dropbox", "local", "pdf", etc.

    # Health metrics
    status: str = "active"      # "active" | "syncing" | "error" | "disconnected"
    last_sync: Optional[str] = None
    last_error: Optional[str] = None
    last_error_time: Optional[str] = None
    consecutive_failures: int = 0

    # Data metrics
    last_hash: Optional[str] = None  # SHA256 of data/metadata
    row_count: int = 0               # Total rows across all tables
    table_count: int = 0             # Number of tables loaded
    tables: Dict[str, TableStats] = field(default_factory=dict)

    # Auth state
    auth_mode: str = "anonymous"
    credentials_ref: Optional[str] = None  # Reference to secure storage
    token_expires_at: Optional[str] = None

    # Sync settings
    sync_interval: int = 300  # seconds (default 5 minutes)
    next_sync: Optional[str] = None

    # Metadata
    created_at: str = ""
    display_name: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()

    def to_dict(self) -> Dict:
        data = asdict(self)
        # Convert TableStats objects to dicts
        data['tables'] = {k: v if isinstance(v, dict) else v.to_dict()
                         for k, v in self.tables.items()}
        return data

    @classmethod
    def from_dict(cls, data: Dict) -> "SourceState":
        # Convert table dicts to TableStats objects
        if 'tables' in data:
            data['tables'] = {k: TableStats.from_dict(v) if isinstance(v, dict) else v
                             for k, v in data['tables'].items()}
        return cls(**data)


def normalize_url(url: str) -> str:
    """
    Normalize a URL for consistent source ID generation.

    - Removes trailing slashes
    - Lowercases the scheme and host
    - Sorts query parameters
    """
    if not url:
        return ""

    # Handle file:// URLs
    if url.startswith('file://'):
        return url.lower().rstrip('/')

    # Handle local paths
    if os.path.isabs(url):
        return os.path.normpath(url).lower()

    try:
        parsed = urlparse(url)

        # Lowercase scheme and netloc
        scheme = parsed.scheme.lower()
        netloc = parsed.netloc.lower()

        # Normalize path
        path = parsed.path.rstrip('/')

        # Sort query parameters
        query_params = parse_qs(parsed.query)
        sorted_query = '&'.join(
            f"{k}={v[0]}" for k, v in sorted(query_params.items())
        ) if query_params else ""

        # Reconstruct URL
        normalized = f"{scheme}://{netloc}{path}"
        if sorted_query:
            normalized += f"?{sorted_query}"

        return normalized
    except Exception:
        return url.lower().rstrip('/')


def generate_source_id(url: str, auth_identity: str = "") -> str:
    """
    Generate deterministic source ID on backend.

    RULE: Never trust client-generated source IDs.
    Always regenerate on backend.

    Args:
        url: Source URL
        auth_identity: User ID or service account identifier

    Returns:
        16-character hex string
    """
    normalized_url = normalize_url(url)
    identity_string = f"{normalized_url}|{auth_identity}"
    return hashlib.sha256(identity_string.encode()).hexdigest()[:16]


class SourceRegistry:
    """
    Registry for managing connected data source state.

    State is persisted to JSON and loaded on startup.
    All mutations are immediately persisted.
    """

    def __init__(self, registry_path: Optional[Path] = None):
        self.registry_path = registry_path or REGISTRY_PATH
        self.sources: Dict[str, SourceState] = {}
        self._load()

    def _load(self) -> None:
        """Load registry state from disk."""
        if self.registry_path.exists():
            try:
                with open(self.registry_path, 'r') as f:
                    data = json.load(f)
                    self.sources = {
                        k: SourceState.from_dict(v) for k, v in data.items()
                    }
                print(f"[SourceRegistry] Loaded {len(self.sources)} sources from {self.registry_path}")
            except Exception as e:
                print(f"[SourceRegistry] Error loading registry: {e}")
                self.sources = {}
        else:
            self.sources = {}

    def _save(self) -> None:
        """Persist registry state to disk."""
        try:
            # Ensure directory exists
            self.registry_path.parent.mkdir(parents=True, exist_ok=True)

            data = {k: v.to_dict() for k, v in self.sources.items()}
            with open(self.registry_path, 'w') as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            print(f"[SourceRegistry] Error saving registry: {e}")

    def get(self, source_id: str) -> Optional[SourceState]:
        """Get source state by ID."""
        return self.sources.get(source_id)

    def get_by_url(self, url: str, auth_identity: str = "") -> Optional[SourceState]:
        """Get source state by URL (regenerates source ID)."""
        source_id = generate_source_id(url, auth_identity)
        return self.get(source_id)

    def get_all(self) -> List[SourceState]:
        """Get all registered sources."""
        return list(self.sources.values())

    def create(self, state: SourceState) -> SourceState:
        """
        Create a new source registration.

        Args:
            state: Initial source state

        Returns:
            Created source state
        """
        if state.source_id in self.sources:
            raise ValueError(f"Source {state.source_id} already exists")

        self.sources[state.source_id] = state
        self._save()
        print(f"[SourceRegistry] Created source: {state.source_id}")
        return state

    def update(self, source_id: str, **updates) -> Optional[SourceState]:
        """
        Update an existing source.

        Args:
            source_id: Source ID to update
            **updates: Field updates

        Returns:
            Updated source state or None if not found
        """
        source = self.sources.get(source_id)
        if not source:
            return None

        for key, value in updates.items():
            if hasattr(source, key):
                setattr(source, key, value)

        self._save()
        return source

    def delete(self, source_id: str) -> bool:
        """
        Delete a source registration.

        Args:
            source_id: Source ID to delete

        Returns:
            True if deleted, False if not found
        """
        if source_id in self.sources:
            del self.sources[source_id]
            self._save()
            print(f"[SourceRegistry] Deleted source: {source_id}")
            return True
        return False

    def mark_syncing(self, source_id: str) -> None:
        """Mark a source as currently syncing."""
        self.update(source_id, status="syncing")

    def mark_success(self, source_id: str, new_hash: str,
                     row_count: int = 0, table_count: int = 0,
                     tables: Optional[Dict[str, TableStats]] = None) -> None:
        """Mark a sync as successful."""
        now = datetime.now().isoformat()
        updates = {
            "status": "active",
            "last_sync": now,
            "last_hash": new_hash,
            "last_error": None,
            "consecutive_failures": 0,
            "row_count": row_count,
            "table_count": table_count,
        }
        if tables:
            updates["tables"] = tables

        # Calculate next sync time
        source = self.get(source_id)
        if source:
            next_sync_dt = datetime.now()
            next_sync_dt = next_sync_dt.replace(
                second=next_sync_dt.second + source.sync_interval
            )
            updates["next_sync"] = next_sync_dt.isoformat()

        self.update(source_id, **updates)

    def mark_error(self, source_id: str, error: str) -> None:
        """Mark a sync as failed."""
        source = self.get(source_id)
        if not source:
            return

        now = datetime.now().isoformat()
        self.update(
            source_id,
            status="error",
            last_error=error,
            last_error_time=now,
            consecutive_failures=source.consecutive_failures + 1
        )

    def get_sources_due_for_sync(self) -> List[SourceState]:
        """Get all sources that need syncing based on their schedule."""
        now = datetime.now()
        due = []

        for source in self.sources.values():
            if source.status == "syncing":
                continue  # Already syncing

            if source.next_sync:
                try:
                    next_sync = datetime.fromisoformat(source.next_sync)
                    if now >= next_sync:
                        due.append(source)
                except ValueError:
                    due.append(source)  # Invalid date, sync anyway
            elif source.last_sync is None:
                due.append(source)  # Never synced

        return due

    def get_health_summary(self) -> Dict[str, Any]:
        """Get health summary for all sources."""
        sources = list(self.sources.values())
        return {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total": len(sources),
                "active": sum(1 for s in sources if s.status == "active"),
                "syncing": sum(1 for s in sources if s.status == "syncing"),
                "error": sum(1 for s in sources if s.status == "error"),
                "disconnected": sum(1 for s in sources if s.status == "disconnected"),
                "total_rows": sum(s.row_count for s in sources),
                "total_tables": sum(s.table_count for s in sources)
            },
            "sources": [
                {
                    "source_id": s.source_id,
                    "connector": s.connector_type,
                    "display_name": s.display_name or s.url[:50],
                    "status": s.status,
                    "last_sync": s.last_sync,
                    "last_error": s.last_error,
                    "row_count": s.row_count,
                    "table_count": s.table_count,
                    "consecutive_failures": s.consecutive_failures
                }
                for s in sources
            ]
        }


# Singleton instance
_registry: Optional[SourceRegistry] = None


def get_registry() -> SourceRegistry:
    """Get the singleton registry instance."""
    global _registry
    if _registry is None:
        _registry = SourceRegistry()
    return _registry
