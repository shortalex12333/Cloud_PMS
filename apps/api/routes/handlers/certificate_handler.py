"""
Certificate Action Handlers — Phase 4 native.

These handlers take priority over the internal_adapter shim in routes/handlers/__init__.py.
Only Phase 4 native handlers live here. All other certificate actions (renew, archive,
suspend, revoke, add_note) are handled by internal_adapter → internal_dispatcher → certificate_handlers.

Routing priority (from __init__.py):
    CERT_HANDLERS (this file) > ADAPTER_HANDLERS (internal_adapter)
"""
import logging

from fastapi import HTTPException
from supabase import Client

logger = logging.getLogger(__name__)

_ALLOWED_ROLES: dict = {
    "create_vessel_certificate": ["chief_engineer", "captain", "manager"],
    "create_crew_certificate":   ["chief_engineer", "captain", "manager"],
    "update_certificate":        ["chief_engineer", "captain", "manager"],
    "link_document_to_certificate": ["chief_engineer", "captain", "manager"],
    "supersede_certificate":     ["captain", "manager"],
}


def _enforce_rbac(action: str, user_context: dict) -> None:
    role = user_context.get("role", "")
    allowed = _ALLOWED_ROLES.get(action, [])
    if role not in allowed:
        logger.warning(f"[RLS] Role '{role}' denied for '{action}'. Allowed: {allowed}")
        raise HTTPException(403, detail=f"Role '{role}' not authorised for '{action}'")


async def _delegate(action_name: str, db_client: Client, payload: dict,
                    yacht_id: str, user_id: str, user_context: dict) -> dict:
    from handlers.certificate_handlers import get_certificate_handlers
    handlers = get_certificate_handlers(db_client)
    fn = handlers.get(action_name)
    if not fn:
        raise HTTPException(501, detail=f"'{action_name}' not registered in certificate_handlers")
    return await fn(**{"yacht_id": yacht_id, "user_id": user_id, **payload})


async def create_vessel_certificate(payload, context, yacht_id, user_id, user_context, db_client):
    _enforce_rbac("create_vessel_certificate", user_context)
    return await _delegate("create_vessel_certificate", db_client, payload, yacht_id, user_id, user_context)


async def create_crew_certificate(payload, context, yacht_id, user_id, user_context, db_client):
    _enforce_rbac("create_crew_certificate", user_context)
    return await _delegate("create_crew_certificate", db_client, payload, yacht_id, user_id, user_context)


async def update_certificate(payload, context, yacht_id, user_id, user_context, db_client):
    _enforce_rbac("update_certificate", user_context)
    return await _delegate("update_certificate", db_client, payload, yacht_id, user_id, user_context)


async def link_document_to_certificate(payload, context, yacht_id, user_id, user_context, db_client):
    _enforce_rbac("link_document_to_certificate", user_context)
    doc_id = payload.get("document_id")
    if not doc_id:
        raise HTTPException(400, detail="document_id is required")
    try:
        dm = db_client.table("doc_metadata").select("id").eq("id", doc_id).maybe_single().execute()
    except Exception:
        dm = None
    if not getattr(dm, "data", None):
        raise HTTPException(404, detail="document_id not found")
    return await _delegate("link_document_to_certificate", db_client, payload, yacht_id, user_id, user_context)


async def supersede_certificate(payload, context, yacht_id, user_id, user_context, db_client):
    _enforce_rbac("supersede_certificate", user_context)
    if not payload.get("signature"):
        raise HTTPException(400, detail="signature payload required for supersede (signed action)")
    return await _delegate("supersede_certificate", db_client, payload, yacht_id, user_id, user_context)


HANDLERS: dict = {
    "create_vessel_certificate":    create_vessel_certificate,
    "create_crew_certificate":      create_crew_certificate,
    "update_certificate":           update_certificate,
    "link_document_to_certificate": link_document_to_certificate,
    "supersede_certificate":        supersede_certificate,
    # renew, archive, suspend, revoke, add_note handled by internal_adapter → internal_dispatcher
}
