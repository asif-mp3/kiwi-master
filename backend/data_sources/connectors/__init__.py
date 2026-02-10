"""
Data Source Connectors Package

This package contains connectors for various data sources:
- Local files and folders (highest priority)
- CSV files (local and remote)
- Excel files (.xlsx, .xls, .xlsm)
- PDF documents with table extraction
- Google Drive files and folders
- Dropbox files (shared links and API)
- OneDrive/SharePoint files

All connectors implement the BaseConnector interface with:
- Capability metadata (supports_sync, supports_folders, etc.)
- Priority-based URL matching
- Auth mode declaration

Priority Order:
1. LocalConnector (200) - Handles file:// and absolute paths
2. Cloud connectors (150) - Dropbox, OneDrive, Google Drive
3. Format connectors (100) - CSV, Excel, PDF
"""

from data_sources.connectors.csv_connector import CSVConnector
from data_sources.connectors.excel_connector import ExcelConnector
from data_sources.connectors.gdrive_connector import GoogleDriveConnector
from data_sources.connectors.gdrive_folder_connector import GoogleDriveFolderConnector

# New connectors (Sprint 1)
try:
    from data_sources.connectors.local_connector import LocalConnector
except ImportError:
    LocalConnector = None

try:
    from data_sources.connectors.pdf_connector import PDFConnector
except ImportError:
    PDFConnector = None

try:
    from data_sources.connectors.dropbox_connector import DropboxConnector
except ImportError:
    DropboxConnector = None

try:
    from data_sources.connectors.onedrive_connector import OneDriveConnector
except ImportError:
    OneDriveConnector = None

__all__ = [
    # Original connectors
    'CSVConnector',
    'ExcelConnector',
    'GoogleDriveConnector',
    'GoogleDriveFolderConnector',
    # New connectors (Sprint 1)
    'LocalConnector',
    'PDFConnector',
    'DropboxConnector',
    'OneDriveConnector',
]
