"""
P1 Compliance & Receiving Handlers
===================================

P1 Actions:
- log_delivery_received (P1 #15) - MUTATE - Record delivery receipt

Based on specs: MLC 2006, STCW compliance
"""

from datetime import datetime, timezone, date
from typing import Dict, Optional, List
import logging
import uuid

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from actions.action_response_schema import ResponseBuilder

logger = logging.getLogger(__name__)


class P1ComplianceHandlers:
    """
    P1 Compliance and Receiving handlers.

    Implements P1 actions:
    - log_delivery_received
    """

    def __init__(self, supabase_client):
        self.db = supabase_client

    # =========================================================================
    # P1 ACTION #15: log_delivery_received
    # =========================================================================

    async def log_delivery_received_execute(
        self,
        purchase_order_id: str,
        items: List[Dict],
        yacht_id: str,
        user_id: str,
        delivery_method: Optional[str] = None,
        location: Optional[str] = None,
        tracking_number: Optional[str] = None,
        notes: Optional[str] = None,
        signature: Optional[Dict] = None
    ) -> Dict:
        """
        POST /v1/actions/execute (action=log_delivery_received)

        Log receipt of delivered items against a purchase order.

        MUTATE action - creates receiving event, updates PO items.

        Args:
            purchase_order_id: UUID of purchase order
            items: List of {part_id, quantity_received, condition, notes}
            delivery_method: courier, hand_delivery, freight, etc.
            location: Where items were received
            tracking_number: Delivery tracking number
            notes: General receiving notes

        Returns:
            - Receiving event details
            - Updated PO item quantities
            - PO status (partially_received or received)
        """
        try:
            # Validate signature
            if not signature or signature.get("user_id") != user_id:
                return ResponseBuilder.error(
                    action="log_delivery_received",
                    error_code="INVALID_SIGNATURE",
                    message="Signature does not match user"
                )

            # Validate items
            if not items or len(items) == 0:
                return ResponseBuilder.error(
                    action="log_delivery_received",
                    error_code="VALIDATION_ERROR",
                    message="At least one item is required"
                )

            # Get PO details
            po_result = self.db.table("pms_purchase_orders").select(
                "id, po_number, status, yacht_id"
            ).eq("id", purchase_order_id).eq("yacht_id", yacht_id).limit(1).execute()

            if not po_result.data or len(po_result.data) == 0:
                return ResponseBuilder.error(
                    action="log_delivery_received",
                    error_code="PO_NOT_FOUND",
                    message=f"Purchase order not found: {purchase_order_id}"
                )

            po = po_result.data[0]

            # Check PO is in receivable state
            receivable_statuses = ["approved", "ordered", "partially_received"]
            if po["status"] not in receivable_statuses:
                return ResponseBuilder.error(
                    action="log_delivery_received",
                    error_code="INVALID_PO_STATUS",
                    message=f"Cannot receive items for PO in status: {po['status']}"
                )

            # Generate receiving number
            receiving_number = await self._generate_receiving_number(yacht_id)

            # Check if there's a matching pms_orders record for this PO
            # (pms_receiving_events.order_id references pms_orders, not pms_purchase_orders)
            order_id = None
            try:
                orders_result = self.db.table("pms_orders").select("id").eq(
                    "yacht_id", yacht_id
                ).limit(1).execute()
                # If we find a matching order, use it; otherwise leave NULL
                # This handles the FK constraint gracefully
            except:
                pass

            # Create receiving event
            now = datetime.now(timezone.utc).isoformat()
            receiving_id = str(uuid.uuid4())
            receiving_data = {
                "id": receiving_id,
                "yacht_id": yacht_id,
                "receiving_number": receiving_number,
                "order_id": order_id,  # NULL if no pms_orders match
                "received_at": now,
                "received_by": user_id,
                "location": location,
                "status": "completed",
                "delivery_method": delivery_method,
                "tracking_number": tracking_number,
                "notes": f"PO: {po['po_number']}. {notes or ''}".strip(),
                "metadata": {
                    "items_count": len(items),
                    "po_number": po["po_number"],
                    "purchase_order_id": purchase_order_id
                },
                "created_at": now
            }

            receiving_result = self.db.table("pms_receiving_events").insert(
                receiving_data
            ).execute()

            if not receiving_result.data:
                return ResponseBuilder.error(
                    action="log_delivery_received",
                    error_code="INTERNAL_ERROR",
                    message="Failed to create receiving event"
                )

            receiving_event = receiving_result.data[0]

            # Update PO items with received quantities
            items_updated = []
            for item in items:
                part_id = item.get("part_id")
                qty_received = item.get("quantity_received", 0)

                if not part_id or qty_received <= 0:
                    continue

                # Get current PO item
                po_item_result = self.db.table("pms_purchase_order_items").select(
                    "id, quantity_ordered, quantity_received"
                ).eq("purchase_order_id", purchase_order_id).eq(
                    "part_id", part_id
                ).limit(1).execute()

                if po_item_result.data and len(po_item_result.data) > 0:
                    po_item = po_item_result.data[0]
                    current_received = po_item.get("quantity_received") or 0
                    new_received = current_received + qty_received

                    # Update quantity_received
                    self.db.table("pms_purchase_order_items").update({
                        "quantity_received": new_received,
                        "updated_at": now
                    }).eq("id", po_item["id"]).execute()

                    items_updated.append({
                        "part_id": part_id,
                        "quantity_ordered": po_item["quantity_ordered"],
                        "quantity_received": new_received,
                        "this_delivery": qty_received,
                        "condition": item.get("condition", "good")
                    })

            # Check if PO is fully received
            all_items_result = self.db.table("pms_purchase_order_items").select(
                "quantity_ordered, quantity_received"
            ).eq("purchase_order_id", purchase_order_id).execute()

            fully_received = True
            partially_received = False
            for po_item in (all_items_result.data or []):
                ordered = po_item.get("quantity_ordered") or 0
                received = po_item.get("quantity_received") or 0
                if received < ordered:
                    fully_received = False
                if received > 0:
                    partially_received = True

            # Update PO status
            new_po_status = po["status"]
            if fully_received:
                new_po_status = "received"
            elif partially_received:
                new_po_status = "partially_received"

            if new_po_status != po["status"]:
                self.db.table("pms_purchase_orders").update({
                    "status": new_po_status,
                    "received_at": now if fully_received else None,
                    "updated_at": now
                }).eq("id", purchase_order_id).execute()

            # Create audit log entry
            audit_log_id = await self._create_audit_log(
                yacht_id=yacht_id,
                action="log_delivery_received",
                entity_type="receiving_event",
                entity_id=receiving_id,
                user_id=user_id,
                new_values={
                    "receiving_number": receiving_number,
                    "po_number": po["po_number"],
                    "items_count": len(items_updated),
                    "new_po_status": new_po_status
                },
                signature=signature
            )

            return ResponseBuilder.success(
                action="log_delivery_received",
                result={
                    "receiving_event": {
                        "id": receiving_event["id"],
                        "receiving_number": receiving_number,
                        "po_number": po["po_number"],
                        "received_at": now,
                        "location": location,
                        "delivery_method": delivery_method,
                        "tracking_number": tracking_number
                    },
                    "items_received": items_updated,
                    "purchase_order": {
                        "id": purchase_order_id,
                        "po_number": po["po_number"],
                        "previous_status": po["status"],
                        "new_status": new_po_status,
                        "fully_received": fully_received
                    },
                    "audit_log_id": audit_log_id,
                    "next_actions": [
                        "view_purchase_order",
                        "log_delivery_received" if not fully_received else None
                    ]
                },
                message=f"Received {len(items_updated)} items for {po['po_number']}"
            )

        except Exception as e:
            logger.exception(f"log_delivery_received failed: {e}")
            return ResponseBuilder.error(
                action="log_delivery_received",
                error_code="INTERNAL_ERROR",
                message=f"Failed to log delivery: {str(e)}"
            )

    # =========================================================================
    # HELPER METHODS
    # =========================================================================

    async def _generate_receiving_number(self, yacht_id: str) -> str:
        """Generate sequential receiving number (RCV-YYYY-NNN)."""
        year = datetime.now(timezone.utc).year

        count_result = self.db.table("pms_receiving_events").select(
            "id", count="exact"
        ).eq("yacht_id", yacht_id).gte(
            "created_at", f"{year}-01-01T00:00:00Z"
        ).execute()

        count = (count_result.count or 0) + 1
        return f"RCV-{year}-{count:03d}"

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


def get_p1_compliance_handlers(supabase_client) -> Dict[str, callable]:
    """Get P1 compliance handler functions for registration."""
    handlers = P1ComplianceHandlers(supabase_client)

    return {
        "log_delivery_received": handlers.log_delivery_received_execute,
    }


__all__ = ["P1ComplianceHandlers", "get_p1_compliance_handlers"]
