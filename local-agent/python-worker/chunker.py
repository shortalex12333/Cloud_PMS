"""
CelesteOS Local Agent - File Chunker
Splits large files into chunks for upload
"""

import os
import math
import logging
from typing import List, Tuple
from pathlib import Path
from hasher import FileHasher

logger = logging.getLogger(__name__)


class FileChunker:
    """
    Splits files into fixed-size chunks for resumable uploads.
    """

    # Default chunk size: 10MB (configurable based on network conditions)
    DEFAULT_CHUNK_SIZE = 10 * 1024 * 1024  # 10MB
    MIN_CHUNK_SIZE = 5 * 1024 * 1024       # 5MB minimum
    MAX_CHUNK_SIZE = 20 * 1024 * 1024      # 20MB maximum

    def __init__(self, chunk_size: int = None, temp_dir: str = None):
        """
        Initialize file chunker.

        Args:
            chunk_size: Chunk size in bytes (default: 10MB)
            temp_dir: Directory for temporary chunk files
        """
        if chunk_size is None:
            chunk_size = self.DEFAULT_CHUNK_SIZE

        # Validate chunk size
        if chunk_size < self.MIN_CHUNK_SIZE:
            logger.warning(f"Chunk size {chunk_size} below minimum, using {self.MIN_CHUNK_SIZE}")
            chunk_size = self.MIN_CHUNK_SIZE
        elif chunk_size > self.MAX_CHUNK_SIZE:
            logger.warning(f"Chunk size {chunk_size} above maximum, using {self.MAX_CHUNK_SIZE}")
            chunk_size = self.MAX_CHUNK_SIZE

        self.chunk_size = chunk_size

        # Set up temp directory
        if temp_dir is None:
            temp_dir = os.path.expanduser("~/Library/Application Support/CelesteOS/chunks")

        self.temp_dir = temp_dir
        os.makedirs(self.temp_dir, exist_ok=True)

        logger.info(f"FileChunker initialized: chunk_size={chunk_size}, temp_dir={temp_dir}")

    def calculate_chunks(self, file_size: int) -> int:
        """
        Calculate number of chunks needed for a file.

        Args:
            file_size: File size in bytes

        Returns:
            Number of chunks needed
        """
        return math.ceil(file_size / self.chunk_size)

    def should_chunk_file(self, file_size: int) -> bool:
        """
        Determine if a file should be chunked.

        Args:
            file_size: File size in bytes

        Returns:
            True if file should be chunked (larger than chunk size)
        """
        return file_size > self.chunk_size

    def create_chunks(self, file_path: str, file_sha256: str) -> List[dict]:
        """
        Split a file into chunks and save to temp directory.

        Args:
            file_path: Path to source file
            file_sha256: SHA256 hash of the file (for naming)

        Returns:
            List of chunk metadata dicts with:
                - chunk_index: int
                - chunk_path: str
                - chunk_size: int
                - chunk_sha256: str

        Raises:
            FileNotFoundError: If source file doesn't exist
            IOError: If chunk creation fails
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        file_size = os.path.getsize(file_path)
        total_chunks = self.calculate_chunks(file_size)

        logger.info(f"Chunking file {file_path} ({file_size} bytes) into {total_chunks} chunks")

        chunks = []

        try:
            with open(file_path, 'rb') as source_file:
                for chunk_index in range(total_chunks):
                    # Read chunk data
                    chunk_data = source_file.read(self.chunk_size)
                    actual_chunk_size = len(chunk_data)

                    if actual_chunk_size == 0:
                        break  # End of file

                    # Generate chunk filename: {file_sha256}_chunk_{index}
                    chunk_filename = f"{file_sha256}_chunk_{chunk_index}"
                    chunk_path = os.path.join(self.temp_dir, chunk_filename)

                    # Write chunk to temp file
                    with open(chunk_path, 'wb') as chunk_file:
                        chunk_file.write(chunk_data)

                    # Compute chunk SHA256
                    chunk_sha256 = FileHasher.compute_sha256_for_data(chunk_data)

                    chunk_metadata = {
                        'chunk_index': chunk_index,
                        'chunk_path': chunk_path,
                        'chunk_size': actual_chunk_size,
                        'chunk_sha256': chunk_sha256
                    }

                    chunks.append(chunk_metadata)

                    logger.debug(f"Created chunk {chunk_index}/{total_chunks}: "
                               f"{actual_chunk_size} bytes, hash={chunk_sha256[:16]}...")

            logger.info(f"Successfully created {len(chunks)} chunks for {file_path}")
            return chunks

        except Exception as e:
            logger.error(f"Failed to create chunks for {file_path}: {e}")
            # Clean up any partially created chunks
            self._cleanup_partial_chunks(chunks)
            raise

    def _cleanup_partial_chunks(self, chunks: List[dict]):
        """Clean up partially created chunks on error"""
        for chunk in chunks:
            chunk_path = chunk.get('chunk_path')
            if chunk_path and os.path.exists(chunk_path):
                try:
                    os.remove(chunk_path)
                    logger.debug(f"Cleaned up partial chunk: {chunk_path}")
                except Exception as e:
                    logger.warning(f"Failed to clean up chunk {chunk_path}: {e}")

    def cleanup_chunks(self, chunks: List[dict]):
        """
        Clean up chunk files after successful upload.

        Args:
            chunks: List of chunk metadata dicts
        """
        deleted_count = 0
        for chunk in chunks:
            chunk_path = chunk.get('chunk_path')
            if chunk_path and os.path.exists(chunk_path):
                try:
                    os.remove(chunk_path)
                    deleted_count += 1
                except Exception as e:
                    logger.warning(f"Failed to delete chunk {chunk_path}: {e}")

        logger.info(f"Cleaned up {deleted_count}/{len(chunks)} chunk files")

    def cleanup_file_chunks(self, file_sha256: str):
        """
        Clean up all chunks for a specific file.

        Args:
            file_sha256: SHA256 hash of the file
        """
        pattern = f"{file_sha256}_chunk_*"
        deleted_count = 0

        for filename in os.listdir(self.temp_dir):
            if filename.startswith(f"{file_sha256}_chunk_"):
                chunk_path = os.path.join(self.temp_dir, filename)
                try:
                    os.remove(chunk_path)
                    deleted_count += 1
                except Exception as e:
                    logger.warning(f"Failed to delete chunk {chunk_path}: {e}")

        if deleted_count > 0:
            logger.info(f"Cleaned up {deleted_count} chunks for file {file_sha256[:16]}...")

    def cleanup_old_chunks(self, age_hours: int = 24):
        """
        Clean up chunks older than specified age.

        Args:
            age_hours: Age threshold in hours
        """
        import time
        current_time = time.time()
        age_seconds = age_hours * 3600
        deleted_count = 0

        for filename in os.listdir(self.temp_dir):
            chunk_path = os.path.join(self.temp_dir, filename)

            if not os.path.isfile(chunk_path):
                continue

            try:
                file_age = current_time - os.path.getmtime(chunk_path)
                if file_age > age_seconds:
                    os.remove(chunk_path)
                    deleted_count += 1
                    logger.debug(f"Deleted old chunk: {filename}")
            except Exception as e:
                logger.warning(f"Failed to process chunk {chunk_path}: {e}")

        if deleted_count > 0:
            logger.info(f"Cleaned up {deleted_count} old chunk files (>{age_hours}h)")

        return deleted_count

    def get_chunk_info(self, chunk_path: str) -> dict:
        """
        Get metadata for a chunk file.

        Args:
            chunk_path: Path to chunk file

        Returns:
            Dict with chunk metadata
        """
        if not os.path.exists(chunk_path):
            raise FileNotFoundError(f"Chunk not found: {chunk_path}")

        stat = os.stat(chunk_path)
        chunk_sha256 = FileHasher.compute_sha256(chunk_path)

        return {
            'chunk_path': chunk_path,
            'chunk_size': stat.st_size,
            'chunk_sha256': chunk_sha256,
            'modified': stat.st_mtime
        }

    def verify_chunks(self, chunks: List[dict]) -> Tuple[bool, List[int]]:
        """
        Verify that all chunks exist and have correct hashes.

        Args:
            chunks: List of chunk metadata dicts

        Returns:
            Tuple of (all_valid, list_of_invalid_indices)
        """
        invalid_indices = []

        for chunk in chunks:
            chunk_index = chunk['chunk_index']
            chunk_path = chunk['chunk_path']
            expected_hash = chunk['chunk_sha256']

            # Check existence
            if not os.path.exists(chunk_path):
                logger.error(f"Chunk {chunk_index} missing: {chunk_path}")
                invalid_indices.append(chunk_index)
                continue

            # Verify hash
            try:
                actual_hash = FileHasher.compute_sha256(chunk_path)
                if actual_hash != expected_hash:
                    logger.error(f"Chunk {chunk_index} hash mismatch. "
                               f"Expected: {expected_hash}, Actual: {actual_hash}")
                    invalid_indices.append(chunk_index)
            except Exception as e:
                logger.error(f"Failed to verify chunk {chunk_index}: {e}")
                invalid_indices.append(chunk_index)

        all_valid = len(invalid_indices) == 0

        if all_valid:
            logger.info(f"All {len(chunks)} chunks verified successfully")
        else:
            logger.warning(f"{len(invalid_indices)} chunks failed verification")

        return all_valid, invalid_indices


def chunk_file(file_path: str, file_sha256: str, chunk_size: int = None) -> List[dict]:
    """
    Convenience function to chunk a file.

    Args:
        file_path: Path to file
        file_sha256: SHA256 hash of file
        chunk_size: Optional chunk size

    Returns:
        List of chunk metadata dicts
    """
    chunker = FileChunker(chunk_size=chunk_size)
    return chunker.create_chunks(file_path, file_sha256)
