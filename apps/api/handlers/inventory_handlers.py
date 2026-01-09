"""
Inventory & Parts Handlers
===========================

P0 Actions for inventory management:
- check_stock_level (P0 Action #6) - READ
- log_part_usage (P0 Action #7) - MUTATE

Based on specs: /P0_ACTION_CONTRACTS.md - Cluster 04: INVENTORY_PARTS
"""

from datetime import datetime, timezone, timedelta
from typing import Dict, Optional, List
import logging
import uuid

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from actions.action_response_schema import ResponseBuilder

logger = logging.getLogger(__name__)


class InventoryHandlers:
    """
    Handlers for inventory and parts management actions.

    Implements P0 actions:
    - check_stock_level (READ)
    - log_part_usage (MUTATE)
    """

    def __init__(self, supabase_client):
        self.db = supabase_client

    # =========================================================================
    # P0 ACTION #6: check_stock_level
    # =========================================================================

    async def check_stock_level_execute(
        self,
        part_id: str,
        yacht_id: str,
        user_id: str
    ) -> Dict:
        """
        POST /v1/actions/execute (action=check_stock_level)

        Check current stock level for a part.

        READ action - execute only (no prefill or preview needed).

        Returns:
        - Part details (name, part_number, category, unit)
        - Stock info (quantity_on_hand, minimum_quantity, stock_status, location)
        - Usage stats (last 30 days, estimated runout)
        - Last counted info (accountability: who counted, when)

        Stock status logic:
        - OUT_OF_STOCK: quantity_on_hand == 0
        - LOW_STOCK: quantity_on_hand > 0 AND quantity_on_hand <= minimum_quantity
        - IN_STOCK: quantity_on_hand > minimum_quantity
        """
        try:
            # Get part details with stock info
            part_result = self.db.table("pms_parts").select(
                "id, name, part_number, category, description, unit, "
                "quantity_on_hand, minimum_quantity, maximum_quantity, location, "
                "last_counted_at, last_counted_by, "
                "counter:last_counted_by(id, full_name)"
            ).eq("id", part_id).eq("yacht_id", yacht_id).maybe_single().execute()

            if not part_result.data:
                return ResponseBuilder.error(
                    action="check_stock_level",
                    error_code="PART_NOT_FOUND",
                    message=f"Part not found: {part_id}"
                )

            part = part_result.data
            quantity_on_hand = part.get("quantity_on_hand", 0)
            minimum_quantity = part.get("minimum_quantity", 0)
            maximum_quantity = part.get("maximum_quantity")

            # Determine stock status
            if quantity_on_hand == 0:
                stock_status = "OUT_OF_STOCK"
            elif quantity_on_hand <= minimum_quantity:
                stock_status = "LOW_STOCK"
            elif maximum_quantity and quantity_on_hand > maximum_quantity:
                stock_status = "OVERSTOCKED"
            else:
                stock_status = "IN_STOCK"

            # Get usage stats (last 30 days)
            thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
            usage_result = self.db.table("pms_part_usage").select(
                "quantity, used_at"
            ).eq("yacht_id", yacht_id).eq(
                "part_id", part_id
            ).gte(
                "used_at", thirty_days_ago.isoformat()
            ).execute()

            # Calculate usage stats
            usage_last_30_days = sum(u.get("quantity", 0) for u in usage_result.data) if usage_result.data else 0
            average_monthly = usage_last_30_days  # Already 30 days

            # Estimate runout days (if usage > 0)
            estimated_runout_days = None
            if usage_last_30_days > 0 and quantity_on_hand > 0:
                daily_usage = usage_last_30_days / 30
                estimated_runout_days = int(quantity_on_hand / daily_usage)

            # Get counter name
            counter_name = "Unknown"
            if part.get("counter"):
                counter_name = part["counter"].get("full_name", "Unknown")

            # Build response
            return ResponseBuilder.success(
                action="check_stock_level",
                result={
                    "part": {
                        "id": part["id"],
                        "name": part["name"],
                        "part_number": part.get("part_number", ""),
                        "category": part.get("category", ""),
                        "description": part.get("description", ""),
                        "unit": part.get("unit", "ea")
                    },
                    "stock": {
                        "quantity_on_hand": quantity_on_hand,
                        "minimum_quantity": minimum_quantity,
                        "maximum_quantity": maximum_quantity,
                        "stock_status": stock_status,
                        "location": part.get("location", ""),
                        "last_counted_at": part.get("last_counted_at"),
                        "last_counted_by": counter_name
                    },
                    "usage_stats": {
                        "last_30_days": usage_last_30_days,
                        "average_monthly": average_monthly,
                        "estimated_runout_days": estimated_runout_days
                    },
                    "pending_orders": []  # TODO: Implement when purchase orders exist
                }
            )

        except Exception as e:
            logger.exception(f"Error checking stock level for part {part_id}")
            return ResponseBuilder.error(
                action="check_stock_level",
                error_code="INTERNAL_ERROR",
                message=f"Failed to check stock level: {str(e)}"
            )


    # =========================================================================
    # P0 ACTION #7: log_part_usage
    # =========================================================================

    async def log_part_usage_prefill(
        self,
        part_id: str,
        yacht_id: str,
        user_id: str,
        work_order_id: Optional[str] = None
    ) -> Dict:
        """
        GET /v1/actions/log_part_usage/prefill

        Pre-fill part usage form.

        Returns:
        - Part details (name, part_number, unit, stock_available)
        - Work order details (if work_order_id provided)
        - Suggested quantity = 1
        - Usage reason = "work_order" if WO provided, else "other"
        """
        try:
            # Get part details
            part_result = self.db.table("pms_parts").select(
                "id, name, part_number, unit, quantity_on_hand"
            ).eq("id", part_id).eq("yacht_id", yacht_id).maybe_single().execute()

            if not part_result.data:
                return {
                    "status": "error",
                    "error_code": "PART_NOT_FOUND",
                    "message": f"Part not found: {part_id}"
                }

            part = part_result.data

            prefill_data = {
                "part_id": part["id"],
                "part_name": part["name"],
                "part_number": part.get("part_number", ""),
                "unit": part.get("unit", "ea"),
                "stock_available": part.get("quantity_on_hand", 0),
                "suggested_quantity": 1
            }

            # Add work order details if provided
            if work_order_id:
                wo_result = self.db.table("pms_work_orders").select(
                    "id, number, title"
                ).eq("id", work_order_id).eq("yacht_id", yacht_id).maybe_single().execute()

                if wo_result.data:
                    prefill_data["work_order_id"] = work_order_id
                    prefill_data["work_order_number"] = wo_result.data.get("number", "")
                    prefill_data["usage_reason"] = "work_order"
                else:
                    prefill_data["usage_reason"] = "other"
            else:
                prefill_data["usage_reason"] = "other"

            return {
                "status": "success",
                "prefill_data": prefill_data
            }

        except Exception as e:
            logger.exception(f"Error prefilling log_part_usage for part {part_id}")
            return {
                "status": "error",
                "error_code": "INTERNAL_ERROR",
                "message": f"Failed to prefill: {str(e)}"
            }

    async def log_part_usage_preview(
        self,
        part_id: str,
        quantity: float,
        yacht_id: str,
        user_id: str,
        work_order_id: Optional[str] = None,
        equipment_id: Optional[str] = None,
        usage_reason: str = "other",
        notes: Optional[str] = None
    ) -> Dict:
        """
        POST /v1/actions/log_part_usage/preview

        Preview inventory deduction before execution.

        Shows:
        - What will be deducted
        - Current stock → new stock
        - Warnings if stock goes to zero or below minimum
        """
        try:
            # Get part details
            part_result = self.db.table("pms_parts").select(
                "id, name, part_number, unit, quantity_on_hand, minimum_quantity"
            ).eq("id", part_id).eq("yacht_id", yacht_id).maybe_single().execute()

            if not part_result.data:
                return ResponseBuilder.error(
                    action="log_part_usage",
                    error_code="PART_NOT_FOUND",
                    message=f"Part not found: {part_id}"
                )

            part = part_result.data
            current_stock = part.get("quantity_on_hand", 0)
            minimum_quantity = part.get("minimum_quantity", 0)
            after_usage = current_stock - quantity

            # Get user name
            user_result = self.db.table("user_profiles").select(
                "full_name"
            ).eq("id", user_id).maybe_single().execute()
            user_name = user_result.data.get("full_name", "Unknown") if user_result.data else "Unknown"

            # Get work order number if provided
            wo_number = None
            if work_order_id:
                wo_result = self.db.table("pms_work_orders").select(
                    "number"
                ).eq("id", work_order_id).maybe_single().execute()
                if wo_result.data:
                    wo_number = wo_result.data.get("number", "")

            # Build preview
            changes = {
                "part": f"{part['name']} ({part.get('part_number', '')})",
                "quantity": f"{quantity} {part.get('unit', 'ea')}",
                "used_by": user_name,
                "used_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
            }

            if wo_number:
                changes["work_order"] = wo_number

            side_effects = [
                f"Inventory will be DEDUCTED by {quantity} {part.get('unit', 'ea')}",
                "Part usage log entry will be created",
                f"Stock level will change from {current_stock} → {after_usage}",
                "Audit log entry will be created",
                "Usage will be attributed to your user account"
            ]

            # Check for warnings
            warnings = []
            warning_obj = None

            if after_usage < 0:
                warnings.append(f"❌ INSUFFICIENT STOCK: Current stock ({current_stock}) is less than requested quantity ({quantity})")
                warning_obj = "INSUFFICIENT_STOCK"
            elif after_usage == 0:
                warnings.append(f"⚠️  Stock will be ZERO after this usage")
            elif after_usage <= minimum_quantity:
                warnings.append(f"⚠️  Stock will be LOW after this usage (below minimum: {minimum_quantity})")

            inventory_changes = [{
                "part": f"{part['name']} ({part.get('part_number', '')})",
                "current_stock": current_stock,
                "after_usage": after_usage,
                "warning": warning_obj
            }]

            return {
                "status": "success",
                "preview": {
                    "action": "log_part_usage",
                    "summary": "You are about to log part usage:",
                    "changes": changes,
                    "side_effects": side_effects,
                    "inventory_changes": inventory_changes,
                    "requires_signature": False,
                    "warnings": warnings
                }
            }

        except Exception as e:
            logger.exception(f"Error previewing log_part_usage for part {part_id}")
            return ResponseBuilder.error(
                action="log_part_usage",
                error_code="INTERNAL_ERROR",
                message=f"Failed to preview: {str(e)}"
            )

    async def log_part_usage_execute(
        self,
        part_id: str,
        quantity: float,
        usage_reason: str,
        yacht_id: str,
        user_id: str,
        work_order_id: Optional[str] = None,
        equipment_id: Optional[str] = None,
        notes: Optional[str] = None
    ) -> Dict:
        """
        POST /v1/actions/execute (action=log_part_usage)

        Execute part usage logging with inventory deduction.

        Uses deduct_part_inventory() helper function for atomic operation.

        Creates:
        - pms_part_usage log entry
        - Updates pms_parts.quantity_on_hand
        - Creates audit log entry

        Returns error if insufficient stock.
        """
        try:
            # Validate quantity
            if quantity <= 0:
                return ResponseBuilder.error(
                    action="log_part_usage",
                    error_code="INVALID_QUANTITY",
                    message="Quantity must be positive"
                )

            # Validate work order exists if provided
            if work_order_id:
                wo_result = self.db.table("pms_work_orders").select(
                    "id"
                ).eq("id", work_order_id).eq("yacht_id", yacht_id).maybe_single().execute()
                if not wo_result.data:
                    return ResponseBuilder.error(
                        action="log_part_usage",
                        error_code="WO_NOT_FOUND",
                        message=f"Work order not found: {work_order_id}"
                    )

            # Call deduct_part_inventory() helper function
            # This does atomic operation: row lock, check stock, deduct, create usage log
            try:
                deduct_result = self.db.rpc(
                    "deduct_part_inventory",
                    {
                        "p_yacht_id": yacht_id,
                        "p_part_id": part_id,
                        "p_quantity": int(quantity) if quantity == int(quantity) else quantity,
                        "p_work_order_id": work_order_id,
                        "p_equipment_id": equipment_id,
                        "p_usage_reason": usage_reason,
                        "p_notes": notes,
                        "p_used_by": user_id
                    }
                ).execute()

                # If function returned false, insufficient stock
                if not deduct_result.data:
                    return ResponseBuilder.error(
                        action="log_part_usage",
                        error_code="INSUFFICIENT_STOCK",
                        message="Not enough stock to deduct requested quantity"
                    )

            except Exception as e:
                # Function doesn't exist yet (migrations not deployed)
                logger.warning(f"deduct_part_inventory() function not found. Using manual deduction.")

                # Manual deduction (fallback)
                # Get current stock with row lock
                part_result = self.db.table("pms_parts").select(
                    "id, name, part_number, quantity_on_hand, minimum_quantity"
                ).eq("id", part_id).eq("yacht_id", yacht_id).maybe_single().execute()

                if not part_result.data:
                    return ResponseBuilder.error(
                        action="log_part_usage",
                        error_code="PART_NOT_FOUND",
                        message=f"Part not found: {part_id}"
                    )

                part = part_result.data
                current_stock = part.get("quantity_on_hand", 0)

                # Check sufficient stock
                if current_stock < quantity:
                    return ResponseBuilder.error(
                        action="log_part_usage",
                        error_code="INSUFFICIENT_STOCK",
                        message=f"Insufficient stock: {current_stock} available, {quantity} requested"
                    )

                # Update part stock
                new_stock = current_stock - quantity
                update_result = self.db.table("pms_parts").update({
                    "quantity_on_hand": new_stock,
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }).eq("id", part_id).eq("yacht_id", yacht_id).execute()

                # Create usage log entry
                usage_log_id = str(uuid.uuid4())
                usage_result = self.db.table("pms_part_usage").insert({
                    "id": usage_log_id,
                    "yacht_id": yacht_id,
                    "part_id": part_id,
                    "quantity": quantity,
                    "work_order_id": work_order_id,
                    "equipment_id": equipment_id,
                    "usage_reason": usage_reason,
                    "notes": notes,
                    "used_by": user_id,
                    "used_at": datetime.now(timezone.utc).isoformat()
                }).execute()

            # Get created usage log entry
            usage_log = self.db.table("pms_part_usage").select(
                "id, part_id, quantity, work_order_id, equipment_id, "
                "usage_reason, notes, used_at, used_by, "
                "part:part_id(name, part_number), "
                "user:used_by(full_name)"
            ).eq("part_id", part_id).eq("yacht_id", yacht_id).order(
                "used_at", desc=True
            ).limit(1).maybe_single().execute()

            if not usage_log.data:
                logger.error(f"Failed to retrieve usage log after creation")
                usage_log_data = {}
            else:
                usage_log_data = usage_log.data

            # Get new stock level
            part_result = self.db.table("pms_parts").select(
                "quantity_on_hand, minimum_quantity"
            ).eq("id", part_id).eq("yacht_id", yacht_id).maybe_single().execute()

            new_stock_level = part_result.data.get("quantity_on_hand", 0) if part_result.data else 0
            minimum_quantity = part_result.data.get("minimum_quantity", 0) if part_result.data else 0

            # Check stock warning
            stock_warning = new_stock_level <= minimum_quantity or new_stock_level == 0

            # Get part and user names
            part_name = "Unknown"
            user_name = "Unknown"
            if usage_log_data.get("part"):
                part_name = usage_log_data["part"].get("name", "Unknown")
            if usage_log_data.get("user"):
                user_name = usage_log_data["user"].get("full_name", "Unknown")

            # Create audit log entry
            audit_log_id = str(uuid.uuid4())
            try:
                self.db.table("pms_audit_log").insert({
                    "id": audit_log_id,
                    "yacht_id": yacht_id,
                    "action": "log_part_usage",
                    "entity_type": "part_usage",
                    "entity_id": usage_log_data.get("id", ""),
                    "user_id": user_id,
                    "signature": {
                        "user_id": user_id,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    },
                    "old_values": None,
                    "new_values": {
                        "part_id": part_id,
                        "quantity": quantity,
                        "usage_reason": usage_reason,
                        "new_stock_level": new_stock_level
                    },
                    "created_at": datetime.now(timezone.utc).isoformat()
                }).execute()
            except Exception as e:
                logger.warning(f"Failed to create audit log: {e}")

            # Build response
            return ResponseBuilder.success(
                action="log_part_usage",
                result={
                    "usage_log": {
                        "id": usage_log_data.get("id", ""),
                        "part_id": part_id,
                        "part_name": part_name,
                        "quantity": quantity,
                        "work_order_id": work_order_id,
                        "equipment_id": equipment_id,
                        "usage_reason": usage_reason,
                        "notes": notes,
                        "used_at": usage_log_data.get("used_at", datetime.now(timezone.utc).isoformat()),
                        "used_by": user_id,
                        "used_by_name": user_name
                    },
                    "new_stock_level": new_stock_level,
                    "stock_warning": stock_warning,
                    "audit_log_id": audit_log_id
                },
                message="Part usage logged"
            )

        except Exception as e:
            logger.exception(f"Error executing log_part_usage for part {part_id}")
            return ResponseBuilder.error(
                action="log_part_usage",
                error_code="INTERNAL_ERROR",
                message=f"Failed to log part usage: {str(e)}"
            )


__all__ = ["InventoryHandlers"]
