# apps/api/routes/handlers/wo_completion_handler.py
"""
Work Order Completion Handlers — Phase 5 Task 1.

Migrated from p0_actions_routes.py legacy elif chain.
Handler contract: see routes/handlers/__init__.py header.
Do NOT call get_tenant_supabase_client — db_client is pre-constructed by dispatcher.
"""
from datetime import datetime, timezone
import logging

from fastapi import HTTPException
from supabase import Client

from routes.handlers.ledger_utils import build_ledger_event

logger = logging.getLogger(__name__)


async def create_work_order_from_fault(
    payload: dict, context: dict, yacht_id: str, user_id: str,
    user_context: dict, db_client: Client,
) -> dict:
    """Create WO from fault with wet-signature validation. (was L1240–1381)"""
    signature = payload.get("signature")

    if not signature:
        raise HTTPException(status_code=400, detail={
            "status": "error", "error_code": "signature_required",
            "message": "Signature payload required for SIGNED action"
        })

    if not isinstance(signature, dict):
        raise HTTPException(status_code=400, detail={
            "status": "error", "error_code": "invalid_signature",
            "message": "Signature must be an object"
        })

    required_sig_keys = {"signed_at", "user_id", "role_at_signing", "signature_type"}
    missing_keys = required_sig_keys - set(signature.keys())
    if missing_keys:
        raise HTTPException(status_code=400, detail={
            "status": "error", "error_code": "invalid_signature",
            "message": f"Invalid signature: missing keys {sorted(missing_keys)}"
        })

    role_at_signing = signature.get("role_at_signing")
    allowed_signer_roles = ["captain", "manager"]
    if role_at_signing not in allowed_signer_roles:
        raise HTTPException(status_code=403, detail={
            "status": "error", "error_code": "invalid_signer_role",
            "message": f"Role '{role_at_signing}' cannot sign this action",
            "required_roles": allowed_signer_roles
        })

    fault_id = payload.get("fault_id")
    fault = db_client.table("pms_faults").select("*").eq("id", fault_id).eq("yacht_id", yacht_id).single().execute()
    if not fault.data:
        raise HTTPException(status_code=404, detail="Fault not found")

    existing = db_client.table("pms_work_orders").select("id").eq("fault_id", fault_id).execute()
    if existing.data and not payload.get("override_duplicate", False):
        return {"status": "error", "error_code": "DUPLICATE_WO_EXISTS", "message": "Work order already exists for this fault"}

    raw_priority = payload.get("priority", "routine")
    priority_map = {"normal": "routine", "low": "routine", "medium": "routine", "high": "critical"}
    priority = priority_map.get(raw_priority, raw_priority if raw_priority in ("routine", "emergency", "critical") else "routine")

    wo_data = {
        "yacht_id": yacht_id,
        "fault_id": fault_id,
        "equipment_id": payload.get("equipment_id") or fault.data.get("equipment_id"),
        "title": payload.get("title", fault.data.get("title", "Work order from fault")),
        "description": payload.get("description", fault.data.get("description", "")),
        "priority": priority,
        "status": "planned",
        "created_by": user_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    wo_result = db_client.table("pms_work_orders").insert(wo_data).execute()
    if not wo_result.data:
        return {"status": "error", "error_code": "INSERT_FAILED", "message": "Failed to create work order"}

    wo_id = wo_result.data[0]["id"]
    db_client.table("pms_faults").update({
        "work_order_id": wo_id,
        "updated_by": user_id,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", fault_id).eq("yacht_id", yacht_id).execute()

    audit_data = {
        "yacht_id": yacht_id,
        "action": "create_work_order_from_fault",
        "entity_type": "work_order",
        "entity_id": wo_id,
        "user_id": user_id,
        "signature": signature,
        "new_values": wo_result.data[0],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    db_client.table("pms_audit_log").insert(audit_data).execute()

    try:
        ledger_event = build_ledger_event(
            yacht_id=yacht_id, user_id=user_id, event_type="create",
            entity_type="work_order", entity_id=wo_id,
            action="create_work_order_from_fault",
            user_role=user_context.get("role"),
            change_summary="Work order created from fault",
        )
        db_client.table("ledger_events").insert(ledger_event).execute()
    except Exception as ledger_err:
        if "204" not in str(ledger_err):
            logger.warning(f"[Ledger] Failed: {ledger_err}")

    return {"status": "success", "work_order_id": wo_id, "message": "Work order created from fault"}


async def add_note_to_work_order(
    payload: dict, context: dict, yacht_id: str, user_id: str,
    user_context: dict, db_client: Client,
) -> dict:
    """Insert note into pms_work_order_notes with FK fallback. (was L1382–1481)"""
    work_order_id = payload.get("work_order_id")
    note_text = payload.get("note_text", "")
    note_type = payload.get("note_type", "general")

    if not work_order_id:
        raise HTTPException(status_code=400, detail="work_order_id is required")
    if not note_text or len(note_text) < 1:
        raise HTTPException(status_code=400, detail="note_text is required")

    valid_types = ("general", "progress", "issue", "resolution")
    if note_type not in valid_types:
        note_type = "general"

    try:
        check = db_client.table("pms_work_orders").select("id").eq("id", work_order_id).eq("yacht_id", yacht_id).single().execute()
        if not check.data:
            raise HTTPException(status_code=404, detail="Work order not found")
    except HTTPException:
        raise
    except Exception as e:
        error_str = str(e)
        if "PGRST116" in error_str or "0 rows" in error_str or "result contains 0 rows" in error_str.lower():
            raise HTTPException(status_code=404, detail="Work order not found")
        raise

    note_data = {
        "work_order_id": work_order_id,
        "note_text": note_text,
        "note_type": note_type,
        "created_by": user_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    try:
        note_result = db_client.table("pms_work_order_notes").insert(note_data).execute()
        if note_result.data:
            try:
                ledger_event = build_ledger_event(
                    yacht_id=yacht_id, user_id=user_id, event_type="update",
                    entity_type="work_order", entity_id=work_order_id,
                    action="add_note_to_work_order",
                    user_role=user_context.get("role"),
                    change_summary="Note added to work order",
                )
                db_client.table("ledger_events").insert(ledger_event).execute()
            except Exception as ledger_err:
                if "204" not in str(ledger_err):
                    logger.warning(f"[Ledger] Failed: {ledger_err}")
            return {"status": "success", "success": True, "note_id": note_result.data[0]["id"], "message": "Note added to work order successfully"}
        return {"status": "error", "error_code": "INSERT_FAILED", "message": "Failed to add note to work order"}
    except Exception as db_err:
        error_str = str(db_err)
        if "23503" in error_str or "foreign key" in error_str.lower():
            # Legacy fallback inherited from original elif block: if the inserting user's
            # UUID has no matching profile (e.g. service account), retry with any valid
            # profile ID so the note is not silently lost. Attribution caveat is accepted.
            fallback_user = db_client.table("auth_users_profiles").select("id").limit(1).execute()
            if fallback_user.data:
                note_data["created_by"] = fallback_user.data[0]["id"]
                try:
                    note_result = db_client.table("pms_work_order_notes").insert(note_data).execute()
                    if note_result.data:
                        return {"status": "success", "success": True, "note_id": note_result.data[0]["id"], "message": "Note added (with system user attribution)"}
                    raise HTTPException(status_code=500, detail=f"Insert failed: {error_str}")
                except Exception as retry_err:
                    raise HTTPException(status_code=500, detail=f"FK constraint: {error_str}. Retry: {str(retry_err)}")
            raise HTTPException(status_code=500, detail=f"FK constraint and no fallback user: {error_str}")
        raise HTTPException(status_code=500, detail=f"Database error: {error_str}")


async def add_part_to_work_order(
    payload: dict, context: dict, yacht_id: str, user_id: str,
    user_context: dict, db_client: Client,
) -> dict:
    """Delegate to WorkOrderMutationHandlers. (was L1483–1493)"""
    work_order_id = payload.get("work_order_id")
    part_id = payload.get("part_id")
    quantity = payload.get("quantity", 1)
    if not work_order_id:
        raise HTTPException(status_code=400, detail="work_order_id is required")
    if not part_id:
        raise HTTPException(status_code=400, detail="part_id is required")

    from handlers.work_order_mutation_handlers import WorkOrderMutationHandlers
    wo_handlers = WorkOrderMutationHandlers(db_client)
    return await wo_handlers.add_part_to_work_order_execute(
        work_order_id=work_order_id,
        part_id=part_id,
        quantity=quantity,
        notes=payload.get("notes"),
        yacht_id=yacht_id,
        user_id=user_id,
    )


async def mark_work_order_complete(
    payload: dict, context: dict, yacht_id: str, user_id: str,
    user_context: dict, db_client: Client,
) -> dict:
    """Delegate to WorkOrderMutationHandlers + ledger. (was L1495–1537)"""
    work_order_id = payload.get("work_order_id")
    completion_notes = payload.get("completion_notes")
    signature = payload.get("signature")
    if not work_order_id:
        raise HTTPException(status_code=400, detail="work_order_id is required")
    if not completion_notes:
        raise HTTPException(status_code=400, detail="completion_notes is required")
    if not signature:
        raise HTTPException(status_code=400, detail="signature is required for mark_work_order_complete")

    parts_used = payload.get("parts_used", [])

    from handlers.work_order_mutation_handlers import WorkOrderMutationHandlers
    wo_handlers = WorkOrderMutationHandlers(db_client)
    result = await wo_handlers.mark_work_order_complete_execute(
        work_order_id=work_order_id,
        completion_notes=completion_notes,
        parts_used=parts_used,
        signature=signature,
        yacht_id=yacht_id,
        user_id=user_id,
    )

    try:
        ledger_event = build_ledger_event(
            yacht_id=yacht_id, user_id=user_id, event_type="status_change",
            entity_type="work_order", entity_id=work_order_id,
            action="mark_work_order_complete",
            user_role=user_context.get("role", "member"),
            change_summary="Work order marked as complete",
            metadata={
                "completion_notes": completion_notes,
                "parts_used_count": len(parts_used),
                "domain": "Work Orders",
            }
        )
        try:
            db_client.table("ledger_events").insert(ledger_event).execute()
        except Exception as e:
            if "204" not in str(e):
                logger.warning(f"[Ledger] Failed: {e}")
    except Exception as e:
        logger.warning(f"[Ledger] Failed to prepare event: {e}")

    return result


async def reassign_work_order(
    payload: dict, context: dict, yacht_id: str, user_id: str,
    user_context: dict, db_client: Client,
) -> dict:
    """Delegate to WorkOrderMutationHandlers + ledger. (was L1609–1659)"""
    signature = payload.get("signature")
    if not signature:
        raise HTTPException(status_code=400, detail="signature is required for reassign_work_order")
    required_sig_keys = {"signed_at", "user_id", "role_at_signing", "signature_type", "signature_hash"}
    if not isinstance(signature, dict) or not required_sig_keys.issubset(set(signature.keys())):
        raise HTTPException(status_code=400, detail="invalid signature payload: missing required fields")

    work_order_id = payload.get("work_order_id")
    assignee_id = payload.get("assignee_id")
    if not work_order_id:
        raise HTTPException(status_code=400, detail="work_order_id is required")
    if not assignee_id:
        raise HTTPException(status_code=400, detail="assignee_id is required")

    from handlers.work_order_mutation_handlers import WorkOrderMutationHandlers
    wo_handlers = WorkOrderMutationHandlers(db_client)
    result = await wo_handlers.reassign_work_order_execute(
        work_order_id=work_order_id,
        new_assignee_id=assignee_id,
        reason=payload.get("reason", "Reassigned"),
        signature=signature,
        yacht_id=yacht_id,
        user_id=user_id,
    )

    try:
        ledger_event = build_ledger_event(
            yacht_id=yacht_id, user_id=user_id, event_type="assignment",
            entity_type="work_order", entity_id=work_order_id,
            action="reassign_work_order",
            user_role=user_context.get("role", "member"),
            change_summary=f"Work order reassigned: {payload.get('reason', 'Reassigned')}",
            metadata={
                "new_assignee_id": assignee_id,
                "reason": payload.get("reason", "Reassigned"),
                "domain": "Work Orders",
            }
        )
        try:
            db_client.table("ledger_events").insert(ledger_event).execute()
        except Exception as e:
            if "204" not in str(e):
                logger.warning(f"[Ledger] Failed: {e}")
    except Exception as e:
        logger.warning(f"[Ledger] Failed to prepare event: {e}")

    return result


async def archive_work_order(
    payload: dict, context: dict, yacht_id: str, user_id: str,
    user_context: dict, db_client: Client,
) -> dict:
    """Delegate to WorkOrderMutationHandlers + ledger. (was L1661–1708)"""
    signature = payload.get("signature")
    if not signature:
        raise HTTPException(status_code=400, detail="signature is required for archive_work_order")
    required_sig_keys = {"signed_at", "user_id", "role_at_signing", "signature_type", "signature_hash"}
    if not isinstance(signature, dict) or not required_sig_keys.issubset(set(signature.keys())):
        raise HTTPException(status_code=400, detail="invalid signature payload: missing required fields")

    work_order_id = payload.get("work_order_id")
    if not work_order_id:
        raise HTTPException(status_code=400, detail="work_order_id is required")

    from handlers.work_order_mutation_handlers import WorkOrderMutationHandlers
    wo_handlers = WorkOrderMutationHandlers(db_client)
    result = await wo_handlers.archive_work_order_execute(
        work_order_id=work_order_id,
        deletion_reason=payload.get("deletion_reason", "Archived"),
        signature=signature,
        yacht_id=yacht_id,
        user_id=user_id,
    )

    try:
        ledger_event = build_ledger_event(
            yacht_id=yacht_id, user_id=user_id, event_type="delete",
            entity_type="work_order", entity_id=work_order_id,
            action="archive_work_order",
            user_role=user_context.get("role", "member"),
            change_summary=f"Work order archived: {payload.get('deletion_reason', 'Archived')}",
            metadata={"deletion_reason": payload.get("deletion_reason", "Archived"), "domain": "Work Orders"}
        )
        try:
            db_client.table("ledger_events").insert(ledger_event).execute()
        except Exception as e:
            if "204" not in str(e):
                logger.warning(f"[Ledger] Failed: {e}")
    except Exception as e:
        logger.warning(f"[Ledger] Failed to prepare event: {e}")

    return result


async def add_work_order_note(
    payload: dict, context: dict, yacht_id: str, user_id: str,
    user_context: dict, db_client: Client,
) -> dict:
    """Append note to work order metadata.notes array + ledger. (was L4291–4376)"""
    work_order_id = payload.get("work_order_id")
    note_text = payload.get("note_text")

    if not work_order_id:
        raise HTTPException(status_code=400, detail="work_order_id is required")
    if not note_text:
        raise HTTPException(status_code=400, detail="note_text is required")

    wo = db_client.table("pms_work_orders").select("id, title, wo_number, metadata").eq("id", work_order_id).eq("yacht_id", yacht_id).maybe_single().execute()
    if not wo.data:
        raise HTTPException(status_code=404, detail="Work order not found")

    metadata = wo.data.get("metadata", {}) or {}
    notes = metadata.get("notes", []) or []
    notes.append({
        "text": note_text,
        "added_by": user_id,
        "added_at": datetime.now(timezone.utc).isoformat(),
    })
    metadata["notes"] = notes

    try:
        db_client.table("pms_work_orders").update({"metadata": metadata}).eq("id", work_order_id).eq("yacht_id", yacht_id).execute()
    except Exception as update_err:
        if "204" in str(update_err):
            logger.info(f"Work order update succeeded with 204 for {work_order_id}")
        else:
            raise

    try:
        wo_title = wo.data.get("title", "Untitled")
        wo_number = wo.data.get("number", "")
        display_name = f"Work Order #{wo_number} — {wo_title}" if wo_number else f"Work Order — {wo_title}"
        user_name = user_context.get("name") or user_context.get("email", "Unknown")
        user_role_str = user_context.get("role", "member")

        ledger_event = build_ledger_event(
            yacht_id=yacht_id, user_id=user_id, event_type="update",
            entity_type="work_order", entity_id=work_order_id,
            action="add_note",
            user_role=user_role_str,
            change_summary=f"Note added to {display_name}",
            metadata={
                "display_name": display_name,
                "note_text": note_text[:200] + "..." if len(note_text) > 200 else note_text,
                "user_name": user_name,
                "notes_count": len(notes),
                "domain": "Work Orders",
            }
        )
        try:
            db_client.table("ledger_events").insert(ledger_event).execute()
        except Exception as ledger_insert_err:
            if "204" in str(ledger_insert_err):
                pass
            else:
                logger.warning(f"[Ledger] Failed: {ledger_insert_err}")
    except Exception as ledger_err:
        logger.warning(f"[Ledger] Failed to prepare event: {ledger_err}")

    return {"status": "success", "success": True, "message": "Note added to work order", "work_order_id": work_order_id, "notes_count": len(notes)}


HANDLERS: dict = {
    "create_work_order_from_fault": create_work_order_from_fault,
    "add_note_to_work_order":       add_note_to_work_order,
    "add_part_to_work_order":       add_part_to_work_order,
    "mark_work_order_complete":     mark_work_order_complete,
    "reassign_work_order":          reassign_work_order,
    "archive_work_order":           archive_work_order,
    "add_work_order_note":          add_work_order_note,
}
