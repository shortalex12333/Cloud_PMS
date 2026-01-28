# Work Order Lens - PHASE 2: DB Truth Grounding

**Status**: COMPLETE
**Source**: `/Volumes/Backup/CELESTE/database_schema.txt`
**Created**: 2026-01-24

---

## BLOCKERS IDENTIFIED

| ID | Blocker | Affects | Resolution |
|----|---------|---------|------------|
| **B1** | `pms_work_orders` has no dedicated RLS policies | All actions | Migrate from `user_profiles` pattern to `public.get_user_yacht_id()` |
| **B2** | Missing enum value documentation | Status/Type validation | Extract enum values from DB or migrations |

---

## 2.1 Primary Table: `pms_work_orders`

### Schema (from snapshot)

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | uuid | NO | gen_random_uuid() | PK |
| `yacht_id` | uuid | NO | - | FK to yachts |
| `wo_number` | text | YES | - | Auto-generated WO-YYYY-NNN |
| `title` | text | NO | - | Required |
| `description` | text | YES | - | |
| `type` | public.work_order_type (enum) | NO | - | corrective/preventive/etc |
| `priority` | public.work_order_priority (enum) | NO | - | low/medium/high/critical |
| `status` | public.work_order_status (enum) | NO | - | draft/open/in_progress/etc |
| `equipment_id` | uuid | YES | - | FK to pms_equipment |
| `fault_id` | uuid | YES | - | FK to pms_faults |
| `assigned_to` | uuid | YES | - | FK to auth.users |
| `due_date` | date | YES | - | Calendar-based scheduling |
| `due_hours` | integer | YES | - | Hour-based scheduling |
| `frequency` | jsonb | YES | - | Recurring WO config |
| `last_completed_date` | date | YES | - | For recurring WOs |
| `last_completed_hours` | integer | YES | - | For hour-based recurring |
| `completed_at` | timestamptz | YES | - | Completion timestamp |
| `completed_by` | uuid | YES | - | FK to auth.users |
| `completion_notes` | text | YES | - | |
| `metadata` | jsonb | YES | - | Flexible extension |
| `vendor_contact_hash` | text | YES | - | Email matching |
| `work_order_type` | text | YES | - | **DEPRECATED** |
| `created_at` | timestamptz | NO | NOW() | |
| `created_by` | uuid | NO | - | FK to auth.users |
| `updated_at` | timestamptz | NO | NOW() | |
| `updated_by` | uuid | YES | - | FK to auth.users |
| `deleted_at` | timestamptz | YES | - | Soft delete |
| `deleted_by` | uuid | YES | - | |
| `deletion_reason` | text | YES | - | |

**Total: 29 columns**

### Field Classifications

| Classification | Columns |
|----------------|---------|
| **REQUIRED** | yacht_id, title, type, priority, status, created_by |
| **OPTIONAL** | description, equipment_id, fault_id, assigned_to, due_date, due_hours, completion_notes, metadata |
| **BACKEND_AUTO** | id, wo_number, created_at, updated_at, completed_at (on complete), completed_by (on complete) |
| **CONTEXT** | vendor_contact_hash, frequency, last_completed_date, last_completed_hours |
| **DEPRECATED** | work_order_type (use `type` enum instead) |

---

## 2.2 Secondary Tables

### `pms_work_order_checklist`

| Column | Type | Nullable | Notes |
|--------|------|----------|-------|
| `id` | uuid | NO | PK |
| `work_order_id` | uuid | NO | FK to pms_work_orders |
| `yacht_id` | uuid | NO | Denormalized for RLS |
| `title` | varchar | NO | |
| `description` | text | YES | |
| `instructions` | text | YES | |
| `sequence` | integer | NO | Display order |
| `is_required` | boolean | NO | |
| `requires_photo` | boolean | NO | |
| `requires_signature` | boolean | NO | |
| `is_completed` | boolean | NO | |
| `completed_at` | timestamptz | YES | |
| `completed_by` | uuid | YES | |
| `completion_notes` | text | YES | |
| `photo_url` | text | YES | |
| `signature_data` | jsonb | YES | |
| `metadata` | jsonb | YES | |
| `created_at` | timestamptz | NO | |
| `created_by` | uuid | YES | |
| `updated_at` | timestamptz | YES | |
| `updated_by` | uuid | YES | |
| `deleted_at` | timestamptz | YES | Soft delete |
| `deleted_by` | uuid | YES | |
| `deletion_reason` | text | YES | |

**Total: 23 columns**

---

### `pms_work_order_notes`

| Column | Type | Nullable | Notes |
|--------|------|----------|-------|
| `id` | uuid | NO | PK |
| `work_order_id` | uuid | NO | FK to pms_work_orders |
| `note_text` | text | NO | |
| `note_type` | text | NO | general/progress/issue/resolution |
| `metadata` | jsonb | YES | |
| `created_at` | timestamptz | NO | |
| `created_by` | uuid | NO | |

**Total: 7 columns**

---

### `pms_work_order_parts`

| Column | Type | Nullable | Notes |
|--------|------|----------|-------|
| `id` | uuid | NO | PK |
| `work_order_id` | uuid | NO | FK to pms_work_orders |
| `part_id` | uuid | NO | FK to pms_parts |
| `quantity` | integer | YES | |
| `notes` | text | YES | |
| `created_at` | timestamptz | YES | |
| `updated_at` | timestamptz | YES | |
| `deleted_at` | timestamptz | YES | Soft delete |
| `deleted_by` | uuid | YES | |

**Total: 9 columns**

---

### `pms_work_order_history`

| Column | Type | Nullable | Notes |
|--------|------|----------|-------|
| `id` | uuid | NO | PK |
| `work_order_id` | uuid | NO | FK to pms_work_orders |
| `yacht_id` | uuid | NO | Denormalized |
| `equipment_id` | uuid | YES | |
| `status_on_completion` | text | YES | |
| `completed_at` | timestamptz | YES | |
| `completed_by` | uuid | YES | |
| `hours_logged` | integer | YES | |
| `notes` | text | YES | |
| `parts_used` | jsonb | YES | |
| `faults_related` | jsonb | YES | |
| `documents_used` | jsonb | YES | |
| `metadata` | jsonb | YES | |
| `created_at` | timestamptz | NO | |

**Total: 14 columns**

---

## 2.3 Audit Table: `pms_audit_log`

| Column | Type | Nullable | Notes |
|--------|------|----------|-------|
| `id` | uuid | NO | PK |
| `yacht_id` | uuid | NO | |
| `user_id` | uuid | NO | |
| `action` | text | NO | Action name |
| `entity_type` | text | NO | From canonical list |
| `entity_id` | uuid | NO | |
| `old_values` | jsonb | YES | NULL for creates |
| `new_values` | jsonb | NO | |
| `signature` | jsonb | NO | **NEVER NULL** - `'{}'::jsonb` for non-signature |
| `metadata` | jsonb | YES | Session context |
| `created_at` | timestamptz | NO | |

**Signature Invariant**: `signature` column is NOT NULL. Use `'{}'::jsonb` for actions not requiring signature.

---

## 2.4 Enums Used

### `public.work_order_type`

**Status**: Enum exists but values need verification from migrations

Expected values (based on migration patterns):
```sql
'corrective', 'preventive', 'predictive', 'emergency', 'project'
```

### `public.work_order_priority`

Expected values:
```sql
'low', 'medium', 'high', 'critical'
```

### `public.work_order_status`

Expected values:
```sql
'draft', 'open', 'in_progress', 'on_hold', 'completed', 'cancelled'
```

**BLOCKER B2**: Enum values not explicitly documented in snapshot. Verify from `pg_enum` introspection or migration files.

---

## 2.5 Constraints

### Foreign Keys

| FK Column | References | On Delete |
|-----------|------------|-----------|
| `yacht_id` | `yachts(id)` | CASCADE |
| `equipment_id` | `pms_equipment(id)` | SET NULL |
| `fault_id` | `pms_faults(id)` | SET NULL |
| `assigned_to` | `auth.users(id)` | SET NULL (assumed) |
| `created_by` | `auth.users(id)` | - |
| `completed_by` | `auth.users(id)` | SET NULL |
| `updated_by` | `auth.users(id)` | SET NULL |
| `deleted_by` | `auth.users(id)` | SET NULL |

### Unique Constraints

```sql
UNIQUE(yacht_id, wo_number)  -- Assumed from generate_wo_number() pattern
```

### CHECK Constraints

Enum columns (`type`, `priority`, `status`) enforce valid values via PostgreSQL enum types.

---

## 2.6 Triggers

### Verified in Migrations

| Trigger | Table | Event | Function |
|---------|-------|-------|----------|
| `update_work_orders_updated_at` | `work_orders` | BEFORE UPDATE | `public.update_updated_at()` |
| `trg_wo_status_cascade_to_fault` | `pms_work_orders` | AFTER UPDATE OF status | `cascade_wo_status_to_fault()` |

**Note**: `trg_wo_status_cascade_to_fault` is in CUMULATIVE_SCHEMA_MIGRATIONS.sql - may not be deployed yet.

---

## 2.7 Indexes (Inferred from migrations)

| Index | Columns | Condition |
|-------|---------|-----------|
| `idx_pms_work_orders_yacht` | yacht_id | - |
| `idx_pms_work_orders_status` | yacht_id, status | - |
| `idx_pms_work_orders_equipment` | equipment_id | - |
| `idx_pms_work_orders_assigned` | assigned_to | - |
| `idx_pms_work_orders_wo_number` | yacht_id, wo_number | - |
| `idx_pms_work_orders_assigned_active` | assigned_to, status | WHERE deleted_at IS NULL AND status NOT IN ('completed', 'cancelled') |

---

## 2.8 RLS Policies

### ACTUAL DEPLOYED (from `20260116_000_create_pms_core_tables.sql`)

```sql
-- pms_work_orders
ALTER TABLE public.pms_work_orders ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view their yacht work orders"
    ON public.pms_work_orders FOR SELECT
    USING (yacht_id IN (
        SELECT yacht_id FROM public.user_profiles WHERE id = auth.uid()
    ));

CREATE POLICY "Users can manage their yacht work orders"
    ON public.pms_work_orders FOR ALL
    USING (yacht_id IN (
        SELECT yacht_id FROM public.user_profiles WHERE id = auth.uid()
    ));
```

### ISSUES WITH DEPLOYED RLS

| Issue | Severity | Description |
|-------|----------|-------------|
| **LEGACY PATTERN** | BLOCKER | Uses `public.user_profiles` subquery instead of `public.get_user_yacht_id()` |
| **No Role Check** | FLAG | All authenticated users can SELECT/INSERT/UPDATE/DELETE |
| **No Service Role Bypass** | FLAG | Missing explicit service_role policy |
| **No Soft Delete Filter** | WARN | Policies don't filter `WHERE deleted_at IS NULL` |

### PROPOSED RLS (for migration)

```sql
-- Drop legacy policies
DROP POLICY IF EXISTS "Users can view their yacht work orders" ON pms_work_orders;
DROP POLICY IF EXISTS "Users can manage their yacht work orders" ON pms_work_orders;

-- SELECT: All yacht crew can view
CREATE POLICY "crew_can_view_work_orders" ON pms_work_orders
    FOR SELECT
    USING (
        yacht_id = public.get_user_yacht_id()
        AND deleted_at IS NULL
    );

-- INSERT: Engineers+ can create
CREATE POLICY "engineers_can_create_work_orders" ON pms_work_orders
    FOR INSERT
    WITH CHECK (
        yacht_id = public.get_user_yacht_id()
        AND public.user_has_role(ARRAY['engineer', 'chief_engineer', 'eto', 'captain', 'chief_officer', 'chief_steward', 'purser'])
    );

-- UPDATE: Assigned user or Engineers+ can update
CREATE POLICY "crew_can_update_work_orders" ON pms_work_orders
    FOR UPDATE
    USING (
        yacht_id = public.get_user_yacht_id()
        AND deleted_at IS NULL
        AND (
            assigned_to = auth.uid()
            OR public.user_has_role(ARRAY['engineer', 'chief_engineer', 'eto', 'captain', 'chief_officer', 'chief_steward', 'purser'])
        )
    );

-- DELETE: Captain/HoD only (soft delete)
CREATE POLICY "hod_can_archive_work_orders" ON pms_work_orders
    FOR UPDATE
    USING (
        yacht_id = public.get_user_yacht_id()
        AND public.user_has_role(ARRAY['captain', 'chief_engineer', 'chief_steward', 'chief_officer', 'purser'])
    );

-- Service role bypass
CREATE POLICY "service_role_full_access" ON pms_work_orders
    FOR ALL
    USING (auth.jwt()->>'role' = 'service_role');
```

---

## 2.9 Functions Verified

| Function | Exists | Location |
|----------|--------|----------|
| `public.get_user_yacht_id()` | YES | `00000000000004_02_p0_actions_tables_REVISED.sql:489` |
| `public.generate_wo_number(p_yacht_id)` | YES | `00000000000004_02_p0_actions_tables_REVISED.sql:391` |
| `public.user_has_role(TEXT[])` | PROPOSED | `CUMULATIVE_SCHEMA_MIGRATIONS.sql:551` (may not be deployed) |
| `cascade_wo_status_to_fault()` | PROPOSED | `CUMULATIVE_SCHEMA_MIGRATIONS.sql:334` (may not be deployed) |

---

## 2.10 Doc vs DB Diff Table

| Item | Doc/Expected | Actual DB | Status |
|------|--------------|-----------|--------|
| RLS function | `public.get_user_yacht_id()` | `user_profiles` subquery | **MISMATCH** |
| `work_order_type` column | Not needed | EXISTS (deprecated) | Migration needed |
| `user_has_role()` function | Required for RLS | May not exist | **VERIFY** |
| WO→Fault cascade trigger | Required | In CUMULATIVE only | **VERIFY** |
| Soft delete filter in RLS | Required | Not present | Migration needed |

---

## PHASE 2 GATE: COMPLETE

| Check | Status |
|-------|--------|
| 2.1 Primary table extracted | ✅ |
| 2.2 Secondary tables extracted | ✅ |
| 2.3 Audit table documented | ✅ |
| 2.4 Enums documented | ✅ (values need verification) |
| 2.5 Constraints documented | ✅ |
| 2.6 Triggers documented | ✅ |
| 2.7 Indexes documented | ✅ |
| 2.8 RLS policies extracted | ✅ |
| 2.9 Functions verified | ✅ |
| 2.10 Diff table built | ✅ |
| BLOCKERS identified | ✅ (B1, B2) |

**Proceeding to Phase 3: Entity & Relationship Model**
