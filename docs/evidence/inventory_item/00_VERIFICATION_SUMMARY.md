# Inventory Item Lens v1.2 GOLD - Post-Migration Verification Summary

**Date:** 2026-01-27
**Staging Tenant:** vzsohavtuotocgrfkfyd.supabase.co
**Verification Status:** ✅ ALL CHECKS PASSED

---

## Quick Reference

| Check | Status | Evidence File |
|-------|--------|---------------|
| RLS Enabled | ✅ | `01_rls_status.txt` |
| Helper Signatures | ✅ | `02_helper_functions.txt` |
| RLS Policies | ✅ | `03_rls_policies.txt` |
| Inventory Functions | ✅ | `04_inventory_functions.txt` |
| Storage Policies | ✅ | `05_storage_policies.txt` |
| Indexes | ✅ | `06_indexes.txt` |
| Full Deployment Report | ✅ | `DEPLOYMENT_REPORT.md` |

---

## Critical Invariants Verified

### ✅ Two-Tier Model Enforced
- `pms_inventory_transactions` references **stock_id** (not part_id)
- `stock_id` FK points to `pms_inventory_stock.id`
- All atomic functions use `stock_id` parameter

### ✅ Explicit-Arity Helpers
- `is_operational_crew(p_user_id UUID, p_yacht_id UUID)` - **2 args**
- `is_hod(p_user_id UUID, p_yacht_id UUID)` - **2 args**
- `is_manager(p_user_id UUID, p_yacht_id UUID)` - **2 args**
- **No zero-arg versions exist** - eliminates PostgreSQL ambiguity

### ✅ Transaction-Type RLS Gating
- **Crew:** `consumed` only (`crew_insert_consume` policy)
- **HOD:** `received`, `transferred_out`, `transferred_in`, `adjusted` (`hod_insert_receive_transfer_adjust` policy)
- **Manager/Captain:** `write_off`, `reversed` (`manager_insert_writeoff_reversed` policy)

### ✅ Append-Only Ledger
- **NO UPDATE policies** on `pms_inventory_transactions`
- **NO DELETE policies** on `pms_inventory_transactions`
- **NO UPDATE policies** on `pms_part_usage`
- **NO DELETE policies** on `pms_part_usage`

### ✅ Soft-Delete Enforcement
- Triggers block mutations on deactivated stock:
  - `trg_block_deactivated_stock_update` (BEFORE UPDATE on pms_inventory_stock)
  - `trg_block_deactivated_stock_transactions` (BEFORE INSERT on pms_inventory_transactions)
  - `trg_block_deactivated_stock_usage` (BEFORE INSERT on pms_part_usage)

### ✅ Reversal Uniqueness
- Trigger `trg_block_reversal_of_reversal` prevents reversing a reversal
- Function `block_reversal_of_reversal()` enforces single reversal per transaction

### ✅ Atomic Stock Operations
- `deduct_stock_inventory(stock_id, quantity, yacht_id)` with SELECT FOR UPDATE
- `add_stock_inventory(stock_id, quantity, yacht_id)` with SELECT FOR UPDATE
- Both return (success, quantity_before, quantity_after, error_code)

### ✅ Location Normalization
- `pms_part_locations` table with `yacht_registry` FK
- 78 locations created from backfill
- 170 parts updated with `primary_location_id`
- UNIQUE constraint on `(yacht_id, name)`

---

## Verification SQL (Run on Production)

```sql
-- 1. RLS Status
SELECT relname, relrowsecurity
FROM pg_class
WHERE relname IN ('pms_part_locations', 'pms_inventory_transactions', 'pms_part_usage', 'pms_shopping_list_items');

-- 2. Helper Signatures
SELECT proname, pronargs, pg_get_function_identity_arguments(oid)
FROM pg_proc
WHERE proname IN ('is_operational_crew', 'is_hod', 'is_manager')
  AND pronamespace = 'public'::regnamespace;

-- 3. Transaction-Type Policies
SELECT policyname, cmd
FROM pg_policies
WHERE tablename = 'pms_inventory_transactions'
  AND policyname LIKE '%insert%'
ORDER BY policyname;

-- 4. Append-Only Ledger
SELECT COUNT(*) as update_policies
FROM pg_policies
WHERE tablename IN ('pms_inventory_transactions', 'pms_part_usage')
  AND cmd = 'UPDATE';
-- Should return: 0

SELECT COUNT(*) as delete_policies
FROM pg_policies
WHERE tablename IN ('pms_inventory_transactions', 'pms_part_usage')
  AND cmd = 'DELETE';
-- Should return: 0

-- 5. Inventory Drift Check
SELECT * FROM check_inventory_drift();
-- Should return: 0 rows (no drift)

-- 6. Backfill Results
SELECT COUNT(*) as locations FROM pms_part_locations;
-- Should return: 78

SELECT COUNT(*) as parts_with_location
FROM pms_parts
WHERE primary_location_id IS NOT NULL;
-- Should return: 170
```

---

## Evidence Files Manifest

### 01_rls_status.txt
RLS enabled status for all 5 target tables (pms_part_locations, pms_inventory_transactions, pms_part_usage, pms_shopping_list_items, pms_inventory_stock).

### 02_helper_functions.txt
Function signatures showing explicit (user_id, yacht_id) arity for all RLS helpers.

### 03_rls_policies.txt
Complete list of RLS policies with transaction-type gating rules.

### 04_inventory_functions.txt
Source code and signatures for all 5 inventory functions (deduct_stock_inventory, add_stock_inventory, block_deactivated_stock_mutations, block_reversal_of_reversal, check_inventory_drift).

### 05_storage_policies.txt
Storage RLS policies for yacht-scoped document and label access.

### 06_indexes.txt
Index definitions for idempotency, location lookups, and active parts filtering.

### DEPLOYMENT_REPORT.md
Complete deployment report with migration history, issues resolved, verification results, and next steps.

---

## Sign-Off Criteria

- [x] All 8 migrations applied successfully
- [x] RLS enabled on all target tables
- [x] Helper functions have explicit (user_id, yacht_id) signatures
- [x] Transaction-type RLS gating policies in place
- [x] NO UPDATE/DELETE policies on append-only tables
- [x] Soft-delete triggers deployed
- [x] Atomic stock functions with SELECT FOR UPDATE
- [x] Location normalization complete (78 locations, 170 parts)
- [x] Zero inventory drift detected
- [x] Storage policies enforce yacht isolation

**Ready for staging QA approval.**

---

**Generated:** 2026-01-27
**Staging Tenant:** db.vzsohavtuotocgrfkfyd.supabase.co
**Lens Version:** Inventory Item Lens v1.2 GOLD
