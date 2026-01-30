# PR #26 - Quick Summary (Forward to Engineers)

**Branch:** `fix/attachment-table-handlers`
**Status:** ✅ Ready for merge to main
**Commit:** `34b083d`

---

## What's Ready

### 1. Fixed Critical Bugs
- Work order photo uploads now write to correct table (`pms_attachments`)
- Fault photo uploads now write to correct table (was trying to use non-existent table)

### 2. New Infrastructure
- **4 new storage buckets** for entity-based attachments (work_order, fault, equipment, checklist)
- **Comments table** (`pms_attachment_comments`) with department-based RLS
- **Handler updates** to route to new buckets

### 3. Files Changed
```
apps/api/handlers/p2_mutation_light_handlers.py   (bug fix)
apps/api/handlers/fault_mutation_handlers.py      (bug fix)
apps/api/handlers/work_order_handlers.py          (bucket routing)
apps/api/handlers/fault_handlers.py               (bucket routing)
apps/api/handlers/equipment_handlers.py           (bucket routing)
supabase/migrations/20260130_109_*.sql            (storage buckets)
supabase/migrations/20260130_110_*.sql            (comments table)
```

---

## After Merge - TODO

### Immediate (Database)
```bash
# Apply migrations to production
psql $SUPABASE_DB_URL < supabase/migrations/20260130_109_create_attachment_storage_buckets.sql
psql $SUPABASE_DB_URL < supabase/migrations/20260130_110_create_attachment_comments_table.sql
```

### Next Phase (Code)
1. **Upload Endpoints:** Clone `apps/api/routes/receiving_upload.py` for work_order/fault/equipment
2. **Frontend UI:** Add upload button to WorkOrderCard component
3. **Image-Processing:** Extend for entity types (work_order, fault, equipment)

---

## Reference Docs (in repo)

- `PR_26_MERGE_DETAILS.md` - Full technical spec
- `docs/ATTACHMENT_UPLOAD_ENDPOINTS_NEEDED.md` - Upload endpoint implementation guide
- `docs/UPLOAD_PROCESSING_WORKFLOW.md` - Queue strategy & processing flow

---

## Key Points for Your Engineer

### Architecture Pattern
Follow the **receiving upload pattern** (already exists):
```
User uploads file
  → Cloud_PMS endpoint validates
  → Proxy to image-processing (OCR)
  → Create pms_attachments record
  → Return immediately with signed URL
```

### New Tables/Buckets Available
```sql
-- Table for attachment metadata
pms_attachments (entity_type, entity_id, category, storage_path)

-- Table for comments ON attachments
pms_attachment_comments (attachment_id, comment, author_department)

-- Storage buckets (path: yacht_id/entity_id/filename)
pms-work-order-attachments
pms-fault-attachments
pms-equipment-attachments
```

### Upload Endpoint Template
```python
POST /api/work_orders/{work_order_id}/upload

Request:
  - file: multipart/form-data
  - category: "photo" | "document" | "pdf" | "manual"
  - description: optional text

Response:
  {
    "attachment_id": "uuid",
    "signed_url": "https://...",
    "filename": "leak_photo.jpg"
  }
```

### Frontend Integration
```typescript
// Add to WorkOrderCard.tsx
<input type="file" onChange={handleUpload} />

async function handleUpload(file) {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('category', 'photo');

  const res = await fetch(`/api/work_orders/${id}/upload`, {
    method: 'POST',
    headers: { 'Authorization': `Bearer ${jwt}` },
    body: formData
  });

  const { signed_url } = await res.json();
  // Display image with signed_url
}
```

---

## Questions?

See full technical details in `PR_26_MERGE_DETAILS.md` or reach out!

**Ready to build:** Upload endpoints, frontend UI, image-processing extension
