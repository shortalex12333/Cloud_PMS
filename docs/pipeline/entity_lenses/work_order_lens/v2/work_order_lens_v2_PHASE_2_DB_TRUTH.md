# Work Order Lens v2 - PHASE 2: Database Truth

**Status**: COMPLETE
**Source**: Production Database Snapshot (2026-01-24T06:35:34)
**Tables**: 6 (1 primary + 5 secondary/related)

---

## 2.1 PRIMARY TABLE: pms_work_orders

**Row Count**: 2,820
**Columns**: 29
**Has yacht_id**: YES
**RLS**: ✅ CANONICAL

### Schema

| # | Column | Type | Nullable | Default | Classification |
|---|--------|------|----------|---------|----------------|
| 1 | `id` | uuid | NO | gen_random_uuid() | BACKEND_AUTO |
| 2 | `yacht_id` | uuid | NO | - | BACKEND_AUTO |
| 3 | `equipment_id` | uuid | YES | - | OPTIONAL |
| 4 | `title` | text | NO | - | REQUIRED |
| 5 | `description` | text | YES | - | OPTIONAL |
| 6 | `type` | work_order_type | NO | 'scheduled' | REQUIRED |
| 7 | `priority` | work_order_priority | NO | 'routine' | REQUIRED |
| 8 | `status` | work_order_status | NO | 'planned' | BACKEND_AUTO |
| 9 | `due_date` | date | YES | - | OPTIONAL |
| 10 | `due_hours` | integer | YES | - | OPTIONAL |
| 11 | `last_completed_date` | date | YES | - | CONTEXT |
| 12 | `last_completed_hours` | integer | YES | - | CONTEXT |
| 13 | `frequency` | jsonb | YES | - | CONTEXT |
| 14 | `created_by` | uuid | NO | - | BACKEND_AUTO |
| 15 | `updated_by` | uuid | YES | - | BACKEND_AUTO |
| 16 | `metadata` | jsonb | YES | '{}' | OPTIONAL |
| 17 | `created_at` | timestamptz | NO | now() | BACKEND_AUTO |
| 18 | `updated_at` | timestamptz | NO | now() | BACKEND_AUTO |
| 19 | `wo_number` | text | YES | - | BACKEND_AUTO |
| 20 | `deleted_at` | timestamptz | YES | - | BACKEND_AUTO |
| 21 | `deleted_by` | uuid | YES | - | BACKEND_AUTO |
| 22 | `deletion_reason` | text | YES | - | REQUIRED (on archive) |
| 23 | `work_order_type` | text | YES | 'planned' | DEPRECATED |
| 24 | `fault_id` | uuid | YES | - | OPTIONAL |
| 25 | `assigned_to` | uuid | YES | - | OPTIONAL |
| 26 | `completed_by` | uuid | YES | - | BACKEND_AUTO |
| 27 | `completed_at` | timestamptz | YES | - | BACKEND_AUTO |
| 28 | `completion_notes` | text | YES | - | OPTIONAL |
| 29 | `vendor_contact_hash` | text | YES | - | CONTEXT |

### Field Classifications

| Classification | Count | Fields |
|----------------|-------|--------|
| BACKEND_AUTO | 13 | id, yacht_id, status, created_by, updated_by, created_at, updated_at, wo_number, deleted_at, deleted_by, completed_by, completed_at |
| REQUIRED | 4 | title, type, priority, deletion_reason (conditional) |
| OPTIONAL | 6 | equipment_id, description, due_date, due_hours, metadata, fault_id, assigned_to, completion_notes |
| CONTEXT | 4 | last_completed_date, last_completed_hours, frequency, vendor_contact_hash |
| DEPRECATED | 1 | work_order_type |

### Constraints

| Type | Name | Details |
|------|------|---------|
| PK | id | Primary key |
| FK | yacht_id → yacht_registry(id) | ON DELETE CASCADE |
| FK | equipment_id → pms_equipment(id) | ON DELETE SET NULL |
| FK | fault_id → pms_faults(id) | ON DELETE SET NULL |
| NOT NULL | Multiple | id, yacht_id, title, type, priority, status, created_by, created_at, updated_at |

### Triggers

| Trigger | Event | Function |
|---------|-------|----------|
| no_hard_delete_work_orders | BEFORE DELETE | prevent_hard_delete() |
| set_updated_at_work_orders | BEFORE UPDATE | update_updated_at() |
| trg_work_order_insert_predictive | AFTER INSERT | on_work_order_insert_notify_predictive() |
| trg_work_order_update_predictive | AFTER UPDATE | on_work_order_update_notify_predictive() |

---

## 2.2 SECONDARY TABLE: pms_work_order_checklist

**Row Count**: 11,742
**Columns**: 24
**Has yacht_id**: YES
**RLS**: ⚠️ Mixed patterns (functionally secure)

### Schema

| # | Column | Type | Nullable | Default |
|---|--------|------|----------|---------|
| 1 | `id` | uuid | NO | gen_random_uuid() |
| 2 | `yacht_id` | uuid | NO | - |
| 3 | `work_order_id` | uuid | NO | - |
| 4 | `title` | text | NO | - |
| 5 | `description` | text | YES | - |
| 6 | `notes` | text | YES | - |
| 7 | `sequence` | integer | NO | 0 |
| 8 | `is_completed` | boolean | NO | false |
| 9 | `is_required` | boolean | NO | true |
| 10 | `requires_photo` | boolean | NO | false |
| 11 | `requires_signature` | boolean | NO | false |
| 12 | `completed_at` | timestamptz | YES | - |
| 13 | `completed_by` | uuid | YES | - |
| 14 | `completion_notes` | text | YES | - |
| 15 | `measurement_value` | decimal | YES | - |
| 16 | `measurement_unit` | text | YES | - |
| 17 | `metadata` | jsonb | YES | '{}' |
| 18 | `created_at` | timestamptz | NO | now() |
| 19 | `created_by` | uuid | YES | - |
| 20 | `updated_at` | timestamptz | YES | - |
| 21 | `updated_by` | uuid | YES | - |
| 22 | `deleted_at` | timestamptz | YES | - |
| 23 | `deleted_by` | uuid | YES | - |
| 24 | `deletion_reason` | text | YES | - |

### Constraints

| Type | Details |
|------|---------|
| FK | work_order_id → pms_work_orders(id) ON DELETE CASCADE |

---

## 2.3 SECONDARY TABLE: pms_work_order_notes

**Row Count**: 2,687
**Columns**: 7
**Has yacht_id**: NO
**RLS**: ❌ CROSS-YACHT LEAKAGE (`USING (true)`)

### Schema

| # | Column | Type | Nullable | Default |
|---|--------|------|----------|---------|
| 1 | `id` | uuid | NO | uuid_generate_v4() |
| 2 | `work_order_id` | uuid | NO | - |
| 3 | `note_text` | text | NO | - |
| 4 | `note_type` | text | NO | 'general' |
| 5 | `created_by` | uuid | NO | - |
| 6 | `created_at` | timestamptz | NO | now() |
| 7 | `metadata` | jsonb | YES | '{}' |

### Constraints

| Type | Details |
|------|---------|
| FK | work_order_id → pms_work_orders(id) ON DELETE CASCADE |
| FK | created_by → auth_users_profiles(id) ON DELETE SET NULL |
| CHECK | note_type IN ('general', 'progress', 'issue', 'resolution') |

### BLOCKER B1

**Issue**: SELECT policy uses `USING (true)` - any authenticated user can see ALL notes from ALL yachts.

**Required Fix**: Replace with join-based yacht isolation:
```sql
USING (
    EXISTS (
        SELECT 1 FROM pms_work_orders wo
        WHERE wo.id = pms_work_order_notes.work_order_id
        AND wo.yacht_id = public.get_user_yacht_id()
    )
)
```

---

## 2.4 SECONDARY TABLE: pms_work_order_parts

**Row Count**: 117
**Columns**: 9
**Has yacht_id**: NO
**RLS**: ❌ CROSS-YACHT LEAKAGE (`USING (true)`)

### Schema

| # | Column | Type | Nullable | Default |
|---|--------|------|----------|---------|
| 1 | `id` | uuid | NO | gen_random_uuid() |
| 2 | `work_order_id` | uuid | NO | - |
| 3 | `part_id` | uuid | NO | - |
| 4 | `quantity` | integer | YES | 1 |
| 5 | `notes` | text | YES | - |
| 6 | `created_at` | timestamptz | YES | now() |
| 7 | `updated_at` | timestamptz | YES | now() |
| 8 | `deleted_at` | timestamptz | YES | - |
| 9 | `deleted_by` | uuid | YES | - |

### Constraints

| Type | Details |
|------|---------|
| FK | work_order_id → pms_work_orders(id) ON DELETE CASCADE |
| FK | part_id → pms_parts(id) ON DELETE CASCADE |
| UNIQUE | (work_order_id, part_id) |

### BLOCKER B2

**Issue**: SELECT policy uses `USING (true)` - any authenticated user can see ALL parts assignments from ALL yachts.

**Note**: There IS a proper join-based policy ("Users can view work order parts") but it's bypassed by the `USING (true)` policy.

**Required Fix**: DROP the `USING (true)` policy.

---

## 2.5 SECONDARY TABLE: pms_work_order_history

**Row Count**: 0
**Columns**: 14
**Has yacht_id**: YES
**RLS**: ✅ CANONICAL

### Schema

| # | Column | Type | Nullable | Default |
|---|--------|------|----------|---------|
| 1 | `id` | uuid | NO | gen_random_uuid() |
| 2 | `yacht_id` | uuid | NO | - |
| 3 | `work_order_id` | uuid | NO | - |
| 4 | `equipment_id` | uuid | YES | - |
| 5 | `completed_by` | uuid | YES | - |
| 6 | `completed_at` | timestamptz | YES | - |
| 7 | `notes` | text | YES | - |
| 8 | `hours_logged` | integer | YES | - |
| 9 | `status_on_completion` | text | YES | - |
| 10 | `parts_used` | jsonb | YES | '[]' |
| 11 | `documents_used` | jsonb | YES | '[]' |
| 12 | `faults_related` | jsonb | YES | '[]' |
| 13 | `metadata` | jsonb | YES | '{}' |
| 14 | `created_at` | timestamptz | NO | now() |

### Constraints

| Type | Details |
|------|---------|
| FK | work_order_id → pms_work_orders(id) ON DELETE CASCADE |
| FK | equipment_id → pms_equipment(id) ON DELETE SET NULL |
| FK | yacht_id → yacht_registry(id) ON DELETE CASCADE |

---

## 2.6 RELATED TABLE: pms_part_usage

**Row Count**: 8
**Columns**: 11
**Has yacht_id**: YES
**RLS**: ❌ CROSS-YACHT LEAKAGE (`USING (true)`)

### Schema

| # | Column | Type | Nullable | Default |
|---|--------|------|----------|---------|
| 1 | `id` | uuid | NO | uuid_generate_v4() |
| 2 | `yacht_id` | uuid | NO | - |
| 3 | `part_id` | uuid | NO | - |
| 4 | `quantity` | integer | NO | - |
| 5 | `work_order_id` | uuid | YES | - |
| 6 | `equipment_id` | uuid | YES | - |
| 7 | `usage_reason` | text | NO | - |
| 8 | `notes` | text | YES | - |
| 9 | `used_by` | uuid | NO | - |
| 10 | `used_at` | timestamptz | NO | now() |
| 11 | `metadata` | jsonb | YES | '{}' |

### Constraints

| Type | Details |
|------|---------|
| FK | work_order_id → pms_work_orders(id) ON DELETE SET NULL |
| FK | part_id → pms_parts(id) ON DELETE RESTRICT |
| FK | equipment_id → pms_equipment(id) ON DELETE SET NULL |
| CHECK | quantity > 0 |
| CHECK | usage_reason IN ('work_order', 'preventive_maintenance', 'emergency_repair', 'testing', 'other') |

### BLOCKER B3

**Issue**: SELECT policy uses `USING (true)` - any authenticated user can see ALL part usage from ALL yachts.

**Required Fix**: Replace with:
```sql
USING (yacht_id = public.get_user_yacht_id())
```

---

## 2.7 CANONICAL FUNCTIONS

| Function | Location | Status |
|----------|----------|--------|
| `public.get_user_yacht_id()` | Verified in production | ✅ DEPLOYED |
| `public.get_user_role()` | Verified in production | ✅ DEPLOYED |
| `public.is_manager()` | Verified in production | ✅ DEPLOYED |
| `public.generate_wo_number(uuid)` | 02_p0_actions.sql:391 | ✅ DEPLOYED |
| `public.deduct_part_inventory(...)` | 02_p0_actions.sql:424 | ✅ DEPLOYED |
| `cascade_wo_status_to_fault()` | - | ❌ NOT DEPLOYED |

---

## 2.8 ENUM VALUES

### work_order_status
```
planned | in_progress | completed | deferred | cancelled
```

### work_order_priority
```
routine | important | critical | emergency
```

### work_order_type
```
scheduled | corrective | unplanned | preventive
```

### note_type (pms_work_order_notes)
```
general | progress | issue | resolution
```

### usage_reason (pms_part_usage)
```
work_order | preventive_maintenance | emergency_repair | testing | other
```

---

## 2.9 TABLE SUMMARY

| Table | Columns | yacht_id | RLS | Security |
|-------|---------|----------|-----|----------|
| pms_work_orders | 29 | YES | ✅ | CANONICAL |
| pms_work_order_checklist | 24 | YES | ⚠️ | Mixed but secure |
| pms_work_order_notes | 7 | NO | ❌ | CROSS-YACHT LEAKAGE |
| pms_work_order_parts | 9 | NO | ❌ | CROSS-YACHT LEAKAGE |
| pms_work_order_history | 14 | YES | ✅ | CANONICAL |
| pms_part_usage | 11 | YES | ❌ | CROSS-YACHT LEAKAGE |

---

## PHASE 2 GATE: COMPLETE

| Check | Status |
|-------|--------|
| 2.1 Primary table schema documented | ✅ |
| 2.2-2.6 All secondary tables documented | ✅ |
| 2.7 Canonical functions verified | ✅ |
| 2.8 Enum values documented | ✅ |
| 2.9 Security status per table | ✅ |
| All column counts verified against snapshot | ✅ |
| No phantom columns documented | ✅ |

**Proceeding to Phase 3: Entity Graph**
