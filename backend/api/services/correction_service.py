"""Correction intent handling - table, filter, metric, negation, revert corrections."""
import re
import copy
import traceback
from typing import Dict, Any, Optional, List

from utils.logger import get_logger
from schema_intelligence.profile_store import ProfileStore
from api.services.app_state import app_state
from api.services.query_utils import _extract_metric_name_from_result, _humanize_metric, _extract_result_values, _sanitize_for_json
from api.services.query_executor import (
    _re_execute_with_table, _re_execute_with_entities,
    _re_execute_with_corrections, _re_execute_turn,
    _execute_with_forced_table, _execute_with_modified_plan
)
from planning_layer.planner_client import generate_plan
from validation_layer.plan_validator import validate_plan
from execution_layer.sql_compiler import compile_sql
from explanation_layer.explainer_client import explain_results
from utils.translation import translate_to_tamil

logger = get_logger("correction")

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
    logger.info("Table Correction Handler")

    # Get profile store for table lookups
    profile_store = app_state.profile_store

    # Case 1: Explicit table name mentioned
    if correction_intent.explicit_table:
        explicit_table = correction_intent.explicit_table
        logger.debug("Explicit table: %s", explicit_table)

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
            logger.warning("Table '%s' not found", explicit_table)
            # Try fuzzy match
            all_tables = profile_store.get_table_names() or []
            for table in all_tables:
                if explicit_table.lower() in table.lower():
                    logger.debug("Fuzzy match: %s", table)
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
        logger.info("Auto-selected table: %s", selected_table)
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
    logger.warning("No suitable alternative found, re-routing query")
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
                logger.debug("Detected keyword '%s' -> target type: %s", keyword, table_type)
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
        logger.debug("Previous type '%s' -> target opposite: %s", prev_type, target_type)

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
                logger.debug("Boosted %s (type=%s matches target)", table_name, table_type)

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
    logger.info("Filter Correction Handler")

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

        logger.debug("Correcting %s: %s -> %s", entity_key, old_value, new_value)
        # Store old value for question text replacement
        # If old_value not explicitly provided, get it from previous turn's entities
        if old_value:
            old_values[entity_key] = old_value
        elif previous_turn.entities and previous_turn.entities.get(entity_key):
            # Use the previous turn's entity value as old_value for text replacement
            old_values[entity_key] = previous_turn.entities[entity_key]
            logger.debug("Using previous entity as old_value: %s", old_values[entity_key])
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
    logger.info("Filter Removal Handler - Preserving Query Structure")

    # Get filters to remove
    filter_removals = correction_intent.filter_removals or []
    logger.debug("Filters to remove: %s", filter_removals)

    # Get the ORIGINAL query plan from previous turn
    original_plan = previous_turn.query_plan
    if not original_plan:
        logger.warning("No original query_plan found, falling back to re-execution")
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

    # Column classification for filter removal
    date_related_columns = ['date', 'month', 'year', 'time',
                           'created_at', 'updated_at', 'timestamp']
    location_related_columns = ['state', 'city', 'region', 'area', 'location',
                                'branch', 'district', 'zone']
    category_related_columns = ['category', 'type', 'product', 'segment', 'group']

    def _should_remove_filter(column: str, filter_removals: list) -> bool:
        """Check if a filter column matches any of the requested removals."""
        col_lower = column.lower()
        if any(fr in ['month', 'date', 'time', 'year'] for fr in filter_removals):
            if any(dc in col_lower for dc in date_related_columns):
                return True
        if 'location' in filter_removals:
            if any(lc in col_lower for lc in location_related_columns):
                return True
        if 'category' in filter_removals:
            if any(cc in col_lower for cc in category_related_columns):
                return True
        return False

    # Remove matching filters from subset_filters
    if 'subset_filters' in modified_plan and modified_plan['subset_filters']:
        original_filters = modified_plan['subset_filters']
        new_filters = []

        for f in original_filters:
            column = f.get('column', '')
            if _should_remove_filter(column, filter_removals):
                removed_filters.append(f"  {column} {f.get('operator')} {f.get('value')}")
                logger.debug("Removed filter: %s %s %s", column, f.get('operator'), f.get('value'))
            else:
                new_filters.append(f)

        modified_plan['subset_filters'] = new_filters
        logger.debug("Filters kept: %d, Removed: %d", len(new_filters), len(removed_filters))

    # Also remove from filters array if present
    if 'filters' in modified_plan and modified_plan['filters']:
        original_filters = modified_plan['filters']
        new_filters = []

        for f in original_filters:
            column = f.get('column', '')
            if _should_remove_filter(column, filter_removals):
                removed_filters.append(f"  {column} {f.get('operator')} {f.get('value')}")
                logger.debug("Removed filter from 'filters': %s", column)
            else:
                new_filters.append(f)

        modified_plan['filters'] = new_filters

    logger.debug("Query type preserved: %s", modified_plan.get('query_type'))
    logger.debug("Modified plan subset_filters: %s", modified_plan.get('subset_filters'))

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
        logger.info("Running with MODIFIED plan (preserving query structure)...")
        logger.debug("Table: %s", table)
        logger.debug("Query type: %s", modified_plan.get('query_type'))
        logger.debug("Original question: %s...", (original_question or '')[:80])

        # Step 1: Execute SQL with modified plan
        logger.info("Step 1/2: Executing query with modified plan...")
        query_type = modified_plan.get('query_type')

        if query_type in ADVANCED_QUERY_TYPES:
            logger.debug("Advanced query type: %s", query_type)
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
            logger.debug("SQL: %s...", sql[:150])
            result, final_sql = app_state.query_healer.execute_with_healing(sql, modified_plan)

        logger.info("Query executed (%.2fs)", time.time() - step_start)

        # Check for empty results
        no_results = False
        row_count = len(result) if result is not None and hasattr(result, '__len__') else 0
        if result is None or row_count == 0:
            no_results = True
            logger.warning("Query returned 0 rows")
        else:
            logger.info("Query returned %d rows", row_count)

        # Step 2: Generate explanation
        logger.info("Step 2/2: Generating explanation (LLM call)...")
        step_start = time.time()
        emotional_message = user_correction_message if user_correction_message else original_question
        explanation = explain_results(
            result,
            query_plan=modified_plan,
            original_question=original_question,
            raw_user_message=emotional_message,
            user_name=app_state.personality.user_name
        )
        logger.info("Explanation generated (%.2fs)", time.time() - step_start)

        # NOTE: explain_results() already handles empty results - no double response needed

        # Translate if Tamil
        if is_tamil:
            from utils.translation import translate_to_tamil
            explanation = translate_to_tamil(explanation)

        # Extract result values for context
        result_values = _extract_result_values(result, modified_plan) if result is not None else {}
        if result_values:
            logger.debug("Extracted result values for context: %s", result_values)

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

        logger.info("Query completed with modified plan (filter removal)!")

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
        error_str = str(e)
        logger.error("Failed to execute with modified plan: %s", error_str, exc_info=True)

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
    logger.info("Metric Correction Handler")

    # Get entities from previous turn
    corrected_entities = (previous_turn.entities or {}).copy()
    old_values = {}

    # Apply metric corrections
    for correction in (correction_intent.metric_corrections or []):
        old_metric = correction.get('old_metric')
        new_metric = correction.get('new_metric')

        if new_metric:
            logger.debug("Correcting metric: %s -> %s", old_metric, new_metric)
            # Store old metric for question text replacement
            # If old_metric not explicitly provided, get it from previous turn's entities
            if old_metric:
                old_values['metric'] = old_metric
            elif previous_turn.entities and previous_turn.entities.get('metric'):
                old_values['metric'] = previous_turn.entities['metric']
                logger.debug("Using previous entity as old_metric: %s", old_values['metric'])
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
    logger.info("Negation Handler - Smart Auto-Resolution")

    # Strategy 1: Low confidence -> try alternative table
    if previous_turn.confidence < 0.6 and previous_turn.routing_alternatives:
        logger.debug("Previous confidence was low (%.0f%%), trying alternative table", previous_turn.confidence * 100)
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
        logger.debug("Previous query returned no results, trying alternative approach")
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
            logger.debug("Trying alternative table: %s", selected_table)
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
    logger.info("No auto-resolution possible, asking for clarification")
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
        message = """I'm not sure what to correct. Here are some examples:
- For a different table: "use the summary table"
- For a different filter: "for September" or "in Tamil Nadu"
- For a different metric: "show profit instead" """

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
    logger.info("Revert Handler")

    # Find original turn before corrections
    original_turn = ctx.find_original_turn(previous_turn)

    if original_turn and original_turn != previous_turn:
        logger.info("Reverting to original query: %s...", original_turn.question[:50])

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
    logger.info("Multiple Corrections Handler")

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
            logger.debug("Applied filter correction: %s=%s", field, new_value)

    # Apply metric corrections
    for correction in (correction_intent.metric_corrections or []):
        old_metric = correction.get('old_metric')
        new_metric = correction.get('new_metric')
        if new_metric:
            if old_metric:
                old_values['metric'] = old_metric
            corrected_entities['metric'] = new_metric
            logger.debug("Applied metric correction: metric=%s", new_metric)

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
        logger.debug("Applied table correction: %s", table_to_use)

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
    logger.info("Pending Correction Response Handler")

    # Get the turn being corrected
    previous_turn = ctx.get_turn_by_index(pending_correction.previous_turn_index)
    if not previous_turn:
        return None

    # Try to detect what the user wants to correct from their response
    correction_detector = app_state.correction_detector
    correction_intent = correction_detector.detect(user_response, previous_turn)

    if correction_intent:
        logger.debug("Detected correction type from response: %s", correction_intent.correction_type.value)
        return _handle_correction(
            correction_intent=correction_intent,
            previous_turn=previous_turn,
            question=user_response,
            ctx=ctx,
            app_state=app_state,
            is_tamil=is_tamil
        )

    return None

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
