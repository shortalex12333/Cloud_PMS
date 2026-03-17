"""
Certificate Action Handlers

Migrated from p0_actions_routes.py elif blocks (Phase 4, Task 5).
Handler contract: see handlers/__init__.py header.
Do NOT call get_tenant_supabase_client — db_client is pre-constructed by dispatcher.

Block 1 (L2557-2562): add_certificate, renew_certificate, add_service_contract, record_contract_claim
    — BLOCKED: pms_certificates / pms_service_contracts tables do not exist.
Block 2 (L4897-4959): create_vessel_certificate, create_crew_certificate, update_certificate,
    link_document_to_certificate, supersede_certificate
    — Delegates to handlers.certificate_handlers.CertificateHandlers via get_certificate_handlers().
"""
import logging

from fastapi import HTTPException
from supabase import Client

logger = logging.getLogger(__name__)

# RBAC mapping for Certificate Lens v2 actions (from original elif block L4902-4908)
_CERT_V2_ALLOWED_ROLES = {
    "create_vessel_certificate": ["chief_engineer", "captain", "manager"],
    "create_crew_certificate": ["chief_engineer", "captain", "manager"],
    "update_certificate": ["chief_engineer", "captain", "manager"],
    "link_document_to_certificate": ["chief_engineer", "captain", "manager"],
    "supersede_certificate": ["captain", "manager"],
}


# ============================================================================
# BLOCKED ACTIONS (L2557-2562) — tables do not exist yet
# ============================================================================

async def add_certificate(
    payload: dict,
    context: dict,
    yacht_id: str,
    user_id: str,
    user_context: dict,
    db_client: Client,
) -> dict:
    raise HTTPException(
        status_code=501,
        detail="Action 'add_certificate' BLOCKED: pms_certificates/pms_service_contracts tables do not exist."
    )


async def renew_certificate(
    payload: dict,
    context: dict,
    yacht_id: str,
    user_id: str,
    user_context: dict,
    db_client: Client,
) -> dict:
    raise HTTPException(
        status_code=501,
        detail="Action 'renew_certificate' BLOCKED: pms_certificates/pms_service_contracts tables do not exist."
    )


async def add_service_contract(
    payload: dict,
    context: dict,
    yacht_id: str,
    user_id: str,
    user_context: dict,
    db_client: Client,
) -> dict:
    raise HTTPException(
        status_code=501,
        detail="Action 'add_service_contract' BLOCKED: pms_certificates/pms_service_contracts tables do not exist."
    )


async def record_contract_claim(
    payload: dict,
    context: dict,
    yacht_id: str,
    user_id: str,
    user_context: dict,
    db_client: Client,
) -> dict:
    raise HTTPException(
        status_code=501,
        detail="Action 'record_contract_claim' BLOCKED: pms_certificates/pms_service_contracts tables do not exist."
    )


# ============================================================================
# CERT LENS V2 ACTIONS (L4897-4959) — delegate to handlers.certificate_handlers
# ============================================================================

async def _delegate_to_cert_handler(
    action_name: str,
    db_client: Client,
    payload: dict,
    yacht_id: str,
    user_id: str,
    user_context: dict,
) -> dict:
    """Single factory call shared by all cert v2 delegate functions."""
    from handlers.certificate_handlers import get_certificate_handlers
    cert_handlers = get_certificate_handlers(db_client)
    handler_fn = cert_handlers.get(action_name)
    if not handler_fn:
        raise HTTPException(status_code=501, detail=f"Certificate action '{action_name}' not implemented")
    handler_params = {"yacht_id": yacht_id, "user_id": user_id, **payload}
    return await handler_fn(**handler_params)


async def create_vessel_certificate(
    payload: dict,
    context: dict,
    yacht_id: str,
    user_id: str,
    user_context: dict,
    db_client: Client,
) -> dict:
    _enforce_cert_rbac("create_vessel_certificate", user_context)
    return await _delegate_to_cert_handler("create_vessel_certificate", db_client, payload, yacht_id, user_id, user_context)


async def create_crew_certificate(
    payload: dict,
    context: dict,
    yacht_id: str,
    user_id: str,
    user_context: dict,
    db_client: Client,
) -> dict:
    _enforce_cert_rbac("create_crew_certificate", user_context)
    return await _delegate_to_cert_handler("create_crew_certificate", db_client, payload, yacht_id, user_id, user_context)


async def update_certificate(
    payload: dict,
    context: dict,
    yacht_id: str,
    user_id: str,
    user_context: dict,
    db_client: Client,
) -> dict:
    _enforce_cert_rbac("update_certificate", user_context)
    return await _delegate_to_cert_handler("update_certificate", db_client, payload, yacht_id, user_id, user_context)


async def link_document_to_certificate(
    payload: dict,
    context: dict,
    yacht_id: str,
    user_id: str,
    user_context: dict,
    db_client: Client,
) -> dict:
    _enforce_cert_rbac("link_document_to_certificate", user_context)
    # Defensive validation: ensure document exists (from original L4944-4953)
    doc_id = payload.get("document_id")
    if not doc_id:
        raise HTTPException(status_code=400, detail="document_id is required")
    try:
        dm = db_client.table("doc_metadata").select("id").eq("id", doc_id).maybe_single().execute()
    except Exception:
        dm = None
    if not getattr(dm, 'data', None):
        raise HTTPException(status_code=404, detail="document_id not found")

    return await _delegate_to_cert_handler("link_document_to_certificate", db_client, payload, yacht_id, user_id, user_context)


async def supersede_certificate(
    payload: dict,
    context: dict,
    yacht_id: str,
    user_id: str,
    user_context: dict,
    db_client: Client,
) -> dict:
    _enforce_cert_rbac("supersede_certificate", user_context)
    # Signature required (from original L4957-4958)
    if not payload.get("signature"):
        raise HTTPException(status_code=400, detail="signature payload is required for supersede action")

    return await _delegate_to_cert_handler("supersede_certificate", db_client, payload, yacht_id, user_id, user_context)


# ============================================================================
# HELPERS
# ============================================================================

def _enforce_cert_rbac(action: str, user_context: dict) -> None:
    """Check RBAC for cert v2 actions. Raises HTTPException(403) if denied."""
    user_role = user_context.get("role", "")
    allowed_roles = _CERT_V2_ALLOWED_ROLES.get(action, [])
    if user_role not in allowed_roles:
        logger.warning(f"[RLS] Role '{user_role}' denied for action '{action}'. Allowed: {allowed_roles}")
        raise HTTPException(
            status_code=403,
            detail=f"Role '{user_role}' is not authorized to perform action '{action}'"
        )


# ============================================================================
# HANDLER REGISTRY
# ============================================================================
HANDLERS: dict = {
    # Blocked legacy actions (501)
    "add_certificate": add_certificate,
    "renew_certificate": renew_certificate,
    "add_service_contract": add_service_contract,
    "record_contract_claim": record_contract_claim,
    # Certificate Lens v2 actions (delegate)
    "create_vessel_certificate": create_vessel_certificate,
    "create_crew_certificate": create_crew_certificate,
    "update_certificate": update_certificate,
    "link_document_to_certificate": link_document_to_certificate,
    "supersede_certificate": supersede_certificate,
}
