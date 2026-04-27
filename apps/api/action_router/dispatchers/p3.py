"""P3 read-only action handlers."""

from typing import Dict, Any
import logging
from integrations.supabase import get_supabase_client
from handlers.p3_read_only_handlers import P3ReadOnlyHandlers

logger = logging.getLogger(__name__)

_p3_handlers = None


def _get_p3_handlers():
    global _p3_handlers
    if _p3_handlers is None:
        _p3_handlers = P3ReadOnlyHandlers(get_supabase_client())
    return _p3_handlers


async def _view_document(params: Dict[str, Any]) -> Dict[str, Any]:
    return await _get_p3_handlers().view_document_execute(
        document_id=params.get("document_id") or params.get("entity_id"),
        yacht_id=params["yacht_id"],
    )


async def _view_related_documents(params: Dict[str, Any]) -> Dict[str, Any]:
    return await _get_p3_handlers().view_related_documents_execute(
        entity_id=params.get("entity_id"),
        entity_type=params.get("entity_type"),
        yacht_id=params["yacht_id"],
    )


async def _view_document_section(params: Dict[str, Any]) -> Dict[str, Any]:
    return await _get_p3_handlers().view_document_section_execute(
        document_id=params.get("document_id"),
        section_id=params.get("section_id"),
        yacht_id=params["yacht_id"],
    )


async def _view_work_order_history(params: Dict[str, Any]) -> Dict[str, Any]:
    return await _get_p3_handlers().view_work_order_history_execute(
        work_order_id=params.get("work_order_id") or params.get("entity_id"),
        yacht_id=params["yacht_id"],
    )


async def _view_checklist(params: Dict[str, Any]) -> Dict[str, Any]:
    return await _get_p3_handlers().view_checklist_execute(
        checklist_id=params.get("checklist_id") or params.get("entity_id"),
        yacht_id=params["yacht_id"],
    )


async def _view_equipment_details(params: Dict[str, Any]) -> Dict[str, Any]:
    return await _get_p3_handlers().view_equipment_details_execute(
        equipment_id=params.get("equipment_id") or params.get("entity_id"),
        yacht_id=params["yacht_id"],
    )


async def _view_equipment_history(params: Dict[str, Any]) -> Dict[str, Any]:
    return await _get_p3_handlers().view_equipment_history_execute(
        equipment_id=params.get("equipment_id") or params.get("entity_id"),
        yacht_id=params["yacht_id"],
    )


async def _view_equipment_parts(params: Dict[str, Any]) -> Dict[str, Any]:
    return await _get_p3_handlers().view_equipment_parts_execute(
        equipment_id=params.get("equipment_id") or params.get("entity_id"),
        yacht_id=params["yacht_id"],
    )


async def _view_linked_faults(params: Dict[str, Any]) -> Dict[str, Any]:
    return await _get_p3_handlers().view_linked_faults_execute(
        equipment_id=params.get("equipment_id") or params.get("entity_id"),
        yacht_id=params["yacht_id"],
    )


async def _view_equipment_manual(params: Dict[str, Any]) -> Dict[str, Any]:
    return await _get_p3_handlers().view_equipment_manual_execute(
        equipment_id=params.get("equipment_id") or params.get("entity_id"),
        yacht_id=params["yacht_id"],
    )


async def _view_fleet_summary(params: Dict[str, Any]) -> Dict[str, Any]:
    return await _get_p3_handlers().view_fleet_summary_execute(yacht_id=params["yacht_id"])


async def _open_vessel(params: Dict[str, Any]) -> Dict[str, Any]:
    return await _get_p3_handlers().open_vessel_execute(
        vessel_id=params.get("vessel_id") or params.get("entity_id"),
        yacht_id=params["yacht_id"],
    )


async def _export_fleet_summary(params: Dict[str, Any]) -> Dict[str, Any]:
    return await _get_p3_handlers().export_fleet_summary_execute(
        yacht_id=params["yacht_id"],
        format=params.get("format", "pdf"),
    )


async def _request_predictive_insight(params: Dict[str, Any]) -> Dict[str, Any]:
    return await _get_p3_handlers().request_predictive_insight_execute(
        equipment_id=params.get("equipment_id") or params.get("entity_id"),
        yacht_id=params["yacht_id"],
    )


async def _view_part_stock(params: Dict[str, Any]) -> Dict[str, Any]:
    return await _get_p3_handlers().view_part_stock_execute(
        part_id=params.get("part_id") or params.get("entity_id"),
        yacht_id=params["yacht_id"],
    )


async def _view_part_location(params: Dict[str, Any]) -> Dict[str, Any]:
    return await _get_p3_handlers().view_part_location_execute(
        part_id=params.get("part_id") or params.get("entity_id"),
        yacht_id=params["yacht_id"],
    )


async def _view_part_usage(params: Dict[str, Any]) -> Dict[str, Any]:
    return await _get_p3_handlers().view_part_usage_execute(
        part_id=params.get("part_id") or params.get("entity_id"),
        yacht_id=params["yacht_id"],
    )


async def _scan_part_barcode(params: Dict[str, Any]) -> Dict[str, Any]:
    return await _get_p3_handlers().scan_part_barcode_execute(
        barcode=params.get("barcode"),
        yacht_id=params["yacht_id"],
    )


async def _view_linked_equipment(params: Dict[str, Any]) -> Dict[str, Any]:
    return await _get_p3_handlers().view_linked_equipment_execute(
        part_id=params.get("part_id") or params.get("entity_id"),
        yacht_id=params["yacht_id"],
    )


async def _export_handover(params: Dict[str, Any]) -> Dict[str, Any]:
    return await _get_p3_handlers().export_handover_execute(
        yacht_id=params["yacht_id"],
        user_id=params.get("user_id", ""),
        date_range_hours=int(params.get("date_range_hours", 24)),
        format=params.get("format", "json"),
    )


async def _view_smart_summary(params: Dict[str, Any]) -> Dict[str, Any]:
    return await _get_p3_handlers().view_smart_summary_execute(
        yacht_id=params["yacht_id"],
        period=params.get("period", "today"),
    )


async def _view_compliance_status(params: Dict[str, Any]) -> Dict[str, Any]:
    return await _get_p3_handlers().view_compliance_status_execute(yacht_id=params["yacht_id"])


HANDLERS: Dict[str, Any] = {
    "view_document": _view_document,
    "view_related_documents": _view_related_documents,
    "view_document_section": _view_document_section,
    "view_work_order_history": _view_work_order_history,
    "view_checklist": _view_checklist,
    "view_equipment_details": _view_equipment_details,
    "view_equipment_history": _view_equipment_history,
    "view_equipment_parts": _view_equipment_parts,
    "view_linked_faults": _view_linked_faults,
    "view_equipment_manual": _view_equipment_manual,
    "view_fleet_summary": _view_fleet_summary,
    "open_vessel": _open_vessel,
    "export_fleet_summary": _export_fleet_summary,
    "request_predictive_insight": _request_predictive_insight,
    "view_part_stock": _view_part_stock,
    "view_part_location": _view_part_location,
    "view_part_usage": _view_part_usage,
    "scan_part_barcode": _scan_part_barcode,
    "view_linked_equipment": _view_linked_equipment,
    "export_handover": _export_handover,
    "view_smart_summary": _view_smart_summary,
    "view_compliance_status": _view_compliance_status,
}
