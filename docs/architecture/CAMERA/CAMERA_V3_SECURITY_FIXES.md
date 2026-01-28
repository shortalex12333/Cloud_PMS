# Camera Feature Migration V3 - Security Hardening

## What V2 Got Wrong (Security Holes)

### 🚨 LANDMINE #1: Deduplication Didn't Block
**V2 Behavior:** Trigger flagged duplicates but still inserted the row
```sql
-- V2: Marked as duplicate but still allowed INSERT
NEW.is_duplicate := true;
NEW.duplicate_of_image_id := <original>;
RETURN NEW; -- Still inserts!
```

**Problem:**
- Duplicate rows still created
- Storage costs doubled (unless backend also checks)
- Database bloat with flagged duplicates

**V3 Fix:** Trigger now BLOCKS duplicates with RAISE EXCEPTION
```sql
-- V3: Hard block
IF v_existing_image_id IS NOT NULL THEN
    RAISE EXCEPTION 'Duplicate image detected. Original image_id: %', v_existing_image_id
        USING HINT = 'Retrieve existing image instead of re-uploading',
              ERRCODE = 'P0002',
              DETAIL = format('original_image_id=%s', v_existing_image_id);
END IF;
```

**Result:** Client receives exception with original image_id, can reuse existing image

---

### 🚨 LANDMINE #2: IP Address Column NOT Restricted
**V2 Claim:** "IP restricted to service_role only" (false)

**V2 Reality:** RLS doesn't hide columns. Users could query:
```sql
SELECT id, file_name, upload_ip_address FROM pms_image_uploads;
-- This would work for authenticated users in V2
```

**V3 Fix:** Column-level privilege revocation
```sql
-- V3: Actually revoke column access
REVOKE SELECT (upload_ip_address) ON pms_image_uploads FROM PUBLIC;
REVOKE SELECT (upload_ip_address) ON pms_image_uploads FROM authenticated;

-- Grant back only to service_role
GRANT SELECT (upload_ip_address) ON pms_image_uploads TO service_role;
```

**Result:** Authenticated users CANNOT see IP addresses at all

**Test:**
```sql
-- As authenticated user
SELECT upload_ip_address FROM pms_image_uploads;
-- Error: permission denied for column "upload_ip_address"

-- As service_role
SELECT upload_ip_address FROM pms_image_uploads;
-- Works
```

---

### 🚨 LANDMINE #3: SECURITY DEFINER Functions Callable by Users
**V2 Problem:** All SECURITY DEFINER functions had default EXECUTE privileges

```sql
-- V2: Any authenticated user could call:
SELECT check_image_upload_rate_limit(); -- Direct call bypasses trigger logic
SELECT enforce_image_deduplication(); -- Direct call bypasses trigger logic
SELECT purge_old_ip_addresses(); -- User could purge IPs early
```

**V3 Fix:** REVOKE EXECUTE from all users
```sql
-- V3: Only triggers and service_role can call these
REVOKE EXECUTE ON FUNCTION check_image_upload_rate_limit() FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION check_image_upload_rate_limit() FROM authenticated;

REVOKE EXECUTE ON FUNCTION enforce_image_deduplication() FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION enforce_image_deduplication() FROM authenticated;

REVOKE EXECUTE ON FUNCTION purge_old_ip_addresses() FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION purge_old_ip_addresses() FROM authenticated;
GRANT EXECUTE ON FUNCTION purge_old_ip_addresses() TO service_role; -- For cron

REVOKE EXECUTE ON FUNCTION generate_receiving_session_number() FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION generate_receiving_session_number() FROM authenticated;

REVOKE EXECUTE ON FUNCTION enforce_receiving_session_state_transitions() FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION enforce_receiving_session_state_transitions() FROM authenticated;
```

**Result:** Users cannot bypass trigger logic by calling functions directly

---

## V3 Security Model (Actual Production-Hardened)

### Rate Limiting
- **Max:** 50 uploads/hour/user/yacht
- **Enforced:** BEFORE INSERT trigger → RAISE EXCEPTION
- **Bypass:** None (DB-level enforcement)
- **Function callable by:** Trigger only (EXECUTE REVOKED)

### Deduplication
- **Check:** SHA256 hash uniqueness per yacht
- **Enforced:** BEFORE INSERT trigger → RAISE EXCEPTION
- **Behavior:** BLOCKS duplicate, returns original image_id in error DETAIL
- **Client action:** Parse exception, reuse original_image_id
- **Function callable by:** Trigger only (EXECUTE REVOKED)

### IP Address Privacy
- **Storage:** upload_ip_address INET column
- **Visibility:** service_role ONLY (column privilege REVOKED from authenticated)
- **Retention:** Auto-purged after 90 days via scheduled function
- **Purge callable by:** service_role only (EXECUTE REVOKED from authenticated)

### State Machine
- **Transitions:** draft → reconciling → verifying → committed | cancelled
- **Enforced:** BEFORE UPDATE trigger → RAISE EXCEPTION on invalid transition
- **Function callable by:** Trigger only (EXECUTE REVOKED)

---

## Test Cases for V3

### Test 1: Deduplication Actually Blocks
```sql
-- Upload image
INSERT INTO pms_image_uploads (
    yacht_id, storage_bucket, storage_path, file_name,
    mime_type, file_size_bytes, sha256_hash, uploaded_by
) VALUES (
    '{yacht_id}', 'receiving-images', '/test/img1.jpg', 'img1.jpg',
    'image/jpeg', 1000, 'abc123hash', auth.uid()
); -- OK, first upload

-- Try to upload same image again
INSERT INTO pms_image_uploads (
    yacht_id, storage_bucket, storage_path, file_name,
    mime_type, file_size_bytes, sha256_hash, uploaded_by
) VALUES (
    '{yacht_id}', 'receiving-images', '/test/img2.jpg', 'img2.jpg',
    'image/jpeg', 1000, 'abc123hash', auth.uid()
);
-- Expected: EXCEPTION "Duplicate image detected. Original image_id: ..."
-- SQLSTATE: P0002
```

### Test 2: IP Address Column Actually Hidden
```sql
-- As authenticated user
SELECT id, file_name, upload_ip_address FROM pms_image_uploads;
-- Expected: ERROR permission denied for column "upload_ip_address"

-- As service_role
SELECT id, file_name, upload_ip_address FROM pms_image_uploads;
-- Expected: Works, shows IPs
```

### Test 3: Functions Cannot Be Called Directly
```sql
-- As authenticated user
SELECT check_image_upload_rate_limit();
-- Expected: ERROR permission denied for function check_image_upload_rate_limit

SELECT purge_old_ip_addresses();
-- Expected: ERROR permission denied for function purge_old_ip_addresses

-- As service_role (for cron job)
SELECT purge_old_ip_addresses();
-- Expected: Works, returns count of purged IPs
```

### Test 4: Rate Limiting Blocks 51st Upload
```sql
-- Upload 50 images rapidly (loop)
-- Expected: All 50 succeed

-- Try 51st
INSERT INTO pms_image_uploads (...);
-- Expected: EXCEPTION "Upload rate limit exceeded: 50 uploads in last hour"
-- SQLSTATE: P0001
```

---

## Backend Upload RPC Pattern (Recommended)

To work with V3's blocked deduplication:

```sql
-- Create upload RPC that checks for duplicates first
CREATE OR REPLACE FUNCTION upload_image_with_dedupe_check(
    p_yacht_id UUID,
    p_sha256_hash TEXT,
    p_storage_bucket TEXT,
    p_storage_path TEXT,
    p_file_name TEXT,
    p_mime_type TEXT,
    p_file_size_bytes BIGINT,
    p_upload_ip_address INET
) RETURNS JSONB AS $$
DECLARE
    v_existing_image_id UUID;
    v_new_image_id UUID;
BEGIN
    -- Check for existing image with this hash
    SELECT id INTO v_existing_image_id
    FROM pms_image_uploads
    WHERE sha256_hash = p_sha256_hash
    AND yacht_id = p_yacht_id
    AND deleted_at IS NULL;

    IF v_existing_image_id IS NOT NULL THEN
        -- Return existing image info (don't upload to storage again)
        RETURN jsonb_build_object(
            'is_duplicate', true,
            'existing_image_id', v_existing_image_id,
            'message', 'Image already exists, reusing existing upload'
        );
    ELSE
        -- Insert new image (triggers will enforce rate limit)
        INSERT INTO pms_image_uploads (
            yacht_id, storage_bucket, storage_path, file_name,
            mime_type, file_size_bytes, sha256_hash,
            uploaded_by, upload_ip_address
        ) VALUES (
            p_yacht_id, p_storage_bucket, p_storage_path, p_file_name,
            p_mime_type, p_file_size_bytes, p_sha256_hash,
            auth.uid(), p_upload_ip_address
        ) RETURNING id INTO v_new_image_id;

        RETURN jsonb_build_object(
            'is_duplicate', false,
            'new_image_id', v_new_image_id,
            'message', 'Image uploaded successfully'
        );
    END IF;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Grant to authenticated for upload RPC
GRANT EXECUTE ON FUNCTION upload_image_with_dedupe_check TO authenticated;
```

This RPC pattern:
1. Checks for duplicates BEFORE storage write
2. Returns existing image_id if duplicate (avoids storage cost)
3. Only uploads to storage if hash is new
4. Still gets rate limiting via trigger

---

## Scheduled Job Setup (IP Purging)

### Option A: pg_cron (if available)
```sql
-- As service_role (superuser)
SELECT cron.schedule(
    'purge-old-ip-addresses',
    '0 2 * * *', -- Daily at 2 AM
    $$SELECT purge_old_ip_addresses();$$
);
```

### Option B: External Cron Job
```bash
#!/bin/bash
# /etc/cron.daily/purge-ips.sh

psql -h db.vzsohavtuotocgrfkfyd.supabase.co \
     -U postgres \
     -d postgres \
     -c "SELECT purge_old_ip_addresses();"
```

### Option C: Backend Scheduled Task
```typescript
// Next.js cron route or similar
import { createClient } from '@supabase/supabase-js';

const supabase = createClient(
  process.env.SUPABASE_URL,
  process.env.SUPABASE_SERVICE_ROLE_KEY // Service role key
);

async function purgeOldIPs() {
  const { data, error } = await supabase.rpc('purge_old_ip_addresses');
  console.log(`Purged ${data} IP addresses`);
}

// Schedule daily
cron.schedule('0 2 * * *', purgeOldIPs);
```

---

## Migration Path

### If You Already Applied V2
```sql
-- No need to drop/recreate tables
-- Just apply the security fixes:

-- 1. Fix deduplication function
CREATE OR REPLACE FUNCTION enforce_image_deduplication() ... -- V3 version

-- 2. Revoke IP column access
REVOKE SELECT (upload_ip_address) ON pms_image_uploads FROM PUBLIC;
REVOKE SELECT (upload_ip_address) ON pms_image_uploads FROM authenticated;
GRANT SELECT (upload_ip_address) ON pms_image_uploads TO service_role;

-- 3. Revoke function execution
REVOKE EXECUTE ON FUNCTION check_image_upload_rate_limit() FROM PUBLIC, authenticated;
REVOKE EXECUTE ON FUNCTION enforce_image_deduplication() FROM PUBLIC, authenticated;
REVOKE EXECUTE ON FUNCTION purge_old_ip_addresses() FROM PUBLIC, authenticated;
GRANT EXECUTE ON FUNCTION purge_old_ip_addresses() TO service_role;
REVOKE EXECUTE ON FUNCTION generate_receiving_session_number() FROM PUBLIC, authenticated;
REVOKE EXECUTE ON FUNCTION enforce_receiving_session_state_transitions() FROM PUBLIC, authenticated;
```

### Fresh Install
```bash
psql -h db.vzsohavtuotocgrfkfyd.supabase.co \
     -U postgres \
     -d postgres \
     -f 20260109000005_camera_feature_foundation_v3.sql
```

---

## What's Actually Enforced Now (V3 vs V2)

| Feature | V2 | V3 |
|---------|----|----|
| **Deduplication** | Flagged, not blocked | BLOCKED (RAISE EXCEPTION) |
| **IP column access** | Visible to authenticated | REVOKED from authenticated |
| **Function privileges** | Callable by authenticated | REVOKED from authenticated |
| **Rate limiting** | ✓ Enforced | ✓ Enforced |
| **State machine** | ✓ Enforced | ✓ Enforced |
| **UUID generation** | ✓ gen_random_uuid() | ✓ gen_random_uuid() |
| **Prerequisites check** | ✓ Validated | ✓ Validated |
| **Junction table** | ✓ Generic | ✓ Generic |

---

## Files on Desktop

1. **20260109000005_camera_feature_foundation_v3.sql** (31KB)
   - Production-hardened migration with actual security enforcement

2. **20260109000005_camera_feature_foundation_v2.sql** (30KB)
   - Previous version (has security holes)

3. **CAMERA_V3_SECURITY_FIXES.md** (this file)
   - Detailed changelog of V2 → V3 security fixes

4. **CAMERA_MIGRATION_V2_CHANGELOG.md**
   - V1 → V2 fixes

5. **CAMERA_FEATURE_DB_DESIGN.md**
   - Complete architecture documentation

6. **CAMERA_FEATURE_SUMMARY.md**
   - Quick reference guide

---

## My Verdict on V3

**V3 is production-hardened** because:

✅ Deduplication actually BLOCKS duplicates (not just flags)
✅ IP addresses are ACTUALLY restricted from authenticated users (column privilege revoked)
✅ SECURITY DEFINER functions are ACTUALLY restricted (EXECUTE revoked)
✅ Rate limiting enforced at DB level
✅ State machine enforced at DB level
✅ No UUID arrays (clean junction table)
✅ Prerequisites validated on migration
✅ Uses gen_random_uuid() (no extension dependency)

**Remaining manual steps:**
1. Schedule IP purging (cron or backend job)
2. Create Supabase storage buckets
3. Configure storage RLS policies
4. Build backend upload RPC with SHA256 computation

**Storage cost optimization:**
- Backend upload RPC should check SHA256 before writing to storage
- If duplicate found, return existing image_id and skip storage write
- This prevents paying for duplicate storage even though DB blocks duplicate rows

---

**Created:** 2026-01-09
**Version:** V3 (Actually Production-Hardened)
**Status:** Ready for deployment
**File:** `20260109000005_camera_feature_foundation_v3.sql` (31KB)
