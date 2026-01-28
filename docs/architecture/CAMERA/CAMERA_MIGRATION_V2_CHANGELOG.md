# Camera Feature Migration V2 - Production Hardening Changelog

## What Was Broken in V1

### 1. ❌ Rate Limiting Not Enforced
**V1 Problem:** Function `check_image_upload_rate_limit()` existed but was never called.
**V2 Fix:** Added `BEFORE INSERT` trigger that ENFORCES rate limit on every upload.

```sql
-- V2: ENFORCED via trigger
CREATE TRIGGER trg_enforce_rate_limit
BEFORE INSERT ON pms_image_uploads
FOR EACH ROW
EXECUTE FUNCTION check_image_upload_rate_limit();
```

**Result:** Users now CANNOT upload more than 50 images/hour. Hard rejection at database level.

---

### 2. ❌ Deduplication Not Enforced
**V1 Problem:** Function `check_duplicate_image()` existed but was never called.
**V2 Fix:** Added `BEFORE INSERT` trigger that checks SHA256 hash and marks duplicates.

```sql
-- V2: ENFORCED via trigger
CREATE TRIGGER trg_enforce_deduplication
BEFORE INSERT ON pms_image_uploads
FOR EACH ROW
EXECUTE FUNCTION enforce_image_deduplication();
```

**Result:** Duplicate images are automatically detected, marked as `is_duplicate = true`, and linked to original via `duplicate_of_image_id`.

---

### 3. ❌ UUID Arrays Reintroduced Anti-Pattern
**V1 Problem:** Added UUID arrays to 5 tables:
- `source_image_ids UUID[]`
- `discrepancy_photo_ids UUID[]`
- `photo_ids UUID[]`
- `shipping_label_image_ids UUID[]`
- `invoice_image_ids UUID[]`

**V2 Fix:** Removed ALL UUID arrays. Created single generic junction table instead.

```sql
-- V2: Generic junction table (clean, queryable, RLS-compatible)
CREATE TABLE pms_entity_images (
    entity_type TEXT, -- 'order', 'part', 'shopping_list_item', 'receiving_line_item', etc.
    entity_id UUID,
    image_id UUID REFERENCES pms_image_uploads(id),
    image_role TEXT, -- 'primary', 'supplementary', 'discrepancy', 'shipping_label', 'invoice'
    ...
);
```

**Result:** Clean M:M relationships. Properly indexed. RLS-compatible. No array manipulation needed.

---

### 4. ❌ IP Address Retention Compliance Gap
**V1 Problem:** `upload_ip_address INET` stored forever with no purge policy.
**V2 Fix:** Added purge function + documented need for cron job.

```sql
-- V2: IP purge function
CREATE FUNCTION purge_old_ip_addresses() RETURNS INTEGER AS $$
BEGIN
    UPDATE pms_image_uploads
    SET upload_ip_address = NULL
    WHERE uploaded_at < NOW() - INTERVAL '90 days';
    ...
END;
$$ LANGUAGE plpgsql;
```

**Result:** IP addresses auto-purged after 90 days. Compliance-ready.

**Action Required:** Schedule via cron or backend job:
```sql
SELECT cron.schedule('purge-old-ip-addresses', '0 2 * * *', $$SELECT purge_old_ip_addresses();$$);
```

---

### 5. ❌ uuid_generate_v4() Not Available by Default
**V1 Problem:** Used `uuid_generate_v4()` which requires `uuid-ossp` extension.
**V2 Fix:** Switched to `gen_random_uuid()` (built-in via pgcrypto).

```sql
-- V2: Uses gen_random_uuid() instead
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
...
id UUID PRIMARY KEY DEFAULT gen_random_uuid()
```

**Result:** Works on all Supabase instances without additional extensions.

---

### 6. ❌ Missing Prerequisites Check
**V1 Problem:** Migration assumed `yacht_registry` and `get_user_yacht_id()` exist.
**V2 Fix:** Added explicit prerequisite validation at start of migration.

```sql
-- V2: Prerequisites check (fails fast if missing)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_tables WHERE tablename = 'yacht_registry') THEN
        RAISE EXCEPTION 'Prerequisite missing: yacht_registry table does not exist';
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_proc WHERE proname = 'get_user_yacht_id') THEN
        RAISE EXCEPTION 'Prerequisite missing: get_user_yacht_id() function does not exist';
    END IF;
END $$;
```

**Result:** Migration fails fast with clear error if prerequisites missing.

---

## What's Actually Enforced Now (V2)

### ✅ Rate Limiting
- **Max:** 50 uploads per hour per user per yacht
- **Enforced by:** `BEFORE INSERT` trigger
- **Failure mode:** EXCEPTION raised, upload rejected
- **Bypass:** None (enforced at DB level)

### ✅ Deduplication
- **Check:** SHA256 hash uniqueness per yacht
- **Enforced by:** `BEFORE INSERT` trigger
- **Failure mode:** Marked as duplicate, links to original
- **Result:** `is_duplicate = true`, `validation_stage = 'failed'`

### ✅ State Machine
- **States:** draft → reconciling → verifying → committed | cancelled
- **Enforced by:** `BEFORE UPDATE` trigger
- **Failure mode:** EXCEPTION raised, invalid transition rejected
- **One-way:** Committed/cancelled sessions cannot change

### ✅ IP Address Purging
- **Retention:** 90 days
- **Enforced by:** Scheduled function (needs cron setup)
- **Method:** Sets `upload_ip_address = NULL` after 90 days
- **Audit trail:** Logs purge timestamp to metadata

---

## Architecture Improvements (V2)

### From UUID Arrays → Generic Junction Table

**V1 Pattern (BAD):**
```sql
-- Each table had its own array
ALTER TABLE pms_orders ADD COLUMN shipping_label_image_ids UUID[];
ALTER TABLE pms_parts ADD COLUMN photo_ids UUID[];
ALTER TABLE pms_shopping_list_items ADD COLUMN source_image_ids UUID[];
-- etc.
```

**V2 Pattern (GOOD):**
```sql
-- Single junction table handles all attachments
CREATE TABLE pms_entity_images (
    entity_type TEXT, -- 'order', 'part', 'shopping_list_item', etc.
    entity_id UUID,
    image_id UUID,
    image_role TEXT, -- 'primary', 'supplementary', 'discrepancy', etc.
    ...
);

-- Example: Attach shipping label to order
INSERT INTO pms_entity_images (entity_type, entity_id, image_id, image_role)
VALUES ('order', '{order_id}', '{image_id}', 'shipping_label');

-- Query: Get all images for an order
SELECT * FROM pms_entity_images WHERE entity_type = 'order' AND entity_id = '{order_id}';
```

**Benefits:**
- Single RLS policy covers all entities
- Proper indexing: `CREATE INDEX idx_entity_images_entity ON pms_entity_images(entity_type, entity_id);`
- No array manipulation needed
- Clear audit trail (who added, when)
- Sequence support for multi-image ordering

---

## Test Cases to Verify V2

### Test 1: Rate Limiting
```sql
-- Try to upload 51 images rapidly as same user
-- Expected: First 50 succeed, 51st raises EXCEPTION
INSERT INTO pms_image_uploads (yacht_id, storage_bucket, storage_path, file_name, mime_type, file_size_bytes, sha256_hash, uploaded_by)
VALUES ('{yacht_id}', 'receiving-images', '/test/51st.jpg', '51st.jpg', 'image/jpeg', 1000, 'hash51', auth.uid());

-- Expected error: "Upload rate limit exceeded: 50 uploads in last hour. Maximum 50 uploads per hour."
```

### Test 2: Deduplication
```sql
-- Upload same image twice
INSERT INTO pms_image_uploads (..., sha256_hash, ...) VALUES (..., 'abc123', ...); -- OK
INSERT INTO pms_image_uploads (..., sha256_hash, ...) VALUES (..., 'abc123', ...); -- Marked as duplicate

-- Verify duplicate detected
SELECT is_duplicate, duplicate_of_image_id, validation_stage FROM pms_image_uploads WHERE sha256_hash = 'abc123';
-- Expected: Second row has is_duplicate = true, points to first row
```

### Test 3: State Machine
```sql
-- Try invalid transition
UPDATE pms_receiving_sessions SET status = 'committed' WHERE status = 'draft';
-- Expected error: "Invalid transition from draft to committed"

-- Valid transition
UPDATE pms_receiving_sessions SET status = 'reconciling' WHERE status = 'draft'; -- OK
UPDATE pms_receiving_sessions SET status = 'verifying' WHERE status = 'reconciling'; -- OK
UPDATE pms_receiving_sessions SET status = 'committed' WHERE status = 'verifying'; -- OK
```

### Test 4: Junction Table
```sql
-- Attach multiple images to an order
INSERT INTO pms_entity_images (entity_type, entity_id, image_id, image_role, added_by)
VALUES
    ('order', '{order_id}', '{image1}', 'shipping_label', auth.uid()),
    ('order', '{order_id}', '{image2}', 'invoice', auth.uid()),
    ('order', '{order_id}', '{image3}', 'packing_slip', auth.uid());

-- Query all images for order
SELECT i.*, ei.image_role
FROM pms_entity_images ei
JOIN pms_image_uploads i ON i.id = ei.image_id
WHERE ei.entity_type = 'order' AND ei.entity_id = '{order_id}';
```

---

## Remaining Manual Steps

### 1. Schedule IP Address Purging
**Via pg_cron (if available):**
```sql
SELECT cron.schedule('purge-old-ip-addresses', '0 2 * * *', $$SELECT purge_old_ip_addresses();$$);
```

**Via external scheduler (if pg_cron not available):**
- Set up daily cron job to call: `SELECT purge_old_ip_addresses();`
- Or build into backend scheduled task

### 2. Create Supabase Storage Buckets
Via Supabase Dashboard → Storage:
1. `receiving-images` (15MB limit, jpg/png/pdf/heic)
2. `discrepancy-photos` (10MB limit, jpg/png/heic)
3. `label-pdfs` (5MB limit, pdf only)
4. `part-photos` (5MB limit, jpg/png)

### 3. Configure Storage RLS Policies
For each bucket:
```sql
-- Users can upload to their yacht folder
CREATE POLICY "Users upload to yacht folder"
ON storage.objects FOR INSERT
TO authenticated
WITH CHECK (
    bucket_id = 'receiving-images'
    AND (storage.foldername(name))[1] = (SELECT yacht_id::TEXT FROM user_profiles WHERE id = auth.uid())
);

-- Users can read their yacht's images
CREATE POLICY "Users read yacht images"
ON storage.objects FOR SELECT
TO authenticated
USING (
    bucket_id = 'receiving-images'
    AND (storage.foldername(name))[1] = (SELECT yacht_id::TEXT FROM user_profiles WHERE id = auth.uid())
);
```

### 4. Build Backend OCR Pipeline
- Image upload endpoint (compute SHA256)
- OCR service (Tesseract or cloud)
- Classification service
- Extraction service
- Matching/reconciliation service

---

## File Size Comparison

- **V1:** 27KB (enforcement missing)
- **V2:** 30KB (enforcement wired, arrays removed, prerequisites added)

---

## Migration Path

If you already applied V1:
```sql
-- Drop V1 artifacts
DROP TABLE IF EXISTS pms_receiving_session_images CASCADE;
DROP FUNCTION IF EXISTS check_image_upload_rate_limit(UUID, UUID);
DROP FUNCTION IF EXISTS check_duplicate_image(TEXT, UUID);

-- Remove UUID array columns added by V1
ALTER TABLE pms_receiving_events DROP COLUMN IF EXISTS source_image_ids;
ALTER TABLE pms_receiving_line_items DROP COLUMN IF EXISTS discrepancy_photo_ids;
ALTER TABLE pms_shopping_list_items DROP COLUMN IF EXISTS source_image_ids;
ALTER TABLE pms_parts DROP COLUMN IF EXISTS photo_ids;
ALTER TABLE pms_parts DROP COLUMN IF EXISTS primary_photo_id;
ALTER TABLE pms_orders DROP COLUMN IF EXISTS shipping_label_image_ids;
ALTER TABLE pms_orders DROP COLUMN IF EXISTS invoice_image_ids;

-- Then apply V2
\i 20260109000005_camera_feature_foundation_v2.sql
```

If fresh install:
```sql
-- Just apply V2
\i 20260109000005_camera_feature_foundation_v2.sql
```

---

## Summary: V1 → V2 Fixes

| Issue | V1 | V2 |
|-------|----|----|
| **Rate limiting** | Function exists, not called | ENFORCED via trigger |
| **Deduplication** | Function exists, not called | ENFORCED via trigger |
| **UUID arrays** | 5 tables polluted | Removed, generic junction table |
| **IP retention** | Stored forever | Auto-purged after 90 days |
| **UUID generation** | uuid_generate_v4() (needs extension) | gen_random_uuid() (built-in) |
| **Prerequisites** | Assumed to exist | Validated at migration start |
| **State machine** | Defined, not enforced | ENFORCED via trigger |

---

**Created:** 2026-01-09
**Version:** V2 (Production-Hardened)
**Status:** Ready for deployment
**File:** `20260109000005_camera_feature_foundation_v2.sql` (30KB)
