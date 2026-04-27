"""
Email Thread Routes
===================
GET /email/thread/{id}
POST /email/thread/{id}/mark-read
GET /email/thread/{id}/links
GET /email/message/{id}/render
GET /email/message/{id}/attachments
GET /email/message/{id}/attachments/{aid}/download
"""

import base64
import time
import uuid as _uuid
import logging
from datetime import datetime, timezone
from threading import Lock

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import StreamingResponse
from cachetools import TTLCache

from middleware.auth import get_authenticated_user
from integrations.supabase import get_tenant_client
from integrations.feature_flags import check_email_feature
from integrations.graph_client import (
    create_read_client,
    TokenNotFoundError,
    TokenExpiredError,
    TokenRevokedError,
    TokenRefreshError,
    TokenPurposeMismatchError,
    GraphApiError,
)
from services.email_graph_helpers import outlook_auth_error, mark_watcher_degraded, sanitize_filename, utcnow

logger = logging.getLogger(__name__)

router = APIRouter(tags=["email"])

# ── In-memory cache for Graph API message content (60s TTL, yacht-scoped keys) ──
_message_content_cache: TTLCache = TTLCache(maxsize=500, ttl=60)
_cache_lock = Lock()

# ── Attachment security constants ────────────────────────────────────────────
MAX_ATTACHMENT_SIZE_BYTES = 25 * 1024 * 1024

ALLOWED_ATTACHMENT_TYPES = {
    'application/pdf',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'application/vnd.ms-excel',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'text/plain',
    'text/csv',
    'image/jpeg',
    'image/png',
    'image/gif',
    'image/webp',
    'image/tiff',
    'application/zip',
}

INLINE_SAFE_TYPES = {
    'application/pdf',
    'image/jpeg',
    'image/jpg',
    'image/png',
    'image/gif',
    'image/webp',
    'image/tiff',
    'image/svg+xml',
}




# ── GET /thread/{thread_id} ───────────────────────────────────────────────────

@router.get("/thread/{thread_id}")
async def get_thread(
    thread_id: str,
    auth: dict = Depends(get_authenticated_user),
):
    enabled, error_msg = check_email_feature('thread')
    if not enabled:
        raise HTTPException(status_code=503, detail=error_msg)

    yacht_id = auth['yacht_id']
    user_id = auth['user_id']

    try:
        _uuid.UUID(thread_id)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=404,
            detail={"code": "thread_not_found", "message": "Invalid thread ID format", "thread_id": thread_id, "yacht_id": yacht_id}
        )

    supabase = get_tenant_client(auth['tenant_key_alias'])

    try:
        thread_result = supabase.table('email_threads').select(
            'id, yacht_id, watcher_id, provider_conversation_id, latest_subject, message_count, '
            'has_attachments, participant_hashes, source, first_message_at, last_activity_at, '
            'last_inbound_at, last_outbound_at, created_at, updated_at, extracted_tokens, '
            'suggestions_generated_at, active_message_count, is_read'
        ).eq('id', thread_id).eq('yacht_id', yacht_id).limit(1).execute()

        if not thread_result.data:
            # Diagnostic: check if thread exists with a different yacht
            try:
                any_result = supabase.table('email_threads').select('id, yacht_id, latest_subject').eq('id', thread_id).limit(1).execute()
                if any_result.data:
                    actual = any_result.data[0]
                    logger.warning(
                        f"[email/thread] YACHT_ID_MISMATCH: thread={thread_id} exists under "
                        f"yacht={actual.get('yacht_id')} but caller has yacht={yacht_id}. "
                        f"Subject: {actual.get('latest_subject', '')[:50]}"
                    )
                else:
                    logger.info(f"[email/thread] Thread truly does not exist: {thread_id}")
            except Exception as diag_err:
                logger.debug(f"[email/thread] Diagnostic query failed: {diag_err}")

            raise HTTPException(
                status_code=404,
                detail={"code": "thread_not_found", "message": "Thread not found or not accessible", "thread_id": thread_id, "yacht_id": yacht_id}
            )

        thread = thread_result.data[0]

        messages_result = supabase.table('email_messages').select(
            'id, provider_message_id, direction, from_display_name, subject, sent_at, received_at, has_attachments, attachments, web_link'
        ).eq('thread_id', thread_id).eq('yacht_id', yacht_id).order('sent_at', desc=False).execute()

        return {**thread, 'messages': messages_result.data or []}

    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        logger.error(f"[email/thread] Unexpected error: {error_msg}", exc_info=True)
        if 'not found' in error_msg.lower() or 'does not exist' in error_msg.lower():
            raise HTTPException(
                status_code=404,
                detail={"code": "thread_not_found", "message": "Thread not found", "thread_id": thread_id}
            )
        raise HTTPException(
            status_code=500,
            detail={"code": "internal_error", "message": "Failed to fetch thread", "thread_id": thread_id}
        )


# ── POST /thread/{thread_id}/mark-read ────────────────────────────────────────

@router.post("/thread/{thread_id}/mark-read")
async def mark_thread_read(
    thread_id: str,
    auth: dict = Depends(get_authenticated_user),
):
    enabled, error_msg = check_email_feature('thread')
    if not enabled:
        raise HTTPException(status_code=503, detail=error_msg)

    yacht_id = auth['yacht_id']
    supabase = get_tenant_client(auth['tenant_key_alias'])

    try:
        _uuid.UUID(thread_id)
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Invalid thread ID format")

    try:
        result = supabase.table('email_threads').update({
            'is_read': True,
            'updated_at': utcnow(),
        }).eq('id', thread_id).eq('yacht_id', yacht_id).execute()

        if not result.data:
            raise HTTPException(status_code=404, detail="Thread not found")

        logger.debug(f"[email/thread] Marked as read: {thread_id}")
        return {"success": True, "thread_id": thread_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[email/thread/mark-read] Error: {e}")
        raise HTTPException(status_code=500, detail="Failed to mark thread as read")


# ── GET /message/{provider_message_id}/render ────────────────────────────────

@router.get("/message/{provider_message_id}/render")
async def render_message(
    provider_message_id: str,
    response: Response,
    auth: dict = Depends(get_authenticated_user),
):
    """
    Fetch full message content from Graph for rendering.
    DOCTRINE: Content is NOT stored. Fetched on-click only. READ token only.
    """
    start_time = time.time()
    cache_status = "MISS"

    enabled, error_msg = check_email_feature('render')
    if not enabled:
        raise HTTPException(status_code=503, detail=error_msg)

    yacht_id = auth['yacht_id']
    user_id = auth['user_id']
    supabase = get_tenant_client(auth['tenant_key_alias'])

    msg_result = supabase.table('email_messages').select('id').eq(
        'provider_message_id', provider_message_id
    ).eq('yacht_id', yacht_id).maybe_single().execute()

    if not msg_result or not msg_result.data:
        raise HTTPException(status_code=404, detail="Message not found")

    cache_key = f"{yacht_id}:{provider_message_id}"

    try:
        with _cache_lock:
            content = _message_content_cache.get(cache_key)

        if content is not None:
            cache_status = "HIT"
            logger.debug(f"[email/render] Cache HIT for {provider_message_id[:16]}...")
        else:
            read_client = create_read_client(supabase, user_id, yacht_id)
            content = await read_client.get_message_content(provider_message_id)
            with _cache_lock:
                _message_content_cache[cache_key] = content

        body_obj = content.get('body', {})
        body_type = body_obj.get('contentType', 'unknown')
        body_len = len(body_obj.get('content', '')) if body_obj.get('content') else 0
        logger.info(
            f"[email/render] message={provider_message_id[:16]}... "
            f"type={body_type} size={body_len} yacht={yacht_id[:8]}"
        )

        weblink = content.get('webLink')
        if weblink and msg_result.data:
            try:
                supabase.table('email_messages').update({'web_link': weblink}).eq(
                    'provider_message_id', provider_message_id
                ).eq('yacht_id', yacht_id).execute()
            except Exception as e:
                logger.warning(f"[email/render] Failed to update web_link: {e}")

        elapsed_ms = int((time.time() - start_time) * 1000)
        response.headers["X-Graph-Cache"] = cache_status
        response.headers["X-Graph-Time"] = str(elapsed_ms)

        return {
            'id': content.get('id'),
            'subject': content.get('subject'),
            'body': content.get('body', {}),
            'body_preview': content.get('bodyPreview'),
            'from_address': content.get('from', {}),
            'to_recipients': content.get('toRecipients', []),
            'cc_recipients': content.get('ccRecipients', []),
            'received_at': content.get('receivedDateTime'),
            'sent_at': content.get('sentDateTime'),
            'has_attachments': content.get('hasAttachments', False),
            'attachments': content.get('attachments', []),
            'web_link': content.get('webLink'),
        }

    except TokenNotFoundError:
        raise outlook_auth_error("outlook_not_connected", "Email not connected. Please connect your Outlook account.")
    except TokenExpiredError:
        raise outlook_auth_error("outlook_token_expired", "Email connection expired. Please reconnect.")
    except TokenRevokedError:
        await mark_watcher_degraded(supabase, user_id, yacht_id, "Token revoked")
        raise outlook_auth_error("outlook_token_revoked", "Email connection revoked. Please reconnect.")
    except TokenRefreshError as e:
        await mark_watcher_degraded(supabase, user_id, yacht_id, f"Token refresh failed: {e}")
        raise outlook_auth_error("outlook_refresh_failed", "Email connection expired and refresh failed. Please reconnect.")
    except GraphApiError as e:
        if e.status_code == 401:
            await mark_watcher_degraded(supabase, user_id, yacht_id, f"Graph API 401: {e}")
            raise outlook_auth_error("outlook_api_rejected", "Microsoft rejected the request. Please reconnect your Outlook account.")
        elif e.status_code == 404:
            try:
                supabase.table('email_messages').update({
                    'is_deleted': True,
                    'deleted_at': datetime.now(timezone.utc).isoformat(),
                    'updated_at': datetime.now(timezone.utc).isoformat(),
                }).eq('provider_message_id', provider_message_id).eq('yacht_id', yacht_id).execute()
                logger.info(f"[email/render] Auto-marked {provider_message_id[:16]}... as deleted (404 from Graph)")
            except Exception as mark_err:
                logger.error(f"[email/render] Failed to mark message as deleted: {mark_err}")
            raise HTTPException(status_code=404, detail="Message not found in Outlook. It has been removed from your inbox.")
        else:
            logger.error(f"[email/render] Graph API error {e.status_code}: {e}")
            raise HTTPException(status_code=502, detail=f"Microsoft Graph error: {e}")
    except TokenPurposeMismatchError as e:
        logger.error(f"[email/render] Token purpose mismatch: {e}")
        raise HTTPException(status_code=500, detail="Internal configuration error")
    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        graph_status = None
        if hasattr(e, 'response') and hasattr(e.response, 'status_code'):
            graph_status = e.response.status_code
            if graph_status == 401:
                await mark_watcher_degraded(supabase, user_id, yacht_id, f"Graph 401: {error_msg}")
                raise outlook_auth_error("outlook_api_rejected", "Microsoft rejected the request. Please reconnect.")
            elif graph_status == 404:
                try:
                    supabase.table('email_messages').update({
                        'is_deleted': True,
                        'deleted_at': datetime.now(timezone.utc).isoformat(),
                        'updated_at': datetime.now(timezone.utc).isoformat(),
                    }).eq('provider_message_id', provider_message_id).eq('yacht_id', yacht_id).execute()
                except Exception:
                    pass
                raise HTTPException(status_code=404, detail="Message not found in Outlook. It has been removed from your inbox.")
            elif graph_status == 403:
                raise HTTPException(status_code=403, detail="Access denied to this message.")
        logger.error(f"[email/render] Unexpected error ({type(e).__name__}, graph_status={graph_status}): {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch message content")


# ── GET /message/{message_id}/attachments ────────────────────────────────────

@router.get("/message/{message_id}/attachments")
async def list_message_attachments(
    message_id: str,
    auth: dict = Depends(get_authenticated_user),
):
    """List attachment metadata from DB (no content bytes — use /download for that)."""
    enabled, error_msg = check_email_feature('render')
    if not enabled:
        raise HTTPException(status_code=503, detail=error_msg)

    yacht_id = auth['yacht_id']
    supabase = get_tenant_client(auth['tenant_key_alias'])

    msg_result = supabase.table('email_messages').select(
        'id, provider_message_id, has_attachments'
    ).eq('id', message_id).eq('yacht_id', yacht_id).maybe_single().execute()

    if not msg_result.data:
        raise HTTPException(status_code=404, detail="Message not found")

    message = msg_result.data

    if not message.get('has_attachments'):
        return {
            'message_id': message_id,
            'provider_message_id': message['provider_message_id'],
            'attachments': [],
            'count': 0,
        }

    try:
        attachments_result = supabase.table('email_attachments_view').select(
            'link_id, blob_id, name, content_type, size_bytes, is_inline, provider_attachment_id'
        ).eq('message_id', message_id).eq('yacht_id', yacht_id).execute()

        attachments = [
            {
                'link_id': row['link_id'],
                'blob_id': row['blob_id'],
                'name': row['name'],
                'content_type': row.get('content_type'),
                'size_bytes': row.get('size_bytes'),
                'is_inline': row.get('is_inline', False),
                'provider_attachment_id': row.get('provider_attachment_id'),
            }
            for row in (attachments_result.data or [])
        ]

        logger.info(f"[email/attachments] yacht={yacht_id[:8]} message={message_id[:8]} count={len(attachments)}")

        return {
            'message_id': message_id,
            'provider_message_id': message['provider_message_id'],
            'attachments': attachments,
            'count': len(attachments),
        }

    except Exception as e:
        logger.error(f"[email/attachments] Error: {e}")
        raise HTTPException(status_code=500, detail="Failed to list attachments")


# ── GET /message/{provider_message_id}/attachments/{attachment_id}/download ──

@router.get("/message/{provider_message_id}/attachments/{attachment_id}/download")
async def download_attachment(
    provider_message_id: str,
    attachment_id: str,
    inline: bool = False,
    auth: dict = Depends(get_authenticated_user),
):
    """
    Stream attachment content from Graph (NOT stored).
    READ token only. Size + content-type enforced.
    """
    enabled, error_msg = check_email_feature('render')
    if not enabled:
        raise HTTPException(status_code=503, detail=error_msg)

    yacht_id = auth['yacht_id']
    user_id = auth['user_id']
    supabase = get_tenant_client(auth['tenant_key_alias'])

    msg_result = supabase.table('email_messages').select('id').eq(
        'provider_message_id', provider_message_id
    ).eq('yacht_id', yacht_id).maybe_single().execute()

    if not msg_result.data:
        raise HTTPException(status_code=404, detail="Message not found")

    try:
        read_client = create_read_client(supabase, user_id, yacht_id)
        attachment = await read_client.get_attachment(provider_message_id, attachment_id)

        if not attachment:
            raise HTTPException(status_code=404, detail="Attachment not found")

        filename = attachment.get('name', 'attachment')
        content_type = attachment.get('contentType', 'application/octet-stream')
        size_bytes = attachment.get('size', 0)
        content_b64 = attachment.get('contentBytes')

        if not content_b64:
            raise HTTPException(status_code=404, detail="Attachment has no content")

        if size_bytes > MAX_ATTACHMENT_SIZE_BYTES:
            logger.warning(f"[email/download] Attachment too large: {size_bytes} bytes")
            raise HTTPException(
                status_code=413,
                detail=f"Attachment too large ({size_bytes // (1024*1024)} MB). Maximum: {MAX_ATTACHMENT_SIZE_BYTES // (1024*1024)} MB"
            )

        if content_type not in ALLOWED_ATTACHMENT_TYPES:
            logger.warning(f"[email/download] Content type not allowed: {content_type}")
            raise HTTPException(status_code=415, detail=f"Content type '{content_type}' is not allowed for download")

        try:
            file_data = base64.b64decode(content_b64)
        except Exception as decode_error:
            logger.error(f"[email/download] Failed to decode content: {decode_error}")
            raise HTTPException(status_code=502, detail="Failed to decode attachment content")

        if len(file_data) > MAX_ATTACHMENT_SIZE_BYTES:
            raise HTTPException(
                status_code=413,
                detail=f"Attachment too large after decode. Maximum: {MAX_ATTACHMENT_SIZE_BYTES // (1024*1024)} MB"
            )

        safe_filename = sanitize_filename(filename)

        if inline and content_type.lower() in INLINE_SAFE_TYPES:
            disposition = f'inline; filename="{safe_filename}"'
            disposition_type = 'inline'
        else:
            disposition = f'attachment; filename="{safe_filename}"'
            disposition_type = 'attachment'

        logger.info(
            f"[email/download] Serving: {safe_filename} ({len(file_data)} bytes) "
            f"type={content_type} disposition={disposition_type} user={user_id[:8]}"
        )

        def content_generator():
            yield file_data

        return StreamingResponse(
            content_generator(),
            media_type=content_type,
            headers={
                'Content-Disposition': disposition,
                'Content-Length': str(len(file_data)),
                'X-Content-Type-Options': 'nosniff',
            }
        )

    except TokenNotFoundError:
        raise outlook_auth_error("outlook_not_connected", "Email not connected. Please connect your Outlook account.")
    except TokenExpiredError:
        raise outlook_auth_error("outlook_token_expired", "Email connection expired. Please reconnect.")
    except TokenRevokedError:
        await mark_watcher_degraded(supabase, user_id, yacht_id, "Token revoked during download")
        raise outlook_auth_error("outlook_token_revoked", "Email connection revoked. Please reconnect.")
    except TokenRefreshError as e:
        await mark_watcher_degraded(supabase, user_id, yacht_id, f"Token refresh failed: {e}")
        raise outlook_auth_error("outlook_refresh_failed", "Email connection expired and refresh failed. Please reconnect.")
    except GraphApiError as e:
        if e.status_code == 401:
            await mark_watcher_degraded(supabase, user_id, yacht_id, f"Graph API 401: {e}")
            raise outlook_auth_error("outlook_api_rejected", "Microsoft rejected the request. Please reconnect.")
        elif e.status_code == 404:
            raise HTTPException(status_code=404, detail="Attachment not found in Outlook")
        else:
            logger.error(f"[email/download] Graph API error {e.status_code}: {e}")
            raise HTTPException(status_code=502, detail=f"Microsoft Graph error: {e}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[email/download] Unexpected error: {e}")
        raise HTTPException(status_code=500, detail="Failed to download attachment")


# ── GET /thread/{thread_id}/links ─────────────────────────────────────────────

@router.get("/thread/{thread_id}/links")
async def get_thread_links(
    thread_id: str,
    auth: dict = Depends(get_authenticated_user),
):
    """Get all entity links for a thread with resolved object names."""
    yacht_id = auth['yacht_id']
    supabase = get_tenant_client(auth['tenant_key_alias'])

    try:
        thread_result = supabase.table('email_threads').select('id').eq(
            'id', thread_id
        ).eq('yacht_id', yacht_id).limit(1).execute()

        if not thread_result.data:
            raise HTTPException(status_code=404, detail="Thread not found")

        links_result = supabase.table('email_links').select(
            'id, object_type, object_id, confidence, suggested_reason, accepted_at, accepted_by, is_active, score'
        ).eq('thread_id', thread_id).eq('yacht_id', yacht_id).eq('is_active', True).execute()

        links = links_result.data or []

        ENTITY_TABLE_MAP = {
            'work_order': ('pms_work_orders', 'id,title,wo_number',     'title', 'wo_number'),
            'equipment':  ('pms_equipment',   'id,name,serial_number',  'name',  'serial_number'),
            'fault':      ('pms_faults',      'id,title,fault_number',  'title', 'fault_number'),
            'part':       ('pms_parts',       'id,name,part_number',    'name',  'part_number'),
        }

        for link in links:
            obj_type = link.get('object_type', '')
            obj_id = link.get('object_id', '')
            config = ENTITY_TABLE_MAP.get(obj_type)
            if config:
                table, select, name_field, ref_field = config
                try:
                    row = supabase.table(table).select(select).eq('id', obj_id).eq('yacht_id', yacht_id).limit(1).execute()
                    if row.data:
                        d = row.data[0]
                        link['object_name'] = d.get(name_field) or obj_id[:8]
                        link['object_ref'] = d.get(ref_field) or ''
                    else:
                        link['object_name'] = obj_id[:8]
                        link['object_ref'] = 'not found'
                except Exception:
                    link['object_name'] = obj_id[:8]
                    link['object_ref'] = ''
            else:
                link['object_name'] = obj_id[:8]
                link['object_ref'] = obj_type

        grouped: dict = {}
        for link in links:
            obj_type = link.get('object_type', 'other')
            grouped.setdefault(obj_type, []).append(link)

        return {
            'thread_id': thread_id,
            'links': links,
            'grouped': grouped,
            'total_count': len(links),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[email/thread/links] Error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch thread links: {e}")
