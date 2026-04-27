"""Warranty domain dispatcher — thin param-unpack wrapper over handlers/warranty_handlers.py."""

from typing import Dict, Any
from integrations.supabase import get_supabase_client
from handlers.warranty_handlers import WarrantyHandlers

_warranty_handlers = None


def _get_handlers() -> WarrantyHandlers:
    global _warranty_handlers
    if _warranty_handlers is None:
        _warranty_handlers = WarrantyHandlers(get_supabase_client())
    return _warranty_handlers


async def _draft_warranty_claim(params: Dict[str, Any]) -> Dict[str, Any]:
    return await _get_handlers().draft_warranty_claim(
        yacht_id=params["yacht_id"],
        user_id=params.get("user_id"),
        title=params.get("title", ""),
        description=params.get("description", ""),
        equipment_id=params.get("equipment_id"),
        fault_id=params.get("fault_id"),
        work_order_id=params.get("work_order_id"),
        vendor_name=params.get("vendor_name"),
        manufacturer=params.get("manufacturer"),
        warranty_expiry=params.get("warranty_expiry"),
        claimed_amount=params.get("claimed_amount"),
        currency=params.get("currency"),
        manufacturer_email=params.get("manufacturer_email"),
    )


async def _submit_warranty_claim(params: Dict[str, Any]) -> Dict[str, Any]:
    return await _get_handlers().submit_warranty_claim(
        warranty_id=params.get("warranty_id") or params.get("claim_id") or params.get("entity_id"),
        yacht_id=params["yacht_id"],
        user_id=params.get("user_id"),
    )


async def _approve_warranty_claim(params: Dict[str, Any]) -> Dict[str, Any]:
    return await _get_handlers().approve_warranty_claim(
        warranty_id=params.get("warranty_id") or params.get("claim_id") or params.get("entity_id"),
        yacht_id=params["yacht_id"],
        user_id=params.get("user_id"),
        approved_amount=params.get("approved_amount"),
    )


async def _reject_warranty_claim(params: Dict[str, Any]) -> Dict[str, Any]:
    return await _get_handlers().reject_warranty_claim(
        warranty_id=params.get("warranty_id") or params.get("claim_id") or params.get("entity_id"),
        yacht_id=params["yacht_id"],
        user_id=params.get("user_id"),
        rejection_reason=params.get("rejection_reason", ""),
    )


async def _close_warranty_claim(params: Dict[str, Any]) -> Dict[str, Any]:
    return await _get_handlers().close_warranty_claim(
        warranty_id=params.get("warranty_id") or params.get("claim_id") or params.get("entity_id"),
        yacht_id=params["yacht_id"],
        user_id=params.get("user_id"),
    )


async def _compose_warranty_email(params: Dict[str, Any]) -> Dict[str, Any]:
    return await _get_handlers().compose_warranty_email(
        warranty_id=params.get("warranty_id") or params.get("claim_id") or params.get("entity_id"),
        yacht_id=params["yacht_id"],
        user_id=params.get("user_id"),
    )


async def _add_warranty_note_handler(params: Dict[str, Any]) -> Dict[str, Any]:
    return await _get_handlers().add_warranty_note(
        warranty_id=params.get("warranty_id") or params.get("entity_id"),
        yacht_id=params["yacht_id"],
        user_id=params.get("user_id"),
        note_text=params.get("note_text") or params.get("text", ""),
    )


HANDLERS: Dict[str, Any] = {
    "draft_warranty_claim": _draft_warranty_claim,
    "file_warranty_claim": _draft_warranty_claim,
    "submit_warranty_claim": _submit_warranty_claim,
    "approve_warranty_claim": _approve_warranty_claim,
    "reject_warranty_claim": _reject_warranty_claim,
    "close_warranty_claim": _close_warranty_claim,
    "compose_warranty_email": _compose_warranty_email,
    "add_warranty_note": _add_warranty_note_handler,
    "archive_warranty": None,   # soft_delete — resolved in index.py
    "void_warranty": None,      # soft_delete — resolved in index.py
}
