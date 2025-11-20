"""
CelesteOS Cloud Ingestion API

Main FastAPI application for receiving file uploads from Local Agent
"""
import logging
import mimetypes
from uuid import UUID, uuid4
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, status, Depends, Request, Header
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from config import settings
from models import (
    IngestionInitRequest,
    IngestionInitResponse,
    UploadChunkResponse,
    IngestionCompleteRequest,
    IngestionCompleteResponse
)
from auth import YachtAuth, check_file_extension, sanitize_filename
from storage import TempStorageManager
from supabase_client import SupabaseManager
from n8n_trigger import N8NTrigger

# Configure logging
logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Initialize managers
storage_manager = TempStorageManager()
supabase_manager = SupabaseManager()
n8n_trigger = N8NTrigger()
yacht_auth = YachtAuth(supabase_manager.client)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    logger.info("Starting CelesteOS Ingestion API")
    logger.info(f"Temp storage directory: {settings.TEMP_UPLOAD_DIR}")

    # Startup: Clean expired uploads
    try:
        count = await storage_manager.cleanup_expired_uploads()
        logger.info(f"Cleaned up {count} expired uploads on startup")
    except Exception as e:
        logger.error(f"Error cleaning up expired uploads: {e}")

    yield

    # Shutdown
    logger.info("Shutting down CelesteOS Ingestion API")


# Create FastAPI app
app = FastAPI(
    title="CelesteOS Ingestion API",
    description="Cloud ingestion service for CelesteOS document processing",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"}
    )


# ==================== ENDPOINTS ====================


@app.get("/v1/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "ok",
        "service": "celesteos-ingestion-api",
        "version": "1.0.0"
    }


@app.post("/v1/ingest/init", response_model=IngestionInitResponse)
async def ingest_init(
    request: IngestionInitRequest,
    yacht_id: UUID = Depends(yacht_auth.validate_yacht_signature)
):
    """
    Initialize a new file upload session

    Creates upload_id, allocates temp storage, and returns expected chunk count
    """
    try:
        # Check file extension
        if not check_file_extension(request.filename):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File type not allowed: {request.filename}"
            )

        # Check for duplicate document
        existing = await supabase_manager.check_duplicate_document(
            yacht_id, request.sha256
        )
        if existing:
            logger.info(
                f"Duplicate document detected: {request.sha256} for yacht {yacht_id}"
            )
            # Return existing document info (could be configured differently)
            # For now, allow re-upload

        # Rate limiting check
        upload_count = await supabase_manager.get_yacht_upload_count(
            yacht_id, minutes=60
        )
        if upload_count >= settings.RATE_LIMIT_PER_YACHT_HOUR:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded"
            )

        # Calculate expected chunks (32MB chunks)
        chunk_size = 33554432  # 32MB
        expected_chunks = (request.size_bytes + chunk_size - 1) // chunk_size

        # Generate upload_id
        upload_id = uuid4()

        # Initialize storage
        state = await storage_manager.init_upload(
            upload_id=upload_id,
            yacht_id=yacht_id,
            filename=sanitize_filename(request.filename),
            file_sha256=request.sha256,
            file_size=request.size_bytes,
            total_chunks=expected_chunks,
            source=request.source
        )

        # Log event
        await supabase_manager.log_ingestion_event(
            yacht_id=yacht_id,
            upload_id=upload_id,
            document_id=None,
            event_type="init",
            status="initiated",
            metadata={
                "filename": request.filename,
                "size_bytes": request.size_bytes,
                "expected_chunks": expected_chunks
            }
        )

        logger.info(
            f"Initialized upload {upload_id} for yacht {yacht_id}: "
            f"{request.filename} ({request.size_bytes} bytes, {expected_chunks} chunks)"
        )

        return IngestionInitResponse(
            upload_id=upload_id,
            storage_key=f"yachts/{yacht_id}/temp/{upload_id}/",
            expected_chunks=expected_chunks,
            status="pending"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in ingest_init: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error initializing upload"
        )


@app.patch("/v1/ingest/upload_chunk", response_model=UploadChunkResponse)
async def upload_chunk(
    request: Request,
    yacht_id: UUID = Depends(yacht_auth.validate_yacht_signature),
    upload_headers: dict = Depends(yacht_auth.validate_upload_headers)
):
    """
    Upload a single chunk of a document

    Headers required:
    - Upload-ID: UUID of upload session
    - Chunk-Index: Index of this chunk
    - Chunk-SHA256: SHA256 hash of this chunk
    - Content-Type: application/octet-stream
    """
    upload_id = upload_headers["upload_id"]
    chunk_index = upload_headers["chunk_index"]
    chunk_sha256 = upload_headers["chunk_sha256"]

    try:
        # Load upload state
        state = await storage_manager.load_state(upload_id)
        if not state:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Upload session not found"
            )

        # Verify yacht_id matches
        if state.yacht_id != yacht_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Upload does not belong to this yacht"
            )

        # Verify chunk index is valid
        if chunk_index >= state.total_chunks:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Chunk index {chunk_index} exceeds total chunks {state.total_chunks}"
            )

        # Read chunk data
        chunk_data = await request.body()

        # Verify chunk size
        if len(chunk_data) > settings.MAX_CHUNK_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"Chunk size exceeds maximum {settings.MAX_CHUNK_SIZE} bytes"
            )

        # Save chunk
        success = await storage_manager.save_chunk(
            upload_id=upload_id,
            chunk_index=chunk_index,
            chunk_data=chunk_data,
            chunk_sha256=chunk_sha256
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Chunk hash verification failed"
            )

        # Update state
        state.chunks_received += 1
        state.status = "UPLOADING"
        await storage_manager.save_state(state)

        logger.info(
            f"Received chunk {chunk_index}/{state.total_chunks} "
            f"for upload {upload_id}"
        )

        return UploadChunkResponse(status="ok")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in upload_chunk: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error uploading chunk"
        )


@app.post("/v1/ingest/complete", response_model=IngestionCompleteResponse)
async def ingest_complete(
    request: IngestionCompleteRequest,
    yacht_id: UUID = Depends(yacht_auth.validate_yacht_signature)
):
    """
    Complete upload, assemble file, verify, upload to storage, and trigger indexing

    This endpoint:
    1. Verifies all chunks are present
    2. Assembles chunks into final file
    3. Verifies final SHA256
    4. Uploads to Supabase Storage
    5. Creates document record in database
    6. Triggers n8n indexing workflow
    7. Cleans up temporary files
    """
    upload_id = request.upload_id

    try:
        # Load upload state
        state = await storage_manager.load_state(upload_id)
        if not state:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Upload session not found"
            )

        # Verify yacht_id matches
        if state.yacht_id != yacht_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Upload does not belong to this yacht"
            )

        # Verify all chunks received
        if state.chunks_received != request.total_chunks:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Missing chunks: received {state.chunks_received}, expected {request.total_chunks}"
            )

        # Verify SHA256 matches
        if state.file_sha256 != request.sha256:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="SHA256 mismatch"
            )

        logger.info(f"Completing upload {upload_id}")

        # Assemble file
        assembled_path = await storage_manager.assemble_file(upload_id)
        if not assembled_path:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to assemble file"
            )

        # Verify assembled file
        verified = await storage_manager.verify_file(upload_id, assembled_path)
        if not verified:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File verification failed"
            )

        # Update state
        state.status = "UPLOADED"
        await storage_manager.save_state(state)

        # Detect content type
        content_type, _ = mimetypes.guess_type(state.filename)

        # Upload to Supabase Storage
        storage_path = await supabase_manager.upload_to_storage(
            yacht_id=yacht_id,
            file_sha256=state.file_sha256,
            filename=state.filename,
            file_path=assembled_path
        )

        # Create document record
        document_id = await supabase_manager.create_document_record(
            state=state,
            storage_path=storage_path,
            content_type=content_type
        )

        # Update state
        state.status = "READY_FOR_INDEXING"
        await storage_manager.save_state(state)

        # Log completion event
        await supabase_manager.log_ingestion_event(
            yacht_id=yacht_id,
            upload_id=upload_id,
            document_id=document_id,
            event_type="complete",
            status="completed",
            metadata={
                "storage_path": storage_path,
                "document_id": str(document_id)
            }
        )

        # Trigger n8n indexing workflow
        triggered = await n8n_trigger.trigger_indexing(
            document_id=document_id,
            yacht_id=yacht_id,
            file_sha256=state.file_sha256,
            storage_path=storage_path,
            filename=state.filename,
            file_size=state.file_size
        )

        if not triggered:
            logger.warning(
                f"Failed to trigger indexing for document {document_id}, "
                "but document is saved"
            )

        # Clean up temporary files
        await storage_manager.cleanup_upload(upload_id)

        logger.info(
            f"Successfully completed upload {upload_id}, "
            f"created document {document_id}"
        )

        return IngestionCompleteResponse(
            document_id=document_id,
            status="received",
            queued_for_indexing=triggered
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in ingest_complete: {e}", exc_info=True)

        # Log error event
        try:
            await supabase_manager.log_ingestion_event(
                yacht_id=yacht_id,
                upload_id=upload_id,
                document_id=None,
                event_type="complete",
                status="error",
                error_message=str(e)
            )
        except:
            pass

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error completing upload"
        )


# ==================== INTERNAL ENDPOINTS ====================


@app.post("/internal/indexer/start")
async def start_indexing(
    document_id: UUID,
    yacht_id: UUID
):
    """
    Internal endpoint to start indexing for a document
    Called by n8n or internal scheduler
    """
    try:
        # Trigger indexing
        # This could fetch document from database and trigger processing
        logger.info(f"Starting indexing for document {document_id}")

        return {"status": "started", "document_id": str(document_id)}

    except Exception as e:
        logger.error(f"Error starting indexing: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error starting indexing"
        )


@app.post("/internal/cron/cleanup_uploads")
async def cleanup_expired_uploads():
    """
    Internal cron endpoint to clean up expired uploads
    Should be called periodically by scheduler
    """
    try:
        count = await storage_manager.cleanup_expired_uploads()
        logger.info(f"Cleaned up {count} expired uploads")

        return {
            "status": "ok",
            "cleaned_up": count
        }

    except Exception as e:
        logger.error(f"Error cleaning up uploads: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error cleaning up uploads"
        )


# ==================== MAIN ====================


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        workers=settings.API_WORKERS if not settings.DEBUG else 1,
        reload=settings.DEBUG,
        log_level="info" if not settings.DEBUG else "debug"
    )
