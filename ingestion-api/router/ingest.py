"""
Ingestion API Router
Handles file uploads from local agent
"""
from fastapi import APIRouter, Header, HTTPException, status, UploadFile, File
from fastapi.responses import JSONResponse
import logging
import uuid
import math

from models.requests import InitUploadRequest, CompleteUploadRequest
from models.responses import InitUploadResponse, UploadChunkResponse, CompleteUploadResponse
from utils.supabase_client import (
    create_upload_record,
    update_chunk_status,
    complete_upload,
    get_yacht_signature_info
)
from services.file_handler import (
    save_chunk,
    assemble_file,
    cleanup_temp_files,
    move_to_storage
)
from services.indexing_queue import trigger_indexing
from config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/ingest", tags=["ingestion"])


@router.post("/init", response_model=InitUploadResponse)
async def init_upload(
    request: InitUploadRequest,
    x_yacht_signature: str = Header(..., alias="X-Yacht-Signature")
):
    """
    Initialize upload session

    Called by local agent before uploading chunks
    """
    logger.info(f"Initializing upload for {request.filename} ({request.size_bytes} bytes)")

    # Validate yacht signature
    try:
        yacht_info = await get_yacht_signature_info(x_yacht_signature)
        yacht_id = yacht_info["id"]

    except Exception as e:
        logger.error(f"Invalid yacht signature: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid yacht signature"
        )

    # Validate file size
    if request.size_bytes > settings.max_file_size:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large (max {settings.max_file_size} bytes)"
        )

    # Calculate expected chunks
    expected_chunks = math.ceil(request.size_bytes / settings.max_chunk_size)

    # Create upload session
    try:
        upload_id = await create_upload_record(
            yacht_id=yacht_id,
            filename=request.filename,
            sha256=request.sha256,
            size_bytes=request.size_bytes,
            source=request.source
        )

    except Exception as e:
        logger.error(f"Failed to create upload session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initialize upload"
        )

    # Generate storage key
    storage_key = f"yachts/{yacht_id}/temp/{upload_id}/"

    response = InitUploadResponse(
        upload_id=upload_id,
        storage_key=storage_key,
        expected_chunks=expected_chunks
    )

    logger.info(f"Upload session initialized: {upload_id} ({expected_chunks} chunks)")

    return response


@router.patch("/upload_chunk", response_model=UploadChunkResponse)
async def upload_chunk(
    file: UploadFile = File(...),
    upload_id: str = Header(..., alias="Upload-ID"),
    chunk_index: int = Header(..., alias="Chunk-Index"),
    chunk_sha256: str = Header(..., alias="Chunk-SHA256"),
    x_yacht_signature: str = Header(..., alias="X-Yacht-Signature")
):
    """
    Upload a single chunk

    Called multiple times by local agent to upload file in chunks
    """
    logger.info(f"Receiving chunk {chunk_index} for upload {upload_id}")

    # Validate yacht signature
    try:
        await get_yacht_signature_info(x_yacht_signature)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid yacht signature"
        )

    # Read chunk data
    chunk_data = await file.read()

    # Validate chunk size
    if len(chunk_data) > settings.max_chunk_size:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Chunk too large (max {settings.max_chunk_size} bytes)"
        )

    # Save chunk and verify SHA256
    try:
        chunk_path, actual_sha256 = await save_chunk(
            upload_id=upload_id,
            chunk_index=chunk_index,
            chunk_data=chunk_data
        )

        # Verify chunk SHA256
        if actual_sha256 != chunk_sha256:
            logger.error(
                f"Chunk SHA256 mismatch: expected {chunk_sha256}, "
                f"got {actual_sha256}"
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Chunk SHA256 verification failed"
            )

        # Update database
        await update_chunk_status(
            upload_id=upload_id,
            chunk_index=chunk_index,
            chunk_sha256=chunk_sha256
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to save chunk: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save chunk"
        )

    return UploadChunkResponse(
        status="ok",
        chunk_index=chunk_index,
        upload_id=upload_id
    )


@router.post("/complete", response_model=CompleteUploadResponse)
async def complete_upload_session(
    request: CompleteUploadRequest,
    x_yacht_signature: str = Header(..., alias="X-Yacht-Signature")
):
    """
    Complete upload and trigger indexing

    Called by local agent after all chunks uploaded
    """
    logger.info(f"Completing upload {request.upload_id}")

    # Validate yacht signature
    try:
        yacht_info = await get_yacht_signature_info(x_yacht_signature)
        yacht_id = yacht_info["id"]

    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid yacht signature"
        )

    # Assemble file and verify SHA256
    try:
        assembled_file, verification_passed = await assemble_file(
            upload_id=request.upload_id,
            total_chunks=request.total_chunks,
            expected_sha256=request.sha256
        )

        if not verification_passed:
            await cleanup_temp_files(request.upload_id)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="SHA256 verification failed"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to assemble file: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to assemble file"
        )

    # Move to Supabase storage
    try:
        storage_path = await move_to_storage(
            assembled_file=assembled_file,
            yacht_id=yacht_id,
            filename=request.filename,
            sha256=request.sha256
        )

    except Exception as e:
        logger.error(f"Failed to move to storage: {e}")
        await cleanup_temp_files(request.upload_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload to storage"
        )

    # Create document record
    try:
        doc_info = await complete_upload(request.upload_id, yacht_id)
        document_id = doc_info["document_id"]

    except Exception as e:
        logger.error(f"Failed to create document record: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create document record"
        )

    # Trigger indexing
    queued = await trigger_indexing(
        document_id=document_id,
        yacht_id=yacht_id,
        filename=request.filename,
        storage_path=storage_path,
        sha256=request.sha256
    )

    # Cleanup temp files
    await cleanup_temp_files(request.upload_id)

    logger.info(
        f"Upload complete: document_id={document_id}, "
        f"queued_for_indexing={queued}"
    )

    return CompleteUploadResponse(
        document_id=document_id,
        status="received",
        queued_for_indexing=queued,
        storage_path=storage_path
    )
