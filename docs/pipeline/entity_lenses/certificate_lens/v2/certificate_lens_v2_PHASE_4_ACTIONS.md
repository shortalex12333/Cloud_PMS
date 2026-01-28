# Certificate Lens v2 - Phase 4: Micro-Actions Contract
**Status**: ACTIONS DEFINED
**Date**: 2026-01-25

---

## PURPOSE

This phase defines each micro-action with:
- Field classification (REQUIRED, OPTIONAL, BACKEND_AUTO, CONTEXT)
- Full SQL implementation
- Business rules
- RLS proof (or blocker)
- Ledger UI event

---

## BLOCKERS AFFECTING ACTIONS

| ID | Description | Actions Affected |
|----|-------------|------------------|
| **B1** | No RLS on `pms_vessel_certificates` | ALL vessel certificate actions |
| **B2** | Crew cert INSERT/UPDATE pending | `create_crew_certificate`, `update_crew_certificate` |

**Note**: Actions marked ⚠️ BLOCKED cannot be deployed until blockers resolved.

---

# ACTION 1: `create_vessel_certificate`

**Purpose**: Create a new vessel compliance certificate

**Status**: ⚠️ BLOCKED (B1)

**Allowed Roles**: HOD (captain, chief_engineer, chief_officer, purser, manager)

**Signature**: NO

**Gating**: Confirm dialog

---

## Field Classification

| Field | Table.Column | Classification | Source | Validation |
|-------|--------------|----------------|--------|------------|
| `certificate_type` | pms_vessel_certificates.certificate_type | REQUIRED | User dropdown | NOT NULL |
| `certificate_name` | pms_vessel_certificates.certificate_name | REQUIRED | User input | NOT NULL |
| `issuing_authority` | pms_vessel_certificates.issuing_authority | REQUIRED | User input | NOT NULL |
| `certificate_number` | pms_vessel_certificates.certificate_number | OPTIONAL | User input | - |
| `issue_date` | pms_vessel_certificates.issue_date | OPTIONAL | User date picker | Valid date |
| `expiry_date` | pms_vessel_certificates.expiry_date | OPTIONAL | User date picker | >= issue_date |
| `last_survey_date` | pms_vessel_certificates.last_survey_date | OPTIONAL | User date picker | Valid date |
| `next_survey_due` | pms_vessel_certificates.next_survey_due | OPTIONAL | User date picker | >= last_survey_date |
| `document_id` | pms_vessel_certificates.document_id | CONTEXT | From doc upload | FK exists check |
| `properties` | pms_vessel_certificates.properties | OPTIONAL | User JSON | Valid JSONB |
| `id` | pms_vessel_certificates.id | BACKEND_AUTO | gen_random_uuid() | - |
| `yacht_id` | pms_vessel_certificates.yacht_id | BACKEND_AUTO | get_user_yacht_id() | - |
| `status` | pms_vessel_certificates.status | BACKEND_AUTO | 'valid' | - |
| `created_at` | pms_vessel_certificates.created_at | BACKEND_AUTO | now() | - |

---

## Business Rules

1. **HOD Only**: Only officers with HOD-level roles can create certificates
2. **Yacht Scope**: Certificate belongs to user's current yacht only
3. **Date Logic**: If `expiry_date` provided and `issue_date` provided, `expiry_date` >= `issue_date`
4. **Document Optional**: Can create certificate without document, link later
5. **Unique Per Type**: Recommend unique constraint on (yacht_id, certificate_type, certificate_number) where number is not null

---

## Real SQL

```sql
-- create_vessel_certificate
-- BLOCKED: Requires RLS policies to be deployed first (B1)

BEGIN;

-- 1. Insert certificate
INSERT INTO pms_vessel_certificates (
    id,
    yacht_id,
    certificate_type,
    certificate_name,
    certificate_number,
    issuing_authority,
    issue_date,
    expiry_date,
    last_survey_date,
    next_survey_due,
    status,
    document_id,
    properties,
    created_at
) VALUES (
    gen_random_uuid(),
    public.get_user_yacht_id(),
    :certificate_type,                          -- REQUIRED: user input
    :certificate_name,                          -- REQUIRED: user input
    :certificate_number,                        -- OPTIONAL
    :issuing_authority,                         -- REQUIRED: user input
    :issue_date,                                -- OPTIONAL
    :expiry_date,                               -- OPTIONAL
    :last_survey_date,                          -- OPTIONAL
    :next_survey_due,                           -- OPTIONAL
    'valid',                                    -- BACKEND_AUTO: default
    :document_id,                               -- CONTEXT: from doc upload
    COALESCE(:properties, '{}'::jsonb),         -- OPTIONAL
    now()
)
RETURNING id INTO :new_certificate_id;

-- 2. Insert audit log
INSERT INTO pms_audit_log (
    id,
    yacht_id,
    entity_type,
    entity_id,
    action,
    user_id,
    old_values,
    new_values,
    signature,
    metadata,
    created_at
) VALUES (
    gen_random_uuid(),
    public.get_user_yacht_id(),
    'certificate',
    :new_certificate_id,
    'create_vessel_certificate',
    auth.uid(),
    NULL,                                       -- No old values for create
    jsonb_build_object(
        'certificate_type', :certificate_type,
        'certificate_name', :certificate_name,
        'issuing_authority', :issuing_authority,
        'expiry_date', :expiry_date
    ),
    '{}'::jsonb,                                -- Non-signature action
    jsonb_build_object(
        'source', 'certificate_lens',
        'session_id', :session_id
    ),
    now()
);

COMMIT;
```

---

## RLS Proof

**Required Policy** (PROPOSED - not deployed):
```sql
CREATE POLICY cert_insert_hod ON pms_vessel_certificates
    FOR INSERT TO authenticated
    WITH CHECK (
        yacht_id = public.get_user_yacht_id()
        AND get_user_role() = ANY (ARRAY['captain', 'chief_engineer', 'chief_officer', 'purser', 'manager'])
    );
```

**Status**: ⚠️ BLOCKED until B1 resolved

---

## Ledger UI Event

```json
{
  "event": "certificate_created",
  "message": "Class Certificate 'Lloyds Class A' created",
  "entity_type": "certificate",
  "entity_id": "uuid-here",
  "user_name": "Captain Smith",
  "timestamp": "2026-01-25T10:30:00Z",
  "metadata": {
    "certificate_type": "class",
    "expiry_date": "2027-01-25"
  }
}
```

---

# ACTION 2: `create_crew_certificate`

**Purpose**: Create a new crew member certificate (STCW, ENG1, etc.)

**Status**: ⚠️ BLOCKED (B2 - pending migration)

**Allowed Roles**: HOD (captain, chief_engineer, purser, manager)

**Signature**: NO

**Gating**: Confirm dialog

---

## Field Classification

| Field | Table.Column | Classification | Source | Validation |
|-------|--------------|----------------|--------|------------|
| `person_name` | pms_crew_certificates.person_name | REQUIRED | User input / crew select | NOT NULL |
| `certificate_type` | pms_crew_certificates.certificate_type | REQUIRED | User dropdown | NOT NULL |
| `certificate_number` | pms_crew_certificates.certificate_number | OPTIONAL | User input | - |
| `issuing_authority` | pms_crew_certificates.issuing_authority | OPTIONAL | User input | - |
| `issue_date` | pms_crew_certificates.issue_date | OPTIONAL | User date picker | Valid date |
| `expiry_date` | pms_crew_certificates.expiry_date | OPTIONAL | User date picker | >= issue_date |
| `document_id` | pms_crew_certificates.document_id | CONTEXT | From doc upload | FK exists check |
| `person_node_id` | pms_crew_certificates.person_node_id | CONTEXT | From crew focus | FK exists check |
| `properties` | pms_crew_certificates.properties | OPTIONAL | User JSON | Valid JSONB |
| `id` | pms_crew_certificates.id | BACKEND_AUTO | gen_random_uuid() | - |
| `yacht_id` | pms_crew_certificates.yacht_id | BACKEND_AUTO | get_user_yacht_id() | - |
| `created_at` | pms_crew_certificates.created_at | BACKEND_AUTO | now() | - |

---

## Business Rules

1. **HOD Only**: Officers with captain, chief_engineer, purser, or manager roles
2. **Person Required**: `person_name` must be provided (either typed or from crew focus)
3. **Certificate Type Required**: Must specify what kind of certificate
4. **Optional Person Link**: `person_node_id` links to crew entity if available
5. **Yacht Scope**: Certificate belongs to current yacht only

---

## Real SQL

```sql
-- create_crew_certificate
-- BLOCKED: Requires migration 20260125_006 to be deployed (B2)

BEGIN;

-- 1. Insert certificate
INSERT INTO pms_crew_certificates (
    id,
    yacht_id,
    person_name,
    person_node_id,
    certificate_type,
    certificate_number,
    issuing_authority,
    issue_date,
    expiry_date,
    document_id,
    properties,
    created_at
) VALUES (
    gen_random_uuid(),
    public.get_user_yacht_id(),
    :person_name,                               -- REQUIRED: user input
    :person_node_id,                            -- CONTEXT: from crew focus
    :certificate_type,                          -- REQUIRED: user dropdown
    :certificate_number,                        -- OPTIONAL
    :issuing_authority,                         -- OPTIONAL
    :issue_date,                                -- OPTIONAL
    :expiry_date,                               -- OPTIONAL
    :document_id,                               -- CONTEXT: from doc upload
    COALESCE(:properties, '{}'::jsonb),         -- OPTIONAL
    now()
)
RETURNING id INTO :new_certificate_id;

-- 2. Insert audit log
INSERT INTO pms_audit_log (
    id,
    yacht_id,
    entity_type,
    entity_id,
    action,
    user_id,
    old_values,
    new_values,
    signature,
    metadata,
    created_at
) VALUES (
    gen_random_uuid(),
    public.get_user_yacht_id(),
    'certificate',
    :new_certificate_id,
    'create_crew_certificate',
    auth.uid(),
    NULL,
    jsonb_build_object(
        'person_name', :person_name,
        'certificate_type', :certificate_type,
        'expiry_date', :expiry_date
    ),
    '{}'::jsonb,
    jsonb_build_object(
        'source', 'certificate_lens',
        'session_id', :session_id
    ),
    now()
);

COMMIT;
```

---

## RLS Proof

**Required Policy** (in pending migration 20260125_006):
```sql
CREATE POLICY "officers_insert_crew_certificates" ON pms_crew_certificates
    FOR INSERT TO authenticated
    WITH CHECK (
        yacht_id = public.get_user_yacht_id()
        AND get_user_role() = ANY (ARRAY['captain', 'chief_engineer', 'purser', 'manager'])
    );
```

**Status**: ⚠️ Policy exists but migration not deployed

---

## Ledger UI Event

```json
{
  "event": "certificate_created",
  "message": "STCW certificate created for John Smith",
  "entity_type": "certificate",
  "entity_id": "uuid-here",
  "user_name": "Chief Engineer",
  "timestamp": "2026-01-25T11:00:00Z",
  "metadata": {
    "person_name": "John Smith",
    "certificate_type": "stcw",
    "expiry_date": "2028-01-25"
  }
}
```

---

# ACTION 3: `update_certificate`

**Purpose**: Update certificate details (any field except id, yacht_id)

**Status**: ⚠️ BLOCKED (B1 for vessel, B2 for crew)

**Allowed Roles**: HOD (captain, chief_engineer, chief_officer, purser, manager)

**Signature**: NO

**Gating**: Confirm dialog

---

## Field Classification

| Field | Table.Column | Classification | Source | Validation |
|-------|--------------|----------------|--------|------------|
| `certificate_id` | *.id | CONTEXT | From focused cert | UUID exists |
| `certificate_type` | *.certificate_type | OPTIONAL | User edit | NOT NULL |
| `certificate_name` | pms_vessel_certificates.certificate_name | OPTIONAL | User edit | NOT NULL if vessel |
| `person_name` | pms_crew_certificates.person_name | OPTIONAL | User edit | NOT NULL if crew |
| `certificate_number` | *.certificate_number | OPTIONAL | User edit | - |
| `issuing_authority` | *.issuing_authority | OPTIONAL | User edit | - |
| `issue_date` | *.issue_date | OPTIONAL | User edit | Valid date |
| `expiry_date` | *.expiry_date | OPTIONAL | User edit | >= issue_date |
| `status` | *.status | OPTIONAL | User dropdown | Valid status |
| `properties` | *.properties | OPTIONAL | User edit | Valid JSONB |

---

## Business Rules

1. **Cannot Change Yacht**: `yacht_id` is immutable
2. **Cannot Change ID**: `id` is immutable
3. **Status Transitions**: If status changed manually, must be valid value
4. **Audit Old Values**: Must capture previous state in audit log
5. **Apply to Correct Table**: Based on certificate type (vessel vs crew)

---

## Real SQL (Vessel)

```sql
-- update_vessel_certificate
-- BLOCKED: Requires RLS policies (B1)

BEGIN;

-- 1. Capture old values
SELECT
    certificate_type,
    certificate_name,
    certificate_number,
    issuing_authority,
    issue_date,
    expiry_date,
    status,
    document_id,
    properties
INTO :old_values
FROM pms_vessel_certificates
WHERE id = :certificate_id
  AND yacht_id = public.get_user_yacht_id();

-- 2. Update certificate
UPDATE pms_vessel_certificates
SET
    certificate_type = COALESCE(:certificate_type, certificate_type),
    certificate_name = COALESCE(:certificate_name, certificate_name),
    certificate_number = COALESCE(:certificate_number, certificate_number),
    issuing_authority = COALESCE(:issuing_authority, issuing_authority),
    issue_date = COALESCE(:issue_date, issue_date),
    expiry_date = COALESCE(:expiry_date, expiry_date),
    last_survey_date = COALESCE(:last_survey_date, last_survey_date),
    next_survey_due = COALESCE(:next_survey_due, next_survey_due),
    status = COALESCE(:status, status),
    document_id = COALESCE(:document_id, document_id),
    properties = COALESCE(:properties, properties)
WHERE id = :certificate_id
  AND yacht_id = public.get_user_yacht_id();

-- 3. Insert audit log
INSERT INTO pms_audit_log (
    id,
    yacht_id,
    entity_type,
    entity_id,
    action,
    user_id,
    old_values,
    new_values,
    signature,
    metadata,
    created_at
) VALUES (
    gen_random_uuid(),
    public.get_user_yacht_id(),
    'certificate',
    :certificate_id,
    'update_certificate',
    auth.uid(),
    to_jsonb(:old_values),
    jsonb_build_object(
        'certificate_type', COALESCE(:certificate_type, :old_values.certificate_type),
        'expiry_date', COALESCE(:expiry_date, :old_values.expiry_date),
        'status', COALESCE(:status, :old_values.status)
    ),
    '{}'::jsonb,
    jsonb_build_object(
        'source', 'certificate_lens',
        'session_id', :session_id
    ),
    now()
);

COMMIT;
```

---

## Ledger UI Event

```json
{
  "event": "certificate_updated",
  "message": "Class Certificate updated: expiry_date changed to 2027-06-01",
  "entity_type": "certificate",
  "entity_id": "uuid-here",
  "user_name": "Captain Smith",
  "timestamp": "2026-01-25T12:00:00Z",
  "metadata": {
    "changed_fields": ["expiry_date"],
    "old_expiry_date": "2027-01-01",
    "new_expiry_date": "2027-06-01"
  }
}
```

---

# ACTION 4: `supersede_certificate`

**Purpose**: Mark existing certificate as superseded and create replacement

**Status**: ⚠️ BLOCKED (B1 for vessel)

**Allowed Roles**: HOD (captain, chief_engineer, manager)

**Signature**: **YES** (required)

**Gating**: Confirm dialog + Signature capture

---

## Field Classification

| Field | Table.Column | Classification | Source |
|-------|--------------|----------------|--------|
| `old_certificate_id` | *.id | CONTEXT | From focused cert |
| `new_certificate_name` | *.certificate_name | REQUIRED | User input |
| `new_certificate_number` | *.certificate_number | OPTIONAL | User input |
| `new_issuing_authority` | *.issuing_authority | REQUIRED | User input |
| `new_issue_date` | *.issue_date | OPTIONAL | User input |
| `new_expiry_date` | *.expiry_date | OPTIONAL | User input |
| `new_document_id` | *.document_id | CONTEXT | From new doc upload |
| `signature_payload` | pms_audit_log.signature | REQUIRED | Signature capture |

---

## Business Rules

1. **Signature Required**: Cannot supersede without captured signature
2. **Old Status Changes**: Old certificate status → 'superseded'
3. **New Status Valid**: New certificate status = 'valid'
4. **Same Type**: New certificate inherits `certificate_type` from old
5. **Audit Both**: Audit log entries for BOTH old and new certificates
6. **Yacht Match**: Both certificates must belong to same yacht

---

## Real SQL

```sql
-- supersede_vessel_certificate
-- BLOCKED: Requires RLS policies (B1)
-- SIGNATURE REQUIRED

BEGIN;

-- 1. Verify old certificate exists and get type
SELECT certificate_type, certificate_name
INTO :old_type, :old_name
FROM pms_vessel_certificates
WHERE id = :old_certificate_id
  AND yacht_id = public.get_user_yacht_id()
  AND status != 'superseded';

IF NOT FOUND THEN
    RAISE EXCEPTION 'Certificate not found or already superseded';
END IF;

-- 2. Mark old certificate as superseded
UPDATE pms_vessel_certificates
SET status = 'superseded'
WHERE id = :old_certificate_id
  AND yacht_id = public.get_user_yacht_id();

-- 3. Create new certificate
INSERT INTO pms_vessel_certificates (
    id,
    yacht_id,
    certificate_type,
    certificate_name,
    certificate_number,
    issuing_authority,
    issue_date,
    expiry_date,
    status,
    document_id,
    properties,
    created_at
) VALUES (
    gen_random_uuid(),
    public.get_user_yacht_id(),
    :old_type,                                  -- Inherit from old
    :new_certificate_name,
    :new_certificate_number,
    :new_issuing_authority,
    :new_issue_date,
    :new_expiry_date,
    'valid',
    :new_document_id,
    COALESCE(:properties, '{}'::jsonb),
    now()
)
RETURNING id INTO :new_certificate_id;

-- 4. Audit log for supersession (SIGNED)
INSERT INTO pms_audit_log (
    id,
    yacht_id,
    entity_type,
    entity_id,
    action,
    user_id,
    old_values,
    new_values,
    signature,
    metadata,
    created_at
) VALUES (
    gen_random_uuid(),
    public.get_user_yacht_id(),
    'certificate',
    :old_certificate_id,
    'supersede_certificate',
    auth.uid(),
    jsonb_build_object(
        'status', 'valid',
        'certificate_name', :old_name
    ),
    jsonb_build_object(
        'status', 'superseded',
        'superseded_by', :new_certificate_id
    ),
    :signature_payload::jsonb,                  -- REQUIRED: actual signature
    jsonb_build_object(
        'source', 'certificate_lens',
        'new_certificate_id', :new_certificate_id,
        'session_id', :session_id
    ),
    now()
);

-- 5. Audit log for new certificate creation
INSERT INTO pms_audit_log (
    id,
    yacht_id,
    entity_type,
    entity_id,
    action,
    user_id,
    old_values,
    new_values,
    signature,
    metadata,
    created_at
) VALUES (
    gen_random_uuid(),
    public.get_user_yacht_id(),
    'certificate',
    :new_certificate_id,
    'create_certificate',
    auth.uid(),
    NULL,
    jsonb_build_object(
        'certificate_type', :old_type,
        'certificate_name', :new_certificate_name,
        'supersedes', :old_certificate_id
    ),
    '{}'::jsonb,                                -- Create doesn't need signature
    jsonb_build_object(
        'source', 'certificate_lens',
        'supersedes_certificate_id', :old_certificate_id,
        'session_id', :session_id
    ),
    now()
);

COMMIT;
```

---

## Signature Payload Format

```json
{
  "signed_by": "uuid-user-id",
  "signed_at": "2026-01-25T14:00:00Z",
  "signature_type": "typed_name",
  "signature_value": "Captain John Smith",
  "acknowledgment": "I confirm this certificate supersession is authorized",
  "ip_address": "192.168.1.100",
  "user_agent": "Mozilla/5.0..."
}
```

---

## Ledger UI Event

```json
{
  "event": "certificate_superseded",
  "message": "Class Certificate superseded: 'Lloyds Class A (2024)' replaced by 'Lloyds Class A (2026)'",
  "entity_type": "certificate",
  "entity_id": "old-cert-uuid",
  "user_name": "Captain Smith",
  "timestamp": "2026-01-25T14:00:00Z",
  "metadata": {
    "old_certificate_name": "Lloyds Class A (2024)",
    "new_certificate_name": "Lloyds Class A (2026)",
    "new_certificate_id": "new-cert-uuid",
    "signed": true
  }
}
```

---

# ACTION 5: `link_document_to_certificate`

**Purpose**: Attach an uploaded document to an existing certificate

**Status**: ⚠️ BLOCKED (B1 for vessel)

**Allowed Roles**: HOD (captain, chief_engineer, purser, manager)

**Signature**: NO

**Gating**: Confirm dialog

---

## Field Classification

| Field | Table.Column | Classification | Source |
|-------|--------------|----------------|--------|
| `certificate_id` | *.id | CONTEXT | From focused cert |
| `document_id` | *.document_id | REQUIRED | From doc_metadata after upload |

---

## Business Rules

1. **Document Must Exist**: `document_id` must reference valid doc_metadata row
2. **Same Yacht**: Document and certificate must belong to same yacht
3. **Replaces Previous**: If certificate already has document_id, this replaces it
4. **Audit Previous**: If replacing, capture old document_id in audit

---

## Real SQL

```sql
-- link_document_to_vessel_certificate
-- BLOCKED: Requires RLS policies (B1)

BEGIN;

-- 1. Verify document exists and same yacht
SELECT id INTO :verified_doc_id
FROM doc_metadata
WHERE id = :document_id
  AND yacht_id = public.get_user_yacht_id();

IF NOT FOUND THEN
    RAISE EXCEPTION 'Document not found or wrong yacht';
END IF;

-- 2. Get current document_id (may be NULL)
SELECT document_id INTO :old_document_id
FROM pms_vessel_certificates
WHERE id = :certificate_id
  AND yacht_id = public.get_user_yacht_id();

-- 3. Update certificate
UPDATE pms_vessel_certificates
SET document_id = :document_id
WHERE id = :certificate_id
  AND yacht_id = public.get_user_yacht_id();

-- 4. Audit log
INSERT INTO pms_audit_log (
    id,
    yacht_id,
    entity_type,
    entity_id,
    action,
    user_id,
    old_values,
    new_values,
    signature,
    metadata,
    created_at
) VALUES (
    gen_random_uuid(),
    public.get_user_yacht_id(),
    'certificate',
    :certificate_id,
    'link_document',
    auth.uid(),
    jsonb_build_object('document_id', :old_document_id),
    jsonb_build_object('document_id', :document_id),
    '{}'::jsonb,
    jsonb_build_object(
        'source', 'certificate_lens',
        'session_id', :session_id
    ),
    now()
);

COMMIT;
```

---

## Ledger UI Event

```json
{
  "event": "document_linked",
  "message": "Document 'class-certificate-2026.pdf' linked to Class Certificate",
  "entity_type": "certificate",
  "entity_id": "cert-uuid",
  "user_name": "Purser",
  "timestamp": "2026-01-25T15:00:00Z",
  "metadata": {
    "document_filename": "class-certificate-2026.pdf",
    "document_id": "doc-uuid"
  }
}
```

---

# ACTION 6: `view_certificate_history`

**Purpose**: View audit trail for a certificate (read-only escape hatch)

**Status**: ✅ READY (SELECT policies exist)

**Allowed Roles**: All Crew (read-only)

**Signature**: NO

**Tables Written**: None (read-only)

---

## Real SQL

```sql
-- view_certificate_history
-- Works for both vessel and crew certificates

SELECT
    a.id AS audit_id,
    a.action,
    a.old_values,
    a.new_values,
    CASE
        WHEN a.signature = '{}'::jsonb THEN false
        ELSE true
    END AS was_signed,
    a.created_at,
    (SELECT name FROM auth_users_profiles WHERE id = a.user_id) AS performed_by,
    a.metadata
FROM pms_audit_log a
WHERE a.entity_type = 'certificate'
  AND a.entity_id = :certificate_id
  AND a.yacht_id = public.get_user_yacht_id()
ORDER BY a.created_at DESC
LIMIT 50;
```

---

# ACTIONS SUMMARY

| # | Action | Tables Written | Signature | Status | Blocker |
|---|--------|---------------|-----------|--------|---------|
| 1 | `create_vessel_certificate` | vessel_certs, audit | NO | ⚠️ BLOCKED | B1 |
| 2 | `create_crew_certificate` | crew_certs, audit | NO | ⚠️ BLOCKED | B2 |
| 3 | `update_certificate` | *_certs, audit | NO | ⚠️ BLOCKED | B1/B2 |
| 4 | `supersede_certificate` | vessel_certs, audit | **YES** | ⚠️ BLOCKED | B1 |
| 5 | `link_document` | *_certs, audit | NO | ⚠️ BLOCKED | B1/B2 |
| 6 | `view_certificate_history` | None (read) | NO | ✅ READY | - |

---

**ACTIONS STATUS**: ✅ DEFINED - Proceed to Phase 5

---

**END OF PHASE 4**
