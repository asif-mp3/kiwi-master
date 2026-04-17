"""
Profile Store - Manages table profiles with caching and persistence.
"""

import json
import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
from utils.logger import get_logger

logger = get_logger("profile_store")


# Use path relative to this module's location, not current working directory
_MODULE_DIR = Path(__file__).parent.parent  # backend directory
PROFILES_PATH = str(_MODULE_DIR / "data_sources" / "table_profiles.json")


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
                logger.info("Loaded %d table profiles from disk", len(self._profiles))
        except Exception as e:
            logger.warning("Could not load profiles: %s", e)
            self._profiles = {}

    def save_profiles(self):
        """Persist profiles to disk with guaranteed write"""
        try:
            Path(self._profiles_path).parent.mkdir(parents=True, exist_ok=True)
            with open(self._profiles_path, 'w', encoding='utf-8') as f:
                json.dump(self._profiles, f, indent=2, default=str)
                f.flush()
                os.fsync(f.fileno())  # Ensure write completes before returning
            logger.info("Saved %d table profiles to disk", len(self._profiles))
        except Exception as e:
            logger.warning("Could not save profiles: %s", e)

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
        - +50: Table name contains keyword from query (e.g., "attendance" matches "Attendance Records")
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

        # Extract keywords from the raw question for table name matching
        raw_question = entities.get('raw_question', '').lower()
        # Strip parenthetical content — "(like UPI, cash, credit card etc)" is examples, not intent
        raw_question = re.sub(r'\([^)]*\)', ' ', raw_question).strip()
        # Get significant words (>= 4 chars, exclude common words)
        # EXPANDED: Include generic English words that cause false matches on column names/values
        stop_words = {
            # Question/grammar words
            'what', 'where', 'when', 'which', 'how', 'tell', 'show', 'give', 'find',
            'the', 'and', 'for', 'from', 'with', 'about', 'this', 'that', 'have', 'does',
            'will', 'would', 'could', 'should', 'shall', 'were', 'been', 'being',
            'some', 'many', 'much', 'more', 'most', 'very', 'also', 'just', 'only',
            'into', 'over', 'under', 'than', 'then', 'each', 'every', 'both',
            # Meta/abstract words that match column values but aren't data terms
            'quality', 'general', 'standard', 'special', 'regular', 'basic',
            'premium', 'normal', 'default', 'custom', 'other', 'unknown',
            'good', 'look', 'like', 'make', 'take', 'keep', 'know', 'think',
            'want', 'need', 'help', 'work', 'feel', 'seem', 'call', 'come',
            'information', 'detail', 'details', 'overview', 'summary',
            'analysis', 'insight', 'insights', 'interesting', 'something',
            'performance', 'status', 'result', 'results', 'report',
        }

        # Important short keywords that should ALWAYS be included even if < 4 chars
        # These are domain-specific terms that often appear in table/column names
        important_short_keywords = {'sku', 'id', 'hr', 'upi', 'qty', 'atm', 'pos', 'cod', 'emi',
                                   'tax', 'gst', 'mrp', 'avg', 'sum', 'min', 'max', 'top', 'kpi'}

        query_keywords = []
        for w in raw_question.split():
            w_lower = w.lower().strip('?.,!:;')
            # Include if: (1) important short keyword, OR (2) >= 4 chars and not stop word
            if w_lower in important_short_keywords:
                query_keywords.append(w_lower)
            elif len(w_lower) >= 4 and w_lower not in stop_words:
                query_keywords.append(w_lower)

        # --- NEGATION-AWARE KEYWORD SUPPRESSION ---
        # If user says "don't want the branch details", remove "branch" from keywords
        # so it doesn't boost the Branch_Details table
        _negation_patterns = [
            r"(?:don'?t|do\s+not|not|no)\s+(?:want|need|use|show|from)\s+(?:the\s+)?(\w+(?:\s+\w+)?)",
            r"(?:instead\s+of|rather\s+than)\s+(?:the\s+)?(\w+(?:\s+\w+)?)",
        ]
        _negated_words = set()
        for _np in _negation_patterns:
            for _m in re.finditer(_np, raw_question):
                _negated_words.update(_m.group(1).lower().split())
        if _negated_words:
            query_keywords = [kw for kw in query_keywords if kw not in _negated_words]

        # --- CRITICAL: EXPLICIT TABLE NAME PHRASE MATCHING ---
        # When query contains a phrase like "top 20 branches", it should STRONGLY match
        # table "Top_20_Branches_Table1". This is a direct table reference, not keyword matching.
        # Pre-compute table name match scores for phrase matching
        table_phrase_scores = {}
        for table_name, profile in self._profiles.items():
            # Normalize table name: replace underscores/numbers with spaces, lowercase
            table_name_normalized = table_name.lower().replace('_', ' ')
            # Remove common suffixes like "table1", "sheet1" for cleaner matching
            for suffix in ['table1', 'table2', 'table3', 'sheet1', 'sheet2', 'sheet3']:
                table_name_normalized = table_name_normalized.replace(suffix, '').strip()

            # Check if query contains a multi-word phrase matching the table name
            # e.g., "top 20 branches" matches "top 20 branches" from "Top_20_Branches_Table1"
            if table_name_normalized and len(table_name_normalized) >= 5:
                # Check if the normalized table name appears as a phrase in the query
                if table_name_normalized in raw_question:
                    # Check for negation context: "don't want branch details" means AVOID it
                    _negation_prefixes = [
                        "don't want", "dont want", "not the ", "not this ",
                        "instead of", "not from", "don't need", "dont need",
                    ]
                    _match_pos = raw_question.index(table_name_normalized)
                    _prefix_text = raw_question[max(0, _match_pos - 25):_match_pos]
                    _is_negated = any(neg in _prefix_text for neg in _negation_prefixes)

                    if _is_negated:
                        # User explicitly doesn't want this table — penalize instead
                        table_phrase_scores[table_name] = -200
                    else:
                        # VERY strong match - explicit table name reference
                        table_phrase_scores[table_name] = 300
                else:
                    # Check word-by-word overlap for partial phrase matching
                    table_words = [w for w in table_name_normalized.split() if len(w) >= 2]
                    if len(table_words) >= 2:
                        # Count consecutive matching words
                        matched_words = sum(1 for tw in table_words if tw in raw_question)
                        if matched_words >= 2:
                            # Multiple words from table name found in query
                            match_ratio = matched_words / len(table_words)
                            if match_ratio >= 0.6:  # At least 60% of table name words match
                                table_phrase_scores[table_name] = int(200 * match_ratio)

        for table_name, profile in self._profiles.items():
            score = 0
            match_reasons = []
            table_type = profile.get('table_type', 'unknown')

            # --- APPLY EXPLICIT TABLE NAME PHRASE MATCHING ---
            # This is the HIGHEST priority - if user mentions "top 20 branches",
            # table "Top_20_Branches_Table1" should almost always win
            if table_name in table_phrase_scores:
                phrase_score = table_phrase_scores[table_name]
                score += phrase_score
                match_reasons.append(f"EXPLICIT_TABLE_PHRASE_MATCH:+{phrase_score}")

            # --- CRITICAL: Table name keyword match ---
            # Strong boost when table name contains keywords from the query
            # e.g., "attendance" in query matches "Attendance Records Table1"
            # Also handles simple plurals: "categories" matches "category"
            table_name_lower = table_name.lower()
            for keyword in query_keywords:
                # Try exact substring match first
                if keyword in table_name_lower:
                    score += 50  # Strong boost for keyword match
                    match_reasons.append(f"table_name_keyword_match:{keyword}")
                    break
                # Try stem match: strip common suffixes (s, es, ies→y)
                stem = keyword
                if stem.endswith('ies'):
                    stem = stem[:-3] + 'y'  # categories → category
                elif stem.endswith('es'):
                    stem = stem[:-2]  # branches → branch
                elif stem.endswith('s') and not stem.endswith('ss'):
                    stem = stem[:-1]  # products → product
                if stem != keyword and stem in table_name_lower:
                    score += 50
                    match_reasons.append(f"table_name_keyword_match:{keyword}~{stem}")
                    break

            # --- PENALTY: Top_N/Partial tables for COUNT queries ---
            # When user asks "how many", "total number", "count of", they need COMPLETE data
            # Top_N tables only have partial data and would return WRONG counts
            is_count_query = any(phrase in raw_question for phrase in [
                'how many', 'total number', 'count of', 'number of', 'all branches',
                'all employees', 'all categories', 'all areas', 'all items'
            ])
            is_partial_table = any(x in table_name_lower for x in ['top_', 'top10', 'top20', 'top50', 'top100'])

            if is_count_query and is_partial_table:
                # HEAVY penalty - partial data tables should NEVER be used for count queries
                score -= 300
                match_reasons.append("HEAVY_PENALTY:partial_table_for_count_query:-300")

            # --- PENALTY: Category tables for location queries ---
            # "Sales by area" should NOT go to category tables even if they have area columns
            is_location_query = any(loc in raw_question for loc in [
                'area', 'branch', 'location', 'pincode', 'zone', 'state', 'city', 'region'
            ])
            is_category_table = 'category' in table_name_lower

            if is_location_query and is_category_table:
                # Strong penalty - location queries should go to location tables
                score -= 200
                match_reasons.append("PENALTY:category_table_for_location_query:-200")

            # --- INTENT-BASED TABLE ROUTING ---
            # For broad/generalized queries, detect the INTENT from raw_question
            # and boost tables whose names match that intent.
            # This bypasses stop_words so "summary", "performance", "trend" still match.
            # ORDERING MATTERS: Specific intents FIRST, generic ones LAST.
            # All keywords here are UNIVERSAL business terms — no dataset-specific terms.
            _intent_map = {
                # --- Specific intents (check first) ---
                'attendance': (['attendance', 'leave', 'check-in', 'checkin', 'absent', 'present'],
                               ['attendance', 'department']),
                'department': (['department', 'departments', 'dept', 'department wise', 'department summary'],
                               ['department']),
                'payroll':    (['payroll', 'salary', 'salaries', 'compensation'],
                               ['payroll']),
                'hr':         (['employee', 'employees', 'staff', 'workforce'],
                               ['staff', 'employee', 'attendance']),
                'sku':        (['sku', 'individual item', 'product level', 'specific product', 'item level'],
                               ['sku']),
                'transaction':(['transaction', 'transactions', 'individual sales',
                                'day-by-day', 'day by day', 'raw data', 'actual entries'],
                               ['transaction', 'daily']),
                'cost':       (['cost', 'costs', 'expense', 'expenses'],
                               ['cost']),
                'payment':    (['payment', 'pay mode', 'payment mode', 'payment breakdown'],
                               ['payment']),
                'product':    (['product', 'products'],
                               ['category', 'sku']),
                # --- Generic intents (check last) ---
                'summary':    (['overall', 'summary', 'overview'],
                               ['summary', 'overall', 'performance', 'quarterly']),
                'trend':      (['trend', 'trends', 'trending', 'over time'],
                               ['trend', 'monthly']),
            }
            _detected_intent = None
            for _intent, (_words, _tbl_keys) in _intent_map.items():
                if any(w in raw_question for w in _words):
                    _detected_intent = _intent
                    for _tk in _tbl_keys:
                        if _tk in table_name_lower:
                            score += 120
                            match_reasons.append(f"INTENT:{_intent}_match:{_tk}")
                            break
                    # Also penalize transactional tables when intent is analysis/summary
                    if table_type == 'transactional' and _intent in (
                        'payment', 'cost', 'summary', 'trend', 'department', 'payroll'
                    ):
                        _analysis_words = ['breakdown', 'analysis', 'overview', 'summary',
                                           'mode', 'wise', 'combined']
                        if any(aw in raw_question for aw in _analysis_words):
                            score -= 50
                            match_reasons.append(f"PENALTY:transactional_for_{_intent}_analysis")
                    break  # Only match the first/strongest intent

            # --- DYNAMIC CROSS-DOMAIN PENALTY (dataset-agnostic) ---
            # Instead of hardcoding "HR keywords" and "Sales keywords", we derive
            # domain affinity from the actual loaded table profiles.
            # If a query keyword strongly matches column/table names in OTHER tables
            # but NOT in this table, this table is likely the wrong domain.
            if _detected_intent and query_keywords:
                # Build a set of words from THIS table's column names and table name
                _this_table_words = set()
                for _col_name in profile.get('columns', {}).keys():
                    _this_table_words.update(_col_name.lower().replace('_', ' ').split())
                _this_table_words.update(table_name_lower.replace('_', ' ').split())
                # Remove generic words that appear in every table
                _generic_table_words = {'id', 'name', 'total', 'date', 'type', 'value',
                                        'dataset', 'table', 'sheet', 'data', 'no', 'number'}
                _this_table_words -= _generic_table_words

                # Check: do OTHER tables have much stronger column-name affinity?
                _other_tables_with_keyword = 0
                _this_table_has_keyword = 0
                for _qk in query_keywords:
                    if len(_qk) < 4:
                        continue
                    # Check if this keyword appears in THIS table's columns/name
                    if _qk in _this_table_words:
                        _this_table_has_keyword += 1
                    # Check if this keyword appears in any OTHER table's name
                    for _other_name in self._profiles:
                        if _other_name == table_name:
                            continue
                        if _qk in _other_name.lower():
                            _other_tables_with_keyword += 1

                # If query keywords match OTHER table names but NOT this table's columns,
                # this table is likely wrong domain
                if _other_tables_with_keyword >= 1 and _this_table_has_keyword == 0:
                    # Check: does the intent keyword itself appear in this table's name?
                    _intent_in_this_table = any(
                        tk in table_name_lower for tk in _intent_map.get(_detected_intent, ([], []))[1]
                    )
                    if not _intent_in_this_table:
                        score -= 150
                        match_reasons.append("CROSS_DOMAIN_PENALTY:keywords_match_other_tables")

            # Penalize large detail/transactional tables for broad overview queries
            _is_broad = any(w in raw_question for w in [
                'overall', 'summary', 'overview', 'how is the business',
                'give me a', 'quick look', 'high level', 'breakdown',
            ])
            if _is_broad and table_type == 'transactional':
                score -= 30
                match_reasons.append("PENALTY:detail_table_for_broad_query")

            # --- DIMENSION COLUMN NAME MATCHING ---
            # Strong boost when query keywords match dimension column names
            # e.g., "payment modes" query should match "Payment_Mode" column
            columns = profile.get('columns', {})
            for keyword in query_keywords:
                keyword_lower = keyword.lower()
                # Skip common non-specific words that cause false column name matches
                if keyword_lower in {'used', 'data', 'this', 'that', 'show', 'list', 'types',
                                     'like', 'look', 'quality', 'general', 'standard',
                                     'good', 'make', 'want', 'need', 'help', 'work',
                                     'interesting', 'something', 'overview', 'summary'}:
                    continue
                for col_name, col_info in columns.items():
                    col_name_lower = col_name.lower().replace('_', ' ')
                    # Check if keyword matches the column name (handling underscores)
                    if keyword_lower in col_name_lower:
                        col_role = col_info.get('role', '')
                        if col_role == 'dimension':
                            # VERY strong boost - query asking about a specific dimension
                            score += 100
                            match_reasons.append(f"dimension_col_name_match:{col_name}:{keyword}")
                            break
                        elif col_role in ['identifier', 'metric']:
                            score += 30
                            match_reasons.append(f"col_name_match:{col_name}:{keyword}")
                            break

            # --- COMPOUND METRIC COLUMN MATCHING ---
            # Match compound terms like "sale amount" to "Sale_Amount" column
            # This is CRITICAL for queries like "total sale amount"
            for col_name, col_info in columns.items():
                if col_info.get('role') == 'metric':
                    col_name_lower = col_name.lower()
                    col_parts = col_name_lower.replace('_', ' ').split()
                    # Count how many query keywords match column name parts
                    matches = sum(1 for kw in query_keywords if kw.lower() in col_parts)
                    if matches >= 2:
                        # Strong match - multiple keywords match column name
                        score += 120
                        match_reasons.append(f"compound_metric_match:{col_name}:matches={matches}")
                    elif matches == 1 and len(col_parts) <= 2:
                        # Check if keyword EXACTLY matches the full column name
                        exact = any(kw.lower() == col_name_lower for kw in query_keywords)
                        if exact:
                            # VERY strong — query keyword is the metric column name
                            score += 100
                            match_reasons.append(f"EXACT_metric_match:{col_name}")
                        else:
                            # Single keyword match on short column name
                            score += 40
                            match_reasons.append(f"metric_keyword_match:{col_name}")

            # --- TRANSACTIONAL TABLE PREFERENCE ---
            # When query asks for "across all transactions", prefer transactional tables
            # with actual amounts over summary tables with counts
            table_type = profile.get('table_type', 'unknown')
            if 'transaction' in raw_question or 'across all' in raw_question:
                if table_type == 'transactional':
                    # Check if table has numeric metric columns (amounts, not just counts)
                    has_amount_col = any(
                        info.get('role') == 'metric' and info.get('dtype') in ('float64', 'int64')
                        for col, info in columns.items()
                    )
                    if has_amount_col:
                        score += 80
                        match_reasons.append("transactional_with_amounts")
                    else:
                        score += 30
                        match_reasons.append("transactional_table")
                elif table_type == 'summary':
                    # Penalize summary tables when asking about "all transactions"
                    score -= 40
                    match_reasons.append("PENALTY:summary_for_all_transactions")

            # --- TIME PERIOD GRANULARITY MATCHING ---
            # When query asks about "months", "quarterly", etc., boost tables with matching granularity
            granularity = profile.get('granularity', 'unknown')
            time_period_keywords = {
                'month': 'monthly', 'months': 'monthly', 'monthly': 'monthly',
                'quarter': 'quarterly', 'quarters': 'quarterly', 'quarterly': 'quarterly',
                'year': 'yearly', 'years': 'yearly', 'yearly': 'yearly', 'annual': 'yearly',
                'week': 'weekly', 'weeks': 'weekly', 'weekly': 'weekly',
                'day': 'daily', 'days': 'daily', 'daily': 'daily'
            }

            for keyword in query_keywords:
                if keyword in time_period_keywords:
                    expected_granularity = time_period_keywords[keyword]
                    if granularity == expected_granularity:
                        score += 100  # Strong boost for matching granularity
                        match_reasons.append(f"granularity_match:{keyword}->{granularity}")
                    # Also check if table name contains the time period
                    if keyword in table_name_lower or expected_granularity in table_name_lower:
                        score += 50
                        match_reasons.append(f"time_period_in_name:{keyword}")
                    # Check for Month/Quarter/Year column
                    for col_name, col_info in columns.items():
                        col_lower = col_name.lower()
                        if col_info.get('role') == 'date' and keyword in col_lower:
                            score += 60
                            match_reasons.append(f"time_column_match:{col_name}")
                            break

            # --- Value matching in sample_values ---
            # Check if query words match sample_values (IDs, names, etc.)
            columns = profile.get('columns', {})
            synonym_map = profile.get('synonym_map', {})
            for keyword in query_keywords:
                keyword_upper = keyword.upper()
                keyword_lower = keyword.lower()

                # Skip common words that shouldn't trigger value matching
                value_skip_words = {
                    'the', 'and', 'for', 'what', 'which', 'how', 'does', 'belong',
                    'state', 'department', 'data', 'used', 'this', 'that', 'show',
                    'list', 'types', 'like', 'look', 'quality', 'general', 'standard',
                    'good', 'make', 'want', 'need', 'help', 'work', 'feel',
                    'interesting', 'something', 'overview', 'summary', 'analysis',
                }
                if keyword_lower in value_skip_words:
                    continue

                for col_name, col_info in columns.items():
                    sample_values = col_info.get('sample_values', [])
                    col_role = col_info.get('role', '')

                    # Check if keyword matches any sample value
                    for sample in sample_values:
                        sample_str = str(sample).upper()
                        if keyword_upper == sample_str or keyword_upper in sample_str:
                            # ID patterns (EMP_004, TXN_001) get highest boost
                            if '_' in keyword or keyword.upper() == keyword:
                                score += 150  # VERY strong - exact ID match
                                match_reasons.append(f"id_value_match:{col_name}:{keyword}")
                            # Person names in identifier columns get strong boost
                            elif col_role == 'identifier' and keyword[0].isupper():
                                score += 120  # Strong - name match in identifier column
                                match_reasons.append(f"name_value_match:{col_name}:{keyword}")
                            else:
                                score += 80  # Moderate - general value match
                                match_reasons.append(f"value_match:{col_name}:{keyword}")
                            break
                    else:
                        continue
                    break  # Found match in this column, move to next keyword

            # --- Synonym map keyword match (dataset-agnostic) ---
            # If query keyword appears as a key in this table's synonym_map,
            # boost the table. Works for ANY dataset — no hardcoded domain terms.
            # VALIDATED: Only give full boost if mapped columns include metric columns.
            # Prevents "hours" → ["Start_Month", "End_Month"] from stealing routing.
            for keyword in query_keywords:
                keyword_lower = keyword.lower()
                if keyword_lower in synonym_map:
                    mapped_cols = synonym_map[keyword_lower]
                    if isinstance(mapped_cols, list) and mapped_cols:
                        has_metric_mapping = any(
                            columns.get(mc, {}).get('role') == 'metric'
                            for mc in mapped_cols
                        )
                        if has_metric_mapping:
                            score += 60
                            match_reasons.append(f"synonym_map_match:{keyword_lower}")
                        else:
                            # Synonym maps to non-metric columns — weak boost only
                            score += 10
                            match_reasons.append(f"synonym_map_weak:{keyword_lower}->non_metric")
                    else:
                        score += 60
                        match_reasons.append(f"synonym_map_match:{keyword_lower}")

            # --- Cross-table intent: Boost tables with aggregate columns ---
            # When user asks for "across all months" or "overall total", prefer tables
            # that have pre-computed aggregate columns or are summary tables
            # BUT: If dimension keywords are present, user wants DIMENSIONAL breakdown
            #      not just aggregates - reduce cross-table boost in that case
            dimension_keywords = entities.get('dimension_keywords', [])
            has_dimension_request = len(dimension_keywords) > 0

            if entities.get('cross_table_intent'):
                columns = profile.get('columns', {})
                table_type = profile.get('table_type', 'unknown')

                # Only give full aggregate boost if user isn't asking for specific dimension
                aggregate_boost = 40 if not has_dimension_request else 15
                summary_boost = 25 if not has_dimension_request else 10

                # Check for aggregate columns (total, grand total, sum, etc.)
                has_aggregate_col = False
                for col_name in columns.keys():
                    col_lower = col_name.lower()
                    if any(term in col_lower for term in ['total', 'grand', 'sum', 'overall', 'aggregate']):
                        has_aggregate_col = True
                        score += aggregate_boost
                        match_reasons.append(f"has_aggregate_col:{col_name}")
                        break

                # Boost summary tables for cross-table queries
                if table_type == 'summary':
                    score += summary_boost
                    match_reasons.append("type:summary_boost_cross_table")

                # If no month specified but cross-table intent, don't require month match
                # (the whole point is to get data across all months)

            # --- Multi-month comparison: PENALIZE month-specific tables ---
            # When comparing multiple months, we need tables with columns for ALL months,
            # NOT tables named after a single month (like "September_Detailed_Breakdown")
            all_months = entities.get('all_months', [])
            is_multi_month = entities.get('multi_month_comparison', False)

            if is_multi_month and len(all_months) >= 2:
                table_lower = table_name.lower()
                # Check if table name contains a specific month
                month_names = ['january', 'february', 'march', 'april', 'may', 'june',
                              'july', 'august', 'september', 'october', 'november', 'december']
                month_to_num = {m: i+1 for i, m in enumerate(month_names)}
                table_has_single_month = any(m in table_lower for m in month_names)

                if table_has_single_month:
                    # HEAVILY penalize month-specific tables for multi-month comparisons
                    score -= 100
                    match_reasons.append("PENALTY:month_specific_table_for_multi_month_query")

                # BOOST tables with columns for multiple months
                columns = profile.get('columns', {})
                months_in_cols = set()
                for col_name in columns.keys():
                    col_lower = col_name.lower()
                    for m in month_names:
                        if m in col_lower:
                            months_in_cols.add(m)

                if len(months_in_cols) >= 2:
                    # Table has multiple month columns - BOOST heavily
                    score += 80
                    match_reasons.append(f"BOOST:multi_month_columns:{len(months_in_cols)}")

                # CRITICAL: Also BOOST tables with DATE COLUMNS that span the required months
                # e.g., Daily_Sales_Transactions_Table1 has Date from Aug 1 to Dec 16
                # This is IDEAL for "compare August vs December" queries!
                date_range = profile.get('date_range', {})
                date_min = date_range.get('min', '')
                date_max = date_range.get('max', '')

                if date_min and date_max:
                    try:
                        # Extract month numbers from date range
                        # date_min format: "2025-08-01T00:00:00"
                        min_month = int(date_min[5:7]) if len(date_min) >= 7 else 0
                        max_month = int(date_max[5:7]) if len(date_max) >= 7 else 0

                        # Check if date range covers all requested months
                        requested_months_nums = []
                        for req_month in all_months:
                            req_month_lower = req_month.lower()
                            if req_month_lower in month_to_num:
                                requested_months_nums.append(month_to_num[req_month_lower])

                        if requested_months_nums:
                            min_requested = min(requested_months_nums)
                            max_requested = max(requested_months_nums)

                            # Check if table's date range covers requested months
                            covers_all = min_month <= min_requested and max_month >= max_requested
                            if covers_all:
                                # Check if table has a date column (transactional data)
                                has_date_col = any(
                                    col_info.get('role') == 'date'
                                    for col_info in columns.values()
                                )
                                if has_date_col:
                                    # HEAVILY boost - this table has granular date data spanning all months
                                    score += 100
                                    match_reasons.append(f"BOOST:date_range_spans_all_months:{date_min[:10]}_to_{date_max[:10]}")

                                    # Extra boost for transactional tables
                                    # These are IDEAL for month comparisons as they have row-level date data
                                    # Use table_type from profile instead of hardcoded keywords
                                    if table_type == 'transactional':
                                        score += 50
                                        match_reasons.append("BOOST:transactional_table_for_comparison")
                    except (ValueError, IndexError):
                        pass

            # --- Month matching (for single-month queries) ---
            if entities.get('month') and not is_multi_month:
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
                        col_lower = col_name.lower()
                        if metric_lower == col_lower:
                            # Exact entity metric match
                            score += 80
                            match_reasons.append(f"metric_direct_exact:{col_name}")
                            col_match = True
                            break
                        elif metric_lower in col_lower:
                            score += 40
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
                    score += 50  # VERY strong boost for category tables
                    match_reasons.append(f"table_name_has_category")

            # --- Location table name matching (parallel to category matching) ---
            # PRIORITY: Check if table NAME contains location keywords (e.g., "Pincode_Sales", "Area_Breakdown")
            # These are the best tables for location/area-specific queries
            location_table_keywords = ['area', 'pincode', 'zone', 'region', 'location', 'branch', 'zip']
            for loc_kw in location_table_keywords:
                if loc_kw in table_name.lower():
                    score += 50  # Same bonus as category tables
                    match_reasons.append(f"table_name_has_location:{loc_kw}")
                    break

            if entities.get('category'):
                # Check if any column NAME matches the category (e.g., "Batter & Dough" as column)
                # This is CRITICAL for pivoted category tables
                for col_name in columns.keys():
                    if category_lower in col_name.lower():
                        score += 60  # VERY strong boost - exact column name match
                        match_reasons.append(f"category_as_column_name:{col_name}")
                        break

                # Check ALL dimension columns, not just the first one
                category_value_found = False
                category_col_found = False
                for col_name, col_info in columns.items():
                    if col_info.get('role') == 'dimension':
                        unique_values = col_info.get('unique_values', [])
                        # Check if category value exists in column
                        if not category_value_found and any(category_lower in str(v).lower() for v in unique_values):
                            score += 15
                            match_reasons.append(f"category_match:{col_name}")
                            category_value_found = True
                        # Check if column name suggests categories (only if value not found)
                        elif not category_value_found and not category_col_found and 'category' in col_name.lower():
                            score += 10
                            match_reasons.append(f"has_category_col:{col_name}")
                            category_col_found = True

            # --- Location matching ---
            if entities.get('location'):
                columns = profile.get('columns', {})
                location_lower = entities['location'].lower()
                location_found = False
                for col_name, col_info in columns.items():
                    if col_info.get('role') in ['dimension', 'identifier']:
                        unique_values = col_info.get('unique_values', [])
                        if any(location_lower in str(v).lower() for v in unique_values):
                            score += 15
                            match_reasons.append(f"location_match:{col_name}")
                            location_found = True
                            break  # Location match found, can stop

            # --- Table type scoring ---
            table_type = profile.get('table_type', 'unknown')

            if table_type == 'transactional':
                score += 10
                match_reasons.append("type:transactional")
            elif table_type == 'summary':
                # Penalize summary tables unless query is broad/overview or explicitly asked
                if entities.get('aggregation') not in ['SUM', 'AVG', 'MAX', 'MIN'] and not _is_broad:
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

            # --- Trend query boost ---
            # Trend queries (increasing/decreasing/pattern) NEED temporal data (date columns).
            # Strongly prefer daily/transactional tables over summary/metadata tables.
            if entities.get('trend_intent') and granularity == 'daily':
                score += 50
                match_reasons.append("trend:temporal_data_boost")

            # --- Quality bonus ---
            quality = profile.get('data_quality_score', 0)
            quality_bonus = int(quality * 10)
            if quality_bonus > 0:
                score += quality_bonus
                match_reasons.append(f"quality:{quality_bonus}")

            # --- Dimension keyword matching (DYNAMIC - works with any dataset) ---
            # When question mentions keywords like "area", "pincode", "zone", etc.,
            # boost tables that have columns containing those keywords
            # This is CRITICAL for routing - user wants to GROUP BY or FILTER BY this dimension
            # Note: dimension_keywords already defined above for cross_table_intent logic
            if dimension_keywords:
                columns = profile.get('columns', {})
                scored_columns = set()  # Track columns already scored to prevent duplicates
                scored_table_keywords = set()  # Track table name keywords already scored
                for keyword in dimension_keywords:
                    keyword_lower = keyword.lower()
                    for col_name, col_info in columns.items():
                        col_lower = col_name.lower()
                        # Check if column name contains the dimension keyword
                        # Only score if this column hasn't been scored yet
                        if keyword_lower in col_lower and col_name not in scored_columns:
                            # VERY strong boost - user explicitly asked about this dimension
                            # Must beat cross_table aggregate boosts (40+25=65)
                            score += 70
                            match_reasons.append(f"dimension_col_match:{col_name}:{keyword}")
                            scored_columns.add(col_name)  # Mark column as scored
                            break  # Only count once per keyword
                    # Also check table name (only once per keyword)
                    if keyword_lower in table_name.lower() and keyword_lower not in scored_table_keywords:
                        score += 30
                        match_reasons.append(f"dimension_table_match:{keyword}")
                        scored_table_keywords.add(keyword_lower)

                # --- Fix 4: Strengthen location column matching ---
                # When user explicitly mentions "area" and table has "Area Name" column, VERY strong boost
                location_dims = ['area', 'zone', 'region', 'pincode', 'zip', 'city', 'location', 'branch']
                asking_about_location = any(kw.lower() in location_dims for kw in dimension_keywords)

                if asking_about_location:
                    for keyword in dimension_keywords:
                        keyword_lower = keyword.lower()
                        if keyword_lower in location_dims:
                            for col_name in columns.keys():
                                if keyword_lower in col_name.lower():
                                    score += 100  # VERY strong - exact dimension match
                                    match_reasons.append(f"exact_location_column_match:{col_name}")
                                    break

                    # --- Fix 3: Penalize wrong dimension type ---
                    # User wants location data - penalize category tables HEAVILY
                    table_lower = table_name.lower()
                    if 'category' in table_lower or profile.get('table_type') == 'category_breakdown':
                        score -= 80  # Heavy penalty - location query should NOT go to category table
                        match_reasons.append("PENALTY:location_query_on_category_table")

            # --- CRITICAL: "Who is..." / "Which person..." queries ---
            # These questions ask about SPECIFIC INDIVIDUALS, not aggregates
            # BOOST tables with individual row data (First_Name, Last_Name, Emp_ID)
            # PENALIZE summary tables that only have department/category aggregates
            individual_query_patterns = [
                'who is', 'who are', 'who has', 'who was',
                'which employee', 'which person', 'which staff',
                'name of the', 'names of the',
                'highest paid employee', 'lowest paid employee',
                'highest-paid employee', 'lowest-paid employee',
                'most experienced', 'least experienced',
                'oldest employee', 'newest employee', 'youngest employee'
            ]
            is_individual_query = any(pattern in raw_question for pattern in individual_query_patterns)

            if is_individual_query:
                columns = profile.get('columns', {})
                table_type = profile.get('table_type', 'unknown')

                # Check if table has individual person identifier columns
                person_cols = ['first_name', 'last_name', 'emp_id', 'employee_id',
                               'name', 'full_name', 'employee_name', 'staff_name']
                has_person_data = False
                for col_name in columns.keys():
                    if any(pc in col_name.lower() for pc in person_cols):
                        has_person_data = True
                        break

                if has_person_data:
                    # VERY strong boost - this table has individual person data
                    score += 150
                    match_reasons.append("BOOST:individual_person_data")
                else:
                    # HEAVY penalty - table doesn't have individual person data
                    score -= 100
                    match_reasons.append("PENALTY:no_individual_person_data")

                # Additional penalty for summary tables on individual queries
                if table_type == 'summary':
                    score -= 80
                    match_reasons.append("PENALTY:summary_table_for_individual_query")

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
                    return f"Hmm, '{table_name}' table கிடைக்கல! Available tables: {available}{more}"
                return f"Hmm, I can't find a table called '{table_name}'! Here's what I have: {available}{more}"
            return self._format_brief_summary(profile, language)
        else:
            return self._format_all_tables_summary(language)

    def _format_brief_summary(self, profile: dict, language: str = 'en') -> str:
        """
        Conversational brief summary of a single table in Thara's personality.
        Template-based — NO LLM. Warm, natural, no markdown formatting.
        """
        import random

        name = profile.get('table_name', 'Unknown')
        rows = profile.get('row_count', 0)
        table_type = profile.get('table_type', 'data')

        # Clean display name
        parts = name.split('_')
        clean_name = name
        for i, part in enumerate(parts):
            if part.lower() not in ('dataset', 'data') and not part.isdigit() and len(part) > 1:
                clean_name = '_'.join(parts[i:]).replace('_', ' ')
                break

        # Get key columns by role
        cols = profile.get('columns', {})
        metrics = [c.replace('_', ' ') for c, info in cols.items() if info.get('role') == 'metric'][:3]
        dimensions = [c.replace('_', ' ') for c, info in cols.items() if info.get('role') == 'dimension'][:3]

        if language == 'ta':
            openers = [
                f"Adhu unga {clean_name} table!",
                f"Okay, {clean_name} table paakuren!",
                f"Seri, {clean_name} pathi solluren!",
            ]
            response = random.choice(openers)
            response += f" Idhu oru {table_type} table, {rows:,} rows irukku."

            if metrics:
                response += f" Idhu la {', '.join(metrics)} maathiri metrics track pannuthu"
            if dimensions:
                response += f" - {', '.join(dimensions)} vachi break down panalam."
            else:
                response += "."

            response += " Enna therinjikka want? Numbers ah pull pannalama?"
        else:
            openers = [
                f"That's your {clean_name} table!",
                f"Alright, here's {clean_name}!",
                f"Okay, let me tell you about {clean_name}!",
            ]
            response = random.choice(openers)
            response += f" It's a {table_type} table with {rows:,} rows."

            if metrics:
                response += f" It tracks {', '.join(metrics)}"
            if dimensions:
                if metrics:
                    response += f", broken down by {', '.join(dimensions)}."
                else:
                    response += f" It's organized by {', '.join(dimensions)}."
            elif metrics:
                response += "."

            response += " I can run numbers on any of these."

        return response

    def _format_all_tables_summary(self, language: str = 'en') -> str:
        """
        Conversational summary of all tables in Thara's personality.
        Template-based — NO LLM. Warm, natural, no markdown formatting.
        """
        import random

        profiles = self.get_all_profiles()
        if not profiles:
            if language == 'ta':
                return "Innum data load aagala! Mudhalil oru dataset connect pannunga."
            return "No data loaded yet! Connect a dataset first and I'll take a look."

        total = len(profiles)

        # Categorize tables by type
        transactional = []
        summary_tables = []
        others = []
        for name, p in profiles.items():
            # Clean up display name: remove "Dataset_1_Sales_" prefix etc.
            parts = name.split('_')
            # Skip dataset/number prefix parts, keep meaningful name
            clean = name
            for i, part in enumerate(parts):
                if part.lower() not in ('dataset', 'data') and not part.isdigit() and len(part) > 1:
                    clean = '_'.join(parts[i:]).replace('_', ' ')
                    break

            row_count = p.get('row_count', 0)
            ttype = p.get('table_type', 'data')

            entry = (clean, row_count, ttype)
            if ttype == 'transactional':
                transactional.append(entry)
            elif ttype == 'summary':
                summary_tables.append(entry)
            else:
                others.append(entry)

        # Find biggest table
        all_entries = transactional + summary_tables + others
        biggest = max(all_entries, key=lambda x: x[1])

        # Build natural description
        if language == 'ta':
            openers = [
                f"Unga data la totally {total} tables irukku!",
                f"Seri, {total} tables irukku unga kitta!",
                f"Okay, unga dataset la {total} tables paakuren!",
            ]
        else:
            openers = [
                f"You've got {total} tables in your dataset!",
                f"Alright, there are {total} tables to work with!",
                f"Nice, I can see {total} tables in your data!",
            ]

        parts = [random.choice(openers)]

        # Describe the biggest table
        if language == 'ta':
            parts.append(f" Periya table {biggest[0]} — {biggest[1]:,} rows irukku.")
        else:
            parts.append(f" The biggest one is {biggest[0]} with {biggest[1]:,} rows.")

        # Mention categories naturally
        if transactional and summary_tables:
            t_names = [e[0] for e in transactional[:2]]
            s_names = [e[0] for e in summary_tables[:3]]
            if language == 'ta':
                parts.append(
                    f" {len(transactional)} detailed transaction tables irukku"
                    f" ({', '.join(t_names)}) plus {len(summary_tables)} summary tables"
                    f" like {', '.join(s_names)}."
                )
            else:
                parts.append(
                    f" You have {len(transactional)} detailed transaction table{'s' if len(transactional) > 1 else ''}"
                    f" ({', '.join(t_names)}) and {len(summary_tables)} summary tables"
                    f" like {', '.join(s_names)}."
                )
        elif summary_tables:
            s_names = [e[0] for e in summary_tables[:4]]
            if language == 'ta':
                parts.append(f" Summary tables: {', '.join(s_names)}.")
            else:
                parts.append(f" These include {', '.join(s_names)}.")

        # Closing
        if language == 'ta':
            parts.append(" Ellaa tables um ready, boss.")
        else:
            parts.append(" All tables are ready to query.")

        return ''.join(parts)

    def _find_profile_by_reference(self, table_ref: str) -> Optional[dict]:
        """
        Find profile by flexible reference (sheet 1, sales table, etc.).
        Supports:
        - Direct name match
        - Sheet number reference (sheet 1 -> first table)
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

        # 2. Sheet number reference (sheet 1 -> first table)
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
        Detailed profile with all columns — conversational Thara style.
        Template-based — NO LLM.
        """
        import random

        profile = self._find_profile_by_reference(table_name)
        if not profile:
            available = ", ".join(self.get_table_names()[:5])
            if language == 'ta':
                return f"Hmm, '{table_name}' table kanomae! Irukkura tables: {available}"
            return f"Hmm, can't find '{table_name}'! Here's what I have: {available}"

        name = profile.get('table_name', 'Unknown')
        rows = profile.get('row_count', 0)
        table_type = profile.get('table_type', 'data')
        columns = profile.get('columns', {})

        # Clean display name
        parts_list = name.split('_')
        clean_name = name
        for i, part in enumerate(parts_list):
            if part.lower() not in ('dataset', 'data') and not part.isdigit() and len(part) > 1:
                clean_name = '_'.join(parts_list[i:]).replace('_', ' ')
                break

        # Group columns by role
        metrics = [c.replace('_', ' ') for c, info in columns.items() if info.get('role') == 'metric']
        dates = [c.replace('_', ' ') for c, info in columns.items() if info.get('role') == 'date']
        dimensions = [c.replace('_', ' ') for c, info in columns.items() if info.get('role') == 'dimension']
        identifiers = [c.replace('_', ' ') for c, info in columns.items() if info.get('role') == 'identifier']

        if language == 'ta':
            openers = [
                f"Seri, {clean_name} table full ah paakuren!",
                f"Okay, {clean_name} details idho!",
            ]
            response = random.choice(openers)
            response += f" Idhu oru {table_type} table, {rows:,} rows, totally {len(columns)} columns irukku."

            if metrics:
                response += f" Metrics: {', '.join(metrics)}."
            if dates:
                response += f" Date columns: {', '.join(dates)}."
            if dimensions:
                response += f" Dimensions: {', '.join(dimensions)}."
            if identifiers:
                response += f" Identifiers: {', '.join(identifiers)}."

            response += " Enna query try pannalama?"
        else:
            openers = [
                f"Here's the full breakdown of {clean_name}!",
                f"Alright, diving deep into {clean_name}!",
            ]
            response = random.choice(openers)
            response += f" It's a {table_type} table with {rows:,} rows and {len(columns)} columns."

            if metrics:
                response += f" Metrics: {', '.join(metrics)}."
            if dates:
                response += f" Date columns: {', '.join(dates)}."
            if dimensions:
                response += f" Dimensions: {', '.join(dimensions)}."
            if identifiers:
                response += f" Identifiers: {', '.join(identifiers)}."

            response += " Everything's ready to query."

        return response

    def format_quality_report(self, language: str = 'en') -> str:
        """
        Generate a conversational data quality summary in Thara's personality.
        Warm, natural, informative — not a dry report.
        Template-based — NO LLM.
        """
        import random

        profiles = self.get_all_profiles()
        if not profiles:
            if language == 'ta':
                return "Innum data load aagala! Mudhalil oru dataset connect pannunga, naan paakuren."
            return "No data loaded yet! Connect a dataset first and I'll take a look."

        total_tables = len(profiles)
        total_rows = sum(p.get('row_count', 0) for p in profiles.values())

        # Quality scores
        quality_scores = [p.get('data_quality_score', 0) for p in profiles.values()]
        avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0

        # Date coverage
        date_ranges = []
        for p in profiles.values():
            dr = p.get('date_range', {})
            if dr.get('min') and dr.get('max'):
                date_ranges.append((dr['min'][:10], dr['max'][:10]))

        date_info = ""
        if date_ranges:
            min_date = min(d[0] for d in date_ranges)
            max_date = max(d[1] for d in date_ranges)
            date_info = f" covering {min_date} to {max_date}"

        # Biggest table
        biggest = max(profiles.items(), key=lambda x: x[1].get('row_count', 0))
        biggest_name = biggest[0].split('_')[-1] if '_' in biggest[0] else biggest[0]
        biggest_rows = biggest[1].get('row_count', 0)

        # Build natural response
        if avg_quality >= 0.85:
            if language == 'ta':
                openers = [
                    f"Unga data super clean ah irukku!",
                    f"Data quality excellent ah irukku!",
                    f"Romba nalla data - quality wise top notch!",
                ]
            else:
                openers = [
                    f"Your data looks really solid!",
                    f"Great news - your data quality is excellent!",
                    f"Looking good! Your data is in great shape.",
                ]
        elif avg_quality >= 0.7:
            if language == 'ta':
                openers = [
                    f"Unga data nalla irukku!",
                    f"Data quality good ah irukku, no worries!",
                ]
            else:
                openers = [
                    f"Your data is looking good!",
                    f"Nice - your data quality is solid.",
                ]
        elif avg_quality >= 0.5:
            if language == 'ta':
                openers = [
                    f"Data okay ah irukku, but some gaps irukku.",
                    f"Data usable ah irukku, but perfect illa.",
                ]
            else:
                openers = [
                    f"Your data is usable, but there are some gaps.",
                    f"It's decent, though a few tables could use some cleanup.",
                ]
        else:
            if language == 'ta':
                openers = [
                    f"Data quality konjam low ah irukku - missing values irukkalam.",
                ]
            else:
                openers = [
                    f"Heads up - the data quality is on the lower side. There might be missing values.",
                ]

        opener = random.choice(openers)

        if language == 'ta':
            details = (
                f" {total_tables} tables irukku with {total_rows:,} total rows{date_info}."
                f" Quality score {avg_quality:.0%}."
                f" Biggest table {biggest_name} - {biggest_rows:,} rows."
                f" Enna explore pannalam? Sales, trends, comparisons - kelu!"
            )
        else:
            details = (
                f" You've got {total_tables} tables with {total_rows:,} total rows{date_info}."
                f" Overall quality score is {avg_quality:.0%}."
                f" Your biggest table is {biggest_name} with {biggest_rows:,} rows."
                f" Everything's ready to query."
            )

        return opener + details

    def format_structure_description(self, language: str = 'en') -> str:
        """
        Describes the structure/schema of all tables — columns, types, relationships.
        For questions like "describe the structure", "what columns do I have".
        """
        import random

        profiles = self.get_all_profiles()
        if not profiles:
            return "No data loaded yet! Connect a dataset first."

        # Collect structure info per table
        table_infos = []
        all_metrics = set()
        all_dimensions = set()
        total_cols = 0

        for name, p in profiles.items():
            # Clean name
            parts = name.split('_')
            clean = name
            for i, part in enumerate(parts):
                if part.lower() not in ('dataset', 'data') and not part.isdigit() and len(part) > 1:
                    clean = '_'.join(parts[i:]).replace('_', ' ')
                    break

            cols = p.get('columns', {})
            total_cols += len(cols)
            m = [c.replace('_', ' ') for c, info in cols.items() if info.get('role') == 'metric']
            d = [c.replace('_', ' ') for c, info in cols.items() if info.get('role') == 'dimension']
            all_metrics.update(m)
            all_dimensions.update(d)
            table_infos.append((clean, len(cols), m[:2], d[:2], p.get('row_count', 0)))

        # Sort by column count descending — most complex first
        table_infos.sort(key=lambda x: x[1], reverse=True)

        if language == 'ta':
            openers = [
                "Seri, unga tables structure paakalam!",
                "Okay, unga data structure explain pannuren!",
            ]
        else:
            openers = [
                "Let me walk you through the structure!",
                "Here's how your data is organized!",
                "Okay, let me break down the structure for you!",
            ]

        parts_list = [random.choice(openers)]

        # Overall stats
        parts_list.append(
            f" Across {len(profiles)} tables, there are {total_cols} total columns"
            f" — {len(all_metrics)} unique metrics and {len(all_dimensions)} dimensions."
        )

        # Top 3 tables with their key columns
        for clean, ncols, metrics, dims, rows in table_infos[:3]:
            col_desc = ""
            if metrics and dims:
                col_desc = f" tracks {', '.join(metrics)} by {', '.join(dims)}"
            elif metrics:
                col_desc = f" tracks {', '.join(metrics)}"
            elif dims:
                col_desc = f" organized by {', '.join(dims)}"
            parts_list.append(f" {clean} ({ncols} cols, {rows:,} rows){col_desc}.")

        if len(table_infos) > 3:
            remaining = len(table_infos) - 3
            parts_list.append(f" Plus {remaining} more tables.")

        parts_list.append(" Ask about any specific table for full column details!")

        return ''.join(parts_list)

    def format_data_highlights(self, language: str = 'en') -> str:
        """
        Highlights interesting/notable patterns in the data.
        For questions like "anything interesting?", "anything unusual?".
        """
        import random

        profiles = self.get_all_profiles()
        if not profiles:
            return "No data loaded yet! Connect a dataset first."

        highlights = []

        # Find size extremes
        sorted_by_rows = sorted(profiles.items(), key=lambda x: x[1].get('row_count', 0), reverse=True)
        biggest = sorted_by_rows[0]
        smallest = sorted_by_rows[-1]

        big_name = self._clean_table_name(biggest[0])
        small_name = self._clean_table_name(smallest[0])
        big_rows = biggest[1].get('row_count', 0)
        small_rows = smallest[1].get('row_count', 0)

        if big_rows > small_rows * 10:
            highlights.append(
                f"{big_name} is massive with {big_rows:,} rows while {small_name} has only {small_rows:,}"
                f" — that's a {big_rows // max(small_rows, 1)}x difference!"
            )

        # Date coverage
        date_ranges = []
        for name, p in profiles.items():
            dr = p.get('date_range', {})
            if dr.get('min') and dr.get('max'):
                date_ranges.append((self._clean_table_name(name), dr['min'][:10], dr['max'][:10]))

        if date_ranges:
            min_date = min(d[1] for d in date_ranges)
            max_date = max(d[2] for d in date_ranges)
            highlights.append(f"Your data spans from {min_date} to {max_date}.")

        # Quality variation
        quality_scores = [(self._clean_table_name(n), p.get('data_quality_score', 0))
                         for n, p in profiles.items() if p.get('data_quality_score')]
        if quality_scores:
            best_q = max(quality_scores, key=lambda x: x[1])
            worst_q = min(quality_scores, key=lambda x: x[1])
            if best_q[1] - worst_q[1] > 0.15:
                highlights.append(
                    f"Quality varies — {best_q[0]} scores {best_q[1]:.0%} "
                    f"while {worst_q[0]} is at {worst_q[1]:.0%}."
                )

        # Tables with many metrics (feature-rich)
        metric_rich = []
        for name, p in profiles.items():
            cols = p.get('columns', {})
            m_count = sum(1 for info in cols.values() if info.get('role') == 'metric')
            if m_count >= 4:
                metric_rich.append((self._clean_table_name(name), m_count))
        if metric_rich:
            metric_rich.sort(key=lambda x: x[1], reverse=True)
            top = metric_rich[0]
            highlights.append(f"{top[0]} is the richest table with {top[1]} trackable metrics.")

        # Table type distribution
        types = {}
        for p in profiles.values():
            t = p.get('table_type', 'data')
            types[t] = types.get(t, 0) + 1
        if len(types) > 1:
            type_desc = ', '.join(f"{count} {t}" for t, count in types.items())
            highlights.append(f"Mix of table types: {type_desc}.")

        if language == 'ta':
            openers = [
                "Interesting ah irukku unga data!",
                "Sila notable things paathein!",
                "Unga data la konjam observations sollurenl!",
            ]
        else:
            openers = [
                "Here's what stands out in your data!",
                "A few interesting things I noticed!",
                "Let me share what caught my eye!",
            ]

        response = random.choice(openers)
        if highlights:
            response += " " + " ".join(highlights)
        else:
            response += f" You have {len(profiles)} clean tables ready to explore. No obvious red flags!"

        response += " I can dig into any of these tables."
        return response

    def format_analysis_capabilities(self, language: str = 'en') -> str:
        """
        Describes what kind of analysis is possible based on the data.
        For questions like "what kind of analysis can I do?", "what insights can I get?".
        """
        import random

        profiles = self.get_all_profiles()
        if not profiles:
            return "No data loaded yet! Connect a dataset first."

        # Discover available analysis types from actual data
        capabilities = []
        has_dates = False
        has_metrics = False
        has_dimensions = False
        has_multiple_tables = len(profiles) > 1
        metric_names = set()
        dimension_names = set()

        for p in profiles.values():
            cols = p.get('columns', {})
            for col_name, info in cols.items():
                role = info.get('role', '')
                clean = col_name.replace('_', ' ')
                if role == 'date':
                    has_dates = True
                elif role == 'metric':
                    has_metrics = True
                    metric_names.add(clean)
                elif role == 'dimension':
                    has_dimensions = True
                    dimension_names.add(clean)

        if has_metrics:
            sample_metrics = list(metric_names)[:3]
            capabilities.append(f"totals, averages, and comparisons for {', '.join(sample_metrics)}")

        if has_dates and has_metrics:
            capabilities.append("trends over time — monthly, weekly, daily patterns")

        if has_dimensions and has_metrics:
            sample_dims = list(dimension_names)[:3]
            capabilities.append(f"breakdowns by {', '.join(sample_dims)}")

        if has_multiple_tables:
            capabilities.append("cross-table analysis linking related data")

        if has_dimensions:
            capabilities.append("top/bottom rankings and filtering")

        if language == 'ta':
            openers = [
                "Unga data vachi romba vishayam panna mudiyum!",
                "Niraiya analysis options irukku!",
            ]
        else:
            openers = [
                "There's a lot you can do with this data!",
                "You've got plenty of analysis options!",
                "Great question — here's what's possible!",
            ]

        response = random.choice(openers)
        if capabilities:
            response += " You can look at " + "; ".join(capabilities) + "."
        response += " Just ask a question naturally and I'll figure out the rest!"

        return response

    def _clean_table_name(self, name: str) -> str:
        """Strip Dataset_1_Sales_ prefixes from table names for display."""
        parts = name.split('_')
        for i, part in enumerate(parts):
            if part.lower() not in ('dataset', 'data') and not part.isdigit() and len(part) > 1:
                return '_'.join(parts[i:]).replace('_', ' ')
        return name.replace('_', ' ')

