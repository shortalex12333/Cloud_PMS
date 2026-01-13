"""
P1 Purchasing & Work Order Handlers
====================================

P1 Actions:
- create_work_order (P1 Action #10) - MUTATE - Standalone WO creation
- order_part (P1 Action #11) - MUTATE - Add part to purchase order
- create_purchase_request (P1 Action #13) - MUTATE - Create purchase request
- approve_purchase (P1 Action #14) - MUTATE - Approve purchase request

Based on specs: /P0_ACTION_CONTRACTS.md - P1 Actions
"""

from datetime import datetime, timezone
from typing import Dict, Optional, List
import logging
import uuid

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from actions.action_response_schema import ResponseBuilder

logger = logging.getLogger(__name__)


# Purchase Order Status Workflow
PO_STATUS_TRANSITIONS = {
    "draft": ["requested", "cancelled"],
    "requested": ["approved", "rejected", "cancelled"],
    "approved": ["ordered", "cancelled"],
    "ordered": ["partially_received", "received", "cancelled"],
    "partially_received": ["received"],
    "received": [],  # Terminal state
    "rejected": ["draft"],  # Can resubmit
    "cancelled": [],  # Terminal state
}

# Roles that can approve purchases
PURCHASE_APPROVER_ROLES = ["captain", "chief_engineer", "chief_officer", "admin", "owner"]


class P1PurchasingHandlers:
    """
    P1 Purchasing and Work Order handlers.

    Implements P1 actions:
    - create_work_order (standalone)
    - order_part
    - create_purchase_request
    - approve_purchase
    """

    def __init__(self, supabase_client):
        self.db = supabase_client

    # =========================================================================
    # P1 ACTION #10: create_work_order (standalone)
    # =========================================================================

    async def create_work_order_execute(
        self,
        title: str,
        yacht_id: str,
        user_id: str,
        description: Optional[str] = None,
        equipment_id: Optional[str] = None,
        priority: str = "routine",
        signature: Optional[Dict] = None
    ) -> Dict:
        """
        POST /v1/actions/execute (action=create_work_order)

        Create a standalone work order (not from fault).

        MUTATE action - execute only (low-risk creation).

        Creates:
        - Work order record (status=planned)
        - Audit log entry

        Returns:
        - Work order details
        - Generated WO number
        - Next available actions
        """
        try:
            # Validate signature
            if not signature or signature.get("user_id") != user_id:
                return ResponseBuilder.error(
                    action="create_work_order",
                    error_code="INVALID_SIGNATURE",
                    message="Signature does not match user"
                )

            # Validate title
            if not title or len(title.strip()) < 5:
                return ResponseBuilder.error(
                    action="create_work_order",
                    error_code="VALIDATION_ERROR",
                    message="Title must be at least 5 characters"
                )

            # Validate priority (DB enum: routine, urgent, emergency)
            valid_priorities = ["routine", "urgent", "emergency"]
            if priority not in valid_priorities:
                return ResponseBuilder.error(
                    action="create_work_order",
                    error_code="VALIDATION_ERROR",
                    message=f"Invalid priority: {priority}. Must be one of: {', '.join(valid_priorities)}"
                )

            # Validate equipment exists (if provided)
            if equipment_id:
                eq_result = self.db.table("pms_equipment").select(
                    "id, name"
                ).eq("id", equipment_id).eq("yacht_id", yacht_id).limit(1).execute()

                if not eq_result.data or len(eq_result.data) == 0:
                    return ResponseBuilder.error(
                        action="create_work_order",
                        error_code="EQUIPMENT_NOT_FOUND",
                        message=f"Equipment not found: {equipment_id}"
                    )

            # Generate work order number
            wo_number = await self._generate_wo_number(yacht_id)

            # Create work order
            now = datetime.now(timezone.utc).isoformat()
            wo_id = str(uuid.uuid4())
            wo_data = {
                "id": wo_id,
                "yacht_id": yacht_id,
                "wo_number": wo_number,
                "title": title.strip(),
                "description": description,
                "equipment_id": equipment_id,
                "fault_id": None,  # Standalone WO - no fault
                "priority": priority,
                "status": "planned",
                "created_by": user_id,
                "created_at": now,
                "updated_at": now
            }

            wo_result = self.db.table("pms_work_orders").insert(wo_data).execute()

            if not wo_result.data:
                return ResponseBuilder.error(
                    action="create_work_order",
                    error_code="INTERNAL_ERROR",
                    message="Failed to create work order"
                )

            work_order = wo_result.data[0]

            # Create audit log entry
            audit_log_id = await self._create_audit_log(
                yacht_id=yacht_id,
                action="create_work_order",
                entity_type="work_order",
                entity_id=work_order["id"],
                user_id=user_id,
                new_values=work_order,
                signature=signature
            )

            return ResponseBuilder.success(
                action="create_work_order",
                result={
                    "work_order": {
                        "id": work_order["id"],
                        "number": work_order.get("wo_number", wo_number),
                        "title": work_order["title"],
                        "equipment_id": work_order.get("equipment_id"),
                        "description": work_order.get("description"),
                        "priority": work_order["priority"],
                        "status": work_order["status"],
                        "created_at": work_order["created_at"],
                        "created_by": work_order["created_by"]
                    },
                    "audit_log_id": audit_log_id,
                    "next_actions": [
                        "add_note_to_work_order",
                        "add_part_to_work_order",
                        "view_work_order"
                    ]
                },
                message=f"Work order {wo_number} created"
            )

        except Exception as e:
            logger.exception(f"create_work_order failed: {e}")
            return ResponseBuilder.error(
                action="create_work_order",
                error_code="INTERNAL_ERROR",
                message=f"Failed to create work order: {str(e)}"
            )

    # =========================================================================
    # P1 ACTION #13: create_purchase_request
    # =========================================================================

    async def create_purchase_request_execute(
        self,
        yacht_id: str,
        user_id: str,
        supplier_id: Optional[str] = None,
        notes: Optional[str] = None,
        items: Optional[List[Dict]] = None,
        signature: Optional[Dict] = None
    ) -> Dict:
        """
        POST /v1/actions/execute (action=create_purchase_request)

        Create a new purchase request/order.

        MUTATE action - creates PO in 'draft' or 'requested' status.

        Args:
            supplier_id: Optional supplier UUID
            notes: Purchase notes/description
            items: List of {part_id, quantity, unit_price, notes}

        Returns:
        - Purchase order details
        - Generated PO number
        - Next available actions
        """
        try:
            # Validate signature
            if not signature or signature.get("user_id") != user_id:
                return ResponseBuilder.error(
                    action="create_purchase_request",
                    error_code="INVALID_SIGNATURE",
                    message="Signature does not match user"
                )

            # Validate supplier exists (if provided)
            if supplier_id:
                supplier_result = self.db.table("pms_suppliers").select(
                    "id, name"
                ).eq("id", supplier_id).eq("yacht_id", yacht_id).limit(1).execute()

                if not supplier_result.data or len(supplier_result.data) == 0:
                    return ResponseBuilder.error(
                        action="create_purchase_request",
                        error_code="SUPPLIER_NOT_FOUND",
                        message=f"Supplier not found: {supplier_id}"
                    )

            # Generate PO number
            po_number = await self._generate_po_number(yacht_id)

            # Create purchase order
            now = datetime.now(timezone.utc).isoformat()
            po_id = str(uuid.uuid4())
            po_data = {
                "id": po_id,
                "yacht_id": yacht_id,
                "po_number": po_number,
                "supplier_id": supplier_id,
                "status": "requested",
                "metadata": {
                    "notes": notes,
                    "requested_by": user_id,
                    "requested_at": now
                },
                "created_at": now,
                "updated_at": now
            }

            po_result = self.db.table("pms_purchase_orders").insert(po_data).execute()

            if not po_result.data:
                return ResponseBuilder.error(
                    action="create_purchase_request",
                    error_code="INTERNAL_ERROR",
                    message="Failed to create purchase request"
                )

            purchase_order = po_result.data[0]

            # Add line items if provided
            items_created = []
            if items and len(items) > 0:
                for item in items:
                    item_id = str(uuid.uuid4())
                    item_data = {
                        "id": item_id,
                        "yacht_id": yacht_id,
                        "purchase_order_id": po_id,
                        "part_id": item.get("part_id"),
                        "quantity_ordered": item.get("quantity", 1),
                        "unit_price": item.get("unit_price"),
                        "description": item.get("notes"),  # Use description column
                        "created_at": now
                    }
                    item_result = self.db.table("pms_purchase_order_items").insert(item_data).execute()
                    if item_result.data:
                        items_created.append(item_result.data[0])

            # Create audit log entry
            audit_log_id = await self._create_audit_log(
                yacht_id=yacht_id,
                action="create_purchase_request",
                entity_type="purchase_order",
                entity_id=po_id,
                user_id=user_id,
                new_values={**purchase_order, "items_count": len(items_created)},
                signature=signature
            )

            metadata = purchase_order.get("metadata", {}) or {}
            return ResponseBuilder.success(
                action="create_purchase_request",
                result={
                    "purchase_order": {
                        "id": purchase_order["id"],
                        "po_number": purchase_order.get("po_number", po_number),
                        "supplier_id": purchase_order.get("supplier_id"),
                        "status": purchase_order["status"],
                        "notes": metadata.get("notes"),
                        "requested_by": metadata.get("requested_by"),
                        "requested_at": metadata.get("requested_at"),
                        "items_count": len(items_created)
                    },
                    "items": items_created,
                    "audit_log_id": audit_log_id,
                    "next_actions": [
                        "order_part",
                        "approve_purchase",
                        "view_purchase_order"
                    ]
                },
                message=f"Purchase request {po_number} created"
            )

        except Exception as e:
            logger.exception(f"create_purchase_request failed: {e}")
            return ResponseBuilder.error(
                action="create_purchase_request",
                error_code="INTERNAL_ERROR",
                message=f"Failed to create purchase request: {str(e)}"
            )

    # =========================================================================
    # P1 ACTION #11: order_part
    # =========================================================================

    async def order_part_execute(
        self,
        purchase_order_id: str,
        part_id: str,
        quantity: int,
        yacht_id: str,
        user_id: str,
        unit_price: Optional[float] = None,
        notes: Optional[str] = None,
        signature: Optional[Dict] = None
    ) -> Dict:
        """
        POST /v1/actions/execute (action=order_part)

        Add a part to an existing purchase order.

        MUTATE action - adds line item to PO.

        Args:
            purchase_order_id: UUID of purchase order
            part_id: UUID of part to order
            quantity: Quantity to order
            unit_price: Optional unit price
            notes: Optional notes

        Returns:
        - Line item details
        - Updated PO summary
        """
        try:
            # Validate signature
            if not signature or signature.get("user_id") != user_id:
                return ResponseBuilder.error(
                    action="order_part",
                    error_code="INVALID_SIGNATURE",
                    message="Signature does not match user"
                )

            # Validate quantity
            if not quantity or quantity < 1:
                return ResponseBuilder.error(
                    action="order_part",
                    error_code="VALIDATION_ERROR",
                    message="Quantity must be at least 1"
                )

            # Validate PO exists and is in valid state
            po_result = self.db.table("pms_purchase_orders").select(
                "id, po_number, status, yacht_id"
            ).eq("id", purchase_order_id).eq("yacht_id", yacht_id).limit(1).execute()

            if not po_result.data or len(po_result.data) == 0:
                return ResponseBuilder.error(
                    action="order_part",
                    error_code="PO_NOT_FOUND",
                    message=f"Purchase order not found: {purchase_order_id}"
                )

            po = po_result.data[0]

            # Check PO is in editable state
            if po["status"] not in ["draft", "requested"]:
                return ResponseBuilder.error(
                    action="order_part",
                    error_code="INVALID_PO_STATUS",
                    message=f"Cannot add parts to PO in status: {po['status']}. Must be draft or requested."
                )

            # Validate part exists
            part_result = self.db.table("pms_parts").select(
                "id, name, part_number"
            ).eq("id", part_id).eq("yacht_id", yacht_id).limit(1).execute()

            if not part_result.data or len(part_result.data) == 0:
                return ResponseBuilder.error(
                    action="order_part",
                    error_code="PART_NOT_FOUND",
                    message=f"Part not found: {part_id}"
                )

            part = part_result.data[0]

            # Check for duplicate line item
            existing_item = self.db.table("pms_purchase_order_items").select(
                "id"
            ).eq("purchase_order_id", purchase_order_id).eq("part_id", part_id).limit(1).execute()

            if existing_item.data and len(existing_item.data) > 0:
                return ResponseBuilder.error(
                    action="order_part",
                    error_code="DUPLICATE_LINE_ITEM",
                    message=f"Part already exists in this PO. Use update_line_item to change quantity."
                )

            # Create line item
            now = datetime.now(timezone.utc).isoformat()
            item_id = str(uuid.uuid4())
            item_data = {
                "id": item_id,
                "yacht_id": yacht_id,
                "purchase_order_id": purchase_order_id,
                "part_id": part_id,
                "quantity_ordered": quantity,
                "unit_price": unit_price,  # User provides price
                "description": notes,  # Use description column
                "created_at": now
            }

            item_result = self.db.table("pms_purchase_order_items").insert(item_data).execute()

            if not item_result.data:
                return ResponseBuilder.error(
                    action="order_part",
                    error_code="INTERNAL_ERROR",
                    message="Failed to add part to purchase order"
                )

            line_item = item_result.data[0]

            # Create audit log entry
            audit_log_id = await self._create_audit_log(
                yacht_id=yacht_id,
                action="order_part",
                entity_type="purchase_order_item",
                entity_id=item_id,
                user_id=user_id,
                new_values={
                    "purchase_order_id": purchase_order_id,
                    "po_number": po["po_number"],
                    "part_id": part_id,
                    "part_number": part.get("part_number"),
                    "quantity": quantity
                },
                signature=signature
            )

            return ResponseBuilder.success(
                action="order_part",
                result={
                    "line_item": {
                        "id": line_item["id"],
                        "purchase_order_id": purchase_order_id,
                        "po_number": po["po_number"],
                        "part_id": part_id,
                        "part_name": part.get("name"),
                        "part_number": part.get("part_number"),
                        "quantity_ordered": line_item["quantity_ordered"],
                        "unit_price": line_item.get("unit_price"),
                        "description": line_item.get("description")
                    },
                    "audit_log_id": audit_log_id,
                    "next_actions": [
                        "order_part",
                        "approve_purchase",
                        "view_purchase_order"
                    ]
                },
                message=f"Added {quantity}x {part.get('name', part_id)} to {po['po_number']}"
            )

        except Exception as e:
            logger.exception(f"order_part failed: {e}")
            return ResponseBuilder.error(
                action="order_part",
                error_code="INTERNAL_ERROR",
                message=f"Failed to add part to purchase order: {str(e)}"
            )

    # =========================================================================
    # P1 ACTION #14: approve_purchase
    # =========================================================================

    async def approve_purchase_execute(
        self,
        purchase_order_id: str,
        yacht_id: str,
        user_id: str,
        user_role: str,
        approval_notes: Optional[str] = None,
        signature: Optional[Dict] = None
    ) -> Dict:
        """
        POST /v1/actions/execute (action=approve_purchase)

        Approve a purchase request.

        MUTATE action - changes PO status from 'requested' to 'approved'.

        Role-based approval:
        - Only captain, chief_engineer, chief_officer, admin, owner can approve

        Args:
            purchase_order_id: UUID of purchase order
            user_role: Role of approving user
            approval_notes: Optional notes

        Returns:
        - Updated PO details
        - Approval timestamp
        """
        try:
            # Validate signature
            if not signature or signature.get("user_id") != user_id:
                return ResponseBuilder.error(
                    action="approve_purchase",
                    error_code="INVALID_SIGNATURE",
                    message="Signature does not match user"
                )

            # Validate role
            if user_role not in PURCHASE_APPROVER_ROLES:
                return ResponseBuilder.error(
                    action="approve_purchase",
                    error_code="UNAUTHORIZED",
                    message=f"Role '{user_role}' cannot approve purchases. Required roles: {', '.join(PURCHASE_APPROVER_ROLES)}"
                )

            # Get PO
            po_result = self.db.table("pms_purchase_orders").select(
                "id, po_number, status, yacht_id, supplier_id, metadata"
            ).eq("id", purchase_order_id).eq("yacht_id", yacht_id).limit(1).execute()

            if not po_result.data or len(po_result.data) == 0:
                return ResponseBuilder.error(
                    action="approve_purchase",
                    error_code="PO_NOT_FOUND",
                    message=f"Purchase order not found: {purchase_order_id}"
                )

            po = po_result.data[0]

            # Validate status transition
            if po["status"] != "requested":
                valid_from = [k for k, v in PO_STATUS_TRANSITIONS.items() if "approved" in v]
                return ResponseBuilder.error(
                    action="approve_purchase",
                    error_code="INVALID_STATUS_TRANSITION",
                    message=f"Cannot approve PO in status '{po['status']}'. Must be in: {', '.join(valid_from)}"
                )

            # Self-approval check (optional - can be enabled)
            # if po["requested_by"] == user_id:
            #     return ResponseBuilder.error(
            #         action="approve_purchase",
            #         error_code="SELF_APPROVAL_NOT_ALLOWED",
            #         message="Cannot approve your own purchase request"
            #     )

            # Update PO status - merge approval info into metadata
            now = datetime.now(timezone.utc).isoformat()
            existing_metadata = po.get("metadata", {}) or {}
            updated_metadata = {
                **existing_metadata,
                "approved_by": user_id,
                "approved_at": now,
                "approval_notes": approval_notes,
                "approver_role": user_role
            }
            update_data = {
                "status": "approved",
                "metadata": updated_metadata,
                "updated_at": now
            }

            update_result = self.db.table("pms_purchase_orders").update(
                update_data
            ).eq("id", purchase_order_id).execute()

            if not update_result.data:
                return ResponseBuilder.error(
                    action="approve_purchase",
                    error_code="INTERNAL_ERROR",
                    message="Failed to approve purchase order"
                )

            updated_po = update_result.data[0]
            result_metadata = updated_po.get("metadata", {}) or {}

            # Create audit log entry
            audit_log_id = await self._create_audit_log(
                yacht_id=yacht_id,
                action="approve_purchase",
                entity_type="purchase_order",
                entity_id=purchase_order_id,
                user_id=user_id,
                old_values={"status": po["status"]},
                new_values={
                    "status": "approved",
                    "approved_by": user_id,
                    "approved_at": now,
                    "approver_role": user_role
                },
                signature=signature
            )

            return ResponseBuilder.success(
                action="approve_purchase",
                result={
                    "purchase_order": {
                        "id": updated_po["id"],
                        "po_number": updated_po.get("po_number"),
                        "status": updated_po["status"],
                        "approved_by": result_metadata.get("approved_by"),
                        "approved_at": result_metadata.get("approved_at"),
                        "approval_notes": result_metadata.get("approval_notes")
                    },
                    "audit_log_id": audit_log_id,
                    "next_actions": [
                        "view_purchase_order",
                        "log_delivery_received"
                    ]
                },
                message=f"Purchase order {updated_po.get('po_number')} approved"
            )

        except Exception as e:
            logger.exception(f"approve_purchase failed: {e}")
            return ResponseBuilder.error(
                action="approve_purchase",
                error_code="INTERNAL_ERROR",
                message=f"Failed to approve purchase order: {str(e)}"
            )

    # =========================================================================
    # HELPER METHODS
    # =========================================================================

    async def _generate_wo_number(self, yacht_id: str) -> str:
        """Generate sequential work order number (WO-YYYY-NNN)."""
        year = datetime.now(timezone.utc).year

        # Get count of work orders this year
        count_result = self.db.table("pms_work_orders").select(
            "id", count="exact"
        ).eq("yacht_id", yacht_id).gte(
            "created_at", f"{year}-01-01T00:00:00Z"
        ).execute()

        count = (count_result.count or 0) + 1
        return f"WO-{year}-{count:03d}"

    async def _generate_po_number(self, yacht_id: str) -> str:
        """Generate sequential PO number (PO-YYYY-NNN)."""
        year = datetime.now(timezone.utc).year

        # Get count of POs this year
        count_result = self.db.table("pms_purchase_orders").select(
            "id", count="exact"
        ).eq("yacht_id", yacht_id).gte(
            "created_at", f"{year}-01-01T00:00:00Z"
        ).execute()

        count = (count_result.count or 0) + 1
        return f"PO-{year}-{count:03d}"

    async def _create_audit_log(
        self,
        yacht_id: str,
        action: str,
        entity_type: str,
        entity_id: str,
        user_id: str,
        new_values: Dict,
        signature: Dict,
        old_values: Optional[Dict] = None
    ) -> str:
        """Create audit log entry."""
        audit_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()

        audit_data = {
            "id": audit_id,
            "yacht_id": yacht_id,
            "action": action,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "user_id": user_id,
            "old_values": old_values,
            "new_values": new_values,
            "signature": {
                **signature,
                "timestamp": now
            },
            "created_at": now
        }

        try:
            self.db.table("pms_audit_log").insert(audit_data).execute()
        except Exception as e:
            logger.warning(f"Failed to create audit log: {e}")

        return audit_id


def get_p1_purchasing_handlers(supabase_client) -> Dict[str, callable]:
    """Get P1 purchasing handler functions for registration."""
    handlers = P1PurchasingHandlers(supabase_client)

    return {
        "create_work_order": handlers.create_work_order_execute,
        "create_purchase_request": handlers.create_purchase_request_execute,
        "order_part": handlers.order_part_execute,
        "approve_purchase": handlers.approve_purchase_execute,
    }


__all__ = ["P1PurchasingHandlers", "get_p1_purchasing_handlers"]
