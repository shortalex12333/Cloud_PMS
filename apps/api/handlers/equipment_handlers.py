"""
Equipment Domain Handlers
=========================

Consolidated single-file handler for the equipment domain.

Group 1: EquipmentHandlers class — READ methods returning ResponseBuilder envelopes.
          Used by entity_routes.py for GET /v1/entity/equipment/{id}.
          Kept intact; do NOT remove.

Group 2: Flat async action handlers — dispatcher signature:
          async def fn(payload, context, yacht_id, user_id, user_context, db_client) -> dict
          Registered in HANDLERS dict at the bottom.
"""

from datetime import datetime, timezone
from typing import Any, Dict, Optional, List
import logging

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

from handlers.equipment_utils import (
    validate_storage_path_for_equipment,
    extract_audit_metadata,
    validate_status_transition,
    validate_work_order_for_oos,
    is_prepare_mode,
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


# =============================================================================
# EQUIPMENT HANDLERS CLASS — entity_routes.py READ interface (KEEP)
# =============================================================================

class EquipmentHandlers:
    """
    Equipment domain READ handlers.

    All methods return Dict in standardized envelope format.
    Used by entity_routes.py for GET /v1/entity/equipment/{id}.
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
        builder = ResponseBuilder("view_equipment", entity_id, "equipment", yacht_id)

        try:
            result = self.db.table(get_table("equipment")).select(
                map_equipment_select()
            ).eq("yacht_id", yacht_id).eq("id", entity_id).maybe_single().execute()

            if not result or not result.data:
                builder.set_error("NOT_FOUND", f"Equipment not found: {entity_id}")
                return builder.build()

            equipment = normalize_equipment(result.data)
            equipment["risk_score"] = await self._get_risk_score(entity_id)
            builder.set_data(equipment)

            files = await self._get_equipment_files(entity_id, yacht_id)
            if files:
                builder.add_files(files)

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
        builder = ResponseBuilder("view_maintenance_history", entity_id, "equipment", yacht_id)

        try:
            offset = (params or {}).get("offset", 0)
            limit = (params or {}).get("limit", 20)

            result = self.db.table(get_table("work_orders")).select(
                map_work_order_select(),
                count="exact"
            ).eq("yacht_id", yacht_id).eq(
                "equipment_id", entity_id
            ).order("created_at", desc=True).range(offset, offset + limit - 1).execute()

            work_orders = [normalize_work_order(wo) for wo in (result.data or [])]
            total_count = result.count or len(work_orders)

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
        builder = ResponseBuilder("view_equipment_parts", entity_id, "equipment", yacht_id)

        try:
            result = self.db.table(get_table("parts")).select(
                map_parts_select()
            ).eq("yacht_id", yacht_id).limit(50).execute()

            parts = [normalize_part(p) for p in (result.data or [])]

            for part in parts:
                part["stock_status"] = self._compute_stock_status(part)
                part["is_low_stock"] = part["stock_status"] in ("LOW_STOCK", "OUT_OF_STOCK")

            builder.set_data({
                "equipment_id": entity_id,
                "parts": parts,
                "summary": {
                    "total": len(parts),
                    "low_stock": len([p for p in parts if p.get("is_low_stock")]),
                    "in_stock": len([p for p in parts if p.get("stock_status") == "IN_STOCK"])
                }
            })

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
        builder = ResponseBuilder("view_linked_faults", entity_id, "equipment", yacht_id)

        try:
            offset = (params or {}).get("offset", 0)
            limit = (params or {}).get("limit", 20)

            result = self.db.table(get_table("faults")).select(
                map_faults_select(),
                count="exact"
            ).eq("yacht_id", yacht_id).eq(
                "equipment_id", entity_id
            ).order("created_at", desc=True).range(offset, offset + limit - 1).execute()

            faults = [normalize_fault(f) for f in (result.data or [])]
            total_count = result.count or len(faults)

            for fault in faults:
                fault["is_active"] = not fault.get("is_resolved", False)
                if fault["is_active"] and fault.get("created_at"):
                    try:
                        reported = datetime.fromisoformat(fault["created_at"].replace("Z", "+00:00"))
                        fault["days_open"] = (datetime.now(timezone.utc) - reported).days
                    except Exception:
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
        builder = ResponseBuilder("view_equipment_manual", entity_id, "equipment", yacht_id)

        try:
            eq_result = self.db.table(get_table("equipment")).select(
                "name"
            ).eq("id", entity_id).maybe_single().execute()

            if not eq_result.data:
                builder.set_error("NOT_FOUND", f"Equipment not found: {entity_id}")
                return builder.build()

            label = eq_result.data["name"]

            # Search pms_equipment_documents filtered by equipment_id (FIX: not document_chunks)
            docs_result = self.db.table("pms_equipment_documents").select(
                "id, document_id, filename, storage_path, mime_type, description"
            ).eq("equipment_id", entity_id).eq("yacht_id", yacht_id).limit(20).execute()

            docs = docs_result.data or []

            files = []
            seen_docs = set()

            for doc in docs:
                doc_id = doc.get("document_id") or doc.get("id")
                if doc_id and doc_id not in seen_docs:
                    seen_docs.add(doc_id)
                    if self.url_generator and doc.get("storage_path"):
                        file_ref = self.url_generator.create_file_reference(
                            bucket="documents",
                            path=doc["storage_path"],
                            filename=doc.get("filename", "document.pdf"),
                            file_id=doc_id,
                            display_name=doc.get("filename"),
                            mime_type=doc.get("mime_type", "application/pdf"),
                            expires_in_minutes=30
                        )
                        if file_ref:
                            files.append(file_ref.to_dict())

            builder.set_data({
                "equipment_id": entity_id,
                "equipment_label": label,
                "manual_sections": [
                    {
                        "document_id": d.get("document_id") or d.get("id"),
                        "filename": d.get("filename"),
                        "description": d.get("description"),
                    }
                    for d in docs
                ],
                "document_count": len(seen_docs)
            })

            if files:
                builder.add_files(files)

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
        category = (category or "").lower()
        mime_type = (mime_type or "").lower()

        if entity_type == "equipment":
            if category in ("photo", "image") or mime_type.startswith("image/"):
                return "pms-work-order-photos"

        if category in ("manual", "document", "pdf") or mime_type == "application/pdf":
            return "documents"

        return "attachments"

    async def _get_equipment_files(
        self,
        equipment_id: str,
        yacht_id: str
    ) -> List[Dict]:
        files = []

        if not self.url_generator:
            return files

        try:
            result = self.db.table("pms_attachments").select(
                "id, filename, mime_type, storage_path, category"
            ).eq("entity_type", "equipment").eq("entity_id", equipment_id).is_(
                "deleted_at", "null"
            ).execute()

            for att in (result.data or []):
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
# HANDLER REGISTRATION — entity_routes.py READ interface
# =============================================================================

def get_equipment_handlers(supabase_client) -> Dict[str, Any]:
    """
    Get equipment READ handlers for entity_routes.py.
    Returns EquipmentHandlers methods (ResponseBuilder envelopes).
    """
    handlers = EquipmentHandlers(supabase_client)
    return {
        "view_equipment": handlers.view_equipment,
        "view_maintenance_history": handlers.view_maintenance_history,
        "view_equipment_parts": handlers.view_equipment_parts,
        "view_linked_faults": handlers.view_linked_faults,
        "view_equipment_manual": handlers.view_equipment_manual,
    }


# =============================================================================
# HELPER: Write Audit Log
# =============================================================================

def _write_audit_log(db, entry: Dict):
    """
    Write entry to pms_audit_log.
    signature is NEVER NULL — {} for unsigned, full payload for signed actions.
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
            "signature": entry.get("signature", {}),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        db.table("pms_audit_log").insert(audit_payload).execute()
    except Exception as e:
        logger.error(f"Failed to write audit log: {e}")


# =============================================================================
# FLAT ACTION HANDLERS
# Dispatcher signature: (payload, context, yacht_id, user_id, user_context, db_client) -> dict
# context  = entity IDs resolved by CONTEXT_PREFILL_MAP (e.g. equipment_id)
# payload  = user-supplied form fields
# =============================================================================

async def view_equipment(payload, context, yacht_id, user_id, user_context, db_client):
    h = EquipmentHandlers(db_client)
    equipment_id = context.get("equipment_id") or payload.get("equipment_id")
    return await h.view_equipment(entity_id=equipment_id, yacht_id=yacht_id, params=payload)


async def view_maintenance_history(payload, context, yacht_id, user_id, user_context, db_client):
    h = EquipmentHandlers(db_client)
    equipment_id = context.get("equipment_id") or payload.get("equipment_id")
    return await h.view_maintenance_history(entity_id=equipment_id, yacht_id=yacht_id, params=payload)


async def view_equipment_parts(payload, context, yacht_id, user_id, user_context, db_client):
    h = EquipmentHandlers(db_client)
    equipment_id = context.get("equipment_id") or payload.get("equipment_id")
    return await h.view_equipment_parts(entity_id=equipment_id, yacht_id=yacht_id, params=payload)


async def view_linked_faults(payload, context, yacht_id, user_id, user_context, db_client):
    h = EquipmentHandlers(db_client)
    equipment_id = context.get("equipment_id") or payload.get("equipment_id")
    return await h.view_linked_faults(entity_id=equipment_id, yacht_id=yacht_id, params=payload)


async def view_equipment_manual(payload, context, yacht_id, user_id, user_context, db_client):
    h = EquipmentHandlers(db_client)
    equipment_id = context.get("equipment_id") or payload.get("equipment_id")
    return await h.view_equipment_manual(entity_id=equipment_id, yacht_id=yacht_id, params=payload)


async def update_equipment_status(payload, context, yacht_id, user_id, user_context, db_client):
    db = db_client
    equipment_id = context.get("equipment_id") or payload.get("equipment_id")
    new_status = payload.get("status") or payload.get("new_status")
    if not new_status:
        return {"status": "error", "error_code": "VALIDATION_ERROR", "message": "status is required"}
    attention_reason = payload.get("attention_reason")
    clear_attention = payload.get("clear_attention", False)
    linked_work_order_id = payload.get("linked_work_order_id")
    request_context = payload.get("request_context")

    eq_result = db.table("pms_equipment").select(
        "id, name, status, yacht_id"
    ).eq("id", equipment_id).eq("yacht_id", yacht_id).maybe_single().execute()

    if not eq_result.data:
        return {"status": "error", "error_code": "NOT_FOUND", "message": "Equipment not found"}

    old_status = eq_result.data.get("status")

    is_valid, error_msg = validate_status_transition(old_status, new_status, linked_work_order_id)
    if not is_valid:
        return {"status": "error", "error_code": "INVALID_STATUS_TRANSITION", "message": error_msg}

    if new_status == OOS_STATUS:
        wo_valid, wo_error = validate_work_order_for_oos(db, linked_work_order_id, equipment_id, yacht_id)
        if not wo_valid:
            return {"status": "error", "error_code": "INVALID_WORK_ORDER", "message": wo_error}

    update_payload = {
        "status": new_status,
        "updated_by": user_id,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

    if new_status in ('failed', 'degraded') and attention_reason:
        update_payload["attention_flag"] = True
        update_payload["attention_reason"] = attention_reason
    elif clear_attention or new_status == 'operational':
        update_payload["attention_flag"] = False
        update_payload["attention_reason"] = None

    db.table("pms_equipment").update(update_payload).eq("id", equipment_id).execute()

    audit_meta = extract_audit_metadata(request_context)
    _write_audit_log(db, {
        "yacht_id": yacht_id,
        "entity_type": "equipment",
        "entity_id": equipment_id,
        "action": "set_equipment_status",
        "user_id": user_id,
        "old_values": {"status": old_status},
        "new_values": {"status": new_status, "attention_reason": attention_reason, "work_order_id": linked_work_order_id},
        "signature": {},
        **audit_meta,
    })

    if new_status in ("failed", "degraded"):
        equipment_name = eq_result.data.get("name", "Equipment")
        try:
            db.rpc("upsert_notification", {
                "p_yacht_id": yacht_id,
                "p_user_id": user_id,
                "p_notification_type": "equipment_status_degraded",
                "p_title": f"Action required: {equipment_name} is {new_status}",
                "p_body": "Create a work order to address this issue before it worsens.",
                "p_priority": "high" if new_status == "failed" else "normal",
                "p_entity_type": "equipment",
                "p_entity_id": equipment_id,
                "p_cta_action_id": "create_work_order_for_equipment",
                "p_cta_payload": {"equipment_id": equipment_id},
                "p_idempotency_key": f"equip:{equipment_id}:degraded:{datetime.now(timezone.utc).date()}",
            }).execute()
        except Exception:
            pass

    return {
        "status": "success",
        "equipment_id": equipment_id,
        "old_status": old_status,
        "new_status": new_status,
        "work_order_id": linked_work_order_id,
    }


async def add_equipment_note(payload, context, yacht_id, user_id, user_context, db_client):
    db = db_client
    equipment_id = context.get("equipment_id") or payload.get("equipment_id")
    text = payload.get("note_text") or payload.get("text")
    note_type = payload.get("note_type", "observation")
    requires_ack = payload.get("requires_ack", False)

    eq_result = db.table("pms_equipment").select(
        "id"
    ).eq("id", equipment_id).eq("yacht_id", yacht_id).maybe_single().execute()

    if not eq_result.data:
        return {"status": "error", "error_code": "NOT_FOUND", "message": "Equipment not found"}

    # FIX: Write to pms_notes (not metadata JSON)
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

    _write_audit_log(db, {
        "yacht_id": yacht_id,
        "entity_type": "equipment",
        "entity_id": equipment_id,
        "action": "equipment_note_added",
        "user_id": user_id,
        "old_values": None,
        "new_values": {"note_id": note_id, "text": (text or "")[:100]},
        "signature": {},
    })

    return {"status": "success", "note_id": note_id, "equipment_id": equipment_id}


async def attach_file_to_equipment(payload, context, yacht_id, user_id, user_context, db_client):
    db = db_client
    equipment_id = context.get("equipment_id") or payload.get("equipment_id")
    description = payload.get("description")
    tags = payload.get("tags", [])
    filename = payload.get("filename")
    original_filename = payload.get("original_filename")
    mime_type = payload.get("mime_type")
    file_size = payload.get("file_size")
    storage_path = payload.get("storage_path")

    if not storage_path:
        return {"status": "error", "error_code": "MISSING_FILE", "message": "File upload required"}

    eq_result = db.table("pms_equipment").select(
        "id"
    ).eq("id", equipment_id).eq("yacht_id", yacht_id).maybe_single().execute()

    if not eq_result.data:
        return {"status": "error", "error_code": "NOT_FOUND", "message": "Equipment not found"}

    _bucket_fn = EquipmentHandlers(None)._get_bucket_for_attachment
    bucket = _bucket_fn("equipment", None, mime_type)

    attachment_payload = {
        "yacht_id": yacht_id,
        "entity_type": "equipment",
        "entity_id": equipment_id,
        "filename": filename,
        "original_filename": original_filename,
        "mime_type": mime_type,
        "file_size": file_size,
        "storage_path": storage_path,
        "storage_bucket": bucket,
        "description": description,
        "tags": tags if tags else None,
        "uploaded_by": user_id,
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
    }

    ins = db.table("pms_attachments").insert(attachment_payload).execute()
    attachment_id = (ins.data or [{}])[0].get("id")

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


async def create_work_order_for_equipment(payload, context, yacht_id, user_id, user_context, db_client):
    db = db_client
    equipment_id = context.get("equipment_id") or payload.get("equipment_id")
    title = payload.get("title")
    wo_type = payload.get("type")
    priority = payload.get("priority")
    description = payload.get("description")
    assigned_to = payload.get("assigned_to")
    due_date = payload.get("due_date")
    fault_severity = payload.get("fault_severity")
    request_context = payload.get("request_context")

    eq_result = db.table("pms_equipment").select(
        "id, name, status"
    ).eq("id", equipment_id).eq("yacht_id", yacht_id).maybe_single().execute()

    if not eq_result.data:
        return {"status": "error", "error_code": "NOT_FOUND", "message": "Equipment not found"}

    equipment_name = eq_result.data.get("name")
    equipment_status = eq_result.data.get("status")

    valid_types = ['corrective', 'preventive', 'predictive', 'emergency', 'project']
    if wo_type and wo_type not in valid_types:
        return {"status": "error", "error_code": "INVALID_TYPE", "message": f"Invalid type: must be one of {valid_types}"}

    if is_prepare_mode(payload):
        confirmation_token = generate_confirmation_token("create_work_order_for_equipment", equipment_id)
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
        will_create_fault = fault_severity and wo_type in ('corrective', 'emergency')
        return {
            "status": "success",
            "mode": "prepare",
            "confirmation_token": confirmation_token,
            "proposed_work_order": proposed_wo,
            "will_create_fault": will_create_fault,
            "fault_severity": fault_severity if will_create_fault else None,
            "validation": {"equipment_exists": True, "type_valid": True},
        }

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
            db.table("pms_work_orders").update({"fault_id": fault_id}).eq("id", wo_id).execute()
        except Exception as e:
            logger.warning(f"Failed to create fault: {e}")

    audit_meta = extract_audit_metadata(request_context)
    _write_audit_log(db, {
        "yacht_id": yacht_id,
        "entity_type": "equipment",
        "entity_id": equipment_id,
        "action": "create_work_order_for_equipment",
        "user_id": user_id,
        "old_values": None,
        "new_values": {"work_order_id": wo_id, "wo_number": wo_number, "fault_id": fault_id, "type": wo_type, "priority": priority},
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


async def link_part_to_equipment(payload, context, yacht_id, user_id, user_context, db_client):
    db = db_client
    equipment_id = context.get("equipment_id") or payload.get("equipment_id")
    part_id = payload.get("part_id")
    quantity_required = payload.get("quantity_required", 1)
    notes = payload.get("notes")

    eq_result = db.table("pms_equipment").select(
        "id"
    ).eq("id", equipment_id).eq("yacht_id", yacht_id).maybe_single().execute()

    if not eq_result.data:
        return {"status": "error", "error_code": "NOT_FOUND", "message": "Equipment not found"}

    part_result = db.table("pms_parts").select(
        "id, name"
    ).eq("id", part_id).eq("yacht_id", yacht_id).maybe_single().execute()

    if not part_result.data:
        return {"status": "error", "error_code": "NOT_FOUND", "message": "Part not found"}

    part_name = part_result.data.get("name")

    existing = db.table("pms_equipment_parts_bom").select(
        "id"
    ).eq("equipment_id", equipment_id).eq("part_id", part_id).maybe_single().execute()

    if existing.data:
        return {"status": "error", "error_code": "DUPLICATE", "message": "Part is already linked to this equipment"}

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


async def flag_equipment_attention(payload, context, yacht_id, user_id, user_context, db_client):
    db = db_client
    equipment_id = context.get("equipment_id") or payload.get("equipment_id")
    attention_flag = payload.get("attention_flag")
    attention_reason = payload.get("attention_reason")

    eq_result = db.table("pms_equipment").select(
        "id, attention_flag"
    ).eq("id", equipment_id).eq("yacht_id", yacht_id).maybe_single().execute()

    if not eq_result.data:
        return {"status": "error", "error_code": "NOT_FOUND", "message": "Equipment not found"}

    old_flag = eq_result.data.get("attention_flag", False)

    db.table("pms_equipment").update({
        "attention_flag": attention_flag,
        "attention_reason": attention_reason if attention_flag else None,
        "updated_by": user_id,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", equipment_id).execute()

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

    if attention_flag:
        try:
            eq_name_r = db.table("pms_equipment").select("name").eq("id", equipment_id).maybe_single().execute()
            eq_name = (eq_name_r.data or {}).get("name", "Equipment") if eq_name_r else "Equipment"
            db.rpc("upsert_notification", {
                "p_yacht_id": yacht_id,
                "p_user_id": user_id,
                "p_notification_type": "equipment_attention_flagged",
                "p_title": f"Follow up: {eq_name} flagged for attention",
                "p_body": attention_reason or "Equipment has been flagged — assign a responsible party and create a work order if needed.",
                "p_priority": "normal",
                "p_entity_type": "equipment",
                "p_entity_id": equipment_id,
                "p_cta_action_id": "create_work_order_for_equipment",
                "p_cta_payload": {"equipment_id": equipment_id},
                "p_idempotency_key": f"equip:{equipment_id}:attention:{datetime.now(timezone.utc).date()}",
            }).execute()
        except Exception:
            pass

    return {"status": "success", "equipment_id": equipment_id, "attention_flag": attention_flag}


async def decommission_equipment(payload, context, yacht_id, user_id, user_context, db_client):
    db = db_client
    equipment_id = context.get("equipment_id") or payload.get("equipment_id")
    reason = payload.get("reason")
    signature = payload.get("signature")
    replacement_equipment_id = payload.get("replacement_equipment_id")

    if not signature or not isinstance(signature, dict):
        return {"status": "error", "error_code": "SIGNATURE_REQUIRED", "message": "This action requires a signature"}

    eq_result = db.table("pms_equipment").select(
        "id, name, status"
    ).eq("id", equipment_id).eq("yacht_id", yacht_id).maybe_single().execute()

    if not eq_result.data:
        return {"status": "error", "error_code": "NOT_FOUND", "message": "Equipment not found"}

    old_status = eq_result.data.get("status")
    equipment_name = eq_result.data.get("name")

    if old_status == "decommissioned":
        return {"status": "error", "error_code": "ALREADY_DECOMMISSIONED", "message": "Equipment is already decommissioned"}

    now = datetime.now(timezone.utc).isoformat()
    db.table("pms_equipment").update({
        "status": "decommissioned",
        "deletion_reason": reason,
        "deleted_by": user_id,
        "deleted_at": now,
        "updated_by": user_id,
        "updated_at": now,
    }).eq("id", equipment_id).execute()

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
                "created_at": now,
            }).execute()
        except Exception as e:
            logger.warning(f"Failed to create replacement link: {e}")

    _write_audit_log(db, {
        "yacht_id": yacht_id,
        "entity_type": "equipment",
        "entity_id": equipment_id,
        "action": "equipment_decommissioned",
        "user_id": user_id,
        "old_values": {"status": old_status},
        "new_values": {"status": "decommissioned", "reason": reason},
        "signature": signature,
    })

    return {
        "status": "success",
        "equipment_id": equipment_id,
        "equipment_name": equipment_name,
        "decommissioned": True,
        "replacement_equipment_id": replacement_equipment_id,
    }


async def record_equipment_hours(payload, context, yacht_id, user_id, user_context, db_client):
    db = db_client
    equipment_id = context.get("equipment_id") or payload.get("equipment_id")
    hours_reading = payload.get("hours_reading")
    reading_type = payload.get("reading_type", "manual")
    notes = payload.get("notes")

    try:
        hours_reading = float(hours_reading)
        if hours_reading < 0:
            raise ValueError("Hours must be positive")
    except (TypeError, ValueError):
        return {"status": "error", "error_code": "INVALID_HOURS", "message": "Hours reading must be a positive number"}

    eq_result = db.table("pms_equipment").select(
        "id, name, running_hours"
    ).eq("id", equipment_id).eq("yacht_id", yacht_id).maybe_single().execute()

    if not eq_result.data:
        return {"status": "error", "error_code": "NOT_FOUND", "message": "Equipment not found"}

    old_hours = eq_result.data.get("running_hours", 0) or 0

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

    # FIX: Explicitly update running_hours on equipment row (not relying on trigger alone)
    db.table("pms_equipment").update({
        "running_hours": hours_reading,
        "updated_by": user_id,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", equipment_id).execute()

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


async def create_equipment(payload, context, yacht_id, user_id, user_context, db_client):
    db = db_client
    name = payload.get("name")
    category = payload.get("category")
    manufacturer = payload.get("manufacturer")
    model = payload.get("model")
    serial_number = payload.get("serial_number")
    location = payload.get("location")
    parent_id = payload.get("parent_id")
    running_hours = payload.get("running_hours")

    if parent_id:
        parent_result = db.table("pms_equipment").select(
            "id"
        ).eq("id", parent_id).eq("yacht_id", yacht_id).maybe_single().execute()
        if not parent_result.data:
            return {"status": "error", "error_code": "INVALID_PARENT", "message": "Parent equipment not found in this yacht"}

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

    _missing = []
    if not manufacturer: _missing.append("manufacturer")
    if not model: _missing.append("model")
    if not serial_number: _missing.append("serial number")
    if running_hours is None: _missing.append("running hours")
    if _missing and equipment_id:
        try:
            db.rpc("upsert_notification", {
                "p_yacht_id": yacht_id,
                "p_user_id": user_id,
                "p_notification_type": "equipment_record_incomplete",
                "p_title": f"Complete record: {name}",
                "p_body": f"Missing: {', '.join(_missing)}. Open the equipment card to fill in these details.",
                "p_priority": "low",
                "p_entity_type": "equipment",
                "p_entity_id": equipment_id,
                "p_cta_action_id": "view_equipment",
                "p_cta_payload": {"equipment_id": equipment_id},
                "p_idempotency_key": f"equip:{equipment_id}:incomplete:created",
            }).execute()
        except Exception:
            pass

    return {"status": "success", "equipment_id": equipment_id, "name": name, "category": category}


async def assign_parent_equipment(payload, context, yacht_id, user_id, user_context, db_client):
    db = db_client
    equipment_id = context.get("equipment_id") or payload.get("equipment_id")
    parent_id = payload.get("parent_id")  # None to clear

    eq_result = db.table("pms_equipment").select(
        "id, name, parent_id"
    ).eq("id", equipment_id).eq("yacht_id", yacht_id).maybe_single().execute()

    if not eq_result.data:
        return {"status": "error", "error_code": "NOT_FOUND", "message": "Equipment not found"}

    old_parent_id = eq_result.data.get("parent_id")

    if parent_id:
        if parent_id == equipment_id:
            return {"status": "error", "error_code": "INVALID_PARENT", "message": "Equipment cannot be its own parent"}

        parent_result = db.table("pms_equipment").select(
            "id, name"
        ).eq("id", parent_id).eq("yacht_id", yacht_id).maybe_single().execute()

        if not parent_result.data:
            return {"status": "error", "error_code": "INVALID_PARENT", "message": "Parent equipment not found in this yacht"}

    db.table("pms_equipment").update({
        "parent_id": parent_id,
        "updated_by": user_id,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", equipment_id).execute()

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


async def archive_equipment(payload, context, yacht_id, user_id, user_context, db_client):
    db = db_client
    equipment_id = context.get("equipment_id") or payload.get("equipment_id")
    reason = payload.get("reason")
    request_context = payload.get("request_context")

    eq_result = db.table("pms_equipment").select(
        "id, name, status"
    ).eq("id", equipment_id).eq("yacht_id", yacht_id).maybe_single().execute()

    if not eq_result.data:
        return {"status": "error", "error_code": "NOT_FOUND", "message": "Equipment not found"}

    old_status = eq_result.data.get("status")

    if old_status == "archived":
        return {"status": "error", "error_code": "ALREADY_ARCHIVED", "message": "Equipment is already archived"}

    if old_status == "decommissioned":
        return {"status": "error", "error_code": "CANNOT_ARCHIVE", "message": "Decommissioned equipment cannot be archived"}

    equipment_name = eq_result.data.get("name")
    now = datetime.now(timezone.utc).isoformat()

    db.table("pms_equipment").update({
        "status": "archived",
        "updated_by": user_id,
        "updated_at": now,
    }).eq("id", equipment_id).execute()

    audit_meta = extract_audit_metadata(request_context)
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


async def restore_archived_equipment(payload, context, yacht_id, user_id, user_context, db_client):
    db = db_client
    equipment_id = context.get("equipment_id") or payload.get("equipment_id")
    signature = payload.get("signature")
    restore_reason = payload.get("restore_reason", "Restored by authorized user")
    request_context = payload.get("request_context")

    if not signature or not isinstance(signature, dict):
        return {"status": "error", "error_code": "SIGNATURE_REQUIRED", "message": "This action requires a signature"}

    eq_result = db.table("pms_equipment").select(
        "id, name, status"
    ).eq("id", equipment_id).eq("yacht_id", yacht_id).maybe_single().execute()

    if not eq_result.data:
        return {"status": "error", "error_code": "NOT_FOUND", "message": "Equipment not found"}

    old_status = eq_result.data.get("status")

    if old_status != "archived":
        return {"status": "error", "error_code": "NOT_ARCHIVED", "message": f"Equipment is not archived (current status: {old_status})"}

    equipment_name = eq_result.data.get("name")
    now = datetime.now(timezone.utc).isoformat()

    db.table("pms_equipment").update({
        "status": "in_service",
        "updated_by": user_id,
        "updated_at": now,
    }).eq("id", equipment_id).execute()

    audit_meta = extract_audit_metadata(request_context)
    _write_audit_log(db, {
        "yacht_id": yacht_id,
        "entity_type": "equipment",
        "entity_id": equipment_id,
        "action": "equipment_restored",
        "user_id": user_id,
        "old_values": {"status": old_status},
        "new_values": {"status": "in_service", "restore_reason": restore_reason},
        "signature": signature,
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


async def get_open_faults_for_equipment(payload, context, yacht_id, user_id, user_context, db_client):
    db = db_client
    equipment_id = context.get("equipment_id") or payload.get("equipment_id")
    limit = payload.get("limit", 20)
    offset = payload.get("offset", 0)
    include_historical = payload.get("include_historical", False)

    eq_result = db.table("pms_equipment").select(
        "id, name"
    ).eq("id", equipment_id).eq("yacht_id", yacht_id).maybe_single().execute()

    if not eq_result.data:
        return {"status": "error", "error_code": "NOT_FOUND", "message": "Equipment not found"}

    equipment_name = eq_result.data.get("name")

    query = db.table("pms_faults").select(
        "id, fault_code, title, severity, status, detected_at, created_at",
        count="exact"
    ).eq("yacht_id", yacht_id).eq("equipment_id", equipment_id)

    if not include_historical:
        query = query.not_.in_("status", ["closed", "resolved", "dismissed"])

    result = query.order("created_at", desc=True).range(offset, offset + limit - 1).execute()

    faults = result.data or []
    total_count = result.count or len(faults)

    return {
        "status": "success",
        "equipment_id": equipment_id,
        "equipment_name": equipment_name,
        "faults": faults,
        "summary": {
            "total": total_count,
            "critical": len([f for f in faults if f.get("severity") == "critical"]),
            "major": len([f for f in faults if f.get("severity") == "major"]),
            "minor": len([f for f in faults if f.get("severity") == "minor"]),
        },
        "include_historical": include_historical,
        "pagination": {"offset": offset, "limit": limit, "total": total_count},
    }


async def get_related_entities_for_equipment(payload, context, yacht_id, user_id, user_context, db_client):
    db = db_client
    equipment_id = context.get("equipment_id") or payload.get("equipment_id")
    entity_types = payload.get("entity_types")

    eq_result = db.table("pms_equipment").select(
        "id, name"
    ).eq("id", equipment_id).eq("yacht_id", yacht_id).maybe_single().execute()

    if not eq_result.data:
        return {"status": "error", "error_code": "NOT_FOUND", "message": "Equipment not found"}

    equipment_name = eq_result.data.get("name")

    outgoing_query = db.table("pms_entity_links").select(
        "id, target_entity_type, target_entity_id, relationship_type, notes, created_at"
    ).eq("yacht_id", yacht_id).eq("source_entity_type", "equipment").eq("source_entity_id", equipment_id)

    incoming_query = db.table("pms_entity_links").select(
        "id, source_entity_type, source_entity_id, relationship_type, notes, created_at"
    ).eq("yacht_id", yacht_id).eq("target_entity_type", "equipment").eq("target_entity_id", equipment_id)

    if entity_types:
        outgoing_query = outgoing_query.in_("target_entity_type", entity_types)
        incoming_query = incoming_query.in_("source_entity_type", entity_types)

    outgoing_result = outgoing_query.execute()
    incoming_result = incoming_query.execute()

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

    by_type: Dict[str, list] = {}
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


async def add_entity_link(payload, context, yacht_id, user_id, user_context, db_client):
    db = db_client
    source_entity_type = payload.get("source_entity_type")
    source_entity_id = payload.get("source_entity_id") or context.get("equipment_id")
    target_entity_type = payload.get("target_entity_type")
    target_entity_id = payload.get("target_entity_id")
    relationship_type = payload.get("relationship_type", "related")
    notes = payload.get("notes")

    if source_entity_type == target_entity_type and source_entity_id == target_entity_id:
        return {"status": "error", "error_code": "INVALID_LINK", "message": "Cannot link entity to itself"}

    existing = db.table("pms_entity_links").select(
        "id"
    ).eq("yacht_id", yacht_id).eq(
        "source_entity_type", source_entity_type
    ).eq("source_entity_id", source_entity_id).eq(
        "target_entity_type", target_entity_type
    ).eq("target_entity_id", target_entity_id).maybe_single().execute()

    if existing.data:
        return {"status": "error", "error_code": "DUPLICATE_LINK", "message": "Link already exists"}

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


async def link_document_to_equipment(payload, context, yacht_id, user_id, user_context, db_client):
    db = db_client
    equipment_id = context.get("equipment_id") or payload.get("equipment_id")
    document_id = payload.get("document_id")
    description = payload.get("description")

    eq_result = db.table("pms_equipment").select(
        "id"
    ).eq("id", equipment_id).eq("yacht_id", yacht_id).maybe_single().execute()

    if not eq_result or not eq_result.data:
        return {"status": "error", "error_code": "NOT_FOUND", "message": "Equipment not found"}

    doc_result = db.table("doc_metadata").select(
        "id, filename, storage_path, content_type, size_bytes"
    ).eq("id", document_id).eq("yacht_id", yacht_id).maybe_single().execute()

    if not doc_result or not doc_result.data:
        return {"status": "error", "error_code": "DOCUMENT_NOT_FOUND", "message": "Document not found"}

    doc = doc_result.data

    existing = db.table("pms_equipment_documents").select(
        "id"
    ).eq("equipment_id", equipment_id).eq("document_id", document_id).maybe_single().execute()

    if existing and existing.data:
        return {"status": "error", "error_code": "ALREADY_LINKED", "message": "Document is already linked to this equipment"}

    link_payload = {
        "yacht_id": yacht_id,
        "equipment_id": equipment_id,
        "document_id": document_id,
        "storage_path": doc.get("storage_path"),
        "filename": doc.get("filename"),
        "original_filename": doc.get("filename"),
        "mime_type": doc.get("content_type"),
        "file_size": doc.get("size_bytes"),
        "document_type": "general",
        "description": description,
        "uploaded_by": user_id,
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
    }

    ins = db.table("pms_equipment_documents").insert(link_payload).execute()
    eq_doc_id = (ins.data or [{}])[0].get("id")

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


async def attach_image_with_comment(payload, context, yacht_id, user_id, user_context, db_client):
    db = db_client
    equipment_id = context.get("equipment_id") or payload.get("equipment_id")
    comment = payload.get("comment")
    tags = payload.get("tags", [])
    request_context = payload.get("request_context")

    filename = payload.get("filename")
    original_filename = payload.get("original_filename")
    mime_type = payload.get("mime_type")
    file_size = payload.get("file_size")
    storage_path = payload.get("storage_path")

    if not storage_path:
        return {"status": "error", "error_code": "MISSING_FILE", "message": "File upload required"}

    path_valid, path_error = validate_storage_path_for_equipment(yacht_id, equipment_id, storage_path)
    if not path_valid:
        return {"status": "error", "error_code": "INVALID_STORAGE_PATH", "message": path_error}

    eq_result = db.table("pms_equipment").select(
        "id"
    ).eq("id", equipment_id).eq("yacht_id", yacht_id).maybe_single().execute()

    if not eq_result.data:
        return {"status": "error", "error_code": "NOT_FOUND", "message": "Equipment not found"}

    doc_payload = {
        "yacht_id": yacht_id,
        "equipment_id": equipment_id,
        "storage_path": storage_path,
        "filename": filename,
        "original_filename": original_filename,
        "mime_type": mime_type,
        "file_size": file_size,
        "document_type": "photo",
        "comment": comment,
        "tags": tags if tags else None,
        "uploaded_by": user_id,
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
    }

    ins = db.table("pms_equipment_documents").insert(doc_payload).execute()
    doc_id = (ins.data or [{}])[0].get("id")

    audit_meta = extract_audit_metadata(request_context)
    _write_audit_log(db, {
        "yacht_id": yacht_id,
        "entity_type": "equipment",
        "entity_id": equipment_id,
        "action": "attach_image_with_comment",
        "user_id": user_id,
        "old_values": None,
        "new_values": {"document_id": doc_id, "filename": original_filename, "comment": (comment or "")[:100]},
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


async def decommission_and_replace_equipment(payload, context, yacht_id, user_id, user_context, db_client):
    db = db_client
    equipment_id = context.get("equipment_id") or payload.get("equipment_id")
    reason = payload.get("reason")
    signature = payload.get("signature")
    request_context = payload.get("request_context")

    replacement_name = payload.get("replacement_name")
    replacement_manufacturer = payload.get("replacement_manufacturer")
    replacement_model = payload.get("replacement_model")
    replacement_serial_number = payload.get("replacement_serial_number")

    if not replacement_name:
        return {"status": "error", "error_code": "MISSING_REPLACEMENT_NAME", "message": "replacement_name is required"}

    eq_result = db.table("pms_equipment").select(
        "id, name, status, manufacturer, model, serial_number, system_type, location"
    ).eq("id", equipment_id).eq("yacht_id", yacht_id).maybe_single().execute()

    if not eq_result.data:
        return {"status": "error", "error_code": "NOT_FOUND", "message": "Equipment not found"}

    old_equipment = eq_result.data
    old_status = old_equipment.get("status")

    if old_status == "decommissioned":
        return {"status": "error", "error_code": "ALREADY_DECOMMISSIONED", "message": "Equipment is already decommissioned"}

    if is_prepare_mode(payload):
        confirmation_token = generate_confirmation_token("decommission_and_replace", equipment_id)
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
            "validation": {"signature_required": True, "roles_allowed": ["captain", "manager"]},
            "warning": f"This will permanently decommission '{old_equipment['name']}' and create replacement '{replacement_name}'."
        }

    if not signature or not isinstance(signature, dict):
        return {"status": "error", "error_code": "SIGNATURE_REQUIRED", "message": "This action requires a signature for execution"}

    now = datetime.now(timezone.utc).isoformat()

    db.table("pms_equipment").update({
        "status": "decommissioned",
        "deletion_reason": reason,
        "deleted_by": user_id,
        "deleted_at": now,
        "updated_by": user_id,
        "updated_at": now,
    }).eq("id", equipment_id).execute()

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
    replacement_id = (replacement_result.data or [{}])[0].get("id")

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

    audit_meta = extract_audit_metadata(request_context)
    _write_audit_log(db, {
        "yacht_id": yacht_id,
        "entity_type": "equipment",
        "entity_id": equipment_id,
        "action": "decommission_and_replace_equipment",
        "user_id": user_id,
        "old_values": {"status": old_status},
        "new_values": {"status": "decommissioned", "reason": reason, "replacement_id": replacement_id, "replacement_name": replacement_name},
        "signature": signature,
        **audit_meta,
    })

    _write_audit_log(db, {
        "yacht_id": yacht_id,
        "entity_type": "equipment",
        "entity_id": replacement_id,
        "action": "create_equipment",
        "user_id": user_id,
        "old_values": None,
        "new_values": {"name": replacement_name, "replaces_equipment_id": equipment_id},
        "signature": {},
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


async def suggest_parts(payload, context, yacht_id, user_id, user_context, db_client):
    return {"status": "error", "message": "Not yet implemented", "action": "suggest_parts"}


# =============================================================================
# HANDLER REGISTRY
# =============================================================================

HANDLERS: Dict[str, Any] = {
    # READ — EquipmentHandlers wrappers
    "view_equipment": view_equipment,
    "view_maintenance_history": view_maintenance_history,
    "view_equipment_parts": view_equipment_parts,
    "view_linked_faults": view_linked_faults,
    "view_equipment_manual": view_equipment_manual,
    # MUTATION — flat handlers
    "update_equipment_status": update_equipment_status,
    "set_equipment_status": update_equipment_status,  # alias
    "add_equipment_note": add_equipment_note,
    "attach_file_to_equipment": attach_file_to_equipment,
    "create_work_order_for_equipment": create_work_order_for_equipment,
    "link_part_to_equipment": link_part_to_equipment,
    "flag_equipment_attention": flag_equipment_attention,
    "decommission_equipment": decommission_equipment,
    "record_equipment_hours": record_equipment_hours,
    "create_equipment": create_equipment,
    "assign_parent_equipment": assign_parent_equipment,
    "archive_equipment": archive_equipment,
    "restore_archived_equipment": restore_archived_equipment,
    "get_open_faults_for_equipment": get_open_faults_for_equipment,
    "get_related_entities_for_equipment": get_related_entities_for_equipment,
    "add_entity_link": add_entity_link,
    "link_document_to_equipment": link_document_to_equipment,
    "attach_image_with_comment": attach_image_with_comment,
    "decommission_and_replace_equipment": decommission_and_replace_equipment,
    "suggest_parts": suggest_parts,
}
