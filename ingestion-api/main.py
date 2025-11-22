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
    - Chunk-Index: Index of this chunk (0-based)
    - Chunk-SHA256: SHA256 hash of this chunk
    - Content-Type: application/octet-stream

    This endpoint is idempotent - re-uploading the same chunk with the same
    hash will succeed without error. Re-uploading with a different hash will fail.
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
                detail="Upload session not found or expired"
            )

        # TENANT ISOLATION: Verify yacht_id matches upload owner
        if state.yacht_id != yacht_id:
            logger.warning(
                f"Tenant isolation violation: yacht {yacht_id} attempted to upload "
                f"chunk to upload {upload_id} owned by yacht {state.yacht_id}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Upload does not belong to this yacht"
            )

        # Verify upload is in valid state for receiving chunks
        if state.status not in ["INITIATED", "UPLOADING"]:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Upload is in state '{state.status}', cannot receive chunks"
            )

        # Verify chunk index is valid (0-based indexing)
        if chunk_index < 0 or chunk_index >= state.expected_chunks:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Chunk index {chunk_index} out of range [0, {state.expected_chunks - 1}]"
            )

        # Read chunk data
        chunk_data = await request.body()

        # Verify chunk is not empty
        if len(chunk_data) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Empty chunk data received"
            )

        # Verify chunk size
        if len(chunk_data) > settings.MAX_CHUNK_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"Chunk size {len(chunk_data)} exceeds maximum {settings.MAX_CHUNK_SIZE} bytes"
            )

        # Save chunk with hash verification and idempotency
        success, is_duplicate, error_msg = await storage_manager.save_chunk(
            upload_id=upload_id,
            chunk_index=chunk_index,
            chunk_data=chunk_data,
            chunk_sha256=chunk_sha256,
            state=state
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Chunk validation failed: {error_msg}"
            )

        # Update state only if not a duplicate
        if not is_duplicate:
            state.chunks_received += 1
            state.chunks_received_set.add(chunk_index)
            state.chunk_hashes[chunk_index] = chunk_sha256
            state.status = "UPLOADING"
            await storage_manager.save_state(state)

        logger.info(
            f"Received chunk {chunk_index + 1}/{state.expected_chunks} "
            f"for upload {upload_id} (duplicate={is_duplicate})"
        )

        return UploadChunkResponse(
            status="ok",
            message="Chunk received" if not is_duplicate else "Chunk already received (idempotent)"
        )

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
    1. Verifies expected_chunks matches what was set at init
    2. Verifies all chunks are present (using chunk tracking set)
    3. Assembles chunks into final file
    4. Verifies final SHA256 matches
    5. Uploads to Supabase Storage (tenant-isolated path)
    6. Creates document record in database
    7. Queues for indexing (n8n or stub queue)
    8. Cleans up temporary files
    """
    upload_id = request.upload_id

    try:
        # Load upload state
        state = await storage_manager.load_state(upload_id)
        if not state:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Upload session not found or expired"
            )

        # TENANT ISOLATION: Verify yacht_id matches upload owner
        if state.yacht_id != yacht_id:
            logger.warning(
                f"Tenant isolation violation: yacht {yacht_id} attempted to complete "
                f"upload {upload_id} owned by yacht {state.yacht_id}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Upload does not belong to this yacht"
            )

        # Verify upload is in valid state for completion
        if state.status not in ["INITIATED", "UPLOADING"]:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Upload is in state '{state.status}', cannot complete"
            )

        # INTEGRITY CHECK 1: Verify total_chunks matches expected_chunks from init
        if request.total_chunks != state.expected_chunks:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"total_chunks mismatch: request says {request.total_chunks}, "
                       f"init expected {state.expected_chunks}"
            )

        # INTEGRITY CHECK 2: Verify all chunks received using chunk tracking set
        all_received, missing_chunks = storage_manager.verify_all_chunks_received(state)
        if not all_received:
            missing_preview = missing_chunks[:10]  # Show first 10 missing
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Missing {len(missing_chunks)} chunks. Missing indices: {missing_preview}"
                       + ("..." if len(missing_chunks) > 10 else "")
            )

        # INTEGRITY CHECK 3: Verify SHA256 from request matches init
        if state.file_sha256 != request.sha256:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"SHA256 mismatch: init={state.file_sha256[:16]}..., "
                       f"complete={request.sha256[:16]}..."
            )

        # INTEGRITY CHECK 4: Verify filename matches
        if state.filename != request.filename:
            logger.warning(
                f"Filename changed between init and complete: "
                f"init='{state.filename}', complete='{request.filename}'"
            )
            # Allow this but log it - could be intentional rename

        logger.info(
            f"Completing upload {upload_id}: {state.chunks_received} chunks, "
            f"{state.file_size} bytes, sha256={state.file_sha256[:16]}..."
        )

        # Assemble file from chunks
        assembled_path = await storage_manager.assemble_file(upload_id)
        if not assembled_path:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to assemble file from chunks"
            )

        # INTEGRITY CHECK 5: Verify assembled file SHA256 matches expected
        verified = await storage_manager.verify_file(upload_id, assembled_path)
        if not verified:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Assembled file SHA256 verification failed - data corruption detected"
            )

        # Update state
        state.status = "UPLOADED"
        await storage_manager.save_state(state)

        # Detect content type
        content_type, _ = mimetypes.guess_type(state.filename)

        # Upload to Supabase Storage (tenant-isolated path)
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
                "document_id": str(document_id),
                "chunks_received": state.chunks_received,
                "file_size": state.file_size
            }
        )

        # QUEUE FOR INDEXING: Try n8n, fallback to stub queue with logging
        triggered = await n8n_trigger.trigger_indexing(
            document_id=document_id,
            yacht_id=yacht_id,
            file_sha256=state.file_sha256,
            storage_path=storage_path,
            filename=state.filename,
            file_size=state.file_size
        )

        if not triggered:
            # Stub queue fallback: log the job for manual/later processing
            logger.warning(
                f"STUB_QUEUE: Failed to trigger n8n indexing for document {document_id}. "
                f"Logging for manual processing. yacht_id={yacht_id}, "
                f"storage_path={storage_path}, filename={state.filename}"
            )
            # Log to stub queue table (document is still saved, just not indexed yet)
            await supabase_manager.log_ingestion_event(
                yacht_id=yacht_id,
                upload_id=upload_id,
                document_id=document_id,
                event_type="indexing_queued",
                status="stub_queue",
                metadata={
                    "reason": "n8n_trigger_failed",
                    "storage_path": storage_path,
                    "filename": state.filename
                }
            )

        # Clean up temporary files
        await storage_manager.cleanup_upload(upload_id)

        logger.info(
            f"Successfully completed upload {upload_id}, "
            f"created document {document_id}, queued_for_indexing={triggered}"
        )

        return IngestionCompleteResponse(
            document_id=document_id,
            status="received",
            queued_for_indexing=triggered,
            message="Document stored and queued for indexing" if triggered
                    else "Document stored, indexing pending (stub queue)"
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


# ==================== STATUS ENDPOINTS ====================


@app.get("/v1/ingest/status/{upload_id}")
async def get_upload_status(
    upload_id: UUID,
    yacht_id: UUID = Depends(yacht_auth.validate_yacht_signature)
):
    """
    Get the status of an upload session

    Returns chunk progress, status, and any error messages.
    Useful for resuming uploads after connection issues.
    """
    try:
        state = await storage_manager.load_state(upload_id)
        if not state:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Upload session not found or expired"
            )

        # TENANT ISOLATION: Verify yacht_id matches
        if state.yacht_id != yacht_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Upload does not belong to this yacht"
            )

        # Get missing chunks for resume capability
        missing_chunks = storage_manager.get_missing_chunks(state)

        return {
            "upload_id": str(upload_id),
            "status": state.status,
            "filename": state.filename,
            "file_size": state.file_size,
            "expected_chunks": state.expected_chunks,
            "chunks_received": state.chunks_received,
            "chunks_missing": len(missing_chunks),
            "missing_chunk_indices": missing_chunks[:50],  # First 50 for debugging
            "created_at": state.created_at.isoformat(),
            "updated_at": state.updated_at.isoformat(),
            "error_message": state.error_message
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting upload status: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error getting upload status"
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
        logger.info(f"Starting indexing for document {document_id}, yacht {yacht_id}")

        # Fetch document from database to get storage_path and other metadata
        result = supabase_manager.client.table("documents").select("*").eq(
            "id", str(document_id)
        ).eq(
            "yacht_id", str(yacht_id)  # Tenant isolation
        ).execute()

        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found or does not belong to yacht"
            )

        doc = result.data[0]

        # Trigger n8n indexing
        triggered = await n8n_trigger.trigger_indexing(
            document_id=document_id,
            yacht_id=yacht_id,
            file_sha256=doc.get("sha256", ""),
            storage_path=doc.get("storage_path", ""),
            filename=doc.get("filename", ""),
            file_size=doc.get("size_bytes", 0)
        )

        if triggered:
            return {"status": "started", "document_id": str(document_id)}
        else:
            return {"status": "queued_stub", "document_id": str(document_id)}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting indexing: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error starting indexing"
        )


@app.post("/internal/indexer/retry_failed")
async def retry_failed_indexing():
    """
    Retry indexing for all documents in stub queue

    Fetches documents that failed to trigger n8n and retries them.
    Called by cron scheduler or manually.
    """
    try:
        # Find documents that are ready for indexing but not indexed
        result = supabase_manager.client.table("documents").select(
            "id, yacht_id, sha256, storage_path, filename, size_bytes"
        ).eq(
            "indexed", False
        ).eq(
            "status", "ready_for_indexing"
        ).limit(50).execute()

        if not result.data:
            return {"status": "ok", "retried": 0, "message": "No pending documents"}

        retried = 0
        failed = 0

        for doc in result.data:
            try:
                triggered = await n8n_trigger.trigger_indexing(
                    document_id=UUID(doc["id"]),
                    yacht_id=UUID(doc["yacht_id"]),
                    file_sha256=doc.get("sha256", ""),
                    storage_path=doc.get("storage_path", ""),
                    filename=doc.get("filename", ""),
                    file_size=doc.get("size_bytes", 0)
                )

                if triggered:
                    retried += 1
                    logger.info(f"Successfully retried indexing for document {doc['id']}")
                else:
                    failed += 1

            except Exception as e:
                logger.error(f"Error retrying document {doc['id']}: {e}")
                failed += 1

        return {
            "status": "ok",
            "retried": retried,
            "failed": failed,
            "total_pending": len(result.data)
        }

    except Exception as e:
        logger.error(f"Error in retry_failed_indexing: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrying failed indexing"
        )


@app.get("/internal/stub_queue/list")
async def list_stub_queue(limit: int = 50):
    """
    List documents in the stub indexing queue

    Returns documents that are stored but not yet indexed.
    """
    try:
        result = supabase_manager.client.table("documents").select(
            "id, yacht_id, filename, storage_path, size_bytes, created_at, status"
        ).eq(
            "indexed", False
        ).order(
            "created_at", desc=True
        ).limit(limit).execute()

        return {
            "status": "ok",
            "count": len(result.data) if result.data else 0,
            "documents": result.data or []
        }

    except Exception as e:
        logger.error(f"Error listing stub queue: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error listing stub queue"
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
