"""
Internal Action Dispatcher

Handles fast actions directly via Supabase.

These are simple CRUD operations that don't require complex workflow orchestration.
"""

from typing import Dict, Any, Callable
import os
from datetime import datetime
from supabase import create_client, Client

# Import handler classes for P1/P3 handlers
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "handlers"))

from handlers.p3_read_only_handlers import P3ReadOnlyHandlers
from handlers.p1_compliance_handlers import P1ComplianceHandlers
from handlers.p1_purchasing_handlers import P1PurchasingHandlers
from handlers.p2_mutation_light_handlers import P2MutationLightHandlers

# Lazy-initialized handler instances
_p3_handlers = None
_p1_compliance_handlers = None
_p1_purchasing_handlers = None
_p2_handlers = None


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


def get_supabase_client() -> Client:
    """Get initialized Supabase client."""
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_KEY")

    if not url or not key:
        raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")

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
        - storage_path: str (path in Supabase storage)
    """
    supabase = get_supabase_client()

    # Generate signed URL (valid for 1 hour)
    try:
        result = supabase.storage.from_("documents").create_signed_url(
            params["storage_path"],
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
    result = supabase.table("handovers").update({
        "content": content,
        "updated_at": datetime.utcnow().isoformat(),
        "updated_by": params["user_id"],
    }).eq("id", params["handover_id"]).execute()

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
    except Exception:
        pass  # Don't fail if audit log fails

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

    # Map priority to integer
    priority_value = {"low": 1, "normal": 2, "high": 3, "urgent": 4}.get(
        params.get("priority", "normal"), 2
    )

    # Create handover entry
    handover_id = str(uuid_lib.uuid4())
    handover_entry = {
        "id": handover_id,
        "yacht_id": params["yacht_id"],
        "entity_type": params.get("entity_type", "equipment"),
        "entity_id": params.get("entity_id") or params.get("equipment_id"),
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
    try:
        supabase.table("pms_audit_log").insert({
            "yacht_id": params["yacht_id"],
            "action": "add_to_handover",
            "entity_type": "handover",
            "entity_id": handover_id,
            "user_id": params["user_id"],
            "new_values": {
                "entity_type": params.get("entity_type"),
                "entity_id": params.get("entity_id") or params.get("equipment_id"),
                "category": category,
            },
            "created_at": datetime.utcnow().isoformat(),
        }).execute()
    except Exception:
        pass  # Don't fail if audit log fails

    return {
        "handover_id": handover_id,
        "entity_type": params.get("entity_type", "equipment"),
        "entity_id": params.get("entity_id") or params.get("equipment_id"),
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
    result = supabase.table("documents").update({
        "deleted_at": datetime.utcnow().isoformat(),
        "deleted_by": params["user_id"],
        "delete_reason": params.get("reason", "Deleted via API"),
    }).eq("id", params["document_id"]).execute()

    if not result.data:
        raise Exception("Failed to delete document")

    # Create audit log
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
    except Exception:
        pass

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
    except Exception:
        pass

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
    Report a new fault.

    Required params:
        - yacht_id: UUID
        - equipment_id: UUID
        - description: str
        - user_id: UUID (from JWT)
    """
    import uuid as uuid_lib
    supabase = get_supabase_client()

    fault_id = str(uuid_lib.uuid4())
    fault_data = {
        "id": fault_id,
        "yacht_id": params["yacht_id"],
        "equipment_id": params["equipment_id"],
        "description": params["description"],
        "priority": params.get("priority", "medium"),
        "status": "open",
        "reported_by": params["user_id"],
        "reported_at": datetime.utcnow().isoformat(),
        "created_at": datetime.utcnow().isoformat(),
    }

    result = supabase.table("pms_faults").insert(fault_data).execute()

    if not result.data:
        raise Exception("Failed to create fault")

    return {
        "fault_id": fault_id,
        "status": "open",
        "created_at": fault_data["created_at"],
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
        - note: str
        - user_id: UUID (from JWT)
    """
    import uuid as uuid_lib
    supabase = get_supabase_client()

    note_id = str(uuid_lib.uuid4())
    note_data = {
        "id": note_id,
        "entity_type": "fault",
        "entity_id": params["fault_id"],
        "note_text": params["note"],
        "created_by": params["user_id"],
        "created_at": datetime.utcnow().isoformat(),
    }

    result = supabase.table("notes").insert(note_data).execute()

    return {
        "note_id": note_id,
        "fault_id": params["fault_id"],
        "created_at": note_data["created_at"],
    }


async def create_work_order_from_fault(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a work order from a fault.

    Required params:
        - yacht_id: UUID
        - fault_id: UUID
        - user_id: UUID (from JWT)
    """
    import uuid as uuid_lib
    supabase = get_supabase_client()

    # Get fault details
    fault_result = supabase.table("pms_faults").select("*").eq(
        "id", params["fault_id"]
    ).eq("yacht_id", params["yacht_id"]).execute()

    if not fault_result.data:
        raise ValueError(f"Fault {params['fault_id']} not found or access denied")

    fault = fault_result.data[0]

    # Create work order
    wo_id = str(uuid_lib.uuid4())
    wo_data = {
        "id": wo_id,
        "yacht_id": params["yacht_id"],
        "equipment_id": fault.get("equipment_id"),
        "fault_id": params["fault_id"],
        "title": f"Fix: {fault.get('description', 'Fault repair')[:100]}",
        "description": fault.get("description"),
        "priority": fault.get("priority", "medium"),
        "status": "open",
        "created_by": params["user_id"],
        "created_at": datetime.utcnow().isoformat(),
    }

    result = supabase.table("pms_work_orders").insert(wo_data).execute()

    if not result.data:
        raise Exception("Failed to create work order")

    return {
        "work_order_id": wo_id,
        "fault_id": params["fault_id"],
        "status": "open",
        "created_at": wo_data["created_at"],
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
# HANDLER REGISTRY
# ============================================================================

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
