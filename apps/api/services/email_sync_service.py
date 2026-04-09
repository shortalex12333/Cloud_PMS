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

from .ms_graph_rate_limiter import MicrosoftRateLimiter
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
        "receivedDateTime,sentDateTime,hasAttachments,internetMessageId,webLink,bodyPreview,"
        "parentFolderId"
    )

    # Attachment fields
    ATTACHMENT_SELECT = "id,name,contentType,size"

    # Folders to skip during mailbox-level sync (not relevant for PMS)
    SKIP_FOLDERS = {'drafts', 'junkemail', 'deleteditems', 'outbox'}

    # Map Microsoft wellKnownName to DB-friendly folder names
    FOLDER_NAME_MAP = {
        'inbox': 'inbox',
        'sentitems': 'sent',
        'archive': 'archive',
        'deleteditems': 'deleted',
        'drafts': 'drafts',
        'junkemail': 'junk',
    }

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
        Sync a watcher's mailbox. Dispatches to folder-level or mailbox-level
        sync based on the watcher's sync_version field.
        """
        if watcher.get('sync_version') == 'mailbox':
            return await self._sync_watcher_mailbox(watcher, max_messages)
        return await self._sync_watcher_folder(watcher, max_messages)

    async def _sync_watcher_folder(
        self,
        watcher: Dict[str, Any],
        max_messages: int = 100
    ) -> Dict[str, Any]:
        """
        Original folder-level sync (inbox + sent separately).
        Used when sync_version='folder' (default).
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

    async def _sync_watcher_mailbox(
        self,
        watcher: Dict[str, Any],
        max_messages: int = 100
    ) -> Dict[str, Any]:
        """
        All-folder delta sync with move detection.
        Used when sync_version='mailbox'.

        Iterates every non-skip folder via per-folder delta queries
        (Graph v1.0 doesn't support /me/messages/delta).
        Uses _process_message_v2() which detects folder moves via
        parent_folder_id and un-deletes messages that reappear.

        Delta links stored as JSON dict in email_watchers.delta_link:
          {"folder_guid_1": "https://...deltaLink...", "folder_guid_2": "..."}
        """
        import json as _json

        user_id = watcher['user_id']
        yacht_id = watcher['yacht_id']
        watcher_id = watcher.get('id')
        mailbox_address_hash = watcher.get('mailbox_address_hash', '')

        result = {
            'user_id': user_id,
            'yacht_id': yacht_id,
            'synced': 0,
            'skipped': 0,
            'deleted': 0,
            'moved': 0,
            'api_calls': 0,
            'errors': [],
        }

        # Check rate limit
        if not await self.rate_limiter.can_make_call(user_id, yacht_id):
            logger.warning(f"[EmailSync] Rate limited for user {user_id}")
            result['skipped_reason'] = 'rate_limit'
            return result

        # Build folder GUID → wellKnownName map
        try:
            folder_map = await self._get_folder_map()
        except Exception as e:
            logger.error(f"[EmailSync] Failed to fetch folder map: {e}")
            result['errors'].append(f"folder_map: {str(e)}")
            return result

        result['api_calls'] += 1

        # Load per-folder delta links from JSON blob
        raw_delta = watcher.get('delta_link') or '{}'
        try:
            delta_links = _json.loads(raw_delta) if isinstance(raw_delta, str) else {}
        except _json.JSONDecodeError:
            delta_links = {}

        # Filter to folders we care about
        sync_folders = {
            fid: name for fid, name in folder_map.items()
            if name.lower() not in self.SKIP_FOLDERS
        }

        logger.info(f"[EmailSync] Mailbox sync: {len(sync_folders)} folders to sync")

        # Iterate each folder
        for folder_id, well_known in sync_folders.items():
            if not await self.rate_limiter.can_make_call(user_id, yacht_id):
                logger.warning(f"[EmailSync] Rate limited mid-sync, stopping")
                break

            folder_name = self.FOLDER_NAME_MAP.get(well_known.lower(), well_known or 'other')
            folder_delta = delta_links.get(folder_id)

            # Build URL
            if folder_delta:
                url = folder_delta
            else:
                url = f"{self.GRAPH_BASE_URL}/me/mailFolders/{folder_id}/messages/delta"
                url += f"?$select={self.MESSAGE_SELECT}&$top=50"

            folder_processed = 0

            try:
                async with httpx.AsyncClient() as client:
                    while url and folder_processed < max_messages:
                        response = await client.get(
                            url,
                            headers={'Authorization': f'Bearer {self.access_token}'},
                            timeout=30.0
                        )
                        result['api_calls'] += 1
                        await self.rate_limiter.record_call(user_id, yacht_id)

                        if response.status_code != 200:
                            logger.error(
                                f"[EmailSync] Graph API error on folder {folder_name}: "
                                f"{response.status_code} {response.text[:200]}"
                            )
                            result['errors'].append(f"{folder_name}: {response.status_code}")
                            break

                        data = response.json()
                        messages = data.get('value', [])

                        for msg in messages:
                            if folder_processed >= max_messages:
                                break

                            # Handle @removed
                            if '@removed' in msg:
                                await self._mark_message_deleted(yacht_id, msg)
                                result['deleted'] += 1
                                folder_processed += 1
                                continue

                            # Determine direction from envelope
                            from_addr = msg.get('from', {}).get('emailAddress', {}).get('address', '')
                            from_hash = self._hash_email(from_addr)
                            direction = 'outbound' if from_hash == mailbox_address_hash else 'inbound'

                            thread_id = await self._process_message_v2(
                                yacht_id=yacht_id,
                                watcher_id=watcher_id,
                                msg=msg,
                                folder=folder_name,
                                direction=direction,
                                parent_folder_id=folder_id,
                            )
                            if thread_id:
                                result['synced'] += 1
                            folder_processed += 1

                        # Next page or delta link
                        if '@odata.nextLink' in data:
                            url = data['@odata.nextLink']
                        elif '@odata.deltaLink' in data:
                            delta_links[folder_id] = data['@odata.deltaLink']
                            url = None
                        else:
                            url = None

            except Exception as e:
                logger.error(f"[EmailSync] Error syncing folder {folder_name}: {e}")
                result['errors'].append(f"{folder_name}: {str(e)}")

        # Persist all delta links as JSON
        self.supabase.table('email_watchers').update({
            'delta_link': _json.dumps(delta_links)
        }).eq('id', watcher_id).execute()

        # Update watcher last_sync_at
        await self._update_watcher_sync_status(watcher_id, result)

        logger.info(
            f"[EmailSync] Mailbox sync complete: synced={result['synced']}, "
            f"deleted={result['deleted']}, moved={result['moved']}, "
            f"skipped={result['skipped']}, api_calls={result['api_calls']}"
        )

        return result

    async def _get_folder_map(self) -> Dict[str, str]:
        """
        Fetch folder GUID → wellKnownName map from Microsoft Graph.

        Returns dict like: {'AAMk...==': 'inbox', 'AAMk...==': 'sentitems', ...}
        Unknown folders map to their displayName.
        """
        url = f"{self.GRAPH_BASE_URL}/me/mailFolders?$top=100"

        async with httpx.AsyncClient() as client:
            response = await client.get(
                url,
                headers={'Authorization': f'Bearer {self.access_token}'},
                timeout=15.0
            )

            if response.status_code != 200:
                raise Exception(f"Failed to fetch mail folders: {response.status_code} {response.text[:300]}")

            data = response.json()
            folder_map = {}
            for folder in data.get('value', []):
                folder_id = folder.get('id')
                # Prefer wellKnownName, fall back to displayName
                # Normalize: "Deleted Items" → "deleteditems" to match SKIP_FOLDERS
                name = folder.get('wellKnownName') or folder.get('displayName', '')
                folder_map[folder_id] = name.lower().replace(' ', '')

            return folder_map

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

    async def _process_message_v2(
        self,
        yacht_id: str,
        watcher_id: str,
        msg: Dict[str, Any],
        folder: str,
        direction: str,
        parent_folder_id: str,
    ) -> Optional[str]:
        """
        Process a message for mailbox-level sync (v2).

        Unlike _process_message(), direction and folder are passed in
        (determined from envelope and folder map), and parent_folder_id
        is stored for move detection.
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

            all_participants = list(set([from_hash] + to_hashes + cc_hashes))

            # Upsert thread (same as v1)
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

            # Check if message already exists (for move detection)
            provider_message_id = msg.get('id')
            existing = self.supabase.table('email_messages').select(
                'id, parent_folder_id, is_deleted'
            ).eq(
                'provider_message_id', provider_message_id
            ).eq('watcher_id', watcher_id).execute()

            if existing.data:
                existing_msg = existing.data[0]
                update_data = {}

                # Folder move detection
                if existing_msg.get('parent_folder_id') != parent_folder_id:
                    update_data['parent_folder_id'] = parent_folder_id
                    update_data['folder'] = folder
                    logger.info(
                        f"[EmailSync] Message {provider_message_id[:8]}... moved to {folder}"
                    )

                # Un-delete if message reappears (was moved, not truly deleted)
                if existing_msg.get('is_deleted'):
                    update_data['is_deleted'] = False
                    update_data['deleted_at'] = None

                if update_data:
                    self.supabase.table('email_messages').update(
                        update_data
                    ).eq('id', existing_msg['id']).execute()

                return thread_id

            # New message — insert
            await self._insert_message_v2(
                yacht_id=yacht_id,
                watcher_id=watcher_id,
                thread_id=thread_id,
                msg=msg,
                folder=folder,
                direction=direction,
                from_hash=from_hash,
                to_hashes=to_hashes,
                cc_hashes=cc_hashes,
                parent_folder_id=parent_folder_id,
            )

            return thread_id

        except Exception as e:
            logger.error(f"[EmailSync] Error processing message v2: {e}")
            return None

    async def _insert_message_v2(
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
        parent_folder_id: str,
    ) -> Optional[str]:
        """
        Insert email message for mailbox-level sync (v2).

        Same as _insert_message() but with parent_folder_id and
        direction/folder passed explicitly instead of inferred.
        """
        provider_message_id = msg.get('id')

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
            'watcher_id': watcher_id,
            'thread_id': thread_id,
            'provider_message_id': provider_message_id,
            'internet_message_id': msg.get('internetMessageId'),
            'subject': subject,
            'from_address_hash': from_hash,
            'from_display_name': from_display_name,
            'to_addresses_hash': to_hashes,
            'cc_addresses_hash': cc_hashes,
            'folder': folder,
            'direction': direction,
            'received_at': msg.get('receivedDateTime'),
            'sent_at': msg.get('sentDateTime'),
            'has_attachments': msg.get('hasAttachments', False),
            'attachments': attachments,
            'web_link': msg.get('webLink'),
            'preview_text': preview_text,
            'parent_folder_id': parent_folder_id,
        }

        result = self.supabase.table('email_messages').insert(message_data).execute()
        message_id = result.data[0]['id'] if result.data else None

        # Generate embeddings for the new message
        if message_id:
            await self._embed_message(yacht_id, message_id, subject, from_display_name, attachments)

        return message_id

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
