# Lens Ops - Observability Guide

## Overview

This document describes how to monitor lens health using the ops infrastructure.

---

## Service Level Objectives (SLOs)

### Health Targets

| Metric | Target | Alert Threshold |
|--------|--------|-----------------|
| P95 Latency | < 500ms | > 500ms for 2 consecutive checks |
| Error Rate | < 1% | > 1% for 2 consecutive checks |
| Health Status | `healthy` | 2 consecutive `unhealthy` checks |

### Alert Criteria

**Trigger alert when:**
- 2 consecutive health checks return `unhealthy` status
- P95 latency exceeds 500ms for 2 consecutive checks
- Error rate exceeds 1% for 2 consecutive checks

**Query for alerting:**
```sql
-- Check for consecutive unhealthy
SELECT lens_id, COUNT(*) as unhealthy_count
FROM (
    SELECT lens_id, status,
           ROW_NUMBER() OVER (PARTITION BY lens_id ORDER BY observed_at DESC) as rn
    FROM pms_health_checks
    WHERE observed_at > now() - interval '1 hour'
) recent
WHERE rn <= 2 AND status = 'unhealthy'
GROUP BY lens_id
HAVING COUNT(*) = 2;
```

---

## Health Check Tables

**Database:** Tenant Supabase
**Tables:** `pms_health_checks`, `pms_health_events`

### Querying Health Status

```sql
-- Latest health status for all lenses
SELECT
    lens_id,
    status,
    p95_latency_ms,
    error_rate_percent,
    observed_at
FROM pms_health_checks
WHERE observed_at > now() - interval '1 hour'
ORDER BY observed_at DESC;

-- Latest check per lens
SELECT DISTINCT ON (lens_id)
    lens_id,
    status,
    p95_latency_ms,
    error_rate_percent,
    observed_at,
    notes
FROM pms_health_checks
ORDER BY lens_id, observed_at DESC;

-- Unhealthy lenses (current)
SELECT * FROM get_unhealthy_lenses('<yacht_id>');

-- Error events in last hour
SELECT
    hc.lens_id,
    he.level,
    he.detail_json,
    he.created_at
FROM pms_health_events he
JOIN pms_health_checks hc ON he.check_id = hc.id
WHERE he.created_at > now() - interval '1 hour'
  AND he.level = 'error'
ORDER BY he.created_at DESC;
```

---

## Health Worker Smoke Checks

Each health worker performs these checks every cycle:

| Check | Endpoint | Purpose |
|-------|----------|---------|
| Service Health | `GET /v1/actions/health` | Pipeline is running |
| Feature Flags | Render API | Flags enabled |
| List Endpoint | `GET /v1/actions/list?domain={lens}` | Actions discoverable |
| Execute Action | `POST /v1/actions/execute` | Core action works |

### Status Thresholds

| Status | Criteria |
|--------|----------|
| `healthy` | All checks pass, 0 errors |
| `degraded` | Some warnings (e.g., feature flags not configured) |
| `unhealthy` | Any 5xx error or critical failure |

---

## REST API Access

Health data is accessible via Supabase REST API:

```bash
# Latest health check for documents lens
curl -X GET \
  "${TENANT_SUPABASE_URL}/rest/v1/pms_health_checks?lens_id=eq.documents&order=observed_at.desc&limit=1" \
  -H "apikey: ${SUPABASE_SERVICE_KEY}" \
  -H "Authorization: Bearer ${SUPABASE_SERVICE_KEY}"

# Recent error events
curl -X GET \
  "${TENANT_SUPABASE_URL}/rest/v1/pms_health_events?level=eq.error&order=created_at.desc&limit=10" \
  -H "apikey: ${SUPABASE_SERVICE_KEY}" \
  -H "Authorization: Bearer ${SUPABASE_SERVICE_KEY}"
```

---

## Alerting Integration

### Grafana/Prometheus

Query endpoint for metrics:

```sql
-- Metric: lens_health_status (gauge)
SELECT
    lens_id,
    CASE status
        WHEN 'healthy' THEN 1
        WHEN 'degraded' THEN 0.5
        WHEN 'unhealthy' THEN 0
    END as health_score,
    p95_latency_ms,
    error_rate_percent
FROM pms_health_checks
WHERE observed_at > now() - interval '30 minutes'
ORDER BY lens_id, observed_at DESC;
```

### Slack Webhook (Example)

Add to health worker for alerts:

```python
def send_alert(lens_id: str, status: str, errors: list):
    webhook_url = os.getenv('SLACK_WEBHOOK_URL')
    if not webhook_url or status == 'healthy':
        return

    payload = {
        "text": f"⚠️ Lens Health Alert: {lens_id}",
        "blocks": [
            {"type": "section", "text": {"type": "mrkdwn", "text": f"*Lens:* {lens_id}\n*Status:* {status}"}},
            {"type": "section", "text": {"type": "mrkdwn", "text": f"*Errors:*\n" + "\n".join(f"• {e}" for e in errors)}}
        ]
    }
    requests.post(webhook_url, json=payload)
```

---

## Dashboard SQL (Retool/Metabase)

### Health Summary Dashboard

```sql
-- Widget 1: Current Health by Lens
WITH latest AS (
    SELECT DISTINCT ON (lens_id)
        lens_id,
        status,
        p95_latency_ms,
        error_rate_percent,
        observed_at
    FROM pms_health_checks
    WHERE observed_at > now() - interval '1 hour'
    ORDER BY lens_id, observed_at DESC
)
SELECT
    lens_id,
    status,
    p95_latency_ms || 'ms' as latency,
    error_rate_percent || '%' as error_rate,
    observed_at
FROM latest
ORDER BY
    CASE status WHEN 'unhealthy' THEN 0 WHEN 'degraded' THEN 1 ELSE 2 END,
    lens_id;

-- Widget 2: Health Timeline (last 24h)
SELECT
    lens_id,
    date_trunc('hour', observed_at) as hour,
    mode() WITHIN GROUP (ORDER BY status) as status,
    avg(p95_latency_ms)::int as avg_latency,
    avg(error_rate_percent)::numeric(5,2) as avg_error_rate
FROM pms_health_checks
WHERE observed_at > now() - interval '24 hours'
GROUP BY lens_id, date_trunc('hour', observed_at)
ORDER BY hour DESC, lens_id;

-- Widget 3: Recent Errors
SELECT
    hc.lens_id,
    he.detail_json->>'message' as error,
    he.created_at
FROM pms_health_events he
JOIN pms_health_checks hc ON he.check_id = hc.id
WHERE he.level = 'error'
  AND he.created_at > now() - interval '24 hours'
ORDER BY he.created_at DESC
LIMIT 20;
```

---

## Worker Logs (Render)

View worker logs in Render dashboard or CLI:

```bash
# Tail documents health worker logs
render logs -s documents-health-worker --tail 100

# Filter for errors only
render logs -s documents-health-worker | grep -E "(ERROR|❌|unhealthy)"
```

### Log Format

```
[2026-01-28T20:30:00Z] INFO: Starting health check for lens=documents yacht=85fe1119...
[2026-01-28T20:30:01Z] INFO: ✅ Service health: healthy (15/15 handlers)
[2026-01-28T20:30:02Z] INFO: ✅ List endpoint: 200 OK (6 actions, 245ms)
[2026-01-28T20:30:03Z] INFO: ✅ Execute list_documents: 200 OK (312ms)
[2026-01-28T20:30:03Z] INFO: Health check complete: status=healthy p95=312ms error_rate=0.00%
[2026-01-28T20:30:04Z] INFO: ✅ Wrote health check to DB: id=abc123...
```

---

## Deployed Lenses

| Lens | Worker | Status | Interval |
|------|--------|--------|----------|
| documents | documents-health-worker | Active | 15 min |
| certificates | (pending) | - | - |
| equipment | (pending) | - | - |
| faults | (pending) | - | - |
| work_orders | (pending) | - | - |

---

## Troubleshooting

### No Data in Health Tables

1. Check worker is running in Render
2. Verify `SUPABASE_SERVICE_KEY` is set correctly
3. Check worker logs for DB write errors

### High Latency

1. Check P95 trend in `pms_health_checks`
2. Review Render metrics for resource constraints
3. Check Supabase for slow queries

### Frequent Unhealthy Status

1. Query `pms_health_events` for error details
2. Check if feature flags are enabled
3. Verify API endpoints are responding

---

**Last Updated:** 2026-01-28
