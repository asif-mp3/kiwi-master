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

    # Tamil ordinal numbers (1-31 for date extraction)
    # Includes both cardinal and ordinal forms
    TAMIL_NUMBERS = {
        # Cardinal numbers
        'ஒன்று': 1, 'இரண்டு': 2, 'மூன்று': 3, 'நான்கு': 4, 'ஐந்து': 5,
        'ஆறு': 6, 'ஏழு': 7, 'எட்டு': 8, 'ஒன்பது': 9, 'பத்து': 10,
        'பதினொன்று': 11, 'பன்னிரண்டு': 12, 'பதிமூன்று': 13, 'பதினான்கு': 14, 'பதினைந்து': 15,
        'பதினாறு': 16, 'பதினேழு': 17, 'பதினெட்டு': 18, 'பத்தொன்பது': 19, 'இருபது': 20,
        'இருபத்தொன்று': 21, 'இருபத்திரண்டு': 22, 'இருபத்திமூன்று': 23, 'இருபத்தி நான்கு': 24,
        'இருபத்தைந்து': 25, 'இருபத்தாறு': 26, 'இருபத்தேழு': 27, 'இருபத்தெட்டு': 28,
        'இருபத்தொன்பது': 29, 'முப்பது': 30, 'முப்பத்தொன்று': 31,
        # Ordinal forms (with -ஆம் suffix)
        'ஒன்றாம்': 1, 'இரண்டாம்': 2, 'மூன்றாம்': 3, 'நான்காம்': 4, 'ஐந்தாம்': 5,
        'ஆறாம்': 6, 'ஏழாம்': 7, 'எட்டாம்': 8, 'ஒன்பதாம்': 9, 'பத்தாம்': 10,
        'பதினொன்றாம்': 11, 'பன்னிரண்டாம்': 12, 'பதிமூன்றாம்': 13, 'பதினான்காம்': 14, 'பதினைந்தாம்': 15,
        'பதினாறாம்': 16, 'பதினேழாம்': 17, 'பதினெட்டாம்': 18, 'பத்தொன்பதாம்': 19, 'இருபதாம்': 20,
        'இருபத்தொன்றாம்': 21, 'இருபத்திரண்டாம்': 22, 'இருபத்திமூன்றாம்': 23, 'இருபத்தி நான்காம்': 24,
        'இருபத்தைந்தாம்': 25, 'இருபத்தாறாம்': 26, 'இருபத்தேழாம்': 27, 'இருபத்தெட்டாம்': 28,
        'இருபத்தொன்பதாம்': 29, 'முப்பதாம்': 30, 'முப்பத்தொன்றாம்': 31,
        # Alternative spellings (with space variations)
        'இருபத்திநான்கு': 24, 'இருபத்திநான்காம்': 24,
    }

    # Tamil date keywords
    TAMIL_DATE_KEYWORDS = ['தேதி', 'நாள்', 'தினம்']  # date, day, day

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
    # NOTE: "sales" is NOT a category - it's a metric! Do not add it here.
    _DEFAULT_CATEGORIES: Set[str] = {
        'orders', 'products', 'customers',
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
        print(f"  [OK] Learned entities from profiles:")
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

    # Multi-domain query patterns - queries requiring data from DIFFERENT tables
    # Format: (pattern, source_hint, target_hint, intermediate_variable)
    # These are GENERIC patterns - they detect cross-table intent without hardcoding specific table names
    MULTI_DOMAIN_PATTERNS = [
        # Pattern: "who/what [from table B] on/during [extreme from table A]"
        # E.g., "who worked on peak sales date", "what sold on best attendance day"
        (r'who (?:worked|was present|attended|came|showed up).*(?:peak|highest|best|top|maximum)', 'primary', 'secondary', 'peak_date'),
        (r'(?:staff|employees|workers|people).*(?:on|during|when).*(?:peak|highest|best|top|maximum)', 'primary', 'secondary', 'peak_date'),
        
        # Pattern: "[table B data] on/during [extreme from table A]"
        (r'(?:inventory|stock|products|items|orders).*(?:peak|highest|best|top|maximum)', 'primary', 'secondary', 'peak_date'),
        
        # Pattern: "on the day when [table A metric was extreme], show [table B data]"
        (r'(?:on|during).*(?:day|date).*(?:when|where).*(?:highest|lowest|peak|best|worst)', 'primary', 'secondary', 'target_date'),
        
        # Pattern: Explicit cross-reference 
        (r'(?:combine|join|merge|cross.?reference).*(?:tables?|data|sheets?)', 'primary', 'secondary', 'join_key'),
        (r'from (?:both|multiple|different) (?:tables?|sheets?|data)', 'primary', 'secondary', 'join_key'),
    ]

    # Trend analysis keywords - indicates user wants trend/pattern analysis
    TREND_ANALYSIS_TERMS = [
        'trend', 'trends', 'trending', 'pattern', 'patterns',
        'how does', 'how did', 'how has', 'how is',
        'change over', 'changes over', 'changed over',
        'observed', 'can be observed', 'observation',
        'movement', 'direction', 'going up', 'going down',
        'increasing', 'decreasing', 'growing', 'declining',
        'fluctuation', 'variation', 'volatility',
        'போக்கு', 'மாற்றம்', 'எப்படி உள்ளது'  # Tamil: trend, change, how is it
    ]

    # Summary/overview keywords - indicates user wants high-level summary
    SUMMARY_TERMS = [
        'summary', 'summarize', 'summarise', 'overview', 'high-level',
        'high level', 'overall picture', 'big picture', 'snapshot',
        'business summary', 'executive summary', 'key insights',
        'main points', 'highlights', 'takeaways', 'key findings',
        'at a glance', 'quick summary', 'brief overview',
        'சுருக்கம்', 'முக்கிய அம்சங்கள்'  # Tamil: summary, key points
    ]

    # Impact/correlation keywords - indicates user wants to understand relationships
    IMPACT_ANALYSIS_TERMS = [
        'affects', 'affect', 'affecting', 'affected',
        'impacts', 'impact', 'impacting', 'impacted',
        'influences', 'influence', 'influencing',
        'factor', 'factors', 'driver', 'drivers',
        'correlate', 'correlation', 'relationship',
        'depends on', 'dependent on', 'related to',
        'contributes to', 'contribution', 'effect on',
        'what causes', 'why is', 'reason for',
        'பாதிக்கிறது', 'காரணம்'  # Tamil: affects, reason
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
            'multi_domain_query': self._detect_multi_domain_query(q_lower),
            'dimension_keywords': self._extract_dimension_keywords(q_lower),
            'time_period': self._extract_time_period(q_lower),
            'explicit_table': self._extract_explicit_table(question),
            'date_specific': self._extract_specific_date(q_lower),
            'custom_entities': self._extract_custom_entities(q_lower),
            # Analytical intent detection
            'trend_intent': self._is_trend_query(q_lower),
            'summary_intent': self._is_summary_query(q_lower),
            'impact_intent': self._is_impact_query(q_lower),
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

    # Metric keywords that should NEVER be extracted as categories
    # Even if they accidentally appear in learned categories
    METRIC_EXCLUSIONS = {
        'sales', 'revenue', 'profit', 'cost', 'expense', 'margin',
        'orders', 'transactions', 'quantity', 'units', 'items',
        'discount', 'tax', 'gst', 'subtotal', 'shipping', 'aov',
        'total', 'average', 'count', 'sum', 'net', 'gross'
    }

    def _extract_category(self, text_lower: str, original: str) -> Optional[str]:
        """
        Extract product category from text.
        Checks quoted terms first, then known categories.

        IMPORTANT: Excludes metric keywords (sales, revenue, etc.) from being
        extracted as categories to avoid confusion like "Sarees" vs "sales".
        """
        # Check for double-quoted terms
        double_quoted = re.findall(r'"([^"]+)"', original)
        if double_quoted:
            return double_quoted[0]

        # Check for single-quoted terms
        single_quoted = re.findall(r"'([^']+)'", original)
        if single_quoted:
            return single_quoted[0]

        # Collect all matching categories with their position and length
        matches = []
        for cat in self.CATEGORIES:
            # Skip if this is a metric keyword (not a real product category)
            if cat.lower() in self.METRIC_EXCLUSIONS:
                continue

            pattern = r'\b' + re.escape(cat) + r'\b'
            match = re.search(pattern, text_lower)
            if match:
                matches.append((cat, len(cat), match.start()))

        if not matches:
            return None

        # Sort by: 1) Length descending (longer = more specific)
        #          2) Position ascending (earlier in text = more likely intended)
        # This ensures "Sarees" beats "sales" and earlier mentions win ties
        matches.sort(key=lambda x: (-x[1], x[2]))

        return matches[0][0].title()

    def _extract_location(self, text: str) -> Optional[str]:
        """Extract location/city from text with fuzzy matching support.

        Handles cases like:
        - "Chennai" matching "Chennai Main" or "Chennai North"
        - "Bangalore" matching "Bangalore Central"
        """
        text_lower = text.lower()

        # First try exact match on learned locations
        for loc in self.LOCATIONS:
            pattern = r'\b' + re.escape(loc) + r'\b'
            if re.search(pattern, text_lower):
                return loc.title()

        # FUZZY MATCH: Check if user's input is a PREFIX of any learned location
        # e.g., "chennai" should match "chennai main"
        # Extract potential location words from user input
        common_cities = ['chennai', 'bangalore', 'mumbai', 'delhi', 'hyderabad', 'pune',
                        'kolkata', 'ahmedabad', 'jaipur', 'lucknow', 'coimbatore', 'madurai']

        for city in common_cities:
            if city in text_lower:
                # Find any learned location that STARTS with this city
                for loc in self.LOCATIONS:
                    if loc.startswith(city):
                        return loc.title()  # Return the full location name
                # If no learned location, return the city itself
                return city.title()

        # Also check custom entities that might be area/location related
        location_entity_types = ['area_name', 'area', 'location', 'city', 'zone', 'region']
        for entity_type in location_entity_types:
            if entity_type in self._learned_custom_entities:
                for val in self._learned_custom_entities[entity_type]:
                    val_lower = val.lower()
                    # Exact match
                    pattern = r'\b' + re.escape(val_lower) + r'\b'
                    if re.search(pattern, text_lower):
                        return val.title()
                    # Fuzzy: check if user input contains start of location
                    for city in common_cities:
                        if city in text_lower and val_lower.startswith(city):
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
        """
        Extract ALL month names mentioned in the text.
        Handles various connectors: spaces, hyphens, "to", "and", "vs", etc.

        Examples:
        - "september-october" -> ['September', 'October']
        - "sep to oct" -> ['September', 'October']
        - "august and december" -> ['August', 'December']
        """
        found_months = []

        # Normalize text: replace hyphens and common connectors with spaces
        # This helps word boundary matching work correctly
        normalized_text = text.replace('-', ' ').replace('/', ' ')

        full_names = {
            '01': 'January', '02': 'February', '03': 'March',
            '04': 'April', '05': 'May', '06': 'June',
            '07': 'July', '08': 'August', '09': 'September',
            '10': 'October', '11': 'November', '12': 'December'
        }

        for month_name, month_num in self.MONTHS.items():
            # Use word boundaries on normalized text
            pattern = r'\b' + month_name + r'\b'
            if re.search(pattern, normalized_text):
                full_name = full_names[month_num]
                if full_name not in found_months:
                    found_months.append(full_name)
        return found_months

    def _is_multi_month_comparison(self, text: str) -> bool:
        """
        Check if question compares TWO OR MORE months.
        This helps route to tables with multi-month columns instead of month-specific tables.

        Examples:
        - "Compare September and October sales" -> True
        - "September vs October" -> True
        - "How did sales change from September to October?" -> True
        - "What were September sales?" -> False (only one month)
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

    # Spelled-out numbers for time period parsing
    SPELLED_NUMBERS = {
        'one': '1', 'two': '2', 'three': '3', 'four': '4', 'five': '5',
        'six': '6', 'seven': '7', 'eight': '8', 'nine': '9', 'ten': '10',
        'eleven': '11', 'twelve': '12'
    }

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

        # Last N days/weeks/months (with digits)
        last_match = re.search(r'last\s+(\d+)\s*(days?|weeks?|months?)', text)
        if last_match:
            return f"last_{last_match.group(1)}_{last_match.group(2)}"

        # Last N days/weeks/months (with spelled-out numbers like "three", "two")
        spelled_pattern = r'last\s+(one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve)\s*(days?|weeks?|months?)'
        spelled_match = re.search(spelled_pattern, text)
        if spelled_match:
            num = self.SPELLED_NUMBERS.get(spelled_match.group(1), '1')
            return f"last_{num}_{spelled_match.group(2)}"

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
        # Common words that should NOT be treated as table names
        skip_words = {'or', 'and', 'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be',
                      'this', 'that', 'these', 'those', 'it', 'they', 'we', 'you',
                      'my', 'your', 'our', 'their', 'his', 'her', 'its',
                      'what', 'which', 'who', 'where', 'when', 'why', 'how',
                      'all', 'any', 'some', 'no', 'not', 'more', 'less',
                      'stable', 'volatile', 'over', 'time', 'data'}

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
                table_name = match.group(1).strip().lower()
                # Skip common words
                if table_name in skip_words:
                    continue
                return match.group(1).strip()

        return None

    def _extract_specific_date(self, text: str) -> Optional[Dict]:
        """
        Extract specific date references like "November 15th" or "15/11/2025"
        Also handles Tamil date patterns like "இருபத்தி நான்காம் தேதி நவம்பர்"
        """
        # First, try Tamil number + month pattern
        tamil_date = self._extract_tamil_date(text)
        if tamil_date:
            return tamil_date

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

    def _extract_tamil_date(self, text: str) -> Optional[Dict]:
        """
        Extract date from Tamil text patterns like:
        - "இருபத்தி நான்காம் தேதி நவம்பர்" (24th date November)
        - "நவம்பர் மாதம் இருபத்தி நான்காம் தேதி" (November month 24th date)
        - "24 தேதி நவம்பர்" (24 date November)
        """
        day = None
        month_num = None

        # Try to find Tamil number word in text
        for tamil_num, num_value in self.TAMIL_NUMBERS.items():
            if tamil_num in text:
                day = num_value
                break

        # If no Tamil number found, try numeric + தேதி pattern
        if day is None:
            numeric_date_pattern = r'(\d{1,2})\s*(?:' + '|'.join(self.TAMIL_DATE_KEYWORDS) + r')'
            match = re.search(numeric_date_pattern, text)
            if match:
                day = int(match.group(1))

        # Find Tamil month name
        for month_name, m_num in self.MONTHS.items():
            if month_name in text:
                month_num = int(m_num)
                break

        # Return if we found both day and month
        if day is not None and month_num is not None:
            if 1 <= day <= 31:
                return {
                    'type': 'specific_day',
                    'month': month_num,
                    'day': day
                }

        # If only day found with Tamil date keyword, return partial
        if day is not None and any(kw in text for kw in self.TAMIL_DATE_KEYWORDS):
            if 1 <= day <= 31:
                return {
                    'type': 'specific_day',
                    'day': day,
                    'month': None  # Month to be inferred from context
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

    def _is_trend_query(self, text: str) -> bool:
        """
        Check if question is asking for trend/pattern analysis.

        Examples:
        - "What trends can be observed in sales over time?"
        - "How did sales trend last month?"
        - "காலப்போக்கில் sales trend எப்படி உள்ளது?"
        """
        return any(term in text for term in self.TREND_ANALYSIS_TERMS)

    def _is_summary_query(self, text: str) -> bool:
        """
        Check if question is asking for a high-level summary/overview.

        Examples:
        - "Give a high-level business summary"
        - "What's the overall picture?"
        - "இந்த dataset-க்கு ஒரு summary கொடு"
        """
        return any(term in text for term in self.SUMMARY_TERMS)

    def _is_impact_query(self, text: str) -> bool:
        """
        Check if question is asking about impact/correlation analysis.

        Examples:
        - "Which factor affects profit the most?"
        - "What impacts sales?"
        - "Profit-ஐ அதிகமாக பாதிக்கும் காரணி எது?"
        """
        return any(term in text for term in self.IMPACT_ANALYSIS_TERMS)

    def _detect_multi_domain_query(self, text: str) -> Optional[Dict[str, str]]:
        """
        Detect if query requires data from multiple different tables/domains.
        
        Returns dict with:
        - source_domain: Primary data domain (e.g., 'sales')
        - target_domain: Secondary data domain (e.g., 'attendance')
        - intermediate_variable: What needs to be extracted from source (e.g., 'peak_sales_date')
        - pattern_matched: The regex pattern that matched
        
        Examples:
        - "Who worked on peak sales dates?" -> {source: 'sales', target: 'attendance', var: 'peak_sales_date'}
        - "What was sold on best attendance days?" -> {source: 'attendance', target: 'sales', var: 'best_attendance_date'}
        """
        for pattern, source, target, var in self.MULTI_DOMAIN_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return {
                    'source_domain': source,
                    'target_domain': target,
                    'intermediate_variable': var,
                    'pattern_matched': pattern
                }
        return None

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

        # Projection/continuation phrases - user is asking about previous result
        projection_phrases = [
            'if this', 'if the', 'if it', 'if they',
            'continues', 'continue', 'expected', 'predict',
            'projection', 'forecast', 'trend', 'pattern',
            'next month', 'next quarter', 'next week',
            'going forward', 'based on this', 'given this',
            'the top', 'the bottom', 'the highest', 'the lowest',
            'that category', 'this category', 'these categories',
            'the best', 'the worst', 'the same',
        ]

        if any(phrase in q_lower for phrase in projection_phrases):
            return True

        # Tamil follow-up phrases (check against original, not lowercase)
        tamil_followup_phrases = [
            'அதே நாள்', 'அதே தேதி', 'அந்த நாள்',  # same day, same date, that day
            'எப்படி', 'என்ன பற்றி',  # how about, what about
            'தொடர்ந்தால்', 'அடுத்த', 'எதிர்பார்க்கப்படும்',  # continues, next, expected
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
        # Analytical intents
        if entities.get('trend_intent'):
            parts.append("Intent: Trend Analysis")
        if entities.get('summary_intent'):
            parts.append("Intent: Summary/Overview")
        if entities.get('impact_intent'):
            parts.append("Intent: Impact/Correlation Analysis")

        return " | ".join(parts) if parts else "No entities extracted"
