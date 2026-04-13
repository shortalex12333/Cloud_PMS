# routes/handlers/fault_handler.py
#
# Phase 5 Task 2 — Fault management actions migrated from p0_actions_routes.py
# 13 handlers: report_fault, acknowledge_fault, resolve_fault, diagnose_fault,
#              close_fault, update_fault, reopen_fault, mark_fault_false_alarm,
#              add_fault_photo, view_fault_detail, view_fault_history,
#              add_fault_note, list_faults

from datetime import datetime, timezone
import uuid as uuid_module
import logging
from fastapi import HTTPException
from supabase import Client
from routes.handlers.ledger_utils import build_ledger_event
from action_router.middleware import validate_state_transition, InvalidStateTransitionError

logger = logging.getLogger(__name__)


async def report_fault(
    payload: dict,
    context: dict,
    yacht_id: str,
    user_id: str,
    user_context: dict,
    db_client: Client,
) -> dict:
    if not payload.get("equipment_id"):
        raise HTTPException(status_code=400, detail="equipment_id is required")
    description = payload.get("description", "")
    if len(description) < 10:
        raise HTTPException(status_code=400, detail="description must be at least 10 characters")

    severity = payload.get("severity", "medium")
    if severity not in ("low", "medium", "high", "critical"):
        severity = "medium"

    fault_title = payload.get("title", description[:100] if description else "Reported fault")
    fault_data = {
        "yacht_id": yacht_id,
        "equipment_id": payload.get("equipment_id"),
        "fault_code": payload.get("fault_code", "MANUAL"),
        "title": fault_title,
        "description": description,
        "severity": severity,
        "status": "open",
        "detected_at": datetime.now(timezone.utc).isoformat(),
        "metadata": {"reported_by": user_id},
    }
    fault_result = db_client.table("pms_faults").insert(fault_data).execute()
    if fault_result.data:
        fault_id = fault_result.data[0]["id"]
        try:
            ledger_event = build_ledger_event(
                yacht_id=yacht_id,
                user_id=user_id,
                event_type="create",
                entity_type="fault",
                entity_id=fault_id,
                action="report_fault",
                user_role=user_context.get("role"),
                change_summary=f"Fault reported: {fault_title}",
                entity_name=fault_title,
                new_state={
                    "title": fault_title,
                    "status": "open",
                    "severity": severity,
                    "equipment_id": payload.get("equipment_id"),
                },
            )
            db_client.table("ledger_events").insert(ledger_event).execute()
        except Exception as ledger_err:
            if "204" in str(ledger_err):
                pass
            else:
                logger.warning(f"[Ledger] Failed to record report_fault: {ledger_err}")
        return {
            "status": "success",
            "fault_id": fault_id,
            "message": "Fault reported successfully",
        }
    return {
        "status": "error",
        "error_code": "INSERT_FAILED",
        "message": "Failed to create fault record",
    }


async def acknowledge_fault(
    payload: dict,
    context: dict,
    yacht_id: str,
    user_id: str,
    user_context: dict,
    db_client: Client,
) -> dict:
    fault_id = payload.get("fault_id")
    if not fault_id:
        raise HTTPException(status_code=400, detail="fault_id is required")
    execution_id = str(uuid_module.uuid4())

    check = (
        db_client.table("pms_faults")
        .select("id, status, severity, title")
        .eq("id", fault_id)
        .eq("yacht_id", yacht_id)
        .single()
        .execute()
    )
    if not check.data:
        raise HTTPException(status_code=404, detail="Fault not found")

    old_status = check.data.get("status", "unknown")
    old_severity = check.data.get("severity", "unknown")
    entity_name = check.data.get("title") or ""

    update_data = {
        "status": "investigating",
        # DB invariant: pms_faults check constraint requires a non-null severity on every UPDATE.
        # "medium" is the safe sentinel — this does not reflect a business-logic change.
        "severity": "medium",
        "updated_by": user_id,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

    fault_result = (
        db_client.table("pms_faults")
        .update(update_data)
        .eq("id", fault_id)
        .eq("yacht_id", yacht_id)
        .execute()
    )
    if fault_result.data:
        try:
            audit_entry = {
                "id": str(uuid_module.uuid4()),
                "yacht_id": yacht_id,
                "action": "acknowledge_fault",
                "entity_type": "fault",
                "entity_id": fault_id,
                "user_id": user_id,
                "old_values": {"status": old_status, "severity": old_severity},
                "new_values": {
                    "status": "investigating",
                    "severity": "medium",
                    "note": payload.get("note"),
                },
                "signature": {},
            }
            db_client.table("pms_audit_log").insert(audit_entry).execute()
            logger.info(f"Audit log created for acknowledge_fault: execution_id={execution_id}")
        except Exception as audit_err:
            logger.warning(f"Audit log failed for acknowledge_fault (fault_id={fault_id}): {audit_err}")

        try:
            ledger_event = build_ledger_event(
                yacht_id=yacht_id,
                user_id=user_id,
                event_type="status_change",
                entity_type="fault",
                entity_id=fault_id,
                action="acknowledge_fault",
                user_role=user_context.get("role"),
                change_summary=f"Fault acknowledged — status: {old_status} → investigating",
                entity_name=entity_name,
                previous_state={"status": old_status, "severity": old_severity},
                new_state={"status": "investigating", "severity": "medium"},
            )
            db_client.table("ledger_events").insert(ledger_event).execute()
        except Exception as ledger_err:
            if "204" in str(ledger_err):
                pass
            else:
                logger.warning(f"[Ledger] Failed to record acknowledge_fault: {ledger_err}")

        return {
            "status": "success",
            "message": "Fault acknowledged",
            "execution_id": execution_id,
            "fault_id": fault_id,
            "new_status": "investigating",
        }
    return {"status": "error", "error_code": "UPDATE_FAILED", "message": "Failed to acknowledge fault"}


async def resolve_fault(
    payload: dict,
    context: dict,
    yacht_id: str,
    user_id: str,
    user_context: dict,
    db_client: Client,
) -> dict:
    fault_id = payload.get("fault_id")
    if not fault_id:
        raise HTTPException(status_code=400, detail="fault_id is required")

    check = (
        db_client.table("pms_faults")
        .select("id, status, title")
        .eq("id", fault_id)
        .eq("yacht_id", yacht_id)
        .single()
        .execute()
    )
    if not check.data:
        raise HTTPException(status_code=404, detail="Fault not found")

    prev_status = check.data.get("status", "unknown")
    entity_name = check.data.get("title") or ""
    resolution_notes = payload.get("resolution_notes") or payload.get("note") or ""

    now = datetime.now(timezone.utc).isoformat()
    update_data = {
        "status": "resolved",
        # DB invariant: pms_faults check constraint requires a non-null severity on every UPDATE.
        # "medium" is the safe sentinel — this does not reflect a business-logic change.
        "severity": "medium",
        "resolved_by": user_id,
        "resolved_at": now,
        "updated_by": user_id,
        "updated_at": now,
    }

    fault_result = (
        db_client.table("pms_faults")
        .update(update_data)
        .eq("id", fault_id)
        .eq("yacht_id", yacht_id)
        .execute()
    )
    if fault_result.data:
        try:
            new_state = {"status": "resolved", "resolved_by": user_id}
            if resolution_notes:
                new_state["resolution_notes"] = resolution_notes
            ledger_event = build_ledger_event(
                yacht_id=yacht_id,
                user_id=user_id,
                event_type="status_change",
                entity_type="fault",
                entity_id=fault_id,
                action="resolve_fault",
                user_role=user_context.get("role"),
                change_summary=f"Fault resolved — status: {prev_status} → resolved",
                entity_name=entity_name,
                previous_state={"status": prev_status},
                new_state=new_state,
            )
            db_client.table("ledger_events").insert(ledger_event).execute()
        except Exception as ledger_err:
            if "204" not in str(ledger_err):
                logger.warning(f"[Ledger] Failed to record resolve_fault: {ledger_err}")
        return {"status": "success", "message": "Fault resolved", "_ledger_written": True}
    return {"status": "error", "error_code": "UPDATE_FAILED", "message": "Failed to resolve fault"}


async def diagnose_fault(
    payload: dict,
    context: dict,
    yacht_id: str,
    user_id: str,
    user_context: dict,
    db_client: Client,
) -> dict:
    fault_id = payload.get("fault_id")
    if not fault_id:
        raise HTTPException(status_code=400, detail="fault_id is required")

    current = (
        db_client.table("pms_faults")
        .select("id, metadata, title")
        .eq("id", fault_id)
        .eq("yacht_id", yacht_id)
        .single()
        .execute()
    )
    if not current.data:
        raise HTTPException(status_code=404, detail="Fault not found")

    entity_name = current.data.get("title") or ""
    diagnosis_text = payload.get("diagnosis", "")

    metadata = current.data.get("metadata", {}) or {}
    metadata["diagnosis"] = diagnosis_text
    metadata["diagnosed_by"] = user_id
    metadata["diagnosed_at"] = datetime.now(timezone.utc).isoformat()

    update_data = {
        "metadata": metadata,
        # DB invariant: pms_faults check constraint requires a non-null severity on every UPDATE.
        # "medium" is the safe sentinel — this does not reflect a business-logic change.
        "severity": "medium",
        "updated_by": user_id,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

    fault_result = (
        db_client.table("pms_faults")
        .update(update_data)
        .eq("id", fault_id)
        .eq("yacht_id", yacht_id)
        .execute()
    )
    if fault_result.data:
        try:
            ledger_event = build_ledger_event(
                yacht_id=yacht_id,
                user_id=user_id,
                event_type="update",
                entity_type="fault",
                entity_id=fault_id,
                action="diagnose_fault",
                user_role=user_context.get("role"),
                change_summary="Fault diagnosed",
                entity_name=entity_name,
                new_state={"diagnosis": diagnosis_text, "diagnosed_by": user_id},
            )
            db_client.table("ledger_events").insert(ledger_event).execute()
        except Exception as ledger_err:
            if "204" in str(ledger_err):
                pass
            else:
                logger.warning(f"[Ledger] Failed to record diagnose_fault: {ledger_err}")
        return {"status": "success", "message": "Diagnosis added"}
    return {"status": "error", "error_code": "UPDATE_FAILED", "message": "Failed to add diagnosis"}


async def close_fault(
    payload: dict,
    context: dict,
    yacht_id: str,
    user_id: str,
    user_context: dict,
    db_client: Client,
) -> dict:
    fault_id = payload.get("fault_id")
    if not fault_id:
        raise HTTPException(status_code=400, detail="fault_id is required")

    check = (
        db_client.table("pms_faults")
        .select("id, status, title")
        .eq("id", fault_id)
        .eq("yacht_id", yacht_id)
        .single()
        .execute()
    )
    if not check.data:
        raise HTTPException(status_code=404, detail="Fault not found")

    current_status = check.data.get("status", "open")
    entity_name = check.data.get("title") or ""
    try:
        validate_state_transition("fault", current_status, "close_fault")
    except InvalidStateTransitionError as e:
        logger.warning(f"[STATE] {e.message}")
        return {
            "success": False,
            "code": e.code,
            "message": e.message,
            "current_status": current_status,
        }

    update_data = {
        "status": "closed",
        # DB invariant: pms_faults check constraint requires a non-null severity on every UPDATE.
        # "medium" is the safe sentinel — this does not reflect a business-logic change.
        "severity": "medium",
        "updated_by": user_id,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

    fault_result = (
        db_client.table("pms_faults")
        .update(update_data)
        .eq("id", fault_id)
        .eq("yacht_id", yacht_id)
        .execute()
    )
    if fault_result.data:
        try:
            ev = build_ledger_event(
                yacht_id=yacht_id,
                user_id=user_id,
                event_type="status_change",
                entity_type="fault",
                entity_id=fault_id,
                action="close_fault",
                user_role=user_context.get("role"),
                change_summary=f"Fault closed — status: {current_status} → closed",
                entity_name=entity_name,
                previous_state={"status": current_status},
                new_state={"status": "closed"},
            )
            db_client.table("ledger_events").insert(ev).execute()
        except Exception as ledger_err:
            if "204" in str(ledger_err):
                pass
            else:
                logger.warning(f"[Ledger] Failed: {ledger_err}")
        return {"status": "success", "message": "Fault closed"}
    return {"status": "error", "error_code": "UPDATE_FAILED", "message": "Failed to close fault"}


async def update_fault(
    payload: dict,
    context: dict,
    yacht_id: str,
    user_id: str,
    user_context: dict,
    db_client: Client,
) -> dict:
    fault_id = payload.get("fault_id")
    if not fault_id:
        raise HTTPException(status_code=400, detail="fault_id is required")

    check = (
        db_client.table("pms_faults")
        .select("id, title, description, severity, status")
        .eq("id", fault_id)
        .eq("yacht_id", yacht_id)
        .single()
        .execute()
    )
    if not check.data:
        raise HTTPException(status_code=404, detail="Fault not found")

    prev = check.data
    entity_name = prev.get("title") or ""

    update_data = {
        "updated_by": user_id,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    if payload.get("title"):
        update_data["title"] = payload["title"]
    if payload.get("description"):
        update_data["description"] = payload["description"]

    if payload.get("severity") and payload["severity"] in ("low", "medium", "high", "critical"):
        update_data["severity"] = payload["severity"]
    else:
        # DB invariant sentinel: no valid severity supplied by caller; default to "medium" to satisfy check constraint.
        logger.debug(f"[update_fault] severity '{payload.get('severity')}' not in valid set; using 'medium' sentinel.")
        update_data["severity"] = "medium"

    fault_result = (
        db_client.table("pms_faults")
        .update(update_data)
        .eq("id", fault_id)
        .eq("yacht_id", yacht_id)
        .execute()
    )
    if fault_result.data:
        try:
            # Compute per-field diffs for change_summary
            diff_fields = ("title", "description", "severity")
            changes = []
            for f in diff_fields:
                old_val = prev.get(f)
                new_val = update_data.get(f)
                if new_val is not None and old_val != new_val:
                    changes.append(f"{f}: {old_val} → {new_val}")
            summary = "Fault updated" + (" — " + ", ".join(changes) if changes else "")

            prev_state = {f: prev.get(f) for f in diff_fields}
            new_state = {f: update_data.get(f, prev.get(f)) for f in diff_fields}

            ledger_event = build_ledger_event(
                yacht_id=yacht_id,
                user_id=user_id,
                event_type="update",
                entity_type="fault",
                entity_id=fault_id,
                action="update_fault",
                user_role=user_context.get("role"),
                change_summary=summary,
                entity_name=entity_name,
                previous_state=prev_state,
                new_state=new_state,
            )
            db_client.table("ledger_events").insert(ledger_event).execute()
        except Exception as ledger_err:
            if "204" in str(ledger_err):
                pass
            else:
                logger.warning(f"[Ledger] Failed to record update_fault: {ledger_err}")
        return {"status": "success", "message": "Fault updated"}
    return {"status": "error", "error_code": "UPDATE_FAILED", "message": "Failed to update fault"}


async def reopen_fault(
    payload: dict,
    context: dict,
    yacht_id: str,
    user_id: str,
    user_context: dict,
    db_client: Client,
) -> dict:
    fault_id = payload.get("fault_id")
    if not fault_id:
        raise HTTPException(status_code=400, detail="fault_id is required")

    check = (
        db_client.table("pms_faults")
        .select("id, status, title")
        .eq("id", fault_id)
        .eq("yacht_id", yacht_id)
        .single()
        .execute()
    )
    if not check.data:
        raise HTTPException(status_code=404, detail="Fault not found")

    current_status = check.data.get("status", "open")
    entity_name = check.data.get("title") or ""
    try:
        validate_state_transition("fault", current_status, "reopen_fault")
    except InvalidStateTransitionError as e:
        logger.warning(f"[STATE] {e.message}")
        return {
            "success": False,
            "code": e.code,
            "message": e.message,
            "current_status": current_status,
        }

    update_data = {
        "status": "open",
        # DB invariant: pms_faults check constraint requires a non-null severity on every UPDATE.
        # "medium" is the safe sentinel — this does not reflect a business-logic change.
        "severity": "medium",
        "resolved_at": None,
        "resolved_by": None,
        "updated_by": user_id,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

    fault_result = (
        db_client.table("pms_faults")
        .update(update_data)
        .eq("id", fault_id)
        .eq("yacht_id", yacht_id)
        .execute()
    )
    if fault_result.data:
        try:
            ledger_event = build_ledger_event(
                yacht_id=yacht_id,
                user_id=user_id,
                event_type="status_change",
                entity_type="fault",
                entity_id=fault_id,
                action="reopen_fault",
                user_role=user_context.get("role"),
                change_summary=f"Fault reopened — status: {current_status} → open",
                entity_name=entity_name,
                previous_state={"status": current_status},
                new_state={"status": "open"},
            )
            db_client.table("ledger_events").insert(ledger_event).execute()
        except Exception as ledger_err:
            if "204" in str(ledger_err):
                pass
            else:
                logger.warning(f"[Ledger] Failed to record reopen_fault: {ledger_err}")
        return {"status": "success", "message": "Fault reopened"}
    return {"status": "error", "error_code": "UPDATE_FAILED", "message": "Failed to reopen fault"}


async def mark_fault_false_alarm(
    payload: dict,
    context: dict,
    yacht_id: str,
    user_id: str,
    user_context: dict,
    db_client: Client,
) -> dict:
    fault_id = payload.get("fault_id")
    if not fault_id:
        raise HTTPException(status_code=400, detail="fault_id is required")

    current = (
        db_client.table("pms_faults")
        .select("id, metadata, title, status")
        .eq("id", fault_id)
        .eq("yacht_id", yacht_id)
        .single()
        .execute()
    )
    if not current.data:
        raise HTTPException(status_code=404, detail="Fault not found")

    entity_name = current.data.get("title") or ""
    prev_status = current.data.get("status", "open")

    metadata = current.data.get("metadata", {}) or {}
    metadata["false_alarm"] = True
    metadata["false_alarm_by"] = user_id
    metadata["false_alarm_at"] = datetime.now(timezone.utc).isoformat()

    update_data = {
        "status": "closed",
        "metadata": metadata,
        # DB invariant: pms_faults check constraint requires a non-null severity on every UPDATE.
        # "medium" is the safe sentinel — this does not reflect a business-logic change.
        "severity": "medium",
        "updated_by": user_id,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

    fault_result = (
        db_client.table("pms_faults")
        .update(update_data)
        .eq("id", fault_id)
        .eq("yacht_id", yacht_id)
        .execute()
    )
    if fault_result.data:
        try:
            ledger_event = build_ledger_event(
                yacht_id=yacht_id,
                user_id=user_id,
                event_type="status_change",
                entity_type="fault",
                entity_id=fault_id,
                action="mark_fault_false_alarm",
                user_role=user_context.get("role"),
                change_summary=f"Fault marked as false alarm — status: {prev_status} → closed",
                entity_name=entity_name,
                previous_state={"status": prev_status},
                new_state={"status": "closed", "false_alarm": True},
            )
            db_client.table("ledger_events").insert(ledger_event).execute()
        except Exception as ledger_err:
            if "204" in str(ledger_err):
                pass
            else:
                logger.warning(f"[Ledger] Failed to record mark_fault_false_alarm: {ledger_err}")
        return {"status": "success", "message": "Fault marked as false alarm"}
    return {"status": "error", "error_code": "UPDATE_FAILED", "message": "Failed to mark as false alarm"}


async def add_fault_photo(
    payload: dict,
    context: dict,
    yacht_id: str,
    user_id: str,
    user_context: dict,
    db_client: Client,
) -> dict:
    fault_id = payload.get("fault_id")
    if not fault_id:
        raise HTTPException(status_code=400, detail="fault_id is required")

    current = (
        db_client.table("pms_faults")
        .select("id, metadata")
        .eq("id", fault_id)
        .eq("yacht_id", yacht_id)
        .single()
        .execute()
    )
    if not current.data:
        raise HTTPException(status_code=404, detail="Fault not found")

    photo_url = payload.get("photo_url")
    if not photo_url:
        raise HTTPException(status_code=400, detail="photo_url is required")

    metadata = current.data.get("metadata", {}) or {}
    photos = metadata.get("photos", [])
    photos.append({
        "url": photo_url,
        "added_by": user_id,
        "added_at": datetime.now(timezone.utc).isoformat(),
    })
    metadata["photos"] = photos

    update_data = {
        "metadata": metadata,
        # DB invariant: pms_faults check constraint requires a non-null severity on every UPDATE.
        # "medium" is the safe sentinel — this does not reflect a business-logic change.
        "severity": "medium",
        "updated_by": user_id,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

    fault_result = (
        db_client.table("pms_faults")
        .update(update_data)
        .eq("id", fault_id)
        .eq("yacht_id", yacht_id)
        .execute()
    )
    if fault_result.data:
        return {"status": "success", "message": "Photo added to fault"}
    return {"status": "error", "error_code": "UPDATE_FAILED", "message": "Failed to add photo"}


async def view_fault_detail(
    payload: dict,
    context: dict,
    yacht_id: str,
    user_id: str,
    user_context: dict,
    db_client: Client,
) -> dict:
    fault_id = payload.get("fault_id")
    if not fault_id:
        raise HTTPException(status_code=400, detail="fault_id is required")
    fault_result = (
        db_client.table("pms_faults")
        .select("*, pms_equipment(*)")
        .eq("id", fault_id)
        .eq("yacht_id", yacht_id)
        .single()
        .execute()
    )
    if fault_result.data:
        return {"status": "success", "fault": fault_result.data}
    return {"status": "error", "error_code": "NOT_FOUND", "message": "Fault not found"}


async def view_fault_history(
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

    faults = (
        db_client.table("pms_faults")
        .select("id, title, description, status, severity, detected_at, resolved_at, created_at")
        .eq("equipment_id", equipment_id)
        .eq("yacht_id", yacht_id)
        .order("created_at", desc=True)
        .limit(50)
        .execute()
    )

    return {
        "status": "success",
        "success": True,
        "faults": faults.data or [],
        "count": len(faults.data) if faults.data else 0,
    }


async def add_fault_note(
    payload: dict,
    context: dict,
    yacht_id: str,
    user_id: str,
    user_context: dict,
    db_client: Client,
) -> dict:
    fault_id = payload.get("fault_id")
    note_text = payload.get("note_text", "")

    if not fault_id:
        raise HTTPException(status_code=400, detail="fault_id is required")
    if not note_text:
        raise HTTPException(status_code=400, detail="note_text is required")

    current = (
        db_client.table("pms_faults")
        .select("id, metadata, severity, title")
        .eq("id", fault_id)
        .eq("yacht_id", yacht_id)
        .single()
        .execute()
    )
    if not current.data:
        raise HTTPException(status_code=404, detail="Fault not found")

    entity_name = current.data.get("title") or ""
    metadata = current.data.get("metadata", {}) or {}
    current_severity = current.data.get("severity") or "medium"
    notes = metadata.get("notes", []) or []
    notes.append({
        "text": note_text,
        "added_by": user_id,
        "added_at": datetime.now(timezone.utc).isoformat(),
    })
    metadata["notes"] = notes

    note_result = db_client.table("pms_faults").update({
        "metadata": metadata,
        # Preserve original severity — NOT NULL constraint requires it on every UPDATE.
        "severity": current_severity,
        "updated_by": user_id,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", fault_id).eq("yacht_id", yacht_id).execute()

    if not note_result.data:
        return {"status": "error", "error_code": "UPDATE_FAILED", "message": "Failed to add fault note"}

    try:
        ledger_event = build_ledger_event(
            yacht_id=yacht_id,
            user_id=user_id,
            event_type="update",
            entity_type="fault",
            entity_id=fault_id,
            action="add_fault_note",
            user_role=user_context.get("role"),
            change_summary="Note added to fault",
            entity_name=entity_name,
            new_state={"note_text": note_text, "added_by": user_id},
        )
        db_client.table("ledger_events").insert(ledger_event).execute()
    except Exception as ledger_err:
        if "204" in str(ledger_err):
            pass
        else:
            logger.warning(f"[Ledger] Failed to record add_fault_note: {ledger_err}")

    return {
        "status": "success",
        "success": True,
        "message": "Note added to fault",
        "notes_count": len(notes),
    }


async def list_faults(
    payload: dict,
    context: dict,
    yacht_id: str,
    user_id: str,
    user_context: dict,
    db_client: Client,
) -> dict:
    query = db_client.table("pms_faults").select("*").eq("yacht_id", yacht_id)

    if payload.get("status"):
        query = query.eq("status", payload["status"])
    if payload.get("priority"):
        query = query.eq("severity", payload["priority"])

    limit = payload.get("limit", 50)
    faults_result = query.order("detected_at", desc=True).limit(limit).execute()

    return {
        "status": "success",
        "success": True,
        "faults": faults_result.data or [],
        "total": len(faults_result.data or []),
    }


HANDLERS: dict = {
    "report_fault": report_fault,
    "acknowledge_fault": acknowledge_fault,
    "resolve_fault": resolve_fault,
    "diagnose_fault": diagnose_fault,
    "close_fault": close_fault,
    "update_fault": update_fault,
    "reopen_fault": reopen_fault,
    "mark_fault_false_alarm": mark_fault_false_alarm,
    "add_fault_photo": add_fault_photo,
    "view_fault_detail": view_fault_detail,
    "view_fault_history": view_fault_history,
    "add_fault_note": add_fault_note,
    "list_faults": list_faults,
}
