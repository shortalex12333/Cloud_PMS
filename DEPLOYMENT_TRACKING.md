# Deployment Tracking - Inventory Lens Domain Detection

**Date**: 2026-02-09
**PR**: #179
**Commit**: 6b9292f
**Status**: 🚀 **DEPLOYING**

---

## 🎯 Deployment Details

**Merged To**: main
**Deploy Commit**: 6b9292f
**Deploy Time**: 2026-02-09 ~09:00 EST
**Environment**: Production (pipeline-core.int.celeste7.ai)
**Expected Duration**: ~5 minutes

---

## 📊 Changes Being Deployed

### 1. Domain Detection Keywords
- **File**: `apps/api/orchestration/term_classifier.py`
- **Change**: +26 part keywords (filter, bearing, gasket, seal, etc.)
- **Impact**: "fuel filter", "bearing" → domain="parts"

### 2. Fusion Normalization
- **File**: `apps/api/routes/orchestrated_search_routes.py`
- **Change**: Normalize "part"→"parts", "inventory"→"parts"
- **Impact**: Consistent domain="parts", action surfacing works

### 3. Code Cleanup
- **File**: `apps/api/routes/p0_actions_routes.py`
- **Change**: Remove redundant validation
- **Impact**: Cleaner code, no functional change

---

## ✅ Post-Deploy Verification (Run After Deployment Completes)

### Quick Verification Commands

```bash
BASE="https://pipeline-core.int.celeste7.ai"
CREW_JWT=$(jq -r '.CREW.jwt' test-jwts.json)
HOD_JWT=$(jq -r '.HOD.jwt' test-jwts.json)
YACHT_ID="85fe1119-b04c-41ac-80f1-829d23322598"

echo "=== Test 1: Domain Detection (fuel filter) ==="
curl -s -X POST "$BASE/v2/search" \
  -H "Authorization: Bearer $HOD_JWT" \
  -H "Content-Type: application/json" \
  -H "X-Yacht-ID: $YACHT_ID" \
  -d '{"query_text":"fuel filter"}' | jq '.context.domain'
# Expected: "parts"
echo ""

echo "=== Test 2: Fusion Normalization + Actions ==="
curl -s -X POST "$BASE/search" \
  -H "Authorization: Bearer $HOD_JWT" \
  -H "Content-Type: application/json" \
  -H "X-Yacht-ID: $YACHT_ID" \
  -d '{"query":"fuel filter"}' | jq '{domain:.context.domain,actions:(.actions|length)}'
# Expected: {"domain":"parts","actions":>0}
echo ""

echo "=== Test 3: Domain Detection (bearing) ==="
curl -s -X POST "$BASE/v2/search" \
  -H "Authorization: Bearer $CREW_JWT" \
  -H "Content-Type: application/json" \
  -H "X-Yacht-ID: $YACHT_ID" \
  -d '{"query_text":"bearing"}' | jq '.context.domain'
# Expected: "parts"
echo ""

echo "=== Test 4: Role Gating (CREW blocked) ==="
curl -s -w "\nHTTP:%{http_code}\n" -X POST "$BASE/v1/actions/execute" \
  -H "Authorization: Bearer $CREW_JWT" \
  -H "Content-Type: application/json" \
  -d '{
    "action":"log_part_usage",
    "context":{"yacht_id":"'"$YACHT_ID"'"},
    "payload":{"part_id":"f7913ad1-6832-4169-b816-4538c8b7a417","quantity":1}
  }' | jq '{error_code}'
# Expected: {"error_code":"FORBIDDEN"} HTTP:403
echo ""

echo "=== Test 5: Suggestions (CREW READ-only) ==="
curl -s "$BASE/v1/actions/list?q=check+stock&domain=parts" \
  -H "Authorization: Bearer $CREW_JWT" | jq '{
    total:(.actions|length),
    read:[.actions[]|select(.variant=="READ")|.action_id],
    mutate:[.actions[]|select(.variant=="MUTATE")|.action_id]
  }'
# Expected: {"total":2,"read":["check_stock_level","view_part_details"],"mutate":[]}
```

---

## 📋 Verification Checklist

### Critical Tests (Must Pass)
- [ ] Test 1: "fuel filter" → domain="parts" ✅
- [ ] Test 2: Fusion domain="parts" + actions>0 ✅
- [ ] Test 3: "bearing" → domain="parts" ✅
- [ ] Test 4: CREW log_part_usage → HTTP 403 ✅
- [ ] Test 5: CREW suggestions → READ only ✅

### Additional Verification
- [ ] Check Render logs for deployment errors
- [ ] Verify service health: GET /health
- [ ] Check for any error spike in monitoring
- [ ] Verify no regressions in other lenses

---

## 🔍 Monitoring Points

### Render Dashboard
**URL**: https://dashboard.render.com/

**Check**:
- [ ] Build completed successfully
- [ ] Service restarted
- [ ] Health check passed
- [ ] No errors in deploy logs

### Application Logs
**Watch for**:
- ✅ "fuel filter" queries returning parts results
- ✅ Fusion returning normalized domain
- ✅ Role validation working (403 for crew MUTATE)
- ❌ Any unexpected 500 errors
- ❌ Domain classification failures

---

## ⚠️ Known Issues (Not Blocking)

### Issue #1: HOD log_part_usage DB Error
**Status**: Separate ticket (TICKET_HOD_LOG_PART_USAGE_DB_ERROR.md)
**Impact**: HOD cannot log part usage (DB trigger error)
**Action**: Backend team to fix database trigger
**Timeline**: Separate deployment

### Issue #2: /v1/search Endpoint 404
**Status**: Separate ticket (TICKET_V1_SEARCH_404.md)
**Impact**: /v1/search not accessible (may be deprecated)
**Action**: Investigate endpoint mounting
**Timeline**: Separate investigation

---

## 🔄 Rollback Plan (If Needed)

### Signs to Rollback
- ❌ Test 1-5 fail after deployment
- ❌ Spike in 500 errors
- ❌ Domain detection broken for other lenses
- ❌ Frontend reports broken search

### Rollback Steps

**Option 1: Render Dashboard (Fastest)**
```
1. Go to https://dashboard.render.com/
2. Select "api" service
3. Click "Manual Deploy"
4. Select commit before 6b9292f
5. Click "Deploy"
```

**Option 2: Git Revert**
```bash
git revert 6b9292f
git push origin main
# Wait for automatic deployment
```

**Rollback Time**: ~5 minutes

---

## 📊 Success Criteria

### Deployment Successful If:
1. ✅ All 5 critical tests pass
2. ✅ No error spike in logs
3. ✅ Service health check passes
4. ✅ "fuel filter" and "bearing" route to parts domain
5. ✅ Fusion returns normalized domain="parts"
6. ✅ Role gating still works (CREW blocked)

### Deployment Failed If:
1. ❌ Any critical test fails
2. ❌ Service won't start or health check fails
3. ❌ Domain detection breaks for other queries
4. ❌ Role gating breaks (CREW allowed MUTATE)

---

## 📝 Post-Deploy Report Template

```markdown
## Deployment Verification Report

**Commit**: 6b9292f
**Deploy Time**: 2026-02-09 HH:MM EST
**Verification Time**: 2026-02-09 HH:MM EST
**Verified By**: [Name]

### Test Results
- [ ] Test 1 (fuel filter domain): PASS/FAIL
- [ ] Test 2 (fusion normalization): PASS/FAIL
- [ ] Test 3 (bearing domain): PASS/FAIL
- [ ] Test 4 (CREW blocked): PASS/FAIL
- [ ] Test 5 (suggestions filtered): PASS/FAIL

### Render Status
- [ ] Build completed: YES/NO
- [ ] Service healthy: YES/NO
- [ ] Logs clean: YES/NO

### Decision
- [ ] ✅ Deployment SUCCESSFUL - all tests pass
- [ ] ⚠️ Deployment PARTIAL - some issues but functional
- [ ] ❌ Deployment FAILED - rollback required

### Notes
[Any observations, issues, or additional context]
```

---

## 🔗 Reference Links

- **PR**: https://github.com/shortalex12333/Cloud_PMS/pull/179
- **Commit**: 6b9292f
- **Evidence**: apps/api/test_artifacts/inventory/
- **Render**: https://dashboard.render.com/
- **Test Tokens**: test-jwts.json

---

## 📅 Timeline

| Time | Event | Status |
|------|-------|--------|
| 09:00 EST | PR #179 merged | ✅ DONE |
| 09:00 EST | Deployment started (6b9292f) | 🚀 IN PROGRESS |
| 09:05 EST | Deployment complete (expected) | ⏳ PENDING |
| 09:10 EST | Verification tests run (expected) | ⏳ PENDING |
| 09:15 EST | Deployment confirmed (expected) | ⏳ PENDING |

---

**Current Status**: 🚀 **DEPLOYMENT IN PROGRESS**
**Next Action**: Wait for deployment to complete (~5 min), then run verification tests
**Expected Result**: All 5 tests PASS ✅
