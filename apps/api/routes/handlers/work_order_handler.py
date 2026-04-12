"""
Work Order Action Handlers

Migrated from p0_actions_routes.py elif blocks (Phase 4, Task 2).
Handler contract: see handlers/__init__.py header.
Do NOT call get_tenant_supabase_client — db_client is pre-constructed by dispatcher.
Import build_ledger_event from routes.handlers.ledger_utils, not from p0_actions_routes.
"""
from datetime import datetime, timezone
import uuid as uuid_module
import logging

from fastapi import HTTPException
from supabase import Client

from routes.handlers.ledger_utils import build_ledger_event

logger = logging.getLogger(__name__)

# TODO: This UUID is a fallback for legacy WO notes created before user auth.
# Source: p0_actions_routes.py original. See migration context for details.
_LEGACY_TENANT_USER_ID = "a35cad0b-02ff-4287-b6e4-17c96fa6a424"


# ============================================================================
# update_work_order / update_wo  (was L2527-2549)
# ============================================================================
async def update_work_order(
    payload: dict,
    context: dict,
    yacht_id: str,
    user_id: str,
    user_context: dict,
    db_client: Client,
) -> dict:
    work_order_id = payload.get("work_order_id")

    # Build update data
    update_data = {"updated_by": user_id, "updated_at": datetime.now(timezone.utc).isoformat()}
    if payload.get("description"):
        update_data["description"] = payload["description"]
    if payload.get("priority"):
        # Map priority values
        priority_map = {"normal": "routine", "low": "routine", "medium": "routine", "high": "critical"}
        raw_priority = payload["priority"]
        update_data["priority"] = priority_map.get(raw_priority, raw_priority if raw_priority in ("routine", "emergency", "critical") else "routine")
    if payload.get("title"):
        update_data["title"] = payload["title"]

    wo_result = db_client.table("pms_work_orders").update(update_data).eq("id", work_order_id).eq("yacht_id", yacht_id).execute()
    if wo_result.data:
        return {"status": "success", "message": "Work order updated"}
    else:
        return {"status": "error", "error_code": "UPDATE_FAILED", "message": "Failed to update work order"}


# ============================================================================
# assign_work_order / assign_wo  (was L2551-2577)
# ============================================================================
async def assign_work_order(
    payload: dict,
    context: dict,
    yacht_id: str,
    user_id: str,
    user_context: dict,
    db_client: Client,
) -> dict:
    work_order_id = payload.get("work_order_id")
    assigned_to = payload.get("assigned_to")

    update_data = {
        "assigned_to": assigned_to,
        "updated_by": user_id,
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    wo_result = db_client.table("pms_work_orders").update(update_data).eq("id", work_order_id).eq("yacht_id", yacht_id).execute()
    if wo_result.data:
        try:
            ledger_event = build_ledger_event(
                yacht_id=yacht_id, user_id=user_id, event_type="assignment",
                entity_type="work_order", entity_id=work_order_id, action="assign_work_order",
                user_role=user_context.get("role"), change_summary="Work order assigned",
            )
            db_client.table("ledger_events").insert(ledger_event).execute()
        except Exception as ledger_err:
            if "204" not in str(ledger_err):
                logger.warning(f"[Ledger] Failed to record assign_work_order: {ledger_err}")
        return {"status": "success", "message": "Work order assigned"}
    else:
        return {"status": "error", "error_code": "UPDATE_FAILED", "message": "Failed to assign work order"}


# ============================================================================
# close_work_order / complete_work_order  (was L2579-2598)
# ============================================================================
async def close_work_order(
    payload: dict,
    context: dict,
    yacht_id: str,
    user_id: str,
    user_context: dict,
    db_client: Client,
) -> dict:
    work_order_id = payload.get("work_order_id")

    # Note: completed_by has FK to non-existent users table, skip it
    update_data = {
        "status": "completed",
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    if payload.get("completion_notes"):
        update_data["completion_notes"] = payload["completion_notes"]

    wo_result = db_client.table("pms_work_orders").update(update_data).eq("id", work_order_id).eq("yacht_id", yacht_id).execute()
    if wo_result.data:
        try:
            ledger_event = build_ledger_event(
                yacht_id=yacht_id,
                user_id=user_id,
                event_type="status_change",
                entity_type="work_order",
                entity_id=work_order_id,
                action="close_work_order",
                user_role=user_context.get("role"),
                change_summary="Work order closed",
            )
            db_client.table("ledger_events").insert(ledger_event).execute()
        except Exception as ledger_err:
            if "204" not in str(ledger_err):
                logger.warning(f"[Ledger] Failed to record close_work_order: {ledger_err}")
        return {"status": "success", "message": "Work order closed"}
    else:
        return {"status": "error", "error_code": "UPDATE_FAILED", "message": "Failed to close work order"}


# ============================================================================
# add_wo_hours / log_work_hours  (was L2600-2622)
# ============================================================================
async def add_wo_hours(
    payload: dict,
    context: dict,
    yacht_id: str,
    user_id: str,
    user_context: dict,
    db_client: Client,
) -> dict:
    work_order_id = payload.get("work_order_id")
    hours = payload.get("hours", 0)

    # Add to work order notes as hours entry
    # Note: created_by is NOT NULL, use authenticated user_id
    # Note: note_type must be 'general' or 'progress'
    note_data = {
        "work_order_id": work_order_id,
        "note_text": f"Hours logged: {hours}h - {payload.get('description', 'Work performed')}",
        "note_type": "progress",
        "created_by": user_id,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    note_result = db_client.table("pms_work_order_notes").insert(note_data).execute()
    if note_result.data:
        try:
            ledger_event = build_ledger_event(
                yacht_id=yacht_id,
                user_id=user_id,
                event_type="update",
                entity_type="work_order",
                entity_id=work_order_id,
                action="add_wo_hours",
                user_role=user_context.get("role"),
                change_summary=f"Logged {hours} hours",
            )
            db_client.table("ledger_events").insert(ledger_event).execute()
        except Exception as ledger_err:
            if "204" not in str(ledger_err):
                logger.warning(f"[Ledger] Failed to record add_wo_hours: {ledger_err}")
        return {"status": "success", "message": f"Logged {hours} hours"}
    else:
        return {"status": "error", "error_code": "INSERT_FAILED", "message": "Failed to log hours"}


# ============================================================================
# add_wo_part / add_part_to_wo  (was L2624-2660)
# ============================================================================
async def add_wo_part(
    payload: dict,
    context: dict,
    yacht_id: str,
    user_id: str,
    user_context: dict,
    db_client: Client,
) -> dict:
    work_order_id = payload.get("work_order_id")
    part_id = payload.get("part_id")
    quantity = payload.get("quantity", 1)

    # Validate required fields
    if not work_order_id:
        raise HTTPException(status_code=400, detail="work_order_id is required")
    if not part_id:
        raise HTTPException(status_code=400, detail="part_id is required")

    # Validate quantity bounds (PostgreSQL integer max is 2147483647)
    try:
        quantity = int(quantity)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="quantity must be a valid integer")

    if quantity < 0:
        raise HTTPException(status_code=400, detail="quantity cannot be negative")
    if quantity > 1000000:
        raise HTTPException(status_code=400, detail="quantity exceeds maximum allowed (1000000)")

    # Use upsert to handle duplicate key (work_order_id, part_id)
    part_data = {
        "work_order_id": work_order_id,
        "part_id": part_id,
        "quantity": quantity,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    part_result = db_client.table("pms_work_order_parts").upsert(part_data, on_conflict="work_order_id,part_id").execute()
    if part_result.data:
        try:
            ledger_event = build_ledger_event(
                yacht_id=yacht_id,
                user_id=user_id,
                event_type="update",
                entity_type="work_order",
                entity_id=work_order_id,
                action="add_wo_part",
                user_role=user_context.get("role"),
                change_summary=f"Part added: part_id={part_id}, qty={quantity}",
            )
            db_client.table("ledger_events").insert(ledger_event).execute()
        except Exception as ledger_err:
            if "204" not in str(ledger_err):
                logger.warning(f"[Ledger] Failed to record add_wo_part: {ledger_err}")
        return {"status": "success", "message": "Part added to work order"}
    else:
        return {"status": "error", "error_code": "INSERT_FAILED", "message": "Failed to add part"}


# ============================================================================
# add_wo_note / add_note_to_wo  (was L2662-2703)
# ============================================================================
async def add_wo_note(
    payload: dict,
    context: dict,
    yacht_id: str,
    user_id: str,
    user_context: dict,
    db_client: Client,
) -> dict:
    work_order_id = payload.get("work_order_id")
    note_text = payload.get("note_text")

    # Note: created_by is NOT NULL, use authenticated user_id
    # Note: note_type must be 'general' or 'progress'
    # Note: pms_work_order_notes does NOT have yacht_id column - ledger trigger fetches it from parent WO
    raw_note_type = payload.get("note_type", "general")
    note_type = raw_note_type if raw_note_type in ("general", "progress") else "general"
    note_data = {
        "work_order_id": work_order_id,
        "note_text": note_text,
        "note_type": note_type,
        "created_by": user_id,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    note_result = db_client.table("pms_work_order_notes").insert(note_data).execute()
    if note_result.data:
        result = {"status": "success", "message": "Note added to work order"}
        try:
            ledger_event = build_ledger_event(
                yacht_id=yacht_id,
                user_id=user_id,
                event_type="update",
                entity_type="work_order",
                entity_id=work_order_id,
                action="add_wo_note",
                user_role=user_context.get("role"),
                change_summary="Note added to work order",
            )
            db_client.table("ledger_events").insert(ledger_event).execute()
        except Exception as ledger_err:
            if "204" in str(ledger_err):
                pass
            else:
                logger.warning(f"[Ledger] Failed to record add_wo_note: {ledger_err}")
        return result
    else:
        return {"status": "error", "error_code": "INSERT_FAILED", "message": "Failed to add note"}


# ============================================================================
# start_work_order / begin_wo  (was L2705-2731)
# ============================================================================
async def start_work_order(
    payload: dict,
    context: dict,
    yacht_id: str,
    user_id: str,
    user_context: dict,
    db_client: Client,
) -> dict:
    work_order_id = payload.get("work_order_id")

    # Note: started_at column doesn't exist, just update status
    update_data = {
        "status": "in_progress",
        "updated_by": user_id,
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    wo_result = db_client.table("pms_work_orders").update(update_data).eq("id", work_order_id).eq("yacht_id", yacht_id).execute()
    if wo_result.data:
        try:
            ledger_event = build_ledger_event(
                yacht_id=yacht_id, user_id=user_id, event_type="status_change",
                entity_type="work_order", entity_id=work_order_id, action="start_work_order",
                user_role=user_context.get("role"), change_summary="Work order started",
            )
            db_client.table("ledger_events").insert(ledger_event).execute()
        except Exception as ledger_err:
            if "204" not in str(ledger_err):
                logger.warning(f"[Ledger] Failed to record start_work_order: {ledger_err}")
        return {"status": "success", "message": "Work order started"}
    else:
        return {"status": "error", "error_code": "UPDATE_FAILED", "message": "Failed to start work order"}


# ============================================================================
# cancel_work_order / cancel_wo  (was L2733-2759)
# ============================================================================
async def cancel_work_order(
    payload: dict,
    context: dict,
    yacht_id: str,
    user_id: str,
    user_context: dict,
    db_client: Client,
) -> dict:
    work_order_id = payload.get("work_order_id")

    # Note: cancellation columns don't exist, just update status and add note
    update_data = {
        "status": "cancelled",
        "updated_by": user_id,
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    wo_result = db_client.table("pms_work_orders").update(update_data).eq("id", work_order_id).eq("yacht_id", yacht_id).execute()
    if wo_result.data:
        try:
            ledger_event = build_ledger_event(
                yacht_id=yacht_id, user_id=user_id, event_type="status_change",
                entity_type="work_order", entity_id=work_order_id, action="cancel_work_order",
                user_role=user_context.get("role"), change_summary="Work order cancelled",
            )
            db_client.table("ledger_events").insert(ledger_event).execute()
        except Exception as ledger_err:
            if "204" not in str(ledger_err):
                logger.warning(f"[Ledger] Failed to record cancel_work_order: {ledger_err}")
        return {"status": "success", "message": "Work order cancelled"}
    else:
        return {"status": "error", "error_code": "UPDATE_FAILED", "message": "Failed to cancel work order"}


# ============================================================================
# create_work_order / create_wo  (was L2761-2856)
# ============================================================================
async def create_work_order(
    payload: dict,
    context: dict,
    yacht_id: str,
    user_id: str,
    user_context: dict,
    db_client: Client,
) -> dict:
    # Validate required fields
    title = payload.get("title")
    if not title:
        raise HTTPException(status_code=400, detail="title is required")

    # Map priority
    raw_priority = payload.get("priority", "routine")
    priority_map = {"normal": "routine", "low": "routine", "medium": "routine", "high": "critical"}
    priority = priority_map.get(raw_priority, raw_priority if raw_priority in ("routine", "emergency", "critical") else "routine")

    # Department-level RBAC for crew (2026-02-09)
    user_role = user_context.get("role")
    if user_role == "crew":
        # Get user's department from TENANT DB (stored in metadata JSON)
        try:
            user_dept_result = db_client.table("auth_users_profiles").select("metadata").eq("id", user_id).eq("yacht_id", yacht_id).maybe_single().execute()
            if user_dept_result.data and user_dept_result.data.get("metadata"):
                # Department is stored in metadata->department JSON field
                user_dept = user_dept_result.data["metadata"].get("department")
                # Normalize to lowercase for comparison
                user_dept = user_dept.lower() if user_dept else None
            else:
                user_dept = None
        except Exception:
            # User doesn't have a profile record - no department
            user_dept = None

        # Get work order department from payload
        wo_dept = payload.get("department")

        # Require department in payload
        if not wo_dept:
            raise HTTPException(status_code=400, detail="department is required for crew")

        # Normalize to lowercase for comparison
        wo_dept = wo_dept.lower() if wo_dept else None

        # Require crew to have a department in profile
        if not user_dept:
            raise HTTPException(status_code=403, detail="Crew user must have a department assigned in their profile")

        # Enforce department match
        if user_dept != wo_dept:
            raise HTTPException(
                status_code=403,
                detail=f"Crew can only create work orders for their department (user: {user_dept}, work order: {wo_dept})"
            )

    wo_data = {
        "yacht_id": yacht_id,
        "equipment_id": payload.get("equipment_id"),
        "title": title,
        "description": payload.get("description", ""),
        "priority": priority,
        "status": "planned",
        "work_order_type": payload.get("work_order_type", "corrective"),
        "created_by": user_id,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    wo_result = db_client.table("pms_work_orders").insert(wo_data).execute()
    if wo_result.data:
        work_order_id = wo_result.data[0]["id"]
        execution_id = str(uuid_module.uuid4())

        # Create audit log entry
        try:
            audit_entry = {
                "id": str(uuid_module.uuid4()),
                "yacht_id": yacht_id,
                "action": "create_work_order",
                "entity_type": "work_order",
                "entity_id": work_order_id,
                "user_id": user_id,
                "old_values": {},
                "new_values": wo_data,
                "signature": {
                    "user_id": user_id,
                    "execution_id": execution_id,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "action": "create_work_order"
                }
            }
            db_client.table("pms_audit_log").insert(audit_entry).execute()
            logger.info(f"Audit log created for create_work_order: execution_id={execution_id}")
        except Exception as audit_err:
            # Log audit failure but don't fail the action
            logger.warning(f"Audit log failed for create_work_order (work_order_id={work_order_id}): {audit_err}")

        return {"status": "success", "work_order_id": work_order_id, "message": "Work order created"}
    else:
        return {"status": "error", "error_code": "INSERT_FAILED", "message": "Failed to create work order"}


# ============================================================================
# list_work_orders  (was L2858-2876)
# ============================================================================
async def list_work_orders(
    payload: dict,
    context: dict,
    yacht_id: str,
    user_id: str,
    user_context: dict,
    db_client: Client,
) -> dict:
    logger.info(f"[WORK_ORDER] Listing work orders - yacht_id={yacht_id}")

    from handlers.list_handlers import ListHandlers
    list_handlers_instance = ListHandlers(db_client)

    # Extract filters from payload
    filters = payload.get("filters", {})
    params = payload.get("params", {})

    result = await list_handlers_instance.list_work_orders(
        yacht_id=yacht_id,
        filters=filters,
        params=params
    )
    return result


# ============================================================================
# view_work_order_detail / view_work_order / get_work_order  (was L2878-2887)
# ============================================================================
async def view_work_order_detail(
    payload: dict,
    context: dict,
    yacht_id: str,
    user_id: str,
    user_context: dict,
    db_client: Client,
) -> dict:
    work_order_id = payload.get("work_order_id")

    wo_result = db_client.table("pms_work_orders").select("*, pms_equipment(*)").eq("id", work_order_id).eq("yacht_id", yacht_id).single().execute()
    if wo_result.data:
        return {"status": "success", "work_order": wo_result.data}
    else:
        return {"status": "error", "error_code": "NOT_FOUND", "message": "Work order not found"}


# ============================================================================
# view_work_order_checklist  (was L3214-3241)
# ============================================================================
async def view_work_order_checklist(
    payload: dict,
    context: dict,
    yacht_id: str,
    user_id: str,
    user_context: dict,
    db_client: Client,
) -> dict:
    work_order_id = payload.get("work_order_id")

    # Check if work order exists and get its metadata
    wo_data = db_client.table("pms_work_orders").select("id, metadata").eq("id", work_order_id).eq("yacht_id", yacht_id).single().execute()
    if not wo_data.data:
        raise HTTPException(status_code=404, detail="Work order not found")

    metadata = wo_data.data.get("metadata", {}) or {}
    checklist = metadata.get("checklist", [])

    # Calculate progress
    total = len(checklist)
    completed = len([item for item in checklist if item.get("completed")])

    return {
        "status": "success",
        "success": True,
        "work_order_id": work_order_id,
        "checklist": checklist,
        "progress": {
            "completed": completed,
            "total": total,
            "percent": round((completed / total * 100) if total > 0 else 0, 1)
        }
    }


# ============================================================================
# view_worklist  (was L3244-3258)
# ============================================================================
async def view_worklist(
    payload: dict,
    context: dict,
    yacht_id: str,
    user_id: str,
    user_context: dict,
    db_client: Client,
) -> dict:
    # Get open work orders as worklist items
    wo_result = db_client.table("pms_work_orders").select(
        "id, title, description, priority, status, created_at"
    ).eq("yacht_id", yacht_id).in_("status", ["planned", "in_progress"]).order("priority", desc=True).limit(50).execute()

    return {
        "status": "success",
        "success": True,
        "worklist": wo_result.data or [],
        "total": len(wo_result.data or [])
    }


# ============================================================================
# add_worklist_task  (was L3260-3299)
# ============================================================================
async def add_worklist_task(
    payload: dict,
    context: dict,
    yacht_id: str,
    user_id: str,
    user_context: dict,
    db_client: Client,
) -> dict:
    task_description = payload.get("task_description") or payload.get("description")
    if not task_description:
        raise HTTPException(status_code=400, detail="task_description is required")

    # Create a work order as a worklist task
    # Map priority
    raw_priority = payload.get("priority", "routine")
    priority_map = {"normal": "routine", "low": "routine", "medium": "routine", "high": "critical"}
    priority = priority_map.get(raw_priority, raw_priority if raw_priority in ("routine", "emergency", "critical") else "routine")

    task_data = {
        "yacht_id": yacht_id,
        "title": task_description[:100] if len(task_description) > 100 else task_description,
        "description": task_description,
        "priority": priority,
        "status": "planned",
        "work_order_type": "task",
        "created_by": user_id,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    task_result = db_client.table("pms_work_orders").insert(task_data).execute()

    if task_result.data:
        return {
            "status": "success",
            "success": True,
            "task_id": task_result.data[0]["id"],
            "message": "Worklist task added"
        }
    else:
        return {
            "status": "error",
            "error_code": "INSERT_FAILED",
            "message": "Failed to add worklist task"
        }


# ============================================================================
# export_worklist  (was L3301-3316)
# ============================================================================
async def export_worklist(
    payload: dict,
    context: dict,
    yacht_id: str,
    user_id: str,
    user_context: dict,
    db_client: Client,
) -> dict:
    # Get all work orders for export
    wo_result = db_client.table("pms_work_orders").select("*").eq("yacht_id", yacht_id).order("created_at", desc=True).execute()

    return {
        "status": "success",
        "success": True,
        "data": wo_result.data or [],
        "total": len(wo_result.data or []),
        "export_format": "json",
        "exported_at": datetime.now(timezone.utc).isoformat()
    }


# ============================================================================
# view_work_order_history  (was L3528-3548)
# ============================================================================
async def view_work_order_history(
    payload: dict,
    context: dict,
    yacht_id: str,
    user_id: str,
    user_context: dict,
    db_client: Client,
) -> dict:
    equipment_id = payload.get("equipment_id")

    if not equipment_id:
        raise HTTPException(status_code=400, detail="equipment_id is required")

    work_orders = db_client.table("pms_work_orders").select(
        "id, wo_number, title, description, status, priority, created_at, completed_at"
    ).eq("equipment_id", equipment_id).eq("yacht_id", yacht_id).order(
        "created_at", desc=True
    ).limit(50).execute()

    return {
        "status": "success",
        "success": True,
        "work_orders": work_orders.data or [],
        "count": len(work_orders.data) if work_orders.data else 0
    }


# ============================================================================
# update_worklist_progress  (was L5429-5497)
# ============================================================================
async def update_worklist_progress(
    payload: dict,
    context: dict,
    yacht_id: str,
    user_id: str,
    user_context: dict,
    db_client: Client,
) -> dict:
    worklist_item_id = payload.get("worklist_item_id")
    progress = payload.get("progress")  # Percentage 0-100
    notes = payload.get("notes", "")

    if not worklist_item_id:
        raise HTTPException(status_code=400, detail="worklist_item_id is required")
    if progress is None:
        raise HTTPException(status_code=400, detail="progress is required")

    try:
        # Try to update in worklist_items table
        update_data = {
            "progress": int(progress),
            "updated_by": user_id,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        if notes:
            update_data["notes"] = notes

        db_client.table("worklist_items").update(update_data).eq(
            "id", worklist_item_id
        ).eq("yacht_id", yacht_id).execute()

        return {
            "status": "success",
            "success": True,
            "message": f"Progress updated to {progress}%",
            "worklist_item_id": worklist_item_id,
            "progress": int(progress)
        }
    except Exception:
        # Try worklist table with metadata
        try:
            item = db_client.table("worklist").select("id, metadata").eq(
                "id", worklist_item_id
            ).eq("yacht_id", yacht_id).maybe_single().execute()

            if item.data:
                metadata = item.data.get("metadata", {}) or {}
                metadata["progress"] = int(progress)
                if notes:
                    metadata["progress_notes"] = notes
                metadata["progress_updated_at"] = datetime.now(timezone.utc).isoformat()
                metadata["progress_updated_by"] = user_id

                db_client.table("worklist").update({
                    "metadata": metadata
                }).eq("id", worklist_item_id).execute()

            return {
                "status": "success",
                "success": True,
                "message": f"Progress updated to {progress}%",
                "worklist_item_id": worklist_item_id,
                "progress": int(progress)
            }
        except Exception:
            return {
                "status": "success",
                "success": True,
                "message": "Progress update registered",
                "worklist_item_id": worklist_item_id,
                "progress": int(progress)
            }


# ============================================================================
# create_work_order_for_equipment  (was L6312-6351)
# ============================================================================
async def create_work_order_for_equipment(
    payload: dict,
    context: dict,
    yacht_id: str,
    user_id: str,
    user_context: dict,
    db_client: Client,
) -> dict:
    # resolve_entity_context already mapped entity_id → equipment_id
    equipment_id = payload.get("equipment_id") or context.get("equipment_id")
    title = payload.get("title", "Work Order")
    description = payload.get("description", "")
    priority = payload.get("priority", "routine")
    wo_type = payload.get("type", "corrective")
    if not equipment_id:
        raise HTTPException(status_code=400, detail="equipment_id is required")
    wo_data = {
        "id": str(uuid_module.uuid4()),
        "yacht_id": yacht_id,
        "equipment_id": equipment_id,
        "title": title,
        "description": description,
        "priority": priority,
        "type": wo_type,
        "status": "planned",
        "created_by": user_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    wo_result = db_client.table("pms_work_orders").insert(wo_data).execute()
    if wo_result.data:
        wo_id = wo_result.data[0]["id"]
        try:
            ledger_event = build_ledger_event(
                yacht_id=yacht_id, user_id=user_id, event_type="create",
                entity_type="work_order", entity_id=wo_id, action="create_work_order_for_equipment",
                user_role=user_context.get("role"), change_summary=f"Work order created for equipment {equipment_id}",
            )
            db_client.table("ledger_events").insert(ledger_event).execute()
        except Exception as ledger_err:
            if "204" not in str(ledger_err):
                logger.warning(f"[Ledger] Failed to record create_work_order_for_equipment: {ledger_err}")
        return {"status": "success", "work_order_id": wo_id, "message": "Work order created for equipment"}
    else:
        return {"status": "error", "error_code": "CREATE_FAILED", "message": "Failed to create work order"}


# ============================================================================
# add_work_order_photo  (was L2695-2774)
# ============================================================================
async def add_work_order_photo(
    payload: dict,
    context: dict,
    yacht_id: str,
    user_id: str,
    user_context: dict,
    db_client: Client,
) -> dict:
    work_order_id = payload.get("work_order_id")
    photo_url = payload.get("photo_url")

    if not work_order_id:
        raise HTTPException(status_code=400, detail="work_order_id is required")
    if not photo_url:
        raise HTTPException(status_code=400, detail="photo_url is required")

    # Check if work order exists
    try:
        check = db_client.table("pms_work_orders").select("id").eq("id", work_order_id).eq("yacht_id", yacht_id).single().execute()
        if not check.data:
            raise HTTPException(status_code=404, detail="Work order not found")
    except HTTPException:
        raise  # Re-raise our own 404
    except Exception as e:
        # Supabase single() raises exception when 0 rows found
        error_str = str(e)
        if "PGRST116" in error_str or "0 rows" in error_str or "result contains 0 rows" in error_str.lower():
            raise HTTPException(status_code=404, detail="Work order not found")
        # Re-raise other exceptions as 500
        raise

    # Store photo URL in metadata (work orders don't have a dedicated photos table)
    wo_data = db_client.table("pms_work_orders").select("metadata").eq("id", work_order_id).single().execute()
    metadata = wo_data.data.get("metadata", {}) if wo_data.data else {}
    if not metadata:
        metadata = {}
    photos = metadata.get("photos", [])
    photos.append({
        "url": photo_url,
        "caption": payload.get("caption", ""),
        "added_by": user_id,
        "added_at": datetime.now(timezone.utc).isoformat()
    })
    metadata["photos"] = photos

    db_client.table("pms_work_orders").update({
        "metadata": metadata,
        "updated_at": datetime.now(timezone.utc).isoformat()
    }).eq("id", work_order_id).eq("yacht_id", yacht_id).execute()

    # Record ledger event
    try:
        ledger_event = build_ledger_event(
            yacht_id=yacht_id,
            user_id=user_id,
            event_type="update",
            entity_type="work_order",
            entity_id=work_order_id,
            action="add_work_order_photo",
            user_role=user_context.get("role", "member"),
            change_summary="Photo added to work order",
            metadata={
                "photo_url": photo_url,
                "caption": payload.get("caption", ""),
                "domain": "Work Orders"
            }
        )
        try:
            db_client.table("ledger_events").insert(ledger_event).execute()
            logger.info(f"[Ledger] add_work_order_photo recorded for {work_order_id}")
        except Exception as e:
            if "204" in str(e):
                logger.info(f"[Ledger] add_work_order_photo recorded (204)")
            else:
                logger.warning(f"[Ledger] Failed: {e}")
    except Exception as e:
        logger.warning(f"[Ledger] Failed to prepare event: {e}")

    return {
        "status": "success",
        "success": True,
        "work_order_id": work_order_id,
        "message": "Photo added to work order"
    }


# ============================================================================
# add_parts_to_work_order  (was L2777-2857)
# ============================================================================
async def add_parts_to_work_order(
    payload: dict,
    context: dict,
    yacht_id: str,
    user_id: str,
    user_context: dict,
    db_client: Client,
) -> dict:
    work_order_id = payload.get("work_order_id")
    part_id = payload.get("part_id")

    if not work_order_id:
        raise HTTPException(status_code=400, detail="work_order_id is required")
    if not part_id:
        raise HTTPException(status_code=400, detail="part_id is required")

    # Check if work order exists
    try:
        check = db_client.table("pms_work_orders").select("id").eq("id", work_order_id).eq("yacht_id", yacht_id).single().execute()
        if not check.data:
            raise HTTPException(status_code=404, detail="Work order not found")
    except HTTPException:
        raise  # Re-raise our own 404
    except Exception as e:
        # Supabase single() raises exception when 0 rows found
        error_str = str(e)
        if "PGRST116" in error_str or "0 rows" in error_str or "result contains 0 rows" in error_str.lower():
            raise HTTPException(status_code=404, detail="Work order not found")
        # Re-raise other exceptions as 500
        raise

    # Store part link in metadata
    wo_data = db_client.table("pms_work_orders").select("metadata").eq("id", work_order_id).single().execute()
    metadata = wo_data.data.get("metadata", {}) if wo_data.data else {}
    if not metadata:
        metadata = {}
    parts = metadata.get("parts", [])
    parts.append({
        "part_id": part_id,
        "quantity": payload.get("quantity", 1),
        "added_by": user_id,
        "added_at": datetime.now(timezone.utc).isoformat()
    })
    metadata["parts"] = parts

    db_client.table("pms_work_orders").update({
        "metadata": metadata,
        "updated_at": datetime.now(timezone.utc).isoformat()
    }).eq("id", work_order_id).eq("yacht_id", yacht_id).execute()

    # Record ledger event
    try:
        ledger_event = build_ledger_event(
            yacht_id=yacht_id,
            user_id=user_id,
            event_type="update",
            entity_type="work_order",
            entity_id=work_order_id,
            action="add_parts_to_work_order",
            user_role=user_context.get("role", "member"),
            change_summary=f"Part {part_id} added (qty: {payload.get('quantity', 1)})",
            metadata={
                "part_id": part_id,
                "quantity": payload.get("quantity", 1),
                "domain": "Work Orders"
            }
        )
        try:
            db_client.table("ledger_events").insert(ledger_event).execute()
            logger.info(f"[Ledger] add_parts_to_work_order recorded for {work_order_id}")
        except Exception as e:
            if "204" in str(e):
                logger.info(f"[Ledger] add_parts_to_work_order recorded (204)")
            else:
                logger.warning(f"[Ledger] Failed: {e}")
    except Exception as e:
        logger.warning(f"[Ledger] Failed to prepare event: {e}")

    return {
        "status": "success",
        "success": True,
        "work_order_id": work_order_id,
        "part_id": part_id,
        "message": "Part added to work order"
    }


# ============================================================================
# HANDLER REGISTRY
# ============================================================================
HANDLERS: dict = {
    # update_work_order / update_wo
    "update_work_order":                update_work_order,
    "update_wo":                        update_work_order,
    # assign_work_order / assign_wo
    "assign_work_order":                assign_work_order,
    "assign_wo":                        assign_work_order,
    # close_work_order / complete_work_order
    "close_work_order":                 close_work_order,
    "complete_work_order":              close_work_order,
    # add_wo_hours / log_work_hours
    "add_wo_hours":                     add_wo_hours,
    "log_work_hours":                   add_wo_hours,
    # add_wo_part / add_part_to_wo
    "add_wo_part":                      add_wo_part,
    "add_part_to_wo":                   add_wo_part,
    # add_wo_note / add_note_to_wo
    "add_wo_note":                      add_wo_note,
    "add_note_to_wo":                   add_wo_note,
    # start_work_order / begin_wo
    "start_work_order":                 start_work_order,
    "begin_wo":                         start_work_order,
    # cancel_work_order / cancel_wo
    "cancel_work_order":                cancel_work_order,
    "cancel_wo":                        cancel_work_order,
    # create_work_order / create_wo
    "create_work_order":                create_work_order,
    "create_wo":                        create_work_order,
    # list_work_orders
    "list_work_orders":                 list_work_orders,
    # view_work_order_detail / view_work_order / get_work_order
    "view_work_order_detail":           view_work_order_detail,
    "view_work_order":                  view_work_order_detail,
    "get_work_order":                   view_work_order_detail,
    # view_work_order_checklist
    "view_work_order_checklist":        view_work_order_checklist,
    # view_worklist
    "view_worklist":                    view_worklist,
    # add_worklist_task
    "add_worklist_task":                add_worklist_task,
    # export_worklist
    "export_worklist":                  export_worklist,
    # view_work_order_history
    "view_work_order_history":          view_work_order_history,
    # update_worklist_progress
    "update_worklist_progress":         update_worklist_progress,
    # create_work_order_for_equipment
    "create_work_order_for_equipment":  create_work_order_for_equipment,
    # add_work_order_photo
    "add_work_order_photo":             add_work_order_photo,
    # add_parts_to_work_order
    "add_parts_to_work_order":          add_parts_to_work_order,
}
