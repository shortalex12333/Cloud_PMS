"""
Email Sync Routes
=================
POST /email/sync/now
POST /email/sync/all-folders
POST /email/backfill-embeddings
POST /email/backfill-weblinks
GET  /email/ledger/{entity_type}/{entity_id}
GET  /email/debug/search-folders
GET  /email/debug/graph-me
GET  /email/debug/inbox-compare
GET  /email/debug/thread-yacht-check
POST /email/debug/force-sync-missing

Also contains _process_message(), called only by sync endpoints in this file.
"""

import hashlib
import logging
from typing import Dict

import httpx
from fastapi import APIRouter, Depends, HTTPException

from middleware.auth import get_authenticated_user
from integrations.supabase import get_tenant_client
from integrations.feature_flags import check_email_feature
from integrations.graph_client import (
    create_read_client,
    TokenNotFoundError,
    TokenExpiredError,
    TokenRevokedError,
)
from services.email_suggestion_service import generate_suggestions_for_thread
from services.email_graph_helpers import outlook_auth_error, utcnow

logger = logging.getLogger(__name__)

router = APIRouter(tags=["email"])


# ── _process_message (used by sync/now and sync/all-folders) ─────────────────

async def _process_message(supabase, yacht_id: str, msg: Dict, folder: str) -> None:
    """Process a single Graph message into email_threads + email_messages."""
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

    to_addrs = [r.get('emailAddress', {}).get('address', '') for r in msg.get('toRecipients', [])]
    to_hashes = [hashlib.sha256(a.lower().encode()).hexdigest() for a in to_addrs if a]

    cc_addrs = [r.get('emailAddress', {}).get('address', '') for r in msg.get('ccRecipients', [])]
    cc_hashes = [hashlib.sha256(a.lower().encode()).hexdigest() for a in cc_addrs if a]

    direction = 'outbound' if folder == 'sent' else 'inbound'

    existing = supabase.table('email_messages').select('id').eq(
        'yacht_id', yacht_id
    ).eq('provider_message_id', msg.get('id')).maybe_single().execute()

    if existing and existing.data:
        return

    body_preview = msg.get('bodyPreview', '') or ''
    preview_text = body_preview[:200] if body_preview else None

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
        message_id = insert_result.data[0]['id']
        try:
            supabase.rpc('queue_email_extraction', {
                'p_message_id': message_id,
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


# ── POST /sync/now ────────────────────────────────────────────────────────────

@router.post("/sync/now")
async def sync_now(
    auth: dict = Depends(get_authenticated_user),
    full_resync: bool = False,
    upgrade_to_mailbox: bool = False,
):
    """
    Manual sync trigger. Backfills 14 days of inbox + sent.

    full_resync: clears delta links to force full sync from scratch.
    upgrade_to_mailbox: switches watcher to mailbox-level delta sync.
    """
    enabled, error_msg = check_email_feature('sync')
    if not enabled:
        raise HTTPException(status_code=503, detail=error_msg)

    yacht_id = auth['yacht_id']
    user_id = auth['user_id']
    role = auth.get('role', '')

    if role not in ('chief_engineer', 'manager', 'captain', 'admin'):
        raise HTTPException(status_code=403, detail="Insufficient permissions for sync")

    supabase = get_tenant_client(auth['tenant_key_alias'])

    try:
        watcher_result = supabase.table('email_watchers').select('*').eq(
            'user_id', user_id
        ).eq('yacht_id', yacht_id).eq('provider', 'microsoft_graph').maybe_single().execute()

        if not watcher_result.data:
            raise HTTPException(status_code=400, detail="No email watcher configured")

        watcher = watcher_result.data

        if full_resync:
            logger.info("[email/sync/now] Full resync requested - clearing delta links")
            supabase.table('email_watchers').update({
                'delta_link_inbox': None,
                'delta_link_sent': None,
                'delta_link': None,
            }).eq('id', watcher['id']).execute()
            watcher.update({'delta_link_inbox': None, 'delta_link_sent': None, 'delta_link': None})

        if upgrade_to_mailbox:
            logger.info("[email/sync/now] Upgrading watcher to mailbox-level delta sync")
            supabase.table('email_watchers').update({
                'sync_version': 'mailbox',
                'delta_link': None,
                'delta_link_inbox': None,
                'delta_link_sent': None,
            }).eq('id', watcher['id']).execute()
            watcher.update({'sync_version': 'mailbox', 'delta_link': None,
                            'delta_link_inbox': None, 'delta_link_sent': None})

        read_client = create_read_client(supabase, user_id, yacht_id)
        stats = {'threads_created': 0, 'messages_created': 0, 'errors': [], 'full_resync': full_resync}

        for folder in ('inbox', 'sent'):
            delta_link = watcher.get(f'delta_link_{folder}')
            total_processed = 0
            max_messages = 500 if full_resync else 100

            try:
                while total_processed < max_messages:
                    result = await read_client.list_messages(
                        folder=folder,
                        top=min(100, max_messages - total_processed),
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
                            total_processed += 1
                        except Exception as e:
                            stats['errors'].append(f"Message {msg.get('id')}: {e}")

                    next_link = result.get('next_link')
                    new_delta = result.get('delta_link')

                    if new_delta:
                        supabase.table('email_watchers').update({
                            f'delta_link_{folder}': new_delta,
                        }).eq('id', watcher['id']).execute()
                        break
                    elif next_link:
                        delta_link = next_link
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


# ── POST /sync/all-folders ────────────────────────────────────────────────────

@router.post("/sync/all-folders")
async def sync_all_folders(
    auth: dict = Depends(get_authenticated_user),
    max_per_folder: int = 100,
):
    """Sync emails from ALL mail folders, not just inbox/sent."""
    enabled, error_msg = check_email_feature('sync')
    if not enabled:
        raise HTTPException(status_code=503, detail=error_msg)

    yacht_id = auth['yacht_id']
    user_id = auth['user_id']
    supabase = get_tenant_client(auth['tenant_key_alias'])

    try:
        read_client = create_read_client(supabase, user_id, yacht_id)
        token = await read_client._get_token()

        stats = {
            'folders_synced': 0,
            'messages_created': 0,
            'messages_skipped': 0,
            'errors': [],
            'folder_stats': {},
        }

        async with httpx.AsyncClient() as client:
            folders_response = await client.get(
                "https://graph.microsoft.com/v1.0/me/mailFolders",
                headers={"Authorization": f"Bearer {token}"},
                timeout=30.0,
            )

            if folders_response.status_code != 200:
                raise HTTPException(status_code=502, detail="Failed to list folders")

            folders = folders_response.json().get('value', [])

            for folder in folders:
                folder_name = folder.get('displayName', 'Unknown')
                folder_id = folder.get('id')
                folder_stats = {'synced': 0, 'skipped': 0, 'errors': 0}

                try:
                    messages_response = await client.get(
                        f"https://graph.microsoft.com/v1.0/me/mailFolders/{folder_id}/messages"
                        f"?$select=id,conversationId,subject,from,toRecipients,ccRecipients,"
                        f"receivedDateTime,sentDateTime,hasAttachments,internetMessageId,bodyPreview,webLink"
                        f"&$top={max_per_folder}&$orderby=receivedDateTime desc",
                        headers={"Authorization": f"Bearer {token}"},
                        timeout=60.0,
                    )

                    if messages_response.status_code == 200:
                        messages = messages_response.json().get('value', [])

                        for msg in messages:
                            try:
                                is_sent = folder_name.lower() in ('sent items', 'sent', 'sentitems')
                                folder_type = 'sent' if is_sent else 'inbox'
                                await _process_message(supabase, yacht_id, msg, folder_type)
                                folder_stats['synced'] += 1
                                stats['messages_created'] += 1
                            except Exception as e:
                                if 'duplicate' in str(e).lower() or 'already exists' in str(e).lower():
                                    folder_stats['skipped'] += 1
                                    stats['messages_skipped'] += 1
                                else:
                                    folder_stats['errors'] += 1
                                    stats['errors'].append(f"{folder_name}: {str(e)[:50]}")

                    stats['folders_synced'] += 1
                    stats['folder_stats'][folder_name] = folder_stats

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


# ── POST /backfill-embeddings ─────────────────────────────────────────────────

@router.post("/backfill-embeddings")
async def backfill_embeddings(
    auth: dict = Depends(get_authenticated_user),
    limit: int = 100,
):
    """Backfill embeddings for emails missing meta_embedding."""
    from services.email_embedding_service import EmailEmbeddingUpdater

    yacht_id = auth['yacht_id']
    supabase = get_tenant_client(auth['tenant_key_alias'])

    try:
        updater = EmailEmbeddingUpdater(supabase, yacht_id)

        if not updater.embedding_service.is_available():
            raise HTTPException(status_code=503, detail="Embedding service not available - check OPENAI_API_KEY")

        stats = await updater.backfill_embeddings(limit=limit)
        logger.info(f"[email/backfill-embeddings] yacht={yacht_id[:8]} stats={stats}")

        return {'success': True, 'yacht_id': yacht_id, 'stats': stats}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[email/backfill-embeddings] Error: {e}")
        raise HTTPException(status_code=500, detail=f"Backfill failed: {e}")


# ── POST /backfill-weblinks ───────────────────────────────────────────────────

@router.post("/backfill-weblinks")
async def backfill_weblinks(
    auth: dict = Depends(get_authenticated_user),
    limit: int = 100,
):
    """Backfill webLink (Open in Outlook) for emails missing it."""
    yacht_id = auth['yacht_id']
    user_id = auth['user_id']
    supabase = get_tenant_client(auth['tenant_key_alias'])

    try:
        messages_result = supabase.table('email_messages').select(
            'id, provider_message_id'
        ).eq('yacht_id', yacht_id).is_('web_link', 'null').limit(limit).execute()

        messages = messages_result.data or []
        if not messages:
            return {
                'success': True,
                'yacht_id': yacht_id,
                'stats': {'processed': 0, 'updated': 0, 'skipped': 0, 'failed': 0, 'message': 'No messages need backfill'},
            }

        read_client = create_read_client(supabase, user_id, yacht_id)
        stats = {'processed': 0, 'updated': 0, 'skipped': 0, 'failed': 0}

        for msg in messages:
            stats['processed'] += 1
            provider_id = msg['provider_message_id']
            try:
                content = await read_client.get_message_content(provider_id)
                weblink = content.get('webLink')
                if weblink:
                    supabase.table('email_messages').update({'web_link': weblink}).eq('id', msg['id']).execute()
                    stats['updated'] += 1
                else:
                    stats['skipped'] += 1
            except Exception as e:
                stats['failed'] += 1
                logger.warning(f"[email/backfill-weblinks] Failed for {provider_id[:20]}...: {e}")

        logger.info(f"[email/backfill-weblinks] yacht={yacht_id[:8]} stats={stats}")
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


# ── GET /ledger/{entity_type}/{entity_id} ─────────────────────────────────────

@router.get("/ledger/{entity_type}/{entity_id}")
async def get_entity_ledger(
    entity_type: str,
    entity_id: str,
    limit: int = 50,
    offset: int = 0,
    auth: dict = Depends(get_authenticated_user),
):
    """
    Chronological ledger entries for an entity (M5).

    Read-only view over pms_audit_log. Supports entity_type:
    email_thread, email_message, work_order, equipment, part, document.
    """
    enabled, error_msg = check_email_feature('focus')
    if not enabled:
        raise HTTPException(status_code=503, detail=error_msg)

    yacht_id = auth['yacht_id']
    supabase = get_tenant_client(auth['tenant_key_alias'])

    valid_types = ['email_thread', 'email_message', 'work_order', 'equipment', 'part', 'document']
    if entity_type not in valid_types:
        raise HTTPException(status_code=400, detail=f"Invalid entity_type. Must be one of: {valid_types}")

    limit = min(max(1, limit), 100)
    offset = max(0, offset)

    try:
        result = supabase.table('pms_audit_log').select(
            'id, action, entity_type, entity_id, user_id, old_values, new_values, signature, created_at',
            count='exact'
        ).eq('yacht_id', yacht_id).eq('entity_type', entity_type).eq(
            'entity_id', entity_id
        ).order('created_at', desc=True).order('id', desc=False).range(
            offset, offset + limit - 1
        ).execute()

        direct_count = result.count or 0
        entries = [
            {
                'id': row['id'],
                'event_type': row['action'],
                'timestamp': row['created_at'],
                'actor_id': row['user_id'],
                'details': row['new_values'],
                'metadata': row.get('signature', {}),
            }
            for row in (result.data or [])
        ]

        remaining = limit - len(entries)
        related_entries = []
        related_count = 0

        if remaining > 0:
            related_result = supabase.table('pms_audit_log').select(
                'id, action, entity_type, entity_id, user_id, old_values, new_values, signature, created_at',
                count='exact'
            ).eq('yacht_id', yacht_id).eq(
                'new_values->>related_entity_type', entity_type
            ).eq('new_values->>related_entity_id', entity_id).order(
                'created_at', desc=True
            ).order('id', desc=False).limit(remaining).execute()

            related_count = related_result.count or 0
            for row in (related_result.data or []):
                related_entries.append({
                    'id': row['id'],
                    'event_type': row['action'],
                    'timestamp': row['created_at'],
                    'actor_id': row['user_id'],
                    'source_entity_type': row['entity_type'],
                    'source_entity_id': row['entity_id'],
                    'details': row['new_values'],
                    'metadata': row.get('signature', {}),
                    'is_related': True,
                })

        all_entries = entries + related_entries
        all_entries.sort(key=lambda x: (x['timestamp'], x['id']), reverse=True)
        all_entries = all_entries[:limit]

        total_count = direct_count + related_count
        has_more = offset + len(all_entries) < total_count

        logger.info(f"[email/ledger] entity={entity_type}:{entity_id[:8]} entries={len(all_entries)} total={total_count}")

        return {
            'entity_type': entity_type,
            'entity_id': entity_id,
            'entries': all_entries,
            'count': len(all_entries),
            'total_count': total_count,
            'offset': offset,
            'limit': limit,
            'has_more': has_more,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[email/ledger] Error: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch ledger")


# ── GET /debug/search-folders ─────────────────────────────────────────────────

@router.get("/debug/search-folders")
async def debug_search_folders(
    q: str,
    auth: dict = Depends(get_authenticated_user),
):
    """Debug: search all Graph folders for emails matching a subject pattern."""
    yacht_id = auth['yacht_id']
    user_id = auth['user_id']
    supabase = get_tenant_client(auth['tenant_key_alias'])

    try:
        read_client = create_read_client(supabase, user_id, yacht_id)
        token = await read_client._get_token()

        results = {'query': q, 'folders': {}, 'total_found': 0}

        async with httpx.AsyncClient() as client:
            folders_response = await client.get(
                "https://graph.microsoft.com/v1.0/me/mailFolders",
                headers={"Authorization": f"Bearer {token}"},
                timeout=30.0,
            )

            if folders_response.status_code != 200:
                raise HTTPException(status_code=502, detail="Failed to list folders")

            folders = folders_response.json().get('value', [])
            results['folder_count'] = len(folders)

            for folder in folders:
                folder_name = folder.get('displayName', 'Unknown')
                folder_id = folder.get('id')

                messages_response = await client.get(
                    f"https://graph.microsoft.com/v1.0/me/mailFolders/{folder_id}/messages"
                    f"?$select=id,subject,from,receivedDateTime,conversationId&$top=100&$orderby=receivedDateTime desc",
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=30.0,
                )

                if messages_response.status_code == 200:
                    messages = messages_response.json().get('value', [])
                    matching = [
                        {
                            'subject': msg.get('subject', ''),
                            'from': msg.get('from', {}).get('emailAddress', {}).get('address', ''),
                            'received': msg.get('receivedDateTime', ''),
                            'conversationId': (
                                (msg.get('conversationId', 'NONE') or 'NONE')[:50] + '...'
                                if msg.get('conversationId') else 'NONE'
                            ),
                        }
                        for msg in messages
                        if q.lower() in (msg.get('subject', '') or '').lower()
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


# ── GET /debug/graph-me ───────────────────────────────────────────────────────

@router.get("/debug/graph-me")
async def debug_graph_me(
    auth: dict = Depends(get_authenticated_user),
):
    """Debug: show which Microsoft account the connected token belongs to."""
    yacht_id = auth['yacht_id']
    user_id = auth['user_id']
    supabase = get_tenant_client(auth['tenant_key_alias'])

    try:
        read_client = create_read_client(supabase, user_id, yacht_id)
        token = await read_client._get_token()

        async with httpx.AsyncClient() as client:
            me_response = await client.get(
                "https://graph.microsoft.com/v1.0/me",
                headers={"Authorization": f"Bearer {token}"},
                timeout=30.0,
            )

            if me_response.status_code != 200:
                raise HTTPException(status_code=502, detail=f"Graph /me error: {me_response.status_code}")

            me_data = me_response.json()

            inbox_response = await client.get(
                "https://graph.microsoft.com/v1.0/me/mailFolders/inbox",
                headers={"Authorization": f"Bearer {token}"},
                timeout=30.0,
            )
            inbox_data = inbox_response.json() if inbox_response.status_code == 200 else {}

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


# ── GET /debug/inbox-compare ──────────────────────────────────────────────────

@router.get("/debug/inbox-compare")
async def debug_inbox_compare(
    auth: dict = Depends(get_authenticated_user),
):
    """Debug: compare Graph Inbox messages with what's in our DB."""
    yacht_id = auth['yacht_id']
    user_id = auth['user_id']
    supabase = get_tenant_client(auth['tenant_key_alias'])

    try:
        read_client = create_read_client(supabase, user_id, yacht_id)
        token = await read_client._get_token()

        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://graph.microsoft.com/v1.0/me/mailFolders/inbox/messages"
                "?$select=id,conversationId,subject,from,receivedDateTime,hasAttachments,bodyPreview"
                "&$top=200&$orderby=receivedDateTime desc",
                headers={"Authorization": f"Bearer {token}"},
                timeout=60.0,
            )

            if response.status_code != 200:
                raise HTTPException(status_code=502, detail=f"Graph API error: {response.status_code} - {response.text[:200]}")

            graph_messages = response.json().get('value', [])

        db_result = supabase.table('email_messages').select('provider_message_id, subject').eq('yacht_id', yacht_id).execute()
        db_message_ids = {m['provider_message_id'] for m in db_result.data}

        in_graph = []
        missing_from_db = []

        for msg in graph_messages:
            msg_id = msg.get('id')
            conversation_id = msg.get('conversationId', '')
            msg_info = {
                'id': (msg_id[:30] + '...' if len(msg_id) > 30 else msg_id) if msg_id else None,
                'subject': msg.get('subject', '(no subject)'),
                'from': msg.get('from', {}).get('emailAddress', {}).get('address', ''),
                'received': msg.get('receivedDateTime', ''),
                'hasAttachments': msg.get('hasAttachments', False),
                'conversationId': (conversation_id[:30] + '...' if len(conversation_id) > 30 else conversation_id) if conversation_id else None,
                'preview': (msg.get('bodyPreview', '') or '')[:100],
            }
            in_graph.append(msg_info)
            if msg_id not in db_message_ids:
                missing_from_db.append(msg_info)

        return {
            'graph_inbox_count': len(graph_messages),
            'db_message_count': len(db_message_ids),
            'missing_count': len(missing_from_db),
            'missing_from_db': missing_from_db,
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


# ── GET /debug/thread-yacht-check ─────────────────────────────────────────────

@router.get("/debug/thread-yacht-check")
async def debug_thread_yacht_check(
    thread_ids: str,
    auth: dict = Depends(get_authenticated_user),
):
    """Debug: verify yacht_id assignment for specific threads (comma-separated UUIDs)."""
    user_yacht_id = auth['yacht_id']
    supabase = get_tenant_client(auth['tenant_key_alias'])

    ids = [t.strip() for t in thread_ids.split(',') if t.strip()]
    results = []

    for thread_id in ids[:10]:
        try:
            thread_result = supabase.table('email_threads').select(
                'id, yacht_id, latest_subject, created_at'
            ).eq('id', thread_id).limit(1).execute()

            if thread_result.data:
                thread = thread_result.data[0]
                thread_yacht_id = thread.get('yacht_id')
                results.append({
                    'thread_id': thread_id,
                    'exists': True,
                    'thread_yacht_id': thread_yacht_id,
                    'user_yacht_id': user_yacht_id,
                    'match': thread_yacht_id == user_yacht_id,
                    'subject': (thread.get('latest_subject') or 'N/A')[:50],
                })
            else:
                results.append({
                    'thread_id': thread_id,
                    'exists': False,
                    'thread_yacht_id': None,
                    'user_yacht_id': user_yacht_id,
                    'match': False,
                    'error': 'Thread not found in database',
                })
        except Exception as e:
            results.append({'thread_id': thread_id, 'exists': False, 'error': str(e)})

    mismatches = [r for r in results if r.get('exists') and not r.get('match')]
    not_found = [r for r in results if not r.get('exists')]

    return {
        'user_yacht_id': user_yacht_id,
        'tenant_key_alias': auth['tenant_key_alias'],
        'checked_count': len(results),
        'mismatch_count': len(mismatches),
        'not_found_count': len(not_found),
        'results': results,
        'diagnosis': (
            'YACHT_ID_MISMATCH: Threads exist but belong to different yacht' if mismatches else
            'THREADS_NOT_FOUND: Threads do not exist in this tenant database' if not_found else
            'OK: All threads match user yacht_id'
        ),
    }


# ── POST /debug/force-sync-missing ────────────────────────────────────────────

@router.post("/debug/force-sync-missing")
async def debug_force_sync_missing(
    auth: dict = Depends(get_authenticated_user),
):
    """Debug: force-sync all Inbox messages missing from our DB."""
    yacht_id = auth['yacht_id']
    user_id = auth['user_id']
    supabase = get_tenant_client(auth['tenant_key_alias'])

    try:
        read_client = create_read_client(supabase, user_id, yacht_id)
        token = await read_client._get_token()

        stats = {'checked': 0, 'synced': 0, 'already_existed': 0, 'errors': [], 'synced_subjects': []}

        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://graph.microsoft.com/v1.0/me/mailFolders/inbox/messages"
                "?$select=id,conversationId,subject,from,toRecipients,ccRecipients,"
                "receivedDateTime,sentDateTime,hasAttachments,internetMessageId,bodyPreview,webLink"
                "&$top=200&$orderby=receivedDateTime desc",
                headers={"Authorization": f"Bearer {token}"},
                timeout=60.0,
            )

            if response.status_code != 200:
                raise HTTPException(status_code=502, detail="Graph API error")

            graph_messages = response.json().get('value', [])
            stats['checked'] = len(graph_messages)

        db_result = supabase.table('email_messages').select('provider_message_id').eq('yacht_id', yacht_id).execute()
        existing_ids = {m['provider_message_id'] for m in db_result.data}

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
                error_msg = str(e)
                if 'duplicate' not in error_msg.lower():
                    stats['errors'].append(f"{msg.get('subject', 'unknown')[:30]}: {error_msg[:50]}")
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
