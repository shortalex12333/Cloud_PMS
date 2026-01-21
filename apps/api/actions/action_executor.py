"""
Action Executor
===============

SQL execution layer for microactions. Maps action_id to database operations.

Architecture:
- READ actions: Execute immediately, return data
- MUTATE actions: Support prepare → sign → commit flow

Tables Used:
- work_orders: Work order management
- parts: Inventory parts
- faults: Fault tracking
- equipment: Equipment registry
- document_chunks: Documentation
- handover_items: Handover notes
- checklists / checklist_items: Task checklists
- purchases: Purchase orders
- hours_of_rest: Crew rest tracking

Usage:
    from action_executor import ActionExecutor

    executor = ActionExecutor(supabase_client)

    # READ action - immediate execution
    result = await executor.execute_read("view_equipment", entity_id, yacht_id)

    # MUTATE action - staged execution
    staged = await executor.prepare_mutation("edit_inventory_quantity", entity_id, yacht_id, payload)
    committed = await executor.commit_mutation(staged['staged_id'], signature)
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any, Callable, Tuple
from datetime import datetime, timedelta, timezone
from enum import Enum
import hashlib
import json
import uuid
import logging

logger = logging.getLogger(__name__)


# =============================================================================
# DATA TYPES
# =============================================================================

class ExecutionResult:
    """Result of action execution"""
    def __init__(
        self,
        success: bool,
        data: Optional[Dict] = None,
        error: Optional[str] = None,
        action_id: str = "",
        entity_id: str = "",
    ):
        self.success = success
        self.data = data or {}
        self.error = error
        self.action_id = action_id
        self.entity_id = entity_id

    def to_dict(self) -> Dict:
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "action_id": self.action_id,
            "entity_id": self.entity_id,
        }


@dataclass
class StagedMutation:
    """A mutation staged for signature and commit"""
    staged_id: str
    action_id: str
    action_label: str
    entity_id: str
    entity_type: str
    yacht_id: str
    user_id: str
    payload: Dict
    requires_signature: bool
    diff: Dict  # {before: {...}, after: {...}, changes: [...]}
    diff_hash: str
    confirmation_message: str
    expires_at: datetime
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict:
        return {
            "staged_id": self.staged_id,
            "action_id": self.action_id,
            "action_label": self.action_label,
            "entity_id": self.entity_id,
            "entity_type": self.entity_type,
            "yacht_id": self.yacht_id,
            "user_id": self.user_id,
            "payload": self.payload,
            "requires_signature": self.requires_signature,
            "diff": self.diff,
            "diff_hash": self.diff_hash,
            "confirmation_message": self.confirmation_message,
            "expires_at": self.expires_at.isoformat(),
            "created_at": self.created_at.isoformat(),
        }


# =============================================================================
# TABLE MAPPINGS
# =============================================================================

# Entity type to database table
ENTITY_TO_TABLE = {
    "equipment": "equipment",
    "part": "parts",
    "inventory_item": "parts",
    "work_order": "work_orders",
    "fault": "faults",
    "document": "documents",
    "document_chunk": "document_chunks",
    "manual_section": "document_chunks",
    "handover": "handover_items",
    "checklist": "checklists",
    "checklist_item": "checklist_items",
    "purchase": "purchases",
    "crew": "crew_members",
    "hours_of_rest": "hours_of_rest",
    "worklist": "worklists",
    "worklist_item": "worklist_items",
    "yacht": "yachts",
    "fleet": "fleets",
}

# Status flow for work orders
WORK_ORDER_STATUS_FLOW = {
    "draft": ["open"],
    "open": ["in_progress", "cancelled"],
    "in_progress": ["pending_parts", "completed", "cancelled"],
    "pending_parts": ["in_progress", "cancelled"],
    "completed": ["closed"],
    "closed": [],
    "cancelled": [],
}


# =============================================================================
# ACTION EXECUTOR
# =============================================================================

class ActionExecutor:
    """
    Executes microactions against the database.

    Provides:
    - READ handlers (immediate execution)
    - MUTATE handlers (staged prepare → commit)
    - Diff generation for mutations
    - Audit logging
    """

    # In-memory staging store (replace with Redis in production)
    _staged_mutations: Dict[str, StagedMutation] = {}

    # Staging expiry (10 minutes)
    STAGING_TTL_MINUTES = 10

    def __init__(self, supabase_client):
        """
        Initialize executor with Supabase client.

        Args:
            supabase_client: Initialized supabase-py client
        """
        self.db = supabase_client
        self._register_handlers()

    def _register_handlers(self):
        """Register all action handlers"""
        # READ handlers - immediate execution
        self._read_handlers: Dict[str, Callable] = {
            # Equipment domain
            "view_equipment": self._read_equipment,
            "view_maintenance_history": self._read_maintenance_history,
            "view_equipment_parts": self._read_equipment_parts,
            "view_linked_faults": self._read_linked_faults,
            "view_equipment_manual": self._read_equipment_manual,

            # Inventory domain
            "view_inventory_item": self._read_inventory_item,
            "view_stock_levels": self._read_stock_levels,
            "view_part_location": self._read_part_location,
            "view_part_usage": self._read_part_usage,
            "scan_part_barcode": self._read_part_barcode,
            "check_stock_level": self._read_stock_levels,  # Alias

            # Work order domain
            "view_work_order": self._read_work_order,
            "view_work_order_history": self._read_work_order_history,
            "view_work_order_checklist": self._read_work_order_checklist,
            "open_work_order": self._read_work_order,  # Alias for navigation

            # Fault domain
            "view_fault": self._read_fault,
            "diagnose_fault": self._read_fault_diagnosis,
            "run_diagnostic": self._read_diagnostic,
            "view_fault_history": self._read_fault_history,
            "suggest_parts": self._read_suggested_parts,

            # Manual/document domain
            "view_manual_section": self._read_document_chunk,
            "view_related_docs": self._read_related_docs,

            # Handover domain
            "view_handover": self._read_handover,
            "export_handover": self._read_handover_export,

            # Hours of rest domain
            "view_hours_of_rest": self._read_hours_of_rest,
            "export_hours_of_rest": self._read_hours_of_rest_export,
            "view_compliance_status": self._read_compliance_status,

            # Purchasing domain
            "track_delivery": self._read_delivery_tracking,

            # Checklists domain
            "view_checklist": self._read_checklist,

            # Shipyard domain
            "view_worklist": self._read_worklist,
            "export_worklist": self._read_worklist_export,

            # Fleet domain
            "view_fleet_summary": self._read_fleet_summary,
            "open_vessel": self._read_vessel,
            "export_fleet_summary": self._read_fleet_export,

            # Predictive domain
            "request_predictive_insight": self._read_predictive_insight,
            "view_smart_summary": self._read_smart_summary,

            # Mobile domain
            "view_attachments": self._read_attachments,
        }

        # MUTATE handlers - staged execution
        self._mutate_handlers: Dict[str, Tuple[Callable, Callable]] = {
            # (prepare_fn, commit_fn)

            # Inventory domain
            "edit_inventory_quantity": (self._prepare_edit_quantity, self._commit_edit_quantity),
            "create_reorder": (self._prepare_create_reorder, self._commit_create_reorder),
            "log_part_usage": (self._prepare_log_usage, self._commit_log_usage),
            "add_part": (self._prepare_add_part, self._commit_add_part),

            # Work order domain
            "create_work_order": (self._prepare_create_work_order, self._commit_create_work_order),
            "update_work_order_status": (self._prepare_update_wo_status, self._commit_update_wo_status),
            "mark_work_order_complete": (self._prepare_mark_wo_complete, self._commit_mark_wo_complete),
            "add_work_order_note": (self._prepare_add_wo_note, self._commit_add_wo_note),
            "add_work_order_photo": (self._prepare_add_wo_photo, self._commit_add_wo_photo),
            "add_parts_to_work_order": (self._prepare_add_parts_to_wo, self._commit_add_parts_to_wo),
            "assign_work_order": (self._prepare_assign_wo, self._commit_assign_wo),
            "edit_work_order_details": (self._prepare_edit_wo, self._commit_edit_wo),

            # Fault domain
            "log_symptom": (self._prepare_log_symptom, self._commit_log_symptom),
            "report_fault": (self._prepare_report_fault, self._commit_report_fault),
            "add_fault_note": (self._prepare_add_fault_note, self._commit_add_fault_note),
            "add_fault_photo": (self._prepare_add_fault_photo, self._commit_add_fault_photo),

            # Equipment domain
            "add_equipment_note": (self._prepare_add_equipment_note, self._commit_add_equipment_note),

            # Handover domain
            "add_to_handover": (self._prepare_add_to_handover, self._commit_add_to_handover),
            "add_document_to_handover": (self._prepare_add_doc_to_handover, self._commit_add_doc_to_handover),
            "add_predictive_insight_to_handover": (self._prepare_add_insight_to_handover, self._commit_add_insight_to_handover),
            "edit_handover_section": (self._prepare_edit_handover, self._commit_edit_handover),
            "regenerate_handover_summary": (self._prepare_regen_handover, self._commit_regen_handover),

            # Hours of rest domain
            "update_hours_of_rest": (self._prepare_update_hours, self._commit_update_hours),

            # Purchasing domain
            "create_purchase_request": (self._prepare_create_purchase, self._commit_create_purchase),
            "add_item_to_purchase": (self._prepare_add_to_purchase, self._commit_add_to_purchase),
            "approve_purchase": (self._prepare_approve_purchase, self._commit_approve_purchase),
            "upload_invoice": (self._prepare_upload_invoice, self._commit_upload_invoice),
            "log_delivery_received": (self._prepare_log_delivery, self._commit_log_delivery),
            "update_purchase_status": (self._prepare_update_purchase_status, self._commit_update_purchase_status),

            # Checklists domain
            "mark_checklist_item_complete": (self._prepare_mark_checklist_done, self._commit_mark_checklist_done),
            "add_checklist_note": (self._prepare_add_checklist_note, self._commit_add_checklist_note),
            "add_checklist_photo": (self._prepare_add_checklist_photo, self._commit_add_checklist_photo),

            # Shipyard domain
            "add_worklist_task": (self._prepare_add_worklist_task, self._commit_add_worklist_task),
            "update_worklist_progress": (self._prepare_update_worklist, self._commit_update_worklist),
            "tag_for_survey": (self._prepare_tag_survey, self._commit_tag_survey),

            # Mobile domain
            "upload_photo": (self._prepare_upload_photo, self._commit_upload_photo),
            "record_voice_note": (self._prepare_voice_note, self._commit_voice_note),
        }

    # =========================================================================
    # PUBLIC API
    # =========================================================================

    async def execute_read(
        self,
        action_id: str,
        entity_id: str,
        yacht_id: str,
        params: Optional[Dict] = None
    ) -> ExecutionResult:
        """
        Execute a READ action immediately.

        Args:
            action_id: The action to execute
            entity_id: Target entity ID
            yacht_id: Yacht context
            params: Optional additional parameters

        Returns:
            ExecutionResult with data or error
        """
        handler = self._read_handlers.get(action_id)
        if not handler:
            return ExecutionResult(
                success=False,
                error=f"Unknown READ action: {action_id}",
                action_id=action_id,
                entity_id=entity_id
            )

        try:
            data = await handler(entity_id, yacht_id, params or {})
            return ExecutionResult(
                success=True,
                data=data,
                action_id=action_id,
                entity_id=entity_id
            )
        except Exception as e:
            logger.error(f"READ action failed: {action_id} - {e}")
            return ExecutionResult(
                success=False,
                error=str(e),
                action_id=action_id,
                entity_id=entity_id
            )

    async def prepare_mutation(
        self,
        action_id: str,
        entity_id: str,
        entity_type: str,
        yacht_id: str,
        user_id: str,
        payload: Dict,
        action_label: str = "",
        requires_signature: bool = True,
        confirmation_message: str = ""
    ) -> Dict:
        """
        Prepare a MUTATE action for signing.

        Args:
            action_id: The action to prepare
            entity_id: Target entity ID
            entity_type: Type of entity
            yacht_id: Yacht context
            user_id: User performing action
            payload: Mutation payload
            action_label: Human-readable label
            requires_signature: Whether signature is required
            confirmation_message: Message to show user

        Returns:
            Staged mutation details with diff preview
        """
        handlers = self._mutate_handlers.get(action_id)
        if not handlers:
            return {
                "success": False,
                "error": f"Unknown MUTATE action: {action_id}"
            }

        prepare_fn, _ = handlers

        try:
            # Get current state and compute diff
            diff = await prepare_fn(entity_id, yacht_id, payload)

            # Generate staged mutation
            staged_id = str(uuid.uuid4())
            expires_at = datetime.now(timezone.utc) + timedelta(minutes=self.STAGING_TTL_MINUTES)

            # Hash the diff for integrity verification
            diff_hash = hashlib.sha256(
                json.dumps(diff, sort_keys=True, default=str).encode()
            ).hexdigest()

            staged = StagedMutation(
                staged_id=staged_id,
                action_id=action_id,
                action_label=action_label or action_id.replace("_", " ").title(),
                entity_id=entity_id,
                entity_type=entity_type,
                yacht_id=yacht_id,
                user_id=user_id,
                payload=payload,
                requires_signature=requires_signature,
                diff=diff,
                diff_hash=diff_hash,
                confirmation_message=confirmation_message or f"Confirm {action_label}",
                expires_at=expires_at,
            )

            # Store in staging area
            self._staged_mutations[staged_id] = staged

            return {
                "success": True,
                "staged_id": staged_id,
                "action_id": action_id,
                "action_label": staged.action_label,
                "entity_id": entity_id,
                "requires_signature": requires_signature,
                "diff": diff,
                "diff_hash": diff_hash,
                "confirmation_message": staged.confirmation_message,
                "expires_at": expires_at.isoformat(),
                "next_step": "POST /v1/signatures with staged_id to sign, then POST /v1/actions/commit"
            }

        except Exception as e:
            logger.error(f"MUTATE prepare failed: {action_id} - {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def commit_mutation(
        self,
        staged_id: str,
        signature: Optional[str] = None,
        signature_timestamp: Optional[datetime] = None
    ) -> ExecutionResult:
        """
        Commit a staged mutation after signature.

        Args:
            staged_id: ID of staged mutation
            signature: Biometric/PIN signature (if required)
            signature_timestamp: When signature was captured

        Returns:
            ExecutionResult with commit status
        """
        staged = self._staged_mutations.get(staged_id)
        if not staged:
            return ExecutionResult(
                success=False,
                error="Staged mutation not found or expired"
            )

        # Check expiry
        if datetime.now(timezone.utc) > staged.expires_at:
            del self._staged_mutations[staged_id]
            return ExecutionResult(
                success=False,
                error="Staged mutation has expired"
            )

        # Check signature if required
        if staged.requires_signature and not signature:
            return ExecutionResult(
                success=False,
                error="Signature required for this action"
            )

        # Get commit handler
        handlers = self._mutate_handlers.get(staged.action_id)
        if not handlers:
            return ExecutionResult(
                success=False,
                error=f"No commit handler for: {staged.action_id}"
            )

        _, commit_fn = handlers

        try:
            # Execute the commit
            result = await commit_fn(
                entity_id=staged.entity_id,
                yacht_id=staged.yacht_id,
                payload=staged.payload,
                diff=staged.diff,
                user_id=staged.user_id
            )

            # Log to audit
            await self._log_audit(
                yacht_id=staged.yacht_id,
                user_id=staged.user_id,
                action_id=staged.action_id,
                entity_id=staged.entity_id,
                entity_type=staged.entity_type,
                diff=staged.diff,
                signature=signature,
                signature_timestamp=signature_timestamp
            )

            # Remove from staging
            del self._staged_mutations[staged_id]

            return ExecutionResult(
                success=True,
                data=result,
                action_id=staged.action_id,
                entity_id=staged.entity_id
            )

        except Exception as e:
            logger.error(f"MUTATE commit failed: {staged.action_id} - {e}")
            return ExecutionResult(
                success=False,
                error=str(e),
                action_id=staged.action_id,
                entity_id=staged.entity_id
            )

    def get_staged(self, staged_id: str) -> Optional[Dict]:
        """Get details of a staged mutation"""
        staged = self._staged_mutations.get(staged_id)
        if staged and datetime.now(timezone.utc) <= staged.expires_at:
            return staged.to_dict()
        return None

    # =========================================================================
    # READ HANDLERS - Equipment Domain
    # =========================================================================

    async def _read_equipment(self, entity_id: str, yacht_id: str, params: Dict) -> Dict:
        """View equipment details"""
        result = self.db.table("equipment").select(
            "id, canonical_label, category, manufacturer, model, serial_number, "
            "location, install_date, last_service_date, running_hours, status, notes"
        ).eq("yacht_id", yacht_id).eq("id", entity_id).single().execute()

        if not result.data:
            raise ValueError(f"Equipment not found: {entity_id}")

        return {
            "equipment": result.data,
            "fetched_at": datetime.now(timezone.utc).isoformat()
        }

    async def _read_maintenance_history(self, entity_id: str, yacht_id: str, params: Dict) -> Dict:
        """View maintenance history for equipment"""
        result = self.db.table("work_orders").select(
            "id, title, description, status, created_at, completed_at, resolution"
        ).eq("yacht_id", yacht_id).eq(
            "equipment_id", entity_id
        ).order("created_at", desc=True).limit(20).execute()

        return {
            "equipment_id": entity_id,
            "maintenance_history": result.data or [],
            "count": len(result.data or [])
        }

    async def _read_equipment_parts(self, entity_id: str, yacht_id: str, params: Dict) -> Dict:
        """View parts associated with equipment"""
        result = self.db.table("parts").select(
            "id, canonical_name, part_number, manufacturer, quantity, min_quantity, location"
        ).eq("yacht_id", yacht_id).eq("equipment_id", entity_id).execute()

        return {
            "equipment_id": entity_id,
            "parts": result.data or [],
            "count": len(result.data or [])
        }

    async def _read_linked_faults(self, entity_id: str, yacht_id: str, params: Dict) -> Dict:
        """View faults linked to equipment"""
        result = self.db.table("faults").select(
            "id, fault_code, description, severity, status, reported_at, resolved_at"
        ).eq("yacht_id", yacht_id).eq(
            "equipment_id", entity_id
        ).order("reported_at", desc=True).limit(20).execute()

        return {
            "equipment_id": entity_id,
            "faults": result.data or [],
            "count": len(result.data or [])
        }

    async def _read_equipment_manual(self, entity_id: str, yacht_id: str, params: Dict) -> Dict:
        """Find manual sections for equipment"""
        # Get equipment label first
        eq = self.db.table("equipment").select("canonical_label").eq(
            "id", entity_id
        ).single().execute()

        if not eq.data:
            raise ValueError(f"Equipment not found: {entity_id}")

        label = eq.data["canonical_label"]

        # Search document chunks for this equipment
        result = self.db.table("document_chunks").select(
            "id, document_id, section_title, page_number, content"
        ).eq("yacht_id", yacht_id).ilike(
            "content", f"%{label}%"
        ).limit(10).execute()

        return {
            "equipment_id": entity_id,
            "equipment_label": label,
            "manual_sections": result.data or [],
            "count": len(result.data or [])
        }

    # =========================================================================
    # READ HANDLERS - Inventory Domain
    # =========================================================================

    async def _read_inventory_item(self, entity_id: str, yacht_id: str, params: Dict) -> Dict:
        """View inventory item details"""
        result = self.db.table("parts").select(
            "id, canonical_name, part_number, manufacturer, description, "
            "quantity, min_quantity, max_quantity, unit, location, "
            "last_ordered_at, last_used_at, unit_cost, supplier"
        ).eq("yacht_id", yacht_id).eq("id", entity_id).single().execute()

        if not result.data:
            raise ValueError(f"Part not found: {entity_id}")

        return {
            "part": result.data,
            "low_stock": (result.data.get("quantity", 0) <= result.data.get("min_quantity", 0)),
            "fetched_at": datetime.now(timezone.utc).isoformat()
        }

    async def _read_stock_levels(self, entity_id: str, yacht_id: str, params: Dict) -> Dict:
        """View stock levels with history"""
        # Current level
        current = self.db.table("parts").select(
            "id, canonical_name, quantity, min_quantity, max_quantity, unit"
        ).eq("yacht_id", yacht_id).eq("id", entity_id).single().execute()

        if not current.data:
            raise ValueError(f"Part not found: {entity_id}")

        # Usage history (last 30 days)
        # This would normally query a stock_transactions table
        # For now, return current state
        return {
            "part_id": entity_id,
            "current": current.data,
            "status": self._stock_status(current.data),
            "fetched_at": datetime.now(timezone.utc).isoformat()
        }

    def _stock_status(self, part: Dict) -> str:
        """Determine stock status"""
        qty = part.get("quantity", 0)
        min_qty = part.get("min_quantity", 0)
        max_qty = part.get("max_quantity", float("inf"))

        if qty <= 0:
            return "OUT_OF_STOCK"
        elif qty <= min_qty:
            return "LOW_STOCK"
        elif qty >= max_qty:
            return "OVERSTOCKED"
        else:
            return "NORMAL"

    async def _read_part_location(self, entity_id: str, yacht_id: str, params: Dict) -> Dict:
        """View part storage location"""
        result = self.db.table("parts").select(
            "id, canonical_name, location, bin_number, deck, compartment"
        ).eq("yacht_id", yacht_id).eq("id", entity_id).single().execute()

        if not result.data:
            raise ValueError(f"Part not found: {entity_id}")

        return {"location": result.data}

    async def _read_part_usage(self, entity_id: str, yacht_id: str, params: Dict) -> Dict:
        """View part usage history"""
        # Query work orders where this part was used
        result = self.db.table("work_order_parts").select(
            "work_order_id, quantity_used, used_at, work_orders(title)"
        ).eq("part_id", entity_id).order("used_at", desc=True).limit(20).execute()

        return {
            "part_id": entity_id,
            "usage_history": result.data or [],
            "count": len(result.data or [])
        }

    async def _read_part_barcode(self, entity_id: str, yacht_id: str, params: Dict) -> Dict:
        """Scan/lookup by barcode"""
        barcode = params.get("barcode", entity_id)

        result = self.db.table("parts").select("*").eq(
            "yacht_id", yacht_id
        ).or_(f"barcode.eq.{barcode},part_number.eq.{barcode}").single().execute()

        if not result.data:
            raise ValueError(f"Part not found for barcode: {barcode}")

        return {"part": result.data}

    # =========================================================================
    # READ HANDLERS - Work Order Domain
    # =========================================================================

    async def _read_work_order(self, entity_id: str, yacht_id: str, params: Dict) -> Dict:
        """View work order details"""
        result = self.db.table("work_orders").select(
            "*, equipment:equipment_id(canonical_label), "
            "assignee:assigned_to(name)"
        ).eq("yacht_id", yacht_id).eq("id", entity_id).single().execute()

        if not result.data:
            raise ValueError(f"Work order not found: {entity_id}")

        return {
            "work_order": result.data,
            "fetched_at": datetime.now(timezone.utc).isoformat()
        }

    async def _read_work_order_history(self, entity_id: str, yacht_id: str, params: Dict) -> Dict:
        """View work order status history"""
        # Query audit log for this work order
        result = self.db.table("audit_log").select(
            "action, old_values, new_values, created_at, user:user_id(name)"
        ).eq("entity_type", "work_order").eq(
            "entity_id", entity_id
        ).order("created_at", desc=True).limit(50).execute()

        return {
            "work_order_id": entity_id,
            "history": result.data or []
        }

    async def _read_work_order_checklist(self, entity_id: str, yacht_id: str, params: Dict) -> Dict:
        """View work order checklist items"""
        result = self.db.table("checklist_items").select(
            "id, description, is_completed, completed_at, completed_by, notes"
        ).eq("work_order_id", entity_id).order("sequence").execute()

        return {
            "work_order_id": entity_id,
            "checklist": result.data or [],
            "completed": len([i for i in (result.data or []) if i.get("is_completed")]),
            "total": len(result.data or [])
        }

    # =========================================================================
    # READ HANDLERS - Fault Domain
    # =========================================================================

    async def _read_fault(self, entity_id: str, yacht_id: str, params: Dict) -> Dict:
        """View fault details"""
        result = self.db.table("faults").select(
            "*, equipment:equipment_id(canonical_label)"
        ).eq("yacht_id", yacht_id).eq("id", entity_id).single().execute()

        if not result.data:
            raise ValueError(f"Fault not found: {entity_id}")

        return {
            "fault": result.data,
            "fetched_at": datetime.now(timezone.utc).isoformat()
        }

    async def _read_fault_diagnosis(self, entity_id: str, yacht_id: str, params: Dict) -> Dict:
        """Run fault diagnosis analysis"""
        fault = self.db.table("faults").select(
            "fault_code, equipment_id"
        ).eq("id", entity_id).single().execute()

        if not fault.data:
            raise ValueError(f"Fault not found: {entity_id}")

        # Get related diagnostic info from knowledge graph
        diagnosis = self.db.table("graph_edges").select(
            "target_node:target_id(label, properties)"
        ).eq("source_id", entity_id).eq("edge_type", "DIAGNOSED_BY").execute()

        # Get suggested remedies
        remedies = self.db.table("maintenance_templates").select(
            "action, interval_hours, procedure, parts_needed"
        ).eq("fault_code", fault.data["fault_code"]).execute()

        return {
            "fault_id": entity_id,
            "fault_code": fault.data["fault_code"],
            "diagnosis": diagnosis.data or [],
            "suggested_remedies": remedies.data or []
        }

    async def _read_diagnostic(self, entity_id: str, yacht_id: str, params: Dict) -> Dict:
        """Run diagnostic on equipment"""
        # Get latest sensor data
        sensors = self.db.table("sensor_readings").select(
            "sensor_type, value, unit, timestamp"
        ).eq("equipment_id", entity_id).order(
            "timestamp", desc=True
        ).limit(10).execute()

        # Get predictive state
        predictive = self.db.table("predictive_state").select(
            "risk_score, confidence, anomalies, next_maintenance_due"
        ).eq("equipment_id", entity_id).single().execute()

        return {
            "equipment_id": entity_id,
            "sensor_readings": sensors.data or [],
            "predictive_state": predictive.data,
            "ran_at": datetime.now(timezone.utc).isoformat()
        }

    async def _read_fault_history(self, entity_id: str, yacht_id: str, params: Dict) -> Dict:
        """View fault history for equipment"""
        # entity_id could be fault_id or equipment_id
        result = self.db.table("faults").select(
            "id, fault_code, description, severity, status, reported_at, resolved_at"
        ).eq("yacht_id", yacht_id).or_(
            f"id.eq.{entity_id},equipment_id.eq.{entity_id}"
        ).order("reported_at", desc=True).limit(20).execute()

        return {
            "faults": result.data or [],
            "count": len(result.data or [])
        }

    async def _read_suggested_parts(self, entity_id: str, yacht_id: str, params: Dict) -> Dict:
        """Suggest parts for fault repair"""
        # Get fault details
        fault = self.db.table("faults").select(
            "fault_code, equipment_id"
        ).eq("id", entity_id).single().execute()

        if not fault.data:
            raise ValueError(f"Fault not found: {entity_id}")

        # Get parts from maintenance templates
        templates = self.db.table("maintenance_templates").select(
            "parts_needed"
        ).eq("fault_code", fault.data["fault_code"]).execute()

        # Get actual inventory for those parts
        part_names = []
        for t in (templates.data or []):
            if t.get("parts_needed"):
                part_names.extend(t["parts_needed"])

        if part_names:
            parts = self.db.table("parts").select(
                "id, canonical_name, quantity, min_quantity, location"
            ).eq("yacht_id", yacht_id).in_("canonical_name", part_names).execute()
        else:
            parts = {"data": []}

        return {
            "fault_id": entity_id,
            "suggested_parts": parts.data or [],
            "available": len([p for p in (parts.data or []) if p.get("quantity", 0) > 0])
        }

    # =========================================================================
    # READ HANDLERS - Document Domain
    # =========================================================================

    async def _read_document_chunk(self, entity_id: str, yacht_id: str, params: Dict) -> Dict:
        """View document/manual section"""
        result = self.db.table("document_chunks").select(
            "id, document_id, section_title, content, page_number, "
            "documents(title, category)"
        ).eq("id", entity_id).single().execute()

        if not result.data:
            raise ValueError(f"Document chunk not found: {entity_id}")

        return {"chunk": result.data}

    async def _read_related_docs(self, entity_id: str, yacht_id: str, params: Dict) -> Dict:
        """Find related documents"""
        # Get source chunk
        source = self.db.table("document_chunks").select(
            "content, document_id"
        ).eq("id", entity_id).single().execute()

        if not source.data:
            raise ValueError(f"Document chunk not found: {entity_id}")

        # Get related via graph edges
        related = self.db.table("graph_edges").select(
            "target_node:target_id(id, label)"
        ).eq("source_id", entity_id).eq("edge_type", "REFERENCES").limit(10).execute()

        return {
            "source_id": entity_id,
            "related": related.data or []
        }

    # =========================================================================
    # READ HANDLERS - Handover Domain
    # =========================================================================

    async def _read_handover(self, entity_id: str, yacht_id: str, params: Dict) -> Dict:
        """View handover notes"""
        result = self.db.table("handover_items").select(
            "id, summary, content, author, created_at, equipment_id, category"
        ).eq("yacht_id", yacht_id).order("created_at", desc=True).limit(50).execute()

        return {
            "handover_items": result.data or [],
            "count": len(result.data or [])
        }

    async def _read_handover_export(self, entity_id: str, yacht_id: str, params: Dict) -> Dict:
        """Export handover as PDF (returns data for rendering)"""
        items = self.db.table("handover_items").select("*").eq(
            "yacht_id", yacht_id
        ).order("created_at", desc=True).execute()

        return {
            "export_format": "pdf",
            "items": items.data or [],
            "generated_at": datetime.now(timezone.utc).isoformat()
        }

    # =========================================================================
    # READ HANDLERS - Hours of Rest Domain
    # =========================================================================

    async def _read_hours_of_rest(self, entity_id: str, yacht_id: str, params: Dict) -> Dict:
        """View hours of rest for crew"""
        result = self.db.table("hours_of_rest").select(
            "id, crew_member_id, date, work_hours, rest_hours, is_compliant, notes"
        ).eq("yacht_id", yacht_id).eq(
            "crew_member_id", entity_id
        ).order("date", desc=True).limit(30).execute()

        return {
            "crew_member_id": entity_id,
            "records": result.data or []
        }

    async def _read_hours_of_rest_export(self, entity_id: str, yacht_id: str, params: Dict) -> Dict:
        """Export hours of rest logs"""
        records = self.db.table("hours_of_rest").select(
            "*, crew:crew_member_id(name)"
        ).eq("yacht_id", yacht_id).order("date", desc=True).execute()

        return {
            "export_format": "xlsx",
            "records": records.data or [],
            "generated_at": datetime.now(timezone.utc).isoformat()
        }

    async def _read_compliance_status(self, entity_id: str, yacht_id: str, params: Dict) -> Dict:
        """Check MLC compliance status"""
        result = self.db.rpc("check_mlc_compliance", {
            "p_yacht_id": yacht_id,
            "p_crew_member_id": entity_id
        }).execute()

        return {
            "crew_member_id": entity_id,
            "compliance": result.data or {"status": "unknown"}
        }

    # =========================================================================
    # READ HANDLERS - Other Domains
    # =========================================================================

    async def _read_delivery_tracking(self, entity_id: str, yacht_id: str, params: Dict) -> Dict:
        """Track purchase delivery"""
        result = self.db.table("purchases").select(
            "id, status, tracking_number, supplier, expected_delivery, "
            "shipped_at, delivered_at"
        ).eq("id", entity_id).single().execute()

        if not result.data:
            raise ValueError(f"Purchase not found: {entity_id}")

        return {"delivery": result.data}

    async def _read_checklist(self, entity_id: str, yacht_id: str, params: Dict) -> Dict:
        """View checklist details"""
        checklist = self.db.table("checklists").select(
            "id, title, category, created_at"
        ).eq("id", entity_id).single().execute()

        items = self.db.table("checklist_items").select(
            "id, description, is_completed, completed_at, sequence"
        ).eq("checklist_id", entity_id).order("sequence").execute()

        return {
            "checklist": checklist.data,
            "items": items.data or [],
            "progress": {
                "completed": len([i for i in (items.data or []) if i.get("is_completed")]),
                "total": len(items.data or [])
            }
        }

    async def _read_worklist(self, entity_id: str, yacht_id: str, params: Dict) -> Dict:
        """View shipyard worklist"""
        result = self.db.table("worklists").select(
            "*, items:worklist_items(*)"
        ).eq("yacht_id", yacht_id).eq("id", entity_id).single().execute()

        if not result.data:
            raise ValueError(f"Worklist not found: {entity_id}")

        return {"worklist": result.data}

    async def _read_worklist_export(self, entity_id: str, yacht_id: str, params: Dict) -> Dict:
        """Export worklist"""
        result = self.db.table("worklists").select(
            "*, items:worklist_items(*)"
        ).eq("id", entity_id).single().execute()

        return {
            "export_format": "xlsx",
            "worklist": result.data,
            "generated_at": datetime.now(timezone.utc).isoformat()
        }

    async def _read_fleet_summary(self, entity_id: str, yacht_id: str, params: Dict) -> Dict:
        """View fleet summary"""
        yachts = self.db.table("yachts").select(
            "id, name, imo_number, flag, status"
        ).eq("fleet_id", entity_id).execute()

        return {
            "fleet_id": entity_id,
            "vessels": yachts.data or [],
            "count": len(yachts.data or [])
        }

    async def _read_vessel(self, entity_id: str, yacht_id: str, params: Dict) -> Dict:
        """Open vessel details"""
        result = self.db.table("yachts").select("*").eq("id", entity_id).single().execute()

        if not result.data:
            raise ValueError(f"Vessel not found: {entity_id}")

        return {"vessel": result.data}

    async def _read_fleet_export(self, entity_id: str, yacht_id: str, params: Dict) -> Dict:
        """Export fleet summary"""
        yachts = self.db.table("yachts").select("*").eq("fleet_id", entity_id).execute()

        return {
            "export_format": "pdf",
            "fleet_id": entity_id,
            "vessels": yachts.data or [],
            "generated_at": datetime.now(timezone.utc).isoformat()
        }

    async def _read_predictive_insight(self, entity_id: str, yacht_id: str, params: Dict) -> Dict:
        """Get predictive insight for equipment"""
        result = self.db.table("predictive_state").select(
            "risk_score, confidence, anomalies, failure_probability, "
            "next_maintenance_due, trend"
        ).eq("equipment_id", entity_id).single().execute()

        return {
            "equipment_id": entity_id,
            "insight": result.data or {"risk_score": 0, "confidence": 0}
        }

    async def _read_smart_summary(self, entity_id: str, yacht_id: str, params: Dict) -> Dict:
        """Get AI-generated smart summary"""
        # This would normally call an AI service
        return {
            "entity_id": entity_id,
            "summary": "Smart summary generation requires AI service integration",
            "generated_at": datetime.now(timezone.utc).isoformat()
        }

    async def _read_attachments(self, entity_id: str, yacht_id: str, params: Dict) -> Dict:
        """View attachments for entity"""
        result = self.db.table("attachments").select(
            "id, filename, mime_type, storage_path, uploaded_at, uploaded_by"
        ).eq("entity_id", entity_id).order("uploaded_at", desc=True).execute()

        return {
            "entity_id": entity_id,
            "attachments": result.data or []
        }

    # =========================================================================
    # MUTATE HANDLERS - Inventory Domain
    # =========================================================================

    async def _prepare_edit_quantity(self, entity_id: str, yacht_id: str, payload: Dict) -> Dict:
        """Prepare quantity edit - compute diff"""
        current = self.db.table("parts").select(
            "id, canonical_name, quantity, unit"
        ).eq("id", entity_id).single().execute()

        if not current.data:
            raise ValueError(f"Part not found: {entity_id}")

        new_quantity = payload.get("quantity")
        if new_quantity is None:
            raise ValueError("New quantity required")

        return {
            "before": {
                "quantity": current.data["quantity"],
                "unit": current.data.get("unit", "units")
            },
            "after": {
                "quantity": new_quantity,
                "unit": current.data.get("unit", "units")
            },
            "changes": [
                {
                    "field": "quantity",
                    "from": current.data["quantity"],
                    "to": new_quantity,
                    "delta": new_quantity - current.data["quantity"]
                }
            ],
            "part_name": current.data["canonical_name"]
        }

    async def _commit_edit_quantity(
        self, entity_id: str, yacht_id: str, payload: Dict, diff: Dict, user_id: str
    ) -> Dict:
        """Commit quantity edit"""
        result = self.db.table("parts").update({
            "quantity": payload["quantity"],
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "updated_by": user_id
        }).eq("id", entity_id).execute()

        return {
            "updated": True,
            "entity_id": entity_id,
            "new_quantity": payload["quantity"]
        }

    async def _prepare_create_reorder(self, entity_id: str, yacht_id: str, payload: Dict) -> Dict:
        """Prepare reorder request"""
        part = self.db.table("parts").select(
            "id, canonical_name, quantity, min_quantity, supplier, unit_cost"
        ).eq("id", entity_id).single().execute()

        if not part.data:
            raise ValueError(f"Part not found: {entity_id}")

        reorder_qty = payload.get("quantity", part.data.get("min_quantity", 10))

        return {
            "before": {"reorders": 0},
            "after": {
                "reorder_quantity": reorder_qty,
                "estimated_cost": reorder_qty * (part.data.get("unit_cost", 0) or 0)
            },
            "changes": [{"field": "reorder", "action": "create", "quantity": reorder_qty}],
            "part_name": part.data["canonical_name"],
            "supplier": part.data.get("supplier")
        }

    async def _commit_create_reorder(
        self, entity_id: str, yacht_id: str, payload: Dict, diff: Dict, user_id: str
    ) -> Dict:
        """Commit reorder creation"""
        reorder = self.db.table("reorders").insert({
            "yacht_id": yacht_id,
            "part_id": entity_id,
            "quantity": diff["after"]["reorder_quantity"],
            "status": "pending",
            "requested_by": user_id,
            "created_at": datetime.now(timezone.utc).isoformat()
        }).execute()

        return {
            "created": True,
            "reorder_id": reorder.data[0]["id"] if reorder.data else None
        }

    async def _prepare_log_usage(self, entity_id: str, yacht_id: str, payload: Dict) -> Dict:
        """Prepare part usage logging"""
        part = self.db.table("parts").select(
            "id, canonical_name, quantity"
        ).eq("id", entity_id).single().execute()

        if not part.data:
            raise ValueError(f"Part not found: {entity_id}")

        qty_used = payload.get("quantity", 1)

        return {
            "before": {"quantity": part.data["quantity"]},
            "after": {"quantity": part.data["quantity"] - qty_used},
            "changes": [{"field": "quantity", "delta": -qty_used}],
            "part_name": part.data["canonical_name"]
        }

    async def _commit_log_usage(
        self, entity_id: str, yacht_id: str, payload: Dict, diff: Dict, user_id: str
    ) -> Dict:
        """Commit part usage"""
        new_qty = diff["after"]["quantity"]

        # Update quantity
        self.db.table("parts").update({
            "quantity": new_qty,
            "last_used_at": datetime.now(timezone.utc).isoformat()
        }).eq("id", entity_id).execute()

        # Log usage
        self.db.table("part_usage_log").insert({
            "part_id": entity_id,
            "quantity_used": abs(diff["changes"][0]["delta"]),
            "work_order_id": payload.get("work_order_id"),
            "used_by": user_id,
            "used_at": datetime.now(timezone.utc).isoformat()
        }).execute()

        return {"logged": True, "new_quantity": new_qty}

    async def _prepare_add_part(self, entity_id: str, yacht_id: str, payload: Dict) -> Dict:
        """Prepare new part creation"""
        return {
            "before": {"parts_count": "n/a"},
            "after": payload,
            "changes": [{"action": "create_part", "data": payload}]
        }

    async def _commit_add_part(
        self, entity_id: str, yacht_id: str, payload: Dict, diff: Dict, user_id: str
    ) -> Dict:
        """Commit new part creation"""
        result = self.db.table("parts").insert({
            "yacht_id": yacht_id,
            "canonical_name": payload.get("name"),
            "part_number": payload.get("part_number"),
            "manufacturer": payload.get("manufacturer"),
            "quantity": payload.get("quantity", 0),
            "min_quantity": payload.get("min_quantity", 0),
            "location": payload.get("location"),
            "created_by": user_id,
            "created_at": datetime.now(timezone.utc).isoformat()
        }).execute()

        return {
            "created": True,
            "part_id": result.data[0]["id"] if result.data else None
        }

    # =========================================================================
    # MUTATE HANDLERS - Work Order Domain
    # =========================================================================

    async def _prepare_create_work_order(self, entity_id: str, yacht_id: str, payload: Dict) -> Dict:
        """Prepare work order creation"""
        return {
            "before": {"work_orders": "n/a"},
            "after": {
                "title": payload.get("title", "New Work Order"),
                "equipment_id": entity_id,
                "priority": payload.get("priority", "normal"),
                "status": "draft"
            },
            "changes": [{"action": "create_work_order"}]
        }

    async def _commit_create_work_order(
        self, entity_id: str, yacht_id: str, payload: Dict, diff: Dict, user_id: str
    ) -> Dict:
        """Commit work order creation"""
        result = self.db.table("work_orders").insert({
            "yacht_id": yacht_id,
            "equipment_id": entity_id if entity_id != "new" else None,
            "title": payload.get("title", "New Work Order"),
            "description": payload.get("description", ""),
            "priority": payload.get("priority", "normal"),
            "status": "draft",
            "created_by": user_id,
            "created_at": datetime.now(timezone.utc).isoformat()
        }).execute()

        return {
            "created": True,
            "work_order_id": result.data[0]["id"] if result.data else None
        }

    async def _prepare_update_wo_status(self, entity_id: str, yacht_id: str, payload: Dict) -> Dict:
        """Prepare work order status update"""
        current = self.db.table("work_orders").select(
            "id, title, status"
        ).eq("id", entity_id).single().execute()

        if not current.data:
            raise ValueError(f"Work order not found: {entity_id}")

        new_status = payload.get("status")
        if not new_status:
            raise ValueError("New status required")

        # Validate status transition
        allowed = WORK_ORDER_STATUS_FLOW.get(current.data["status"], [])
        if new_status not in allowed:
            raise ValueError(
                f"Invalid status transition: {current.data['status']} → {new_status}. "
                f"Allowed: {allowed}"
            )

        return {
            "before": {"status": current.data["status"]},
            "after": {"status": new_status},
            "changes": [{"field": "status", "from": current.data["status"], "to": new_status}],
            "work_order_title": current.data["title"]
        }

    async def _commit_update_wo_status(
        self, entity_id: str, yacht_id: str, payload: Dict, diff: Dict, user_id: str
    ) -> Dict:
        """Commit work order status update"""
        update_data = {
            "status": payload["status"],
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "updated_by": user_id
        }

        # If completing, set completed_at
        if payload["status"] in ("completed", "closed"):
            update_data["completed_at"] = datetime.now(timezone.utc).isoformat()

        # SECURITY FIX P0-004: Add yacht_id filter for tenant isolation
        self.db.table("work_orders").update(update_data).eq("id", entity_id).eq("yacht_id", yacht_id).execute()

        return {"updated": True, "new_status": payload["status"]}

    async def _prepare_mark_wo_complete(self, entity_id: str, yacht_id: str, payload: Dict) -> Dict:
        """Prepare marking work order complete"""
        payload["status"] = "completed"
        return await self._prepare_update_wo_status(entity_id, yacht_id, payload)

    async def _commit_mark_wo_complete(
        self, entity_id: str, yacht_id: str, payload: Dict, diff: Dict, user_id: str
    ) -> Dict:
        """Commit marking work order complete"""
        payload["status"] = "completed"
        return await self._commit_update_wo_status(entity_id, yacht_id, payload, diff, user_id)

    async def _prepare_add_wo_note(self, entity_id: str, yacht_id: str, payload: Dict) -> Dict:
        """Prepare adding note to work order"""
        return {
            "before": {"notes": "existing"},
            "after": {"note": payload.get("note", "")},
            "changes": [{"action": "add_note"}]
        }

    async def _commit_add_wo_note(
        self, entity_id: str, yacht_id: str, payload: Dict, diff: Dict, user_id: str
    ) -> Dict:
        """Commit adding note to work order"""
        result = self.db.table("work_order_notes").insert({
            "work_order_id": entity_id,
            "content": payload.get("note", ""),
            "author_id": user_id,
            "created_at": datetime.now(timezone.utc).isoformat()
        }).execute()

        return {"added": True, "note_id": result.data[0]["id"] if result.data else None}

    async def _prepare_add_wo_photo(self, entity_id: str, yacht_id: str, payload: Dict) -> Dict:
        """Prepare adding photo to work order"""
        return {
            "before": {"attachments": "existing"},
            "after": {"attachment": payload.get("filename", "photo")},
            "changes": [{"action": "add_photo"}]
        }

    async def _commit_add_wo_photo(
        self, entity_id: str, yacht_id: str, payload: Dict, diff: Dict, user_id: str
    ) -> Dict:
        """Commit adding photo to work order"""
        result = self.db.table("attachments").insert({
            "entity_type": "work_order",
            "entity_id": entity_id,
            "filename": payload.get("filename"),
            "mime_type": payload.get("mime_type", "image/jpeg"),
            "storage_path": payload.get("storage_path"),
            "uploaded_by": user_id,
            "uploaded_at": datetime.now(timezone.utc).isoformat()
        }).execute()

        return {"uploaded": True, "attachment_id": result.data[0]["id"] if result.data else None}

    async def _prepare_add_parts_to_wo(self, entity_id: str, yacht_id: str, payload: Dict) -> Dict:
        """Prepare adding parts to work order"""
        parts = payload.get("parts", [])
        return {
            "before": {"parts_count": 0},
            "after": {"parts_to_add": len(parts)},
            "changes": [{"action": "add_parts", "count": len(parts)}]
        }

    async def _commit_add_parts_to_wo(
        self, entity_id: str, yacht_id: str, payload: Dict, diff: Dict, user_id: str
    ) -> Dict:
        """Commit adding parts to work order"""
        parts = payload.get("parts", [])
        for part in parts:
            self.db.table("work_order_parts").insert({
                "work_order_id": entity_id,
                "part_id": part.get("part_id"),
                "quantity_needed": part.get("quantity", 1)
            }).execute()

        return {"added": True, "parts_count": len(parts)}

    async def _prepare_assign_wo(self, entity_id: str, yacht_id: str, payload: Dict) -> Dict:
        """Prepare assigning work order"""
        current = self.db.table("work_orders").select(
            "id, assigned_to"
        ).eq("id", entity_id).single().execute()

        return {
            "before": {"assigned_to": current.data.get("assigned_to") if current.data else None},
            "after": {"assigned_to": payload.get("assignee_id")},
            "changes": [{"field": "assigned_to", "to": payload.get("assignee_id")}]
        }

    async def _commit_assign_wo(
        self, entity_id: str, yacht_id: str, payload: Dict, diff: Dict, user_id: str
    ) -> Dict:
        """Commit assigning work order"""
        self.db.table("work_orders").update({
            "assigned_to": payload.get("assignee_id"),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }).eq("id", entity_id).execute()

        return {"assigned": True, "assignee_id": payload.get("assignee_id")}

    async def _prepare_edit_wo(self, entity_id: str, yacht_id: str, payload: Dict) -> Dict:
        """Prepare editing work order details"""
        current = self.db.table("work_orders").select(
            "id, title, description, priority"
        ).eq("id", entity_id).single().execute()

        if not current.data:
            raise ValueError(f"Work order not found: {entity_id}")

        changes = []
        for field in ["title", "description", "priority"]:
            if field in payload and payload[field] != current.data.get(field):
                changes.append({
                    "field": field,
                    "from": current.data.get(field),
                    "to": payload[field]
                })

        return {
            "before": current.data,
            "after": {**current.data, **payload},
            "changes": changes
        }

    async def _commit_edit_wo(
        self, entity_id: str, yacht_id: str, payload: Dict, diff: Dict, user_id: str
    ) -> Dict:
        """Commit editing work order"""
        update_data = {
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "updated_by": user_id
        }
        for change in diff["changes"]:
            update_data[change["field"]] = change["to"]

        # SECURITY FIX P0-004: Add yacht_id filter for tenant isolation
        self.db.table("work_orders").update(update_data).eq("id", entity_id).eq("yacht_id", yacht_id).execute()

        return {"updated": True}

    # =========================================================================
    # MUTATE HANDLERS - Fault Domain
    # =========================================================================

    async def _prepare_log_symptom(self, entity_id: str, yacht_id: str, payload: Dict) -> Dict:
        """Prepare logging a symptom"""
        return {
            "before": {"symptoms": "existing"},
            "after": {"symptom": payload.get("symptom_code", payload.get("description", ""))},
            "changes": [{"action": "log_symptom"}]
        }

    async def _commit_log_symptom(
        self, entity_id: str, yacht_id: str, payload: Dict, diff: Dict, user_id: str
    ) -> Dict:
        """Commit logging a symptom"""
        result = self.db.table("symptom_reports").insert({
            "yacht_id": yacht_id,
            "equipment_id": entity_id,
            "symptom_code": payload.get("symptom_code"),
            "description": payload.get("description", ""),
            "severity": payload.get("severity", "medium"),
            "reported_by": user_id,
            "reported_at": datetime.now(timezone.utc).isoformat()
        }).execute()

        return {"logged": True, "report_id": result.data[0]["id"] if result.data else None}

    async def _prepare_report_fault(self, entity_id: str, yacht_id: str, payload: Dict) -> Dict:
        """Prepare reporting a fault"""
        return {
            "before": {"faults": "existing"},
            "after": {
                "fault_code": payload.get("fault_code"),
                "description": payload.get("description"),
                "severity": payload.get("severity", "medium")
            },
            "changes": [{"action": "report_fault"}]
        }

    async def _commit_report_fault(
        self, entity_id: str, yacht_id: str, payload: Dict, diff: Dict, user_id: str
    ) -> Dict:
        """Commit reporting a fault"""
        result = self.db.table("faults").insert({
            "yacht_id": yacht_id,
            "equipment_id": entity_id,
            "fault_code": payload.get("fault_code"),
            "description": payload.get("description", ""),
            "severity": payload.get("severity", "medium"),
            "status": "open",
            "reported_by": user_id,
            "reported_at": datetime.now(timezone.utc).isoformat()
        }).execute()

        return {"reported": True, "fault_id": result.data[0]["id"] if result.data else None}

    async def _prepare_add_fault_note(self, entity_id: str, yacht_id: str, payload: Dict) -> Dict:
        """Prepare adding note to fault"""
        return {
            "before": {"notes": "existing"},
            "after": {"note": payload.get("note", "")},
            "changes": [{"action": "add_note"}]
        }

    async def _commit_add_fault_note(
        self, entity_id: str, yacht_id: str, payload: Dict, diff: Dict, user_id: str
    ) -> Dict:
        """Commit adding note to fault"""
        result = self.db.table("fault_notes").insert({
            "fault_id": entity_id,
            "content": payload.get("note", ""),
            "author_id": user_id,
            "created_at": datetime.now(timezone.utc).isoformat()
        }).execute()

        return {"added": True, "note_id": result.data[0]["id"] if result.data else None}

    async def _prepare_add_fault_photo(self, entity_id: str, yacht_id: str, payload: Dict) -> Dict:
        """Prepare adding photo to fault"""
        return {
            "before": {"attachments": "existing"},
            "after": {"attachment": payload.get("filename", "photo")},
            "changes": [{"action": "add_photo"}]
        }

    async def _commit_add_fault_photo(
        self, entity_id: str, yacht_id: str, payload: Dict, diff: Dict, user_id: str
    ) -> Dict:
        """Commit adding photo to fault"""
        result = self.db.table("attachments").insert({
            "entity_type": "fault",
            "entity_id": entity_id,
            "filename": payload.get("filename"),
            "mime_type": payload.get("mime_type", "image/jpeg"),
            "storage_path": payload.get("storage_path"),
            "uploaded_by": user_id,
            "uploaded_at": datetime.now(timezone.utc).isoformat()
        }).execute()

        return {"uploaded": True, "attachment_id": result.data[0]["id"] if result.data else None}

    # =========================================================================
    # MUTATE HANDLERS - Equipment Domain
    # =========================================================================

    async def _prepare_add_equipment_note(self, entity_id: str, yacht_id: str, payload: Dict) -> Dict:
        """Prepare adding note to equipment"""
        return {
            "before": {"notes": "existing"},
            "after": {"note": payload.get("note", "")},
            "changes": [{"action": "add_note"}]
        }

    async def _commit_add_equipment_note(
        self, entity_id: str, yacht_id: str, payload: Dict, diff: Dict, user_id: str
    ) -> Dict:
        """Commit adding note to equipment"""
        result = self.db.table("equipment_notes").insert({
            "equipment_id": entity_id,
            "content": payload.get("note", ""),
            "author_id": user_id,
            "created_at": datetime.now(timezone.utc).isoformat()
        }).execute()

        return {"added": True, "note_id": result.data[0]["id"] if result.data else None}

    # =========================================================================
    # MUTATE HANDLERS - Handover Domain
    # =========================================================================

    async def _prepare_add_to_handover(self, entity_id: str, yacht_id: str, payload: Dict) -> Dict:
        """Prepare adding item to handover"""
        return {
            "before": {"handover_items": "existing"},
            "after": {
                "entity_id": entity_id,
                "entity_type": payload.get("entity_type"),
                "summary": payload.get("summary", "")
            },
            "changes": [{"action": "add_to_handover"}]
        }

    async def _commit_add_to_handover(
        self, entity_id: str, yacht_id: str, payload: Dict, diff: Dict, user_id: str
    ) -> Dict:
        """Commit adding item to handover"""
        result = self.db.table("handover_items").insert({
            "yacht_id": yacht_id,
            "linked_entity_id": entity_id,
            "linked_entity_type": payload.get("entity_type"),
            "summary": payload.get("summary", ""),
            "content": payload.get("content", ""),
            "author": user_id,
            "created_at": datetime.now(timezone.utc).isoformat()
        }).execute()

        return {"added": True, "handover_item_id": result.data[0]["id"] if result.data else None}

    async def _prepare_add_doc_to_handover(self, entity_id: str, yacht_id: str, payload: Dict) -> Dict:
        """Prepare adding document to handover"""
        return await self._prepare_add_to_handover(entity_id, yacht_id, {
            **payload,
            "entity_type": "document"
        })

    async def _commit_add_doc_to_handover(
        self, entity_id: str, yacht_id: str, payload: Dict, diff: Dict, user_id: str
    ) -> Dict:
        """Commit adding document to handover"""
        return await self._commit_add_to_handover(entity_id, yacht_id, {
            **payload,
            "entity_type": "document"
        }, diff, user_id)

    async def _prepare_add_insight_to_handover(self, entity_id: str, yacht_id: str, payload: Dict) -> Dict:
        """Prepare adding predictive insight to handover"""
        return await self._prepare_add_to_handover(entity_id, yacht_id, {
            **payload,
            "entity_type": "predictive_insight"
        })

    async def _commit_add_insight_to_handover(
        self, entity_id: str, yacht_id: str, payload: Dict, diff: Dict, user_id: str
    ) -> Dict:
        """Commit adding predictive insight to handover"""
        return await self._commit_add_to_handover(entity_id, yacht_id, {
            **payload,
            "entity_type": "predictive_insight"
        }, diff, user_id)

    async def _prepare_edit_handover(self, entity_id: str, yacht_id: str, payload: Dict) -> Dict:
        """Prepare editing handover section"""
        current = self.db.table("handover_items").select(
            "id, summary, content"
        ).eq("id", entity_id).single().execute()

        if not current.data:
            raise ValueError(f"Handover item not found: {entity_id}")

        return {
            "before": current.data,
            "after": {**current.data, **payload},
            "changes": [{"action": "edit_handover"}]
        }

    async def _commit_edit_handover(
        self, entity_id: str, yacht_id: str, payload: Dict, diff: Dict, user_id: str
    ) -> Dict:
        """Commit editing handover section"""
        self.db.table("handover_items").update({
            "summary": payload.get("summary", diff["before"]["summary"]),
            "content": payload.get("content", diff["before"]["content"]),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }).eq("id", entity_id).execute()

        return {"updated": True}

    async def _prepare_regen_handover(self, entity_id: str, yacht_id: str, payload: Dict) -> Dict:
        """Prepare regenerating handover summary"""
        return {
            "before": {"summary": "existing"},
            "after": {"summary": "regenerated"},
            "changes": [{"action": "regenerate_summary"}]
        }

    async def _commit_regen_handover(
        self, entity_id: str, yacht_id: str, payload: Dict, diff: Dict, user_id: str
    ) -> Dict:
        """Commit regenerating handover summary (would call AI)"""
        # This would normally call an AI service to regenerate
        return {
            "regenerated": True,
            "note": "AI summary regeneration requires AI service integration"
        }

    # =========================================================================
    # MUTATE HANDLERS - Hours of Rest Domain
    # =========================================================================

    async def _prepare_update_hours(self, entity_id: str, yacht_id: str, payload: Dict) -> Dict:
        """Prepare updating hours of rest"""
        current = self.db.table("hours_of_rest").select(
            "id, work_hours, rest_hours"
        ).eq("id", entity_id).single().execute()

        if not current.data:
            # New entry
            return {
                "before": {"entry": None},
                "after": payload,
                "changes": [{"action": "create_hours_entry"}]
            }

        return {
            "before": current.data,
            "after": {**current.data, **payload},
            "changes": [{"action": "update_hours"}]
        }

    async def _commit_update_hours(
        self, entity_id: str, yacht_id: str, payload: Dict, diff: Dict, user_id: str
    ) -> Dict:
        """Commit updating hours of rest"""
        if diff["before"].get("entry") is None:
            # Create new
            result = self.db.table("hours_of_rest").insert({
                "yacht_id": yacht_id,
                "crew_member_id": entity_id,
                "date": payload.get("date", datetime.now(timezone.utc).date().isoformat()),
                "work_hours": payload.get("work_hours", 0),
                "rest_hours": payload.get("rest_hours", 0),
                "created_at": datetime.now(timezone.utc).isoformat()
            }).execute()
            return {"created": True, "entry_id": result.data[0]["id"] if result.data else None}
        else:
            # Update existing
            self.db.table("hours_of_rest").update({
                "work_hours": payload.get("work_hours", diff["before"]["work_hours"]),
                "rest_hours": payload.get("rest_hours", diff["before"]["rest_hours"]),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }).eq("id", entity_id).execute()
            return {"updated": True}

    # =========================================================================
    # MUTATE HANDLERS - Purchasing Domain
    # =========================================================================

    async def _prepare_create_purchase(self, entity_id: str, yacht_id: str, payload: Dict) -> Dict:
        """Prepare creating purchase request"""
        return {
            "before": {"purchases": "n/a"},
            "after": {
                "part_id": entity_id,
                "quantity": payload.get("quantity", 1),
                "supplier": payload.get("supplier")
            },
            "changes": [{"action": "create_purchase"}]
        }

    async def _commit_create_purchase(
        self, entity_id: str, yacht_id: str, payload: Dict, diff: Dict, user_id: str
    ) -> Dict:
        """Commit creating purchase request"""
        result = self.db.table("purchases").insert({
            "yacht_id": yacht_id,
            "status": "draft",
            "supplier": payload.get("supplier"),
            "requested_by": user_id,
            "created_at": datetime.now(timezone.utc).isoformat()
        }).execute()

        purchase_id = result.data[0]["id"] if result.data else None

        # Add the item
        if purchase_id and entity_id:
            self.db.table("purchase_items").insert({
                "purchase_id": purchase_id,
                "part_id": entity_id,
                "quantity": payload.get("quantity", 1)
            }).execute()

        return {"created": True, "purchase_id": purchase_id}

    async def _prepare_add_to_purchase(self, entity_id: str, yacht_id: str, payload: Dict) -> Dict:
        """Prepare adding item to purchase"""
        return {
            "before": {"items": "existing"},
            "after": {"item": payload},
            "changes": [{"action": "add_item"}]
        }

    async def _commit_add_to_purchase(
        self, entity_id: str, yacht_id: str, payload: Dict, diff: Dict, user_id: str
    ) -> Dict:
        """Commit adding item to purchase"""
        result = self.db.table("purchase_items").insert({
            "purchase_id": entity_id,
            "part_id": payload.get("part_id"),
            "quantity": payload.get("quantity", 1)
        }).execute()

        return {"added": True}

    async def _prepare_approve_purchase(self, entity_id: str, yacht_id: str, payload: Dict) -> Dict:
        """Prepare approving purchase"""
        current = self.db.table("purchases").select(
            "id, status"
        ).eq("id", entity_id).single().execute()

        if not current.data:
            raise ValueError(f"Purchase not found: {entity_id}")

        if current.data["status"] != "pending_approval":
            raise ValueError(f"Purchase cannot be approved from status: {current.data['status']}")

        return {
            "before": {"status": current.data["status"]},
            "after": {"status": "approved"},
            "changes": [{"field": "status", "from": "pending_approval", "to": "approved"}]
        }

    async def _commit_approve_purchase(
        self, entity_id: str, yacht_id: str, payload: Dict, diff: Dict, user_id: str
    ) -> Dict:
        """Commit approving purchase"""
        self.db.table("purchases").update({
            "status": "approved",
            "approved_by": user_id,
            "approved_at": datetime.now(timezone.utc).isoformat()
        }).eq("id", entity_id).execute()

        return {"approved": True}

    async def _prepare_upload_invoice(self, entity_id: str, yacht_id: str, payload: Dict) -> Dict:
        """Prepare uploading invoice"""
        return {
            "before": {"invoice": None},
            "after": {"invoice": payload.get("filename")},
            "changes": [{"action": "upload_invoice"}]
        }

    async def _commit_upload_invoice(
        self, entity_id: str, yacht_id: str, payload: Dict, diff: Dict, user_id: str
    ) -> Dict:
        """Commit uploading invoice"""
        result = self.db.table("attachments").insert({
            "entity_type": "purchase",
            "entity_id": entity_id,
            "filename": payload.get("filename"),
            "mime_type": payload.get("mime_type", "application/pdf"),
            "storage_path": payload.get("storage_path"),
            "category": "invoice",
            "uploaded_by": user_id,
            "uploaded_at": datetime.now(timezone.utc).isoformat()
        }).execute()

        return {"uploaded": True}

    async def _prepare_log_delivery(self, entity_id: str, yacht_id: str, payload: Dict) -> Dict:
        """Prepare logging delivery received"""
        return {
            "before": {"status": "shipped"},
            "after": {"status": "delivered"},
            "changes": [{"field": "status", "to": "delivered"}]
        }

    async def _commit_log_delivery(
        self, entity_id: str, yacht_id: str, payload: Dict, diff: Dict, user_id: str
    ) -> Dict:
        """Commit logging delivery received"""
        self.db.table("purchases").update({
            "status": "delivered",
            "delivered_at": datetime.now(timezone.utc).isoformat(),
            "received_by": user_id
        }).eq("id", entity_id).execute()

        return {"logged": True, "status": "delivered"}

    async def _prepare_update_purchase_status(self, entity_id: str, yacht_id: str, payload: Dict) -> Dict:
        """Prepare updating purchase status"""
        # SECURITY FIX P0-004: Add yacht_id filter for tenant isolation
        current = self.db.table("purchases").select("status").eq("id", entity_id).eq("yacht_id", yacht_id).single().execute()

        return {
            "before": {"status": current.data["status"] if current.data else None},
            "after": {"status": payload.get("status")},
            "changes": [{"field": "status", "to": payload.get("status")}]
        }

    async def _commit_update_purchase_status(
        self, entity_id: str, yacht_id: str, payload: Dict, diff: Dict, user_id: str
    ) -> Dict:
        """Commit updating purchase status"""
        self.db.table("purchases").update({
            "status": payload["status"],
            "updated_at": datetime.now(timezone.utc).isoformat()
        }).eq("id", entity_id).execute()

        return {"updated": True}

    # =========================================================================
    # MUTATE HANDLERS - Checklists Domain
    # =========================================================================

    async def _prepare_mark_checklist_done(self, entity_id: str, yacht_id: str, payload: Dict) -> Dict:
        """Prepare marking checklist item complete"""
        current = self.db.table("checklist_items").select(
            "id, is_completed"
        ).eq("id", entity_id).single().execute()

        return {
            "before": {"is_completed": current.data["is_completed"] if current.data else False},
            "after": {"is_completed": True},
            "changes": [{"field": "is_completed", "to": True}]
        }

    async def _commit_mark_checklist_done(
        self, entity_id: str, yacht_id: str, payload: Dict, diff: Dict, user_id: str
    ) -> Dict:
        """Commit marking checklist item complete"""
        self.db.table("checklist_items").update({
            "is_completed": True,
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "completed_by": user_id
        }).eq("id", entity_id).execute()

        return {"marked": True}

    async def _prepare_add_checklist_note(self, entity_id: str, yacht_id: str, payload: Dict) -> Dict:
        """Prepare adding note to checklist item"""
        return {
            "before": {"notes": "existing"},
            "after": {"note": payload.get("note", "")},
            "changes": [{"action": "add_note"}]
        }

    async def _commit_add_checklist_note(
        self, entity_id: str, yacht_id: str, payload: Dict, diff: Dict, user_id: str
    ) -> Dict:
        """Commit adding note to checklist item"""
        # Append to existing notes or create new
        # SECURITY FIX P0-004: Add yacht_id filter for tenant isolation
        current = self.db.table("checklist_items").select("notes").eq("id", entity_id).eq("yacht_id", yacht_id).single().execute()
        existing_notes = current.data.get("notes", "") if current.data else ""
        new_notes = f"{existing_notes}\n[{datetime.now(timezone.utc).isoformat()}] {payload.get('note', '')}"

        # SECURITY FIX P0-004: Add yacht_id filter for tenant isolation
        self.db.table("checklist_items").update({
            "notes": new_notes.strip()
        }).eq("id", entity_id).eq("yacht_id", yacht_id).execute()

        return {"added": True}

    async def _prepare_add_checklist_photo(self, entity_id: str, yacht_id: str, payload: Dict) -> Dict:
        """Prepare adding photo to checklist item"""
        return {
            "before": {"attachments": "existing"},
            "after": {"attachment": payload.get("filename", "photo")},
            "changes": [{"action": "add_photo"}]
        }

    async def _commit_add_checklist_photo(
        self, entity_id: str, yacht_id: str, payload: Dict, diff: Dict, user_id: str
    ) -> Dict:
        """Commit adding photo to checklist item"""
        result = self.db.table("attachments").insert({
            "entity_type": "checklist_item",
            "entity_id": entity_id,
            "filename": payload.get("filename"),
            "mime_type": payload.get("mime_type", "image/jpeg"),
            "storage_path": payload.get("storage_path"),
            "uploaded_by": user_id,
            "uploaded_at": datetime.now(timezone.utc).isoformat()
        }).execute()

        return {"uploaded": True}

    # =========================================================================
    # MUTATE HANDLERS - Shipyard Domain
    # =========================================================================

    async def _prepare_add_worklist_task(self, entity_id: str, yacht_id: str, payload: Dict) -> Dict:
        """Prepare adding task to worklist"""
        return {
            "before": {"tasks": "existing"},
            "after": {"task": payload},
            "changes": [{"action": "add_task"}]
        }

    async def _commit_add_worklist_task(
        self, entity_id: str, yacht_id: str, payload: Dict, diff: Dict, user_id: str
    ) -> Dict:
        """Commit adding task to worklist"""
        result = self.db.table("worklist_items").insert({
            "worklist_id": entity_id,
            "title": payload.get("title"),
            "description": payload.get("description", ""),
            "priority": payload.get("priority", "normal"),
            "status": "pending",
            "created_at": datetime.now(timezone.utc).isoformat()
        }).execute()

        return {"added": True, "task_id": result.data[0]["id"] if result.data else None}

    async def _prepare_update_worklist(self, entity_id: str, yacht_id: str, payload: Dict) -> Dict:
        """Prepare updating worklist progress"""
        current = self.db.table("worklist_items").select(
            "id, progress_percent"
        ).eq("id", entity_id).single().execute()

        return {
            "before": {"progress": current.data.get("progress_percent", 0) if current.data else 0},
            "after": {"progress": payload.get("progress", 0)},
            "changes": [{"field": "progress", "to": payload.get("progress")}]
        }

    async def _commit_update_worklist(
        self, entity_id: str, yacht_id: str, payload: Dict, diff: Dict, user_id: str
    ) -> Dict:
        """Commit updating worklist progress"""
        self.db.table("worklist_items").update({
            "progress_percent": payload.get("progress", 0),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }).eq("id", entity_id).execute()

        return {"updated": True}

    async def _prepare_tag_survey(self, entity_id: str, yacht_id: str, payload: Dict) -> Dict:
        """Prepare tagging for survey"""
        return {
            "before": {"survey_tag": None},
            "after": {"survey_tag": payload.get("survey_type", "class")},
            "changes": [{"action": "tag_for_survey"}]
        }

    async def _commit_tag_survey(
        self, entity_id: str, yacht_id: str, payload: Dict, diff: Dict, user_id: str
    ) -> Dict:
        """Commit tagging for survey"""
        result = self.db.table("survey_tags").insert({
            "entity_id": entity_id,
            "entity_type": payload.get("entity_type", "equipment"),
            "survey_type": payload.get("survey_type", "class"),
            "tagged_by": user_id,
            "tagged_at": datetime.now(timezone.utc).isoformat()
        }).execute()

        return {"tagged": True}

    # =========================================================================
    # MUTATE HANDLERS - Mobile Domain
    # =========================================================================

    async def _prepare_upload_photo(self, entity_id: str, yacht_id: str, payload: Dict) -> Dict:
        """Prepare uploading photo"""
        return {
            "before": {"attachments": "existing"},
            "after": {"attachment": payload.get("filename", "photo")},
            "changes": [{"action": "upload_photo"}]
        }

    async def _commit_upload_photo(
        self, entity_id: str, yacht_id: str, payload: Dict, diff: Dict, user_id: str
    ) -> Dict:
        """Commit uploading photo"""
        result = self.db.table("attachments").insert({
            "entity_type": payload.get("entity_type", "unknown"),
            "entity_id": entity_id,
            "filename": payload.get("filename"),
            "mime_type": payload.get("mime_type", "image/jpeg"),
            "storage_path": payload.get("storage_path"),
            "uploaded_by": user_id,
            "uploaded_at": datetime.now(timezone.utc).isoformat()
        }).execute()

        return {"uploaded": True, "attachment_id": result.data[0]["id"] if result.data else None}

    async def _prepare_voice_note(self, entity_id: str, yacht_id: str, payload: Dict) -> Dict:
        """Prepare recording voice note"""
        return {
            "before": {"voice_notes": "existing"},
            "after": {"voice_note": payload.get("filename", "recording")},
            "changes": [{"action": "record_voice_note"}]
        }

    async def _commit_voice_note(
        self, entity_id: str, yacht_id: str, payload: Dict, diff: Dict, user_id: str
    ) -> Dict:
        """Commit recording voice note"""
        result = self.db.table("attachments").insert({
            "entity_type": payload.get("entity_type", "unknown"),
            "entity_id": entity_id,
            "filename": payload.get("filename"),
            "mime_type": "audio/m4a",
            "storage_path": payload.get("storage_path"),
            "category": "voice_note",
            "transcription": payload.get("transcription"),
            "uploaded_by": user_id,
            "uploaded_at": datetime.now(timezone.utc).isoformat()
        }).execute()

        return {"recorded": True, "attachment_id": result.data[0]["id"] if result.data else None}

    # =========================================================================
    # AUDIT LOGGING
    # =========================================================================

    async def _log_audit(
        self,
        yacht_id: str,
        user_id: str,
        action_id: str,
        entity_id: str,
        entity_type: str,
        diff: Dict,
        signature: Optional[str] = None,
        signature_timestamp: Optional[datetime] = None
    ) -> None:
        """Log action to audit trail"""
        try:
            self.db.table("audit_log").insert({
                "yacht_id": yacht_id,
                "user_id": user_id,
                "action": action_id,
                "entity_type": entity_type,
                "entity_id": entity_id,
                "old_values": diff.get("before"),
                "new_values": diff.get("after"),
                "changes": diff.get("changes"),
                "signature": signature,
                "signature_at": signature_timestamp.isoformat() if signature_timestamp else None,
                "created_at": datetime.now(timezone.utc).isoformat()
            }).execute()
        except Exception as e:
            logger.error(f"Failed to log audit: {e}")


# =============================================================================
# SINGLETON INSTANCE
# =============================================================================

_executor: Optional[ActionExecutor] = None


def get_executor(supabase_client=None) -> ActionExecutor:
    """Get singleton executor instance"""
    global _executor
    if _executor is None:
        if supabase_client is None:
            raise ValueError("Supabase client required for first initialization")
        _executor = ActionExecutor(supabase_client)
        logger.info("ActionExecutor initialized")
    return _executor


# =============================================================================
# MODULE TEST
# =============================================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    print("=" * 60)
    print("ACTION EXECUTOR")
    print("=" * 60)

    # List handlers
    executor = ActionExecutor(None)  # No DB for listing

    print("\n--- READ Handlers ---")
    for action_id in sorted(executor._read_handlers.keys()):
        print(f"  {action_id}")
    print(f"\nTotal READ handlers: {len(executor._read_handlers)}")

    print("\n--- MUTATE Handlers ---")
    for action_id in sorted(executor._mutate_handlers.keys()):
        print(f"  {action_id}")
    print(f"\nTotal MUTATE handlers: {len(executor._mutate_handlers)}")

    print(f"\nTotal handlers: {len(executor._read_handlers) + len(executor._mutate_handlers)}")
