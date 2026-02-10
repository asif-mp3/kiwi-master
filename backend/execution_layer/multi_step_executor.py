"""
Multi-Step Query Executor - Handles queries requiring data from multiple tables.

This module enables cross-table queries like:
- "Who worked on peak sales dates in Chennai?"
- "What products were sold on days with best attendance?"

It breaks complex queries into sequential steps, executes each step,
and passes results between steps using variable substitution.

ARCHITECTURE NOTES:
- Follows existing pattern: module-level functions (not classes)
- Uses DuckDBManager for database connections
- Returns dict with 'data', 'analysis' keys like advanced_executor
- Integrates with execute_plan() in executor.py
"""

import json
from typing import Dict, List, Any, Optional
from datetime import datetime

from analytics_engine.duckdb_manager import DuckDBManager
from execution_layer.sql_compiler import compile_sql


# ============================================
# MULTI-STEP QUERY TYPES
# ============================================
MULTI_STEP_QUERY_TYPES = ['multi_step', 'cross_table']


def is_multi_step_query(plan: dict) -> bool:
    """Check if this plan requires multi-step execution."""
    return (
        plan.get("query_type") in MULTI_STEP_QUERY_TYPES or
        plan.get("steps") is not None
    )


def execute_multi_step_query(plan: dict) -> Dict[str, Any]:
    """
    Execute a multi-step query plan.
    
    The plan should contain a 'steps' array, where each step is a sub-plan
    that follows the standard plan schema. Results from earlier steps
    can be referenced in later steps using ${variable_name} syntax.
    
    Args:
        plan: Multi-step query plan with 'steps' array
        
    Returns:
        Dict with:
        - data: Final result data (list of dicts)
        - analysis: Metadata about execution
        - steps_executed: Details of each step
        - variables: All extracted intermediate values
    
    Example plan:
    {
        "query_type": "multi_step",
        "description": "Find staff present on peak sales date",
        "steps": [
            {
                "step_id": 1,
                "description": "Find peak sales date in Chennai",
                "query_type": "extrema_lookup", 
                "table": "Sales_Data",
                "filters": [{"column": "Branch", "operator": "LIKE", "value": "%Chennai%"}],
                "order_by": [{"column": "Sale_Amount", "direction": "DESC"}],
                "limit": 1,
                "output_variable": "peak_date",
                "extract_column": "Date"
            },
            {
                "step_id": 2,
                "description": "Get attendance for that date",
                "query_type": "filter",
                "table": "Attendance_Records",
                "filters": [
                    {"column": "Date", "operator": "=", "value": "${peak_date}"},
                    {"column": "Branch", "operator": "LIKE", "value": "%Chennai%"}
                ]
            }
        ]
    }
    """
    import time
    import copy
    start_time = time.time()

    # CRITICAL: Deep copy plan to prevent modifications from bleeding back to caller
    # This protects against in-place modifications during variable substitution
    plan = copy.deepcopy(plan)

    steps = plan.get("steps", [])
    if not steps:
        return {
            "data": [],
            "analysis": {"error": "No steps defined in multi-step plan"},
            "success": False
        }
    
    print(f"\n{'='*60}")
    print(f"[MULTI-STEP] Starting execution of {len(steps)} steps")
    print(f"{'='*60}\n")
    
    # Get DuckDB connection
    db = DuckDBManager()
    conn = db.get_connection()
    
    # Track variables and executed steps
    variables = {}
    executed_steps = []
    
    try:
        for i, step in enumerate(steps, 1):
            step_start = time.time()
            step_id = step.get('step_id', i)
            description = step.get('description', f'Step {step_id}')
            
            print(f"\n[STEP {i}/{len(steps)}] {description}")
            print(f"  Table: {step.get('table', 'N/A')}")
            print(f"  Type: {step.get('query_type', 'N/A')}")
            
            # Substitute variables in this step
            substituted_step = _substitute_variables(step, variables)
            
            # Execute the step
            step_result = _execute_single_step(substituted_step, conn)
            
            if step_result.get('error'):
                error_msg = step_result.get('error')
                print(f"  [FAIL] Step {step_id} failed: {error_msg}")

                # Build helpful error message
                helpful_msg = f"Cross-table query failed at step {step_id} ({description}): {error_msg}"
                if "no such table" in error_msg.lower():
                    helpful_msg += f"\n\nTip: Check that the table name '{step.get('table')}' exists in your data."
                elif "no such column" in error_msg.lower():
                    helpful_msg += f"\n\nTip: Check that the column names in filters exist in table '{step.get('table')}'."

                return {
                    "data": [],
                    "analysis": {
                        "error": helpful_msg,
                        "failed_step": step_id,
                        "step_description": description
                    },
                    "success": False,
                    "steps_executed": executed_steps
                }
            
            # Extract output variable if specified
            output_var = step.get('output_variable')
            if output_var:
                extract_col = step.get('extract_column')
                extracted_value = _extract_variable(step_result, extract_col)
                if extracted_value is not None:
                    variables[output_var] = extracted_value
                    print(f"  [OK] Extracted ${{{output_var}}} = {extracted_value}")

                    # Validate extracted date exists in target table's date range
                    # This prevents cross-table queries from failing silently
                    if 'date' in output_var.lower() and i < len(steps):
                        next_step = steps[i]  # i is already 1-indexed
                        next_table = next_step.get("table")
                        if next_table:
                            try:
                                from schema_intelligence.profile_store import ProfileStore
                                profile_store = ProfileStore()
                                profile = profile_store.get_profile(next_table)
                                if profile and profile.get('date_range'):
                                    date_range = profile['date_range']
                                    date_min = date_range.get('min', '')
                                    date_max = date_range.get('max', '')
                                    if date_min and date_max:
                                        # Extract just the date part for comparison
                                        extracted_str = str(extracted_value)[:10]  # YYYY-MM-DD
                                        min_str = date_min[:10] if isinstance(date_min, str) else str(date_min)[:10]
                                        max_str = date_max[:10] if isinstance(date_max, str) else str(date_max)[:10]
                                        if extracted_str < min_str or extracted_str > max_str:
                                            warning_msg = (
                                                f"The date {extracted_str} doesn't have data in {next_table}. "
                                                f"Available range: {min_str} to {max_str}"
                                            )
                                            print(f"  [WARN] {warning_msg}")
                                            return {
                                                "data": [],
                                                "analysis": {
                                                    "error": warning_msg,
                                                    "date_mismatch": True
                                                },
                                                "success": False,
                                                "steps_executed": executed_steps
                                            }
                            except Exception as e:
                                print(f"  [WARN] Could not validate date range: {e}")
                else:
                    # Variable extraction failed - this is critical for multi-step queries
                    warning_msg = f"Could not extract variable ${{{output_var}}} from column '{extract_col}'"
                    print(f"  [WARN] {warning_msg}")
                    print(f"  [INFO] Step returned {len(step_result.get('data', []))} rows")
                    if len(step_result.get('data', [])) == 0:
                        return {
                            "data": [],
                            "analysis": {
                                "error": f"Step {step_id} returned no data to extract ${{{output_var}}} from. This means the first query found no matching records.",
                                "failed_step": step_id
                            },
                            "success": False,
                            "steps_executed": executed_steps
                        }
            
            step_elapsed = (time.time() - step_start) * 1000
            print(f"  [TIME] Step completed in {step_elapsed:.0f}ms")
            print(f"  [DATA] Rows returned: {len(step_result.get('data', []))}")
            
            # Store step result
            executed_steps.append({
                'step_id': step_id,
                'description': description,
                'data': step_result.get('data', []),
                'elapsed_ms': step_elapsed
            })
        
        total_elapsed = (time.time() - start_time) * 1000
        print(f"\n{'='*60}")
        print(f"[MULTI-STEP] All steps completed in {total_elapsed:.0f}ms")
        print(f"{'='*60}\n")
        
        # Return final step's data as main result
        final_data = executed_steps[-1]['data'] if executed_steps else []
        
        return {
            "data": final_data,
            "analysis": {
                "multi_step": True,
                "total_steps": len(steps),
                "steps_executed": len(executed_steps),
                "variables": variables,
                "total_elapsed_ms": total_elapsed
            },
            "success": True,
            "steps_executed": executed_steps,
            "variables": variables
        }
        
    except Exception as e:
        print(f"\n[ERROR] Multi-step execution failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            "data": [],
            "analysis": {
                "error": f"Multi-step execution failed: {str(e)}",
                "multi_step": True
            },
            "success": False,
            "steps_executed": executed_steps
        }


def _substitute_variables(step: Dict[str, Any], variables: Dict[str, Any]) -> Dict[str, Any]:
    """
    Substitute ${variable_name} placeholders with actual values.

    Works recursively through the step dict, replacing placeholders
    in all string values (including nested in filters, etc.)

    IMPORTANT: This function returns a NEW dict - the input 'step' is never modified.
    The JSON round-trip (dumps → replace → loads) creates a deep copy.
    """
    # Convert to JSON for easy recursive substitution
    step_json = json.dumps(step)
    
    # Replace each variable
    for var_name, var_value in variables.items():
        placeholder = f"${{{var_name}}}"
        # Format dates appropriately
        if hasattr(var_value, 'strftime'):
            value_str = var_value.strftime('%Y-%m-%d')
        else:
            value_str = str(var_value)
        step_json = step_json.replace(placeholder, value_str)
    
    return json.loads(step_json)


def _execute_single_step(step: Dict[str, Any], conn) -> Dict[str, Any]:
    """
    Execute a single step of the multi-step plan.
    
    Compiles the step plan to SQL and executes it.
    Returns dict with 'data' and optional 'error'.
    """
    try:
        # Use standard SQL compiler
        sql = compile_sql(step)
        
        print(f"  [SQL] {sql[:100]}..." if len(sql) > 100 else f"  [SQL] {sql}")
        
        # Execute query
        result = conn.execute(sql).fetchall()
        
        # Get column names
        columns = [desc[0] for desc in conn.description]
        
        # Convert to list of dicts
        data = [dict(zip(columns, row)) for row in result]
        
        return {"data": data}
        
    except Exception as e:
        return {"data": [], "error": str(e)}


def _extract_variable(step_result: Dict[str, Any], column_name: Optional[str] = None) -> Optional[Any]:
    """
    Extract a variable value from step result.
    
    If column_name is specified, extracts that column from first row.
    Otherwise, extracts first column of first row.
    """
    data = step_result.get('data', [])
    if not data:
        return None
    
    first_row = data[0]
    
    if column_name and column_name in first_row:
        return first_row[column_name]
    
    # Return first column value
    return list(first_row.values())[0] if first_row else None


# ============================================
# MULTI-STEP PLAN GENERATION HELPERS
# ============================================

def generate_cross_table_plan(
    source_domain: str,
    target_domain: str,
    intermediate_variable: str,
    source_table: str,
    target_table: str,
    location_filter: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generate a multi-step plan for cross-table queries.
    
    This is a utility function to help the planner create
    proper multi-step plans for detected cross-domain queries.
    
    Args:
        source_domain: Primary domain (e.g., 'sales')
        target_domain: Secondary domain (e.g., 'attendance')
        intermediate_variable: Variable to extract (e.g., 'peak_sales_date')
        source_table: Table name for source domain
        target_table: Table name for target domain
        location_filter: Optional location to filter by
        
    Returns:
        Multi-step plan dict
    """
    # Build location filter
    filters = []
    if location_filter:
        filters.append({
            "column": "Branch",  # May need schema-aware column selection
            "operator": "LIKE",
            "value": f"%{location_filter}%"
        })
    
    # Define step templates based on intermediate variable
    if intermediate_variable == 'peak_sales_date':
        steps = [
            {
                "step_id": 1,
                "description": f"Find peak sales date{f' in {location_filter}' if location_filter else ''}",
                "query_type": "extrema_lookup",
                "table": source_table,
                "filters": filters.copy(),
                "metrics": [{"column": "Sale_Amount", "aggregation": "SUM"}],
                "order_by": [{"column": "Sale_Amount", "direction": "DESC"}],
                "limit": 1,
                "output_variable": "peak_date",
                "extract_column": "Date"
            },
            {
                "step_id": 2,
                "description": f"Find staff present on that date",
                "query_type": "filter",
                "table": target_table,
                "filters": [
                    {"column": "Date", "operator": "=", "value": "${peak_date}"},
                    *filters
                ]
            }
        ]
    elif intermediate_variable == 'best_attendance_date':
        steps = [
            {
                "step_id": 1,
                "description": f"Find best attendance date{f' in {location_filter}' if location_filter else ''}",
                "query_type": "extrema_lookup",
                "table": source_table,
                "filters": filters.copy(),
                "group_by": ["Date"],
                "metrics": [{"column": "Employee_ID", "aggregation": "COUNT"}],
                "order_by": [{"column": "COUNT", "direction": "DESC"}],
                "limit": 1,
                "output_variable": "best_date",
                "extract_column": "Date"
            },
            {
                "step_id": 2,
                "description": f"Find sales on that date",
                "query_type": "filter",
                "table": target_table,
                "filters": [
                    {"column": "Date", "operator": "=", "value": "${best_date}"},
                    *filters
                ]
            }
        ]
    else:
        # Generic template
        steps = [
            {
                "step_id": 1,
                "description": f"Step 1 for {source_domain}",
                "query_type": "filter",
                "table": source_table,
                "filters": filters,
                "limit": 1,
                "output_variable": intermediate_variable
            },
            {
                "step_id": 2,
                "description": f"Step 2 for {target_domain}",
                "query_type": "filter",
                "table": target_table,
                "filters": [
                    {"column": "Date", "operator": "=", "value": f"${{{intermediate_variable}}}"}
                ]
            }
        ]
    
    return {
        "query_type": "multi_step",
        "description": f"Cross-table query: {source_domain} → {target_domain}",
        "source_domain": source_domain,
        "target_domain": target_domain,
        "steps": steps
    }
