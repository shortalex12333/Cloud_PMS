"""
Telemetry logging for CelesteOS Local Agent.
Logs ingestion events locally and prepares payloads for later batch upload.
"""

import json
import time
import uuid
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict, field
from datetime import datetime

from .logger import get_logger
from .database import Database

logger = get_logger(__name__)


@dataclass
class TelemetryEvent:
    """Represents a telemetry event."""
    event_type: str
    timestamp: int = field(default_factory=lambda: int(time.time()))
    yacht_id: Optional[str] = None
    file_path: Optional[str] = None
    file_sha256: Optional[str] = None
    file_size: Optional[int] = None
    chunk_index: Optional[int] = None
    total_chunks: Optional[int] = None
    duration_ms: Optional[int] = None
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary, excluding None values."""
        d = asdict(self)
        return {k: v for k, v in d.items() if v is not None}


class TelemetryCollector:
    """Collects and stores telemetry events locally."""

    # Valid event types
    VALID_EVENTS = {
        'scan_started', 'scan_completed', 'scan_failed',
        'file_discovered', 'file_modified', 'file_deleted',
        'upload_started', 'upload_chunk_completed', 'upload_completed', 'upload_failed',
        'daemon_started', 'daemon_stopped', 'error_occurred',
        'resume_detected', 'hash_computed', 'tombstone_created'
    }

    def __init__(self, db: Database, yacht_id: Optional[str] = None):
        """Initialize telemetry collector.

        Args:
            db: Database instance
            yacht_id: Optional yacht identifier
        """
        self.db = db
        self.yacht_id = yacht_id
        self._event_buffer: List[TelemetryEvent] = []
        self._buffer_size = 100  # Flush to DB after this many events

    def set_yacht_id(self, yacht_id: str) -> None:
        """Set the yacht ID for all future events.

        Args:
            yacht_id: Yacht identifier
        """
        self.yacht_id = yacht_id

    def log(
        self,
        event_type: str,
        file_path: Optional[str] = None,
        file_sha256: Optional[str] = None,
        file_size: Optional[int] = None,
        chunk_index: Optional[int] = None,
        total_chunks: Optional[int] = None,
        duration_ms: Optional[int] = None,
        error_message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log a telemetry event.

        Args:
            event_type: Type of event
            file_path: Optional file path
            file_sha256: Optional file hash
            file_size: Optional file size
            chunk_index: Optional chunk index
            total_chunks: Optional total chunks
            duration_ms: Optional duration in milliseconds
            error_message: Optional error message
            metadata: Optional additional metadata
        """
        if event_type not in self.VALID_EVENTS:
            logger.warning(f"Invalid telemetry event type: {event_type}")
            return

        event = TelemetryEvent(
            event_type=event_type,
            yacht_id=self.yacht_id,
            file_path=file_path,
            file_sha256=file_sha256,
            file_size=file_size,
            chunk_index=chunk_index,
            total_chunks=total_chunks,
            duration_ms=duration_ms,
            error_message=error_message,
            metadata=metadata
        )

        self._event_buffer.append(event)

        # Log to standard logger as well
        log_msg = f"[TELEMETRY] {event_type}"
        if file_path:
            log_msg += f" | file={file_path}"
        if error_message:
            log_msg += f" | error={error_message}"

        logger.debug(log_msg)

        # Flush if buffer is full
        if len(self._event_buffer) >= self._buffer_size:
            self.flush()

    def log_scan_started(self, scan_type: str = "full") -> None:
        """Log scan started event."""
        self.log('scan_started', metadata={'scan_type': scan_type})

    def log_scan_completed(
        self,
        duration_ms: int,
        files_discovered: int,
        files_modified: int,
        files_deleted: int
    ) -> None:
        """Log scan completed event."""
        self.log(
            'scan_completed',
            duration_ms=duration_ms,
            metadata={
                'files_discovered': files_discovered,
                'files_modified': files_modified,
                'files_deleted': files_deleted
            }
        )

    def log_scan_failed(self, error_message: str) -> None:
        """Log scan failed event."""
        self.log('scan_failed', error_message=error_message)

    def log_file_discovered(
        self,
        file_path: str,
        file_sha256: str,
        file_size: int
    ) -> None:
        """Log file discovered event."""
        self.log(
            'file_discovered',
            file_path=file_path,
            file_sha256=file_sha256,
            file_size=file_size
        )

    def log_file_modified(
        self,
        file_path: str,
        old_sha256: str,
        new_sha256: str,
        file_size: int
    ) -> None:
        """Log file modified event."""
        self.log(
            'file_modified',
            file_path=file_path,
            file_sha256=new_sha256,
            file_size=file_size,
            metadata={'old_sha256': old_sha256}
        )

    def log_file_deleted(
        self,
        file_path: str,
        file_sha256: Optional[str] = None
    ) -> None:
        """Log file deleted event."""
        self.log(
            'file_deleted',
            file_path=file_path,
            file_sha256=file_sha256
        )

    def log_upload_started(
        self,
        file_path: str,
        file_sha256: str,
        file_size: int,
        total_chunks: int,
        upload_id: Optional[str] = None
    ) -> None:
        """Log upload started event."""
        self.log(
            'upload_started',
            file_path=file_path,
            file_sha256=file_sha256,
            file_size=file_size,
            total_chunks=total_chunks,
            metadata={'upload_id': upload_id} if upload_id else None
        )

    def log_upload_chunk_completed(
        self,
        file_path: str,
        chunk_index: int,
        total_chunks: int,
        duration_ms: int
    ) -> None:
        """Log chunk upload completed event."""
        self.log(
            'upload_chunk_completed',
            file_path=file_path,
            chunk_index=chunk_index,
            total_chunks=total_chunks,
            duration_ms=duration_ms
        )

    def log_upload_completed(
        self,
        file_path: str,
        file_sha256: str,
        file_size: int,
        duration_ms: int,
        document_id: Optional[str] = None
    ) -> None:
        """Log upload completed event."""
        self.log(
            'upload_completed',
            file_path=file_path,
            file_sha256=file_sha256,
            file_size=file_size,
            duration_ms=duration_ms,
            metadata={'document_id': document_id} if document_id else None
        )

    def log_upload_failed(
        self,
        file_path: str,
        error_message: str,
        retry_count: int = 0
    ) -> None:
        """Log upload failed event."""
        self.log(
            'upload_failed',
            file_path=file_path,
            error_message=error_message,
            metadata={'retry_count': retry_count}
        )

    def log_resume_detected(
        self,
        file_path: str,
        chunks_completed: int,
        total_chunks: int
    ) -> None:
        """Log upload resume detected event."""
        self.log(
            'resume_detected',
            file_path=file_path,
            chunk_index=chunks_completed,
            total_chunks=total_chunks,
            metadata={'progress_percent': round(chunks_completed / total_chunks * 100, 1)}
        )

    def log_error(self, error_type: str, error_message: str, context: Optional[Dict] = None) -> None:
        """Log error occurred event."""
        metadata = {'error_type': error_type}
        if context:
            metadata.update(context)
        self.log('error_occurred', error_message=error_message, metadata=metadata)

    def flush(self) -> int:
        """Flush buffered events to database.

        Returns:
            Number of events flushed
        """
        if not self._event_buffer:
            return 0

        events_to_flush = self._event_buffer.copy()
        self._event_buffer.clear()

        flushed = 0
        with self.db.get_connection() as conn:
            for event in events_to_flush:
                try:
                    metadata_json = json.dumps(event.metadata) if event.metadata else None
                    conn.execute("""
                        INSERT INTO telemetry_events (
                            event_type, timestamp, yacht_id, file_path,
                            file_sha256, file_size, chunk_index, total_chunks,
                            duration_ms, error_message, metadata
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        event.event_type,
                        event.timestamp,
                        event.yacht_id,
                        event.file_path,
                        event.file_sha256,
                        event.file_size,
                        event.chunk_index,
                        event.total_chunks,
                        event.duration_ms,
                        event.error_message,
                        metadata_json
                    ))
                    flushed += 1
                except Exception as e:
                    logger.error(f"Failed to flush telemetry event: {e}")

        logger.debug(f"Flushed {flushed} telemetry events to database")
        return flushed

    def get_pending_events(self, limit: int = 1000) -> List[Dict[str, Any]]:
        """Get events not yet uploaded to cloud.

        Args:
            limit: Maximum number to return

        Returns:
            List of event records
        """
        with self.db.get_connection() as conn:
            rows = conn.execute("""
                SELECT * FROM telemetry_events
                WHERE uploaded_to_cloud = 0
                ORDER BY timestamp ASC
                LIMIT ?
            """, (limit,)).fetchall()
            return [dict(row) for row in rows]

    def prepare_upload_payload(self, limit: int = 1000) -> Dict[str, Any]:
        """Prepare a compact telemetry payload for cloud upload.

        Args:
            limit: Maximum number of events to include

        Returns:
            Payload dictionary ready for JSON serialization
        """
        events = self.get_pending_events(limit)

        if not events:
            return {'events': [], 'count': 0}

        batch_id = str(uuid.uuid4())

        # Compact format - remove null fields
        compact_events = []
        for event in events:
            compact = {
                'type': event['event_type'],
                'ts': event['timestamp']
            }

            # Only include non-null optional fields
            if event['file_path']:
                compact['path'] = event['file_path']
            if event['file_sha256']:
                compact['sha256'] = event['file_sha256']
            if event['file_size']:
                compact['size'] = event['file_size']
            if event['chunk_index'] is not None:
                compact['chunk'] = event['chunk_index']
            if event['total_chunks']:
                compact['total'] = event['total_chunks']
            if event['duration_ms']:
                compact['dur'] = event['duration_ms']
            if event['error_message']:
                compact['err'] = event['error_message']
            if event['metadata']:
                compact['meta'] = json.loads(event['metadata']) if isinstance(event['metadata'], str) else event['metadata']

            compact_events.append(compact)

        return {
            'batch_id': batch_id,
            'yacht_id': self.yacht_id,
            'collected_at': int(time.time()),
            'events': compact_events,
            'count': len(compact_events)
        }

    def mark_events_uploaded(self, event_ids: List[int], batch_id: str) -> None:
        """Mark events as uploaded to cloud.

        Args:
            event_ids: List of event IDs
            batch_id: Batch identifier
        """
        if not event_ids:
            return

        now = int(time.time())
        placeholders = ','.join('?' * len(event_ids))

        with self.db.get_connection() as conn:
            conn.execute(f"""
                UPDATE telemetry_events SET
                    uploaded_to_cloud = 1,
                    uploaded_at = ?,
                    batch_id = ?
                WHERE id IN ({placeholders})
            """, [now, batch_id] + event_ids)

    def get_statistics(self) -> Dict[str, Any]:
        """Get telemetry statistics.

        Returns:
            Statistics dictionary
        """
        with self.db.get_connection() as conn:
            # Total events
            total = conn.execute("SELECT COUNT(*) as count FROM telemetry_events").fetchone()['count']

            # Pending uploads
            pending = conn.execute(
                "SELECT COUNT(*) as count FROM telemetry_events WHERE uploaded_to_cloud = 0"
            ).fetchone()['count']

            # Events by type
            by_type = conn.execute("""
                SELECT event_type, COUNT(*) as count
                FROM telemetry_events
                GROUP BY event_type
                ORDER BY count DESC
            """).fetchall()

            # Recent errors
            recent_errors = conn.execute("""
                SELECT * FROM telemetry_events
                WHERE event_type IN ('scan_failed', 'upload_failed', 'error_occurred')
                ORDER BY timestamp DESC
                LIMIT 10
            """).fetchall()

            return {
                'total_events': total,
                'pending_upload': pending,
                'events_by_type': {row['event_type']: row['count'] for row in by_type},
                'recent_errors': [dict(row) for row in recent_errors]
            }

    def cleanup_old_events(self, days_to_keep: int = 30) -> int:
        """Remove old uploaded events.

        Args:
            days_to_keep: Number of days to retain events

        Returns:
            Number of events deleted
        """
        cutoff = int(time.time()) - (days_to_keep * 24 * 60 * 60)

        with self.db.get_connection() as conn:
            cursor = conn.execute("""
                DELETE FROM telemetry_events
                WHERE uploaded_to_cloud = 1
                AND timestamp < ?
            """, (cutoff,))

            deleted = cursor.rowcount
            logger.info(f"Cleaned up {deleted} old telemetry events")
            return deleted
