# Document Lens - Quick Start (Mirror Work Order Lens)

**For:** Engineer working on Document Lens integration
**Pattern:** Copy Work Order Lens V2 infrastructure

---

## What You're Building

Apply Work Order Lens attachment pattern to Document Lens:
- ✅ Comments ON documents (threaded conversations)
- ✅ OCR on upload (automatic text extraction)
- ✅ Entity extraction queue (find parts, procedures)
- ✅ Department-based RLS (technical crew can't edit deck comments)

---

## Current State

**Already Exists:**
- `doc_metadata` table (like pms_attachments)
- `documents` storage bucket
- Upload handlers (metadata only)
- Soft delete support

**Missing:**
- Comments table
- OCR integration
- Extraction queue
- Processing hooks

---

## Implementation (4 Days)

### Day 1: Comments Infrastructure

**Create:** `doc_metadata_comments` table (mirrors `pms_attachment_comments`)

```sql
-- Migration: 20260130_111_create_doc_metadata_comments_table.sql
CREATE TABLE doc_metadata_comments (
    id UUID PRIMARY KEY,
    document_id UUID REFERENCES doc_metadata(id),
    comment TEXT NOT NULL,
    created_by UUID NOT NULL,
    author_department VARCHAR(100),  -- Auto-populated
    parent_comment_id UUID,  -- Threading
    deleted_at TIMESTAMPTZ,
    ...
);
```

**Create:** `document_comment_handlers.py`
- add_document_comment
- list_document_comments (with threading)
- update_document_comment
- delete_document_comment

**Test:**
```bash
# Add comment
POST /api/documents/{id}/comment
Body: { "comment": "Pages 45-52 cover hydraulic specs" }

# List comments
GET /api/documents/{id}/comments
```

---

### Day 2: Upload & OCR

**Create:** `apps/api/routes/document_upload.py`

**Pattern:** Clone `receiving_upload.py`

```python
@router.post("/upload")
async def upload_document(file: UploadFile, doc_type: str, ...):
    # 1. Create doc_metadata record
    # 2. Upload to Supabase Storage (documents bucket)
    # 3. Proxy to image-processing for OCR
    # 4. Return signed URL + extracted_text
```

**Flow:**
```
User uploads PDF
  → Create doc_metadata record
  → Upload to storage
  → Proxy to image-processing (OCR)
  → Queue extraction job
  → Return immediately
```

**Test:**
```bash
curl -X POST 'http://localhost:8000/api/documents/upload' \
  -H "Authorization: Bearer $JWT" \
  -F "file=@manual.pdf" \
  -F "doc_type=manual" \
  -F "oem=Caterpillar"

# Response:
{
  "document_id": "uuid",
  "signed_url": "https://...",
  "extracted_text": "...",
  "processing_status": "queued"
}
```

---

### Day 3: Extraction Queue

**Create:** `extraction_jobs` table

```sql
-- Migration: 20260130_112_create_extraction_jobs_table.sql
CREATE TABLE extraction_jobs (
    id UUID PRIMARY KEY,
    job_type VARCHAR(50),  -- 'document_ingestion'
    priority VARCHAR(20),  -- 'user_upload', 'background'
    entity_type VARCHAR(50),  -- 'document'
    entity_id UUID,
    payload JSONB,
    status VARCHAR(20),  -- 'pending', 'processing', 'completed'
    ...
);
```

**Add to Worker:** `apps/api/workers/extraction_worker.py`

```python
async def process_document_ingestion(self, job: Dict):
    """Extract entities from document text."""
    payload = job["payload"]
    document_id = payload["document_id"]
    extracted_text = payload["extracted_text"]

    # Use existing extraction pipeline
    from extraction.orchestrator import ExtractionOrchestrator
    orchestrator = ExtractionOrchestrator()
    entities = orchestrator.extract(extracted_text)

    # Update doc_metadata
    await self.db.table("doc_metadata").update({
        "related_text": extracted_text,
        "metadata": {"entities_extracted": entities}
    }).eq("id", document_id).execute()
```

**Queue Strategy:** Weighted fair queuing (60% user uploads, 30% background)

**Test:**
```bash
# Check job queued
SELECT * FROM extraction_jobs WHERE entity_id='$DOC_ID';

# Watch worker process
tail -f /var/log/extraction_worker.log

# Verify completion
SELECT metadata FROM doc_metadata WHERE id='$DOC_ID';
```

---

### Day 4: Frontend Integration

**Add to DocumentCard.tsx:**
```typescript
// Upload button
<input type="file" onChange={handleUpload} />

async function handleUpload(file: File) {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('doc_type', 'manual');

  const res = await fetch('/api/documents/upload', {
    method: 'POST',
    headers: { 'Authorization': `Bearer ${jwt}` },
    body: formData
  });

  const { signed_url, document_id } = await res.json();
  // Display document with signed URL
}

// Comment input
<CommentThread documentId={documentId} />
```

---

## File Checklist

### Migrations
```
[ ] supabase/migrations/20260130_111_create_doc_metadata_comments_table.sql
[ ] supabase/migrations/20260130_112_create_extraction_jobs_table.sql
```

### Handlers
```
[ ] apps/api/handlers/document_comment_handlers.py (NEW)
[ ] apps/api/handlers/document_handlers.py (UPDATE - existing)
```

### Routes
```
[ ] apps/api/routes/document_upload.py (NEW)
```

### Workers
```
[ ] apps/api/workers/extraction_worker.py (ADD process_document_ingestion)
```

### Frontend
```
[ ] apps/web/src/components/cards/DocumentCard.tsx (UPDATE)
[ ] apps/web/src/components/comments/CommentThread.tsx (NEW)
```

---

## Reference Implementation

**Work Order Lens (Copy from here):**
```
supabase/migrations/20260130_110_create_attachment_comments_table.sql
apps/api/routes/receiving_upload.py
apps/api/handlers/work_order_handlers.py
docs/UPLOAD_PROCESSING_WORKFLOW.md
```

**Full Plan:**
See `DOCUMENT_LENS_INFRASTRUCTURE_PLAN.md` for detailed specs

---

## Key Differences: Document vs Work Order

| Aspect | Work Order | Document |
|--------|-----------|----------|
| **Table** | pms_attachments | doc_metadata |
| **Bucket** | pms-work-order-attachments | documents |
| **Entity** | Polymorphic (work_order, fault) | Single (document) |
| **Upload** | Linked to entity (work_order_id) | Standalone |
| **Comments** | pms_attachment_comments | doc_metadata_comments |
| **Use Case** | Photos of repairs | Equipment manuals, drawings |

---

## Queue Priority Strategy

```
Extraction Worker Batch (10 jobs):
├─ 6 slots: user_upload (documents, attachments)
├─ 3 slots: background (emails, batch)
└─ 1 slot: low (cleanup)

Result:
✅ User document uploads process within 30-60s
✅ Background jobs not starved (30% capacity)
✅ No blocking
```

---

## Testing Flow

```bash
# 1. Upload document
POST /api/documents/upload → document_id, signed_url

# 2. Check extraction queued
SELECT * FROM extraction_jobs WHERE entity_id='$DOC_ID';

# 3. Worker processes (~30-60s)
Watch logs: extraction_worker.log

# 4. Add comment
POST /api/documents/{id}/comment → comment_id

# 5. List comments with threading
GET /api/documents/{id}/comments → [{comment, replies: [...]}]

# 6. Verify entities extracted
SELECT metadata FROM doc_metadata WHERE id='$DOC_ID';
→ {"entities_extracted": {"parts": [...], "procedures": [...]}}
```

---

## Questions?

**Full Technical Spec:** `DOCUMENT_LENS_INFRASTRUCTURE_PLAN.md`
**Queue Strategy:** `docs/UPLOAD_PROCESSING_WORKFLOW.md`
**Work Order Reference:** PR #26 files

Ready to start! Day 1 = Comments table 🚀
