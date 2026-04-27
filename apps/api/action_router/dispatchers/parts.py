"""Parts domain action handlers."""

from typing import Dict, Any
import logging
from integrations.supabase import get_supabase_client
from handlers.part_handlers import get_part_handlers as _get_part_handlers_raw

logger = logging.getLogger(__name__)

_part_handlers = None


def _get_part_handlers():
    global _part_handlers
    if _part_handlers is None:
        _part_handlers = _get_part_handlers_raw(get_supabase_client())
    return _part_handlers


async def _part_view_part_details(params: Dict[str, Any]) -> Dict[str, Any]:
    fn = _get_part_handlers().get("view_part_details")
    if not fn:
        raise ValueError("view_part_details handler not registered")
    return await fn(
        entity_id=params.get("part_id") or params.get("entity_id", ""),
        yacht_id=params["yacht_id"],
        user_id=params["user_id"],
    )


async def _part_add_to_shopping_list(params: Dict[str, Any]) -> Dict[str, Any]:
    fn = _get_part_handlers().get("add_to_shopping_list")
    if not fn:
        raise ValueError("add_to_shopping_list handler not registered")
    part_id = params.get("part_id") or params.get("entity_id")
    if not part_id:
        raise ValueError("part_id is required")
    return await fn(
        yacht_id=params["yacht_id"],
        user_id=params["user_id"],
        part_id=part_id,
        quantity_requested=params.get("quantity_requested") or params.get("quantity", 1),
        urgency=params.get("urgency", "normal"),
        notes=params.get("reason") or params.get("notes"),
        shopping_list_id=params.get("shopping_list_id"),
    )


async def _part_consume_part(params: Dict[str, Any]) -> Dict[str, Any]:
    fn = _get_part_handlers().get("consume_part")
    if not fn:
        raise ValueError("consume_part handler not registered")
    return await fn(
        yacht_id=params["yacht_id"], user_id=params["user_id"],
        part_id=params["part_id"], quantity=params["quantity"],
        work_order_id=params.get("work_order_id"), notes=params.get("notes"),
    )


async def _part_receive_part(params: Dict[str, Any]) -> Dict[str, Any]:
    fn = _get_part_handlers().get("receive_part")
    if not fn:
        raise ValueError("receive_part handler not registered")
    return await fn(
        yacht_id=params["yacht_id"], user_id=params["user_id"],
        part_id=params["part_id"], quantity=params["quantity"],
        to_location_id=params.get("to_location_id"), supplier_id=params.get("supplier_id"),
        invoice_number=params.get("invoice_number"), photo_storage_path=params.get("photo_storage_path"),
        idempotency_key=params.get("idempotency_key"),
    )


async def _part_transfer_part(params: Dict[str, Any]) -> Dict[str, Any]:
    fn = _get_part_handlers().get("transfer_part")
    if not fn:
        raise ValueError("transfer_part handler not registered")
    return await fn(
        yacht_id=params["yacht_id"], user_id=params["user_id"],
        part_id=params["part_id"], quantity=params["quantity"],
        from_location=params["from_location"], to_location=params["to_location"],
        notes=params.get("notes"),
    )


async def _part_adjust_stock_quantity(params: Dict[str, Any]) -> Dict[str, Any]:
    fn = _get_part_handlers().get("adjust_stock_quantity")
    if not fn:
        raise ValueError("adjust_stock_quantity handler not registered")
    return await fn(
        yacht_id=params["yacht_id"], user_id=params["user_id"],
        part_id=params["part_id"], new_quantity=params["new_quantity"],
        reason=params["reason"], signature=params.get("signature"), location=params.get("location"),
    )


async def _part_write_off_part(params: Dict[str, Any]) -> Dict[str, Any]:
    fn = _get_part_handlers().get("write_off_part")
    if not fn:
        raise ValueError("write_off_part handler not registered")
    return await fn(
        yacht_id=params["yacht_id"], user_id=params["user_id"],
        part_id=params["part_id"], quantity=params["quantity"],
        reason=params["reason"], signature=params.get("signature"),
    )


async def _part_generate_part_labels(params: Dict[str, Any]) -> Dict[str, Any]:
    fn = _get_part_handlers().get("generate_part_labels")
    if not fn:
        raise ValueError("generate_part_labels handler not registered")
    return await fn(
        yacht_id=params["yacht_id"], user_id=params["user_id"],
        part_ids=params["part_ids"], label_type=params.get("label_type", "standard"),
        include_qr=params.get("include_qr", True),
    )


async def _part_request_label_output(params: Dict[str, Any]) -> Dict[str, Any]:
    fn = _get_part_handlers().get("request_label_output")
    if not fn:
        raise ValueError("request_label_output handler not registered")
    return await fn(
        yacht_id=params["yacht_id"], user_id=params["user_id"],
        label_pdf_path=params["label_pdf_path"], output_method=params["output_method"],
        recipient_email=params.get("recipient_email"),
    )


HANDLERS: Dict[str, Any] = {
    "view_part_details": _part_view_part_details,
    "add_to_shopping_list": _part_add_to_shopping_list,
    "consume_part": _part_consume_part,
    "receive_part": _part_receive_part,
    "transfer_part": _part_transfer_part,
    "adjust_stock_quantity": _part_adjust_stock_quantity,
    "write_off_part": _part_write_off_part,
    "generate_part_labels": _part_generate_part_labels,
    "request_label_output": _part_request_label_output,
    "reorder_part": _part_add_to_shopping_list,
    "update_part_details": _part_view_part_details,
    "archive_part": None,  # soft_delete in index.py
    "delete_part": None,
}
