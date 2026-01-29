# Lens Ops Monitoring Alerts Template

**Purpose**: Define alerting rules for lens health monitoring
**Version**: 1.0.0
**Date**: 2026-01-28

**Canon Citations**:
- 500 is always failure: `/Volumes/Backup/CELESTE/testing_success_ci:cd.md:249`
- 0×500 requirement: All lenses must maintain zero 5xx errors in production
- P99 latency: <10s is acceptable for MUTATE actions, <1s preferred

---

## Alert Categories

### 1. Critical Alerts (Immediate Action Required)

**Trigger Conditions**:
- Any 5xx error from lens endpoints (0×500 violation)
- `status='unhealthy'` for 2+ consecutive health checks
- Worker crash/restart loop (>3 restarts in 1 hour)
- Database write failures (health check data not persisted)

**Notification Channels**:
- PagerDuty (if configured)
- Slack #ops-critical channel
- Email to on-call engineer

**Response SLA**: 15 minutes

---

### 2. Warning Alerts (Attention Required)

**Trigger Conditions**:
- `status='degraded'` for 2+ consecutive health checks
- P99 latency > 10s for 2 consecutive health check cycles
- Error rate > 1% for 2 consecutive cycles
- P95 latency > 5s for 2 consecutive cycles

**Notification Channels**:
- Slack #ops-warnings channel
- Email digest (hourly)

**Response SLA**: 1 hour

---

### 3. Informational Alerts (Review Later)

**Trigger Conditions**:
- Feature flag toggled (503 → 200 or 200 → 503 transition)
- First successful health check after deployment
- P95 latency increase >50% (but still <5s)
- Error rate 0.5-1% (edge of acceptable range)

**Notification Channels**:
- Slack #ops-info channel
- Daily summary email

**Response SLA**: Next business day

---

## Alert Definitions

### Alert 1: 5xx Error Detected (CRITICAL)

**Condition**:
```sql
SELECT COUNT(*) FROM pms_health_checks
WHERE lens_id = '{LENS_ID}'
  AND yacht_id = '{YACHT_ID}'
  AND observed_at > NOW() - INTERVAL '15 minutes'
  AND (
    notes->'checks'->'list_endpoint'->>'status_code' >= '500'
    OR notes->'checks'->'suggestions_endpoint'->>'status_code' >= '500'
    OR notes->'checks'->'execute_endpoint'->>'status_code' >= '500'
  );
-- Alert if count > 0
```

**Message Template**:
```
🚨 CRITICAL: 5xx error detected in {LENS_ID} lens (yacht: {YACHT_ID})

Endpoint: {endpoint_name}
Status Code: {status_code}
Timestamp: {observed_at}
Error Details: {error_message}

0×500 requirement violated - immediate investigation required.

Citation: /Volumes/Backup/CELESTE/testing_success_ci:cd.md:249

Runbook: docs/pipeline/{LENS_ID}_lens/INCIDENT_RESPONSE.md
```

**Incident Response**:
1. Check Render logs for error stack traces
2. Query `pms_health_events` for related errors
3. If feature flag issue: toggle `{LENS_ID}_V1_ENABLED=false` (rollback)
4. If code bug: revert last deployment
5. Post-incident: Update `docs/pipeline/{LENS_ID}_lens/INCIDENT_LOG.md`

---

### Alert 2: Consecutive Unhealthy Status (CRITICAL)

**Condition**:
```sql
WITH recent_checks AS (
  SELECT status, observed_at
  FROM pms_health_checks
  WHERE lens_id = '{LENS_ID}'
    AND yacht_id = '{YACHT_ID}'
    AND observed_at > NOW() - INTERVAL '30 minutes'
  ORDER BY observed_at DESC
  LIMIT 2
)
SELECT COUNT(*) FROM recent_checks WHERE status = 'unhealthy';
-- Alert if count = 2
```

**Message Template**:
```
🚨 CRITICAL: {LENS_ID} lens unhealthy for 2+ consecutive checks (yacht: {YACHT_ID})

Last Check: {observed_at}
Error Rate: {error_rate_percent}%
Errors: {errors_json}

Possible causes:
- Feature flag disabled (check SHOPPING_LIST_LENS_V1_ENABLED)
- Service degradation
- Database connectivity issues

Runbook: docs/pipeline/{LENS_ID}_lens/INCIDENT_RESPONSE.md
```

**Incident Response**:
1. Query latest health check:
   ```sql
   SELECT * FROM pms_health_checks
   WHERE lens_id = '{LENS_ID}' AND yacht_id = '{YACHT_ID}'
   ORDER BY observed_at DESC LIMIT 1;
   ```
2. Check `notes->errors` array for specific failures
3. Verify feature flags via Render dashboard
4. Check service logs for exceptions
5. If persistent: rollback deployment

---

### Alert 3: P99 Latency Threshold Exceeded (WARNING)

**Condition**:
```sql
WITH recent_checks AS (
  SELECT p95_latency_ms, observed_at
  FROM pms_health_checks
  WHERE lens_id = '{LENS_ID}'
    AND yacht_id = '{YACHT_ID}'
    AND observed_at > NOW() - INTERVAL '30 minutes'
  ORDER BY observed_at DESC
  LIMIT 2
)
SELECT COUNT(*) FROM recent_checks WHERE p95_latency_ms > 10000;
-- Alert if count = 2
```

**Message Template**:
```
⚠️ WARNING: {LENS_ID} lens P95 latency > 10s for 2+ consecutive checks (yacht: {YACHT_ID})

Current P95: {p95_latency_ms}ms
Last Check: {observed_at}

Possible causes:
- Database query slow (check slow query log)
- LLM inference timeout (check OpenAI status)
- Network latency

Runbook: docs/pipeline/{LENS_ID}_lens/PERFORMANCE_TUNING.md
```

**Incident Response**:
1. Check Supabase slow query log
2. Check OpenAI API status (https://status.openai.com/)
3. Review recent code changes for inefficient queries
4. If persistent: add database indexes or optimize handlers

---

### Alert 4: Error Rate Threshold Exceeded (WARNING)

**Condition**:
```sql
WITH recent_checks AS (
  SELECT error_rate_percent, observed_at
  FROM pms_health_checks
  WHERE lens_id = '{LENS_ID}'
    AND yacht_id = '{YACHT_ID}'
    AND observed_at > NOW() - INTERVAL '30 minutes'
  ORDER BY observed_at DESC
  LIMIT 2
)
SELECT COUNT(*) FROM recent_checks WHERE error_rate_percent > 1.0;
-- Alert if count = 2
```

**Message Template**:
```
⚠️ WARNING: {LENS_ID} lens error rate > 1% for 2+ consecutive checks (yacht: {YACHT_ID})

Current Error Rate: {error_rate_percent}%
Sample Size: {sample_size}
Last Check: {observed_at}
Errors: {errors_json}

Possible causes:
- Intermittent 4xx errors (permissions, validation)
- Service degradation (503, 502)
- Network issues

Runbook: docs/pipeline/{LENS_ID}_lens/INCIDENT_RESPONSE.md
```

**Incident Response**:
1. Query health events for error details:
   ```sql
   SELECT * FROM pms_health_events
   WHERE check_id IN (
     SELECT id FROM pms_health_checks
     WHERE lens_id = '{LENS_ID}' AND yacht_id = '{YACHT_ID}'
       AND observed_at > NOW() - INTERVAL '1 hour'
   )
   ORDER BY occurred_at DESC;
   ```
2. Check if errors are 4xx (client) or 5xx (server)
3. If 4xx: review role permissions, validation logic
4. If 5xx: escalate to CRITICAL (0×500 violation)

---

### Alert 5: Worker Crash Loop (CRITICAL)

**Condition**:
- Monitor Render dashboard for worker restarts
- Or check log timestamps for restart pattern

**Manual Check**:
```bash
# Check worker restart count via Render API
curl -H "Authorization: Bearer $RENDER_API_KEY" \
  "https://api.render.com/v1/services/{SERVICE_ID}/events" | \
  jq '.[] | select(.type == "service-restart")'
# Alert if >3 restarts in 1 hour
```

**Message Template**:
```
🚨 CRITICAL: {LENS_ID} health worker crash loop detected (>3 restarts in 1 hour)

Service: shopping-list-health-worker
Restarts: {restart_count}
Last Restart: {last_restart_time}

Possible causes:
- Missing environment variables (JWT_SECRET, SERVICE_KEY)
- Database connection failures
- Unhandled exception in health check logic

Runbook: verification_handoff/ops/OPS_HEALTH_FIRST_RUN.md (Troubleshooting)
```

**Incident Response**:
1. Check Render logs for exception stack traces
2. Verify all environment variables are set
3. Test database connectivity via Supabase dashboard
4. If needed: disable worker temporarily, fix code, re-deploy

---

### Alert 6: Feature Flag Toggle Detected (INFO)

**Condition**:
```sql
-- Compare last 2 health checks for flag status change
WITH recent_checks AS (
  SELECT
    notes->'checks'->'feature_flags'->>'status' AS flag_status,
    observed_at
  FROM pms_health_checks
  WHERE lens_id = '{LENS_ID}'
    AND yacht_id = '{YACHT_ID}'
    AND observed_at > NOW() - INTERVAL '30 minutes'
  ORDER BY observed_at DESC
  LIMIT 2
)
SELECT COUNT(DISTINCT flag_status) FROM recent_checks;
-- Alert if count = 2 (status changed)
```

**Message Template**:
```
ℹ️ INFO: {LENS_ID} lens feature flag toggled (yacht: {YACHT_ID})

Previous Status: {previous_flag_status}
Current Status: {current_flag_status}
Timestamp: {observed_at}

Expected: 503 FEATURE_DISABLED errors if toggled OFF
Expected: 200 OK responses if toggled ON

No action required unless unexpected toggle.
```

**Incident Response**:
- None (informational only)
- Review if toggle was unintentional

---

## Implementation Guide

### Step 1: Create Monitoring Script

**File**: `tools/ops/monitors/{LENS_ID}_alert_checker.py`

```python
#!/usr/bin/env python3
"""
{LENS_ID} Lens Alert Checker

Queries pms_health_checks and triggers alerts based on thresholds.
Run via cron every 5 minutes.
"""

import os
import requests
from datetime import datetime, timedelta, timezone

SUPABASE_URL = os.getenv('SUPABASE_URL')
SERVICE_KEY = os.getenv('SUPABASE_SERVICE_KEY')
SLACK_WEBHOOK = os.getenv('SLACK_OPS_WEBHOOK')
LENS_ID = "{LENS_ID}"
YACHT_ID = "{YACHT_ID}"

def check_5xx_errors():
    """Alert 1: Check for 5xx errors"""
    # Query pms_health_checks for recent 5xx errors
    # POST to SLACK_WEBHOOK if found
    pass

def check_unhealthy_status():
    """Alert 2: Check for consecutive unhealthy status"""
    # Query last 2 health checks
    # POST to SLACK_WEBHOOK if both unhealthy
    pass

# ... implement all alerts ...

if __name__ == "__main__":
    check_5xx_errors()
    check_unhealthy_status()
    # ... run all checks ...
```

### Step 2: Configure Slack Webhooks

1. Create Slack webhook URL for #ops-critical channel
2. Create Slack webhook URL for #ops-warnings channel
3. Create Slack webhook URL for #ops-info channel
4. Add to Render environment:
   ```yaml
   - key: SLACK_OPS_CRITICAL_WEBHOOK
     value: "https://hooks.slack.com/services/..."
   - key: SLACK_OPS_WARNINGS_WEBHOOK
     value: "https://hooks.slack.com/services/..."
   - key: SLACK_OPS_INFO_WEBHOOK
     value: "https://hooks.slack.com/services/..."
   ```

### Step 3: Set Up Cron Job (Render Cron Service)

**Option A: Render Cron Job**
```yaml
- type: cron
  name: shopping-list-alert-checker
  runtime: python
  schedule: "*/5 * * * *"  # Every 5 minutes
  buildCommand: pip install requests
  startCommand: python tools/ops/monitors/shopping_list_alert_checker.py
  envVars:
    - key: SUPABASE_URL
      value: "https://vzsohavtuotocgrfkfyd.supabase.co"
    - key: SUPABASE_SERVICE_KEY
      sync: false
    - key: SLACK_OPS_CRITICAL_WEBHOOK
      sync: false
```

**Option B: GitHub Actions (Scheduled Workflow)**
```yaml
name: Shopping List Alert Checker
on:
  schedule:
    - cron: '*/5 * * * *'  # Every 5 minutes
jobs:
  check-alerts:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - run: python tools/ops/monitors/shopping_list_alert_checker.py
        env:
          SUPABASE_URL: ${{ secrets.SUPABASE_URL }}
          SUPABASE_SERVICE_KEY: ${{ secrets.SUPABASE_SERVICE_KEY }}
          SLACK_OPS_CRITICAL_WEBHOOK: ${{ secrets.SLACK_OPS_CRITICAL_WEBHOOK }}
```

---

## Monitoring Dashboard

### Recommended Metrics to Display

**Supabase Dashboard** (or custom Grafana):
1. Health status over time (healthy/degraded/unhealthy)
2. P95 latency trend (last 7 days)
3. Error rate trend (last 7 days)
4. 5xx error count (last 24 hours)
5. Worker uptime % (last 30 days)

**Sample SQL for Dashboard**:
```sql
-- Health status over last 7 days
SELECT
    DATE_TRUNC('hour', observed_at) AS hour,
    status,
    COUNT(*) AS check_count,
    AVG(p95_latency_ms) AS avg_latency,
    AVG(error_rate_percent) AS avg_error_rate
FROM pms_health_checks
WHERE lens_id = '{LENS_ID}'
  AND yacht_id = '{YACHT_ID}'
  AND observed_at > NOW() - INTERVAL '7 days'
GROUP BY DATE_TRUNC('hour', observed_at), status
ORDER BY hour DESC;
```

---

## Incident Response Runbook

### Severity 1: Production Outage (5xx errors, 0×500 violation)

**Steps**:
1. **Immediate**: Check Render logs for stack traces
2. **Within 5 min**: Query `pms_health_events` for error details
3. **Within 10 min**: Decide rollback or hotfix
4. **Rollback**: Set feature flag `{LENS_ID}_V1_ENABLED=false`, deploy
5. **Hotfix**: Fix code, deploy, monitor for 15 minutes
6. **Post-incident**: Write incident report in `docs/pipeline/{LENS_ID}_lens/INCIDENTS/YYYY-MM-DD.md`

### Severity 2: Degraded Service (P99 > 10s, error_rate > 1%)

**Steps**:
1. **Within 30 min**: Identify root cause (slow queries, API timeouts, etc.)
2. **Within 1 hour**: Implement mitigation (indexes, caching, etc.)
3. **Monitor**: Check health checks for improvement
4. **If persists**: Escalate to Severity 1

### Severity 3: Informational (feature flag toggle)

**Steps**:
1. Verify toggle was intentional
2. Monitor next health check for expected behavior
3. Document in change log

---

## Testing Alert System

**Dry Run Test**:
```bash
# Manually trigger alert (test Slack webhook)
curl -X POST "$SLACK_OPS_CRITICAL_WEBHOOK" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "🧪 TEST ALERT: {LENS_ID} lens monitoring (please ignore)"
  }'
```

**Simulated Failure Test**:
1. Temporarily disable feature flag: `{LENS_ID}_V1_ENABLED=false`
2. Wait 15 minutes for health check to run
3. Verify Alert 2 (Unhealthy Status) triggers
4. Re-enable feature flag: `{LENS_ID}_V1_ENABLED=true`
5. Verify Alert 6 (Feature Flag Toggle) triggers

---

## Customization for Shopping List Lens

**Lens ID**: `shopping_list`
**Domain**: `shopping_list`
**Feature Flag**: `SHOPPING_LIST_LENS_V1_ENABLED`
**Canary Yacht**: `85fe1119-b04c-41ac-80f1-829d23322598`

**Endpoints to Monitor**:
- `/v1/actions/list?domain=shopping_list`
- `POST /v1/actions/suggestions` (payload: `{"domain": "shopping_list"}`)
- `POST /v1/actions/execute` (create_shopping_list_item)

**Alert Thresholds**:
- P95 latency: 5000ms warning, 10000ms critical
- Error rate: 1% warning, 5% critical
- 5xx errors: 0 (immediate critical alert)

**Notification Channels**:
- Slack #celeste-ops-critical
- Slack #celeste-ops-warnings
- Email: ops@celeste7.ai

---

**Template Version**: 1.0.0
**Last Updated**: 2026-01-28
**Next Review**: After first 7 days of canary monitoring
