"""
Equipment Domain Handlers
=========================

Group 1: READ handlers for equipment-related actions.

Handlers:
- view_equipment: Equipment details with manual files
- view_maintenance_history: Work order history
- view_equipment_parts: Parts associated with equipment
- view_linked_faults: Faults for equipment
- view_equipment_manual: Manual sections with PDF files

All handlers return standardized ActionResponseEnvelope.
"""

from datetime import datetime, timezone
from typing import Dict, Optional, List
import logging

# Import schema components
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from actions.action_response_schema import (
    ResponseBuilder,
    FileReference,
    FileType,
    AvailableAction,
    SignedUrlGenerator,
    get_available_actions_for_entity
)

# Import Equipment Lens v2 utilities
from handlers.equipment_utils import (
    validate_storage_path_for_equipment,
    extract_audit_metadata,
    validate_status_transition,
    validate_work_order_for_oos,
    is_prepare_mode,
    is_execute_mode,
    generate_confirmation_token,
    VALID_EQUIPMENT_STATUSES,
    OOS_STATUS,
)

from .schema_mapping import (
    get_table,
    map_equipment_select,
    map_work_order_select,
    map_parts_select,
    map_faults_select,
    normalize_equipment,
    normalize_work_order,
    normalize_part,
    normalize_fault
)

logger = logging.getLogger(__name__)


class EquipmentHandlers:
    """
    Equipment domain READ handlers.

    All methods return Dict in standardized envelope format.
    """

    def __init__(self, supabase_client):
        self.db = supabase_client
        self.url_generator = SignedUrlGenerator(supabase_client) if supabase_client else None

    async def view_equipment(
        self,
        entity_id: str,
        yacht_id: str,
        params: Optional[Dict] = None
    ) -> Dict:
        """
        View equipment details.

        Returns:
        - Equipment data (id, label, manufacturer, model, status, etc.)
        - Associated manual files (if any)
        - Available actions for this equipment
        """
        builder = ResponseBuilder("view_equipment", entity_id, "equipment", yacht_id)

        try:
            # Query equipment using actual schema columns
            result = self.db.table(get_table("equipment")).select(
                map_equipment_select()
            ).eq("yacht_id", yacht_id).eq("id", entity_id).maybe_single().execute()

            if not result or not result.data:
                builder.set_error("NOT_FOUND", f"Equipment not found: {entity_id}")
                return builder.build()

            # Normalize to handler expected format
            equipment = normalize_equipment(result.data)

            # Add computed fields
            equipment["risk_score"] = await self._get_risk_score(entity_id)

            builder.set_data(equipment)

            # Get associated manual files
            files = await self._get_equipment_files(entity_id, yacht_id)
            if files:
                builder.add_files(files)

            # Add available actions
            actions = self._get_equipment_actions(entity_id)
            builder.add_available_actions(actions)

            return builder.build()

        except Exception as e:
            logger.error(f"view_equipment failed: {e}", exc_info=True)
            builder.set_error("INTERNAL_ERROR", str(e))
            return builder.build()

    async def view_maintenance_history(
        self,
        entity_id: str,
        yacht_id: str,
        params: Optional[Dict] = None
    ) -> Dict:
        """
        View maintenance/work order history for equipment.

        Returns:
        - List of work orders for this equipment
        - Pagination info
        """
        builder = ResponseBuilder("view_maintenance_history", entity_id, "equipment", yacht_id)

        try:
            # Get pagination params
            offset = (params or {}).get("offset", 0)
            limit = (params or {}).get("limit", 20)

            # Query work orders for this equipment using actual table
            result = self.db.table(get_table("work_orders")).select(
                map_work_order_select(),
                count="exact"
            ).eq("yacht_id", yacht_id).eq(
                "equipment_id", entity_id
            ).order("created_at", desc=True).range(offset, offset + limit - 1).execute()

            # Normalize each work order
            work_orders = [normalize_work_order(wo) for wo in (result.data or [])]
            total_count = result.count or len(work_orders)

            # Build list data structure
            builder.set_data({
                "equipment_id": entity_id,
                "work_orders": work_orders,
                "summary": {
                    "total": total_count,
                    "open": len([wo for wo in work_orders if wo.get("status") in ("open", "in_progress", "pending")]),
                    "completed": len([wo for wo in work_orders if wo.get("status") in ("completed", "closed")])
                }
            })

            builder.set_pagination(offset, limit, total_count)

            # Add actions
            builder.add_available_action(AvailableAction(
                action_id="create_work_order",
                label="Create Work Order",
                variant="MUTATE",
                icon="plus",
                requires_signature=True,
                confirmation_message="Create new work order for this equipment?"
            ))

            return builder.build()

        except Exception as e:
            logger.error(f"view_maintenance_history failed: {e}", exc_info=True)
            builder.set_error("INTERNAL_ERROR", str(e))
            return builder.build()

    async def view_equipment_parts(
        self,
        entity_id: str,
        yacht_id: str,
        params: Optional[Dict] = None
    ) -> Dict:
        """
        View parts associated with equipment.

        Returns:
        - List of parts used by/for this equipment
        - Stock status for each part
        """
        builder = ResponseBuilder("view_equipment_parts", entity_id, "equipment", yacht_id)

        try:
            # Query parts - pms_parts doesn't have equipment_id
            # Instead search by model_compatibility or get all parts for yacht
            result = self.db.table(get_table("parts")).select(
                map_parts_select()
            ).eq("yacht_id", yacht_id).limit(50).execute()

            # Normalize parts
            parts = [normalize_part(p) for p in (result.data or [])]

            # Add stock status to each part (defaults since not in current schema)
            for part in parts:
                part["stock_status"] = self._compute_stock_status(part)
                part["is_low_stock"] = part["stock_status"] in ("LOW_STOCK", "OUT_OF_STOCK")

            # Build response
            builder.set_data({
                "equipment_id": entity_id,
                "parts": parts,
                "summary": {
                    "total": len(parts),
                    "low_stock": len([p for p in parts if p.get("is_low_stock")]),
                    "in_stock": len([p for p in parts if p.get("stock_status") == "IN_STOCK"])
                }
            })

            # Add actions
            builder.add_available_action(AvailableAction(
                action_id="view_inventory_item",
                label="View Part Details",
                variant="READ",
                icon="eye"
            ))
            builder.add_available_action(AvailableAction(
                action_id="create_reorder",
                label="Create Reorder",
                variant="MUTATE",
                icon="cart",
                requires_signature=True
            ))

            return builder.build()

        except Exception as e:
            logger.error(f"view_equipment_parts failed: {e}", exc_info=True)
            builder.set_error("INTERNAL_ERROR", str(e))
            return builder.build()

    async def view_linked_faults(
        self,
        entity_id: str,
        yacht_id: str,
        params: Optional[Dict] = None
    ) -> Dict:
        """
        View faults linked to equipment.

        Returns:
        - List of faults for this equipment
        - Severity breakdown
        """
        builder = ResponseBuilder("view_linked_faults", entity_id, "equipment", yacht_id)

        try:
            # Get pagination params
            offset = (params or {}).get("offset", 0)
            limit = (params or {}).get("limit", 20)

            # Query faults for this equipment using actual table
            result = self.db.table(get_table("faults")).select(
                map_faults_select(),
                count="exact"
            ).eq("yacht_id", yacht_id).eq(
                "equipment_id", entity_id
            ).order("created_at", desc=True).range(offset, offset + limit - 1).execute()

            # Normalize faults
            faults = [normalize_fault(f) for f in (result.data or [])]
            total_count = result.count or len(faults)

            # Compute days open for each fault
            for fault in faults:
                fault["is_active"] = not fault.get("is_resolved", False)
                if fault["is_active"] and fault.get("created_at"):
                    try:
                        reported = datetime.fromisoformat(fault["created_at"].replace("Z", "+00:00"))
                        fault["days_open"] = (datetime.now(timezone.utc) - reported).days
                    except:
                        fault["days_open"] = 0
                else:
                    fault["days_open"] = 0

            builder.set_data({
                "equipment_id": entity_id,
                "faults": faults,
                "summary": {
                    "total": total_count,
                    "active": len([f for f in faults if f.get("is_active")]),
                    "critical": len([f for f in faults if f.get("severity") == "critical"]),
                    "high": len([f for f in faults if f.get("severity") == "high"])
                }
            })

            builder.set_pagination(offset, limit, total_count)

            # Add actions
            builder.add_available_action(AvailableAction(
                action_id="view_fault",
                label="View Fault Details",
                variant="READ",
                icon="alert"
            ))
            builder.add_available_action(AvailableAction(
                action_id="report_fault",
                label="Report New Fault",
                variant="MUTATE",
                icon="alert-circle",
                requires_signature=True
            ))

            return builder.build()

        except Exception as e:
            logger.error(f"view_linked_faults failed: {e}", exc_info=True)
            builder.set_error("INTERNAL_ERROR", str(e))
            return builder.build()

    async def view_equipment_manual(
        self,
        entity_id: str,
        yacht_id: str,
        params: Optional[Dict] = None
    ) -> Dict:
        """
        Find manual sections for equipment.

        Returns:
        - Document chunks mentioning this equipment
        - Signed URLs for PDF files
        """
        builder = ResponseBuilder("view_equipment_manual", entity_id, "equipment", yacht_id)

        try:
            # First get equipment name using actual schema
            eq_result = self.db.table(get_table("equipment")).select(
                "name"
            ).eq("id", entity_id).maybe_single().execute()

            if not eq_result.data:
                builder.set_error("NOT_FOUND", f"Equipment not found: {entity_id}")
                return builder.build()

            label = eq_result.data["name"]

            # Search document chunks for this equipment (no FK join available)
            chunks_result = self.db.table("document_chunks").select(
                "id, document_id, section_title, page_number, content"
            ).eq("yacht_id", yacht_id).ilike(
                "content", f"%{label}%"
            ).limit(10).execute()

            chunks = chunks_result.data or []

            # Get document IDs and fetch document info separately
            doc_ids = list(set(c.get("document_id") for c in chunks if c.get("document_id")))

            # Fetch documents
            docs_map = {}
            if doc_ids:
                docs_result = self.db.table("documents").select(
                    "id, filename, storage_path, content_type"
                ).in_("id", doc_ids).execute()

                for doc in (docs_result.data or []):
                    docs_map[doc["id"]] = doc

            # Generate signed URLs for documents
            files = []
            seen_docs = set()

            for chunk in chunks:
                doc_id = chunk.get("document_id")
                if doc_id and doc_id not in seen_docs:
                    seen_docs.add(doc_id)
                    doc = docs_map.get(doc_id, {})

                    # Create signed URL
                    if self.url_generator and doc.get("storage_path"):
                        file_ref = self.url_generator.create_file_reference(
                            bucket="documents",
                            path=doc["storage_path"],
                            filename=doc.get("filename", "document.pdf"),
                            file_id=doc_id,
                            display_name=doc.get("filename"),
                            mime_type=doc.get("content_type", "application/pdf"),
                            expires_in_minutes=30
                        )
                        if file_ref:
                            files.append(file_ref.to_dict())

            builder.set_data({
                "equipment_id": entity_id,
                "equipment_label": label,
                "manual_sections": [
                    {
                        "chunk_id": c["id"],
                        "document_id": c.get("document_id"),
                        "section_title": c.get("section_title"),
                        "page_number": c.get("page_number"),
                        "content_preview": c.get("content", "")[:200] + "..." if c.get("content") else ""
                    }
                    for c in chunks
                ],
                "document_count": len(seen_docs)
            })

            if files:
                builder.add_files(files)

            # Add actions
            builder.add_available_action(AvailableAction(
                action_id="view_manual_section",
                label="Open Manual",
                variant="READ",
                icon="book",
                is_primary=True
            ))
            builder.add_available_action(AvailableAction(
                action_id="view_related_docs",
                label="Related Documents",
                variant="READ",
                icon="link"
            ))

            return builder.build()

        except Exception as e:
            logger.error(f"view_equipment_manual failed: {e}", exc_info=True)
            builder.set_error("INTERNAL_ERROR", str(e))
            return builder.build()

    # =========================================================================
    # HELPER METHODS
    # =========================================================================

    async def _get_risk_score(self, equipment_id: str) -> float:
        """Get risk score from predictive_state table"""
        try:
            result = self.db.table("predictive_state").select(
                "risk_score"
            ).eq("equipment_id", equipment_id).maybe_single().execute()

            if result.data:
                return result.data.get("risk_score", 0.0)
        except Exception:
            pass
        return 0.0

    def _get_bucket_for_attachment(self, entity_type: str, category: str, mime_type: str) -> str:
        """
        Determine storage bucket based on entity type.

        CRITICAL: Table name is pms_attachments (NOT attachments).

        Entity-based bucket strategy (created 2026-01-30):
        - work_order → pms-work-order-attachments
        - fault → pms-fault-attachments
        - equipment → pms-equipment-attachments
        - checklist_item → pms-checklist-attachments

        Legacy buckets maintained for backwards compatibility:
        - pms-work-order-photos (read-only, old photos)
        - documents (NAS manuals, separate system)
        """
        category = (category or "").lower()
        mime_type = (mime_type or "").lower()

        # Entity-based buckets (NEW - 2026-01-30)
        if entity_type == "work_order":
            return "pms-work-order-attachments"
        elif entity_type == "fault":
            return "pms-fault-attachments"
        elif entity_type == "equipment":
            return "pms-equipment-attachments"
        elif entity_type == "checklist_item":
            return "pms-checklist-attachments"

        # Legacy fallback for old attachments
        # Check old pms-work-order-photos bucket first
        if entity_type in ("work_order", "fault", "equipment"):
            if category in ("photo", "image") or mime_type.startswith("image/"):
                return "pms-work-order-photos"

        # NAS documents bucket (separate system)
        if category in ("manual", "document") and mime_type == "application/pdf":
            return "documents"

        # Default: generic attachments bucket
        return "attachments"

    async def _get_equipment_files(
        self,
        equipment_id: str,
        yacht_id: str
    ) -> List[Dict]:
        """Get files associated with equipment (photos, manuals, etc.)"""
        files = []

        if not self.url_generator:
            return files

        try:
            # CRITICAL: Use pms_attachments (NOT attachments) - see soft delete migration
            result = self.db.table("pms_attachments").select(
                "id, filename, mime_type, storage_path, category"
            ).eq("entity_type", "equipment").eq("entity_id", equipment_id).is_(
                "deleted_at", "null"  # Soft delete filter required
            ).execute()

            for att in (result.data or []):
                # Determine bucket based on entity type and category
                bucket = self._get_bucket_for_attachment(
                    entity_type="equipment",
                    category=att.get("category"),
                    mime_type=att.get("mime_type")
                )

                file_ref = self.url_generator.create_file_reference(
                    bucket=bucket,
                    path=att.get("storage_path", ""),
                    filename=att.get("filename", "file"),
                    file_id=att["id"],
                    mime_type=att.get("mime_type"),
                    expires_in_minutes=30
                )
                if file_ref:
                    files.append(file_ref.to_dict())

        except Exception as e:
            logger.warning(f"Failed to get equipment files: {e}")

        return files

    def _compute_stock_status(self, part: Dict) -> str:
        """Compute stock status for a part"""
        qty = part.get("quantity", 0) or 0
        min_qty = part.get("min_quantity", 0) or 0
        max_qty = part.get("max_quantity", float("inf")) or float("inf")

        if qty <= 0:
            return "OUT_OF_STOCK"
        elif qty <= min_qty:
            return "LOW_STOCK"
        elif max_qty and qty >= max_qty:
            return "OVERSTOCKED"
        else:
            return "IN_STOCK"

    def _get_equipment_actions(self, equipment_id: str) -> List[AvailableAction]:
        """Get available actions for equipment entity"""
        return [
            AvailableAction(
                action_id="view_maintenance_history",
                label="Maintenance History",
                variant="READ",
                icon="history"
            ),
            AvailableAction(
                action_id="view_equipment_parts",
                label="View Parts",
                variant="READ",
                icon="package"
            ),
            AvailableAction(
                action_id="view_linked_faults",
                label="View Faults",
                variant="READ",
                icon="alert"
            ),
            AvailableAction(
                action_id="view_equipment_manual",
                label="Open Manual",
                variant="READ",
                icon="book"
            ),
            AvailableAction(
                action_id="run_diagnostic",
                label="Run Diagnostic",
                variant="READ",
                icon="search"
            ),
            AvailableAction(
                action_id="create_work_order",
                label="Create Work Order",
                variant="MUTATE",
                icon="plus",
                requires_signature=True,
                confirmation_message="Create work order for this equipment?"
            ),
            AvailableAction(
                action_id="report_fault",
                label="Report Fault",
                variant="MUTATE",
                icon="alert-circle",
                requires_signature=True
            ),
            AvailableAction(
                action_id="add_equipment_note",
                label="Add Note",
                variant="MUTATE",
                icon="message"
            )
        ]


# =============================================================================
# HANDLER REGISTRATION
# =============================================================================

def get_equipment_handlers(supabase_client) -> Dict[str, callable]:
    """
    Get equipment handler functions for registration with ActionExecutor.

    Returns dict mapping action_id to async handler function.
    """
    handlers = EquipmentHandlers(supabase_client)

    return {
        # READ handlers
        "view_equipment": handlers.view_equipment,
        "view_maintenance_history": handlers.view_maintenance_history,
        "view_equipment_parts": handlers.view_equipment_parts,
        "view_linked_faults": handlers.view_linked_faults,
        "view_equipment_manual": handlers.view_equipment_manual,
        # MUTATION handlers (v2)
        "update_equipment_status": _update_equipment_status_adapter(handlers),
        "add_equipment_note": _add_equipment_note_adapter(handlers),
        "attach_file_to_equipment": _attach_file_to_equipment_adapter(handlers),
        "create_work_order_for_equipment": _create_work_order_for_equipment_adapter(handlers),
        "link_part_to_equipment": _link_part_to_equipment_adapter(handlers),
        "flag_equipment_attention": _flag_equipment_attention_adapter(handlers),
        "decommission_equipment": _decommission_equipment_adapter(handlers),
        "record_equipment_hours": _record_equipment_hours_adapter(handlers),
        # Additional Equipment Lens v2 handlers (Phase A)
        "create_equipment": _create_equipment_adapter(handlers),
        "assign_parent_equipment": _assign_parent_equipment_adapter(handlers),
        "archive_equipment": _archive_equipment_adapter(handlers),
        "restore_archived_equipment": _restore_archived_equipment_adapter(handlers),
        "get_open_faults_for_equipment": _get_open_faults_for_equipment_adapter(handlers),
        "get_related_entities_for_equipment": _get_related_entities_for_equipment_adapter(handlers),
        "add_entity_link": _add_entity_link_adapter(handlers),
        "link_document_to_equipment": _link_document_to_equipment_adapter(handlers),
        # Equipment Lens v2 - Additional handlers (spec completion)
        "set_equipment_status": _update_equipment_status_adapter(handlers),  # OOS→WO enforcement
        "attach_image_with_comment": _attach_image_with_comment_adapter(handlers),
        "decommission_and_replace_equipment": _decommission_and_replace_equipment_adapter(handlers),
    }


# =============================================================================
# MUTATION ADAPTERS - Equipment Lens v2
# =============================================================================

def _update_equipment_status_adapter(handlers: EquipmentHandlers):
    """
    Update equipment status (set_equipment_status).

    Required fields: equipment_id, status
    Optional fields: attention_reason, clear_attention, linked_work_order_id
    Allowed roles: engineer, eto, chief_engineer, chief_officer, captain, purser, manager

    CRITICAL: out_of_service status requires linked_work_order_id with OPEN WO.
    """
    async def _fn(**params):
        db = handlers.db
        yacht_id = params["yacht_id"]
        user_id = params["user_id"]
        equipment_id = params["equipment_id"]
        new_status = params["status"]
        attention_reason = params.get("attention_reason")
        clear_attention = params.get("clear_attention", False)
        linked_work_order_id = params.get("linked_work_order_id")
        request_context = params.get("request_context")

        # Get current equipment
        eq_result = db.table("pms_equipment").select(
            "id, name, status, yacht_id"
        ).eq("id", equipment_id).eq("yacht_id", yacht_id).maybe_single().execute()

        if not eq_result.data:
            return {
                "status": "error",
                "error_code": "NOT_FOUND",
                "message": "Equipment not found"
            }

        old_status = eq_result.data.get("status")

        # Validate status transition
        is_valid, error_msg = validate_status_transition(
            old_status,
            new_status,
            linked_work_order_id
        )

        if not is_valid:
            return {
                "status": "error",
                "error_code": "INVALID_STATUS_TRANSITION",
                "message": error_msg
            }

        # If OOS, validate the work order
        if new_status == OOS_STATUS:
            wo_valid, wo_error = validate_work_order_for_oos(
                db,
                linked_work_order_id,
                equipment_id,
                yacht_id
            )
            if not wo_valid:
                return {
                    "status": "error",
                    "error_code": "INVALID_WORK_ORDER",
                    "message": wo_error
                }

        # Build update payload
        update_payload = {
            "status": new_status,
            "updated_by": user_id,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

        # Handle attention flag
        if new_status in ('failed', 'degraded') and attention_reason:
            update_payload["attention_flag"] = True
            update_payload["attention_reason"] = attention_reason
        elif clear_attention or new_status == 'operational':
            update_payload["attention_flag"] = False
            update_payload["attention_reason"] = None

        # Update equipment (trigger will log status change)
        db.table("pms_equipment").update(update_payload).eq(
            "id", equipment_id
        ).execute()

        # Extract audit metadata
        audit_meta = extract_audit_metadata(request_context)

        # Audit log with metadata
        _write_audit_log(db, {
            "yacht_id": yacht_id,
            "entity_type": "equipment",
            "entity_id": equipment_id,
            "action": "set_equipment_status",
            "user_id": user_id,
            "old_values": {"status": old_status},
            "new_values": {
                "status": new_status,
                "attention_reason": attention_reason,
                "work_order_id": linked_work_order_id
            },
            "signature": {},  # Non-signed action
            **audit_meta,  # session_id, ip_address, source, lens
        })

        return {
            "status": "success",
            "equipment_id": equipment_id,
            "old_status": old_status,
            "new_status": new_status,
            "work_order_id": linked_work_order_id,
        }

    return _fn


def _add_equipment_note_adapter(handlers: EquipmentHandlers):
    """
    Add a note to equipment.

    Required fields: equipment_id, text
    Optional fields: note_type, requires_ack
    Allowed roles: all crew
    """
    async def _fn(**params):
        db = handlers.db
        yacht_id = params["yacht_id"]
        user_id = params["user_id"]
        equipment_id = params["equipment_id"]
        text = params["text"]
        note_type = params.get("note_type", "observation")
        requires_ack = params.get("requires_ack", False)

        # Verify equipment exists
        eq_result = db.table("pms_equipment").select(
            "id"
        ).eq("id", equipment_id).eq("yacht_id", yacht_id).maybe_single().execute()

        if not eq_result.data:
            return {
                "status": "error",
                "error_code": "NOT_FOUND",
                "message": "Equipment not found"
            }

        # Insert note
        note_payload = {
            "yacht_id": yacht_id,
            "equipment_id": equipment_id,
            "text": text,
            "note_type": note_type,
            "requires_ack": requires_ack,
            "created_by": user_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        ins = db.table("pms_notes").insert(note_payload).execute()
        note_id = (ins.data or [{}])[0].get("id")

        # Audit log
        _write_audit_log(db, {
            "yacht_id": yacht_id,
            "entity_type": "equipment",
            "entity_id": equipment_id,
            "action": "equipment_note_added",
            "user_id": user_id,
            "old_values": None,
            "new_values": {"note_id": note_id, "text": text[:100]},
            "signature": {},
        })

        return {
            "status": "success",
            "note_id": note_id,
            "equipment_id": equipment_id,
        }

    return _fn


def _attach_file_to_equipment_adapter(handlers: EquipmentHandlers):
    """
    Attach a file (photo/document) to equipment.

    Required fields: equipment_id, file (file upload)
    Optional fields: description, tags
    Allowed roles: all crew
    """
    async def _fn(**params):
        db = handlers.db
        yacht_id = params["yacht_id"]
        user_id = params["user_id"]
        equipment_id = params["equipment_id"]
        description = params.get("description")
        tags = params.get("tags", [])

        # File upload params (provided by storage layer)
        filename = params.get("filename")
        original_filename = params.get("original_filename")
        mime_type = params.get("mime_type")
        file_size = params.get("file_size")
        storage_path = params.get("storage_path")

        if not storage_path:
            return {
                "status": "error",
                "error_code": "MISSING_FILE",
                "message": "File upload required"
            }

        # Verify equipment exists
        eq_result = db.table("pms_equipment").select(
            "id"
        ).eq("id", equipment_id).eq("yacht_id", yacht_id).maybe_single().execute()

        if not eq_result.data:
            return {
                "status": "error",
                "error_code": "NOT_FOUND",
                "message": "Equipment not found"
            }

        # Insert attachment
        attachment_payload = {
            "yacht_id": yacht_id,
            "entity_type": "equipment",
            "entity_id": equipment_id,
            "filename": filename,
            "original_filename": original_filename,
            "mime_type": mime_type,
            "file_size": file_size,
            "storage_path": storage_path,
            "description": description,
            "tags": tags if tags else None,
            "uploaded_by": user_id,
            "uploaded_at": datetime.now(timezone.utc).isoformat(),
        }

        ins = db.table("pms_attachments").insert(attachment_payload).execute()
        attachment_id = (ins.data or [{}])[0].get("id")

        # Audit log
        _write_audit_log(db, {
            "yacht_id": yacht_id,
            "entity_type": "equipment",
            "entity_id": equipment_id,
            "action": "equipment_file_attached",
            "user_id": user_id,
            "old_values": None,
            "new_values": {"attachment_id": attachment_id, "filename": original_filename},
            "signature": {},
        })

        return {
            "status": "success",
            "attachment_id": attachment_id,
            "equipment_id": equipment_id,
            "storage_path": storage_path,
        }

    return _fn


def _create_work_order_for_equipment_adapter(handlers: EquipmentHandlers):
    """
    Create a work order for equipment (prepare/execute pattern).

    Required fields: equipment_id, title, type, priority
    Optional fields: description, assigned_to, due_date, fault_severity
    Allowed roles: engineer, eto, chief_engineer, chief_officer, captain, purser, manager

    CRITICAL: Prepare returns proposed WO; execute creates WO and optionally linked fault.
    """
    async def _fn(**params):
        db = handlers.db
        yacht_id = params["yacht_id"]
        user_id = params["user_id"]
        equipment_id = params["equipment_id"]
        title = params["title"]
        wo_type = params["type"]
        priority = params["priority"]
        description = params.get("description")
        assigned_to = params.get("assigned_to")
        due_date = params.get("due_date")
        fault_severity = params.get("fault_severity")
        request_context = params.get("request_context")

        # Verify equipment exists
        eq_result = db.table("pms_equipment").select(
            "id, name, status"
        ).eq("id", equipment_id).eq("yacht_id", yacht_id).maybe_single().execute()

        if not eq_result.data:
            return {
                "status": "error",
                "error_code": "NOT_FOUND",
                "message": "Equipment not found"
            }

        equipment_name = eq_result.data.get("name")
        equipment_status = eq_result.data.get("status")

        # Validate work order type
        valid_types = ['corrective', 'preventive', 'predictive', 'emergency', 'project']
        if wo_type not in valid_types:
            return {
                "status": "error",
                "error_code": "INVALID_TYPE",
                "message": f"Invalid type: must be one of {valid_types}"
            }

        # PREPARE MODE: Return proposed WO
        if is_prepare_mode(params):
            confirmation_token = generate_confirmation_token(
                "create_work_order_for_equipment",
                equipment_id
            )

            wo_number = f"WO-{datetime.now().strftime('%Y%m%d')}-{datetime.now().strftime('%H%M%S')}"

            proposed_wo = {
                "wo_number": wo_number,
                "equipment_id": equipment_id,
                "equipment_name": equipment_name,
                "equipment_status": equipment_status,
                "title": title,
                "description": description,
                "type": wo_type,
                "priority": priority,
                "status": "open",
                "assigned_to": assigned_to,
                "due_date": due_date,
            }

            # Check if fault will be created
            will_create_fault = fault_severity and wo_type in ('corrective', 'emergency')

            return {
                "status": "success",
                "mode": "prepare",
                "confirmation_token": confirmation_token,
                "proposed_work_order": proposed_wo,
                "will_create_fault": will_create_fault,
                "fault_severity": fault_severity if will_create_fault else None,
                "validation": {
                    "equipment_exists": True,
                    "type_valid": True,
                },
            }

        # EXECUTE MODE: Create work order
        wo_number = f"WO-{datetime.now().strftime('%Y%m%d')}-{datetime.now().strftime('%H%M%S')}"

        wo_payload = {
            "yacht_id": yacht_id,
            "wo_number": wo_number,
            "equipment_id": equipment_id,
            "title": title,
            "description": description,
            "wo_type": wo_type,
            "priority": priority,
            "status": "open",
            "assigned_to": assigned_to,
            "due_date": due_date,
            "created_by": user_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        ins = db.table("pms_work_orders").insert(wo_payload).execute()
        wo_id = (ins.data or [{}])[0].get("id")

        # If fault severity provided and type is corrective/emergency, create fault
        fault_id = None
        if fault_severity and wo_type in ('corrective', 'emergency'):
            fault_code = f"FLT-{datetime.now().strftime('%Y%m%d')}-{datetime.now().strftime('%H%M%S')}"
            fault_payload = {
                "yacht_id": yacht_id,
                "fault_code": fault_code,
                "equipment_id": equipment_id,
                "work_order_id": wo_id,
                "title": title,
                "severity": fault_severity,
                "status": "open",
                "detected_by": user_id,
                "detected_at": datetime.now(timezone.utc).isoformat(),
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            try:
                fault_ins = db.table("pms_faults").insert(fault_payload).execute()
                fault_id = (fault_ins.data or [{}])[0].get("id")

                # Link fault to WO
                db.table("pms_work_orders").update(
                    {"fault_id": fault_id}
                ).eq("id", wo_id).execute()
            except Exception as e:
                logger.warning(f"Failed to create fault: {e}")

        # Extract audit metadata
        audit_meta = extract_audit_metadata(request_context)

        # Audit log
        _write_audit_log(db, {
            "yacht_id": yacht_id,
            "entity_type": "equipment",
            "entity_id": equipment_id,
            "action": "create_work_order_for_equipment",
            "user_id": user_id,
            "old_values": None,
            "new_values": {
                "work_order_id": wo_id,
                "wo_number": wo_number,
                "fault_id": fault_id,
                "type": wo_type,
                "priority": priority
            },
            "signature": {},
            **audit_meta,
        })

        return {
            "status": "success",
            "mode": "execute",
            "work_order_id": wo_id,
            "wo_number": wo_number,
            "equipment_id": equipment_id,
            "equipment_name": equipment_name,
            "fault_id": fault_id,
        }

    return _fn


def _link_part_to_equipment_adapter(handlers: EquipmentHandlers):
    """
    Link a part to equipment (BOM entry).

    Required fields: equipment_id, part_id
    Optional fields: quantity_required, notes
    Allowed roles: engineer, eto, chief_engineer, chief_officer, captain, manager
    """
    async def _fn(**params):
        db = handlers.db
        yacht_id = params["yacht_id"]
        user_id = params["user_id"]
        equipment_id = params["equipment_id"]
        part_id = params["part_id"]
        quantity_required = params.get("quantity_required", 1)
        notes = params.get("notes")

        # Verify equipment exists
        eq_result = db.table("pms_equipment").select(
            "id"
        ).eq("id", equipment_id).eq("yacht_id", yacht_id).maybe_single().execute()

        if not eq_result.data:
            return {
                "status": "error",
                "error_code": "NOT_FOUND",
                "message": "Equipment not found"
            }

        # Verify part exists and belongs to same yacht
        part_result = db.table("pms_parts").select(
            "id, name"
        ).eq("id", part_id).eq("yacht_id", yacht_id).maybe_single().execute()

        if not part_result.data:
            return {
                "status": "error",
                "error_code": "NOT_FOUND",
                "message": "Part not found"
            }

        part_name = part_result.data.get("name")

        # Check if link already exists
        existing = db.table("pms_equipment_parts_bom").select(
            "id"
        ).eq("equipment_id", equipment_id).eq("part_id", part_id).maybe_single().execute()

        if existing.data:
            return {
                "status": "error",
                "error_code": "DUPLICATE",
                "message": "Part is already linked to this equipment"
            }

        # Create BOM link
        bom_payload = {
            "yacht_id": yacht_id,
            "equipment_id": equipment_id,
            "part_id": part_id,
            "quantity_required": quantity_required,
            "notes": notes,
            "created_by": user_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        ins = db.table("pms_equipment_parts_bom").insert(bom_payload).execute()
        bom_id = (ins.data or [{}])[0].get("id")

        # Audit log
        _write_audit_log(db, {
            "yacht_id": yacht_id,
            "entity_type": "equipment",
            "entity_id": equipment_id,
            "action": "equipment_part_linked",
            "user_id": user_id,
            "old_values": None,
            "new_values": {"bom_id": bom_id, "part_id": part_id, "part_name": part_name},
            "signature": {},
        })

        return {
            "status": "success",
            "bom_id": bom_id,
            "equipment_id": equipment_id,
            "part_id": part_id,
            "part_name": part_name,
        }

    return _fn


def _flag_equipment_attention_adapter(handlers: EquipmentHandlers):
    """
    Flag equipment for attention.

    Required fields: equipment_id, attention_flag
    Optional fields: attention_reason
    Allowed roles: engineer, eto, chief_engineer, chief_officer, captain, manager
    """
    async def _fn(**params):
        db = handlers.db
        yacht_id = params["yacht_id"]
        user_id = params["user_id"]
        equipment_id = params["equipment_id"]
        attention_flag = params["attention_flag"]
        attention_reason = params.get("attention_reason")

        # Verify equipment exists
        eq_result = db.table("pms_equipment").select(
            "id, attention_flag"
        ).eq("id", equipment_id).eq("yacht_id", yacht_id).maybe_single().execute()

        if not eq_result.data:
            return {
                "status": "error",
                "error_code": "NOT_FOUND",
                "message": "Equipment not found"
            }

        old_flag = eq_result.data.get("attention_flag", False)

        # Update attention flag
        update_payload = {
            "attention_flag": attention_flag,
            "attention_reason": attention_reason if attention_flag else None,
            "updated_by": user_id,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

        db.table("pms_equipment").update(update_payload).eq(
            "id", equipment_id
        ).execute()

        # Audit log
        _write_audit_log(db, {
            "yacht_id": yacht_id,
            "entity_type": "equipment",
            "entity_id": equipment_id,
            "action": "equipment_attention_flagged",
            "user_id": user_id,
            "old_values": {"attention_flag": old_flag},
            "new_values": {"attention_flag": attention_flag, "attention_reason": attention_reason},
            "signature": {},
        })

        return {
            "status": "success",
            "equipment_id": equipment_id,
            "attention_flag": attention_flag,
        }

    return _fn


def _decommission_equipment_adapter(handlers: EquipmentHandlers):
    """
    Decommission equipment (SIGNED action).

    Required fields: equipment_id, reason, signature
    Optional fields: replacement_equipment_id
    Allowed roles: captain, manager
    """
    async def _fn(**params):
        db = handlers.db
        yacht_id = params["yacht_id"]
        user_id = params["user_id"]
        equipment_id = params["equipment_id"]
        reason = params["reason"]
        signature = params["signature"]  # {pin_hash, totp_hash, timestamp}
        replacement_equipment_id = params.get("replacement_equipment_id")

        # Validate signature is present
        if not signature or not isinstance(signature, dict):
            return {
                "status": "error",
                "error_code": "SIGNATURE_REQUIRED",
                "message": "This action requires a signature"
            }

        # Verify equipment exists
        eq_result = db.table("pms_equipment").select(
            "id, name, status"
        ).eq("id", equipment_id).eq("yacht_id", yacht_id).maybe_single().execute()

        if not eq_result.data:
            return {
                "status": "error",
                "error_code": "NOT_FOUND",
                "message": "Equipment not found"
            }

        old_status = eq_result.data.get("status")
        equipment_name = eq_result.data.get("name")

        # Check if already decommissioned
        if old_status == "decommissioned":
            return {
                "status": "error",
                "error_code": "ALREADY_DECOMMISSIONED",
                "message": "Equipment is already decommissioned"
            }

        # Decommission (trigger will set deleted_at)
        update_payload = {
            "status": "decommissioned",
            "deletion_reason": reason,
            "deleted_by": user_id,
            "deleted_at": datetime.now(timezone.utc).isoformat(),
            "updated_by": user_id,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

        db.table("pms_equipment").update(update_payload).eq(
            "id", equipment_id
        ).execute()

        # Create entity link to replacement if provided
        if replacement_equipment_id:
            try:
                db.table("pms_entity_links").insert({
                    "yacht_id": yacht_id,
                    "source_entity_type": "equipment",
                    "source_entity_id": equipment_id,
                    "target_entity_type": "equipment",
                    "target_entity_id": replacement_equipment_id,
                    "link_type": "replaced_by",
                    "note": f"Decommissioned and replaced: {reason}",
                    "created_by": user_id,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }).execute()
            except Exception as e:
                logger.warning(f"Failed to create replacement link: {e}")

        # Audit log with SIGNATURE (non-empty)
        _write_audit_log(db, {
            "yacht_id": yacht_id,
            "entity_type": "equipment",
            "entity_id": equipment_id,
            "action": "equipment_decommissioned",
            "user_id": user_id,
            "old_values": {"status": old_status},
            "new_values": {"status": "decommissioned", "reason": reason},
            "signature": signature,  # SIGNED action - actual signature payload
        })

        return {
            "status": "success",
            "equipment_id": equipment_id,
            "equipment_name": equipment_name,
            "decommissioned": True,
            "replacement_equipment_id": replacement_equipment_id,
        }

    return _fn


def _record_equipment_hours_adapter(handlers: EquipmentHandlers):
    """
    Record equipment running hours.

    Required fields: equipment_id, hours_reading
    Optional fields: reading_type, notes
    Allowed roles: engineer, eto, chief_engineer, chief_officer, captain, manager
    """
    async def _fn(**params):
        db = handlers.db
        yacht_id = params["yacht_id"]
        user_id = params["user_id"]
        equipment_id = params["equipment_id"]
        hours_reading = params["hours_reading"]
        reading_type = params.get("reading_type", "manual")
        notes = params.get("notes")

        # Validate hours
        try:
            hours_reading = float(hours_reading)
            if hours_reading < 0:
                raise ValueError("Hours must be positive")
        except (TypeError, ValueError):
            return {
                "status": "error",
                "error_code": "INVALID_HOURS",
                "message": "Hours reading must be a positive number"
            }

        # Verify equipment exists
        eq_result = db.table("pms_equipment").select(
            "id, name, running_hours"
        ).eq("id", equipment_id).eq("yacht_id", yacht_id).maybe_single().execute()

        if not eq_result.data:
            return {
                "status": "error",
                "error_code": "NOT_FOUND",
                "message": "Equipment not found"
            }

        old_hours = eq_result.data.get("running_hours", 0) or 0

        # Insert hours log (trigger will update equipment.running_hours)
        log_payload = {
            "yacht_id": yacht_id,
            "equipment_id": equipment_id,
            "hours_reading": hours_reading,
            "reading_type": reading_type,
            "notes": notes,
            "source": "celeste",
            "recorded_by": user_id,
            "recorded_at": datetime.now(timezone.utc).isoformat(),
        }

        ins = db.table("pms_equipment_hours_log").insert(log_payload).execute()
        log_id = (ins.data or [{}])[0].get("id")

        # Audit log
        _write_audit_log(db, {
            "yacht_id": yacht_id,
            "entity_type": "equipment",
            "entity_id": equipment_id,
            "action": "equipment_hours_recorded",
            "user_id": user_id,
            "old_values": {"running_hours": old_hours},
            "new_values": {"running_hours": hours_reading, "reading_type": reading_type},
            "signature": {},
        })

        return {
            "status": "success",
            "log_id": log_id,
            "equipment_id": equipment_id,
            "hours_reading": hours_reading,
            "hours_delta": hours_reading - old_hours if old_hours else None,
        }

    return _fn


# =============================================================================
# ADDITIONAL MUTATION ADAPTERS - Equipment Lens v2 Phase A
# =============================================================================

def _create_equipment_adapter(handlers: EquipmentHandlers):
    """
    Create new equipment.

    Required fields: name, category
    Optional fields: manufacturer, model, serial_number, location, parent_id, running_hours
    Allowed roles: engineer, eto, chief_engineer, chief_officer, captain, manager
    """
    async def _fn(**params):
        db = handlers.db
        yacht_id = params["yacht_id"]
        user_id = params["user_id"]
        name = params["name"]
        category = params["category"]
        manufacturer = params.get("manufacturer")
        model = params.get("model")
        serial_number = params.get("serial_number")
        location = params.get("location")
        parent_id = params.get("parent_id")
        running_hours = params.get("running_hours")

        # Validate parent exists in same yacht if provided
        if parent_id:
            parent_result = db.table("pms_equipment").select(
                "id"
            ).eq("id", parent_id).eq("yacht_id", yacht_id).maybe_single().execute()

            if not parent_result.data:
                return {
                    "status": "error",
                    "error_code": "INVALID_PARENT",
                    "message": "Parent equipment not found in this yacht"
                }

        # Create equipment
        equipment_payload = {
            "yacht_id": yacht_id,
            "name": name,
            "category": category,
            "manufacturer": manufacturer,
            "model": model,
            "serial_number": serial_number,
            "location": location,
            "parent_id": parent_id,
            "running_hours": running_hours,
            "status": "operational",
            "created_by": user_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        ins = db.table("pms_equipment").insert(equipment_payload).execute()
        equipment = (ins.data or [{}])[0]
        equipment_id = equipment.get("id")

        # Audit log
        _write_audit_log(db, {
            "yacht_id": yacht_id,
            "entity_type": "equipment",
            "entity_id": equipment_id,
            "action": "equipment_created",
            "user_id": user_id,
            "old_values": None,
            "new_values": {"name": name, "category": category},
            "signature": {},
        })

        return {
            "status": "success",
            "equipment_id": equipment_id,
            "name": name,
            "category": category,
        }

    return _fn


def _assign_parent_equipment_adapter(handlers: EquipmentHandlers):
    """
    Assign parent equipment (set parent_id).

    Required fields: equipment_id, parent_id (null to clear)
    Allowed roles: engineer, eto, chief_engineer, chief_officer, captain, manager
    """
    async def _fn(**params):
        db = handlers.db
        yacht_id = params["yacht_id"]
        user_id = params["user_id"]
        equipment_id = params["equipment_id"]
        parent_id = params.get("parent_id")  # None to clear

        # Verify equipment exists
        eq_result = db.table("pms_equipment").select(
            "id, name, parent_id"
        ).eq("id", equipment_id).eq("yacht_id", yacht_id).maybe_single().execute()

        if not eq_result.data:
            return {
                "status": "error",
                "error_code": "NOT_FOUND",
                "message": "Equipment not found"
            }

        old_parent_id = eq_result.data.get("parent_id")

        # Validate parent exists in same yacht if provided
        if parent_id:
            # Prevent self-reference
            if parent_id == equipment_id:
                return {
                    "status": "error",
                    "error_code": "INVALID_PARENT",
                    "message": "Equipment cannot be its own parent"
                }

            parent_result = db.table("pms_equipment").select(
                "id, name"
            ).eq("id", parent_id).eq("yacht_id", yacht_id).maybe_single().execute()

            if not parent_result.data:
                return {
                    "status": "error",
                    "error_code": "INVALID_PARENT",
                    "message": "Parent equipment not found in this yacht"
                }

        # Update parent
        db.table("pms_equipment").update({
            "parent_id": parent_id,
            "updated_by": user_id,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", equipment_id).execute()

        # Audit log
        _write_audit_log(db, {
            "yacht_id": yacht_id,
            "entity_type": "equipment",
            "entity_id": equipment_id,
            "action": "equipment_parent_assigned",
            "user_id": user_id,
            "old_values": {"parent_id": old_parent_id},
            "new_values": {"parent_id": parent_id},
            "signature": {},
        })

        return {
            "status": "success",
            "equipment_id": equipment_id,
            "parent_id": parent_id,
            "previous_parent_id": old_parent_id,
        }

    return _fn


def _archive_equipment_adapter(handlers: EquipmentHandlers):
    """
    Archive equipment (status flip, reversible).

    Required fields: equipment_id, reason
    Allowed roles: captain, manager

    CRITICAL: Archive uses status='archived' (not deleted_at). Reversible via restore.
    """
    async def _fn(**params):
        db = handlers.db
        yacht_id = params["yacht_id"]
        user_id = params["user_id"]
        equipment_id = params["equipment_id"]
        reason = params["reason"]
        request_context = params.get("request_context")

        # Verify equipment exists
        eq_result = db.table("pms_equipment").select(
            "id, name, status"
        ).eq("id", equipment_id).eq("yacht_id", yacht_id).maybe_single().execute()

        if not eq_result.data:
            return {
                "status": "error",
                "error_code": "NOT_FOUND",
                "message": "Equipment not found"
            }

        old_status = eq_result.data.get("status")

        # Check if already archived
        if old_status == "archived":
            return {
                "status": "error",
                "error_code": "ALREADY_ARCHIVED",
                "message": "Equipment is already archived"
            }

        # Check if decommissioned (terminal - cannot archive)
        if old_status == "decommissioned":
            return {
                "status": "error",
                "error_code": "CANNOT_ARCHIVE",
                "message": "Decommissioned equipment cannot be archived"
            }

        equipment_name = eq_result.data.get("name")

        # Archive (status flip only)
        now = datetime.now(timezone.utc).isoformat()
        db.table("pms_equipment").update({
            "status": "archived",
            "updated_by": user_id,
            "updated_at": now,
        }).eq("id", equipment_id).execute()

        # Extract audit metadata
        audit_meta = extract_audit_metadata(request_context)

        # Audit log
        _write_audit_log(db, {
            "yacht_id": yacht_id,
            "entity_type": "equipment",
            "entity_id": equipment_id,
            "action": "equipment_archived",
            "user_id": user_id,
            "old_values": {"status": old_status},
            "new_values": {"status": "archived", "reason": reason},
            "signature": {},
            **audit_meta,
        })

        return {
            "status": "success",
            "equipment_id": equipment_id,
            "equipment_name": equipment_name,
            "archived": True,
            "old_status": old_status,
            "new_status": "archived",
        }

    return _fn


def _restore_archived_equipment_adapter(handlers: EquipmentHandlers):
    """
    Restore archived equipment (SIGNED action).

    Required fields: equipment_id, signature
    Optional fields: restore_reason
    Allowed roles: captain, manager

    CRITICAL: Restores from status='archived' to status='in_service'. Decommissioned remains terminal.
    """
    async def _fn(**params):
        db = handlers.db
        yacht_id = params["yacht_id"]
        user_id = params["user_id"]
        equipment_id = params["equipment_id"]
        signature = params["signature"]  # {pin_hash, totp_hash, timestamp}
        restore_reason = params.get("restore_reason", "Restored by authorized user")
        request_context = params.get("request_context")

        # Validate signature is present
        if not signature or not isinstance(signature, dict):
            return {
                "status": "error",
                "error_code": "SIGNATURE_REQUIRED",
                "message": "This action requires a signature"
            }

        # Verify equipment exists
        eq_result = db.table("pms_equipment").select(
            "id, name, status"
        ).eq("id", equipment_id).eq("yacht_id", yacht_id).maybe_single().execute()

        if not eq_result.data:
            return {
                "status": "error",
                "error_code": "NOT_FOUND",
                "message": "Equipment not found"
            }

        old_status = eq_result.data.get("status")

        # Check if not archived
        if old_status != "archived":
            return {
                "status": "error",
                "error_code": "NOT_ARCHIVED",
                "message": f"Equipment is not archived (current status: {old_status})"
            }

        # Note: Decommissioned check not needed here since archived != decommissioned
        # Decommissioned is terminal and cannot be archived

        equipment_name = eq_result.data.get("name")

        # Restore (status flip to in_service)
        now = datetime.now(timezone.utc).isoformat()
        db.table("pms_equipment").update({
            "status": "in_service",  # Restored to in_service
            "updated_by": user_id,
            "updated_at": now,
        }).eq("id", equipment_id).execute()

        # Extract audit metadata
        audit_meta = extract_audit_metadata(request_context)

        # Audit log with SIGNATURE
        _write_audit_log(db, {
            "yacht_id": yacht_id,
            "entity_type": "equipment",
            "entity_id": equipment_id,
            "action": "equipment_restored",
            "user_id": user_id,
            "old_values": {"status": old_status},
            "new_values": {"status": "in_service", "restore_reason": restore_reason},
            "signature": signature,  # SIGNED action
            **audit_meta,
        })

        return {
            "status": "success",
            "equipment_id": equipment_id,
            "equipment_name": equipment_name,
            "restored": True,
            "old_status": old_status,
            "new_status": "in_service",
        }

    return _fn


def _get_open_faults_for_equipment_adapter(handlers: EquipmentHandlers):
    """
    Get open faults for equipment (READ handler).

    Required fields: equipment_id
    Optional fields: limit, offset, include_historical
    Allowed roles: all crew

    CRITICAL: By default returns only OPEN faults. Use include_historical=true to include closed/resolved.
    """
    async def _fn(**params):
        db = handlers.db
        yacht_id = params["yacht_id"]
        equipment_id = params["equipment_id"]
        limit = params.get("limit", 20)
        offset = params.get("offset", 0)
        include_historical = params.get("include_historical", False)  # Toggle for historical faults

        # Verify equipment exists
        eq_result = db.table("pms_equipment").select(
            "id, name"
        ).eq("id", equipment_id).eq("yacht_id", yacht_id).maybe_single().execute()

        if not eq_result.data:
            return {
                "status": "error",
                "error_code": "NOT_FOUND",
                "message": "Equipment not found"
            }

        equipment_name = eq_result.data.get("name")

        # Build query
        query = db.table("pms_faults").select(
            "id, fault_code, title, severity, status, detected_at, created_at",
            count="exact"
        ).eq("yacht_id", yacht_id).eq("equipment_id", equipment_id)

        # Filter by status (default: exclude closed/resolved/dismissed)
        if not include_historical:
            query = query.not_.in_("status", ["closed", "resolved", "dismissed"])

        # Execute query
        result = query.order("created_at", desc=True).range(offset, offset + limit - 1).execute()

        faults = result.data or []
        total_count = result.count or len(faults)

        # Compute summary (count by severity)
        summary = {
            "total": total_count,
            "critical": len([f for f in faults if f.get("severity") == "critical"]),
            "major": len([f for f in faults if f.get("severity") == "major"]),
            "minor": len([f for f in faults if f.get("severity") == "minor"]),
        }

        return {
            "status": "success",
            "equipment_id": equipment_id,
            "equipment_name": equipment_name,
            "faults": faults,
            "summary": summary,
            "include_historical": include_historical,
            "pagination": {
                "offset": offset,
                "limit": limit,
                "total": total_count,
            },
        }

    return _fn


def _get_related_entities_for_equipment_adapter(handlers: EquipmentHandlers):
    """
    Get related entities for equipment (Show Related feature).

    Required fields: equipment_id
    Optional fields: entity_types (filter)
    Allowed roles: all crew
    """
    async def _fn(**params):
        db = handlers.db
        yacht_id = params["yacht_id"]
        equipment_id = params["equipment_id"]
        entity_types = params.get("entity_types")  # Optional filter

        # Verify equipment exists
        eq_result = db.table("pms_equipment").select(
            "id, name"
        ).eq("id", equipment_id).eq("yacht_id", yacht_id).maybe_single().execute()

        if not eq_result.data:
            return {
                "status": "error",
                "error_code": "NOT_FOUND",
                "message": "Equipment not found"
            }

        equipment_name = eq_result.data.get("name")

        # Query entity links (both directions)
        outgoing_query = db.table("pms_entity_links").select(
            "id, target_entity_type, target_entity_id, relationship_type, notes, created_at"
        ).eq("yacht_id", yacht_id).eq(
            "source_entity_type", "equipment"
        ).eq("source_entity_id", equipment_id)

        incoming_query = db.table("pms_entity_links").select(
            "id, source_entity_type, source_entity_id, relationship_type, notes, created_at"
        ).eq("yacht_id", yacht_id).eq(
            "target_entity_type", "equipment"
        ).eq("target_entity_id", equipment_id)

        if entity_types:
            outgoing_query = outgoing_query.in_("target_entity_type", entity_types)
            incoming_query = incoming_query.in_("source_entity_type", entity_types)

        outgoing_result = outgoing_query.execute()
        incoming_result = incoming_query.execute()

        # Format related entities
        related = []

        for link in (outgoing_result.data or []):
            related.append({
                "link_id": link["id"],
                "entity_type": link["target_entity_type"],
                "entity_id": link["target_entity_id"],
                "relationship": link.get("relationship_type", "related"),
                "direction": "outgoing",
                "notes": link.get("notes"),
                "created_at": link.get("created_at"),
            })

        for link in (incoming_result.data or []):
            related.append({
                "link_id": link["id"],
                "entity_type": link["source_entity_type"],
                "entity_id": link["source_entity_id"],
                "relationship": link.get("relationship_type", "related"),
                "direction": "incoming",
                "notes": link.get("notes"),
                "created_at": link.get("created_at"),
            })

        # Group by entity type
        by_type = {}
        for r in related:
            t = r["entity_type"]
            if t not in by_type:
                by_type[t] = []
            by_type[t].append(r)

        return {
            "status": "success",
            "equipment_id": equipment_id,
            "equipment_name": equipment_name,
            "related_entities": related,
            "by_type": by_type,
            "total_count": len(related),
        }

    return _fn


def _add_entity_link_adapter(handlers: EquipmentHandlers):
    """
    Add entity link (cross-entity relationship).

    Required fields: source_entity_type, source_entity_id, target_entity_type, target_entity_id
    Optional fields: relationship_type, notes
    Allowed roles: engineer, eto, chief_engineer, chief_officer, captain, manager
    """
    async def _fn(**params):
        db = handlers.db
        yacht_id = params["yacht_id"]
        user_id = params["user_id"]
        source_entity_type = params["source_entity_type"]
        source_entity_id = params["source_entity_id"]
        target_entity_type = params["target_entity_type"]
        target_entity_id = params["target_entity_id"]
        relationship_type = params.get("relationship_type", "related")
        notes = params.get("notes")

        # Validate not same entity
        if source_entity_type == target_entity_type and source_entity_id == target_entity_id:
            return {
                "status": "error",
                "error_code": "INVALID_LINK",
                "message": "Cannot link entity to itself"
            }

        # Check for duplicate link
        existing = db.table("pms_entity_links").select(
            "id"
        ).eq("yacht_id", yacht_id).eq(
            "source_entity_type", source_entity_type
        ).eq("source_entity_id", source_entity_id).eq(
            "target_entity_type", target_entity_type
        ).eq("target_entity_id", target_entity_id).maybe_single().execute()

        if existing.data:
            return {
                "status": "error",
                "error_code": "DUPLICATE_LINK",
                "message": "Link already exists"
            }

        # Create link
        link_payload = {
            "yacht_id": yacht_id,
            "source_entity_type": source_entity_type,
            "source_entity_id": source_entity_id,
            "target_entity_type": target_entity_type,
            "target_entity_id": target_entity_id,
            "relationship_type": relationship_type,
            "notes": notes,
            "created_by": user_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        ins = db.table("pms_entity_links").insert(link_payload).execute()
        link = (ins.data or [{}])[0]
        link_id = link.get("id")

        # Audit log
        _write_audit_log(db, {
            "yacht_id": yacht_id,
            "entity_type": source_entity_type,
            "entity_id": source_entity_id,
            "action": "entity_link_created",
            "user_id": user_id,
            "old_values": None,
            "new_values": {
                "link_id": link_id,
                "target_entity_type": target_entity_type,
                "target_entity_id": target_entity_id,
                "relationship_type": relationship_type,
            },
            "signature": {},
        })

        return {
            "status": "success",
            "link_id": link_id,
            "source_entity_type": source_entity_type,
            "source_entity_id": source_entity_id,
            "target_entity_type": target_entity_type,
            "target_entity_id": target_entity_id,
            "relationship_type": relationship_type,
        }

    return _fn


def _link_document_to_equipment_adapter(handlers: EquipmentHandlers):
    """
    Link a doc_metadata entry to equipment.

    Required fields: equipment_id, document_id
    Optional fields: description
    Allowed roles: all crew
    """
    async def _fn(**params):
        db = handlers.db
        yacht_id = params["yacht_id"]
        user_id = params["user_id"]
        equipment_id = params["equipment_id"]
        document_id = params["document_id"]
        description = params.get("description")

        # Verify equipment exists
        eq_result = db.table("pms_equipment").select(
            "id"
        ).eq("id", equipment_id).eq("yacht_id", yacht_id).maybe_single().execute()

        if not eq_result.data:
            return {
                "status": "error",
                "error_code": "NOT_FOUND",
                "message": "Equipment not found"
            }

        # Verify document exists
        doc_result = db.table("doc_metadata").select(
            "id, filename, storage_path, mime_type, file_size"
        ).eq("id", document_id).eq("yacht_id", yacht_id).maybe_single().execute()

        if not doc_result.data:
            return {
                "status": "error",
                "error_code": "DOCUMENT_NOT_FOUND",
                "message": "Document not found"
            }

        doc = doc_result.data

        # Check if already linked
        existing = db.table("pms_equipment_documents").select(
            "id"
        ).eq("equipment_id", equipment_id).eq("document_id", document_id).maybe_single().execute()

        if existing.data:
            return {
                "status": "error",
                "error_code": "ALREADY_LINKED",
                "message": "Document is already linked to this equipment"
            }

        # Create equipment document link
        link_payload = {
            "yacht_id": yacht_id,
            "equipment_id": equipment_id,
            "document_id": document_id,
            "storage_path": doc.get("storage_path"),
            "filename": doc.get("filename"),
            "original_filename": doc.get("filename"),
            "mime_type": doc.get("mime_type"),
            "file_size": doc.get("file_size"),
            "document_type": "general",
            "description": description,
            "uploaded_by": user_id,
            "uploaded_at": datetime.now(timezone.utc).isoformat(),
        }

        ins = db.table("pms_equipment_documents").insert(link_payload).execute()
        eq_doc = (ins.data or [{}])[0]
        eq_doc_id = eq_doc.get("id")

        # Audit log
        _write_audit_log(db, {
            "yacht_id": yacht_id,
            "entity_type": "equipment",
            "entity_id": equipment_id,
            "action": "equipment_document_linked",
            "user_id": user_id,
            "old_values": None,
            "new_values": {"equipment_document_id": eq_doc_id, "document_id": document_id},
            "signature": {},
        })

        return {
            "status": "success",
            "equipment_document_id": eq_doc_id,
            "equipment_id": equipment_id,
            "document_id": document_id,
        }

    return _fn


def _attach_image_with_comment_adapter(handlers: EquipmentHandlers):
    """
    Attach image to equipment with comment.

    Required fields: equipment_id, file (via storage layer), comment
    Optional fields: tags
    Allowed roles: all crew

    CRITICAL: Validates storage path format and persists comment in pms_equipment_documents.
    """
    async def _fn(**params):
        db = handlers.db
        yacht_id = params["yacht_id"]
        user_id = params["user_id"]
        equipment_id = params["equipment_id"]
        comment = params["comment"]
        tags = params.get("tags", [])
        request_context = params.get("request_context")

        # File upload params (provided by storage layer)
        filename = params.get("filename")
        original_filename = params.get("original_filename")
        mime_type = params.get("mime_type")
        file_size = params.get("file_size")
        storage_path = params.get("storage_path")

        if not storage_path:
            return {
                "status": "error",
                "error_code": "MISSING_FILE",
                "message": "File upload required"
            }

        # Validate storage path format
        path_valid, path_error = validate_storage_path_for_equipment(
            yacht_id,
            equipment_id,
            storage_path
        )

        if not path_valid:
            return {
                "status": "error",
                "error_code": "INVALID_STORAGE_PATH",
                "message": path_error
            }

        # Verify equipment exists
        eq_result = db.table("pms_equipment").select(
            "id"
        ).eq("id", equipment_id).eq("yacht_id", yacht_id).maybe_single().execute()

        if not eq_result.data:
            return {
                "status": "error",
                "error_code": "NOT_FOUND",
                "message": "Equipment not found"
            }

        # Insert equipment document with comment
        doc_payload = {
            "yacht_id": yacht_id,
            "equipment_id": equipment_id,
            "storage_path": storage_path,
            "filename": filename,
            "original_filename": original_filename,
            "mime_type": mime_type,
            "file_size": file_size,
            "document_type": "photo",
            "comment": comment,  # Inline image comment (spec-required column)
            "tags": tags if tags else None,
            "uploaded_by": user_id,
            "uploaded_at": datetime.now(timezone.utc).isoformat(),
        }

        ins = db.table("pms_equipment_documents").insert(doc_payload).execute()
        doc_id = (ins.data or [{}])[0].get("id")

        # Extract audit metadata
        audit_meta = extract_audit_metadata(request_context)

        # Audit log
        _write_audit_log(db, {
            "yacht_id": yacht_id,
            "entity_type": "equipment",
            "entity_id": equipment_id,
            "action": "attach_image_with_comment",
            "user_id": user_id,
            "old_values": None,
            "new_values": {
                "document_id": doc_id,
                "filename": original_filename,
                "comment": comment[:100]  # Truncate for audit
            },
            "signature": {},
            **audit_meta,
        })

        return {
            "status": "success",
            "document_id": doc_id,
            "equipment_id": equipment_id,
            "storage_path": storage_path,
            "comment": comment,
        }

    return _fn


def _decommission_and_replace_equipment_adapter(handlers: EquipmentHandlers):
    """
    Decommission equipment and create replacement (SIGNED, atomic, prepare/execute).

    Required fields: equipment_id, reason, signature (execute only), replacement_name
    Optional fields: replacement_manufacturer, replacement_model, replacement_serial_number
    Allowed roles: captain, manager

    CRITICAL: Prepare returns proposed changes; execute atomically marks old as decommissioned
    and creates replacement. Single signature covers entire operation.
    """
    async def _fn(**params):
        db = handlers.db
        yacht_id = params["yacht_id"]
        user_id = params["user_id"]
        equipment_id = params["equipment_id"]
        reason = params["reason"]
        signature = params.get("signature")
        request_context = params.get("request_context")

        # Replacement equipment params
        replacement_name = params.get("replacement_name")
        replacement_manufacturer = params.get("replacement_manufacturer")
        replacement_model = params.get("replacement_model")
        replacement_serial_number = params.get("replacement_serial_number")

        if not replacement_name:
            return {
                "status": "error",
                "error_code": "MISSING_REPLACEMENT_NAME",
                "message": "replacement_name is required"
            }

        # Verify old equipment exists
        eq_result = db.table("pms_equipment").select(
            "id, name, status, manufacturer, model, serial_number, system_type, location"
        ).eq("id", equipment_id).eq("yacht_id", yacht_id).maybe_single().execute()

        if not eq_result.data:
            return {
                "status": "error",
                "error_code": "NOT_FOUND",
                "message": "Equipment not found"
            }

        old_equipment = eq_result.data
        old_status = old_equipment.get("status")

        # Check if already decommissioned
        if old_status == "decommissioned":
            return {
                "status": "error",
                "error_code": "ALREADY_DECOMMISSIONED",
                "message": "Equipment is already decommissioned"
            }

        # PREPARE MODE: Return proposed changes
        if is_prepare_mode(params):
            confirmation_token = generate_confirmation_token(
                "decommission_and_replace",
                equipment_id
            )

            return {
                "status": "success",
                "mode": "prepare",
                "confirmation_token": confirmation_token,
                "proposed_changes": {
                    "old_equipment": {
                        "id": equipment_id,
                        "name": old_equipment["name"],
                        "current_status": old_status,
                        "new_status": "decommissioned",
                    },
                    "replacement_equipment": {
                        "name": replacement_name,
                        "manufacturer": replacement_manufacturer or old_equipment.get("manufacturer"),
                        "model": replacement_model or old_equipment.get("model"),
                        "serial_number": replacement_serial_number,
                        "system_type": old_equipment.get("system_type"),
                        "location": old_equipment.get("location"),
                        "status": "operational",
                    }
                },
                "validation": {
                    "signature_required": True,
                    "roles_allowed": ["captain", "manager"],
                },
                "warning": f"This will permanently decommission '{old_equipment['name']}' and create replacement '{replacement_name}'."
            }

        # EXECUTE MODE: Requires signature
        if not signature or not isinstance(signature, dict):
            return {
                "status": "error",
                "error_code": "SIGNATURE_REQUIRED",
                "message": "This action requires a signature for execution"
            }

        # Atomic transaction: decommission + create replacement
        now = datetime.now(timezone.utc).isoformat()

        # 1. Decommission old equipment
        db.table("pms_equipment").update({
            "status": "decommissioned",
            "deletion_reason": reason,
            "deleted_by": user_id,
            "deleted_at": now,
            "updated_by": user_id,
            "updated_at": now,
        }).eq("id", equipment_id).execute()

        # 2. Create replacement equipment
        replacement_payload = {
            "yacht_id": yacht_id,
            "name": replacement_name,
            "manufacturer": replacement_manufacturer or old_equipment.get("manufacturer"),
            "model": replacement_model or old_equipment.get("model"),
            "serial_number": replacement_serial_number,
            "system_type": old_equipment.get("system_type"),
            "location": old_equipment.get("location"),
            "status": "operational",
            "created_at": now,
        }

        replacement_result = db.table("pms_equipment").insert(replacement_payload).execute()
        replacement_equipment = (replacement_result.data or [{}])[0]
        replacement_id = replacement_equipment.get("id")

        # 3. Create entity link between old and replacement
        try:
            db.table("pms_entity_links").insert({
                "yacht_id": yacht_id,
                "source_entity_type": "equipment",
                "source_entity_id": equipment_id,
                "target_entity_type": "equipment",
                "target_entity_id": replacement_id,
                "relationship_type": "replaced_by",
                "notes": f"Decommissioned and replaced: {reason}",
                "created_by": user_id,
                "created_at": now,
            }).execute()
        except Exception as e:
            logger.warning(f"Failed to create replacement link: {e}")

        # Extract audit metadata
        audit_meta = extract_audit_metadata(request_context)

        # 4. Audit log for decommission (SIGNED)
        _write_audit_log(db, {
            "yacht_id": yacht_id,
            "entity_type": "equipment",
            "entity_id": equipment_id,
            "action": "decommission_and_replace_equipment",
            "user_id": user_id,
            "old_values": {"status": old_status},
            "new_values": {
                "status": "decommissioned",
                "reason": reason,
                "replacement_id": replacement_id,
                "replacement_name": replacement_name,
            },
            "signature": signature,  # SIGNED action - non-NULL
            **audit_meta,
        })

        # 5. Audit log for replacement creation (linked to parent action)
        _write_audit_log(db, {
            "yacht_id": yacht_id,
            "entity_type": "equipment",
            "entity_id": replacement_id,
            "action": "create_equipment",
            "user_id": user_id,
            "old_values": None,
            "new_values": {
                "name": replacement_name,
                "replaces_equipment_id": equipment_id,
            },
            "signature": {},  # Non-signed, but linked to parent
            **audit_meta,
        })

        return {
            "status": "success",
            "mode": "execute",
            "old_equipment_id": equipment_id,
            "old_equipment_name": old_equipment["name"],
            "replacement_equipment_id": replacement_id,
            "replacement_equipment_name": replacement_name,
            "decommissioned": True,
            "decommissioned_at": now,
        }

    return _fn


# =============================================================================
# HELPER: Write Audit Log
# =============================================================================

def _write_audit_log(db, entry: Dict):
    """
    Write entry to pms_audit_log.

    INVARIANT: signature is NEVER NULL - {} for non-signed, full payload for signed.
    """
    try:
        audit_payload = {
            "yacht_id": entry["yacht_id"],
            "entity_type": entry["entity_type"],
            "entity_id": entry["entity_id"],
            "action": entry["action"],
            "user_id": entry["user_id"],
            "old_values": entry.get("old_values"),
            "new_values": entry["new_values"],
            "signature": entry.get("signature", {}),  # Default to {} if not provided
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        db.table("pms_audit_log").insert(audit_payload).execute()
    except Exception as e:
        logger.error(f"Failed to write audit log: {e}")


# =============================================================================
# TEST
# =============================================================================

if __name__ == "__main__":
    import json

    print("=" * 60)
    print("EQUIPMENT HANDLERS - Response Format Test")
    print("=" * 60)

    # Test ResponseBuilder without database
    builder = ResponseBuilder("view_equipment", "eq-test", "equipment", "yacht-test")
    builder.set_data({
        "id": "eq-test",
        "canonical_label": "Main Engine Generator 1",
        "manufacturer": "Caterpillar",
        "model": "3512B",
        "status": "operational",
        "running_hours": 12450,
        "risk_score": 0.23
    })

    builder.add_file({
        "file_id": "doc-001",
        "filename": "CAT_3512B_Manual.pdf",
        "file_type": "pdf",
        "mime_type": "application/pdf",
        "signed_url": "https://example.supabase.co/storage/...",
        "expires_at": "2026-01-06T19:30:00+00:00"
    })

    handlers = EquipmentHandlers(None)
    for action in handlers._get_equipment_actions("eq-test"):
        builder.add_available_action(action)

    response = builder.build(source="test")

    print("\nExample view_equipment response:")
    print(json.dumps(response, indent=2))
