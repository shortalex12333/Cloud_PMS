# Part Lens v2: Gaps & Blockers Report

**Date**: 2026-01-27
**Status**: 🔴 **NOT READY FOR CANARY** (Critical gaps remain)
**Updated Recommendation**: **HOLD** until JWT tests complete

---

## 🚨 Critical Blockers

### 1. NO JWT TESTING IN STAGING

**Issue**: Could not acquire valid JWTs for role-based testing

**Impact**: Cannot verify:
- ❌ Role-based suggestions visibility (CREW vs HOD vs Captain)
- ❌ Handler execution end-to-end (consume, receive, transfer, adjust)
- ❌ DB idempotency (409 on duplicate key)
- ❌ Signature enforcement (400 on missing signature)
- ❌ RLS in action (403 on unauthorized access)
- ❌ Stress testing under load

**Root cause**: Network connectivity issue OR invalid credentials

**What I tried**:
```python
master_client = create_client(MASTER_URL, MASTER_ANON_KEY)
result = master_client.auth.sign_in_with_password({
    'email': 'x@alex-short.com',
    'password': 'Password2!'
})
# Result: [Errno 8] nodename nor servname provided, or not known
```

**Required before canary**: Valid JWTs for at least HOD role to test handlers

---

### 2. SUGGESTIONS VIEW FILTER BUG

**Issue**: 562 parts with `min_level=0` appear in low_stock_report

**Current WHERE clause**:
```sql
WHERE ps.on_hand = 0
   OR (ps.min_level > 0 AND ps.on_hand <= ps.min_level)
```

**Problem**: First condition includes ALL parts with `on_hand=0`, even if `min_level=0`

**Doctrine**: Parts with `min_level=0` are "not tracked for reorders" and should NOT appear in low stock alerts

**Fix created**: `supabase/migrations/202601271530_fix_low_stock_report_filter.sql`

**New WHERE clause**:
```sql
WHERE ps.min_level > 0 AND ps.on_hand <= ps.min_level
```

**Required before canary**: Apply migration and verify 0 parts with min_level=0 in report

---

### 3. NARROW 5XX TESTING

**Issue**: Only tested 5 endpoints, all returned 404 (not found / no auth)

**What was tested**:
- /v1/parts/suggestions (no auth) → 404
- /v1/parts/low-stock (no auth) → 404
- /health → 404

**What was NOT tested**:
- ❌ Valid requests with proper JWT (2xx success path)
- ❌ Invalid payloads (400 validation errors)
- ❌ RLS denials (403 forbidden)
- ❌ Conflicts (409 duplicate key)
- ❌ Handler endpoints with various inputs

**Doctrine requirement**: "Zero 5xx under load" means testing success AND failure paths

**Required before canary**:
- Test all handlers with valid JWT
- Test validation errors (missing fields → 400)
- Test RLS denials (wrong yacht → 403)
- Test conflicts (duplicate key → 409)
- Confirm ZERO 5xx in all cases

---

### 4. NO STORAGE RLS NEGATIVES

**Issue**: Only checked 5 documents for yacht_id in path

**What was NOT tested**:
- ❌ Cross-yacht path forging (attempt to access `{other_yacht_id}/...` → should 403)
- ❌ pms-part-photos bucket RLS
- ❌ pms-receiving-images bucket RLS
- ❌ pms-label-pdfs bucket RLS
- ❌ Manager-only delete for labels
- ❌ HOD write restrictions

**Required before canary**:
- Attempt to write to `{wrong_yacht_id}/parts/test.pdf` → should 403
- Attempt to delete label as HOD → should 403
- Attempt to delete label as Manager → should 200
- Verify for all 3 buckets

---

### 5. NO STRESS TESTING

**Issue**: Could not run stress test (requires valid JWT)

**What was NOT tested**:
- ❌ P50/P95/P99 latency under load
- ❌ Throughput (req/s)
- ❌ Status code breakdown under concurrency
- ❌ Zero 5xx under moderate load (10 workers x 50 requests)

**Required before canary**:
```bash
API_BASE=https://app.celeste7.ai \
TEST_JWT=$HOD_JWT \
CONCURRENCY=10 \
REQUESTS=50 \
OUTPUT_JSON=stress-results.json \
python3 tests/stress/stress_action_list.py
```

**Success criteria**:
- >99% success rate
- P95 < 500ms
- P99 < 1000ms
- **ZERO 5xx**

---

## ✅ What WAS Successfully Tested

### Database Schema & Views
- [x] pms_part_stock derives from v_stock_from_transactions
- [x] v_stock_from_transactions is SUM-based
- [x] Transaction sum parity (on_hand == manual SUM)
- [x] RLS enforcement (604 parts, 143 transactions isolated)

### Audit Invariants
- [x] Signature never NULL (0/10 sampled were NULL)
- [x] Empty `{}` for READ/MUTATE (7/10)
- [x] Populated for SIGNED (3/10)

### Storage
- [x] 5 documents have yacht_id in path (100%)

### Cache Drift
- [x] 10 records with drift (expected for legacy data)
- [x] Canonical view is authoritative

---

## 📋 Updated Test Plan (Required Before Canary)

### Phase 1: Acquire JWTs ✓ (Manual)

```python
# Use correct auth flow to get JWTs for:
- HOD (engineer role)
- Captain (captain role)
- Manager (manager role)
- Crew (crew role)

# Export to .env:
export HOD_JWT="..."
export CAPTAIN_JWT="..."
export CREW_JWT="..."
```

### Phase 2: Handler End-to-End Tests

```python
# Test with HOD JWT
test_receive_part_success()           # → 200
test_receive_part_duplicate_409()     # → 409 (idempotency)
test_consume_part_success()           # → 200
test_consume_insufficient_409()       # → 409 (conflict)
test_transfer_part_success()          # → 200
test_adjust_stock_no_sig_400()        # → 400 (signed action)
test_adjust_stock_with_sig_200()      # → 200
test_write_off_no_sig_400()           # → 400 (signed action)
test_write_off_with_sig_200()         # → 200
```

### Phase 3: Role-Based Suggestions

```python
# Test with each role
crew_suggestions = get_suggestions(CREW_JWT)
assert no_mutate_or_signed_actions(crew_suggestions)  # Crew sees only READ

hod_suggestions = get_suggestions(HOD_JWT)
assert has_mutate_actions(hod_suggestions)  # HOD sees MUTATE

captain_suggestions = get_suggestions(CAPTAIN_JWT)
assert has_signed_actions(captain_suggestions)  # Captain sees SIGNED
```

### Phase 4: Storage RLS Negatives

```python
# Attempt cross-yacht access
write_to_wrong_yacht_path()    # → 403
read_from_wrong_yacht_path()   # → 403

# Test manager-only delete
delete_label_as_hod()          # → 403
delete_label_as_manager()      # → 200

# Test all 3 buckets
test_pms_part_photos_rls()
test_pms_receiving_images_rls()
test_pms_label_pdfs_rls()
```

### Phase 5: Stress Test

```bash
# Run with HOD JWT
CONCURRENCY=10 REQUESTS=50 python3 tests/stress/stress_action_list.py

# Verify:
- Success rate > 99%
- P95 < 500ms
- Zero 5xx
```

### Phase 6: Apply View Fix

```sql
-- Apply migration
\i supabase/migrations/202601271530_fix_low_stock_report_filter.sql

-- Verify
SELECT COUNT(*) FROM v_low_stock_report WHERE min_level = 0;
-- Expected: 0
```

---

## 🎯 Artifacts Still Needed

| Artifact | Status | Required |
|----------|--------|----------|
| Valid JWTs (HOD, Captain, Crew) | ❌ Missing | YES |
| Handler execution logs | ❌ Missing | YES |
| Role-based suggestions JSON | ❌ Missing | YES |
| Idempotency 409 evidence | ❌ Missing | YES |
| Storage RLS 403 evidence | ❌ Missing | YES |
| Stress test results (P50/P95/P99) | ❌ Missing | YES |
| Zero 5xx proof (all paths) | ⚠️ Partial | YES |
| View fix applied + verified | ❌ Missing | YES |
| SQL viewdefs | ✓ Have | NO (already collected) |
| RLS policy listings | ✓ Have | NO (already collected) |
| Audit samples | ✓ Have | NO (already collected) |

---

## 🔴 Updated Recommendation

**Status**: 🔴 **NOT READY FOR CANARY**

**Blockers**:
1. No JWT testing (cannot verify handlers, RLS, or role-based features)
2. Suggestions view filter bug (min_level=0 parts included)
3. Narrow 5xx testing (only tested 404 paths)
4. No storage RLS negatives
5. No stress testing

**Required Actions**:
1. ✅ **URGENT**: Acquire valid staging JWTs for HOD, Captain, Crew
2. ✅ **URGENT**: Apply view fix migration
3. ✅ **URGENT**: Run handler end-to-end tests with JWT
4. ✅ **URGENT**: Run stress test with JWT
5. ✅ Run storage RLS negatives
6. ✅ Collect comprehensive 5xx evidence (all paths)

**Timeline**: Cannot proceed to canary until ALL urgent items complete

---

## 💡 What Went Right

Despite the blockers, significant progress was made:

✅ Canonical view proven to work (SQL evidence)
✅ Transaction sum parity verified
✅ RLS structure verified
✅ Audit invariants confirmed
✅ Cache drift explained (not a blocker)
✅ Local tests comprehensive (53/54 passed)
✅ View filter bug identified and fix created

The **foundation is solid**. We just need **JWT access** to complete validation.

---

## 📞 Next Steps

1. **Obtain JWTs**: Use correct auth flow or provide valid tokens
2. **Run JWT test suite**: Complete all handler, RLS, and stress tests
3. **Apply view fix**: Migrate to remove min_level=0 parts
4. **Collect artifacts**: Handler logs, stress results, RLS 403s
5. **Re-evaluate**: After ALL gaps closed, reassess canary readiness

**Do NOT proceed to canary without completing JWT tests.**

---

**Report Date**: 2026-01-27
**Status**: HOLD (Critical gaps)
**Confidence**: Cannot assess without JWT testing
**Verdict**: NOT READY
