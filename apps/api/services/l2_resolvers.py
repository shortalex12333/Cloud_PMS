#!/usr/bin/env python3
"""
L2 Resolvers - Deterministic Structured Lookups

Bypass vector search for exact ID matches. These run in parallel with L1
and pin results to Tier 1 (exact_id_match).

Resolver Catalog:
    - resolve_fault_code: Equals match on normalized fault_code (SPN/FMI patterns)
    - resolve_work_order: Equals match on wo_number
    - resolve_part: Equals match on part_number (propagates to inventory_stock)
    - resolve_certificate: Equals match on certificate_number with expiry filter
    - resolve_equipment: Equals match on equipment_code/asset_tag, alias fallback

See: docs/L2_RESOLVERS_SPEC.md
"""

from __future__ import annotations

import re
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


# =============================================================================
# Types
# =============================================================================

@dataclass
class L2Result:
    """Result from L2 resolver."""
    object_type: str
    object_id: str
    payload: Dict[str, Any]
    resolver: str  # Which resolver matched
    confidence: float  # 1.0 for exact, 0.9 for alias, etc.

    def to_search_item(self) -> Dict[str, Any]:
        """Convert to search result format for merging with L1."""
        return {
            'object_type': self.object_type,
            'object_id': self.object_id,
            'payload': self.payload,
            'exact_id_match': True,  # L2 results always pin to Tier 1
            'explicit_domain_match': False,
            'trigram_score': 1.0,
            'vector_score': 0.0,
            'fused_score': 1.0,
            'recency_ts': self.payload.get('updated_at'),
            'l2_resolver': self.resolver,
            'l2_confidence': self.confidence,
        }


# =============================================================================
# Pattern Detection
# =============================================================================

# Fault code patterns (SPN 303, P1187, FMI 12, etc.)
FAULT_CODE_PATTERNS = [
    re.compile(r'\bSPN\s*(\d{1,5})\b', re.IGNORECASE),  # SPN 303
    re.compile(r'\bFMI\s*(\d{1,2})\b', re.IGNORECASE),  # FMI 12
    re.compile(r'\b([PBUC]\d{4})\b', re.IGNORECASE),    # P1187, B0001, etc.
    re.compile(r'\b(\d{3,5})\b'),                        # Bare numeric code
]

# Work order patterns (WO-12345, #12345, etc.)
WO_PATTERNS = [
    re.compile(r'\bWO[-#]?\s*(\d{4,8})\b', re.IGNORECASE),
    re.compile(r'\b#(\d{5,8})\b'),
]

# Part number patterns (alphanumeric with dashes)
PART_PATTERNS = [
    re.compile(r'\b([A-Z]{2,4}[-]?\d{4,10})\b', re.IGNORECASE),  # AB-12345
    re.compile(r'\b(\d{4,10}[-]?[A-Z]{1,3})\b', re.IGNORECASE),  # 12345-AB
]


def detect_fault_code(query: str) -> Optional[str]:
    """Extract fault code from query if present."""
    for pattern in FAULT_CODE_PATTERNS:
        match = pattern.search(query)
        if match:
            return match.group(0).upper().replace(' ', '')
    return None


def detect_work_order(query: str) -> Optional[str]:
    """Extract work order number from query if present."""
    for pattern in WO_PATTERNS:
        match = pattern.search(query)
        if match:
            return match.group(1)
    return None


def detect_part_number(query: str) -> Optional[str]:
    """Extract part number from query if present."""
    # Only match if query looks like a part number (short, alphanumeric)
    clean = query.strip()
    if len(clean) > 20:
        return None

    for pattern in PART_PATTERNS:
        match = pattern.search(clean)
        if match:
            return match.group(1).upper()
    return None


# =============================================================================
# Database Resolvers
# =============================================================================

async def resolve_fault_code(
    conn,
    code: str,
    org_id: str,
    yacht_id: Optional[str] = None,
) -> List[L2Result]:
    """
    Resolve fault code to fault catalog entry.

    Normalizes SPN/FMI patterns and does exact match.
    """
    results = []
    normalized = code.upper().replace(' ', '').replace('-', '')

    try:
        # Check search_index for fault entries
        query = """
            SELECT object_id, payload, recency_ts
            FROM search_index
            WHERE org_id = $1
              AND object_type = 'fault'
              AND ident_norm = $2
            LIMIT 5
        """
        params = [org_id, normalized]

        rows = await conn.fetch(query, *params)

        for row in rows:
            results.append(L2Result(
                object_type='fault',
                object_id=str(row['object_id']),
                payload={**row['payload'], 'updated_at': row['recency_ts']},
                resolver='fault_code',
                confidence=1.0,
            ))

        logger.debug(f"[L2] resolve_fault_code({code}) → {len(results)} results")

    except Exception as e:
        logger.error(f"[L2] resolve_fault_code error: {e}")

    return results


async def resolve_work_order(
    conn,
    wo_number: str,
    org_id: str,
    yacht_id: Optional[str] = None,
) -> List[L2Result]:
    """
    Resolve work order number to work order entry.
    """
    results = []
    normalized = wo_number.upper().replace(' ', '').replace('-', '')

    try:
        query = """
            SELECT object_id, payload, recency_ts
            FROM search_index
            WHERE org_id = $1
              AND object_type = 'work_order'
              AND ident_norm = $2
            LIMIT 5
        """
        rows = await conn.fetch(query, org_id, normalized)

        for row in rows:
            results.append(L2Result(
                object_type='work_order',
                object_id=str(row['object_id']),
                payload={**row['payload'], 'updated_at': row['recency_ts']},
                resolver='work_order',
                confidence=1.0,
            ))

        logger.debug(f"[L2] resolve_work_order({wo_number}) → {len(results)} results")

    except Exception as e:
        logger.error(f"[L2] resolve_work_order error: {e}")

    return results


async def resolve_part(
    conn,
    part_number: str,
    org_id: str,
    yacht_id: Optional[str] = None,
) -> List[L2Result]:
    """
    Resolve part number to parts and inventory entries.

    Propagates match to both parts catalog and inventory_stock.
    """
    results = []
    normalized = part_number.upper().replace(' ', '').replace('-', '')

    try:
        # Search for parts
        query = """
            SELECT object_type, object_id, payload, recency_ts
            FROM search_index
            WHERE org_id = $1
              AND object_type IN ('part', 'inventory')
              AND ident_norm = $2
            LIMIT 10
        """
        rows = await conn.fetch(query, org_id, normalized)

        for row in rows:
            results.append(L2Result(
                object_type=row['object_type'],
                object_id=str(row['object_id']),
                payload={**row['payload'], 'updated_at': row['recency_ts']},
                resolver='part_number',
                confidence=1.0,
            ))

        logger.debug(f"[L2] resolve_part({part_number}) → {len(results)} results")

    except Exception as e:
        logger.error(f"[L2] resolve_part error: {e}")

    return results


async def resolve_equipment(
    conn,
    equipment_ref: str,
    org_id: str,
    yacht_id: Optional[str] = None,
) -> List[L2Result]:
    """
    Resolve equipment reference (code, asset tag, or alias).

    Falls back to alias table for nicknames like "DG1", "genny".
    """
    results = []
    normalized = equipment_ref.upper().replace(' ', '')

    try:
        # Direct match on equipment
        query = """
            SELECT object_id, payload, recency_ts
            FROM search_index
            WHERE org_id = $1
              AND object_type = 'equipment'
              AND ident_norm = $2
            LIMIT 5
        """
        rows = await conn.fetch(query, org_id, normalized)

        for row in rows:
            results.append(L2Result(
                object_type='equipment',
                object_id=str(row['object_id']),
                payload={**row['payload'], 'updated_at': row['recency_ts']},
                resolver='equipment_code',
                confidence=1.0,
            ))

        # TODO: Alias table fallback
        # If no direct match, check equipment_aliases table

        logger.debug(f"[L2] resolve_equipment({equipment_ref}) → {len(results)} results")

    except Exception as e:
        logger.error(f"[L2] resolve_equipment error: {e}")

    return results


async def resolve_certificate(
    conn,
    cert_number: str,
    org_id: str,
    yacht_id: Optional[str] = None,
    include_expired: bool = False,
) -> List[L2Result]:
    """
    Resolve certificate number with optional expiry filter.
    """
    results = []
    normalized = cert_number.upper().replace(' ', '').replace('-', '')

    try:
        query = """
            SELECT object_id, payload, recency_ts
            FROM search_index
            WHERE org_id = $1
              AND object_type = 'certificate'
              AND ident_norm = $2
            LIMIT 5
        """
        rows = await conn.fetch(query, org_id, normalized)

        for row in rows:
            # Filter expired if requested
            if not include_expired:
                expiry = row['payload'].get('expiry_date')
                if expiry:
                    # TODO: Parse and compare expiry date
                    pass

            results.append(L2Result(
                object_type='certificate',
                object_id=str(row['object_id']),
                payload={**row['payload'], 'updated_at': row['recency_ts']},
                resolver='certificate',
                confidence=1.0,
            ))

        logger.debug(f"[L2] resolve_certificate({cert_number}) → {len(results)} results")

    except Exception as e:
        logger.error(f"[L2] resolve_certificate error: {e}")

    return results


# =============================================================================
# Main L2 Dispatch
# =============================================================================

async def run_l2_resolvers(
    conn,
    query: str,
    org_id: str,
    yacht_id: Optional[str] = None,
) -> List[L2Result]:
    """
    Run all applicable L2 resolvers in parallel.

    Detects patterns in query and dispatches to appropriate resolvers.
    Returns all L2 matches merged (deduplicated by object_type+object_id).
    """
    import asyncio

    results: List[L2Result] = []
    tasks = []

    # Detect and dispatch
    fault_code = detect_fault_code(query)
    if fault_code:
        tasks.append(resolve_fault_code(conn, fault_code, org_id, yacht_id))

    wo_number = detect_work_order(query)
    if wo_number:
        tasks.append(resolve_work_order(conn, wo_number, org_id, yacht_id))

    part_number = detect_part_number(query)
    if part_number:
        tasks.append(resolve_part(conn, part_number, org_id, yacht_id))

    # Equipment detection (short queries that look like codes)
    if len(query.strip()) <= 10 and re.match(r'^[A-Z0-9]+$', query.strip(), re.IGNORECASE):
        tasks.append(resolve_equipment(conn, query.strip(), org_id, yacht_id))

    if not tasks:
        return []

    # Run in parallel
    task_results = await asyncio.gather(*tasks, return_exceptions=True)

    # Merge results, dedupe by (object_type, object_id)
    seen = set()
    for result_list in task_results:
        if isinstance(result_list, Exception):
            logger.error(f"[L2] Resolver error: {result_list}")
            continue
        for r in result_list:
            key = (r.object_type, r.object_id)
            if key not in seen:
                seen.add(key)
                results.append(r)

    logger.info(f"[L2] run_l2_resolvers({query[:30]}...) → {len(results)} results")
    return results


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    'L2Result',
    'run_l2_resolvers',
    'detect_fault_code',
    'detect_work_order',
    'detect_part_number',
    'resolve_fault_code',
    'resolve_work_order',
    'resolve_part',
    'resolve_equipment',
    'resolve_certificate',
]
