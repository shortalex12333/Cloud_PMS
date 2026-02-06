#!/usr/bin/env python3
"""
Email Link Suggester Worker (Background)

Runs linking ladder on threads that haven't had suggestions generated yet.
Creates email_links suggestions for high-confidence matches.

This worker is OPTIONAL - suggestions can also be created on-demand when user opens thread.

Usage:
    LINK_SUGGESTER_ENABLED=true python -m workers.link_suggester_worker

Environment:
    LINK_SUGGESTER_ENABLED - Set to 'true' to enable (default: false)
    LINK_SUGGESTER_POLL_INTERVAL - Seconds between polls (default: 60)
    LINK_SUGGESTER_BATCH_SIZE - Threads per batch (default: 10)
    SUPABASE_URL - Supabase URL
    SUPABASE_SERVICE_KEY - Service role key

Table Dependencies:
    - email_threads (id, yacht_id, latest_subject, suggestions_generated_at, extracted_tokens)
    - email_links (thread_id, object_type, object_id, confidence, score, suggested_at, is_primary)
    - email_link_decisions (thread_id, action, created_at)
"""

import os
import sys
import asyncio
import logging
from datetime import datetime
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
logger = logging.getLogger('link_suggester_worker')

# Configuration
POLL_INTERVAL = int(os.getenv('LINK_SUGGESTER_POLL_INTERVAL', '60'))
BATCH_SIZE = int(os.getenv('LINK_SUGGESTER_BATCH_SIZE', '10'))
ENABLED = os.getenv('LINK_SUGGESTER_ENABLED', 'false').lower() == 'true'


class LinkSuggesterWorker:
    """
    Background worker for email link suggestions.

    Workflow:
    1. Query threads with extracted_tokens but no suggestions_generated_at
    2. For each thread, run LinkingLadder (L1 -> L2.5)
    3. If result score >= 70 (weak_suggest threshold), create suggestions
    4. Mark thread.suggestions_generated_at
    """

    def __init__(self):
        """Initialize the worker."""
        self.supabase = get_supabase_client()
        self.running = True
        self.stats = {
            'cycles': 0,
            'threads_processed': 0,
            'suggestions_created': 0,
            'errors': 0,
        }

    async def run(self):
        """Main worker loop."""
        logger.info("=" * 60)
        logger.info("Link Suggester Worker Starting")
        logger.info(f"Poll Interval: {POLL_INTERVAL}s")
        logger.info(f"Batch Size: {BATCH_SIZE}")
        logger.info("=" * 60)

        while self.running:
            try:
                await self.process_pending_threads()
                self.stats['cycles'] += 1

                if self.stats['cycles'] % 10 == 0:
                    self._log_stats()

            except Exception as e:
                logger.error(f"Error in worker loop: {e}")
                self.stats['errors'] += 1

            await asyncio.sleep(POLL_INTERVAL)

    async def process_pending_threads(self):
        """Find and process threads needing suggestion generation."""
        threads = await self._get_threads_needing_suggestions()

        if not threads:
            logger.debug("No threads needing suggestions")
            return

        logger.info(f"Found {len(threads)} thread(s) needing suggestions")

        for thread in threads:
            try:
                await self.suggest_for_thread(thread)
                self.stats['threads_processed'] += 1

            except Exception as e:
                logger.error(f"Error processing thread {thread['id']}: {e}")
                self.stats['errors'] += 1

    async def suggest_for_thread(self, thread: Dict[str, Any]):
        """
        Run linking ladder and create suggestions for a thread.

        Args:
            thread: Thread record with id, yacht_id, latest_subject, latest_from_address, extracted_tokens
        """
        thread_id = thread['id']
        yacht_id = thread['yacht_id']
        subject = thread.get('latest_subject', '')
        from_address = thread.get('latest_from_address', '')

        logger.debug(f"Processing thread {thread_id[:8]}... subject='{subject[:50]}'")

        # Initialize linking ladder
        ladder = LinkingLadder(self.supabase)

        # Run ladder to determine primary
        result = await ladder.determine_primary(
            yacht_id=yacht_id,
            thread_id=thread_id,
            subject=subject,
            from_address=from_address,
            attachments=None,  # TODO: Load if needed
            participant_hashes=None,  # TODO: Load if needed
            context=None
        )

        # If we got a result with actionable suggestions, create them
        if result and result.get('action') in ('auto_link', 'suggest', 'weak_suggest'):
            suggestions_created = await ladder.create_link_suggestion(
                yacht_id=yacht_id,
                thread_id=thread_id,
                selection=result,
                max_suggestions=3
            )

            self.stats['suggestions_created'] += len(suggestions_created)

            logger.info(
                f"Thread {thread_id[:8]}...: Created {len(suggestions_created)} suggestions "
                f"(level={result.get('level')}, score={result.get('candidate', {}).get('score', 0)})"
            )
        else:
            logger.debug(f"Thread {thread_id[:8]}...: No suggestions (L5 or below threshold)")

        # Mark thread as suggestions_generated (even if no suggestions)
        await self._mark_suggestions_generated(thread_id)

    async def _get_threads_needing_suggestions(self) -> List[Dict[str, Any]]:
        """
        Query threads that have extracted_tokens but no suggestions_generated_at.

        Returns:
            List of thread records
        """
        try:
            result = self.supabase.table('email_threads').select(
                'id, yacht_id, latest_subject, latest_from_address, extracted_tokens'
            ).is_(
                'suggestions_generated_at', 'null'
            ).not_.is_(
                'extracted_tokens', 'null'
            ).order(
                'created_at', desc=True
            ).limit(BATCH_SIZE).execute()

            return result.data or []

        except Exception as e:
            logger.error(f"Error querying threads: {e}")
            return []

    async def _mark_suggestions_generated(self, thread_id: str):
        """
        Mark thread as suggestions_generated.

        Args:
            thread_id: Thread ID
        """
        try:
            self.supabase.table('email_threads').update({
                'suggestions_generated_at': datetime.utcnow().isoformat()
            }).eq('id', thread_id).execute()

        except Exception as e:
            logger.error(f"Error marking thread as suggestions_generated: {e}")

    def _log_stats(self):
        """Log worker statistics."""
        logger.info(
            f"Stats: cycles={self.stats['cycles']}, "
            f"threads={self.stats['threads_processed']}, "
            f"suggestions={self.stats['suggestions_created']}, "
            f"errors={self.stats['errors']}"
        )

    def stop(self):
        """Stop the worker gracefully."""
        logger.info("Stopping worker...")
        self.running = False


async def main():
    """Entry point."""
    if not ENABLED:
        logger.warning("Link suggester is disabled (LINK_SUGGESTER_ENABLED != true)")
        logger.warning("Set LINK_SUGGESTER_ENABLED=true to enable")
        return

    worker = LinkSuggesterWorker()

    try:
        await worker.run()
    except KeyboardInterrupt:
        worker.stop()
    except Exception as e:
        logger.error(f"Worker crashed: {e}")
        raise


if __name__ == '__main__':
    asyncio.run(main())
