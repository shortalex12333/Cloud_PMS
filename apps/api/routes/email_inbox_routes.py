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

import json
import hashlib
import time
import logging
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException

from middleware.auth import get_authenticated_user
from integrations.supabase import get_tenant_client
from integrations.feature_flags import check_email_feature
from integrations.graph_client import (
    create_read_client,
    TokenNotFoundError,
    TokenExpiredError,
)
from services.email_search_service import (
    _embedding_cache,
    MIN_FREE_TEXT_LENGTH,
    search_email_threads,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["email"])


# ── GET /search ──────────────────────────────────────────────────────────────

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
    """
    Hybrid semantic + entity search for emails with operator support (M2).

    Operators: from:, to:, subject:, has:attachment, before:, after:, in:work_order:<id>, thread:<id>
    Scoring: vector similarity (70%) + entity keyword (30%).
    Tenant-scoped by yacht_id from auth context.
    """
    start_time = time.time()

    enabled, error_msg = check_email_feature('search')
    if not enabled:
        raise HTTPException(status_code=503, detail=error_msg)

    if not q or not q.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    yacht_id = auth['yacht_id']
    user_id = auth.get('user_id', 'unknown')
    supabase = get_tenant_client(auth['tenant_key_alias'])

    telemetry = {
        'parse_ms': 0, 'embed_ms': 0, 'search_ms': 0, 'total_ms': 0,
        'operators_count': 0, 'keywords_count': 0, 'results_count': 0,
        'zero_results': False, 'parse_warnings': 0,
        'embed_skipped': False, 'embed_cached': False,
    }

    try:
        parse_start = time.time()
        from email_rag.query_parser import prepare_query_for_search
        parsed = prepare_query_for_search(q)
        telemetry['parse_ms'] = int((time.time() - parse_start) * 1000)
        telemetry['operators_count'] = parsed['operators_count']
        telemetry['keywords_count'] = len(parsed['keywords'])
        telemetry['parse_warnings'] = len(parsed['warnings'])

        logger.info(
            f"[email/search] yacht={yacht_id[:8]} operators={parsed['operators_count']} "
            f"keywords={len(parsed['keywords'])} warnings={len(parsed['warnings'])}"
        )

        embed_start = time.time()
        free_text = parsed['free_text'].strip() if parsed['free_text'] else ''
        embedding = None

        subject_filter = parsed['filters'].get('p_subject', '')
        subject_has_phrase = subject_filter and ' ' in subject_filter

        should_skip_embed = (
            len(free_text) < MIN_FREE_TEXT_LENGTH
            and parsed['operators_count'] > 0
            and not subject_has_phrase
        )

        if should_skip_embed:
            embedding = [0.0] * 1536
            telemetry['embed_skipped'] = True
            logger.info("[email/search] Skipping embedding - operator-only query")
        else:
            search_text = free_text if free_text else q
            embedding = _embedding_cache.get(search_text, yacht_id, user_id)

            if embedding:
                telemetry['embed_cached'] = True
                logger.debug("[email/search] Cache hit for query")
            else:
                from email_rag.embedder import generate_embedding_sync
                embedding = generate_embedding_sync(search_text)
                if embedding:
                    _embedding_cache.set(search_text, yacht_id, user_id, embedding)

        telemetry['embed_ms'] = int((time.time() - embed_start) * 1000)

        if not embedding:
            logger.warning("[email/search] No embedding available; degrading to entity-only search")
            embedding = [0.0] * 1536
            telemetry['embed_skipped'] = True

        effective_threshold = 0.0 if telemetry['embed_skipped'] else threshold

        user_email = auth.get('email', '')
        user_email_hash = hashlib.sha256(user_email.lower().encode()).hexdigest() if user_email else None

        params = {
            'p_yacht_id': yacht_id,
            'p_embedding': embedding,
            'p_entity_keywords': parsed['keywords'] if parsed['keywords'] else [],
            'p_limit': min(limit, 100),
            'p_similarity_threshold': effective_threshold,
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

        search_start = time.time()
        result = supabase.rpc('search_email_hybrid', params).execute()
        telemetry['search_ms'] = int((time.time() - search_start) * 1000)
        telemetry['results_count'] = len(result.data or [])
        telemetry['zero_results'] = telemetry['results_count'] == 0

        results = []
        for row in (result.data or []):
            score_obj = {
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

        telemetry['total_ms'] = int((time.time() - start_time) * 1000)

        logger.info(
            f"[email/search/telemetry] yacht={yacht_id[:8]} total_ms={telemetry['total_ms']} "
            f"parse_ms={telemetry['parse_ms']} embed_ms={telemetry['embed_ms']} "
            f"search_ms={telemetry['search_ms']} results={telemetry['results_count']} "
            f"operators={telemetry['operators_count']} zero_results={telemetry['zero_results']} "
            f"embed_skipped={telemetry['embed_skipped']} embed_cached={telemetry['embed_cached']}"
        )

        if telemetry['total_ms'] > 500:
            logger.warning(
                f"[email/search/slow] yacht={yacht_id[:8]} total_ms={telemetry['total_ms']} "
                f"search_ms={telemetry['search_ms']} operators={telemetry['operators_count']}"
            )

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
            'telemetry': {
                'total_ms': telemetry['total_ms'],
                'search_ms': telemetry['search_ms'],
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        tb_str = traceback.format_exc()
        logger.error(f"[email/search] Error: {e}\n{tb_str}")
        telemetry['total_ms'] = int((time.time() - start_time) * 1000)
        logger.error(f"[email/search/error] yacht={yacht_id[:8]} total_ms={telemetry['total_ms']} error={str(e)[:200]}")
        raise HTTPException(status_code=500, detail=f"Search failed: {type(e).__name__}: {str(e)[:100]}")


# ── GET /inbox ───────────────────────────────────────────────────────────────

@router.get("/inbox")
async def get_inbox_threads(
    page: int = 1,
    page_size: int = 20,
    linked: bool = False,
    q: str = None,
    direction: str = None,
    auth: dict = Depends(get_authenticated_user),
):
    """
    Get email threads for the inbox view.

    linked=false (default): unlinked threads only.
    q: hybrid search (SQL text + vector if embeddings exist).
    direction: 'inbound', 'outbound', or None for both.
    """
    enabled, error_msg = check_email_feature('related')
    if not enabled:
        raise HTTPException(status_code=503, detail=error_msg)

    yacht_id = auth['yacht_id']
    user_id = auth['user_id']
    supabase = get_tenant_client(auth['tenant_key_alias'])

    try:
        offset = (page - 1) * page_size

        watcher_result = supabase.table('email_watchers').select('id').eq(
            'user_id', user_id
        ).eq('yacht_id', yacht_id).eq('sync_status', 'active').limit(1).execute()

        watcher_id = watcher_result.data[0]['id'] if watcher_result.data else None

        if q and len(q) >= 2:
            return await search_email_threads(
                supabase, yacht_id, user_id, q, direction, page, page_size, linked, watcher_id
            )

        base_query = supabase.table('email_threads').select(
            'id, yacht_id, watcher_id, provider_conversation_id, latest_subject, message_count, '
            'has_attachments, source, last_activity_at, created_at, last_inbound_at, last_outbound_at, is_read',
            count='exact'
        ).eq('yacht_id', yacht_id)

        if direction == 'inbound':
            base_query = base_query.not_.is_('last_inbound_at', 'null')
        elif direction == 'outbound':
            base_query = base_query.not_.is_('last_outbound_at', 'null')

        if linked:
            result = base_query.order('last_activity_at', desc=True).range(offset, offset + page_size - 1).execute()
        else:
            result = None
            try:
                result = supabase.rpc('get_unlinked_email_threads', {
                    'p_yacht_id': yacht_id,
                    'p_limit': page_size,
                    'p_offset': offset,
                    'p_search': '',
                }).execute()
            except Exception as rpc_err:
                logger.debug(f"[email/inbox] RPC not available, using fallback: {rpc_err}")
                result = None

            if not result or not result.data:
                fallback_query = supabase.table('email_threads').select(
                    'id, yacht_id, watcher_id, provider_conversation_id, latest_subject, message_count, '
                    'has_attachments, source, last_activity_at, created_at, last_inbound_at, last_outbound_at, is_read'
                ).eq('yacht_id', yacht_id)

                if direction == 'inbound':
                    fallback_query = fallback_query.not_.is_('last_inbound_at', 'null')
                elif direction == 'outbound':
                    fallback_query = fallback_query.not_.is_('last_outbound_at', 'null')

                all_threads = fallback_query.order('last_activity_at', desc=True).limit(100).execute()

                linked_result = supabase.table('email_links').select('thread_id').eq(
                    'yacht_id', yacht_id
                ).eq('is_active', True).execute()

                linked_ids = {l['thread_id'] for l in (linked_result.data or [])}
                unlinked = [t for t in (all_threads.data or []) if t['id'] not in linked_ids]

                class _FallbackResult:
                    def __init__(self, data, count):
                        self.data = data
                        self.count = count

                result = _FallbackResult(
                    data=unlinked[offset:offset + page_size],
                    count=len(unlinked),
                )

        threads = result.data or []
        total = result.count if hasattr(result, 'count') and result.count else len(threads)

        return {
            'threads': threads,
            'total': total,
            'page': page,
            'page_size': page_size,
            'has_more': offset + len(threads) < total,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[email/inbox] Error: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch inbox")


# ── GET /related ─────────────────────────────────────────────────────────────

@router.get("/related")
async def get_related_threads(
    object_type: str,
    object_id: str,
    auth: dict = Depends(get_authenticated_user),
):
    """Get email threads linked to an object. Tenant-scoped by yacht_id."""
    from services.email_link_service import VALID_LINK_OBJECT_TYPES

    enabled, error_msg = check_email_feature('related')
    if not enabled:
        raise HTTPException(status_code=503, detail=error_msg)

    yacht_id = auth['yacht_id']
    supabase = get_tenant_client(auth['tenant_key_alias'])

    if object_type not in VALID_LINK_OBJECT_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid object_type. Must be one of: {VALID_LINK_OBJECT_TYPES}")

    try:
        links_result = supabase.table('email_links').select(
            'id, thread_id, confidence, suggested_reason, accepted_at, accepted_by'
        ).eq('yacht_id', yacht_id).eq('object_type', object_type).eq(
            'object_id', object_id
        ).eq('is_active', True).execute()

        if not links_result.data:
            return {'threads': [], 'count': 0}

        thread_ids = [link['thread_id'] for link in links_result.data]
        threads_result = supabase.table('email_threads').select(
            'id, provider_conversation_id, latest_subject, message_count, has_attachments, source, last_activity_at'
        ).eq('yacht_id', yacht_id).in_('id', thread_ids).order('last_activity_at', desc=True).execute()

        link_map = {link['thread_id']: link for link in links_result.data}
        threads = [
            {
                **thread,
                'link_id': link_map.get(thread['id'], {}).get('id'),
                'confidence': link_map.get(thread['id'], {}).get('confidence'),
                'suggested_reason': link_map.get(thread['id'], {}).get('suggested_reason'),
                'accepted': link_map.get(thread['id'], {}).get('accepted_at') is not None,
            }
            for thread in (threads_result.data or [])
        ]

        return {'threads': threads, 'count': len(threads)}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[email/related] Error: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch related threads")


# ── GET /focus/{message_id} ───────────────────────────────────────────────────

@router.get("/focus/{message_id}")
async def get_message_focus(
    message_id: str,
    auth: dict = Depends(get_authenticated_user),
):
    """
    Get focused view of a message with available micro-actions (M4).

    Returns email metadata, extracted entities, and available micro-actions.
    """
    enabled, error_msg = check_email_feature('focus')
    if not enabled:
        raise HTTPException(status_code=503, detail=error_msg)

    yacht_id = auth['yacht_id']
    user_role = auth.get('role', 'member')
    supabase = get_tenant_client(auth['tenant_key_alias'])

    try:
        msg_result = supabase.table('email_messages').select(
            'id, thread_id, subject, from_display_name, sent_at, has_attachments, attachments, preview_text'
        ).eq('id', message_id).eq('yacht_id', yacht_id).maybe_single().execute()

        if not msg_result.data:
            raise HTTPException(status_code=404, detail="Message not found")

        message = msg_result.data

        entities_result = supabase.table('email_extraction_results').select(
            'entity_type, entity_value, confidence'
        ).eq('message_id', message_id).execute()

        extracted_entities: dict = {}
        for entity in (entities_result.data or []):
            entity_type = entity['entity_type']
            extracted_entities.setdefault(entity_type, []).append(entity['entity_value'])

        if not extracted_entities and message.get('preview_text'):
            from email_rag.entity_extractor import EmailEntityExtractor
            extractor = EmailEntityExtractor()
            full_text = f"{message.get('subject', '')}\n\n{message.get('preview_text', '')}"
            extracted_entities = extractor.extract(full_text)

        links_result = supabase.table('email_links').select(
            'id, object_type, object_id, confidence, accepted_at'
        ).eq('thread_id', message['thread_id']).eq('yacht_id', yacht_id).eq('is_active', True).execute()

        existing_links = [
            {
                'id': link['id'],
                'object_type': link['object_type'],
                'object_id': link['object_id'],
                'confidence': link['confidence'],
                'accepted': link['accepted_at'] is not None,
            }
            for link in (links_result.data or [])
        ]

        attachments = message.get('attachments') or []
        if isinstance(attachments, str):
            try:
                attachments = json.loads(attachments)
            except Exception:
                attachments = []
        attachment_count = len(attachments) if attachments else 0

        from email_rag.micro_actions import build_focus_response
        response = build_focus_response(
            message_id=message_id,
            thread_id=message['thread_id'],
            subject=message.get('subject'),
            from_display_name=message.get('from_display_name'),
            sent_at=message.get('sent_at'),
            has_attachments=message.get('has_attachments', False),
            attachment_count=attachment_count,
            extracted_entities=extracted_entities,
            existing_links=existing_links,
            user_role=user_role,
        )

        logger.info(
            f"[email/focus] yacht={yacht_id[:8]} message={message_id[:8]} "
            f"entities={len(extracted_entities)} links={len(existing_links)} "
            f"actions={len(response.micro_actions)}"
        )

        return response.to_dict()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[email/focus] Error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get message focus")


# ── GET /search-objects ───────────────────────────────────────────────────────

@router.get("/search-objects")
async def search_linkable_objects(
    q: str,
    types: str = "work_order,equipment,part",
    limit: int = 10,
    auth: dict = Depends(get_authenticated_user),
):
    """Search for objects that can be linked to emails."""
    enabled, error_msg = check_email_feature('link')
    if not enabled:
        raise HTTPException(status_code=503, detail=error_msg)

    if len(q) < 2:
        return {'results': []}

    yacht_id = auth['yacht_id']
    supabase = get_tenant_client(auth['tenant_key_alias'])

    type_list = [t.strip() for t in types.split(',')]
    results = []

    try:
        if 'work_order' in type_list:
            wo_result = supabase.table('pms_work_orders').select(
                'id, title, status, wo_number'
            ).eq('yacht_id', yacht_id).or_(f"title.ilike.%{q}%,wo_number.ilike.%{q}%").limit(limit).execute()

            for wo in (wo_result.data or []):
                results.append({
                    'type': 'work_order',
                    'id': wo['id'],
                    'label': f"WO-{wo.get('wo_number', '')}: {wo.get('title', 'Untitled')}",
                    'status': wo.get('status'),
                })

        if 'equipment' in type_list:
            eq_result = supabase.table('pms_equipment').select(
                'id, name, serial_number, model'
            ).eq('yacht_id', yacht_id).or_(
                f"name.ilike.%{q}%,serial_number.ilike.%{q}%,model.ilike.%{q}%"
            ).limit(limit).execute()

            for eq in (eq_result.data or []):
                label = eq.get('name', 'Unknown')
                if eq.get('serial_number'):
                    label += f" (S/N: {eq['serial_number']})"
                results.append({'type': 'equipment', 'id': eq['id'], 'label': label})

        if 'part' in type_list:
            parts_result = supabase.table('pms_parts').select(
                'id, name, part_number'
            ).eq('yacht_id', yacht_id).or_(
                f"name.ilike.%{q}%,part_number.ilike.%{q}%"
            ).limit(limit).execute()

            for part in (parts_result.data or []):
                label = part.get('name', 'Unknown')
                if part.get('part_number'):
                    label += f" (P/N: {part['part_number']})"
                results.append({'type': 'part', 'id': part['id'], 'label': label})

        if 'fault' in type_list:
            fault_result = supabase.table('pms_faults').select(
                'id, title, status'
            ).eq('yacht_id', yacht_id).ilike('title', f'%{q}%').limit(limit).execute()

            for fault in (fault_result.data or []):
                results.append({
                    'type': 'fault',
                    'id': fault['id'],
                    'label': fault.get('title', 'Untitled'),
                    'status': fault.get('status'),
                })

        if 'purchase_order' in type_list:
            po_result = supabase.table('pms_purchase_orders').select(
                'id, po_number, description, status'
            ).eq('yacht_id', yacht_id).or_(
                f"po_number.ilike.%{q}%,description.ilike.%{q}%"
            ).limit(limit).execute()

            for po in (po_result.data or []):
                results.append({
                    'type': 'purchase_order',
                    'id': po['id'],
                    'label': f"PO-{po.get('po_number', '')}: {po.get('description', '')}",
                    'status': po.get('status'),
                })

        if 'supplier' in type_list:
            supplier_result = supabase.table('pms_suppliers').select(
                'id, name, category'
            ).eq('yacht_id', yacht_id).ilike('name', f'%{q}%').limit(limit).execute()

            for supplier in (supplier_result.data or []):
                label = supplier.get('name', 'Unknown')
                if supplier.get('category'):
                    label += f" ({supplier['category']})"
                results.append({'type': 'supplier', 'id': supplier['id'], 'label': label})

        return {'results': results}

    except Exception as e:
        logger.error(f"[email/search-objects] Error: {e}")
        raise HTTPException(status_code=500, detail="Search failed")


# ── GET /unread-count ─────────────────────────────────────────────────────────

@router.get("/unread-count")
async def get_unread_count(
    auth: dict = Depends(get_authenticated_user),
):
    """
    Returns unread email count from Graph inbox.
    Lightweight endpoint for sidebar badge polling (every 60s).
    Never errors — returns graceful defaults.
    """
    yacht_id = auth['yacht_id']
    user_id = auth['user_id']
    supabase = get_tenant_client(auth['tenant_key_alias'])

    try:
        read_client = create_read_client(supabase, user_id, yacht_id)
        token = await read_client._get_token()

        async with httpx.AsyncClient() as client:
            inbox_response = await client.get(
                "https://graph.microsoft.com/v1.0/me/mailFolders/inbox?$select=unreadItemCount",
                headers={"Authorization": f"Bearer {token}"},
                timeout=10.0,
            )

            if inbox_response.status_code != 200:
                return {"unread_count": 0, "status": "graph_error"}

            inbox_data = inbox_response.json()
            return {"unread_count": inbox_data.get("unreadItemCount", 0), "status": "connected"}

    except (TokenNotFoundError, TokenExpiredError):
        return {"unread_count": 0, "status": "not_connected"}
    except Exception as e:
        logger.warning(f"[email/unread-count] Failed: {e}")
        return {"unread_count": 0, "status": "error"}


# ── GET /worker/status ────────────────────────────────────────────────────────

@router.get("/worker/status")
async def get_worker_status(
    auth: dict = Depends(get_authenticated_user),
):
    """Get email sync worker status for the current user."""
    yacht_id = auth['yacht_id']
    user_id = auth['user_id']
    supabase = get_tenant_client(auth['tenant_key_alias'])

    try:
        watcher_result = supabase.table('email_watchers').select(
            'sync_status, last_sync_at, subscription_expires_at, last_sync_error, delta_link_inbox, sync_version, updated_at'
        ).eq('user_id', user_id).eq('yacht_id', yacht_id).eq(
            'provider', 'microsoft_graph'
        ).limit(1).execute()

        if not watcher_result.data:
            return {
                'connected': False,
                'sync_status': 'disconnected',
                'last_sync_at': None,
                'last_error': None,
                'message': 'No email connection found',
            }

        watcher = watcher_result.data[0]
        sync_status = watcher.get('sync_status', 'unknown')

        return {
            'connected': sync_status not in ['disconnected', 'pending'],
            'sync_status': sync_status,
            'sync_version': watcher.get('sync_version', 'folder'),
            'last_sync_at': watcher.get('last_sync_at'),
            'subscription_expires_at': watcher.get('subscription_expires_at'),
            'last_error': watcher.get('last_sync_error'),
            'has_delta_link': bool(watcher.get('delta_link_inbox')),
            'updated_at': watcher.get('updated_at'),
        }

    except Exception as e:
        logger.error(f"[email/worker/status] Error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch worker status: {e}")
