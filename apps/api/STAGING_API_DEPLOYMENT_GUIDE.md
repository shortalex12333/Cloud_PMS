# Staging API Deployment Guide

**BLOCKER**: Part Lens v2 handlers cannot be tested in staging until the API service is deployed.

**Evidence**: https://app.celeste7.ai/v1/parts/low-stock → 404 (routes not registered)

---

## Quick Start (If Using Render)

### Option A: Update Existing Render Service

If you have an existing Render web service for the API:

1. **Update start command**:
   ```bash
   # Change from:
   uvicorn pipeline_service:app --host 0.0.0.0 --port $PORT

   # To:
   uvicorn microaction_service:app --host 0.0.0.0 --port $PORT
   ```

2. **Set environment variables** (in Render Dashboard):
   ```bash
   TENANT_1_SUPABASE_URL=https://vzsohavtuotocgrfkfyd.supabase.co
   TENANT_1_SUPABASE_SERVICE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
   TENANT_1_SUPABASE_JWT_SECRET=ep2o/+mEQD/b54M8W50Vk3GrsuVayQZf...
   DEFAULT_YACHT_CODE=yTEST_YACHT_001
   yTEST_YACHT_001_SUPABASE_URL=https://vzsohavtuotocgrfkfyd.supabase.co
   yTEST_YACHT_001_SUPABASE_SERVICE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
   ```

3. **Trigger redeploy**

4. **Verify**:
   ```bash
   curl https://your-render-app.onrender.com/health
   curl https://your-render-app.onrender.com/v1/parts/low-stock?yacht_id=85fe1119-b04c-41ac-80f1-829d23322598 \
     -H "Authorization: Bearer $JWT"
   ```

### Option B: Create New Render Service

Use the updated `render-api.yaml` provided below.

---

## Option C: Deploy to Any Platform

### 1. Build Docker Image

```bash
cd apps/api

# Build
docker build -t celeste-api:staging -f Dockerfile.microaction .

# Test locally
docker run -p 8080:8080 \
  -e TENANT_1_SUPABASE_URL=https://vzsohavtuotocgrfkfyd.supabase.co \
  -e TENANT_1_SUPABASE_SERVICE_KEY=... \
  celeste-api:staging

# Verify
curl http://localhost:8080/health
curl http://localhost:8080/v1/parts/low-stock?yacht_id=... \
  -H "Authorization: Bearer $JWT"
```

### 2. Deploy to Cloud

**Google Cloud Run**:
```bash
gcloud builds submit --tag gcr.io/PROJECT_ID/celeste-api:staging
gcloud run deploy celeste-api-staging \
  --image gcr.io/PROJECT_ID/celeste-api:staging \
  --platform managed \
  --region us-central1 \
  --set-env-vars TENANT_1_SUPABASE_URL=...,TENANT_1_SUPABASE_SERVICE_KEY=...
```

**AWS ECS/Fargate**:
```bash
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin ...
docker tag celeste-api:staging ACCOUNT.dkr.ecr.us-east-1.amazonaws.com/celeste-api:staging
docker push ACCOUNT.dkr.ecr.us-east-1.amazonaws.com/celeste-api:staging
# Then deploy via ECS console or Terraform
```

**Fly.io**:
```bash
fly launch --dockerfile Dockerfile.microaction
fly secrets set TENANT_1_SUPABASE_URL=... TENANT_1_SUPABASE_SERVICE_KEY=...
fly deploy
```

---

## Required Environment Variables

These must be set in your deployment platform:

```bash
# Tenant-specific (CI pattern)
TENANT_1_SUPABASE_URL=https://vzsohavtuotocgrfkfyd.supabase.co
TENANT_1_SUPABASE_SERVICE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ6c29oYXZ0dW90b2NncmZrZnlkIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MzU5Mjg3NSwiZXhwIjoyMDc5MTY4ODc1fQ.fC7eC_4xGnCHIebPzfaJ18pFMPKgImE7BuN0I3A-pSY
TENANT_1_SUPABASE_JWT_SECRET=ep2o/+mEQD/b54M8W50Vk3GrsuVayQZfValBnshte7yaZtoIGDhb9ffFQNU31su109d2wBz8WjSNX6wc3MiEFg==
TENANT_1_DB_PASSWORD=@-Ei-9Pa.uENn6g

# Yacht-specific (runtime pattern)
DEFAULT_YACHT_CODE=yTEST_YACHT_001
yTEST_YACHT_001_SUPABASE_URL=https://vzsohavtuotocgrfkfyd.supabase.co
yTEST_YACHT_001_SUPABASE_SERVICE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ6c29oYXZ0dW90b2NncmZrZnlkIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MzU5Mjg3NSwiZXhwIjoyMDc5MTY4ODc1fQ.fC7eC_4xGnCHIebPzfaJ18pFMPKgImE7BuN0I3A-pSY
```

**Note**: The middleware code uses both patterns. CI tests use `TENANT_*`; runtime handlers use `yYACHT_CODE_*`. Both must be set and point to the same Supabase instance for staging.

---

## Verification Checklist

After deployment, verify these endpoints return non-404:

```bash
export API_BASE="https://your-staging-api.example.com"
export JWT="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
export YACHT_ID="85fe1119-b04c-41ac-80f1-829d23322598"

# 1. Health check (should return 200)
curl -I $API_BASE/health

# 2. Low stock endpoint (should return 200 or 401/403, NOT 404)
curl -I "$API_BASE/v1/parts/low-stock?yacht_id=$YACHT_ID" \
  -H "Authorization: Bearer $JWT"

# 3. Suggestions endpoint (should return 200 or 401/403, NOT 404)
curl -I "$API_BASE/v1/parts/suggestions?part_id=SOME_UUID&yacht_id=$YACHT_ID" \
  -H "Authorization: Bearer $JWT"

# 4. Actions execute endpoint (should return 200/400/401/403, NOT 404)
curl -I "$API_BASE/v1/actions/execute" \
  -H "Authorization: Bearer $JWT" \
  -H "Content-Type: application/json"
```

**Expected**:
- ✅ 200, 401, 403, 400 → Routes are registered, API is live
- ❌ 404 → Routes not registered or API not deployed

---

## After Deployment: Run Staging Validation

Once the API is live and returning non-404:

```bash
cd /Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS

# 1. Set environment variables
export API_BASE="https://your-staging-api.example.com"
export TENANT_SUPABASE_URL="https://vzsohavtuotocgrfkfyd.supabase.co"
export TENANT_SUPABASE_SERVICE_KEY="..."
export TEST_YACHT_ID="85fe1119-b04c-41ac-80f1-829d23322598"
export HOD_JWT="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
export CAPTAIN_JWT="..."
export CREW_JWT="..."

# 2. Run staging acceptance
python3 tests/ci/staging_part_lens_acceptance.py

# 3. Run handler tests
export TEST_JWT=$HOD_JWT
python3 tests/ci/staging_handler_tests.py

# 4. Run stress test
CONCURRENCY=10 REQUESTS=50 OUTPUT_JSON=stress-results.json \
  python3 tests/stress/stress_action_list.py

# 5. Collect evidence
python3 tests/ci/collect_staging_evidence.py
```

---

## Troubleshooting

### "404 on all /v1/parts/* endpoints"

**Cause**: Routes not registered in the deployed service

**Fix**: Ensure `microaction_service.py` is the entry point, not `pipeline_service.py`

**Check**:
```python
# In apps/api/microaction_service.py
app.include_router(part_routes_router)  # Line 181
```

### "401 Unauthorized" or "403 Forbidden"

**Good!** This means the API is deployed and routes are registered. The issue is authentication, which is expected.

**Fix**: Use generated JWTs from `tests/ci/generate_all_test_jwts.py`

### "Network connectivity issue"

**Check DNS**: Does `https://app.celeste7.ai` resolve?

**Check if different domain**: The staging API might be at a different URL (e.g., `https://staging-api.celeste7.ai` or Render subdomain)

---

## Files Updated for Deployment

- `apps/api/Dockerfile.microaction` - New Dockerfile for microaction_service
- `apps/api/render-api.yaml` - Render configuration with web service
- `apps/api/STAGING_API_DEPLOYMENT_GUIDE.md` - This file

---

## Next Steps After Successful Deployment

1. ✅ Verify routes return non-404
2. ✅ Run staging acceptance (captures handler execution, idempotency, signatures)
3. ✅ Run role-based suggestions tests (Crew/HOD/Captain artifacts)
4. ✅ Run storage RLS cross-yacht 403 tests
5. ✅ Run stress test (P50/P95/P99, zero 5xx)
6. ✅ Collect SQL evidence (viewdefs, policies, single-tenant assertion)
7. ✅ Create artifacts package
8. ✅ Enable 5% canary with monitoring

**Timeline**: 1-2 hours from deployment to canary approval (assuming all tests green)
