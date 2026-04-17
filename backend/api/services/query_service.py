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

# CRITICAL: Force UTF-8 encoding for stdout/stderr
# This prevents UnicodeEncodeError when printing non-ASCII characters (emojis, Tamil, etc.)
import sys
import io
import os
import builtins

os.environ['PYTHONIOENCODING'] = 'utf-8'
os.environ['PYTHONLEGACYWINDOWSSTDIO'] = '0'

# Create a safe print function if not already defined
if not hasattr(builtins, '_original_print'):
    builtins._original_print = builtins.print
    def _safe_print(*args, **kwargs):
        """Print function that handles Unicode encoding errors gracefully."""
        try:
            safe_args = []
            for arg in args:
                if isinstance(arg, str):
                    safe_args.append(arg.encode('utf-8', errors='replace').decode('utf-8'))
                else:
                    safe_args.append(arg)
            builtins._original_print(*safe_args, **kwargs)
        except UnicodeEncodeError:
            try:
                safe_args = [str(arg).encode('ascii', errors='replace').decode('ascii') for arg in args]
                builtins._original_print(*safe_args, **kwargs)
            except Exception:
                pass
        except Exception:
            pass
    builtins.print = _safe_print

def _setup_utf8_output():
    """Wrap stdout/stderr with UTF-8 encoding."""
    try:
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        elif hasattr(sys.stdout, 'buffer'):
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)
    except Exception:
        pass
    try:
        if hasattr(sys.stderr, 'reconfigure'):
            sys.stderr.reconfigure(encoding='utf-8', errors='replace')
        elif hasattr(sys.stderr, 'buffer'):
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace', line_buffering=True)
    except Exception:
        pass

_setup_utf8_output()

from pathlib import Path
import re
import time
import traceback
import copy
from typing import Dict, Any, Optional, List
from concurrent.futures import ThreadPoolExecutor, as_completed

import numpy as np

# Add project root to Python path (api/services/ -> api/ -> backend/)
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from utils.logger import get_logger
from utils.config_loader import get_config, get_routing_config

# Import split service modules
from api.services.app_state import app_state
from api.services.query_utils import (
    _extract_metric_name_from_result, _humanize_metric,
    _resolve_top_references, _extract_result_values, _sanitize_for_json
)
from api.services.dataset_service import (
    extract_spreadsheet_id, load_dataset_service,
    load_dataset_from_source, sync_drive_folder,
    check_and_refresh_data
)
from api.services.projection_service import _handle_projection
from api.services.correction_service import (
    _handle_correction, _handle_pending_correction_response,
    _generate_clarification_message
)
from api.services.query_executor import _execute_with_forced_table

# Direct imports still needed by orchestrator
from planning_layer.table_router import RoutingResult
from planning_layer.entity_extractor import EntityExtractor
from planning_layer.planner_client import generate_plan
from validation_layer.plan_validator import validate_plan
from execution_layer.executor import execute_plan
from execution_layer.query_healer import QueryExecutionError
from execution_layer.sql_compiler import compile_sql
from explanation_layer.explainer_client import explain_results, generate_off_topic_response
from utils.translation import translate_to_english, translate_to_tamil
from utils.voice_utils import transcribe_audio
from utils.memory_detector import detect_memory_intent
from utils.permanent_memory import update_memory
from utils.onboarding import get_user_name
from utils.greeting_detector import (
    is_greeting, detect_schema_inquiry,
    is_date_context_statement, get_date_context_response
)
from utils.visualization import determine_visualization
from utils.query_context import QueryTurn, PendingCorrection

logger = get_logger("services")

def process_query_service(question: str, conversation_id: str = None, user_name: str = None) -> Dict[str, Any]:
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

    Args:
        question: User query text
        conversation_id: Optional conversation ID for context tracking
        user_name: Session-based name for "Call me X" feature (passed from frontend)
    """
    import time as _time
    _query_start = _time.time()
    _timings = {}

    def _log_timing(step_name: str, step_start: float):
        """Log timing for a step and update cumulative total."""
        elapsed = (_time.time() - step_start) * 1000
        cumulative = (_time.time() - _query_start) * 1000
        _timings[step_name] = elapsed
        logger.debug(f"  [TIME]  {step_name}: {elapsed:.0f}ms (total: {cumulative:.0f}ms)")

    try:
        # === FLOW LOGGING START ===
        logger.debug("\n" + "=" * 60)
        logger.debug(f"[QUERY] New query received: \"{question[:80]}{'...' if len(question) > 80 else ''}\"")
        logger.debug("=" * 60)

        # Initialize components
        _step_start = _time.time()
        logger.info("\n[STEP 0/8] INITIALIZING...")
        app_state.initialize()
        logger.info("  [OK] App state initialized")
        _log_timing("initialization", _step_start)

        # Get conversation context FIRST (needed for clarification check)
        ctx = app_state.conversation_manager.get_context(conversation_id)
        logger.info(f"  [OK] Context loaded (conversation: {conversation_id or 'default'})")

        # Apply session-based name if provided from frontend
        if user_name:
            app_state.personality.set_name(user_name)
            ctx.set_user_name(user_name)
            logger.info(f"  [OK] Session name applied: {user_name}")

        # Sync name from personality to context (in case context was reset)
        # This fixes the bug where name is forgotten after 2 questions
        if app_state.personality.user_name and not ctx.user_name:
            ctx.set_user_name(app_state.personality.user_name)
            logger.debug(f"  [Name] Synced from personality: {app_state.personality.user_name}")

        # Set default name to "Boss" if no name is provided
        if not ctx.user_name and not app_state.personality.user_name:
            app_state.personality.set_name("Boss")
            ctx.set_user_name("Boss")
            logger.debug(f"  [Name] Using default name: Boss")

        # === VALIDATE INPUT ===
        # Reject empty, too short, or obvious noise (transcription artifacts)
        # BUT: Allow short inputs (like "1", "2", "3") if there's a pending clarification
        question_clean = question.strip()
        has_pending = ctx.has_pending_clarification()

        if not question_clean:
            logger.error("  [FAIL] Empty input detected")
            logger.debug("=" * 60 + "\n")
            return {
                'success': False,
                'error': 'Empty or invalid input',
                'explanation': "I didn't catch that — the input was too short.",
                'error_type': 'invalid_input'
            }

        # Allow short inputs (1-2 chars) ONLY when clarification is pending OR it's a greeting
        # Short greetings like "Hi", "Hey", "Yo" should be allowed through
        short_greetings = ['hi', 'hey', 'yo', 'ok', 'no', 'yes', 'ya', 'na']
        is_short_greeting = question_clean.lower() in short_greetings

        if len(question_clean) < 3 and not has_pending and not is_short_greeting:
            logger.error("  [FAIL] Input too short (no pending clarification)")
            logger.debug("=" * 60 + "\n")
            return {
                'success': False,
                'error': 'Empty or invalid input',
                'explanation': "I didn't catch that — the input was too short.",
                'error_type': 'invalid_input'
            }


        # === NOISE DETECTION REMOVED ===
        # The transcription service (ElevenLabs Scribe) already filters noise
        # This check was causing false positives on legitimate typed queries
        # If transcription returns noise markers, they'll be in the text and user can retry
        
        # Log the query for debugging
        if len(question_clean) > 100:
            logger.info(f"  [INFO] Long query detected ({len(question_clean)} chars): {question_clean[:100]}...")
        else:
            logger.info(f"  [INFO] Query: {question_clean}")


        # === TABLE CLARIFICATION FEATURE REMOVED ===
        # Clear any stale pending clarification from before this change
        if ctx.has_pending_clarification():
            ctx.clear_pending_clarification()
            logger.info("  [OK] Cleared stale pending clarification (feature disabled)")

        # NOTE: Removed hardcoded "Freshggies" STT correction
        # The system should work with any business name via ProfileStore dynamic learning

        # === CHECK FOR PENDING CORRECTION CLARIFICATION ===
        if ctx.has_pending_correction_state():
            logger.info("\n[STEP 0.6a/9] CHECKING PENDING CORRECTION...")
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
                logger.error("  [FAIL] Could not match correction response, treating as new query")

        # === CHECK FOR CORRECTION INTENT ===
        # Only check if there's previous context to correct
        if ctx.turns:
            _step_start = _time.time()
            logger.info("\n[STEP 0.6b/9] CORRECTION INTENT DETECTION...")
            previous_turn = ctx.get_last_turn()
            correction_intent = app_state.correction_detector.detect(question, previous_turn)

            if correction_intent:
                logger.info(f"  [OK] Correction detected: {correction_intent.correction_type.value}")
                logger.debug(f"    Confidence: {correction_intent.confidence:.0%}")
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
                logger.error("  [FAIL] No correction intent detected")
            _log_timing("correction_detection", _step_start)

        # === RESOLVE TOP REFERENCES (NEW STEP 0.65) ===
        # Replace "top category", "best seller", etc. with actual values from previous results
        if ctx.turns:
            previous_turn = ctx.get_last_turn()
            resolved_question = _resolve_top_references(question, previous_turn)
            if resolved_question != question:
                logger.info(f"\n[STEP 0.65/9] TOP REFERENCE RESOLUTION...")
                logger.info(f"  [OK] Resolved: '{question[:50]}...' -> '{resolved_question[:50]}...'")
                question = resolved_question  # Use resolved question for rest of pipeline

        # === CHECK FOR PROJECTION INTENT (NEW STEP 0.7) ===
        if ctx.turns:
            _step_start = _time.time()
            logger.info("\n[STEP 0.7/9] PROJECTION INTENT DETECTION...")
            previous_turn = ctx.get_last_turn()

            from utils.projection_detector import detect_projection_intent
            projection_intent = detect_projection_intent(question, previous_turn)

            if projection_intent:
                logger.info(f"  [OK] Projection intent detected: {projection_intent.projection_type.value}")
                logger.debug(f"    Target period: {projection_intent.target_period}")
                logger.debug(f"    Confidence: {projection_intent.confidence:.0%}")
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
                    logger.debug(f"\n  [TIME]  TIMING SUMMARY (PROJECTION):")
                    for step, ms in _timings.items():
                        logger.debug(f"      {step}: {ms:.0f}ms")
                    logger.debug(f"      TOTAL: {_total_time:.0f}ms ({_total_time/1000:.2f}s)")
                    logger.debug("=" * 60 + "\n")
                    return projection_result
            else:
                logger.error("  [FAIL] No projection intent detected")
            _log_timing("projection_detection", _step_start)

        # === FAST PATH: Destructive Command Detection ===
        _destructive_patterns = [
            r'\b(delete|remove|drop|destroy|erase|truncate|wipe|clear)\b.*\b(records?|rows?|data|tables?|all|everything)\b',
            r'\b(records?|rows?|data|tables?|all|everything)\b.*\b(delete|remove|drop|destroy|erase|truncate|wipe|clear)\b',
        ]
        if any(re.search(p, question.lower()) for p in _destructive_patterns):
            logger.info("  [BLOCK] Destructive command detected - refusing")
            return {
                'success': True,
                'explanation': "I can only read and analyze data — I can't modify or delete anything. Your data is safe with me, Boss!",
                'data': None,
                'plan': None,
                'schema_context': [],
                'data_refreshed': False,
                'is_greeting': True,
            }

        # === FAST PATH: Obvious Greetings ===
        # Only catches clear-cut greetings (hi, hello, good morning, etc.)
        # Complex cases (Tanglish, off-topic, random Tamil) are handled by
        # routing — if no table matches, LLM responds naturally (Step 7).
        _step_start = _time.time()
        logger.info("\n[STEP 1/8] QUICK GREETING CHECK...")
        is_tamil_text = bool(re.search(r'[\u0B80-\u0BFF]', question))

        if is_greeting(question):
            logger.info(f"  [OK] Obvious greeting detected - generating LLM response")

            # Use LLM for ALL conversational responses (natural, not hardcoded)
            response = generate_off_topic_response(question, is_tamil=is_tamil_text)

            _log_timing("conversational_detection", _step_start)
            _total_time = (_time.time() - _query_start) * 1000
            logger.debug("  -> Returning LLM-generated conversational response")
            logger.debug(f"\n  [TIME]  TIMING SUMMARY (CONVERSATIONAL PATH):")
            for step, ms in _timings.items():
                logger.debug(f"      {step}: {ms:.0f}ms")
            logger.debug(f"      TOTAL: {_total_time:.0f}ms ({_total_time/1000:.2f}s)")
            logger.debug("=" * 60 + "\n")
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
        
        logger.error("  [FAIL] Not conversational (likely a data query)")
        _log_timing("conversational_detection", _step_start)

        # === FAST PATH: Date Context Detection (BEFORE Memory) ===
        _step_start = _time.time()
        logger.info("\n[STEP 1.8/8] DATE CONTEXT DETECTION...")
        is_date_ctx, date_info = is_date_context_statement(question)
        if is_date_ctx:
            logger.info(f"  [OK] Date context detected: {date_info}")
            # Store date context in conversation for subsequent queries
            if date_info:
                ctx.set_date_context(date_info)
            is_tamil = bool(re.search(r'[\u0B80-\u0BFF]', question))
            response = get_date_context_response(date_info, is_tamil=is_tamil)
            _log_timing("date_context", _step_start)
            logger.debug("  -> Returning date context acknowledgment")
            logger.debug("=" * 60 + "\n")
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
        logger.error("  [FAIL] Not a date context statement")
        _log_timing("date_context", _step_start)

        # === FAST PATH: Memory Intent ===
        _step_start = _time.time()
        logger.info("\n[STEP 2/8] MEMORY INTENT DETECTION...")
        memory_result = detect_memory_intent(question)
        if memory_result and memory_result.get("has_memory_intent"):
            logger.info(f"  [OK] Memory intent detected!")
            category = memory_result["category"]
            key = memory_result["key"]
            value = memory_result["value"]
            logger.debug(f"    Category: {category}, Key: {key}, Value: {value}")

            # Handle "Call me X" - SESSION ONLY (no persistent storage)
            if key == "address_as":
                app_state.personality.set_name(value)
                ctx.set_user_name(value)

                # NOTE: Name is stored in session only, NOT persisted across sessions
                # Each new session starts fresh with "Boss" as default
                logger.info(f"  [OK] Session name set to: {value} (session only, not persisted)")

                # CRITICAL: Invalidate cached LLM models so they pick up the new name
                from planning_layer.planner_client import invalidate_planner_model
                from explanation_layer.explainer_client import invalidate_explainer_model
                invalidate_planner_model()
                invalidate_explainer_model()
                logger.info("  [OK] LLM model caches invalidated")
                logger.debug("  -> Returning name confirmation (frontend will store in session)")
                logger.debug("=" * 60 + "\n")

                # Warm, conversational confirmations
                import random
                confirmations = [
                    f"Got it {value}! So what would you like to explore?",
                    f"Ohh okay {value}! What can I help you with?",
                    f"Alright {value}! Ready when you are.",
                    f"Sure thing {value}! What do you want to know?"
                ]
                explanation = random.choice(confirmations)

                return {
                    'success': True,
                    'explanation': explanation,
                    'data': None,
                    'plan': None,
                    'schema_context': [],
                    'data_refreshed': False,
                    'is_memory_storage': True,
                    'name_changed': True,  # Tell frontend to store in session
                    'new_name': value
                }

            # Handle other memory intents (bot identity, etc.) - keep permanent storage
            success = update_memory(category, key, value)
            if success:
                logger.info("  [OK] Memory saved successfully")
                logger.debug("  -> Returning memory confirmation")
                logger.debug("=" * 60 + "\n")

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
            logger.error("  [FAIL] No memory intent")
        _log_timing("memory_detection", _step_start)

        # === FAST PATH: Schema Inquiry ===
        _step_start = _time.time()
        # Handles questions like "what is sheet 1", "describe the data", "what tables do I have"
        # Uses template-based responses - NO LLM (prevents hallucination)
        logger.info("\n[STEP 3/8] SCHEMA INQUIRY DETECTION...")
        schema_intent = detect_schema_inquiry(question)
        if schema_intent:
            logger.info(f"  [OK] Schema inquiry detected: {schema_intent}")
            table_ref = schema_intent.get('table')
            is_detailed = schema_intent.get('detailed', False)

            # All schema inquiries use template responses (no redirect to routing).
            # Routing picks ONE table → narrow/misleading answers for meta questions.
            # Templates have random openers + thinking delay for natural feel.

        if schema_intent:
            # Get user language preference
            is_tamil = bool(re.search(r'[\u0B80-\u0BFF]', question))
            language = 'ta' if is_tamil else 'en'

            # Generate response from profile store (template-based, no LLM)
            # Each question type gets a DISTINCT response — not the same summary
            if app_state.profile_store:
                q_lower = question.lower()
                is_quality_question = any(kw in q_lower for kw in [
                    'quality', 'completeness', 'integrity', 'health',
                    'how good', 'how complete', 'how reliable',
                    'data look', 'data like', 'reliable',
                ])
                is_structure_question = any(kw in q_lower for kw in [
                    'structure', 'columns', 'fields', 'schema',
                    'describe', 'organized', 'layout',
                ])
                is_interesting_question = any(kw in q_lower for kw in [
                    'interesting', 'unusual', 'notable', 'stands out',
                    'stand out', 'catch your eye', 'highlight',
                ])
                is_capabilities_question = any(kw in q_lower for kw in [
                    'what kind of analysis', 'what can i do', 'what can i ask',
                    'what insights', 'what analysis', 'capabilities',
                    'what queries', 'what questions',
                ])

                if is_quality_question:
                    response = app_state.profile_store.format_quality_report(
                        language=language
                    )
                elif is_detailed and table_ref:
                    response = app_state.profile_store.format_detailed_profile(
                        table_name=table_ref,
                        language=language
                    )
                elif is_structure_question and not table_ref:
                    response = app_state.profile_store.format_structure_description(
                        language=language
                    )
                elif is_interesting_question:
                    response = _generate_data_insights(language=language)
                elif is_capabilities_question:
                    response = app_state.profile_store.format_analysis_capabilities(
                        language=language
                    )
                else:
                    # General overview — real data insights for broad questions
                    response = _generate_data_insights(language=language)
            else:
                response = "No data loaded yet. Please connect a dataset first."

            # Personalize — all schema responses are already conversational,
            # just prepend name naturally
            user_name = get_user_name()
            if user_name and user_name.lower() not in ["there", "user", "friend", ""]:
                response = f"{user_name}, {response[0].lower()}{response[1:]}"

            # Small delay so response feels natural (not instant template)
            import random as _rand
            _time.sleep(_rand.uniform(0.3, 0.7))

            logger.debug("  -> Returning schema info response")
            _log_timing("schema_inquiry", _step_start)
            logger.debug("=" * 60 + "\n")
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
            logger.error("  [FAIL] Not a schema inquiry")

            # === SAFETY NET: Meta-question fallback ===
            # Catches meta/overview questions that regex missed
            q_lower = question.lower()
            meta_keywords = [
                'quality', 'completeness', 'integrity', 'health', 'reliability',
                'how good', 'how complete', 'how reliable',
                'data look', 'data like', 'data structure',
                'overview', 'give me an overview', 'give me a summary',
                'about my data', 'about the data', 'about this data',
                'about my dataset', 'about my tables', 'about the dataset',
                'what does this dataset', 'what does the data',
                'describe the data', 'explain the data',
                'describe the structure', 'structure of my',
                'summarize', 'summarise', 'recap',
                'anything interesting', 'anything unusual', 'anything notable',
                'something interesting', 'something unusual', 'something useful',
                'what insights', 'what can i do', 'what can i ask',
                'what kind of analysis', 'what do you know',
                'what you know', 'know about my',
            ]
            # Use word-boundary matching to prevent "sum" matching "summarize"
            data_action_patterns = [
                # Aggregation/analysis actions
                r'\btotal\b', r'\bsum\b', r'\baverage\b', r'\bcount\b',
                r'\bhow many\b', r'\bcompare\b', r'\btrend\b',
                r'\btop\b', r'\bbottom\b', r'\bhighest\b', r'\blowest\b',
                # Time-specific filters (any dataset)
                r'\blast month\b', r'\bthis month\b', r'\blast year\b',
                r'\bjanuary\b', r'\bfebruary\b', r'\bmarch\b', r'\bapril\b',
                r'\bjune\b', r'\bjuly\b', r'\baugust\b', r'\bseptember\b',
                r'\boctober\b', r'\bnovember\b', r'\bdecember\b',
                # Generic business terms (universal, not dataset-specific)
                r'\bcost\b', r'\bexpenses?\b', r'\bpayment\b',
                r'\bbranch\b', r'\bcategory\b', r'\bsku\b',
                r'\bquarterly\b', r'\bmonthly\b', r'\bdaily\b',
                # Raw data / transaction queries
                r'\btransactions?\b', r'\braw\b', r'\bentries\b',
                r'\bproducts?\b', r'\bitems?\b',
                r'\bindividual\b', r'\bday[- ]by[- ]day\b',
            ]
            has_meta = any(kw in q_lower for kw in meta_keywords)
            has_data_action = any(re.search(p, q_lower) for p in data_action_patterns)

            if has_meta and not has_data_action and app_state.profile_store:
                logger.info("  [OK] Meta-question fallback triggered")
                is_tamil = bool(re.search(r'[\u0B80-\u0BFF]', question))
                language = 'ta' if is_tamil else 'en'

                is_quality_q = any(kw in q_lower for kw in [
                    'quality', 'completeness', 'integrity', 'health',
                    'how good', 'how complete', 'how reliable',
                    'data look', 'data like', 'reliable',
                ])
                is_structure_q = any(kw in q_lower for kw in [
                    'structure', 'columns', 'describe', 'organized',
                ])
                is_interesting_q = any(kw in q_lower for kw in [
                    'interesting', 'unusual', 'notable', 'stands out',
                ])
                is_capabilities_q = any(kw in q_lower for kw in [
                    'what kind of analysis', 'what can i do', 'what can i ask',
                    'what insights', 'what analysis', 'capabilities',
                ])

                if is_quality_q:
                    response = app_state.profile_store.format_quality_report(language=language)
                elif is_structure_q:
                    response = app_state.profile_store.format_structure_description(language=language)
                elif is_interesting_q:
                    response = _generate_data_insights(language=language)
                elif is_capabilities_q:
                    response = app_state.profile_store.format_analysis_capabilities(language=language)
                else:
                    response = _generate_data_insights(language=language)

                user_name = get_user_name()
                if user_name and user_name.lower() not in ["there", "user", "friend", ""]:
                    response = f"{user_name}, {response[0].lower()}{response[1:]}"

                # Small delay so response feels natural
                import random as _rand
                _time.sleep(_rand.uniform(0.3, 0.7))

                _log_timing("schema_inquiry", _step_start)
                return {
                    'success': True,
                    'explanation': response,
                    'data': None,
                    'plan': None,
                    'schema_context': [],
                    'data_refreshed': False,
                    'is_schema_inquiry': True
                }

        _log_timing("schema_inquiry", _step_start)

        # Initialize processing_query before any transformations
        processing_query = question

        # === SAFETY NET: Single-word metric queries ===
        # "revenue" alone should generate a SUM query, not fail
        words = processing_query.strip().split()
        if len(words) == 1 and app_state.profile_store:
            single_word = words[0].lower()
            # Check if this word matches any column name across all tables
            all_profiles = app_state.profile_store.get_all_profiles()
            for table_name, profile in all_profiles.items():
                columns = profile.get('columns', {})
                for col_name, col_info in columns.items():
                    if single_word in col_name.lower() or col_name.lower() in single_word:
                        # Found a matching column - auto-generate a summary
                        semantic_type = col_info.get('semantic_type', '')
                        if semantic_type in ('metric', 'currency', 'numeric', 'percentage') or col_info.get('dtype') in ('DOUBLE', 'BIGINT', 'INTEGER', 'FLOAT'):
                            logger.info(f"  [OK] Single-word '{single_word}' matched column '{col_name}' in {table_name} - generating summary")
                            response = f"Here's a summary of {col_name} from {table_name}."
                            # Don't return early - let it proceed through the normal pipeline
                            # Just expand the query to be more specific
                            processing_query = f"show total {col_name} from {table_name}"
                            question = processing_query
                            logger.info(f"  -> Expanded to: {processing_query}")
                            break
                else:
                    continue
                break

        # === EARLY CACHE CHECK (BEFORE TRANSLATION - SAVES 300-600ms) ===
        _step_start = _time.time()
        logger.info("\n[STEP 3.5/8] EARLY CACHE CHECK...")

        # Get spreadsheet_id for cache lookup
        spreadsheet_id = app_state.current_spreadsheet_id
        if not spreadsheet_id:
            try:
                config = get_config()
                spreadsheet_id = config.google_sheets.spreadsheet_id
                if spreadsheet_id:
                    app_state.current_spreadsheet_id = spreadsheet_id
            except (AttributeError, KeyError, FileNotFoundError):
                spreadsheet_id = ""

        # === PARALLEL: TRANSLATION + ENTITY EXTRACTION (SAVES 200-400ms) ===
        _step_start = _time.time()
        logger.info("\n[STEP 4-5/8] PARALLEL: TRANSLATION + ENTITY EXTRACTION...")

        processing_query = question
        is_tamil = bool(re.search(r'[\u0B80-\u0BFF]', question))
        entities = {}

        if is_tamil:
            logger.info(f"  [OK] Tamil detected - running translation + entity extraction in parallel")
            logger.debug(f"    Original: {question[:50]}...")
            ctx.set_language('ta')

            # Run translation and entity extraction in parallel
            with ThreadPoolExecutor(max_workers=2) as executor:
                # Submit both tasks
                future_translation = executor.submit(translate_to_english, question)
                future_entities = executor.submit(app_state.entity_extractor.extract, question)

                # Get results
                try:
                    processing_query = future_translation.result(timeout=10)
                    logger.info(f"    Translated: {processing_query[:50]}...")
                except Exception as e:
                    logger.error(f"  ! Translation failed: {e}, using original")
                    processing_query = question

                try:
                    entities = future_entities.result(timeout=5)
                except Exception as e:
                    logger.error(f"  ! Entity extraction failed: {e}")
                    entities = {}

            # Re-extract entities from translated text for better accuracy
            if processing_query != question:
                translated_entities = app_state.entity_extractor.extract(processing_query)
                # Merge: prefer translated entities but keep Tamil-detected ones
                for key, value in translated_entities.items():
                    if value and (not entities.get(key) or key in ['time_period', 'locations', 'categories']):
                        entities[key] = value
        else:
            logger.error("  [FAIL] No translation needed (English) - extracting entities")
            entities = app_state.entity_extractor.extract(processing_query)

        entity_summary = app_state.entity_extractor.get_entities_summary(entities)
        logger.info(f"  [OK] Entities extracted: {entity_summary}")
        # DEBUG: Specifically log time_period for date validation tracking
        logger.debug(f"  [DEBUG] time_period entity: '{entities.get('time_period', 'NOT SET')}'")
        logger.debug(f"  [DEBUG] All date-related entities: time_period={entities.get('time_period')}, month={entities.get('month')}, date_specific={entities.get('date_specific')}")

        # Check for follow-up
        is_followup = ctx.is_followup(processing_query)
        if is_followup:
            logger.info(f"  [OK] Follow-up question detected")
            entities = ctx.merge_entities(entities)
            logger.info(f"  [OK] Merged with context: {app_state.entity_extractor.get_entities_summary(entities)}")
        else:
            logger.error("  [FAIL] Not a follow-up (new query)")

        _log_timing("parallel_translation_entities", _step_start)

        # === CHECK FOR DATA CHANGES (INVALIDATE STALE CACHE) ===
        _step_start = _time.time()
        logger.info("\n[STEP 6/8] CACHE & DATA CHECK...")
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

        # === CHECK DATA LOADED ===
        profiles = app_state.profile_store.get_all_profiles() if app_state.profile_store else {}
        logger.info(f"  [OK] {len(profiles)} table profiles loaded")
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
        logger.info("\n[STEP 7/8] TABLE ROUTING & PLANNING...")
        # This is the CORE FIX - no more top_k=50 schema dump!
        previous_context = {
            'entities': ctx.active_entities,
            'table': ctx.active_table
        } if is_followup else None

        # Domain switching detection for follow-ups
        if is_followup:
            domain_switch_keywords = {
                'attendance': ['attendance', 'present', 'absent', 'leave', 'check_in', 'check_out'],
                'sales': ['sales', 'revenue', 'profit', 'transaction', 'branch'],
                'payroll': ['payroll', 'salary', 'bonus', 'deduction', 'net'],
            }
            for domain, keywords in domain_switch_keywords.items():
                if any(kw in processing_query.lower() for kw in keywords):
                    # Check if previous table was in a different domain
                    prev_table = (ctx.active_table or '').lower()
                    if domain not in prev_table:
                        logger.info(f"  [OK] Domain switch detected: {prev_table} -> {domain}")
                        previous_context = None  # Clear context to force re-routing
                        break

        routing_result = app_state.table_router.route(processing_query, previous_context)

        # Unpack routing result
        best_table = routing_result.table
        routing_entities = routing_result.entities
        confidence = routing_result.confidence

        logger.info(f"  [OK] Router result: {best_table} (confidence: {confidence:.0%})")
        _log_timing("table_routing", _step_start)

        # === CONVERSATIONAL: LLM router determined this isn't a data query ===
        # The LLM router (primary) returns table=None, confidence=0.0 for conversational
        # queries. The scoring fallback also caps confidence at 0.10 when no data intent.
        # Both paths converge here.
        rc = get_routing_config()
        has_data_intent = bool(
            entities.get('month') or entities.get('metric') or
            entities.get('comparison') or entities.get('time_period') or
            entities.get('explicit_table') or entities.get('dimension_keywords') or
            entities.get('trend_intent') or entities.get('summary_intent') or
            entities.get('cross_table_intent')
        )

        if routing_result.table is None and confidence == 0.0:
            logger.info("  [CONVERSATIONAL] Router returned no table — sending to LLM for conversational response")
            response = generate_off_topic_response(processing_query, is_tamil=is_tamil)

            # Translate if needed
            if is_tamil and not bool(re.search(r'[\u0B80-\u0BFF]', response)):
                response = translate_to_tamil(response)

            _log_timing("conversational_llm_fallback", _step_start)
            _total_time = (_time.time() - _query_start) * 1000
            logger.debug(f"\n  [TIME]  TIMING SUMMARY (ROUTING → CONVERSATIONAL):")
            for step, ms in _timings.items():
                logger.debug(f"      {step}: {ms:.0f}ms")
            logger.debug(f"      TOTAL: {_total_time:.0f}ms ({_total_time/1000:.2f}s)")
            logger.debug("=" * 60 + "\n")
            return {
                'success': True,
                'explanation': response,
                'data': None,
                'plan': None,
                'schema_context': [],
                'data_refreshed': False,
                'is_greeting': True,
                'is_conversational': True,
            }

        # Safety net for scoring fallback path: if scoring returned a table
        # but entities show no data intent and confidence is very low, go conversational
        if not has_data_intent and confidence < rc.confidence_threshold_low:
            logger.info("  [CONVERSATIONAL] Safety net: scoring fallback has no data intent "
                        f"(conf={confidence:.0%}) — sending to LLM")
            response = generate_off_topic_response(processing_query, is_tamil=is_tamil)
            if is_tamil and not bool(re.search(r'[\u0B80-\u0BFF]', response)):
                response = translate_to_tamil(response)
            _log_timing("conversational_safety_net", _step_start)
            _total_time = (_time.time() - _query_start) * 1000
            logger.debug(f"\n  [TIME]  TIMING SUMMARY (ROUTING → CONVERSATIONAL SAFETY NET):")
            for step, ms in _timings.items():
                logger.debug(f"      {step}: {ms:.0f}ms")
            logger.debug(f"      TOTAL: {_total_time:.0f}ms ({_total_time/1000:.2f}s)")
            logger.debug("=" * 60 + "\n")
            return {
                'success': True,
                'explanation': response,
                'data': None,
                'plan': None,
                'schema_context': [],
                'data_refreshed': False,
                'is_greeting': True,
                'is_conversational': True,
            }

        # For low confidence, log a warning (but still try execution since data intent was detected)
        if confidence < 0.25:
            logger.info(f"  ! Low confidence ({confidence:.0%}) — proceeding with best candidate")

        # === TABLE CLARIFICATION DISABLED ===
        # Instead of asking "Which table?", just pick the best candidate automatically.
        # User can correct via "check from X table" if wrong.
        if routing_result.needs_clarification:
            logger.info(f"  ! AMBIGUITY DETECTED - auto-selecting best candidate (clarification disabled)")
            candidates = routing_result.get_clarification_options()
            if candidates:
                best_table = candidates[0]  # Pick first (best scored) candidate
                logger.debug(f"  -> Auto-selected table: {best_table}")

        # === SCHEMA CONTEXT GENERATION ===
        if best_table and routing_result.is_confident:
            # High confidence - use single table schema
            schema_context = app_state.table_router.get_table_schema(best_table)
            logger.info(f"  [OK] Using focused schema for: {best_table}")
        elif routing_result.should_fallback:
            # Very low confidence - try INTELLIGENT LLM FALLBACK first!
            logger.debug(f"  ! Very low confidence - trying LLM-based intelligent table selection...")
            llm_suggested_table = app_state.table_router.get_llm_fallback_table(processing_query)

            if llm_suggested_table:
                # LLM successfully picked a table - use it!
                schema_context = app_state.table_router.get_table_schema(llm_suggested_table)
                best_table = llm_suggested_table  # Update best_table for execution
                logger.info(f"  [OK] LLM Fallback SUCCESS - using: {llm_suggested_table}")
            else:
                # LLM couldn't pick - fall back to top 5 candidates
                schema_context = app_state.table_router.get_fallback_schema(processing_query, top_k=5)
                logger.error(f"  ! LLM Fallback failed - using top 5 candidates")
        else:
            # Medium confidence - use the best match
            schema_context = app_state.table_router.get_table_schema(best_table)
            logger.info(f"  [OK] Using best match schema for: {best_table} (medium confidence)")

        # Add previous context to schema if follow-up
        if is_followup:
            context_prompt = ctx.get_context_prompt()
            if context_prompt:
                schema_context = f"{context_prompt}\n\n---\n\n{schema_context}"

        # === CRITICAL: PRE-VALIDATE DATE FOR "TODAY/YESTERDAY" QUERIES ===
        # Check BEFORE planning to avoid hallucination with wrong data
        time_period = (entities.get('time_period') or '').lower() if entities else ''

        # FALLBACK: Also check raw question for today/yesterday keywords (belt and suspenders)
        query_lower = processing_query.lower()
        if not time_period:
            if 'today' in query_lower or "today's" in query_lower:
                time_period = 'today'
                logger.info(f"  [DEBUG] Detected 'today' from query text (entity extraction missed it)")
            elif 'yesterday' in query_lower or "yesterday's" in query_lower:
                time_period = 'yesterday'
                logger.info(f"  [DEBUG] Detected 'yesterday' from query text (entity extraction missed it)")

        logger.debug(f"  [DEBUG] Date validation check: time_period='{time_period}', entities keys={list(entities.keys()) if entities else 'None'}")
        if time_period in ['today', 'yesterday', 'this_week', 'last_week'] and best_table:
            from datetime import datetime, timedelta
            from schema_intelligence.profile_store import ProfileStore

            try:
                # Use app_state's profile_store if available, else create new one
                profile_store = app_state.profile_store if app_state.profile_store else ProfileStore()
                profile = profile_store.get_profile(best_table)
                logger.debug(f"  [DEBUG] Profile for {best_table}: date_range={profile.get('date_range') if profile else 'No profile'}")
                if not profile:
                    # Try case-insensitive lookup
                    all_tables = profile_store.get_table_names()
                    logger.debug(f"  [DEBUG] Available tables in profile_store: {all_tables}")
                    for t in all_tables:
                        if t.lower() == best_table.lower():
                            profile = profile_store.get_profile(t)
                            logger.info(f"  [DEBUG] Found profile via case-insensitive match: {t}")
                            break

                if profile and profile.get('date_range'):
                    date_range = profile['date_range']
                    # CRITICAL: Properly handle None values - don't convert None to 'None' string
                    raw_min = date_range.get('min')
                    raw_max = date_range.get('max')
                    min_date = str(raw_min)[:10] if raw_min is not None else None
                    max_date = str(raw_max)[:10] if raw_max is not None else None
                    logger.debug(f"  [DEBUG] Date range: min={min_date}, max={max_date} (raw: {raw_min}, {raw_max})")

                    # Calculate the requested date
                    now = datetime.now()
                    if time_period == 'today':
                        requested_date = now.strftime('%Y-%m-%d')
                        date_label = f"Today ({requested_date})"
                    elif time_period == 'yesterday':
                        requested_date = (now - timedelta(days=1)).strftime('%Y-%m-%d')
                        date_label = f"Yesterday ({requested_date})"
                    else:
                        requested_date = now.strftime('%Y-%m-%d')
                        date_label = time_period.replace('_', ' ').title()

                    logger.debug(f"  [DEBUG] Requested date: {requested_date}, label: {date_label}")

                    # Check if requested date is outside the data range
                    # Only validate if we have valid date range (not None)
                    if min_date and max_date and min_date != 'None' and max_date != 'None':
                        if requested_date < min_date or requested_date > max_date:
                            error_msg = f"Boss, {date_label} is outside the available data range. The dataset only has data from {min_date} to {max_date}. Try asking about a date within that range!"
                            logger.error(f"  [WARN] DATE VALIDATION FAILED: {error_msg}")

                            _total_time = (_time.time() - _query_start) * 1000
                            logger.debug(f"\n  [TIME]  TIMING SUMMARY (DATE OUT OF RANGE):")
                            for step, ms in _timings.items():
                                logger.debug(f"      {step}: {ms:.0f}ms")
                            logger.debug(f"      TOTAL: {_total_time:.0f}ms ({_total_time/1000:.2f}s)")
                            logger.debug("=" * 60 + "\n")

                            return {
                                'success': True,
                                'explanation': error_msg,
                                'data': None,
                                'plan': None,
                                'table_used': best_table,
                                'date_out_of_range': True,
                                'available_range': {'min': min_date, 'max': max_date},
                                'requested_date': requested_date
                            }
                        else:
                            logger.debug(f"  [DEBUG] Date {requested_date} is within range [{min_date} to {max_date}]")
                    else:
                        logger.warning(f"  [DEBUG] Skipping date validation - no valid date range (min={min_date}, max={max_date})")
                else:
                    logger.debug(f"  [DEBUG] No date_range in profile for {best_table}")
            except Exception as e:
                logger.warning(f"  [WARN] Could not validate date range: {e}")
                import traceback
                traceback.print_exc()

        # === PLANNING ===
        _step_start = _time.time()
        logger.debug("  -> Generating query plan via LLM...")
        plan = generate_plan(processing_query, schema_context, entities=entities)
        validate_plan(plan)
        _log_timing("llm_planning", _step_start)
        logger.info(f"  [OK] Plan generated:")
        logger.debug(f"    Query type: {plan.get('query_type', 'unknown')}")
        logger.debug(f"    Table: {plan.get('table', 'unknown')}")
        logger.debug(f"    Metrics: {plan.get('metrics', [])}")
        logger.debug(f"    Filters: {plan.get('filters', [])}")

        # === EXECUTION WITH HEALING ===
        _step_start = _time.time()
        logger.info("\n[STEP 8/8] QUERY EXECUTION...")
        try:
            # Import at function level to avoid circular imports
            from execution_layer.executor import ADVANCED_QUERY_TYPES, MULTI_STEP_QUERY_TYPES
            
            query_type = plan.get('query_type')
            
            # Route multi-step queries to cross-table executor
            if query_type in MULTI_STEP_QUERY_TYPES or plan.get('steps') is not None:
                logger.info(f"  -> Executing multi-step query: {query_type}")
                from execution_layer.executor import execute_plan
                result = execute_plan(plan)
                final_sql = f"[Multi-step {query_type} query - see steps]"
                logger.info(f"  [OK] Multi-step query completed")
                
                # Attach multi-step metadata for explainer
                if hasattr(result, 'attrs'):
                    result.attrs['is_multi_step'] = True
            
            # Route advanced query types to specialized executor (comparison, percentage, trend)
            elif query_type in ADVANCED_QUERY_TYPES:
                logger.debug(f"  -> Executing advanced query type: {query_type}")
                from execution_layer.executor import execute_plan
                result = execute_plan(plan)
                final_sql = f"[Advanced {query_type} query - see analysis]"
                logger.info(f"  [OK] Advanced query completed")

                # CRITICAL: For projection support, merge analysis from result back into plan
                # Advanced queries return DataFrames with analysis in attrs
                # We need 'analysis' in plan for projection follow-ups
                if hasattr(result, 'attrs') and 'analysis' in result.attrs:
                    analysis = result.attrs['analysis']
                    plan['analysis'] = analysis if isinstance(analysis, dict) else {}
                    if plan['analysis']:
                        logger.debug(f"    -> Stored analysis in plan for projection: {list(plan['analysis'].keys())}")
                    else:
                        logger.debug(f"    ! Analysis was empty or invalid")
                elif isinstance(result, dict) and 'analysis' in result:
                    plan['analysis'] = result.get('analysis', {})
                    logger.debug(f"    -> Stored analysis in plan for projection support: {list(plan['analysis'].keys())}")
                else:
                    logger.info(f"    ! No analysis found in result (type: {type(result).__name__})")
            else:
                # Standard query execution with healing
                sql = compile_sql(plan)
                logger.info(f"  [OK] SQL compiled: {sql[:100]}{'...' if len(sql) > 100 else ''}")
                logger.debug("  -> Executing with self-healing...")
                result, final_sql = app_state.query_healer.execute_with_healing(sql, plan)

            # Track healing changes — surface to user so they know data was adjusted
            healing_history = app_state.query_healer.get_healing_history()
            healing_notes = []
            if healing_history:
                logger.info(f"  ! Applied {len(healing_history)} healing fix(es)")
                for attempt in healing_history:
                    if attempt.success:
                        healing_notes.append(attempt.fix_type)
                        logger.info(f"    Healing applied: {attempt.fix_type}")

        except QueryExecutionError as e:
            # All healing attempts failed
            logger.error(f"  [FAIL] EXECUTION FAILED after all healing attempts")
            logger.error(f"    Error: {str(e)[:100]}")
            logger.debug("=" * 60 + "\n")
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
        date_out_of_range_msg = None
        row_count = len(result) if result is not None and hasattr(result, '__len__') else 0
        if result is None or row_count == 0:
            no_results = True
            logger.debug(f"  ! Query returned 0 rows")

            # Check if this is a "today/yesterday" query with date outside data range
            time_period = (entities.get('time_period') or '').lower() if entities else ''
            # Fallback: check raw query for today/yesterday
            if not time_period:
                query_lower_check = processing_query.lower()
                if 'today' in query_lower_check:
                    time_period = 'today'
                elif 'yesterday' in query_lower_check:
                    time_period = 'yesterday'

            if time_period in ['today', 'yesterday', 'this_week', 'last_week']:
                from datetime import datetime, timedelta
                from schema_intelligence.profile_store import ProfileStore
                try:
                    profile_store = app_state.profile_store if app_state.profile_store else ProfileStore()
                    table_to_check = plan.get('table') or best_table
                    profile = profile_store.get_profile(table_to_check)
                    if profile and profile.get('date_range'):
                        date_range = profile['date_range']
                        # Properly handle None values
                        raw_min = date_range.get('min')
                        raw_max = date_range.get('max')
                        min_date = str(raw_min)[:10] if raw_min is not None else None
                        max_date = str(raw_max)[:10] if raw_max is not None else None

                        # Calculate correct date based on time_period
                        now = datetime.now()
                        if time_period == 'yesterday':
                            check_date = (now - timedelta(days=1)).strftime('%Y-%m-%d')
                            date_label = f"Yesterday ({check_date})"
                        else:
                            check_date = now.strftime('%Y-%m-%d')
                            date_label = f"Today ({check_date})"

                        if min_date and max_date and min_date != 'None' and max_date != 'None':
                            if check_date < min_date or check_date > max_date:
                                date_out_of_range_msg = f"{date_label} is outside the available data range ({min_date} to {max_date}). The dataset doesn't have data for {time_period}."
                                logger.warning(f"  [WARN] {date_out_of_range_msg}")
                except Exception as e:
                    logger.warning(f"  [WARN] Could not check date range: {e}")
        else:
            logger.info(f"  [OK] Query returned {row_count} rows")
        _log_timing("sql_execution", _step_start)

        # === EXPLANATION WITH PERSONALITY ===
        _step_start = _time.time()
        logger.debug("\n[RESPONSE] Generating explanation...")

        # If date is out of range, provide specific explanation
        if date_out_of_range_msg:
            explanation = f"Boss, {date_out_of_range_msg}"
        else:
            explanation = explain_results(
                result,
                query_plan=plan,
                original_question=processing_query,
                raw_user_message=question,  # Original message with emotional tone
                user_name=app_state.personality.user_name
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

        # Surface healing changes — append note if query was auto-corrected
        if healing_notes:
            heal_map = {
                'column_name_fix': 'adjusted column name',
                'type_cast_fix': 'adjusted data type',
                'table_name_fix': 'adjusted table name',
                'syntax_fix': 'fixed query syntax',
                'ambiguous_column_fix': 'resolved ambiguous column',
                'generic_fix': 'auto-corrected query',
            }
            fixes = [heal_map.get(h, h) for h in healing_notes]
            explanation += f"\n\n(Note: I {', '.join(fixes)} to get this result.)"

        _log_timing("llm_explanation", _step_start)

        # === TRANSLATION (POST-PROCESS) ===
        _step_start = _time.time()
        if is_tamil:
            logger.debug("  -> Translating response to Tamil...")
            explanation = translate_to_tamil(explanation)
            logger.info("  [OK] Response translated")
            _log_timing("translation_response", _step_start)
        else:
            _log_timing("translation_response", _step_start)

        # === UPDATE CONTEXT ===
        # Extract key result values for pronoun resolution in follow-ups
        # e.g., "that state" -> "West Bengal" from previous query result
        result_values = _extract_result_values(result, plan)
        if result_values:
            logger.info(f"  [OK] Extracted result values for context: {result_values}")

        # Make a deep copy of plan to preserve analysis for projection follow-ups
        # (reference passing could cause issues if plan is modified elsewhere)
        import copy
        stored_plan = copy.deepcopy(plan)

        # Debug: Verify analysis is in stored_plan
        if stored_plan.get('analysis'):
            logger.info(f"  [OK] Plan analysis preserved for projection: {list(stored_plan['analysis'].keys())}")

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
        logger.info("\n[SUCCESS] Query completed successfully!")
        logger.debug(f"  Table: {plan.get('table', best_table)}")
        logger.debug(f"  Rows: {row_count}")
        logger.debug(f"  Confidence: {confidence:.0%}")
        logger.debug(f"\n  [TIME]  TIMING SUMMARY:")
        for step, ms in _timings.items():
            logger.debug(f"      {step}: {ms:.0f}ms")
        logger.debug(f"      ────────────────────")
        logger.debug(f"      TOTAL: {_total_time:.0f}ms ({_total_time/1000:.2f}s)")
        logger.debug("=" * 60 + "\n")

        # Sanitize numpy types for JSON serialization
        data_list = None
        if result is not None and hasattr(result, 'to_dict'):
            # For aggregation queries, prefer underlying_rows for the data table
            # This shows WHAT was counted, not just the count
            if hasattr(result, 'attrs') and result.attrs.get('underlying_rows'):
                data_list = _sanitize_for_json(result.attrs['underlying_rows'])
                logger.debug(f"  [DATA] Using underlying rows for data table ({len(data_list)} rows)")
            else:
                data_list = _sanitize_for_json(result.to_dict('records'))

        # Determine visualization type based on query type and data
        # For visualization, use the aggregated result (not underlying rows)
        viz_data = None
        if result is not None and hasattr(result, 'to_dict'):
            viz_data = _sanitize_for_json(result.to_dict('records'))

        # NOTE: Removed len(data_list) > 1 gate to allow metric cards for single-value results
        visualization = None
        if viz_data:
            try:
                visualization = determine_visualization(plan, viz_data, entities)
            except Exception as viz_err:
                logger.warning(f"[Visualization] Warning: Could not determine visualization: {viz_err}")

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
            'no_results': no_results,  # Flag for empty result set
            'visualization': visualization,  # Chart config for visual analytics
            'healing_applied': healing_notes if healing_notes else None  # What the query healer changed
        }

        # Sanitize entire response to handle numpy types in plan, entities, etc.
        response = _sanitize_for_json(response)

        return response

    except ValueError as e:
        # Planning/validation errors (LLM response issues)
        error_str = str(e).lower()
        logger.error("\n[ERROR] ValueError in query processing:")
        logger.debug("  %s", e)

        # === FALLBACK 1: Try raw data from the routed table ===
        try:
            _routed_table = locals().get('best_table')
            if _routed_table:
                logger.info("[FALLBACK 1] Attempting raw data from table: %s", _routed_table)
                fallback_plan = {
                    "query_type": "list",
                    "table": _routed_table,
                    "select_columns": ["*"],
                    "limit": 20
                }
                fallback_df = execute_plan(fallback_plan)
                if fallback_df is not None and len(fallback_df) > 0:
                    data_list = fallback_df.head(20).to_dict(orient='records')
                    data_list = _sanitize_for_json(data_list)
                    explanation = app_state.personality.get_starter() + \
                        f" Here's the data from {_routed_table}. Try asking something more specific to dig deeper."
                    return {
                        'success': True,
                        'explanation': explanation,
                        'data': data_list,
                        'plan': fallback_plan,
                        'table_used': _routed_table,
                        'is_raw_fallback': True,
                    }
        except Exception as fb1_err:
            logger.debug("[FALLBACK 1] Failed: %s", fb1_err)

        # === FALLBACK 2: Gemini general LLM answer ===
        try:
            from utils.llm_fallback import gemini_general_fallback, get_schema_summary
            _routed = locals().get('best_table')
            _name = app_state.personality.get_name()
            schema_summary = get_schema_summary(app_state.profile_store)
            table_names = list(app_state.profile_store.get_all_profiles().keys())

            gemini_response = gemini_general_fallback(
                question=question,
                available_tables=table_names,
                schema_summary=schema_summary,
                user_name=_name,
                routed_table=_routed,
            )
            if gemini_response:
                logger.info("[FALLBACK 2] Gemini LLM provided general answer")
                return {
                    'success': True,
                    'explanation': gemini_response,
                    'data': None,
                    'table_used': None,
                    'is_llm_fallback': True,
                }
        except Exception as fb2_err:
            logger.debug("[FALLBACK 2] Gemini fallback failed: %s", fb2_err)

        # === FALLBACK 3: Personality-based error message ===
        if 'timeout' in error_str or 'timed out' in error_str:
            error_msg = app_state.personality.handle_error('general',
                "Request took too long. Please try again or simplify your question.")
        elif 'json' in error_str or 'parse' in error_str:
            error_msg = app_state.personality.handle_error('general',
                "I had trouble understanding how to answer that. A slight rephrase might help.")
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
        logger.error(f"\n[ERROR] ConnectionError:")
        logger.debug(f"  {e}")
        logger.debug("=" * 60 + "\n")
        error_msg = app_state.personality.handle_error('connection')
        return {
            'success': False,
            'error': str(e),
            'explanation': error_msg,
            'error_type': 'connection_error'
        }

    except TimeoutError as e:
        # Explicit timeout errors
        logger.error(f"\n[ERROR] TimeoutError:")
        logger.debug(f"  {e}")
        logger.debug("=" * 60 + "\n")
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
        logger.error(f"\n[ERROR] Unexpected exception:")
        logger.debug(f"  Type: {type(e).__name__}")
        logger.debug(f"  Message: {str(e)}")
        logger.error(f"  Traceback:\n{error_trace}")
        logger.debug("=" * 60 + "\n")

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


def _generate_data_insights(language: str = 'en') -> str:
    """
    Query actual data from DuckDB across multiple tables to find real patterns.
    Returns a conversational summary with real values — not just metadata.
    """
    import random
    from analytics_engine.duckdb_manager import DuckDBManager
    from utils.formatting import format_indian_number

    profiles = app_state.profile_store.get_all_profiles() if app_state.profile_store else {}
    if not profiles:
        return "No data loaded yet! Connect a dataset first."

    try:
        db = DuckDBManager()
    except Exception as e:
        logger.warning("Could not connect to DuckDB for insights: %s", e)
        # Fall back to metadata-only highlights
        return app_state.profile_store.format_data_highlights(language=language)

    insights = []

    # Sort tables by row count — focus on the top 5 most substantial tables
    sorted_tables = sorted(
        profiles.items(),
        key=lambda x: x[1].get('row_count', 0),
        reverse=True
    )[:5]

    def _clean_name(name: str) -> str:
        parts = name.split('_')
        for i, part in enumerate(parts):
            if part.lower() not in ('dataset', 'sales', 'data') and not part.isdigit():
                return '_'.join(parts[i:]).replace('_', ' ')
        return name.replace('_', ' ')

    for table_name, profile in sorted_tables:
        cols = profile.get('columns', {})
        metrics = [(c, info) for c, info in cols.items() if info.get('role') == 'metric']
        dimensions = [(c, info) for c, info in cols.items() if info.get('role') == 'dimension']
        clean = _clean_name(table_name)

        if not metrics:
            continue

        # Pick the primary metric (first one, usually the most important)
        primary_metric = metrics[0][0]

        # --- Insight 1: Overall aggregate for the primary metric ---
        try:
            agg_sql = f'SELECT SUM("{primary_metric}") as total, AVG("{primary_metric}") as avg, COUNT(*) as cnt FROM "{table_name}"'
            agg_result = db.query(agg_sql)
            if len(agg_result) > 0:
                total_val = agg_result.iloc[0]['total']
                avg_val = agg_result.iloc[0]['avg']
                row_cnt = int(agg_result.iloc[0]['cnt'])

                import math

                def _is_valid_number(val):
                    return val is not None and not (isinstance(val, float) and math.isnan(val))

                if _is_valid_number(total_val):
                    total_num = float(total_val)
                    metric_display = primary_metric.replace('_', ' ')
                    total_str = format_indian_number(total_num)

                    if _is_valid_number(avg_val):
                        avg_str = format_indian_number(float(avg_val))
                        insights.append(
                            f"In {clean}, total {metric_display} is {total_str}"
                            f" across {row_cnt:,} records (avg {avg_str} per record)."
                        )
                    else:
                        insights.append(
                            f"In {clean}, total {metric_display} is {total_str}"
                            f" across {row_cnt:,} records."
                        )
        except Exception as e:
            logger.debug("Aggregate query failed for %s.%s: %s", table_name, primary_metric, e)

        # --- Insight 2: Top dimension breakdown (if dimensions exist) ---
        if dimensions:
            primary_dim = dimensions[0][0]
            try:
                top_sql = (
                    f'SELECT "{primary_dim}", SUM("{primary_metric}") as total '
                    f'FROM "{table_name}" '
                    f'WHERE "{primary_dim}" IS NOT NULL '
                    f'GROUP BY "{primary_dim}" '
                    f'ORDER BY total DESC LIMIT 3'
                )
                top_result = db.query(top_sql)
                if len(top_result) >= 2:
                    dim_display = primary_dim.replace('_', ' ')
                    top_items = []
                    for _, row in top_result.iterrows():
                        dim_val = str(row[primary_dim])
                        metric_val = format_indian_number(float(row['total']))
                        top_items.append(f"{dim_val} ({metric_val})")

                    insights.append(
                        f"Top {dim_display} by {primary_metric.replace('_', ' ')}: "
                        + ", ".join(top_items) + "."
                    )
            except Exception as e:
                logger.debug("Top breakdown query failed for %s: %s", table_name, e)

        # Limit to 2 insights per table to keep response concise
        if len(insights) >= 6:
            break

    # --- Cross-table comparison (if multiple tables have same metric) ---
    if len(sorted_tables) >= 2:
        metric_totals = []
        for table_name, profile in sorted_tables[:5]:
            cols = profile.get('columns', {})
            metrics_list = [c for c, info in cols.items() if info.get('role') == 'metric']
            if metrics_list:
                primary = metrics_list[0]
                try:
                    result = db.query(f'SELECT SUM("{primary}") as total FROM "{table_name}"')
                    if len(result) > 0:
                        val = result.iloc[0]['total']
                        if val is not None and str(val) != 'nan':
                            metric_totals.append((_clean_name(table_name), primary, float(val)))
                except Exception:
                    pass

        if len(metric_totals) >= 2:
            # Find the table with the highest total
            metric_totals.sort(key=lambda x: x[2], reverse=True)
            top_table = metric_totals[0]
            insights.append(
                f"Across tables, {top_table[0]} has the highest {top_table[1].replace('_', ' ')} "
                f"at {format_indian_number(top_table[2])}."
            )

    # Build conversational response
    if language == 'ta':
        openers = [
            "Unga data la sila interesting patterns paathein!",
            "Data la drill down pannein — idho paathein!",
            "Actual numbers check pannein, sila useful findings!",
        ]
    else:
        openers = [
            "I dug into your actual data — here's what I found!",
            "After looking at the numbers, here's what stands out!",
            "I ran some queries across your tables — check this out!",
        ]

    response = random.choice(openers)
    if insights:
        response += " " + " ".join(insights)
    else:
        # Fallback if no numeric insights could be generated
        return app_state.profile_store.format_data_highlights(language=language)

    response += " I can break any of these down further."
    return response


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
    Called when user clears chat.
    """
    # Clear conversation context
    app_state.conversation_manager.clear_context(conversation_id)

    logger.debug(f"[CONTEXT] Cleared conversation context")

    return {
        'success': True,
        'message': 'Context cleared'
    }
