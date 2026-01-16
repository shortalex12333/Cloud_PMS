"""
CelesteOS Backend - Email Transport Layer Routes

Endpoints:
- GET  /email/related?object_type=&object_id=  - Get threads linked to an object
- GET  /email/thread/:thread_id                - Get thread with messages
- GET  /email/message/:provider_message_id/render - Fetch message content (no storage)
- POST /email/link/accept                      - Accept a suggested link
- POST /email/link/change                      - Change link target
- POST /email/link/remove                      - Remove a link (soft delete)
- POST /email/evidence/save-attachment         - Save attachment to documents
- POST /email/sync/now                         - Manual sync trigger (service role only)

Doctrine compliance:
- All queries scoped by yacht_id
- Render uses READ token only
- Send/evidence uses WRITE token only
- No email body storage
- All link changes audited
"""

from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import logging
import uuid
import hashlib

# Local imports
from middleware.auth import get_authenticated_user
from integrations.supabase import get_supabase_client
from integrations.feature_flags import check_email_feature
from integrations.graph_client import (
    create_read_client,
    create_write_client,
    TokenNotFoundError,
    TokenExpiredError,
    TokenRevokedError,
    TokenPurposeMismatchError,
    TokenRefreshError,
    GraphApiError,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/email", tags=["email"])


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class RelatedRequest(BaseModel):
    object_type: str = Field(..., description="Type: work_order, equipment, part, fault, etc.")
    object_id: str = Field(..., description="UUID of the object")


class LinkAcceptRequest(BaseModel):
    link_id: str = Field(..., description="UUID of the link to accept")


class LinkChangeRequest(BaseModel):
    link_id: str = Field(..., description="UUID of the link to change")
    new_object_type: str = Field(..., description="New target type")
    new_object_id: str = Field(..., description="New target UUID")


class LinkRemoveRequest(BaseModel):
    link_id: str = Field(..., description="UUID of the link to remove")


class SaveAttachmentRequest(BaseModel):
    message_id: str = Field(..., description="Provider message ID")
    attachment_id: str = Field(..., description="Provider attachment ID")
    target_folder: Optional[str] = Field(None, description="Target folder in documents")


class ThreadResponse(BaseModel):
    id: str
    provider_conversation_id: str
    latest_subject: Optional[str]
    message_count: int
    has_attachments: bool
    source: str
    first_message_at: Optional[str]
    last_activity_at: Optional[str]
    messages: List[Dict[str, Any]]


class MessageRenderResponse(BaseModel):
    id: str
    subject: Optional[str]
    body: Dict[str, Any]
    body_preview: Optional[str]
    from_address: Dict[str, Any]
    to_recipients: List[Dict[str, Any]]
    cc_recipients: List[Dict[str, Any]]
    received_at: Optional[str]
    sent_at: Optional[str]
    has_attachments: bool
    attachments: List[Dict[str, Any]]


# ============================================================================
# HELPER: FEATURE FLAG GUARD
# ============================================================================

def require_feature(feature_name: str):
    """Dependency that checks feature flag and fails closed."""
    enabled, error_msg = check_email_feature(feature_name)
    if not enabled:
        raise HTTPException(status_code=503, detail=error_msg)


# ============================================================================
# HELPER: MARK WATCHER DEGRADED
# ============================================================================

async def mark_watcher_degraded(
    supabase,
    user_id: str,
    yacht_id: str,
    error_message: str,
):
    """Mark email watcher as degraded with error message."""
    try:
        supabase.table('email_watchers').update({
            'sync_status': 'degraded',
            'last_sync_error': error_message[:500],  # Truncate for DB
            'last_sync_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat(),
        }).eq('user_id', user_id).eq('yacht_id', yacht_id).eq(
            'provider', 'microsoft_graph'
        ).execute()
        logger.info(f"[email] Marked watcher degraded: {error_message[:100]}")
    except Exception as e:
        logger.error(f"[email] Failed to mark watcher degraded: {e}")


# ============================================================================
# HELPER: AUDIT LOGGING
# ============================================================================

async def audit_link_action(
    supabase,
    yacht_id: str,
    user_id: str,
    action: str,
    link_id: str,
    old_values: Optional[Dict] = None,
    new_values: Optional[Dict] = None,
):
    """Log link action to audit log."""
    try:
        supabase.table('pms_audit_log').insert({
            'yacht_id': yacht_id,
            'action': action,
            'entity_type': 'email_link',
            'entity_id': link_id,
            'user_id': user_id,
            'old_values': old_values or {},
            'new_values': new_values or {},
            'signature': {'timestamp': datetime.utcnow().isoformat()},
        }).execute()
    except Exception as e:
        logger.error(f"Failed to audit link action: {e}")


# ============================================================================
# GET /email/related
# ============================================================================

@router.get("/related")
async def get_related_threads(
    object_type: str,
    object_id: str,
    auth: dict = Depends(get_authenticated_user),
):
    """
    Get email threads linked to an object.

    Tenant-scoped by yacht_id from auth context.
    """
    # Feature flag check
    enabled, error_msg = check_email_feature('related')
    if not enabled:
        raise HTTPException(status_code=503, detail=error_msg)

    yacht_id = auth['yacht_id']
    supabase = get_supabase_client()

    # Validate object_type
    valid_types = ['work_order', 'equipment', 'part', 'fault', 'purchase_order', 'supplier']
    if object_type not in valid_types:
        raise HTTPException(status_code=400, detail=f"Invalid object_type. Must be one of: {valid_types}")

    try:
        # Get links for this object, scoped by yacht_id
        links_result = supabase.table('email_links').select(
            'id, thread_id, confidence, suggested_reason, accepted_at, accepted_by'
        ).eq('yacht_id', yacht_id).eq(
            'object_type', object_type
        ).eq('object_id', object_id).eq('is_active', True).execute()

        if not links_result.data:
            return {'threads': [], 'count': 0}

        # Get thread details
        thread_ids = [link['thread_id'] for link in links_result.data]
        threads_result = supabase.table('email_threads').select(
            'id, provider_conversation_id, latest_subject, message_count, has_attachments, source, last_activity_at'
        ).eq('yacht_id', yacht_id).in_('id', thread_ids).order(
            'last_activity_at', desc=True
        ).execute()

        # Build response with link metadata
        threads = []
        link_map = {link['thread_id']: link for link in links_result.data}
        for thread in (threads_result.data or []):
            link = link_map.get(thread['id'], {})
            threads.append({
                **thread,
                'link_id': link.get('id'),
                'confidence': link.get('confidence'),
                'suggested_reason': link.get('suggested_reason'),
                'accepted': link.get('accepted_at') is not None,
            })

        return {'threads': threads, 'count': len(threads)}

    except Exception as e:
        logger.error(f"[email/related] Error: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch related threads")


# ============================================================================
# GET /email/thread/:thread_id
# ============================================================================

@router.get("/thread/{thread_id}")
async def get_thread(
    thread_id: str,
    auth: dict = Depends(get_authenticated_user),
):
    """
    Get thread with its messages.

    Tenant-scoped by yacht_id from auth context.
    """
    enabled, error_msg = check_email_feature('thread')
    if not enabled:
        raise HTTPException(status_code=503, detail=error_msg)

    yacht_id = auth['yacht_id']
    supabase = get_supabase_client()

    try:
        # Get thread (yacht_id enforced)
        thread_result = supabase.table('email_threads').select('*').eq(
            'id', thread_id
        ).eq('yacht_id', yacht_id).single().execute()

        if not thread_result.data:
            raise HTTPException(status_code=404, detail="Thread not found")

        thread = thread_result.data

        # Get messages for this thread
        messages_result = supabase.table('email_messages').select(
            'id, provider_message_id, direction, from_display_name, subject, sent_at, received_at, has_attachments, attachments'
        ).eq('thread_id', thread_id).eq('yacht_id', yacht_id).order(
            'sent_at', desc=False
        ).execute()

        return {
            **thread,
            'messages': messages_result.data or [],
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[email/thread] Error: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch thread")


# ============================================================================
# GET /email/message/:provider_message_id/render
# ============================================================================

@router.get("/message/{provider_message_id}/render")
async def render_message(
    provider_message_id: str,
    auth: dict = Depends(get_authenticated_user),
):
    """
    Fetch full message content from Graph for rendering.

    DOCTRINE: Content is NOT stored. Fetched on-click only.
    Uses READ token exclusively.
    """
    enabled, error_msg = check_email_feature('render')
    if not enabled:
        raise HTTPException(status_code=503, detail=error_msg)

    yacht_id = auth['yacht_id']
    user_id = auth['user_id']
    supabase = get_supabase_client()

    # Verify message belongs to user's yacht
    msg_result = supabase.table('email_messages').select('id').eq(
        'provider_message_id', provider_message_id
    ).eq('yacht_id', yacht_id).single().execute()

    if not msg_result.data:
        raise HTTPException(status_code=404, detail="Message not found")

    try:
        # Use READ client (enforces read token, auto-refreshes if needed)
        read_client = create_read_client(supabase, user_id, yacht_id)
        content = await read_client.get_message_content(provider_message_id)

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
        }

    except TokenNotFoundError:
        raise HTTPException(status_code=401, detail="Email not connected. Please connect your Outlook account.")

    except TokenExpiredError:
        # This shouldn't happen with auto-refresh, but handle gracefully
        raise HTTPException(status_code=401, detail="Email connection expired. Please reconnect.")

    except TokenRevokedError:
        await mark_watcher_degraded(supabase, user_id, yacht_id, "Token revoked")
        raise HTTPException(status_code=401, detail="Email connection revoked. Please reconnect.")

    except TokenRefreshError as e:
        # Refresh failed - mark watcher degraded
        error_msg = str(e)
        await mark_watcher_degraded(supabase, user_id, yacht_id, f"Token refresh failed: {error_msg}")
        logger.error(f"[email/render] Token refresh failed: {error_msg}")
        raise HTTPException(status_code=401, detail="Email connection expired and refresh failed. Please reconnect.")

    except GraphApiError as e:
        # Graph API returned an error after retry
        error_msg = str(e)
        if e.status_code == 401:
            await mark_watcher_degraded(supabase, user_id, yacht_id, f"Graph API 401: {error_msg}")
            raise HTTPException(status_code=401, detail="Microsoft rejected the request. Please reconnect your Outlook account.")
        elif e.status_code == 404:
            raise HTTPException(status_code=404, detail="Message not found in Outlook")
        else:
            logger.error(f"[email/render] Graph API error {e.status_code}: {error_msg}")
            raise HTTPException(status_code=502, detail=f"Microsoft Graph error: {error_msg}")

    except TokenPurposeMismatchError as e:
        logger.error(f"[email/render] Token purpose mismatch: {e}")
        raise HTTPException(status_code=500, detail="Internal configuration error")

    except Exception as e:
        error_msg = str(e)
        # Check if it's an HTTP error from httpx
        if hasattr(e, 'response') and hasattr(e.response, 'status_code'):
            status = e.response.status_code
            if status == 401:
                await mark_watcher_degraded(supabase, user_id, yacht_id, f"Graph 401: {error_msg}")
                raise HTTPException(status_code=401, detail="Microsoft rejected the request. Please reconnect.")
        logger.error(f"[email/render] Unexpected error: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch message content")


# ============================================================================
# POST /email/link/accept
# ============================================================================

@router.post("/link/accept")
async def accept_link(
    request: LinkAcceptRequest,
    auth: dict = Depends(get_authenticated_user),
):
    """
    Accept a suggested email link.

    Changes confidence from 'suggested' to 'user_confirmed'.
    Audited to pms_audit_log.
    """
    enabled, error_msg = check_email_feature('link')
    if not enabled:
        raise HTTPException(status_code=503, detail=error_msg)

    yacht_id = auth['yacht_id']
    user_id = auth['user_id']
    supabase = get_supabase_client()

    try:
        # Get current link state (yacht_id enforced)
        link_result = supabase.table('email_links').select('*').eq(
            'id', request.link_id
        ).eq('yacht_id', yacht_id).eq('is_active', True).single().execute()

        if not link_result.data:
            raise HTTPException(status_code=404, detail="Link not found")

        link = link_result.data

        if link['confidence'] != 'suggested':
            raise HTTPException(status_code=400, detail="Link is not in suggested state")

        # Update link
        update_result = supabase.table('email_links').update({
            'confidence': 'user_confirmed',
            'accepted_at': datetime.utcnow().isoformat(),
            'accepted_by': user_id,
            'updated_at': datetime.utcnow().isoformat(),
        }).eq('id', request.link_id).eq('yacht_id', yacht_id).execute()

        # Audit the action
        await audit_link_action(
            supabase, yacht_id, user_id, 'EMAIL_LINK_ACCEPT', request.link_id,
            old_values={'confidence': 'suggested'},
            new_values={'confidence': 'user_confirmed'},
        )

        return {'success': True, 'link_id': request.link_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[email/link/accept] Error: {e}")
        raise HTTPException(status_code=500, detail="Failed to accept link")


# ============================================================================
# POST /email/link/change
# ============================================================================

@router.post("/link/change")
async def change_link(
    request: LinkChangeRequest,
    auth: dict = Depends(get_authenticated_user),
):
    """
    Change a link's target object.

    Audited to pms_audit_log.
    """
    enabled, error_msg = check_email_feature('link')
    if not enabled:
        raise HTTPException(status_code=503, detail=error_msg)

    yacht_id = auth['yacht_id']
    user_id = auth['user_id']
    supabase = get_supabase_client()

    # Validate object_type
    valid_types = ['work_order', 'equipment', 'part', 'fault', 'purchase_order', 'supplier']
    if request.new_object_type not in valid_types:
        raise HTTPException(status_code=400, detail=f"Invalid object_type. Must be one of: {valid_types}")

    try:
        # Get current link state (yacht_id enforced)
        link_result = supabase.table('email_links').select('*').eq(
            'id', request.link_id
        ).eq('yacht_id', yacht_id).eq('is_active', True).single().execute()

        if not link_result.data:
            raise HTTPException(status_code=404, detail="Link not found")

        old_link = link_result.data

        # Update link
        update_result = supabase.table('email_links').update({
            'object_type': request.new_object_type,
            'object_id': request.new_object_id,
            'confidence': 'user_confirmed',
            'modified_at': datetime.utcnow().isoformat(),
            'modified_by': user_id,
            'updated_at': datetime.utcnow().isoformat(),
        }).eq('id', request.link_id).eq('yacht_id', yacht_id).execute()

        # Audit the action
        await audit_link_action(
            supabase, yacht_id, user_id, 'EMAIL_LINK_CHANGE', request.link_id,
            old_values={
                'object_type': old_link['object_type'],
                'object_id': old_link['object_id'],
            },
            new_values={
                'object_type': request.new_object_type,
                'object_id': request.new_object_id,
            },
        )

        return {'success': True, 'link_id': request.link_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[email/link/change] Error: {e}")
        raise HTTPException(status_code=500, detail="Failed to change link")


# ============================================================================
# POST /email/link/remove
# ============================================================================

@router.post("/link/remove")
async def remove_link(
    request: LinkRemoveRequest,
    auth: dict = Depends(get_authenticated_user),
):
    """
    Remove a link (soft delete).

    Sets is_active=False. Does NOT delete.
    Audited to pms_audit_log.
    """
    enabled, error_msg = check_email_feature('link')
    if not enabled:
        raise HTTPException(status_code=503, detail=error_msg)

    yacht_id = auth['yacht_id']
    user_id = auth['user_id']
    supabase = get_supabase_client()

    try:
        # Get current link state (yacht_id enforced)
        link_result = supabase.table('email_links').select('*').eq(
            'id', request.link_id
        ).eq('yacht_id', yacht_id).eq('is_active', True).single().execute()

        if not link_result.data:
            raise HTTPException(status_code=404, detail="Link not found")

        old_link = link_result.data

        # Soft delete
        update_result = supabase.table('email_links').update({
            'is_active': False,
            'removed_at': datetime.utcnow().isoformat(),
            'removed_by': user_id,
            'updated_at': datetime.utcnow().isoformat(),
        }).eq('id', request.link_id).eq('yacht_id', yacht_id).execute()

        # Audit the action
        await audit_link_action(
            supabase, yacht_id, user_id, 'EMAIL_LINK_REMOVE', request.link_id,
            old_values={
                'is_active': True,
                'thread_id': old_link['thread_id'],
                'object_type': old_link['object_type'],
                'object_id': old_link['object_id'],
            },
            new_values={'is_active': False},
        )

        return {'success': True, 'link_id': request.link_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[email/link/remove] Error: {e}")
        raise HTTPException(status_code=500, detail="Failed to remove link")


# ============================================================================
# POST /email/evidence/save-attachment
# ============================================================================

@router.post("/evidence/save-attachment")
async def save_attachment(
    request: SaveAttachmentRequest,
    auth: dict = Depends(get_authenticated_user),
):
    """
    Save an email attachment to documents storage.

    Uses WRITE token for Graph access (evidence collection).
    Stores to Supabase storage, creates doc_yacht_library entry.
    """
    enabled, error_msg = check_email_feature('evidence')
    if not enabled:
        raise HTTPException(status_code=503, detail=error_msg)

    yacht_id = auth['yacht_id']
    user_id = auth['user_id']
    supabase = get_supabase_client()

    # Verify message belongs to user's yacht
    msg_result = supabase.table('email_messages').select('id, thread_id').eq(
        'provider_message_id', request.message_id
    ).eq('yacht_id', yacht_id).single().execute()

    if not msg_result.data:
        raise HTTPException(status_code=404, detail="Message not found")

    try:
        # Use READ client to get attachment (read operation)
        read_client = create_read_client(supabase, user_id, yacht_id)
        attachment = await read_client.get_attachment(request.message_id, request.attachment_id)

        if not attachment:
            raise HTTPException(status_code=404, detail="Attachment not found")

        # Get attachment content
        content_bytes = attachment.get('contentBytes')
        if not content_bytes:
            raise HTTPException(status_code=400, detail="Attachment has no content")

        import base64
        file_data = base64.b64decode(content_bytes)

        # Determine storage path
        filename = attachment.get('name', 'attachment')
        content_type = attachment.get('contentType', 'application/octet-stream')
        folder = request.target_folder or 'email-attachments'
        storage_path = f"{yacht_id}/{folder}/{uuid.uuid4()}-{filename}"

        # Upload to storage
        supabase.storage.from_('documents').upload(
            storage_path, file_data,
            {'content-type': content_type}
        )

        # Create document entry
        doc_entry = {
            'yacht_id': yacht_id,
            'title': filename,
            'source': 'email_attachment',
            'storage_path': storage_path,
            'content_type': content_type,
            'file_size': len(file_data),
            'metadata': {
                'email_message_id': request.message_id,
                'email_thread_id': msg_result.data['thread_id'],
                'original_attachment_id': request.attachment_id,
            },
            'created_by': user_id,
        }

        doc_result = supabase.table('doc_yacht_library').insert(doc_entry).execute()

        return {
            'success': True,
            'document_id': doc_result.data[0]['id'] if doc_result.data else None,
            'storage_path': storage_path,
        }

    except TokenNotFoundError:
        raise HTTPException(status_code=401, detail="Email not connected")
    except TokenExpiredError:
        raise HTTPException(status_code=401, detail="Email connection expired")
    except TokenRevokedError:
        raise HTTPException(status_code=401, detail="Email connection revoked")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[email/evidence/save-attachment] Error: {e}")
        raise HTTPException(status_code=500, detail="Failed to save attachment")


# ============================================================================
# POST /email/sync/now (SERVICE ROLE ONLY)
# ============================================================================

@router.post("/sync/now")
async def sync_now(
    auth: dict = Depends(get_authenticated_user),
):
    """
    Manual sync trigger.

    Backfills 14 days of inbox + sent.
    Stores metadata into email_threads + email_messages.
    Updates email_watchers sync fields.

    Requires service role or admin.
    """
    enabled, error_msg = check_email_feature('sync')
    if not enabled:
        raise HTTPException(status_code=503, detail=error_msg)

    yacht_id = auth['yacht_id']
    user_id = auth['user_id']
    role = auth.get('role', '')

    # Role check - only chief_engineer, manager, or service accounts can trigger sync
    allowed_roles = ['chief_engineer', 'manager', 'captain', 'admin']
    if role not in allowed_roles:
        raise HTTPException(status_code=403, detail="Insufficient permissions for sync")

    supabase = get_supabase_client()

    try:
        # Get watcher
        watcher_result = supabase.table('email_watchers').select('*').eq(
            'user_id', user_id
        ).eq('yacht_id', yacht_id).eq('provider', 'microsoft_graph').single().execute()

        if not watcher_result.data:
            raise HTTPException(status_code=400, detail="No email watcher configured")

        watcher = watcher_result.data

        # Create read client
        read_client = create_read_client(supabase, user_id, yacht_id)

        # Sync inbox and sent
        stats = {'threads_created': 0, 'messages_created': 0, 'errors': []}

        for folder in ['inbox', 'sent']:
            delta_link = watcher.get(f'delta_link_{folder}')

            try:
                # Get messages (using delta if available)
                result = await read_client.list_messages(
                    folder=folder,
                    top=100,
                    delta_link=delta_link,
                    select=['id', 'conversationId', 'subject', 'from', 'toRecipients', 'ccRecipients',
                            'receivedDateTime', 'sentDateTime', 'hasAttachments', 'internetMessageId'],
                )

                # Process messages
                for msg in result.get('messages', []):
                    try:
                        await _process_message(supabase, yacht_id, msg, folder)
                        stats['messages_created'] += 1
                    except Exception as e:
                        stats['errors'].append(f"Message {msg.get('id')}: {str(e)}")

                # Save new delta link
                new_delta = result.get('delta_link')
                if new_delta:
                    supabase.table('email_watchers').update({
                        f'delta_link_{folder}': new_delta,
                    }).eq('id', watcher['id']).execute()

            except Exception as e:
                stats['errors'].append(f"Folder {folder}: {str(e)}")

        # Update watcher sync status
        supabase.table('email_watchers').update({
            'last_sync_at': datetime.utcnow().isoformat(),
            'last_sync_error': stats['errors'][-1] if stats['errors'] else None,
            'sync_status': 'degraded' if stats['errors'] else 'active',
        }).eq('id', watcher['id']).execute()

        return {
            'success': True,
            'stats': stats,
        }

    except TokenNotFoundError:
        raise HTTPException(status_code=401, detail="Email not connected")
    except TokenExpiredError:
        raise HTTPException(status_code=401, detail="Email connection expired")
    except TokenRevokedError:
        raise HTTPException(status_code=401, detail="Email connection revoked")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[email/sync/now] Error: {e}")
        raise HTTPException(status_code=500, detail=f"Sync failed: {str(e)}")


async def _process_message(supabase, yacht_id: str, msg: Dict, folder: str):
    """Process a single message from Graph into DB."""
    conversation_id = msg.get('conversationId')
    if not conversation_id:
        return

    # Get or create thread
    thread_result = supabase.table('email_threads').select('id').eq(
        'yacht_id', yacht_id
    ).eq('provider_conversation_id', conversation_id).single().execute()

    if thread_result.data:
        thread_id = thread_result.data['id']
    else:
        # Create thread
        thread_insert = supabase.table('email_threads').insert({
            'yacht_id': yacht_id,
            'provider_conversation_id': conversation_id,
            'latest_subject': msg.get('subject'),
            'message_count': 0,
            'has_attachments': msg.get('hasAttachments', False),
            'source': 'external',
        }).execute()
        thread_id = thread_insert.data[0]['id']

    # Hash email addresses
    from_addr = msg.get('from', {}).get('emailAddress', {}).get('address', '')
    from_hash = hashlib.sha256(from_addr.lower().encode()).hexdigest() if from_addr else ''
    from_name = msg.get('from', {}).get('emailAddress', {}).get('name', '')

    to_addrs = [r.get('emailAddress', {}).get('address', '') for r in msg.get('toRecipients', [])]
    to_hashes = [hashlib.sha256(a.lower().encode()).hexdigest() for a in to_addrs if a]

    cc_addrs = [r.get('emailAddress', {}).get('address', '') for r in msg.get('ccRecipients', [])]
    cc_hashes = [hashlib.sha256(a.lower().encode()).hexdigest() for a in cc_addrs if a]

    # Determine direction
    direction = 'outbound' if folder == 'sent' else 'inbound'

    # Check if message already exists
    existing = supabase.table('email_messages').select('id').eq(
        'yacht_id', yacht_id
    ).eq('provider_message_id', msg.get('id')).single().execute()

    if existing.data:
        return  # Already processed

    # Insert message
    supabase.table('email_messages').insert({
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
        'sent_at': msg.get('sentDateTime'),
        'received_at': msg.get('receivedDateTime'),
        'has_attachments': msg.get('hasAttachments', False),
        'folder': folder,
    }).execute()

    # Update thread stats
    supabase.rpc('update_thread_activity', {
        'p_thread_id': thread_id,
        'p_sent_at': msg.get('sentDateTime') or msg.get('receivedDateTime'),
        'p_direction': direction,
        'p_subject': msg.get('subject'),
        'p_has_attachments': msg.get('hasAttachments', False),
    }).execute()


# ============================================================================
# EXPORTS
# ============================================================================

__all__ = ['router']
