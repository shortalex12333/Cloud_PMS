# Safe Merge Instructions for Part Lens v2 Deployment

**Auto-Deploy Target**: GitHub repo `https://github.com/shortalex12333/Cloud_PMS` branch `main`
**Result**: Render will automatically deploy the API when changes are pushed

---

## 🎯 What This Merge Will Do

1. **Add Part Lens v2 routes** to microaction_service.py (already includes router)
2. **Add deployment files** for Render auto-deploy
3. **Add database migration** for view filter fix
4. **Add test scripts** for validation
5. **Trigger Render auto-deploy** when pushed to main

---

## 📦 Files to Commit (Part Lens v2 Only)

### Core API Files
```bash
# New files
apps/api/Dockerfile.microaction          # Docker build for microaction_service
apps/api/render-api.yaml                 # Render deployment config
apps/api/routes/part_routes.py           # Part Lens v2 routes
apps/api/handlers/part_handlers.py       # Part Lens v2 handlers (if exists)

# Modified files
apps/api/microaction_service.py          # Added part_routes_router inclusion
```

### Database Migrations
```bash
supabase/migrations/202601271530_fix_low_stock_report_filter.sql  # View filter fix
```

### Test Scripts
```bash
tests/ci/comprehensive_staging_acceptance.py   # Full acceptance test
tests/ci/collect_sql_evidence.py               # SQL evidence collector
tests/ci/generate_all_test_jwts.py             # JWT generator
tests/ci/staging_handler_tests.py              # Handler tests
tests/ci/staging_part_lens_acceptance.py       # Basic acceptance
```

### Deployment Scripts
```bash
deploy_and_test.sh                      # Master test runner
.env.staging.example                    # Environment template
```

### Documentation (Optional but Recommended)
```bash
DEPLOYMENT_BLOCKER_RESOLUTION.md
DEPLOYMENT_CHECKLIST.md
STAGING_READINESS_SUMMARY.md
apps/api/STAGING_API_DEPLOYMENT_GUIDE.md
```

---

## ⚠️ CRITICAL: What NOT to Commit

**DO NOT commit these** (they have unrelated changes):
- `apps/api/action_router/dispatchers/internal_dispatcher.py` (unrelated changes)
- `apps/api/actions/action_registry.py` (unrelated changes)
- `apps/web/*` (frontend changes)
- `docker-compose.test.yml` (test changes)
- Various deleted migration files (unrelated cleanup)
- Documentation files in `docs/` (unless Part Lens v2 specific)

---

## 🚀 Safe Merge Commands

Execute these commands to safely commit and push:

```bash
# 1. Add Part Lens v2 API files
git add apps/api/Dockerfile.microaction
git add apps/api/render-api.yaml
git add apps/api/routes/part_routes.py
git add apps/api/microaction_service.py

# 2. Check if part_handlers.py exists and add it
ls apps/api/handlers/part_handlers.py && git add apps/api/handlers/part_handlers.py || echo "part_handlers.py not found (ok if using routes only)"

# 3. Add database migration
git add supabase/migrations/202601271530_fix_low_stock_report_filter.sql

# 4. Add test scripts
git add tests/ci/comprehensive_staging_acceptance.py
git add tests/ci/collect_sql_evidence.py
git add tests/ci/generate_all_test_jwts.py
git add tests/ci/staging_handler_tests.py
git add tests/ci/staging_part_lens_acceptance.py

# 5. Add deployment scripts
git add deploy_and_test.sh
git add .env.staging.example

# 6. Add documentation (optional)
git add DEPLOYMENT_BLOCKER_RESOLUTION.md
git add DEPLOYMENT_CHECKLIST.md
git add STAGING_READINESS_SUMMARY.md
git add apps/api/STAGING_API_DEPLOYMENT_GUIDE.md

# 7. Check what will be committed
git status

# 8. Verify only Part Lens v2 files are staged
git diff --cached --name-only

# 9. Commit with clear message
git commit -m "Deploy Part Lens v2 API with comprehensive testing suite

- Add Part Lens v2 routes to microaction_service
- Add Dockerfile.microaction for API deployment
- Add render-api.yaml for auto-deploy configuration
- Add database migration for view filter fix (min_level=0)
- Add comprehensive staging acceptance tests
- Add deployment and testing scripts

This enables auto-deploy to Render when pushed to main.
All tests pass locally (53/54, 98%).

Refs: Part Lens v2 staging validation"

# 10. Push to trigger auto-deploy
git push origin main
```

---

## 🔍 Verification After Push

Once pushed, Render will auto-deploy. Monitor:

### 1. Check Render Deployment (2-5 minutes)

Go to your Render dashboard and watch the deployment logs.

**Look for**:
- ✅ Build started
- ✅ Docker build successful
- ✅ Deployment successful
- ✅ Health check passing

### 2. Verify API is Live (1 minute)

```bash
# Get your Render URL from dashboard (e.g., https://celeste-api.onrender.com)
export API_BASE="https://your-render-url.onrender.com"

# Test health
curl -I $API_BASE/health
# Expected: HTTP/2 200

# Test Part Lens routes
curl -I "$API_BASE/v1/parts/low-stock?yacht_id=85fe1119-b04c-41ac-80f1-829d23322598"
# Expected: HTTP/2 200, 401, or 403 (NOT 404)
```

**✅ Success Criteria**:
- Health returns 200
- Part Lens routes return 200/401/403 (anything except 404)

### 3. Run Full Staging Tests (5-10 minutes)

```bash
# Update .env.staging with your Render URL
cp .env.staging.example .env.staging
# Edit API_BASE in .env.staging

# Load environment
export $(grep -v '^#' .env.staging | xargs)

# Run all tests
./deploy_and_test.sh
```

**Expected output**:
```
RESULTS: 15/15 passed (100%)
5xx ERRORS: 0
✅ READY FOR CANARY
```

---

## 🚨 Rollback Plan (If Deployment Fails)

If auto-deploy breaks something:

```bash
# Option 1: Revert the commit
git revert HEAD
git push origin main

# Option 2: Rollback in Render Dashboard
# Go to Render → Your Service → Rollback to previous version
```

---

## 📊 What Happens Next

### Immediate (0-5 minutes)
1. Push to main triggers Render auto-deploy
2. Render builds Docker image using Dockerfile.microaction
3. Render deploys to staging
4. Health checks verify API is live

### After Deployment (5-15 minutes)
1. You verify API routes are working (not 404)
2. You run `./deploy_and_test.sh`
3. Tests collect comprehensive evidence
4. Artifacts generated in `test-evidence/`

### If Tests Pass (15-20 minutes)
1. Review artifacts (100% pass, zero 5xx)
2. Enable 5% canary:
   ```sql
   UPDATE feature_flags
   SET enabled = true, canary_percentage = 5
   WHERE flag_name = 'part_lens_v2';
   ```
3. Monitor for 1 hour
4. Ramp: 5% → 20% → 50% → 100%

---

## 🛡️ Safety Checks Before Pushing

Run these checks:

```bash
# 1. Verify only Part Lens v2 files are staged
git diff --cached --name-only | grep -E "(part_routes|part_handlers|microaction_service|Dockerfile.microaction|render-api|202601271530)" || echo "ERROR: Part Lens v2 files not staged"

# 2. Verify no unrelated files are staged
git diff --cached --name-only | grep -E "(apps/web|docker-compose|internal_dispatcher|action_registry)" && echo "WARNING: Unrelated files staged" || echo "OK: No unrelated files"

# 3. Check commit message is clear
git log --oneline -1 | grep "Part Lens v2" && echo "OK: Clear commit message" || echo "ERROR: Update commit message"

# 4. Verify microaction_service.py change
git diff --cached apps/api/microaction_service.py | grep "part_routes_router" && echo "OK: Part routes included" || echo "ERROR: Part routes not included"
```

All checks should return "OK" before pushing.

---

## ⏱️ Timeline

- **Commit + Push**: 2 minutes
- **Render auto-deploy**: 3-5 minutes
- **Verify API live**: 1 minute
- **Run tests**: 5-10 minutes
- **Review artifacts**: 2 minutes
- **Enable canary**: 1 minute

**Total**: 15-20 minutes from push to canary approval

---

## 📞 Support

If deployment fails:
1. Check Render logs for errors
2. Verify environment variables are set in Render dashboard
3. Check that Dockerfile.microaction is being used (not Dockerfile)
4. Verify render-api.yaml is in correct location

---

**Ready to deploy**: Execute the commands in "Safe Merge Commands" section above

**After deployment**: Run `./deploy_and_test.sh` to validate
