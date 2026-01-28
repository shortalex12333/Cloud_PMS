# Changelog

All notable changes to CelesteOS PMS will be documented in this file.

## [document-lens-gold] - 2026-01-28

### Added

**Backend**
- Document Lens v2 with 6 role-gated actions (upload, update, tags, delete, get_url, list)
- Soft delete support with `deleted_at`, `deleted_by`, `deleted_reason` columns
- `system_path` and `tags` columns with GIN indexes
- Signature-required delete action (captain/manager only)

**Ops Infrastructure**
- Health monitoring tables (`pms_health_checks`, `pms_health_events`)
- Documents health worker for Render background service
- Stress testing suite with P50/P95/P99 metrics
- Nightly stress CI workflow (`.github/workflows/documents-stress.yml`)

**Tests**
- Staging documents acceptance (17 tests passing)
- Docker RLS tests for document role-gating
- Stress test: 0×500 errors under concurrent load

**Documentation**
- `docs/architecture/19_HOLISTIC_ACTIONS_LENS/DOCUMENT_LENS_V2/` architecture docs
- `docs/architecture/20_lens_ops/DOCUMENTS_LENS_OPS.md` ops guide
- `docs/architecture/20_lens_ops/WORKER_DEPLOYMENT_GUIDE.md` deployment steps
- `docs/architecture/20_lens_ops/OPS_OBSERVABILITY.md` monitoring guide

### Fixed
- `test_v2_search_endpoint.py` no longer exits during pytest collection
- RLS policies updated to exclude soft-deleted documents by default

### Security
- SIGNED delete action requires captain/manager role + signature payload
- Soft delete preserves audit trail (deleted_by, deleted_reason logged)
- RLS enforces yacht isolation for health check queries

---

## [cert-lens-gold] - 2026-01-27

### Added

**Backend**
- `GET /v1/actions/list` endpoint with JWT validation and role-gated search
- `ActionVariant` enum (READ, MUTATE, SIGNED) for action classification
- Domain and search metadata for certificate actions
- `ACTION_STORAGE_CONFIG` for file-related actions (bucket, path templates)
- `get_storage_options()` and `search_actions()` helpers in registry

**Frontend**
- `getActionSuggestions()` client for fetching backend action suggestions
- `SuggestedActions` component renders backend-provided action buttons
- `ActionModal` component with dynamic form fields and storage confirmation
- Certificate action intent detection in `useCelesteSearch` hook

**Tests**
- Docker RLS tests for action list role-gating (HOD vs CREW)
- Staging CI assertions for action suggestions endpoint

### Fixed
- Domain filter in `search_actions()` now correctly excludes actions without matching domain
- Added missing `isomorphic-dompurify` dependency for email sanitization

### Security
- Role-based filtering applied server-side before returning action suggestions
- SIGNED actions (e.g., supersede_certificate) restricted to captain/manager roles
- Storage paths scoped to `{yacht_id}/certificates/` prefix
