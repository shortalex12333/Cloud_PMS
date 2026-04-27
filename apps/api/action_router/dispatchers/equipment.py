"""Equipment domain action handlers."""

from typing import Dict, Any
import logging
from integrations.supabase import get_supabase_client
from handlers.equipment_handlers import get_equipment_handlers as _get_equipment_handlers_raw

logger = logging.getLogger(__name__)

_equipment_handlers = None


def _get_equipment_handlers():
    global _equipment_handlers
    if _equipment_handlers is None:
        _equipment_handlers = _get_equipment_handlers_raw(get_supabase_client())
    return _equipment_handlers


async def _eq_view_equipment(params: Dict[str, Any]) -> Dict[str, Any]:
    handlers = _get_equipment_handlers()
    fn = handlers.get("view_equipment")
    if not fn:
        raise ValueError("view_equipment handler not registered")
    return await fn(
        entity_id=params.get("equipment_id") or params.get("entity_id"),
        yacht_id=params["yacht_id"],
        params=params,
    )


async def _eq_view_maintenance_history(params: Dict[str, Any]) -> Dict[str, Any]:
    handlers = _get_equipment_handlers()
    fn = handlers.get("view_maintenance_history")
    if not fn:
        raise ValueError("view_maintenance_history handler not registered")
    return await fn(
        entity_id=params.get("equipment_id") or params.get("entity_id"),
        yacht_id=params["yacht_id"],
        params=params,
    )


async def _eq_view_equipment_parts(params: Dict[str, Any]) -> Dict[str, Any]:
    handlers = _get_equipment_handlers()
    fn = handlers.get("view_equipment_parts")
    if not fn:
        raise ValueError("view_equipment_parts handler not registered")
    return await fn(
        entity_id=params.get("equipment_id") or params.get("entity_id"),
        yacht_id=params["yacht_id"],
        params=params,
    )


async def _eq_view_linked_faults(params: Dict[str, Any]) -> Dict[str, Any]:
    handlers = _get_equipment_handlers()
    fn = handlers.get("view_linked_faults")
    if not fn:
        raise ValueError("view_linked_faults handler not registered")
    return await fn(
        entity_id=params.get("equipment_id") or params.get("entity_id"),
        yacht_id=params["yacht_id"],
        params=params,
    )


async def _eq_view_equipment_manual(params: Dict[str, Any]) -> Dict[str, Any]:
    handlers = _get_equipment_handlers()
    fn = handlers.get("view_equipment_manual")
    if not fn:
        raise ValueError("view_equipment_manual handler not registered")
    return await fn(
        entity_id=params.get("equipment_id") or params.get("entity_id"),
        yacht_id=params["yacht_id"],
        params=params,
    )


async def _eq_update_equipment_status(params: Dict[str, Any]) -> Dict[str, Any]:
    handlers = _get_equipment_handlers()
    fn = handlers.get("update_equipment_status")
    if not fn:
        raise ValueError("update_equipment_status handler not registered")
    return await fn(**params)


async def _eq_add_equipment_note(params: Dict[str, Any]) -> Dict[str, Any]:
    handlers = _get_equipment_handlers()
    fn = handlers.get("add_equipment_note")
    if not fn:
        raise ValueError("add_equipment_note handler not registered")
    return await fn(**params)


async def _eq_attach_file_to_equipment(params: Dict[str, Any]) -> Dict[str, Any]:
    handlers = _get_equipment_handlers()
    fn = handlers.get("attach_file_to_equipment")
    if not fn:
        raise ValueError("attach_file_to_equipment handler not registered")
    return await fn(**params)


async def _eq_create_work_order_for_equipment(params: Dict[str, Any]) -> Dict[str, Any]:
    handlers = _get_equipment_handlers()
    fn = handlers.get("create_work_order_for_equipment")
    if not fn:
        raise ValueError("create_work_order_for_equipment handler not registered")
    return await fn(**params)


async def _eq_link_part_to_equipment(params: Dict[str, Any]) -> Dict[str, Any]:
    handlers = _get_equipment_handlers()
    fn = handlers.get("link_part_to_equipment")
    if not fn:
        raise ValueError("link_part_to_equipment handler not registered")
    return await fn(**params)


async def _eq_flag_equipment_attention(params: Dict[str, Any]) -> Dict[str, Any]:
    handlers = _get_equipment_handlers()
    fn = handlers.get("flag_equipment_attention")
    if not fn:
        raise ValueError("flag_equipment_attention handler not registered")
    return await fn(**params)


async def _eq_decommission_equipment(params: Dict[str, Any]) -> Dict[str, Any]:
    handlers = _get_equipment_handlers()
    fn = handlers.get("decommission_equipment")
    if not fn:
        raise ValueError("decommission_equipment handler not registered")
    return await fn(**params)


async def _eq_record_equipment_hours(params: Dict[str, Any]) -> Dict[str, Any]:
    handlers = _get_equipment_handlers()
    fn = handlers.get("record_equipment_hours")
    if not fn:
        raise ValueError("record_equipment_hours handler not registered")
    return await fn(**params)


async def _eq_create_equipment(params: Dict[str, Any]) -> Dict[str, Any]:
    handlers = _get_equipment_handlers()
    fn = handlers.get("create_equipment")
    if not fn:
        raise ValueError("create_equipment handler not registered")
    return await fn(**params)


async def _eq_assign_parent_equipment(params: Dict[str, Any]) -> Dict[str, Any]:
    handlers = _get_equipment_handlers()
    fn = handlers.get("assign_parent_equipment")
    if not fn:
        raise ValueError("assign_parent_equipment handler not registered")
    return await fn(**params)


async def _eq_archive_equipment(params: Dict[str, Any]) -> Dict[str, Any]:
    handlers = _get_equipment_handlers()
    fn = handlers.get("archive_equipment")
    if not fn:
        raise ValueError("archive_equipment handler not registered")
    return await fn(**params)


async def _eq_restore_archived_equipment(params: Dict[str, Any]) -> Dict[str, Any]:
    handlers = _get_equipment_handlers()
    fn = handlers.get("restore_archived_equipment")
    if not fn:
        raise ValueError("restore_archived_equipment handler not registered")
    return await fn(**params)


async def _eq_get_open_faults_for_equipment(params: Dict[str, Any]) -> Dict[str, Any]:
    handlers = _get_equipment_handlers()
    fn = handlers.get("get_open_faults_for_equipment")
    if not fn:
        raise ValueError("get_open_faults_for_equipment handler not registered")
    return await fn(**params)


async def _eq_get_related_entities_for_equipment(params: Dict[str, Any]) -> Dict[str, Any]:
    handlers = _get_equipment_handlers()
    fn = handlers.get("get_related_entities_for_equipment")
    if not fn:
        raise ValueError("get_related_entities_for_equipment handler not registered")
    return await fn(**params)


async def _eq_add_entity_link(params: Dict[str, Any]) -> Dict[str, Any]:
    handlers = _get_equipment_handlers()
    fn = handlers.get("add_entity_link")
    if not fn:
        raise ValueError("add_entity_link handler not registered")
    return await fn(**params)


async def _eq_link_document_to_equipment(params: Dict[str, Any]) -> Dict[str, Any]:
    handlers = _get_equipment_handlers()
    fn = handlers.get("link_document_to_equipment")
    if not fn:
        raise ValueError("link_document_to_equipment handler not registered")
    return await fn(**params)


async def _eq_attach_image_with_comment(params: Dict[str, Any]) -> Dict[str, Any]:
    handlers = _get_equipment_handlers()
    fn = handlers.get("attach_image_with_comment")
    if not fn:
        raise ValueError("attach_image_with_comment handler not registered")
    return await fn(**params)


async def _eq_decommission_and_replace(params: Dict[str, Any]) -> Dict[str, Any]:
    handlers = _get_equipment_handlers()
    fn = handlers.get("decommission_and_replace_equipment")
    if not fn:
        raise ValueError("decommission_and_replace_equipment handler not registered")
    return await fn(**params)


HANDLERS: Dict[str, Any] = {
    "view_equipment": _eq_view_equipment,
    "view_maintenance_history": _eq_view_maintenance_history,
    "view_equipment_parts": _eq_view_equipment_parts,
    "view_linked_faults": _eq_view_linked_faults,
    "view_equipment_manual": _eq_view_equipment_manual,
    "update_equipment_status": _eq_update_equipment_status,
    "add_equipment_note": _eq_add_equipment_note,
    "attach_file_to_equipment": _eq_attach_file_to_equipment,
    "create_work_order_for_equipment": _eq_create_work_order_for_equipment,
    "link_part_to_equipment": _eq_link_part_to_equipment,
    "flag_equipment_attention": _eq_flag_equipment_attention,
    "decommission_equipment": _eq_decommission_equipment,
    "record_equipment_hours": _eq_record_equipment_hours,
    "create_equipment": _eq_create_equipment,
    "assign_parent_equipment": _eq_assign_parent_equipment,
    "archive_equipment": _eq_archive_equipment,
    "restore_archived_equipment": _eq_restore_archived_equipment,
    "get_open_faults_for_equipment": _eq_get_open_faults_for_equipment,
    "get_related_entities_for_equipment": _eq_get_related_entities_for_equipment,
    "add_entity_link": _eq_add_entity_link,
    "link_document_to_equipment": _eq_link_document_to_equipment,
    "attach_image_with_comment": _eq_attach_image_with_comment,
    "decommission_and_replace_equipment": _eq_decommission_and_replace,
}
