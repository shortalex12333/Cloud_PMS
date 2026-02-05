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
from typing import Dict, Optional
import logging
import uuid

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from actions.action_response_schema import ResponseBuilder

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
            valid_types = ["fault", "work_order", "equipment", "document_chunk", "document", "part", "note"]
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
            if not summary or len(summary) < 10:
                return ResponseBuilder.error(
                    action="add_to_handover",
                    error_code="VALIDATION_ERROR",
                    message="Summary must be at least 10 characters"
                )

            if len(summary) > 2000:
                return ResponseBuilder.error(
                    action="add_to_handover",
                    error_code="VALIDATION_ERROR",
                    message="Summary must be less than 2000 characters"
                )

            # Validate category (must match DB constraint)
            valid_categories = ["urgent", "in_progress", "completed", "watch", "fyi"]
            if category not in valid_categories:
                return ResponseBuilder.error(
                    action="add_to_handover",
                    error_code="VALIDATION_ERROR",
                    message=f"Invalid category: {category}. Must be one of: {', '.join(valid_categories)}"
                )

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
    # Alias methods for backward compatibility
    # =========================================================================

    # Alias for tests that use summary_text instead of summary
    async def add_to_handover_execute_legacy(self, *args, summary_text: str = None, **kwargs):
        """Legacy wrapper - converts summary_text to summary."""
        if summary_text and 'summary' not in kwargs:
            kwargs['summary'] = summary_text
        return await self.add_to_handover_execute(*args, **kwargs)


__all__ = ["HandoverHandlers"]
