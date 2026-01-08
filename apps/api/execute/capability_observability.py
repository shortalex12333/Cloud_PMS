"""
Capability Observability - Request Logging
============================================

Logs capability execution for analysis:
- Which capabilities are requested
- Which are executed vs blocked
- Execution times and row counts
- UNKNOWN outcomes

Enables data-driven decisions:
- Where do users want coverage next?
- Where is UNKNOWN acceptable vs frustrating?
- Which capability to unblock next?

USAGE:
    from api.capability_observability import log_search_request

    log_search_request(
        yacht_id="85fe1119-...",
        query="impeller main engine",
        entities=[...],
        response=composed_response,
    )

LOG FORMAT (JSON Lines):
    {
        "timestamp": "2026-01-02T18:55:00Z",
        "yacht_id": "85fe1119-...",
        "query": "impeller main engine",
        "entities": [...],
        "capabilities_considered": [...],
        "capabilities_executed": [...],
        "capabilities_blocked": [...],
        "execution_times_ms": {...},
        "rows_per_capability": {...},
        "total_results": 10,
        "total_time_ms": 150.5,
        "outcome": "success|partial|blocked|unknown"
    }
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional

# Configure logger
logger = logging.getLogger("capability_observability")
logger.setLevel(logging.INFO)

# Create logs directory if needed
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
os.makedirs(LOG_DIR, exist_ok=True)

# File handler for JSON lines
log_file = os.path.join(LOG_DIR, "capability_requests.jsonl")
file_handler = logging.FileHandler(log_file, mode="a")
file_handler.setFormatter(logging.Formatter("%(message)s"))
logger.addHandler(file_handler)


def determine_outcome(
    considered: List[str],
    executed: List[str],
    blocked: List[Dict],
    total_results: int,
) -> str:
    """
    Determine the outcome category for a search request.

    Returns:
        - "success": At least one capability executed with results
        - "empty": Capabilities executed but no results
        - "partial": Some capabilities blocked but others executed
        - "blocked": All capabilities blocked
        - "unknown": No capabilities matched
    """
    if not considered:
        return "unknown"

    if len(blocked) == len(considered):
        return "blocked"

    if not executed:
        return "unknown"

    if blocked and executed:
        return "partial" if total_results > 0 else "empty"

    return "success" if total_results > 0 else "empty"


def log_search_request(
    yacht_id: str,
    query: str,
    entities: List[Dict[str, Any]],
    capabilities_considered: List[str],
    capabilities_executed: List[str],
    capabilities_blocked: List[Dict[str, str]],
    execution_times_ms: Dict[str, float],
    rows_per_capability: Dict[str, int],
    total_results: int,
    total_time_ms: float,
    lane: Optional[str] = None,
    error: Optional[str] = None,
) -> None:
    """
    Log a search request for observability.

    This creates a JSON line in logs/capability_requests.jsonl
    """
    outcome = determine_outcome(
        capabilities_considered,
        capabilities_executed,
        capabilities_blocked,
        total_results,
    )

    log_entry = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "yacht_id": yacht_id,
        "query": query[:200],  # Truncate long queries
        "entities": entities,
        "lane": lane,
        "capabilities_considered": capabilities_considered,
        "capabilities_executed": capabilities_executed,
        "capabilities_blocked": capabilities_blocked,
        "execution_times_ms": execution_times_ms,
        "rows_per_capability": rows_per_capability,
        "total_results": total_results,
        "total_time_ms": round(total_time_ms, 2),
        "outcome": outcome,
        "error": error,
    }

    logger.info(json.dumps(log_entry))


def log_from_composed_response(
    yacht_id: str,
    query: str,
    entities: List[Dict[str, Any]],
    response,  # ComposedResponse
    lane: Optional[str] = None,
) -> None:
    """
    Convenience function to log from a ComposedResponse object.
    """
    log_search_request(
        yacht_id=yacht_id,
        query=query,
        entities=entities,
        capabilities_considered=response.capabilities_considered,
        capabilities_executed=response.capabilities_executed,
        capabilities_blocked=response.capabilities_blocked,
        execution_times_ms=response.execution_times_ms,
        rows_per_capability=response.rows_per_capability,
        total_results=response.total_count,
        total_time_ms=response.total_execution_time_ms,
        lane=lane,
        error=response.error,
    )


# =============================================================================
# ANALYTICS HELPERS
# =============================================================================

def get_log_stats(log_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Analyze the log file and return summary statistics.

    Returns:
        Dict with:
        - total_requests
        - outcomes: {success: N, empty: N, partial: N, blocked: N, unknown: N}
        - capabilities: {cap_name: {requested: N, executed: N, blocked: N}}
        - avg_execution_times: {cap_name: avg_ms}
    """
    if log_path is None:
        log_path = log_file

    if not os.path.exists(log_path):
        return {"error": "Log file not found"}

    stats = {
        "total_requests": 0,
        "outcomes": {"success": 0, "empty": 0, "partial": 0, "blocked": 0, "unknown": 0},
        "capabilities": {},
        "execution_times": {},
    }

    with open(log_path) as f:
        for line in f:
            try:
                entry = json.loads(line.strip())
            except json.JSONDecodeError:
                continue

            stats["total_requests"] += 1

            # Count outcomes
            outcome = entry.get("outcome", "unknown")
            if outcome in stats["outcomes"]:
                stats["outcomes"][outcome] += 1

            # Count capability usage
            for cap in entry.get("capabilities_considered", []):
                if cap not in stats["capabilities"]:
                    stats["capabilities"][cap] = {"requested": 0, "executed": 0, "blocked": 0}
                stats["capabilities"][cap]["requested"] += 1

            for cap in entry.get("capabilities_executed", []):
                if cap in stats["capabilities"]:
                    stats["capabilities"][cap]["executed"] += 1

            for blocked in entry.get("capabilities_blocked", []):
                cap = blocked.get("name", "")
                if cap in stats["capabilities"]:
                    stats["capabilities"][cap]["blocked"] += 1

            # Collect execution times
            for cap, time_ms in entry.get("execution_times_ms", {}).items():
                if cap not in stats["execution_times"]:
                    stats["execution_times"][cap] = []
                stats["execution_times"][cap].append(time_ms)

    # Calculate averages
    stats["avg_execution_times"] = {
        cap: round(sum(times) / len(times), 2)
        for cap, times in stats["execution_times"].items()
        if times
    }
    del stats["execution_times"]  # Remove raw data

    return stats


# =============================================================================
# CLI
# =============================================================================

if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--stats":
        stats = get_log_stats()
        print(json.dumps(stats, indent=2))
    else:
        print("Usage: python -m api.capability_observability --stats")
        print(f"\nLog file: {log_file}")
        if os.path.exists(log_file):
            with open(log_file) as f:
                lines = sum(1 for _ in f)
            print(f"Entries: {lines}")
