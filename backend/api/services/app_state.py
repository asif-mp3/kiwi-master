"""Application state management - singleton pattern with lazy-loaded components."""
import os
import sys
from typing import Optional, List, Dict, Any

from utils.logger import get_logger
from schema_intelligence.chromadb_client import SchemaVectorStore
from schema_intelligence.profile_store import ProfileStore
from planning_layer.table_router import TableRouter
from execution_layer.query_healer import QueryHealer
from planning_layer.entity_extractor import EntityExtractor
from utils.query_context import ConversationManager
from utils.personality import TharaPersonality
from utils.onboarding import OnboardingManager, get_user_name
from utils.correction_detector import CorrectionIntentDetector
from utils.permanent_memory import load_memory
from analytics_engine.duckdb_manager import DuckDBManager

logger = get_logger("state")

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

        # Default data source tracking (Phase 1)
        self.default_source_url: Optional[str] = None  # Drive folder URL used as default
        self.is_default_source: bool = False  # True if using default, not user-added
        self.startup_error: Optional[str] = None  # Error message if default load failed

        # Loading progress tracking (Phase 2 - SSE)
        self.loading_status: Dict[str, Any] = {
            "phase": "idle",       # idle | connecting | fetching | profiling | ready | error
            "message": "",
            "progress": 0,         # 0-100
            "tables_found": 0,
            "tables_profiled": 0,
            "total_tables": 0,
            "complete": False,
            "error": None,
        }

        # Gemini availability flag (Phase 6)
        self.gemini_available: bool = False

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

        # Load user preferences from permanent memory (e.g., "address_as": "Boss")
        self._load_user_preferences()
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

        Also loads metadata (total_records, detected_tables) so the
        /api/dataset-status endpoint returns correct values.
        """
        try:
            from analytics_engine.duckdb_manager import DuckDBManager

            db_path = project_root / "data_sources" / "snapshots" / "latest.duckdb"
            profiles_path = project_root / "data_sources" / "table_profiles.json"

            # Check DuckDB has data
            has_duckdb_data = False
            table_names = []
            if db_path.exists() and db_path.stat().st_size > 0:
                db = DuckDBManager()
                table_names = db.list_tables()
                if table_names and len(table_names) > 0:
                    has_duckdb_data = True

            # Check profiles exist
            has_profiles = profiles_path.exists() and profiles_path.stat().st_size > 100

            # Only mark as loaded if BOTH exist
            if has_duckdb_data and has_profiles:
                self.data_loaded = True
                logger.info("Found existing data (DuckDB + profiles) - no reload needed")

                # IMPORTANT: Also load metadata so /api/dataset-status returns correct values
                try:
                    db = DuckDBManager()
                    total_records = 0
                    detected_tables = []
                    original_sheets = set()

                    for table_name in table_names:
                        try:
                            # Get row count for this table
                            result = db.query(f'SELECT COUNT(*) as cnt FROM "{table_name}"')
                            # Convert numpy.int64 to native Python int for JSON serialization
                            row_count = int(result.iloc[0]['cnt']) if len(result) > 0 else 0
                            total_records += row_count

                            # Get column info
                            sample = db.query(f'SELECT * FROM "{table_name}" LIMIT 1')
                            columns = [str(col) for col in sample.columns] if len(sample) > 0 else []

                            # Extract original sheet name (remove file prefix if present)
                            # Format is typically: "filename__sheetname" or just "sheetname"
                            if '__' in table_name:
                                parts = table_name.split('__')
                                sheet_name = parts[-1] if len(parts) > 1 else table_name
                            else:
                                sheet_name = table_name
                            original_sheets.add(sheet_name)

                            detected_tables.append({
                                'table_id': str(table_name),
                                'title': str(table_name),
                                'sheet_name': str(sheet_name),
                                'source_id': '',
                                'total_rows': row_count,  # Already converted to int above
                                'columns': columns
                            })
                        except Exception as table_err:
                            logger.warning("Could not get metadata for %s: %s", table_name, table_err)

                    self.total_records = int(total_records)  # Ensure native int
                    self.detected_tables = detected_tables
                    self.original_sheet_names = list(original_sheets)
                    logger.info("Loaded metadata: %d tables, %s records", len(table_names), f"{total_records:,}")

                except Exception as meta_err:
                    logger.warning("Could not load metadata: %s", meta_err)

        except Exception as e:
            # Silently fail - will load data normally
            pass

    def _load_user_preferences(self):
        """
        Load user preferences from permanent memory on startup.
        This ensures the user's saved name preference (e.g., "Boss") is used.
        """
        try:
            memory = load_memory()
            user_prefs = memory.get("user_preferences", {})

            # Load user's preferred name
            if user_prefs.get("address_as"):
                name = user_prefs["address_as"]
                self.personality.set_name(name)
                logger.info("Loaded user preference: address_as = '%s'", name)
        except Exception as e:
            logger.warning("Could not load user preferences: %s", e)

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

    def update_loading_status(self, phase: str, message: str, progress: int = 0,
                               tables_found: int = 0, tables_profiled: int = 0,
                               total_tables: int = 0, complete: bool = False,
                               error: Optional[str] = None):
        """Update loading status for SSE progress streaming."""
        self.loading_status = {
            "phase": phase,
            "message": message,
            "progress": min(progress, 100),
            "tables_found": tables_found,
            "tables_profiled": tables_profiled,
            "total_tables": total_tables,
            "complete": complete,
            "error": error,
        }

    def reset_loading_status(self):
        """Reset loading status to idle."""
        self.loading_status = {
            "phase": "idle",
            "message": "",
            "progress": 0,
            "tables_found": 0,
            "tables_profiled": 0,
            "total_tables": 0,
            "complete": False,
            "error": None,
        }

    def get_smart_suggestions(self, max_suggestions: int = 5) -> List[str]:
        """
        Generate starter query suggestions based on loaded table profiles.
        Returns dataset-aware questions the user can ask.
        """
        try:
            if not self.data_loaded or self._profile_store is None:
                return []

            profiles = self._profile_store.get_all_profiles()
            if not profiles:
                return []

            suggestions = []

            for table_name, profile in list(profiles.items())[:6]:
                columns = profile.get("columns", {})
                metrics = [c for c, info in columns.items() if info.get("role") == "metric"]
                dimensions = [c for c, info in columns.items() if info.get("role") == "dimension"]
                date_cols = [c for c, info in columns.items() if info.get("role") == "date"]

                # Clean table name for display
                display_name = table_name.replace("_", " ")

                # Metric-based suggestions
                if metrics:
                    metric = metrics[0].replace("_", " ")
                    suggestions.append(f"What is the total {metric}?")
                    if dimensions:
                        dim = dimensions[0].replace("_", " ")
                        suggestions.append(f"Show {metric} by {dim}")
                    if date_cols:
                        suggestions.append(f"Show {metric} trend over time")

                # Dimension-based suggestions
                if dimensions and len(dimensions) >= 2:
                    dim = dimensions[0].replace("_", " ")
                    suggestions.append(f"What are the top 5 {dim}?")

                # Row count suggestion
                total_rows = profile.get("total_rows", 0)
                if total_rows > 100:
                    suggestions.append(f"How many records are in {display_name}?")

                if len(suggestions) >= max_suggestions * 2:
                    break

            # Deduplicate and limit
            seen = set()
            unique = []
            for s in suggestions:
                s_lower = s.lower()
                if s_lower not in seen:
                    seen.add(s_lower)
                    unique.append(s)

            return unique[:max_suggestions]

        except Exception as e:
            logger.warning("Could not generate smart suggestions: %s", e)
            return []


# Singleton instance
app_state = AppState()
