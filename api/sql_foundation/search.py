#!/usr/bin/env python3
"""
SQL FOUNDATION — UNIFIED SEARCH
================================
Single entry point for entity-based search.

Usage:
    from api.sql_foundation import search
    results = search(supabase_client, yacht_id, entities)
"""
import time
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

from .compiler import compile_probes
from .executor import ProbeExecutor, WaveResult
from .probe import ProbeResult


@dataclass
class SearchResult:
    """Complete search result with observability."""
    # Core results
    rows: List[Dict[str, Any]]
    total_count: int

    # Observability
    waves_executed: int
    probes_executed: int
    execution_time_ms: float
    early_exit: bool

    # Per-table breakdown
    results_by_table: Dict[str, List[Dict]]

    # Debug info
    wave_details: List[Dict] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


def search(
    supabase_client,
    yacht_id: str,
    entities: List[Dict[str, str]],
    max_results: int = 50,
    max_waves: int = 2,  # Default to waves 0-1 (EXACT + ILIKE)
) -> SearchResult:
    """
    Execute entity-based search.

    Args:
        supabase_client: Supabase client instance
        yacht_id: UUID of yacht
        entities: List of {"type": "PART_NUMBER", "value": "ENG-0008-103"}
        max_results: Maximum total results to return
        max_waves: Maximum wave number to execute (0=EXACT, 1=ILIKE, 2=TRIGRAM)

    Returns:
        SearchResult with rows and observability data
    """
    start = time.time()

    # 1. Compile entities to probes
    probes_by_wave = compile_probes(yacht_id, entities)

    if not any(probes_by_wave.values()):
        return SearchResult(
            rows=[],
            total_count=0,
            waves_executed=0,
            probes_executed=0,
            execution_time_ms=(time.time() - start) * 1000,
            early_exit=False,
            results_by_table={},
            errors=["No probes compiled - check entity types"]
        )

    # 2. Execute probes wave by wave
    executor = ProbeExecutor(supabase_client, yacht_id)

    all_rows = []
    results_by_table = {}
    wave_details = []
    errors = []
    probes_executed = 0
    waves_executed = 0
    early_exit = False

    for wave in range(max_waves + 1):
        probes = probes_by_wave.get(wave, [])
        if not probes:
            continue

        wave_result = executor.execute_wave(probes, wave)
        waves_executed += 1
        probes_executed += wave_result.probes_executed

        # Collect results
        for probe_result in wave_result.results:
            if probe_result.error:
                errors.append(f"{probe_result.probe_id}: {probe_result.error}")
            elif probe_result.rows:
                all_rows.extend(probe_result.rows)

                # Group by table
                if probe_result.table not in results_by_table:
                    results_by_table[probe_result.table] = []
                results_by_table[probe_result.table].extend(probe_result.rows)

        # Record wave details
        wave_details.append({
            "wave": wave,
            "probes": wave_result.probes_executed,
            "rows": wave_result.total_rows,
            "time_ms": round(wave_result.execution_time_ms, 1),
            "early_exit": wave_result.early_exit
        })

        # Check early exit
        if wave_result.early_exit:
            early_exit = True
            break

        # Stop if we have enough results
        if len(all_rows) >= max_results:
            break

    # 3. Deduplicate by ID (if present)
    seen_ids = set()
    unique_rows = []
    for row in all_rows:
        row_id = row.get("id")
        if row_id:
            if row_id not in seen_ids:
                seen_ids.add(row_id)
                unique_rows.append(row)
        else:
            unique_rows.append(row)

    # Limit results
    final_rows = unique_rows[:max_results]

    elapsed = (time.time() - start) * 1000

    return SearchResult(
        rows=final_rows,
        total_count=len(final_rows),
        waves_executed=waves_executed,
        probes_executed=probes_executed,
        execution_time_ms=round(elapsed, 1),
        early_exit=early_exit,
        results_by_table=results_by_table,
        wave_details=wave_details,
        errors=errors
    )


def search_by_text(
    supabase_client,
    yacht_id: str,
    query_text: str,
    entity_extractor=None,
    max_results: int = 50,
) -> SearchResult:
    """
    Search by raw text query.

    If entity_extractor is provided, uses it to extract entities.
    Otherwise, treats the entire query as a generic search term.

    Args:
        supabase_client: Supabase client
        yacht_id: UUID of yacht
        query_text: Raw user query
        entity_extractor: Optional callable that extracts entities from text
        max_results: Max results

    Returns:
        SearchResult
    """
    if entity_extractor:
        # Use provided extractor (e.g., GPT-based)
        entities = entity_extractor(query_text)
    else:
        # Fallback: treat as free text search across common fields
        entities = [{"type": "FREE_TEXT", "value": query_text}]

    return search(supabase_client, yacht_id, entities, max_results)
