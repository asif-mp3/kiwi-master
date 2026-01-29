"""
Google Drive Folder Connector

Syncs all CSV/Excel files from a Google Drive folder.
Supports publicly shared folders ("Anyone with link" access).
Includes smart caching - only re-downloads when files change.

Usage:
    connector = GoogleDriveFolderConnector(folder_url)
    all_tables = connector.fetch_all_files()
"""

import os
import re
import json
import hashlib
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import pandas as pd
import requests

from data_sources.base_connector import BaseConnector

# Cache directory for folder metadata (relative to backend directory)
_BACKEND_DIR = Path(__file__).parent.parent.parent  # connectors -> data_sources -> backend
CACHE_DIR = _BACKEND_DIR / "data" / "gdrive_cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)


class GoogleDriveFolderConnector(BaseConnector):
    """
    Connector for Google Drive folders.

    Lists all files in a shared folder and loads CSV/Excel files.
    Requires folder to be shared with "Anyone with link" permission.
    """

    SUPPORTED_EXTENSIONS = ['.csv', '.xlsx', '.xls']

    def __init__(self, url: str):
        super().__init__(url)
        self._folder_id: Optional[str] = None
        self._files: List[Dict] = []

    @classmethod
    def can_handle(cls, url: str) -> bool:
        """Check if URL is a Google Drive folder."""
        if not url:
            return False

        # Match folder URLs
        patterns = [
            r'drive\.google\.com/drive/folders/([a-zA-Z0-9_-]+)',
            r'drive\.google\.com/drive/u/\d+/folders/([a-zA-Z0-9_-]+)',
        ]

        for pattern in patterns:
            if re.search(pattern, url):
                return True

        return False

    def get_source_name(self) -> str:
        """Get folder name."""
        if self.source_name:
            return self.source_name

        folder_id = self._extract_folder_id()
        self.source_name = f"DriveFolder_{folder_id[:8]}" if folder_id else "Google_Drive_Folder"
        return self.source_name

    def _extract_folder_id(self) -> Optional[str]:
        """Extract folder ID from URL."""
        if self._folder_id:
            return self._folder_id

        patterns = [
            r'drive\.google\.com/drive/folders/([a-zA-Z0-9_-]+)',
            r'drive\.google\.com/drive/u/\d+/folders/([a-zA-Z0-9_-]+)',
        ]

        for pattern in patterns:
            match = re.search(pattern, self.url)
            if match:
                self._folder_id = match.group(1)
                return self._folder_id

        return None

    def _get_cache_path(self) -> Path:
        """Get the cache file path for this folder."""
        folder_id = self._extract_folder_id()
        return CACHE_DIR / f"folder_{folder_id}.json"

    def _load_cache(self) -> Optional[Dict]:
        """Load cached folder metadata."""
        cache_path = self._get_cache_path()
        if cache_path.exists():
            try:
                with open(cache_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"[GDriveFolderConnector] Cache read error: {e}")
        return None

    def _save_cache(self, files: List[Dict]):
        """Save folder metadata to cache."""
        cache_path = self._get_cache_path()
        try:
            cache_data = {
                "folder_id": self._extract_folder_id(),
                "files": files,
                "file_hash": self._compute_files_hash(files)
            }
            with open(cache_path, 'w') as f:
                json.dump(cache_data, f, indent=2)
            print(f"[GDriveFolderConnector] Cache saved: {len(files)} files")
        except Exception as e:
            print(f"[GDriveFolderConnector] Cache write error: {e}")

    def _compute_files_hash(self, files: List[Dict]) -> str:
        """Compute a hash of file metadata to detect changes."""
        # Sort files by ID for consistent hashing
        sorted_files = sorted(files, key=lambda f: f.get('id', ''))
        # Include id, name, size, and modifiedTime in hash
        hash_input = json.dumps([
            {
                "id": f.get("id"),
                "name": f.get("name"),
                "size": f.get("size", 0),
                "modifiedTime": f.get("modifiedTime", "")
            }
            for f in sorted_files
        ], sort_keys=True)
        return hashlib.md5(hash_input.encode()).hexdigest()

    def has_changes(self) -> bool:
        """
        Check if folder contents have changed since last sync.

        Returns:
            True if files changed (need re-sync), False if unchanged
        """
        cache = self._load_cache()
        if not cache:
            print("[GDriveFolderConnector] No cache found - will sync")
            return True

        # Clear cached files to force fresh API call
        self._files = []

        # Fetch current file list from API
        current_files = self.list_files()
        if not current_files:
            return True

        # Compare hashes
        current_hash = self._compute_files_hash(current_files)
        cached_hash = cache.get("file_hash", "")

        if current_hash != cached_hash:
            cached_count = len(cache.get("files", []))
            print(f"[GDriveFolderConnector] Files changed ({cached_count} -> {len(current_files)}) - will sync")
            return True

        print(f"[GDriveFolderConnector] No changes detected ({len(current_files)} files) - skipping sync")
        return False

    def list_files(self) -> List[Dict]:
        """
        List all files in the folder.

        Returns:
            List of file info dicts with 'id', 'name', 'mimeType'
        """
        # Return cached results if available
        if self._files:
            return self._files

        folder_id = self._extract_folder_id()
        if not folder_id:
            raise ValueError("Could not extract folder ID from URL")

        # Use Google Drive API (no auth needed for public folders)
        # This is the "list files" endpoint for public folders
        api_url = f"https://www.googleapis.com/drive/v3/files"
        params = {
            "q": f"'{folder_id}' in parents and trashed = false",
            "key": os.getenv("GOOGLE_API_KEY", "").strip(),  # Optional API key (strip whitespace)
            "fields": "files(id,name,mimeType,size,modifiedTime)",
            "pageSize": 100
        }

        try:
            # Try with API key first
            if params["key"]:
                response = requests.get(api_url, params=params, timeout=30)
                if response.ok:
                    data = response.json()
                    self._files = data.get("files", [])
                    return self._files

            # Fallback: scrape the folder page (works for public folders)
            return self._scrape_folder_files(folder_id)

        except Exception as e:
            print(f"[GDriveFolderConnector] Error listing files: {e}")
            # Try scraping as fallback
            return self._scrape_folder_files(folder_id)

    def _scrape_folder_files(self, folder_id: str) -> List[Dict]:
        """
        Scrape file list from public folder page.

        This works for publicly shared folders without API key.
        """
        try:
            # Request the folder page
            folder_url = f"https://drive.google.com/drive/folders/{folder_id}"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }

            response = requests.get(folder_url, headers=headers, timeout=30)
            response.raise_for_status()

            html = response.text

            # Parse file IDs and names from the page
            # Google embeds file data in JavaScript
            files = []

            # Pattern to find file entries in the page data
            # Format: ["file_id","file_name",...]
            file_pattern = r'\["([a-zA-Z0-9_-]{25,})","([^"]+\.(?:csv|xlsx|xls))"'
            matches = re.findall(file_pattern, html, re.IGNORECASE)

            for file_id, file_name in matches:
                mime_type = self._guess_mime_type(file_name)
                files.append({
                    "id": file_id,
                    "name": file_name,
                    "mimeType": mime_type
                })

            # Deduplicate
            seen = set()
            unique_files = []
            for f in files:
                if f["id"] not in seen:
                    seen.add(f["id"])
                    unique_files.append(f)

            self._files = unique_files
            print(f"[GDriveFolderConnector] Found {len(unique_files)} files in folder")
            return unique_files

        except Exception as e:
            print(f"[GDriveFolderConnector] Error scraping folder: {e}")
            return []

    def _guess_mime_type(self, filename: str) -> str:
        """Guess MIME type from filename."""
        lower = filename.lower()
        if lower.endswith('.csv'):
            return 'text/csv'
        elif lower.endswith('.xlsx'):
            return 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        elif lower.endswith('.xls'):
            return 'application/vnd.ms-excel'
        return 'application/octet-stream'

    def fetch_tables(self) -> Dict[str, List[pd.DataFrame]]:
        """
        Fetch all supported files from the folder.

        Returns:
            Dict mapping filenames to lists of DataFrames
        """
        files = self.list_files()

        if not files:
            print("[GDriveFolderConnector] No files found in folder")
            return {}

        all_tables = {}

        for file_info in files:
            file_name = file_info.get("name", "")
            file_id = file_info.get("id", "")

            # Check if file is supported
            if not any(file_name.lower().endswith(ext) for ext in self.SUPPORTED_EXTENSIONS):
                print(f"[GDriveFolderConnector] Skipping unsupported file: {file_name}")
                continue

            try:
                # Download and parse the file
                tables = self._download_and_parse(file_id, file_name)
                if tables:
                    all_tables.update(tables)
                    print(f"[GDriveFolderConnector] Loaded: {file_name}")
            except Exception as e:
                print(f"[GDriveFolderConnector] Error loading {file_name}: {e}")

        # Save cache after successful load
        if all_tables:
            self._save_cache(files)

        return self.validate_dataframes(all_tables)

    def _download_and_parse(self, file_id: str, file_name: str) -> Dict[str, List[pd.DataFrame]]:
        """Download a file and parse it."""
        import time

        # Google Drive direct download URL
        download_url = f"https://drive.google.com/uc?export=download&id={file_id}"

        # Retry logic for transient connection issues
        max_retries = 3
        last_error = None
        response = None

        for attempt in range(max_retries):
            try:
                session = requests.Session()
                response = session.get(download_url, stream=True, timeout=60)
                break  # Success, exit retry loop
            except Exception as e:
                last_error = e
                if attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 2  # 2, 4 seconds
                    print(f"[GDriveFolderConnector] Download attempt {attempt + 1} failed, retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    raise ValueError(f"Failed to download after {max_retries} attempts: {last_error}")

        if response is None:
            raise ValueError(f"Failed to download {file_name}: No response received")

        try:
            # Handle virus scan warning for large files
            if 'confirm' in response.url or 'virus scan warning' in response.text.lower():
                # Try to get confirmation token
                for key, value in response.cookies.items():
                    if key.startswith('download_warning'):
                        download_url = f"{download_url}&confirm={value}"
                        response = session.get(download_url, stream=True, timeout=60)
                        break

            response.raise_for_status()

            # Save to temp file
            suffix = os.path.splitext(file_name)[1]
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        tmp.write(chunk)
                tmp_path = tmp.name

            try:
                # Parse based on file type
                base_name = os.path.splitext(file_name)[0]

                if file_name.lower().endswith('.csv'):
                    df = pd.read_csv(tmp_path)
                    return {base_name: [df]}

                elif file_name.lower().endswith(('.xlsx', '.xls')):
                    excel_file = pd.ExcelFile(tmp_path)
                    result = {}
                    for sheet_name in excel_file.sheet_names:
                        df = pd.read_excel(excel_file, sheet_name=sheet_name)
                        if not df.empty:
                            # Use "FileName_SheetName" as key
                            key = f"{base_name}_{sheet_name}"
                            result[key] = [df]
                    return result

            finally:
                # Clean up temp file
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass  # File cleanup is non-critical

        except Exception as e:
            raise ValueError(f"Failed to download {file_name}: {e}")

        return {}

    def get_file_list(self) -> List[Dict]:
        """Get list of files (for display purposes)."""
        if not self._files:
            self.list_files()
        return self._files
