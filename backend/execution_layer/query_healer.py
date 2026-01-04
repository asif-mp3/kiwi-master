"""
Query Healer - Self-healing query executor that retries with fixes on failure.
Handles common SQL errors automatically without user intervention.
"""

import re
from typing import Tuple, Optional, Dict, Any, List
from dataclasses import dataclass
import pandas as pd


@dataclass
class HealingAttempt:
    """Record of a healing attempt"""
    attempt_number: int
    original_sql: str
    fixed_sql: str
    error: str
    fix_type: str
    success: bool


class QueryExecutionError(Exception):
    """Custom exception for query execution failures after all retries"""

    def __init__(self, message: str, attempts: List[HealingAttempt] = None):
        super().__init__(message)
        self.attempts = attempts or []


class QueryHealer:
    """
    Self-healing query executor that automatically fixes common SQL errors.

    Error types handled:
    1. Column not found - Try synonyms, case variations
    2. Type mismatch - Add CAST() operations
    3. Table not found - Try case-insensitive match
    4. Syntax errors - Fix common issues (quotes, operators)
    5. Empty results - Relax filters progressively
    6. Binder errors - Fix column references
    """

    MAX_RETRIES = 3

    def __init__(self, db_manager=None, profile_store=None):
        # Lazy imports to avoid circular dependencies
        self._db = db_manager
        self._profile_store = profile_store
        self._healing_history: List[HealingAttempt] = []

    @property
    def db(self):
        if self._db is None:
            from analytics_engine.duckdb_manager import DuckDBManager
            self._db = DuckDBManager()
        return self._db

    @property
    def profile_store(self):
        if self._profile_store is None:
            from schema_intelligence.profile_store import ProfileStore
            self._profile_store = ProfileStore()
        return self._profile_store

    def execute_with_healing(self, sql: str, plan: Dict[str, Any]) -> Tuple[pd.DataFrame, str]:
        """
        Execute SQL with automatic error recovery.

        Args:
            sql: The SQL query to execute
            plan: The query plan (for context about table, columns, etc.)

        Returns:
            (result_df, final_sql) - The result and the SQL that worked
        """
        self._healing_history = []
        # Defensive check: ensure plan is a dict
        if not isinstance(plan, dict):
            raise QueryExecutionError(f"Invalid plan type: expected dict, got {type(plan).__name__}")
        table_name = plan.get('table')
        profile = self.profile_store.get_profile(table_name) if table_name else None

        current_sql = sql
        last_error = None

        for attempt in range(self.MAX_RETRIES):
            try:
                result = self.db.query(current_sql)

                # Check for empty results
                if result.empty and attempt < self.MAX_RETRIES - 1:
                    # Only relax if we have filters to relax
                    if plan.get('filters') or plan.get('subset_filters'):
                        relaxed_sql = self._relax_filters(current_sql, plan)
                        if relaxed_sql != current_sql:
                            print(f"  [Healer] Empty result, relaxing filters (attempt {attempt + 2})")
                            self._record_attempt(attempt + 1, current_sql, relaxed_sql,
                                                "Empty result", "relax_filters", False)
                            current_sql = relaxed_sql
                            continue

                # Success!
                return result, current_sql

            except Exception as e:
                last_error = str(e)
                print(f"  [Healer] Error on attempt {attempt + 1}: {last_error[:100]}")

                fixed_sql = self._diagnose_and_fix(current_sql, last_error, plan, profile)

                if fixed_sql and fixed_sql != current_sql:
                    fix_type = self._get_fix_type(last_error)
                    print(f"  [Healer] Applying fix: {fix_type}")
                    self._record_attempt(attempt + 1, current_sql, fixed_sql,
                                        last_error, fix_type, False)
                    current_sql = fixed_sql
                else:
                    # Can't fix, record and break
                    self._record_attempt(attempt + 1, current_sql, current_sql,
                                        last_error, "no_fix_available", False)
                    break

        # All retries failed
        raise QueryExecutionError(
            f"Query failed after {self.MAX_RETRIES} attempts. Last error: {last_error}",
            attempts=self._healing_history
        )

    def _record_attempt(self, attempt_num: int, original: str, fixed: str,
                       error: str, fix_type: str, success: bool):
        """Record a healing attempt for debugging"""
        self._healing_history.append(HealingAttempt(
            attempt_number=attempt_num,
            original_sql=original,
            fixed_sql=fixed,
            error=error,
            fix_type=fix_type,
            success=success
        ))

    def _diagnose_and_fix(self, sql: str, error: str, plan: Dict[str, Any],
                         profile: Optional[Dict]) -> Optional[str]:
        """
        Diagnose error and return fixed SQL.
        """
        error_lower = error.lower()

        # Column not found / Binder Error
        if any(term in error_lower for term in ['column', 'binder', 'not found', 'does not exist', 'no column']):
            fixed = self._fix_column_not_found(sql, error, plan, profile)
            if fixed:
                return fixed

        # Type mismatch / Cast error
        if any(term in error_lower for term in ['cast', 'type', 'conversion', 'cannot compare']):
            fixed = self._fix_type_mismatch(sql, error, plan, profile)
            if fixed:
                return fixed

        # Table not found
        if 'table' in error_lower and any(term in error_lower for term in ['not found', 'does not exist', 'no table']):
            fixed = self._fix_table_not_found(sql, plan)
            if fixed:
                return fixed

        # Syntax error
        if 'syntax' in error_lower or 'parse' in error_lower:
            fixed = self._fix_syntax_error(sql, error)
            if fixed:
                return fixed

        # Ambiguous column reference
        if 'ambiguous' in error_lower:
            fixed = self._fix_ambiguous_column(sql, error, plan)
            if fixed:
                return fixed

        return None

    def _fix_column_not_found(self, sql: str, error: str, plan: Dict[str, Any],
                             profile: Optional[Dict]) -> Optional[str]:
        """
        Fix column not found by trying:
        1. Case-insensitive match
        2. Synonym lookup from profile
        3. Fuzzy column name match
        """
        # Extract missing column name from error
        # DuckDB has many error variations for column not found:
        # - "Binder Error: Referenced column \"X\" not found"
        # - "column \"X\" does not exist"
        # - "no column named X"
        # - "Referenced column X not found in FROM clause"
        # - "Catalog Error: Table with name X does not contain column Y"
        patterns = [
            # Most specific patterns first
            r'Binder Error.*Referenced column\s+["\']?([^"\']+)["\']?\s+not found',
            r'Binder Error.*column[:\s]+["\']?([^"\']+)["\']?',
            r'does not contain column\s+["\']?([^"\']+)["\']?',
            r'Referenced column\s+["\']?([^"\']+)["\']?\s+not found',
            r'column\s+["\']([^"\']+)["\'].*not found',
            r'column\s+["\']([^"\']+)["\'].*does not exist',
            r'no column named\s+["\']?([^"\']+?)["\']?\s',
            r'unknown column[:\s]+["\']?([^"\']+)["\']?',
            # Generic patterns as fallback
            r'column[:\s]+["\']?(\w+(?:\s+\w+)*)["\']?',
            r'["\']([^"\']+)["\'].*(?:not found|does not exist)',
        ]

        missing_col = None
        for pattern in patterns:
            match = re.search(pattern, error, re.IGNORECASE)
            if match:
                missing_col = match.group(1).strip()
                # Clean up any trailing punctuation
                missing_col = missing_col.rstrip('.,;:')
                if missing_col and len(missing_col) > 0:
                    break

        if not missing_col:
            return None

        # Get actual columns from profile
        if profile:
            columns = profile.get('columns', {})
            synonym_map = profile.get('synonym_map', {})

            # Try case-insensitive match
            for actual_col in columns.keys():
                if actual_col.lower() == missing_col.lower():
                    return self._replace_column_in_sql(sql, missing_col, actual_col)

            # Try synonym lookup
            for term, actual_cols in synonym_map.items():
                if missing_col.lower() in term.lower() or term.lower() in missing_col.lower():
                    for actual_col in actual_cols:
                        if actual_col in columns:
                            return self._replace_column_in_sql(sql, missing_col, actual_col)

            # Try fuzzy match (contains)
            for actual_col in columns.keys():
                if missing_col.lower() in actual_col.lower() or actual_col.lower() in missing_col.lower():
                    return self._replace_column_in_sql(sql, missing_col, actual_col)

            # Try fuzzy matching for typos (80% similarity threshold)
            from difflib import SequenceMatcher
            best_match = None
            best_ratio = 0.75  # Minimum threshold

            for actual_col in columns.keys():
                ratio = SequenceMatcher(None, missing_col.lower(), actual_col.lower()).ratio()
                if ratio > best_ratio:
                    best_ratio = ratio
                    best_match = actual_col

            if best_match:
                print(f"    [Healer] Fuzzy matched '{missing_col}' to '{best_match}' ({best_ratio:.0%})")
                return self._replace_column_in_sql(sql, missing_col, best_match)

        # Try getting columns from database directly
        table_name = plan.get('table')
        if table_name:
            try:
                # Query to get actual column names
                schema_sql = f'DESCRIBE "{table_name}"'
                schema_df = self.db.query(schema_sql)
                actual_columns = schema_df['column_name'].tolist() if 'column_name' in schema_df.columns else []

                for actual_col in actual_columns:
                    if actual_col.lower() == missing_col.lower():
                        return self._replace_column_in_sql(sql, missing_col, actual_col)

            except Exception:
                pass

        return None

    def _replace_column_in_sql(self, sql: str, old_col: str, new_col: str) -> str:
        """Replace column name in SQL, handling quotes"""
        # Try quoted replacement first
        result = sql.replace(f'"{old_col}"', f'"{new_col}"')
        if result != sql:
            return result

        # Try unquoted replacement with word boundaries
        result = re.sub(rf'\b{re.escape(old_col)}\b', f'"{new_col}"', sql)
        return result

    def _fix_type_mismatch(self, sql: str, error: str, plan: Dict[str, Any],
                          profile: Optional[Dict]) -> Optional[str]:
        """
        Fix type mismatches by adding CAST() operations.
        """
        # Common patterns:
        # - Comparing string to number: add CAST to VARCHAR
        # - Comparing number to string: add CAST to numeric type
        # - Date format issues: standardize date format

        # Pattern: Column = 'value' where column is numeric
        # Fix: CAST("Column" AS VARCHAR) = 'value' or TRY_CAST('value' AS DOUBLE)

        # Try wrapping string comparisons with appropriate casts
        modified = sql

        # Find comparison patterns
        comparison_pattern = r'"([^"]+)"\s*(=|>|<|>=|<=|<>|!=)\s*\'([^\']+)\''
        matches = re.findall(comparison_pattern, sql)

        for col_name, operator, value in matches:
            if profile:
                columns = profile.get('columns', {})
                col_info = columns.get(col_name, {})

                # If column is numeric, try casting the value
                if col_info.get('role') == 'metric':
                    try:
                        # If value looks numeric, cast column comparison
                        float(value.replace(',', '').replace('$', '').replace('₹', ''))
                        old_pattern = f'"{col_name}" {operator} \'{value}\''
                        new_pattern = f'"{col_name}" {operator} {value.replace(",", "")}'
                        modified = modified.replace(old_pattern, new_pattern)
                    except ValueError:
                        # Value is not numeric, cast column to string
                        old_pattern = f'"{col_name}" {operator} \'{value}\''
                        new_pattern = f'CAST("{col_name}" AS VARCHAR) {operator} \'{value}\''
                        modified = modified.replace(old_pattern, new_pattern)
            else:
                # Without profile, try safe cast approach
                old_pattern = f'"{col_name}" {operator} \'{value}\''
                new_pattern = f'CAST("{col_name}" AS VARCHAR) {operator} \'{value}\''
                modified = modified.replace(old_pattern, new_pattern)

        if modified != sql:
            return modified

        # Try TRY_CAST for numeric conversions
        try_cast_pattern = r"CAST\(([^)]+)\s+AS\s+(INTEGER|DOUBLE|FLOAT|DECIMAL)\)"
        modified = re.sub(try_cast_pattern, r"TRY_CAST(\1 AS \2)", sql, flags=re.IGNORECASE)

        if modified != sql:
            return modified

        return None

    def _fix_table_not_found(self, sql: str, plan: Dict[str, Any]) -> Optional[str]:
        """
        Fix table not found by trying case-insensitive and partial matches.
        """
        table_name = plan.get('table')
        if not table_name:
            return None

        # Get all available tables
        all_profiles = self.profile_store.get_all_profiles()
        all_tables = list(all_profiles.keys())

        # Also try getting tables from database
        try:
            db_tables = self.db.list_tables()
            all_tables = list(set(all_tables + db_tables))
        except Exception:
            pass

        # Try case-insensitive match
        for actual_table in all_tables:
            if actual_table.lower() == table_name.lower():
                return sql.replace(f'"{table_name}"', f'"{actual_table}"')

        # Try partial match (contains)
        for actual_table in all_tables:
            if table_name.lower() in actual_table.lower():
                return sql.replace(f'"{table_name}"', f'"{actual_table}"')

        # Try word overlap match
        table_words = set(table_name.lower().replace('-', ' ').replace('–', ' ').split())
        best_match = None
        best_overlap = 0

        for actual_table in all_tables:
            actual_words = set(actual_table.lower().replace('-', ' ').replace('–', ' ').split())
            overlap = len(table_words & actual_words)
            if overlap > best_overlap:
                best_overlap = overlap
                best_match = actual_table

        if best_match and best_overlap >= len(table_words) * 0.5:
            return sql.replace(f'"{table_name}"', f'"{best_match}"')

        return None

    def _fix_syntax_error(self, sql: str, error: str) -> Optional[str]:
        """
        Fix common SQL syntax errors.
        """
        modified = sql

        # Fix 1: Double quotes in string values should be single quotes
        # e.g., WHERE name = "John" -> WHERE name = 'John'
        modified = re.sub(
            r'=\s*"([^"]+)"(?!\s*(?:AND|OR|ORDER|GROUP|LIMIT|$))',
            r"= '\1'",
            modified
        )

        # Fix 2: Single quotes around column names should be double
        # e.g., SELECT 'column' -> SELECT "column"
        # Be careful not to change string literals

        # Fix 3: Missing quotes around column names with spaces
        column_pattern = r'(?:SELECT|FROM|WHERE|GROUP BY|ORDER BY)\s+([A-Za-z][A-Za-z0-9 ]+[A-Za-z0-9])(?=\s|,|$)'
        for match in re.finditer(column_pattern, modified, re.IGNORECASE):
            col = match.group(1)
            if ' ' in col and not (col.startswith('"') or col.startswith("'")):
                modified = modified.replace(col, f'"{col}"')

        # Fix 4: LIKE operator with = instead of LIKE
        # e.g., WHERE category = '%Dairy%' -> WHERE category LIKE '%Dairy%'
        like_fix_pattern = r'=\s*\'(%[^\']+%)\''
        modified = re.sub(like_fix_pattern, r"LIKE '\1'", modified)

        if modified != sql:
            return modified

        return None

    def _fix_ambiguous_column(self, sql: str, error: str, plan: Dict[str, Any]) -> Optional[str]:
        """
        Fix ambiguous column references by qualifying with table name.
        """
        table_name = plan.get('table')
        if not table_name:
            return None

        # Extract ambiguous column name from error
        match = re.search(r'["\']([^"\']+)["\'].*ambiguous', error, re.IGNORECASE)
        if not match:
            return None

        ambiguous_col = match.group(1)

        # Qualify with table name
        # Replace "column" with "table"."column"
        old_pattern = f'"{ambiguous_col}"'
        new_pattern = f'"{table_name}"."{ambiguous_col}"'

        return sql.replace(old_pattern, new_pattern)

    def _relax_filters(self, sql: str, plan: Dict[str, Any]) -> str:
        """
        Relax filters progressively to get more results.
        """
        modified = sql

        # Strategy 1: Increase LIMIT
        limit_match = re.search(r'LIMIT\s+(\d+)', modified, re.IGNORECASE)
        if limit_match:
            current_limit = int(limit_match.group(1))
            if current_limit < 100:
                new_limit = min(current_limit * 10, 1000)
                modified = re.sub(r'LIMIT\s+\d+', f'LIMIT {new_limit}', modified, flags=re.IGNORECASE)

        # Strategy 2: Make LIKE patterns more generous
        # e.g., LIKE 'Dairy' -> LIKE '%Dairy%'
        like_pattern = r"LIKE\s+'([^%][^']*[^%])'"
        modified = re.sub(like_pattern, r"LIKE '%\1%'", modified, flags=re.IGNORECASE)

        # Strategy 3: Convert exact matches to LIKE for text columns
        # e.g., = 'Chennai' -> LIKE '%Chennai%'
        # Only do this if there are filters in the plan
        if plan.get('filters') or plan.get('subset_filters'):
            # Get text columns from profile
            table_name = plan.get('table')
            profile = self.profile_store.get_profile(table_name) if table_name else None

            if profile:
                text_columns = [col for col, info in profile.get('columns', {}).items()
                               if info.get('role') in ['dimension', 'identifier']]

                for col in text_columns:
                    # Pattern: "Column" = 'value'
                    pattern = rf'"{re.escape(col)}"\s*=\s*\'([^\']+)\''
                    replacement = rf'"{col}" LIKE \'%\1%\''
                    modified = re.sub(pattern, replacement, modified)

        if modified != sql:
            return modified

        # Strategy 4: Remove one filter at a time
        # This is aggressive - only do if other strategies didn't help
        filters = plan.get('filters', []) + plan.get('subset_filters', [])
        if len(filters) > 1:
            # Remove the last filter from WHERE clause
            where_match = re.search(r'WHERE\s+(.+?)(?=\s+(?:GROUP|ORDER|LIMIT|$))', sql, re.IGNORECASE | re.DOTALL)
            if where_match:
                where_clause = where_match.group(1)
                # Split by AND and remove last condition
                conditions = re.split(r'\s+AND\s+', where_clause, flags=re.IGNORECASE)
                if len(conditions) > 1:
                    new_where = ' AND '.join(conditions[:-1])
                    modified = sql.replace(where_clause, new_where)

        return modified

    def _get_fix_type(self, error: str) -> str:
        """Get human-readable description of fix type"""
        error_lower = error.lower()

        if any(term in error_lower for term in ['column', 'binder', 'not found']):
            return "column_name_fix"
        if any(term in error_lower for term in ['cast', 'type', 'conversion']):
            return "type_cast_fix"
        if 'table' in error_lower:
            return "table_name_fix"
        if 'syntax' in error_lower:
            return "syntax_fix"
        if 'ambiguous' in error_lower:
            return "ambiguous_column_fix"

        return "generic_fix"

    def get_healing_history(self) -> List[HealingAttempt]:
        """Get the history of healing attempts for the last query"""
        return self._healing_history.copy()

    def explain_healing(self) -> str:
        """
        Get a human-readable explanation of healing attempts.
        """
        if not self._healing_history:
            return "No healing attempts recorded."

        lines = ["Query Healing Report:", "=" * 40]

        for attempt in self._healing_history:
            lines.append(f"\nAttempt {attempt.attempt_number}:")
            lines.append(f"  Error: {attempt.error[:100]}...")
            lines.append(f"  Fix type: {attempt.fix_type}")
            lines.append(f"  Success: {'Yes' if attempt.success else 'No'}")

            if attempt.fixed_sql != attempt.original_sql:
                lines.append(f"  Changes applied: Yes")
            else:
                lines.append(f"  Changes applied: No (no fix found)")

        return "\n".join(lines)
