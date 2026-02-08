from analytics_engine.duckdb_manager import DuckDBManager
from execution_layer.sql_compiler import compile_sql
from analytics_engine.sanity_checks import run_sanity_checks
import pandas as pd

# Advanced query types that need special handling
ADVANCED_QUERY_TYPES = ['comparison', 'percentage', 'trend']

# Multi-step query types that need cross-table execution
MULTI_STEP_QUERY_TYPES = ['multi_step', 'cross_table']


def execute_plan(plan: dict):
    """
    Execute a query plan and return results.

    Routes to:
    - Multi-step executor for cross-table queries
    - Advanced executor for comparison/percentage/trend queries
    - Standard executor for simple queries
    """
    query_type = plan.get("query_type")

    # Route multi-step queries to specialized executor
    if query_type in MULTI_STEP_QUERY_TYPES or plan.get("steps") is not None:
        return execute_multi_step_plan(plan)

    # Route advanced query types to specialized executor
    if query_type in ADVANCED_QUERY_TYPES:
        return execute_advanced_plan(plan)

    # Standard query execution
    sql = compile_sql(plan)
    db = DuckDBManager()
    result_df = db.query(sql)

    # Pass query_type to sanity checks to allow empty results for filter/lookup queries
    run_sanity_checks(result_df, query_type=query_type)


    # For aggregation_on_subset, the result is already calculated by DuckDB
    # Just attach metadata for the explainer
    if query_type == "aggregation_on_subset":
        aggregation_function = plan["aggregation_function"]
        aggregation_column = plan["aggregation_column"]

        # Store metadata for the explainer
        result_df.attrs['aggregation_function'] = aggregation_function
        result_df.attrs['aggregation_column'] = aggregation_column
        result_df.attrs['query_type'] = 'aggregation_on_subset'

    return result_df


def execute_advanced_plan(plan: dict):
    """
    Execute advanced query types (comparison, percentage, trend).

    These queries require multi-step processing and return enriched results.
    """
    from execution_layer.advanced_executor import execute_advanced_query

    db = DuckDBManager()
    conn = db.get_connection()

    try:
        result = execute_advanced_query(plan, conn)

        # Convert to DataFrame with analysis metadata
        data = result.get("data", [])
        df = pd.DataFrame(data) if data else pd.DataFrame()

        # Attach analysis metadata to DataFrame
        df.attrs['query_type'] = plan.get("query_type")
        df.attrs['analysis'] = result.get("analysis", {})
        df.attrs['calculation_result'] = result.get("calculation_result")
        df.attrs['is_advanced_query'] = True

        return df

    except Exception as e:
        print(f"[Executor] Advanced query failed: {e}")
        # Return empty DataFrame with error info
        df = pd.DataFrame()
        df.attrs['query_type'] = plan.get("query_type")
        df.attrs['analysis'] = {"error": f"Oops! Something went wrong processing that query. Let's try rephrasing it!"}
        df.attrs['is_advanced_query'] = True
        return df


def execute_multi_step_plan(plan: dict):
    """
    Execute multi-step query plans (cross-table queries).

    These queries require sequential execution of multiple steps,
    with intermediate results passed between steps.
    
    Example: "Who worked on peak sales dates in Chennai?"
    - Step 1: Find peak sales date from Sales table
    - Step 2: Find staff from Attendance table for that date
    """
    from execution_layer.multi_step_executor import execute_multi_step_query

    try:
        result = execute_multi_step_query(plan)

        # Get final data from result
        data = result.get("data", [])
        df = pd.DataFrame(data) if data else pd.DataFrame()

        # Attach metadata to DataFrame
        df.attrs['query_type'] = plan.get("query_type", "multi_step")
        df.attrs['analysis'] = result.get("analysis", {})
        df.attrs['is_multi_step'] = True
        df.attrs['steps_executed'] = result.get("steps_executed", [])
        df.attrs['variables'] = result.get("variables", {})

        # Add success flag for explainer to check
        if not result.get("success", False):
            df.attrs['analysis']['error'] = result.get("analysis", {}).get("error", "Multi-step query failed")

        return df

    except Exception as e:
        print(f"[Executor] Multi-step query failed: {e}")
        import traceback
        traceback.print_exc()
        
        # Return empty DataFrame with error info
        df = pd.DataFrame()
        df.attrs['query_type'] = plan.get("query_type", "multi_step")
        df.attrs['analysis'] = {"error": f"Cross-table query failed: {str(e)}"}
        df.attrs['is_multi_step'] = True
        return df

