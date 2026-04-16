"""
CelesteOS Backend - Document Routes
Version: 2026-02-08-v3 (maybe_single fix)

Endpoints:
- POST /v1/documents/link     - Link a document to an object (work order, equipment, etc.)
- POST /v1/documents/unlink   - Unlink a document from an object
- GET  /v1/documents/links    - Get all links for a document

SOC-2 Compliance:
- All queries scoped by yacht_id
- Role-based access control
- Audit logging for all mutations
- Idempotent operations
"""

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form, status
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
import logging
import os
import uuid

from middleware.auth import get_authenticated_user
from middleware.vessel_access import resolve_yacht_id
from supabase import create_client
from utils.filenames import sanitize_storage_filename
from routes.handlers.ledger_utils import build_ledger_event

logger = logging.getLogger(__name__)


def _get_tenant_client(tenant_key_alias: str):
    """
    Get Supabase client for tenant DB.

    Uses tenant-prefixed env vars: {tenant_key_alias}_SUPABASE_URL
    Falls back to TENANT_1 if specific tenant vars not found.
    """
    url = os.environ.get(f'{tenant_key_alias}_SUPABASE_URL')
    key = os.environ.get(f'{tenant_key_alias}_SUPABASE_SERVICE_KEY')

    if not url or not key:
        # Fallback to TENANT_1 vars (for single-tenant setup)
        url = os.environ.get('TENANT_1_SUPABASE_URL')
        key = os.environ.get('TENANT_1_SUPABASE_SERVICE_KEY')

    if not url or not key:
        logger.error(f"[TenantClient] Missing credentials for {tenant_key_alias}")
        raise ValueError(f'Missing credentials for tenant {tenant_key_alias}')

    return create_client(url, key)

router = APIRouter(prefix="/v1/documents", tags=["documents"])


# ============================================================================
# CONSTANTS
# ============================================================================

# Valid object types for document links.
# IMPORTANT: this list must stay in sync with the DB CHECK constraint
# `email_attachment_object_links_object_type_check`. See migration
# 20260415_f3_warranty_claim_constraint.sql for the matching ALTER.
VALID_OBJECT_TYPES = ['work_order', 'equipment', 'handover', 'fault', 'part', 'receiving', 'purchase_order', 'warranty_claim']

# Roles that can link/unlink documents.
# chief_steward added 2026-04-15 so provisions invoices can be attached to POs.
LINK_MANAGE_ROLES = ['admin', 'captain', 'chief_engineer', 'chief_officer', 'chief_steward', 'crew_member', 'engineer', 'purser']

# Roles that can upload new documents via POST /v1/documents/upload.
# Matches the action_router registry entry for `upload_document` (HOD+).
UPLOAD_DOCUMENT_ROLES = [
    'chief_engineer', 'chief_officer', 'chief_steward',
    'purser', 'captain', 'manager',
]

# Upload constraints (must mirror frontend AttachmentUploadModal).
MAX_UPLOAD_BYTES = 15 * 1024 * 1024  # 15 MB
ACCEPTED_UPLOAD_MIME_TYPES = {
    'application/pdf',
    'image/jpeg', 'image/png', 'image/heic', 'image/webp', 'image/tiff',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'application/vnd.ms-excel',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'text/plain',
    'application/zip',
    'application/octet-stream',
}

# Storage bucket for lens-uploaded documents. Matches doc_metadata.storage_bucket
# distribution (2,940 rows) and the path convention used by existing doc_metadata rows.
DOCUMENTS_BUCKET = 'documents'


def _split_csv(value: Optional[str]) -> Optional[List[str]]:
    """Parse a CSV form field into a list. Empty/None returns None."""
    if not value:
        return None
    parts = [p.strip() for p in value.split(',') if p.strip()]
    return parts or None


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class DocumentLinkRequest(BaseModel):
    document_id: str = Field(..., description="UUID of the document to link")
    object_type: str = Field(..., description="Type of object to link to (work_order, equipment, etc.)")
    object_id: str = Field(..., description="UUID of the target object")
    link_reason: Optional[str] = Field(None, description="Reason for linking: email_attachment, manual")
    source_context: Optional[dict] = Field(None, description="Additional context (e.g., email_message_id)")
    idempotency_key: Optional[str] = Field(None, description="Client-generated key for idempotency")


class DocumentUnlinkRequest(BaseModel):
    document_id: str = Field(..., description="UUID of the document to unlink")
    object_type: str = Field(..., description="Type of object to unlink from")
    object_id: str = Field(..., description="UUID of the target object")
    idempotency_key: Optional[str] = Field(None, description="Client-generated key for idempotency")


class DocumentLinksQuery(BaseModel):
    document_id: str = Field(..., description="UUID of the document")


# ============================================================================
# AUDIT HELPER
# ============================================================================

async def audit_document_action(
    supabase,
    yacht_id: str,
    user_id: str,
    action: str,
    document_id: str,
    object_type: str,
    object_id: str,
    old_values: dict = None,
    new_values: dict = None,
    user_role: str = None,
    idempotency_key: str = None,
):
    """Log document link/unlink actions to audit log."""
    try:
        supabase.table('pms_audit_log').insert({
            'yacht_id': yacht_id,
            'action': action,
            'entity_type': 'document_link',
            'entity_id': document_id,
            'user_id': user_id,
            'old_values': old_values or {},
            'new_values': new_values or {},
            'signature': {
                'timestamp': datetime.utcnow().isoformat(),
                'action_version': 'M1',
                'user_role': user_role,
                'idempotency_key': idempotency_key,
                'target': {
                    'object_type': object_type,
                    'object_id': object_id,
                },
            },
        }).execute()
    except Exception as e:
        logger.error(f"[document/audit] Failed to log action {action}: {e}")


# ============================================================================
# POST /v1/documents/link
# ============================================================================

@router.post("/link")
async def link_document(
    request: DocumentLinkRequest,
    auth: dict = Depends(get_authenticated_user),
    yacht_id: Optional[str] = Query(None, description="Vessel scope (fleet users)"),
):
    """
    Link a document to an object (work order, equipment, handover, etc.).

    SOC-2 Compliance:
    - Yacht isolation enforced
    - Role-based access control
    - Idempotent (duplicate links return success)
    - Audit logged
    """
    yacht_id = resolve_yacht_id(auth, yacht_id)
    user_id = auth['user_id']
    user_role = auth.get('role', '')
    supabase = _get_tenant_client(auth['tenant_key_alias'])

    # Role check
    if user_role not in LINK_MANAGE_ROLES:
        logger.warning(f"[documents/link] Forbidden: role={user_role} user={user_id[:8]}")
        raise HTTPException(status_code=403, detail="Insufficient permissions to link documents")

    # Validate object_type
    if request.object_type not in VALID_OBJECT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid object_type. Must be one of: {', '.join(VALID_OBJECT_TYPES)}"
        )

    try:
        # Verify document exists and belongs to yacht
        # Check both doc_yacht_library (email attachments) and doc_metadata (bulk uploads)
        # Note: maybe_single() returns None if no rows found, not an object with .data = None
        doc_result = supabase.table('doc_yacht_library').select('id').eq(
            'id', request.document_id
        ).eq('yacht_id', yacht_id).maybe_single().execute()

        if not doc_result or not doc_result.data:
            # Fallback to doc_metadata for legacy/bulk-uploaded documents
            doc_result = supabase.table('doc_metadata').select('id').eq(
                'id', request.document_id
            ).eq('yacht_id', yacht_id).maybe_single().execute()

        if not doc_result or not doc_result.data:
            raise HTTPException(status_code=404, detail="Document not found")

        # Check for existing active link (idempotency)
        existing = supabase.table('email_attachment_object_links').select('id').eq(
            'yacht_id', yacht_id
        ).eq('document_id', request.document_id).eq(
            'object_type', request.object_type
        ).eq('object_id', request.object_id).eq('is_active', True).limit(1).execute()

        if existing.data:
            existing_id = existing.data[0]['id']
            logger.info(
                f"[documents/link] Already exists: link={existing_id[:8]} "
                f"doc={request.document_id[:8]} → {request.object_type}={request.object_id[:8]}"
            )

            # Audit even for already_exists
            await audit_document_action(
                supabase, yacht_id, user_id,
                action='DOCUMENT_LINK_ALREADY_EXISTS',
                document_id=request.document_id,
                object_type=request.object_type,
                object_id=request.object_id,
                user_role=user_role,
                idempotency_key=request.idempotency_key,
            )

            return {
                'success': True,
                'link_id': existing_id,
                'already_exists': True,
            }

        # Create new link
        link_entry = {
            'yacht_id': yacht_id,
            'document_id': request.document_id,
            'object_type': request.object_type,
            'object_id': request.object_id,
            'link_reason': request.link_reason or 'manual',
            'source_context': request.source_context,
            'is_active': True,
            'created_by': user_id,
        }

        result = supabase.table('email_attachment_object_links').insert(link_entry).execute()
        link_id = result.data[0]['id'] if result.data else None

        # Audit
        await audit_document_action(
            supabase, yacht_id, user_id,
            action='DOCUMENT_LINKED',
            document_id=request.document_id,
            object_type=request.object_type,
            object_id=request.object_id,
            new_values={
                'link_id': link_id,
                'link_reason': request.link_reason,
            },
            user_role=user_role,
            idempotency_key=request.idempotency_key,
        )

        logger.info(
            f"[documents/link] Created: link={link_id[:8] if link_id else 'N/A'} "
            f"doc={request.document_id[:8]} → {request.object_type}={request.object_id[:8]} "
            f"user={user_id[:8]}"
        )

        return {
            'success': True,
            'link_id': link_id,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[documents/link] Error: {e}")
        raise HTTPException(status_code=500, detail="Failed to link document")


# ============================================================================
# POST /v1/documents/unlink
# ============================================================================

@router.post("/unlink")
async def unlink_document(
    request: DocumentUnlinkRequest,
    auth: dict = Depends(get_authenticated_user),
    yacht_id: Optional[str] = Query(None, description="Vessel scope (fleet users)"),
):
    """
    Unlink a document from an object (soft delete).

    SOC-2 Compliance:
    - Yacht isolation enforced
    - Role-based access control
    - Idempotent (already unlinked returns success)
    - Audit logged
    """
    yacht_id = resolve_yacht_id(auth, yacht_id)
    user_id = auth['user_id']
    user_role = auth.get('role', '')
    supabase = _get_tenant_client(auth['tenant_key_alias'])

    # Role check
    if user_role not in LINK_MANAGE_ROLES:
        logger.warning(f"[documents/unlink] Forbidden: role={user_role} user={user_id[:8]}")
        raise HTTPException(status_code=403, detail="Insufficient permissions to unlink documents")

    # Validate object_type
    if request.object_type not in VALID_OBJECT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid object_type. Must be one of: {', '.join(VALID_OBJECT_TYPES)}"
        )

    try:
        # Find the active link
        link_result = supabase.table('email_attachment_object_links').select('id, is_active').eq(
            'yacht_id', yacht_id
        ).eq('document_id', request.document_id).eq(
            'object_type', request.object_type
        ).eq('object_id', request.object_id).limit(1).execute()

        if not link_result.data:
            # No link exists - idempotent success
            logger.info(
                f"[documents/unlink] No link found: "
                f"doc={request.document_id[:8]} → {request.object_type}={request.object_id[:8]}"
            )
            return {
                'success': True,
                'already_unlinked': True,
            }

        link = link_result.data[0]
        link_id = link['id']

        # Already inactive - idempotent success
        if not link.get('is_active', True):
            logger.info(f"[documents/unlink] Already unlinked: link={link_id[:8]}")
            return {
                'success': True,
                'link_id': link_id,
                'already_unlinked': True,
            }

        # Soft delete the link
        supabase.table('email_attachment_object_links').update({
            'is_active': False,
            'removed_at': datetime.utcnow().isoformat(),
            'removed_by': user_id,
        }).eq('id', link_id).execute()

        # Audit
        await audit_document_action(
            supabase, yacht_id, user_id,
            action='DOCUMENT_UNLINKED',
            document_id=request.document_id,
            object_type=request.object_type,
            object_id=request.object_id,
            old_values={'link_id': link_id, 'is_active': True},
            new_values={'is_active': False},
            user_role=user_role,
            idempotency_key=request.idempotency_key,
        )

        logger.info(
            f"[documents/unlink] Removed: link={link_id[:8]} "
            f"doc={request.document_id[:8]} → {request.object_type}={request.object_id[:8]} "
            f"user={user_id[:8]}"
        )

        return {
            'success': True,
            'link_id': link_id,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[documents/unlink] Error: {e}")
        raise HTTPException(status_code=500, detail="Failed to unlink document")


# ============================================================================
# GET /v1/documents/{document_id}/links
# ============================================================================

@router.get("/{document_id}/links")
async def get_document_links(
    document_id: str,
    auth: dict = Depends(get_authenticated_user),
    yacht_id: Optional[str] = Query(None, description="Vessel scope (fleet users)"),
):
    """
    Get all active links for a document.

    Returns the list of objects (work orders, equipment, etc.) that this document is linked to.
    """
    yacht_id = resolve_yacht_id(auth, yacht_id)
    supabase = _get_tenant_client(auth['tenant_key_alias'])

    try:
        # Verify document exists and belongs to yacht
        # Check both doc_yacht_library (email attachments) and doc_metadata (bulk uploads)
        # Note: maybe_single() returns None if no rows found
        doc_result = supabase.table('doc_yacht_library').select('id').eq(
            'id', document_id
        ).eq('yacht_id', yacht_id).maybe_single().execute()

        if not doc_result or not doc_result.data:
            doc_result = supabase.table('doc_metadata').select('id').eq(
                'id', document_id
            ).eq('yacht_id', yacht_id).maybe_single().execute()

        if not doc_result or not doc_result.data:
            raise HTTPException(status_code=404, detail="Document not found")

        # Get all active links
        links_result = supabase.table('email_attachment_object_links').select(
            'id, object_type, object_id, link_reason, source_context, created_at, created_by'
        ).eq('yacht_id', yacht_id).eq('document_id', document_id).eq('is_active', True).execute()

        return {
            'document_id': document_id,
            'links': links_result.data or [],
            'count': len(links_result.data or []),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[documents/links] Error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get document links")


# ============================================================================
# GET /v1/documents/for-object
# ============================================================================

@router.get("/for-object")
async def get_documents_for_object(
    object_type: str,
    object_id: str,
    auth: dict = Depends(get_authenticated_user),
    yacht_id: Optional[str] = Query(None, description="Vessel scope (fleet users)"),
):
    """
    Get all documents linked to a specific object.

    Use this to show attached documents on a work order, equipment, etc.
    """
    yacht_id = resolve_yacht_id(auth, yacht_id)
    supabase = _get_tenant_client(auth['tenant_key_alias'])

    # Validate object_type
    if object_type not in VALID_OBJECT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid object_type. Must be one of: {', '.join(VALID_OBJECT_TYPES)}"
        )

    try:
        # Get all active links for this object
        links_result = supabase.table('email_attachment_object_links').select(
            'id, document_id, link_reason, source_context, created_at'
        ).eq('yacht_id', yacht_id).eq(
            'object_type', object_type
        ).eq('object_id', object_id).eq('is_active', True).execute()

        if not links_result.data:
            return {
                'object_type': object_type,
                'object_id': object_id,
                'documents': [],
                'count': 0,
            }

        # Get document details for each link
        document_ids = [link['document_id'] for link in links_result.data]
        docs_result = supabase.table('doc_yacht_library').select(
            'id, document_name, document_path, document_type'
        ).in_('id', document_ids).execute()

        # Create lookup
        doc_lookup = {doc['id']: doc for doc in (docs_result.data or [])}

        # Combine link info with document info
        documents = []
        for link in links_result.data:
            doc = doc_lookup.get(link['document_id'], {})
            documents.append({
                'link_id': link['id'],
                'document_id': link['document_id'],
                'document_name': doc.get('document_name'),
                'document_path': doc.get('document_path'),
                'document_type': doc.get('document_type'),
                'link_reason': link.get('link_reason'),
                'linked_at': link.get('created_at'),
            })

        return {
            'object_type': object_type,
            'object_id': object_id,
            'documents': documents,
            'count': len(documents),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[documents/for-object] Error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get documents for object")


# ============================================================================
# POST /v1/documents/upload  — multipart
# ============================================================================
#
# This is the REAL upload endpoint. It receives actual file bytes (multipart/
# form-data), writes them to Supabase Storage, then inserts a row into
# doc_metadata. The F2 trigger `trg_doc_metadata_extraction_enqueue` fires on
# that insert and enqueues a search_index row with `embedding_status =
# 'pending_extraction'` so the extraction_worker picks it up, extracts text,
# and flips to `pending` for the projection/embedding pipeline.
#
# This replaces the broken flow where the frontend called the action_router
# `upload_document` action, which only inserted a doc_metadata row without
# uploading file bytes — producing ghost records that 404 on every download.
# The legacy `_upload_document_adapter` stays callable for programmatic
# metadata-only use (tests, re-ingest) but MUST NOT be called from the UI.
#
# Multi-tenant safety:
# - yacht_id and tenant_key_alias come from the authenticated user context,
#   never from the request body.
# - The tenant-scoped Supabase client is used exclusively (no default client).
# - The storage path embeds yacht_id as its first segment, matching the
#   existing convention enforced by internal_dispatcher.py:342.
#
# Failure handling:
# - If storage upload fails → 500, no doc_metadata row written (no ghost).
# - If doc_metadata insert fails → compensating delete of the just-uploaded
#   blob, then 500. The compensating delete is wrapped so that a rollback
#   failure still surfaces the original error and logs the orphaned blob.
# ============================================================================


class DocumentUploadResponse(BaseModel):
    success: bool
    document_id: str
    storage_path: str
    storage_bucket: str
    filename: str
    size_bytes: int
    content_type: str


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(..., description="Document file (PDF, image, or office doc; ≤15 MB)"),
    title: Optional[str] = Form(None, description="Human-readable title (defaults to filename)"),
    doc_type: Optional[str] = Form(None, description="Classification: manual, drawing, certificate, report, photo, spec_sheet, schematic, other"),
    oem: Optional[str] = Form(None, description="Manufacturer"),
    model: Optional[str] = Form(None, description="Model number"),
    system_path: Optional[str] = Form(None, description="Hierarchical system path (e.g. ENGINE_ROOM/MAIN_ENGINE)"),
    description: Optional[str] = Form(None, description="Longer description"),
    tags_csv: Optional[str] = Form(None, description="Comma-separated tags"),
    equipment_ids_csv: Optional[str] = Form(None, description="Comma-separated equipment UUIDs"),
    notes: Optional[str] = Form(None, description="Upload notes"),
    yacht_id: Optional[str] = Query(None, description="Vessel scope (fleet users)"),
    auth: dict = Depends(get_authenticated_user),
):
    """Upload a new document.

    Accepts multipart/form-data with an actual file. Writes the blob to the
    `documents` Supabase Storage bucket at
    `{yacht_id}/documents/{document_id}/{filename}`, then inserts a row into
    `doc_metadata`. The F2 DB trigger auto-enqueues the new row for
    extraction.

    SOC-2 compliance:
    - Yacht isolation enforced (yacht_id from auth context only)
    - Role-based access control (HOD+ only)
    - Audit logged (non-signed — matches upload_document action parity)
    - Storage and metadata writes roll back together on any failure
    """
    yacht_id = resolve_yacht_id(auth, yacht_id)
    user_id = auth['user_id']
    user_role = auth.get('role', '')

    # -----------------------------------------------------------------------
    # Role gate
    # -----------------------------------------------------------------------
    if user_role not in UPLOAD_DOCUMENT_ROLES:
        logger.warning(
            f"[documents/upload] Forbidden: role={user_role} user={user_id[:8] if user_id else 'unknown'}"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Insufficient permissions to upload documents (role '{user_role}' is not in HOD+)"
        )

    # -----------------------------------------------------------------------
    # MIME type gate
    # -----------------------------------------------------------------------
    content_type = (file.content_type or 'application/octet-stream').lower()
    if content_type not in ACCEPTED_UPLOAD_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported file type: {content_type}"
        )

    # -----------------------------------------------------------------------
    # Read file bytes and validate size
    # -----------------------------------------------------------------------
    # UploadFile doesn't expose size until we read — read, then check.
    # The 15 MB cap keeps memory pressure bounded per request.
    try:
        file_content = await file.read()
    except Exception as e:
        logger.error(f"[documents/upload] Failed to read upload stream: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to read uploaded file"
        )

    size_bytes = len(file_content)
    if size_bytes == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty"
        )
    if size_bytes > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum size of {MAX_UPLOAD_BYTES // (1024 * 1024)} MB"
        )

    # -----------------------------------------------------------------------
    # Build document identity + storage path
    # -----------------------------------------------------------------------
    doc_id = str(uuid.uuid4())
    raw_filename = file.filename or 'document'
    filename = sanitize_storage_filename(raw_filename)
    storage_path = f"{yacht_id}/documents/{doc_id}/{filename}"

    supabase = _get_tenant_client(auth['tenant_key_alias'])

    # -----------------------------------------------------------------------
    # Step 1 — upload the blob to Supabase Storage FIRST.
    # If this fails, no doc_metadata row is written (no ghost).
    # -----------------------------------------------------------------------
    try:
        supabase.storage.from_(DOCUMENTS_BUCKET).upload(
            path=storage_path,
            file=file_content,
            file_options={
                'content-type': content_type,
                'upsert': 'false',
            },
        )
    except Exception as e:
        logger.error(
            f"[documents/upload] Storage upload failed: yacht={yacht_id[:8]} "
            f"path={storage_path} err={e}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload file to storage"
        )

    # -----------------------------------------------------------------------
    # Step 2 — insert doc_metadata. The F2 trigger fires AFTER this INSERT
    # and writes search_index(pending_extraction, payload={bucket, path, ...}).
    # -----------------------------------------------------------------------
    doc_metadata_row = {
        'id': doc_id,
        'yacht_id': yacht_id,
        'source': 'document_lens',
        'filename': filename,
        'storage_path': storage_path,
        'storage_bucket': DOCUMENTS_BUCKET,
        'content_type': content_type,
        'size_bytes': size_bytes,
    }
    # Optional columns — only add if the caller supplied them.
    if title:
        doc_metadata_row['metadata'] = {'title': title}
    if doc_type:
        doc_metadata_row['doc_type'] = doc_type
    if oem:
        doc_metadata_row['oem'] = oem
    if model:
        doc_metadata_row['model'] = model
    if system_path:
        doc_metadata_row['system_path'] = system_path
    if description:
        doc_metadata_row['description'] = description

    tags_list = _split_csv(tags_csv)
    if tags_list:
        doc_metadata_row['tags'] = tags_list

    equipment_ids = _split_csv(equipment_ids_csv)
    if equipment_ids:
        doc_metadata_row['equipment_ids'] = equipment_ids

    try:
        ins = supabase.table('doc_metadata').insert(doc_metadata_row).execute()
        if not ins.data:
            raise ValueError("doc_metadata insert returned no data")
        inserted_id = ins.data[0].get('id', doc_id)
    except Exception as e:
        logger.error(
            f"[documents/upload] doc_metadata insert failed — rolling back storage blob: "
            f"yacht={yacht_id[:8]} path={storage_path} err={e}"
        )
        # Compensating delete — best-effort. If this fails, we've leaked a blob
        # but we still surface the original error to the caller.
        try:
            supabase.storage.from_(DOCUMENTS_BUCKET).remove([storage_path])
            logger.info(f"[documents/upload] rolled back storage blob {storage_path}")
        except Exception as rollback_err:
            logger.error(
                f"[documents/upload] ROLLBACK FAILED — orphan blob: "
                f"bucket={DOCUMENTS_BUCKET} path={storage_path} err={rollback_err}"
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to record document metadata"
        )

    # -----------------------------------------------------------------------
    # Step 3 — audit log (non-signed, matches upload_document action parity)
    # -----------------------------------------------------------------------
    audit = {
        'yacht_id': yacht_id,
        'entity_type': 'document',
        'entity_id': inserted_id,
        'action': 'upload_document',
        'user_id': user_id,
        'old_values': None,
        'new_values': {
            'filename': filename,
            'doc_type': doc_type,
            'title': title,
            'size_bytes': size_bytes,
            'storage_bucket': DOCUMENTS_BUCKET,
        },
        'signature': {
            'timestamp': datetime.utcnow().isoformat(),
            'action_version': 'M1',
            'user_role': user_role,
            'source': 'multipart_upload',
        },
        'metadata': {'source': 'document_lens', 'route': '/v1/documents/upload'},
        'created_at': datetime.utcnow().isoformat(),
    }
    try:
        supabase.table('pms_audit_log').insert(audit).execute()
    except Exception as audit_err:
        logger.warning(f"[documents/upload] audit log insert failed (non-fatal): {audit_err}")

    # -----------------------------------------------------------------------
    # Step 4 — ledger_events (required for receipt-layer sealing)
    # -----------------------------------------------------------------------
    try:
        ledger_event = build_ledger_event(
            yacht_id=yacht_id,
            user_id=user_id,
            event_type="create",
            entity_type="document",
            entity_id=inserted_id,
            action="upload_document",
            user_role=user_role,
            change_summary=f"Document uploaded: {filename}",
        )
        supabase.table('ledger_events').insert(ledger_event).execute()
    except Exception as ledger_err:
        if "204" not in str(ledger_err):
            logger.warning(f"[documents/upload] ledger insert failed (non-fatal): {ledger_err}")

    # -----------------------------------------------------------------------
    # Step 5 — notification (non-fatal)
    # -----------------------------------------------------------------------
    try:
        notif_key = f"doc_upload_{inserted_id}"
        supabase.table('pms_notifications').insert({
            'yacht_id': yacht_id,
            'user_id': user_id,
            'notification_type': 'document_uploaded',
            'title': 'Document uploaded',
            'body': f'{filename} uploaded to vessel documents',
            'priority': 'normal',
            'entity_type': 'document',
            'entity_id': inserted_id,
            'cta_action_id': 'get_document_url',
            'cta_payload': {'document_id': inserted_id},
            'idempotency_key': notif_key,
            'is_read': False,
            'triggered_by': user_id,
            'metadata': {'source': 'document_lens', 'filename': filename, 'role': user_role},
        }).execute()
    except Exception as notif_err:
        logger.warning(f"[documents/upload] notification insert failed (non-fatal): {notif_err}")

    logger.info(
        f"[documents/upload] OK: doc_id={inserted_id[:8]} yacht={yacht_id[:8]} "
        f"size={size_bytes} user={user_id[:8] if user_id else 'unknown'} role={user_role}"
    )

    return DocumentUploadResponse(
        success=True,
        document_id=inserted_id,
        storage_path=storage_path,
        storage_bucket=DOCUMENTS_BUCKET,
        filename=filename,
        size_bytes=size_bytes,
        content_type=content_type,
    )
