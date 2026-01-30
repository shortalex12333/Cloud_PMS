# Document Lens - Copy Guide (What to Clone)

**Pattern:** Copy Work Order Lens → Adapt for Document Lens

---

## File-by-File Copy Instructions

### 1. Comments Table Migration

**COPY FROM:**
```
supabase/migrations/20260130_110_create_attachment_comments_table.sql
```

**CREATE AS:**
```
supabase/migrations/20260130_111_create_doc_metadata_comments_table.sql
```

**FIND/REPLACE:**
```
pms_attachment_comments    → doc_metadata_comments
pms_attachments            → doc_metadata
attachment_id              → document_id
"Attachment comments"      → "Document comments"
"attachment"               → "document"
```

**KEEP SAME:**
- RLS policies structure
- Department auto-populate trigger
- Threading (parent_comment_id)
- Soft delete pattern

---

### 2. Comment Handlers

**COPY FROM:**
```
(Work order lens doesn't have separate comment handlers yet)
```

**CREATE AS:**
```
apps/api/handlers/document_comment_handlers.py
```

**TEMPLATE:**
```python
class DocumentCommentHandlers:
    def __init__(self, supabase_client):
        self.db = supabase_client

    async def add_document_comment(self, document_id, yacht_id, user_id, comment, parent_comment_id=None):
        # Validate document exists
        # Create comment record
        # Return comment_id

    async def list_document_comments(self, document_id, yacht_id):
        # Query comments
        # Build threaded structure
        # Return comment tree

    async def update_document_comment(self, comment_id, yacht_id, user_id, comment):
        # Check ownership or admin
        # Update comment
        # Return success

    async def delete_document_comment(self, comment_id, yacht_id, user_id):
        # Soft delete (set deleted_at)
        # Return success
```

---

### 3. Upload Endpoint

**COPY FROM:**
```
apps/api/routes/receiving_upload.py
```

**CREATE AS:**
```
apps/api/routes/document_upload.py
```

**FIND/REPLACE:**
```
/api/receiving/{receiving_id}/upload  → /api/documents/upload
receiving_id                          → document_id
pms_receiving                         → doc_metadata
upload_type: "receiving"              → upload_type: "document"
doc_type                              → doc_type (keep same)
comment                               → notes
```

**KEY CHANGES:**
```python
# BEFORE (receiving):
bucket_name = "receiving"
table_name = "pms_image_uploads"

# AFTER (document):
bucket_name = "documents"
table_name = "doc_metadata"

# BEFORE (receiving):
storage_path = f"{yacht_id}/receiving/{receiving_id}/{filename}"

# AFTER (document):
storage_path = f"{yacht_id}/documents/{document_id}/{filename}"
```

---

### 4. Extraction Worker Method

**COPY FROM:**
```
(Planned in docs/UPLOAD_PROCESSING_WORKFLOW.md)
process_attachment_ingestion()
```

**ADD TO:**
```
apps/api/workers/extraction_worker.py
```

**TEMPLATE:**
```python
async def process_document_ingestion(self, job: Dict):
    """
    Process document for entity extraction and GraphRAG.

    Job payload:
    - document_id: UUID
    - extracted_text: OCR text
    - doc_type: manual, drawing, etc.
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
        "related_text": extracted_text,
        "metadata": {
            **payload.get("metadata", {}),
            "entities_extracted": entities,
            "extraction_completed_at": datetime.now(timezone.utc).isoformat(),
        }
    }).eq("id", document_id).execute()

    logger.info(f"Document ingestion completed: {document_id}")
```

**FIND/REPLACE:**
```
process_attachment_ingestion  → process_document_ingestion
pms_attachments               → doc_metadata
attachment_id                 → document_id
```

---

### 5. Extraction Jobs Table

**COPY FROM:**
```
(Planned in docs/UPLOAD_PROCESSING_WORKFLOW.md)
extraction_jobs table spec
```

**CREATE AS:**
```
supabase/migrations/20260130_112_create_extraction_jobs_table.sql
```

**NO CHANGES NEEDED:**
- Table supports both attachment_ingestion AND document_ingestion
- job_type column distinguishes between them
- Same priority queue strategy

---

### 6. Frontend Component (Pseudocode)

**COPY FROM:**
```
(Planned) WorkOrderCard.tsx upload logic
```

**CREATE AS:**
```
apps/web/src/components/cards/DocumentCard.tsx
```

**TEMPLATE:**
```typescript
// Upload button
<input
  type="file"
  accept=".pdf,.jpg,.png"
  onChange={handleFileUpload}
/>

async function handleFileUpload(e: React.ChangeEvent<HTMLInputElement>) {
  const file = e.target.files?.[0];
  if (!file) return;

  const formData = new FormData();
  formData.append('file', file);
  formData.append('doc_type', selectedDocType);  // manual, drawing, etc.
  formData.append('oem', oem);
  formData.append('notes', notes);

  const response = await fetch('/api/documents/upload', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${jwtToken}`,
    },
    body: formData,
  });

  const result = await response.json();

  // Display document
  setDocuments([...documents, {
    id: result.document_id,
    filename: result.filename,
    url: result.signed_url,
    extractedText: result.extracted_text,
    status: result.processing_status,  // 'queued' | 'completed'
  }]);
}

// Comment thread component
<CommentThread
  documentId={document.id}
  comments={comments}
  onAddComment={handleAddComment}
/>
```

---

## Side-by-Side Comparison

### Table Names
| Work Order Lens | Document Lens |
|----------------|---------------|
| pms_attachments | doc_metadata |
| pms_attachment_comments | doc_metadata_comments |
| extraction_jobs | extraction_jobs (same) |

### Column Names
| Work Order Lens | Document Lens |
|----------------|---------------|
| attachment_id | document_id |
| entity_type: 'work_order' | entity_type: 'document' |
| entity_id: work_order_id | entity_id: document_id |
| category: 'photo' | doc_type: 'manual' |
| description | notes |

### Storage Paths
| Work Order Lens | Document Lens |
|----------------|---------------|
| {yacht_id}/{work_order_id}/{filename} | {yacht_id}/documents/{document_id}/{filename} |
| pms-work-order-attachments bucket | documents bucket |

### Handler Names
| Work Order Lens | Document Lens |
|----------------|---------------|
| add_work_order_photo | upload_document |
| add_attachment_comment | add_document_comment |
| list_attachment_comments | list_document_comments |

### Job Types
| Work Order Lens | Document Lens |
|----------------|---------------|
| attachment_ingestion | document_ingestion |
| entity_type: work_order | entity_type: document |

---

## Step-by-Step Clone Process

### Step 1: Clone Comments Migration
```bash
# Copy file
cp supabase/migrations/20260130_110_create_attachment_comments_table.sql \
   supabase/migrations/20260130_111_create_doc_metadata_comments_table.sql

# Find/replace in new file
sed -i 's/pms_attachment_comments/doc_metadata_comments/g' \
    supabase/migrations/20260130_111_create_doc_metadata_comments_table.sql
sed -i 's/pms_attachments/doc_metadata/g' \
    supabase/migrations/20260130_111_create_doc_metadata_comments_table.sql
sed -i 's/attachment_id/document_id/g' \
    supabase/migrations/20260130_111_create_doc_metadata_comments_table.sql
```

### Step 2: Clone Upload Route
```bash
# Copy file
cp apps/api/routes/receiving_upload.py \
   apps/api/routes/document_upload.py

# Manual edits needed:
# - Change prefix to /api/documents
# - Change table to doc_metadata
# - Change bucket to documents
# - Change upload_type to "document"
```

### Step 3: Create Comment Handlers
```bash
# Create new file (no direct copy)
# Use template from this guide
touch apps/api/handlers/document_comment_handlers.py
```

### Step 4: Extend Worker
```bash
# Edit existing file
vim apps/api/workers/extraction_worker.py

# Add new method: process_document_ingestion()
# Register job_type: "document_ingestion"
```

---

## Testing Checklist (After Cloning)

```bash
# 1. Migrations applied
psql $SUPABASE_DB_URL -c "\dt doc_metadata_comments extraction_jobs"

# 2. Upload works
curl -X POST 'http://localhost:8000/api/documents/upload' \
  -H "Authorization: Bearer $JWT" \
  -F "file=@test.pdf" \
  -F "doc_type=manual"

# 3. Comment works
curl -X POST 'http://localhost:8000/api/documents/{id}/comment' \
  -H "Authorization: Bearer $JWT" \
  -d "comment=Test comment"

# 4. Job queued
psql $SUPABASE_DB_URL -c "SELECT * FROM extraction_jobs WHERE entity_type='document';"

# 5. Worker processes
tail -f /var/log/extraction_worker.log | grep document_ingestion
```

---

## Common Mistakes to Avoid

### ❌ Wrong: Mixing table names
```python
# Don't do this:
db.table("pms_attachments").insert({
    "document_id": doc_id  # Wrong table!
})
```

### ✅ Right: Consistent naming
```python
db.table("doc_metadata").insert({
    "document_id": doc_id
})
```

### ❌ Wrong: Using attachment bucket
```python
bucket_name = "pms-work-order-attachments"  # Wrong bucket!
```

### ✅ Right: Using documents bucket
```python
bucket_name = "documents"
```

### ❌ Wrong: Wrong job type
```python
job_type = "attachment_ingestion"  # Wrong for documents!
```

### ✅ Right: Correct job type
```python
job_type = "document_ingestion"
```

---

## Quick Reference Card

```
┌──────────────────────────────────────────────────┐
│         WORK ORDER → DOCUMENT MAPPING            │
├──────────────────────────────────────────────────┤
│ pms_attachments          → doc_metadata          │
│ pms_attachment_comments  → doc_metadata_comments │
│ attachment_id            → document_id           │
│ entity_type: work_order  → entity_type: document │
│ pms-work-order-*         → documents bucket      │
│ attachment_ingestion     → document_ingestion    │
│ add_work_order_photo     → upload_document       │
│ category: photo          → doc_type: manual      │
│ description              → notes                 │
└──────────────────────────────────────────────────┘
```

---

## Summary

**Clone These Files:**
1. ✅ Comments migration (110 → 111)
2. ✅ Upload route (receiving_upload → document_upload)
3. ✅ Worker method (add process_document_ingestion)

**Find/Replace:**
- pms_attachments → doc_metadata
- attachment_id → document_id
- entity_type: work_order → entity_type: document
- pms-work-order-attachments → documents

**Don't Copy:**
- Bucket creation migration (documents bucket already exists)
- Handler base class (document_handlers.py already exists)

Ready to clone! Start with comments migration 🚀
