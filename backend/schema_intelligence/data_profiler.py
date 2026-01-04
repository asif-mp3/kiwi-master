"""
Data Profiler - Analyzes tables to create semantic profiles for intelligent routing.
Works with ANY dataset structure.
"""

import pandas as pd
import numpy as np
import re
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime


class DataProfiler:
    """
    Profiles tables to enable intelligent query routing.
    Creates comprehensive metadata about table structure, content, and semantics.
    """

    # Common metric keywords for column classification
    METRIC_KEYWORDS = [
        'sales', 'amount', 'revenue', 'profit', 'cost', 'price',
        'order', 'quantity', 'count', 'total', 'gross', 'net',
        'value', 'shipping', 'tax', 'gst', 'aov', 'discount',
        'subtotal', 'margin', 'expense', 'income', 'balance'
    ]

    # Common dimension keywords
    DIMENSION_KEYWORDS = [
        'category', 'type', 'status', 'channel', 'region', 'area',
        'zone', 'department', 'group', 'segment', 'class', 'tier'
    ]

    # Common identifier keywords
    IDENTIFIER_KEYWORDS = [
        'name', 'id', 'code', 'sku', 'item', 'product', 'customer',
        'employee', 'vendor', 'supplier', 'account', 'number'
    ]

    # Month names for detection (English + Tamil)
    MONTH_NAMES = {
        # English
        'january': 1, 'jan': 1,
        'february': 2, 'feb': 2,
        'march': 3, 'mar': 3,
        'april': 4, 'apr': 4,
        'may': 5,
        'june': 6, 'jun': 6,
        'july': 7, 'jul': 7,
        'august': 8, 'aug': 8,
        'september': 9, 'sep': 9, 'sept': 9,
        'october': 10, 'oct': 10,
        'november': 11, 'nov': 11,
        'december': 12, 'dec': 12,
        # Tamil month names
        'ஜனவரி': 1,
        'பிப்ரவரி': 2,
        'மார்ச்': 3,
        'ஏப்ரல்': 4,
        'மே': 5,
        'ஜூன்': 6,
        'ஜூலை': 7,
        'ஆகஸ்ட்': 8,
        'செப்டம்பர்': 9,
        'அக்டோபர்': 10,
        'நவம்பர்': 11,
        'டிசம்பர்': 12,
    }

    def profile_table(self, table_name: str, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Create comprehensive profile for a table.

        Args:
            table_name: Name of the table
            df: DataFrame containing the table data

        Returns:
            Dict containing complete table profile
        """
        if df is None or df.empty:
            return self._empty_profile(table_name)

        # Classify columns
        columns = self._classify_columns(df)

        # Build synonym map
        synonym_map = self._build_synonym_map(columns)

        # Detect table type
        table_type = self._detect_table_type(table_name, df, columns)

        # Detect granularity
        granularity = self._detect_granularity(df, columns)

        # Extract date range
        date_range = self._extract_date_range(df, columns, table_name)

        # Calculate quality score
        quality_score = self._calculate_quality_score(df)

        # Extract keywords from table name
        keywords = self._extract_keywords(table_name)

        # Determine primary use case
        primary_use = self._determine_primary_use(table_type, granularity, date_range, table_name)

        return {
            'table_name': table_name,
            'table_type': table_type,
            'granularity': granularity,
            'date_range': date_range,
            'columns': columns,
            'synonym_map': synonym_map,
            'data_quality_score': quality_score,
            'row_count': len(df),
            'column_count': len(df.columns),
            'keywords': keywords,
            'primary_use': primary_use,
            'profiled_at': datetime.now().isoformat()
        }

    def _empty_profile(self, table_name: str) -> Dict[str, Any]:
        """Create profile for empty table"""
        return {
            'table_name': table_name,
            'table_type': 'unknown',
            'granularity': 'unknown',
            'date_range': {'min': None, 'max': None, 'month': None},
            'columns': {},
            'synonym_map': {},
            'data_quality_score': 0.0,
            'row_count': 0,
            'column_count': 0,
            'keywords': self._extract_keywords(table_name),
            'primary_use': 'unknown',
            'profiled_at': datetime.now().isoformat()
        }

    def _detect_table_type(self, table_name: str, df: pd.DataFrame, columns: Dict) -> str:
        """
        Detect table type using multiple signals.

        Types:
        - transactional: Regular data with dates and metrics
        - summary: Aggregated/calculation data
        - category_breakdown: Data broken down by category
        - pivot: Pivoted data with dates/categories as columns
        - item_level: Product/item-level data
        - lookup: Reference/lookup table
        - unknown: Cannot determine
        """
        name_lower = table_name.lower()

        # Check name for type hints
        if any(kw in name_lower for kw in ['calculation', 'run rate', 'summary']):
            return 'summary'

        if 'by category' in name_lower or 'breakdown' in name_lower:
            return 'category_breakdown'

        if 'pivot' in name_lower:
            return 'pivot'

        if any(kw in name_lower for kw in ['item', 'product', 'sku']):
            return 'item_level'

        if any(kw in name_lower for kw in ['lookup', 'reference', 'master']):
            return 'lookup'

        # Check structure
        if len(df) == 1:
            return 'summary'

        if len(df) <= 5 and self._has_metric_structure(df, columns):
            return 'summary'

        # Check for pivot structure (many numeric columns with date/month names)
        if self._is_pivot_structure(df):
            return 'pivot'

        # Default: check for transactional pattern
        has_date = any(info.get('role') == 'date' for info in columns.values())
        has_metric = any(info.get('role') == 'metric' for info in columns.values())

        if has_date and has_metric:
            return 'transactional'

        if has_metric and not has_date:
            return 'summary'

        return 'unknown'

    def _detect_granularity(self, df: pd.DataFrame, columns: Dict) -> str:
        """
        Detect time granularity from date columns.
        """
        # Find date columns
        date_cols = [col for col, info in columns.items() if info.get('role') == 'date']

        if not date_cols:
            # Check if columns are months (pivot table)
            month_cols = [c for c in df.columns if self._is_month_name(c)]
            if month_cols:
                return 'monthly_pivot'
            return 'unknown'

        # Analyze date frequency from first date column
        for col in date_cols:
            try:
                dates = pd.to_datetime(df[col], errors='coerce').dropna()
                if len(dates) < 2:
                    continue

                # Sort and calculate median difference
                dates = dates.sort_values()
                diff = dates.diff().dropna().median()

                if pd.isna(diff):
                    continue

                if diff <= pd.Timedelta(days=1):
                    return 'daily'
                elif diff <= pd.Timedelta(days=7):
                    return 'weekly'
                elif diff <= pd.Timedelta(days=35):
                    return 'monthly'
                elif diff <= pd.Timedelta(days=100):
                    return 'quarterly'
                elif diff <= pd.Timedelta(days=400):
                    return 'yearly'

            except Exception:
                continue

        return 'unknown'

    def _extract_date_range(self, df: pd.DataFrame, columns: Dict, table_name: str) -> Dict:
        """
        Extract date range from date columns and table name.
        """
        result = {'min': None, 'max': None, 'month': None, 'months': []}

        # Extract month from table name
        name_lower = table_name.lower()
        for month_name, month_num in self.MONTH_NAMES.items():
            if month_name in name_lower:
                result['month'] = month_name.capitalize()
                result['months'].append(month_name.capitalize())
                break

        # Find date columns
        date_cols = [col for col, info in columns.items() if info.get('role') == 'date']

        min_date, max_date = None, None

        for col in date_cols:
            try:
                dates = pd.to_datetime(df[col], errors='coerce').dropna()
                if len(dates) > 0:
                    col_min = dates.min()
                    col_max = dates.max()

                    min_date = col_min if min_date is None else min(min_date, col_min)
                    max_date = col_max if max_date is None else max(max_date, col_max)
            except Exception:
                continue

        if min_date is not None:
            result['min'] = min_date.isoformat()
        if max_date is not None:
            result['max'] = max_date.isoformat()

        # Extract month from date range if not found in name
        if not result['month'] and min_date is not None and max_date is not None:
            # If dates are within same month, set that month
            if min_date.month == max_date.month and min_date.year == max_date.year:
                month_names = list(self.MONTH_NAMES.keys())
                # Find full month name
                for name, num in self.MONTH_NAMES.items():
                    if num == min_date.month and len(name) > 3:
                        result['month'] = name.capitalize()
                        break

        return result

    def _classify_columns(self, df: pd.DataFrame) -> Dict[str, Dict]:
        """
        Classify each column by role and extract metadata.
        """
        classifications = {}

        for col in df.columns:
            col_data = df[col]
            # Ensure column name is a string (some tables have numeric headers)
            col_str = str(col)
            col_lower = col_str.lower()

            # Skip empty columns
            if col_data.isna().all():
                classifications[col] = {
                    'role': 'empty',
                    'dtype': str(col_data.dtype),
                    'null_ratio': 1.0,
                    'synonyms': []
                }
                continue

            # Calculate basic stats
            non_null_count = col_data.notna().sum()
            null_ratio = 1 - (non_null_count / len(col_data)) if len(col_data) > 0 else 1.0

            # Check for date
            if self._is_date_column(col_data, col):
                date_format = self._detect_date_format(col_data)
                classifications[col] = {
                    'role': 'date',
                    'dtype': str(col_data.dtype),
                    'format': date_format,
                    'null_ratio': null_ratio,
                    'synonyms': ['date', 'time', 'day', 'period']
                }
                continue

            # Check for numeric
            if pd.api.types.is_numeric_dtype(col_data):
                # Determine if metric or dimension
                is_metric = any(kw in col_lower for kw in self.METRIC_KEYWORDS)
                cardinality = col_data.nunique()

                if is_metric or cardinality > 20:
                    # It's a metric
                    metric_type = self._detect_metric_type(col_lower)
                    synonyms = self._generate_metric_synonyms(col)
                    classifications[col] = {
                        'role': 'metric',
                        'dtype': str(col_data.dtype),
                        'metric_type': metric_type,
                        'null_ratio': null_ratio,
                        'min': float(col_data.min()) if not col_data.isna().all() else None,
                        'max': float(col_data.max()) if not col_data.isna().all() else None,
                        'mean': float(col_data.mean()) if not col_data.isna().all() else None,
                        'synonyms': synonyms
                    }
                else:
                    # Low cardinality numeric - treat as dimension
                    classifications[col] = {
                        'role': 'dimension',
                        'dtype': str(col_data.dtype),
                        'cardinality': cardinality,
                        'null_ratio': null_ratio,
                        'unique_values': list(col_data.dropna().unique()[:20]),
                        'synonyms': self._generate_dimension_synonyms(col)
                    }
                continue

            # Text column - dimension or identifier
            cardinality = col_data.nunique()
            is_identifier = any(kw in col_lower for kw in self.IDENTIFIER_KEYWORDS)

            if is_identifier or cardinality > 50:
                # High cardinality = identifier
                classifications[col] = {
                    'role': 'identifier',
                    'dtype': 'text',
                    'cardinality': cardinality,
                    'null_ratio': null_ratio,
                    'sample_values': list(col_data.dropna().head(5).astype(str)),
                    'synonyms': self._generate_identifier_synonyms(col)
                }
            else:
                # Low cardinality = dimension
                unique_values = list(col_data.dropna().unique()[:30])
                classifications[col] = {
                    'role': 'dimension',
                    'dtype': 'text',
                    'cardinality': cardinality,
                    'null_ratio': null_ratio,
                    'unique_values': [str(v) for v in unique_values],
                    'synonyms': self._generate_dimension_synonyms(col)
                }

        return classifications

    def _is_date_column(self, col_data: pd.Series, col_name: str) -> bool:
        """Check if column contains date data"""
        col_lower = col_name.lower()

        # Check name hints
        date_hints = ['date', 'time', 'timestamp', 'created', 'updated', 'day', 'month', 'year']
        if any(hint in col_lower for hint in date_hints):
            # Verify it's actually date-like
            try:
                dates = pd.to_datetime(col_data, errors='coerce')
                valid_ratio = dates.notna().sum() / len(col_data) if len(col_data) > 0 else 0
                if valid_ratio > 0.5:
                    return True
            except Exception:
                pass

        # Check dtype
        if pd.api.types.is_datetime64_any_dtype(col_data):
            return True

        # Try parsing as date
        if col_data.dtype == object:
            try:
                non_null = col_data.dropna()
                if len(non_null) > 0:
                    # Sample a few values
                    sample = non_null.head(10)
                    dates = pd.to_datetime(sample, errors='coerce')
                    valid_ratio = dates.notna().sum() / len(sample)
                    if valid_ratio > 0.7:
                        return True
            except Exception:
                pass

        return False

    def _detect_date_format(self, col_data: pd.Series) -> str:
        """Detect the date format used in the column"""
        non_null = col_data.dropna().astype(str)

        if len(non_null) == 0:
            return 'unknown'

        # Check a few samples
        for val in non_null.head(10):
            val_str = str(val)

            # Check for DD/MM/YYYY vs MM/DD/YYYY
            if re.match(r'\d{1,2}/\d{1,2}/\d{4}', val_str):
                parts = val_str.split('/')
                if len(parts) == 3:
                    first = int(parts[0])
                    second = int(parts[1])
                    if first > 12:
                        return 'DD/MM/YYYY'
                    elif second > 12:
                        return 'MM/DD/YYYY'

            # ISO format
            if re.match(r'\d{4}-\d{2}-\d{2}', val_str):
                return 'YYYY-MM-DD'

        # Default to DD/MM/YYYY (international)
        return 'DD/MM/YYYY'

    def _detect_metric_type(self, col_name: str) -> str:
        """Detect the type of metric"""
        col_lower = col_name.lower()

        if any(kw in col_lower for kw in ['sales', 'revenue', 'income']):
            return 'revenue'
        if any(kw in col_lower for kw in ['profit', 'margin']):
            return 'profit'
        if any(kw in col_lower for kw in ['cost', 'expense']):
            return 'cost'
        if any(kw in col_lower for kw in ['order', 'transaction', 'count']):
            return 'count'
        if any(kw in col_lower for kw in ['quantity', 'unit', 'qty']):
            return 'quantity'
        if any(kw in col_lower for kw in ['tax', 'gst', 'vat']):
            return 'tax'
        if any(kw in col_lower for kw in ['shipping', 'delivery', 'freight']):
            return 'shipping'
        if any(kw in col_lower for kw in ['discount', 'rebate']):
            return 'discount'
        if any(kw in col_lower for kw in ['aov', 'average']):
            return 'average'

        return 'amount'

    def _generate_metric_synonyms(self, col_name: str) -> List[str]:
        """Generate synonyms for a metric column"""
        col_lower = col_name.lower()
        synonyms = []

        # Add base terms
        if 'sales' in col_lower or 'revenue' in col_lower:
            synonyms.extend(['sales', 'revenue', 'amount', 'value', 'total'])
        if 'order' in col_lower:
            synonyms.extend(['orders', 'order count', 'transactions'])
        if 'profit' in col_lower:
            synonyms.extend(['profit', 'margin', 'earnings'])
        if 'gross' in col_lower:
            synonyms.append('gross')
        if 'net' in col_lower:
            synonyms.append('net')
        if 'quantity' in col_lower or 'qty' in col_lower:
            synonyms.extend(['quantity', 'qty', 'units', 'items'])

        return list(set(synonyms))

    def _generate_dimension_synonyms(self, col_name: str) -> List[str]:
        """Generate synonyms for a dimension column"""
        col_lower = col_name.lower()
        synonyms = []

        if 'category' in col_lower:
            synonyms.extend(['category', 'type', 'group'])
        if 'region' in col_lower or 'area' in col_lower:
            synonyms.extend(['region', 'area', 'location', 'zone'])
        if 'channel' in col_lower:
            synonyms.extend(['channel', 'source', 'platform'])
        if 'status' in col_lower:
            synonyms.extend(['status', 'state', 'condition'])

        return list(set(synonyms))

    def _generate_identifier_synonyms(self, col_name: str) -> List[str]:
        """Generate synonyms for an identifier column"""
        col_lower = col_name.lower()
        synonyms = []

        if 'name' in col_lower:
            synonyms.extend(['name', 'title', 'label'])
        if 'product' in col_lower or 'item' in col_lower:
            synonyms.extend(['product', 'item', 'sku', 'article'])
        if 'customer' in col_lower:
            synonyms.extend(['customer', 'client', 'buyer'])

        return list(set(synonyms))

    def _build_synonym_map(self, columns: Dict) -> Dict[str, List[str]]:
        """
        Build reverse mapping from common terms to actual column names.
        """
        synonym_map = {}

        # Common search terms
        common_terms = {
            'sales': ['sales', 'revenue', 'amount', 'value', 'total', 'gross sales'],
            'orders': ['orders', 'order count', 'transactions', 'order'],
            'profit': ['profit', 'margin', 'net profit', 'gross profit', 'earnings'],
            'quantity': ['quantity', 'qty', 'units', 'items', 'count'],
            'date': ['date', 'time', 'day', 'period', 'timestamp'],
            'category': ['category', 'type', 'group', 'segment'],
            'product': ['product', 'item', 'sku', 'name', 'article'],
            'location': ['location', 'region', 'area', 'zone', 'city']
        }

        for col_name, col_info in columns.items():
            col_lower = col_name.lower()
            synonyms = col_info.get('synonyms', [])

            # Check which common terms match this column
            for term, term_synonyms in common_terms.items():
                # Check if column name contains any of the term synonyms
                matches = any(syn in col_lower for syn in term_synonyms)
                # Or if column's synonyms overlap with term synonyms
                matches = matches or bool(set(synonyms) & set(term_synonyms))

                if matches:
                    if term not in synonym_map:
                        synonym_map[term] = []
                    if col_name not in synonym_map[term]:
                        synonym_map[term].append(col_name)

        return synonym_map

    def _calculate_quality_score(self, df: pd.DataFrame) -> float:
        """
        Calculate data quality score (0-1).
        Higher score = better quality, more reliable for queries.
        """
        if len(df) == 0:
            return 0.0

        scores = []

        # 1. Completeness (40% weight)
        total_cells = df.size
        non_null = df.notna().sum().sum()
        completeness = non_null / total_cells if total_cells > 0 else 0
        scores.append(('completeness', completeness, 0.4))

        # 2. Row count factor (20% weight)
        # Prefer tables with more data, up to a point
        row_factor = min(1.0, len(df) / 100)
        scores.append(('row_factor', row_factor, 0.2))

        # 3. Column consistency (20% weight)
        # Check for mixed types in text columns
        consistency = 1.0
        for col in df.columns:
            if df[col].dtype == object:
                # Check if column has mostly consistent type
                non_null = df[col].dropna()
                if len(non_null) > 0:
                    types = non_null.apply(type).nunique()
                    if types > 1:
                        consistency -= 0.05
        consistency = max(0, consistency)
        scores.append(('consistency', consistency, 0.2))

        # 4. Column variety (20% weight)
        # Having both metrics and dimensions is good
        has_variety = len(df.columns) >= 3
        variety_score = 1.0 if has_variety else 0.5
        scores.append(('variety', variety_score, 0.2))

        # Calculate weighted average
        total = sum(score * weight for _, score, weight in scores)
        return round(total, 3)

    def _is_pivot_structure(self, df: pd.DataFrame) -> bool:
        """Check if dataframe has pivot structure (dates/months as columns)"""
        # Count columns that look like dates or months
        date_like_cols = 0
        for col in df.columns:
            col_str = str(col).lower()
            # Check for month names
            if any(month in col_str for month in self.MONTH_NAMES.keys()):
                date_like_cols += 1
            # Check for date patterns in column name
            elif re.match(r'\d{1,2}/\d{1,2}|\d{4}-\d{2}', col_str):
                date_like_cols += 1

        # If more than 3 columns look like dates/months, it's probably a pivot
        return date_like_cols >= 3

    def _has_metric_structure(self, df: pd.DataFrame, columns: Dict) -> bool:
        """Check if table has summary/metric structure"""
        # Summary tables often have metric names in first column
        if len(df.columns) >= 2:
            first_col = df.columns[0]
            first_col_data = df[first_col].dropna()

            # Check if first column contains metric-like labels
            metric_labels = ['sales', 'orders', 'profit', 'revenue', 'total', 'count', 'average']
            if first_col_data.dtype == object:
                values_lower = first_col_data.astype(str).str.lower()
                if any(any(label in val for label in metric_labels) for val in values_lower):
                    return True

        return False

    def _is_month_name(self, col_name: str) -> bool:
        """Check if column name is a month name"""
        col_lower = str(col_name).lower().strip()
        return col_lower in self.MONTH_NAMES

    def _extract_keywords(self, table_name: str) -> List[str]:
        """Extract searchable keywords from table name"""
        # Remove common prefixes/suffixes
        name = table_name.lower()

        # Split on non-alphanumeric
        words = re.split(r'[^a-z0-9]+', name)

        # Filter out common stop words
        stop_words = {'table', 'data', 'sheet', 'the', 'a', 'an', 'of', 'in', 'on', 'at', 'to', 'for'}
        keywords = [w for w in words if w and len(w) > 2 and w not in stop_words]

        # Add month if found
        for month in self.MONTH_NAMES.keys():
            if month in name and len(month) > 3:
                keywords.append(month)

        return list(set(keywords))

    def _determine_primary_use(self, table_type: str, granularity: str,
                               date_range: Dict, table_name: str) -> str:
        """Determine the primary use case for this table"""
        name_lower = table_name.lower()

        if table_type == 'summary':
            return 'aggregated metrics and calculations'

        if table_type == 'category_breakdown':
            return 'category-level analysis and comparison'

        if table_type == 'pivot':
            return 'time-series comparison across periods'

        if table_type == 'item_level':
            return 'product/item performance analysis'

        if table_type == 'lookup':
            return 'reference data lookup'

        if table_type == 'transactional':
            month = date_range.get('month', '')
            if month:
                return f'{month} {granularity} transaction data'
            return f'{granularity} transaction data'

        return 'general data analysis'
