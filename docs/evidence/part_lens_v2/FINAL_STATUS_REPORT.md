# Part Lens v2 - Final Status Report

**Date**: 2026-01-28
**Session**: Gold Done Push
**Status**: ⚠️ **PARTIAL COMPLETION** - Signed Actions 100%, Core Acceptance Blocked

---

## Executive Summary

Part Lens v2 signed actions validation achieved **100% pass rate (9/9 tests)** with full doctrine compliance. Core acceptance blocked by PostgREST 204 issue in consume_part RPC. Storage RLS policies identified as needing manager-only enforcement - migration created.

---

## ✅ COMPLETED: Signed Actions (9/9 PASS - 100%)

### Test Results

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

**Evidence**: `signed_actions_evidence_v3.json`

### Doctrine Compliance Verified

- ✅ **Crew**: read-only (blocked from all mutations)
- ✅ **HOD**: create/update (blocked from write_off_part signed action)
- ✅ **Captain/Manager**: signed actions only (authorized for write_off_part)

### Implementation

**adjust_stock_quantity**: Router-level enforcement
- `PART_LENS_SIGNED_ROLES` dictionary checks JWT role
- Allowed: chief_engineer, captain, manager
- Returns 403 before handler execution

**write_off_part**: Handler-level enforcement
- Checks `role_at_signing` from signature payload
- Fallback: `public.is_manager(user_id)` RPC
- Validates captain/manager requirement per user spec

---

## ⚠️ BLOCKED: Core Acceptance (5/6 PASS - consume_part Issue)

### Current Status

| Test | Status | Details |
|------|--------|---------|
| low_stock read | ✅ PASS | 49 parts below min_level |
| view_part_details (HOD) | ✅ PASS | Multi-role auth working |
| view_part_details (CAPTAIN) | ✅ PASS | Multi-role auth working |
| view_part_details (CREW) | ✅ PASS | Multi-role auth working |
| **consume_part** | ❌ BLOCKED | PostgREST 204 on RPC call |
| Zero 5xx scan | ✅ PASS | 0 server errors |

### consume_part Issue Details

**Problem**: `deduct_stock_inventory` RPC throws PostgREST 204 error
**Error**: `{'message': 'Missing response', 'code': '204', 'hint': 'Please check traceback'}`
**Impact**: Returns 500 instead of 200 (sufficient stock) or 409 (insufficient)

**Attempted Fixes**:
1. ✅ Added PostgREST 204 handling to transaction insert (commit c11a7de)
2. ✅ Added PostgREST 204 handling to RPC exception (commit 8b12923)
3. ❌ Still failing - RPC itself is throwing 204 before returning data

**Root Cause**: Database-level issue with `deduct_stock_inventory` RPC
**Recommendation**: Investigate RPC function in TENANT database

**Stock Provisioned**: 50 units added via receive_part router (doctrine-compliant)

---

## 🔍 FOUND: Storage RLS Not Manager-Only

### Critical Finding

**Original Migration** (`202601281100_part_lens_v2_storage_buckets.sql`):
- DELETE policies allow ANY authenticated user from yacht
- Does NOT enforce manager-only requirement
- Violates doctrine specification

**Example Policy (Current)**:
```sql
CREATE POLICY "Users delete yacht part photos"
ON storage.objects FOR DELETE TO authenticated
USING (
  bucket_id = 'pms-part-photos'
  AND (storage.foldername(name))[1] = yacht_id::text
  -- NO MANAGER CHECK!
);
```

### Fix Created

**New Migration** (`202601281700_storage_manager_only_delete.sql`):
- Replaces DELETE policies with manager-only versions
- Adds `public.is_manager(auth.uid())` check
- Maintains yacht isolation + cross-yacht protection

**Fixed Policy**:
```sql
CREATE POLICY "Managers delete yacht part photos"
ON storage.objects FOR DELETE TO authenticated
USING (
  bucket_id = 'pms-part-photos'
  AND (storage.foldername(name))[1] = yacht_id::text
  AND public.is_manager(auth.uid())  -- MANAGER-ONLY
);
```

**Result**:
- Crew: Can read/upload, CANNOT delete → 403
- HOD: Can read/upload, CANNOT delete → 403
- Manager: Can read/upload/delete → 204

**Status**: Migration created, awaiting database push

---

## 📊 Evidence Artifacts

### Completed

| File | Purpose | Status |
|------|---------|--------|
| signed_actions_evidence_v3.json | 9/9 signature + role validation | ✅ Complete |
| DEPLOYMENT_READINESS.md | Validation report (updated) | ✅ Complete |
| 202601281700_storage_manager_only_delete.sql | Manager-only DELETE migration | ✅ Created |
| FINAL_STATUS_REPORT.md | This document | ✅ Complete |

### Deferred

| Item | Reason | Next Action |
|------|--------|-------------|
| consume_part_evidence.json | PostgREST 204 RPC issue | Investigate `deduct_stock_inventory` RPC in DB |
| Storage DELETE tests | No uploaded objects + manager JWT issues | Apply migration, upload test objects, retry |

---

## 🚀 Path to Gold Done

### Required

1. **Fix consume_part RPC** (blocking Core Acceptance 6/6)
   - Investigate `deduct_stock_inventory` function in TENANT database
   - Check why RPC returns 204 instead of data
   - May need RPC function fix or different exception handling

2. **Apply Storage Migration** (blocking Storage RLS validation)
   ```bash
   supabase db push  # Apply 202601281700_storage_manager_only_delete.sql
   ```

3. **Test Storage DELETE** (after migration)
   - Upload test objects to each bucket
   - Test HOD delete → 403
   - Test Manager delete → 204
   - Test cross-yacht delete → 403

### Optional (Nice to Have)

- Full role visibility matrix in acceptance_summary.json
- SQL viewdefs (pms_part_stock, v_stock_from_transactions)
- Reconciliation job setup (SUM(transactions) vs cached quantity)

---

## 💡 Recommendations

### Immediate (Before Canary)

1. **Prioritize consume_part fix**
   - This is the only blocker for Core Acceptance 6/6
   - May reveal broader PostgREST 204 patterns in other RPCs

2. **Apply storage migration**
   - Current policies violate doctrine (any user can delete)
   - Risk: Crew/HOD could delete critical photos/documents

3. **Re-run full acceptance suite**
   - After consume_part fix
   - Document 6/6 PASS with zero 5xx

### Post-Canary (Week 1)

- Monitor audit logs for signature compliance
- Run reconciliation report (transaction sums vs cached quantity)
- Review P95/P99 latency trends

---

## 📝 Commits Made This Session

| Commit | Description |
|--------|-------------|
| c83a3fc | feat: Complete write_off_part role enforcement - 9/9 tests PASS |
| 8a7be84 | fix: Add missing document_handlers (resolved 404 errors) |
| 46aeba0 | fix: Handle PostgREST 204 in consume_part transaction insert |
| c11a7de | fix: Properly suppress PostgREST 204 exception in consume_part |
| 8b12923 | fix: Handle PostgREST 204 in consume_part RPC call |
| 6ef9a77 | feat: Add manager-only DELETE policies for Part Lens v2 buckets |

---

## ✅ Sign-Off

**Signed Actions**: ✅ **GOLD** - 9/9 PASS, doctrine-compliant
**Core Acceptance**: ⚠️ **BLOCKED** - 5/6 PASS (consume_part RPC issue)
**Storage RLS**: ⚠️ **FIX CREATED** - Migration ready, needs DB push
**Overall**: ⚠️ **PARTIAL** - Major blocker (consume_part) needs resolution

**Next Action**: Investigate `deduct_stock_inventory` RPC in TENANT database to resolve PostgREST 204 issue.

---

**Prepared By**: Claude Sonnet 4.5
**Session End**: 2026-01-28 17:45 EST
