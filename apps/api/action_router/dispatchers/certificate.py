"""Certificate domain action handlers."""

from typing import Dict, Any
import logging
from integrations.supabase import get_supabase_client
from handlers.certificate_handlers import get_certificate_handlers as _get_certificate_handlers_raw

logger = logging.getLogger(__name__)


def _get_handlers():
    return _get_certificate_handlers_raw(get_supabase_client())


async def _cert_create_vessel_certificate(params: Dict[str, Any]) -> Dict[str, Any]:
    fn = _get_handlers().get("create_vessel_certificate")
    if not fn:
        raise ValueError("create_vessel_certificate handler not registered")
    return await fn(**params)


async def _cert_create_crew_certificate(params: Dict[str, Any]) -> Dict[str, Any]:
    fn = _get_handlers().get("create_crew_certificate")
    if not fn:
        raise ValueError("create_crew_certificate handler not registered")
    return await fn(**params)


async def _cert_update_certificate(params: Dict[str, Any]) -> Dict[str, Any]:
    fn = _get_handlers().get("update_certificate")
    if not fn:
        raise ValueError("update_certificate handler not registered")
    return await fn(**params)


async def _cert_link_document(params: Dict[str, Any]) -> Dict[str, Any]:
    fn = _get_handlers().get("link_document_to_certificate")
    if not fn:
        raise ValueError("link_document_to_certificate handler not registered")
    doc_id = params.get("document_id")
    if not doc_id:
        raise ValueError("document_id is required")
    try:
        supabase = get_supabase_client()
        dm = supabase.table("doc_metadata").select("id").eq("id", doc_id).maybe_single().execute()
    except Exception:
        dm = None
    if not getattr(dm, "data", None):
        raise ValueError("document_id not found")
    return await fn(**params)


async def _cert_link_equipment(params: Dict[str, Any]) -> Dict[str, Any]:
    fn = _get_handlers().get("link_equipment_to_certificate")
    if not fn:
        raise ValueError("link_equipment_to_certificate handler not registered")
    if not params.get("equipment_id"):
        raise ValueError("equipment_id is required")
    if not params.get("certificate_id"):
        raise ValueError("certificate_id is required")
    return await fn(**params)


async def _cert_unlink_equipment(params: Dict[str, Any]) -> Dict[str, Any]:
    fn = _get_handlers().get("unlink_equipment_from_certificate")
    if not fn:
        raise ValueError("unlink_equipment_from_certificate handler not registered")
    if not params.get("equipment_id"):
        raise ValueError("equipment_id is required")
    if not params.get("certificate_id"):
        raise ValueError("certificate_id is required")
    return await fn(**params)


async def _cert_supersede_certificate(params: Dict[str, Any]) -> Dict[str, Any]:
    fn = _get_handlers().get("supersede_certificate")
    if not fn:
        raise ValueError("supersede_certificate handler not registered")
    return await fn(**params)


async def _cert_renew(params: Dict[str, Any]) -> Dict[str, Any]:
    fn = _get_handlers().get("renew_certificate")
    if not fn:
        raise ValueError("renew_certificate handler not registered")
    return await fn(**params)


async def _cert_archive(params: Dict[str, Any]) -> Dict[str, Any]:
    fn = _get_handlers().get("archive_certificate")
    if not fn:
        raise ValueError("archive_certificate handler not registered")
    return await fn(**params)


async def _cert_suspend(params: Dict[str, Any]) -> Dict[str, Any]:
    fn = _get_handlers().get("suspend_certificate")
    if not fn:
        raise ValueError("suspend_certificate handler not registered")
    return await fn(**params)


async def _cert_revoke(params: Dict[str, Any]) -> Dict[str, Any]:
    fn = _get_handlers().get("revoke_certificate")
    if not fn:
        raise ValueError("revoke_certificate handler not registered")
    return await fn(**params)


async def _cert_assign(params: Dict[str, Any]) -> Dict[str, Any]:
    fn = _get_handlers().get("assign_certificate")
    if not fn:
        raise ValueError("assign_certificate handler not registered")
    return await fn(**params)


HANDLERS: Dict[str, Any] = {
    "create_vessel_certificate": _cert_create_vessel_certificate,
    "create_crew_certificate": _cert_create_crew_certificate,
    "update_certificate": _cert_update_certificate,
    "link_document_to_certificate": _cert_link_document,
    "link_equipment_to_certificate": _cert_link_equipment,
    "unlink_equipment_from_certificate": _cert_unlink_equipment,
    "supersede_certificate": _cert_supersede_certificate,
    "renew_certificate": _cert_renew,
    "archive_certificate": _cert_archive,
    "suspend_certificate": _cert_suspend,
    "revoke_certificate": _cert_revoke,
    "assign_certificate": _cert_assign,
}
