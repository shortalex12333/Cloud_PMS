"""
Card Generator
Converts fused results into canonical SearchResultCard objects for the frontend

Uses the standardized card schema from models/card.py
"""
from typing import List, Dict, Any, Optional
from models.card import (
    SearchResultCard,
    CardType,
    CardMetadata,
    SourceLabel,
    MicroAction
)
from models.micro_action_catalogue import (
    get_actions_for_card,
    IntentType as CatalogueIntentType,
    UserRole
)
from models.responses import IntentType, EntityExtractionResult
from config import settings
import logging

logger = logging.getLogger(__name__)


# =============================================================================
# MAIN CARD GENERATION
# =============================================================================

async def generate_cards(
    fused_results: List[Dict[str, Any]],
    intent: Optional[IntentType] = None,
    entities: Optional[EntityExtractionResult] = None,
    user_role: str = "Engineer",
    yacht_config: Optional[Dict[str, Any]] = None
) -> List[SearchResultCard]:
    """
    Generate canonical SearchResultCard objects from fused results

    Args:
        fused_results: List of fused and scored results
        intent: Detected intent (for micro-action assignment)
        entities: Extracted entities (for micro-action context)
        user_role: User's role (for micro-action filtering)
        yacht_config: Yacht-specific feature flags

    Returns:
        List of SearchResultCard objects
    """
    logger.info(f"Generating cards for {len(fused_results)} results")

    cards = []
    yacht_config = yacht_config or {
        "predictive_enabled": settings.predictive_enabled
    }

    for result in fused_results:
        try:
            card = create_card(
                result,
                intent=intent,
                entities=entities,
                user_role=user_role,
                yacht_config=yacht_config
            )
            if card:
                cards.append(card)
        except Exception as e:
            logger.error(f"Failed to create card for result: {e}")
            continue

    logger.info(f"Generated {len(cards)} cards")
    return cards


def create_card(
    result: Dict[str, Any],
    intent: Optional[IntentType] = None,
    entities: Optional[EntityExtractionResult] = None,
    user_role: str = "Engineer",
    yacht_config: Optional[Dict[str, Any]] = None
) -> Optional[SearchResultCard]:
    """
    Create a single SearchResultCard from a fused result

    Args:
        result: Fused result dictionary
        intent: Detected intent
        entities: Extracted entities
        user_role: User role
        yacht_config: Yacht configuration

    Returns:
        SearchResultCard object or None
    """
    result_type = result.get("type", "document_chunk")
    data = result.get("data", {})

    # Map result type to canonical card type
    card_type = map_to_card_type(result_type)

    # Build metadata
    metadata = build_metadata(result, data, card_type)

    # Build source label
    source_label = build_source_label(result, data, card_type)

    # Get title and snippet
    title = result.get("title", "Result")[:100]
    snippet = result.get("preview", "")[:300]

    # Get relevance score
    relevance_score = result.get("final_score", 0.5)

    # Get micro-actions
    actions = []
    if intent:
        catalogue_intent = map_intent_to_catalogue(intent)
        role = map_role_string(user_role)

        actions = get_actions_for_card(
            card_type=card_type,
            intent=catalogue_intent,
            user_role=role,
            yacht_config=yacht_config,
            metadata=metadata.model_dump(),
            max_actions=4
        )

    # Build graph context (if available)
    graph_context = None
    if result.get("source_type") == "graph" or result.get("graph_context"):
        graph_context = {
            "discovered_via": result.get("source", "graph"),
            "depth": result.get("data", {}).get("depth", 0)
        }

    return SearchResultCard(
        card_type=card_type,
        title=title,
        snippet=snippet,
        source_label=source_label,
        metadata=metadata,
        actions=actions,
        relevance_score=relevance_score,
        graph_context=graph_context
    )


# =============================================================================
# TYPE MAPPING
# =============================================================================

def map_to_card_type(result_type: str) -> CardType:
    """Map result type string to CardType enum"""
    mapping = {
        "document_chunk": CardType.DOCUMENT,
        "document": CardType.DOCUMENT,
        "fault": CardType.FAULT,
        "work_order": CardType.WORK_ORDER,
        "part": CardType.PART,
        "equipment": CardType.EQUIPMENT,
        "predictive": CardType.PREDICTIVE,
        "handover": CardType.HANDOVER,
        "email": CardType.DOCUMENT,  # Emails map to document type
        "note": CardType.NOTE,
    }
    return mapping.get(result_type, CardType.DOCUMENT)


def map_intent_to_catalogue(intent: IntentType) -> CatalogueIntentType:
    """Map response IntentType to catalogue IntentType"""
    mapping = {
        IntentType.DIAGNOSE_FAULT: CatalogueIntentType.DIAGNOSE_FAULT,
        IntentType.FIND_DOCUMENT: CatalogueIntentType.FIND_DOCUMENT,
        IntentType.CREATE_WORK_ORDER: CatalogueIntentType.CREATE_WORK_ORDER,
        IntentType.ADD_TO_HANDOVER: CatalogueIntentType.ADD_TO_HANDOVER,
        IntentType.FIND_PART: CatalogueIntentType.FIND_PART,
        IntentType.PREDICTIVE_REQUEST: CatalogueIntentType.PREDICTIVE_REQUEST,
        IntentType.GENERAL_SEARCH: CatalogueIntentType.GENERAL_SEARCH,
    }
    return mapping.get(intent, CatalogueIntentType.GENERAL_SEARCH)


def map_role_string(role_str: str) -> UserRole:
    """Map role string to UserRole enum"""
    role_lower = role_str.lower()
    if "chief" in role_lower:
        return UserRole.CHIEF_ENGINEER
    elif "hod" in role_lower:
        return UserRole.HOD
    elif "eto" in role_lower:
        return UserRole.ETO
    elif "engineer" in role_lower:
        return UserRole.ENGINEER
    elif "deck" in role_lower:
        return UserRole.DECK_OFFICER
    elif "captain" in role_lower:
        return UserRole.CAPTAIN
    elif "viewer" in role_lower:
        return UserRole.VIEWER
    return UserRole.ENGINEER  # Default


# =============================================================================
# METADATA BUILDING
# =============================================================================

def build_metadata(
    result: Dict[str, Any],
    data: Dict[str, Any],
    card_type: CardType
) -> CardMetadata:
    """Build CardMetadata from result data"""

    metadata = CardMetadata(
        id=result.get("id") or data.get("id"),
        similarity_score=result.get("similarity"),
        is_global_knowledge=result.get("is_global", False)
    )

    # Document metadata
    if card_type == CardType.DOCUMENT:
        metadata.document_id = data.get("document_id") or result.get("id")
        metadata.page_number = data.get("page_number")
        metadata.chunk_index = data.get("chunk_index")

        if "document" in data and isinstance(data["document"], dict):
            doc = data["document"]
            metadata.filename = doc.get("filename")
            metadata.document_type = doc.get("document_type")

        # Equipment association
        if data.get("equipment_ids"):
            eq_ids = data["equipment_ids"]
            if isinstance(eq_ids, list) and eq_ids:
                metadata.equipment_id = eq_ids[0]

    # Fault metadata
    elif card_type == CardType.FAULT:
        metadata.fault_id = data.get("id")
        metadata.fault_code = data.get("fault_code")
        metadata.equipment_id = data.get("equipment_id")
        metadata.severity = data.get("severity")
        metadata.detected_at = data.get("detected_at")
        metadata.resolved_at = data.get("resolved_at")

        if "equipment" in data and isinstance(data["equipment"], dict):
            metadata.equipment_name = data["equipment"].get("name")

    # Work order metadata
    elif card_type == CardType.WORK_ORDER:
        metadata.work_order_id = data.get("work_order_id") or data.get("id")
        metadata.equipment_id = data.get("equipment_id")
        metadata.work_order_status = data.get("status_on_completion") or data.get("status")
        metadata.completed_at = data.get("completed_at")
        metadata.assigned_to = data.get("assigned_to")

        if "work_order" in data and isinstance(data["work_order"], dict):
            wo = data["work_order"]
            metadata.work_order_id = wo.get("id")
            metadata.work_order_status = wo.get("status")

    # Part metadata
    elif card_type == CardType.PART:
        metadata.part_id = data.get("id")
        metadata.part_number = data.get("part_number")
        metadata.manufacturer = data.get("manufacturer")

        # Calculate stock level
        if "stock_levels" in data and isinstance(data["stock_levels"], list):
            total_stock = sum(
                s.get("quantity", 0)
                for s in data["stock_levels"]
                if isinstance(s, dict)
            )
            metadata.stock_level = total_stock

            # Get first location
            if data["stock_levels"] and isinstance(data["stock_levels"][0], dict):
                loc = data["stock_levels"][0].get("location", {})
                if isinstance(loc, dict):
                    metadata.stock_location = loc.get("name")

    # Equipment metadata
    elif card_type == CardType.EQUIPMENT:
        metadata.equipment_id = data.get("id")
        metadata.equipment_name = data.get("name")
        metadata.equipment_code = data.get("code")
        metadata.manufacturer = data.get("manufacturer")
        metadata.model = data.get("model")
        metadata.location = data.get("location")
        metadata.criticality = data.get("criticality")
        metadata.system_type = data.get("system_type")

    # Predictive metadata
    elif card_type == CardType.PREDICTIVE:
        metadata.equipment_id = data.get("equipment_id")
        metadata.prediction_confidence = data.get("confidence")
        metadata.predicted_failure_window = data.get("failure_window")
        metadata.risk_level = data.get("risk_level")

    # Handover metadata
    elif card_type == CardType.HANDOVER:
        metadata.handover_id = data.get("id")
        metadata.shift_date = data.get("shift_date")
        metadata.author = data.get("author")

    # Note metadata
    elif card_type == CardType.NOTE:
        metadata.note_id = data.get("id")
        metadata.note_type = data.get("note_type")
        metadata.created_by = data.get("created_by")

    return metadata


def build_source_label(
    result: Dict[str, Any],
    data: Dict[str, Any],
    card_type: CardType
) -> SourceLabel:
    """Build SourceLabel from result data"""

    # Check if result already has source_label
    if "source_label" in result and isinstance(result["source_label"], dict):
        sl = result["source_label"]
        return SourceLabel(
            source_type=sl.get("source_type", "Unknown"),
            source_name=sl.get("source_name", ""),
            location=sl.get("location")
        )

    # Build based on card type
    if card_type == CardType.DOCUMENT:
        source_type = "Document"
        source_name = ""
        location = None

        if "document" in data and isinstance(data["document"], dict):
            doc = data["document"]
            doc_type = doc.get("document_type", "")
            if "manual" in doc_type.lower():
                source_type = "Manual"
            elif "bulletin" in doc_type.lower():
                source_type = "Tech Bulletin"
            elif "email" in doc_type.lower():
                source_type = "Email"
            source_name = doc.get("filename", "")

        if data.get("page_number"):
            location = f"Page {data['page_number']}"

        return SourceLabel(
            source_type=source_type,
            source_name=source_name,
            location=location
        )

    elif card_type == CardType.FAULT:
        return SourceLabel(
            source_type="Fault Log",
            source_name=data.get("fault_code", ""),
            location=data.get("detected_at", "")[:10] if data.get("detected_at") else None
        )

    elif card_type == CardType.WORK_ORDER:
        return SourceLabel(
            source_type="Work Order",
            source_name=data.get("work_order_id", "")[:8] if data.get("work_order_id") else "",
            location=None
        )

    elif card_type == CardType.PART:
        return SourceLabel(
            source_type="Parts Inventory",
            source_name=data.get("part_number", ""),
            location=None
        )

    elif card_type == CardType.EQUIPMENT:
        return SourceLabel(
            source_type="Equipment",
            source_name=data.get("code", "") or data.get("name", ""),
            location=data.get("location")
        )

    elif card_type == CardType.PREDICTIVE:
        return SourceLabel(
            source_type="Predictive",
            source_name="Analysis",
            location=None
        )

    elif card_type == CardType.HANDOVER:
        return SourceLabel(
            source_type="Handover",
            source_name=data.get("shift_date", ""),
            location=None
        )

    elif card_type == CardType.NOTE:
        return SourceLabel(
            source_type="Note",
            source_name=data.get("note_type", ""),
            location=None
        )

    # Default
    return SourceLabel(
        source_type=result.get("source", "Unknown"),
        source_name="",
        location=None
    )


# =============================================================================
# LEGACY COMPATIBILITY (for existing code)
# =============================================================================

async def generate_micro_actions(
    cards: List[SearchResultCard],
    intent: IntentType,
    entities: EntityExtractionResult,
    user_role: str = "Engineer",
    yacht_config: Optional[Dict[str, Any]] = None
) -> List[SearchResultCard]:
    """
    Legacy function - micro-actions are now generated in create_card()
    This function exists for backward compatibility but is a no-op
    since actions are already attached.

    Returns cards unchanged.
    """
    # Actions are already attached during card creation
    # This function exists for backward compatibility
    return cards
