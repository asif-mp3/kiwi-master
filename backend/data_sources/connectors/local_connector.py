"""
Local Filesystem Connector

Handles loading data from local files and folders:
- Single files: CSV, Excel, PDF
- Folders: Recursively scan for supported files
- Security: Path traversal prevention, configurable allowed directories

This connector has the highest priority (200) to ensure local paths
are always handled correctly.
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Optional, ClassVar
import pandas as pd

from data_sources.base_connector import BaseConnector


class SecurityError(Exception):
    """Raised when a security violation is detected."""
    pass


class LocalConnector(BaseConnector):
    """
    Connector for local files and folders.

    Supports:
    - file:// URLs: file:///C:/Data/sales.csv
    - Absolute paths: C:\\Data\\sales.xlsx or /home/user/data.csv
    - Folder scanning: Recursively finds all supported files

    Security:
    - Path traversal prevention
    - Configurable allowed base directories
    - Real path validation
    """

    # Capability metadata
    supports_sync: ClassVar[bool] = True
    supports_folders: ClassVar[bool] = True
    supports_preview: ClassVar[bool] = False
    supports_streaming: ClassVar[bool] = False
    auth_mode: ClassVar[str] = "anonymous"
    required_credentials: ClassVar[List[str]] = []
    priority: ClassVar[int] = 200  # Highest priority for local paths

    # Supported file extensions
    SUPPORTED_EXTENSIONS = ['.csv', '.xlsx', '.xls', '.xlsm', '.pdf']

    # Configurable base directory restriction
    # Set via environment variable or override in subclass
    ALLOWED_BASE_DIRS: ClassVar[List[str]] = []

    def __init__(self, url: str, credentials: Optional[Dict] = None):
        super().__init__(url, credentials)
        self._initialize_allowed_dirs()

    def _initialize_allowed_dirs(self) -> None:
        """Initialize allowed directories from environment or defaults."""
        if not self.ALLOWED_BASE_DIRS:
            # Default allowed directories
            self.ALLOWED_BASE_DIRS = [
                os.getenv("DATA_DIR", ""),
                os.path.expanduser("~/Documents"),
                os.path.expanduser("~/Downloads"),
                os.path.expanduser("~/Desktop"),
            ]
            # Filter out empty strings
            self.ALLOWED_BASE_DIRS = [d for d in self.ALLOWED_BASE_DIRS if d]

    @classmethod
    def can_handle(cls, url: str) -> bool:
        """
        Check if this connector can handle the URL.

        Handles:
        - file:// URLs
        - Absolute paths (Unix and Windows)
        - Paths starting with ~ (home directory)
        """
        if not url:
            return False

        # file:// URLs
        if url.startswith('file://'):
            return True

        # Windows absolute paths: C:\, D:\, etc.
        if len(url) >= 2 and url[1] == ':':
            return True

        # Unix absolute paths
        if url.startswith('/'):
            return True

        # Home directory paths
        if url.startswith('~'):
            return True

        return False

    def get_source_name(self) -> str:
        """Get human-readable name for this data source."""
        if self.source_name:
            return self.source_name

        path = self._normalize_path(self.url)

        if os.path.isdir(path):
            # Use folder name
            self.source_name = os.path.basename(path) or "Local_Folder"
        else:
            # Use filename without extension
            filename = os.path.basename(path)
            name, _ = os.path.splitext(filename)
            self.source_name = name or "Local_File"

        return self.source_name

    def fetch_tables(self) -> Dict[str, List[pd.DataFrame]]:
        """
        Fetch data from local file or folder.

        For single files: Delegates to appropriate connector (CSV, Excel, PDF)
        For folders: Scans recursively and loads all supported files

        Returns:
            Dict mapping file/table names to lists of DataFrames
        """
        path = self._normalize_path(self.url)

        # Validate path security
        self._validate_path(path)

        if os.path.isdir(path):
            return self._scan_folder(path)
        elif os.path.isfile(path):
            return self._process_file(path)
        else:
            raise ValueError(f"Path not found: {path}")

    def _normalize_path(self, url: str) -> str:
        """Normalize URL/path to absolute file path."""
        path = url

        # Handle file:// prefix
        if path.startswith('file://'):
            path = path[7:]
            # Handle Windows paths like file:///C:/
            if len(path) >= 3 and path[0] == '/' and path[2] == ':':
                path = path[1:]  # Remove leading /

        # Expand ~ to home directory
        if path.startswith('~'):
            path = os.path.expanduser(path)

        # Normalize path separators and resolve ..
        path = os.path.normpath(path)

        return path

    def _validate_path(self, path: str) -> str:
        """
        Validate path for security.

        Prevents:
        - Path traversal attacks (../)
        - Access outside allowed directories

        Args:
            path: Normalized absolute path

        Returns:
            Validated real path

        Raises:
            SecurityError: If path is outside allowed directories
        """
        # Resolve to real path (follows symlinks)
        real_path = os.path.realpath(path)

        # If no allowed directories configured, allow all paths
        if not self.ALLOWED_BASE_DIRS:
            return real_path

        # Check against allowed directories
        for allowed in self.ALLOWED_BASE_DIRS:
            if not allowed:
                continue
            allowed_real = os.path.realpath(allowed)
            if real_path.startswith(allowed_real):
                return real_path

        raise SecurityError(
            f"Access denied: {path} is outside allowed directories.\n"
            f"Allowed: {self.ALLOWED_BASE_DIRS}"
        )

    def _scan_folder(self, folder_path: str) -> Dict[str, List[pd.DataFrame]]:
        """
        Recursively scan folder for supported files.

        Args:
            folder_path: Absolute path to folder

        Returns:
            Dict mapping relative file paths to DataFrames
        """
        result = {}
        folder_path = Path(folder_path)

        print(f"[LocalConnector] Scanning folder: {folder_path}")

        for ext in self.SUPPORTED_EXTENSIONS:
            for file_path in folder_path.rglob(f"*{ext}"):
                try:
                    # Use relative path as table name
                    rel_path = file_path.relative_to(folder_path)
                    table_name = str(rel_path).replace(os.sep, "_").replace(".", "_")

                    # Remove extension from name
                    name, _ = os.path.splitext(table_name)

                    file_result = self._process_file(str(file_path))

                    # Merge results with unique names
                    for key, dfs in file_result.items():
                        unique_key = f"{name}_{key}" if key != name else name
                        result[unique_key] = dfs

                except Exception as e:
                    print(f"[LocalConnector] Error processing {file_path}: {e}")
                    continue

        print(f"[LocalConnector] Found {len(result)} tables in folder")
        return self.validate_dataframes(result)

    def _process_file(self, file_path: str) -> Dict[str, List[pd.DataFrame]]:
        """
        Process a single file by delegating to appropriate connector.

        Args:
            file_path: Absolute path to file

        Returns:
            Dict mapping table names to DataFrames
        """
        _, ext = os.path.splitext(file_path.lower())

        if ext == '.csv':
            return self._load_csv(file_path)
        elif ext in ('.xlsx', '.xls', '.xlsm'):
            return self._load_excel(file_path)
        elif ext == '.pdf':
            return self._load_pdf(file_path)
        else:
            raise ValueError(f"Unsupported file type: {ext}")

    def _load_csv(self, file_path: str) -> Dict[str, List[pd.DataFrame]]:
        """Load CSV file."""
        from data_sources.connectors.csv_connector import CSVConnector

        connector = CSVConnector(file_path)
        return connector.fetch_tables()

    def _load_excel(self, file_path: str) -> Dict[str, List[pd.DataFrame]]:
        """Load Excel file."""
        from data_sources.connectors.excel_connector import ExcelConnector

        connector = ExcelConnector(file_path)
        return connector.fetch_tables()

    def _load_pdf(self, file_path: str) -> Dict[str, List[pd.DataFrame]]:
        """Load PDF file with table extraction."""
        try:
            from data_sources.connectors.pdf_connector import PDFConnector
            connector = PDFConnector(file_path)
            return connector.fetch_tables()
        except ImportError:
            print(f"[LocalConnector] PDFConnector not available, skipping {file_path}")
            return {}
        except Exception as e:
            print(f"[LocalConnector] Error loading PDF {file_path}: {e}")
            return {}
