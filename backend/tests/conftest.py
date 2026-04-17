"""Shared test fixtures for Thara AI backend tests."""

import os
import sys
import pytest

# Ensure backend directory is on the path
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

# Set test environment
os.environ["ENVIRONMENT"] = "test"
os.environ["SKIP_AUTH"] = "true"


@pytest.fixture
def sample_metric_plan():
    """A rank query plan that exercises aggregation (metric type needs MetricRegistry)."""
    return {
        "query_type": "rank",
        "table": "sales_data",
        "metrics": [],
        "aggregation_function": "SUM",
        "group_by": ["Category"],
        "order_by": [("Revenue", "DESC")],
        "filters": [],
        "limit": 10,
        "date_grouping": "",
    }


@pytest.fixture
def sample_filter_plan():
    """A filter query plan."""
    return {
        "query_type": "filter",
        "table": "employees",
        "select_columns": ["Name", "Department"],
        "filters": [
            {"column": "Department", "operator": "=", "value": "Engineering"}
        ],
    }


@pytest.fixture
def sample_lookup_plan():
    """A lookup query plan."""
    return {
        "query_type": "lookup",
        "table": "employees",
        "select_columns": ["Name", "Salary"],
        "filters": [
            {"column": "Name", "operator": "=", "value": "Rajesh"}
        ],
    }
