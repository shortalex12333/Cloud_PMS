#!/usr/bin/env python3
"""
Email RAG Micro-Actions Module (M4)

Defines micro-action metadata schema and precondition logic for
email-focused operations. These actions bridge emails to operational entities.

Architecture:
- Focus endpoint returns available actions based on email content
- Preconditions evaluate extracted entities and linked state
- Frontend renders action buttons with reasons

Actions for v1:
- link_to_work_order: Suggest/confirm linking email to existing WO
- create_work_order_from_email: Create new WO from email content
- attach_evidence: Save attachment as document evidence
- link_to_equipment: Link email to equipment (via extracted entities)
- link_to_part: Link email to part (via part numbers)
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field, asdict
from enum import Enum


class Severity(str, Enum):
    """Action severity levels for UI styling."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class SideEffect(str, Enum):
    """Action side effect classification."""
    READ_ONLY = "read_only"
    MUTATION_LIGHT = "mutation_light"
    MUTATION_HEAVY = "mutation_heavy"


@dataclass
class Precondition:
    """
    Precondition for action availability.

    All preconditions must be satisfied for action to appear.
    """
    key: str  # Unique identifier (e.g., "has_work_order_mention")
    description: str  # Human-readable description
    satisfied: bool  # Whether condition is met
    reason: Optional[str] = None  # Why condition is/isn't met


@dataclass
class InputField:
    """Input field schema for action parameters."""
    name: str
    type: str  # "text", "select", "entity_picker", "file"
    label: str
    required: bool = True
    default: Optional[Any] = None
    options: Optional[List[Dict[str, str]]] = None  # For select fields
    entity_type: Optional[str] = None  # For entity_picker fields


@dataclass
class EmailMicroAction:
    """
    Email-focused micro-action definition.

    Returned by focus endpoint to describe available actions
    for a specific email message.
    """
    id: str  # Unique action ID
    name: str  # Action name (snake_case)
    label: str  # Display label
    description: str  # Help text

    # Access control
    allowed_roles: List[str]  # Roles that can execute
    requires_signature: bool = False  # Requires HOD signature

    # Classification
    severity: Severity = Severity.INFO
    side_effect: SideEffect = SideEffect.MUTATION_LIGHT

    # Preconditions (all must be satisfied)
    preconditions: List[Precondition] = field(default_factory=list)

    # Input schema (for action parameters)
    inputs_schema: List[InputField] = field(default_factory=list)

    # Explainability
    explain_why: str = ""  # Why this action is suggested
    confidence: float = 0.0  # Suggestion confidence (0-1)

    # State
    available: bool = True  # All preconditions met
    disabled_reason: Optional[str] = None  # Why action is disabled

    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return {
            'id': self.id,
            'name': self.name,
            'label': self.label,
            'description': self.description,
            'allowed_roles': self.allowed_roles,
            'requires_signature': self.requires_signature,
            'severity': self.severity.value,
            'side_effect': self.side_effect.value,
            'preconditions': [asdict(p) for p in self.preconditions],
            'inputs_schema': [asdict(i) for i in self.inputs_schema],
            'explain_why': self.explain_why,
            'confidence': self.confidence,
            'available': self.available,
            'disabled_reason': self.disabled_reason,
        }


# =============================================================================
# ACTION DEFINITIONS (v1)
# =============================================================================

def link_to_work_order_action(
    has_wo_mention: bool,
    mentioned_wo_ids: List[str],
    existing_links: List[str],
) -> EmailMicroAction:
    """
    Build link_to_work_order action.

    Preconditions:
    - Email mentions a work order (WO-1234, #1234, etc.)
    - Email is not already linked to that WO
    """
    preconditions = [
        Precondition(
            key="has_wo_mention",
            description="Email mentions a work order",
            satisfied=has_wo_mention,
            reason=f"Found WO references: {mentioned_wo_ids}" if has_wo_mention else "No work order references found in email",
        ),
        Precondition(
            key="not_already_linked",
            description="Email not already linked to this work order",
            satisfied=not any(wo in existing_links for wo in mentioned_wo_ids) if mentioned_wo_ids else True,
            reason="Already linked" if mentioned_wo_ids and any(wo in existing_links for wo in mentioned_wo_ids) else None,
        ),
    ]

    all_satisfied = all(p.satisfied for p in preconditions)

    return EmailMicroAction(
        id="email_link_to_wo",
        name="link_to_work_order",
        label="Link to Work Order",
        description="Link this email thread to an existing work order",
        allowed_roles=["chief_engineer", "eto", "captain", "manager", "member"],
        requires_signature=False,
        severity=Severity.INFO,
        side_effect=SideEffect.MUTATION_LIGHT,
        preconditions=preconditions,
        inputs_schema=[
            InputField(
                name="work_order_id",
                type="entity_picker" if not mentioned_wo_ids else "select",
                label="Work Order",
                required=True,
                options=[{"value": wo, "label": f"WO {wo}"} for wo in mentioned_wo_ids] if mentioned_wo_ids else None,
                entity_type="work_order" if not mentioned_wo_ids else None,
            ),
        ],
        explain_why=f"Email references work order(s): {', '.join(mentioned_wo_ids)}" if mentioned_wo_ids else "",
        confidence=0.9 if has_wo_mention else 0.0,
        available=all_satisfied,
        disabled_reason=next((p.reason for p in preconditions if not p.satisfied), None),
    )


def create_work_order_action(
    has_actionable_content: bool,
    extracted_equipment: List[str],
    extracted_symptoms: List[str],
    user_role: str,
) -> EmailMicroAction:
    """
    Build create_work_order_from_email action.

    Preconditions:
    - Email has actionable content (equipment, symptoms, actions)
    - User has permission to create work orders
    """
    can_create_wo = user_role in ["chief_engineer", "eto", "captain", "manager"]

    preconditions = [
        Precondition(
            key="has_actionable_content",
            description="Email contains equipment or symptoms",
            satisfied=has_actionable_content,
            reason=f"Found: {extracted_equipment + extracted_symptoms}" if has_actionable_content else "No equipment or symptoms detected",
        ),
        Precondition(
            key="can_create_wo",
            description="User can create work orders",
            satisfied=can_create_wo,
            reason=f"Role {user_role} cannot create work orders" if not can_create_wo else None,
        ),
    ]

    all_satisfied = all(p.satisfied for p in preconditions)

    # Build suggested title
    suggested_title = ""
    if extracted_equipment and extracted_symptoms:
        suggested_title = f"{extracted_equipment[0].title()} - {extracted_symptoms[0]}"
    elif extracted_equipment:
        suggested_title = f"{extracted_equipment[0].title()} - Maintenance"
    elif extracted_symptoms:
        suggested_title = f"Issue - {extracted_symptoms[0]}"

    return EmailMicroAction(
        id="email_create_wo",
        name="create_work_order_from_email",
        label="Create Work Order",
        description="Create a new work order from this email's content",
        allowed_roles=["chief_engineer", "eto", "captain", "manager"],
        requires_signature=False,
        severity=Severity.INFO,
        side_effect=SideEffect.MUTATION_HEAVY,
        preconditions=preconditions,
        inputs_schema=[
            InputField(
                name="title",
                type="text",
                label="Work Order Title",
                required=True,
                default=suggested_title,
            ),
            InputField(
                name="equipment_id",
                type="entity_picker",
                label="Equipment",
                required=False,
                entity_type="equipment",
            ),
            InputField(
                name="priority",
                type="select",
                label="Priority",
                required=True,
                default="medium",
                options=[
                    {"value": "low", "label": "Low"},
                    {"value": "medium", "label": "Medium"},
                    {"value": "high", "label": "High"},
                    {"value": "critical", "label": "Critical"},
                ],
            ),
        ],
        explain_why=f"Email mentions {', '.join(extracted_equipment[:2])}" if extracted_equipment else "Email contains actionable maintenance content",
        confidence=0.7 if has_actionable_content else 0.0,
        available=all_satisfied,
        disabled_reason=next((p.reason for p in preconditions if not p.satisfied), None),
    )


def attach_evidence_action(
    has_attachments: bool,
    attachment_count: int,
    user_role: str,
) -> EmailMicroAction:
    """
    Build attach_evidence action.

    Preconditions:
    - Email has attachments
    """
    preconditions = [
        Precondition(
            key="has_attachments",
            description="Email has attachments",
            satisfied=has_attachments,
            reason=f"{attachment_count} attachment(s) available" if has_attachments else "No attachments in this email",
        ),
    ]

    all_satisfied = all(p.satisfied for p in preconditions)

    return EmailMicroAction(
        id="email_attach_evidence",
        name="attach_evidence",
        label="Save Attachment",
        description="Save email attachment to yacht document library",
        allowed_roles=["chief_engineer", "eto", "captain", "manager", "member"],
        requires_signature=False,
        severity=Severity.INFO,
        side_effect=SideEffect.MUTATION_LIGHT,
        preconditions=preconditions,
        inputs_schema=[
            InputField(
                name="attachment_id",
                type="select",
                label="Attachment",
                required=True,
            ),
            InputField(
                name="target_folder",
                type="text",
                label="Folder",
                required=False,
                default="email-attachments",
            ),
        ],
        explain_why=f"Email has {attachment_count} attachment(s) that can be saved",
        confidence=0.95 if has_attachments else 0.0,
        available=all_satisfied,
        disabled_reason=next((p.reason for p in preconditions if not p.satisfied), None),
    )


def link_to_equipment_action(
    has_equipment_mention: bool,
    mentioned_equipment: List[str],
    existing_links: List[str],
) -> EmailMicroAction:
    """
    Build link_to_equipment action.

    Preconditions:
    - Email mentions equipment
    - Email not already linked to that equipment
    """
    preconditions = [
        Precondition(
            key="has_equipment_mention",
            description="Email mentions equipment",
            satisfied=has_equipment_mention,
            reason=f"Found equipment: {mentioned_equipment}" if has_equipment_mention else "No equipment references found",
        ),
    ]

    all_satisfied = all(p.satisfied for p in preconditions)

    return EmailMicroAction(
        id="email_link_to_equipment",
        name="link_to_equipment",
        label="Link to Equipment",
        description="Link this email thread to equipment",
        allowed_roles=["chief_engineer", "eto", "captain", "manager", "member"],
        requires_signature=False,
        severity=Severity.INFO,
        side_effect=SideEffect.MUTATION_LIGHT,
        preconditions=preconditions,
        inputs_schema=[
            InputField(
                name="equipment_id",
                type="entity_picker",
                label="Equipment",
                required=True,
                entity_type="equipment",
            ),
        ],
        explain_why=f"Email mentions: {', '.join(mentioned_equipment[:3])}" if mentioned_equipment else "",
        confidence=0.75 if has_equipment_mention else 0.0,
        available=all_satisfied,
        disabled_reason=next((p.reason for p in preconditions if not p.satisfied), None),
    )


def link_to_part_action(
    has_part_mention: bool,
    mentioned_parts: List[str],
) -> EmailMicroAction:
    """
    Build link_to_part action.

    Preconditions:
    - Email mentions part numbers
    """
    preconditions = [
        Precondition(
            key="has_part_mention",
            description="Email mentions part numbers",
            satisfied=has_part_mention,
            reason=f"Found part numbers: {mentioned_parts}" if has_part_mention else "No part numbers found",
        ),
    ]

    all_satisfied = all(p.satisfied for p in preconditions)

    return EmailMicroAction(
        id="email_link_to_part",
        name="link_to_part",
        label="Link to Part",
        description="Link this email thread to a part",
        allowed_roles=["chief_engineer", "eto", "captain", "manager", "member"],
        requires_signature=False,
        severity=Severity.INFO,
        side_effect=SideEffect.MUTATION_LIGHT,
        preconditions=preconditions,
        inputs_schema=[
            InputField(
                name="part_id",
                type="entity_picker",
                label="Part",
                required=True,
                entity_type="part",
            ),
        ],
        explain_why=f"Email mentions part numbers: {', '.join(mentioned_parts[:3])}" if mentioned_parts else "",
        confidence=0.8 if has_part_mention else 0.0,
        available=all_satisfied,
        disabled_reason=next((p.reason for p in preconditions if not p.satisfied), None),
    )


# =============================================================================
# FOCUS RESPONSE BUILDER
# =============================================================================

@dataclass
class FocusResponse:
    """
    Response from focus endpoint.

    Contains email metadata and available micro-actions.
    """
    message_id: str
    thread_id: str
    subject: Optional[str]
    from_display_name: Optional[str]
    sent_at: Optional[str]

    # Extracted entities (for context)
    extracted_entities: Dict[str, List[str]]

    # Available actions with preconditions
    micro_actions: List[EmailMicroAction]

    # Existing links
    linked_objects: List[Dict[str, str]]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return {
            'message_id': self.message_id,
            'thread_id': self.thread_id,
            'subject': self.subject,
            'from_display_name': self.from_display_name,
            'sent_at': self.sent_at,
            'extracted_entities': self.extracted_entities,
            'micro_actions': [a.to_dict() for a in self.micro_actions],
            'linked_objects': self.linked_objects,
        }


def build_focus_response(
    message_id: str,
    thread_id: str,
    subject: Optional[str],
    from_display_name: Optional[str],
    sent_at: Optional[str],
    has_attachments: bool,
    attachment_count: int,
    extracted_entities: Dict[str, List[str]],
    existing_links: List[Dict[str, str]],
    user_role: str,
) -> FocusResponse:
    """
    Build complete focus response with all available micro-actions.

    Args:
        message_id: UUID of email_messages record
        thread_id: UUID of email_threads record
        subject: Email subject
        from_display_name: Sender display name
        sent_at: Sent timestamp
        has_attachments: Whether email has attachments
        attachment_count: Number of attachments
        extracted_entities: Dict of entity_type -> values
        existing_links: List of existing email_links
        user_role: Current user's role

    Returns:
        FocusResponse with all available micro-actions
    """
    # Extract specific entity types for action building
    work_order_refs = extracted_entities.get('document_id', [])
    equipment_refs = extracted_entities.get('equipment', []) + extracted_entities.get('subcomponent', [])
    part_refs = extracted_entities.get('part_number', [])
    symptoms = extracted_entities.get('symptom', []) + extracted_entities.get('status', [])

    existing_link_ids = [link.get('object_id', '') for link in existing_links]

    # Build all available actions
    actions = []

    # Link to work order
    wo_action = link_to_work_order_action(
        has_wo_mention=len(work_order_refs) > 0,
        mentioned_wo_ids=work_order_refs,
        existing_links=existing_link_ids,
    )
    actions.append(wo_action)

    # Create work order
    has_actionable = len(equipment_refs) > 0 or len(symptoms) > 0
    create_wo_action = create_work_order_action(
        has_actionable_content=has_actionable,
        extracted_equipment=equipment_refs,
        extracted_symptoms=symptoms,
        user_role=user_role,
    )
    actions.append(create_wo_action)

    # Attach evidence
    evidence_action = attach_evidence_action(
        has_attachments=has_attachments,
        attachment_count=attachment_count,
        user_role=user_role,
    )
    actions.append(evidence_action)

    # Link to equipment
    equipment_action = link_to_equipment_action(
        has_equipment_mention=len(equipment_refs) > 0,
        mentioned_equipment=equipment_refs,
        existing_links=existing_link_ids,
    )
    actions.append(equipment_action)

    # Link to part
    part_action = link_to_part_action(
        has_part_mention=len(part_refs) > 0,
        mentioned_parts=part_refs,
    )
    actions.append(part_action)

    # Sort by confidence (highest first), then by availability
    actions.sort(key=lambda a: (-int(a.available), -a.confidence))

    return FocusResponse(
        message_id=message_id,
        thread_id=thread_id,
        subject=subject,
        from_display_name=from_display_name,
        sent_at=sent_at,
        extracted_entities=extracted_entities,
        micro_actions=actions,
        linked_objects=existing_links,
    )


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    'EmailMicroAction',
    'Precondition',
    'InputField',
    'Severity',
    'SideEffect',
    'FocusResponse',
    'build_focus_response',
    'link_to_work_order_action',
    'create_work_order_action',
    'attach_evidence_action',
    'link_to_equipment_action',
    'link_to_part_action',
]
