# Shopping List Lens - Monitoring Alerts

**Lens ID**: `shopping_list`
**Domain**: `shopping_list`
**Feature Flag**: `SHOPPING_LIST_LENS_V1_ENABLED`
**Canary Yacht**: `85fe1119-b04c-41ac-80f1-829d23322598`
**Version**: 1.0.0
**Date**: 2026-01-28

**Based on**: `docs/pipeline/templates/lens_ops/OPS_ALERTS_TEMPLATE.md`

---

## Active Alerts

### CRITICAL Alerts (15-minute SLA)

#### 1. 5xx Error Detected
**Condition**: Any endpoint returns 5xx status code
**Query**:
```sql
SELECT COUNT(*) FROM pms_health_checks
WHERE lens_id = 'shopping_list'
  AND yacht_id = '85fe1119-b04c-41ac-80f1-829d23322598'
  AND observed_at > NOW() - INTERVAL '15 minutes'
  AND (
    notes->'checks'->'list_endpoint'->>'status_code' >= '500'
    OR notes->'checks'->'suggestions_endpoint'->>'status_code' >= '500'
  );
-- Alert if count > 0
```

**Slack**: #celeste-ops-critical
**Incident Response**: Rollback feature flag → `SHOPPING_LIST_LENS_V1_ENABLED=false`

#### 2. Consecutive Unhealthy Status
**Condition**: `status='unhealthy'` for 2+ consecutive checks
**Query**:
```sql
WITH recent_checks AS (
  SELECT status, observed_at
  FROM pms_health_checks
  WHERE lens_id = 'shopping_list'
    AND yacht_id = '85fe1119-b04c-41ac-80f1-829d23322598'
    AND observed_at > NOW() - INTERVAL '30 minutes'
  ORDER BY observed_at DESC
  LIMIT 2
)
SELECT COUNT(*) FROM recent_checks WHERE status = 'unhealthy';
-- Alert if count = 2
```

**Slack**: #celeste-ops-critical
**Incident Response**: Check feature flag status, verify service health

#### 3. Worker Crash Loop
**Condition**: >3 worker restarts in 1 hour
**Manual Check**: Render dashboard → shopping-list-health-worker → Events
**Slack**: #celeste-ops-critical
**Incident Response**: Check environment variables, database connectivity

---

### WARNING Alerts (1-hour SLA)

#### 4. P95 Latency Threshold Exceeded
**Condition**: P95 latency > 10,000ms for 2+ consecutive checks
**Query**:
```sql
WITH recent_checks AS (
  SELECT p95_latency_ms, observed_at
  FROM pms_health_checks
  WHERE lens_id = 'shopping_list'
    AND yacht_id = '85fe1119-b04c-41ac-80f1-829d23322598'
    AND observed_at > NOW() - INTERVAL '30 minutes'
  ORDER BY observed_at DESC
  LIMIT 2
)
SELECT COUNT(*) FROM recent_checks WHERE p95_latency_ms > 10000;
-- Alert if count = 2
```

**Slack**: #celeste-ops-warnings
**Incident Response**: Check Supabase slow query log, OpenAI API status

#### 5. Error Rate Threshold Exceeded
**Condition**: Error rate > 1% for 2+ consecutive checks
**Query**:
```sql
WITH recent_checks AS (
  SELECT error_rate_percent, observed_at
  FROM pms_health_checks
  WHERE lens_id = 'shopping_list'
    AND yacht_id = '85fe1119-b04c-41ac-80f1-829d23322598'
    AND observed_at > NOW() - INTERVAL '30 minutes'
  ORDER BY observed_at DESC
  LIMIT 2
)
SELECT COUNT(*) FROM recent_checks WHERE error_rate_percent > 1.0;
-- Alert if count = 2
```

**Slack**: #celeste-ops-warnings
**Incident Response**: Query `pms_health_events` for error details

---

### INFO Alerts (Next business day)

#### 6. Feature Flag Toggle Detected
**Condition**: Flag status changes between checks
**Query**:
```sql
WITH recent_checks AS (
  SELECT
    notes->'checks'->'feature_flags'->>'status' AS flag_status,
    observed_at
  FROM pms_health_checks
  WHERE lens_id = 'shopping_list'
    AND yacht_id = '85fe1119-b04c-41ac-80f1-829d23322598'
    AND observed_at > NOW() - INTERVAL '30 minutes'
  ORDER BY observed_at DESC
  LIMIT 2
)
SELECT COUNT(DISTINCT flag_status) FROM recent_checks;
-- Alert if count = 2
```

**Slack**: #celeste-ops-info
**Incident Response**: Verify intentional toggle, document in change log

---

## Shopping List Specific Configuration

### Endpoints Monitored

**List Endpoint**: `GET /v1/actions/list?domain=shopping_list`
- Expected: 200 OK with 5 actions
- Critical if: 5xx error
- Warning if: 503 FEATURE_DISABLED (flag off)

**Suggestions Endpoint**: `POST /v1/actions/suggestions` (payload: `{"domain": "shopping_list"}`)
- Expected: 200 OK with 3 suggested actions
- Critical if: 5xx error
- Warning if: 503 FEATURE_DISABLED (flag off)

### Alert Thresholds

| Metric | Warning | Critical | Notes |
|--------|---------|----------|-------|
| P95 Latency | 5,000ms | 10,000ms | Typical: 100-500ms |
| Error Rate | 1% | 5% | Target: 0% |
| 5xx Errors | N/A | Any (>0) | 0×500 requirement |
| Unhealthy Status | 1 check | 2+ checks | Consecutive only |
| Worker Restarts | 2/hour | 3/hour | Check Render logs |

### Actions Monitored

**MUTATE actions** (all require role checks):
1. `create_shopping_list_item` - All authenticated users
2. `approve_shopping_list_item` - HOD only
3. `reject_shopping_list_item` - HOD only
4. `promote_candidate_to_part` - Engineers only

**READ actions**:
5. `view_shopping_list_item_history` - All authenticated users

**Note**: Shopping List has NO SIGNED actions (no signature validation required)

---

## Incident Response Runbook

### Scenario 1: 5xx Error on List Endpoint

**Symptoms**:
- Alert: "🚨 CRITICAL: 5xx error detected in shopping_list lens"
- `notes->checks->list_endpoint->status_code` = 500/502/503

**Steps**:
1. **0-5 min**: Check Render logs for stack trace
   ```bash
   # Render dashboard → celeste-pipeline-v1 → Logs
   # Search for: "GET /v1/actions/list?domain=shopping_list"
   ```

2. **5-10 min**: Query health events for details
   ```sql
   SELECT detail_json FROM pms_health_events
   WHERE check_id = (
     SELECT id FROM pms_health_checks
     WHERE lens_id = 'shopping_list'
       AND yacht_id = '85fe1119-b04c-41ac-80f1-829d23322598'
     ORDER BY observed_at DESC LIMIT 1
   );
   ```

3. **10-15 min**: Decide rollback vs hotfix
   - **Rollback** (safe, fast): Set `SHOPPING_LIST_LENS_V1_ENABLED=false`
   - **Hotfix** (if trivial fix): Deploy code fix, monitor 15 minutes

4. **Post-incident**: Document in `docs/pipeline/shopping_list_lens/INCIDENTS/2026-01-28-5xx-error.md`

### Scenario 2: Feature Flag Disabled Unexpectedly

**Symptoms**:
- Alert: "ℹ️ INFO: shopping_list lens feature flag toggled"
- `notes->checks->feature_flags->status` = "disabled"
- List endpoint returns 503 FEATURE_DISABLED

**Steps**:
1. Verify flag status in Render dashboard:
   ```
   celeste-pipeline-v1 → Environment → SHOPPING_LIST_LENS_V1_ENABLED
   ```

2. Check if toggle was intentional (review recent deployments)

3. If unintentional:
   - Set `SHOPPING_LIST_LENS_V1_ENABLED=true`
   - Deploy via Render dashboard
   - Monitor next health check (15 min)

4. If intentional (rollback):
   - Document reason in change log
   - Update canary rollout plan

### Scenario 3: P95 Latency Spike (>10s)

**Symptoms**:
- Alert: "⚠️ WARNING: shopping_list lens P95 latency > 10s"
- `p95_latency_ms` > 10000 for 2+ checks

**Steps**:
1. Check Supabase slow query log:
   ```sql
   SELECT * FROM pg_stat_statements
   WHERE query LIKE '%pms_shopping_list_items%'
   ORDER BY total_time DESC
   LIMIT 10;
   ```

2. Check OpenAI API status: https://status.openai.com/

3. Review recent code changes for inefficient queries

4. Mitigations:
   - Add database indexes if missing
   - Optimize handler logic (reduce N+1 queries)
   - Increase OpenAI timeout threshold
   - Scale up database (if needed)

---

## Monitoring Dashboard Queries

### 7-Day Health Trend

```sql
SELECT
    DATE_TRUNC('hour', observed_at) AS hour,
    status,
    COUNT(*) AS check_count,
    AVG(p95_latency_ms) AS avg_latency,
    AVG(error_rate_percent) AS avg_error_rate
FROM pms_health_checks
WHERE lens_id = 'shopping_list'
  AND yacht_id = '85fe1119-b04c-41ac-80f1-829d23322598'
  AND observed_at > NOW() - INTERVAL '7 days'
GROUP BY DATE_TRUNC('hour', observed_at), status
ORDER BY hour DESC;
```

### Latest Errors

```sql
SELECT
    e.occurred_at,
    e.level,
    e.detail_json,
    c.status,
    c.p95_latency_ms,
    c.error_rate_percent
FROM pms_health_events e
JOIN pms_health_checks c ON e.check_id = c.id
WHERE c.lens_id = 'shopping_list'
  AND c.yacht_id = '85fe1119-b04c-41ac-80f1-829d23322598'
  AND e.occurred_at > NOW() - INTERVAL '24 hours'
ORDER BY e.occurred_at DESC;
```

### Uptime Percentage (Last 30 Days)

```sql
SELECT
    COUNT(*) FILTER (WHERE status = 'healthy') AS healthy_count,
    COUNT(*) AS total_count,
    ROUND(
        100.0 * COUNT(*) FILTER (WHERE status = 'healthy') / COUNT(*),
        2
    ) AS uptime_percent
FROM pms_health_checks
WHERE lens_id = 'shopping_list'
  AND yacht_id = '85fe1119-b04c-41ac-80f1-829d23322598'
  AND observed_at > NOW() - INTERVAL '30 days';
```

---

## Implementation Status

### Completed ✅

- [x] Alert definitions documented (6 alerts)
- [x] SQL queries for each alert condition
- [x] Incident response runbooks (3 scenarios)
- [x] Monitoring dashboard queries (3 queries)
- [x] Threshold configuration (P95, error rate, 5xx)

### Pending ⏳

- [ ] Deploy alert checker script (`tools/ops/monitors/shopping_list_alert_checker.py`)
- [ ] Configure Slack webhooks (#celeste-ops-critical, #celeste-ops-warnings, #celeste-ops-info)
- [ ] Set up Render cron job or GitHub Actions workflow (5-minute interval)
- [ ] Test alert system (dry run + simulated failure)
- [ ] Create Grafana/Supabase dashboard (optional)

### Next Steps

1. **Week 1** (after deployment):
   - Monitor health checks manually (daily query)
   - Document any alerts triggered
   - Tune thresholds if needed

2. **Week 2-4**:
   - Implement automated alert checker
   - Set up Slack webhooks
   - Deploy cron job

3. **Production rollout**:
   - Apply same alerts to production canary yacht
   - Expand to 10% → 50% → 100% with monitoring

---

## Contact & Escalation

**On-Call**: ops@celeste7.ai
**Slack**: #celeste-ops-critical (urgent), #celeste-ops-warnings (non-urgent)
**Documentation**: `docs/pipeline/shopping_list_lens/`
**Health Worker Logs**: Render dashboard → shopping-list-health-worker
**Database**: https://vzsohavtuotocgrfkfyd.supabase.co

---

**Last Updated**: 2026-01-28
**Next Review**: After 7 days of canary monitoring
**Owner**: Ops Team
