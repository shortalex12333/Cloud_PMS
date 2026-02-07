#!/usr/bin/env python3
"""
Email Linking Requeue Worker

Re-runs the linking ladder for threads that:
1. Have been updated since suggestions were last generated
2. Have suggestions_generated_at IS NULL (never processed)
3. Have new messages since last link attempt

This closes the "only new threads" gap by giving threads a second chance
when new information arrives (replies, attachments, subject changes).

Usage:
    LINKING_REQUEUE_ENABLED=true python -m workers.linking_requeue_worker

Environment:
    LINKING_REQUEUE_ENABLED - Set to 'true' to enable (default: false)
    LINKING_REQUEUE_POLL_INTERVAL - Seconds between polls (default: 120)
    LINKING_REQUEUE_BATCH_SIZE - Threads per batch (default: 20)
    LINKING_REQUEUE_LOOKBACK_HOURS - How far back to check (default: 168 = 7 days)
"""

import os
import sys
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from integrations.supabase import get_supabase_client
from services.linking_ladder import LinkingLadder

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('linking_requeue_worker')

# Configuration
POLL_INTERVAL = int(os.getenv('LINKING_REQUEUE_POLL_INTERVAL', '120'))
BATCH_SIZE = int(os.getenv('LINKING_REQUEUE_BATCH_SIZE', '20'))
LOOKBACK_HOURS = int(os.getenv('LINKING_REQUEUE_LOOKBACK_HOURS', '168'))
ENABLED = os.getenv('LINKING_REQUEUE_ENABLED', 'false').lower() == 'true'


class LinkingRequeueWorker:
    """
    Background worker to reprocess threads needing linking.

    Targets:
    1. Never processed: suggestions_generated_at IS NULL
    2. Stale: updated_at > suggestions_generated_at (new activity since last link)
    3. Unlinked with tokens: has extracted_tokens but no email_links
    """

    def __init__(self):
        """Initialize the worker."""
        self.supabase = get_supabase_client()
        self.running = True
        self.stats = {
            'cycles': 0,
            'threads_processed': 0,
            'links_created': 0,
            'upgrades': 0,  # L5 → L1/L2.5/L3
            'errors': 0,
        }

    async def run(self):
        """Main worker loop."""
        logger.info("=" * 60)
        logger.info("Linking Requeue Worker Starting")
        logger.info(f"Poll Interval: {POLL_INTERVAL}s")
        logger.info(f"Batch Size: {BATCH_SIZE}")
        logger.info(f"Lookback: {LOOKBACK_HOURS} hours")
        logger.info("=" * 60)

        while self.running:
            try:
                await self.process_stale_threads()
                self.stats['cycles'] += 1

                if self.stats['cycles'] % 5 == 0:
                    self._log_stats()

            except Exception as e:
                logger.error(f"Error in worker loop: {e}")
                self.stats['errors'] += 1

            await asyncio.sleep(POLL_INTERVAL)

    async def process_stale_threads(self):
        """Find and reprocess threads needing linking."""
        threads = await self._get_threads_needing_relink()

        if not threads:
            logger.debug("No threads needing relink")
            return

        logger.info(f"Found {len(threads)} thread(s) needing relink")

        for thread in threads:
            try:
                result = await self.relink_thread(thread)
                self.stats['threads_processed'] += 1

                if result.get('links_created', 0) > 0:
                    self.stats['links_created'] += result['links_created']

                if result.get('upgraded'):
                    self.stats['upgrades'] += 1

            except Exception as e:
                logger.error(f"Error relinking thread {thread['id']}: {e}")
                self.stats['errors'] += 1

    async def relink_thread(self, thread: Dict[str, Any]) -> Dict[str, Any]:
        """
        Re-run linking ladder for a thread.

        Args:
            thread: Thread record

        Returns:
            Result dict with links_created, upgraded, etc.
        """
        thread_id = thread['id']
        yacht_id = thread['yacht_id']
        subject = thread.get('latest_subject', '')
        old_tokens = thread.get('extracted_tokens') or {}

        result = {
            'thread_id': thread_id,
            'links_created': 0,
            'upgraded': False,
            'old_level': None,
            'new_level': None,
        }

        # Check if thread already has links
        existing_links = self.supabase.table('email_links').select(
            'id, suggested_reason, score'
        ).eq('thread_id', thread_id).eq('is_primary', True).limit(1).execute()

        had_links = bool(existing_links.data)
        if had_links:
            result['old_level'] = self._infer_level(existing_links.data[0])

        # Get participant hashes from tokens or thread
        participant_hashes = old_tokens.get('vendor', {}).get('participant_hashes', [])
        if not participant_hashes:
            participant_hashes = thread.get('participant_hashes', [])

        # Run linking ladder
        ladder = LinkingLadder(self.supabase)

        selection = await ladder.determine_primary(
            yacht_id=yacht_id,
            thread_id=thread_id,
            subject=subject,
            from_address='',
            attachments=None,  # TODO: fetch from latest message
            participant_hashes=participant_hashes,
            context=None
        )

        if not selection:
            result['new_level'] = 'L5'
            logger.debug(f"Thread {thread_id[:8]}...: Still L5 (no match)")
            return result

        result['new_level'] = selection.get('level', 'L5')

        # Only create new links if we found a match
        if selection.get('action') in ('auto_link', 'suggest', 'weak_suggest'):
            # Check if this would be an upgrade
            if not had_links:
                result['upgraded'] = True
                logger.info(
                    f"Thread {thread_id[:8]}...: UPGRADED L5 → {result['new_level']} "
                    f"({selection.get('candidate', {}).get('label', 'unknown')})"
                )

            # Create links (idempotent - won't duplicate)
            created_ids = await self._create_links_idempotent(
                yacht_id=yacht_id,
                thread_id=thread_id,
                selection=selection,
                ladder=ladder
            )
            result['links_created'] = len(created_ids)

        return result

    async def _create_links_idempotent(
        self,
        yacht_id: str,
        thread_id: str,
        selection: Dict[str, Any],
        ladder: LinkingLadder
    ) -> List[str]:
        """
        Create links idempotently (skip if already exists).

        Uses (thread_id, object_type, object_id) as unique key.
        """
        created_ids = []
        candidate = selection.get('candidate')

        if not candidate:
            return created_ids

        object_type = candidate['object_type']
        object_id = candidate['object_id']

        # Check if link already exists
        existing = self.supabase.table('email_links').select('id').eq(
            'thread_id', thread_id
        ).eq('object_type', object_type).eq('object_id', object_id).limit(1).execute()

        if existing.data:
            logger.debug(f"Link already exists for {thread_id[:8]}... → {object_type}")
            return created_ids

        # Create via ladder method
        created_ids = await ladder.create_link_suggestion(
            yacht_id=yacht_id,
            thread_id=thread_id,
            selection=selection,
            max_suggestions=3
        )

        return created_ids

    async def _get_threads_needing_relink(self) -> List[Dict[str, Any]]:
        """
        Find threads that need relinking.

        Criteria:
        1. suggestions_generated_at IS NULL (never processed)
        2. updated_at > suggestions_generated_at (activity since last link)
        3. Has extracted_tokens but no email_links

        Returns:
            List of thread records
        """
        cutoff = (datetime.utcnow() - timedelta(hours=LOOKBACK_HOURS)).isoformat()
        threads_to_relink = []

        try:
            # Case 1: Never processed
            never_processed = self.supabase.table('email_threads').select(
                'id, yacht_id, latest_subject, extracted_tokens, participant_hashes, '
                'suggestions_generated_at, updated_at'
            ).is_(
                'suggestions_generated_at', 'null'
            ).gte('created_at', cutoff).order(
                'created_at', desc=True
            ).limit(BATCH_SIZE).execute()

            threads_to_relink.extend(never_processed.data or [])

            # Case 2: Updated since last link attempt
            if len(threads_to_relink) < BATCH_SIZE:
                # This requires a raw query since Supabase doesn't support column comparison
                stale = self.supabase.rpc('get_stale_link_threads', {
                    'p_cutoff': cutoff,
                    'p_limit': BATCH_SIZE - len(threads_to_relink)
                }).execute()

                threads_to_relink.extend(stale.data or [])

            # Case 3: Has tokens but no links (handled by backfill, but include stragglers)
            if len(threads_to_relink) < BATCH_SIZE:
                # Get threads with tokens
                with_tokens = self.supabase.table('email_threads').select(
                    'id, yacht_id, latest_subject, extracted_tokens, participant_hashes, '
                    'suggestions_generated_at, updated_at'
                ).not_.is_(
                    'extracted_tokens', 'null'
                ).not_.is_(
                    'suggestions_generated_at', 'null'
                ).gte('created_at', cutoff).order(
                    'updated_at', desc=True
                ).limit(BATCH_SIZE * 2).execute()

                # Filter to those without links
                for thread in with_tokens.data or []:
                    if len(threads_to_relink) >= BATCH_SIZE:
                        break

                    # Skip if already in list
                    if any(t['id'] == thread['id'] for t in threads_to_relink):
                        continue

                    # Check for existing links
                    links = self.supabase.table('email_links').select('id').eq(
                        'thread_id', thread['id']
                    ).limit(1).execute()

                    if not links.data:
                        threads_to_relink.append(thread)

        except Exception as e:
            logger.error(f"Error querying threads: {e}")
            # If RPC doesn't exist, fall back to simpler query
            if 'get_stale_link_threads' in str(e):
                logger.warning("get_stale_link_threads RPC not found, using fallback")

        return threads_to_relink[:BATCH_SIZE]

    def _infer_level(self, link: Dict[str, Any]) -> str:
        """Infer linking level from link properties."""
        reason = link.get('suggested_reason', '')
        score = link.get('score', 0)

        if reason in ('wo_pattern', 'po_pattern') or score >= 130:
            return 'L1'
        elif reason == 'token_match' or (60 <= score < 100):
            return 'L2.5'
        elif reason in ('part_number', 'serial_match'):
            return 'L3'
        elif reason == 'vendor_domain':
            return 'L4'
        return 'L5'

    def _log_stats(self):
        """Log worker statistics."""
        logger.info(
            f"Stats: cycles={self.stats['cycles']}, "
            f"processed={self.stats['threads_processed']}, "
            f"links={self.stats['links_created']}, "
            f"upgrades={self.stats['upgrades']}, "
            f"errors={self.stats['errors']}"
        )

    def stop(self):
        """Stop the worker gracefully."""
        logger.info("Stopping worker...")
        self.running = False


async def main():
    """Entry point."""
    if not ENABLED:
        logger.warning("Linking requeue is disabled (LINKING_REQUEUE_ENABLED != true)")
        logger.warning("Set LINKING_REQUEUE_ENABLED=true to enable")
        return

    worker = LinkingRequeueWorker()

    try:
        await worker.run()
    except KeyboardInterrupt:
        worker.stop()
    except Exception as e:
        logger.error(f"Worker crashed: {e}")
        raise


if __name__ == '__main__':
    asyncio.run(main())
