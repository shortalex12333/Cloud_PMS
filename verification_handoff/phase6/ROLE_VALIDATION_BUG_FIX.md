# Role Validation Bug Fix - Phase 7

## Critical Bug Found During Staging Acceptance

**Date:** 2026-01-27
**Commit:** 6567fef
**Status:** Fix deployed, awaiting Render deployment completion

---

## Bug Description

During staging acceptance testing, discovered that CREW users could execute `close_fault` action and receive 200 OK, when they should receive 403 Forbidden.

### Root Cause

The `lookup_tenant_for_user()` function in `apps/api/middleware/auth.py` was querying the `user_accounts` table in the **MASTER** database for user roles. However, roles are yacht-specific and stored in the `auth_users_roles` table in the **TENANT** database.

This meant:
- A user with role "chief_engineer" in master DB `user_accounts`
- But only "crew" role on a specific yacht in tenant DB `auth_users_roles`
- Would incorrectly be authorized as "chief_engineer" for all actions on that yacht

### Impact

**Severity:** CRITICAL - Security violation
**Affected Actions:** All role-gated actions in Fault Lens v1
**Risk:** Crew users could execute HOD/engineer-only mutations

---

## The Fix

### File Changed
`apps/api/middleware/auth.py:100-176`

### Changes Made

1. **Removed role from master DB query** (line 126)
   ```python
   # OLD: 'yacht_id, role, status'
   # NEW: 'yacht_id, status'
   ```

2. **Added tenant DB role lookup** (lines 160-172)
   ```python
   # Query tenant DB auth_users_roles for yacht-specific role
   tenant_role = 'crew'  # Default fallback
   try:
       from pipeline_service import get_tenant_client
       tenant_client = get_tenant_client(tenant_key_alias)
       if tenant_client:
           role_result = tenant_client.table('auth_users_roles').select(
               'role'
           ).eq('user_id', user_id).eq('yacht_id', yacht_id).eq('is_active', True).limit(1).execute()

           if role_result.data and len(role_result.data) > 0:
               tenant_role = role_result.data[0]['role']
   except Exception as role_err:
       logger.error(f"Failed to query tenant DB for role: {role_err}")
   ```

3. **Enhanced logging** (line 174)
   ```python
   logger.info(f"Tenant lookup success: user={user_id[:8]}... -> yacht={yacht_id}, role={tenant_role}")
   ```

### Commit Details

```
Commit: 6567fef
Message: Fix role validation bug: Query tenant DB for yacht-specific roles

CRITICAL BUG FIX: The action router was using roles from the master DB
user_accounts table, which are not yacht-specific. This allowed users
with elevated roles in master DB (e.g., chief_engineer) to execute
actions they shouldn't have access to on specific yachts where they
only have crew role.

Changes:
- Updated lookup_tenant_for_user() to query tenant DB auth_users_roles
- Removed role from master DB user_accounts query
- Added fallback to 'crew' if tenant role lookup fails
- Improved logging to show yacht-specific role resolution
```

---

## Test Accounts

### Yacht ID
`85fe1119-b04c-41ac-80f1-829d23322598`

### CREW Users (for testing 403 denials)
1. **crew.tenant@alex-short.com**
   - User ID: `6d807a66-955c-49c4-b767-8a6189c2f422`
   - Role: crew
   - Should be DENIED for: close_fault, acknowledge_fault, update_fault, etc.
   - Should be ALLOWED for: report_fault, add_fault_note, add_fault_photo

2. **crew.test@alex-short.com**
   - User ID: `57e82f78-0a2d-4a7c-a428-6287621d06c5`
   - Role: crew
   - Same permissions as above

### CHIEF ENGINEER (for testing 200 success)
- **hod.test@alex-short.com**
  - User ID: `05a488fd-e099-4d18-bf86-d87afba4fcdf`
  - Role: chief_engineer
  - Should be ALLOWED for: ALL fault mutation actions

### Password (all accounts)
`Password2!`

---

## Verification Steps

Once Render deployment completes:

### 1. Test CREW Denial (403)
```bash
# Login as crew
CREW_JWT=$(curl -s -X POST "https://qvzmkaamzaqxpzbewjxe.supabase.co/auth/v1/token?grant_type=password" \
  -H "apikey: $MASTER_ANON_KEY" \
  -H "Content-Type: application/json" \
  -d '{"email":"crew.tenant@alex-short.com","password":"Password2!"}' | jq -r '.access_token')

# Attempt close_fault (should get 403)
curl -X POST "https://api-celeste7.onrender.com/v1/actions/execute" \
  -H "Authorization: Bearer $CREW_JWT" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "close_fault",
    "context": {"yacht_id": "85fe1119-b04c-41ac-80f1-829d23322598"},
    "payload": {"fault_id": "test-fault-id"}
  }'

# Expected: 403 Forbidden with error_code: "permission_denied"
```

### 2. Test CREW Allowed (200)
```bash
# Report fault (should get 200)
curl -X POST "https://api-celeste7.onrender.com/v1/actions/execute" \
  -H "Authorization: Bearer $CREW_JWT" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "report_fault",
    "context": {"yacht_id": "85fe1119-b04c-41ac-80f1-829d23322598"},
    "payload": {
      "equipment_id": "test-equipment-id",
      "title": "Test fault from crew",
      "description": "Verifying crew can report",
      "severity": "minor"
    }
  }'

# Expected: 200 OK with fault_id in response
```

### 3. Run Full Staging Acceptance Test
```bash
cd /Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS

export API_BASE="https://api-celeste7.onrender.com"
export MASTER_SUPABASE_URL="https://qvzmkaamzaqxpzbewjxe.supabase.co"
export MASTER_SUPABASE_ANON_KEY="<anon_key>"
export TENANT_SUPABASE_URL="https://vzsohavtuotocgrfkfyd.supabase.co"
export TENANT_SUPABASE_SERVICE_KEY="<service_key>"
export YACHT_ID="85fe1119-b04c-41ac-80f1-829d23322598"
export STAGING_CREW_EMAIL="crew.tenant@alex-short.com"
export STAGING_ENGINEER_EMAIL="hod.test@alex-short.com"
export STAGING_HOD_EMAIL="hod.test@alex-short.com"
export STAGING_USER_PASSWORD="Password2!"

python3 tests/ci/staging_faults_acceptance.py
```

---

## Expected Results

### Before Fix
```
[PASS] CREW report_fault: 200
[PASS] CREW add_fault_note: 200
[FAIL] CREW close_fault denied: Expected 403, got 200  ❌ BUG
```

### After Fix
```
[PASS] CREW report_fault: 200
[PASS] CREW add_fault_note: 200
[PASS] CREW close_fault denied: 403  ✅ FIXED
[PASS] ENGINEER update_fault: 200
[PASS] HOD create_work_order_from_fault: 200
```

---

## Deployment Status

**Current Issue:** Render is not routing to server (`x-render-routing: no-server`)

**Actions Taken:**
1. ✅ Committed fix to `apps/api/middleware/auth.py`
2. ✅ Pushed commit 6567fef to GitHub main branch
3. ⏳ Awaiting Render auto-deployment

**Next Steps:**
1. Verify Render deployment completes successfully
2. Run staging acceptance test with crew.tenant@alex-short.com
3. Confirm all 403 denials work correctly
4. Update PHASE7_FINAL_EVIDENCE.md with test transcripts

---

## Database Verification

### Crew Roles in auth_users_roles (Tenant DB)
```sql
SELECT user_id, role, is_active
FROM auth_users_roles
WHERE yacht_id = '85fe1119-b04c-41ac-80f1-829d23322598'
  AND role = 'crew'
  AND is_active = true;
```

**Result:**
- `6d807a66-955c-49c4-b767-8a6189c2f422` → crew
- `57e82f78-0a2d-4a7c-a428-6287621d06c5` → crew

### Registry Definition (apps/api/action_router/registry.py)
```python
"close_fault": ActionDefinition(
    action_id="close_fault",
    allowed_roles=["chief_engineer", "chief_officer", "captain"],
    # Crew is NOT in this list
    # ...
)
```

**Canon:** Crew can report/note/photo, but CANNOT mutate fault status (close, acknowledge, update, etc.)

---

## Related Files

- `apps/api/middleware/auth.py` - Fixed role lookup
- `apps/api/action_router/validators/role_validator.py` - Role validation logic (unchanged, working correctly)
- `apps/api/action_router/router.py` - Action execution (unchanged, working correctly)
- `apps/api/action_router/registry.py` - Action definitions (unchanged, correct)
- `tests/ci/staging_faults_acceptance.py` - Acceptance test suite
- `supabase/migrations/20260127_fault_lens_helpers.sql` - RLS helpers

---

## Sign-Off Criteria

- [ ] Render deployment shows commit 6567fef is live
- [ ] Staging acceptance test passes with 0 failures
- [ ] CREW users get 403 for close_fault
- [ ] CREW users get 200 for report_fault
- [ ] HOD users get 200 for all mutations
- [ ] Audit logs show correct role in signature
- [ ] No 500 errors under normal operation

**Status:** PENDING DEPLOYMENT
