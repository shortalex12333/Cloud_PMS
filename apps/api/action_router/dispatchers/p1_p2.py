"""P1 compliance, P1 purchasing, and P2 mutation-light action handlers."""

from typing import Dict, Any
import logging
from integrations.supabase import get_supabase_client
from handlers.p1_compliance_handlers import P1ComplianceHandlers
from handlers.p1_purchasing_handlers import P1PurchasingHandlers
from handlers.p2_mutation_light_handlers import P2MutationLightHandlers
from handlers.stub_handlers import not_yet_implemented as _not_yet_implemented

logger = logging.getLogger(__name__)

_p1_compliance_handlers = None
_p1_purchasing_handlers = None
_p2_handlers = None


def _get_p1_compliance():
    global _p1_compliance_handlers
    if _p1_compliance_handlers is None:
        _p1_compliance_handlers = P1ComplianceHandlers(get_supabase_client())
    return _p1_compliance_handlers


def _get_p1_purchasing():
    global _p1_purchasing_handlers
    if _p1_purchasing_handlers is None:
        _p1_purchasing_handlers = P1PurchasingHandlers(get_supabase_client())
    return _p1_purchasing_handlers


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
# P1 Purchasing
# ============================================================================

async def _create_purchase_request(params: Dict[str, Any]) -> Dict[str, Any]:
    return await _get_p1_purchasing().create_purchase_request_execute(
        yacht_id=params["yacht_id"],
        user_id=params.get("user_id"),
        items=params.get("items", []),
        supplier_id=params.get("supplier_id"),
        notes=params.get("notes"),
        priority=params.get("priority", "normal"),
    )


async def _order_part(params: Dict[str, Any]) -> Dict[str, Any]:
    purchase_order_id = params.get("purchase_order_id")
    if not purchase_order_id:
        return await _not_yet_implemented(params)
    return await _get_p1_purchasing().order_part_execute(
        purchase_order_id=purchase_order_id,
        part_id=params.get("part_id") or params.get("entity_id"),
        yacht_id=params["yacht_id"],
        user_id=params.get("user_id"),
        quantity=params.get("quantity", 1),
        notes=params.get("notes"),
    )


async def _approve_purchase(params: Dict[str, Any]) -> Dict[str, Any]:
    return await _get_p1_purchasing().approve_purchase_execute(
        purchase_order_id=params.get("purchase_order_id") or params.get("entity_id"),
        yacht_id=params["yacht_id"],
        user_id=params.get("user_id"),
        approval_notes=params.get("approval_notes"),
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


async def _p2_add_equipment_note(params: Dict[str, Any]) -> Dict[str, Any]:
    return await _get_p2().add_equipment_note_execute(
        equipment_id=params.get("equipment_id") or params.get("entity_id"),
        yacht_id=params["yacht_id"],
        user_id=params.get("user_id"),
        note_text=params.get("note_text") or params.get("note"),
    )


async def _p2_add_item_to_purchase(params: Dict[str, Any]) -> Dict[str, Any]:
    return await _get_p2().add_item_to_purchase_execute(
        purchase_order_id=params.get("purchase_order_id") or params.get("entity_id"),
        yacht_id=params["yacht_id"],
        user_id=params.get("user_id"),
        part_id=params.get("part_id"),
        quantity=params.get("quantity", 1),
        unit_price=params.get("unit_price"),
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


async def _p2_update_purchase_status(params: Dict[str, Any]) -> Dict[str, Any]:
    return await _get_p2().update_purchase_status_execute(
        purchase_order_id=params.get("purchase_order_id") or params.get("entity_id"),
        yacht_id=params["yacht_id"],
        user_id=params.get("user_id"),
        new_status=params.get("new_status") or params.get("status"),
    )


async def _p2_update_worklist_progress(params: Dict[str, Any]) -> Dict[str, Any]:
    return await _get_p2().update_worklist_progress_execute(
        task_id=params.get("task_id") or params.get("entity_id"),
        yacht_id=params["yacht_id"],
        user_id=params.get("user_id"),
        progress_percent=params.get("progress_percent") or params.get("progress"),
    )


async def _p2_upload_invoice(params: Dict[str, Any]) -> Dict[str, Any]:
    return await _get_p2().upload_invoice_execute(
        purchase_order_id=params.get("purchase_order_id") or params.get("entity_id"),
        yacht_id=params["yacht_id"],
        user_id=params.get("user_id"),
        invoice_url=params.get("invoice_url"),
        invoice_number=params.get("invoice_number"),
        amount=params.get("amount"),
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
    # P1 Purchasing
    "create_purchase_request": _create_purchase_request,
    "order_part": _order_part,
    "approve_purchase": _approve_purchase,
    # P2 Mutation Light
    "add_checklist_item": _p2_add_checklist_item,
    "add_checklist_note": _p2_add_checklist_note,
    "add_checklist_photo": _p2_add_checklist_photo,
    "upsert_sop": _p2_upsert_sop,
    "add_document_to_handover": _p2_add_document_to_handover,
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
    "cancel_po": None,  # soft_delete — resolved in index.py
    "delete_po": None,  # soft_delete — resolved in index.py
}
