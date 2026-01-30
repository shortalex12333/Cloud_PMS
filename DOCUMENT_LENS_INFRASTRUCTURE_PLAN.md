# Document Lens Infrastructure - Mimic Work Order Lens Pattern

**Created:** 2026-01-30
**For:** Engineer working on Document Lens
**Pattern:** Mirror Work Order Lens V2 Embeddings Phase 2

---

## Overview

This plan applies the **same infrastructure pattern** from Work Order Lens V2 to Document Lens:
- ✅ Comments on documents (like comments on attachments)
- ✅ Processing hooks (OCR, extraction, ingestion)
- ✅ Queue-based digestion pipeline
- ✅ Entity extraction integration

---

## Work Order Lens Pattern (Reference)

### What Was Built (PR #26)

```
1. pms_attachments table
   ├─ Polymorphic (entity_type, entity_id)
   ├─ category column (photo, document, pdf, manual)
   ├─ storage_path, mime_type
   └─ Soft delete (deleted_at)

2. pms_attachment_comments table
   ├─ Threaded comments ON attachments
   ├─ Department-based RLS
   ├─ parent_comment_id for threading
   └─ Auto-populate author_department

3. Entity-based storage buckets
   ├─ pms-work-order-attachments
   ├─ pms-fault-attachments
   ├─ pms-equipment-attachments
   └─ RLS policies per bucket

4. Handler bucket routing
   ├─ _get_bucket_for_attachment()
   └─ Entity-type → bucket mapping

5. Upload workflow
   ├─ Proxy to image-processing (OCR)
   ├─ Queue extraction job (entities)
   └─ Return immediately (non-blocking)
```

---

## Document Lens Current State

### Existing Infrastructure ✅

**Table:** `doc_metadata` (similar to pms_attachments)
```sql
CREATE TABLE doc_metadata (
    id UUID PRIMARY KEY,
    yacht_id UUID NOT NULL,
    filename VARCHAR(255) NOT NULL,
    storage_path TEXT NOT NULL,
    content_type VARCHAR(100) NOT NULL,
    source VARCHAR(50) NOT NULL,  -- 'document_lens', 'nas', etc.

    -- Metadata
    title TEXT,
    doc_type VARCHAR(50),  -- 'manual', 'drawing', 'certificate', etc.
    oem TEXT,
    model_number TEXT,
    serial_number TEXT,
    system_path TEXT,
    tags TEXT[],
    equipment_ids UUID[],
    notes TEXT,
    uploaded_by UUID,

    -- Soft delete (added 2026-01-28)
    deleted_at TIMESTAMPTZ,
    deleted_by UUID,
    deleted_reason TEXT,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

**Storage Bucket:** `documents` (already exists)
- Path pattern: `{yacht_id}/documents/{document_id}/{filename}`
- RLS: Yacht-scoped access

**Handlers:** `apps/api/handlers/document_handlers.py`
- ✅ `upload_document` (creates metadata, prepares storage path)
- ✅ `get_document_url` (signed URLs)
- ✅ `list_documents` (filtering, pagination)
- ✅ `update_document` (metadata)
- ✅ `add_document_tags` (tagging)
- ✅ `delete_document` (soft delete with signature)

---

## What's Missing (To Mirror Work Order Lens)

### 1. Document Comments Table ❌
**Pattern:** `pms_attachment_comments` → `doc_metadata_comments`

**Use Case:**
- User uploads equipment manual
- Comment: "Pages 45-52 cover hydraulic system specs"
- Another user replies: "See section 3.2 for troubleshooting"

**vs Current:**
- `doc_metadata.notes` field (single text, not threaded)
- No conversation/threading
- No department-based access control

### 2. Processing Hooks ❌
**Pattern:** Work order lens proxies to image-processing → extraction

**Use Case:**
- User uploads PDF manual
- OCR extracts text (image-processing service)
- Entity extraction identifies parts, procedures (extraction service)
- GraphRAG population for RAG queries
- Update doc_metadata.related_text for search

**vs Current:**
- `upload_document` only creates metadata record
- No OCR integration
- No entity extraction
- No ingestion pipeline trigger

### 3. Queue Integration ❌
**Pattern:** extraction_jobs table with priority tiers

**Use Case:**
- User uploads 10 equipment manuals
- Jobs queued with priority: 'user_upload' (high)
- Worker processes with weighted fair queuing
- Background email embeddings continue (30% capacity)

**vs Current:**
- No job queue
- No async processing
- No extraction worker integration

### 4. Storage Path in Metadata ⚠️
**Pattern:** storage_path field for signed URL generation

**Status:** `doc_metadata.storage_path` EXISTS ✅
- Already has storage_path column
- Pattern: `{yacht_id}/documents/{document_id}/{filename}`

---

## Implementation Plan

### Phase 1: Comments Infrastructure (Mirror PR #26)

#### Step 1.1: Create doc_metadata_comments Table

**Migration:** `20260130_111_create_doc_metadata_comments_table.sql`

```sql
-- =====================================================
-- Migration: Create Document Comments Table
-- Created: 2026-01-30
-- Pattern: Mirrors pms_attachment_comments for Document Lens
-- =====================================================

CREATE TABLE IF NOT EXISTS public.doc_metadata_comments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    yacht_id UUID NOT NULL,
    document_id UUID NOT NULL REFERENCES public.doc_metadata(id) ON DELETE CASCADE,

    -- Comment content
    comment TEXT NOT NULL,

    -- Author tracking
    created_by UUID NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Edit tracking
    updated_by UUID,
    updated_at TIMESTAMPTZ,

    -- Soft delete
    deleted_by UUID,
    deleted_at TIMESTAMPTZ,

    -- Department context (cached at creation)
    author_department VARCHAR(100),

    -- Threading support
    parent_comment_id UUID REFERENCES public.doc_metadata_comments(id) ON DELETE CASCADE,

    -- Metadata
    metadata JSONB DEFAULT '{}'::jsonb,

    -- Constraints
    CONSTRAINT chk_comment_not_empty CHECK (LENGTH(TRIM(comment)) > 0),
    CONSTRAINT chk_valid_department CHECK (
        author_department IS NULL OR author_department IN (
            'technical', 'deck', 'interior', 'galley', 'engineering', 'bridge'
        )
    )
);

-- Indexes
CREATE INDEX idx_doc_comments_document_id ON public.doc_metadata_comments(document_id);
CREATE INDEX idx_doc_comments_yacht_id ON public.doc_metadata_comments(yacht_id);
CREATE INDEX idx_doc_comments_created_at ON public.doc_metadata_comments(created_at DESC);
CREATE INDEX idx_doc_comments_deleted_at ON public.doc_metadata_comments(deleted_at) WHERE deleted_at IS NULL;
CREATE INDEX idx_doc_comments_parent ON public.doc_metadata_comments(parent_comment_id) WHERE parent_comment_id IS NOT NULL;

-- =====================================================
-- RLS Policies
-- =====================================================

ALTER TABLE public.doc_metadata_comments ENABLE ROW LEVEL SECURITY;

-- SELECT: Users can read comments if they have access to yacht
CREATE POLICY "doc_comments_select"
ON public.doc_metadata_comments
FOR SELECT
USING (
    EXISTS (
        SELECT 1 FROM public.auth_users_roles aur
        WHERE aur.user_id = auth.uid()
        AND aur.yacht_id = doc_metadata_comments.yacht_id
    )
    AND deleted_at IS NULL
);

-- INSERT: Users can create comments on documents they can access
CREATE POLICY "doc_comments_insert"
ON public.doc_metadata_comments
FOR INSERT
WITH CHECK (
    EXISTS (
        SELECT 1 FROM public.auth_users_roles aur
        WHERE aur.user_id = auth.uid()
        AND aur.yacht_id = doc_metadata_comments.yacht_id
    )
    AND EXISTS (
        SELECT 1 FROM public.doc_metadata doc
        WHERE doc.id = doc_metadata_comments.document_id
        AND doc.yacht_id = doc_metadata_comments.yacht_id
        AND doc.deleted_at IS NULL
    )
    AND created_by = auth.uid()
);

-- UPDATE: Users can edit own comments OR same department OR admin
CREATE POLICY "doc_comments_update"
ON public.doc_metadata_comments
FOR UPDATE
USING (
    EXISTS (
        SELECT 1 FROM public.auth_users_roles aur
        WHERE aur.user_id = auth.uid()
        AND aur.yacht_id = doc_metadata_comments.yacht_id
    )
    AND deleted_at IS NULL
    AND (
        created_by = auth.uid()
        OR EXISTS (
            SELECT 1 FROM public.auth_users_roles aur
            WHERE aur.user_id = auth.uid()
            AND aur.yacht_id = doc_metadata_comments.yacht_id
            AND aur.role IN ('admin', 'chief_engineer')
        )
    )
)
WITH CHECK (
    updated_by = auth.uid()
);

-- =====================================================
-- Trigger: Auto-populate Department
-- =====================================================

CREATE OR REPLACE FUNCTION public.trg_populate_doc_comment_department()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_user_role VARCHAR(100);
BEGIN
    -- Get user's primary role
    SELECT role INTO v_user_role
    FROM public.auth_users_roles
    WHERE user_id = NEW.created_by
    AND yacht_id = NEW.yacht_id
    LIMIT 1;

    -- Map role to department
    NEW.author_department := CASE
        WHEN v_user_role IN ('chief_engineer', 'engineer', 'technical_crew') THEN 'technical'
        WHEN v_user_role IN ('captain', 'officer', 'deckhand') THEN 'deck'
        WHEN v_user_role IN ('chief_steward', 'stewardess') THEN 'interior'
        WHEN v_user_role = 'chef' THEN 'galley'
        ELSE 'technical'
    END;

    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_populate_doc_comment_department_before_insert
BEFORE INSERT ON public.doc_metadata_comments
FOR EACH ROW
EXECUTE FUNCTION public.trg_populate_doc_comment_department();

COMMENT ON TABLE public.doc_metadata_comments IS
'Threaded comments on documents with department-based RLS.
Mirrors pms_attachment_comments pattern for Document Lens.
Created 2026-01-30.';
```

#### Step 1.2: Create Comment Handler

**File:** `apps/api/handlers/document_comment_handlers.py`

```python
"""
Document Comment Handlers
==========================

Handlers for document comment actions (Document Lens v2).

ACTIONS:
- add_document_comment: Add comment to document
- update_document_comment: Edit own comment
- delete_document_comment: Soft-delete comment
- list_document_comments: Get comments for document (with threading)
"""

from datetime import datetime, timezone
from typing import Dict, Optional, List
import logging

from actions.action_response_schema import ResponseBuilder

logger = logging.getLogger(__name__)


class DocumentCommentHandlers:
    """Document comment domain handlers."""

    def __init__(self, supabase_client):
        self.db = supabase_client

    async def add_document_comment(
        self,
        document_id: str,
        yacht_id: str,
        user_id: str,
        comment: str,
        parent_comment_id: Optional[str] = None,
    ) -> Dict:
        """
        Add comment to document.

        Args:
            document_id: UUID of document
            yacht_id: UUID of yacht
            user_id: UUID of user
            comment: Comment text
            parent_comment_id: Optional parent comment for threading

        Returns:
            ActionResponseEnvelope with comment_id
        """
        builder = ResponseBuilder("add_document_comment", document_id, "document", yacht_id)

        try:
            # Validate document exists and not deleted
            doc_result = self.db.table("doc_metadata").select("id, deleted_at").eq(
                "id", document_id
            ).eq("yacht_id", yacht_id).maybe_single().execute()

            if not doc_result or not doc_result.data:
                builder.set_error("NOT_FOUND", f"Document not found: {document_id}")
                return builder.build()

            if doc_result.data.get("deleted_at"):
                builder.set_error("INVALID_STATE", "Cannot comment on deleted document")
                return builder.build()

            # Validate parent comment if provided
            if parent_comment_id:
                parent_result = self.db.table("doc_metadata_comments").select("id").eq(
                    "id", parent_comment_id
                ).eq("document_id", document_id).maybe_single().execute()

                if not parent_result or not parent_result.data:
                    builder.set_error("NOT_FOUND", f"Parent comment not found: {parent_comment_id}")
                    return builder.build()

            # Create comment
            comment_data = {
                "yacht_id": yacht_id,
                "document_id": document_id,
                "comment": comment,
                "created_by": user_id,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "parent_comment_id": parent_comment_id,
            }

            result = self.db.table("doc_metadata_comments").insert(comment_data).execute()

            if not result.data:
                builder.set_error("INTERNAL_ERROR", "Failed to create comment")
                return builder.build()

            comment_id = result.data[0]["id"]

            builder.set_data({
                "comment_id": comment_id,
                "document_id": document_id,
                "created_at": comment_data["created_at"],
            })

            return builder.build()

        except Exception as e:
            logger.error(f"add_document_comment failed: {e}", exc_info=True)
            builder.set_error("INTERNAL_ERROR", str(e))
            return builder.build()

    async def list_document_comments(
        self,
        document_id: str,
        yacht_id: str,
        include_threads: bool = True,
    ) -> Dict:
        """
        List comments for document.

        Args:
            document_id: UUID of document
            yacht_id: UUID of yacht
            include_threads: If True, include threaded replies

        Returns:
            ActionResponseEnvelope with comments array
        """
        builder = ResponseBuilder("list_document_comments", document_id, "document", yacht_id)

        try:
            # Get all comments for document
            query = self.db.table("doc_metadata_comments").select(
                "id, comment, created_by, created_at, updated_at, parent_comment_id, author_department"
            ).eq("document_id", document_id).eq("yacht_id", yacht_id).is_(
                "deleted_at", "null"
            ).order("created_at", desc=False)

            result = query.execute()
            comments = result.data or []

            # Build threaded structure if requested
            if include_threads:
                comments = self._build_comment_tree(comments)

            builder.set_data({
                "document_id": document_id,
                "comments": comments,
                "total_count": len(comments),
            })

            return builder.build()

        except Exception as e:
            logger.error(f"list_document_comments failed: {e}", exc_info=True)
            builder.set_error("INTERNAL_ERROR", str(e))
            return builder.build()

    def _build_comment_tree(self, comments: List[Dict]) -> List[Dict]:
        """Build threaded comment tree."""
        comment_map = {c["id"]: {**c, "replies": []} for c in comments}
        root_comments = []

        for comment in comments:
            if comment.get("parent_comment_id"):
                parent = comment_map.get(comment["parent_comment_id"])
                if parent:
                    parent["replies"].append(comment_map[comment["id"]])
            else:
                root_comments.append(comment_map[comment["id"]])

        return root_comments
```

---

### Phase 2: Processing Hooks (OCR + Extraction)

#### Step 2.1: Create Document Upload Endpoint

**File:** `apps/api/routes/document_upload.py`

**Pattern:** Clone `receiving_upload.py` for documents

```python
"""
Document Upload Proxy
Proxies multipart file uploads to image-processing service with Authorization JWT
"""
import os
import logging
from typing import Optional
from fastapi import APIRouter, File, Form, UploadFile, Header, HTTPException, status
import httpx

from middleware.auth import get_authenticated_user
from handlers.document_handlers import DocumentHandlers

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/documents", tags=["document_upload"])

IMAGE_PROCESSOR_URL = os.getenv("IMAGE_PROCESSOR_URL", "https://image-processing-givq.onrender.com")
PROXY_TIMEOUT = 30.0


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    doc_type: str = Form("manual"),  # manual, drawing, certificate, etc.
    title: Optional[str] = Form(None),
    oem: Optional[str] = Form(None),
    notes: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),  # Comma-separated
    authorization: str = Header(...),
):
    """
    Upload document with OCR and entity extraction.

    Flow:
    1. Validate JWT and extract user context
    2. Create doc_metadata record (metadata only)
    3. Upload file to Supabase Storage (documents bucket)
    4. If PDF/image: Proxy to image-processing for OCR
    5. Queue extraction job for entity extraction
    6. Return immediately with signed URL

    Args:
        file: Uploaded file (PDF, image, etc.)
        doc_type: Document type (manual, drawing, certificate, etc.)
        title: Human-readable title
        oem: OEM/manufacturer
        notes: Upload notes
        tags: Comma-separated tags
        authorization: Authorization: Bearer <JWT> header

    Returns:
        JSON response with document_id and signed_url
    """
    # Extract JWT
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header",
        )

    jwt_token = authorization.split(" ", 1)[1]

    # Get user context (yacht_id, user_id from JWT)
    try:
        user_context = await get_authenticated_user(jwt_token)
        yacht_id = user_context["yacht_id"]
        user_id = user_context["user_id"]
    except Exception as e:
        logger.error(f"JWT validation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired JWT",
        )

    # Create document metadata record
    from integrations.supabase import get_supabase_client
    db = get_supabase_client()
    handlers = DocumentHandlers(db)

    # Call existing upload_document handler
    tags_list = [t.strip() for t in tags.split(",")] if tags else []

    upload_result = await handlers._upload_document_adapter()({
        "yacht_id": yacht_id,
        "user_id": user_id,
        "file_name": file.filename,
        "mime_type": file.content_type,
        "title": title,
        "doc_type": doc_type,
        "oem": oem,
        "notes": notes,
        "tags": tags_list,
    })

    if upload_result.get("status") != "success":
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create document metadata",
        )

    document_id = upload_result["document_id"]
    storage_path = upload_result["storage_path"]

    # Upload file to Supabase Storage
    file_content = await file.read()
    storage_client = db.storage.from_("documents")

    try:
        storage_client.upload(
            path=storage_path,
            file=file_content,
            file_options={"content-type": file.content_type}
        )
    except Exception as e:
        logger.error(f"Storage upload failed: {e}")
        # Cleanup metadata record
        db.table("doc_metadata").delete().eq("id", document_id).execute()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload file to storage",
        )

    # If PDF or image, proxy to image-processing for OCR
    extracted_text = None
    if file.content_type in ("application/pdf", "image/jpeg", "image/png"):
        try:
            async with httpx.AsyncClient(timeout=PROXY_TIMEOUT) as client:
                ocr_response = await client.post(
                    f"{IMAGE_PROCESSOR_URL}/api/v1/images/upload",
                    files={"file": (file.filename, file_content, file.content_type)},
                    data={
                        "upload_type": "document",
                        "entity_type": "document",
                        "entity_id": document_id,
                        "doc_type": doc_type,
                    },
                    headers={"Authorization": authorization}
                )

                if ocr_response.status_code == 200:
                    ocr_data = ocr_response.json()
                    extracted_text = ocr_data.get("extracted_text")
        except Exception as e:
            logger.warning(f"OCR processing failed (non-blocking): {e}")

    # Queue extraction job for entity extraction
    if extracted_text:
        job_data = {
            "yacht_id": yacht_id,
            "job_type": "document_ingestion",
            "priority": "user_upload",  # High priority
            "entity_type": "document",
            "entity_id": document_id,
            "payload": {
                "document_id": document_id,
                "storage_path": storage_path,
                "extracted_text": extracted_text,
                "mime_type": file.content_type,
                "doc_type": doc_type,
            },
            "status": "pending",
        }

        try:
            db.table("extraction_jobs").insert(job_data).execute()
        except Exception as e:
            logger.warning(f"Failed to queue extraction job (non-blocking): {e}")

    # Generate signed URL for immediate display
    from actions.action_response_schema import SignedUrlGenerator
    url_generator = SignedUrlGenerator(db)

    signed_url = url_generator.create_signed_url(
        "documents", storage_path, expires_in=3600
    )

    return {
        "status": "success",
        "document_id": document_id,
        "filename": file.filename,
        "storage_path": storage_path,
        "signed_url": signed_url,
        "extracted_text": extracted_text,
        "processing_status": "queued" if extracted_text else "completed",
    }


@router.post("/{document_id}/comment")
async def add_document_comment_endpoint(
    document_id: str,
    comment: str = Form(...),
    parent_comment_id: Optional[str] = Form(None),
    authorization: str = Header(...),
):
    """Add comment to document."""
    jwt_token = authorization.split(" ", 1)[1]

    try:
        user_context = await get_authenticated_user(jwt_token)
        yacht_id = user_context["yacht_id"]
        user_id = user_context["user_id"]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired JWT",
        )

    from integrations.supabase import get_supabase_client
    from handlers.document_comment_handlers import DocumentCommentHandlers

    db = get_supabase_client()
    handlers = DocumentCommentHandlers(db)

    result = await handlers.add_document_comment(
        document_id=document_id,
        yacht_id=yacht_id,
        user_id=user_id,
        comment=comment,
        parent_comment_id=parent_comment_id,
    )

    if result.get("status") == "error":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("message"),
        )

    return result
```

#### Step 2.2: Extend Image-Processing Service

**Same as work order lens:**

Add `upload_type: "document"` to image-processing service.

**PR to shortalex12333/Image-processing:**

```python
# src/routes/upload_routes.py

upload_type: Annotated[
    Literal[
        "receiving", "shipping_label", "discrepancy", "part_photo", "finance",
        "work_order", "fault", "equipment",
        "document"  # ← NEW
    ],
    Form(description="Type of upload")
],

# Route logic:
if upload_type == "document":
    # Don't write to pms_image_uploads (that's for receiving)
    # Don't write to pms_attachments (that's for work orders/faults)
    # OCR only - return extracted_text
    # Cloud_PMS handles doc_metadata write

    return {
        "document_id": entity_id,
        "extracted_text": extracted_text,
        "status": "completed"
    }
```

---

### Phase 3: Extraction Worker Integration

#### Step 3.1: Create extraction_jobs Table

**Migration:** `20260130_112_create_extraction_jobs_table.sql`

**Pattern:** Same as work order lens (see `docs/UPLOAD_PROCESSING_WORKFLOW.md`)

```sql
CREATE TABLE IF NOT EXISTS public.extraction_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    yacht_id UUID NOT NULL,
    job_type VARCHAR(50) NOT NULL,  -- 'document_ingestion', 'attachment_ingestion', 'email_embedding'
    priority VARCHAR(20) NOT NULL,  -- 'user_upload', 'background', 'low'
    entity_type VARCHAR(50),        -- 'document', 'work_order', 'email'
    entity_id UUID,
    payload JSONB NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    attempts INT DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    completed_by VARCHAR(100),
    error TEXT,
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX idx_extraction_jobs_queue ON public.extraction_jobs(status, priority, created_at)
    WHERE status = 'pending';
```

#### Step 3.2: Add Document Ingestion Handler to Worker

**File:** `apps/api/workers/extraction_worker.py`

```python
class ExtractionWorker:
    """Processes extraction_jobs with weighted fair queuing."""

    async def process_document_ingestion(self, job: Dict):
        """
        Process document for entity extraction and GraphRAG.

        Job payload:
        - document_id: UUID
        - extracted_text: OCR text
        - doc_type: manual, drawing, etc.
        - mime_type: application/pdf, etc.
        """
        payload = job["payload"]
        document_id = payload["document_id"]
        extracted_text = payload["extracted_text"]

        # Use existing extraction pipeline
        from extraction.orchestrator import ExtractionOrchestrator

        orchestrator = ExtractionOrchestrator()
        entities = orchestrator.extract(extracted_text)

        # Update doc_metadata with extraction results
        await self.db.table("doc_metadata").update({
            "related_text": extracted_text,  # For full-text search
            "metadata": {
                **payload.get("metadata", {}),
                "entities_extracted": entities,
                "extraction_completed_at": datetime.now(timezone.utc).isoformat(),
            }
        }).eq("id", document_id).execute()

        # TODO: Populate GraphRAG with entities
        # await self.populate_graph(document_id, entities)

        logger.info(f"Document ingestion completed: {document_id}")
```

---

## Comparison Table

| Feature | Work Order Lens | Document Lens | Status |
|---------|----------------|---------------|---------|
| **Metadata Table** | pms_attachments | doc_metadata | ✅ Exists |
| **Comments Table** | pms_attachment_comments | doc_metadata_comments | ❌ Need to create |
| **Storage Bucket** | pms-work-order-attachments | documents | ✅ Exists |
| **Upload Handler** | add_work_order_photo | upload_document | ✅ Exists (metadata only) |
| **Upload Endpoint** | /api/work_orders/{id}/upload | /api/documents/upload | ❌ Need to create |
| **OCR Integration** | Proxy to image-processing | Proxy to image-processing | ❌ Need to add |
| **Extraction Queue** | extraction_jobs (attachment_ingestion) | extraction_jobs (document_ingestion) | ❌ Need to create |
| **Extraction Worker** | ExtractionWorker.process_attachment_ingestion | ExtractionWorker.process_document_ingestion | ❌ Need to add |
| **Department RLS** | author_department column | author_department column | ❌ Need to add |
| **Comment Threading** | parent_comment_id | parent_comment_id | ❌ Need to add |
| **Soft Delete** | deleted_at | deleted_at | ✅ Exists (added 2026-01-28) |

---

## Migration Sequence

```bash
# 1. Comments table
psql $SUPABASE_DB_URL < supabase/migrations/20260130_111_create_doc_metadata_comments_table.sql

# 2. Extraction jobs table
psql $SUPABASE_DB_URL < supabase/migrations/20260130_112_create_extraction_jobs_table.sql

# 3. Verify
psql $SUPABASE_DB_URL -c "SELECT tablename FROM pg_tables WHERE tablename LIKE 'doc_%' OR tablename = 'extraction_jobs';"
```

---

## Implementation Checklist

### Phase 1: Comments (Day 1)
- [ ] Create migration 111 (doc_metadata_comments table)
- [ ] Apply migration to production
- [ ] Create document_comment_handlers.py
- [ ] Register handlers in action router
- [ ] Test: Add comment to document
- [ ] Test: List comments with threading
- [ ] Test: Department RLS (technical can't edit deck comments)

### Phase 2: Upload & OCR (Day 2)
- [ ] Create document_upload.py endpoint
- [ ] Register route in pipeline_service.py
- [ ] Test: Upload PDF → metadata created
- [ ] Test: Upload PDF → file in storage
- [ ] Submit PR to Image-processing (add "document" type)
- [ ] Test: Upload PDF → OCR returns text
- [ ] Verify: extracted_text returned in response

### Phase 3: Extraction Queue (Day 3)
- [ ] Create migration 112 (extraction_jobs table)
- [ ] Apply migration to production
- [ ] Add process_document_ingestion to extraction_worker.py
- [ ] Test: Upload PDF → job queued
- [ ] Deploy extraction worker to Render
- [ ] Test: Worker polls and processes job
- [ ] Verify: doc_metadata.related_text updated
- [ ] Verify: Entities extracted to metadata

### Phase 4: Frontend Integration (Day 4)
- [ ] Add upload button to DocumentCard component
- [ ] File picker with multipart upload
- [ ] Display signed URLs for documents
- [ ] Show extraction status (queued/processing/completed)
- [ ] Comment UI on document detail view
- [ ] Thread display with nesting

---

## Code References

### Work Order Lens (Reference Implementation)
```
apps/api/handlers/work_order_handlers.py:323  (bucket routing)
apps/api/handlers/p2_mutation_light_handlers.py:417  (add_work_order_photo)
apps/api/routes/receiving_upload.py  (proxy pattern)
supabase/migrations/20260130_110_create_attachment_comments_table.sql  (comments)
docs/UPLOAD_PROCESSING_WORKFLOW.md  (queue strategy)
```

### Document Lens (Target Files)
```
apps/api/handlers/document_handlers.py  (existing handlers)
apps/api/routes/document_upload.py  (NEW - upload endpoint)
apps/api/handlers/document_comment_handlers.py  (NEW - comment handlers)
apps/api/workers/extraction_worker.py  (NEW - add document_ingestion)
```

---

## Testing Workflow

### Test 1: Upload with Comments
```bash
# 1. Upload document
curl -X POST 'http://localhost:8000/api/documents/upload' \
  -H "Authorization: Bearer $JWT" \
  -F "file=@hydraulic_manual.pdf" \
  -F "doc_type=manual" \
  -F "title=Hydraulic System Manual" \
  -F "oem=Caterpillar"

# Response:
{
  "document_id": "uuid",
  "signed_url": "https://...",
  "extracted_text": "...",
  "processing_status": "queued"
}

# 2. Add comment
curl -X POST 'http://localhost:8000/api/documents/{uuid}/comment' \
  -H "Authorization: Bearer $JWT" \
  -d "comment=Pages 45-52 cover troubleshooting"

# 3. List comments
curl -X GET 'http://localhost:8000/api/documents/{uuid}/comments' \
  -H "Authorization: Bearer $JWT"
```

### Test 2: Extraction Pipeline
```bash
# 1. Check extraction job created
psql $SUPABASE_DB_URL -c "SELECT * FROM extraction_jobs WHERE entity_id='$DOC_ID';"

# 2. Watch worker logs
tail -f /var/log/extraction_worker.log

# 3. Verify completion
psql $SUPABASE_DB_URL -c "SELECT metadata FROM doc_metadata WHERE id='$DOC_ID';"

# Should show:
{
  "entities_extracted": {
    "parts": ["hydraulic_pump", "seal_kit"],
    "procedures": ["bleeding_hydraulics"],
    ...
  },
  "extraction_completed_at": "2026-01-30T12:00:00Z"
}
```

---

## Summary

**What You're Building:**
- Comments on documents (like notes on photos in work orders)
- OCR extraction on upload (automatic text extraction)
- Entity extraction queue (find parts, procedures, specs)
- GraphRAG integration (make documents searchable by AI)

**Pattern:**
- Clone Work Order Lens infrastructure
- Use same queue, RLS, threading
- Integrate with existing extraction service

**Timeline:**
- Day 1: Comments table + handlers
- Day 2: Upload endpoint + OCR
- Day 3: Extraction queue + worker
- Day 4: Frontend integration

**Result:**
Users can:
1. Upload equipment manual PDF
2. See OCR text immediately
3. Comment: "Section 3.2 has troubleshooting"
4. Search by extracted entities (parts, procedures)
5. RAG queries: "How do I bleed the hydraulics?" → finds relevant manual section

Ready to start! 🚀
