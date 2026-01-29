# Part Lens v2 - Hour 0 Results

**Date**: 2026-01-28
**Time**: Hour 0-1 Complete
**Status**: ✅ **DIRECT SQL FIX SUCCESSFUL**

---

## Deployment Verification

### 1. Health Check
```bash
GET /health
Status: 200
Response: {"status":"healthy","version":"1.0.0","pipeline_ready":true}
```
✅ **PASS**: Staging API healthy

### 2. view_part_details (Direct SQL)
```bash
POST /v1/actions/execute
Action: view_part_details
Part ID: 8ad67e2f-2579-4d6c-afd2-0dee85f4d8b3
```

**Result**:
- Status: **200** (was 400/204 before fix)
- Stock retrieved: `on_hand=37`
- **ROOT CAUSE FIXED**: Direct SQL via TenantPGGateway bypasses PostgREST 204

✅ **PASS**: Canonical read working

### 3. consume_part (RPC + SQL Confirmation)
```bash
POST /v1/actions/execute
Action: consume_part
Quantity: 1
```

**Test 1 - Sufficient Stock**:
- Status: **200**
- Quantity Before: 77
- Quantity After: 76
- Transaction ID: `19649e02-590d-431c-a082-0b88b3699ccd`

✅ **PASS**: Consume succeeded

**Test 2 - Insufficient Stock**:
- Status: **409**
- Message: Correctly rejected

✅ **PASS**: Validation working

---

## Direct SQL Implementation Verified

### TenantPGGateway Working
- psycopg2 connection to vzsohavtuotocgrfkfyd.supabase.co
- `get_part_stock()` returns data from pms_part_stock view
- Yacht-scoped filtering applied (yacht_id in WHERE clause)
- No PostgREST 204 errors

### Handler Changes Validated
1. **view_part_details**:
   - Uses `get_part_stock(tenant_key_alias, yacht_id, part_id)`
   - Returns 200 with stock data
   - No more PostgREST `.maybe_single()` issues

2. **consume_part**:
   - Pre-check via SQL: `qty_before < quantity` → 409
   - RPC call: `deduct_stock_inventory`
   - If RPC returns 204: SQL confirmation query
   - Verification: `qty_after == qty_before - quantity`

---

## Storage Migration Applied

### Migration: `20260128_storage_manager_only_delete.sql`
- **Applied**: User confirmed pushed to TENANT_1
- **Policies Created**: 3 manager-only DELETE policies
  - `pms-part-photos`
  - `pms-receiving-images`
  - `pms-label-pdfs`

### Verification Needed
**SQL Query**:
```sql
SELECT policyname, cmd
FROM pg_policies
WHERE schemaname = 'storage'
  AND tablename = 'objects'
  AND cmd = 'DELETE'
  AND policyname LIKE 'Managers delete%';
```

**Expected**: 3 rows

### Testing Status
- [ ] HOD delete → 403 (all 3 buckets)
- [ ] Manager delete → 204 (all 3 buckets) - **Blocked: Need Manager JWT**
- [ ] Cross-yacht → 403 (all 3 buckets)

---

## Evidence Generated

### Test Results
1. **health_check.txt**: 200 OK
2. **view_part_details_200.json**: Stock data retrieved
3. **consume_part_sufficient_200.json**: Qty 77 → 76
4. **consume_part_insufficient_409.json**: Rejected correctly

### Logs
- Render logs should show: `[PGGateway] Connected to yTEST_YACHT_001`
- No PostgREST 204 errors in consume/view actions

---

## Hour 0 Summary

| Test | Status | Notes |
|------|--------|-------|
| Health endpoint | ✅ PASS | 200 OK |
| view_part_details | ✅ PASS | 200, was 400/204 |
| consume_part (sufficient) | ✅ PASS | 200, qty 77→76 |
| consume_part (insufficient) | ✅ PASS | 409 rejection |
| Storage RLS verification | 🚧 PENDING | Need Manager JWT |

**Zero 5xx errors observed**

---

## Next Steps (Hour 1-2)

### Storage RLS Testing
**Blocked Item**: Manager JWT required for testing Manager delete → 204

**Options**:
1. User provides Manager JWT → Run full storage tests
2. Skip Manager tests → Document as manual verification
3. Create Manager user → Generate JWT → Test

**Once unblocked**:
- Run `tests/acceptance/test_storage_rls_delete.py`
- Verify HOD 403, Manager 204, cross-yacht 403
- Generate `storage_rls_403_evidence.json`

### Core Acceptance (Hour 2-4)
- receive_part: 201, duplicate → 409
- transfer_part: net-zero, by-location correct
- adjust_stock_quantity: 400 missing sig, 200 signed
- write_off_part: 400 missing sig, 200 signed
- Role visibility: Crew/HOD/Captain/Manager

---

## Acceptance Criteria Met (Hour 0)

- [x] Staging deployed from security/signoff
- [x] Health endpoint 200
- [x] view_part_details 200 (direct SQL working)
- [x] consume_part 200/409 (RPC + SQL confirmation)
- [x] Storage migration applied
- [x] Zero 5xx errors
- [ ] Storage RLS tests (pending Manager JWT)

**Status**: ✅ **On track for 6/6 PASS**

---

**Prepared By**: Claude Sonnet 4.5
**Session Duration**: 1 hour
**Commits Tested**: `b0cacd3` (security/signoff branch)
