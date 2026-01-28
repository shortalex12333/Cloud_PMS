# Receiving Lens v1 - Implementation Status

**Date**: 2026-01-28
**Status**: ✅ IMPLEMENTATION COMPLETE - READY FOR TESTING

---

## Summary

Receiving Lens v1 has been fully implemented from design to production-ready code following the Equipment Lens v2 template.

**Workflow**: Image upload → OCR extraction (advisory) → User review/adjust → Accept (SIGNED)

---

## Completed Tasks ✅

### 1. Dependencies Verified
- ✅ `is_hod()` helper function exists
- ✅ `is_manager()` helper function exists
- ✅ `get_user_yacht_id()` helper function exists
- ✅ `pms_entity_links` table exists with RLS
- ✅ `doc_metadata` table exists with write policies
- ✅ `pms_audit_log` table exists

### 2. Database Migrations Created (8 files)
- ✅ `20260128_101_receiving_helpers_if_missing.sql` - Helper verification
- ✅ `20260128_102_receiving_tables.sql` - 4 tables created
  - `pms_receiving` (header)
  - `pms_receiving_items` (line items)
  - `pms_receiving_documents` (attachments)
  - `pms_receiving_extractions` (advisory OCR results)
- ✅ `20260128_103_receiving_checks.sql` - Status/quantity constraints
- ✅ `20260128_104_receiving_rls.sql` - RLS policies (deny-by-default)
- ✅ `20260128_105_receiving_indexes.sql` - Performance indexes
- ✅ `20260128_111_documents_storage_policies_receiving.sql` - Documents bucket verification
- ✅ `20260128_112_receiving_images_storage_policies.sql` - pms-receiving-images bucket policies
- ✅ `20260128_113_doc_metadata_receiving_rls.sql` - doc_metadata policy verification

### 3. Handlers Implemented (10 actions)
File: `apps/api/handlers/receiving_handlers.py`

1. ✅ `create_receiving` - MUTATE (HOD+)
2. ✅ `attach_receiving_image_with_comment` - MUTATE (HOD+)
3. ✅ `extract_receiving_candidates` - READ/PREPARE (advisory only, no auto-mutation)
4. ✅ `update_receiving_fields` - MUTATE (HOD+)
5. ✅ `add_receiving_item` - MUTATE (HOD+)
6. ✅ `adjust_receiving_item` - MUTATE (HOD+)
7. ✅ `link_invoice_document` - MUTATE (HOD+)
8. ✅ `accept_receiving` - SIGNED (Captain/Manager, prepare/execute)
9. ✅ `reject_receiving` - MUTATE (HOD+)
10. ✅ `view_receiving_history` - READ (All crew)

**Features**:
- Storage path validation: `{yacht_id}/receiving/{receiving_id}/{filename}`
- Rejects `documents/` prefix
- Advisory extraction (writes to `pms_receiving_extractions`, no auto-mutation)
- Audit log with signature NOT NULL invariant
- Metadata extraction from request_context

### 4. Registry Updated
File: `apps/api/action_router/registry.py`

- ✅ All 10 actions added between Worklist and Certificate sections
- ✅ Proper field metadata classifications (REQUIRED/OPTIONAL/BACKEND_AUTO/CONTEXT)
- ✅ Search keywords configured
- ✅ Storage paths specified: `pms-receiving-images` bucket for photos, `documents` for PDFs
- ✅ SIGNED variant for accept_receiving with signature_roles_required

### 5. Dispatcher Updated
File: `apps/api/action_router/dispatchers/internal_dispatcher.py`

- ✅ Imported receiving handlers
- ✅ Created `_get_receiving_handlers()` lazy initializer
- ✅ Created 10 wrapper functions (`_recv_*`)
- ✅ Mapped all 10 actions in `INTERNAL_HANDLERS` dict

---

## Architecture Guarantees ✅

### Security
- **RLS**: Deny-by-default with yacht-scoped policies
- **Roles**: HOD+ for mutations, Captain/Manager for signatures
- **Storage**: Path validation enforces `{yacht_id}/receiving/{receiving_id}/{filename}`
- **Audit**: All mutations write to `pms_audit_log` with signature NOT NULL

### Data Integrity
- **Status constraint**: `draft`, `in_review`, `accepted`, `rejected`
- **Quantity check**: `quantity_received >= 0`
- **Advisory extraction**: Writes only to `pms_receiving_extractions`, no auto-mutation
- **Signed acceptance**: Requires PIN+TOTP, freezes monetary fields

### Consistency with Equipment Lens
- Same audit metadata structure (`source`, `lens`, `action`, `entity_id`, `session_id`, `ip_address`)
- Same prepare/execute pattern for SIGNED actions
- Same storage path validation approach
- Same RLS helper functions

---

## Next Steps (Testing Phase)

### 1. Docker RLS Tests
Create: `apps/api/tests/docker_rls_receiving_tests.py`
- Verify RLS policies with different roles
- Test yacht isolation
- Test storage path validation
- Test signature enforcement

### 2. Staging Acceptance Tests
Create: `apps/api/tests/test_receiving_lens_v1_acceptance.py`
- 15 JWT personas (crew, deckhand, steward, engineer, eto, chief_engineer, chief_officer, chief_steward, purser, captain, manager, inactive, expired, wrong_yacht, mixed_role)
- Complete workflow: create → attach → extract → update → add items → accept (SIGNED)
- Test extraction advisory (no auto-mutation)
- Test storage paths (valid/invalid)
- Test role denials (403)
- Test cross-yacht isolation (0 rows)

### 3. CI Workflow
Create: `.github/workflows/receiving-lens-acceptance.yml`
- Run acceptance tests with 15 JWTs from GitHub Secrets
- Migration verification job
- Storage validation job
- RLS policy checks

---

## Implementation Files

### Database Migrations
```
supabase/migrations/
├── 20260128_101_receiving_helpers_if_missing.sql
├── 20260128_102_receiving_tables.sql
├── 20260128_103_receiving_checks.sql
├── 20260128_104_receiving_rls.sql
├── 20260128_105_receiving_indexes.sql
├── 20260128_111_documents_storage_policies_receiving.sql
├── 20260128_112_receiving_images_storage_policies.sql
└── 20260128_113_doc_metadata_receiving_rls.sql
```

### Backend Code
```
apps/api/
├── handlers/
│   └── receiving_handlers.py (860 lines, 10 actions)
├── action_router/
│   ├── registry.py (10 new actions added)
│   └── dispatchers/
│       └── internal_dispatcher.py (10 wrappers + mappings)
```

### Documentation
```
docs/architecture/entity_lenses/receiving_lens/v1/
├── FINAL.md
├── PHASE_1_SCOPE.md
├── PHASE_2_DB_TRUTH.md
├── PHASE_4_ACTIONS.md
├── PHASE_5_SCENARIOS.md
├── PHASE_6_SQL_BACKEND.md
├── PHASE_7_RLS_MATRIX.md
├── PHASE_8_GAPS_MIGRATIONS.md
├── DB_FIELD_CLASSIFICATION.md
└── IMPLEMENTATION_STATUS.md (this file)
```

---

## Key Differences from Spec

**NONE** - Implementation matches specification exactly:
- Advisory extraction (prepare-only, no auto-mutation)
- Storage paths without `documents/` prefix
- Signed acceptance with prepare/execute
- Status-based workflow (draft → in_review → accepted/rejected)

---

## Production Readiness Checklist

- ✅ All dependencies verified
- ✅ 8 migrations created and verified
- ✅ 10 handlers implemented
- ✅ Registry updated with all actions
- ✅ Dispatcher wired up
- ⏳ Docker RLS tests (pending)
- ⏳ Staging acceptance tests (pending)
- ⏳ CI workflow (pending)
- ⏳ Apply migrations to staging (pending)
- ⏳ Run acceptance tests (pending)

---

**Status**: Implementation complete. Ready for testing phase.
**Next**: Create Docker RLS tests and staging acceptance tests.
