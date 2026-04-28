"""Parts domain action dispatchers.

Bridges the dispatcher calling convention (async fn(params: dict) → dict) to the
Phase 4 handler signature (payload, context, yacht_id, user_id, user_context, db_client).

All business logic lives in handlers/part_handlers.py — nothing here except the bridge.
"""

from typing import Dict, Any
import logging
from integrations.supabase import get_supabase_client
from handlers.part_handlers import HANDLERS as _PARTS_P4_HANDLERS

logger = logging.getLogger(__name__)


def _phase4_call(action_id: str, params: Dict[str, Any]) -> Any:
    """Call a Phase 4 flat handler (payload, context, yacht_id, user_id, user_context, db_client)."""
    fn = _PARTS_P4_HANDLERS.get(action_id)
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


async def _part_view_part_details(params: Dict[str, Any]) -> Dict[str, Any]:
    return await _phase4_call("view_part_details", params)


async def _part_update_part_details(params: Dict[str, Any]) -> Dict[str, Any]:
    return await _phase4_call("update_part_details", params)


async def _part_add_to_shopping_list(params: Dict[str, Any]) -> Dict[str, Any]:
    return await _phase4_call("add_to_shopping_list", params)


async def _part_consume_part(params: Dict[str, Any]) -> Dict[str, Any]:
    return await _phase4_call("consume_part", params)


async def _part_receive_part(params: Dict[str, Any]) -> Dict[str, Any]:
    return await _phase4_call("receive_part", params)


async def _part_transfer_part(params: Dict[str, Any]) -> Dict[str, Any]:
    return await _phase4_call("transfer_part", params)


async def _part_adjust_stock_quantity(params: Dict[str, Any]) -> Dict[str, Any]:
    return await _phase4_call("adjust_stock_quantity", params)


async def _part_write_off_part(params: Dict[str, Any]) -> Dict[str, Any]:
    return await _phase4_call("write_off_part", params)


async def _part_generate_part_labels(params: Dict[str, Any]) -> Dict[str, Any]:
    return await _phase4_call("generate_part_labels", params)


async def _part_request_label_output(params: Dict[str, Any]) -> Dict[str, Any]:
    return await _phase4_call("request_label_output", params)


async def _part_view_part_stock(params: Dict[str, Any]) -> Dict[str, Any]:
    return await _phase4_call("view_part_stock", params)


async def _part_view_part_location(params: Dict[str, Any]) -> Dict[str, Any]:
    return await _phase4_call("view_part_location", params)


async def _part_view_part_usage(params: Dict[str, Any]) -> Dict[str, Any]:
    return await _phase4_call("view_part_usage", params)


async def _part_view_linked_equipment(params: Dict[str, Any]) -> Dict[str, Any]:
    return await _phase4_call("view_linked_equipment", params)


async def _part_order_part(params: Dict[str, Any]) -> Dict[str, Any]:
    return await _phase4_call("order_part", params)


async def _part_scan_part_barcode(params: Dict[str, Any]) -> Dict[str, Any]:
    return await _phase4_call("scan_part_barcode", params)


async def _part_check_stock_level(params: Dict[str, Any]) -> Dict[str, Any]:
    return await _phase4_call("check_stock_level", params)


async def _part_log_part_usage(params: Dict[str, Any]) -> Dict[str, Any]:
    return await _phase4_call("log_part_usage", params)


async def _part_view_low_stock(params: Dict[str, Any]) -> Dict[str, Any]:
    return await _phase4_call("view_low_stock", params)


HANDLERS: Dict[str, Any] = {
    "view_part_details": _part_view_part_details,
    "update_part_details": _part_update_part_details,
    "add_to_shopping_list": _part_add_to_shopping_list,
    "reorder_part": _part_add_to_shopping_list,      # alias
    "consume_part": _part_consume_part,
    "receive_part": _part_receive_part,
    "transfer_part": _part_transfer_part,
    "adjust_stock_quantity": _part_adjust_stock_quantity,
    "write_off_part": _part_write_off_part,
    "generate_part_labels": _part_generate_part_labels,
    "request_label_output": _part_request_label_output,
    "view_part_stock": _part_view_part_stock,
    "view_part_location": _part_view_part_location,
    "view_part_usage": _part_view_part_usage,
    "view_linked_equipment": _part_view_linked_equipment,
    "order_part": _part_order_part,
    "scan_part_barcode": _part_scan_part_barcode,
    "check_stock_level": _part_check_stock_level,
    "log_part_usage": _part_log_part_usage,
    "view_low_stock": _part_view_low_stock,
    "archive_part": None,    # soft_delete — resolved in dispatchers/index.py
    "delete_part": None,     # soft_delete — resolved in dispatchers/index.py
    "suggest_parts": None,   # not yet implemented
}
