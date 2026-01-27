# Changelog

All notable changes to CelesteOS PMS will be documented in this file.

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
