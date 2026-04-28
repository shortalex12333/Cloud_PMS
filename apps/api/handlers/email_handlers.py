"""
Email Handlers
==============
All business logic for the email domain.
Routes parse → call here → return. Zero DB queries in routes/.

Sections:
  Thread  — get_thread, mark_thread_read, render_message,
             list_message_attachments, download_attachment, get_thread_links
  Inbox   — search_emails, get_inbox_threads, get_related_threads,
             get_message_focus, search_linkable_objects,
             get_unread_count, get_worker_status
  Links   — add_link, accept_link, change_link, remove_link, reject_link,
             execute_action, save_attachment
  Sync    — sync_now, sync_all_folders, backfill_embeddings,
             backfill_weblinks, get_entity_ledger
  Debug   — debug_search_folders, debug_graph_me, debug_inbox_compare,
             debug_thread_yacht_check, debug_force_sync_missing
"""

import asyncio
import base64
import hashlib
import json
import logging
import os
import time
import uuid as _uuid_mod
from threading import Lock
from typing import Any, Dict, List, Optional, Tuple

import httpx
from cachetools import TTLCache
from fastapi import HTTPException
from fastapi.responses import StreamingResponse

from integrations.graph_client import (
    GraphApiError,
    TokenExpiredError,
    TokenNotFoundError,
    TokenPurposeMismatchError,
    TokenRefreshError,
    TokenRevokedError,
    create_read_client,
)
from services.email_graph_helpers import (
    mark_watcher_degraded,
    outlook_auth_error,
    sanitize_filename,
    utcnow,
)
from services.email_link_service import (
    OBJECT_TYPE_TABLE_MAP,
    audit_link_action,
    check_idempotency,
    upsert_email_link,
)
from services.email_search_service import (
    MIN_FREE_TEXT_LENGTH,
    _embedding_cache,
    search_email_threads,
)
from services.email_suggestion_service import generate_suggestions_for_thread

logger = logging.getLogger(__name__)

# ── Message content cache (yacht-scoped, 60s TTL) ────────────────────────────
_message_content_cache: TTLCache = TTLCache(maxsize=500, ttl=60)
_cache_lock = Lock()

# ── Attachment download constants ─────────────────────────────────────────────
MAX_ATTACHMENT_SIZE_BYTES = 25 * 1024 * 1024

ALLOWED_ATTACHMENT_TYPES = {
    'application/pdf', 'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'application/vnd.ms-excel',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'text/plain', 'text/csv',
    'image/jpeg', 'image/png', 'image/gif', 'image/webp', 'image/tiff',
    'application/zip',
}

INLINE_SAFE_TYPES = {
    'application/pdf',
    'image/jpeg', 'image/jpg', 'image/png', 'image/gif',
    'image/webp', 'image/tiff', 'image/svg+xml',
}

# ── Evidence upload constants ─────────────────────────────────────────────────
MAX_EVIDENCE_SIZE_BYTES = 50 * 1024 * 1024

ALLOWED_EVIDENCE_EXTENSIONS = {
    '.pdf', '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff',
    '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
    '.txt', '.csv', '.rtf', '.odt', '.ods', '.odp',
}

ALLOWED_EVIDENCE_MIME_TYPES = {
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

TRIGGER_TIMEOUT_SECONDS = 5

VALID_LINK_REASONS = [
    'token_match', 'vendor_domain', 'wo_pattern', 'po_pattern',
    'serial_match', 'part_number', 'manual',
]

ACTION_PERMISSIONS: Dict[str, List[str]] = {
    'link_to_work_order':           ['chief_engineer', 'eto', 'captain', 'manager', 'member'],
    'link_to_equipment':            ['chief_engineer', 'eto', 'captain', 'manager', 'member'],
    'link_to_part':                 ['chief_engineer', 'eto', 'captain', 'manager', 'member'],
    'create_work_order_from_email': ['chief_engineer', 'eto', 'captain', 'manager'],
}

LINK_MANAGE_ROLES = ['chief_engineer', 'eto', 'captain', 'manager', 'member']
EVIDENCE_SAVE_ROLES = ['chief_engineer', 'eto', 'captain', 'manager', 'member']

_ENTITY_TABLE_MAP = {
    'work_order': ('pms_work_orders', 'id,title,wo_number',    'title', 'wo_number'),
    'equipment':  ('pms_equipment',   'id,name,serial_number', 'name',  'serial_number'),
    'fault':      ('pms_faults',      'id,title,fault_number', 'title', 'fault_number'),
    'part':       ('pms_parts',       'id,name,part_number',   'name',  'part_number'),
}


# ══════════════════════════════════════════════════════════════════════════════
# INTERNAL
# ══════════════════════════════════════════════════════════════════════════════

async def _process_message(supabase, yacht_id: str, msg: Dict, folder: str) -> None:
    """Upsert a single Graph message into email_threads + email_messages."""
    conversation_id = msg.get('conversationId')
    if not conversation_id:
        return

    thread_result = supabase.table('email_threads').select('id').eq(
        'yacht_id', yacht_id
    ).eq('provider_conversation_id', conversation_id).maybe_single().execute()

    if thread_result and thread_result.data:
        thread_id = thread_result.data['id']
    else:
        thread_insert = supabase.table('email_threads').insert({
            'yacht_id': yacht_id,
            'provider_conversation_id': conversation_id,
            'latest_subject': msg.get('subject'),
            'message_count': 0,
            'has_attachments': msg.get('hasAttachments', False),
            'source': 'external',
        }).execute()
        if not thread_insert or not thread_insert.data:
            raise Exception(f"Failed to create thread for conversation {conversation_id[:20]}...")
        thread_id = thread_insert.data[0]['id']

    from_addr = msg.get('from', {}).get('emailAddress', {}).get('address', '')
    from_hash = hashlib.sha256(from_addr.lower().encode()).hexdigest() if from_addr else ''
    from_name = msg.get('from', {}).get('emailAddress', {}).get('name', '')
    to_hashes = [
        hashlib.sha256(r.get('emailAddress', {}).get('address', '').lower().encode()).hexdigest()
        for r in msg.get('toRecipients', [])
        if r.get('emailAddress', {}).get('address')
    ]
    cc_hashes = [
        hashlib.sha256(r.get('emailAddress', {}).get('address', '').lower().encode()).hexdigest()
        for r in msg.get('ccRecipients', [])
        if r.get('emailAddress', {}).get('address')
    ]
    direction = 'outbound' if folder == 'sent' else 'inbound'

    existing = supabase.table('email_messages').select('id').eq(
        'yacht_id', yacht_id
    ).eq('provider_message_id', msg.get('id')).maybe_single().execute()
    if existing and existing.data:
        return

    preview_text = (msg.get('bodyPreview', '') or '')[:200] or None

    insert_result = supabase.table('email_messages').insert({
        'thread_id': thread_id,
        'yacht_id': yacht_id,
        'provider_message_id': msg.get('id'),
        'internet_message_id': msg.get('internetMessageId'),
        'direction': direction,
        'from_address_hash': from_hash,
        'from_display_name': from_name,
        'to_addresses_hash': to_hashes,
        'cc_addresses_hash': cc_hashes,
        'subject': msg.get('subject'),
        'preview_text': preview_text,
        'sent_at': msg.get('sentDateTime'),
        'received_at': msg.get('receivedDateTime'),
        'has_attachments': msg.get('hasAttachments', False),
        'folder': folder,
    }).execute()

    if insert_result.data and preview_text:
        try:
            supabase.rpc('queue_email_extraction', {
                'p_message_id': insert_result.data[0]['id'],
                'p_yacht_id': yacht_id,
                'p_job_type': 'full',
            }).execute()
        except Exception as e:
            logger.warning(f"[email/sync] Failed to queue extraction job: {e}")

    supabase.rpc('update_thread_activity', {
        'p_thread_id': thread_id,
        'p_sent_at': msg.get('sentDateTime') or msg.get('receivedDateTime'),
        'p_direction': direction,
        'p_subject': msg.get('subject'),
        'p_has_attachments': msg.get('hasAttachments', False),
    }).execute()

    try:
        await generate_suggestions_for_thread(supabase, thread_id, yacht_id)
    except Exception as e:
        logger.warning(f"Failed to generate suggestions for thread {thread_id}: {e}")


# ══════════════════════════════════════════════════════════════════════════════
# THREAD
# ══════════════════════════════════════════════════════════════════════════════

async def get_thread(supabase, yacht_id: str, user_id: str, thread_id: str) -> dict:
    result = supabase.table('email_threads').select(
        'id, yacht_id, watcher_id, provider_conversation_id, latest_subject, message_count, '
        'has_attachments, participant_hashes, source, first_message_at, last_activity_at, '
        'last_inbound_at, last_outbound_at, created_at, updated_at, extracted_tokens, '
        'suggestions_generated_at, active_message_count, is_read'
    ).eq('id', thread_id).eq('yacht_id', yacht_id).limit(1).execute()

    if not result.data:
        try:
            any_r = supabase.table('email_threads').select('id, yacht_id, latest_subject').eq('id', thread_id).limit(1).execute()
            if any_r.data:
                actual = any_r.data[0]
                logger.warning(
                    f"[email/thread] YACHT_ID_MISMATCH thread={thread_id} "
                    f"exists under yacht={actual.get('yacht_id')} caller={yacht_id} "
                    f"subject={actual.get('latest_subject', '')[:50]}"
                )
            else:
                logger.info(f"[email/thread] Thread truly does not exist: {thread_id}")
        except Exception as e:
            logger.debug(f"[email/thread] Diagnostic query failed: {e}")
        raise HTTPException(
            status_code=404,
            detail={"code": "thread_not_found", "message": "Thread not found or not accessible",
                    "thread_id": thread_id, "yacht_id": yacht_id}
        )

    thread = result.data[0]
    messages = supabase.table('email_messages').select(
        'id, provider_message_id, direction, from_display_name, subject, '
        'sent_at, received_at, has_attachments, attachments, web_link'
    ).eq('thread_id', thread_id).eq('yacht_id', yacht_id).order('sent_at', desc=False).execute()

    return {**thread, 'messages': messages.data or []}


async def mark_thread_read(supabase, yacht_id: str, thread_id: str) -> dict:
    result = supabase.table('email_threads').update({
        'is_read': True,
        'updated_at': utcnow(),
    }).eq('id', thread_id).eq('yacht_id', yacht_id).execute()

    if not result.data:
        raise HTTPException(status_code=404, detail="Thread not found")

    logger.debug(f"[email/thread] Marked as read: {thread_id}")
    return {"success": True, "thread_id": thread_id}


async def render_message(
    supabase, user_id: str, yacht_id: str, provider_message_id: str
) -> Tuple[dict, str, int]:
    """Returns (data, cache_status, elapsed_ms). Route sets response headers."""
    start = time.time()
    cache_status = "MISS"

    msg_check = supabase.table('email_messages').select('id').eq(
        'provider_message_id', provider_message_id
    ).eq('yacht_id', yacht_id).maybe_single().execute()
    if not msg_check or not msg_check.data:
        raise HTTPException(status_code=404, detail="Message not found")

    cache_key = f"{yacht_id}:{provider_message_id}"
    try:
        with _cache_lock:
            content = _message_content_cache.get(cache_key)

        if content is not None:
            cache_status = "HIT"
        else:
            read_client = create_read_client(supabase, user_id, yacht_id)
            content = await read_client.get_message_content(provider_message_id)
            with _cache_lock:
                _message_content_cache[cache_key] = content

        body_obj = content.get('body', {})
        logger.info(
            f"[email/render] message={provider_message_id[:16]}... "
            f"type={body_obj.get('contentType','?')} "
            f"size={len(body_obj.get('content',''))} yacht={yacht_id[:8]}"
        )

        weblink = content.get('webLink')
        if weblink:
            try:
                supabase.table('email_messages').update({'web_link': weblink}).eq(
                    'provider_message_id', provider_message_id
                ).eq('yacht_id', yacht_id).execute()
            except Exception as e:
                logger.warning(f"[email/render] Failed to update web_link: {e}")

        data = {
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
        return data, cache_status, int((time.time() - start) * 1000)

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
        if e.status_code == 404:
            _try_mark_deleted(supabase, provider_message_id, yacht_id)
            raise HTTPException(status_code=404, detail="Message not found in Outlook. It has been removed from your inbox.")
        logger.error(f"[email/render] Graph API error {e.status_code}: {e}")
        raise HTTPException(status_code=502, detail=f"Microsoft Graph error: {e}")
    except TokenPurposeMismatchError as e:
        logger.error(f"[email/render] Token purpose mismatch: {e}")
        raise HTTPException(status_code=500, detail="Internal configuration error")
    except HTTPException:
        raise
    except Exception as e:
        graph_status = getattr(getattr(e, 'response', None), 'status_code', None)
        if graph_status == 401:
            await mark_watcher_degraded(supabase, user_id, yacht_id, f"Graph 401: {e}")
            raise outlook_auth_error("outlook_api_rejected", "Microsoft rejected the request. Please reconnect.")
        if graph_status == 404:
            _try_mark_deleted(supabase, provider_message_id, yacht_id)
            raise HTTPException(status_code=404, detail="Message not found in Outlook.")
        if graph_status == 403:
            raise HTTPException(status_code=403, detail="Access denied to this message.")
        logger.error(f"[email/render] Unexpected error ({type(e).__name__}, graph_status={graph_status}): {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch message content")


def _try_mark_deleted(supabase, provider_message_id: str, yacht_id: str) -> None:
    try:
        supabase.table('email_messages').update({
            'is_deleted': True,
            'deleted_at': utcnow(),
            'updated_at': utcnow(),
        }).eq('provider_message_id', provider_message_id).eq('yacht_id', yacht_id).execute()
        logger.info(f"[email/render] Auto-marked {provider_message_id[:16]}... as deleted")
    except Exception as e:
        logger.error(f"[email/render] Failed to mark message deleted: {e}")


async def list_message_attachments(supabase, yacht_id: str, message_id: str) -> dict:
    msg = supabase.table('email_messages').select(
        'id, provider_message_id, has_attachments'
    ).eq('id', message_id).eq('yacht_id', yacht_id).maybe_single().execute()

    if not msg.data:
        raise HTTPException(status_code=404, detail="Message not found")

    if not msg.data.get('has_attachments'):
        return {'message_id': message_id, 'provider_message_id': msg.data['provider_message_id'], 'attachments': [], 'count': 0}

    rows = supabase.table('email_attachments_view').select(
        'link_id, blob_id, name, content_type, size_bytes, is_inline, provider_attachment_id'
    ).eq('message_id', message_id).eq('yacht_id', yacht_id).execute()

    attachments = [
        {
            'link_id': r['link_id'], 'blob_id': r['blob_id'], 'name': r['name'],
            'content_type': r.get('content_type'), 'size_bytes': r.get('size_bytes'),
            'is_inline': r.get('is_inline', False),
            'provider_attachment_id': r.get('provider_attachment_id'),
        }
        for r in (rows.data or [])
    ]
    logger.info(f"[email/attachments] yacht={yacht_id[:8]} message={message_id[:8]} count={len(attachments)}")
    return {
        'message_id': message_id,
        'provider_message_id': msg.data['provider_message_id'],
        'attachments': attachments,
        'count': len(attachments),
    }


async def download_attachment(
    supabase, user_id: str, yacht_id: str,
    provider_message_id: str, attachment_id: str, inline: bool,
) -> Tuple[bytes, str, str]:
    """Returns (file_data, content_type, disposition). Route wraps in StreamingResponse."""
    msg_check = supabase.table('email_messages').select('id').eq(
        'provider_message_id', provider_message_id
    ).eq('yacht_id', yacht_id).maybe_single().execute()
    if not msg_check.data:
        raise HTTPException(status_code=404, detail="Message not found")

    try:
        read_client = create_read_client(supabase, user_id, yacht_id)
        attachment = await read_client.get_attachment(provider_message_id, attachment_id)

        if not attachment:
            raise HTTPException(status_code=404, detail="Attachment not found")

        content_b64 = attachment.get('contentBytes')
        if not content_b64:
            raise HTTPException(status_code=404, detail="Attachment has no content")

        size_bytes = attachment.get('size', 0)
        content_type = attachment.get('contentType', 'application/octet-stream')
        filename = attachment.get('name', 'attachment')

        if size_bytes > MAX_ATTACHMENT_SIZE_BYTES:
            raise HTTPException(status_code=413, detail=f"Attachment too large ({size_bytes // (1024*1024)} MB). Maximum: {MAX_ATTACHMENT_SIZE_BYTES // (1024*1024)} MB")

        if content_type not in ALLOWED_ATTACHMENT_TYPES:
            raise HTTPException(status_code=415, detail=f"Content type '{content_type}' is not allowed for download")

        try:
            file_data = base64.b64decode(content_b64)
        except Exception as e:
            logger.error(f"[email/download] Failed to decode content: {e}")
            raise HTTPException(status_code=502, detail="Failed to decode attachment content")

        if len(file_data) > MAX_ATTACHMENT_SIZE_BYTES:
            raise HTTPException(status_code=413, detail=f"Attachment too large after decode. Maximum: {MAX_ATTACHMENT_SIZE_BYTES // (1024*1024)} MB")

        safe_filename = sanitize_filename(filename)
        if inline and content_type.lower() in INLINE_SAFE_TYPES:
            disposition = f'inline; filename="{safe_filename}"'
        else:
            disposition = f'attachment; filename="{safe_filename}"'

        logger.info(f"[email/download] Serving: {safe_filename} ({len(file_data)} bytes) type={content_type} user={user_id[:8]}")
        return file_data, content_type, disposition

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
        if e.status_code == 404:
            raise HTTPException(status_code=404, detail="Attachment not found in Outlook")
        raise HTTPException(status_code=502, detail=f"Microsoft Graph error: {e}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[email/download] Unexpected error: {e}")
        raise HTTPException(status_code=500, detail="Failed to download attachment")


async def get_thread_links(supabase, yacht_id: str, thread_id: str) -> dict:
    if not supabase.table('email_threads').select('id').eq('id', thread_id).eq('yacht_id', yacht_id).limit(1).execute().data:
        raise HTTPException(status_code=404, detail="Thread not found")

    links = supabase.table('email_links').select(
        'id, object_type, object_id, confidence, suggested_reason, accepted_at, accepted_by, is_active, score'
    ).eq('thread_id', thread_id).eq('yacht_id', yacht_id).eq('is_active', True).execute().data or []

    for link in links:
        obj_type = link.get('object_type', '')
        obj_id = link.get('object_id', '')
        config = _ENTITY_TABLE_MAP.get(obj_type)
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
        grouped.setdefault(link.get('object_type', 'other'), []).append(link)

    return {'thread_id': thread_id, 'links': links, 'grouped': grouped, 'total_count': len(links)}


# ══════════════════════════════════════════════════════════════════════════════
# INBOX
# ══════════════════════════════════════════════════════════════════════════════

async def search_emails(
    supabase, yacht_id: str, user_id: str, user_email: str,
    q: str, limit: int, threshold: float,
    date_from: Optional[str], date_to: Optional[str],
    boost_recency: bool, boost_affinity: bool, boost_linkage: bool,
) -> dict:
    from email_rag.query_parser import prepare_query_for_search
    start = time.time()
    t: Dict[str, Any] = {
        'parse_ms': 0, 'embed_ms': 0, 'search_ms': 0, 'total_ms': 0,
        'operators_count': 0, 'keywords_count': 0, 'results_count': 0,
        'zero_results': False, 'parse_warnings': 0,
        'embed_skipped': False, 'embed_cached': False,
    }

    t0 = time.time()
    parsed = prepare_query_for_search(q)
    t['parse_ms'] = int((time.time() - t0) * 1000)
    t['operators_count'] = parsed['operators_count']
    t['keywords_count'] = len(parsed['keywords'])
    t['parse_warnings'] = len(parsed['warnings'])
    logger.info(f"[email/search] yacht={yacht_id[:8]} operators={parsed['operators_count']} keywords={len(parsed['keywords'])}")

    t0 = time.time()
    free_text = (parsed['free_text'] or '').strip()
    subject_filter = parsed['filters'].get('p_subject', '')
    should_skip = (
        len(free_text) < MIN_FREE_TEXT_LENGTH
        and parsed['operators_count'] > 0
        and not (subject_filter and ' ' in subject_filter)
    )

    if should_skip:
        embedding = [0.0] * 1536
        t['embed_skipped'] = True
    else:
        search_text = free_text or q
        embedding = _embedding_cache.get(search_text, yacht_id, user_id)
        if embedding:
            t['embed_cached'] = True
        else:
            from email_rag.embedder import generate_embedding_sync
            embedding = generate_embedding_sync(search_text)
            if embedding:
                _embedding_cache.set(search_text, yacht_id, user_id, embedding)

    if not embedding:
        embedding = [0.0] * 1536
        t['embed_skipped'] = True
    t['embed_ms'] = int((time.time() - t0) * 1000)

    user_email_hash = hashlib.sha256(user_email.lower().encode()).hexdigest() if user_email else None
    params: Dict[str, Any] = {
        'p_yacht_id': yacht_id,
        'p_embedding': embedding,
        'p_entity_keywords': parsed['keywords'] or [],
        'p_limit': min(limit, 100),
        'p_similarity_threshold': 0.0 if t['embed_skipped'] else threshold,
        'p_user_email_hash': user_email_hash,
        'p_boost_recency': boost_recency,
        'p_boost_affinity': boost_affinity and user_email_hash is not None,
        'p_boost_linkage': boost_linkage,
    }
    params.update(parsed['filters'])
    if date_from:
        params['p_date_from'] = date_from
    if date_to:
        params['p_date_to'] = date_to

    t0 = time.time()
    result = supabase.rpc('search_email_hybrid', params).execute()
    t['search_ms'] = int((time.time() - t0) * 1000)
    t['results_count'] = len(result.data or [])
    t['zero_results'] = t['results_count'] == 0

    results = []
    for row in (result.data or []):
        score_obj: Dict[str, Any] = {
            'total': row.get('total_score'),
            'vector': row.get('vector_score'),
            'entity': row.get('entity_score'),
        }
        for key in ('recency_score', 'affinity_score', 'linkage_score', 'activity_score'):
            if key in row:
                score_obj[key.replace('_score', '')] = row[key]
        results.append({
            'message_id': row.get('message_id'),
            'thread_id': row.get('thread_id'),
            'subject': row.get('subject'),
            'preview_text': row.get('preview_text'),
            'from_display_name': row.get('from_display_name'),
            'from_address': row.get('from_address_hash'),
            'sent_at': row.get('sent_at'),
            'direction': row.get('direction'),
            'has_attachments': row.get('has_attachments'),
            'score': score_obj,
            'score_breakdown': row.get('score_breakdown'),
            'matched_entities': row.get('matched_entities', []),
            'filters_applied': row.get('filters_applied', []),
        })

    t['total_ms'] = int((time.time() - start) * 1000)
    logger.info(f"[email/search/telemetry] yacht={yacht_id[:8]} total_ms={t['total_ms']} results={t['results_count']}")
    if t['total_ms'] > 500:
        logger.warning(f"[email/search/slow] yacht={yacht_id[:8]} total_ms={t['total_ms']}")

    return {
        'results': results,
        'count': len(results),
        'query': q,
        'parsed': {
            'free_text': parsed['free_text'],
            'operators_count': parsed['operators_count'],
            'filters': parsed['filters'],
            'match_reasons': parsed['match_reasons'],
            'warnings': parsed['warnings'],
        },
        'extracted_keywords': parsed['keywords'],
        'telemetry': {'total_ms': t['total_ms'], 'search_ms': t['search_ms']},
    }


async def get_inbox_threads(
    supabase, yacht_id: str, user_id: str,
    page: int, page_size: int, linked: bool,
    q: Optional[str], direction: Optional[str],
) -> dict:
    offset = (page - 1) * page_size

    watcher_r = supabase.table('email_watchers').select('id').eq(
        'user_id', user_id
    ).eq('yacht_id', yacht_id).eq('sync_status', 'active').limit(1).execute()
    watcher_id = watcher_r.data[0]['id'] if watcher_r.data else None

    if q and len(q) >= 2:
        return await search_email_threads(supabase, yacht_id, user_id, q, direction, page, page_size, linked, watcher_id)

    def _apply_direction(query):
        if direction == 'inbound':
            return query.not_.is_('last_inbound_at', 'null')
        if direction == 'outbound':
            return query.not_.is_('last_outbound_at', 'null')
        return query

    thread_cols = (
        'id, yacht_id, watcher_id, provider_conversation_id, latest_subject, message_count, '
        'has_attachments, source, last_activity_at, created_at, last_inbound_at, last_outbound_at, is_read'
    )

    if linked:
        q_obj = _apply_direction(
            supabase.table('email_threads').select(thread_cols, count='exact').eq('yacht_id', yacht_id)
        )
        result = q_obj.order('last_activity_at', desc=True).range(offset, offset + page_size - 1).execute()
    else:
        result = None
        try:
            result = supabase.rpc('get_unlinked_email_threads', {
                'p_yacht_id': yacht_id, 'p_limit': page_size, 'p_offset': offset, 'p_search': '',
            }).execute()
        except Exception as e:
            logger.debug(f"[email/inbox] RPC fallback: {e}")

        if not result or not result.data:
            all_threads = _apply_direction(
                supabase.table('email_threads').select(thread_cols).eq('yacht_id', yacht_id)
            ).order('last_activity_at', desc=True).limit(100).execute()

            linked_ids = {
                l['thread_id'] for l in (
                    supabase.table('email_links').select('thread_id').eq('yacht_id', yacht_id).eq('is_active', True).execute().data or []
                )
            }
            unlinked = [t for t in (all_threads.data or []) if t['id'] not in linked_ids]

            class _R:
                def __init__(self, data, count):
                    self.data = data
                    self.count = count

            result = _R(data=unlinked[offset:offset + page_size], count=len(unlinked))

    threads = result.data or []
    total = result.count if hasattr(result, 'count') and result.count else len(threads)
    return {'threads': threads, 'total': total, 'page': page, 'page_size': page_size, 'has_more': offset + len(threads) < total}


async def get_related_threads(supabase, yacht_id: str, object_type: str, object_id: str) -> dict:
    links_r = supabase.table('email_links').select(
        'id, thread_id, confidence, suggested_reason, accepted_at, accepted_by'
    ).eq('yacht_id', yacht_id).eq('object_type', object_type).eq('object_id', object_id).eq('is_active', True).execute()

    if not links_r.data:
        return {'threads': [], 'count': 0}

    thread_ids = [l['thread_id'] for l in links_r.data]
    threads_r = supabase.table('email_threads').select(
        'id, provider_conversation_id, latest_subject, message_count, has_attachments, source, last_activity_at'
    ).eq('yacht_id', yacht_id).in_('id', thread_ids).order('last_activity_at', desc=True).execute()

    link_map = {l['thread_id']: l for l in links_r.data}
    threads = [
        {
            **t,
            'link_id': link_map.get(t['id'], {}).get('id'),
            'confidence': link_map.get(t['id'], {}).get('confidence'),
            'suggested_reason': link_map.get(t['id'], {}).get('suggested_reason'),
            'accepted': link_map.get(t['id'], {}).get('accepted_at') is not None,
        }
        for t in (threads_r.data or [])
    ]
    return {'threads': threads, 'count': len(threads)}


async def get_message_focus(supabase, yacht_id: str, user_role: str, message_id: str) -> dict:
    from email_rag.micro_actions import build_focus_response

    msg_r = supabase.table('email_messages').select(
        'id, thread_id, subject, from_display_name, sent_at, has_attachments, attachments, preview_text'
    ).eq('id', message_id).eq('yacht_id', yacht_id).maybe_single().execute()

    if not msg_r.data:
        raise HTTPException(status_code=404, detail="Message not found")

    message = msg_r.data

    entities_r = supabase.table('email_extraction_results').select(
        'entity_type, entity_value, confidence'
    ).eq('message_id', message_id).execute()

    extracted: dict = {}
    for e in (entities_r.data or []):
        extracted.setdefault(e['entity_type'], []).append(e['entity_value'])

    if not extracted and message.get('preview_text'):
        from email_rag.entity_extractor import EmailEntityExtractor
        extractor = EmailEntityExtractor()
        extracted = extractor.extract(f"{message.get('subject', '')}\n\n{message.get('preview_text', '')}")

    links_r = supabase.table('email_links').select(
        'id, object_type, object_id, confidence, accepted_at'
    ).eq('thread_id', message['thread_id']).eq('yacht_id', yacht_id).eq('is_active', True).execute()

    existing_links = [
        {'id': l['id'], 'object_type': l['object_type'], 'object_id': l['object_id'],
         'confidence': l['confidence'], 'accepted': l['accepted_at'] is not None}
        for l in (links_r.data or [])
    ]

    attachments = message.get('attachments') or []
    if isinstance(attachments, str):
        try:
            attachments = json.loads(attachments)
        except Exception:
            attachments = []

    response = build_focus_response(
        message_id=message_id,
        thread_id=message['thread_id'],
        subject=message.get('subject'),
        from_display_name=message.get('from_display_name'),
        sent_at=message.get('sent_at'),
        has_attachments=message.get('has_attachments', False),
        attachment_count=len(attachments),
        extracted_entities=extracted,
        existing_links=existing_links,
        user_role=user_role,
    )
    logger.info(
        f"[email/focus] yacht={yacht_id[:8]} message={message_id[:8]} "
        f"entities={len(extracted)} links={len(existing_links)} actions={len(response.micro_actions)}"
    )
    return response.to_dict()


async def search_linkable_objects(supabase, yacht_id: str, q: str, type_list: List[str], limit: int) -> dict:
    results: List[dict] = []

    if 'work_order' in type_list:
        for wo in (supabase.table('pms_work_orders').select('id, title, status, wo_number').eq('yacht_id', yacht_id).or_(f"title.ilike.%{q}%,wo_number.ilike.%{q}%").limit(limit).execute().data or []):
            results.append({'type': 'work_order', 'id': wo['id'], 'label': f"WO-{wo.get('wo_number', '')}: {wo.get('title', 'Untitled')}", 'status': wo.get('status')})

    if 'equipment' in type_list:
        for eq in (supabase.table('pms_equipment').select('id, name, serial_number, model').eq('yacht_id', yacht_id).or_(f"name.ilike.%{q}%,serial_number.ilike.%{q}%,model.ilike.%{q}%").limit(limit).execute().data or []):
            label = eq.get('name', 'Unknown')
            if eq.get('serial_number'):
                label += f" (S/N: {eq['serial_number']})"
            results.append({'type': 'equipment', 'id': eq['id'], 'label': label})

    if 'part' in type_list:
        for part in (supabase.table('pms_parts').select('id, name, part_number').eq('yacht_id', yacht_id).or_(f"name.ilike.%{q}%,part_number.ilike.%{q}%").limit(limit).execute().data or []):
            label = part.get('name', 'Unknown')
            if part.get('part_number'):
                label += f" (P/N: {part['part_number']})"
            results.append({'type': 'part', 'id': part['id'], 'label': label})

    if 'fault' in type_list:
        for fault in (supabase.table('pms_faults').select('id, title, status').eq('yacht_id', yacht_id).ilike('title', f'%{q}%').limit(limit).execute().data or []):
            results.append({'type': 'fault', 'id': fault['id'], 'label': fault.get('title', 'Untitled'), 'status': fault.get('status')})

    if 'purchase_order' in type_list:
        for po in (supabase.table('pms_purchase_orders').select('id, po_number, description, status').eq('yacht_id', yacht_id).or_(f"po_number.ilike.%{q}%,description.ilike.%{q}%").limit(limit).execute().data or []):
            results.append({'type': 'purchase_order', 'id': po['id'], 'label': f"PO-{po.get('po_number', '')}: {po.get('description', '')}", 'status': po.get('status')})

    if 'supplier' in type_list:
        for s in (supabase.table('pms_suppliers').select('id, name, category').eq('yacht_id', yacht_id).ilike('name', f'%{q}%').limit(limit).execute().data or []):
            label = s.get('name', 'Unknown')
            if s.get('category'):
                label += f" ({s['category']})"
            results.append({'type': 'supplier', 'id': s['id'], 'label': label})

    return {'results': results}


async def get_unread_count(supabase, user_id: str, yacht_id: str) -> dict:
    try:
        read_client = create_read_client(supabase, user_id, yacht_id)
        token = await read_client._get_token()
        async with httpx.AsyncClient() as client:
            r = await client.get(
                "https://graph.microsoft.com/v1.0/me/mailFolders/inbox?$select=unreadItemCount",
                headers={"Authorization": f"Bearer {token}"},
                timeout=10.0,
            )
            if r.status_code != 200:
                return {"unread_count": 0, "status": "graph_error"}
            return {"unread_count": r.json().get("unreadItemCount", 0), "status": "connected"}
    except (TokenNotFoundError, TokenExpiredError):
        return {"unread_count": 0, "status": "not_connected"}
    except Exception as e:
        logger.warning(f"[email/unread-count] Failed: {e}")
        return {"unread_count": 0, "status": "error"}


async def get_worker_status(supabase, user_id: str, yacht_id: str) -> dict:
    r = supabase.table('email_watchers').select(
        'sync_status, last_sync_at, subscription_expires_at, last_sync_error, delta_link_inbox, sync_version, updated_at'
    ).eq('user_id', user_id).eq('yacht_id', yacht_id).eq('provider', 'microsoft_graph').limit(1).execute()

    if not r.data:
        return {'connected': False, 'sync_status': 'disconnected', 'last_sync_at': None, 'last_error': None, 'message': 'No email connection found'}

    w = r.data[0]
    sync_status = w.get('sync_status', 'unknown')
    return {
        'connected': sync_status not in ['disconnected', 'pending'],
        'sync_status': sync_status,
        'sync_version': w.get('sync_version', 'folder'),
        'last_sync_at': w.get('last_sync_at'),
        'subscription_expires_at': w.get('subscription_expires_at'),
        'last_error': w.get('last_sync_error'),
        'has_delta_link': bool(w.get('delta_link_inbox')),
        'updated_at': w.get('updated_at'),
    }


# ══════════════════════════════════════════════════════════════════════════════
# LINKS
# ══════════════════════════════════════════════════════════════════════════════

async def add_link(
    supabase, yacht_id: str, user_id: str, user_role: str,
    thread_id: str, object_type: str, object_id: str,
    reason: str, idempotency_key: Optional[str],
) -> dict:
    if idempotency_key:
        cached = await check_idempotency(supabase, yacht_id, idempotency_key, 'EMAIL_LINK_ADD')
        if cached:
            return {'link_id': cached.get('link_id'), 'status': cached.get('status', 'created'), 'cached': True}

    if not supabase.table('email_threads').select('id').eq('id', thread_id).eq('yacht_id', yacht_id).maybe_single().execute().data:
        raise HTTPException(status_code=404, detail="Thread not found or access denied")

    target_table = OBJECT_TYPE_TABLE_MAP.get(object_type)
    if target_table:
        try:
            if not supabase.table(target_table).select('id').eq('id', object_id).eq('yacht_id', yacht_id).maybe_single().execute().data:
                raise HTTPException(status_code=404, detail=f"{object_type.replace('_', ' ').title()} not found or access denied")
        except HTTPException:
            raise
        except Exception as e:
            logger.warning(f"[email/link/add] Target check failed (non-fatal): {e}")

    existing = supabase.table('email_links').select('id').eq('yacht_id', yacht_id).eq(
        'thread_id', thread_id
    ).eq('object_type', object_type).eq('object_id', object_id).eq('is_active', True).limit(1).execute()

    if existing.data:
        existing_id = existing.data[0]['id']
        await audit_link_action(
            supabase, yacht_id, user_id, 'EMAIL_LINK_ADD_DUPLICATE', existing_id,
            old_values={},
            new_values={'link_id': existing_id, 'status': 'already_exists',
                        'thread_id': thread_id, 'object_type': object_type, 'object_id': object_id},
            idempotency_key=idempotency_key, user_role=user_role,
        )
        return {'link_id': existing_id, 'status': 'already_exists'}

    insert_r = supabase.table('email_links').insert({
        'yacht_id': yacht_id, 'thread_id': thread_id, 'object_type': object_type,
        'object_id': object_id, 'confidence': 'user_confirmed', 'suggested_reason': reason,
        'suggested_at': utcnow(), 'accepted_at': utcnow(), 'accepted_by': user_id, 'is_active': True,
    }).execute()

    new_id = insert_r.data[0]['id'] if insert_r.data else None
    if not new_id:
        raise HTTPException(status_code=500, detail="Failed to create link")

    await audit_link_action(
        supabase, yacht_id, user_id, 'EMAIL_LINK_ADD', new_id,
        old_values={},
        new_values={'link_id': new_id, 'status': 'created', 'thread_id': thread_id,
                    'object_type': object_type, 'object_id': object_id, 'reason': reason},
        idempotency_key=idempotency_key, user_role=user_role,
    )
    logger.info(f"[email/link/add] Created: link={new_id[:8]} thread={thread_id[:8]} → {object_type}={object_id[:8]} user={user_id[:8]}")
    return {'link_id': new_id, 'status': 'created'}


async def accept_link(
    supabase, yacht_id: str, user_id: str, user_role: str,
    link_id: str, idempotency_key: Optional[str],
) -> dict:
    if idempotency_key:
        cached = await check_idempotency(supabase, yacht_id, idempotency_key, 'EMAIL_LINK_ACCEPT')
        if cached:
            return {'success': True, 'link_id': link_id, 'cached': True}

    link_r = supabase.table('email_links').select('*').eq('id', link_id).eq('yacht_id', yacht_id).eq('is_active', True).maybe_single().execute()
    if not link_r.data:
        raise HTTPException(status_code=404, detail="Link not found")

    link = link_r.data
    if link['confidence'] == 'user_confirmed':
        return {'success': True, 'link_id': link_id, 'already_accepted': True}
    if link['confidence'] != 'suggested':
        raise HTTPException(status_code=400, detail="Link is not in suggested state")

    supabase.table('email_links').update({
        'confidence': 'user_confirmed',
        'accepted_at': utcnow(),
        'accepted_by': user_id,
        'updated_at': utcnow(),
    }).eq('id', link_id).eq('yacht_id', yacht_id).execute()

    await audit_link_action(
        supabase, yacht_id, user_id, 'EMAIL_LINK_ACCEPT', link_id,
        old_values={'confidence': 'suggested'},
        new_values={'confidence': 'user_confirmed'},
        idempotency_key=idempotency_key, user_role=user_role,
    )
    return {'success': True, 'link_id': link_id}


async def change_link(
    supabase, yacht_id: str, user_id: str, user_role: str,
    link_id: str, new_object_type: str, new_object_id: str, idempotency_key: Optional[str],
) -> dict:
    if idempotency_key:
        cached = await check_idempotency(supabase, yacht_id, idempotency_key, 'EMAIL_LINK_CHANGE')
        if cached:
            return {'success': True, 'link_id': link_id, 'cached': True}

    link_r = supabase.table('email_links').select('*').eq('id', link_id).eq('yacht_id', yacht_id).eq('is_active', True).maybe_single().execute()
    if not link_r.data:
        raise HTTPException(status_code=404, detail="Link not found")

    old = link_r.data
    if old['object_type'] == new_object_type and old['object_id'] == new_object_id:
        return {'success': True, 'link_id': link_id, 'no_change': True}

    supabase.table('email_links').update({
        'object_type': new_object_type, 'object_id': new_object_id,
        'confidence': 'user_confirmed',
        'modified_at': utcnow(), 'modified_by': user_id, 'updated_at': utcnow(),
    }).eq('id', link_id).eq('yacht_id', yacht_id).execute()

    await audit_link_action(
        supabase, yacht_id, user_id, 'EMAIL_LINK_CHANGE', link_id,
        old_values={'object_type': old['object_type'], 'object_id': old['object_id']},
        new_values={'object_type': new_object_type, 'object_id': new_object_id},
        idempotency_key=idempotency_key, user_role=user_role,
    )
    return {'success': True, 'link_id': link_id}


async def remove_link(
    supabase, yacht_id: str, user_id: str, user_role: str,
    link_id: str, idempotency_key: Optional[str],
) -> dict:
    if idempotency_key:
        cached = await check_idempotency(supabase, yacht_id, idempotency_key, 'EMAIL_LINK_REMOVE')
        if cached:
            return {'success': True, 'link_id': link_id, 'cached': True}

    link_r = supabase.table('email_links').select('*').eq('id', link_id).eq('yacht_id', yacht_id).maybe_single().execute()
    if not link_r.data:
        raise HTTPException(status_code=404, detail="Link not found")

    old = link_r.data
    if not old.get('is_active', True):
        return {'success': True, 'link_id': link_id, 'already_removed': True}

    supabase.table('email_links').update({
        'is_active': False, 'removed_at': utcnow(), 'removed_by': user_id, 'updated_at': utcnow(),
    }).eq('id', link_id).eq('yacht_id', yacht_id).execute()

    await audit_link_action(
        supabase, yacht_id, user_id, 'EMAIL_LINK_REMOVE', link_id,
        old_values={'is_active': True, 'thread_id': old['thread_id'],
                    'object_type': old['object_type'], 'object_id': old['object_id']},
        new_values={'is_active': False},
        idempotency_key=idempotency_key, user_role=user_role,
    )
    return {'success': True, 'link_id': link_id}


async def reject_link(supabase, yacht_id: str, user_id: str, link_id: str) -> dict:
    link_r = supabase.table('email_links').select('*').eq('id', link_id).eq('yacht_id', yacht_id).eq('is_active', True).maybe_single().execute()
    if not link_r.data:
        raise HTTPException(status_code=404, detail="Link not found")

    if link_r.data['confidence'] != 'suggested':
        raise HTTPException(status_code=400, detail="Only suggested links can be rejected")

    supabase.table('email_links').update({
        'confidence': 'rejected', 'rejected_at': utcnow(), 'rejected_by': user_id, 'updated_at': utcnow(),
    }).eq('id', link_id).eq('yacht_id', yacht_id).execute()

    await audit_link_action(
        supabase, yacht_id, user_id, 'EMAIL_LINK_REJECT', link_id,
        old_values={'confidence': 'suggested'},
        new_values={'confidence': 'rejected'},
    )
    return {'success': True, 'link_id': link_id}


async def execute_action(
    supabase, yacht_id: str, user_id: str, user_role: str,
    action_name: str, message_id: Optional[str], thread_id: Optional[str],
    target_type: Optional[str], target_id: Optional[str],
    params: Dict[str, Any], idempotency_key: Optional[str],
) -> dict:
    from email_rag.triggers import TriggerContext, dispatch_trigger, apply_trigger_effects

    if idempotency_key:
        cached = await check_idempotency(supabase, yacht_id, idempotency_key, action_name)
        if cached:
            cached_result = cached.get('result', {})
            return {
                'success': cached_result.get('success', True),
                'action_name': action_name,
                'result': cached_result,
                'cached': True,
                'trigger': None,
            }

    precondition_errors = []
    if action_name in ('link_to_work_order', 'link_to_equipment', 'link_to_part'):
        if not thread_id:
            precondition_errors.append("thread_id is required")
        if not target_id:
            precondition_errors.append("target_id is required")
        if thread_id:
            if not supabase.table('email_threads').select('id').eq('id', thread_id).eq('yacht_id', yacht_id).maybe_single().execute().data:
                precondition_errors.append("Thread not found or access denied")
        if thread_id and target_id:
            existing = supabase.table('email_links').select('id').eq('yacht_id', yacht_id).eq(
                'thread_id', thread_id
            ).eq('object_id', target_id).eq('is_active', True).limit(1).execute()
            if existing.data:
                return {
                    'success': True, 'action_name': action_name,
                    'result': {'link_id': existing.data[0]['id'], 'already_linked': True},
                    'trigger': None,
                }
    elif action_name == 'create_work_order_from_email':
        if not params.get('title'):
            precondition_errors.append("title is required in params")

    if precondition_errors:
        raise HTTPException(status_code=400, detail="; ".join(precondition_errors))

    action_audit_id = str(_uuid_mod.uuid4())
    action_result: Dict[str, Any] = {'success': False, 'error': 'Unknown action'}

    if action_name in ('link_to_work_order', 'link_to_equipment', 'link_to_part'):
        obj_type = {'link_to_work_order': 'work_order', 'link_to_equipment': 'equipment', 'link_to_part': 'part'}[action_name]
        upsert = await upsert_email_link(
            supabase, yacht_id=yacht_id, thread_id=thread_id,
            object_type=obj_type, object_id=target_id, user_id=user_id,
            confidence='user_confirmed', suggested_reason='manual',
        )
        action_result = {'success': True, 'link_id': upsert.get('link_id')}

    elif action_name == 'create_work_order_from_email':
        wo = supabase.table('pms_work_orders').insert({
            'yacht_id': yacht_id,
            'title': params.get('title', 'Work Order from Email'),
            'priority': params.get('priority', 'medium'),
            'equipment_id': params.get('equipment_id'),
            'status': 'open',
            'source': 'email',
            'source_reference': message_id,
            'created_by': user_id,
        }).execute()
        action_result = {'success': True, 'work_order_id': wo.data[0]['id'] if wo.data else None}

    else:
        raise HTTPException(status_code=400, detail=f"Unknown action: {action_name}")

    supabase.table('pms_audit_log').insert({
        'yacht_id': yacht_id,
        'action': f'EMAIL_ACTION_{action_name.upper()}',
        'entity_type': 'email_action',
        'entity_id': message_id or thread_id or 'unknown',
        'user_id': user_id,
        'old_values': {},
        'new_values': {
            'action_name': action_name, 'target_type': target_type,
            'target_id': target_id, 'result': action_result,
        },
        'signature': {
            'timestamp': utcnow(), 'action_version': 'M5',
            'action_audit_id': action_audit_id, 'user_role': user_role,
            'idempotency_key': idempotency_key,
        },
    }).execute()

    trigger_result = None
    trigger_error = None

    if action_result.get('success'):
        ctx = TriggerContext(
            yacht_id=yacht_id, user_id=user_id, user_role=user_role,
            action_name=action_name, action_id=action_audit_id,
            message_id=message_id, thread_id=thread_id,
            target_type=target_type or 'work_order', target_id=target_id,
            success=True, result_data=action_result,
        )
        try:
            trigger_result = dispatch_trigger(ctx)
            if trigger_result and trigger_result.executed:
                effects = await asyncio.wait_for(
                    apply_trigger_effects(supabase, trigger_result),
                    timeout=TRIGGER_TIMEOUT_SECONDS,
                )
                logger.info(f"[email/action/execute] Trigger effects applied: {effects}")
        except asyncio.TimeoutError:
            trigger_error = "Trigger execution timed out"
            logger.error(f"[email/action/execute] Trigger timeout for {action_name}")
            try:
                supabase.table('pms_audit_log').insert({
                    'yacht_id': yacht_id, 'action': 'TRIGGER_DLQ',
                    'entity_type': 'trigger_failure', 'entity_id': action_audit_id,
                    'user_id': user_id, 'old_values': {},
                    'new_values': {'action_name': action_name, 'error': trigger_error},
                    'signature': {'timestamp': utcnow()},
                }).execute()
            except Exception:
                pass
        except Exception as te:
            trigger_error = str(te)
            logger.error(f"[email/action/execute] Trigger error: {te}")

    resp = {
        'success': action_result.get('success', False),
        'action_name': action_name,
        'action_audit_id': action_audit_id,
        'result': action_result,
        'trigger': trigger_result.to_dict() if trigger_result else None,
    }
    if trigger_error:
        resp['trigger_error'] = trigger_error
    return resp


async def save_attachment(
    supabase, user_id: str, yacht_id: str, user_role: str,
    message_id: str, attachment_id: str,
    target_folder: Optional[str], idempotency_key: Optional[str],
) -> dict:
    msg_hash = hashlib.md5(message_id.encode()).hexdigest()[:12]
    att_hash = hashlib.md5(attachment_id.encode()).hexdigest()[:12]
    path_prefix = f"{yacht_id}/email-attachments/{msg_hash}_{att_hash}"

    if idempotency_key:
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

    msg_r = supabase.table('email_messages').select('id, thread_id').eq(
        'provider_message_id', message_id
    ).eq('yacht_id', yacht_id).maybe_single().execute()
    if not msg_r.data:
        raise HTTPException(status_code=404, detail="Message not found")

    try:
        read_client = create_read_client(supabase, user_id, yacht_id)
        attachment = await read_client.get_attachment(message_id, attachment_id)

        if not attachment:
            raise HTTPException(status_code=404, detail="Attachment not found")

        content_bytes = attachment.get('contentBytes')
        if not content_bytes:
            raise HTTPException(status_code=400, detail="Attachment has no content")

        file_data = base64.b64decode(content_bytes)

        if len(file_data) > MAX_EVIDENCE_SIZE_BYTES:
            raise HTTPException(status_code=413, detail=f"File too large. Maximum size is {MAX_EVIDENCE_SIZE_BYTES // (1024*1024)}MB")

        original_filename = sanitize_filename(attachment.get('name', 'attachment'))
        _, ext = os.path.splitext(original_filename)
        ext = ext.lower()

        if ext not in ALLOWED_EVIDENCE_EXTENSIONS:
            raise HTTPException(status_code=400, detail=f"File type '{ext}' not allowed.")

        content_type = attachment.get('contentType', 'application/octet-stream')
        if content_type not in ALLOWED_EVIDENCE_MIME_TYPES:
            raise HTTPException(status_code=400, detail=f"Content type '{content_type}' not allowed")

        safe_filename = f"{_uuid_mod.uuid4()}{ext}"
        storage_path = f"{path_prefix}/{safe_filename}"

        supabase.storage.from_('documents').upload(storage_path, file_data, {'content-type': content_type})

        doc_r = supabase.table('doc_yacht_library').insert({
            'yacht_id': yacht_id, 'document_name': original_filename,
            'document_path': storage_path, 'document_type': content_type, 'user_id': user_id,
        }).execute()
        document_id = doc_r.data[0]['id'] if doc_r.data else None

        try:
            supabase.table('pms_audit_log').insert({
                'yacht_id': yacht_id, 'action': 'EMAIL_EVIDENCE_SAVED',
                'entity_type': 'document', 'entity_id': document_id, 'user_id': user_id,
                'old_values': {},
                'new_values': {
                    'filename': original_filename, 'content_type': content_type,
                    'file_size': len(file_data), 'email_message_id': message_id,
                },
                'signature': {'timestamp': utcnow(), 'action_version': 'M4',
                              'user_role': user_role, 'idempotency_key': idempotency_key},
            }).execute()
        except Exception as ae:
            logger.error(f"[email/evidence/save-attachment] Audit log failed: {ae}")

        logger.info(f"[email/evidence/save-attachment] Saved: doc={document_id[:8] if document_id else 'N/A'} size={len(file_data)} type={content_type}")

        auto_linked = []
        thread_id = msg_r.data.get('thread_id')
        if document_id and thread_id:
            try:
                thread_links = supabase.table('email_links').select('object_type, object_id').eq(
                    'yacht_id', yacht_id
                ).eq('thread_id', thread_id).eq('is_active', True).in_(
                    'confidence', ['deterministic', 'user_confirmed']
                ).execute()
                for link in (thread_links.data or []):
                    try:
                        supabase.table('email_attachment_object_links').insert({
                            'yacht_id': yacht_id, 'document_id': document_id,
                            'object_type': link['object_type'], 'object_id': link['object_id'],
                            'link_reason': 'auto_from_thread',
                            'source_context': {'email_thread_id': thread_id, 'email_message_id': message_id},
                            'is_active': True, 'created_by': user_id,
                        }).execute()
                        auto_linked.append({'object_type': link['object_type'], 'object_id': link['object_id']})
                    except Exception as le:
                        logger.warning(f"[email/evidence/save-attachment] Auto-link skipped: {le}")
            except Exception as ae:
                logger.warning(f"[email/evidence/save-attachment] Auto-link lookup failed: {ae}")

        return {'success': True, 'document_id': document_id, 'storage_path': storage_path, 'auto_linked': auto_linked or None}

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


# ══════════════════════════════════════════════════════════════════════════════
# SYNC
# ══════════════════════════════════════════════════════════════════════════════

async def sync_now(supabase, user_id: str, yacht_id: str, full_resync: bool, upgrade_to_mailbox: bool) -> dict:
    watcher_r = supabase.table('email_watchers').select('*').eq(
        'user_id', user_id
    ).eq('yacht_id', yacht_id).eq('provider', 'microsoft_graph').maybe_single().execute()

    if not watcher_r.data:
        raise HTTPException(status_code=400, detail="No email watcher configured")

    watcher = watcher_r.data

    if full_resync:
        supabase.table('email_watchers').update({
            'delta_link_inbox': None, 'delta_link_sent': None, 'delta_link': None,
        }).eq('id', watcher['id']).execute()
        watcher.update({'delta_link_inbox': None, 'delta_link_sent': None, 'delta_link': None})

    if upgrade_to_mailbox:
        supabase.table('email_watchers').update({
            'sync_version': 'mailbox', 'delta_link': None,
            'delta_link_inbox': None, 'delta_link_sent': None,
        }).eq('id', watcher['id']).execute()
        watcher.update({'sync_version': 'mailbox', 'delta_link': None,
                        'delta_link_inbox': None, 'delta_link_sent': None})

    try:
        read_client = create_read_client(supabase, user_id, yacht_id)
        stats = {'threads_created': 0, 'messages_created': 0, 'errors': [], 'full_resync': full_resync}
        max_messages = 500 if full_resync else 100

        for folder in ('inbox', 'sent'):
            delta_link = watcher.get(f'delta_link_{folder}')
            total = 0
            try:
                while total < max_messages:
                    result = await read_client.list_messages(
                        folder=folder,
                        top=min(100, max_messages - total),
                        delta_link=delta_link,
                        select=['id', 'conversationId', 'subject', 'from', 'toRecipients',
                                'ccRecipients', 'receivedDateTime', 'sentDateTime',
                                'hasAttachments', 'internetMessageId', 'bodyPreview'],
                    )
                    messages = result.get('messages', [])
                    if not messages:
                        break
                    for msg in messages:
                        try:
                            await _process_message(supabase, yacht_id, msg, folder)
                            stats['messages_created'] += 1
                            total += 1
                        except Exception as e:
                            stats['errors'].append(f"Message {msg.get('id')}: {e}")
                    new_delta = result.get('delta_link')
                    if new_delta:
                        supabase.table('email_watchers').update({f'delta_link_{folder}': new_delta}).eq('id', watcher['id']).execute()
                        break
                    elif result.get('next_link'):
                        delta_link = result['next_link']
                    else:
                        break
            except Exception as e:
                stats['errors'].append(f"Folder {folder}: {e}")

        supabase.table('email_watchers').update({
            'last_sync_at': utcnow(),
            'last_sync_error': stats['errors'][-1] if stats['errors'] else None,
            'sync_status': 'degraded' if stats['errors'] else 'active',
        }).eq('id', watcher['id']).execute()

        return {'success': True, 'stats': stats}

    except TokenNotFoundError:
        raise outlook_auth_error("outlook_not_connected", "Email not connected")
    except TokenExpiredError:
        raise outlook_auth_error("outlook_token_expired", "Email connection expired")
    except TokenRevokedError:
        raise outlook_auth_error("outlook_token_revoked", "Email connection revoked")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[email/sync/now] Error: {e}")
        raise HTTPException(status_code=500, detail=f"Sync failed: {e}")


async def sync_all_folders(supabase, user_id: str, yacht_id: str, max_per_folder: int) -> dict:
    try:
        read_client = create_read_client(supabase, user_id, yacht_id)
        token = await read_client._get_token()
        stats = {'folders_synced': 0, 'messages_created': 0, 'messages_skipped': 0, 'errors': [], 'folder_stats': {}}

        async with httpx.AsyncClient() as client:
            folders_r = await client.get(
                "https://graph.microsoft.com/v1.0/me/mailFolders",
                headers={"Authorization": f"Bearer {token}"}, timeout=30.0,
            )
            if folders_r.status_code != 200:
                raise HTTPException(status_code=502, detail="Failed to list folders")

            for folder in folders_r.json().get('value', []):
                folder_name = folder.get('displayName', 'Unknown')
                folder_id = folder.get('id')
                fs = {'synced': 0, 'skipped': 0, 'errors': 0}
                try:
                    msgs_r = await client.get(
                        f"https://graph.microsoft.com/v1.0/me/mailFolders/{folder_id}/messages"
                        f"?$select=id,conversationId,subject,from,toRecipients,ccRecipients,"
                        f"receivedDateTime,sentDateTime,hasAttachments,internetMessageId,bodyPreview,webLink"
                        f"&$top={max_per_folder}&$orderby=receivedDateTime desc",
                        headers={"Authorization": f"Bearer {token}"}, timeout=60.0,
                    )
                    if msgs_r.status_code == 200:
                        is_sent = folder_name.lower() in ('sent items', 'sent', 'sentitems')
                        folder_type = 'sent' if is_sent else 'inbox'
                        for msg in msgs_r.json().get('value', []):
                            try:
                                await _process_message(supabase, yacht_id, msg, folder_type)
                                fs['synced'] += 1
                                stats['messages_created'] += 1
                            except Exception as e:
                                if 'duplicate' in str(e).lower() or 'already exists' in str(e).lower():
                                    fs['skipped'] += 1
                                    stats['messages_skipped'] += 1
                                else:
                                    fs['errors'] += 1
                                    stats['errors'].append(f"{folder_name}: {str(e)[:50]}")
                    stats['folders_synced'] += 1
                    stats['folder_stats'][folder_name] = fs
                except Exception as e:
                    stats['errors'].append(f"Folder {folder_name}: {str(e)[:100]}")

        return {'success': True, 'stats': stats}

    except TokenNotFoundError:
        raise outlook_auth_error("outlook_not_connected", "Email not connected")
    except TokenExpiredError:
        raise outlook_auth_error("outlook_token_expired", "Email connection expired")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[email/sync/all-folders] Error: {e}")
        raise HTTPException(status_code=500, detail=f"Sync failed: {e}")


async def backfill_embeddings(supabase, yacht_id: str, limit: int) -> dict:
    from services.email_embedding_service import EmailEmbeddingUpdater
    updater = EmailEmbeddingUpdater(supabase, yacht_id)
    if not updater.embedding_service.is_available():
        raise HTTPException(status_code=503, detail="Embedding service not available - check OPENAI_API_KEY")
    stats = await updater.backfill_embeddings(limit=limit)
    logger.info(f"[email/backfill-embeddings] yacht={yacht_id[:8]} stats={stats}")
    return {'success': True, 'yacht_id': yacht_id, 'stats': stats}


async def backfill_weblinks(supabase, user_id: str, yacht_id: str, limit: int) -> dict:
    msgs_r = supabase.table('email_messages').select('id, provider_message_id').eq(
        'yacht_id', yacht_id
    ).is_('web_link', 'null').limit(limit).execute()

    messages = msgs_r.data or []
    if not messages:
        return {'success': True, 'yacht_id': yacht_id, 'stats': {'processed': 0, 'updated': 0, 'skipped': 0, 'failed': 0, 'message': 'No messages need backfill'}}

    try:
        read_client = create_read_client(supabase, user_id, yacht_id)
        stats = {'processed': 0, 'updated': 0, 'skipped': 0, 'failed': 0}
        for msg in messages:
            stats['processed'] += 1
            try:
                content = await read_client.get_message_content(msg['provider_message_id'])
                weblink = content.get('webLink')
                if weblink:
                    supabase.table('email_messages').update({'web_link': weblink}).eq('id', msg['id']).execute()
                    stats['updated'] += 1
                else:
                    stats['skipped'] += 1
            except Exception as e:
                stats['failed'] += 1
                logger.warning(f"[email/backfill-weblinks] Failed for {msg['provider_message_id'][:20]}...: {e}")
        return {'success': True, 'yacht_id': yacht_id, 'stats': stats}

    except TokenNotFoundError:
        raise outlook_auth_error("outlook_not_connected", "Email not connected. Please connect Outlook first.")
    except TokenExpiredError:
        raise outlook_auth_error("outlook_token_expired", "Email connection expired. Please reconnect.")
    except TokenRevokedError:
        raise outlook_auth_error("outlook_token_revoked", "Email connection revoked. Please reconnect.")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[email/backfill-weblinks] Error: {e}")
        raise HTTPException(status_code=500, detail=f"Backfill failed: {e}")


async def get_entity_ledger(supabase, yacht_id: str, entity_type: str, entity_id: str, limit: int, offset: int) -> dict:
    result = supabase.table('pms_audit_log').select(
        'id, action, entity_type, entity_id, user_id, old_values, new_values, signature, created_at',
        count='exact'
    ).eq('yacht_id', yacht_id).eq('entity_type', entity_type).eq(
        'entity_id', entity_id
    ).order('created_at', desc=True).order('id', desc=False).range(offset, offset + limit - 1).execute()

    direct_count = result.count or 0
    entries = [
        {'id': r['id'], 'event_type': r['action'], 'timestamp': r['created_at'],
         'actor_id': r['user_id'], 'details': r['new_values'], 'metadata': r.get('signature', {})}
        for r in (result.data or [])
    ]

    remaining = limit - len(entries)
    related_entries = []
    related_count = 0

    if remaining > 0:
        related_r = supabase.table('pms_audit_log').select(
            'id, action, entity_type, entity_id, user_id, old_values, new_values, signature, created_at',
            count='exact'
        ).eq('yacht_id', yacht_id).eq(
            'new_values->>related_entity_type', entity_type
        ).eq('new_values->>related_entity_id', entity_id).order(
            'created_at', desc=True
        ).order('id', desc=False).limit(remaining).execute()

        related_count = related_r.count or 0
        for r in (related_r.data or []):
            related_entries.append({
                'id': r['id'], 'event_type': r['action'], 'timestamp': r['created_at'],
                'actor_id': r['user_id'], 'source_entity_type': r['entity_type'],
                'source_entity_id': r['entity_id'], 'details': r['new_values'],
                'metadata': r.get('signature', {}), 'is_related': True,
            })

    all_entries = sorted(entries + related_entries, key=lambda x: (x['timestamp'], x['id']), reverse=True)[:limit]
    total_count = direct_count + related_count

    logger.info(f"[email/ledger] entity={entity_type}:{entity_id[:8]} entries={len(all_entries)} total={total_count}")
    return {
        'entity_type': entity_type, 'entity_id': entity_id,
        'entries': all_entries, 'count': len(all_entries),
        'total_count': total_count, 'offset': offset, 'limit': limit,
        'has_more': offset + len(all_entries) < total_count,
    }


# ══════════════════════════════════════════════════════════════════════════════
# DEBUG
# ══════════════════════════════════════════════════════════════════════════════

async def debug_search_folders(supabase, user_id: str, yacht_id: str, q: str) -> dict:
    try:
        read_client = create_read_client(supabase, user_id, yacht_id)
        token = await read_client._get_token()
        results: Dict[str, Any] = {'query': q, 'folders': {}, 'total_found': 0}

        async with httpx.AsyncClient() as client:
            folders_r = await client.get(
                "https://graph.microsoft.com/v1.0/me/mailFolders",
                headers={"Authorization": f"Bearer {token}"}, timeout=30.0,
            )
            if folders_r.status_code != 200:
                raise HTTPException(status_code=502, detail="Failed to list folders")

            folders = folders_r.json().get('value', [])
            results['folder_count'] = len(folders)

            for folder in folders:
                folder_name = folder.get('displayName', 'Unknown')
                msgs_r = await client.get(
                    f"https://graph.microsoft.com/v1.0/me/mailFolders/{folder.get('id')}/messages"
                    f"?$select=id,subject,from,receivedDateTime,conversationId&$top=100&$orderby=receivedDateTime desc",
                    headers={"Authorization": f"Bearer {token}"}, timeout=30.0,
                )
                if msgs_r.status_code == 200:
                    matching = [
                        {
                            'subject': m.get('subject', ''),
                            'from': m.get('from', {}).get('emailAddress', {}).get('address', ''),
                            'received': m.get('receivedDateTime', ''),
                            'conversationId': ((m.get('conversationId', 'NONE') or 'NONE')[:50] + '...' if m.get('conversationId') else 'NONE'),
                        }
                        for m in msgs_r.json().get('value', [])
                        if q.lower() in (m.get('subject', '') or '').lower()
                    ]
                    if matching:
                        results['folders'][folder_name] = {'count': len(matching), 'messages': matching}
                        results['total_found'] += len(matching)

        return results

    except TokenNotFoundError:
        raise outlook_auth_error("outlook_not_connected", "Email not connected")
    except TokenExpiredError:
        raise outlook_auth_error("outlook_token_expired", "Email connection expired")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[email/debug/search-folders] Error: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {e}")


async def debug_graph_me(supabase, user_id: str, yacht_id: str) -> dict:
    try:
        read_client = create_read_client(supabase, user_id, yacht_id)
        token = await read_client._get_token()

        async with httpx.AsyncClient() as client:
            me_r = await client.get("https://graph.microsoft.com/v1.0/me", headers={"Authorization": f"Bearer {token}"}, timeout=30.0)
            if me_r.status_code != 200:
                raise HTTPException(status_code=502, detail=f"Graph /me error: {me_r.status_code}")
            me_data = me_r.json()

            inbox_r = await client.get("https://graph.microsoft.com/v1.0/me/mailFolders/inbox", headers={"Authorization": f"Bearer {token}"}, timeout=30.0)
            inbox_data = inbox_r.json() if inbox_r.status_code == 200 else {}

        return {
            'profile': {
                'displayName': me_data.get('displayName'),
                'mail': me_data.get('mail'),
                'userPrincipalName': me_data.get('userPrincipalName'),
                'id': me_data.get('id'),
            },
            'inbox_folder': {
                'displayName': inbox_data.get('displayName'),
                'totalItemCount': inbox_data.get('totalItemCount'),
                'unreadItemCount': inbox_data.get('unreadItemCount'),
            },
        }

    except TokenNotFoundError:
        raise outlook_auth_error("outlook_not_connected", "Email not connected")
    except TokenExpiredError:
        raise outlook_auth_error("outlook_token_expired", "Email connection expired")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[email/debug/graph-me] Error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed: {e}")


async def debug_inbox_compare(supabase, user_id: str, yacht_id: str) -> dict:
    try:
        read_client = create_read_client(supabase, user_id, yacht_id)
        token = await read_client._get_token()

        async with httpx.AsyncClient() as client:
            r = await client.get(
                "https://graph.microsoft.com/v1.0/me/mailFolders/inbox/messages"
                "?$select=id,conversationId,subject,from,receivedDateTime,hasAttachments,bodyPreview"
                "&$top=200&$orderby=receivedDateTime desc",
                headers={"Authorization": f"Bearer {token}"}, timeout=60.0,
            )
            if r.status_code != 200:
                raise HTTPException(status_code=502, detail=f"Graph API error: {r.status_code} - {r.text[:200]}")
            graph_messages = r.json().get('value', [])

        db_ids = {m['provider_message_id'] for m in (supabase.table('email_messages').select('provider_message_id').eq('yacht_id', yacht_id).execute().data or [])}

        in_graph = []
        missing = []
        for msg in graph_messages:
            msg_id = msg.get('id')
            conv_id = msg.get('conversationId', '')
            info = {
                'id': (msg_id[:30] + '...' if len(msg_id) > 30 else msg_id) if msg_id else None,
                'subject': msg.get('subject', '(no subject)'),
                'from': msg.get('from', {}).get('emailAddress', {}).get('address', ''),
                'received': msg.get('receivedDateTime', ''),
                'hasAttachments': msg.get('hasAttachments', False),
                'conversationId': (conv_id[:30] + '...' if len(conv_id) > 30 else conv_id) if conv_id else None,
                'preview': (msg.get('bodyPreview', '') or '')[:100],
            }
            in_graph.append(info)
            if msg_id not in db_ids:
                missing.append(info)

        return {
            'graph_inbox_count': len(graph_messages),
            'db_message_count': len(db_ids),
            'missing_count': len(missing),
            'missing_from_db': missing,
            'all_graph_inbox': in_graph,
        }

    except TokenNotFoundError:
        raise outlook_auth_error("outlook_not_connected", "Email not connected")
    except TokenExpiredError:
        raise outlook_auth_error("outlook_token_expired", "Email connection expired")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[email/debug/inbox-compare] Error: {e}")
        raise HTTPException(status_code=500, detail=f"Compare failed: {e}")


async def debug_thread_yacht_check(supabase, user_yacht_id: str, tenant_key_alias: str, thread_ids_str: str) -> dict:
    ids = [t.strip() for t in thread_ids_str.split(',') if t.strip()]
    results = []
    for thread_id in ids[:10]:
        try:
            r = supabase.table('email_threads').select('id, yacht_id, latest_subject, created_at').eq('id', thread_id).limit(1).execute()
            if r.data:
                thread = r.data[0]
                thread_yacht = thread.get('yacht_id')
                results.append({
                    'thread_id': thread_id, 'exists': True,
                    'thread_yacht_id': thread_yacht, 'user_yacht_id': user_yacht_id,
                    'match': thread_yacht == user_yacht_id,
                    'subject': (thread.get('latest_subject') or 'N/A')[:50],
                })
            else:
                results.append({'thread_id': thread_id, 'exists': False, 'thread_yacht_id': None,
                                'user_yacht_id': user_yacht_id, 'match': False, 'error': 'Thread not found in database'})
        except Exception as e:
            results.append({'thread_id': thread_id, 'exists': False, 'error': str(e)})

    mismatches = [r for r in results if r.get('exists') and not r.get('match')]
    not_found = [r for r in results if not r.get('exists')]
    return {
        'user_yacht_id': user_yacht_id, 'tenant_key_alias': tenant_key_alias,
        'checked_count': len(results), 'mismatch_count': len(mismatches),
        'not_found_count': len(not_found), 'results': results,
        'diagnosis': (
            'YACHT_ID_MISMATCH: Threads exist but belong to different yacht' if mismatches else
            'THREADS_NOT_FOUND: Threads do not exist in this tenant database' if not_found else
            'OK: All threads match user yacht_id'
        ),
    }


async def debug_force_sync_missing(supabase, user_id: str, yacht_id: str) -> dict:
    try:
        read_client = create_read_client(supabase, user_id, yacht_id)
        token = await read_client._get_token()
        stats = {'checked': 0, 'synced': 0, 'already_existed': 0, 'errors': [], 'synced_subjects': []}

        async with httpx.AsyncClient() as client:
            r = await client.get(
                "https://graph.microsoft.com/v1.0/me/mailFolders/inbox/messages"
                "?$select=id,conversationId,subject,from,toRecipients,ccRecipients,"
                "receivedDateTime,sentDateTime,hasAttachments,internetMessageId,bodyPreview,webLink"
                "&$top=200&$orderby=receivedDateTime desc",
                headers={"Authorization": f"Bearer {token}"}, timeout=60.0,
            )
            if r.status_code != 200:
                raise HTTPException(status_code=502, detail="Graph API error")
            graph_messages = r.json().get('value', [])
            stats['checked'] = len(graph_messages)

        existing_ids = {m['provider_message_id'] for m in (supabase.table('email_messages').select('provider_message_id').eq('yacht_id', yacht_id).execute().data or [])}

        for msg in graph_messages:
            msg_id = msg.get('id')
            if msg_id in existing_ids:
                stats['already_existed'] += 1
                continue
            try:
                await _process_message(supabase, yacht_id, msg, 'inbox')
                stats['synced'] += 1
                stats['synced_subjects'].append(msg.get('subject', '(no subject)'))
            except Exception as e:
                err = str(e)
                if 'duplicate' not in err.lower():
                    stats['errors'].append(f"{msg.get('subject', 'unknown')[:30]}: {err[:50]}")
                else:
                    stats['already_existed'] += 1

        return {'success': True, 'stats': stats}

    except TokenNotFoundError:
        raise outlook_auth_error("outlook_not_connected", "Email not connected")
    except TokenExpiredError:
        raise outlook_auth_error("outlook_token_expired", "Email connection expired")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[email/debug/force-sync-missing] Error: {e}")
        raise HTTPException(status_code=500, detail=f"Force sync failed: {e}")
