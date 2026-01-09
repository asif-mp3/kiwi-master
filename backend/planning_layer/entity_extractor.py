"""
Entity Extractor - Extracts entities (month, metric, category, location) from questions.
Uses regex and keyword matching for speed - no LLM needed.

DYNAMIC LEARNING:
Locations and categories are learned from table profiles when available.
Falls back to basic defaults only when no profiles are loaded.
"""

import re
from typing import Dict, Optional, List, Any, Set
from datetime import datetime, timedelta


class EntityExtractor:
    """
    Extracts entities from natural language questions.
    Fast, deterministic extraction using patterns and keywords.

    IMPORTANT: Call refresh_from_profiles() after loading data to learn
    locations, categories, and other entities from the actual data.
    """

    # Month names with variations (English + Tamil)
    MONTHS = {
        # English
        'january': '01', 'jan': '01',
        'february': '02', 'feb': '02',
        'march': '03', 'mar': '03',
        'april': '04', 'apr': '04',
        'may': '05',
        'june': '06', 'jun': '06',
        'july': '07', 'jul': '07',
        'august': '08', 'aug': '08',
        'september': '09', 'sep': '09', 'sept': '09',
        'october': '10', 'oct': '10',
        'november': '11', 'nov': '11',
        'december': '12', 'dec': '12',
        # Tamil month names
        'ஜனவரி': '01',
        'பிப்ரவரி': '02',
        'மார்ச்': '03',
        'ஏப்ரல்': '04',
        'மே': '05',
        'ஜூன்': '06',
        'ஜூலை': '07',
        'ஆகஸ்ட்': '08',
        'செப்டம்பர்': '09',
        'அக்டோபர்': '10',
        'நவம்பர்': '11',
        'டிசம்பர்': '12',
    }

    # Metric terms (order matters - longer matches first)
    METRICS = [
        'gross sales', 'net sales', 'total sales',
        'gross profit', 'net profit',
        'order count', 'average order value',
        'sales', 'revenue', 'profit', 'margin',
        'orders', 'transactions',
        'quantity', 'units', 'items sold', 'items',
        'aov', 'shipping', 'tax', 'gst', 'subtotal',
        'discount', 'cost', 'expense'
    ]

    # Minimal fallback locations (only used if no profiles loaded)
    _DEFAULT_LOCATIONS: Set[str] = {
        'chennai', 'bangalore', 'mumbai', 'delhi', 'hyderabad',
        # Common Chennai areas (Freshggies delivery zones)
        'velachery', 'adyar', 'koyambedu', 'anna nagar', 'chromepet',
        'tambaram', 'porur', 't nagar', 'mylapore', 'besant nagar',
        'thiruvanmiyur', 'guindy', 'nanganallur', 'madipakkam',
        # Indian states (for state-level filtering)
        'tamil nadu', 'karnataka', 'kerala', 'andhra pradesh', 'telangana',
        'maharashtra', 'gujarat', 'rajasthan', 'punjab', 'haryana',
        'uttar pradesh', 'madhya pradesh', 'west bengal', 'odisha', 'bihar'
    }

    # Fallback categories (used if not learned from profiles)
    # Includes common Freshggies product categories
    _DEFAULT_CATEGORIES: Set[str] = {
        'sales', 'orders', 'products', 'customers',
        # Freshggies categories
        'fresh cut vegetables', 'fresh cut fruits', 'leafy greens',
        'exotic vegetables', 'salad mixes', 'ready to cook',
        'dairy', 'beverages', 'groceries', 'snacks', 'frozen',
        'fruits', 'vegetables', 'organic', 'premium',
        # Additional common categories
        'fresh produce', 'dairy & homemade', 'snacks & sweets',
        'bakery', 'meat', 'seafood', 'pantry', 'household',
        # Freshggies specific categories from user data (EXACT column names)
        'dairy & homemade essentials', 'batter & dough',
        'ready to cook & eat', 'fresh fruits', 'fresh vegetables',
        'juices & beverages', 'homemade powders, pastes & pickles',
        'pickles & preserves', 'salads & dressings', 'combo / value pack',
        'fresh cut vegetables / prepped veggies'
    }

    # Aggregation keywords
    AGGREGATION_TERMS = {
        'SUM': ['total', 'sum', 'overall', 'combined', 'aggregate', 'all'],
        'AVG': ['average', 'avg', 'mean', 'typical'],
        'MAX': ['maximum', 'max', 'highest', 'best', 'top', 'peak'],
        'MIN': ['minimum', 'min', 'lowest', 'worst', 'bottom'],
        'COUNT': ['count', 'how many', 'number of', 'total number']
    }

    # Dimension keywords - when these appear in question, boost tables with matching columns
    DIMENSION_KEYWORDS = [
        'area', 'zone', 'region', 'pincode', 'zip', 'shipping',
        'city', 'state', 'district', 'branch', 'location',
        'category', 'type', 'product', 'item', 'customer', 'segment'
    ]

    def __init__(self):
        """Initialize with empty learned entities (populated by refresh_from_profiles)"""
        self._learned_locations: Set[str] = set()
        self._learned_categories: Set[str] = set()
        self._learned_products: Set[str] = set()
        self._learned_custom_entities: Dict[str, Set[str]] = {}
        self._profiles_loaded = False

    def refresh_from_profiles(self, profile_store=None):
        """
        Learn entities from table profiles.

        This extracts:
        - Locations: From columns that look like location/city/region
        - Categories: From columns that look like category/type/group
        - Products: From columns that look like product/item/name
        - Custom: Any other dimension with unique values

        Call this after loading/refreshing data.
        """
        if profile_store is None:
            # Try to import and create profile store
            try:
                from schema_intelligence.profile_store import ProfileStore
                profile_store = ProfileStore()
            except Exception as e:
                print(f"  Warning: Could not load ProfileStore for entity learning: {e}")
                return

        profiles = profile_store.get_all_profiles()
        if not profiles:
            print("  No profiles available for entity learning")
            return

        # Clear previous learned entities
        self._learned_locations = set()
        self._learned_categories = set()
        self._learned_products = set()
        self._learned_custom_entities = {}

        # Patterns to identify column types
        location_patterns = ['city', 'location', 'region', 'area', 'state', 'district', 'zone', 'branch']
        category_patterns = ['category', 'type', 'group', 'class', 'segment', 'department']
        product_patterns = ['product', 'item', 'name', 'sku', 'description']

        for table_name, profile in profiles.items():
            columns = profile.get('columns', {})

            for col_name, col_info in columns.items():
                role = col_info.get('role', '')
                unique_values = col_info.get('unique_values', [])

                # Skip if no unique values or too many (not useful for matching)
                if not unique_values or len(unique_values) > 500:
                    continue

                col_lower = col_name.lower()

                # Learn locations
                if any(pattern in col_lower for pattern in location_patterns):
                    for val in unique_values:
                        if val and isinstance(val, str) and len(val) > 1:
                            self._learned_locations.add(val.lower().strip())

                # Learn categories
                elif any(pattern in col_lower for pattern in category_patterns):
                    for val in unique_values:
                        if val and isinstance(val, str) and len(val) > 1:
                            self._learned_categories.add(val.lower().strip())

                # Learn products
                elif any(pattern in col_lower for pattern in product_patterns):
                    for val in unique_values:
                        if val and isinstance(val, str) and len(val) > 1:
                            self._learned_products.add(val.lower().strip())

                # Learn from any dimension column
                elif role == 'dimension':
                    entity_key = col_name.lower().replace(' ', '_')
                    if entity_key not in self._learned_custom_entities:
                        self._learned_custom_entities[entity_key] = set()
                    for val in unique_values:
                        if val and isinstance(val, str) and len(val) > 1:
                            self._learned_custom_entities[entity_key].add(val.lower().strip())

        self._profiles_loaded = True
        print(f"  ✓ Learned entities from profiles:")
        print(f"    - {len(self._learned_locations)} locations")
        print(f"    - {len(self._learned_categories)} categories")
        print(f"    - {len(self._learned_products)} products")
        print(f"    - {len(self._learned_custom_entities)} custom dimensions")

    @property
    def LOCATIONS(self) -> Set[str]:
        """Get locations - learned from profiles or fallback defaults"""
        if self._profiles_loaded and self._learned_locations:
            return self._learned_locations
        return self._DEFAULT_LOCATIONS

    @property
    def CATEGORIES(self) -> Set[str]:
        """Get categories - learned from profiles or fallback defaults"""
        if self._profiles_loaded and self._learned_categories:
            return self._learned_categories
        return self._DEFAULT_CATEGORIES

    # Comparison keywords
    COMPARISON_TERMS = ['compare', 'versus', 'vs', 'compared to', 'difference',
                        'against', 'between', 'relative to']

    # Cross-table / aggregate keywords - indicates query needs data across all periods/tables
    CROSS_TABLE_TERMS = [
        'across all', 'all months', 'all time', 'overall', 'grand total',
        'entire', 'whole', 'complete', 'combined', 'aggregate',
        'year to date', 'ytd', 'month to date', 'mtd',
        'month over month', 'year over year', 'yoy', 'mom',
        'throughout', 'over time', 'across months', 'across periods',
        'total for', 'sum of all', 'everything', 'all data',
        # Time range patterns - "from X to Y" indicates cross-table trend
        'from august to', 'from september to', 'from october to', 'from november to',
        'from december to', 'from january to', 'from february to', 'from march to',
        'august to december', 'september to december', 'october to december',
        'january to december', 'august to november', 'trend change',
        'trend from', 'trend over', 'trend across'
    ]

    def extract(self, question: str) -> Dict[str, Any]:
        """
        Extract all entities from a question.

        Returns dict with:
        - month: Detected month name (capitalized) or None
        - metric: Detected metric type or None
        - category: Product category or None
        - location: City/region or None
        - aggregation: SUM, AVG, MAX, MIN, COUNT or default SUM
        - comparison: Boolean - is this a comparison query?
        - time_period: Special time references like "top 5", "last week"
        - explicit_table: If user mentions specific table/sheet
        """
        q_lower = question.lower()

        return {
            'month': self._extract_month(q_lower),
            'all_months': self._extract_all_months(q_lower),
            'metric': self._extract_metric(q_lower),
            'category': self._extract_category(q_lower, question),
            'location': self._extract_location(q_lower),
            'aggregation': self._extract_aggregation(q_lower),
            'comparison': self._is_comparison(q_lower),
            'multi_month_comparison': self._is_multi_month_comparison(q_lower),
            'cross_table_intent': self._is_cross_table_query(q_lower),
            'dimension_keywords': self._extract_dimension_keywords(q_lower),
            'time_period': self._extract_time_period(q_lower),
            'explicit_table': self._extract_explicit_table(question),
            'date_specific': self._extract_specific_date(q_lower),
            'custom_entities': self._extract_custom_entities(q_lower),
            'raw_question': question
        }

    def _extract_month(self, text: str) -> Optional[str]:
        """Extract month name from text"""
        # Check for explicit month names
        for month_name, month_num in self.MONTHS.items():
            # Use word boundary to avoid partial matches
            pattern = r'\b' + month_name + r'\b'
            if re.search(pattern, text):
                # Return full capitalized month name
                full_names = {
                    '01': 'January', '02': 'February', '03': 'March',
                    '04': 'April', '05': 'May', '06': 'June',
                    '07': 'July', '08': 'August', '09': 'September',
                    '10': 'October', '11': 'November', '12': 'December'
                }
                return full_names[month_num]

        # Check for relative references
        if 'last month' in text:
            last_month = datetime.now().month - 1
            if last_month == 0:
                last_month = 12
            return self._month_num_to_name(last_month)

        if 'this month' in text:
            return self._month_num_to_name(datetime.now().month)

        return None

    def _month_num_to_name(self, month_num: int) -> Optional[str]:
        """Convert month number to name. Returns None for invalid month numbers."""
        names = ['January', 'February', 'March', 'April', 'May', 'June',
                 'July', 'August', 'September', 'October', 'November', 'December']
        return names[month_num - 1] if 1 <= month_num <= 12 else None

    def _extract_metric(self, text: str) -> Optional[str]:
        """Extract metric type from text"""
        # Check longer phrases first
        for metric in self.METRICS:
            if metric in text:
                return metric
        return None

    def _extract_category(self, text_lower: str, original: str) -> Optional[str]:
        """
        Extract product category from text.
        Checks quoted terms first, then known categories.
        """
        # Check for double-quoted terms
        double_quoted = re.findall(r'"([^"]+)"', original)
        if double_quoted:
            return double_quoted[0]

        # Check for single-quoted terms
        single_quoted = re.findall(r"'([^']+)'", original)
        if single_quoted:
            return single_quoted[0]

        # Check known categories
        for cat in self.CATEGORIES:
            pattern = r'\b' + re.escape(cat) + r'\b'
            if re.search(pattern, text_lower):
                return cat.title()

        return None

    def _extract_location(self, text: str) -> Optional[str]:
        """Extract location/city from text"""
        # First check learned locations
        for loc in self.LOCATIONS:
            pattern = r'\b' + re.escape(loc) + r'\b'
            if re.search(pattern, text):
                # Return properly capitalized
                return loc.title()

        # Also check custom entities that might be area/location related
        # This catches area names learned from "Area Name" type columns
        location_entity_types = ['area_name', 'area', 'location', 'city', 'zone', 'region']
        for entity_type in location_entity_types:
            if entity_type in self._learned_custom_entities:
                for val in self._learned_custom_entities[entity_type]:
                    pattern = r'\b' + re.escape(val) + r'\b'
                    if re.search(pattern, text):
                        return val.title()

        return None

    def _extract_aggregation(self, text: str) -> str:
        """Extract aggregation type from text"""
        for agg_type, keywords in self.AGGREGATION_TERMS.items():
            for keyword in keywords:
                if keyword in text:
                    return agg_type

        # Default to SUM for most queries
        return 'SUM'

    def _is_comparison(self, text: str) -> bool:
        """Check if question is asking for comparison"""
        return any(term in text for term in self.COMPARISON_TERMS)

    def _extract_all_months(self, text: str) -> List[str]:
        """Extract ALL month names mentioned in the text"""
        found_months = []
        for month_name, month_num in self.MONTHS.items():
            pattern = r'\b' + month_name + r'\b'
            if re.search(pattern, text):
                full_names = {
                    '01': 'January', '02': 'February', '03': 'March',
                    '04': 'April', '05': 'May', '06': 'June',
                    '07': 'July', '08': 'August', '09': 'September',
                    '10': 'October', '11': 'November', '12': 'December'
                }
                full_name = full_names[month_num]
                if full_name not in found_months:
                    found_months.append(full_name)
        return found_months

    def _is_multi_month_comparison(self, text: str) -> bool:
        """
        Check if question compares TWO OR MORE months.
        This helps route to tables with multi-month columns instead of month-specific tables.

        Examples:
        - "Compare September and October sales" → True
        - "September vs October" → True
        - "How did sales change from September to October?" → True
        - "What were September sales?" → False (only one month)
        """
        months_found = self._extract_all_months(text)
        if len(months_found) >= 2:
            # Multiple months mentioned - likely a comparison
            return True
        # Also check for comparison terms + month
        if len(months_found) == 1 and self._is_comparison(text):
            # Single month with comparison term might be "compare X to Y" pattern
            return True
        return False

    def _is_cross_table_query(self, text: str) -> bool:
        """
        Check if question needs data aggregated across all tables/periods.
        
        Examples:
        - "Which area has the highest total sales across all months?"
        - "What is the overall revenue?"
        - "Show grand total sales"
        """
        return any(term in text for term in self.CROSS_TABLE_TERMS)

    def _extract_dimension_keywords(self, text: str) -> List[str]:
        """
        Extract dimension-related keywords from the question.
        
        These are used to boost tables that have columns matching these keywords.
        For example, if the question asks about "area", tables with an "Area Name" 
        column should be boosted.
        """
        found_keywords = []
        for keyword in self.DIMENSION_KEYWORDS:
            # Use word boundary matching
            pattern = r'\b' + re.escape(keyword) + r'\b'
            if re.search(pattern, text):
                found_keywords.append(keyword)
        return found_keywords

    def _extract_time_period(self, text: str) -> Optional[str]:
        """Extract special time period references"""
        # Top N pattern
        top_match = re.search(r'top\s+(\d+)', text)
        if top_match:
            return f"top_{top_match.group(1)}"

        # Bottom N pattern
        bottom_match = re.search(r'bottom\s+(\d+)', text)
        if bottom_match:
            return f"bottom_{bottom_match.group(1)}"

        # Last N days/weeks/months
        last_match = re.search(r'last\s+(\d+)\s*(days?|weeks?|months?)', text)
        if last_match:
            return f"last_{last_match.group(1)}_{last_match.group(2)}"

        # First N pattern
        first_match = re.search(r'first\s+(\d+)', text)
        if first_match:
            return f"first_{first_match.group(1)}"

        # Today, yesterday, this week
        if 'today' in text:
            return 'today'
        if 'yesterday' in text:
            return 'yesterday'
        if 'this week' in text:
            return 'this_week'
        if 'last week' in text:
            return 'last_week'

        return None

    def _extract_explicit_table(self, question: str) -> Optional[str]:
        """
        Check if user explicitly mentions a table or sheet name.
        Patterns like "from X sheet" or "in X table" or "check X"
        """
        patterns = [
            r'from\s+["\']?([^"\']+?)["\']?\s+(?:sheet|table)',
            r'(?:sheet|table)\s+["\']?([^"\']+?)["\']?(?:\s|$|,|\?)',
            r'in\s+["\']?([^"\']+?)["\']?\s+(?:sheet|table)',
            r'check\s+(?:the\s+)?["\']?([^"\']+?)["\']?\s+(?:sheet|table)',
            r'look\s+(?:at|in)\s+["\']?([^"\']+?)["\']?\s+(?:sheet|table)'
        ]

        for pattern in patterns:
            match = re.search(pattern, question, re.IGNORECASE)
            if match:
                return match.group(1).strip()

        return None

    def _extract_specific_date(self, text: str) -> Optional[Dict]:
        """
        Extract specific date references like "November 15th" or "15/11/2025"
        """
        # Pattern: Month Day (e.g., "November 15th", "Nov 15")
        # Use word boundaries to avoid false matches like "margin" matching "mar"
        month_names_escaped = '|'.join(re.escape(m) for m in self.MONTHS.keys())
        month_day_pattern = r'\b(' + month_names_escaped + r')\s+(\d{1,2})(?:st|nd|rd|th)?\b'
        match = re.search(month_day_pattern, text, re.IGNORECASE)
        if match:
            month = match.group(1).lower()
            day = int(match.group(2))
            month_num = self.MONTHS.get(month[:3], self.MONTHS.get(month))
            if month_num:
                return {
                    'type': 'specific_day',
                    'month': int(month_num),
                    'day': day
                }

        # Pattern: DD/MM or DD/MM/YYYY
        date_pattern = r'(\d{1,2})[/\-](\d{1,2})(?:[/\-](\d{4}))?'
        match = re.search(date_pattern, text)
        if match:
            day = int(match.group(1))
            month = int(match.group(2))
            year = int(match.group(3)) if match.group(3) else datetime.now().year

            # Validate - assume DD/MM format (international)
            if 1 <= day <= 31 and 1 <= month <= 12:
                return {
                    'type': 'specific_date',
                    'day': day,
                    'month': month,
                    'year': year
                }

        return None

    def _extract_custom_entities(self, text: str) -> Dict[str, str]:
        """
        Extract custom entities learned from dimension columns.
        Returns dict mapping entity_type -> matched_value
        """
        found = {}
        for entity_type, values in self._learned_custom_entities.items():
            for val in values:
                pattern = r'\b' + re.escape(val) + r'\b'
                if re.search(pattern, text):
                    found[entity_type] = val.title()
                    break  # Only one match per entity type
        return found

    def is_followup_question(self, question: str, has_previous_context: bool = False) -> bool:
        """
        Detect if this is likely a follow-up question.
        Used by context manager to decide whether to merge with previous context.
        """
        if not has_previous_context:
            return False

        q_lower = question.lower()

        # Explicit follow-up phrases (English)
        english_followup_phrases = [
            'how about', 'what about', 'and for', 'also for',
            'same for', 'now for', 'compare to', 'versus',
            'and what', 'now show', 'also show', 'but for',
            'instead of', 'rather than', 'as opposed to',
            'same day', 'same date', 'that day', 'that date',
        ]

        if any(phrase in q_lower for phrase in english_followup_phrases):
            return True

        # Tamil follow-up phrases (check against original, not lowercase)
        tamil_followup_phrases = [
            'அதே நாள்', 'அதே தேதி', 'அந்த நாள்',  # same day, same date, that day
            'எப்படி', 'என்ன பற்றி',  # how about, what about
        ]

        if any(phrase in question for phrase in tamil_followup_phrases):
            return True

        # Very short questions are likely follow-ups
        word_count = len(question.split())
        if word_count <= 3:
            return True

        # Questions that are just a location or month
        if word_count <= 2:
            # Check if it's just a location name
            if self._extract_location(q_lower):
                return True
            # Check if it's just a month
            if self._extract_month(q_lower):
                return True

        return False

    def get_entities_summary(self, entities: Dict) -> str:
        """
        Create human-readable summary of extracted entities.
        Useful for debugging.
        """
        parts = []

        if entities.get('month'):
            parts.append(f"Month: {entities['month']}")
        if entities.get('metric'):
            parts.append(f"Metric: {entities['metric']}")
        if entities.get('category'):
            parts.append(f"Category: {entities['category']}")
        if entities.get('location'):
            parts.append(f"Location: {entities['location']}")
        if entities.get('aggregation') != 'SUM':
            parts.append(f"Aggregation: {entities['aggregation']}")
        if entities.get('comparison'):
            parts.append("Type: Comparison")
        if entities.get('cross_table_intent'):
            parts.append("Intent: Cross-table/Aggregate")
        if entities.get('dimension_keywords'):
            parts.append(f"Dimensions: {entities['dimension_keywords']}")
        if entities.get('time_period'):
            parts.append(f"Time period: {entities['time_period']}")
        if entities.get('explicit_table'):
            parts.append(f"Explicit table: {entities['explicit_table']}")

        return " | ".join(parts) if parts else "No entities extracted"
