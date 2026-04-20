"""
Google Drive Folder Connector

Syncs all CSV/Excel files from a public Google Drive folder.
Uses gdown for reliable access to "Anyone with link" shared folders.

Usage:
    connector = GoogleDriveFolderConnector(folder_url)
    all_tables = connector.fetch_tables()
"""

import os
import re
import json
import hashlib
import tempfile
from pathlib import Path
from typing import Dict, List, Optional
import pandas as pd

from data_sources.base_connector import BaseConnector
from utils.logger import get_logger

logger = get_logger("gdrive_folder_connector")

_BACKEND_DIR = Path(__file__).parent.parent.parent
CACHE_DIR = _BACKEND_DIR / "data" / "gdrive_cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)


class GoogleDriveFolderConnector(BaseConnector):
    """
    Connector for public Google Drive folders (shared with "Anyone with link").
    Uses gdown for reliable listing and downloading without OAuth.
    """

    SUPPORTED_EXTENSIONS = ['.csv', '.xlsx', '.xls']

    def __init__(self, url: str):
        super().__init__(url)
        self._folder_id: Optional[str] = None
        self._files: List[Dict] = []

    @classmethod
    def can_handle(cls, url: str) -> bool:
        if not url:
            return False
        patterns = [
            r'drive\.google\.com/drive/folders/([a-zA-Z0-9_-]+)',
            r'drive\.google\.com/drive/u/\d+/folders/([a-zA-Z0-9_-]+)',
        ]
        return any(re.search(p, url) for p in patterns)

    def get_source_name(self) -> str:
        if self.source_name:
            return self.source_name
        folder_id = self._extract_folder_id()
        self.source_name = f"DriveFolder_{folder_id[:8]}" if folder_id else "Google_Drive_Folder"
        return self.source_name

    def _extract_folder_id(self) -> Optional[str]:
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
        folder_id = self._extract_folder_id()
        return CACHE_DIR / f"folder_{folder_id}.json"

    def _load_cache(self) -> Optional[Dict]:
        cache_path = self._get_cache_path()
        if cache_path.exists():
            try:
                with open(cache_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error("Cache read error: %s", e)
        return None

    def _save_cache(self, files: List[Dict]):
        cache_path = self._get_cache_path()
        try:
            cache_data = {
                "folder_id": self._extract_folder_id(),
                "files": files,
                "file_hash": self._compute_files_hash(files),
            }
            with open(cache_path, 'w') as f:
                json.dump(cache_data, f, indent=2)
            logger.info("Cache saved: %d files", len(files))
        except Exception as e:
            logger.error("Cache write error: %s", e)

    def _compute_files_hash(self, files: List[Dict]) -> str:
        sorted_files = sorted(files, key=lambda f: f.get('id', ''))
        hash_input = json.dumps(
            [{"id": f.get("id"), "name": f.get("name")} for f in sorted_files],
            sort_keys=True,
        )
        return hashlib.md5(hash_input.encode()).hexdigest()

    def list_files(self) -> List[Dict]:
        """List supported files in the folder using gdown (no download)."""
        if self._files:
            return self._files

        folder_id = self._extract_folder_id()
        if not folder_id:
            raise ValueError("Could not extract folder ID from URL")

        try:
            import gdown
            folder_url = f"https://drive.google.com/drive/folders/{folder_id}"
            file_list = gdown.download_folder(
                url=folder_url,
                quiet=True,
                use_cookies=False,
                skip_download=True,
            )

            if file_list is None:
                logger.warning("gdown returned None — folder may be private or empty")
                return []

            supported = []
            for f in file_list:
                # f is a GoogleDriveFileToDownload NamedTuple: .id, .path, .local_path
                name = Path(f.path).name if hasattr(f, 'path') else str(f)
                if any(name.lower().endswith(ext) for ext in self.SUPPORTED_EXTENSIONS):
                    supported.append({
                        "id": f.id if hasattr(f, 'id') else "",
                        "name": name,
                        "path": f.path if hasattr(f, 'path') else name,
                    })

            self._files = supported
            logger.info("Found %d supported files in folder", len(supported))
            return supported

        except Exception as e:
            logger.error("gdown list failed: %s", e)
            return []

    def has_changes(self) -> bool:
        cache = self._load_cache()
        if not cache:
            return True
        self._files = []
        current_files = self.list_files()
        if not current_files:
            return True
        current_hash = self._compute_files_hash(current_files)
        if current_hash != cache.get("file_hash", ""):
            logger.info("Files changed — will sync")
            return True
        logger.info("No changes detected (%d files)", len(current_files))
        return False

    def fetch_tables(self) -> Dict[str, List[pd.DataFrame]]:
        """Download all supported files from the folder and parse into DataFrames."""
        folder_id = self._extract_folder_id()
        if not folder_id:
            logger.error("No folder ID in URL")
            return {}

        all_tables: Dict[str, List[pd.DataFrame]] = {}

        try:
            import gdown
        except ImportError:
            logger.error("gdown not installed — run: pip install gdown==5.2.0")
            return {}

        folder_url = f"https://drive.google.com/drive/folders/{folder_id}"
        tmpdir_obj = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)

        try:
            tmpdir = tmpdir_obj.name
            logger.info("Downloading folder contents...")
            downloaded = gdown.download_folder(
                url=folder_url,
                output=tmpdir,
                quiet=False,
                use_cookies=False,
            )

            if downloaded is None:
                logger.error(
                    "gdown returned None — folder is private, empty, or rate-limited. "
                    "Make sure the folder is shared as 'Anyone with the link'."
                )
                return {}

            # downloaded is a list of local file paths (strings)
            for file_path_str in downloaded:
                file_path = Path(file_path_str)
                if not file_path.is_file():
                    continue
                if file_path.suffix.lower() not in self.SUPPORTED_EXTENSIONS:
                    continue
                try:
                    tables = self._parse_file(file_path)
                    if tables:
                        all_tables.update(tables)
                        logger.info("Loaded: %s (%d tables)", file_path.name, len(tables))
                except Exception as e:
                    logger.error("Error parsing %s: %s", file_path.name, e)

        except Exception as e:
            logger.error("Folder download failed: %s", e)
            if not all_tables:
                return {}
        finally:
            tmpdir_obj.cleanup()

        if all_tables:
            self._save_cache([{"id": "", "name": k} for k in all_tables])

        return self.validate_dataframes(all_tables)

    def _parse_file(self, file_path: Path) -> Dict[str, List[pd.DataFrame]]:
        """Parse a local file into DataFrames."""
        base_name = file_path.stem
        suffix = file_path.suffix.lower()

        if suffix == '.csv':
            df = pd.read_csv(file_path)
            return {base_name: [df]}

        if suffix in ('.xlsx', '.xls'):
            with pd.ExcelFile(file_path) as excel_file:
                result = {}
                for sheet_name in excel_file.sheet_names:
                    df = pd.read_excel(excel_file, sheet_name=sheet_name)
                    if not df.empty:
                        key = (
                            f"{base_name}_{sheet_name}"
                            if len(excel_file.sheet_names) > 1
                            else base_name
                        )
                        result[key] = [df]
            return result

        return {}

    def get_file_list(self) -> List[Dict]:
        if not self._files:
            self.list_files()
        return self._files
