"""
Connector Factory

Factory for creating appropriate data source connectors based on URL.
Includes URL detection to route to the correct connector.

This is ADDITIVE code - does not modify existing Google Sheets functionality.
Google Sheets URLs are detected and routed to EXISTING code path.
"""

import re
from typing import Optional, Type, List
from data_sources.base_connector import BaseConnector


# Registry of available connectors
_connector_registry: List[Type[BaseConnector]] = []


def register_connector(connector_class: Type[BaseConnector]):
    """
    Register a connector class with the factory.

    Args:
        connector_class: Connector class to register
    """
    if connector_class not in _connector_registry:
        _connector_registry.append(connector_class)


def is_google_sheets_url(url: str) -> bool:
    """
    Check if URL is a Google Sheets URL.

    These URLs should be handled by the EXISTING Google Sheets code path,
    not the new connector system.

    Args:
        url: URL to check

    Returns:
        True if it's a Google Sheets URL
    """
    if not url:
        return False

    patterns = [
        r'docs\.google\.com/spreadsheets/d/',
        r'sheets\.google\.com/',
        r'^[a-zA-Z0-9_-]{44}$',  # Just a spreadsheet ID
    ]

    for pattern in patterns:
        if re.search(pattern, url):
            return True

    return False


def is_google_drive_url(url: str) -> bool:
    """
    Check if URL is a Google Drive file URL (not Sheets).

    Args:
        url: URL to check

    Returns:
        True if it's a Google Drive URL
    """
    if not url:
        return False

    patterns = [
        r'drive\.google\.com/file/d/',
        r'drive\.google\.com/open\?id=',
        r'drive\.google\.com/uc\?',
    ]

    for pattern in patterns:
        if re.search(pattern, url):
            return True

    return False


def detect_source_type(url: str) -> str:
    """
    Detect the type of data source from URL.

    Args:
        url: URL to analyze

    Returns:
        Source type: 'google_sheets', 'google_drive', 'csv', 'excel', 'unknown'
    """
    if not url:
        return 'unknown'

    url_lower = url.lower()

    # Check Google Sheets first (uses existing code path)
    if is_google_sheets_url(url):
        return 'google_sheets'

    # Check Google Drive
    if is_google_drive_url(url):
        return 'google_drive'

    # Check file extensions
    if url_lower.endswith('.csv'):
        return 'csv'

    if url_lower.endswith(('.xlsx', '.xls', '.xlsm')):
        return 'excel'

    # Check content-type hints in URL
    if 'format=csv' in url_lower or 'output=csv' in url_lower:
        return 'csv'

    return 'unknown'


class ConnectorFactory:
    """
    Factory for creating data source connectors.

    Usage:
        connector = ConnectorFactory.create(url)
        tables = connector.fetch_tables()
    """

    @staticmethod
    def create(url: str) -> BaseConnector:
        """
        Create appropriate connector for the given URL.

        Args:
            url: Data source URL

        Returns:
            Appropriate connector instance

        Raises:
            ValueError: If no connector can handle the URL
        """
        # Check registered connectors
        for connector_class in _connector_registry:
            if connector_class.can_handle(url):
                return connector_class(url)

        # If no connector found, provide helpful error
        source_type = detect_source_type(url)

        if source_type == 'google_sheets':
            raise ValueError(
                "Google Sheets URLs should use the existing load_dataset_service() function, "
                "not the connector factory. This is by design to preserve existing functionality."
            )

        raise ValueError(
            f"No connector available for URL: {url}\n"
            f"Detected type: {source_type}\n"
            f"Supported: CSV files, Excel files (.xlsx, .xls), Google Drive files"
        )

    @staticmethod
    def get_supported_types() -> List[str]:
        """
        Get list of supported data source types.

        Returns:
            List of type names
        """
        types = ['csv', 'excel', 'google_drive']
        return types

    @staticmethod
    def can_handle(url: str) -> bool:
        """
        Check if any connector can handle this URL.

        Note: Returns False for Google Sheets URLs since those
        use the existing code path.

        Args:
            url: URL to check

        Returns:
            True if a connector is available
        """
        # Google Sheets uses existing code path
        if is_google_sheets_url(url):
            return False

        for connector_class in _connector_registry:
            if connector_class.can_handle(url):
                return True

        return False


# Import and register connectors when this module is loaded
def _register_all_connectors():
    """Register all available connectors."""
    try:
        from data_sources.connectors.csv_connector import CSVConnector
        register_connector(CSVConnector)
    except ImportError:
        pass

    try:
        from data_sources.connectors.excel_connector import ExcelConnector
        register_connector(ExcelConnector)
    except ImportError:
        pass

    try:
        from data_sources.connectors.gdrive_connector import GoogleDriveConnector
        register_connector(GoogleDriveConnector)
    except ImportError:
        pass


# Register connectors on module load
_register_all_connectors()
