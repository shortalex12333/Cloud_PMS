# Crew Lens v2 - PHASE 2: DB GROUND TRUTH

**Version**: v2.0
**Status**: DB SCHEMA VERIFIED (NO MIGRATIONS NEEDED)
**Date**: 2026-01-30
**Template**: Certificate Lens v2 (Gold Standard)

---

## EXECUTIVE SUMMARY

All tables required for Crew Lens v2 already exist in production. RLS policies are deployed and correct. No migrations needed.

### Database Inventory

| Table | Columns | RLS Enabled | Purpose |
|-------|---------|-------------|---------|
| `auth_users_profiles` | 8 | ✅ | Crew member profiles |
| `auth_users_roles` | 9 | ✅ | Role assignments |
| `pms_crew_certificates` | 12 | ✅ | Crew qualifications |
| `pms_work_orders` | 26 | ✅ | Work order history |
| `pms_audit_log` | 11 | ✅ | Immutable audit trail |

---

## TABLE SCHEMAS

### Table 1: `auth_users_profiles`

**Purpose**: Crew member profiles (one profile per user)

| Column | PostgreSQL Type | Nullable | Classification | Notes |
|--------|-----------------|----------|----------------|-------|
| `id` | uuid | NOT NULL | BACKEND_AUTO | PK, matches auth.users.id |
| `yacht_id` | uuid | NOT NULL | BACKEND_AUTO | FK → yachts(id) |
| `email` | text | NOT NULL | BACKEND_AUTO | Unique, from auth.users |
| `name` | text | NOT NULL | REQUIRED/OPTIONAL | Display name (editable by user) |
| `is_active` | boolean | NOT NULL | BACKEND_AUTO | Default: true (Captain/Manager can update) |
| `metadata` | jsonb | YES | OPTIONAL | Additional crew data (future extensions) |
| `created_at` | timestamptz | NOT NULL | BACKEND_AUTO | NOW() |
| `updated_at` | timestamptz | NOT NULL | BACKEND_AUTO | NOW() on UPDATE |

**Indexes**:
```sql
idx_auth_users_profiles_yacht_id (yacht_id)
idx_auth_users_profiles_email (email)
idx_auth_users_profiles_active (yacht_id, is_active) WHERE is_active = true
```

**RLS Policies** (DEPLOYED):
```sql
-- SELECT: Users can view their own profile
CREATE POLICY "Users can view own profile"
    ON auth_users_profiles FOR SELECT TO authenticated
    USING (auth.uid() = id);

-- UPDATE: Users can update their own profile
CREATE POLICY "Users can update own profile"
    ON auth_users_profiles FOR UPDATE TO authenticated
    USING (auth.uid() = id)
    WITH CHECK (auth.uid() = id);
```

**Note**: No policy for listing all profiles. HOD must query with service role or use helper function.

---

### Table 2: `auth_users_roles`

**Purpose**: Role assignments per yacht (one active role per user per yacht)

| Column | PostgreSQL Type | Nullable | Classification | Notes |
|--------|-----------------|----------|----------------|-------|
| `id` | uuid | NOT NULL | BACKEND_AUTO | PK |
| `user_id` | uuid | NOT NULL | CONTEXT | FK → auth.users(id) |
| `yacht_id` | uuid | NOT NULL | BACKEND_AUTO | FK → yachts(id) |
| `role` | text | NOT NULL | REQUIRED | CHECK constraint on valid roles |
| `assigned_at` | timestamptz | NOT NULL | BACKEND_AUTO | NOW() |
| `assigned_by` | uuid | YES | BACKEND_AUTO | auth.uid() of assigner |
| `is_active` | boolean | NOT NULL | BACKEND_AUTO | Default: true (soft revoke) |
| `valid_from` | timestamptz | NOT NULL | BACKEND_AUTO | NOW() (can be overridden) |
| `valid_until` | timestamptz | YES | OPTIONAL | NULL = no expiry |

**Role Values** (CHECK constraint):
```sql
CHECK (role IN (
    'chief_engineer', 'eto', 'captain', 'manager',
    'vendor', 'crew', 'deck', 'interior', 'chief_officer', 'purser'
))
```

**Indexes**:
```sql
idx_auth_users_roles_user_id (user_id)
idx_auth_users_roles_yacht_id (yacht_id)
idx_auth_users_roles_active (user_id, yacht_id, is_active) WHERE is_active = true
```

**Constraints**:
```sql
CONSTRAINT unique_active_user_yacht_role UNIQUE (user_id, yacht_id, is_active)
-- Ensures one active role per user per yacht
```

**RLS Policies** (DEPLOYED):
```sql
-- SELECT: Users can view their own roles
CREATE POLICY "Users can view own roles"
    ON auth_users_roles FOR SELECT TO authenticated
    USING (auth.uid() = user_id);

-- ALL: HODs can manage roles
CREATE POLICY "HODs can manage roles"
    ON auth_users_roles FOR ALL TO authenticated
    USING (is_hod(auth.uid(), yacht_id));
```

---

### Table 3: `pms_crew_certificates`

**Purpose**: Crew member qualifications and certifications

| Column | PostgreSQL Type | Nullable | Classification | Notes |
|--------|-----------------|----------|----------------|-------|
| `id` | uuid | NOT NULL | BACKEND_AUTO | PK |
| `yacht_id` | uuid | NOT NULL | BACKEND_AUTO | FK → yachts(id) |
| `person_name` | text | NOT NULL | CONTEXT | Matches auth_users_profiles.name |
| `person_node_id` | uuid | YES | CONTEXT | FK → auth_users_profiles(id) |
| `certificate_type` | text | NOT NULL | REQUIRED | STCW, ENG1, COC, etc. |
| `certificate_number` | text | YES | OPTIONAL | Cert number/ID |
| `issuing_authority` | text | YES | OPTIONAL | Issuing body |
| `issue_date` | date | YES | OPTIONAL | Issue date |
| `expiry_date` | date | YES | OPTIONAL | Expiry date |
| `document_id` | uuid | YES | CONTEXT | FK → doc_metadata(id) |
| `properties` | jsonb | YES | OPTIONAL | Additional data |
| `created_at` | timestamptz | NOT NULL | BACKEND_AUTO | NOW() |

**RLS Policies** (DEPLOYED):
```sql
-- SELECT: All crew can view yacht crew certificates
-- INSERT/UPDATE: Officers (HOD)
-- DELETE: Managers only
```

---

### Table 4: `pms_work_orders`

**Purpose**: Work order tracking and assignment

| Column | PostgreSQL Type | Nullable | Classification | Notes |
|--------|-----------------|----------|----------------|-------|
| `id` | uuid | NOT NULL | BACKEND_AUTO | PK |
| `yacht_id` | uuid | NOT NULL | BACKEND_AUTO | FK → yachts(id) |
| `wo_number` | text | YES | BACKEND_AUTO | Auto-generated |
| `title` | text | NOT NULL | REQUIRED | WO title |
| `description` | text | YES | OPTIONAL | Details |
| `status` | text | NOT NULL | BACKEND_AUTO | open, in_progress, completed, etc. |
| `priority` | text | NOT NULL | REQUIRED | low, medium, high, critical, emergency |
| `assigned_to` | uuid | YES | CONTEXT | FK → auth.users(id) |
| `assigned_at` | timestamptz | YES | BACKEND_AUTO | When assigned |
| `due_date` | timestamptz | YES | OPTIONAL | Due date |
| `completed_at` | timestamptz | YES | BACKEND_AUTO | When completed |
| `deleted_at` | timestamptz | YES | BACKEND_AUTO | Soft delete timestamp |
| ...other columns... | | | | (26 total) |

**Relevant for Crew Lens**:
- `assigned_to` - Filter by auth.uid() for "my work orders"
- `status` - Filter out completed/cancelled
- `deleted_at` - Filter out soft-deleted WOs

---

### Table 5: `pms_audit_log`

**Purpose**: Immutable audit trail for all mutations

| Column | PostgreSQL Type | Nullable | Classification | Notes |
|--------|-----------------|----------|----------------|-------|
| `id` | uuid | NOT NULL | BACKEND_AUTO | PK |
| `yacht_id` | uuid | NOT NULL | BACKEND_AUTO | FK → yachts(id) |
| `entity_type` | text | NOT NULL | BACKEND_AUTO | 'crew', 'role', etc. |
| `entity_id` | uuid | NOT NULL | BACKEND_AUTO | ID of affected entity |
| `action` | text | NOT NULL | BACKEND_AUTO | Action name |
| `user_id` | uuid | NOT NULL | BACKEND_AUTO | auth.uid() |
| `old_values` | jsonb | YES | BACKEND_AUTO | Before mutation |
| `new_values` | jsonb | YES | BACKEND_AUTO | After mutation |
| `signature` | jsonb | NOT NULL | BACKEND_AUTO | `{}` for non-signed |
| `metadata` | jsonb | YES | BACKEND_AUTO | Context data |
| `created_at` | timestamptz | NOT NULL | BACKEND_AUTO | NOW() |

**Signature Invariant**:
- All Crew Lens actions: `signature = '{}'::jsonb`
- Never NULL
- No SIGNED actions in Crew Lens v2

---

## ACTION → TABLE MAPPING

### 1. `view_my_profile` (READ)

**Tables Read**:
- `auth_users_profiles` WHERE id = auth.uid()
- `auth_users_roles` WHERE user_id = auth.uid() AND is_active = true

**Tables Written**: None

**Field Classification**: N/A (READ only)

**RLS**: Self-only (auth.uid() = id)

---

### 2. `update_my_profile` (MUTATE)

**Tables Read**:
- `auth_users_profiles` WHERE id = auth.uid()

**Tables Written**:
- `auth_users_profiles` (UPDATE name, metadata)
- `pms_audit_log` (INSERT)

**Field Classification**:

| Field | Classification | Source | Validation |
|-------|----------------|--------|------------|
| `user_id` | CONTEXT | auth.uid() | Immutable |
| `yacht_id` | BACKEND_AUTO | JWT | Immutable |
| `name` | OPTIONAL | User input | Max 255 chars |
| `metadata` | OPTIONAL | User input | Valid JSON |
| `email` | BACKEND_AUTO | Existing | Immutable |
| `is_active` | BACKEND_AUTO | Existing | Immutable (not in payload) |
| `updated_at` | BACKEND_AUTO | NOW() | Auto-set |

**RLS**: Self-only (auth.uid() = id)

**Error Mapping**:
- 400: Invalid JSON in metadata
- 403: Attempt to update another user's profile
- 404: User not found (should never happen for self)

---

### 3. `view_assigned_work_orders` (READ)

**Tables Read**:
- `pms_work_orders` WHERE assigned_to = auth.uid() AND deleted_at IS NULL AND status NOT IN ('completed', 'cancelled')
- JOIN `pms_equipment` for equipment_name

**Tables Written**: None

**Field Classification**: N/A (READ only)

**RLS**: Implicit (assigned_to = auth.uid())

**Sorting**:
```sql
ORDER BY
    CASE priority
        WHEN 'emergency' THEN 1
        WHEN 'critical' THEN 2
        WHEN 'high' THEN 3
        WHEN 'medium' THEN 4
        ELSE 5
    END,
    due_date NULLS LAST
```

---

### 4. `list_crew_members` (READ)

**Tables Read**:
- `auth_users_profiles` WHERE yacht_id = get_user_yacht_id()
- `auth_users_roles` WHERE yacht_id = get_user_yacht_id() AND is_active = true

**Tables Written**: None

**Field Classification**: N/A (READ only)

**RLS**: HOD-gated (requires service role or helper function)

**Filtering**:
```sql
WHERE yacht_id = public.get_user_yacht_id()
ORDER BY is_active DESC, name ASC
```

---

### 5. `view_crew_member_details` (READ)

**Tables Read**:
- `auth_users_profiles` WHERE id = :user_id AND yacht_id = get_user_yacht_id()
- `auth_users_roles` WHERE user_id = :user_id AND yacht_id = get_user_yacht_id()

**Tables Written**: None

**Field Classification**:

| Field | Classification | Source |
|-------|----------------|--------|
| `user_id` | CONTEXT | Focused entity |
| `yacht_id` | BACKEND_AUTO | JWT |

**RLS**: HOD-gated

**Error Mapping**:
- 403: Non-HOD attempt
- 404: User not found or wrong yacht

---

### 6. `assign_role` (MUTATE)

**Tables Read**:
- `auth_users_profiles` WHERE id = :user_id (verify exists)
- `auth_users_roles` WHERE user_id = :user_id AND is_active = true (check duplicate)

**Tables Written**:
- `auth_users_roles` (INSERT)
- `pms_audit_log` (INSERT)

**Field Classification**:

| Field | Classification | Source | Validation |
|-------|----------------|--------|------------|
| `user_id` | CONTEXT | Focused entity | Must exist in auth_users_profiles |
| `yacht_id` | BACKEND_AUTO | JWT | From get_user_yacht_id() |
| `role` | REQUIRED | User input | CHECK constraint values |
| `assigned_by` | BACKEND_AUTO | auth.uid() | Current user |
| `assigned_at` | BACKEND_AUTO | NOW() | Auto-set |
| `is_active` | BACKEND_AUTO | true | Default |
| `valid_from` | BACKEND_AUTO | NOW() | Can be overridden |
| `valid_until` | OPTIONAL | User input | NULL or future date |

**RLS**: HOD-gated (is_hod(auth.uid(), yacht_id))

**Error Mapping**:
- 400: Invalid role value
- 403: Non-HOD attempt
- 404: User not found
- 409: Duplicate active role (UNIQUE constraint violation)

**SQL Pattern**:
```sql
-- Check for existing active role
SELECT COUNT(*) FROM auth_users_roles
WHERE user_id = :user_id
  AND yacht_id = public.get_user_yacht_id()
  AND is_active = true;
-- If count > 0, return 409

-- Insert new role
INSERT INTO auth_users_roles (
    id, user_id, yacht_id, role, assigned_by,
    assigned_at, is_active, valid_from, valid_until
) VALUES (
    gen_random_uuid(),
    :user_id,
    public.get_user_yacht_id(),
    :role,
    auth.uid(),
    NOW(),
    true,
    COALESCE(:valid_from, NOW()),
    :valid_until
);

-- Audit log
INSERT INTO pms_audit_log (
    id, yacht_id, entity_type, entity_id, action, user_id,
    old_values, new_values, signature, metadata, created_at
) VALUES (
    gen_random_uuid(),
    public.get_user_yacht_id(),
    'role',
    :new_role_id,
    'assign_role',
    auth.uid(),
    NULL,
    jsonb_build_object('user_id', :user_id, 'role', :role),
    '{}'::jsonb,
    jsonb_build_object('source', 'crew_lens'),
    NOW()
);
```

---

### 7. `revoke_role` (MUTATE)

**Tables Read**:
- `auth_users_roles` WHERE id = :role_id AND yacht_id = get_user_yacht_id()

**Tables Written**:
- `auth_users_roles` (UPDATE is_active=false)
- `pms_audit_log` (INSERT)

**Field Classification**:

| Field | Classification | Source | Validation |
|-------|----------------|--------|------------|
| `role_id` | REQUIRED | User selection | Must exist |
| `reason` | OPTIONAL | User input | Max 500 chars |
| `yacht_id` | BACKEND_AUTO | JWT | Ownership check |

**RLS**: HOD-gated

**Error Mapping**:
- 400: Cannot revoke if user has only one role
- 403: Non-HOD attempt
- 404: Role not found or wrong yacht
- 409: Role already revoked (is_active=false)

**SQL Pattern**:
```sql
-- Verify role exists and is active
SELECT user_id, role, is_active
FROM auth_users_roles
WHERE id = :role_id
  AND yacht_id = public.get_user_yacht_id()
  AND is_active = true;
-- If not found, return 404/409

-- Count user's remaining active roles
SELECT COUNT(*) FROM auth_users_roles
WHERE user_id = :user_id
  AND yacht_id = public.get_user_yacht_id()
  AND is_active = true;
-- If count = 1, return 400 "Cannot revoke last role"

-- Soft delete role
UPDATE auth_users_roles
SET is_active = false,
    valid_until = NOW()
WHERE id = :role_id
  AND yacht_id = public.get_user_yacht_id();

-- Audit log
INSERT INTO pms_audit_log (...) VALUES (...);
```

---

### 8. `view_crew_certificates` (READ)

**Tables Read**:
- `pms_crew_certificates` WHERE person_node_id = :user_id AND yacht_id = get_user_yacht_id()

**Tables Written**: None

**Field Classification**:

| Field | Classification | Source |
|-------|----------------|--------|
| `user_id` | CONTEXT | Focused entity |
| `yacht_id` | BACKEND_AUTO | JWT |

**RLS**: HOD-gated

**Computed Fields**:
- `is_expiring_soon`: expiry_date < current_date + 90 days
- `is_expired`: expiry_date < current_date
- `days_until_expiry`: expiry_date - current_date

---

### 9. `view_crew_work_history` (READ)

**Tables Read**:
- `pms_work_orders` WHERE assigned_to = :user_id AND yacht_id = get_user_yacht_id() AND status IN ('completed', 'cancelled')

**Tables Written**: None

**Field Classification**:

| Field | Classification | Source |
|-------|----------------|--------|
| `user_id` | CONTEXT | Focused entity |
| `yacht_id` | BACKEND_AUTO | JWT |
| `offset` | OPTIONAL | Pagination |
| `limit` | OPTIONAL | Pagination (default 50) |

**RLS**: HOD-gated

**Filtering**:
```sql
WHERE assigned_to = :user_id
  AND yacht_id = public.get_user_yacht_id()
  AND status IN ('completed', 'cancelled')
  AND deleted_at IS NULL
ORDER BY completed_at DESC
LIMIT :limit OFFSET :offset
```

---

### 10. `update_crew_member_status` (MUTATE)

**Tables Read**:
- `auth_users_profiles` WHERE id = :user_id AND yacht_id = get_user_yacht_id()

**Tables Written**:
- `auth_users_profiles` (UPDATE is_active)
- `pms_audit_log` (INSERT)

**Field Classification**:

| Field | Classification | Source | Validation |
|-------|----------------|--------|------------|
| `user_id` | CONTEXT | Focused entity | Must exist |
| `yacht_id` | BACKEND_AUTO | JWT | Ownership check |
| `is_active` | REQUIRED | User input | Boolean |
| `reason` | OPTIONAL | User input | Max 500 chars |
| `updated_by` | BACKEND_AUTO | auth.uid() | Current user |
| `updated_at` | BACKEND_AUTO | NOW() | Auto-set |

**RLS**: Captain/Manager only

**Error Mapping**:
- 400: Missing is_active
- 403: Non-Captain/Manager attempt
- 404: User not found or wrong yacht
- 409: Status already set to requested value

**SQL Pattern**:
```sql
-- Fetch current status
SELECT is_active FROM auth_users_profiles
WHERE id = :user_id
  AND yacht_id = public.get_user_yacht_id();
-- If not found, return 404
-- If is_active = :new_is_active, return 409

-- Update status
UPDATE auth_users_profiles
SET is_active = :is_active,
    updated_at = NOW()
WHERE id = :user_id
  AND yacht_id = public.get_user_yacht_id();

-- Audit log
INSERT INTO pms_audit_log (
    id, yacht_id, entity_type, entity_id, action, user_id,
    old_values, new_values, signature, metadata, created_at
) VALUES (
    gen_random_uuid(),
    public.get_user_yacht_id(),
    'crew',
    :user_id,
    'update_crew_member_status',
    auth.uid(),
    jsonb_build_object('is_active', :old_is_active),
    jsonb_build_object('is_active', :is_active, 'reason', :reason),
    '{}'::jsonb,
    jsonb_build_object('source', 'crew_lens'),
    NOW()
);
```

---

## HELPER FUNCTIONS (DEPLOYED)

### `public.get_user_yacht_id()`
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

**Usage**: Derive yacht_id from JWT in all queries

---

### `public.is_hod(p_user_id UUID, p_yacht_id UUID)`
```sql
CREATE OR REPLACE FUNCTION public.is_hod(p_user_id UUID, p_yacht_id UUID)
RETURNS BOOLEAN
LANGUAGE sql
SECURITY DEFINER
STABLE
AS $$
    SELECT EXISTS (
        SELECT 1
        FROM public.auth_users_roles
        WHERE user_id = p_user_id
          AND yacht_id = p_yacht_id
          AND role IN ('chief_engineer', 'chief_officer', 'purser', 'captain', 'manager')
          AND is_active = true
          AND valid_from <= NOW()
          AND (valid_until IS NULL OR valid_until > NOW())
    );
$$;
```

**Usage**: Gate HOD-only actions (assign_role, revoke_role, list_crew_members, etc.)

---

### `public.is_manager(p_user_id UUID, p_yacht_id UUID)`
```sql
CREATE OR REPLACE FUNCTION public.is_manager(p_user_id UUID, p_yacht_id UUID)
RETURNS BOOLEAN
LANGUAGE sql
SECURITY DEFINER
STABLE
AS $$
    SELECT EXISTS (
        SELECT 1
        FROM public.auth_users_roles
        WHERE user_id = p_user_id
          AND yacht_id = p_yacht_id
          AND role IN ('captain', 'manager')
          AND is_active = true
          AND valid_from <= NOW()
          AND (valid_until IS NULL OR valid_until > NOW())
    );
$$;
```

**Usage**: Gate Captain/Manager-only actions (update_crew_member_status)

---

## RLS SUMMARY

| Table | SELECT Policy | INSERT/UPDATE Policy | DELETE Policy |
|-------|---------------|----------------------|---------------|
| `auth_users_profiles` | Self-only (auth.uid() = id) | Self-only (auth.uid() = id) | No policy (denied) |
| `auth_users_roles` | Self-only (user_id = auth.uid()) | HOD (is_hod()) | HOD (is_hod()) |
| `pms_crew_certificates` | Yacht-scoped | HOD | Manager |
| `pms_work_orders` | Yacht-scoped | Yacht-scoped | No policy (denied) |
| `pms_audit_log` | Yacht-scoped | Service role only | No DELETE allowed |

**Note**: HOD actions that query across all crew members must use service role or helper functions to bypass self-only policies.

---

## BLOCKERS

| ID | Blocker | Severity | Status |
|----|---------|----------|--------|
| **None** | All tables exist, RLS deployed | N/A | ✅ READY |

---

## VERIFICATION QUERIES

### 1. Verify Tables Exist
```sql
SELECT tablename, schemaname
FROM pg_tables
WHERE tablename IN (
    'auth_users_profiles',
    'auth_users_roles',
    'pms_crew_certificates',
    'pms_work_orders',
    'pms_audit_log'
)
ORDER BY tablename;
-- Should return 5 rows
```

### 2. Verify RLS Enabled
```sql
SELECT relname, relrowsecurity
FROM pg_class
WHERE relname IN (
    'auth_users_profiles',
    'auth_users_roles',
    'pms_crew_certificates',
    'pms_work_orders',
    'pms_audit_log'
);
-- All should show relrowsecurity = TRUE
```

### 3. Verify RLS Policies
```sql
SELECT tablename, policyname, cmd
FROM pg_policies
WHERE tablename IN ('auth_users_profiles', 'auth_users_roles')
ORDER BY tablename, policyname;
-- Should show 4 policies (2 per table)
```

### 4. Verify Helper Functions
```sql
SELECT proname, prosrc
FROM pg_proc
WHERE proname IN ('get_user_yacht_id', 'is_hod', 'is_manager');
-- Should return 3 rows
```

### 5. Verify Role Values
```sql
SELECT DISTINCT role
FROM auth_users_roles
WHERE is_active = true
ORDER BY role;
-- Should show valid role values
```

---

## NON-NEGOTIABLES

1. **No new migrations**: All tables exist. Do not create new tables.
2. **Server-derived context**: yacht_id from `get_user_yacht_id()`, role from `is_hod()`/`is_manager()`.
3. **RLS everywhere**: All queries honor RLS. Service role only where necessary (list_crew_members).
4. **Signature invariant**: `signature = '{}'::jsonb` for all crew actions. Never NULL.
5. **Soft delete roles**: Revoke with `is_active=false`, never DELETE.
6. **Error discipline**: 400=validation, 403=RLS, 404=not found, 409=conflict. Never 500.

---

**END OF PHASE 2: DB GROUND TRUTH**
