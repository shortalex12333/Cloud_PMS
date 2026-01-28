# Camera Feature - Quick Reference Summary

## What Was Created

### 5 New Tables

1. **`pms_image_uploads`** - Stores all uploaded images with validation, OCR, and classification
2. **`pms_receiving_sessions`** - Tracks complete receiving workflow from upload to commit
3. **`pms_receiving_session_images`** - Links sessions to multiple images (M:M)
4. **`pms_receiving_draft_lines`** - Pre-verification extracted lines with human checkbox approval
5. **`pms_label_generations`** - Tracks PDF label generation and distribution

### Modified 5 Existing Tables

1. **`pms_receiving_events`** - Added `receiving_session_id`, `source_image_ids`
2. **`pms_receiving_line_items`** - Added `draft_line_id`, `discrepancy_photo_ids`
3. **`pms_shopping_list_items`** - Added `source_image_ids`
4. **`pms_parts`** - Added `photo_ids`, `primary_photo_id`
5. **`pms_orders`** - Added `shipping_label_image_ids`, `invoice_image_ids`

### 4 Supabase Storage Buckets (To Be Created)

1. **`receiving-images`** - Packing slips, shipping labels, invoices
2. **`discrepancy-photos`** - Photos of damaged/missing items
3. **`label-pdfs`** - Generated label PDFs
4. **`part-photos`** - Part identification photos

---

## Core Workflow

```
1. User uploads image → pms_image_uploads
2. System validates, classifies, extracts (OCR) → updates pms_image_uploads
3. Create session → pms_receiving_sessions
4. Link images to session → pms_receiving_session_images
5. Extract draft lines → pms_receiving_draft_lines
6. User verifies each line (checkbox truth) → updates pms_receiving_draft_lines
7. User commits session → triggers:
   - Create pms_receiving_event
   - Create pms_receiving_line_items (from verified drafts)
   - Update pms_shopping_list_items (if matched)
8. Generate labels → pms_label_generations
```

---

## Key Features

### ✅ Checkbox Truth
- All draft lines start unchecked
- Users must explicitly verify each line
- Only checked + verified lines committed

### ✅ Immutable Audit
- Images never deleted (soft delete only)
- OCR results preserved
- Draft lines preserved after commit

### ✅ Anti-Abuse
- SHA256 deduplication
- Rate limiting (50 uploads/hour/user)
- Validation gates (file type, size, text detection)
- Duplicate detection

### ✅ Multi-Stage Pipeline
- Stage 0: Upload
- Stage 1: Validation
- Stage 2: Classification (packing slip vs label vs invoice)
- Stage 3: OCR + extraction
- Stage 4: Sanity checks
- Stage 5: Reconciliation (match to orders/parts)
- Stage 6: Human verification
- Stage 7: Commit

### ✅ Session State Machine
```
draft → reconciling → verifying → committed
                    ↘ cancelled
```

---

## How Data Links Together

### Receiving Session Flow
```
pms_receiving_sessions
  ↓ has many
pms_receiving_session_images
  ↓ references
pms_image_uploads
  ↓ extracted into
pms_receiving_draft_lines
  ↓ verified and committed to
pms_receiving_line_items
  ↓ part of
pms_receiving_events
```

### Image Attachments
```
pms_orders
  ├── shipping_label_image_ids → pms_image_uploads
  └── invoice_image_ids → pms_image_uploads

pms_parts
  ├── photo_ids → pms_image_uploads
  └── primary_photo_id → pms_image_uploads

pms_shopping_list_items
  └── source_image_ids → pms_image_uploads

pms_receiving_line_items
  └── discrepancy_photo_ids → pms_image_uploads
```

---

## Database Functions

1. **`generate_receiving_session_number()`** - Auto-generate RSESS-YYYY-NNN
2. **`check_image_upload_rate_limit(user_id, yacht_id)`** - Enforce 50/hour limit
3. **`check_duplicate_image(sha256, yacht_id)`** - Find duplicates
4. **`enforce_receiving_session_state_transitions()`** - State machine validation

---

## RLS Security

All tables have multi-tenant isolation:
- Users can only see their yacht's data
- Service role has full access (for processing)
- No hard deletes allowed (soft delete only)

---

## Storage Bucket Structure

### `receiving-images`
```
/{yacht_id}/receiving/{year}/{month}/{session_id}/{image_id}.jpg
```

### `discrepancy-photos`
```
/{yacht_id}/discrepancies/{year}/{month}/{receiving_event_id}/{line_item_id}_{timestamp}.jpg
```

### `label-pdfs`
```
/{yacht_id}/labels/{year}/{month}/{receiving_event_id}/labels_{timestamp}.pdf
```

### `part-photos`
```
/{yacht_id}/parts/{part_id}/{photo_id}.jpg
```

---

## Next Steps

### Immediate (Database)
1. ✅ Migration SQL created: `20260109000005_camera_feature_foundation.sql`
2. ⏳ Apply migration to development database
3. ⏳ Create Supabase storage buckets
4. ⏳ Configure storage RLS policies

### Backend (API Layer)
1. Image upload endpoint + SHA256 hashing
2. OCR/extraction pipeline (Tesseract or cloud OCR)
3. Classification service (document type detection)
4. Matching/reconciliation service (link to orders/parts)
5. Label PDF generation service

### Frontend (UI)
1. Camera/upload UI component
2. Session draft table (checkbox verification)
3. Image preview + retake
4. Discrepancy photo capture
5. Label download/email

---

## Migration File Location

```
/private/tmp/Cloud_PMS_fix/supabase/migrations/20260109000005_camera_feature_foundation.sql
```

**Apply with:**
```bash
psql -h db.vzsohavtuotocgrfkfyd.supabase.co -U postgres -d postgres -f supabase/migrations/20260109000005_camera_feature_foundation.sql
```

**Or use the push_migrations.py script**

---

## Documentation Files

1. **CAMERA_FEATURE_DB_DESIGN.md** - Complete architecture design (65 pages)
2. **20260109000005_camera_feature_foundation.sql** - Migration SQL
3. **CAMERA_FEATURE_SUMMARY.md** - This file

---

## Table Row Estimates (After Deployment)

| Table | Expected Volume | Notes |
|-------|----------------|-------|
| `pms_image_uploads` | 1000+ / month | Packing slips, labels, photos |
| `pms_receiving_sessions` | 50-100 / month | One per delivery |
| `pms_receiving_session_images` | 2000+ / month | Multiple images per session |
| `pms_receiving_draft_lines` | 5000+ / month | 10-50 lines per session |
| `pms_label_generations` | 50-100 / month | One per receiving event |

---

## Key Design Decisions

1. **Draft lines separate from committed** - Preserves audit trail
2. **Array columns for image references** - Efficient for 1:M relationships
3. **JSONB for flexible metadata** - Future-proof without schema changes
4. **Soft deletes only** - Images never hard-deleted (compliance)
5. **State machine enforcement** - Prevents invalid workflow transitions
6. **Multi-stage pipeline** - Clear separation of concerns
7. **Checkbox = truth** - No auto-commit, explicit verification required

---

**Created:** 2026-01-09
**Status:** Ready for deployment
**Version:** 1.0
