"""
Document Processing Security Layer
Military-Grade Security for High-Value Targets

Features:
- Yacht signature authentication (HMAC-SHA256)
- File size limits (prevent DoS)
- Content type validation (prevent malware)
- Rate limiting (per yacht + global)
- Audit logging (forensic trails)
- Input sanitization
"""

import os
import hashlib
import logging
from typing import Optional, Dict, Any
from fastapi import Header, HTTPException, UploadFile
from datetime import datetime

logger = logging.getLogger(__name__)

# Security configuration
MAX_FILE_SIZE = 500 * 1024 * 1024  # 500 MB max per file
YACHT_SALT = os.getenv("YACHT_SALT", "")

# Allowed content types (whitelist approach)
ALLOWED_CONTENT_TYPES = {
    # Documents
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # .docx
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",  # .xlsx
    "application/vnd.ms-excel",  # .xls
    "application/msword",  # .doc
    "text/plain",
    "text/csv",
    "application/json",
    "application/xml",
    "text/xml",
    "text/html",
    # Images
    "image/jpeg",
    "image/png",
    "image/gif",
    "image/webp",
    "image/svg+xml",
    # Archives (for batch uploads)
    "application/zip",
    "application/x-tar",
    "application/gzip",
}

# Rate limit configuration (stricter than general API)
DOCUMENT_RATE_LIMITS = {
    "upload_per_yacht": ["10/minute", "50/hour", "200/day"],  # Per yacht limits
    "upload_global": ["100/minute", "500/hour"],  # Global limit
    "index_per_yacht": ["20/minute", "100/hour"],
}


def verify_yacht_signature(
    yacht_id: str,
    x_yacht_signature: Optional[str] = None
) -> bool:
    """
    Verify yacht signature using HMAC-SHA256

    Signature = sha256(yacht_id + salt)

    Args:
        yacht_id: UUID of yacht
        x_yacht_signature: Signature from X-Yacht-Signature header

    Returns:
        True if signature valid, raises HTTPException if invalid
    """
    if not YACHT_SALT:
        # If no salt configured, skip verification (development mode)
        logger.warning("YACHT_SALT not configured - signature verification disabled")
        return True

    if not x_yacht_signature:
        logger.error(f"Missing yacht signature for yacht {yacht_id}")
        raise HTTPException(
            status_code=401,
            detail="Missing X-Yacht-Signature header"
        )

    # Calculate expected signature
    expected_signature = hashlib.sha256(
        f"{yacht_id}{YACHT_SALT}".encode()
    ).hexdigest()

    if x_yacht_signature != expected_signature:
        logger.error(
            f"Invalid yacht signature for {yacht_id}. "
            f"Expected: {expected_signature[:8]}..., Got: {x_yacht_signature[:8]}..."
        )
        raise HTTPException(
            status_code=403,
            detail="Invalid yacht signature"
        )

    logger.info(f"Yacht signature verified for {yacht_id}")
    return True


def validate_file_upload(
    file: UploadFile,
    max_size: int = MAX_FILE_SIZE,
    allowed_types: set = ALLOWED_CONTENT_TYPES
) -> Dict[str, Any]:
    """
    Validate uploaded file for security

    Checks:
    - File size (prevent DoS)
    - Content type (prevent malware)
    - Filename sanitization (prevent path traversal)

    Args:
        file: Uploaded file
        max_size: Maximum allowed file size in bytes
        allowed_types: Set of allowed MIME types

    Returns:
        Dict with validation results

    Raises:
        HTTPException if validation fails
    """
    # Check content type
    if file.content_type not in allowed_types:
        logger.error(
            f"Blocked upload with disallowed content type: {file.content_type} "
            f"(filename: {file.filename})"
        )
        raise HTTPException(
            status_code=415,
            detail=f"Content type not allowed: {file.content_type}. "
                   f"Allowed types: {', '.join(sorted(allowed_types))}"
        )

    # Sanitize filename (prevent path traversal)
    filename = os.path.basename(file.filename)
    if filename != file.filename:
        logger.warning(
            f"Filename contained path separators, sanitized: "
            f"{file.filename} -> {filename}"
        )

    # Check for suspicious filenames
    dangerous_extensions = {'.exe', '.bat', '.sh', '.cmd', '.com', '.scr', '.vbs'}
    file_ext = os.path.splitext(filename)[1].lower()
    if file_ext in dangerous_extensions:
        logger.error(f"Blocked upload with dangerous extension: {file_ext} ({filename})")
        raise HTTPException(
            status_code=415,
            detail=f"File extension not allowed: {file_ext}"
        )

    return {
        "filename": filename,
        "content_type": file.content_type,
        "validated": True
    }


def validate_file_size(
    file_content: bytes,
    max_size: int = MAX_FILE_SIZE,
    filename: str = "unknown"
) -> bool:
    """
    Validate file size after reading

    Args:
        file_content: File bytes
        max_size: Maximum allowed size
        filename: Filename for logging

    Returns:
        True if valid

    Raises:
        HTTPException if too large
    """
    actual_size = len(file_content)

    if actual_size > max_size:
        logger.error(
            f"File too large: {filename} ({actual_size:,} bytes, "
            f"max: {max_size:,} bytes)"
        )
        raise HTTPException(
            status_code=413,
            detail=f"File too large: {actual_size:,} bytes. "
                   f"Maximum allowed: {max_size:,} bytes ({max_size // (1024*1024)} MB)"
        )

    logger.info(f"File size validated: {filename} ({actual_size:,} bytes)")
    return True


def sanitize_metadata(metadata: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sanitize metadata to prevent injection attacks

    Args:
        metadata: Metadata dictionary

    Returns:
        Sanitized metadata
    """
    sanitized = metadata.copy()

    # Sanitize string fields
    string_fields = ['filename', 'system_path', 'doc_type', 'system_tag', 'local_path']
    for field in string_fields:
        if field in sanitized and isinstance(sanitized[field], str):
            # Remove null bytes (can break SQL/file operations)
            sanitized[field] = sanitized[field].replace('\x00', '')

            # Limit length to prevent buffer overflow
            if len(sanitized[field]) > 500:
                logger.warning(f"Truncated long {field}: {len(sanitized[field])} chars")
                sanitized[field] = sanitized[field][:500]

    # Validate yacht_id format (must be UUID)
    if 'yacht_id' in sanitized:
        yacht_id = sanitized['yacht_id']
        if not isinstance(yacht_id, str) or len(yacht_id) != 36:
            logger.error(f"Invalid yacht_id format: {yacht_id}")
            raise HTTPException(
                status_code=400,
                detail="Invalid yacht_id format (must be UUID)"
            )

    return sanitized


def log_document_operation(
    operation: str,
    yacht_id: str,
    filename: str,
    status: str,
    client_ip: str,
    request_id: str,
    file_size: Optional[int] = None,
    document_id: Optional[str] = None,
    error: Optional[str] = None
):
    """
    Log document operation for audit trail

    Args:
        operation: Operation type (upload, index, delete)
        yacht_id: Yacht UUID
        filename: Document filename
        status: success, failed, duplicate
        client_ip: Client IP address
        request_id: Request tracking ID
        file_size: File size in bytes
        document_id: Document UUID (if created)
        error: Error message (if failed)
    """
    log_entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "operation": operation,
        "yacht_id": yacht_id,
        "filename": filename,
        "status": status,
        "client_ip": client_ip,
        "request_id": request_id,
    }

    if file_size:
        log_entry["file_size"] = file_size
    if document_id:
        log_entry["document_id"] = document_id
    if error:
        log_entry["error"] = error

    if status == "success":
        logger.info(f"DOCUMENT_AUDIT: {operation.upper()}", extra=log_entry)
    elif status == "duplicate":
        logger.info(f"DOCUMENT_DUPLICATE: {operation.upper()}", extra=log_entry)
    else:
        logger.error(f"DOCUMENT_FAILED: {operation.upper()}", extra=log_entry)


def get_rate_limit_key(yacht_id: str, operation: str) -> str:
    """
    Generate rate limit key for yacht-specific limits

    Args:
        yacht_id: Yacht UUID
        operation: Operation type

    Returns:
        Rate limit key
    """
    return f"yacht:{yacht_id}:{operation}"
