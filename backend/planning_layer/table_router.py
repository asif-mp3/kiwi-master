"""
Table Router - Intelligent query routing to the correct table.

UPDATED: Now uses hybrid LLM-based selection for better accuracy with any dataset.
The old hardcoded scoring approach is kept as a fallback.

Selection Strategy:
1. Check for explicit table reference (user mentions "from X table")
2. Try LLM-based semantic selection (understands intent)
3. Fall back to rule-based scoring if LLM fails
"""

from typing import Optional, List, Tuple, Dict, Any
from schema_intelligence.profile_store import ProfileStore
from planning_layer.entity_extractor import EntityExtractor

# Configuration for LLM-based selection
USE_LLM_SELECTION = True  # Set to False to disable LLM and use only rule-based
LLM_SELECTION_TIMEOUT = 8  # Seconds to wait for LLM response


def _get_actual_duckdb_tables() -> List[str]:
    """Get list of tables that actually exist in DuckDB (not just in profiles)."""
    try:
        from analytics_engine.duckdb_manager import DuckDBManager
        db = DuckDBManager()
        return db.list_tables()
    except Exception as e:
        print(f"[TableRouter] Warning: Could not get DuckDB tables: {e}")
        return []


class TableRouter:
    """
    Routes queries to the correct table using intelligent scoring.

    This is the CORE FIX for the table confusion problem.
    Instead of dumping 50 schemas to the LLM, we:
    1. Extract entities from the question
    2. Score tables based on entity matches
    3. Return only the best table's schema
    """

    def __init__(self, profile_store: ProfileStore = None):
        self.profile_store = profile_store or ProfileStore()
        self.entity_extractor = EntityExtractor()
        self._last_routing_debug = {}

    def route(self, question: str, previous_context: Dict[str, Any] = None) -> 'RoutingResult':
        """
        Find the best table for a question.

        Args:
            question: User's natural language question
            previous_context: Optional context from previous query (for follow-ups)

        Returns:
            RoutingResult with:
            - table: Best matching table name (or None)
            - entities: Extracted entities from question
            - confidence: 0.0 to 1.0 confidence score
            - alternatives: List of (table_name, score) tuples

        Use RoutingResult properties:
        - is_confident: True if confidence >= 0.6 (use single table)
        - needs_clarification: True if 0.3 <= confidence < 0.6 with multiple alternatives
        - should_fallback: True if confidence < 0.3 or no table found
        """
        # Extract entities from question
        entities = self.entity_extractor.extract(question)

        # Check if this is a follow-up question
        if previous_context and self.entity_extractor.is_followup_question(question, True):
            entities = self._merge_with_context(entities, previous_context)

        # Check for explicit table reference first
        if entities.get('explicit_table'):
            explicit_match = self._find_explicit_table(entities['explicit_table'])
            if explicit_match:
                # Validate that table actually exists in DuckDB
                actual_tables = _get_actual_duckdb_tables()
                if actual_tables:
                    actual_tables_lower = {t.lower(): t for t in actual_tables}
                    if explicit_match not in actual_tables:
                        # Try case-insensitive match
                        if explicit_match.lower() in actual_tables_lower:
                            explicit_match = actual_tables_lower[explicit_match.lower()]
                        else:
                            # Table doesn't exist, skip explicit match
                            explicit_match = None
                            print(f"[TableRouter] Explicit table reference not found in DuckDB")

            if explicit_match:
                self._last_routing_debug = {
                    'method': 'explicit_reference',
                    'table': explicit_match,
                    'confidence': 1.0
                }
                return RoutingResult(
                    table=explicit_match,
                    entities=entities,
                    confidence=1.0,
                    alternatives=[(explicit_match, 100)]
                )

        # NEW: Try LLM-based semantic selection for better accuracy
        if USE_LLM_SELECTION:
            try:
                from planning_layer.llm_table_selector import select_table_hybrid

                profiles = self.profile_store.get_all_profiles()
                if profiles:
                    selected_table, confidence, reason = select_table_hybrid(
                        question=question,
                        profiles=profiles,
                        entities=entities,
                        use_llm=True,
                        llm_timeout=LLM_SELECTION_TIMEOUT
                    )

                    if selected_table and confidence >= 0.6:
                        # Validate table exists in DuckDB
                        actual_tables = _get_actual_duckdb_tables()
                        if not actual_tables or selected_table in actual_tables:
                            self._last_routing_debug = {
                                'method': 'llm_semantic_selection',
                                'table': selected_table,
                                'confidence': confidence,
                                'reason': reason
                            }
                            return RoutingResult(
                                table=selected_table,
                                entities=entities,
                                confidence=confidence,
                                alternatives=[(selected_table, int(confidence * 100))]
                            )
                        else:
                            # Try case-insensitive match
                            actual_tables_lower = {t.lower(): t for t in actual_tables}
                            if selected_table.lower() in actual_tables_lower:
                                corrected_table = actual_tables_lower[selected_table.lower()]
                                self._last_routing_debug = {
                                    'method': 'llm_semantic_selection',
                                    'table': corrected_table,
                                    'confidence': confidence,
                                    'reason': reason
                                }
                                return RoutingResult(
                                    table=corrected_table,
                                    entities=entities,
                                    confidence=confidence,
                                    alternatives=[(corrected_table, int(confidence * 100))]
                                )
            except Exception as e:
                print(f"[TableRouter] LLM selection failed, falling back to scoring: {e}")

        # FALLBACK: Get candidate tables with rule-based scoring
        candidates = self.profile_store.find_best_table_for_query(entities)

        # CRITICAL: Filter candidates to only include tables that actually exist in DuckDB
        # This prevents errors from stale profiles referencing non-existent tables
        actual_tables = _get_actual_duckdb_tables()
        if actual_tables:
            # Build case-insensitive lookup map
            actual_tables_lower = {t.lower(): t for t in actual_tables}

            validated_candidates = []
            for table_name, score in candidates:
                # Try exact match first
                if table_name in actual_tables:
                    validated_candidates.append((table_name, score))
                # Try case-insensitive match
                elif table_name.lower() in actual_tables_lower:
                    # Use the actual table name from DuckDB (correct casing)
                    actual_name = actual_tables_lower[table_name.lower()]
                    validated_candidates.append((actual_name, score))
                    print(f"[TableRouter] Fixed table name casing: {table_name} -> {actual_name}")
                else:
                    print(f"[TableRouter] Filtered out non-existent table: {table_name}")

            candidates = validated_candidates

        if not candidates:
            # No tables matched - return None and let planner handle with fallback
            self._last_routing_debug = {
                'method': 'no_match',
                'entities': entities,
                'candidates': []
            }
            return RoutingResult(
                table=None,
                entities=entities,
                confidence=0.0,
                alternatives=[]
            )

        best_table, best_score = candidates[0]

        # Calculate confidence based on score distribution
        confidence = self._calculate_confidence(candidates)

        # Boost confidence for cross-table queries when we found a table with aggregate data
        # This prevents unnecessary clarification for "across all months" type queries
        if entities.get('cross_table_intent') and best_score >= 40:
            # High score with cross-table intent means we found a good aggregate table
            confidence = min(1.0, confidence + 0.25)

        # Store debug info for transparency
        self._last_routing_debug = {
            'method': 'scoring',
            'entities': entities,
            'candidates': candidates[:5],  # Top 5
            'selected': best_table,
            'score': best_score,
            'confidence': confidence,
            'cross_table_intent': entities.get('cross_table_intent', False)
        }

        return RoutingResult(
            table=best_table,
            entities=entities,
            confidence=confidence,
            alternatives=candidates[:5]  # Top 5 candidates
        )

    def _merge_with_context(self, new_entities: Dict[str, Any],
                           previous_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Merge new entities with previous context for follow-up questions.
        New values override old, but old values are kept if new is None.
        """
        merged = {}

        # Get previous entities
        prev_entities = previous_context.get('entities', {})

        # Keys to merge (inherit from previous if new is None)
        merge_keys = ['month', 'metric', 'category', 'location', 'aggregation', 'date_specific']

        for key in merge_keys:
            new_val = new_entities.get(key)
            prev_val = prev_entities.get(key)

            # New value takes precedence if set
            if new_val is not None:
                merged[key] = new_val
            elif prev_val is not None:
                merged[key] = prev_val

        # Always use new values for these (don't inherit)
        merged['comparison'] = new_entities.get('comparison', False)
        merged['time_period'] = new_entities.get('time_period')
        merged['explicit_table'] = new_entities.get('explicit_table')
        merged['raw_question'] = new_entities.get('raw_question')

        return merged

    def _find_explicit_table(self, table_ref: str) -> Optional[str]:
        """
        Find table by explicit reference in question.
        Handles partial matches and case insensitivity.
        """
        table_ref_lower = table_ref.lower().strip()
        all_tables = self.profile_store.get_table_names()

        # First: Try exact match (case insensitive)
        for table in all_tables:
            if table.lower() == table_ref_lower:
                return table

        # Second: Try contains match
        matches = []
        for table in all_tables:
            if table_ref_lower in table.lower():
                matches.append(table)

        if len(matches) == 1:
            return matches[0]
        elif len(matches) > 1:
            # Multiple matches - try to find best one
            # Prefer shorter names (more specific match)
            matches.sort(key=lambda x: len(x))
            return matches[0]

        # Third: Try word-based partial match
        ref_words = set(table_ref_lower.split())
        best_match = None
        best_word_overlap = 0

        for table in all_tables:
            table_words = set(table.lower().replace('-', ' ').replace('–', ' ').split())
            overlap = len(ref_words & table_words)
            if overlap > best_word_overlap:
                best_word_overlap = overlap
                best_match = table

        if best_word_overlap >= len(ref_words) * 0.5:  # At least 50% words match
            return best_match

        return None

    def _calculate_confidence(self, candidates: List[Tuple[str, int]]) -> float:
        """
        Calculate confidence score based on candidate distribution.

        High confidence if:
        - Single table scores much higher than others
        - Clear winner based on multiple matching criteria
        - Best table's name strongly matches query keywords

        Low confidence if:
        - Multiple tables with very similar scores (within 10%)
        - Low overall scores (under 20)
        """
        if not candidates:
            return 0.0

        if len(candidates) == 1:
            # Only one candidate - base confidence on score
            score = candidates[0][1]
            return min(1.0, score / 40)  # 40+ score = max confidence (lowered threshold)

        # Multiple candidates - check score gap
        best_table, best_score = candidates[0]
        second_score = candidates[1][1]

        # Score gap analysis
        if best_score <= 0:
            return 0.0

        gap = best_score - second_score
        gap_ratio = gap / best_score

        # HIGH CONFIDENCE CONDITIONS (no clarification needed):
        # 1. Strong absolute score (>= 50) with reasonable gap (>= 15%)
        if best_score >= 50 and gap_ratio >= 0.15:
            return max(0.7, min(1.0, best_score / 60))

        # 2. Very high score (>= 70) regardless of gap - clear keyword match
        if best_score >= 70:
            return max(0.75, min(1.0, best_score / 80))

        # 3. Large gap (>= 30 points) - clear winner even if scores are moderate
        if gap >= 30:
            return max(0.7, min(1.0, gap / 50 + 0.5))

        # Base confidence from score magnitude
        magnitude_confidence = min(1.0, best_score / 50)  # 50+ = max

        # Gap confidence - penalize very close scores more heavily
        if gap_ratio < 0.1:  # Within 10% - genuinely ambiguous
            gap_confidence = 0.2
        elif gap_ratio < 0.2:  # Within 20%
            gap_confidence = 0.4
        else:
            gap_confidence = min(1.0, gap_ratio * 1.5)

        # Combined confidence
        confidence = (magnitude_confidence * 0.5) + (gap_confidence * 0.5)

        return round(confidence, 2)

    def get_table_schema(self, table_name: str) -> str:
        """
        Get concise schema description for a single table.
        This replaces the 'top_k=50' schema dump.

        Returns a focused schema suitable for the planner LLM.
        """
        profile = self.profile_store.get_profile(table_name)
        if not profile:
            return f"Table '{table_name}' not found in profiles."

        schema_parts = []

        # Table header
        schema_parts.append(f"Table: {table_name}")
        schema_parts.append(f"Type: {profile.get('table_type', 'unknown')}")
        schema_parts.append(f"Rows: {profile.get('row_count', 'unknown')}")
        schema_parts.append(f"Granularity: {profile.get('granularity', 'unknown')}")

        # Date range
        date_range = profile.get('date_range', {})
        if date_range.get('min') or date_range.get('month'):
            if date_range.get('month'):
                schema_parts.append(f"Month: {date_range['month']}")
            if date_range.get('min') and date_range.get('max'):
                schema_parts.append(f"Date range: {date_range['min'][:10]} to {date_range['max'][:10]}")

        # Columns by role
        columns = profile.get('columns', {})

        # Date columns
        date_cols = [col for col, info in columns.items() if info.get('role') == 'date']
        if date_cols:
            schema_parts.append(f"Date columns: {', '.join(date_cols)}")

        # Metric columns
        metric_cols = [col for col, info in columns.items() if info.get('role') == 'metric']
        if metric_cols:
            schema_parts.append(f"Metric columns: {', '.join(metric_cols[:10])}")  # Limit to 10
            if len(metric_cols) > 10:
                schema_parts.append(f"  ... and {len(metric_cols) - 10} more metrics")

        # Dimension columns with sample values
        dimension_cols = [(col, info) for col, info in columns.items()
                         if info.get('role') == 'dimension']
        if dimension_cols:
            dim_parts = []
            for col, info in dimension_cols[:5]:  # Limit to 5
                unique_values = info.get('unique_values', [])
                if unique_values:
                    sample = ', '.join(str(v) for v in unique_values[:3])
                    dim_parts.append(f"  - {col} (e.g., {sample})")
                else:
                    dim_parts.append(f"  - {col}")

            schema_parts.append("Dimension columns:")
            schema_parts.extend(dim_parts)

        # Identifier columns
        id_cols = [col for col, info in columns.items() if info.get('role') == 'identifier']
        if id_cols:
            schema_parts.append(f"Identifier columns: {', '.join(id_cols[:5])}")

        # Add description if available
        description = profile.get('description')
        if description:
            schema_parts.append(f"Description: {description}")

        return "\n".join(schema_parts)

    def get_fallback_schema(self, question: str, top_k: int = 5) -> str:
        """
        Fallback: Get schemas for top K candidate tables.
        Used when routing confidence is low or table not found.

        This is still much better than top_k=50!
        """
        entities = self.entity_extractor.extract(question)
        candidates = self.profile_store.find_best_table_for_query(entities)

        if not candidates:
            # No matches at all - return all tables with basic info
            all_tables = self.profile_store.get_table_names()
            return self._generate_basic_schema_list(all_tables[:top_k])

        schemas = []
        for table_name, score in candidates[:top_k]:
            schema = self.get_table_schema(table_name)
            schemas.append(f"[Score: {score}]\n{schema}")

        return "\n\n---\n\n".join(schemas)

    def _generate_basic_schema_list(self, table_names: List[str]) -> str:
        """
        Generate basic schema list for tables without detailed profiles.
        """
        parts = []
        for table_name in table_names:
            profile = self.profile_store.get_profile(table_name)
            if profile:
                parts.append(self.get_table_schema(table_name))
            else:
                parts.append(f"Table: {table_name} (no profile available)")

        return "\n\n---\n\n".join(parts)

    def get_tables_for_comparison(self, entities: Dict[str, Any],
                                  months: List[str] = None) -> List[str]:
        """
        Get tables for comparison queries.

        When user asks to compare months/periods, we need multiple tables.
        """
        if not months:
            # Try to extract months from entities
            if entities.get('month'):
                months = [entities['month']]
            else:
                return []

        tables = []
        for month in months:
            month_tables = self.profile_store.get_tables_for_month(month)
            if month_tables:
                # Get the best one for each month
                # Prefer transactional over summary
                for table in month_tables:
                    profile = self.profile_store.get_profile(table)
                    if profile and profile.get('table_type') == 'transactional':
                        tables.append(table)
                        break
                else:
                    # No transactional found, use first match
                    tables.append(month_tables[0])

        return tables

    def get_routing_debug(self) -> Dict[str, Any]:
        """
        Get debug information about the last routing decision.
        Useful for transparency and troubleshooting.
        """
        return self._last_routing_debug.copy()

    def explain_routing(self, question: str) -> str:
        """
        Explain why a specific table was chosen.
        Human-readable explanation for debugging.
        """
        result = self.route(question)
        table = result.table
        entities = result.entities
        confidence = result.confidence
        debug = self.get_routing_debug()

        lines = [f"Question: {question}", ""]

        # Show extracted entities
        lines.append("Extracted entities:")
        for key, value in entities.items():
            if value and key != 'raw_question':
                lines.append(f"  - {key}: {value}")

        lines.append("")

        # Show routing result
        if table:
            lines.append(f"Selected table: {table}")
            lines.append(f"Confidence: {confidence:.0%}")

            # Show clarification status
            if result.needs_clarification:
                lines.append("⚠️  NEEDS CLARIFICATION - multiple similar-scoring tables")
                lines.append(f"   Options: {result.get_clarification_options()}")
            elif result.is_confident:
                lines.append("✓ HIGH CONFIDENCE - clear winner")
            else:
                lines.append("⚡ MEDIUM CONFIDENCE - using best match")

            # Show why
            if debug.get('method') == 'explicit_reference':
                lines.append("Reason: User explicitly mentioned this table")
            elif debug.get('candidates'):
                lines.append("Top candidates:")
                for t, score in debug['candidates'][:3]:
                    marker = "→" if t == table else " "
                    lines.append(f"  {marker} {t}: {score} points")

                # Explain scoring
                profile = self.profile_store.get_profile(table)
                if profile:
                    explanation = self.profile_store.get_match_explanation(table, entities)
                    lines.append(f"Match explanation: {explanation}")
        else:
            lines.append("No table matched the query criteria")
            if result.should_fallback:
                lines.append("Falling back to multi-table schema context")

        return "\n".join(lines)


class RoutingResult:
    """
    Structured result from table routing.
    """

    def __init__(self, table: Optional[str], entities: Dict[str, Any],
                 confidence: float, alternatives: List[Tuple[str, int]] = None):
        self.table = table
        self.entities = entities
        self.confidence = confidence
        self.alternatives = alternatives or []

    @property
    def is_confident(self) -> bool:
        """Check if routing result is confident enough to use single table"""
        return self.confidence >= 0.6

    @property
    def needs_clarification(self) -> bool:
        """
        Check if we should ask user for clarification.

        GENUINE CONFUSION only - not all the time. We ask when:
        1. Multiple tables have VERY close scores (within 10% of each other)
        2. Both tables have meaningful scores (>= 30) - not random low matches
        3. Neither table has an explicit phrase match (300+ score)

        Don't ask when:
        - One table clearly wins (>15% score gap)
        - Scores are too low to be meaningful
        - There's an explicit table name match
        """
        if len(self.alternatives) < 2:
            return False

        best_table, best_score = self.alternatives[0]
        second_table, second_score = self.alternatives[1]

        if best_score <= 0:
            return False

        # NEVER ask if there's an explicit table phrase match (high score)
        # This means user explicitly mentioned a table by name
        if best_score >= 200:
            return False

        # NEVER ask if scores are too low - neither is a good match anyway
        if best_score < 30 or second_score < 25:
            return False

        # Calculate score gap ratio
        score_gap_ratio = (best_score - second_score) / best_score if best_score > 0 else 1

        # GENUINE CONFUSION: Scores are VERY close (within 10%)
        # Both tables are plausible matches - user should choose
        if score_gap_ratio < 0.10:
            return True

        # BORDERLINE: Scores within 15% AND both have decent scores (>40)
        # This catches cases like 85 vs 75 where both are reasonable
        if score_gap_ratio < 0.15 and best_score >= 40 and second_score >= 35:
            return True

        return False

    @property
    def should_fallback(self) -> bool:
        """Check if we should use fallback multi-table approach"""
        return self.confidence < 0.3 or self.table is None

    def get_clarification_options(self) -> List[str]:
        """Get table options for user clarification"""
        if not self.needs_clarification:
            return []

        # Return tables with significant scores (>= 40% of best score)
        best_score = self.alternatives[0][1] if self.alternatives else 0
        threshold = best_score * 0.4

        options = [t for t, score in self.alternatives if score >= threshold]

        # Limit to 5 options max
        return options[:5]
