"""
CelesteOS Backend - Document Routes

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

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
import logging
import os

from middleware.auth import get_authenticated_user
from supabase import create_client

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

# Valid object types for document links
VALID_OBJECT_TYPES = ['work_order', 'equipment', 'handover', 'fault', 'part', 'receiving', 'purchase_order']

# Roles that can link/unlink documents
LINK_MANAGE_ROLES = ['admin', 'captain', 'chief_engineer', 'chief_officer', 'crew_member', 'engineer', 'purser']


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
):
    """
    Link a document to an object (work order, equipment, handover, etc.).

    SOC-2 Compliance:
    - Yacht isolation enforced
    - Role-based access control
    - Idempotent (duplicate links return success)
    - Audit logged
    """
    yacht_id = auth['yacht_id']
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
):
    """
    Unlink a document from an object (soft delete).

    SOC-2 Compliance:
    - Yacht isolation enforced
    - Role-based access control
    - Idempotent (already unlinked returns success)
    - Audit logged
    """
    yacht_id = auth['yacht_id']
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
):
    """
    Get all active links for a document.

    Returns the list of objects (work orders, equipment, etc.) that this document is linked to.
    """
    yacht_id = auth['yacht_id']
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
):
    """
    Get all documents linked to a specific object.

    Use this to show attached documents on a work order, equipment, etc.
    """
    yacht_id = auth['yacht_id']
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
