# Document Lens v2 - Architecture Document

## Overview

Document Lens v2 provides role-gated document management with signature-required delete operations. Backend defines all actions, validation rules, and RLS enforcement.

**Tag:** `document-lens-gold` at commit `583b24a`
**Staging CI:** 17/17 tests passing
**Status:** Production-grade

---

## Actions Summary

| Action | Variant | Allowed Roles | Signature |
|--------|---------|---------------|-----------|
| `upload_document` | MUTATE | HOD roles | No |
| `update_document` | MUTATE | HOD roles | No |
| `add_document_tags` | MUTATE | HOD roles | No |
| `delete_document` | SIGNED | captain, manager | Yes |
| `get_document_url` | READ | All crew | No |
| `list_documents` | READ | All crew | No |

**HOD Roles:** chief_engineer, chief_officer, chief_steward, purser, captain, manager

---

## Key Files

| File | Purpose |
|------|---------|
| `apps/api/handlers/document_handlers.py` | Handler implementations |
| `apps/api/routes/p0_actions_routes.py` | Route definitions, role gating |
| `tests/ci/staging_documents_acceptance.py` | Staging CI tests |
| `.github/workflows/staging-documents-acceptance.yml` | CI workflow |

---

## Role Enforcement

### Mutation Actions (upload, update, tags)
```python
ALLOWED_ROLES = [
    "chief_engineer", "chief_officer", "chief_steward",
    "purser", "captain", "manager"
]
```

### Signed Actions (delete)
```python
ALLOWED_ROLES = ["captain", "manager"]
```

### Read Actions (get_url, list)
All authenticated users with valid yacht_id.

---

## Audit Log Invariants

| Action Type | signature Field |
|-------------|-----------------|
| Non-signed (upload, update, tags) | `{}` |
| Signed (delete) | `{signature_type, role_at_signing, signed_at, signature_hash}` |

---

## Deployment

**Commit:** 583b24a
**Tag:** document-lens-gold
**Workflow:** Staging Documents Acceptance (mark as required)
