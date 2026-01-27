#!/usr/bin/env python3
"""
Email RAG Sync Checkpoint Module (M6.1)

Deterministic delta sync checkpointing for Outlook email ingestion.

Invariants:
- Checkpoint persisted ONLY after full page success
- Resume from last_delta_url on restart/crash
- Idempotent message upserts (no duplicates on replay)
- Degraded state on token/auth errors (no infinite retry)

Architecture:
    Watcher (DB) → Delta Query → Page Loop → Persist Checkpoint
                       ↓
                   Process Items → Upsert Messages → Enqueue Prepare Jobs

Usage:
    from email_rag.sync_checkpoint import DeltaSyncManager

    manager = DeltaSyncManager(supabase)
    async for result in manager.sync_watcher(watcher_id):
        print(f"Processed page: {result.processed_count} items")
"""

from __future__ import annotations

import asyncio
import logging
import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List, AsyncIterator, Callable
import httpx

logger = logging.getLogger(__name__)


# =============================================================================
# CHECKPOINT STATE MACHINE
# =============================================================================

class WatcherStatus(str, Enum):
    """Watcher sync status states."""
    ACTIVE = "active"  # Normal operation
    DEGRADED = "degraded"  # Token/auth issue
    PAUSED = "paused"  # Manual pause
    RECONNECTING = "reconnecting"  # Re-auth in progress
    INITIAL_SYNC = "initial_sync"  # First crawl (no delta)


class ErrorType(str, Enum):
    """Classification of sync errors."""
    TRANSIENT = "transient"  # 429, 5xx - retry with backoff
    AUTH = "auth"  # 401, token_revoked - degrade watcher
    INVALID_DELTA = "invalid_delta"  # Delta token expired/invalid - reset
    PERMANENT = "permanent"  # Message not found, etc - skip


class SyncError(Exception):
    """Error captured during sync - inherits from Exception to be raiseable."""

    def __init__(
        self,
        error_type: ErrorType,
        error_code: str,
        message: str,
        retry_after: Optional[int] = None,
    ):
        super().__init__(message)
        self.error_type = error_type
        self.error_code = error_code
        self.message = message
        self.retry_after = retry_after

    def __repr__(self):
        return f"SyncError(error_type={self.error_type}, error_code={self.error_code!r}, message={self.message!r}, retry_after={self.retry_after})"

    @classmethod
    def from_http_status(cls, status: int, message: str, retry_after: Optional[int] = None) -> 'SyncError':
        """Create error from HTTP status code."""
        if status == 429:
            return cls(ErrorType.TRANSIENT, "429", message, retry_after)
        elif status == 401:
            return cls(ErrorType.AUTH, "401", message)
        elif status == 410:  # Delta token invalid
            return cls(ErrorType.INVALID_DELTA, "410", message)
        elif 500 <= status < 600:
            return cls(ErrorType.TRANSIENT, str(status), message)
        elif status == 404:
            return cls(ErrorType.PERMANENT, "404", message)
        else:
            return cls(ErrorType.PERMANENT, str(status), message)


@dataclass
class CheckpointState:
    """Current checkpoint state for a watcher."""
    watcher_id: str
    yacht_id: str
    delta_url: Optional[str]
    last_commit_at: Optional[datetime]
    status: WatcherStatus
    error_count: int

    @property
    def has_checkpoint(self) -> bool:
        return self.delta_url is not None

    @property
    def needs_initial_sync(self) -> bool:
        return self.delta_url is None or self.status == WatcherStatus.INITIAL_SYNC


@dataclass
class PageResult:
    """Result of processing one page of delta results."""
    processed_count: int
    created_count: int
    updated_count: int
    deleted_count: int
    skipped_count: int  # Duplicates
    next_link: Optional[str]
    delta_link: Optional[str]  # Final delta URL (only on last page)
    errors: List[str] = field(default_factory=list)


@dataclass
class SyncResult:
    """Result of full sync operation."""
    watcher_id: str
    success: bool
    total_processed: int
    total_created: int
    total_updated: int
    total_deleted: int
    total_skipped: int
    pages_processed: int
    final_delta_url: Optional[str]
    error: Optional[SyncError] = None
    duration_ms: int = 0


# =============================================================================
# CHECKPOINT MANAGER
# =============================================================================

class CheckpointManager:
    """
    Manages checkpoint persistence for delta sync.

    All checkpoint operations are atomic and idempotent.
    """

    def __init__(self, supabase):
        self.supabase = supabase

    async def get_checkpoint(self, watcher_id: str) -> Optional[CheckpointState]:
        """
        Get current checkpoint state for a watcher.

        Returns None if watcher not found.
        """
        try:
            result = self.supabase.rpc('get_email_checkpoint', {
                'p_watcher_id': watcher_id
            }).execute()

            if not result.data:
                return None

            row = result.data[0]

            # Get yacht_id from watcher table
            watcher = self.supabase.table('email_watchers').select(
                'yacht_id'
            ).eq('id', watcher_id).single().execute()

            if not watcher.data:
                return None

            return CheckpointState(
                watcher_id=watcher_id,
                yacht_id=watcher.data['yacht_id'],
                delta_url=row.get('delta_url'),
                last_commit_at=row.get('last_commit_at'),
                status=WatcherStatus(row.get('status', 'active')),
                error_count=row.get('error_count', 0),
            )
        except Exception as e:
            logger.error(f"[checkpoint] Failed to get checkpoint: {e}")
            return None

    async def persist_checkpoint(
        self,
        watcher_id: str,
        delta_url: str,
        processed_count: int = 0,
    ) -> bool:
        """
        Persist checkpoint after successful page processing.

        CRITICAL: Call ONLY after full page success.
        """
        try:
            self.supabase.rpc('persist_email_checkpoint', {
                'p_watcher_id': watcher_id,
                'p_delta_url': delta_url,
                'p_processed_count': processed_count,
            }).execute()

            logger.info(f"[checkpoint] Persisted: watcher={watcher_id[:8]} processed={processed_count}")
            return True
        except Exception as e:
            logger.error(f"[checkpoint] Failed to persist: {e}")
            return False

    async def mark_degraded(
        self,
        watcher_id: str,
        error_code: str,
        error_message: str,
    ) -> bool:
        """
        Mark watcher as degraded (token/auth error).

        Stops sync until reconnect flow completes.
        """
        try:
            self.supabase.rpc('mark_watcher_degraded', {
                'p_watcher_id': watcher_id,
                'p_error_code': error_code,
                'p_error_message': error_message[:500],
            }).execute()

            logger.warning(f"[checkpoint] Marked degraded: watcher={watcher_id[:8]} error={error_code}")
            return True
        except Exception as e:
            logger.error(f"[checkpoint] Failed to mark degraded: {e}")
            return False

    async def increment_error(self, watcher_id: str, error_code: str) -> int:
        """
        Increment error count for transient errors.

        Returns new error count.
        """
        try:
            result = self.supabase.rpc('increment_watcher_error', {
                'p_watcher_id': watcher_id,
                'p_error_code': error_code,
            }).execute()

            count = result.data if isinstance(result.data, int) else 1
            logger.info(f"[checkpoint] Error count incremented: watcher={watcher_id[:8]} count={count}")
            return count
        except Exception as e:
            logger.error(f"[checkpoint] Failed to increment error: {e}")
            return 1

    async def reset_checkpoint(self, watcher_id: str, reason: str = "delta_token_invalid") -> bool:
        """
        Reset checkpoint for fresh crawl.

        Called when delta token is invalid/expired.
        """
        try:
            self.supabase.rpc('reset_watcher_checkpoint', {
                'p_watcher_id': watcher_id,
                'p_reason': reason,
            }).execute()

            logger.warning(f"[checkpoint] Reset: watcher={watcher_id[:8]} reason={reason}")
            return True
        except Exception as e:
            logger.error(f"[checkpoint] Failed to reset: {e}")
            return False


# =============================================================================
# MESSAGE PROCESSOR
# =============================================================================

class MessageProcessor:
    """
    Processes delta items into database messages.

    Handles:
    - Added messages (insert)
    - Updated messages (upsert by change_key)
    - Deleted messages (soft delete)
    - Moved messages (mark and update folder)
    """

    def __init__(self, supabase, yacht_id: str):
        self.supabase = supabase
        self.yacht_id = yacht_id

    def compute_content_hash(self, subject: str, preview: str, from_addr: str) -> str:
        """
        Compute content hash for deduplication.

        Used to detect no-op updates (same content, different change_key).
        """
        normalized = f"{subject or ''}|{preview or ''}|{from_addr or ''}"
        return hashlib.sha256(normalized.encode()).hexdigest()[:32]

    async def process_item(
        self,
        item: Dict[str, Any],
        reason: str,  # @odata.deltaLink reason: 'added', 'updated', 'deleted'
    ) -> Dict[str, Any]:
        """
        Process a single delta item.

        Returns processing result: {'action': 'created'|'updated'|'skipped'|'deleted', ...}
        """
        provider_message_id = item.get('id')
        if not provider_message_id:
            return {'action': 'error', 'error': 'Missing id'}

        # Handle deletions
        if reason == 'deleted' or item.get('@removed'):
            return await self._handle_deletion(provider_message_id)

        # Handle adds/updates
        change_key = item.get('changeKey')

        # Check if message exists
        existing = self.supabase.table('email_messages').select(
            'id, change_key, content_hash'
        ).eq('yacht_id', self.yacht_id).eq(
            'provider_message_id', provider_message_id
        ).limit(1).execute()

        if existing.data:
            # Update path
            existing_msg = existing.data[0]

            # Check if change_key is same (no actual change)
            if existing_msg.get('change_key') == change_key:
                return {'action': 'skipped', 'reason': 'same_change_key'}

            # Compute content hash to detect no-op updates
            from_addr = item.get('from', {}).get('emailAddress', {}).get('address', '')
            content_hash = self.compute_content_hash(
                item.get('subject', ''),
                item.get('bodyPreview', ''),
                from_addr
            )

            if existing_msg.get('content_hash') == content_hash:
                # Same content - just update change_key
                self.supabase.table('email_messages').update({
                    'change_key': change_key,
                    'updated_at': datetime.utcnow().isoformat(),
                }).eq('id', existing_msg['id']).execute()
                return {'action': 'skipped', 'reason': 'same_content'}

            # Real update - update message
            return await self._update_message(existing_msg['id'], item, change_key, content_hash)
        else:
            # Insert path
            return await self._insert_message(item, change_key)

    async def _handle_deletion(self, provider_message_id: str) -> Dict[str, Any]:
        """Soft delete a message."""
        try:
            result = self.supabase.table('email_messages').update({
                'is_active': False,
                'deleted_at': datetime.utcnow().isoformat(),
                'updated_at': datetime.utcnow().isoformat(),
            }).eq('yacht_id', self.yacht_id).eq(
                'provider_message_id', provider_message_id
            ).execute()

            if result.data:
                return {'action': 'deleted', 'message_id': result.data[0]['id']}
            else:
                return {'action': 'skipped', 'reason': 'not_found'}
        except Exception as e:
            return {'action': 'error', 'error': str(e)}

    async def _insert_message(
        self,
        item: Dict[str, Any],
        change_key: str,
    ) -> Dict[str, Any]:
        """Insert a new message."""
        try:
            # Hash email addresses
            from_addr = item.get('from', {}).get('emailAddress', {}).get('address', '')
            from_hash = hashlib.sha256(from_addr.lower().encode()).hexdigest() if from_addr else ''
            from_name = item.get('from', {}).get('emailAddress', {}).get('name', '')

            to_addrs = [r.get('emailAddress', {}).get('address', '') for r in item.get('toRecipients', [])]
            to_hashes = [hashlib.sha256(a.lower().encode()).hexdigest() for a in to_addrs if a]

            cc_addrs = [r.get('emailAddress', {}).get('address', '') for r in item.get('ccRecipients', [])]
            cc_hashes = [hashlib.sha256(a.lower().encode()).hexdigest() for a in cc_addrs if a]

            # Preview text (truncate to 200 chars)
            body_preview = item.get('bodyPreview', '') or ''
            preview_text = body_preview[:200] if body_preview else None

            # Content hash for dedup
            content_hash = self.compute_content_hash(
                item.get('subject', ''),
                preview_text,
                from_addr
            )

            # Get or create thread
            conversation_id = item.get('conversationId')
            thread_id = await self._get_or_create_thread(conversation_id, item)

            # Determine direction from folder
            folder = item.get('parentFolderId', '')
            direction = 'outbound' if 'sent' in folder.lower() else 'inbound'

            # Insert message
            insert_data = {
                'yacht_id': self.yacht_id,
                'thread_id': thread_id,
                'provider_message_id': item.get('id'),
                'internet_message_id': item.get('internetMessageId'),
                'change_key': change_key,
                'content_hash': content_hash,
                'direction': direction,
                'from_address_hash': from_hash,
                'from_display_name': from_name,
                'to_addresses_hash': to_hashes,
                'cc_addresses_hash': cc_hashes,
                'subject': item.get('subject'),
                'preview_text': preview_text,
                'sent_at': item.get('sentDateTime'),
                'received_at': item.get('receivedDateTime'),
                'has_attachments': item.get('hasAttachments', False),
                'is_active': True,
            }

            result = self.supabase.table('email_messages').insert(insert_data).execute()

            if result.data:
                message_id = result.data[0]['id']

                # Queue extraction job
                try:
                    self.supabase.rpc('queue_email_extraction', {
                        'p_message_id': message_id,
                        'p_yacht_id': self.yacht_id,
                        'p_job_type': 'full'
                    }).execute()
                except Exception as job_err:
                    logger.warning(f"[processor] Failed to queue extraction: {job_err}")

                return {
                    'action': 'created',
                    'message_id': message_id,
                    'thread_id': thread_id,
                }
            else:
                return {'action': 'error', 'error': 'Insert returned no data'}

        except Exception as e:
            # Check if it's a duplicate key error (race condition)
            if 'duplicate' in str(e).lower() or '23505' in str(e):
                return {'action': 'skipped', 'reason': 'duplicate'}
            return {'action': 'error', 'error': str(e)}

    async def _update_message(
        self,
        message_id: str,
        item: Dict[str, Any],
        change_key: str,
        content_hash: str,
    ) -> Dict[str, Any]:
        """Update an existing message."""
        try:
            # Preview text (truncate to 200 chars)
            body_preview = item.get('bodyPreview', '') or ''
            preview_text = body_preview[:200] if body_preview else None

            update_data = {
                'change_key': change_key,
                'content_hash': content_hash,
                'subject': item.get('subject'),
                'preview_text': preview_text,
                'has_attachments': item.get('hasAttachments', False),
                'updated_at': datetime.utcnow().isoformat(),
            }

            self.supabase.table('email_messages').update(update_data).eq(
                'id', message_id
            ).execute()

            return {'action': 'updated', 'message_id': message_id}

        except Exception as e:
            return {'action': 'error', 'error': str(e)}

    async def _get_or_create_thread(
        self,
        conversation_id: Optional[str],
        item: Dict[str, Any],
    ) -> str:
        """Get or create thread for a message."""
        if not conversation_id:
            # Generate a fallback thread for orphan messages
            conversation_id = f"orphan_{item.get('id', 'unknown')}"

        # Check if thread exists
        existing = self.supabase.table('email_threads').select('id').eq(
            'yacht_id', self.yacht_id
        ).eq('provider_conversation_id', conversation_id).single().execute()

        if existing.data:
            return existing.data['id']

        # Create new thread
        thread_data = {
            'yacht_id': self.yacht_id,
            'provider_conversation_id': conversation_id,
            'latest_subject': item.get('subject'),
            'message_count': 0,
            'has_attachments': item.get('hasAttachments', False),
            'source': 'external',
        }

        result = self.supabase.table('email_threads').insert(thread_data).execute()

        if result.data:
            return result.data[0]['id']
        else:
            raise Exception("Failed to create thread")


# =============================================================================
# DELTA SYNC MANAGER
# =============================================================================

class DeltaSyncManager:
    """
    Manages the full delta sync lifecycle.

    Flow:
    1. Load checkpoint state
    2. If no checkpoint → initial crawl
    3. Else → resume from delta_url
    4. Page loop:
       - Fetch page (respect Retry-After)
       - Process items
       - Persist checkpoint (only on full page success)
       - Continue while nextLink exists
    5. On error:
       - Transient (429, 5xx) → backoff, retry, increment error_count
       - Auth (401, token_revoked) → mark degraded, stop
       - Invalid delta → reset checkpoint, restart
    """

    # Backoff configuration
    BASE_BACKOFF_SECONDS = 2
    MAX_BACKOFF_SECONDS = 60
    MAX_ERROR_COUNT = 10  # Before marking degraded

    def __init__(
        self,
        supabase,
        graph_client_factory: Optional[Callable] = None,
    ):
        self.supabase = supabase
        self.checkpoint_mgr = CheckpointManager(supabase)
        self.graph_client_factory = graph_client_factory

    def _compute_backoff(self, error_count: int, retry_after: Optional[int] = None) -> float:
        """Compute backoff with exponential increase and jitter."""
        import random

        if retry_after:
            # Use Retry-After from 429
            base = retry_after
        else:
            # Exponential backoff
            base = min(
                self.BASE_BACKOFF_SECONDS * (2 ** error_count),
                self.MAX_BACKOFF_SECONDS
            )

        # Add 20% jitter
        jitter = base * 0.2 * random.random()
        return base + jitter

    async def sync_watcher(
        self,
        watcher_id: str,
        max_pages: int = 100,
    ) -> SyncResult:
        """
        Run delta sync for a watcher.

        Args:
            watcher_id: UUID of email_watcher
            max_pages: Maximum pages to process (safety limit)

        Returns:
            SyncResult with totals and final state
        """
        import time
        start_time = time.time()

        # Initialize result
        result = SyncResult(
            watcher_id=watcher_id,
            success=False,
            total_processed=0,
            total_created=0,
            total_updated=0,
            total_deleted=0,
            total_skipped=0,
            pages_processed=0,
            final_delta_url=None,
        )

        # Get checkpoint state
        state = await self.checkpoint_mgr.get_checkpoint(watcher_id)
        if not state:
            logger.error(f"[sync] Watcher not found: {watcher_id}")
            result.error = SyncError(ErrorType.PERMANENT, "NOT_FOUND", "Watcher not found")
            return result

        # Check if degraded
        if state.status == WatcherStatus.DEGRADED:
            logger.warning(f"[sync] Watcher degraded, skipping: {watcher_id}")
            result.error = SyncError(ErrorType.AUTH, "DEGRADED", "Watcher is degraded")
            return result

        # Initialize processor
        processor = MessageProcessor(self.supabase, state.yacht_id)

        # Determine starting URL
        if state.needs_initial_sync:
            logger.info(f"[sync] Initial sync: {watcher_id[:8]}")
            # Start with inbox messages (will get delta URL after)
            current_url = None  # Will trigger initial crawl
        else:
            current_url = state.delta_url
            logger.info(f"[sync] Resume from checkpoint: {watcher_id[:8]}")

        # Page loop
        pages = 0
        while pages < max_pages:
            try:
                # Fetch page
                page_data = await self._fetch_page(
                    state.yacht_id,
                    current_url,
                    watcher_id,
                )

                # Process items
                items = page_data.get('value', [])
                page_result = await self._process_page(processor, items)

                # Update totals
                result.total_processed += page_result.processed_count
                result.total_created += page_result.created_count
                result.total_updated += page_result.updated_count
                result.total_deleted += page_result.deleted_count
                result.total_skipped += page_result.skipped_count
                pages += 1

                # Determine next URL
                next_link = page_data.get('@odata.nextLink')
                delta_link = page_data.get('@odata.deltaLink')

                if delta_link:
                    # Last page - persist final checkpoint
                    await self.checkpoint_mgr.persist_checkpoint(
                        watcher_id,
                        delta_link,
                        result.total_processed,
                    )
                    result.final_delta_url = delta_link
                    result.success = True
                    break
                elif next_link:
                    # More pages - persist intermediate checkpoint
                    await self.checkpoint_mgr.persist_checkpoint(
                        watcher_id,
                        next_link,
                        page_result.processed_count,
                    )
                    current_url = next_link
                else:
                    # No more data
                    result.success = True
                    break

            except SyncError as e:
                result.error = e
                await self._handle_error(watcher_id, e, state.error_count)
                break
            except Exception as e:
                logger.error(f"[sync] Unexpected error: {e}")
                result.error = SyncError(ErrorType.PERMANENT, "INTERNAL", str(e))
                break

        result.pages_processed = pages
        result.duration_ms = int((time.time() - start_time) * 1000)

        logger.info(
            f"[sync] Complete: watcher={watcher_id[:8]} "
            f"pages={pages} processed={result.total_processed} "
            f"created={result.total_created} updated={result.total_updated} "
            f"deleted={result.total_deleted} skipped={result.total_skipped} "
            f"success={result.success} duration_ms={result.duration_ms}"
        )

        return result

    async def _fetch_page(
        self,
        yacht_id: str,
        url: Optional[str],
        watcher_id: str,
    ) -> Dict[str, Any]:
        """
        Fetch a page from Graph API.

        Raises SyncError on failure.
        """
        # TODO: Use actual Graph client
        # For now, this is a placeholder that should be replaced with
        # actual Graph API calls via graph_client_factory

        if self.graph_client_factory:
            client = self.graph_client_factory(yacht_id)
            try:
                if url:
                    return await client.fetch_url(url)
                else:
                    return await client.get_initial_messages()
            except httpx.HTTPStatusError as e:
                retry_after = None
                if 'Retry-After' in e.response.headers:
                    try:
                        retry_after = int(e.response.headers['Retry-After'])
                    except ValueError:
                        pass
                raise SyncError.from_http_status(
                    e.response.status_code,
                    str(e),
                    retry_after
                )
        else:
            # Mock response for testing
            logger.warning("[sync] No graph client factory - returning mock response")
            return {
                'value': [],
                '@odata.deltaLink': f'https://graph.microsoft.com/v1.0/me/mailFolders/inbox/messages/delta?$deltatoken=mock_{watcher_id[:8]}'
            }

    async def _process_page(
        self,
        processor: MessageProcessor,
        items: List[Dict[str, Any]],
    ) -> PageResult:
        """Process all items in a page."""
        result = PageResult(
            processed_count=0,
            created_count=0,
            updated_count=0,
            deleted_count=0,
            skipped_count=0,
            next_link=None,
            delta_link=None,
        )

        for item in items:
            # Determine reason from item
            if item.get('@removed'):
                reason = 'deleted'
            elif item.get('@odata.etag'):
                # Could be add or update - processor will check
                reason = 'updated'
            else:
                reason = 'added'

            item_result = await processor.process_item(item, reason)
            result.processed_count += 1

            action = item_result.get('action')
            if action == 'created':
                result.created_count += 1
            elif action == 'updated':
                result.updated_count += 1
            elif action == 'deleted':
                result.deleted_count += 1
            elif action == 'skipped':
                result.skipped_count += 1
            elif action == 'error':
                result.errors.append(item_result.get('error', 'unknown'))

        return result

    async def _handle_error(
        self,
        watcher_id: str,
        error: SyncError,
        current_error_count: int,
    ):
        """Handle sync error based on type."""
        if error.error_type == ErrorType.TRANSIENT:
            # Increment error count
            new_count = await self.checkpoint_mgr.increment_error(
                watcher_id,
                error.error_code
            )

            if new_count >= self.MAX_ERROR_COUNT:
                # Too many errors - degrade
                await self.checkpoint_mgr.mark_degraded(
                    watcher_id,
                    f"MAX_ERRORS_{error.error_code}",
                    f"Max error count reached after {new_count} consecutive errors"
                )
            else:
                # Calculate backoff
                backoff = self._compute_backoff(new_count, error.retry_after)
                logger.info(f"[sync] Transient error, backing off {backoff:.1f}s")
                await asyncio.sleep(backoff)

        elif error.error_type == ErrorType.AUTH:
            # Mark degraded immediately
            await self.checkpoint_mgr.mark_degraded(
                watcher_id,
                error.error_code,
                error.message
            )

        elif error.error_type == ErrorType.INVALID_DELTA:
            # Reset checkpoint and restart
            await self.checkpoint_mgr.reset_checkpoint(
                watcher_id,
                f"delta_invalid_{error.error_code}"
            )


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    'WatcherStatus',
    'ErrorType',
    'SyncError',
    'CheckpointState',
    'PageResult',
    'SyncResult',
    'CheckpointManager',
    'MessageProcessor',
    'DeltaSyncManager',
]
