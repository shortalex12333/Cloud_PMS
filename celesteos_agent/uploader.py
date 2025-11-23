"""
Upload manager for CelesteOS Local Agent.
Orchestrates file chunking, queuing, and cloud upload with retry logic.
Supports resumable uploads after interruption.
"""

import json
import time
from pathlib import Path
from typing import Optional, Dict, Any, List, Set
from concurrent.futures import ThreadPoolExecutor, as_completed

from .logger import get_logger
from .database import Database
from .hasher import FileHasher
from .chunker import FileChunker
from .api_client import RetryableAPIClient
from .telemetry import TelemetryCollector

logger = get_logger(__name__)


class UploadState:
    """Manages lightweight upload state for resumability."""

    def __init__(self, db: Database):
        """Initialize upload state manager.

        Args:
            db: Database instance
        """
        self.db = db

    def create_state(
        self,
        upload_queue_id: int,
        file_sha256: str,
        total_chunks: int
    ) -> int:
        """Create upload state record.

        Args:
            upload_queue_id: Upload queue ID
            file_sha256: File SHA256 hash
            total_chunks: Total number of chunks

        Returns:
            State record ID
        """
        with self.db.get_connection() as conn:
            cursor = conn.execute("""
                INSERT INTO upload_state (
                    upload_queue_id, file_sha256, total_chunks
                ) VALUES (?, ?, ?)
                ON CONFLICT(upload_queue_id) DO UPDATE SET
                    file_sha256 = excluded.file_sha256,
                    total_chunks = excluded.total_chunks,
                    updated_at = strftime('%s', 'now')
            """, (upload_queue_id, file_sha256, total_chunks))
            return cursor.lastrowid

    def get_state(self, upload_queue_id: int) -> Optional[Dict[str, Any]]:
        """Get upload state.

        Args:
            upload_queue_id: Upload queue ID

        Returns:
            State dict or None
        """
        with self.db.get_connection() as conn:
            row = conn.execute("""
                SELECT * FROM upload_state
                WHERE upload_queue_id = ?
            """, (upload_queue_id,)).fetchone()

            if row:
                state = dict(row)
                state['chunks_completed'] = json.loads(state['chunks_completed'])
                return state
            return None

    def mark_chunk_complete(self, upload_queue_id: int, chunk_index: int, chunk_size: int) -> None:
        """Mark a chunk as completed.

        Args:
            upload_queue_id: Upload queue ID
            chunk_index: Chunk index
            chunk_size: Chunk size in bytes
        """
        with self.db.get_connection() as conn:
            # Get current state
            row = conn.execute("""
                SELECT chunks_completed, bytes_uploaded, state_version
                FROM upload_state WHERE upload_queue_id = ?
            """, (upload_queue_id,)).fetchone()

            if not row:
                logger.warning(f"No upload state found for queue_id={upload_queue_id}")
                return

            chunks_completed = json.loads(row['chunks_completed'])
            if chunk_index not in chunks_completed:
                chunks_completed.append(chunk_index)
                chunks_completed.sort()

            bytes_uploaded = row['bytes_uploaded'] + chunk_size

            # Optimistic locking update
            conn.execute("""
                UPDATE upload_state SET
                    chunks_completed = ?,
                    last_chunk_uploaded = ?,
                    bytes_uploaded = ?,
                    last_activity = ?,
                    state_version = state_version + 1
                WHERE upload_queue_id = ?
                AND state_version = ?
            """, (
                json.dumps(chunks_completed),
                chunk_index,
                bytes_uploaded,
                int(time.time()),
                upload_queue_id,
                row['state_version']
            ))

    def get_pending_chunks(self, upload_queue_id: int, total_chunks: int) -> List[int]:
        """Get list of chunk indices that need to be uploaded.

        Args:
            upload_queue_id: Upload queue ID
            total_chunks: Total number of chunks

        Returns:
            List of pending chunk indices
        """
        state = self.get_state(upload_queue_id)

        if not state:
            return list(range(total_chunks))

        completed = set(state['chunks_completed'])
        return [i for i in range(total_chunks) if i not in completed]

    def is_complete(self, upload_queue_id: int) -> bool:
        """Check if all chunks are uploaded.

        Args:
            upload_queue_id: Upload queue ID

        Returns:
            True if complete
        """
        state = self.get_state(upload_queue_id)
        if not state:
            return False

        return len(state['chunks_completed']) >= state['total_chunks']

    def delete_state(self, upload_queue_id: int) -> None:
        """Delete upload state (after successful completion).

        Args:
            upload_queue_id: Upload queue ID
        """
        with self.db.get_connection() as conn:
            conn.execute("""
                DELETE FROM upload_state WHERE upload_queue_id = ?
            """, (upload_queue_id,))


class UploadManager:
    """Manages file upload lifecycle with resumability support."""

    # Retry delays in seconds
    RETRY_DELAYS = [5, 10, 30, 120, 300]  # 5s, 10s, 30s, 2min, 5min

    def __init__(
        self,
        db: Database,
        api_client: RetryableAPIClient,
        chunk_size_mb: int = 64,
        temp_dir: str = "~/.celesteos/tmp",
        max_concurrent_uploads: int = 3,
        telemetry: Optional[TelemetryCollector] = None
    ):
        """Initialize upload manager.

        Args:
            db: Database instance
            api_client: API client
            chunk_size_mb: Chunk size in MB
            temp_dir: Temporary directory
            max_concurrent_uploads: Max parallel uploads
            telemetry: Optional telemetry collector
        """
        self.db = db
        self.api = api_client
        self.hasher = FileHasher(num_workers=4)
        self.chunker = FileChunker(chunk_size_mb=chunk_size_mb, temp_dir=temp_dir)
        self.max_concurrent_uploads = max_concurrent_uploads
        self.executor = ThreadPoolExecutor(max_workers=max_concurrent_uploads)
        self.upload_state = UploadState(db)
        self.telemetry = telemetry

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
        """Upload a file with resumable chunk support.

        This method:
        1. Checks for existing upload state (for resume)
        2. Only chunks/uploads remaining chunks
        3. Maintains state for crash recovery
        4. Reports telemetry events

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
        filename = upload_job['filename']
        upload_start_time = time.time()

        if not file_path.exists():
            logger.error(f"File not found: {file_path}")
            self.db.update_upload_status(upload_queue_id, 'error', 'File not found')
            if self.telemetry:
                self.telemetry.log_upload_failed(
                    str(file_path), 'File not found', upload_job['retry_count']
                )
            return False

        try:
            # Check for existing upload state (resume scenario)
            existing_state = self.upload_state.get_state(upload_queue_id)
            is_resume = existing_state is not None and len(existing_state['chunks_completed']) > 0

            if is_resume:
                completed_count = len(existing_state['chunks_completed'])
                total_chunks = existing_state['total_chunks']
                logger.info(
                    f"Resuming upload: {filename} "
                    f"({completed_count}/{total_chunks} chunks completed)"
                )
                if self.telemetry:
                    self.telemetry.log_resume_detected(
                        str(file_path), completed_count, total_chunks
                    )
            else:
                logger.info(f"Starting new upload: {filename}")
                if self.telemetry:
                    self.telemetry.log_upload_started(
                        str(file_path),
                        upload_job['file_sha256'],
                        upload_job['file_size'],
                        upload_job['total_chunks'],
                        upload_job['upload_id']
                    )

            # Update status
            self.db.update_upload_status(upload_queue_id, 'uploading')

            # Chunk file (chunker handles caching if chunks exist)
            logger.info(f"Preparing chunks for: {file_path.name}")
            chunks = self.chunker.chunk_file(file_path, upload_job['file_sha256'])

            # Create upload state if not exists
            if not existing_state:
                self.upload_state.create_state(
                    upload_queue_id,
                    upload_job['file_sha256'],
                    len(chunks)
                )

            # Store chunk metadata in database (idempotent)
            for chunk in chunks:
                # Check if chunk record already exists
                with self.db.get_connection() as conn:
                    existing = conn.execute("""
                        SELECT id FROM upload_chunks
                        WHERE upload_queue_id = ? AND chunk_index = ?
                    """, (upload_queue_id, chunk['chunk_index'])).fetchone()

                    if not existing:
                        self.db.create_chunk(
                            upload_queue_id=upload_queue_id,
                            chunk_index=chunk['chunk_index'],
                            chunk_sha256=chunk['chunk_sha256'],
                            chunk_size=chunk['chunk_size'],
                            chunk_path=chunk['chunk_path']
                        )

            # Get pending chunks (skips already-uploaded)
            pending_indices = self.upload_state.get_pending_chunks(
                upload_queue_id, len(chunks)
            )

            if pending_indices:
                logger.info(f"Uploading {len(pending_indices)} remaining chunks")

            # Upload only pending chunks
            for chunk in chunks:
                if chunk['chunk_index'] not in pending_indices:
                    logger.debug(f"Skipping already-uploaded chunk {chunk['chunk_index']}")
                    continue

                chunk_start_time = time.time()

                logger.info(
                    f"Uploading chunk {chunk['chunk_index'] + 1}/{len(chunks)} "
                    f"for {filename}"
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

                chunk_duration_ms = int((time.time() - chunk_start_time) * 1000)

                # Update upload state (for resumability)
                self.upload_state.mark_chunk_complete(
                    upload_queue_id,
                    chunk['chunk_index'],
                    len(chunk_data)
                )

                # Update database records
                with self.db.get_connection() as conn:
                    chunk_record = conn.execute("""
                        SELECT id FROM upload_chunks
                        WHERE upload_queue_id = ? AND chunk_index = ?
                    """, (upload_queue_id, chunk['chunk_index'])).fetchone()

                    if chunk_record:
                        self.db.mark_chunk_uploaded(chunk_record['id'])

                self.db.increment_uploaded_chunks(upload_queue_id)

                # Log telemetry
                if self.telemetry:
                    self.telemetry.log_upload_chunk_completed(
                        str(file_path),
                        chunk['chunk_index'],
                        len(chunks),
                        chunk_duration_ms
                    )

            # Complete upload
            logger.info(f"Completing upload: {filename}")

            complete_response = self.api.complete_upload(
                upload_id=upload_job['upload_id'],
                total_chunks=len(chunks),
                sha256=upload_job['file_sha256'],
                filename=filename
            )

            upload_duration_ms = int((time.time() - upload_start_time) * 1000)

            # Update status
            self.db.update_upload_status(upload_queue_id, 'complete')
            self.db.update_file_status(upload_job['file_id'], 'uploaded')

            # Clean up upload state
            self.upload_state.delete_state(upload_queue_id)

            # Cleanup chunks
            self.chunker.cleanup_chunks(chunks)

            # Log activity
            self.db.log_activity(
                'upload_completed',
                f"Upload completed: {filename}",
                upload_queue_id=upload_queue_id
            )

            # Log telemetry
            if self.telemetry:
                self.telemetry.log_upload_completed(
                    str(file_path),
                    upload_job['file_sha256'],
                    upload_job['file_size'],
                    upload_duration_ms,
                    complete_response.get('document_id')
                )

            logger.info(
                f"Upload successful: {filename} "
                f"(document_id={complete_response.get('document_id')}, "
                f"duration={upload_duration_ms}ms)"
            )

            return True

        except Exception as e:
            logger.error(
                f"Upload failed for {filename}: {e}",
                exc_info=True
            )

            # Log telemetry
            if self.telemetry:
                self.telemetry.log_upload_failed(
                    str(file_path), str(e), upload_job['retry_count']
                )

            # Handle retry (state is preserved for resume)
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
                    f"(attempt {retry_count + 1}/{len(self.RETRY_DELAYS)}). "
                    f"State preserved for resume."
                )
            else:
                # Max retries exceeded
                self.db.update_upload_status(upload_queue_id, 'error', str(e))
                self.db.update_file_status(upload_job['file_id'], 'error')

                # Clean up state on permanent failure
                self.upload_state.delete_state(upload_queue_id)

                self.db.log_error(
                    error_type='upload_chunk',
                    severity='error',
                    message=f"Upload failed after {retry_count} retries: {e}",
                    upload_queue_id=upload_queue_id
                )

                logger.error(
                    f"Upload failed permanently after {retry_count} retries: "
                    f"{filename}"
                )

                # Cleanup chunks on permanent failure
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
