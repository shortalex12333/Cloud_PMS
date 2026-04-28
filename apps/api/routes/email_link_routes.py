"""
Email Link Routes
=================
POST /email/link/add     (+ /link/create alias — canonical)
POST /email/link/accept
POST /email/link/change
POST /email/link/remove
POST /email/link/reject
POST /email/action/execute
POST /email/evidence/save-attachment
"""
import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from middleware.auth import get_authenticated_user
from integrations.supabase import get_tenant_client
from integrations.feature_flags import check_email_feature
from services.email_link_service import VALID_LINK_OBJECT_TYPES
from handlers.email_handlers import ACTION_PERMISSIONS, EVIDENCE_SAVE_ROLES, LINK_MANAGE_ROLES
import handlers.email_handlers as email_handlers

logger = logging.getLogger(__name__)

router = APIRouter(tags=["email"])

_VALID_LINK_REASONS = [
    'token_match', 'vendor_domain', 'wo_pattern', 'po_pattern',
    'serial_match', 'part_number', 'manual',
]


class LinkAddRequest(BaseModel):
    thread_id: str = Field(..., description="UUID of the email thread to link")
    object_type: str = Field(..., description="Target type: work_order, equipment, part, fault, purchase_order, supplier")
    object_id: str = Field(..., description="UUID of the target object")
    reason: Optional[str] = Field(None)
    idempotency_key: Optional[str] = Field(None)


class LinkAcceptRequest(BaseModel):
    link_id: str = Field(..., description="UUID of the link to accept")
    idempotency_key: Optional[str] = Field(None)


class LinkChangeRequest(BaseModel):
    link_id: str = Field(..., description="UUID of the link to change")
    new_object_type: str = Field(...)
    new_object_id: str = Field(...)
    idempotency_key: Optional[str] = Field(None)


class LinkRemoveRequest(BaseModel):
    link_id: str = Field(..., description="UUID of the link to remove")
    idempotency_key: Optional[str] = Field(None)


class LinkRejectRequest(BaseModel):
    link_id: str = Field(..., description="UUID of the link to reject")


class SaveAttachmentRequest(BaseModel):
    message_id: str = Field(..., description="Provider message ID")
    attachment_id: str = Field(..., description="Provider attachment ID")
    target_folder: Optional[str] = Field(None)
    idempotency_key: Optional[str] = Field(None)


class ActionExecuteRequest(BaseModel):
    action_name: str = Field(...)
    message_id: Optional[str] = Field(None)
    thread_id: Optional[str] = Field(None)
    target_type: Optional[str] = Field(None)
    target_id: Optional[str] = Field(None)
    params: Dict[str, Any] = Field(default_factory=dict)
    idempotency_key: Optional[str] = Field(None)


@router.post("/link/add")
@router.post("/link/create")
async def add_link(request: LinkAddRequest, auth: dict = Depends(get_authenticated_user)):
    enabled, error_msg = check_email_feature('link')
    if not enabled:
        raise HTTPException(status_code=503, detail=error_msg)
    user_role = auth.get('role', '')
    if user_role not in LINK_MANAGE_ROLES:
        raise HTTPException(status_code=403, detail="Insufficient permissions to add links")
    if request.object_type not in VALID_LINK_OBJECT_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid object_type '{request.object_type}'. Must be one of: {VALID_LINK_OBJECT_TYPES}")
    reason = request.reason or 'manual'
    if reason not in _VALID_LINK_REASONS:
        raise HTTPException(status_code=400, detail=f"Invalid reason '{reason}'. Must be one of: {_VALID_LINK_REASONS}")
    supabase = get_tenant_client(auth['tenant_key_alias'])
    return await email_handlers.add_link(
        supabase=supabase, yacht_id=auth['yacht_id'], user_id=auth['user_id'], user_role=user_role,
        thread_id=request.thread_id, object_type=request.object_type, object_id=request.object_id,
        reason=reason, idempotency_key=request.idempotency_key,
    )


@router.post("/link/accept")
async def accept_link(request: LinkAcceptRequest, auth: dict = Depends(get_authenticated_user)):
    enabled, error_msg = check_email_feature('link')
    if not enabled:
        raise HTTPException(status_code=503, detail=error_msg)
    user_role = auth.get('role', '')
    if user_role not in LINK_MANAGE_ROLES:
        raise HTTPException(status_code=403, detail="Insufficient permissions to accept links")
    supabase = get_tenant_client(auth['tenant_key_alias'])
    return await email_handlers.accept_link(
        supabase=supabase, yacht_id=auth['yacht_id'], user_id=auth['user_id'], user_role=user_role,
        link_id=request.link_id, idempotency_key=request.idempotency_key,
    )


@router.post("/link/change")
async def change_link(request: LinkChangeRequest, auth: dict = Depends(get_authenticated_user)):
    enabled, error_msg = check_email_feature('link')
    if not enabled:
        raise HTTPException(status_code=503, detail=error_msg)
    user_role = auth.get('role', '')
    if user_role not in LINK_MANAGE_ROLES:
        raise HTTPException(status_code=403, detail="Insufficient permissions to change links")
    supabase = get_tenant_client(auth['tenant_key_alias'])
    return await email_handlers.change_link(
        supabase=supabase, yacht_id=auth['yacht_id'], user_id=auth['user_id'], user_role=user_role,
        link_id=request.link_id, new_object_type=request.new_object_type,
        new_object_id=request.new_object_id, idempotency_key=request.idempotency_key,
    )


@router.post("/link/remove")
async def remove_link(request: LinkRemoveRequest, auth: dict = Depends(get_authenticated_user)):
    enabled, error_msg = check_email_feature('link')
    if not enabled:
        raise HTTPException(status_code=503, detail=error_msg)
    user_role = auth.get('role', '')
    if user_role not in LINK_MANAGE_ROLES:
        raise HTTPException(status_code=403, detail="Insufficient permissions to remove links")
    supabase = get_tenant_client(auth['tenant_key_alias'])
    return await email_handlers.remove_link(
        supabase=supabase, yacht_id=auth['yacht_id'], user_id=auth['user_id'], user_role=user_role,
        link_id=request.link_id, idempotency_key=request.idempotency_key,
    )


@router.post("/link/reject")
async def reject_link(request: LinkRejectRequest, auth: dict = Depends(get_authenticated_user)):
    enabled, error_msg = check_email_feature('link')
    if not enabled:
        raise HTTPException(status_code=503, detail=error_msg)
    supabase = get_tenant_client(auth['tenant_key_alias'])
    return await email_handlers.reject_link(
        supabase=supabase, yacht_id=auth['yacht_id'], user_id=auth['user_id'],
        link_id=request.link_id,
    )


@router.post("/action/execute")
async def execute_action(request: ActionExecuteRequest, auth: dict = Depends(get_authenticated_user)):
    enabled, error_msg = check_email_feature('focus')
    if not enabled:
        raise HTTPException(status_code=503, detail=error_msg)
    user_role = auth.get('role', '')
    allowed_roles = ACTION_PERMISSIONS.get(request.action_name)
    if allowed_roles is None:
        raise HTTPException(status_code=400, detail=f"Unknown action: {request.action_name}")
    if user_role not in allowed_roles:
        raise HTTPException(status_code=403, detail=f"Role '{user_role}' cannot execute action '{request.action_name}'")
    supabase = get_tenant_client(auth['tenant_key_alias'])
    return await email_handlers.execute_action(
        supabase=supabase, yacht_id=auth['yacht_id'], user_id=auth['user_id'], user_role=user_role,
        action_name=request.action_name, message_id=request.message_id, thread_id=request.thread_id,
        target_type=request.target_type, target_id=request.target_id,
        params=request.params, idempotency_key=request.idempotency_key,
    )


@router.post("/evidence/save-attachment")
async def save_attachment(request: SaveAttachmentRequest, auth: dict = Depends(get_authenticated_user)):
    enabled, error_msg = check_email_feature('evidence')
    if not enabled:
        raise HTTPException(status_code=503, detail=error_msg)
    user_role = auth.get('role', '')
    if user_role not in EVIDENCE_SAVE_ROLES:
        raise HTTPException(status_code=403, detail="Insufficient permissions to save attachments")
    supabase = get_tenant_client(auth['tenant_key_alias'])
    return await email_handlers.save_attachment(
        supabase=supabase, user_id=auth['user_id'], yacht_id=auth['yacht_id'], user_role=user_role,
        message_id=request.message_id, attachment_id=request.attachment_id,
        target_folder=request.target_folder, idempotency_key=request.idempotency_key,
    )
