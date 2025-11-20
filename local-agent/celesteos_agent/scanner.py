"""
NAS file scanner for CelesteOS Local Agent.
Discovers, tracks, and monitors files on NAS.
"""

import os
import time
from pathlib import Path
from typing import List, Dict, Any, Optional, Set
import magic
import fnmatch
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent

from .logger import get_logger
from .database import Database

logger = get_logger(__name__)


class FileScanner:
    """Scans NAS filesystem for documents."""

    def __init__(self, db: Database, nas_path: str, ignore_patterns: List[Dict[str, Any]]):
        """Initialize file scanner.

        Args:
            db: Database instance
            nas_path: Path to NAS root
            ignore_patterns: List of ignore pattern dicts
        """
        self.db = db
        self.nas_path = Path(nas_path).expanduser()
        self.ignore_patterns = ignore_patterns
        self.mime = magic.Magic(mime=True)

        # Statistics
        self.files_discovered = 0
        self.files_changed = 0
        self.files_deleted = 0
        self.scan_start_time = 0

    def should_ignore(self, path: Path) -> bool:
        """Check if file/folder should be ignored.

        Args:
            path: File or folder path

        Returns:
            True if should be ignored
        """
        name = path.name
        relative_path = str(path.relative_to(self.nas_path))

        for pattern_dict in self.ignore_patterns:
            pattern = pattern_dict['pattern']
            pattern_type = pattern_dict['pattern_type']

            if pattern_type == 'glob':
                if fnmatch.fnmatch(name, pattern):
                    return True
                if fnmatch.fnmatch(relative_path, pattern):
                    return True

            elif pattern_type == 'regex':
                import re
                if re.match(pattern, name) or re.match(pattern, relative_path):
                    return True

            elif pattern_type == 'extension':
                if path.suffix == pattern or path.suffix == f".{pattern}":
                    return True

            elif pattern_type == 'folder':
                if pattern in relative_path.split(os.sep):
                    return True

        return False

    def scan(self, full_scan: bool = True, max_depth: int = 100) -> Dict[str, int]:
        """Perform full or incremental scan of NAS.

        Args:
            full_scan: If True, scan all files; if False, only check known files
            max_depth: Maximum directory depth

        Returns:
            Statistics dict
        """
        logger.info(f"Starting {'full' if full_scan else 'incremental'} scan of {self.nas_path}")

        self.scan_start_time = int(time.time())
        self.files_discovered = 0
        self.files_changed = 0
        self.files_deleted = 0

        # Update sync state
        self.db.update_sync_state({
            'is_scanning': True,
            'last_scan_started': self.scan_start_time
        })

        self.db.log_activity('scan_started', f"Started scan of {self.nas_path}")

        try:
            if not self.nas_path.exists():
                raise FileNotFoundError(f"NAS path not found: {self.nas_path}")

            if full_scan:
                self._full_scan(max_depth)
            else:
                self._incremental_scan()

            scan_duration = int(time.time()) - self.scan_start_time

            # Update sync state
            self.db.update_sync_state({
                'is_scanning': False,
                'last_scan_completed': int(time.time()),
                'last_scan_duration_seconds': scan_duration,
                'total_files_discovered': self.files_discovered
            })

            self.db.log_activity(
                'scan_completed',
                f"Scan completed: {self.files_discovered} files discovered, "
                f"{self.files_changed} changed, {self.files_deleted} deleted",
                details=f'{{"duration_seconds": {scan_duration}}}'
            )

            logger.info(
                f"Scan completed in {scan_duration}s: "
                f"{self.files_discovered} discovered, "
                f"{self.files_changed} changed, "
                f"{self.files_deleted} deleted"
            )

            return {
                'files_discovered': self.files_discovered,
                'files_changed': self.files_changed,
                'files_deleted': self.files_deleted,
                'duration_seconds': scan_duration
            }

        except Exception as e:
            logger.error(f"Scan failed: {e}", exc_info=True)
            self.db.update_sync_state({'is_scanning': False})
            self.db.log_error(
                'nas_scan',
                'error',
                f"Scan failed: {e}",
                stack_trace=str(e)
            )
            raise

    def _full_scan(self, max_depth: int) -> None:
        """Perform full recursive scan.

        Args:
            max_depth: Maximum directory depth
        """
        seen_paths: Set[str] = set()

        for root, dirs, files in os.walk(self.nas_path, followlinks=False):
            root_path = Path(root)

            # Check depth
            try:
                depth = len(root_path.relative_to(self.nas_path).parts)
                if depth > max_depth:
                    logger.warning(f"Max depth reached at: {root_path}")
                    dirs.clear()  # Don't descend further
                    continue
            except ValueError:
                # Not relative to nas_path
                continue

            # Filter directories to descend into
            dirs[:] = [d for d in dirs if not self.should_ignore(root_path / d)]

            # Process files
            for filename in files:
                file_path = root_path / filename

                # Skip if should be ignored
                if self.should_ignore(file_path):
                    continue

                try:
                    relative_path = str(file_path.relative_to(self.nas_path))
                    seen_paths.add(relative_path)

                    # Get file info
                    stat = file_path.stat()

                    # Detect MIME type
                    try:
                        mime_type = self.mime.from_file(str(file_path))
                    except Exception:
                        mime_type = 'application/octet-stream'

                    # Store in database (will compute hash later)
                    # For now, use empty SHA256
                    # Hasher will compute actual hash

                    self.files_discovered += 1

                    if self.files_discovered % 100 == 0:
                        logger.info(f"Scanned {self.files_discovered} files...")

                except Exception as e:
                    logger.warning(f"Error processing {file_path}: {e}")
                    continue

        # Mark files not seen as deleted
        # (This would require querying all known files and comparing)
        # For now, we'll do this in a separate cleanup phase

    def _incremental_scan(self) -> None:
        """Perform incremental scan (check only known files)."""
        # Get all known files from database
        # For each file, check if it still exists and if modified time changed
        # This is faster than full scan but doesn't discover new files
        pass

    def discover_file(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """Discover and register a single file.

        Args:
            file_path: Absolute path to file

        Returns:
            File info dict or None if error
        """
        try:
            if not file_path.exists():
                logger.warning(f"File not found: {file_path}")
                return None

            if not file_path.is_file():
                logger.warning(f"Not a file: {file_path}")
                return None

            if self.should_ignore(file_path):
                logger.debug(f"File ignored: {file_path}")
                return None

            stat = file_path.stat()
            relative_path = str(file_path.relative_to(self.nas_path))

            # Detect MIME type
            try:
                mime_type = self.mime.from_file(str(file_path))
            except Exception:
                mime_type = 'application/octet-stream'

            file_info = {
                'file_path': relative_path,
                'absolute_path': str(file_path),
                'filename': file_path.name,
                'file_size': stat.st_size,
                'file_extension': file_path.suffix.lstrip('.'),
                'mime_type': mime_type,
                'last_modified': int(stat.st_mtime)
            }

            logger.debug(f"Discovered file: {file_path.name} ({stat.st_size} bytes)")

            return file_info

        except Exception as e:
            logger.error(f"Error discovering file {file_path}: {e}", exc_info=True)
            return None


class FileWatcher(FileSystemEventHandler):
    """Watches NAS for real-time file changes."""

    def __init__(self, scanner: FileScanner, db: Database):
        """Initialize file watcher.

        Args:
            scanner: FileScanner instance
            db: Database instance
        """
        super().__init__()
        self.scanner = scanner
        self.db = db

    def on_created(self, event: FileSystemEvent) -> None:
        """Handle file creation event.

        Args:
            event: File system event
        """
        if event.is_directory:
            return

        file_path = Path(event.src_path)
        logger.info(f"File created: {file_path}")

        file_info = self.scanner.discover_file(file_path)
        if file_info:
            self.db.log_activity(
                'file_discovered',
                f"New file detected: {file_info['filename']}",
                details=f'{{"size": {file_info["file_size"]}}}'
            )

    def on_modified(self, event: FileSystemEvent) -> None:
        """Handle file modification event.

        Args:
            event: File system event
        """
        if event.is_directory:
            return

        file_path = Path(event.src_path)
        logger.info(f"File modified: {file_path}")

        # Will be picked up by next scan
        # Re-hashing will detect the change

    def on_deleted(self, event: FileSystemEvent) -> None:
        """Handle file deletion event.

        Args:
            event: File system event
        """
        if event.is_directory:
            return

        file_path = Path(event.src_path)
        logger.info(f"File deleted: {file_path}")

        try:
            relative_path = str(file_path.relative_to(self.scanner.nas_path))
            self.db.mark_file_deleted(relative_path)
            self.db.log_activity(
                'file_deleted',
                f"File deleted: {file_path.name}"
            )
        except Exception as e:
            logger.error(f"Error handling file deletion: {e}")

    def on_moved(self, event: FileSystemEvent) -> None:
        """Handle file move event.

        Args:
            event: File system event
        """
        if event.is_directory:
            return

        # Treat as delete + create
        self.on_deleted(event)
        # New file will be discovered on next scan


class NASWatcher:
    """Manages file system watching."""

    def __init__(self, scanner: FileScanner, db: Database):
        """Initialize NAS watcher.

        Args:
            scanner: FileScanner instance
            db: Database instance
        """
        self.scanner = scanner
        self.db = db
        self.observer: Optional[Observer] = None

    def start(self) -> None:
        """Start watching NAS for changes."""
        if self.observer is not None:
            logger.warning("Watcher already running")
            return

        logger.info(f"Starting file watcher for {self.scanner.nas_path}")

        event_handler = FileWatcher(self.scanner, self.db)
        self.observer = Observer()
        self.observer.schedule(
            event_handler,
            str(self.scanner.nas_path),
            recursive=True
        )
        self.observer.start()

        logger.info("File watcher started")

    def stop(self) -> None:
        """Stop watching NAS."""
        if self.observer is None:
            return

        logger.info("Stopping file watcher")
        self.observer.stop()
        self.observer.join(timeout=5)
        self.observer = None

        logger.info("File watcher stopped")

    def is_running(self) -> bool:
        """Check if watcher is running.

        Returns:
            True if running
        """
        return self.observer is not None and self.observer.is_alive()
