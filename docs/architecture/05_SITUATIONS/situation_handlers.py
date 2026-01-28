"""
Situation State Machine Handlers
================================

Situations are contextual state machines that track entity lifecycles
and available actions based on current state.

Situations:
- S1: fault_situation - Fault lifecycle from report to resolution
- S2: work_order_situation - Work order from creation to completion
- S3: equipment_situation - Equipment operational status
- S4: part_situation - Part inventory lifecycle
- S5: document_situation - Document lifecycle
- S6: handover_situation - Handover note lifecycle
- S7: purchase_situation - Purchase order workflow
- S8: receiving_situation - Receiving/delivery workflow
- S9: compliance_situation - Compliance tracking state

Each situation provides:
- Current state
- Available transitions
- Allowed actions based on state
- Context for AI assistant
"""

from datetime import datetime, timezone, timedelta
from typing import Dict, Optional, List, Any
from enum import Enum
import logging

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

logger = logging.getLogger(__name__)


# =============================================================================
# S1: Fault Situation
# =============================================================================

class FaultState(str, Enum):
    REPORTED = "reported"
    INVESTIGATING = "investigating"
    DIAGNOSED = "diagnosed"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"
    DEFERRED = "deferred"


FAULT_TRANSITIONS = {
    FaultState.REPORTED: [FaultState.INVESTIGATING, FaultState.DIAGNOSED, FaultState.DEFERRED],
    FaultState.INVESTIGATING: [FaultState.DIAGNOSED, FaultState.DEFERRED],
    FaultState.DIAGNOSED: [FaultState.IN_PROGRESS, FaultState.DEFERRED],
    FaultState.IN_PROGRESS: [FaultState.RESOLVED, FaultState.DIAGNOSED],
    FaultState.RESOLVED: [FaultState.CLOSED, FaultState.IN_PROGRESS],
    FaultState.CLOSED: [],
    FaultState.DEFERRED: [FaultState.INVESTIGATING, FaultState.CLOSED]
}

FAULT_ACTIONS = {
    FaultState.REPORTED: [
        "view_fault_history", "add_fault_note", "add_fault_photo",
        "diagnose_fault", "create_work_order_from_fault", "suggest_parts"
    ],
    FaultState.INVESTIGATING: [
        "view_fault_history", "add_fault_note", "add_fault_photo",
        "diagnose_fault", "create_work_order_from_fault", "show_manual_section"
    ],
    FaultState.DIAGNOSED: [
        "view_fault_history", "add_fault_note", "add_fault_photo",
        "create_work_order_from_fault", "suggest_parts", "order_part"
    ],
    FaultState.IN_PROGRESS: [
        "view_fault_history", "add_fault_note", "add_fault_photo",
        "view_work_order_history"
    ],
    FaultState.RESOLVED: [
        "view_fault_history", "add_fault_note"
    ],
    FaultState.CLOSED: [
        "view_fault_history"
    ],
    FaultState.DEFERRED: [
        "view_fault_history", "add_fault_note"
    ]
}


class FaultSituation:
    """S1: Fault lifecycle state machine."""

    def __init__(self, supabase_client):
        self.db = supabase_client

    async def get_situation(
        self,
        fault_id: str,
        yacht_id: str
    ) -> Dict:
        """Get current fault situation context."""
        try:
            # Get fault details
            result = self.db.table("pms_faults").select(
                "id, fault_code, title, description, severity, status, "
                "equipment_id, detected_at, resolved_at, resolved_by, "
                "work_order_id, metadata"
            ).eq("id", fault_id).eq("yacht_id", yacht_id).limit(1).execute()

            if not result.data:
                return {
                    "status": "error",
                    "error_code": "FAULT_NOT_FOUND",
                    "message": f"Fault not found: {fault_id}"
                }

            fault = result.data[0]
            current_state = fault.get("status", "reported")

            # Map DB status to enum
            try:
                state = FaultState(current_state)
            except ValueError:
                state = FaultState.REPORTED

            # Get linked work orders
            wo_result = self.db.table("pms_work_orders").select(
                "id, wo_number, status"
            ).eq("fault_id", fault_id).eq("yacht_id", yacht_id).execute()

            work_orders = wo_result.data if wo_result.data else []

            # Get equipment info if linked
            equipment = None
            if fault.get("equipment_id"):
                eq_result = self.db.table("pms_equipment").select(
                    "id, name, model, criticality"
                ).eq("id", fault["equipment_id"]).limit(1).execute()
                if eq_result.data:
                    equipment = eq_result.data[0]

            return {
                "status": "success",
                "situation": "fault_situation",
                "entity_id": fault_id,
                "current_state": state.value,
                "entity": fault,
                "context": {
                    "equipment": equipment,
                    "work_orders": work_orders,
                    "has_work_order": bool(fault.get("work_order_id")),
                    "is_resolved": bool(fault.get("resolved_at")),
                    "is_critical": fault.get("severity") == "critical"
                },
                "available_transitions": [t.value for t in FAULT_TRANSITIONS.get(state, [])],
                "available_actions": FAULT_ACTIONS.get(state, []),
                "guards": self._get_guards(fault, state)
            }

        except Exception as e:
            logger.error(f"FaultSituation.get_situation failed: {e}", exc_info=True)
            return {
                "status": "error",
                "error_code": "INTERNAL_ERROR",
                "message": str(e)
            }

    def _get_guards(self, fault: Dict, state: FaultState) -> Dict:
        """Get guard conditions for current state."""
        guards = {
            "can_create_work_order": state in (
                FaultState.REPORTED, FaultState.INVESTIGATING, FaultState.DIAGNOSED
            ),
            "can_diagnose": state in (
                FaultState.REPORTED, FaultState.INVESTIGATING
            ),
            "can_resolve": state == FaultState.IN_PROGRESS,
            "requires_work_order_for_resolution": fault.get("severity") == "critical",
            "can_close": state == FaultState.RESOLVED
        }
        return guards


# =============================================================================
# S2: Work Order Situation
# =============================================================================

class WorkOrderState(str, Enum):
    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    ON_HOLD = "on_hold"
    COMPLETED = "completed"
    VERIFIED = "verified"
    CLOSED = "closed"
    CANCELLED = "cancelled"


WORK_ORDER_TRANSITIONS = {
    WorkOrderState.PLANNED: [WorkOrderState.IN_PROGRESS, WorkOrderState.CANCELLED],
    WorkOrderState.IN_PROGRESS: [WorkOrderState.COMPLETED, WorkOrderState.ON_HOLD, WorkOrderState.CANCELLED],
    WorkOrderState.ON_HOLD: [WorkOrderState.IN_PROGRESS, WorkOrderState.CANCELLED],
    WorkOrderState.COMPLETED: [WorkOrderState.VERIFIED, WorkOrderState.IN_PROGRESS],
    WorkOrderState.VERIFIED: [WorkOrderState.CLOSED],
    WorkOrderState.CLOSED: [],
    WorkOrderState.CANCELLED: []
}

WORK_ORDER_ACTIONS = {
    WorkOrderState.PLANNED: [
        "view_work_order_history", "add_work_order_note", "add_work_order_photo",
        "assign_work_order", "add_part_to_work_order", "view_work_order_checklist"
    ],
    WorkOrderState.IN_PROGRESS: [
        "view_work_order_history", "add_work_order_note", "add_work_order_photo",
        "add_part_to_work_order", "log_part_usage", "update_worklist_progress",
        "view_work_order_checklist", "mark_checklist_item_complete", "mark_work_order_complete"
    ],
    WorkOrderState.ON_HOLD: [
        "view_work_order_history", "add_work_order_note", "order_part"
    ],
    WorkOrderState.COMPLETED: [
        "view_work_order_history", "add_work_order_note", "add_work_order_photo"
    ],
    WorkOrderState.VERIFIED: [
        "view_work_order_history", "add_work_order_note"
    ],
    WorkOrderState.CLOSED: [
        "view_work_order_history"
    ],
    WorkOrderState.CANCELLED: [
        "view_work_order_history"
    ]
}


class WorkOrderSituation:
    """S2: Work order lifecycle state machine."""

    def __init__(self, supabase_client):
        self.db = supabase_client

    async def get_situation(
        self,
        work_order_id: str,
        yacht_id: str
    ) -> Dict:
        """Get current work order situation context."""
        try:
            result = self.db.table("pms_work_orders").select(
                "id, wo_number, title, description, type, work_order_type, "
                "priority, status, equipment_id, fault_id, assigned_to, "
                "due_date, completed_at, completed_by, metadata"
            ).eq("id", work_order_id).eq("yacht_id", yacht_id).limit(1).execute()

            if not result.data:
                return {
                    "status": "error",
                    "error_code": "WO_NOT_FOUND",
                    "message": f"Work order not found: {work_order_id}"
                }

            wo = result.data[0]
            current_state = wo.get("status", "planned")

            try:
                state = WorkOrderState(current_state)
            except ValueError:
                state = WorkOrderState.PLANNED

            # Get parts used
            parts_result = self.db.table("pms_work_order_parts").select(
                "id, part_id, quantity"
            ).eq("work_order_id", work_order_id).execute()

            parts = parts_result.data if parts_result.data else []

            # Get checklist progress from work order metadata
            wo_metadata = wo.get("metadata") or {}
            checklist = wo_metadata.get("checklist") or []
            checklist_completed = sum(1 for c in checklist if c.get("is_completed"))

            # Get linked fault if any
            fault = None
            if wo.get("fault_id"):
                fault_result = self.db.table("pms_faults").select(
                    "id, fault_code, severity, status"
                ).eq("id", wo["fault_id"]).limit(1).execute()
                if fault_result.data:
                    fault = fault_result.data[0]

            return {
                "status": "success",
                "situation": "work_order_situation",
                "entity_id": work_order_id,
                "current_state": state.value,
                "entity": wo,
                "context": {
                    "fault": fault,
                    "parts_count": len(parts),
                    "checklist_total": len(checklist),
                    "checklist_completed": checklist_completed,
                    "is_overdue": wo.get("due_date") and wo["due_date"] < datetime.now(timezone.utc).date().isoformat(),
                    "is_critical": wo.get("priority") in ("critical", "emergency")
                },
                "available_transitions": [t.value for t in WORK_ORDER_TRANSITIONS.get(state, [])],
                "available_actions": WORK_ORDER_ACTIONS.get(state, []),
                "guards": self._get_guards(wo, state, checklist, checklist_completed)
            }

        except Exception as e:
            logger.error(f"WorkOrderSituation.get_situation failed: {e}", exc_info=True)
            return {
                "status": "error",
                "error_code": "INTERNAL_ERROR",
                "message": str(e)
            }

    def _get_guards(self, wo: Dict, state: WorkOrderState, checklist: List, completed: int) -> Dict:
        """Get guard conditions for current state."""
        guards = {
            "can_start": state == WorkOrderState.PLANNED,
            "can_complete": state == WorkOrderState.IN_PROGRESS,
            "checklist_required": len(checklist) > 0,
            "checklist_complete": completed == len(checklist) if checklist else True,
            "requires_verification": wo.get("priority") in ("critical", "emergency"),
            "can_add_parts": state in (WorkOrderState.PLANNED, WorkOrderState.IN_PROGRESS)
        }
        return guards


# =============================================================================
# S3: Equipment Situation
# =============================================================================

class EquipmentState(str, Enum):
    OPERATIONAL = "operational"
    DEGRADED = "degraded"
    FAILED = "failed"
    MAINTENANCE = "maintenance"
    DECOMMISSIONED = "decommissioned"


EQUIPMENT_ACTIONS = {
    EquipmentState.OPERATIONAL: [
        "view_equipment_details", "view_equipment_history", "view_equipment_parts",
        "add_equipment_note", "view_equipment_manual", "request_predictive_insight"
    ],
    EquipmentState.DEGRADED: [
        "view_equipment_details", "view_equipment_history", "view_linked_faults",
        "add_equipment_note", "create_work_order", "suggest_parts"
    ],
    EquipmentState.FAILED: [
        "view_equipment_details", "view_linked_faults", "add_equipment_note",
        "create_work_order", "order_part", "show_manual_section"
    ],
    EquipmentState.MAINTENANCE: [
        "view_equipment_details", "view_work_order_history", "add_equipment_note",
        "view_equipment_parts", "log_part_usage"
    ],
    EquipmentState.DECOMMISSIONED: [
        "view_equipment_details", "view_equipment_history"
    ]
}


class EquipmentSituation:
    """S3: Equipment operational state machine."""

    def __init__(self, supabase_client):
        self.db = supabase_client

    async def get_situation(
        self,
        equipment_id: str,
        yacht_id: str
    ) -> Dict:
        """Get current equipment situation context."""
        try:
            result = self.db.table("pms_equipment").select(
                "id, name, model, manufacturer, serial_number, system_type, "
                "location, criticality, metadata"
            ).eq("id", equipment_id).eq("yacht_id", yacht_id).limit(1).execute()

            if not result.data:
                return {
                    "status": "error",
                    "error_code": "EQUIPMENT_NOT_FOUND",
                    "message": f"Equipment not found: {equipment_id}"
                }

            equipment = result.data[0]
            # Derive state from metadata or default to operational
            metadata = equipment.get("metadata") or {}
            current_state = metadata.get("status", "operational")

            try:
                state = EquipmentState(current_state)
            except ValueError:
                state = EquipmentState.OPERATIONAL

            # Get active faults
            faults_result = self.db.table("pms_faults").select(
                "id, fault_code, severity, status"
            ).eq("equipment_id", equipment_id).eq("yacht_id", yacht_id).in_(
                "status", ["open", "investigating", "in_progress"]
            ).execute()

            faults = faults_result.data if faults_result.data else []
            critical_faults = [f for f in faults if f.get("severity") == "critical"]

            # Get pending work orders
            wos_result = self.db.table("pms_work_orders").select(
                "id, wo_number, status, priority"
            ).eq("equipment_id", equipment_id).eq("yacht_id", yacht_id).in_(
                "status", ["planned", "in_progress"]
            ).execute()

            work_orders = wos_result.data if wos_result.data else []

            # Check maintenance status from metadata
            maintenance_due = False
            eq_metadata = equipment.get("metadata") or {}
            if eq_metadata.get("next_service_date"):
                next_service = eq_metadata["next_service_date"]
                maintenance_due = next_service <= datetime.now(timezone.utc).date().isoformat()

            return {
                "status": "success",
                "situation": "equipment_situation",
                "entity_id": equipment_id,
                "current_state": state.value,
                "entity": equipment,
                "context": {
                    "active_faults": len(faults),
                    "critical_faults": len(critical_faults),
                    "pending_work_orders": len(work_orders),
                    "maintenance_due": maintenance_due,
                    "is_critical": equipment.get("criticality") == "critical"
                },
                "available_actions": EQUIPMENT_ACTIONS.get(state, []),
                "guards": self._get_guards(equipment, state, faults, work_orders)
            }

        except Exception as e:
            logger.error(f"EquipmentSituation.get_situation failed: {e}", exc_info=True)
            return {
                "status": "error",
                "error_code": "INTERNAL_ERROR",
                "message": str(e)
            }

    def _get_guards(self, equipment: Dict, state: EquipmentState, faults: List, work_orders: List) -> Dict:
        """Get guard conditions for current state."""
        guards = {
            "can_operate": state == EquipmentState.OPERATIONAL,
            "has_active_faults": len(faults) > 0,
            "has_critical_faults": any(f.get("severity") == "critical" for f in faults),
            "maintenance_in_progress": any(wo.get("status") == "in_progress" for wo in work_orders),
            "requires_immediate_attention": state == EquipmentState.FAILED and equipment.get("criticality") == "critical"
        }
        return guards


# =============================================================================
# S4: Part Situation
# =============================================================================

class PartState(str, Enum):
    ADEQUATE = "adequate"
    LOW_STOCK = "low_stock"
    REORDER_REQUIRED = "reorder_required"
    OUT_OF_STOCK = "out_of_stock"
    ON_ORDER = "on_order"


PART_ACTIONS = {
    PartState.ADEQUATE: [
        "view_part_stock", "view_part_location", "view_part_usage",
        "view_linked_equipment", "log_part_usage"
    ],
    PartState.LOW_STOCK: [
        "view_part_stock", "view_part_location", "view_part_usage",
        "view_linked_equipment", "order_part", "create_purchase_request"
    ],
    PartState.REORDER_REQUIRED: [
        "view_part_stock", "view_part_usage", "order_part",
        "create_purchase_request"
    ],
    PartState.OUT_OF_STOCK: [
        "view_part_stock", "view_part_usage", "order_part",
        "create_purchase_request", "track_delivery"
    ],
    PartState.ON_ORDER: [
        "view_part_stock", "track_delivery", "log_delivery_received"
    ]
}


class PartSituation:
    """S4: Part inventory state machine."""

    def __init__(self, supabase_client):
        self.db = supabase_client

    async def get_situation(
        self,
        part_id: str,
        yacht_id: str
    ) -> Dict:
        """Get current part situation context."""
        try:
            result = self.db.table("pms_parts").select(
                "id, name, part_number, manufacturer, category, "
                "quantity_on_hand, minimum_quantity, "
                "unit, location, metadata"
            ).eq("id", part_id).eq("yacht_id", yacht_id).limit(1).execute()

            if not result.data:
                return {
                    "status": "error",
                    "error_code": "PART_NOT_FOUND",
                    "message": f"Part not found: {part_id}"
                }

            part = result.data[0]

            # Determine state based on quantity
            qty = part.get("quantity_on_hand", 0) or 0
            min_qty = part.get("minimum_quantity", 0) or 0
            part_metadata = part.get("metadata") or {}
            reorder = part_metadata.get("reorder_point", min_qty) or min_qty

            # Check if on order
            po_result = self.db.table("pms_purchase_order_items").select(
                "id, purchase_order_id"
            ).eq("part_id", part_id).execute()

            on_order = False
            if po_result.data:
                # Check if any PO is pending
                for item in po_result.data:
                    po_check = self.db.table("pms_purchase_orders").select(
                        "status"
                    ).eq("id", item["purchase_order_id"]).in_(
                        "status", ["requested", "approved", "ordered"]
                    ).limit(1).execute()
                    if po_check.data:
                        on_order = True
                        break

            if on_order and qty <= 0:
                state = PartState.ON_ORDER
            elif qty <= 0:
                state = PartState.OUT_OF_STOCK
            elif qty <= reorder:
                state = PartState.REORDER_REQUIRED
            elif qty <= min_qty:
                state = PartState.LOW_STOCK
            else:
                state = PartState.ADEQUATE

            # Get linked equipment count
            eq_result = self.db.table("pms_equipment_parts_bom").select(
                "equipment_id"
            ).eq("part_id", part_id).execute()

            linked_equipment = len(eq_result.data) if eq_result.data else 0

            return {
                "status": "success",
                "situation": "part_situation",
                "entity_id": part_id,
                "current_state": state.value,
                "entity": part,
                "context": {
                    "quantity_on_hand": qty,
                    "minimum_quantity": min_qty,
                    "reorder_point": reorder,
                    "on_order": on_order,
                    "linked_equipment_count": linked_equipment
                },
                "available_actions": PART_ACTIONS.get(state, []),
                "guards": self._get_guards(part, state, on_order)
            }

        except Exception as e:
            logger.error(f"PartSituation.get_situation failed: {e}", exc_info=True)
            return {
                "status": "error",
                "error_code": "INTERNAL_ERROR",
                "message": str(e)
            }

    def _get_guards(self, part: Dict, state: PartState, on_order: bool) -> Dict:
        """Get guard conditions for current state."""
        part_metadata = part.get("metadata") or {}
        guards = {
            "can_use": state != PartState.OUT_OF_STOCK,
            "should_reorder": state in (PartState.LOW_STOCK, PartState.REORDER_REQUIRED, PartState.OUT_OF_STOCK),
            "on_order": on_order,
            "has_supplier": bool(part_metadata.get("preferred_supplier"))
        }
        return guards


# =============================================================================
# S5: Document Situation
# =============================================================================

class DocumentState(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    UNDER_REVIEW = "under_review"
    SUPERSEDED = "superseded"
    ARCHIVED = "archived"


DOCUMENT_ACTIONS = {
    DocumentState.DRAFT: [
        "view_document", "view_document_section"
    ],
    DocumentState.ACTIVE: [
        "view_document", "view_document_section", "view_related_documents",
        "show_manual_section"
    ],
    DocumentState.UNDER_REVIEW: [
        "view_document", "view_document_section", "view_related_documents"
    ],
    DocumentState.SUPERSEDED: [
        "view_document", "view_related_documents"
    ],
    DocumentState.ARCHIVED: [
        "view_document"
    ]
}


class DocumentSituation:
    """S5: Document lifecycle state machine."""

    def __init__(self, supabase_client):
        self.db = supabase_client

    async def get_situation(
        self,
        document_id: str,
        yacht_id: str
    ) -> Dict:
        """Get current document situation context."""
        try:
            result = self.db.table("documents").select(
                "id, filename, storage_path, doc_type, "
                "tags, metadata"
            ).eq("id", document_id).eq("yacht_id", yacht_id).limit(1).execute()

            if not result.data:
                return {
                    "status": "error",
                    "error_code": "DOCUMENT_NOT_FOUND",
                    "message": f"Document not found: {document_id}"
                }

            document = result.data[0]
            doc_metadata = document.get("metadata") or {}
            current_state = doc_metadata.get("status", "active")

            try:
                state = DocumentState(current_state)
            except ValueError:
                state = DocumentState.ACTIVE

            # Check for related documents
            related_result = self.db.table("documents").select(
                "id"
            ).eq("yacht_id", yacht_id).eq(
                "doc_type", document.get("doc_type")
            ).neq("id", document_id).limit(10).execute()

            related_count = len(related_result.data) if related_result.data else 0

            return {
                "status": "success",
                "situation": "document_situation",
                "entity_id": document_id,
                "current_state": state.value,
                "entity": document,
                "context": {
                    "doc_type": document.get("doc_type"),
                    "version": doc_metadata.get("version"),
                    "page_count": doc_metadata.get("pages"),
                    "section_count": len(doc_metadata.get("sections") or []),
                    "related_documents": related_count
                },
                "available_actions": DOCUMENT_ACTIONS.get(state, []),
                "guards": self._get_guards(document, state)
            }

        except Exception as e:
            logger.error(f"DocumentSituation.get_situation failed: {e}", exc_info=True)
            return {
                "status": "error",
                "error_code": "INTERNAL_ERROR",
                "message": str(e)
            }

    def _get_guards(self, document: Dict, state: DocumentState) -> Dict:
        """Get guard conditions for current state."""
        doc_metadata = document.get("metadata") or {}
        guards = {
            "is_current_version": state == DocumentState.ACTIVE,
            "has_sections": len(doc_metadata.get("sections") or []) > 0,
            "is_manual": document.get("doc_type") in ("manual", "technical")
        }
        return guards


# =============================================================================
# S6: Handover Situation
# =============================================================================

class HandoverState(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    ARCHIVED = "archived"


HANDOVER_ACTIONS = {
    HandoverState.DRAFT: [
        "edit_handover_section", "add_document_to_handover",
        "add_predictive_insight_to_handover", "regenerate_handover_summary"
    ],
    HandoverState.ACTIVE: [
        "edit_handover_section", "add_document_to_handover",
        "add_predictive_insight_to_handover", "export_handover"
    ],
    HandoverState.ACKNOWLEDGED: [
        "export_handover"
    ],
    HandoverState.ARCHIVED: [
        "export_handover"
    ]
}


class HandoverSituation:
    """S6: Handover note lifecycle state machine."""

    def __init__(self, supabase_client):
        self.db = supabase_client

    async def get_situation(
        self,
        handover_id: str,
        yacht_id: str
    ) -> Dict:
        """Get current handover situation context."""
        try:
            result = self.db.table("pms_handover").select(
                "id, summary_text, category, priority, entity_type, entity_id, "
                "added_by, added_at, metadata"
            ).eq("id", handover_id).eq("yacht_id", yacht_id).limit(1).execute()

            if not result.data:
                return {
                    "status": "error",
                    "error_code": "HANDOVER_NOT_FOUND",
                    "message": f"Handover not found: {handover_id}"
                }

            handover = result.data[0]
            metadata = handover.get("metadata") or {}
            current_state = metadata.get("status", "active")

            try:
                state = HandoverState(current_state)
            except ValueError:
                state = HandoverState.ACTIVE

            # Count documents and insights
            documents = metadata.get("documents") or []
            insights = metadata.get("predictive_insights") or []

            return {
                "status": "success",
                "situation": "handover_situation",
                "entity_id": handover_id,
                "current_state": state.value,
                "entity": handover,
                "context": {
                    "category": handover.get("category"),
                    "priority": handover.get("priority"),
                    "documents_count": len(documents),
                    "insights_count": len(insights),
                    "has_linked_entity": bool(handover.get("entity_id"))
                },
                "available_actions": HANDOVER_ACTIONS.get(state, []),
                "guards": self._get_guards(handover, state)
            }

        except Exception as e:
            logger.error(f"HandoverSituation.get_situation failed: {e}", exc_info=True)
            return {
                "status": "error",
                "error_code": "INTERNAL_ERROR",
                "message": str(e)
            }

    def _get_guards(self, handover: Dict, state: HandoverState) -> Dict:
        """Get guard conditions for current state."""
        guards = {
            "can_edit": state in (HandoverState.DRAFT, HandoverState.ACTIVE),
            "is_urgent": handover.get("category") == "urgent",
            "can_export": state != HandoverState.DRAFT
        }
        return guards


# =============================================================================
# S7: Purchase Situation
# =============================================================================

class PurchaseState(str, Enum):
    DRAFT = "draft"
    REQUESTED = "requested"
    APPROVED = "approved"
    ORDERED = "ordered"
    PARTIALLY_RECEIVED = "partially_received"
    RECEIVED = "received"
    CANCELLED = "cancelled"


PURCHASE_TRANSITIONS = {
    PurchaseState.DRAFT: [PurchaseState.REQUESTED, PurchaseState.CANCELLED],
    PurchaseState.REQUESTED: [PurchaseState.APPROVED, PurchaseState.CANCELLED],
    PurchaseState.APPROVED: [PurchaseState.ORDERED, PurchaseState.CANCELLED],
    PurchaseState.ORDERED: [PurchaseState.PARTIALLY_RECEIVED, PurchaseState.RECEIVED, PurchaseState.CANCELLED],
    PurchaseState.PARTIALLY_RECEIVED: [PurchaseState.RECEIVED, PurchaseState.CANCELLED],
    PurchaseState.RECEIVED: [],
    PurchaseState.CANCELLED: []
}

PURCHASE_ACTIONS = {
    PurchaseState.DRAFT: [
        "add_item_to_purchase", "update_purchase_status"
    ],
    PurchaseState.REQUESTED: [
        "add_item_to_purchase", "approve_purchase", "update_purchase_status"
    ],
    PurchaseState.APPROVED: [
        "update_purchase_status", "upload_invoice"
    ],
    PurchaseState.ORDERED: [
        "track_delivery", "upload_invoice", "log_delivery_received",
        "update_purchase_status"
    ],
    PurchaseState.PARTIALLY_RECEIVED: [
        "track_delivery", "log_delivery_received", "upload_invoice",
        "update_purchase_status"
    ],
    PurchaseState.RECEIVED: [
        "track_delivery", "upload_invoice"
    ],
    PurchaseState.CANCELLED: []
}


class PurchaseSituation:
    """S7: Purchase order workflow state machine."""

    def __init__(self, supabase_client):
        self.db = supabase_client

    async def get_situation(
        self,
        purchase_order_id: str,
        yacht_id: str
    ) -> Dict:
        """Get current purchase order situation context."""
        try:
            result = self.db.table("pms_purchase_orders").select(
                "id, po_number, status, supplier_id, ordered_at, "
                "received_at, currency, metadata"
            ).eq("id", purchase_order_id).eq("yacht_id", yacht_id).limit(1).execute()

            if not result.data:
                return {
                    "status": "error",
                    "error_code": "PO_NOT_FOUND",
                    "message": f"Purchase order not found: {purchase_order_id}"
                }

            po = result.data[0]
            current_state = po.get("status", "draft")

            try:
                state = PurchaseState(current_state)
            except ValueError:
                state = PurchaseState.DRAFT

            # Get line items
            items_result = self.db.table("pms_purchase_order_items").select(
                "id, quantity_ordered, quantity_received, unit_price"
            ).eq("purchase_order_id", purchase_order_id).execute()

            items = items_result.data if items_result.data else []
            total_ordered = sum(i.get("quantity_ordered", 0) for i in items)
            total_received = sum(i.get("quantity_received", 0) for i in items)
            total_value = sum(
                (i.get("quantity_ordered", 0) * (i.get("unit_price") or 0))
                for i in items
            )

            return {
                "status": "success",
                "situation": "purchase_situation",
                "entity_id": purchase_order_id,
                "current_state": state.value,
                "entity": po,
                "context": {
                    "line_items_count": len(items),
                    "total_ordered": total_ordered,
                    "total_received": total_received,
                    "receive_percent": round(total_received / total_ordered * 100, 1) if total_ordered > 0 else 0,
                    "total_value": total_value,
                    "currency": po.get("currency", "USD")
                },
                "available_transitions": [t.value for t in PURCHASE_TRANSITIONS.get(state, [])],
                "available_actions": PURCHASE_ACTIONS.get(state, []),
                "guards": self._get_guards(po, state, items)
            }

        except Exception as e:
            logger.error(f"PurchaseSituation.get_situation failed: {e}", exc_info=True)
            return {
                "status": "error",
                "error_code": "INTERNAL_ERROR",
                "message": str(e)
            }

    def _get_guards(self, po: Dict, state: PurchaseState, items: List) -> Dict:
        """Get guard conditions for current state."""
        guards = {
            "can_add_items": state in (PurchaseState.DRAFT, PurchaseState.REQUESTED),
            "can_approve": state == PurchaseState.REQUESTED,
            "can_receive": state in (PurchaseState.ORDERED, PurchaseState.PARTIALLY_RECEIVED),
            "has_items": len(items) > 0,
            "requires_approval": True  # All POs require approval
        }
        return guards


# =============================================================================
# S8: Receiving Situation
# =============================================================================

class ReceivingState(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    INSPECTING = "inspecting"
    COMPLETED = "completed"
    DISPUTED = "disputed"


RECEIVING_ACTIONS = {
    ReceivingState.PENDING: [
        "track_delivery"
    ],
    ReceivingState.IN_PROGRESS: [
        "log_delivery_received", "upload_photo"
    ],
    ReceivingState.INSPECTING: [
        "add_work_order_note", "upload_photo"
    ],
    ReceivingState.COMPLETED: [
        "track_delivery"
    ],
    ReceivingState.DISPUTED: [
        "add_work_order_note", "upload_photo"
    ]
}


class ReceivingSituation:
    """S8: Receiving/delivery workflow state machine."""

    def __init__(self, supabase_client):
        self.db = supabase_client

    async def get_situation(
        self,
        receiving_id: str,
        yacht_id: str
    ) -> Dict:
        """Get current receiving situation context."""
        try:
            result = self.db.table("pms_receiving_events").select(
                "id, receiving_number, order_id, received_at, received_by, "
                "location, delivery_method, tracking_number, status, metadata"
            ).eq("id", receiving_id).eq("yacht_id", yacht_id).limit(1).execute()

            if not result.data:
                return {
                    "status": "error",
                    "error_code": "RECEIVING_NOT_FOUND",
                    "message": f"Receiving event not found: {receiving_id}"
                }

            receiving = result.data[0]
            current_state = receiving.get("status", "pending")

            try:
                state = ReceivingState(current_state)
            except ValueError:
                state = ReceivingState.PENDING

            # Get linked PO if any
            po = None
            if receiving.get("order_id"):
                po_result = self.db.table("pms_purchase_orders").select(
                    "id, po_number, status"
                ).eq("id", receiving["order_id"]).limit(1).execute()
                if po_result.data:
                    po = po_result.data[0]

            return {
                "status": "success",
                "situation": "receiving_situation",
                "entity_id": receiving_id,
                "current_state": state.value,
                "entity": receiving,
                "context": {
                    "purchase_order": po,
                    "delivery_method": receiving.get("delivery_method"),
                    "tracking_number": receiving.get("tracking_number"),
                    "location": receiving.get("location")
                },
                "available_actions": RECEIVING_ACTIONS.get(state, []),
                "guards": self._get_guards(receiving, state)
            }

        except Exception as e:
            logger.error(f"ReceivingSituation.get_situation failed: {e}", exc_info=True)
            return {
                "status": "error",
                "error_code": "INTERNAL_ERROR",
                "message": str(e)
            }

    def _get_guards(self, receiving: Dict, state: ReceivingState) -> Dict:
        """Get guard conditions for current state."""
        guards = {
            "can_receive": state in (ReceivingState.PENDING, ReceivingState.IN_PROGRESS),
            "requires_inspection": False,  # Could be based on item type
            "has_tracking": bool(receiving.get("tracking_number"))
        }
        return guards


# =============================================================================
# S9: Compliance Situation
# =============================================================================

class ComplianceState(str, Enum):
    COMPLIANT = "compliant"
    WARNING = "warning"
    NON_COMPLIANT = "non_compliant"
    EXCEPTION = "exception"


COMPLIANCE_ACTIONS = {
    ComplianceState.COMPLIANT: [
        "view_compliance_status", "view_hours_of_rest", "export_hours_of_rest"
    ],
    ComplianceState.WARNING: [
        "view_compliance_status", "view_hours_of_rest", "update_hours_of_rest"
    ],
    ComplianceState.NON_COMPLIANT: [
        "view_compliance_status", "view_hours_of_rest", "update_hours_of_rest"
    ],
    ComplianceState.EXCEPTION: [
        "view_compliance_status", "view_hours_of_rest", "export_hours_of_rest"
    ]
}


class ComplianceSituation:
    """S9: Compliance tracking state machine."""

    def __init__(self, supabase_client):
        self.db = supabase_client

    async def get_situation(
        self,
        user_id: str,
        yacht_id: str,
        compliance_type: str = "hours_of_rest"
    ) -> Dict:
        """Get current compliance situation context."""
        try:
            # Get last 7 days of HOR records
            cutoff = (datetime.now(timezone.utc) - timedelta(days=7)).date().isoformat()

            result = self.db.table("pms_hours_of_rest").select(
                "id, record_date, total_rest_hours, is_daily_compliant, "
                "is_weekly_compliant, is_compliant, status, has_exception"
            ).eq("user_id", user_id).eq("yacht_id", yacht_id).gte(
                "record_date", cutoff
            ).order("record_date", desc=True).execute()

            records = result.data if result.data else []

            # Determine overall state
            if not records:
                state = ComplianceState.WARNING  # No records = concern
            else:
                non_compliant = [r for r in records if not r.get("is_compliant")]
                has_exception = any(r.get("has_exception") for r in records)

                if has_exception:
                    state = ComplianceState.EXCEPTION
                elif len(non_compliant) > 2:
                    state = ComplianceState.NON_COMPLIANT
                elif len(non_compliant) > 0:
                    state = ComplianceState.WARNING
                else:
                    state = ComplianceState.COMPLIANT

            # Calculate stats
            total_rest_7d = sum(r.get("total_rest_hours", 0) for r in records[:7])
            compliant_days = sum(1 for r in records if r.get("is_compliant"))

            return {
                "status": "success",
                "situation": "compliance_situation",
                "entity_id": user_id,
                "compliance_type": compliance_type,
                "current_state": state.value,
                "context": {
                    "records_count": len(records),
                    "compliant_days": compliant_days,
                    "non_compliant_days": len(records) - compliant_days,
                    "weekly_rest_hours": round(total_rest_7d, 2),
                    "weekly_compliant": total_rest_7d >= 77,
                    "compliance_rate": round(compliant_days / len(records) * 100, 1) if records else 0
                },
                "available_actions": COMPLIANCE_ACTIONS.get(state, []),
                "guards": self._get_guards(state, records)
            }

        except Exception as e:
            logger.error(f"ComplianceSituation.get_situation failed: {e}", exc_info=True)
            return {
                "status": "error",
                "error_code": "INTERNAL_ERROR",
                "message": str(e)
            }

    def _get_guards(self, state: ComplianceState, records: List) -> Dict:
        """Get guard conditions for current state."""
        guards = {
            "is_compliant": state == ComplianceState.COMPLIANT,
            "requires_attention": state in (ComplianceState.WARNING, ComplianceState.NON_COMPLIANT),
            "can_export": len(records) > 0,
            "missing_today": not any(
                r.get("record_date") == datetime.now(timezone.utc).date().isoformat()
                for r in records
            )
        }
        return guards


# =============================================================================
# Situation Manager
# =============================================================================

class SituationManager:
    """
    Central manager for all situation state machines.

    Provides unified interface for getting situation context
    for any entity type.
    """

    def __init__(self, supabase_client):
        self.db = supabase_client
        self.fault = FaultSituation(supabase_client)
        self.work_order = WorkOrderSituation(supabase_client)
        self.equipment = EquipmentSituation(supabase_client)
        self.part = PartSituation(supabase_client)
        self.document = DocumentSituation(supabase_client)
        self.handover = HandoverSituation(supabase_client)
        self.purchase = PurchaseSituation(supabase_client)
        self.receiving = ReceivingSituation(supabase_client)
        self.compliance = ComplianceSituation(supabase_client)

    async def get_situation(
        self,
        situation_type: str,
        entity_id: str,
        yacht_id: str,
        **kwargs
    ) -> Dict:
        """
        Get situation context for any entity type.

        Args:
            situation_type: One of fault, work_order, equipment, part,
                          document, handover, purchase, receiving, compliance
            entity_id: The entity ID
            yacht_id: The yacht ID for isolation
            **kwargs: Additional parameters for specific situations
        """
        situation_map = {
            "fault": self.fault.get_situation,
            "work_order": self.work_order.get_situation,
            "equipment": self.equipment.get_situation,
            "part": self.part.get_situation,
            "document": self.document.get_situation,
            "handover": self.handover.get_situation,
            "purchase": self.purchase.get_situation,
            "receiving": self.receiving.get_situation,
            "compliance": self.compliance.get_situation
        }

        handler = situation_map.get(situation_type)
        if not handler:
            return {
                "status": "error",
                "error_code": "INVALID_SITUATION_TYPE",
                "message": f"Unknown situation type: {situation_type}"
            }

        return await handler(entity_id, yacht_id, **kwargs)


def get_situation_handlers(supabase_client) -> Dict[str, callable]:
    """Get situation handler functions for registration."""
    manager = SituationManager(supabase_client)

    return {
        "get_situation": manager.get_situation,
        "fault_situation": manager.fault.get_situation,
        "work_order_situation": manager.work_order.get_situation,
        "equipment_situation": manager.equipment.get_situation,
        "part_situation": manager.part.get_situation,
        "document_situation": manager.document.get_situation,
        "handover_situation": manager.handover.get_situation,
        "purchase_situation": manager.purchase.get_situation,
        "receiving_situation": manager.receiving.get_situation,
        "compliance_situation": manager.compliance.get_situation
    }
