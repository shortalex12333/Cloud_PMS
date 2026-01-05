"""
SQL Execution Layer - Consumes PREPARE output, generates and executes SQL

This module:
1. Takes SearchPlan from PREPARE
2. Generates parameterized SQL based on table capabilities
3. Executes via Supabase REST API (fallback) or RPC (preferred)
4. Returns ranked, scored results
"""

import os
import re
import json
import time
import uuid
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple, Set
from enum import Enum

import httpx

# Import from column_config
from .column_config import (
    TABLES,
    TableCapability,
    ColumnCapability,
    Operator,
    get_columns_for_entity,
    get_table
)

# Import canonical normalization
from .canonical import canonical, canonical_ilike_pattern

# Import canonical trace classes from contracts
try:
    from contracts import (
        WaveType, WaveTrace, ExecutionTrace, ExecutionStrategy,
        Lane, LaneReason
    )
    HAS_CONTRACTS = True
except ImportError:
    # Fallback if contracts not available
    HAS_CONTRACTS = False

# Import SQL Planner
try:
    from .sql_planner import (
        SQLPlanner, SQLPlan, Intent,
        Lane as PlannerLane,
        ExecutionTrace as PlannerTrace,
        SecurityTrace, WaveTrace as PlannerWaveTrace,
        validate_plan
    )
    HAS_PLANNER = True
except ImportError:
    HAS_PLANNER = False

logger = logging.getLogger(__name__)

# Environment
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://vzsohavtuotocgrfkfyd.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", os.environ.get("SUPABASE_KEY", ""))

# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class SQLClause:
    """A single WHERE clause component"""
    column: str
    operator: Operator
    value: str
    param_name: str
    priority: int = 0  # Lower = higher priority


@dataclass
class TableQuery:
    """Query for a single table"""
    table: str
    select_columns: List[str]
    where_clauses: List[SQLClause]
    yacht_id: str
    limit: int = 50
    operator_mode: str = "OR"  # OR within entity, AND across entities


@dataclass
class SQLResult:
    """Result from a single SQL execution"""
    table: str
    rows: List[Dict]
    query_time_ms: float
    wave: str  # EXACT, ILIKE, TRIGRAM
    error: Optional[str] = None


@dataclass
class RankedRow:
    """A result row with scoring"""
    data: Dict
    source_table: str
    score: float
    score_components: Dict[str, float]
    match_type: str  # EXACT, ILIKE, TRIGRAM
    matched_columns: List[str]


# =============================================================================
# SQL GENERATION - Wave-based
# =============================================================================

class SQLGenerator:
    """
    Generates SQL queries based on PREPARE output.

    Waves:
    - Wave 0: EXACT matches only (highest priority)
    - Wave 1: ILIKE contains/prefix
    - Wave 2: TRIGRAM similarity
    """

    WAVE_OPERATORS = {
        "EXACT": [Operator.EXACT],
        "ILIKE": [Operator.ILIKE],
        "TRIGRAM": [Operator.TRIGRAM],
    }

    def __init__(self, yacht_id: str):
        self.yacht_id = yacht_id
        self.param_counter = 0

    def _next_param(self) -> str:
        """Generate unique parameter name"""
        self.param_counter += 1
        return f"p{self.param_counter}"

    def generate_for_table(
        self,
        table_name: str,
        terms: List[Dict],  # [{"type": "PART_NUMBER", "value": "ENG-0008-103", "variants": [...]}]
        wave: str
    ) -> Optional[Tuple[str, Dict[str, Any], List[str]]]:
        """
        Generate SQL for a single table in a specific wave.

        Returns: (sql_query, params_dict, matched_columns) or None if no query possible
        """
        table_cfg = get_table(table_name)
        if not table_cfg:
            return None

        wave_ops = self.WAVE_OPERATORS.get(wave, [])
        if not wave_ops:
            return None

        # Build WHERE clauses
        where_parts = []
        params = {}
        matched_columns = []

        # yacht_id is always first
        params["yacht_id"] = self.yacht_id

        # Process each term
        entity_clauses = []
        for term in terms:
            entity_type = term.get("type", "")
            value = term.get("value", "")

            # Skip empty, whitespace-only, or too-short values
            # Also strip null chars and other control characters
            if value:
                value = ''.join(c for c in value if ord(c) >= 32 or c in '\t\n\r')
                value = value.strip()

            if not value or len(value) < 2:
                continue

            # Find columns that support this entity type
            col_clauses = []
            for col_name, col_cfg in table_cfg.columns.items():
                if entity_type not in col_cfg.entity_types:
                    continue

                # Check if column supports this wave's operator
                for op in wave_ops:
                    if op not in col_cfg.operators:
                        continue

                    param_name = self._next_param()
                    clause, param_value = self._make_clause(col_name, op, value, param_name)
                    if clause:
                        col_clauses.append(clause)
                        params[param_name] = param_value
                        matched_columns.append(col_name)

            if col_clauses:
                # OR within entity type (e.g., name OR description matches "filter")
                entity_clauses.append(f"({' OR '.join(col_clauses)})")

        if not entity_clauses:
            return None

        # AND across entity types
        where_sql = " AND ".join(entity_clauses)

        # Build full query
        select_cols = table_cfg.default_select
        limit = table_cfg.default_limit

        sql = f"""
SELECT {', '.join(select_cols)}, '{table_name}' as _source_table, '{wave}' as _match_type
FROM {table_name}
WHERE yacht_id = :yacht_id AND ({where_sql})
LIMIT {limit}
"""

        return sql.strip(), params, list(set(matched_columns))

    def _make_clause(
        self,
        column: str,
        operator: Operator,
        value: str,
        param_name: str
    ) -> Tuple[Optional[str], Any]:
        """
        Generate a single WHERE clause.
        Returns (sql_clause, param_value)
        """
        if operator == Operator.EXACT:
            return f"{column} = :{param_name}", value

        elif operator == Operator.ILIKE:
            return f"{column} ILIKE :{param_name}", f"%{value}%"

        elif operator == Operator.TRIGRAM:
            # Trigram similarity - requires pg_trgm extension
            return f"similarity({column}, :{param_name}) > 0.3", value

        elif operator == Operator.ARRAY_ANY_ILIKE:
            # For array columns (symptoms, causes)
            return f"EXISTS (SELECT 1 FROM unnest({column}) AS elem WHERE elem ILIKE :{param_name})", f"%{value}%"

        elif operator == Operator.JSONB_PATH_ILIKE:
            # For JSONB columns
            return f"{column}::text ILIKE :{param_name}", f"%{value}%"

        return None, None


# =============================================================================
# SQL EXECUTOR
# =============================================================================

class SQLExecutor:
    """
    Executes SQL against Supabase.

    Strategy:
    1. Try RPC (search_union) for batched execution
    2. Fall back to REST API per-table
    3. Use TRIGRAM RPCs for fuzzy matching (PostgREST can't do similarity())
    """

    # TRIGRAM RPC mapping: table -> RPC function name
    TRIGRAM_RPCS = {
        "pms_parts": "search_parts_fuzzy",
        "pms_equipment": "search_equipment_fuzzy",
        "symptom_aliases": "search_symptoms_fuzzy",
    }

    def __init__(self, supabase_url: str = None, supabase_key: str = None):
        self.url = supabase_url or SUPABASE_URL
        self.key = supabase_key or SUPABASE_KEY
        self.client = httpx.Client(timeout=30.0)

    def execute_trigram_via_rpc(
        self,
        table: str,
        terms: List[Dict],
        yacht_id: str,
        threshold: float = 0.15  # Lower threshold for typos
    ) -> SQLResult:
        """
        Execute TRIGRAM search via RPC function.

        Uses unified_trigram_search for cross-table or table-specific RPCs.
        """
        start = time.time()

        # Get search term (combine canonical values from terms)
        # Canonical normalization ensures "4 c" and "4c" match
        search_parts = []
        for t in terms:
            value = t.get("value", "")
            if value:
                entity_type = t.get("type", "")
                search_parts.append(canonical(value, entity_type))
        search_term = " ".join(search_parts)

        if not search_term or len(search_term) < 2:
            return SQLResult(
                table=table,
                rows=[],
                query_time_ms=0,
                wave="TRIGRAM",
                error="No valid search term"
            )

        try:
            # Use table-specific RPC if available, otherwise unified
            rpc_name = self.TRIGRAM_RPCS.get(table, "unified_trigram_search")

            url = f"{self.url}/rest/v1/rpc/{rpc_name}"
            headers = {
                "apikey": self.key,
                "Authorization": f"Bearer {self.key}",
                "Content-Type": "application/json",
            }

            payload = {
                "p_yacht_id": yacht_id,
                "p_search_term": search_term,
                "p_threshold": threshold,
                "p_limit": 20,
            }

            resp = self.client.post(url, json=payload, headers=headers)
            elapsed = (time.time() - start) * 1000

            if resp.status_code != 200:
                return SQLResult(
                    table=table,
                    rows=[],
                    query_time_ms=elapsed,
                    wave="TRIGRAM",
                    error=f"RPC error {resp.status_code}: {resp.text[:200]}"
                )

            rows = resp.json()

            # Normalize row format
            for row in rows:
                # unified_trigram_search returns source_table
                if "source_table" in row:
                    row["_source_table"] = row.pop("source_table")
                else:
                    row["_source_table"] = table
                row["_match_type"] = "TRIGRAM"
                # Rename similarity_score to _similarity
                if "similarity_score" in row:
                    row["_similarity"] = row.pop("similarity_score")

            return SQLResult(
                table=table,
                rows=rows,
                query_time_ms=elapsed,
                wave="TRIGRAM"
            )

        except Exception as e:
            elapsed = (time.time() - start) * 1000
            return SQLResult(
                table=table,
                rows=[],
                query_time_ms=elapsed,
                wave="TRIGRAM",
                error=str(e)
            )

    def execute_via_rest(
        self,
        table: str,
        terms: List[Dict],
        wave: str,
        yacht_id: str
    ) -> SQLResult:
        """
        Execute query via REST API.

        This translates our SQL structure to PostgREST query params.
        """
        start = time.time()

        table_cfg = get_table(table)
        if not table_cfg:
            return SQLResult(
                table=table,
                rows=[],
                query_time_ms=0,
                wave=wave,
                error=f"Unknown table: {table}"
            )

        # Build PostgREST query params
        params = {
            "yacht_id": f"eq.{yacht_id}",
            "limit": str(table_cfg.default_limit),
            "select": ",".join(table_cfg.default_select)
        }

        # Build OR conditions
        or_conditions = []

        for term in terms:
            entity_type = term.get("type", "")
            value = term.get("value", "")

            # Skip empty, whitespace-only, or too-short values
            # Also strip null chars and other control characters
            if value:
                value = ''.join(c for c in value if ord(c) >= 32 or c in '\t\n\r')
                value = value.strip()

            if not value or len(value) < 2:
                continue

            # Apply canonical normalization
            # This maps "4 c" → "4c", "ENG-0001" → "eng0001", etc.
            canonical_value = canonical(value, entity_type)

            for col_name, col_cfg in table_cfg.columns.items():
                if entity_type not in col_cfg.entity_types:
                    continue

                if wave == "EXACT" and Operator.EXACT in col_cfg.operators:
                    # Try both canonical and original for exact match
                    or_conditions.append(f"{col_name}.eq.{canonical_value}")
                    if canonical_value != value.lower():
                        or_conditions.append(f"{col_name}.eq.{value}")
                elif wave == "ILIKE" and Operator.ILIKE in col_cfg.operators:
                    # Use canonical ILIKE pattern for fuzzy matching
                    # Pattern matches variants: "4c" matches "4-c", "4 c", etc.
                    ilike_pattern = canonical_ilike_pattern(value, entity_type)
                    or_conditions.append(f"{col_name}.ilike.{ilike_pattern}")

        if not or_conditions:
            # TRIGRAM requires pg_trgm similarity() which PostgREST doesn't support
            # Skip silently for TRIGRAM wave - only report error for EXACT/ILIKE
            if wave == "TRIGRAM":
                return SQLResult(
                    table=table,
                    rows=[],
                    query_time_ms=0,
                    wave=wave,
                    error=None  # Silent skip - TRIGRAM requires RPC
                )
            return SQLResult(
                table=table,
                rows=[],
                query_time_ms=0,
                wave=wave,
                error="No matching columns for wave"
            )

        # Combine with OR
        if len(or_conditions) > 1:
            params["or"] = f"({','.join(or_conditions)})"
        else:
            # Parse single condition and add directly
            cond = or_conditions[0]
            col, op_val = cond.split(".", 1)
            if op_val.startswith("eq."):
                params[col] = f"eq.{op_val[3:]}"
            elif op_val.startswith("ilike."):
                params[col] = f"ilike.{op_val[6:]}"

        try:
            url = f"{self.url}/rest/v1/{table}"
            headers = {
                "apikey": self.key,
                "Authorization": f"Bearer {self.key}",
            }

            resp = self.client.get(url, params=params, headers=headers)
            elapsed = (time.time() - start) * 1000

            if resp.status_code != 200:
                return SQLResult(
                    table=table,
                    rows=[],
                    query_time_ms=elapsed,
                    wave=wave,
                    error=f"HTTP {resp.status_code}: {resp.text[:200]}"
                )

            rows = resp.json()
            # Add metadata
            for row in rows:
                row["_source_table"] = table
                row["_match_type"] = wave

            return SQLResult(
                table=table,
                rows=rows,
                query_time_ms=elapsed,
                wave=wave
            )

        except Exception as e:
            elapsed = (time.time() - start) * 1000
            return SQLResult(
                table=table,
                rows=[],
                query_time_ms=elapsed,
                wave=wave,
                error=str(e)
            )

    def execute_wave(
        self,
        tables: List[str],
        terms: List[Dict],
        wave: str,
        yacht_id: str
    ) -> Tuple[List[SQLResult], float]:
        """
        Execute a wave across multiple tables.

        For TRIGRAM wave, uses RPC functions instead of REST API
        (PostgREST can't do similarity() queries).

        Returns: (results, wave_latency_ms)
        """
        wave_start = time.time()
        results = []

        if wave == "TRIGRAM":
            # Use unified TRIGRAM RPC for all tables at once
            result = self.execute_trigram_via_rpc("unified", terms, yacht_id)
            results.append(result)
        else:
            # Standard REST API for EXACT and ILIKE
            for table in tables:
                result = self.execute_via_rest(table, terms, wave, yacht_id)
                results.append(result)

        wave_latency = (time.time() - wave_start) * 1000
        return results, wave_latency


# =============================================================================
# RANKING ENGINE
# =============================================================================

class RankingEngine:
    """
    Ranks and scores results.

    Scoring signals:
    - match_type: EXACT > ILIKE > TRIGRAM
    - table_weight: based on entity type primacy
    - entity_confidence: from extraction
    - column_specificity: primary columns > secondary
    """

    MATCH_SCORES = {
        "EXACT": 3.0,
        "ILIKE": 1.5,
        "TRIGRAM": 0.5,
    }

    TABLE_WEIGHTS = {
        "pms_parts": 1.0,
        "pms_equipment": 1.2,
        "pms_faults": 1.1,
        "pms_suppliers": 0.6,
        "pms_work_orders": 0.9,
        "pms_purchase_orders": 0.7,
        "graph_nodes": 0.8,
        "symptom_aliases": 0.7,
    }

    def __init__(self, terms: List[Dict]):
        self.terms = terms
        self.term_values = {t["value"].lower() for t in terms if t.get("value")}

    def score_row(self, row: Dict) -> RankedRow:
        """Score a single result row"""
        source_table = row.get("_source_table", "unknown")
        match_type = row.get("_match_type", "ILIKE")

        components = {}

        # Match type score
        components["match_type"] = self.MATCH_SCORES.get(match_type, 1.0)

        # Table weight
        components["table_weight"] = self.TABLE_WEIGHTS.get(source_table, 0.8)

        # Value match bonus (check if any term value appears in row)
        value_bonus = 0.0
        matched_cols = []
        for key, val in row.items():
            if key.startswith("_"):
                continue
            if isinstance(val, str):
                val_lower = val.lower()
                for term_val in self.term_values:
                    if term_val in val_lower:
                        value_bonus += 0.5
                        matched_cols.append(key)
                        break
        components["value_match"] = min(value_bonus, 2.0)

        # Calculate total
        total = (
            components["match_type"] *
            components["table_weight"] *
            (1 + components["value_match"])
        )

        return RankedRow(
            data=row,
            source_table=source_table,
            score=total,
            score_components=components,
            match_type=match_type,
            matched_columns=list(set(matched_cols))
        )

    def rank_results(self, results: List[SQLResult]) -> List[RankedRow]:
        """Rank all results across tables with deduplication"""
        all_rows = []
        seen_ids = set()  # Track by (table, id) to dedupe

        for result in results:
            if result.error:
                continue
            for row in result.rows:
                # Deduplicate by table + id
                row_id = row.get("id", "")
                table = row.get("_source_table", "")
                key = f"{table}:{row_id}"

                if key in seen_ids:
                    continue
                seen_ids.add(key)

                ranked = self.score_row(row)
                all_rows.append(ranked)

        # Sort by score descending
        all_rows.sort(key=lambda r: r.score, reverse=True)

        return all_rows

    def diversify(self, rows: List[RankedRow], max_per_table: int = 10) -> List[RankedRow]:
        """Cap results per table to ensure diversity"""
        table_counts = {}
        diversified = []

        for row in rows:
            count = table_counts.get(row.source_table, 0)
            if count < max_per_table:
                diversified.append(row)
                table_counts[row.source_table] = count + 1

        return diversified


# =============================================================================
# MAIN EXECUTION PIPELINE
# =============================================================================

def execute_search(
    terms: List[Dict],
    tables: List[str],
    yacht_id: str,
    max_results: int = 50,
    early_exit_threshold: int = 20,
    include_vector: bool = False,
    query_text: str = "",
    embedding: Optional[List[float]] = None
) -> Dict[str, Any]:
    """
    Main execution pipeline.

    Waves:
    1. EXACT - try exact matches first
    2. ILIKE - if not enough, try fuzzy
    3. TRIGRAM - if still not enough, try similarity (requires RPC)
    4. VECTOR - semantic document search (GPT lane only)

    Early exit: stop if we have enough good results

    Args:
        terms: Entity terms to search for
        tables: Tables to search
        yacht_id: Yacht ID filter
        max_results: Maximum results to return
        early_exit_threshold: Stop early if we have this many results
        include_vector: Whether to include vector/semantic search (Wave 4)
        query_text: Original query text for vector search fallback
        embedding: Pre-computed 1536-dim embedding from extraction API
    """
    start_time = time.time()
    request_id = str(uuid.uuid4())[:8]

    executor = SQLExecutor()
    ranker = RankingEngine(terms)

    all_results = []
    waves_executed = []
    wave_traces = []  # Per-wave timing and results
    vector_results = None
    early_exit_triggered = False

    # Wave progression for structured data
    for wave in ["EXACT", "ILIKE", "TRIGRAM"]:
        wave_results, wave_latency = executor.execute_wave(tables, terms, wave, yacht_id)
        all_results.extend(wave_results)
        waves_executed.append(wave)

        # Build wave trace
        wave_rows = sum(len(r.rows) for r in wave_results if not r.error)
        wave_tables = [r.table for r in wave_results if not r.error and r.rows]
        wave_error = next((r.error for r in wave_results if r.error), None)

        wave_traces.append({
            "wave": wave,
            "tables_queried": wave_tables,
            "rows_returned": wave_rows,
            "latency_ms": round(wave_latency, 2),
            "error": wave_error
        })

        # Count total rows so far
        total_rows = sum(len(r.rows) for r in all_results if not r.error)

        # Early exit check
        if total_rows >= early_exit_threshold:
            early_exit_triggered = True
            break

    # Wave 4: Vector search (optional, for GPT lane)
    # Uses pre-computed embedding from extraction API
    if include_vector and (embedding or query_text):
        vector_start = time.time()
        try:
            from .vector_search import execute_vector_search
            vector_results = execute_vector_search(
                embedding=embedding,
                yacht_id=yacht_id,
                limit=10,
                query_text=query_text  # Fallback for text search if no embedding
            )
            vector_latency = (time.time() - vector_start) * 1000
            waves_executed.append("VECTOR")

            wave_traces.append({
                "wave": "VECTOR",
                "tables_queried": ["search_document_chunks"],
                "rows_returned": len(vector_results.get("results", [])),
                "latency_ms": round(vector_latency, 2),
                "error": vector_results.get("error")
            })
        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            vector_latency = (time.time() - vector_start) * 1000
            vector_results = {"results": [], "error": str(e)}
            wave_traces.append({
                "wave": "VECTOR",
                "tables_queried": [],
                "rows_returned": 0,
                "latency_ms": round(vector_latency, 2),
                "error": str(e)
            })

    # Rank all results
    ranked = ranker.rank_results(all_results)

    # Diversify
    diversified = ranker.diversify(ranked, max_per_table=10)

    # Limit to max_results
    final = diversified[:max_results]

    elapsed = (time.time() - start_time) * 1000

    # Build trace with per-wave latency breakdown
    trace = {
        "request_id": request_id,
        "waves_executed": waves_executed,
        "wave_traces": wave_traces,  # Per-wave latency breakdown
        "tables_hit": list(set(r.source_table for r in final)),
        "total_rows_before_ranking": sum(len(r.rows) for r in all_results if not r.error),
        "final_count": len(final),
        "early_exit": early_exit_triggered,
        "total_latency_ms": round(elapsed, 2),
        "latency_breakdown": {
            wave["wave"]: wave["latency_ms"]
            for wave in wave_traces
        },
        "errors": [
            {"table": r.table, "wave": r.wave, "error": r.error}
            for r in all_results if r.error
        ],
        "vector_search": {
            "enabled": include_vector,
            "method": vector_results.get("method") if vector_results else None,
            "document_count": len(vector_results.get("results", [])) if vector_results else 0,
            "error": vector_results.get("error") if vector_results else None
        } if include_vector else None
    }

    # Build final results
    results = [
        {
            **r.data,
            "_score": r.score,
            "_score_components": r.score_components,
            "_match_type": r.match_type,
            "_matched_columns": r.matched_columns
        }
        for r in final
    ]

    # Append vector/document results if any
    if vector_results and vector_results.get("results"):
        for vr in vector_results["results"][:5]:  # Limit document results
            results.append({
                "id": vr.chunk_id,
                "content": vr.content[:200] + "..." if len(vr.content) > 200 else vr.content,
                "metadata": vr.metadata,
                "_source_table": "search_document_chunks",
                "_match_type": "VECTOR",
                "_score": vr.similarity,
                "_score_components": {"vector_similarity": vr.similarity}
            })

    return {
        "results": results,
        "trace": trace
    }


# =============================================================================
# PLAN-DRIVEN EXECUTION (uses SQLPlanner)
# =============================================================================

def execute_with_plan(
    plan: 'SQLPlan',
    embedding: Optional[List[float]] = None
) -> Dict[str, Any]:
    """
    Execute using a SQLPlan from the planner.

    This is the NEW recommended entry point that:
    1. Uses deterministic rules from sql_planner.py
    2. Respects lane capabilities
    3. Emits structured trace with security telemetry
    """
    if not HAS_PLANNER:
        raise ImportError("sql_planner module not available")

    start_time = time.time()

    # Validate plan
    violations = validate_plan(plan)
    if violations:
        return {
            "results": [],
            "trace": {
                "request_id": plan.request_id,
                "error": "Plan validation failed",
                "violations": violations,
            }
        }

    executor = SQLExecutor()
    ranker = RankingEngine(plan.entities)

    all_results = []
    wave_traces = []
    early_exit_triggered = False

    # Execute waves in order
    wave_map = {0: "EXACT", 1: "ILIKE", 2: "TRIGRAM", 3: "VECTOR"}

    for wave_num in plan.waves:
        wave_name = wave_map.get(wave_num, f"WAVE_{wave_num}")
        wave_start = time.time()

        if wave_num == 3 and plan.vector_enabled:
            # Vector wave
            try:
                from .vector_search import execute_vector_search
                vector_result = execute_vector_search(
                    embedding=embedding,
                    yacht_id=plan.security["yacht_id"],
                    limit=10,
                    query_text=" ".join(e.get("value", "") for e in plan.entities)
                )
                wave_latency = (time.time() - wave_start) * 1000
                wave_rows = len(vector_result.get("results", []))

                wave_traces.append({
                    "wave": wave_name,
                    "tables_queried": ["search_document_chunks"],
                    "rows_returned": wave_rows,
                    "latency_ms": round(wave_latency, 2),
                    "error": vector_result.get("error"),
                })

                # Store vector results for later merging
                if vector_result.get("results"):
                    all_results.append(SQLResult(
                        table="search_document_chunks",
                        rows=[{
                            "id": vr.chunk_id,
                            "content": vr.content,
                            "_source_table": "search_document_chunks",
                            "_match_type": "VECTOR",
                        } for vr in vector_result["results"]],
                        query_time_ms=wave_latency,
                        wave=wave_name,
                    ))
            except Exception as e:
                wave_traces.append({
                    "wave": wave_name,
                    "tables_queried": [],
                    "rows_returned": 0,
                    "latency_ms": round((time.time() - wave_start) * 1000, 2),
                    "error": str(e),
                })
        else:
            # SQL wave
            terms = [{"type": e.get("type"), "value": e.get("value")} for e in plan.entities]
            wave_results, wave_latency = executor.execute_wave(
                plan.tables, terms, wave_name, plan.security["yacht_id"]
            )
            all_results.extend(wave_results)

            wave_rows = sum(len(r.rows) for r in wave_results if not r.error)
            wave_tables = [r.table for r in wave_results if not r.error and r.rows]
            wave_error = next((r.error for r in wave_results if r.error), None)

            wave_traces.append({
                "wave": wave_name,
                "tables_queried": wave_tables,
                "rows_returned": wave_rows,
                "latency_ms": round(wave_latency, 2),
                "error": wave_error,
            })

        # Early exit check
        total_rows = sum(len(r.rows) for r in all_results if not r.error)
        if total_rows >= plan.stop_conditions["early_exit_threshold"]:
            early_exit_triggered = True
            break

    # Rank results
    ranked = ranker.rank_results(all_results)
    diversified = ranker.diversify(ranked, max_per_table=plan.ranking.max_per_table)
    final = diversified[:plan.constraints.max_total_rows]

    elapsed = (time.time() - start_time) * 1000

    # Build trace
    trace = {
        "request_id": plan.request_id,
        "lane": plan.lane.value,
        "intent": plan.intent.value,
        "waves_executed": [wave_map.get(w, f"WAVE_{w}") for w in plan.waves],
        "wave_traces": wave_traces,
        "tables_hit": list(set(r.source_table for r in final)),
        "total_latency_ms": round(elapsed, 2),
        "result_count": len(final),
        "early_exit": early_exit_triggered,
        "stop_reason": "threshold" if early_exit_triggered else "complete",
        "security": {
            "yacht_id_enforced": plan.security["yacht_id_enforced"],
            "parameterized": plan.security["parameterized"],
        },
    }

    # Build results
    results = [
        {
            **r.data,
            "_score": r.score,
            "_match_type": r.match_type,
        }
        for r in final
    ]

    return {
        "results": results,
        "trace": trace,
        "plan": plan.to_dict(),
    }


# =============================================================================
# STREAMING / FAST-FIRST EXECUTION
# =============================================================================

from typing import Generator, Iterator

@dataclass
class StreamChunk:
    """A chunk of streaming results"""
    wave: str
    results: List[Dict]
    is_final: bool
    cumulative_count: int
    latency_ms: float
    trace: Optional[Dict] = None


def execute_search_streaming(
    terms: List[Dict],
    tables: List[str],
    yacht_id: str,
    max_results: int = 50,
    early_exit_threshold: int = 20,
    include_vector: bool = False,
    query_text: str = "",
    embedding: Optional[List[float]] = None
) -> Generator[StreamChunk, None, None]:
    """
    Streaming execution pipeline - yields results wave-by-wave.

    This enables fast-first response patterns:
    - Client gets EXACT matches immediately
    - Then ILIKE fuzzy matches
    - Then TRIGRAM similarity
    - Finally VECTOR semantic matches

    Each yield contains:
    - wave: which wave produced these results
    - results: ranked results from this wave
    - is_final: whether this is the last chunk
    - cumulative_count: total results so far
    - latency_ms: time to get this wave
    - trace: full trace (only on final chunk)

    Usage:
        for chunk in execute_search_streaming(...):
            yield f"data: {json.dumps(chunk.__dict__)}\\n\\n"  # SSE format
    """
    start_time = time.time()
    request_id = str(uuid.uuid4())[:8]

    executor = SQLExecutor()
    ranker = RankingEngine(terms)

    all_results = []
    waves_executed = []
    wave_traces = []
    cumulative_ranked = []
    seen_ids = set()

    waves = ["EXACT", "ILIKE", "TRIGRAM"]
    if include_vector:
        waves.append("VECTOR")

    for i, wave in enumerate(waves):
        wave_start = time.time()

        if wave == "VECTOR" and (embedding or query_text):
            # Vector search
            try:
                from .vector_search import execute_vector_search
                vector_result = execute_vector_search(
                    embedding=embedding,
                    yacht_id=yacht_id,
                    limit=10,
                    query_text=query_text
                )
                wave_latency = (time.time() - wave_start) * 1000
                wave_rows = vector_result.get("results", [])

                # Convert vector results to dict format
                new_results = []
                for vr in wave_rows[:5]:
                    new_results.append({
                        "id": vr.chunk_id,
                        "content": vr.content[:200] + "..." if len(vr.content) > 200 else vr.content,
                        "metadata": vr.metadata,
                        "_source_table": "search_document_chunks",
                        "_match_type": "VECTOR",
                        "_score": vr.similarity,
                    })

                wave_traces.append({
                    "wave": wave,
                    "tables_queried": ["search_document_chunks"],
                    "rows_returned": len(wave_rows),
                    "latency_ms": round(wave_latency, 2),
                    "error": vector_result.get("error")
                })

            except Exception as e:
                wave_latency = (time.time() - wave_start) * 1000
                new_results = []
                wave_traces.append({
                    "wave": wave,
                    "tables_queried": [],
                    "rows_returned": 0,
                    "latency_ms": round(wave_latency, 2),
                    "error": str(e)
                })
        else:
            # Standard SQL wave
            wave_results, wave_latency = executor.execute_wave(tables, terms, wave, yacht_id)
            all_results.extend(wave_results)

            wave_rows = sum(len(r.rows) for r in wave_results if not r.error)
            wave_tables = [r.table for r in wave_results if not r.error and r.rows]
            wave_error = next((r.error for r in wave_results if r.error), None)

            wave_traces.append({
                "wave": wave,
                "tables_queried": wave_tables,
                "rows_returned": wave_rows,
                "latency_ms": round(wave_latency, 2),
                "error": wave_error
            })

            # Rank this wave's results
            wave_ranked = ranker.rank_results(wave_results)

            # Dedupe against previous waves
            new_results = []
            for r in wave_ranked:
                row_id = r.data.get("id", "")
                table = r.data.get("_source_table", "")
                key = f"{table}:{row_id}"
                if key not in seen_ids:
                    seen_ids.add(key)
                    new_results.append({
                        **r.data,
                        "_score": r.score,
                        "_score_components": r.score_components,
                        "_match_type": r.match_type,
                        "_matched_columns": r.matched_columns
                    })

        cumulative_ranked.extend(new_results)
        waves_executed.append(wave)

        # Determine if this is the final chunk
        total_so_far = len(cumulative_ranked)
        is_last_wave = (i == len(waves) - 1)
        early_exit = total_so_far >= early_exit_threshold and not is_last_wave

        is_final = is_last_wave or early_exit

        # Build trace only for final chunk
        trace = None
        if is_final:
            elapsed = (time.time() - start_time) * 1000
            trace = {
                "request_id": request_id,
                "waves_executed": waves_executed,
                "wave_traces": wave_traces,
                "total_latency_ms": round(elapsed, 2),
                "early_exit": early_exit,
                "final_count": min(len(cumulative_ranked), max_results)
            }

        # Yield this wave's chunk
        yield StreamChunk(
            wave=wave,
            results=new_results[:max_results - (total_so_far - len(new_results))] if new_results else [],
            is_final=is_final,
            cumulative_count=min(total_so_far, max_results),
            latency_ms=round(wave_latency, 2),
            trace=trace
        )

        if early_exit:
            break


def execute_search_fast_first(
    terms: List[Dict],
    tables: List[str],
    yacht_id: str,
    max_results: int = 50,
    first_wave_only: bool = False
) -> Dict[str, Any]:
    """
    Fast-first execution - returns immediately after first wave with results.

    This is optimized for latency-critical requests:
    - Only runs EXACT wave
    - Returns in <50ms typically
    - Client can request more via follow-up if needed

    Args:
        first_wave_only: If True, only run EXACT wave and return immediately
    """
    start_time = time.time()
    request_id = str(uuid.uuid4())[:8]

    executor = SQLExecutor()
    ranker = RankingEngine(terms)

    # Just run EXACT wave
    wave_results, wave_latency = executor.execute_wave(tables, terms, "EXACT", yacht_id)

    wave_rows = sum(len(r.rows) for r in wave_results if not r.error)

    if wave_rows > 0 or first_wave_only:
        # Return EXACT results immediately
        ranked = ranker.rank_results(wave_results)
        results = [
            {
                **r.data,
                "_score": r.score,
                "_match_type": r.match_type,
            }
            for r in ranked[:max_results]
        ]

        elapsed = (time.time() - start_time) * 1000
        return {
            "results": results,
            "trace": {
                "request_id": request_id,
                "waves_executed": ["EXACT"],
                "total_latency_ms": round(elapsed, 2),
                "partial": True,
                "more_available": True
            }
        }

    # No EXACT results, fall back to full search
    return execute_search(
        terms=terms,
        tables=tables,
        yacht_id=yacht_id,
        max_results=max_results
    )


# =============================================================================
# TEST HARNESS
# =============================================================================

def test_sql_execution():
    """Test the SQL execution layer with real queries"""
    yacht_id = "85fe1119-b04c-41ac-80f1-829d23322598"

    test_cases = [
        # Wave 0 - EXACT
        {
            "name": "Exact part number lookup",
            "terms": [{"type": "PART_NUMBER", "value": "ENG-0008-103"}],
            "tables": ["pms_parts"],
            "expected_wave": "EXACT",
        },
        {
            "name": "Exact fault code lookup",
            "terms": [{"type": "FAULT_CODE", "value": "E047"}],
            "tables": ["pms_faults"],
            "expected_wave": "EXACT",
        },
        # Wave 1 - ILIKE
        {
            "name": "Fuzzy equipment search",
            "terms": [{"type": "EQUIPMENT_NAME", "value": "generator"}],
            "tables": ["pms_equipment"],
            "expected_wave": "ILIKE",
        },
        {
            "name": "Part name search",
            "terms": [{"type": "PART_NAME", "value": "filter"}],
            "tables": ["pms_parts"],
            "expected_wave": "ILIKE",
        },
        # Multi-entity
        {
            "name": "Part + Manufacturer",
            "terms": [
                {"type": "PART_NAME", "value": "filter"},
                {"type": "MANUFACTURER", "value": "MTU"}
            ],
            "tables": ["pms_parts"],
            "expected_wave": "ILIKE",
        },
    ]

    print("=" * 60)
    print("SQL EXECUTION LAYER TESTS")
    print("=" * 60)

    for tc in test_cases:
        print(f"\n--- {tc['name']} ---")
        print(f"Terms: {tc['terms']}")
        print(f"Tables: {tc['tables']}")

        result = execute_search(
            terms=tc["terms"],
            tables=tc["tables"],
            yacht_id=yacht_id,
            max_results=10
        )

        print(f"Results: {len(result['results'])} rows")
        print(f"Waves: {result['trace']['waves_executed']}")
        print(f"Early exit: {result['trace']['early_exit']}")
        print(f"Time: {result['trace']['execution_time_ms']:.2f}ms")

        if result["trace"]["errors"]:
            print(f"ERRORS: {result['trace']['errors']}")

        if result["results"]:
            print("Top 3 results:")
            for r in result["results"][:3]:
                print(f"  - {r}")

        print()


if __name__ == "__main__":
    test_sql_execution()
