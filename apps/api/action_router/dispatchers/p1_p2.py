"""P1 compliance, P1 purchasing, and P2 mutation-light action handlers."""

from typing import Dict, Any
import logging
from integrations.supabase import get_supabase_client
from handlers.p1_compliance_handlers import P1ComplianceHandlers
from handlers.p2_mutation_light_handlers import P2MutationLightHandlers
logger = logging.getLogger(__name__)

_p1_compliance_handlers = None
_p2_handlers = None


def _get_p1_compliance():
    global _p1_compliance_handlers
    if _p1_compliance_handlers is None:
        _p1_compliance_handlers = P1ComplianceHandlers(get_supabase_client())
    return _p1_compliance_handlers


def _get_p2():
    global _p2_handlers
    if _p2_handlers is None:
        _p2_handlers = P2MutationLightHandlers(get_supabase_client())
    return _p2_handlers


# ============================================================================
# P1 Compliance
# ============================================================================

async def _log_delivery_received(params: Dict[str, Any]) -> Dict[str, Any]:
    return await _get_p1_compliance().log_delivery_received_execute(
        order_id=params.get("order_id") or params.get("entity_id"),
        yacht_id=params["yacht_id"],
        received_by=params.get("received_by") or params.get("user_id"),
        received_items=params.get("received_items"),
        notes=params.get("notes"),
    )


# ============================================================================
# P2 Mutation Light
# ============================================================================

async def _p2_add_checklist_item(params: Dict[str, Any]) -> Dict[str, Any]:
    return await _get_p2().add_checklist_item_execute(
        work_order_id=params.get("work_order_id") or params.get("entity_id"),
        yacht_id=params["yacht_id"],
        user_id=params.get("user_id"),
        title=params.get("title") or "",
        description=params.get("description"),
        instructions=params.get("instructions"),
        is_required=bool(params.get("is_required", True)),
        requires_photo=bool(params.get("requires_photo", False)),
        requires_signature=bool(params.get("requires_signature", False)),
        category=params.get("category") or "general",
        sequence=params.get("sequence"),
    )


async def _p2_upsert_sop(params: Dict[str, Any]) -> Dict[str, Any]:
    return await _get_p2().upsert_sop_execute(
        work_order_id=params.get("work_order_id") or params.get("entity_id"),
        yacht_id=params["yacht_id"],
        user_id=params.get("user_id"),
        sop_text=params.get("sop_text"),
        sop_document_id=params.get("sop_document_id"),
    )


async def _p2_add_checklist_note(params: Dict[str, Any]) -> Dict[str, Any]:
    return await _get_p2().add_checklist_note_execute(
        checklist_id=params.get("checklist_id") or params.get("entity_id"),
        yacht_id=params["yacht_id"],
        user_id=params.get("user_id"),
        note_text=params.get("note_text") or params.get("note"),
    )


async def _p2_add_checklist_photo(params: Dict[str, Any]) -> Dict[str, Any]:
    return await _get_p2().add_checklist_photo_execute(
        checklist_id=params.get("checklist_id") or params.get("entity_id"),
        yacht_id=params["yacht_id"],
        user_id=params.get("user_id"),
        photo_url=params.get("photo_url"),
        filename=params.get("filename"),
    )


async def _p2_add_document_to_handover(params: Dict[str, Any]) -> Dict[str, Any]:
    return await _get_p2().add_document_to_handover_execute(
        handover_id=params.get("handover_id") or params.get("entity_id"),
        yacht_id=params["yacht_id"],
        user_id=params.get("user_id"),
        document_id=params.get("document_id"),
    )


async def _p2_add_predictive_insight_to_handover(params: Dict[str, Any]) -> Dict[str, Any]:
    return await _get_p2().add_predictive_insight_to_handover_execute(
        handover_id=params.get("handover_id") or params.get("entity_id"),
        yacht_id=params["yacht_id"],
        user_id=params.get("user_id"),
        insight_id=params.get("insight_id"),
    )


async def _p2_add_work_order_note(params: Dict[str, Any]) -> Dict[str, Any]:
    return await _get_p2().add_work_order_note_execute(
        work_order_id=params.get("work_order_id") or params.get("entity_id"),
        yacht_id=params["yacht_id"],
        user_id=params.get("user_id"),
        note_text=params.get("note_text") or params.get("note"),
    )


async def _p2_mark_checklist_item_complete(params: Dict[str, Any]) -> Dict[str, Any]:
    return await _get_p2().mark_checklist_item_complete_execute(
        checklist_item_id=params.get("checklist_item_id") or params.get("item_id") or params.get("entity_id"),
        yacht_id=params["yacht_id"],
        user_id=params.get("user_id"),
        notes=params.get("notes"),
    )


async def _p2_record_voice_note(params: Dict[str, Any]) -> Dict[str, Any]:
    return await _get_p2().record_voice_note_execute(
        entity_id=params.get("entity_id"),
        entity_type=params.get("entity_type"),
        yacht_id=params["yacht_id"],
        user_id=params.get("user_id"),
        audio_url=params.get("audio_url"),
        duration_seconds=params.get("duration_seconds"),
    )


async def _p2_regenerate_handover_summary(params: Dict[str, Any]) -> Dict[str, Any]:
    return await _get_p2().regenerate_handover_summary_execute(
        handover_id=params.get("handover_id") or params.get("entity_id"),
        yacht_id=params["yacht_id"],
        user_id=params.get("user_id"),
    )


async def _p2_tag_for_survey(params: Dict[str, Any]) -> Dict[str, Any]:
    return await _get_p2().tag_for_survey_execute(
        entity_id=params.get("entity_id"),
        entity_type=params.get("entity_type"),
        yacht_id=params["yacht_id"],
        user_id=params.get("user_id"),
        survey_type=params.get("survey_type"),
    )


async def _p2_update_worklist_progress(params: Dict[str, Any]) -> Dict[str, Any]:
    return await _get_p2().update_worklist_progress_execute(
        task_id=params.get("task_id") or params.get("entity_id"),
        yacht_id=params["yacht_id"],
        user_id=params.get("user_id"),
        progress_percent=params.get("progress_percent") or params.get("progress"),
    )


async def _p2_upload_photo(params: Dict[str, Any]) -> Dict[str, Any]:
    return await _get_p2().upload_photo_execute(
        entity_id=params.get("entity_id"),
        entity_type=params.get("entity_type"),
        yacht_id=params["yacht_id"],
        user_id=params.get("user_id"),
        photo_url=params.get("photo_url"),
        filename=params.get("filename"),
        description=params.get("description"),
    )


HANDLERS: Dict[str, Any] = {
    # P1 Compliance
    "log_delivery_received": _log_delivery_received,
    # P2 Mutation Light
    "add_checklist_item": _p2_add_checklist_item,
    "add_checklist_note": _p2_add_checklist_note,
    "add_checklist_photo": _p2_add_checklist_photo,
    "upsert_sop": _p2_upsert_sop,
    "add_document_to_handover": _p2_add_document_to_handover,
    "add_predictive_insight_to_handover": _p2_add_predictive_insight_to_handover,
    "add_work_order_note": _p2_add_work_order_note,
    "mark_checklist_item_complete": _p2_mark_checklist_item_complete,
    "record_voice_note": _p2_record_voice_note,
    "regenerate_handover_summary": _p2_regenerate_handover_summary,
    "tag_for_survey": _p2_tag_for_survey,
    "update_worklist_progress": _p2_update_worklist_progress,
    "upload_photo": _p2_upload_photo,
}
