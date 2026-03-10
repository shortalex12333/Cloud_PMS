#!/usr/bin/env python3
"""
Ground Truth Search Validation — Literacy-Variant Test Suite

Measures search quality across 5 literacy levels for 15 known items.
Two ranking tiers: @3 (top 3) and @5 (top 5). Pure positional math.

Principle: VAGUE IN = VAGUE OUT.
Every query carries enough semantic signal to deserve its expected result.
If a query is ambiguous, ambiguous results are CORRECT — not a failure.

Usage:
    export JWT_TOKEN="eyJ..."
    export API_BASE_URL="https://your-api.onrender.com"  # or http://localhost:8000
    python3 test/ground_truth_search.py

Data source: Supabase CSVs from search_index table (9 files, 100K+ rows).
Object IDs verified against CSV exports 2026-03-09.
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple


# ============================================================================
# Configuration
# ============================================================================

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
JWT_TOKEN = os.getenv("JWT_TOKEN", "")
YACHT_ID = "85fe1119-b04c-41ac-80f1-829d23322598"
QUERY_DELAY_S = 2.0  # seconds between queries to avoid DB timeout

# Ranking tiers — no bias, pure positional math
TOP_3 = 3
TOP_5 = 5


# ============================================================================
# Literacy Levels
# ============================================================================

LEVELS = {
    "L1": "Articulate",
    "L2": "Crew shorthand",
    "L3": "Typos/misspelling",
    "L4": "ESL/broken grammar",
    "L5": "Abbreviation/code",
}


# ============================================================================
# Ground Truth — 15 Items × 5 Literacy Levels = 75 Queries
#
# Every query earns its expected result. No biasing. No charity.
# Part-number queries (L5) are the most unambiguous — if those fail,
# the index is broken. Vague queries deserve vague results.
# ============================================================================

@dataclass
class GroundTruthItem:
    """One known item with 5 query variants."""
    number: int
    name: str
    entity_type: str
    detail: str          # manufacturer/description
    object_id: str       # full UUID
    queries: Dict[str, str]  # L1..L5 -> query text


GROUND_TRUTH: List[GroundTruthItem] = [

    # ── PARTS (8 items) ─────────────────────────────────────────────────

    GroundTruthItem(
        number=1,
        name="Fuel Filter Generator",
        entity_type="part",
        detail="Fleetguard FLT-0033-146",
        object_id="f7913ad1-6832-4169-b816-4538c8b7a417",
        queries={
            "L1": "Show me the Fleetguard fuel filter for generator 2",
            "L2": "fuel filter generator 2 fleetguard",
            "L3": "fleetgard fule filter genrator 2",
            "L4": "the filter of fuel for generator 2 from Fleetguard please",
            "L5": "FLT-0033-146",
        },
    ),
    GroundTruthItem(
        number=2,
        name="Raw Water Pump Seal Kit",
        entity_type="part",
        detail="Grundfos PMP-0018-280",
        object_id="2f452e3b-bf3e-464e-82d5-7d0bc849e6c0",
        queries={
            "L1": "I need the raw water pump seal kit from Grundfos",
            "L2": "raw water pump seal kit grundfos",
            "L3": "raw watter pump seel kit grundfos",
            "L4": "seal kit for the raw water pump by Grundfos",
            "L5": "PMP-0018-280",
        },
    ),
    GroundTruthItem(
        number=3,
        name="Watermaker Membrane",
        entity_type="part",
        detail="Grundfos PMP-0116-528",
        object_id="ecfed2a8-3d37-4fcd-9c89-455fa32be282",
        queries={
            "L1": "Show me the watermaker membrane from Grundfos",
            "L2": "watermaker membrane grundfos",
            "L3": "watermakr membrain grundfos",
            "L4": "the membrane for watermaker from Grundfos please",
            "L5": "PMP-0116-528",
        },
    ),
    GroundTruthItem(
        number=4,
        name="GPS Antenna",
        entity_type="part",
        detail="Raymarine NAV-0132-326",
        object_id="4cc4e240-50ff-4736-b9c9-265628e54184",
        queries={
            "L1": "I need the GPS antenna by Raymarine",
            "L2": "GPS antenna raymarine",
            "L3": "GPS antena raymarene",
            "L4": "antenna for GPS from Raymarine",
            "L5": "NAV-0132-326",
        },
    ),
    GroundTruthItem(
        number=5,
        name="EPIRB Battery Replacement",
        entity_type="part",
        detail="Viking SAF-0099-425",
        object_id="384f95b5-c9fb-4f9a-8f65-8c08eb10b1fc",
        queries={
            "L1": "I need the EPIRB battery replacement from Viking",
            "L2": "EPIRB battery replacement viking",
            "L3": "eprib batter replacemnt viking",
            "L4": "battery replacement for EPIRB from Viking please",
            "L5": "SAF-0099-425",
        },
    ),
    GroundTruthItem(
        number=6,
        name="Navigation Light Bulb 12V 25W",
        entity_type="part",
        detail="Blue Sea Systems ELC-0053-760",
        object_id="c7ac473c-cf02-4241-b901-42d322fc6920",
        queries={
            "L1": "Show me the navigation light bulb 12V 25W from Blue Sea Systems",
            "L2": "navigation light bulb 12v 25w blue sea",
            "L3": "navigaton lite bulb 12v blue sea systms",
            "L4": "bulb for navigation light 12V from Blue Sea Systems",
            "L5": "ELC-0053-760",
        },
    ),
    GroundTruthItem(
        number=7,
        name="Zinc Anode Heat Exchanger",
        entity_type="part",
        detail="MTU ENG-0025-358",
        object_id="4a0ca679-8514-4fcd-8ee4-89265bb62ebf",
        queries={
            "L1": "I need the zinc anode for the heat exchanger from MTU",
            "L2": "zinc anode heat exchanger MTU",
            "L3": "zink anode heat exchanger MTU",
            "L4": "anode zinc for heat exchanger from MTU please",
            "L5": "ENG-0025-358",
        },
    ),
    GroundTruthItem(
        number=8,
        name="Anchor Chain Shackle 16mm",
        entity_type="part",
        detail="Lewmar DCK-0076-515",
        object_id="149e7a22-9d5c-4883-a990-1161516e04d1",
        queries={
            "L1": "Show me the 16mm anchor chain shackle from Lewmar",
            "L2": "anchor chain shackle 16mm lewmar",
            "L3": "anchr chain shackle 16mm lewmar",
            "L4": "shackle for anchor chain 16mm from Lewmar",
            "L5": "DCK-0076-515",
        },
    ),

    # ── WORK ORDERS (3 items) ───────────────────────────────────────────

    GroundTruthItem(
        number=9,
        name="WO-0045 Generator 2 Service",
        entity_type="work_order",
        detail="500 hour service",
        object_id="1af54ee4-d90c-450e-9687-039ed7128068",
        queries={
            "L1": "Show me work order 45 for the generator 2 service",
            "L2": "WO-0045 generator 2 service",
            "L3": "WO-0045 genertor servce",
            "L4": "the work order for 500 hour service on generator 2",
            "L5": "WO-0045",
        },
    ),
    GroundTruthItem(
        number=10,
        name="WO-0056 Generator 2 Belt Inspection",
        entity_type="work_order",
        detail="alternator and water pump belts",
        object_id="280841c4-1103-45f6-8004-75f7023e54e1",
        queries={
            "L1": "Show me work order 56 for the generator belt inspection",
            "L2": "WO-0056 generator belt inspection",
            "L3": "WO-0056 genrator belt inspecton",
            "L4": "work order to inspect belts on generator 2",
            "L5": "WO-0056",
        },
    ),
    GroundTruthItem(
        number=11,
        name="WO-0037 Sewage System Service",
        entity_type="work_order",
        detail="MSD and holding tanks",
        object_id="300c1f75-02d0-4e55-a4da-4d91ca233211",
        queries={
            "L1": "Show me work order 37 for the sewage system service",
            "L2": "WO-0037 sewage system service",
            "L3": "WO-0037 sewige systm service",
            "L4": "work order for service of sewage system and holding tanks",
            "L5": "WO-0037",
        },
    ),

    # ── FAULTS (2 items) ────────────────────────────────────────────────

    GroundTruthItem(
        number=12,
        name="GPS Signal Lost",
        entity_type="fault",
        detail="Fault code E032",
        object_id="29c6f2d0-69c2-4263-87ad-7ab56d5f9ab9",
        queries={
            "L1": "Show me the GPS signal lost fault with code E032",
            "L2": "GPS signal lost fault E032",
            "L3": "GPS siganl lost falt E032",
            "L4": "fault for GPS signal that is lost code E032",
            "L5": "E032",
        },
    ),
    GroundTruthItem(
        number=13,
        name="Generator Overheating",
        entity_type="fault",
        detail="FLT-AC6CD65E coolant 95C",
        object_id="2bf90382-4c1b-428a-bd00-decf741864a0",
        queries={
            "L1": "Show me the generator overheating fault FLT-AC6CD65E",
            "L2": "generator overheating fault FLT-AC6CD65E",
            "L3": "genrator overheeting fault FLT-AC6CD65E",
            "L4": "fault for generator overheating with coolant temperature",
            "L5": "FLT-AC6CD65E",
        },
    ),

    # ── SHOPPING LIST (1 item) ──────────────────────────────────────────

    GroundTruthItem(
        number=14,
        name="Fuel Filter CF-2250",
        entity_type="shopping_item",
        detail="Cummins",
        object_id="386121a0-1956-44af-b662-0274680024c2",
        queries={
            "L1": "I need the Cummins fuel filter CF-2250 from the shopping list",
            "L2": "fuel filter CF-2250 cummins",
            "L3": "fule filter CF-2250 cumins",
            "L4": "filter fuel CF-2250 from Cummins",
            "L5": "CF-2250",
        },
    ),

    # ── CERTIFICATE (1 item) ────────────────────────────────────────────

    GroundTruthItem(
        number=15,
        name="SOLAS Safety Certificate",
        entity_type="certificate",
        detail="Flag State",
        object_id="fdd53619-89c6-46b1-8e9f-4211e3c16fae",
        queries={
            "L1": "Show me the SOLAS safety certificate from Flag State",
            "L2": "SOLAS safety certificate flag state",
            "L3": "SOLAS safty certifcate flag state",
            "L4": "certificate for SOLAS safety from Flag State",
            "L5": "SOLAS certificate",
        },
    ),
]


# ============================================================================
# Result Types
# ============================================================================

@dataclass
class QueryResult:
    """Result of a single query against the search API."""
    item_number: int
    level: str
    query: str
    rank: Optional[int]       # 1-indexed position, None if not found
    total_results: int
    in_top_3: bool
    in_top_5: bool
    latency_ms: int
    error: Optional[str] = None


# ============================================================================
# SSE Parser
# ============================================================================

def parse_sse_response(body: str) -> Tuple[List[dict], int]:
    """
    Parse SSE response body into list of result items (ordered by rank).

    Returns:
        (items, latency_ms) — items are in rank order (index 0 = rank 1).
    """
    items = []
    latency_ms = 0

    current_event = None
    data_lines = []

    for line in body.split('\n'):
        if line.startswith('event:'):
            current_event = line[len('event:'):].strip()
            data_lines = []
        elif line.startswith('data:'):
            data_lines.append(line[len('data:'):].strip())
        elif line == '' and current_event and data_lines:
            # End of event — process it
            raw = ''.join(data_lines)
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                current_event = None
                data_lines = []
                continue

            if current_event == 'result_batch':
                batch_items = payload.get('items', [])
                items.extend(batch_items)

            elif current_event == 'finalized':
                latency_ms = payload.get('latency_ms', 0)

            current_event = None
            data_lines = []

    return items, latency_ms


# ============================================================================
# Search Execution
# ============================================================================

def run_search(query: str) -> Tuple[List[dict], int, Optional[str]]:
    """
    Execute a single search query against the SSE endpoint.

    Returns:
        (items, latency_ms, error) — items in rank order.
    """
    encoded_q = urllib.parse.quote(query, safe='')
    url = f"{API_BASE_URL}/api/f1/search/stream?q={encoded_q}"

    req = urllib.request.Request(url)
    req.add_header("Accept", "text/event-stream")
    if JWT_TOKEN:
        req.add_header("Authorization", f"Bearer {JWT_TOKEN}")

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read().decode('utf-8')
            items, latency_ms = parse_sse_response(body)
            return items, latency_ms, None
    except urllib.error.HTTPError as e:
        return [], 0, f"HTTP {e.code}: {e.reason}"
    except urllib.error.URLError as e:
        return [], 0, f"URL Error: {e.reason}"
    except Exception as e:
        return [], 0, f"Error: {str(e)}"


def find_rank(items: List[dict], expected_id: str) -> Optional[int]:
    """
    Find 1-indexed rank of expected_id in items list.
    Matches on first 8 chars of object_id (prefix match).
    Returns None if not found.
    """
    prefix = expected_id[:8]
    for i, item in enumerate(items):
        item_id = str(item.get('object_id', ''))
        if item_id.startswith(prefix):
            return i + 1  # 1-indexed
    return None


# ============================================================================
# Test Runner
# ============================================================================

def run_all_queries() -> List[QueryResult]:
    """Run all 75 queries sequentially with delays."""
    results = []
    total = len(GROUND_TRUTH) * len(LEVELS)
    completed = 0

    for item in GROUND_TRUTH:
        print(f"\n── ITEM #{item.number}: {item.name} ({item.entity_type}, {item.detail})")

        for level_key in ["L1", "L2", "L3", "L4", "L5"]:
            query = item.queries[level_key]
            completed += 1

            # Execute search
            items, latency_ms, error = run_search(query)

            if error:
                result = QueryResult(
                    item_number=item.number,
                    level=level_key,
                    query=query,
                    rank=None,
                    total_results=0,
                    in_top_3=False,
                    in_top_5=False,
                    latency_ms=0,
                    error=error,
                )
                status = f"  ERROR: {error}"
            else:
                rank = find_rank(items, item.object_id)
                in_3 = rank is not None and rank <= TOP_3
                in_5 = rank is not None and rank <= TOP_5

                result = QueryResult(
                    item_number=item.number,
                    level=level_key,
                    query=query,
                    rank=rank,
                    total_results=len(items),
                    in_top_3=in_3,
                    in_top_5=in_5,
                    latency_ms=latency_ms,
                )

                # Format rank display
                if rank is not None:
                    r3 = f"✓ #{rank}" if in_3 else f"✗ #{rank}"
                    r5 = f"✓ #{rank}" if in_5 else f"✗ #{rank}"
                else:
                    r3 = "✗ MISS"
                    r5 = "✗ MISS"

                status = f"  @3: {r3:<8}  @5: {r5:<8}  ({len(items)} results, {latency_ms}ms)"

            print(f"  {level_key} {query[:60]:<60} {status}")
            results.append(result)

            # Progress
            sys.stdout.flush()

            # Delay between queries
            if completed < total:
                time.sleep(QUERY_DELAY_S)

    return results


# ============================================================================
# Reporting
# ============================================================================

def print_summary(results: List[QueryResult]):
    """Print summary tables — pure math, no spin."""

    print("\n")
    print("=" * 78)
    print("  SUMMARY BY LITERACY LEVEL")
    print("=" * 78)

    for level_key, level_name in LEVELS.items():
        level_results = [r for r in results if r.level == level_key and r.error is None]
        n = len(level_results)
        if n == 0:
            continue

        at3 = sum(1 for r in level_results if r.in_top_3)
        at5 = sum(1 for r in level_results if r.in_top_5)

        pct3 = (at3 / n) * 100
        pct5 = (at5 / n) * 100

        print(f"  {level_key} ({level_name:<20}):  "
              f"@3: {at3:>2}/{n} ({pct3:5.1f}%)   "
              f"@5: {at5:>2}/{n} ({pct5:5.1f}%)")

    # ── Per-item summary ────────────────────────────────────────────
    print("\n")
    print("=" * 78)
    print("  SUMMARY BY ITEM")
    print("=" * 78)

    for item in GROUND_TRUTH:
        item_results = [r for r in results
                        if r.item_number == item.number and r.error is None]
        n = len(item_results)
        if n == 0:
            continue

        at3 = sum(1 for r in item_results if r.in_top_3)
        at5 = sum(1 for r in item_results if r.in_top_5)

        pct3 = (at3 / n) * 100
        pct5 = (at5 / n) * 100

        tag = f"#{item.number:<2} {item.name[:35]:<35}"
        print(f"  {tag}  @3: {at3}/{n} ({pct3:5.1f}%)   @5: {at5}/{n} ({pct5:5.1f}%)")

    # ── Bias detection ──────────────────────────────────────────────
    print("\n")
    print("=" * 78)
    print("  BIAS DETECTION — Pure Math")
    print("=" * 78)

    level_pcts: Dict[str, Tuple[float, float]] = {}
    for level_key in LEVELS:
        level_results = [r for r in results if r.level == level_key and r.error is None]
        n = len(level_results)
        if n == 0:
            continue
        pct3 = (sum(1 for r in level_results if r.in_top_3) / n) * 100
        pct5 = (sum(1 for r in level_results if r.in_top_5) / n) * 100
        level_pcts[level_key] = (pct3, pct5)

    if "L1" in level_pcts and "L5" in level_pcts:
        gap3 = level_pcts["L1"][0] - level_pcts["L5"][0]
        gap5 = level_pcts["L1"][1] - level_pcts["L5"][1]
        print(f"  L1 @3 - L5 @3 gap: {gap3:+.1f}%")
        print(f"  L1 @5 - L5 @5 gap: {gap5:+.1f}%")
        print()
        if abs(gap3) > 30:
            print(f"  WARNING: @3 gap exceeds 30% — investigate L5 query quality")
        else:
            print(f"  @3 gap within 30% threshold")
        if abs(gap5) > 30:
            print(f"  WARNING: @5 gap exceeds 30% — investigate L5 query quality")
        else:
            print(f"  @5 gap within 30% threshold")

    # ── Error summary ───────────────────────────────────────────────
    errors = [r for r in results if r.error is not None]
    if errors:
        print(f"\n  ERRORS: {len(errors)} queries failed")
        for r in errors:
            print(f"    #{r.item_number} {r.level}: {r.error}")

    # ── Overall ─────────────────────────────────────────────────────
    valid = [r for r in results if r.error is None]
    n = len(valid)
    if n > 0:
        overall_3 = sum(1 for r in valid if r.in_top_3)
        overall_5 = sum(1 for r in valid if r.in_top_5)
        avg_latency = sum(r.latency_ms for r in valid) / n

        print("\n")
        print("=" * 78)
        print("  OVERALL")
        print("=" * 78)
        print(f"  Total queries:    {n}")
        print(f"  @3 pass rate:     {overall_3}/{n} ({(overall_3/n)*100:.1f}%)")
        print(f"  @5 pass rate:     {overall_5}/{n} ({(overall_5/n)*100:.1f}%)")
        print(f"  Avg latency:      {avg_latency:.0f}ms")
        print(f"  Errors:           {len(errors)}")


# ============================================================================
# Main
# ============================================================================

def main():
    # ── Preflight ───────────────────────────────────────────────────
    if not JWT_TOKEN:
        print("ERROR: JWT_TOKEN environment variable is required.")
        print("  Extract from browser dev tools → Application → Cookies → sb-access-token")
        print("  Or from Supabase dashboard → API Settings")
        print()
        print("  export JWT_TOKEN='eyJ...'")
        print("  export API_BASE_URL='https://your-api.onrender.com'")
        print("  python3 test/ground_truth_search.py")
        sys.exit(1)

    total_queries = len(GROUND_TRUTH) * len(LEVELS)
    estimated_time = total_queries * QUERY_DELAY_S

    print("=" * 78)
    print("  GROUND TRUTH SEARCH VALIDATION")
    print("=" * 78)
    print(f"  Date:          {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"  API:           {API_BASE_URL}")
    print(f"  Yacht:         {YACHT_ID[:8]}...")
    print(f"  Items:         {len(GROUND_TRUTH)}")
    print(f"  Queries:       {total_queries}")
    print(f"  Ranking:       @3 (top 3) and @5 (top 5)")
    print(f"  Est. time:     ~{estimated_time/60:.1f} min ({QUERY_DELAY_S}s delay)")
    print(f"  Bias policy:   NONE — vague in = vague out")
    print("=" * 78)

    # ── Run ─────────────────────────────────────────────────────────
    results = run_all_queries()

    # ── Report ──────────────────────────────────────────────────────
    print_summary(results)

    print("\n" + "=" * 78)
    print("  END OF REPORT")
    print("=" * 78)


if __name__ == "__main__":
    main()
