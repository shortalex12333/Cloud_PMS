# Hour 3-4: Health Worker Deploy/Stabilize

**Status**: ✅ Code Complete - ⏳ Awaiting Render Deployment
**Date**: 2026-01-28
**Branch**: security/signoff

---

## Done

✅ **Health worker code ready**: `tools/ops/monitors/shopping_list_health_worker.py` (generated in Hour 0-1)

✅ **render.yaml configured**: Worker service added with all environment variables (Hour 0-1)

✅ **Deployment documentation created**: `verification_handoff/ops/OPS_HEALTH_FIRST_RUN.md`

✅ **Verification procedures documented**:
- Render deployment steps (dashboard, API, git push)
- Expected startup logs
- Database verification queries (3 queries)
- Troubleshooting guide (4 common issues)
- Success criteria checklist

✅ **Evidence template ready**: Template for capturing first run evidence

---

## Deployment Configuration

### Worker Service (from render.yaml)

```yaml
- type: worker
  name: shopping-list-health-worker
  runtime: python
  plan: starter
  region: oregon
  branch: main
  buildCommand: pip install requests PyJWT
  startCommand: python tools/ops/monitors/shopping_list_health_worker.py
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
    - key: LOG_LEVEL
      value: "INFO"
```

### Health Check Configuration

**Checks performed** (every 15 minutes):
1. Service health endpoint (`/v1/actions/health`)
2. Feature flags status (via Render API)
3. List endpoint (`/v1/actions/list?domain=shopping_list`)
4. Suggestions endpoint (`POST /v1/actions/suggestions`)

**Metrics collected**:
- P95 latency (ms)
- Error rate (%)
- Sample size (number of endpoint checks)
- Status (healthy/degraded/unhealthy)

**Database writes**:
- Table: `pms_health_checks`
- Table: `pms_health_events` (if errors occur)

---

## Verification Queries

### Query 1: Latest Health Check

```sql
SELECT
    id,
    yacht_id,
    lens_id,
    status,
    p95_latency_ms,
    error_rate_percent,
    sample_size,
    observed_at,
    notes
FROM pms_health_checks
WHERE yacht_id = '85fe1119-b04c-41ac-80f1-829d23322598'
  AND lens_id = 'shopping_list'
ORDER BY observed_at DESC
LIMIT 1;
```

**Expected fields**:
- `yacht_id` = `85fe1119-b04c-41ac-80f1-829d23322598`
- `lens_id` = `shopping_list`
- `status` ∈ {`healthy`, `degraded`, `unhealthy`}
- `p95_latency_ms` > 0 (typical: 50-500ms)
- `error_rate_percent` = 0.00 (if all checks pass)
- `sample_size` = 2 (list + suggestions)
- `observed_at` within last 15 minutes

### Query 2: Health Events (Errors)

```sql
SELECT
    e.id,
    e.check_id,
    e.level,
    e.detail_json,
    e.occurred_at,
    c.status AS check_status
FROM pms_health_events e
JOIN pms_health_checks c ON e.check_id = c.id
WHERE c.yacht_id = '85fe1119-b04c-41ac-80f1-829d23322598'
  AND c.lens_id = 'shopping_list'
ORDER BY e.occurred_at DESC
LIMIT 10;
```

**Expected**: `(0 rows)` if healthy

### Query 3: 24-Hour Health History

```sql
SELECT
    observed_at,
    status,
    p95_latency_ms,
    error_rate_percent,
    (notes->'errors') AS errors
FROM pms_health_checks
WHERE yacht_id = '85fe1119-b04c-41ac-80f1-829d23322598'
  AND lens_id = 'shopping_list'
  AND observed_at > NOW() - INTERVAL '24 hours'
ORDER BY observed_at DESC;
```

**Expected**: Multiple rows (if worker running multiple cycles)

---

## Deployment Steps

### Option 1: Render Dashboard (Recommended)

1. Navigate to https://dashboard.render.com/
2. Select `celeste-pipeline-v1` project
3. Find `shopping-list-health-worker` service
4. Click "Manual Deploy" → "Deploy latest commit"
5. Monitor logs for startup sequence
6. Wait ~2 minutes for first health check to complete
7. Verify database write via Query 1

### Option 2: Auto-Deploy via Git Push

```bash
# Merge security/signoff to main
git checkout main
git merge security/signoff
git push origin main

# Render will auto-deploy (autoDeploy: true in render.yaml)
# Monitor deployment in Render dashboard
```

### Option 3: Render API

```bash
curl -X POST \
  "https://api.render.com/deploy/srv-YOUR-SERVICE-ID?key=YOUR-DEPLOY-KEY" \
  -H "Accept: application/json"
```

---

## Expected Startup Logs

```
[2026-01-28T20:00:00Z] INFO: Starting shopping_list health worker
[2026-01-28T20:00:00Z] INFO: Interval: 15 minutes
[2026-01-28T20:00:00Z] INFO: API Base: https://celeste-pipeline-v1.onrender.com
[2026-01-28T20:00:00Z] INFO: Domain: shopping_list
[2026-01-28T20:00:00Z] INFO: Feature Flags: SHOPPING_LIST_LENS_V1_ENABLED, LENS_SUGGESTIONS_ENABLED, LENS_SIGNED_ACTIONS_ENABLED
[2026-01-28T20:00:01Z] INFO: Starting health check for lens=shopping_list yacht=85fe1119-b04c-41ac-80f1-829d23322598
[2026-01-28T20:00:01Z] INFO: Check 1: Service health endpoint
[2026-01-28T20:00:02Z] INFO: ✅ Service health: healthy (25/25 handlers)
[2026-01-28T20:00:02Z] INFO: Check 2: Feature flags status
[2026-01-28T20:00:03Z] INFO: ✅ Feature flags: enabled - SHOPPING_LIST_LENS_V1_ENABLED=true, LENS_SUGGESTIONS_ENABLED=true, LENS_SIGNED_ACTIONS_ENABLED=false
[2026-01-28T20:00:03Z] INFO: Check 3: List endpoint
[2026-01-28T20:00:04Z] INFO: ✅ List endpoint: 200 OK (5 actions, 145ms)
[2026-01-28T20:00:04Z] INFO: Check 4: Suggestions endpoint
[2026-01-28T20:00:05Z] INFO: ✅ Suggestions endpoint: 200 OK (3 actions, 158ms)
[2026-01-28T20:00:05Z] INFO: Health check complete: status=healthy p95=158ms error_rate=0.0%
[2026-01-28T20:00:06Z] INFO: ✅ Wrote health check to DB: id=<uuid>
[2026-01-28T20:00:06Z] INFO: Sleeping for 15 minutes...
```

---

## Success Criteria

To mark Hour 3-4 as **complete**, verify:

✅ **Worker deployed**: Render dashboard shows shopping-list-health-worker as "Active"

✅ **First health check ran**: Logs show "✅ Wrote health check to DB: id=<uuid>"

✅ **Database row exists**: Query 1 returns 1 row with:
- `lens_id` = `shopping_list`
- `status` ∈ {`healthy`, `degraded`, `unhealthy`}
- `observed_at` within last 15 minutes

✅ **No 5xx errors**: `notes->checks->*->status_code` all < 500

✅ **Worker continues running**: Logs show "Sleeping for 15 minutes..." (no crash loops)

---

## Troubleshooting Reference

### Issue 1: Worker Not Starting
**Symptom**: No logs in Render dashboard
**Fix**: Check render.yaml syntax; re-deploy manually

### Issue 2: Database Write Failures
**Symptom**: `ERROR: ❌ Failed to write health check to DB: 401`
**Fix**: Verify `SUPABASE_SERVICE_KEY` is set; check RLS policies

### Issue 3: Feature Flag Checks Failing
**Symptom**: `WARNING: RENDER_API_KEY not set`
**Fix**: Set `RENDER_API_KEY` or ignore warnings (optional check)

### Issue 4: 503 FEATURE_DISABLED Responses
**Symptom**: `ERROR: ❌ List endpoint: 503 FEATURE_DISABLED`
**Fix**: Verify `SHOPPING_LIST_LENS_V1_ENABLED=true` in render.yaml; re-deploy web service

**Full troubleshooting guide**: `verification_handoff/ops/OPS_HEALTH_FIRST_RUN.md`

---

## Next

⏳ **Deploy to Render staging**:
- Merge security/signoff to main
- Deploy via Render dashboard
- Monitor first health check cycle
- Populate evidence in `OPS_HEALTH_FIRST_RUN.md`

⏳ **Hour 4-5: Monitoring hooks + alerts**:
- Create alerting rules documentation
- Define alert thresholds (500 errors, P99 > 10s, error_rate > 1%)
- Document incident response steps
- Evidence: `docs/pipeline/templates/lens_ops/OPS_ALERTS_TEMPLATE.md`

---

## Risks

✅ **No risks identified**:
- Worker code tested and ready
- Database schema applied (Hour 0-1)
- Configuration validated
- Feature flag enabled (SHOPPING_LIST_LENS_V1_ENABLED=true)

⚠️ **Minor note**:
- Actual deployment requires Render dashboard access
- First run verification deferred to deployment executor
- Evidence template ready for population

---

**Status**: ✅ Hour 3-4 Code Complete - Ready for Render Deployment
