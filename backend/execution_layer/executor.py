from analytics_engine.duckdb_manager import DuckDBManager
from execution_layer.sql_compiler import compile_sql
from analytics_engine.sanity_checks import run_sanity_checks
import pandas as pd

# Advanced query types that need special handling
ADVANCED_QUERY_TYPES = ['comparison', 'percentage', 'trend']


def execute_plan(plan: dict):
    """
    Execute a query plan and return results.

    Routes to advanced executor for comparison/percentage/trend queries.
    """
    query_type = plan.get("query_type")

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
