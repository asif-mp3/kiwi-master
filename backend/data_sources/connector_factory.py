"""
Connector Factory

Factory for creating appropriate data source connectors based on URL.
Includes URL detection to route to the correct connector with priority-based routing.

This is ADDITIVE code - does not modify existing Google Sheets functionality.
Google Sheets URLs are detected and routed to EXISTING code path.

Priority-Based Routing:
- Each connector has a priority (higher wins)
- LocalConnector: 200 (highest - handles file:// and absolute paths)
- Cloud connectors: 150 (Dropbox, OneDrive, Google Drive)
- Format connectors: 100 (CSV, Excel, PDF)

This ensures that local paths are always handled correctly, and cloud URLs
take precedence over format-based detection.
"""

import re
from typing import Optional, Type, List, Dict, Tuple
from data_sources.base_connector import BaseConnector


class UnsupportedSourceError(ValueError):
    """Raised when no connector can handle the given URL."""
    pass


class AmbiguousConnectorError(ValueError):
    """Raised when multiple connectors match with the same priority."""
    pass


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
        print(f"[ConnectorFactory] Registered: {connector_class.__name__} (priority={getattr(connector_class, 'priority', 100)})")


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

    Uses priority-based routing to select the best connector for a URL.
    Higher priority connectors are preferred when multiple match.

    Usage:
        connector = ConnectorFactory.create(url)
        tables = connector.fetch_tables()

        # With credentials
        connector = ConnectorFactory.create(url, credentials={"access_token": "..."})
    """

    @staticmethod
    def create(url: str, credentials: Optional[Dict] = None) -> BaseConnector:
        """
        Create appropriate connector for the given URL.

        Uses priority-based routing - higher priority connectors are preferred
        when multiple connectors can handle the same URL.

        Args:
            url: Data source URL
            credentials: Optional dict of credentials for authenticated sources

        Returns:
            Appropriate connector instance

        Raises:
            UnsupportedSourceError: If no connector can handle the URL
            AmbiguousConnectorError: If multiple connectors match with same priority
        """
        # Find all matching connectors with their priorities
        matches: List[Tuple[int, Type[BaseConnector]]] = []

        for connector_class in _connector_registry:
            if connector_class.can_handle(url):
                priority = getattr(connector_class, 'priority', 100)
                matches.append((priority, connector_class))

        if not matches:
            # If no connector found, provide helpful error
            source_type = detect_source_type(url)

            if source_type == 'google_sheets':
                raise ValueError(
                    "Google Sheets URLs should use the existing load_dataset_service() function, "
                    "not the connector factory. This is by design to preserve existing functionality."
                )

            raise UnsupportedSourceError(
                f"No connector available for URL: {url}\n"
                f"Detected type: {source_type}\n"
                f"Supported: Local files, CSV, Excel, PDF, Google Drive, Dropbox, OneDrive"
            )

        # Sort by priority (highest first)
        matches.sort(key=lambda x: x[0], reverse=True)

        # Check for ambiguous matches (same priority)
        if len(matches) > 1 and matches[0][0] == matches[1][0]:
            # Log warning but proceed with first match
            print(
                f"[ConnectorFactory] Warning: Multiple connectors match with same priority: "
                f"{[m[1].__name__ for m in matches[:2]]}"
            )

        # Use highest priority connector
        selected_class = matches[0][1]
        print(f"[ConnectorFactory] Selected: {selected_class.__name__} for {url[:50]}...")

        return selected_class(url, credentials)

    @staticmethod
    def get_supported_types() -> List[str]:
        """
        Get list of supported data source types.

        Returns:
            List of type names
        """
        types = [
            'local',        # Local files and folders
            'csv',          # CSV files
            'excel',        # Excel files (.xlsx, .xls, .xlsm)
            'pdf',          # PDF documents with tables
            'google_drive', # Google Drive files
            'dropbox',      # Dropbox files and folders
            'onedrive',     # OneDrive/SharePoint files
        ]
        return types

    @staticmethod
    def get_registered_connectors() -> List[Dict]:
        """
        Get info about all registered connectors.

        Returns:
            List of connector info dicts
        """
        connectors = []
        for cls in _connector_registry:
            connectors.append({
                'name': cls.__name__,
                'priority': getattr(cls, 'priority', 100),
                'auth_mode': getattr(cls, 'auth_mode', 'anonymous'),
                'supports_sync': getattr(cls, 'supports_sync', True),
                'supports_folders': getattr(cls, 'supports_folders', False),
            })
        # Sort by priority
        connectors.sort(key=lambda x: x['priority'], reverse=True)
        return connectors

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
    """
    Register all available connectors.

    Connectors are registered in order of priority (highest first).
    This ensures that when the factory is queried, higher priority
    connectors are checked first.
    """
    # Priority 200: Local filesystem (highest - handles file:// and absolute paths)
    try:
        from data_sources.connectors.local_connector import LocalConnector
        register_connector(LocalConnector)
    except ImportError as e:
        print(f"[ConnectorFactory] LocalConnector not available: {e}")

    # Priority 150: Cloud storage connectors
    try:
        from data_sources.connectors.dropbox_connector import DropboxConnector
        register_connector(DropboxConnector)
    except ImportError as e:
        print(f"[ConnectorFactory] DropboxConnector not available: {e}")

    try:
        from data_sources.connectors.onedrive_connector import OneDriveConnector
        register_connector(OneDriveConnector)
    except ImportError as e:
        print(f"[ConnectorFactory] OneDriveConnector not available: {e}")

    try:
        from data_sources.connectors.gdrive_connector import GoogleDriveConnector
        register_connector(GoogleDriveConnector)
    except ImportError as e:
        print(f"[ConnectorFactory] GoogleDriveConnector not available: {e}")

    # Priority 100: Format-specific connectors
    try:
        from data_sources.connectors.csv_connector import CSVConnector
        register_connector(CSVConnector)
    except ImportError as e:
        print(f"[ConnectorFactory] CSVConnector not available: {e}")

    try:
        from data_sources.connectors.excel_connector import ExcelConnector
        register_connector(ExcelConnector)
    except ImportError as e:
        print(f"[ConnectorFactory] ExcelConnector not available: {e}")

    try:
        from data_sources.connectors.pdf_connector import PDFConnector
        register_connector(PDFConnector)
    except ImportError as e:
        print(f"[ConnectorFactory] PDFConnector not available (install pdfplumber): {e}")

    print(f"[ConnectorFactory] Registered {len(_connector_registry)} connectors")


# Register connectors on module load
_register_all_connectors()
