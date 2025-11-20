"""
Micro-Action Generator
Generates context-aware micro-actions for result cards
"""
from typing import List
from models.responses import ResultCard, MicroAction, CardType, IntentType, EntityExtractionResult
import logging

logger = logging.getLogger(__name__)


async def generate_micro_actions(
    cards: List[ResultCard],
    intent: IntentType,
    entities: EntityExtractionResult
) -> List[ResultCard]:
    """
    Generate and attach micro-actions to result cards

    Args:
        cards: List of result cards
        intent: Detected intent
        entities: Extracted entities

    Returns:
        Cards with micro-actions attached
    """
    logger.info(f"Generating micro-actions for {len(cards)} cards")

    for card in cards:
        try:
            actions = determine_actions(card, intent, entities)
            card.actions = actions
        except Exception as e:
            logger.error(f"Failed to generate actions for card: {e}")
            card.actions = []

    return cards


def determine_actions(
    card: ResultCard,
    intent: IntentType,
    entities: EntityExtractionResult
) -> List[MicroAction]:
    """
    Determine appropriate micro-actions for a card

    Args:
        card: Result card
        intent: Detected intent
        entities: Extracted entities

    Returns:
        List of MicroAction objects
    """
    actions = []

    # Card-type specific actions
    if card.type == CardType.DOCUMENT_CHUNK:
        actions.extend(document_chunk_actions(card, intent))

    elif card.type == CardType.FAULT:
        actions.extend(fault_actions(card, intent, entities))

    elif card.type == CardType.WORK_ORDER:
        actions.extend(work_order_actions(card, intent))

    elif card.type == CardType.PART:
        actions.extend(part_actions(card, intent))

    elif card.type == CardType.EQUIPMENT:
        actions.extend(equipment_actions(card, intent))

    elif card.type == CardType.EMAIL:
        actions.extend(email_actions(card, intent))

    # Universal actions (available on all cards)
    actions.extend(universal_actions(card, intent))

    # Limit to 2-4 actions max per spec
    return actions[:4]


def document_chunk_actions(card: ResultCard, intent: IntentType) -> List[MicroAction]:
    """Actions for document chunks"""

    actions = []

    # Open document
    if card.document_id:
        actions.append(MicroAction(
            label="Open Document",
            action="open_document",
            context={
                "document_id": card.document_id,
                "page": card.page_number,
                "chunk_index": card.chunk_index
            }
        ))

    # Add to handover
    if intent != IntentType.ADD_TO_HANDOVER:
        actions.append(MicroAction(
            label="Add to Handover",
            action="add_to_handover",
            context={
                "source_type": "document_chunk",
                "source_id": card.document_id,
                "chunk_index": card.chunk_index
            }
        ))

    return actions


def fault_actions(
    card: ResultCard,
    intent: IntentType,
    entities: EntityExtractionResult
) -> List[MicroAction]:
    """Actions for faults"""

    actions = []

    # Create work order (if not already the intent)
    if intent != IntentType.CREATE_WORK_ORDER:
        actions.append(MicroAction(
            label="Create Work Order",
            action="create_work_order",
            context={
                "equipment_id": card.equipment_id,
                "fault_code": card.fault_code,
                "prefill_title": f"Fix fault {card.fault_code}"
            }
        ))

    # View history
    if card.equipment_id:
        actions.append(MicroAction(
            label="View History",
            action="view_equipment_history",
            context={
                "equipment_id": card.equipment_id,
                "filter": "faults"
            }
        ))

    # Show related manual
    actions.append(MicroAction(
        label="Find Manual",
        action="search_related_documents",
        context={
            "fault_code": card.fault_code,
            "equipment_id": card.equipment_id
        }
    ))

    # Add to handover
    actions.append(MicroAction(
        label="Add to Handover",
        action="add_to_handover",
        context={
            "source_type": "fault",
            "source_id": card.metadata.get("id"),
            "summary": f"Fault {card.fault_code}"
        }
    ))

    return actions


def work_order_actions(card: ResultCard, intent: IntentType) -> List[MicroAction]:
    """Actions for work orders"""

    actions = []

    # View full work order
    if card.work_order_id:
        actions.append(MicroAction(
            label="View Details",
            action="view_work_order",
            context={
                "work_order_id": card.work_order_id
            }
        ))

    # View equipment
    if card.equipment_id:
        actions.append(MicroAction(
            label="View Equipment",
            action="view_equipment",
            context={
                "equipment_id": card.equipment_id
            }
        ))

    # Add to handover
    actions.append(MicroAction(
        label="Add to Handover",
        action="add_to_handover",
        context={
            "source_type": "work_order",
            "source_id": card.work_order_id
        }
    ))

    return actions


def part_actions(card: ResultCard, intent: IntentType) -> List[MicroAction]:
    """Actions for parts"""

    actions = []

    # Order part (if stock low)
    in_stock = card.metadata.get("in_stock", 0)

    if in_stock == 0:
        actions.append(MicroAction(
            label="Order Part",
            action="create_purchase_order",
            context={
                "part_id": card.part_id,
                "part_name": card.title,
                "reason": "out_of_stock"
            }
        ))
    elif in_stock < 3:  # Low stock threshold
        actions.append(MicroAction(
            label="Order More",
            action="create_purchase_order",
            context={
                "part_id": card.part_id,
                "part_name": card.title,
                "reason": "low_stock"
            }
        ))

    # Add to work order
    if intent == IntentType.CREATE_WORK_ORDER:
        actions.append(MicroAction(
            label="Add to Work Order",
            action="add_part_to_work_order",
            context={
                "part_id": card.part_id
            }
        ))

    # View stock details
    actions.append(MicroAction(
        label="View Stock",
        action="view_part_stock",
        context={
            "part_id": card.part_id
        }
    ))

    return actions


def equipment_actions(card: ResultCard, intent: IntentType) -> List[MicroAction]:
    """Actions for equipment"""

    actions = []

    # View full equipment details
    if card.equipment_id:
        actions.append(MicroAction(
            label="View Details",
            action="view_equipment",
            context={
                "equipment_id": card.equipment_id
            }
        ))

    # View history
    actions.append(MicroAction(
        label="View History",
        action="view_equipment_history",
        context={
            "equipment_id": card.equipment_id
        }
    ))

    # Show predictive insight
    actions.append(MicroAction(
        label="Predictive Insight",
        action="show_predictive_insight",
        context={
            "equipment_id": card.equipment_id
        }
    ))

    return actions


def email_actions(card: ResultCard, intent: IntentType) -> List[MicroAction]:
    """Actions for emails"""

    actions = []

    # Open email
    external_id = card.metadata.get("external_id")
    if external_id:
        actions.append(MicroAction(
            label="Open Email",
            action="open_email",
            context={
                "external_id": external_id
            }
        ))

    # Add to handover
    actions.append(MicroAction(
        label="Add to Handover",
        action="add_to_handover",
        context={
            "source_type": "email",
            "source_id": external_id
        }
    ))

    return actions


def universal_actions(card: ResultCard, intent: IntentType) -> List[MicroAction]:
    """Actions available on all cards"""

    actions = []

    # Note: "Add to Handover" is usually added by type-specific handlers
    # Only add it here if not already present

    # For now, no truly universal actions beyond type-specific ones

    return actions
