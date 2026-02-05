#!/usr/bin/env python3
"""
Stage-1 Merge - Hard Tiers Post-Processing

Applies deterministic tier-based sorting to hyper_search_multi results.
This replaces the previous "magic math" domain weight boosts with a
transparent, predictable ranking system.

Hard Tiers ORDER BY (as implemented in RPC):
    1. exact_id_match (TRUE first)
    2. explicit_domain_match (TRUE first)
    3. recency_ts DESC
    4. text_score DESC

This module provides post-processing for:
    1. Email thread collapsing (keep highest scorer per thread)
    2. Tier annotation passthrough for debugging/transparency
    3. Final sorting verification

See: docs/HARD_TIERS_SPEC.md
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Tuple

logger = logging.getLogger(__name__)


# =============================================================================
# Email Thread Collapsing
# =============================================================================

def collapse_by_thread(items: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], int]:
    """
    Collapse email results by thread_id, keeping highest scorer.

    When multiple emails from the same thread appear in results,
    only show the highest-scoring one to reduce noise.

    Args:
        items: Search results (may include emails with thread_id in payload)

    Returns:
        Tuple of (collapsed_items, collapse_count)
    """
    threads_seen: Dict[str, Dict[str, Any]] = {}
    result: List[Dict[str, Any]] = []
    collapsed = 0

    for item in items:
        if item.get('object_type') != 'email':
            result.append(item)
            continue

        # Get thread_id from payload
        payload = item.get('payload') or {}
        thread_id = payload.get('thread_id')

        if not thread_id:
            # No thread_id, include as-is
            result.append(item)
            continue

        # Use fused_score for comparison (preserved from RPC)
        score = item.get('fused_score') or 0

        if thread_id not in threads_seen:
            # First email from this thread
            threads_seen[thread_id] = item
            result.append(item)
        elif score > (threads_seen[thread_id].get('fused_score') or 0):
            # Higher scorer replaces existing
            result.remove(threads_seen[thread_id])
            threads_seen[thread_id] = item
            result.append(item)
            collapsed += 1
        else:
            # Lower scorer, skip
            collapsed += 1

    return result, collapsed


# =============================================================================
# Tier Sort Key
# =============================================================================

def tier_sort_key(item: Dict[str, Any]) -> tuple:
    """
    Generate sort key for Hard Tiers ordering.

    The RPC already sorts by this order, but we re-apply after
    thread collapse to maintain correct ordering.

    ORDER BY:
        1. exact_id_match DESC (TRUE=0, FALSE=1)
        2. explicit_domain_match DESC (TRUE=0, FALSE=1)
        3. recency_ts DESC (newer first, NULL last)
        4. fused_score DESC (higher first)

    Returns tuple for sorting (lower = better rank).
    """
    # Exact ID match: TRUE sorts first
    exact_id = 0 if item.get('exact_id_match') else 1

    # Explicit domain match: TRUE sorts first
    explicit_domain = 0 if item.get('explicit_domain_match') else 1

    # Recency: newer is better, NULL is worst
    recency_ts = item.get('recency_ts')
    if recency_ts is None:
        # NULL recency goes to the end
        recency_sort = datetime.min.replace(tzinfo=timezone.utc)
    elif isinstance(recency_ts, str):
        try:
            if recency_ts.endswith('Z'):
                recency_ts = recency_ts[:-1] + '+00:00'
            recency_sort = datetime.fromisoformat(recency_ts)
        except (ValueError, TypeError):
            recency_sort = datetime.min.replace(tzinfo=timezone.utc)
    elif isinstance(recency_ts, datetime):
        recency_sort = recency_ts
    else:
        recency_sort = datetime.min.replace(tzinfo=timezone.utc)

    # Negate for DESC sort (more recent = lower sort key)
    recency_ordinal = -recency_sort.timestamp() if recency_sort else float('inf')

    # Fused score: higher is better (negate for DESC)
    fused_score = -(item.get('fused_score') or 0)

    return (exact_id, explicit_domain, recency_ordinal, fused_score)


# =============================================================================
# Tier Annotation
# =============================================================================

def compute_tier(item: Dict[str, Any]) -> int:
    """
    Compute display tier (1-4) for UI presentation.

    Tier 1: Exact ID match
    Tier 2: Explicit domain match (no exact ID)
    Tier 3: Recent (within 30 days, no exact/explicit match)
    Tier 4: Everything else
    """
    if item.get('exact_id_match'):
        return 1

    if item.get('explicit_domain_match'):
        return 2

    # Check recency for tier 3
    recency_ts = item.get('recency_ts')
    if recency_ts:
        try:
            if isinstance(recency_ts, str):
                if recency_ts.endswith('Z'):
                    recency_ts = recency_ts[:-1] + '+00:00'
                dt = datetime.fromisoformat(recency_ts)
            elif isinstance(recency_ts, datetime):
                dt = recency_ts
            else:
                dt = None

            if dt:
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                now = datetime.now(timezone.utc)
                days_old = (now - dt).days
                if days_old <= 30:
                    return 3
        except (ValueError, TypeError):
            pass

    return 4


def build_explain(item: Dict[str, Any], tier: int) -> Dict[str, Any]:
    """
    Build explain dict for SSE payload transparency.

    Returns:
        {
            tier: 1-4,
            reasons: ['exact_id_match', 'recent_7d', ...],
            scores: {trigram: 0.85, vector: 0.72, fused: 0.78},
            flags: {exact_id: True, explicit_domain: False, ...}
        }
    """
    reasons = []

    # Tier reasons
    if item.get('exact_id_match'):
        reasons.append('exact_id_match')
    if item.get('explicit_domain_match'):
        reasons.append('explicit_domain_match')

    # Recency reasons
    recency_ts = item.get('recency_ts')
    if recency_ts:
        try:
            if isinstance(recency_ts, str):
                if recency_ts.endswith('Z'):
                    recency_ts = recency_ts[:-1] + '+00:00'
                dt = datetime.fromisoformat(recency_ts)
            elif isinstance(recency_ts, datetime):
                dt = recency_ts
            else:
                dt = None

            if dt:
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                now = datetime.now(timezone.utc)
                days_old = (now - dt).days
                if days_old <= 7:
                    reasons.append('recent_7d')
                elif days_old <= 30:
                    reasons.append('recent_30d')
        except (ValueError, TypeError):
            pass

    # Score reasons
    trigram_score = item.get('trigram_score') or 0
    vector_score = item.get('vector_score') or 0

    if trigram_score >= 0.85:
        reasons.append('strong_text_match')
    elif trigram_score >= 0.30:
        reasons.append('text_match')

    if vector_score >= 0.85:
        reasons.append('strong_semantic_match')
    elif vector_score >= 0.75:
        reasons.append('semantic_match')

    return {
        'tier': tier,
        'reasons': reasons,
        'scores': {
            'trigram': round(trigram_score, 3),
            'vector': round(vector_score, 3),
            'fused': round(item.get('fused_score') or 0, 3),
        },
        'flags': {
            'exact_id': bool(item.get('exact_id_match')),
            'explicit_domain': bool(item.get('explicit_domain_match')),
            'has_recency': recency_ts is not None,
        }
    }


def annotate_tiers(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Add tier annotations to items for debugging and transparency.

    Adds:
        - tier: 1-4 tier level
        - tier_reason: human-readable explanation
        - explain: detailed dict for SSE payload
    """
    tier_reasons = {
        1: 'exact_id_match',
        2: 'explicit_domain_match',
        3: 'recent_30d',
        4: 'relevance_score',
    }

    for item in items:
        tier = compute_tier(item)
        item['tier'] = tier
        item['tier_reason'] = tier_reasons[tier]
        item['explain'] = build_explain(item, tier)

    return items


# =============================================================================
# Main Stage-1 Merge Function
# =============================================================================

def stage1_merge(
    items: List[Dict[str, Any]],
    query: str,
    enable_thread_collapse: bool = True,
    # Legacy parameters (no longer used, kept for API compatibility)
    enable_domain_weights: bool = False,  # DEPRECATED - Hard Tiers replaces this
    enable_recency_boost: bool = False,   # DEPRECATED - recency_ts in RPC replaces this
    recency_decay: float = 0.9,           # DEPRECATED
    recency_window_days: int = 7,         # DEPRECATED
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Apply Stage-1 merge transformations to search results.

    Post-processes hyper_search_multi results with:
        1. Email thread collapsing
        2. Tier annotations
        3. Hard Tiers sort verification

    NOTE: Domain weights and recency boost are DEPRECATED.
    The RPC now handles deterministic tier-based sorting via:
        ORDER BY exact_id_match, explicit_domain_match, recency_ts, fused_score

    Args:
        items: Raw search results from hyper_search_multi
        query: Original search query (for logging)
        enable_thread_collapse: Dedupe emails by thread

    Returns:
        Tuple of (merged_items, metadata)
    """
    if not items:
        return [], {
            'stage1_applied': True,
            'hard_tiers': True,
            'input_count': 0,
            'output_count': 0,
        }

    metadata = {
        'stage1_applied': True,
        'hard_tiers': True,
        'input_count': len(items),
        'threads_collapsed': 0,
        'tier_distribution': {1: 0, 2: 0, 3: 0, 4: 0},
    }

    # Warn if legacy flags are enabled (they no longer do anything)
    if enable_domain_weights:
        logger.warning(
            "[Stage1Merge] enable_domain_weights is DEPRECATED - "
            "Hard Tiers replaces magic weight boosts"
        )
    if enable_recency_boost:
        logger.warning(
            "[Stage1Merge] enable_recency_boost is DEPRECATED - "
            "RPC now uses recency_ts for tier sorting"
        )

    # Step 1: Collapse email threads
    collapsed_count = 0
    if enable_thread_collapse:
        items, collapsed_count = collapse_by_thread(items)
        metadata['threads_collapsed'] = collapsed_count

    # Step 2: Annotate tiers for transparency
    items = annotate_tiers(items)

    # Count tier distribution
    for item in items:
        tier = item.get('tier', 4)
        metadata['tier_distribution'][tier] = metadata['tier_distribution'].get(tier, 0) + 1

    # Step 3: Re-sort by Hard Tiers (verifies RPC ordering after collapse)
    items.sort(key=tier_sort_key)

    metadata['output_count'] = len(items)

    logger.info(
        f"[Stage1Merge] Hard Tiers: in={metadata['input_count']}, "
        f"out={metadata['output_count']}, collapsed={collapsed_count}, "
        f"tiers={metadata['tier_distribution']}"
    )

    return items, metadata


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    'stage1_merge',
    'collapse_by_thread',
    'tier_sort_key',
    'compute_tier',
    'annotate_tiers',
]
