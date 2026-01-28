# Part Lens v2: Deployment Blocker & Resolution

**Date**: 2026-01-27
**Status**: 🔴 **BLOCKED** - API not deployed
**Action Required**: **YOU** must deploy the API (I cannot access cloud accounts)

---

## 🚨 Critical Blocker

**I cannot deploy the API for you because**:
- I don't have access to your Render/cloud accounts
- I cannot execute deployment commands that require authentication
- I cannot create cloud resources or configure services

**What this means**:
- ❌ I cannot run staging tests (API returns 404)
- ❌ I cannot collect staging artifacts
- ❌ I cannot verify handlers in staging
- ❌ I cannot approve canary

---

## ✅ What I Have Completed

### 1. Database Layer (100% Complete)
- ✅ Fixed view filter bug (min_level=0 excluded)
- ✅ Applied migration to staging database
- ✅ Verified: 0 parts with min_level=0 in v_low_stock_report
- ✅ Proven canonical view works (SQL evidence)
- ✅ Transaction parity verified

### 2. JWT Tokens (100% Complete)
- ✅ Generated JWTs for HOD (chief_engineer)
- ✅ Generated JWTs for Captain
- ✅ Generated JWTs for Crew
- ✅ All tokens ready for use

### 3. Deployment Configuration (100% Complete)
- ✅ Created `Dockerfile.microaction` (builds microaction_service)
- ✅ Created `render-api.yaml` (Render deployment config)
- ✅ Created comprehensive deployment guide
- ✅ Verified microaction_service.py includes part_routes_router (line 181)

### 4. Test Suite (100% Complete)
- ✅ Created `comprehensive_staging_acceptance.py`:
  - Canonical view parity
  - View filter fix verification
  - Single-tenant assertion
  - Handler execution (receive, consume, adjust, transfer)
  - Idempotency (409)
  - Signature enforcement (400 without, 200 with)
  - Audit signature keys validation
  - Role-based suggestions (Crew/HOD/Captain visibility)
  - Suggestions edge case (qty<=0 handling)
  - Storage RLS cross-yacht (403 tests)
  - Storage manager-only delete
  - Zero 5xx comprehensive
- ✅ Created `collect_sql_evidence.py`:
  - View definitions (pg_get_viewdef)
  - RLS policies
  - Storage policies
  - Single-tenant assertion
  - Transaction parity samples
- ✅ Created `generate_all_test_jwts.py` (ready to use)

### 5. Master Test Runner (100% Complete)
- ✅ Created `deploy_and_test.sh`:
  - Verifies API deployment
  - Generates JWTs
  - Runs all acceptance tests
  - Collects SQL evidence
  - Runs stress test (if available)
  - Generates artifacts summary
  - Provides canary approval recommendation

### 6. Documentation (100% Complete)
- ✅ `DEPLOYMENT_CHECKLIST.md` - Step-by-step instructions
- ✅ `STAGING_API_DEPLOYMENT_GUIDE.md` - Detailed deployment guide
- ✅ `STAGING_READINESS_SUMMARY.md` - Complete overview
- ✅ `.env.staging.example` - Environment template

---

## 🎯 What YOU Must Do (3 Steps)

### Step 1: Deploy API (10-30 minutes)

**Choose ONE method**:

#### Method A: Render

```bash
# 1. Push files to git
git add apps/api/Dockerfile.microaction apps/api/render-api.yaml
git commit -m "Deploy Part Lens v2 API"
git push

# 2. Go to Render Dashboard
open https://dashboard.render.com/select-repo?type=blueprint

# 3. Select your repo → Choose render-api.yaml

# 4. Set environment variables:
TENANT_1_SUPABASE_URL=https://vzsohavtuotocgrfkfyd.supabase.co
TENANT_1_SUPABASE_SERVICE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
TENANT_1_SUPABASE_JWT_SECRET=ep2o/+mEQD/b54M8W50Vk3GrsuVayQZf...
DEFAULT_YACHT_CODE=yTEST_YACHT_001
yTEST_YACHT_001_SUPABASE_URL=https://vzsohavtuotocgrfkfyd.supabase.co
yTEST_YACHT_001_SUPABASE_SERVICE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

# 5. Click "Apply" and wait for deployment (~5 minutes)
```

#### Method B: Docker + Any Cloud

```bash
cd apps/api
docker build -t celeste-api:staging -f Dockerfile.microaction .

# Test locally
docker run -p 8080:8080 -e ... celeste-api:staging

# Deploy to your cloud provider
# (See STAGING_API_DEPLOYMENT_GUIDE.md)
```

### Step 2: Verify API is Live (1 minute)

```bash
# Replace with your actual deployed URL
export API_BASE="https://your-deployed-url"

# Should return 200 (NOT 404)
curl -I $API_BASE/health

# Should return 200/401/403 (NOT 404)
curl -I "$API_BASE/v1/parts/low-stock?yacht_id=85fe1119-b04c-41ac-80f1-829d23322598"
```

**Success**: Health returns 200, Part Lens routes return 200/401/403
**Failure**: Anything returns 404 → API not deployed correctly

### Step 3: Run Tests (5-10 minutes)

```bash
# 1. Configure environment
cp .env.staging.example .env.staging
# Edit .env.staging with your API_BASE URL

# 2. Load environment
export $(grep -v '^#' .env.staging | xargs)

# 3. Run tests
./deploy_and_test.sh
```

**Expected output if all green**:
```
=============================================================================
STAGING VALIDATION COMPLETE
=============================================================================

RESULTS: 15/15 passed (100%)
5xx ERRORS: 0

✅ READY FOR CANARY

Next step: Enable 5% canary with monitoring
=============================================================================
```

---

## 📊 What Happens After Tests Pass

### Artifacts Generated

```
test-evidence/
├── comprehensive_acceptance_summary.json  ← Main results
├── canonical_parity.json                  ← Proof canonical view works
├── view_filter_fix.json                   ← Proof min_level=0 excluded
├── single_tenant_assertion.json           ← Proof single tenant
├── receive_part_201.json                  ← Handler execution
├── idempotency_409.json                   ← Idempotency proof
├── adjust_stock_no_sig_400.json           ← Signature enforcement
├── adjust_stock_with_sig_200.json         ← Signed action success
├── role_based_suggestions.json            ← Role visibility proof
├── suggestions_edge_case_pass.json        ← Edge case handling
├── storage_rls_cross_yacht.json           ← Storage RLS 403 proof
├── zero_5xx_comprehensive.json            ← Zero 5xx proof
├── viewdef_*.sql                          ← View definitions (3 files)
├── rls_policies.json                      ← RLS policies
├── storage_policies.json                  ← Storage policies
├── transaction_parity_samples.json        ← Transaction parity
└── STAGING_VALIDATION_COMPLETE.md         ← Summary report
```

### Canary Approval

If tests show **100% pass** and **zero 5xx**, you can enable canary:

```sql
UPDATE feature_flags
SET enabled = true,
    canary_percentage = 5,
    updated_at = NOW()
WHERE flag_name = 'part_lens_v2';
```

Then monitor and ramp: 5% (1h) → 20% (2h) → 50% (4h) → 100%

---

## 🔍 Why We Need This

**Doctrine requirement**: "Staging CI with real JWTs before canary"

**What we cannot approve without**:
- ❌ Handler execution in staging
- ❌ Idempotency verification (409)
- ❌ Signature enforcement (400/200)
- ❌ Role-based suggestions (Crew/HOD/Captain)
- ❌ Zero 5xx comprehensive proof
- ❌ Stress testing

**All of these require**: API deployed and returning non-404

---

## 📞 Summary

**My work**: ✅ COMPLETE (database, tests, deployment config, docs)
**Your work**: 🔴 REQUIRED (deploy API, run tests)
**Timeline**: 30 minutes to deploy + 10 minutes to test = **40 minutes to canary approval**

**Exact next step**: Deploy the API using one of the methods in Step 1 above

---

## 📁 Quick Reference

| What | Where |
|------|-------|
| Deploy API | `DEPLOYMENT_CHECKLIST.md` Step 1 |
| Verify API | `DEPLOYMENT_CHECKLIST.md` Step 2 |
| Run tests | `./deploy_and_test.sh` |
| Review artifacts | `test-evidence/` |
| Enable canary | `DEPLOYMENT_CHECKLIST.md` Step 5 |

---

**Last Updated**: 2026-01-27
**Status**: Waiting for API deployment
**Next Action**: Deploy API → Run `./deploy_and_test.sh` → Review artifacts → Enable canary
