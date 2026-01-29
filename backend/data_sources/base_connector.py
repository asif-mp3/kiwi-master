"""
Base Connector Abstract Class

All data source connectors inherit from this class to ensure
consistent interface for loading data into the system.

This is ADDITIVE code - does not modify existing Google Sheets functionality.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional
import pandas as pd


class BaseConnector(ABC):
    """
    Abstract base class for all data source connectors.

    Each connector must implement fetch_tables() which returns data
    in the same format as fetch_sheets_with_tables() from the existing
    Google Sheets connector.

    Output format: Dict[str, List[pd.DataFrame]]
    - Key: sheet/file name
    - Value: List of DataFrames (tables detected in that sheet/file)
    """

    def __init__(self, url: str):
        """
        Initialize connector with source URL.

        Args:
            url: Source URL (can be file path, HTTP URL, or service-specific URL)
        """
        self.url = url
        self.source_name: Optional[str] = None

    @abstractmethod
    def fetch_tables(self) -> Dict[str, List[pd.DataFrame]]:
        """
        Fetch and return tables from the data source.

        Returns:
            Dict mapping sheet/file names to lists of DataFrames.
            Each DataFrame represents a detected table.

        Example output:
            {
                "Sales Data": [df1, df2],  # Two tables in this sheet
                "Inventory": [df3]          # One table in this sheet
            }
        """
        pass

    @abstractmethod
    def get_source_name(self) -> str:
        """
        Get a human-readable name for this data source.

        Returns:
            Name like "Sales_Report.csv" or "Q4 Revenue"
        """
        pass

    @classmethod
    @abstractmethod
    def can_handle(cls, url: str) -> bool:
        """
        Check if this connector can handle the given URL.

        Args:
            url: URL to check

        Returns:
            True if this connector can handle the URL
        """
        pass

    def validate_dataframes(self, sheets_with_tables: Dict[str, List[pd.DataFrame]]) -> Dict[str, List[pd.DataFrame]]:
        """
        Validate and clean the fetched DataFrames.

        Args:
            sheets_with_tables: Raw output from fetch_tables

        Returns:
            Cleaned and validated output
        """
        result = {}

        for sheet_name, tables in sheets_with_tables.items():
            valid_tables = []
            for df in tables:
                if df is not None and not df.empty:
                    # Clean column names
                    df.columns = [str(col).strip() for col in df.columns]
                    # Remove completely empty rows
                    df = df.dropna(how='all')
                    if not df.empty:
                        valid_tables.append(df)

            if valid_tables:
                result[sheet_name] = valid_tables

        return result
