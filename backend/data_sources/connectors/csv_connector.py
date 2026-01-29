"""
CSV Connector

Handles loading CSV files from:
- Local file paths
- HTTP/HTTPS URLs
- Data URLs

This is ADDITIVE code - does not modify existing Google Sheets functionality.
"""

import os
import re
from typing import Dict, List
from urllib.parse import urlparse
import pandas as pd
import requests

from data_sources.base_connector import BaseConnector


class CSVConnector(BaseConnector):
    """
    Connector for CSV files.

    Supports:
    - Local files: /path/to/file.csv or C:\\path\\to\\file.csv
    - HTTP URLs: https://example.com/data.csv
    - GitHub raw URLs: https://raw.githubusercontent.com/...
    """

    def __init__(self, url: str):
        super().__init__(url)
        self._df: pd.DataFrame = None

    @classmethod
    def can_handle(cls, url: str) -> bool:
        """Check if this connector can handle the URL."""
        if not url:
            return False

        url_lower = url.lower()

        # Check file extension
        if url_lower.endswith('.csv'):
            return True

        # Check for CSV format hints in URL
        if 'format=csv' in url_lower or 'output=csv' in url_lower:
            return True

        return False

    def get_source_name(self) -> str:
        """Get human-readable name for this data source."""
        if self.source_name:
            return self.source_name

        # Extract filename from URL or path
        parsed = urlparse(self.url)

        if parsed.scheme in ('http', 'https'):
            # Get filename from URL path
            path = parsed.path
            filename = os.path.basename(path)
            if filename:
                self.source_name = filename.replace('.csv', '')
            else:
                self.source_name = 'CSV_Data'
        else:
            # Local file path
            filename = os.path.basename(self.url)
            self.source_name = filename.replace('.csv', '')

        return self.source_name

    def fetch_tables(self) -> Dict[str, List[pd.DataFrame]]:
        """
        Fetch CSV data and return as tables.

        Returns:
            Dict with source name as key and list containing single DataFrame
        """
        df = self._load_csv()

        if df is None or df.empty:
            return {}

        source_name = self.get_source_name()

        # CSV is a single table
        result = {source_name: [df]}

        return self.validate_dataframes(result)

    def _load_csv(self) -> pd.DataFrame:
        """Load CSV from URL or file path."""
        try:
            parsed = urlparse(self.url)

            if parsed.scheme in ('http', 'https'):
                return self._load_from_url()
            else:
                return self._load_from_file()

        except Exception as e:
            print(f"[CSVConnector] Error loading CSV: {e}")
            raise ValueError(f"Failed to load CSV: {e}")

    def _load_from_url(self) -> pd.DataFrame:
        """Load CSV from HTTP/HTTPS URL."""
        try:
            # Use requests to handle various URL types
            headers = {
                'User-Agent': 'Mozilla/5.0 (compatible; TharaAI/1.0)'
            }

            response = requests.get(self.url, headers=headers, timeout=30)
            response.raise_for_status()

            # Try to detect encoding
            encoding = response.apparent_encoding or 'utf-8'

            # Parse CSV with pandas
            from io import StringIO
            content = response.content.decode(encoding)
            df = pd.read_csv(StringIO(content))

            print(f"[CSVConnector] Loaded {len(df)} rows from URL")
            return df

        except requests.RequestException as e:
            raise ValueError(f"Failed to download CSV from URL: {e}")

    def _load_from_file(self) -> pd.DataFrame:
        """Load CSV from local file."""
        file_path = self.url

        # Handle file:// prefix
        if file_path.startswith('file://'):
            file_path = file_path[7:]

        if not os.path.exists(file_path):
            raise ValueError(f"CSV file not found: {file_path}")

        # Try different encodings
        encodings = ['utf-8', 'latin-1', 'cp1252']

        for encoding in encodings:
            try:
                df = pd.read_csv(file_path, encoding=encoding)
                print(f"[CSVConnector] Loaded {len(df)} rows from file")
                return df
            except UnicodeDecodeError:
                continue

        raise ValueError(f"Could not decode CSV file with any supported encoding")
