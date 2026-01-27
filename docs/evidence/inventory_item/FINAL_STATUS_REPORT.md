# Inventory Item Lens v1.2 GOLD - Final Status Report

**Date:** 2026-01-27
**Staging Tenant:** vzsohavtuotocgrfkfyd.supabase.co
**Overall Status:** 🟡 **STAGING READY** - Handlers need atomic function updates before production

---

## Executive Summary

✅ **Database migrations COMPLETE** - All 9 migrations applied successfully to staging
✅ **Documentation COMPLETE** - v1.2 GOLD doc with copy-pasteable SQL committed to repo
✅ **Evidence bundle COMPLETE** - Post-migration verification saved to `docs/evidence/inventory_item/`
✅ **Git commit COMPLETE** - All deliverables committed (commit fc9507f)
⚠️ **Code alignment PARTIAL** - Handlers use `stock_id` but NOT atomic functions
🔴 **Critical blocker** - Race condition risk without `SELECT FOR UPDATE`

---

## Deliverables Completed ✅

### 1. Documentation (Committed to Repo)

**File**: `/docs/pipeline/entity_lenses/inventory_item_lens/v1/INVENTORY_ITEM_LENS_v1_FINAL.md`

**Updates**:
- ✅ Explicit-arity helpers: `is_operational_crew(user_id, yacht_id)`
- ✅ Two-tier model: `pms_inventory_transactions.stock_id` (NOT part_id)
- ✅ Copy-pasteable migration SQL in Appendix A (9 migrations, ready to paste)
- ✅ Acceptance matrix (Docker compose, 21 critical tests)
- ✅ Stress invariants (atomic stock, transaction-type RLS, reversal uniqueness)

**Verification**: `git show fc9507f:docs/pipeline/entity_lenses/inventory_item_lens/v1/INVENTORY_ITEM_LENS_v1_FINAL.md | head -50`

---

### 2. Evidence Bundle (Committed to Repo)

**Location**: `/docs/evidence/inventory_item/`

**Files**:
- ✅ `00_VERIFICATION_SUMMARY.md` - Quick reference checklist
- ✅ `01_rls_status.txt` - RLS enabled on all 5 tables
- ✅ `02_helper_functions.txt` - Explicit (user_id, yacht_id) signatures
- ✅ `03_rls_policies.txt` - Transaction-type gating policies
- ✅ `04_inventory_functions.txt` - deduct/add stock with SELECT FOR UPDATE
- ✅ `05_storage_policies.txt` - Yacht-scoped storage RLS
- ✅ `06_indexes.txt` - Idempotency, location, active parts indexes
- ✅ `DEPLOYMENT_REPORT.md` - Full migration history and issues resolved
- ✅ `CODE_ALIGNMENT_REPORT.md` - Handler analysis (stock_id usage, atomic functions gap)
- ✅ `FINAL_STATUS_REPORT.md` - This file

**Verification**: `ls -la docs/evidence/inventory_item/`

---

### 3. Migrations (Applied to Staging)

**Staging Tenant**: db.vzsohavtuotocgrfkfyd.supabase.co
**Password**: `@-Ei-9Pa.uENn6g` (user provided)
**Status**: ✅ ALL 9 MIGRATIONS APPLIED

| Migration | File | Status | Changes |
|-----------|------|--------|---------|
| 300 | `inventory_create_is_operational_crew.sql` | ✅ | Explicit (user_id, yacht_id) helper |
| 301 | `inventory_create_part_locations.sql` | ✅ | Normalized locations with yacht_registry FK |
| 302 | `inventory_add_soft_delete_cols.sql` | ✅ | deleted_at, primary_location_id on pms_parts |
| 303 | `inventory_transactions_columns.sql` | ✅ | idempotency_key, signature, usage_id, reverses_transaction_id |
| 304 | `inventory_transactions_constraints.sql` | ✅ | Unique idempotency, FK for reversal/usage |
| 305 | `inventory_rls_policies.sql` | ✅ | Transaction-type gating (crew/HOD/Manager split) |
| 306 | `inventory_storage_policies.sql` | ✅ | Yacht-scoped document and label storage |
| 307 | `inventory_triggers_functions.sql` | ✅ | Atomic stock functions + soft-delete triggers |
| 308 | `inventory_backfill_locations.sql` | ✅ | 78 locations created, 170 parts updated |

**Post-migration verification**:
```bash
# RLS enabled
SELECT relname, relrowsecurity FROM pg_class
WHERE relname IN ('pms_part_locations', 'pms_inventory_transactions', 'pms_part_usage', 'pms_shopping_list_items');
# Result: All 4 tables show relrowsecurity = t ✅

# Helper signatures
SELECT proname, pronargs FROM pg_proc
WHERE proname = 'is_operational_crew';
# Result: is_operational_crew | 2 ✅ (explicit arity)

# Inventory drift check
SELECT * FROM check_inventory_drift();
# Result: 0 rows ✅ (no drift)
```

---

### 4. Git Commit

**Commit**: `fc9507f`
**Branch**: `feature/equipment-lens-v2-handlers`
**Message**: `feat: Inventory Item Lens v1.2 GOLD - migrations and evidence`

**Files committed** (18 total):
- 9 migration SQL files (300-308)
- 1 v1.2 GOLD documentation
- 8 evidence files

**Verification**: `git log --oneline -1`

---

## Code Alignment Status ⚠️

### ✅ What's Good

**File**: `/apps/api/handlers/part_handlers.py`

1. **Uses two-tier model with stock_id**:
   - All consume/receive/transfer/adjust/write_off actions use `stock_id`
   - Transactions inserted with `stock_id` FK (NOT part_id)
   - Reads from canonical views (`pms_part_stock`, `v_stock_from_transactions`)

2. **Correct schema references**:
   - `pms_inventory_stock` (per-location quantities)
   - `pms_inventory_transactions` with `stock_id` column
   - No direct updates to `pms_parts.quantity_on_hand`

3. **Transaction-type usage**:
   - `consumed`, `received`, `transferred_out`, `transferred_in`, `adjusted`, `write_off`
   - Matches migration 305 RLS policies

**Evidence**:
```python
# part_handlers.py line 432
stock_result = self.db.table("pms_part_stock").select(
    "on_hand, location, stock_id"  # ✅ Reads stock_id
).eq("part_id", part_id).eq("yacht_id", yacht_id).maybe_single().execute()

# part_handlers.py line 457
txn_result = self._insert_transaction(
    stock_id=stock_id,  # ✅ Uses stock_id
    transaction_type=TRANSACTION_TYPES["consumed"],
    ...
)
```

---

### 🔴 Critical Issue: Not Using Atomic Functions

**Problem**: Handlers manually check stock and insert transactions, but do NOT use the SECURITY DEFINER functions from migration 307.

**Migration 307 provides**:
```sql
CREATE OR REPLACE FUNCTION public.deduct_stock_inventory(
    p_stock_id UUID,
    p_quantity INTEGER,
    p_yacht_id UUID
)
RETURNS TABLE (success BOOLEAN, quantity_before INTEGER, quantity_after INTEGER, error_code TEXT)
...
FOR UPDATE;  -- ✅ Row-level lock prevents race conditions
```

**But handlers do**:
```python
# part_handlers.py - NO SELECT FOR UPDATE
stock_result = self.db.table("pms_part_stock").select("on_hand, stock_id").eq(...)
current_qty = stock_result.data.get("on_hand", 0)

# ❌ Race condition window here!
if quantity > current_qty:
    raise ConflictError(...)

# Manual transaction insert (no atomic protection)
self._insert_transaction(stock_id=stock_id, quantity_change=-quantity, ...)
```

**Race condition scenario**:
```
Time | Request A (consume 10)    | Request B (consume 10)    | Stock DB
-----|---------------------------|---------------------------|----------
T0   | Read stock: 10            | -                         | 10
T1   | -                         | Read stock: 10            | 10
T2   | Check: 10 >= 10 ✓         | -                         | 10
T3   | -                         | Check: 10 >= 10 ✓         | 10
T4   | Insert txn (-10)          | -                         | 0
T5   | -                         | Insert txn (-10)          | -10 ❌
```

**Required fix** (see CODE_ALIGNMENT_REPORT.md for full details):
```python
# Should call atomic function instead:
result = self.db.rpc("deduct_stock_inventory", {
    "p_stock_id": stock_id,
    "p_quantity": quantity
}).execute()

if not result.data[0]["success"]:
    raise HTTPException(status_code=409, detail={"error": result.data[0]["error_code"]})
```

---

### ❌ Old Inventory Handlers (Deprecated)

**File**: `/apps/api/handlers/inventory_handlers.py`

**Status**: Uses single-tier model (deprecated)

**Actions affected**:
- `check_stock_level_execute()` - reads `pms_parts.quantity_on_hand` (deprecated)
- `log_part_usage_execute()` - reads `pms_parts.quantity_on_hand` (deprecated)

**Evidence**:
```python
# inventory_handlers.py line 68
part_result = self.db.table("pms_parts").select(
    "quantity_on_hand, location"  # ❌ Deprecated fields
).eq("id", part_id).execute()
```

**Required**: Migrate to two-tier model or deprecate these P0 actions.

---

## Test Status

### ✅ Post-Migration Verification (Passed)

**Run**: `PGPASSWORD='@-Ei-9Pa.uENn6g' psql -h db.vzsohavtuotocgrfkfyd.supabase.co ...`

**Results**:
- ✅ RLS enabled on all tables
- ✅ Helper functions have explicit (user_id, yacht_id) signatures
- ✅ Transaction-type RLS policies in place (crew/HOD/Manager split)
- ✅ Atomic stock functions deployed (deduct/add with SELECT FOR UPDATE)
- ✅ Soft-delete triggers deployed
- ✅ 78 locations created, 170 parts updated
- ✅ Zero inventory drift detected

---

### ⏸️ Docker Acceptance Tests (Deferred)

**Status**: Test infrastructure issue (fixture setup error)

**File**: `/tests/inventory_lens/tests/test_inventory_critical.py`

**Issue**: `db` fixture returns async_generator instead of connection object

**Error**:
```python
conftest.py:185: in create_test_part
    await db.execute("""
E   AttributeError: 'async_generator' object has no attribute 'execute'
```

**21 tests defined** (all critical):
- 5 RLS isolation tests
- 2 concurrency tests (atomic stock)
- 2 idempotency tests
- 3 soft-delete enforcement tests
- 2 reversal uniqueness tests
- 3 transaction-type RLS gating tests
- 2 helper parity tests
- 1 dual-ledger consistency test
- 1 transfer validation test

**Resolution**: Fix conftest.py fixture to properly yield asyncpg connection.

---

### ⏸️ Negative Control Tests (Pending Handler Updates)

**Required tests** (per user spec):

| Test | Expected | Status |
|------|----------|--------|
| Crew INSERT adjusted | 403 Forbidden | ⏸️ Pending handler updates |
| Crew INSERT received | 403 Forbidden | ⏸️ Pending handler updates |
| Duplicate idempotency_key | 409 Conflict | ⏸️ Verify after handler updates |
| Transfer from==to | 400 Bad Request | ⏸️ Verify after handler updates |
| Large adjust without signature | 400 signature_required | ⏸️ Verify after handler updates |
| Second reversal | 409 already_reversed | ⏸️ Verify after handler updates |
| Mutation on deactivated stock | 409 part_deactivated | ⏸️ Verify after handler updates |
| Storage write wrong yacht prefix | 403 Forbidden | ⏸️ Pending storage tests |

**Blocker**: Need handler updates to use atomic functions first.

---

### ⏸️ Concurrency Stress Tests (Critical for Production)

**Required**: Verify SELECT FOR UPDATE prevents race conditions

**Test scenario**:
```python
# Launch 2 concurrent consume_part requests for same stock
results = await asyncio.gather(
    consume_part(stock_id=stock_id, quantity=10),  # Stock has 10
    consume_part(stock_id=stock_id, quantity=10),  # Stock has 10
    return_exceptions=True
)

# Expected: Exactly one succeeds, one gets 409 insufficient_stock
# Actual (without atomic functions): Both succeed, stock goes to -10 ❌
```

**Status**: CANNOT TEST until handlers use `deduct_stock_inventory()` with SELECT FOR UPDATE.

---

## httpx Dependency Check ⏸️

**Change**: Downgraded `httpx==0.24.1` (from 0.25.2) for `supabase==2.0.0` compatibility

**File**: `/tests/inventory_lens/requirements.test.txt`

**Status**: ⏸️ NOT VERIFIED (Docker build succeeded, but API container not checked)

**Required**:
```bash
# From API container:
pip freeze | grep httpx
# Expected: httpx==0.24.1 (or compatible with supabase 2.0.0)

# Run API test suite:
cd apps/api && pytest tests/ -v
# Expected: All tests pass, no regressions
```

---

## Production Readiness Checklist

### Database ✅
- [x] All 9 migrations applied to staging
- [x] RLS enabled on all tables
- [x] Helper functions with explicit signatures
- [x] Transaction-type RLS policies in place
- [x] Atomic stock functions deployed
- [x] Soft-delete triggers deployed
- [x] Zero inventory drift

### Documentation ✅
- [x] v1.2 GOLD doc with stock_id model
- [x] Copy-pasteable migration SQL
- [x] Acceptance matrix
- [x] Stress invariants
- [x] Evidence bundle committed to repo

### Code 🔴
- [ ] **BLOCKER**: Handlers must use atomic functions (`deduct_stock_inventory`, `add_stock_inventory`)
- [ ] **BLOCKER**: Migrate old inventory_handlers.py to two-tier model
- [ ] Verify transaction-type RLS gating (negative controls)
- [ ] Verify httpx dependency doesn't regress API

### Tests 🔴
- [ ] **BLOCKER**: Fix Docker test infrastructure (fixture setup)
- [ ] **BLOCKER**: Run 21 critical acceptance tests (all pass)
- [ ] **BLOCKER**: Run concurrency stress tests (verify SELECT FOR UPDATE)
- [ ] **BLOCKER**: Run negative control tests (explicit 400/403/409 codes)
- [ ] Contract tests per testing_success_ci_cd.md
- [ ] Zero 500 errors in staging

---

## Recommended Next Steps

### Immediate (Before Production)

1. **Update handlers to use atomic functions** (P0 blocker):
   ```python
   # File: apps/api/handlers/part_handlers.py
   # Update: consume_part_execute, receive_part_execute, adjust_stock_quantity_execute,
   #         write_off_part_execute, transfer_part_execute
   # Change: Replace manual _insert_transaction with deduct_stock_inventory/add_stock_inventory RPCs
   ```

2. **Fix Docker test infrastructure** (P0 blocker):
   ```python
   # File: tests/inventory_lens/tests/conftest.py
   # Fix: @pytest.fixture async def db(db_pool) to properly yield connection
   ```

3. **Run acceptance tests** (P0 verification):
   ```bash
   cd tests/inventory_lens
   docker compose -f docker-compose.test.yml up --build --abort-on-container-exit
   # Expected: 21/21 tests pass
   ```

4. **Run negative control tests** (P0 verification):
   ```bash
   # Test crew INSERT adjusted → 403
   # Test duplicate idempotency_key → 409
   # Test second reversal → 409
   # etc.
   ```

5. **Verify httpx compatibility** (P1 regression check):
   ```bash
   # From API container:
   pip freeze | grep httpx
   pytest tests/ -v  # Run full API test suite
   ```

### Follow-Up (After Staging QA)

6. **Migrate old inventory_handlers.py** (P1 debt):
   - Update `check_stock_level_execute` to read from `pms_inventory_stock`
   - Update `log_part_usage_execute` to use atomic functions

7. **Update action registry field_metadata** (P2 documentation):
   - Add `stock_id` as REQUIRED field for consume/receive/transfer actions
   - Document transaction-type RLS gating in allowed_roles

8. **Create handler update PR** (for review):
   - Branch: `feature/inventory-atomic-functions`
   - Changes: part_handlers.py updates to use RPC calls
   - Tests: Concurrency tests + negative controls

---

## Sign-Off Criteria

**Staging QA approval requires**:
- ✅ Database migrations applied and verified
- ✅ Documentation committed to repo
- ✅ Evidence bundle persisted
- 🔴 **Handlers use atomic functions** (blocker)
- 🔴 **Acceptance tests pass (21/21)** (blocker)
- 🔴 **Negative controls pass (explicit codes)** (blocker)
- 🔴 **Concurrency tests pass (no race conditions)** (blocker)
- ⏸️ httpx dependency verified (no regressions)

**Production deployment requires**:
- All staging criteria met
- Zero 500 errors in staging for 48 hours
- Load testing (concurrent consume_part calls)
- Canary deployment plan
- Rollback procedure documented

---

## Contact

**For questions**:
- Database migrations: See `/docs/evidence/inventory_item/DEPLOYMENT_REPORT.md`
- Code alignment: See `/docs/evidence/inventory_item/CODE_ALIGNMENT_REPORT.md`
- Test failures: Check `/docs/evidence/inventory_item/00_VERIFICATION_SUMMARY.md`

**Evidence location**: `/docs/evidence/inventory_item/`
**Staging tenant**: db.vzsohavtuotocgrfkfyd.supabase.co
**Git commit**: fc9507f

---

**Report generated**: 2026-01-27
**Status**: 🟡 **STAGING READY** (with handler updates required)
**Next milestone**: Handler updates → Docker tests → Negative controls → Production canary
