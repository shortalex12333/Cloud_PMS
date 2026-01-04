"""
SearchPlan Architecture - Wave-Based Federated Search
======================================================

Implements the wave-based search strategy defined in ENTITY_TABLE_PRIORS.md.

Wave 0 (<100ms): Exact ID lookups
Wave 1 (<300ms): Top 2-4 sources based on entity type
Wave 2 (<800ms): Broader search, fuzzier matches
Wave 3 (async): Vector/semantic search

SECURITY:
- yacht_id is ALWAYS required
- All queries parameterized
- Only declared columns searchable

Usage:
    from api.search_planner import SearchPlanner, SearchPlan

    planner = SearchPlanner(supabase_client, yacht_id)
    plan = planner.create_plan(entities=[{"type": "PART_NUMBER", "value": "ENG-0008"}])
    results = planner.execute_plan(plan)
"""

import time
import asyncio
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor, as_completed
import re


class MatchType(Enum):
    """How to match a search term against a column."""
    EXACT = "exact"
    ILIKE = "ilike"
    TRIGRAM = "trigram"
    RANGE = "range"
    CONTAINS = "contains"
    VECTOR = "vector"


class Wave(Enum):
    """Search wave with timing budget."""
    WAVE_0 = 0  # <100ms - Exact lookups
    WAVE_1 = 1  # <300ms - Top sources
    WAVE_2 = 2  # <800ms - Broader search
    WAVE_3 = 3  # Async - Vector/semantic


@dataclass
class SearchSource:
    """A table/column combination to search."""
    table: str
    column: str
    match_type: MatchType
    wave: Wave
    limit: int = 5
    priority: int = 1  # Lower = higher priority


@dataclass
class SearchResult:
    """Result from a single source search."""
    source: SearchSource
    rows: List[Dict[str, Any]]
    row_count: int
    execution_time_ms: float
    match_type_used: MatchType
    confidence_scores: List[float] = field(default_factory=list)
    error: Optional[str] = None


@dataclass
class SearchPlan:
    """Complete search plan with wave assignments."""
    entities: List[Dict[str, Any]]
    wave_0_sources: List[SearchSource] = field(default_factory=list)
    wave_1_sources: List[SearchSource] = field(default_factory=list)
    wave_2_sources: List[SearchSource] = field(default_factory=list)
    wave_3_sources: List[SearchSource] = field(default_factory=list)
    budget_ms: int = 800  # Total sync budget
    created_at: float = field(default_factory=time.time)


@dataclass
class PlanExecutionResult:
    """Results from executing a search plan."""
    plan: SearchPlan
    results: List[SearchResult]
    total_rows: int
    unique_rows: int
    waves_executed: List[Wave]
    total_time_ms: float
    early_exit: bool = False
    early_exit_reason: Optional[str] = None


# =============================================================================
# ENTITY → SOURCE ROUTING TABLE
# =============================================================================

ENTITY_SOURCE_MAP: Dict[str, List[SearchSource]] = {
    # IDENTIFIERS - Wave 0 (Exact)
    "PART_NUMBER": [
        SearchSource("pms_parts", "part_number", MatchType.EXACT, Wave.WAVE_0, limit=1, priority=1),
        SearchSource("v_inventory", "part_number", MatchType.EXACT, Wave.WAVE_0, limit=5, priority=2),
    ],
    "FAULT_CODE": [
        SearchSource("search_fault_code_catalog", "code", MatchType.EXACT, Wave.WAVE_0, limit=1, priority=1),
        SearchSource("pms_faults", "fault_code", MatchType.EXACT, Wave.WAVE_0, limit=5, priority=2),
        SearchSource("search_fault_code_catalog", "code", MatchType.ILIKE, Wave.WAVE_1, limit=5, priority=3),
        SearchSource("pms_faults", "fault_code", MatchType.ILIKE, Wave.WAVE_1, limit=5, priority=4),
    ],
    "SERIAL_NUMBER": [
        SearchSource("pms_equipment", "serial_number", MatchType.EXACT, Wave.WAVE_0, limit=1, priority=1),
    ],

    # NAMES - Wave 1 (ILIKE)
    "PART_NAME": [
        SearchSource("pms_parts", "name", MatchType.ILIKE, Wave.WAVE_1, limit=5, priority=1),
        SearchSource("v_inventory", "name", MatchType.ILIKE, Wave.WAVE_1, limit=5, priority=2),
        SearchSource("pms_parts", "name", MatchType.TRIGRAM, Wave.WAVE_2, limit=10, priority=3),
    ],
    "EQUIPMENT_NAME": [
        SearchSource("graph_nodes", "label", MatchType.ILIKE, Wave.WAVE_1, limit=5, priority=1),
        SearchSource("pms_equipment", "name", MatchType.ILIKE, Wave.WAVE_1, limit=5, priority=2),
        SearchSource("graph_nodes", "label", MatchType.TRIGRAM, Wave.WAVE_2, limit=10, priority=3),
    ],
    "SYSTEM_NAME": [
        SearchSource("graph_nodes", "normalized_label", MatchType.EXACT, Wave.WAVE_0, limit=1, priority=1),
        SearchSource("graph_nodes", "label", MatchType.ILIKE, Wave.WAVE_1, limit=5, priority=2),
        SearchSource("alias_systems", "alias", MatchType.ILIKE, Wave.WAVE_1, limit=5, priority=2),
        SearchSource("graph_nodes", "label", MatchType.TRIGRAM, Wave.WAVE_2, limit=10, priority=3),
    ],
    "COMPONENT_NAME": [
        SearchSource("graph_nodes", "label", MatchType.ILIKE, Wave.WAVE_1, limit=5, priority=1),
        SearchSource("graph_nodes", "label", MatchType.TRIGRAM, Wave.WAVE_2, limit=10, priority=2),
    ],
    "MANUFACTURER": [
        SearchSource("pms_parts", "manufacturer", MatchType.ILIKE, Wave.WAVE_1, limit=5, priority=1),
        SearchSource("pms_suppliers", "name", MatchType.ILIKE, Wave.WAVE_1, limit=5, priority=2),
    ],
    "SUPPLIER_NAME": [
        SearchSource("pms_suppliers", "name", MatchType.ILIKE, Wave.WAVE_1, limit=5, priority=1),
    ],
    "SYMPTOM_NAME": [
        SearchSource("alias_symptoms", "alias", MatchType.ILIKE, Wave.WAVE_1, limit=5, priority=1),
        SearchSource("symptom_aliases", "canonical", MatchType.ILIKE, Wave.WAVE_1, limit=5, priority=2),
        SearchSource("search_document_chunks", "content", MatchType.ILIKE, Wave.WAVE_2, limit=10, priority=3),
    ],

    # LOCATIONS
    "STOCK_LOCATION": [
        SearchSource("v_inventory", "location", MatchType.EXACT, Wave.WAVE_0, limit=10, priority=1),
        SearchSource("v_inventory", "location", MatchType.ILIKE, Wave.WAVE_1, limit=10, priority=2),
    ],
    "EQUIPMENT_LOCATION": [
        SearchSource("pms_equipment", "location", MatchType.ILIKE, Wave.WAVE_1, limit=10, priority=1),
    ],

    # DOCUMENTS
    "DOCUMENT_QUERY": [
        SearchSource("search_document_chunks", "content", MatchType.ILIKE, Wave.WAVE_1, limit=5, priority=1),
        SearchSource("search_document_chunks", "content", MatchType.TRIGRAM, Wave.WAVE_2, limit=10, priority=2),
        SearchSource("search_document_chunks", "content", MatchType.VECTOR, Wave.WAVE_3, limit=10, priority=3),
    ],
    "SECTION_NAME": [
        SearchSource("search_document_chunks", "section_title", MatchType.ILIKE, Wave.WAVE_1, limit=5, priority=1),
    ],
    "DOC_TYPE": [
        SearchSource("search_document_chunks", "doc_type", MatchType.EXACT, Wave.WAVE_0, limit=10, priority=1),
    ],
    "PROCEDURE_SEARCH": [
        SearchSource("search_document_chunks", "content", MatchType.ILIKE, Wave.WAVE_1, limit=5, priority=1),
        SearchSource("maintenance_facts", "content", MatchType.ILIKE, Wave.WAVE_1, limit=5, priority=2),
        SearchSource("search_document_chunks", "content", MatchType.VECTOR, Wave.WAVE_3, limit=10, priority=3),
    ],

    # STATUS/ENUM
    "PRIORITY": [
        SearchSource("pms_work_orders", "priority", MatchType.EXACT, Wave.WAVE_0, limit=20, priority=1),
    ],
    "STATUS": [
        SearchSource("pms_work_orders", "status", MatchType.EXACT, Wave.WAVE_0, limit=20, priority=1),
        SearchSource("pms_faults", "severity", MatchType.EXACT, Wave.WAVE_0, limit=20, priority=2),
    ],
    "SEVERITY": [
        SearchSource("search_fault_code_catalog", "severity", MatchType.EXACT, Wave.WAVE_0, limit=10, priority=1),
    ],

    # GRAPH
    "NODE_TYPE": [
        SearchSource("graph_nodes", "node_type", MatchType.EXACT, Wave.WAVE_0, limit=50, priority=1),
    ],
    "CANONICAL_ENTITY": [
        SearchSource("graph_nodes", "normalized_label", MatchType.EXACT, Wave.WAVE_0, limit=1, priority=1),
        SearchSource("graph_nodes", "normalized_label", MatchType.ILIKE, Wave.WAVE_1, limit=5, priority=2),
    ],

    # FREE TEXT / UNKNOWN
    "FREE_TEXT": [
        SearchSource("graph_nodes", "label", MatchType.ILIKE, Wave.WAVE_1, limit=5, priority=1),
        SearchSource("pms_parts", "name", MatchType.ILIKE, Wave.WAVE_1, limit=5, priority=2),
        SearchSource("search_document_chunks", "content", MatchType.ILIKE, Wave.WAVE_2, limit=10, priority=3),
        SearchSource("search_document_chunks", "content", MatchType.TRIGRAM, Wave.WAVE_2, limit=10, priority=4),
    ],
    "UNKNOWN": [
        SearchSource("graph_nodes", "label", MatchType.ILIKE, Wave.WAVE_1, limit=5, priority=1),
        SearchSource("pms_parts", "name", MatchType.ILIKE, Wave.WAVE_2, limit=10, priority=2),
        SearchSource("search_document_chunks", "content", MatchType.ILIKE, Wave.WAVE_2, limit=10, priority=3),
    ],
}

# Wave timing budgets (cumulative from start)
# NOTE: Budgets must account for network latency to Supabase (~100-300ms per request)
WAVE_BUDGETS_MS = {
    Wave.WAVE_0: 500,   # Exact lookups (single request)
    Wave.WAVE_1: 1500,  # Top sources (2-4 parallel requests)
    Wave.WAVE_2: 3000,  # Broader search
    Wave.WAVE_3: 5000,  # Vector/semantic
}

# Row limits per wave
WAVE_ROW_LIMITS = {
    Wave.WAVE_0: {"per_source": 1, "total": 2},
    Wave.WAVE_1: {"per_source": 5, "total": 15},
    Wave.WAVE_2: {"per_source": 10, "total": 25},
    Wave.WAVE_3: {"per_source": 10, "total": 20},
}


class SearchPlanner:
    """
    Creates and executes search plans based on entity types.

    Security: yacht_id is REQUIRED for all queries.
    """

    def __init__(self, supabase_client, yacht_id: str):
        """Initialize with Supabase client and yacht_id."""
        if not yacht_id:
            raise ValueError("yacht_id is required for all queries")

        uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
        if not re.match(uuid_pattern, yacht_id.lower()):
            raise ValueError(f"Invalid yacht_id format: {yacht_id}")

        self.client = supabase_client
        self.yacht_id = yacht_id

    def create_plan(
        self,
        entities: List[Dict[str, Any]],
        max_waves: int = 3,
    ) -> SearchPlan:
        """
        Create a search plan based on extracted entities.

        Args:
            entities: List of {"type": "ENTITY_TYPE", "value": "search_term"}
            max_waves: Maximum wave to include (0-3)

        Returns:
            SearchPlan with sources organized by wave
        """
        plan = SearchPlan(entities=entities)

        # Collect all sources for detected entity types
        all_sources: Dict[Wave, List[SearchSource]] = {
            Wave.WAVE_0: [],
            Wave.WAVE_1: [],
            Wave.WAVE_2: [],
            Wave.WAVE_3: [],
        }

        for entity in entities:
            entity_type = entity.get("type", "UNKNOWN")
            sources = ENTITY_SOURCE_MAP.get(entity_type, ENTITY_SOURCE_MAP["UNKNOWN"])

            for source in sources:
                if source.wave.value <= max_waves:
                    all_sources[source.wave].append(source)

        # Deduplicate sources (same table+column+match_type)
        def dedupe_sources(sources: List[SearchSource]) -> List[SearchSource]:
            seen = set()
            unique = []
            for s in sources:
                key = (s.table, s.column, s.match_type)
                if key not in seen:
                    seen.add(key)
                    unique.append(s)
            return sorted(unique, key=lambda x: x.priority)

        plan.wave_0_sources = dedupe_sources(all_sources[Wave.WAVE_0])
        plan.wave_1_sources = dedupe_sources(all_sources[Wave.WAVE_1])
        plan.wave_2_sources = dedupe_sources(all_sources[Wave.WAVE_2])
        plan.wave_3_sources = dedupe_sources(all_sources[Wave.WAVE_3])

        return plan

    def execute_plan(
        self,
        plan: SearchPlan,
        early_exit_threshold: int = 3,
    ) -> PlanExecutionResult:
        """
        Execute a search plan, respecting wave budgets.

        Args:
            plan: SearchPlan to execute
            early_exit_threshold: Stop early if this many high-confidence results found

        Returns:
            PlanExecutionResult with all results
        """
        start_time = time.time()
        all_results: List[SearchResult] = []
        waves_executed: List[Wave] = []
        early_exit = False
        early_exit_reason = None

        # Get search values from entities
        search_values = {e["type"]: e["value"] for e in plan.entities}
        default_value = plan.entities[0]["value"] if plan.entities else ""

        # Execute Wave 0
        if plan.wave_0_sources:
            wave_results = self._execute_wave(
                plan.wave_0_sources,
                search_values,
                default_value,
                WAVE_BUDGETS_MS[Wave.WAVE_0],
            )
            all_results.extend(wave_results)
            waves_executed.append(Wave.WAVE_0)

            # Check for early exit (exact match found)
            exact_matches = sum(1 for r in wave_results if r.row_count > 0)
            if exact_matches >= early_exit_threshold:
                early_exit = True
                early_exit_reason = f"Wave 0: {exact_matches} exact matches found"

        # Execute Wave 1 if budget allows and no early exit
        elapsed_ms = (time.time() - start_time) * 1000
        if not early_exit and plan.wave_1_sources and elapsed_ms < WAVE_BUDGETS_MS[Wave.WAVE_1]:
            remaining_budget = WAVE_BUDGETS_MS[Wave.WAVE_1] - elapsed_ms
            wave_results = self._execute_wave(
                plan.wave_1_sources,
                search_values,
                default_value,
                remaining_budget,
            )
            all_results.extend(wave_results)
            waves_executed.append(Wave.WAVE_1)

            # Check for early exit
            total_rows = sum(r.row_count for r in all_results)
            if total_rows >= early_exit_threshold:
                early_exit = True
                early_exit_reason = f"Wave 1: {total_rows} results found"

        # Execute Wave 2 if budget allows and no early exit
        elapsed_ms = (time.time() - start_time) * 1000
        if not early_exit and plan.wave_2_sources and elapsed_ms < WAVE_BUDGETS_MS[Wave.WAVE_2]:
            remaining_budget = WAVE_BUDGETS_MS[Wave.WAVE_2] - elapsed_ms
            wave_results = self._execute_wave(
                plan.wave_2_sources,
                search_values,
                default_value,
                remaining_budget,
            )
            all_results.extend(wave_results)
            waves_executed.append(Wave.WAVE_2)

        # Note: Wave 3 (VECTOR) is async - not implemented in sync path
        # Would need separate async execution with streaming results

        total_time_ms = (time.time() - start_time) * 1000
        total_rows = sum(r.row_count for r in all_results)

        # Deduplicate rows across sources
        unique_ids = set()
        unique_rows = 0
        for result in all_results:
            for row in result.rows:
                row_id = row.get("id")
                if row_id and row_id not in unique_ids:
                    unique_ids.add(row_id)
                    unique_rows += 1
                elif not row_id:
                    unique_rows += 1  # Can't dedupe without ID

        return PlanExecutionResult(
            plan=plan,
            results=all_results,
            total_rows=total_rows,
            unique_rows=unique_rows,
            waves_executed=waves_executed,
            total_time_ms=total_time_ms,
            early_exit=early_exit,
            early_exit_reason=early_exit_reason,
        )

    def _execute_wave(
        self,
        sources: List[SearchSource],
        search_values: Dict[str, str],
        default_value: str,
        budget_ms: float,
    ) -> List[SearchResult]:
        """Execute all sources in a wave, respecting budget."""
        results: List[SearchResult] = []

        # Execute sources in parallel
        with ThreadPoolExecutor(max_workers=min(len(sources), 4)) as executor:
            futures = {}
            for source in sources:
                # Get search value for this source's entity type
                search_value = default_value
                for entity_type, value in search_values.items():
                    if entity_type in ENTITY_SOURCE_MAP:
                        # Check if this source is associated with this entity type
                        for s in ENTITY_SOURCE_MAP[entity_type]:
                            if s.table == source.table and s.column == source.column:
                                search_value = value
                                break

                future = executor.submit(
                    self._execute_source,
                    source,
                    search_value,
                )
                futures[future] = source

            # Collect results with timeout
            deadline = time.time() + (budget_ms / 1000)
            try:
                for future in as_completed(futures, timeout=max(budget_ms / 1000, 5)):
                    if time.time() > deadline:
                        break
                    try:
                        result = future.result(timeout=1)
                        results.append(result)
                    except Exception as e:
                        source = futures[future]
                        results.append(SearchResult(
                            source=source,
                            rows=[],
                            row_count=0,
                            execution_time_ms=0,
                            match_type_used=source.match_type,
                            error=str(e),
                        ))
            except TimeoutError:
                # Some futures didn't complete in time - that's OK
                pass

        return results

    def _execute_source(
        self,
        source: SearchSource,
        search_value: str,
    ) -> SearchResult:
        """Execute a single source query."""
        start_time = time.time()

        try:
            query = self.client.table(source.table).select("*")

            # ALWAYS filter by yacht_id first
            query = query.eq("yacht_id", self.yacht_id)

            # Apply match type
            if source.match_type == MatchType.EXACT:
                query = query.eq(source.column, search_value)
            elif source.match_type == MatchType.ILIKE:
                query = query.ilike(source.column, f"%{search_value}%")
            elif source.match_type == MatchType.TRIGRAM:
                # Supabase client doesn't support trigram directly
                # Fall back to ilike
                query = query.ilike(source.column, f"%{search_value}%")
            elif source.match_type == MatchType.CONTAINS:
                # For array columns
                query = query.contains(source.column, [search_value])
            elif source.match_type == MatchType.VECTOR:
                # Vector search not implemented in sync path
                # Would need RPC call to vector similarity function
                return SearchResult(
                    source=source,
                    rows=[],
                    row_count=0,
                    execution_time_ms=(time.time() - start_time) * 1000,
                    match_type_used=source.match_type,
                    error="VECTOR search not implemented in sync path",
                )

            # Apply limit
            query = query.limit(source.limit)

            # Execute
            response = query.execute()
            rows = response.data or []

            return SearchResult(
                source=source,
                rows=rows,
                row_count=len(rows),
                execution_time_ms=(time.time() - start_time) * 1000,
                match_type_used=source.match_type,
            )

        except Exception as e:
            return SearchResult(
                source=source,
                rows=[],
                row_count=0,
                execution_time_ms=(time.time() - start_time) * 1000,
                match_type_used=source.match_type,
                error=str(e),
            )


# =============================================================================
# CONFIDENCE SCORING
# =============================================================================

def calculate_confidence(
    result: SearchResult,
    search_value: str,
) -> List[float]:
    """Calculate confidence scores for each row in a result."""
    scores = []

    for row in result.rows:
        score = 0.0

        # Base score from match type
        if result.match_type_used == MatchType.EXACT:
            score += 50
        elif result.match_type_used == MatchType.ILIKE:
            if len(search_value) <= 5:
                score += 30
            else:
                score += 20
        elif result.match_type_used == MatchType.TRIGRAM:
            score += 15
        elif result.match_type_used == MatchType.VECTOR:
            # Would need similarity score from vector search
            score += 25

        # Bonus for exact column match
        col_value = str(row.get(result.source.column, "")).lower()
        if col_value == search_value.lower():
            score += 20

        scores.append(min(score, 100))  # Cap at 100

    return scores


# =============================================================================
# CLI TESTING
# =============================================================================

if __name__ == "__main__":
    import sys
    import os
    import json

    print("=" * 60)
    print("SEARCH PLANNER TEST")
    print("=" * 60)

    try:
        from supabase import create_client
    except ImportError:
        print("ERROR: supabase not installed")
        sys.exit(1)

    SUPABASE_URL = "https://vzsohavtuotocgrfkfyd.supabase.co"
    SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")
    TEST_YACHT_ID = "85fe1119-b04c-41ac-80f1-829d23322598"

    client = create_client(SUPABASE_URL, SUPABASE_KEY)
    planner = SearchPlanner(client, TEST_YACHT_ID)

    # Test cases
    test_cases = [
        [{"type": "PART_NUMBER", "value": "ENG-0008-103"}],
        [{"type": "PART_NAME", "value": "fuel filter"}],
        [{"type": "FAULT_CODE", "value": "1234"}],
        [{"type": "SYSTEM_NAME", "value": "fuel system"}],
        [{"type": "DOCUMENT_QUERY", "value": "maintenance schedule"}],
        [{"type": "FREE_TEXT", "value": "engine"}],
    ]

    for entities in test_cases:
        print(f"\n--- Testing: {entities[0]['type']} = '{entities[0]['value']}' ---")

        plan = planner.create_plan(entities)
        print(f"Wave 0 sources: {len(plan.wave_0_sources)}")
        print(f"Wave 1 sources: {len(plan.wave_1_sources)}")
        print(f"Wave 2 sources: {len(plan.wave_2_sources)}")

        result = planner.execute_plan(plan)
        print(f"Total time: {result.total_time_ms:.1f}ms")
        print(f"Waves executed: {[w.name for w in result.waves_executed]}")
        print(f"Total rows: {result.total_rows}")
        print(f"Unique rows: {result.unique_rows}")
        if result.early_exit:
            print(f"Early exit: {result.early_exit_reason}")

        # Show results by source
        for sr in result.results:
            if sr.row_count > 0:
                print(f"  {sr.source.table}.{sr.source.column} ({sr.source.match_type.value}): {sr.row_count} rows")
