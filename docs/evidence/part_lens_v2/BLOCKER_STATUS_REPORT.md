# Part Lens v2 - Blocker Status Report

**Date**: 2026-01-28
**Session**: consume_part + Storage Investigation
**Status**: 🚫 **BLOCKED** - Database-level Issues

---

## Executive Summary

Part Lens v2 implementation is blocked by two critical database-level issues that cannot be resolved from application code:

1. **consume_part**: Pervasive PostgREST 204 "Missing response" errors on ALL query types
2. **Storage RLS**: Storage buckets not created - base migration not applied

**Signed Actions**: ✅ Still 100% (9/9 PASS) - no regression

---

## 🚫 BLOCKER #1: consume_part PostgREST 204 Issue

### Problem

`deduct_stock_inventory` RPC and ALL related queries return PostgREST 204 "Missing response" error:

```
{'message': 'Missing response', 'code': '204',
 'hint': 'Please check traceback of the code',
 'details': "Postgrest couldn't retrieve response..."}
```

### Investigation Completed

| Item | Status | Finding |
|------|--------|---------|
| RPC function definition | ✅ Verified | Correctly returns TABLE (success, quantity_before, quantity_after, error_code) |
| RPC permissions | ✅ Verified | `GRANT EXECUTE ... TO authenticated` present |
| RPC security | ✅ Verified | `SECURITY DEFINER` configured |
| Handler exception handling | ✅ Implemented | Try/except at 3 levels: initial query, RPC call, verification query |
| View fallback | ✅ Implemented | Falls back to base tables (pms_parts + pms_inventory_stock) on 204 |
| Base table fallback | ✅ Implemented | Wrapped in try/except with ConflictError (409) on failure |

### Code Changes Attempted

**Commit aba7dd1**: Wrap RPC verification query in try/except, query base table instead of view
**Commit 709ea16**: Wrap initial stock query in try/except, fall back to base tables on 204

**Result**: Still returns 500 with PostgREST 204 error

### Root Cause Analysis

PostgREST 204 affects:
- ✗ Views (`pms_part_stock`)
- ✗ RPCs (`deduct_stock_inventory`)
- ✗ Base tables (`pms_inventory_stock`, `pms_parts`) - suspected

This suggests a **PostgREST configuration or client version issue**, not a function design or handler code issue.

### Impact

- Core Acceptance: BLOCKED at 5/6 (consume_part fails)
- Cannot test sufficient stock → 200
- Cannot test insufficient stock → 409
- Cannot achieve "zero 5xx" acceptance criteria

### Required Fix

**Database-level investigation required:**

1. Check PostgREST version compatibility with supabase-py client
2. Verify PostgREST configuration for RPC response handling
3. Check database connection pool settings
4. Review PostgREST logs for underlying errors
5. Consider RPC function signature changes (e.g., OUT parameters vs RETURNS TABLE)
6. Test RPC directly via psql to confirm it returns data

**Recommended Next Step**: Query TENANT database directly via psql to test RPC:

```sql
SELECT * FROM public.deduct_stock_inventory(
    '<stock_id>'::UUID,
    5,  -- quantity
    '<yacht_id>'::UUID
);
```

If this returns data, the issue is PostgREST client/server communication, not the function.

---

## 🚫 BLOCKER #2: Storage RLS Testing

### Problem

Storage buckets do not exist in staging database:

```
{"statusCode":"404","error":"Bucket not found","message":"Bucket not found"}
```

### Missing Migrations

| Migration | Status | Purpose |
|-----------|--------|---------|
| `202601281100_part_lens_v2_storage_buckets.sql` | ❌ Not applied | Creates buckets: pms-part-photos, pms-receiving-images, pms-label-pdfs |
| `202601281700_storage_manager_only_delete.sql` | ❌ Not applied | Replaces DELETE policies with manager-only versions |

### Impact

- Cannot upload test objects
- Cannot test HOD delete → 403
- Cannot test Manager delete → 204
- Cannot test cross-yacht delete → 403
- Cannot verify manager-only enforcement

### Required Fix

**Apply both migrations to staging database:**

```bash
# Requires DB credentials
supabase db push

# OR manually apply via Dashboard → SQL Editor:
# 1. Run 202601281100_part_lens_v2_storage_buckets.sql
# 2. Run 202601281700_storage_manager_only_delete.sql
```

**Then retest storage DELETE policies:**

```bash
python3 upload_test_objects.py  # Upload test files
python3 test_storage_rls_delete.py  # Test DELETE enforcement
```

---

## ✅ COMPLETED: Signed Actions (No Regression)

| Category | Test | Status | Result |
|----------|------|--------|--------|
| **adjust_stock_quantity** | Missing signature | ✅ PASS | 400 "Missing required field(s): signature" |
| | Invalid signature | ✅ PASS | 400 "Signature must contain 'pin' and 'totp'" |
| | Crew forbidden | ✅ PASS | 403 "Role 'crew' forbidden" |
| | HOD authorized | ✅ PASS | 200 success |
| **write_off_part** | Missing signature | ✅ PASS | 400 "Missing required field(s): signature" |
| | Invalid signature | ✅ PASS | 400 "Missing required field(s): signature" |
| | Crew forbidden | ✅ PASS | 403 "write_off_part requires Captain/Manager role" |
| | HOD forbidden | ✅ PASS | 403 "write_off_part requires Captain/Manager role" |
| | Manager authorized | ✅ PASS | 200 success (validates role_at_signing) |

**Evidence**: `signed_actions_evidence_v3.json` (unchanged)

---

## 📊 Acceptance Criteria Status

| Criterion | Target | Current | Status |
|-----------|--------|---------|--------|
| Core Acceptance | 6/6 PASS | 5/6 (consume_part blocked) | ⚠️ BLOCKED |
| Zero 5xx | 0 errors | 2/2 tests return 500 | ⚠️ BLOCKED |
| Signed Actions | 100% | 9/9 PASS (100%) | ✅ COMPLETE |
| Storage RLS | Manager-only DELETE | Cannot test (no buckets) | ⚠️ BLOCKED |
| Stress Tests | >99%, P95 < 500ms | Not started (blocked) | ⏸️ PENDING |

**Overall**: Cannot proceed to gold done until database issues resolved

---

## 🔧 Commits Made This Session

| Commit | Description | Status |
|--------|-------------|--------|
| aba7dd1 | Wrap consume_part 204 fallback query in try/except | ⚠️ Deployed but still failing |
| 709ea16 | Handle PostgREST 204 on initial stock query | ⚠️ Deployed but still failing |

---

## 🚀 Path Forward

### Immediate (Unblock Core Acceptance)

1. **Investigate PostgREST 204 issue** (database admin required)
   - Test RPC directly via psql
   - Check PostgREST version and configuration
   - Review PostgREST logs for underlying errors
   - Consider RPC signature changes if client/server incompatibility found

2. **Apply storage migrations** (database push required)
   - Apply `202601281100_part_lens_v2_storage_buckets.sql`
   - Apply `202601281700_storage_manager_only_delete.sql`
   - Verify buckets created via Dashboard

3. **Retest after fixes**
   - consume_part: 200 (sufficient) and 409 (insufficient)
   - Storage DELETE: HOD 403, Manager 204, cross-yacht 403

### Once Unblocked

4. Re-run Core Acceptance to 6/6 PASS
5. Zero 5xx scan
6. Stress tests (CONCURRENCY=10, REQUESTS=50)
7. Final evidence bundle

---

## 💡 Recommendations

### Critical

1. **Prioritize PostgREST 204 investigation**
   - This is the ONLY blocker for Core Acceptance 6/6
   - May reveal broader patterns affecting other RPCs
   - Likely requires DB admin or DevOps support

2. **Apply storage migrations ASAP**
   - Current policies violate doctrine (any user can delete)
   - Risk: Crew/HOD could delete critical photos/documents
   - 5-minute fix once DB access available

### Optional

- Consider switching to direct psycopg2 queries if PostgREST continues to have issues
- Add PostgREST version check to CI/CD pipeline
- Document PostgREST 204 troubleshooting in runbook

---

## 📝 Artifacts

| File | Purpose | Status |
|------|---------|--------|
| signed_actions_evidence_v3.json | 9/9 signature + role validation | ✅ Complete |
| consume_part_evidence.json | PostgREST 204 failures | ✅ Documented |
| BLOCKER_STATUS_REPORT.md | This document | ✅ Complete |
| 202601281700_storage_manager_only_delete.sql | Manager-only DELETE migration | ⏳ Ready, not applied |

---

**Prepared By**: Claude Sonnet 4.5
**Session End**: 2026-01-28 (PostgREST investigation session)
**Next Action**: Database admin must investigate PostgREST 204 issue and apply storage migrations
