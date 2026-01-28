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
    """
    supabase = get_supabase_client()

    # Verify work order exists and belongs to yacht
    wo_result = supabase.table("work_orders").select("id").eq(
        "id", params["work_order_id"]
    ).eq("yacht_id", params["yacht_id"]).execute()

    if not wo_result.data:
        raise ValueError(f"Work order {params['work_order_id']} not found or access denied")

    # Insert note
    result = supabase.table("work_order_notes").insert({
        "work_order_id": params["work_order_id"],
        "note_text": params["note_text"],
        "created_by": params["user_id"],
        "created_at": datetime.utcnow().isoformat(),
    }).execute()

    if not result.data:
        raise Exception("Failed to create work order note")

    return {
        "note_id": result.data[0]["id"],
        "created_at": result.data[0]["created_at"],
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


# ============================================================================
# HANDLER REGISTRY
# ============================================================================

INTERNAL_HANDLERS: Dict[str, Callable] = {
    "add_note": add_note,
    "add_note_to_work_order": add_note_to_work_order,
    "close_work_order": close_work_order,
    "open_document": open_document,
    "edit_handover_section": edit_handover_section,
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
