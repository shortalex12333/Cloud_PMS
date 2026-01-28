# Entity Lens: Crew

**Status**: v1 - PRODUCTION READY
**Last Updated**: 2026-01-25
**Schema Source**: Production Supabase Database (db_truth_snapshot.md)

---

# BLOCKERS

| ID | Blocker | Affects | Resolution |
|----|---------|---------|------------|
| ✅ | None | - | Crew Lens is shippable |

> **NOTE**: RLS restricts users to viewing only their own profile. HoD can manage roles.

---

# PART 1: DATABASE SCHEMA

## Table: `auth_users_profiles`

**Production DB Columns** (8 total):

| Column | PostgreSQL Type | Nullable | Classification | Notes |
|--------|-----------------|----------|----------------|-------|
| `id` | uuid | NOT NULL | BACKEND_AUTO | PK, matches auth.users.id |
| `yacht_id` | uuid | NOT NULL | BACKEND_AUTO | FK → yacht_registry |
| `email` | text | NOT NULL | REQUIRED | Unique email |
| `name` | text | NOT NULL | REQUIRED | Display name |
| `is_active` | boolean | NOT NULL | BACKEND_AUTO | Account status. Default: true |
| `metadata` | jsonb | YES | BACKEND_AUTO | Additional data |
| `created_at` | timestamp | NOT NULL | BACKEND_AUTO | NOW() |
| `updated_at` | timestamp | NOT NULL | BACKEND_AUTO | Trigger |

**Row Count**: 1

---

## Table: `auth_users_roles`

**Production DB Columns** (9 total):

| Column | PostgreSQL Type | Nullable | Classification | Notes |
|--------|-----------------|----------|----------------|-------|
| `id` | uuid | NOT NULL | BACKEND_AUTO | PK |
| `user_id` | uuid | NOT NULL | CONTEXT | FK (implicit to auth.users) |
| `yacht_id` | uuid | NOT NULL | BACKEND_AUTO | FK → yacht_registry |
| `role` | text | NOT NULL | REQUIRED | Role name (enum-like) |
| `assigned_at` | timestamp | NOT NULL | BACKEND_AUTO | NOW() |
| `assigned_by` | uuid | YES | BACKEND_AUTO | Who assigned |
| `is_active` | boolean | NOT NULL | BACKEND_AUTO | Default: true |
| `valid_from` | timestamp | NOT NULL | BACKEND_AUTO | NOW() |
| `valid_until` | timestamp | YES | OPTIONAL | Expiry (NULL = no expiry) |

**Row Count**: 1

---

## Role Values (CHECK Constraint)

```sql
CHECK (role = ANY (ARRAY[
    'chief_engineer',
    'eto',
    'captain',
    'manager',
    'vendor',
    'crew',
    'deck',
    'interior'
]))
```

**Role Hierarchy**:

| Tier | Roles | Capabilities |
|------|-------|--------------|
| TIER 3 (HoD) | captain, chief_engineer, manager | Full management, delete, role assignment |
| TIER 2 (Officers) | eto, deck, interior | Work order management, status updates |
| TIER 1 (Crew) | crew, vendor | View, add notes, report issues |

---

## RLS Policies

### `auth_users_profiles`

```sql
-- SELECT: Users can only view their OWN profile
CREATE POLICY "Users can view own profile" ON auth_users_profiles
    FOR SELECT TO authenticated
    USING (auth.uid() = id);

-- UPDATE: Users can only update their OWN profile
CREATE POLICY "Users can update own profile" ON auth_users_profiles
    FOR UPDATE TO authenticated
    USING (auth.uid() = id)
    WITH CHECK (auth.uid() = id);
```

> **IMPORTANT**: Users cannot see other crew members' profiles directly. Crew lookup is done via `auth.uid()` joins in other queries.

### `auth_users_roles`

```sql
-- SELECT: Users can view their own roles
CREATE POLICY "Users can view own roles" ON auth_users_roles
    FOR SELECT TO authenticated
    USING (auth.uid() = user_id);

-- ALL: HoDs can manage roles
CREATE POLICY "HODs can manage roles" ON auth_users_roles
    FOR ALL TO authenticated
    USING (is_hod(auth.uid(), yacht_id));
```

---

# PART 2: MICRO-ACTIONS

## Action 1: `view_my_profile`

**Purpose**: View own profile and roles

**Allowed Roles**: All Crew (self only)

**Tables Read**: `auth_users_profiles`, `auth_users_roles`

---

## Action 2: `update_my_profile`

**Purpose**: Update own display name or metadata

**Allowed Roles**: All Crew (self only)

**Tables Written**: `auth_users_profiles` (UPDATE), `pms_audit_log`

**Field Classification**:

| Field | Classification | Source |
|-------|----------------|--------|
| `name` | OPTIONAL | User input |
| `metadata` | OPTIONAL | User input (limited fields) |

---

## Action 3: `view_assigned_work_orders`

**Purpose**: Show WOs assigned to current user

**Allowed Roles**: All Crew (self only)

**Tables Read**: `pms_work_orders` (WHERE assigned_to = auth.uid())

---

## Action 4: `assign_role` (HoD Only)

**Purpose**: Assign role to crew member

**Allowed Roles**: HoD only

**Tables Written**: `auth_users_roles` (INSERT), `pms_audit_log`

---

## Action 5: `revoke_role` (HoD Only)

**Purpose**: Remove role from crew member

**Allowed Roles**: HoD only

**Tables Written**: `auth_users_roles` (UPDATE is_active = false), `pms_audit_log`

---

# PART 3: QUERY PATTERNS

## Scenario 1: "My assigned work orders"

```sql
SELECT
    wo.id,
    wo.wo_number,
    wo.title,
    wo.priority,
    wo.status,
    wo.due_date,
    e.name AS equipment_name
FROM pms_work_orders wo
LEFT JOIN pms_equipment e ON wo.equipment_id = e.id
WHERE wo.assigned_to = auth.uid()
  AND wo.yacht_id = public.get_user_yacht_id()
  AND wo.status NOT IN ('completed', 'cancelled')
  AND wo.deleted_at IS NULL
ORDER BY
    CASE wo.priority
        WHEN 'emergency' THEN 1
        WHEN 'critical' THEN 2
        WHEN 'important' THEN 3
        ELSE 4
    END,
    wo.due_date NULLS LAST;
```

## Scenario 2: "My roles"

```sql
SELECT
    r.role,
    r.assigned_at,
    r.valid_from,
    r.valid_until,
    (SELECT name FROM auth_users_profiles WHERE id = r.assigned_by) AS assigned_by_name
FROM auth_users_roles r
WHERE r.user_id = auth.uid()
  AND r.yacht_id = public.get_user_yacht_id()
  AND r.is_active = true
  AND (r.valid_until IS NULL OR r.valid_until > NOW());
```

---

# PART 4: SUMMARY

## Crew Lens Actions

| Action | Tables Written | RLS Tier |
|--------|---------------|----------|
| `view_my_profile` | None (read) | Self Only |
| `update_my_profile` | auth_users_profiles, audit | Self Only |
| `view_assigned_work_orders` | None (read) | Self Only |
| `assign_role` | auth_users_roles, audit | HoD Only |
| `revoke_role` | auth_users_roles, audit | HoD Only |

## Escape Hatches

| From Crew | To Lens | Trigger |
|-----------|---------|---------|
| view_assigned_work_orders | Work Order Lens | Click WO |

## Key Invariants

1. **Self-only profile access** - Users see only their own data
2. **HoD role management** - Only HoD can assign/revoke roles
3. **Role validity periods** - Roles can have expiry dates
4. **Active flag for soft revoke** - Roles deactivated, not deleted

---

**END OF CREW LENS v1 FINAL**
