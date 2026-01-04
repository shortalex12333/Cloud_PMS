"""
EXECUTE UNION: Proper UNION ALL batching execution
===================================================
Executes tier+wave batched SQL via:
1. RPC if search_union function exists
2. Raw SQL via postgrest-py if not
3. Falls back to REST per-table if all else fails
"""
import os
import time
import requests
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

from .prepare import ExecutionPlan, Lane
from .sql_variants import generate_sql_for_plan, SQLVariant


@dataclass
class UnionResult:
    """Result from UNION execution."""
    rows: List[Dict]
    total_rows: int
    tables_hit: List[str]
    waves_executed: int
    tiers_executed: int
    early_exit: bool
    execution_time_ms: float
    trace: Dict[str, Any]
    error: Optional[str] = None


def get_supabase_config() -> Tuple[str, str]:
    """Get Supabase URL and key from environment."""
    url = os.environ.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_SERVICE_KEY", os.environ.get("SUPABASE_KEY", ""))
    return url, key


def execute_rpc(
    base_url: str,
    api_key: str,
    function_name: str,
    params: Dict[str, Any]
) -> Tuple[List[Dict], Optional[str]]:
    """Execute Supabase RPC function."""
    headers = {
        "apikey": api_key,
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    try:
        resp = requests.post(
            f"{base_url}/rest/v1/rpc/{function_name}",
            headers=headers,
            json=params,
            timeout=30
        )

        if resp.status_code == 200:
            return resp.json(), None
        elif resp.status_code == 404:
            return [], "RPC function not found"
        else:
            return [], f"RPC error: {resp.status_code} - {resp.text[:200]}"

    except Exception as e:
        return [], str(e)


def execute_union_sql(
    plan: ExecutionPlan,
    base_url: str = None,
    api_key: str = None,
    max_waves: int = 2,
    early_exit_threshold: int = 20
) -> UnionResult:
    """
    Execute UNION ALL batched SQL.

    Flow:
    1. Generate SQL variants from plan
    2. Execute tier by tier, wave by wave
    3. Early exit if enough results
    4. Return merged results with trace

    Args:
        plan: ExecutionPlan from prepare()
        base_url: Supabase URL (defaults to env)
        api_key: Supabase key (defaults to env)
        max_waves: Maximum waves to execute (0=EXACT, 1=ILIKE, 2=TRIGRAM)
        early_exit_threshold: Stop if this many results found

    Returns:
        UnionResult with rows, trace, metadata
    """
    start_time = time.time()

    # Get config
    if not base_url or not api_key:
        base_url, api_key = get_supabase_config()

    if not base_url or not api_key:
        return UnionResult(
            rows=[], total_rows=0, tables_hit=[], waves_executed=0,
            tiers_executed=0, early_exit=False, execution_time_ms=0,
            trace={"error": "Missing Supabase config"},
            error="SUPABASE_URL or SUPABASE_KEY not set"
        )

    # Generate SQL variants
    variants = generate_sql_for_plan(plan)

    if not variants:
        # BLOCKED or UNKNOWN lane
        return UnionResult(
            rows=[], total_rows=0, tables_hit=[], waves_executed=0,
            tiers_executed=0, early_exit=False,
            execution_time_ms=(time.time() - start_time) * 1000,
            trace={"lane": plan.lane.lane.value, "reason": "No SQL generated"}
        )

    # Group variants by tier
    tiers = {}
    for v in variants:
        tier = int(v.variant_id.split("_")[-1].replace("w", "")) if "w" in v.variant_id else 0
        if tier not in tiers:
            tiers[tier] = []
        tiers[tier].append(v)

    all_rows = []
    tables_hit = set()
    waves_executed = 0
    tiers_executed = 0
    trace = {"waves": [], "variants_executed": []}
    early_exit = False

    # Execute tier by tier
    for tier_num in sorted(tiers.keys()):
        tier_variants = tiers[tier_num]
        tiers_executed += 1

        for variant in tier_variants:
            if variant.wave > max_waves:
                continue

            waves_executed = max(waves_executed, variant.wave + 1)

            # Try RPC first
            rows, err = execute_rpc(
                base_url, api_key,
                "search_union",
                {
                    "p_yacht_id": plan.user_scope.yacht_ids[0] if plan.user_scope.yacht_ids else "",
                    "p_sql": variant.sql,
                    "p_params": variant.params[1:] if len(variant.params) > 1 else []  # Skip yacht_id
                }
            )

            if err and "not found" in err.lower():
                # RPC not deployed - execute via raw SQL REST
                rows, err = execute_raw_sql(base_url, api_key, variant.sql, variant.params)

            if err:
                trace["waves"].append({
                    "tier": tier_num,
                    "wave": variant.wave,
                    "tables": variant.tables,
                    "error": err
                })
                continue

            trace["waves"].append({
                "tier": tier_num,
                "wave": variant.wave,
                "tables": variant.tables,
                "rows": len(rows)
            })
            trace["variants_executed"].append(variant.variant_id)

            all_rows.extend(rows)
            tables_hit.update(variant.tables)

            # Early exit check
            if len(all_rows) >= early_exit_threshold:
                early_exit = True
                break

        if early_exit:
            break

    # Dedupe by id
    seen_ids = set()
    unique_rows = []
    for row in all_rows:
        row_id = row.get("id", str(row))
        if row_id not in seen_ids:
            seen_ids.add(row_id)
            unique_rows.append(row)

    elapsed = (time.time() - start_time) * 1000

    return UnionResult(
        rows=unique_rows,
        total_rows=len(unique_rows),
        tables_hit=list(tables_hit),
        waves_executed=waves_executed,
        tiers_executed=tiers_executed,
        early_exit=early_exit,
        execution_time_ms=elapsed,
        trace=trace
    )


def execute_raw_sql(
    base_url: str,
    api_key: str,
    sql: str,
    params: List
) -> Tuple[List[Dict], Optional[str]]:
    """
    Execute raw SQL via PostgREST (if supported) or fallback.

    Note: PostgREST doesn't support raw SQL execution.
    This function is a placeholder for when we have a proper
    SQL execution endpoint (e.g., pg-rest proxy or Edge Function).

    For now, returns error so caller falls back to per-table REST.
    """
    # PostgREST doesn't support raw SQL
    # Would need Edge Function or direct Postgres connection
    return [], "Raw SQL execution not supported via REST"


def execute_union_with_fallback(
    plan: ExecutionPlan,
    base_url: str,
    api_key: str,
    max_waves: int = 2,
    early_exit_threshold: int = 20
) -> UnionResult:
    """
    Execute with UNION RPC if available, fallback to per-table REST.

    This is the REAL entry point - tries true UNION first, then falls back.
    """
    start_time = time.time()

    # Try RPC UNION first
    result = execute_union_sql(plan, base_url, api_key, max_waves, early_exit_threshold)

    # Check if we got results or if RPC failed
    rpc_worked = result.rows or (not result.error)

    if rpc_worked and result.rows:
        # RPC worked and returned results
        return result

    # Fallback to per-table REST
    from .execute import execute_search

    rest_result = execute_search(base_url, api_key, plan, max_waves=max_waves)

    elapsed = (time.time() - start_time) * 1000

    return UnionResult(
        rows=rest_result.rows,
        total_rows=rest_result.total_rows,
        tables_hit=rest_result.tables_hit,
        waves_executed=rest_result.waves_executed,
        tiers_executed=len(plan.batches),
        early_exit=rest_result.early_exit,
        execution_time_ms=elapsed,
        trace={
            "strategy": "REST_FALLBACK",
            "rpc_error": result.error,
            "rest_trace": rest_result.trace
        }
    )


# Convenience function for direct use
def search_with_union(
    query: str,
    entities: List[Dict],
    yacht_id: str,
    user_id: str = "anonymous",
    user_role: str = "crew",
    base_url: str = None,
    api_key: str = None
) -> UnionResult:
    """
    Full search flow with UNION batching.

    Args:
        query: User query
        entities: Extracted entities
        yacht_id: Target yacht
        user_id: User ID
        user_role: User role
        base_url: Supabase URL (optional, uses env)
        api_key: Supabase key (optional, uses env)

    Returns:
        UnionResult with rows and trace
    """
    from .prepare import prepare

    plan = prepare(query, entities, yacht_id, user_id, user_role)

    return execute_union_sql(
        plan,
        base_url=base_url,
        api_key=api_key
    )
