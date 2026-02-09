# Deployment Instructions - Commit 6b9292f

**Status**: 🚀 **DEPLOYMENT IN PROGRESS**
**Time Started**: 2026-02-09 ~09:00 EST
**Expected Completion**: ~09:05 EST (~5 minutes)

---

## 📊 What's Being Deployed

**Commit**: 6b9292f
**PR**: #179
**Branch**: feature/hor-complete-wiring → main

### Changes:
1. ✅ Added 26 part-specific keywords (filter, bearing, gasket, etc.)
2. ✅ Fixed fusion normalization ("part" → "parts")
3. ✅ Removed redundant validation code
4. ✅ Work order RBAC and GraphRAG fixes

---

## ⏱️ Wait for Deployment to Complete

### Monitor Render Dashboard
**URL**: https://dashboard.render.com/

**Watch for**:
- ✅ Build completes
- ✅ Service restarts
- ✅ Health check passes
- ✅ "Live" status displayed

**Duration**: ~5 minutes from merge

---

## ✅ After Deployment Completes

### Run Verification Script

```bash
# Wait for deployment to show "Live" in Render dashboard
# Then run:

./verify_inventory_deployment.sh
```

This will test:
1. ✓ "fuel filter" → domain="parts"
2. ✓ Fusion normalization + actions
3. ✓ "bearing" → domain="parts"
4. ✓ CREW blocked from MUTATE (403)
5. ✓ Suggestions filtered by role

**Expected**: All 5 tests PASS ✅

---

## 📋 Manual Verification (If Script Fails)

If the script encounters issues, run tests manually:

### Test 1: Domain Detection (fuel filter)
```bash
curl -s -X POST "https://pipeline-core.int.celeste7.ai/v2/search" \
  -H "Authorization: Bearer $(jq -r '.HOD.jwt' test-jwts.json)" \
  -H "Content-Type: application/json" \
  -H "X-Yacht-ID: 85fe1119-b04c-41ac-80f1-829d23322598" \
  -d '{"query_text":"fuel filter"}' | jq '.context.domain'
```
**Expected**: `"parts"`

### Test 2: Fusion Normalization
```bash
curl -s -X POST "https://pipeline-core.int.celeste7.ai/search" \
  -H "Authorization: Bearer $(jq -r '.HOD.jwt' test-jwts.json)" \
  -H "Content-Type: application/json" \
  -H "X-Yacht-ID: 85fe1119-b04c-41ac-80f1-829d23322598" \
  -d '{"query":"fuel filter"}' | jq '{domain:.context.domain,actions:(.actions|length)}'
```
**Expected**: `{"domain":"parts","actions":>0}`

### Test 3: Domain Detection (bearing)
```bash
curl -s -X POST "https://pipeline-core.int.celeste7.ai/v2/search" \
  -H "Authorization: Bearer $(jq -r '.CREW.jwt' test-jwts.json)" \
  -H "Content-Type: application/json" \
  -H "X-Yacht-ID: 85fe1119-b04c-41ac-80f1-829d23322598" \
  -d '{"query_text":"bearing"}' | jq '.context.domain'
```
**Expected**: `"parts"`

### Test 4: Role Gating
```bash
curl -s -w "\nHTTP:%{http_code}" -X POST "https://pipeline-core.int.celeste7.ai/v1/actions/execute" \
  -H "Authorization: Bearer $(jq -r '.CREW.jwt' test-jwts.json)" \
  -H "Content-Type: application/json" \
  -d '{
    "action":"log_part_usage",
    "context":{"yacht_id":"85fe1119-b04c-41ac-80f1-829d23322598"},
    "payload":{"part_id":"f7913ad1-6832-4169-b816-4538c8b7a417","quantity":1}
  }' | jq '.error_code'
```
**Expected**: `"FORBIDDEN"` with `HTTP:403`

### Test 5: Suggestions
```bash
curl -s "https://pipeline-core.int.celeste7.ai/v1/actions/list?q=check+stock&domain=parts" \
  -H "Authorization: Bearer $(jq -r '.CREW.jwt' test-jwts.json)" | \
  jq '{total:(.actions|length),mutate:[.actions[]|select(.variant=="MUTATE")|.action_id]}'
```
**Expected**: `{"total":2,"mutate":[]}`

---

## ✅ Success Criteria

**Deployment Successful If**:
- ✅ All 5 tests pass
- ✅ Render shows "Live" status
- ✅ No error spike in logs
- ✅ Service health check passes

**Result**: 🎉 **DEPLOYMENT COMPLETE** - Inventory Lens domain detection fixed!

---

## ⚠️ If Tests Fail

### Investigate
1. Check Render logs for errors
2. Verify service restarted properly
3. Check if JWTs are still valid (may need refresh)
4. Look for any deployment errors

### Rollback (If Critical Failure)

**Option 1: Render Dashboard**
1. Go to https://dashboard.render.com/
2. Select "api" service
3. Click "Manual Deploy"
4. Select commit before 6b9292f
5. Deploy

**Option 2: Git Revert**
```bash
git revert 6b9292f
git push origin main
```

**Rollback Time**: ~5 minutes

---

## 📈 Next Steps After Verification

### If All Tests Pass ✅
1. Update PR #179 with verification results
2. Close related tickets
3. Notify team: Domain detection fixed
4. Monitor for 24h for any issues

### If Tests Fail ❌
1. Check logs for specific errors
2. Document failure details
3. Decide: Fix forward or rollback
4. Update tickets with findings

---

## 🔗 Quick Links

- **Render**: https://dashboard.render.com/
- **PR**: https://github.com/shortalex12333/Cloud_PMS/pull/179
- **Script**: `./verify_inventory_deployment.sh`
- **Evidence**: `apps/api/test_artifacts/inventory/`
- **Tracking**: `DEPLOYMENT_TRACKING.md`

---

## 📞 Summary

**What to do now**:
1. ⏱️ Wait ~5 minutes for deployment
2. 🔍 Check Render dashboard shows "Live"
3. ✅ Run `./verify_inventory_deployment.sh`
4. 🎉 Confirm all tests pass

**Expected result**: All 5 tests PASS, deployment successful ✅
