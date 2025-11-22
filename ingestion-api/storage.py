"""
Temporary storage management for chunked uploads
"""
import os
import json
import shutil
import asyncio
from pathlib import Path
from typing import Optional
from uuid import UUID
from datetime import datetime, timedelta
import logging

from config import settings
from models import IngestionState

logger = logging.getLogger(__name__)


class TempStorageManager:
    """Manages temporary storage for chunked file uploads"""

    def __init__(self, base_dir: str = None):
        self.base_dir = Path(base_dir or settings.TEMP_UPLOAD_DIR)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def get_upload_dir(self, upload_id: UUID) -> Path:
        """Get the directory path for a specific upload"""
        return self.base_dir / str(upload_id)

    def get_chunk_path(self, upload_id: UUID, chunk_index: int) -> Path:
        """Get the file path for a specific chunk"""
        upload_dir = self.get_upload_dir(upload_id)
        return upload_dir / f"chunk_{chunk_index:06d}.bin"

    def get_meta_path(self, upload_id: UUID) -> Path:
        """Get the metadata file path for an upload"""
        upload_dir = self.get_upload_dir(upload_id)
        return upload_dir / "meta.json"

    async def init_upload(
        self,
        upload_id: UUID,
        yacht_id: UUID,
        filename: str,
        file_sha256: str,
        file_size: int,
        total_chunks: int,
        source: str = "nas"
    ) -> IngestionState:
        """
        Initialize a new upload session

        Creates directory structure and metadata file
        """
        upload_dir = self.get_upload_dir(upload_id)

        # Create upload directory
        upload_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Created upload directory: {upload_dir}")

        # Create initial state with chunk tracking
        state = IngestionState(
            upload_id=upload_id,
            yacht_id=yacht_id,
            filename=filename,
            file_sha256=file_sha256,
            file_size=file_size,
            total_chunks=total_chunks,
            expected_chunks=total_chunks,  # Store expected count for verification
            chunks_received=0,
            chunks_received_set=set(),  # Track which chunks received
            chunk_hashes={},  # Track hash of each chunk
            status="INITIATED",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            source=source
        )

        # Write metadata
        await self.save_state(state)

        return state

    async def save_state(self, state: IngestionState) -> None:
        """Save upload state to metadata file"""
        meta_path = self.get_meta_path(state.upload_id)
        state.updated_at = datetime.utcnow()

        # Convert state to dict with proper serialization for sets
        state_dict = state.model_dump(mode="json")
        # Convert set to list for JSON serialization
        state_dict["chunks_received_set"] = list(state.chunks_received_set)
        # Convert dict keys to strings for JSON
        state_dict["chunk_hashes"] = {str(k): v for k, v in state.chunk_hashes.items()}

        with open(meta_path, "w") as f:
            json.dump(state_dict, f, indent=2, default=str)

    async def load_state(self, upload_id: UUID) -> Optional[IngestionState]:
        """Load upload state from metadata file"""
        meta_path = self.get_meta_path(upload_id)

        if not meta_path.exists():
            return None

        try:
            with open(meta_path, "r") as f:
                data = json.load(f)

            # Convert list back to set for chunks_received_set
            if "chunks_received_set" in data:
                data["chunks_received_set"] = set(data["chunks_received_set"])
            else:
                data["chunks_received_set"] = set()

            # Convert string keys back to int for chunk_hashes
            if "chunk_hashes" in data:
                data["chunk_hashes"] = {int(k): v for k, v in data["chunk_hashes"].items()}
            else:
                data["chunk_hashes"] = {}

            # Handle legacy state files without expected_chunks
            if "expected_chunks" not in data:
                data["expected_chunks"] = data.get("total_chunks", 0)

            return IngestionState(**data)
        except Exception as e:
            logger.error(f"Error loading state for {upload_id}: {e}")
            return None

    async def save_chunk(
        self,
        upload_id: UUID,
        chunk_index: int,
        chunk_data: bytes,
        chunk_sha256: str,
        state: IngestionState
    ) -> tuple[bool, bool, str]:
        """
        Save a chunk to disk and verify its hash

        Args:
            upload_id: Upload session ID
            chunk_index: Index of the chunk (0-based)
            chunk_data: Raw chunk bytes
            chunk_sha256: Expected SHA256 hash of chunk
            state: Current upload state for idempotency check

        Returns:
            Tuple of (success, is_duplicate, error_message)
            - success: True if chunk saved/verified successfully
            - is_duplicate: True if this chunk was already received (idempotent)
            - error_message: Error description if success is False
        """
        import hashlib

        # Check if chunk was already received (idempotency)
        if chunk_index in state.chunks_received_set:
            # Verify the hash matches what we received before
            previous_hash = state.chunk_hashes.get(chunk_index)
            if previous_hash and previous_hash == chunk_sha256:
                logger.info(
                    f"Duplicate chunk {chunk_index} for upload {upload_id} - "
                    f"hash matches, returning success (idempotent)"
                )
                return (True, True, "")
            else:
                # Hash mismatch on re-upload - this is suspicious
                logger.warning(
                    f"Duplicate chunk {chunk_index} for upload {upload_id} - "
                    f"hash mismatch! Previous: {previous_hash}, new: {chunk_sha256}"
                )
                return (False, True, "Chunk hash mismatch on re-upload")

        # Verify chunk hash
        computed_hash = hashlib.sha256(chunk_data).hexdigest()
        if computed_hash != chunk_sha256:
            error_msg = (
                f"Chunk hash mismatch for chunk {chunk_index}: "
                f"expected {chunk_sha256}, computed {computed_hash}"
            )
            logger.error(f"{upload_id}: {error_msg}")
            return (False, False, error_msg)

        # Save chunk
        chunk_path = self.get_chunk_path(upload_id, chunk_index)

        try:
            with open(chunk_path, "wb") as f:
                f.write(chunk_data)
            logger.info(f"Saved chunk {chunk_index} for upload {upload_id}")
            return (True, False, "")
        except Exception as e:
            error_msg = f"Error saving chunk {chunk_index}: {e}"
            logger.error(error_msg)
            return (False, False, error_msg)

    def get_missing_chunks(self, state: IngestionState) -> list[int]:
        """
        Get list of missing chunk indices

        Args:
            state: Current upload state

        Returns:
            List of missing chunk indices (0-based)
        """
        expected = set(range(state.expected_chunks))
        received = state.chunks_received_set
        missing = sorted(expected - received)
        return missing

    def verify_all_chunks_received(self, state: IngestionState) -> tuple[bool, list[int]]:
        """
        Verify all expected chunks have been received

        Args:
            state: Current upload state

        Returns:
            Tuple of (all_received, missing_chunks)
        """
        missing = self.get_missing_chunks(state)
        return (len(missing) == 0, missing)

    async def assemble_file(self, upload_id: UUID) -> Optional[Path]:
        """
        Assemble all chunks into final file

        Returns:
            Path to assembled file, or None if assembly failed
        """
        state = await self.load_state(upload_id)
        if not state:
            logger.error(f"Cannot assemble file: state not found for {upload_id}")
            return None

        # Update state
        state.status = "ASSEMBLING"
        await self.save_state(state)

        upload_dir = self.get_upload_dir(upload_id)
        assembled_path = upload_dir / "assembled.bin"

        try:
            with open(assembled_path, "wb") as outfile:
                for chunk_index in range(state.total_chunks):
                    chunk_path = self.get_chunk_path(upload_id, chunk_index)

                    if not chunk_path.exists():
                        logger.error(
                            f"Missing chunk {chunk_index} for upload {upload_id}"
                        )
                        state.status = "ERROR"
                        state.error_message = f"Missing chunk {chunk_index}"
                        await self.save_state(state)
                        return None

                    with open(chunk_path, "rb") as infile:
                        chunk_data = infile.read()
                        outfile.write(chunk_data)

            logger.info(f"Assembled file for upload {upload_id}")
            return assembled_path

        except Exception as e:
            logger.error(f"Error assembling file for {upload_id}: {e}")
            state.status = "ERROR"
            state.error_message = f"Assembly error: {str(e)}"
            await self.save_state(state)
            return None

    async def verify_file(self, upload_id: UUID, assembled_path: Path) -> bool:
        """
        Verify assembled file SHA256 matches expected hash

        Returns:
            True if hash matches, False otherwise
        """
        import hashlib

        state = await self.load_state(upload_id)
        if not state:
            return False

        # Update state
        state.status = "VERIFYING"
        await self.save_state(state)

        try:
            sha256_hash = hashlib.sha256()
            with open(assembled_path, "rb") as f:
                # Read in chunks to handle large files
                for chunk in iter(lambda: f.read(8192), b""):
                    sha256_hash.update(chunk)

            computed_hash = sha256_hash.hexdigest()

            if computed_hash != state.file_sha256:
                logger.error(
                    f"File hash mismatch for {upload_id}: "
                    f"expected {state.file_sha256}, got {computed_hash}"
                )
                state.status = "ERROR"
                state.error_message = "SHA256 verification failed"
                await self.save_state(state)
                return False

            logger.info(f"File verification successful for {upload_id}")
            return True

        except Exception as e:
            logger.error(f"Error verifying file for {upload_id}: {e}")
            state.status = "ERROR"
            state.error_message = f"Verification error: {str(e)}"
            await self.save_state(state)
            return False

    async def cleanup_upload(self, upload_id: UUID) -> None:
        """Remove upload directory and all contents"""
        upload_dir = self.get_upload_dir(upload_id)

        try:
            if upload_dir.exists():
                shutil.rmtree(upload_dir)
                logger.info(f"Cleaned up upload directory: {upload_dir}")
        except Exception as e:
            logger.error(f"Error cleaning up {upload_id}: {e}")

    async def cleanup_expired_uploads(self) -> int:
        """
        Clean up uploads older than timeout threshold

        Returns:
            Number of uploads cleaned up
        """
        count = 0
        cutoff_time = datetime.utcnow() - timedelta(hours=settings.UPLOAD_TIMEOUT_HOURS)

        for upload_dir in self.base_dir.iterdir():
            if not upload_dir.is_dir():
                continue

            try:
                upload_id = UUID(upload_dir.name)
                state = await self.load_state(upload_id)

                if state and state.created_at < cutoff_time:
                    if state.status not in ["UPLOADED", "READY_FOR_INDEXING"]:
                        logger.info(f"Cleaning up expired upload: {upload_id}")
                        await self.cleanup_upload(upload_id)
                        count += 1

            except ValueError:
                # Not a valid UUID directory, skip
                continue
            except Exception as e:
                logger.error(f"Error checking upload {upload_dir.name}: {e}")

        logger.info(f"Cleaned up {count} expired uploads")
        return count

    async def get_upload_stats(self, upload_id: UUID) -> Optional[dict]:
        """Get statistics about an upload"""
        state = await self.load_state(upload_id)
        if not state:
            return None

        upload_dir = self.get_upload_dir(upload_id)
        chunks_on_disk = len(list(upload_dir.glob("chunk_*.bin")))

        return {
            "upload_id": str(upload_id),
            "status": state.status,
            "total_chunks": state.total_chunks,
            "chunks_received": state.chunks_received,
            "chunks_on_disk": chunks_on_disk,
            "file_size": state.file_size,
            "created_at": state.created_at.isoformat(),
            "updated_at": state.updated_at.isoformat()
        }
