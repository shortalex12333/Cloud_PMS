"""
CelesteOS API - Secure Document Handlers
=========================================

Secured document handlers with yacht prefix validation for storage signing.

Security invariants (per 02_INVARIANTS_DO_NOT_BREAK.md):
1. Key format is {yacht_id}/... for all storage paths
2. Validate prefix BEFORE creating signed URLs
3. Only accept document_id (never raw path from client)
4. Server-side lookup: SELECT path, yacht_id FROM documents WHERE id=:id AND yacht_id=:ctx.yacht_id
5. Deny with 404 on miss (not 403 to prevent enumeration)
6. Never cache signed URLs beyond their lifetime

Usage:
    from handlers.secure_document_handlers import (
        get_secure_download_url,
        get_secure_upload_url,
        validate_storage_path,
    )
"""

from typing import Dict, Any, Optional
import logging

from middleware.action_security import (
    secure_action,
    ActionContext,
    OwnershipValidationError,
    ActionSecurityError,
    build_audit_entry,
)

logger = logging.getLogger(__name__)


# ============================================================================
# Path Validation
# ============================================================================

class StoragePathError(ActionSecurityError):
    """Raised when storage path validation fails."""
    def __init__(self, message: str = "Invalid storage path"):
        super().__init__(
            code="INVALID_PATH",
            message=message,
            status_code=400,
        )


def validate_storage_path(path: str, yacht_id: str) -> bool:
    """
    Validate that storage path has correct yacht prefix.

    Security invariants:
    - All storage paths MUST start with {yacht_id}/
    - No path traversal (..) allowed
    - No URL-encoded traversal attempts
    - No leading whitespace (prefix must be at start)

    Args:
        path: Storage path to validate
        yacht_id: Expected yacht ID

    Returns:
        True if valid, False otherwise
    """
    if not path:
        return False
    if not yacht_id:
        return False

    # No leading whitespace (prefix must be at exact start)
    if path != path.lstrip():
        return False

    # Block path traversal attempts (raw and URL-encoded)
    traversal_patterns = [
        "..",           # Standard traversal
        "%2e%2e",       # URL-encoded ..
        "%2E%2E",       # URL-encoded .. (uppercase)
        "%252e",        # Double-encoded
    ]
    path_lower = path.lower()
    for pattern in traversal_patterns:
        if pattern.lower() in path_lower:
            return False

    # Path must start with yacht_id/
    expected_prefix = f"{yacht_id}/"
    return path.startswith(expected_prefix)


def extract_yacht_from_path(path: str) -> Optional[str]:
    """
    Extract yacht_id from storage path.

    Args:
        path: Storage path like "yacht_id/documents/file.pdf"

    Returns:
        Yacht ID or None if invalid
    """
    if not path:
        return None

    parts = path.split("/", 1)
    if len(parts) < 2:
        return None

    return parts[0]


# ============================================================================
# Document Lookup
# ============================================================================

async def lookup_document_by_id(
    db_client,
    document_id: str,
    yacht_id: str,
) -> Optional[Dict[str, Any]]:
    """
    Server-side lookup of document by ID with yacht scoping.

    Args:
        db_client: Supabase client
        document_id: Document UUID
        yacht_id: Context yacht ID (from ActionContext)

    Returns:
        Document metadata dict or None if not found/not owned
    """
    try:
        result = db_client.table("doc_metadata").select(
            "id, filename, storage_path, content_type, yacht_id, created_at"
        ).eq("id", document_id).eq("yacht_id", yacht_id).single().execute()

        if not result.data:
            return None

        return result.data

    except Exception as e:
        logger.warning(f"[SecureDoc] Lookup failed: {e}")
        return None


# ============================================================================
# Secured Handlers
# ============================================================================

@secure_action(
    action_id="get_secure_download_url",
    action_group="READ",
    required_roles=["crew", "chief_engineer", "chief_officer", "captain", "manager", "hod"],
    validate_entities=["document_id"],
    entity_type_mapping={"document_id": "doc_metadata"},
)
async def get_secure_download_url(
    ctx: ActionContext,
    document_id: str,
    expires_in: int = 3600,
    **params
) -> Dict[str, Any]:
    """
    Generate secure download URL for a document.

    Security checks:
    1. @secure_action validates JWT, membership, role, yacht freeze
    2. Ownership validation ensures document belongs to ctx.yacht_id
    3. Path prefix validation confirms {yacht_id}/ prefix
    4. Audit logging for all access attempts

    Args:
        ctx: ActionContext (validated by decorator)
        document_id: Document UUID (only parameter from client)
        expires_in: URL expiry in seconds (max 3600)

    Returns:
        {
            "signed_url": "https://...",
            "expires_in": 3600,
            "filename": "document.pdf",
            "content_type": "application/pdf"
        }

    Raises:
        OwnershipValidationError (404): Document not found or not owned
        StoragePathError (400): Invalid storage path
    """
    db_client = params.get('_db_client')
    if not db_client:
        raise ActionSecurityError("DB_ERROR", "Database client not available", 500)

    # Server-side lookup (never trust client-provided path)
    doc = await lookup_document_by_id(db_client, document_id, ctx.yacht_id)

    if not doc:
        # Return 404 to prevent enumeration
        logger.warning(
            f"[SecureDoc] Document not found: id={document_id[:8]}..., "
            f"yacht={ctx.yacht_id[:8]}..."
        )
        raise OwnershipValidationError("document", document_id)

    # Validate storage path prefix
    storage_path = doc.get("storage_path")
    if not validate_storage_path(storage_path, ctx.yacht_id):
        logger.error(
            f"[SecureDoc] SECURITY: Invalid path prefix: path={storage_path}, "
            f"expected_prefix={ctx.yacht_id}/"
        )
        # Still return 404 to prevent enumeration
        raise OwnershipValidationError("document", document_id)

    # Enforce max expiry (never cache beyond lifetime)
    safe_expires = min(expires_in, 3600)  # Max 1 hour

    # Generate signed URL
    try:
        signed_url = await _generate_signed_download_url(
            db_client,
            storage_path,
            safe_expires,
        )
    except Exception as e:
        logger.error(f"[SecureDoc] URL generation failed: {e}")
        raise ActionSecurityError("URL_ERROR", "Failed to generate URL", 500)

    logger.info(
        f"[SecureDoc] Download URL generated: user={ctx.user_id[:8]}..., "
        f"doc={document_id[:8]}..., expires_in={safe_expires}"
    )

    return {
        "signed_url": signed_url,
        "expires_in": safe_expires,
        "filename": doc.get("filename"),
        "content_type": doc.get("content_type"),
        "document_id": document_id,
    }


@secure_action(
    action_id="get_secure_upload_url",
    action_group="MUTATE",
    required_roles=["crew", "chief_engineer", "chief_officer", "captain", "manager", "hod"],
)
async def get_secure_upload_url(
    ctx: ActionContext,
    filename: str,
    content_type: str = "application/octet-stream",
    folder: str = "documents",
    **params
) -> Dict[str, Any]:
    """
    Generate secure upload URL for a new document.

    Security checks:
    1. @secure_action validates JWT, membership, role, yacht freeze, idempotency
    2. Path is constructed server-side with yacht prefix
    3. Client cannot specify arbitrary path

    Args:
        ctx: ActionContext (validated by decorator)
        filename: Filename for the upload (sanitized)
        content_type: MIME type
        folder: Folder within yacht (documents, attachments, etc.)

    Returns:
        {
            "upload_url": "https://...",
            "storage_path": "yacht_id/documents/uuid/filename",
            "expires_in": 300
        }
    """
    db_client = params.get('_db_client')
    if not db_client:
        raise ActionSecurityError("DB_ERROR", "Database client not available", 500)

    # Sanitize filename
    safe_filename = _sanitize_filename(filename)
    if not safe_filename:
        raise ActionSecurityError("INVALID_FILENAME", "Invalid filename", 400)

    # Construct path server-side (yacht prefix enforced)
    import uuid
    upload_id = str(uuid.uuid4())
    storage_path = f"{ctx.yacht_id}/{folder}/{upload_id}/{safe_filename}"

    # Validate our own construction (defensive)
    if not validate_storage_path(storage_path, ctx.yacht_id):
        logger.error(f"[SecureDoc] SECURITY: Path construction failed: {storage_path}")
        raise ActionSecurityError("INTERNAL_ERROR", "Path construction failed", 500)

    # Generate signed upload URL
    try:
        upload_url = await _generate_signed_upload_url(
            db_client,
            storage_path,
            content_type,
            expires_in=300,  # 5 minutes for upload
        )
    except Exception as e:
        logger.error(f"[SecureDoc] Upload URL generation failed: {e}")
        raise ActionSecurityError("URL_ERROR", "Failed to generate URL", 500)

    logger.info(
        f"[SecureDoc] Upload URL generated: user={ctx.user_id[:8]}..., "
        f"path={storage_path[:30]}..."
    )

    return {
        "upload_url": upload_url,
        "storage_path": storage_path,
        "upload_id": upload_id,
        "expires_in": 300,
    }


@secure_action(
    action_id="delete_document",
    action_group="SIGNED",
    required_roles=["captain", "manager"],
    validate_entities=["document_id"],
    entity_type_mapping={"document_id": "doc_metadata"},
)
async def delete_document(
    ctx: ActionContext,
    document_id: str,
    signature: Dict[str, Any] = None,
    **params
) -> Dict[str, Any]:
    """
    Delete a document (soft delete).

    SIGNED action requiring signature from captain/manager.

    Security checks:
    1. @secure_action validates JWT, membership, role, yacht freeze, idempotency
    2. Ownership validation ensures document belongs to ctx.yacht_id
    3. Signature required for SIGNED actions
    4. Audit with full signature payload

    Args:
        ctx: ActionContext
        document_id: Document UUID
        signature: Signature payload (required for SIGNED)

    Returns:
        {"deleted": True, "document_id": "..."}
    """
    db_client = params.get('_db_client')
    if not db_client:
        raise ActionSecurityError("DB_ERROR", "Database client not available", 500)

    # Signature required for SIGNED actions
    if not signature:
        raise ActionSecurityError("SIGNATURE_REQUIRED", "Signature required", 400)

    # Lookup document (validates ownership)
    doc = await lookup_document_by_id(db_client, document_id, ctx.yacht_id)
    if not doc:
        raise OwnershipValidationError("document", document_id)

    # Soft delete
    try:
        db_client.table("doc_metadata").update({
            "deleted_at": "now()",
            "deleted_by": ctx.user_id,
        }).eq("id", document_id).eq("yacht_id", ctx.yacht_id).execute()

    except Exception as e:
        logger.error(f"[SecureDoc] Delete failed: {e}")
        raise ActionSecurityError("DELETE_ERROR", "Failed to delete document", 500)

    # Build audit entry with signature
    audit = build_audit_entry(
        ctx=ctx,
        action="delete_document",
        entity_type="document",
        entity_id=document_id,
        old_values={"deleted_at": None},
        new_values={"deleted_at": "now()"},
        signature=signature,
        outcome="allowed",
    )

    # Write audit
    try:
        db_client.table("pms_audit_log").insert(audit).execute()
    except Exception as e:
        logger.error(f"[SecureDoc] Audit write failed: {e}")

    logger.info(
        f"[SecureDoc] Document deleted: user={ctx.user_id[:8]}..., "
        f"doc={document_id[:8]}..."
    )

    return {
        "deleted": True,
        "document_id": document_id,
    }


# ============================================================================
# Helper Functions
# ============================================================================

def _sanitize_filename(filename: str) -> Optional[str]:
    """
    Sanitize filename for storage.

    Removes path traversal attempts and invalid characters.
    """
    if not filename:
        return None

    # Remove path separators
    safe = filename.replace("/", "_").replace("\\", "_")

    # Remove path traversal
    safe = safe.replace("..", "_")

    # Remove leading dots
    while safe.startswith("."):
        safe = safe[1:]

    # Limit length
    if len(safe) > 255:
        safe = safe[:255]

    if not safe:
        return None

    return safe


async def _generate_signed_download_url(
    db_client,
    storage_path: str,
    expires_in: int,
) -> str:
    """
    Generate signed download URL.

    Uses Supabase storage.createSignedUrl.
    """
    try:
        result = db_client.storage.from_("documents").create_signed_url(
            storage_path,
            expires_in,
        )
        return result.get("signedURL") or result.get("signed_url") or result
    except Exception as e:
        logger.error(f"[SecureDoc] Signed URL error: {e}")
        raise


async def _generate_signed_upload_url(
    db_client,
    storage_path: str,
    content_type: str,
    expires_in: int,
) -> str:
    """
    Generate signed upload URL.

    Uses Supabase storage.createSignedUploadUrl.
    """
    try:
        result = db_client.storage.from_("documents").create_signed_upload_url(
            storage_path,
        )
        return result.get("signedURL") or result.get("signed_url") or result.get("signedUrl")
    except Exception as e:
        logger.error(f"[SecureDoc] Signed upload URL error: {e}")
        raise


# ============================================================================
# Exports
# ============================================================================

__all__ = [
    # Validation
    "validate_storage_path",
    "extract_yacht_from_path",
    "StoragePathError",
    # Lookup
    "lookup_document_by_id",
    # Handlers
    "get_secure_download_url",
    "get_secure_upload_url",
    "delete_document",
]
