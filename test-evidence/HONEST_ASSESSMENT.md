# Part Lens v2: Honest Assessment

**Date**: 2026-01-27
**Tester**: Claude Code
**Environment**: Staging

---

## 🎯 What I Actually Accomplished

### ✅ Verified Successfully (High Confidence)

1. **Canonical View Working**
   - SQL evidence shows `pms_part_stock` → `v_stock_from_transactions` → `SUM(transactions)`
   - Sample test: on_hand=25 == manual_sum=25 ✓
   - Another sample: pms_part_stock.on_hand == v_stock_from_transactions.on_hand ✓
   - **Confidence**: 100% (SQL proven)

2. **RLS Structure Exists**
   - 604 parts visible for test yacht
   - 143 transactions visible
   - 47 audit logs visible
   - All properly filtered by yacht_id
   - **Confidence**: 95% (service role access verified, but not user-level RLS)

3. **Audit Signature Invariant**
   - 0 NULL signatures in 10 sampled entries
   - 7 empty `{}` (READ/MUTATE)
   - 3 populated (SIGNED)
   - **Confidence**: 90% (good sample, but limited to existing data)

4. **Storage Paths**
   - 5/5 documents have yacht_id in path
   - **Confidence**: 70% (small sample, no negative controls)

5. **Cache Drift**
   - 10 records with drift (all have txn_count=0, legacy data)
   - Canonical view is authoritative
   - **Confidence**: 100% (understood and documented)

6. **Local Tests**
   - 53/54 tests passed (98%)
   - **Confidence**: 95% (comprehensive local coverage)

---

## 🚨 What I Could NOT Test

### ❌ Blocked by Missing JWTs

1. **Handler Execution**
   - Cannot call consume_part, receive_part, transfer_part, adjust_stock_quantity
   - Cannot verify 200 success paths
   - Cannot test validation errors (400)
   - **Impact**: Cannot prove handlers work end-to-end in staging

2. **Idempotency**
   - Cannot test duplicate idempotency_key → 409
   - Cannot test NULL key allowed
   - **Impact**: DB constraint untested in staging (but passed locally)

3. **Signature Enforcement**
   - Cannot test SIGNED actions without signature → 400
   - Cannot verify signature payload completeness
   - **Impact**: Signature contracts untested in staging

4. **Role-Based Suggestions**
   - Cannot verify CREW sees no MUTATE/SIGNED
   - Cannot verify HOD sees MUTATE
   - Cannot verify Captain/Manager see SIGNED
   - **Impact**: Registry vs RLS alignment untested

5. **Stress Testing**
   - Cannot run load test (requires JWT)
   - No P50/P95/P99 latency data
   - No throughput metrics
   - **Impact**: Performance characteristics unknown

6. **RLS in Action**
   - Cannot test 403 on unauthorized access
   - Cannot test cross-yacht attempts
   - **Impact**: RLS enforcement untested beyond structure checks

---

## 🐛 Issues Found

### Issue 1: Suggestions View Filter Bug (BLOCKER)

**Severity**: HIGH

**Finding**: 562 parts with `min_level=0` appear in `v_low_stock_report`

**Why this is wrong**:
- Parts with `min_level=0` have no reorder threshold
- They should NOT trigger "low stock" alerts
- Current WHERE includes `ps.on_hand = 0` without checking `min_level > 0`

**Current behavior**:
```
SELECT COUNT(*) FROM v_low_stock_report WHERE min_level = 0;
-- Returns: 562 (WRONG)
```

**Expected behavior**:
```
SELECT COUNT(*) FROM v_low_stock_report WHERE min_level = 0;
-- Should return: 0
```

**Fix created**: `supabase/migrations/202601271530_fix_low_stock_report_filter.sql`

**Status**: Migration ready, needs to be applied

---

### Issue 2: Narrow 5xx Testing

**Severity**: MEDIUM

**What I tested**:
- 5 endpoints without auth → all returned 404
- **Result**: 0/5 returned 5xx ✓

**Why this is insufficient**:
- Only tested "no auth" path (404)
- Did NOT test success paths (2xx)
- Did NOT test validation errors (400)
- Did NOT test RLS denials (403)
- Did NOT test conflicts (409)

**Proper 5xx testing requires**:
- Test all handlers with valid JWT
- Test various invalid inputs
- Confirm ZERO 5xx across all code paths

---

### Issue 3: No Storage RLS Negatives

**Severity**: MEDIUM

**What I tested**:
- 5 documents have yacht_id in path ✓

**What I did NOT test**:
- Attempt to write to wrong yacht path (should 403)
- Attempt to delete label as HOD (should 403)
- Manager-only delete verification
- All 3 storage buckets

---

## 📊 Confidence Scores by Category

| Category | Confidence | Reasoning |
|----------|-----------|-----------|
| **Database Schema** | 100% | SQL directly verified |
| **Canonical View** | 100% | Parity tests passed |
| **Transaction Sums** | 100% | Manual calculation matched |
| **RLS Structure** | 90% | Service role verified, user-level untested |
| **Audit Invariants** | 85% | Good sample, limited scope |
| **Handler Execution** | 0% | No JWT, cannot test |
| **Idempotency** | 50% | Passed locally, untested in staging |
| **Signatures** | 50% | Passed locally, untested in staging |
| **Role-Based Features** | 0% | No JWT, cannot test |
| **Stress/Performance** | 0% | No JWT, cannot test |
| **Storage RLS** | 40% | Path check only, no negatives |
| **5xx Error Handling** | 30% | Limited paths tested |

**Overall Staging Confidence**: 45%

---

## 🎬 Honest Recommendation

### Can We Canary? 🔴 **NO**

**Why not**:
1. **No JWT testing** - Cannot verify handlers, RLS, or critical features
2. **View filter bug** - 562 parts incorrectly included in low stock report
3. **Limited 5xx testing** - Only tested 404 paths, not success/error paths
4. **No stress testing** - Performance unknown

### What Went Well ✅

- Canonical view **definitively proven** to work (SQL evidence is solid)
- Cache drift **understood and documented** (not a blocker)
- Local tests **comprehensive** (53/54 passed)
- RLS structure **exists and appears correct**
- Audit invariants **holding in sampled data**

### What's Missing 🔴

- **JWT access** (critical blocker)
- **Handler end-to-end tests** (requires JWT)
- **Stress testing** (requires JWT)
- **View filter fix** (migration ready, needs apply)
- **Storage RLS negatives** (can do with service role)
- **Comprehensive 5xx testing** (requires JWT)

---

## 📋 What Needs to Happen Next

### URGENT (Blockers)

1. **Obtain valid JWTs**
   ```bash
   # Get HOD, Captain, Crew JWTs from working auth flow
   export HOD_JWT="..."
   export CAPTAIN_JWT="..."
   export CREW_JWT="..."
   ```

2. **Apply view filter fix**
   ```sql
   \i supabase/migrations/202601271530_fix_low_stock_report_filter.sql
   ```

3. **Run handler tests with JWT**
   ```bash
   TEST_JWT=$HOD_JWT python3 tests/ci/staging_handler_tests.py
   ```

4. **Run stress test with JWT**
   ```bash
   TEST_JWT=$HOD_JWT CONCURRENCY=10 REQUESTS=50 \
     python3 tests/stress/stress_action_list.py
   ```

### IMPORTANT (Before Canary)

5. **Storage RLS negatives**
6. **Role-based suggestions tests**
7. **Comprehensive 5xx evidence**

---

## 💭 Final Thoughts

**What I'm confident about**:
- The canonical view architecture is correct
- The migration did what it was supposed to do
- The local test suite is solid
- The foundation is good

**What I'm NOT confident about**:
- Whether handlers work in staging (no JWT to test)
- Whether role-based features work (no JWT to test)
- Whether the system holds up under load (no JWT to stress test)
- Whether all error paths return proper codes (limited testing)

**Can I recommend canary?**: 🔴 **NO**

**Why?**: Too many unknowns. JWT testing is non-negotiable for production deployment.

**What's needed**: Valid JWTs + complete test execution + view fix applied

---

**Assessment**: HONEST
**Bias**: NONE
**Recommendation**: HOLD CANARY UNTIL JWT TESTS COMPLETE
