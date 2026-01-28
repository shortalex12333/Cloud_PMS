# Entity Lens: Certificate (Vessel & Crew)
**Version**: v2 FINAL
**Status**: PRODUCTION READY (after migrations deployed)
**Date**: 2026-01-25
**Gold Standard Reference**: `fault_lens_v5_FINAL.md`

---

# EXECUTIVE SUMMARY

The Certificate Lens governs all operations for vessel compliance certificates (Class, ISM, ISPS, etc.) and crew qualification certificates (STCW, ENG1, licenses, etc.).

## Key Metrics
| Metric | Value |
|--------|-------|
| Primary Tables | 2 (pms_vessel_certificates, pms_crew_certificates) |
| Actions Registered | 5 mutations + READ handlers |
| Scenarios Documented | 10 |
| Average Step Reduction | 47.5% |
| Blockers | 4 (B1: vessel RLS, B2: crew RLS, B5: storage write, B6: doc_metadata write) |
| Migrations Ready | 7 |

---

# BLOCKERS

| ID | Description | Severity | Status | Resolution |
|----|-------------|----------|--------|------------|
| **B1** | `pms_vessel_certificates` has NO RLS | CRITICAL | Migration Ready | Deploy 20260125_007 |
| **B2** | Crew cert INSERT/UPDATE/DELETE pending | MEDIUM | Migration Ready | Deploy 20260125_006 |
| **B5** | Storage bucket missing write policies | MEDIUM | Migration Ready | Deploy 20260125_011 |
| **B6** | doc_metadata missing write policies | MEDIUM | Migration Ready | Deploy 20260125_012 |
| **B3** | No CHECK on `status` column | LOW | Optional | Deploy 20260125_008 |
| **B4** | No expiration trigger | LOW | Optional | Deploy 20260125_009 |

**Note**: All vessel certificate actions are DISABLED until B1 resolved. Service role bypasses RLS automatically.

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

-- AVAILABLE but prefer boolean helpers above:
public.get_user_role()
-- Returns TEXT: captain, chief_engineer, purser, manager, etc.
```

**Best Practice**: Use `is_hod()` and `is_manager()` in RLS policies instead of string comparisons. Boolean helpers are clearer and easier to maintain if role names change.

## Audit Entity Type
```sql
entity_type = 'certificate'
```

## Signature Invariant
```sql
-- Non-signature action:
signature = '{}'::jsonb

-- Signed action (supersede):
signature = :signature_payload::jsonb
```
**NEVER** NULL. See APPENDIX: SIGNATURE PAYLOAD SCHEMA for exact structure.

---

# PART 1: DATABASE SCHEMA

## Table: `pms_vessel_certificates` (14 columns)

| Column | Type | Nullable | Classification |
|--------|------|----------|----------------|
| `id` | uuid | NOT NULL | BACKEND_AUTO |
| `yacht_id` | uuid | NOT NULL | BACKEND_AUTO |
| `certificate_type` | text | NOT NULL | REQUIRED |
| `certificate_name` | text | NOT NULL | REQUIRED |
| `certificate_number` | text | YES | OPTIONAL |
| `issuing_authority` | text | NOT NULL | REQUIRED |
| `issue_date` | date | YES | OPTIONAL |
| `expiry_date` | date | YES | OPTIONAL |
| `last_survey_date` | date | YES | OPTIONAL |
| `next_survey_due` | date | YES | OPTIONAL |
| `status` | text | NOT NULL | BACKEND_AUTO |
| `document_id` | uuid | YES | CONTEXT |
| `properties` | jsonb | YES | OPTIONAL |
| `created_at` | timestamptz | NOT NULL | BACKEND_AUTO |

## Table: `pms_crew_certificates` (12 columns)

| Column | Type | Nullable | Classification |
|--------|------|----------|----------------|
| `id` | uuid | NOT NULL | BACKEND_AUTO |
| `yacht_id` | uuid | NOT NULL | BACKEND_AUTO |
| `person_name` | text | NOT NULL | REQUIRED |
| `person_node_id` | uuid | YES | CONTEXT |
| `certificate_type` | text | NOT NULL | REQUIRED |
| `certificate_number` | text | YES | OPTIONAL |
| `issuing_authority` | text | YES | OPTIONAL |
| `issue_date` | date | YES | OPTIONAL |
| `expiry_date` | date | YES | OPTIONAL |
| `document_id` | uuid | YES | CONTEXT |
| `properties` | jsonb | YES | OPTIONAL |
| `created_at` | timestamptz | NOT NULL | BACKEND_AUTO |

---

# PART 2: MICRO-ACTIONS

## Action Summary

| # | Action | Tables Written | Signature | Status |
|---|--------|---------------|-----------|--------|
| 1 | `create_vessel_certificate` | vessel_certs, audit | NO | ⚠️ B1 |
| 2 | `create_crew_certificate` | crew_certs, audit | NO | ⚠️ B2 |
| 3 | `update_certificate` | *_certs, audit | NO | ⚠️ B1/B2 |
| 4 | `supersede_certificate` | vessel_certs, audit | **YES** | ⚠️ B1 |
| 5 | `link_document` | *_certs, audit | NO | ⚠️ B1/B2 |
| 6 | `view_certificate_history` | None (read) | NO | ✅ READY |

## Role Permissions

| Role | View | Create | Update | Supersede | Delete |
|------|------|--------|--------|-----------|--------|
| Crew (deckhand, steward, etc.) | ✅ | ❌ | ❌ | ❌ | ❌ |
| Chief Officer | ✅ | ✅ | ✅ | ❌ | ❌ |
| Chief Engineer | ✅ | ✅ | ✅ | ✅ (signed) | ❌ |
| Purser | ✅ | ✅ | ✅ | ❌ | ❌ |
| Captain | ✅ | ✅ | ✅ | ✅ (signed) | ✅ |
| Manager | ✅ | ✅ | ✅ | ✅ (signed) | ✅ |

---

# PART 2B: ACTION ROUTER REGISTRATION

All certificate mutations are executed via the Action Router at `/v1/actions/execute`.

## Registered Actions

| Action ID | Endpoint | Handler | Allowed Roles | Required Fields |
|-----------|----------|---------|---------------|-----------------|
| `create_vessel_certificate` | `/v1/certificates/create-vessel` | INTERNAL | HOD, Manager | yacht_id, certificate_type, certificate_name, issuing_authority |
| `create_crew_certificate` | `/v1/certificates/create-crew` | INTERNAL | HOD, Manager | yacht_id, person_name, certificate_type, issuing_authority |
| `update_certificate` | `/v1/certificates/update` | INTERNAL | HOD, Manager | yacht_id, certificate_id |
| `link_document_to_certificate` | `/v1/certificates/link-document` | INTERNAL | HOD, Manager | yacht_id, certificate_id, document_id |
| `supersede_certificate` | `/v1/certificates/supersede` | INTERNAL | Captain, Manager | yacht_id, certificate_id, reason, **signature** |

## Request Contract

```json
{
  "action": "create_vessel_certificate",
  "context": {
    "yacht_id": "uuid"
  },
  "payload": {
    "certificate_type": "CLASS",
    "certificate_name": "Lloyd's Classification",
    "issuing_authority": "Lloyd's Register",
    "issue_date": "2026-01-15",
    "expiry_date": "2027-01-15"
  }
}
```

## Role Mapping (Registry → RLS)

| Registry Role | RLS Function | DB Roles |
|---------------|--------------|----------|
| HOD | `is_hod()` | chief_engineer, captain, manager |
| Manager | `is_manager()` | manager |
| Captain | `is_hod()` | captain |

**Note**: "Engineer" (non-chief) is NOT permitted for certificate mutations per RLS policies.

## Action Gating

| Action | Gating Class | Notes |
|--------|--------------|-------|
| `create_vessel_certificate` | STATE_CHANGING | Suggest, confirm if low confidence |
| `create_crew_certificate` | STATE_CHANGING | Suggest, confirm if low confidence |
| `update_certificate` | STATE_CHANGING | Suggest, confirm if low confidence |
| `link_document_to_certificate` | STATE_CHANGING | Suggest, confirm if low confidence |
| `supersede_certificate` | **GATED** | Always requires confirmation + signature |

---

# PART 3: KEY SQL PATTERNS

## Create Vessel Certificate
```sql
INSERT INTO pms_vessel_certificates (
    id, yacht_id, certificate_type, certificate_name,
    certificate_number, issuing_authority, issue_date,
    expiry_date, status, document_id, properties, created_at
) VALUES (
    gen_random_uuid(),
    public.get_user_yacht_id(),
    :certificate_type,
    :certificate_name,
    :certificate_number,
    :issuing_authority,
    :issue_date,
    :expiry_date,
    'valid',
    :document_id,
    COALESCE(:properties, '{}'::jsonb),
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
    'certificate',
    :new_id,
    'create_vessel_certificate',
    auth.uid(),
    NULL,
    jsonb_build_object('certificate_type', :certificate_type, 'certificate_name', :certificate_name),
    '{}'::jsonb,
    jsonb_build_object('source', 'certificate_lens'),
    now()
);
```

## Supersede Certificate (SIGNED)
```sql
-- Mark old as superseded
UPDATE pms_vessel_certificates
SET status = 'superseded'
WHERE id = :old_certificate_id
  AND yacht_id = public.get_user_yacht_id();

-- Create new certificate
INSERT INTO pms_vessel_certificates (...) VALUES (...) RETURNING id;

-- Audit log (SIGNED)
INSERT INTO pms_audit_log (..., signature, ...)
VALUES (..., :signature_payload::jsonb, ...);
```

## Expiring Certificates Query
```sql
SELECT 'vessel' AS category, id, certificate_name, expiry_date,
       (expiry_date - current_date) AS days_until_expiry
FROM pms_vessel_certificates
WHERE yacht_id = public.get_user_yacht_id()
  AND expiry_date <= current_date + INTERVAL '90 days'
  AND status != 'superseded'
UNION ALL
SELECT 'crew', id, person_name || ' - ' || certificate_type, expiry_date,
       (expiry_date - current_date)
FROM pms_crew_certificates
WHERE yacht_id = public.get_user_yacht_id()
  AND expiry_date <= current_date + INTERVAL '90 days'
ORDER BY days_until_expiry ASC;
```

---

# PART 4: RLS POLICIES

## pms_vessel_certificates (PROPOSED - Migration 007)
```sql
-- SELECT: All crew (yacht scope)
USING (yacht_id = public.get_user_yacht_id());

-- INSERT/UPDATE: HOD only (using boolean helper)
WITH CHECK (
    yacht_id = public.get_user_yacht_id()
    AND is_hod(auth.uid(), public.get_user_yacht_id())
);

-- DELETE: Manager only (using boolean helper)
USING (
    yacht_id = public.get_user_yacht_id()
    AND is_manager()
);
```

**Note**: Service role bypasses RLS automatically; no explicit policy needed.

## pms_crew_certificates (Migration 006)
```sql
-- SELECT: Deployed (yacht scope)
-- INSERT/UPDATE: Officers (captain, chief_engineer, purser, manager)
-- DELETE: Managers only (is_manager())
```

---

# PART 5: SCENARIOS SUMMARY

| # | Scenario | Steps Saved |
|---|----------|-------------|
| 1 | Create Class Certificate | 44% |
| 2 | Find Expiring Certificates | 62% |
| 3 | Supersede ISM Certificate | 42% |
| 4 | Add Crew STCW Certificate | 44% |
| 5 | View Certificate Document | 50% |
| 6 | Audit Trail Lookup | 57% |
| 7 | Bulk Status Check | 57% |
| 8 | Link Document | 44% |
| 9 | Crew Certificate List | 50% |
| 10 | Update After Survey | 25% |

**Average**: 47.5% step reduction

---

# PART 6: ESCAPE HATCHES

| From Certificate | To Lens | Trigger |
|------------------|---------|---------|
| View linked document | Document Lens | Click document_id |
| View crew member | Crew Lens | Click person_node_id |
| Create maintenance task | Work Order Lens | Future: equipment-linked |

---

# PART 7: MIGRATIONS

## Required (P0-P1)
1. `20260125_006_fix_crew_certificates_rls.sql` - Crew RLS enable + INSERT/UPDATE/DELETE
2. `20260125_007_vessel_certificates_rls.sql` - Vessel RLS (CRITICAL)
3. `20260125_011_documents_storage_write_policies.sql` - Storage INSERT/UPDATE/DELETE
4. `20260125_012_doc_metadata_write_rls.sql` - doc_metadata INSERT/UPDATE/DELETE

## Recommended (P2)
5. `20260125_010_certificate_indexes.sql` - Performance indexes

## Optional (P3)
6. `20260125_008_certificate_status_constraint.sql` - Status CHECK
7. `20260125_009_certificate_expiration_trigger.sql` - Auto-status

---

# PART 8: DEPLOYMENT CHECKLIST

## Pre-Deploy
- [ ] Backup database
- [ ] Verify `get_user_yacht_id()` deployed
- [ ] Verify `is_hod()` deployed
- [ ] Verify `is_manager()` deployed
- [ ] Test migrations on staging

## Deploy Order
1. [ ] 20260125_006 (crew RLS enable + policies)
2. [ ] 20260125_007 (vessel RLS)
3. [ ] 20260125_011 (storage write policies)
4. [ ] 20260125_012 (doc_metadata write policies)
5. [ ] 20260125_010 (indexes)
6. [ ] Optional: 008, 009

## Post-Deploy Verification

### 1. RLS Enabled Check
```sql
SELECT relname, relrowsecurity FROM pg_class
WHERE relname IN ('pms_vessel_certificates', 'pms_crew_certificates', 'doc_metadata');
-- All should show TRUE
```

### 2. Certificate Policies Check
```sql
SELECT tablename, policyname FROM pg_policies
WHERE tablename IN ('pms_vessel_certificates', 'pms_crew_certificates')
ORDER BY tablename, policyname;
-- Should show 4+ policies per table
```

### 3. Storage Write Policies Check
```sql
SELECT policyname FROM pg_policies
WHERE schemaname = 'storage' AND tablename = 'objects'
  AND policyname IN (
    'hod_insert_yacht_documents',
    'hod_update_yacht_documents',
    'manager_delete_yacht_documents'
  );
-- Should return 3 rows
```

### 4. doc_metadata Write Policies Check
```sql
SELECT policyname FROM pg_policies
WHERE tablename = 'doc_metadata'
  AND policyname IN (
    'crew_insert_doc_metadata',
    'hod_update_doc_metadata',
    'manager_delete_doc_metadata'
  );
-- Should return 3 rows
```

### 5. Yacht Isolation Test
```sql
-- As user from Yacht A, verify cannot see Yacht B's certificates
SELECT COUNT(*) FROM pms_vessel_certificates WHERE yacht_id = 'yacht-b-uuid';
-- Should return 0
```

## REST Acceptance Tests

### HOD Can Create Certificate
```http
POST /rest/v1/pms_vessel_certificates
Authorization: Bearer <hod_jwt>
Content-Type: application/json

{
  "certificate_type": "class",
  "certificate_name": "Lloyd's Register Class Certificate",
  "issuing_authority": "Lloyd's Register",
  "expiry_date": "2027-01-10"
}
-- Expect: 201 Created (HOD)
-- Expect: 403 Forbidden (Crew/Deckhand)
```

### Crew Cannot Create Certificate
```http
POST /rest/v1/pms_vessel_certificates
Authorization: Bearer <crew_jwt>
Content-Type: application/json

{
  "certificate_type": "class",
  "certificate_name": "Test",
  "issuing_authority": "Test"
}
-- Expect: 403 Forbidden
```

### HOD Can Link Document
```http
PATCH /rest/v1/pms_vessel_certificates?id=eq.{cert_id}
Authorization: Bearer <hod_jwt>
Content-Type: application/json

{
  "document_id": "{doc_id}"
}
-- Expect: 204 No Content (HOD)
-- Expect: 403 Forbidden (Crew)
```

### Manager Can Delete Certificate
```http
DELETE /rest/v1/pms_vessel_certificates?id=eq.{cert_id}
Authorization: Bearer <manager_jwt>
-- Expect: 204 No Content (Manager)
-- Expect: 403 Forbidden (HOD non-manager)
```

### Single-Tenant Assertion
```sql
-- Verify all tables have exactly 1 yacht_id (single-tenant invariant)
SELECT 'pms_vessel_certificates' AS tbl, COUNT(DISTINCT yacht_id) AS n
FROM pms_vessel_certificates WHERE yacht_id IS NOT NULL
UNION ALL
SELECT 'pms_crew_certificates', COUNT(DISTINCT yacht_id)
FROM pms_crew_certificates WHERE yacht_id IS NOT NULL;
-- Both should show n = 1 (or 0 if empty)
```

---

# APPENDIX: STATUS LIFECYCLE

```
valid (default)
    ↓ (expiry_date - 30 days)
due_soon
    ↓ (expiry_date passed)
expired
    ↓ (supersede action)
superseded (terminal)
```

## Supersede is Terminal - No Reversal

**Rule**: Once a certificate is `superseded`, it cannot be un-superseded.

**Rationale**: The audit ledger requires immutable history. Reversing supersession would break the chain of custody.

**Recovery Pattern**: If a supersede was done in error:
1. The superseded certificate remains `superseded` (immutable)
2. Create a new certificate with the correct details
3. Supersede the erroneously-created certificate (if any)
4. The audit log shows the full correction history

**Ledger View**:
```sql
-- View full certificate history including supersessions
SELECT
    al.created_at,
    al.action,
    al.user_id,
    al.old_values->>'status' AS old_status,
    al.new_values->>'status' AS new_status,
    al.signature
FROM pms_audit_log al
WHERE al.entity_type = 'certificate'
  AND al.entity_id = :certificate_id
ORDER BY al.created_at ASC;
```

---

# APPENDIX: SIGNATURE PAYLOAD SCHEMA

Signed actions (e.g., `supersede_certificate`) must include a structured signature payload in the audit log.

```json
{
  "user_id": "uuid",
  "role_at_signing": "captain|chief_engineer|manager",
  "signature_type": "supersede_certificate",
  "reason": "Renewal after expiry",
  "old_certificate_id": "uuid",
  "new_certificate_id": "uuid",
  "signature_hash": "sha256:base64...",
  "signed_at": "2026-01-25T14:30:00Z"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `user_id` | uuid | YES | User performing the signed action |
| `role_at_signing` | text | YES | User's role at the moment of signing |
| `signature_type` | text | YES | Action being signed (e.g., `supersede_certificate`) |
| `reason` | text | NO | Optional reason for the action |
| `old_certificate_id` | uuid | YES* | ID of certificate being superseded |
| `new_certificate_id` | uuid | YES* | ID of new certificate created |
| `signature_hash` | text | YES | Hash of the signed payload for verification |
| `signed_at` | timestamptz | YES | Timestamp of signature |

**Note**: For non-signed actions, `signature = '{}'::jsonb` (empty object, never NULL).

---

# APPENDIX: SINGLE-TENANT MODE

## Deployment Model

This database serves **one yacht**. All `yacht_id` values are equal in production. Each yacht has its own isolated database instance.

## Why Keep yacht_id Everywhere

| Reason | Explanation |
|--------|-------------|
| Forward compatibility | Multi-tenant expansion requires zero policy changes |
| Invariant preservation | Handlers and RLS use the same pattern regardless of mode |
| Audit clarity | Every row explicitly belongs to a yacht, even when there's only one |
| Defense in depth | Prevents accidental cross-tenant leaks if data is ever imported incorrectly |

## What Changes in Single-Tenant

| Control | Multi-Tenant | Single-Tenant |
|---------|--------------|---------------|
| RLS SELECT | Filters to user's yacht | Returns all rows (one yacht) |
| RLS INSERT/UPDATE | yacht_id + role gating | **Role gating is the actual control** |
| RLS DELETE | yacht_id + manager check | **Manager check is the actual control** |
| Unique indexes | Per-yacht uniqueness | Reduces to global uniqueness |

## Essential Guardrails (Still Required)

- **Role gating**: `is_hod()` / `is_manager()` checks are the primary access control
- **Signature invariant**: Required on signed actions; ledger correctness is independent of tenancy
- **Storage prefixes**: `documents/{yacht_id}/...` remains valuable for structure and auditability
- **Handler yacht_id**: Always set `yacht_id = public.get_user_yacht_id()` on INSERTs as backstop

## Tenant Assertion (Acceptance Test)

Run after imports/migrations to verify single-tenant assumption:
```sql
-- All core tables should have exactly 1 distinct yacht_id
SELECT 'pms_vessel_certificates' AS tbl, COUNT(DISTINCT yacht_id) AS yacht_count
FROM pms_vessel_certificates
UNION ALL
SELECT 'pms_crew_certificates', COUNT(DISTINCT yacht_id)
FROM pms_crew_certificates
UNION ALL
SELECT 'doc_metadata', COUNT(DISTINCT yacht_id)
FROM doc_metadata
UNION ALL
SELECT 'pms_audit_log', COUNT(DISTINCT yacht_id)
FROM pms_audit_log;
-- All rows should show yacht_count = 1 (or 0 if empty table)
```

---

# APPENDIX: DOCUMENT STORAGE PATH

**Bucket name**: `documents`

**Object path** (stored in `doc_metadata.storage_path`):
```
{yacht_id}/certificates/{certificate_id}/{filename}
```

**Important**: Do NOT include `documents/` prefix in `storage_path` - the bucket name is already `documents`. The storage_path value should start with `{yacht_id}/...`.

**RLS Note**: Path uses `storage.foldername(name)[1]` for yacht_id extraction (1-indexed array from path segments).

---

# PHASE FILES REFERENCE

| Phase | File | Lines |
|-------|------|-------|
| 0 | certificate_lens_v2_PHASE_0_EXTRACTION_GATE.md | 98 |
| 1 | certificate_lens_v2_PHASE_1_SCOPE.md | 220 |
| 2 | certificate_lens_v2_PHASE_2_DB_TRUTH.md | 280 |
| 3 | certificate_lens_v2_PHASE_3_ENTITY_GRAPH.md | 190 |
| 4 | certificate_lens_v2_PHASE_4_ACTIONS.md | 450 |
| 5 | certificate_lens_v2_PHASE_5_SCENARIOS.md | 480 |
| 6 | certificate_lens_v2_PHASE_6_SQL_BACKEND.md | 380 |
| 7 | certificate_lens_v2_PHASE_7_RLS_MATRIX.md | 260 |
| 8 | certificate_lens_v2_PHASE_8_GAPS_MIGRATIONS.md | 320 |

**Total Documentation**: ~2,700 lines across 10 files

---

**END OF CERTIFICATE LENS v2 FINAL**
