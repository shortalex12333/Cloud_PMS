"""
Handover Handlers
=================

P0 Actions for shift handover:
- add_to_handover (P0 Action #8) - MUTATE
- edit_handover_item - UPDATE
- export_handover - QUERY
- regenerate_handover_summary - QUERY

Based on specs: /P0_ACTION_CONTRACTS.md - Cluster 05: HANDOVER_COMMUNICATION

Schema: Consolidated handover tables (2026-02-05)
- handover_items: standalone draft notes (no parent container)
- handover_exports: exported documents with signoff tracking
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import hashlib
import json
import logging
import uuid

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from schemas.action_response_schema import ResponseBuilder
from handlers.ledger_utils import build_ledger_event
from action_router.entity_actions import get_available_actions
from lib.entity_helpers import _sign_url, _nav

logger = logging.getLogger(__name__)


class HandoverHandlers:
    """
    Handlers for shift handover actions.

    Implements P0 actions:
    - add_to_handover (MUTATE)
    """

    def __init__(self, supabase_client):
        self.db = supabase_client

    # =========================================================================
    # P0 ACTION #8: add_to_handover
    # =========================================================================

    async def add_to_handover_prefill(
        self,
        entity_type: str,
        entity_id: str,
        yacht_id: str,
        user_id: str
    ) -> Dict:
        """
        GET /v1/actions/add_to_handover/prefill

        Pre-fill handover entry from entity data.

        Entity type determines category:
        - fault → ongoing_fault
        - work_order → work_in_progress
        - document → important_info
        - equipment → equipment_status
        - part → general

        Summary auto-generated from entity data.
        """
        try:
            prefill_data = {
                "entity_type": entity_type,
                "entity_id": entity_id
            }

            # Fetch entity data based on type
            if entity_type == "fault":
                result = self.db.table("pms_faults").select(
                    "id, fault_code, title, description, severity, "
                    "equipment:equipment_id(name, location)"
                ).eq("id", entity_id).eq("yacht_id", yacht_id).maybe_single().execute()

                if not result.data:
                    return {
                        "status": "error",
                        "error_code": "ENTITY_NOT_FOUND",
                        "message": f"Fault not found: {entity_id}"
                    }

                entity = result.data
                equipment = entity.get("equipment", {})
                
                prefill_data.update({
                    "title": f"{equipment.get('name', 'Unknown Equipment')} - {entity.get('fault_code', 'Unknown Code')}",
                    "summary_text": (
                        f"{equipment.get('name', 'Unknown Equipment')} - {entity.get('title', '')}\n\n"
                        f"{entity.get('description', '')}"
                    ),
                    "category": "ongoing_fault",
                    "equipment_name": equipment.get("name", ""),
                    "location": equipment.get("location", ""),
                    "priority": "high" if entity.get("severity") == "critical" else "normal"
                })

            elif entity_type == "work_order":
                result = self.db.table("pms_work_orders").select(
                    "id, number, title, description, status, priority, "
                    "equipment:equipment_id(name, location)"
                ).eq("id", entity_id).eq("yacht_id", yacht_id).maybe_single().execute()

                if not result.data:
                    return {
                        "status": "error",
                        "error_code": "ENTITY_NOT_FOUND",
                        "message": f"Work order not found: {entity_id}"
                    }

                entity = result.data
                equipment = entity.get("equipment", {})
                
                prefill_data.update({
                    "title": f"WO-{entity.get('number', '')} - {entity.get('title', '')}",
                    "summary_text": (
                        f"Work Order {entity.get('number', '')}: {entity.get('title', '')}\n"
                        f"Equipment: {equipment.get('name', 'Unknown')}\n"
                        f"Status: {entity.get('status', 'Unknown')}\n\n"
                        f"{entity.get('description', '')}"
                    ),
                    "category": "work_in_progress",
                    "equipment_name": equipment.get("name", ""),
                    "location": equipment.get("location", ""),
                    "priority": entity.get("priority", "normal")
                })

            elif entity_type == "equipment":
                result = self.db.table("pms_equipment").select(
                    "id, name, model, manufacturer, location, status"
                ).eq("id", entity_id).eq("yacht_id", yacht_id).maybe_single().execute()

                if not result.data:
                    return {
                        "status": "error",
                        "error_code": "ENTITY_NOT_FOUND",
                        "message": f"Equipment not found: {entity_id}"
                    }

                entity = result.data
                
                prefill_data.update({
                    "title": entity.get("name", "Unknown Equipment"),
                    "summary_text": (
                        f"{entity.get('name', '')} ({entity.get('manufacturer', '')} {entity.get('model', '')})\n"
                        f"Location: {entity.get('location', '')}\n"
                        f"Status: {entity.get('status', '')}"
                    ),
                    "category": "equipment_status",
                    "equipment_name": entity.get("name", ""),
                    "location": entity.get("location", ""),
                    "priority": "normal"
                })

            elif entity_type == "document_chunk":
                result = self.db.table("document_chunks").select(
                    "id, text, document:document_id(title, manufacturer, model)"
                ).eq("id", entity_id).maybe_single().execute()

                if not result.data:
                    return {
                        "status": "error",
                        "error_code": "ENTITY_NOT_FOUND",
                        "message": f"Document chunk not found: {entity_id}"
                    }

                entity = result.data
                document = entity.get("document", {})
                
                prefill_data.update({
                    "title": f"Manual Reference: {document.get('title', 'Unknown Document')}",
                    "summary_text": (
                        f"Reference from {document.get('manufacturer', '')} {document.get('model', '')} manual:\n\n"
                        f"{entity.get('text', '')[:500]}..."
                    ),
                    "category": "important_info",
                    "equipment_name": f"{document.get('manufacturer', '')} {document.get('model', '')}",
                    "location": "",
                    "priority": "normal"
                })

            elif entity_type == "part":
                result = self.db.table("pms_parts").select(
                    "id, name, part_number, category, quantity_on_hand, minimum_quantity, location"
                ).eq("id", entity_id).eq("yacht_id", yacht_id).maybe_single().execute()

                if not result.data:
                    return {
                        "status": "error",
                        "error_code": "ENTITY_NOT_FOUND",
                        "message": f"Part not found: {entity_id}"
                    }

                entity = result.data
                stock_status = "low stock" if entity.get("quantity_on_hand", 0) <= entity.get("minimum_quantity", 0) else "in stock"
                
                prefill_data.update({
                    "title": f"{entity.get('name', '')} ({entity.get('part_number', '')})",
                    "summary_text": (
                        f"{entity.get('name', '')} ({entity.get('part_number', '')})\n"
                        f"Category: {entity.get('category', '')}\n"
                        f"Stock: {entity.get('quantity_on_hand', 0)} ({stock_status})\n"
                        f"Location: {entity.get('location', '')}"
                    ),
                    "category": "general",
                    "equipment_name": "",
                    "location": entity.get("location", ""),
                    "priority": "high" if stock_status == "low stock" else "normal"
                })

            elif entity_type == "receiving":
                result = self.db.table("pms_receiving").select(
                    "id, vendor_name, vendor_reference, status, total, currency, "
                    "po_id, purchase_order:po_id(order_number)"
                ).eq("id", entity_id).eq("yacht_id", yacht_id).maybe_single().execute()

                if not result.data:
                    return {
                        "status": "error",
                        "error_code": "ENTITY_NOT_FOUND",
                        "message": f"Receiving not found: {entity_id}"
                    }

                entity = result.data
                po = entity.get("purchase_order") or {}
                po_ref = po.get("order_number") or entity.get("vendor_reference") or "—"

                # Count line items + discrepancies
                items_r = self.db.table("pms_receiving_items").select(
                    "id", count="exact"
                ).eq("receiving_id", entity_id).eq("yacht_id", yacht_id).execute()
                line_count = items_r.count if hasattr(items_r, "count") and items_r.count is not None else len(items_r.data or [])

                disc_r = self.db.table("ledger_events").select(
                    "id", count="exact"
                ).eq("entity_id", entity_id).eq("entity_type", "receiving").eq("event_category", "discrepancy").execute()
                disc_count = disc_r.count if hasattr(disc_r, "count") and disc_r.count is not None else len(disc_r.data or [])

                prefill_data.update({
                    "title": (
                        f"Receiving — {entity.get('vendor_name', 'Unknown Vendor')} "
                        f"({po_ref})"
                    ),
                    "summary_text": (
                        f"Receiving from {entity.get('vendor_name', 'Unknown Vendor')}\n"
                        f"PO / Reference: {po_ref}\n"
                        f"Status: {entity.get('status', 'pending')}\n"
                        f"Lines: {line_count} | Discrepancies: {disc_count}\n"
                        f"Value: {entity.get('currency', '')} {entity.get('total') or '—'}"
                    ),
                    "category": "work_in_progress" if disc_count > 0 else "fyi",
                    "equipment_name": "",
                    "location": "",
                    "priority": "high" if disc_count > 0 else "normal",
                })

            else:
                return {
                    "status": "error",
                    "error_code": "INVALID_ENTITY_TYPE",
                    "message": f"Unsupported entity type for handover: {entity_type}"
                }

            return {
                "status": "success",
                "prefill_data": prefill_data
            }

        except Exception as e:
            logger.exception(f"Error prefilling add_to_handover for {entity_type} {entity_id}")
            return {
                "status": "error",
                "error_code": "INTERNAL_ERROR",
                "message": f"Failed to prefill: {str(e)}"
            }

    async def add_to_handover_execute(
        self,
        entity_type: str,
        entity_id: str,
        summary: str,
        category: str,
        yacht_id: str,
        user_id: str,
        priority: str = "normal",
        section: Optional[str] = None,
        is_critical: bool = False,
        requires_action: bool = False,
        action_summary: Optional[str] = None,
        entity_url: Optional[str] = None
    ) -> Dict:
        """
        POST /v1/actions/execute (action=add_to_handover)

        Add item to shift handover list.

        MUTATE action - execute only (no preview needed, low-risk).

        Creates entry in handover_items table (standalone, no parent container).

        Returns:
        - Handover item details
        - WHO added it
        - WHEN added
        """
        try:
            # Validate entity type
            # Gating matrix (add_to_handover_gating.py) controls which entity types
            # each role can use — this list is the full set supported by handover_items.
            valid_types = [
                "fault", "work_order", "equipment", "part", "document", "document_chunk",
                "certificate", "purchase_order", "warranty", "hours_of_rest",
                "shopping_list", "receiving", "location", "note",
            ]
            if entity_type not in valid_types:
                return ResponseBuilder.error(
                    action="add_to_handover",
                    error_code="INVALID_ENTITY_TYPE",
                    message=f"Invalid entity type: {entity_type}. Must be one of: {', '.join(valid_types)}"
                )

            # entity_id is optional for "note" type
            if entity_type != "note" and not entity_id:
                return ResponseBuilder.error(
                    action="add_to_handover",
                    error_code="VALIDATION_ERROR",
                    message=f"entity_id is required for entity_type: {entity_type}"
                )

            # Validate summary text
            if not summary or len(summary.strip()) < 3:
                return ResponseBuilder.error(
                    action="add_to_handover",
                    error_code="VALIDATION_ERROR",
                    message="Summary must be at least 3 characters"
                )

            if len(summary) > 2000:
                return ResponseBuilder.error(
                    action="add_to_handover",
                    error_code="VALIDATION_ERROR",
                    message="Summary must be less than 2000 characters"
                )

            # Normalise category — accept new UI values (critical/standard/low) and legacy values
            category_map = {
                "critical": "urgent",
                "standard": "fyi",
                "low": "fyi",
                "urgent": "urgent",
                "in_progress": "in_progress",
                "completed": "completed",
                "watch": "watch",
                "fyi": "fyi",
            }
            raw_category = category
            category = category_map.get(category, "fyi")
            # Derive is_critical from raw_category if not explicitly set
            if raw_category == "critical":
                is_critical = True

            # Check for duplicate entry (optional - allow override) - only if entity_id present
            if entity_id:
                existing = self.db.table("handover_items").select(
                    "id"
                ).eq("yacht_id", yacht_id).eq(
                    "entity_type", entity_type
                ).eq("entity_id", entity_id).is_("deleted_at", "null").execute()
                # Note: We allow duplicates for now - multiple shifts may reference same entity

            # Create handover item (standalone, no parent container)
            item_id = str(uuid.uuid4())
            priority_value = {"low": 0, "normal": 1, "high": 2, "critical": 3, "urgent": 3}.get(priority, 1)

            handover_item = {
                "id": item_id,
                "yacht_id": yacht_id,
                "entity_type": entity_type,
                "entity_id": entity_id,
                "summary": summary,
                "section": section,
                "category": category,
                "priority": priority_value,
                "is_critical": is_critical,
                "requires_action": requires_action,
                "action_summary": action_summary,
                "entity_url": entity_url,
                "added_by": user_id,
                "created_at": datetime.now(timezone.utc).isoformat()
            }

            insert_result = self.db.table("handover_items").insert(
                handover_item
            ).execute()

            if not insert_result.data:
                return ResponseBuilder.error(
                    action="add_to_handover",
                    error_code="INTERNAL_ERROR",
                    message="Failed to create handover item"
                )

            # Get user name
            user_result = self.db.table("auth_users_profiles").select(
                "name"
            ).eq("id", user_id).maybe_single().execute()
            user_name = user_result.data.get("name", "Unknown") if user_result.data else "Unknown"

            # Create audit log entry
            audit_log_id = str(uuid.uuid4())
            try:
                self.db.table("pms_audit_log").insert({
                    "id": audit_log_id,
                    "yacht_id": yacht_id,
                    "action": "add_to_handover",
                    "entity_type": "handover_item",
                    "entity_id": item_id,
                    "user_id": user_id,
                    "signature": {
                        "user_id": user_id,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    },
                    "old_values": None,
                    "new_values": {
                        "entity_type": entity_type,
                        "entity_id": entity_id,
                        "category": category,
                        "priority": priority,
                        "is_critical": is_critical
                    },
                    "created_at": datetime.now(timezone.utc).isoformat()
                }).execute()
            except Exception as e:
                logger.warning(f"Failed to create audit log: {e}")

            # If item is critical — notify HOD immediately
            if is_critical:
                try:
                    hod_rows = self.db.table("auth_users_roles").select("user_id, role, department") \
                        .eq("yacht_id", yacht_id) \
                        .in_("role", ["chief_engineer", "chief_officer", "captain"]) \
                        .eq("is_active", True).execute()
                    for hod in (hod_rows.data or []):
                        ledger_event = build_ledger_event(
                            yacht_id=yacht_id,
                            user_id=hod["user_id"],
                            event_type="escalation",
                            entity_type="handover_item",
                            entity_id=item_id,
                            action="critical_item_added",
                            user_role=hod["role"],
                            change_summary=f"Critical handover item added: {summary[:100]}",
                            actor_name=user_name,
                            metadata={"added_by": user_id, "item_id": item_id, "summary": summary[:200]}
                        )
                        self.db.table("ledger_events").insert(ledger_event).execute()
                except Exception as e:
                    logger.warning(f"Critical item HOD notification failed: {e}")

            # Data-continuity: for receiving entities, write a ledger row that marks
            # this handover as requiring follow-up, and immediately create a
            # pms_notifications entry for all HOD+ on the vessel.
            # The philosophy: never trust "I'll fill it in later". Force the loop.
            if entity_type == "receiving":
                try:
                    ledger_event = build_ledger_event(
                        yacht_id=yacht_id,
                        user_id=user_id,
                        event_type="update",
                        entity_type="receiving",
                        entity_id=entity_id,
                        action="added_to_handover",
                        event_category="handover",
                        change_summary=f"Receiving added to shift handover by {user_name}: {summary[:120]}",
                        metadata={
                            "handover_item_id": item_id,
                            "summary": summary[:300],
                            "requires_followup": True,
                        },
                        new_state={"in_handover": True, "requires_followup": True},
                    )
                    self.db.table("ledger_events").insert(ledger_event).execute()
                except Exception as e:
                    logger.warning(f"Receiving handover ledger write failed: {e}")

                try:
                    purser_band = self.db.table("auth_users_roles").select("user_id, role").eq(
                        "yacht_id", yacht_id
                    ).in_("role", [
                        "purser", "chief_engineer", "chief_officer",
                        "chief_steward", "captain", "manager",
                    ]).eq("is_active", True).execute()
                    now_iso = datetime.now(timezone.utc).isoformat()
                    notifs = []
                    for member in (purser_band.data or []):
                        if member["user_id"] == user_id:
                            continue  # don't notify yourself
                        notifs.append({
                            "id": str(uuid.uuid4()),
                            "yacht_id": yacht_id,
                            "user_id": member["user_id"],
                            "notification_type": "receiving_added_to_handover",
                            "title": "Receiving added to handover — follow-up required",
                            "body": (
                                f"{user_name} has added a receiving record to the shift handover. "
                                f"Please review and complete: {summary[:200]}"
                            ),
                            "priority": "high" if is_critical else "normal",
                            "entity_type": "receiving",
                            "entity_id": entity_id,
                            "triggered_by": user_id,
                            "idempotency_key": f"rcv_handover:{entity_id}:{item_id}:{member['user_id']}",
                            "is_read": False,
                            "created_at": now_iso,
                        })
                    if notifs:
                        self.db.table("pms_notifications").upsert(
                            notifs, on_conflict="yacht_id,user_id,idempotency_key"
                        ).execute()
                except Exception as e:
                    logger.warning(f"Receiving handover notification loop failed: {e}")

            # Build response
            return ResponseBuilder.success(
                action="add_to_handover",
                result={
                    "item_id": item_id,
                    "handover_item": {
                        "id": item_id,
                        "yacht_id": yacht_id,
                        "entity_type": entity_type,
                        "entity_id": entity_id,
                        "summary": summary,
                        "section": section,
                        "category": category,
                        "priority": priority,
                        "is_critical": is_critical,
                        "requires_action": requires_action,
                        "created_at": handover_item["created_at"],
                        "added_by": user_id,
                        "added_by_name": user_name
                    }
                },
                message="Added to handover"
            )

        except Exception as e:
            logger.exception(f"Error executing add_to_handover for {entity_type} {entity_id}")
            return ResponseBuilder.error(
                action="add_to_handover",
                error_code="INTERNAL_ERROR",
                message=f"Failed to add to handover: {str(e)}"
            )

    # =========================================================================
    # EDIT HANDOVER ITEM
    # =========================================================================

    async def edit_handover_item_execute(
        self,
        item_id: str,
        yacht_id: str,
        user_id: str,
        summary: Optional[str] = None,
        category: Optional[str] = None,
        is_critical: Optional[bool] = None,
        requires_action: Optional[bool] = None,
        action_summary: Optional[str] = None
    ) -> Dict:
        """
        POST /v1/actions/execute (action=edit_handover_section)

        Edit a handover item.

        Schema: Consolidated (2026-02-05) - items are standalone.
        """
        try:
            # Verify item exists and belongs to yacht
            existing = self.db.table("handover_items").select(
                "id, summary, category, is_critical"
            ).eq("id", item_id).eq("yacht_id", yacht_id).is_("deleted_at", "null").maybe_single().execute()

            if not existing.data:
                return ResponseBuilder.error(
                    action="edit_handover_section",
                    error_code="NOT_FOUND",
                    message=f"Handover item not found: {item_id}"
                )

            # Build update data
            update_data = {
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "updated_by": user_id
            }

            if summary is not None:
                update_data["summary"] = summary
            if category is not None:
                valid_categories = ["urgent", "in_progress", "completed", "watch", "fyi"]
                if category not in valid_categories:
                    return ResponseBuilder.error(
                        action="edit_handover_section",
                        error_code="VALIDATION_ERROR",
                        message=f"Invalid category: {category}"
                    )
                update_data["category"] = category
            if is_critical is not None:
                update_data["is_critical"] = is_critical
            if requires_action is not None:
                update_data["requires_action"] = requires_action
            if action_summary is not None:
                update_data["action_summary"] = action_summary

            # Update item
            result = self.db.table("handover_items").update(
                update_data
            ).eq("id", item_id).execute()

            if not result.data:
                return ResponseBuilder.error(
                    action="edit_handover_section",
                    error_code="INTERNAL_ERROR",
                    message="Failed to update handover item"
                )

            # Audit trail for item edit
            try:
                self.db.table("pms_audit_log").insert({
                    "id": str(uuid.uuid4()),
                    "yacht_id": yacht_id,
                    "action": "edit_handover_item",
                    "entity_type": "handover_item",
                    "entity_id": item_id,
                    "user_id": user_id,
                    "actor_id": user_id,
                    "signature": {
                        "user_id": user_id,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    },
                    "old_values": {
                        "summary": existing.data.get("summary"),
                        "category": existing.data.get("category"),
                        "is_critical": existing.data.get("is_critical")
                    },
                    "new_values": update_data,
                    "metadata": {"item_id": item_id}
                }).execute()
            except Exception as e:
                logger.warning(f"Audit log failed for edit_handover_item {item_id}: {e}")

            return ResponseBuilder.success(
                action="edit_handover_section",
                result={
                    "item_id": item_id,
                    "updated_fields": list(update_data.keys()),
                    "item": result.data[0] if result.data else None
                },
                message="Handover item updated"
            )

        except Exception as e:
            logger.exception(f"Error editing handover item {item_id}")
            return ResponseBuilder.error(
                action="edit_handover_section",
                error_code="INTERNAL_ERROR",
                message=f"Failed to edit handover item: {str(e)}"
            )

    # =========================================================================
    # EXPORT HANDOVER
    # =========================================================================

    async def export_handover_execute(
        self,
        yacht_id: str,
        user_id: str,
        department: Optional[str] = None,
        export_type: str = "pdf"
    ) -> Dict:
        """
        POST /v1/actions/execute (action=export_handover)

        Create an export record for handover items.

        Schema: Consolidated (2026-02-05) - exports to handover_exports table.
        """
        try:
            # Get items for this yacht
            query = self.db.table("handover_items").select(
                "id, summary, section, category, is_critical, requires_action"
            ).eq("yacht_id", yacht_id).is_("deleted_at", "null")

            if department:
                query = query.eq("section", department)

            items_result = query.execute()
            items = items_result.data or []

            # Create export record
            export_id = str(uuid.uuid4())
            export_record = {
                "id": export_id,
                "yacht_id": yacht_id,
                "export_type": export_type,
                "department": department,
                "exported_by_user_id": user_id,
                "export_status": "pending",
                "exported_at": datetime.now(timezone.utc).isoformat()
            }

            self.db.table("handover_exports").insert(export_record).execute()

            return ResponseBuilder.success(
                action="export_handover",
                result={
                    "export_id": export_id,
                    "department": department,
                    "export_type": export_type,
                    "item_count": len(items),
                    "export_url": f"https://handover-export.onrender.com/api/v1/export/{export_id}?format={export_type}"
                },
                message="Export created"
            )

        except Exception as e:
            logger.exception(f"Error creating handover export")
            return ResponseBuilder.error(
                action="export_handover",
                error_code="INTERNAL_ERROR",
                message=f"Failed to create export: {str(e)}"
            )

    # =========================================================================
    # REGENERATE HANDOVER SUMMARY
    # =========================================================================

    async def regenerate_handover_summary_execute(
        self,
        yacht_id: str,
        user_id: str,
        department: Optional[str] = None
    ) -> Dict:
        """
        POST /v1/actions/execute (action=regenerate_handover_summary)

        Generate summary from current handover items.

        Schema: Consolidated (2026-02-05) - no parent handover record.
        """
        try:
            # Get items for this yacht
            query = self.db.table("handover_items").select(
                "id, entity_type, summary, category, is_critical, requires_action"
            ).eq("yacht_id", yacht_id).is_("deleted_at", "null")

            if department:
                query = query.eq("section", department)

            items_result = query.execute()
            items = items_result.data or []

            # Generate summary
            fault_count = sum(1 for i in items if i.get("entity_type") == "fault")
            wo_count = sum(1 for i in items if i.get("entity_type") == "work_order")
            equipment_count = sum(1 for i in items if i.get("entity_type") == "equipment")
            critical_count = sum(1 for i in items if i.get("is_critical"))
            action_count = sum(1 for i in items if i.get("requires_action"))

            parts = []
            if critical_count > 0:
                parts.append(f"{critical_count} CRITICAL")
            if action_count > 0:
                parts.append(f"{action_count} requiring action")
            if fault_count > 0:
                parts.append(f"{fault_count} fault(s)")
            if wo_count > 0:
                parts.append(f"{wo_count} work order(s)")
            if equipment_count > 0:
                parts.append(f"{equipment_count} equipment item(s)")

            summary = f"Handover includes {', '.join(parts) if parts else 'no items'}."

            return ResponseBuilder.success(
                action="regenerate_handover_summary",
                result={
                    "summary": summary,
                    "item_count": len(items),
                    "department": department or "all",
                    "critical_count": critical_count,
                    "action_required_count": action_count
                },
                message="Summary generated"
            )

        except Exception as e:
            logger.exception(f"Error generating handover summary")
            return ResponseBuilder.error(
                action="regenerate_handover_summary",
                error_code="INTERNAL_ERROR",
                message=f"Failed to generate summary: {str(e)}"
            )

    # =========================================================================
    # READ: get_handover_items — GET /v1/actions/handover
    # =========================================================================

    async def get_handover_items(
        self,
        yacht_id: str,
        user_id: str,
        limit: int = 200,
        category: Optional[str] = None,
    ) -> Dict:
        query = self.db.table("handover_items").select("*") \
            .eq("yacht_id", yacht_id) \
            .eq("added_by", user_id) \
            .is_("deleted_at", None) \
            .neq("export_status", "exported") \
            .order("created_at", desc=True) \
            .limit(limit)
        if category:
            query = query.eq("category", category)
        result = query.execute()
        items = result.data or []
        return {"status": "success", "items": items, "count": len(items)}

    # =========================================================================
    # READ: get_handover_queue — GET /v1/actions/handover/queue
    # =========================================================================

    async def get_handover_queue(
        self,
        yacht_id: str,
        sections: Optional[set] = None,
    ) -> Dict:
        from datetime import datetime, timezone
        all_sections = {"faults", "work_orders", "parts", "orders", "queued"}
        requested = sections if sections else all_sections

        open_faults: list = []
        overdue_work_orders: list = []
        low_stock_parts: list = []
        pending_orders: list = []
        already_queued: list = []

        if "faults" in requested:
            try:
                r = self.db.table("pms_faults").select(
                    "id, title, severity, equipment_name, created_at"
                ).eq("yacht_id", yacht_id).neq("status", "resolved") \
                    .order("created_at", desc=True).limit(20).execute()
                open_faults = r.data or []
            except Exception as e:
                logger.warning(f"[handover/queue] faults query failed: {e}")

        if "work_orders" in requested:
            try:
                now_iso = datetime.now(timezone.utc).isoformat()
                r = self.db.table("pms_work_orders").select(
                    "id, title, priority, due_at, assigned_to"
                ).eq("yacht_id", yacht_id).not_.in_(
                    "status", ["completed", "cancelled", "closed"]
                ).lt("due_at", now_iso).order("due_at").limit(20).execute()
                overdue_work_orders = r.data or []
            except Exception as e:
                logger.warning(f"[handover/queue] work_orders query failed: {e}")

        if "parts" in requested:
            try:
                r = self.db.table("pms_parts").select(
                    "id, name, quantity_on_hand, minimum_quantity"
                ).eq("yacht_id", yacht_id).execute()
                low_stock_parts = [
                    {
                        "id": p["id"],
                        "name": p.get("name", ""),
                        "current_qty": p.get("quantity_on_hand", 0),
                        "reorder_threshold": p.get("minimum_quantity", 0),
                    }
                    for p in (r.data or [])
                    if (p.get("quantity_on_hand") or 0) <= (p.get("minimum_quantity") or 0)
                ][:20]
            except Exception as e:
                logger.warning(f"[handover/queue] parts query failed: {e}")

        if "orders" in requested:
            try:
                r = self.db.table("pms_purchase_orders").select(
                    "id, po_number, status, created_at"
                ).eq("yacht_id", yacht_id).in_(
                    "status", ["draft", "pending", "submitted", "pending_approval"]
                ).order("created_at", desc=True).limit(20).execute()
                pending_orders = [
                    {
                        "id": p["id"],
                        "title": p.get("po_number") or f"PO {p['id'][:8]}",
                        "status": p.get("status", ""),
                        "created_at": p.get("created_at", ""),
                    }
                    for p in (r.data or [])
                ]
            except Exception as e:
                logger.warning(f"[handover/queue] orders query failed: {e}")

        if "queued" in requested:
            try:
                r = self.db.table("handover_items").select(
                    "id, entity_type, entity_id, summary, priority"
                ).eq("yacht_id", yacht_id).eq("status", "pending") \
                    .order("priority", desc=True).limit(50).execute()
                already_queued = r.data or []
            except Exception as e:
                logger.warning(f"[handover/queue] handover_items query failed: {e}")

        return {
            "open_faults": open_faults,
            "overdue_work_orders": overdue_work_orders,
            "low_stock_parts": low_stock_parts,
            "pending_orders": pending_orders,
            "already_queued": already_queued,
            "counts": {
                "faults": len(open_faults),
                "work_orders": len(overdue_work_orders),
                "parts": len(low_stock_parts),
                "orders": len(pending_orders),
                "already_queued": len(already_queued),
            },
        }


__all__ = ["HandoverHandlers", "HandoverWorkflowHandlers", "HANDLERS"]


# ============================================================================
# HandoverWorkflowHandlers — dual-hash, dual-signature state machine
# Called directly by REST endpoints in p0_actions_routes.py (not action dispatch)
# ============================================================================

class HandoverWorkflowHandlers:
    """Handlers for handover workflow: finalize → export → sign → verify"""

    def __init__(self, supabase_client):
        self.db = supabase_client

    # ── Stage 1: Draft Review & Finalization ──────────────────────────────────

    async def validate_draft(
        self,
        yacht_id: str,
        user_id: str,
        section: Optional[str] = None,
        category: Optional[str] = None,
    ) -> Dict:
        query = self.db.table("handover_items").select("*").eq("yacht_id", yacht_id).is_("deleted_at", None)
        if section:
            query = query.eq("section", section)
        if category:
            query = query.eq("category", category)

        result = query.execute()
        items = result.data or []
        errors: List[Dict] = []
        warnings: List[Dict] = []

        for item in items:
            item_id = item["id"]
            summary = item.get("summary", "").strip()
            if not summary:
                errors.append({"item_id": item_id, "type": "empty_summary", "message": "Item has empty summary"})
            if item.get("is_critical") and not item.get("action_summary"):
                errors.append({"item_id": item_id, "type": "missing_action", "message": "Critical item missing action_summary"})
            if not item.get("category"):
                warnings.append({"item_id": item_id, "type": "missing_category", "message": "Item has no category"})

        return {
            "valid": len(errors) == 0,
            "total_items": len(items),
            "errors": errors,
            "warnings": warnings,
            "blocking_count": len(errors),
            "warning_count": len(warnings),
        }

    async def finalize_draft(
        self,
        yacht_id: str,
        user_id: str,
        section: Optional[str] = None,
        category: Optional[str] = None,
    ) -> Dict:
        validation = await self.validate_draft(yacht_id, user_id, section, category)
        if not validation["valid"]:
            return {
                "status": "error",
                "error_code": "VALIDATION_FAILED",
                "message": f"Draft has {validation['blocking_count']} blocking errors",
                "validation": validation,
            }

        query = self.db.table("handover_items").select("*").eq("yacht_id", yacht_id).is_("deleted_at", None)
        if section:
            query = query.eq("section", section)
        if category:
            query = query.eq("category", category)

        result = query.order("category", desc=False).order("created_at", desc=False).execute()
        items = result.data or []

        if not items:
            return {"status": "error", "error_code": "NO_ITEMS", "message": "No items to finalize"}

        normalized = self._normalize_draft_content(items)
        content_json = json.dumps(normalized, sort_keys=True, separators=(',', ':'))
        content_hash = hashlib.sha256(content_json.encode('utf-8')).hexdigest()

        now = datetime.now(timezone.utc).isoformat()
        item_ids = [item["id"] for item in items]
        self.db.table("handover_items").update({
            "is_finalized": True,
            "content_hash": content_hash,
            "finalized_at": now,
            "finalized_by": user_id,
            "version": 1,
        }).in_("id", item_ids).execute()

        logger.info(f"Draft finalized: yacht={yacht_id}, items={len(items)}, hash={content_hash[:16]}")
        return {
            "status": "success",
            "content_hash": content_hash,
            "finalized_at": now,
            "finalized_by": user_id,
            "item_count": len(items),
            "message": "Draft finalized and locked",
        }

    def _normalize_draft_content(self, items: List[Dict]) -> Dict:
        return {
            "version": 1,
            "items": [
                {
                    "id": item["id"],
                    "summary": item.get("summary", ""),
                    "category": item.get("category"),
                    "section": item.get("section"),
                    "priority": item.get("priority", "normal"),
                    "is_critical": item.get("is_critical", False),
                    "requires_action": item.get("requires_action", False),
                    "action_summary": item.get("action_summary"),
                    "entity_type": item.get("entity_type"),
                    "entity_id": item.get("entity_id"),
                    "risk_tags": item.get("risk_tags", []),
                }
                for item in items
            ],
        }

    # ── Stage 2: Export ───────────────────────────────────────────────────────

    async def export_handover(
        self,
        yacht_id: str,
        user_id: str,
        export_type: str = "html",
        section: Optional[str] = None,
        department: Optional[str] = None,
        shift_date: Optional[str] = None,
        user_role: Optional[str] = None,
    ) -> Dict:
        _OFFICER_ROLES = {"chief_engineer", "chief_officer", "captain", "manager"}
        if user_role and user_role not in _OFFICER_ROLES:
            return {
                "status": "error",
                "error_code": "FORBIDDEN",
                "message": f"Requires officer+ role. Your role: {user_role}",
            }
        query = self.db.table("handover_items").select("content_hash, is_finalized").eq("yacht_id", yacht_id).is_("deleted_at", None)
        if section:
            query = query.eq("section", section)

        result = query.limit(1).execute()
        if not result.data:
            return {"status": "error", "error_code": "NO_ITEMS", "message": "No items found for export"}

        item = result.data[0]
        if not item.get("is_finalized"):
            return {"status": "error", "error_code": "NOT_FINALIZED", "message": "Draft must be finalized before export"}

        content_hash = item.get("content_hash")

        try:
            from apps.api.services.handover_export_service import HandoverExportService
            export_service = HandoverExportService(self.db)
            export_result = await export_service.generate_export(
                yacht_id=yacht_id, user_id=user_id, export_type=export_type, include_completed=False
            )
        except ImportError as e:
            logger.error(f"Export service import failed: {e}")
            return {"status": "error", "error_code": "SERVICE_UNAVAILABLE", "message": "Export service not available"}
        except Exception as e:
            logger.error(f"Export generation failed: {e}", exc_info=True)
            return {"status": "error", "error_code": "EXPORT_FAILED", "message": f"Failed to generate export: {str(e)}"}

        document_bytes = export_result.html.encode('utf-8')
        document_hash = hashlib.sha256(document_bytes).hexdigest()
        export_id = export_result.export_id

        try:
            # DEPRECATED: `status` column retired as state-machine driver (PR #642).
            # `review_status` is SSOT. Written here only for T4 twin-path compat.
            self.db.table("handover_exports").update({
                "document_hash": document_hash,
                "content_hash": content_hash,
                "status": "pending_outgoing",
                "department": department,
                "shift_date": shift_date,
            }).eq("id", export_id).execute()
        except Exception as e:
            logger.error(f"Failed to update export record: {e}", exc_info=True)
            return {"status": "error", "error_code": "DATABASE_ERROR", "message": "Failed to update export record"}

        try:
            await self._notify_ledger_export_ready(
                yacht_id=yacht_id, export_id=export_id, user_id=user_id,
                notification_type="handover_ready_outgoing",
            )
        except Exception as e:
            logger.warning(f"Failed to send notification: {e}")

        logger.info(f"Export created: export_id={export_id}, document_hash={document_hash[:16]}")
        return {
            "status": "success",
            "export_id": export_id,
            "document_hash": document_hash,
            "content_hash": content_hash,
            "export_type": export_type,
            "total_items": export_result.total_items,
            "message": "Export generated, awaiting outgoing signature",
        }

    # ── Stage 3: Dual Signature ───────────────────────────────────────────────

    async def sign_outgoing(
        self,
        export_id: str,
        yacht_id: str,
        user_id: str,
        user_role: str,
        note: Optional[str] = None,
        method: str = "typed",
    ) -> Dict:
        """[DEPRECATED — T4] Migrate callers to POST /v1/handover/export/{id}/submit."""
        logger.warning(
            "DEPRECATED: HandoverWorkflowHandlers.sign_outgoing called for "
            "export=%s user=%s role=%s; migrate to POST /v1/handover/export/{id}/submit.",
            export_id, user_id, user_role,
        )

        result = self.db.table("handover_exports").select("*").eq("id", export_id).eq("yacht_id", yacht_id).single().execute()
        if not result.data:
            return {"status": "error", "error_code": "EXPORT_NOT_FOUND", "message": f"Export {export_id} not found"}

        export = result.data
        # DEPRECATED: reads legacy `status` column. `review_status` is SSOT (PR #642).
        if export["status"] != "pending_outgoing":
            return {"status": "error", "error_code": "INVALID_STATUS", "message": f"Export status is '{export['status']}', expected 'pending_outgoing'"}

        document_hash = export.get("document_hash")
        if not document_hash:
            return {"status": "error", "error_code": "MISSING_HASH", "message": "Export missing document_hash"}

        now = datetime.now(timezone.utc)
        signature_envelope = self._create_signature_envelope({
            "document_hash": document_hash,
            "export_id": export_id,
            "signer_user_id": user_id,
            "role": user_role,
            "timestamp": now.isoformat(),
            "method": method,
        })

        signatures = export.get("signatures") or {}
        signatures["outgoing"] = signature_envelope

        self.db.table("handover_exports").update({
            "outgoing_user_id": user_id,
            "outgoing_role": user_role,
            "outgoing_signed_at": now.isoformat(),
            "outgoing_comments": note,
            "signatures": json.dumps(signatures),
        }).eq("id", export_id).execute()

        await self._notify_ledger_export_ready(
            yacht_id=yacht_id, export_id=export_id, user_id=user_id,
            notification_type="handover_ready_incoming",
        )

        logger.info(f"Outgoing signature: export={export_id}, user={user_id}, role={user_role}")
        return {
            "status": "success",
            "export_id": export_id,
            "signed_at": now.isoformat(),
            "signed_by": user_id,
            "role": user_role,
            "signature_method": method,
            "message": "Outgoing signature recorded, awaiting incoming signature",
        }

    async def sign_incoming(
        self,
        export_id: str,
        yacht_id: str,
        user_id: str,
        user_role: str,
        acknowledge_critical: bool,
        note: Optional[str] = None,
        method: str = "typed",
    ) -> Dict:
        """Canonical incoming-crew acknowledgement. No twin exists."""
        result = (
            self.db.table("handover_exports")
            .select(
                "id, yacht_id, status, review_status, document_hash, signatures, "
                "incoming_signed_at, outgoing_user_id, exported_by_user_id, department"
            )
            .eq("id", export_id).eq("yacht_id", yacht_id).single().execute()
        )

        if not result.data:
            return {"status": "error", "error_code": "EXPORT_NOT_FOUND", "message": f"Export {export_id} not found"}

        export = result.data
        review_status = export.get("review_status")
        if review_status != "complete":
            return {
                "status": "error",
                "error_code": "INVALID_STATUS",
                "message": (
                    f"Export review_status is '{review_status}', expected 'complete' "
                    "(handover must be HOD-countersigned before incoming ack)."
                ),
            }

        if export.get("incoming_signed_at") is not None:
            return {"status": "error", "error_code": "INVALID_STATUS", "message": "Handover has already been acknowledged by incoming crew."}

        if not acknowledge_critical:
            return {"status": "error", "error_code": "CRITICAL_NOT_ACKNOWLEDGED", "message": "Must acknowledge critical items before signing"}

        document_hash = export.get("document_hash")
        now = datetime.now(timezone.utc)
        signature_envelope = self._create_signature_envelope({
            "document_hash": document_hash,
            "export_id": export_id,
            "signer_user_id": user_id,
            "role": user_role,
            "timestamp": now.isoformat(),
            "method": method,
            "critical_acknowledged": acknowledge_critical,
        })

        raw_sigs = export.get("signatures") or {}
        if isinstance(raw_sigs, str):
            try:
                signatures = json.loads(raw_sigs) if raw_sigs else {}
            except Exception:
                signatures = {}
        else:
            signatures = dict(raw_sigs)
        signatures["incoming"] = signature_envelope

        self.db.table("handover_exports").update({
            "incoming_user_id": user_id,
            "incoming_role": user_role,
            "incoming_signed_at": now.isoformat(),
            "incoming_comments": note,
            "incoming_acknowledged_critical": acknowledge_critical,
            "signatures": json.dumps(signatures),
            "signoff_complete": True,
            "status": "completed",  # legacy column kept in sync; review_status is SSOT
        }).eq("id", export_id).execute()

        logger.info(f"Incoming signature: export={export_id}, user={user_id}, signoff complete")

        self._emit_handover_acknowledged_events(
            export_id=export_id,
            yacht_id=yacht_id,
            actor_id=user_id,
            actor_role=user_role,
            acknowledge_critical=acknowledge_critical,
            outgoing_user_id=(export.get("outgoing_user_id") or export.get("exported_by_user_id")),
            department=export.get("department"),
            now_iso=now.isoformat(),
        )

        return {
            "status": "success",
            "export_id": export_id,
            "signed_at": now.isoformat(),
            "signed_by": user_id,
            "role": user_role,
            "signoff_complete": True,
            "message": "Handover sign-off complete",
        }

    def _create_signature_envelope(self, payload: Dict) -> Dict:
        import hmac
        payload_json = json.dumps(payload, sort_keys=True)
        sig = hmac.new(b"handover_signing_key_v1", payload_json.encode(), hashlib.sha256).hexdigest()
        return {"payload": payload, "signature": sig, "alg": "HS256", "typ": "soft"}

    def _emit_handover_acknowledged_events(
        self,
        export_id: str,
        yacht_id: str,
        actor_id: str,
        actor_role: str,
        acknowledge_critical: bool,
        outgoing_user_id: Optional[str],
        department: Optional[str],
        now_iso: str,
    ) -> None:
        try:
            from handlers.ledger_utils import build_ledger_event
        except Exception as e:
            logger.warning("sign_incoming: ledger_utils import failed: %s", e)
            return

        change_summary = "Handover acknowledged by incoming crew"
        metadata = {"acknowledged_critical": acknowledge_critical, "export_id": export_id}
        new_values = {
            "incoming_user_id": actor_id,
            "incoming_signed_at": now_iso,
            "incoming_acknowledged_critical": acknowledge_critical,
        }

        recipients: List[Dict[str, Any]] = [
            {"user_id": actor_id, "department": department, "role": actor_role}
        ]
        if outgoing_user_id and outgoing_user_id != actor_id:
            recipients.append({"user_id": outgoing_user_id, "department": department, "role": None})

        try:
            roles_result = (
                self.db.table("auth_users_roles")
                .select("user_id, role, department")
                .eq("yacht_id", yacht_id)
                .in_("role", ["captain", "manager"])
                .eq("is_active", True)
                .execute()
            )
            for r in (roles_result.data or []):
                recipients.append({"user_id": r["user_id"], "department": r.get("department") or department, "role": r.get("role")})
        except Exception as e:
            logger.warning("sign_incoming: auth_users_roles lookup failed: %s", e)

        seen_ids: set = set()
        for rec in recipients:
            uid = rec.get("user_id")
            if not uid or uid in seen_ids:
                continue
            seen_ids.add(uid)

            try:
                self.db.table("pms_audit_log").insert({
                    "id": str(uuid.uuid4()),
                    "yacht_id": yacht_id,
                    "entity_type": "handover_export",
                    "entity_id": export_id,
                    "action": "handover_acknowledged",
                    "user_id": uid,
                    "actor_id": actor_id,
                    "signature": {"actor_id": actor_id, "actor_role": actor_role, "timestamp": now_iso},
                    "old_values": {},
                    "new_values": new_values,
                    "metadata": metadata,
                    "created_at": now_iso,
                }).execute()
            except Exception as e:
                logger.warning("sign_incoming: pms_audit_log insert failed (export=%s, user=%s): %s", export_id, uid, e)

            try:
                ledger_event = build_ledger_event(
                    yacht_id=yacht_id, user_id=uid, event_type="handover",
                    entity_type="handover_export", entity_id=export_id,
                    action="handover_acknowledged", user_role=actor_role,
                    change_summary=change_summary, metadata=metadata,
                    department=rec.get("department"), new_state=new_values,
                )
                self.db.table("ledger_events").insert(ledger_event).execute()
            except Exception as e:
                logger.warning("sign_incoming: ledger_events insert failed (export=%s, user=%s): %s", export_id, uid, e)

            if uid == actor_id:
                continue
            try:
                self.db.table("pms_notifications").upsert({
                    "id": str(uuid.uuid4()),
                    "yacht_id": yacht_id,
                    "user_id": uid,
                    "notification_type": "handover_acknowledged",
                    "title": "Handover acknowledged",
                    "body": change_summary,
                    "priority": "normal",
                    "entity_type": "handover_export",
                    "entity_id": export_id,
                    "triggered_by": actor_id,
                    "idempotency_key": f"handover_acknowledged:{export_id}:{uid}",
                    "is_read": False,
                    "created_at": now_iso,
                }, on_conflict="yacht_id,user_id,idempotency_key").execute()
            except Exception as e:
                logger.warning("sign_incoming: pms_notifications upsert failed (export=%s, user=%s): %s", export_id, uid, e)

    # ── Stage 4: Verification & Pending ──────────────────────────────────────

    async def get_pending_handovers(
        self,
        yacht_id: str,
        user_id: str,
        role_filter: Optional[str] = None,
    ) -> Dict:
        query = self.db.table("handover_exports").select("*").eq("yacht_id", yacht_id)

        if role_filter == "outgoing":
            query = (
                query.in_("review_status", ["pending_review", "pending_hod_signature"])
                .is_("outgoing_signed_at", "null")
            )
        elif role_filter == "incoming":
            query = query.eq("review_status", "complete").is_("incoming_signed_at", "null")
        else:
            query = query.or_("review_status.neq.complete,incoming_signed_at.is.null")

        result = query.order("created_at", desc=True).execute()
        exports = result.data or []
        return {"status": "success", "pending_count": len(exports), "exports": exports}

    async def verify_export(self, export_id: str, yacht_id: str) -> Dict:
        result = self.db.table("handover_exports").select("*").eq("id", export_id).eq("yacht_id", yacht_id).single().execute()

        if not result.data:
            return {"status": "error", "error_code": "NOT_FOUND", "message": "Export not found"}

        export = result.data
        signatures = json.loads(export.get("signatures") or "{}")
        return {
            "status": "success",
            "export_id": export_id,
            "content_hash": export.get("content_hash"),
            "document_hash": export.get("document_hash"),
            "signoff_complete": export.get("signoff_complete", False),
            "outgoing": {
                "user_id": export.get("outgoing_user_id"),
                "role": export.get("outgoing_role"),
                "signed_at": export.get("outgoing_signed_at"),
                "signature": signatures.get("outgoing"),
            },
            "incoming": {
                "user_id": export.get("incoming_user_id"),
                "role": export.get("incoming_role"),
                "signed_at": export.get("incoming_signed_at"),
                "critical_acknowledged": export.get("incoming_acknowledged_critical"),
                "signature": signatures.get("incoming"),
            },
            "timestamps": {
                "exported_at": export.get("exported_at"),
                "completed_at": export.get("incoming_signed_at") if export.get("signoff_complete") else None,
            },
        }

    # ── Notifications ─────────────────────────────────────────────────────────

    async def _notify_ledger_export_ready(
        self, yacht_id: str, export_id: str, user_id: str, notification_type: str
    ):
        notification_data = {
            "id": str(uuid.uuid4()),
            "yacht_id": yacht_id,
            "notification_type": notification_type,
            "entity_type": "handover_export",
            "entity_id": export_id,
            "created_by": user_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "metadata": {"export_id": export_id, "action_required": "sign"},
        }
        self.db.table("notifications").insert(notification_data).execute()
        logger.info(f"Notification sent: type={notification_type}, export={export_id}")

    # ── Entity Lens read ──────────────────────────────────────────────────────

    async def get_export_entity(self, export_id: str, yacht_id: str, user_role: str) -> dict:
        """Return the full handover_export entity payload for the lens view."""
        supabase = self.db

        r = supabase.table("handover_exports").select("*") \
            .eq("id", export_id).eq("yacht_id", yacht_id).maybe_single().execute()

        if r is None or not r.data:
            raise Exception("Handover export not found")

        data = r.data

        # Sections priority: edited_content > generated draft > empty
        edited_content = data.get("edited_content") or {}
        if isinstance(edited_content, str):
            try:
                edited_content = json.loads(edited_content) if edited_content else {}
            except Exception:
                edited_content = {}
        if isinstance(edited_content, list):
            sections = edited_content
        elif isinstance(edited_content, dict):
            sections = edited_content.get("sections", [])
        else:
            sections = []

        if not sections:
            draft_id = data.get("draft_id")
            if draft_id:
                try:
                    dr = supabase.table("v_handover_draft_complete").select(
                        "sections"
                    ).eq("draft_id", draft_id).maybe_single().execute()
                    if dr and dr.data and dr.data.get("sections"):
                        raw_sections = dr.data["sections"] or []
                        mapped = []
                        for s in raw_sections:
                            s_items = []
                            for it in (s.get("items") or []):
                                s_items.append({
                                    "id": it.get("id", ""),
                                    "content": it.get("summary_text", "") or "",
                                    "priority": "critical" if it.get("is_critical") else "normal",
                                    "entity_type": it.get("source_entity_type"),
                                    "entity_id": it.get("source_entity_id"),
                                    "entity_url": it.get("entity_url"),
                                    "action_summary": it.get("action_summary"),
                                })
                            mapped.append({
                                "id": s.get("id", ""),
                                "title": s.get("display_title") or s.get("bucket_name") or "",
                                "content": "",
                                "items": s_items,
                                "is_critical": (s.get("critical_count") or 0) > 0,
                                "order": s.get("section_order") or 0,
                            })
                        sections = mapped
                except Exception as _draft_err:
                    logger.warning(
                        "Fallback to v_handover_draft_complete failed for draft_id=%s: %s",
                        draft_id, _draft_err
                    )

        raw_storage_url = data.get("original_storage_url") or data.get("file_name") or ""
        export_path = raw_storage_url.replace("handover-exports/", "", 1) if raw_storage_url.startswith("handover-exports/") else raw_storage_url
        export_url = _sign_url(supabase, "handover-exports", export_path) if export_path else None

        nav = [n for n in [
            _nav("handover_export", data.get("draft_id"), "Source Draft"),
        ] if n]

        user_sig = data.get("user_signature")
        dept = data.get("department") or ""

        incoming_user_id = data.get("incoming_user_id")
        incoming_user_name = None
        if incoming_user_id:
            try:
                ir = supabase.table("auth_users_profiles").select(
                    "name, email"
                ).eq("id", incoming_user_id).eq("yacht_id", yacht_id).limit(1).execute()
                if ir and ir.data:
                    prof = ir.data[0]
                    incoming_user_name = prof.get("name") or prof.get("email")
            except Exception as _ie:
                logger.warning("Failed to resolve incoming_user_name for %s: %s", incoming_user_id, _ie)

        raw_sigs = data.get("signatures") or {}
        if isinstance(raw_sigs, str):
            try:
                raw_sigs = json.loads(raw_sigs) if raw_sigs else {}
            except Exception:
                raw_sigs = {}
        incoming_signature = raw_sigs.get("incoming") if isinstance(raw_sigs, dict) else None

        _entity_response = {
            "id": data.get("id"),
            "yacht_id": data.get("yacht_id"),
            "title": f"{dept} Handover Report".strip() if dept else "Handover Report",
            "status": data.get("review_status", "pending_review"),
            "review_status": data.get("review_status"),
            "export_type": data.get("export_type"),
            "export_status": data.get("export_status"),
            "department": dept or None,
            "original_storage_url": data.get("original_storage_url"),
            "document_hash": data.get("document_hash"),
            "file_name": data.get("file_name"),
            "export_url": export_url,
            "sections": sections,
            "user_signature": user_sig,
            "userSignature": user_sig,
            "hod_signature": data.get("hod_signature"),
            "incoming_user_id": incoming_user_id,
            "incoming_user_name": incoming_user_name,
            "incoming_role": data.get("incoming_role"),
            "incoming_signed_at": data.get("incoming_signed_at"),
            "incoming_comments": data.get("incoming_comments"),
            "incoming_acknowledged_critical": data.get("incoming_acknowledged_critical"),
            "incoming_signature": incoming_signature,
            "signoff_complete": data.get("signoff_complete"),
            "submitted_at": data.get("exported_at"),
            "created_at": data.get("created_at"),
            "draft_id": data.get("draft_id"),
            "attachments": [],
            "related_entities": nav,
        }
        _entity_response["available_actions"] = get_available_actions(
            "handover_export", _entity_response, user_role
        )
        return _entity_response


# ============================================================================
# Phase 4 module-level handlers
# Signature: (payload, context, yacht_id, user_id, user_context, db_client)
# ============================================================================

from fastapi import HTTPException
from supabase import Client


# ── helpers ──────────────────────────────────────────────────────────────────

def _find_handover_export(db_client: Client, export_id: str, yacht_id: str, columns: str = "id"):
    """Return (row_data, table_name) for the first matching handover record, or raise 404."""
    for table_name in ("handover_exports", "handovers", "handover"):
        try:
            res = db_client.table(table_name).select(columns).eq(
                "id", export_id
            ).eq("yacht_id", yacht_id).maybe_single().execute()
            if res.data:
                return res, table_name
        except Exception:
            continue
    raise HTTPException(status_code=404, detail="Handover not found")


# ── blocked (parent table does not yet exist) ─────────────────────────────────

async def create_handover(
    payload: dict, context: dict, yacht_id: str, user_id: str,
    user_context: dict, db_client: Client,
) -> dict:
    raise HTTPException(
        status_code=501,
        detail="Action 'create_handover' BLOCKED: dash_handover_items.handover_id is NOT NULL but no parent handovers table exists.",
    )


async def acknowledge_handover(
    payload: dict, context: dict, yacht_id: str, user_id: str,
    user_context: dict, db_client: Client,
) -> dict:
    raise HTTPException(
        status_code=501,
        detail="Action 'acknowledge_handover' BLOCKED: dash_handover_items.handover_id is NOT NULL but no parent handovers table exists.",
    )


async def update_handover(
    payload: dict, context: dict, yacht_id: str, user_id: str,
    user_context: dict, db_client: Client,
) -> dict:
    raise HTTPException(
        status_code=501,
        detail="Action 'update_handover' BLOCKED: dash_handover_items.handover_id is NOT NULL but no parent handovers table exists.",
    )


async def delete_handover(
    payload: dict, context: dict, yacht_id: str, user_id: str,
    user_context: dict, db_client: Client,
) -> dict:
    raise HTTPException(
        status_code=501,
        detail="Action 'delete_handover' BLOCKED: dash_handover_items.handover_id is NOT NULL but no parent handovers table exists.",
    )


async def filter_handover(
    payload: dict, context: dict, yacht_id: str, user_id: str,
    user_context: dict, db_client: Client,
) -> dict:
    raise HTTPException(
        status_code=501,
        detail="Action 'filter_handover' BLOCKED: dash_handover_items.handover_id is NOT NULL but no parent handovers table exists.",
    )


# ── add_to_handover ───────────────────────────────────────────────────────────

async def add_to_handover(
    payload: dict,
    context: dict,
    yacht_id: str,
    user_id: str,
    user_context: dict,
    db_client: Client,
) -> dict:
    handler = HandoverHandlers(db_client)

    summary = payload.get("summary") or payload.get("summary_text")
    if not summary:
        title = payload.get("title")
        description = payload.get("description", "")
        summary = f"{title}\n\n{description}" if title and description else (title or description or "")

    if not summary or len(summary.strip()) < 6:
        raise HTTPException(
            status_code=400,
            detail={"status": "error", "error_code": "VALIDATION_ERROR",
                    "message": "Summary must be at least 6 characters"},
        )

    entity_type = payload.get("entity_type", "note")
    entity_id = payload.get("entity_id")
    category = payload.get("category", "fyi")
    priority = payload.get("priority", "normal")
    is_critical = payload.get("is_critical", False)
    requires_action = payload.get("requires_action", False)
    action_summary = payload.get("action_summary")
    section = payload.get("section") or payload.get("presentation_bucket")

    try:
        result = await handler.add_to_handover_execute(
            entity_type=entity_type,
            entity_id=entity_id,
            summary=summary,
            category=category,
            yacht_id=yacht_id,
            user_id=user_id,
            priority=priority,
            section=section,
            is_critical=is_critical,
            requires_action=requires_action,
            action_summary=action_summary,
        )

        if result.get("status") == "error":
            error_code = result.get("error_code", "")
            status_code = 500 if error_code == "INTERNAL_ERROR" else 400
            raise HTTPException(
                status_code=status_code,
                detail={"status": "error", "error_code": error_code, "message": result.get("message")},
            )

        try:
            ledger_event = build_ledger_event(
                yacht_id=yacht_id,
                user_id=user_id,
                event_type="create",
                entity_type="handover_item",
                entity_id=result.get("item_id", entity_id or yacht_id),
                action="add_to_handover",
                user_role=user_context.get("role"),
                change_summary=f"Added to handover: {summary[:80]}",
            )
            db_client.table("ledger_events").insert(ledger_event).execute()
        except Exception as ledger_err:
            if "204" not in str(ledger_err):
                logger.warning(f"[Ledger] Failed to record add_to_handover: {ledger_err}")

        result["_ledger_written"] = True
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Unexpected error in add_to_handover: {e}")
        raise HTTPException(
            status_code=500,
            detail={"status": "error", "error_code": "INTERNAL_ERROR",
                    "message": f"Failed to add to handover: {str(e)}"},
        )


# ── add_document_to_handover ──────────────────────────────────────────────────

async def add_document_to_handover(
    payload: dict,
    context: dict,
    yacht_id: str,
    user_id: str,
    user_context: dict,
    db_client: Client,
) -> dict:
    handover_id = payload.get("handover_id")
    document_id = payload.get("document_id")
    summary = payload.get("summary", "")

    if not handover_id:
        raise HTTPException(status_code=400, detail="handover_id is required")
    if not document_id:
        raise HTTPException(status_code=400, detail="document_id is required")

    _find_handover_export(db_client, handover_id, yacht_id)

    item_data = {
        "id": str(uuid.uuid4()),
        "yacht_id": yacht_id,
        "handover_id": handover_id,
        "entity_id": document_id,
        "entity_type": "document",
        "summary": summary or "Document attached",
        "added_by": user_id,
        "status": "pending",
    }
    db_client.table("handover_items").insert(item_data).execute()

    return {
        "status": "success",
        "success": True,
        "message": "Document added to handover",
        "handover_id": handover_id,
        "document_id": document_id,
    }


# ── add_predictive_insight_to_handover ───────────────────────────────────────

async def add_predictive_insight_to_handover(
    payload: dict,
    context: dict,
    yacht_id: str,
    user_id: str,
    user_context: dict,
    db_client: Client,
) -> dict:
    handover_id = payload.get("handover_id")
    insight_text = payload.get("insight_text")
    insight_type = payload.get("insight_type", "general")

    if not handover_id:
        raise HTTPException(status_code=400, detail="handover_id is required")
    if not insight_text:
        raise HTTPException(status_code=400, detail="insight_text is required")

    handover, table_name = _find_handover_export(db_client, handover_id, yacht_id, "id, metadata")

    metadata = handover.data.get("metadata", {}) or {}
    insights = metadata.get("predictive_insights", []) or []
    insights.append({
        "text": insight_text,
        "type": insight_type,
        "added_by": user_id,
        "added_at": datetime.now(timezone.utc).isoformat(),
    })
    metadata["predictive_insights"] = insights

    db_client.table(table_name).update({
        "metadata": metadata,
        "updated_by": user_id,
    }).eq("id", handover_id).execute()

    return {
        "status": "success",
        "success": True,
        "message": "Predictive insight added to handover",
        "handover_id": handover_id,
        "insights_count": len(insights),
    }


# ── edit_handover_section ─────────────────────────────────────────────────────
# Uses edited_content.sections[] on handover_exports (not metadata.sections).

async def edit_handover_section(
    payload: dict,
    context: dict,
    yacht_id: str,
    user_id: str,
    user_context: dict,
    db_client: Client,
) -> dict:
    export_id = (
        payload.get("export_id")
        or payload.get("handover_id")
        or context.get("entity_id")
    )
    section_name = payload.get("section_name")
    content = payload.get("new_text") or payload.get("content", "")

    if not export_id:
        raise HTTPException(status_code=400, detail="export_id or handover_id is required")
    if not section_name:
        raise HTTPException(status_code=400, detail="section_name is required")

    res = db_client.table("handover_exports").select(
        "id, yacht_id, edited_content, review_status"
    ).eq("id", export_id).eq("yacht_id", yacht_id).limit(1).execute()

    if not res.data:
        raise HTTPException(status_code=404, detail=f"Handover export {export_id} not found")

    export_row = res.data[0]
    if export_row.get("review_status") not in (None, "pending_review"):
        raise HTTPException(status_code=409, detail="Cannot edit after submission")

    edited_content = export_row.get("edited_content") or {}
    if "sections" not in edited_content:
        edited_content["sections"] = []

    found = False
    for section in edited_content["sections"]:
        if section.get("title") == section_name or section.get("id") == section_name:
            section["content"] = content
            section["updated_by"] = user_id
            section["updated_at"] = datetime.now(timezone.utc).isoformat()
            found = True
            break

    if not found:
        edited_content["sections"].append({
            "title": section_name,
            "content": content,
            "updated_by": user_id,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        })

    edited_content["last_saved_at"] = datetime.now(timezone.utc).isoformat()
    edited_content["saved_by"] = user_id

    db_client.table("handover_exports").update({"edited_content": edited_content}).eq(
        "id", export_id
    ).eq("yacht_id", yacht_id).execute()

    return {"status": "success", "export_id": export_id, "section_name": section_name}


# ── export_handover ───────────────────────────────────────────────────────────

async def export_handover(
    payload: dict,
    context: dict,
    yacht_id: str,
    user_id: str,
    user_context: dict,
    db_client: Client,
) -> dict:
    handover_id = payload.get("handover_id")
    export_format = payload.get("format", "pdf")

    if not handover_id:
        raise HTTPException(status_code=400, detail="handover_id is required")

    handover, _ = _find_handover_export(db_client, handover_id, yacht_id, "*")

    items = []
    try:
        items_res = db_client.table("handover_items").select("*").eq(
            "handover_id", handover_id
        ).execute()
        items = items_res.data or []
    except Exception:
        pass

    return {
        "status": "success",
        "success": True,
        "handover": handover.data,
        "items": items,
        "export_format": export_format,
        "message": f"Handover ready for {export_format} export",
    }


# ── regenerate_handover_summary ───────────────────────────────────────────────

async def regenerate_handover_summary(
    payload: dict,
    context: dict,
    yacht_id: str,
    user_id: str,
    user_context: dict,
    db_client: Client,
) -> dict:
    handover_id = payload.get("handover_id")

    if not handover_id:
        raise HTTPException(status_code=400, detail="handover_id is required")

    handover, table_name = _find_handover_export(db_client, handover_id, yacht_id, "id, metadata")

    metadata = handover.data.get("metadata", {}) or {}
    metadata["summary_regeneration_requested"] = True
    metadata["summary_regeneration_requested_at"] = datetime.now(timezone.utc).isoformat()
    metadata["summary_regeneration_requested_by"] = user_id

    db_client.table(table_name).update({
        "metadata": metadata,
        "updated_by": user_id,
    }).eq("id", handover_id).execute()

    return {
        "status": "success",
        "success": True,
        "message": "Summary regeneration requested",
        "handover_id": handover_id,
    }


# ── sign_handover ─────────────────────────────────────────────────────────────
# Migrated from action_router/dispatchers/handover.py (_sign_handover).
# Uses handover_exports table; advances review_status to pending_hod_signature.

async def sign_handover(
    payload: dict,
    context: dict,
    yacht_id: str,
    user_id: str,
    user_context: dict,
    db_client: Client,
) -> dict:
    export_id = (
        payload.get("export_id")
        or payload.get("handover_id")
        or context.get("entity_id")
    )

    if not export_id:
        raise HTTPException(status_code=400, detail="export_id or handover_id is required")

    res = db_client.table("handover_exports").select(
        "id, yacht_id, review_status, exported_by_user_id"
    ).eq("id", export_id).eq("yacht_id", yacht_id).limit(1).execute()

    if not res.data:
        raise HTTPException(status_code=404, detail=f"Handover export {export_id} not found")

    review_status = res.data[0].get("review_status")
    if review_status not in (None, "pending_review"):
        raise HTTPException(
            status_code=409,
            detail=f"Cannot sign: export is '{review_status}', expected 'pending_review'",
        )

    now = datetime.now(timezone.utc).isoformat()
    signature = payload.get("signature") or {"signer_name": user_id, "signed_at": now}

    db_client.table("handover_exports").update({
        "user_signature": signature,
        "user_signed_at": now,
        "review_status": "pending_hod_signature",
    }).eq("id", export_id).eq("yacht_id", yacht_id).execute()

    return {"status": "success", "export_id": export_id, "review_status": "pending_hod_signature"}


# ── archive_handover ──────────────────────────────────────────────────────────

async def archive_handover(
    payload: dict,
    context: dict,
    yacht_id: str,
    user_id: str,
    user_context: dict,
    db_client: Client,
) -> dict:
    export_id = (
        payload.get("export_id")
        or payload.get("handover_id")
        or context.get("entity_id")
    )

    if not export_id:
        raise HTTPException(status_code=400, detail="export_id or handover_id is required")

    res = db_client.table("handover_exports").select("id").eq(
        "id", export_id
    ).eq("yacht_id", yacht_id).limit(1).execute()

    if not res.data:
        raise HTTPException(status_code=404, detail=f"Handover export {export_id} not found")

    now = datetime.now(timezone.utc).isoformat()
    db_client.table("handover_exports").update({
        "deleted_at": now,
        "updated_by": user_id,
    }).eq("id", export_id).eq("yacht_id", yacht_id).execute()

    return {"status": "success", "export_id": export_id, "archived_at": now}


# ── HANDLERS registry ─────────────────────────────────────────────────────────

HANDLERS: dict = {
    # Blocked (parent handovers table does not exist)
    "create_handover": create_handover,
    "acknowledge_handover": acknowledge_handover,
    "update_handover": update_handover,
    "delete_handover": delete_handover,
    "filter_handover": filter_handover,
    # Live actions
    "add_to_handover": add_to_handover,
    "add_document_to_handover": add_document_to_handover,
    "add_predictive_insight_to_handover": add_predictive_insight_to_handover,
    "edit_handover_section": edit_handover_section,
    "export_handover": export_handover,
    "regenerate_handover_summary": regenerate_handover_summary,
    "sign_handover": sign_handover,
    "archive_handover": archive_handover,
}
