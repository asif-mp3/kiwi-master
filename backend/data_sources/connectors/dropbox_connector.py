"""
Dropbox Connector

Handles loading data from Dropbox:
- Shared links (public, no auth needed)
- Private files via API (requires access token)

Supports CSV and Excel files from Dropbox shared links.

Dependencies (optional for authenticated access):
- dropbox>=11.0.0

This is ADDITIVE code - does not modify existing functionality.
"""

import os
import re
import tempfile
from typing import Dict, List, Optional, ClassVar
from urllib.parse import urlparse, parse_qs
import pandas as pd
import requests

from data_sources.base_connector import BaseConnector
from utils.logger import get_logger

logger = get_logger("dropbox_connector")

# Try to import dropbox SDK, make it optional for shared links
try:
    import dropbox
    DROPBOX_SDK_AVAILABLE = True
except ImportError:
    DROPBOX_SDK_AVAILABLE = False
    dropbox = None


class DropboxConnector(BaseConnector):
    """
    Connector for Dropbox files and folders.

    Supports:
    - Public shared links: https://www.dropbox.com/s/xxx/file.xlsx
    - Folder shared links: https://www.dropbox.com/sh/xxx/folder
    - Private files via API (requires DROPBOX_ACCESS_TOKEN)

    Auth Options:
    1. Public shared links -> No auth needed (most common)
    2. Private files -> Dropbox access token via environment variable
    """

    # Capability metadata
    supports_sync: ClassVar[bool] = True
    supports_folders: ClassVar[bool] = True
    supports_preview: ClassVar[bool] = False
    supports_streaming: ClassVar[bool] = False
    auth_mode: ClassVar[str] = "anonymous"  # Anonymous for shared links, oauth for private
    required_credentials: ClassVar[List[str]] = []  # Token optional
    priority: ClassVar[int] = 150  # Higher than file-type connectors

    # Supported file extensions
    SUPPORTED_EXTENSIONS = ['.csv', '.xlsx', '.xls', '.xlsm', '.pdf']

    def __init__(self, url: str, credentials: Optional[Dict] = None):
        super().__init__(url, credentials)

        # Get access token from credentials or environment
        self.access_token = None
        if credentials and 'access_token' in credentials:
            self.access_token = credentials['access_token']
        elif os.getenv('DROPBOX_ACCESS_TOKEN'):
            self.access_token = os.getenv('DROPBOX_ACCESS_TOKEN')

    @classmethod
    def can_handle(cls, url: str) -> bool:
        """Check if this connector can handle the URL."""
        if not url:
            return False

        url_lower = url.lower()

        # Dropbox shared links
        if 'dropbox.com/s/' in url_lower:
            return True
        if 'dropbox.com/sh/' in url_lower:
            return True
        if 'dropbox.com/scl/' in url_lower:
            return True

        # dl.dropboxusercontent.com direct download links
        if 'dropboxusercontent.com' in url_lower:
            return True

        return False

    def get_source_name(self) -> str:
        """Get human-readable name for this data source."""
        if self.source_name:
            return self.source_name

        # Try to extract filename from URL
        parsed = urlparse(self.url)
        path = parsed.path

        # Get last path component
        filename = os.path.basename(path)

        # Remove query parameters from filename
        if '?' in filename:
            filename = filename.split('?')[0]

        # Remove extension for name
        if filename:
            name, _ = os.path.splitext(filename)
            self.source_name = name or 'Dropbox_File'
        else:
            self.source_name = 'Dropbox_File'

        return self.source_name

    def fetch_tables(self) -> Dict[str, List[pd.DataFrame]]:
        """
        Fetch data from Dropbox.

        Returns:
            Dict mapping table names to DataFrames
        """
        if self._is_shared_link():
            return self._fetch_shared_link()
        else:
            return self._fetch_via_api()

    def _is_shared_link(self) -> bool:
        """Check if URL is a Dropbox shared link."""
        url_lower = self.url.lower()
        return (
            'dropbox.com/s/' in url_lower or
            'dropbox.com/sh/' in url_lower or
            'dropbox.com/scl/' in url_lower or
            'dropboxusercontent.com' in url_lower
        )

    def _get_direct_download_url(self) -> str:
        """
        Convert Dropbox shared link to direct download URL.

        Dropbox shared links with ?dl=0 show a preview page.
        Changing to ?dl=1 or using raw=1 gives direct download.
        """
        url = self.url

        # Already a direct download link
        if 'dropboxusercontent.com' in url:
            return url

        # Parse URL
        parsed = urlparse(url)
        query = parse_qs(parsed.query)

        # Remove dl=0 or set dl=1
        if 'dl' in query:
            query['dl'] = ['1']
        else:
            query['dl'] = ['1']

        # Reconstruct URL
        query_string = '&'.join(f"{k}={v[0]}" for k, v in query.items())
        direct_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
        if query_string:
            direct_url += f"?{query_string}"

        return direct_url

    def _fetch_shared_link(self) -> Dict[str, List[pd.DataFrame]]:
        """
        Fetch file or folder from Dropbox shared link.

        No authentication needed for public shared links.
        Handles both single files and folders (ZIP downloads).
        Includes retry with exponential backoff for transient failures.
        """
        import time
        import zipfile

        direct_url = self._get_direct_download_url()
        logger.info("Fetching from: %s", direct_url)

        max_retries = 3
        last_error = None
        response = None

        for attempt in range(max_retries):
            try:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (compatible; TharaAI/1.0)'
                }

                response = requests.get(
                    direct_url,
                    headers=headers,
                    timeout=120,
                    allow_redirects=True
                )
                response.raise_for_status()
                break  # Success
            except requests.RequestException as e:
                last_error = e
                if attempt < max_retries - 1:
                    wait = (attempt + 1) * 2  # 2s, 4s
                    logger.warning("Dropbox download attempt %d failed, retrying in %ds: %s", attempt + 1, wait, e)
                    time.sleep(wait)
                else:
                    raise ValueError(f"Failed to download from Dropbox after {max_retries} attempts: {last_error}")

        if response is None:
            raise ValueError("Failed to download from Dropbox")

        content_type = response.headers.get('Content-Type', '').lower()

        # Check if response is a ZIP (Dropbox sends ZIP for folder downloads)
        is_zip = (
            'zip' in content_type
            or response.content[:4] == b'PK\x03\x04'  # ZIP magic bytes
        )

        if is_zip:
            logger.info("Dropbox returned ZIP (folder download), extracting files...")
            return self._process_zip(response.content)

        # Single file — determine file type from Content-Disposition or URL
        content_disposition = response.headers.get('Content-Disposition', '')
        filename_match = re.search(r'filename="?([^";\n]+)"?', content_disposition)

        if filename_match:
            filename = filename_match.group(1)
        else:
            filename = os.path.basename(urlparse(self.url).path)

        filename_lower = filename.lower()
        suffix = self._get_suffix(filename_lower, content_type)

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

    def _process_zip(self, zip_bytes: bytes) -> Dict[str, List[pd.DataFrame]]:
        """
        Extract and process files from a ZIP archive (Dropbox folder download).
        Returns combined results from all supported files.
        """
        import zipfile
        import io

        all_results: Dict[str, List[pd.DataFrame]] = {}

        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            file_list = [f for f in zf.namelist() if not f.endswith('/')]
            logger.info("ZIP contains %d files: %s", len(file_list), file_list[:10])

            for zip_entry in file_list:
                filename = os.path.basename(zip_entry)
                filename_lower = filename.lower()

                # Skip hidden/system files
                if filename.startswith('.') or filename.startswith('__'):
                    continue

                # Only process supported file types
                ext = os.path.splitext(filename_lower)[1]
                if ext not in self.SUPPORTED_EXTENSIONS:
                    logger.info("Skipping unsupported file in ZIP: %s", filename)
                    continue

                logger.info("Processing ZIP entry: %s", zip_entry)

                with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
                    tmp.write(zf.read(zip_entry))
                    temp_path = tmp.name

                try:
                    file_results = self._process_file(temp_path, filename)
                    all_results.update(file_results)
                except Exception as e:
                    logger.warning("Failed to process %s from ZIP: %s", filename, e)
                finally:
                    try:
                        os.unlink(temp_path)
                    except Exception:
                        pass

        if not all_results:
            raise ValueError(
                "No supported data files found in Dropbox folder. "
                "Supported formats: CSV, Excel (.xlsx/.xls/.xlsm), PDF"
            )

        logger.info("Extracted %d tables from Dropbox folder ZIP", len(all_results))
        return all_results

    def _get_suffix(self, filename: str, content_type: str) -> str:
        """Determine file suffix from filename or content type."""
        for ext in self.SUPPORTED_EXTENSIONS:
            if filename.endswith(ext):
                return ext

        # Fallback to content type
        if 'csv' in content_type:
            return '.csv'
        elif 'spreadsheet' in content_type or 'excel' in content_type:
            return '.xlsx'
        elif 'pdf' in content_type:
            return '.pdf'

        # Default to CSV
        return '.csv'

    def _process_file(self, file_path: str, original_name: str) -> Dict[str, List[pd.DataFrame]]:
        """Process downloaded file based on its type."""
        _, ext = os.path.splitext(file_path.lower())

        # Update source name from original filename
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
            raise ValueError(f"Unsupported file type: {ext}")

    def _load_csv(self, file_path: str) -> Dict[str, List[pd.DataFrame]]:
        """Load CSV file."""
        encodings = ['utf-8', 'latin-1', 'cp1252']

        for encoding in encodings:
            try:
                df = pd.read_csv(file_path, encoding=encoding)
                source_name = self.get_source_name()
                logger.info("Loaded CSV: %d rows", len(df))
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
                    logger.info("Loaded sheet '%s': %d rows", sheet_name, len(df))

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
        Fetch file via Dropbox API.

        Requires DROPBOX_ACCESS_TOKEN environment variable or credentials.
        """
        if not DROPBOX_SDK_AVAILABLE:
            raise ImportError(
                "Dropbox SDK required for API access. "
                "Install with: pip install dropbox>=11.0.0"
            )

        if not self.access_token:
            raise ValueError(
                "Dropbox access token required. "
                "Set DROPBOX_ACCESS_TOKEN environment variable or pass in credentials."
            )

        try:
            dbx = dropbox.Dropbox(self.access_token)

            # Extract path from URL or use directly
            path = self._extract_path_from_url()

            # Download file
            metadata, response = dbx.files_download(path)

            # Save to temp file
            suffix = os.path.splitext(metadata.name)[1] or '.csv'

            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                tmp.write(response.content)
                temp_path = tmp.name

            try:
                return self._process_file(temp_path, metadata.name)
            finally:
                try:
                    os.unlink(temp_path)
                except Exception:
                    pass

        except Exception as e:
            raise ValueError(f"Dropbox API error: {e}")

    def _extract_path_from_url(self) -> str:
        """Extract Dropbox file path from URL."""
        # For API paths, the URL might be a direct path like /folder/file.csv
        if self.url.startswith('/'):
            return self.url

        # Try to extract from shared link URL
        # This is a best-effort extraction
        parsed = urlparse(self.url)
        path = parsed.path

        # Remove common prefixes
        for prefix in ['/s/', '/sh/', '/scl/']:
            if prefix in path:
                # The actual file path comes after the share ID
                parts = path.split(prefix, 1)
                if len(parts) > 1:
                    remainder = parts[1]
                    # Split by / to get potential path
                    path_parts = remainder.split('/')
                    if len(path_parts) > 1:
                        return '/' + '/'.join(path_parts[1:])

        raise ValueError(
            "Cannot extract file path from URL. "
            "For API access, provide a direct Dropbox path like '/folder/file.csv'"
        )
