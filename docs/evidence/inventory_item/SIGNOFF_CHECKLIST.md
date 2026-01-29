# Inventory Lens v1.2 Sign-Off Checklist

**Date**: 2026-01-29
**Status**: Awaiting Manual Deployment + Schema Refresh
**Current Deployment**: 09cc644 (15 commits behind main)
**Target Deployment**: c215d04+ (includes all v1.2 fixes)

---

## ✅ Completed Tasks

### Phase 0-1: Code Development ✅
- [x] All Part Lens v2 handlers wired into internal_dispatcher
- [x] Exception handlers added to pipeline_service.py (commit 2a16dcb)
- [x] 404 error mapping fix (commit ee4cb10)
- [x] Instrumentation for RPC errors (commit 3d91c6c)
- [x] CI deployment polling and health checks (commit f792157)
- [x] All commits pushed to main and security/signoff branches

### Phase 8: Documentation ✅
- [x] schema_function_definitions.md created
- [x] 07_acceptance_results.md updated (baseline results)
- [x] RELEASE_NOTES_v1.2.md created
- [x] All evidence committed to repository

---

## ⏳ Pending Manual Tasks

### Phase 2: Trigger Render Deployment

**Issue**: Render deployment stuck at commit 09cc644 (15 commits behind main)

**Actions Required**:

1. **Trigger Manual Deployment**:
   - Navigate to: https://dashboard.render.com
   - Select service: **pipeline-core**
   - Click: **Manual Deploy** → **Deploy latest commit**
   - Select branch: **main** (commit c215d04)
   - Click: **Deploy**

2. **Monitor Deployment** (10-15 minutes):
   - Watch Render build logs for completion
   - Or use polling script:
     ```bash
     bash /private/tmp/claude/-Volumes-Backup-CELESTE/c98cc619-82ab-402f-91a6-c868af22a09a/scratchpad/poll_deployment.sh
     ```
   - Or manually check:
     ```bash
     curl -s https://pipeline-core.int.celeste7.ai/version | jq .
     ```

3. **Verify Deployment**:
   - [ ] `/version` shows git_commit = c215d04 (or later)
   - [ ] `/health` responds with status "healthy"
   - [ ] Timestamp confirms recent deployment

**Expected Git Commit**: `c215d04` (or later, includes ee4cb10 + additional fixes)

---

### Phase 3: Supabase TENANT Schema Refresh

**Database**: vzsohavtuotocgrfkfyd (TENANT)

**Actions Required**:

1. **Execute Schema Reload via SQL Editor**:
   - Navigate to: https://supabase.com/dashboard/project/vzsohavtuotocgrfkfyd
   - Go to: **SQL Editor** → **New Query**
   - Execute:
     ```sql
     -- Send schema reload notification to PostgREST
     SELECT pg_notify('pgrst', 'reload schema');
     ```
   - Expected result: `pg_notify` row with blank value

2. **Verify RPC Functions**:
   - Execute in SQL Editor:
     ```sql
     -- Verify add_stock_inventory
     SELECT pg_get_functiondef('public.add_stock_inventory(uuid, integer, uuid)'::regprocedure);

     -- Verify deduct_stock_inventory
     SELECT pg_get_functiondef('public.deduct_stock_inventory(uuid, integer, uuid)'::regprocedure);
     ```
   - [ ] Both functions show `RETURNS TABLE (success, quantity_before, quantity_after, error_code)`
   - [ ] Both functions use `RETURN NEXT;` (NOT `RETURN QUERY`)
   - [ ] Both functions use `SELECT ... FOR UPDATE` for row locking

3. **Restart Connection Pooler**:
   - Go to: **Database** → **Connection Pooling**
   - Click: **Restart Pooler** button
   - Wait: 2-3 minutes for pooler to fully restart
   - [ ] Pooler shows "Running" status

4. **Reload API Schema**:
   - Go to: **Database** → **API**
   - Click: **Reload Schema** button
   - Wait: 30 seconds
   - [ ] Schema reload completes successfully

**Why This Matters**: Ensures PostgREST picks up latest function definitions and clears any stale metadata cache.

---

### Phase 4: Manual API Sanity Check

**Prerequisites**:
- [ ] Render deployed to c215d04+
- [ ] Supabase schema refreshed

**Actions Required**:

1. **Get Fresh HOD JWT** (expires 2026-01-29 19:39 UTC):
   ```bash
   export HOD_JWT="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhdWQiOiJhdXRoZW50aWNhdGVkIiwiZXhwIjoxNzY5NzE1OTU1LCJzdWIiOiI4OWIxMjYyYy1mZjU5LTQ1OTEtYjk1NC03NTdjZGYzZDYwOWQiLCJlbWFpbCI6ImhvZC50ZW5hbnRAYWxleC1zaG9ydC5jb20iLCJwaG9uZSI6IiIsImFwcF9tZXRhZGF0YSI6eyJwcm92aWRlciI6ImVtYWlsIiwicHJvdmlkZXJzIjpbImVtYWlsIl19LCJ1c2VyX21ldGFkYXRhIjp7fSwicm9sZSI6ImF1dGhlbnRpY2F0ZWQiLCJhYWwiOiJhYWwxIiwiYW1yIjpbeyJtZXRob2QiOiJwYXNzd29yZCIsInRpbWVzdGFtcCI6MTc2OTYyOTU1NX1dLCJzZXNzaW9uX2lkIjoidGVzdC1zZXNzaW9uLTg5YjEyNjJjIiwiaXNfYW5vbnltb3VzIjpmYWxzZSwiaXNzIjoiaHR0cHM6Ly9xdnpta2FhbXphcXhwemJld2p4ZS5zdXBhYmFzZS5jby9hdXRoL3YxIiwiaWF0IjoxNzY5NjI5NTU1fQ.J1wlORRELXwoVYBbMtjunfBiPQSNDRFbRcfZMBjK5pI"
   ```

2. **Test receive_part (First Call)**:
   ```bash
   IDEMPOTENCY_KEY=$(uuidgen)

   curl -X POST https://pipeline-core.int.celeste7.ai/v1/actions/execute \
     -H "Authorization: Bearer $HOD_JWT" \
     -H "Content-Type: application/json" \
     -d "{
       \"action\": \"receive_part\",
       \"context\": {
         \"yacht_id\": \"85fe1119-b04c-41ac-80f1-829d23322598\"
       },
       \"payload\": {
         \"part_id\": \"00000000-0000-4000-8000-000000000003\",
         \"quantity\": 5,
         \"idempotency_key\": \"$IDEMPOTENCY_KEY\"
       }
     }" | jq .
   ```

   **Expected**:
   - [ ] Status: 200 OK
   - [ ] Response includes: `transaction_id`, `new_stock_level`
   - [ ] No PostgREST 204 errors
   - [ ] No 500 errors

3. **Test Idempotency (Duplicate Call)**:
   ```bash
   # Reissue with SAME idempotency_key
   curl -X POST https://pipeline-core.int.celeste7.ai/v1/actions/execute \
     -H "Authorization: Bearer $HOD_JWT" \
     -H "Content-Type: application/json" \
     -d "{
       \"action\": \"receive_part\",
       \"context\": {
         \"yacht_id\": \"85fe1119-b04c-41ac-80f1-829d23322598\"
       },
       \"payload\": {
         \"part_id\": \"00000000-0000-4000-8000-000000000003\",
         \"quantity\": 5,
         \"idempotency_key\": \"$IDEMPOTENCY_KEY\"
       }
     }" | jq .
   ```

   **Expected**:
   - [ ] Status: 409 Conflict
   - [ ] Error message: "Duplicate receive: idempotency_key ... already exists"

**Save Results**: Copy output to `docs/evidence/inventory_item/manual_sanity_check.txt`

---

### Phase 5: Final Acceptance Tests

**Prerequisites**:
- [ ] Render deployed to c215d04+
- [ ] Supabase schema refreshed
- [ ] Manual sanity check passed

**Actions Required**:

1. **Trigger GitHub Actions Workflow**:
   - Navigate to: https://github.com/shortalex12333/Cloud_PMS/actions/workflows/inventory-lens-api-acceptance.yml
   - Click: **Run workflow** → **Run workflow**
   - Branch: **main**

2. **Monitor Test Execution** (5-10 minutes):
   - Watch workflow progress
   - New CI features will:
     - Poll /version until git_commit matches current commit
     - Check /health endpoint before running tests
     - Generate fresh JWTs via password-grant

3. **Verify Test Results**:
   - [ ] **12/13 tests passing (92.3%)**
   - [ ] **1 test skipped** (integration workflow)
   - [ ] **0 tests failing**

   **Expected Passing Tests**:
   - ✅ test_crew_can_consume_part
   - ✅ test_crew_cannot_adjust_stock
   - ✅ test_captain_can_adjust_stock
   - ✅ test_hod_can_receive_part (PostgREST 204 RESOLVED)
   - ✅ test_duplicate_receive_blocked (PostgREST 204 RESOLVED)
   - ✅ test_consume_negative_quantity_rejected
   - ✅ test_transfer_same_location_rejected
   - ✅ test_missing_required_field_rejected
   - ✅ test_adjust_stock_without_signature_rejected
   - ✅ test_write_off_without_signature_rejected
   - ✅ test_insufficient_stock_returns_409
   - ✅ test_nonexistent_part_returns_404 (404 fix DEPLOYED)

   **Expected Skipped**:
   - ⏭️ test_full_workflow_receive_consume_transfer

4. **Download Test Artifacts**:
   - [ ] Download JUnit XML from workflow artifacts
   - [ ] Save to `docs/evidence/inventory_item/api_test_runs/junit_api_final_$(date +%Y%m%d_%H%M%S).xml`

5. **Capture Evidence**:
   ```bash
   # Capture /version
   curl -s https://pipeline-core.int.celeste7.ai/version | jq . > docs/evidence/inventory_item/version_final.json

   # Capture /health
   curl -s https://pipeline-core.int.celeste7.ai/health | jq . > docs/evidence/inventory_item/health_final.json
   ```

---

### Phase 6: Update Final Evidence

**Actions Required**:

1. **Update 07_acceptance_results.md**:
   - [ ] Add "Run 4 - Final Results (After c215d04 Deployment)" section
   - [ ] Document 12/13 passing (92.3%)
   - [ ] Include workflow run URL
   - [ ] Add timestamps for deployment and test run
   - [ ] Confirm PostgREST 204 fully resolved
   - [ ] Confirm 404 fix working

2. **Update RELEASE_NOTES_v1.2.md**:
   - [ ] Change status from "Production-Ready (pending deployment)" to "RELEASED"
   - [ ] Update test coverage to final 12/13 (92.3%)
   - [ ] Add final deployment timestamp
   - [ ] Add final test run evidence links

3. **Create Final Summary**:
   - [ ] Create `docs/evidence/inventory_item/FINAL_SIGNOFF.md`
   - [ ] Include: deployment commit, test results, manual checks, evidence files
   - [ ] Sign off with timestamp and "APPROVED FOR PRODUCTION"

4. **Commit Evidence**:
   ```bash
   git add docs/evidence/inventory_item/
   git commit -m "docs(inventory-lens): Final v1.2 sign-off evidence with 12/13 passing"
   git push origin main
   ```

---

## Phase 7: Release Tagging and Canary Deploy

### 7.1 Create Release Tag

**Prerequisites**: All Phase 1-6 tasks complete, 12/13 tests passing

**Actions Required**:

1. **Tag Release**:
   ```bash
   git checkout main
   git pull origin main
   git tag -a release/inventory-lens-v1.2 -m "Inventory Lens v1.2 - Production Release

   Features:
   - Complete dispatcher integration (10 Part Lens actions)
   - PostgREST 204 issue resolved
   - Atomic RPC operations with row-level locking
   - Error discipline: 400/403/404/409 (zero 500s for validation)
   - CI deployment polling and health checks
   - Comprehensive instrumentation

   Test Coverage: 12/13 passing (92.3%)
   Deployment: commit c215d04
   Evidence: docs/evidence/inventory_item/"

   git push origin release/inventory-lens-v1.2
   ```

2. **Create GitHub Release**:
   - Navigate to: https://github.com/shortalex12333/Cloud_PMS/releases/new
   - Tag: `release/inventory-lens-v1.2`
   - Title: **Inventory Lens v1.2 - Production Release**
   - Description: Copy from `RELEASE_NOTES_v1.2.md`
   - Attach: JUnit XML, version/health JSON captures
   - Click: **Publish release**

### 7.2 Branch Protection

**Actions Required**:

1. **Mark Acceptance as Required Check**:
   - Navigate to: https://github.com/shortalex12333/Cloud_PMS/settings/branches
   - Edit rule for: **main**
   - Under "Require status checks to pass":
     - [ ] Add: "Inventory Lens API Acceptance Results"
     - [ ] Add: "Contracts + Stress" (if available)
   - Click: **Save changes**

### 7.3 Canary Deploy Planning

**Canary Yacht Selection**:
- Select 1 yacht for initial rollout (24-hour monitoring)
- Recommend: Test yacht 85fe1119-b04c-41ac-80f1-829d23322598 (already seeded)

**Monitoring Checklist** (24 hours):
- [ ] Zero 500 errors in logs
- [ ] Correct role-based 403 responses
- [ ] Storage isolation policies enforced
- [ ] RPC functions returning data (no PostgREST 204)
- [ ] Idempotency working (duplicate operations return 409)
- [ ] Database drift check: `SELECT * FROM check_inventory_drift();` returns 0 rows

**Rollout Schedule**:
1. **Day 1**: 1 yacht (test yacht) - 24h monitoring
2. **Day 2**: 10% of yachts - 24h monitoring
3. **Day 3**: 50% of yachts - 24h monitoring
4. **Day 4**: 100% rollout

**Rollback Plan**:
- If issues detected: Revert to previous commit via Render manual deploy
- Database rollback: RPC functions are backwards-compatible (no schema changes)
- Communication: Notify affected yachts via email

---

## Phase 8: Post-Deploy Follow-Ups

### Short-term (Week 1)

1. **Monitor Production Logs**:
   - [ ] Check for any PostgREST 204 recurrences
   - [ ] Verify error rates match expectations
   - [ ] Monitor RPC call performance

2. **Seed Yacht_B Test Data**:
   - [ ] Create ticket: "Add Yacht_B test data for cross-yacht validation"
   - [ ] Seed second yacht with parts and stock
   - [ ] Enable cross-yacht test in acceptance suite

3. **Performance Baseline**:
   - [ ] Capture RPC call latency (p50, p95, p99)
   - [ ] Document baseline in `docs/evidence/inventory_item/performance_baseline.md`

### Medium-term (Month 1)

1. **Integration Workflow Test**:
   - [ ] Implement `test_full_workflow_receive_consume_transfer`
   - [ ] Test end-to-end: receive → consume → transfer → audit trail
   - [ ] Bring test coverage to 13/13 (100%)

2. **RPC Refactor (Optional)**:
   - [ ] Evaluate removing read-after-write fallback
   - [ ] Ensure all RPC functions consistently return rows
   - [ ] Simplify handler error handling

3. **Documentation**:
   - [ ] Update main README with Inventory Lens v1.2 status
   - [ ] Create user guide for Part Lens actions
   - [ ] Document idempotency key usage for frontend

---

## Current Status Summary

**Code Status**: ✅ Complete and committed
- All commits on main branch (c215d04)
- All documentation complete
- All instrumentation in place

**Deployment Status**: ⏳ Awaiting Manual Trigger
- Current: 09cc644 (15 commits behind)
- Target: c215d04 (includes all v1.2 fixes)
- Action: Manual Render deployment required

**Test Status**: ⏳ Awaiting Deployment
- Baseline: 10/13 passing (76.9%) - from commit 2d7a950
- Expected: 12/13 passing (92.3%) - after commit c215d04

**Schema Status**: ⏳ Awaiting Manual Refresh
- Functions verified correct in migration files
- Schema reload notification needed
- Pooler restart recommended

---

## Success Criteria

All of the following must be TRUE for sign-off:

- [ ] Render deployed to c215d04 or later
- [ ] Supabase schema refreshed and pooler restarted
- [ ] Manual sanity check: receive_part returns 200, duplicate returns 409
- [ ] Acceptance tests: 12/13 passing (92.3%), 1 skipped
- [ ] Zero PostgREST 204 errors in test run
- [ ] Zero 500 errors for validation failures (all 400/403/404/409)
- [ ] All evidence documented and committed
- [ ] Release tag created: release/inventory-lens-v1.2
- [ ] GitHub Release published with notes
- [ ] Branch protection updated with required checks

**Once all criteria met**: APPROVED FOR CANARY DEPLOY

---

**Checklist Created**: 2026-01-29 02:01 UTC
**Created By**: Claude Sonnet 4.5
**For Release**: Inventory Lens v1.2
