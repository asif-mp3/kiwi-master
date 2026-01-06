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
from utils.greeting_detector import is_greeting, get_greeting_response, detect_schema_inquiry
from utils.query_context import QueryContext, QueryTurn, ConversationManager, PendingClarification
from utils.personality import TharaPersonality
from utils.onboarding import OnboardingManager, get_user_name
from utils.query_cache import get_query_cache, cache_query_result, get_cached_query_result, invalidate_spreadsheet_cache
from utils.config_loader import get_config
from analytics_engine.duckdb_manager import DuckDBManager
import yaml


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
        self._user_name_loaded: bool = False

        # Lazy-initialized heavy components (use underscore prefix)
        self._vector_store: Optional[SchemaVectorStore] = None
        self._profile_store: Optional[ProfileStore] = None
        self._table_router: Optional[TableRouter] = None
        self._query_healer: Optional[QueryHealer] = None

        # Light components - initialize immediately (cheap)
        self.conversation_manager: ConversationManager = ConversationManager()
        self.personality: TharaPersonality = TharaPersonality()
        self.onboarding: OnboardingManager = OnboardingManager()
        self.entity_extractor: EntityExtractor = EntityExtractor()

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


def load_dataset_service(url: str, user_id: str = None) -> Dict[str, Any]:
    """
    Load data from Google Sheets with profiling.
    Now includes table profiling for intelligent routing.

    Args:
        url: Google Sheets URL or ID
        user_id: Optional user ID for OAuth credentials
    """
    try:
        print(f"[Dataset] Starting load for URL: {url}")

        # Set current user for OAuth credentials
        if user_id:
            from data_sources.gsheet.connector import set_current_user
            set_current_user(user_id)
            print(f"[Dataset] Using credentials for user: {user_id}")

        spreadsheet_id = extract_spreadsheet_id(url)
        if not spreadsheet_id:
            return {
                'success': False,
                'error': 'Invalid Google Sheets URL or ID'
            }

        print(f"[Dataset] Extracted spreadsheet ID: {spreadsheet_id}")

        # Update config with new spreadsheet ID
        config_path = project_root / "config" / "settings.yaml"
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)

        config['google_sheets']['spreadsheet_id'] = spreadsheet_id

        with open(config_path, 'w') as f:
            yaml.dump(config, f)

        # Initialize all components
        app_state.initialize()
        store = app_state.vector_store

        # Fetch sheets with multi-table detection
        print(f"[Dataset] Fetching sheets with tables...")
        sheets_with_tables = fetch_sheets_with_tables()
        print(f"[Dataset] Fetched {len(sheets_with_tables)} sheets")

        # OPTIMIZATION: Populate sheet cache so first query doesn't re-fetch
        from data_sources.gsheet.connector import get_sheet_cache
        sheet_cache = get_sheet_cache()
        sheet_cache.set_cached_data(spreadsheet_id, sheets_with_tables)
        print(f"[Dataset] Populated sheet cache for 60s TTL")

        # Clear and rebuild vector store
        print(f"[Dataset] Clearing vector store...")
        store.clear_collection()
        print(f"[Dataset] Loading snapshot...")
        load_snapshot(sheets_with_tables, full_reset=True)
        print(f"[Dataset] Rebuilding vector store...")
        store.rebuild()

        # === NEW: Profile all tables for intelligent routing ===
        print(f"[Dataset] Profiling tables for intelligent routing...")
        profiler = DataProfiler()
        db = DuckDBManager()
        tables = db.list_tables()

        # CRITICAL: Clear old profiles first to prevent stale data
        # This ensures profiles match exactly what's in DuckDB
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

        # Build response
        total_tables = sum(len(tables) for tables in sheets_with_tables.values())
        total_records = 0
        detected_tables = []

        for sheet_name, tables in sheets_with_tables.items():
            for table in tables:
                df = table.get('dataframe')
                actual_rows = len(df) if df is not None else 0
                # Ensure all column names are strings (some tables have numeric headers)
                actual_columns = [str(col) for col in df.columns] if df is not None else []

                detected_tables.append({
                    'table_id': table.get('table_id', ''),
                    'title': table.get('title', ''),
                    'sheet_name': sheet_name,
                    'source_id': table.get('source_id', ''),
                    'sheet_hash': table.get('sheet_hash', ''),
                    'row_range': table.get('row_range', [0, 0]),
                    'col_range': table.get('col_range', [0, 0]),
                    'total_rows': actual_rows,
                    'columns': actual_columns,
                    'preview_data': []
                })
                total_records += actual_rows

        app_state.data_loaded = True
        app_state.current_spreadsheet_id = spreadsheet_id

        # Invalidate query cache for this spreadsheet (data has changed)
        invalidate_spreadsheet_cache(spreadsheet_id)
        print(f"[Cache] Invalidated query cache for new dataset")

        # Get data summary from onboarding
        profiles = app_state.profile_store.get_all_profiles()
        data_summary = app_state.onboarding.get_data_summary(profiles)

        print(f"[Dataset] Successfully loaded: {total_tables} tables, {total_records} records")

        return {
            'success': True,
            'stats': {
                'totalTables': total_tables,
                'totalRecords': total_records,
                'sheetCount': len(sheets_with_tables),
                'sheets': list(sheets_with_tables.keys()),
                'detectedTables': detected_tables,
                'profiledTables': profile_count
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

    OPTIMIZATION: Uses SheetCache to skip redundant downloads.
    If cache is valid (within 60s TTL), skip the expensive fetch entirely.
    """
    try:
        from data_sources.gsheet.connector import get_sheet_cache

        # FAST PATH: Check if sheet cache is still valid (saves 10-25s)
        cache = get_sheet_cache()
        spreadsheet_id = app_state.current_spreadsheet_id or ""

        # Debug: Show cache status
        print(f"  [Cache] Checking spreadsheet_id: '{spreadsheet_id[:20] if spreadsheet_id else 'EMPTY'}...'")

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
            print(f"  [Cache] Stored sheets data in cache for 60s")

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


def _execute_with_forced_table(
    original_question: str,
    processing_query: str,
    entities: Dict[str, Any],
    forced_table: str,
    is_tamil: bool,
    ctx: 'QueryContext',
    app_state: 'AppState'
) -> Dict[str, Any]:
    """
    Execute a query with a specific table (after user clarification).

    This function is called when the user has responded to a clarification
    request and we need to resume the query with their selected table.
    """
    try:
        print("\n[EXECUTE] Running with forced table...")
        print(f"  Table: {forced_table}")

        # Get schema for the forced table
        schema_context = app_state.table_router.get_table_schema(forced_table)

        # Generate plan
        print("  → Generating query plan...")
        from planning_layer.planner_client import generate_plan
        from validation_layer.plan_validator import validate_plan
        from execution_layer.sql_compiler import compile_sql
        from execution_layer.executor import execute_plan, ADVANCED_QUERY_TYPES

        plan = generate_plan(processing_query, schema_context, entities=entities)
        validate_plan(plan)

        # Override table in plan if needed
        plan['table'] = forced_table

        print(f"  ✓ Plan generated for table: {plan.get('table')}")

        # Execute - route advanced query types to specialized executor
        query_type = plan.get('query_type')
        if query_type in ADVANCED_QUERY_TYPES:
            print(f"  → Executing advanced query type: {query_type}")
            result = execute_plan(plan)
            final_sql = f"[Advanced {query_type} query - see analysis]"  # No SQL for advanced types
        else:
            sql = compile_sql(plan)
            print(f"  → Executing SQL...")
            result, final_sql = app_state.query_healer.execute_with_healing(sql, plan)

        # Check for empty results
        no_results = False
        row_count = len(result) if result is not None and hasattr(result, '__len__') else 0
        if result is None or row_count == 0:
            no_results = True
            print(f"  ! Query returned 0 rows")
        else:
            print(f"  ✓ Query returned {row_count} rows")

        # Generate explanation
        from explanation_layer.explainer_client import explain_results
        explanation = explain_results(result, query_plan=plan, original_question=processing_query)

        if no_results and explanation:
            no_data_hint = app_state.personality.handle_error('empty_result',
                "I found no data matching your query. Try adjusting your filters.")
            explanation = f"{explanation}\n\n{no_data_hint}"

        # NOTE: Personality prefix REMOVED - LLM already generates crisp responses
        # The explain_results() function handles response formatting
        # Adding personality.format_response() caused double greetings like "Looking good, Viswa!"

        # Translate if Tamil
        if is_tamil:
            from utils.translation import translate_to_tamil
            explanation = translate_to_tamil(explanation)

        # Update context
        from utils.query_context import QueryTurn
        turn = QueryTurn(
            question=original_question,
            resolved_question=processing_query,
            entities=entities,
            table_used=forced_table,
            filters_applied=plan.get('filters', []),
            result_summary=f"{row_count} rows returned",
            sql_executed=final_sql,
            was_followup=False,
            confidence=1.0  # High confidence since user chose
        )
        ctx.add_turn(turn)

        # Build response
        data_list = None
        if result is not None and hasattr(result, 'to_dict'):
            data_list = result.to_dict('records')

        print("\n[SUCCESS] Query completed with forced table!")
        print("=" * 60 + "\n")

        return {
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

    except Exception as e:
        print(f"\n[ERROR] Failed to execute with forced table: {e}")
        import traceback
        traceback.print_exc()
        error_msg = app_state.personality.handle_error('general', str(e))
        return {
            'success': False,
            'error': str(e),
            'explanation': error_msg,
            'error_type': 'execution_error'
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

    # Generate options with brief descriptions
    options = []
    for i, table_name in enumerate(candidates[:3], 1):  # Max 3 options
        profile = profile_store.get_profile(table_name) if profile_store else None
        if profile:
            table_type = profile.get('table_type', 'data')
            granularity = profile.get('granularity', '')
            row_count = profile.get('row_count', 0)

            # Create brief description
            desc_parts = []
            if granularity:
                desc_parts.append(f"{granularity} level")
            if row_count:
                desc_parts.append(f"{row_count:,} rows")
            desc = f" ({', '.join(desc_parts)})" if desc_parts else ""

            # Make table name more readable
            display_name = table_name.replace('_', ' ').replace('-', ' ')
            options.append(f"{i}. {display_name}{desc}")
        else:
            display_name = table_name.replace('_', ' ').replace('-', ' ')
            options.append(f"{i}. {display_name}")

    options_text = "\n".join(options)

    if is_tamil:
        # Tamil clarification message
        message = f"""உங்கள் கேள்விக்கு "{context_str}" பல அட்டவணைகள் பொருந்துகின்றன.

எந்த அட்டவணையை நீங்கள் குறிப்பிடுகிறீர்கள்?

{options_text}

எண் அல்லது பெயரை தட்டச்சு செய்யவும்."""
    else:
        message = f"""I found multiple tables that could answer your question about {context_str}.

Which one would you like me to use?

{options_text}

Just type the number or name."""

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
    try:
        # === FLOW LOGGING START ===
        print("\n" + "=" * 60)
        print(f"[QUERY] New query received: \"{question[:80]}{'...' if len(question) > 80 else ''}\"")
        print("=" * 60)

        # Initialize components
        print("\n[STEP 0/8] INITIALIZING...")
        app_state.initialize()
        print("  ✓ App state initialized")

        # === VALIDATE INPUT ===
        # Reject empty, too short, or obvious noise (transcription artifacts)
        question_clean = question.strip()
        if not question_clean or len(question_clean) < 3:
            print("  ✗ Empty or invalid input detected")
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

        # Get conversation context
        ctx = app_state.conversation_manager.get_context(conversation_id)
        print(f"  ✓ Context loaded (conversation: {conversation_id or 'default'})")

        # Track if we preserved context from a failed clarification match
        preserved_from_clarification = False

        # === CHECK FOR PENDING CLARIFICATION (DISAMBIGUATION FLOW) ===
        if ctx.has_pending_clarification():
            print("\n[STEP 0.5/9] CHECKING PENDING CLARIFICATION...")
            pending = ctx.get_pending_clarification()
            matched_table = ctx.match_clarification_response(question)

            if matched_table:
                print(f"  ✓ User selected table: {matched_table}")
                # User responded with a table selection - use it!
                ctx.clear_pending_clarification()

                # Restore state from pending clarification
                original_question = pending.original_question
                processing_query = pending.translated_question
                entities = pending.entities
                is_tamil = pending.is_tamil

                # Force this table to be used (bypass routing)
                forced_table = matched_table
                print(f"  → Resuming query with forced table: {forced_table}")
                print(f"  → Original question: {original_question[:50]}...")

                # Skip to planning phase with forced table
                # (This jumps ahead in the pipeline)
                return _execute_with_forced_table(
                    original_question=original_question,
                    processing_query=processing_query,
                    entities=entities,
                    forced_table=forced_table,
                    is_tamil=is_tamil,
                    ctx=ctx,
                    app_state=app_state
                )
            else:
                print(f"  ✗ Could not match response to a table option")
                print(f"    Candidates were: {pending.candidates}")
                print(f"    User said: {question}")
                # User's response didn't match - but preserve context for follow-up!
                # Save the entities from original question so they merge with new query
                if pending.entities:
                    # Preserve category, metric, location from original question
                    ctx.active_entities = pending.entities
                    ctx.active_table = None  # Don't force a table, let routing decide
                    preserved_from_clarification = True
                    print(f"  ✓ Preserved context: category={pending.entities.get('category')}, metric={pending.entities.get('metric')}")
                # Clear the pending state and continue normally
                ctx.clear_pending_clarification()
                print("  → Treating as follow-up with preserved context")

        # NOTE: Removed hardcoded "Freshggies" STT correction
        # The system should work with any business name via ProfileStore dynamic learning

        # === FAST PATH: Greetings & Conversational ===
        print("\n[STEP 1/8] GREETING DETECTION...")
        if is_greeting(question):
            print("  ✓ Greeting detected - using fast path")
            response = get_greeting_response(question)
            user_name = ctx.get_user_name() or app_state.personality.user_name
            # Only personalize if we have a real name (not empty or placeholder)
            if user_name and user_name.lower() not in ["there", "user", "friend", ""]:
                response = response.replace("Hi!", f"Hi {user_name}!")
                response = response.replace("Hello!", f"Hello {user_name}!")

            print("  → Returning greeting response")
            print("=" * 60 + "\n")
            return {
                'success': True,
                'explanation': response,
                'data': None,
                'plan': None,
                'schema_context': [],
                'data_refreshed': False,
                'is_greeting': True
            }
        print("  ✗ Not a greeting")

        # === FAST PATH: Memory Intent ===
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

        # === FAST PATH: Schema Inquiry ===
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

        # === TRANSLATION LAYER (PRE-PROCESS) ===
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

        # === CONTEXT DETECTION ===
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

        # Merge with previous context if follow-up OR if we preserved context from clarification
        if is_followup or preserved_from_clarification:
            entities = ctx.merge_entities(entities)
            merge_reason = "follow-up" if is_followup else "preserved from clarification"
            print(f"  ✓ Merged with context ({merge_reason}): {app_state.entity_extractor.get_entities_summary(entities)}")

        # === CHECK FOR DATA CHANGES (INVALIDATE STALE CACHE) ===
        print("\n[STEP 6/8] CACHE & DATA CHECK...")
        # If data was refreshed mid-session, invalidate cache to avoid stale answers
        spreadsheet_id = app_state.current_spreadsheet_id or ""
        data_was_refreshed = check_and_refresh_data()
        if data_was_refreshed:
            print(f"  ! Data was refreshed - invalidating stale cache")
            invalidate_spreadsheet_cache(spreadsheet_id)

        # === CHECK CACHE (CACHING FLOW FROM ARCHITECTURE) ===
        # Generate cache key: Hash(question + spreadsheet_id)
        # Check if result cached - saves significant time on repeat queries
        cache_hit, cached_result = get_cached_query_result(processing_query, spreadsheet_id)

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

        # === CHECK IF CLARIFICATION NEEDED (DISAMBIGUATION FLOW) ===
        if routing_result.needs_clarification:
            print(f"  ! AMBIGUITY DETECTED - need clarification")
            print(f"    Alternatives: {[t for t, _ in routing_result.alternatives[:3]]}")

            # Get candidate table names
            candidates = routing_result.get_clarification_options()

            if candidates and len(candidates) > 1:
                # Save state for when user responds
                ctx.set_pending_clarification(
                    original_question=question,
                    translated_question=processing_query,
                    candidates=candidates,
                    entities=entities,
                    is_tamil=is_tamil
                )

                # Generate clarification message
                clarification_msg = _generate_clarification_message(
                    candidates=candidates,
                    entities=entities,
                    is_tamil=is_tamil,
                    profile_store=app_state.profile_store
                )

                print("  → Returning clarification request")
                print("=" * 60 + "\n")

                return {
                    'success': True,
                    'explanation': clarification_msg,
                    'data': None,
                    'plan': None,
                    'needs_clarification': True,
                    'clarification_options': candidates,
                    'table_used': None,
                    'routing_confidence': confidence,
                    'entities_extracted': {k: v for k, v in entities.items()
                                          if v and k not in ['raw_question']},
                    'data_refreshed': data_was_refreshed
                }

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
        print("  → Generating query plan via LLM...")
        plan = generate_plan(processing_query, schema_context, entities=entities)
        validate_plan(plan)
        print(f"  ✓ Plan generated:")
        print(f"    Query type: {plan.get('query_type', 'unknown')}")
        print(f"    Table: {plan.get('table', 'unknown')}")
        print(f"    Metrics: {plan.get('metrics', [])}")
        print(f"    Filters: {plan.get('filters', [])}")

        # === EXECUTION WITH HEALING ===
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

        # === EXPLANATION WITH PERSONALITY ===
        print("\n[RESPONSE] Generating explanation...")
        explanation = explain_results(result, query_plan=plan, original_question=processing_query)

        # Modify explanation if no results found
        if no_results and explanation:
            # Add context about why there might be no results
            no_data_hint = app_state.personality.handle_error('empty_result',
                "I found no data matching your query. Try adjusting your filters or check if the data exists for that time period.")
            explanation = f"{explanation}\n\n{no_data_hint}"

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

        # === TRANSLATION (POST-PROCESS) ===
        if is_tamil:
            print("  → Translating response to Tamil...")
            explanation = translate_to_tamil(explanation)
            print("  ✓ Response translated")

        # === UPDATE CONTEXT ===
        turn = QueryTurn(
            question=question,
            resolved_question=processing_query,
            entities=entities,
            table_used=plan.get('table', best_table or ''),
            filters_applied=plan.get('filters', []) + plan.get('subset_filters', []),
            result_summary=f"{len(result)} rows returned" if result is not None else "No data",
            sql_executed=final_sql if 'final_sql' in dir() else None,
            was_followup=is_followup,
            confidence=confidence
        )
        ctx.add_turn(turn)

        # === BUILD RESPONSE ===
        print("\n[SUCCESS] Query completed successfully!")
        print(f"  Table: {plan.get('table', best_table)}")
        print(f"  Rows: {row_count}")
        print(f"  Confidence: {confidence:.0%}")
        print("=" * 60 + "\n")

        data_list = None
        if result is not None and hasattr(result, 'to_dict'):
            data_list = result.to_dict('records')

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

        # === CACHE RESULT (CACHING FLOW FROM ARCHITECTURE) ===
        # Store for 5 minutes (configurable via settings.yaml)
        try:
            cache_query_result(
                processing_query,
                spreadsheet_id,
                response,
                table_name=plan.get('table', best_table),
                filters=plan.get('filters', [])
            )
            print(f"[Cache] Stored result for: {processing_query[:50]}...")
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
        print(f"\n[ERROR] Unexpected exception:")
        print(f"  {str(e)}")
        import traceback
        traceback.print_exc()
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
        else:
            # Truly generic error - provide actionable message
            error_msg = app_state.personality.handle_error('general',
                "Something went wrong. Try rephrasing your question or check if the data is loaded.")

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
