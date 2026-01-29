"""
Shadow Logging for V2 Embedding Re-Ranking

Logs cosine similarity metrics without affecting ordering.
Used to validate re-ranking before enabling in production.

Features:
- Compute cosine scores but don't alter order (alpha=0.0)
- Log aggregate stats (avg cosine, top-N deltas, distribution)
- No entity text in logs (only IDs and scores)
- Feature flag: SHOW_RELATED_SHADOW=true

Usage:
    from services.embedding_shadow_logger import shadow_log_rerank_scores

    shadow_log_rerank_scores(
        groups=groups,
        focused_embedding=focused_embedding,
        yacht_id=yacht_id,
        entity_type=entity_type,
        entity_id=entity_id
    )
"""

import os
import logging
from typing import List, Dict, Any, Optional
import statistics

logger = logging.getLogger('EmbeddingShadow')

# Feature flag
SHADOW_LOGGING_ENABLED = os.getenv('SHOW_RELATED_SHADOW', 'false').lower() == 'true'


def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """
    Compute cosine similarity between two vectors.

    Args:
        vec1: First vector
        vec2: Second vector

    Returns:
        Cosine similarity (-1.0 to 1.0)
    """
    if not vec1 or not vec2:
        return 0.0

    if len(vec1) != len(vec2):
        logger.warning(f"Vector dimension mismatch: {len(vec1)} vs {len(vec2)}")
        return 0.0

    # Dot product
    dot_product = sum(a * b for a, b in zip(vec1, vec2))

    # Magnitudes
    mag1 = sum(a * a for a in vec1) ** 0.5
    mag2 = sum(b * b for b in vec2) ** 0.5

    if mag1 == 0 or mag2 == 0:
        return 0.0

    return dot_product / (mag1 * mag2)


def shadow_log_rerank_scores(
    groups: List[Dict[str, Any]],
    focused_embedding: Optional[List[float]],
    yacht_id: str,
    entity_type: str,
    entity_id: str,
    alpha: float = 0.0
) -> None:
    """
    Log re-rank metrics in shadow mode without affecting order.

    Args:
        groups: Groups from get_related response
        focused_embedding: Embedding of focused entity (or None)
        yacht_id: Yacht ID (for isolation in logs)
        entity_type: Type of focused entity
        entity_id: ID of focused entity
        alpha: Alpha value (for simulation)
    """
    if not SHADOW_LOGGING_ENABLED:
        return

    if not focused_embedding:
        logger.debug(f"[SHADOW] No focused embedding for {entity_type}:{entity_id[:8]}...")
        return

    all_scores = []
    group_stats = {}

    for group in groups:
        group_key = group.get('group_key', 'unknown')
        items = group.get('items', [])

        if not items:
            continue

        cosine_scores = []
        fk_deltas = []

        for item in items:
            item_embedding = item.get('embedding')
            fk_weight = item.get('weight', 0)

            if not item_embedding:
                continue

            # Compute cosine similarity
            cosine = cosine_similarity(focused_embedding, item_embedding)
            cosine_scores.append(cosine)
            all_scores.append(cosine)

            # Compute what the re-ranked score would be
            reranked_score = fk_weight + (alpha * 100 * cosine)
            delta = reranked_score - fk_weight

            fk_deltas.append({
                'entity_id': item['entity_id'][:8] + '...',  # Truncated for privacy
                'fk_weight': fk_weight,
                'cosine': cosine,
                'would_be_score': reranked_score,
                'delta': delta
            })

        # Aggregate stats for this group
        if cosine_scores:
            group_stats[group_key] = {
                'count': len(cosine_scores),
                'avg_cosine': statistics.mean(cosine_scores),
                'max_cosine': max(cosine_scores),
                'min_cosine': min(cosine_scores),
                'median_cosine': statistics.median(cosine_scores),
                'top_3_deltas': sorted(fk_deltas, key=lambda x: x['delta'], reverse=True)[:3]
            }

    # Overall stats
    if all_scores:
        overall_stats = {
            'total_items_with_embeddings': len(all_scores),
            'avg_cosine': statistics.mean(all_scores),
            'max_cosine': max(all_scores),
            'min_cosine': min(all_scores),
            'median_cosine': statistics.median(all_scores),
            'stdev_cosine': statistics.stdev(all_scores) if len(all_scores) > 1 else 0.0,
        }

        # Log structured summary
        logger.info(
            f"[SHADOW] entity={entity_type}:{entity_id[:8]}... "
            f"yacht={yacht_id[:8]}... "
            f"alpha={alpha} "
            f"items={overall_stats['total_items_with_embeddings']} "
            f"avg_cosine={overall_stats['avg_cosine']:.3f} "
            f"median={overall_stats['median_cosine']:.3f} "
            f"stdev={overall_stats['stdev_cosine']:.3f}"
        )

        # Log per-group stats
        for group_key, stats in group_stats.items():
            logger.info(
                f"[SHADOW]   {group_key}: "
                f"count={stats['count']} "
                f"avg={stats['avg_cosine']:.3f} "
                f"range=[{stats['min_cosine']:.3f}, {stats['max_cosine']:.3f}]"
            )

            # Log top deltas (what would change with re-ranking)
            for i, delta_info in enumerate(stats['top_3_deltas'], 1):
                logger.debug(
                    f"[SHADOW]     top_{i}: "
                    f"id={delta_info['entity_id']} "
                    f"fk={delta_info['fk_weight']} "
                    f"cosine={delta_info['cosine']:.3f} "
                    f"would_be={delta_info['would_be_score']:.1f} "
                    f"delta={delta_info['delta']:.1f}"
                )

    else:
        logger.debug(f"[SHADOW] No items with embeddings for {entity_type}:{entity_id[:8]}...")


def shadow_log_alpha_simulation(
    groups: List[Dict[str, Any]],
    focused_embedding: Optional[List[float]],
    yacht_id: str,
    entity_type: str,
    entity_id: str,
    alphas: List[float] = [0.0, 0.1, 0.3, 0.5, 1.0]
) -> None:
    """
    Simulate re-ranking with multiple alpha values (for A/B planning).

    Logs how ordering would change at different alpha values.

    Args:
        groups: Groups from get_related response
        focused_embedding: Embedding of focused entity
        yacht_id: Yacht ID
        entity_type: Type of focused entity
        entity_id: ID of focused entity
        alphas: Alpha values to simulate
    """
    if not SHADOW_LOGGING_ENABLED:
        return

    if not focused_embedding:
        return

    logger.info(f"[SHADOW-SIM] Alpha simulation for {entity_type}:{entity_id[:8]}...")

    for alpha in alphas:
        shadow_log_rerank_scores(
            groups=groups,
            focused_embedding=focused_embedding,
            yacht_id=yacht_id,
            entity_type=entity_type,
            entity_id=entity_id,
            alpha=alpha
        )


def compute_rerank_effectiveness(
    groups: List[Dict[str, Any]],
    focused_embedding: Optional[List[float]],
    alpha: float = 0.3
) -> Dict[str, Any]:
    """
    Compute re-ranking effectiveness metrics.

    Metrics:
    - How many items would change position?
    - What's the avg rank delta?
    - Would any items cross FK tier boundaries?

    Args:
        groups: Groups from get_related response
        focused_embedding: Embedding of focused entity
        alpha: Alpha value to simulate

    Returns:
        Dict with effectiveness metrics
    """
    if not focused_embedding:
        return {'error': 'no_focused_embedding'}

    all_items = []
    for group in groups:
        all_items.extend(group.get('items', []))

    if not all_items:
        return {'error': 'no_items'}

    # Compute FK-only ranking
    fk_ranking = sorted(enumerate(all_items), key=lambda x: x[1].get('weight', 0), reverse=True)

    # Compute re-ranked ranking
    reranked_items = []
    for idx, item in enumerate(all_items):
        fk_weight = item.get('weight', 0)
        item_embedding = item.get('embedding')

        if item_embedding:
            cosine = cosine_similarity(focused_embedding, item_embedding)
            final_score = fk_weight + (alpha * 100 * cosine)
        else:
            final_score = fk_weight

        reranked_items.append((idx, item, final_score))

    reranked_ranking = sorted(reranked_items, key=lambda x: x[2], reverse=True)

    # Compute position changes
    position_changes = []
    for new_pos, (orig_idx, item, _) in enumerate(reranked_ranking):
        # Find original position
        orig_pos = next(i for i, (idx, _) in enumerate(fk_ranking) if idx == orig_idx)

        if new_pos != orig_pos:
            position_changes.append({
                'entity_id': item['entity_id'][:8] + '...',
                'orig_pos': orig_pos,
                'new_pos': new_pos,
                'delta': new_pos - orig_pos
            })

    # Metrics
    metrics = {
        'total_items': len(all_items),
        'items_with_embeddings': sum(1 for item in all_items if item.get('embedding')),
        'items_changed_position': len(position_changes),
        'pct_changed': (len(position_changes) / len(all_items) * 100) if all_items else 0,
        'avg_rank_delta': (
            statistics.mean(abs(c['delta']) for c in position_changes)
            if position_changes else 0
        ),
        'max_rank_improvement': (
            max(c['delta'] for c in position_changes if c['delta'] < 0)
            if any(c['delta'] < 0 for c in position_changes) else 0
        ),
        'max_rank_demotion': (
            max(c['delta'] for c in position_changes if c['delta'] > 0)
            if any(c['delta'] > 0 for c in position_changes) else 0
        ),
    }

    return metrics
