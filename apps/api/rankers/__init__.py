"""
F1 Search - Rankers Module

Optional re-ranking components for search results.
Lazy-loaded to avoid import failures if model is missing.
"""

import os
import logging

logger = logging.getLogger(__name__)

_reranker_loaded = False
_rerank_fn = None


def get_rerank():
    """Lazy-load reranker to avoid import failure if model missing."""
    global _reranker_loaded, _rerank_fn

    if _reranker_loaded:
        return _rerank_fn

    _reranker_loaded = True

    try:
        from .onnx_reranker import rerank
        _rerank_fn = rerank
        logger.info("[Rankers] ONNX reranker loaded")
    except Exception as e:
        logger.warning(f"[Rankers] ONNX reranker not available: {e}")
        _rerank_fn = None

    return _rerank_fn


def rerank(query: str, items: list, top_k: int = 10, budget_ms: int = 80) -> list:
    """
    Re-rank items if reranker is available, else return original.

    GUARDRAILS:
    - If model not loaded, returns items unchanged
    - If budget exceeded, returns items unchanged
    """
    fn = get_rerank()
    if fn is None:
        return items
    return fn(query, items, top_k=top_k, budget_ms=budget_ms)


def is_reranker_available() -> bool:
    """Check if reranker is available."""
    return get_rerank() is not None


__all__ = ["rerank", "is_reranker_available"]
