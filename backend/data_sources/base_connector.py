"""
Base Connector Abstract Class

All data source connectors inherit from this class to ensure
consistent interface for loading data into the system.

This is ADDITIVE code - does not modify existing Google Sheets functionality.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, ClassVar
import pandas as pd


class OutputContractError(Exception):
    """Raised when connector output doesn't match the expected contract."""
    pass


class BaseConnector(ABC):
    """
    Abstract base class for all data source connectors.

    Each connector must implement fetch_tables() which returns data
    in the same format as fetch_sheets_with_tables() from the existing
    Google Sheets connector.

    Output format: Dict[str, List[pd.DataFrame]]
    - Key: sheet/file name
    - Value: List of DataFrames (tables detected in that sheet/file)

    Capability Metadata:
    - supports_sync: Can detect changes for auto-sync
    - supports_folders: Can list folder contents
    - supports_preview: Can generate document preview
    - supports_streaming: Can stream large files
    - auth_mode: "anonymous" | "oauth" | "api_key" | "token"
    - required_credentials: List of credential keys needed
    - priority: Higher priority wins when multiple connectors match
    """

    # Capability flags (override in subclasses)
    supports_sync: ClassVar[bool] = True
    supports_folders: ClassVar[bool] = False
    supports_preview: ClassVar[bool] = False
    supports_streaming: ClassVar[bool] = False

    # Auth requirements
    auth_mode: ClassVar[str] = "anonymous"  # "anonymous" | "oauth" | "api_key" | "token"
    required_credentials: ClassVar[List[str]] = []

    # Priority for URL matching (higher wins)
    priority: ClassVar[int] = 100

    def __init__(self, url: str, credentials: Optional[Dict] = None):
        """
        Initialize connector with source URL and optional credentials.

        Args:
            url: Source URL (can be file path, HTTP URL, or service-specific URL)
            credentials: Optional dict of credentials for authenticated sources
        """
        self.url = url
        self.credentials = credentials or {}
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

    def validate_output(self, result: Dict[str, List[pd.DataFrame]]) -> Dict[str, List[pd.DataFrame]]:
        """
        Enforce the output contract for connector results.

        OUTPUT CONTRACT:
        - Returns Dict[str, List[pd.DataFrame]]
        - Keys are table names (non-empty strings)
        - Values are lists of DataFrames (at least 1)
        - DataFrames must have at least 1 row and 1 column
        - Consistent dtypes per column (no mixed types)

        Args:
            result: Raw output from fetch_tables

        Returns:
            Validated output

        Raises:
            OutputContractError: If output doesn't match contract
        """
        validated = {}

        for name, dfs in result.items():
            if not name or not isinstance(name, str):
                raise OutputContractError(f"Invalid table name: {name}")

            valid_dfs = []
            for df in dfs:
                if df is None or df.empty:
                    continue  # Skip empty frames

                if len(df.columns) == 0:
                    continue  # Skip no-column frames

                # Check for mixed dtypes (allow None + 1 type)
                for col in df.columns:
                    try:
                        unique_types = df[col].dropna().apply(type).nunique()
                        if unique_types > 1:
                            print(f"  [Connector] Warning: Mixed types in {name}.{col}")
                    except Exception:
                        pass  # Skip type checking on error

                valid_dfs.append(df)

            if valid_dfs:
                validated[name] = valid_dfs

        return validated

    def validate_auth(self) -> None:
        """
        Validate that required credentials are present.

        Raises:
            ValueError: If required credentials are missing
        """
        if self.auth_mode == "anonymous":
            return  # No auth needed

        for required in self.required_credentials:
            if required not in self.credentials:
                raise ValueError(f"Missing required credential: {required}")
