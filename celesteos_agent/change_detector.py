"""
Robust file change detection for CelesteOS Local Agent.
Detects new, modified, and deleted files using SHA256 hashing.
"""

import os
import time
import json
from pathlib import Path
from typing import Dict, Any, List, Optional, Set, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

from .logger import get_logger
from .database import Database
from .hasher import FileHasher

logger = get_logger(__name__)


class ChangeType(Enum):
    """Types of file changes detected."""
    NEW = "new"
    MODIFIED = "modified"
    DELETED = "deleted"
    MOVED = "moved"
    UNCHANGED = "unchanged"


@dataclass
class FileChange:
    """Represents a detected file change."""
    file_path: str  # Relative path from NAS root
    absolute_path: str
    change_type: ChangeType
    filename: str
    file_size: Optional[int] = None
    new_sha256: Optional[str] = None
    old_sha256: Optional[str] = None
    last_modified: Optional[int] = None
    mime_type: Optional[str] = None
    new_path: Optional[str] = None  # For moved files

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        d = asdict(self)
        d['change_type'] = self.change_type.value
        return d


class ChangeDetector:
    """Detects file changes using SHA256 comparison."""

    def __init__(
        self,
        db: Database,
        nas_path: str,
        hasher: Optional[FileHasher] = None,
        batch_size: int = 100
    ):
        """Initialize change detector.

        Args:
            db: Database instance
            nas_path: Path to NAS root
            hasher: Optional FileHasher instance
            batch_size: Number of files to process per batch
        """
        self.db = db
        self.nas_path = Path(nas_path).expanduser()
        self.hasher = hasher or FileHasher(num_workers=4)
        self.batch_size = batch_size

        # Statistics
        self.stats = {
            'new_files': 0,
            'modified_files': 0,
            'deleted_files': 0,
            'moved_files': 0,
            'unchanged_files': 0,
            'errors': 0,
            'bytes_hashed': 0,
            'duration_ms': 0
        }

    def detect_changes_full(self, seen_paths: Set[str]) -> Tuple[List[FileChange], Dict[str, int]]:
        """Detect all file changes during a full scan.

        Args:
            seen_paths: Set of relative paths currently seen on filesystem

        Returns:
            Tuple of (list of FileChange objects, statistics dict)
        """
        start_time = time.time()
        changes: List[FileChange] = []

        # Reset stats
        self.stats = {
            'new_files': 0,
            'modified_files': 0,
            'deleted_files': 0,
            'moved_files': 0,
            'unchanged_files': 0,
            'errors': 0,
            'bytes_hashed': 0,
            'duration_ms': 0
        }

        logger.info(f"Detecting changes for {len(seen_paths)} files")

        # Get all known files from database
        known_files = self._get_all_known_files()
        known_paths = set(known_files.keys())

        # Detect deleted files (in DB but not on filesystem)
        deleted_paths = known_paths - seen_paths
        for deleted_path in deleted_paths:
            known_file = known_files[deleted_path]

            # Check if this might be a move (same SHA256 in seen_paths)
            moved_to = self._find_moved_file(known_file, seen_paths)

            if moved_to:
                change = FileChange(
                    file_path=deleted_path,
                    absolute_path=str(self.nas_path / deleted_path),
                    change_type=ChangeType.MOVED,
                    filename=known_file['filename'],
                    file_size=known_file['file_size'],
                    old_sha256=known_file['sha256'],
                    new_path=moved_to
                )
                self.stats['moved_files'] += 1
            else:
                change = FileChange(
                    file_path=deleted_path,
                    absolute_path=str(self.nas_path / deleted_path),
                    change_type=ChangeType.DELETED,
                    filename=known_file['filename'],
                    file_size=known_file['file_size'],
                    old_sha256=known_file['sha256']
                )
                self.stats['deleted_files'] += 1

            changes.append(change)

            # Create tombstone
            self._create_tombstone(change)

            logger.info(f"File {change.change_type.value}: {deleted_path}")

        # Detect new files (on filesystem but not in DB)
        new_paths = seen_paths - known_paths
        for new_path in new_paths:
            try:
                change = self._process_new_file(new_path)
                if change:
                    changes.append(change)
                    self.stats['new_files'] += 1
                    logger.info(f"File new: {new_path}")
            except Exception as e:
                logger.error(f"Error processing new file {new_path}: {e}")
                self.stats['errors'] += 1

        # Detect modified files (in both, check SHA256)
        existing_paths = seen_paths & known_paths
        for existing_path in existing_paths:
            try:
                change = self._check_file_modified(existing_path, known_files[existing_path])
                if change:
                    changes.append(change)
                    if change.change_type == ChangeType.MODIFIED:
                        self.stats['modified_files'] += 1
                        logger.info(f"File modified: {existing_path}")
                    else:
                        self.stats['unchanged_files'] += 1
            except Exception as e:
                logger.error(f"Error checking file {existing_path}: {e}")
                self.stats['errors'] += 1

        self.stats['duration_ms'] = int((time.time() - start_time) * 1000)

        logger.info(
            f"Change detection complete: {self.stats['new_files']} new, "
            f"{self.stats['modified_files']} modified, {self.stats['deleted_files']} deleted, "
            f"{self.stats['moved_files']} moved in {self.stats['duration_ms']}ms"
        )

        return changes, self.stats.copy()

    def detect_single_file_change(self, file_path: Path) -> Optional[FileChange]:
        """Detect change for a single file (for real-time events).

        Args:
            file_path: Absolute path to file

        Returns:
            FileChange object or None if no change detected
        """
        try:
            relative_path = str(file_path.relative_to(self.nas_path))
        except ValueError:
            logger.error(f"File not under NAS path: {file_path}")
            return None

        # Get existing record from database
        known_file = self.db.get_file_by_path(relative_path)

        if not file_path.exists():
            # File deleted
            if known_file:
                return FileChange(
                    file_path=relative_path,
                    absolute_path=str(file_path),
                    change_type=ChangeType.DELETED,
                    filename=known_file['filename'],
                    file_size=known_file['file_size'],
                    old_sha256=known_file['sha256']
                )
            return None

        if not known_file:
            # New file
            return self._process_new_file(relative_path)

        # Check if modified
        return self._check_file_modified(relative_path, known_file)

    def _get_all_known_files(self) -> Dict[str, Dict[str, Any]]:
        """Get all known files from database.

        Returns:
            Dict mapping file_path to file record
        """
        with self.db.get_connection() as conn:
            rows = conn.execute("""
                SELECT * FROM files
                WHERE status != 'deleted'
            """).fetchall()
            return {row['file_path']: dict(row) for row in rows}

    def _process_new_file(self, relative_path: str) -> Optional[FileChange]:
        """Process a newly discovered file.

        Args:
            relative_path: Relative path from NAS root

        Returns:
            FileChange object or None if error
        """
        absolute_path = self.nas_path / relative_path

        if not absolute_path.exists():
            return None

        try:
            stat = absolute_path.stat()

            # Compute SHA256
            sha256 = self.hasher.compute_hash(absolute_path)
            self.stats['bytes_hashed'] += stat.st_size

            # Detect MIME type
            try:
                import magic
                mime = magic.Magic(mime=True)
                mime_type = mime.from_file(str(absolute_path))
            except Exception:
                mime_type = 'application/octet-stream'

            return FileChange(
                file_path=relative_path,
                absolute_path=str(absolute_path),
                change_type=ChangeType.NEW,
                filename=absolute_path.name,
                file_size=stat.st_size,
                new_sha256=sha256,
                last_modified=int(stat.st_mtime),
                mime_type=mime_type
            )
        except Exception as e:
            logger.error(f"Error processing new file {relative_path}: {e}")
            return None

    def _check_file_modified(
        self,
        relative_path: str,
        known_file: Dict[str, Any]
    ) -> Optional[FileChange]:
        """Check if a known file has been modified.

        Uses a two-phase approach:
        1. Quick check: file size + mtime
        2. Full check: SHA256 if quick check suggests change

        Args:
            relative_path: Relative path from NAS root
            known_file: Known file record from database

        Returns:
            FileChange object or None if unchanged
        """
        absolute_path = self.nas_path / relative_path

        if not absolute_path.exists():
            return FileChange(
                file_path=relative_path,
                absolute_path=str(absolute_path),
                change_type=ChangeType.DELETED,
                filename=known_file['filename'],
                file_size=known_file['file_size'],
                old_sha256=known_file['sha256']
            )

        try:
            stat = absolute_path.stat()
            current_size = stat.st_size
            current_mtime = int(stat.st_mtime)

            # Quick check: size or mtime changed?
            size_changed = current_size != known_file['file_size']
            mtime_changed = current_mtime != known_file.get('last_modified', 0)

            # If neither changed, skip expensive hash computation
            if not size_changed and not mtime_changed:
                return FileChange(
                    file_path=relative_path,
                    absolute_path=str(absolute_path),
                    change_type=ChangeType.UNCHANGED,
                    filename=known_file['filename'],
                    file_size=current_size,
                    new_sha256=known_file['sha256'],
                    old_sha256=known_file['sha256'],
                    last_modified=current_mtime
                )

            # Full check: compute SHA256
            new_sha256 = self.hasher.compute_hash(absolute_path)
            self.stats['bytes_hashed'] += current_size

            if new_sha256 != known_file['sha256']:
                # File genuinely modified
                return FileChange(
                    file_path=relative_path,
                    absolute_path=str(absolute_path),
                    change_type=ChangeType.MODIFIED,
                    filename=absolute_path.name,
                    file_size=current_size,
                    new_sha256=new_sha256,
                    old_sha256=known_file['sha256'],
                    last_modified=current_mtime
                )
            else:
                # Hash same - just metadata changed (mtime touched)
                return FileChange(
                    file_path=relative_path,
                    absolute_path=str(absolute_path),
                    change_type=ChangeType.UNCHANGED,
                    filename=known_file['filename'],
                    file_size=current_size,
                    new_sha256=new_sha256,
                    old_sha256=known_file['sha256'],
                    last_modified=current_mtime
                )

        except Exception as e:
            logger.error(f"Error checking file {relative_path}: {e}")
            return None

    def _find_moved_file(
        self,
        known_file: Dict[str, Any],
        seen_paths: Set[str]
    ) -> Optional[str]:
        """Try to detect if a deleted file was actually moved.

        Looks for a new file with the same SHA256 hash.

        Args:
            known_file: The deleted file record
            seen_paths: Set of paths currently on filesystem

        Returns:
            New path if move detected, None otherwise
        """
        if not known_file.get('sha256'):
            return None

        # Check if any new file has the same hash
        # This is a heuristic - same hash strongly suggests same content
        # For efficiency, we check files with same size first

        for path in seen_paths:
            # Skip if we know this file already
            existing = self.db.get_file_by_path(path)
            if existing:
                continue

            abs_path = self.nas_path / path
            if not abs_path.exists():
                continue

            try:
                # Quick size check first
                if abs_path.stat().st_size != known_file['file_size']:
                    continue

                # Expensive hash check
                new_hash = self.hasher.compute_hash(abs_path)
                if new_hash == known_file['sha256']:
                    return path
            except Exception:
                continue

        return None

    def _create_tombstone(self, change: FileChange) -> None:
        """Create a tombstone record for a deleted/moved file.

        Args:
            change: FileChange representing deletion or move
        """
        reason = 'moved' if change.change_type == ChangeType.MOVED else 'deleted'

        with self.db.get_connection() as conn:
            conn.execute("""
                INSERT INTO tombstones (
                    file_path, filename, file_sha256, file_size,
                    reason, new_path
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                change.file_path,
                change.filename,
                change.old_sha256,
                change.file_size,
                reason,
                change.new_path
            ))

        logger.info(f"Created tombstone for {change.file_path} (reason: {reason})")

    def get_unreported_tombstones(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get tombstones not yet reported to cloud.

        Args:
            limit: Maximum number to return

        Returns:
            List of tombstone records
        """
        with self.db.get_connection() as conn:
            rows = conn.execute("""
                SELECT * FROM tombstones
                WHERE reported_to_cloud = 0
                ORDER BY deleted_at ASC
                LIMIT ?
            """, (limit,)).fetchall()
            return [dict(row) for row in rows]

    def mark_tombstone_reported(
        self,
        tombstone_id: int,
        cloud_response: Optional[str] = None
    ) -> None:
        """Mark a tombstone as reported to cloud.

        Args:
            tombstone_id: Tombstone ID
            cloud_response: Optional JSON response from cloud
        """
        with self.db.get_connection() as conn:
            conn.execute("""
                UPDATE tombstones SET
                    reported_to_cloud = 1,
                    reported_at = ?,
                    cloud_response = ?
                WHERE id = ?
            """, (int(time.time()), cloud_response, tombstone_id))


class ChangeBuffer:
    """Buffers file changes for batch processing."""

    def __init__(self, max_size: int = 1000, flush_interval_seconds: int = 60):
        """Initialize change buffer.

        Args:
            max_size: Maximum buffer size before auto-flush
            flush_interval_seconds: Time between auto-flushes
        """
        self.max_size = max_size
        self.flush_interval = flush_interval_seconds
        self.buffer: List[FileChange] = []
        self.last_flush = time.time()

    def add(self, change: FileChange) -> bool:
        """Add a change to buffer.

        Args:
            change: FileChange to add

        Returns:
            True if buffer should be flushed
        """
        self.buffer.append(change)

        should_flush = (
            len(self.buffer) >= self.max_size or
            (time.time() - self.last_flush) >= self.flush_interval
        )

        return should_flush

    def flush(self) -> List[FileChange]:
        """Flush and return buffered changes.

        Returns:
            List of buffered changes
        """
        changes = self.buffer.copy()
        self.buffer.clear()
        self.last_flush = time.time()
        return changes

    def __len__(self) -> int:
        return len(self.buffer)
