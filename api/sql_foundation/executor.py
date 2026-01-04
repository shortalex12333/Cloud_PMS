"""
SQL FOUNDATION — PROBE EXECUTOR
================================
Executes probes against database.
ONLY substitutes values and runs. No SQL logic here.
"""
import time
import json
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from .probe import Probe, ProbeResult
from .operators import WAVE_BUDGETS_MS

@dataclass
class WaveResult:
    """Results from executing a wave of probes."""
    wave: int
    probes_executed: int
    total_rows: int
    execution_time_ms: float
    results: List[ProbeResult]
    early_exit: bool = False

class ProbeExecutor:
    """
    Executes probes against Supabase.

    Responsibilities:
    1. Substitute values into SQL
    2. Execute with parameterization
    3. Record timing and results
    4. Early exit on strong hits

    NOT responsible for:
    - SQL generation (that's the compiler)
    - Result ranking (that's the scorer)
    """

    def __init__(self, supabase_client, yacht_id: str):
        self.client = supabase_client
        self.yacht_id = yacht_id

    def execute_probe(self, probe: Probe) -> ProbeResult:
        """Execute a single probe."""
        start = time.time()
        error = None
        rows = []

        try:
            sql = probe.to_sql()
            # Execute via Supabase RPC or direct query
            # For now, using REST API pattern
            response = self._execute_sql(sql, probe.params)
            rows = response if isinstance(response, list) else []

        except Exception as e:
            error = str(e)

        elapsed = (time.time() - start) * 1000

        return ProbeResult(
            probe_id=probe.probe_id,
            table=probe.table,
            operator=probe.where_clauses[0].operator if probe.where_clauses else None,
            rows_returned=len(rows),
            execution_time_ms=elapsed,
            rows=rows,
            error=error
        )

    def execute_wave(
        self,
        probes: List[Probe],
        wave: int,
        concurrency: int = 5,
        early_exit_threshold: int = 10
    ) -> WaveResult:
        """
        Execute a wave of probes with budget enforcement.

        Args:
            probes: Probes to execute in this wave
            wave: Wave number (0-3)
            concurrency: Max parallel executions
            early_exit_threshold: Exit if this many strong hits found
        """
        budget_ms = WAVE_BUDGETS_MS.get(wave, 3000)
        start = time.time()
        results = []
        total_rows = 0
        early_exit = False

        for probe in probes:
            # Check budget
            elapsed = (time.time() - start) * 1000
            if elapsed >= budget_ms:
                break

            result = self.execute_probe(probe)
            results.append(result)
            total_rows += result.rows_returned

            # Early exit on strong hits (wave 0 only)
            if wave == 0 and result.has_hits and total_rows >= early_exit_threshold:
                early_exit = True
                break

        elapsed = (time.time() - start) * 1000

        return WaveResult(
            wave=wave,
            probes_executed=len(results),
            total_rows=total_rows,
            execution_time_ms=elapsed,
            results=results,
            early_exit=early_exit
        )

    def execute_search(
        self,
        probes_by_wave: Dict[int, List[Probe]],
        max_waves: int = 4
    ) -> List[WaveResult]:
        """
        Execute full search across waves.

        Stops early if:
        - Strong exact hits found in wave 0
        - Confidence threshold met
        """
        wave_results = []

        for wave in range(max_waves):
            probes = probes_by_wave.get(wave, [])
            if not probes:
                continue

            result = self.execute_wave(probes, wave)
            wave_results.append(result)

            # Early exit if wave 0 found strong hits
            if result.early_exit:
                break

        return wave_results

    def _execute_sql(self, sql: str, params: List[Any]) -> List[Dict]:
        """
        Execute SQL via Supabase PostgREST.

        This is the ONLY place actual database calls happen.
        Uses PostgREST filters instead of raw SQL for security.
        """
        # We can't execute raw SQL via PostgREST - must use filters
        # This method is called by execute_probe which has the Probe object
        # We need to refactor to use the probe directly
        raise NotImplementedError("Use execute_probe_rest instead")

    def execute_probe_rest(self, probe: Probe) -> ProbeResult:
        """
        Execute a probe via PostgREST API.

        Converts probe to PostgREST query format.
        """
        start = time.time()
        error = None
        rows = []

        try:
            # Build PostgREST query
            table = probe.table
            select_cols = ",".join(probe.select_cols)

            # Start with table query
            query = self.client.table(table).select(select_cols)

            # Always filter by yacht_id (first param)
            query = query.eq("yacht_id", probe.params[0])

            # Apply WHERE clauses
            unsupported_operator = False
            for i, clause in enumerate(probe.where_clauses):
                param_idx = clause.param_ref - 1  # Convert $2 to index 1
                if param_idx < len(probe.params):
                    value = probe.params[param_idx]

                    if clause.operator.value == "EXACT":
                        query = query.eq(clause.column, value)
                    elif clause.operator.value == "ILIKE":
                        query = query.ilike(clause.column, value)
                    elif clause.operator.value == "IN":
                        query = query.in_(clause.column, value if isinstance(value, list) else [value])
                    else:
                        # TRIGRAM, VECTOR, etc. need RPC - skip this probe
                        unsupported_operator = True
                        break

            if unsupported_operator:
                # Return empty result for unsupported operators
                return ProbeResult(
                    probe_id=probe.probe_id,
                    table=probe.table,
                    operator=probe.where_clauses[0].operator if probe.where_clauses else None,
                    rows_returned=0,
                    execution_time_ms=(time.time() - start) * 1000,
                    rows=[],
                    error=f"Operator {probe.where_clauses[0].operator.value} requires RPC (not implemented)"
                )

            # Apply limit
            query = query.limit(probe.limit)

            # Execute
            response = query.execute()
            rows = response.data if response.data else []

        except Exception as e:
            error = str(e)

        elapsed = (time.time() - start) * 1000

        return ProbeResult(
            probe_id=probe.probe_id,
            table=probe.table,
            operator=probe.where_clauses[0].operator if probe.where_clauses else None,
            rows_returned=len(rows),
            execution_time_ms=elapsed,
            rows=rows,
            error=error
        )

    def execute_probe(self, probe: Probe) -> ProbeResult:
        """Execute a single probe via REST."""
        return self.execute_probe_rest(probe)


# =============================================================================
# SUPABASE RPC FUNCTION (to be deployed)
# =============================================================================
EXECUTE_PROBE_RPC = """
-- Deploy this function to Supabase
CREATE OR REPLACE FUNCTION execute_probe(
    p_table text,
    p_select_cols text[],
    p_where_column text,
    p_operator text,
    p_yacht_id uuid,
    p_value text,
    p_limit integer DEFAULT 50
)
RETURNS SETOF jsonb
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    query text;
    result jsonb;
BEGIN
    -- Build query based on operator
    query := format(
        'SELECT to_jsonb(t.*) FROM %I t WHERE yacht_id = %L',
        p_table, p_yacht_id
    );

    CASE p_operator
        WHEN 'EXACT' THEN
            query := query || format(' AND %I = %L', p_where_column, p_value);
        WHEN 'ILIKE' THEN
            query := query || format(' AND %I ILIKE %L', p_where_column, p_value);
        WHEN 'TRIGRAM' THEN
            query := query || format(
                ' AND similarity(%I, %L) >= 0.3 ORDER BY similarity(%I, %L) DESC',
                p_where_column, p_value, p_where_column, p_value
            );
        ELSE
            RAISE EXCEPTION 'Unknown operator: %', p_operator;
    END CASE;

    query := query || format(' LIMIT %s', p_limit);

    -- Execute and return
    RETURN QUERY EXECUTE query;
END;
$$;

-- Grant execute to authenticated users
GRANT EXECUTE ON FUNCTION execute_probe TO authenticated;
GRANT EXECUTE ON FUNCTION execute_probe TO service_role;
"""

# =============================================================================
# MOCK EXECUTOR FOR TESTING
# =============================================================================
class MockProbeExecutor(ProbeExecutor):
    """Mock executor for testing without database."""

    def __init__(self, yacht_id: str, mock_data: Dict[str, List[Dict]] = None):
        self.yacht_id = yacht_id
        self.mock_data = mock_data or {}
        self.executed_probes = []

    def _execute_sql(self, sql: str, params: List[Any]) -> List[Dict]:
        """Return mock data based on table."""
        self.executed_probes.append({"sql": sql, "params": params})

        # Extract table from SQL
        for table, rows in self.mock_data.items():
            if table in sql:
                # Simple mock: return all rows for matching table
                return rows[:10]

        return []
