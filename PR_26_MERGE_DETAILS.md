# PR #26 - Attachment Infrastructure Ready for Merge

**Branch:** `fix/attachment-table-handlers`
**Latest Commit:** `34b083d`
**Status:** ✅ Ready for main
**Related Work:** Work Order Lens V2 Embeddings Phase 2

---

## What's Included

### 1. Critical Bug Fixes (Commit 3acedfd)

**Problem:** Attachment handlers wrote to wrong tables, causing photos to never appear.

**Fixed:**
- `add_work_order_photo`: Now writes to `pms_attachments` (was: `documents`)
- `add_fault_photo`: Now writes to `pms_attachments` (was: `pms_fault_attachments` - doesn't exist)

**Files:**
- `apps/api/handlers/p2_mutation_light_handlers.py`
- `apps/api/handlers/fault_mutation_handlers.py`

### 2. Entity-Based Storage Buckets (Commit 34b083d)

**New Buckets Created:**
```
pms-work-order-attachments   (50MB limit)
pms-fault-attachments         (50MB limit)
pms-equipment-attachments     (100MB limit - technical docs)
pms-checklist-attachments     (50MB limit)
```

**Benefits:**
- RLS policies mirror entity access patterns (yacht_id + department)
- Lifecycle management (delete entity → bulk delete bucket path)
- Storage analytics per entity type
- Path structure: `{yacht_id}/{entity_id}/{filename}`

**Migration:** `supabase/migrations/20260130_109_create_attachment_storage_buckets.sql`

### 3. Attachment Comments with Department RLS (Commit 34b083d)

**Table:** `pms_attachment_comments`

**Key Features:**
- Threaded comments on attachments
- **Department-based RLS:** User role must match entity department
- Prevents non-technical crew from overwriting technical notes
- Auto-populate `author_department` via trigger
- Threading support (`parent_comment_id` for nested replies)
- Soft delete support

**Use Case:** When user uploads "leak on starboard engine", they can comment directly ON the image instead of separate note saying "see image 4".

**Migration:** `supabase/migrations/20260130_110_create_attachment_comments_table.sql`

### 4. Handler Bucket Routing Updates (Commit 34b083d)

**Updated:** `_get_bucket_for_attachment()` in:
- `apps/api/handlers/work_order_handlers.py:323`
- `apps/api/handlers/fault_handlers.py:514`
- `apps/api/handlers/equipment_handlers.py:459`

**Logic:**
```python
# NEW (entity-based):
work_order → pms-work-order-attachments
fault → pms-fault-attachments
equipment → pms-equipment-attachments

# LEGACY (backwards compatibility):
old photos → pms-work-order-photos (read-only)
NAS docs → documents (separate system)
```

---

## Files Changed

```
✅ apps/api/handlers/p2_mutation_light_handlers.py  (table name fix)
✅ apps/api/handlers/fault_mutation_handlers.py     (table name fix)
✅ apps/api/handlers/work_order_handlers.py         (bucket routing)
✅ apps/api/handlers/fault_handlers.py              (bucket routing)
✅ apps/api/handlers/equipment_handlers.py          (bucket routing)
✅ supabase/migrations/20260130_109_create_attachment_storage_buckets.sql
✅ supabase/migrations/20260130_110_create_attachment_comments_table.sql
```

---

## Post-Merge Actions

### 1. Apply Migrations to Production

**Already Applied:**
- ✅ `20260130000001_add_category_to_pms_attachments.sql` (applied via psql)

**Need to Apply:**
```sql
-- Migration 109: Storage buckets
psql $SUPABASE_DB_URL < supabase/migrations/20260130_109_create_attachment_storage_buckets.sql

-- Migration 110: Comments table
psql $SUPABASE_DB_URL < supabase/migrations/20260130_110_create_attachment_comments_table.sql
```

**Verify:**
```sql
-- Check buckets created
SELECT id, name, public, file_size_limit
FROM storage.buckets
WHERE id LIKE 'pms-%attachments';

-- Check comments table
SELECT COUNT(*) FROM pms_attachment_comments;
```

### 2. Render Auto-Deploy

Once merged to `main`, Render will auto-deploy:
- Service: `pipeline-core.int.celeste7.ai`
- ETA: ~5-10 minutes
- Verify: Check `/health` endpoint after deployment

---

## What You Can Build On (After Merge)

### 1. Upload Endpoints

**Pattern:** Clone `apps/api/routes/receiving_upload.py` for each entity type.

**Needed:**
```python
POST /api/work_orders/{work_order_id}/upload
POST /api/faults/{fault_id}/upload
POST /api/equipment/{equipment_id}/upload
```

**Flow:**
```
User uploads file →
  1. Validate JWT & entity exists
  2. Upload to Supabase Storage (new bucket)
  3. Create pms_attachments record
  4. Proxy to image-processing for OCR (if image/PDF)
  5. Queue extraction job (if document)
  6. Return immediately with signed URL
```

**Reference Docs:**
- `docs/ATTACHMENT_UPLOAD_ENDPOINTS_NEEDED.md` (detailed specs)
- `docs/UPLOAD_PROCESSING_WORKFLOW.md` (queue strategy)

### 2. Frontend Integration

**Component:** `apps/web/src/components/cards/WorkOrderCard.tsx`

**Add:**
```typescript
async function handleFileUpload(file: File, description: string) {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('category', 'photo');
  formData.append('description', description);

  const response = await fetch(
    `/api/work_orders/${workOrder.id}/upload`,
    {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${jwtToken}` },
      body: formData,
    }
  );

  const result = await response.json();

  // Display attachment with signed URL
  setAttachments([...attachments, {
    id: result.attachment_id,
    filename: result.filename,
    url: result.signed_url,
  }]);
}
```

### 3. Image-Processing Extension

**Repo:** `shortalex12333/Image-processing`

**Add to `upload_type` enum:**
```python
"work_order", "fault", "equipment"
```

**Route logic:**
```python
if upload_type in ("work_order", "fault", "equipment"):
    # Use entity-based buckets
    bucket_name = f"pms-{entity_type}-attachments"

    # Write to pms_attachments (NOT pms_image_uploads)
    supabase.table("pms_attachments").insert({...}).execute()
```

### 4. Extraction Worker (Optional - If Queue Needed)

**Only needed if documents require entity extraction.**

See: `docs/UPLOAD_PROCESSING_WORKFLOW.md` for queue fairness strategy.

---

## Database Schema Reference

### pms_attachments (Existing + Category Column)
```sql
CREATE TABLE pms_attachments (
    id UUID PRIMARY KEY,
    yacht_id UUID NOT NULL,
    entity_type VARCHAR(50) NOT NULL,  -- 'work_order', 'fault', 'equipment'
    entity_id UUID NOT NULL,
    filename VARCHAR(255) NOT NULL,
    original_filename VARCHAR(255) NOT NULL,
    mime_type VARCHAR(100) NOT NULL,
    storage_path TEXT NOT NULL,
    category VARCHAR(50),  -- ← NEW: 'photo', 'document', 'pdf', etc.
    description TEXT,
    uploaded_by UUID NOT NULL,
    uploaded_at TIMESTAMPTZ NOT NULL,
    deleted_at TIMESTAMPTZ,
    metadata JSONB DEFAULT '{}'
);
```

### pms_attachment_comments (NEW)
```sql
CREATE TABLE pms_attachment_comments (
    id UUID PRIMARY KEY,
    yacht_id UUID NOT NULL,
    attachment_id UUID NOT NULL REFERENCES pms_attachments(id) ON DELETE CASCADE,
    comment TEXT NOT NULL,
    created_by UUID NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    updated_by UUID,
    updated_at TIMESTAMPTZ,
    deleted_at TIMESTAMPTZ,
    author_department VARCHAR(100),  -- Auto-populated via trigger
    parent_comment_id UUID REFERENCES pms_attachment_comments(id),
    metadata JSONB DEFAULT '{}'
);
```

### Storage Buckets (NEW)
```
pms-work-order-attachments/
    {yacht_id}/
        {work_order_id}/
            photo_1.jpg
            manual_v2.pdf

pms-fault-attachments/
    {yacht_id}/
        {fault_id}/
            leak_evidence.jpg
```

---

## Testing Checklist (Post-Merge)

### Backend Verification
```bash
# 1. Check migrations applied
psql $SUPABASE_DB_URL -c "\dt pms_attachment_comments"

# 2. Check buckets exist
psql $SUPABASE_DB_URL -c "SELECT id FROM storage.buckets WHERE id LIKE '%attachments'"

# 3. Test handler (via action router)
curl -X POST 'https://pipeline-core.int.celeste7.ai/v1/actions/execute' \
  -H "Authorization: Bearer $JWT" \
  -d '{
    "action": "add_work_order_photo",
    "context": {},
    "payload": {
      "work_order_id": "test-wo-id",
      "storage_path": "test/path.jpg",
      "filename": "test.jpg",
      "mime_type": "image/jpeg",
      "category": "photo"
    }
  }'
```

### Expected Result
```json
{
  "status": "success",
  "attachment_id": "uuid",
  "work_order_id": "test-wo-id"
}
```

### Verify in Database
```sql
SELECT * FROM pms_attachments
WHERE entity_type = 'work_order'
AND entity_id = 'test-wo-id';

-- Should show new record with:
-- ✓ category = 'photo'
-- ✓ storage_path = 'test/path.jpg'
-- ✓ uploaded_by = user_id from JWT
```

---

## Known Issues / Notes

### 1. Legacy Bucket Compatibility
Handlers check NEW buckets first, fallback to legacy `pms-work-order-photos` for old attachments. Ensures backwards compatibility.

### 2. Category Column Backfilled
Migration 20260130000001 already backfilled existing records:
- image/* → category: 'photo'
- application/pdf → category: 'pdf'
- Other → category: 'other'

### 3. RLS Enforcement
All new buckets have RLS policies requiring:
- User belongs to yacht (via auth_users_roles)
- DELETE restricted to admin/chief_engineer/technical_crew

### 4. Comment Department Logic
`author_department` auto-populated via trigger mapping:
- chief_engineer/engineer/technical_crew → 'technical'
- captain/officer/deckhand → 'deck'
- chief_steward/stewardess → 'interior'
- chef → 'galley'

---

## Questions / Support

**Architecture Docs:**
- `docs/ATTACHMENT_UPLOAD_ENDPOINTS_NEEDED.md` - Upload endpoint specs
- `docs/UPLOAD_PROCESSING_WORKFLOW.md` - Queue fairness strategy

**Related PRs:**
- PR #27: RLS + JWT architecture (already merged to main)
- PR #24: Stock seeding fixes (already merged to main)

**Deployment:**
- Service: https://pipeline-core.int.celeste7.ai
- Image-processing: https://image-processing-givq.onrender.com
- Supabase: vzsohavtuotocgrfkfyd.supabase.co

---

## Summary

**This PR enables:**
- ✅ Attachment uploads to work orders/faults/equipment
- ✅ Entity-based storage buckets with RLS
- ✅ Threaded comments on attachments (UX: "note ON the file")
- ✅ Department-based access control
- ✅ Foundation for upload endpoints and frontend UI

**Next Steps:**
1. Merge this PR
2. Apply migrations 109 & 110 to production
3. Build upload endpoints (clone receiving pattern)
4. Integrate frontend upload UI
5. Extend image-processing service for entity types

Ready to merge! 🚀
