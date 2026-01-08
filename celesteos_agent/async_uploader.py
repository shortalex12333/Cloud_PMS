"""
Async upload manager for background, resilient uploads.

Architecture:
    - Background thread processes upload queue
    - Checks connection before uploads
    - Respects retry limits and backoff
    - Non-blocking UI operations
    - Progress tracking

Flow:
    1. Add file to queue → Returns immediately
    2. Background thread picks up file
    3. Check connection → Wait if offline
    4. Upload file → Handle success/failure
    5. Update queue status → Retry or complete
"""

import time
import threading
from pathlib import Path
from typing import Optional, Dict, Any, Callable
from datetime import datetime

from .upload_queue import UploadQueue, UploadQueueItem
from .connection_monitor import ConnectionMonitor
from .uploader import FileUploader, UploadError


class UploadProgress:
    """Track upload progress for UI updates."""

    def __init__(self):
        self.current_file: Optional[str] = None
        self.current_item_id: Optional[int] = None
        self.total_uploaded: int = 0
        self.total_failed: int = 0
        self.is_uploading: bool = False
        self.last_error: Optional[str] = None
        self.upload_start_time: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for UI."""
        return {
            'current_file': self.current_file,
            'current_item_id': self.current_item_id,
            'total_uploaded': self.total_uploaded,
            'total_failed': self.total_failed,
            'is_uploading': self.is_uploading,
            'last_error': self.last_error,
            'upload_duration': time.time() - self.upload_start_time if self.upload_start_time else None
        }


class AsyncUploadManager:
    """
    Manage async uploads with network resilience.

    Features:
        - Background upload processing
        - Connection monitoring
        - Retry with exponential backoff
        - Progress tracking
        - Thread-safe operations
    """

    def __init__(
        self,
        uploader: FileUploader,
        connection_monitor: ConnectionMonitor,
        upload_queue: Optional[UploadQueue] = None,
        on_upload_complete: Optional[Callable[[UploadQueueItem, Dict[str, Any]], None]] = None,
        on_upload_failed: Optional[Callable[[UploadQueueItem, str], None]] = None
    ):
        """
        Initialize async upload manager.

        Args:
            uploader: FileUploader instance
            connection_monitor: ConnectionMonitor instance
            upload_queue: UploadQueue instance (creates default if None)
            on_upload_complete: Callback(item, result) on successful upload
            on_upload_failed: Callback(item, error) on permanent failure
        """
        self.uploader = uploader
        self.connection_monitor = connection_monitor
        self.upload_queue = upload_queue or UploadQueue()
        self.on_upload_complete = on_upload_complete
        self.on_upload_failed = on_upload_failed

        self.progress = UploadProgress()
        self._lock = threading.Lock()
        self._stop_processing = threading.Event()
        self._processor_thread: Optional[threading.Thread] = None
        self._paused = False

    def add_to_queue(
        self,
        file_path: str,
        system_path: str,
        directories: list,
        doc_type: str,
        system_tag: str,
        priority: int = 5
    ) -> int:
        """
        Add file to upload queue (non-blocking).

        Args:
            file_path: Absolute path to file
            system_path: Relative path from NAS root
            directories: Directory hierarchy
            doc_type: Document type
            system_tag: System tag
            priority: Priority (1-10, higher first)

        Returns:
            Queue item ID
        """
        item_id = self.upload_queue.add(
            file_path=file_path,
            yacht_id=self.uploader.yacht_id,
            system_path=system_path,
            directories=directories,
            doc_type=doc_type,
            system_tag=system_tag,
            priority=priority
        )

        print(f"📋 Added to queue: {Path(file_path).name} (ID: {item_id}, Priority: {priority})")
        return item_id

    def start_processing(self):
        """Start background upload processing."""
        if self._processor_thread and self._processor_thread.is_alive():
            print("⚠️  Upload processor already running")
            return

        self._stop_processing.clear()
        self._paused = False
        self._processor_thread = threading.Thread(
            target=self._processing_loop,
            daemon=True,
            name="AsyncUploadProcessor"
        )
        self._processor_thread.start()
        print("🚀 Started background upload processor")

    def stop_processing(self):
        """Stop background upload processing."""
        if not self._processor_thread or not self._processor_thread.is_alive():
            return

        print("⏹  Stopping upload processor...")
        self._stop_processing.set()
        self._processor_thread.join(timeout=30)
        print("✅ Upload processor stopped")

    def pause(self):
        """Pause upload processing (finish current upload)."""
        self._paused = True
        print("⏸  Upload processing paused")

    def resume(self):
        """Resume upload processing."""
        self._paused = False
        print("▶️  Upload processing resumed")

    def _processing_loop(self):
        """Background processing loop."""
        print("🔄 Upload processor started")

        while not self._stop_processing.is_set():
            try:
                # Check if paused
                if self._paused:
                    time.sleep(5)
                    continue

                # Get next item from queue
                item = self.upload_queue.get_next()

                if not item:
                    # Queue empty, wait and check again
                    time.sleep(5)
                    continue

                # Process upload
                self._process_upload(item)

            except Exception as e:
                print(f"❌ Error in processing loop: {e}")
                time.sleep(10)

        print("🔄 Upload processor stopped")

    def _process_upload(self, item: UploadQueueItem):
        """
        Process single upload with retry logic.

        Args:
            item: Upload queue item
        """
        file_path = Path(item.file_path)
        filename = file_path.name

        # Update progress
        with self._lock:
            self.progress.current_file = filename
            self.progress.current_item_id = item.item_id
            self.progress.is_uploading = True
            self.progress.upload_start_time = time.time()

        try:
            # Check if file still exists
            if not file_path.exists():
                error_msg = f"File not found: {file_path}"
                print(f"❌ {error_msg}")
                self.upload_queue.mark_failed(item.item_id, error_msg, retry=False)
                self._update_progress_failed(error_msg)
                return

            # Wait for backoff if retrying
            if item.retry_count > 0:
                backoff_seconds = self.upload_queue.get_backoff_seconds(item.retry_count)
                print(f"⏳ Retry {item.retry_count}/{item.max_retries} - waiting {backoff_seconds}s (backoff)...")
                time.sleep(backoff_seconds)

            # Check connection before upload
            print(f"🔍 Checking connection for: {filename}")
            if not self.connection_monitor.check_connectivity():
                print(f"📡 Offline - waiting for connection...")

                # Wait for connection (max 5 minutes)
                if not self.connection_monitor.wait_for_connection(max_wait=300):
                    error_msg = "Connection timeout - will retry later"
                    print(f"⏸  {error_msg}")
                    self.upload_queue.mark_failed(item.item_id, error_msg, retry=True)
                    self._update_progress_failed(error_msg)
                    return

            # Check connection quality
            recommendation = self.connection_monitor.get_upload_recommendation()
            if not recommendation['should_upload']:
                print(f"⏸  {recommendation['reason']} - will retry later")
                time.sleep(recommendation['wait_seconds'])
                self.upload_queue.mark_failed(
                    item.item_id,
                    recommendation['reason'],
                    retry=True
                )
                self._update_progress_failed(recommendation['reason'])
                return

            # Mark as uploading
            self.upload_queue.mark_uploading(item.item_id)

            # Perform upload
            print(f"📤 Uploading: {filename} (Attempt {item.retry_count + 1}/{item.max_retries + 1})")

            result = self.uploader.upload_file(
                file_path=file_path,
                system_path=item.system_path,
                directories=item.directories,
                doc_type=item.doc_type,
                system_tag=item.system_tag
            )

            # Success
            self.upload_queue.mark_completed(item.item_id)
            self._update_progress_success()

            print(f"✅ Upload complete: {filename} (Status: {result.get('status')})")

            # Trigger callback
            if self.on_upload_complete:
                try:
                    self.on_upload_complete(item, result)
                except Exception as e:
                    print(f"⚠️  Error in upload complete callback: {e}")

        except UploadError as e:
            # Upload failed
            error_msg = str(e)
            print(f"❌ Upload failed: {filename} - {error_msg}")

            # Determine if retriable
            retry = True
            if "413" in error_msg or "415" in error_msg:
                # File too large or wrong type - don't retry
                retry = False

            self.upload_queue.mark_failed(item.item_id, error_msg, retry=retry)
            self._update_progress_failed(error_msg)

            # Trigger callback if permanently failed
            if not retry or item.retry_count >= item.max_retries - 1:
                if self.on_upload_failed:
                    try:
                        self.on_upload_failed(item, error_msg)
                    except Exception as e:
                        print(f"⚠️  Error in upload failed callback: {e}")

        except Exception as e:
            # Unexpected error
            error_msg = f"Unexpected error: {e}"
            print(f"❌ {error_msg}")
            self.upload_queue.mark_failed(item.item_id, error_msg, retry=True)
            self._update_progress_failed(error_msg)

        finally:
            # Clear progress
            with self._lock:
                self.progress.is_uploading = False
                self.progress.current_file = None
                self.progress.current_item_id = None
                self.progress.upload_start_time = None

    def _update_progress_success(self):
        """Update progress counters on success."""
        with self._lock:
            self.progress.total_uploaded += 1
            self.progress.last_error = None

    def _update_progress_failed(self, error_msg: str):
        """Update progress counters on failure."""
        with self._lock:
            self.progress.total_failed += 1
            self.progress.last_error = error_msg

    def get_progress(self) -> Dict[str, Any]:
        """Get current upload progress."""
        with self._lock:
            progress = self.progress.to_dict()

        # Add queue status
        queue_status = self.upload_queue.get_status()
        progress.update({
            'queue_pending': queue_status['pending'],
            'queue_completed': queue_status['completed'],
            'queue_failed': queue_status['failed'],
            'queue_total': queue_status['total']
        })

        # Add connection status
        conn_state = self.connection_monitor.get_state()
        progress.update({
            'connection_online': conn_state['is_online'],
            'connection_quality': self.connection_monitor.get_quality_score()
        })

        return progress

    def get_queue_status(self) -> Dict[str, Any]:
        """Get detailed queue status."""
        status = self.upload_queue.get_status()

        # Add pending items
        pending = self.upload_queue.get_all_pending()
        status['pending_items'] = [
            {
                'item_id': item.item_id,
                'filename': Path(item.file_path).name,
                'priority': item.priority,
                'retry_count': item.retry_count,
                'created_at': item.created_at
            }
            for item in pending
        ]

        # Add failed items
        failed = self.upload_queue.get_failed()
        status['failed_items'] = [
            {
                'item_id': item.item_id,
                'filename': Path(item.file_path).name,
                'error': item.error_message,
                'retry_count': item.retry_count,
                'updated_at': item.updated_at
            }
            for item in failed
        ]

        return status

    def retry_all_failed(self):
        """Retry all permanently failed items."""
        failed = self.upload_queue.get_failed()
        for item in failed:
            self.upload_queue.retry_failed(item.item_id)
            print(f"🔄 Retrying: {Path(item.file_path).name} (ID: {item.item_id})")

    def clear_old_completed(self, hours: int = 24):
        """Clear completed items older than specified hours."""
        self.upload_queue.clear_completed(older_than_hours=hours)
        print(f"🗑️  Cleared completed items older than {hours} hours")


def create_async_uploader(
    webhook_endpoint: str,
    yacht_id: str,
    yacht_salt: str,
    auto_start: bool = True
) -> AsyncUploadManager:
    """
    Convenience function to create async upload manager with monitoring.

    Args:
        webhook_endpoint: API endpoint
        yacht_id: Yacht UUID
        yacht_salt: Salt for signature
        auto_start: Start processing automatically

    Returns:
        AsyncUploadManager instance
    """
    from .connection_monitor import create_monitor

    # Create components
    uploader = FileUploader(
        webhook_endpoint=webhook_endpoint,
        yacht_id=yacht_id,
        yacht_salt=yacht_salt
    )

    health_endpoint = f"{webhook_endpoint}/health"
    monitor = create_monitor(health_endpoint, auto_start=True)

    queue = UploadQueue()

    # Create manager
    manager = AsyncUploadManager(
        uploader=uploader,
        connection_monitor=monitor,
        upload_queue=queue
    )

    if auto_start:
        manager.start_processing()

    return manager
