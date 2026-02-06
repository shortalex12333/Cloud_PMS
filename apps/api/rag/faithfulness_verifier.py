"""
RAG Faithfulness Verifier
=========================

Verifies that generated answers are faithful to the retrieved context.

Checks:
1. Every factual sentence maps to at least one citation
2. No unsupported claims (hallucinations)
3. Citation accuracy (cited text actually supports the claim)

Uses a secondary check with similarity + entailment scoring.
"""

import re
import os
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
import openai

from .context_builder import RAGContext, ContextChunk
from .answer_generator import RAGAnswer


@dataclass
class SentenceVerification:
    """Verification result for a single sentence."""
    sentence: str
    is_factual: bool  # Does it make a factual claim?
    is_supported: bool  # Is it supported by context?
    supporting_chunks: List[int]  # Indices of supporting chunks
    confidence: float  # 0-1 verification confidence
    issue: Optional[str] = None  # Description of issue if not supported


@dataclass
class VerificationResult:
    """Complete verification result for an answer."""
    is_faithful: bool
    faithfulness_score: float  # 0-1
    sentence_results: List[SentenceVerification]
    total_sentences: int
    factual_sentences: int
    supported_sentences: int
    unsupported_sentences: int
    issues: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            'is_faithful': self.is_faithful,
            'faithfulness_score': self.faithfulness_score,
            'total_sentences': self.total_sentences,
            'factual_sentences': self.factual_sentences,
            'supported_sentences': self.supported_sentences,
            'unsupported_sentences': self.unsupported_sentences,
            'issues': self.issues,
        }


def split_into_sentences(text: str) -> List[str]:
    """Split text into sentences."""
    # Simple sentence splitting
    sentences = re.split(r'(?<=[.!?])\s+', text)
    return [s.strip() for s in sentences if s.strip()]


def is_factual_sentence(sentence: str) -> bool:
    """
    Determine if a sentence makes a factual claim.

    Non-factual sentences include:
    - Questions
    - Hedged statements ("I don't have information...")
    - Meta-statements ("Based on the context...")
    """
    sentence_lower = sentence.lower()

    # Questions
    if sentence.endswith('?'):
        return False

    # Hedging phrases (not factual claims)
    hedge_phrases = [
        "i don't have",
        "i couldn't find",
        "not enough information",
        "based on the context",
        "according to the provided",
        "i cannot confirm",
        "please note",
        "it appears that",
        "it seems",
    ]
    for phrase in hedge_phrases:
        if phrase in sentence_lower:
            return False

    # Very short sentences are usually not factual
    if len(sentence.split()) < 4:
        return False

    return True


def extract_citations_from_sentence(sentence: str) -> List[int]:
    """Extract citation indices from a sentence."""
    pattern = r'\[(\d+)\]'
    matches = re.findall(pattern, sentence)
    return [int(m) for m in matches]


def compute_text_similarity(text1: str, text2: str) -> float:
    """
    Compute simple text similarity using word overlap.

    For production, use embedding similarity instead.
    """
    words1 = set(text1.lower().split())
    words2 = set(text2.lower().split())

    if not words1 or not words2:
        return 0.0

    intersection = words1 & words2
    union = words1 | words2

    return len(intersection) / len(union)


def verify_sentence_against_context(
    sentence: str,
    context: RAGContext,
    cited_indices: List[int],
    similarity_threshold: float = 0.15,
) -> SentenceVerification:
    """
    Verify a single sentence against the context.

    A sentence is supported if:
    1. It cites a chunk AND the chunk contains supporting text
    2. OR it's similar enough to a cited chunk (for paraphrasing)
    """
    if not is_factual_sentence(sentence):
        return SentenceVerification(
            sentence=sentence,
            is_factual=False,
            is_supported=True,  # Non-factual sentences are always "supported"
            supporting_chunks=[],
            confidence=1.0,
        )

    supporting_chunks = []
    max_similarity = 0.0

    # Check cited chunks first
    for idx in cited_indices:
        if 0 < idx <= len(context.chunks):
            chunk = context.chunks[idx - 1]
            similarity = compute_text_similarity(sentence, chunk.text)
            if similarity > similarity_threshold:
                supporting_chunks.append(idx)
                max_similarity = max(max_similarity, similarity)

    # If no citations, check all chunks for implicit support
    if not cited_indices:
        for i, chunk in enumerate(context.chunks, 1):
            similarity = compute_text_similarity(sentence, chunk.text)
            if similarity > similarity_threshold:
                supporting_chunks.append(i)
                max_similarity = max(max_similarity, similarity)

    is_supported = len(supporting_chunks) > 0

    issue = None
    if not is_supported:
        if cited_indices:
            issue = f"Cited sources [{', '.join(map(str, cited_indices))}] do not support this claim"
        else:
            issue = "No citation provided and no supporting context found"

    return SentenceVerification(
        sentence=sentence,
        is_factual=True,
        is_supported=is_supported,
        supporting_chunks=supporting_chunks,
        confidence=max_similarity if is_supported else 0.0,
        issue=issue,
    )


def verify_answer(
    answer: RAGAnswer,
    context: RAGContext,
    faithfulness_threshold: float = 0.85,
) -> VerificationResult:
    """
    Verify the complete answer against the context.

    An answer is faithful if:
    - >= faithfulness_threshold of factual sentences are supported
    """
    sentences = split_into_sentences(answer.answer)
    sentence_results = []

    for sentence in sentences:
        cited_indices = extract_citations_from_sentence(sentence)
        result = verify_sentence_against_context(sentence, context, cited_indices)
        sentence_results.append(result)

    # Compute metrics
    total_sentences = len(sentence_results)
    factual_sentences = sum(1 for r in sentence_results if r.is_factual)
    supported_sentences = sum(1 for r in sentence_results if r.is_factual and r.is_supported)
    unsupported_sentences = factual_sentences - supported_sentences

    # Faithfulness score
    if factual_sentences > 0:
        faithfulness_score = supported_sentences / factual_sentences
    else:
        faithfulness_score = 1.0  # No factual claims = trivially faithful

    is_faithful = faithfulness_score >= faithfulness_threshold

    # Collect issues
    issues = [r.issue for r in sentence_results if r.issue]

    return VerificationResult(
        is_faithful=is_faithful,
        faithfulness_score=faithfulness_score,
        sentence_results=sentence_results,
        total_sentences=total_sentences,
        factual_sentences=factual_sentences,
        supported_sentences=supported_sentences,
        unsupported_sentences=unsupported_sentences,
        issues=issues,
    )


# =============================================================================
# LLM-BASED VERIFICATION (for higher accuracy)
# =============================================================================

VERIFICATION_PROMPT = """You are a fact-checker verifying if a claim is supported by the given context.

CONTEXT:
{context}

CLAIM: {claim}

Is this claim fully supported by the context? Answer with:
- "SUPPORTED" if the context contains information that supports this claim
- "NOT_SUPPORTED" if the context doesn't contain enough information
- "CONTRADICTED" if the context contradicts this claim

Also provide a brief explanation.

Format:
VERDICT: [SUPPORTED/NOT_SUPPORTED/CONTRADICTED]
EXPLANATION: [brief explanation]"""


async def verify_with_llm(
    sentence: str,
    context: RAGContext,
    model: str = "gpt-4o-mini",
) -> Tuple[bool, str]:
    """
    Verify a sentence using LLM for more accurate assessment.

    Use sparingly due to cost - only for sampled sentences.
    """
    api_key = os.environ.get('OPENAI_API_KEY')
    if not api_key:
        raise ValueError("OPENAI_API_KEY not set")

    prompt = VERIFICATION_PROMPT.format(
        context=context.to_prompt_context(),
        claim=sentence
    )

    response = openai.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0,
        max_tokens=150,
    )

    result = response.choices[0].message.content

    is_supported = "SUPPORTED" in result.upper() and "NOT_SUPPORTED" not in result.upper()
    explanation = result.split("EXPLANATION:")[-1].strip() if "EXPLANATION:" in result else result

    return is_supported, explanation


def verify_with_llm_sync(
    sentence: str,
    context: RAGContext,
    model: str = "gpt-4o-mini",
) -> Tuple[bool, str]:
    """Synchronous version for testing."""
    api_key = os.environ.get('OPENAI_API_KEY')
    if not api_key:
        raise ValueError("OPENAI_API_KEY not set")

    prompt = VERIFICATION_PROMPT.format(
        context=context.to_prompt_context(),
        claim=sentence
    )

    response = openai.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0,
        max_tokens=150,
    )

    result = response.choices[0].message.content

    is_supported = "SUPPORTED" in result.upper() and "NOT_SUPPORTED" not in result.upper()
    explanation = result.split("EXPLANATION:")[-1].strip() if "EXPLANATION:" in result else result

    return is_supported, explanation
