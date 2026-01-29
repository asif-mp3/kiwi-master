"""
Data Source Connectors Package

This package contains connectors for various data sources:
- CSV files (local and remote)
- Excel files (.xlsx, .xls)
- Google Drive files
- Google Drive folders (sync all files)

All connectors implement the BaseConnector interface.
"""

from data_sources.connectors.csv_connector import CSVConnector
from data_sources.connectors.excel_connector import ExcelConnector
from data_sources.connectors.gdrive_connector import GoogleDriveConnector
from data_sources.connectors.gdrive_folder_connector import GoogleDriveFolderConnector

__all__ = [
    'CSVConnector',
    'ExcelConnector',
    'GoogleDriveConnector',
    'GoogleDriveFolderConnector',
]
