# Document Lens v2 - Engineer Handoff

## Summary

Document Lens v2 provides role-gated document management with 6 actions.

**Tag:** `document-lens-gold` at commit `583b24a`
**Staging CI:** 17/17 tests passing

---

## Actions

| Action | Variant | Purpose |
|--------|---------|---------|
| upload_document | MUTATE | Create metadata + signed upload URL |
| update_document | MUTATE | Edit document metadata |
| add_document_tags | MUTATE | Add/replace tags array |
| delete_document | SIGNED | Soft-delete with captain signature |
| get_document_url | READ | Generate signed download URL |
| list_documents | READ | Browse documents with filters |

---

## Key Files

| File | Lines | Purpose |
|------|-------|---------|
| `apps/api/handlers/document_handlers.py` | 1-600 | Handler implementations |
| `apps/api/routes/p0_actions_routes.py` | 4465-4510 | Route + role gating |
| `tests/ci/staging_documents_acceptance.py` | 1-407 | Staging tests |

---

## Lens Ops Files

| File | Purpose |
|------|---------|
| `tools/ops/monitors/documents_health_worker.py` | Render health worker |
| `tests/stress/documents_actions_endpoints.py` | Stress testing |
| `.github/workflows/documents-stress.yml` | Nightly stress CI |
| `docs/pipeline/DOCUMENTS_FEATURE_FLAGS.md` | Feature flags |

---

## Quick Stats

- 6 document actions
- 3 variants (READ, MUTATE, SIGNED)
- 17 staging tests passing
- Yacht-isolated paths

**Tag:** document-lens-gold
