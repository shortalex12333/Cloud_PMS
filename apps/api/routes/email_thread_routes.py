"""
Email Thread Routes
===================
GET  /email/thread/{thread_id}
POST /email/thread/{thread_id}/mark-read
GET  /email/message/{provider_message_id}/render
GET  /email/message/{message_id}/attachments
GET  /email/message/{provider_message_id}/attachments/{attachment_id}/download
GET  /email/thread/{thread_id}/links
"""
import uuid as _uuid
import logging

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import StreamingResponse

from middleware.auth import get_authenticated_user
from integrations.supabase import get_tenant_client
from integrations.feature_flags import check_email_feature
import handlers.email_handlers as email_handlers

logger = logging.getLogger(__name__)

router = APIRouter(tags=["email"])


@router.get("/thread/{thread_id}")
async def get_thread(thread_id: str, auth: dict = Depends(get_authenticated_user)):
    enabled, error_msg = check_email_feature('thread')
    if not enabled:
        raise HTTPException(status_code=503, detail=error_msg)
    try:
        _uuid.UUID(thread_id)
    except (ValueError, TypeError):
        raise HTTPException(status_code=404, detail={
            "code": "thread_not_found", "message": "Invalid thread ID format",
            "thread_id": thread_id, "yacht_id": auth['yacht_id'],
        })
    supabase = get_tenant_client(auth['tenant_key_alias'])
    return await email_handlers.get_thread(
        supabase=supabase, yacht_id=auth['yacht_id'], user_id=auth['user_id'], thread_id=thread_id,
    )


@router.post("/thread/{thread_id}/mark-read")
async def mark_thread_read(thread_id: str, auth: dict = Depends(get_authenticated_user)):
    enabled, error_msg = check_email_feature('thread')
    if not enabled:
        raise HTTPException(status_code=503, detail=error_msg)
    try:
        _uuid.UUID(thread_id)
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Invalid thread ID format")
    supabase = get_tenant_client(auth['tenant_key_alias'])
    return await email_handlers.mark_thread_read(
        supabase=supabase, yacht_id=auth['yacht_id'], thread_id=thread_id,
    )


@router.get("/message/{provider_message_id}/render")
async def render_message(
    provider_message_id: str,
    response: Response,
    auth: dict = Depends(get_authenticated_user),
):
    enabled, error_msg = check_email_feature('render')
    if not enabled:
        raise HTTPException(status_code=503, detail=error_msg)
    supabase = get_tenant_client(auth['tenant_key_alias'])
    data, cache_status, elapsed_ms = await email_handlers.render_message(
        supabase=supabase, user_id=auth['user_id'], yacht_id=auth['yacht_id'],
        provider_message_id=provider_message_id,
    )
    response.headers.update({"X-Graph-Cache": cache_status, "X-Graph-Time": str(elapsed_ms)})
    return data


@router.get("/message/{message_id}/attachments")
async def list_message_attachments(message_id: str, auth: dict = Depends(get_authenticated_user)):
    enabled, error_msg = check_email_feature('render')
    if not enabled:
        raise HTTPException(status_code=503, detail=error_msg)
    supabase = get_tenant_client(auth['tenant_key_alias'])
    return await email_handlers.list_message_attachments(
        supabase=supabase, yacht_id=auth['yacht_id'], message_id=message_id,
    )


@router.get("/message/{provider_message_id}/attachments/{attachment_id}/download")
async def download_attachment(
    provider_message_id: str,
    attachment_id: str,
    inline: bool = False,
    auth: dict = Depends(get_authenticated_user),
):
    enabled, error_msg = check_email_feature('render')
    if not enabled:
        raise HTTPException(status_code=503, detail=error_msg)
    supabase = get_tenant_client(auth['tenant_key_alias'])
    file_data, content_type, disposition = await email_handlers.download_attachment(
        supabase=supabase, user_id=auth['user_id'], yacht_id=auth['yacht_id'],
        provider_message_id=provider_message_id, attachment_id=attachment_id, inline=inline,
    )

    return StreamingResponse(
        iter([file_data]), media_type=content_type,
        headers={'Content-Disposition': disposition, 'Content-Length': str(len(file_data)), 'X-Content-Type-Options': 'nosniff'},
    )


@router.get("/thread/{thread_id}/links")
async def get_thread_links(thread_id: str, auth: dict = Depends(get_authenticated_user)):
    supabase = get_tenant_client(auth['tenant_key_alias'])
    return await email_handlers.get_thread_links(
        supabase=supabase, yacht_id=auth['yacht_id'], thread_id=thread_id,
    )
