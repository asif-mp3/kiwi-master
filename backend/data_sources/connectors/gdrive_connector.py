"""
Google Drive Connector

Handles loading files from Google Drive:
- Publicly shared files
- Files shared with "anyone with link" permission

Supports CSV and Excel files hosted on Google Drive.
Note: Google Sheets URLs are handled by the EXISTING code path.

This is ADDITIVE code - does not modify existing Google Sheets functionality.
"""

import os
import re
import tempfile
from typing import Dict, List, Optional
import pandas as pd
import requests

from data_sources.base_connector import BaseConnector
from data_sources.connector_factory import is_google_sheets_url


class GoogleDriveConnector(BaseConnector):
    """
    Connector for Google Drive files.

    Supports:
    - drive.google.com/file/d/{file_id}/view links
    - drive.google.com/open?id={file_id} links
    - Direct download links

    Note: For Google Sheets, use the existing Google Sheets code path.
    """

    def __init__(self, url: str, credentials: Optional[Dict] = None):
        super().__init__(url, credentials)
        self._file_id: Optional[str] = None
        self._detected_type: Optional[str] = None

    @classmethod
    def can_handle(cls, url: str) -> bool:
        """Check if this connector can handle the URL."""
        if not url:
            return False

        # Don't handle Google Sheets (uses existing code path)
        if is_google_sheets_url(url):
            return False

        # Check for Google Drive URL patterns
        patterns = [
            r'drive\.google\.com/file/d/',
            r'drive\.google\.com/open\?id=',
            r'drive\.google\.com/uc\?',
        ]

        for pattern in patterns:
            if re.search(pattern, url):
                return True

        return False

    def get_source_name(self) -> str:
        """Get human-readable name for this data source."""
        if self.source_name:
            return self.source_name

        file_id = self._extract_file_id()
        self.source_name = f"GDrive_{file_id[:8]}" if file_id else "Google_Drive_Data"
        return self.source_name

    def fetch_tables(self) -> Dict[str, List[pd.DataFrame]]:
        """
        Fetch Google Drive file and return as tables.

        Returns:
            Dict with source name as key and list of DataFrames
        """
        file_id = self._extract_file_id()

        if not file_id:
            raise ValueError("Could not extract file ID from Google Drive URL")

        # Download and detect file type
        file_path, file_type = self._download_file(file_id)

        try:
            if file_type == 'csv':
                df = pd.read_csv(file_path)
                source_name = self.get_source_name()
                result = {source_name: [df]}

            elif file_type in ('xlsx', 'xls'):
                excel_file = pd.ExcelFile(file_path)
                result = {}

                for sheet_name in excel_file.sheet_names:
                    df = pd.read_excel(excel_file, sheet_name=sheet_name)
                    if not df.empty:
                        result[sheet_name] = [df]

            else:
                raise ValueError(f"Unsupported file type: {file_type}")

            return self.validate_dataframes(result)

        finally:
            # Clean up temp file
            try:
                os.unlink(file_path)
            except Exception:
                pass

    def _extract_file_id(self) -> Optional[str]:
        """Extract file ID from Google Drive URL."""
        if self._file_id:
            return self._file_id

        patterns = [
            r'drive\.google\.com/file/d/([a-zA-Z0-9_-]+)',
            r'drive\.google\.com/open\?id=([a-zA-Z0-9_-]+)',
            r'drive\.google\.com/uc\?.*id=([a-zA-Z0-9_-]+)',
            r'id=([a-zA-Z0-9_-]+)',
        ]

        for pattern in patterns:
            match = re.search(pattern, self.url)
            if match:
                self._file_id = match.group(1)
                return self._file_id

        return None

    def _download_file(self, file_id: str) -> tuple:
        """
        Download file from Google Drive.

        Returns:
            Tuple of (file_path, file_type)
        """
        # Google Drive direct download URL
        download_url = f"https://drive.google.com/uc?export=download&id={file_id}"

        try:
            session = requests.Session()

            # First request to get the file
            response = session.get(download_url, stream=True, timeout=60)

            # Check for virus scan warning (large files)
            if 'virus scan warning' in response.text.lower() or 'confirm' in response.url:
                # Try to get the confirmation token
                confirm_token = self._get_confirm_token(response)
                if confirm_token:
                    download_url = f"{download_url}&confirm={confirm_token}"
                    response = session.get(download_url, stream=True, timeout=60)

            response.raise_for_status()

            # Detect file type from content-disposition or content-type
            file_type = self._detect_file_type(response)

            # Save to temp file
            suffix = f'.{file_type}' if file_type else ''
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        tmp.write(chunk)
                tmp_path = tmp.name

            print(f"[GDriveConnector] Downloaded file (type: {file_type})")
            return tmp_path, file_type

        except requests.RequestException as e:
            raise ValueError(f"Failed to download from Google Drive: {e}")

    def _get_confirm_token(self, response) -> Optional[str]:
        """Extract confirmation token for large files."""
        for key, value in response.cookies.items():
            if key.startswith('download_warning'):
                return value
        return None

    def _detect_file_type(self, response) -> str:
        """Detect file type from response headers."""
        content_disp = response.headers.get('content-disposition', '')
        content_type = response.headers.get('content-type', '')

        # Check content-disposition for filename
        if 'filename=' in content_disp:
            match = re.search(r'filename[*]?=["\']?([^"\';\n]+)', content_disp)
            if match:
                filename = match.group(1).lower()
                if filename.endswith('.csv'):
                    return 'csv'
                elif filename.endswith('.xlsx'):
                    return 'xlsx'
                elif filename.endswith('.xls'):
                    return 'xls'

        # Check content-type
        if 'csv' in content_type or 'text/plain' in content_type:
            return 'csv'
        elif 'spreadsheet' in content_type or 'excel' in content_type:
            return 'xlsx'

        # Default to CSV for unknown types (can be parsed)
        return 'csv'
