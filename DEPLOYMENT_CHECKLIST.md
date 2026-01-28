# Part Lens v2: Deployment Checklist

**Status**: 🟡 Ready to Deploy
**Blocker**: API must be deployed to staging before tests can run

---

## ⚠️ IMPORTANT: I Cannot Deploy For You

I have prepared everything, but I **cannot**:
- Access your Render/cloud account
- Deploy the API service
- Run tests against a live API (404 blocker)

You **must**:
1. Deploy the API yourself
2. Verify it's live (non-404 responses)
3. Run the test script

---

## 🚀 Step-by-Step Deployment

### Step 1: Deploy API to Staging

**Option A: Render (Recommended)**

```bash
# 1. Push deployment files to git
git add apps/api/Dockerfile.microaction apps/api/render-api.yaml
git commit -m "Deploy Part Lens v2 API to staging"
git push

# 2. Deploy via Render Dashboard
# Go to: https://dashboard.render.com/select-repo?type=blueprint
# Select your repo → Choose render-api.yaml
# Set environment variables (see below)
# Click "Apply"

# 3. Wait for deployment (~5-10 minutes)
```

**Required Environment Variables in Render Dashboard**:
```bash
TENANT_1_SUPABASE_URL=https://vzsohavtuotocgrfkfyd.supabase.co
TENANT_1_SUPABASE_SERVICE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ6c29oYXZ0dW90b2NncmZrZnlkIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MzU5Mjg3NSwiZXhwIjoyMDc5MTY4ODc1fQ.fC7eC_4xGnCHIebPzfaJ18pFMPKgImE7BuN0I3A-pSY
TENANT_1_SUPABASE_JWT_SECRET=ep2o/+mEQD/b54M8W50Vk3GrsuVayQZfValBnshte7yaZtoIGDhb9ffFQNU31su109d2wBz8WjSNX6wc3MiEFg==
DEFAULT_YACHT_CODE=yTEST_YACHT_001
yTEST_YACHT_001_SUPABASE_URL=https://vzsohavtuotocgrfkfyd.supabase.co
yTEST_YACHT_001_SUPABASE_SERVICE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ6c29oYXZ0dW90b2NncmZrZnlkIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MzU5Mjg3NSwiZXhwIjoyMDc5MTY4ODc1fQ.fC7eC_4xGnCHIebPzfaJ18pFMPKgImE7BuN0I3A-pSY
```

**Option B: Docker + Any Cloud**

```bash
cd apps/api

# Build
docker build -t celeste-api:staging -f Dockerfile.microaction .

# Test locally first
docker run -p 8080:8080 \
  -e TENANT_1_SUPABASE_URL=https://vzsohavtuotocgrfkfyd.supabase.co \
  -e TENANT_1_SUPABASE_SERVICE_KEY='...' \
  -e TENANT_1_SUPABASE_JWT_SECRET='...' \
  -e DEFAULT_YACHT_CODE=yTEST_YACHT_001 \
  -e yTEST_YACHT_001_SUPABASE_URL=https://vzsohavtuotocgrfkfyd.supabase.co \
  -e yTEST_YACHT_001_SUPABASE_SERVICE_KEY='...' \
  celeste-api:staging

# Verify locally
curl http://localhost:8080/health  # Should return 200

# Deploy to your cloud provider
# (See STAGING_API_DEPLOYMENT_GUIDE.md for platform-specific commands)
```

### Step 2: Verify API is Live

```bash
# Get your deployed URL (e.g., from Render dashboard)
export API_BASE="https://celeste-api-staging.onrender.com"

# Test health
curl -I $API_BASE/health
# Expected: HTTP/2 200 (NOT 404)

# Test Part Lens routes
curl -I "$API_BASE/v1/parts/low-stock?yacht_id=85fe1119-b04c-41ac-80f1-829d23322598"
# Expected: HTTP/2 200, 401, or 403 (NOT 404)
```

**✅ Success Criteria**:
- Health endpoint returns 200
- Part Lens routes return 200/401/403 (anything except 404)

**❌ Failure (API not deployed)**:
- Health endpoint returns 404
- Part Lens routes return 404

### Step 3: Run All Tests

```bash
# Copy environment template
cp .env.staging.example .env.staging

# Edit .env.staging with your deployed API URL
# API_BASE=https://your-actual-deployed-url

# Load environment
export $(grep -v '^#' .env.staging | xargs)

# Make script executable
chmod +x deploy_and_test.sh

# Run all tests
./deploy_and_test.sh
```

**What this script does**:
1. ✅ Verifies API is deployed (health + routes check)
2. ✅ Generates JWTs for all roles (HOD, Captain, Crew)
3. ✅ Runs comprehensive staging acceptance:
   - Canonical view parity
   - View filter fix
   - Single-tenant assertion
   - Handler execution (receive, consume, adjust, transfer)
   - Idempotency (409)
   - Signature enforcement (400 without, 200 with)
   - Audit signature keys
   - Role-based suggestions (Crew/HOD/Captain)
   - Suggestions edge case (qty<=0)
   - Storage RLS cross-yacht (403 tests)
   - Zero 5xx comprehensive
4. ✅ Collects SQL evidence (viewdefs, policies, parity)
5. ✅ Runs stress test (if available)
6. ✅ Generates artifacts summary

**Expected output**:
```
=============================================================================
STAGING VALIDATION COMPLETE
=============================================================================

Artifacts location: test-evidence/
Log file: test-evidence/deploy_test_YYYYMMDD_HHMMSS.log

✅ READY FOR CANARY

Next step: Enable 5% canary with monitoring
=============================================================================
```

### Step 4: Review Artifacts

```bash
# Check main results
cat test-evidence/comprehensive_acceptance_summary.json | jq '.success_rate, .five_xx_count'
# Expected: 1.0 (100%), 0 (zero 5xx)

# Check role-based suggestions
cat test-evidence/role_based_suggestions.json | jq '.'
# Expected: Crew=no MUTATE/SIGNED, HOD=MUTATE, Captain=SIGNED

# Check zero 5xx proof
cat test-evidence/zero_5xx_comprehensive.json | jq '.["5xx_count"]'
# Expected: 0

# View all artifacts
ls -lh test-evidence/
```

### Step 5: Enable Canary (Only if 100% pass, zero 5xx)

```sql
-- In Supabase SQL Editor
UPDATE feature_flags
SET enabled = true,
    canary_percentage = 5,
    updated_at = NOW()
WHERE flag_name = 'part_lens_v2';
```

**Monitor for 1 hour**:
- Error rate dashboard (watch for 5xx)
- P95/P99 latency (target: <500ms)
- Audit log signature checks (no NULLs)
- User feedback

**Ramp schedule**:
- Hour 0-1: 5% (monitor closely)
- Hour 1-3: 20% (if stable)
- Hour 3-7: 50% (if stable)
- Hour 7-15: 100% (if stable)

**Rollback triggers** (immediate rollback to 0%):
- Any 5xx errors
- P95 latency >1000ms
- NULL audit signatures
- User reports of data loss/inconsistency

---

## 📋 Quick Pre-Deployment Checklist

Before deploying, verify:

- [ ] Dockerfile.microaction exists and uses `microaction_service:app`
- [ ] render-api.yaml has correct env vars
- [ ] microaction_service.py includes: `app.include_router(part_routes_router)`
- [ ] All environment variables are set (no placeholders)
- [ ] Database migrations applied (view filter fix)
- [ ] JWTs can be generated (JWT secret is correct)

After deploying, verify:

- [ ] Health endpoint returns 200 (not 404)
- [ ] Part Lens routes return 200/401/403 (not 404)
- [ ] Can generate JWTs successfully
- [ ] Test script runs without errors

---

## 🔧 Troubleshooting

### "404 on /health"

**Cause**: API not deployed or wrong URL

**Fix**: Check deployment logs, verify URL is correct

### "404 on /v1/parts/*"

**Cause**: microaction_service.py not deployed or routes not registered

**Fix**: Verify Dockerfile.microaction is used, check that line 181 includes part_routes_router

### "Cannot generate JWTs"

**Cause**: TENANT_1_SUPABASE_JWT_SECRET not set or incorrect

**Fix**: Verify secret matches Supabase project JWT secret

### "Tests fail with connection errors"

**Cause**: API not accessible or environment variables incorrect

**Fix**: Verify API_BASE is correct and accessible, check all env vars are set

---

## 📁 Files Reference

| File | Purpose |
|------|---------|
| `deploy_and_test.sh` | Master test runner (run this) |
| `.env.staging.example` | Environment template |
| `apps/api/Dockerfile.microaction` | Docker build file |
| `apps/api/render-api.yaml` | Render deployment config |
| `tests/ci/comprehensive_staging_acceptance.py` | Main test suite |
| `tests/ci/collect_sql_evidence.py` | SQL evidence collector |
| `tests/ci/generate_all_test_jwts.py` | JWT generator |
| `STAGING_API_DEPLOYMENT_GUIDE.md` | Detailed deployment guide |
| `STAGING_READINESS_SUMMARY.md` | Readiness summary |

---

## 🎯 Success Criteria

**Before canary approval**:
- ✅ API deployed and returning non-404
- ✅ 100% test pass rate
- ✅ Zero 5xx errors
- ✅ Role-based suggestions verified
- ✅ SQL evidence collected
- ✅ All artifacts generated

**Timeline**: 1-2 hours from deployment to canary

---

**Next Step**: Deploy the API, then run `./deploy_and_test.sh`
