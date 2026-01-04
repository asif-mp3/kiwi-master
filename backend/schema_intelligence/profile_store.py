"""
Profile Store - Manages table profiles with caching and persistence.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime


PROFILES_PATH = "data_sources/table_profiles.json"


class ProfileStore:
    """
    Manages table profiles with caching and persistence.
    Provides intelligent table lookup and scoring.
    """

    def __init__(self, profiles_path: str = PROFILES_PATH):
        self._profiles: Dict[str, dict] = {}
        self._profiles_path = profiles_path
        self._load_profiles()

    def _load_profiles(self):
        """Load profiles from disk"""
        try:
            if Path(self._profiles_path).exists():
                with open(self._profiles_path, 'r', encoding='utf-8') as f:
                    self._profiles = json.load(f)
                print(f"  Loaded {len(self._profiles)} table profiles from disk")
        except Exception as e:
            print(f"  Warning: Could not load profiles: {e}")
            self._profiles = {}

    def save_profiles(self):
        """Persist profiles to disk"""
        try:
            Path(self._profiles_path).parent.mkdir(parents=True, exist_ok=True)
            with open(self._profiles_path, 'w', encoding='utf-8') as f:
                json.dump(self._profiles, f, indent=2, default=str)
            print(f"  Saved {len(self._profiles)} table profiles to disk")
        except Exception as e:
            print(f"  Warning: Could not save profiles: {e}")

    def get_profile(self, table_name: str) -> Optional[dict]:
        """Get profile for a specific table"""
        return self._profiles.get(table_name)

    def set_profile(self, table_name: str, profile: dict):
        """Set profile for a table"""
        profile['profiled_at'] = datetime.now().isoformat()
        self._profiles[table_name] = profile

    def get_all_profiles(self) -> Dict[str, dict]:
        """Get all profiles"""
        return self._profiles.copy()

    def get_table_names(self) -> List[str]:
        """Get list of all profiled table names"""
        return list(self._profiles.keys())

    def clear_profiles(self):
        """Clear all profiles"""
        self._profiles = {}

    def delete_profile(self, table_name: str) -> bool:
        """Delete profile for a specific table"""
        if table_name in self._profiles:
            del self._profiles[table_name]
            return True
        return False

    def get_tables_by_type(self, table_type: str) -> List[str]:
        """Get all tables of a specific type"""
        return [name for name, p in self._profiles.items()
                if p.get('table_type') == table_type]

    def get_tables_for_month(self, month: str) -> List[str]:
        """Get tables that cover a specific month"""
        month_lower = month.lower()
        results = []

        for name, profile in self._profiles.items():
            # Check table name
            if month_lower in name.lower():
                results.append(name)
                continue

            # Check date range
            date_range = profile.get('date_range', {})
            profile_month = date_range.get('month', '')
            if profile_month and profile_month.lower() == month_lower:
                results.append(name)

        return results

    def get_tables_with_column(self, column_term: str) -> List[str]:
        """Find tables that have a column matching the search term"""
        column_lower = column_term.lower()
        results = []

        for name, profile in self._profiles.items():
            columns = profile.get('columns', {})
            synonym_map = profile.get('synonym_map', {})

            # Direct column name match
            for col_name in columns.keys():
                if column_lower in col_name.lower():
                    results.append(name)
                    break

            # Synonym match
            if name not in results:
                for term, cols in synonym_map.items():
                    if column_lower in term.lower():
                        results.append(name)
                        break

        return results

    def find_best_table_for_query(self, entities: Dict[str, Any]) -> List[Tuple[str, int]]:
        """
        Find tables that match query entities.
        Returns list of (table_name, score) tuples sorted by score descending.

        Scoring criteria:
        - +30: Month explicitly matches table name
        - +25: Month matches table's date range
        - +20: Metric column exists with exact match
        - +15: Metric column exists via synonym
        - +15: Has required dimension (category, location)
        - +10: Is transactional type (preferred for detail queries)
        - -20: Is summary type (penalized for detail queries)
        - +10: Quality bonus (up to 10 based on quality score)
        """
        scores = []

        for table_name, profile in self._profiles.items():
            score = 0
            match_reasons = []

            # --- Month matching ---
            if entities.get('month'):
                month_lower = entities['month'].lower()

                # Check table name
                if month_lower in table_name.lower():
                    score += 30
                    match_reasons.append(f"month_in_name:{entities['month']}")
                else:
                    # Check date range
                    date_range = profile.get('date_range', {})
                    profile_month = date_range.get('month', '')
                    if profile_month and profile_month.lower() == month_lower:
                        score += 25
                        match_reasons.append(f"month_in_range:{entities['month']}")

            # --- Metric matching ---
            if entities.get('metric'):
                metric_lower = entities['metric'].lower()
                columns = profile.get('columns', {})
                synonym_map = profile.get('synonym_map', {})

                # Try direct column match
                col_match = False
                for col_name, col_info in columns.items():
                    if col_info.get('role') == 'metric':
                        if metric_lower in col_name.lower():
                            score += 20
                            match_reasons.append(f"metric_direct:{col_name}")
                            col_match = True
                            break

                # Try synonym match
                if not col_match:
                    for term, cols in synonym_map.items():
                        if metric_lower in term.lower():
                            score += 15
                            match_reasons.append(f"metric_synonym:{term}")
                            break

            # --- Category matching ---
            if entities.get('category'):
                category_lower = entities['category'].lower()
                columns = profile.get('columns', {})

                # PRIORITY: Check if table NAME contains "category" (e.g., "By_Category")
                # These are the best tables for category-specific queries
                if 'category' in table_name.lower() or 'by_cat' in table_name.lower():
                    score += 30  # Strong boost for category tables
                    match_reasons.append(f"table_name_has_category")

                for col_name, col_info in columns.items():
                    if col_info.get('role') == 'dimension':
                        unique_values = col_info.get('unique_values', [])
                        # Check if category value exists in column
                        if any(category_lower in str(v).lower() for v in unique_values):
                            score += 15
                            match_reasons.append(f"category_match:{col_name}")
                            break
                        # Check if column name suggests categories
                        if 'category' in col_name.lower():
                            score += 10
                            match_reasons.append(f"has_category_col:{col_name}")
                            break

            # --- Location matching ---
            if entities.get('location'):
                columns = profile.get('columns', {})
                for col_name, col_info in columns.items():
                    if col_info.get('role') in ['dimension', 'identifier']:
                        unique_values = col_info.get('unique_values', [])
                        location_lower = entities['location'].lower()
                        if any(location_lower in str(v).lower() for v in unique_values):
                            score += 15
                            match_reasons.append(f"location_match:{col_name}")
                            break

            # --- Table type scoring ---
            table_type = profile.get('table_type', 'unknown')

            if table_type == 'transactional':
                score += 10
                match_reasons.append("type:transactional")
            elif table_type == 'summary':
                # Penalize summary tables unless explicitly asked
                if entities.get('aggregation') not in ['SUM', 'AVG', 'MAX', 'MIN']:
                    score -= 20
                    match_reasons.append("type:summary_penalty")
            elif table_type == 'category_breakdown':
                # Boost if asking about categories
                if entities.get('category'):
                    score += 15
                    match_reasons.append("type:category_breakdown_boost")

            # --- Granularity preference ---
            granularity = profile.get('granularity', 'unknown')
            if granularity == 'daily':
                score += 5
                match_reasons.append("granularity:daily")

            # --- Quality bonus ---
            quality = profile.get('data_quality_score', 0)
            quality_bonus = int(quality * 10)
            if quality_bonus > 0:
                score += quality_bonus
                match_reasons.append(f"quality:{quality_bonus}")

            # Only include tables with positive score
            if score > 0:
                scores.append((table_name, score, match_reasons))

        # Sort by score descending
        scores.sort(key=lambda x: x[1], reverse=True)

        # Return just table name and score
        return [(name, score) for name, score, _ in scores]

    def get_match_explanation(self, table_name: str, entities: Dict[str, Any]) -> str:
        """
        Explain why a table matches the given entities.
        Useful for debugging and transparency.
        """
        profile = self._profiles.get(table_name)
        if not profile:
            return f"Table '{table_name}' not found in profiles"

        explanations = []

        if entities.get('month'):
            month_lower = entities['month'].lower()
            if month_lower in table_name.lower():
                explanations.append(f"Table name contains '{entities['month']}'")
            date_range = profile.get('date_range', {})
            if date_range.get('month', '').lower() == month_lower:
                explanations.append(f"Date range covers {entities['month']}")

        if entities.get('metric'):
            columns = profile.get('columns', {})
            for col_name in columns.keys():
                if entities['metric'].lower() in col_name.lower():
                    explanations.append(f"Has column '{col_name}' matching metric")

        if entities.get('category'):
            explanations.append(f"May contain category '{entities['category']}'")

        if not explanations:
            explanations.append("No specific match found")

        return "; ".join(explanations)

    def get_column_for_term(self, table_name: str, term: str) -> Optional[str]:
        """
        Find the actual column name in a table that matches a search term.
        Returns the column name or None.
        """
        profile = self._profiles.get(table_name)
        if not profile:
            return None

        term_lower = term.lower()
        columns = profile.get('columns', {})
        synonym_map = profile.get('synonym_map', {})

        # Direct match
        for col_name in columns.keys():
            if term_lower in col_name.lower():
                return col_name

        # Synonym match
        for syn_term, cols in synonym_map.items():
            if term_lower in syn_term.lower() and cols:
                return cols[0]

        return None

    def get_metric_columns(self, table_name: str) -> List[str]:
        """Get all metric columns for a table"""
        profile = self._profiles.get(table_name)
        if not profile:
            return []

        columns = profile.get('columns', {})
        return [col for col, info in columns.items() if info.get('role') == 'metric']

    def get_dimension_columns(self, table_name: str) -> List[str]:
        """Get all dimension columns for a table"""
        profile = self._profiles.get(table_name)
        if not profile:
            return []

        columns = profile.get('columns', {})
        return [col for col, info in columns.items() if info.get('role') == 'dimension']

    def get_date_columns(self, table_name: str) -> List[str]:
        """Get all date columns for a table"""
        profile = self._profiles.get(table_name)
        if not profile:
            return []

        columns = profile.get('columns', {})
        return [col for col, info in columns.items() if info.get('role') == 'date']

    # =========================================================================
    # Schema Inquiry Methods - Template-based responses (NO LLM)
    # =========================================================================

    def format_profile_for_user(self, table_name: str = None, language: str = 'en') -> str:
        """
        Format table profile(s) as user-friendly description.
        Uses templates - NO LLM to avoid hallucination.
        Returns brief summary with offer to show more details.

        Args:
            table_name: Specific table reference (e.g., "sheet 1", "sales table")
                       If None, returns summary of all tables.
            language: 'en' for English, 'ta' for Tamil
        """
        if table_name:
            profile = self._find_profile_by_reference(table_name)
            if not profile:
                available = ", ".join(self.get_table_names()[:5])
                more = f"... and {len(self._profiles) - 5} more" if len(self._profiles) > 5 else ""
                if language == 'ta':
                    return f"'{table_name}' என்ற அட்டவணை கிடைக்கவில்லை. கிடைக்கும் அட்டவணைகள்: {available}{more}"
                return f"I couldn't find a table called '{table_name}'. Available tables: {available}{more}"
            return self._format_brief_summary(profile, language)
        else:
            return self._format_all_tables_summary(language)

    def _format_brief_summary(self, profile: dict, language: str = 'en') -> str:
        """
        Brief summary with follow-up offer (Interactive approach).
        Template-based - NO LLM involvement.
        """
        name = profile.get('table_name', 'Unknown')
        rows = profile.get('row_count', 0)
        table_type = profile.get('table_type', 'data')

        # Get key columns by role
        cols = profile.get('columns', {})
        metrics = [c for c, info in cols.items() if info.get('role') == 'metric'][:3]
        dates = [c for c, info in cols.items() if info.get('role') == 'date'][:1]
        dimensions = [c for c, info in cols.items() if info.get('role') == 'dimension'][:3]

        # Get date range if available
        date_range = profile.get('date_range', {})
        date_info = ""
        if date_range:
            month = date_range.get('month', '')
            if month:
                date_info = f" ({month})"

        if language == 'ta':
            metrics_str = ', '.join(metrics) if metrics else 'இல்லை'
            date_col = dates[0] if dates else 'இல்லை'
            dims_str = ', '.join(dimensions) if dimensions else 'இல்லை'

            return (
                f"**{name}**{date_info} - {rows:,} வரிசைகள் உள்ளன.\n\n"
                f"📊 **முக்கிய metrics:** {metrics_str}\n"
                f"📅 **Date column:** {date_col}\n"
                f"📁 **Dimensions:** {dims_str}\n\n"
                f"மேலும் விவரம் வேண்டுமா? 'show all columns' அல்லது 'describe {name} in detail' என்று கேளுங்கள்."
            )

        metrics_str = ', '.join(metrics) if metrics else 'None found'
        date_col = dates[0] if dates else 'None found'
        dims_str = ', '.join(dimensions) if dimensions else 'None found'

        return (
            f"**{name}**{date_info} is a {table_type} table with {rows:,} rows.\n\n"
            f"📊 **Key metrics:** {metrics_str}\n"
            f"📅 **Date column:** {date_col}\n"
            f"📁 **Dimensions:** {dims_str}\n\n"
            f"Want more details? Ask 'show all columns' or 'describe {name} in detail'."
        )

    def _format_all_tables_summary(self, language: str = 'en') -> str:
        """
        Summary of all available tables.
        Template-based - NO LLM involvement.
        """
        profiles = self.get_all_profiles()
        if not profiles:
            if language == 'ta':
                return "இன்னும் எந்த அட்டவணையும் ஏற்றப்படவில்லை. முதலில் ஒரு dataset இணைக்கவும்."
            return "No tables loaded yet. Please connect a dataset first."

        if language == 'ta':
            lines = ["**கிடைக்கும் அட்டவணைகள்:**\n"]
        else:
            lines = ["**Available Tables:**\n"]

        for idx, (name, profile) in enumerate(list(profiles.items())[:10]):
            rows = profile.get('row_count', 0)
            table_type = profile.get('table_type', 'data')
            date_range = profile.get('date_range', {})
            month = date_range.get('month', '')
            month_info = f" ({month})" if month else ""

            lines.append(f"• **{name}**{month_info} - {table_type}, {rows:,} rows")

        if len(profiles) > 10:
            remaining = len(profiles) - 10
            if language == 'ta':
                lines.append(f"\n...மேலும் {remaining} அட்டவணைகள் உள்ளன.")
            else:
                lines.append(f"\n...and {remaining} more tables.")

        if language == 'ta':
            lines.append("\nகுறிப்பிட்ட அட்டவணை பற்றி கேளுங்கள்: 'what is [table name]'")
        else:
            lines.append("\nAsk about any specific table: 'what is [table name]'")

        return "\n".join(lines)

    def _find_profile_by_reference(self, table_ref: str) -> Optional[dict]:
        """
        Find profile by flexible reference (sheet 1, sales table, etc.).
        Supports:
        - Direct name match
        - Sheet number reference (sheet 1 → first table)
        - Scored partial/substring match (best match, not first)
        - Word-based match with coverage scoring
        - Fuzzy matching for typos (80% threshold)
        """
        import re
        from difflib import SequenceMatcher

        if not table_ref:
            return None

        ref_lower = table_ref.lower().strip()
        table_names = self.get_table_names()

        if not table_names:
            return None

        # 1. Direct exact match (case-insensitive)
        for name in table_names:
            if name.lower() == ref_lower:
                return self.get_profile(name)

        # 2. Sheet number reference (sheet 1 → first table)
        # Use word boundaries to avoid matching "sheet123sales"
        sheet_match = re.search(r'\bsheet\s*[_]?\s*(\d+)\b', ref_lower)
        if sheet_match:
            idx = int(sheet_match.group(1)) - 1  # 1-indexed to 0-indexed
            if 0 <= idx < len(table_names):
                return self.get_profile(table_names[idx])

        # 3. Scored substring match - return BEST match, not first
        # Score by how much extra the table name has beyond the search term
        substring_matches = []
        for name in table_names:
            name_lower = name.lower()
            if ref_lower in name_lower:
                # Penalty = extra characters in name (smaller = better match)
                penalty = len(name_lower) - len(ref_lower)
                substring_matches.append((name, penalty))
            elif name_lower in ref_lower:
                # Table name is contained in search - higher penalty
                penalty = len(ref_lower) - len(name_lower) + 10
                substring_matches.append((name, penalty))

        if substring_matches:
            # Sort by penalty (ascending) - best match first
            substring_matches.sort(key=lambda x: x[1])
            return self.get_profile(substring_matches[0][0])

        # 4. Word-based match with coverage scoring
        ref_words = set(ref_lower.replace('_', ' ').split())
        word_matches = []
        for name in table_names:
            name_words = set(name.lower().replace('_', ' ').split())
            common = ref_words & name_words
            if common:
                # Score: common words count, then coverage percentage
                coverage = len(common) / max(len(ref_words), 1)
                word_matches.append((name, len(common), coverage))

        if word_matches:
            # Sort by common word count (desc), then coverage (desc)
            word_matches.sort(key=lambda x: (x[1], x[2]), reverse=True)
            return self.get_profile(word_matches[0][0])

        # 5. Fuzzy matching for typos (80% threshold)
        fuzzy_matches = []
        for name in table_names:
            ratio = SequenceMatcher(None, ref_lower, name.lower()).ratio()
            if ratio >= 0.8:  # 80% similarity threshold
                fuzzy_matches.append((name, ratio))

        if fuzzy_matches:
            # Sort by similarity (descending) - best match first
            fuzzy_matches.sort(key=lambda x: x[1], reverse=True)
            return self.get_profile(fuzzy_matches[0][0])

        return None

    def format_detailed_profile(self, table_name: str, language: str = 'en') -> str:
        """
        Detailed profile with all columns listed.
        Template-based - NO LLM involvement.
        """
        profile = self._find_profile_by_reference(table_name)
        if not profile:
            available = ", ".join(self.get_table_names()[:5])
            if language == 'ta':
                return f"'{table_name}' என்ற அட்டவணை கிடைக்கவில்லை. கிடைக்கும்: {available}"
            return f"Table '{table_name}' not found. Available: {available}"

        name = profile.get('table_name', 'Unknown')
        rows = profile.get('row_count', 0)
        table_type = profile.get('table_type', 'data')
        columns = profile.get('columns', {})

        # Group columns by role
        metrics = []
        dates = []
        dimensions = []
        identifiers = []
        others = []

        for col_name, col_info in columns.items():
            role = col_info.get('role', 'unknown')
            dtype = col_info.get('dtype', 'unknown')
            entry = f"{col_name} ({dtype})"

            if role == 'metric':
                metrics.append(entry)
            elif role == 'date':
                dates.append(entry)
            elif role == 'dimension':
                dimensions.append(entry)
            elif role == 'identifier':
                identifiers.append(entry)
            else:
                others.append(entry)

        if language == 'ta':
            lines = [
                f"## {name} - முழு விவரம்",
                f"",
                f"**வகை:** {table_type}",
                f"**வரிசைகள்:** {rows:,}",
                f"**மொத்த columns:** {len(columns)}",
                f"",
            ]
        else:
            lines = [
                f"## {name} - Full Details",
                f"",
                f"**Type:** {table_type}",
                f"**Rows:** {rows:,}",
                f"**Total columns:** {len(columns)}",
                f"",
            ]

        if metrics:
            lines.append(f"**📊 Metrics ({len(metrics)}):** {', '.join(metrics)}")
        if dates:
            lines.append(f"**📅 Date columns ({len(dates)}):** {', '.join(dates)}")
        if dimensions:
            lines.append(f"**📁 Dimensions ({len(dimensions)}):** {', '.join(dimensions)}")
        if identifiers:
            lines.append(f"**🔑 Identifiers ({len(identifiers)}):** {', '.join(identifiers)}")
        if others:
            lines.append(f"**📄 Other ({len(others)}):** {', '.join(others)}")

        return "\n".join(lines)
