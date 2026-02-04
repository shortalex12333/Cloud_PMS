#!/usr/bin/env python3
"""
F1 Search - ONNX Re-ranker

Cross-encoder re-ranking using TinyBERT MSMARCO model.
Behind flag - disabled by default.

GUARDRAILS:
- Budget: 80ms. If >80ms, return original order (RRF-only).
- Do NOT block SSE emission.
- Single-threaded to avoid CPU contention.

Usage:
    from rankers.onnx_reranker import rerank
    if RERANKER_ENABLED and len(items) > 1:
        items = rerank(q, items, top_k=10, budget_ms=80)
"""

import os
import time

import numpy as np
import onnxruntime as ort
from transformers import AutoTokenizer

# ============================================================================
# Model Configuration
# ============================================================================

MODEL_DIR = os.getenv("RERANKER_MODEL_DIR", "models")
MODEL_PATH = os.path.join(MODEL_DIR, "msmarco-tinybert-l2-v2-int8.onnx")

# Single-threaded ONNX session to avoid CPU contention
so = ort.SessionOptions()
so.intra_op_num_threads = 1
so.inter_op_num_threads = 1

sess = ort.InferenceSession(MODEL_PATH, sess_options=so, providers=["CPUExecutionProvider"])
tokenizer = AutoTokenizer.from_pretrained("cross-encoder/ms-marco-TinyBERT-L-2-v2")


# ============================================================================
# Re-ranking Function
# ============================================================================

def rerank(query: str, items: list[dict], top_k: int = 10, budget_ms: int = 80) -> list[dict]:
    """
    Re-rank search results using cross-encoder model.

    GUARDRAILS:
    - Budget: budget_ms (default 80ms)
    - If >budget_ms, returns original order (RRF-only)
    - Does NOT block SSE emission

    Args:
        query: Search query
        items: List of result dicts
        top_k: Max items to re-rank (default 10)
        budget_ms: Max time budget (default 80ms)

    Returns:
        Re-ranked list with "rerank_score" added to each item.
        Falls back to original order if timeout exceeded.
    """
    if not items:
        return items

    # Build query-passage pairs
    pairs = [
        (query, it.get("title") or it.get("payload", {}).get("name") or str(it.get("object_id")))
        for it in items[:top_k]
    ]

    # Tokenize
    encoded = tokenizer.batch_encode_plus(
        pairs,
        padding=True,
        truncation=True,
        max_length=256,
        return_tensors="np"
    )

    # Build inputs
    inputs = {
        "input_ids": encoded["input_ids"].astype(np.int64),
        "attention_mask": encoded["attention_mask"].astype(np.int64),
        # Some ONNX exports require token_type_ids; provide zeros if missing
        "token_type_ids": np.zeros_like(encoded["input_ids"], dtype=np.int64),
    }

    # Run inference with timing
    t0 = time.perf_counter()
    logits = sess.run(None, inputs)[0].squeeze(-1)
    dt = (time.perf_counter() - t0) * 1000

    if dt > budget_ms:
        # Over budget; return original order (RRF-only)
        return items[:top_k]

    # Higher logits = more relevant
    scored = []
    for it, logit in zip(items[:top_k], logits.tolist()):
        it2 = dict(it)
        it2["rerank_score"] = float(logit)
        scored.append(it2)

    scored.sort(key=lambda x: x["rerank_score"], reverse=True)
    return scored


# ============================================================================
# Exports
# ============================================================================

__all__ = ["rerank"]
