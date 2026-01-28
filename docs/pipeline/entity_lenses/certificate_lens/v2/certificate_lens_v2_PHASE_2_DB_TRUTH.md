# Certificate Lens v2 - Phase 2: DB Truth
**Status**: SCHEMA EXTRACTED
**Date**: 2026-01-25
**Source**: `/Volumes/Backup/CELESTE/database_schema.txt`

---

## PURPOSE

This phase documents the **exact** database schema from the production snapshot. No assumptions. No inferred columns. Only what exists in the database.

---

# PRIMARY TABLE: `pms_vessel_certificates`

## Columns (14 total)

| # | Column | PostgreSQL Type | Nullable | Default | Classification | Notes |
|---|--------|-----------------|----------|---------|----------------|-------|
| 1 | `id` | uuid | NOT NULL | `gen_random_uuid()` | BACKEND_AUTO | Primary Key |
| 2 | `yacht_id` | uuid | NOT NULL | - | BACKEND_AUTO | FK → yacht_registry.id |
| 3 | `certificate_type` | text | NOT NULL | - | REQUIRED | e.g., 'class', 'ism', 'isps' |
| 4 | `certificate_name` | text | NOT NULL | - | REQUIRED | Human-readable name |
| 5 | `certificate_number` | text | YES | - | OPTIONAL | Issuing authority's number |
| 6 | `issuing_authority` | text | NOT NULL | - | REQUIRED | e.g., 'Lloyds Register' |
| 7 | `issue_date` | date | YES | - | OPTIONAL | When issued |
| 8 | `expiry_date` | date | YES | - | OPTIONAL | When expires |
| 9 | `last_survey_date` | date | YES | - | OPTIONAL | Last survey/audit |
| 10 | `next_survey_due` | date | YES | - | OPTIONAL | Next survey/audit due |
| 11 | `status` | text | NOT NULL | 'valid' | BACKEND_AUTO | Lifecycle state |
| 12 | `document_id` | uuid | YES | - | CONTEXT | FK → doc_metadata.id |
| 13 | `properties` | jsonb | YES | '{}' | OPTIONAL | Additional metadata |
| 14 | `created_at` | timestamptz | NOT NULL | `now()` | BACKEND_AUTO | Record creation |

## Indexes (Extracted from Production)

| Index Name | Columns | Type | Notes |
|------------|---------|------|-------|
| `pms_vessel_certificates_pkey` | `id` | PRIMARY KEY | Unique identifier |
| (inferred) | `yacht_id` | btree | Yacht isolation |
| (inferred) | `expiry_date` | btree | Expiration queries |

## Foreign Keys

| Column | References | On Delete |
|--------|------------|-----------|
| `yacht_id` | `yacht_registry(id)` | RESTRICT |
| `document_id` | `doc_metadata(id)` | SET NULL |

## Triggers

| Trigger | Event | Function | Notes |
|---------|-------|----------|-------|
| *(none found)* | - | - | **B4**: No auto-status trigger exists |

## RLS Policies

**STATUS**: ❌ **NO POLICIES FOUND** - **BLOCKER B1**

---

# PRIMARY TABLE: `pms_crew_certificates`

## Columns (12 total)

| # | Column | PostgreSQL Type | Nullable | Default | Classification | Notes |
|---|--------|-----------------|----------|---------|----------------|-------|
| 1 | `id` | uuid | NOT NULL | `gen_random_uuid()` | BACKEND_AUTO | Primary Key |
| 2 | `yacht_id` | uuid | NOT NULL | - | BACKEND_AUTO | FK → yacht_registry.id |
| 3 | `person_name` | text | NOT NULL | - | REQUIRED | Crew member name |
| 4 | `person_node_id` | uuid | YES | - | CONTEXT | FK → (person entity - if exists) |
| 5 | `certificate_type` | text | NOT NULL | - | REQUIRED | e.g., 'stcw', 'eng1', 'gmdss' |
| 6 | `certificate_number` | text | YES | - | OPTIONAL | Certificate ID number |
| 7 | `issuing_authority` | text | YES | - | OPTIONAL | Who issued it |
| 8 | `issue_date` | date | YES | - | OPTIONAL | When issued |
| 9 | `expiry_date` | date | YES | - | OPTIONAL | When expires |
| 10 | `document_id` | uuid | YES | - | CONTEXT | FK → doc_metadata.id |
| 11 | `properties` | jsonb | YES | '{}' | OPTIONAL | Additional metadata |
| 12 | `created_at` | timestamptz | NOT NULL | `now()` | BACKEND_AUTO | Record creation |

## Indexes (Extracted from Production)

| Index Name | Columns | Type | Notes |
|------------|---------|------|-------|
| `pms_crew_certificates_pkey` | `id` | PRIMARY KEY | Unique identifier |
| (inferred) | `yacht_id` | btree | Yacht isolation |
| (inferred) | `person_node_id` | btree | Person lookup |

## Foreign Keys

| Column | References | On Delete |
|--------|------------|-----------|
| `yacht_id` | `yacht_registry(id)` | RESTRICT |
| `document_id` | `doc_metadata(id)` | SET NULL |
| `person_node_id` | *(unverified)* | *(unknown)* |

## Triggers

| Trigger | Event | Function | Notes |
|---------|-------|----------|-------|
| *(none found)* | - | - | No auto-status trigger |

## RLS Policies

### Existing (Pre-Migration)
```sql
-- SELECT: All authenticated users can view crew certificates
CREATE POLICY "crew_select_own_yacht_crew_certificates" ON pms_crew_certificates
    FOR SELECT TO authenticated
    USING (yacht_id = public.get_user_yacht_id());
```

### Pending Migration (20260125_006)
```sql
-- INSERT: Officers can create
CREATE POLICY "officers_insert_crew_certificates" ON pms_crew_certificates
    FOR INSERT TO authenticated
    WITH CHECK (
        yacht_id = public.get_user_yacht_id()
        AND get_user_role() = ANY (ARRAY['captain', 'chief_engineer', 'purser', 'manager'])
    );

-- UPDATE: Officers can update
CREATE POLICY "officers_update_crew_certificates" ON pms_crew_certificates
    FOR UPDATE TO authenticated
    USING (yacht_id = public.get_user_yacht_id())
    WITH CHECK (
        yacht_id = public.get_user_yacht_id()
        AND get_user_role() = ANY (ARRAY['captain', 'chief_engineer', 'purser', 'manager'])
    );

-- DELETE: Managers only
CREATE POLICY "managers_delete_crew_certificates" ON pms_crew_certificates
    FOR DELETE TO authenticated
    USING (
        yacht_id = public.get_user_yacht_id()
        AND is_manager()
    );
```

**STATUS**: ⚠️ SELECT works; INSERT/UPDATE/DELETE blocked until migration deployed (**B2**)

---

# SECONDARY TABLE: `doc_metadata`

## Columns (21 total - relevant subset)

| # | Column | PostgreSQL Type | Nullable | Default | Classification |
|---|--------|-----------------|----------|---------|----------------|
| 1 | `id` | uuid | NOT NULL | `gen_random_uuid()` | BACKEND_AUTO |
| 2 | `yacht_id` | uuid | NOT NULL | - | BACKEND_AUTO |
| 3 | `source` | text | NOT NULL | - | BACKEND_AUTO |
| 4 | `filename` | text | NOT NULL | - | REQUIRED |
| 5 | `content_type` | text | YES | - | BACKEND_AUTO |
| 6 | `size_bytes` | bigint | YES | - | BACKEND_AUTO |
| 7 | `sha256` | text | YES | - | BACKEND_AUTO |
| 8 | `storage_path` | text | NOT NULL | - | BACKEND_AUTO |
| 9 | `tags` | text[] | YES | '{}' | OPTIONAL |
| 10 | `metadata` | jsonb | YES | '{}' | OPTIONAL |
| 11 | `created_at` | timestamptz | NOT NULL | `now()` | BACKEND_AUTO |
| 12 | `updated_at` | timestamptz | NOT NULL | `now()` | BACKEND_AUTO |

## RLS Policies (Existing)

```sql
-- SELECT: Yacht scope
CREATE POLICY "Users can view documents" ON doc_metadata
    FOR SELECT TO public
    USING (yacht_id = COALESCE(jwt_yacht_id(), get_user_yacht_id()));

-- INSERT: Yacht scope
CREATE POLICY "System can insert documents" ON doc_metadata
    FOR INSERT TO public
    WITH CHECK (yacht_id = get_user_yacht_id());

-- ALL: Managers can manage
CREATE POLICY "Managers can manage documents" ON doc_metadata
    FOR ALL TO public
    USING ((yacht_id = jwt_yacht_id()) AND is_manager());
```

---

# SECONDARY TABLE: `pms_audit_log`

## Columns (11 total)

| # | Column | PostgreSQL Type | Nullable | Default | Notes |
|---|--------|-----------------|----------|---------|-------|
| 1 | `id` | uuid | NOT NULL | `gen_random_uuid()` | PK |
| 2 | `yacht_id` | uuid | NOT NULL | - | FK |
| 3 | `entity_type` | text | NOT NULL | - | 'certificate' for this lens |
| 4 | `entity_id` | uuid | NOT NULL | - | Certificate ID |
| 5 | `action` | text | NOT NULL | - | Action name |
| 6 | `user_id` | uuid | NOT NULL | - | auth.uid() |
| 7 | `old_values` | jsonb | YES | - | Previous state |
| 8 | `new_values` | jsonb | YES | - | New state |
| 9 | `signature` | jsonb | NOT NULL | - | **NEVER NULL** |
| 10 | `metadata` | jsonb | YES | - | Additional context |
| 11 | `created_at` | timestamptz | NOT NULL | `now()` | Timestamp |

---

# HELPER FUNCTIONS (Verified Deployed)

## `public.get_user_yacht_id()`
```sql
CREATE OR REPLACE FUNCTION public.get_user_yacht_id()
RETURNS UUID
LANGUAGE sql
STABLE SECURITY DEFINER
AS $$
  SELECT yacht_id
  FROM auth_users_profiles
  WHERE id = auth.uid()
    AND is_active = true
  LIMIT 1;
$$;
```

## `public.get_user_role()`
```sql
CREATE OR REPLACE FUNCTION public.get_user_role()
RETURNS TEXT
LANGUAGE sql
SECURITY DEFINER STABLE
AS $$
  SELECT r.role
  FROM auth_users_profiles p
  JOIN auth_users_roles r ON r.user_id = p.id AND r.yacht_id = p.yacht_id
  WHERE p.id = auth.uid()
    AND p.is_active = true
    AND r.is_active = true
    AND r.valid_from <= NOW()
    AND (r.valid_until IS NULL OR r.valid_until > NOW())
  ORDER BY r.assigned_at DESC
  LIMIT 1;
$$;
```

## `public.is_hod(p_user_id, p_yacht_id)`
```sql
CREATE OR REPLACE FUNCTION public.is_hod(p_user_id UUID, p_yacht_id UUID)
RETURNS BOOLEAN
LANGUAGE sql
SECURITY DEFINER STABLE
AS $$
    SELECT EXISTS (
        SELECT 1
        FROM public.auth_users_roles
        WHERE user_id = p_user_id
          AND yacht_id = p_yacht_id
          AND role IN ('chief_engineer', 'captain', 'manager')
          AND is_active = true
          AND valid_from <= NOW()
          AND (valid_until IS NULL OR valid_until > NOW())
    );
$$;
```

---

# FIELD CLASSIFICATION SUMMARY

## REQUIRED Fields (User Must Provide)

### Vessel Certificate
| Field | Why Required |
|-------|--------------|
| `certificate_type` | Categorization |
| `certificate_name` | Display name |
| `issuing_authority` | Regulatory body |

### Crew Certificate
| Field | Why Required |
|-------|--------------|
| `person_name` | Who holds it |
| `certificate_type` | Categorization |

## OPTIONAL Fields (User May Provide)

| Field | Table | Notes |
|-------|-------|-------|
| `certificate_number` | Both | Issuer's reference |
| `issue_date` | Both | When granted |
| `expiry_date` | Both | When expires |
| `last_survey_date` | Vessel only | Survey tracking |
| `next_survey_due` | Vessel only | Survey tracking |
| `issuing_authority` | Crew only | Optional for crew |
| `properties` | Both | Extensible metadata |

## BACKEND_AUTO Fields (System Sets)

| Field | Value Source |
|-------|--------------|
| `id` | `gen_random_uuid()` |
| `yacht_id` | `public.get_user_yacht_id()` |
| `status` | Default 'valid'; updated by trigger/logic |
| `created_at` | `now()` |

## CONTEXT Fields (From Focused Entity)

| Field | Source |
|-------|--------|
| `document_id` | From linked doc_metadata record |
| `person_node_id` | From crew member focus (crew certs) |

---

# MISSING DATABASE OBJECTS

| Object | Type | Status | Migration Needed |
|--------|------|--------|------------------|
| RLS policies for `pms_vessel_certificates` | Policy | **MISSING** | Yes - B1 |
| CHECK constraint on `status` column | Constraint | **MISSING** | Optional - B3 |
| Status update trigger | Trigger | **MISSING** | Optional - B4 |
| Index on `expiry_date` for both tables | Index | Unverified | Recommended |
| Unique constraint on `(yacht_id, certificate_type, certificate_number)` | Constraint | **MISSING** | Recommended |

---

# STORAGE (Bucket: `documents`)

## Path Convention
```
documents/yacht/{yacht_id}/certificates/{certificate_id}/{filename}
```

## Storage RLS (Verified Separate from DB RLS)
| Operation | Policy |
|-----------|--------|
| INSERT | Authenticated, path prefix matches yacht_id |
| SELECT | Authenticated, path prefix matches yacht_id |
| UPDATE | HOD/Manager only |
| DELETE | HOD/Manager only |

---

# BLOCKERS CONSOLIDATED

| ID | Description | Severity | Tables Affected | Resolution |
|----|-------------|----------|-----------------|------------|
| **B1** | No RLS on `pms_vessel_certificates` | CRITICAL | pms_vessel_certificates | Write migration |
| **B2** | Crew cert RLS migration pending | MEDIUM | pms_crew_certificates | Deploy 20260125_006 |
| **B3** | No CHECK constraint on `status` | LOW | Both | Optional migration |
| **B4** | No expiration trigger | LOW | Both | Optional migration |

---

**DB TRUTH STATUS**: ✅ EXTRACTED - Proceed to Phase 3

---

**END OF PHASE 2**
