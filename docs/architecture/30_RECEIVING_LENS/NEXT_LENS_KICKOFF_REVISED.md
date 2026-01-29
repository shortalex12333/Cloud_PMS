# Receiving Lens v1 - Canary Deployment Plan (REVISED)

**Lens ID**: `receiving`
**Domain**: `receiving`
**Priority**: #2 (after Shopping List canary stabilization)
**Status**: ✅ IMPLEMENTATION COMPLETE - Ready for Canary Prep
**Date**: 2026-01-29

**REVISION NOTICE**: Original kickoff planned Zero→Gold implementation (5-6 days). **Receiving Lens v1 is already 100% implemented.** This revised plan focuses on canary deployment only (2-3 days).

---

## Discovery: Implementation Already Complete

### What Exists (100% Complete)

**10 Actions** (vs. 5 planned):
1. ✅ create_receiving (MUTATE)
2. ✅ attach_receiving_image_with_comment (MUTATE)
3. ✅ extract_receiving_candidates (PREPARE - advisory OCR)
4. ✅ update_receiving_fields (MUTATE)
5. ✅ add_receiving_item (MUTATE)
6. ✅ adjust_receiving_item (MUTATE)
7. ✅ link_invoice_document (MUTATE)
8. ✅ accept_receiving (SIGNED - prepare/execute)
9. ✅ reject_receiving (MUTATE)
10. ✅ view_receiving_history (READ)

**Database Schema** (4 tables):
- ✅ pms_receiving (header)
- ✅ pms_receiving_items (line items)
- ✅ pms_receiving_documents (attachments)
- ✅ pms_receiving_extractions (OCR results)

**RLS Policies**: ✅ 16 policies (4 tables × 4 operations)
**Storage**: ✅ 2 buckets (pms-receiving-images, documents)
**Integration**: ✅ Shopping List, Inventory, Work Orders
**Testing**: ✅ Acceptance + stress tests passing
**Documentation**: ✅ receiving_lens_v1_FINAL.md (comprehensive)

**File**: `/apps/api/handlers/receiving_handlers.py` (1,254 lines)

---

## Revised Timeline: Canary Prep Only

**Original Estimate**: 5-6 days (35-45 hours) for Zero→Gold
**Revised Estimate**: 2-3 days (16-20 hours) for canary prep only

**Phases**: 6 instead of 10 (no implementation needed)

---

## Phase 1: Feature Flags (4 hours)

### Tasks

1. **Add Flag to Code** (`apps/api/integrations/feature_flags.py`):
   ```python
   # RECEIVING LENS V1 FLAGS (default: OFF - fail-closed)
   RECEIVING_LENS_V1_ENABLED = os.getenv('RECEIVING_LENS_V1_ENABLED', 'false').lower() == 'true'

   logger.info(f"[FeatureFlags] RECEIVING_LENS_V1_ENABLED={RECEIVING_LENS_V1_ENABLED}")

   def check_receiving_lens_feature() -> tuple[bool, str]:
       """Check if Receiving Lens v1 is enabled."""
       if not RECEIVING_LENS_V1_ENABLED:
           return False, "Receiving Lens v1 is disabled (canary flag off)"
       return True, ""
   ```

2. **Update Handler Entry Points** (add check to first line of each handler):
   ```python
   def create_receiving(payload, user_jwt):
       # Check feature flag
       enabled, error_msg = check_receiving_lens_feature()
       if not enabled:
           return 503, {"error_code": "feature_disabled", "message": error_msg}

       # ... existing handler code ...
   ```

3. **Update render.yaml** (canary service only):
   ```yaml
   envVars:
     - key: RECEIVING_LENS_V1_ENABLED
       value: "true"  # OFF by default, ON for canary
   ```

4. **Test Flag Toggle**:
   - Flag OFF: `/v1/receiving/*` → 503 FEATURE_DISABLED
   - Flag ON: `/v1/receiving/*` → 200/403 based on role

### Deliverables

- [ ] Feature flag added to code (default: false)
- [ ] Handler checks integrated
- [ ] render.yaml updated (canary: true)
- [ ] Toggle tested (503 when OFF, 200 when ON)
- [ ] Docs: `docs/pipeline/RECEIVING_FEATURE_FLAGS.md`

---

## Phase 2: Ops Health Worker (4 hours)

### Tasks

1. **Create Health Worker** (`tools/ops/monitors/receiving_health_worker.py`):
   - Copy template from shopping_list_health_worker.py
   - Configure:
     ```python
     LENS_ID = "receiving"
     DOMAIN = "receiving"
     FEATURE_FLAGS = [
         "RECEIVING_LENS_V1_ENABLED",
         "LENS_SUGGESTIONS_ENABLED",
         "LENS_SIGNED_ACTIONS_ENABLED",
     ]
     ```

2. **Add to render.yaml**:
   ```yaml
   - type: worker
     name: receiving-health-worker
     runtime: python
     plan: starter
     region: oregon
     branch: main
     buildCommand: pip install requests PyJWT
     startCommand: python tools/ops/monitors/receiving_health_worker.py
     autoDeploy: true
     envVars:
       - key: HEALTH_CHECK_INTERVAL_MINUTES
         value: "15"
       - key: API_BASE_URL
         value: "https://celeste-pipeline-v1.onrender.com"
       - key: TENANT_SUPABASE_URL
         value: "https://vzsohavtuotocgrfkfyd.supabase.co"
       - key: SUPABASE_SERVICE_KEY
         sync: false
       - key: TENANT_SUPABASE_JWT_SECRET
         sync: false
       - key: TEST_YACHT_ID
         value: "85fe1119-b04c-41ac-80f1-829d23322598"
       - key: TEST_HOD_USER_ID
         value: "05a488fd-e099-4d18-bf86-d87afba4fcdf"
       - key: TEST_HOD_EMAIL
         value: "hod.test@alex-short.com"
   ```

3. **Health Checks** (4 checks):
   - Service health (`/v1/actions/health`)
   - Feature flags (via Render API)
   - List endpoint (`/v1/actions/list?domain=receiving`)
   - Suggestions endpoint (`POST /v1/actions/suggestions`)

4. **Verify First Run**:
   ```sql
   SELECT * FROM pms_health_checks
   WHERE lens_id = 'receiving'
     AND yacht_id = '85fe1119-b04c-41ac-80f1-829d23322598'
   ORDER BY observed_at DESC
   LIMIT 1;
   ```

### Deliverables

- [ ] Health worker created
- [ ] Added to render.yaml
- [ ] Worker deployed to Render
- [ ] First health check row verified in DB
- [ ] Docs: `verification_handoff/ops/RECEIVING_HEALTH_FIRST_RUN.md`

---

## Phase 3: Monitoring Alerts (3 hours)

### Tasks

1. **Create Alerts Document** (`docs/pipeline/receiving_lens/OPS_ALERTS.md`):
   - Copy template: `docs/pipeline/templates/lens_ops/OPS_ALERTS_TEMPLATE.md`
   - Customize for Receiving Lens (10 actions, SIGNED variant)

2. **Define 6 Alerts**:
   - **CRITICAL**: 5xx error detected (0×500 violation)
   - **CRITICAL**: Consecutive unhealthy status (2+ checks)
   - **CRITICAL**: Worker crash loop (>3 restarts/hour)
   - **WARNING**: P95 latency > 10s (2 checks)
   - **WARNING**: Error rate > 1% (2 checks)
   - **INFO**: Feature flag toggle detected

3. **Incident Runbooks** (3 scenarios):
   - 5xx error on list endpoint (rollback procedure)
   - Feature flag disabled unexpectedly (re-enable procedure)
   - P95 latency spike (slow query investigation)

4. **Monitoring Dashboard Queries** (3 queries):
   - 7-day health trend
   - Latest errors
   - Uptime percentage (last 30 days)

### Deliverables

- [ ] Alerts document created
- [ ] 6 alerts defined with SQL queries
- [ ] 3 incident runbooks documented
- [ ] 3 monitoring dashboard queries ready
- [ ] Docs: `docs/pipeline/receiving_lens/OPS_ALERTS.md`

---

## Phase 4: Smoke Tests (3 hours)

### Tasks

1. **Create Smoke Test** (`tests/smoke/receiving_canary_smoke.py`):
   - Copy template from shopping_list_canary_smoke.py
   - Adapt for Receiving Lens actions

2. **Test Coverage** (10 tests):
   - Health endpoint → 200 OK
   - CREW create → 403 Forbidden (expected)
   - HOD create → 200 OK
   - HOD attach image → 200 OK
   - HOD add item → 200 OK
   - HOD update fields → 200 OK
   - ENGINEER accept (PREPARE) → 200 OK with confirmation_token
   - ENGINEER accept (EXECUTE without signature) → 400 signature_required
   - ENGINEER accept (EXECUTE with signature) → 200 OK
   - View history → 200 OK

3. **Evidence Output**:
   - Full HTTP transcripts
   - Status code verification
   - 0×500 requirement check
   - File: `verification_handoff/canary/RECEIVING_CANARY_SMOKE.md`

4. **Run Test**:
   ```bash
   export TENANT_SUPABASE_JWT_SECRET="..."
   python3 tests/smoke/receiving_canary_smoke.py
   ```

### Deliverables

- [ ] Smoke test script created (10 tests)
- [ ] Evidence output configured
- [ ] Test executed successfully
- [ ] Results appended to PHASE5_STAGING_CANARY_SUMMARY.md
- [ ] File: `tests/smoke/receiving_canary_smoke.py`

---

## Phase 5: CI/CD Workflows (2 hours)

### Tasks

1. **Staging Acceptance Workflow** (`.github/workflows/receiving-staging-acceptance.yml`):
   - Trigger: On push to receiving-related files
   - Runs: Acceptance tests against staging
   - Uploads: Evidence artifacts
   - Enforces: 0×500 requirement

2. **Nightly Stress Workflow** (`.github/workflows/receiving-stress.yml`):
   - Schedule: Nightly at 2 AM UTC
   - Tests: 50× /list + 30× /execute (create_receiving)
   - Reports: P50/P95/P99 latencies
   - Enforces: 0×500 requirement

3. **Add to Required Checks**:
   - GitHub branch protection rules
   - Require status checks to pass

### Deliverables

- [ ] Staging acceptance workflow created
- [ ] Nightly stress workflow created
- [ ] Workflows added to required checks
- [ ] Files: `.github/workflows/receiving-*.yml`

---

## Phase 6: 24h Canary Monitoring (24 hours)

### Tasks

1. **Enable Canary Flag** (Staging):
   ```yaml
   # render.yaml
   - key: RECEIVING_LENS_V1_ENABLED
     value: "true"
   ```

2. **Deploy to Staging**:
   - Merge feature branch to main
   - Deploy via Render dashboard
   - Verify deployment (green checkmark)

3. **Run Smoke Tests**:
   - Execute all 10 tests
   - Verify 10/10 passing
   - Capture evidence

4. **Monitor Health Checks** (every 15 minutes for 24 hours):
   ```sql
   SELECT observed_at, status, p95_latency_ms, error_rate_percent
   FROM pms_health_checks
   WHERE lens_id = 'receiving'
     AND yacht_id = '85fe1119-b04c-41ac-80f1-829d23322598'
     AND observed_at > NOW() - INTERVAL '24 hours'
   ORDER BY observed_at DESC;
   ```

5. **Alert Thresholds**:
   - 🚨 CRITICAL: Any 5xx error (immediate rollback)
   - ⚠️ WARNING: P99 > 10s for 2 consecutive checks
   - ⚠️ WARNING: Error rate > 1% for 2 consecutive checks

6. **Consolidate Evidence**:
   - Create: `docs/pipeline/receiving_lens/PHASE5_STAGING_CANARY_SUMMARY.md`
   - Include: Flags ON proof, smoke transcripts, health check results

### Deliverables

- [ ] Flag enabled in staging
- [ ] Smoke tests passed (10/10)
- [ ] 24h monitoring complete
- [ ] Success criteria met:
  - ✅ 0×500 requirement (zero 5xx errors)
  - ✅ P99 < 10s
  - ✅ Error rate < 1%
  - ✅ Uptime > 99.5%
- [ ] Evidence: PHASE5_STAGING_CANARY_SUMMARY.md

---

## Integration with Shopping List Lens

### Data Flow

**Request → Order → Receive Loop**:
1. Shopping List: `create_shopping_list_item` (CREW)
2. Shopping List: `approve_shopping_list_item` (HOD)
3. **External**: Create PO from approved items
4. **Receiving**: `create_receiving` (HOD) - link to PO
5. **Receiving**: `add_receiving_item` (HOD) - add line items
6. **Receiving**: `accept_receiving` (ENGINEER - SIGNED) - finalize
7. **Inventory**: Update stock levels (future enhancement)

### Reverse Flow (Discrepancy → Shopping List)

**Receiving Discrepancy → Shopping List Request**:
1. Receiving: Item missing/damaged
2. Shopping List: `create_shopping_list_item` (source_receiving_id set)
   - Source type: `receiving_missing` or `receiving_damaged`
   - Source notes: Details from receiving
3. Shopping List: Approve → Order → New receiving created

### Database Linkages

**Shopping List → Receiving**:
- `pms_shopping_list_items.source_receiving_id` → `pms_receiving.id`
- Source types: receiving_missing, receiving_damaged

**Receiving → Parts**:
- `pms_receiving_items.part_id` → `pms_parts.id`

**Receiving → Work Orders**:
- `pms_receiving.linked_work_order_id` → `pms_work_orders.id`

---

## Success Criteria

- [ ] Feature flag working (OFF → 503, ON → 200)
- [ ] Health worker writing to DB every 15 minutes
- [ ] 10/10 smoke tests passing
- [ ] 24h canary stable:
  - 0×500 requirement met (zero 5xx errors)
  - P99 latency < 10s
  - Error rate < 1%
  - Uptime > 99.5%
- [ ] Alerts defined and documented
- [ ] CI/CD workflows configured
- [ ] Evidence consolidated

---

## Comparison: Original vs. Revised Plan

| Phase | Original Plan | Revised Plan | Time Saved |
|-------|---------------|--------------|------------|
| 0 | Spec & DB Truth (2-3 hours) | ❌ N/A (already done) | 3 hours |
| 1 | Registry & Suggestions (3-4 hours) | ❌ N/A (already done) | 4 hours |
| 2 | Handlers & Execute (6-8 hours) | ❌ N/A (already done) | 8 hours |
| 3 | RLS & Storage (4-5 hours) | ❌ N/A (already done) | 5 hours |
| 4 | Docker RLS Tests (4-6 hours) | ❌ N/A (already done) | 6 hours |
| 5 | Staging Acceptance (3-4 hours) | ❌ N/A (already done) | 4 hours |
| 6 | Stress Tests (2-3 hours) | ❌ N/A (already done) | 3 hours |
| 7 | Feature Flags + Docs (2 hours) | ✅ Phase 1 (4 hours) | -2 hours |
| 8 | Ops Health (2-3 hours) | ✅ Phase 2 (4 hours) | -2 hours |
| 9 | Canary Rollout (24 hours) | ✅ Phases 3-6 (32 hours) | -8 hours |
| 10 | Final Sign-Off (3-4 hours) | ❌ N/A (evidence only) | 4 hours |

**Total Original**: 35-45 hours (5-6 days)
**Total Revised**: 16-20 hours (2-3 days)
**Time Saved**: 19-25 hours (3 days)

---

## Risk Mitigation

**Risk 1: OCR Integration Missing**
- Status: Extract action returns mock data (TODO: integrate real OCR)
- Impact: Canary deployment NOT blocked (OCR is advisory only)
- Mitigation: Document as future enhancement

**Risk 2: Inventory Auto-Update Missing**
- Status: Not implemented in v1 (manual reconciliation)
- Impact: Canary deployment NOT blocked (not critical for canary)
- Mitigation: Document as future enhancement

**Risk 3: Tax Calculation Missing**
- Status: Subtotal/tax/total fields exist but calculation is manual
- Impact: Canary deployment NOT blocked (users can enter manually)
- Mitigation: Document as future enhancement

---

## Next Steps

1. ✅ Document implementation status (RECEIVING_LENS_V1_STATUS.md)
2. ⏳ Wait for Shopping List canary to stabilize (7 days)
3. ⏳ Begin Receiving canary prep (2-3 days, this plan)
4. ⏳ Deploy Receiving canary (7 days monitoring)
5. ⏳ Gradual rollout (10% → 50% → 100%)

---

## References

**Implementation**: `/apps/api/handlers/receiving_handlers.py`
**Documentation**: `/docs/pipeline/entity_lenses/receiving_lens/v1/receiving_lens_v1_FINAL.md`
**Status**: `/docs/architecture/30_RECEIVING_LENS/RECEIVING_LENS_V1_STATUS.md`
**Migrations**: `/supabase/migrations/20260128_10*_receiving_*.sql`
**Tests**: `/apps/api/tests/test_receiving_lens_v1_acceptance.py`

---

**Last Updated**: 2026-01-29 02:45 UTC
**Status**: Ready for Canary Prep (after Shopping List stabilizes)
**Priority**: #2 (next lens after Shopping List)
