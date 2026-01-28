# Shopping List Lens v1 - Ops Deployment

**Date**: 2026-01-28
**Status**: ✅ Ops Files Generated, Ready for Deployment
**For**: Production monitoring and automated health checks

---

## What Was Generated

Applied the Lens Ops Template system to Shopping List Lens v1 for automated health monitoring and CI/CD testing.

### Files Created

1. **tools/ops/monitors/shopping_list_health_worker.py**
   - Automated health monitoring worker for Render
   - Checks every 15 minutes (configurable)
   - Writes to `pms_health_checks` table
   - Tests: service health, feature flags, action list endpoint
   - Emits structured logs for observability

2. **tests/ci/shopping_list_signed_flow_acceptance.py**
   - **NOTE**: Shopping List Lens has no SIGNED actions
   - All actions are MUTATE (approve/reject) or READ
   - This test file can be adapted or skipped
   - Generated as template placeholder for future SIGNED actions

3. **tests/stress/shopping_list_actions_endpoints.py**
   - Concurrent load testing (50 /list + 30 /execute)
   - Captures P50/P95/P99 latencies
   - Enforces 0×500 requirement
   - Status code breakdown (200/4xx/5xx)
   - Generates evidence artifacts

4. **.github/workflows/shopping_list-staging-acceptance.yml**
   - CI workflow for acceptance testing
   - Triggers on Shopping List code changes
   - Uploads evidence artifacts
   - **NOTE**: Adapt to skip signed flow test

5. **.github/workflows/shopping_list-stress.yml**
   - Nightly stress testing workflow
   - Runs at 2 AM UTC
   - Manual trigger available
   - Uploads stress test results

6. **docs/pipeline/SHOPPING_LIST_FEATURE_FLAGS.md**
   - Feature flag documentation
   - Toggle procedures (enable/disable)
   - Monitoring guidelines
   - Canary rollout steps

7. **supabase/migrations/20260128_ops_health_tables.sql**
   - Health monitoring database schema
   - Tables: `pms_health_checks`, `pms_health_events`
   - Helper functions: `get_latest_health_check`, `get_health_check_history`, `get_unhealthy_lenses`
   - RLS policies for yacht-scoped access

---

## Configuration

### Lens Parameters

```python
LENS_ID = "shopping_list"
DOMAIN = "shopping_list"
FEATURE_FLAGS = ["SHOPPING_LIST_LENS_V1_ENABLED"]
```

### Test Users

```python
YACHT_ID = "85fe1119-b04c-41ac-80f1-829d23322598" (yTEST_YACHT_001)
HOD_USER_ID = "05a488fd-e099-4d18-bf86-d87afba4fcdf" (hod.test@alex-short.com)
CREW_USER_ID = "57e82f78-0a2d-4a7c-a428-6287621d06c5" (crew.test@alex-short.com)
CAPTAIN_USER_ID = "c2f980b6-9a69-4953-bc33-3324f08602fe" (captain.test@alex-short.com)
```

### Roles

```
crew, deckhand, steward, engineer, eto, chief_engineer, chief_officer, purser, captain, manager
```

---

## Shopping List Lens Specifics

### Action Variants

**Shopping List has NO SIGNED actions.** All actions are:
- **MUTATE**: create_shopping_list_item, approve_shopping_list_item, reject_shopping_list_item, promote_candidate_to_part
- **READ**: view_shopping_list_item_history

This differs from other lenses (e.g., Faults Lens has `create_work_order_from_fault` as SIGNED).

### Implications for Testing

1. **Signed Flow Acceptance Test**: Can be adapted to test MUTATE actions instead
   - Test 1: CREW create → 200 OK
   - Test 2: CREW approve → 403 Forbidden
   - Test 3: HOD approve → 200 OK
   - Test 4: ENGINEER promote → 200 OK

2. **Health Worker**: Already configured correctly for MUTATE/READ actions

3. **Stress Test**: Works as-is (tests READ action `view_shopping_list_item_history`)

---

## Deployment Steps

### Step 1: Apply Database Migration ✅

```bash
# Migration file already copied to supabase/migrations/
cp docs/architecture/20_lens_ops/migrations/ops_health_tables.sql \
   supabase/migrations/20260128_ops_health_tables.sql

# Apply to staging/production
psql $STAGING_DB_URL < supabase/migrations/20260128_ops_health_tables.sql

# Verify tables created
psql $STAGING_DB_URL -c "\\dt pms_health*"
# Expected: pms_health_checks, pms_health_events
```

### Step 2: Review Generated Files ✅

All files generated successfully:
- ✅ Health worker configured for Shopping List
- ✅ Stress test ready for deployment
- ⚠️ Signed flow test needs adaptation (no SIGNED actions)
- ✅ CI workflows ready
- ✅ Feature flags documented

### Step 3: Deploy Health Worker to Render

Add to `render.yaml`:

```yaml
services:
  # Existing services...

  # NEW: Shopping List Health Worker
  - type: worker
    name: shopping-list-health-worker
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: python tools/ops/monitors/shopping_list_health_worker.py
    envVars:
      - key: HEALTH_CHECK_INTERVAL_MINUTES
        value: 15
      - key: API_BASE_URL
        value: https://pipeline-core.int.celeste7.ai
      - key: TENANT_SUPABASE_URL
        sync: false  # From existing env vars
      - key: TENANT_SUPABASE_JWT_SECRET
        sync: false
      - key: SUPABASE_SERVICE_KEY
        sync: false
      - key: RENDER_API_KEY
        value: rnd_8BakHjSO36rN90gAbQHgfqTnFjJY
      - key: RENDER_SERVICE_ID
        value: srv-d5fr5hre5dus73d3gdn0
```

Deploy:
```bash
git add render.yaml tools/ops/monitors/shopping_list_health_worker.py
git commit -m "Add Shopping List Health Worker for automated monitoring"
git push origin main
```

Verify:
```bash
# Check Render logs
# Expected: [FeatureFlags] SHOPPING_LIST_LENS_V1_ENABLED=True
# Expected: Starting health check for lens=shopping_list

# Check DB after 15 minutes
psql $STAGING_DB_URL -c "
  SELECT * FROM pms_health_checks
  WHERE lens_id = 'shopping_list'
  ORDER BY observed_at DESC LIMIT 1;
"
# Expected: status='healthy', error_rate_percent=0.00
```

### Step 4: Enable CI Workflows

```bash
git add .github/workflows/shopping_list-staging-acceptance.yml
git add .github/workflows/shopping_list-stress.yml
git add tests/ci/shopping_list_signed_flow_acceptance.py
git add tests/stress/shopping_list_actions_endpoints.py
git commit -m "Add CI workflows for Shopping List Lens monitoring"
git push origin main
```

Add GitHub Secrets:
- `STAGING_JWT_SECRET`
- `SUPABASE_SERVICE_KEY`
- `STAGING_DB_URL`

Trigger manually:
1. GitHub → Actions
2. Select "shopping_list - Stress Testing"
3. Run workflow

### Step 5: Adapt Signed Flow Test (Optional)

Since Shopping List has no SIGNED actions, adapt the acceptance test:

**Option A**: Skip signed flow test entirely
- Comment out or delete `shopping_list_signed_flow_acceptance.py`
- Update CI workflow to only run stress test

**Option B**: Adapt to test MUTATE role gating
- Replace SIGNED action tests with MUTATE tests
- Test CREW create (200) → HOD approve (200) → CREW approve (403)

**Option C**: Keep as placeholder for future SIGNED actions
- Leave file as-is
- Document that it's not currently used

### Step 6: Monitor for 7 Days

**Daily Checks**:

```sql
-- Latest health checks
SELECT
  observed_at,
  status,
  p95_latency_ms,
  error_rate_percent
FROM pms_health_checks
WHERE lens_id = 'shopping_list'
ORDER BY observed_at DESC
LIMIT 10;

-- Expected: status='healthy', error_rate=0.00%, one row every 15 min
```

**Check for Errors**:

```sql
-- Recent errors
SELECT
  he.created_at,
  he.level,
  he.detail_json
FROM pms_health_events he
JOIN pms_health_checks hc ON he.check_id = hc.id
WHERE hc.lens_id = 'shopping_list'
  AND he.level = 'error'
ORDER BY he.created_at DESC;

-- Expected: 0 rows (no errors)
```

**Render Worker Logs**:

```
Expected every 15 minutes:
[2026-01-28T15:00:00Z] INFO: Starting health check for lens=shopping_list
[2026-01-28T15:00:01Z] INFO: ✅ Service health: healthy
[2026-01-28T15:00:02Z] INFO: ✅ Feature flags: enabled
[2026-01-28T15:00:03Z] INFO: ✅ List endpoint: 200 OK (5 actions)
[2026-01-28T15:00:04Z] INFO: ✅ Wrote health check to DB
[2026-01-28T15:00:04Z] INFO: Sleeping for 15 minutes...
```

**CI Workflow Results**:

```
GitHub → Actions → "shopping_list - Stress Testing"
Expected: ✅ Green (0×500 across 80 requests)
Download artifacts → shopping_list-stress-results.md → verify P50/P95/P99
```

---

## Success Criteria

### Health Worker Running ✅

```
Render Dashboard → shopping-list-health-worker → Status: Running
Logs show: "✅ OVERALL: CANARY HEALTHY" every 15 minutes
```

### DB Writes Working ✅

```sql
SELECT COUNT(*) FROM pms_health_checks WHERE lens_id = 'shopping_list';
-- Should return > 0 (health checks being written)
```

### CI Workflows Green ✅

```
GitHub Actions → shopping_list-stress → ✅ Green (0×500)
Artifacts generated → shopping_list-stress-results.md
```

### 7-Day Monitoring Complete ✅

```sql
SELECT COUNT(*) FROM pms_health_checks
WHERE lens_id = 'shopping_list'
  AND status = 'healthy'
  AND observed_at >= now() - interval '7 days';
-- Should return ~672 rows (7 days × 24 hours × 4 checks/hour)
```

---

## Testing Philosophy (Canon)

All generated tests enforce CelesteOS testing doctrine:

### 1. Expected 4xx is Success (When Asserted)

**Cite**: `/Volumes/Backup/CELESTE/testing_success_ci:cd.md:799`

> "Role denial asserts 403 (crew mutations)"

```python
# CORRECT: Assert 403 for CREW
status, body = execute_action("approve_shopping_list_item", crew_jwt, payload)
assert status == 403, f"Expected 403, got {status}"  # ✅ PASS
assert body["error_code"] == "FORBIDDEN"
```

### 2. 500 is Always Failure

**Cite**: `/Volumes/Backup/CELESTE/testing_success_ci:cd.md:249`

> "500 indicates bug in contracts"

```python
# Stress test verdict
if status_5xx_count > 0:
    verdict = "FAIL"
    reason = f"{status_5xx_count}×500 errors detected"
else:
    verdict = "PASS"  # Only PASS if 0×500
```

### 3. Evidence Artifacts Required

**Cite**: `/Volumes/Backup/CELESTE/testing_success_ci:cd.md:815`

> "Evidence table types"

```python
# Capture full HTTP transcript
transcript = f"""
POST /v1/actions/execute HTTP/1.1
Authorization: Bearer {jwt[:20]}...

{json.dumps(payload, indent=2)}

HTTP/1.1 {status} {reason}

{json.dumps(body, indent=2)}
"""
evidence.append(transcript)
```

---

## Next Steps

### Immediate (This Sprint)

1. ✅ Apply DB migration
2. ✅ Generate ops files
3. ⏳ Review and adapt signed flow test
4. ⏳ Deploy health worker to Render
5. ⏳ Enable CI workflows
6. ⏳ Monitor for 7 days

### Future Enhancements

1. **Ops Dashboard Integration**
   - Query `pms_health_checks` table
   - Display lens health status UI
   - Alert on unhealthy status

2. **Additional Health Checks**
   - Test promote action endpoint
   - Check rejection reason validation
   - Verify state transitions

3. **Canary Rollout**
   - Enable `SHOPPING_LIST_LENS_V1_ENABLED` in staging
   - Monitor for 24h
   - Enable in production (10% → 50% → 100%)

---

## Files Reference

### Generated Files

| File | Purpose | Status |
|------|---------|--------|
| tools/ops/monitors/shopping_list_health_worker.py | Render worker | ✅ Ready |
| tests/ci/shopping_list_signed_flow_acceptance.py | Acceptance tests | ⚠️ Needs adaptation (no SIGNED) |
| tests/stress/shopping_list_actions_endpoints.py | Stress tests | ✅ Ready |
| .github/workflows/shopping_list-staging-acceptance.yml | CI workflow | ✅ Ready |
| .github/workflows/shopping_list-stress.yml | CI workflow | ✅ Ready |
| docs/pipeline/SHOPPING_LIST_FEATURE_FLAGS.md | Feature flags | ✅ Ready |
| supabase/migrations/20260128_ops_health_tables.sql | DB schema | ✅ Ready |

### Documentation

| File | Purpose |
|------|---------|
| docs/architecture/20_SHOPPING_LIST_LENS/SHOPPING_LIST_LENS_V1.md | Architecture |
| docs/architecture/20_SHOPPING_LIST_LENS/SHOPPING_LIST_LENS_V1_MICROACTION_CATALOG.md | Action catalog |
| docs/architecture/20_SHOPPING_LIST_LENS/SHOPPING_LIST_LENS_V1_FLOWCHARTS.md | Visual flows |
| docs/architecture/20_SHOPPING_LIST_LENS/SHOPPING_LIST_LENS_V1_ENGINEER_HANDOFF.md | Engineer handoff |
| docs/architecture/20_SHOPPING_LIST_LENS/SHOPPING_LIST_LENS_V1_OPS_DEPLOYMENT.md | This document |

---

## Summary

✅ **Ops deployment files generated successfully**
✅ **Health monitoring infrastructure ready**
✅ **CI/CD workflows configured**
⚠️ **Signed flow test needs adaptation (no SIGNED actions)**
⏳ **Ready for deployment to Render**

**Shopping List Lens v1 is ready for automated monitoring and health checks!**

---

**Document Created**: 2026-01-28
**Ops Deployment**: Ready ✅
**Shopping List Lens v1**: Production Monitoring Ready 🚀
