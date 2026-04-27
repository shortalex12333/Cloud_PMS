"""Receiving domain action handlers."""

from typing import Dict, Any
import logging
from integrations.supabase import get_supabase_client
from handlers.receiving_handlers import (
    ReceivingHandlers,
    _create_receiving_adapter,
    _attach_receiving_image_with_comment_adapter,
    _extract_receiving_candidates_adapter,
    _update_receiving_fields_adapter,
    _add_receiving_item_adapter,
    _adjust_receiving_item_adapter,
    _link_invoice_document_adapter,
    _accept_receiving_adapter,
    _reject_receiving_adapter,
    _view_receiving_history_adapter,
    _flag_discrepancy_adapter,
)
from handlers.receiving_email_handlers import _draft_supplier_email_adapter

logger = logging.getLogger(__name__)

_receiving_handlers = None


def _get_receiving_handlers():
    global _receiving_handlers
    if _receiving_handlers is None:
        handlers_instance = ReceivingHandlers(get_supabase_client())
        _receiving_handlers = {
            "create_receiving": _create_receiving_adapter(handlers_instance),
            "attach_receiving_image_with_comment": _attach_receiving_image_with_comment_adapter(handlers_instance),
            "extract_receiving_candidates": _extract_receiving_candidates_adapter(handlers_instance),
            "update_receiving_fields": _update_receiving_fields_adapter(handlers_instance),
            "add_receiving_item": _add_receiving_item_adapter(handlers_instance),
            "adjust_receiving_item": _adjust_receiving_item_adapter(handlers_instance),
            "link_invoice_document": _link_invoice_document_adapter(handlers_instance),
            "accept_receiving": _accept_receiving_adapter(handlers_instance),
            "reject_receiving": _reject_receiving_adapter(handlers_instance),
            "view_receiving_history": _view_receiving_history_adapter(handlers_instance),
            "flag_discrepancy": _flag_discrepancy_adapter(handlers_instance),
            "draft_supplier_email": _draft_supplier_email_adapter(),
        }
    return _receiving_handlers


async def _recv_create_receiving(params: Dict[str, Any]) -> Dict[str, Any]:
    fn = _get_receiving_handlers().get("create_receiving")
    if not fn:
        raise ValueError("create_receiving handler not registered")
    return await fn(**params)


async def _recv_attach_image_with_comment(params: Dict[str, Any]) -> Dict[str, Any]:
    fn = _get_receiving_handlers().get("attach_receiving_image_with_comment")
    if not fn:
        raise ValueError("attach_receiving_image_with_comment handler not registered")
    return await fn(**params)


async def _recv_extract_candidates(params: Dict[str, Any]) -> Dict[str, Any]:
    fn = _get_receiving_handlers().get("extract_receiving_candidates")
    if not fn:
        raise ValueError("extract_receiving_candidates handler not registered")
    return await fn(**params)


async def _recv_update_fields(params: Dict[str, Any]) -> Dict[str, Any]:
    fn = _get_receiving_handlers().get("update_receiving_fields")
    if not fn:
        raise ValueError("update_receiving_fields handler not registered")
    return await fn(**params)


async def _recv_add_item(params: Dict[str, Any]) -> Dict[str, Any]:
    fn = _get_receiving_handlers().get("add_receiving_item")
    if not fn:
        raise ValueError("add_receiving_item handler not registered")
    return await fn(**params)


async def _recv_adjust_item(params: Dict[str, Any]) -> Dict[str, Any]:
    fn = _get_receiving_handlers().get("adjust_receiving_item")
    if not fn:
        raise ValueError("adjust_receiving_item handler not registered")
    return await fn(**params)


async def _recv_link_invoice(params: Dict[str, Any]) -> Dict[str, Any]:
    fn = _get_receiving_handlers().get("link_invoice_document")
    if not fn:
        raise ValueError("link_invoice_document handler not registered")
    return await fn(**params)


async def _recv_accept(params: Dict[str, Any]) -> Dict[str, Any]:
    fn = _get_receiving_handlers().get("accept_receiving")
    if not fn:
        raise ValueError("accept_receiving handler not registered")
    return await fn(**params)


async def _recv_reject(params: Dict[str, Any]) -> Dict[str, Any]:
    fn = _get_receiving_handlers().get("reject_receiving")
    if not fn:
        raise ValueError("reject_receiving handler not registered")
    return await fn(**params)


async def _recv_view_history(params: Dict[str, Any]) -> Dict[str, Any]:
    fn = _get_receiving_handlers().get("view_receiving_history")
    if not fn:
        raise ValueError("view_receiving_history handler not registered")
    return await fn(**params)


async def _recv_flag_discrepancy(params: Dict[str, Any]) -> Dict[str, Any]:
    fn = _get_receiving_handlers().get("flag_discrepancy")
    if not fn:
        raise ValueError("flag_discrepancy handler not registered")
    return await fn(**params)


async def _recv_draft_supplier_email(params: Dict[str, Any]) -> Dict[str, Any]:
    fn = _get_receiving_handlers().get("draft_supplier_email")
    if not fn:
        raise ValueError("draft_supplier_email handler not registered")
    return await fn(**params)


HANDLERS: Dict[str, Any] = {
    "create_receiving": _recv_create_receiving,
    "attach_receiving_image_with_comment": _recv_attach_image_with_comment,
    "extract_receiving_candidates": _recv_extract_candidates,
    "update_receiving_fields": _recv_update_fields,
    "add_receiving_item": _recv_add_item,
    "adjust_receiving_item": _recv_adjust_item,
    "link_invoice_document": _recv_link_invoice,
    "accept_receiving": _recv_accept,
    "confirm_receiving": _recv_accept,
    "reject_receiving": _recv_reject,
    "view_receiving_history": _recv_view_history,
    "flag_discrepancy": _recv_flag_discrepancy,
    "draft_supplier_email": _recv_draft_supplier_email,
}
