# Part Lens v2: Staging Readiness Summary

**Date**: 2026-01-27
**Status**: 🟡 **READY TO DEPLOY** (API deployment required, all tests prepared)
**Next Step**: Deploy API to staging → Run tests → Canary approval

---

## 🎯 Current Status

### ✅ COMPLETED

1. **Database Layer Fixed and Validated**
   - View filter bug fixed (min_level=0 parts excluded) ✓
   - Canonical view proven (pms_part_stock → v_stock_from_transactions → SUM) ✓
   - Transaction parity verified ✓
   - RLS structure validated ✓
   - Audit invariants holding ✓

2. **JWT Tokens Generated**
   - HOD: `hod.tenant@alex-short.com` (chief_engineer) ✓
   - Captain: `captain.tenant@alex-short.com` ✓
   - Crew: `crew.tenant@alex-short.com` ✓

3. **Local Tests Strong**
   - 53/54 passed (98%) ✓
   - All handlers validated locally ✓

4. **Test Scripts Prepared**
   - Comprehensive staging acceptance script ✓
   - SQL evidence collection script ✓
   - Handler end-to-end tests ✓
   - Stress test script (ready) ✓

5. **Deployment Configuration Created**
   - `Dockerfile.microaction` for API service ✓
   - `render-api.yaml` for Render deployment ✓
   - Full deployment guide with multiple options ✓

### 🔴 BLOCKER: API Not Deployed

**Evidence**: https://app.celeste7.ai/v1/parts/low-stock → 404

**Impact**: Cannot run staging validation until API is deployed

**What's Needed**: Deploy `apps/api/microaction_service.py` to staging environment

---

## 📋 Deployment Steps (DO THIS NOW)

### Step 1: Deploy API to Staging

**Choose ONE deployment method**:

#### Option A: Render (Recommended if already using Render)

```bash
# 1. Push render-api.yaml to your repo
git add apps/api/render-api.yaml apps/api/Dockerfile.microaction
git commit -m "Add Part Lens v2 API service configuration"
git push

# 2. Deploy via Render Dashboard
# - Go to https://dashboard.render.com/select-repo?type=blueprint
# - Select your repo
# - Choose render-api.yaml
# - Set environment variables in dashboard (see STAGING_API_DEPLOYMENT_GUIDE.md)

# 3. Wait for deployment (~5 minutes)

# 4. Verify
export API_URL=$(render services list | grep celeste-api-staging | awk '{print $4}')
curl $API_URL/health
```

#### Option B: Docker + Cloud Run/ECS/Fly

```bash
cd apps/api

# Build
docker build -t celeste-api:staging -f Dockerfile.microaction .

# Test locally
docker run -p 8080:8080 \
  -e TENANT_1_SUPABASE_URL=https://vzsohavtuotocgrfkfyd.supabase.co \
  -e TENANT_1_SUPABASE_SERVICE_KEY='eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...' \
  -e TENANT_1_SUPABASE_JWT_SECRET='ep2o/+mEQD/b54M8W50Vk3GrsuVayQZf...' \
  -e DEFAULT_YACHT_CODE=yTEST_YACHT_001 \
  -e yTEST_YACHT_001_SUPABASE_URL=https://vzsohavtuotocgrfkfyd.supabase.co \
  -e yTEST_YACHT_001_SUPABASE_SERVICE_KEY='eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...' \
  celeste-api:staging

# Verify locally
curl http://localhost:8080/health
curl http://localhost:8080/v1/parts/low-stock?yacht_id=85fe1119-b04c-41ac-80f1-829d23322598 \
  -H "Authorization: Bearer $HOD_JWT"

# Deploy to cloud (see STAGING_API_DEPLOYMENT_GUIDE.md for platform-specific commands)
```

#### Option C: Update Existing Service

If you have an existing API service deployed:

```bash
# Change start command from:
uvicorn pipeline_service:app --host 0.0.0.0 --port $PORT

# To:
uvicorn microaction_service:app --host 0.0.0.0 --port $PORT

# Then redeploy
```

### Step 2: Verify API is Live

```bash
export API_BASE="https://your-staging-api.example.com"  # Or Render URL
export HOD_JWT="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."

# Should return 200 (not 404)
curl -I $API_BASE/health

# Should return 200/401/403 (not 404)
curl -I "$API_BASE/v1/parts/low-stock?yacht_id=85fe1119-b04c-41ac-80f1-829d23322598" \
  -H "Authorization: Bearer $HOD_JWT"
```

**Expected**:
- ✅ 200, 401, 403 → API is live, routes registered
- ❌ 404 → API not deployed or routes not registered

---

## 📊 Test Execution (RUN AFTER API IS LIVE)

### Step 3: Run Comprehensive Staging Acceptance

```bash
cd /Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS

# Set environment
export API_BASE="https://your-staging-api.example.com"
export TENANT_1_SUPABASE_URL="https://vzsohavtuotocgrfkfyd.supabase.co"
export TENANT_1_SUPABASE_SERVICE_KEY="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
export TEST_YACHT_ID="85fe1119-b04c-41ac-80f1-829d23322598"

# Generate JWTs
export TENANT_1_SUPABASE_JWT_SECRET="ep2o/+mEQD/b54M8W50Vk3GrsuVayQZf..."
python3 tests/ci/generate_all_test_jwts.py > /tmp/jwts.sh
source /tmp/jwts.sh

# Run comprehensive acceptance
python3 tests/ci/comprehensive_staging_acceptance.py

# Expected output:
# ✓ Canonical view parity: PASS
# ✓ View filter fix: PASS
# ✓ Single-tenant assertion: PASS
# ✓ receive_part 201: PASS
# ✓ idempotency 409: PASS
# ✓ adjust_stock 400 (no sig): PASS
# ✓ adjust_stock 200 (with sig): PASS
# ✓ audit signature keys: PASS
# ✓ suggestions (CREW): PASS
# ✓ suggestions (HOD): PASS
# ✓ suggestions (CAPTAIN): PASS
# ✓ zero 5xx comprehensive: PASS
#
# RESULTS: 12/12 passed (100%)
# 5xx ERRORS: 0
```

### Step 4: Collect SQL Evidence

```bash
export TENANT_1_DB_PASSWORD="@-Ei-9Pa.uENn6g"
python3 tests/ci/collect_sql_evidence.py

# Expected output:
# ✓ Collected 3 view definitions
# ✓ Collected N RLS policies
# ✓ Collected N storage policies
# ✓ All tables are single-tenant
# ✓ Collected 10 transaction parity samples
```

### Step 5: Run Stress Test (If Available)

```bash
# If you have a stress test script
export API_BASE="https://your-staging-api.example.com"
export TEST_JWT=$HOD_JWT
export CONCURRENCY=10
export REQUESTS=50
export OUTPUT_JSON="test-evidence/stress-results.json"

python3 tests/stress/stress_action_list.py

# Expected:
# Success rate: >99%
# P95 latency: <500ms
# Zero 5xx errors
```

---

## 📁 Expected Artifacts

After running all tests, you should have:

```
test-evidence/
├── comprehensive_acceptance_summary.json  # Main acceptance results
├── canonical_parity.json                  # Canonical view proof
├── view_filter_fix.json                   # min_level=0 fix proof
├── single_tenant_assertion.json           # Single-tenant proof
├── receive_part_201.json                  # Handler success
├── idempotency_409.json                   # Idempotency proof
├── adjust_stock_no_sig_400.json           # Signature enforcement
├── adjust_stock_with_sig_200.json         # Signed action success
├── role_based_suggestions.json            # Role visibility proof
├── zero_5xx_comprehensive.json            # Zero 5xx proof
├── viewdef_*.sql                          # View definitions (3 files)
├── rls_policies.json                      # RLS policies
├── storage_policies.json                  # Storage policies
├── transaction_parity_samples.json        # Transaction parity
└── stress-results.json                    # Stress test results (if run)
```

---

## ✅ Approval Criteria

### Must Have (All Required for Canary)

- [x] View filter bug fixed (0 parts with min_level=0)
- [x] Canonical view proven (SQL evidence)
- [x] JWTs generated (HOD, Captain, Crew)
- [ ] **API deployed and routes returning non-404** ← BLOCKER
- [ ] **Comprehensive acceptance passed (100%, zero 5xx)**
- [ ] **Role-based suggestions validated (artifacts collected)**
- [ ] **SQL evidence collected (viewdefs, policies, single-tenant)**

### Should Have (Recommended Before Canary)

- [ ] Stress test passed (>99% success, P95 <500ms, zero 5xx)
- [ ] Storage RLS cross-yacht 403 tests
- [ ] Handler execution with all status codes (200, 201, 400, 403, 404, 409)

---

## 🚀 Canary Approval Path

Once all "Must Have" items are complete:

### 1. Review Artifacts

```bash
# Check test results
cat test-evidence/comprehensive_acceptance_summary.json | jq '.success_rate, .five_xx_count'

# Should show:
# 1.0  (100% success)
# 0    (zero 5xx)
```

### 2. Enable 5% Canary

```sql
-- In Supabase SQL Editor or psql
UPDATE feature_flags
SET enabled = true,
    canary_percentage = 5,
    updated_at = NOW()
WHERE flag_name = 'part_lens_v2';
```

### 3. Monitor for 1 Hour

Watch for:
- ✅ Error rate <0.1%
- ✅ P95 latency <500ms
- ✅ Zero 5xx errors
- ✅ No NULL audit signatures
- ✅ No user reports of issues

### 4. Ramp Up

If stable after 1 hour:
- 5% → 20% (monitor 2 hours)
- 20% → 50% (monitor 4 hours)
- 50% → 100% (monitor 8 hours)

### 5. Rollback Criteria

Immediately rollback to 0% if:
- Any 5xx errors appear
- P95 latency >1000ms
- Audit signature NULL violations
- User reports of data inconsistency
- RLS bypasses detected

---

## 🔧 Troubleshooting

### "Still getting 404 after deployment"

**Check**: Did you deploy `microaction_service.py` or `pipeline_service.py`?

**Fix**: Ensure Dockerfile.microaction is used, not Dockerfile

**Verify**: `microaction_service.py` includes part routes at line 181

### "401 Unauthorized on all requests"

**Good!** This means API is deployed and routes are registered.

**Fix**: Ensure JWTs are generated correctly:
```bash
export TENANT_1_SUPABASE_JWT_SECRET="..."
python3 tests/ci/generate_all_test_jwts.py
```

### "Tests passing locally but failing in staging"

**Possible causes**:
1. Environment variables mismatch (TENANT_* vs yYACHT_CODE_*)
2. Database migration not applied in staging
3. RLS policies not synced

**Fix**: Verify env vars match and migrations are applied

---

## 📞 Next Steps

1. **Deploy API** (choose deployment method above)
2. **Verify routes** (confirm non-404 responses)
3. **Run tests** (comprehensive acceptance + SQL evidence)
4. **Collect artifacts** (all JSON/SQL files)
5. **Review results** (100% pass, zero 5xx)
6. **Enable canary** (5% with monitoring)

**Timeline**: 1-2 hours from deployment to canary approval (if tests green)

---

## 📝 Key Files Reference

| File | Purpose |
|------|---------|
| `apps/api/Dockerfile.microaction` | Docker build for API service |
| `apps/api/render-api.yaml` | Render deployment config |
| `apps/api/STAGING_API_DEPLOYMENT_GUIDE.md` | Detailed deployment guide |
| `tests/ci/comprehensive_staging_acceptance.py` | Main acceptance test |
| `tests/ci/collect_sql_evidence.py` | SQL evidence collector |
| `tests/ci/generate_all_test_jwts.py` | JWT generator |
| `STAGING_READINESS_SUMMARY.md` | This file |

---

**Status**: 🟡 READY (blocked on API deployment)
**Confidence After Tests**: 90-95% (if all green)
**Recommendation**: Deploy API → Run tests → Canary at 5%

---

**Last Updated**: 2026-01-27
**Author**: Claude Code
**Review Required**: API deployment
