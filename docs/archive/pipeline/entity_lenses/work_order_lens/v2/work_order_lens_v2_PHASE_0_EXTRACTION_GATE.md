# Work Order Lens v2 - PHASE 0: Schema Extraction & Verification GATE

**Status**: VERIFIED
**Source**: Production Database Snapshot (`db_truth_snapshot.md`)
**Generated**: 2026-01-24
**Snapshot Date**: 2026-01-24T06:35:34

---

## v1 ERRORS CORRECTED IN THIS EXTRACTION

| Error ID | v1 Claim | Production Truth | Impact |
|----------|----------|------------------|--------|
| E1 | pms_work_order_parts has yacht_id | **NO yacht_id** (9 columns) | Phantom column |
| E2 | pms_work_orders uses legacy user_profiles RLS | Uses **canonical get_user_yacht_id()** | Mischaracterized |
| E3 | pms_work_order_history has "NO RLS" | Has **proper canonical RLS** | Mischaracterized |
| E4 | pms_work_order_notes "wrong table reference" | Has `USING (true)` = **CROSS-YACHT LEAKAGE** | Underspecified |
| E5 | pms_part_usage not documented | **11 columns, HAS yacht_id** | Missing table |
| E6 | created_by classified as REQUIRED | Should be **BACKEND_AUTO** (set from auth.uid()) | Wrong classification |

---

## 1. PRIMARY TABLE: pms_work_orders

**Row Count**: 2,820
**Columns**: 29
**yacht_id**: YES

### Schema (Verified)

| Column | Type | Nullable | Default | Classification |
|--------|------|----------|---------|----------------|
| `id` | uuid | NO | gen_random_uuid() | BACKEND_AUTO |
| `yacht_id` | uuid | NO | - | BACKEND_AUTO |
| `equipment_id` | uuid | YES | - | OPTIONAL |
| `title` | text | NO | - | REQUIRED |
| `description` | text | YES | - | OPTIONAL |
| `type` | work_order_type | NO | 'scheduled' | REQUIRED |
| `priority` | work_order_priority | NO | 'routine' | REQUIRED |
| `status` | work_order_status | NO | 'planned' | BACKEND_AUTO |
| `due_date` | date | YES | - | OPTIONAL |
| `due_hours` | integer | YES | - | OPTIONAL |
| `last_completed_date` | date | YES | - | CONTEXT |
| `last_completed_hours` | integer | YES | - | CONTEXT |
| `frequency` | jsonb | YES | - | CONTEXT |
| `created_by` | uuid | NO | - | **BACKEND_AUTO** |
| `updated_by` | uuid | YES | - | BACKEND_AUTO |
| `metadata` | jsonb | YES | '{}' | OPTIONAL |
| `created_at` | timestamptz | NO | now() | BACKEND_AUTO |
| `updated_at` | timestamptz | NO | now() | BACKEND_AUTO |
| `wo_number` | text | YES | - | BACKEND_AUTO |
| `deleted_at` | timestamptz | YES | - | BACKEND_AUTO |
| `deleted_by` | uuid | YES | - | BACKEND_AUTO |
| `deletion_reason` | text | YES | - | REQUIRED (on archive) |
| `work_order_type` | text | YES | 'planned' | **DEPRECATED** |
| `fault_id` | uuid | YES | - | OPTIONAL |
| `assigned_to` | uuid | YES | - | OPTIONAL |
| `completed_by` | uuid | YES | - | BACKEND_AUTO |
| `completed_at` | timestamptz | YES | - | BACKEND_AUTO |
| `completion_notes` | text | YES | - | OPTIONAL |
| `vendor_contact_hash` | text | YES | - | CONTEXT |

### RLS Policies (PRODUCTION)

**RLS Status**: ✅ ENABLED - **CANONICAL PATTERN**

| Policy Name | Operation | Condition | Security |
|-------------|-----------|-----------|----------|
| Users can view work orders | SELECT | `yacht_id = get_user_yacht_id()` | ✅ CANONICAL |
| Engineers can create work orders | INSERT | `yacht_id = get_user_yacht_id() AND get_user_role() IN [...]` | ✅ CANONICAL + ROLE |
| Engineers can update work orders | UPDATE | `yacht_id = get_user_yacht_id() AND get_user_role() IN [...]` | ✅ CANONICAL + ROLE |
| Managers can delete work orders | DELETE | `yacht_id = get_user_yacht_id() AND is_manager()` | ✅ CANONICAL + ROLE |
| Service role full access | ALL | `true` | ✅ SERVICE_ROLE |

### Triggers (PRODUCTION)

| Trigger | Event | Function |
|---------|-------|----------|
| no_hard_delete_work_orders | BEFORE DELETE | prevent_hard_delete() |
| set_updated_at_work_orders | BEFORE UPDATE | update_updated_at() |
| trg_work_order_insert_predictive | AFTER INSERT | on_work_order_insert_notify_predictive() |
| trg_work_order_update_predictive | AFTER UPDATE | on_work_order_update_notify_predictive() |

### FK Constraints (PRODUCTION)

| Column | References | On Delete |
|--------|------------|-----------|
| yacht_id | yacht_registry(id) | CASCADE |
| equipment_id | pms_equipment(id) | SET NULL |
| fault_id | pms_faults(id) | SET NULL |

---

## 2. SECONDARY TABLE: pms_work_order_checklist

**Row Count**: 11,742
**Columns**: 24
**yacht_id**: YES

### Schema (Verified)

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| `id` | uuid | NO | gen_random_uuid() |
| `yacht_id` | uuid | NO | - |
| `work_order_id` | uuid | NO | - |
| `title` | text | NO | - |
| `description` | text | YES | - |
| `notes` | text | YES | - |
| `sequence` | integer | NO | 0 |
| `is_completed` | boolean | NO | false |
| `is_required` | boolean | NO | true |
| `requires_photo` | boolean | NO | false |
| `requires_signature` | boolean | NO | false |
| `completed_at` | timestamptz | YES | - |
| `completed_by` | uuid | YES | - |
| `completion_notes` | text | YES | - |
| `measurement_value` | decimal | YES | - |
| `measurement_unit` | text | YES | - |
| `metadata` | jsonb | YES | '{}' |
| `created_at` | timestamptz | NO | now() |
| `created_by` | uuid | YES | - |
| `updated_at` | timestamptz | YES | - |
| `updated_by` | uuid | YES | - |
| `deleted_at` | timestamptz | YES | - |
| `deleted_by` | uuid | YES | - |
| `deletion_reason` | text | YES | - |

### RLS Policies (PRODUCTION)

**RLS Status**: ✅ ENABLED - **MIXED PATTERN** (9 policies)

Has overlapping policies using:
1. JWT claims pattern: `yacht_id::text = (request.jwt.claims->>'yacht_id')`
2. auth_users_profiles subquery: `yacht_id IN (SELECT yacht_id FROM auth_users_profiles...)`
3. Canonical pattern: `yacht_id = get_user_yacht_id()`

**Security**: ⚠️ FUNCTIONALLY SECURE but inconsistent

---

## 3. SECONDARY TABLE: pms_work_order_notes

**Row Count**: 2,687
**Columns**: 7
**yacht_id**: **NO**

### Schema (Verified)

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| `id` | uuid | NO | uuid_generate_v4() |
| `work_order_id` | uuid | NO | - |
| `note_text` | text | NO | - |
| `note_type` | text | NO | 'general' |
| `created_by` | uuid | NO | - |
| `created_at` | timestamptz | NO | now() |
| `metadata` | jsonb | YES | '{}' |

**Note Types**: `general`, `progress`, `issue`, `resolution`

### RLS Policies (PRODUCTION)

**RLS Status**: ✅ ENABLED - **SECURITY HOLE**

| Policy Name | Operation | Condition | Security |
|-------------|-----------|-----------|----------|
| Authenticated users can view notes | SELECT | `USING (true)` | ❌ **CROSS-YACHT LEAKAGE** |
| Service role full access | ALL | `true` | ✅ SERVICE_ROLE |
| pms_work_order_notes_yacht_isolation | ALL | Uses `app.current_yacht_id` setting | ⚠️ NON-CANONICAL |

**BLOCKER**: `USING (true)` on SELECT means ANY authenticated user can see ALL notes from ALL yachts.

---

## 4. SECONDARY TABLE: pms_work_order_parts

**Row Count**: 117
**Columns**: 9
**yacht_id**: **NO**

### Schema (Verified)

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| `id` | uuid | NO | gen_random_uuid() |
| `work_order_id` | uuid | NO | - |
| `part_id` | uuid | NO | - |
| `quantity` | integer | YES | 1 |
| `notes` | text | YES | - |
| `created_at` | timestamptz | YES | now() |
| `updated_at` | timestamptz | YES | now() |
| `deleted_at` | timestamptz | YES | - |
| `deleted_by` | uuid | YES | - |

**Note**: Unique constraint on (work_order_id, part_id)

### RLS Policies (PRODUCTION)

**RLS Status**: ✅ ENABLED - **SECURITY HOLE**

| Policy Name | Operation | Condition | Security |
|-------------|-----------|-----------|----------|
| Authenticated users can view parts | SELECT | `USING (true)` | ❌ **CROSS-YACHT LEAKAGE** |
| Engineers can manage work order parts | ALL | Via join to pms_work_orders + yacht_id check | ✅ SECURE |
| Users can view work order parts | SELECT | Via join to pms_work_orders + yacht_id check | ✅ SECURE |
| Service role full access | ALL | `true` | ✅ SERVICE_ROLE |

**BLOCKER**: Policy conflict - `USING (true)` bypasses the secure join-based policy.

---

## 5. SECONDARY TABLE: pms_work_order_history

**Row Count**: 0
**Columns**: 14
**yacht_id**: YES

### Schema (Verified)

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| `id` | uuid | NO | gen_random_uuid() |
| `yacht_id` | uuid | NO | - |
| `work_order_id` | uuid | NO | - |
| `equipment_id` | uuid | YES | - |
| `completed_by` | uuid | YES | - |
| `completed_at` | timestamptz | YES | - |
| `notes` | text | YES | - |
| `hours_logged` | integer | YES | - |
| `status_on_completion` | text | YES | - |
| `parts_used` | jsonb | YES | '[]' |
| `documents_used` | jsonb | YES | '[]' |
| `faults_related` | jsonb | YES | '[]' |
| `metadata` | jsonb | YES | '{}' |
| `created_at` | timestamptz | NO | now() |

### RLS Policies (PRODUCTION)

**RLS Status**: ✅ ENABLED - **CANONICAL PATTERN**

| Policy Name | Operation | Condition | Security |
|-------------|-----------|-----------|----------|
| Users can view work order history | SELECT | `yacht_id = get_user_yacht_id()` | ✅ CANONICAL |
| Engineers can add history | INSERT | `yacht_id = get_user_yacht_id() AND get_user_role() IN [...]` | ✅ CANONICAL + ROLE |
| Service role full access | ALL | `true` | ✅ SERVICE_ROLE |

---

## 6. RELATED TABLE: pms_part_usage (MISSING FROM v1)

**Row Count**: 8
**Columns**: 11
**yacht_id**: YES

### Schema (Verified)

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| `id` | uuid | NO | uuid_generate_v4() |
| `yacht_id` | uuid | NO | - |
| `part_id` | uuid | NO | - |
| `quantity` | integer | NO | - |
| `work_order_id` | uuid | YES | - |
| `equipment_id` | uuid | YES | - |
| `usage_reason` | text | NO | - |
| `notes` | text | YES | - |
| `used_by` | uuid | NO | - |
| `used_at` | timestamptz | NO | now() |
| `metadata` | jsonb | YES | '{}' |

**Usage Reasons**: `work_order`, `preventive_maintenance`, `emergency_repair`, `testing`, `other`

### RLS Policies (PRODUCTION)

**RLS Status**: ✅ ENABLED - **SECURITY HOLE**

| Policy Name | Operation | Condition | Security |
|-------------|-----------|-----------|----------|
| Authenticated users can view usage | SELECT | `USING (true)` | ❌ **CROSS-YACHT LEAKAGE** |
| Service role full access | ALL | `true` | ✅ SERVICE_ROLE |
| pms_part_usage_yacht_isolation | ALL | Uses `app.current_yacht_id` setting | ⚠️ NON-CANONICAL |

**BLOCKER**: `USING (true)` on SELECT means ANY authenticated user can see ALL part usage from ALL yachts.

---

## 7. SECURITY SUMMARY

### Cross-Yacht Data Leakage

| Table | SELECT Policy | Can User A See User B's Data? |
|-------|---------------|-------------------------------|
| pms_work_orders | `yacht_id = get_user_yacht_id()` | ❌ No |
| pms_work_order_checklist | Multiple patterns | ❌ No |
| pms_work_order_notes | `USING (true)` | ✅ **YES - SECURITY HOLE** |
| pms_work_order_parts | `USING (true)` | ✅ **YES - SECURITY HOLE** |
| pms_work_order_history | `yacht_id = get_user_yacht_id()` | ❌ No |
| pms_part_usage | `USING (true)` | ✅ **YES - SECURITY HOLE** |

### Blocker List for v2

| ID | Table | Issue | Severity |
|----|-------|-------|----------|
| **B1** | pms_work_order_notes | `USING (true)` SELECT bypasses yacht isolation | CRITICAL |
| **B2** | pms_work_order_parts | `USING (true)` SELECT bypasses yacht isolation | CRITICAL |
| **B3** | pms_part_usage | `USING (true)` SELECT bypasses yacht isolation | CRITICAL |
| **B4** | pms_work_orders | Missing `cascade_wo_status_to_fault()` trigger | HIGH |
| **B5** | pms_work_order_checklist | Inconsistent RLS patterns (works but messy) | LOW |

---

## 8. ENUM VALUES (Verified)

### work_order_status
`planned`, `in_progress`, `completed`, `deferred`, `cancelled`

### work_order_priority
`routine`, `important`, `critical`, `emergency`

### work_order_type
`scheduled`, `corrective`, `unplanned`, `preventive`

### note_type (pms_work_order_notes)
`general`, `progress`, `issue`, `resolution`

### usage_reason (pms_part_usage)
`work_order`, `preventive_maintenance`, `emergency_repair`, `testing`, `other`

---

## 9. CANONICAL FUNCTIONS (Verified in Production)

| Function | Verified | Usage |
|----------|----------|-------|
| `public.get_user_yacht_id()` | ✅ | Used in pms_work_orders, pms_work_order_history RLS |
| `public.get_user_role()` | ✅ | Used in role-based RLS policies |
| `public.is_manager()` | ✅ | Used in delete policy |
| `public.generate_wo_number(uuid)` | ✅ | Verified in 02_p0_actions.sql:391 |
| `public.deduct_part_inventory(...)` | ✅ | Verified in 02_p0_actions.sql:424 |

### Missing Functions

| Function | Status | Needed For |
|----------|--------|------------|
| `cascade_wo_status_to_fault()` | NOT DEPLOYED | Complete WO, Archive WO |

---

## PHASE 0 GATE: PASSED

| Verification | Status |
|--------------|--------|
| All 6 tables extracted from production snapshot | ✅ |
| Column counts verified | ✅ |
| yacht_id presence/absence confirmed | ✅ |
| ACTUAL RLS policies documented (not assumed) | ✅ |
| Security holes identified with correct description | ✅ |
| Enum values verified from pg_enum | ✅ |
| Canonical functions verified | ✅ |
| v1 errors catalogued | ✅ |

**Proceeding to Phase 1: Scope Definition**
