# Health Worker Blueprint Registry

**Purpose:** Track all lens health workers and their Render Blueprint status.

**Location:** `render.yaml` (root)

---

## Blueprint Sync Requirement

When adding a new lens, you MUST:
1. Create the health worker script in `tools/ops/monitors/{lens}_health_worker.py`
2. Add the worker definition to `render.yaml`
3. Perform a **Blueprint Sync** in Render Dashboard to create the service
4. Add required secrets to the new service

---

## Current Health Workers

| Lens | Worker Script | Render Service Name | In Blueprint | Deployed |
|------|---------------|---------------------|--------------|----------|
| Documents | `tools/ops/monitors/documents_health_worker.py` | `documents-health-worker` | Yes | Pending Sync |
| Shopping List | `tools/ops/monitors/shopping_list_health_worker.py` | `shopping-list-health-worker` | Yes | Pending Sync |

---

## Future Lenses (Add When Ready)

| Lens | Worker Script | Render Service Name | Status |
|------|---------------|---------------------|--------|
| Certificates | `tools/ops/monitors/certificates_health_worker.py` | `certificates-health-worker` | Not Created |
| Work Orders | `tools/ops/monitors/work_orders_health_worker.py` | `work-orders-health-worker` | Not Created |
| Inventory | `tools/ops/monitors/inventory_health_worker.py` | `inventory-health-worker` | Not Created |
| Parts | `tools/ops/monitors/parts_health_worker.py` | `parts-health-worker` | Not Created |
| Equipment | `tools/ops/monitors/equipment_health_worker.py` | `equipment-health-worker` | Not Created |
| Receiving | `tools/ops/monitors/receiving_health_worker.py` | `receiving-health-worker` | Not Created |

---

## Required Secrets (All Workers)

```
SUPABASE_SERVICE_KEY      = <tenant service role key>
TENANT_SUPABASE_JWT_SECRET = <tenant JWT secret for test user generation>
```

These secrets are marked `sync: false` in render.yaml - must be added manually per service.

---

## Blueprint Worker Template

When adding a new lens health worker to `render.yaml`:

```yaml
  # {Lens Name} Health Worker - Lens Ops Monitoring
  - type: worker
    name: {lens-name}-health-worker
    runtime: python
    plan: starter
    region: oregon
    branch: main
    buildCommand: pip install requests PyJWT
    startCommand: python tools/ops/monitors/{lens_name}_health_worker.py
    autoDeploy: true
    envVars:
      - key: PYTHON_VERSION
        value: "3.11.6"
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

---

## Deployment Checklist

After adding a worker to render.yaml:

- [ ] Commit and push to main
- [ ] Go to Render Dashboard → Blueprints
- [ ] Click **Sync** on Cloud_PMS blueprint
- [ ] Verify new service appears
- [ ] Add secrets: `SUPABASE_SERVICE_KEY`, `TENANT_SUPABASE_JWT_SECRET`
- [ ] Verify first health check appears in `pms_health_checks` table (~20 min)

---

## Verification Query

```sql
-- Check all lens health statuses
SELECT
    lens_id,
    status,
    p95_latency_ms,
    error_rate_percent,
    observed_at
FROM pms_health_checks
WHERE observed_at > NOW() - INTERVAL '1 hour'
ORDER BY lens_id, observed_at DESC;
```

---

**Last Updated:** 2026-01-29
