"""
File handling service for ingestion
"""
import hashlib
import aiofiles
from pathlib import Path
import logging
from config import settings

logger = logging.getLogger(__name__)


async def save_chunk(
    upload_id: str,
    chunk_index: int,
    chunk_data: bytes
) -> tuple[str, str]:
    """
    Save uploaded chunk to temp directory

    Returns: (filepath, sha256)
    """
    # Create upload directory
    upload_dir = Path(settings.upload_temp_dir) / upload_id
    upload_dir.mkdir(parents=True, exist_ok=True)

    # Save chunk
    chunk_path = upload_dir / f"chunk_{chunk_index:04d}.bin"

    async with aiofiles.open(chunk_path, 'wb') as f:
        await f.write(chunk_data)

    # Calculate SHA256
    sha256 = hashlib.sha256(chunk_data).hexdigest()

    logger.info(f"Saved chunk {chunk_index} for upload {upload_id}: {len(chunk_data)} bytes")

    return str(chunk_path), sha256


async def assemble_file(
    upload_id: str,
    total_chunks: int,
    expected_sha256: str
) -> tuple[Path, bool]:
    """
    Assemble chunks into final file and verify SHA256

    Returns: (assembled_file_path, verification_passed)
    """
    upload_dir = Path(settings.upload_temp_dir) / upload_id
    output_file = upload_dir / "assembled_file"

    logger.info(f"Assembling {total_chunks} chunks for upload {upload_id}")

    # Assemble chunks in order
    hasher = hashlib.sha256()

    async with aiofiles.open(output_file, 'wb') as outfile:
        for i in range(total_chunks):
            chunk_path = upload_dir / f"chunk_{i:04d}.bin"

            if not chunk_path.exists():
                logger.error(f"Missing chunk {i} for upload {upload_id}")
                return output_file, False

            async with aiofiles.open(chunk_path, 'rb') as infile:
                chunk_data = await infile.read()
                await outfile.write(chunk_data)
                hasher.update(chunk_data)

    # Verify SHA256
    actual_sha256 = hasher.hexdigest()
    verification_passed = (actual_sha256 == expected_sha256)

    if verification_passed:
        logger.info(f"SHA256 verification PASSED for upload {upload_id}")
    else:
        logger.error(
            f"SHA256 verification FAILED for upload {upload_id}: "
            f"expected {expected_sha256}, got {actual_sha256}"
        )

    return output_file, verification_passed


async def cleanup_temp_files(upload_id: str) -> None:
    """Remove temporary upload directory"""
    import shutil

    upload_dir = Path(settings.upload_temp_dir) / upload_id

    if upload_dir.exists():
        shutil.rmtree(upload_dir)
        logger.info(f"Cleaned up temp files for upload {upload_id}")


async def move_to_storage(
    assembled_file: Path,
    yacht_id: str,
    filename: str,
    sha256: str
) -> str:
    """
    Move assembled file to Supabase storage

    Returns: storage_path
    """
    from utils.supabase_client import get_supabase_client

    client = get_supabase_client()

    # Construct storage path
    storage_path = f"yachts/{yacht_id}/raw/{sha256}/{filename}"

    logger.info(f"Uploading to Supabase storage: {storage_path}")

    # Read file
    async with aiofiles.open(assembled_file, 'rb') as f:
        file_data = await f.read()

    # Upload to Supabase storage
    try:
        client.storage.from_("documents").upload(
            path=storage_path,
            file=file_data,
            file_options={"content-type": "application/octet-stream"}
        )

        logger.info(f"Successfully uploaded to storage: {storage_path}")
        return storage_path

    except Exception as e:
        logger.error(f"Failed to upload to storage: {e}")
        raise
