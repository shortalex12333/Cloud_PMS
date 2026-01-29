# Shopping List Health Worker - First Run Verification

**Status**: ⏳ Awaiting Deployment
**Date**: 2026-01-28
**Worker**: shopping-list-health-worker
**Lens**: shopping_list

---

## Deployment Checklist

### 1. Verify render.yaml Configuration

✅ **Worker service added** (completed in Hour 0-1):
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
```

✅ **Environment variables configured**:
- `HEALTH_CHECK_INTERVAL_MINUTES=15`
- `API_BASE_URL=https://celeste-pipeline-v1.onrender.com`
- `TENANT_SUPABASE_URL=https://vzsohavtuotocgrfkfyd.supabase.co`
- `SUPABASE_SERVICE_KEY` (synced from secrets)
- `TENANT_SUPABASE_JWT_SECRET` (synced from secrets)
- `TEST_YACHT_ID=85fe1119-b04c-41ac-80f1-829d23322598`
- `TEST_HOD_USER_ID=05a488fd-e099-4d18-bf86-d87afba4fcdf`
- `TEST_HOD_EMAIL=hod.test@alex-short.com`
- `LOG_LEVEL=INFO`

### 2. Deploy to Render

**Option A: Via Render Dashboard**
1. Navigate to https://dashboard.render.com/
2. Select `celeste-pipeline-v1` project
3. Go to "Environment" tab
4. Click "Manual Deploy" → "Deploy latest commit"
5. Wait for deployment to complete (green checkmark)

**Option B: Via Render API**
```bash
curl -X POST \
  "https://api.render.com/deploy/srv-YOUR-SERVICE-ID?key=YOUR-DEPLOY-KEY" \
  -H "Accept: application/json"
```

**Option C: Via Git Push**
```bash
# Changes already in security/signoff branch
# Merge to main when ready:
git checkout main
git merge security/signoff
git push origin main
# Render will auto-deploy (autoDeploy: true)
```

### 3. Verify Worker Started

Check Render dashboard → shopping-list-health-worker → Logs:

**Expected startup logs**:
```
[2026-01-28T...] INFO: Starting shopping_list health worker
[2026-01-28T...] INFO: Interval: 15 minutes
[2026-01-28T...] INFO: API Base: https://celeste-pipeline-v1.onrender.com
[2026-01-28T...] INFO: Domain: shopping_list
[2026-01-28T...] INFO: Feature Flags: SHOPPING_LIST_LENS_V1_ENABLED, LENS_SUGGESTIONS_ENABLED, LENS_SIGNED_ACTIONS_ENABLED
[2026-01-28T...] INFO: Starting health check for lens=shopping_list yacht=85fe1119-b04c-41ac-80f1-829d23322598
[2026-01-28T...] INFO: Check 1: Service health endpoint
[2026-01-28T...] INFO: ✅ Service health: healthy (XX/YY handlers)
[2026-01-28T...] INFO: Check 2: Feature flags status
[2026-01-28T...] INFO: ✅ Feature flags: enabled - SHOPPING_LIST_LENS_V1_ENABLED=true, ...
[2026-01-28T...] INFO: Check 3: List endpoint
[2026-01-28T...] INFO: ✅ List endpoint: 200 OK (5 actions, XXms)
[2026-01-28T...] INFO: Check 4: Suggestions endpoint
[2026-01-28T...] INFO: ✅ Suggestions endpoint: 200 OK (3 actions, XXms)
[2026-01-28T...] INFO: Health check complete: status=healthy p95=XXms error_rate=0.0%
[2026-01-28T...] INFO: ✅ Wrote health check to DB: id=<uuid>
[2026-01-28T...] INFO: Sleeping for 15 minutes...
```

**Error scenarios**:
```
# Scenario 1: Feature flags disabled
[2026-01-28T...] ERROR: ❌ List endpoint: 503 FEATURE_DISABLED
[2026-01-28T...] INFO: Health check complete: status=unhealthy p95=XXms error_rate=50.0%

# Scenario 2: Service unhealthy
[2026-01-28T...] WARNING: Service health: degraded
[2026-01-28T...] INFO: Health check complete: status=degraded p95=XXms error_rate=0.0%

# Scenario 3: Database write failure
[2026-01-28T...] ERROR: ❌ Failed to write health check to DB: 401 - ...
```

---

## Verify Database Writes

### Query 1: Check Latest Health Check

```sql
-- Run in Supabase SQL Editor (https://vzsohavtuotocgrfkfyd.supabase.co)
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

**Expected result** (first successful run):
```
| id                                   | yacht_id                             | lens_id        | status  | p95_latency_ms | error_rate_percent | sample_size | observed_at              | notes                                    |
|--------------------------------------|--------------------------------------|----------------|---------|----------------|-------------------|-------------|--------------------------|------------------------------------------|
| <uuid>                               | 85fe1119-b04c-41ac-80f1-829d23322598 | shopping_list  | healthy | 150            | 0.00              | 2           | 2026-01-28T20:15:00Z     | {"checks": {...}, "errors": []}         |
```

**Field validation**:
- ✅ `yacht_id` = `85fe1119-b04c-41ac-80f1-829d23322598` (canary yacht)
- ✅ `lens_id` = `shopping_list`
- ✅ `status` ∈ {`healthy`, `degraded`, `unhealthy`}
- ✅ `p95_latency_ms` > 0 (typical range: 50-500ms)
- ✅ `error_rate_percent` = 0.00 (if all checks pass)
- ✅ `sample_size` = 2 (list + suggestions endpoints)
- ✅ `observed_at` within last 15 minutes
- ✅ `notes` contains `checks` and `errors` arrays

### Query 2: Check Health Events

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

**Expected result** (if healthy):
```
(0 rows)
```

**Expected result** (if degraded/unhealthy):
```
| id     | check_id | level | detail_json                                      | occurred_at          | check_status |
|--------|----------|-------|--------------------------------------------------|----------------------|--------------|
| <uuid> | <uuid>   | error | {"message": "List endpoint: 503 FEATURE_DISABLED"} | 2026-01-28T20:15:00Z | unhealthy    |
```

### Query 3: Check Health History (Last 24 Hours)

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

**Expected pattern** (if worker running for multiple cycles):
```
| observed_at          | status  | p95_latency_ms | error_rate_percent | errors |
|----------------------|---------|----------------|-------------------|--------|
| 2026-01-28T21:00:00Z | healthy | 140            | 0.00              | []     |
| 2026-01-28T20:45:00Z | healthy | 155            | 0.00              | []     |
| 2026-01-28T20:30:00Z | healthy | 148            | 0.00              | []     |
| 2026-01-28T20:15:00Z | healthy | 150            | 0.00              | []     |
```

---

## Verification Evidence Template

**Populate this section after first successful run:**

### Evidence Capture

**Date/Time of First Run**: `____________________`

**Worker Logs** (copy from Render dashboard):
```
[Paste startup logs + first health check cycle here]
```

**Database Query Results**:

```sql
-- Query 1: Latest health check
[Paste query result here]

-- Query 2: Health events (if any)
[Paste query result here]

-- Query 3: Health history
[Paste query result here]
```

**Health Check JSON** (from `notes` column):
```json
{
  "checks": {
    "service_health": {
      "status": "healthy",
      "data": {
        "status": "healthy",
        "handlers_loaded": 25,
        "total_handlers": 25
      }
    },
    "feature_flags": {
      "status": "enabled",
      "flags": {
        "SHOPPING_LIST_LENS_V1_ENABLED": "true",
        "LENS_SUGGESTIONS_ENABLED": "true",
        "LENS_SIGNED_ACTIONS_ENABLED": "false"
      }
    },
    "list_endpoint": {
      "status_code": 200,
      "latency_ms": 145,
      "action_count": 5
    },
    "suggestions_endpoint": {
      "status_code": 200,
      "latency_ms": 158,
      "action_count": 3
    }
  },
  "errors": []
}
```

### Validation Checklist

After capturing evidence, verify:

- ✅ Worker logs show `INFO: Starting shopping_list health worker`
- ✅ Worker logs show `INFO: ✅ Wrote health check to DB: id=<uuid>`
- ✅ Database row exists in `pms_health_checks` with `lens_id='shopping_list'`
- ✅ `status` field is `healthy` (or `degraded`/`unhealthy` with documented reason)
- ✅ `p95_latency_ms` is reasonable (<1000ms)
- ✅ `error_rate_percent` is 0.00 (if all checks pass)
- ✅ `sample_size` = 2
- ✅ `observed_at` is recent (within last 15 minutes)
- ✅ `notes->checks->service_health->status` = `healthy`
- ✅ `notes->checks->feature_flags->status` = `enabled`
- ✅ `notes->checks->list_endpoint->status_code` = 200
- ✅ `notes->checks->suggestions_endpoint->status_code` = 200
- ✅ `notes->errors` = [] (empty array)
- ✅ Worker continues running (check logs for "Sleeping for 15 minutes...")

---

## Troubleshooting

### Issue 1: Worker Not Starting

**Symptoms**:
- No logs in Render dashboard
- Worker status: "Not Deployed"

**Fix**:
```bash
# Check render.yaml syntax
python3 -c "import yaml; yaml.safe_load(open('render.yaml'))"

# Re-deploy manually via Render dashboard
# Or push to main branch to trigger auto-deploy
```

### Issue 2: Database Write Failures

**Symptoms**:
```
ERROR: ❌ Failed to write health check to DB: 401 - ...
```

**Fix**:
1. Verify `SUPABASE_SERVICE_KEY` is set correctly in Render environment
2. Check RLS policies allow service_role to INSERT:
   ```sql
   SELECT * FROM pg_policies WHERE tablename = 'pms_health_checks';
   -- Should have policy: service_role_write_health_checks
   ```
3. Test direct insert via Supabase dashboard:
   ```sql
   INSERT INTO pms_health_checks (yacht_id, lens_id, status, observed_at)
   VALUES ('85fe1119-b04c-41ac-80f1-829d23322598', 'shopping_list', 'healthy', NOW())
   RETURNING id;
   ```

### Issue 3: Feature Flag Checks Failing

**Symptoms**:
```
WARNING: RENDER_API_KEY not set - feature flag checks will fail
ERROR: Feature flags: unknown - {"error": "exception", ...}
```

**Fix**:
1. Set `RENDER_API_KEY` in Render environment (optional)
2. Or ignore feature flag check warnings (worker will still run health checks)
3. Verify flags via Render dashboard instead:
   - Navigate to celeste-pipeline-v1 → Environment
   - Check `SHOPPING_LIST_LENS_V1_ENABLED=true`

### Issue 4: 503 FEATURE_DISABLED Responses

**Symptoms**:
```
ERROR: ❌ List endpoint: 503 FEATURE_DISABLED
ERROR: ❌ Suggestions endpoint: 503 FEATURE_DISABLED
```

**Fix**:
1. Verify feature flag is enabled in `render.yaml`:
   ```yaml
   - key: SHOPPING_LIST_LENS_V1_ENABLED
     value: "true"
   ```
2. Re-deploy web service (not just worker):
   ```bash
   # Render dashboard → celeste-pipeline-v1 → Manual Deploy
   ```
3. Wait 2-3 minutes for deployment to complete
4. Check worker logs for next health check cycle (15 min interval)

---

## Success Criteria

✅ **Worker deployed and running**: Render dashboard shows "Active" status

✅ **First health check completed**: Logs show:
```
INFO: ✅ Wrote health check to DB: id=<uuid>
INFO: Sleeping for 15 minutes...
```

✅ **Database row exists**: Query 1 returns 1 row with:
- `yacht_id` = canary yacht
- `lens_id` = `shopping_list`
- `status` ∈ {`healthy`, `degraded`, `unhealthy`}
- `observed_at` within last 15 minutes

✅ **No critical errors**:
- `error_rate_percent` ≤ 50% (some errors tolerated during initial rollout)
- No 5xx errors in `notes->checks->*->status_code`
- No database write failures in logs

✅ **Worker continues running**:
- Logs show repeating 15-minute cycles
- No crash/restart loops

---

## Next Steps (After Verification)

1. ✅ **Document evidence**: Fill in "Evidence Capture" section above
2. ⏳ **Monitor for 7 days**:
   - Check health history daily via Query 3
   - Alert if `status=unhealthy` for >2 consecutive checks
   - Alert if `p95_latency_ms` > 10,000ms (10s)
   - Alert if `error_rate_percent` > 1%
3. ⏳ **Hour 4-5: Set up monitoring alerts**:
   - Create `docs/pipeline/templates/lens_ops/OPS_ALERTS_TEMPLATE.md`
   - Define alerting rules (500 errors, P99 > 10s, error_rate > 1%)
4. ⏳ **Hour 5-6: Consolidate evidence**:
   - Create `docs/pipeline/shopping_list_lens/PHASE5_STAGING_CANARY_SUMMARY.md`
   - Include first run evidence + 7-day monitoring summary

---

**Status**: ⏳ Awaiting Deployment to Render Staging

**Ready for deployment**: All code, configuration, and DB migrations complete
