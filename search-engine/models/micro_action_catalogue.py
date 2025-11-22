"""
Micro-Action Catalogue
Defines all available micro-actions and their assignment rules
based on card_type, intent, role, and yacht configuration
"""
from typing import Dict, List, Set, Optional, Any
from enum import Enum
from dataclasses import dataclass, field
from models.card import CardType, MicroAction


class ActionId(str, Enum):
    """Canonical action identifiers"""
    # Document actions
    OPEN_DOCUMENT = "open_document"
    DOWNLOAD_DOCUMENT = "download_document"
    COPY_LINK = "copy_link"

    # Equipment actions
    VIEW_EQUIPMENT = "view_equipment"
    VIEW_EQUIPMENT_HISTORY = "view_equipment_history"
    CREATE_WORK_ORDER = "create_work_order"
    SHOW_PREDICTIVE_INSIGHT = "show_predictive_insight"

    # Fault actions
    VIEW_FAULT_DETAILS = "view_fault_details"
    FIND_RELATED_MANUAL = "find_related_manual"
    VIEW_FAULT_HISTORY = "view_fault_history"

    # Part actions
    VIEW_PART_STOCK = "view_part_stock"
    ORDER_PART = "order_part"
    ADD_PART_TO_WORK_ORDER = "add_part_to_work_order"
    FIND_SUBSTITUTE = "find_substitute"

    # Work order actions
    VIEW_WORK_ORDER = "view_work_order"
    CLONE_WORK_ORDER = "clone_work_order"

    # Handover actions
    VIEW_HANDOVER = "view_handover"
    ADD_TO_HANDOVER = "add_to_handover"

    # Universal actions
    BOOKMARK = "bookmark"
    SHARE = "share"
    COPY_SNIPPET = "copy_snippet"


class IntentType(str, Enum):
    """Intent types (mirror from responses.py)"""
    DIAGNOSE_FAULT = "diagnose_fault"
    FIND_DOCUMENT = "find_document"
    CREATE_WORK_ORDER = "create_work_order"
    ADD_TO_HANDOVER = "add_to_handover"
    FIND_PART = "find_part"
    PREDICTIVE_REQUEST = "predictive_request"
    GENERAL_SEARCH = "general_search"


class UserRole(str, Enum):
    """User roles with different action permissions"""
    CHIEF_ENGINEER = "Chief Engineer"
    HOD = "HOD"
    ENGINEER = "Engineer"
    ETO = "ETO"
    DECK_OFFICER = "Deck Officer"
    CAPTAIN = "Captain"
    VIEWER = "Viewer"


@dataclass
class ActionDefinition:
    """Definition of a micro-action with its metadata and rules"""
    id: ActionId
    label: str
    icon: str
    action_type: str  # 'navigate', 'modal', 'api_call', 'copy'
    requires_confirmation: bool = False

    # Role restrictions (empty = all roles)
    allowed_roles: Set[UserRole] = field(default_factory=set)

    # Card type restrictions (empty = all types)
    allowed_card_types: Set[CardType] = field(default_factory=set)

    # Intent boost (actions more relevant for these intents)
    boosted_intents: Set[IntentType] = field(default_factory=set)

    # Yacht configuration requirements
    requires_feature: Optional[str] = None  # e.g., 'predictive_enabled'


# =============================================================================
# ACTION CATALOGUE
# =============================================================================

ACTION_CATALOGUE: Dict[ActionId, ActionDefinition] = {
    # ----- DOCUMENT ACTIONS -----
    ActionId.OPEN_DOCUMENT: ActionDefinition(
        id=ActionId.OPEN_DOCUMENT,
        label="Open Document",
        icon="document",
        action_type="navigate",
        allowed_card_types={CardType.DOCUMENT},
        boosted_intents={IntentType.FIND_DOCUMENT, IntentType.DIAGNOSE_FAULT}
    ),
    ActionId.DOWNLOAD_DOCUMENT: ActionDefinition(
        id=ActionId.DOWNLOAD_DOCUMENT,
        label="Download",
        icon="download",
        action_type="api_call",
        allowed_card_types={CardType.DOCUMENT},
    ),
    ActionId.COPY_LINK: ActionDefinition(
        id=ActionId.COPY_LINK,
        label="Copy Link",
        icon="link",
        action_type="copy",
        allowed_card_types={CardType.DOCUMENT, CardType.WORK_ORDER, CardType.HANDOVER},
    ),

    # ----- EQUIPMENT ACTIONS -----
    ActionId.VIEW_EQUIPMENT: ActionDefinition(
        id=ActionId.VIEW_EQUIPMENT,
        label="View Equipment",
        icon="engine",
        action_type="navigate",
        allowed_card_types={CardType.EQUIPMENT, CardType.FAULT, CardType.WORK_ORDER},
    ),
    ActionId.VIEW_EQUIPMENT_HISTORY: ActionDefinition(
        id=ActionId.VIEW_EQUIPMENT_HISTORY,
        label="View History",
        icon="history",
        action_type="navigate",
        allowed_card_types={CardType.EQUIPMENT, CardType.FAULT},
        boosted_intents={IntentType.DIAGNOSE_FAULT, IntentType.PREDICTIVE_REQUEST}
    ),
    ActionId.CREATE_WORK_ORDER: ActionDefinition(
        id=ActionId.CREATE_WORK_ORDER,
        label="Create Work Order",
        icon="wrench",
        action_type="modal",
        requires_confirmation=False,
        allowed_roles={UserRole.CHIEF_ENGINEER, UserRole.HOD, UserRole.ENGINEER, UserRole.ETO},
        allowed_card_types={CardType.EQUIPMENT, CardType.FAULT, CardType.PREDICTIVE},
        boosted_intents={IntentType.DIAGNOSE_FAULT, IntentType.CREATE_WORK_ORDER}
    ),
    ActionId.SHOW_PREDICTIVE_INSIGHT: ActionDefinition(
        id=ActionId.SHOW_PREDICTIVE_INSIGHT,
        label="Predictive Insight",
        icon="chart",
        action_type="modal",
        allowed_card_types={CardType.EQUIPMENT, CardType.PREDICTIVE},
        boosted_intents={IntentType.PREDICTIVE_REQUEST},
        requires_feature="predictive_enabled"
    ),

    # ----- FAULT ACTIONS -----
    ActionId.VIEW_FAULT_DETAILS: ActionDefinition(
        id=ActionId.VIEW_FAULT_DETAILS,
        label="View Details",
        icon="alert",
        action_type="navigate",
        allowed_card_types={CardType.FAULT},
    ),
    ActionId.FIND_RELATED_MANUAL: ActionDefinition(
        id=ActionId.FIND_RELATED_MANUAL,
        label="Find Manual",
        icon="book",
        action_type="api_call",
        allowed_card_types={CardType.FAULT, CardType.EQUIPMENT},
        boosted_intents={IntentType.DIAGNOSE_FAULT, IntentType.FIND_DOCUMENT}
    ),
    ActionId.VIEW_FAULT_HISTORY: ActionDefinition(
        id=ActionId.VIEW_FAULT_HISTORY,
        label="Fault History",
        icon="history",
        action_type="navigate",
        allowed_card_types={CardType.FAULT},
        boosted_intents={IntentType.DIAGNOSE_FAULT, IntentType.PREDICTIVE_REQUEST}
    ),

    # ----- PART ACTIONS -----
    ActionId.VIEW_PART_STOCK: ActionDefinition(
        id=ActionId.VIEW_PART_STOCK,
        label="View Stock",
        icon="inventory",
        action_type="navigate",
        allowed_card_types={CardType.PART},
        boosted_intents={IntentType.FIND_PART}
    ),
    ActionId.ORDER_PART: ActionDefinition(
        id=ActionId.ORDER_PART,
        label="Order Part",
        icon="cart",
        action_type="modal",
        requires_confirmation=True,
        allowed_roles={UserRole.CHIEF_ENGINEER, UserRole.HOD, UserRole.ENGINEER},
        allowed_card_types={CardType.PART},
        boosted_intents={IntentType.FIND_PART}
    ),
    ActionId.ADD_PART_TO_WORK_ORDER: ActionDefinition(
        id=ActionId.ADD_PART_TO_WORK_ORDER,
        label="Add to Work Order",
        icon="plus",
        action_type="modal",
        allowed_roles={UserRole.CHIEF_ENGINEER, UserRole.HOD, UserRole.ENGINEER, UserRole.ETO},
        allowed_card_types={CardType.PART},
        boosted_intents={IntentType.CREATE_WORK_ORDER}
    ),
    ActionId.FIND_SUBSTITUTE: ActionDefinition(
        id=ActionId.FIND_SUBSTITUTE,
        label="Find Substitute",
        icon="swap",
        action_type="api_call",
        allowed_card_types={CardType.PART},
        boosted_intents={IntentType.FIND_PART}
    ),

    # ----- WORK ORDER ACTIONS -----
    ActionId.VIEW_WORK_ORDER: ActionDefinition(
        id=ActionId.VIEW_WORK_ORDER,
        label="View Details",
        icon="clipboard",
        action_type="navigate",
        allowed_card_types={CardType.WORK_ORDER},
    ),
    ActionId.CLONE_WORK_ORDER: ActionDefinition(
        id=ActionId.CLONE_WORK_ORDER,
        label="Clone as Template",
        icon="copy",
        action_type="modal",
        allowed_roles={UserRole.CHIEF_ENGINEER, UserRole.HOD, UserRole.ENGINEER},
        allowed_card_types={CardType.WORK_ORDER},
        boosted_intents={IntentType.CREATE_WORK_ORDER}
    ),

    # ----- HANDOVER ACTIONS -----
    ActionId.VIEW_HANDOVER: ActionDefinition(
        id=ActionId.VIEW_HANDOVER,
        label="View Handover",
        icon="handover",
        action_type="navigate",
        allowed_card_types={CardType.HANDOVER},
    ),
    ActionId.ADD_TO_HANDOVER: ActionDefinition(
        id=ActionId.ADD_TO_HANDOVER,
        label="Add to Handover",
        icon="clipboard-plus",
        action_type="api_call",
        allowed_roles={UserRole.CHIEF_ENGINEER, UserRole.HOD, UserRole.ENGINEER, UserRole.ETO},
        allowed_card_types={
            CardType.DOCUMENT, CardType.FAULT, CardType.WORK_ORDER,
            CardType.EQUIPMENT, CardType.PART, CardType.NOTE
        },
        boosted_intents={IntentType.ADD_TO_HANDOVER}
    ),

    # ----- UNIVERSAL ACTIONS -----
    ActionId.BOOKMARK: ActionDefinition(
        id=ActionId.BOOKMARK,
        label="Bookmark",
        icon="bookmark",
        action_type="api_call",
    ),
    ActionId.COPY_SNIPPET: ActionDefinition(
        id=ActionId.COPY_SNIPPET,
        label="Copy Snippet",
        icon="copy",
        action_type="copy",
    ),
}


# =============================================================================
# CARD TYPE -> DEFAULT ACTIONS MAPPING
# =============================================================================

DEFAULT_ACTIONS_BY_CARD_TYPE: Dict[CardType, List[ActionId]] = {
    CardType.DOCUMENT: [
        ActionId.OPEN_DOCUMENT,
        ActionId.ADD_TO_HANDOVER,
        ActionId.COPY_LINK,
        ActionId.DOWNLOAD_DOCUMENT,
    ],
    CardType.EQUIPMENT: [
        ActionId.VIEW_EQUIPMENT,
        ActionId.VIEW_EQUIPMENT_HISTORY,
        ActionId.CREATE_WORK_ORDER,
        ActionId.SHOW_PREDICTIVE_INSIGHT,
    ],
    CardType.FAULT: [
        ActionId.VIEW_FAULT_DETAILS,
        ActionId.CREATE_WORK_ORDER,
        ActionId.FIND_RELATED_MANUAL,
        ActionId.ADD_TO_HANDOVER,
    ],
    CardType.PART: [
        ActionId.VIEW_PART_STOCK,
        ActionId.ORDER_PART,
        ActionId.ADD_PART_TO_WORK_ORDER,
        ActionId.FIND_SUBSTITUTE,
    ],
    CardType.PREDICTIVE: [
        ActionId.VIEW_EQUIPMENT,
        ActionId.CREATE_WORK_ORDER,
        ActionId.VIEW_EQUIPMENT_HISTORY,
        ActionId.SHOW_PREDICTIVE_INSIGHT,
    ],
    CardType.HANDOVER: [
        ActionId.VIEW_HANDOVER,
        ActionId.COPY_LINK,
    ],
    CardType.WORK_ORDER: [
        ActionId.VIEW_WORK_ORDER,
        ActionId.VIEW_EQUIPMENT,
        ActionId.CLONE_WORK_ORDER,
        ActionId.ADD_TO_HANDOVER,
    ],
    CardType.NOTE: [
        ActionId.ADD_TO_HANDOVER,
        ActionId.COPY_SNIPPET,
    ],
}


# =============================================================================
# ACTION ASSIGNMENT LOGIC
# =============================================================================

def get_actions_for_card(
    card_type: CardType,
    intent: IntentType,
    user_role: UserRole,
    yacht_config: Optional[Dict[str, Any]] = None,
    metadata: Optional[Dict[str, Any]] = None,
    max_actions: int = 4
) -> List[MicroAction]:
    """
    Get appropriate micro-actions for a card based on context

    Args:
        card_type: Type of card
        intent: Detected search intent
        user_role: User's role
        yacht_config: Yacht-specific feature flags
        metadata: Card metadata for building payloads
        max_actions: Maximum actions to return (default 4)

    Returns:
        List of MicroAction objects
    """
    yacht_config = yacht_config or {}
    metadata = metadata or {}

    # Get candidate actions for this card type
    candidate_action_ids = DEFAULT_ACTIONS_BY_CARD_TYPE.get(card_type, [])

    # Score and filter actions
    scored_actions: List[tuple[float, ActionId]] = []

    for action_id in candidate_action_ids:
        action_def = ACTION_CATALOGUE.get(action_id)
        if not action_def:
            continue

        # Check role permissions
        if action_def.allowed_roles and user_role not in action_def.allowed_roles:
            continue

        # Check feature requirements
        if action_def.requires_feature:
            if not yacht_config.get(action_def.requires_feature, False):
                continue

        # Calculate relevance score
        score = 1.0

        # Boost if action matches intent
        if intent in action_def.boosted_intents:
            score += 0.5

        # Special case: suppress "Create Work Order" if intent is already create_work_order
        if action_id == ActionId.CREATE_WORK_ORDER and intent == IntentType.CREATE_WORK_ORDER:
            score -= 0.3  # Still include but lower priority

        # Special case: boost "Add to Handover" if intent is add_to_handover
        if action_id == ActionId.ADD_TO_HANDOVER and intent == IntentType.ADD_TO_HANDOVER:
            score += 1.0  # Make it primary

        scored_actions.append((score, action_id))

    # Sort by score (descending) and take top N
    scored_actions.sort(key=lambda x: x[0], reverse=True)
    selected_ids = [action_id for _, action_id in scored_actions[:max_actions]]

    # Build MicroAction objects with payloads
    actions = []
    for action_id in selected_ids:
        action = build_micro_action(action_id, card_type, metadata)
        if action:
            actions.append(action)

    return actions


def build_micro_action(
    action_id: ActionId,
    card_type: CardType,
    metadata: Dict[str, Any]
) -> Optional[MicroAction]:
    """
    Build a MicroAction with appropriate payload based on context

    Args:
        action_id: Action identifier
        card_type: Card type
        metadata: Card metadata

    Returns:
        MicroAction object or None
    """
    action_def = ACTION_CATALOGUE.get(action_id)
    if not action_def:
        return None

    # Build payload based on action type
    payload = {}

    if action_id == ActionId.OPEN_DOCUMENT:
        payload = {
            "document_id": metadata.get("document_id"),
            "page": metadata.get("page_number"),
            "chunk_index": metadata.get("chunk_index"),
        }

    elif action_id == ActionId.DOWNLOAD_DOCUMENT:
        payload = {
            "document_id": metadata.get("document_id"),
            "filename": metadata.get("filename"),
        }

    elif action_id == ActionId.VIEW_EQUIPMENT:
        payload = {
            "equipment_id": metadata.get("equipment_id"),
        }

    elif action_id == ActionId.VIEW_EQUIPMENT_HISTORY:
        payload = {
            "equipment_id": metadata.get("equipment_id"),
            "filter": "all",
        }

    elif action_id == ActionId.CREATE_WORK_ORDER:
        payload = {
            "equipment_id": metadata.get("equipment_id"),
            "fault_code": metadata.get("fault_code"),
            "prefill_title": _generate_work_order_title(metadata),
        }

    elif action_id == ActionId.SHOW_PREDICTIVE_INSIGHT:
        payload = {
            "equipment_id": metadata.get("equipment_id"),
        }

    elif action_id == ActionId.VIEW_FAULT_DETAILS:
        payload = {
            "fault_id": metadata.get("fault_id") or metadata.get("id"),
        }

    elif action_id == ActionId.FIND_RELATED_MANUAL:
        payload = {
            "equipment_id": metadata.get("equipment_id"),
            "fault_code": metadata.get("fault_code"),
            "search_type": "related_documentation",
        }

    elif action_id == ActionId.VIEW_FAULT_HISTORY:
        payload = {
            "equipment_id": metadata.get("equipment_id"),
            "fault_code": metadata.get("fault_code"),
        }

    elif action_id == ActionId.VIEW_PART_STOCK:
        payload = {
            "part_id": metadata.get("part_id") or metadata.get("id"),
        }

    elif action_id == ActionId.ORDER_PART:
        payload = {
            "part_id": metadata.get("part_id") or metadata.get("id"),
            "part_number": metadata.get("part_number"),
            "current_stock": metadata.get("stock_level", 0),
        }

    elif action_id == ActionId.ADD_PART_TO_WORK_ORDER:
        payload = {
            "part_id": metadata.get("part_id") or metadata.get("id"),
            "part_number": metadata.get("part_number"),
        }

    elif action_id == ActionId.FIND_SUBSTITUTE:
        payload = {
            "part_id": metadata.get("part_id") or metadata.get("id"),
            "part_number": metadata.get("part_number"),
        }

    elif action_id == ActionId.VIEW_WORK_ORDER:
        payload = {
            "work_order_id": metadata.get("work_order_id") or metadata.get("id"),
        }

    elif action_id == ActionId.CLONE_WORK_ORDER:
        payload = {
            "source_work_order_id": metadata.get("work_order_id") or metadata.get("id"),
        }

    elif action_id == ActionId.VIEW_HANDOVER:
        payload = {
            "handover_id": metadata.get("handover_id") or metadata.get("id"),
        }

    elif action_id == ActionId.ADD_TO_HANDOVER:
        payload = {
            "source_type": card_type.value,
            "source_id": metadata.get("id"),
            "title": metadata.get("title", ""),
        }

    elif action_id == ActionId.COPY_LINK:
        payload = {
            "entity_type": card_type.value,
            "entity_id": metadata.get("id"),
        }

    elif action_id == ActionId.COPY_SNIPPET:
        payload = {
            "text": metadata.get("snippet", ""),
        }

    # Clean None values from payload
    payload = {k: v for k, v in payload.items() if v is not None}

    return MicroAction(
        id=action_id.value,
        label=action_def.label,
        icon=action_def.icon,
        action_type=action_def.action_type,
        payload=payload,
        requires_confirmation=action_def.requires_confirmation
    )


def _generate_work_order_title(metadata: Dict[str, Any]) -> str:
    """Generate a prefilled work order title from metadata"""
    parts = []

    if metadata.get("fault_code"):
        parts.append(f"Fix fault {metadata['fault_code']}")
    elif metadata.get("equipment_name"):
        parts.append(f"Work on {metadata['equipment_name']}")
    else:
        parts.append("New work order")

    return " - ".join(parts)
