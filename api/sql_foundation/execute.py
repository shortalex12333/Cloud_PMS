"""
EXECUTE: Run prepared SQL against database
==========================================

Two execution strategies:

1. REST (PostgREST) - Multiple calls, merge client-side
   - Works now, no DB changes needed
   - One HTTP call per table
   - Merge and dedupe results

2. RPC (Postgres function) - Single call, DB-side UNION
   - Requires deploying RPC function
   - Single HTTP call
   - Better performance

This module implements Strategy 1 (REST).
For Strategy 2, deploy the RPC function in execute_rpc.sql
"""
import time
import requests
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

from .prepare import ExecutionPlan, ResolvedQuery, Operator
from .generate_sql import GeneratedSQL
from .column_config import TABLES


@dataclass
class ExecutionResult:
    """Result from executing a query."""
    rows: List[Dict]
    tables_queried: List[str]
    execution_time_ms: float
    wave: int
    early_exit: bool
    error: Optional[str] = None


@dataclass
class SearchResult:
    """Complete search result."""
    rows: List[Dict]
    total_rows: int
    tables_hit: List[str]
    waves_executed: int
    total_time_ms: float
    early_exit: bool
    trace: Dict[str, Any]


def execute_table_query(
    base_url: str,
    api_key: str,
    table: str,
    yacht_id: str,
    conditions: List[Dict],
    wave_op: Operator,
    limit: int = 20
) -> Tuple[List[Dict], float, Optional[str]]:
    """
    Execute single table query via PostgREST.

    Returns (rows, time_ms, error)
    """
    headers = {
        "apikey": api_key,
        "Authorization": f"Bearer {api_key}",
    }

    table_cfg = TABLES.get(table)
    if not table_cfg:
        return [], 0, f"Unknown table: {table}"

    select_cols = ",".join(table_cfg.default_select[:5])

    # Use params dict for proper URL encoding
    params = {
        "select": select_cols,
        "yacht_id": f"eq.{yacht_id}",
        "limit": limit
    }

    # Build conditions based on wave operator
    for cond in conditions:
        col = cond["column"]
        variants = cond["variants"]

        if wave_op == Operator.EXACT:
            # Find canonical variant for EXACT
            for variant in variants:
                if variant.operator == Operator.EXACT and variant.form == "canonical":
                    params[col] = f"eq.{variant.value}"
                    break

        elif wave_op == Operator.ILIKE:
            # Find the fuzzy variant (most inclusive: %value%)
            for variant in variants:
                if variant.operator == Operator.ILIKE and variant.form == "fuzzy":
                    # Convert % to * for PostgREST
                    value = variant.value.replace("%", "*")
                    params[col] = f"ilike.{value}"
                    break

        elif wave_op == Operator.TRIGRAM:
            # TRIGRAM not supported via REST
            return [], 0, "TRIGRAM requires RPC"

    url = f"{base_url}/rest/v1/{table}"

    start = time.time()
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=10)
        elapsed = (time.time() - start) * 1000

        if resp.status_code == 200:
            rows = resp.json()
            # Add source table to each row
            for row in rows:
                row["_source"] = table
            return rows, elapsed, None
        else:
            return [], elapsed, f"HTTP {resp.status_code}: {resp.text[:100]}"
    except Exception as e:
        return [], (time.time() - start) * 1000, str(e)


def execute_wave(
    base_url: str,
    api_key: str,
    plan: ExecutionPlan,
    wave_op: Operator,
    max_per_table: int = 20
) -> ExecutionResult:
    """
    Execute one wave across all tables in plan.

    Strategy: Parallel-ish (could use async, but sequential for now)
    """
    all_rows = []
    tables_queried = []
    total_time = 0
    errors = []

    for resolved in plan.resolved_queries:
        rows, time_ms, error = execute_table_query(
            base_url=base_url,
            api_key=api_key,
            table=resolved.table,
            yacht_id=plan.user_scope.yacht_ids[0],
            conditions=resolved.conditions,
            wave_op=wave_op,
            limit=max_per_table
        )

        total_time += time_ms
        tables_queried.append(resolved.table)

        if error:
            errors.append(f"{resolved.table}: {error}")
        else:
            all_rows.extend(rows)

    # Check early exit
    early_exit = len(all_rows) >= plan.exit_conditions.strong_hit_count

    return ExecutionResult(
        rows=all_rows,
        tables_queried=tables_queried,
        execution_time_ms=total_time,
        wave=wave_op.value,
        early_exit=early_exit,
        error="; ".join(errors) if errors else None
    )


def execute_search(
    base_url: str,
    api_key: str,
    plan: ExecutionPlan,
    max_waves: int = 2
) -> SearchResult:
    """
    Execute complete search using REST strategy.

    Executes waves in order (EXACT → ILIKE → TRIGRAM).
    Stops early if enough results found.
    """
    trace = {"waves": []}
    all_rows = []
    tables_hit = set()
    waves_executed = 0
    total_time = 0
    early_exit = False

    # Wave order from first batch
    if not plan.batches:
        return SearchResult(
            rows=[],
            total_rows=0,
            tables_hit=[],
            waves_executed=0,
            total_time_ms=0,
            early_exit=False,
            trace={"error": "No batches in plan"}
        )

    wave_order = plan.batches[0].wave_order[:max_waves]

    for wave_op in wave_order:
        # Skip TRIGRAM (not supported via REST)
        if wave_op == Operator.TRIGRAM:
            trace["waves"].append({"wave": wave_op.value, "skipped": "TRIGRAM requires RPC"})
            continue

        result = execute_wave(base_url, api_key, plan, wave_op)
        waves_executed += 1
        total_time += result.execution_time_ms

        trace["waves"].append({
            "wave": wave_op.value,
            "rows": len(result.rows),
            "tables": result.tables_queried,
            "time_ms": result.execution_time_ms,
            "error": result.error
        })

        all_rows.extend(result.rows)
        tables_hit.update(result.tables_queried)

        # Check early exit
        if result.early_exit:
            early_exit = True
            break

        # Check time budget
        if total_time >= plan.exit_conditions.max_time_ms:
            trace["budget_exceeded"] = True
            break

    # Deduplicate by id
    seen_ids = set()
    unique_rows = []
    for row in all_rows:
        row_id = row.get("id")
        if row_id and row_id not in seen_ids:
            seen_ids.add(row_id)
            unique_rows.append(row)

    return SearchResult(
        rows=unique_rows,
        total_rows=len(unique_rows),
        tables_hit=list(tables_hit),
        waves_executed=waves_executed,
        total_time_ms=total_time,
        early_exit=early_exit,
        trace=trace
    )


# =============================================================================
# CONVENIENCE: Full pipeline
# =============================================================================

def search(
    base_url: str,
    api_key: str,
    query: str,
    entities: List[Dict],
    yacht_id: str,
    user_id: str = "anonymous",
    user_role: str = "crew"
) -> SearchResult:
    """
    Complete search: PREPARE → EXECUTE.

    This is the main entry point.
    """
    from .prepare import prepare, Lane

    # Prepare
    plan = prepare(query, entities, yacht_id, user_id, user_role)

    # Check lane
    if plan.lane.lane == Lane.BLOCKED:
        return SearchResult(
            rows=[],
            total_rows=0,
            tables_hit=[],
            waves_executed=0,
            total_time_ms=0,
            early_exit=False,
            trace={"blocked": plan.lane.block_message}
        )

    if plan.lane.lane == Lane.UNKNOWN:
        return SearchResult(
            rows=[],
            total_rows=0,
            tables_hit=[],
            waves_executed=0,
            total_time_ms=0,
            early_exit=False,
            trace={"unknown": plan.lane.suggestions}
        )

    # Execute
    return execute_search(base_url, api_key, plan)
