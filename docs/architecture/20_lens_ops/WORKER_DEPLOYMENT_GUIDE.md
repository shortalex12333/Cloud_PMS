# Health Worker Deployment Guide

## Overview

This guide covers deploying lens health workers to Render. Workers monitor endpoint health and write results to `pms_health_checks` table.

---

## Prerequisites

1. **Health tables applied** to tenant database:
   ```sql
   -- Run migration: docs/architecture/20_lens_ops/migrations/ops_health_tables.sql
   -- Tables: pms_health_checks, pms_health_events
   -- RLS policies enabled
   ```

2. **Worker block in render.yaml** (already configured for documents)

3. **Secrets ready:**
   - Tenant Supabase service key
   - Tenant JWT secret

---

## Deployment Steps

### Step 1: Blueprint Sync

1. Go to Render Dashboard → **Blueprints**
2. Select the Cloud_PMS blueprint
3. Click **Sync** to pull latest `render.yaml`
4. Verify `documents-health-worker` appears in services list

### Step 2: Add Secrets

In Render Dashboard → `documents-health-worker` → **Environment**:

| Key | Value | Notes |
|-----|-------|-------|
| `SUPABASE_SERVICE_KEY` | `eyJ...` | Tenant service role key (writes to pms_health_*) |
| `TENANT_SUPABASE_JWT_SECRET` | `...` | JWT secret for generating test tokens |

Optional (for feature flag monitoring):
| Key | Value | Notes |
|-----|-------|-------|
| `RENDER_API_KEY` | `rnd_...` | Render API key |
| `RENDER_SERVICE_ID` | `srv-...` | Pipeline service ID |

### Step 3: Deploy

1. Click **Manual Deploy** or wait for autoDeploy
2. Monitor deploy logs for startup messages:
   ```
   Starting documents health worker
   Interval: 15 minutes
   API Base: https://celeste-pipeline-v1.onrender.com
   ```

### Step 4: Verify (within 15 minutes)

Query tenant database:
```sql
SELECT id, status, p95_latency_ms, error_rate_percent, observed_at
FROM pms_health_checks
WHERE lens_id = 'documents'
ORDER BY observed_at DESC
LIMIT 1;
```

Expected result:
```
id: <uuid>
status: healthy
p95_latency_ms: <number>
error_rate_percent: 0.00
observed_at: <recent timestamp>
```

---

## Troubleshooting

### No rows after 20 minutes

1. **Check worker logs:**
   ```bash
   render logs -s documents-health-worker --tail 100
   ```

2. **Verify secrets:**
   - `SUPABASE_SERVICE_KEY` must be the service role key (not anon key)
   - `TENANT_SUPABASE_URL` must point to tenant (not master)

3. **Test API connectivity:**
   ```bash
   curl https://celeste-pipeline-v1.onrender.com/v1/actions/health
   ```

### Worker shows unhealthy status

1. **Check error details:**
   ```sql
   SELECT he.level, he.detail_json
   FROM pms_health_events he
   JOIN pms_health_checks hc ON he.check_id = hc.id
   WHERE hc.lens_id = 'documents'
   ORDER BY he.created_at DESC
   LIMIT 5;
   ```

2. **Common causes:**
   - API returning 5xx → Check pipeline service logs
   - Feature flags disabled → Check Render env vars
   - JWT expired → Worker generates fresh tokens each cycle

---

## Worker Configuration Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `HEALTH_CHECK_INTERVAL_MINUTES` | 15 | Check frequency |
| `API_BASE_URL` | - | Pipeline API endpoint |
| `TENANT_SUPABASE_URL` | - | Tenant DB URL |
| `SUPABASE_SERVICE_KEY` | - | Service role for writes |
| `TENANT_SUPABASE_JWT_SECRET` | - | JWT secret for test auth |
| `TEST_YACHT_ID` | (default) | Yacht for health checks |
| `TEST_HOD_USER_ID` | (default) | HOD user for testing |
| `TEST_HOD_EMAIL` | (default) | HOD email for JWT |
| `LOG_LEVEL` | INFO | Logging verbosity |

---

## Deployed Workers

| Worker | Lens | Status |
|--------|------|--------|
| `documents-health-worker` | documents | Pending deployment |

---

**Last Updated:** 2026-01-28
