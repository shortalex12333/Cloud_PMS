"""
handlers/media_phase4.py — Multi-domain media / utility actions.

Actions here operate across entity types (fault, work_order, equipment, handover)
and do not belong to any single domain.

Covers:
  view_checklist     — named checklist template system (pms_checklists / pms_checklist_items)
  view_smart_summary — AI/metadata summary reader (any entity)
  upload_photo       — generic photo attachment (any entity)
  record_voice_note  — generic voice note attachment (any entity)
  show_manual_section — equipment manual lookup (delegates to ManualHandlers)
"""
from datetime import datetime, timezone
import uuid as uuid_module
import logging
from fastapi import HTTPException
from supabase import Client
from routes.handlers.ledger_utils import build_ledger_event

logger = logging.getLogger(__name__)


async def view_checklist(
    payload: dict,
    context: dict,
    yacht_id: str,
    user_id: str,
    user_context: dict,
    db_client: Client,
) -> dict:
    checklist_id = payload.get("checklist_id")
    if not checklist_id:
        raise HTTPException(status_code=400, detail="checklist_id is required")

    checklist = db_client.table("pms_checklists").select(
        "id, name, description, checklist_type, status, total_items, completed_items, created_at"
    ).eq("id", checklist_id).eq("yacht_id", yacht_id).maybe_single().execute()

    if not checklist.data:
        raise HTTPException(status_code=404, detail="Checklist not found")

    items = db_client.table("pms_checklist_items").select(
        "id, description, instructions, sequence, is_completed, completed_at, completed_by, "
        "is_required, requires_photo, requires_signature, recorded_value, photo_url, status"
    ).eq("checklist_id", checklist_id).eq("yacht_id", yacht_id).order("sequence").execute()

    return {
        "status": "success",
        "success": True,
        "checklist": checklist.data,
        "items": items.data or [],
        "progress": {
            "total": checklist.data.get("total_items", 0),
            "completed": checklist.data.get("completed_items", 0),
        },
    }


async def view_smart_summary(
    payload: dict,
    context: dict,
    yacht_id: str,
    user_id: str,
    user_context: dict,
    db_client: Client,
) -> dict:
    entity_type = payload.get("entity_type")
    entity_id = payload.get("entity_id")

    if not entity_type:
        raise HTTPException(status_code=400, detail="entity_type is required")
    if not entity_id:
        raise HTTPException(status_code=400, detail="entity_id is required")

    table_map = {
        "fault": "pms_faults",
        "work_order": "pms_work_orders",
        "equipment": "pms_equipment",
        "handover": "handovers",
    }

    summary = None
    if entity_type in table_map:
        try:
            entity = db_client.table(table_map[entity_type]).select(
                "id, metadata"
            ).eq("id", entity_id).eq("yacht_id", yacht_id).maybe_single().execute()
            if entity.data:
                metadata = entity.data.get("metadata", {}) or {}
                summary = metadata.get("smart_summary") or metadata.get("ai_summary")
        except Exception:
            pass

    return {
        "status": "success",
        "success": True,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "smart_summary": summary or "No smart summary available yet",
        "has_summary": summary is not None,
    }


async def upload_photo(
    payload: dict,
    context: dict,
    yacht_id: str,
    user_id: str,
    user_context: dict,
    db_client: Client,
) -> dict:
    entity_type = payload.get("entity_type")
    entity_id = payload.get("entity_id")
    photo_url = payload.get("photo_url")
    description = payload.get("description", "")

    if not entity_type:
        raise HTTPException(status_code=400, detail="entity_type is required")
    if not entity_id:
        raise HTTPException(status_code=400, detail="entity_id is required")
    if not photo_url:
        raise HTTPException(status_code=400, detail="photo_url is required")

    table_map = {
        "fault": "pms_faults",
        "work_order": "pms_work_orders",
        "equipment": "pms_equipment",
        "checklist_item": "pms_checklist_items",
    }

    if entity_type not in table_map:
        raise HTTPException(status_code=400, detail=f"Unsupported entity_type: {entity_type}")

    table_name = table_map[entity_type]
    entity = db_client.table(table_name).select("id, metadata").eq(
        "id", entity_id
    ).eq("yacht_id", yacht_id).maybe_single().execute()

    if not entity.data:
        raise HTTPException(status_code=404, detail=f"{entity_type} not found")

    metadata = entity.data.get("metadata", {}) or {}
    photos = metadata.get("photos", []) or []
    photos.append({
        "url": photo_url,
        "description": description,
        "uploaded_by": user_id,
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
    })
    metadata["photos"] = photos

    db_client.table(table_name).update({"metadata": metadata}).eq("id", entity_id).eq("yacht_id", yacht_id).execute()

    return {
        "status": "success",
        "success": True,
        "message": "Photo uploaded successfully",
        "entity_type": entity_type,
        "entity_id": entity_id,
        "photo_url": photo_url,
        "photos_count": len(photos),
    }


async def record_voice_note(
    payload: dict,
    context: dict,
    yacht_id: str,
    user_id: str,
    user_context: dict,
    db_client: Client,
) -> dict:
    entity_type = payload.get("entity_type")
    entity_id = payload.get("entity_id")
    audio_url = payload.get("audio_url", "")
    transcript = payload.get("transcript", "")
    duration_seconds = payload.get("duration_seconds", 0)

    if not entity_type:
        raise HTTPException(status_code=400, detail="entity_type is required")
    if not entity_id:
        raise HTTPException(status_code=400, detail="entity_id is required")

    table_map = {
        "fault": "pms_faults",
        "work_order": "pms_work_orders",
        "equipment": "pms_equipment",
        "handover": "handovers",
    }

    if entity_type not in table_map:
        raise HTTPException(status_code=400, detail=f"Unsupported entity_type: {entity_type}")

    table_name = table_map[entity_type]
    entity = db_client.table(table_name).select("id, metadata").eq(
        "id", entity_id
    ).eq("yacht_id", yacht_id).maybe_single().execute()

    if not entity.data:
        raise HTTPException(status_code=404, detail=f"{entity_type} not found")

    metadata = entity.data.get("metadata", {}) or {}
    voice_notes = metadata.get("voice_notes", []) or []
    voice_notes.append({
        "id": str(uuid_module.uuid4()),
        "audio_url": audio_url,
        "transcript": transcript,
        "duration_seconds": duration_seconds,
        "recorded_by": user_id,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
    })
    metadata["voice_notes"] = voice_notes

    db_client.table(table_name).update({"metadata": metadata}).eq("id", entity_id).eq("yacht_id", yacht_id).execute()

    return {
        "status": "success",
        "success": True,
        "message": "Voice note recorded",
        "entity_type": entity_type,
        "entity_id": entity_id,
        "voice_notes_count": len(voice_notes),
    }


async def show_manual_section(
    payload: dict,
    context: dict,
    yacht_id: str,
    user_id: str,
    user_context: dict,
    db_client: Client,
) -> dict:
    if not payload.get("equipment_id"):
        raise HTTPException(status_code=400, detail="equipment_id is required")

    from handlers.manual_handlers import ManualHandlers
    manual = ManualHandlers(db_client)
    return await manual.show_manual_section_execute(
        equipment_id=payload["equipment_id"],
        yacht_id=yacht_id,
        user_id=user_id,
        fault_code=payload.get("fault_code"),
        section_id=payload.get("section_id"),
    )


HANDLERS: dict = {
    "view_checklist": view_checklist,
    "view_smart_summary": view_smart_summary,
    "upload_photo": upload_photo,
    "record_voice_note": record_voice_note,
    "show_manual_section": show_manual_section,
}
