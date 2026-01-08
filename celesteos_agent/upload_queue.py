"""
SQLite-based persistent upload queue for network resilience.

Architecture:
    - Queue survives crashes and restarts
    - Priority-based queuing (higher priority = processed first)
    - Retry tracking with exponential backoff
    - Status tracking (pending, uploading, completed, failed)
    - Thread-safe operations

Flow:
    1. Add file to queue → SQLite insert
    2. Get next file → Priority-based select
    3. Mark uploading → Update status
    4. Upload completes → Mark completed OR retry
    5. Failed permanently → Mark failed
"""

import sqlite3
import time
import json
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime
import threading


class UploadQueueItem:
    """Represents a single upload queue item."""

    def __init__(
        self,
        item_id: int,
        file_path: str,
        yacht_id: str,
        system_path: str,
        directories: List[str],
        doc_type: str,
        system_tag: str,
        priority: int = 5,
        status: str = "pending",
        retry_count: int = 0,
        max_retries: int = 3,
        created_at: str = None,
        updated_at: str = None,
        error_message: str = None
    ):
        self.item_id = item_id
        self.file_path = file_path
        self.yacht_id = yacht_id
        self.system_path = system_path
        self.directories = directories if isinstance(directories, list) else json.loads(directories)
        self.doc_type = doc_type
        self.system_tag = system_tag
        self.priority = priority
        self.status = status
        self.retry_count = retry_count
        self.max_retries = max_retries
        self.created_at = created_at or datetime.utcnow().isoformat()
        self.updated_at = updated_at or datetime.utcnow().isoformat()
        self.error_message = error_message

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'item_id': self.item_id,
            'file_path': self.file_path,
            'yacht_id': self.yacht_id,
            'system_path': self.system_path,
            'directories': self.directories,
            'doc_type': self.doc_type,
            'system_tag': self.system_tag,
            'priority': self.priority,
            'status': self.status,
            'retry_count': self.retry_count,
            'max_retries': self.max_retries,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'error_message': self.error_message
        }


class UploadQueue:
    """
    Persistent upload queue using SQLite.

    Features:
        - Survives crashes/restarts
        - Priority-based queuing
        - Retry with exponential backoff
        - Thread-safe operations
        - Status tracking
    """

    def __init__(self, db_path: str = None):
        """
        Initialize upload queue.

        Args:
            db_path: Path to SQLite database (default: ~/.celesteos/upload_queue.db)
        """
        if db_path is None:
            # Default location
            home = Path.home()
            celesteos_dir = home / ".celesteos"
            celesteos_dir.mkdir(exist_ok=True)
            db_path = str(celesteos_dir / "upload_queue.db")

        self.db_path = db_path
        self._lock = threading.Lock()
        self._init_db()

    def _init_db(self):
        """Create database tables if they don't exist."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS upload_queue (
                    item_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_path TEXT NOT NULL,
                    yacht_id TEXT NOT NULL,
                    system_path TEXT NOT NULL,
                    directories TEXT NOT NULL,  -- JSON array
                    doc_type TEXT NOT NULL,
                    system_tag TEXT NOT NULL,
                    priority INTEGER DEFAULT 5,
                    status TEXT DEFAULT 'pending',
                    retry_count INTEGER DEFAULT 0,
                    max_retries INTEGER DEFAULT 3,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    error_message TEXT
                )
            """)

            # Create indices for performance
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_status_priority
                ON upload_queue(status, priority DESC, created_at ASC)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_yacht_id
                ON upload_queue(yacht_id)
            """)

            conn.commit()

    def add(
        self,
        file_path: str,
        yacht_id: str,
        system_path: str,
        directories: List[str],
        doc_type: str,
        system_tag: str,
        priority: int = 5,
        max_retries: int = 3
    ) -> int:
        """
        Add file to upload queue.

        Args:
            file_path: Absolute path to file
            yacht_id: Yacht UUID
            system_path: Relative path from NAS root
            directories: Directory hierarchy
            doc_type: Document type (manual, schematic, etc.)
            system_tag: System tag (electrical, hvac, etc.)
            priority: Priority (1-10, higher = processed first)
            max_retries: Maximum retry attempts

        Returns:
            Queue item ID
        """
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    INSERT INTO upload_queue
                    (file_path, yacht_id, system_path, directories, doc_type,
                     system_tag, priority, max_retries, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    file_path,
                    yacht_id,
                    system_path,
                    json.dumps(directories),
                    doc_type,
                    system_tag,
                    priority,
                    max_retries,
                    datetime.utcnow().isoformat(),
                    datetime.utcnow().isoformat()
                ))
                conn.commit()
                return cursor.lastrowid

    def get_next(self) -> Optional[UploadQueueItem]:
        """
        Get next pending item to upload.

        Priority order:
            1. Higher priority first
            2. Older items first (FIFO within priority)

        Returns:
            Next upload item or None if queue empty
        """
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("""
                    SELECT * FROM upload_queue
                    WHERE status = 'pending'
                    ORDER BY priority DESC, created_at ASC
                    LIMIT 1
                """)
                row = cursor.fetchone()

                if row:
                    return UploadQueueItem(**dict(row))
                return None

    def mark_uploading(self, item_id: int):
        """Mark item as currently uploading."""
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    UPDATE upload_queue
                    SET status = 'uploading',
                        updated_at = ?
                    WHERE item_id = ?
                """, (datetime.utcnow().isoformat(), item_id))
                conn.commit()

    def mark_completed(self, item_id: int):
        """Mark item as successfully uploaded."""
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    UPDATE upload_queue
                    SET status = 'completed',
                        updated_at = ?
                    WHERE item_id = ?
                """, (datetime.utcnow().isoformat(), item_id))
                conn.commit()

    def mark_failed(self, item_id: int, error_message: str, retry: bool = True):
        """
        Mark item as failed.

        Args:
            item_id: Queue item ID
            error_message: Error description
            retry: If True, increment retry count and set to pending if retries remain
        """
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                # Get current item
                cursor = conn.execute("""
                    SELECT retry_count, max_retries FROM upload_queue
                    WHERE item_id = ?
                """, (item_id,))
                row = cursor.fetchone()

                if not row:
                    return

                retry_count, max_retries = row
                new_retry_count = retry_count + 1

                # Determine new status
                if retry and new_retry_count < max_retries:
                    # Still have retries left
                    new_status = 'pending'
                else:
                    # Permanently failed
                    new_status = 'failed'

                conn.execute("""
                    UPDATE upload_queue
                    SET status = ?,
                        retry_count = ?,
                        error_message = ?,
                        updated_at = ?
                    WHERE item_id = ?
                """, (
                    new_status,
                    new_retry_count,
                    error_message,
                    datetime.utcnow().isoformat(),
                    item_id
                ))
                conn.commit()

    def get_status(self) -> Dict[str, int]:
        """
        Get queue status summary.

        Returns:
            {
                'pending': count,
                'uploading': count,
                'completed': count,
                'failed': count,
                'total': count
            }
        """
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT status, COUNT(*) as count
                    FROM upload_queue
                    GROUP BY status
                """)

                status = {
                    'pending': 0,
                    'uploading': 0,
                    'completed': 0,
                    'failed': 0
                }

                for row in cursor:
                    status[row[0]] = row[1]

                status['total'] = sum(status.values())
                return status

    def get_all_pending(self) -> List[UploadQueueItem]:
        """Get all pending items (for display/monitoring)."""
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("""
                    SELECT * FROM upload_queue
                    WHERE status = 'pending'
                    ORDER BY priority DESC, created_at ASC
                """)

                return [UploadQueueItem(**dict(row)) for row in cursor.fetchall()]

    def get_failed(self) -> List[UploadQueueItem]:
        """Get all permanently failed items."""
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("""
                    SELECT * FROM upload_queue
                    WHERE status = 'failed'
                    ORDER BY updated_at DESC
                """)

                return [UploadQueueItem(**dict(row)) for row in cursor.fetchall()]

    def clear_completed(self, older_than_hours: int = 24):
        """
        Clear completed items older than specified hours.

        Args:
            older_than_hours: Remove completed items older than this (default 24h)
        """
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                cutoff_time = datetime.utcnow().timestamp() - (older_than_hours * 3600)
                cutoff_iso = datetime.fromtimestamp(cutoff_time).isoformat()

                conn.execute("""
                    DELETE FROM upload_queue
                    WHERE status = 'completed'
                    AND updated_at < ?
                """, (cutoff_iso,))
                conn.commit()

    def retry_failed(self, item_id: int):
        """Manually retry a failed item."""
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    UPDATE upload_queue
                    SET status = 'pending',
                        retry_count = 0,
                        error_message = NULL,
                        updated_at = ?
                    WHERE item_id = ?
                    AND status = 'failed'
                """, (datetime.utcnow().isoformat(), item_id))
                conn.commit()

    def remove(self, item_id: int):
        """Remove item from queue (any status)."""
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    DELETE FROM upload_queue
                    WHERE item_id = ?
                """, (item_id,))
                conn.commit()

    def get_backoff_seconds(self, retry_count: int) -> int:
        """
        Calculate exponential backoff delay.

        Args:
            retry_count: Current retry attempt (0-based)

        Returns:
            Seconds to wait before retry

        Formula: min(60 * (2 ^ retry_count), 3600)
        - Retry 0: 60s
        - Retry 1: 120s
        - Retry 2: 240s
        - Retry 3: 480s
        - Max: 3600s (1 hour)
        """
        base_delay = 60
        max_delay = 3600
        delay = base_delay * (2 ** retry_count)
        return min(delay, max_delay)
