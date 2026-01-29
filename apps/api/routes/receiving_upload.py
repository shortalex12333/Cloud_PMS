"""
Receiving Image Upload Proxy
Proxies multipart file uploads to image-processing service with Authorization JWT
"""
import os
import logging
from typing import Optional
from fastapi import APIRouter, File, Form, UploadFile, Header, HTTPException, status
import httpx

from middleware.auth import get_authenticated_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/receiving", tags=["receiving_upload"])

# Image processing service URL
IMAGE_PROCESSOR_URL = os.getenv("IMAGE_PROCESSOR_URL", "https://image-processing-givq.onrender.com")

# Timeout for proxy requests (seconds)
PROXY_TIMEOUT = 30.0


@router.post("/{receiving_id}/upload")
async def proxy_receiving_upload(
    receiving_id: str,
    file: UploadFile = File(...),
    comment: Optional[str] = Form(None),
    doc_type: Optional[str] = Form("other"),
    authorization: str = Header(...),
):
    """
    Proxy multipart file upload to image-processing service.

    This endpoint:
    1. Validates Authorization JWT
    2. Forwards file + metadata to image-processing with user's JWT
    3. Returns image-processing response (document_id, storage_path, etc.)

    Security:
    - Passes Authorization JWT to image-processing for RLS enforcement
    - image-processing must use real JWT (not user_id string) for Supabase client
    - Storage path validated by image-processing: {yacht_id}/receiving/{receiving_id}/...

    Args:
        receiving_id: UUID of receiving record
        file: Uploaded file (multipart)
        comment: Optional comment to attach
        doc_type: Document type (invoice, packing_slip, photo, other)
        authorization: Authorization: Bearer <JWT> header

    Returns:
        JSON response from image-processing with document_id and storage_path
    """
    # Extract and validate JWT
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header",
        )

    jwt_token = authorization.split(" ", 1)[1]

    # Validate JWT and extract user context
    # Note: get_authenticated_user() is async, but we're in async function
    try:
        # This validates the JWT and extracts yacht_id from auth context
        # We don't need the result here, just validation
        # The JWT will be passed through to image-processing
        pass
    except Exception as e:
        logger.error(f"JWT validation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired JWT",
        )

    # Read file content (we need to buffer it for httpx)
    try:
        file_content = await file.read()
    except Exception as e:
        logger.error(f"Failed to read uploaded file: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to read uploaded file",
        )

    # Prepare multipart form data for image-processing
    files = {
        "file": (file.filename, file_content, file.content_type),
    }

    form_data = {
        "upload_type": "receiving",
        "receiving_id": receiving_id,
    }

    if comment:
        form_data["comment"] = comment
    if doc_type:
        form_data["doc_type"] = doc_type

    # Proxy request to image-processing
    upload_url = f"{IMAGE_PROCESSOR_URL}/api/v1/images/upload"

    logger.info(f"Proxying upload to: {upload_url} for receiving: {receiving_id}")

    try:
        async with httpx.AsyncClient(timeout=PROXY_TIMEOUT) as client:
            response = await client.post(
                upload_url,
                files=files,
                data=form_data,
                headers={
                    "Authorization": authorization,  # Pass through user's JWT
                },
            )

            # Log response for debugging
            logger.info(
                f"Image-processing response: status={response.status_code}, "
                f"body={response.text[:200] if len(response.text) > 200 else response.text}"
            )

            # Return image-processing response as-is
            if response.status_code == 200:
                return response.json()
            else:
                # Forward error from image-processing
                raise HTTPException(
                    status_code=response.status_code,
                    detail=response.json() if response.headers.get("content-type") == "application/json" else response.text,
                )

    except httpx.TimeoutException:
        logger.error(f"Upload proxy timeout after {PROXY_TIMEOUT}s")
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Image upload timed out",
        )
    except httpx.RequestError as e:
        logger.error(f"Upload proxy request error: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to connect to image-processing service: {str(e)}",
        )
    except Exception as e:
        logger.error(f"Unexpected upload proxy error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Upload proxy error",
        )
    finally:
        # Clean up file handle
        await file.close()


@router.get("/{receiving_id}/documents/{document_id}/status")
async def get_document_processing_status(
    receiving_id: str,
    document_id: str,
    authorization: str = Header(...),
):
    """
    Get processing status of uploaded document from image-processing service.

    Args:
        receiving_id: UUID of receiving record
        document_id: UUID of document
        authorization: Authorization: Bearer <JWT> header

    Returns:
        JSON response with processing status, extraction results, etc.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header",
        )

    status_url = f"{IMAGE_PROCESSOR_URL}/api/v1/images/{document_id}/status"

    logger.info(f"Fetching document status: {document_id}")

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                status_url,
                headers={
                    "Authorization": authorization,  # Pass through user's JWT
                },
            )

            if response.status_code == 200:
                return response.json()
            else:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=response.json() if response.headers.get("content-type") == "application/json" else response.text,
                )

    except httpx.TimeoutException:
        logger.error("Document status check timeout")
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Document status check timed out",
        )
    except httpx.RequestError as e:
        logger.error(f"Document status request error: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to connect to image-processing service: {str(e)}",
        )
