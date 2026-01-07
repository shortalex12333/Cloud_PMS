"""
Action Registry
================

Defines all microactions available in the system with READ/MUTATE classification.

Rules:
- Every action has a canonical action_id
- Every action is READ or MUTATE (no third type)
- MUTATE actions require signature, diff preview, and audit log
- Primary actions MUST be READ
- MUTATE actions MUST live behind dropdown logic

Usage:
    from action_registry import get_registry, ActionVariant

    registry = get_registry()
    action = registry.get_action("view_inventory_item")

    if action.variant == ActionVariant.MUTATE:
        # Require signature flow
        pass
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class ActionVariant(str, Enum):
    """Action classification - READ or MUTATE only"""
    READ = "READ"
    MUTATE = "MUTATE"


class AuditLevel(str, Enum):
    """Audit logging levels"""
    NONE = "none"      # No audit logging (READ actions)
    BASIC = "basic"    # Log action + user + timestamp
    FULL = "full"      # Log action + user + timestamp + before/after diff


@dataclass
class ActionUI:
    """UI configuration for action"""
    primary: bool = False           # Can be primary action on card
    dropdown_only: bool = False     # Only show in dropdown menu
    icon: str = ""                  # Icon identifier
    label_override: str = ""        # Override default label


@dataclass
class ActionExecution:
    """Execution configuration"""
    handler: str = ""               # Handler function name
    timeout_ms: int = 30000         # Execution timeout
    requires_entity_id: bool = True # Requires target entity


@dataclass
class ActionMutation:
    """Mutation-specific configuration (only for MUTATE actions)"""
    requires_signature: bool = True
    preview_diff: bool = True
    reversible: bool = False
    confirmation_message: str = ""


@dataclass
class ActionAudit:
    """Audit configuration"""
    level: AuditLevel = AuditLevel.NONE
    retention_days: int = 90


@dataclass
class Action:
    """Complete action definition"""
    action_id: str
    label: str
    variant: ActionVariant
    domain: str  # inventory, work_orders, equipment, manual, fault

    # Configurations
    ui: ActionUI = field(default_factory=ActionUI)
    execution: ActionExecution = field(default_factory=ActionExecution)
    mutation: Optional[ActionMutation] = None
    audit: ActionAudit = field(default_factory=ActionAudit)

    # Entity types this action applies to
    entity_types: List[str] = field(default_factory=list)

    # Optional description
    description: str = ""

    def __post_init__(self):
        """Validate action configuration"""
        # READ actions cannot have mutation config
        if self.variant == ActionVariant.READ and self.mutation is not None:
            raise ValueError(f"READ action '{self.action_id}' cannot have mutation config")

        # MUTATE actions must have mutation config
        if self.variant == ActionVariant.MUTATE:
            if self.mutation is None:
                self.mutation = ActionMutation()
            # MUTATE actions must have audit
            if self.audit.level == AuditLevel.NONE:
                self.audit.level = AuditLevel.FULL

        # Primary actions must be READ
        if self.ui.primary and self.variant == ActionVariant.MUTATE:
            raise ValueError(f"Primary action '{self.action_id}' must be READ, not MUTATE")

        # MUTATE actions should be dropdown_only
        if self.variant == ActionVariant.MUTATE and not self.ui.dropdown_only:
            self.ui.dropdown_only = True


class ActionRegistry:
    """
    Central registry for all microactions.

    Provides:
    - Action lookup by ID
    - Action validation
    - Actions by domain
    - Actions by entity type
    """

    def __init__(self):
        self._actions: Dict[str, Action] = {}
        self._by_domain: Dict[str, List[str]] = {}
        self._by_entity_type: Dict[str, List[str]] = {}

    def register(self, action: Action) -> None:
        """Register an action"""
        if action.action_id in self._actions:
            raise ValueError(f"Action '{action.action_id}' already registered")

        self._actions[action.action_id] = action

        # Index by domain
        if action.domain not in self._by_domain:
            self._by_domain[action.domain] = []
        self._by_domain[action.domain].append(action.action_id)

        # Index by entity type
        for entity_type in action.entity_types:
            if entity_type not in self._by_entity_type:
                self._by_entity_type[entity_type] = []
            self._by_entity_type[entity_type].append(action.action_id)

        logger.debug(f"Registered action: {action.action_id} ({action.variant.value})")

    def get_action(self, action_id: str) -> Optional[Action]:
        """Get action by ID"""
        return self._actions.get(action_id)

    def get_actions_for_domain(self, domain: str) -> List[Action]:
        """Get all actions for a domain"""
        action_ids = self._by_domain.get(domain, [])
        return [self._actions[aid] for aid in action_ids]

    def get_actions_for_entity(self, entity_type: str) -> List[Action]:
        """Get all actions applicable to an entity type"""
        action_ids = self._by_entity_type.get(entity_type, [])
        return [self._actions[aid] for aid in action_ids]

    def get_primary_action(self, entity_type: str) -> Optional[Action]:
        """Get the primary (READ) action for an entity type"""
        actions = self.get_actions_for_entity(entity_type)
        for action in actions:
            if action.ui.primary:
                return action
        # If no primary, return first READ action
        for action in actions:
            if action.variant == ActionVariant.READ:
                return action
        return None

    def get_dropdown_actions(self, entity_type: str) -> List[Action]:
        """Get dropdown actions for an entity type"""
        actions = self.get_actions_for_entity(entity_type)
        return [a for a in actions if not a.ui.primary]

    def is_mutate(self, action_id: str) -> bool:
        """Check if action is a MUTATE action"""
        action = self.get_action(action_id)
        return action is not None and action.variant == ActionVariant.MUTATE

    def is_read(self, action_id: str) -> bool:
        """Check if action is a READ action"""
        action = self.get_action(action_id)
        return action is not None and action.variant == ActionVariant.READ

    def validate(self) -> List[str]:
        """Validate registry and return any errors"""
        errors = []

        for action_id, action in self._actions.items():
            # Every entity type must have at least one READ action
            # (This is checked across all actions, not per action)
            pass

        # Check each domain has at least one primary READ action
        for domain, action_ids in self._by_domain.items():
            actions = [self._actions[aid] for aid in action_ids]
            has_primary = any(a.ui.primary and a.variant == ActionVariant.READ for a in actions)
            if not has_primary:
                errors.append(f"Domain '{domain}' has no primary READ action")

        return errors

    def to_dict(self) -> Dict[str, Any]:
        """Export registry as dictionary (for API responses)"""
        return {
            "actions": {
                aid: {
                    "action_id": a.action_id,
                    "label": a.label,
                    "variant": a.variant.value,
                    "domain": a.domain,
                    "primary": a.ui.primary,
                    "dropdown_only": a.ui.dropdown_only,
                    "entity_types": a.entity_types,
                    "requires_signature": a.mutation.requires_signature if a.mutation else False,
                }
                for aid, a in self._actions.items()
            },
            "domains": list(self._by_domain.keys()),
            "entity_types": list(self._by_entity_type.keys()),
        }


# =============================================================================
# DEFAULT REGISTRY
# =============================================================================

def _create_default_registry() -> ActionRegistry:
    """Create and populate the default action registry"""
    registry = ActionRegistry()

    # -------------------------------------------------------------------------
    # INVENTORY DOMAIN
    # -------------------------------------------------------------------------

    # READ: View inventory item details
    registry.register(Action(
        action_id="view_inventory_item",
        label="View Details",
        variant=ActionVariant.READ,
        domain="inventory",
        entity_types=["part", "inventory_item"],
        ui=ActionUI(primary=True, icon="eye"),
        execution=ActionExecution(handler="view_inventory_item"),
        description="View full details of an inventory item"
    ))

    # READ: View stock levels
    registry.register(Action(
        action_id="view_stock_levels",
        label="Stock Levels",
        variant=ActionVariant.READ,
        domain="inventory",
        entity_types=["part", "inventory_item"],
        ui=ActionUI(primary=False, icon="chart"),
        execution=ActionExecution(handler="view_stock_levels"),
        description="View current stock levels and history"
    ))

    # MUTATE: Edit inventory quantity
    registry.register(Action(
        action_id="edit_inventory_quantity",
        label="Adjust Quantity",
        variant=ActionVariant.MUTATE,
        domain="inventory",
        entity_types=["part", "inventory_item"],
        ui=ActionUI(dropdown_only=True, icon="edit"),
        execution=ActionExecution(handler="edit_inventory_quantity"),
        mutation=ActionMutation(
            requires_signature=True,
            preview_diff=True,
            reversible=True,
            confirmation_message="Confirm quantity adjustment"
        ),
        audit=ActionAudit(level=AuditLevel.FULL, retention_days=365),
        description="Adjust inventory quantity (requires signature)"
    ))

    # MUTATE: Create reorder request
    registry.register(Action(
        action_id="create_reorder",
        label="Create Reorder",
        variant=ActionVariant.MUTATE,
        domain="inventory",
        entity_types=["part", "inventory_item"],
        ui=ActionUI(dropdown_only=True, icon="cart"),
        execution=ActionExecution(handler="create_reorder"),
        mutation=ActionMutation(
            requires_signature=True,
            preview_diff=True,
            confirmation_message="Confirm reorder request"
        ),
        audit=ActionAudit(level=AuditLevel.FULL),
        description="Create a reorder request for this item"
    ))

    # -------------------------------------------------------------------------
    # MANUAL/DOCUMENTATION DOMAIN
    # -------------------------------------------------------------------------

    # READ: View manual section
    registry.register(Action(
        action_id="view_manual_section",
        label="View Manual",
        variant=ActionVariant.READ,
        domain="manual",
        entity_types=["document", "manual_section", "document_chunk"],
        ui=ActionUI(primary=True, icon="book"),
        execution=ActionExecution(handler="view_manual_section"),
        description="View the manual section or document"
    ))

    # READ: View related sections
    registry.register(Action(
        action_id="view_related_docs",
        label="Related Docs",
        variant=ActionVariant.READ,
        domain="manual",
        entity_types=["document", "manual_section", "document_chunk"],
        ui=ActionUI(icon="link"),
        execution=ActionExecution(handler="view_related_docs"),
        description="View related documentation"
    ))

    # -------------------------------------------------------------------------
    # EQUIPMENT DOMAIN
    # -------------------------------------------------------------------------

    # READ: View equipment details
    registry.register(Action(
        action_id="view_equipment",
        label="View Equipment",
        variant=ActionVariant.READ,
        domain="equipment",
        entity_types=["equipment"],
        ui=ActionUI(primary=True, icon="cog"),
        execution=ActionExecution(handler="view_equipment"),
        description="View equipment details and status"
    ))

    # READ: View maintenance history
    registry.register(Action(
        action_id="view_maintenance_history",
        label="Maintenance History",
        variant=ActionVariant.READ,
        domain="equipment",
        entity_types=["equipment"],
        ui=ActionUI(icon="history"),
        execution=ActionExecution(handler="view_maintenance_history"),
        description="View maintenance history for this equipment"
    ))

    # -------------------------------------------------------------------------
    # WORK ORDER DOMAIN
    # -------------------------------------------------------------------------

    # READ: View work order
    registry.register(Action(
        action_id="view_work_order",
        label="View Work Order",
        variant=ActionVariant.READ,
        domain="work_orders",
        entity_types=["work_order"],
        ui=ActionUI(primary=True, icon="clipboard"),
        execution=ActionExecution(handler="view_work_order"),
        description="View work order details"
    ))

    # MUTATE: Create work order
    registry.register(Action(
        action_id="create_work_order",
        label="Create Work Order",
        variant=ActionVariant.MUTATE,
        domain="work_orders",
        entity_types=["equipment", "fault"],
        ui=ActionUI(dropdown_only=True, icon="plus"),
        execution=ActionExecution(handler="create_work_order"),
        mutation=ActionMutation(
            requires_signature=True,
            preview_diff=True,
            confirmation_message="Confirm work order creation"
        ),
        audit=ActionAudit(level=AuditLevel.FULL),
        description="Create a new work order"
    ))

    # MUTATE: Update work order status
    registry.register(Action(
        action_id="update_work_order_status",
        label="Update Status",
        variant=ActionVariant.MUTATE,
        domain="work_orders",
        entity_types=["work_order"],
        ui=ActionUI(dropdown_only=True, icon="check"),
        execution=ActionExecution(handler="update_work_order_status"),
        mutation=ActionMutation(
            requires_signature=True,
            preview_diff=True,
            confirmation_message="Confirm status change"
        ),
        audit=ActionAudit(level=AuditLevel.FULL),
        description="Update work order status"
    ))

    # -------------------------------------------------------------------------
    # FAULT DOMAIN
    # -------------------------------------------------------------------------

    # READ: View fault details
    registry.register(Action(
        action_id="view_fault",
        label="View Fault",
        variant=ActionVariant.READ,
        domain="fault",
        entity_types=["fault"],
        ui=ActionUI(primary=True, icon="alert"),
        execution=ActionExecution(handler="view_fault"),
        description="View fault details and diagnosis"
    ))

    # READ: Run diagnostic
    registry.register(Action(
        action_id="run_diagnostic",
        label="Run Diagnostic",
        variant=ActionVariant.READ,
        domain="fault",
        entity_types=["fault", "equipment"],
        ui=ActionUI(icon="search"),
        execution=ActionExecution(handler="run_diagnostic"),
        description="Run diagnostic analysis"
    ))

    # MUTATE: Log symptom
    registry.register(Action(
        action_id="log_symptom",
        label="Log Symptom",
        variant=ActionVariant.MUTATE,
        domain="fault",
        entity_types=["equipment", "fault"],
        ui=ActionUI(dropdown_only=True, icon="note"),
        execution=ActionExecution(handler="log_symptom"),
        mutation=ActionMutation(
            requires_signature=False,  # Low-risk action
            preview_diff=False,
            confirmation_message="Confirm symptom logging"
        ),
        audit=ActionAudit(level=AuditLevel.BASIC),
        description="Log a symptom observation"
    ))

    # -------------------------------------------------------------------------
    # FAULT DOMAIN - Additional Actions (from spec)
    # -------------------------------------------------------------------------

    # READ: Diagnose fault
    registry.register(Action(
        action_id="diagnose_fault",
        label="Diagnose Fault",
        variant=ActionVariant.READ,
        domain="fault",
        entity_types=["fault", "equipment"],
        ui=ActionUI(icon="stethoscope"),
        execution=ActionExecution(handler="diagnose_fault"),
        description="Run fault diagnosis analysis"
    ))

    # MUTATE: Report fault
    registry.register(Action(
        action_id="report_fault",
        label="Report Fault",
        variant=ActionVariant.MUTATE,
        domain="fault",
        entity_types=["equipment"],
        ui=ActionUI(dropdown_only=True, icon="alert-circle"),
        execution=ActionExecution(handler="report_fault"),
        mutation=ActionMutation(
            requires_signature=True,
            preview_diff=True,
            confirmation_message="Confirm fault report"
        ),
        audit=ActionAudit(level=AuditLevel.FULL),
        description="Report a new fault"
    ))

    # READ: View fault history
    registry.register(Action(
        action_id="view_fault_history",
        label="View History",
        variant=ActionVariant.READ,
        domain="fault",
        entity_types=["fault", "equipment"],
        ui=ActionUI(icon="history"),
        execution=ActionExecution(handler="view_fault_history"),
        description="View fault history"
    ))

    # READ: Suggest parts for fault
    registry.register(Action(
        action_id="suggest_parts",
        label="Suggest Parts",
        variant=ActionVariant.READ,
        domain="fault",
        entity_types=["fault", "equipment"],
        ui=ActionUI(icon="package"),
        execution=ActionExecution(handler="suggest_parts"),
        description="Suggest parts for repair"
    ))

    # MUTATE: Add note to fault
    registry.register(Action(
        action_id="add_fault_note",
        label="Add Note",
        variant=ActionVariant.MUTATE,
        domain="fault",
        entity_types=["fault"],
        ui=ActionUI(dropdown_only=True, icon="message"),
        execution=ActionExecution(handler="add_fault_note"),
        mutation=ActionMutation(
            requires_signature=False,
            preview_diff=False,
            confirmation_message="Add note to fault"
        ),
        audit=ActionAudit(level=AuditLevel.BASIC),
        description="Add a note to the fault"
    ))

    # MUTATE: Add photo to fault
    registry.register(Action(
        action_id="add_fault_photo",
        label="Add Photo",
        variant=ActionVariant.MUTATE,
        domain="fault",
        entity_types=["fault"],
        ui=ActionUI(dropdown_only=True, icon="camera"),
        execution=ActionExecution(handler="add_fault_photo"),
        mutation=ActionMutation(
            requires_signature=False,
            preview_diff=False,
            confirmation_message="Upload photo"
        ),
        audit=ActionAudit(level=AuditLevel.BASIC),
        description="Add a photo to the fault"
    ))

    # -------------------------------------------------------------------------
    # WORK ORDER DOMAIN - Additional Actions
    # -------------------------------------------------------------------------

    # READ: View work order history
    registry.register(Action(
        action_id="view_work_order_history",
        label="View History",
        variant=ActionVariant.READ,
        domain="work_orders",
        entity_types=["work_order", "equipment"],
        ui=ActionUI(icon="history"),
        execution=ActionExecution(handler="view_work_order_history"),
        description="View work order history"
    ))

    # MUTATE: Mark work order complete
    registry.register(Action(
        action_id="mark_work_order_complete",
        label="Mark Done",
        variant=ActionVariant.MUTATE,
        domain="work_orders",
        entity_types=["work_order"],
        ui=ActionUI(dropdown_only=True, icon="check-circle"),
        execution=ActionExecution(handler="mark_work_order_complete"),
        mutation=ActionMutation(
            requires_signature=True,
            preview_diff=True,
            confirmation_message="Mark work order as complete"
        ),
        audit=ActionAudit(level=AuditLevel.FULL),
        description="Mark work order as complete"
    ))

    # MUTATE: Add note to work order
    registry.register(Action(
        action_id="add_work_order_note",
        label="Add Note",
        variant=ActionVariant.MUTATE,
        domain="work_orders",
        entity_types=["work_order"],
        ui=ActionUI(dropdown_only=True, icon="message"),
        execution=ActionExecution(handler="add_work_order_note"),
        mutation=ActionMutation(
            requires_signature=False,
            preview_diff=False,
            confirmation_message="Add note"
        ),
        audit=ActionAudit(level=AuditLevel.BASIC),
        description="Add note to work order"
    ))

    # MUTATE: Add photo to work order
    registry.register(Action(
        action_id="add_work_order_photo",
        label="Add Photo",
        variant=ActionVariant.MUTATE,
        domain="work_orders",
        entity_types=["work_order"],
        ui=ActionUI(dropdown_only=True, icon="camera"),
        execution=ActionExecution(handler="add_work_order_photo"),
        mutation=ActionMutation(
            requires_signature=False,
            preview_diff=False,
            confirmation_message="Upload photo"
        ),
        audit=ActionAudit(level=AuditLevel.BASIC),
        description="Add photo to work order"
    ))

    # MUTATE: Add parts to work order
    registry.register(Action(
        action_id="add_parts_to_work_order",
        label="Add Parts",
        variant=ActionVariant.MUTATE,
        domain="work_orders",
        entity_types=["work_order"],
        ui=ActionUI(dropdown_only=True, icon="package"),
        execution=ActionExecution(handler="add_parts_to_work_order"),
        mutation=ActionMutation(
            requires_signature=False,
            preview_diff=True,
            confirmation_message="Add parts to work order"
        ),
        audit=ActionAudit(level=AuditLevel.BASIC),
        description="Add parts to work order"
    ))

    # READ: View work order checklist
    registry.register(Action(
        action_id="view_work_order_checklist",
        label="Show Checklist",
        variant=ActionVariant.READ,
        domain="work_orders",
        entity_types=["work_order"],
        ui=ActionUI(icon="list"),
        execution=ActionExecution(handler="view_work_order_checklist"),
        description="View work order checklist"
    ))

    # MUTATE: Assign work order
    registry.register(Action(
        action_id="assign_work_order",
        label="Assign Task",
        variant=ActionVariant.MUTATE,
        domain="work_orders",
        entity_types=["work_order"],
        ui=ActionUI(dropdown_only=True, icon="user"),
        execution=ActionExecution(handler="assign_work_order"),
        mutation=ActionMutation(
            requires_signature=False,
            preview_diff=True,
            confirmation_message="Assign work order"
        ),
        audit=ActionAudit(level=AuditLevel.BASIC),
        description="Assign work order to crew member"
    ))

    # MUTATE: Edit work order details
    registry.register(Action(
        action_id="edit_work_order_details",
        label="Edit Work Order",
        variant=ActionVariant.MUTATE,
        domain="work_orders",
        entity_types=["work_order"],
        ui=ActionUI(dropdown_only=True, icon="edit"),
        execution=ActionExecution(handler="edit_work_order_details"),
        mutation=ActionMutation(
            requires_signature=True,
            preview_diff=True,
            confirmation_message="Save changes to work order"
        ),
        audit=ActionAudit(level=AuditLevel.FULL),
        description="Edit work order details"
    ))

    # -------------------------------------------------------------------------
    # EQUIPMENT DOMAIN - Additional Actions
    # -------------------------------------------------------------------------

    # READ: View equipment parts
    registry.register(Action(
        action_id="view_equipment_parts",
        label="View Parts",
        variant=ActionVariant.READ,
        domain="equipment",
        entity_types=["equipment"],
        ui=ActionUI(icon="package"),
        execution=ActionExecution(handler="view_equipment_parts"),
        description="View parts for equipment"
    ))

    # READ: View linked faults
    registry.register(Action(
        action_id="view_linked_faults",
        label="View Faults",
        variant=ActionVariant.READ,
        domain="equipment",
        entity_types=["equipment"],
        ui=ActionUI(icon="alert"),
        execution=ActionExecution(handler="view_linked_faults"),
        description="View faults linked to equipment"
    ))

    # READ: View equipment manual
    registry.register(Action(
        action_id="view_equipment_manual",
        label="Open Manual",
        variant=ActionVariant.READ,
        domain="equipment",
        entity_types=["equipment"],
        ui=ActionUI(icon="book"),
        execution=ActionExecution(handler="view_equipment_manual"),
        description="Open manual for equipment"
    ))

    # MUTATE: Add equipment note
    registry.register(Action(
        action_id="add_equipment_note",
        label="Add Note",
        variant=ActionVariant.MUTATE,
        domain="equipment",
        entity_types=["equipment"],
        ui=ActionUI(dropdown_only=True, icon="message"),
        execution=ActionExecution(handler="add_equipment_note"),
        mutation=ActionMutation(
            requires_signature=False,
            preview_diff=False,
            confirmation_message="Add note"
        ),
        audit=ActionAudit(level=AuditLevel.BASIC),
        description="Add note to equipment"
    ))

    # -------------------------------------------------------------------------
    # INVENTORY DOMAIN - Additional Actions
    # -------------------------------------------------------------------------

    # READ: View part location
    registry.register(Action(
        action_id="view_part_location",
        label="View Storage Location",
        variant=ActionVariant.READ,
        domain="inventory",
        entity_types=["part", "inventory_item"],
        ui=ActionUI(icon="map-pin"),
        execution=ActionExecution(handler="view_part_location"),
        description="View storage location"
    ))

    # READ: View part usage
    registry.register(Action(
        action_id="view_part_usage",
        label="View Usage History",
        variant=ActionVariant.READ,
        domain="inventory",
        entity_types=["part", "inventory_item"],
        ui=ActionUI(icon="activity"),
        execution=ActionExecution(handler="view_part_usage"),
        description="View part usage history"
    ))

    # MUTATE: Log part usage
    registry.register(Action(
        action_id="log_part_usage",
        label="Log Usage",
        variant=ActionVariant.MUTATE,
        domain="inventory",
        entity_types=["part", "inventory_item"],
        ui=ActionUI(dropdown_only=True, icon="minus"),
        execution=ActionExecution(handler="log_part_usage"),
        mutation=ActionMutation(
            requires_signature=False,
            preview_diff=True,
            confirmation_message="Log part usage"
        ),
        audit=ActionAudit(level=AuditLevel.BASIC),
        description="Log part usage"
    ))

    # MUTATE: Add part
    registry.register(Action(
        action_id="add_part",
        label="Add Part",
        variant=ActionVariant.MUTATE,
        domain="inventory",
        entity_types=["inventory_item"],
        ui=ActionUI(dropdown_only=True, icon="plus"),
        execution=ActionExecution(handler="add_part", requires_entity_id=False),
        mutation=ActionMutation(
            requires_signature=True,
            preview_diff=True,
            confirmation_message="Add new part to inventory"
        ),
        audit=ActionAudit(level=AuditLevel.FULL),
        description="Add a new part to inventory"
    ))

    # READ: Scan part barcode
    registry.register(Action(
        action_id="scan_part_barcode",
        label="Scan Barcode",
        variant=ActionVariant.READ,
        domain="inventory",
        entity_types=["part", "inventory_item"],
        ui=ActionUI(icon="scan"),
        execution=ActionExecution(handler="scan_part_barcode"),
        description="Scan part barcode"
    ))

    # -------------------------------------------------------------------------
    # HANDOVER DOMAIN (All New)
    # -------------------------------------------------------------------------

    # MUTATE: Add to handover
    registry.register(Action(
        action_id="add_to_handover",
        label="Add to Handover",
        variant=ActionVariant.MUTATE,
        domain="handover",
        entity_types=["fault", "work_order", "equipment", "part", "document_chunk"],
        ui=ActionUI(dropdown_only=True, icon="send"),
        execution=ActionExecution(handler="add_to_handover"),
        mutation=ActionMutation(
            requires_signature=False,
            preview_diff=False,
            confirmation_message="Add to handover"
        ),
        audit=ActionAudit(level=AuditLevel.BASIC),
        description="Add item to handover notes"
    ))

    # MUTATE: Add document to handover
    registry.register(Action(
        action_id="add_document_to_handover",
        label="Add Document",
        variant=ActionVariant.MUTATE,
        domain="handover",
        entity_types=["document", "document_chunk"],
        ui=ActionUI(dropdown_only=True, icon="file-plus"),
        execution=ActionExecution(handler="add_document_to_handover"),
        mutation=ActionMutation(
            requires_signature=False,
            preview_diff=False,
            confirmation_message="Add document to handover"
        ),
        audit=ActionAudit(level=AuditLevel.BASIC),
        description="Add document to handover"
    ))

    # MUTATE: Add predictive insight to handover
    registry.register(Action(
        action_id="add_predictive_insight_to_handover",
        label="Add Insight",
        variant=ActionVariant.MUTATE,
        domain="handover",
        entity_types=["predictive", "equipment"],
        ui=ActionUI(dropdown_only=True, icon="trending-up"),
        execution=ActionExecution(handler="add_predictive_insight_to_handover"),
        mutation=ActionMutation(
            requires_signature=False,
            preview_diff=False,
            confirmation_message="Add insight to handover"
        ),
        audit=ActionAudit(level=AuditLevel.BASIC),
        description="Add predictive insight to handover"
    ))

    # MUTATE: Edit handover section
    registry.register(Action(
        action_id="edit_handover_section",
        label="Edit Section",
        variant=ActionVariant.MUTATE,
        domain="handover",
        entity_types=["handover"],
        ui=ActionUI(dropdown_only=True, icon="edit"),
        execution=ActionExecution(handler="edit_handover_section"),
        mutation=ActionMutation(
            requires_signature=False,
            preview_diff=True,
            confirmation_message="Save section changes"
        ),
        audit=ActionAudit(level=AuditLevel.BASIC),
        description="Edit handover section"
    ))

    # READ: Export handover
    registry.register(Action(
        action_id="export_handover",
        label="Export PDF",
        variant=ActionVariant.READ,
        domain="handover",
        entity_types=["handover"],
        ui=ActionUI(primary=True, icon="download"),
        execution=ActionExecution(handler="export_handover"),
        description="Export handover as PDF"
    ))

    # MUTATE: Regenerate handover summary
    registry.register(Action(
        action_id="regenerate_handover_summary",
        label="Regenerate Summary",
        variant=ActionVariant.MUTATE,
        domain="handover",
        entity_types=["handover"],
        ui=ActionUI(dropdown_only=True, icon="refresh"),
        execution=ActionExecution(handler="regenerate_handover_summary"),
        mutation=ActionMutation(
            requires_signature=False,
            preview_diff=False,
            confirmation_message="Regenerate AI summary"
        ),
        audit=ActionAudit(level=AuditLevel.BASIC),
        description="Regenerate AI summary"
    ))

    # -------------------------------------------------------------------------
    # HOURS OF REST DOMAIN (All New)
    # -------------------------------------------------------------------------

    # READ: View hours of rest
    registry.register(Action(
        action_id="view_hours_of_rest",
        label="View Hours",
        variant=ActionVariant.READ,
        domain="hours_of_rest",
        entity_types=["crew", "hours_of_rest"],
        ui=ActionUI(primary=True, icon="clock"),
        execution=ActionExecution(handler="view_hours_of_rest"),
        description="View hours of rest"
    ))

    # MUTATE: Update hours of rest
    registry.register(Action(
        action_id="update_hours_of_rest",
        label="Update Hours",
        variant=ActionVariant.MUTATE,
        domain="hours_of_rest",
        entity_types=["crew", "hours_of_rest"],
        ui=ActionUI(dropdown_only=True, icon="edit"),
        execution=ActionExecution(handler="update_hours_of_rest"),
        mutation=ActionMutation(
            requires_signature=True,
            preview_diff=True,
            confirmation_message="Update hours of rest"
        ),
        audit=ActionAudit(level=AuditLevel.FULL),
        description="Update hours of rest entry"
    ))

    # READ: Export hours of rest
    registry.register(Action(
        action_id="export_hours_of_rest",
        label="Export Logs",
        variant=ActionVariant.READ,
        domain="hours_of_rest",
        entity_types=["crew", "hours_of_rest"],
        ui=ActionUI(icon="download"),
        execution=ActionExecution(handler="export_hours_of_rest"),
        description="Export hours of rest logs"
    ))

    # READ: View compliance status
    registry.register(Action(
        action_id="view_compliance_status",
        label="Check Compliance",
        variant=ActionVariant.READ,
        domain="hours_of_rest",
        entity_types=["crew", "hours_of_rest"],
        ui=ActionUI(icon="shield"),
        execution=ActionExecution(handler="view_compliance_status"),
        description="Check compliance status"
    ))

    # -------------------------------------------------------------------------
    # PURCHASING DOMAIN (All New)
    # -------------------------------------------------------------------------

    # MUTATE: Create purchase request
    registry.register(Action(
        action_id="create_purchase_request",
        label="Create Purchase",
        variant=ActionVariant.MUTATE,
        domain="purchasing",
        entity_types=["part", "inventory_item", "purchase"],
        ui=ActionUI(dropdown_only=True, icon="shopping-cart"),
        execution=ActionExecution(handler="create_purchase_request"),
        mutation=ActionMutation(
            requires_signature=True,
            preview_diff=True,
            confirmation_message="Create purchase request"
        ),
        audit=ActionAudit(level=AuditLevel.FULL),
        description="Create a purchase request"
    ))

    # MUTATE: Add item to purchase
    registry.register(Action(
        action_id="add_item_to_purchase",
        label="Add Item",
        variant=ActionVariant.MUTATE,
        domain="purchasing",
        entity_types=["purchase"],
        ui=ActionUI(dropdown_only=True, icon="plus"),
        execution=ActionExecution(handler="add_item_to_purchase"),
        mutation=ActionMutation(
            requires_signature=False,
            preview_diff=True,
            confirmation_message="Add item to purchase"
        ),
        audit=ActionAudit(level=AuditLevel.BASIC),
        description="Add item to purchase order"
    ))

    # MUTATE: Approve purchase
    registry.register(Action(
        action_id="approve_purchase",
        label="Approve",
        variant=ActionVariant.MUTATE,
        domain="purchasing",
        entity_types=["purchase"],
        ui=ActionUI(dropdown_only=True, icon="check"),
        execution=ActionExecution(handler="approve_purchase"),
        mutation=ActionMutation(
            requires_signature=True,
            preview_diff=True,
            confirmation_message="Approve purchase"
        ),
        audit=ActionAudit(level=AuditLevel.FULL),
        description="Approve purchase order"
    ))

    # MUTATE: Upload invoice
    registry.register(Action(
        action_id="upload_invoice",
        label="Upload Invoice",
        variant=ActionVariant.MUTATE,
        domain="purchasing",
        entity_types=["purchase"],
        ui=ActionUI(dropdown_only=True, icon="upload"),
        execution=ActionExecution(handler="upload_invoice"),
        mutation=ActionMutation(
            requires_signature=False,
            preview_diff=False,
            confirmation_message="Upload invoice"
        ),
        audit=ActionAudit(level=AuditLevel.BASIC),
        description="Upload invoice document"
    ))

    # READ: Track delivery
    registry.register(Action(
        action_id="track_delivery",
        label="Track Delivery",
        variant=ActionVariant.READ,
        domain="purchasing",
        entity_types=["purchase"],
        ui=ActionUI(primary=True, icon="truck"),
        execution=ActionExecution(handler="track_delivery"),
        description="Track delivery status"
    ))

    # MUTATE: Log delivery received
    registry.register(Action(
        action_id="log_delivery_received",
        label="Log Delivery",
        variant=ActionVariant.MUTATE,
        domain="purchasing",
        entity_types=["purchase"],
        ui=ActionUI(dropdown_only=True, icon="package"),
        execution=ActionExecution(handler="log_delivery_received"),
        mutation=ActionMutation(
            requires_signature=True,
            preview_diff=True,
            confirmation_message="Confirm delivery received"
        ),
        audit=ActionAudit(level=AuditLevel.FULL),
        description="Log delivery as received"
    ))

    # MUTATE: Update purchase status
    registry.register(Action(
        action_id="update_purchase_status",
        label="Update Status",
        variant=ActionVariant.MUTATE,
        domain="purchasing",
        entity_types=["purchase"],
        ui=ActionUI(dropdown_only=True, icon="refresh"),
        execution=ActionExecution(handler="update_purchase_status"),
        mutation=ActionMutation(
            requires_signature=False,
            preview_diff=True,
            confirmation_message="Update status"
        ),
        audit=ActionAudit(level=AuditLevel.BASIC),
        description="Update purchase status"
    ))

    # -------------------------------------------------------------------------
    # CHECKLISTS DOMAIN (All New)
    # -------------------------------------------------------------------------

    # READ: View checklist
    registry.register(Action(
        action_id="view_checklist",
        label="View Checklist",
        variant=ActionVariant.READ,
        domain="checklists",
        entity_types=["checklist", "work_order"],
        ui=ActionUI(primary=True, icon="list"),
        execution=ActionExecution(handler="view_checklist"),
        description="View checklist"
    ))

    # MUTATE: Mark checklist item complete
    registry.register(Action(
        action_id="mark_checklist_item_complete",
        label="Mark Complete",
        variant=ActionVariant.MUTATE,
        domain="checklists",
        entity_types=["checklist_item", "checklist"],
        ui=ActionUI(dropdown_only=True, icon="check"),
        execution=ActionExecution(handler="mark_checklist_item_complete"),
        mutation=ActionMutation(
            requires_signature=False,
            preview_diff=True,
            confirmation_message="Mark item complete"
        ),
        audit=ActionAudit(level=AuditLevel.BASIC),
        description="Mark checklist item complete"
    ))

    # MUTATE: Add checklist note
    registry.register(Action(
        action_id="add_checklist_note",
        label="Add Note",
        variant=ActionVariant.MUTATE,
        domain="checklists",
        entity_types=["checklist_item", "checklist"],
        ui=ActionUI(dropdown_only=True, icon="message"),
        execution=ActionExecution(handler="add_checklist_note"),
        mutation=ActionMutation(
            requires_signature=False,
            preview_diff=False,
            confirmation_message="Add note"
        ),
        audit=ActionAudit(level=AuditLevel.BASIC),
        description="Add note to checklist item"
    ))

    # MUTATE: Add checklist photo
    registry.register(Action(
        action_id="add_checklist_photo",
        label="Add Photo",
        variant=ActionVariant.MUTATE,
        domain="checklists",
        entity_types=["checklist_item", "checklist"],
        ui=ActionUI(dropdown_only=True, icon="camera"),
        execution=ActionExecution(handler="add_checklist_photo"),
        mutation=ActionMutation(
            requires_signature=False,
            preview_diff=False,
            confirmation_message="Upload photo"
        ),
        audit=ActionAudit(level=AuditLevel.BASIC),
        description="Add photo to checklist item"
    ))

    # -------------------------------------------------------------------------
    # SHIPYARD/REFIT DOMAIN (All New)
    # -------------------------------------------------------------------------

    # READ: View worklist
    registry.register(Action(
        action_id="view_worklist",
        label="View Worklist",
        variant=ActionVariant.READ,
        domain="shipyard",
        entity_types=["worklist", "refit"],
        ui=ActionUI(primary=True, icon="clipboard"),
        execution=ActionExecution(handler="view_worklist"),
        description="View shipyard worklist"
    ))

    # MUTATE: Add worklist task
    registry.register(Action(
        action_id="add_worklist_task",
        label="Add Task",
        variant=ActionVariant.MUTATE,
        domain="shipyard",
        entity_types=["worklist", "refit"],
        ui=ActionUI(dropdown_only=True, icon="plus"),
        execution=ActionExecution(handler="add_worklist_task"),
        mutation=ActionMutation(
            requires_signature=True,
            preview_diff=True,
            confirmation_message="Add task to worklist"
        ),
        audit=ActionAudit(level=AuditLevel.FULL),
        description="Add task to worklist"
    ))

    # MUTATE: Update worklist progress
    registry.register(Action(
        action_id="update_worklist_progress",
        label="Update Progress",
        variant=ActionVariant.MUTATE,
        domain="shipyard",
        entity_types=["worklist_item", "worklist"],
        ui=ActionUI(dropdown_only=True, icon="trending-up"),
        execution=ActionExecution(handler="update_worklist_progress"),
        mutation=ActionMutation(
            requires_signature=False,
            preview_diff=True,
            confirmation_message="Update progress"
        ),
        audit=ActionAudit(level=AuditLevel.BASIC),
        description="Update worklist progress"
    ))

    # READ: Export worklist
    registry.register(Action(
        action_id="export_worklist",
        label="Export Worklist",
        variant=ActionVariant.READ,
        domain="shipyard",
        entity_types=["worklist", "refit"],
        ui=ActionUI(icon="download"),
        execution=ActionExecution(handler="export_worklist"),
        description="Export worklist"
    ))

    # MUTATE: Tag for survey
    registry.register(Action(
        action_id="tag_for_survey",
        label="Tag for Survey",
        variant=ActionVariant.MUTATE,
        domain="shipyard",
        entity_types=["equipment", "worklist_item"],
        ui=ActionUI(dropdown_only=True, icon="flag"),
        execution=ActionExecution(handler="tag_for_survey"),
        mutation=ActionMutation(
            requires_signature=False,
            preview_diff=True,
            confirmation_message="Tag for survey"
        ),
        audit=ActionAudit(level=AuditLevel.BASIC),
        description="Tag item for class/flag survey"
    ))

    # -------------------------------------------------------------------------
    # FLEET DOMAIN (All New)
    # -------------------------------------------------------------------------

    # READ: View fleet summary
    registry.register(Action(
        action_id="view_fleet_summary",
        label="View Fleet",
        variant=ActionVariant.READ,
        domain="fleet",
        entity_types=["fleet", "yacht"],
        ui=ActionUI(primary=True, icon="anchor"),
        execution=ActionExecution(handler="view_fleet_summary"),
        description="View fleet summary"
    ))

    # READ: Open vessel
    registry.register(Action(
        action_id="open_vessel",
        label="Open Vessel",
        variant=ActionVariant.READ,
        domain="fleet",
        entity_types=["yacht", "fleet"],
        ui=ActionUI(icon="ship"),
        execution=ActionExecution(handler="open_vessel"),
        description="Open vessel details"
    ))

    # READ: Export fleet summary
    registry.register(Action(
        action_id="export_fleet_summary",
        label="Export Summary",
        variant=ActionVariant.READ,
        domain="fleet",
        entity_types=["fleet"],
        ui=ActionUI(icon="download"),
        execution=ActionExecution(handler="export_fleet_summary"),
        description="Export fleet summary"
    ))

    # -------------------------------------------------------------------------
    # PREDICTIVE DOMAIN (All New)
    # -------------------------------------------------------------------------

    # READ: Request predictive insight
    registry.register(Action(
        action_id="request_predictive_insight",
        label="Predictive Insight",
        variant=ActionVariant.READ,
        domain="predictive",
        entity_types=["equipment", "predictive"],
        ui=ActionUI(primary=True, icon="trending-up"),
        execution=ActionExecution(handler="request_predictive_insight"),
        description="Request predictive insight"
    ))

    # READ: View smart summary
    registry.register(Action(
        action_id="view_smart_summary",
        label="View Summary",
        variant=ActionVariant.READ,
        domain="predictive",
        entity_types=["equipment", "predictive", "handover"],
        ui=ActionUI(icon="brain"),
        execution=ActionExecution(handler="view_smart_summary"),
        description="View AI-generated smart summary"
    ))

    # -------------------------------------------------------------------------
    # MOBILE DOMAIN (All New)
    # -------------------------------------------------------------------------

    # READ: View attachments/media
    registry.register(Action(
        action_id="view_attachments",
        label="View Attachments",
        variant=ActionVariant.READ,
        domain="mobile",
        entity_types=["work_order", "fault", "equipment", "checklist_item"],
        ui=ActionUI(primary=True, icon="image"),
        execution=ActionExecution(handler="view_attachments"),
        description="View photos and attachments"
    ))

    # MUTATE: Upload photo
    registry.register(Action(
        action_id="upload_photo",
        label="Upload Photo",
        variant=ActionVariant.MUTATE,
        domain="mobile",
        entity_types=["work_order", "fault", "equipment", "checklist_item"],
        ui=ActionUI(dropdown_only=True, icon="camera"),
        execution=ActionExecution(handler="upload_photo"),
        mutation=ActionMutation(
            requires_signature=False,
            preview_diff=False,
            confirmation_message="Upload photo"
        ),
        audit=ActionAudit(level=AuditLevel.BASIC),
        description="Upload photo from mobile"
    ))

    # MUTATE: Record voice note
    registry.register(Action(
        action_id="record_voice_note",
        label="Voice Note",
        variant=ActionVariant.MUTATE,
        domain="mobile",
        entity_types=["work_order", "fault", "equipment", "handover"],
        ui=ActionUI(dropdown_only=True, icon="mic"),
        execution=ActionExecution(handler="record_voice_note"),
        mutation=ActionMutation(
            requires_signature=False,
            preview_diff=False,
            confirmation_message="Save voice note"
        ),
        audit=ActionAudit(level=AuditLevel.BASIC),
        description="Record voice note"
    ))

    # Validate registry
    errors = registry.validate()
    if errors:
        logger.warning(f"Registry validation warnings: {errors}")

    return registry


# Singleton registry
_registry: Optional[ActionRegistry] = None


def get_registry() -> ActionRegistry:
    """Get the singleton action registry"""
    global _registry
    if _registry is None:
        _registry = _create_default_registry()
        logger.info(f"Action registry initialized with {len(_registry._actions)} actions")
    return _registry


def get_action(action_id: str) -> Optional[Action]:
    """Convenience function to get an action"""
    return get_registry().get_action(action_id)


def is_mutate_action(action_id: str) -> bool:
    """Check if action is MUTATE"""
    return get_registry().is_mutate(action_id)


def is_read_action(action_id: str) -> bool:
    """Check if action is READ"""
    return get_registry().is_read(action_id)


# =============================================================================
# MODULE TEST
# =============================================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    registry = get_registry()

    print("=" * 60)
    print("ACTION REGISTRY")
    print("=" * 60)

    print("\n--- All Actions ---")
    for action_id, action in registry._actions.items():
        print(f"  {action_id}: {action.variant.value} ({action.domain})")
        if action.ui.primary:
            print(f"    ^ PRIMARY")
        if action.mutation:
            print(f"    requires_signature={action.mutation.requires_signature}")

    print("\n--- Actions by Entity Type ---")
    for entity_type in registry._by_entity_type:
        actions = registry.get_actions_for_entity(entity_type)
        primary = registry.get_primary_action(entity_type)
        dropdown = registry.get_dropdown_actions(entity_type)
        print(f"\n  {entity_type}:")
        print(f"    Primary: {primary.action_id if primary else 'None'}")
        print(f"    Dropdown: {[a.action_id for a in dropdown]}")

    print("\n--- Validation ---")
    errors = registry.validate()
    if errors:
        print(f"  Errors: {errors}")
    else:
        print("  OK - No errors")
