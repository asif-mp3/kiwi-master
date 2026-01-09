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
        # Get significant words (>= 4 chars, exclude common words)
        stop_words = {'what', 'where', 'when', 'which', 'how', 'tell', 'show', 'give', 'find',
                     'the', 'and', 'for', 'from', 'with', 'about', 'this', 'that', 'have', 'does'}

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
            table_name_lower = table_name.lower()
            for keyword in query_keywords:
                if keyword in table_name_lower:
                    score += 50  # Strong boost for keyword match
                    match_reasons.append(f"table_name_keyword_match:{keyword}")
                    break  # One keyword match is enough

            # --- DIMENSION COLUMN NAME MATCHING ---
            # Strong boost when query keywords match dimension column names
            # e.g., "payment modes" query should match "Payment_Mode" column
            columns = profile.get('columns', {})
            for keyword in query_keywords:
                keyword_lower = keyword.lower()
                # Skip common non-specific words
                if keyword_lower in {'used', 'data', 'this', 'that', 'show', 'list', 'types'}:
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
                        # Single keyword match on short column name
                        score += 40
                        match_reasons.append(f"metric_keyword_match:{col_name}")

            # --- TRANSACTIONAL TABLE PREFERENCE ---
            # When query asks for "across all transactions", prefer transactional tables
            # with actual amounts over summary tables with counts
            table_type = profile.get('table_type', 'unknown')
            if 'transaction' in raw_question or 'across all' in raw_question:
                if table_type == 'transactional':
                    # Check if table has actual amount/value columns (not just counts)
                    has_amount_col = any(
                        'amount' in col.lower() or 'value' in col.lower() or 'revenue' in col.lower()
                        for col, info in columns.items() if info.get('role') == 'metric'
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
                        match_reasons.append(f"granularity_match:{keyword}→{granularity}")
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
                skip_words = {'the', 'and', 'for', 'what', 'which', 'how', 'does', 'belong', 'state', 'department'}
                if keyword_lower in skip_words:
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

            # --- Synonym map keyword match ---
            # If query mentions "employee", "department", "designation" etc.
            # and table has these in synonym_map, boost the table
            hr_keywords = ['employee', 'staff', 'department', 'designation', 'salary', 'payroll']
            for keyword in query_keywords:
                keyword_lower = keyword.lower()
                if keyword_lower in hr_keywords and keyword_lower in synonym_map:
                    score += 60  # Strong boost for synonym match
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

                                    # Extra boost for transactional tables (Daily, Transaction, Sales)
                                    # These are IDEAL for month comparisons as they have row-level date data
                                    transactional_keywords = ['daily', 'transaction', 'sales', 'order']
                                    if any(kw in table_lower for kw in transactional_keywords):
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
