"""
Excel Connector

Handles loading Excel files from:
- Local file paths
- HTTP/HTTPS URLs

Supports .xlsx, .xls, and .xlsm formats.

This is ADDITIVE code - does not modify existing Google Sheets functionality.
"""

import os
import tempfile
from typing import Dict, List
from urllib.parse import urlparse
import pandas as pd
import requests

from data_sources.base_connector import BaseConnector


class ExcelConnector(BaseConnector):
    """
    Connector for Excel files.

    Supports:
    - Local files: /path/to/file.xlsx
    - HTTP URLs: https://example.com/data.xlsx
    - Multiple sheets within a workbook
    """

    SUPPORTED_EXTENSIONS = ('.xlsx', '.xls', '.xlsm')

    def __init__(self, url: str):
        super().__init__(url)
        self._sheets: Dict[str, pd.DataFrame] = {}

    @classmethod
    def can_handle(cls, url: str) -> bool:
        """Check if this connector can handle the URL."""
        if not url:
            return False

        url_lower = url.lower()

        # Check file extension
        for ext in cls.SUPPORTED_EXTENSIONS:
            if url_lower.endswith(ext):
                return True

        return False

    def get_source_name(self) -> str:
        """Get human-readable name for this data source."""
        if self.source_name:
            return self.source_name

        # Extract filename from URL or path
        parsed = urlparse(self.url)

        if parsed.scheme in ('http', 'https'):
            path = parsed.path
            filename = os.path.basename(path)
        else:
            filename = os.path.basename(self.url)

        # Remove extension
        for ext in self.SUPPORTED_EXTENSIONS:
            if filename.lower().endswith(ext):
                filename = filename[:-len(ext)]
                break

        self.source_name = filename or 'Excel_Data'
        return self.source_name

    def fetch_tables(self) -> Dict[str, List[pd.DataFrame]]:
        """
        Fetch Excel data and return as tables.

        Returns:
            Dict with sheet names as keys and lists of DataFrames
        """
        sheets = self._load_excel()

        if not sheets:
            return {}

        # Each sheet is treated as a single table
        result = {}
        for sheet_name, df in sheets.items():
            if df is not None and not df.empty:
                result[sheet_name] = [df]

        return self.validate_dataframes(result)

    def _load_excel(self) -> Dict[str, pd.DataFrame]:
        """Load Excel from URL or file path."""
        try:
            parsed = urlparse(self.url)

            if parsed.scheme in ('http', 'https'):
                return self._load_from_url()
            else:
                return self._load_from_file()

        except Exception as e:
            print(f"[ExcelConnector] Error loading Excel: {e}")
            raise ValueError(f"Failed to load Excel file: {e}")

    def _load_from_url(self) -> Dict[str, pd.DataFrame]:
        """Load Excel from HTTP/HTTPS URL."""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (compatible; TharaAI/1.0)'
            }

            response = requests.get(self.url, headers=headers, timeout=60)
            response.raise_for_status()

            # Save to temp file (openpyxl needs a file)
            with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:
                tmp.write(response.content)
                tmp_path = tmp.name

            try:
                sheets = self._read_excel_file(tmp_path)
                return sheets
            finally:
                # Clean up temp file
                try:
                    os.unlink(tmp_path)
                except Exception:
                    pass

        except requests.RequestException as e:
            raise ValueError(f"Failed to download Excel from URL: {e}")

    def _load_from_file(self) -> Dict[str, pd.DataFrame]:
        """Load Excel from local file."""
        file_path = self.url

        # Handle file:// prefix
        if file_path.startswith('file://'):
            file_path = file_path[7:]

        if not os.path.exists(file_path):
            raise ValueError(f"Excel file not found: {file_path}")

        return self._read_excel_file(file_path)

    def _read_excel_file(self, file_path: str) -> Dict[str, pd.DataFrame]:
        """Read all sheets from Excel file."""
        try:
            # Read all sheets
            excel_file = pd.ExcelFile(file_path)
            sheets = {}

            for sheet_name in excel_file.sheet_names:
                try:
                    df = pd.read_excel(excel_file, sheet_name=sheet_name)

                    # Skip empty sheets
                    if df.empty:
                        continue

                    sheets[sheet_name] = df
                    print(f"[ExcelConnector] Loaded sheet '{sheet_name}' with {len(df)} rows")

                except Exception as e:
                    print(f"[ExcelConnector] Error reading sheet '{sheet_name}': {e}")
                    continue

            return sheets

        except Exception as e:
            raise ValueError(f"Failed to read Excel file: {e}")
