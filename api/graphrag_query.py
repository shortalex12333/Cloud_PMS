"""
GraphRAG Query Service
=======================

Intent-based search using the Graph RAG layer.

This service provides search capabilities that combine:
- Entity resolution (aliases -> canonical IDs)
- Graph traversal (nodes -> edges -> related entities)
- Vector search (document_chunks embeddings)
- Micro-action generation (action + payloads)

SUPPORTED INTENTS:
1. find_document_section - "Open Cat main engine manual to lube oil section"
2. equipment_history - "Engine is overheating, show historic data"
3. diagnose_fault - "What does error E047 mean?"
4. find_part - "Find filter for port main engine"
5. relationship_traversal - "What parts are affected if heat exchanger fails?"
6. maintenance_lookup - "When is oil change due on generator 1?"

ARCHITECTURE:
┌─────────────────────┐
│  User Query         │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Intent Detection   │  (Module A: action detector)
│  + Entity Extraction│  (Module B: entity extractor)
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Entity Resolution  │  resolve_entity_alias()
│  (aliases -> IDs)   │  resolve_symptom_alias()
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Graph Traversal    │  SELECT from graph_nodes/edges
│  + Vector Search    │  Cosine similarity on embeddings
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Result Cards +     │  equipment_card, document_card, etc.
│  Micro-Actions      │  open_document, create_work_order, etc.
└─────────────────────┘

GUARDRAILS:
- All queries filtered by yacht_id
- Read-only results + suggested actions (no direct mutations)
- Ambiguous intent -> read-only results only
- Confidence thresholds for action suggestions
"""

import os
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field, asdict
from enum import Enum
import json

# Import unified extraction pipeline
from unified_extraction_pipeline import get_pipeline

# Database client
try:
    from supabase import create_client, Client
except ImportError:
    Client = None

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# ENUMS
# ============================================================================

class QueryIntent(str, Enum):
    """Supported query intents"""
    FIND_DOCUMENT_SECTION = "find_document_section"
    EQUIPMENT_HISTORY = "equipment_history"
    DIAGNOSE_FAULT = "diagnose_fault"
    FIND_PART = "find_part"
    RELATIONSHIP_TRAVERSAL = "relationship_traversal"
    MAINTENANCE_LOOKUP = "maintenance_lookup"
    HANDOVER_RELATED = "handover_related"
    GENERAL_SEARCH = "general_search"


class CardType(str, Enum):
    """Result card types"""
    EQUIPMENT = "equipment_card"
    DOCUMENT = "document_card"
    PART = "part_card"
    FAULT = "fault_card"
    WORK_ORDER = "work_order_card"
    HANDOVER = "handover_card"
    MAINTENANCE = "maintenance_card"
    SYMPTOM = "symptom_card"


class ActionType(str, Enum):
    """Micro-action types"""
    OPEN_DOCUMENT = "open_document"
    SHOW_HISTORY = "show_history"
    CREATE_WORK_ORDER = "create_work_order"
    SHOW_PARTS = "show_parts"
    SHOW_MAINTENANCE = "show_maintenance"
    SHOW_FAULT_INFO = "show_fault_info"
    ORDER_PART = "order_part"
    ADD_TO_HANDOVER = "add_to_handover"


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class ResolvedEntity:
    """Entity resolved to canonical ID"""
    original_text: str
    entity_type: str
    canonical_id: Optional[str] = None
    canonical_name: Optional[str] = None
    confidence: float = 0.0
    metadata: Dict = field(default_factory=dict)


@dataclass
class ResultCard:
    """Search result card"""
    card_type: CardType
    title: str
    subtitle: Optional[str] = None
    confidence: float = 0.0
    data: Dict = field(default_factory=dict)
    source_chunk_id: Optional[str] = None
    source_document_id: Optional[str] = None


@dataclass
class SuggestedAction:
    """Suggested micro-action"""
    action: ActionType
    confidence: float
    requires_confirmation: bool = True
    parameters: Dict = field(default_factory=dict)
    context: Dict = field(default_factory=dict)


@dataclass
class QueryResult:
    """Complete query result"""
    query: str
    intent: QueryIntent
    intent_confidence: float
    resolved_entities: List[ResolvedEntity]
    cards: List[ResultCard]
    suggested_actions: List[SuggestedAction]
    graph_stats: Dict = field(default_factory=dict)
    metadata: Dict = field(default_factory=dict)


# ============================================================================
# CONFIDENCE THRESHOLDS
# ============================================================================

ACTION_THRESHOLDS = {
    ActionType.OPEN_DOCUMENT: 0.60,      # Low risk, reversible
    ActionType.SHOW_HISTORY: 0.50,       # Informational only
    ActionType.SHOW_PARTS: 0.50,         # Informational only
    ActionType.SHOW_MAINTENANCE: 0.50,   # Informational only
    ActionType.SHOW_FAULT_INFO: 0.50,    # Informational only
    ActionType.CREATE_WORK_ORDER: 0.80,  # Requires confirmation
    ActionType.ADD_TO_HANDOVER: 0.75,    # Requires confirmation
    ActionType.ORDER_PART: 0.90,         # Financial impact
}


# ============================================================================
# GRAPHRAG QUERY SERVICE
# ============================================================================

class GraphRAGQueryService:
    """
    GraphRAG query service for intent-based searches.

    Combines entity resolution, graph traversal, and vector search
    to produce result cards and suggested micro-actions.
    """

    def __init__(self, supabase_url: str = None, supabase_key: str = None):
        self.supabase_url = supabase_url or os.getenv("SUPABASE_URL")
        self.supabase_key = supabase_key or os.getenv("SUPABASE_SERVICE_KEY")

        if self.supabase_url and self.supabase_key and Client:
            self.client: Client = create_client(self.supabase_url, self.supabase_key)
            logger.info("GraphRAG Query Service initialized with Supabase")
        else:
            self.client = None
            logger.warning("GraphRAG Query Service running without Supabase")

        # Load unified extraction pipeline
        self.pipeline = get_pipeline()

        # Intent mapping from detected actions
        self.action_to_intent = {
            "open_document": QueryIntent.FIND_DOCUMENT_SECTION,
            "find_document": QueryIntent.FIND_DOCUMENT_SECTION,
            "diagnose_fault": QueryIntent.DIAGNOSE_FAULT,
            "view_fault": QueryIntent.DIAGNOSE_FAULT,
            "create_work_order": QueryIntent.EQUIPMENT_HISTORY,
            "find_part": QueryIntent.FIND_PART,
            "order_part": QueryIntent.FIND_PART,
            "view_maintenance": QueryIntent.MAINTENANCE_LOOKUP,
            "schedule_maintenance": QueryIntent.MAINTENANCE_LOOKUP,
            "add_to_handover": QueryIntent.HANDOVER_RELATED,
            "view_handover": QueryIntent.HANDOVER_RELATED,
        }

    # ========================================================================
    # MAIN QUERY METHOD
    # ========================================================================

    def query(self, yacht_id: str, query_text: str) -> QueryResult:
        """
        Execute GraphRAG query.

        Args:
            yacht_id: Tenant yacht ID
            query_text: User natural language query

        Returns:
            QueryResult with cards and suggested actions
        """
        logger.info(f"GraphRAG query: yacht={yacht_id}, query='{query_text}'")

        # STEP 1: Extract entities and detect intent
        extraction = self.pipeline.extract(query_text)

        # STEP 2: Determine query intent
        intent, intent_confidence = self._determine_intent(extraction)

        # STEP 3: Resolve entities to canonical IDs
        resolved_entities = self._resolve_entities(yacht_id, extraction)

        # STEP 4: Execute intent-specific query
        cards, actions = self._execute_intent_query(
            yacht_id=yacht_id,
            intent=intent,
            query_text=query_text,
            extraction=extraction,
            resolved_entities=resolved_entities
        )

        # STEP 5: Get graph stats for context
        graph_stats = self._get_graph_stats(yacht_id)

        return QueryResult(
            query=query_text,
            intent=intent,
            intent_confidence=intent_confidence,
            resolved_entities=resolved_entities,
            cards=cards,
            suggested_actions=actions,
            graph_stats=graph_stats,
            metadata={
                "extraction": extraction.get("metadata", {}),
                "entity_count": len(resolved_entities),
                "card_count": len(cards),
                "action_count": len(actions)
            }
        )

    # ========================================================================
    # INTENT DETERMINATION
    # ========================================================================

    def _determine_intent(self, extraction: Dict) -> Tuple[QueryIntent, float]:
        """Determine query intent from extraction results"""
        microactions = extraction.get("microactions", [])

        if microactions:
            # Use detected action to map to intent
            best_action = microactions[0]
            action_name = best_action.get("action", "")
            confidence = best_action.get("confidence", 0.5)

            intent = self.action_to_intent.get(action_name, QueryIntent.GENERAL_SEARCH)
            return (intent, confidence)

        # No action detected - infer from entities
        entities = extraction.get("canonical_entities", [])

        if any(e.get("type") == "fault_code" for e in entities):
            return (QueryIntent.DIAGNOSE_FAULT, 0.7)

        if any(e.get("type") == "maritime_term" for e in entities):
            # Symptom-related
            return (QueryIntent.EQUIPMENT_HISTORY, 0.6)

        if any(e.get("type") == "part" for e in entities):
            return (QueryIntent.FIND_PART, 0.6)

        if any(e.get("type") == "equipment" for e in entities):
            return (QueryIntent.GENERAL_SEARCH, 0.5)

        return (QueryIntent.GENERAL_SEARCH, 0.3)

    # ========================================================================
    # ENTITY RESOLUTION
    # ========================================================================

    def _resolve_entities(
        self,
        yacht_id: str,
        extraction: Dict
    ) -> List[ResolvedEntity]:
        """Resolve extracted entities to canonical IDs"""
        resolved = []
        canonical_entities = extraction.get("canonical_entities", [])

        for entity in canonical_entities:
            original = entity.get("value", "")
            entity_type = entity.get("type", "")
            canonical = entity.get("canonical", "")
            confidence = entity.get("confidence", 0.0)

            resolved_entity = ResolvedEntity(
                original_text=original,
                entity_type=entity_type,
                confidence=confidence
            )

            # Try to resolve to database ID
            if entity_type in ("equipment", "part", "fault_code", "supplier"):
                canonical_id = self._resolve_entity_alias(
                    yacht_id,
                    entity_type,
                    canonical
                )
                if canonical_id:
                    resolved_entity.canonical_id = canonical_id
                    resolved_entity.canonical_name = canonical

            elif entity_type in ("maritime_term", "symptom"):
                symptom_code = self._resolve_symptom_alias(original)
                if symptom_code:
                    resolved_entity.canonical_id = symptom_code
                    resolved_entity.canonical_name = symptom_code

            resolved.append(resolved_entity)

        return resolved

    def _resolve_entity_alias(
        self,
        yacht_id: str,
        entity_type: str,
        alias_text: str
    ) -> Optional[str]:
        """Call database resolve_entity_alias function"""
        if not self.client:
            return None

        # Map entity type
        type_map = {
            "equipment": "equipment",
            "part": "part",
            "fault_code": "fault",
            "supplier": "supplier"
        }
        db_type = type_map.get(entity_type, entity_type)

        try:
            result = self.client.rpc(
                "resolve_entity_alias",
                {
                    "p_yacht_id": yacht_id,
                    "p_entity_type": db_type,
                    "p_alias_text": alias_text
                }
            ).execute()

            return result.data if result.data else None

        except Exception as e:
            logger.debug(f"Entity resolution failed: {e}")
            return None

    def _resolve_symptom_alias(self, alias_text: str) -> Optional[str]:
        """Call database resolve_symptom_alias function"""
        if not self.client:
            return None

        try:
            result = self.client.rpc(
                "resolve_symptom_alias",
                {"p_alias_text": alias_text}
            ).execute()

            return result.data if result.data else None

        except Exception as e:
            logger.debug(f"Symptom resolution failed: {e}")
            return None

    # ========================================================================
    # INTENT-SPECIFIC QUERIES
    # ========================================================================

    def _execute_intent_query(
        self,
        yacht_id: str,
        intent: QueryIntent,
        query_text: str,
        extraction: Dict,
        resolved_entities: List[ResolvedEntity]
    ) -> Tuple[List[ResultCard], List[SuggestedAction]]:
        """Execute intent-specific query"""

        if intent == QueryIntent.FIND_DOCUMENT_SECTION:
            return self._query_document_section(
                yacht_id, query_text, resolved_entities
            )

        elif intent == QueryIntent.EQUIPMENT_HISTORY:
            return self._query_equipment_history(
                yacht_id, query_text, resolved_entities
            )

        elif intent == QueryIntent.DIAGNOSE_FAULT:
            return self._query_diagnose_fault(
                yacht_id, query_text, resolved_entities
            )

        elif intent == QueryIntent.FIND_PART:
            return self._query_find_part(
                yacht_id, query_text, resolved_entities
            )

        elif intent == QueryIntent.RELATIONSHIP_TRAVERSAL:
            return self._query_relationships(
                yacht_id, query_text, resolved_entities
            )

        elif intent == QueryIntent.MAINTENANCE_LOOKUP:
            return self._query_maintenance(
                yacht_id, query_text, resolved_entities
            )

        else:
            return self._query_general_search(
                yacht_id, query_text, resolved_entities
            )

    # ------------------------------------------------------------------------
    # Find Document Section
    # ------------------------------------------------------------------------

    def _query_document_section(
        self,
        yacht_id: str,
        query_text: str,
        resolved_entities: List[ResolvedEntity]
    ) -> Tuple[List[ResultCard], List[SuggestedAction]]:
        """Find document section based on equipment + keywords"""
        cards = []
        actions = []

        # Extract equipment and keywords from query
        equipment_entities = [
            e for e in resolved_entities if e.entity_type == "equipment"
        ]

        if not self.client:
            # Return placeholder
            return (
                [ResultCard(
                    card_type=CardType.DOCUMENT,
                    title="Document Search (dry-run)",
                    subtitle=f"Would search for: {query_text}",
                    confidence=0.5
                )],
                []
            )

        # Search document chunks mentioning equipment
        for equip in equipment_entities:
            if equip.canonical_id:
                chunks = self._find_document_chunks_by_equipment(
                    yacht_id,
                    equip.canonical_id,
                    query_text
                )

                for chunk in chunks[:5]:
                    card = ResultCard(
                        card_type=CardType.DOCUMENT,
                        title=chunk.get("section_title", "Document Section"),
                        subtitle=f"Page {chunk.get('page_number', '?')}",
                        confidence=chunk.get("confidence", 0.7),
                        data={
                            "document_id": chunk.get("document_id"),
                            "chunk_id": chunk.get("id"),
                            "page_number": chunk.get("page_number"),
                            "section_path": chunk.get("section_path"),
                            "preview": chunk.get("content", "")[:200]
                        },
                        source_chunk_id=chunk.get("id"),
                        source_document_id=chunk.get("document_id")
                    )
                    cards.append(card)

                    # Suggest open_document action
                    if card.confidence >= ACTION_THRESHOLDS[ActionType.OPEN_DOCUMENT]:
                        actions.append(SuggestedAction(
                            action=ActionType.OPEN_DOCUMENT,
                            confidence=card.confidence,
                            requires_confirmation=False,
                            parameters={
                                "document_id": chunk.get("document_id"),
                                "page_number": chunk.get("page_number"),
                                "section_title": chunk.get("section_title"),
                                "highlight_text": query_text
                            },
                            context={
                                "equipment": equip.original_text
                            }
                        ))

        return (cards, actions)

    def _find_document_chunks_by_equipment(
        self,
        yacht_id: str,
        equipment_id: str,
        search_text: str
    ) -> List[Dict]:
        """Find document chunks related to equipment"""
        if not self.client:
            return []

        try:
            # Query graph nodes -> chunks
            result = self.client.table("document_chunks").select(
                "id, document_id, content, section_title, page_number, section_path"
            ).eq("yacht_id", yacht_id).ilike(
                "content", f"%{search_text}%"
            ).limit(10).execute()

            return result.data if result.data else []

        except Exception as e:
            logger.error(f"Document chunk search failed: {e}")
            return []

    # ------------------------------------------------------------------------
    # Equipment History (Symptom Diagnosis)
    # ------------------------------------------------------------------------

    def _query_equipment_history(
        self,
        yacht_id: str,
        query_text: str,
        resolved_entities: List[ResolvedEntity]
    ) -> Tuple[List[ResultCard], List[SuggestedAction]]:
        """Find equipment history including past symptoms/faults"""
        cards = []
        actions = []

        equipment_entities = [e for e in resolved_entities if e.entity_type == "equipment"]
        symptom_entities = [e for e in resolved_entities if e.entity_type in ("maritime_term", "symptom")]

        if not self.client:
            return (
                [ResultCard(
                    card_type=CardType.EQUIPMENT,
                    title="Equipment History (dry-run)",
                    subtitle=f"Would search history for: {query_text}",
                    confidence=0.5
                )],
                []
            )

        # Get graph edges for equipment -> symptoms/faults
        for equip in equipment_entities:
            history = self._get_equipment_graph_history(
                yacht_id,
                equip.canonical_id or equip.original_text
            )

            if history:
                card = ResultCard(
                    card_type=CardType.EQUIPMENT,
                    title=f"{equip.original_text} History",
                    subtitle=f"{len(history)} related items found",
                    confidence=0.8,
                    data={
                        "equipment_id": equip.canonical_id,
                        "equipment_name": equip.original_text,
                        "history": history
                    }
                )
                cards.append(card)

        # Add symptom cards
        for symptom in symptom_entities:
            cards.append(ResultCard(
                card_type=CardType.SYMPTOM,
                title=f"Symptom: {symptom.original_text}",
                subtitle=f"Code: {symptom.canonical_id or 'Unknown'}",
                confidence=symptom.confidence,
                data={
                    "symptom_code": symptom.canonical_id,
                    "symptom_text": symptom.original_text
                }
            ))

        # Suggest create_work_order if symptom is present
        if symptom_entities and equipment_entities:
            equip = equipment_entities[0]
            symptom = symptom_entities[0]

            actions.append(SuggestedAction(
                action=ActionType.CREATE_WORK_ORDER,
                confidence=0.75,
                requires_confirmation=True,
                parameters={
                    "equipment_id": equip.canonical_id,
                    "symptom_code": symptom.canonical_id,
                    "suggested_title": f"{equip.original_text} - {symptom.original_text} Investigation"
                },
                context={
                    "detected_symptom": symptom.original_text,
                    "equipment": equip.original_text
                }
            ))

        # Always add show_history action
        actions.append(SuggestedAction(
            action=ActionType.SHOW_HISTORY,
            confidence=0.85,
            requires_confirmation=False,
            parameters={
                "equipment_ids": [e.canonical_id for e in equipment_entities if e.canonical_id],
                "symptom_codes": [s.canonical_id for s in symptom_entities if s.canonical_id]
            }
        ))

        return (cards, actions)

    def _get_equipment_graph_history(
        self,
        yacht_id: str,
        equipment_ref: str
    ) -> List[Dict]:
        """Get equipment history from graph"""
        if not self.client:
            return []

        try:
            # Query graph edges for this equipment
            result = self.client.table("graph_edges").select(
                "id, edge_type, from_label, to_label, confidence, created_at"
            ).eq("yacht_id", yacht_id).or_(
                f"from_label.ilike.%{equipment_ref}%,to_label.ilike.%{equipment_ref}%"
            ).order("created_at", desc=True).limit(20).execute()

            return result.data if result.data else []

        except Exception as e:
            logger.error(f"Equipment history query failed: {e}")
            return []

    # ------------------------------------------------------------------------
    # Diagnose Fault
    # ------------------------------------------------------------------------

    def _query_diagnose_fault(
        self,
        yacht_id: str,
        query_text: str,
        resolved_entities: List[ResolvedEntity]
    ) -> Tuple[List[ResultCard], List[SuggestedAction]]:
        """Diagnose fault code"""
        cards = []
        actions = []

        fault_entities = [e for e in resolved_entities if e.entity_type == "fault_code"]

        if not self.client:
            return (
                [ResultCard(
                    card_type=CardType.FAULT,
                    title="Fault Diagnosis (dry-run)",
                    subtitle=f"Would diagnose: {query_text}",
                    confidence=0.5
                )],
                []
            )

        for fault in fault_entities:
            # Look up fault in database
            fault_info = self._get_fault_info(yacht_id, fault.original_text)

            if fault_info:
                card = ResultCard(
                    card_type=CardType.FAULT,
                    title=f"Fault {fault.original_text}",
                    subtitle=fault_info.get("canonical_name", "Unknown fault"),
                    confidence=0.9,
                    data={
                        "fault_code": fault.original_text,
                        "description": fault_info.get("description"),
                        "severity": fault_info.get("severity"),
                        "resolution_steps": fault_info.get("resolution_steps", [])
                    }
                )
                cards.append(card)
            else:
                # Fault not in database - search documents
                doc_chunks = self._search_fault_in_documents(
                    yacht_id, fault.original_text
                )

                card = ResultCard(
                    card_type=CardType.FAULT,
                    title=f"Fault {fault.original_text}",
                    subtitle="Found in documentation",
                    confidence=0.7,
                    data={
                        "fault_code": fault.original_text,
                        "document_references": doc_chunks[:3]
                    }
                )
                cards.append(card)

            # Always suggest show_fault_info
            actions.append(SuggestedAction(
                action=ActionType.SHOW_FAULT_INFO,
                confidence=0.9,
                requires_confirmation=False,
                parameters={
                    "fault_code": fault.original_text
                }
            ))

        return (cards, actions)

    def _get_fault_info(self, yacht_id: str, fault_code: str) -> Optional[Dict]:
        """Get fault info from database"""
        if not self.client:
            return None

        try:
            result = self.client.table("faults").select("*").eq(
                "yacht_id", yacht_id
            ).eq("fault_code", fault_code).single().execute()

            return result.data

        except Exception:
            return None

    def _search_fault_in_documents(self, yacht_id: str, fault_code: str) -> List[Dict]:
        """Search for fault code in documents"""
        if not self.client:
            return []

        try:
            result = self.client.table("document_chunks").select(
                "id, section_title, page_number, content"
            ).eq("yacht_id", yacht_id).ilike(
                "content", f"%{fault_code}%"
            ).limit(5).execute()

            return result.data if result.data else []

        except Exception:
            return []

    # ------------------------------------------------------------------------
    # Find Part
    # ------------------------------------------------------------------------

    def _query_find_part(
        self,
        yacht_id: str,
        query_text: str,
        resolved_entities: List[ResolvedEntity]
    ) -> Tuple[List[ResultCard], List[SuggestedAction]]:
        """Find parts for equipment"""
        cards = []
        actions = []

        part_entities = [e for e in resolved_entities if e.entity_type == "part"]
        equipment_entities = [e for e in resolved_entities if e.entity_type == "equipment"]

        if not self.client:
            return (
                [ResultCard(
                    card_type=CardType.PART,
                    title="Part Search (dry-run)",
                    subtitle=f"Would search: {query_text}",
                    confidence=0.5
                )],
                []
            )

        # Search for parts
        for part in part_entities:
            part_info = self._get_part_info(yacht_id, part.original_text)

            card = ResultCard(
                card_type=CardType.PART,
                title=part.original_text,
                subtitle=part_info.get("part_number", "") if part_info else "Part search",
                confidence=0.8 if part_info else 0.6,
                data={
                    "part_id": part_info.get("id") if part_info else None,
                    "part_number": part_info.get("part_number") if part_info else None,
                    "manufacturer": part_info.get("manufacturer") if part_info else None,
                    "stock_level": part_info.get("current_stock") if part_info else None
                }
            )
            cards.append(card)

        # If equipment specified, get parts via graph
        for equip in equipment_entities:
            if equip.canonical_id:
                parts = self._get_equipment_parts(yacht_id, equip.canonical_id)
                for part in parts[:5]:
                    cards.append(ResultCard(
                        card_type=CardType.PART,
                        title=part.get("canonical_name", "Part"),
                        subtitle=f"Used by {equip.original_text}",
                        confidence=0.85,
                        data=part
                    ))

        # Suggest show_parts action
        actions.append(SuggestedAction(
            action=ActionType.SHOW_PARTS,
            confidence=0.8,
            requires_confirmation=False,
            parameters={
                "equipment_ids": [e.canonical_id for e in equipment_entities if e.canonical_id],
                "part_search": query_text
            }
        ))

        return (cards, actions)

    def _get_part_info(self, yacht_id: str, part_text: str) -> Optional[Dict]:
        """Get part info from database"""
        if not self.client:
            return None

        try:
            result = self.client.table("parts").select("*").eq(
                "yacht_id", yacht_id
            ).or_(
                f"canonical_name.ilike.%{part_text}%,part_number.ilike.%{part_text}%"
            ).limit(1).execute()

            return result.data[0] if result.data else None

        except Exception:
            return None

    def _get_equipment_parts(self, yacht_id: str, equipment_id: str) -> List[Dict]:
        """Get parts for equipment via graph"""
        if not self.client:
            return []

        try:
            result = self.client.table("graph_edges").select(
                "to_label, to_canonical_id, confidence"
            ).eq("yacht_id", yacht_id).eq(
                "from_canonical_id", equipment_id
            ).eq("edge_type", "USES_PART").execute()

            return result.data if result.data else []

        except Exception:
            return []

    # ------------------------------------------------------------------------
    # Relationship Traversal
    # ------------------------------------------------------------------------

    def _query_relationships(
        self,
        yacht_id: str,
        query_text: str,
        resolved_entities: List[ResolvedEntity]
    ) -> Tuple[List[ResultCard], List[SuggestedAction]]:
        """Traverse graph relationships"""
        cards = []
        actions = []

        equipment_entities = [e for e in resolved_entities if e.entity_type == "equipment"]

        for equip in equipment_entities:
            if equip.canonical_id:
                # Use get_equipment_graph function
                graph = self._call_get_equipment_graph(yacht_id, equip.canonical_id)

                if graph:
                    card = ResultCard(
                        card_type=CardType.EQUIPMENT,
                        title=f"{equip.original_text} Relationships",
                        subtitle=f"{len(graph)} connections found",
                        confidence=0.9,
                        data={
                            "equipment_id": equip.canonical_id,
                            "relationships": graph
                        }
                    )
                    cards.append(card)

        return (cards, actions)

    def _call_get_equipment_graph(self, yacht_id: str, equipment_id: str) -> List[Dict]:
        """Call database get_equipment_graph function"""
        if not self.client:
            return []

        try:
            result = self.client.rpc(
                "get_equipment_graph",
                {
                    "p_yacht_id": yacht_id,
                    "p_equipment_id": equipment_id
                }
            ).execute()

            return result.data if result.data else []

        except Exception as e:
            logger.error(f"get_equipment_graph failed: {e}")
            return []

    # ------------------------------------------------------------------------
    # Maintenance Lookup
    # ------------------------------------------------------------------------

    def _query_maintenance(
        self,
        yacht_id: str,
        query_text: str,
        resolved_entities: List[ResolvedEntity]
    ) -> Tuple[List[ResultCard], List[SuggestedAction]]:
        """Look up maintenance schedules"""
        cards = []
        actions = []

        equipment_entities = [e for e in resolved_entities if e.entity_type == "equipment"]

        if not self.client:
            return (
                [ResultCard(
                    card_type=CardType.MAINTENANCE,
                    title="Maintenance Lookup (dry-run)",
                    subtitle=f"Would lookup: {query_text}",
                    confidence=0.5
                )],
                []
            )

        for equip in equipment_entities:
            if equip.canonical_id:
                maintenance = self._get_maintenance_templates(
                    yacht_id, equip.canonical_id
                )

                for maint in maintenance[:5]:
                    card = ResultCard(
                        card_type=CardType.MAINTENANCE,
                        title=f"{equip.original_text} - {maint.get('action', 'Maintenance')}",
                        subtitle=f"Every {maint.get('interval_hours', '?')} hours",
                        confidence=0.85,
                        data={
                            "equipment_id": equip.canonical_id,
                            "interval_hours": maint.get("interval_hours"),
                            "interval_days": maint.get("interval_days"),
                            "action": maint.get("action"),
                            "action_description": maint.get("action_description"),
                            "tools_required": maint.get("tools_required")
                        }
                    )
                    cards.append(card)

        # Suggest show_maintenance action
        actions.append(SuggestedAction(
            action=ActionType.SHOW_MAINTENANCE,
            confidence=0.85,
            requires_confirmation=False,
            parameters={
                "equipment_ids": [e.canonical_id for e in equipment_entities if e.canonical_id]
            }
        ))

        return (cards, actions)

    def _get_maintenance_templates(self, yacht_id: str, equipment_id: str) -> List[Dict]:
        """Get maintenance templates for equipment"""
        if not self.client:
            return []

        try:
            result = self.client.table("maintenance_templates").select("*").eq(
                "yacht_id", yacht_id
            ).eq("equipment_id", equipment_id).execute()

            return result.data if result.data else []

        except Exception:
            return []

    # ------------------------------------------------------------------------
    # General Search
    # ------------------------------------------------------------------------

    def _query_general_search(
        self,
        yacht_id: str,
        query_text: str,
        resolved_entities: List[ResolvedEntity]
    ) -> Tuple[List[ResultCard], List[SuggestedAction]]:
        """General search fallback"""
        cards = []
        actions = []

        # Add cards for all resolved entities
        for entity in resolved_entities:
            card_type = {
                "equipment": CardType.EQUIPMENT,
                "part": CardType.PART,
                "fault_code": CardType.FAULT,
                "maritime_term": CardType.SYMPTOM
            }.get(entity.entity_type, CardType.EQUIPMENT)

            cards.append(ResultCard(
                card_type=card_type,
                title=entity.original_text,
                subtitle=f"Type: {entity.entity_type}",
                confidence=entity.confidence,
                data={
                    "canonical_id": entity.canonical_id,
                    "canonical_name": entity.canonical_name
                }
            ))

        return (cards, actions)

    # ========================================================================
    # GRAPH STATS
    # ========================================================================

    def _get_graph_stats(self, yacht_id: str) -> Dict:
        """Get graph statistics using v_graph_stats view"""
        if not self.client:
            return {}

        try:
            result = self.client.table("v_graph_stats").select("*").eq(
                "yacht_id", yacht_id
            ).single().execute()

            return result.data if result.data else {}

        except Exception:
            return {}


# ============================================================================
# SINGLETON
# ============================================================================

_query_service_instance = None

def get_query_service() -> GraphRAGQueryService:
    """Get or create singleton query service"""
    global _query_service_instance
    if _query_service_instance is None:
        _query_service_instance = GraphRAGQueryService()
    return _query_service_instance


# ============================================================================
# HELPER FOR SERIALIZATION
# ============================================================================

def query_result_to_dict(result: QueryResult) -> Dict:
    """Convert QueryResult to JSON-serializable dict"""
    return {
        "query": result.query,
        "intent": result.intent.value,
        "intent_confidence": result.intent_confidence,
        "resolved_entities": [
            {
                "original_text": e.original_text,
                "entity_type": e.entity_type,
                "canonical_id": e.canonical_id,
                "canonical_name": e.canonical_name,
                "confidence": e.confidence
            }
            for e in result.resolved_entities
        ],
        "cards": [
            {
                "card_type": c.card_type.value,
                "title": c.title,
                "subtitle": c.subtitle,
                "confidence": c.confidence,
                "data": c.data
            }
            for c in result.cards
        ],
        "suggested_actions": [
            {
                "action": a.action.value,
                "confidence": a.confidence,
                "requires_confirmation": a.requires_confirmation,
                "parameters": a.parameters,
                "context": a.context
            }
            for a in result.suggested_actions
        ],
        "graph_stats": result.graph_stats,
        "metadata": result.metadata
    }


# ============================================================================
# MAIN (for testing)
# ============================================================================

if __name__ == "__main__":
    service = GraphRAGQueryService()

    test_queries = [
        "Open Cat main engine manual to lube oil section",
        "Engine is overheating, show historic data",
        "What does error code E047 mean?",
        "Find oil filter for generator 1",
        "When is oil change due on main engine?"
    ]

    print("GraphRAG Query Service - Test")
    print("=" * 70)

    for query in test_queries:
        print(f"\nQuery: '{query}'")
        print("-" * 50)

        result = service.query("test-yacht-123", query)

        print(f"Intent: {result.intent.value} (confidence: {result.intent_confidence:.2f})")
        print(f"Resolved entities: {len(result.resolved_entities)}")
        for e in result.resolved_entities:
            print(f"  - {e.original_text} ({e.entity_type}) -> {e.canonical_id or 'unresolved'}")

        print(f"Cards: {len(result.cards)}")
        for c in result.cards:
            print(f"  - {c.card_type.value}: {c.title}")

        print(f"Suggested actions: {len(result.suggested_actions)}")
        for a in result.suggested_actions:
            print(f"  - {a.action.value} (confidence: {a.confidence:.2f})")
