#!/usr/bin/env python3
"""
Email RAG Background Worker

Polls email_extraction_jobs table and processes pending jobs:
- Generate vector embeddings
- Extract entities
- Match entities to database

Runs continuously until SIGTERM/SIGINT received.

For Render deployment: Run as separate Background Worker service.
Root directory: apps/api
Start command: python worker.py
"""

import os
import sys
import asyncio
import signal
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

# Configure logging - use stdout only (Render captures stdout)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Test yacht ID - only process this yacht in staging
TEST_YACHT_ID = "85fe1119-b04c-41ac-80f1-829d23322598"


class EmailRAGWorker:
    """Background worker for email RAG processing."""

    def __init__(
        self,
        poll_interval: int = 60,
        batch_size: int = 10,
        yacht_filter: Optional[str] = None
    ):
        """
        Initialize worker.

        Args:
            poll_interval: Seconds between polls (default 60)
            batch_size: Max jobs to process per batch (default 10)
            yacht_filter: If set, only process jobs for this yacht (staging mode)
        """
        self.poll_interval = poll_interval
        self.batch_size = batch_size
        self.yacht_filter = yacht_filter
        self.running = False
        self.supabase = None
        self.stats = {
            'jobs_processed': 0,
            'jobs_succeeded': 0,
            'jobs_failed': 0,
            'jobs_skipped': 0,
            'started_at': None,
            'last_poll': None
        }

    def _init_supabase(self):
        """Initialize Supabase client (lazy load)."""
        if self.supabase is None:
            from integrations.supabase import get_supabase_client
            self.supabase = get_supabase_client()
        return self.supabase

    def start(self):
        """Start the worker (blocking)."""
        logger.info("=" * 80)
        logger.info("EMAIL RAG WORKER STARTING")
        logger.info("=" * 80)
        logger.info(f"Poll interval: {self.poll_interval}s")
        logger.info(f"Batch size: {self.batch_size}")
        if self.yacht_filter:
            logger.info(f"Yacht filter: {self.yacht_filter} (staging mode)")
        logger.info("=" * 80)

        self.running = True
        self.stats['started_at'] = datetime.now(timezone.utc)

        # Register signal handlers
        signal.signal(signal.SIGTERM, self._handle_shutdown)
        signal.signal(signal.SIGINT, self._handle_shutdown)

        # Run main loop
        asyncio.run(self._run_loop())

    def _handle_shutdown(self, signum, frame):
        """Handle shutdown signals gracefully."""
        logger.info(f"Received signal {signum} - shutting down gracefully...")
        self.running = False

    async def _run_loop(self):
        """Main worker loop."""
        logger.info("Worker loop started")

        while self.running:
            try:
                self.stats['last_poll'] = datetime.now(timezone.utc)

                # Process batch of jobs
                processed = await self.process_batch()

                if processed > 0:
                    logger.info(f"Batch complete: {processed} jobs processed")
                else:
                    logger.debug("No pending jobs")

                # Sleep until next poll
                if self.running:
                    await asyncio.sleep(self.poll_interval)

            except Exception as e:
                logger.error(f"Error in worker loop: {e}", exc_info=True)
                # Continue running even on error
                await asyncio.sleep(self.poll_interval)

        logger.info("Worker loop stopped")
        self._print_stats()

    async def process_batch(self) -> int:
        """
        Process a batch of pending jobs.

        Returns:
            Number of jobs processed
        """
        try:
            supabase = self._init_supabase()

            # Build query for pending jobs
            query = supabase.table('email_extraction_jobs').select(
                'id, message_id, yacht_id, job_type, retry_count'
            ).eq('status', 'pending')

            # Apply yacht filter if in staging mode
            if self.yacht_filter:
                query = query.eq('yacht_id', self.yacht_filter)

            jobs = query.order(
                'created_at', desc=False
            ).limit(self.batch_size).execute()

            if not jobs.data:
                return 0

            logger.info(f"Processing {len(jobs.data)} jobs...")

            # Process each job
            for job in jobs.data:
                try:
                    await self.process_job(job)
                except Exception as e:
                    logger.error(f"Job {job['id']} failed: {e}", exc_info=True)
                    await self.mark_job_failed(job['id'], str(e))

            return len(jobs.data)

        except Exception as e:
            logger.error(f"Failed to fetch jobs: {e}", exc_info=True)
            return 0

    async def process_job(self, job: Dict[str, Any]):
        """
        Process a single extraction job.

        Args:
            job: Job record from email_extraction_jobs
        """
        job_id = job['id']
        message_id = job['message_id']
        yacht_id = job['yacht_id']

        logger.info(f"Processing job {job_id} (message {message_id})")

        supabase = self._init_supabase()

        # Mark job as processing
        supabase.table('email_extraction_jobs').update({
            'status': 'running',
            'started_at': datetime.now(timezone.utc).isoformat()
        }).eq('id', job_id).execute()

        # Fetch email message
        message_result = supabase.table('email_messages').select(
            'id, subject, preview_text, extraction_status'
        ).eq('id', message_id).eq('yacht_id', yacht_id).single().execute()

        if not message_result.data:
            raise Exception(f"Message {message_id} not found")

        message = message_result.data
        subject = message.get('subject', '') or ''
        preview_text = message.get('preview_text', '') or ''

        if not preview_text:
            logger.warning(f"Message {message_id} has no preview_text - skipping")
            await self.mark_job_skipped(job_id)
            return

        logger.info(f"  Subject: {subject[:60]}...")
        logger.info(f"  Preview: {preview_text[:80]}...")

        # Step 1: Generate embedding
        logger.info("  Generating embedding...")
        from email_rag.embedder import generate_email_embedding
        embedding = await generate_email_embedding(
            message_id=message_id,
            preview_text=preview_text,
            yacht_id=yacht_id,
            supabase=supabase
        )

        if not embedding:
            raise Exception("Embedding generation failed")

        logger.info(f"  ✅ Embedding generated ({len(embedding)}D)")

        # Step 2: Extract entities
        logger.info("  Extracting entities...")
        from email_rag.entity_extractor import extract_email_entities
        extraction_result = await extract_email_entities(
            message_id=message_id,
            subject=subject,
            preview_text=preview_text,
            yacht_id=yacht_id,
            supabase=supabase
        )

        entities = extraction_result.get('entities', [])
        matches = extraction_result.get('matches', {})
        total_matches = sum(len(m) for m in matches.values())

        logger.info(f"  ✅ Extracted {len(entities)} entities, {total_matches} DB matches")

        # Step 3: Mark job complete
        logger.info("  Marking job complete...")
        supabase.rpc('complete_email_extraction', {
            'p_job_id': job_id,
            'p_entities_found': {'entities': entities, 'matches': matches},
            'p_embedding_generated': True
        }).execute()

        logger.info(f"✅ Job {job_id} completed successfully")

        # Update stats
        self.stats['jobs_processed'] += 1
        self.stats['jobs_succeeded'] += 1

    async def mark_job_failed(self, job_id: str, error_message: str):
        """Mark job as failed and increment retry count."""
        try:
            supabase = self._init_supabase()

            # Get current job
            job = supabase.table('email_extraction_jobs').select(
                'retry_count'
            ).eq('id', job_id).single().execute()

            retry_count = (job.data.get('retry_count', 0) or 0) + 1
            max_retries = 3

            if retry_count >= max_retries:
                # Max retries reached - mark as failed
                status = 'failed'
                logger.error(f"Job {job_id} failed after {retry_count} attempts")
            else:
                # Retry - mark as pending
                status = 'pending'
                logger.warning(f"Job {job_id} failed, will retry ({retry_count}/{max_retries})")

            supabase.table('email_extraction_jobs').update({
                'status': status,
                'retry_count': retry_count,
                'error_message': error_message[:500]  # Truncate long errors
            }).eq('id', job_id).execute()

            self.stats['jobs_processed'] += 1
            if status == 'failed':
                self.stats['jobs_failed'] += 1

        except Exception as e:
            logger.error(f"Failed to mark job failed: {e}", exc_info=True)

    async def mark_job_skipped(self, job_id: str):
        """Mark job as completed but skipped (no preview_text)."""
        try:
            supabase = self._init_supabase()

            # Use 'completed' status (valid per DB constraint) with embedding_generated=false
            supabase.table('email_extraction_jobs').update({
                'status': 'completed',  # 'skipped' not valid - use 'completed' with flag
                'error_message': 'Skipped: No preview_text available',
                'embedding_generated': False,
                'completed_at': datetime.now(timezone.utc).isoformat()
            }).eq('id', job_id).execute()

            logger.info(f"Job {job_id} skipped (marked completed, no embedding)")

            self.stats['jobs_processed'] += 1
            self.stats['jobs_skipped'] += 1

        except Exception as e:
            logger.error(f"Failed to mark job skipped: {e}", exc_info=True)

    def _print_stats(self):
        """Print final statistics."""
        logger.info("=" * 80)
        logger.info("WORKER STATISTICS")
        logger.info("=" * 80)

        if self.stats['started_at']:
            uptime = datetime.now(timezone.utc) - self.stats['started_at']
            logger.info(f"Uptime: {uptime}")

        logger.info(f"Jobs processed: {self.stats['jobs_processed']}")
        logger.info(f"Jobs succeeded: {self.stats['jobs_succeeded']}")
        logger.info(f"Jobs failed: {self.stats['jobs_failed']}")
        logger.info(f"Jobs skipped: {self.stats['jobs_skipped']}")

        if self.stats['jobs_processed'] > 0:
            success_rate = (self.stats['jobs_succeeded'] / self.stats['jobs_processed']) * 100
            logger.info(f"Success rate: {success_rate:.1f}%")

        logger.info("=" * 80)

    def get_stats(self) -> Dict[str, Any]:
        """Get current statistics (for health checks)."""
        return self.stats.copy()


def main():
    """Entry point."""
    # Check environment variables
    required_env_vars = ['SUPABASE_URL', 'SUPABASE_SERVICE_KEY', 'OPENAI_API_KEY']
    missing = [var for var in required_env_vars if not os.getenv(var)]

    if missing:
        logger.error(f"Missing required environment variables: {', '.join(missing)}")
        sys.exit(1)

    # Parse args from environment
    poll_interval = int(os.getenv('WORKER_POLL_INTERVAL', '60'))
    batch_size = int(os.getenv('WORKER_BATCH_SIZE', '10'))

    # Staging mode - only process test yacht
    staging_mode = os.getenv('WORKER_STAGING_MODE', 'true').lower() == 'true'
    yacht_filter = TEST_YACHT_ID if staging_mode else None

    if yacht_filter:
        logger.info(f"Running in STAGING MODE - only processing yacht {yacht_filter}")

    # Start worker
    worker = EmailRAGWorker(
        poll_interval=poll_interval,
        batch_size=batch_size,
        yacht_filter=yacht_filter
    )
    worker.start()


if __name__ == '__main__':
    main()
