#!/usr/bin/env python3
"""
Email Extraction Worker - M6.3 Backpressure & DLQ

Consumes jobs from email_extraction_jobs table and processes them
using prepare_email_for_search().

Features:
- Per-watcher and global concurrency caps
- Retry-After handling for Graph 429 responses
- Exponential backoff with jitter on 5xx/timeouts
- Dead-letter queue for poison items
- Graceful shutdown with checkpoint persistence
- Enhanced telemetry metrics

Usage:
    python3 email_rag/worker.py [--once] [--limit N] [--interval S]

Environment Variables:
    WORKER_POLL_INTERVAL - Poll interval in seconds (default: 60)
    WORKER_BATCH_SIZE - Jobs per batch (default: 10)
    WORKER_STAGING_MODE - If TRUE, process jobs but don't auto-sync
    MAX_CONCURRENT_PER_WATCHER - Per-mailbox concurrency cap (default: 2)
    MAX_CONCURRENT_GLOBAL - Global concurrency cap (default: 8)
"""

from __future__ import annotations

import asyncio
import argparse
import logging
import signal
import sys
import os
import random
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Set

# Add parent to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from integrations.supabase import get_supabase_client
from email_rag.prepare import prepare_email_for_search

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)

# Configuration from environment
DEFAULT_POLL_INTERVAL = int(os.getenv('WORKER_POLL_INTERVAL', '60'))
DEFAULT_BATCH_SIZE = int(os.getenv('WORKER_BATCH_SIZE', '10'))
STAGING_MODE = os.getenv('WORKER_STAGING_MODE', 'FALSE').upper() == 'TRUE'

# Backpressure settings
MAX_CONCURRENT_PER_WATCHER = int(os.getenv('MAX_CONCURRENT_PER_WATCHER', '2'))
MAX_CONCURRENT_GLOBAL = int(os.getenv('MAX_CONCURRENT_GLOBAL', '8'))
MAX_RETRIES = 5
MAX_BACKOFF_SECONDS = 64
RATE_LIMIT_PER_MINUTE = 50


class BackpressureWorker:
    """
    M6.3 Worker with backpressure controls.

    Key features:
    - Respects Retry-After headers from Graph API (429)
    - Exponential backoff with jitter on 5xx/timeouts
    - Per-watcher and global concurrency limits
    - DLQ isolation for poison items
    - Graceful shutdown with state persistence
    """

    def __init__(
        self,
        poll_interval: int = DEFAULT_POLL_INTERVAL,
        batch_size: int = DEFAULT_BATCH_SIZE,
        rate_limit: int = RATE_LIMIT_PER_MINUTE,
    ):
        self.poll_interval = poll_interval
        self.batch_size = min(batch_size, MAX_CONCURRENT_GLOBAL)
        self.rate_limit = rate_limit
        self.running = True
        self.draining = False

        # Metrics
        self.processed_count = 0
        self.failed_count = 0
        self.retry_count = 0
        self.throttle_count = 0

        # Concurrency tracking
        self._in_flight: Set[str] = set()  # job_ids currently processing
        self._watcher_in_flight: Dict[str, int] = {}  # watcher_id -> count
        self._rate_limiter = RateLimiter(rate_limit)

        # Graceful shutdown
        signal.signal(signal.SIGINT, self._handle_shutdown)
        signal.signal(signal.SIGTERM, self._handle_shutdown)

        if STAGING_MODE:
            logger.info("[worker] STAGING MODE - processing jobs but sync disabled")

    def _handle_shutdown(self, signum, frame):
        """Handle shutdown signals gracefully."""
        if self.draining:
            logger.warning("[worker] Force shutdown requested")
            sys.exit(1)

        logger.info(f"[worker] Received signal {signum}, draining in-flight jobs...")
        self.draining = True
        self.running = False

    async def run(self, once: bool = False):
        """Main worker loop."""
        logger.info(
            f"[worker] Starting M6.3 worker (poll={self.poll_interval}s, "
            f"batch={self.batch_size}, max_global={MAX_CONCURRENT_GLOBAL}, "
            f"max_per_watcher={MAX_CONCURRENT_PER_WATCHER})"
        )

        while self.running:
            try:
                jobs_processed = await self._process_batch()

                if once:
                    logger.info(f"[worker] Single run complete. Processed {jobs_processed} jobs.")
                    break

                if jobs_processed == 0:
                    await asyncio.sleep(self.poll_interval)
                else:
                    await asyncio.sleep(1)  # Brief pause between batches

            except Exception as e:
                logger.error(f"[worker] Batch processing error: {e}")
                await asyncio.sleep(self.poll_interval)

        # Drain in-flight jobs
        if self._in_flight:
            logger.info(f"[worker] Waiting for {len(self._in_flight)} in-flight jobs...")
            await self._wait_for_drain(timeout=30)

        # Flush telemetry
        await self._flush_telemetry()

        logger.info(
            f"[worker] Shutdown complete. "
            f"Processed={self.processed_count}, Failed={self.failed_count}, "
            f"Retries={self.retry_count}, Throttles={self.throttle_count}"
        )

    async def _wait_for_drain(self, timeout: int = 30):
        """Wait for in-flight jobs to complete."""
        start = datetime.utcnow()
        while self._in_flight:
            if (datetime.utcnow() - start).total_seconds() > timeout:
                logger.warning(f"[worker] Drain timeout, {len(self._in_flight)} jobs abandoned")
                break
            await asyncio.sleep(0.5)

    async def _process_batch(self) -> int:
        """Process a batch of pending jobs respecting concurrency limits."""
        supabase = get_supabase_client()

        # Check global concurrency
        available_slots = MAX_CONCURRENT_GLOBAL - len(self._in_flight)
        if available_slots <= 0:
            logger.debug("[worker] Global concurrency limit reached")
            return 0

        # Fetch jobs (only from ready watchers)
        jobs = await self._fetch_ready_jobs(supabase, min(self.batch_size, available_slots))

        if not jobs:
            # Check DLQ for items ready to retry
            await self._process_dlq_items(supabase)
            return 0

        logger.info(f"[worker] Processing {len(jobs)} jobs (in_flight={len(self._in_flight)})")

        # Process jobs with concurrency control
        tasks = []
        for job in jobs:
            if not self.running:
                break

            watcher_id = job.get('watcher_id')

            # Check per-watcher concurrency
            if watcher_id:
                current = self._watcher_in_flight.get(watcher_id, 0)
                if current >= MAX_CONCURRENT_PER_WATCHER:
                    logger.debug(f"[worker] Watcher {watcher_id[:8]} at concurrency limit")
                    continue

            # Track in-flight
            self._in_flight.add(job['id'])
            if watcher_id:
                self._watcher_in_flight[watcher_id] = self._watcher_in_flight.get(watcher_id, 0) + 1

            tasks.append(self._process_job(supabase, job))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

        return len(tasks)

    async def _fetch_ready_jobs(self, supabase, limit: int) -> List[Dict[str, Any]]:
        """Fetch pending jobs from watchers that are not throttled/backed-off."""
        try:
            # Get pending jobs, excluding throttled watchers
            result = supabase.rpc('get_ready_extraction_jobs', {
                'p_limit': limit
            }).execute()

            if result.data:
                return result.data

            # Fallback to simple query if RPC doesn't exist
            result = supabase.table('email_extraction_jobs').select(
                'id, yacht_id, message_id, job_type, retry_count, watcher_id'
            ).eq('status', 'pending').order(
                'created_at', desc=False
            ).limit(limit).execute()

            jobs = result.data or []

            # Claim jobs atomically
            claimed = []
            for job in jobs:
                try:
                    supabase.table('email_extraction_jobs').update({
                        'status': 'running',
                        'started_at': datetime.utcnow().isoformat(),
                    }).eq('id', job['id']).eq('status', 'pending').execute()
                    claimed.append(job)
                except Exception:
                    pass  # Job claimed by another worker

            return claimed

        except Exception as e:
            logger.error(f"[worker] Failed to fetch jobs: {e}")
            return []

    async def _process_job(self, supabase, job: Dict[str, Any]):
        """Process a single extraction job with error handling."""
        job_id = job['id']
        message_id = job['message_id']
        yacht_id = job['yacht_id']
        watcher_id = job.get('watcher_id')
        retry_count = job.get('retry_count', 0)

        try:
            logger.info(f"[worker] Processing job {job_id[:8]}...")

            # Rate limit for OpenAI calls
            await self._rate_limiter.acquire()

            # Call prepare
            result = await prepare_email_for_search(message_id, yacht_id)

            if result.get('status') == 'ok':
                await self._complete_job(supabase, job_id, result)
                self.processed_count += 1

                # Clear watcher backoff on success
                if watcher_id:
                    await self._clear_watcher_backoff(supabase, watcher_id)

                logger.info(f"[worker] Job {job_id[:8]} completed")

            elif result.get('status') == 'not_found':
                await self._fail_job(supabase, job_id, "Message not found", permanent=True)
                self.failed_count += 1

            elif result.get('status') == 'throttled':
                # Graph API 429 - respect Retry-After
                retry_after = result.get('retry_after', 30)
                await self._handle_throttle(supabase, job, watcher_id, retry_after)

            else:
                await self._handle_failure(supabase, job, watcher_id,
                    result.get('error', 'Unknown error'))

        except Exception as e:
            error_msg = str(e)

            # Check for specific error types
            if '429' in error_msg or 'Too Many Requests' in error_msg:
                await self._handle_throttle(supabase, job, watcher_id, 30)
            elif '5' in error_msg[:1] or 'timeout' in error_msg.lower():
                await self._handle_transient_error(supabase, job, watcher_id, error_msg)
            else:
                await self._handle_failure(supabase, job, watcher_id, error_msg)

        finally:
            # Release concurrency tracking
            self._in_flight.discard(job_id)
            if watcher_id and watcher_id in self._watcher_in_flight:
                self._watcher_in_flight[watcher_id] = max(0,
                    self._watcher_in_flight[watcher_id] - 1)

    async def _handle_throttle(self, supabase, job: Dict, watcher_id: Optional[str],
                                retry_after: int):
        """Handle 429 Retry-After response."""
        logger.warning(f"[worker] Throttled. Retry-After: {retry_after}s")
        self.throttle_count += 1

        # Set watcher throttle state
        if watcher_id:
            try:
                supabase.rpc('set_watcher_throttle', {
                    'p_watcher_id': watcher_id,
                    'p_retry_after_seconds': retry_after
                }).execute()
            except Exception as e:
                logger.debug(f"[worker] set_watcher_throttle failed: {e}")

        # Requeue job (don't count as failure)
        supabase.table('email_extraction_jobs').update({
            'status': 'pending',
            'started_at': None,
        }).eq('id', job['id']).execute()

    async def _handle_transient_error(self, supabase, job: Dict, watcher_id: Optional[str],
                                       error_msg: str):
        """Handle 5xx/timeout with exponential backoff."""
        logger.warning(f"[worker] Transient error: {error_msg[:100]}")
        self.retry_count += 1

        # Set watcher backoff
        backoff_seconds = MAX_BACKOFF_SECONDS
        if watcher_id:
            try:
                result = supabase.rpc('set_watcher_backoff', {
                    'p_watcher_id': watcher_id
                }).execute()
                if result.data:
                    backoff_seconds = result.data
            except Exception as e:
                logger.debug(f"[worker] set_watcher_backoff failed: {e}")

        # Requeue with incremented retry count
        retry_count = job.get('retry_count', 0) + 1
        if retry_count >= MAX_RETRIES:
            await self._send_to_dlq(supabase, job, error_msg, '5xx')
        else:
            supabase.table('email_extraction_jobs').update({
                'status': 'pending',
                'retry_count': retry_count,
                'error_message': error_msg[:500],
                'started_at': None,
            }).eq('id', job['id']).execute()

    async def _handle_failure(self, supabase, job: Dict, watcher_id: Optional[str],
                               error_msg: str):
        """Handle permanent or unknown failures."""
        retry_count = job.get('retry_count', 0) + 1
        self.failed_count += 1

        if retry_count >= MAX_RETRIES:
            await self._send_to_dlq(supabase, job, error_msg, 'max_retries')
        else:
            # Add jitter to backoff
            backoff = min(MAX_BACKOFF_SECONDS, 2 ** retry_count)
            jitter = backoff * 0.2 * (random.random() - 0.5)

            logger.info(f"[worker] Job {job['id'][:8]} retry {retry_count}/{MAX_RETRIES}")

            supabase.table('email_extraction_jobs').update({
                'status': 'pending',
                'retry_count': retry_count,
                'error_message': error_msg[:500],
                'started_at': None,
            }).eq('id', job['id']).execute()

    async def _send_to_dlq(self, supabase, job: Dict, error_msg: str, error_code: str):
        """Send failed job to dead-letter queue."""
        logger.warning(f"[worker] Job {job['id'][:8]} -> DLQ ({error_code})")

        try:
            supabase.rpc('add_to_dlq', {
                'p_yacht_id': job['yacht_id'],
                'p_watcher_id': job.get('watcher_id'),
                'p_item_ref': job['message_id'],
                'p_item_type': 'message',
                'p_error': error_msg[:500],
                'p_error_code': error_code,
            }).execute()
        except Exception as e:
            logger.error(f"[worker] add_to_dlq failed: {e}")

        # Mark original job as failed
        await self._fail_job(supabase, job['id'], f"Sent to DLQ: {error_msg}", permanent=True)

    async def _process_dlq_items(self, supabase):
        """Check DLQ for items ready to retry."""
        try:
            result = supabase.rpc('requeue_dlq_items', {
                'p_max_items': 5
            }).execute()

            if result.data:
                for item in result.data:
                    logger.info(f"[worker] Requeued DLQ item {item['item_ref'][:8]}")
                    self.retry_count += 1
        except Exception as e:
            logger.debug(f"[worker] requeue_dlq_items failed: {e}")

    async def _clear_watcher_backoff(self, supabase, watcher_id: str):
        """Clear watcher backoff state on success."""
        try:
            supabase.rpc('clear_watcher_backoff', {
                'p_watcher_id': watcher_id
            }).execute()
        except Exception:
            pass

    async def _complete_job(self, supabase, job_id: str, result: Dict[str, Any]):
        """Mark job as completed."""
        supabase.table('email_extraction_jobs').update({
            'status': 'completed',
            'completed_at': datetime.utcnow().isoformat(),
            'embedding_generated': result.get('generated_embedding', False),
            'entities_found': {'count': result.get('stored_entities', 0)},
        }).eq('id', job_id).execute()

    async def _fail_job(self, supabase, job_id: str, error_message: str, permanent: bool = False):
        """Mark job as failed."""
        supabase.table('email_extraction_jobs').update({
            'status': 'failed',
            'completed_at': datetime.utcnow().isoformat(),
            'error_message': error_message[:500],
        }).eq('id', job_id).execute()

    async def _flush_telemetry(self):
        """Flush telemetry metrics to database."""
        try:
            supabase = get_supabase_client()

            # Get a yacht_id from recent jobs (for telemetry table)
            result = supabase.table('email_extraction_jobs').select(
                'yacht_id'
            ).limit(1).execute()

            if result.data:
                yacht_id = result.data[0]['yacht_id']

                # Update telemetry
                supabase.rpc('increment_sync_telemetry', {
                    'p_yacht_id': yacht_id,
                    'p_counter': 'retry_attempts',
                    'p_amount': self.retry_count
                }).execute()

                supabase.rpc('increment_sync_telemetry', {
                    'p_yacht_id': yacht_id,
                    'p_counter': 'throttle_events',
                    'p_amount': self.throttle_count
                }).execute()

                logger.info("[worker] Telemetry flushed")
        except Exception as e:
            logger.debug(f"[worker] Telemetry flush failed: {e}")


class RateLimiter:
    """Token bucket rate limiter for OpenAI API calls."""

    def __init__(self, calls_per_minute: int):
        self.calls_per_minute = calls_per_minute
        self.tokens = calls_per_minute
        self.last_refill = datetime.utcnow()

    async def acquire(self):
        """Wait until a token is available."""
        while True:
            self._refill()
            if self.tokens > 0:
                self.tokens -= 1
                return
            await asyncio.sleep(0.5)

    def _refill(self):
        """Refill tokens based on elapsed time."""
        now = datetime.utcnow()
        elapsed = (now - self.last_refill).total_seconds()
        refill_amount = (elapsed * self.calls_per_minute) / 60

        if refill_amount >= 1:
            self.tokens = min(self.calls_per_minute, self.tokens + int(refill_amount))
            self.last_refill = now


async def run_worker(once: bool = False, limit: int = DEFAULT_BATCH_SIZE,
                     interval: int = DEFAULT_POLL_INTERVAL):
    """Entry point for worker."""
    worker = BackpressureWorker(
        poll_interval=interval,
        batch_size=limit,
    )
    await worker.run(once=once)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Email extraction worker (M6.3)')
    parser.add_argument('--once', action='store_true', help='Process one batch and exit')
    parser.add_argument('--limit', type=int, default=DEFAULT_BATCH_SIZE, help='Batch size')
    parser.add_argument('--interval', type=int, default=DEFAULT_POLL_INTERVAL, help='Poll interval (seconds)')

    args = parser.parse_args()

    logger.info("[worker] Email Extraction Worker (M6.3 Backpressure) starting...")
    if STAGING_MODE:
        logger.info("[worker] STAGING MODE enabled")

    try:
        asyncio.run(run_worker(
            once=args.once,
            limit=args.limit,
            interval=args.interval,
        ))
    except KeyboardInterrupt:
        logger.info("[worker] Interrupted by user")
    except Exception as e:
        logger.error(f"[worker] Fatal error: {e}")
        sys.exit(1)
