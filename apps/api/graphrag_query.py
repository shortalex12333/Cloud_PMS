"""
GraphRAG Query Service (Internal Engine)
=========================================

Internal search engine layer using Graph RAG with GPT extraction.
NOT a public API endpoint - called by /v1/search.

ARCHITECTURE:
    Frontend → POST /v1/search → graphrag_query.query() → Cards + Actions → Frontend

EXTRACTION:
    - GPT-4o-mini for entity extraction (same model understanding as index time)
    - text-embedding-3-small for query embeddings (same as index time)
    - match_documents() for vector similarity search

CARD TYPES (Section 8):
- document_chunk, fault, work_order, part, equipment, predictive, handover

ACTION STRUCTURE (micro-action-catalogue.md):
{
    "label": "Create Work Order",
    "action": "create_work_order",
    "endpoint": "/v1/work-orders/create",
    "method": "POST",
    "payload_template": {...},
    "constraints": {...}
}

Frontend clicks action → POST /v1/actions/execute (action-endpoint-contract.md)

GUARDRAILS:
- All queries filtered by yacht_id
- Read-only results + suggested actions
- Never mutates data directly
"""

import os
import logging
from typing import Dict, List, Optional, Tuple
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timedelta

# GPT-based extraction (replaces regex pipeline)
from gpt_extractor import get_gpt_extractor, GPTExtractor, ExtractionResult

try:
    from supabase import create_client, Client
except ImportError:
    Client = None

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# RESOLUTION & SCORING (4-Step Pipeline)
# ============================================================================
# Priority order:
# 1. Regex/canonical rules (existing patterns from Modules A+B)
# 2. resolve_entity_alias() / resolve_symptom_alias()
# 3. Graph hints (connected nodes, edges)
# 4. Vector similarity (fallback)
# ============================================================================

@dataclass
class ResolutionScore:
    """Confidence scores for entity resolution"""
    regex_score: float = 0.0      # Step 1: Pattern match confidence
    alias_score: float = 0.0      # Step 2: DB alias resolution confidence
    graph_score: float = 0.0      # Step 3: Graph connectivity score
    vector_score: float = 0.0     # Step 4: Embedding similarity score

    @property
    def total(self) -> float:
        """Weighted total score"""
        # Weights: regex > alias > graph > vector
        return (
            self.regex_score * 0.40 +
            self.alias_score * 0.30 +
            self.graph_score * 0.20 +
            self.vector_score * 0.10
        )

    @property
    def is_confident(self) -> bool:
        """True if resolution is confident enough for write actions"""
        return self.total >= 0.6 or self.regex_score >= 0.8


@dataclass
class ResultScore:
    """Scoring for search result ranking"""
    text_score: float = 0.0       # Lexical + embedding similarity
    entity_score: float = 0.0     # Exact match on equipment_id, symptom_code, etc
    graph_score: float = 0.0      # Connectivity to main entities
    recency_score: float = 0.0    # Newer items get boost for history queries

    @property
    def total(self) -> float:
        """Weighted total score for ranking"""
        return (
            self.text_score * 0.30 +
            self.entity_score * 0.35 +
            self.graph_score * 0.20 +
            self.recency_score * 0.15
        )


@dataclass
class ResolvedEntity:
    """Entity with resolution metadata"""
    text: str
    type: str
    canonical: str
    canonical_id: Optional[str] = None
    symptom_code: Optional[str] = None
    score: ResolutionScore = field(default_factory=ResolutionScore)

    def to_dict(self) -> Dict:
        return {
            "text": self.text,
            "type": self.type,
            "canonical": self.canonical,
            "canonical_id": self.canonical_id,
            "symptom_code": self.symptom_code,
            "confidence": self.score.total
        }


# ============================================================================
# CARD TYPES (search-engine-spec.md Section 8)
# ============================================================================

class CardType(str, Enum):
    # FIX: Use actual table names instead of enum strings for frontend compatibility
    # Frontend DocumentSituationView expects table names, not custom enum values
    DOCUMENT_CHUNK = "search_document_chunks"  # Was: "document_chunk"
    FAULT = "search_fault_code_catalog"        # Was: "fault"
    WORK_ORDER = "pms_work_orders"             # Was: "work_order"
    PART = "pms_parts"                         # Was: "part"
    EQUIPMENT = "pms_equipment"                # Was: "equipment"
    PREDICTIVE = "predictive_insights"         # Was: "predictive"
    HANDOVER = "handover_items"                # Was: "handover"


class QueryIntent(str, Enum):
    DIAGNOSE_FAULT = "diagnose_fault"
    FIND_DOCUMENT = "find_document"
    CREATE_WORK_ORDER = "create_work_order"
    ADD_TO_HANDOVER = "add_to_handover"
    FIND_PART = "find_part"
    GENERAL_SEARCH = "general_search"
    EQUIPMENT_HISTORY = "equipment_history"


# ============================================================================
# ACTION CATALOGUE (from micro-action-catalogue.md - CANONICAL)
# ============================================================================

ACTION_CATALOGUE = {
    # Equipment Card Actions (Section 4.1)
    "add_note": {
        "label": "Add Note",
        "action": "add_note",
        "endpoint": "/v1/notes/create",
        "method": "POST",
        "payload_fields": ["yacht_id", "equipment_id", "note_text"],
        "constraints": {"requires_equipment_id": True, "requires_note_text": True}
    },
    "create_work_order": {
        "label": "Create Work Order",
        "action": "create_work_order",
        "endpoint": "/v1/work-orders/create",
        "method": "POST",
        "payload_fields": ["yacht_id", "equipment_id", "title", "description", "priority"],
        "constraints": {"requires_equipment_id": True}
    },
    "view_history": {
        "label": "View History",
        "action": "view_history",
        "endpoint": "/v1/work-orders/history",
        "method": "GET",
        "payload_fields": ["equipment_id"],
        "constraints": {}
    },
    "add_to_handover": {
        "label": "Add to Handover",
        "action": "add_to_handover",
        "endpoint": "/v1/handover/add-item",
        "method": "POST",
        "payload_fields": ["yacht_id", "equipment_id", "summary_text"],
        "constraints": {}
    },
    # Document Card Actions (Section 4.2)
    "open_document": {
        "label": "Open Document",
        "action": "open_document",
        "endpoint": "/v1/documents/open",
        "method": "POST",
        "payload_fields": ["storage_path"],
        "constraints": {}
    },
    "add_document_to_handover": {
        "label": "Add to Handover",
        "action": "add_document_to_handover",
        "endpoint": "/v1/handover/add-document",
        "method": "POST",
        "payload_fields": ["yacht_id", "document_id", "context"],
        "constraints": {}
    },
    # Fault Card Actions (Section 4.3)
    "diagnose_fault": {
        "label": "Diagnose Fault",
        "action": "diagnose_fault",
        "endpoint": "/v1/faults/diagnose",
        "method": "GET",
        "payload_fields": ["code", "equipment_id"],
        "constraints": {}
    },
    "create_work_order_fault": {
        "label": "Create Work Order",
        "action": "create_work_order_fault",
        "endpoint": "/v1/work-orders/create",
        "method": "POST",
        "payload_fields": ["yacht_id", "suspected_fault_code", "equipment_id", "description"],
        "constraints": {}
    },
    # Part Card Actions (Section 4.5)
    "view_stock": {
        "label": "Check Stock",
        "action": "view_stock",
        "endpoint": "/v1/inventory/stock",
        "method": "GET",
        "payload_fields": ["part_id"],
        "constraints": {}
    },
    "order_part": {
        "label": "Order Part",
        "action": "order_part",
        "endpoint": "/v1/inventory/order-part",
        "method": "POST",
        "payload_fields": ["yacht_id", "part_id", "qty"],
        "constraints": {"requires_confirmation": True}
    },
}


def build_action(action_name: str, yacht_id: str, **fields) -> Optional[Dict]:
    """Build action dict with payload_template from ACTION_CATALOGUE"""
    if action_name not in ACTION_CATALOGUE:
        return None

    action_def = ACTION_CATALOGUE[action_name].copy()
    payload = {"yacht_id": yacht_id}

    for field in action_def.get("payload_fields", []):
        if field in fields and fields[field] is not None:
            payload[field] = fields[field]
        elif field != "yacht_id":
            payload[field] = ""

    action_def["payload_template"] = payload
    return action_def


def build_card(card_type: CardType, title: str, yacht_id: str, actions: List[str] = None, **data) -> Dict:
    """Build spec-compliant card with canonical fields for frontend compatibility"""

    # Determine primary_id based on card type and available data
    primary_id = None
    if card_type == CardType.DOCUMENT_CHUNK:
        # For documents: prefer chunk id, fallback to document_id
        primary_id = data.get("id") or data.get("chunk_id") or data.get("document_id")
    elif card_type == CardType.FAULT:
        primary_id = data.get("id") or data.get("fault_id")
    elif card_type == CardType.WORK_ORDER:
        primary_id = data.get("id") or data.get("work_order_id")
    elif card_type == CardType.PART:
        primary_id = data.get("id") or data.get("part_id")
    elif card_type == CardType.EQUIPMENT:
        primary_id = data.get("id") or data.get("equipment_id")
    elif card_type == CardType.HANDOVER:
        primary_id = data.get("id") or data.get("handover_id")
    else:
        # Generic fallback
        primary_id = data.get("id")

    # Build card with canonical fields that frontend expects
    card = {
        "type": card_type.value,           # Table name (e.g., "search_document_chunks")
        "source_table": card_type.value,   # Same as type for consistency
        "primary_id": primary_id,          # UUID of the record
        "title": title,
        **data  # All original data preserved
    }

    if actions:
        card["actions"] = []
        for action_name in actions:
            action = build_action(action_name, yacht_id, **data)
            if action:
                card["actions"].append(action)

    return card


# ============================================================================
# GRAPHRAG QUERY SERVICE
# ============================================================================

class GraphRAGQueryService:
    """
    Internal GraphRAG query service - called by /v1/search.

    Uses GPT-4o-mini for entity extraction and text-embedding-3-small for embeddings.
    Same models as used at index time for consistent semantic matching.
    """

    def __init__(self, supabase_url: str = None, supabase_key: str = None):
        self.supabase_url = supabase_url or os.getenv("SUPABASE_URL")
        self.supabase_key = supabase_key or os.getenv("SUPABASE_SERVICE_KEY")

        if self.supabase_url and self.supabase_key and Client:
            self.client: Client = create_client(self.supabase_url, self.supabase_key)
        else:
            self.client = None

        # GPT extractor for entity extraction + embeddings
        try:
            self.gpt = get_gpt_extractor()
        except Exception as e:
            logger.warning(f"GPT extractor not available: {e}. Falling back to basic search.")
            self.gpt = None

        # Initialize lens registries for capability-based search and microactions
        self.capability_registry = None
        self.microaction_registry = None
        if self.client:
            try:
                from prepare.capability_registry import CapabilityRegistry
                from microactions.microaction_registry import MicroactionRegistry

                self.capability_registry = CapabilityRegistry(self.client)
                self.capability_registry.discover_and_register()

                self.microaction_registry = MicroactionRegistry(self.client)
                self.microaction_registry.discover_and_register()

                logger.info("✅ Lens registries initialized")
            except Exception as e:
                logger.warning(f"Lens registries not available: {e}. Microactions disabled.")

    def query(self, yacht_id: str, query_text: str) -> Dict:
        """
        Execute GraphRAG query using GPT extraction + vector search.

        Pipeline:
        1. GPT-4o-mini extracts entities and detects action
        2. text-embedding-3-small generates query embedding
        3. match_documents() finds similar documents
        4. Resolve entities against DB aliases
        5. Build cards from results

        Called internally by /v1/search, NOT directly by frontend.
        """
        # Step 1: GPT extraction (entities + action)
        if self.gpt:
            extraction = self.gpt.extract(query_text)
            intent = self._determine_intent_from_gpt(extraction)
            person_filter = extraction.person_filter
        else:
            # Fallback if GPT not available
            extraction = None
            intent = QueryIntent.GENERAL_SEARCH
            person_filter = None

        # Step 2: Generate query embedding for vector search
        query_embedding = None
        if self.gpt:
            query_embedding = self.gpt.embed(query_text)

        # Step 3: Vector search via match_documents()
        similar_docs = []
        if query_embedding and self.client:
            similar_docs = self._match_documents(yacht_id, query_embedding, match_count=10)

        # Step 4: Resolve entities against DB
        if extraction:
            entities = self._resolve_entities_from_gpt(yacht_id, extraction)
        else:
            entities = []

        # Step 5: Build cards
        cards = self._execute_query(yacht_id, intent, query_text, entities, similar_docs, person_filter)

        # Step 6: Add microactions to cards (lens-based action suggestions)
        if self.microaction_registry:
            cards = self._enrich_cards_with_microactions(yacht_id, cards, intent.value, query_text)

        return {
            "query": query_text,
            "intent": intent.value,
            "entities": entities,
            "cards": cards,
            "metadata": {
                "entity_count": len(entities),
                "card_count": len(cards),
                "vector_matches": len(similar_docs),
                "extraction_confidence": extraction.action_confidence if extraction else 0.0
            }
        }

    def _match_documents(self, yacht_id: str, query_embedding: List[float], match_count: int = 10) -> List[Dict]:
        """
        Vector similarity search using match_documents() Supabase function.

        This is the SAME function used in rag_baseline.json for retrieval.
        Uses cosine similarity: 1 - (embedding <=> query_embedding)

        Args:
            yacht_id: Filter by yacht
            query_embedding: 1536-dim embedding from text-embedding-3-small
            match_count: Number of results to return

        Returns:
            List of matching documents with similarity scores
        """
        if not self.client:
            return []

        try:
            result = self.client.rpc('match_documents', {
                'filter': {"yacht_id": yacht_id},
                'match_count': match_count,
                'query_embedding': query_embedding
            }).execute()

            return result.data or []

        except Exception as e:
            logger.error(f"match_documents failed: {e}")
            # Fallback to basic text search
            return []

    def _determine_intent_from_gpt(self, extraction: ExtractionResult) -> QueryIntent:
        """Map GPT-detected action to intent taxonomy"""
        action = extraction.action if extraction else "general_search"

        intent_map = {
            "diagnose_fault": QueryIntent.DIAGNOSE_FAULT,
            "open_document": QueryIntent.FIND_DOCUMENT,
            "find_document": QueryIntent.FIND_DOCUMENT,
            "find_manual": QueryIntent.FIND_DOCUMENT,
            "create_work_order": QueryIntent.CREATE_WORK_ORDER,
            "add_to_handover": QueryIntent.ADD_TO_HANDOVER,
            "find_part": QueryIntent.FIND_PART,
            "check_stock": QueryIntent.FIND_PART,
            "order_parts": QueryIntent.FIND_PART,
            "view_history": QueryIntent.EQUIPMENT_HISTORY,
            "general_search": QueryIntent.GENERAL_SEARCH,
        }

        return intent_map.get(action, QueryIntent.GENERAL_SEARCH)

    def _resolve_entities_from_gpt(self, yacht_id: str, extraction: ExtractionResult) -> List[Dict]:
        """
        Resolve GPT-extracted entities against database.

        Pipeline:
        1. GPT confidence (already provided)
        2. DB alias lookup
        3. Graph hints (if alias fails)
        4. Vector similarity (fallback - already done in match_documents)
        """
        resolved = []

        for entity in extraction.entities:
            score = ResolutionScore()
            score.regex_score = entity.confidence  # GPT confidence = "regex" score

            # Get canonical (Module B has it, GPT extractor doesn't)
            canonical = getattr(entity, 'canonical', None) or entity.value.upper().replace(" ", "_")

            resolved_entity = ResolvedEntity(
                text=entity.value,
                type=entity.type,
                canonical=canonical,
                score=score
            )

            # Step 2: DB alias lookup
            if entity.type in ("equipment", "part", "fault_code", "supplier"):
                canonical_id = self._resolve_entity_alias(yacht_id, entity.type, canonical)
                if canonical_id:
                    resolved_entity.canonical_id = canonical_id
                    score.alias_score = 0.9
                else:
                    # Try with original value
                    canonical_id = self._resolve_entity_alias(yacht_id, entity.type, entity.value)
                    if canonical_id:
                        resolved_entity.canonical_id = canonical_id
                        score.alias_score = 0.7

            elif entity.type in ("symptom", "maritime_term"):
                code = self._resolve_symptom_alias(entity.value)
                if code:
                    resolved_entity.canonical_id = code
                    resolved_entity.symptom_code = code
                    score.alias_score = 0.85

            # Step 3: Graph hints (if no alias match)
            if not resolved_entity.canonical_id and self.client:
                graph_id = self._resolve_via_graph(yacht_id, entity.type, entity.value, canonical)
                if graph_id:
                    resolved_entity.canonical_id = graph_id
                    score.graph_score = 0.6

            resolved.append(resolved_entity.to_dict())

        return resolved

    def _resolve_entities(self, yacht_id: str, extraction: Dict) -> List[Dict]:
        """
        Resolve entities using 4-step priority pipeline.

        RESOLUTION PIPELINE:
        1. Regex/canonical rules (from Module B extraction) - highest priority
        2. resolve_entity_alias() / resolve_symptom_alias() - database lookup
        3. Graph hints - check graph_nodes for matching labels
        4. Vector similarity - fallback (not yet implemented)

        Returns List[Dict] with confidence scores for ranking.
        """
        resolved = []
        for entity in extraction.get("canonical_entities", []):
            score = ResolutionScore()
            etype = entity.get("type", "")
            canonical = entity.get("canonical", "")
            value = entity.get("value", "")

            # STEP 1: Regex/canonical rules (already applied in Module B)
            # The confidence from extraction IS the regex score
            regex_confidence = entity.get("confidence", 0.0)
            score.regex_score = regex_confidence

            resolved_entity = ResolvedEntity(
                text=value,
                type=etype,
                canonical=canonical,
                score=score
            )

            # STEP 2: Database alias resolution
            if etype in ("equipment", "part", "fault_code", "supplier"):
                canonical_id = self._resolve_entity_alias(yacht_id, etype, canonical)
                if canonical_id:
                    resolved_entity.canonical_id = canonical_id
                    score.alias_score = 0.9  # High confidence on DB match
                else:
                    # Try with original value as fallback
                    canonical_id = self._resolve_entity_alias(yacht_id, etype, value)
                    if canonical_id:
                        resolved_entity.canonical_id = canonical_id
                        score.alias_score = 0.7  # Lower confidence on value match

            elif etype in ("maritime_term", "symptom"):
                code = self._resolve_symptom_alias(value)
                if code:
                    resolved_entity.canonical_id = code
                    resolved_entity.symptom_code = code
                    score.alias_score = 0.85

            # STEP 3: Graph hints (if no alias match, check graph_nodes)
            if not resolved_entity.canonical_id and self.client:
                graph_id = self._resolve_via_graph(yacht_id, etype, value, canonical)
                if graph_id:
                    resolved_entity.canonical_id = graph_id
                    score.graph_score = 0.6  # Lower confidence on graph-only match

            # STEP 4: Vector similarity (placeholder for future)
            # If still no match, could query embeddings here
            # score.vector_score = self._resolve_via_vector(yacht_id, value)

            resolved.append(resolved_entity.to_dict())

        return resolved

    def _resolve_via_graph(self, yacht_id: str, etype: str, value: str, canonical: str) -> Optional[str]:
        """
        Step 3: Try to resolve entity via graph_nodes label matching.
        Used when alias resolution fails.
        """
        if not self.client:
            return None

        try:
            # Search graph_nodes for matching labels
            type_map = {"equipment": "equipment", "part": "part", "fault_code": "fault", "symptom": "symptom"}
            node_type = type_map.get(etype, etype)

            result = self.client.table("graph_nodes").select("canonical_id").eq(
                "yacht_id", yacht_id
            ).eq("node_type", node_type).or_(
                f"label.ilike.%{value}%,label.ilike.%{canonical}%"
            ).limit(1).execute()

            if result.data and result.data[0].get("canonical_id"):
                return result.data[0]["canonical_id"]
            return None

        except Exception as e:
            logger.debug(f"Graph resolution failed for {value}: {e}")
            return None

    def _resolve_entity_alias(self, yacht_id: str, etype: str, alias: str) -> Optional[str]:
        if not self.client:
            return None
        type_map = {"equipment": "equipment", "part": "part", "fault_code": "fault"}
        try:
            result = self.client.rpc("resolve_entity_alias", {
                "p_yacht_id": yacht_id,
                "p_entity_type": type_map.get(etype, etype),
                "p_alias_text": alias
            }).execute()
            return result.data if result.data else None
        except Exception:
            return None

    def _resolve_symptom_alias(self, alias: str) -> Optional[str]:
        if not self.client:
            return None
        try:
            result = self.client.rpc("resolve_symptom_alias", {"p_alias_text": alias}).execute()
            return result.data if result.data else None
        except Exception:
            return None

    # ========================================================================
    # INTENT EXECUTION
    # ========================================================================

    def _execute_query(self, yacht_id: str, intent: QueryIntent, query: str, entities: List[Dict]) -> List[Dict]:
        """Execute intent-specific query pattern"""
        if intent == QueryIntent.DIAGNOSE_FAULT:
            return self._query_fault(yacht_id, query, entities)
        elif intent == QueryIntent.FIND_DOCUMENT:
            return self._query_document(yacht_id, query, entities)
        elif intent == QueryIntent.FIND_PART:
            return self._query_part(yacht_id, query, entities)
        elif intent == QueryIntent.EQUIPMENT_HISTORY:
            return self._query_equipment(yacht_id, query, entities)
        elif intent == QueryIntent.CREATE_WORK_ORDER:
            return self._query_create_wo(yacht_id, query, entities)
        else:
            return self._query_general(yacht_id, query, entities)

    def _query_fault(self, yacht_id: str, query: str, entities: List[Dict]) -> List[Dict]:
        """
        DIAGNOSE_FAULT Pattern:
        1. Extract fault_code → lookup faults table
        2. Search document_chunks for fault mentions
        3. Traverse graph_edges for related equipment/symptoms
        Returns: fault card + related document cards
        """
        cards = []
        fault_entities = [e for e in entities if e.get("type") == "fault_code"]
        equip_entities = [e for e in entities if e.get("type") == "equipment"]
        equipment_id = equip_entities[0].get("canonical_id") if equip_entities else None

        for f in fault_entities:
            code = f.get("canonical", f.get("text", ""))
            info = self._get_fault(yacht_id, code)

            cards.append(build_card(
                CardType.FAULT, f"Fault {code}", yacht_id,
                actions=["diagnose_fault", "create_work_order_fault", "add_note"],
                id=info.get("id") if info else None,  # FIX: Add fault id for primary_id field
                fault_code=code, equipment_id=equipment_id,
                summary=info.get("description", "") if info else "",
                severity=info.get("severity") if info else None
            ))

            # Related documents
            for chunk in self._search_chunks(yacht_id, code)[:3]:
                cards.append(build_card(
                    CardType.DOCUMENT_CHUNK, chunk.get("section_title", "Document"), yacht_id,
                    actions=["open_document", "add_document_to_handover"],
                    id=chunk.get("id"),  # FIX: Add chunk id for primary_id field
                    document_id=chunk.get("document_id"),
                    page_number=chunk.get("page_number"),
                    text_preview=chunk.get("content", "")[:200],
                    storage_path=chunk.get("storage_path", "")
                ))
        return cards

    def _query_document(self, yacht_id: str, query: str, entities: List[Dict]) -> List[Dict]:
        """
        FIND_DOCUMENT Pattern:
        1. Resolve equipment → find graph_nodes linking to chunks
        2. Search document_chunks by content + section_title
        Returns: document_chunk cards
        """
        cards = []
        for chunk in self._search_chunks(yacht_id, query)[:8]:
            cards.append(build_card(
                CardType.DOCUMENT_CHUNK, chunk.get("section_title", "Document"), yacht_id,
                actions=["open_document", "add_document_to_handover"],
                id=chunk.get("id"),  # FIX: Add chunk id for primary_id field
                document_id=chunk.get("document_id"),
                page_number=chunk.get("page_number"),
                text_preview=chunk.get("content", "")[:200],
                storage_path=chunk.get("storage_path", "")
            ))
        return cards

    def _query_part(self, yacht_id: str, query: str, entities: List[Dict]) -> List[Dict]:
        """
        FIND_PART Pattern:
        1. Search parts table
        2. If equipment specified, traverse graph_edges (USES_PART)
        Returns: part cards
        """
        cards = []
        for part in self._search_parts(yacht_id, query)[:5]:
            cards.append(build_card(
                CardType.PART, part.get("canonical_name", "Part"), yacht_id,
                actions=["view_stock", "order_part", "add_to_handover"],
                id=part.get("id"),  # FIX: Add part id for primary_id field
                part_id=part.get("id"),
                name=part.get("canonical_name"),
                in_stock=part.get("current_stock", 0),
                location=part.get("location", "")
            ))
        return cards

    def _query_equipment(self, yacht_id: str, query: str, entities: List[Dict]) -> List[Dict]:
        """
        EQUIPMENT_HISTORY Pattern:
        1. Resolve equipment → canonical_id
        2. Traverse graph_edges for faults/symptoms/work_orders
        3. Filter by person/role if specified
        4. Include handover items if symptom context present
        Returns: equipment card + work_order cards + handover cards
        """
        cards = []
        equip = [e for e in entities if e.get("type") == "equipment"]
        symptoms = [e for e in entities if e.get("type") in ("maritime_term", "symptom")]
        persons = [e for e in entities if e.get("type") == "person"]
        person_filter = persons[0].get("canonical") if persons else None

        for e in equip:
            eid = e.get("canonical_id")
            symptom_text = symptoms[0].get("text") if symptoms else None
            symptom_code = symptoms[0].get("symptom_code") if symptoms else None

            # Equipment card with detected symptom
            cards.append(build_card(
                CardType.EQUIPMENT, e.get("text", "Equipment"), yacht_id,
                actions=["view_history", "create_work_order", "add_note", "add_to_handover"],
                id=eid,  # FIX: Add equipment id for primary_id field
                equipment_id=eid,
                symptom_detected=symptom_text,
                symptom_code=symptom_code,
                person_filter=person_filter
            ))

            # Get work orders filtered by person if specified
            work_orders = self._get_work_orders_filtered(yacht_id, eid, person_filter, symptom_text)
            for wo in work_orders[:5]:
                cards.append(build_card(
                    CardType.WORK_ORDER, wo.get("title", "Work Order"), yacht_id,
                    actions=["view_history", "add_to_handover"],
                    id=wo.get("id"),  # FIX: Add work order id for primary_id field
                    work_order_id=wo.get("id"),
                    status=wo.get("status"),
                    equipment_id=eid,
                    created_by=wo.get("created_by"),
                    created_at=wo.get("created_at"),
                    resolution=wo.get("resolution")
                ))

            # Get handover items if symptom present
            if symptom_text:
                handovers = self._get_handover_items(yacht_id, eid, person_filter, symptom_text)
                for hi in handovers[:3]:
                    cards.append(build_card(
                        CardType.HANDOVER, hi.get("summary", "Handover Item"), yacht_id,
                        actions=["add_to_handover"],
                        id=hi.get("id"),  # FIX: Add handover id for primary_id field
                        handover_id=hi.get("id"),
                        author=hi.get("author"),
                        content=hi.get("content", "")[:200],
                        created_at=hi.get("created_at")
                    ))

            # Get graph-related documents mentioning this symptom + equipment
            if symptom_text:
                docs = self._get_symptom_documents(yacht_id, eid, symptom_text)
                for doc in docs[:3]:
                    cards.append(build_card(
                        CardType.DOCUMENT_CHUNK, doc.get("section_title", "Related Document"), yacht_id,
                        actions=["open_document", "add_document_to_handover"],
                        id=doc.get("id"),  # FIX: Add chunk id for primary_id field
                        document_id=doc.get("document_id"),
                        page_number=doc.get("page_number"),
                        text_preview=doc.get("content", "")[:200],
                        storage_path=doc.get("storage_path", "")
                    ))

        return cards

    def _query_create_wo(self, yacht_id: str, query: str, entities: List[Dict]) -> List[Dict]:
        """CREATE_WORK_ORDER Pattern: Return equipment card with create_work_order action"""
        cards = []
        equip = [e for e in entities if e.get("type") == "equipment"]
        symptoms = [e for e in entities if e.get("type") in ("maritime_term", "symptom")]

        for e in equip:
            cards.append(build_card(
                CardType.EQUIPMENT, e.get("text", "Equipment"), yacht_id,
                actions=["create_work_order", "add_note"],
                equipment_id=e.get("canonical_id"),
                title=f"{e.get('text', '')} - {symptoms[0].get('text', 'Issue') if symptoms else 'Inspection'}",
                description=query
            ))
        return cards

    def _query_general(self, yacht_id: str, query: str, entities: List[Dict]) -> List[Dict]:
        """GENERAL_SEARCH: Multi-source fallback"""
        cards = []
        for chunk in self._search_chunks(yacht_id, query)[:5]:
            cards.append(build_card(
                CardType.DOCUMENT_CHUNK, chunk.get("section_title", "Document"), yacht_id,
                actions=["open_document", "add_document_to_handover"],
                document_id=chunk.get("document_id"),
                text_preview=chunk.get("content", "")[:200],
                storage_path=chunk.get("storage_path", "")
            ))

        for e in entities:
            if e.get("type") == "equipment":
                cards.append(build_card(
                    CardType.EQUIPMENT, e.get("text", "Equipment"), yacht_id,
                    actions=["view_history", "create_work_order", "add_note"],
                    equipment_id=e.get("canonical_id")
                ))
        return cards

    # ========================================================================
    # DB HELPERS
    # ========================================================================

    def _get_fault(self, yacht_id: str, code: str) -> Optional[Dict]:
        if not self.client:
            return None
        try:
            return self.client.table("faults").select("*").eq("yacht_id", yacht_id).eq("fault_code", code).single().execute().data
        except Exception:
            return None

    def _search_chunks(self, yacht_id: str, text: str) -> List[Dict]:
        if not self.client:
            return []
        try:
            return self.client.table("document_chunks").select(
                "id,document_id,content,section_title,page_number,storage_path"
            ).eq("yacht_id", yacht_id).ilike("content", f"%{text}%").limit(10).execute().data or []
        except Exception:
            return []

    def _search_parts(self, yacht_id: str, text: str) -> List[Dict]:
        if not self.client:
            return []
        try:
            return self.client.table("parts").select("*").eq("yacht_id", yacht_id).or_(
                f"canonical_name.ilike.%{text}%,part_number.ilike.%{text}%"
            ).limit(10).execute().data or []
        except Exception:
            return []

    def _get_work_orders(self, yacht_id: str, equipment_id: str) -> List[Dict]:
        if not self.client or not equipment_id:
            return []
        try:
            return self.client.table("work_orders").select("*").eq("yacht_id", yacht_id).eq(
                "equipment_id", equipment_id
            ).order("created_at", desc=True).limit(10).execute().data or []
        except Exception:
            return []

    def _get_work_orders_filtered(
        self, yacht_id: str, equipment_id: str, person_filter: str = None, symptom_text: str = None
    ) -> List[Dict]:
        """
        Get work orders with optional person and symptom filters.

        SQL equivalent:
        SELECT wo.*
        FROM work_orders wo
        WHERE wo.yacht_id = $yacht_id
          AND wo.equipment_id = $equipment_id
          AND ($person_filter IS NULL OR wo.created_by ILIKE '%' || $person_filter || '%')
          AND ($symptom_text IS NULL OR wo.description ILIKE '%' || $symptom_text || '%')
        ORDER BY wo.created_at DESC
        LIMIT 10;
        """
        if not self.client:
            return []
        try:
            query = self.client.table("work_orders").select(
                "id,title,description,status,created_by,created_at,resolution,equipment_id"
            ).eq("yacht_id", yacht_id)

            if equipment_id:
                query = query.eq("equipment_id", equipment_id)

            # Filter by person/role (created_by column)
            if person_filter:
                # Convert "2ND_ENGINEER" to search pattern
                search_term = person_filter.replace("_", " ").replace("2ND", "2nd")
                query = query.ilike("created_by", f"%{search_term}%")

            # Filter by symptom in description
            if symptom_text:
                query = query.ilike("description", f"%{symptom_text}%")

            return query.order("created_at", desc=True).limit(10).execute().data or []
        except Exception:
            return []

    def _get_handover_items(
        self, yacht_id: str, equipment_id: str = None, person_filter: str = None, symptom_text: str = None
    ) -> List[Dict]:
        """
        Get handover items with optional filters.

        SQL equivalent:
        SELECT hi.*
        FROM handover_items hi
        WHERE hi.yacht_id = $yacht_id
          AND ($equipment_id IS NULL OR hi.equipment_id = $equipment_id)
          AND ($person_filter IS NULL OR hi.author ILIKE '%' || $person_filter || '%')
          AND ($symptom_text IS NULL OR hi.content ILIKE '%' || $symptom_text || '%')
        ORDER BY hi.created_at DESC
        LIMIT 5;
        """
        if not self.client:
            return []
        try:
            query = self.client.table("handover_items").select(
                "id,summary,content,author,created_at,equipment_id"
            ).eq("yacht_id", yacht_id)

            if equipment_id:
                query = query.eq("equipment_id", equipment_id)

            if person_filter:
                search_term = person_filter.replace("_", " ").replace("2ND", "2nd")
                query = query.ilike("author", f"%{search_term}%")

            if symptom_text:
                query = query.ilike("content", f"%{symptom_text}%")

            return query.order("created_at", desc=True).limit(5).execute().data or []
        except Exception:
            return []

    def _get_symptom_documents(self, yacht_id: str, equipment_id: str, symptom_text: str) -> List[Dict]:
        """
        Get documents mentioning symptom and equipment via graph traversal.

        SQL equivalent (using graph_edges):
        SELECT DISTINCT dc.id, dc.document_id, dc.content, dc.section_title,
               dc.page_number, dc.storage_path
        FROM document_chunks dc
        JOIN graph_nodes gn ON gn.ref_id = dc.id AND gn.ref_table = 'document_chunks'
        JOIN graph_edges ge ON ge.from_node_id = gn.id OR ge.to_node_id = gn.id
        WHERE dc.yacht_id = $yacht_id
          AND (gn.canonical_id = $equipment_id OR gn.label ILIKE '%engine%')
          AND (
              dc.content ILIKE '%' || $symptom_text || '%'
              OR ge.edge_type = 'HAS_SYMPTOM'
          )
        ORDER BY dc.created_at DESC
        LIMIT 5;
        """
        if not self.client:
            return []
        try:
            # First, search document_chunks directly for symptom mentions
            return self.client.table("document_chunks").select(
                "id,document_id,content,section_title,page_number,storage_path"
            ).eq("yacht_id", yacht_id).ilike(
                "content", f"%{symptom_text}%"
            ).limit(5).execute().data or []
        except Exception:
            return []

    def _enrich_cards_with_microactions(self, yacht_id: str, cards: List[Dict],
                                         query_intent: str, query_text: str,
                                         user_role: str = "chief_engineer") -> List[Dict]:
        """Enrich cards with lens-based microaction suggestions."""
        import asyncio

        async def enrich_card(card: Dict) -> Dict:
            # Get lens name from card type
            lens_name = self._get_lens_name_from_card_type(card.get("type", ""))
            if not lens_name:
                return card

            # Get entity type and ID
            entity_type = self._get_entity_type_from_card_type(card.get("type", ""))
            entity_id = card.get("primary_id") or card.get("id")

            if not entity_id:
                return card

            # Get microaction suggestions
            try:
                suggestions = await self.microaction_registry.get_suggestions(
                    lens_name=lens_name,
                    entity_type=entity_type,
                    entity_id=entity_id,
                    entity_data=card,
                    user_role=user_role,
                    yacht_id=yacht_id,
                    query_intent=query_intent
                )

                # Convert to dict format
                card["suggested_actions"] = [
                    {
                        "action_id": s.action_id,
                        "label": s.label,
                        "variant": s.variant,
                        "priority": s.priority,
                        "prefill_data": s.prefill_data
                    }
                    for s in suggestions
                ]
            except Exception as e:
                logger.warning(f"Failed to get microactions for card {entity_id}: {e}")
                card["suggested_actions"] = []

            return card

        # Run async enrichment
        try:
            loop = asyncio.get_event_loop()
            enriched_cards = loop.run_until_complete(
                asyncio.gather(*[enrich_card(card) for card in cards])
            )
            return list(enriched_cards)
        except Exception as e:
            logger.error(f"Failed to enrich cards with microactions: {e}")
            return cards

    def _get_lens_name_from_card_type(self, card_type: str) -> Optional[str]:
        """Map card type to lens name."""
        type_to_lens = {
            "pms_parts": "part_lens",
            "part": "part_lens",
            "crew": "crew_lens",
            "certificate": "certificate_lens",
            "equipment": "equipment_lens",
            "work_order": "work_order_lens",
        }
        return type_to_lens.get(card_type)

    def _get_entity_type_from_card_type(self, card_type: str) -> str:
        """Map card type to entity type for microaction lookup."""
        type_to_entity = {
            "pms_parts": "part",
            "part": "part",
            "crew": "crew_member",
            "certificate": "certificate",
            "equipment": "equipment",
            "work_order": "work_order",
        }
        return type_to_entity.get(card_type, card_type)

    def get_graph_stats(self, yacht_id: str) -> Dict:
        """Admin: Get graph stats from v_graph_stats"""
        if not self.client:
            return {}
        try:
            return self.client.table("v_graph_stats").select("*").eq("yacht_id", yacht_id).single().execute().data or {}
        except Exception:
            return {}

    def get_extraction_stats(self, yacht_id: str) -> List[Dict]:
        """Admin: Get extraction status from v_extraction_status"""
        if not self.client:
            return []
        try:
            return self.client.table("v_extraction_status").select("*").eq("yacht_id", yacht_id).execute().data or []
        except Exception:
            return []


# ============================================================================
# SINGLETON
# ============================================================================

_instance = None

def get_query_service() -> GraphRAGQueryService:
    global _instance
    if _instance is None:
        _instance = GraphRAGQueryService()
    return _instance
