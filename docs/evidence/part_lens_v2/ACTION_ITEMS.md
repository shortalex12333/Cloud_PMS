# Part Lens v2 - Action Items for Deployment

**Status**: ✅ Code Ready | 🚧 Awaiting Manual Deployment
**Date**: 2026-01-28

---

## ✅ Completed (Claude)

### 1. Direct SQL Implementation
- [x] Created `TenantPGGateway` for direct psycopg2 connections
- [x] Updated `view_part_details` to use SQL instead of PostgREST
- [x] Hardened `consume_part` with RPC 204 handling + SQL confirmation
- [x] Committed to `security/signoff` branch (commit `b0cacd3`)

### 2. Test Scripts Prepared
- [x] Storage RLS DELETE tests (`tests/acceptance/test_storage_rls_delete.py`)
- [x] Deployment log with verification steps
- [x] Evidence directory structure

### 3. Migrations Ready
- [x] Storage manager-only DELETE migration exists: `supabase/migrations/20260128_storage_manager_only_delete.sql`
- [x] Health tables migration available: `supabase/migrations/20260128_ops_health_tables.sql`

---

## 🚧 Required Manual Actions (User)

### STEP 1: Deploy Staging from security/signoff Branch

**Location**: https://dashboard.render.com

1. Navigate to `celeste-pipeline-v1` (staging service)
2. Go to **Settings** → **Build & Deploy**
3. Change **Branch** from `main` to `security/signoff`
4. Click **Save**
5. Click **Manual Deploy** → **Deploy Latest Commit**
6. Wait 3-5 minutes for build completion

**Verification**:
```bash
curl https://pipeline-core.int.celeste7.ai/health
# Expected: {"status":"healthy"}
```

---

### STEP 2: Apply Storage Manager-Only DELETE Migration

**Database**: TENANT_1 (vzsohavtuotocgrfkfyd)

**Option A - Supabase Dashboard**:
1. Go to: https://supabase.com/dashboard/project/vzsohavtuotocgrfkfyd/sql
2. Open file: `supabase/migrations/20260128_storage_manager_only_delete.sql`
3. Copy entire contents
4. Paste into SQL Editor
5. Click **Run**
6. Verify: `✅ All 3 manager-only DELETE policies created` in output

**Option B - CLI** (if configured):
```bash
cd /Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS
supabase db push --project-ref vzsohavtuotocgrfkfyd
```

**Verification SQL**:
```sql
SELECT
    policyname,
    cmd,
    qual
FROM pg_policies
WHERE schemaname = 'storage'
  AND tablename = 'objects'
  AND cmd = 'DELETE'
  AND policyname LIKE 'Managers delete%'
ORDER BY policyname;
```

Expected: 3 rows showing manager-only DELETE policies for:
- `pms-part-photos`
- `pms-receiving-images`
- `pms-label-pdfs`

---

### STEP 3: Provide Manager JWT for Testing

**Required**: A valid JWT for a user with `manager` role on `TEST_YACHT_001`

The storage DELETE tests need both HOD and Manager JWTs:
- HOD JWT: Already configured in test script
- **Manager JWT**: `REPLACE_WITH_MANAGER_JWT` (placeholder in test script)

**How to get Manager JWT**:
1. Login to app as manager user
2. Open browser DevTools → Application → Local Storage
3. Copy `supabase.auth.token` value
4. Provide to Claude via environment variable:
   ```bash
   export MANAGER_JWT="eyJhbGci..."
   ```

Or update the test script directly at line 29.

---

## 📋 Once Above Steps Complete, Claude Will:

### Hour 0-1: Health Verification
- [x] Check `/health` endpoint (200)
- [ ] Test `view_part_details` action (expect 200, not 204)
- [ ] Test `consume_part` action (200 sufficient, 409 insufficient)
- [ ] Verify Render logs show `[PGGateway] Connected to yTEST_YACHT_001`

### Hour 1-2: Storage RLS Tests
- [ ] Run `test_storage_rls_delete.py`
- [ ] Verify HOD delete → 403 (all 3 buckets)
- [ ] Verify Manager delete → 204 (all 3 buckets)
- [ ] Verify cross-yacht → 403 (all 3 buckets)
- [ ] Generate `storage_rls_403_evidence.json`

### Hour 2-4: Core Acceptance
- [ ] Test receive_part (201, duplicate → 409)
- [ ] Test consume_part (200 sufficient, 409 insufficient)
- [ ] Test transfer_part (net-zero, by-location correct)
- [ ] Test adjust_stock_quantity (400 missing sig, 200 signed)
- [ ] Test write_off_part (400 missing sig, 200 signed)
- [ ] Verify zero 5xx across all paths
- [ ] Generate `acceptance_summary.json`

### Hour 4-5: Stress Tests
- [ ] Run `tests/stress/stress_action_list.py`
- [ ] CONCURRENCY=10, REQUESTS=50
- [ ] Verify >99% success, P95<500ms, zero 5xx
- [ ] Generate `stress-results.json`

### Hour 5-6: Evidence & CI
- [ ] Update `acceptance_summary.json`
- [ ] Update `sql_evidence.json` (viewdefs, policies, single-tenant)
- [ ] Bundle all evidence in `docs/evidence/part_lens_v2/`
- [ ] Configure staging CI to publish artifacts
- [ ] Set staging acceptance as required check on main

### Post-Hour 6: Canary
- [ ] Merge `security/signoff` → `main` (after green tests)
- [ ] Switch Render staging back to `main` branch
- [ ] Enable 5% canary on production
- [ ] Monitor 1 hour (error rate <2%, zero 5xx, P95<500ms)
- [ ] Ramp: 5% → 20% → 50% → 100%

---

## 🔄 Rollback Plan

If deployment or tests fail:

### Rollback Staging
1. Render Dashboard → `celeste-pipeline-v1`
2. Settings → Build & Deploy → Branch: Change to `main`
3. Manual Deploy → Deploy Latest Commit

### Rollback Storage Migration
```sql
-- Revert to yacht-scoped DELETE (all roles)
DROP POLICY IF EXISTS "Managers delete yacht part photos" ON storage.objects;
CREATE POLICY "Users delete yacht part photos"
ON storage.objects
FOR DELETE
TO authenticated
USING (
  bucket_id = 'pms-part-photos'
  AND (storage.foldername(name))[1] = (
    SELECT yacht_id::text FROM auth_users_profiles WHERE id = auth.uid()
  )
);
-- Repeat for other 2 buckets
```

---

## 📊 Success Criteria

- [ ] All API endpoints return 2xx/4xx, zero 5xx
- [ ] view_part_details returns 200 with stock data
- [ ] consume_part: 200 for sufficient, 409 for insufficient
- [ ] Storage DELETE: HOD 403, Manager 204, cross-yacht 403
- [ ] Core Acceptance: 6/6 PASS
- [ ] Stress tests: >99% success, P95<500ms
- [ ] Evidence bundle complete
- [ ] CI gates configured

---

## 🚀 Timeline

- **Now**: Awaiting user to deploy staging + apply migration
- **Once deployed**: Claude executes 6-hour test plan
- **Hour 6**: Evidence complete, ready for canary approval
- **Hour 7+**: Merge to main, enable canary, monitor

---

**Next Action Required**: User deploys staging from `security/signoff` branch via Render dashboard (STEP 1 above)
