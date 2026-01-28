# Part Lens v2 - Pre-Canary Deployment Checklist

**Date**: 2026-01-28
**Status**: 🔧 **REQUIRES DB MIGRATIONS**

---

## Critical: Database Migrations Not Applied

Testing reveals that TENANT database is missing Part Lens v2 schema. All Supabase queries return PostgREST 204 errors.

### Required Migrations (TENANT DB)

Apply these migrations to the TENANT Supabase instance (`qvzmkaamzaqxpzbewjxe`):

| Migration | Purpose | Status |
|-----------|---------|--------|
| `202601271212_pms_part_stock_canonical_from_transactions.sql` | Creates `pms_part_stock` view (canonical stock source) | ❌ NOT APPLIED |
| `202601271307_inventory_triggers_functions.sql` | Creates `deduct_stock_inventory` + `add_stock_inventory` RPCs | ❌ NOT APPLIED |
| `202601281100_part_lens_v2_storage_buckets.sql` | Creates storage buckets (pms-part-photos, pms-receiving-images, pms-label-pdfs) | ❌ NOT APPLIED |
| `202601281700_storage_manager_only_delete.sql` | Replaces DELETE policies with manager-only versions | ❌ NOT APPLIED |

### Application Steps

**Option 1: Supabase CLI** (requires DB password)

```bash
cd /Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS
supabase link --project-ref qvzmkaamzaqxpzbewjxe
supabase db push
```

**Option 2: Dashboard SQL Editor**

1. Go to: https://supabase.com/dashboard/project/qvzmkaamzaqxpzbewjxe/sql/new
2. Copy/paste each migration file in order
3. Execute each one
4. Verify no errors

**Option 3: psql Direct**

```bash
psql "postgresql://postgres:[PASSWORD]@aws-1-us-east-1.pooler.supabase.com:5432/postgres" \
  -f supabase/migrations/202601271212_pms_part_stock_canonical_from_transactions.sql

psql "postgresql://postgres:[PASSWORD]@aws-1-us-east-1.pooler.supabase.com:5432/postgres" \
  -f supabase/migrations/202601271307_inventory_triggers_functions.sql

psql "postgresql://postgres:[PASSWORD]@aws-1-us-east-1.pooler.supabase.com:5432/postgres" \
  -f supabase/migrations/202601281100_part_lens_v2_storage_buckets.sql

psql "postgresql://postgres:[PASSWORD]@aws-1-us-east-1.pooler.supabase.com:5432/postgres" \
  -f supabase/migrations/202601281700_storage_manager_only_delete.sql
```

### Verification Steps

After applying migrations:

```sql
-- Verify view exists
SELECT COUNT(*) FROM pms_part_stock;

-- Verify RPC exists
SELECT proname FROM pg_proc WHERE proname = 'deduct_stock_inventory';

-- Verify storage buckets exist
SELECT name FROM storage.buckets WHERE name LIKE 'pms-%';

-- Verify manager-only DELETE policies
SELECT policyname FROM pg_policies
WHERE schemaname = 'storage'
  AND tablename = 'objects'
  AND cmd = 'DELETE'
  AND policyname LIKE 'Managers delete%';
```

Expected results:
- pms_part_stock: Returns row count (may be 0 if no parts exist)
- deduct_stock_inventory: Returns 1 row
- storage.buckets: Returns 3 rows (pms-part-photos, pms-receiving-images, pms-label-pdfs)
- pg_policies: Returns 3 rows (one per bucket)

---

## Once Migrations Applied: Test Suite

### 1. consume_part Tests

```bash
cd /private/tmp/claude/-Volumes-Backup-CELESTE/6154729d-7aeb-45f6-a740-f9e2eea35f83/scratchpad
python3 test_consume_part.py
```

**Expected**:
- Sufficient stock → 200
- Insufficient stock → 409
- Zero 5xx errors

### 2. Storage DELETE Tests

```bash
cd /private/tmp/claude/-Volumes-Backup-CELESTE/6154729d-7aeb-45f6-a740-f9e2eea35f83/scratchpad
python3 upload_test_objects.py  # Upload test files
python3 test_storage_rls_delete.py  # Test DELETE policies
```

**Expected** (per bucket):
- HOD delete → 403
- Manager delete → 204
- Cross-yacht delete → 403

### 3. Core Acceptance Suite

```bash
cd tests/ci
python3 comprehensive_staging_acceptance.py
```

**Expected**:
- 6/6 PASS (including consume_part)
- Zero 5xx errors
- All role enforcement passing

### 4. Stress Tests

```bash
cd tests/stress
python3 stress_action_list.py --concurrency 10 --requests 50
```

**Expected**:
- >99% success rate
- P95 latency < 500ms
- Zero 5xx errors

---

## Signed Actions Status (Already Passing)

✅ **9/9 PASS** - No migration required

| Action | Tests | Status |
|--------|-------|--------|
| adjust_stock_quantity | 4/4 | ✅ PASS |
| write_off_part | 5/5 | ✅ PASS |

Evidence: `signed_actions_evidence_v3.json`

---

## Deployment Readiness Criteria

| Criterion | Status | Blocker |
|-----------|--------|---------|
| Core Acceptance 6/6 | ⚠️ BLOCKED | Migrations not applied |
| Zero 5xx | ⚠️ BLOCKED | Migrations not applied |
| Signed Actions 100% | ✅ PASS | None |
| Storage RLS Manager-Only | ⚠️ BLOCKED | Migrations not applied |
| Stress Tests | ⏸️ PENDING | Awaiting migrations |
| MASTER→TENANT Ready | ✅ PASS | None (fleet_registry exists) |

**Overall**: ⚠️ **NOT READY** - Apply migrations first

---

## Post-Migration: Expected Timeline

| Task | Duration | Owner |
|------|----------|-------|
| Apply 4 migrations | 10 min | DB Admin |
| Verify migrations | 5 min | DB Admin |
| Run consume_part tests | 2 min | Claude |
| Run storage DELETE tests | 5 min | Claude |
| Run Core Acceptance | 10 min | Claude |
| Run stress tests | 15 min | Claude |
| Generate evidence bundle | 5 min | Claude |
| Update deployment docs | 5 min | Claude |
| **TOTAL** | **~60 min** | - |

---

## Canary Gate Approval

Once migrations applied and all tests green:

✅ Enable 5% canary on `/v1/actions/execute` for Part Lens v2 actions:
- consume_part
- receive_part
- transfer_part
- adjust_stock_quantity
- write_off_part
- generate_part_labels
- request_label_output
- view_part_details (read-only, already live)

Monitor per `CANARY_DEPLOYMENT_PLAN.md`.

---

**Prepared By**: Claude Sonnet 4.5
**Last Updated**: 2026-01-28
**Next Action**: Apply migrations to TENANT DB (`qvzmkaamzaqxpzbewjxe`)
