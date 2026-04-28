# handlers/fault_handler.py
#
# Fault domain — single source of truth.
# All fault actions resolve in 1 hop from the dispatch table.
#
# DB tables: pms_faults, pms_fault_parts, pms_notifications,
#            pms_audit_log, ledger_events
#
# Bug fixes applied:
#   - severity sentinel: all UPDATE ops read current severity (never hardcode "medium")
#   - resolve_fault: resolution_notes now persisted in metadata
#   - mark_fault_false_alarm: status set to "false_alarm" (was incorrectly "closed")
#   - link_parts_to_fault: entity_name now uses fault title, not raw UUID
#   - list_faults: filter key is "severity" (was "priority")

from datetime import datetime, timezone
import uuid as uuid_module
import logging
from fastapi import HTTPException
from supabase import Client
from handlers.ledger_utils import build_ledger_event
from middleware.state_machine import validate_state_transition, InvalidStateTransitionError

logger = logging.getLogger(__name__)

_VALID_CLOSE_REASONS = frozenset({
    "fault_resolved",
    "awaiting_parts",
    "machinery_out_of_service",
    "false_alarm",
    "superseded_by_work_order",
    "other",
})

_FOLLOW_UP_CLOSE_REASONS = frozenset({"awaiting_parts", "machinery_out_of_service", "other"})

_FOLLOW_UP_MESSAGES = {
    "awaiting_parts": "Fault closed pending parts delivery — reopen and raise purchase order when parts arrive.",
    "machinery_out_of_service": "Fault closed with machinery OOS — schedule return to service.",
    "other": "Fault closed with reason 'other' — no standard path. Review and document findings.",
}

# Standard column set fetched by all mutating handlers
_FAULT_COLS = "id, status, severity, title, metadata, deleted_at"


# ─── Private helpers ──────────────────────────────────────────────────────────

def _fetch_fault(db_client, fault_id: str, yacht_id: str) -> dict:
    """Fetch fault by id+yacht_id. Raises 404 HTTPException if not found."""
    result = (
        db_client.table("pms_faults")
        .select(_FAULT_COLS)
        .eq("id", fault_id).eq("yacht_id", yacht_id).single().execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Fault not found")
    return result.data


def _write_ledger(db_client, **kwargs) -> None:
    """Write one ledger event. Suppresses 204 no-content false-positives from Supabase SDK."""
    try:
        db_client.table("ledger_events").insert(build_ledger_event(**kwargs)).execute()
    except Exception as e:
        if "204" not in str(e):
            logger.warning(f"[Ledger] {kwargs.get('action', 'unknown')}: {e}")


def _notify_hods(
    db_client, yacht_id: str, actor_user_id: str,
    notification_type: str, title: str, body: str,
    entity_id: str, priority: str = "normal",
) -> None:
    try:
        hod_rows = (
            db_client.table("auth_users_roles")
            .select("user_id")
            .eq("yacht_id", yacht_id)
            .in_("role", ["chief_engineer", "chief_officer", "captain"])
            .eq("is_active", True)
            .execute()
        )
        notifs = []
        for row in (hod_rows.data or []):
            hod_uid = row["user_id"]
            if hod_uid == actor_user_id:
                continue
            notifs.append({
                "id": str(uuid_module.uuid4()),
                "yacht_id": yacht_id,
                "user_id": hod_uid,
                "notification_type": notification_type,
                "title": title,
                "body": body,
                "priority": priority,
                "entity_type": "fault",
                "entity_id": entity_id,
                "triggered_by": actor_user_id,
                "idempotency_key": f"{notification_type}:{entity_id}:{hod_uid}",
                "is_read": False,
                "created_at": datetime.now(timezone.utc).isoformat(),
            })
        if notifs:
            db_client.table("pms_notifications").upsert(
                notifs, on_conflict="yacht_id,user_id,idempotency_key"
            ).execute()
    except Exception as e:
        logger.warning(f"[Notify] {notification_type} HOD broadcast failed: {e}")


def _notify_user(
    db_client, yacht_id: str, target_user_id: str, actor_user_id: str,
    notification_type: str, title: str, body: str,
    entity_id: str, priority: str = "normal",
) -> None:
    if not target_user_id or target_user_id == actor_user_id:
        return
    try:
        db_client.table("pms_notifications").upsert({
            "id": str(uuid_module.uuid4()),
            "yacht_id": yacht_id,
            "user_id": target_user_id,
            "notification_type": notification_type,
            "title": title,
            "body": body,
            "priority": priority,
            "entity_type": "fault",
            "entity_id": entity_id,
            "triggered_by": actor_user_id,
            "idempotency_key": f"{notification_type}:{entity_id}:{target_user_id}",
            "is_read": False,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }, on_conflict="yacht_id,user_id,idempotency_key").execute()
    except Exception as e:
        logger.warning(f"[Notify] {notification_type} to {target_user_id} failed: {e}")


def _ledger_follow_up(
    db_client, yacht_id: str, user_id: str, user_role: str,
    fault_id: str, entity_name: str, action: str, close_reason: str,
) -> None:
    _write_ledger(
        db_client,
        yacht_id=yacht_id, user_id=user_id,
        event_type="follow_up_required", entity_type="fault", entity_id=fault_id,
        action=action, user_role=user_role,
        change_summary=_FOLLOW_UP_MESSAGES.get(close_reason, f"Follow up required ({close_reason})."),
        entity_name=entity_name,
        metadata={"close_reason": close_reason},
    )


# ─── Action handlers ──────────────────────────────────────────────────────────

async def report_fault(
    payload: dict, context: dict,
    yacht_id: str, user_id: str, user_context: dict, db_client: Client,
) -> dict:
    description = payload.get("description", "")
    severity = payload.get("severity", "medium")
    if severity not in ("low", "medium", "high", "critical"):
        severity = "medium"
    fault_title = payload.get("title", description[:100] if description else "Reported fault")

    result = db_client.table("pms_faults").insert({
        "yacht_id": yacht_id,
        "equipment_id": payload.get("equipment_id") or None,
        "fault_code": payload.get("fault_code", "MANUAL"),
        "title": fault_title,
        "description": description,
        "severity": severity,
        "status": "open",
        "detected_at": datetime.now(timezone.utc).isoformat(),
        "metadata": {"reported_by": user_id},
    }).execute()
    if not result.data:
        return {"status": "error", "error_code": "INSERT_FAILED", "message": "Failed to create fault record"}

    fault_id = result.data[0]["id"]
    try:
        db_client.table("pms_audit_log").insert({
            "id": str(uuid_module.uuid4()), "yacht_id": yacht_id,
            "action": "report_fault", "entity_type": "fault", "entity_id": fault_id,
            "user_id": user_id,
            "old_values": None,
            "new_values": {"title": fault_title, "status": "open", "severity": severity},
            "signature": {},
        }).execute()
    except Exception as e:
        logger.warning(f"[Audit] report_fault: {e}")
    _write_ledger(
        db_client,
        yacht_id=yacht_id, user_id=user_id,
        event_type="create", entity_type="fault", entity_id=fault_id,
        action="report_fault", user_role=user_context.get("role"),
        change_summary=f"Fault reported: {fault_title}",
        entity_name=fault_title,
        new_state={"title": fault_title, "status": "open", "severity": severity},
    )
    _notify_hods(
        db_client, yacht_id, user_id,
        notification_type="fault_reported",
        title=f"New fault: {fault_title}",
        body=f"Severity: {severity}. Acknowledgement required.",
        entity_id=fault_id,
        priority="high" if severity in ("critical", "high") else "normal",
    )
    return {"status": "success", "fault_id": fault_id, "message": "Fault reported successfully"}


async def acknowledge_fault(
    payload: dict, context: dict,
    yacht_id: str, user_id: str, user_context: dict, db_client: Client,
) -> dict:
    fault_id = payload.get("fault_id")
    if not fault_id:
        raise HTTPException(status_code=400, detail="fault_id is required")

    fault = _fetch_fault(db_client, fault_id, yacht_id)
    old_status = fault.get("status", "unknown")
    current_severity = fault.get("severity") or "medium"
    entity_name = fault.get("title") or ""

    result = (
        db_client.table("pms_faults")
        .update({
            "status": "investigating",
            "severity": current_severity,
            "updated_by": user_id,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        })
        .eq("id", fault_id).eq("yacht_id", yacht_id).execute()
    )
    if not result.data:
        return {"status": "error", "error_code": "UPDATE_FAILED", "message": "Failed to acknowledge fault"}

    try:
        db_client.table("pms_audit_log").insert({
            "id": str(uuid_module.uuid4()), "yacht_id": yacht_id,
            "action": "acknowledge_fault", "entity_type": "fault", "entity_id": fault_id,
            "user_id": user_id,
            "old_values": {"status": old_status},
            "new_values": {"status": "investigating"},
            "signature": {},
        }).execute()
    except Exception as e:
        logger.warning(f"[Audit] acknowledge_fault: {e}")

    _write_ledger(
        db_client,
        yacht_id=yacht_id, user_id=user_id,
        event_type="status_change", entity_type="fault", entity_id=fault_id,
        action="acknowledge_fault", user_role=user_context.get("role"),
        change_summary=f"Fault acknowledged — status: {old_status} → investigating",
        entity_name=entity_name,
        previous_state={"status": old_status},
        new_state={"status": "investigating"},
    )
    reported_by = (fault.get("metadata") or {}).get("reported_by")
    _notify_user(
        db_client, yacht_id, reported_by, user_id,
        notification_type="fault_acknowledged",
        title=f"Fault acknowledged: {entity_name}",
        body="Your fault report has been acknowledged and is under investigation.",
        entity_id=fault_id,
    )
    return {"status": "success", "message": "Fault acknowledged", "fault_id": fault_id, "new_status": "investigating"}


async def resolve_fault(
    payload: dict, context: dict,
    yacht_id: str, user_id: str, user_context: dict, db_client: Client,
) -> dict:
    fault_id = payload.get("fault_id")
    if not fault_id:
        raise HTTPException(status_code=400, detail="fault_id is required")

    fault = _fetch_fault(db_client, fault_id, yacht_id)
    prev_status = fault.get("status", "unknown")
    current_severity = fault.get("severity") or "medium"
    entity_name = fault.get("title") or ""
    resolution_notes = payload.get("resolution_notes") or payload.get("note") or ""

    # Persist resolution_notes in metadata so entity_routes can surface it
    metadata = fault.get("metadata") or {}
    if resolution_notes:
        metadata["resolution_notes"] = resolution_notes

    now = datetime.now(timezone.utc).isoformat()
    result = (
        db_client.table("pms_faults")
        .update({
            "status": "resolved",
            "severity": current_severity,
            "resolved_by": user_id,
            "resolved_at": now,
            "updated_by": user_id,
            "updated_at": now,
            "metadata": metadata,
        })
        .eq("id", fault_id).eq("yacht_id", yacht_id).execute()
    )
    if not result.data:
        return {"status": "error", "error_code": "UPDATE_FAILED", "message": "Failed to resolve fault"}

    new_state = {"status": "resolved", "resolved_by": user_id}
    if resolution_notes:
        new_state["resolution_notes"] = resolution_notes
    try:
        db_client.table("pms_audit_log").insert({
            "id": str(uuid_module.uuid4()), "yacht_id": yacht_id,
            "action": "resolve_fault", "entity_type": "fault", "entity_id": fault_id,
            "user_id": user_id,
            "old_values": {"status": prev_status},
            "new_values": new_state,
            "signature": {},
        }).execute()
    except Exception as e:
        logger.warning(f"[Audit] resolve_fault: {e}")
    _write_ledger(
        db_client,
        yacht_id=yacht_id, user_id=user_id,
        event_type="status_change", entity_type="fault", entity_id=fault_id,
        action="resolve_fault", user_role=user_context.get("role"),
        change_summary=f"Fault resolved — status: {prev_status} → resolved",
        entity_name=entity_name,
        previous_state={"status": prev_status},
        new_state=new_state,
    )
    return {"status": "success", "message": "Fault resolved", "_ledger_written": True}


async def diagnose_fault(
    payload: dict, context: dict,
    yacht_id: str, user_id: str, user_context: dict, db_client: Client,
) -> dict:
    fault_id = payload.get("fault_id")
    if not fault_id:
        raise HTTPException(status_code=400, detail="fault_id is required")

    fault = _fetch_fault(db_client, fault_id, yacht_id)
    entity_name = fault.get("title") or ""
    current_severity = fault.get("severity") or "medium"
    metadata = fault.get("metadata") or {}
    metadata.update({
        "diagnosis": payload.get("diagnosis", ""),
        "diagnosed_by": user_id,
        "diagnosed_at": datetime.now(timezone.utc).isoformat(),
    })

    result = (
        db_client.table("pms_faults")
        .update({
            "metadata": metadata,
            "severity": current_severity,
            "updated_by": user_id,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        })
        .eq("id", fault_id).eq("yacht_id", yacht_id).execute()
    )
    if not result.data:
        return {"status": "error", "error_code": "UPDATE_FAILED", "message": "Failed to add diagnosis"}

    try:
        db_client.table("pms_audit_log").insert({
            "id": str(uuid_module.uuid4()), "yacht_id": yacht_id,
            "action": "diagnose_fault", "entity_type": "fault", "entity_id": fault_id,
            "user_id": user_id,
            "old_values": None,
            "new_values": {"diagnosis": metadata.get("diagnosis"), "diagnosed_by": user_id},
            "signature": {},
        }).execute()
    except Exception as e:
        logger.warning(f"[Audit] diagnose_fault: {e}")
    _write_ledger(
        db_client,
        yacht_id=yacht_id, user_id=user_id,
        event_type="update", entity_type="fault", entity_id=fault_id,
        action="diagnose_fault", user_role=user_context.get("role"),
        change_summary="Fault diagnosed",
        entity_name=entity_name,
        new_state={"diagnosis": metadata.get("diagnosis"), "diagnosed_by": user_id},
    )
    return {"status": "success", "message": "Diagnosis added"}


async def close_fault(
    payload: dict, context: dict,
    yacht_id: str, user_id: str, user_context: dict, db_client: Client,
) -> dict:
    fault_id = payload.get("fault_id")
    if not fault_id:
        raise HTTPException(status_code=400, detail="fault_id is required")

    close_reason = payload.get("close_reason", "")
    if close_reason and close_reason not in _VALID_CLOSE_REASONS:
        return {
            "status": "error",
            "error_code": "INVALID_CLOSE_REASON",
            "message": f"Invalid close_reason '{close_reason}'. Valid: {', '.join(sorted(_VALID_CLOSE_REASONS))}",
        }

    fault = _fetch_fault(db_client, fault_id, yacht_id)
    current_status = fault.get("status", "open")
    current_severity = fault.get("severity") or "medium"
    entity_name = fault.get("title") or ""
    reported_by = (fault.get("metadata") or {}).get("reported_by")
    updated_meta = {**(fault.get("metadata") or {})}
    if close_reason:
        updated_meta["close_reason"] = close_reason

    try:
        validate_state_transition("fault", current_status, "close_fault")
    except InvalidStateTransitionError as e:
        logger.warning(f"[STATE] {e.message}")
        return {"success": False, "code": e.code, "message": e.message, "current_status": current_status}

    result = (
        db_client.table("pms_faults")
        .update({
            "status": "closed",
            "metadata": updated_meta,
            "severity": current_severity,
            "updated_by": user_id,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        })
        .eq("id", fault_id).eq("yacht_id", yacht_id).execute()
    )
    if not result.data:
        return {"status": "error", "error_code": "UPDATE_FAILED", "message": "Failed to close fault"}

    try:
        db_client.table("pms_audit_log").insert({
            "id": str(uuid_module.uuid4()), "yacht_id": yacht_id,
            "action": "close_fault", "entity_type": "fault", "entity_id": fault_id,
            "user_id": user_id,
            "old_values": {"status": current_status},
            "new_values": {"status": "closed", "close_reason": close_reason},
            "signature": {},
        }).execute()
    except Exception as e:
        logger.warning(f"[Audit] close_fault: {e}")
    _write_ledger(
        db_client,
        yacht_id=yacht_id, user_id=user_id,
        event_type="status_change", entity_type="fault", entity_id=fault_id,
        action="close_fault", user_role=user_context.get("role"),
        change_summary=f"Fault closed — {current_status} → closed. Reason: {close_reason or 'not specified'}",
        entity_name=entity_name,
        previous_state={"status": current_status},
        new_state={"status": "closed", "close_reason": close_reason},
    )
    if close_reason in _FOLLOW_UP_CLOSE_REASONS:
        _ledger_follow_up(
            db_client, yacht_id, user_id, user_context.get("role"),
            fault_id, entity_name, "close_fault", close_reason,
        )
    _notify_user(
        db_client, yacht_id, reported_by, user_id,
        notification_type="fault_closed",
        title=f"Fault closed: {entity_name}",
        body=f"Reason: {close_reason or 'not specified'}.",
        entity_id=fault_id,
    )
    if close_reason == "machinery_out_of_service":
        _notify_hods(
            db_client, yacht_id, user_id,
            notification_type="fault_machinery_oos",
            title=f"Machinery out of service: {entity_name}",
            body="Fault closed with machinery OOS. Schedule return to service.",
            entity_id=fault_id,
            priority="high",
        )
    return {"status": "success", "message": "Fault closed"}


async def update_fault(
    payload: dict, context: dict,
    yacht_id: str, user_id: str, user_context: dict, db_client: Client,
) -> dict:
    fault_id = payload.get("fault_id")
    if not fault_id:
        raise HTTPException(status_code=400, detail="fault_id is required")

    fault = _fetch_fault(db_client, fault_id, yacht_id)
    entity_name = fault.get("title") or ""
    current_severity = fault.get("severity") or "medium"

    update_data: dict = {
        "updated_by": user_id,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    if payload.get("title"):
        update_data["title"] = payload["title"]
    if payload.get("description"):
        update_data["description"] = payload["description"]
    new_sev = payload.get("severity")
    update_data["severity"] = new_sev if new_sev in ("low", "medium", "high", "critical") else current_severity

    result = (
        db_client.table("pms_faults")
        .update(update_data).eq("id", fault_id).eq("yacht_id", yacht_id).execute()
    )
    if not result.data:
        return {"status": "error", "error_code": "UPDATE_FAILED", "message": "Failed to update fault"}

    diff_fields = ("title", "description", "severity")
    changes = [
        f"{f}: {fault.get(f)} → {update_data[f]}"
        for f in diff_fields
        if f in update_data and update_data[f] != fault.get(f)
    ]
    try:
        db_client.table("pms_audit_log").insert({
            "id": str(uuid_module.uuid4()), "yacht_id": yacht_id,
            "action": "update_fault", "entity_type": "fault", "entity_id": fault_id,
            "user_id": user_id,
            "old_values": {f: fault.get(f) for f in diff_fields},
            "new_values": {f: update_data.get(f, fault.get(f)) for f in diff_fields},
            "signature": {},
        }).execute()
    except Exception as e:
        logger.warning(f"[Audit] update_fault: {e}")
    _write_ledger(
        db_client,
        yacht_id=yacht_id, user_id=user_id,
        event_type="update", entity_type="fault", entity_id=fault_id,
        action="update_fault", user_role=user_context.get("role"),
        change_summary="Fault updated" + (" — " + ", ".join(changes) if changes else ""),
        entity_name=entity_name,
        previous_state={f: fault.get(f) for f in diff_fields},
        new_state={f: update_data.get(f, fault.get(f)) for f in diff_fields},
    )
    return {"status": "success", "message": "Fault updated"}


async def reopen_fault(
    payload: dict, context: dict,
    yacht_id: str, user_id: str, user_context: dict, db_client: Client,
) -> dict:
    fault_id = payload.get("fault_id")
    if not fault_id:
        raise HTTPException(status_code=400, detail="fault_id is required")

    fault = _fetch_fault(db_client, fault_id, yacht_id)
    current_status = fault.get("status", "open")
    current_severity = fault.get("severity") or "medium"
    entity_name = fault.get("title") or ""

    try:
        validate_state_transition("fault", current_status, "reopen_fault")
    except InvalidStateTransitionError as e:
        logger.warning(f"[STATE] {e.message}")
        return {"success": False, "code": e.code, "message": e.message, "current_status": current_status}

    result = (
        db_client.table("pms_faults")
        .update({
            "status": "open",
            "severity": current_severity,
            "resolved_at": None,
            "resolved_by": None,
            "updated_by": user_id,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        })
        .eq("id", fault_id).eq("yacht_id", yacht_id).execute()
    )
    if not result.data:
        return {"status": "error", "error_code": "UPDATE_FAILED", "message": "Failed to reopen fault"}

    try:
        db_client.table("pms_audit_log").insert({
            "id": str(uuid_module.uuid4()), "yacht_id": yacht_id,
            "action": "reopen_fault", "entity_type": "fault", "entity_id": fault_id,
            "user_id": user_id,
            "old_values": {"status": current_status},
            "new_values": {"status": "open"},
            "signature": {},
        }).execute()
    except Exception as e:
        logger.warning(f"[Audit] reopen_fault: {e}")
    _write_ledger(
        db_client,
        yacht_id=yacht_id, user_id=user_id,
        event_type="status_change", entity_type="fault", entity_id=fault_id,
        action="reopen_fault", user_role=user_context.get("role"),
        change_summary=f"Fault reopened — status: {current_status} → open",
        entity_name=entity_name,
        previous_state={"status": current_status},
        new_state={"status": "open"},
    )
    return {"status": "success", "message": "Fault reopened"}


async def mark_fault_false_alarm(
    payload: dict, context: dict,
    yacht_id: str, user_id: str, user_context: dict, db_client: Client,
) -> dict:
    fault_id = payload.get("fault_id")
    if not fault_id:
        raise HTTPException(status_code=400, detail="fault_id is required")

    fault = _fetch_fault(db_client, fault_id, yacht_id)
    entity_name = fault.get("title") or ""
    prev_status = fault.get("status", "open")
    current_severity = fault.get("severity") or "medium"
    metadata = fault.get("metadata") or {}
    metadata.update({
        "false_alarm": True,
        "false_alarm_by": user_id,
        "false_alarm_at": datetime.now(timezone.utc).isoformat(),
    })

    result = (
        db_client.table("pms_faults")
        .update({
            "status": "false_alarm",  # Terminal state per state machine — not "closed"
            "metadata": metadata,
            "severity": current_severity,
            "updated_by": user_id,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        })
        .eq("id", fault_id).eq("yacht_id", yacht_id).execute()
    )
    if not result.data:
        return {"status": "error", "error_code": "UPDATE_FAILED", "message": "Failed to mark as false alarm"}

    try:
        db_client.table("pms_audit_log").insert({
            "id": str(uuid_module.uuid4()), "yacht_id": yacht_id,
            "action": "mark_fault_false_alarm", "entity_type": "fault", "entity_id": fault_id,
            "user_id": user_id,
            "old_values": {"status": prev_status},
            "new_values": {"status": "false_alarm", "false_alarm": True},
            "signature": {},
        }).execute()
    except Exception as e:
        logger.warning(f"[Audit] mark_fault_false_alarm: {e}")
    _write_ledger(
        db_client,
        yacht_id=yacht_id, user_id=user_id,
        event_type="status_change", entity_type="fault", entity_id=fault_id,
        action="mark_fault_false_alarm", user_role=user_context.get("role"),
        change_summary=f"Fault marked as false alarm — {prev_status} → false_alarm",
        entity_name=entity_name,
        previous_state={"status": prev_status},
        new_state={"status": "false_alarm", "false_alarm": True},
    )
    return {"status": "success", "message": "Fault marked as false alarm"}


async def add_fault_photo(
    payload: dict, context: dict,
    yacht_id: str, user_id: str, user_context: dict, db_client: Client,
) -> dict:
    fault_id = payload.get("fault_id")
    if not fault_id:
        raise HTTPException(status_code=400, detail="fault_id is required")
    photo_url = payload.get("photo_url")
    if not photo_url:
        raise HTTPException(status_code=400, detail="photo_url is required")

    fault = _fetch_fault(db_client, fault_id, yacht_id)
    current_severity = fault.get("severity") or "medium"
    metadata = fault.get("metadata") or {}
    photos = metadata.get("photos", [])
    photos.append({"url": photo_url, "added_by": user_id, "added_at": datetime.now(timezone.utc).isoformat()})
    metadata["photos"] = photos

    result = (
        db_client.table("pms_faults")
        .update({
            "metadata": metadata,
            "severity": current_severity,
            "updated_by": user_id,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        })
        .eq("id", fault_id).eq("yacht_id", yacht_id).execute()
    )
    if not result.data:
        return {"status": "error", "error_code": "UPDATE_FAILED", "message": "Failed to add photo"}
    try:
        db_client.table("pms_audit_log").insert({
            "id": str(uuid_module.uuid4()), "yacht_id": yacht_id,
            "action": "add_fault_photo", "entity_type": "fault", "entity_id": fault_id,
            "user_id": user_id,
            "old_values": None,
            "new_values": {"photo_url": photo_url, "photos_count": len(photos)},
            "signature": {},
        }).execute()
    except Exception as e:
        logger.warning(f"[Audit] add_fault_photo: {e}")
    return {"status": "success", "message": "Photo added to fault"}


async def view_fault_detail(
    payload: dict, context: dict,
    yacht_id: str, user_id: str, user_context: dict, db_client: Client,
) -> dict:
    fault_id = payload.get("fault_id")
    if not fault_id:
        raise HTTPException(status_code=400, detail="fault_id is required")
    result = (
        db_client.table("pms_faults")
        .select("*, pms_equipment(*)")
        .eq("id", fault_id).eq("yacht_id", yacht_id).single().execute()
    )
    if result.data:
        return {"status": "success", "fault": result.data}
    return {"status": "error", "error_code": "NOT_FOUND", "message": "Fault not found"}


async def view_fault_history(
    payload: dict, context: dict,
    yacht_id: str, user_id: str, user_context: dict, db_client: Client,
) -> dict:
    equipment_id = payload.get("equipment_id")
    if not equipment_id:
        raise HTTPException(status_code=400, detail="equipment_id is required")
    faults = (
        db_client.table("pms_faults")
        .select("id, title, description, status, severity, detected_at, resolved_at, created_at")
        .eq("equipment_id", equipment_id).eq("yacht_id", yacht_id)
        .order("created_at", desc=True).limit(50).execute()
    )
    return {"status": "success", "success": True, "faults": faults.data or [], "count": len(faults.data or [])}


async def add_fault_note(
    payload: dict, context: dict,
    yacht_id: str, user_id: str, user_context: dict, db_client: Client,
) -> dict:
    fault_id = payload.get("fault_id")
    note_text = payload.get("note_text", "")
    if not fault_id:
        raise HTTPException(status_code=400, detail="fault_id is required")
    if not note_text:
        raise HTTPException(status_code=400, detail="note_text is required")

    fault = _fetch_fault(db_client, fault_id, yacht_id)
    entity_name = fault.get("title") or ""
    current_severity = fault.get("severity") or "medium"
    metadata = fault.get("metadata") or {}
    notes = metadata.get("notes", []) or []
    notes.append({"text": note_text, "added_by": user_id, "added_at": datetime.now(timezone.utc).isoformat()})
    metadata["notes"] = notes

    result = (
        db_client.table("pms_faults")
        .update({
            "metadata": metadata,
            "severity": current_severity,
            "updated_by": user_id,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        })
        .eq("id", fault_id).eq("yacht_id", yacht_id).execute()
    )
    if not result.data:
        return {"status": "error", "error_code": "UPDATE_FAILED", "message": "Failed to add fault note"}

    try:
        db_client.table("pms_audit_log").insert({
            "id": str(uuid_module.uuid4()), "yacht_id": yacht_id,
            "action": "add_fault_note", "entity_type": "fault", "entity_id": fault_id,
            "user_id": user_id,
            "old_values": None,
            "new_values": {"note_text": note_text, "added_by": user_id},
            "signature": {},
        }).execute()
    except Exception as e:
        logger.warning(f"[Audit] add_fault_note: {e}")
    _write_ledger(
        db_client,
        yacht_id=yacht_id, user_id=user_id,
        event_type="update", entity_type="fault", entity_id=fault_id,
        action="add_fault_note", user_role=user_context.get("role"),
        change_summary="Note added to fault",
        entity_name=entity_name,
        new_state={"note_text": note_text, "added_by": user_id},
    )
    return {"status": "success", "success": True, "message": "Note added to fault", "notes_count": len(notes)}


async def list_faults(
    payload: dict, context: dict,
    yacht_id: str, user_id: str, user_context: dict, db_client: Client,
) -> dict:
    query = db_client.table("pms_faults").select("*").eq("yacht_id", yacht_id)
    if payload.get("status"):
        query = query.eq("status", payload["status"])
    # Accept both "severity" (canonical) and "priority" (legacy alias)
    severity_filter = payload.get("severity") or payload.get("priority")
    if severity_filter:
        query = query.eq("severity", severity_filter)
    limit = payload.get("limit", 50)
    result = query.order("detected_at", desc=True).limit(limit).execute()
    return {"status": "success", "success": True, "faults": result.data or [], "total": len(result.data or [])}


async def archive_fault(
    payload: dict, context: dict,
    yacht_id: str, user_id: str, user_context: dict, db_client: Client,
) -> dict:
    fault_id = payload.get("fault_id") or payload.get("entity_id")
    reason = payload.get("reason", "")
    if not fault_id:
        raise HTTPException(status_code=400, detail="fault_id is required")

    fault = _fetch_fault(db_client, fault_id, yacht_id)
    if fault.get("deleted_at"):
        return {"status": "error", "error_code": "ALREADY_ARCHIVED", "message": "Fault is already archived"}

    entity_name = fault.get("title") or ""
    current_severity = fault.get("severity") or "medium"
    now = datetime.now(timezone.utc).isoformat()

    result = (
        db_client.table("pms_faults")
        .update({
            "deleted_at": now,
            "deleted_by": user_id,
            "deletion_reason": reason,
            "severity": current_severity,
            "updated_by": user_id,
            "updated_at": now,
        })
        .eq("id", fault_id).eq("yacht_id", yacht_id).execute()
    )
    if not result.data:
        return {"status": "error", "error_code": "UPDATE_FAILED", "message": "Failed to archive fault"}

    try:
        db_client.table("pms_audit_log").insert({
            "id": str(uuid_module.uuid4()), "yacht_id": yacht_id,
            "action": "archive_fault", "entity_type": "fault", "entity_id": fault_id,
            "user_id": user_id,
            "old_values": {"deleted_at": None},
            "new_values": {"deleted_at": now, "deletion_reason": reason},
            "signature": {},
        }).execute()
    except Exception as e:
        logger.warning(f"[Audit] archive_fault: {e}")
    _write_ledger(
        db_client,
        yacht_id=yacht_id, user_id=user_id,
        event_type="archive", entity_type="fault", entity_id=fault_id,
        action="archive_fault", user_role=user_context.get("role"),
        change_summary=f"Fault archived — reason: {reason or 'not specified'}",
        entity_name=entity_name,
        new_state={"deleted_at": now, "deletion_reason": reason},
    )
    _notify_hods(
        db_client, yacht_id, user_id,
        notification_type="fault_archived",
        title=f"Fault archived: {entity_name}",
        body=f"Reason: {reason or 'not specified'}. Review if action is still required.",
        entity_id=fault_id,
    )
    return {"status": "success", "fault_id": fault_id, "message": "Fault archived"}


async def link_parts_to_fault(
    payload: dict, context: dict,
    yacht_id: str, user_id: str, user_context: dict, db_client: Client,
) -> dict:
    fault_id = payload.get("fault_id")
    part_ids = payload.get("part_ids", [])
    notes = payload.get("notes", "")
    if not fault_id:
        raise HTTPException(status_code=400, detail="fault_id is required")
    if not part_ids:
        raise HTTPException(status_code=400, detail="part_ids is required and must be non-empty")

    fault = _fetch_fault(db_client, fault_id, yacht_id)
    entity_name = fault.get("title") or fault_id

    inserted = skipped = 0
    for part_id in part_ids:
        try:
            r = (
                db_client.table("pms_fault_parts")
                .upsert(
                    {"fault_id": fault_id, "part_id": part_id, "linked_by": user_id, "notes": notes},
                    on_conflict="fault_id,part_id", ignore_duplicates=True,
                ).execute()
            )
            inserted += 1 if r.data else 0
            skipped += 0 if r.data else 1
        except Exception as e:
            logger.warning(f"[link_parts_to_fault] part {part_id}: {e}")
            skipped += 1

    try:
        db_client.table("pms_audit_log").insert({
            "id": str(uuid_module.uuid4()), "yacht_id": yacht_id,
            "action": "link_parts_to_fault", "entity_type": "fault", "entity_id": fault_id,
            "user_id": user_id,
            "old_values": None,
            "new_values": {"part_ids": part_ids, "inserted": inserted, "skipped": skipped},
            "signature": {},
        }).execute()
    except Exception as e:
        logger.warning(f"[Audit] link_parts_to_fault: {e}")
    _write_ledger(
        db_client,
        yacht_id=yacht_id, user_id=user_id,
        event_type="update", entity_type="fault", entity_id=fault_id,
        action="link_parts_to_fault", user_role=user_context.get("role"),
        change_summary=f"Parts linked — {inserted} inserted, {skipped} skipped",
        entity_name=entity_name,
        new_state={"part_ids": part_ids, "inserted": inserted},
    )
    return {"status": "success", "inserted": inserted, "skipped": skipped}


async def unlink_part_from_fault(
    payload: dict, context: dict,
    yacht_id: str, user_id: str, user_context: dict, db_client: Client,
) -> dict:
    fault_id = payload.get("fault_id")
    part_id = payload.get("part_id")
    if not fault_id:
        raise HTTPException(status_code=400, detail="fault_id is required")
    if not part_id:
        raise HTTPException(status_code=400, detail="part_id is required")

    fault = _fetch_fault(db_client, fault_id, yacht_id)
    entity_name = fault.get("title") or fault_id

    db_client.table("pms_fault_parts").delete().eq("fault_id", fault_id).eq("part_id", part_id).execute()

    try:
        db_client.table("pms_audit_log").insert({
            "id": str(uuid_module.uuid4()), "yacht_id": yacht_id,
            "action": "unlink_part_from_fault", "entity_type": "fault", "entity_id": fault_id,
            "user_id": user_id,
            "old_values": {"part_id": part_id},
            "new_values": {"unlinked_part_id": part_id},
            "signature": {},
        }).execute()
    except Exception as e:
        logger.warning(f"[Audit] unlink_part_from_fault: {e}")
    _write_ledger(
        db_client,
        yacht_id=yacht_id, user_id=user_id,
        event_type="update", entity_type="fault", entity_id=fault_id,
        action="unlink_part_from_fault", user_role=user_context.get("role"),
        change_summary=f"Part unlinked from fault — part_id: {part_id}",
        entity_name=entity_name,
        new_state={"unlinked_part_id": part_id},
    )
    return {"status": "success", "message": "Part unlinked from fault"}


HANDLERS: dict = {
    "report_fault":           report_fault,
    "acknowledge_fault":      acknowledge_fault,
    "resolve_fault":          resolve_fault,
    "diagnose_fault":         diagnose_fault,
    "investigate_fault":      diagnose_fault,   # legacy alias
    "close_fault":            close_fault,
    "update_fault":           update_fault,
    "reopen_fault":           reopen_fault,
    "mark_fault_false_alarm": mark_fault_false_alarm,
    "add_fault_photo":        add_fault_photo,
    "view_fault_detail":      view_fault_detail,
    "view_fault_history":     view_fault_history,
    "add_fault_note":         add_fault_note,
    "list_faults":            list_faults,
    "archive_fault":          archive_fault,
    "delete_fault":           archive_fault,    # soft-delete alias
    "link_parts_to_fault":    link_parts_to_fault,
    "unlink_part_from_fault": unlink_part_from_fault,
}
