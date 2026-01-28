"""
Handover Handlers
=================

P0 Actions for shift handover:
- add_to_handover (P0 Action #8) - MUTATE

Based on specs: /P0_ACTION_CONTRACTS.md - Cluster 05: HANDOVER_COMMUNICATION
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
        summary_text: str,
        category: str,
        yacht_id: str,
        user_id: str,
        priority: str = "normal"
    ) -> Dict:
        """
        POST /v1/actions/execute (action=add_to_handover)

        Add item to shift handover list.

        MUTATE action - execute only (no preview needed, low-risk).

        Creates entry in handover table linking to entity.

        Returns:
        - Handover entry details
        - WHO added it
        - WHEN added
        """
        try:
            # Validate entity type
            valid_types = ["fault", "work_order", "equipment", "document_chunk", "part"]
            if entity_type not in valid_types:
                return ResponseBuilder.error(
                    action="add_to_handover",
                    error_code="INVALID_ENTITY_TYPE",
                    message=f"Invalid entity type: {entity_type}. Must be one of: {', '.join(valid_types)}"
                )

            # Validate summary text
            if not summary_text or len(summary_text) < 10:
                return ResponseBuilder.error(
                    action="add_to_handover",
                    error_code="VALIDATION_ERROR",
                    message="Summary text must be at least 10 characters"
                )

            if len(summary_text) > 2000:
                return ResponseBuilder.error(
                    action="add_to_handover",
                    error_code="VALIDATION_ERROR",
                    message="Summary text must be less than 2000 characters"
                )

            # Validate category (must match DB constraint)
            valid_categories = ["urgent", "in_progress", "completed", "watch", "fyi"]
            if category not in valid_categories:
                return ResponseBuilder.error(
                    action="add_to_handover",
                    error_code="VALIDATION_ERROR",
                    message=f"Invalid category: {category}. Must be one of: {', '.join(valid_categories)}"
                )

            # Check for duplicate entry (optional - allow override)
            # NOTE: As per spec, duplicates are allowed but can be flagged
            existing = self.db.table("pms_handover").select(
                "id"
            ).eq("yacht_id", yacht_id).eq(
                "entity_type", entity_type
            ).eq("entity_id", entity_id).execute()

            # Create handover entry
            handover_id = str(uuid.uuid4())
            priority_value = {"low": 1, "normal": 2, "high": 3, "urgent": 4}.get(priority, 2)

            handover_entry = {
                "id": handover_id,
                "yacht_id": yacht_id,
                "entity_type": entity_type,
                "entity_id": entity_id,
                "summary_text": summary_text,
                "category": category,
                "priority": priority_value,
                "added_by": user_id,
                "added_at": datetime.now(timezone.utc).isoformat()
            }

            insert_result = self.db.table("pms_handover").insert(
                handover_entry
            ).execute()

            if not insert_result.data:
                return ResponseBuilder.error(
                    action="add_to_handover",
                    error_code="INTERNAL_ERROR",
                    message="Failed to create handover entry"
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
                    "entity_type": "handover",
                    "entity_id": handover_id,
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
                        "priority": priority
                    },
                    "created_at": datetime.now(timezone.utc).isoformat()
                }).execute()
            except Exception as e:
                logger.warning(f"Failed to create audit log: {e}")

            # Build response
            return ResponseBuilder.success(
                action="add_to_handover",
                result={
                    "handover_entry": {
                        "id": handover_id,
                        "yacht_id": yacht_id,
                        "entity_type": entity_type,
                        "entity_id": entity_id,
                        "summary_text": summary_text,
                        "category": category,
                        "priority": priority,
                        "added_at": handover_entry["added_at"],
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


__all__ = ["HandoverHandlers"]
