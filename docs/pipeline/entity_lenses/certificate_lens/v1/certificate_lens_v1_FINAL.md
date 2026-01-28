# Entity Lens: Certificate

**Status**: v1 - PRODUCTION READY
**Last Updated**: 2026-01-25
**Schema Source**: Production Supabase Database (db_truth_snapshot.md)

---

# BLOCKERS

| ID | Blocker | Affects | Resolution |
|----|---------|---------|------------|
| ⚠️ | `pms_crew_certificates` missing INSERT/UPDATE policies | Crew cert management | Deploy RLS migration |

---

# PART 1: DATABASE SCHEMA

## Table: `pms_certificates` (Equipment/Vessel Certificates)

**Production DB Columns** (17 total):

| Column | PostgreSQL Type | Nullable | Classification | Notes |
|--------|-----------------|----------|----------------|-------|
| `id` | uuid | NOT NULL | BACKEND_AUTO | PK |
| `yacht_id` | uuid | NOT NULL | BACKEND_AUTO | FK → yacht_registry |
| `certificate_name` | text | NOT NULL | REQUIRED | Certificate title |
| `certificate_type` | text | NOT NULL | REQUIRED | Type classification |
| `certificate_number` | text | YES | OPTIONAL | Official number |
| `issuing_authority` | text | YES | OPTIONAL | Who issued |
| `issue_date` | date | YES | OPTIONAL | When issued |
| `expiry_date` | date | YES | OPTIONAL | When expires |
| `document_id` | uuid | YES | CONTEXT | FK → doc_metadata |
| `equipment_id` | uuid | YES | CONTEXT | FK → pms_equipment |
| `status` | text | YES | BACKEND_AUTO | Default: 'valid' |
| `superseded_by` | uuid | YES | CONTEXT | FK → pms_certificates (newer version) |
| `notes` | text | YES | OPTIONAL | Additional notes |
| `metadata` | jsonb | YES | BACKEND_AUTO | Additional data |
| `created_at` | timestamp | NOT NULL | BACKEND_AUTO | NOW() |
| `updated_at` | timestamp | NOT NULL | BACKEND_AUTO | Trigger |
| `created_by` | uuid | YES | BACKEND_AUTO | Who created |

**Row Count**: 0

---

## Table: `pms_crew_certificates` (Crew Certificates)

**Production DB Columns** (12 total):

| Column | PostgreSQL Type | Nullable | Classification | Notes |
|--------|-----------------|----------|----------------|-------|
| `id` | uuid | NOT NULL | BACKEND_AUTO | PK |
| `yacht_id` | uuid | NOT NULL | BACKEND_AUTO | FK → yacht_registry |
| `person_node_id` | uuid | YES | CONTEXT | FK → search_graph_nodes |
| `person_name` | text | NOT NULL | REQUIRED | Crew member name |
| `certificate_type` | text | NOT NULL | REQUIRED | Type (STCW, medical, etc.) |
| `certificate_number` | text | YES | OPTIONAL | Official number |
| `issuing_authority` | text | YES | OPTIONAL | Who issued |
| `issue_date` | date | YES | OPTIONAL | When issued |
| `expiry_date` | date | YES | OPTIONAL | When expires |
| `document_id` | uuid | YES | CONTEXT | FK → doc_metadata |
| `properties` | jsonb | YES | OPTIONAL | Additional properties |
| `created_at` | timestamp | NOT NULL | BACKEND_AUTO | NOW() |

**Row Count**: 0

---

## RLS Policies

### `pms_certificates` (Equipment/Vessel)

```sql
-- SELECT: All users can view
CREATE POLICY "Users can view certificates" ON pms_certificates
    FOR SELECT TO authenticated
    USING (yacht_id = get_user_yacht_id());

-- INSERT/UPDATE: Officers only
CREATE POLICY "Officers can create certificates" ON pms_certificates
    FOR INSERT TO authenticated
    WITH CHECK (
        (yacht_id = get_user_yacht_id())
        AND (get_user_role() = ANY (ARRAY['chief_engineer', 'eto', 'manager', 'captain', 'purser']))
    );

CREATE POLICY "Officers can update certificates" ON pms_certificates
    FOR UPDATE TO authenticated
    USING ((yacht_id = get_user_yacht_id()) AND (get_user_role() = ANY (...)));

-- DELETE: Managers only
CREATE POLICY "Managers can delete certificates" ON pms_certificates
    FOR DELETE TO authenticated
    USING ((yacht_id = get_user_yacht_id()) AND is_manager());

-- Service role bypass
CREATE POLICY "Service role full access certificates" ON pms_certificates
    FOR ALL TO service_role USING (true);
```

**RLS Status**: ✅ CANONICAL

### `pms_crew_certificates`

```sql
-- SELECT: All users can view
CREATE POLICY "Users can view yacht crew certificates" ON pms_crew_certificates
    FOR SELECT TO public
    USING (yacht_id = get_user_yacht_id());

-- Service role bypass
CREATE POLICY "Service role full access crew_certificates" ON pms_crew_certificates
    FOR ALL TO service_role USING (true);
```

**RLS Status**: ⚠️ Missing INSERT/UPDATE for authenticated users

---

# PART 2: MICRO-ACTIONS

## Action 1: `create_certificate`

**Purpose**: Add new equipment/vessel certificate

**Allowed Roles**: Officers (chief_engineer, eto, manager, captain, purser)

**Tables Written**: `pms_certificates` (INSERT), `pms_audit_log`

**Field Classification**:

| Field | Classification | Source |
|-------|----------------|--------|
| `certificate_name` | REQUIRED | User input |
| `certificate_type` | REQUIRED | User dropdown |
| `certificate_number` | OPTIONAL | User input |
| `issuing_authority` | OPTIONAL | User input |
| `issue_date` | OPTIONAL | User date picker |
| `expiry_date` | OPTIONAL | User date picker |
| `document_id` | OPTIONAL | User selects document |
| `equipment_id` | OPTIONAL | User selects equipment |
| `notes` | OPTIONAL | User input |

---

## Action 2: `update_certificate`

**Purpose**: Update certificate details

**Allowed Roles**: Officers

**Tables Written**: `pms_certificates` (UPDATE), `pms_audit_log`

---

## Action 3: `supersede_certificate`

**Purpose**: Replace certificate with newer version

**Allowed Roles**: Officers

**Tables Written**:
- `pms_certificates` (INSERT - new cert)
- `pms_certificates` (UPDATE old cert: status = 'superseded', superseded_by = new_id)
- `pms_audit_log`

---

## Action 4: `view_linked_document` (Escape Hatch)

**Purpose**: Open the certificate document

**Allowed Roles**: All Crew (read-only)

**Tables Read**: `doc_metadata`

---

## Action 5: `view_linked_equipment` (Escape Hatch)

**Purpose**: Navigate to equipment this certificate covers

**Allowed Roles**: All Crew (read-only)

---

# PART 3: QUERY PATTERNS

## Scenario 1: "Certificates expiring soon"

```sql
SELECT
    c.id,
    c.certificate_name,
    c.certificate_type,
    c.certificate_number,
    c.issuing_authority,
    c.expiry_date,
    c.expiry_date - CURRENT_DATE AS days_until_expiry,
    e.name AS equipment_name
FROM pms_certificates c
LEFT JOIN pms_equipment e ON c.equipment_id = e.id
WHERE c.expiry_date IS NOT NULL
  AND c.expiry_date <= CURRENT_DATE + INTERVAL '90 days'
  AND c.status = 'valid'
  AND c.yacht_id = public.get_user_yacht_id()
ORDER BY c.expiry_date ASC;
```

## Scenario 2: "Certificates for Generator #1"

```sql
SELECT
    c.id,
    c.certificate_name,
    c.certificate_type,
    c.certificate_number,
    c.expiry_date,
    c.status
FROM pms_certificates c
WHERE c.equipment_id = :equipment_id
  AND c.yacht_id = public.get_user_yacht_id()
ORDER BY c.expiry_date DESC NULLS LAST;
```

## Scenario 3: "Crew certificates for John Smith"

```sql
SELECT
    cc.id,
    cc.certificate_type,
    cc.certificate_number,
    cc.issuing_authority,
    cc.issue_date,
    cc.expiry_date,
    cc.expiry_date - CURRENT_DATE AS days_until_expiry
FROM pms_crew_certificates cc
WHERE cc.person_name ILIKE '%John Smith%'
  AND cc.yacht_id = public.get_user_yacht_id()
ORDER BY cc.expiry_date ASC NULLS LAST;
```

---

# PART 4: EXPIRY TRACKING

## Automatic Alerts

Certificates with approaching expiry dates should trigger alerts:

| Days Until Expiry | Alert Level |
|-------------------|-------------|
| > 90 days | No alert |
| 60-90 days | Info |
| 30-60 days | Warning |
| < 30 days | Critical |
| Expired | Emergency |

## Index for Expiry Queries

```sql
CREATE INDEX idx_certificates_expiry ON pms_certificates
    USING btree (expiry_date)
    WHERE (expiry_date IS NOT NULL);

CREATE INDEX idx_crew_certs_expiry_range ON pms_crew_certificates
    USING btree (yacht_id, expiry_date)
    WHERE (expiry_date IS NOT NULL);
```

---

# PART 5: SUMMARY

## Certificate Lens Actions

| Action | Tables Written | RLS Tier |
|--------|---------------|----------|
| `create_certificate` | pms_certificates, audit | Officers |
| `update_certificate` | pms_certificates, audit | Officers |
| `supersede_certificate` | pms_certificates x2, audit | Officers |
| `view_linked_document` | None (read) | All Crew |
| `view_linked_equipment` | None (read) | All Crew |

## Escape Hatches

| From Certificate | To Lens | Trigger |
|------------------|---------|---------|
| view_linked_document | Document Lens | Click document |
| view_linked_equipment | Equipment Lens | Click equipment |

## Key Invariants

1. **Expiry tracking** - `expiry_date` drives compliance alerts
2. **Supersede pattern** - Old certs linked to new via `superseded_by`
3. **Document linking** - Certificates can attach to scanned documents
4. **Equipment linking** - Equipment certs tied to specific equipment
5. **Crew certs separate** - `pms_crew_certificates` for personnel

---

# PART 6: GAPS & MIGRATIONS

## Security Gap

| Gap | Table | Migration | Status |
|-----|-------|-----------|--------|
| Missing INSERT/UPDATE policies | pms_crew_certificates | 20260125_006_fix_crew_certificates_rls.sql | **REQUIRED** |

### Proposed Migration

```sql
-- 20260125_006_fix_crew_certificates_rls.sql
BEGIN;

CREATE POLICY "officers_insert_crew_certificates" ON pms_crew_certificates
    FOR INSERT TO authenticated
    WITH CHECK (
        yacht_id = public.get_user_yacht_id()
        AND get_user_role() = ANY (ARRAY['captain', 'chief_engineer', 'purser', 'manager'])
    );

CREATE POLICY "officers_update_crew_certificates" ON pms_crew_certificates
    FOR UPDATE TO authenticated
    USING (yacht_id = public.get_user_yacht_id())
    WITH CHECK (
        yacht_id = public.get_user_yacht_id()
        AND get_user_role() = ANY (ARRAY['captain', 'chief_engineer', 'purser', 'manager'])
    );

COMMIT;
```

---

**END OF CERTIFICATE LENS v1 FINAL**
