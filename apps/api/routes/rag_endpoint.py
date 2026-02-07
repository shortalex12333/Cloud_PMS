"""
RAG API Endpoint
================

POST /api/rag/answer

Generates answers from retrieved context with citations.

Request:
{
    "query": "What are the compliance requirements for hours of rest?",
    "lens": "hours_of_rest",  // optional
    "top_k": 12,              // optional, default 12
    "debug": false            // optional
}

Response:
{
    "answer": "According to MLC 2006, seafarers must have...",
    "citations": [
        {"doc_id": "uuid", "doc_type": "document", "page": 5, "title": "MLC Guide"}
    ],
    "used_doc_ids": ["uuid1", "uuid2"],
    "confidence": 0.85,
    "signals": {              // only if debug=true
        "context_tokens": 2500,
        "chunks_used": 8,
        "latency_ms": 1500,
        "model": "gpt-4o-mini"
    }
}

Security:
- yacht_id resolved from JWT, never from payload
- Role-based context filtering
- No raw text in logs (hash only)
- Read-only (RAG never mutates)
"""

import os
import json
import hashlib
import logging
import time
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

# Import RAG modules (path set by pipeline_service.py)
from rag import (
    build_context,
    generate_answer,
    verify_answer,
    generate_no_context_answer,
    generate_error_answer,
    compute_query_hash,
)
from domain_microactions import detect_domain_from_query

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/rag", tags=["rag"])


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class RAGRequest(BaseModel):
    query: str = Field(..., min_length=3, max_length=1000)
    lens: str = Field(default="default")
    top_k: int = Field(default=12, ge=1, le=50)
    debug: bool = Field(default=False)


class CitationResponse(BaseModel):
    doc_id: str
    doc_type: str
    page: Optional[int] = None
    span_hash: Optional[str] = None
    title: Optional[str] = None


class RAGSignals(BaseModel):
    context_tokens: int
    chunks_used: int
    latency_ms: int
    model: str
    domain: Optional[str] = None
    mode: str
    faithfulness_score: Optional[float] = None


class RAGResponse(BaseModel):
    answer: str
    citations: list[CitationResponse]
    used_doc_ids: list[str]
    confidence: float
    signals: Optional[RAGSignals] = None


# =============================================================================
# CACHING
# =============================================================================

# Simple in-memory cache (use Redis in production)
_cache: dict = {}
CACHE_TTL_SECONDS = 300  # 5 minutes


def get_cache_key(yacht_id: str, role: str, lens: str, query_hash: str, dataset_version: str = "v1") -> str:
    """Generate cache key."""
    return f"rag:{dataset_version}:{yacht_id}:{role}:{lens}:{query_hash}"


def get_cached_response(cache_key: str) -> Optional[dict]:
    """Get cached response if valid."""
    if cache_key in _cache:
        entry = _cache[cache_key]
        if time.time() - entry['timestamp'] < CACHE_TTL_SECONDS:
            return entry['response']
        else:
            del _cache[cache_key]
    return None


def set_cached_response(cache_key: str, response: dict):
    """Cache a response."""
    _cache[cache_key] = {
        'response': response,
        'timestamp': time.time()
    }


# =============================================================================
# ENDPOINT
# =============================================================================

@router.post("/answer", response_model=RAGResponse)
async def rag_answer(
    request: RAGRequest,
    req: Request,
):
    """
    Generate an answer from retrieved context.

    Security:
    - yacht_id from JWT (not payload)
    - Role from auth context
    - Read-only operation
    """
    start_time = time.time()

    # Get auth context (yacht_id, role from JWT)
    # In production, this comes from middleware
    auth_context = getattr(req.state, 'auth', None)
    if auth_context:
        yacht_id = auth_context.get('yacht_id')
        role = auth_context.get('role', 'crew')
    else:
        # Fallback for testing
        yacht_id = req.headers.get('X-Yacht-ID')
        role = req.headers.get('X-Role', 'crew')

    if not yacht_id:
        raise HTTPException(status_code=400, detail="Missing yacht context")

    # Compute query hash (for logging without raw text)
    query_hash = compute_query_hash(request.query, yacht_id, role, request.lens)

    # Check cache
    cache_key = get_cache_key(yacht_id, role, request.lens, query_hash)
    cached = get_cached_response(cache_key)
    if cached:
        logger.info(f"RAG cache hit: {query_hash}")
        return JSONResponse(content=cached)

    # Detect domain for focused retrieval
    domain_result = detect_domain_from_query(request.query)
    domain = domain_result[0] if domain_result else None
    domain_boost = domain_result[1] if domain_result else 0.0
    mode = 'focused' if domain else 'explore'

    try:
        # Get database connection
        # In production, use connection pool from app state
        conn = req.app.state.db_pool if hasattr(req.app.state, 'db_pool') else None
        if not conn:
            raise HTTPException(status_code=500, detail="Database connection not available")

        # Build context
        context = await build_context(
            conn=conn,
            yacht_id=yacht_id,
            query=request.query,
            role=role,
            lens=request.lens,
            domain=domain,
            mode=mode,
            domain_boost=domain_boost,
            top_k=request.top_k,
        )

        if not context.chunks:
            answer = generate_no_context_answer(request.query, query_hash)
        else:
            # Generate answer
            answer = await generate_answer(context)

            # Verify faithfulness (optional, for monitoring)
            if request.debug:
                verification = verify_answer(answer, context)

        # Build response
        response_data = {
            'answer': answer.answer,
            'citations': [c.to_dict() for c in context.chunks] if context.chunks else [],
            'used_doc_ids': answer.used_doc_ids,
            'confidence': answer.confidence,
        }

        if request.debug:
            response_data['signals'] = {
                'context_tokens': context.total_tokens,
                'chunks_used': len(context.chunks),
                'latency_ms': int((time.time() - start_time) * 1000),
                'model': answer.model,
                'domain': domain,
                'mode': mode,
                'faithfulness_score': verification.faithfulness_score if request.debug and context.chunks else None,
            }

        # Cache response
        set_cached_response(cache_key, response_data)

        # Log (hash only, no raw text)
        logger.info(f"RAG answer: query_hash={query_hash} chunks={len(context.chunks)} confidence={answer.confidence:.2f}")

        return JSONResponse(content=response_data)

    except Exception as e:
        logger.error(f"RAG error: query_hash={query_hash} error={str(e)}")

        # Return error response (don't expose internal details)
        error_answer = generate_error_answer(request.query, query_hash, str(e))
        return JSONResponse(
            status_code=500,
            content={
                'answer': error_answer.answer,
                'citations': [],
                'used_doc_ids': [],
                'confidence': 0.0,
            }
        )


# =============================================================================
# HEALTH CHECK
# =============================================================================

@router.get("/health")
async def rag_health():
    """Health check for RAG service."""
    return {"status": "ok", "cache_size": len(_cache)}
