"""
RAG Context Builder
===================

Retrieves top-K documents via f1_search_fusion and builds context for answer generation.

Flow:
1. Generate GPT embedding for query
2. Call f1_search_fusion with domain params
3. Extract chunks from results with overlap scoring
4. De-duplicate by source document
5. Budget to token cap per answer
6. Return context with citation metadata

All queries are yacht-scoped. Doc IDs, pages, and spans are preserved for citations.
"""

import hashlib
import json
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import openai
import os

# Token estimation (rough: 4 chars ≈ 1 token for English)
CHARS_PER_TOKEN = 4
DEFAULT_TOKEN_BUDGET = 4000  # Max tokens for context
DEFAULT_TOP_K = 12


@dataclass
class Citation:
    """Citation reference for a retrieved chunk."""
    doc_id: str
    doc_type: str
    page: Optional[int] = None
    span_start: Optional[int] = None
    span_end: Optional[int] = None
    span_hash: Optional[str] = None
    title: Optional[str] = None
    source_url: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'doc_id': self.doc_id,
            'doc_type': self.doc_type,
            'page': self.page,
            'span_hash': self.span_hash,
            'title': self.title,
        }


@dataclass
class ContextChunk:
    """A chunk of context with citation metadata."""
    text: str
    citation: Citation
    score: float
    tokens: int = 0

    def __post_init__(self):
        self.tokens = len(self.text) // CHARS_PER_TOKEN


@dataclass
class RAGContext:
    """Complete context for answer generation."""
    query: str
    query_hash: str
    chunks: List[ContextChunk]
    total_tokens: int
    yacht_id: str
    role: str
    lens: str
    domain: Optional[str]
    mode: str
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_prompt_context(self) -> str:
        """Format chunks for GPT prompt."""
        parts = []
        for i, chunk in enumerate(self.chunks, 1):
            citation_ref = f"[{i}]"
            parts.append(f"{citation_ref} ({chunk.citation.doc_type}): {chunk.text}")
        return "\n\n".join(parts)

    def get_citations(self) -> List[Dict[str, Any]]:
        """Get citation list for response."""
        return [chunk.citation.to_dict() for chunk in self.chunks]


def generate_query_embedding(query: str) -> Optional[List[float]]:
    """Generate embedding via OpenAI GPT text-embedding-3-small."""
    try:
        api_key = os.environ.get('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY not set")

        response = openai.embeddings.create(
            model="text-embedding-3-small",
            input=query,
            dimensions=1536
        )
        return response.data[0].embedding
    except Exception as e:
        print(f"ERROR: Failed to generate embedding: {e}")
        return None


def compute_query_hash(query: str, yacht_id: str, role: str, lens: str) -> str:
    """Compute deterministic hash for caching."""
    content = f"{yacht_id}:{role}:{lens}:{query.lower().strip()}"
    return hashlib.sha256(content.encode()).hexdigest()[:16]


def compute_span_hash(text: str) -> str:
    """Compute hash for a text span (for citation verification)."""
    return hashlib.md5(text.encode()).hexdigest()[:8]


async def retrieve_chunks(
    conn,  # asyncpg connection
    yacht_id: str,
    query: str,
    query_embedding: List[float],
    role: str,
    lens: str,
    domain: Optional[str] = None,
    mode: str = 'explore',
    domain_boost: float = 0.25,
    top_k: int = DEFAULT_TOP_K,
    time_from: Optional[datetime] = None,
    time_to: Optional[datetime] = None,
) -> List[Dict[str, Any]]:
    """
    Retrieve top-K chunks via f1_search_fusion.

    Returns raw results from the fusion function.
    """
    # Convert embedding to PostgreSQL vector format
    vec_literal = '[' + ','.join(str(x) for x in query_embedding) + ']'

    results = await conn.fetch("""
        SELECT
            object_id,
            object_type,
            payload,
            final_score,
            s_text,
            s_vector,
            s_recency,
            s_bias,
            s_domain
        FROM f1_search_fusion(
            $1::uuid,           -- yacht_id
            $2,                 -- query_text
            $3::vector(1536),   -- query_embedding
            $4,                 -- role
            $5,                 -- lens
            $6,                 -- domain
            $7,                 -- mode
            $8,                 -- domain_boost
            0.50, 0.25, 0.15, 0.10, 0.20,  -- weights
            0.01, 60, 6.0, 0.2,            -- params
            200, 200,                       -- m_text, m_vec
            $9, 0,                          -- limit, offset
            true                            -- debug
        )
    """, yacht_id, query, vec_literal, role, lens, domain, mode, domain_boost, top_k)

    return [dict(r) for r in results]


def serialize_hours_of_rest(payload: Dict[str, Any]) -> str:
    """Serialize hours_of_rest payload to readable text."""
    parts = []

    record_date = payload.get('record_date', 'Unknown date')
    total_hours = payload.get('total_hours', payload.get('hours_total', 'N/A'))
    rest_hours = payload.get('rest_hours', payload.get('hours_rest', 'N/A'))
    work_hours = payload.get('work_hours', payload.get('hours_work', 'N/A'))

    # Compliance status
    compliance = 'Compliant' if payload.get('is_daily_compliant', payload.get('compliant')) else 'Non-compliant'
    weekly_compliance = payload.get('weekly_compliance_status', '')
    violation = payload.get('violation_type', payload.get('violation', ''))

    parts.append(f"Date: {record_date}")
    parts.append(f"Total Hours: {total_hours}")
    if rest_hours != 'N/A':
        parts.append(f"Rest Hours: {rest_hours}")
    if work_hours != 'N/A':
        parts.append(f"Work Hours: {work_hours}")
    parts.append(f"Status: {compliance}")

    if weekly_compliance:
        parts.append(f"Weekly Status: {weekly_compliance}")
    if violation:
        parts.append(f"Violation: {violation}")

    # Signoff status
    signoff = payload.get('signoff_status', payload.get('status', ''))
    if signoff:
        parts.append(f"Signoff: {signoff}")

    # Crew info if available
    crew_name = payload.get('crew_name', payload.get('user_name', ''))
    if crew_name:
        parts.append(f"Crew Member: {crew_name}")

    return " | ".join(parts)


def serialize_work_order(payload: Dict[str, Any]) -> str:
    """Serialize work_order payload to readable text."""
    parts = []

    code = payload.get('code', payload.get('wo_number', 'N/A'))
    title = payload.get('title', payload.get('name', 'Untitled'))
    status = payload.get('status', 'Unknown')
    priority = payload.get('priority', '')
    equipment = payload.get('equipment_name', payload.get('equipment', ''))
    description = payload.get('description', '')[:200]
    assignee = payload.get('assignee_name', payload.get('assigned_to', ''))
    updated = payload.get('updated_at', payload.get('last_updated', ''))

    parts.append(f"WO #{code}")
    parts.append(f"Title: {title}")
    parts.append(f"Status: {status}")
    if priority:
        parts.append(f"Priority: {priority}")
    if equipment:
        parts.append(f"Equipment: {equipment}")
    if assignee:
        parts.append(f"Assigned to: {assignee}")
    if description:
        parts.append(f"Description: {description}")
    if updated:
        parts.append(f"Updated: {updated}")

    return " | ".join(parts)


def serialize_equipment(payload: Dict[str, Any]) -> str:
    """Serialize equipment payload to readable text."""
    parts = []

    name = payload.get('name', payload.get('equipment_name', 'Unknown'))
    serial = payload.get('serial_number', payload.get('serial', ''))
    location = payload.get('location', '')
    category = payload.get('category', payload.get('type', ''))
    manufacturer = payload.get('manufacturer', payload.get('make', ''))
    model = payload.get('model', '')
    status = payload.get('status', '')

    parts.append(f"Equipment: {name}")
    if serial:
        parts.append(f"Serial: {serial}")
    if manufacturer:
        parts.append(f"Manufacturer: {manufacturer}")
    if model:
        parts.append(f"Model: {model}")
    if location:
        parts.append(f"Location: {location}")
    if category:
        parts.append(f"Category: {category}")
    if status:
        parts.append(f"Status: {status}")

    return " | ".join(parts)


def serialize_part(payload: Dict[str, Any]) -> str:
    """Serialize part/inventory payload to readable text."""
    parts = []

    part_number = payload.get('part_number', payload.get('sku', 'N/A'))
    name = payload.get('name', payload.get('item_name', payload.get('description', 'Unknown')))
    on_hand = payload.get('on_hand', payload.get('quantity', payload.get('qty', 'N/A')))
    min_level = payload.get('min_level', payload.get('reorder_point', ''))
    location = payload.get('location', payload.get('bin_location', ''))
    category = payload.get('category', '')
    unit = payload.get('unit', payload.get('uom', ''))

    parts.append(f"Part: {part_number}")
    parts.append(f"Name: {name}")
    parts.append(f"On Hand: {on_hand}")
    if unit:
        parts[-1] += f" {unit}"
    if min_level:
        parts.append(f"Min Level: {min_level}")
    if location:
        parts.append(f"Location: {location}")
    if category:
        parts.append(f"Category: {category}")

    return " | ".join(parts)


def serialize_fault(payload: Dict[str, Any]) -> str:
    """Serialize fault payload to readable text."""
    parts = []

    code = payload.get('code', payload.get('fault_code', ''))
    title = payload.get('title', payload.get('name', payload.get('description', 'Unknown fault')[:100]))
    severity = payload.get('severity', payload.get('priority', ''))
    status = payload.get('status', '')
    equipment = payload.get('equipment_name', payload.get('equipment', ''))
    reported = payload.get('reported_at', payload.get('created_at', ''))
    resolution = payload.get('resolution', payload.get('fix', ''))[:200] if payload.get('resolution') or payload.get('fix') else ''

    if code:
        parts.append(f"Fault #{code}")
    parts.append(f"Issue: {title}")
    if severity:
        parts.append(f"Severity: {severity}")
    if status:
        parts.append(f"Status: {status}")
    if equipment:
        parts.append(f"Equipment: {equipment}")
    if reported:
        parts.append(f"Reported: {reported}")
    if resolution:
        parts.append(f"Resolution: {resolution}")

    return " | ".join(parts)


def serialize_document(payload: Dict[str, Any]) -> str:
    """Serialize document payload to readable text."""
    parts = []

    title = payload.get('title', payload.get('name', 'Untitled'))
    doc_type = payload.get('doc_type', payload.get('type', payload.get('category', '')))
    description = payload.get('description', payload.get('summary', ''))[:300]
    page_count = payload.get('page_count', payload.get('pages', ''))

    parts.append(f"Document: {title}")
    if doc_type:
        parts.append(f"Type: {doc_type}")
    if description:
        parts.append(f"Summary: {description}")
    if page_count:
        parts.append(f"Pages: {page_count}")

    # Include actual text content if available
    content = payload.get('content', payload.get('text', payload.get('body', '')))
    if content:
        parts.append(f"Content: {content[:500]}")

    return " | ".join(parts)


def serialize_certificate(payload: Dict[str, Any]) -> str:
    """Serialize certificate payload to readable text."""
    parts = []

    name = payload.get('name', payload.get('title', 'Certificate'))
    cert_type = payload.get('type', payload.get('certificate_type', ''))
    expiry = payload.get('expiry_date', payload.get('expires_at', ''))
    status = payload.get('status', '')
    issuer = payload.get('issuer', payload.get('issued_by', ''))

    parts.append(f"Certificate: {name}")
    if cert_type:
        parts.append(f"Type: {cert_type}")
    if expiry:
        parts.append(f"Expires: {expiry}")
    if status:
        parts.append(f"Status: {status}")
    if issuer:
        parts.append(f"Issuer: {issuer}")

    return " | ".join(parts)


def serialize_generic(payload: Dict[str, Any]) -> str:
    """Generic serializer for unknown types."""
    parts = []

    # Try common fields
    for field in ['title', 'name', 'description', 'summary', 'content', 'text']:
        if field in payload and payload[field]:
            parts.append(f"{field.title()}: {str(payload[field])[:200]}")

    if not parts:
        # Fallback: stringify first few fields
        for key, value in list(payload.items())[:5]:
            if value and not key.startswith('_'):
                parts.append(f"{key}: {str(value)[:100]}")

    return " | ".join(parts) if parts else "No content available"


# Domain serializer registry
DOMAIN_SERIALIZERS = {
    'hours_of_rest': serialize_hours_of_rest,
    'work_order': serialize_work_order,
    'work_order_note': serialize_work_order,
    'equipment': serialize_equipment,
    'part': serialize_part,
    'parts': serialize_part,
    'inventory': serialize_part,
    'fault': serialize_fault,
    'document': serialize_document,
    'certificate': serialize_certificate,
}


def extract_text_from_payload(payload: Dict[str, Any], doc_type: str) -> str:
    """
    Extract readable text from payload using domain-specific serializers.

    Fix 1: Uses structured payload fields, not search_text keyword soup.
    """
    if not payload:
        return ""

    # Get domain-specific serializer
    serializer = DOMAIN_SERIALIZERS.get(doc_type, serialize_generic)

    try:
        return serializer(payload)
    except Exception as e:
        # Fallback to generic
        return serialize_generic(payload)


def deduplicate_by_source(chunks: List[ContextChunk], max_per_source: int = 2) -> List[ContextChunk]:
    """
    De-duplicate chunks by source document.

    Keep at most max_per_source chunks from each document.
    """
    source_counts: Dict[str, int] = {}
    deduped = []

    for chunk in chunks:
        doc_id = chunk.citation.doc_id
        count = source_counts.get(doc_id, 0)

        if count < max_per_source:
            deduped.append(chunk)
            source_counts[doc_id] = count + 1

    return deduped


def budget_to_token_cap(chunks: List[ContextChunk], token_budget: int) -> List[ContextChunk]:
    """
    Select chunks to fit within token budget.

    Greedy selection by score until budget exhausted.
    """
    # Already sorted by score from fusion
    selected = []
    total_tokens = 0

    for chunk in chunks:
        if total_tokens + chunk.tokens <= token_budget:
            selected.append(chunk)
            total_tokens += chunk.tokens
        else:
            # Try to fit partial chunk
            remaining = token_budget - total_tokens
            if remaining > 100:  # At least 100 tokens worth
                truncated_text = chunk.text[:remaining * CHARS_PER_TOKEN]
                truncated_chunk = ContextChunk(
                    text=truncated_text,
                    citation=chunk.citation,
                    score=chunk.score,
                )
                selected.append(truncated_chunk)
            break

    return selected


async def build_context(
    conn,
    yacht_id: str,
    query: str,
    role: str,
    lens: str = 'default',
    domain: Optional[str] = None,
    mode: str = 'explore',
    domain_boost: float = 0.25,
    top_k: int = DEFAULT_TOP_K,
    token_budget: int = DEFAULT_TOKEN_BUDGET,
    max_per_source: int = 2,
) -> RAGContext:
    """
    Build complete RAG context for answer generation.

    Steps:
    1. Generate query embedding
    2. Retrieve top-K via f1_search_fusion
    3. Extract text chunks with citations
    4. De-duplicate by source
    5. Budget to token cap
    """
    # Generate embedding
    query_embedding = generate_query_embedding(query)
    if not query_embedding:
        raise ValueError("Failed to generate query embedding")

    # Retrieve results
    results = await retrieve_chunks(
        conn=conn,
        yacht_id=yacht_id,
        query=query,
        query_embedding=query_embedding,
        role=role,
        lens=lens,
        domain=domain,
        mode=mode,
        domain_boost=domain_boost,
        top_k=top_k,
    )

    # Convert to chunks with citations
    chunks = []
    for result in results:
        payload = result.get('payload', {})
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except:
                payload = {}

        doc_type = result.get('object_type', 'unknown')
        text = extract_text_from_payload(payload, doc_type)

        if not text.strip():
            continue

        citation = Citation(
            doc_id=str(result['object_id']),
            doc_type=doc_type,
            page=payload.get('page_number'),
            span_hash=compute_span_hash(text[:100]),
            title=payload.get('title') or payload.get('name'),
        )

        chunk = ContextChunk(
            text=text,
            citation=citation,
            score=float(result.get('final_score', 0)),
        )
        chunks.append(chunk)

    # De-duplicate
    chunks = deduplicate_by_source(chunks, max_per_source)

    # Budget to token cap
    chunks = budget_to_token_cap(chunks, token_budget)

    # Compute totals
    total_tokens = sum(c.tokens for c in chunks)
    query_hash = compute_query_hash(query, yacht_id, role, lens)

    return RAGContext(
        query=query,
        query_hash=query_hash,
        chunks=chunks,
        total_tokens=total_tokens,
        yacht_id=yacht_id,
        role=role,
        lens=lens,
        domain=domain,
        mode=mode,
    )


# =============================================================================
# SYNC VERSION (for testing without async)
# =============================================================================

def build_context_sync(
    conn,  # psycopg2 connection
    yacht_id: str,
    query: str,
    role: str,
    lens: str = 'default',
    domain: Optional[str] = None,
    mode: str = 'explore',
    domain_boost: float = 0.25,
    top_k: int = DEFAULT_TOP_K,
    token_budget: int = DEFAULT_TOKEN_BUDGET,
) -> RAGContext:
    """
    Synchronous version for testing.
    """
    import psycopg2.extras

    # Generate embedding
    query_embedding = generate_query_embedding(query)
    if not query_embedding:
        raise ValueError("Failed to generate query embedding")

    vec_literal = '[' + ','.join(str(x) for x in query_embedding) + ']'

    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
        SELECT
            object_id,
            object_type,
            payload,
            final_score
        FROM f1_search_fusion(
            %s::uuid, %s, %s::vector(1536), %s, %s,
            %s, %s, %s,
            0.50, 0.25, 0.15, 0.10, 0.20,
            0.01, 60, 6.0, 0.2,
            200, 200,
            %s, 0,
            true
        )
    """, (yacht_id, query, vec_literal, role, lens, domain, mode, domain_boost, top_k))

    results = [dict(r) for r in cur.fetchall()]

    # Convert to chunks
    chunks = []
    for result in results:
        payload = result.get('payload', {})
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except:
                payload = {}

        doc_type = result.get('object_type', 'unknown')
        text = extract_text_from_payload(payload, doc_type)

        if not text.strip():
            continue

        citation = Citation(
            doc_id=str(result['object_id']),
            doc_type=doc_type,
            span_hash=compute_span_hash(text[:100]),
            title=payload.get('title') or payload.get('name'),
        )

        chunk = ContextChunk(
            text=text,
            citation=citation,
            score=float(result.get('final_score', 0)),
        )
        chunks.append(chunk)

    chunks = deduplicate_by_source(chunks, 2)
    chunks = budget_to_token_cap(chunks, token_budget)

    total_tokens = sum(c.tokens for c in chunks)
    query_hash = compute_query_hash(query, yacht_id, role, lens)

    return RAGContext(
        query=query,
        query_hash=query_hash,
        chunks=chunks,
        total_tokens=total_tokens,
        yacht_id=yacht_id,
        role=role,
        lens=lens,
        domain=domain,
        mode=mode,
    )
