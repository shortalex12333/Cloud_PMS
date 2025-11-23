"""
File chunking and compression for large file uploads.
Splits files into manageable chunks with gzip compression.
"""

import gzip
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from .logger import get_logger
from .hasher import FileHasher

logger = get_logger(__name__)


class FileChunker:
    """Chunks and compresses files for upload."""

    def __init__(self, chunk_size_mb: int = 64, temp_dir: str = "~/.celesteos/tmp"):
        """Initialize file chunker.

        Args:
            chunk_size_mb: Chunk size in MB
            temp_dir: Temporary directory for chunks
        """
        self.chunk_size_bytes = chunk_size_mb * 1024 * 1024
        self.temp_dir = Path(temp_dir).expanduser()
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.hasher = FileHasher(num_workers=1)

    def chunk_file(self, file_path: Path, file_sha256: str) -> List[Dict[str, Any]]:
        """Chunk and compress a file.

        Args:
            file_path: Path to source file
            file_sha256: SHA256 of source file (for naming chunks)

        Returns:
            List of chunk dicts with metadata

        Example chunk dict:
            {
                'chunk_index': 0,
                'chunk_path': '/path/to/chunk',
                'chunk_size': 12345,
                'chunk_sha256': 'abc123...',
                'original_size': 67890  # Before compression
            }
        """
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        file_size = file_path.stat().st_size
        total_chunks = (file_size + self.chunk_size_bytes - 1) // self.chunk_size_bytes

        logger.info(
            f"Chunking file {file_path.name} ({file_size} bytes) "
            f"into {total_chunks} chunks"
        )

        chunks = []

        try:
            with open(file_path, 'rb') as source:
                for chunk_index in range(total_chunks):
                    chunk_data = source.read(self.chunk_size_bytes)
                    original_size = len(chunk_data)

                    if not chunk_data:
                        break

                    # Create compressed chunk
                    chunk_filename = f"{file_sha256}.part_{chunk_index}.gz"
                    chunk_path = self.temp_dir / chunk_filename

                    # Compress chunk
                    with gzip.open(chunk_path, 'wb', compresslevel=6) as gz:
                        gz.write(chunk_data)

                    chunk_size = chunk_path.stat().st_size

                    # Compute chunk SHA256
                    chunk_sha256 = self.hasher.compute_hash(chunk_path)

                    chunk_info = {
                        'chunk_index': chunk_index,
                        'chunk_path': str(chunk_path),
                        'chunk_size': chunk_size,
                        'chunk_sha256': chunk_sha256,
                        'original_size': original_size
                    }

                    chunks.append(chunk_info)

                    logger.debug(
                        f"Created chunk {chunk_index}/{total_chunks-1}: "
                        f"{original_size} -> {chunk_size} bytes "
                        f"({chunk_size/original_size*100:.1f}% compression)"
                    )

            logger.info(
                f"File chunked into {len(chunks)} parts, "
                f"total compressed size: {sum(c['chunk_size'] for c in chunks)} bytes"
            )

            return chunks

        except Exception as e:
            logger.error(f"Error chunking file {file_path}: {e}", exc_info=True)
            # Cleanup partial chunks
            self.cleanup_chunks(chunks)
            raise

    def cleanup_chunks(self, chunks: List[Dict[str, Any]]) -> None:
        """Delete chunk files.

        Args:
            chunks: List of chunk dicts
        """
        for chunk in chunks:
            chunk_path = Path(chunk['chunk_path'])
            if chunk_path.exists():
                try:
                    chunk_path.unlink()
                    logger.debug(f"Deleted chunk: {chunk_path}")
                except Exception as e:
                    logger.warning(f"Failed to delete chunk {chunk_path}: {e}")

    def cleanup_by_sha(self, file_sha256: str) -> None:
        """Delete all chunks for a given file SHA256.

        Args:
            file_sha256: File SHA256 hash
        """
        pattern = f"{file_sha256}.part_*.gz"
        deleted = 0

        for chunk_file in self.temp_dir.glob(pattern):
            try:
                chunk_file.unlink()
                deleted += 1
            except Exception as e:
                logger.warning(f"Failed to delete {chunk_file}: {e}")

        if deleted > 0:
            logger.info(f"Cleaned up {deleted} chunks for {file_sha256}")

    def cleanup_old_chunks(self, max_age_hours: int = 24) -> int:
        """Delete chunks older than specified age.

        Args:
            max_age_hours: Maximum age in hours

        Returns:
            Number of chunks deleted
        """
        import time
        max_age_seconds = max_age_hours * 3600
        now = time.time()
        deleted = 0

        for chunk_file in self.temp_dir.glob("*.part_*.gz"):
            try:
                age = now - chunk_file.stat().st_mtime
                if age > max_age_seconds:
                    chunk_file.unlink()
                    deleted += 1
            except Exception as e:
                logger.warning(f"Failed to delete old chunk {chunk_file}: {e}")

        if deleted > 0:
            logger.info(f"Cleaned up {deleted} old chunks")

        return deleted

    def reassemble_file(
        self,
        chunks: List[Dict[str, Any]],
        output_path: Path,
        verify_sha256: Optional[str] = None
    ) -> bool:
        """Reassemble file from chunks (for testing/verification).

        Args:
            chunks: List of chunk dicts
            output_path: Path for reassembled file
            verify_sha256: Optional SHA256 to verify

        Returns:
            True if successful and hash matches (if provided)
        """
        logger.info(f"Reassembling {len(chunks)} chunks to {output_path}")

        try:
            # Sort chunks by index
            sorted_chunks = sorted(chunks, key=lambda c: c['chunk_index'])

            with open(output_path, 'wb') as output:
                for chunk in sorted_chunks:
                    chunk_path = Path(chunk['chunk_path'])

                    if not chunk_path.exists():
                        raise FileNotFoundError(f"Chunk not found: {chunk_path}")

                    # Decompress and write
                    with gzip.open(chunk_path, 'rb') as gz:
                        data = gz.read()
                        output.write(data)

            logger.info(f"File reassembled: {output_path}")

            # Verify hash if provided
            if verify_sha256:
                actual_hash = self.hasher.compute_hash(output_path)
                if actual_hash.lower() == verify_sha256.lower():
                    logger.info("SHA256 verification passed")
                    return True
                else:
                    logger.error(
                        f"SHA256 mismatch! Expected: {verify_sha256}, Got: {actual_hash}"
                    )
                    return False

            return True

        except Exception as e:
            logger.error(f"Error reassembling file: {e}", exc_info=True)
            return False
