# Extended Overnight Backlog - Evidence Summary

**Date:** 2026-01-29
**Branch:** `security/signoff`
**Commit:** `2347997`

---

## Completed Tasks

### 1. Validation (CI Gates)

| Check | Status | Evidence |
|-------|--------|----------|
| Staging Documents Acceptance | ✅ Green | Run #21462549531 |
| Staging Certificates Acceptance | ✅ Green | Passing |
| Documents Stress Test | ✅ Green | 0×500 errors |

### 2. Lens Ops Hardening

**Worker Resilience Added:**
- Retries with exponential backoff (3 attempts, 500ms-5s)
- Error classification: `connectivity`, `client_4xx`, `server_5xx`, `timeout`, `unknown`
- Per-endpoint metrics in `notes` JSON
- Rate limiting: 100ms delay between requests
- Consecutive unhealthy tracking with alert at 2+

**SLO Monitoring:**
- Target p95 < 500ms
- Target error_rate < 1%
- Auto-log warnings on SLO breach

### 3. Schema Consistency

**Created:**
- `scripts/preflight/check_doc_metadata_schema.py` - Schema validation
- `supabase/migrations/20260128_staged_mutations.sql` - Two-phase mutations

**Migration Features:**
- Idempotent column adds (IF NOT EXISTS)
- GIN indexes for tags
- RLS policies for yacht/user isolation

### 4. Document Handlers Polish

**Changes:**
- `get_document_url` excludes soft-deleted documents
- Storage errors mapped to NOT_FOUND (clean frontend messaging)
- `list_documents` supports `include_deleted` param

### 5. Security Hardening

**Created:**
- `scripts/security/audit_service_role_usage.py`
- Scans for service role patterns
- Validates yacht_id validation exists
- Flags files missing yacht isolation

### 6. Two-Phase Mutations

**Table:** `pms_staged_mutations`

**Columns:**
- `idempotency_token` - Unique per mutation
- `preview_hash` - SHA256 for validation
- `payload` - Full mutation data
- `expires_at` - 15 minute default TTL

**Functions:**
- `stage_mutation()` - Create staged mutation
- `commit_mutation()` - Validate and commit
- `cleanup_expired_mutations()` - Periodic cleanup

### 7. Observability Updates

**Added to OPS_OBSERVABILITY.md:**
- SLO section with targets and thresholds
- Alert criteria (2 consecutive unhealthy)
- Alerting query for consecutive failures

---

## Files Created/Modified

### New Files

| File | Purpose |
|------|---------|
| `scripts/preflight/check_doc_metadata_schema.py` | Schema validation |
| `scripts/security/audit_service_role_usage.py` | Security audit |
| `supabase/migrations/20260128_staged_mutations.sql` | Two-phase mutations |

### Modified Files

| File | Changes |
|------|---------|
| `tools/ops/monitors/documents_health_worker.py` | Resilience, metrics, SLOs |
| `apps/api/handlers/document_handlers.py` | Soft delete, storage errors |
| `docs/architecture/20_lens_ops/OPS_OBSERVABILITY.md` | SLOs section |

---

## Pending Manual Actions

### Immediate (Render Dashboard)

1. **Blueprint Sync** - Pull `render.yaml` with health worker
2. **Add Worker Secrets:**
   - `SUPABASE_SERVICE_KEY`
   - `TENANT_SUPABASE_JWT_SECRET`
3. **Deploy Worker** - Verify first health check row

### Database Migrations

```bash
# Apply soft delete migration
psql < supabase/migrations/20260128_doc_metadata_soft_delete.sql

# Apply staged mutations (for two-phase flows)
psql < supabase/migrations/20260128_staged_mutations.sql
```

### Verification

```bash
# Check health worker
render logs -s documents-health-worker --tail 50

# Verify health check row
psql -c "SELECT * FROM pms_health_checks WHERE lens_id='documents' ORDER BY observed_at DESC LIMIT 1;"

# Run security audit
python scripts/security/audit_service_role_usage.py

# Run schema check
python scripts/preflight/check_doc_metadata_schema.py
```

---

## CI Status Summary

| Workflow | Status | Notes |
|----------|--------|-------|
| Staging Documents Acceptance | ✅ | 17/17 tests |
| Staging Certificates Acceptance | ✅ | Passing |
| Documents Stress Test | ✅ | 0×500 on security/signoff |
| Microaction Verification Suite | ⏳ | In progress |

---

## Next Steps

1. **Merge PR** - `security/signoff` → `main`
2. **Deploy Health Worker** - Render blueprint sync
3. **Apply Migrations** - Soft delete + staged mutations
4. **Monitor** - Check `pms_health_checks` for first row

---

**Handoff Complete**
