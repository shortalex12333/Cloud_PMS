# Entity Lens: Document
**Version**: v2 FINAL
**Status**: PRODUCTION READY (after migrations verified)
**Date**: 2026-01-28
**Gold Standard Reference**: `certificate_lens_v2_FINAL.md`

---

# EXECUTIVE SUMMARY

The Document Lens governs all operations for yacht documents including manuals, technical drawings, certificates (as files), photos, and any uploaded file. Documents are stored in Supabase storage with metadata tracked in `doc_metadata`.

## Key Metrics
| Metric | Value |
|--------|-------|
| Primary Tables | 1 (doc_metadata) |
| Actions Registered | 6 (3 MUTATE, 2 READ, 1 SIGNED) |
| Scenarios Documented | 8 |
| Blockers | 0 (RLS already deployed) |
| Migrations Required | 1 (indexes) |

---

# BLOCKERS

| ID | Description | Severity | Status | Resolution |
|----|-------------|----------|--------|------------|
| - | None | - | - | RLS policies exist from Equipment Lens v2 |

**Note**: `doc_metadata` RLS was deployed as part of Equipment Lens v2 migration `20260127_012_doc_metadata_write_rls.sql`.

---

# PART 0: CANONICAL HELPERS

## Yacht ID Resolution
```sql
public.get_user_yacht_id()
-- Returns UUID of current user's yacht
-- SECURITY DEFINER, STABLE
```

## Role Check (Canonical Helpers)
```sql
-- PREFERRED for write operations:
public.is_hod(auth.uid(), public.get_user_yacht_id())
-- Returns BOOLEAN: true if user has HOD role (captain, chief_engineer, chief_officer, purser, manager)

public.is_manager()
-- Returns BOOLEAN: true if user has manager role (for DELETE operations)
```

## Audit Entity Type
```sql
entity_type = 'document'
```

## Signature Invariant
```sql
-- Non-signature action:
signature = '{}'::jsonb

-- Signed action (delete_document):
signature = :signature_payload::jsonb
```
**NEVER** NULL. See APPENDIX: SIGNATURE PAYLOAD SCHEMA for exact structure.

---

# PART 1: DATABASE SCHEMA

## Table: `doc_metadata` (21 columns)

| Column | Type | Nullable | Classification | Notes |
|--------|------|----------|----------------|-------|
| `id` | uuid | NOT NULL | BACKEND_AUTO | PK, gen_random_uuid() |
| `yacht_id` | uuid | NOT NULL | BACKEND_AUTO | FK to yacht_registry |
| `source` | text | NOT NULL | BACKEND_AUTO | Upload source (manual, email, api) |
| `original_path` | text | YES | BACKEND_AUTO | Original file location |
| `filename` | text | NOT NULL | REQUIRED | File name |
| `content_type` | text | YES | BACKEND_AUTO | MIME type |
| `size_bytes` | bigint | YES | BACKEND_AUTO | File size |
| `sha256` | text | YES | BACKEND_AUTO | Checksum for dedup |
| `storage_path` | text | NOT NULL | BACKEND_AUTO | Cloud storage path |
| `equipment_ids` | uuid[] | YES | CONTEXT | Linked equipment. Default: '{}' |
| `tags` | text[] | YES | OPTIONAL | User tags. Default: '{}' |
| `indexed` | boolean | YES | BACKEND_AUTO | Is document indexed. Default: false |
| `indexed_at` | timestamptz | YES | BACKEND_AUTO | When indexed |
| `metadata` | jsonb | YES | OPTIONAL | Additional structured data |
| `created_at` | timestamptz | NOT NULL | BACKEND_AUTO | NOW() |
| `updated_at` | timestamptz | NOT NULL | BACKEND_AUTO | Trigger |
| `system_path` | text | YES | CONTEXT | Hierarchical path (e.g., "Engineering/Main Engine") |
| `doc_type` | text | YES | OPTIONAL | Document type (manual, drawing, certificate, photo) |
| `oem` | text | YES | OPTIONAL | OEM/Manufacturer |
| `model` | text | YES | OPTIONAL | Model reference |
| `system_type` | text | YES | OPTIONAL | System classification |

**Row Count**: ~2,759 (production)

## Field Classifications

| Classification | Fields |
|----------------|--------|
| REQUIRED | filename |
| OPTIONAL | tags, metadata, doc_type, oem, model, system_type |
| CONTEXT | equipment_ids, system_path |
| BACKEND_AUTO | id, yacht_id, source, original_path, content_type, size_bytes, sha256, storage_path, indexed, indexed_at, created_at, updated_at |

---

## Key Indexes

| Index | Columns | Purpose |
|-------|---------|---------|
| `idx_doc_metadata_yacht_id` | yacht_id | RLS filter |
| `idx_doc_metadata_equipment_ids` | equipment_ids (GIN) | Equipment lookup |
| `idx_doc_metadata_tags` | tags (GIN) | Tag filtering |
| `idx_doc_metadata_system_path` | system_path | Hierarchical navigation |
| `idx_doc_metadata_doc_type` | doc_type | Filter by type |
| `idx_doc_metadata_oem` | oem | Filter by manufacturer |
| `idx_doc_metadata_indexed` | indexed | Find unindexed docs |
| `idx_doc_metadata_created_at` | created_at | Recent uploads |

---

## RLS Policies (Deployed)

```sql
-- SELECT: All crew can view their yacht's documents
CREATE POLICY "Crew can view doc metadata"
    ON doc_metadata FOR SELECT TO authenticated
    USING (yacht_id = public.get_user_yacht_id());

-- INSERT: All crew can upload documents
CREATE POLICY "Crew can insert doc metadata"
    ON doc_metadata FOR INSERT TO authenticated
    WITH CHECK (yacht_id = public.get_user_yacht_id());

-- UPDATE: HOD only
CREATE POLICY "HOD can update doc metadata"
    ON doc_metadata FOR UPDATE TO authenticated
    USING (yacht_id = public.get_user_yacht_id())
    WITH CHECK (
        yacht_id = public.get_user_yacht_id()
        AND public.is_hod(auth.uid(), public.get_user_yacht_id())
    );

-- DELETE: Manager only
CREATE POLICY "Manager can delete doc metadata"
    ON doc_metadata FOR DELETE TO authenticated
    USING (
        yacht_id = public.get_user_yacht_id()
        AND public.is_manager()
    );

-- Service role bypass
CREATE POLICY "Service role doc metadata bypass"
    ON doc_metadata FOR ALL TO service_role
    USING (true) WITH CHECK (true);
```

---

# PART 2: MICRO-ACTIONS

## Action Summary

| # | Action | Tables Written | Signature | Allowed Roles |
|---|--------|---------------|-----------|---------------|
| 1 | `upload_document` | doc_metadata, audit | NO | HOD |
| 2 | `update_document` | doc_metadata, audit | NO | HOD |
| 3 | `add_document_tags` | doc_metadata, audit | NO | HOD |
| 4 | `link_document_to_equipment` | doc_metadata, audit | NO | HOD |
| 5 | `delete_document` | doc_metadata, audit | **YES** | Manager |
| 6 | `get_document_url` | None (read) | NO | All Crew |

## Role Permissions Matrix

| Role | View | Upload | Update | Add Tags | Link Equipment | Delete |
|------|------|--------|--------|----------|----------------|--------|
| Crew (deckhand, steward, etc.) | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Engineer | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Chief Officer | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| Chief Engineer | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| Purser | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| Captain | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ (signed) |
| Manager | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ (signed) |

**Guardrail**: Crew deny mutations by default. Only READ actions (view/download) are available to crew roles.

---

# PART 2B: ACTION ROUTER REGISTRATION

All document mutations are executed via the Action Router at `/v1/actions/execute`.

## Registered Actions

| Action ID | Endpoint | Handler | Allowed Roles | Required Fields |
|-----------|----------|---------|---------------|-----------------|
| `upload_document` | `/v1/documents/upload` | INTERNAL | crew, engineer, chief_engineer, captain, manager | yacht_id, filename, storage_path |
| `update_document` | `/v1/documents/update` | INTERNAL | chief_engineer, captain, manager | yacht_id, document_id |
| `add_document_tags` | `/v1/documents/add-tags` | INTERNAL | chief_engineer, captain, manager | yacht_id, document_id, tags |
| `link_document_to_equipment` | `/v1/documents/link-equipment` | INTERNAL | chief_engineer, captain, manager | yacht_id, document_id, equipment_id |
| `delete_document` | `/v1/documents/delete` | INTERNAL | captain, manager | yacht_id, document_id, **signature** |
| `get_document_url` | `/v1/documents/url` | INTERNAL | All Crew | yacht_id, document_id |

## Request Contract

```json
{
  "action": "upload_document",
  "context": {
    "yacht_id": "uuid"
  },
  "payload": {
    "filename": "Main_Engine_Manual.pdf",
    "storage_path": "{yacht_id}/documents/{document_id}/Main_Engine_Manual.pdf",
    "content_type": "application/pdf",
    "size_bytes": 2456789,
    "doc_type": "manual",
    "tags": ["engine", "caterpillar"],
    "system_path": "Engineering/Main Engine"
  }
}
```

## Role Mapping (Registry to RLS)

| Registry Role | RLS Function | DB Roles |
|---------------|--------------|----------|
| Crew | - (INSERT allowed) | crew, deckhand, steward, engineer |
| HOD | `is_hod()` | chief_engineer, captain, manager |
| Manager | `is_manager()` | captain, manager |

---

# PART 3: KEY SQL PATTERNS

## Upload Document
```sql
INSERT INTO doc_metadata (
    id, yacht_id, source, filename, content_type, size_bytes,
    storage_path, tags, doc_type, system_path, equipment_ids,
    metadata, created_at, updated_at
) VALUES (
    gen_random_uuid(),
    public.get_user_yacht_id(),
    'manual',
    :filename,
    :content_type,
    :size_bytes,
    :storage_path,
    COALESCE(:tags, '{}'),
    :doc_type,
    :system_path,
    COALESCE(:equipment_ids, '{}'),
    COALESCE(:metadata, '{}'::jsonb),
    now(),
    now()
)
RETURNING id;

-- Audit log (non-signature)
INSERT INTO pms_audit_log (
    id, yacht_id, entity_type, entity_id, action, user_id,
    old_values, new_values, signature, metadata, created_at
) VALUES (
    gen_random_uuid(),
    public.get_user_yacht_id(),
    'document',
    :new_id,
    'upload_document',
    auth.uid(),
    NULL,
    jsonb_build_object('filename', :filename, 'doc_type', :doc_type),
    '{}'::jsonb,
    jsonb_build_object('source', 'document_lens'),
    now()
);
```

## Update Document Metadata
```sql
UPDATE doc_metadata
SET
    doc_type = COALESCE(:doc_type, doc_type),
    oem = COALESCE(:oem, oem),
    model = COALESCE(:model, model),
    system_path = COALESCE(:system_path, system_path),
    system_type = COALESCE(:system_type, system_type),
    metadata = COALESCE(:metadata, metadata),
    updated_at = now()
WHERE id = :document_id
  AND yacht_id = public.get_user_yacht_id()
RETURNING *;

-- RLS enforces is_hod() for UPDATE
```

## Add Tags
```sql
UPDATE doc_metadata
SET
    tags = array_cat(tags, :new_tags),
    updated_at = now()
WHERE id = :document_id
  AND yacht_id = public.get_user_yacht_id()
RETURNING tags;

-- Deduplicate tags
UPDATE doc_metadata
SET tags = (SELECT ARRAY(SELECT DISTINCT unnest(tags)))
WHERE id = :document_id;
```

## Link Document to Equipment
```sql
UPDATE doc_metadata
SET
    equipment_ids = array_append(equipment_ids, :equipment_id::uuid),
    updated_at = now()
WHERE id = :document_id
  AND yacht_id = public.get_user_yacht_id()
  AND NOT (:equipment_id::uuid = ANY(equipment_ids))
RETURNING equipment_ids;
```

## Delete Document (SIGNED)
```sql
-- Mark for deletion (soft delete pattern) or hard delete
DELETE FROM doc_metadata
WHERE id = :document_id
  AND yacht_id = public.get_user_yacht_id();

-- Also delete from storage
-- DELETE FROM storage.objects WHERE name = :storage_path;

-- Audit log (SIGNED)
INSERT INTO pms_audit_log (
    id, yacht_id, entity_type, entity_id, action, user_id,
    old_values, new_values, signature, metadata, created_at
) VALUES (
    gen_random_uuid(),
    public.get_user_yacht_id(),
    'document',
    :document_id,
    'delete_document',
    auth.uid(),
    jsonb_build_object('filename', :old_filename, 'storage_path', :old_storage_path),
    NULL,
    :signature_payload::jsonb,
    jsonb_build_object('source', 'document_lens', 'reason', :reason),
    now()
);
```

## Get Signed URL (Read)
```sql
-- Get document metadata
SELECT id, filename, storage_path, content_type
FROM doc_metadata
WHERE id = :document_id
  AND yacht_id = public.get_user_yacht_id();

-- Generate signed URL via Supabase Storage API
-- storage.createSignedUrl(storage_path, expires_in_seconds)
```

## Search Documents by Equipment
```sql
SELECT
    d.id,
    d.filename,
    d.doc_type,
    d.oem,
    d.system_path,
    d.storage_path,
    d.tags,
    d.created_at
FROM doc_metadata d
WHERE :equipment_id = ANY(d.equipment_ids)
  AND d.yacht_id = public.get_user_yacht_id()
ORDER BY d.filename;
```

## Search Documents by Tags
```sql
SELECT id, filename, doc_type, system_path, tags
FROM doc_metadata
WHERE :tag = ANY(tags)
  AND yacht_id = public.get_user_yacht_id()
ORDER BY created_at DESC;
```

## Search Documents by OEM
```sql
SELECT id, filename, doc_type, model, system_path
FROM doc_metadata
WHERE oem ILIKE '%' || :oem || '%'
  AND yacht_id = public.get_user_yacht_id()
ORDER BY filename;
```

---

# PART 4: STORAGE PATH CONVENTION

**Bucket name**: `documents`

**Object path** (stored in `doc_metadata.storage_path`):
```
{yacht_id}/documents/{document_id}/{filename}
```

**Important**: Do NOT include `documents/` prefix in `storage_path` - the bucket name is already `documents`. The storage_path value should start with `{yacht_id}/...`.

**Examples**:
```
85fe1119-b04c-41ac-80f1-829d23322598/documents/a1b2c3d4/Main_Engine_Manual.pdf
85fe1119-b04c-41ac-80f1-829d23322598/documents/e5f6g7h8/Safety_Diagram.png
```

**RLS Note**: Storage policies use `storage.foldername(name)[1]` for yacht_id extraction (1-indexed array from path segments).

---

# PART 5: SCENARIOS SUMMARY

| # | Scenario | Query Example | Steps Saved |
|---|----------|---------------|-------------|
| 1 | Upload Manual | "upload main engine manual" | 40% |
| 2 | Find Equipment Docs | "show generator documents" | 55% |
| 3 | Search by Tag | "documents tagged safety" | 60% |
| 4 | Filter by OEM | "caterpillar manuals" | 50% |
| 5 | Link to Equipment | "link this doc to aux gen" | 45% |
| 6 | Add Tags | "tag document as maintenance" | 40% |
| 7 | Download Document | "download fire plan" | 35% |
| 8 | Delete Obsolete | "delete old manual" | 30% |

**Average**: 44% step reduction

---

# PART 6: ESCAPE HATCHES

| From Document | To Lens | Trigger |
|---------------|---------|---------|
| View linked equipment | Equipment Lens | Click equipment_id in equipment_ids array |
| View related certificate | Certificate Lens | If doc linked to certificate via document_id FK |
| Create work order | Work Order Lens | "Create WO for this document" (e.g., update manual) |

---

# PART 7: EDGE CASES & ERROR MAPPING

| Scenario | Expected HTTP | Error Code |
|----------|---------------|------------|
| Upload with duplicate filename | 200 (allowed) | - |
| Upload with existing sha256 | 200 (warn: possible duplicate) | POSSIBLE_DUPLICATE |
| Update non-existent document | 404 | DOCUMENT_NOT_FOUND |
| Link to non-existent equipment | 400 | EQUIPMENT_NOT_FOUND |
| Delete without signature | 400 | SIGNATURE_REQUIRED |
| Delete by non-manager | 403 | FORBIDDEN |
| Update by crew (non-HOD) | 403 | FORBIDDEN |
| Cross-yacht access | 403 (RLS blocks) | FORBIDDEN |
| Invalid storage path prefix | 400 | INVALID_STORAGE_PATH |

---

# PART 8: MIGRATIONS

## Required (P0)
None - RLS already deployed via `20260127_012_doc_metadata_write_rls.sql`

## Recommended (P1)
1. `20260128_200_doc_metadata_indexes.sql` - Performance indexes

## Migration: Index Creation

```sql
-- 20260128_200_doc_metadata_indexes.sql
DO $$
BEGIN
    -- Yacht ID index (RLS performance)
    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'idx_doc_metadata_yacht_id') THEN
        CREATE INDEX idx_doc_metadata_yacht_id ON doc_metadata(yacht_id);
        RAISE NOTICE 'Created idx_doc_metadata_yacht_id';
    END IF;

    -- Equipment IDs GIN index
    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'idx_doc_metadata_equipment_ids') THEN
        CREATE INDEX idx_doc_metadata_equipment_ids ON doc_metadata USING GIN(equipment_ids);
        RAISE NOTICE 'Created idx_doc_metadata_equipment_ids';
    END IF;

    -- Tags GIN index
    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'idx_doc_metadata_tags') THEN
        CREATE INDEX idx_doc_metadata_tags ON doc_metadata USING GIN(tags);
        RAISE NOTICE 'Created idx_doc_metadata_tags';
    END IF;

    -- Doc type index
    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'idx_doc_metadata_doc_type') THEN
        CREATE INDEX idx_doc_metadata_doc_type ON doc_metadata(doc_type);
        RAISE NOTICE 'Created idx_doc_metadata_doc_type';
    END IF;

    -- OEM index
    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'idx_doc_metadata_oem') THEN
        CREATE INDEX idx_doc_metadata_oem ON doc_metadata(oem);
        RAISE NOTICE 'Created idx_doc_metadata_oem';
    END IF;

    -- Created at index (recent uploads)
    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'idx_doc_metadata_created_at') THEN
        CREATE INDEX idx_doc_metadata_created_at ON doc_metadata(created_at DESC);
        RAISE NOTICE 'Created idx_doc_metadata_created_at';
    END IF;

    RAISE NOTICE 'SUCCESS: doc_metadata indexes verified/created';
END $$;
```

---

# PART 9: DEPLOYMENT CHECKLIST

## Pre-Deploy Verification
- [x] `get_user_yacht_id()` deployed
- [x] `is_hod()` deployed
- [x] `is_manager()` deployed
- [x] doc_metadata RLS enabled (from Equipment Lens v2)

## Verification Queries

### 1. RLS Enabled Check
```sql
SELECT relname, relrowsecurity FROM pg_class
WHERE relname = 'doc_metadata';
-- Should show TRUE
```

### 2. Policies Check
```sql
SELECT policyname, cmd FROM pg_policies
WHERE tablename = 'doc_metadata'
ORDER BY policyname;
-- Should show: Crew can view, Crew can insert, HOD can update, Manager can delete, Service role bypass
```

### 3. Yacht Isolation Test
```sql
-- As user from Yacht A, verify cannot see Yacht B's documents
SELECT COUNT(*) FROM doc_metadata WHERE yacht_id = 'yacht-b-uuid';
-- Should return 0
```

---

# PART 10: ACCEPTANCE TESTS

## Docker RLS Tests (`tests/docker/run_documents_rls_tests.py`)

| Test | Expected | HTTP Code |
|------|----------|-----------|
| CREW can view documents | PASS | 200 |
| CREW can upload document | PASS | 200 |
| CREW cannot update document | FAIL | 403 |
| HOD can update document | PASS | 200 |
| HOD can add tags | PASS | 200 |
| HOD can link equipment | PASS | 200 |
| HOD cannot delete document | FAIL | 403 |
| Manager can delete document (signed) | PASS | 200 |
| Delete without signature | FAIL | 400 |
| Cross-yacht read blocked | FAIL | 0 rows |
| Invalid equipment link | FAIL | 400 |

## Staging CI Tests (`tests/ci/staging_documents_acceptance.py`)

| Test | Assertion |
|------|-----------|
| HOD can upload | 200 |
| HOD can update | 200 |
| CREW cannot update | 403 |
| Invalid equipment link | 400 |
| Audit log created | Row exists |

---

# APPENDIX: SIGNATURE PAYLOAD SCHEMA

Signed actions (e.g., `delete_document`) must include a structured signature payload.

```json
{
  "user_id": "uuid",
  "role_at_signing": "captain|manager",
  "signature_type": "delete_document",
  "reason": "Document obsolete, replaced by newer version",
  "document_id": "uuid",
  "filename": "Old_Manual_v1.pdf",
  "signature_hash": "sha256:base64...",
  "signed_at": "2026-01-28T14:30:00Z"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `user_id` | uuid | YES | User performing the signed action |
| `role_at_signing` | text | YES | User's role at the moment of signing |
| `signature_type` | text | YES | Action being signed (e.g., `delete_document`) |
| `reason` | text | YES | Reason for deletion |
| `document_id` | uuid | YES | ID of document being deleted |
| `filename` | text | YES | Filename for audit trail |
| `signature_hash` | text | YES | Hash of the signed payload for verification |
| `signed_at` | timestamptz | YES | Timestamp of signature |

**Note**: For non-signed actions, `signature = '{}'::jsonb` (empty object, never NULL).

---

# APPENDIX: DOCUMENT TYPES

Recommended values for `doc_type`:

| Type | Description |
|------|-------------|
| `manual` | Equipment/system manuals |
| `drawing` | Technical drawings, schematics |
| `certificate` | Certificate scans (PDFs) |
| `photo` | Inspection photos, equipment images |
| `invoice` | Supplier invoices |
| `report` | Inspection reports, surveys |
| `specification` | Technical specifications |
| `procedure` | Operating procedures, checklists |
| `safety` | Safety plans, MSDS sheets |
| `other` | Uncategorized |

---

# APPENDIX: SINGLE-TENANT MODE

This database serves **one yacht**. All `yacht_id` values are equal in production. Each yacht has its own isolated database instance.

**Guardrails Still Required**:
- Role gating via `is_hod()` / `is_manager()` is the primary access control
- Signature invariant required on `delete_document`
- Storage prefixes: `{yacht_id}/documents/...` remains valuable for structure

---

**END OF DOCUMENT LENS v2 FINAL**
