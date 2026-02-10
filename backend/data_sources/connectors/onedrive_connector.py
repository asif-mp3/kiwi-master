"""
OneDrive/SharePoint Connector

Handles loading data from Microsoft OneDrive and SharePoint:
- Shared links (1drv.ms, onedrive.live.com)
- SharePoint document libraries
- Private files via Microsoft Graph API

Supports CSV and Excel files from OneDrive shared links.

Dependencies (optional for authenticated access):
- msal>=1.20.0

This is ADDITIVE code - does not modify existing functionality.
"""

import os
import re
import tempfile
from typing import Dict, List, Optional, ClassVar
from urllib.parse import urlparse, parse_qs, unquote
import pandas as pd
import requests

from data_sources.base_connector import BaseConnector

# Try to import MSAL for authentication, make it optional
try:
    from msal import ConfidentialClientApplication
    MSAL_AVAILABLE = True
except ImportError:
    MSAL_AVAILABLE = False
    ConfidentialClientApplication = None


class OneDriveConnector(BaseConnector):
    """
    Connector for OneDrive and SharePoint files.

    Supports:
    - Short links: https://1drv.ms/x/xxxxx
    - OneDrive links: https://onedrive.live.com/...
    - SharePoint links: https://company.sharepoint.com/...

    Auth Options:
    1. Public shared links -> No auth needed (common case)
    2. Private files -> Microsoft Graph API via MSAL

    Note: Many OneDrive shared links can be converted to direct download URLs
    without authentication.
    """

    # Capability metadata
    supports_sync: ClassVar[bool] = True
    supports_folders: ClassVar[bool] = True
    supports_preview: ClassVar[bool] = False
    supports_streaming: ClassVar[bool] = False
    auth_mode: ClassVar[str] = "anonymous"  # Anonymous for shared links
    required_credentials: ClassVar[List[str]] = []  # OAuth optional
    priority: ClassVar[int] = 150  # Higher than file-type connectors

    # Supported file extensions
    SUPPORTED_EXTENSIONS = ['.csv', '.xlsx', '.xls', '.xlsm', '.pdf']

    def __init__(self, url: str, credentials: Optional[Dict] = None):
        super().__init__(url, credentials)

        # Microsoft Graph API credentials (optional)
        self.client_id = None
        self.client_secret = None
        self.tenant_id = None
        self.access_token = None

        if credentials:
            self.client_id = credentials.get('client_id')
            self.client_secret = credentials.get('client_secret')
            self.tenant_id = credentials.get('tenant_id')
            self.access_token = credentials.get('access_token')

        # Environment variable fallbacks
        if not self.client_id:
            self.client_id = os.getenv('MICROSOFT_CLIENT_ID')
        if not self.client_secret:
            self.client_secret = os.getenv('MICROSOFT_CLIENT_SECRET')
        if not self.tenant_id:
            self.tenant_id = os.getenv('MICROSOFT_TENANT_ID')

    @classmethod
    def can_handle(cls, url: str) -> bool:
        """Check if this connector can handle the URL."""
        if not url:
            return False

        url_lower = url.lower()

        # Short OneDrive links
        if '1drv.ms' in url_lower:
            return True

        # OneDrive personal
        if 'onedrive.live.com' in url_lower:
            return True

        # OneDrive for Business / SharePoint
        if 'sharepoint.com' in url_lower:
            return True

        # Direct OneDrive download links
        if 'onedrive.com' in url_lower:
            return True

        return False

    def get_source_name(self) -> str:
        """Get human-readable name for this data source."""
        if self.source_name:
            return self.source_name

        parsed = urlparse(self.url)
        path = parsed.path

        # Get filename from path
        filename = os.path.basename(path)

        # URL decode the filename
        filename = unquote(filename)

        # Remove query parameters
        if '?' in filename:
            filename = filename.split('?')[0]

        if filename:
            name, _ = os.path.splitext(filename)
            self.source_name = name or 'OneDrive_File'
        else:
            self.source_name = 'OneDrive_File'

        return self.source_name

    def fetch_tables(self) -> Dict[str, List[pd.DataFrame]]:
        """
        Fetch data from OneDrive/SharePoint.

        Returns:
            Dict mapping table names to DataFrames
        """
        # Try to resolve shared link to direct download URL
        try:
            direct_url = self._resolve_share_link()
            return self._fetch_from_url(direct_url)
        except Exception as e:
            print(f"[OneDriveConnector] Shared link resolution failed: {e}")

            # Fall back to Graph API if credentials available
            if self.access_token or (self.client_id and self.client_secret):
                return self._fetch_via_api()
            else:
                raise ValueError(
                    f"Could not access OneDrive file. Error: {e}\n"
                    "For private files, provide Microsoft Graph API credentials."
                )

    def _resolve_share_link(self) -> str:
        """
        Resolve OneDrive shared link to direct download URL.

        OneDrive uses base64-encoded sharing tokens that can be converted
        to direct download URLs.
        """
        url = self.url

        # Handle 1drv.ms short links - follow redirects
        if '1drv.ms' in url:
            try:
                response = requests.head(
                    url,
                    allow_redirects=True,
                    timeout=10
                )
                url = response.url
                print(f"[OneDriveConnector] Resolved short URL to: {url}")
            except Exception as e:
                print(f"[OneDriveConnector] Warning: Could not resolve short URL: {e}")

        # Try to convert to download URL
        download_url = self._convert_to_download_url(url)

        return download_url

    def _convert_to_download_url(self, url: str) -> str:
        """
        Convert OneDrive/SharePoint URL to direct download URL.

        The technique involves encoding the share URL in base64 and
        using the Graph API sharing endpoint format.
        """
        import base64

        # Clean up URL
        url = url.strip()

        # If already a download URL, return as-is
        if 'download=1' in url or 'download.aspx' in url:
            return url

        # Add download=1 parameter for SharePoint URLs
        if 'sharepoint.com' in url:
            parsed = urlparse(url)
            query = parse_qs(parsed.query)

            # Add download parameter
            if 'download' not in query:
                separator = '&' if parsed.query else '?'
                return f"{url}{separator}download=1"
            return url

        # For OneDrive personal, try to modify the resid parameter
        if 'onedrive.live.com' in url:
            # Try to extract and modify the share link
            parsed = urlparse(url)
            query = parse_qs(parsed.query)

            if 'resid' in query:
                resid = query['resid'][0]
                # Construct download URL
                return f"https://onedrive.live.com/download?resid={resid}"

        # As a fallback, try the sharing token approach
        # Encode URL to sharing token format
        try:
            encoded = base64.b64encode(url.encode()).decode()
            # OneDrive uses a modified base64 format
            sharing_token = "u!" + encoded.rstrip('=').replace('/', '_').replace('+', '-')

            # This creates a Graph API compatible sharing URL
            # But requires authentication for private files
            return url  # Return original if we can't convert

        except Exception:
            return url

    def _fetch_from_url(self, url: str) -> Dict[str, List[pd.DataFrame]]:
        """
        Fetch file from URL (resolved share link or direct download).
        """
        print(f"[OneDriveConnector] Fetching from: {url}")

        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }

            response = requests.get(
                url,
                headers=headers,
                timeout=60,
                allow_redirects=True
            )
            response.raise_for_status()

            # Determine file type
            content_disposition = response.headers.get('Content-Disposition', '')
            filename_match = re.search(r'filename\*?=(?:UTF-8\'\')?\"?([^";\n]+)\"?', content_disposition)

            if filename_match:
                filename = unquote(filename_match.group(1))
            else:
                # Try from URL
                parsed = urlparse(response.url)
                filename = os.path.basename(parsed.path)
                filename = unquote(filename)

            if not filename or filename == '/':
                filename = 'download.xlsx'  # Default assumption

            # Detect file type
            content_type = response.headers.get('Content-Type', '').lower()
            suffix = self._get_suffix(filename.lower(), content_type)

            # Save to temp file
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                tmp.write(response.content)
                temp_path = tmp.name

            try:
                return self._process_file(temp_path, filename)
            finally:
                try:
                    os.unlink(temp_path)
                except Exception:
                    pass

        except requests.RequestException as e:
            raise ValueError(f"Failed to download from OneDrive: {e}")

    def _get_suffix(self, filename: str, content_type: str) -> str:
        """Determine file suffix from filename or content type."""
        for ext in self.SUPPORTED_EXTENSIONS:
            if filename.endswith(ext):
                return ext

        # Fallback to content type
        if 'csv' in content_type or 'text/plain' in content_type:
            return '.csv'
        elif 'spreadsheet' in content_type or 'excel' in content_type:
            return '.xlsx'
        elif 'pdf' in content_type:
            return '.pdf'

        # Default to xlsx for OneDrive (common case)
        return '.xlsx'

    def _process_file(self, file_path: str, original_name: str) -> Dict[str, List[pd.DataFrame]]:
        """Process downloaded file based on its type."""
        _, ext = os.path.splitext(file_path.lower())

        # Update source name
        name, _ = os.path.splitext(original_name)
        if name:
            self.source_name = name

        if ext == '.csv':
            return self._load_csv(file_path)
        elif ext in ('.xlsx', '.xls', '.xlsm'):
            return self._load_excel(file_path)
        elif ext == '.pdf':
            return self._load_pdf(file_path)
        else:
            # Try as Excel (common for OneDrive)
            try:
                return self._load_excel(file_path)
            except Exception:
                raise ValueError(f"Unsupported file type: {ext}")

    def _load_csv(self, file_path: str) -> Dict[str, List[pd.DataFrame]]:
        """Load CSV file."""
        encodings = ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252']

        for encoding in encodings:
            try:
                df = pd.read_csv(file_path, encoding=encoding)
                source_name = self.get_source_name()
                print(f"[OneDriveConnector] Loaded CSV: {len(df)} rows")
                return self.validate_dataframes({source_name: [df]})
            except UnicodeDecodeError:
                continue

        raise ValueError("Could not decode CSV file")

    def _load_excel(self, file_path: str) -> Dict[str, List[pd.DataFrame]]:
        """Load Excel file."""
        try:
            excel_file = pd.ExcelFile(file_path)
            result = {}

            for sheet_name in excel_file.sheet_names:
                df = pd.read_excel(excel_file, sheet_name=sheet_name)
                if not df.empty:
                    result[sheet_name] = [df]
                    print(f"[OneDriveConnector] Loaded sheet '{sheet_name}': {len(df)} rows")

            return self.validate_dataframes(result)

        except Exception as e:
            raise ValueError(f"Failed to read Excel file: {e}")

    def _load_pdf(self, file_path: str) -> Dict[str, List[pd.DataFrame]]:
        """Load PDF file with table extraction."""
        try:
            from data_sources.connectors.pdf_connector import PDFConnector
            connector = PDFConnector(file_path)
            return connector.fetch_tables()
        except ImportError:
            raise ValueError("PDF support requires pdfplumber. Install with: pip install pdfplumber")

    def _fetch_via_api(self) -> Dict[str, List[pd.DataFrame]]:
        """
        Fetch file via Microsoft Graph API.

        Requires either an access_token directly or client credentials
        for authentication.
        """
        if not MSAL_AVAILABLE and not self.access_token:
            raise ImportError(
                "MSAL required for API access. "
                "Install with: pip install msal>=1.20.0"
            )

        # Get access token if not provided
        token = self.access_token
        if not token:
            token = self._get_access_token()

        # Extract drive item info from URL and make Graph API call
        # This is a simplified implementation - full Graph API integration
        # would require more URL parsing and API calls
        raise NotImplementedError(
            "Full Microsoft Graph API integration not yet implemented. "
            "Please use a public shared link or provide a direct download URL."
        )

    def _get_access_token(self) -> str:
        """Get access token using client credentials."""
        if not self.client_id or not self.client_secret or not self.tenant_id:
            raise ValueError(
                "Microsoft Graph API credentials required. "
                "Set MICROSOFT_CLIENT_ID, MICROSOFT_CLIENT_SECRET, and MICROSOFT_TENANT_ID "
                "environment variables."
            )

        authority = f"https://login.microsoftonline.com/{self.tenant_id}"
        app = ConfidentialClientApplication(
            self.client_id,
            authority=authority,
            client_credential=self.client_secret
        )

        result = app.acquire_token_for_client(
            scopes=["https://graph.microsoft.com/.default"]
        )

        if "access_token" in result:
            return result["access_token"]
        else:
            raise ValueError(f"Failed to get access token: {result.get('error_description')}")
