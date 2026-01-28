# Part Lens v2: Final Deployment Steps

**You must do these 3 simple steps to deploy and validate Part Lens v2.**

---

## Step 1: Commit and Push (2 minutes)

Run this script to safely commit Part Lens v2 files and trigger Render auto-deploy:

```bash
./commit_and_deploy.sh
```

**What this does**:
1. Stages ONLY Part Lens v2 files (API, migrations, tests, docs)
2. Creates a clear commit message
3. Pushes to `origin/main`
4. Triggers Render auto-deploy

**You'll see**:
```
✓ No unrelated files staged
✓ microaction_service.py includes part routes
✓ Commit created successfully

Push now? (y/N)
```

Type `y` and press Enter.

---

## Step 2: Monitor Render Deployment (3-5 minutes)

While Render deploys, go to your Render dashboard:

```
https://dashboard.render.com
```

**Watch for**:
- ✅ Build started
- ✅ Docker build successful
- ✅ Deployment successful
- ✅ Health check passing

**If deployment fails**, check:
1. Environment variables are set in Render dashboard
2. Dockerfile.microaction is being used (not Dockerfile)
3. Check logs for errors

---

## Step 3: Run Tests (5-10 minutes)

Once Render shows "Live", run the test suite:

```bash
# Get your Render URL from dashboard
export API_BASE="https://your-app.onrender.com"

# Quick verify API is live
curl -I $API_BASE/health
# Expected: HTTP/2 200

curl -I "$API_BASE/v1/parts/low-stock?yacht_id=85fe1119-b04c-41ac-80f1-829d23322598"
# Expected: HTTP/2 200, 401, or 403 (NOT 404)

# If both return non-404, run full tests
export TENANT_1_SUPABASE_URL="https://vzsohavtuotocgrfkfyd.supabase.co"
export TENANT_1_SUPABASE_SERVICE_KEY="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ6c29oYXZ0dW90b2NncmZrZnlkIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MzU5Mjg3NSwiZXhwIjoyMDc5MTY4ODc1fQ.fC7eC_4xGnCHIebPzfaJ18pFMPKgImE7BuN0I3A-pSY"
export TENANT_1_SUPABASE_JWT_SECRET="ep2o/+mEQD/b54M8W50Vk3GrsuVayQZfValBnshte7yaZtoIGDhb9ffFQNU31su109d2wBz8WjSNX6wc3MiEFg=="
export TENANT_1_DB_PASSWORD="@-Ei-9Pa.uENn6g"
export TEST_YACHT_ID="85fe1119-b04c-41ac-80f1-829d23322598"

./deploy_and_test.sh
```

**Expected output**:
```
RESULTS: 15/15 passed (100%)
5xx ERRORS: 0

✅ READY FOR CANARY
```

---

## What Happens If Tests Pass

All artifacts will be in `test-evidence/`:

```
test-evidence/
├── comprehensive_acceptance_summary.json  ← Main results
├── zero_5xx_comprehensive.json            ← Zero 5xx proof
├── role_based_suggestions.json            ← Role visibility
├── viewdef_*.sql                          ← View definitions
├── rls_policies.json                      ← RLS policies
├── storage_rls_cross_yacht.json           ← Storage RLS 403 proof
└── ... (15+ files total)
```

**Enable 5% Canary**:

```sql
-- In Supabase SQL Editor
UPDATE feature_flags
SET enabled = true,
    canary_percentage = 5,
    updated_at = NOW()
WHERE flag_name = 'part_lens_v2';
```

**Monitor for 1 hour**, then ramp: 5% → 20% → 50% → 100%

---

## Troubleshooting

### "Health endpoint returns 404"

**Cause**: API not deployed or wrong URL

**Fix**: Check Render dashboard for actual URL

### "Part Lens routes return 404"

**Cause**: microaction_service.py not deployed or routes not registered

**Fix**: Check Render logs, verify Dockerfile.microaction is used

### "Tests fail with connection errors"

**Cause**: Environment variables not set

**Fix**: Verify all TENANT_1_* variables are set correctly

### "Permission denied on commit_and_deploy.sh"

**Fix**: Make it executable first:
```bash
chmod +x commit_and_deploy.sh
```

---

## Quick Command Reference

```bash
# 1. Deploy
./commit_and_deploy.sh

# 2. Verify (replace URL with your Render URL)
curl -I https://your-app.onrender.com/health

# 3. Test
export API_BASE="https://your-app.onrender.com"
export TENANT_1_SUPABASE_URL="https://vzsohavtuotocgrfkfyd.supabase.co"
export TENANT_1_SUPABASE_SERVICE_KEY="..."
export TENANT_1_SUPABASE_JWT_SECRET="..."
export TENANT_1_DB_PASSWORD="..."
export TEST_YACHT_ID="85fe1119-b04c-41ac-80f1-829d23322598"
./deploy_and_test.sh

# 4. Review
cat test-evidence/comprehensive_acceptance_summary.json | jq '.success_rate, .five_xx_count'

# 5. Enable canary (if 100% pass, zero 5xx)
psql ... -c "UPDATE feature_flags SET enabled = true, canary_percentage = 5 WHERE flag_name = 'part_lens_v2';"
```

---

## Timeline

- **Commit + Push**: 2 minutes
- **Render deploy**: 3-5 minutes
- **Run tests**: 5-10 minutes
- **Review artifacts**: 2 minutes
- **Enable canary**: 1 minute

**Total**: 15-20 minutes from start to canary

---

## Files Created for You

| File | Purpose |
|------|---------|
| **`commit_and_deploy.sh`** | **Run this first** - Safe commit and push |
| **`deploy_and_test.sh`** | **Run this second** - Full test suite |
| `FINAL_DEPLOYMENT_STEPS.md` | This file - Simple instructions |
| `SAFE_MERGE_INSTRUCTIONS.md` | Detailed merge guide (if you need it) |
| `DEPLOYMENT_CHECKLIST.md` | Complete deployment checklist |
| `STAGING_READINESS_SUMMARY.md` | Readiness overview |

---

## Summary

**Right now**:
1. Run `./commit_and_deploy.sh`
2. Wait for Render to deploy (watch dashboard)
3. Run `./deploy_and_test.sh` (after verifying API is live)

**If tests pass** (100%, zero 5xx):
4. Enable 5% canary
5. Monitor and ramp

**Timeline**: 15-20 minutes total

---

**Ready? Run `./commit_and_deploy.sh` now.**
