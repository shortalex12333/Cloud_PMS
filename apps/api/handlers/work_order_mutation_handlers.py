"""
Work Order Mutation Handlers
=============================

MUTATE actions for work orders:
- create_work_order_from_fault (P0 Action #2)
- add_note_to_work_order (P0 Action #3)
- add_part_to_work_order (P0 Action #4)
- mark_work_order_complete (P0 Action #5)

Each MUTATE action has 3 endpoints:
1. GET /prefill - Pre-filled form data
2. POST /preview - Preview changes before commit
3. POST /execute - Execute with signature

Based on specs: /action_specifications/cluster_02_DO_MAINTENANCE/
"""

from datetime import datetime, timezone, timedelta
from typing import Dict, Optional, List
import logging

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from actions.action_response_schema import ResponseBuilder

logger = logging.getLogger(__name__)


class WorkOrderMutationHandlers:
    """
    MUTATE handlers for work order actions.

    Implements P0 actions:
    - create_work_order_from_fault
    - add_note_to_work_order
    - add_part_to_work_order
    - mark_work_order_complete
    """

    def __init__(self, supabase_client):
        self.db = supabase_client

    # =========================================================================
    # P0 ACTION #2: create_work_order_from_fault
    # =========================================================================

    async def create_work_order_from_fault_prefill(
        self,
        fault_id: str,
        yacht_id: str,
        user_id: str
    ) -> Dict:
        """
        GET /v1/actions/create_work_order_from_fault/prefill

        Pre-fill work order form from fault data.

        Logic (from spec):
        - title = f"{location} - {equipment_name} - {fault_code}"
        - equipment = fault.equipment
        - location = fault.location
        - description = fault.description + f"\\n\\nOccurrences: {count} in last 30 days"
        - priority = fault.severity if exists else "normal"

        Also checks for duplicate WO.
        """
        try:
            # Get fault details
            fault_result = self.db.table("pms_faults").select(
                "id, fault_code, title, description, severity, equipment_id, "
                "equipment:equipment_id(id, name, location), detected_at"
            ).eq("id", fault_id).eq("yacht_id", yacht_id).maybe_single().execute()

            if not fault_result.data:
                return {
                    "status": "error",
                    "error_code": "FAULT_NOT_FOUND",
                    "message": f"Fault not found: {fault_id}"
                }

            fault = fault_result.data
            equipment = fault.get("equipment") or {}

            # Get fault occurrence count (last 30 days)
            occurrence_count = 0
            if fault.get("fault_code"):
                count_result = self.db.table("pms_faults").select(
                    "id", count="exact"
                ).eq("yacht_id", yacht_id).eq(
                    "fault_code", fault["fault_code"]
                ).gte(
                    "detected_at",
                    (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
                ).execute()
                occurrence_count = count_result.count or 0

            # Build pre-fill data
            equipment_name = equipment.get("name", "Unknown Equipment")
            location = equipment.get("location", "Unknown Location")
            fault_code = fault.get("fault_code", "")

            # Title format: "{location} - {equipment_name} - {fault_code}"
            title_parts = []
            if location:
                title_parts.append(location)
            if equipment_name:
                title_parts.append(equipment_name)
            if fault_code:
                title_parts.append(fault_code)
            title = " - ".join(title_parts) if title_parts else fault.get("title", "Work Order")

            # Description with occurrence count
            description = fault.get("description", "")
            if occurrence_count > 1:
                description += f"\n\nOccurrences: {occurrence_count} in last 30 days"

            # Priority from severity mapping (DB enum: routine, urgent, emergency)
            severity_to_priority = {
                "critical": "emergency",
                "high": "urgent",
                "medium": "routine",
                "low": "routine"
            }
            priority = severity_to_priority.get(fault.get("severity"), "routine")

            prefill_data = {
                "title": title,
                "equipment_id": fault.get("equipment_id"),
                "equipment_name": equipment_name,
                "location": location,
                "description": description,
                "priority": priority,
                "fault_id": fault_id,
                "fault_code": fault_code
            }

            # Duplicate check: Look for existing WO for this fault
            duplicate_check = await self._check_duplicate_work_order(fault_id, yacht_id)

            return {
                "status": "success",
                "prefill_data": prefill_data,
                "duplicate_check": duplicate_check
            }

        except Exception as e:
            logger.error(f"create_work_order_from_fault_prefill failed: {e}", exc_info=True)
            return {
                "status": "error",
                "error_code": "INTERNAL_ERROR",
                "message": str(e)
            }

    async def create_work_order_from_fault_preview(
        self,
        fault_id: str,
        title: str,
        equipment_id: str,
        location: str,
        description: str,
        priority: str,
        yacht_id: str,
        user_id: str
    ) -> Dict:
        """
        POST /v1/actions/create_work_order_from_fault/preview

        Preview work order before creation.
        Shows all side effects.
        """
        try:
            # Get fault info for preview
            fault_result = self.db.table("pms_faults").select(
                "id, fault_code, title"
            ).eq("id", fault_id).maybe_single().execute()

            if not fault_result.data:
                return {
                    "status": "error",
                    "error_code": "FAULT_NOT_FOUND",
                    "message": f"Fault not found: {fault_id}"
                }

            fault = fault_result.data

            # Get equipment name
            equipment_name = "Unknown Equipment"
            if equipment_id:
                eq_result = self.db.table("pms_equipment").select(
                    "name, model"
                ).eq("id", equipment_id).maybe_single().execute()
                if eq_result.data:
                    eq = eq_result.data
                    equipment_name = f"{eq.get('name')} ({eq.get('model')})" if eq.get('model') else eq.get('name')

            # Build preview
            preview = {
                "action": "create_work_order_from_fault",
                "summary": "You are about to create:",
                "entity_type": "work_order",
                "changes": {
                    "title": title,
                    "equipment": equipment_name,
                    "location": location,
                    "priority": priority.capitalize(),
                    "status": "Candidate",
                    "linked_to": f"Fault {fault.get('fault_code') or fault['id'][:8]}"
                },
                "side_effects": [
                    "Work order will be created with status CANDIDATE",
                    f"Work order will be linked to fault {fault.get('fault_code') or fault['id'][:8]}",
                    "Audit log entry will be created",
                    "Fault status will NOT change (remains active)"
                ],
                "requires_signature": True,
                "warning": None
            }

            return {
                "status": "success",
                "preview": preview
            }

        except Exception as e:
            logger.error(f"create_work_order_from_fault_preview failed: {e}", exc_info=True)
            return {
                "status": "error",
                "error_code": "INTERNAL_ERROR",
                "message": str(e)
            }

    async def create_work_order_from_fault_execute(
        self,
        fault_id: str,
        title: str,
        equipment_id: str,
        location: str,
        description: str,
        priority: str,
        signature: Dict,
        yacht_id: str,
        user_id: str,
        override_duplicate: bool = False
    ) -> Dict:
        """
        POST /v1/actions/execute (action=create_work_order_from_fault)

        Execute work order creation with signature.

        Validates:
        - Fault exists
        - Equipment exists
        - Signature matches user
        - No duplicate (unless override_duplicate=True)

        Creates:
        - Work order record (status=CANDIDATE)
        - Audit log entry

        Does NOT:
        - Change fault status
        - Auto-assign work order
        - Create notes or parts
        """
        try:
            # Validate signature
            if not signature or signature.get("user_id") != user_id:
                return {
                    "status": "error",
                    "error_code": "INVALID_SIGNATURE",
                    "message": "Signature does not match user"
                }

            # Check duplicate (unless overridden)
            if not override_duplicate:
                duplicate_check = await self._check_duplicate_work_order(fault_id, yacht_id)
                if duplicate_check["has_duplicate"]:
                    return {
                        "status": "error",
                        "error_code": "DUPLICATE_WO_EXISTS",
                        "message": "Work order already exists for this fault",
                        "details": duplicate_check["existing_wo"]
                    }

            # Validate fault exists
            fault_result = self.db.table("pms_faults").select("id").eq(
                "id", fault_id
            ).eq("yacht_id", yacht_id).maybe_single().execute()

            if not fault_result.data:
                return {
                    "status": "error",
                    "error_code": "FAULT_NOT_FOUND",
                    "message": f"Fault not found: {fault_id}"
                }

            # Validate equipment exists (if provided)
            if equipment_id:
                eq_result = self.db.table("pms_equipment").select("id").eq(
                    "id", equipment_id
                ).eq("yacht_id", yacht_id).maybe_single().execute()

                if not eq_result.data:
                    return {
                        "status": "error",
                        "error_code": "EQUIPMENT_NOT_FOUND",
                        "message": f"Equipment not found: {equipment_id}"
                    }

            # Generate work order number
            wo_number = await self._generate_wo_number(yacht_id)

            # Create work order (using actual schema columns)
            now = datetime.now(timezone.utc).isoformat()
            wo_data = {
                "yacht_id": yacht_id,
                "wo_number": wo_number,  # Column is wo_number, not number
                "title": title,
                "description": description,
                "equipment_id": equipment_id,
                "fault_id": fault_id,
                # "location" column doesn't exist - stored in equipment table
                "priority": priority,
                "status": "planned",
                "created_by": user_id,
                "created_at": now,
                "updated_at": now
            }

            wo_result = self.db.table("pms_work_orders").insert(wo_data).execute()

            if not wo_result.data:
                return {
                    "status": "error",
                    "error_code": "INTERNAL_ERROR",
                    "message": "Failed to create work order"
                }

            work_order = wo_result.data[0]

            # Create audit log entry
            audit_log_id = await self._create_audit_log(
                yacht_id=yacht_id,
                action="create_work_order_from_fault",
                entity_type="work_order",
                entity_id=work_order["id"],
                user_id=user_id,
                new_values=work_order,
                signature=signature
            )

            # Build response (use wo_number column)
            result = {
                "work_order": {
                    "id": work_order["id"],
                    "number": work_order.get("wo_number", wo_number),  # Use wo_number column
                    "title": work_order["title"],
                    "equipment_id": work_order.get("equipment_id"),
                    "description": work_order.get("description"),
                    "priority": work_order["priority"],
                    "status": work_order["status"],
                    "fault_id": work_order.get("fault_id"),
                    "created_at": work_order["created_at"],
                    "created_by": work_order["created_by"]
                },
                "audit_log_id": audit_log_id,
                "next_actions": [
                    "add_note_to_work_order",
                    "add_part_to_work_order",
                    "view_work_order"
                ]
            }

            return {
                "status": "success",
                "action": "create_work_order_from_fault",
                "result": result,
                "message": f"✓ {wo_number} created"
            }

        except Exception as e:
            logger.error(f"create_work_order_from_fault_execute failed: {e}", exc_info=True)
            return {
                "status": "error",
                "error_code": "INTERNAL_ERROR",
                "message": str(e)
            }

    # =========================================================================
    # P0 ACTION #3: add_note_to_work_order
    # =========================================================================

    async def add_note_to_work_order_prefill(
        self,
        work_order_id: str,
        yacht_id: str
    ) -> Dict:
        """GET /v1/actions/add_note_to_work_order/prefill"""
        try:
            # Get work order info
            wo_result = self.db.table("pms_work_orders").select(
                "id, wo_number, equipment_id, status"
            ).eq("id", work_order_id).eq("yacht_id", yacht_id).limit(1).execute()

            if not wo_result.data or len(wo_result.data) == 0:
                return {
                    "status": "error",
                    "error_code": "WO_NOT_FOUND",
                    "message": f"Work order not found: {work_order_id}"
                }

            wo = wo_result.data[0]

            # Get equipment name separately
            equipment_name = "Unknown Equipment"
            if wo.get("equipment_id"):
                eq_result = self.db.table("pms_equipment").select("name").eq("id", wo["equipment_id"]).limit(1).execute()
                if eq_result.data and len(eq_result.data) > 0:
                    equipment_name = eq_result.data[0].get("name", "Unknown Equipment")
            wo["equipment"] = {"name": equipment_name}
            equipment_name = wo.get("equipment", {}).get("name", "Unknown Equipment")

            return {
                "status": "success",
                "prefill_data": {
                    "work_order_id": work_order_id,
                    "work_order_number": wo.get("wo_number", "N/A"),
                    "equipment_name": equipment_name,
                    "current_status": wo["status"]
                }
            }

        except Exception as e:
            logger.error(f"add_note_to_work_order_prefill failed: {e}", exc_info=True)
            return {
                "status": "error",
                "error_code": "INTERNAL_ERROR",
                "message": str(e)
            }

    async def add_note_to_work_order_execute(
        self,
        work_order_id: str,
        note_text: str,
        note_type: str,
        yacht_id: str,
        user_id: str
    ) -> Dict:
        """
        POST /v1/actions/execute (action=add_note_to_work_order)

        No signature required (low-risk WRITE-NOTE action).
        """
        try:
            # Validate work order exists and not closed
            wo_result = self.db.table("pms_work_orders").select(
                "id, wo_number, status"
            ).eq("id", work_order_id).eq("yacht_id", yacht_id).limit(1).execute()

            if not wo_result.data or len(wo_result.data) == 0:
                return {
                    "status": "error",
                    "error_code": "WO_NOT_FOUND",
                    "message": f"Work order not found: {work_order_id}"
                }

            wo = wo_result.data[0]

            if wo["status"] in ("closed", "cancelled"):
                return {
                    "status": "error",
                    "error_code": "WO_CLOSED",
                    "message": "Cannot add note to closed or cancelled work order"
                }

            # Create note
            note_data = {
                "work_order_id": work_order_id,
                "note_text": note_text,
                "note_type": note_type,
                "created_by": user_id,
                "created_at": datetime.now(timezone.utc).isoformat()
            }

            note_result = self.db.table("pms_work_order_notes").insert(note_data).execute()

            if not note_result.data:
                return {
                    "status": "error",
                    "error_code": "INTERNAL_ERROR",
                    "message": "Failed to create note"
                }

            note = note_result.data[0]

            # Get user name
            user_result = self.db.table("auth_users_profiles").select(
                "name"
            ).eq("id", user_id).limit(1).execute()
            user_name = user_result.data[0].get("name") if user_result.data and len(user_result.data) > 0 else "Unknown User"

            result = {
                "note": {
                    "id": note["id"],
                    "work_order_id": note["work_order_id"],
                    "note_text": note["note_text"],
                    "note_type": note["note_type"],
                    "created_at": note["created_at"],
                    "created_by": note["created_by"],
                    "created_by_name": user_name
                }
            }

            return {
                "status": "success",
                "action": "add_note_to_work_order",
                "result": result,
                "message": f"Note added to {wo['wo_number']}"
            }

        except Exception as e:
            logger.error(f"add_note_to_work_order_execute failed: {e}", exc_info=True)
            return {
                "status": "error",
                "error_code": "INTERNAL_ERROR",
                "message": str(e)
            }

    # =========================================================================
    # P0 ACTION #4: add_part_to_work_order
    # =========================================================================

    async def add_part_to_work_order_prefill(
        self,
        work_order_id: str,
        part_id: str,
        yacht_id: str
    ) -> Dict:
        """
        GET /v1/actions/add_part_to_work_order/prefill?work_order_id={uuid}&part_id={uuid}

        Pre-fill form with part details and stock status.
        """
        try:
            # Get work order details
            wo_result = self.db.table("pms_work_orders").select(
                "id, wo_number, status"
            ).eq("id", work_order_id).eq("yacht_id", yacht_id).maybe_single().execute()

            if not wo_result.data:
                return {
                    "status": "error",
                    "error_code": "WO_NOT_FOUND",
                    "message": f"Work order not found: {work_order_id}"
                }

            wo = wo_result.data

            if wo["status"] in ("closed", "cancelled"):
                return {
                    "status": "error",
                    "error_code": "WO_CLOSED",
                    "message": "Cannot add parts to closed or cancelled work order"
                }

            # Get part details
            part_result = self.db.table("pms_parts").select(
                "id, name, part_number, unit, quantity_on_hand, minimum_quantity, location"
            ).eq("id", part_id).eq("yacht_id", yacht_id).maybe_single().execute()

            if not part_result.data:
                return {
                    "status": "error",
                    "error_code": "PART_NOT_FOUND",
                    "message": f"Part not found: {part_id}"
                }

            part = part_result.data

            # Determine stock status
            stock_available = part.get("quantity_on_hand", 0)
            minimum_qty = part.get("minimum_quantity", 0)

            if stock_available <= 0:
                stock_status = "OUT_OF_STOCK"
            elif stock_available <= minimum_qty:
                stock_status = "LOW_STOCK"
            else:
                stock_status = "IN_STOCK"

            prefill_data = {
                "work_order_id": work_order_id,
                "work_order_number": wo.get("wo_number", "N/A"),
                "part": {
                    "id": part["id"],
                    "name": part["name"],
                    "part_number": part.get("part_number", "N/A"),
                    "unit": part.get("unit", "each"),
                    "stock_available": stock_available,
                    "stock_status": stock_status,
                    "location": part.get("location", "Unknown")
                },
                "suggested_quantity": 1
            }

            return {
                "status": "success",
                "prefill_data": prefill_data
            }

        except Exception as e:
            logger.error(f"add_part_to_work_order_prefill failed: {e}", exc_info=True)
            return {
                "status": "error",
                "error_code": "INTERNAL_ERROR",
                "message": str(e)
            }

    async def add_part_to_work_order_preview(
        self,
        work_order_id: str,
        part_id: str,
        quantity: int,
        notes: Optional[str],
        yacht_id: str,
        user_id: str
    ) -> Dict:
        """
        POST /v1/actions/add_part_to_work_order/preview

        Preview adding part to work order (does NOT deduct inventory).
        """
        try:
            # Get work order
            wo_result = self.db.table("pms_work_orders").select(
                "id, wo_number, status"
            ).eq("id", work_order_id).eq("yacht_id", yacht_id).maybe_single().execute()

            if not wo_result.data:
                return {
                    "status": "error",
                    "error_code": "WO_NOT_FOUND",
                    "message": "Work order not found"
                }

            wo = wo_result.data

            # Get part
            part_result = self.db.table("pms_parts").select(
                "id, name, part_number, unit, quantity_on_hand, minimum_quantity"
            ).eq("id", part_id).eq("yacht_id", yacht_id).maybe_single().execute()

            if not part_result.data:
                return {
                    "status": "error",
                    "error_code": "PART_NOT_FOUND",
                    "message": "Part not found"
                }

            part = part_result.data
            stock_available = part.get("quantity_on_hand", 0)
            minimum_qty = part.get("minimum_quantity", 0)

            # Build preview
            preview = {
                "action": "add_part_to_work_order",
                "summary": "You are about to add part to work order:",
                "changes": {
                    "work_order": wo.get("wo_number", "N/A"),
                    "part": f"{part['name']} ({part.get('part_number', 'N/A')})",
                    "quantity": f"{quantity} {part.get('unit', 'each')}",
                    "notes": notes or "None"
                },
                "side_effects": [
                    "Part will be ADDED to work order parts list",
                    "Inventory will NOT be deducted (use 'mark_work_order_complete' or 'log_part_usage' to deduct)",
                    "Parts list on WO will be updated",
                    "Audit log entry will be created"
                ],
                "warnings": [],
                "requires_signature": False
            }

            # Add stock warnings
            if stock_available <= 0:
                preview["warnings"].append(
                    f"⚠️  OUT OF STOCK: 0 available. Part must be ordered."
                )
            elif stock_available < quantity:
                preview["warnings"].append(
                    f"⚠️  INSUFFICIENT STOCK: {stock_available} available, {quantity} needed. {quantity - stock_available} short."
                )
            elif stock_available <= minimum_qty:
                preview["warnings"].append(
                    f"ℹ️  LOW STOCK: {stock_available} available (minimum: {minimum_qty}). Consider reordering."
                )
            else:
                preview["warnings"].append(
                    f"ℹ️  Current stock: {stock_available} available. Sufficient for this work order."
                )

            return {
                "status": "success",
                "preview": preview
            }

        except Exception as e:
            logger.error(f"add_part_to_work_order_preview failed: {e}", exc_info=True)
            return {
                "status": "error",
                "error_code": "INTERNAL_ERROR",
                "message": str(e)
            }

    async def add_part_to_work_order_execute(
        self,
        work_order_id: str,
        part_id: str,
        quantity: int,
        notes: Optional[str],
        yacht_id: str,
        user_id: str
    ) -> Dict:
        """
        POST /v1/actions/execute (action=add_part_to_work_order)

        Add part to work order shopping list (does NOT deduct inventory).
        No signature required (low-risk action).
        """
        try:
            # Validate work order
            wo_result = self.db.table("pms_work_orders").select(
                "id, wo_number, status"
            ).eq("id", work_order_id).eq("yacht_id", yacht_id).limit(1).execute()

            if not wo_result.data or len(wo_result.data) == 0:
                return {
                    "status": "error",
                    "error_code": "WO_NOT_FOUND",
                    "message": f"Work order not found: {work_order_id}"
                }

            wo = wo_result.data[0]

            if wo["status"] in ("closed", "cancelled"):
                return {
                    "status": "error",
                    "error_code": "WO_CLOSED",
                    "message": "Cannot add parts to closed or cancelled work order"
                }

            # Validate part
            part_result = self.db.table("pms_parts").select(
                "id, name, part_number, quantity_on_hand, minimum_quantity"
            ).eq("id", part_id).eq("yacht_id", yacht_id).limit(1).execute()

            if not part_result.data or len(part_result.data) == 0:
                return {
                    "status": "error",
                    "error_code": "PART_NOT_FOUND",
                    "message": f"Part not found: {part_id}"
                }

            part = part_result.data[0]

            # Validate quantity
            if quantity <= 0:
                return {
                    "status": "error",
                    "error_code": "INVALID_QUANTITY",
                    "message": "Quantity must be positive"
                }

            # Check if part already added to this WO
            existing_result = self.db.table("pms_work_order_parts").select(
                "id, quantity"
            ).eq("work_order_id", work_order_id).eq("part_id", part_id).limit(1).execute()

            if existing_result and existing_result.data and len(existing_result.data) > 0:
                # Update quantity instead of creating duplicate
                existing_record = existing_result.data[0]
                new_quantity = existing_record["quantity"] + quantity
                update_result = self.db.table("pms_work_order_parts").update({
                    "quantity": new_quantity,
                    "notes": notes
                }).eq("id", existing_record["id"]).execute()

                wo_part = update_result.data[0] if update_result.data else existing_record
            else:
                # Create new work_order_part entry
                wo_part_data = {
                    "work_order_id": work_order_id,
                    "part_id": part_id,
                    "quantity": quantity,
                    "notes": notes,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }

                wo_part_result = self.db.table("pms_work_order_parts").insert(wo_part_data).execute()

                if not wo_part_result.data:
                    return {
                        "status": "error",
                        "error_code": "INTERNAL_ERROR",
                        "message": "Failed to add part to work order"
                    }

                wo_part = wo_part_result.data[0]

            # Check stock warning
            stock_available = part.get("quantity_on_hand", 0)
            minimum_qty = part.get("minimum_quantity", 0)
            stock_warning = (stock_available <= minimum_qty) or (stock_available < quantity)

            # Create audit log entry
            await self._create_audit_log(
                yacht_id=yacht_id,
                action="add_part_to_work_order",
                entity_type="work_order_part",
                entity_id=wo_part["id"],
                user_id=user_id,
                new_values={
                    "work_order_id": work_order_id,
                    "work_order_number": wo.get("wo_number", "N/A"),
                    "part_id": part_id,
                    "part_name": part["name"],
                    "quantity": quantity,
                    "notes": notes
                },
                signature={"user_id": user_id, "timestamp": datetime.now(timezone.utc).isoformat()}
            )

            result = {
                "work_order_part": {
                    "id": wo_part["id"],
                    "work_order_id": wo_part["work_order_id"],
                    "part_id": wo_part["part_id"],
                    "part_name": part["name"],
                    "part_number": part.get("part_number", "N/A"),
                    "quantity": wo_part["quantity"],
                    "notes": wo_part.get("notes"),
                    "created_at": wo_part.get("created_at"),
                    "added_by": user_id
                },
                "stock_warning": stock_warning
            }

            return {
                "status": "success",
                "action": "add_part_to_work_order",
                "result": result,
                "message": f"Part added to {wo['wo_number']}"
            }

        except Exception as e:
            logger.error(f"add_part_to_work_order_execute failed: {e}", exc_info=True)
            return {
                "status": "error",
                "error_code": "INTERNAL_ERROR",
                "message": str(e)
            }

    # =========================================================================
    # P0 ACTION #5: mark_work_order_complete
    # =========================================================================

    async def mark_work_order_complete_prefill(
        self,
        work_order_id: str,
        yacht_id: str,
        user_id: str
    ) -> Dict:
        """
        GET /v1/actions/mark_work_order_complete/prefill?work_order_id={uuid}

        Pre-fill completion form with WO details, parts list, validation.
        """
        try:
            # Get work order details
            wo_result = self.db.table("pms_work_orders").select(
                "id, wo_number, title, status, equipment_id, created_at"
            ).eq("id", work_order_id).eq("yacht_id", yacht_id).limit(1).execute()

            if not wo_result.data or len(wo_result.data) == 0:
                return {
                    "status": "error",
                    "error_code": "WO_NOT_FOUND",
                    "message": f"Work order not found: {work_order_id}"
                }

            wo = wo_result.data[0]

            # Get equipment name separately
            equipment = {}
            if wo.get("equipment_id"):
                eq_result = self.db.table("pms_equipment").select("name").eq("id", wo["equipment_id"]).limit(1).execute()
                if eq_result.data and len(eq_result.data) > 0:
                    equipment = eq_result.data[0]

            # Get parts list for this WO
            parts_result = self.db.table("pms_work_order_parts").select(
                "id, part_id, quantity, notes"
            ).eq("work_order_id", work_order_id).execute()

            parts_list = []
            for wp in parts_result.data or []:
                # Get part details separately
                part = {}
                if wp.get("part_id"):
                    part_res = self.db.table("pms_parts").select("id, name, part_number, quantity_on_hand").eq("id", wp["part_id"]).limit(1).execute()
                    if part_res.data and len(part_res.data) > 0:
                        part = part_res.data[0]
                parts_list.append({
                    "id": wp["id"],
                    "part_id": wp["part_id"],
                    "part_name": part.get("name", "Unknown Part"),
                    "part_number": part.get("part_number", "N/A"),
                    "quantity": wp["quantity"],
                    "stock_available": part.get("quantity_on_hand", 0)
                })

            # Get notes count
            notes_result = self.db.table("pms_work_order_notes").select(
                "id", count="exact"
            ).eq("work_order_id", work_order_id).execute()
            notes_count = notes_result.count or 0

            # Calculate days open
            created_at = datetime.fromisoformat(wo["created_at"].replace('Z', '+00:00'))
            days_open = (datetime.now(timezone.utc) - created_at).days

            # Validation
            can_complete = True
            warnings = []
            blockers = []

            # Check status
            if wo["status"] in ("closed", "cancelled"):
                can_complete = False
                blockers.append(f"❌ Work order is already {wo['status']}")
            elif wo["status"] == "pending_parts":
                can_complete = False
                blockers.append("❌ Work order status is 'pending_parts' - cannot complete until parts arrive")
            elif wo["status"] == "planned":
                warnings.append("⚠️  Work order was never started (status: planned)")

            # Check for notes
            if notes_count == 0:
                warnings.append("⚠️  No notes added to work order")

            # Check for insufficient stock
            for part in parts_list:
                if part["stock_available"] < part["quantity"]:
                    warnings.append(
                        f"⚠️  Insufficient stock for {part['part_name']}: "
                        f"{part['stock_available']} available, {part['quantity']} needed"
                    )

            prefill_data = {
                "work_order_id": work_order_id,
                "work_order_number": wo.get("wo_number", "N/A"),
                "title": wo["title"],
                "equipment_name": equipment.get("name", "Unknown Equipment"),
                "current_status": wo["status"],
                "parts_list": parts_list,
                "notes_count": notes_count,
                "days_open": days_open,
                "completion_summary": ""  # User fills this in
            }

            validation = {
                "can_complete": can_complete,
                "warnings": warnings,
                "blockers": blockers
            }

            return {
                "status": "success",
                "prefill_data": prefill_data,
                "validation": validation
            }

        except Exception as e:
            logger.error(f"mark_work_order_complete_prefill failed: {e}", exc_info=True)
            return {
                "status": "error",
                "error_code": "INTERNAL_ERROR",
                "message": str(e)
            }

    async def mark_work_order_complete_preview(
        self,
        work_order_id: str,
        completion_notes: str,
        parts_used: List[Dict],
        signature: Dict,
        yacht_id: str,
        user_id: str
    ) -> Dict:
        """
        POST /v1/actions/mark_work_order_complete/preview

        Preview completion with inventory deduction simulation.
        """
        try:
            # Get work order
            wo_result = self.db.table("pms_work_orders").select(
                "id, wo_number, status"
            ).eq("id", work_order_id).eq("yacht_id", yacht_id).maybe_single().execute()

            if not wo_result.data:
                return {
                    "status": "error",
                    "error_code": "WO_NOT_FOUND",
                    "message": "Work order not found"
                }

            wo = wo_result.data

            # Get user name
            user_result = self.db.table("auth_users_profiles").select(
                "name"
            ).eq("id", user_id).limit(1).execute()
            user_name = user_result.data[0].get("name") if user_result.data and len(user_result.data) > 0 else "Unknown User"

            # Get user role
            role_result = self.db.table("auth_users_roles").select(
                "role"
            ).eq("user_id", user_id).eq("yacht_id", yacht_id).eq("is_active", True).maybe_single().execute()
            user_role = role_result.data.get("role") if role_result.data else "crew"

            # Build inventory changes preview
            inventory_changes = []
            parts_to_deduct = []

            for part_usage in (parts_used or []):
                part_id = part_usage["part_id"]
                quantity_used = part_usage["quantity_used"]

                # Get part details
                part_result = self.db.table("pms_parts").select(
                    "id, name, part_number, quantity_on_hand, minimum_quantity"
                ).eq("id", part_id).eq("yacht_id", yacht_id).maybe_single().execute()

                if part_result.data:
                    part = part_result.data
                    current_stock = part.get("quantity_on_hand", 0)
                    after_deduction = current_stock - quantity_used
                    minimum_qty = part.get("minimum_quantity", 0)

                    warning = None
                    if after_deduction < 0:
                        warning = f"⚠️  INSUFFICIENT STOCK: {current_stock} available, {quantity_used} needed"
                    elif after_deduction <= minimum_qty:
                        warning = f"⚠️  Will fall below minimum ({minimum_qty}) - consider reordering"

                    inventory_changes.append({
                        "part": f"{part['name']} ({part.get('part_number', 'N/A')})",
                        "current_stock": current_stock,
                        "after_deduction": after_deduction,
                        "warning": warning
                    })

                    parts_to_deduct.append(
                        f"{part['name']} ({part.get('part_number', 'N/A')}): {quantity_used} each"
                    )

            # Build preview
            preview = {
                "action": "mark_work_order_complete",
                "summary": "You are about to mark work order as complete:",
                "entity_type": "work_order",
                "changes": {
                    "work_order": wo.get("wo_number", "N/A"),
                    "status_change": f"{wo['status']} → completed",
                    "completion_notes": completion_notes[:100] + "..." if len(completion_notes) > 100 else completion_notes,
                    "parts_to_deduct": parts_to_deduct if parts_to_deduct else ["None"],
                    "completed_by": f"{user_name} ({user_role.replace('_', ' ').title()})",
                    "completed_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
                },
                "side_effects": [
                    "Work order status will change to COMPLETED",
                    f"{'Parts will be DEDUCTED from inventory' if parts_used else 'No parts to deduct'}",
                    f"{len(parts_used or [])} part usage log entries will be created" if parts_used else "No part usage entries",
                    "Completion timestamp and signature will be recorded",
                    "Audit log entry will be created",
                    "Work order will appear in 'Completed' list"
                ],
                "inventory_changes": inventory_changes,
                "requires_signature": True,
                "warnings": [ic["warning"] for ic in inventory_changes if ic["warning"]]
            }

            return {
                "status": "success",
                "preview": preview
            }

        except Exception as e:
            logger.error(f"mark_work_order_complete_preview failed: {e}", exc_info=True)
            return {
                "status": "error",
                "error_code": "INTERNAL_ERROR",
                "message": str(e)
            }

    async def mark_work_order_complete_execute(
        self,
        work_order_id: str,
        completion_notes: str,
        parts_used: List[Dict],
        signature: Dict,
        yacht_id: str,
        user_id: str
    ) -> Dict:
        """
        POST /v1/actions/execute (action=mark_work_order_complete)

        Mark work order as complete, deduct parts from inventory.
        Requires signature.
        """
        try:
            # Validate signature
            if not signature or signature.get("user_id") != user_id:
                return {
                    "status": "error",
                    "error_code": "INVALID_SIGNATURE",
                    "message": "Signature does not match user"
                }

            # Validate work order
            wo_result = self.db.table("pms_work_orders").select(
                "id, wo_number, status"
            ).eq("id", work_order_id).eq("yacht_id", yacht_id).maybe_single().execute()

            if not wo_result.data:
                return {
                    "status": "error",
                    "error_code": "WO_NOT_FOUND",
                    "message": f"Work order not found: {work_order_id}"
                }

            wo = wo_result.data

            if wo["status"] in ("completed", "closed", "cancelled"):
                return {
                    "status": "error",
                    "error_code": "WO_CLOSED",
                    "message": f"Work order is already {wo['status']}"
                }

            # Validate completion notes
            if not completion_notes or len(completion_notes.strip()) < 10:
                return {
                    "status": "error",
                    "error_code": "VALIDATION_ERROR",
                    "message": "Completion notes must be at least 10 characters"
                }

            # Deduct parts from inventory (using database function for atomicity)
            inventory_updates = []
            for part_usage in (parts_used or []):
                part_id = part_usage["part_id"]
                quantity_used = part_usage["quantity_used"]

                # Get part details first
                part_result = self.db.table("pms_parts").select(
                    "id, name, part_number, quantity_on_hand"
                ).eq("id", part_id).eq("yacht_id", yacht_id).maybe_single().execute()

                if not part_result.data:
                    return {
                        "status": "error",
                        "error_code": "PART_NOT_FOUND",
                        "message": f"Part not found: {part_id}"
                    }

                part = part_result.data

                # Call deduct_part_inventory function
                deduct_result = self.db.rpc(
                    'deduct_part_inventory',
                    {
                        'p_yacht_id': yacht_id,
                        'p_part_id': part_id,
                        'p_quantity': int(quantity_used),
                        'p_work_order_id': work_order_id,
                        'p_equipment_id': None,
                        'p_usage_reason': 'work_order',
                        'p_notes': f"Used for {wo['wo_number']}",
                        'p_used_by': user_id
                    }
                ).execute()

                success = deduct_result.data if deduct_result.data is not None else False

                if not success:
                    return {
                        "status": "error",
                        "error_code": "INSUFFICIENT_STOCK",
                        "message": f"Insufficient stock for {part['name']}"
                    }

                inventory_updates.append({
                    "part_id": part_id,
                    "part_name": part["name"],
                    "part_number": part.get("part_number", "N/A"),
                    "quantity_deducted": quantity_used,
                    "previous_stock": part["quantity_on_hand"],
                    "new_stock": part["quantity_on_hand"] - quantity_used
                })

            # Update work order to completed
            completed_at = datetime.now(timezone.utc).isoformat()
            update_data = {
                "status": "completed",
                "completed_at": completed_at,
                "completed_by": user_id,
                "completion_notes": completion_notes
            }

            wo_update_result = self.db.table("pms_work_orders").update(update_data).eq(
                "id", work_order_id
            ).eq("yacht_id", yacht_id).execute()

            if not wo_update_result.data:
                return {
                    "status": "error",
                    "error_code": "INTERNAL_ERROR",
                    "message": "Failed to update work order"
                }

            completed_wo = wo_update_result.data[0]

            # Create audit log entry
            await self._create_audit_log(
                yacht_id=yacht_id,
                action="mark_work_order_complete",
                entity_type="work_order",
                entity_id=work_order_id,
                user_id=user_id,
                old_values={"status": wo["status"]},
                new_values={
                    "status": "completed",
                    "completed_at": completed_at,
                    "completed_by": user_id,
                    "completion_notes": completion_notes,
                    "parts_deducted": inventory_updates
                },
                signature=signature
            )

            result = {
                "work_order": {
                    "id": completed_wo["id"],
                    "number": completed_wo.get("wo_number", "N/A"),
                    "status": completed_wo["status"],
                    "completed_at": completed_wo["completed_at"],
                    "completed_by": completed_wo["completed_by"],
                    "completion_notes": completed_wo["completion_notes"]
                },
                "inventory_updates": inventory_updates
            }

            return {
                "status": "success",
                "action": "mark_work_order_complete",
                "result": result,
                "message": f"✓ {wo['wo_number']} marked as complete"
            }

        except Exception as e:
            logger.error(f"mark_work_order_complete_execute failed: {e}", exc_info=True)
            return {
                "status": "error",
                "error_code": "INTERNAL_ERROR",
                "message": str(e)
            }

    # =========================================================================
    # HELPER METHODS
    # =========================================================================

    async def _check_duplicate_work_order(self, fault_id: str, yacht_id: str) -> Dict:
        """
        Check if work order already exists for this fault.

        Returns:
        {
            "has_duplicate": bool,
            "existing_wo": {...} or None
        }
        """
        try:
            # Simplified query - no join on assigned_to (foreign key may not exist)
            result = self.db.table("pms_work_orders").select(
                "id, wo_number, status, assigned_to, created_at"
            ).eq("yacht_id", yacht_id).eq("fault_id", fault_id).not_.in_(
                "status", ["cancelled"]
            ).order("created_at", desc=True).limit(1).execute()

            if result.data and len(result.data) > 0:
                wo = result.data[0]
                assigned_to = wo.get("assigned_to")  # Just the ID, no name lookup

                # Calculate days ago
                created_at = datetime.fromisoformat(wo["created_at"].replace("Z", "+00:00"))
                days_ago = (datetime.now(timezone.utc) - created_at).days

                return {
                    "has_duplicate": True,
                    "existing_wo": {
                        "id": wo["id"],
                        "number": wo.get("wo_number", "N/A"),
                        "status": wo["status"],
                        "assigned_to": assigned_to,
                        "created_at": wo["created_at"],
                        "days_ago": days_ago
                    }
                }
            else:
                return {
                    "has_duplicate": False,
                    "existing_wo": None
                }

        except Exception as e:
            logger.warning(f"Duplicate check failed: {e}")
            return {
                "has_duplicate": False,
                "existing_wo": None
            }

    async def _generate_wo_number(self, yacht_id: str) -> str:
        """
        Generate work order number: WO-YYYY-XXX

        Uses Supabase function if available, otherwise generates locally.
        """
        try:
            # Try to use database function
            result = self.db.rpc("generate_wo_number", {"p_yacht_id": yacht_id}).execute()
            if result.data:
                return result.data
        except Exception as e:
            logger.debug(f"Database function not available, generating locally: {e}")

        # Fallback: Generate locally
        year = datetime.now(timezone.utc).year

        # Get count of WOs this year
        count_result = self.db.table("pms_work_orders").select(
            "id", count="exact"
        ).eq("yacht_id", yacht_id).gte(
            "created_at", f"{year}-01-01"
        ).execute()

        count = (count_result.count or 0) + 1

        return f"WO-{year}-{count:03d}"

    async def _create_audit_log(
        self,
        yacht_id: str,
        action: str,
        entity_type: str,
        entity_id: str,
        user_id: str,
        old_values: Optional[Dict] = None,
        new_values: Optional[Dict] = None,
        signature: Optional[Dict] = None
    ) -> str:
        """Create audit log entry."""
        try:
            audit_data = {
                "yacht_id": yacht_id,
                "action": action,
                "entity_type": entity_type,
                "entity_id": entity_id,
                "user_id": user_id,
                "old_values": old_values,
                "new_values": new_values,
                "signature": signature,
                "created_at": datetime.now(timezone.utc).isoformat()
            }

            result = self.db.table("pms_audit_log").insert(audit_data).execute()

            if result.data:
                return result.data[0]["id"]
            else:
                logger.warning("Audit log creation returned no data")
                return None

        except Exception as e:
            logger.error(f"Failed to create audit log: {e}", exc_info=True)
            # Don't fail the action if audit log fails
            return None


def get_work_order_mutation_handlers(supabase_client) -> Dict[str, callable]:
    """Get work order mutation handler functions for registration."""
    handlers = WorkOrderMutationHandlers(supabase_client)

    return {
        # create_work_order_from_fault
        "create_work_order_from_fault_prefill": handlers.create_work_order_from_fault_prefill,
        "create_work_order_from_fault_preview": handlers.create_work_order_from_fault_preview,
        "create_work_order_from_fault": handlers.create_work_order_from_fault_execute,

        # add_note_to_work_order
        "add_note_to_work_order_prefill": handlers.add_note_to_work_order_prefill,
        "add_note_to_work_order": handlers.add_note_to_work_order_execute,

        # add_part_to_work_order
        "add_part_to_work_order_prefill": handlers.add_part_to_work_order_prefill,
        "add_part_to_work_order_preview": handlers.add_part_to_work_order_preview,
        "add_part_to_work_order": handlers.add_part_to_work_order_execute,

        # mark_work_order_complete
        "mark_work_order_complete_prefill": handlers.mark_work_order_complete_prefill,
        "mark_work_order_complete_preview": handlers.mark_work_order_complete_preview,
        "mark_work_order_complete": handlers.mark_work_order_complete_execute,
    }
