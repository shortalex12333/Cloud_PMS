# Hour 4-5: Monitoring Hooks + Alerts

**Status**: ✅ Complete
**Date**: 2026-01-28
**Branch**: security/signoff

---

## Done

✅ **Created alerts template**: `docs/pipeline/templates/lens_ops/OPS_ALERTS_TEMPLATE.md`
- 6 alert definitions (3 critical, 2 warning, 1 info)
- SQL queries for each alert condition
- Incident response runbooks
- Implementation guide (Slack webhooks, cron jobs)
- Testing procedures

✅ **Created Shopping List alerts**: `docs/pipeline/shopping_list_lens/OPS_ALERTS.md`
- Customized for Shopping List Lens specifics
- Alert thresholds configured (P95: 10s, error rate: 1%, 5xx: 0)
- 3 incident response scenarios documented
- 3 monitoring dashboard queries ready
- Implementation status checklist

✅ **Alert thresholds defined**:
- **CRITICAL**: Any 5xx error (0×500 requirement), consecutive unhealthy status, worker crash loop
- **WARNING**: P95 > 10s for 2 checks, error rate > 1% for 2 checks
- **INFO**: Feature flag toggle detection

✅ **Incident response documented**: 3 common scenarios with step-by-step runbooks

---

## Alert Definitions Summary

### CRITICAL Alerts (15-minute SLA)

**1. 5xx Error Detected**
- Condition: Any endpoint returns 5xx
- Response: Rollback feature flag immediately
- Citation: `/Volumes/Backup/CELESTE/testing_success_ci:cd.md:249` (0×500 requirement)

**2. Consecutive Unhealthy Status**
- Condition: `status='unhealthy'` for 2+ consecutive checks
- Response: Check feature flag status, verify service health

**3. Worker Crash Loop**
- Condition: >3 worker restarts in 1 hour
- Response: Check environment variables, database connectivity

### WARNING Alerts (1-hour SLA)

**4. P95 Latency Threshold Exceeded**
- Condition: P95 > 10,000ms for 2+ consecutive checks
- Response: Check slow query log, OpenAI API status

**5. Error Rate Threshold Exceeded**
- Condition: Error rate > 1% for 2+ consecutive checks
- Response: Query `pms_health_events` for error details

### INFO Alerts (Next business day)

**6. Feature Flag Toggle Detected**
- Condition: Flag status changes between checks
- Response: Verify intentional toggle, document in change log

---

## Alert Queries

All queries available in `docs/pipeline/shopping_list_lens/OPS_ALERTS.md`

### Example: Check for 5xx Errors

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

---

## Incident Response Runbooks

### Scenario 1: 5xx Error on List Endpoint

**Steps** (0-15 minutes):
1. Check Render logs for stack trace
2. Query `pms_health_events` for details
3. Decide: Rollback (`SHOPPING_LIST_LENS_V1_ENABLED=false`) or hotfix
4. Document in incident log

### Scenario 2: Feature Flag Disabled Unexpectedly

**Steps**:
1. Verify flag in Render dashboard
2. Check if toggle was intentional
3. Re-enable if unintentional: `SHOPPING_LIST_LENS_V1_ENABLED=true`
4. Monitor next health check (15 min)

### Scenario 3: P95 Latency Spike (>10s)

**Steps**:
1. Check Supabase slow query log
2. Check OpenAI API status
3. Review recent code changes
4. Mitigate: Add indexes, optimize handlers, increase timeouts

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
    c.p95_latency_ms
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

## Implementation Roadmap

### Week 1 (Manual Monitoring)

- [x] Alert definitions documented
- [x] SQL queries ready
- [x] Incident runbooks written
- [ ] Deploy health worker to Render
- [ ] Monitor health checks manually (daily)
- [ ] Document any alerts triggered

### Week 2-4 (Automated Alerts)

- [ ] Create `tools/ops/monitors/shopping_list_alert_checker.py`
- [ ] Configure Slack webhooks (#celeste-ops-critical, #celeste-ops-warnings, #celeste-ops-info)
- [ ] Deploy Render cron job (5-minute interval) or GitHub Actions workflow
- [ ] Test alert system (dry run + simulated failure)

### Production Rollout

- [ ] Apply alerts to production canary yacht
- [ ] Expand monitoring to 10% → 50% → 100% of yachts
- [ ] Create Grafana/Supabase dashboard (optional)

---

## Alert Thresholds

| Metric | Warning | Critical | Notes |
|--------|---------|----------|-------|
| P95 Latency | 5,000ms | 10,000ms | Typical: 100-500ms |
| Error Rate | 1% | 5% | Target: 0% |
| 5xx Errors | N/A | Any (>0) | 0×500 requirement |
| Unhealthy Status | 1 check | 2+ checks | Consecutive only |
| Worker Restarts | 2/hour | 3/hour | Check Render logs |

**Rationale**:
- **P95 < 10s**: Canon doctrine for acceptable MUTATE action latency
- **Error rate < 1%**: Production-grade reliability threshold
- **0×500**: Hard requirement (Citation: `testing_success_ci:cd.md:249`)

---

## Testing Procedures

### Test 1: Dry Run (Slack Webhook)

```bash
curl -X POST "$SLACK_OPS_CRITICAL_WEBHOOK" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "🧪 TEST ALERT: shopping_list lens monitoring (please ignore)"
  }'
```

**Expected**: Message appears in #celeste-ops-critical channel

### Test 2: Simulated Failure (Feature Flag Toggle)

**Steps**:
1. Disable feature flag: `SHOPPING_LIST_LENS_V1_ENABLED=false`
2. Wait 15 minutes for health check to run
3. Verify Alert #2 triggers (Consecutive Unhealthy Status)
4. Re-enable flag: `SHOPPING_LIST_LENS_V1_ENABLED=true`
5. Wait 15 minutes
6. Verify Alert #6 triggers (Feature Flag Toggle)

**Expected**:
- Alert #2: "🚨 CRITICAL: shopping_list lens unhealthy for 2+ consecutive checks"
- Alert #6: "ℹ️ INFO: shopping_list lens feature flag toggled"

---

## Documentation References

**Alerts Template**: `docs/pipeline/templates/lens_ops/OPS_ALERTS_TEMPLATE.md`
- Generic template for all lenses
- 6 alert patterns with SQL queries
- Implementation guide
- Testing procedures

**Shopping List Alerts**: `docs/pipeline/shopping_list_lens/OPS_ALERTS.md`
- Shopping List specific configuration
- Customized thresholds and runbooks
- Implementation status checklist

**Health Worker Deployment**: `verification_handoff/ops/OPS_HEALTH_FIRST_RUN.md`
- Deployment steps
- Verification queries
- Troubleshooting guide

**Ops Health Migration**: `verification_handoff/ops/OPS_HEALTH_MIGRATION_APPLIED.md`
- Database schema (pms_health_checks, pms_health_events)
- RLS policies
- Helper functions

---

## Next

⏳ **Hour 5-6: Consolidate + next lens prep**
- Create `docs/pipeline/shopping_list_lens/PHASE5_STAGING_CANARY_SUMMARY.md`
  - Consolidate evidence from Hours 0-5
  - Flags ON proof
  - Smoke test transcripts
  - First health check results (pending deployment)
  - Pass/fail summary
- Create `NEXT_LENS_KICKOFF.md` (Receiving Lens)
  - Zero→Gold plan
  - DB truth, actions, RLS, storage, signatures, tests, flags
- Status ping: Canary schedule, worker status, backlog items

---

## Risks

✅ **No risks identified**:
- Alert definitions complete and documented
- SQL queries tested and ready
- Incident runbooks written
- Implementation roadmap clear

⚠️ **Pending work**:
- Automated alert checker requires Slack webhooks (deferred to Week 2)
- Testing requires deployed health worker (pending Render deployment)
- Manual monitoring sufficient for Week 1 (query database daily)

---

**Status**: ✅ Hour 4-5 Complete - Monitoring Alerts Documented

**Deliverables**:
1. Generic alerts template (all lenses)
2. Shopping List alerts (customized)
3. 6 alert definitions with SQL queries
4. 3 incident response runbooks
5. 3 monitoring dashboard queries
6. Implementation roadmap
7. Testing procedures
