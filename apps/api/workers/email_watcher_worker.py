"""
Email Watcher Background Worker

Phase 5: Runs continuously on Render, syncing mailboxes in rotation.
Respects rate limits and sync intervals.

Usage:
    python -m workers.email_watcher_worker

Environment Variables:
    EMAIL_WATCHER_ENABLED=true
    EMAIL_WATCHER_POLL_INTERVAL=60  (seconds between poll cycles)
    SUPABASE_URL=...
    SUPABASE_SERVICE_KEY=...
"""

import os
import sys
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, Optional

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from supabase import create_client
from integrations.graph_client import (
    get_valid_token,
    refresh_expiring_tokens,
    acquire_refresh_lock,
    release_refresh_lock
)
from services.email_sync_service import EmailSyncService
from services.graph_api_rate_limiter import MicrosoftRateLimiter

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('EmailWatcher')

# Configuration
POLL_INTERVAL = int(os.getenv('EMAIL_WATCHER_POLL_INTERVAL', '30'))  # Changed from 60 to 30 seconds
WATCHER_BATCH_SIZE = int(os.getenv('EMAIL_WATCHER_BATCH_SIZE', '10'))
ENABLED = os.getenv('EMAIL_WATCHER_ENABLED', 'false').lower() == 'true'

# Token refresh heartbeat configuration
TOKEN_REFRESH_ENABLED = os.getenv('TOKEN_REFRESH_HEARTBEAT_ENABLED', 'true').lower() == 'true'
TOKEN_REFRESH_INTERVAL_CYCLES = int(os.getenv('TOKEN_REFRESH_INTERVAL_CYCLES', '2'))  # Run every N cycles
TOKEN_REFRESH_LOOKAHEAD = int(os.getenv('TOKEN_REFRESH_LOOKAHEAD_SECONDS', '300'))  # 5 minutes
TOKEN_REFRESH_COOLDOWN = int(os.getenv('TOKEN_REFRESH_COOLDOWN_SECONDS', '600'))  # 10 minutes
TOKEN_REFRESH_ACTIVITY_DAYS = int(os.getenv('TOKEN_REFRESH_ACTIVITY_DAYS', '14'))
TOKEN_REFRESH_BATCH_LIMIT = int(os.getenv('TOKEN_REFRESH_BATCH_LIMIT', '50'))
TOKEN_REFRESH_JITTER_MAX = int(os.getenv('TOKEN_REFRESH_JITTER_MAX_SECONDS', '20'))


class EmailWatcherWorker:
    """
    Background worker that syncs email for all active watchers.

    Runs in a continuous loop:
    1. Query watchers due for sync
    2. For each watcher, refresh token and sync
    3. Update sync status
    4. Sleep and repeat
    """

    def __init__(self):
        """Initialize the worker."""
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_SERVICE_KEY')

        if not supabase_url or not supabase_key:
            raise ValueError("Missing SUPABASE_URL or SUPABASE_SERVICE_KEY")

        self.supabase = create_client(supabase_url, supabase_key)
        self.rate_limiter = MicrosoftRateLimiter(self.supabase)
        self.running = True
        self.stats = {
            'cycles': 0,
            'watchers_synced': 0,
            'messages_synced': 0,
            'errors': 0,
        }

    async def run(self):
        """Main worker loop."""
        logger.info("=" * 60)
        logger.info("Email Watcher Worker Starting")
        logger.info(f"Poll Interval: {POLL_INTERVAL}s")
        logger.info(f"Batch Size: {WATCHER_BATCH_SIZE}")
        logger.info(f"Token Refresh Heartbeat: {'Enabled' if TOKEN_REFRESH_ENABLED else 'Disabled'}")
        if TOKEN_REFRESH_ENABLED:
            logger.info(f"  Interval: Every {TOKEN_REFRESH_INTERVAL_CYCLES} cycles")
            logger.info(f"  Lookahead: {TOKEN_REFRESH_LOOKAHEAD}s, Cooldown: {TOKEN_REFRESH_COOLDOWN}s")
        logger.info("=" * 60)

        while self.running:
            try:
                # Process pending watcher syncs
                await self.process_pending_syncs()
                self.stats['cycles'] += 1

                # Token refresh heartbeat (every N cycles)
                if TOKEN_REFRESH_ENABLED and self.stats['cycles'] % TOKEN_REFRESH_INTERVAL_CYCLES == 0:
                    await self.run_token_refresh_heartbeat()

                if self.stats['cycles'] % 10 == 0:
                    self._log_stats()

            except Exception as e:
                logger.error(f"Error in worker loop: {e}")
                self.stats['errors'] += 1

            await asyncio.sleep(POLL_INTERVAL)

    async def run_token_refresh_heartbeat(self):
        """
        Proactive token refresh heartbeat.

        Acquires distributed lock and refreshes tokens expiring soon.
        Only one worker instance runs this at a time.
        """
        logger.info("[TokenRefreshHeartbeat] Starting")

        # Try to acquire lock
        lock_acquired = await acquire_refresh_lock(self.supabase)
        if not lock_acquired:
            logger.debug("[TokenRefreshHeartbeat] Lock held by another worker, skipping")
            return

        try:
            # Run proactive refresh with configured params
            stats = await refresh_expiring_tokens(
                self.supabase,
                lookahead_seconds=TOKEN_REFRESH_LOOKAHEAD,
                cooldown_seconds=TOKEN_REFRESH_COOLDOWN,
                recent_activity_days=TOKEN_REFRESH_ACTIVITY_DAYS,
                batch_limit=TOKEN_REFRESH_BATCH_LIMIT,
                jitter_max_seconds=TOKEN_REFRESH_JITTER_MAX
            )

            logger.info(
                f"[TokenRefreshHeartbeat] Complete: "
                f"{len(stats['refreshed'])} refreshed, "
                f"{len(stats['failed'])} failed, "
                f"{stats['skipped_inactive']} inactive"
            )

            # Log any hard failures
            hard_fails = [f for f in stats['failed'] if f.get('error_type') == 'hard_fail']
            if hard_fails:
                logger.warning(f"[TokenRefreshHeartbeat] {len(hard_fails)} hard failures (reconnect required)")

        except Exception as e:
            logger.error(f"[TokenRefreshHeartbeat] Error: {e}")
        finally:
            # Always release lock
            await release_refresh_lock(self.supabase)

    async def process_pending_syncs(self):
        """Find and process watchers due for sync."""

        # Get watchers due for sync
        watchers = await self._get_watchers_due_for_sync()

        if not watchers:
            logger.debug("No watchers due for sync")
            return

        logger.info(f"Found {len(watchers)} watcher(s) due for sync")

        for watcher in watchers:
            try:
                await self.sync_single_watcher(watcher)
                self.stats['watchers_synced'] += 1

            except Exception as e:
                logger.error(f"Error syncing watcher {watcher['id']}: {e}")
                self.stats['errors'] += 1

                # Mark watcher as degraded
                await self._mark_watcher_error(watcher['id'], str(e))

    async def sync_single_watcher(self, watcher: Dict[str, Any]):
        """
        Sync a single watcher's mailbox.

        Args:
            watcher: Watcher record from get_email_watchers_due_for_sync
        """
        user_id = watcher['user_id']
        yacht_id = watcher['yacht_id']

        logger.info(f"Syncing watcher for user={user_id[:8]}... yacht={yacht_id[:8]}...")

        # GUARDRAIL: Validate watcher.user_id has a valid token before syncing
        # This prevents the "user_id mismatch" bug where watcher pointed to wrong user
        token_exists = self.supabase.table('auth_microsoft_tokens').select('user_id').eq(
            'user_id', user_id
        ).eq('yacht_id', yacht_id).eq('provider', 'microsoft_graph').eq(
            'token_purpose', 'read'
        ).eq('is_revoked', False).execute()

        if not token_exists.data:
            logger.error(
                f"[GUARDRAIL] No valid token for watcher user_id={user_id[:8]}... "
                "This may indicate watcher/token user mismatch. "
                "Verify watcher.user_id matches token.user_id in auth_microsoft_tokens."
            )
            await self._mark_watcher_error(watcher['id'], 'token_user_mismatch')
            return

        # Get fresh access token
        access_token = await self._get_access_token(user_id, yacht_id)

        if not access_token:
            logger.warning(f"No valid token for user={user_id[:8]}...")
            await self._mark_watcher_error(watcher['id'], 'token_expired')
            return

        # Create sync service and run
        sync_service = EmailSyncService(self.supabase, access_token)

        # Build full watcher record (RPC returns partial)
        full_watcher = {
            'id': watcher['id'],
            'user_id': user_id,
            'yacht_id': yacht_id,
            'delta_link_inbox': watcher.get('delta_link_inbox'),
            'delta_link_sent': watcher.get('delta_link_sent'),
        }

        result = await sync_service.sync_watcher(full_watcher)

        # Log result
        inbox_count = result.get('inbox', {}).get('synced', 0)
        sent_count = result.get('sent', {}).get('synced', 0)
        total = inbox_count + sent_count

        self.stats['messages_synced'] += total

        logger.info(
            f"Synced: inbox={inbox_count}, sent={sent_count}, "
            f"api_calls={result.get('api_calls', 0)}"
        )

        if result.get('errors'):
            logger.warning(f"Sync errors: {result['errors']}")

    async def _get_watchers_due_for_sync(self):
        """Get watchers that are due for sync."""
        try:
            result = self.supabase.rpc('get_email_watchers_due_for_sync', {
                'p_limit': WATCHER_BATCH_SIZE
            }).execute()

            return result.data or []

        except Exception as e:
            logger.error(f"Error getting watchers: {e}")
            return []

    async def _get_access_token(
        self,
        user_id: str,
        yacht_id: str
    ) -> Optional[str]:
        """
        Get valid access token for a user.

        Refreshes token if needed.
        """
        try:
            # Use get_valid_token which handles token refresh
            token = await get_valid_token(
                self.supabase,
                user_id,
                yacht_id,
                'read'  # purpose: read token for email sync
            )
            return token

        except Exception as e:
            logger.error(f"Error getting access token: {e}")
            return None

    async def _mark_watcher_error(self, watcher_id: str, error: str):
        """Mark a watcher as having an error."""
        try:
            self.supabase.table('email_watchers').update({
                'sync_status': 'degraded',
                'last_sync_error': error,
                'last_sync_at': datetime.utcnow().isoformat(),
            }).eq('id', watcher_id).execute()

        except Exception as e:
            logger.error(f"Error updating watcher status: {e}")

    def _log_stats(self):
        """Log worker statistics."""
        logger.info(
            f"Stats: cycles={self.stats['cycles']}, "
            f"watchers={self.stats['watchers_synced']}, "
            f"messages={self.stats['messages_synced']}, "
            f"errors={self.stats['errors']}"
        )

    def stop(self):
        """Stop the worker gracefully."""
        logger.info("Stopping worker...")
        self.running = False


async def main():
    """Entry point."""
    if not ENABLED:
        logger.warning("Email watcher is disabled (EMAIL_WATCHER_ENABLED != true)")
        logger.warning("Set EMAIL_WATCHER_ENABLED=true to enable")
        return

    worker = EmailWatcherWorker()

    try:
        await worker.run()
    except KeyboardInterrupt:
        worker.stop()
    except Exception as e:
        logger.error(f"Worker crashed: {e}")
        raise


if __name__ == '__main__':
    asyncio.run(main())
