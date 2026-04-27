"""Equipment domain action handlers.

Phase C: re-pointed to equipment_handler.HANDLERS (canonical flat-function file).
equipment_handlers.py has been deleted; all its unique actions were merged into
equipment_handler.py.

Calling convention bridge:
  - dispatchers/index.py calls these as: await fn(params)
  - Phase 5 flat handlers expect: (payload, context, yacht_id, user_id, user_context, db_client)
  - Phase C **params handlers expect: **params including db_client
  - This module bridges both by injecting get_supabase_client() as db_client.
"""

from typing import Dict, Any
import logging
from integrations.supabase import get_supabase_client
from handlers.equipment_handler import HANDLERS as _EQUIP_HANDLERS

logger = logging.getLogger(__name__)


def _phase5_call(action_id: str, params: Dict[str, Any]) -> Any:
    """
    Call a Phase 5 flat handler (payload, context, yacht_id, user_id, user_context, db_client).
    Returns the coroutine — caller must await it.
    """
    fn = _EQUIP_HANDLERS.get(action_id)
    if not fn:
        raise ValueError(f"{action_id} handler not registered")
    db = params.get("db_client") or get_supabase_client()
    return fn(
        payload=params,
        context={},
        yacht_id=params["yacht_id"],
        user_id=params.get("user_id", ""),
        user_context=params,
        db_client=db,
    )


def _adapter_call(action_id: str, params: Dict[str, Any]) -> Any:
    """
    Call a Phase C adapter handler (**params contract).
    Returns the coroutine — caller must await it.
    """
    fn = _EQUIP_HANDLERS.get(action_id)
    if not fn:
        raise ValueError(f"{action_id} handler not registered")
    db = params.get("db_client") or get_supabase_client()
    return fn(**{**params, "db_client": db})


# ---------------------------------------------------------------------------
# Phase 5 READ wrappers
# ---------------------------------------------------------------------------

async def _eq_view_equipment(params: Dict[str, Any]) -> Dict[str, Any]:
    return await _phase5_call("view_equipment", params)


async def _eq_view_maintenance_history(params: Dict[str, Any]) -> Dict[str, Any]:
    return await _adapter_call("view_maintenance_history", params)


async def _eq_view_equipment_parts(params: Dict[str, Any]) -> Dict[str, Any]:
    return await _phase5_call("view_equipment_parts", params)


async def _eq_view_linked_faults(params: Dict[str, Any]) -> Dict[str, Any]:
    return await _phase5_call("view_linked_faults", params)


async def _eq_view_equipment_manual(params: Dict[str, Any]) -> Dict[str, Any]:
    return await _phase5_call("view_equipment_manual", params)


# ---------------------------------------------------------------------------
# Phase C MUTATE wrappers
# ---------------------------------------------------------------------------

async def _eq_update_equipment_status(params: Dict[str, Any]) -> Dict[str, Any]:
    return await _phase5_call("update_equipment_status", params)


async def _eq_set_equipment_status(params: Dict[str, Any]) -> Dict[str, Any]:
    return await _adapter_call("set_equipment_status", params)


async def _eq_add_equipment_note(params: Dict[str, Any]) -> Dict[str, Any]:
    return await _phase5_call("add_equipment_note", params)


async def _eq_attach_file_to_equipment(params: Dict[str, Any]) -> Dict[str, Any]:
    return await _adapter_call("attach_file_to_equipment", params)


async def _eq_create_work_order_for_equipment(params: Dict[str, Any]) -> Dict[str, Any]:
    return await _adapter_call("create_work_order_for_equipment", params)


async def _eq_link_part_to_equipment(params: Dict[str, Any]) -> Dict[str, Any]:
    return await _adapter_call("link_part_to_equipment", params)


async def _eq_flag_equipment_attention(params: Dict[str, Any]) -> Dict[str, Any]:
    return await _adapter_call("flag_equipment_attention", params)


async def _eq_decommission_equipment(params: Dict[str, Any]) -> Dict[str, Any]:
    return await _adapter_call("decommission_equipment", params)


async def _eq_record_equipment_hours(params: Dict[str, Any]) -> Dict[str, Any]:
    return await _adapter_call("record_equipment_hours", params)


async def _eq_create_equipment(params: Dict[str, Any]) -> Dict[str, Any]:
    return await _adapter_call("create_equipment", params)


async def _eq_assign_parent_equipment(params: Dict[str, Any]) -> Dict[str, Any]:
    return await _adapter_call("assign_parent_equipment", params)


async def _eq_archive_equipment(params: Dict[str, Any]) -> Dict[str, Any]:
    return await _adapter_call("archive_equipment", params)


async def _eq_restore_archived_equipment(params: Dict[str, Any]) -> Dict[str, Any]:
    return await _adapter_call("restore_archived_equipment", params)


async def _eq_get_open_faults_for_equipment(params: Dict[str, Any]) -> Dict[str, Any]:
    return await _adapter_call("get_open_faults_for_equipment", params)


async def _eq_get_related_entities_for_equipment(params: Dict[str, Any]) -> Dict[str, Any]:
    return await _adapter_call("get_related_entities_for_equipment", params)


async def _eq_add_entity_link(params: Dict[str, Any]) -> Dict[str, Any]:
    return await _adapter_call("add_entity_link", params)


async def _eq_link_document_to_equipment(params: Dict[str, Any]) -> Dict[str, Any]:
    return await _adapter_call("link_document_to_equipment", params)


async def _eq_attach_image_with_comment(params: Dict[str, Any]) -> Dict[str, Any]:
    return await _adapter_call("attach_image_with_comment", params)


async def _eq_decommission_and_replace(params: Dict[str, Any]) -> Dict[str, Any]:
    return await _adapter_call("decommission_and_replace_equipment", params)


HANDLERS: Dict[str, Any] = {
    "view_equipment": _eq_view_equipment,
    "view_maintenance_history": _eq_view_maintenance_history,
    "view_equipment_parts": _eq_view_equipment_parts,
    "view_linked_faults": _eq_view_linked_faults,
    "view_equipment_manual": _eq_view_equipment_manual,
    "update_equipment_status": _eq_update_equipment_status,
    "set_equipment_status": _eq_set_equipment_status,
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
