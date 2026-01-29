import gspread
import pandas as pd
import numpy as np
import yaml
import os
import time
import threading
from google.oauth2.service_account import Credentials as ServiceAccountCredentials
from typing import Dict, List, Any, Optional, Tuple

# ============================================
# THREAD-LOCAL STORAGE FOR USER CREDENTIALS
# Fixes cross-user credential leakage in concurrent requests
# ============================================
_user_context = threading.local()


# ============================================
# GOOGLE SHEETS SNAPSHOT CACHE
# Implements the caching flow from the architecture:
# - Cache interval: 60 seconds between change checks
# - Full cache: Stores sheet data to avoid re-fetching
# - Saves 5-15 seconds on subsequent queries
# ============================================
class SheetCache:
    """Thread-safe cache for Google Sheets data."""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._init_cache()
        return cls._instance

    def _init_cache(self):
        """Initialize cache state."""
        self._data: Optional[Dict] = None
        self._last_check: float = 0
        self._check_interval: int = 300  # Only check changes every 5 minutes (was 60s)
        self._spreadsheet_id: Optional[str] = None
        self._cache_lock = threading.RLock()

    def get_cached_data(
        self,
        spreadsheet_id: str,
        force_refresh: bool = False
    ) -> Tuple[Optional[Dict], bool]:
        """
        Get cached sheet data if available and fresh.

        Args:
            spreadsheet_id: The spreadsheet to get data for
            force_refresh: Force a refresh regardless of cache state

        Returns:
            Tuple of (cached_data or None, was_cache_hit: bool)
        """
        with self._cache_lock:
            now = time.time()

            # Check if cache is valid
            if (
                not force_refresh
                and self._data is not None
                and self._spreadsheet_id == spreadsheet_id
                and now - self._last_check < self._check_interval
            ):
                return self._data, True

            return None, False

    def set_cached_data(self, spreadsheet_id: str, data: Dict) -> None:
        """
        Store sheet data in cache.

        Args:
            spreadsheet_id: The spreadsheet ID
            data: The sheet data to cache
        """
        with self._cache_lock:
            self._data = data
            self._spreadsheet_id = spreadsheet_id
            self._last_check = time.time()

    def invalidate(self) -> None:
        """Invalidate the cache (e.g., on data refresh)."""
        with self._cache_lock:
            self._data = None
            self._last_check = 0
            self._spreadsheet_id = None

    def is_valid(self, spreadsheet_id: str) -> bool:
        """
        Check if cache is valid without returning data.
        Used by check_and_refresh_data() to skip redundant downloads.

        Args:
            spreadsheet_id: The spreadsheet ID to check

        Returns:
            True if cache is valid and fresh, False otherwise
        """
        with self._cache_lock:
            if self._data is None:
                print(f"    [SheetCache] Invalid: no data cached")
                return False
            if self._spreadsheet_id != spreadsheet_id:
                print(f"    [SheetCache] Invalid: ID mismatch (cached: {self._spreadsheet_id[:15] if self._spreadsheet_id else 'None'}...)")
                return False
            age = time.time() - self._last_check
            if age >= self._check_interval:
                print(f"    [SheetCache] Invalid: cache expired (age: {age:.1f}s > {self._check_interval}s)")
                return False
            print(f"    [SheetCache] Valid! Age: {age:.1f}s < {self._check_interval}s TTL")
            return True

    def set_check_interval(self, seconds: int) -> None:
        """Update the cache check interval."""
        self._check_interval = seconds


def get_sheet_cache() -> SheetCache:
    """Get the singleton SheetCache instance."""
    return SheetCache()


# Legacy global state (deprecated - use thread-local instead)
_current_user_id: Optional[str] = None


def set_current_user(user_id: str):
    """
    Set the current user ID for OAuth credential lookup.
    Uses thread-local storage to prevent cross-user credential leakage.
    """
    global _current_user_id
    # Thread-local storage (preferred - thread-safe)
    _user_context.user_id = user_id
    # Also set global for backwards compatibility
    _current_user_id = user_id


def get_current_user() -> Optional[str]:
    """
    Get the current user ID.
    Uses thread-local storage for thread safety.
    """
    # Try thread-local first (thread-safe)
    user_id = getattr(_user_context, 'user_id', None)
    if user_id:
        return user_id
    # Fallback to global (backwards compatibility)
    return _current_user_id


def clear_current_user():
    """Clear the current user context (call at end of request)."""
    global _current_user_id
    if hasattr(_user_context, 'user_id'):
        delattr(_user_context, 'user_id')
    _current_user_id = None


def _load_config():
    with open("config/settings.yaml") as f:
        return yaml.safe_load(f)


def _get_credentials(scopes: List[str]):
    """
    Get Google credentials - either from user OAuth or service account.

    Priority:
    1. User OAuth tokens (if user is logged in and has authorized Sheets)
    2. Service account from environment variable (for Railway/cloud deployment)
    3. Service account from file (for local development)

    Returns:
        Google credentials object compatible with gspread
    """
    import json

    # Get user from thread-local storage (thread-safe)
    current_user = get_current_user()

    # Try user OAuth first
    if current_user:
        try:
            from utils.gsheet_oauth import get_gspread_credentials, has_sheets_access

            if has_sheets_access(current_user):
                print(f"[GSheet] Using OAuth credentials for user: {current_user}")
                return get_gspread_credentials(current_user)
        except Exception as e:
            print(f"[GSheet] OAuth credentials failed: {e}, falling back to service account")

    # Try service account from environment variable (for cloud deployment)
    service_account_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
    if service_account_json:
        try:
            print(f"[GSheet] Using service account from environment variable")
            service_account_info = json.loads(service_account_json)
            return ServiceAccountCredentials.from_service_account_info(
                service_account_info,
                scopes=scopes
            )
        except Exception as e:
            print(f"[GSheet] Failed to load service account from env: {e}")

    # Fallback to service account file (for local development)
    config = _load_config()
    gs_config = config.get("google_sheets", {})
    credentials_path = gs_config.get("credentials_path", "credentials/service_account.json")

    if os.path.exists(credentials_path):
        print(f"[GSheet] Using service account credentials from file")
        return ServiceAccountCredentials.from_service_account_file(
            credentials_path,
            scopes=scopes
        )

    # No credentials available
    raise ValueError(
        "No Google Sheets credentials available. "
        "Set GOOGLE_SERVICE_ACCOUNT_JSON environment variable, "
        "authorize with Google Sheets OAuth, or configure a service account file."
    )


def infer_and_convert_types(df, numeric_threshold: float = None, date_threshold: float = None):
    """
    Intelligently infer and convert data types from string data.
    Converts numeric strings to INT/FLOAT, dates to datetime, booleans to bool.

    Args:
        df: DataFrame to process
        numeric_threshold: Minimum ratio of numeric values to convert column (default from config)
        date_threshold: Minimum ratio of valid dates to convert column (default from config)
    """
    # Get thresholds from config if not provided
    if numeric_threshold is None or date_threshold is None:
        try:
            from utils.config_loader import get_config
            config = get_config()
            if numeric_threshold is None:
                numeric_threshold = config.google_sheets.numeric_conversion_threshold
            if date_threshold is None:
                date_threshold = config.google_sheets.date_conversion_threshold
        except Exception:
            # Fallback defaults
            numeric_threshold = numeric_threshold or 0.8
            date_threshold = date_threshold or 0.5

    for col in df.columns:
        try:
            # Skip if already numeric (check dtype, not boolean evaluation)
            if pd.api.types.is_numeric_dtype(df[col]):
                continue
            
            # Skip if all values are NA
            if df[col].isna().all():
                continue
            
            # Get non-null values for analysis
            non_null = df[col].dropna()
            if len(non_null) == 0:
                continue
            
            # Try boolean conversion first (True/False, Yes/No, 1/0)
            if non_null.isin(['True', 'False', 'true', 'false', 'TRUE', 'FALSE', 
                              'Yes', 'No', 'yes', 'no', 'YES', 'NO',
                              '1', '0', 1, 0]).all():
                try:
                    df[col] = df[col].map({
                        'True': True, 'true': True, 'TRUE': True, 'Yes': True, 'yes': True, 'YES': True, '1': True, 1: True,
                        'False': False, 'false': False, 'FALSE': False, 'No': False, 'no': False, 'NO': False, '0': False, 0: False
                    })
                    continue
                except (ValueError, TypeError, KeyError):
                    pass  # Boolean conversion failed, try other types
            
            # Try numeric conversion (int or float)
            try:
                # Remove common formatting (commas, currency symbols, whitespace)
                cleaned = non_null.astype(str).str.strip()
                cleaned = cleaned.str.replace(',', '')
                cleaned = cleaned.str.replace('$', '')
                cleaned = cleaned.str.replace('₹', '')
                cleaned = cleaned.str.replace('%', '')
                
                # Try converting to numeric
                numeric_values = pd.to_numeric(cleaned, errors='coerce')
                
                # Convert if ratio exceeds threshold (default 80% from config)
                # Less aggressive than before (was 30%) to avoid converting mostly-text columns
                ratio = numeric_values.notna().sum() / len(non_null)
                if ratio >= numeric_threshold:
                    # Check if all numeric values are integers
                    if numeric_values.dropna().apply(lambda x: x == int(x)).all():
                        df[col] = pd.to_numeric(df[col].astype(str).str.strip().str.replace(',', '').str.replace('$', '').str.replace('₹', '').str.replace('%', ''), errors='coerce').astype('Int64')
                    else:
                        df[col] = pd.to_numeric(df[col].astype(str).str.strip().str.replace(',', '').str.replace('$', '').str.replace('₹', '').str.replace('%', ''), errors='coerce')
                    continue
            except (ValueError, TypeError, AttributeError):
                pass  # Numeric conversion failed, try other types
            
            # Try date/datetime conversion
            try:
                import warnings
                with warnings.catch_warnings():
                    warnings.simplefilter('ignore')  # Suppress all warnings during date inference

                    # Debug: Log sample values for date-like columns
                    col_lower = col.lower()
                    if 'date' in col_lower or 'joining' in col_lower or 'dob' in col_lower:
                        sample = non_null.head(3).tolist()
                        print(f"\n      [DATE DEBUG] Column '{col}' samples: {sample}")

                    # Check for Google Sheets serial date numbers (e.g., 44941 = 2023-01-15)
                    # Serial dates are typically between 1 and 100000 (covers 1900-2173)
                    try:
                        numeric_vals = pd.to_numeric(non_null, errors='coerce')
                        if numeric_vals.notna().sum() / len(non_null) >= 0.5:
                            # Check if values are in valid serial date range
                            valid_serial = numeric_vals.between(1, 100000)
                            if valid_serial.sum() / len(non_null) >= 0.5:
                                # Convert Google Sheets serial dates (epoch: Dec 30, 1899)
                                from datetime import datetime, timedelta
                                serial_epoch = datetime(1899, 12, 30)
                                date_values = numeric_vals.apply(
                                    lambda x: serial_epoch + timedelta(days=int(x)) if pd.notna(x) and 1 <= x <= 100000 else pd.NaT
                                )
                                if date_values.notna().sum() / len(non_null) >= date_threshold:
                                    df[col] = df[col].apply(
                                        lambda x: serial_epoch + timedelta(days=int(float(x)))
                                        if pd.notna(x) and str(x).replace('.', '').isdigit() and 1 <= float(x) <= 100000
                                        else pd.NaT
                                    )
                                    df[col] = pd.to_datetime(df[col], errors='coerce')
                                    continue
                    except (ValueError, TypeError, OverflowError):
                        pass  # Serial date conversion failed

                    # Detect date format first (DD/MM/YYYY vs MM/DD/YYYY)
                    detected_format = detect_date_format(non_null)

                    # Map to pandas format string
                    if detected_format == 'DD/MM/YYYY':
                        fmt = '%d/%m/%Y'
                    elif detected_format == 'MM/DD/YYYY':
                        fmt = '%m/%d/%Y'
                    else:
                        fmt = None  # Let pandas infer

                    # Try parsing with detected format first (FAST)
                    if fmt:
                        date_values = pd.to_datetime(non_null, format=fmt, errors='coerce')
                        # If format didn't work well, fall back to inference
                        if date_values.notna().sum() / len(non_null) < 0.5:
                            date_values = pd.to_datetime(non_null, errors='coerce')
                    else:
                        # Try common date formats in order
                        date_formats = [
                            '%Y-%m-%d',           # ISO: 2023-01-15
                            '%d-%m-%Y',           # 15-01-2023
                            '%d-%b-%Y',           # 15-Jan-2023
                            '%d %b %Y',           # 15 Jan 2023
                            '%b %d, %Y',          # Jan 15, 2023
                            '%B %d, %Y',          # January 15, 2023
                            '%d/%m/%Y',           # 15/01/2023
                            '%m/%d/%Y',           # 01/15/2023
                            '%Y/%m/%d',           # 2023/01/15
                            '%d.%m.%Y',           # 15.01.2023
                        ]

                        date_values = None
                        for date_fmt in date_formats:
                            try:
                                test_values = pd.to_datetime(non_null, format=date_fmt, errors='coerce')
                                if test_values.notna().sum() / len(non_null) >= 0.5:
                                    date_values = test_values
                                    fmt = date_fmt
                                    break
                            except (ValueError, TypeError):
                                continue  # This format doesn't match

                        # Fall back to pandas inference if no format matched
                        if date_values is None or date_values.notna().sum() / len(non_null) < 0.5:
                            date_values = pd.to_datetime(non_null, errors='coerce', dayfirst=True)

                # Convert if ratio exceeds threshold (default 50% from config)
                if date_values is not None and date_values.notna().sum() / len(non_null) >= date_threshold:
                    with warnings.catch_warnings():
                        warnings.simplefilter('ignore')
                        if fmt:
                            df[col] = pd.to_datetime(df[col], format=fmt, errors='coerce')
                        else:
                            df[col] = pd.to_datetime(df[col], errors='coerce', dayfirst=True)
                    # Debug: confirm successful date parsing
                    valid_count = df[col].notna().sum()
                    sample_dates = df[col].dropna().head(2).tolist()
                    print(f"      ✓ [DATE SUCCESS] Column '{col}': {valid_count}/{len(df)} valid dates. Samples: {sample_dates}")
                    continue
            except (ValueError, TypeError, OverflowError):
                pass  # Date conversion failed, keep original type
        except Exception as e:
            # If any error occurs for this column, skip it and continue with next column
            print(f"      ⚠️  Warning: Could not infer type for column '{col}': {e}")
            continue
    
    return df


def detect_date_format(date_series):
    """
    Detect date format including separator and order.

    Strategy:
    1. Detect separator (/, -, ., space)
    2. Check for ISO format (YYYY-MM-DD) - return None to use comprehensive format list
    3. For ambiguous dates, detect DD/MM vs MM/DD order

    Returns:
        str: 'DD/MM/YYYY', 'MM/DD/YYYY', or None for ISO/other formats
    """
    # Get non-null string values
    non_null = date_series.dropna().astype(str)

    if len(non_null) == 0:
        return None  # Let pandas infer

    # Check first few values to detect format
    for date_str in non_null.head(20):
        date_str = date_str.strip()

        # Check for ISO format (YYYY-MM-DD or YYYY/MM/DD)
        # ISO dates start with 4-digit year
        if len(date_str) >= 10:
            # Check if starts with 4-digit year
            first_part = date_str[:4]
            if first_part.isdigit() and 1900 <= int(first_part) <= 2100:
                # This is ISO format - return None to use comprehensive format list
                print(f"      [DATE] Detected ISO format: {date_str}")
                return None

        # Check for month names (Jan, January, etc.)
        month_names = ['jan', 'feb', 'mar', 'apr', 'may', 'jun',
                       'jul', 'aug', 'sep', 'oct', 'nov', 'dec']
        if any(month in date_str.lower() for month in month_names):
            print(f"      [DATE] Detected month name format: {date_str}")
            return None  # Use comprehensive format list

        # Try to detect separator and order for DD/MM/YYYY style dates
        for sep in ['/', '-', '.']:
            parts = date_str.split(sep)
            if len(parts) == 3:
                try:
                    first = int(parts[0])
                    second = int(parts[1])
                    third = int(parts[2])

                    # If first part is 4 digits, it's YYYY-... format
                    if first > 1900:
                        print(f"      [DATE] Detected YYYY-first format: {date_str}")
                        return None

                    # If first part > 12, it must be day (DD/MM/YYYY or DD-MM-YYYY)
                    if first > 12 and first <= 31:
                        fmt = 'DD/MM/YYYY' if sep == '/' else None
                        print(f"      [DATE] Detected DD-first format: {date_str} -> {fmt}")
                        return fmt

                    # If second part > 12, it must be day (MM/DD/YYYY or MM-DD-YYYY)
                    if second > 12 and second <= 31:
                        fmt = 'MM/DD/YYYY' if sep == '/' else None
                        print(f"      [DATE] Detected MM-first format: {date_str} -> {fmt}")
                        return fmt
                except ValueError:
                    continue

    # If we found "/" separator but couldn't determine order, default to DD/MM/YYYY
    for date_str in non_null.head(5):
        if '/' in date_str:
            print(f"      [DATE] Defaulting to DD/MM/YYYY for: {date_str}")
            return 'DD/MM/YYYY'

    # For other separators or unknown formats, return None to use comprehensive list
    print(f"      [DATE] Unknown format, using comprehensive list")
    return None


def combine_date_time_columns(df):
    """
    Combine separate Date and Time columns into a single proper timestamp.
    This fixes time range queries by ensuring Time has the correct date component.
    
    If both 'Date' and 'Time' columns exist:
    - Detect date format (DD/MM/YYYY vs MM/DD/YYYY)
    - Parse dates with correct format
    - Normalize Date column to ISO format (YYYY-MM-DD)
    - Combine them into Time as a proper timestamp (timezone-naive)
    """
    # Check if both Date and Time columns exist
    if 'Date' not in df.columns or 'Time' not in df.columns:
        return df
    
    try:
        # Detect date format
        date_format = detect_date_format(df['Date'])
        dayfirst = (date_format == 'DD/MM/YYYY')
        
        # Parse dates with correct format
        import warnings
        with warnings.catch_warnings():
            warnings.filterwarnings('ignore', category=FutureWarning)
            parsed_dates = pd.to_datetime(
                df['Date'],
                errors='coerce',
                dayfirst=dayfirst
            )
        
        # Parse time column to extract time components
        # The Time column may contain just time strings like "01:00", "14:30", etc.
        with warnings.catch_warnings():
            warnings.filterwarnings('ignore', category=FutureWarning)
            parsed_times = pd.to_datetime(
                df['Time'].astype(str),
                errors='coerce',
                format='mixed'
            )
        
        # Combine the date from parsed_dates with the time from parsed_times
        # This ensures we use the correct date from the Date column, not today's date
        combined = pd.to_datetime(
            parsed_dates.dt.strftime('%Y-%m-%d') + ' ' + 
            parsed_times.dt.strftime('%H:%M:%S'),
            errors='coerce'
        )
        
        # Remove timezone info if present
        if combined.dt.tz is not None:
            combined = combined.dt.tz_localize(None)
        
        # Only update if combination was successful for most rows
        if combined.notna().sum() / len(df) > 0.5:
            # Update Time column with proper timestamp
            df['Time'] = combined
            
            # Normalize Date column to ISO format (YYYY-MM-DD) for consistency
            df['Date'] = parsed_dates.dt.strftime('%d/%m/%Y')
            
            print(f"      → Combined Date + Time into timestamp column (detected {date_format} format)")
    except Exception as e:
        # If combination fails, keep original columns
        print(f"      ⚠️  Warning: Could not combine Date + Time columns: {e}")
        pass
    
    return df


def fetch_sheets():
    """
    Fetches all tabs from the Google Sheet as Pandas DataFrames.
    Handles duplicate and empty column headers by making them unique.
    Read-only. No mutation allowed.
    """
    config = _load_config()
    gs_config = config["google_sheets"]

    scopes = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
    credentials = _get_credentials(scopes)

    client = gspread.authorize(credentials)
    spreadsheet = client.open_by_key(gs_config["spreadsheet_id"])

    sheets_data = {}
    total_sheets = len(spreadsheet.worksheets())
    
    print(f"📊 Loading {total_sheets} sheets from Google Sheets...")

    for idx, worksheet in enumerate(spreadsheet.worksheets(), 1):
        try:
            sheet_name = worksheet.title
            print(f"   [{idx}/{total_sheets}] Loading '{sheet_name}'...", end=" ")
            
            # Get all values including headers
            all_values = worksheet.get_all_values()
            
            if not all_values or len(all_values) < 2:
                # Skip empty sheets or sheets with only headers
                print("⊘ Empty, skipped")
                continue
            
            # Extract headers and data
            headers = all_values[0]
            data_rows = all_values[1:]
            
            # Make headers unique by appending numbers to duplicates
            unique_headers = []
            header_counts = {}
            
            for header in headers:
                # Handle empty headers
                if not header or header.strip() == '':
                    header = 'Unnamed'
                else:
                    # Strip leading/trailing whitespace from column names
                    header = header.strip()
                
                # Make duplicates unique
                if header in header_counts:
                    header_counts[header] += 1
                    unique_header = f"{header}_{header_counts[header]}"
                else:
                    header_counts[header] = 0
                    unique_header = header
                
                unique_headers.append(unique_header)
            
            # Create DataFrame
            df = pd.DataFrame(data_rows, columns=unique_headers)
            
            # Remove completely empty rows
            df = df.replace('', pd.NA).dropna(how='all')
            
            if df.empty:
                print("⊘ No data, skipped")
                continue
            
            # Apply intelligent type inference
            df = infer_and_convert_types(df)
            
            # Combine Date + Time columns if both exist
            df = combine_date_time_columns(df)
            
            sheets_data[worksheet.title] = df
            print(f"✓ {len(df):,} rows, {len(df.columns)} cols")
            
        except Exception as e:
            print(f"⚠️  Error: {e}")
            continue

    print(f"\n✓ Loaded {len(sheets_data)} sheets successfully")

    if not sheets_data:
        raise RuntimeError("No data found in Google Sheets")

    return sheets_data


def fetch_sheets_with_tables(spreadsheet_id: str = None) -> Dict[str, List[Dict[str, Any]]]:
    """
    Fetches all tabs from Google Sheet and detects multiple tables within each sheet.

    CRITICAL CHANGES:
    1. Computes RAW SHEET HASH before any processing (for change detection)
    2. Adds source_id to each detected table for atomic tracking
    3. Fetches RAW data WITHOUT type inference first
    4. Detects tables, then applies type inference to each detected table

    Args:
        spreadsheet_id: Optional spreadsheet ID. If None, reads from config.

    Returns:
        Dict mapping sheet_name to list of detected tables.
        Each table contains:
        - table_id: Unique identifier
        - row_range: (start_row, end_row)
        - col_range: (start_col, end_col)
        - dataframe: Table data with proper headers and types
        - title: Optional table title
        - sheet_name: Source sheet name
        - source_id: Unique identifier for the source sheet (spreadsheet_id#sheet_name)
        - sheet_hash: SHA-256 hash of raw sheet data (for change detection)
    """
    from data_sources.gsheet.table_detection import detect_and_clean_tables
    from data_sources.gsheet.sheet_hasher import compute_sheet_hash, get_source_id

    # Use provided spreadsheet_id or fall back to config
    if spreadsheet_id is None:
        config = _load_config()
        gs_config = config["google_sheets"]
        spreadsheet_id = gs_config["spreadsheet_id"]

    scopes = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
    credentials = _get_credentials(scopes)

    client = gspread.authorize(credentials)
    spreadsheet = client.open_by_key(spreadsheet_id)

    sheets_with_tables = {}
    total_sheets = len(spreadsheet.worksheets())
    
    print(f"📊 Loading {total_sheets} sheets from Google Sheets...")

    for idx, worksheet in enumerate(spreadsheet.worksheets(), 1):
        try:
            sheet_name = worksheet.title
            print(f"   [{idx}/{total_sheets}] Loading '{sheet_name}'...", end=" ")
            
            # Get all values including headers
            all_values = worksheet.get_all_values()
            
            if not all_values or len(all_values) < 2:
                # Skip empty sheets or sheets with only headers
                print("⊘ Empty, skipped")
                continue
            
            # STEP 1: Compute raw sheet hash BEFORE any processing
            # This hash represents the complete state of the sheet
            # FORCE INVALIDATION: Append version to force rebuild with new type inference logic
            sheet_hash = compute_sheet_hash(all_values) + "_v3_force_numeric"
            source_id = get_source_id(spreadsheet_id, sheet_name)
            
            # Create DataFrame with RAW string data (no type inference yet)
            # IMPORTANT: Do not extract headers here! 
            # The custom detector processing pipeline (detect_and_clean_tables -> clean_detected_tables)
            # expects the headers to be in the first row of the DataFrame body.
            # If we extract headers here, clean_detected_tables will treat the first DATA row as headers.
            raw_df = pd.DataFrame(all_values)
            
            # DO NOT remove empty rows here! The custom detector NEEDS them to separate tables.
            # Empty rows act as separators between tables in the sheet.
            # The table_cleaner will handle empty row removal AFTER detection.
            
            if raw_df.empty:
                print("⊘ No data, skipped")
                continue
            
            # STEP 2: Detect tables in this sheet using RAW data
            print(f"✓ {len(raw_df):,} rows, detecting tables...", end=" ")
            detected_tables = detect_and_clean_tables(raw_df, sheet_name)
            
            # STEP 3: Add source_id and sheet_hash to each detected table
            for table in detected_tables:
                table['source_id'] = source_id
                table['sheet_hash'] = sheet_hash
            
            # STEP 4: Apply type inference and date/time combination to each detected table
            for table in detected_tables:
                table_df = table['dataframe']
                
                # Apply intelligent type inference
                table_df = infer_and_convert_types(table_df)
                
                # Combine Date + Time columns if both exist
                table_df = combine_date_time_columns(table_df)
                
                # Update the dataframe in the table info
                table['dataframe'] = table_df
            
            sheets_with_tables[worksheet.title] = detected_tables
            print(f"✓ Found {len(detected_tables)} table(s) [hash: {sheet_hash[:8]}...]")
            
        except Exception as e:
            import traceback
            print(f"⚠️  Error processing '{sheet_name}': {e}")
            print(f"    Traceback:")
            traceback.print_exc()
            print(f"    → Skipping this sheet")
            continue

    print(f"\n✓ Loaded {len(sheets_with_tables)} sheets successfully")
    print(f"✓ Detected {sum(len(tables) for tables in sheets_with_tables.values())} total tables across {len(sheets_with_tables)} sheets\n")

    if not sheets_with_tables:
        raise RuntimeError("No data found in Google Sheets")

    return sheets_with_tables
