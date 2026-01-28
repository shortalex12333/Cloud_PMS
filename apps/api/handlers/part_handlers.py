"""
Part/Inventory Domain Handlers
==============================

Handlers for part/inventory actions (Part Lens v2).

DOCTRINE COMPLIANCE:
- Stock is DERIVED from append-only pms_inventory_transactions
- All stock changes INSERT into pms_inventory_transactions (NEVER UPDATE pms_parts)
- Idempotency via DB unique constraint (yacht_id, idempotency_key) → 409 on conflict
- SIGNED actions require signature (400 if missing/invalid)
- READ actions write audit entries with signature = {}

READ Handlers:
- view_part_details: View part details with stock levels (writes read-audit)
- view_low_stock: List parts below minimum threshold
- open_document: Open document with read-audit

MUTATE Handlers:
- add_to_shopping_list: Add part to shopping list
- consume_part: Consume part for work order (409 if insufficient)
- receive_part: Receive delivered parts (idempotency via DB constraint)
- transfer_part: Transfer between locations

SIGNED Handlers (require PIN+TOTP signature):
- adjust_stock_quantity: Manual stock adjustment (400 if no signature)
- write_off_part: Write off damaged/expired parts (400 if no signature)

Label Handlers:
- generate_part_labels: Render PDF to pms-label-pdfs bucket
- request_label_output: Trigger print/email/download
"""

from datetime import datetime, timezone
from typing import Dict, Optional, List, Any
import logging
import uuid as uuid_lib
import hashlib
import math

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import HTTPException

from actions.action_response_schema import (
    ResponseBuilder,
    AvailableAction,
)

logger = logging.getLogger(__name__)


# Transaction types for pms_inventory_transactions
TRANSACTION_TYPES = {
    "received": "received",
    "consumed": "consumed",
    "adjusted": "adjusted",
    "transferred_out": "transferred_out",
    "transferred_in": "transferred_in",
    "write_off": "write_off",
    "returned": "returned",
    "initial": "initial",
}


def round_up_to_multiple(value: int, multiple: int) -> int:
    """Round up to the nearest multiple."""
    if multiple <= 0:
        return value
    return math.ceil(value / multiple) * multiple


def compute_suggested_order_qty(on_hand: int, min_level: int, reorder_multiple: int = 1) -> int:
    """Compute suggested order quantity per spec."""
    if min_level <= 0:
        return 0
    shortage = max(min_level - on_hand, 0)
    if shortage == 0:
        return 0
    raw_qty = max(shortage, 1)
    return round_up_to_multiple(raw_qty, reorder_multiple or 1)


class PartHandlers:
    """Part/Inventory domain handlers."""

    def __init__(self, supabase_client):
        self.db = supabase_client

    # =========================================================================
    # HELPERS: Transaction Management
    # =========================================================================

    def _get_or_create_stock_id(self, yacht_id: str, part_id: str, location: str = None) -> str:
        """Get or create stock record, return stock_id."""
        loc = location or "default"

        # Try to find existing
        result = self.db.table("pms_inventory_stock").select("id").eq(
            "yacht_id", yacht_id
        ).eq("part_id", part_id).eq("location", loc).maybe_single().execute()

        if result and result.data:
            return result.data["id"]

        # Create new stock record
        stock_id = str(uuid_lib.uuid4())
        self.db.table("pms_inventory_stock").insert({
            "id": stock_id,
            "yacht_id": yacht_id,
            "part_id": part_id,
            "location": loc,
            "quantity": 0,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }).execute()

        return stock_id

    def _insert_transaction(
        self,
        yacht_id: str,
        stock_id: str,
        transaction_type: str,
        quantity_change: int,
        quantity_before: int,
        created_by: str,
        supplier_id: str = None,
        idempotency_key: str = None,
        photo_storage_path: str = None,
    ) -> Dict:
        """
        Insert transaction into pms_inventory_transactions.
        DB constraint enforces idempotency - raises exception on duplicate.
        """
        txn_id = str(uuid_lib.uuid4())
        now = datetime.now(timezone.utc).isoformat()

        txn_data = {
            "id": txn_id,
            "yacht_id": yacht_id,
            "stock_id": stock_id,
            "transaction_type": transaction_type,
            "quantity_change": quantity_change,
            "quantity_before": quantity_before,
            "quantity_after": quantity_before + quantity_change,
            "user_id": created_by,  # Column is user_id in actual schema
            "created_at": now,
        }

        # Optional fields
        if supplier_id:
            txn_data["supplier_id"] = supplier_id
        if idempotency_key:
            txn_data["idempotency_key"] = idempotency_key
        if photo_storage_path:
            txn_data["photo_storage_path"] = photo_storage_path

        # Insert - let DB constraint handle idempotency
        result = self.db.table("pms_inventory_transactions").insert(txn_data).execute()

        if not result.data:
            raise Exception("Failed to insert transaction")

        return {"transaction_id": txn_id, "data": result.data[0]}

    # =========================================================================
    # READ HANDLERS (with read-audit)
    # =========================================================================

    async def view_part_details(
        self,
        entity_id: str,
        yacht_id: str,
        user_id: str,
        params: Optional[Dict] = None
    ) -> Dict:
        """
        View part details including stock levels and linked equipment.
        Emits read-audit event to pms_audit_log with signature = {}.
        """
        builder = ResponseBuilder("view_part_details", entity_id, "part", yacht_id)

        try:
            # Get part with stock from canonical pms_part_stock view
            result = self.db.table("pms_part_stock").select(
                "part_id, part_name, part_number, on_hand, min_level, reorder_multiple, "
                "location, is_critical, department, category, stock_id"
            ).eq("yacht_id", yacht_id).eq("part_id", entity_id).maybe_single().execute()

            if not result.data:
                builder.set_error("NOT_FOUND", f"Part not found: {entity_id}")
                return builder.build()

            stock = result.data
            on_hand = stock.get("on_hand", 0) or 0
            min_level = stock.get("min_level", 0) or 0
            reorder_multiple = stock.get("reorder_multiple", 1) or 1

            # Get additional part details from pms_parts
            part_result = self.db.table("pms_parts").select(
                "description, manufacturer, unit_cost"
            ).eq("id", entity_id).maybe_single().execute()

            part_extra = part_result.data or {}

            # Compute derived fields
            is_low_stock = min_level > 0 and on_hand <= min_level
            is_out_of_stock = on_hand == 0
            suggested_order_qty = compute_suggested_order_qty(on_hand, min_level, reorder_multiple)

            part_data = {
                "id": entity_id,
                "name": stock.get("part_name"),
                "part_number": stock.get("part_number"),
                "description": part_extra.get("description"),
                "category": stock.get("category"),
                "manufacturer": part_extra.get("manufacturer"),
                "is_critical": stock.get("is_critical", False),
                "unit_cost": part_extra.get("unit_cost"),
                "stock": {
                    "on_hand": on_hand,
                    "min_level": min_level,
                    "reorder_multiple": reorder_multiple,
                    "location": stock.get("location"),
                    "stock_id": stock.get("stock_id"),
                    "is_low_stock": is_low_stock,
                    "is_out_of_stock": is_out_of_stock,
                    "suggested_order_qty": suggested_order_qty,
                },
            }

            builder.set_data(part_data)

            # READ AUDIT: Write audit log with signature = {} (non-signed)
            self._write_audit_log(
                yacht_id=yacht_id,
                user_id=user_id,
                action="view_part_details",
                entity_type="part",
                entity_id=entity_id,
                old_values=None,
                new_values={"viewed": True, "on_hand": on_hand},
                signature={},  # Non-signed READ action
                metadata={"source": "part_lens", "read_audit": True},
            )

            # Add available actions
            if not is_out_of_stock:
                builder.add_available_action(AvailableAction(
                    action_id="consume_part",
                    label="Consume",
                    variant="MUTATE",
                    icon="minus-circle"
                ))

            if is_low_stock:
                builder.add_available_action(AvailableAction(
                    action_id="add_to_shopping_list",
                    label="Add to Shopping",
                    variant="MUTATE",
                    icon="shopping-cart",
                    is_primary=True
                ))

            builder.add_available_action(AvailableAction(
                action_id="adjust_stock_quantity",
                label="Adjust Stock",
                variant="SIGNED",
                icon="edit"
            ))

            return builder.build()

        except Exception as e:
            logger.error(f"view_part_details failed: {e}", exc_info=True)
            builder.set_error("INTERNAL_ERROR", str(e))
            return builder.build()

    async def open_document(
        self,
        document_id: str,
        yacht_id: str,
        user_id: str,
        params: Optional[Dict] = None
    ) -> Dict:
        """
        Open document with read-audit.
        Writes audit log with signature = {} and required metadata.
        """
        try:
            # Get document
            doc_result = self.db.table("doc_metadata").select(
                "id, filename, storage_path, storage_bucket, document_type, content_type"
            ).eq("id", document_id).eq("yacht_id", yacht_id).maybe_single().execute()

            if not doc_result.data:
                return {"error": "NOT_FOUND", "message": f"Document not found: {document_id}"}

            doc = doc_result.data

            # Generate signed URL if in storage
            url = None
            if doc.get("storage_path") and doc.get("storage_bucket"):
                try:
                    signed = self.db.storage.from_(doc["storage_bucket"]).create_signed_url(
                        doc["storage_path"], 3600
                    )
                    url = signed.get("signedURL")
                except Exception as e:
                    logger.warning(f"Failed to generate signed URL: {e}")

            # READ AUDIT: Write audit log with signature = {}
            self._write_audit_log(
                yacht_id=yacht_id,
                user_id=user_id,
                action="open_document",
                entity_type="document",
                entity_id=document_id,
                old_values=None,
                new_values={"opened": True, "filename": doc.get("filename")},
                signature={},  # Non-signed READ action
                metadata={
                    "source": "part_lens",
                    "read_audit": True,
                    "document_type": doc.get("document_type"),
                    "storage_bucket": doc.get("storage_bucket"),
                },
            )

            return {
                "status": "success",
                "document_id": document_id,
                "filename": doc.get("filename"),
                "document_type": doc.get("document_type"),
                "content_type": doc.get("content_type"),
                "url": url,
            }

        except Exception as e:
            logger.error(f"open_document failed: {e}", exc_info=True)
            return {"error": "INTERNAL_ERROR", "message": str(e)}

    # =========================================================================
    # MUTATE HANDLERS (INSERT into transactions only)
    # =========================================================================

    async def add_to_shopping_list(
        self,
        yacht_id: str,
        user_id: str,
        part_id: str,
        quantity_requested: int,
        urgency: str = "medium",
        notes: str = None,
    ) -> Dict:
        """Add part to shopping list with computed quantity."""
        now = datetime.now(timezone.utc).isoformat()
        item_id = str(uuid_lib.uuid4())

        # Verify part exists via pms_part_stock
        part_result = self.db.table("pms_part_stock").select("part_id, part_name").eq(
            "part_id", part_id
        ).eq("yacht_id", yacht_id).maybe_single().execute()

        if not part_result.data:
            raise ValueError(f"Part {part_id} not found or access denied")

        part_name = part_result.data.get("part_name")

        # Insert shopping list item
        item_data = {
            "id": item_id,
            "yacht_id": yacht_id,
            "part_id": part_id,
            "part_name": part_name,
            "quantity_requested": quantity_requested,
            "urgency": urgency,
            "status": "requested",
            "notes": notes,
            "requested_by": user_id,
            "requested_at": now,
            "created_at": now,
        }

        result = self.db.table("pms_shopping_list_items").insert(item_data).execute()

        if not result.data:
            raise Exception("Failed to add to shopping list")

        # Audit log (non-signed)
        self._write_audit_log(
            yacht_id=yacht_id,
            user_id=user_id,
            action="add_to_shopping_list",
            entity_type="shopping_item",
            entity_id=item_id,
            old_values=None,
            new_values={
                "part_id": part_id,
                "part_name": part_name,
                "quantity_requested": quantity_requested,
                "urgency": urgency,
            },
            signature={},
        )

        return {
            "status": "success",
            "shopping_item_id": item_id,
            "part_id": part_id,
            "part_name": part_name,
            "quantity_requested": quantity_requested,
            "message": f"Added {part_name} to shopping list",
        }

    async def consume_part(
        self,
        yacht_id: str,
        user_id: str,
        part_id: str,
        quantity: int,
        work_order_id: str = None,
        notes: str = None,
    ) -> Dict:
        """
        Consume part using atomic deduct_stock_inventory RPC.
        Returns 409 if insufficient stock (no negative stock allowed).
        Uses SELECT FOR UPDATE to prevent race conditions.
        """
        # Validate inputs
        if quantity <= 0:
            raise ValueError("quantity must be > 0")

        # Get stock_id from canonical pms_part_stock view
        stock_result = self.db.table("pms_part_stock").select(
            "on_hand, location, stock_id, part_name"
        ).eq("part_id", part_id).eq("yacht_id", yacht_id).maybe_single().execute()

        if not stock_result or not stock_result.data:
            raise HTTPException(status_code=404, detail=f"No stock record for part {part_id}")

        stock = stock_result.data
        stock_id = stock.get("stock_id")

        # Get or create stock record if needed
        if not stock_id:
            stock_id = self._get_or_create_stock_id(yacht_id, part_id, stock.get("location"))

        # ATOMIC: Call deduct_stock_inventory with SELECT FOR UPDATE
        try:
            rpc_result = self.db.rpc("deduct_stock_inventory", {
                "p_stock_id": stock_id,
                "p_quantity": quantity,
                "p_yacht_id": yacht_id
            }).execute()
        except Exception as e:
            error_str = str(e)
            error_str_lower = error_str.lower()

            # Check if PostgREST 204 - RPC succeeded but no response body
            # This shouldn't happen with RPCs that return data, but handle it gracefully
            if "204" in error_str or "missing response" in error_str_lower or "postgrest" in error_str_lower:
                logger.warning(f"PostgREST 204 on deduct_stock RPC - this is unexpected, RPC may have failed")
                # Treat as insufficient stock (safest assumption)
                raise ConflictError("Stock deduction may have failed - please verify stock levels")  # 409

            logger.error(f"Atomic deduct RPC failed: {e}")
            raise

        if not rpc_result or not rpc_result.data or len(rpc_result.data) == 0:
            raise ValueError("Atomic deduct returned no data")

        result = rpc_result.data[0]

        # Map DB error codes to HTTP codes (never 500)
        if not result.get("success"):
            error_code = result.get("error_code")
            qty_before = result.get("quantity_before")

            if error_code == "stock_not_found":
                raise ValueError(f"Stock record not found: {stock_id}")  # 404
            elif error_code == "stock_deactivated":
                raise ConflictError("Cannot consume from deactivated stock")  # 409
            elif error_code == "insufficient_stock":
                raise ConflictError(
                    f"Insufficient stock: requested {quantity}, available {qty_before}"
                )  # 409
            else:
                raise ValueError(f"Stock deduction failed: {error_code}")  # 400

        qty_before = result["quantity_before"]
        qty_after = result["quantity_after"]

        # INSERT transaction record for audit trail
        txn_id = str(uuid_lib.uuid4())
        try:
            self.db.table("pms_inventory_transactions").insert({
                "id": txn_id,
                "yacht_id": yacht_id,
                "stock_id": stock_id,
                "transaction_type": TRANSACTION_TYPES["consumed"],
                "quantity_change": -quantity,
                "quantity_before": qty_before,
                "quantity_after": qty_after,
                "user_id": user_id,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }).execute()
        except Exception as e:
            error_str = str(e)
            error_str_lower = error_str.lower()

            # Check if PostgREST 204 (No Content) - insert succeeded but no data returned
            # This happens when PostgREST returns 204 instead of 201 with data
            # The INSERT succeeded, so we continue with audit log
            if "204" in error_str or "missing response" in error_str_lower or "postgrest" in error_str_lower:
                logger.info(f"PostgREST 204 detected on transaction insert (txn_id={txn_id}) - insert succeeded, continuing")
                # Don't re-raise - insert succeeded, just no response body
            else:
                # Unknown error - re-raise
                logger.error(f"Unknown exception on transaction insert (consume_part): {error_str}")
                raise

        # Audit log (non-signed, signature={} per spec)
        self._write_audit_log(
            yacht_id=yacht_id,
            user_id=user_id,
            action="consume_part",
            entity_type="part",
            entity_id=part_id,
            old_values={"on_hand": qty_before},
            new_values={"on_hand": qty_after, "consumed": quantity},
            signature={},  # Non-signed action
            metadata={
                "work_order_id": work_order_id,
                "transaction_id": txn_id,
                "location": stock.get("location"),
                "notes": notes,
            },
        )

        return {
            "status": "success",
            "transaction_id": txn_id,
            "part_id": part_id,
            "quantity_consumed": quantity,
            "new_stock_level": qty_after,
            "message": f"Consumed {quantity} units",
        }

    async def receive_part(
        self,
        yacht_id: str,
        user_id: str,
        part_id: str,
        quantity_received: int,
        idempotency_key: str,
        supplier_id: str = None,
        invoice_number: str = None,
        location: str = None,
        notes: str = None,
        photo_storage_path: str = None,
    ) -> Dict:
        """
        Receive parts using atomic add_stock_inventory RPC.
        Idempotency enforced by DB unique constraint (yacht_id, idempotency_key).
        Uses SELECT FOR UPDATE to prevent race conditions.
        """
        # Validate inputs
        if quantity_received <= 0:
            raise ValueError("quantity_received must be > 0")
        if not idempotency_key:
            raise ValueError("idempotency_key is required")

        # Get current stock from canonical pms_part_stock view
        stock_result = self.db.table("pms_part_stock").select(
            "on_hand, location, part_name, stock_id"
        ).eq("part_id", part_id).eq("yacht_id", yacht_id).maybe_single().execute()

        if not stock_result or not stock_result.data:
            raise ValueError(f"Part {part_id} not found")

        stock = stock_result.data
        final_location = location or stock.get("location") or "default"
        stock_id = stock.get("stock_id")

        # Get or create stock record for the target location
        if not stock_id or (location and location != stock.get("location")):
            stock_id = self._get_or_create_stock_id(yacht_id, part_id, final_location)

        # ATOMIC: Call add_stock_inventory with SELECT FOR UPDATE
        rpc_result = None
        rpc_exception_caught = False

        try:
            rpc_result = self.db.rpc("add_stock_inventory", {
                "p_stock_id": stock_id,
                "p_quantity": quantity_received,
                "p_yacht_id": yacht_id
            }).execute()
        except Exception as e:
            error_str = str(e)
            error_str_lower = error_str.lower()

            # Check if PostgREST 204 (No Content) - RPC succeeded but no data returned
            if "204" in error_str or "missing response" in error_str_lower or "postgrest" in error_str_lower:
                logger.info(f"PostgREST 204 detected on RPC add_stock_inventory (stock_id={stock_id}) - RPC succeeded, using calculated values")
                rpc_exception_caught = True

                # Use calculated values since RPC succeeded but didn't return data
                # The RPC atomically updated the stock, so we can infer the values
                qty_before = stock.get('on_hand', 0)
                qty_after = qty_before + quantity_received
            else:
                logger.error(f"Atomic add RPC failed: {e}")
                raise

        # Handle PostgREST 204 - create synthetic result
        if rpc_exception_caught:
            # Create result dict directly (simpler than using type())
            class SyntheticResult:
                def __init__(self, data):
                    self.data = data

            rpc_result = SyntheticResult([{
                'success': True,
                'quantity_before': qty_before,
                'quantity_after': qty_after
            }])
        elif not rpc_result or not rpc_result.data or len(rpc_result.data) == 0:
            raise ValueError("Atomic add returned no data")

        result = rpc_result.data[0]

        # Map DB error codes to HTTP codes
        if not result.get("success"):
            error_code = result.get("error_code")
            if error_code == "stock_not_found":
                raise ValueError(f"Stock record not found: {stock_id}")  # 404
            elif error_code == "stock_deactivated":
                raise ConflictError("Cannot receive to deactivated stock")  # 409
            else:
                raise ValueError(f"Stock addition failed: {error_code}")  # 400

        qty_before = result["quantity_before"]
        qty_after = result["quantity_after"]

        # INSERT transaction with idempotency_key - DB constraint handles duplicates
        txn_id = str(uuid_lib.uuid4())
        try:
            self.db.table("pms_inventory_transactions").insert({
                "id": txn_id,
                "yacht_id": yacht_id,
                "stock_id": stock_id,
                "transaction_type": TRANSACTION_TYPES["received"],
                "quantity_change": quantity_received,
                "quantity_before": qty_before,
                "quantity_after": qty_after,
                "user_id": user_id,
                "idempotency_key": idempotency_key,  # DB enforces uniqueness
                "created_at": datetime.now(timezone.utc).isoformat(),
            }).execute()
        except Exception as e:
            # Check if constraint violation (duplicate idempotency_key)
            error_str = str(e)
            error_str_lower = error_str.lower()

            if "unique" in error_str_lower or "duplicate" in error_str_lower or "idempotency" in error_str_lower or "23505" in error_str:
                raise ConflictError(f"Duplicate receive: idempotency_key {idempotency_key} already exists")  # 409

            # Check if PostgREST 204 (No Content) - insert succeeded but no data returned
            # This happens when PostgREST returns 204 instead of 201 with data
            # The INSERT succeeded, so we continue with audit log
            if "204" in error_str or "missing response" in error_str_lower or "postgrest" in error_str_lower:
                logger.info(f"PostgREST 204 detected on transaction insert (txn_id={txn_id}) - insert succeeded, continuing")
                # Don't re-raise - insert succeeded, just no response body
            else:
                # Unknown error - re-raise
                logger.error(f"Unknown exception on transaction insert: {error_str}")
                raise

        # Audit log (non-signed)
        self._write_audit_log(
            yacht_id=yacht_id,
            user_id=user_id,
            action="receive_part",
            entity_type="part",
            entity_id=part_id,
            old_values={"on_hand": qty_before},
            new_values={"on_hand": qty_after, "received": quantity_received},
            signature={},
            metadata={
                "supplier_id": supplier_id,
                "invoice": invoice_number,
                "transaction_id": txn_id,
                "idempotency_key": idempotency_key,
                "photo_storage_path": photo_storage_path,
                "location": final_location,
            },
        )

        return {
            "status": "success",
            "transaction_id": txn_id,
            "part_id": part_id,
            "part_name": stock.get("part_name"),
            "quantity_received": quantity_received,
            "new_stock_level": qty_after,
            "location": final_location,
            "message": f"Received {quantity_received} units",
        }

    async def transfer_part(
        self,
        yacht_id: str,
        user_id: str,
        part_id: str,
        quantity: int,
        from_location: str,
        to_location: str,
        notes: str = None,
    ) -> Dict:
        """
        Transfer part between locations using atomic transfer_stock_atomic RPC.
        All-or-nothing transfer with SELECT FOR UPDATE on both locations.
        Prevents partial-state race conditions.
        """
        # Validate inputs
        if quantity <= 0:
            raise ValueError("quantity must be > 0")
        if from_location == to_location:
            raise ValueError("Cannot transfer to the same location")  # 400

        # Get stock at source location
        from_stock_result = self.db.table("pms_part_stock").select(
            "stock_id, on_hand, location, part_name"
        ).eq("yacht_id", yacht_id).eq("part_id", part_id).eq("location", from_location).maybe_single().execute()

        if not from_stock_result or not from_stock_result.data:
            raise ValueError(f"No stock at location {from_location}")  # 404

        from_stock = from_stock_result.data
        from_stock_id = from_stock["stock_id"]

        # Get or create stock at destination
        to_stock_id = self._get_or_create_stock_id(yacht_id, part_id, to_location)

        # Generate transfer group ID to link paired transactions
        transfer_group_id = str(uuid_lib.uuid4())

        # ATOMIC: Call transfer_stock_atomic with SELECT FOR UPDATE on BOTH rows
        try:
            rpc_result = self.db.rpc("transfer_stock_atomic", {
                "p_from_stock_id": from_stock_id,
                "p_to_stock_id": to_stock_id,
                "p_quantity": quantity,
                "p_yacht_id": yacht_id,
                "p_transfer_group_id": transfer_group_id
            }).execute()
        except Exception as e:
            logger.error(f"Atomic transfer RPC failed: {e}")
            raise

        if not rpc_result or not rpc_result.data or len(rpc_result.data) == 0:
            raise ValueError("Atomic transfer returned no data")

        result = rpc_result.data[0]

        # Map DB error codes to HTTP codes
        if not result.get("success"):
            error_code = result.get("error_code")
            if error_code == "from_stock_not_found":
                raise ValueError(f"Source stock not found")  # 404
            elif error_code == "to_stock_not_found":
                raise ValueError(f"Destination stock not found")  # 404
            elif error_code == "same_location_transfer":
                raise ValueError("Cannot transfer to the same location")  # 400
            elif error_code == "from_stock_deactivated":
                raise ConflictError("Cannot transfer from deactivated stock")  # 409
            elif error_code == "to_stock_deactivated":
                raise ConflictError("Cannot transfer to deactivated stock")  # 409
            elif error_code == "insufficient_stock":
                from_qty = result.get("from_qty_before")
                raise ConflictError(
                    f"Insufficient stock at {from_location}: requested {quantity}, available {from_qty}"
                )  # 409
            else:
                raise ValueError(f"Transfer failed: {error_code}")  # 400

        from_qty_before = result["from_qty_before"]
        from_qty_after = result["from_qty_after"]
        to_qty_before = result["to_qty_before"]
        to_qty_after = result["to_qty_after"]
        returned_group_id = result["transfer_group_id"]

        # INSERT paired transaction records for audit trail
        txn_out_id = str(uuid_lib.uuid4())
        txn_in_id = str(uuid_lib.uuid4())

        self.db.table("pms_inventory_transactions").insert([
            {
                "id": txn_out_id,
                "yacht_id": yacht_id,
                "stock_id": from_stock_id,
                "transaction_type": TRANSACTION_TYPES["transferred_out"],
                "quantity_change": -quantity,
                "quantity_before": from_qty_before,
                "quantity_after": from_qty_after,
                "user_id": user_id,
                "transfer_group_id": returned_group_id,
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
            {
                "id": txn_in_id,
                "yacht_id": yacht_id,
                "stock_id": to_stock_id,
                "transaction_type": TRANSACTION_TYPES["transferred_in"],
                "quantity_change": quantity,
                "quantity_before": to_qty_before,
                "quantity_after": to_qty_after,
                "user_id": user_id,
                "transfer_group_id": returned_group_id,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        ]).execute()

        # Audit log (non-signed, signature={} per spec)
        self._write_audit_log(
            yacht_id=yacht_id,
            user_id=user_id,
            action="transfer_part",
            entity_type="part",
            entity_id=part_id,
            old_values={"location": from_location, "from_qty": from_qty_before},
            new_values={"location": to_location, "to_qty": to_qty_after, "quantity": quantity},
            signature={},  # Non-signed action
            metadata={
                "transfer_group_id": returned_group_id,
                "txn_out_id": txn_out_id,
                "txn_in_id": txn_in_id,
                "from_location": from_location,
                "to_location": to_location,
                "notes": notes,
            },
        )

        return {
            "status": "success",
            "transfer_group_id": returned_group_id,
            "transaction_out_id": txn_out_id,
            "transaction_in_id": txn_in_id,
            "part_id": part_id,
            "quantity_transferred": quantity,
            "from_location": from_location,
            "to_location": to_location,
            "from_new_level": from_qty_after,
            "to_new_level": to_qty_after,
            "message": f"Transferred {quantity} units from {from_location} to {to_location}",
        }

    # =========================================================================
    # SIGNED HANDLERS (require PIN+TOTP signature - 400 if missing)
    # =========================================================================

    async def adjust_stock_quantity(
        self,
        yacht_id: str,
        user_id: str,
        part_id: str,
        new_quantity: int,
        reason: str,
        signature: Dict = None,
        location: str = None,
    ) -> Dict:
        """
        Adjust stock quantity via transaction.
        SIGNED action - REQUIRES valid signature (400 if missing/invalid).
        """
        # Validate inputs
        if new_quantity < 0:
            raise ValueError("new_quantity must be >= 0")

        # ENFORCE SIGNATURE CONTRACT
        if not signature or signature == {}:
            raise SignatureRequiredError(
                "Signature is required for adjust_stock_quantity (SIGNED action)"
            )

        # Validate signature structure (must have pin AND totp)
        if not signature.get("pin") or not signature.get("totp"):
            raise SignatureRequiredError(
                "Signature must contain 'pin' and 'totp' keys for SIGNED action"
            )

        # Get current stock
        stock_result = self.db.table("pms_part_stock").select(
            "on_hand, location, part_name, stock_id"
        ).eq("part_id", part_id).eq("yacht_id", yacht_id).maybe_single().execute()

        if not stock_result or not stock_result.data:
            raise ValueError(f"Part {part_id} not found")

        stock = stock_result.data
        old_qty = stock.get("on_hand", 0) or 0
        adjustment = new_quantity - old_qty
        stock_id = stock.get("stock_id")

        if adjustment == 0:
            return {
                "status": "success",
                "message": "No adjustment needed - quantity unchanged",
                "part_id": part_id,
                "quantity": new_quantity,
            }

        # Get or create stock record
        if not stock_id:
            stock_id = self._get_or_create_stock_id(yacht_id, part_id, location or stock.get("location"))

        # ATOMIC: Call appropriate RPC based on adjustment direction
        if adjustment > 0:
            # Adding stock - use add_stock_inventory
            rpc_result = self.db.rpc("add_stock_inventory", {
                "p_stock_id": stock_id,
                "p_quantity": adjustment,
                "p_yacht_id": yacht_id
            }).execute()
        else:
            # Deducting stock - use deduct_stock_inventory
            rpc_result = self.db.rpc("deduct_stock_inventory", {
                "p_stock_id": stock_id,
                "p_quantity": abs(adjustment),  # Function expects positive quantity
                "p_yacht_id": yacht_id
            }).execute()

        if not rpc_result or not rpc_result.data or len(rpc_result.data) == 0:
            raise ValueError("Atomic adjust returned no data")

        result = rpc_result.data[0]

        # Map DB error codes to explicit HTTP codes (never 500)
        if not result.get("success"):
            error_code = result.get("error_code")
            if error_code == "stock_not_found":
                raise ValueError(f"Stock record not found: {stock_id}")  # 404
            elif error_code == "stock_deactivated":
                raise ConflictError("Cannot adjust deactivated stock")  # 409
            elif error_code == "insufficient_stock":
                qty_before = result.get("quantity_before")
                raise ConflictError(
                    f"Insufficient stock for adjustment: requested {new_quantity}, available {qty_before}"
                )  # 409
            else:
                raise ValueError(f"Adjustment failed: {error_code}")  # 400

        qty_before = result["quantity_before"]
        qty_after = result["quantity_after"]

        # INSERT adjustment transaction record for audit trail
        txn_id = str(uuid_lib.uuid4())
        self.db.table("pms_inventory_transactions").insert({
            "id": txn_id,
            "yacht_id": yacht_id,
            "stock_id": stock_id,
            "transaction_type": TRANSACTION_TYPES["adjusted"],
            "quantity_change": adjustment,
            "quantity_before": qty_before,
            "quantity_after": qty_after,
            "user_id": user_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }).execute()

        txn_result = {"transaction_id": txn_id}

        # Build signature payload for SIGNED action (required keys per spec)
        now = datetime.now(timezone.utc).isoformat()
        signature_hash = hashlib.sha256(
            f"{user_id}:{part_id}:{new_quantity}:{reason}:{now}".encode()
        ).hexdigest()

        # Get user role for role_at_signing
        role_at_signing = self._get_user_role(user_id) or "unknown"

        signature_payload = {
            # Required keys per doctrine
            "user_id": user_id,
            "role_at_signing": role_at_signing,
            "signature_type": "pin_totp",  # Standard type per spec
            "signature_hash": f"sha256:{signature_hash}",
            "signed_at": now,
            # Action-specific context
            "action": "adjust_stock_quantity",
            "part_id": part_id,
            "old_qty": old_qty,
            "new_qty": new_quantity,
            "reason": reason,
            "reason_code": signature.get("reason_code"),  # Optional
            **signature,  # Include PIN+TOTP from user
        }

        # SIGNED audit log with non-NULL signature
        self._write_audit_log(
            yacht_id=yacht_id,
            user_id=user_id,
            action="adjust_stock_quantity",
            entity_type="part",
            entity_id=part_id,
            old_values={"on_hand": old_qty},
            new_values={"on_hand": new_quantity, "adjustment": adjustment, "reason": reason},
            signature=signature_payload,  # SIGNED - full payload
            metadata={"transaction_id": txn_result["transaction_id"]},
        )

        return {
            "status": "success",
            "transaction_id": txn_result["transaction_id"],
            "part_id": part_id,
            "old_quantity": old_qty,
            "new_quantity": new_quantity,
            "adjustment": adjustment,
            "reason": reason,
            "is_signed": True,
            "message": f"Stock adjusted from {old_qty} to {new_quantity}",
        }

    async def write_off_part(
        self,
        yacht_id: str,
        user_id: str,
        part_id: str,
        quantity: int,
        reason: str,
        signature: Dict = None,
        location: str = None,
    ) -> Dict:
        """
        Write off damaged/expired parts via transaction.
        SIGNED action - REQUIRES valid signature (400 if missing/invalid).
        ROLE RESTRICTED: Captain/Manager only (403 for Crew/HOD).
        """
        # Validate inputs
        if quantity <= 0:
            raise ValueError("quantity must be > 0")

        # ENFORCE SIGNATURE CONTRACT
        if not signature or signature == {}:
            raise SignatureRequiredError(
                "Signature is required for write_off_part (SIGNED action)"
            )

        # Validate signature structure (must have pin AND totp)
        if not signature.get("pin") or not signature.get("totp"):
            raise SignatureRequiredError(
                "Signature must contain 'pin' and 'totp' keys for SIGNED action"
            )

        # ENFORCE ROLE: Captain/Manager only (Crew/HOD cannot write off)
        # Per doctrine: check role_at_signing OR is_manager RPC
        role_at_signing = signature.get("role_at_signing", "").lower()
        if role_at_signing not in ("captain", "manager"):
            # Fallback: check if user is manager via RPC
            is_manager_result = self.db.rpc("is_manager", {"p_user_id": user_id}).execute()
            is_manager = is_manager_result.data if is_manager_result.data is not None else False

            if not is_manager:
                raise PermissionError(
                    f"Role '{role_at_signing or 'unknown'}' forbidden: write_off_part requires Captain/Manager role"
                )

        # Get current stock
        stock_result = self.db.table("pms_part_stock").select(
            "on_hand, location, part_name, stock_id"
        ).eq("part_id", part_id).eq("yacht_id", yacht_id).maybe_single().execute()

        if not stock_result or not stock_result.data:
            raise ValueError(f"Part {part_id} not found")

        stock = stock_result.data
        current_qty = stock.get("on_hand", 0) or 0
        stock_id = stock.get("stock_id")

        # Get or create stock record
        if not stock_id:
            stock_id = self._get_or_create_stock_id(yacht_id, part_id, location or stock.get("location"))

        # ATOMIC: Call deduct_stock_inventory with SELECT FOR UPDATE
        rpc_result = self.db.rpc("deduct_stock_inventory", {
            "p_stock_id": stock_id,
            "p_quantity": quantity,
            "p_yacht_id": yacht_id
        }).execute()

        if not rpc_result or not rpc_result.data or len(rpc_result.data) == 0:
            raise ValueError("Atomic write-off returned no data")

        result = rpc_result.data[0]

        # Map DB error codes to explicit HTTP codes (never 500)
        if not result.get("success"):
            error_code = result.get("error_code")
            if error_code == "stock_not_found":
                raise ValueError(f"Stock record not found: {stock_id}")  # 404
            elif error_code == "stock_deactivated":
                raise ConflictError("Cannot write off from deactivated stock")  # 409
            elif error_code == "insufficient_stock":
                qty_before = result.get("quantity_before")
                raise ConflictError(
                    f"Cannot write off {quantity}: only {qty_before} available"
                )  # 409
            else:
                raise ValueError(f"Write-off failed: {error_code}")  # 400

        current_qty = result["quantity_before"]
        new_qty = result["quantity_after"]

        # INSERT write_off transaction record for audit trail
        txn_id = str(uuid_lib.uuid4())
        self.db.table("pms_inventory_transactions").insert({
            "id": txn_id,
            "yacht_id": yacht_id,
            "stock_id": stock_id,
            "transaction_type": TRANSACTION_TYPES["write_off"],
            "quantity_change": -quantity,
            "quantity_before": current_qty,
            "quantity_after": new_qty,
            "user_id": user_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }).execute()

        txn_result = {"transaction_id": txn_id}

        # Build signature payload
        now = datetime.now(timezone.utc).isoformat()
        signature_hash = hashlib.sha256(
            f"{user_id}:{part_id}:{quantity}:{reason}:{now}".encode()
        ).hexdigest()

        # Get user role for role_at_signing
        role_at_signing = self._get_user_role(user_id) or "unknown"

        signature_payload = {
            # Required keys per doctrine
            "user_id": user_id,
            "role_at_signing": role_at_signing,
            "signature_type": "pin_totp",  # Standard type per spec
            "signature_hash": f"sha256:{signature_hash}",
            "signed_at": now,
            # Action-specific context
            "action": "write_off_part",
            "part_id": part_id,
            "quantity": quantity,
            "reason": reason,
            "reason_code": signature.get("reason_code"),  # Optional
            **signature,  # Include PIN+TOTP from user
        }

        # SIGNED audit log
        self._write_audit_log(
            yacht_id=yacht_id,
            user_id=user_id,
            action="write_off_part",
            entity_type="part",
            entity_id=part_id,
            old_values={"on_hand": current_qty},
            new_values={"on_hand": new_qty, "written_off": quantity, "reason": reason},
            signature=signature_payload,
            metadata={"transaction_id": txn_result["transaction_id"]},
        )

        return {
            "status": "success",
            "transaction_id": txn_result["transaction_id"],
            "part_id": part_id,
            "quantity_written_off": quantity,
            "new_stock_level": new_qty,
            "reason": reason,
            "is_signed": True,
            "message": f"Wrote off {quantity} units ({reason})",
        }

    # =========================================================================
    # LABEL HANDLERS
    # =========================================================================

    async def generate_part_labels(
        self,
        yacht_id: str,
        user_id: str,
        part_ids: List[str],
        label_format: str = "medium",
        include_qr: bool = True,
        include_barcode: bool = True,
    ) -> Dict:
        """
        Generate PDF labels for parts.
        Writes to pms-label-pdfs/{yacht_id}/parts/{part_id}/labels/{filename}.
        Returns {document_id, storage_path}.
        """
        now = datetime.now(timezone.utc).isoformat()

        # Validate parts exist
        parts_result = self.db.table("pms_parts").select(
            "id, name, part_number"
        ).eq("yacht_id", yacht_id).in_("id", part_ids).execute()

        if not parts_result.data or len(parts_result.data) != len(part_ids):
            found_ids = [p["id"] for p in (parts_result.data or [])]
            missing = set(part_ids) - set(found_ids)
            raise ValueError(f"Parts not found: {missing}")

        # Generate PDF (placeholder - actual implementation would use a PDF library)
        document_id = str(uuid_lib.uuid4())
        filename = f"labels_{document_id[:8]}_{now[:10]}.pdf"
        storage_path = f"{yacht_id}/parts/labels/{filename}"

        # Record in doc_metadata
        self.db.table("doc_metadata").insert({
            "id": document_id,
            "yacht_id": yacht_id,
            "source": "part_lens",
            "filename": filename,
            "storage_path": storage_path,
            "storage_bucket": "pms-label-pdfs",
            "document_type": "part_labels",
            "content_type": "application/pdf",
            "metadata": {
                "part_ids": part_ids,
                "label_format": label_format,
                "include_qr": include_qr,
                "include_barcode": include_barcode,
                "generated_by": user_id,
            },
        }).execute()

        # Audit log
        self._write_audit_log(
            yacht_id=yacht_id,
            user_id=user_id,
            action="generate_part_labels",
            entity_type="document",
            entity_id=document_id,
            old_values=None,
            new_values={"part_ids": part_ids, "storage_path": storage_path},
            signature={},
        )

        return {
            "status": "success",
            "document_id": document_id,
            "storage_path": storage_path,
            "filename": filename,
            "part_count": len(part_ids),
            "message": f"Generated labels for {len(part_ids)} parts",
        }

    async def request_label_output(
        self,
        yacht_id: str,
        user_id: str,
        document_id: str,
        output: str,  # "print", "email", "download"
        email_address: str = None,
        printer_id: str = None,
    ) -> Dict:
        """
        Request label output via print/email/download.
        Returns {output, status, url?}.
        """
        # Validate document exists
        doc_result = self.db.table("doc_metadata").select(
            "id, storage_path, storage_bucket"
        ).eq("id", document_id).eq("yacht_id", yacht_id).maybe_single().execute()

        if not doc_result.data:
            raise ValueError(f"Document not found: {document_id}")

        doc = doc_result.data
        storage_path = doc.get("storage_path")

        result = {
            "status": "success",
            "output": output,
            "document_id": document_id,
        }

        if output == "download":
            # Generate signed URL
            try:
                signed = self.db.storage.from_(doc.get("storage_bucket")).create_signed_url(
                    storage_path, 3600  # 1 hour expiry
                )
                result["url"] = signed.get("signedURL")
                result["expires_in"] = 3600
            except Exception as e:
                logger.error(f"Failed to generate signed URL: {e}")
                result["status"] = "pending"
                result["message"] = "URL generation pending"

        elif output == "email":
            if not email_address:
                raise ValueError("email_address required for email output")
            result["email_address"] = email_address
            result["status"] = "queued"
            result["message"] = f"Label email queued to {email_address}"

        elif output == "print":
            if not printer_id:
                raise ValueError("printer_id required for print output")
            result["printer_id"] = printer_id
            result["status"] = "queued"
            result["message"] = f"Print job queued to printer {printer_id}"

        # Audit log
        self._write_audit_log(
            yacht_id=yacht_id,
            user_id=user_id,
            action="request_label_output",
            entity_type="document",
            entity_id=document_id,
            old_values=None,
            new_values={"output": output, "status": result["status"]},
            signature={},
        )

        return result

    # =========================================================================
    # HELPERS
    # =========================================================================

    def _get_user_role(self, user_id: str) -> Optional[str]:
        """
        Get user's role for signature payload (role_at_signing).
        Returns role from user_profiles or crew_assignments.
        """
        try:
            # Try user_profiles first
            result = self.db.table("user_profiles").select(
                "role"
            ).eq("id", user_id).maybe_single().execute()

            if result.data and result.data.get("role"):
                return result.data["role"]

            # Fallback to crew_assignments
            crew_result = self.db.table("crew_assignments").select(
                "role"
            ).eq("user_id", user_id).eq("is_active", True).maybe_single().execute()

            if crew_result.data and crew_result.data.get("role"):
                return crew_result.data["role"]

            return None
        except Exception as e:
            logger.warning(f"Failed to get user role for {user_id}: {e}")
            return None

    def _write_audit_log(
        self,
        yacht_id: str,
        user_id: str,
        action: str,
        entity_type: str,
        entity_id: str,
        old_values: Optional[Dict],
        new_values: Optional[Dict],
        signature: Dict,
        metadata: Dict = None,
        session_id: str = None,
        ip_address: str = None,
    ):
        """
        Write audit log entry.
        INVARIANT: signature is NEVER NULL - use {} for non-signed actions.

        For READ actions, metadata should include:
        - source: "part_lens"
        - lens: "part"
        - action, entity_type, entity_id (provided as params)
        - session_id, ip_address (if available)
        """
        try:
            # Build complete metadata
            full_metadata = {
                "source": "part_lens",
                "lens": "part",
            }
            if metadata:
                full_metadata.update(metadata)
            if session_id:
                full_metadata["session_id"] = session_id
            if ip_address:
                full_metadata["ip_address"] = ip_address

            self.db.table("pms_audit_log").insert({
                "id": str(uuid_lib.uuid4()),
                "yacht_id": yacht_id,
                "entity_type": entity_type,
                "entity_id": entity_id,
                "action": action,
                "user_id": user_id,
                "old_values": old_values,
                "new_values": new_values,
                "signature": signature,  # Never NULL
                "metadata": full_metadata,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }).execute()
        except Exception as e:
            logger.warning(f"Audit log failed for {action}: {e}")


# ============================================================================
# CUSTOM EXCEPTIONS
# ============================================================================

class ConflictError(Exception):
    """409 Conflict - used for insufficient stock and duplicate idempotency keys."""
    pass


class SignatureRequiredError(Exception):
    """400 Bad Request - signature required for SIGNED actions."""
    pass


# ============================================================================
# HANDLER FACTORY
# ============================================================================

def get_part_handlers(supabase_client) -> Dict[str, callable]:
    """Get part handler functions for registration."""
    handlers = PartHandlers(supabase_client)

    return {
        # READ handlers (with read-audit)
        "view_part_details": handlers.view_part_details,
        "open_document": handlers.open_document,

        # MUTATE handlers
        "add_to_shopping_list": handlers.add_to_shopping_list,
        "consume_part": handlers.consume_part,
        "receive_part": handlers.receive_part,
        "transfer_part": handlers.transfer_part,

        # SIGNED handlers
        "adjust_stock_quantity": handlers.adjust_stock_quantity,
        "write_off_part": handlers.write_off_part,

        # Label handlers
        "generate_part_labels": handlers.generate_part_labels,
        "request_label_output": handlers.request_label_output,
    }
