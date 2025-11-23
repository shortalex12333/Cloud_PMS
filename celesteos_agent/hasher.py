"""
SHA256 hash computation for file integrity verification.
Supports parallel hashing with worker pool.
"""

import hashlib
import time
from pathlib import Path
from typing import Optional, Callable
from concurrent.futures import ThreadPoolExecutor, Future
from .logger import get_logger

logger = get_logger(__name__)


class FileHasher:
    """Computes SHA256 hashes for files."""

    CHUNK_SIZE = 8192 * 1024  # 8MB chunks for reading

    def __init__(self, num_workers: int = 4):
        """Initialize file hasher.

        Args:
            num_workers: Number of parallel hash workers
        """
        self.num_workers = num_workers
        self.executor = ThreadPoolExecutor(max_workers=num_workers)

    def compute_hash(self, file_path: Path, progress_callback: Optional[Callable] = None) -> str:
        """Compute SHA256 hash of a file.

        Args:
            file_path: Path to file
            progress_callback: Optional callback(bytes_read, total_bytes)

        Returns:
            SHA256 hash (hex string)

        Raises:
            FileNotFoundError: If file doesn't exist
            PermissionError: If file cannot be read
            OSError: If file is not a regular file (socket, fifo, etc.)
        """
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # Skip special files (sockets, fifos, block/char devices)
        if not file_path.is_file():
            raise OSError(f"Not a regular file (socket/fifo/device): {file_path}")

        logger.debug(f"Computing SHA256 for: {file_path}")
        start_time = time.time()

        sha256 = hashlib.sha256()
        file_size = file_path.stat().st_size
        bytes_read = 0

        try:
            with open(file_path, 'rb') as f:
                while True:
                    chunk = f.read(self.CHUNK_SIZE)
                    if not chunk:
                        break

                    sha256.update(chunk)
                    bytes_read += len(chunk)

                    if progress_callback:
                        progress_callback(bytes_read, file_size)

            hash_hex = sha256.hexdigest()
            duration = time.time() - start_time

            logger.debug(
                f"SHA256 computed for {file_path.name} in {duration:.2f}s: {hash_hex}"
            )

            return hash_hex

        except PermissionError:
            logger.error(f"Permission denied reading file: {file_path}")
            raise

        except Exception as e:
            logger.error(f"Error computing hash for {file_path}: {e}", exc_info=True)
            raise

    def compute_hash_async(
        self,
        file_path: Path,
        callback: Optional[Callable[[str], None]] = None
    ) -> Future:
        """Compute hash asynchronously.

        Args:
            file_path: Path to file
            callback: Optional callback(hash_hex) when complete

        Returns:
            Future object
        """
        future = self.executor.submit(self.compute_hash, file_path)

        if callback:
            future.add_done_callback(lambda f: callback(f.result()))

        return future

    def shutdown(self) -> None:
        """Shutdown the thread pool."""
        logger.info("Shutting down hash worker pool")
        self.executor.shutdown(wait=True)

    @staticmethod
    def verify_hash(file_path: Path, expected_hash: str) -> bool:
        """Verify file hash matches expected value.

        Args:
            file_path: Path to file
            expected_hash: Expected SHA256 hash

        Returns:
            True if hash matches
        """
        hasher = FileHasher(num_workers=1)
        actual_hash = hasher.compute_hash(file_path)
        return actual_hash.lower() == expected_hash.lower()
