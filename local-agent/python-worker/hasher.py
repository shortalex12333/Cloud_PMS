"""
CelesteOS Local Agent - File Hasher
Computes SHA256 hashes for files
"""

import hashlib
import os
import logging
from typing import Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class FileHasher:
    """
    Computes SHA256 hashes for files using streaming to handle large files efficiently.
    """

    BUFFER_SIZE = 1024 * 1024  # 1MB buffer for reading files

    @staticmethod
    def compute_sha256(file_path: str, buffer_size: Optional[int] = None) -> str:
        """
        Compute SHA256 hash of a file.

        Args:
            file_path: Path to file
            buffer_size: Buffer size for reading (default: 1MB)

        Returns:
            SHA256 hash as hex string

        Raises:
            FileNotFoundError: If file doesn't exist
            PermissionError: If file can't be read
            IOError: If read error occurs
        """
        if buffer_size is None:
            buffer_size = FileHasher.BUFFER_SIZE

        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        if not os.path.isfile(file_path):
            raise ValueError(f"Not a file: {file_path}")

        sha256_hash = hashlib.sha256()

        try:
            with open(file_path, 'rb') as f:
                while True:
                    data = f.read(buffer_size)
                    if not data:
                        break
                    sha256_hash.update(data)

            hash_hex = sha256_hash.hexdigest()
            logger.debug(f"Computed SHA256 for {file_path}: {hash_hex}")
            return hash_hex

        except PermissionError as e:
            logger.error(f"Permission denied reading {file_path}: {e}")
            raise
        except IOError as e:
            logger.error(f"IO error reading {file_path}: {e}")
            raise

    @staticmethod
    def compute_sha256_for_data(data: bytes) -> str:
        """
        Compute SHA256 for raw bytes data.

        Args:
            data: Raw bytes

        Returns:
            SHA256 hash as hex string
        """
        sha256_hash = hashlib.sha256()
        sha256_hash.update(data)
        return sha256_hash.hexdigest()

    @staticmethod
    def verify_file_hash(file_path: str, expected_hash: str) -> bool:
        """
        Verify that a file matches an expected SHA256 hash.

        Args:
            file_path: Path to file
            expected_hash: Expected SHA256 hash

        Returns:
            True if hashes match, False otherwise
        """
        try:
            actual_hash = FileHasher.compute_sha256(file_path)
            matches = (actual_hash.lower() == expected_hash.lower())

            if not matches:
                logger.warning(f"Hash mismatch for {file_path}. "
                             f"Expected: {expected_hash}, Actual: {actual_hash}")

            return matches

        except Exception as e:
            logger.error(f"Failed to verify hash for {file_path}: {e}")
            return False

    @staticmethod
    def get_file_info(file_path: str) -> dict:
        """
        Get file information including size and hash.

        Args:
            file_path: Path to file

        Returns:
            Dict with file metadata
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        stat = os.stat(file_path)

        return {
            'path': file_path,
            'filename': os.path.basename(file_path),
            'size': stat.st_size,
            'modified': stat.st_mtime,
            'sha256': FileHasher.compute_sha256(file_path)
        }


class ChunkHasher:
    """
    Handles hashing for file chunks.
    """

    @staticmethod
    def compute_chunk_hash(chunk_path: str) -> str:
        """
        Compute SHA256 hash for a chunk file.

        Args:
            chunk_path: Path to chunk file

        Returns:
            SHA256 hash as hex string
        """
        return FileHasher.compute_sha256(chunk_path)

    @staticmethod
    def verify_chunk_integrity(chunk_path: str, expected_hash: str) -> bool:
        """
        Verify chunk integrity against expected hash.

        Args:
            chunk_path: Path to chunk file
            expected_hash: Expected SHA256 hash

        Returns:
            True if valid, False otherwise
        """
        return FileHasher.verify_file_hash(chunk_path, expected_hash)


class BatchHasher:
    """
    Batch file hashing with progress tracking.
    """

    def __init__(self, callback=None):
        """
        Initialize batch hasher.

        Args:
            callback: Optional callback function(file_path, hash, index, total)
        """
        self.callback = callback

    def hash_files(self, file_paths: list) -> dict:
        """
        Hash multiple files.

        Args:
            file_paths: List of file paths

        Returns:
            Dict mapping file_path -> hash
        """
        results = {}
        total = len(file_paths)

        for index, file_path in enumerate(file_paths):
            try:
                file_hash = FileHasher.compute_sha256(file_path)
                results[file_path] = {
                    'hash': file_hash,
                    'success': True,
                    'error': None
                }

                if self.callback:
                    self.callback(file_path, file_hash, index + 1, total)

            except Exception as e:
                logger.error(f"Failed to hash {file_path}: {e}")
                results[file_path] = {
                    'hash': None,
                    'success': False,
                    'error': str(e)
                }

        return results


# Utility functions for common hash operations

def hash_file(file_path: str) -> str:
    """Convenience function to hash a single file"""
    return FileHasher.compute_sha256(file_path)


def hash_data(data: bytes) -> str:
    """Convenience function to hash raw data"""
    return FileHasher.compute_sha256_for_data(data)


def verify_hash(file_path: str, expected_hash: str) -> bool:
    """Convenience function to verify file hash"""
    return FileHasher.verify_file_hash(file_path, expected_hash)
