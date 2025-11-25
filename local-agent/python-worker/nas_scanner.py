"""
CelesteOS Local Agent - NAS Scanner
Discovers and monitors files on mounted NAS
"""

import os
import logging
import mimetypes
from datetime import datetime
from typing import List, Dict, Optional, Callable
from pathlib import Path

logger = logging.getLogger(__name__)


class NASScanner:
    """
    Scans NAS mount points for files to ingest.
    Supports recursive scanning, file filtering, and change detection.
    """

    # File extensions to include by default
    DEFAULT_INCLUDED_EXTENSIONS = {
        # Documents
        '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
        '.odt', '.ods', '.odp',
        # Text
        '.txt', '.md', '.csv', '.json', '.xml',
        # Email
        '.msg', '.eml',
        # Images (for manuals/diagrams)
        '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.svg',
        # Technical
        '.dwg', '.dxf',  # CAD drawings
        '.stp', '.step',  # 3D models
    }

    # Extensions to explicitly exclude (large binaries)
    DEFAULT_EXCLUDED_EXTENSIONS = {
        '.iso', '.dmg', '.exe', '.dll', '.bin',
        '.mp4', '.mov', '.avi', '.mkv',  # Videos
        '.zip', '.tar', '.gz', '.rar', '.7z',  # Archives
        '.app', '.pkg',  # macOS apps/installers
    }

    def __init__(self,
                 nas_mount_point: str,
                 included_extensions: Optional[set] = None,
                 excluded_extensions: Optional[set] = None,
                 max_file_size: Optional[int] = None):
        """
        Initialize NAS scanner.

        Args:
            nas_mount_point: Path to mounted NAS (e.g., /Volumes/CelesteOS_NAS)
            included_extensions: Set of file extensions to include (e.g., {'.pdf', '.docx'})
            excluded_extensions: Set of file extensions to exclude
            max_file_size: Maximum file size in bytes (None = no limit)
        """
        self.nas_mount_point = os.path.abspath(nas_mount_point)

        if not os.path.exists(self.nas_mount_point):
            raise ValueError(f"NAS mount point does not exist: {nas_mount_point}")

        if not os.path.ismount(self.nas_mount_point):
            logger.warning(f"Path {nas_mount_point} is not a mount point. "
                         "This may cause issues if NAS disconnects.")

        self.included_extensions = included_extensions or self.DEFAULT_INCLUDED_EXTENSIONS
        self.excluded_extensions = excluded_extensions or self.DEFAULT_EXCLUDED_EXTENSIONS
        self.max_file_size = max_file_size

        logger.info(f"NASScanner initialized for: {self.nas_mount_point}")
        logger.info(f"Including extensions: {self.included_extensions}")
        logger.info(f"Excluding extensions: {self.excluded_extensions}")

    def is_nas_available(self) -> bool:
        """
        Check if NAS mount point is available.

        Returns:
            True if NAS is accessible, False otherwise
        """
        return os.path.exists(self.nas_mount_point) and os.path.isdir(self.nas_mount_point)

    def should_include_file(self, file_path: str) -> bool:
        """
        Determine if a file should be included in scan.

        Args:
            file_path: Path to file

        Returns:
            True if file should be included
        """
        # Get file extension
        _, ext = os.path.splitext(file_path)
        ext = ext.lower()

        # Check excluded first
        if ext in self.excluded_extensions:
            return False

        # Check included
        if ext not in self.included_extensions:
            return False

        # Check file size if limit set
        if self.max_file_size:
            try:
                file_size = os.path.getsize(file_path)
                if file_size > self.max_file_size:
                    logger.debug(f"Skipping large file ({file_size} bytes): {file_path}")
                    return False
            except OSError:
                return False

        return True

    def scan_directory(self,
                       directory_path: str = None,
                       recursive: bool = True,
                       progress_callback: Optional[Callable] = None) -> List[Dict]:
        """
        Scan a directory for files.

        Args:
            directory_path: Directory to scan (default: nas_mount_point)
            recursive: Whether to scan subdirectories
            progress_callback: Optional callback(file_count, dir_count)

        Returns:
            List of file metadata dicts
        """
        if directory_path is None:
            directory_path = self.nas_mount_point

        directory_path = os.path.abspath(directory_path)

        if not os.path.exists(directory_path):
            raise ValueError(f"Directory does not exist: {directory_path}")

        if not os.path.isdir(directory_path):
            raise ValueError(f"Not a directory: {directory_path}")

        logger.info(f"Scanning directory: {directory_path} (recursive={recursive})")

        discovered_files = []
        file_count = 0
        dir_count = 0

        try:
            if recursive:
                # Recursive walk
                for root, dirs, files in os.walk(directory_path):
                    dir_count += 1

                    # Skip hidden directories
                    dirs[:] = [d for d in dirs if not d.startswith('.')]

                    for filename in files:
                        # Skip hidden files
                        if filename.startswith('.'):
                            continue

                        file_path = os.path.join(root, filename)

                        if self.should_include_file(file_path):
                            try:
                                file_metadata = self._get_file_metadata(file_path)
                                discovered_files.append(file_metadata)
                                file_count += 1

                                if progress_callback and file_count % 100 == 0:
                                    progress_callback(file_count, dir_count)

                            except Exception as e:
                                logger.warning(f"Failed to process file {file_path}: {e}")

            else:
                # Non-recursive - single directory only
                for filename in os.listdir(directory_path):
                    file_path = os.path.join(directory_path, filename)

                    if not os.path.isfile(file_path):
                        continue

                    if filename.startswith('.'):
                        continue

                    if self.should_include_file(file_path):
                        try:
                            file_metadata = self._get_file_metadata(file_path)
                            discovered_files.append(file_metadata)
                            file_count += 1
                        except Exception as e:
                            logger.warning(f"Failed to process file {file_path}: {e}")

            logger.info(f"Scan complete: {file_count} files discovered in {dir_count} directories")

            return discovered_files

        except PermissionError as e:
            logger.error(f"Permission denied scanning {directory_path}: {e}")
            raise
        except Exception as e:
            logger.error(f"Error scanning {directory_path}: {e}")
            raise

    def _get_file_metadata(self, file_path: str) -> Dict:
        """
        Extract metadata for a file.

        Args:
            file_path: Path to file

        Returns:
            Dict with file metadata
        """
        stat = os.stat(file_path)
        filename = os.path.basename(file_path)
        _, ext = os.path.splitext(filename)

        # Get MIME type
        mime_type, _ = mimetypes.guess_type(file_path)

        # Get relative NAS path
        nas_path = os.path.relpath(file_path, self.nas_mount_point)

        # Convert timestamp to datetime
        last_modified = datetime.fromtimestamp(stat.st_mtime)

        return {
            'file_path': file_path,
            'nas_path': nas_path,
            'filename': filename,
            'file_size': stat.st_size,
            'extension': ext.lower(),
            'mime_type': mime_type,
            'last_modified': last_modified,
        }

    def scan_for_changes(self, known_files: Dict[str, Dict]) -> Dict:
        """
        Scan for changes compared to known files.

        Args:
            known_files: Dict mapping file_path -> metadata

        Returns:
            Dict with 'new', 'modified', 'deleted' lists
        """
        logger.info("Scanning for changes...")

        current_files = {}
        for file_metadata in self.scan_directory():
            current_files[file_metadata['file_path']] = file_metadata

        new_files = []
        modified_files = []
        deleted_files = []

        # Find new and modified files
        for file_path, metadata in current_files.items():
            if file_path not in known_files:
                # New file
                new_files.append(metadata)
            else:
                # Check if modified
                known_metadata = known_files[file_path]
                if metadata['last_modified'] != known_metadata['last_modified']:
                    modified_files.append(metadata)

        # Find deleted files
        for file_path in known_files:
            if file_path not in current_files:
                deleted_files.append(known_files[file_path])

        logger.info(f"Changes detected: {len(new_files)} new, "
                   f"{len(modified_files)} modified, {len(deleted_files)} deleted")

        return {
            'new': new_files,
            'modified': modified_files,
            'deleted': deleted_files
        }

    def get_nas_stats(self) -> Dict:
        """
        Get statistics about NAS mount.

        Returns:
            Dict with NAS statistics
        """
        if not self.is_nas_available():
            return {'available': False}

        try:
            stat = os.statvfs(self.nas_mount_point)
            total_space = stat.f_blocks * stat.f_frsize
            free_space = stat.f_bavail * stat.f_frsize
            used_space = total_space - free_space

            return {
                'available': True,
                'mount_point': self.nas_mount_point,
                'total_space': total_space,
                'used_space': used_space,
                'free_space': free_space,
                'usage_percent': (used_space / total_space * 100) if total_space > 0 else 0
            }
        except Exception as e:
            logger.error(f"Failed to get NAS stats: {e}")
            return {'available': False, 'error': str(e)}


class DirectoryWatcher:
    """
    Monitors specific directories for changes.
    """

    def __init__(self, scanner: NASScanner, watch_dirs: List[str]):
        """
        Initialize directory watcher.

        Args:
            scanner: NASScanner instance
            watch_dirs: List of directory paths to watch
        """
        self.scanner = scanner
        self.watch_dirs = [os.path.abspath(d) for d in watch_dirs]
        self.last_scan = {}

        logger.info(f"DirectoryWatcher initialized for {len(watch_dirs)} directories")

    def scan_all(self) -> List[Dict]:
        """
        Scan all watched directories.

        Returns:
            List of all discovered files
        """
        all_files = []

        for watch_dir in self.watch_dirs:
            if not os.path.exists(watch_dir):
                logger.warning(f"Watch directory not found: {watch_dir}")
                continue

            try:
                files = self.scanner.scan_directory(watch_dir)
                all_files.extend(files)
                self.last_scan[watch_dir] = datetime.now()
            except Exception as e:
                logger.error(f"Failed to scan {watch_dir}: {e}")

        return all_files

    def check_for_updates(self, known_files: Dict[str, Dict]) -> Dict:
        """
        Check all watched directories for changes.

        Args:
            known_files: Dict of known files

        Returns:
            Dict with changes
        """
        return self.scanner.scan_for_changes(known_files)


# Utility functions

def scan_nas(nas_mount_point: str, recursive: bool = True) -> List[Dict]:
    """
    Convenience function to scan NAS.

    Args:
        nas_mount_point: NAS mount path
        recursive: Scan subdirectories

    Returns:
        List of file metadata
    """
    scanner = NASScanner(nas_mount_point)
    return scanner.scan_directory(recursive=recursive)


def check_nas_available(nas_mount_point: str) -> bool:
    """
    Check if NAS is available.

    Args:
        nas_mount_point: NAS mount path

    Returns:
        True if available
    """
    return os.path.exists(nas_mount_point) and os.path.isdir(nas_mount_point)
