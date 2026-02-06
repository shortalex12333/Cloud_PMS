"""
RAG Answer Generator
====================

Generates answers from retrieved context using GPT with strict citation requirements.

Key principles:
1. Deterministic prompt with role, yacht, lens constraints
2. Every factual claim must cite a source
3. No guessing - only state what's in the context
4. Action safety note - RAG is read-only
"""

import json
import os
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import openai

from .context_builder import RAGContext, Citation


@dataclass
class RAGAnswer:
    """Generated answer with citations and confidence."""
    answer: str
    citations: List[Dict[str, Any]]
    used_doc_ids: List[str]
    confidence: float  # 0-1 based on context coverage
    query: str
    query_hash: str
    model: str
    tokens_used: int
    latency_ms: int
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            'answer': self.answer,
            'citations': self.citations,
            'used_doc_ids': self.used_doc_ids,
            'confidence': self.confidence,
            'model': self.model,
            'tokens_used': self.tokens_used,
            'latency_ms': self.latency_ms,
        }


# System prompt template
SYSTEM_PROMPT = """You are a maritime operations assistant for yacht management. You help crew members find information about their vessel, equipment, work orders, and compliance records.

CRITICAL RULES:
1. ONLY use information from the provided context. Never make up facts.
2. CITE every factual claim using [1], [2], etc. matching the context numbers.
3. If the context doesn't contain enough information, say "I don't have enough information to answer that."
4. Never guess at equipment specifications, part numbers, dates, or compliance requirements.
5. This is READ-ONLY. Never suggest direct data modifications - only suggest actions via the system.

USER CONTEXT:
- Role: {role}
- Lens: {lens}
- Query intent: Informational (read-only)

ANSWER FORMAT:
- Be concise but complete
- Use bullet points for lists
- Always include citation numbers [1], [2] after facts
- End with a confidence note if information is partial"""


USER_PROMPT_TEMPLATE = """Based on the following context, answer the question.

CONTEXT:
{context}

QUESTION: {query}

Provide a clear, cited answer. Use [1], [2], etc. to cite sources. If information is insufficient, state that clearly."""


def build_system_prompt(role: str, lens: str) -> str:
    """Build system prompt with user context."""
    return SYSTEM_PROMPT.format(role=role, lens=lens)


def build_user_prompt(context: RAGContext) -> str:
    """Build user prompt with context and query."""
    return USER_PROMPT_TEMPLATE.format(
        context=context.to_prompt_context(),
        query=context.query
    )


def extract_cited_indices(answer: str) -> List[int]:
    """Extract citation indices from answer text."""
    import re
    pattern = r'\[(\d+)\]'
    matches = re.findall(pattern, answer)
    return list(set(int(m) for m in matches))


def compute_confidence(context: RAGContext, cited_indices: List[int]) -> float:
    """
    Compute confidence score based on:
    1. How many context chunks were cited
    2. Average score of cited chunks
    3. Total context coverage
    """
    if not context.chunks:
        return 0.0

    # Citation coverage (how many chunks were used)
    citation_coverage = len(cited_indices) / len(context.chunks) if context.chunks else 0

    # Average score of cited chunks
    cited_scores = []
    for idx in cited_indices:
        if 0 < idx <= len(context.chunks):
            cited_scores.append(context.chunks[idx - 1].score)

    avg_cited_score = sum(cited_scores) / len(cited_scores) if cited_scores else 0

    # Context quality (average of all chunk scores)
    avg_context_score = sum(c.score for c in context.chunks) / len(context.chunks)

    # Weighted confidence
    confidence = (
        0.4 * citation_coverage +
        0.4 * avg_cited_score +
        0.2 * avg_context_score
    )

    return min(1.0, max(0.0, confidence))


async def generate_answer(
    context: RAGContext,
    model: str = "gpt-4o-mini",
    temperature: float = 0.1,  # Low for determinism
    max_tokens: int = 1000,
) -> RAGAnswer:
    """
    Generate answer from context using GPT.

    Uses low temperature for deterministic responses.
    """
    import time
    start_time = time.time()

    api_key = os.environ.get('OPENAI_API_KEY')
    if not api_key:
        raise ValueError("OPENAI_API_KEY not set")

    # Build prompts
    system_prompt = build_system_prompt(context.role, context.lens)
    user_prompt = build_user_prompt(context)

    # Call GPT
    response = openai.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=temperature,
        max_tokens=max_tokens,
    )

    answer_text = response.choices[0].message.content
    tokens_used = response.usage.total_tokens

    # Extract citations used
    cited_indices = extract_cited_indices(answer_text)

    # Map cited indices to actual citations
    used_citations = []
    used_doc_ids = []
    for idx in sorted(cited_indices):
        if 0 < idx <= len(context.chunks):
            chunk = context.chunks[idx - 1]
            used_citations.append(chunk.citation.to_dict())
            if chunk.citation.doc_id not in used_doc_ids:
                used_doc_ids.append(chunk.citation.doc_id)

    # Compute confidence
    confidence = compute_confidence(context, cited_indices)

    # Calculate latency
    latency_ms = int((time.time() - start_time) * 1000)

    return RAGAnswer(
        answer=answer_text,
        citations=used_citations,
        used_doc_ids=used_doc_ids,
        confidence=confidence,
        query=context.query,
        query_hash=context.query_hash,
        model=model,
        tokens_used=tokens_used,
        latency_ms=latency_ms,
    )


def generate_answer_sync(
    context: RAGContext,
    model: str = "gpt-4o-mini",
    temperature: float = 0.1,
    max_tokens: int = 1000,
) -> RAGAnswer:
    """
    Synchronous version for testing.
    """
    import time
    start_time = time.time()

    api_key = os.environ.get('OPENAI_API_KEY')
    if not api_key:
        raise ValueError("OPENAI_API_KEY not set")

    system_prompt = build_system_prompt(context.role, context.lens)
    user_prompt = build_user_prompt(context)

    response = openai.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=temperature,
        max_tokens=max_tokens,
    )

    answer_text = response.choices[0].message.content
    tokens_used = response.usage.total_tokens

    cited_indices = extract_cited_indices(answer_text)

    used_citations = []
    used_doc_ids = []
    for idx in sorted(cited_indices):
        if 0 < idx <= len(context.chunks):
            chunk = context.chunks[idx - 1]
            used_citations.append(chunk.citation.to_dict())
            if chunk.citation.doc_id not in used_doc_ids:
                used_doc_ids.append(chunk.citation.doc_id)

    confidence = compute_confidence(context, cited_indices)
    latency_ms = int((time.time() - start_time) * 1000)

    return RAGAnswer(
        answer=answer_text,
        citations=used_citations,
        used_doc_ids=used_doc_ids,
        confidence=confidence,
        query=context.query,
        query_hash=context.query_hash,
        model=model,
        tokens_used=tokens_used,
        latency_ms=latency_ms,
    )


# =============================================================================
# FALLBACK ANSWERS
# =============================================================================

def generate_no_context_answer(query: str, query_hash: str) -> RAGAnswer:
    """Generate answer when no context is available."""
    return RAGAnswer(
        answer="I couldn't find any relevant information in the system for your query. Please try rephrasing or check if the data exists in the system.",
        citations=[],
        used_doc_ids=[],
        confidence=0.0,
        query=query,
        query_hash=query_hash,
        model="fallback",
        tokens_used=0,
        latency_ms=0,
    )


def generate_error_answer(query: str, query_hash: str, error: str) -> RAGAnswer:
    """Generate answer when an error occurred."""
    return RAGAnswer(
        answer=f"I encountered an error while processing your query. Please try again.",
        citations=[],
        used_doc_ids=[],
        confidence=0.0,
        query=query,
        query_hash=query_hash,
        model="error",
        tokens_used=0,
        latency_ms=0,
    )
