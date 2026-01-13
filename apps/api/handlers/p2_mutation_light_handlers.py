"""
P2 Mutation Light Handlers
===========================

P2 actions for notes, photos, and lightweight mutations.

Actions:
- #17 add_fault_note
- #18 add_fault_photo
- #19 add_work_order_note (extends P0)
- #20 add_work_order_photo
- #21 add_parts_to_work_order
- #22 assign_work_order
- #23 add_equipment_note

These are "soft confirmation" actions - minor edits that don't
require full signature flow but do create audit trails.
"""

from datetime import datetime, timezone, timedelta
from typing import Dict, Optional, List
import logging
import uuid

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

logger = logging.getLogger(__name__)


class P2MutationLightHandlers:
    """
    P2 mutation light handlers.

    All actions:
    - Are low-risk (notes, photos, status updates)
    - Don't require full signature confirmation
    - Create audit log entries for accountability
    - Support yacht isolation
    """

    def __init__(self, supabase_client):
        self.db = supabase_client

    # =========================================================================
    # P2 #17: add_fault_note
    # =========================================================================

    async def add_fault_note_execute(
        self,
        fault_id: str,
        note_text: str,
        yacht_id: str,
        user_id: str,
        note_type: str = "general"
    ) -> Dict:
        """
        Add a note to a fault record.

        Notes are stored in pms_fault_notes table (if exists) or
        appended to fault's metadata.notes JSONB array.

        note_type options:
        - general: General observation
        - diagnosis: Diagnostic findings
        - action_taken: Actions performed
        - follow_up: Follow-up required
        """
        try:
            # Validate fault exists and belongs to yacht
            fault_result = self.db.table("pms_faults").select(
                "id, fault_code, title, metadata"
            ).eq("id", fault_id).eq("yacht_id", yacht_id).limit(1).execute()

            if not fault_result.data or len(fault_result.data) == 0:
                return {
                    "status": "error",
                    "error_code": "FAULT_NOT_FOUND",
                    "message": f"Fault not found: {fault_id}"
                }

            fault = fault_result.data[0]

            # Validate note_type
            valid_types = ["general", "diagnosis", "action_taken", "follow_up", "observation"]
            if note_type not in valid_types:
                note_type = "general"

            # Create note in pms_notes table (polymorphic notes table with fault_id FK)
            now = datetime.now(timezone.utc).isoformat()
            note_id = str(uuid.uuid4())

            note_data = {
                "id": note_id,
                "fault_id": fault_id,
                "yacht_id": yacht_id,
                "text": note_text,  # pms_notes uses 'text' column
                "note_type": note_type,
                "created_by": user_id,
                "created_at": now,
                "metadata": {}
            }

            note_result = self.db.table("pms_notes").insert(note_data).execute()
            if note_result.data:
                note = note_result.data[0]
            else:
                raise Exception("Insert returned no data")

            # Create audit log
            await self._create_audit_log(
                yacht_id=yacht_id,
                action="add_fault_note",
                entity_type="fault",
                entity_id=fault_id,
                user_id=user_id,
                new_values={
                    "note_id": note_id,
                    "note_text": note_text[:100],  # Truncate for audit
                    "note_type": note_type
                }
            )

            return {
                "status": "success",
                "action": "add_fault_note",
                "result": {
                    "note": {
                        "id": note_id,
                        "fault_id": fault_id,
                        "note_text": note_text,
                        "note_type": note_type,
                        "created_by": user_id,
                        "created_at": now
                    },
                    "fault_code": fault.get("fault_code")
                },
                "message": f"Note added to fault {fault.get('fault_code', fault_id[:8])}"
            }

        except Exception as e:
            logger.error(f"add_fault_note_execute failed: {e}", exc_info=True)
            return {
                "status": "error",
                "error_code": "INTERNAL_ERROR",
                "message": str(e)
            }

    # =========================================================================
    # P2 #18: add_fault_photo
    # =========================================================================

    async def add_fault_photo_execute(
        self,
        fault_id: str,
        storage_path: str,
        filename: str,
        yacht_id: str,
        user_id: str,
        mime_type: str = "image/jpeg",
        category: str = "photo",
        description: Optional[str] = None
    ) -> Dict:
        """
        Attach a photo to a fault record.

        Photo file should already be uploaded to Supabase Storage.
        This creates the attachment record linking it to the fault.

        Args:
            storage_path: Path in Supabase Storage (e.g., "faults/abc123/photo1.jpg")
            filename: Original filename
            category: "photo", "before", "after", "evidence"
        """
        try:
            # Validate fault exists
            fault_result = self.db.table("pms_faults").select(
                "id, fault_code, title"
            ).eq("id", fault_id).eq("yacht_id", yacht_id).limit(1).execute()

            if not fault_result.data or len(fault_result.data) == 0:
                return {
                    "status": "error",
                    "error_code": "FAULT_NOT_FOUND",
                    "message": f"Fault not found: {fault_id}"
                }

            fault = fault_result.data[0]
            now = datetime.now(timezone.utc).isoformat()

            # Create document record (using 'documents' table, not 'attachments')
            attachment_data = {
                "yacht_id": yacht_id,
                "filename": filename,
                "content_type": mime_type,
                "storage_path": storage_path,
                "source": "fault_photo",
                "doc_type": category,  # photo, before, after, evidence
                "tags": [f"fault:{fault_id}", f"fault_code:{fault.get('fault_code', '')}"],
                "metadata": {
                    "entity_type": "fault",
                    "entity_id": fault_id,
                    "description": description,
                    "fault_code": fault.get("fault_code"),
                    "uploaded_by": user_id,
                    "category": category
                },
                "created_at": now
            }

            attach_result = self.db.table("documents").insert(attachment_data).execute()

            if not attach_result.data:
                return {
                    "status": "error",
                    "error_code": "INTERNAL_ERROR",
                    "message": "Failed to create attachment record"
                }

            attachment = attach_result.data[0]

            # Create audit log
            await self._create_audit_log(
                yacht_id=yacht_id,
                action="add_fault_photo",
                entity_type="fault",
                entity_id=fault_id,
                user_id=user_id,
                new_values={
                    "attachment_id": attachment["id"],
                    "filename": filename,
                    "category": category
                }
            )

            return {
                "status": "success",
                "action": "add_fault_photo",
                "result": {
                    "attachment": {
                        "id": attachment["id"],
                        "fault_id": fault_id,
                        "filename": filename,
                        "storage_path": storage_path,
                        "category": category,
                        "uploaded_at": now
                    },
                    "fault_code": fault.get("fault_code")
                },
                "message": f"Photo attached to fault {fault.get('fault_code', fault_id[:8])}"
            }

        except Exception as e:
            logger.error(f"add_fault_photo_execute failed: {e}", exc_info=True)
            return {
                "status": "error",
                "error_code": "INTERNAL_ERROR",
                "message": str(e)
            }

    # =========================================================================
    # P2 #19: add_work_order_note (extends P0 #3)
    # =========================================================================

    async def add_work_order_note_execute(
        self,
        work_order_id: str,
        note_text: str,
        yacht_id: str,
        user_id: str,
        note_type: str = "general"
    ) -> Dict:
        """
        Add a note to a work order.

        This is functionally identical to P0 #3 but included here
        for P2 completeness and consistent API surface.

        note_type options:
        - general: General note
        - progress: Progress update
        - issue: Problem encountered
        - resolution: How issue was resolved
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

            # Validate note_type
            valid_types = ["general", "progress", "issue", "resolution"]
            if note_type not in valid_types:
                note_type = "general"

            now = datetime.now(timezone.utc).isoformat()

            # Create note
            note_data = {
                "work_order_id": work_order_id,
                "note_text": note_text,
                "note_type": note_type,
                "created_by": user_id,
                "created_at": now
            }

            note_result = self.db.table("pms_work_order_notes").insert(note_data).execute()

            if not note_result.data:
                return {
                    "status": "error",
                    "error_code": "INTERNAL_ERROR",
                    "message": "Failed to create note"
                }

            note = note_result.data[0]

            # Create audit log
            await self._create_audit_log(
                yacht_id=yacht_id,
                action="add_work_order_note",
                entity_type="work_order",
                entity_id=work_order_id,
                user_id=user_id,
                new_values={
                    "note_id": note["id"],
                    "note_type": note_type,
                    "note_text": note_text[:100]
                }
            )

            return {
                "status": "success",
                "action": "add_work_order_note",
                "result": {
                    "note": {
                        "id": note["id"],
                        "work_order_id": work_order_id,
                        "note_text": note_text,
                        "note_type": note_type,
                        "created_by": user_id,
                        "created_at": now
                    },
                    "work_order_number": wo.get("wo_number")
                },
                "message": f"Note added to {wo.get('wo_number', 'work order')}"
            }

        except Exception as e:
            logger.error(f"add_work_order_note_execute failed: {e}", exc_info=True)
            return {
                "status": "error",
                "error_code": "INTERNAL_ERROR",
                "message": str(e)
            }

    # =========================================================================
    # P2 #20: add_work_order_photo
    # =========================================================================

    async def add_work_order_photo_execute(
        self,
        work_order_id: str,
        storage_path: str,
        filename: str,
        yacht_id: str,
        user_id: str,
        mime_type: str = "image/jpeg",
        category: str = "photo",
        description: Optional[str] = None
    ) -> Dict:
        """
        Attach a photo to a work order.

        Photo file should already be uploaded to Supabase Storage.

        category options:
        - photo: General photo
        - before: Before work started
        - after: After work completed
        - evidence: Evidence of issue/repair
        - parts: Photo of parts used
        """
        try:
            # Validate work order exists
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
            now = datetime.now(timezone.utc).isoformat()

            # Create document record (using 'documents' table)
            attachment_data = {
                "yacht_id": yacht_id,
                "filename": filename,
                "content_type": mime_type,
                "storage_path": storage_path,
                "source": "work_order_photo",
                "doc_type": category,
                "tags": [f"work_order:{work_order_id}", f"wo_number:{wo.get('wo_number', '')}"],
                "metadata": {
                    "entity_type": "work_order",
                    "entity_id": work_order_id,
                    "description": description,
                    "wo_number": wo.get("wo_number"),
                    "uploaded_by": user_id,
                    "category": category
                },
                "created_at": now
            }

            attach_result = self.db.table("documents").insert(attachment_data).execute()

            if not attach_result.data:
                return {
                    "status": "error",
                    "error_code": "INTERNAL_ERROR",
                    "message": "Failed to create attachment record"
                }

            attachment = attach_result.data[0]

            # Create audit log
            await self._create_audit_log(
                yacht_id=yacht_id,
                action="add_work_order_photo",
                entity_type="work_order",
                entity_id=work_order_id,
                user_id=user_id,
                new_values={
                    "attachment_id": attachment["id"],
                    "filename": filename,
                    "category": category
                }
            )

            return {
                "status": "success",
                "action": "add_work_order_photo",
                "result": {
                    "attachment": {
                        "id": attachment["id"],
                        "work_order_id": work_order_id,
                        "filename": filename,
                        "storage_path": storage_path,
                        "category": category,
                        "uploaded_at": now
                    },
                    "work_order_number": wo.get("wo_number")
                },
                "message": f"Photo attached to {wo.get('wo_number', 'work order')}"
            }

        except Exception as e:
            logger.error(f"add_work_order_photo_execute failed: {e}", exc_info=True)
            return {
                "status": "error",
                "error_code": "INTERNAL_ERROR",
                "message": str(e)
            }

    # =========================================================================
    # P2 #22: assign_work_order
    # =========================================================================

    async def assign_work_order_execute(
        self,
        work_order_id: str,
        assignee_id: str,
        yacht_id: str,
        user_id: str,
        notes: Optional[str] = None
    ) -> Dict:
        """
        Assign a work order to a crew member.

        Updates the assigned_to field and creates audit trail.
        """
        try:
            # Validate work order exists
            wo_result = self.db.table("pms_work_orders").select(
                "id, wo_number, status, assigned_to"
            ).eq("id", work_order_id).eq("yacht_id", yacht_id).limit(1).execute()

            if not wo_result.data or len(wo_result.data) == 0:
                return {
                    "status": "error",
                    "error_code": "WO_NOT_FOUND",
                    "message": f"Work order not found: {work_order_id}"
                }

            wo = wo_result.data[0]

            if wo["status"] in ("completed", "closed", "cancelled"):
                return {
                    "status": "error",
                    "error_code": "WO_CLOSED",
                    "message": f"Cannot assign {wo['status']} work order"
                }

            old_assignee = wo.get("assigned_to")
            now = datetime.now(timezone.utc).isoformat()

            # Update work order
            update_data = {
                "assigned_to": assignee_id,
                "updated_at": now
            }

            update_result = self.db.table("pms_work_orders").update(
                update_data
            ).eq("id", work_order_id).eq("yacht_id", yacht_id).execute()

            if not update_result.data:
                return {
                    "status": "error",
                    "error_code": "INTERNAL_ERROR",
                    "message": "Failed to update work order"
                }

            # Create audit log
            await self._create_audit_log(
                yacht_id=yacht_id,
                action="assign_work_order",
                entity_type="work_order",
                entity_id=work_order_id,
                user_id=user_id,
                old_values={"assigned_to": old_assignee},
                new_values={
                    "assigned_to": assignee_id,
                    "notes": notes
                }
            )

            return {
                "status": "success",
                "action": "assign_work_order",
                "result": {
                    "work_order_id": work_order_id,
                    "work_order_number": wo.get("wo_number"),
                    "assigned_to": assignee_id,
                    "previous_assignee": old_assignee
                },
                "message": f"Work order {wo.get('wo_number')} assigned"
            }

        except Exception as e:
            logger.error(f"assign_work_order_execute failed: {e}", exc_info=True)
            return {
                "status": "error",
                "error_code": "INTERNAL_ERROR",
                "message": str(e)
            }

    # =========================================================================
    # P2 #23: add_equipment_note
    # =========================================================================

    async def add_equipment_note_execute(
        self,
        equipment_id: str,
        note_text: str,
        yacht_id: str,
        user_id: str,
        note_type: str = "observation"
    ) -> Dict:
        """
        Add a note/observation about equipment.

        note_type options:
        - observation: General observation
        - condition: Condition assessment
        - maintenance: Maintenance note
        - issue: Issue reported
        """
        try:
            # Validate equipment exists
            eq_result = self.db.table("pms_equipment").select(
                "id, name, model, metadata"
            ).eq("id", equipment_id).eq("yacht_id", yacht_id).limit(1).execute()

            if not eq_result.data or len(eq_result.data) == 0:
                return {
                    "status": "error",
                    "error_code": "EQUIPMENT_NOT_FOUND",
                    "message": f"Equipment not found: {equipment_id}"
                }

            equipment = eq_result.data[0]
            now = datetime.now(timezone.utc).isoformat()
            note_id = str(uuid.uuid4())

            # Store note in equipment metadata (equipment_notes table may not exist)
            existing_metadata = equipment.get("metadata") or {}
            existing_notes = existing_metadata.get("notes") or []

            new_note = {
                "id": note_id,
                "text": note_text,
                "type": note_type,
                "created_by": user_id,
                "created_at": now
            }
            existing_notes.append(new_note)
            existing_metadata["notes"] = existing_notes

            update_result = self.db.table("pms_equipment").update({
                "metadata": existing_metadata,
                "updated_at": now
            }).eq("id", equipment_id).eq("yacht_id", yacht_id).execute()

            # Create audit log
            await self._create_audit_log(
                yacht_id=yacht_id,
                action="add_equipment_note",
                entity_type="equipment",
                entity_id=equipment_id,
                user_id=user_id,
                new_values={
                    "note_id": note_id,
                    "note_text": note_text[:100],
                    "note_type": note_type
                }
            )

            return {
                "status": "success",
                "action": "add_equipment_note",
                "result": {
                    "note": {
                        "id": note_id,
                        "equipment_id": equipment_id,
                        "note_text": note_text,
                        "note_type": note_type,
                        "created_by": user_id,
                        "created_at": now
                    },
                    "equipment_name": equipment.get("name")
                },
                "message": f"Note added to {equipment.get('name', 'equipment')}"
            }

        except Exception as e:
            logger.error(f"add_equipment_note_execute failed: {e}", exc_info=True)
            return {
                "status": "error",
                "error_code": "INTERNAL_ERROR",
                "message": str(e)
            }

    # =========================================================================
    # P2 #24: add_document_to_handover
    # =========================================================================

    async def add_document_to_handover_execute(
        self,
        handover_id: str,
        document_id: str,
        yacht_id: str,
        user_id: str,
        notes: Optional[str] = None
    ) -> Dict:
        """
        Attach a document reference to a handover item.

        Links an existing document (from doc_metadata) to a handover entry.
        """
        try:
            # Validate handover exists
            ho_result = self.db.table("pms_handover").select(
                "id, summary_text, category, metadata"
            ).eq("id", handover_id).eq("yacht_id", yacht_id).limit(1).execute()

            if not ho_result.data or len(ho_result.data) == 0:
                return {
                    "status": "error",
                    "error_code": "HANDOVER_NOT_FOUND",
                    "message": f"Handover item not found: {handover_id}"
                }

            handover = ho_result.data[0]

            # Validate document exists
            doc_result = self.db.table("doc_metadata").select(
                "id, filename, storage_path"
            ).eq("id", document_id).eq("yacht_id", yacht_id).limit(1).execute()

            if not doc_result.data or len(doc_result.data) == 0:
                return {
                    "status": "error",
                    "error_code": "DOCUMENT_NOT_FOUND",
                    "message": f"Document not found: {document_id}"
                }

            document = doc_result.data[0]
            now = datetime.now(timezone.utc).isoformat()

            # Add document to handover metadata
            existing_metadata = handover.get("metadata") or {}
            documents = existing_metadata.get("documents") or []

            doc_ref = {
                "document_id": document_id,
                "filename": document.get("filename"),
                "added_by": user_id,
                "added_at": now,
                "notes": notes
            }
            documents.append(doc_ref)
            existing_metadata["documents"] = documents

            update_result = self.db.table("pms_handover").update({
                "metadata": existing_metadata
            }).eq("id", handover_id).eq("yacht_id", yacht_id).execute()

            # Create audit log
            await self._create_audit_log(
                yacht_id=yacht_id,
                action="add_document_to_handover",
                entity_type="handover",
                entity_id=handover_id,
                user_id=user_id,
                new_values={
                    "document_id": document_id,
                    "filename": document.get("filename")
                }
            )

            return {
                "status": "success",
                "action": "add_document_to_handover",
                "result": {
                    "handover_id": handover_id,
                    "document": {
                        "id": document_id,
                        "filename": document.get("filename")
                    }
                },
                "message": f"Document attached to handover"
            }

        except Exception as e:
            logger.error(f"add_document_to_handover_execute failed: {e}", exc_info=True)
            return {
                "status": "error",
                "error_code": "INTERNAL_ERROR",
                "message": str(e)
            }

    # =========================================================================
    # P2 #26: edit_handover_section
    # =========================================================================

    async def edit_handover_section_execute(
        self,
        handover_id: str,
        summary_text: str,
        yacht_id: str,
        user_id: str,
        category: Optional[str] = None,
        priority: Optional[int] = None
    ) -> Dict:
        """
        Edit a handover section content.

        category options: urgent, in_progress, completed, watch, fyi
        priority: 0-5 (0=lowest, 5=highest)
        """
        try:
            # Validate handover exists
            ho_result = self.db.table("pms_handover").select(
                "id, summary_text, category, priority"
            ).eq("id", handover_id).eq("yacht_id", yacht_id).limit(1).execute()

            if not ho_result.data or len(ho_result.data) == 0:
                return {
                    "status": "error",
                    "error_code": "HANDOVER_NOT_FOUND",
                    "message": f"Handover item not found: {handover_id}"
                }

            handover = ho_result.data[0]
            old_values = {
                "summary_text": handover.get("summary_text"),
                "category": handover.get("category"),
                "priority": handover.get("priority")
            }

            # Build update data
            update_data = {"summary_text": summary_text}
            if category:
                valid_categories = ["urgent", "in_progress", "completed", "watch", "fyi"]
                if category in valid_categories:
                    update_data["category"] = category
            if priority is not None:
                update_data["priority"] = max(0, min(5, priority))

            update_result = self.db.table("pms_handover").update(
                update_data
            ).eq("id", handover_id).eq("yacht_id", yacht_id).execute()

            if not update_result.data:
                return {
                    "status": "error",
                    "error_code": "INTERNAL_ERROR",
                    "message": "Failed to update handover"
                }

            updated = update_result.data[0]

            # Create audit log
            await self._create_audit_log(
                yacht_id=yacht_id,
                action="edit_handover_section",
                entity_type="handover",
                entity_id=handover_id,
                user_id=user_id,
                old_values=old_values,
                new_values={
                    "summary_text": summary_text[:100],
                    "category": updated.get("category"),
                    "priority": updated.get("priority")
                }
            )

            return {
                "status": "success",
                "action": "edit_handover_section",
                "result": {
                    "handover_id": handover_id,
                    "summary_text": summary_text,
                    "category": updated.get("category"),
                    "priority": updated.get("priority")
                },
                "message": "Handover section updated"
            }

        except Exception as e:
            logger.error(f"edit_handover_section_execute failed: {e}", exc_info=True)
            return {
                "status": "error",
                "error_code": "INTERNAL_ERROR",
                "message": str(e)
            }

    # =========================================================================
    # P2 #30: update_purchase_status
    # =========================================================================

    async def update_purchase_status_execute(
        self,
        purchase_order_id: str,
        new_status: str,
        yacht_id: str,
        user_id: str,
        notes: Optional[str] = None
    ) -> Dict:
        """
        Update the status of a purchase order.

        Valid transitions:
        draft -> requested -> approved -> ordered -> partially_received -> received
        draft/requested -> cancelled
        """
        try:
            # Validate PO exists
            po_result = self.db.table("pms_purchase_orders").select(
                "id, po_number, status"
            ).eq("id", purchase_order_id).eq("yacht_id", yacht_id).limit(1).execute()

            if not po_result.data or len(po_result.data) == 0:
                return {
                    "status": "error",
                    "error_code": "PO_NOT_FOUND",
                    "message": f"Purchase order not found: {purchase_order_id}"
                }

            po = po_result.data[0]
            old_status = po.get("status")

            # Validate status
            valid_statuses = ["draft", "requested", "approved", "ordered",
                            "partially_received", "received", "cancelled"]
            if new_status not in valid_statuses:
                return {
                    "status": "error",
                    "error_code": "INVALID_STATUS",
                    "message": f"Invalid status: {new_status}"
                }

            # Validate transition
            valid_transitions = {
                "draft": ["requested", "cancelled"],
                "requested": ["approved", "cancelled"],
                "approved": ["ordered", "cancelled"],
                "ordered": ["partially_received", "received", "cancelled"],
                "partially_received": ["received", "cancelled"],
                "received": [],  # Terminal state
                "cancelled": []  # Terminal state
            }

            if new_status not in valid_transitions.get(old_status, []):
                return {
                    "status": "error",
                    "error_code": "INVALID_TRANSITION",
                    "message": f"Cannot transition from '{old_status}' to '{new_status}'"
                }

            now = datetime.now(timezone.utc).isoformat()

            # Update status
            update_result = self.db.table("pms_purchase_orders").update({
                "status": new_status,
                "updated_at": now
            }).eq("id", purchase_order_id).eq("yacht_id", yacht_id).execute()

            # Create audit log
            await self._create_audit_log(
                yacht_id=yacht_id,
                action="update_purchase_status",
                entity_type="purchase_order",
                entity_id=purchase_order_id,
                user_id=user_id,
                old_values={"status": old_status},
                new_values={
                    "status": new_status,
                    "notes": notes
                }
            )

            return {
                "status": "success",
                "action": "update_purchase_status",
                "result": {
                    "purchase_order_id": purchase_order_id,
                    "po_number": po.get("po_number"),
                    "old_status": old_status,
                    "new_status": new_status
                },
                "message": f"{po.get('po_number')} status updated to {new_status}"
            }

        except Exception as e:
            logger.error(f"update_purchase_status_execute failed: {e}", exc_info=True)
            return {
                "status": "error",
                "error_code": "INTERNAL_ERROR",
                "message": str(e)
            }

    # =========================================================================
    # P2 #31: mark_checklist_item_complete
    # =========================================================================

    async def mark_checklist_item_complete_execute(
        self,
        work_order_id: str,
        checklist_item_id: str,
        yacht_id: str,
        user_id: str,
        notes: Optional[str] = None
    ) -> Dict:
        """
        Mark a checklist item as completed.

        Checklist items are stored in work_order.metadata.checklist[] array.
        Each item has: id, title, is_completed, completed_by, completed_at, notes
        """
        try:
            # Get the work order
            wo_result = self.db.table("pms_work_orders").select(
                "id, wo_number, metadata"
            ).eq("id", work_order_id).eq("yacht_id", yacht_id).limit(1).execute()

            if not wo_result.data:
                return {
                    "status": "error",
                    "error_code": "WORK_ORDER_NOT_FOUND",
                    "message": f"Work order not found: {work_order_id}"
                }

            wo = wo_result.data[0]
            metadata = wo.get("metadata") or {}
            checklist = metadata.get("checklist") or []

            # Find the checklist item
            item_found = False
            item_title = None
            for item in checklist:
                if item.get("id") == checklist_item_id:
                    if item.get("is_completed"):
                        return {
                            "status": "error",
                            "error_code": "ALREADY_COMPLETED",
                            "message": "Checklist item is already completed"
                        }
                    item["is_completed"] = True
                    item["completed_by"] = user_id
                    item["completed_at"] = datetime.now(timezone.utc).isoformat()
                    if notes:
                        item["completion_notes"] = notes
                    item_found = True
                    item_title = item.get("title")
                    break

            if not item_found:
                return {
                    "status": "error",
                    "error_code": "CHECKLIST_ITEM_NOT_FOUND",
                    "message": f"Checklist item not found: {checklist_item_id}"
                }

            now = datetime.now(timezone.utc).isoformat()
            metadata["checklist"] = checklist

            # Update work order metadata
            self.db.table("pms_work_orders").update({
                "metadata": metadata,
                "updated_at": now
            }).eq("id", work_order_id).eq("yacht_id", yacht_id).execute()

            # Create audit log
            await self._create_audit_log(
                yacht_id=yacht_id,
                action="mark_checklist_item_complete",
                entity_type="work_order",
                entity_id=work_order_id,
                user_id=user_id,
                old_values={"is_completed": False},
                new_values={
                    "checklist_item_id": checklist_item_id,
                    "is_completed": True,
                    "notes": notes
                }
            )

            return {
                "status": "success",
                "action": "mark_checklist_item_complete",
                "result": {
                    "work_order_id": work_order_id,
                    "checklist_item_id": checklist_item_id,
                    "title": item_title,
                    "completed_at": now,
                    "completed_by": user_id
                },
                "message": f"Checklist item completed"
            }

        except Exception as e:
            logger.error(f"mark_checklist_item_complete_execute failed: {e}", exc_info=True)
            return {
                "status": "error",
                "error_code": "INTERNAL_ERROR",
                "message": str(e)
            }

    # =========================================================================
    # P2 #35: tag_for_survey
    # =========================================================================

    async def tag_for_survey_execute(
        self,
        entity_type: str,
        entity_id: str,
        survey_type: str,
        yacht_id: str,
        user_id: str,
        notes: Optional[str] = None
    ) -> Dict:
        """
        Tag an item for class/flag survey preparation.

        entity_type: equipment, fault, work_order, document
        survey_type: class, flag, insurance, internal
        """
        try:
            # Validate entity exists
            table_map = {
                "equipment": "pms_equipment",
                "fault": "pms_faults",
                "work_order": "pms_work_orders",
                "document": "doc_metadata"
            }

            if entity_type not in table_map:
                return {
                    "status": "error",
                    "error_code": "INVALID_ENTITY_TYPE",
                    "message": f"Invalid entity type: {entity_type}"
                }

            table_name = table_map[entity_type]
            entity_result = self.db.table(table_name).select(
                "id, metadata"
            ).eq("id", entity_id).eq("yacht_id", yacht_id).limit(1).execute()

            if not entity_result.data or len(entity_result.data) == 0:
                return {
                    "status": "error",
                    "error_code": "ENTITY_NOT_FOUND",
                    "message": f"{entity_type} not found: {entity_id}"
                }

            entity = entity_result.data[0]
            now = datetime.now(timezone.utc).isoformat()

            # Add survey tag to metadata
            existing_metadata = entity.get("metadata") or {}
            survey_tags = existing_metadata.get("survey_tags") or []

            new_tag = {
                "survey_type": survey_type,
                "tagged_by": user_id,
                "tagged_at": now,
                "notes": notes
            }
            survey_tags.append(new_tag)
            existing_metadata["survey_tags"] = survey_tags

            update_result = self.db.table(table_name).update({
                "metadata": existing_metadata
            }).eq("id", entity_id).eq("yacht_id", yacht_id).execute()

            # Create audit log
            await self._create_audit_log(
                yacht_id=yacht_id,
                action="tag_for_survey",
                entity_type=entity_type,
                entity_id=entity_id,
                user_id=user_id,
                new_values={
                    "survey_type": survey_type,
                    "notes": notes
                }
            )

            return {
                "status": "success",
                "action": "tag_for_survey",
                "result": {
                    "entity_type": entity_type,
                    "entity_id": entity_id,
                    "survey_type": survey_type,
                    "tagged_at": now
                },
                "message": f"Tagged for {survey_type} survey"
            }

        except Exception as e:
            logger.error(f"tag_for_survey_execute failed: {e}", exc_info=True)
            return {
                "status": "error",
                "error_code": "INTERNAL_ERROR",
                "message": str(e)
            }

    # =========================================================================
    # P2 #25: add_predictive_insight_to_handover
    # =========================================================================

    async def add_predictive_insight_to_handover_execute(
        self,
        handover_id: str,
        insight_type: str,
        insight_text: str,
        yacht_id: str,
        user_id: str,
        equipment_id: Optional[str] = None,
        confidence: Optional[float] = None,
        source: str = "manual"
    ) -> Dict:
        """
        Add a predictive maintenance insight to handover.

        insight_type: failure_prediction, maintenance_due, anomaly_detected, trend_alert
        source: manual, ml_model, sensor_data, historical_analysis
        """
        try:
            # Validate handover exists
            ho_result = self.db.table("pms_handover").select(
                "id, summary_text, metadata"
            ).eq("id", handover_id).eq("yacht_id", yacht_id).limit(1).execute()

            if not ho_result.data or len(ho_result.data) == 0:
                return {
                    "status": "error",
                    "error_code": "HANDOVER_NOT_FOUND",
                    "message": f"Handover item not found: {handover_id}"
                }

            handover = ho_result.data[0]
            now = datetime.now(timezone.utc).isoformat()
            insight_id = str(uuid.uuid4())

            # Add insight to handover metadata
            existing_metadata = handover.get("metadata") or {}
            insights = existing_metadata.get("predictive_insights") or []

            new_insight = {
                "id": insight_id,
                "type": insight_type,
                "text": insight_text,
                "equipment_id": equipment_id,
                "confidence": confidence,
                "source": source,
                "added_by": user_id,
                "added_at": now
            }
            insights.append(new_insight)
            existing_metadata["predictive_insights"] = insights

            self.db.table("pms_handover").update({
                "metadata": existing_metadata
            }).eq("id", handover_id).eq("yacht_id", yacht_id).execute()

            # Create audit log
            await self._create_audit_log(
                yacht_id=yacht_id,
                action="add_predictive_insight_to_handover",
                entity_type="handover",
                entity_id=handover_id,
                user_id=user_id,
                new_values={
                    "insight_id": insight_id,
                    "insight_type": insight_type,
                    "source": source
                }
            )

            return {
                "status": "success",
                "action": "add_predictive_insight_to_handover",
                "result": {
                    "insight": new_insight,
                    "handover_id": handover_id
                },
                "message": f"Predictive insight added to handover"
            }

        except Exception as e:
            logger.error(f"add_predictive_insight_to_handover_execute failed: {e}", exc_info=True)
            return {
                "status": "error",
                "error_code": "INTERNAL_ERROR",
                "message": str(e)
            }

    # =========================================================================
    # P2 #27: regenerate_handover_summary
    # =========================================================================

    async def regenerate_handover_summary_execute(
        self,
        handover_id: str,
        yacht_id: str,
        user_id: str,
        include_work_orders: bool = True,
        include_faults: bool = True,
        time_range_hours: int = 24
    ) -> Dict:
        """
        Regenerate handover summary from recent activity.

        This creates a new summary based on:
        - Recent work orders (completed, in_progress)
        - Active faults
        - Recent notes and updates

        Note: Full AI summarization requires LLM integration.
        This implementation aggregates data for manual review or
        external AI processing.
        """
        try:
            # Validate handover exists
            ho_result = self.db.table("pms_handover").select(
                "id, summary_text, category, entity_type, entity_id"
            ).eq("id", handover_id).eq("yacht_id", yacht_id).limit(1).execute()

            if not ho_result.data or len(ho_result.data) == 0:
                return {
                    "status": "error",
                    "error_code": "HANDOVER_NOT_FOUND",
                    "message": f"Handover item not found: {handover_id}"
                }

            handover = ho_result.data[0]
            now = datetime.now(timezone.utc)
            cutoff = (now - timedelta(hours=time_range_hours)).isoformat()

            summary_parts = []
            activity_count = 0

            # Gather recent work orders
            if include_work_orders:
                wo_result = self.db.table("pms_work_orders").select(
                    "id, wo_number, title, status, priority"
                ).eq("yacht_id", yacht_id).gte(
                    "updated_at", cutoff
                ).in_("status", ["in_progress", "completed", "planned"]).limit(10).execute()

                if wo_result.data:
                    completed = [wo for wo in wo_result.data if wo["status"] == "completed"]
                    in_progress = [wo for wo in wo_result.data if wo["status"] == "in_progress"]

                    if completed:
                        summary_parts.append(f"Completed: {len(completed)} work orders")
                        activity_count += len(completed)
                    if in_progress:
                        summary_parts.append(f"In Progress: {len(in_progress)} work orders")
                        activity_count += len(in_progress)

            # Gather active faults
            if include_faults:
                fault_result = self.db.table("pms_faults").select(
                    "id, fault_code, title, severity, status"
                ).eq("yacht_id", yacht_id).in_(
                    "status", ["open", "investigating", "in_progress"]
                ).limit(10).execute()

                if fault_result.data:
                    critical = [f for f in fault_result.data if f.get("severity") == "critical"]
                    if critical:
                        summary_parts.append(f"Critical faults: {len(critical)}")
                    summary_parts.append(f"Active faults: {len(fault_result.data)}")
                    activity_count += len(fault_result.data)

            # Build regenerated summary
            if summary_parts:
                new_summary = f"[Auto-generated {now.strftime('%Y-%m-%d %H:%M')}] " + "; ".join(summary_parts)
            else:
                new_summary = f"[Auto-generated {now.strftime('%Y-%m-%d %H:%M')}] No significant activity in last {time_range_hours}h"

            # Update handover with new summary
            old_summary = handover.get("summary_text")
            update_result = self.db.table("pms_handover").update({
                "summary_text": new_summary,
                "metadata": {
                    **(handover.get("metadata") or {}),
                    "last_regenerated": now.isoformat(),
                    "regenerated_by": user_id,
                    "previous_summary": old_summary[:200] if old_summary else None
                }
            }).eq("id", handover_id).eq("yacht_id", yacht_id).execute()

            # Create audit log
            await self._create_audit_log(
                yacht_id=yacht_id,
                action="regenerate_handover_summary",
                entity_type="handover",
                entity_id=handover_id,
                user_id=user_id,
                old_values={"summary_text": old_summary[:100] if old_summary else None},
                new_values={
                    "summary_text": new_summary[:100],
                    "activity_count": activity_count
                }
            )

            return {
                "status": "success",
                "action": "regenerate_handover_summary",
                "result": {
                    "handover_id": handover_id,
                    "new_summary": new_summary,
                    "activity_count": activity_count,
                    "time_range_hours": time_range_hours
                },
                "message": f"Handover summary regenerated ({activity_count} items)"
            }

        except Exception as e:
            logger.error(f"regenerate_handover_summary_execute failed: {e}", exc_info=True)
            return {
                "status": "error",
                "error_code": "INTERNAL_ERROR",
                "message": str(e)
            }

    # =========================================================================
    # P2 #28: add_item_to_purchase
    # =========================================================================

    async def add_item_to_purchase_execute(
        self,
        purchase_order_id: str,
        part_id: str,
        quantity: int,
        yacht_id: str,
        user_id: str,
        unit_price: Optional[float] = None,
        description: Optional[str] = None
    ) -> Dict:
        """
        Add a part/item to an existing purchase order.

        Only allowed when PO status is draft or requested.
        """
        try:
            # Validate PO exists and is editable
            po_result = self.db.table("pms_purchase_orders").select(
                "id, po_number, status"
            ).eq("id", purchase_order_id).eq("yacht_id", yacht_id).limit(1).execute()

            if not po_result.data or len(po_result.data) == 0:
                return {
                    "status": "error",
                    "error_code": "PO_NOT_FOUND",
                    "message": f"Purchase order not found: {purchase_order_id}"
                }

            po = po_result.data[0]

            # Check if PO can be edited
            if po["status"] not in ("draft", "requested"):
                return {
                    "status": "error",
                    "error_code": "PO_NOT_EDITABLE",
                    "message": f"Cannot add items to {po['status']} purchase order"
                }

            # Validate part exists
            part_result = self.db.table("pms_parts").select(
                "id, name, part_number"
            ).eq("id", part_id).eq("yacht_id", yacht_id).limit(1).execute()

            if not part_result.data or len(part_result.data) == 0:
                return {
                    "status": "error",
                    "error_code": "PART_NOT_FOUND",
                    "message": f"Part not found: {part_id}"
                }

            part = part_result.data[0]

            if quantity <= 0:
                return {
                    "status": "error",
                    "error_code": "INVALID_QUANTITY",
                    "message": "Quantity must be positive"
                }

            now = datetime.now(timezone.utc).isoformat()

            # Check if part already exists in this PO
            existing_result = self.db.table("pms_purchase_order_items").select(
                "id, quantity_ordered"
            ).eq("purchase_order_id", purchase_order_id).eq("part_id", part_id).limit(1).execute()

            if existing_result.data and len(existing_result.data) > 0:
                # Update existing line item
                existing = existing_result.data[0]
                new_qty = existing["quantity_ordered"] + quantity

                update_result = self.db.table("pms_purchase_order_items").update({
                    "quantity_ordered": new_qty,
                    "unit_price": unit_price if unit_price else None,
                    "description": description,
                    "updated_at": now
                }).eq("id", existing["id"]).execute()

                line_item = update_result.data[0] if update_result.data else existing
                action_type = "updated"
            else:
                # Create new line item
                item_data = {
                    "yacht_id": yacht_id,
                    "purchase_order_id": purchase_order_id,
                    "part_id": part_id,
                    "quantity_ordered": quantity,
                    "quantity_received": 0,
                    "unit_price": unit_price,
                    "description": description or part.get("name"),
                    "created_at": now,
                    "updated_at": now
                }

                item_result = self.db.table("pms_purchase_order_items").insert(item_data).execute()

                if not item_result.data:
                    return {
                        "status": "error",
                        "error_code": "INTERNAL_ERROR",
                        "message": "Failed to add item to purchase order"
                    }

                line_item = item_result.data[0]
                action_type = "added"

            # Create audit log
            await self._create_audit_log(
                yacht_id=yacht_id,
                action="add_item_to_purchase",
                entity_type="purchase_order",
                entity_id=purchase_order_id,
                user_id=user_id,
                new_values={
                    "line_item_id": line_item["id"],
                    "part_id": part_id,
                    "part_name": part.get("name"),
                    "quantity": quantity,
                    "action_type": action_type
                }
            )

            return {
                "status": "success",
                "action": "add_item_to_purchase",
                "result": {
                    "line_item": {
                        "id": line_item["id"],
                        "part_id": part_id,
                        "part_name": part.get("name"),
                        "part_number": part.get("part_number"),
                        "quantity_ordered": line_item.get("quantity_ordered", quantity),
                        "unit_price": unit_price
                    },
                    "purchase_order": {
                        "id": purchase_order_id,
                        "po_number": po.get("po_number")
                    },
                    "action_type": action_type
                },
                "message": f"Item {action_type} to {po.get('po_number')}"
            }

        except Exception as e:
            logger.error(f"add_item_to_purchase_execute failed: {e}", exc_info=True)
            return {
                "status": "error",
                "error_code": "INTERNAL_ERROR",
                "message": str(e)
            }

    # =========================================================================
    # P2 #29: upload_invoice
    # =========================================================================

    async def upload_invoice_execute(
        self,
        purchase_order_id: str,
        storage_path: str,
        filename: str,
        yacht_id: str,
        user_id: str,
        invoice_number: Optional[str] = None,
        invoice_date: Optional[str] = None,
        invoice_amount: Optional[float] = None,
        currency: str = "USD"
    ) -> Dict:
        """
        Attach supplier invoice to purchase order.

        Invoice file should already be uploaded to Supabase Storage.
        """
        try:
            # Validate PO exists
            po_result = self.db.table("pms_purchase_orders").select(
                "id, po_number, status, metadata"
            ).eq("id", purchase_order_id).eq("yacht_id", yacht_id).limit(1).execute()

            if not po_result.data or len(po_result.data) == 0:
                return {
                    "status": "error",
                    "error_code": "PO_NOT_FOUND",
                    "message": f"Purchase order not found: {purchase_order_id}"
                }

            po = po_result.data[0]
            now = datetime.now(timezone.utc).isoformat()

            # Create document record (using 'documents' table)
            attachment_data = {
                "yacht_id": yacht_id,
                "filename": filename,
                "content_type": "application/pdf",
                "storage_path": storage_path,
                "source": "invoice_upload",
                "doc_type": "invoice",
                "tags": [f"purchase_order:{purchase_order_id}", f"po_number:{po.get('po_number', '')}", f"invoice:{invoice_number}"],
                "metadata": {
                    "entity_type": "purchase_order",
                    "entity_id": purchase_order_id,
                    "invoice_number": invoice_number,
                    "invoice_date": invoice_date,
                    "invoice_amount": invoice_amount,
                    "currency": currency,
                    "po_number": po.get("po_number"),
                    "uploaded_by": user_id,
                    "category": "invoice"
                },
                "created_at": now
            }

            attach_result = self.db.table("documents").insert(attachment_data).execute()

            if not attach_result.data:
                return {
                    "status": "error",
                    "error_code": "INTERNAL_ERROR",
                    "message": "Failed to create attachment record"
                }

            attachment = attach_result.data[0]

            # Update PO metadata with invoice reference
            po_metadata = po.get("metadata") or {}
            invoices = po_metadata.get("invoices") or []
            invoices.append({
                "attachment_id": attachment["id"],
                "invoice_number": invoice_number,
                "invoice_date": invoice_date,
                "invoice_amount": invoice_amount,
                "currency": currency,
                "uploaded_at": now
            })
            po_metadata["invoices"] = invoices

            self.db.table("pms_purchase_orders").update({
                "metadata": po_metadata,
                "updated_at": now
            }).eq("id", purchase_order_id).eq("yacht_id", yacht_id).execute()

            # Create audit log
            await self._create_audit_log(
                yacht_id=yacht_id,
                action="upload_invoice",
                entity_type="purchase_order",
                entity_id=purchase_order_id,
                user_id=user_id,
                new_values={
                    "attachment_id": attachment["id"],
                    "invoice_number": invoice_number,
                    "invoice_amount": invoice_amount
                }
            )

            return {
                "status": "success",
                "action": "upload_invoice",
                "result": {
                    "attachment": {
                        "id": attachment["id"],
                        "filename": filename,
                        "storage_path": storage_path
                    },
                    "invoice": {
                        "number": invoice_number,
                        "date": invoice_date,
                        "amount": invoice_amount,
                        "currency": currency
                    },
                    "purchase_order": {
                        "id": purchase_order_id,
                        "po_number": po.get("po_number")
                    }
                },
                "message": f"Invoice attached to {po.get('po_number')}"
            }

        except Exception as e:
            logger.error(f"upload_invoice_execute failed: {e}", exc_info=True)
            return {
                "status": "error",
                "error_code": "INTERNAL_ERROR",
                "message": str(e)
            }

    # =========================================================================
    # P2 #32: add_checklist_note
    # =========================================================================

    async def add_checklist_note_execute(
        self,
        work_order_id: str,
        checklist_item_id: str,
        note_text: str,
        yacht_id: str,
        user_id: str
    ) -> Dict:
        """
        Add a note to a checklist item.

        Checklist items are stored in work_order.metadata.checklist[] array.
        Notes are added to the item's notes[] array within metadata.
        """
        try:
            # Get the work order
            wo_result = self.db.table("pms_work_orders").select(
                "id, wo_number, metadata"
            ).eq("id", work_order_id).eq("yacht_id", yacht_id).limit(1).execute()

            if not wo_result.data:
                return {
                    "status": "error",
                    "error_code": "WORK_ORDER_NOT_FOUND",
                    "message": f"Work order not found: {work_order_id}"
                }

            wo = wo_result.data[0]
            metadata = wo.get("metadata") or {}
            checklist = metadata.get("checklist") or []

            # Find the checklist item
            item_found = False
            item_title = None
            now = datetime.now(timezone.utc).isoformat()
            note_id = str(uuid.uuid4())

            for item in checklist:
                if item.get("id") == checklist_item_id:
                    item_notes = item.get("notes") or []
                    item_notes.append({
                        "id": note_id,
                        "text": note_text,
                        "created_by": user_id,
                        "created_at": now
                    })
                    item["notes"] = item_notes
                    item_found = True
                    item_title = item.get("title")
                    break

            if not item_found:
                return {
                    "status": "error",
                    "error_code": "CHECKLIST_ITEM_NOT_FOUND",
                    "message": f"Checklist item not found: {checklist_item_id}"
                }

            metadata["checklist"] = checklist

            # Update work order metadata
            self.db.table("pms_work_orders").update({
                "metadata": metadata,
                "updated_at": now
            }).eq("id", work_order_id).eq("yacht_id", yacht_id).execute()

            # Create audit log
            await self._create_audit_log(
                yacht_id=yacht_id,
                action="add_checklist_note",
                entity_type="work_order",
                entity_id=work_order_id,
                user_id=user_id,
                new_values={
                    "checklist_item_id": checklist_item_id,
                    "note_id": note_id,
                    "note_text": note_text[:100]
                }
            )

            return {
                "status": "success",
                "action": "add_checklist_note",
                "result": {
                    "note": {
                        "id": note_id,
                        "text": note_text,
                        "created_by": user_id,
                        "created_at": now
                    },
                    "work_order_id": work_order_id,
                    "checklist_item_id": checklist_item_id,
                    "title": item_title
                },
                "message": "Note added to checklist item"
            }

        except Exception as e:
            logger.error(f"add_checklist_note_execute failed: {e}", exc_info=True)
            return {
                "status": "error",
                "error_code": "INTERNAL_ERROR",
                "message": str(e)
            }

    # =========================================================================
    # P2 #33: add_checklist_photo
    # =========================================================================

    async def add_checklist_photo_execute(
        self,
        work_order_id: str,
        checklist_item_id: str,
        storage_path: str,
        filename: str,
        yacht_id: str,
        user_id: str,
        mime_type: str = "image/jpeg",
        description: Optional[str] = None
    ) -> Dict:
        """
        Attach a photo to a checklist item.

        Checklist items are stored in work_order.metadata.checklist[] array.
        Photo is stored in documents table, reference added to checklist item.
        """
        try:
            # Get the work order
            wo_result = self.db.table("pms_work_orders").select(
                "id, wo_number, metadata"
            ).eq("id", work_order_id).eq("yacht_id", yacht_id).limit(1).execute()

            if not wo_result.data:
                return {
                    "status": "error",
                    "error_code": "WORK_ORDER_NOT_FOUND",
                    "message": f"Work order not found: {work_order_id}"
                }

            wo = wo_result.data[0]
            metadata = wo.get("metadata") or {}
            checklist = metadata.get("checklist") or []

            # Find the checklist item
            item_found = False
            item_title = None
            for item in checklist:
                if item.get("id") == checklist_item_id:
                    item_found = True
                    item_title = item.get("title")
                    break

            if not item_found:
                return {
                    "status": "error",
                    "error_code": "CHECKLIST_ITEM_NOT_FOUND",
                    "message": f"Checklist item not found: {checklist_item_id}"
                }

            now = datetime.now(timezone.utc).isoformat()

            # Create document record
            attachment_data = {
                "yacht_id": yacht_id,
                "filename": filename,
                "content_type": mime_type,
                "storage_path": storage_path,
                "source": "checklist_photo",
                "doc_type": "photo",
                "tags": [f"work_order:{work_order_id}", f"checklist_item:{checklist_item_id}"],
                "metadata": {
                    "entity_type": "checklist_item",
                    "work_order_id": work_order_id,
                    "checklist_item_id": checklist_item_id,
                    "description": description,
                    "checklist_item_title": item_title,
                    "uploaded_by": user_id,
                    "category": "photo"
                },
                "created_at": now
            }

            attach_result = self.db.table("documents").insert(attachment_data).execute()

            if not attach_result.data:
                return {
                    "status": "error",
                    "error_code": "INTERNAL_ERROR",
                    "message": "Failed to create attachment"
                }

            attachment = attach_result.data[0]

            # Add photo reference to checklist item
            for item in checklist:
                if item.get("id") == checklist_item_id:
                    item_photos = item.get("photos") or []
                    item_photos.append({
                        "document_id": attachment["id"],
                        "filename": filename,
                        "uploaded_at": now
                    })
                    item["photos"] = item_photos
                    break

            metadata["checklist"] = checklist

            # Update work order metadata
            self.db.table("pms_work_orders").update({
                "metadata": metadata,
                "updated_at": now
            }).eq("id", work_order_id).eq("yacht_id", yacht_id).execute()

            # Create audit log
            await self._create_audit_log(
                yacht_id=yacht_id,
                action="add_checklist_photo",
                entity_type="work_order",
                entity_id=work_order_id,
                user_id=user_id,
                new_values={
                    "checklist_item_id": checklist_item_id,
                    "attachment_id": attachment["id"],
                    "filename": filename
                }
            )

            return {
                "status": "success",
                "action": "add_checklist_photo",
                "result": {
                    "attachment": {
                        "id": attachment["id"],
                        "filename": filename,
                        "storage_path": storage_path
                    },
                    "work_order_id": work_order_id,
                    "checklist_item_id": checklist_item_id,
                    "title": item_title
                },
                "message": "Photo attached to checklist item"
            }

        except Exception as e:
            logger.error(f"add_checklist_photo_execute failed: {e}", exc_info=True)
            return {
                "status": "error",
                "error_code": "INTERNAL_ERROR",
                "message": str(e)
            }

    # =========================================================================
    # P2 #34: update_worklist_progress
    # =========================================================================

    async def update_worklist_progress_execute(
        self,
        work_order_id: str,
        progress_percent: int,
        yacht_id: str,
        user_id: str,
        status_note: Optional[str] = None
    ) -> Dict:
        """
        Update completion progress of a worklist task.

        Uses work_order_type='task' work orders as worklist items.
        progress_percent: 0-100
        """
        try:
            # Validate work order exists and is a task
            wo_result = self.db.table("pms_work_orders").select(
                "id, wo_number, title, status, work_order_type, metadata"
            ).eq("id", work_order_id).eq("yacht_id", yacht_id).limit(1).execute()

            if not wo_result.data or len(wo_result.data) == 0:
                return {
                    "status": "error",
                    "error_code": "WO_NOT_FOUND",
                    "message": f"Work order not found: {work_order_id}"
                }

            wo = wo_result.data[0]

            if wo["status"] in ("completed", "closed", "cancelled"):
                return {
                    "status": "error",
                    "error_code": "WO_CLOSED",
                    "message": f"Cannot update progress on {wo['status']} work order"
                }

            # Validate progress
            progress_percent = max(0, min(100, progress_percent))

            now = datetime.now(timezone.utc).isoformat()
            old_metadata = wo.get("metadata") or {}
            old_progress = old_metadata.get("progress_percent", 0)

            # Update progress in metadata
            new_metadata = {
                **old_metadata,
                "progress_percent": progress_percent,
                "progress_updated_at": now,
                "progress_updated_by": user_id
            }

            if status_note:
                progress_notes = new_metadata.get("progress_notes") or []
                progress_notes.append({
                    "note": status_note,
                    "progress": progress_percent,
                    "created_by": user_id,
                    "created_at": now
                })
                new_metadata["progress_notes"] = progress_notes

            # Auto-complete if 100%
            update_data = {
                "metadata": new_metadata,
                "updated_at": now
            }

            if progress_percent == 100 and wo["status"] != "completed":
                update_data["status"] = "completed"
                update_data["completed_at"] = now
                update_data["completed_by"] = user_id

            self.db.table("pms_work_orders").update(update_data).eq(
                "id", work_order_id
            ).eq("yacht_id", yacht_id).execute()

            # Create audit log
            await self._create_audit_log(
                yacht_id=yacht_id,
                action="update_worklist_progress",
                entity_type="work_order",
                entity_id=work_order_id,
                user_id=user_id,
                old_values={"progress_percent": old_progress},
                new_values={
                    "progress_percent": progress_percent,
                    "status_note": status_note
                }
            )

            return {
                "status": "success",
                "action": "update_worklist_progress",
                "result": {
                    "work_order_id": work_order_id,
                    "wo_number": wo.get("wo_number"),
                    "title": wo.get("title"),
                    "old_progress": old_progress,
                    "new_progress": progress_percent,
                    "auto_completed": progress_percent == 100
                },
                "message": f"Progress updated to {progress_percent}%"
            }

        except Exception as e:
            logger.error(f"update_worklist_progress_execute failed: {e}", exc_info=True)
            return {
                "status": "error",
                "error_code": "INTERNAL_ERROR",
                "message": str(e)
            }

    # =========================================================================
    # P2 #36: upload_photo (Generic)
    # =========================================================================

    async def upload_photo_execute(
        self,
        entity_type: str,
        entity_id: str,
        storage_path: str,
        filename: str,
        yacht_id: str,
        user_id: str,
        mime_type: str = "image/jpeg",
        category: str = "photo",
        description: Optional[str] = None
    ) -> Dict:
        """
        Generic photo upload to any entity.

        entity_type: work_order, fault, equipment, handover, checklist_item
        """
        try:
            # Validate entity_type
            valid_types = ["work_order", "fault", "equipment", "handover", "checklist_item"]
            if entity_type not in valid_types:
                return {
                    "status": "error",
                    "error_code": "INVALID_ENTITY_TYPE",
                    "message": f"Invalid entity type: {entity_type}. Must be one of: {valid_types}"
                }

            now = datetime.now(timezone.utc).isoformat()

            # Create document record (using 'documents' table)
            attachment_data = {
                "yacht_id": yacht_id,
                "filename": filename,
                "content_type": mime_type,
                "storage_path": storage_path,
                "source": f"{entity_type}_photo",
                "doc_type": category,
                "tags": [f"{entity_type}:{entity_id}"],
                "metadata": {
                    "entity_type": entity_type,
                    "entity_id": entity_id,
                    "description": description,
                    "uploaded_by": user_id,
                    "category": category
                },
                "created_at": now
            }

            attach_result = self.db.table("documents").insert(attachment_data).execute()

            if not attach_result.data:
                return {
                    "status": "error",
                    "error_code": "INTERNAL_ERROR",
                    "message": "Failed to create attachment"
                }

            attachment = attach_result.data[0]

            # Create audit log
            await self._create_audit_log(
                yacht_id=yacht_id,
                action="upload_photo",
                entity_type=entity_type,
                entity_id=entity_id,
                user_id=user_id,
                new_values={
                    "attachment_id": attachment["id"],
                    "filename": filename,
                    "category": category
                }
            )

            return {
                "status": "success",
                "action": "upload_photo",
                "result": {
                    "attachment": {
                        "id": attachment["id"],
                        "filename": filename,
                        "storage_path": storage_path,
                        "category": category
                    },
                    "entity_type": entity_type,
                    "entity_id": entity_id
                },
                "message": f"Photo uploaded to {entity_type}"
            }

        except Exception as e:
            logger.error(f"upload_photo_execute failed: {e}", exc_info=True)
            return {
                "status": "error",
                "error_code": "INTERNAL_ERROR",
                "message": str(e)
            }

    # =========================================================================
    # P2 #37: record_voice_note
    # =========================================================================

    async def record_voice_note_execute(
        self,
        entity_type: str,
        entity_id: str,
        storage_path: str,
        filename: str,
        yacht_id: str,
        user_id: str,
        duration_seconds: Optional[int] = None,
        transcription: Optional[str] = None
    ) -> Dict:
        """
        Record and attach a voice note to an entity.

        Audio file should already be uploaded to Supabase Storage.
        Transcription can be provided externally or processed later.

        entity_type: work_order, fault, equipment, handover
        """
        try:
            valid_types = ["work_order", "fault", "equipment", "handover"]
            if entity_type not in valid_types:
                return {
                    "status": "error",
                    "error_code": "INVALID_ENTITY_TYPE",
                    "message": f"Invalid entity type: {entity_type}"
                }

            now = datetime.now(timezone.utc).isoformat()

            # Create document record for voice note (using 'documents' table)
            attachment_data = {
                "yacht_id": yacht_id,
                "filename": filename,
                "content_type": "audio/webm",  # Common web audio format
                "storage_path": storage_path,
                "source": "voice_note",
                "doc_type": "voice_note",
                "tags": [f"{entity_type}:{entity_id}", "audio"],
                "metadata": {
                    "entity_type": entity_type,
                    "entity_id": entity_id,
                    "duration_seconds": duration_seconds,
                    "transcription": transcription,
                    "transcription_status": "provided" if transcription else "pending",
                    "uploaded_by": user_id,
                    "category": "voice_note"
                },
                "created_at": now
            }

            attach_result = self.db.table("documents").insert(attachment_data).execute()

            if not attach_result.data:
                return {
                    "status": "error",
                    "error_code": "INTERNAL_ERROR",
                    "message": "Failed to create attachment"
                }

            attachment = attach_result.data[0]

            # Create audit log
            await self._create_audit_log(
                yacht_id=yacht_id,
                action="record_voice_note",
                entity_type=entity_type,
                entity_id=entity_id,
                user_id=user_id,
                new_values={
                    "attachment_id": attachment["id"],
                    "duration_seconds": duration_seconds,
                    "has_transcription": bool(transcription)
                }
            )

            return {
                "status": "success",
                "action": "record_voice_note",
                "result": {
                    "attachment": {
                        "id": attachment["id"],
                        "filename": filename,
                        "storage_path": storage_path,
                        "duration_seconds": duration_seconds
                    },
                    "transcription": transcription,
                    "transcription_status": "provided" if transcription else "pending",
                    "entity_type": entity_type,
                    "entity_id": entity_id
                },
                "message": f"Voice note recorded ({duration_seconds}s)" if duration_seconds else "Voice note recorded"
            }

        except Exception as e:
            logger.error(f"record_voice_note_execute failed: {e}", exc_info=True)
            return {
                "status": "error",
                "error_code": "INTERNAL_ERROR",
                "message": str(e)
            }

    # =========================================================================
    # HELPER METHODS
    # =========================================================================

    async def _create_audit_log(
        self,
        yacht_id: str,
        action: str,
        entity_type: str,
        entity_id: str,
        user_id: str,
        old_values: Optional[Dict] = None,
        new_values: Optional[Dict] = None
    ) -> Optional[str]:
        """Create audit log entry for P2 actions."""
        try:
            audit_data = {
                "yacht_id": yacht_id,
                "action": action,
                "entity_type": entity_type,
                "entity_id": entity_id,
                "user_id": user_id,
                "old_values": old_values,
                "new_values": new_values,
                "signature": {
                    "user_id": user_id,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "source": "p2_mutation_light"
                },
                "created_at": datetime.now(timezone.utc).isoformat()
            }

            result = self.db.table("pms_audit_log").insert(audit_data).execute()
            return result.data[0]["id"] if result.data else None

        except Exception as e:
            logger.warning(f"Audit log creation failed: {e}")
            return None


def get_p2_mutation_light_handlers(supabase_client) -> Dict[str, callable]:
    """Get P2 mutation light handler functions for registration."""
    handlers = P2MutationLightHandlers(supabase_client)

    return {
        # #17 add_fault_note
        "add_fault_note": handlers.add_fault_note_execute,

        # #18 add_fault_photo
        "add_fault_photo": handlers.add_fault_photo_execute,

        # #19 add_work_order_note
        "add_work_order_note": handlers.add_work_order_note_execute,

        # #20 add_work_order_photo
        "add_work_order_photo": handlers.add_work_order_photo_execute,

        # #22 assign_work_order
        "assign_work_order": handlers.assign_work_order_execute,

        # #23 add_equipment_note
        "add_equipment_note": handlers.add_equipment_note_execute,

        # #24 add_document_to_handover
        "add_document_to_handover": handlers.add_document_to_handover_execute,

        # #25 add_predictive_insight_to_handover
        "add_predictive_insight_to_handover": handlers.add_predictive_insight_to_handover_execute,

        # #26 edit_handover_section
        "edit_handover_section": handlers.edit_handover_section_execute,

        # #27 regenerate_handover_summary
        "regenerate_handover_summary": handlers.regenerate_handover_summary_execute,

        # #28 add_item_to_purchase
        "add_item_to_purchase": handlers.add_item_to_purchase_execute,

        # #29 upload_invoice
        "upload_invoice": handlers.upload_invoice_execute,

        # #30 update_purchase_status
        "update_purchase_status": handlers.update_purchase_status_execute,

        # #31 mark_checklist_item_complete
        "mark_checklist_item_complete": handlers.mark_checklist_item_complete_execute,

        # #32 add_checklist_note
        "add_checklist_note": handlers.add_checklist_note_execute,

        # #33 add_checklist_photo
        "add_checklist_photo": handlers.add_checklist_photo_execute,

        # #34 update_worklist_progress
        "update_worklist_progress": handlers.update_worklist_progress_execute,

        # #35 tag_for_survey
        "tag_for_survey": handlers.tag_for_survey_execute,

        # #36 upload_photo
        "upload_photo": handlers.upload_photo_execute,

        # #37 record_voice_note
        "record_voice_note": handlers.record_voice_note_execute,
    }
