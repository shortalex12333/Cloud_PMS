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

Dead duplicate removed: second /link/create function that existed in email.py
lines 2075-2174 was never reachable (FastAPI first-match wins) and lacked
idempotency + role checks. Deleted here, not ported.

The three separate email_links.insert() blocks in action/execute for
link_to_work_order / link_to_equipment / link_to_part have been consolidated
into a single upsert_email_link() call from email_link_service.py.
"""

import asyncio
import base64
import hashlib
import os
import uuid as _uuid_mod
import logging
from typing import Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from middleware.auth import get_authenticated_user
from integrations.supabase import get_tenant_client
from integrations.feature_flags import check_email_feature
from integrations.graph_client import (
    create_read_client,
    TokenNotFoundError,
    TokenExpiredError,
    TokenRevokedError,
)
from services.email_link_service import (
    VALID_LINK_OBJECT_TYPES,
    OBJECT_TYPE_TABLE_MAP,
    LINK_MANAGE_ROLES,
    EVIDENCE_SAVE_ROLES,
    audit_link_action,
    check_idempotency,
    upsert_email_link,
)
from services.email_graph_helpers import outlook_auth_error, sanitize_filename, utcnow

logger = logging.getLogger(__name__)

router = APIRouter(tags=["email"])

# ── Evidence upload security constants ───────────────────────────────────────
MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024  # 50MB

ALLOWED_EXTENSIONS = {
    '.pdf', '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff',
    '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
    '.txt', '.csv', '.rtf', '.odt', '.ods', '.odp',
}

ALLOWED_MIME_TYPES = {
    'application/pdf',
    'image/jpeg', 'image/png', 'image/gif', 'image/bmp', 'image/tiff',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'application/vnd.ms-excel',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'application/vnd.ms-powerpoint',
    'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    'text/plain', 'text/csv', 'application/rtf',
    'application/vnd.oasis.opendocument.text',
    'application/vnd.oasis.opendocument.spreadsheet',
    'application/vnd.oasis.opendocument.presentation',
}

# Trigger execution timeout (seconds)
TRIGGER_TIMEOUT_SECONDS = 5

_VALID_LINK_REASONS = ['token_match', 'vendor_domain', 'wo_pattern', 'po_pattern', 'serial_match', 'part_number', 'manual']

# ── Request models ────────────────────────────────────────────────────────────

class LinkAddRequest(BaseModel):
    thread_id: str = Field(..., description="UUID of the email thread to link")
    object_type: str = Field(..., description="Target type: work_order, equipment, part, fault, purchase_order, supplier")
    object_id: str = Field(..., description="UUID of the target object")
    reason: Optional[str] = Field(None, description="Reason for linking (token_match, vendor_domain, wo_pattern, po_pattern, serial_match, part_number, manual)")
    idempotency_key: Optional[str] = Field(None, description="Client-generated key for idempotency")


class LinkAcceptRequest(BaseModel):
    link_id: str = Field(..., description="UUID of the link to accept")
    idempotency_key: Optional[str] = Field(None, description="Client-generated key for idempotency")


class LinkChangeRequest(BaseModel):
    link_id: str = Field(..., description="UUID of the link to change")
    new_object_type: str = Field(..., description="New target type")
    new_object_id: str = Field(..., description="New target UUID")
    idempotency_key: Optional[str] = Field(None, description="Client-generated key for idempotency")


class LinkRemoveRequest(BaseModel):
    link_id: str = Field(..., description="UUID of the link to remove")
    idempotency_key: Optional[str] = Field(None, description="Client-generated key for idempotency")


class LinkRejectRequest(BaseModel):
    link_id: str = Field(..., description="UUID of the link to reject")


class SaveAttachmentRequest(BaseModel):
    message_id: str = Field(..., description="Provider message ID")
    attachment_id: str = Field(..., description="Provider attachment ID")
    target_folder: Optional[str] = Field(None, description="Target folder in documents")
    idempotency_key: Optional[str] = Field(None, description="Client-generated key for idempotency")


class ActionExecuteRequest(BaseModel):
    action_name: str = Field(..., description="Action to execute")
    message_id: Optional[str] = Field(None, description="Email message ID")
    thread_id: Optional[str] = Field(None, description="Email thread ID")
    target_type: Optional[str] = Field(None, description="Target entity type")
    target_id: Optional[str] = Field(None, description="Target entity ID")
    params: Dict[str, Any] = Field(default_factory=dict, description="Action parameters")
    idempotency_key: Optional[str] = Field(None, description="Idempotency key")


# ── Action permissions ────────────────────────────────────────────────────────

ACTION_PERMISSIONS = {
    'link_to_work_order':           ['chief_engineer', 'eto', 'captain', 'manager', 'member'],
    'link_to_equipment':            ['chief_engineer', 'eto', 'captain', 'manager', 'member'],
    'link_to_part':                 ['chief_engineer', 'eto', 'captain', 'manager', 'member'],
    'create_work_order_from_email': ['chief_engineer', 'eto', 'captain', 'manager'],
}


# ── POST /link/add  (+ /link/create alias — canonical endpoint) ───────────────

@router.post("/link/add")
@router.post("/link/create")
async def add_link(
    request: LinkAddRequest,
    auth: dict = Depends(get_authenticated_user),
):
    """
    Add a new email link to any target object (M8).

    Validates type, verifies thread + target exist, idempotent,
    full audit logging. /link/create is an alias for backwards compat.
    """
    enabled, error_msg = check_email_feature('link')
    if not enabled:
        raise HTTPException(status_code=503, detail=error_msg)

    yacht_id = auth['yacht_id']
    user_id = auth['user_id']
    user_role = auth.get('role', '')
    supabase = get_tenant_client(auth['tenant_key_alias'])

    if user_role not in LINK_MANAGE_ROLES:
        logger.warning(f"[email/link/add] Forbidden: role={user_role} user={user_id[:8]}")
        raise HTTPException(status_code=403, detail="Insufficient permissions to add links")

    if request.object_type not in VALID_LINK_OBJECT_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid object_type '{request.object_type}'. Must be one of: {VALID_LINK_OBJECT_TYPES}")

    reason = request.reason or 'manual'
    if reason not in _VALID_LINK_REASONS:
        raise HTTPException(status_code=400, detail=f"Invalid reason '{reason}'. Must be one of: {_VALID_LINK_REASONS}")

    try:
        if request.idempotency_key:
            cached = await check_idempotency(supabase, yacht_id, request.idempotency_key, 'EMAIL_LINK_ADD')
            if cached:
                return {'link_id': cached.get('link_id'), 'status': cached.get('status', 'created'), 'cached': True}

        thread_result = supabase.table('email_threads').select('id').eq(
            'id', request.thread_id
        ).eq('yacht_id', yacht_id).maybe_single().execute()

        if not thread_result.data:
            raise HTTPException(status_code=404, detail="Thread not found or access denied")

        target_table = OBJECT_TYPE_TABLE_MAP.get(request.object_type)
        if target_table:
            try:
                target_result = supabase.table(target_table).select('id').eq(
                    'id', request.object_id
                ).eq('yacht_id', yacht_id).maybe_single().execute()

                if not target_result.data:
                    raise HTTPException(
                        status_code=404,
                        detail=f"{request.object_type.replace('_', ' ').title()} not found or access denied"
                    )
            except HTTPException:
                raise
            except Exception as e:
                logger.warning(f"[email/link/add] Target check failed (non-fatal): {e}")

        existing_result = supabase.table('email_links').select('id').eq(
            'yacht_id', yacht_id
        ).eq('thread_id', request.thread_id).eq(
            'object_type', request.object_type
        ).eq('object_id', request.object_id).eq('is_active', True).limit(1).execute()

        if existing_result.data:
            existing_link_id = existing_result.data[0]['id']
            logger.info(f"[email/link/add] Already exists: link={existing_link_id[:8]}")
            await audit_link_action(
                supabase, yacht_id, user_id, 'EMAIL_LINK_ADD_DUPLICATE', existing_link_id,
                old_values={},
                new_values={'link_id': existing_link_id, 'status': 'already_exists',
                            'thread_id': request.thread_id, 'object_type': request.object_type, 'object_id': request.object_id},
                idempotency_key=request.idempotency_key,
                user_role=user_role,
            )
            return {'link_id': existing_link_id, 'status': 'already_exists'}

        insert_result = supabase.table('email_links').insert({
            'yacht_id': yacht_id,
            'thread_id': request.thread_id,
            'object_type': request.object_type,
            'object_id': request.object_id,
            'confidence': 'user_confirmed',
            'suggested_reason': reason,
            'suggested_at': utcnow(),
            'accepted_at': utcnow(),
            'accepted_by': user_id,
            'is_active': True,
        }).execute()

        new_link_id = insert_result.data[0]['id'] if insert_result.data else None
        if not new_link_id:
            raise HTTPException(status_code=500, detail="Failed to create link")

        await audit_link_action(
            supabase, yacht_id, user_id, 'EMAIL_LINK_ADD', new_link_id,
            old_values={},
            new_values={'link_id': new_link_id, 'status': 'created',
                        'thread_id': request.thread_id, 'object_type': request.object_type,
                        'object_id': request.object_id, 'reason': reason},
            idempotency_key=request.idempotency_key,
            user_role=user_role,
        )

        logger.info(
            f"[email/link/add] Created: link={new_link_id[:8]} "
            f"thread={request.thread_id[:8]} → {request.object_type}={request.object_id[:8]} "
            f"user={user_id[:8]} reason={reason}"
        )
        return {'link_id': new_link_id, 'status': 'created'}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[email/link/add] Error: {e}")
        raise HTTPException(status_code=500, detail="Failed to add link")


# ── POST /link/accept ─────────────────────────────────────────────────────────

@router.post("/link/accept")
async def accept_link(
    request: LinkAcceptRequest,
    auth: dict = Depends(get_authenticated_user),
):
    """Accept a suggested email link (changes confidence → user_confirmed)."""
    enabled, error_msg = check_email_feature('link')
    if not enabled:
        raise HTTPException(status_code=503, detail=error_msg)

    yacht_id = auth['yacht_id']
    user_id = auth['user_id']
    user_role = auth.get('role', '')
    supabase = get_tenant_client(auth['tenant_key_alias'])

    if user_role not in LINK_MANAGE_ROLES:
        raise HTTPException(status_code=403, detail="Insufficient permissions to accept links")

    try:
        if request.idempotency_key:
            cached = await check_idempotency(supabase, yacht_id, request.idempotency_key, 'EMAIL_LINK_ACCEPT')
            if cached:
                return {'success': True, 'link_id': request.link_id, 'cached': True}

        link_result = supabase.table('email_links').select('*').eq(
            'id', request.link_id
        ).eq('yacht_id', yacht_id).eq('is_active', True).maybe_single().execute()

        if not link_result.data:
            raise HTTPException(status_code=404, detail="Link not found")

        link = link_result.data

        if link['confidence'] == 'user_confirmed':
            return {'success': True, 'link_id': request.link_id, 'already_accepted': True}

        if link['confidence'] != 'suggested':
            raise HTTPException(status_code=400, detail="Link is not in suggested state")

        supabase.table('email_links').update({
            'confidence': 'user_confirmed',
            'accepted_at': utcnow(),
            'accepted_by': user_id,
            'updated_at': utcnow(),
        }).eq('id', request.link_id).eq('yacht_id', yacht_id).execute()

        await audit_link_action(
            supabase, yacht_id, user_id, 'EMAIL_LINK_ACCEPT', request.link_id,
            old_values={'confidence': 'suggested'},
            new_values={'confidence': 'user_confirmed'},
            idempotency_key=request.idempotency_key,
            user_role=user_role,
        )

        return {'success': True, 'link_id': request.link_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[email/link/accept] Error: {e}")
        raise HTTPException(status_code=500, detail="Failed to accept link")


# ── POST /link/change ─────────────────────────────────────────────────────────

@router.post("/link/change")
async def change_link(
    request: LinkChangeRequest,
    auth: dict = Depends(get_authenticated_user),
):
    """Change a link's target object."""
    enabled, error_msg = check_email_feature('link')
    if not enabled:
        raise HTTPException(status_code=503, detail=error_msg)

    yacht_id = auth['yacht_id']
    user_id = auth['user_id']
    user_role = auth.get('role', '')
    supabase = get_tenant_client(auth['tenant_key_alias'])

    if user_role not in LINK_MANAGE_ROLES:
        raise HTTPException(status_code=403, detail="Insufficient permissions to change links")

    if request.new_object_type not in VALID_LINK_OBJECT_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid object_type. Must be one of: {VALID_LINK_OBJECT_TYPES}")

    try:
        if request.idempotency_key:
            cached = await check_idempotency(supabase, yacht_id, request.idempotency_key, 'EMAIL_LINK_CHANGE')
            if cached:
                return {'success': True, 'link_id': request.link_id, 'cached': True}

        link_result = supabase.table('email_links').select('*').eq(
            'id', request.link_id
        ).eq('yacht_id', yacht_id).eq('is_active', True).maybe_single().execute()

        if not link_result.data:
            raise HTTPException(status_code=404, detail="Link not found")

        old_link = link_result.data

        if old_link['object_type'] == request.new_object_type and old_link['object_id'] == request.new_object_id:
            return {'success': True, 'link_id': request.link_id, 'no_change': True}

        supabase.table('email_links').update({
            'object_type': request.new_object_type,
            'object_id': request.new_object_id,
            'confidence': 'user_confirmed',
            'modified_at': utcnow(),
            'modified_by': user_id,
            'updated_at': utcnow(),
        }).eq('id', request.link_id).eq('yacht_id', yacht_id).execute()

        await audit_link_action(
            supabase, yacht_id, user_id, 'EMAIL_LINK_CHANGE', request.link_id,
            old_values={'object_type': old_link['object_type'], 'object_id': old_link['object_id']},
            new_values={'object_type': request.new_object_type, 'object_id': request.new_object_id},
            idempotency_key=request.idempotency_key,
            user_role=user_role,
        )

        return {'success': True, 'link_id': request.link_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[email/link/change] Error: {e}")
        raise HTTPException(status_code=500, detail="Failed to change link")


# ── POST /link/remove ─────────────────────────────────────────────────────────

@router.post("/link/remove")
async def remove_link(
    request: LinkRemoveRequest,
    auth: dict = Depends(get_authenticated_user),
):
    """Soft-delete a link (is_active=False). Audited."""
    enabled, error_msg = check_email_feature('link')
    if not enabled:
        raise HTTPException(status_code=503, detail=error_msg)

    yacht_id = auth['yacht_id']
    user_id = auth['user_id']
    user_role = auth.get('role', '')
    supabase = get_tenant_client(auth['tenant_key_alias'])

    if user_role not in LINK_MANAGE_ROLES:
        raise HTTPException(status_code=403, detail="Insufficient permissions to remove links")

    try:
        if request.idempotency_key:
            cached = await check_idempotency(supabase, yacht_id, request.idempotency_key, 'EMAIL_LINK_REMOVE')
            if cached:
                return {'success': True, 'link_id': request.link_id, 'cached': True}

        link_result = supabase.table('email_links').select('*').eq(
            'id', request.link_id
        ).eq('yacht_id', yacht_id).maybe_single().execute()

        if not link_result.data:
            raise HTTPException(status_code=404, detail="Link not found")

        old_link = link_result.data

        if not old_link.get('is_active', True):
            return {'success': True, 'link_id': request.link_id, 'already_removed': True}

        supabase.table('email_links').update({
            'is_active': False,
            'removed_at': utcnow(),
            'removed_by': user_id,
            'updated_at': utcnow(),
        }).eq('id', request.link_id).eq('yacht_id', yacht_id).execute()

        await audit_link_action(
            supabase, yacht_id, user_id, 'EMAIL_LINK_REMOVE', request.link_id,
            old_values={'is_active': True, 'thread_id': old_link['thread_id'],
                        'object_type': old_link['object_type'], 'object_id': old_link['object_id']},
            new_values={'is_active': False},
            idempotency_key=request.idempotency_key,
            user_role=user_role,
        )

        return {'success': True, 'link_id': request.link_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[email/link/remove] Error: {e}")
        raise HTTPException(status_code=500, detail="Failed to remove link")


# ── POST /link/reject ─────────────────────────────────────────────────────────

@router.post("/link/reject")
async def reject_link(
    request: LinkRejectRequest,
    auth: dict = Depends(get_authenticated_user),
):
    """Reject a suggested link (confidence → rejected)."""
    enabled, error_msg = check_email_feature('link')
    if not enabled:
        raise HTTPException(status_code=503, detail=error_msg)

    yacht_id = auth['yacht_id']
    user_id = auth['user_id']
    supabase = get_tenant_client(auth['tenant_key_alias'])

    try:
        link_result = supabase.table('email_links').select('*').eq(
            'id', request.link_id
        ).eq('yacht_id', yacht_id).eq('is_active', True).maybe_single().execute()

        if not link_result.data:
            raise HTTPException(status_code=404, detail="Link not found")

        link = link_result.data

        if link['confidence'] != 'suggested':
            raise HTTPException(status_code=400, detail="Only suggested links can be rejected")

        supabase.table('email_links').update({
            'confidence': 'rejected',
            'rejected_at': utcnow(),
            'rejected_by': user_id,
            'updated_at': utcnow(),
        }).eq('id', request.link_id).eq('yacht_id', yacht_id).execute()

        await audit_link_action(
            supabase, yacht_id, user_id, 'EMAIL_LINK_REJECT', request.link_id,
            old_values={'confidence': 'suggested'},
            new_values={'confidence': 'rejected'},
        )

        return {'success': True, 'link_id': request.link_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[email/link/reject] Error: {e}")
        raise HTTPException(status_code=500, detail="Failed to reject link")


# ── POST /action/execute ──────────────────────────────────────────────────────

@router.post("/action/execute")
async def execute_action(
    request: ActionExecuteRequest,
    auth: dict = Depends(get_authenticated_user),
):
    """
    Execute a micro-action and fire associated triggers (M5).

    Execution order (Audit-First):
    1. Feature flag  2. Permission  3. Idempotency  4. Preconditions
    5. Mutation      6. Audit log   7. Trigger dispatch (timeout-bounded)

    link_to_* actions use upsert_email_link() — single code path,
    no duplicate insert blocks.
    """
    enabled, error_msg = check_email_feature('focus')
    if not enabled:
        raise HTTPException(status_code=503, detail=error_msg)

    yacht_id = auth['yacht_id']
    user_id = auth['user_id']
    user_role = auth.get('role', '')
    supabase = get_tenant_client(auth['tenant_key_alias'])
    action_audit_id = str(_uuid_mod.uuid4())

    allowed_roles = ACTION_PERMISSIONS.get(request.action_name)
    if allowed_roles is None:
        raise HTTPException(status_code=400, detail=f"Unknown action: {request.action_name}")

    if user_role not in allowed_roles:
        raise HTTPException(
            status_code=403,
            detail=f"Role '{user_role}' cannot execute action '{request.action_name}'"
        )

    if request.idempotency_key:
        cached = await check_idempotency(supabase, yacht_id, request.idempotency_key, request.action_name)
        if cached:
            cached_result = cached.get('result', {})
            logger.info(f"[email/action/execute] Idempotent return for key={request.idempotency_key[:16]}")
            return {
                'success': cached_result.get('success', True),
                'action_name': request.action_name,
                'result': cached_result,
                'cached': True,
                'trigger': None,
            }

    precondition_errors = []

    if request.action_name in ('link_to_work_order', 'link_to_equipment', 'link_to_part'):
        if not request.thread_id:
            precondition_errors.append("thread_id is required")
        if not request.target_id:
            precondition_errors.append("target_id is required")

        if request.thread_id:
            thread_check = supabase.table('email_threads').select('id').eq(
                'id', request.thread_id
            ).eq('yacht_id', yacht_id).maybe_single().execute()
            if not thread_check.data:
                precondition_errors.append("Thread not found or access denied")

        if request.thread_id and request.target_id:
            existing_link = supabase.table('email_links').select('id').eq(
                'yacht_id', yacht_id
            ).eq('thread_id', request.thread_id).eq(
                'object_id', request.target_id
            ).eq('is_active', True).limit(1).execute()

            if existing_link.data:
                return {
                    'success': True,
                    'action_name': request.action_name,
                    'result': {'link_id': existing_link.data[0]['id'], 'already_linked': True},
                    'trigger': None,
                }

    elif request.action_name == 'create_work_order_from_email':
        if not request.params.get('title'):
            precondition_errors.append("title is required in params")

    if precondition_errors:
        raise HTTPException(status_code=400, detail="; ".join(precondition_errors))

    from email_rag.triggers import TriggerContext, dispatch_trigger, apply_trigger_effects

    try:
        action_result: Dict[str, Any] = {'success': False, 'error': 'Unknown action'}

        if request.action_name in ('link_to_work_order', 'link_to_equipment', 'link_to_part'):
            object_type_map = {
                'link_to_work_order': 'work_order',
                'link_to_equipment': 'equipment',
                'link_to_part': 'part',
            }
            object_type = object_type_map[request.action_name]

            upsert = await upsert_email_link(
                supabase,
                yacht_id=yacht_id,
                thread_id=request.thread_id,
                object_type=object_type,
                object_id=request.target_id,
                user_id=user_id,
                confidence='user_confirmed',
                suggested_reason='manual',
            )
            action_result = {'success': True, 'link_id': upsert.get('link_id')}

        elif request.action_name == 'create_work_order_from_email':
            title = request.params.get('title', 'Work Order from Email')
            priority = request.params.get('priority', 'medium')
            equipment_id = request.params.get('equipment_id')

            wo_insert = supabase.table('pms_work_orders').insert({
                'yacht_id': yacht_id,
                'title': title,
                'priority': priority,
                'equipment_id': equipment_id,
                'status': 'open',
                'source': 'email',
                'source_reference': request.message_id,
                'created_by': user_id,
            }).execute()

            action_result = {
                'success': True,
                'work_order_id': wo_insert.data[0]['id'] if wo_insert.data else None,
            }

        else:
            raise HTTPException(status_code=400, detail=f"Unknown action: {request.action_name}")

        # Audit BEFORE trigger dispatch
        supabase.table('pms_audit_log').insert({
            'yacht_id': yacht_id,
            'action': f'EMAIL_ACTION_{request.action_name.upper()}',
            'entity_type': 'email_action',
            'entity_id': request.message_id or request.thread_id or 'unknown',
            'user_id': user_id,
            'old_values': {},
            'new_values': {
                'action_name': request.action_name,
                'target_type': request.target_type,
                'target_id': request.target_id,
                'result': action_result,
            },
            'signature': {
                'timestamp': utcnow(),
                'action_version': 'M5',
                'action_audit_id': action_audit_id,
                'user_role': user_role,
                'idempotency_key': request.idempotency_key,
            },
        }).execute()

        logger.info(f"[email/action/execute] Audited: {request.action_name} audit_id={action_audit_id[:8]}")

        trigger_result = None
        trigger_error = None

        if action_result.get('success'):
            ctx = TriggerContext(
                yacht_id=yacht_id,
                user_id=user_id,
                user_role=user_role,
                action_name=request.action_name,
                action_id=action_audit_id,
                message_id=request.message_id,
                thread_id=request.thread_id,
                target_type=request.target_type or 'work_order',
                target_id=request.target_id,
                success=True,
                result_data=action_result,
            )
            try:
                trigger_result = dispatch_trigger(ctx)
                if trigger_result and trigger_result.executed:
                    effects_summary = await asyncio.wait_for(
                        apply_trigger_effects(supabase, trigger_result),
                        timeout=TRIGGER_TIMEOUT_SECONDS,
                    )
                    logger.info(f"[email/action/execute] Trigger effects applied: {effects_summary}")
            except asyncio.TimeoutError:
                trigger_error = "Trigger execution timed out"
                logger.error(f"[email/action/execute] Trigger timeout for {request.action_name}")
                try:
                    supabase.table('pms_audit_log').insert({
                        'yacht_id': yacht_id, 'action': 'TRIGGER_DLQ',
                        'entity_type': 'trigger_failure', 'entity_id': action_audit_id,
                        'user_id': user_id, 'old_values': {},
                        'new_values': {'action_name': request.action_name, 'error': trigger_error},
                        'signature': {'timestamp': utcnow()},
                    }).execute()
                except Exception:
                    pass
            except Exception as te:
                trigger_error = str(te)
                logger.error(f"[email/action/execute] Trigger error: {te}")

        resp = {
            'success': action_result.get('success', False),
            'action_name': request.action_name,
            'action_audit_id': action_audit_id,
            'result': action_result,
            'trigger': trigger_result.to_dict() if trigger_result else None,
        }
        if trigger_error:
            resp['trigger_error'] = trigger_error
        return resp

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[email/action/execute] Error: {e}")
        raise HTTPException(status_code=500, detail=f"Action execution failed: {e}")


# ── POST /evidence/save-attachment ────────────────────────────────────────────

@router.post("/evidence/save-attachment")
async def save_attachment(
    request: SaveAttachmentRequest,
    auth: dict = Depends(get_authenticated_user),
):
    """
    Save an email attachment to documents storage (M4).
    Role-gated, size+MIME enforced, idempotent, audited.
    Uses READ token for Graph access.
    """
    enabled, error_msg = check_email_feature('evidence')
    if not enabled:
        raise HTTPException(status_code=503, detail=error_msg)

    yacht_id = auth['yacht_id']
    user_id = auth['user_id']
    user_role = auth.get('role', '')
    supabase = get_tenant_client(auth['tenant_key_alias'])

    if user_role not in EVIDENCE_SAVE_ROLES:
        raise HTTPException(status_code=403, detail="Insufficient permissions to save attachments")

    msg_hash = hashlib.md5(request.message_id.encode()).hexdigest()[:12]
    att_hash = hashlib.md5(request.attachment_id.encode()).hexdigest()[:12]
    path_prefix = f"{yacht_id}/email-attachments/{msg_hash}_{att_hash}"

    if request.idempotency_key:
        existing = supabase.table('doc_yacht_library').select('id, document_path').eq(
            'yacht_id', yacht_id
        ).like('document_path', f'{path_prefix}%').limit(1).execute()

        if existing.data:
            return {
                'success': True,
                'document_id': existing.data[0]['id'],
                'storage_path': existing.data[0]['document_path'],
                'already_saved': True,
            }

    msg_result = supabase.table('email_messages').select('id, thread_id').eq(
        'provider_message_id', request.message_id
    ).eq('yacht_id', yacht_id).maybe_single().execute()

    if not msg_result.data:
        raise HTTPException(status_code=404, detail="Message not found")

    try:
        read_client = create_read_client(supabase, user_id, yacht_id)
        attachment = await read_client.get_attachment(request.message_id, request.attachment_id)

        if not attachment:
            raise HTTPException(status_code=404, detail="Attachment not found")

        content_bytes = attachment.get('contentBytes')
        if not content_bytes:
            raise HTTPException(status_code=400, detail="Attachment has no content")

        file_data = base64.b64decode(content_bytes)

        if len(file_data) > MAX_FILE_SIZE_BYTES:
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Maximum size is {MAX_FILE_SIZE_BYTES // (1024*1024)}MB"
            )

        original_filename = sanitize_filename(attachment.get('name', 'attachment'))
        _, ext = os.path.splitext(original_filename)
        ext = ext.lower()

        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"File type '{ext}' not allowed. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
            )

        content_type = attachment.get('contentType', 'application/octet-stream')
        if content_type not in ALLOWED_MIME_TYPES:
            raise HTTPException(status_code=400, detail=f"Content type '{content_type}' not allowed")

        safe_filename = f"{_uuid_mod.uuid4()}{ext}"
        storage_path = f"{path_prefix}/{safe_filename}"

        supabase.storage.from_('documents').upload(
            storage_path, file_data, {'content-type': content_type}
        )

        doc_result = supabase.table('doc_yacht_library').insert({
            'yacht_id': yacht_id,
            'document_name': original_filename,
            'document_path': storage_path,
            'document_type': content_type,
            'user_id': user_id,
        }).execute()
        document_id = doc_result.data[0]['id'] if doc_result.data else None

        try:
            supabase.table('pms_audit_log').insert({
                'yacht_id': yacht_id,
                'action': 'EMAIL_EVIDENCE_SAVED',
                'entity_type': 'document',
                'entity_id': document_id,
                'user_id': user_id,
                'old_values': {},
                'new_values': {
                    'filename': original_filename,
                    'content_type': content_type,
                    'file_size': len(file_data),
                    'email_message_id': request.message_id,
                },
                'signature': {
                    'timestamp': utcnow(),
                    'action_version': 'M4',
                    'user_role': user_role,
                    'idempotency_key': request.idempotency_key,
                },
            }).execute()
        except Exception as audit_error:
            logger.error(f"[email/evidence/save-attachment] Audit log failed: {audit_error}")

        logger.info(
            f"[email/evidence/save-attachment] Saved: doc={document_id[:8] if document_id else 'N/A'} "
            f"size={len(file_data)} type={content_type} user={user_id[:8]}"
        )

        auto_linked_objects = []
        if document_id and msg_result.data.get('thread_id'):
            thread_id = msg_result.data['thread_id']
            try:
                thread_links = supabase.table('email_links').select('object_type, object_id').eq(
                    'yacht_id', yacht_id
                ).eq('thread_id', thread_id).eq('is_active', True).in_(
                    'confidence', ['deterministic', 'user_confirmed']
                ).execute()

                for link in (thread_links.data or []):
                    try:
                        supabase.table('email_attachment_object_links').insert({
                            'yacht_id': yacht_id,
                            'document_id': document_id,
                            'object_type': link['object_type'],
                            'object_id': link['object_id'],
                            'link_reason': 'auto_from_thread',
                            'source_context': {
                                'email_thread_id': thread_id,
                                'email_message_id': request.message_id,
                            },
                            'is_active': True,
                            'created_by': user_id,
                        }).execute()
                        auto_linked_objects.append({'object_type': link['object_type'], 'object_id': link['object_id']})
                    except Exception as link_error:
                        logger.warning(f"[email/evidence/save-attachment] Auto-link skipped: {link_error}")
            except Exception as auto_link_error:
                logger.warning(f"[email/evidence/save-attachment] Auto-link lookup failed: {auto_link_error}")

        return {
            'success': True,
            'document_id': document_id,
            'storage_path': storage_path,
            'auto_linked': auto_linked_objects if auto_linked_objects else None,
        }

    except TokenNotFoundError:
        raise outlook_auth_error("outlook_not_connected", "Email not connected")
    except TokenExpiredError:
        raise outlook_auth_error("outlook_token_expired", "Email connection expired")
    except TokenRevokedError:
        raise outlook_auth_error("outlook_token_revoked", "Email connection revoked")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[email/evidence/save-attachment] Error: {e}")
        raise HTTPException(status_code=500, detail="Failed to save attachment")
