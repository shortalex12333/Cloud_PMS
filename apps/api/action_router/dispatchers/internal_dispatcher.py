"""
Internal Action Dispatcher

Handles fast actions directly via Supabase.

These are simple CRUD operations that don't require complex workflow orchestration.
"""

from typing import Dict, Any, Callable
import os
import logging
from datetime import datetime
from supabase import create_client, Client

# SECURITY FIX P1-005: Logger for audit failures
logger = logging.getLogger(__name__)

# Import handler classes for P1/P3 handlers
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "handlers"))

from handlers.p3_read_only_handlers import P3ReadOnlyHandlers
from handlers.p1_compliance_handlers import P1ComplianceHandlers
from handlers.p1_purchasing_handlers import P1PurchasingHandlers
from handlers.p2_mutation_light_handlers import P2MutationLightHandlers
from handlers.certificate_handlers import get_certificate_handlers as _get_certificate_handlers
from handlers.equipment_handlers import get_equipment_handlers as _get_equipment_handlers_raw
from handlers.shopping_list_handlers import get_shopping_list_handlers as _get_shopping_list_handlers_raw
from handlers.document_handlers import get_document_handlers as _get_document_handlers_raw
from handlers.receiving_handlers import (
    ReceivingHandlers,
    _create_receiving_adapter,
    _attach_receiving_image_with_comment_adapter,
    _extract_receiving_candidates_adapter,
    _update_receiving_fields_adapter,
    _add_receiving_item_adapter,
    _adjust_receiving_item_adapter,
    _link_invoice_document_adapter,
    _accept_receiving_adapter,
    _reject_receiving_adapter,
    _view_receiving_history_adapter,
)

# Lazy-initialized handler instances
_p3_handlers = None
_p1_compliance_handlers = None
_p1_purchasing_handlers = None
_p2_handlers = None
_equipment_handlers = None
_shopping_list_handlers = None
_document_handlers = None


def _get_p3_handlers():
    """Get lazy-initialized P3 read-only handlers."""
    global _p3_handlers
    if _p3_handlers is None:
        _p3_handlers = P3ReadOnlyHandlers(get_supabase_client())
    return _p3_handlers


def _get_p1_compliance_handlers():
    """Get lazy-initialized P1 compliance handlers."""
    global _p1_compliance_handlers
    if _p1_compliance_handlers is None:
        _p1_compliance_handlers = P1ComplianceHandlers(get_supabase_client())
    return _p1_compliance_handlers


def _get_p1_purchasing_handlers():
    """Get lazy-initialized P1 purchasing handlers."""
    global _p1_purchasing_handlers
    if _p1_purchasing_handlers is None:
        _p1_purchasing_handlers = P1PurchasingHandlers(get_supabase_client())
    return _p1_purchasing_handlers


def _get_p2_handlers():
    """Get lazy-initialized P2 mutation light handlers."""
    global _p2_handlers
    if _p2_handlers is None:
        _p2_handlers = P2MutationLightHandlers(get_supabase_client())
    return _p2_handlers


def _get_equipment_handlers():
    """Get lazy-initialized Equipment Lens v2 handlers."""
    global _equipment_handlers
    if _equipment_handlers is None:
        _equipment_handlers = _get_equipment_handlers_raw(get_supabase_client())
    return _equipment_handlers


def _get_receiving_handlers():
    """Get lazy-initialized Receiving Lens v1 handlers."""
    global _receiving_handlers


def _get_shopping_list_handlers():
    """Get lazy-initialized Shopping List Lens v1 handlers."""
    global _shopping_list_handlers
    if _shopping_list_handlers is None:
        _shopping_list_handlers = _get_shopping_list_handlers_raw(get_supabase_client())
    return _shopping_list_handlers


def _get_document_handlers():
    """Get lazy-initialized Document Lens v2 handlers."""
    global _document_handlers
    if _document_handlers is None:
        _document_handlers = _get_document_handlers_raw(get_supabase_client())
    return _document_handlers
    if _receiving_handlers is None:
        handlers_instance = ReceivingHandlers(get_supabase_client())
        # Build handler dictionary
        _receiving_handlers = {
            "create_receiving": _create_receiving_adapter(handlers_instance),
            "attach_receiving_image_with_comment": _attach_receiving_image_with_comment_adapter(handlers_instance),
            "extract_receiving_candidates": _extract_receiving_candidates_adapter(handlers_instance),
            "update_receiving_fields": _update_receiving_fields_adapter(handlers_instance),
            "add_receiving_item": _add_receiving_item_adapter(handlers_instance),
            "adjust_receiving_item": _adjust_receiving_item_adapter(handlers_instance),
            "link_invoice_document": _link_invoice_document_adapter(handlers_instance),
            "accept_receiving": _accept_receiving_adapter(handlers_instance),
            "reject_receiving": _reject_receiving_adapter(handlers_instance),
            "view_receiving_history": _view_receiving_history_adapter(handlers_instance),
        }
    return _receiving_handlers


def get_supabase_client() -> Client:
    """Get TENANT Supabase client for action dispatch.

    Uses DEFAULT_YACHT_CODE env var to route to correct tenant DB.
    Actions work with pms_* tables which are in TENANT.
    """
    default_yacht = os.getenv("DEFAULT_YACHT_CODE", "yTEST_YACHT_001")

    url = os.getenv(f"{default_yacht}_SUPABASE_URL") or os.getenv("SUPABASE_URL")
    key = os.getenv(f"{default_yacht}_SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_SERVICE_KEY")

    if not url or not key:
        raise ValueError(f"{default_yacht}_SUPABASE_URL and {default_yacht}_SUPABASE_SERVICE_KEY must be set")

    return create_client(url, key)


# ============================================================================
# ACTION HANDLERS
# ============================================================================


async def add_note(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Add a note to equipment.

    Required params:
        - yacht_id: UUID
        - equipment_id: UUID
        - note_text: str
        - user_id: UUID (from JWT)
    """
    supabase = get_supabase_client()

    # SECURITY FIX P1-002: Verify equipment belongs to yacht before INSERT
    eq_result = supabase.table("pms_equipment").select("id, name").eq(
        "id", params["equipment_id"]
    ).eq("yacht_id", params["yacht_id"]).execute()

    if not eq_result.data:
        raise ValueError(f"Equipment {params['equipment_id']} not found or access denied")

    # Insert note
    result = supabase.table("notes").insert({
        "yacht_id": params["yacht_id"],
        "equipment_id": params["equipment_id"],
        "note_text": params["note_text"],
        "created_by": params["user_id"],
        "created_at": datetime.utcnow().isoformat(),
    }).execute()

    if not result.data:
        raise Exception("Failed to create note")

    return {
        "note_id": result.data[0]["id"],
        "created_at": result.data[0]["created_at"],
    }


async def add_note_to_work_order(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Add a note to a work order.

    Required params:
        - yacht_id: UUID
        - work_order_id: UUID
        - note_text: str
        - user_id: UUID (from JWT)
        - note_type: str (optional, defaults to 'general')
    """
    supabase = get_supabase_client()

    # Verify work order exists and belongs to yacht (use pms_work_orders table)
    wo_result = supabase.table("pms_work_orders").select("id, wo_number, status").eq(
        "id", params["work_order_id"]
    ).eq("yacht_id", params["yacht_id"]).execute()

    if not wo_result.data:
        raise ValueError(f"Work order {params['work_order_id']} not found or access denied")

    wo = wo_result.data[0]

    # Check if work order is closed
    if wo.get("status") in ("closed", "cancelled"):
        raise ValueError(f"Cannot add note to {wo.get('status')} work order")

    # Insert note (use pms_work_order_notes table)
    result = supabase.table("pms_work_order_notes").insert({
        "work_order_id": params["work_order_id"],
        "note_text": params["note_text"],
        "note_type": params.get("note_type", "general"),
        "created_by": params["user_id"],
        "created_at": datetime.utcnow().isoformat(),
    }).execute()

    if not result.data:
        raise Exception("Failed to create work order note")

    return {
        "note_id": result.data[0]["id"],
        "work_order_id": params["work_order_id"],
        "work_order_number": wo.get("wo_number"),
        "note_text": params["note_text"],
        "note_type": params.get("note_type", "general"),
        "created_at": result.data[0]["created_at"],
        "created_by": params["user_id"],
    }


async def close_work_order(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Close a work order.

    Required params:
        - yacht_id: UUID
        - work_order_id: UUID
        - user_id: UUID (from JWT)
    """
    supabase = get_supabase_client()

    # Update work order status
    result = supabase.table("work_orders").update({
        "status": "completed",
        "completed_at": datetime.utcnow().isoformat(),
        "completed_by": params["user_id"],
    }).eq("id", params["work_order_id"]).eq(
        "yacht_id", params["yacht_id"]
    ).execute()

    if not result.data:
        raise ValueError(f"Work order {params['work_order_id']} not found or access denied")

    return {
        "work_order_id": result.data[0]["id"],
        "status": result.data[0]["status"],
        "completed_at": result.data[0]["completed_at"],
    }


async def open_document(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate a signed URL for a document.

    Required params:
        - yacht_id: UUID (from JWT context)
        - storage_path: str (path in Supabase storage)
    """
    supabase = get_supabase_client()

    # SECURITY FIX P1-001: Validate storage_path belongs to user's yacht
    yacht_id = params["yacht_id"]
    storage_path = params["storage_path"]

    # Storage paths must start with yacht_id prefix to prevent cross-tenant access
    if not storage_path.startswith(f"{yacht_id}/"):
        raise ValueError(f"Access denied: Document does not belong to your yacht")

    # Generate signed URL (valid for 1 hour)
    try:
        result = supabase.storage.from_("documents").create_signed_url(
            storage_path,
            expires_in=3600,
        )

        if not result:
            raise Exception("Failed to generate signed URL")

        return {
            "signed_url": result["signedURL"],
            "expires_in": 3600,
        }

    except Exception as e:
        raise Exception(f"Failed to generate document URL: {str(e)}")


# ============================================================================
# CERTIFICATE WRAPPERS (bridge to certificate handlers)
# ============================================================================

async def _cert_create_vessel_certificate(params: Dict[str, Any]) -> Dict[str, Any]:
    handlers = _get_certificate_handlers(get_supabase_client())
    fn = handlers.get("create_vessel_certificate")
    if not fn:
        raise ValueError("create_vessel_certificate handler not registered")
    return await fn(**params)


async def _cert_create_crew_certificate(params: Dict[str, Any]) -> Dict[str, Any]:
    handlers = _get_certificate_handlers(get_supabase_client())
    fn = handlers.get("create_crew_certificate")
    if not fn:
        raise ValueError("create_crew_certificate handler not registered")
    return await fn(**params)


async def _cert_update_certificate(params: Dict[str, Any]) -> Dict[str, Any]:
    handlers = _get_certificate_handlers(get_supabase_client())
    fn = handlers.get("update_certificate")
    if not fn:
        raise ValueError("update_certificate handler not registered")
    return await fn(**params)


async def _cert_link_document(params: Dict[str, Any]) -> Dict[str, Any]:
    handlers = _get_certificate_handlers(get_supabase_client())
    fn = handlers.get("link_document_to_certificate")
    if not fn:
        raise ValueError("link_document_to_certificate handler not registered")
    # Defensive validation: ensure document exists before delegating
    doc_id = params.get("document_id")
    yacht_id = params.get("yacht_id")
    if not doc_id:
        raise ValueError("document_id is required")
    # Resolve tenant client from context if available
    # Fallback to default tenant client if not
    try:
        supabase = get_supabase_client()
        dm = supabase.table("doc_metadata").select("id").eq("id", doc_id).maybe_single().execute()
    except Exception:
        dm = None
    if not getattr(dm, 'data', None):
        raise ValueError("document_id not found")
    return await fn(**params)


async def _cert_supersede_certificate(params: Dict[str, Any]) -> Dict[str, Any]:
    handlers = _get_certificate_handlers(get_supabase_client())
    fn = handlers.get("supersede_certificate")
    if not fn:
        raise ValueError("supersede_certificate handler not registered")
    return await fn(**params)


# ============================================================================
# DOCUMENT WRAPPERS (bridge to document handlers - Document Lens v2)
# ============================================================================

async def _doc_upload_document(params: Dict[str, Any]) -> Dict[str, Any]:
    handlers = _get_document_handlers()
    fn = handlers.get("upload_document")
    if not fn:
        raise ValueError("upload_document handler not registered")
    return await fn(**params)


async def _doc_update_document(params: Dict[str, Any]) -> Dict[str, Any]:
    handlers = _get_document_handlers()
    fn = handlers.get("update_document")
    if not fn:
        raise ValueError("update_document handler not registered")
    return await fn(**params)


async def _doc_add_document_tags(params: Dict[str, Any]) -> Dict[str, Any]:
    handlers = _get_document_handlers()
    fn = handlers.get("add_document_tags")
    if not fn:
        raise ValueError("add_document_tags handler not registered")
    return await fn(**params)


async def _doc_delete_document(params: Dict[str, Any]) -> Dict[str, Any]:
    handlers = _get_document_handlers()
    fn = handlers.get("delete_document")
    if not fn:
        raise ValueError("delete_document handler not registered")
    # Validate signature is present for SIGNED action
    if not params.get("signature") or params.get("signature") == {}:
        raise ValueError("signature payload is required for delete_document (signed action)")
    return await fn(**params)


async def _doc_get_document_url(params: Dict[str, Any]) -> Dict[str, Any]:
    handlers = _get_document_handlers()
    fn = handlers.get("get_document_url")
    if not fn:
        raise ValueError("get_document_url handler not registered")
    # Extract entity_id from params for READ handler
    entity_id = params.get("document_id")
    yacht_id = params.get("yacht_id")
    return await fn(entity_id=entity_id, yacht_id=yacht_id, params=params)


async def edit_handover_section(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Edit a section in a handover document.

    Required params:
        - yacht_id: UUID
        - handover_id: UUID
        - section_name: str
        - new_text: str
        - user_id: UUID (from JWT)
    """
    supabase = get_supabase_client()

    # Get current handover
    handover_result = supabase.table("handovers").select("*").eq(
        "id", params["handover_id"]
    ).eq("yacht_id", params["yacht_id"]).execute()

    if not handover_result.data:
        raise ValueError(f"Handover {params['handover_id']} not found or access denied")

    handover = handover_result.data[0]

    # Update section content
    content = handover.get("content", {})
    content[params["section_name"]] = params["new_text"]

    # Update handover
    # SECURITY FIX P0-005: Add yacht_id filter for tenant isolation
    result = supabase.table("handovers").update({
        "content": content,
        "updated_at": datetime.utcnow().isoformat(),
        "updated_by": params["user_id"],
    }).eq("id", params["handover_id"]).eq("yacht_id", params["yacht_id"]).execute()

    if not result.data:
        raise Exception("Failed to update handover section")

    return {
        "handover_id": result.data[0]["id"],
        "section_name": params["section_name"],
        "updated_at": result.data[0]["updated_at"],
    }


async def update_equipment_status(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Update equipment status/attention flag.

    Required params:
        - yacht_id: UUID
        - equipment_id: UUID
        - attention_flag: bool
        - attention_reason: str (optional, required if attention_flag=True)
        - user_id: UUID (from JWT)
    """
    supabase = get_supabase_client()

    # Verify equipment exists
    eq_result = supabase.table("pms_equipment").select(
        "id, name, attention_flag, attention_reason"
    ).eq("id", params["equipment_id"]).eq("yacht_id", params["yacht_id"]).execute()

    if not eq_result.data:
        raise ValueError(f"Equipment {params['equipment_id']} not found or access denied")

    equipment = eq_result.data[0]
    old_flag = equipment.get("attention_flag", False)
    old_reason = equipment.get("attention_reason")

    # Validate attention_reason required if attention_flag is True
    new_flag = params.get("attention_flag", False)
    new_reason = params.get("attention_reason", "")

    if new_flag and not new_reason:
        raise ValueError("attention_reason is required when setting attention_flag to True")

    # Update equipment
    update_data = {
        "attention_flag": new_flag,
        "attention_reason": new_reason if new_flag else None,
        "updated_at": datetime.utcnow().isoformat(),
    }

    result = supabase.table("pms_equipment").update(update_data).eq(
        "id", params["equipment_id"]
    ).eq("yacht_id", params["yacht_id"]).execute()

    if not result.data:
        raise Exception("Failed to update equipment status")

    # Create audit log
    # SECURITY FIX P1-005: Log warning on audit failure instead of silent pass
    try:
        supabase.table("pms_audit_log").insert({
            "yacht_id": params["yacht_id"],
            "action": "update_equipment_status",
            "entity_type": "equipment",
            "entity_id": params["equipment_id"],
            "user_id": params["user_id"],
            "old_values": {"attention_flag": old_flag, "attention_reason": old_reason},
            "new_values": {"attention_flag": new_flag, "attention_reason": new_reason},
            "created_at": datetime.utcnow().isoformat(),
        }).execute()
    except Exception as e:
        logger.warning(f"Audit log failed for update_equipment_status (equipment_id={params['equipment_id']}): {e}")

    return {
        "equipment_id": params["equipment_id"],
        "equipment_name": equipment.get("name"),
        "attention_flag": new_flag,
        "attention_reason": new_reason if new_flag else None,
        "updated_at": result.data[0].get("updated_at"),
        "updated_by": params["user_id"],
    }


async def add_to_handover(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Add item to shift handover list.

    Required params:
        - yacht_id: UUID
        - entity_type: str (equipment, fault, work_order, part, document)
        - entity_id: UUID
        - summary_text: str
        - category: str (urgent, in_progress, completed, watch, fyi)
        - user_id: UUID (from JWT)
        - priority: str (optional: low, normal, high)
    """
    import uuid as uuid_lib
    supabase = get_supabase_client()

    # Validate category
    valid_categories = ["urgent", "in_progress", "completed", "watch", "fyi"]
    category = params.get("category", "fyi")
    if category not in valid_categories:
        raise ValueError(f"Invalid category: {category}. Must be one of: {', '.join(valid_categories)}")

    # Validate summary text
    summary_text = params.get("summary_text", "")
    if not summary_text or len(summary_text) < 10:
        raise ValueError("summary_text must be at least 10 characters")

    # SECURITY FIX P1-004: Verify entity belongs to yacht before INSERT
    entity_id = params.get("entity_id") or params.get("equipment_id")
    entity_type = params.get("entity_type", "equipment")
    yacht_id = params["yacht_id"]

    # Map entity_type to table name for ownership verification
    entity_table_map = {
        "equipment": "pms_equipment",
        "fault": "pms_faults",
        "work_order": "pms_work_orders",
        "part": "pms_parts",
        "document": "documents",
    }

    if entity_id and entity_type in entity_table_map:
        table_name = entity_table_map[entity_type]
        entity_result = supabase.table(table_name).select("id").eq(
            "id", entity_id
        ).eq("yacht_id", yacht_id).execute()

        if not entity_result.data:
            raise ValueError(f"{entity_type.capitalize()} {entity_id} not found or access denied")

    # Map priority to integer
    priority_value = {"low": 1, "normal": 2, "high": 3, "urgent": 4}.get(
        params.get("priority", "normal"), 2
    )

    # Create handover entry
    handover_id = str(uuid_lib.uuid4())
    handover_entry = {
        "id": handover_id,
        "yacht_id": yacht_id,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "summary_text": summary_text,
        "category": category,
        "priority": priority_value,
        "added_by": params["user_id"],
        "added_at": datetime.utcnow().isoformat(),
    }

    result = supabase.table("handover_items").insert(handover_entry).execute()

    if not result.data:
        raise Exception("Failed to create handover entry")

    # Create audit log
    # SECURITY FIX P1-005: Log warning on audit failure instead of silent pass
    try:
        supabase.table("pms_audit_log").insert({
            "yacht_id": yacht_id,
            "action": "add_to_handover",
            "entity_type": "handover",
            "entity_id": handover_id,
            "user_id": params["user_id"],
            "new_values": {
                "entity_type": entity_type,
                "entity_id": entity_id,
                "category": category,
            },
            "created_at": datetime.utcnow().isoformat(),
        }).execute()
    except Exception as e:
        logger.warning(f"Audit log failed for add_to_handover (handover_id={handover_id}): {e}")

    return {
        "handover_id": handover_id,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "summary_text": summary_text,
        "category": category,
        "priority": params.get("priority", "normal"),
        "added_at": handover_entry["added_at"],
        "added_by": params["user_id"],
    }


async def delete_document(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Soft delete a document.

    Required params:
        - yacht_id: UUID
        - document_id: UUID
        - reason: str (optional)
        - user_id: UUID (from JWT)
    """
    supabase = get_supabase_client()

    # Verify document exists and belongs to yacht
    doc_result = supabase.table("documents").select(
        "id, filename, deleted_at"
    ).eq("id", params["document_id"]).eq("yacht_id", params["yacht_id"]).execute()

    if not doc_result.data:
        raise ValueError(f"Document {params['document_id']} not found or access denied")

    doc = doc_result.data[0]

    if doc.get("deleted_at"):
        raise ValueError("Document is already deleted")

    # Soft delete by setting deleted_at
    # SECURITY FIX P0-005: Add yacht_id filter for tenant isolation
    result = supabase.table("documents").update({
        "deleted_at": datetime.utcnow().isoformat(),
        "deleted_by": params["user_id"],
        "delete_reason": params.get("reason", "Deleted via API"),
    }).eq("id", params["document_id"]).eq("yacht_id", params["yacht_id"]).execute()

    if not result.data:
        raise Exception("Failed to delete document")

    # Create audit log
    # SECURITY FIX P1-005: Log warning on audit failure instead of silent pass
    try:
        supabase.table("pms_audit_log").insert({
            "yacht_id": params["yacht_id"],
            "action": "delete_document",
            "entity_type": "document",
            "entity_id": params["document_id"],
            "user_id": params["user_id"],
            "old_values": {"deleted_at": None},
            "new_values": {"deleted_at": result.data[0].get("deleted_at")},
            "created_at": datetime.utcnow().isoformat(),
        }).execute()
    except Exception as e:
        logger.warning(f"Audit log failed for delete_document (document_id={params['document_id']}): {e}")

    return {
        "document_id": params["document_id"],
        "filename": doc.get("filename"),
        "deleted_at": result.data[0].get("deleted_at"),
        "deleted_by": params["user_id"],
    }


async def delete_shopping_item(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Delete a shopping list item.

    Required params:
        - yacht_id: UUID
        - item_id: UUID
        - user_id: UUID (from JWT)
    """
    supabase = get_supabase_client()

    # Verify item exists and belongs to yacht
    item_result = supabase.table("pms_shopping_list_items").select(
        "id, part_name, status"
    ).eq("id", params["item_id"]).eq("yacht_id", params["yacht_id"]).execute()

    if not item_result.data:
        raise ValueError(f"Shopping item {params['item_id']} not found or access denied")

    item = item_result.data[0]

    # Don't allow deletion of ordered items
    if item.get("status") in ("ordered", "partially_fulfilled", "installed"):
        raise ValueError(f"Cannot delete item with status '{item.get('status')}'")

    # Hard delete the item
    result = supabase.table("pms_shopping_list_items").delete().eq(
        "id", params["item_id"]
    ).eq("yacht_id", params["yacht_id"]).execute()

    # Create audit log
    # SECURITY FIX P1-005: Log warning on audit failure instead of silent pass
    try:
        supabase.table("pms_audit_log").insert({
            "yacht_id": params["yacht_id"],
            "action": "delete_shopping_item",
            "entity_type": "shopping_item",
            "entity_id": params["item_id"],
            "user_id": params["user_id"],
            "old_values": {"part_name": item.get("part_name"), "status": item.get("status")},
            "new_values": None,
            "created_at": datetime.utcnow().isoformat(),
        }).execute()
    except Exception as e:
        logger.warning(f"Audit log failed for delete_shopping_item (item_id={params['item_id']}): {e}")

    return {
        "item_id": params["item_id"],
        "part_name": item.get("part_name"),
        "deleted": True,
        "deleted_by": params["user_id"],
    }


# ============================================================================
# FAULT HANDLERS
# ============================================================================


async def report_fault(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Report a new fault (Fault Lens v1).

    Required params:
        - yacht_id: UUID
        - user_id: UUID (from JWT)
        - equipment_id: UUID (fault MUST be attached to equipment)
        - title: str

    Optional params:
        - severity: str (cosmetic, minor, major, critical, safety) - default: minor
        - description: str

    Returns:
        - fault_id: UUID
        - fault_code: str (e.g., FLT-2026-000001)
        - status: str
        - audit_log_id: UUID
        - handover_item_id: UUID (if severity=critical/safety)
        - next_actions: List[str]

    Fault Lens v1: All crew can report faults they observe.
    Equipment is REQUIRED - every fault must be attached to equipment.
    """
    import uuid as uuid_lib
    supabase = get_supabase_client()

    # Extract required fields
    yacht_id = params["yacht_id"]
    user_id = params["user_id"]
    equipment_id = params.get("equipment_id")
    title = params.get("title")

    # Validate required fields
    if not equipment_id:
        raise ValueError("equipment_id is required - faults must be attached to equipment")
    if not title:
        raise ValueError("title is required")

    severity = params.get("severity", "minor")
    description = params.get("description", "")

    # Validate severity
    valid_severities = ['cosmetic', 'minor', 'major', 'critical', 'safety']
    if severity not in valid_severities:
        raise ValueError(f"Severity must be one of: {', '.join(valid_severities)}")

    # SECURITY FIX P1-003: Verify equipment belongs to yacht before INSERT
    equipment_name = None
    eq_result = supabase.table("pms_equipment").select("id, name").eq(
        "id", equipment_id
    ).eq("yacht_id", yacht_id).execute()

    if not eq_result.data:
        raise ValueError(f"Equipment {equipment_id} not found or access denied")

    equipment_name = eq_result.data[0]["name"]

    # Generate fault_code (FLT-2026-000001 format) - matches schema
    year = datetime.utcnow().year
    count_result = supabase.table("pms_faults").select(
        "id", count="exact"
    ).eq("yacht_id", yacht_id).gte(
        "created_at", f"{year}-01-01"
    ).execute()
    count = (count_result.count or 0) + 1
    fault_code = f"FLT-{year}-{count:06d}"

    # Create fault record - using ACTUAL schema columns
    fault_id = str(uuid_lib.uuid4())
    now = datetime.utcnow().isoformat()
    fault_data = {
        "id": fault_id,
        "yacht_id": yacht_id,
        "equipment_id": equipment_id,
        "fault_code": fault_code,  # Use fault_code (actual column) not fault_number
        "title": title,
        "description": description,
        "severity": severity,
        "status": "open",
        "detected_at": now,  # Use detected_at (actual column) not reported_at
        "metadata": {
            "reported_by": user_id,
            "source": "fault_lens",
        },
        "created_at": now,
        "updated_at": now,
    }

    result = supabase.table("pms_faults").insert(fault_data).execute()

    if not result.data:
        raise Exception("Failed to create fault")

    fault = result.data[0]

    # P1-005: Create audit log entry with signature invariant
    audit_log_id = None
    try:
        audit_id = str(uuid_lib.uuid4())
        audit_data = {
            "id": audit_id,
            "yacht_id": yacht_id,
            "action": "report_fault",
            "entity_type": "fault",
            "entity_id": fault_id,
            "user_id": user_id,
            "old_values": None,
            "new_values": {
                "fault_code": fault_code,
                "title": title,
                "severity": severity,
                "equipment_id": equipment_id,
            },
            "signature": {},  # Non-signed action - empty object NOT NULL
            "metadata": {"source": "fault_lens"},
            "created_at": now,
        }
        audit_result = supabase.table("pms_audit_log").insert(audit_data).execute()
        if audit_result.data:
            audit_log_id = audit_result.data[0]["id"]
    except Exception as e:
        logger.warning(f"Audit log failed for report_fault: {e}")

    # If critical/safety, add to handover (PHASE 13 REQUIREMENT)
    handover_item_id = None
    if severity in ('critical', 'safety'):
        try:
            # Try dash_handover_items table (newer schema)
            handover_item_data = {
                "id": str(uuid_lib.uuid4()),
                "yacht_id": yacht_id,
                "source_type": "fault",
                "source_id": fault_id,
                "title": f"{severity.upper()}: {title}",
                "description": description[:200] if description else None,
                "priority": "high" if severity == "critical" else "urgent",
                "status": "pending",
                "created_at": now,
                "updated_at": now,
            }
            item_result = supabase.table("dash_handover_items").insert(handover_item_data).execute()
            if item_result.data:
                handover_item_id = item_result.data[0]["id"]
        except Exception as e:
            logger.warning(f"Failed to add fault to handover: {e}")

    # Build response
    message = f"Fault {fault_code} reported"
    if handover_item_id:
        message += " (added to handover)"

    return {
        "status": "success",
        "fault_id": fault_id,
        "fault_code": fault_code,  # Use fault_code (actual column)
        "title": title,
        "severity": severity,
        "equipment_id": equipment_id,
        "equipment_name": equipment_name,
        "created_at": fault["created_at"],
        "audit_log_id": audit_log_id,
        "handover_item_id": handover_item_id,
        "next_actions": [
            "add_fault_note",
            "add_fault_photo",
            "create_work_order_from_fault"
        ],
        "message": message,
    }


async def close_fault(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Close a fault.

    Required params:
        - yacht_id: UUID
        - fault_id: UUID
        - user_id: UUID (from JWT)
    """
    supabase = get_supabase_client()

    result = supabase.table("pms_faults").update({
        "status": "closed",
        "resolved_at": datetime.utcnow().isoformat(),
        "resolved_by": params["user_id"],
    }).eq("id", params["fault_id"]).eq("yacht_id", params["yacht_id"]).execute()

    if not result.data:
        raise ValueError(f"Fault {params['fault_id']} not found or access denied")

    return {
        "fault_id": params["fault_id"],
        "status": "closed",
        "resolved_at": result.data[0].get("resolved_at"),
    }


async def update_fault(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Update a fault.

    Required params:
        - yacht_id: UUID
        - fault_id: UUID
        - user_id: UUID (from JWT)
    """
    supabase = get_supabase_client()

    update_data = {"updated_at": datetime.utcnow().isoformat()}
    if "description" in params:
        update_data["description"] = params["description"]
    if "priority" in params:
        update_data["priority"] = params["priority"]
    if "status" in params:
        update_data["status"] = params["status"]

    result = supabase.table("pms_faults").update(update_data).eq(
        "id", params["fault_id"]
    ).eq("yacht_id", params["yacht_id"]).execute()

    if not result.data:
        raise ValueError(f"Fault {params['fault_id']} not found or access denied")

    return {
        "fault_id": params["fault_id"],
        "updated": True,
        "updated_at": update_data["updated_at"],
    }


async def add_fault_photo(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Add a photo to a fault.

    Required params:
        - yacht_id: UUID
        - fault_id: UUID
        - photo_url: str
        - user_id: UUID (from JWT)
    """
    import uuid as uuid_lib
    supabase = get_supabase_client()

    # Verify fault exists
    fault_result = supabase.table("pms_faults").select("id").eq(
        "id", params["fault_id"]
    ).eq("yacht_id", params["yacht_id"]).execute()

    if not fault_result.data:
        raise ValueError(f"Fault {params['fault_id']} not found or access denied")

    # Add attachment
    attachment_id = str(uuid_lib.uuid4())
    attachment_data = {
        "id": attachment_id,
        "entity_type": "fault",
        "entity_id": params["fault_id"],
        "storage_path": params["photo_url"],
        "filename": params.get("filename", "photo.jpg"),
        "mime_type": "image/jpeg",
        "uploaded_by": params["user_id"],
        "uploaded_at": datetime.utcnow().isoformat(),
    }

    result = supabase.table("attachments").insert(attachment_data).execute()

    return {
        "attachment_id": attachment_id,
        "fault_id": params["fault_id"],
        "photo_url": params["photo_url"],
    }


async def view_fault_detail(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    View fault detail.

    Required params:
        - yacht_id: UUID
        - fault_id: UUID
    """
    supabase = get_supabase_client()

    result = supabase.table("pms_faults").select("*").eq(
        "id", params["fault_id"]
    ).eq("yacht_id", params["yacht_id"]).execute()

    if not result.data:
        raise ValueError(f"Fault {params['fault_id']} not found or access denied")

    return result.data[0]


async def diagnose_fault(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Diagnose a fault.

    Required params:
        - yacht_id: UUID
        - fault_id: UUID
    """
    supabase = get_supabase_client()

    # Get fault details
    fault_result = supabase.table("pms_faults").select("*").eq(
        "id", params["fault_id"]
    ).eq("yacht_id", params["yacht_id"]).execute()

    if not fault_result.data:
        raise ValueError(f"Fault {params['fault_id']} not found or access denied")

    fault = fault_result.data[0]

    return {
        "fault_id": params["fault_id"],
        "fault": fault,
        "diagnosis": {
            "findings": [],
            "finding_count": 0
        },
        "remedies": {
            "suggested_actions": [],
            "remedy_count": 0
        }
    }


async def view_fault_history(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    View fault history for an entity.

    Required params:
        - yacht_id: UUID
        - entity_id: UUID
    """
    supabase = get_supabase_client()

    result = supabase.table("pms_faults").select("*").eq(
        "yacht_id", params["yacht_id"]
    ).or_(
        f"id.eq.{params['entity_id']},equipment_id.eq.{params['entity_id']}"
    ).order("created_at", desc=True).limit(50).execute()

    return {
        "entity_id": params["entity_id"],
        "faults": result.data or [],
        "total": len(result.data or [])
    }


async def suggest_parts(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Suggest parts for a fault.

    Required params:
        - yacht_id: UUID
        - fault_id: UUID
    """
    supabase = get_supabase_client()

    # Get fault details
    fault_result = supabase.table("pms_faults").select("*").eq(
        "id", params["fault_id"]
    ).eq("yacht_id", params["yacht_id"]).execute()

    if not fault_result.data:
        raise ValueError(f"Fault {params['fault_id']} not found or access denied")

    return {
        "fault_id": params["fault_id"],
        "suggested_parts": [],
        "summary": {
            "total_suggested": 0,
            "available": 0,
            "unavailable": 0
        }
    }


async def show_manual_section(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Show manual section for equipment.

    Required params:
        - yacht_id: UUID
        - equipment_id: UUID
    """
    return {
        "equipment_id": params["equipment_id"],
        "manual_sections": [],
        "message": "No manual sections found"
    }


async def add_fault_note(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Add a note to a fault.

    Required params:
        - yacht_id: UUID
        - fault_id: UUID
        - text: str (note content)
        - user_id: UUID (from JWT)

    Optional params:
        - note_type: str (general, observation, warning, resolution, handover)

    Fault Lens v1: All crew can add notes to faults.
    """
    import uuid as uuid_lib
    supabase = get_supabase_client()

    yacht_id = params["yacht_id"]
    fault_id = params["fault_id"]
    user_id = params["user_id"]
    text = params.get("text") or params.get("note")  # Support both param names
    note_type = params.get("note_type", "observation")

    if not text:
        raise ValueError("Note text is required")

    # P1-003: Verify fault exists and belongs to yacht
    fault_result = supabase.table("pms_faults").select("id, title").eq(
        "id", fault_id
    ).eq("yacht_id", yacht_id).execute()

    if not fault_result.data:
        raise ValueError(f"Fault {fault_id} not found or access denied")

    note_id = str(uuid_lib.uuid4())
    now = datetime.utcnow().isoformat()

    # Insert note into pms_notes (correct table)
    note_data = {
        "id": note_id,
        "yacht_id": yacht_id,
        "fault_id": fault_id,
        "text": text,
        "note_type": note_type,
        "created_by": user_id,
        "created_at": now,
        "updated_at": now,
    }

    result = supabase.table("pms_notes").insert(note_data).execute()

    if not result.data:
        raise Exception("Failed to insert note")

    # P1-005: Audit log with signature invariant
    try:
        audit_id = str(uuid_lib.uuid4())
        supabase.table("pms_audit_log").insert({
            "id": audit_id,
            "yacht_id": yacht_id,
            "entity_type": "note",
            "entity_id": note_id,
            "action": "add_fault_note",
            "user_id": user_id,
            "old_values": None,
            "new_values": {
                "fault_id": fault_id,
                "text": text[:200] if len(text) > 200 else text,  # Truncate for audit
                "note_type": note_type,
            },
            "signature": {},  # Non-signed action - empty object NOT NULL
            "metadata": {"source": "fault_lens"},
            "created_at": now,
        }).execute()
    except Exception as e:
        logger.warning(f"Audit log failed for add_fault_note: {e}")

    return {
        "note_id": note_id,
        "fault_id": fault_id,
        "created_at": now,
        "message": "Note added successfully",
    }


async def create_work_order_from_fault(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a work order from a fault. SIGNED ACTION.

    Required params:
        - yacht_id: UUID
        - fault_id: UUID
        - user_id: UUID (from JWT)
        - signature: Dict (required for signed action)

    Optional params:
        - priority: str (defaults to fault severity mapping)
        - title: str (defaults to fault title)

    Fault Lens v1: SIGNED action - requires captain/chief_engineer/manager role.
    Updates fault status to 'work_ordered' after WO creation.
    """
    import uuid as uuid_lib
    import hashlib
    supabase = get_supabase_client()

    yacht_id = params["yacht_id"]
    fault_id = params["fault_id"]
    user_id = params["user_id"]
    signature = params.get("signature")

    # Validate signature is provided for signed action
    if not signature:
        raise ValueError("Signature is required for create_work_order_from_fault action")

    # P1-003: Get fault details and verify yacht ownership
    fault_result = supabase.table("pms_faults").select("*").eq(
        "id", fault_id
    ).eq("yacht_id", yacht_id).execute()

    if not fault_result.data:
        raise ValueError(f"Fault {fault_id} not found or access denied")

    fault = fault_result.data[0]

    # Check fault isn't already work_ordered or resolved
    if fault.get("status") in ("work_ordered", "resolved", "closed"):
        raise ValueError(f"Cannot create work order: fault is already {fault.get('status')}")

    # Map fault severity to WO priority
    severity_to_priority = {
        "cosmetic": "routine",
        "minor": "routine",
        "major": "important",
        "critical": "critical",
        "safety": "emergency",
    }
    priority = params.get("priority") or severity_to_priority.get(fault.get("severity"), "important")

    now = datetime.utcnow().isoformat()
    wo_id = str(uuid_lib.uuid4())

    # Create work order
    wo_data = {
        "id": wo_id,
        "yacht_id": yacht_id,
        "equipment_id": fault.get("equipment_id"),
        "fault_id": fault_id,
        "title": params.get("title") or fault.get("title") or f"Fix: {fault.get('description', 'Fault repair')[:100]}",
        "description": fault.get("description"),
        "type": "corrective",
        "priority": priority,
        "status": "planned",
        "created_by": user_id,
        "created_at": now,
        "updated_at": now,
    }

    result = supabase.table("pms_work_orders").insert(wo_data).execute()

    if not result.data:
        raise Exception("Failed to create work order")

    # Update fault status to 'work_ordered' and link WO
    supabase.table("pms_faults").update({
        "status": "work_ordered",
        "work_order_id": wo_id,
        "updated_at": now,
        "updated_by": user_id,
    }).eq("id", fault_id).eq("yacht_id", yacht_id).execute()

    # Build signature payload for audit
    signature_hash = hashlib.sha256(
        f"{user_id}:{fault_id}:{wo_id}:{now}".encode()
    ).hexdigest()

    signature_payload = {
        "user_id": user_id,
        "role_at_signing": signature.get("role_at_signing", "unknown"),
        "signature_type": "create_work_order_from_fault",
        "fault_id": fault_id,
        "work_order_id": wo_id,
        "signature_hash": f"sha256:{signature_hash}",
        "signed_at": now,
    }

    # P1-005: Audit log with SIGNED signature payload
    try:
        audit_id = str(uuid_lib.uuid4())
        supabase.table("pms_audit_log").insert({
            "id": audit_id,
            "yacht_id": yacht_id,
            "entity_type": "work_order",
            "entity_id": wo_id,
            "action": "create_work_order_from_fault",
            "user_id": user_id,
            "old_values": {"fault_status": fault.get("status")},
            "new_values": {
                "work_order_id": wo_id,
                "fault_id": fault_id,
                "fault_status": "work_ordered",
            },
            "signature": signature_payload,  # SIGNED action - full payload
            "metadata": {"source": "fault_lens"},
            "created_at": now,
        }).execute()
    except Exception as e:
        logger.warning(f"Audit log failed for create_work_order_from_fault: {e}")

    return {
        "work_order_id": wo_id,
        "fault_id": fault_id,
        "status": "planned",
        "created_at": now,
        "message": "Work order created from fault",
        "next_actions": ["assign_work_order", "start_work_order"],
    }


async def reopen_fault(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Reopen a closed fault.

    Required params:
        - yacht_id: UUID
        - fault_id: UUID
        - user_id: UUID (from JWT)
    """
    supabase = get_supabase_client()

    result = supabase.table("pms_faults").update({
        "status": "open",
        "resolved_at": None,
        "resolved_by": None,
        "updated_at": datetime.utcnow().isoformat(),
    }).eq("id", params["fault_id"]).eq("yacht_id", params["yacht_id"]).execute()

    if not result.data:
        raise ValueError(f"Fault {params['fault_id']} not found or access denied")

    return {
        "fault_id": params["fault_id"],
        "status": "open",
    }


async def mark_fault_false_alarm(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Mark a fault as a false alarm.

    Required params:
        - yacht_id: UUID
        - fault_id: UUID
        - user_id: UUID (from JWT)
    """
    supabase = get_supabase_client()

    result = supabase.table("pms_faults").update({
        "status": "false_alarm",
        "resolved_at": datetime.utcnow().isoformat(),
        "resolved_by": params["user_id"],
    }).eq("id", params["fault_id"]).eq("yacht_id", params["yacht_id"]).execute()

    if not result.data:
        raise ValueError(f"Fault {params['fault_id']} not found or access denied")

    return {
        "fault_id": params["fault_id"],
        "status": "false_alarm",
    }


async def acknowledge_fault(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Acknowledge a fault.

    Required params:
        - yacht_id: UUID
        - fault_id: UUID
        - user_id: UUID (from JWT)
    """
    supabase = get_supabase_client()

    result = supabase.table("pms_faults").update({
        "acknowledged_at": datetime.utcnow().isoformat(),
        "acknowledged_by": params["user_id"],
    }).eq("id", params["fault_id"]).eq("yacht_id", params["yacht_id"]).execute()

    if not result.data:
        raise ValueError(f"Fault {params['fault_id']} not found or access denied")

    return {
        "fault_id": params["fault_id"],
        "acknowledged": True,
    }


async def classify_fault(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Classify a fault.

    Required params:
        - yacht_id: UUID
        - fault_id: UUID
        - classification: str
    """
    supabase = get_supabase_client()

    result = supabase.table("pms_faults").update({
        "classification": params["classification"],
        "updated_at": datetime.utcnow().isoformat(),
    }).eq("id", params["fault_id"]).eq("yacht_id", params["yacht_id"]).execute()

    if not result.data:
        raise ValueError(f"Fault {params['fault_id']} not found or access denied")

    return {
        "fault_id": params["fault_id"],
        "classification": params["classification"],
    }


# ============================================================================
# WORK ORDER HANDLERS
# ============================================================================


async def update_work_order(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Update a work order.

    Required params:
        - yacht_id: UUID
        - work_order_id: UUID
        - user_id: UUID (from JWT)
    """
    supabase = get_supabase_client()

    update_data = {"updated_at": datetime.utcnow().isoformat()}
    if "title" in params:
        update_data["title"] = params["title"]
    if "description" in params:
        update_data["description"] = params["description"]
    if "priority" in params:
        update_data["priority"] = params["priority"]
    if "status" in params:
        update_data["status"] = params["status"]

    result = supabase.table("pms_work_orders").update(update_data).eq(
        "id", params["work_order_id"]
    ).eq("yacht_id", params["yacht_id"]).execute()

    if not result.data:
        raise ValueError(f"Work order {params['work_order_id']} not found or access denied")

    return {
        "work_order_id": params["work_order_id"],
        "updated": True,
        "updated_at": update_data["updated_at"],
    }


async def assign_work_order(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Assign a work order to a user.

    Required params:
        - yacht_id: UUID
        - work_order_id: UUID
        - assignee_id or assigned_to: UUID
        - user_id: UUID (from JWT)
    """
    supabase = get_supabase_client()

    assignee = params.get("assignee_id") or params.get("assigned_to")

    result = supabase.table("pms_work_orders").update({
        "assigned_to": assignee,
        "updated_at": datetime.utcnow().isoformat(),
    }).eq("id", params["work_order_id"]).eq("yacht_id", params["yacht_id"]).execute()

    if not result.data:
        raise ValueError(f"Work order {params['work_order_id']} not found or access denied")

    return {
        "work_order_id": params["work_order_id"],
        "assigned_to": assignee,
    }


async def add_wo_hours(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Add hours to a work order.

    Required params:
        - yacht_id: UUID
        - work_order_id: UUID
        - hours: float
        - user_id: UUID (from JWT)
    """
    import uuid as uuid_lib
    supabase = get_supabase_client()

    # Verify work order exists
    wo_result = supabase.table("pms_work_orders").select("id, hours_logged").eq(
        "id", params["work_order_id"]
    ).eq("yacht_id", params["yacht_id"]).execute()

    if not wo_result.data:
        raise ValueError(f"Work order {params['work_order_id']} not found or access denied")

    current_hours = wo_result.data[0].get("hours_logged", 0) or 0
    new_hours = current_hours + params["hours"]

    # Update total hours
    supabase.table("pms_work_orders").update({
        "hours_logged": new_hours,
        "updated_at": datetime.utcnow().isoformat(),
    }).eq("id", params["work_order_id"]).execute()

    return {
        "work_order_id": params["work_order_id"],
        "hours_added": params["hours"],
        "total_hours": new_hours,
    }


async def add_wo_part(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Add a part to a work order.

    Required params:
        - yacht_id: UUID
        - work_order_id: UUID
        - part_id: UUID
        - user_id: UUID (from JWT)
    """
    import uuid as uuid_lib
    supabase = get_supabase_client()

    link_id = str(uuid_lib.uuid4())
    link_data = {
        "id": link_id,
        "work_order_id": params["work_order_id"],
        "part_id": params["part_id"],
        "quantity": params.get("quantity", 1),
        "added_by": params["user_id"],
        "added_at": datetime.utcnow().isoformat(),
    }

    result = supabase.table("work_order_parts").insert(link_data).execute()

    return {
        "link_id": link_id,
        "work_order_id": params["work_order_id"],
        "part_id": params["part_id"],
    }


async def add_wo_note(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Add a note to a work order.

    Required params:
        - yacht_id: UUID
        - work_order_id: UUID
        - note_text: str
        - user_id: UUID (from JWT)
    """
    # Reuse the existing add_note_to_work_order handler
    return await add_note_to_work_order(params)


async def start_work_order(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Start a work order (change status to in_progress).

    Required params:
        - yacht_id: UUID
        - work_order_id: UUID
        - user_id: UUID (from JWT)
    """
    supabase = get_supabase_client()

    result = supabase.table("pms_work_orders").update({
        "status": "in_progress",
        "started_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
    }).eq("id", params["work_order_id"]).eq("yacht_id", params["yacht_id"]).execute()

    if not result.data:
        raise ValueError(f"Work order {params['work_order_id']} not found or access denied")

    return {
        "work_order_id": params["work_order_id"],
        "status": "in_progress",
    }


async def cancel_work_order(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Cancel a work order.

    Required params:
        - yacht_id: UUID
        - work_order_id: UUID
        - user_id: UUID (from JWT)
    """
    supabase = get_supabase_client()

    result = supabase.table("pms_work_orders").update({
        "status": "cancelled",
        "cancelled_at": datetime.utcnow().isoformat(),
        "cancel_reason": params.get("reason", "Cancelled by user"),
        "updated_at": datetime.utcnow().isoformat(),
    }).eq("id", params["work_order_id"]).eq("yacht_id", params["yacht_id"]).execute()

    if not result.data:
        raise ValueError(f"Work order {params['work_order_id']} not found or access denied")

    return {
        "work_order_id": params["work_order_id"],
        "status": "cancelled",
    }


async def create_work_order(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a new work order.

    Required params:
        - yacht_id: UUID
        - title: str
        - user_id: UUID (from JWT)
    """
    import uuid as uuid_lib
    supabase = get_supabase_client()

    wo_id = str(uuid_lib.uuid4())
    wo_data = {
        "id": wo_id,
        "yacht_id": params["yacht_id"],
        "title": params["title"],
        "description": params.get("description", ""),
        "priority": params.get("priority", "medium"),
        "equipment_id": params.get("equipment_id"),
        "status": "open",
        "created_by": params["user_id"],
        "created_at": datetime.utcnow().isoformat(),
    }

    result = supabase.table("pms_work_orders").insert(wo_data).execute()

    if not result.data:
        raise Exception("Failed to create work order")

    return {
        "work_order_id": wo_id,
        "status": "open",
        "created_at": wo_data["created_at"],
    }


async def view_work_order_detail(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    View work order detail.

    Required params:
        - yacht_id: UUID
        - work_order_id: UUID
    """
    supabase = get_supabase_client()

    result = supabase.table("pms_work_orders").select("*").eq(
        "id", params["work_order_id"]
    ).eq("yacht_id", params["yacht_id"]).execute()

    if not result.data:
        raise ValueError(f"Work order {params['work_order_id']} not found or access denied")

    return result.data[0]


async def add_work_order_photo(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Add a photo to a work order.

    Required params:
        - yacht_id: UUID
        - work_order_id: UUID
        - photo_url: str
        - user_id: UUID (from JWT)
    """
    import uuid as uuid_lib
    supabase = get_supabase_client()

    attachment_id = str(uuid_lib.uuid4())
    attachment_data = {
        "id": attachment_id,
        "entity_type": "work_order",
        "entity_id": params["work_order_id"],
        "storage_path": params["photo_url"],
        "filename": params.get("filename", "photo.jpg"),
        "mime_type": "image/jpeg",
        "uploaded_by": params["user_id"],
        "uploaded_at": datetime.utcnow().isoformat(),
    }

    result = supabase.table("attachments").insert(attachment_data).execute()

    return {
        "attachment_id": attachment_id,
        "work_order_id": params["work_order_id"],
        "photo_url": params["photo_url"],
    }


async def add_parts_to_work_order(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Add parts to a work order.

    Required params:
        - yacht_id: UUID
        - work_order_id: UUID
        - part_id: UUID
        - user_id: UUID (from JWT)
    """
    return await add_wo_part(params)


async def view_work_order_checklist(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    View work order checklist.

    Required params:
        - yacht_id: UUID
        - work_order_id: UUID
    """
    supabase = get_supabase_client()

    result = supabase.table("checklist_items").select("*").eq(
        "work_order_id", params["work_order_id"]
    ).order("sequence").execute()

    items = result.data or []
    completed = len([i for i in items if i.get("is_completed")])

    return {
        "work_order_id": params["work_order_id"],
        "checklist": items,
        "progress": {
            "completed": completed,
            "total": len(items),
            "percent": round((completed / len(items) * 100) if items else 0, 1)
        }
    }


# ============================================================================
# WORKLIST HANDLERS
# ============================================================================


async def view_worklist(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    View worklist tasks.

    Required params:
        - yacht_id: UUID
    """
    supabase = get_supabase_client()

    result = supabase.table("worklist_tasks").select("*").eq(
        "yacht_id", params["yacht_id"]
    ).order("created_at", desc=True).execute()

    return {
        "tasks": result.data or [],
        "total": len(result.data or [])
    }


async def add_worklist_task(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Add a task to the worklist.

    Required params:
        - yacht_id: UUID
        - task_description: str
        - user_id: UUID (from JWT)
    """
    import uuid as uuid_lib
    supabase = get_supabase_client()

    task_id = str(uuid_lib.uuid4())
    task_data = {
        "id": task_id,
        "yacht_id": params["yacht_id"],
        "description": params["task_description"],
        "status": "pending",
        "created_by": params["user_id"],
        "created_at": datetime.utcnow().isoformat(),
    }

    result = supabase.table("worklist_tasks").insert(task_data).execute()

    return {
        "task_id": task_id,
        "status": "pending",
    }


async def export_worklist(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Export worklist to a format.

    Required params:
        - yacht_id: UUID
    """
    supabase = get_supabase_client()

    result = supabase.table("worklist_tasks").select("*").eq(
        "yacht_id", params["yacht_id"]
    ).execute()

    return {
        "tasks": result.data or [],
        "export_format": "json",
        "exported_at": datetime.utcnow().isoformat()
    }


# ============================================================================
# P3 READ-ONLY WRAPPER FUNCTIONS
# ============================================================================


async def _view_document(params: Dict[str, Any]) -> Dict[str, Any]:
    """Wrapper for P3 view_document handler."""
    handlers = _get_p3_handlers()
    return await handlers.view_document_execute(
        document_id=params.get("document_id") or params.get("entity_id"),
        yacht_id=params["yacht_id"]
    )


async def _view_related_documents(params: Dict[str, Any]) -> Dict[str, Any]:
    """Wrapper for P3 view_related_documents handler."""
    handlers = _get_p3_handlers()
    return await handlers.view_related_documents_execute(
        entity_id=params.get("entity_id"),
        entity_type=params.get("entity_type"),
        yacht_id=params["yacht_id"]
    )


async def _view_document_section(params: Dict[str, Any]) -> Dict[str, Any]:
    """Wrapper for P3 view_document_section handler."""
    handlers = _get_p3_handlers()
    return await handlers.view_document_section_execute(
        document_id=params.get("document_id"),
        section_id=params.get("section_id"),
        yacht_id=params["yacht_id"]
    )


async def _view_work_order_history(params: Dict[str, Any]) -> Dict[str, Any]:
    """Wrapper for P3 view_work_order_history handler."""
    handlers = _get_p3_handlers()
    return await handlers.view_work_order_history_execute(
        work_order_id=params.get("work_order_id") or params.get("entity_id"),
        yacht_id=params["yacht_id"]
    )


async def _view_checklist(params: Dict[str, Any]) -> Dict[str, Any]:
    """Wrapper for P3 view_checklist handler."""
    handlers = _get_p3_handlers()
    return await handlers.view_checklist_execute(
        checklist_id=params.get("checklist_id") or params.get("entity_id"),
        yacht_id=params["yacht_id"]
    )


async def _view_equipment_details(params: Dict[str, Any]) -> Dict[str, Any]:
    """Wrapper for P3 view_equipment_details handler."""
    handlers = _get_p3_handlers()
    return await handlers.view_equipment_details_execute(
        equipment_id=params.get("equipment_id") or params.get("entity_id"),
        yacht_id=params["yacht_id"]
    )


async def _view_equipment_history(params: Dict[str, Any]) -> Dict[str, Any]:
    """Wrapper for P3 view_equipment_history handler."""
    handlers = _get_p3_handlers()
    return await handlers.view_equipment_history_execute(
        equipment_id=params.get("equipment_id") or params.get("entity_id"),
        yacht_id=params["yacht_id"]
    )


async def _view_equipment_parts(params: Dict[str, Any]) -> Dict[str, Any]:
    """Wrapper for P3 view_equipment_parts handler."""
    handlers = _get_p3_handlers()
    return await handlers.view_equipment_parts_execute(
        equipment_id=params.get("equipment_id") or params.get("entity_id"),
        yacht_id=params["yacht_id"]
    )


async def _view_linked_faults(params: Dict[str, Any]) -> Dict[str, Any]:
    """Wrapper for P3 view_linked_faults handler."""
    handlers = _get_p3_handlers()
    return await handlers.view_linked_faults_execute(
        equipment_id=params.get("equipment_id") or params.get("entity_id"),
        yacht_id=params["yacht_id"]
    )


async def _view_equipment_manual(params: Dict[str, Any]) -> Dict[str, Any]:
    """Wrapper for P3 view_equipment_manual handler."""
    handlers = _get_p3_handlers()
    return await handlers.view_equipment_manual_execute(
        equipment_id=params.get("equipment_id") or params.get("entity_id"),
        yacht_id=params["yacht_id"]
    )


async def _view_fleet_summary(params: Dict[str, Any]) -> Dict[str, Any]:
    """Wrapper for P3 view_fleet_summary handler."""
    handlers = _get_p3_handlers()
    return await handlers.view_fleet_summary_execute(
        yacht_id=params["yacht_id"]
    )


async def _open_vessel(params: Dict[str, Any]) -> Dict[str, Any]:
    """Wrapper for P3 open_vessel handler."""
    handlers = _get_p3_handlers()
    return await handlers.open_vessel_execute(
        vessel_id=params.get("vessel_id") or params.get("entity_id"),
        yacht_id=params["yacht_id"]
    )


async def _export_fleet_summary(params: Dict[str, Any]) -> Dict[str, Any]:
    """Wrapper for P3 export_fleet_summary handler."""
    handlers = _get_p3_handlers()
    return await handlers.export_fleet_summary_execute(
        yacht_id=params["yacht_id"],
        format=params.get("format", "pdf")
    )


async def _request_predictive_insight(params: Dict[str, Any]) -> Dict[str, Any]:
    """Wrapper for P3 request_predictive_insight handler."""
    handlers = _get_p3_handlers()
    return await handlers.request_predictive_insight_execute(
        equipment_id=params.get("equipment_id") or params.get("entity_id"),
        yacht_id=params["yacht_id"]
    )


async def _view_part_stock(params: Dict[str, Any]) -> Dict[str, Any]:
    """Wrapper for P3 view_part_stock handler."""
    handlers = _get_p3_handlers()
    return await handlers.view_part_stock_execute(
        part_id=params.get("part_id") or params.get("entity_id"),
        yacht_id=params["yacht_id"]
    )


async def _view_part_location(params: Dict[str, Any]) -> Dict[str, Any]:
    """Wrapper for P3 view_part_location handler."""
    handlers = _get_p3_handlers()
    return await handlers.view_part_location_execute(
        part_id=params.get("part_id") or params.get("entity_id"),
        yacht_id=params["yacht_id"]
    )


async def _view_part_usage(params: Dict[str, Any]) -> Dict[str, Any]:
    """Wrapper for P3 view_part_usage handler."""
    handlers = _get_p3_handlers()
    return await handlers.view_part_usage_execute(
        part_id=params.get("part_id") or params.get("entity_id"),
        yacht_id=params["yacht_id"]
    )


async def _scan_part_barcode(params: Dict[str, Any]) -> Dict[str, Any]:
    """Wrapper for P3 scan_part_barcode handler."""
    handlers = _get_p3_handlers()
    return await handlers.scan_part_barcode_execute(
        barcode=params.get("barcode"),
        yacht_id=params["yacht_id"]
    )


async def _view_linked_equipment(params: Dict[str, Any]) -> Dict[str, Any]:
    """Wrapper for P3 view_linked_equipment handler."""
    handlers = _get_p3_handlers()
    return await handlers.view_linked_equipment_execute(
        part_id=params.get("part_id") or params.get("entity_id"),
        yacht_id=params["yacht_id"]
    )


async def _export_handover(params: Dict[str, Any]) -> Dict[str, Any]:
    """Wrapper for P3 export_handover handler."""
    handlers = _get_p3_handlers()
    return await handlers.export_handover_execute(
        handover_id=params.get("handover_id") or params.get("entity_id"),
        yacht_id=params["yacht_id"],
        format=params.get("format", "pdf")
    )


async def _view_smart_summary(params: Dict[str, Any]) -> Dict[str, Any]:
    """Wrapper for P3 view_smart_summary handler."""
    handlers = _get_p3_handlers()
    return await handlers.view_smart_summary_execute(
        yacht_id=params["yacht_id"],
        period=params.get("period", "today")
    )


async def _view_hours_of_rest(params: Dict[str, Any]) -> Dict[str, Any]:
    """Wrapper for P3 view_hours_of_rest handler."""
    handlers = _get_p3_handlers()
    return await handlers.view_hours_of_rest_execute(
        crew_id=params.get("crew_id") or params.get("entity_id"),
        yacht_id=params["yacht_id"],
        date_from=params.get("date_from"),
        date_to=params.get("date_to")
    )


async def _export_hours_of_rest(params: Dict[str, Any]) -> Dict[str, Any]:
    """Wrapper for P3 export_hours_of_rest handler."""
    handlers = _get_p3_handlers()
    return await handlers.export_hours_of_rest_execute(
        crew_id=params.get("crew_id") or params.get("entity_id"),
        yacht_id=params["yacht_id"],
        format=params.get("format", "pdf")
    )


async def _view_compliance_status(params: Dict[str, Any]) -> Dict[str, Any]:
    """Wrapper for P3 view_compliance_status handler."""
    handlers = _get_p3_handlers()
    return await handlers.view_compliance_status_execute(
        yacht_id=params["yacht_id"]
    )


async def _track_delivery(params: Dict[str, Any]) -> Dict[str, Any]:
    """Wrapper for P3 track_delivery handler."""
    handlers = _get_p3_handlers()
    return await handlers.track_delivery_execute(
        order_id=params.get("order_id") or params.get("entity_id"),
        yacht_id=params["yacht_id"]
    )


# ============================================================================
# P1 COMPLIANCE WRAPPER FUNCTIONS
# ============================================================================


async def _update_hours_of_rest(params: Dict[str, Any]) -> Dict[str, Any]:
    """Wrapper for P1 update_hours_of_rest handler."""
    handlers = _get_p1_compliance_handlers()
    return await handlers.update_hours_of_rest_execute(
        crew_id=params.get("crew_id") or params.get("entity_id"),
        yacht_id=params["yacht_id"],
        date=params.get("date"),
        rest_hours=params.get("rest_hours"),
        work_hours=params.get("work_hours"),
        notes=params.get("notes")
    )


async def _log_delivery_received(params: Dict[str, Any]) -> Dict[str, Any]:
    """Wrapper for P1 log_delivery_received handler."""
    handlers = _get_p1_compliance_handlers()
    return await handlers.log_delivery_received_execute(
        order_id=params.get("order_id") or params.get("entity_id"),
        yacht_id=params["yacht_id"],
        received_by=params.get("received_by") or params.get("user_id"),
        received_items=params.get("received_items"),
        notes=params.get("notes")
    )


# ============================================================================
# P1 PURCHASING WRAPPER FUNCTIONS
# ============================================================================


async def _create_purchase_request(params: Dict[str, Any]) -> Dict[str, Any]:
    """Wrapper for P1 create_purchase_request handler."""
    handlers = _get_p1_purchasing_handlers()
    return await handlers.create_purchase_request_execute(
        yacht_id=params["yacht_id"],
        user_id=params.get("user_id"),
        items=params.get("items", []),
        supplier_id=params.get("supplier_id"),
        notes=params.get("notes"),
        priority=params.get("priority", "normal")
    )


async def _order_part(params: Dict[str, Any]) -> Dict[str, Any]:
    """Wrapper for P1 order_part handler."""
    handlers = _get_p1_purchasing_handlers()
    return await handlers.order_part_execute(
        part_id=params.get("part_id") or params.get("entity_id"),
        yacht_id=params["yacht_id"],
        user_id=params.get("user_id"),
        quantity=params.get("quantity", 1),
        supplier_id=params.get("supplier_id"),
        notes=params.get("notes")
    )


async def _approve_purchase(params: Dict[str, Any]) -> Dict[str, Any]:
    """Wrapper for P1 approve_purchase handler."""
    handlers = _get_p1_purchasing_handlers()
    return await handlers.approve_purchase_execute(
        purchase_order_id=params.get("purchase_order_id") or params.get("entity_id"),
        yacht_id=params["yacht_id"],
        user_id=params.get("user_id"),
        approval_notes=params.get("approval_notes")
    )


# ============================================================================
# P2 MUTATION LIGHT WRAPPER FUNCTIONS
# ============================================================================


async def _p2_add_checklist_note(params: Dict[str, Any]) -> Dict[str, Any]:
    """Wrapper for P2 add_checklist_note handler."""
    handlers = _get_p2_handlers()
    return await handlers.add_checklist_note_execute(
        checklist_id=params.get("checklist_id") or params.get("entity_id"),
        yacht_id=params["yacht_id"],
        user_id=params.get("user_id"),
        note_text=params.get("note_text") or params.get("note")
    )


async def _p2_add_checklist_photo(params: Dict[str, Any]) -> Dict[str, Any]:
    """Wrapper for P2 add_checklist_photo handler."""
    handlers = _get_p2_handlers()
    return await handlers.add_checklist_photo_execute(
        checklist_id=params.get("checklist_id") or params.get("entity_id"),
        yacht_id=params["yacht_id"],
        user_id=params.get("user_id"),
        photo_url=params.get("photo_url"),
        filename=params.get("filename")
    )


async def _p2_add_document_to_handover(params: Dict[str, Any]) -> Dict[str, Any]:
    """Wrapper for P2 add_document_to_handover handler."""
    handlers = _get_p2_handlers()
    return await handlers.add_document_to_handover_execute(
        handover_id=params.get("handover_id") or params.get("entity_id"),
        yacht_id=params["yacht_id"],
        user_id=params.get("user_id"),
        document_id=params.get("document_id")
    )


async def _p2_add_equipment_note(params: Dict[str, Any]) -> Dict[str, Any]:
    """Wrapper for P2 add_equipment_note handler."""
    handlers = _get_p2_handlers()
    return await handlers.add_equipment_note_execute(
        equipment_id=params.get("equipment_id") or params.get("entity_id"),
        yacht_id=params["yacht_id"],
        user_id=params.get("user_id"),
        note_text=params.get("note_text") or params.get("note")
    )


async def _p2_add_item_to_purchase(params: Dict[str, Any]) -> Dict[str, Any]:
    """Wrapper for P2 add_item_to_purchase handler."""
    handlers = _get_p2_handlers()
    return await handlers.add_item_to_purchase_execute(
        purchase_order_id=params.get("purchase_order_id") or params.get("entity_id"),
        yacht_id=params["yacht_id"],
        user_id=params.get("user_id"),
        part_id=params.get("part_id"),
        quantity=params.get("quantity", 1),
        unit_price=params.get("unit_price")
    )


async def _p2_add_predictive_insight_to_handover(params: Dict[str, Any]) -> Dict[str, Any]:
    """Wrapper for P2 add_predictive_insight_to_handover handler."""
    handlers = _get_p2_handlers()
    return await handlers.add_predictive_insight_to_handover_execute(
        handover_id=params.get("handover_id") or params.get("entity_id"),
        yacht_id=params["yacht_id"],
        user_id=params.get("user_id"),
        insight_id=params.get("insight_id")
    )


async def _p2_add_work_order_note(params: Dict[str, Any]) -> Dict[str, Any]:
    """Wrapper for P2 add_work_order_note handler."""
    handlers = _get_p2_handlers()
    return await handlers.add_work_order_note_execute(
        work_order_id=params.get("work_order_id") or params.get("entity_id"),
        yacht_id=params["yacht_id"],
        user_id=params.get("user_id"),
        note_text=params.get("note_text") or params.get("note")
    )


async def _p2_mark_checklist_item_complete(params: Dict[str, Any]) -> Dict[str, Any]:
    """Wrapper for P2 mark_checklist_item_complete handler."""
    handlers = _get_p2_handlers()
    return await handlers.mark_checklist_item_complete_execute(
        checklist_item_id=params.get("checklist_item_id") or params.get("item_id") or params.get("entity_id"),
        yacht_id=params["yacht_id"],
        user_id=params.get("user_id"),
        notes=params.get("notes")
    )


async def _p2_record_voice_note(params: Dict[str, Any]) -> Dict[str, Any]:
    """Wrapper for P2 record_voice_note handler."""
    handlers = _get_p2_handlers()
    return await handlers.record_voice_note_execute(
        entity_id=params.get("entity_id"),
        entity_type=params.get("entity_type"),
        yacht_id=params["yacht_id"],
        user_id=params.get("user_id"),
        audio_url=params.get("audio_url"),
        duration_seconds=params.get("duration_seconds")
    )


async def _p2_regenerate_handover_summary(params: Dict[str, Any]) -> Dict[str, Any]:
    """Wrapper for P2 regenerate_handover_summary handler."""
    handlers = _get_p2_handlers()
    return await handlers.regenerate_handover_summary_execute(
        handover_id=params.get("handover_id") or params.get("entity_id"),
        yacht_id=params["yacht_id"],
        user_id=params.get("user_id")
    )


async def _p2_tag_for_survey(params: Dict[str, Any]) -> Dict[str, Any]:
    """Wrapper for P2 tag_for_survey handler."""
    handlers = _get_p2_handlers()
    return await handlers.tag_for_survey_execute(
        entity_id=params.get("entity_id"),
        entity_type=params.get("entity_type"),
        yacht_id=params["yacht_id"],
        user_id=params.get("user_id"),
        survey_type=params.get("survey_type")
    )


async def _p2_update_purchase_status(params: Dict[str, Any]) -> Dict[str, Any]:
    """Wrapper for P2 update_purchase_status handler."""
    handlers = _get_p2_handlers()
    return await handlers.update_purchase_status_execute(
        purchase_order_id=params.get("purchase_order_id") or params.get("entity_id"),
        yacht_id=params["yacht_id"],
        user_id=params.get("user_id"),
        new_status=params.get("new_status") or params.get("status")
    )


async def _p2_update_worklist_progress(params: Dict[str, Any]) -> Dict[str, Any]:
    """Wrapper for P2 update_worklist_progress handler."""
    handlers = _get_p2_handlers()
    return await handlers.update_worklist_progress_execute(
        task_id=params.get("task_id") or params.get("entity_id"),
        yacht_id=params["yacht_id"],
        user_id=params.get("user_id"),
        progress_percent=params.get("progress_percent") or params.get("progress")
    )


async def _p2_upload_invoice(params: Dict[str, Any]) -> Dict[str, Any]:
    """Wrapper for P2 upload_invoice handler."""
    handlers = _get_p2_handlers()
    return await handlers.upload_invoice_execute(
        purchase_order_id=params.get("purchase_order_id") or params.get("entity_id"),
        yacht_id=params["yacht_id"],
        user_id=params.get("user_id"),
        invoice_url=params.get("invoice_url"),
        invoice_number=params.get("invoice_number"),
        amount=params.get("amount")
    )


async def _p2_upload_photo(params: Dict[str, Any]) -> Dict[str, Any]:
    """Wrapper for P2 upload_photo handler."""
    handlers = _get_p2_handlers()
    return await handlers.upload_photo_execute(
        entity_id=params.get("entity_id"),
        entity_type=params.get("entity_type"),
        yacht_id=params["yacht_id"],
        user_id=params.get("user_id"),
        photo_url=params.get("photo_url"),
        filename=params.get("filename"),
        description=params.get("description")
    )


# ============================================================================
# EQUIPMENT LENS V2 WRAPPER FUNCTIONS
# ============================================================================


async def _eq_view_equipment(params: Dict[str, Any]) -> Dict[str, Any]:
    """Wrapper for Equipment view_equipment handler."""
    handlers = _get_equipment_handlers()
    fn = handlers.get("view_equipment")
    if not fn:
        raise ValueError("view_equipment handler not registered")
    return await fn(
        entity_id=params.get("equipment_id") or params.get("entity_id"),
        yacht_id=params["yacht_id"],
        params=params
    )


async def _eq_view_maintenance_history(params: Dict[str, Any]) -> Dict[str, Any]:
    """Wrapper for Equipment view_maintenance_history handler."""
    handlers = _get_equipment_handlers()
    fn = handlers.get("view_maintenance_history")
    if not fn:
        raise ValueError("view_maintenance_history handler not registered")
    return await fn(
        entity_id=params.get("equipment_id") or params.get("entity_id"),
        yacht_id=params["yacht_id"],
        params=params
    )


async def _eq_view_equipment_parts(params: Dict[str, Any]) -> Dict[str, Any]:
    """Wrapper for Equipment view_equipment_parts handler."""
    handlers = _get_equipment_handlers()
    fn = handlers.get("view_equipment_parts")
    if not fn:
        raise ValueError("view_equipment_parts handler not registered")
    return await fn(
        entity_id=params.get("equipment_id") or params.get("entity_id"),
        yacht_id=params["yacht_id"],
        params=params
    )


async def _eq_view_linked_faults(params: Dict[str, Any]) -> Dict[str, Any]:
    """Wrapper for Equipment view_linked_faults handler."""
    handlers = _get_equipment_handlers()
    fn = handlers.get("view_linked_faults")
    if not fn:
        raise ValueError("view_linked_faults handler not registered")
    return await fn(
        entity_id=params.get("equipment_id") or params.get("entity_id"),
        yacht_id=params["yacht_id"],
        params=params
    )


async def _eq_view_equipment_manual(params: Dict[str, Any]) -> Dict[str, Any]:
    """Wrapper for Equipment view_equipment_manual handler."""
    handlers = _get_equipment_handlers()
    fn = handlers.get("view_equipment_manual")
    if not fn:
        raise ValueError("view_equipment_manual handler not registered")
    return await fn(
        entity_id=params.get("equipment_id") or params.get("entity_id"),
        yacht_id=params["yacht_id"],
        params=params
    )


async def _eq_update_equipment_status(params: Dict[str, Any]) -> Dict[str, Any]:
    """Wrapper for Equipment update_equipment_status handler."""
    handlers = _get_equipment_handlers()
    fn = handlers.get("update_equipment_status")
    if not fn:
        raise ValueError("update_equipment_status handler not registered")
    return await fn(**params)


async def _eq_add_equipment_note(params: Dict[str, Any]) -> Dict[str, Any]:
    """Wrapper for Equipment add_equipment_note handler."""
    handlers = _get_equipment_handlers()
    fn = handlers.get("add_equipment_note")
    if not fn:
        raise ValueError("add_equipment_note handler not registered")
    return await fn(**params)


async def _eq_attach_file_to_equipment(params: Dict[str, Any]) -> Dict[str, Any]:
    """Wrapper for Equipment attach_file_to_equipment handler."""
    handlers = _get_equipment_handlers()
    fn = handlers.get("attach_file_to_equipment")
    if not fn:
        raise ValueError("attach_file_to_equipment handler not registered")
    return await fn(**params)


async def _eq_create_work_order_for_equipment(params: Dict[str, Any]) -> Dict[str, Any]:
    """Wrapper for Equipment create_work_order_for_equipment handler."""
    handlers = _get_equipment_handlers()
    fn = handlers.get("create_work_order_for_equipment")
    if not fn:
        raise ValueError("create_work_order_for_equipment handler not registered")
    return await fn(**params)


async def _eq_link_part_to_equipment(params: Dict[str, Any]) -> Dict[str, Any]:
    """Wrapper for Equipment link_part_to_equipment handler."""
    handlers = _get_equipment_handlers()
    fn = handlers.get("link_part_to_equipment")
    if not fn:
        raise ValueError("link_part_to_equipment handler not registered")
    return await fn(**params)


async def _eq_flag_equipment_attention(params: Dict[str, Any]) -> Dict[str, Any]:
    """Wrapper for Equipment flag_equipment_attention handler."""
    handlers = _get_equipment_handlers()
    fn = handlers.get("flag_equipment_attention")
    if not fn:
        raise ValueError("flag_equipment_attention handler not registered")
    return await fn(**params)


async def _eq_decommission_equipment(params: Dict[str, Any]) -> Dict[str, Any]:
    """Wrapper for Equipment decommission_equipment handler (SIGNED)."""
    handlers = _get_equipment_handlers()
    fn = handlers.get("decommission_equipment")
    if not fn:
        raise ValueError("decommission_equipment handler not registered")
    return await fn(**params)


async def _eq_record_equipment_hours(params: Dict[str, Any]) -> Dict[str, Any]:
    """Wrapper for Equipment record_equipment_hours handler."""
    handlers = _get_equipment_handlers()
    fn = handlers.get("record_equipment_hours")
    if not fn:
        raise ValueError("record_equipment_hours handler not registered")
    return await fn(**params)


async def _eq_create_equipment(params: Dict[str, Any]) -> Dict[str, Any]:
    """Wrapper for Equipment create_equipment handler."""
    handlers = _get_equipment_handlers()
    fn = handlers.get("create_equipment")
    if not fn:
        raise ValueError("create_equipment handler not registered")
    return await fn(**params)


async def _eq_assign_parent_equipment(params: Dict[str, Any]) -> Dict[str, Any]:
    """Wrapper for Equipment assign_parent_equipment handler."""
    handlers = _get_equipment_handlers()
    fn = handlers.get("assign_parent_equipment")
    if not fn:
        raise ValueError("assign_parent_equipment handler not registered")
    return await fn(**params)


async def _eq_archive_equipment(params: Dict[str, Any]) -> Dict[str, Any]:
    """Wrapper for Equipment archive_equipment handler."""
    handlers = _get_equipment_handlers()
    fn = handlers.get("archive_equipment")
    if not fn:
        raise ValueError("archive_equipment handler not registered")
    return await fn(**params)


async def _eq_restore_archived_equipment(params: Dict[str, Any]) -> Dict[str, Any]:
    """Wrapper for Equipment restore_archived_equipment handler (SIGNED)."""
    handlers = _get_equipment_handlers()
    fn = handlers.get("restore_archived_equipment")
    if not fn:
        raise ValueError("restore_archived_equipment handler not registered")
    return await fn(**params)


async def _eq_get_open_faults_for_equipment(params: Dict[str, Any]) -> Dict[str, Any]:
    """Wrapper for Equipment get_open_faults_for_equipment handler."""
    handlers = _get_equipment_handlers()
    fn = handlers.get("get_open_faults_for_equipment")
    if not fn:
        raise ValueError("get_open_faults_for_equipment handler not registered")
    return await fn(**params)


async def _eq_get_related_entities_for_equipment(params: Dict[str, Any]) -> Dict[str, Any]:
    """Wrapper for Equipment get_related_entities_for_equipment handler."""
    handlers = _get_equipment_handlers()
    fn = handlers.get("get_related_entities_for_equipment")
    if not fn:
        raise ValueError("get_related_entities_for_equipment handler not registered")
    return await fn(**params)


async def _eq_add_entity_link(params: Dict[str, Any]) -> Dict[str, Any]:
    """Wrapper for Equipment add_entity_link handler."""
    handlers = _get_equipment_handlers()
    fn = handlers.get("add_entity_link")
    if not fn:
        raise ValueError("add_entity_link handler not registered")
    return await fn(**params)


async def _eq_link_document_to_equipment(params: Dict[str, Any]) -> Dict[str, Any]:
    """Wrapper for Equipment link_document_to_equipment handler."""
    handlers = _get_equipment_handlers()
    fn = handlers.get("link_document_to_equipment")
    if not fn:
        raise ValueError("link_document_to_equipment handler not registered")
    return await fn(**params)


async def _eq_attach_image_with_comment(params: Dict[str, Any]) -> Dict[str, Any]:
    """Wrapper for Equipment attach_image_with_comment handler."""
    handlers = _get_equipment_handlers()
    fn = handlers.get("attach_image_with_comment")
    if not fn:
        raise ValueError("attach_image_with_comment handler not registered")
    return await fn(**params)


async def _eq_decommission_and_replace(params: Dict[str, Any]) -> Dict[str, Any]:
    """Wrapper for Equipment decommission_and_replace_equipment handler (SIGNED)."""
    handlers = _get_equipment_handlers()
    fn = handlers.get("decommission_and_replace_equipment")
    if not fn:
        raise ValueError("decommission_and_replace_equipment handler not registered")
    return await fn(**params)


# =========================================================================
# Receiving Lens v1 Handlers
# =========================================================================

async def _recv_create_receiving(params: Dict[str, Any]) -> Dict[str, Any]:
    """Wrapper for create_receiving handler."""
    handlers = _get_receiving_handlers()
    fn = handlers.get("create_receiving")
    if not fn:
        raise ValueError("create_receiving handler not registered")
    return await fn(**params)


async def _recv_attach_image_with_comment(params: Dict[str, Any]) -> Dict[str, Any]:
    """Wrapper for attach_receiving_image_with_comment handler."""
    handlers = _get_receiving_handlers()
    fn = handlers.get("attach_receiving_image_with_comment")
    if not fn:
        raise ValueError("attach_receiving_image_with_comment handler not registered")
    return await fn(**params)


async def _recv_extract_candidates(params: Dict[str, Any]) -> Dict[str, Any]:
    """Wrapper for extract_receiving_candidates handler (PREPARE only - advisory)."""
    handlers = _get_receiving_handlers()
    fn = handlers.get("extract_receiving_candidates")
    if not fn:
        raise ValueError("extract_receiving_candidates handler not registered")
    return await fn(**params)


async def _recv_update_fields(params: Dict[str, Any]) -> Dict[str, Any]:
    """Wrapper for update_receiving_fields handler."""
    handlers = _get_receiving_handlers()
    fn = handlers.get("update_receiving_fields")
    if not fn:
        raise ValueError("update_receiving_fields handler not registered")
    return await fn(**params)


async def _recv_add_item(params: Dict[str, Any]) -> Dict[str, Any]:
    """Wrapper for add_receiving_item handler."""
    handlers = _get_receiving_handlers()
    fn = handlers.get("add_receiving_item")
    if not fn:
        raise ValueError("add_receiving_item handler not registered")
    return await fn(**params)


async def _recv_adjust_item(params: Dict[str, Any]) -> Dict[str, Any]:
    """Wrapper for adjust_receiving_item handler."""
    handlers = _get_receiving_handlers()
    fn = handlers.get("adjust_receiving_item")
    if not fn:
        raise ValueError("adjust_receiving_item handler not registered")
    return await fn(**params)


async def _recv_link_invoice(params: Dict[str, Any]) -> Dict[str, Any]:
    """Wrapper for link_invoice_document handler."""
    handlers = _get_receiving_handlers()
    fn = handlers.get("link_invoice_document")
    if not fn:
        raise ValueError("link_invoice_document handler not registered")
    return await fn(**params)


async def _recv_accept(params: Dict[str, Any]) -> Dict[str, Any]:
    """Wrapper for accept_receiving handler (SIGNED)."""
    handlers = _get_receiving_handlers()
    fn = handlers.get("accept_receiving")
    if not fn:
        raise ValueError("accept_receiving handler not registered")
    return await fn(**params)


async def _recv_reject(params: Dict[str, Any]) -> Dict[str, Any]:
    """Wrapper for reject_receiving handler."""
    handlers = _get_receiving_handlers()
    fn = handlers.get("reject_receiving")
    if not fn:
        raise ValueError("reject_receiving handler not registered")
    return await fn(**params)


async def _recv_view_history(params: Dict[str, Any]) -> Dict[str, Any]:
    """Wrapper for view_receiving_history handler (READ)."""
    handlers = _get_receiving_handlers()
    fn = handlers.get("view_receiving_history")
    if not fn:
        raise ValueError("view_receiving_history handler not registered")
    return await fn(**params)


# ============================================================================
# HANDLER REGISTRY
# ============================================================================


# ========================================================================
# SHOPPING LIST LENS V1 WRAPPERS (from shopping_list_handlers.py)
# ========================================================================

async def _sl_create_item(params: Dict[str, Any]) -> Dict[str, Any]:
    """Create shopping list item wrapper."""
    handlers = _get_shopping_list_handlers()
    return await handlers.create_shopping_list_item(
        entity_id=None,
        yacht_id=params["yacht_id"],
        params=params
    )

async def _sl_approve_item(params: Dict[str, Any]) -> Dict[str, Any]:
    """Approve shopping list item wrapper."""
    handlers = _get_shopping_list_handlers()
    return await handlers.approve_shopping_list_item(
        entity_id=params["item_id"],
        yacht_id=params["yacht_id"],
        params=params
    )

async def _sl_reject_item(params: Dict[str, Any]) -> Dict[str, Any]:
    """Reject shopping list item wrapper."""
    handlers = _get_shopping_list_handlers()
    return await handlers.reject_shopping_list_item(
        entity_id=params["item_id"],
        yacht_id=params["yacht_id"],
        params=params
    )

async def _sl_promote_candidate(params: Dict[str, Any]) -> Dict[str, Any]:
    """Promote candidate to part wrapper."""
    handlers = _get_shopping_list_handlers()
    return await handlers.promote_candidate_to_part(
        entity_id=params["item_id"],
        yacht_id=params["yacht_id"],
        params=params
    )

async def _sl_view_history(params: Dict[str, Any]) -> Dict[str, Any]:
    """View shopping list history wrapper."""
    handlers = _get_shopping_list_handlers()
    return await handlers.view_shopping_list_history(
        entity_id=params["item_id"],
        yacht_id=params["yacht_id"],
        params=params
    )


INTERNAL_HANDLERS: Dict[str, Callable] = {
    # Original handlers
    "add_note": add_note,
    "add_note_to_work_order": add_note_to_work_order,
    "close_work_order": close_work_order,
    "open_document": open_document,
    "edit_handover_section": edit_handover_section,
    "update_equipment_status": update_equipment_status,
    "add_to_handover": add_to_handover,
    "delete_document": delete_document,
    "delete_shopping_item": delete_shopping_item,

    # Fault handlers
    "report_fault": report_fault,
    "close_fault": close_fault,
    "update_fault": update_fault,
    "add_fault_photo": add_fault_photo,
    "view_fault_detail": view_fault_detail,
    "diagnose_fault": diagnose_fault,
    "view_fault_history": view_fault_history,
    "suggest_parts": suggest_parts,
    "show_manual_section": show_manual_section,
    "add_fault_note": add_fault_note,
    "create_work_order_from_fault": create_work_order_from_fault,
    "reopen_fault": reopen_fault,
    "mark_fault_false_alarm": mark_fault_false_alarm,
    "acknowledge_fault": acknowledge_fault,
    "classify_fault": classify_fault,

    # Work order handlers
    "update_work_order": update_work_order,
    "assign_work_order": assign_work_order,
    "add_wo_hours": add_wo_hours,
    "add_wo_part": add_wo_part,
    "add_wo_note": add_wo_note,
    "start_work_order": start_work_order,
    "cancel_work_order": cancel_work_order,
    "create_work_order": create_work_order,
    "view_work_order_detail": view_work_order_detail,
    "add_work_order_photo": add_work_order_photo,
    "add_parts_to_work_order": add_parts_to_work_order,
    "view_work_order_checklist": view_work_order_checklist,

    # Worklist handlers
    "view_worklist": view_worklist,
    "add_worklist_task": add_worklist_task,
    "export_worklist": export_worklist,

    # =========================================================================
    # P3 Read-Only Handlers (from p3_read_only_handlers.py)
    # =========================================================================
    "view_document": _view_document,
    "view_related_documents": _view_related_documents,
    "view_document_section": _view_document_section,
    "view_work_order_history": _view_work_order_history,
    "view_checklist": _view_checklist,
    "view_equipment_details": _view_equipment_details,
    "view_equipment_history": _view_equipment_history,
    "view_equipment_parts": _view_equipment_parts,
    "view_linked_faults": _view_linked_faults,
    "view_equipment_manual": _view_equipment_manual,
    "view_fleet_summary": _view_fleet_summary,
    "open_vessel": _open_vessel,
    "export_fleet_summary": _export_fleet_summary,
    "request_predictive_insight": _request_predictive_insight,
    "view_part_stock": _view_part_stock,
    "view_part_location": _view_part_location,
    "view_part_usage": _view_part_usage,
    "scan_part_barcode": _scan_part_barcode,
    "view_linked_equipment": _view_linked_equipment,
    "export_handover": _export_handover,
    "view_smart_summary": _view_smart_summary,
    "view_hours_of_rest": _view_hours_of_rest,
    "export_hours_of_rest": _export_hours_of_rest,
    "view_compliance_status": _view_compliance_status,
    "track_delivery": _track_delivery,

    # =========================================================================
    # P1 Compliance Handlers (from p1_compliance_handlers.py)
    # =========================================================================
    "update_hours_of_rest": _update_hours_of_rest,
    "log_delivery_received": _log_delivery_received,

    # =========================================================================
    # P1 Purchasing Handlers (from p1_purchasing_handlers.py)
    # =========================================================================
    "create_purchase_request": _create_purchase_request,
    "order_part": _order_part,
    "approve_purchase": _approve_purchase,

    # =========================================================================
    # P2 Mutation Light Handlers (from p2_mutation_light_handlers.py)
    # =========================================================================
    "add_checklist_note": _p2_add_checklist_note,
    "add_checklist_photo": _p2_add_checklist_photo,
    "add_document_to_handover": _p2_add_document_to_handover,
    "add_equipment_note": _p2_add_equipment_note,
    "add_item_to_purchase": _p2_add_item_to_purchase,
    "add_predictive_insight_to_handover": _p2_add_predictive_insight_to_handover,
    "add_work_order_note": _p2_add_work_order_note,
    "mark_checklist_item_complete": _p2_mark_checklist_item_complete,
    "record_voice_note": _p2_record_voice_note,
    "regenerate_handover_summary": _p2_regenerate_handover_summary,
    "tag_for_survey": _p2_tag_for_survey,
    "update_purchase_status": _p2_update_purchase_status,
    "update_worklist_progress": _p2_update_worklist_progress,
    "upload_invoice": _p2_upload_invoice,
    "upload_photo": _p2_upload_photo,

    # Certificates
    "create_vessel_certificate": _cert_create_vessel_certificate,
    "create_crew_certificate": _cert_create_crew_certificate,
    "update_certificate": _cert_update_certificate,
    "link_document_to_certificate": _cert_link_document,
    "supersede_certificate": _cert_supersede_certificate,

    # =========================================================================
    # Document Lens v2 Handlers (from document_handlers.py)
    # =========================================================================
    "upload_document": _doc_upload_document,
    "update_document": _doc_update_document,
    "add_document_tags": _doc_add_document_tags,
    "delete_document": _doc_delete_document,
    "get_document_url": _doc_get_document_url,

    # =========================================================================
    # Equipment Lens v2 Handlers (from equipment_handlers.py)
    # =========================================================================
    # READ handlers
    "view_equipment": _eq_view_equipment,
    "view_maintenance_history": _eq_view_maintenance_history,
    "view_equipment_parts": _eq_view_equipment_parts,
    "view_linked_faults": _eq_view_linked_faults,
    "view_equipment_manual": _eq_view_equipment_manual,

    # MUTATION handlers (existing)
    "set_equipment_status": _eq_update_equipment_status,
    "add_equipment_note": _eq_add_equipment_note,
    "attach_file_to_equipment": _eq_attach_file_to_equipment,
    "create_work_order_for_equipment": _eq_create_work_order_for_equipment,
    "link_part_to_equipment": _eq_link_part_to_equipment,
    "flag_equipment_attention": _eq_flag_equipment_attention,
    "decommission_equipment": _eq_decommission_equipment,
    "record_equipment_hours": _eq_record_equipment_hours,

    # MUTATION handlers (Equipment Lens v2 Phase A)
    "create_equipment": _eq_create_equipment,
    "assign_parent_equipment": _eq_assign_parent_equipment,
    "archive_equipment": _eq_archive_equipment,
    "restore_archived_equipment": _eq_restore_archived_equipment,
    "get_open_faults_for_equipment": _eq_get_open_faults_for_equipment,
    "get_related_entities_for_equipment": _eq_get_related_entities_for_equipment,
    "add_entity_link": _eq_add_entity_link,
    "link_document_to_equipment": _eq_link_document_to_equipment,

    # Equipment Lens v2 - Spec completion
    "attach_image_with_comment": _eq_attach_image_with_comment,
    "decommission_and_replace_equipment": _eq_decommission_and_replace,

    # =========================================================================
    # Receiving Lens v1 Handlers (from receiving_handlers.py)
    # =========================================================================
    "create_receiving": _recv_create_receiving,
    "attach_receiving_image_with_comment": _recv_attach_image_with_comment,
    "extract_receiving_candidates": _recv_extract_candidates,
    "update_receiving_fields": _recv_update_fields,
    "add_receiving_item": _recv_add_item,
    "adjust_receiving_item": _recv_adjust_item,
    "link_invoice_document": _recv_link_invoice,
    "accept_receiving": _recv_accept,
    "reject_receiving": _recv_reject,
    "view_receiving_history": _recv_view_history,

    # =========================================================================
    # Shopping List Lens v1 Handlers (from shopping_list_handlers.py)
    # =========================================================================
    "create_shopping_list_item": _sl_create_item,
    "approve_shopping_list_item": _sl_approve_item,
    "reject_shopping_list_item": _sl_reject_item,
    "promote_candidate_to_part": _sl_promote_candidate,
    "view_shopping_list_history": _sl_view_history,
}


# ============================================================================
# DISPATCHER
# ============================================================================


async def dispatch(action_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Dispatch action to internal handler.

    Args:
        action_id: ID of action to execute
        params: Merged context + payload + user_context

    Returns:
        Result from handler

    Raises:
        KeyError: If action_id not found
        Exception: If handler fails
    """
    if action_id not in INTERNAL_HANDLERS:
        raise KeyError(f"No internal handler found for action '{action_id}'")

    handler = INTERNAL_HANDLERS[action_id]

    try:
        result = await handler(params)
        return result

    except ValueError as e:
        # Validation errors (e.g., resource not found)
        raise ValueError(str(e))

    except Exception as e:
        # Other errors
        raise Exception(f"Internal handler failed: {str(e)}")


__all__ = ["dispatch", "INTERNAL_HANDLERS"]
