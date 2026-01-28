# Certificate Lens v2 - Phase 6: SQL & Backend Mapping
**Status**: SQL COMPLETE
**Date**: 2026-01-25

---

## PURPOSE

This phase consolidates all SQL patterns, transaction boundaries, and backend implementation details for Certificate Lens actions.

---

# CANONICAL PATTERNS

## 1. Yacht ID Resolution (ALWAYS USE)
```sql
public.get_user_yacht_id()
```
- Returns current user's yacht_id from auth_users_profiles
- SECURITY DEFINER - runs with elevated privileges
- STABLE - result doesn't change within transaction

## 2. Role Check
```sql
public.get_user_role()
```
- Returns current user's active role as TEXT
- Used in RLS WITH CHECK clauses

## 3. HOD Check
```sql
public.is_hod(auth.uid(), public.get_user_yacht_id())
```
- Returns BOOLEAN
- True if user has: captain, chief_engineer, or manager role

## 4. Audit Log Insert Pattern
```sql
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
    'certificate',           -- entity_type for this lens
    :entity_id,
    :action_name,
    auth.uid(),
    :old_values_jsonb,       -- NULL for create
    :new_values_jsonb,
    :signature_jsonb,        -- '{}' for non-signature, payload for signed
    :metadata_jsonb,
    now()
);
```

## 5. Signature Invariant
```sql
-- Non-signature action:
signature = '{}'::jsonb

-- Signed action (supersede, delete):
signature = :signature_payload::jsonb
```
**NEVER** use NULL for signature column (it's NOT NULL).

---

# TRANSACTION BOUNDARIES

## Single-Entity Actions
Actions that affect one certificate use implicit transactions (single statement) or explicit:

```sql
BEGIN;
-- UPDATE certificate
-- INSERT audit
COMMIT;
```

## Multi-Entity Actions (Supersede)
```sql
BEGIN;
-- UPDATE old certificate (status = 'superseded')
-- INSERT new certificate
-- INSERT audit for old
-- INSERT audit for new
COMMIT;
```
Rollback on any failure - no partial state.

---

# COMPLETE SQL BY ACTION

## Action 1: create_vessel_certificate

```sql
-- Handler: POST /api/certificates/vessel
-- Auth: Requires HOD role (captain, chief_engineer, chief_officer, purser, manager)
-- Status: BLOCKED (B1 - no RLS)

CREATE OR REPLACE FUNCTION api.create_vessel_certificate(
    p_certificate_type TEXT,
    p_certificate_name TEXT,
    p_issuing_authority TEXT,
    p_certificate_number TEXT DEFAULT NULL,
    p_issue_date DATE DEFAULT NULL,
    p_expiry_date DATE DEFAULT NULL,
    p_last_survey_date DATE DEFAULT NULL,
    p_next_survey_due DATE DEFAULT NULL,
    p_document_id UUID DEFAULT NULL,
    p_properties JSONB DEFAULT '{}'::jsonb,
    p_session_id UUID DEFAULT NULL
)
RETURNS UUID
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_new_id UUID;
    v_yacht_id UUID;
BEGIN
    -- Get yacht_id
    v_yacht_id := public.get_user_yacht_id();

    IF v_yacht_id IS NULL THEN
        RAISE EXCEPTION 'User not associated with a yacht';
    END IF;

    -- Verify HOD role
    IF NOT (get_user_role() = ANY (ARRAY['captain', 'chief_engineer', 'chief_officer', 'purser', 'manager'])) THEN
        RAISE EXCEPTION 'Insufficient permissions: HOD role required';
    END IF;

    -- Validate dates
    IF p_expiry_date IS NOT NULL AND p_issue_date IS NOT NULL AND p_expiry_date < p_issue_date THEN
        RAISE EXCEPTION 'Expiry date cannot be before issue date';
    END IF;

    -- Insert certificate
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
        v_yacht_id,
        p_certificate_type,
        p_certificate_name,
        p_certificate_number,
        p_issuing_authority,
        p_issue_date,
        p_expiry_date,
        p_last_survey_date,
        p_next_survey_due,
        'valid',
        p_document_id,
        COALESCE(p_properties, '{}'::jsonb),
        now()
    )
    RETURNING id INTO v_new_id;

    -- Audit log
    INSERT INTO pms_audit_log (
        id, yacht_id, entity_type, entity_id, action, user_id,
        old_values, new_values, signature, metadata, created_at
    ) VALUES (
        gen_random_uuid(),
        v_yacht_id,
        'certificate',
        v_new_id,
        'create_vessel_certificate',
        auth.uid(),
        NULL,
        jsonb_build_object(
            'certificate_type', p_certificate_type,
            'certificate_name', p_certificate_name,
            'issuing_authority', p_issuing_authority,
            'expiry_date', p_expiry_date
        ),
        '{}'::jsonb,
        jsonb_build_object('source', 'certificate_lens', 'session_id', p_session_id),
        now()
    );

    RETURN v_new_id;
END;
$$;
```

---

## Action 2: create_crew_certificate

```sql
-- Handler: POST /api/certificates/crew
-- Auth: Requires officer role
-- Status: BLOCKED (B2 - migration pending)

CREATE OR REPLACE FUNCTION api.create_crew_certificate(
    p_person_name TEXT,
    p_certificate_type TEXT,
    p_person_node_id UUID DEFAULT NULL,
    p_certificate_number TEXT DEFAULT NULL,
    p_issuing_authority TEXT DEFAULT NULL,
    p_issue_date DATE DEFAULT NULL,
    p_expiry_date DATE DEFAULT NULL,
    p_document_id UUID DEFAULT NULL,
    p_properties JSONB DEFAULT '{}'::jsonb,
    p_session_id UUID DEFAULT NULL
)
RETURNS UUID
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_new_id UUID;
    v_yacht_id UUID;
BEGIN
    v_yacht_id := public.get_user_yacht_id();

    IF v_yacht_id IS NULL THEN
        RAISE EXCEPTION 'User not associated with a yacht';
    END IF;

    -- Verify officer role
    IF NOT (get_user_role() = ANY (ARRAY['captain', 'chief_engineer', 'purser', 'manager'])) THEN
        RAISE EXCEPTION 'Insufficient permissions: officer role required';
    END IF;

    -- Validate dates
    IF p_expiry_date IS NOT NULL AND p_issue_date IS NOT NULL AND p_expiry_date < p_issue_date THEN
        RAISE EXCEPTION 'Expiry date cannot be before issue date';
    END IF;

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
        v_yacht_id,
        p_person_name,
        p_person_node_id,
        p_certificate_type,
        p_certificate_number,
        p_issuing_authority,
        p_issue_date,
        p_expiry_date,
        p_document_id,
        COALESCE(p_properties, '{}'::jsonb),
        now()
    )
    RETURNING id INTO v_new_id;

    INSERT INTO pms_audit_log (
        id, yacht_id, entity_type, entity_id, action, user_id,
        old_values, new_values, signature, metadata, created_at
    ) VALUES (
        gen_random_uuid(),
        v_yacht_id,
        'certificate',
        v_new_id,
        'create_crew_certificate',
        auth.uid(),
        NULL,
        jsonb_build_object(
            'person_name', p_person_name,
            'certificate_type', p_certificate_type,
            'expiry_date', p_expiry_date
        ),
        '{}'::jsonb,
        jsonb_build_object('source', 'certificate_lens', 'session_id', p_session_id),
        now()
    );

    RETURN v_new_id;
END;
$$;
```

---

## Action 4: supersede_vessel_certificate (SIGNED)

```sql
-- Handler: POST /api/certificates/vessel/supersede
-- Auth: Requires HOD role AND signature
-- Status: BLOCKED (B1)

CREATE OR REPLACE FUNCTION api.supersede_vessel_certificate(
    p_old_certificate_id UUID,
    p_new_certificate_name TEXT,
    p_new_certificate_number TEXT DEFAULT NULL,
    p_new_issuing_authority TEXT,
    p_new_issue_date DATE DEFAULT NULL,
    p_new_expiry_date DATE DEFAULT NULL,
    p_new_document_id UUID DEFAULT NULL,
    p_signature_payload JSONB,              -- REQUIRED for signed action
    p_session_id UUID DEFAULT NULL
)
RETURNS UUID
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_new_id UUID;
    v_yacht_id UUID;
    v_old_type TEXT;
    v_old_name TEXT;
    v_old_status TEXT;
BEGIN
    v_yacht_id := public.get_user_yacht_id();

    -- Verify signature provided
    IF p_signature_payload IS NULL OR p_signature_payload = '{}'::jsonb THEN
        RAISE EXCEPTION 'Signature required for supersede action';
    END IF;

    -- Verify HOD role
    IF NOT public.is_hod(auth.uid(), v_yacht_id) THEN
        RAISE EXCEPTION 'HOD role required for supersede';
    END IF;

    -- Get old certificate details
    SELECT certificate_type, certificate_name, status
    INTO v_old_type, v_old_name, v_old_status
    FROM pms_vessel_certificates
    WHERE id = p_old_certificate_id
      AND yacht_id = v_yacht_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Certificate not found';
    END IF;

    IF v_old_status = 'superseded' THEN
        RAISE EXCEPTION 'Certificate already superseded';
    END IF;

    -- Mark old as superseded
    UPDATE pms_vessel_certificates
    SET status = 'superseded'
    WHERE id = p_old_certificate_id
      AND yacht_id = v_yacht_id;

    -- Create new certificate
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
        v_yacht_id,
        v_old_type,                         -- Inherit type
        p_new_certificate_name,
        p_new_certificate_number,
        p_new_issuing_authority,
        p_new_issue_date,
        p_new_expiry_date,
        'valid',
        p_new_document_id,
        '{}'::jsonb,
        now()
    )
    RETURNING id INTO v_new_id;

    -- Audit: supersede action (SIGNED)
    INSERT INTO pms_audit_log (
        id, yacht_id, entity_type, entity_id, action, user_id,
        old_values, new_values, signature, metadata, created_at
    ) VALUES (
        gen_random_uuid(),
        v_yacht_id,
        'certificate',
        p_old_certificate_id,
        'supersede_certificate',
        auth.uid(),
        jsonb_build_object('status', v_old_status, 'certificate_name', v_old_name),
        jsonb_build_object('status', 'superseded', 'superseded_by', v_new_id),
        p_signature_payload,                -- SIGNED
        jsonb_build_object('source', 'certificate_lens', 'new_certificate_id', v_new_id, 'session_id', p_session_id),
        now()
    );

    -- Audit: new certificate creation
    INSERT INTO pms_audit_log (
        id, yacht_id, entity_type, entity_id, action, user_id,
        old_values, new_values, signature, metadata, created_at
    ) VALUES (
        gen_random_uuid(),
        v_yacht_id,
        'certificate',
        v_new_id,
        'create_certificate',
        auth.uid(),
        NULL,
        jsonb_build_object(
            'certificate_type', v_old_type,
            'certificate_name', p_new_certificate_name,
            'supersedes', p_old_certificate_id
        ),
        '{}'::jsonb,
        jsonb_build_object('source', 'certificate_lens', 'supersedes_certificate_id', p_old_certificate_id, 'session_id', p_session_id),
        now()
    );

    RETURN v_new_id;
END;
$$;
```

---

## Action 5: link_document_to_certificate

```sql
-- Handler: PATCH /api/certificates/:id/link-document
-- Auth: Requires HOD role
-- Status: BLOCKED (B1/B2)

CREATE OR REPLACE FUNCTION api.link_document_to_certificate(
    p_certificate_id UUID,
    p_document_id UUID,
    p_certificate_table TEXT,           -- 'vessel' or 'crew'
    p_session_id UUID DEFAULT NULL
)
RETURNS BOOLEAN
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_yacht_id UUID;
    v_old_doc_id UUID;
BEGIN
    v_yacht_id := public.get_user_yacht_id();

    -- Verify document exists and same yacht
    IF NOT EXISTS (
        SELECT 1 FROM doc_metadata
        WHERE id = p_document_id AND yacht_id = v_yacht_id
    ) THEN
        RAISE EXCEPTION 'Document not found or wrong yacht';
    END IF;

    IF p_certificate_table = 'vessel' THEN
        -- Get old document_id
        SELECT document_id INTO v_old_doc_id
        FROM pms_vessel_certificates
        WHERE id = p_certificate_id AND yacht_id = v_yacht_id;

        IF NOT FOUND THEN
            RAISE EXCEPTION 'Vessel certificate not found';
        END IF;

        -- Update
        UPDATE pms_vessel_certificates
        SET document_id = p_document_id
        WHERE id = p_certificate_id AND yacht_id = v_yacht_id;

    ELSIF p_certificate_table = 'crew' THEN
        SELECT document_id INTO v_old_doc_id
        FROM pms_crew_certificates
        WHERE id = p_certificate_id AND yacht_id = v_yacht_id;

        IF NOT FOUND THEN
            RAISE EXCEPTION 'Crew certificate not found';
        END IF;

        UPDATE pms_crew_certificates
        SET document_id = p_document_id
        WHERE id = p_certificate_id AND yacht_id = v_yacht_id;
    ELSE
        RAISE EXCEPTION 'Invalid certificate_table: must be vessel or crew';
    END IF;

    -- Audit
    INSERT INTO pms_audit_log (
        id, yacht_id, entity_type, entity_id, action, user_id,
        old_values, new_values, signature, metadata, created_at
    ) VALUES (
        gen_random_uuid(),
        v_yacht_id,
        'certificate',
        p_certificate_id,
        'link_document',
        auth.uid(),
        jsonb_build_object('document_id', v_old_doc_id),
        jsonb_build_object('document_id', p_document_id),
        '{}'::jsonb,
        jsonb_build_object('source', 'certificate_lens', 'certificate_table', p_certificate_table, 'session_id', p_session_id),
        now()
    );

    RETURN TRUE;
END;
$$;
```

---

# QUERY PATTERNS

## Search: Expiring Certificates (Unified)

```sql
-- Used by: Scenario 2, 7
-- Returns both vessel and crew certs

SELECT
    'vessel' AS category,
    c.id,
    c.certificate_type,
    c.certificate_name AS name,
    NULL AS person_name,
    c.expiry_date,
    c.status,
    (c.expiry_date - current_date) AS days_until_expiry
FROM pms_vessel_certificates c
WHERE c.yacht_id = public.get_user_yacht_id()
  AND c.expiry_date IS NOT NULL
  AND c.expiry_date <= current_date + INTERVAL '90 days'
  AND c.status != 'superseded'

UNION ALL

SELECT
    'crew' AS category,
    c.id,
    c.certificate_type,
    c.certificate_type AS name,
    c.person_name,
    c.expiry_date,
    'valid' AS status,
    (c.expiry_date - current_date) AS days_until_expiry
FROM pms_crew_certificates c
WHERE c.yacht_id = public.get_user_yacht_id()
  AND c.expiry_date IS NOT NULL
  AND c.expiry_date <= current_date + INTERVAL '90 days'

ORDER BY days_until_expiry ASC;
```

## Search: By Certificate Type

```sql
-- Used by: Scenario 3, 5
SELECT
    c.id,
    c.certificate_type,
    c.certificate_name,
    c.certificate_number,
    c.issuing_authority,
    c.expiry_date,
    c.status,
    d.filename AS document_filename,
    d.storage_path
FROM pms_vessel_certificates c
LEFT JOIN doc_metadata d ON c.document_id = d.id
WHERE c.yacht_id = public.get_user_yacht_id()
  AND c.certificate_type ILIKE '%' || :search_type || '%'
  AND c.status != 'superseded'
ORDER BY c.created_at DESC;
```

## Search: Crew Certificates by Person

```sql
-- Used by: Scenario 4, 9
SELECT
    c.id,
    c.person_name,
    c.certificate_type,
    c.certificate_number,
    c.issuing_authority,
    c.issue_date,
    c.expiry_date,
    CASE
        WHEN c.expiry_date IS NULL THEN 'no_expiry'
        WHEN c.expiry_date < current_date THEN 'expired'
        WHEN c.expiry_date <= current_date + INTERVAL '30 days' THEN 'due_soon'
        ELSE 'valid'
    END AS validity_status,
    d.filename AS document_filename
FROM pms_crew_certificates c
LEFT JOIN doc_metadata d ON c.document_id = d.id
WHERE c.yacht_id = public.get_user_yacht_id()
  AND c.person_name ILIKE '%' || :person_name || '%'
ORDER BY c.expiry_date NULLS LAST;
```

---

# DOCUMENT UPLOAD FLOW

## 1. Upload to Storage
```javascript
// Client-side or Edge Function
const path = `yacht/${yacht_id}/certificates/${certificate_id}/${filename}`;
const { data, error } = await supabase.storage
  .from('documents')
  .upload(path, file);
```

## 2. Create doc_metadata Record
```sql
INSERT INTO doc_metadata (
    id,
    yacht_id,
    source,
    filename,
    content_type,
    size_bytes,
    sha256,
    storage_path,
    tags,
    metadata,
    created_at,
    updated_at
) VALUES (
    gen_random_uuid(),
    public.get_user_yacht_id(),
    'certificate_upload',
    :filename,
    :content_type,
    :size_bytes,
    :sha256_hash,
    :storage_path,
    COALESCE(:tags, ARRAY[]::text[]),
    COALESCE(:metadata, '{}'::jsonb),
    now(),
    now()
)
RETURNING id;
```

## 3. Link to Certificate
```sql
-- Use link_document_to_certificate function
SELECT api.link_document_to_certificate(
    :certificate_id,
    :document_id,
    'vessel',  -- or 'crew'
    :session_id
);
```

---

# ERROR HANDLING

| Error Code | Condition | Message |
|------------|-----------|---------|
| `CERT_001` | User not on yacht | "User not associated with a yacht" |
| `CERT_002` | Insufficient role | "HOD role required" |
| `CERT_003` | Invalid dates | "Expiry date cannot be before issue date" |
| `CERT_004` | Not found | "Certificate not found" |
| `CERT_005` | Already superseded | "Certificate already superseded" |
| `CERT_006` | Signature missing | "Signature required for supersede action" |
| `CERT_007` | Document not found | "Document not found or wrong yacht" |

---

**SQL & BACKEND STATUS**: ✅ COMPLETE - Proceed to Phase 7

---

**END OF PHASE 6**
