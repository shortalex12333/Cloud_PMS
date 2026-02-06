"""
RAG Faithfulness Verifier (Fix 2 + Fix 8)
=========================================

Verifies that generated answers are faithful to the retrieved context.

Robust matching:
- Date canonicalization: "January 5, 2026" ↔ "2026-01-05" ↔ "05/01/2026"
- Numeric equivalence: parse numbers with tolerance
- Token similarity: token-F1 and coverage
- Embedding similarity (optional): cosine on sentence vs chunk

Confidence computation (Fix 8):
- faithfulness = supported_sentences / factual_sentences
- coverage = cited_chunks_used / topK
- consistency = average similarity of supports
- confidence = 0.6*faithfulness + 0.2*coverage + 0.2*consistency
"""

import re
from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import dataclass, field
from datetime import datetime
import math


# =============================================================================
# DATE PARSING & CANONICALIZATION
# =============================================================================

MONTH_NAMES = {
    'january': 1, 'jan': 1,
    'february': 2, 'feb': 2,
    'march': 3, 'mar': 3,
    'april': 4, 'apr': 4,
    'may': 5,
    'june': 6, 'jun': 6,
    'july': 7, 'jul': 7,
    'august': 8, 'aug': 8,
    'september': 9, 'sep': 9, 'sept': 9,
    'october': 10, 'oct': 10,
    'november': 11, 'nov': 11,
    'december': 12, 'dec': 12,
}


def parse_date(text: str) -> Optional[datetime]:
    """
    Parse various date formats to datetime.

    Handles:
    - 2026-01-05
    - 01/05/2026
    - January 5, 2026
    - Jan 5, 2026
    - 5 January 2026
    """
    text = text.strip()

    # ISO format: 2026-01-05
    match = re.match(r'(\d{4})-(\d{1,2})-(\d{1,2})', text)
    if match:
        try:
            return datetime(int(match.group(1)), int(match.group(2)), int(match.group(3)))
        except:
            pass

    # US format: 01/05/2026 or 1/5/2026
    match = re.match(r'(\d{1,2})/(\d{1,2})/(\d{4})', text)
    if match:
        try:
            return datetime(int(match.group(3)), int(match.group(1)), int(match.group(2)))
        except:
            pass

    # Month name first: January 5, 2026 or Jan 5 2026
    for month_name, month_num in MONTH_NAMES.items():
        pattern = rf'\b{month_name}\.?\s+(\d{{1,2}}),?\s+(\d{{4}})\b'
        match = re.search(pattern, text.lower())
        if match:
            try:
                return datetime(int(match.group(2)), month_num, int(match.group(1)))
            except:
                pass

    # Day first: 5 January 2026
    for month_name, month_num in MONTH_NAMES.items():
        pattern = rf'\b(\d{{1,2}})\s+{month_name}\.?,?\s+(\d{{4}})\b'
        match = re.search(pattern, text.lower())
        if match:
            try:
                return datetime(int(match.group(2)), month_num, int(match.group(1)))
            except:
                pass

    return None


def extract_dates(text: str) -> List[datetime]:
    """Extract all dates from text."""
    dates = []

    # ISO dates
    for match in re.finditer(r'\d{4}-\d{1,2}-\d{1,2}', text):
        dt = parse_date(match.group())
        if dt:
            dates.append(dt)

    # US dates
    for match in re.finditer(r'\d{1,2}/\d{1,2}/\d{4}', text):
        dt = parse_date(match.group())
        if dt:
            dates.append(dt)

    # Month name dates
    for month_name in MONTH_NAMES:
        for match in re.finditer(rf'{month_name}\.?\s+\d{{1,2}},?\s+\d{{4}}', text, re.IGNORECASE):
            dt = parse_date(match.group())
            if dt:
                dates.append(dt)

    return dates


def dates_match(date1: datetime, date2: datetime, tolerance_days: int = 0) -> bool:
    """Check if two dates match within tolerance."""
    return abs((date1 - date2).days) <= tolerance_days


# =============================================================================
# NUMBER PARSING & COMPARISON
# =============================================================================

def extract_numbers(text: str) -> List[float]:
    """Extract all numbers from text."""
    numbers = []

    # Match numbers with optional decimal
    for match in re.finditer(r'(\d+(?:\.\d+)?)', text):
        try:
            numbers.append(float(match.group(1)))
        except:
            pass

    return numbers


def numbers_match(num1: float, num2: float, tolerance: float = 0.01) -> bool:
    """Check if two numbers match within tolerance."""
    if num1 == 0 and num2 == 0:
        return True
    if num1 == 0 or num2 == 0:
        return abs(num1 - num2) <= tolerance

    # Relative tolerance
    return abs(num1 - num2) / max(abs(num1), abs(num2)) <= tolerance


# =============================================================================
# TOKEN SIMILARITY
# =============================================================================

def tokenize(text: str) -> Set[str]:
    """Simple tokenization: lowercase, split on non-alphanumeric."""
    return set(re.findall(r'\b\w+\b', text.lower()))


def normalize_text(text: str) -> str:
    """Normalize text for comparison."""
    # Lowercase
    text = text.lower()
    # Remove punctuation except for dates
    text = re.sub(r'[^\w\s\-/]', ' ', text)
    # Collapse whitespace
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def compute_token_f1(text1: str, text2: str) -> float:
    """Compute token-level F1 score."""
    tokens1 = tokenize(text1)
    tokens2 = tokenize(text2)

    if not tokens1 or not tokens2:
        return 0.0

    intersection = tokens1 & tokens2
    precision = len(intersection) / len(tokens1) if tokens1 else 0
    recall = len(intersection) / len(tokens2) if tokens2 else 0

    if precision + recall == 0:
        return 0.0

    return 2 * precision * recall / (precision + recall)


def compute_rouge_l(text1: str, text2: str) -> float:
    """Compute ROUGE-L (longest common subsequence) score."""
    words1 = text1.lower().split()
    words2 = text2.lower().split()

    if not words1 or not words2:
        return 0.0

    # LCS using dynamic programming
    m, n = len(words1), len(words2)
    dp = [[0] * (n + 1) for _ in range(m + 1)]

    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if words1[i-1] == words2[j-1]:
                dp[i][j] = dp[i-1][j-1] + 1
            else:
                dp[i][j] = max(dp[i-1][j], dp[i][j-1])

    lcs_length = dp[m][n]
    precision = lcs_length / m if m else 0
    recall = lcs_length / n if n else 0

    if precision + recall == 0:
        return 0.0

    return 2 * precision * recall / (precision + recall)


# =============================================================================
# SENTENCE VERIFICATION
# =============================================================================

@dataclass
class SentenceVerification:
    """Verification result for a single sentence."""
    sentence: str
    is_factual: bool
    is_supported: bool
    support_type: str  # 'date', 'number', 'token', 'semantic', 'none'
    supporting_chunks: List[int]
    similarity_score: float
    confidence: float


@dataclass
class VerificationResult:
    """Complete verification result for an answer."""
    is_faithful: bool
    faithfulness_score: float
    coverage_score: float
    consistency_score: float
    confidence: float  # Composite: 0.6*faith + 0.2*coverage + 0.2*consistency
    sentence_results: List[SentenceVerification]
    total_sentences: int
    factual_sentences: int
    supported_sentences: int
    issues: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            'is_faithful': self.is_faithful,
            'faithfulness_score': self.faithfulness_score,
            'coverage_score': self.coverage_score,
            'consistency_score': self.consistency_score,
            'confidence': self.confidence,
            'total_sentences': self.total_sentences,
            'factual_sentences': self.factual_sentences,
            'supported_sentences': self.supported_sentences,
            'issues': self.issues,
        }


def is_factual_sentence(sentence: str) -> bool:
    """
    Determine if a sentence makes a factual claim.

    Non-factual: questions, hedges, meta-statements
    """
    sentence_lower = sentence.lower().strip()

    # Questions
    if sentence.endswith('?'):
        return False

    # Hedging phrases
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
        "information is complete",
        "based on the provided",
    ]
    for phrase in hedge_phrases:
        if phrase in sentence_lower:
            return False

    # Very short sentences
    if len(sentence.split()) < 3:
        return False

    # Headers/labels only
    if sentence.endswith(':') and len(sentence.split()) < 5:
        return False

    return True


def verify_sentence_against_chunks(
    sentence: str,
    chunks: List[Any],  # ContextChunk
    cited_indices: List[int],
    token_threshold: float = 0.25,
    date_required: bool = True,
) -> SentenceVerification:
    """
    Verify a single sentence against context chunks.

    A sentence is supported if ANY of these match:
    1. Date match: dates in sentence appear in a chunk
    2. Number match: numbers in sentence appear in a chunk
    3. Token match: token F1 >= threshold
    4. Semantic match: embedding similarity >= 0.8 (if available)
    """
    if not is_factual_sentence(sentence):
        return SentenceVerification(
            sentence=sentence,
            is_factual=False,
            is_supported=True,
            support_type='non_factual',
            supporting_chunks=[],
            similarity_score=1.0,
            confidence=1.0,
        )

    sentence_normalized = normalize_text(sentence)
    sentence_dates = extract_dates(sentence)
    sentence_numbers = extract_numbers(sentence)

    supporting_chunks = []
    support_type = 'none'
    max_similarity = 0.0

    # Determine which chunks to check
    chunks_to_check = []
    if cited_indices:
        for idx in cited_indices:
            if 0 < idx <= len(chunks):
                chunks_to_check.append((idx, chunks[idx - 1]))
    else:
        # Check all chunks if no citations
        chunks_to_check = [(i + 1, chunk) for i, chunk in enumerate(chunks)]

    for idx, chunk in chunks_to_check:
        chunk_text = chunk.text
        chunk_normalized = normalize_text(chunk_text)
        chunk_dates = extract_dates(chunk_text)
        chunk_numbers = extract_numbers(chunk_text)

        # Check date match
        if sentence_dates and chunk_dates:
            for sd in sentence_dates:
                for cd in chunk_dates:
                    if dates_match(sd, cd):
                        supporting_chunks.append(idx)
                        support_type = 'date'
                        max_similarity = max(max_similarity, 0.9)
                        break

        # Check number match
        if sentence_numbers and chunk_numbers:
            matched_numbers = 0
            for sn in sentence_numbers:
                for cn in chunk_numbers:
                    if numbers_match(sn, cn):
                        matched_numbers += 1
                        break
            if matched_numbers > 0:
                number_ratio = matched_numbers / len(sentence_numbers)
                if number_ratio >= 0.5:
                    if idx not in supporting_chunks:
                        supporting_chunks.append(idx)
                    if support_type == 'none':
                        support_type = 'number'
                    max_similarity = max(max_similarity, 0.7 + 0.2 * number_ratio)

        # Check token similarity
        token_f1 = compute_token_f1(sentence_normalized, chunk_normalized)
        rouge_l = compute_rouge_l(sentence_normalized, chunk_normalized)

        combined_token_score = 0.6 * token_f1 + 0.4 * rouge_l

        if combined_token_score >= token_threshold:
            if idx not in supporting_chunks:
                supporting_chunks.append(idx)
            if support_type == 'none':
                support_type = 'token'
            max_similarity = max(max_similarity, combined_token_score)

    is_supported = len(supporting_chunks) > 0

    return SentenceVerification(
        sentence=sentence,
        is_factual=True,
        is_supported=is_supported,
        support_type=support_type,
        supporting_chunks=supporting_chunks,
        similarity_score=max_similarity,
        confidence=max_similarity if is_supported else 0.0,
    )


def extract_citations_from_text(text: str) -> List[int]:
    """Extract citation indices [1], [2], etc. from text."""
    return [int(m) for m in re.findall(r'\[(\d+)\]', text)]


def split_into_sentences(text: str) -> List[str]:
    """Split text into sentences."""
    # Handle bullet points as separate sentences
    text = re.sub(r'^[-•*]\s*', '', text, flags=re.MULTILINE)

    # Split on sentence boundaries
    sentences = re.split(r'(?<=[.!?])\s+', text)

    # Also split on newlines for bullet points
    expanded = []
    for s in sentences:
        for line in s.split('\n'):
            line = line.strip()
            if line and len(line) > 5:
                expanded.append(line)

    return expanded


def verify_answer(
    answer,  # RAGAnswer
    context,  # RAGContext
    faithfulness_threshold: float = 0.85,
) -> VerificationResult:
    """
    Verify the complete answer against the context.

    Computes:
    - faithfulness = supported_sentences / factual_sentences
    - coverage = cited_chunks_used / total_chunks
    - consistency = average similarity of supported sentences
    - confidence = 0.6*faithfulness + 0.2*coverage + 0.2*consistency
    """
    sentences = split_into_sentences(answer.answer)
    sentence_results = []
    all_cited_chunks = set()

    for sentence in sentences:
        cited_indices = extract_citations_from_text(sentence)
        all_cited_chunks.update(cited_indices)

        result = verify_sentence_against_chunks(
            sentence=sentence,
            chunks=context.chunks,
            cited_indices=cited_indices,
        )
        sentence_results.append(result)

    # Compute metrics
    total_sentences = len(sentence_results)
    factual_sentences = sum(1 for r in sentence_results if r.is_factual)
    supported_sentences = sum(1 for r in sentence_results if r.is_factual and r.is_supported)

    # Faithfulness
    if factual_sentences > 0:
        faithfulness_score = supported_sentences / factual_sentences
    else:
        faithfulness_score = 1.0  # No factual claims = trivially faithful

    # Coverage (how many chunks were cited)
    if context.chunks:
        coverage_score = len(all_cited_chunks) / len(context.chunks)
    else:
        coverage_score = 0.0

    # Consistency (average similarity of supported sentences)
    supported_similarities = [r.similarity_score for r in sentence_results if r.is_factual and r.is_supported]
    if supported_similarities:
        consistency_score = sum(supported_similarities) / len(supported_similarities)
    else:
        consistency_score = 0.0

    # Composite confidence (Fix 8)
    confidence = (
        0.6 * faithfulness_score +
        0.2 * coverage_score +
        0.2 * consistency_score
    )

    is_faithful = faithfulness_score >= faithfulness_threshold

    # Collect issues
    issues = []
    for r in sentence_results:
        if r.is_factual and not r.is_supported:
            issues.append(f"Unsupported: {r.sentence[:50]}...")

    return VerificationResult(
        is_faithful=is_faithful,
        faithfulness_score=faithfulness_score,
        coverage_score=coverage_score,
        consistency_score=consistency_score,
        confidence=confidence,
        sentence_results=sentence_results,
        total_sentences=total_sentences,
        factual_sentences=factual_sentences,
        supported_sentences=supported_sentences,
        issues=issues,
    )


# =============================================================================
# TESTING
# =============================================================================

if __name__ == '__main__':
    # Test date parsing
    test_dates = [
        "2026-01-05",
        "01/05/2026",
        "January 5, 2026",
        "Jan 5 2026",
        "5 January 2026",
    ]

    print("=" * 50)
    print(" Date Parsing Tests")
    print("=" * 50)

    for d in test_dates:
        parsed = parse_date(d)
        print(f"{d:25} → {parsed}")

    # Test number extraction
    test_texts = [
        "8.0 hours recorded",
        "Total: 12 hours, Rest: 6.5",
        "Violation at 24 hours",
    ]

    print("\n" + "=" * 50)
    print(" Number Extraction Tests")
    print("=" * 50)

    for t in test_texts:
        nums = extract_numbers(t)
        print(f"{t:30} → {nums}")
