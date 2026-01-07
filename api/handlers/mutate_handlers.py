"""
MUTATE Domain Handlers
======================

Group 7: All MUTATE handlers across domains.

Flow: prepare → sign → commit
1. prepare: Validate inputs, generate preview
2. sign: User confirms (signature for critical actions)
3. commit: Execute the mutation

Domains:
- Equipment: create_work_order, log_equipment_hours
- Inventory: edit_inventory_quantity, log_part_usage, create_reorder
- Work Orders: update_work_order_status, mark_work_order_complete, assign_work_order, add_work_order_note/photo
- Faults: resolve_fault, create_fault, acknowledge_fault
- Documents: add_to_handover
- Hours of Rest: log_rest_hours
- Checklists: toggle_checklist_item, complete_checklist

All handlers return standardized ActionResponseEnvelope with mutation-specific fields.
"""

from datetime import datetime, timezone
from typing import Dict, Optional, List, Tuple
import logging
import uuid

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from action_response_schema import (
    ResponseBuilder,
    AvailableAction,
    MutationState,
    MutationPreview
)

from .schema_mapping import (
    get_table,
    map_equipment_select, normalize_equipment,
    map_work_order_select, normalize_work_order,
    map_parts_select, normalize_part,
    map_faults_select, normalize_fault
)

logger = logging.getLogger(__name__)


class MutationContext:
    """Context for tracking mutation state through prepare/commit flow."""

    # In-memory store for pending mutations (would use Redis in production)
    _pending: Dict[str, Dict] = {}

    @classmethod
    def store_pending(cls, mutation_id: str, data: Dict) -> None:
        """Store pending mutation for later commit."""
        cls._pending[mutation_id] = {
            **data,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "expires_at": (datetime.now(timezone.utc).replace(second=0, microsecond=0)).isoformat()
        }

    @classmethod
    def get_pending(cls, mutation_id: str) -> Optional[Dict]:
        """Retrieve pending mutation."""
        return cls._pending.get(mutation_id)

    @classmethod
    def remove_pending(cls, mutation_id: str) -> None:
        """Remove completed/expired mutation."""
        cls._pending.pop(mutation_id, None)


# =========================================================================
# EQUIPMENT MUTATE HANDLERS
# =========================================================================

class EquipmentMutateHandlers:
    """Equipment domain MUTATE handlers."""

    def __init__(self, supabase_client):
        self.db = supabase_client

    async def create_work_order(
        self,
        entity_id: str,
        yacht_id: str,
        params: Optional[Dict] = None,
        commit: bool = False,
        mutation_id: Optional[str] = None
    ) -> Dict:
        """
        Create work order for equipment.

        Params:
        - title: Work order title
        - description: Description
        - priority: low/medium/high/urgent
        - due_date: Optional due date
        - assigned_to: Optional crew member ID

        Returns (prepare):
        - Preview of work order to be created
        - mutation_id for commit

        Returns (commit):
        - Created work order ID
        - Success confirmation
        """
        builder = ResponseBuilder("create_work_order", entity_id, "equipment", yacht_id)

        try:
            params = params or {}

            if not commit:
                # PREPARE phase
                return await self._prepare_create_work_order(builder, entity_id, yacht_id, params)
            else:
                # COMMIT phase
                return await self._commit_create_work_order(builder, entity_id, yacht_id, params, mutation_id)

        except Exception as e:
            logger.error(f"create_work_order failed: {e}", exc_info=True)
            builder.set_error("INTERNAL_ERROR", str(e))
            return builder.build()

    async def _prepare_create_work_order(
        self,
        builder: ResponseBuilder,
        entity_id: str,
        yacht_id: str,
        params: Dict
    ) -> Dict:
        """Prepare work order creation."""
        # Validate required params
        title = params.get("title")
        if not title:
            builder.set_error("VALIDATION_ERROR", "Title is required")
            return builder.build()

        # Get equipment info
        equip_result = self.db.table(get_table("equipment")).select(
            map_equipment_select()
        ).eq("id", entity_id).maybe_single().execute()

        if not equip_result or not equip_result.data:
            builder.set_error("NOT_FOUND", f"Equipment not found: {entity_id}")
            return builder.build()

        equipment = normalize_equipment(equip_result.data)

        # Generate mutation ID
        mutation_id = str(uuid.uuid4())

        # Build preview
        preview = {
            "title": title,
            "description": params.get("description", ""),
            "priority": params.get("priority", "medium"),
            "due_date": params.get("due_date"),
            "equipment": {
                "id": entity_id,
                "name": equipment.get("canonical_label")
            },
            "assigned_to": params.get("assigned_to"),
            "status": "open"
        }

        # Store pending mutation
        MutationContext.store_pending(mutation_id, {
            "action": "create_work_order",
            "entity_id": entity_id,
            "yacht_id": yacht_id,
            "params": params,
            "preview": preview
        })

        builder.set_mutation_preview(MutationPreview(
            mutation_id=mutation_id,
            action="create_work_order",
            changes=[
                {"field": "title", "value": title},
                {"field": "priority", "value": params.get("priority", "medium")},
                {"field": "equipment_id", "value": entity_id}
            ],
            requires_signature=params.get("priority") in ("high", "urgent"),
            confirmation_message=f"Create work order '{title}' for {equipment.get('canonical_label')}?"
        ))

        builder.set_data({
            "preview": preview,
            "state": "pending_confirmation"
        })

        return builder.build()

    async def _commit_create_work_order(
        self,
        builder: ResponseBuilder,
        entity_id: str,
        yacht_id: str,
        params: Dict,
        mutation_id: str
    ) -> Dict:
        """Commit work order creation."""
        # Verify pending mutation
        pending = MutationContext.get_pending(mutation_id)
        if not pending:
            builder.set_error("INVALID_MUTATION", "Mutation expired or not found")
            return builder.build()

        try:
            # Create work order
            wo_data = {
                "id": str(uuid.uuid4()),
                "yacht_id": yacht_id,
                "equipment_id": entity_id,
                "title": params.get("title"),
                "description": params.get("description", ""),
                "priority": params.get("priority", "medium"),
                "status": "open",
                "due_date": params.get("due_date"),
                "assigned_to": params.get("assigned_to"),
                "created_at": datetime.now(timezone.utc).isoformat(),
                "created_by": params.get("user_id")
            }

            result = self.db.table(get_table("work_orders")).insert(wo_data).execute()

            if result.data:
                MutationContext.remove_pending(mutation_id)

                builder.set_data({
                    "work_order_id": wo_data["id"],
                    "title": wo_data["title"],
                    "status": "created",
                    "message": f"Work order '{wo_data['title']}' created successfully"
                })

                # Add follow-up action
                builder.add_available_action(AvailableAction(
                    action_id="view_work_order",
                    label="View Work Order",
                    variant="READ",
                    icon="eye"
                ))
            else:
                builder.set_error("CREATE_FAILED", "Failed to create work order")

        except Exception as e:
            builder.set_error("COMMIT_FAILED", str(e))

        return builder.build()

    async def log_equipment_hours(
        self,
        entity_id: str,
        yacht_id: str,
        params: Optional[Dict] = None,
        commit: bool = False,
        mutation_id: Optional[str] = None
    ) -> Dict:
        """
        Log equipment running hours.

        Params:
        - hours: New hour reading
        - notes: Optional notes

        Returns:
        - Updated run_hours
        """
        builder = ResponseBuilder("log_equipment_hours", entity_id, "equipment", yacht_id)

        try:
            params = params or {}
            hours = params.get("hours")

            if hours is None:
                builder.set_error("VALIDATION_ERROR", "Hours reading is required")
                return builder.build()

            if not commit:
                # PREPARE
                equip_result = self.db.table(get_table("equipment")).select(
                    map_equipment_select()
                ).eq("id", entity_id).maybe_single().execute()

                if not equip_result or not equip_result.data:
                    builder.set_error("NOT_FOUND", f"Equipment not found: {entity_id}")
                    return builder.build()

                equipment = normalize_equipment(equip_result.data)
                current_hours = equipment.get("run_hours", 0) or 0

                if hours < current_hours:
                    builder.set_error(
                        "VALIDATION_ERROR",
                        f"New reading ({hours}) cannot be less than current ({current_hours})"
                    )
                    return builder.build()

                mutation_id = str(uuid.uuid4())
                MutationContext.store_pending(mutation_id, {
                    "action": "log_equipment_hours",
                    "entity_id": entity_id,
                    "hours": hours
                })

                builder.set_mutation_preview(MutationPreview(
                    mutation_id=mutation_id,
                    action="log_equipment_hours",
                    changes=[
                        {"field": "run_hours", "from": current_hours, "to": hours}
                    ],
                    requires_signature=True,
                    confirmation_message=f"Update {equipment.get('canonical_label')} hours from {current_hours} to {hours}?"
                ))

                builder.set_data({
                    "equipment_name": equipment.get("canonical_label"),
                    "current_hours": current_hours,
                    "new_hours": hours,
                    "delta": hours - current_hours,
                    "state": "pending_confirmation"
                })

            else:
                # COMMIT
                pending = MutationContext.get_pending(mutation_id)
                if not pending:
                    builder.set_error("INVALID_MUTATION", "Mutation expired or not found")
                    return builder.build()

                result = self.db.table(get_table("equipment")).update({
                    "run_hours": hours,
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }).eq("id", entity_id).execute()

                if result.data:
                    MutationContext.remove_pending(mutation_id)
                    builder.set_data({
                        "equipment_id": entity_id,
                        "run_hours": hours,
                        "status": "updated",
                        "message": "Equipment hours updated successfully"
                    })
                else:
                    builder.set_error("UPDATE_FAILED", "Failed to update equipment hours")

            return builder.build()

        except Exception as e:
            logger.error(f"log_equipment_hours failed: {e}", exc_info=True)
            builder.set_error("INTERNAL_ERROR", str(e))
            return builder.build()


# =========================================================================
# INVENTORY MUTATE HANDLERS
# =========================================================================

class InventoryMutateHandlers:
    """Inventory domain MUTATE handlers."""

    def __init__(self, supabase_client):
        self.db = supabase_client

    async def edit_inventory_quantity(
        self,
        entity_id: str,
        yacht_id: str,
        params: Optional[Dict] = None,
        commit: bool = False,
        mutation_id: Optional[str] = None
    ) -> Dict:
        """
        Adjust inventory quantity.

        Params:
        - quantity: New quantity OR
        - adjustment: +/- delta
        - reason: Reason for adjustment
        """
        builder = ResponseBuilder("edit_inventory_quantity", entity_id, "part", yacht_id)

        try:
            params = params or {}

            # Get current part
            part_result = self.db.table(get_table("parts")).select(
                map_parts_select()
            ).eq("id", entity_id).maybe_single().execute()

            if not part_result or not part_result.data:
                builder.set_error("NOT_FOUND", f"Part not found: {entity_id}")
                return builder.build()

            part = normalize_part(part_result.data)
            # Note: quantity field not in current schema - defaults to 0
            current_qty = part.get("quantity", 0) or 0

            # Calculate new quantity
            if "quantity" in params:
                new_qty = params["quantity"]
            elif "adjustment" in params:
                new_qty = current_qty + params["adjustment"]
            else:
                builder.set_error("VALIDATION_ERROR", "Provide quantity or adjustment")
                return builder.build()

            if new_qty < 0:
                builder.set_error("VALIDATION_ERROR", "Quantity cannot be negative")
                return builder.build()

            if not commit:
                # PREPARE
                mutation_id = str(uuid.uuid4())
                MutationContext.store_pending(mutation_id, {
                    "action": "edit_inventory_quantity",
                    "entity_id": entity_id,
                    "new_qty": new_qty,
                    "reason": params.get("reason")
                })

                builder.set_mutation_preview(MutationPreview(
                    mutation_id=mutation_id,
                    action="edit_inventory_quantity",
                    changes=[
                        {"field": "quantity", "from": current_qty, "to": new_qty}
                    ],
                    requires_signature=True,
                    confirmation_message=f"Adjust {part.get('canonical_name')} from {current_qty} to {new_qty} {part.get('unit', 'units')}?"
                ))

                builder.set_data({
                    "part_name": part.get("canonical_name"),
                    "current_quantity": current_qty,
                    "new_quantity": new_qty,
                    "delta": new_qty - current_qty,
                    "unit": part.get("unit", "units"),
                    "state": "pending_confirmation"
                })

            else:
                # COMMIT
                pending = MutationContext.get_pending(mutation_id)
                if not pending:
                    builder.set_error("INVALID_MUTATION", "Mutation expired or not found")
                    return builder.build()

                # Update quantity
                self.db.table(get_table("parts")).update({
                    "quantity": new_qty,
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }).eq("id", entity_id).execute()

                # Log transaction
                try:
                    self.db.table("stock_transactions").insert({
                        "id": str(uuid.uuid4()),
                        "part_id": entity_id,
                        "yacht_id": yacht_id,
                        "transaction_type": "adjustment",
                        "quantity": new_qty - current_qty,
                        "notes": params.get("reason"),
                        "created_at": datetime.now(timezone.utc).isoformat()
                    }).execute()
                except Exception:
                    pass  # Transaction log is optional

                MutationContext.remove_pending(mutation_id)
                builder.set_data({
                    "part_id": entity_id,
                    "quantity": new_qty,
                    "status": "updated",
                    "message": f"Quantity updated to {new_qty}"
                })

            return builder.build()

        except Exception as e:
            logger.error(f"edit_inventory_quantity failed: {e}", exc_info=True)
            builder.set_error("INTERNAL_ERROR", str(e))
            return builder.build()

    async def log_part_usage(
        self,
        entity_id: str,
        yacht_id: str,
        params: Optional[Dict] = None,
        commit: bool = False,
        mutation_id: Optional[str] = None
    ) -> Dict:
        """
        Log part usage (decrement stock).

        Params:
        - quantity_used: Amount used
        - work_order_id: Optional linked work order
        """
        builder = ResponseBuilder("log_part_usage", entity_id, "part", yacht_id)

        try:
            params = params or {}
            qty_used = params.get("quantity_used", 1)

            if qty_used <= 0:
                builder.set_error("VALIDATION_ERROR", "Quantity must be positive")
                return builder.build()

            # Get current stock
            part_result = self.db.table(get_table("parts")).select(
                map_parts_select()
            ).eq("id", entity_id).maybe_single().execute()

            if not part_result or not part_result.data:
                builder.set_error("NOT_FOUND", f"Part not found: {entity_id}")
                return builder.build()

            part = normalize_part(part_result.data)
            current_qty = part.get("quantity", 0) or 0

            if qty_used > current_qty:
                builder.set_error(
                    "INSUFFICIENT_STOCK",
                    f"Cannot use {qty_used}, only {current_qty} available"
                )
                return builder.build()

            new_qty = current_qty - qty_used

            if not commit:
                mutation_id = str(uuid.uuid4())
                MutationContext.store_pending(mutation_id, {
                    "action": "log_part_usage",
                    "entity_id": entity_id,
                    "qty_used": qty_used,
                    "work_order_id": params.get("work_order_id")
                })

                builder.set_mutation_preview(MutationPreview(
                    mutation_id=mutation_id,
                    action="log_part_usage",
                    changes=[
                        {"field": "quantity", "from": current_qty, "to": new_qty}
                    ],
                    requires_signature=False,
                    confirmation_message=f"Log usage of {qty_used} {part.get('unit', 'units')} of {part.get('canonical_name')}?"
                ))

                builder.set_data({
                    "part_name": part.get("canonical_name"),
                    "quantity_used": qty_used,
                    "remaining": new_qty,
                    "state": "pending_confirmation"
                })

            else:
                pending = MutationContext.get_pending(mutation_id)
                if not pending:
                    builder.set_error("INVALID_MUTATION", "Mutation expired or not found")
                    return builder.build()

                # Update quantity
                self.db.table(get_table("parts")).update({
                    "quantity": new_qty,
                    "last_used_at": datetime.now(timezone.utc).isoformat()
                }).eq("id", entity_id).execute()

                # Log usage
                if params.get("work_order_id"):
                    try:
                        self.db.table("work_order_parts").insert({
                            "id": str(uuid.uuid4()),
                            "work_order_id": params["work_order_id"],
                            "part_id": entity_id,
                            "quantity_used": qty_used,
                            "used_at": datetime.now(timezone.utc).isoformat()
                        }).execute()
                    except Exception:
                        pass

                MutationContext.remove_pending(mutation_id)
                builder.set_data({
                    "part_id": entity_id,
                    "quantity_used": qty_used,
                    "remaining": new_qty,
                    "status": "logged",
                    "message": f"Logged usage of {qty_used} {part.get('unit', 'units')}"
                })

            return builder.build()

        except Exception as e:
            logger.error(f"log_part_usage failed: {e}", exc_info=True)
            builder.set_error("INTERNAL_ERROR", str(e))
            return builder.build()

    async def create_reorder(
        self,
        entity_id: str,
        yacht_id: str,
        params: Optional[Dict] = None,
        commit: bool = False,
        mutation_id: Optional[str] = None
    ) -> Dict:
        """
        Create reorder/purchase request for part.

        Params:
        - quantity: Amount to order
        - supplier: Optional supplier override
        - notes: Optional notes
        """
        builder = ResponseBuilder("create_reorder", entity_id, "part", yacht_id)

        try:
            params = params or {}

            # Get part info
            part_result = self.db.table(get_table("parts")).select(
                map_parts_select()
            ).eq("id", entity_id).maybe_single().execute()

            if not part_result or not part_result.data:
                builder.set_error("NOT_FOUND", f"Part not found: {entity_id}")
                return builder.build()

            part = normalize_part(part_result.data)

            # Calculate suggested quantity
            current = part.get("quantity", 0) or 0
            min_qty = part.get("min_quantity", 0) or 0
            suggested_qty = max(min_qty * 2 - current, min_qty)
            order_qty = params.get("quantity", suggested_qty)

            if not commit:
                mutation_id = str(uuid.uuid4())
                MutationContext.store_pending(mutation_id, {
                    "action": "create_reorder",
                    "entity_id": entity_id,
                    "quantity": order_qty,
                    "supplier": params.get("supplier", part.get("supplier"))
                })

                estimated_cost = order_qty * (part.get("unit_cost", 0) or 0)

                builder.set_mutation_preview(MutationPreview(
                    mutation_id=mutation_id,
                    action="create_reorder",
                    changes=[
                        {"field": "reorder_quantity", "value": order_qty},
                        {"field": "estimated_cost", "value": estimated_cost}
                    ],
                    requires_signature=True,
                    confirmation_message=f"Create purchase request for {order_qty} x {part.get('canonical_name')}?"
                ))

                builder.set_data({
                    "part_name": part.get("canonical_name"),
                    "current_stock": current,
                    "order_quantity": order_qty,
                    "supplier": params.get("supplier", part.get("supplier")),
                    "estimated_cost": estimated_cost,
                    "state": "pending_confirmation"
                })

            else:
                pending = MutationContext.get_pending(mutation_id)
                if not pending:
                    builder.set_error("INVALID_MUTATION", "Mutation expired or not found")
                    return builder.build()

                # Create purchase order
                po_id = str(uuid.uuid4())
                po_number = f"PO-{datetime.now().strftime('%Y%m%d')}-{po_id[:8].upper()}"

                self.db.table("purchase_orders").insert({
                    "id": po_id,
                    "yacht_id": yacht_id,
                    "po_number": po_number,
                    "supplier": params.get("supplier", part.get("supplier")),
                    "status": "draft",
                    "total_amount": order_qty * (part.get("unit_cost", 0) or 0),
                    "created_at": datetime.now(timezone.utc).isoformat()
                }).execute()

                # Add line item
                self.db.table("purchase_order_items").insert({
                    "id": str(uuid.uuid4()),
                    "purchase_order_id": po_id,
                    "part_id": entity_id,
                    "quantity": order_qty,
                    "unit_price": part.get("unit_cost", 0)
                }).execute()

                MutationContext.remove_pending(mutation_id)
                builder.set_data({
                    "purchase_order_id": po_id,
                    "po_number": po_number,
                    "status": "created",
                    "message": f"Purchase order {po_number} created"
                })

                builder.add_available_action(AvailableAction(
                    action_id="track_delivery",
                    label="Track Order",
                    variant="READ",
                    icon="truck"
                ))

            return builder.build()

        except Exception as e:
            logger.error(f"create_reorder failed: {e}", exc_info=True)
            builder.set_error("INTERNAL_ERROR", str(e))
            return builder.build()


# =========================================================================
# WORK ORDER MUTATE HANDLERS
# =========================================================================

class WorkOrderMutateHandlers:
    """Work order domain MUTATE handlers."""

    # Actual DB statuses: planned, in_progress, completed
    STATUS_FLOW = {
        "planned": ["in_progress"],
        "in_progress": ["completed", "planned"],
        "completed": [],  # Terminal state
        "closed": [],
        "cancelled": [],
    }

    def __init__(self, supabase_client):
        self.db = supabase_client

    async def update_work_order_status(
        self,
        entity_id: str,
        yacht_id: str,
        params: Optional[Dict] = None,
        commit: bool = False,
        mutation_id: Optional[str] = None
    ) -> Dict:
        """
        Update work order status.

        Params:
        - status: New status
        """
        builder = ResponseBuilder("update_work_order_status", entity_id, "work_order", yacht_id)

        try:
            params = params or {}
            new_status = params.get("status")

            if not new_status:
                builder.set_error("VALIDATION_ERROR", "Status is required")
                return builder.build()

            # Get current WO
            wo_result = self.db.table(get_table("work_orders")).select(
                map_work_order_select()
            ).eq("id", entity_id).maybe_single().execute()

            if not wo_result or not wo_result.data:
                builder.set_error("NOT_FOUND", f"Work order not found: {entity_id}")
                return builder.build()

            wo = normalize_work_order(wo_result.data)
            current_status = wo.get("status")

            # Validate transition
            allowed = self.STATUS_FLOW.get(current_status, [])
            if new_status not in allowed:
                builder.set_error(
                    "INVALID_TRANSITION",
                    f"Cannot change from '{current_status}' to '{new_status}'. Allowed: {allowed}"
                )
                return builder.build()

            if not commit:
                mutation_id = str(uuid.uuid4())
                MutationContext.store_pending(mutation_id, {
                    "action": "update_work_order_status",
                    "entity_id": entity_id,
                    "new_status": new_status
                })

                builder.set_mutation_preview(MutationPreview(
                    mutation_id=mutation_id,
                    action="update_work_order_status",
                    changes=[
                        {"field": "status", "from": current_status, "to": new_status}
                    ],
                    requires_signature=new_status in ("completed", "closed"),
                    confirmation_message=f"Change status to '{new_status}'?"
                ))

                builder.set_data({
                    "work_order_title": wo.get("title"),
                    "current_status": current_status,
                    "new_status": new_status,
                    "state": "pending_confirmation"
                })

            else:
                pending = MutationContext.get_pending(mutation_id)
                if not pending:
                    builder.set_error("INVALID_MUTATION", "Mutation expired or not found")
                    return builder.build()

                update_data = {
                    "status": new_status,
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }

                if new_status == "completed":
                    update_data["completed_at"] = datetime.now(timezone.utc).isoformat()

                self.db.table(get_table("work_orders")).update(update_data).eq("id", entity_id).execute()

                MutationContext.remove_pending(mutation_id)
                builder.set_data({
                    "work_order_id": entity_id,
                    "status": new_status,
                    "message": f"Status updated to '{new_status}'"
                })

            return builder.build()

        except Exception as e:
            logger.error(f"update_work_order_status failed: {e}", exc_info=True)
            builder.set_error("INTERNAL_ERROR", str(e))
            return builder.build()

    async def mark_work_order_complete(
        self,
        entity_id: str,
        yacht_id: str,
        params: Optional[Dict] = None,
        commit: bool = False,
        mutation_id: Optional[str] = None
    ) -> Dict:
        """
        Mark work order as complete.

        Params:
        - resolution: Resolution notes
        """
        params = params or {}
        params["status"] = "completed"

        builder = ResponseBuilder("mark_work_order_complete", entity_id, "work_order", yacht_id)

        try:
            # Get WO for validation
            wo_result = self.db.table(get_table("work_orders")).select(
                map_work_order_select()
            ).eq("id", entity_id).maybe_single().execute()

            if not wo_result or not wo_result.data:
                builder.set_error("NOT_FOUND", f"Work order not found: {entity_id}")
                return builder.build()

            wo = normalize_work_order(wo_result.data)

            if wo.get("status") not in ("in_progress", "pending_parts"):
                builder.set_error(
                    "INVALID_STATE",
                    f"Cannot complete work order in '{wo.get('status')}' status"
                )
                return builder.build()

            if not commit:
                mutation_id = str(uuid.uuid4())
                MutationContext.store_pending(mutation_id, {
                    "action": "mark_work_order_complete",
                    "entity_id": entity_id,
                    "resolution": params.get("resolution")
                })

                builder.set_mutation_preview(MutationPreview(
                    mutation_id=mutation_id,
                    action="mark_work_order_complete",
                    changes=[
                        {"field": "status", "from": wo.get("status"), "to": "completed"},
                        {"field": "resolution", "value": params.get("resolution")}
                    ],
                    requires_signature=True,
                    confirmation_message=f"Mark '{wo.get('title')}' as complete?"
                ))

                builder.set_data({
                    "work_order_title": wo.get("title"),
                    "resolution": params.get("resolution"),
                    "state": "pending_confirmation"
                })

            else:
                pending = MutationContext.get_pending(mutation_id)
                if not pending:
                    builder.set_error("INVALID_MUTATION", "Mutation expired or not found")
                    return builder.build()

                self.db.table(get_table("work_orders")).update({
                    "status": "completed",
                    "resolution": params.get("resolution"),
                    "completed_at": datetime.now(timezone.utc).isoformat()
                }).eq("id", entity_id).execute()

                MutationContext.remove_pending(mutation_id)
                builder.set_data({
                    "work_order_id": entity_id,
                    "status": "completed",
                    "message": "Work order marked as complete"
                })

            return builder.build()

        except Exception as e:
            logger.error(f"mark_work_order_complete failed: {e}", exc_info=True)
            builder.set_error("INTERNAL_ERROR", str(e))
            return builder.build()

    async def assign_work_order(
        self,
        entity_id: str,
        yacht_id: str,
        params: Optional[Dict] = None,
        commit: bool = False,
        mutation_id: Optional[str] = None
    ) -> Dict:
        """
        Assign work order to crew member.

        Params:
        - assigned_to: Crew member ID
        """
        builder = ResponseBuilder("assign_work_order", entity_id, "work_order", yacht_id)

        try:
            params = params or {}
            assignee_id = params.get("assigned_to")

            if not assignee_id:
                builder.set_error("VALIDATION_ERROR", "Assignee is required")
                return builder.build()

            # Validate assignee
            crew_result = self.db.table("crew_members").select(
                "id, name"
            ).eq("id", assignee_id).maybe_single().execute()

            if not crew_result.data:
                builder.set_error("NOT_FOUND", f"Crew member not found: {assignee_id}")
                return builder.build()

            crew = crew_result.data

            # Get WO
            wo_result = self.db.table(get_table("work_orders")).select(
                map_work_order_select()
            ).eq("id", entity_id).maybe_single().execute()

            if not wo_result or not wo_result.data:
                builder.set_error("NOT_FOUND", f"Work order not found: {entity_id}")
                return builder.build()

            wo = normalize_work_order(wo_result.data)

            if not commit:
                mutation_id = str(uuid.uuid4())
                MutationContext.store_pending(mutation_id, {
                    "action": "assign_work_order",
                    "entity_id": entity_id,
                    "assigned_to": assignee_id
                })

                builder.set_mutation_preview(MutationPreview(
                    mutation_id=mutation_id,
                    action="assign_work_order",
                    changes=[
                        {"field": "assigned_to", "from": wo.get("assigned_to"), "to": assignee_id}
                    ],
                    requires_signature=False,
                    confirmation_message=f"Assign '{wo.get('title')}' to {crew.get('name')}?"
                ))

                builder.set_data({
                    "work_order_title": wo.get("title"),
                    "assignee_name": crew.get("name"),
                    "state": "pending_confirmation"
                })

            else:
                pending = MutationContext.get_pending(mutation_id)
                if not pending:
                    builder.set_error("INVALID_MUTATION", "Mutation expired or not found")
                    return builder.build()

                self.db.table(get_table("work_orders")).update({
                    "assigned_to": assignee_id,
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }).eq("id", entity_id).execute()

                MutationContext.remove_pending(mutation_id)
                builder.set_data({
                    "work_order_id": entity_id,
                    "assigned_to": assignee_id,
                    "assignee_name": crew.get("name"),
                    "message": f"Assigned to {crew.get('name')}"
                })

            return builder.build()

        except Exception as e:
            logger.error(f"assign_work_order failed: {e}", exc_info=True)
            builder.set_error("INTERNAL_ERROR", str(e))
            return builder.build()

    async def add_work_order_note(
        self,
        entity_id: str,
        yacht_id: str,
        params: Optional[Dict] = None,
        commit: bool = False,
        mutation_id: Optional[str] = None
    ) -> Dict:
        """
        Add note to work order.

        Params:
        - note: Note content
        """
        builder = ResponseBuilder("add_work_order_note", entity_id, "work_order", yacht_id)

        try:
            params = params or {}
            note = params.get("note")

            if not note:
                builder.set_error("VALIDATION_ERROR", "Note content is required")
                return builder.build()

            if not commit:
                mutation_id = str(uuid.uuid4())
                MutationContext.store_pending(mutation_id, {
                    "action": "add_work_order_note",
                    "entity_id": entity_id,
                    "note": note
                })

                builder.set_mutation_preview(MutationPreview(
                    mutation_id=mutation_id,
                    action="add_work_order_note",
                    changes=[
                        {"field": "note", "value": note[:100] + "..." if len(note) > 100 else note}
                    ],
                    requires_signature=False,
                    confirmation_message="Add this note?"
                ))

                builder.set_data({
                    "note_preview": note[:200],
                    "state": "pending_confirmation"
                })

            else:
                pending = MutationContext.get_pending(mutation_id)
                if not pending:
                    builder.set_error("INVALID_MUTATION", "Mutation expired or not found")
                    return builder.build()

                note_id = str(uuid.uuid4())
                self.db.table("work_order_notes").insert({
                    "id": note_id,
                    "work_order_id": entity_id,
                    "content": note,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "created_by": params.get("user_id")
                }).execute()

                MutationContext.remove_pending(mutation_id)
                builder.set_data({
                    "note_id": note_id,
                    "status": "added",
                    "message": "Note added successfully"
                })

            return builder.build()

        except Exception as e:
            logger.error(f"add_work_order_note failed: {e}", exc_info=True)
            builder.set_error("INTERNAL_ERROR", str(e))
            return builder.build()


# =========================================================================
# FAULT MUTATE HANDLERS
# =========================================================================

class FaultMutateHandlers:
    """Fault domain MUTATE handlers."""

    def __init__(self, supabase_client):
        self.db = supabase_client

    async def resolve_fault(
        self,
        entity_id: str,
        yacht_id: str,
        params: Optional[Dict] = None,
        commit: bool = False,
        mutation_id: Optional[str] = None
    ) -> Dict:
        """
        Resolve/close fault.

        Params:
        - resolution: Resolution notes
        - work_order_id: Optional linked work order
        """
        builder = ResponseBuilder("resolve_fault", entity_id, "fault", yacht_id)

        try:
            params = params or {}

            # Get fault
            fault_result = self.db.table(get_table("faults")).select(
                map_faults_select()
            ).eq("id", entity_id).maybe_single().execute()

            if not fault_result or not fault_result.data:
                builder.set_error("NOT_FOUND", f"Fault not found: {entity_id}")
                return builder.build()

            fault = normalize_fault(fault_result.data)

            if fault.get("is_resolved"):
                builder.set_error("ALREADY_RESOLVED", "Fault is already resolved")
                return builder.build()

            if not commit:
                mutation_id = str(uuid.uuid4())
                MutationContext.store_pending(mutation_id, {
                    "action": "resolve_fault",
                    "entity_id": entity_id,
                    "resolution": params.get("resolution")
                })

                builder.set_mutation_preview(MutationPreview(
                    mutation_id=mutation_id,
                    action="resolve_fault",
                    changes=[
                        {"field": "is_resolved", "from": False, "to": True},
                        {"field": "resolution", "value": params.get("resolution")}
                    ],
                    requires_signature=True,
                    confirmation_message=f"Resolve fault {fault.get('fault_code')}?"
                ))

                builder.set_data({
                    "fault_code": fault.get("fault_code"),
                    "description": fault.get("description"),
                    "resolution": params.get("resolution"),
                    "state": "pending_confirmation"
                })

            else:
                pending = MutationContext.get_pending(mutation_id)
                if not pending:
                    builder.set_error("INVALID_MUTATION", "Mutation expired or not found")
                    return builder.build()

                self.db.table(get_table("faults")).update({
                    "is_resolved": True,
                    "resolved_at": datetime.now(timezone.utc).isoformat(),
                    "resolution": params.get("resolution")
                }).eq("id", entity_id).execute()

                MutationContext.remove_pending(mutation_id)
                builder.set_data({
                    "fault_id": entity_id,
                    "status": "resolved",
                    "message": "Fault resolved successfully"
                })

            return builder.build()

        except Exception as e:
            logger.error(f"resolve_fault failed: {e}", exc_info=True)
            builder.set_error("INTERNAL_ERROR", str(e))
            return builder.build()

    async def create_fault(
        self,
        entity_id: str,
        yacht_id: str,
        params: Optional[Dict] = None,
        commit: bool = False,
        mutation_id: Optional[str] = None
    ) -> Dict:
        """
        Create new fault report.

        Params:
        - fault_code: Fault code
        - description: Description
        - severity: low/medium/high/critical
        - equipment_id: Related equipment (entity_id)
        """
        builder = ResponseBuilder("create_fault", entity_id, "equipment", yacht_id)

        try:
            params = params or {}
            fault_code = params.get("fault_code")
            description = params.get("description")
            severity = params.get("severity", "medium")

            if not description:
                builder.set_error("VALIDATION_ERROR", "Description is required")
                return builder.build()

            if not commit:
                # Generate fault code if not provided
                if not fault_code:
                    fault_code = f"FLT-{datetime.now().strftime('%Y%m%d%H%M%S')}"

                mutation_id = str(uuid.uuid4())
                MutationContext.store_pending(mutation_id, {
                    "action": "create_fault",
                    "entity_id": entity_id,
                    "fault_code": fault_code,
                    "description": description,
                    "severity": severity
                })

                builder.set_mutation_preview(MutationPreview(
                    mutation_id=mutation_id,
                    action="create_fault",
                    changes=[
                        {"field": "fault_code", "value": fault_code},
                        {"field": "severity", "value": severity}
                    ],
                    requires_signature=severity in ("high", "critical"),
                    confirmation_message=f"Report fault {fault_code}?"
                ))

                builder.set_data({
                    "fault_code": fault_code,
                    "description": description,
                    "severity": severity,
                    "equipment_id": entity_id,
                    "state": "pending_confirmation"
                })

            else:
                pending = MutationContext.get_pending(mutation_id)
                if not pending:
                    builder.set_error("INVALID_MUTATION", "Mutation expired or not found")
                    return builder.build()

                fault_id = str(uuid.uuid4())
                self.db.table(get_table("faults")).insert({
                    "id": fault_id,
                    "yacht_id": yacht_id,
                    "equipment_id": entity_id,
                    "fault_code": pending.get("fault_code"),
                    "description": pending.get("description"),
                    "severity": pending.get("severity"),
                    "is_resolved": False,
                    "created_at": datetime.now(timezone.utc).isoformat()
                }).execute()

                MutationContext.remove_pending(mutation_id)
                builder.set_data({
                    "fault_id": fault_id,
                    "fault_code": pending.get("fault_code"),
                    "status": "created",
                    "message": "Fault reported successfully"
                })

                builder.add_available_action(AvailableAction(
                    action_id="view_fault",
                    label="View Fault",
                    variant="READ",
                    icon="alert-triangle"
                ))

            return builder.build()

        except Exception as e:
            logger.error(f"create_fault failed: {e}", exc_info=True)
            builder.set_error("INTERNAL_ERROR", str(e))
            return builder.build()

    async def acknowledge_fault(
        self,
        entity_id: str,
        yacht_id: str,
        params: Optional[Dict] = None,
        commit: bool = False,
        mutation_id: Optional[str] = None
    ) -> Dict:
        """
        Acknowledge fault (mark as seen/being handled).

        Params:
        - notes: Optional acknowledgment notes
        """
        builder = ResponseBuilder("acknowledge_fault", entity_id, "fault", yacht_id)

        try:
            params = params or {}

            # Get fault
            fault_result = self.db.table(get_table("faults")).select(
                map_faults_select()
            ).eq("id", entity_id).maybe_single().execute()

            if not fault_result or not fault_result.data:
                builder.set_error("NOT_FOUND", f"Fault not found: {entity_id}")
                return builder.build()

            fault = normalize_fault(fault_result.data)

            # Note: acknowledged_at not in current schema, skip check

            if not commit:
                mutation_id = str(uuid.uuid4())
                MutationContext.store_pending(mutation_id, {
                    "action": "acknowledge_fault",
                    "entity_id": entity_id
                })

                builder.set_mutation_preview(MutationPreview(
                    mutation_id=mutation_id,
                    action="acknowledge_fault",
                    changes=[
                        {"field": "acknowledged", "value": True}
                    ],
                    requires_signature=False,
                    confirmation_message=f"Acknowledge fault {fault.get('fault_code')}?"
                ))

                builder.set_data({
                    "fault_code": fault.get("fault_code"),
                    "state": "pending_confirmation"
                })

            else:
                pending = MutationContext.get_pending(mutation_id)
                if not pending:
                    builder.set_error("INVALID_MUTATION", "Mutation expired or not found")
                    return builder.build()

                self.db.table(get_table("faults")).update({
                    "acknowledged_at": datetime.now(timezone.utc).isoformat(),
                    "acknowledged_by": params.get("user_id")
                }).eq("id", entity_id).execute()

                MutationContext.remove_pending(mutation_id)
                builder.set_data({
                    "fault_id": entity_id,
                    "status": "acknowledged",
                    "message": "Fault acknowledged"
                })

            return builder.build()

        except Exception as e:
            logger.error(f"acknowledge_fault failed: {e}", exc_info=True)
            builder.set_error("INTERNAL_ERROR", str(e))
            return builder.build()


# =========================================================================
# HOURS OF REST MUTATE HANDLERS
# =========================================================================

class HoursOfRestMutateHandlers:
    """Hours of rest domain MUTATE handlers."""

    def __init__(self, supabase_client):
        self.db = supabase_client

    async def log_rest_hours(
        self,
        entity_id: str,
        yacht_id: str,
        params: Optional[Dict] = None,
        commit: bool = False,
        mutation_id: Optional[str] = None
    ) -> Dict:
        """
        Log rest hours for crew member.

        Params:
        - date: Date (YYYY-MM-DD)
        - rest_hours: Hours of rest
        - work_hours: Hours worked
        - notes: Optional notes
        """
        builder = ResponseBuilder("log_rest_hours", entity_id, "crew_member", yacht_id)

        try:
            params = params or {}
            date = params.get("date", datetime.now(timezone.utc).date().isoformat())
            rest_hours = params.get("rest_hours")
            work_hours = params.get("work_hours")

            if rest_hours is None or work_hours is None:
                builder.set_error("VALIDATION_ERROR", "rest_hours and work_hours are required")
                return builder.build()

            # Validate hours
            if rest_hours + work_hours > 24:
                builder.set_error("VALIDATION_ERROR", "Total hours cannot exceed 24")
                return builder.build()

            # Check MLC compliance
            is_compliant = rest_hours >= 10 and work_hours <= 14

            if not commit:
                mutation_id = str(uuid.uuid4())
                MutationContext.store_pending(mutation_id, {
                    "action": "log_rest_hours",
                    "entity_id": entity_id,
                    "date": date,
                    "rest_hours": rest_hours,
                    "work_hours": work_hours,
                    "is_compliant": is_compliant
                })

                builder.set_mutation_preview(MutationPreview(
                    mutation_id=mutation_id,
                    action="log_rest_hours",
                    changes=[
                        {"field": "rest_hours", "value": rest_hours},
                        {"field": "work_hours", "value": work_hours},
                        {"field": "is_compliant", "value": is_compliant}
                    ],
                    requires_signature=True,
                    confirmation_message=f"Log {rest_hours}h rest, {work_hours}h work for {date}?"
                ))

                warning = None
                if not is_compliant:
                    warning = "This entry does not meet MLC compliance requirements"

                builder.set_data({
                    "date": date,
                    "rest_hours": rest_hours,
                    "work_hours": work_hours,
                    "is_compliant": is_compliant,
                    "warning": warning,
                    "state": "pending_confirmation"
                })

            else:
                pending = MutationContext.get_pending(mutation_id)
                if not pending:
                    builder.set_error("INVALID_MUTATION", "Mutation expired or not found")
                    return builder.build()

                # Upsert record
                record_id = str(uuid.uuid4())
                self.db.table("hours_of_rest").upsert({
                    "id": record_id,
                    "crew_member_id": entity_id,
                    "yacht_id": yacht_id,
                    "date": date,
                    "rest_hours": rest_hours,
                    "work_hours": work_hours,
                    "is_compliant": is_compliant,
                    "notes": params.get("notes"),
                    "created_at": datetime.now(timezone.utc).isoformat()
                }, on_conflict="crew_member_id,date").execute()

                MutationContext.remove_pending(mutation_id)
                builder.set_data({
                    "record_id": record_id,
                    "date": date,
                    "is_compliant": is_compliant,
                    "status": "logged",
                    "message": "Hours logged successfully"
                })

            return builder.build()

        except Exception as e:
            logger.error(f"log_rest_hours failed: {e}", exc_info=True)
            builder.set_error("INTERNAL_ERROR", str(e))
            return builder.build()


# =========================================================================
# CHECKLIST MUTATE HANDLERS
# =========================================================================

class ChecklistMutateHandlers:
    """Checklist domain MUTATE handlers."""

    def __init__(self, supabase_client):
        self.db = supabase_client

    async def toggle_checklist_item(
        self,
        entity_id: str,
        yacht_id: str,
        params: Optional[Dict] = None,
        commit: bool = False,
        mutation_id: Optional[str] = None
    ) -> Dict:
        """
        Toggle checklist item completion.

        Params:
        - item_id: Checklist item ID
        - notes: Optional notes
        """
        builder = ResponseBuilder("toggle_checklist_item", entity_id, "checklist", yacht_id)

        try:
            params = params or {}
            item_id = params.get("item_id")

            if not item_id:
                builder.set_error("VALIDATION_ERROR", "item_id is required")
                return builder.build()

            # Get item
            item_result = self.db.table("checklist_items").select(
                "id, description, is_completed, checklist_id"
            ).eq("id", item_id).maybe_single().execute()

            if not item_result.data:
                builder.set_error("NOT_FOUND", f"Checklist item not found: {item_id}")
                return builder.build()

            item = item_result.data
            new_state = not item.get("is_completed", False)

            if not commit:
                mutation_id = str(uuid.uuid4())
                MutationContext.store_pending(mutation_id, {
                    "action": "toggle_checklist_item",
                    "item_id": item_id,
                    "new_state": new_state
                })

                builder.set_mutation_preview(MutationPreview(
                    mutation_id=mutation_id,
                    action="toggle_checklist_item",
                    changes=[
                        {"field": "is_completed", "from": item.get("is_completed"), "to": new_state}
                    ],
                    requires_signature=False,
                    confirmation_message=f"Mark '{item.get('description')}' as {'complete' if new_state else 'incomplete'}?"
                ))

                builder.set_data({
                    "item_description": item.get("description"),
                    "current_state": item.get("is_completed"),
                    "new_state": new_state,
                    "state": "pending_confirmation"
                })

            else:
                pending = MutationContext.get_pending(mutation_id)
                if not pending:
                    builder.set_error("INVALID_MUTATION", "Mutation expired or not found")
                    return builder.build()

                update_data = {
                    "is_completed": new_state
                }
                if new_state:
                    update_data["completed_at"] = datetime.now(timezone.utc).isoformat()
                    update_data["completed_by"] = params.get("user_id")
                else:
                    update_data["completed_at"] = None
                    update_data["completed_by"] = None

                if params.get("notes"):
                    update_data["notes"] = params["notes"]

                self.db.table("checklist_items").update(update_data).eq("id", item_id).execute()

                MutationContext.remove_pending(mutation_id)
                builder.set_data({
                    "item_id": item_id,
                    "is_completed": new_state,
                    "status": "updated",
                    "message": f"Item marked as {'complete' if new_state else 'incomplete'}"
                })

            return builder.build()

        except Exception as e:
            logger.error(f"toggle_checklist_item failed: {e}", exc_info=True)
            builder.set_error("INTERNAL_ERROR", str(e))
            return builder.build()

    async def complete_checklist(
        self,
        entity_id: str,
        yacht_id: str,
        params: Optional[Dict] = None,
        commit: bool = False,
        mutation_id: Optional[str] = None
    ) -> Dict:
        """
        Mark entire checklist as complete.

        Validates all required items are completed first.
        """
        builder = ResponseBuilder("complete_checklist", entity_id, "checklist", yacht_id)

        try:
            # Get checklist and items
            checklist_result = self.db.table("checklists").select(
                "id, title, status"
            ).eq("id", entity_id).maybe_single().execute()

            if not checklist_result.data:
                builder.set_error("NOT_FOUND", f"Checklist not found: {entity_id}")
                return builder.build()

            checklist = checklist_result.data

            if checklist.get("status") == "completed":
                builder.set_error("ALREADY_COMPLETED", "Checklist is already completed")
                return builder.build()

            # Check required items
            items_result = self.db.table("checklist_items").select(
                "id, is_completed, is_required"
            ).eq("checklist_id", entity_id).execute()

            items = items_result.data or []
            required_incomplete = [i for i in items if i.get("is_required") and not i.get("is_completed")]

            if required_incomplete:
                builder.set_error(
                    "INCOMPLETE_REQUIRED",
                    f"{len(required_incomplete)} required items not completed"
                )
                return builder.build()

            if not commit:
                mutation_id = str(uuid.uuid4())
                MutationContext.store_pending(mutation_id, {
                    "action": "complete_checklist",
                    "entity_id": entity_id
                })

                completed_count = len([i for i in items if i.get("is_completed")])

                builder.set_mutation_preview(MutationPreview(
                    mutation_id=mutation_id,
                    action="complete_checklist",
                    changes=[
                        {"field": "status", "from": checklist.get("status"), "to": "completed"}
                    ],
                    requires_signature=True,
                    confirmation_message=f"Complete checklist '{checklist.get('title')}'? ({completed_count}/{len(items)} items done)"
                ))

                builder.set_data({
                    "checklist_title": checklist.get("title"),
                    "items_completed": completed_count,
                    "items_total": len(items),
                    "state": "pending_confirmation"
                })

            else:
                pending = MutationContext.get_pending(mutation_id)
                if not pending:
                    builder.set_error("INVALID_MUTATION", "Mutation expired or not found")
                    return builder.build()

                self.db.table("checklists").update({
                    "status": "completed",
                    "completed_at": datetime.now(timezone.utc).isoformat(),
                    "completed_by": params.get("user_id") if params else None
                }).eq("id", entity_id).execute()

                MutationContext.remove_pending(mutation_id)
                builder.set_data({
                    "checklist_id": entity_id,
                    "status": "completed",
                    "message": "Checklist completed successfully"
                })

            return builder.build()

        except Exception as e:
            logger.error(f"complete_checklist failed: {e}", exc_info=True)
            builder.set_error("INTERNAL_ERROR", str(e))
            return builder.build()


# =========================================================================
# HANDLER REGISTRATION
# =========================================================================

def get_equipment_mutate_handlers(supabase_client) -> Dict[str, callable]:
    """Get equipment MUTATE handler functions."""
    handlers = EquipmentMutateHandlers(supabase_client)
    return {
        "create_work_order": handlers.create_work_order,
        "log_equipment_hours": handlers.log_equipment_hours,
    }


def get_inventory_mutate_handlers(supabase_client) -> Dict[str, callable]:
    """Get inventory MUTATE handler functions."""
    handlers = InventoryMutateHandlers(supabase_client)
    return {
        "edit_inventory_quantity": handlers.edit_inventory_quantity,
        "log_part_usage": handlers.log_part_usage,
        "create_reorder": handlers.create_reorder,
    }


def get_work_order_mutate_handlers(supabase_client) -> Dict[str, callable]:
    """Get work order MUTATE handler functions."""
    handlers = WorkOrderMutateHandlers(supabase_client)
    return {
        "update_work_order_status": handlers.update_work_order_status,
        "mark_work_order_complete": handlers.mark_work_order_complete,
        "assign_work_order": handlers.assign_work_order,
        "add_work_order_note": handlers.add_work_order_note,
    }


def get_fault_mutate_handlers(supabase_client) -> Dict[str, callable]:
    """Get fault MUTATE handler functions."""
    handlers = FaultMutateHandlers(supabase_client)
    return {
        "resolve_fault": handlers.resolve_fault,
        "create_fault": handlers.create_fault,
        "acknowledge_fault": handlers.acknowledge_fault,
    }


def get_hours_of_rest_mutate_handlers(supabase_client) -> Dict[str, callable]:
    """Get hours of rest MUTATE handler functions."""
    handlers = HoursOfRestMutateHandlers(supabase_client)
    return {
        "log_rest_hours": handlers.log_rest_hours,
    }


def get_checklist_mutate_handlers(supabase_client) -> Dict[str, callable]:
    """Get checklist MUTATE handler functions."""
    handlers = ChecklistMutateHandlers(supabase_client)
    return {
        "toggle_checklist_item": handlers.toggle_checklist_item,
        "complete_checklist": handlers.complete_checklist,
    }


def get_all_mutate_handlers(supabase_client) -> Dict[str, callable]:
    """Get all MUTATE handlers combined."""
    handlers = {}
    handlers.update(get_equipment_mutate_handlers(supabase_client))
    handlers.update(get_inventory_mutate_handlers(supabase_client))
    handlers.update(get_work_order_mutate_handlers(supabase_client))
    handlers.update(get_fault_mutate_handlers(supabase_client))
    handlers.update(get_hours_of_rest_mutate_handlers(supabase_client))
    handlers.update(get_checklist_mutate_handlers(supabase_client))
    return handlers
