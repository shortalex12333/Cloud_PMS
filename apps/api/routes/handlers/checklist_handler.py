# routes/handlers/checklist_handler.py
#
# Phase 5 Task 5 — 9 checklist / media actions migrated from p0_actions_routes.py.
# Handlers: view_checklist, mark_checklist_item_complete, add_checklist_note,
#           add_checklist_item, add_checklist_photo, view_smart_summary,
#           upload_photo, record_voice_note, show_manual_section

from datetime import datetime, timezone
import uuid as uuid_module
import logging
from fastapi import HTTPException
from supabase import Client
from routes.handlers.ledger_utils import build_ledger_event

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# view_checklist
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# mark_checklist_item_complete
# ---------------------------------------------------------------------------

async def mark_checklist_item_complete(
    payload: dict,
    context: dict,
    yacht_id: str,
    user_id: str,
    user_context: dict,
    db_client: Client,
) -> dict:
    checklist_item_id = payload.get("checklist_item_id")
    completion_notes = payload.get("completion_notes", "")
    recorded_value = payload.get("recorded_value")

    if not checklist_item_id:
        raise HTTPException(status_code=400, detail="checklist_item_id is required")

    try:
        item = db_client.table("pms_checklist_items").select(
            "id, is_completed, requires_photo, requires_signature"
        ).eq("id", checklist_item_id).eq("yacht_id", yacht_id).maybe_single().execute()

        if not item.data:
            raise HTTPException(status_code=404, detail="Checklist item not found")

        update_data = {
            "is_completed": True,
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "completed_by": user_id,
            "status": "completed",
            "updated_by": user_id,
        }

        if completion_notes:
            update_data["completion_notes"] = completion_notes
        if recorded_value is not None:
            update_data["recorded_value"] = str(recorded_value)

        db_client.table("pms_checklist_items").update(update_data).eq(
            "id", checklist_item_id
        ).eq("yacht_id", yacht_id).execute()

        # Record ledger event
        try:
            ledger_event = build_ledger_event(
                yacht_id=yacht_id,
                user_id=user_id,
                event_type="status_change",
                entity_type="checklist_item",
                entity_id=checklist_item_id,
                action="mark_checklist_item_complete",
                user_role=user_context.get("role", "member"),
                change_summary="Checklist item marked as complete",
                metadata={"completion_notes": completion_notes, "domain": "Work Orders"},
            )
            try:
                db_client.table("ledger_events").insert(ledger_event).execute()
                logger.info(f"[Ledger] mark_checklist_item_complete recorded for {checklist_item_id}")
            except Exception as e:
                if "204" in str(e):
                    logger.info("[Ledger] mark_checklist_item_complete recorded (204)")
                else:
                    logger.warning(f"[Ledger] Failed: {e}")
        except Exception as e:
            logger.warning(f"[Ledger] Failed to prepare event: {e}")

        return {
            "status": "success",
            "success": True,
            "message": "Checklist item marked as complete",
            "checklist_item_id": checklist_item_id,
        }
    except HTTPException:
        raise
    except Exception:
        return {
            "status": "success",
            "success": True,
            "message": "Checklist feature not yet configured",
            "checklist_item_id": checklist_item_id,
        }


# ---------------------------------------------------------------------------
# add_checklist_note
# ---------------------------------------------------------------------------

async def add_checklist_note(
    payload: dict,
    context: dict,
    yacht_id: str,
    user_id: str,
    user_context: dict,
    db_client: Client,
) -> dict:
    checklist_item_id = payload.get("checklist_item_id")
    note_text = payload.get("note_text")

    if not checklist_item_id:
        raise HTTPException(status_code=400, detail="checklist_item_id is required")
    if not note_text:
        raise HTTPException(status_code=400, detail="note_text is required")

    try:
        item = db_client.table("pms_checklist_items").select(
            "id, metadata"
        ).eq("id", checklist_item_id).eq("yacht_id", yacht_id).maybe_single().execute()

        if not item.data:
            raise HTTPException(status_code=404, detail="Checklist item not found")

        metadata = item.data.get("metadata", {}) or {}
        notes = metadata.get("notes", []) or []
        notes.append({
            "text": note_text,
            "added_by": user_id,
            "added_at": datetime.now(timezone.utc).isoformat(),
        })
        metadata["notes"] = notes

        db_client.table("pms_checklist_items").update({
            "metadata": metadata,
            "updated_by": user_id,
        }).eq("id", checklist_item_id).eq("yacht_id", yacht_id).execute()

        # Record ledger event
        try:
            ledger_event = build_ledger_event(
                yacht_id=yacht_id,
                user_id=user_id,
                event_type="update",
                entity_type="checklist_item",
                entity_id=checklist_item_id,
                action="add_checklist_note",
                user_role=user_context.get("role", "member"),
                change_summary="Note added to checklist item",
                metadata={
                    "note_preview": note_text[:100] if len(note_text) > 100 else note_text,
                    "domain": "Work Orders",
                },
            )
            try:
                db_client.table("ledger_events").insert(ledger_event).execute()
                logger.info(f"[Ledger] add_checklist_note recorded for {checklist_item_id}")
            except Exception as e:
                if "204" in str(e):
                    logger.info("[Ledger] add_checklist_note recorded (204)")
                else:
                    logger.warning(f"[Ledger] Failed: {e}")
        except Exception as e:
            logger.warning(f"[Ledger] Failed to prepare event: {e}")

        return {
            "status": "success",
            "success": True,
            "message": "Note added to checklist item",
            "checklist_item_id": checklist_item_id,
            "notes_count": len(notes),
        }
    except HTTPException:
        raise
    except Exception:
        return {
            "status": "success",
            "success": True,
            "message": "Checklist feature not yet configured",
            "checklist_item_id": checklist_item_id,
        }


# ---------------------------------------------------------------------------
# add_checklist_item
# ---------------------------------------------------------------------------

async def add_checklist_item(
    payload: dict,
    context: dict,
    yacht_id: str,
    user_id: str,
    user_context: dict,
    db_client: Client,
) -> dict:
    work_order_id = payload.get("work_order_id")
    title = payload.get("title")
    description = payload.get("description")

    if not work_order_id:
        raise HTTPException(status_code=400, detail="work_order_id is required")
    if not title:
        raise HTTPException(status_code=400, detail="title is required")

    try:
        wo = db_client.table("pms_work_orders").select(
            "id, yacht_id, title, number"
        ).eq("id", work_order_id).eq("yacht_id", yacht_id).maybe_single().execute()

        if not wo.data:
            raise HTTPException(status_code=404, detail="Work order not found or access denied")

        existing = db_client.table("pms_work_order_checklist").select(
            "sequence"
        ).eq("work_order_id", work_order_id).order("sequence", desc=True).limit(1).execute()

        next_sequence = (existing.data[0]["sequence"] + 1) if existing.data else 1

        new_item = {
            "id": str(uuid_module.uuid4()),
            "yacht_id": yacht_id,
            "work_order_id": work_order_id,
            "title": title.strip(),
            "description": description.strip() if description else None,
            "sequence": next_sequence,
            "is_completed": False,
            "is_required": True,
            "requires_photo": False,
            "requires_signature": False,
            "created_by": user_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        # Intentional: inserts into pms_work_order_checklist (flat checklist items linked to a WO).
        # view_checklist reads pms_checklist_items (named checklist templates). These are different tables.
        # Handle 204 No Content response from Supabase
        try:
            insert_result = db_client.table("pms_work_order_checklist").insert(new_item).execute()
            result_data = insert_result.data[0] if insert_result.data else new_item
        except Exception as insert_err:
            # postgrest-py throws APIError on 204 responses - treat as success
            if "204" in str(insert_err):
                logger.info(f"Checklist insert succeeded with 204 for {work_order_id}")
                result_data = new_item
            else:
                raise

        # Record ledger event
        try:
            ledger_event = build_ledger_event(
                yacht_id=yacht_id,
                user_id=user_id,
                event_type="create",
                entity_type="checklist_item",
                entity_id=new_item["id"],
                action="add_checklist_item",
                user_role=user_context.get("role", "member"),
                change_summary=f"Checklist item added: {title}",
                metadata={
                    "work_order_id": work_order_id,
                    "checklist_title": title,
                    "domain": "Work Orders",
                },
            )
            try:
                db_client.table("ledger_events").insert(ledger_event).execute()
                logger.info(f"[Ledger] add_checklist_item recorded for {new_item['id']}")
            except Exception as e:
                if "204" in str(e):
                    logger.info("[Ledger] add_checklist_item recorded (204)")
                else:
                    logger.warning(f"[Ledger] Failed: {e}")
        except Exception as e:
            logger.warning(f"[Ledger] Failed to prepare event: {e}")

        return {
            "status": "success",
            "success": True,
            "message": "Checklist item added",
            "data": result_data,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"add_checklist_item failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to add checklist item: {str(e)}")


# ---------------------------------------------------------------------------
# add_checklist_photo
# ---------------------------------------------------------------------------

async def add_checklist_photo(
    payload: dict,
    context: dict,
    yacht_id: str,
    user_id: str,
    user_context: dict,
    db_client: Client,
) -> dict:
    checklist_item_id = payload.get("checklist_item_id")
    photo_url = payload.get("photo_url")

    if not checklist_item_id:
        raise HTTPException(status_code=400, detail="checklist_item_id is required")
    if not photo_url:
        raise HTTPException(status_code=400, detail="photo_url is required")

    try:
        item = db_client.table("pms_checklist_items").select(
            "id, metadata"
        ).eq("id", checklist_item_id).eq("yacht_id", yacht_id).maybe_single().execute()

        if not item.data:
            raise HTTPException(status_code=404, detail="Checklist item not found")

        metadata = item.data.get("metadata", {}) or {}
        photos = metadata.get("photos", []) or []
        photos.append({
            "url": photo_url,
            "added_by": user_id,
            "added_at": datetime.now(timezone.utc).isoformat(),
        })
        metadata["photos"] = photos

        db_client.table("pms_checklist_items").update({
            "photo_url": photo_url,
            "metadata": metadata,
            "updated_by": user_id,
        }).eq("id", checklist_item_id).eq("yacht_id", yacht_id).execute()

        # Record ledger event
        try:
            ledger_event = build_ledger_event(
                yacht_id=yacht_id,
                user_id=user_id,
                event_type="update",
                entity_type="checklist_item",
                entity_id=checklist_item_id,
                action="add_checklist_photo",
                user_role=user_context.get("role", "member"),
                change_summary="Photo added to checklist item",
                metadata={"photo_url": photo_url, "domain": "Work Orders"},
            )
            try:
                db_client.table("ledger_events").insert(ledger_event).execute()
                logger.info(f"[Ledger] add_checklist_photo recorded for {checklist_item_id}")
            except Exception as e:
                if "204" in str(e):
                    logger.info("[Ledger] add_checklist_photo recorded (204)")
                else:
                    logger.warning(f"[Ledger] Failed: {e}")
        except Exception as e:
            logger.warning(f"[Ledger] Failed to prepare event: {e}")

        return {
            "status": "success",
            "success": True,
            "message": "Photo added to checklist item",
            "checklist_item_id": checklist_item_id,
            "photo_url": photo_url,
        }
    except HTTPException:
        raise
    except Exception:
        return {
            "status": "success",
            "success": True,
            "message": "Checklist feature not yet configured",
            "checklist_item_id": checklist_item_id,
            "photo_url": photo_url,
        }


# ---------------------------------------------------------------------------
# view_smart_summary
# ---------------------------------------------------------------------------

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

    entity_data = None
    if entity_type in table_map:
        try:
            entity = db_client.table(table_map[entity_type]).select(
                "id, metadata"
            ).eq("id", entity_id).eq("yacht_id", yacht_id).maybe_single().execute()
            entity_data = entity.data
        except Exception:
            pass

    summary = None
    if entity_data:
        metadata = entity_data.get("metadata", {}) or {}
        summary = metadata.get("smart_summary") or metadata.get("ai_summary")

    return {
        "status": "success",
        "success": True,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "smart_summary": summary or "No smart summary available yet",
        "has_summary": summary is not None,
    }


# ---------------------------------------------------------------------------
# upload_photo
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# record_voice_note
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# show_manual_section
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Dispatch table
# ---------------------------------------------------------------------------

HANDLERS: dict = {
    "view_checklist": view_checklist,
    "mark_checklist_item_complete": mark_checklist_item_complete,
    "add_checklist_note": add_checklist_note,
    "add_checklist_item": add_checklist_item,
    "add_checklist_photo": add_checklist_photo,
    "view_smart_summary": view_smart_summary,
    "upload_photo": upload_photo,
    "record_voice_note": record_voice_note,
    "show_manual_section": show_manual_section,
}
