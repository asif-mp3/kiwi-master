"""
PDF Connector

Extracts tables from PDF documents using pdfplumber.
Falls back to text extraction if no tables are found.

Supports:
- Local PDF files
- PDF files from HTTP/HTTPS URLs
- Multi-page documents with multiple tables per page

Dependencies:
- pdfplumber>=0.9.0

This is ADDITIVE code - does not modify existing functionality.
"""

import os
import tempfile
from typing import Dict, List, Optional, ClassVar
from urllib.parse import urlparse
import pandas as pd
import requests

from data_sources.base_connector import BaseConnector

# Try to import pdfplumber, make it optional
try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False
    pdfplumber = None


class PDFConnector(BaseConnector):
    """
    Connector for PDF documents with table extraction.

    Supports:
    - Local files: /path/to/file.pdf
    - HTTP URLs: https://example.com/report.pdf
    - Multi-page documents
    - Multiple tables per page

    Table Extraction Strategy:
    1. Try pdfplumber.extract_tables() first
    2. If no tables found, extract text and attempt CSV-like parsing
    3. Return each page's tables as separate DataFrames
    """

    # Capability metadata
    supports_sync: ClassVar[bool] = True
    supports_folders: ClassVar[bool] = False
    supports_preview: ClassVar[bool] = True  # Can show PDF preview
    supports_streaming: ClassVar[bool] = False
    auth_mode: ClassVar[str] = "anonymous"
    required_credentials: ClassVar[List[str]] = []
    priority: ClassVar[int] = 100

    def __init__(self, url: str, credentials: Optional[Dict] = None):
        if not PDFPLUMBER_AVAILABLE:
            raise ImportError(
                "pdfplumber is required for PDF support. "
                "Install with: pip install pdfplumber>=0.9.0"
            )
        super().__init__(url, credentials)

    @classmethod
    def can_handle(cls, url: str) -> bool:
        """Check if this connector can handle the URL."""
        if not url:
            return False

        # Check file extension
        return url.lower().endswith('.pdf')

    def get_source_name(self) -> str:
        """Get human-readable name for this data source."""
        if self.source_name:
            return self.source_name

        parsed = urlparse(self.url)

        if parsed.scheme in ('http', 'https'):
            path = parsed.path
            filename = os.path.basename(path)
        else:
            # Local file path
            path = self.url
            if path.startswith('file://'):
                path = path[7:]
            filename = os.path.basename(path)

        # Remove .pdf extension
        if filename.lower().endswith('.pdf'):
            filename = filename[:-4]

        self.source_name = filename or 'PDF_Document'
        return self.source_name

    def fetch_tables(self) -> Dict[str, List[pd.DataFrame]]:
        """
        Fetch and extract tables from PDF.

        Returns:
            Dict mapping table names (Page_X_Table_Y) to DataFrames
        """
        pdf_path = self._get_file()

        try:
            tables = self._extract_tables(pdf_path)

            if not tables:
                print(f"[PDFConnector] No tables found, attempting text extraction")
                tables = self._extract_text_as_table(pdf_path)

            return self.validate_dataframes(tables)

        finally:
            # Clean up temp file if it was downloaded
            if hasattr(self, '_temp_path') and self._temp_path:
                try:
                    os.unlink(self._temp_path)
                except Exception:
                    pass

    def _get_file(self) -> str:
        """
        Get the PDF file path, downloading if necessary.

        Returns:
            Path to PDF file (local or temp)
        """
        self._temp_path = None
        parsed = urlparse(self.url)

        if parsed.scheme in ('http', 'https'):
            # Download to temp file
            return self._download_to_temp()
        else:
            # Local file
            path = self.url
            if path.startswith('file://'):
                path = path[7:]
                # Handle Windows paths
                if len(path) >= 3 and path[0] == '/' and path[2] == ':':
                    path = path[1:]

            if not os.path.exists(path):
                raise ValueError(f"PDF file not found: {path}")

            return path

    def _download_to_temp(self) -> str:
        """Download PDF from URL to temp file."""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (compatible; TharaAI/1.0)'
            }

            response = requests.get(self.url, headers=headers, timeout=60)
            response.raise_for_status()

            # Create temp file
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
                tmp.write(response.content)
                self._temp_path = tmp.name

            print(f"[PDFConnector] Downloaded PDF to temp: {self._temp_path}")
            return self._temp_path

        except requests.RequestException as e:
            raise ValueError(f"Failed to download PDF from URL: {e}")

    def _extract_tables(self, pdf_path: str) -> Dict[str, List[pd.DataFrame]]:
        """
        Extract tables from PDF using pdfplumber.

        Args:
            pdf_path: Path to PDF file

        Returns:
            Dict mapping table names to DataFrames
        """
        tables = {}
        source_name = self.get_source_name()

        with pdfplumber.open(pdf_path) as pdf:
            print(f"[PDFConnector] Processing {len(pdf.pages)} pages")

            for page_idx, page in enumerate(pdf.pages):
                page_num = page_idx + 1

                try:
                    page_tables = page.extract_tables()

                    if not page_tables:
                        continue

                    for table_idx, table in enumerate(page_tables):
                        if not table or len(table) < 2:
                            continue  # Skip empty or single-row tables

                        # Use first row as header
                        headers = table[0]
                        data = table[1:]

                        # Clean headers
                        headers = [
                            str(h).strip() if h else f"Column_{i}"
                            for i, h in enumerate(headers)
                        ]

                        # Ensure unique headers
                        seen = {}
                        unique_headers = []
                        for h in headers:
                            if h in seen:
                                seen[h] += 1
                                unique_headers.append(f"{h}_{seen[h]}")
                            else:
                                seen[h] = 0
                                unique_headers.append(h)

                        # Create DataFrame
                        try:
                            df = pd.DataFrame(data, columns=unique_headers)

                            # Clean up the DataFrame
                            df = df.dropna(how='all')  # Remove empty rows
                            df = df.dropna(axis=1, how='all')  # Remove empty columns

                            if not df.empty:
                                table_name = f"{source_name}_Page{page_num}_Table{table_idx + 1}"
                                tables[table_name] = [df]
                                print(f"[PDFConnector] Extracted {table_name}: {len(df)} rows")

                        except Exception as e:
                            print(f"[PDFConnector] Error creating DataFrame: {e}")
                            continue

                except Exception as e:
                    print(f"[PDFConnector] Error on page {page_num}: {e}")
                    continue

        print(f"[PDFConnector] Total tables extracted: {len(tables)}")
        return tables

    def _extract_text_as_table(self, pdf_path: str) -> Dict[str, List[pd.DataFrame]]:
        """
        Fallback: Extract text and attempt to parse as structured data.

        This is useful for PDFs with text-based tables that don't extract
        properly with extract_tables().

        Args:
            pdf_path: Path to PDF file

        Returns:
            Dict with single table from extracted text
        """
        tables = {}
        source_name = self.get_source_name()
        all_text = []

        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    all_text.append(text)

        if not all_text:
            return {}

        combined_text = "\n".join(all_text)

        # Try to parse as CSV-like structure
        lines = combined_text.strip().split('\n')

        if len(lines) < 2:
            return {}

        # Detect delimiter (tab, comma, or multiple spaces)
        first_line = lines[0]
        if '\t' in first_line:
            delimiter = '\t'
        elif ',' in first_line:
            delimiter = ','
        elif '  ' in first_line:
            delimiter = r'\s{2,}'  # Regex for multiple spaces
        else:
            return {}  # Can't determine structure

        try:
            from io import StringIO
            import re

            if delimiter == r'\s{2,}':
                # Split by multiple spaces
                rows = []
                for line in lines:
                    cells = re.split(delimiter, line.strip())
                    rows.append(cells)

                if len(rows) >= 2:
                    df = pd.DataFrame(rows[1:], columns=rows[0])
            else:
                df = pd.read_csv(
                    StringIO(combined_text),
                    sep=delimiter,
                    on_bad_lines='skip'
                )

            if not df.empty:
                tables[f"{source_name}_Text"] = [df]
                print(f"[PDFConnector] Extracted text table: {len(df)} rows")

        except Exception as e:
            print(f"[PDFConnector] Text extraction failed: {e}")

        return tables

    def get_page_count(self) -> int:
        """Get the number of pages in the PDF."""
        pdf_path = self._get_file()
        with pdfplumber.open(pdf_path) as pdf:
            return len(pdf.pages)

    def get_text(self, page_numbers: Optional[List[int]] = None) -> str:
        """
        Get text content from PDF.

        Args:
            page_numbers: Optional list of page numbers (1-indexed).
                         If None, returns all pages.

        Returns:
            Extracted text
        """
        pdf_path = self._get_file()
        text_parts = []

        with pdfplumber.open(pdf_path) as pdf:
            for i, page in enumerate(pdf.pages):
                page_num = i + 1
                if page_numbers is None or page_num in page_numbers:
                    text = page.extract_text()
                    if text:
                        text_parts.append(f"--- Page {page_num} ---\n{text}")

        return "\n\n".join(text_parts)
