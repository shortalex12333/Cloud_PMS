"""
Upload manager for CelesteOS Local Agent.
Orchestrates file chunking, queuing, and cloud upload with retry logic.
"""

import time
from pathlib import Path
from typing import Optional, Dict, Any, List
from concurrent.futures import ThreadPoolExecutor, as_completed

from .logger import get_logger
from .database import Database
from .hasher import FileHasher
from .chunker import FileChunker
from .api_client import RetryableAPIClient

logger = get_logger(__name__)


class UploadManager:
    """Manages file upload lifecycle."""

    # Retry delays in seconds
    RETRY_DELAYS = [5, 10, 30, 120, 300]  # 5s, 10s, 30s, 2min, 5min

    def __init__(
        self,
        db: Database,
        api_client: RetryableAPIClient,
        chunk_size_mb: int = 64,
        temp_dir: str = "~/.celesteos/tmp",
        max_concurrent_uploads: int = 3
    ):
        """Initialize upload manager.

        Args:
            db: Database instance
            api_client: API client
            chunk_size_mb: Chunk size in MB
            temp_dir: Temporary directory
            max_concurrent_uploads: Max parallel uploads
        """
        self.db = db
        self.api = api_client
        self.hasher = FileHasher(num_workers=4)
        self.chunker = FileChunker(chunk_size_mb=chunk_size_mb, temp_dir=temp_dir)
        self.max_concurrent_uploads = max_concurrent_uploads
        self.executor = ThreadPoolExecutor(max_workers=max_concurrent_uploads)

    def prepare_file_for_upload(self, file_path: str, file_id: int) -> Optional[int]:
        """Prepare a file for upload by computing hash and creating chunks.

        Args:
            file_path: Absolute path to file
            file_id: File ID from database

        Returns:
            Upload queue ID or None if failed
        """
        file_path_obj = Path(file_path)

        if not file_path_obj.exists():
            logger.error(f"File not found: {file_path}")
            self.db.update_file_status(file_id, 'error')
            return None

        try:
            # Get file info from database
            file_record = self.db.get_connection().__enter__().execute(
                "SELECT * FROM files WHERE id = ?", (file_id,)
            ).fetchone()
            file_record = dict(file_record)

            # Compute or verify SHA256
            if not file_record.get('sha256'):
                logger.info(f"Computing SHA256 for {file_path_obj.name}")
                sha256 = self.hasher.compute_hash(file_path_obj)

                # Update database
                self.db.get_connection().__enter__().execute(
                    "UPDATE files SET sha256 = ?, last_hashed = ? WHERE id = ?",
                    (sha256, int(time.time()), file_id)
                )
            else:
                sha256 = file_record['sha256']

            file_size = file_path_obj.stat().st_size

            # Calculate total chunks
            total_chunks = (file_size + self.chunker.chunk_size_bytes - 1) // self.chunker.chunk_size_bytes

            # Initialize upload with cloud
            logger.info(f"Initializing upload for {file_record['filename']}")

            init_response = self.api.init_upload(
                filename=file_record['filename'],
                sha256=sha256,
                size_bytes=file_size,
                source='nas'
            )

            upload_id = init_response['upload_id']

            # Create upload job in database
            upload_queue_id = self.db.create_upload_job(
                file_id=file_id,
                upload_id=upload_id,
                file_sha256=sha256,
                filename=file_record['filename'],
                local_path=str(file_path_obj),
                file_size=file_size,
                total_chunks=total_chunks,
                chunk_size_mb=self.chunker.chunk_size_bytes // (1024 * 1024)
            )

            # Update file status
            self.db.update_file_status(file_id, 'queued')

            logger.info(
                f"Upload prepared: {file_record['filename']} "
                f"(upload_queue_id={upload_queue_id}, upload_id={upload_id})"
            )

            return upload_queue_id

        except Exception as e:
            logger.error(f"Failed to prepare file for upload: {e}", exc_info=True)
            self.db.log_error(
                error_type='upload_init',
                severity='error',
                message=f"Failed to prepare upload: {e}",
                file_id=file_id
            )
            self.db.update_file_status(file_id, 'error')
            return None

    def upload_file(self, upload_queue_id: int) -> bool:
        """Upload a file (chunk, upload, complete).

        Args:
            upload_queue_id: Upload queue ID

        Returns:
            True if successful
        """
        upload_job = self.db.get_upload_job(upload_queue_id)

        if not upload_job:
            logger.error(f"Upload job not found: {upload_queue_id}")
            return False

        file_path = Path(upload_job['local_path'])

        if not file_path.exists():
            logger.error(f"File not found: {file_path}")
            self.db.update_upload_status(upload_queue_id, 'error', 'File not found')
            return False

        try:
            logger.info(f"Starting upload: {upload_job['filename']}")

            # Update status
            self.db.update_upload_status(upload_queue_id, 'uploading')

            # Chunk file
            logger.info(f"Chunking file: {file_path.name}")
            chunks = self.chunker.chunk_file(file_path, upload_job['file_sha256'])

            # Store chunk metadata in database
            for chunk in chunks:
                self.db.create_chunk(
                    upload_queue_id=upload_queue_id,
                    chunk_index=chunk['chunk_index'],
                    chunk_sha256=chunk['chunk_sha256'],
                    chunk_size=chunk['chunk_size'],
                    chunk_path=chunk['chunk_path']
                )

            # Upload each chunk
            for chunk in chunks:
                logger.info(
                    f"Uploading chunk {chunk['chunk_index'] + 1}/{len(chunks)} "
                    f"for {upload_job['filename']}"
                )

                # Read chunk data
                with open(chunk['chunk_path'], 'rb') as f:
                    chunk_data = f.read()

                # Upload chunk
                self.api.upload_chunk(
                    upload_id=upload_job['upload_id'],
                    chunk_index=chunk['chunk_index'],
                    chunk_sha256=chunk['chunk_sha256'],
                    chunk_data=chunk_data
                )

                # Update database
                chunk_id = self.db.get_connection().__enter__().execute(
                    "SELECT id FROM upload_chunks WHERE upload_queue_id = ? AND chunk_index = ?",
                    (upload_queue_id, chunk['chunk_index'])
                ).fetchone()['id']

                self.db.mark_chunk_uploaded(chunk_id)
                self.db.increment_uploaded_chunks(upload_queue_id)

            # Complete upload
            logger.info(f"Completing upload: {upload_job['filename']}")

            complete_response = self.api.complete_upload(
                upload_id=upload_job['upload_id'],
                total_chunks=len(chunks),
                sha256=upload_job['file_sha256'],
                filename=upload_job['filename']
            )

            # Update status
            self.db.update_upload_status(upload_queue_id, 'complete')
            self.db.update_file_status(upload_job['file_id'], 'uploaded')

            # Cleanup chunks
            self.chunker.cleanup_chunks(chunks)

            # Log activity
            self.db.log_activity(
                'upload_completed',
                f"Upload completed: {upload_job['filename']}",
                upload_queue_id=upload_queue_id
            )

            logger.info(
                f"Upload successful: {upload_job['filename']} "
                f"(document_id={complete_response.get('document_id')})"
            )

            return True

        except Exception as e:
            logger.error(
                f"Upload failed for {upload_job['filename']}: {e}",
                exc_info=True
            )

            # Handle retry
            retry_count = upload_job['retry_count']

            if retry_count < len(self.RETRY_DELAYS):
                next_delay = self.RETRY_DELAYS[retry_count]

                self.db.increment_upload_retry(
                    upload_queue_id,
                    error=str(e),
                    next_retry_delay=next_delay
                )

                logger.warning(
                    f"Upload will retry in {next_delay}s "
                    f"(attempt {retry_count + 1}/{len(self.RETRY_DELAYS)})"
                )
            else:
                # Max retries exceeded
                self.db.update_upload_status(upload_queue_id, 'error', str(e))
                self.db.update_file_status(upload_job['file_id'], 'error')

                self.db.log_error(
                    error_type='upload_chunk',
                    severity='error',
                    message=f"Upload failed after {retry_count} retries: {e}",
                    upload_queue_id=upload_queue_id
                )

                logger.error(
                    f"Upload failed permanently after {retry_count} retries: "
                    f"{upload_job['filename']}"
                )

            # Cleanup chunks on failure
            try:
                self.chunker.cleanup_by_sha(upload_job['file_sha256'])
            except Exception as cleanup_error:
                logger.warning(f"Chunk cleanup failed: {cleanup_error}")

            return False

    def process_upload_queue(self) -> Dict[str, int]:
        """Process pending uploads from queue.

        Returns:
            Statistics dict with counts
        """
        logger.info("Processing upload queue")

        stats = {
            'processed': 0,
            'successful': 0,
            'failed': 0,
            'skipped': 0
        }

        # Get pending uploads
        pending = self.db.get_pending_uploads(limit=self.max_concurrent_uploads * 2)

        if not pending:
            logger.debug("No pending uploads")
            return stats

        logger.info(f"Found {len(pending)} pending uploads")

        # Update sync state
        self.db.update_sync_state({
            'is_uploading': True,
            'last_upload_at': int(time.time())
        })

        # Submit upload jobs to executor
        futures = []
        for upload_job in pending[:self.max_concurrent_uploads]:
            future = self.executor.submit(self.upload_file, upload_job['id'])
            futures.append((future, upload_job))
            stats['processed'] += 1

        # Wait for completion
        for future, upload_job in futures:
            try:
                success = future.result(timeout=3600)  # 1 hour timeout per upload
                if success:
                    stats['successful'] += 1
                else:
                    stats['failed'] += 1
            except Exception as e:
                logger.error(f"Upload job failed: {e}")
                stats['failed'] += 1

        # Update sync state
        self.db.update_sync_state({'is_uploading': False})

        logger.info(
            f"Upload queue processed: {stats['successful']} successful, "
            f"{stats['failed']} failed, {stats['skipped']} skipped"
        )

        return stats

    def shutdown(self) -> None:
        """Shutdown upload manager."""
        logger.info("Shutting down upload manager")
        self.executor.shutdown(wait=True)
        self.hasher.shutdown()
        self.api.close()
