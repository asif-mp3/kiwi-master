"""
Table Detection Integration Module
====================================

This module provides table detection for Google Sheets data.
Each sheet is treated as a single table with automatic header detection.
"""

import pandas as pd
from typing import List, Dict, Any
import re


def _sanitize_sheet_name(sheet_name: str) -> str:
    """
    Convert sheet name to a clean, lowercase snake_case format for table_id.

    Examples:
        "Payroll Summary" -> "payroll_summary"
        "Staff Maintenance" -> "staff_maintenance"
        "Sales-2024" -> "sales_2024"
        "Department Summary (Q1)" -> "department_summary_q1"
    """
    # Convert to lowercase
    name = sheet_name.lower()
    # Replace spaces, hyphens, and special chars with underscores
    name = re.sub(r'[\s\-\(\)\[\]]+', '_', name)
    # Remove any remaining non-alphanumeric characters except underscores
    name = re.sub(r'[^a-z0-9_]', '', name)
    # Remove leading/trailing underscores and collapse multiple underscores
    name = re.sub(r'_+', '_', name).strip('_')
    return name or 'unknown_sheet'


def detect_and_clean_tables(df: pd.DataFrame, sheet_name: str) -> List[Dict[str, Any]]:
    """
    Detect and clean tables from a sheet DataFrame.

    Args:
        df: Raw DataFrame from Google Sheets
        sheet_name: Name of the source sheet

    Returns:
        List of detected tables with metadata
    """
    if df is None or df.empty:
        return []

    sanitized_name = _sanitize_sheet_name(sheet_name)

    # Clean the dataframe
    cleaned_df = _clean_dataframe(df)

    if cleaned_df.empty:
        return []

    return [{
        'table_id': f'{sanitized_name}_table_1',
        'row_range': (0, int(len(cleaned_df))),
        'col_range': (0, int(len(cleaned_df.columns))),
        'dataframe': cleaned_df,
        'title': sheet_name,
        'sheet_name': sheet_name
    }]


def _clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean a DataFrame by:
    - Removing completely empty rows and columns
    - Setting first row as header if it looks like headers
    - Cleaning column names
    """
    if df is None or df.empty:
        return df

    # Make a copy
    df = df.copy()

    # Remove completely empty rows
    df = df.dropna(how='all')

    # Remove completely empty columns
    df = df.dropna(axis=1, how='all')

    if df.empty:
        return df

    # Check if first row looks like headers (mostly strings, no nulls)
    first_row = df.iloc[0]
    non_null_count = first_row.notna().sum()
    string_count = sum(1 for v in first_row if isinstance(v, str) and v.strip())

    if non_null_count > 0 and string_count >= non_null_count * 0.5:
        # First row looks like headers
        new_headers = [str(v).strip() if pd.notna(v) else f'Column_{i}'
                       for i, v in enumerate(first_row)]
        df = df.iloc[1:].reset_index(drop=True)
        df.columns = new_headers
    else:
        # Generate generic column names
        df.columns = [f'Column_{i}' for i in range(len(df.columns))]

    # Clean column names (remove special chars, make unique)
    seen = {}
    new_cols = []
    for col in df.columns:
        col_clean = re.sub(r'[^\w\s]', '', str(col)).strip()
        col_clean = col_clean.replace(' ', '_') if col_clean else 'Column'

        if col_clean in seen:
            seen[col_clean] += 1
            col_clean = f'{col_clean}_{seen[col_clean]}'
        else:
            seen[col_clean] = 0
        new_cols.append(col_clean)

    df.columns = new_cols

    return df


def get_table_name(sheet_name: str, table_index: int) -> str:
    """
    Generate a standardized table name.
    
    Args:
        sheet_name: Source sheet name
        table_index: 1-indexed table number
    
    Returns:
        Formatted table name: {SheetName}_Table{N}
    """
    return f"{sheet_name}_Table{table_index}"
