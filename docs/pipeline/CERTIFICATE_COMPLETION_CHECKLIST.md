Certificate Lens: Completion Checklist (95% → 100%)
====================================================

Status: IN PROGRESS
Date: 2026-01-26

---

## Current State

| Component | Status | Evidence |
|-----------|--------|----------|
| Handler code | DONE | `apps/api/handlers/certificate_handlers.py` |
| Dispatcher guard | DONE | `internal_dispatcher.py:273-292` - ValueError on invalid doc |
| RLS policies | DONE | 7 migrations deployed |
| Docker tests | DONE | 15/15 PASS |
| CI workflow | DONE | `.github/workflows/staging-certificates-acceptance.yml` |
| CI test script | DONE | `tests/ci/staging_certificates_acceptance.py` |
| Staging redeploy | PENDING | Service running old code |
| CI required gate | PENDING | Not yet marked required on main |

---

## Root Cause (Staging 500)

**Problem**: `link_document_to_certificate` with invalid `document_id` returns 500 on staging.

**Why**: Staging is running old handler code that doesn't defensively check doc_metadata before linking. The current code (already in repo) does:

```python
# internal_dispatcher.py:286-291
dm = supabase.table("doc_metadata").select("id").eq("id", doc_id).maybe_single().execute()
if not getattr(dm, 'data', None):
    raise ValueError("document_id not found")  # → 400
```

**Fix**: Redeploy staging to pick up current code.

---

## Completion Steps

### Step 1: Verify GitHub Secrets

Ensure these secrets exist in repo settings for the CI workflow:

| Secret | Purpose |
|--------|---------|
| `BASE_URL` | Staging API base (e.g., `https://pipeline-core-staging.onrender.com`) |
| `MASTER_SUPABASE_URL` | MASTER Supabase URL |
| `MASTER_SUPABASE_ANON_KEY` | MASTER anon key (for login) |
| `MASTER_SUPABASE_SERVICE_ROLE_KEY` | MASTER service role (for admin user create) |
| `TENANT_SUPABASE_URL` | TENANT Supabase URL |
| `TENANT_SUPABASE_SERVICE_ROLE_KEY` | TENANT service role (for profile/role setup) |
| `TEST_USER_YACHT_ID` | Yacht UUID for test users |
| `STAGING_USER_PASSWORD` | Password for auto-provisioned test users |

---

### Step 2: Trigger Staging Redeploy

```bash
# Replace <service_id> and <deploy_key> with actual values from Render dashboard
curl -X POST "https://api.render.com/deploy/<service_id>?key=<deploy_key>"
```

Watch Render logs for:
- Service restart
- FastAPI boot
- Action router initialization

---

### Step 3: Verify Redeploy

#### 3a. Health check
```bash
curl -s "${BASE_URL}/health"
# Expect: 200 OK
```

#### 3b. Invalid doc link (the fix)
```bash
# Get HOD JWT first (via MASTER login)
curl -s -X POST "${BASE_URL}/v1/actions/execute" \
  -H "Authorization: Bearer ${HOD_JWT}" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "link_document_to_certificate",
    "context": {"yacht_id": "<YACHT_ID>"},
    "payload": {
      "certificate_id": "<ANY_CERT_ID>",
      "domain": "vessel",
      "document_id": "00000000-0000-0000-0000-000000000000"
    }
  }'
# Expect: 400 or 404 (NOT 500)
```

#### 3c. Update certificate (audit FK proof)
```bash
curl -s -X POST "${BASE_URL}/v1/actions/execute" \
  -H "Authorization: Bearer ${HOD_JWT}" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "update_certificate",
    "context": {"yacht_id": "<YACHT_ID>"},
    "payload": {
      "certificate_id": "<CERT_ID>",
      "domain": "vessel",
      "certificate_name": "Verification Update"
    }
  }'
# Expect: 200 (no 409 audit FK error)
```

---

### Step 4: Run CI Workflow

#### 4a. Manual trigger
```bash
gh workflow run "staging-certificates-acceptance.yml"
```

Or via GitHub UI: Actions → "Staging Certificates Acceptance" → Run workflow

#### 4b. Verify green
- All steps pass
- No 500 errors
- Invalid doc returns 400/404
- Update returns 200

---

### Step 5: Mark Workflow as Required

1. Go to: `Settings → Branches → Branch protection rules → main`
2. Edit or create rule for `main`
3. Enable: "Require status checks to pass before merging"
4. Add required check: `staging-certificates / staging-certificates`
5. Save

---

## Sign-off Criteria

| Criterion | Status |
|-----------|--------|
| Invalid document link returns 400/404 (not 500) | [ ] |
| Create/update paths return 200; no audit 409 | [ ] |
| CI workflow passes and is required on main | [ ] |
| No UI authority creep (frontend renders backend actions only) | [x] (verified in design) |

---

## Post-Completion

Once all boxes checked:

1. Update `docs/pipeline/README.md` status to "100% COMPLETE"
2. Mark Certificate lens as production-ready
3. Enable canary flags if not already
4. Proceed to next lens (Fault v5 recommended)

---

## Reference Files

| File | Purpose |
|------|---------|
| `apps/api/handlers/certificate_handlers.py` | Handler implementation |
| `apps/api/action_router/dispatchers/internal_dispatcher.py:273-292` | Document guard |
| `.github/workflows/staging-certificates-acceptance.yml` | CI workflow |
| `tests/ci/staging_certificates_acceptance.py` | CI test script |
| `docs/pipeline/certificate_lens/LENS.md` | Gold lens spec |

---

**END OF CHECKLIST**
