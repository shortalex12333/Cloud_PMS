"""
CelesteOS Local Agent - Manifest Database Manager
Manages local SQLite database for tracking NAS files and upload state
"""

import sqlite3
import os
from datetime import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class ManifestDB:
    """
    Manages the local SQLite manifest database that tracks:
    - Discovered NAS files with metadata
    - Upload queue
    - Upload history
    - SHA256 hashes for deduplication
    """

    def __init__(self, db_path: str):
        """
        Initialize manifest database connection.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._ensure_db_directory()
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row  # Return rows as dicts
        self._init_schema()

    def _ensure_db_directory(self):
        """Ensure the database directory exists"""
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)

    def _init_schema(self):
        """Initialize database schema if not exists"""
        cursor = self.conn.cursor()

        # NAS files table - tracks all discovered files
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS nas_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT NOT NULL UNIQUE,
                nas_path TEXT NOT NULL,
                filename TEXT NOT NULL,
                file_size INTEGER NOT NULL,
                extension TEXT,
                mime_type TEXT,
                sha256 TEXT,
                last_modified TIMESTAMP NOT NULL,
                discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_scanned TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'discovered',
                -- Status: 'discovered', 'queued', 'uploading', 'uploaded', 'failed', 'excluded'
                upload_priority INTEGER DEFAULT 5,
                error_message TEXT,
                retry_count INTEGER DEFAULT 0,
                uploaded_at TIMESTAMP,
                document_id TEXT  -- UUID from cloud
            )
        """)

        # Upload queue table - tracks pending uploads
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS upload_queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nas_file_id INTEGER NOT NULL,
                upload_session_id TEXT,  -- UUID from cloud
                total_chunks INTEGER,
                chunks_uploaded INTEGER DEFAULT 0,
                status TEXT DEFAULT 'pending',
                -- Status: 'pending', 'in_progress', 'completed', 'failed'
                queued_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                started_at TIMESTAMP,
                completed_at TIMESTAMP,
                error_message TEXT,
                retry_count INTEGER DEFAULT 0,
                FOREIGN KEY (nas_file_id) REFERENCES nas_files(id)
            )
        """)

        # Chunk tracking table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS upload_chunks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                upload_queue_id INTEGER NOT NULL,
                chunk_index INTEGER NOT NULL,
                chunk_sha256 TEXT NOT NULL,
                chunk_size INTEGER NOT NULL,
                chunk_path TEXT,  -- Temporary chunk file path
                status TEXT DEFAULT 'pending',
                -- Status: 'pending', 'uploading', 'uploaded', 'verified', 'failed'
                uploaded_at TIMESTAMP,
                verified_at TIMESTAMP,
                error_message TEXT,
                retry_count INTEGER DEFAULT 0,
                FOREIGN KEY (upload_queue_id) REFERENCES upload_queue(id),
                UNIQUE(upload_queue_id, chunk_index)
            )
        """)

        # Upload history (for analytics)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS upload_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT NOT NULL,
                file_size INTEGER NOT NULL,
                sha256 TEXT NOT NULL,
                chunks_count INTEGER,
                upload_duration_seconds INTEGER,
                uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                document_id TEXT
            )
        """)

        # Sync state (tracks last sync times, etc.)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sync_state (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_nas_files_sha256 ON nas_files(sha256)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_nas_files_status ON nas_files(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_nas_files_path ON nas_files(file_path)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_upload_queue_status ON upload_queue(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_upload_chunks_status ON upload_chunks(status)")

        self.conn.commit()
        logger.info(f"Manifest database initialized: {self.db_path}")

    def add_or_update_nas_file(self, file_path: str, nas_path: str,
                                file_size: int, last_modified: datetime,
                                sha256: Optional[str] = None,
                                extension: Optional[str] = None,
                                mime_type: Optional[str] = None) -> int:
        """
        Add a new NAS file or update existing one.
        Returns the file_id.
        """
        cursor = self.conn.cursor()
        filename = os.path.basename(file_path)

        try:
            # Check if file exists
            cursor.execute("SELECT id, sha256, last_modified FROM nas_files WHERE file_path = ?",
                          (file_path,))
            existing = cursor.fetchone()

            if existing:
                # File exists - check if modified
                file_id = existing['id']
                existing_sha256 = existing['sha256']
                existing_modified = existing['last_modified']

                # If modification time changed, file might have changed
                if last_modified != existing_modified:
                    # Reset hash to trigger re-processing
                    cursor.execute("""
                        UPDATE nas_files
                        SET file_size = ?, last_modified = ?, sha256 = NULL,
                            status = 'discovered', last_scanned = CURRENT_TIMESTAMP
                        WHERE id = ?
                    """, (file_size, last_modified, file_id))
                    logger.info(f"File modified, marking for re-hash: {file_path}")
                else:
                    # Just update last_scanned
                    cursor.execute("""
                        UPDATE nas_files SET last_scanned = CURRENT_TIMESTAMP WHERE id = ?
                    """, (file_id,))
            else:
                # New file
                cursor.execute("""
                    INSERT INTO nas_files
                    (file_path, nas_path, filename, file_size, extension, mime_type,
                     sha256, last_modified, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'discovered')
                """, (file_path, nas_path, filename, file_size, extension, mime_type,
                      sha256, last_modified))
                file_id = cursor.lastrowid
                logger.debug(f"New file discovered: {file_path}")

            self.conn.commit()
            return file_id

        except Exception as e:
            self.conn.rollback()
            logger.error(f"Failed to add/update NAS file {file_path}: {e}")
            raise

    def update_file_hash(self, file_id: int, sha256: str):
        """Update SHA256 hash for a file"""
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE nas_files SET sha256 = ?, status = 'hashed' WHERE id = ?
        """, (sha256, file_id))
        self.conn.commit()

    def get_files_needing_hash(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get files that need SHA256 computation"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT id, file_path, file_size
            FROM nas_files
            WHERE sha256 IS NULL AND status = 'discovered'
            ORDER BY file_size ASC
            LIMIT ?
        """, (limit,))
        return [dict(row) for row in cursor.fetchall()]

    def get_files_for_upload_queue(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Get files ready to be queued for upload.
        Files must:
        - Have SHA256 computed
        - Not already uploaded
        - Not currently in queue
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT id, file_path, nas_path, filename, file_size, sha256, mime_type
            FROM nas_files
            WHERE sha256 IS NOT NULL
              AND status IN ('hashed', 'failed')
              AND uploaded_at IS NULL
              AND id NOT IN (
                  SELECT nas_file_id FROM upload_queue
                  WHERE status IN ('pending', 'in_progress')
              )
            ORDER BY upload_priority DESC, file_size ASC
            LIMIT ?
        """, (limit,))
        return [dict(row) for row in cursor.fetchall()]

    def create_upload_queue_entry(self, nas_file_id: int, total_chunks: int) -> int:
        """Create a new upload queue entry"""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO upload_queue (nas_file_id, total_chunks, status)
            VALUES (?, ?, 'pending')
        """, (nas_file_id, total_chunks))
        queue_id = cursor.lastrowid

        # Update nas_file status
        cursor.execute("""
            UPDATE nas_files SET status = 'queued' WHERE id = ?
        """, (nas_file_id,))

        self.conn.commit()
        return queue_id

    def update_upload_session_id(self, queue_id: int, upload_session_id: str):
        """Update upload queue with session ID from cloud"""
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE upload_queue
            SET upload_session_id = ?, status = 'in_progress', started_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (upload_session_id, queue_id))
        self.conn.commit()

    def add_chunk_to_queue(self, queue_id: int, chunk_index: int,
                          chunk_sha256: str, chunk_size: int, chunk_path: str):
        """Add a chunk to upload tracking"""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO upload_chunks
            (upload_queue_id, chunk_index, chunk_sha256, chunk_size, chunk_path, status)
            VALUES (?, ?, ?, ?, ?, 'pending')
        """, (queue_id, chunk_index, chunk_sha256, chunk_size, chunk_path))
        self.conn.commit()

    def get_pending_chunks(self, queue_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """Get pending chunks for an upload queue"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT id, chunk_index, chunk_sha256, chunk_size, chunk_path
            FROM upload_chunks
            WHERE upload_queue_id = ? AND status = 'pending'
            ORDER BY chunk_index ASC
            LIMIT ?
        """, (queue_id, limit))
        return [dict(row) for row in cursor.fetchall()]

    def mark_chunk_uploaded(self, chunk_id: int):
        """Mark chunk as successfully uploaded"""
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE upload_chunks
            SET status = 'verified', uploaded_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (chunk_id,))

        # Update chunks_uploaded count
        cursor.execute("""
            UPDATE upload_queue
            SET chunks_uploaded = (
                SELECT COUNT(*) FROM upload_chunks
                WHERE upload_queue_id = upload_queue.id AND status = 'verified'
            )
            WHERE id = (
                SELECT upload_queue_id FROM upload_chunks WHERE id = ?
            )
        """, (chunk_id,))

        self.conn.commit()

    def mark_chunk_failed(self, chunk_id: int, error_message: str):
        """Mark chunk upload as failed"""
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE upload_chunks
            SET status = 'failed', error_message = ?, retry_count = retry_count + 1
            WHERE id = ?
        """, (error_message, chunk_id))
        self.conn.commit()

    def mark_upload_complete(self, queue_id: int, document_id: str):
        """Mark entire upload as complete"""
        cursor = self.conn.cursor()

        # Mark queue complete
        cursor.execute("""
            UPDATE upload_queue
            SET status = 'completed', completed_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (queue_id,))

        # Get nas_file_id
        cursor.execute("SELECT nas_file_id FROM upload_queue WHERE id = ?", (queue_id,))
        nas_file_id = cursor.fetchone()['nas_file_id']

        # Mark nas_file uploaded
        cursor.execute("""
            UPDATE nas_files
            SET status = 'uploaded', uploaded_at = CURRENT_TIMESTAMP, document_id = ?
            WHERE id = ?
        """, (document_id, nas_file_id))

        self.conn.commit()
        logger.info(f"Upload marked complete: queue_id={queue_id}, document_id={document_id}")

    def mark_upload_failed(self, queue_id: int, error_message: str):
        """Mark upload as failed"""
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE upload_queue
            SET status = 'failed', error_message = ?, retry_count = retry_count + 1
            WHERE id = ?
        """, (error_message, queue_id))

        # Mark nas_file as failed (can be retried)
        cursor.execute("""
            UPDATE nas_files SET status = 'failed', error_message = ?
            WHERE id = (SELECT nas_file_id FROM upload_queue WHERE id = ?)
        """, (error_message, queue_id))

        self.conn.commit()

    def get_sync_state(self, key: str) -> Optional[str]:
        """Get sync state value"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT value FROM sync_state WHERE key = ?", (key,))
        row = cursor.fetchone()
        return row['value'] if row else None

    def set_sync_state(self, key: str, value: str):
        """Set sync state value"""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO sync_state (key, value, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
        """, (key, value))
        self.conn.commit()

    def get_stats(self) -> Dict[str, Any]:
        """Get manifest statistics"""
        cursor = self.conn.cursor()

        stats = {}

        # Total files by status
        cursor.execute("""
            SELECT status, COUNT(*) as count, SUM(file_size) as total_size
            FROM nas_files
            GROUP BY status
        """)
        stats['files_by_status'] = {row['status']: {'count': row['count'],
                                                      'total_size': row['total_size']}
                                     for row in cursor.fetchall()}

        # Upload queue stats
        cursor.execute("""
            SELECT status, COUNT(*) as count
            FROM upload_queue
            GROUP BY status
        """)
        stats['queue_by_status'] = {row['status']: row['count'] for row in cursor.fetchall()}

        # Total uploaded
        cursor.execute("SELECT COUNT(*), SUM(file_size) FROM nas_files WHERE uploaded_at IS NOT NULL")
        row = cursor.fetchone()
        stats['total_uploaded'] = {'count': row[0], 'total_size': row[1]}

        return stats

    def cleanup_old_chunks(self, days: int = 7):
        """Clean up old temporary chunk files"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT chunk_path FROM upload_chunks
            WHERE status IN ('verified', 'failed')
              AND uploaded_at < datetime('now', '-' || ? || ' days')
        """, (days,))

        chunk_paths = [row['chunk_path'] for row in cursor.fetchall()]

        deleted_count = 0
        for chunk_path in chunk_paths:
            if chunk_path and os.path.exists(chunk_path):
                try:
                    os.remove(chunk_path)
                    deleted_count += 1
                except Exception as e:
                    logger.warning(f"Failed to delete chunk {chunk_path}: {e}")

        logger.info(f"Cleaned up {deleted_count} old chunk files")
        return deleted_count

    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            logger.info("Manifest database connection closed")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
