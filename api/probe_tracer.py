"""
Probe Trace Instrumentation for SQL Stress Testing
===================================================
Logs every SQL execution with structured data for analysis.
"""
import json
import time
import uuid
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Optional, List, Any
from enum import Enum

LOG_PATH = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))logs/sql_probe_traces.jsonl")
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

class MatchMode(Enum):
    EXACT = "EXACT"
    ILIKE = "ILIKE"
    TRIGRAM = "TRIGRAM"
    VECTOR = "VECTOR"
    CONTAINS = "CONTAINS"

class Wave(Enum):
    WAVE_0 = 0  # EXACT
    WAVE_1 = 1  # ILIKE
    WAVE_2 = 2  # TRIGRAM
    WAVE_3 = 3  # VECTOR

@dataclass
class ProbeTrace:
    """Single probe trace entry for SQL execution."""
    query_id: str
    timestamp: str
    original_query: str

    # Routing info
    lane: str
    wave: int
    entity_type: str
    canonical_term: str

    # SQL execution
    table: str
    column: str
    match_mode: str
    sql_template: str  # Parameterized SQL (no values)

    # Security
    yacht_id_enforced: bool
    yacht_id: str

    # Results
    rows_returned: int
    execution_time_ms: float
    error: Optional[str] = None

    # Scoring
    base_score: int = 0
    final_score: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)

class ProbeTracer:
    """Central probe tracer for SQL stress testing."""

    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        self._traces: List[ProbeTrace] = []

    def trace(
        self,
        query_id: str,
        original_query: str,
        lane: str,
        wave: int,
        entity_type: str,
        canonical_term: str,
        table: str,
        column: str,
        match_mode: str,
        sql_template: str,
        yacht_id_enforced: bool,
        yacht_id: str,
        rows_returned: int,
        execution_time_ms: float,
        error: Optional[str] = None,
        base_score: int = 0,
        final_score: float = 0.0
    ) -> ProbeTrace:
        """Record a single SQL execution trace."""
        trace = ProbeTrace(
            query_id=query_id,
            timestamp=datetime.utcnow().isoformat(),
            original_query=original_query,
            lane=lane,
            wave=wave,
            entity_type=entity_type,
            canonical_term=canonical_term,
            table=table,
            column=column,
            match_mode=match_mode,
            sql_template=sql_template,
            yacht_id_enforced=yacht_id_enforced,
            yacht_id=yacht_id,
            rows_returned=rows_returned,
            execution_time_ms=execution_time_ms,
            error=error,
            base_score=base_score,
            final_score=final_score
        )

        if self.enabled:
            self._traces.append(trace)
            self._write_trace(trace)

        return trace

    def _write_trace(self, trace: ProbeTrace):
        """Append trace to JSONL log file."""
        with open(LOG_PATH, "a") as f:
            f.write(json.dumps(trace.to_dict()) + "\n")

    def get_traces(self) -> List[ProbeTrace]:
        """Get all traces from current session."""
        return self._traces

    def clear(self):
        """Clear in-memory traces."""
        self._traces = []

    @staticmethod
    def load_traces(limit: int = None) -> List[dict]:
        """Load traces from log file."""
        traces = []
        if LOG_PATH.exists():
            with open(LOG_PATH, "r") as f:
                for line in f:
                    if line.strip():
                        traces.append(json.loads(line))
                        if limit and len(traces) >= limit:
                            break
        return traces

    @staticmethod
    def analyze_traces() -> dict:
        """Analyze all traces and return summary stats."""
        traces = ProbeTracer.load_traces()
        if not traces:
            return {"error": "No traces found"}

        # Basic counts
        total = len(traces)
        by_lane = {}
        by_wave = {}
        by_table = {}
        by_match_mode = {}
        yacht_id_enforced_count = 0
        errors = []
        execution_times = []

        for t in traces:
            # Lane breakdown
            lane = t.get("lane", "UNKNOWN")
            by_lane[lane] = by_lane.get(lane, 0) + 1

            # Wave breakdown
            wave = t.get("wave", -1)
            by_wave[wave] = by_wave.get(wave, 0) + 1

            # Table breakdown
            table = t.get("table", "UNKNOWN")
            by_table[table] = by_table.get(table, 0) + 1

            # Match mode breakdown
            mm = t.get("match_mode", "UNKNOWN")
            by_match_mode[mm] = by_match_mode.get(mm, 0) + 1

            # Security check
            if t.get("yacht_id_enforced"):
                yacht_id_enforced_count += 1

            # Errors
            if t.get("error"):
                errors.append({"query_id": t.get("query_id"), "error": t.get("error")})

            # Execution times
            if t.get("execution_time_ms"):
                execution_times.append(t["execution_time_ms"])

        # Latency stats
        avg_latency = sum(execution_times) / len(execution_times) if execution_times else 0
        p50 = sorted(execution_times)[len(execution_times)//2] if execution_times else 0
        p95 = sorted(execution_times)[int(len(execution_times)*0.95)] if execution_times else 0
        p99 = sorted(execution_times)[int(len(execution_times)*0.99)] if execution_times else 0

        return {
            "total_traces": total,
            "by_lane": by_lane,
            "by_wave": by_wave,
            "by_table": by_table,
            "by_match_mode": by_match_mode,
            "yacht_id_enforcement_rate": yacht_id_enforced_count / total if total else 0,
            "error_count": len(errors),
            "errors": errors[:20],  # First 20 errors
            "latency": {
                "avg_ms": round(avg_latency, 2),
                "p50_ms": round(p50, 2),
                "p95_ms": round(p95, 2),
                "p99_ms": round(p99, 2)
            }
        }


# Global tracer instance
_tracer: Optional[ProbeTracer] = None

def get_tracer() -> ProbeTracer:
    """Get or create global tracer instance."""
    global _tracer
    if _tracer is None:
        _tracer = ProbeTracer(enabled=True)
    return _tracer

def trace_sql_execution(
    query_id: str,
    original_query: str,
    lane: str,
    wave: int,
    entity_type: str,
    canonical_term: str,
    table: str,
    column: str,
    match_mode: str,
    sql_template: str,
    yacht_id_enforced: bool,
    yacht_id: str,
    rows_returned: int,
    execution_time_ms: float,
    error: Optional[str] = None,
    base_score: int = 0,
    final_score: float = 0.0
) -> ProbeTrace:
    """Convenience function to trace SQL execution."""
    return get_tracer().trace(
        query_id=query_id,
        original_query=original_query,
        lane=lane,
        wave=wave,
        entity_type=entity_type,
        canonical_term=canonical_term,
        table=table,
        column=column,
        match_mode=match_mode,
        sql_template=sql_template,
        yacht_id_enforced=yacht_id_enforced,
        yacht_id=yacht_id,
        rows_returned=rows_returned,
        execution_time_ms=execution_time_ms,
        error=error,
        base_score=base_score,
        final_score=final_score
    )


# Decorator for timing SQL functions
def traced_sql(entity_type: str, table: str, column: str, match_mode: str):
    """Decorator to automatically trace SQL execution."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            query_id = str(uuid.uuid4())[:8]
            start = time.time()
            error = None
            rows = 0

            try:
                result = func(*args, **kwargs)
                rows = len(result) if isinstance(result, (list, tuple)) else 0
                return result
            except Exception as e:
                error = str(e)
                raise
            finally:
                elapsed = (time.time() - start) * 1000
                trace_sql_execution(
                    query_id=query_id,
                    original_query=kwargs.get("query", ""),
                    lane=kwargs.get("lane", "UNKNOWN"),
                    wave=kwargs.get("wave", 0),
                    entity_type=entity_type,
                    canonical_term=kwargs.get("term", ""),
                    table=table,
                    column=column,
                    match_mode=match_mode,
                    sql_template=f"SELECT * FROM {table} WHERE {column} = $1",
                    yacht_id_enforced=True,
                    yacht_id=kwargs.get("yacht_id", ""),
                    rows_returned=rows,
                    execution_time_ms=elapsed,
                    error=error
                )
        return wrapper
    return decorator


if __name__ == "__main__":
    # Quick test
    tracer = ProbeTracer(enabled=True)

    # Simulate some traces
    for i in range(5):
        tracer.trace(
            query_id=f"test-{i}",
            original_query=f"test query {i}",
            lane="NO_LLM",
            wave=0,
            entity_type="PART_NUMBER",
            canonical_term=f"PART{i:03d}",
            table="pms_parts",
            column="part_number",
            match_mode="EXACT",
            sql_template="SELECT * FROM pms_parts WHERE part_number = $1 AND yacht_id = $2",
            yacht_id_enforced=True,
            yacht_id="test-yacht-id",
            rows_returned=i,
            execution_time_ms=10.5 + i,
            base_score=1000,
            final_score=1000.0 - i * 10
        )

    # Analyze
    stats = ProbeTracer.analyze_traces()
    print(json.dumps(stats, indent=2))
