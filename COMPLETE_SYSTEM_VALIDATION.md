# COMPLETE PARTS LENS SYSTEM VALIDATION
## Every Possible Failure Mode - Comprehensive Analysis

---

## SYSTEM DEPENDENCIES - WHAT MUST BE TRUE

### 1. DATABASE STATE
```sql
-- MUST EXIST: Parts to test against
SELECT COUNT(*) FROM pms_parts
WHERE yacht_id = '85fe1119-b04c-41ac-80f1-829d23322598'
AND id IN (
    '5dd34337-c4c4-41dd-9c6b-adf84af349a8',  -- TEAK_COMPOUND
    '2f452e3b-bf3e-464e-82d5-7d0bc849e6c0',  -- WATER_PUMP
    '5543266b-2d8c-46a0-88e2-74a7ab403cdd'   -- CYLINDER_RING
);
-- Expected: 3 rows

-- MUST EXIST: User profiles with roles
SELECT id, role FROM auth_users_roles
WHERE user_id IN (
    'b72c35ff-e309-4a19-a617-bfc706a78c0f',  -- Captain
    '89b1262c-ff59-4591-b954-757cdf3d609d',  -- HOD
    '2da12a4b-c0a1-4716-80ae-d29c90d98233'   -- Crew
)
AND yacht_id = '85fe1119-b04c-41ac-80f1-829d23322598'
AND is_active = TRUE;
-- Expected: 3 rows

-- MUST EXIST: Crew department metadata
SELECT metadata->>'department' FROM auth_users_profiles
WHERE id = '2da12a4b-c0a1-4716-80ae-d29c90d98233'
AND yacht_id = '85fe1119-b04c-41ac-80f1-829d23322598';
-- Expected: 'deck'
```

### 2. SUPABASE STORAGE
```bash
# MUST EXIST: Storage bucket
curl -X GET "https://vzsohavtuotocgrfkfyd.supabase.co/storage/v1/bucket/pms-part-images" \
  -H "Authorization: Bearer $TENANT_SUPABASE_SERVICE_KEY"
# Expected: 200 OK

# MUST HAVE: Upload permissions
# Policy: authenticated users can upload to yacht_id path
# Bucket: pms-part-images
# Pattern: {yacht_id}/parts/{part_id}/images/*
```

### 3. ENVIRONMENT VARIABLES
```bash
# MASTER DB (Auth)
MASTER_SUPABASE_URL=https://qvzmkaamzaqxpzbewjxe.supabase.co
MASTER_SUPABASE_ANON_KEY=eyJhbGci...
MASTER_SUPABASE_SERVICE_KEY=eyJhbGci...
MASTER_SUPABASE_JWT_SECRET=xxx

# TENANT DB (Data)
TENANT_SUPABASE_URL=https://vzsohavtuotocgrfkfyd.supabase.co
TENANT_SUPABASE_ANON_KEY=eyJhbGci...
TENANT_SUPABASE_SERVICE_KEY=eyJhbGci...

# Fleet Registry
yTEST_YACHT_001_SUPABASE_URL=https://vzsohavtuotocgrfkfyd.supabase.co
yTEST_YACHT_001_SUPABASE_SERVICE_KEY=eyJhbGci...

# Default tenant mapping
DEFAULT_YACHT_CODE=yTEST_YACHT_001
```

### 4. MASTER DB TABLES
```sql
-- user_accounts: Maps user_id → yacht_id
SELECT yacht_id, status FROM user_accounts
WHERE id = 'b72c35ff-e309-4a19-a617-bfc706a78c0f';

-- fleet_registry: Maps yacht_id → tenant_key_alias
SELECT tenant_key_alias, yacht_name FROM fleet_registry
WHERE yacht_id = '85fe1119-b04c-41ac-80f1-829d23322598';
-- Expected: tenant_key_alias = 'yTEST_YACHT_001' or 'y_ALIAS1'
```

### 5. TENANT DB TABLES
```sql
-- auth_users_roles: Authoritative role source
SELECT role, is_active FROM auth_users_roles
WHERE user_id = 'b72c35ff-e309-4a19-a617-bfc706a78c0f'
AND yacht_id = '85fe1119-b04c-41ac-80f1-829d23322598'
AND is_active = TRUE;
-- Expected: role IN ('captain', 'manager', 'chief_engineer', 'crew')

-- auth_users_profiles: Department metadata for crew RBAC
SELECT metadata FROM auth_users_profiles
WHERE id = '2da12a4b-c0a1-4716-80ae-d29c90d98233'
AND yacht_id = '85fe1119-b04c-41ac-80f1-829d23322598';
-- Expected: {"department": "deck"}

-- pms_parts: Test parts exist
SELECT id, name, part_number FROM pms_parts
WHERE yacht_id = '85fe1119-b04c-41ac-80f1-829d23322598'
AND id = '5dd34337-c4c4-41dd-9c6b-adf84af349a8';
-- Expected: 1 row (TEAK_COMPOUND)
```

---

## EVERY POSSIBLE FAILURE MODE

### JOURNEY 1: Crew Creates Work Order

#### Failure Mode 1: JWT Expired
**Symptom:** HTTP 401 "Invalid token: Expired"
**Detection:** `exp` claim < current time
**Fix:** Sign in user before test (✅ DONE)

#### Failure Mode 2: Crew Missing Department
**Symptom:** HTTP 403 "Crew user must have a department assigned"
**Detection:** `auth_users_profiles.metadata->>'department'` IS NULL
**Fix:** ✅ DONE (set metadata->department='deck')

#### Failure Mode 3: Crew Not in auth_users_roles
**Symptom:** HTTP 403 "Permission denied"
**Detection:** No row in auth_users_roles with is_active=TRUE
**Fix:** Verify crew user has active role

#### Failure Mode 4: Idempotency Collision
**Symptom:** HTTP 409 "Resource already exists"
**Detection:** Duplicate (yacht_id, idempotency_key) in pms_work_orders
**Fix:** ✅ DONE (UUID in description)

#### Failure Mode 5: Invalid Department
**Symptom:** HTTP 400 "Invalid department"
**Detection:** Department not in ['deck', 'engineering', 'interior', 'galley']
**Fix:** Test uses 'deck' (valid)

#### Failure Mode 6: Tenant Lookup Failure
**Symptom:** HTTP 500 "Tenant configuration error"
**Detection:** lookup_tenant_for_user() returns None
**Fix:** Verify MASTER DB user_accounts + fleet_registry have data

---

### JOURNEY 2: Captain Uploads Image

#### Failure Mode 1: ValidationResult.context is None
**Symptom:** HTTP 500 "'ValidationResult' object has no attribute 'get'"
**Detection:** jwt_result.context is None
**Fix:** ✅ DONE (null check)

#### Failure Mode 2: Part Doesn't Exist
**Symptom:** HTTP 404 "Part not found"
**Detection:** No row in pms_parts for (yacht_id, part_id)
**Fix:** Verify part '5dd34337-c4c4-41dd-9c6b-adf84af349a8' exists

#### Failure Mode 3: Storage Bucket Missing
**Symptom:** HTTP 500 "Bucket not found"
**Detection:** Supabase Storage bucket 'pms-part-images' doesn't exist
**Fix:** Create bucket or verify exists

#### Failure Mode 4: Storage Upload Fails
**Symptom:** HTTP 500 "Failed to upload file to storage"
**Detection:** self.db.storage.from_(bucket).upload() raises exception
**Fix:** Verify storage credentials and permissions

#### Failure Mode 5: Storage Permission Denied
**Symptom:** HTTP 500 "Permission denied"
**Detection:** RLS policy blocks upload to {yacht_id}/parts/{part_id}/images/*
**Fix:** Verify storage policies allow authenticated users to upload

#### Failure Mode 6: File Too Large
**Symptom:** HTTP 413 "Payload too large"
**Detection:** File size > Supabase limit (50MB default)
**Fix:** Test uses 100x100 PNG (~5KB)

#### Failure Mode 7: Invalid MIME Type
**Symptom:** HTTP 400 "Invalid mime type"
**Detection:** mime_type not in ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
**Fix:** Test uses 'image/png' (valid)

#### Failure Mode 8: Database Update Fails
**Symptom:** HTTP 500 after upload succeeds
**Detection:** UPDATE pms_parts fails (constraint violation, lock timeout)
**Fix:** Verify pms_parts constraints and no locks

#### Failure Mode 9: Yacht Isolation Violation
**Symptom:** HTTP 403 "Yacht access denied"
**Detection:** yacht_id in form data != yacht_id from tenant lookup
**Fix:** Test uses correct yacht_id

#### Failure Mode 10: Tenant Key Alias Missing
**Symptom:** HTTP 500 "Failed to get tenant client"
**Detection:** lookup_tenant_for_user() returns None for tenant_key_alias
**Fix:** Verify fleet_registry has tenant_key_alias for yacht

#### Failure Mode 11: Tenant Supabase Client Creation Fails
**Symptom:** HTTP 500 "Database connection failed"
**Detection:** get_tenant_supabase_client() returns None
**Fix:** Verify env vars {tenant_key_alias}_SUPABASE_URL and _SERVICE_KEY exist

---

### JOURNEY 3: HOD Updates Image Description

#### Failure Mode 1: Same ValidationResult.context Bug
**Symptom:** HTTP 500 "'ValidationResult' object has no attribute 'get'"
**Fix:** ✅ DONE (null check at line 861)

#### Failure Mode 2: No Image to Update
**Symptom:** HTTP 404 "Part has no image"
**Detection:** pms_parts.image_storage_path IS NULL
**Fix:** Run Journey 2 first OR check for null and skip gracefully

#### Failure Mode 3: image_id != part_id
**Symptom:** HTTP 404 "Part not found"
**Detection:** MVP uses image_id = part_id, but test might use wrong ID
**Fix:** Test uses correct part_id as image_id

#### Failure Mode 4: Empty Description
**Symptom:** HTTP 400 "Description required"
**Detection:** Request body missing 'description' field
**Fix:** Test includes description

---

### JOURNEY 4: NLP Search for Parts

#### Failure Mode 1: Query Doesn't Match Anchors
**Symptom:** domain=None, actions=0
**Detection:** "teak seam compound" doesn't match any pattern in COMPOUND_ANCHORS['part']
**Fix:** ✅ DONE (added marine part anchors)

#### Failure Mode 2: Extractor Not Loaded
**Symptom:** HTTP 500 "Extractor not available"
**Detection:** Extractor module not loaded at startup
**Fix:** Verify extractor initialization in pipeline_service.py

#### Failure Mode 3: Multiple Domain Matches
**Symptom:** domain='work_order' (wrong domain chosen)
**Detection:** Query matches both 'part' and 'work_order' anchors, priority logic picks wrong one
**Fix:** Verify domain priority order

#### Failure Mode 4: Low Confidence
**Symptom:** domain=None despite match
**Detection:** Confidence < 0.6 threshold
**Fix:** Strengthen pattern matches

#### Failure Mode 5: No Actions for Domain
**Symptom:** domain='parts' but actions=[]
**Detection:** DOMAIN_MICROACTIONS[('parts', 'READ')] is empty OR role filtering removes all
**Fix:** Verify microactions registry and role has access

#### Failure Mode 6: Intent Detection Wrong
**Symptom:** intent='CREATE' instead of 'READ'
**Detection:** Query triggers CREATE patterns instead of READ
**Fix:** Verify intent detection rules

---

### JOURNEY 5: Version Check

#### Failure Mode 1: Version Endpoint Missing
**Symptom:** HTTP 404
**Detection:** Route not registered in pipeline_service.py
**Fix:** Already working (✅ PASS in tests)

---

## ADDITIONAL FAILURE MODES NOT IN JOURNEYS

### Image Deletion (Not in E2E but exists)

#### Failure Mode 1: Not Captain/Manager
**Symptom:** HTTP 403 "Role not authorized"
**Detection:** signature.get("role_at_signing") not in ["captain", "manager"]
**Fix:** Only Captain/Manager can delete

#### Failure Mode 2: Missing Signature
**Symptom:** HTTP 400 "Signature required for SIGNED action"
**Detection:** signature field missing or empty
**Fix:** SIGNED actions require PIN+TOTP

#### Failure Mode 3: Invalid PIN/TOTP
**Symptom:** HTTP 401 "Invalid signature"
**Detection:** PIN or TOTP verification fails
**Fix:** Signature validation logic

---

## COMPREHENSIVE VALIDATION SCRIPT

```python
#!/usr/bin/env python3
"""
Complete system validation before E2E tests
"""
import os
import sys
from supabase import create_client

def validate_database_state():
    """Validate all required database state exists"""
    print("🔍 Validating database state...")

    # TENANT DB
    tenant_url = os.getenv("TENANT_SUPABASE_URL")
    tenant_key = os.getenv("TENANT_SUPABASE_SERVICE_KEY")
    tenant_db = create_client(tenant_url, tenant_key)

    yacht_id = "85fe1119-b04c-41ac-80f1-829d23322598"

    # Check test parts exist
    parts = tenant_db.table("pms_parts").select("id, name").eq("yacht_id", yacht_id).in_("id", [
        "5dd34337-c4c4-41dd-9c6b-adf84af349a8",
        "2f452e3b-bf3e-464e-82d5-7d0bc849e6c0",
        "5543266b-2d8c-46a0-88e2-74a7ab403cdd",
    ]).execute()

    if len(parts.data) != 3:
        print(f"   ❌ Expected 3 test parts, found {len(parts.data)}")
        return False
    print(f"   ✅ Test parts exist: {len(parts.data)}")

    # Check user roles
    user_ids = [
        "b72c35ff-e309-4a19-a617-bfc706a78c0f",  # Captain
        "89b1262c-ff59-4591-b954-757cdf3d609d",  # HOD
        "2da12a4b-c0a1-4716-80ae-d29c90d98233",  # Crew
    ]

    roles = tenant_db.table("auth_users_roles").select("user_id, role").eq("yacht_id", yacht_id).eq("is_active", True).in_("user_id", user_ids).execute()

    if len(roles.data) != 3:
        print(f"   ❌ Expected 3 active roles, found {len(roles.data)}")
        return False
    print(f"   ✅ User roles active: {len(roles.data)}")

    # Check crew department
    crew_profile = tenant_db.table("auth_users_profiles").select("metadata").eq("id", "2da12a4b-c0a1-4716-80ae-d29c90d98233").eq("yacht_id", yacht_id).single().execute()

    crew_dept = crew_profile.data.get("metadata", {}).get("department") if crew_profile.data else None
    if not crew_dept:
        print(f"   ❌ Crew missing department metadata")
        return False
    print(f"   ✅ Crew department: {crew_dept}")

    return True

def validate_storage():
    """Validate Supabase Storage bucket exists"""
    print("\n🔍 Validating storage...")

    tenant_url = os.getenv("TENANT_SUPABASE_URL")
    tenant_key = os.getenv("TENANT_SUPABASE_SERVICE_KEY")
    tenant_db = create_client(tenant_url, tenant_key)

    try:
        buckets = tenant_db.storage.list_buckets()
        bucket_names = [b["name"] for b in buckets]

        if "pms-part-images" not in bucket_names:
            print(f"   ❌ Bucket 'pms-part-images' not found")
            print(f"   Available: {bucket_names}")
            return False

        print(f"   ✅ Storage bucket exists: pms-part-images")
        return True
    except Exception as e:
        print(f"   ❌ Storage check failed: {e}")
        return False

def validate_environment():
    """Validate all required environment variables"""
    print("\n🔍 Validating environment variables...")

    required = [
        "MASTER_SUPABASE_URL",
        "MASTER_SUPABASE_ANON_KEY",
        "MASTER_SUPABASE_SERVICE_KEY",
        "TENANT_SUPABASE_URL",
        "TENANT_SUPABASE_SERVICE_KEY",
    ]

    missing = [var for var in required if not os.getenv(var)]

    if missing:
        print(f"   ❌ Missing: {', '.join(missing)}")
        return False

    print(f"   ✅ All required env vars set")
    return True

def validate_master_db():
    """Validate MASTER DB has required data"""
    print("\n🔍 Validating MASTER DB...")

    master_url = os.getenv("MASTER_SUPABASE_URL")
    master_key = os.getenv("MASTER_SUPABASE_SERVICE_KEY")
    master_db = create_client(master_url, master_key)

    # Check user_accounts
    user_ids = [
        "b72c35ff-e309-4a19-a617-bfc706a78c0f",
        "89b1262c-ff59-4591-b954-757cdf3d609d",
        "2da12a4b-c0a1-4716-80ae-d29c90d98233",
    ]

    accounts = master_db.table("user_accounts").select("id, yacht_id").in_("id", user_ids).execute()

    if len(accounts.data) != 3:
        print(f"   ❌ Expected 3 user accounts, found {len(accounts.data)}")
        return False
    print(f"   ✅ User accounts exist: {len(accounts.data)}")

    # Check fleet_registry
    yacht_id = "85fe1119-b04c-41ac-80f1-829d23322598"
    fleet = master_db.table("fleet_registry").select("yacht_id, tenant_key_alias").eq("yacht_id", yacht_id).single().execute()

    if not fleet.data:
        print(f"   ❌ Yacht not in fleet_registry")
        return False

    tenant_key = fleet.data.get("tenant_key_alias")
    if not tenant_key:
        print(f"   ❌ Missing tenant_key_alias")
        return False

    print(f"   ✅ Fleet registry: tenant_key={tenant_key}")
    return True

def main():
    print("=" * 70)
    print("COMPLETE SYSTEM VALIDATION")
    print("=" * 70)

    checks = [
        ("Environment Variables", validate_environment),
        ("MASTER Database", validate_master_db),
        ("TENANT Database", validate_database_state),
        ("Supabase Storage", validate_storage),
    ]

    all_pass = True
    for name, check_fn in checks:
        if not check_fn():
            all_pass = False

    print("\n" + "=" * 70)
    if all_pass:
        print("✅ ALL VALIDATIONS PASSED - Ready for E2E tests")
        print("=" * 70)
        sys.exit(0)
    else:
        print("❌ VALIDATION FAILED - Fix issues before running E2E tests")
        print("=" * 70)
        sys.exit(1)

if __name__ == "__main__":
    main()
```

---

## MISSING TEST COVERAGE

### Tests We Should Add

1. **Error Cases**
   - Upload image to non-existent part (expect 404)
   - Upload image without auth (expect 401)
   - Upload image to wrong yacht (expect 403)
   - Upload oversized file (expect 413)
   - Upload invalid MIME type (expect 400)

2. **Edge Cases**
   - Update image when no image exists (expect 404 or create new)
   - Upload image twice (overwrite or error?)
   - Delete image then try to update (expect 404)
   - Search with very vague query (expect explore mode)
   - Search with multiple domain matches (expect priority logic)

3. **Concurrent Operations**
   - Two users upload to same part simultaneously
   - User creates work order while another user views it
   - Image upload while another user updates description

4. **Data Integrity**
   - Verify audit log written for all operations
   - Verify storage path matches database metadata
   - Verify yacht isolation enforced on all operations

---

## DEPLOYMENT CHECKLIST

Before declaring success:

### Infrastructure
- [ ] Supabase Storage bucket 'pms-part-images' exists
- [ ] Storage RLS policies allow authenticated uploads to yacht paths
- [ ] Storage bucket size limits configured
- [ ] Storage CDN/public URL generation working

### Database
- [ ] All test parts exist in pms_parts
- [ ] All test users exist in auth_users_roles with is_active=TRUE
- [ ] Crew user has metadata->department set
- [ ] MASTER DB user_accounts has all test users
- [ ] MASTER DB fleet_registry has yacht with tenant_key_alias

### Environment Variables
- [ ] MASTER_SUPABASE_URL
- [ ] MASTER_SUPABASE_ANON_KEY
- [ ] MASTER_SUPABASE_SERVICE_KEY
- [ ] MASTER_SUPABASE_JWT_SECRET
- [ ] TENANT_SUPABASE_URL
- [ ] TENANT_SUPABASE_SERVICE_KEY
- [ ] {tenant_key_alias}_SUPABASE_URL
- [ ] {tenant_key_alias}_SUPABASE_SERVICE_KEY

### Code Deployment
- [ ] PR #208 merged to main
- [ ] Render auto-deploy completed (check /version)
- [ ] All 3 image endpoints return 200 with valid auth
- [ ] NLP search detects 'teak seam compound' as domain=parts
- [ ] Work order creation succeeds for crew with UUID

### Monitoring
- [ ] API logs show no errors for image uploads
- [ ] Storage upload metrics show successful uploads
- [ ] Audit logs written for all operations
- [ ] No 500 errors in Render logs

---

## FINAL E2E TEST (COMPREHENSIVE)

```bash
# Pre-flight validation
python3 validate_system.py

# Run E2E tests
export MASTER_SUPABASE_ANON_KEY="..."
export CAPTAIN_PASSWORD="Password2!"
export HOD_PASSWORD="Password2!"
export CREW_PASSWORD="Password2!"

python3 test_e2e_journeys.py

# Expected: ALL 5 PASS
# ✅ Journey 1: Crew creates work order (HTTP 200)
# ✅ Journey 2: Captain uploads image (HTTP 200)
# ✅ Journey 3: HOD updates image (HTTP 200)
# ✅ Journey 4: NLP search (domain=parts, actions>0)
# ✅ Journey 5: Version check (HTTP 200, v2026.02.09.003)
```

---

## RISK MATRIX

| Risk | Probability | Impact | Mitigation Status |
|------|-------------|--------|-------------------|
| JWT validation bug | HIGH | HIGH | ✅ FIXED (null check) |
| NLP domain detection | HIGH | MEDIUM | ✅ FIXED (marine anchors) |
| Test idempotency | HIGH | LOW | ✅ FIXED (UUID) |
| Storage bucket missing | LOW | HIGH | ⚠️ VERIFY |
| Storage permissions wrong | LOW | HIGH | ⚠️ VERIFY |
| Part doesn't exist | LOW | MEDIUM | ⚠️ VERIFY |
| Crew missing department | LOW | HIGH | ✅ FIXED |
| Crew missing role | LOW | HIGH | ⚠️ VERIFY |
| Tenant lookup fails | LOW | HIGH | ⚠️ VERIFY |
| Database connection fails | LOW | HIGH | ⚠️ VERIFY |

---

This is EVERYTHING. Every dependency, every failure mode, every edge case, every validation needed.
