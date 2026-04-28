"""
Email Inbox Routes
==================
GET /email/search
GET /email/inbox
GET /email/related
GET /email/focus/{message_id}
GET /email/search-objects
GET /email/unread-count
GET /email/worker/status
"""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from middleware.auth import get_authenticated_user
from integrations.supabase import get_tenant_client
from integrations.feature_flags import check_email_feature
from services.email_link_service import VALID_LINK_OBJECT_TYPES
import handlers.email_handlers as email_handlers

logger = logging.getLogger(__name__)

router = APIRouter(tags=["email"])


@router.get("/search")
async def search_emails(
    q: str,
    limit: int = 20,
    threshold: float = 0.3,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    boost_recency: bool = True,
    boost_affinity: bool = True,
    boost_linkage: bool = True,
    auth: dict = Depends(get_authenticated_user),
):
    enabled, error_msg = check_email_feature('search')
    if not enabled:
        raise HTTPException(status_code=503, detail=error_msg)
    if not q or not q.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    supabase = get_tenant_client(auth['tenant_key_alias'])
    return await email_handlers.search_emails(
        supabase=supabase, yacht_id=auth['yacht_id'], user_id=auth['user_id'],
        user_email=auth.get('email', ''), q=q, limit=limit, threshold=threshold,
        date_from=date_from, date_to=date_to,
        boost_recency=boost_recency, boost_affinity=boost_affinity, boost_linkage=boost_linkage,
    )


@router.get("/inbox")
async def get_inbox_threads(
    page: int = 1,
    page_size: int = 20,
    linked: bool = False,
    q: Optional[str] = None,
    direction: Optional[str] = None,
    auth: dict = Depends(get_authenticated_user),
):
    enabled, error_msg = check_email_feature('related')
    if not enabled:
        raise HTTPException(status_code=503, detail=error_msg)
    supabase = get_tenant_client(auth['tenant_key_alias'])
    return await email_handlers.get_inbox_threads(
        supabase=supabase, yacht_id=auth['yacht_id'], user_id=auth['user_id'],
        page=page, page_size=page_size, linked=linked, q=q, direction=direction,
    )


@router.get("/related")
async def get_related_threads(
    object_type: str,
    object_id: str,
    auth: dict = Depends(get_authenticated_user),
):
    enabled, error_msg = check_email_feature('related')
    if not enabled:
        raise HTTPException(status_code=503, detail=error_msg)
    if object_type not in VALID_LINK_OBJECT_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid object_type. Must be one of: {VALID_LINK_OBJECT_TYPES}")
    supabase = get_tenant_client(auth['tenant_key_alias'])
    return await email_handlers.get_related_threads(
        supabase=supabase, yacht_id=auth['yacht_id'],
        object_type=object_type, object_id=object_id,
    )


@router.get("/focus/{message_id}")
async def get_message_focus(message_id: str, auth: dict = Depends(get_authenticated_user)):
    enabled, error_msg = check_email_feature('focus')
    if not enabled:
        raise HTTPException(status_code=503, detail=error_msg)
    supabase = get_tenant_client(auth['tenant_key_alias'])
    return await email_handlers.get_message_focus(
        supabase=supabase, yacht_id=auth['yacht_id'], user_role=auth.get('role', 'member'),
        message_id=message_id,
    )


@router.get("/search-objects")
async def search_linkable_objects(
    q: str,
    types: str = "work_order,equipment,part",
    limit: int = 10,
    auth: dict = Depends(get_authenticated_user),
):
    enabled, error_msg = check_email_feature('link')
    if not enabled:
        raise HTTPException(status_code=503, detail=error_msg)
    if len(q) < 2:
        return {'results': []}
    type_list = [t.strip() for t in types.split(',')]
    supabase = get_tenant_client(auth['tenant_key_alias'])
    return await email_handlers.search_linkable_objects(
        supabase=supabase, yacht_id=auth['yacht_id'], q=q, type_list=type_list, limit=limit,
    )


@router.get("/unread-count")
async def get_unread_count(auth: dict = Depends(get_authenticated_user)):
    supabase = get_tenant_client(auth['tenant_key_alias'])
    return await email_handlers.get_unread_count(
        supabase=supabase, user_id=auth['user_id'], yacht_id=auth['yacht_id'],
    )


@router.get("/worker/status")
async def get_worker_status(auth: dict = Depends(get_authenticated_user)):
    supabase = get_tenant_client(auth['tenant_key_alias'])
    return await email_handlers.get_worker_status(
        supabase=supabase, user_id=auth['user_id'], yacht_id=auth['yacht_id'],
    )
