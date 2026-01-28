# File Map (Updated: Document Lens v2)

This map reflects ACTUAL file locations. Updated after Document Lens v2 and ops infrastructure.

---

## Backend (Critical)

| File | Purpose | Notes |
|------|---------|-------|
| `apps/api/routes/p0_actions_routes.py` | **All action endpoints** including `/v1/actions/list` | NOT action_router/router.py |
| `apps/api/action_router/registry.py` | Action definitions, search, storage config | Extended with ActionVariant, domain, search_keywords |
| `apps/api/handlers/certificate_handlers.py` | Certificate CRUD handlers | Called by dispatcher |
| `apps/api/handlers/document_handlers.py` | Document CRUD handlers | Soft delete enabled |
| `apps/api/action_router/dispatchers/internal_dispatcher.py` | Routes to handlers | Bridge between router and handlers |

## Backend (Tests)

| File | Purpose | Notes |
|------|---------|-------|
| `tests/docker/run_rls_tests.py` | Docker-based role-gating tests | 18 tests including action list |
| `tests/ci/staging_certificates_acceptance.py` | Staging CI assertions | Real JWT validation |
| `tests/ci/staging_documents_acceptance.py` | Document lens staging tests | 17 tests, role-gated |
| `tests/stress/documents_actions_endpoints.py` | Document lens stress tests | P50/P95/P99 metrics |
| `.github/workflows/staging-certificates-acceptance.yml` | CI workflow | Mark as required on main |
| `.github/workflows/staging-documents-acceptance.yml` | Document lens CI | Mark as required on main |
| `.github/workflows/documents-stress.yml` | Nightly stress test | 2 AM UTC |

## Backend (Migrations)

| File | Purpose |
|------|---------|
| `supabase/migrations/20260125_006_fix_crew_certificates_rls.sql` | Crew certificate RLS |
| `supabase/migrations/20260125_007_vessel_certificates_rls.sql` | Vessel certificate RLS |
| `supabase/migrations/20260125_010_certificate_indexes.sql` | Performance indexes |
| `supabase/migrations/20260125_011_documents_storage_write_policies.sql` | Storage bucket policies |
| `supabase/migrations/20260125_012_doc_metadata_write_rls.sql` | Document metadata RLS |
| `supabase/migrations/20260126_013_drop_pms_audit_log_user_fk.sql` | Audit FK fix (MASTER/TENANT split) |
| `supabase/migrations/20260128_doc_metadata_soft_delete.sql` | Document soft delete columns |
| `docs/architecture/20_lens_ops/migrations/ops_health_tables.sql` | Health monitoring tables |

---

## Frontend (Critical)

| File | Purpose | Notes |
|------|---------|-------|
| `apps/web/src/lib/actionClient.ts` | Action execution + suggestions API | `executeAction()`, `getActionSuggestions()` |
| `apps/web/src/hooks/useCelesteSearch.ts` | Search hook with action detection | Detects "add certificate" intent |
| `apps/web/src/components/spotlight/SpotlightSearch.tsx` | Main search UI | Wires in SuggestedActions |
| `apps/web/src/components/SuggestedActions.tsx` | **NEW** - Renders action buttons | Backend-driven buttons |
| `apps/web/src/components/actions/ActionModal.tsx` | **NEW** - Action execution modal | Dynamic form + storage confirmation |

## Frontend (Config)

| File | Purpose |
|------|---------|
| `apps/web/package.json` | Dependencies (isomorphic-dompurify added) |
| `apps/web/package-lock.json` | Lockfile (commit this!) |

---

## Documentation

| File | Purpose |
|------|---------|
| `docs/pipeline/README.md` | Pipeline overview + reading order |
| `docs/pipeline/STAGES.md` | 7-stage process (includes frontend) |
| `docs/pipeline/LESSONS_LEARNED.md` | What went wrong and why |
| `docs/pipeline/ACTION_SUGGESTIONS_CONTRACT.md` | Contract for `GET /v1/actions/list` |
| `docs/pipeline/TEMPLATE_CHECKLIST.md` | Zero→Gold checklist |
| `docs/pipeline/TROUBLESHOOTING.md` | Common failures and fixes |
| `docs/pipeline/GUARDRAILS.md` | Non-negotiable rules |
| `docs/pipeline/ACCEPTANCE_MATRIX.md` | Test expectations |
| `docs/pipeline/RUNBOOK.md` | Commands to run |
| `docs/pipeline/DOCUMENTS_FEATURE_FLAGS.md` | Document lens feature flags |
| `docs/architecture/19_HOLISTIC_ACTIONS_LENS/DOCUMENT_LENS_V2/` | Document lens architecture |
| `docs/architecture/20_lens_ops/DOCUMENTS_LENS_OPS.md` | Document lens ops guide |
| `docs/architecture/20_lens_ops/WORKER_DEPLOYMENT_GUIDE.md` | Health worker deployment |
| `docs/architecture/20_lens_ops/OPS_OBSERVABILITY.md` | Monitoring and alerting |
| `CHANGELOG.md` | Release notes |

## Ops (Health Workers)

| File | Purpose |
|------|---------|
| `tools/ops/monitors/documents_health_worker.py` | Documents lens health worker |
| `render.yaml` | Render blueprint (includes health workers) |

---

## What to Ignore

- `apps/api/action_router/router.py` - Legacy, not mounted to app
- `apps/api/action_router/action_search.py` - Does not exist (wasn't needed)
- `apps/api/action_router/storage_semantics.py` - Does not exist (wasn't needed)
- Unrelated routes in `apps/api/routes/` unless debugging infrastructure
