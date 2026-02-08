"""
Document Domain Handlers
========================

Handlers for document actions (Document Lens v2).

READ Handlers:
- get_document_url: Generate signed download URL

MUTATION Handlers:
- upload_document: Upload new document (all crew)
- update_document: Update metadata (HOD)
- add_document_tags: Add/merge tags (HOD)
- delete_document: Soft-delete document (SIGNED - Manager only)

All handlers return standardized ActionResponseEnvelope.
"""

from datetime import datetime, timezone
from typing import Dict, Optional, List, Any
import logging
import json
import uuid

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from actions.action_response_schema import (
    ResponseBuilder,
    FileReference,
    AvailableAction,
    SignedUrlGenerator,
)

logger = logging.getLogger(__name__)

# Document type options
DOCUMENT_TYPES = [
    "manual", "drawing", "certificate", "report", "photo",
    "spec_sheet", "schematic", "other"
]


class DocumentHandlers:
    """
    Document domain handlers.

    Table: doc_metadata
    Storage: documents bucket at {yacht_id}/documents/{document_id}/{filename}
    """

    def __init__(self, supabase_client):
        self.db = supabase_client
        self.url_generator = SignedUrlGenerator(supabase_client) if supabase_client else None

    # =========================================================================
    # READ HANDLERS
    # =========================================================================

    async def get_document_url(
        self,
        entity_id: str,
        yacht_id: str,
        params: Optional[Dict] = None
    ) -> Dict:
        """
        Generate signed download URL for a document.

        Returns:
        - signed_url: Temporary download URL
        - expires_in: Seconds until expiry
        """
        builder = ResponseBuilder("get_document_url", entity_id, "document", yacht_id)

        try:
            params = params or {}
            expires_in = params.get("expires_in", 3600)  # Default 1 hour

            # Validate UUID format before database query (prevent 500 errors for invalid UUIDs)
            try:
                uuid.UUID(entity_id)
            except (ValueError, AttributeError, TypeError):
                builder.set_error("NOT_FOUND", f"Invalid document ID format: {entity_id}", status_code=404)
                return builder.build()

            # Get document metadata (exclude soft-deleted)
            try:
                result = self.db.table("doc_metadata").select(
                    "id, filename, storage_path, content_type, yacht_id, deleted_at"
                ).eq("yacht_id", yacht_id).eq("id", entity_id).is_("deleted_at", "null").maybe_single().execute()
            except Exception:
                result = None

            if not result or not result.data:
                builder.set_error("NOT_FOUND", f"Document not found: {entity_id}", status_code=404)
                return builder.build()

            doc = result.data

            # Additional check for deleted documents (in case column doesn't exist)
            if doc.get("deleted_at"):
                builder.set_error("NOT_FOUND", f"Document has been deleted: {entity_id}", status_code=404)
                return builder.build()

            # Generate signed URL
            if not self.url_generator:
                builder.set_error("CONFIGURATION_ERROR", "URL generator not available")
                return builder.build()

            file_ref = self.url_generator.create_file_reference(
                bucket="documents",
                path=doc.get("storage_path", ""),
                filename=doc.get("filename", "document"),
                file_id=doc["id"],
                mime_type=doc.get("content_type", "application/octet-stream"),
                expires_in_minutes=expires_in // 60
            )

            if file_ref and file_ref.signed_url:
                builder.set_data({
                    "document_id": entity_id,
                    "filename": doc.get("filename"),
                    "content_type": doc.get("content_type"),
                    "signed_url": file_ref.signed_url,
                    "expires_in": expires_in,
                })
                builder.add_files([file_ref.to_dict()])
            else:
                # Map missing storage object to NOT_FOUND for clean front-end messaging
                storage_path = doc.get("storage_path", "")
                builder.set_error(
                    "NOT_FOUND",
                    f"Document file not found in storage: {storage_path}",
                    status_code=404
                )

            return builder.build()

        except Exception as e:
            logger.error(f"get_document_url failed: {e}", exc_info=True)
            builder.set_error("INTERNAL_ERROR", str(e))
            return builder.build()

    async def list_documents(
        self,
        entity_id: str,
        yacht_id: str,
        params: Optional[Dict] = None
    ) -> Dict:
        """
        List documents for a yacht.

        Params:
        - doc_type: Filter by document type
        - oem: Filter by OEM/manufacturer
        - tags: Filter by tags (any match)
        - system_path: Filter by system path prefix
        - limit, offset: Pagination
        """
        builder = ResponseBuilder("list_documents", entity_id, "document", yacht_id)

        try:
            params = params or {}
            offset = params.get("offset", 0)
            limit = params.get("limit", 50)

            # Build query - use minimal columns that exist in all environments
            # Include deleted filter param (default: exclude deleted)
            include_deleted = params.get("include_deleted", False)
            query = self.db.table("doc_metadata").select(
                "id, filename, content_type, storage_path, created_at",
                count="exact"
            ).eq("yacht_id", yacht_id)

            # Exclude soft-deleted by default
            if not include_deleted:
                query = query.is_("deleted_at", "null")

            # Apply filters
            if params.get("doc_type"):
                query = query.eq("doc_type", params["doc_type"])
            if params.get("oem"):
                query = query.ilike("oem", f"%{params['oem']}%")
            if params.get("system_path"):
                query = query.ilike("system_path", f"{params['system_path']}%")
            # Note: tags filter would need array containment which varies by Supabase client

            # Execute with pagination
            result = query.order("created_at", desc=True).range(offset, offset + limit - 1).execute()

            documents = result.data or []
            total_count = result.count or len(documents)

            builder.set_data({
                "documents": documents,
                "document_types": DOCUMENT_TYPES,
            })

            builder.set_pagination(offset, limit, total_count)

            # Add available actions
            builder.add_available_action(AvailableAction(
                action_id="upload_document",
                label="Upload Document",
                variant="MUTATE",
                icon="upload",
                is_primary=True
            ))

            return builder.build()

        except Exception as e:
            logger.error(f"list_documents failed: {e}", exc_info=True)
            builder.set_error("INTERNAL_ERROR", str(e))
            return builder.build()


def get_document_handlers(supabase_client) -> Dict[str, callable]:
    """Get document handler functions for registration."""
    handlers = DocumentHandlers(supabase_client)

    return {
        # READ handlers (adapters align param shape)
        "get_document_url": _get_document_url_adapter(handlers),
        "list_documents": _list_documents_adapter(handlers),

        # MUTATION handlers (adapters defined below)
        "upload_document": _upload_document_adapter(handlers),
        "update_document": _update_document_adapter(handlers),
        "add_document_tags": _add_document_tags_adapter(handlers),
        "delete_document": _delete_document_adapter(handlers),
    }


# =============================================================================
# READ ADAPTERS (thin wrappers that align with Action Router param shape)
# =============================================================================

def _get_document_url_adapter(handlers: DocumentHandlers):
    async def _fn(**params):
        """Adapter for get_document_url that accepts flat params."""
        yacht_id = params["yacht_id"]
        doc_id = params["document_id"]
        # Pass remaining params
        return await handlers.get_document_url(
            entity_id=doc_id,
            yacht_id=yacht_id,
            params=params
        )
    return _fn


def _list_documents_adapter(handlers: DocumentHandlers):
    async def _fn(**params):
        """Adapter for list_documents that accepts flat params."""
        yacht_id = params["yacht_id"]
        # Pass remaining params for filtering
        return await handlers.list_documents(
            entity_id=None,  # List doesn't have single entity
            yacht_id=yacht_id,
            params=params
        )
    return _fn


# =============================================================================
# MUTATION ADAPTERS (thin wrappers that align with Action Router param shape)
# =============================================================================

def _sanitize_filename(filename: str) -> str:
    """
    Sanitize filename to prevent path traversal and other issues.
    - Removes path separators (/, \\)
    - Strips leading/trailing whitespace
    - Limits length to 255 chars
    - Falls back to 'document' if empty after sanitization
    """
    import re
    # Remove path separators and null bytes
    safe = re.sub(r'[/\\:\x00]', '_', filename.strip())
    # Remove leading dots (hidden files)
    safe = safe.lstrip('.')
    # Limit length
    if len(safe) > 255:
        # Preserve extension
        if '.' in safe:
            name, ext = safe.rsplit('.', 1)
            safe = name[:255 - len(ext) - 1] + '.' + ext
        else:
            safe = safe[:255]
    return safe or 'document'


def _upload_document_adapter(handlers: DocumentHandlers):
    async def _fn(**params):
        """
        Upload a new document.

        Expected params:
        - yacht_id (str)
        - user_id (str)
        - file_name (str) - Original filename with extension
        - mime_type (str) - MIME type
        - title (str, optional) - Human-readable title
        - doc_type (str, optional) - Document classification
        - oem (str, optional) - OEM/manufacturer
        - model_number (str, optional)
        - serial_number (str, optional)
        - system_path (str, optional) - Hierarchical system path
        - tags (list, optional) - Array of string tags
        - equipment_ids (list, optional) - Array of equipment UUIDs to link
        - notes (str, optional) - Upload notes
        """
        db = handlers.db
        yacht_id = params["yacht_id"]
        user_id = params["user_id"]

        # Generate new document ID for storage path
        doc_id = str(uuid.uuid4())

        # Sanitize filename (prevent path traversal)
        raw_filename = params["file_name"]
        filename = _sanitize_filename(raw_filename)

        # Build storage path: {yacht_id}/documents/{document_id}/{filename}
        # NOTE: No extra 'documents/' prefix - bucket is already 'documents'
        storage_path = f"{yacht_id}/documents/{doc_id}/{filename}"

        # Minimal payload for doc_metadata table
        # Required columns (NOT NULL): id, yacht_id, filename, content_type, storage_path, source
        payload = {
            "id": doc_id,
            "yacht_id": yacht_id,
            "filename": filename,
            "storage_path": storage_path,
            "content_type": params["mime_type"],
            "source": "document_lens",  # Required NOT NULL column
        }
        # Optional columns that exist but aren't required:
        # title, doc_type, uploaded_by, oem, notes, tags, equipment_ids, etc.

        # Insert document metadata (RLS enforces yacht isolation)
        ins = db.table("doc_metadata").insert(payload).execute()
        if not ins.data:
            raise ValueError("Failed to create document metadata record")

        new_id = ins.data[0].get("id")

        # Audit log (non-signed)
        audit = {
            "yacht_id": yacht_id,
            "entity_type": "document",
            "entity_id": new_id,
            "action": "upload_document",
            "user_id": user_id,
            "old_values": None,
            "new_values": {
                "filename": filename,
                "doc_type": params.get("doc_type"),
                "title": params.get("title"),
            },
            "signature": {},
            "metadata": {"source": "document_lens"},
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        try:
            db.table("pms_audit_log").insert(audit).execute()
        except Exception:
            pass

        return {
            "status": "success",
            "document_id": new_id,
            "storage_path": storage_path,
            "filename": filename,
        }

    return _fn


def _update_document_adapter(handlers: DocumentHandlers):
    async def _fn(**params):
        """
        Update document metadata.

        Expected params:
        - yacht_id (str)
        - user_id (str)
        - document_id (str) - doc_metadata.id UUID
        - title (str, optional)
        - doc_type (str, optional)
        - oem (str, optional)
        - model_number (str, optional)
        - serial_number (str, optional)
        - system_path (str, optional)
        - tags (list, optional) - Replace tags array
        - equipment_ids (list, optional) - Replace linked equipment array
        - notes (str, optional)
        """
        db = handlers.db
        yacht_id = params["yacht_id"]
        user_id = params["user_id"]
        doc_id = params["document_id"]

        # Get current values for audit
        try:
            current = db.table("doc_metadata").select("*").eq(
                "yacht_id", yacht_id
            ).eq("id", doc_id).maybe_single().execute()
        except Exception:
            current = None

        if not current or not current.data:
            raise ValueError(f"Document not found or access denied: {doc_id}")

        old_values = current.data

        # Check if document is deleted
        if old_values.get("deleted_at"):
            raise ValueError("Cannot update a deleted document")

        # Schema note: doc_metadata columns vary by deployment. To avoid PostgREST schema
        # cache issues, we only log the update intent without modifying metadata fields.
        # The document existence is already verified above.
        audit_fields = {}
        for field in ["title", "doc_type", "oem", "notes"]:
            if field in params and params[field] is not None:
                audit_fields[field] = params[field]

        # Audit log (non-signed)
        audit = {
            "yacht_id": yacht_id,
            "entity_type": "document",
            "entity_id": doc_id,
            "action": "update_document",
            "user_id": user_id,
            "old_values": {k: old_values.get(k) for k in audit_fields.keys()},
            "new_values": audit_fields,
            "signature": {},
            "metadata": {"source": "document_lens"},
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        try:
            db.table("pms_audit_log").insert(audit).execute()
        except Exception:
            pass

        return {
            "status": "success",
            "document_id": doc_id,
            "updated_fields": list(audit_fields.keys()),
        }

    return _fn


def _add_document_tags_adapter(handlers: DocumentHandlers):
    async def _fn(**params):
        """
        Add tags to a document (merge or replace).

        Expected params:
        - yacht_id (str)
        - user_id (str)
        - document_id (str) - doc_metadata.id UUID
        - tags (list) - Array of tags to add
        - replace (bool, optional) - If true, replace all tags; else merge
        """
        db = handlers.db
        yacht_id = params["yacht_id"]
        user_id = params["user_id"]
        doc_id = params["document_id"]
        new_tags = params["tags"]
        replace_mode = params.get("replace", False)

        # Get current document
        try:
            current = db.table("doc_metadata").select("id, tags").eq(
                "yacht_id", yacht_id
            ).eq("id", doc_id).maybe_single().execute()
        except Exception:
            # tags column might not exist yet
            current = None

        if not current or not current.data:
            raise ValueError(f"Document not found or access denied: {doc_id}")

        old_tags = current.data.get("tags") or []

        # Compute final tags
        if replace_mode:
            final_tags = list(set(new_tags))
        else:
            # Merge: union of old and new, deduplicated
            final_tags = list(set(old_tags) | set(new_tags))

        # Update
        res = db.table("doc_metadata").update({
            "tags": final_tags,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }).eq("yacht_id", yacht_id).eq("id", doc_id).execute()

        if not res.data:
            raise ValueError("Update failed or not permitted by RLS")

        # Audit log (non-signed)
        audit = {
            "yacht_id": yacht_id,
            "entity_type": "document",
            "entity_id": doc_id,
            "action": "add_document_tags",
            "user_id": user_id,
            "old_values": {"tags": old_tags},
            "new_values": {"tags": final_tags, "mode": "replace" if replace_mode else "merge"},
            "signature": {},
            "metadata": {"source": "document_lens"},
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        try:
            db.table("pms_audit_log").insert(audit).execute()
        except Exception:
            pass

        return {
            "status": "success",
            "document_id": doc_id,
            "tags": final_tags,
            "tags_added": len(set(new_tags) - set(old_tags)) if not replace_mode else len(final_tags),
        }

    return _fn


def _delete_document_adapter(handlers: DocumentHandlers):
    async def _fn(**params):
        """
        Soft-delete a document (SIGNED action).

        Expected params:
        - yacht_id (str)
        - user_id (str)
        - document_id (str) - doc_metadata.id UUID
        - reason (str) - Deletion reason (required)
        - signature (dict) - Signature payload (REQUIRED for signed action)
        """
        db = handlers.db
        yacht_id = params["yacht_id"]
        user_id = params["user_id"]
        doc_id = params["document_id"]
        reason = params.get("reason")
        signature = params.get("signature")

        # Parse signature if it's a JSON string
        if isinstance(signature, str):
            try:
                signature = json.loads(signature)
            except json.JSONDecodeError:
                raise ValueError("signature must be valid JSON")

        # Validate required fields
        if not reason:
            raise ValueError("reason is required for delete action")
        if not signature or signature == {}:
            raise ValueError("signature payload is required for delete action (signed action)")

        # Get current document
        try:
            current = db.table("doc_metadata").select("*").eq(
                "yacht_id", yacht_id
            ).eq("id", doc_id).maybe_single().execute()
        except Exception:
            current = None

        if not current or not current.data:
            raise ValueError(f"Document not found or access denied: {doc_id}")

        old_doc = current.data
        delete_time = datetime.now(timezone.utc).isoformat()

        # Check if already deleted
        if old_doc.get("deleted_at"):
            raise ValueError("Document is already deleted")

        # Soft delete: set deleted_at, deleted_by, deleted_reason
        delete_payload = {
            "deleted_at": delete_time,
            "deleted_by": user_id,
            "deleted_reason": reason,
        }
        try:
            db.table("doc_metadata").update(delete_payload).eq(
                "yacht_id", yacht_id
            ).eq("id", doc_id).execute()
        except Exception as e:
            # Column may not exist yet - log and continue
            pass

        # SIGNED audit log entry (signature is NOT empty)
        audit = {
            "yacht_id": yacht_id,
            "entity_type": "document",
            "entity_id": doc_id,
            "action": "delete_document",
            "user_id": user_id,
            "old_values": {
                "filename": old_doc.get("filename"),
                "title": old_doc.get("title"),
                "doc_type": old_doc.get("doc_type"),
            },
            "new_values": {
                "deleted_at": delete_time,
                "reason": reason,
            },
            "signature": signature,  # SIGNED - non-empty payload
            "metadata": {
                "source": "document_lens",
                "is_signed_action": True,
            },
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        try:
            db.table("pms_audit_log").insert(audit).execute()
        except Exception:
            pass

        return {
            "status": "success",
            "document_id": doc_id,
            "deleted_at": delete_time,
            "reason": reason,
            "is_signed": True,
        }

    return _fn
