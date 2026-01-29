# Document Lens v2 - Final Sign-Off Checklist

**Status:** Conditional Greenlight
**Tag:** `document-lens-gold`
**Branch:** `security/signoff`

---

## Pre-Requisites (Must Complete)

### 1. Apply Migrations

| Migration | Purpose | Status |
|-----------|---------|--------|
| `20260128_doc_metadata_soft_delete.sql` | Soft delete columns | ⬜ Pending |
| `20260128_staged_mutations.sql` | Two-phase commit | ⬜ Pending |

**Commands:**
```bash
# Connect to tenant database
psql "${TENANT_DATABASE_URL}"

# Apply soft delete migration
\i supabase/migrations/20260128_doc_metadata_soft_delete.sql

# Apply staged mutations migration
\i supabase/migrations/20260128_staged_mutations.sql

# Verify columns added
\d doc_metadata
\d pms_staged_mutations
```

**Expected Output:**
```
doc_metadata:
  - deleted_at (timestamptz)
  - deleted_by (uuid)
  - deleted_reason (text)
  - system_path (text)
  - tags (text[])

pms_staged_mutations:
  - id, idempotency_token, yacht_id, user_id, action_id
  - preview_hash, payload, preview_data
  - status, created_at, expires_at, committed_at
```

---

### 2. Deploy Health Worker

| Step | Action | Status |
|------|--------|--------|
| Blueprint Sync | Render Dashboard → Blueprints → Sync | ⬜ |
| Add Secrets | Add to `documents-health-worker` | ⬜ |
| Deploy | Manual deploy or wait for autoDeploy | ⬜ |
| Verify | Check `pms_health_checks` row | ⬜ |

**Required Secrets:**
```
SUPABASE_SERVICE_KEY = <tenant service role key>
TENANT_SUPABASE_JWT_SECRET = <tenant JWT secret>
```

**Verification Query (run after 20 min):**
```sql
SELECT id, status, p95_latency_ms, error_rate_percent, observed_at
FROM pms_health_checks
WHERE lens_id = 'documents'
ORDER BY observed_at DESC
LIMIT 1;
```

**Expected:**
```
status: healthy
p95_latency_ms: < 500
error_rate_percent: 0.00
observed_at: <within last 20 min>
```

---

### 3. Smoke Tests

#### A. Soft Delete Path

```bash
# 1. Create test document (HOD role)
curl -X POST "${API_URL}/v1/actions/execute" \
  -H "Authorization: Bearer ${HOD_JWT}" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "upload_document",
    "context": {"yacht_id": "'${YACHT_ID}'"},
    "payload": {"filename": "test-delete.pdf", "content_type": "application/pdf"}
  }'

# 2. Verify document visible
curl -X POST "${API_URL}/v1/actions/execute" \
  -H "Authorization: Bearer ${HOD_JWT}" \
  -d '{"action": "list_documents", "context": {"yacht_id": "'${YACHT_ID}'"}, "payload": {}}'
# → Should include test-delete.pdf

# 3. Delete document (Captain role with signature)
curl -X POST "${API_URL}/v1/actions/execute" \
  -H "Authorization: Bearer ${CAPTAIN_JWT}" \
  -d '{
    "action": "delete_document",
    "context": {"yacht_id": "'${YACHT_ID}'"},
    "payload": {
      "document_id": "<doc_id>",
      "reason": "Test cleanup",
      "signature": {"signature_type": "captain_delete", "role_at_signing": "captain"}
    }
  }'

# 4. Verify document hidden from default list
curl -X POST "${API_URL}/v1/actions/execute" \
  -H "Authorization: Bearer ${HOD_JWT}" \
  -d '{"action": "list_documents", "context": {"yacht_id": "'${YACHT_ID}'"}, "payload": {}}'
# → Should NOT include test-delete.pdf

# 5. Verify deleted_at set in DB
psql -c "SELECT id, deleted_at, deleted_by FROM doc_metadata WHERE filename = 'test-delete.pdf';"
```

#### B. Staged Mutation Path

```sql
-- 1. Stage a mutation
SELECT * FROM stage_mutation(
  '<yacht_id>'::uuid,
  '<user_id>'::uuid,
  'test_action',
  '{"test": "payload"}'::jsonb,
  '{"preview": "data"}'::jsonb,
  15
);
-- Returns: idempotency_token, preview_hash, expires_at

-- 2. Commit the mutation
SELECT * FROM commit_mutation(
  '<token_from_step_1>',
  '<hash_from_step_1>',
  '<user_id>'::uuid
);
-- Returns: success=true, payload, error_message=null

-- 3. Verify idempotent (same result on retry)
SELECT * FROM commit_mutation(
  '<token_from_step_1>',
  '<hash_from_step_1>',
  '<user_id>'::uuid
);
-- Returns: success=true (idempotent)

-- 4. Verify status updated
SELECT status, committed_at FROM pms_staged_mutations WHERE idempotency_token = '<token>';
-- status=committed, committed_at=<timestamp>
```

---

### 4. Run Security Audit

```bash
cd /path/to/repo
python scripts/security/audit_service_role_usage.py
```

**Expected Output:**
```
✅ AUDIT PASSED: All service role usages have yacht validation
```

**If failures, review and add yacht_id validation to flagged files.**

---

## Verification Summary

| Check | Criteria | Status |
|-------|----------|--------|
| Migrations Applied | Both tables created | ⬜ |
| Worker Running | Health check row exists | ⬜ |
| Soft Delete Works | deleted_at set, excluded from READ | ⬜ |
| Staged Mutations | Prepare/commit/idempotent | ⬜ |
| Security Audit | No unvalidated service clients | ⬜ |
| Staging CI Green | All acceptance tests pass | ✅ |
| Stress CI Green | 0×500 errors | ✅ |

---

## Sign-Off Criteria

**All boxes checked → Document Lens v2 Production Ready**

| Criterion | Required | Status |
|-----------|----------|--------|
| Staging Documents Acceptance | 17/17 pass | ✅ |
| Stress Test | 0×500 errors | ✅ |
| Migrations Applied | Both complete | ⬜ |
| Health Worker Live | Row in DB | ⬜ |
| Soft Delete Verified | Smoke test pass | ⬜ |
| Staged Mutations Verified | Idempotent commit | ⬜ |
| Security Audit Clean | No flags | ⬜ |

---

## Documentation Index

| Document | Purpose | Location |
|----------|---------|----------|
| Architecture | Lens design | `docs/architecture/19_HOLISTIC_ACTIONS_LENS/DOCUMENT_LENS_V2/` |
| Ops Guide | Worker + monitoring | `docs/architecture/20_lens_ops/DOCUMENTS_LENS_OPS.md` |
| Deployment Guide | Render setup | `docs/architecture/20_lens_ops/WORKER_DEPLOYMENT_GUIDE.md` |
| Observability | SLOs + queries | `docs/architecture/20_lens_ops/OPS_OBSERVABILITY.md` |
| Evidence | Backlog completion | `docs/architecture/20_lens_ops/EXTENDED_BACKLOG_EVIDENCE.md` |
| Feature Flags | Toggle reference | `docs/pipeline/DOCUMENTS_FEATURE_FLAGS.md` |
| FILE_MAP | All file locations | `docs/pipeline/FILE_MAP.md` |
| CHANGELOG | Release notes | `CHANGELOG.md` |

---

## Post Sign-Off Actions

1. **Merge PR:** `security/signoff` → `main`
2. **Tag Release:** `git tag document-lens-v2-production`
3. **Update CHANGELOG:** Add production deployment note
4. **Monitor:** Watch `pms_health_checks` for 24h

---

**Prepared By:** Claude Opus 4.5
**Date:** 2026-01-29
