"""
Database operations for CelesteOS Local Agent.
Manages SQLite database for file tracking, upload queue, and state.
"""

import sqlite3
import time
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from contextlib import contextmanager
from .logger import get_logger

logger = get_logger(__name__)


class Database:
    """SQLite database manager for CelesteOS agent."""

    def __init__(self, db_path: str = "~/.celesteos/celesteos.db"):
        """Initialize database connection.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path).expanduser()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn: Optional[sqlite3.Connection] = None

    @contextmanager
    def get_connection(self):
        """Get database connection context manager.

        Yields:
            sqlite3.Connection
        """
        conn = sqlite3.connect(
            self.db_path,
            timeout=30.0,
            check_same_thread=False
        )
        conn.row_factory = sqlite3.Row  # Return rows as dictionaries
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Database error: {e}", exc_info=True)
            raise
        finally:
            conn.close()

    def init(self, schema_path: Optional[Path] = None) -> None:
        """Initialize database schema.

        Args:
            schema_path: Optional path to schema.sql file
        """
        if schema_path is None:
            schema_path = Path(__file__).parent.parent / "schema.sql"

        if not schema_path.exists():
            raise FileNotFoundError(f"Schema file not found: {schema_path}")

        logger.info(f"Initializing database at: {self.db_path}")

        with open(schema_path, 'r') as f:
            schema_sql = f.read()

        with self.get_connection() as conn:
            conn.executescript(schema_sql)

        logger.info("Database initialized successfully")

    # ========================================
    # Yacht Identity
    # ========================================

    def set_yacht_identity(self, yacht_signature: str, yacht_name: Optional[str], api_endpoint: str) -> None:
        """Set yacht identity (upsert).

        Args:
            yacht_signature: Unique yacht signature
            yacht_name: Human-readable yacht name
            api_endpoint: Cloud API endpoint
        """
        with self.get_connection() as conn:
            conn.execute("""
                INSERT INTO yacht_identity (id, yacht_signature, yacht_name, api_endpoint)
                VALUES (1, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    yacht_signature = excluded.yacht_signature,
                    yacht_name = excluded.yacht_name,
                    api_endpoint = excluded.api_endpoint
            """, (yacht_signature, yacht_name, api_endpoint))

        logger.info(f"Yacht identity set: {yacht_name or yacht_signature}")

    def get_yacht_identity(self) -> Optional[Dict[str, Any]]:
        """Get yacht identity.

        Returns:
            Yacht identity dict or None
        """
        with self.get_connection() as conn:
            row = conn.execute("SELECT * FROM yacht_identity WHERE id = 1").fetchone()
            return dict(row) if row else None

    # ========================================
    # Agent Settings
    # ========================================

    def save_settings(self, settings: Dict[str, Any]) -> None:
        """Save agent settings.

        Args:
            settings: Settings dictionary
        """
        with self.get_connection() as conn:
            conn.execute("""
                INSERT INTO agent_settings (
                    id, nas_path, nas_type, nas_username, nas_host, nas_share,
                    scan_interval_minutes, deep_scan_interval_hours,
                    max_concurrent_uploads, chunk_size_mb, enabled
                ) VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    nas_path = excluded.nas_path,
                    nas_type = excluded.nas_type,
                    nas_username = excluded.nas_username,
                    nas_host = excluded.nas_host,
                    nas_share = excluded.nas_share,
                    scan_interval_minutes = excluded.scan_interval_minutes,
                    deep_scan_interval_hours = excluded.deep_scan_interval_hours,
                    max_concurrent_uploads = excluded.max_concurrent_uploads,
                    chunk_size_mb = excluded.chunk_size_mb,
                    enabled = excluded.enabled
            """, (
                settings.get('nas_path'),
                settings.get('nas_type', 'smb'),
                settings.get('nas_username'),
                settings.get('nas_host'),
                settings.get('nas_share'),
                settings.get('scan_interval_minutes', 15),
                settings.get('deep_scan_interval_hours', 1),
                settings.get('max_concurrent_uploads', 3),
                settings.get('chunk_size_mb', 64),
                settings.get('enabled', True)
            ))

    def get_settings(self) -> Optional[Dict[str, Any]]:
        """Get agent settings.

        Returns:
            Settings dict or None
        """
        with self.get_connection() as conn:
            row = conn.execute("SELECT * FROM agent_settings WHERE id = 1").fetchone()
            return dict(row) if row else None

    # ========================================
    # File Registry
    # ========================================

    def upsert_file(self, file_path: str, filename: str, file_size: int,
                    file_extension: str, mime_type: str, sha256: str,
                    last_modified: int) -> int:
        """Insert or update file in registry.

        Args:
            file_path: Relative path from NAS root
            filename: File name
            file_size: File size in bytes
            file_extension: File extension
            mime_type: MIME type
            sha256: SHA256 hash
            last_modified: File modified timestamp

        Returns:
            File ID
        """
        now = int(time.time())

        with self.get_connection() as conn:
            # Check if file exists
            existing = conn.execute(
                "SELECT id, sha256, status FROM files WHERE file_path = ?",
                (file_path,)
            ).fetchone()

            if existing:
                file_id = existing['id']
                previous_sha256 = existing['sha256']
                status = existing['status']

                # Determine new status
                if previous_sha256 != sha256:
                    # File changed - reset to pending
                    new_status = 'pending'
                    logger.info(f"File changed: {filename}")
                else:
                    # File unchanged - keep status
                    new_status = status

                conn.execute("""
                    UPDATE files SET
                        filename = ?,
                        file_size = ?,
                        file_extension = ?,
                        mime_type = ?,
                        sha256 = ?,
                        previous_sha256 = ?,
                        status = ?,
                        last_seen = ?,
                        last_modified = ?,
                        last_hashed = ?
                    WHERE id = ?
                """, (
                    filename, file_size, file_extension, mime_type,
                    sha256, previous_sha256, new_status, now,
                    last_modified, now, file_id
                ))

            else:
                # New file
                cursor = conn.execute("""
                    INSERT INTO files (
                        file_path, filename, file_size, file_extension,
                        mime_type, sha256, status, last_modified, last_hashed
                    ) VALUES (?, ?, ?, ?, ?, ?, 'pending', ?, ?)
                """, (
                    file_path, filename, file_size, file_extension,
                    mime_type, sha256, last_modified, now
                ))
                file_id = cursor.lastrowid
                logger.info(f"New file discovered: {filename}")

            return file_id

    def get_file_by_path(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Get file by path.

        Args:
            file_path: File path

        Returns:
            File dict or None
        """
        with self.get_connection() as conn:
            row = conn.execute("SELECT * FROM files WHERE file_path = ?", (file_path,)).fetchone()
            return dict(row) if row else None

    def get_pending_files(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get files pending upload.

        Args:
            limit: Maximum number of files to return

        Returns:
            List of file dicts
        """
        with self.get_connection() as conn:
            rows = conn.execute("""
                SELECT * FROM v_pending_files
                ORDER BY file_size ASC
                LIMIT ?
            """, (limit,)).fetchall()
            return [dict(row) for row in rows]

    def mark_file_deleted(self, file_path: str) -> None:
        """Mark file as deleted.

        Args:
            file_path: File path
        """
        with self.get_connection() as conn:
            conn.execute(
                "UPDATE files SET status = 'deleted', last_seen = ? WHERE file_path = ?",
                (int(time.time()), file_path)
            )

    def update_file_status(self, file_id: int, status: str) -> None:
        """Update file status.

        Args:
            file_id: File ID
            status: New status
        """
        with self.get_connection() as conn:
            conn.execute(
                "UPDATE files SET status = ? WHERE id = ?",
                (status, file_id)
            )

    # ========================================
    # Upload Queue
    # ========================================

    def create_upload_job(self, file_id: int, upload_id: str, file_sha256: str,
                          filename: str, local_path: str, file_size: int,
                          total_chunks: int, chunk_size_mb: int) -> int:
        """Create new upload job.

        Args:
            file_id: File ID from files table
            upload_id: UUID from cloud /v1/ingest/init
            file_sha256: File SHA256 hash
            filename: Original filename
            local_path: Local file path
            file_size: File size in bytes
            total_chunks: Total number of chunks
            chunk_size_mb: Chunk size in MB

        Returns:
            Upload job ID
        """
        with self.get_connection() as conn:
            cursor = conn.execute("""
                INSERT INTO upload_queue (
                    file_id, upload_id, file_sha256, filename, local_path,
                    file_size, total_chunks, chunk_size_mb, status, started_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?)
            """, (
                file_id, upload_id, file_sha256, filename, local_path,
                file_size, total_chunks, chunk_size_mb, int(time.time())
            ))

            return cursor.lastrowid

    def get_upload_job(self, upload_queue_id: int) -> Optional[Dict[str, Any]]:
        """Get upload job by ID.

        Args:
            upload_queue_id: Upload queue ID

        Returns:
            Upload job dict or None
        """
        with self.get_connection() as conn:
            row = conn.execute("SELECT * FROM upload_queue WHERE id = ?", (upload_queue_id,)).fetchone()
            return dict(row) if row else None

    def get_pending_uploads(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get pending upload jobs.

        Args:
            limit: Maximum number to return

        Returns:
            List of upload job dicts
        """
        now = int(time.time())

        with self.get_connection() as conn:
            rows = conn.execute("""
                SELECT * FROM upload_queue
                WHERE status IN ('pending', 'initializing', 'uploading')
                AND (next_retry_at IS NULL OR next_retry_at <= ?)
                AND retry_count < max_retries
                ORDER BY created_at ASC
                LIMIT ?
            """, (now, limit)).fetchall()

            return [dict(row) for row in rows]

    def update_upload_status(self, upload_queue_id: int, status: str,
                             error: Optional[str] = None) -> None:
        """Update upload job status.

        Args:
            upload_queue_id: Upload queue ID
            status: New status
            error: Optional error message
        """
        now = int(time.time())
        updates = {"status": status}

        if status == 'complete':
            updates['completed_at'] = now

        if error:
            updates['last_error'] = error

        set_clause = ", ".join(f"{k} = ?" for k in updates.keys())
        values = list(updates.values()) + [upload_queue_id]

        with self.get_connection() as conn:
            conn.execute(
                f"UPDATE upload_queue SET {set_clause} WHERE id = ?",
                values
            )

    def increment_upload_retry(self, upload_queue_id: int, error: str, next_retry_delay: int) -> None:
        """Increment retry count and schedule next retry.

        Args:
            upload_queue_id: Upload queue ID
            error: Error message
            next_retry_delay: Seconds until next retry
        """
        now = int(time.time())
        next_retry = now + next_retry_delay

        with self.get_connection() as conn:
            conn.execute("""
                UPDATE upload_queue SET
                    retry_count = retry_count + 1,
                    last_error = ?,
                    last_retry_at = ?,
                    next_retry_at = ?,
                    status = 'error'
                WHERE id = ?
            """, (error, now, next_retry, upload_queue_id))

    def increment_uploaded_chunks(self, upload_queue_id: int) -> int:
        """Increment uploaded chunks counter.

        Args:
            upload_queue_id: Upload queue ID

        Returns:
            New uploaded_chunks count
        """
        with self.get_connection() as conn:
            conn.execute("""
                UPDATE upload_queue
                SET uploaded_chunks = uploaded_chunks + 1
                WHERE id = ?
            """, (upload_queue_id,))

            row = conn.execute(
                "SELECT uploaded_chunks FROM upload_queue WHERE id = ?",
                (upload_queue_id,)
            ).fetchone()

            return row['uploaded_chunks'] if row else 0

    # ========================================
    # Upload Chunks
    # ========================================

    def create_chunk(self, upload_queue_id: int, chunk_index: int,
                     chunk_sha256: str, chunk_size: int, chunk_path: str) -> int:
        """Create chunk record.

        Args:
            upload_queue_id: Upload queue ID
            chunk_index: Chunk index
            chunk_sha256: Chunk SHA256
            chunk_size: Chunk size in bytes
            chunk_path: Temporary local path

        Returns:
            Chunk ID
        """
        with self.get_connection() as conn:
            cursor = conn.execute("""
                INSERT INTO upload_chunks (
                    upload_queue_id, chunk_index, chunk_sha256, chunk_size, chunk_path
                ) VALUES (?, ?, ?, ?, ?)
            """, (upload_queue_id, chunk_index, chunk_sha256, chunk_size, chunk_path))

            return cursor.lastrowid

    def mark_chunk_uploaded(self, chunk_id: int) -> None:
        """Mark chunk as uploaded.

        Args:
            chunk_id: Chunk ID
        """
        with self.get_connection() as conn:
            conn.execute("""
                UPDATE upload_chunks SET
                    status = 'uploaded',
                    uploaded_at = ?
                WHERE id = ?
            """, (int(time.time()), chunk_id))

    def get_pending_chunks(self, upload_queue_id: int) -> List[Dict[str, Any]]:
        """Get pending chunks for upload job.

        Args:
            upload_queue_id: Upload queue ID

        Returns:
            List of chunk dicts
        """
        with self.get_connection() as conn:
            rows = conn.execute("""
                SELECT * FROM upload_chunks
                WHERE upload_queue_id = ?
                AND status = 'pending'
                ORDER BY chunk_index ASC
            """, (upload_queue_id,)).fetchall()

            return [dict(row) for row in rows]

    # ========================================
    # Errors
    # ========================================

    def log_error(self, error_type: str, severity: str, message: str,
                  details: Optional[str] = None, file_id: Optional[int] = None,
                  upload_queue_id: Optional[int] = None,
                  stack_trace: Optional[str] = None) -> int:
        """Log error to database.

        Args:
            error_type: Error type
            severity: Severity level
            message: Error message
            details: Optional detailed info
            file_id: Optional related file ID
            upload_queue_id: Optional related upload job ID
            stack_trace: Optional stack trace

        Returns:
            Error ID
        """
        with self.get_connection() as conn:
            cursor = conn.execute("""
                INSERT INTO errors (
                    error_type, severity, message, details,
                    file_id, upload_queue_id, stack_trace
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (error_type, severity, message, details, file_id, upload_queue_id, stack_trace))

            return cursor.lastrowid

    def get_unresolved_errors(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get unresolved errors.

        Args:
            limit: Maximum number to return

        Returns:
            List of error dicts
        """
        with self.get_connection() as conn:
            rows = conn.execute("""
                SELECT * FROM v_recent_errors
                LIMIT ?
            """, (limit,)).fetchall()

            return [dict(row) for row in rows]

    # ========================================
    # Sync State
    # ========================================

    def update_sync_state(self, updates: Dict[str, Any]) -> None:
        """Update sync state fields.

        Args:
            updates: Dictionary of fields to update
        """
        if not updates:
            return

        set_clause = ", ".join(f"{k} = ?" for k in updates.keys())
        values = list(updates.values())

        with self.get_connection() as conn:
            conn.execute(f"UPDATE sync_state SET {set_clause} WHERE id = 1", values)

    def get_sync_state(self) -> Dict[str, Any]:
        """Get current sync state.

        Returns:
            Sync state dict
        """
        with self.get_connection() as conn:
            row = conn.execute("SELECT * FROM sync_state WHERE id = 1").fetchone()
            return dict(row) if row else {}

    def get_sync_stats(self) -> Dict[str, Any]:
        """Get sync statistics.

        Returns:
            Statistics dict
        """
        with self.get_connection() as conn:
            row = conn.execute("SELECT * FROM v_sync_stats").fetchone()
            return dict(row) if row else {}

    # ========================================
    # Activity Log
    # ========================================

    def log_activity(self, activity_type: str, message: str,
                     details: Optional[str] = None, file_id: Optional[int] = None,
                     upload_queue_id: Optional[int] = None) -> int:
        """Log activity.

        Args:
            activity_type: Activity type
            message: Activity message
            details: Optional details (JSON)
            file_id: Optional related file ID
            upload_queue_id: Optional related upload job ID

        Returns:
            Activity ID
        """
        with self.get_connection() as conn:
            cursor = conn.execute("""
                INSERT INTO activity_log (
                    activity_type, message, details, file_id, upload_queue_id
                ) VALUES (?, ?, ?, ?, ?)
            """, (activity_type, message, details, file_id, upload_queue_id))

            return cursor.lastrowid

    def get_recent_activity(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent activity.

        Args:
            limit: Maximum number of records

        Returns:
            List of activity dicts
        """
        with self.get_connection() as conn:
            rows = conn.execute("""
                SELECT * FROM activity_log
                ORDER BY created_at DESC
                LIMIT ?
            """, (limit,)).fetchall()

            return [dict(row) for row in rows]

    # ========================================
    # Ignore Patterns
    # ========================================

    def get_ignore_patterns(self) -> List[Dict[str, Any]]:
        """Get all enabled ignore patterns.

        Returns:
            List of pattern dicts
        """
        with self.get_connection() as conn:
            rows = conn.execute("""
                SELECT * FROM ignore_patterns
                WHERE enabled = 1
            """).fetchall()

            return [dict(row) for row in rows]
