"""
Secure Document Handlers
=========================

Wraps document_handlers with @secure_action decorator for
security enforcement (Phase 2).

Security invariants enforced:
1. Yacht context from auth (never payload)
2. Storage path must have {yacht_id}/ prefix
3. Ownership validation for document_id
4. Idempotency for MUTATE actions
5. SIGNED action group for delete_document
6. Yacht freeze blocks mutations

Usage:
    from handlers.secure_document_handlers import get_secure_document_handlers
    handlers = get_secure_document_handlers(supabase_client)
"""

from typing import Dict, Optional, Any
import logging
import re

from middleware.action_security import (
    secure_action,
    ActionContext,
    ActionSecurityError,
    build_audit_entry,
)
from handlers.document_handlers import DocumentHandlers, DOCUMENT_TYPES

logger = logging.getLogger(__name__)


# ============================================================================
# ROLE DEFINITIONS
# ============================================================================

CREW_ROLES = ["crew", "hod", "chief_engineer", "captain", "manager", "purser"]
HOD_ROLES = ["hod", "chief_engineer", "captain", "manager"]
MANAGER_ROLES = ["captain", "manager"]


# ============================================================================
# STORAGE PATH VALIDATION
# ============================================================================

class StoragePathError(ActionSecurityError):
    """Raised when storage path validation fails."""
    def __init__(self, message: str):
        super().__init__(
            "INVALID_STORAGE_PATH",
            message,
            status_code=400,
        )


def validate_storage_path_prefix(path: str, yacht_id: str) -> None:
    """
    Validate that storage path has correct yacht_id prefix.

    Security invariant: All storage operations must be scoped to yacht.

    Args:
        path: Storage path to validate
        yacht_id: Expected yacht_id prefix

    Raises:
        StoragePathError: If path doesn't have correct prefix
    """
    if not path:
        raise StoragePathError("Storage path is required")

    # Path must start with {yacht_id}/
    expected_prefix = f"{yacht_id}/"
    if not path.startswith(expected_prefix):
        logger.warning(
            f"[StorageSecurity] Path prefix violation: "
            f"expected '{expected_prefix}...', got '{path[:50]}...'"
        )
        raise StoragePathError(
            f"Storage path must start with yacht prefix"
        )

    # Check for path traversal attempts
    if '..' in path or path.startswith('/'):
        logger.warning(f"[StorageSecurity] Path traversal attempt: {path}")
        raise StoragePathError("Invalid storage path")


def build_storage_path(yacht_id: str, document_id: str, filename: str) -> str:
    """
    Build a secure storage path with yacht prefix.

    Format: {yacht_id}/documents/{document_id}/{filename}

    Args:
        yacht_id: Yacht UUID
        document_id: Document UUID
        filename: Sanitized filename

    Returns:
        Secure storage path
    """
    # Sanitize filename
    safe_filename = re.sub(r'[/\\:\x00]', '_', filename.strip())
    safe_filename = safe_filename.lstrip('.')
    if not safe_filename:
        safe_filename = 'document'
    if len(safe_filename) > 255:
        safe_filename = safe_filename[:255]

    return f"{yacht_id}/documents/{document_id}/{safe_filename}"


# ============================================================================
# SECURED HANDLER WRAPPERS
# ============================================================================

def create_secure_document_handlers(db_client) -> Dict[str, Any]:
    """
    Create secured document handlers with @secure_action decorator.

    Args:
        db_client: Supabase client for TENANT DB

    Returns:
        Dict of action_name -> secured handler function
    """
    handlers = DocumentHandlers(db_client)

    # =========================================================================
    # GET DOCUMENT URL (READ)
    # =========================================================================

    @secure_action(
        action_id="get_document_url",
        action_group="READ",
        required_roles=CREW_ROLES,
        validate_entities=["document_id"],
        entity_type_mapping={"document_id": "doc_metadata"},
    )
    async def get_document_url(ctx: ActionContext, **params):
        """Generate signed download URL (secured wrapper)."""
        document_id = params.get("entity_id") or params.get("document_id")
        return await handlers.get_document_url(
            entity_id=document_id,
            yacht_id=ctx.yacht_id,
            params=params,
        )

    # =========================================================================
    # LIST DOCUMENTS (READ)
    # =========================================================================

    @secure_action(
        action_id="list_documents",
        action_group="READ",
        required_roles=CREW_ROLES,
    )
    async def list_documents(ctx: ActionContext, **params):
        """List documents for yacht (secured wrapper)."""
        return await handlers.list_documents(
            entity_id=None,
            yacht_id=ctx.yacht_id,
            params=params,
        )

    # =========================================================================
    # UPLOAD DOCUMENT (MUTATE - all crew)
    # =========================================================================

    @secure_action(
        action_id="upload_document",
        action_group="MUTATE",
        required_roles=CREW_ROLES,
    )
    async def upload_document(ctx: ActionContext, **params):
        """Upload new document (secured wrapper)."""
        import uuid

        # Generate document ID for storage path
        doc_id = str(uuid.uuid4())

        # Build secure storage path with yacht prefix
        filename = params.get("file_name", "document")
        storage_path = build_storage_path(ctx.yacht_id, doc_id, filename)

        # Validate the path we just built (defense in depth)
        validate_storage_path_prefix(storage_path, ctx.yacht_id)

        # Get the original upload handler
        from handlers.document_handlers import _upload_document_adapter
        upload_fn = _upload_document_adapter(handlers)

        return await upload_fn(
            yacht_id=ctx.yacht_id,
            user_id=ctx.user_id,
            file_name=filename,
            mime_type=params.get("mime_type", "application/octet-stream"),
            title=params.get("title"),
            doc_type=params.get("doc_type"),
            oem=params.get("oem"),
            model_number=params.get("model_number"),
            serial_number=params.get("serial_number"),
            system_path=params.get("system_path"),
            tags=params.get("tags"),
            equipment_ids=params.get("equipment_ids"),
            notes=params.get("notes"),
        )

    # =========================================================================
    # UPDATE DOCUMENT (MUTATE - HOD)
    # =========================================================================

    @secure_action(
        action_id="update_document",
        action_group="MUTATE",
        required_roles=HOD_ROLES,
        validate_entities=["document_id"],
        entity_type_mapping={"document_id": "doc_metadata"},
    )
    async def update_document(ctx: ActionContext, **params):
        """Update document metadata (secured wrapper)."""
        from handlers.document_handlers import _update_document_adapter
        update_fn = _update_document_adapter(handlers)

        return await update_fn(
            yacht_id=ctx.yacht_id,
            user_id=ctx.user_id,
            document_id=params["document_id"],
            title=params.get("title"),
            doc_type=params.get("doc_type"),
            oem=params.get("oem"),
            model_number=params.get("model_number"),
            serial_number=params.get("serial_number"),
            system_path=params.get("system_path"),
            tags=params.get("tags"),
            equipment_ids=params.get("equipment_ids"),
            notes=params.get("notes"),
        )

    # =========================================================================
    # ADD DOCUMENT TAGS (MUTATE - HOD)
    # =========================================================================

    @secure_action(
        action_id="add_document_tags",
        action_group="MUTATE",
        required_roles=HOD_ROLES,
        validate_entities=["document_id"],
        entity_type_mapping={"document_id": "doc_metadata"},
    )
    async def add_document_tags(ctx: ActionContext, **params):
        """Add tags to document (secured wrapper)."""
        from handlers.document_handlers import _add_document_tags_adapter
        tags_fn = _add_document_tags_adapter(handlers)

        return await tags_fn(
            yacht_id=ctx.yacht_id,
            user_id=ctx.user_id,
            document_id=params["document_id"],
            tags=params["tags"],
            replace=params.get("replace", False),
        )

    # =========================================================================
    # DELETE DOCUMENT (SIGNED - Manager only)
    # =========================================================================

    @secure_action(
        action_id="delete_document",
        action_group="SIGNED",
        required_roles=MANAGER_ROLES,
        validate_entities=["document_id"],
        entity_type_mapping={"document_id": "doc_metadata"},
    )
    async def delete_document(ctx: ActionContext, **params):
        """Soft-delete document (secured wrapper - SIGNED action)."""
        from handlers.document_handlers import _delete_document_adapter
        delete_fn = _delete_document_adapter(handlers)

        return await delete_fn(
            yacht_id=ctx.yacht_id,
            user_id=ctx.user_id,
            document_id=params["document_id"],
            reason=params["reason"],
            signature=params["signature"],
        )

    return {
        # READ handlers
        "get_document_url": get_document_url,
        "list_documents": list_documents,

        # MUTATE handlers
        "upload_document": upload_document,
        "update_document": update_document,
        "add_document_tags": add_document_tags,

        # SIGNED handlers
        "delete_document": delete_document,
    }


def get_secure_document_handlers(db_client) -> Dict[str, Any]:
    """
    Get secured document handlers.

    This is the recommended entry point for production use.
    All handlers have @secure_action decorator applied.

    Args:
        db_client: Supabase client for TENANT DB

    Returns:
        Dict of action_name -> secured handler function
    """
    return create_secure_document_handlers(db_client)


# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    'get_secure_document_handlers',
    'create_secure_document_handlers',
    'validate_storage_path_prefix',
    'build_storage_path',
    'StoragePathError',
    'DOCUMENT_TYPES',
]
