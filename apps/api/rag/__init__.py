"""
RAG Module
==========

SQL-based RAG system using f1_search_fusion for retrieval and GPT for answer generation.

Components:
- normalizer: Input normalization and time extraction
- context_builder: Retrieves and chunks documents with domain serializers
- answer_generator: Generates cited answers
- verifier: Robust faithfulness verification with date/number matching
"""

from .normalizer import (
    normalize_query,
    extract_time_window,
    SYNONYMS,
    TIME_EXPRESSIONS,
)

from .context_builder import (
    RAGContext,
    ContextChunk,
    Citation,
    build_context,
    build_context_sync,
    generate_query_embedding,
    compute_query_hash,
    # Domain serializers
    serialize_hours_of_rest,
    serialize_work_order,
    serialize_equipment,
    serialize_part,
    serialize_fault,
    serialize_document,
)

from .answer_generator import (
    RAGAnswer,
    generate_answer,
    generate_answer_sync,
    generate_no_context_answer,
    generate_error_answer,
)

from .verifier import (
    VerificationResult,
    SentenceVerification,
    verify_answer,
    parse_date,
    extract_dates,
    extract_numbers,
)

__all__ = [
    # Context
    'RAGContext',
    'ContextChunk',
    'Citation',
    'build_context',
    'build_context_sync',
    'generate_query_embedding',
    'compute_query_hash',
    # Answer
    'RAGAnswer',
    'generate_answer',
    'generate_answer_sync',
    'generate_no_context_answer',
    'generate_error_answer',
    # Verification
    'VerificationResult',
    'SentenceVerification',
    'verify_answer',
    'verify_with_llm',
    'verify_with_llm_sync',
]
