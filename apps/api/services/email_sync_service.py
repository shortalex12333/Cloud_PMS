"""
Email Watcher - Email Sync Service

Phase 6: Delta Sync Pipeline for Inbox + Sent folders.
Uses Microsoft Graph API delta queries for incremental sync.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
import hashlib
import logging
import httpx

from .graph_api_rate_limiter import MicrosoftRateLimiter
from .linking_ladder import LinkingLadder
from .email_embedding_service import EmailEmbeddingUpdater

logger = logging.getLogger(__name__)


class EmailSyncService:
    """
    Sync emails from Microsoft Graph API using delta queries.

    - Syncs Inbox and Sent folders
    - Stores metadata only (no bodies)
    - Uses delta links for incremental updates
    - Respects rate limits
    """

    GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0"

    # Fields to select (metadata only - no full body)
    # webLink is the OWA URL for "Open in Outlook" feature
    # bodyPreview is needed for extraction trigger and search indexing
    MESSAGE_SELECT = (
        "id,conversationId,subject,from,toRecipients,ccRecipients,"
        "receivedDateTime,sentDateTime,hasAttachments,internetMessageId,webLink,bodyPreview"
    )

    # Attachment fields
    ATTACHMENT_SELECT = "id,name,contentType,size"

    def __init__(self, supabase_client, graph_access_token: str):
        """
        Initialize email sync service.

        Args:
            supabase_client: Supabase client instance
            graph_access_token: Microsoft Graph access token (READ scope)
        """
        self.supabase = supabase_client
        self.access_token = graph_access_token
        self.rate_limiter = MicrosoftRateLimiter(supabase_client)
        self.linking_ladder = LinkingLadder(supabase_client)

    async def sync_watcher(
        self,
        watcher: Dict[str, Any],
        max_messages: int = 100
    ) -> Dict[str, Any]:
        """
        Sync both inbox and sent for a watcher.

        Args:
            watcher: Watcher record from email_watchers
            max_messages: Maximum messages to sync per folder

        Returns:
            Sync result with stats
        """
        user_id = watcher['user_id']
        yacht_id = watcher['yacht_id']

        result = {
            'user_id': user_id,
            'yacht_id': yacht_id,
            'inbox': {'synced': 0, 'threads': 0},
            'sent': {'synced': 0, 'threads': 0},
            'api_calls': 0,
            'errors': [],
        }

        # Check rate limit
        if not await self.rate_limiter.can_make_call(user_id, yacht_id):
            logger.warning(f"[EmailSync] Rate limited for user {user_id}")
            result['skipped'] = True
            result['reason'] = 'rate_limit'
            return result

        # Get watcher_id for per-user thread isolation
        watcher_id = watcher.get('id')

        # Sync Inbox
        try:
            inbox_result = await self.sync_folder(
                user_id=user_id,
                yacht_id=yacht_id,
                watcher_id=watcher_id,
                folder='inbox',
                delta_link=watcher.get('delta_link_inbox'),
                max_messages=max_messages
            )
            result['inbox'] = inbox_result
            result['api_calls'] += inbox_result.get('api_calls', 0)

        except Exception as e:
            logger.error(f"[EmailSync] Inbox sync error: {e}")
            result['errors'].append(f"inbox: {str(e)}")

        # Check rate limit again before sent
        if not await self.rate_limiter.can_make_call(user_id, yacht_id):
            result['sent_skipped'] = True
            return result

        # Sync Sent
        try:
            sent_result = await self.sync_folder(
                user_id=user_id,
                yacht_id=yacht_id,
                watcher_id=watcher_id,
                folder='sentItems',
                delta_link=watcher.get('delta_link_sent'),
                max_messages=max_messages
            )
            result['sent'] = sent_result
            result['api_calls'] += sent_result.get('api_calls', 0)

        except Exception as e:
            logger.error(f"[EmailSync] Sent sync error: {e}")
            result['errors'].append(f"sent: {str(e)}")

        # Update watcher last_sync_at
        await self._update_watcher_sync_status(watcher['id'], result)

        return result

    async def sync_folder(
        self,
        user_id: str,
        yacht_id: str,
        watcher_id: str,
        folder: str,
        delta_link: Optional[str] = None,
        max_messages: int = 100
    ) -> Dict[str, Any]:
        """
        Sync a single folder using delta query.

        Args:
            user_id: User ID
            yacht_id: Yacht ID
            watcher_id: Watcher ID for per-user thread isolation
            folder: Folder name (inbox, sentItems)
            delta_link: Previous delta link for incremental sync
            max_messages: Maximum messages to process

        Returns:
            Sync result with messages and new delta link
        """
        result = {
            'synced': 0,
            'threads': 0,
            'api_calls': 0,
            'delta_link': delta_link,
        }

        # Build URL
        if delta_link:
            url = delta_link
        else:
            url = f"{self.GRAPH_BASE_URL}/me/mailFolders/{folder}/messages/delta"
            url += f"?$select={self.MESSAGE_SELECT}&$top=50"

        messages_processed = 0
        thread_ids = set()

        async with httpx.AsyncClient() as client:
            while url and messages_processed < max_messages:
                # Make API call
                response = await client.get(
                    url,
                    headers={'Authorization': f'Bearer {self.access_token}'},
                    timeout=30.0
                )
                result['api_calls'] += 1

                # Record API call
                await self.rate_limiter.record_call(user_id, yacht_id)

                if response.status_code != 200:
                    logger.error(f"[EmailSync] Graph API error: {response.status_code} {response.text[:200]}")
                    break

                data = response.json()
                messages = data.get('value', [])

                # Process messages
                for msg in messages:
                    if messages_processed >= max_messages:
                        break

                    # Handle deleted messages (Microsoft Graph delta sync)
                    if '@removed' in msg:
                        await self._mark_message_deleted(yacht_id, msg)
                        messages_processed += 1
                        continue

                    thread_id = await self._process_message(yacht_id, watcher_id, msg, folder)
                    if thread_id:
                        thread_ids.add(thread_id)
                        messages_processed += 1

                # Get next page or delta link
                if '@odata.nextLink' in data:
                    url = data['@odata.nextLink']
                elif '@odata.deltaLink' in data:
                    result['delta_link'] = data['@odata.deltaLink']
                    url = None
                else:
                    url = None

        result['synced'] = messages_processed
        result['threads'] = len(thread_ids)

        # Update delta link in watcher
        if result['delta_link'] != delta_link:
            delta_col = 'delta_link_inbox' if folder == 'inbox' else 'delta_link_sent'
            self.supabase.table('email_watchers').update({
                delta_col: result['delta_link']
            }).eq('user_id', user_id).eq('yacht_id', yacht_id).execute()

        return result

    async def _process_message(
        self,
        yacht_id: str,
        watcher_id: str,
        msg: Dict[str, Any],
        folder: str
    ) -> Optional[str]:
        """
        Process a single message from Graph API.

        Creates/updates thread and message records.
        Returns thread ID if successful.
        """
        try:
            conversation_id = msg.get('conversationId')
            if not conversation_id:
                return None

            # Hash email addresses
            from_addr = msg.get('from', {}).get('emailAddress', {}).get('address', '')
            from_hash = self._hash_email(from_addr)

            to_hashes = [
                self._hash_email(r.get('emailAddress', {}).get('address', ''))
                for r in msg.get('toRecipients', [])
            ]

            cc_hashes = [
                self._hash_email(r.get('emailAddress', {}).get('address', ''))
                for r in msg.get('ccRecipients', [])
            ]

            # All participants
            all_participants = list(set([from_hash] + to_hashes + cc_hashes))

            # Determine direction
            direction = 'outbound' if folder == 'sentItems' else 'inbound'

            # Upsert thread
            thread_id = await self._upsert_thread(
                yacht_id=yacht_id,
                watcher_id=watcher_id,
                conversation_id=conversation_id,
                subject=msg.get('subject', ''),
                participant_hashes=all_participants,
                has_attachments=msg.get('hasAttachments', False),
                received_at=msg.get('receivedDateTime'),
                sent_at=msg.get('sentDateTime'),
                direction=direction,
            )

            # Insert message
            await self._insert_message(
                yacht_id=yacht_id,
                watcher_id=watcher_id,
                thread_id=thread_id,
                msg=msg,
                folder=folder,
                direction=direction,
                from_hash=from_hash,
                to_hashes=to_hashes,
                cc_hashes=cc_hashes,
            )

            return thread_id

        except Exception as e:
            logger.error(f"[EmailSync] Error processing message: {e}")
            return None

    async def _upsert_thread(
        self,
        yacht_id: str,
        watcher_id: str,
        conversation_id: str,
        subject: str,
        participant_hashes: List[str],
        has_attachments: bool,
        received_at: Optional[str],
        sent_at: Optional[str],
        direction: str,
    ) -> str:
        """Upsert email thread record."""

        # Check if thread exists for this watcher (per-user isolation)
        existing = self.supabase.table('email_threads').select('id').eq(
            'yacht_id', yacht_id
        ).eq('watcher_id', watcher_id).eq(
            'provider_conversation_id', conversation_id
        ).execute()

        activity_time = received_at or sent_at or datetime.utcnow().isoformat()

        if existing.data:
            # Update existing thread
            thread_id = existing.data[0]['id']

            update_data = {
                'latest_subject': subject,
                'last_activity_at': activity_time,
                'has_attachments': has_attachments,
                'updated_at': datetime.utcnow().isoformat(),
            }

            if direction == 'inbound':
                update_data['last_inbound_at'] = activity_time
            else:
                update_data['last_outbound_at'] = activity_time

            # Update thread metadata (message_count will be recalculated if needed)
            self.supabase.table('email_threads').update(update_data).eq(
                'id', thread_id
            ).execute()

        else:
            # Create new thread with watcher_id for per-user isolation
            thread_data = {
                'yacht_id': yacht_id,
                'watcher_id': watcher_id,
                'provider_conversation_id': conversation_id,
                'latest_subject': subject,
                'participant_hashes': participant_hashes,
                'has_attachments': has_attachments,
                'source': 'external',  # Check constraint: external, internal, celeste
                'message_count': 1,
                'first_message_at': activity_time,
                'last_activity_at': activity_time,
            }

            if direction == 'inbound':
                thread_data['last_inbound_at'] = activity_time
            else:
                thread_data['last_outbound_at'] = activity_time

            result = self.supabase.table('email_threads').insert(thread_data).execute()
            thread_id = result.data[0]['id']

            # Trigger linking ladder for new threads
            await self._trigger_linking(
                yacht_id=yacht_id,
                thread_id=thread_id,
                subject=subject,
                participant_hashes=participant_hashes,
            )

        return thread_id

    async def _insert_message(
        self,
        yacht_id: str,
        watcher_id: str,
        thread_id: str,
        msg: Dict[str, Any],
        folder: str,
        direction: str,
        from_hash: str,
        to_hashes: List[str],
        cc_hashes: List[str],
    ) -> Optional[str]:
        """Insert email message record (metadata only)."""

        provider_message_id = msg.get('id')

        # Check if message already exists for this watcher
        existing = self.supabase.table('email_messages').select('id').eq(
            'provider_message_id', provider_message_id
        ).eq('watcher_id', watcher_id).execute()

        if existing.data:
            return existing.data[0]['id']

        # Get attachment metadata (not content)
        attachments = []
        if msg.get('hasAttachments'):
            attachments = await self._fetch_attachment_metadata(provider_message_id)

        subject = msg.get('subject', '')
        from_display_name = msg.get('from', {}).get('emailAddress', {}).get('name', '')

        # Extract body preview (truncate to 200 chars for SOC-2 compliance)
        body_preview = msg.get('bodyPreview', '') or ''
        preview_text = body_preview[:200] if body_preview else None

        message_data = {
            'yacht_id': yacht_id,
            'watcher_id': watcher_id,  # Per-user isolation
            'thread_id': thread_id,
            'provider_message_id': provider_message_id,
            'internet_message_id': msg.get('internetMessageId'),
            'subject': subject,
            'from_address_hash': from_hash,
            'from_display_name': from_display_name,
            'to_addresses_hash': to_hashes,
            'cc_addresses_hash': cc_hashes,
            'folder': 'sent' if folder == 'sentItems' else folder,  # Map Graph API folder name to DB constraint
            'direction': direction,
            'received_at': msg.get('receivedDateTime'),
            'sent_at': msg.get('sentDateTime'),
            'has_attachments': msg.get('hasAttachments', False),
            'attachments': attachments,
            'web_link': msg.get('webLink'),  # OWA link for "Open in Outlook"
            'preview_text': preview_text,  # For extraction trigger and search indexing
        }

        result = self.supabase.table('email_messages').insert(message_data).execute()
        message_id = result.data[0]['id'] if result.data else None

        # Generate embeddings for the new message
        if message_id:
            await self._embed_message(yacht_id, message_id, subject, from_display_name, attachments)

        return message_id

    async def _mark_message_deleted(
        self,
        yacht_id: str,
        msg: Dict[str, Any]
    ) -> None:
        """
        Mark a message as deleted (soft delete).

        Called when Microsoft Graph delta sync returns a message with @removed property.
        We keep the message in the database to preserve link history and audit trail.

        Args:
            yacht_id: Yacht ID
            msg: Message from Graph API with @removed property
        """
        try:
            provider_message_id = msg.get('id')
            if not provider_message_id:
                return

            # Check if message exists in our database
            existing = self.supabase.table('email_messages').select('id, is_deleted').eq(
                'provider_message_id', provider_message_id
            ).eq('yacht_id', yacht_id).execute()

            if not existing.data:
                # Message doesn't exist in our DB - nothing to delete
                logger.debug(f"[EmailSync] Message {provider_message_id[:8]}... not found for deletion (never synced)")
                return

            message = existing.data[0]
            if message.get('is_deleted'):
                # Already marked as deleted
                logger.debug(f"[EmailSync] Message {provider_message_id[:8]}... already marked as deleted")
                return

            # Soft delete: mark as deleted with timestamp
            from datetime import datetime, timezone
            self.supabase.table('email_messages').update({
                'is_deleted': True,
                'deleted_at': datetime.now(timezone.utc).isoformat(),
                'updated_at': datetime.now(timezone.utc).isoformat()
            }).eq('id', message['id']).execute()

            logger.info(f"[EmailSync] ✓ Marked message {provider_message_id[:8]}... as deleted")

        except Exception as e:
            logger.error(f"[EmailSync] Failed to mark message as deleted: {e}")

    async def _embed_message(
        self,
        yacht_id: str,
        message_id: str,
        subject: str,
        from_display_name: str,
        attachments: List[Dict[str, Any]],
    ) -> None:
        """Generate and store embeddings for an email message."""
        try:
            updater = EmailEmbeddingUpdater(self.supabase, yacht_id)
            await updater.update_email_embeddings(
                email_id=message_id,
                subject=subject,
                sender_name=from_display_name,
                attachments=attachments,
            )
        except Exception as e:
            # Log but don't fail the sync if embedding fails
            logger.warning(f"[EmailSync] Embedding failed for message {message_id}: {e}")

    async def _fetch_attachment_metadata(
        self,
        message_id: str
    ) -> List[Dict[str, Any]]:
        """Fetch attachment metadata (not content)."""
        try:
            async with httpx.AsyncClient() as client:
                url = f"{self.GRAPH_BASE_URL}/me/messages/{message_id}/attachments"
                url += f"?$select={self.ATTACHMENT_SELECT}"

                response = await client.get(
                    url,
                    headers={'Authorization': f'Bearer {self.access_token}'},
                    timeout=15.0
                )

                if response.status_code == 200:
                    data = response.json()
                    return [
                        {
                            'id': att.get('id'),
                            'name': att.get('name'),
                            'contentType': att.get('contentType'),
                            'size': att.get('size'),
                        }
                        for att in data.get('value', [])
                    ]

        except Exception as e:
            logger.error(f"[EmailSync] Error fetching attachments: {e}")

        return []

    async def _trigger_linking(
        self,
        yacht_id: str,
        thread_id: str,
        subject: str,
        participant_hashes: List[str],
    ) -> None:
        """Trigger linking ladder for a new thread."""
        try:
            # Get sender from first participant (usually from_hash)
            from_hash = participant_hashes[0] if participant_hashes else ''

            # Run linking ladder
            selection = await self.linking_ladder.determine_primary(
                yacht_id=yacht_id,
                thread_id=thread_id,
                subject=subject,
                from_address='',  # We only have hash
                participant_hashes=participant_hashes,
            )

            if selection:
                # Create suggestions
                await self.linking_ladder.create_link_suggestion(
                    yacht_id=yacht_id,
                    thread_id=thread_id,
                    selection=selection,
                )

        except Exception as e:
            logger.error(f"[EmailSync] Error in linking: {e}")

    async def _update_watcher_sync_status(
        self,
        watcher_id: str,
        result: Dict[str, Any]
    ) -> None:
        """Update watcher sync status after sync."""
        status = 'active' if not result.get('errors') else 'degraded'
        error_msg = '; '.join(result.get('errors', [])) if result.get('errors') else None

        self.supabase.table('email_watchers').update({
            'last_sync_at': datetime.utcnow().isoformat(),
            'sync_status': status,
            'last_sync_error': error_msg,
            'updated_at': datetime.utcnow().isoformat(),
        }).eq('id', watcher_id).execute()

    def _hash_email(self, email: str) -> str:
        """Hash email address for privacy."""
        if not email:
            return ''
        return hashlib.sha256(email.lower().strip().encode()).hexdigest()


# Export
__all__ = ['EmailSyncService']
