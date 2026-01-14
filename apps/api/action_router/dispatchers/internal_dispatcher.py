"""
Internal Action Dispatcher

Handles fast actions directly via Supabase.

These are simple CRUD operations that don't require complex workflow orchestration.
"""

from typing import Dict, Any, Callable
import os
from datetime import datetime
from supabase import create_client, Client


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


# ============================================================================
# HANDLER REGISTRY
# ============================================================================

INTERNAL_HANDLERS: Dict[str, Callable] = {
    "add_note": add_note,
    "add_note_to_work_order": add_note_to_work_order,
    "close_work_order": close_work_order,
    "open_document": open_document,
    "edit_handover_section": edit_handover_section,
    "update_equipment_status": update_equipment_status,
    "add_to_handover": add_to_handover,
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
