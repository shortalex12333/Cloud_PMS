# Document Lens v2 - Ops Infrastructure

## Overview

Production-grade ops infrastructure for Document Lens v2, following the Lens Ops template pattern.

**Lens ID:** `documents`
**Domain:** `documents`
**Status:** Deployed

---

## Components

### 1. Health Worker

**File:** `tools/ops/monitors/documents_health_worker.py`
**Render Service:** `documents-health-worker` (background worker)

**Purpose:**
- Automated health checks every 15 minutes
- Writes results to `pms_health_checks` table
- Detects feature flag toggles (503 → 200 transitions)
- Structured logging for Render dashboard

**Checks Performed:**
| Check | Endpoint | Success Criteria |
|-------|----------|------------------|
| Service Health | `GET /v1/actions/health` | 200 + all handlers loaded |
| Feature Flags | Render API | All flags enabled |
| List Endpoint | `GET /v1/actions/list?domain=documents` | 200 |
| Execute Action | `POST /v1/actions/execute` (list_documents) | 200 |

**Environment Variables:**
| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `API_BASE_URL` | Yes | - | Pipeline API URL |
| `TENANT_SUPABASE_URL` | Yes | - | Tenant Supabase URL |
| `SUPABASE_SERVICE_KEY` | Yes | - | Service role key for DB writes |
| `TENANT_SUPABASE_JWT_SECRET` | Yes | - | JWT secret for test tokens |
| `HEALTH_CHECK_INTERVAL_MINUTES` | No | 15 | Check interval |
| `TEST_YACHT_ID` | No | (default) | Test yacht UUID |
| `TEST_HOD_USER_ID` | No | (default) | Test HOD user UUID |
| `TEST_HOD_EMAIL` | No | (default) | Test HOD email |
| `RENDER_API_KEY` | No | - | For feature flag checks |
| `RENDER_SERVICE_ID` | No | - | Pipeline service ID |
| `LOG_LEVEL` | No | INFO | Logging level |

---

### 2. Stress Testing

**File:** `tests/stress/documents_actions_endpoints.py`
**Workflow:** `.github/workflows/documents-stress.yml`
**Schedule:** Daily at 2 AM UTC

**Purpose:**
- Concurrent load testing (10 workers, 20 requests/endpoint)
- Measure P50/P95/P99 latencies
- Verify 0×500 errors under load

**Endpoints Tested:**
| Endpoint | Method | Payload |
|----------|--------|---------|
| `/v1/actions/list?domain=documents` | GET | - |
| `/v1/actions/execute` | POST | `{action: "list_documents", ...}` |

**Note:** `get_document_url` excluded from stress testing (requires existing document_id). Tested in staging acceptance instead.

**Verdict Criteria:**
- PASS: 0×500 errors
- FAIL: Any 5xx response

**Environment Variables (GitHub Secrets):**
| Secret | Description |
|--------|-------------|
| `BASE_URL` | Staging API URL |
| `TENANT_SUPABASE_JWT_SECRET` | JWT secret for test tokens |
| `TENANT_SUPABASE_URL` | Tenant Supabase URL |
| `TEST_USER_YACHT_ID` | Test yacht UUID |

---

### 3. Health Tables

**Migration:** `docs/architecture/20_lens_ops/migrations/ops_health_tables.sql`
**Tables:** `pms_health_checks`, `pms_health_events`

**Schema:**
```sql
-- pms_health_checks
- id: uuid (PK)
- yacht_id: uuid (NOT NULL)
- lens_id: text (e.g., 'documents')
- status: text ('healthy', 'degraded', 'unhealthy')
- p95_latency_ms: integer
- error_rate_percent: numeric(5,2)
- sample_size: integer
- observed_at: timestamptz
- notes: jsonb

-- pms_health_events
- id: uuid (PK)
- check_id: uuid (FK → pms_health_checks)
- level: text ('info', 'warning', 'error')
- detail_json: jsonb
- created_at: timestamptz
```

**RLS Policies:**
- `yacht_scoped_health_checks`: Users see only their yacht's checks
- `service_role_write_health_checks`: Workers write via service role
- `yacht_scoped_health_events`: Events scoped via parent check
- `service_role_write_health_events`: Workers write events

**Helper Functions:**
- `get_latest_health_check(yacht_id, lens_id)`: Latest check for a lens
- `get_health_check_history(yacht_id, lens_id, hours)`: History (default 24h)
- `get_unhealthy_lenses(yacht_id)`: All degraded/unhealthy lenses

---

### 4. Feature Flags

**Documentation:** `docs/pipeline/DOCUMENTS_FEATURE_FLAGS.md`

**Flags:**
| Flag | Default | Purpose |
|------|---------|---------|
| `DOCUMENT_LENS_V2_ENABLED` | true | Master switch for Document Lens v2 |
| `DOCUMENT_LENS_SUGGESTIONS_ENABLED` | true | Action suggestions in `/list` |
| `DOCUMENT_LENS_SIGNED_ACTIONS_ENABLED` | true | Signature-required delete |

---

## Render Configuration

**render.yaml block:**
```yaml
- type: worker
  name: documents-health-worker
  runtime: python
  plan: starter
  region: oregon
  branch: main
  buildCommand: pip install requests PyJWT
  startCommand: python tools/ops/monitors/documents_health_worker.py
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

### Worker Deployment
- [ ] Blueprint sync in Render dashboard
- [ ] Add `SUPABASE_SERVICE_KEY` secret
- [ ] Add `TENANT_SUPABASE_JWT_SECRET` secret
- [ ] Deploy worker
- [ ] Verify first row in `pms_health_checks` (within 15 min)

### Verification Queries
```sql
-- Latest health check for documents lens
SELECT * FROM pms_health_checks
WHERE lens_id = 'documents'
ORDER BY observed_at DESC
LIMIT 1;

-- Recent errors
SELECT he.* FROM pms_health_events he
JOIN pms_health_checks hc ON he.check_id = hc.id
WHERE hc.lens_id = 'documents' AND he.level = 'error'
ORDER BY he.created_at DESC
LIMIT 10;
```

---

## Troubleshooting

### Worker Not Writing to DB
1. Check `SUPABASE_SERVICE_KEY` is set correctly
2. Verify `TENANT_SUPABASE_URL` points to tenant DB
3. Tail worker logs: `render logs -s documents-health-worker`

### Stress Test Failing
1. Check `TENANT_SUPABASE_JWT_SECRET` matches tenant
2. Verify `BASE_URL` is accessible
3. Review artifact: `verification_handoff/phase6/DOCUMENTS_STRESS_RESULTS.md`

### Health Check Shows Unhealthy
1. Check `notes` JSONB for specific failures
2. Query `pms_health_events` for error details
3. Verify feature flags are enabled

---

## Evidence Artifacts

| Artifact | Location |
|----------|----------|
| Stress test results | `verification_handoff/phase6/DOCUMENTS_STRESS_RESULTS.md` |
| Stress test JSON | `verification_handoff/phase6/DOCUMENTS_STRESS_RESULTS.json` |
| CI workflow artifacts | GitHub Actions → `documents-stress-results` |

---

## Related Files

| File | Purpose |
|------|---------|
| `docs/architecture/19_HOLISTIC_ACTIONS_LENS/DOCUMENT_LENS_V2/` | Lens architecture docs |
| `apps/api/handlers/document_handlers.py` | Handler implementations |
| `tests/ci/staging_documents_acceptance.py` | Staging acceptance tests |
| `.github/workflows/staging-documents-acceptance.yml` | CI workflow |

---

**Last Updated:** 2026-01-28
**Tag:** document-lens-gold (583b24a)
