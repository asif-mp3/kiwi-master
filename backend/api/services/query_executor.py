"""Query re-execution helpers for corrections and forced table routing."""
import re
import copy
import time
import traceback
from typing import Dict, Any, Optional, List

from utils.logger import get_logger
from api.services.app_state import app_state
from api.services.query_utils import _extract_metric_name_from_result, _humanize_metric, _extract_result_values, _sanitize_for_json
from planning_layer.planner_client import generate_plan
from validation_layer.plan_validator import validate_plan
from execution_layer.sql_compiler import compile_sql
from execution_layer.executor import execute_plan
from explanation_layer.explainer_client import explain_results
from utils.translation import translate_to_tamil
from utils.visualization import determine_visualization

logger = get_logger("executor")

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
    logger.info("Re-executing with table: %s", forced_table)

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
    logger.info("Re-executing with corrected entities")

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
            logger.debug("Replacing '%s' -> '%s' in question text", old_metric, new_metric)
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
                    logger.debug("Found metric '%s' in question, replacing with '%s'", metric, new_metric)
                    processing_query = re.sub(
                        rf'\b{metric}\b',
                        new_metric,
                        processing_query,
                        flags=re.IGNORECASE
                    )
                    break

        logger.debug("Modified question: %s", processing_query)

    # For FILTER corrections, also replace old filter values with new ones
    if correction_type == "filter" and old_values:
        for field, old_val in old_values.items():
            new_val = corrected_entities.get(field)
            if old_val and new_val and str(old_val).lower() != str(new_val).lower():
                logger.debug("Replacing filter '%s' -> '%s' in question text", old_val, new_val)
                processing_query = re.sub(
                    rf'\b{re.escape(str(old_val))}\b',
                    str(new_val),
                    processing_query,
                    flags=re.IGNORECASE
                )
        logger.debug("Modified question: %s", processing_query)

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
    logger.info("Re-executing with table=%s and corrected entities", forced_table)

    original_question = previous_turn.resolved_question or previous_turn.question
    processing_query = original_question

    # Apply text replacements for metric/filter corrections
    if old_values:
        for field, old_val in old_values.items():
            new_val = corrected_entities.get(field)
            if old_val and new_val and str(old_val).lower() != str(new_val).lower():
                logger.debug("Replacing '%s' -> '%s' in question text", old_val, new_val)
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
    logger.info("Re-executing turn: %s...", turn.question[:50])

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
        logger.info("Running with forced table...")
        logger.debug("Table: %s", forced_table)
        logger.debug("Original question: %s...", (original_question or '')[:80])
        logger.debug("Processing query: %s...", (processing_query or '')[:80])

        # Step 1: Get schema
        logger.info("Step 1/5: Getting table schema...")
        schema_context = app_state.table_router.get_table_schema(forced_table)
        logger.info("Schema retrieved (%.2fs)", time.time() - step_start)

        # Step 2: Generate plan
        logger.info("Step 2/5: Generating query plan (LLM call)...")
        step_start = time.time()
        from planning_layer.planner_client import generate_plan
        from validation_layer.plan_validator import validate_plan
        from execution_layer.sql_compiler import compile_sql
        from execution_layer.executor import execute_plan, ADVANCED_QUERY_TYPES

        plan = generate_plan(processing_query, schema_context, entities=entities)
        logger.info("Plan generated (%.2fs)", time.time() - step_start)

        # Step 3: Validate plan
        logger.info("Step 3/5: Validating plan...")
        step_start = time.time()
        validate_plan(plan)
        logger.info("Plan validated (%.2fs)", time.time() - step_start)

        # Override table in plan if needed
        plan['table'] = forced_table

        logger.info("Plan generated for table: %s", plan.get('table'))

        # Step 4: Execute SQL
        logger.info("Step 4/5: Executing query...")
        step_start = time.time()
        query_type = plan.get('query_type')
        if query_type in ADVANCED_QUERY_TYPES:
            logger.debug("Advanced query type: %s", query_type)
            result = execute_plan(plan)
            final_sql = f"[Advanced {query_type} query - see analysis]"
            # CRITICAL: Store analysis in plan for projection support
            # Advanced queries return DataFrames with analysis in attrs
            if hasattr(result, 'attrs') and 'analysis' in result.attrs:
                analysis = result.attrs['analysis']
                plan['analysis'] = analysis if isinstance(analysis, dict) else {}
                if plan['analysis']:
                    logger.debug("Stored analysis in plan for projection: %s", list(plan['analysis'].keys()))
            elif isinstance(result, dict) and 'analysis' in result:
                plan['analysis'] = result.get('analysis', {})
        else:
            sql = compile_sql(plan)
            logger.debug("SQL: %s...", sql[:100])
            result, final_sql = app_state.query_healer.execute_with_healing(sql, plan)
        logger.info(f"    [OK] Query executed ({time.time() - step_start:.2f}s)")

        # Check for empty results
        no_results = False
        row_count = len(result) if result is not None and hasattr(result, '__len__') else 0
        if result is None or row_count == 0:
            no_results = True
            logger.debug(f"    ! Query returned 0 rows")
        else:
            logger.info(f"    [OK] Query returned {row_count} rows")

        # Step 5: Generate explanation
        logger.info("  [Step 5/5] Generating explanation (LLM call)...")
        step_start = time.time()
        from explanation_layer.explainer_client import explain_results
        # Use correction_message (angry message) for emotion detection if available
        # Otherwise fall back to original_question
        emotional_message = correction_message if correction_message else original_question
        explanation = explain_results(
            result,
            query_plan=plan,
            original_question=processing_query,
            raw_user_message=emotional_message,  # Correction message or original for emotion
            user_name=app_state.personality.user_name
        )
        logger.info(f"    [OK] Explanation generated ({time.time() - step_start:.2f}s)")

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
            logger.info(f"  [OK] Extracted result values for context: {result_values}")

        # Make a deep copy of plan to preserve analysis for projection follow-ups
        stored_plan = copy.deepcopy(plan)

        # Debug: Verify analysis is in stored_plan
        if stored_plan.get('analysis'):
            logger.info(f"  [OK] Plan analysis preserved for projection: {list(stored_plan['analysis'].keys())}")

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

        logger.info("\n[SUCCESS] Query completed with forced table!")
        logger.debug("=" * 60 + "\n")

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
        logger.error(f"\n[ERROR] Failed to execute with forced table: {error_str}")
        logger.error(f"  Traceback:\n{error_trace}")

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
