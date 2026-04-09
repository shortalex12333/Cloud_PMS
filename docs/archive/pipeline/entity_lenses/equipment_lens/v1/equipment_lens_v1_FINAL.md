# Entity Lens: Equipment

**Status**: v1 - PRODUCTION READY
**Last Updated**: 2026-01-25
**Schema Source**: Production Supabase Database (db_truth_snapshot.md)
**Operating Procedure**: `LENS_BUILDER_OPERATING_PROCEDURE.md`
**Gold Standard Reference**: `fault_lens_v5_FINAL.md`

---

# BLOCKERS (must resolve before lens is shippable)

| ID | Blocker | Affects | Resolution |
|----|---------|---------|------------|
| ✅ | None | - | Equipment Lens is fully shippable |

> **NOTE**: Equipment RLS uses canonical `get_user_yacht_id()` pattern. All policies properly deployed.

---

# PART 0: CANONICAL HELPERS

## Yacht ID Resolution

**Deployed function** (canonical):

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

**Usage convention**:
- All RLS policies use `public.get_user_yacht_id()` for yacht isolation
- All procedural SQL (INSERTs in handlers) use `public.get_user_yacht_id()`
- Single source of truth - no competing patterns

---

## Audit `entity_type` Convention

| Value | Table |
|-------|-------|
| `equipment` | pms_equipment |
| `equipment_part_bom` | pms_equipment_parts_bom |
| `fault` | pms_faults |
| `work_order` | pms_work_orders |
| `note` | pms_notes |
| `attachment` | pms_attachments |

> **INVARIANT**: Use `entity_type = 'equipment'` in pms_audit_log for all equipment actions.

---

## Signature Invariant

`pms_audit_log.signature` is **NOT NULL**. Convention:

| Scenario | Value |
|----------|-------|
| Non-signature action | `'{}'::jsonb` (empty object) |
| Signature-required action | Full signature payload |

> **INVARIANT**: Signature is always present. Empty object `{}` means "signature not required."

---

# PART 1: EXACT DATABASE SCHEMA

## Table: `pms_equipment`

**Production DB Columns** (24 total):

| Column | PostgreSQL Type | Nullable | Classification | Notes |
|--------|-----------------|----------|----------------|-------|
| `id` | uuid | NOT NULL | BACKEND_AUTO | PK, gen_random_uuid() |
| `yacht_id` | uuid | NOT NULL | BACKEND_AUTO | FK → yacht_registry(id), from auth context |
| `parent_id` | uuid | YES | OPTIONAL | FK → pms_equipment(id), hierarchical relationship |
| `name` | text | NOT NULL | REQUIRED | Display name (unique per yacht) |
| `code` | text | YES | OPTIONAL | Equipment identifier code (e.g., ME-01, GEN-02) |
| `description` | text | YES | OPTIONAL | Long-form details |
| `location` | text | YES | OPTIONAL | Physical location on vessel |
| `manufacturer` | text | YES | OPTIONAL | OEM name |
| `model` | text | YES | OPTIONAL | Model number |
| `serial_number` | text | YES | OPTIONAL | Serial number |
| `installed_date` | date | YES | OPTIONAL | Date equipment was installed |
| `criticality` | equipment_criticality | YES | OPTIONAL | Enum: low, medium, high, critical. Default: 'medium' |
| `system_type` | text | YES | OPTIONAL | System classification (see enum below) |
| `status` | text | YES | BACKEND_AUTO | Default: 'operational'. Values: operational, degraded, failed, maintenance, decommissioned |
| `attention_flag` | boolean | YES | BACKEND_AUTO | Default: false. Highlights equipment needing attention |
| `attention_reason` | text | YES | CONTEXT | Reason for attention flag |
| `attention_updated_at` | timestamp with time zone | YES | BACKEND_AUTO | When attention flag last changed |
| `metadata` | jsonb | YES | BACKEND_AUTO | Additional data |
| `created_at` | timestamp with time zone | NOT NULL | BACKEND_AUTO | Default: NOW() |
| `updated_at` | timestamp with time zone | NOT NULL | BACKEND_AUTO | Trigger: update_updated_at |
| `updated_by` | uuid | YES | BACKEND_AUTO | Set on any UPDATE |
| `deleted_at` | timestamp with time zone | YES | BACKEND_AUTO | Soft delete timestamp |
| `deleted_by` | uuid | YES | BACKEND_AUTO | Who soft-deleted |
| `deletion_reason` | text | YES | OPTIONAL | Why soft-deleted |

**Row Count**: 560

---

## Status Values (CHECK Constraint)

```sql
CHECK (status = ANY (ARRAY[
    'operational'::text,
    'degraded'::text,
    'failed'::text,
    'maintenance'::text,
    'decommissioned'::text
]))
```

| Status | Meaning | Typical Transition |
|--------|---------|-------------------|
| `operational` | Fully functional | Default state |
| `degraded` | Working with reduced capability | From operational when issues detected |
| `failed` | Not operational | From degraded/operational on breakdown |
| `maintenance` | Under scheduled maintenance | From operational when WO started |
| `decommissioned` | Permanently out of service | Terminal state |

---

## Criticality Enum (`equipment_criticality`)

```sql
-- Values: 'low', 'medium', 'high', 'critical'
```

| Criticality | Meaning | Examples |
|-------------|---------|----------|
| `low` | Failure has minimal impact | Interior lighting, decorative items |
| `medium` | Failure affects comfort/convenience | HVAC secondary units, backup systems |
| `high` | Failure significantly impacts operations | Generator, watermaker, stabilizers |
| `critical` | Failure endangers safety or regulatory compliance | Main engines, steering, fire suppression |

---

## System Type Values (Partial - from `system_type` enum)

```sql
-- Values extracted from database:
'main_engine', 'generator', 'hvac', 'electrical', 'hydraulic',
'plumbing', 'fuel', 'freshwater', 'blackwater', 'graywater',
'fire_suppression', 'steering', 'stabilizers', 'thrusters',
'anchor_windlass', 'propulsion', 'navigation', 'communication',
'radar', 'ecdis', 'autopilot', 'gyro', 'lifesaving', 'firefighting',
'security', 'cctv', 'galley', 'laundry', 'housekeeping',
'provisions', 'tender', 'toys', 'dive', 'mooring', 'deck_equipment',
'av_entertainment', 'network', 'satellite', 'lighting_control',
'crew_management', 'guest_services', 'finance', 'compliance',
'charter', 'general', 'multi_system', 'vessel_wide'
```

---

## Indexes (Production)

| Index | Columns | Purpose |
|-------|---------|---------|
| `equipment_pkey` | id | Primary key |
| `idx_equipment_yacht_id` | yacht_id | Yacht isolation queries |
| `idx_equipment_code` | code | Lookup by equipment code |
| `idx_equipment_parent_id` | parent_id | Hierarchical queries |
| `idx_equipment_system_type` | system_type | Filter by system |
| `idx_equipment_criticality` | criticality | Priority filtering |
| `idx_equipment_location` | yacht_id, location | Location queries |
| `idx_equipment_manufacturer` | yacht_id, manufacturer | Manufacturer queries |
| `idx_equipment_attention_flag` | attention_flag (WHERE true) | Attention items |
| `idx_pms_equipment_status` | yacht_id, status | Status filtering |

---

## Triggers

| Trigger | Event | Function | Purpose |
|---------|-------|----------|---------|
| `no_hard_delete_equipment` | BEFORE DELETE | prevent_hard_delete() | Enforces soft delete |

> **DELETION DOCTRINE**: Equipment uses soft delete via `deleted_at`. Hard deletes are blocked by trigger. Decommissioned equipment remains queryable for historical analysis.

---

## Table: `pms_equipment_parts_bom` (Related)

**Production DB Columns** (7 total):

| Column | PostgreSQL Type | Nullable | Classification | Notes |
|--------|-----------------|----------|----------------|-------|
| `id` | uuid | NOT NULL | BACKEND_AUTO | PK |
| `yacht_id` | uuid | NOT NULL | BACKEND_AUTO | FK → yacht_registry(id) |
| `equipment_id` | uuid | NOT NULL | CONTEXT | FK → pms_equipment(id) |
| `part_id` | uuid | NOT NULL | CONTEXT | FK → pms_parts(id) |
| `quantity_required` | integer | YES | OPTIONAL | Default: 1 |
| `notes` | text | YES | OPTIONAL | BOM notes |
| `created_at` | timestamp with time zone | NOT NULL | BACKEND_AUTO | Default: NOW() |

**Row Count**: 15

**Purpose**: Links parts to equipment (Bill of Materials). Used for:
- Determining required parts for maintenance
- Stock level recommendations
- Parts consumption forecasting

---

# PART 2: MICRO-ACTIONS WITH FIELD CLASSIFICATION

> **ACTION ACTIVATION DOCTRINE**: Actions are NOT visible on search results lists. When equipment becomes the **focused entity**, its context actions become available. No ambient buttons on result cards.

---

## Action 1: `update_equipment_status`

**Purpose**: Change equipment operational status

**Allowed Roles**: Engineers (chief_engineer, eto, manager)

**Tables Written**:
- `pms_equipment` (UPDATE)
- `pms_audit_log` (INSERT)

**Field Classification**:

| Field | Table.Column | Classification | Source |
|-------|--------------|----------------|--------|
| `status` | pms_equipment.status | REQUIRED | User dropdown |
| `attention_flag` | pms_equipment.attention_flag | BACKEND_AUTO | Derived from status |
| `attention_reason` | pms_equipment.attention_reason | CONTEXT | Reason if status not 'operational' |
| `attention_updated_at` | pms_equipment.attention_updated_at | BACKEND_AUTO | NOW() if attention changes |
| `updated_at` | pms_equipment.updated_at | BACKEND_AUTO | NOW() |
| `updated_by` | pms_equipment.updated_by | BACKEND_AUTO | auth.uid() |

**Business Rules**:
- Status `failed` → automatically sets `attention_flag = true`
- Status `operational` → optionally clears `attention_flag`
- Status `decommissioned` → requires manager role

**Real SQL**:
```sql
-- 1. Update equipment status
UPDATE pms_equipment
SET
    status = :new_status,                    -- REQUIRED (user input)
    attention_flag = CASE
        WHEN :new_status IN ('failed', 'degraded') THEN true
        WHEN :new_status = 'operational' AND :clear_attention THEN false
        ELSE attention_flag
    END,
    attention_reason = CASE
        WHEN :new_status IN ('failed', 'degraded') THEN COALESCE(:attention_reason, 'Status changed to ' || :new_status)
        WHEN :new_status = 'operational' AND :clear_attention THEN NULL
        ELSE attention_reason
    END,
    attention_updated_at = CASE
        WHEN :new_status IN ('failed', 'degraded', 'operational') THEN NOW()
        ELSE attention_updated_at
    END,
    updated_at = NOW(),
    updated_by = auth.uid()
WHERE id = :equipment_id
  AND yacht_id = public.get_user_yacht_id()  -- RLS enforcement
  AND deleted_at IS NULL
RETURNING id, status, attention_flag;

-- 2. Insert audit log
INSERT INTO pms_audit_log (
    id, yacht_id, entity_type, entity_id, action, user_id,
    old_values, new_values, signature, metadata, created_at
) VALUES (
    gen_random_uuid(),
    public.get_user_yacht_id(),
    'equipment',
    :equipment_id,
    'update_equipment_status',
    auth.uid(),
    jsonb_build_object('status', :old_status, 'attention_flag', :old_attention),
    jsonb_build_object('status', :new_status, 'attention_flag', :new_attention, 'reason', :attention_reason),
    '{}'::jsonb,                     -- Non-signature action
    jsonb_build_object('session_id', :session_id, 'source', 'equipment_lens'),
    NOW()
);
```

**Ledger UI Event**:
```json
{
  "event": "equipment_status_changed",
  "message": "Generator #1 status changed to 'maintenance'",
  "entity_type": "equipment",
  "entity_id": "equipment_uuid",
  "user_name": "John Smith",
  "timestamp": "2026-01-25T10:30:00Z",
  "link": "/equipment/equipment_uuid"
}
```

---

## Action 2: `add_equipment_note`

**Purpose**: Add observation/maintenance note to equipment record

**Allowed Roles**: All Crew (TIER 1+)

**Tables Written**:
- `pms_notes` (INSERT)
- `pms_audit_log` (INSERT)

**Field Classification**:

| Field | Table.Column | Classification | Source |
|-------|--------------|----------------|--------|
| `id` | pms_notes.id | BACKEND_AUTO | gen_random_uuid() |
| `yacht_id` | pms_notes.yacht_id | BACKEND_AUTO | public.get_user_yacht_id() |
| `equipment_id` | pms_notes.equipment_id | CONTEXT | From focused equipment |
| `text` | pms_notes.text | REQUIRED | User input |
| `note_type` | pms_notes.note_type | OPTIONAL | User dropdown, default: 'observation' |
| `attachments` | pms_notes.attachments | OPTIONAL | Inline refs |
| `metadata` | pms_notes.metadata | BACKEND_AUTO | Session context |
| `created_by` | pms_notes.created_by | BACKEND_AUTO | auth.uid() |
| `created_at` | pms_notes.created_at | BACKEND_AUTO | NOW() |

**Real SQL**:
```sql
-- 1. Insert note
INSERT INTO pms_notes (
    id, yacht_id, equipment_id, text, note_type,
    attachments, metadata, created_by, created_at, updated_at
) VALUES (
    gen_random_uuid(),
    public.get_user_yacht_id(),
    :equipment_id,                   -- CONTEXT
    :text,                           -- REQUIRED
    COALESCE(:note_type, 'observation'),
    COALESCE(:attachments, '[]'::jsonb),
    jsonb_build_object('session_id', :session_id, 'source', 'equipment_lens'),
    auth.uid(),
    NOW(),
    NOW()
)
RETURNING id;

-- 2. Insert audit log
INSERT INTO pms_audit_log (
    id, yacht_id, entity_type, entity_id, action, user_id,
    old_values, new_values, signature, metadata, created_at
) VALUES (
    gen_random_uuid(),
    public.get_user_yacht_id(),
    'note',
    :new_note_id,
    'add_equipment_note',
    auth.uid(),
    NULL,
    jsonb_build_object('equipment_id', :equipment_id, 'text', :text, 'note_type', :note_type),
    '{}'::jsonb,
    jsonb_build_object('session_id', :session_id),
    NOW()
);
```

---

## Action 3: `attach_file_to_equipment`

**Purpose**: Upload photo/document to equipment record

**Allowed Roles**: All Crew (TIER 1+)

**Tables Written**:
- `pms_attachments` (INSERT)
- `pms_audit_log` (INSERT)

**Storage Bucket**: `pms-discrepancy-photos`

**Field Classification**:

| Field | Table.Column | Classification | Source |
|-------|--------------|----------------|--------|
| `id` | pms_attachments.id | BACKEND_AUTO | gen_random_uuid() |
| `yacht_id` | pms_attachments.yacht_id | BACKEND_AUTO | public.get_user_yacht_id() |
| `entity_type` | pms_attachments.entity_type | BACKEND_AUTO | 'equipment' |
| `entity_id` | pms_attachments.entity_id | CONTEXT | From focused equipment |
| `file` | (upload) | REQUIRED | User file selection |
| `filename` | pms_attachments.filename | BACKEND_AUTO | Generated UUID + ext |
| `original_filename` | pms_attachments.original_filename | BACKEND_AUTO | From upload |
| `mime_type` | pms_attachments.mime_type | BACKEND_AUTO | Detected |
| `file_size` | pms_attachments.file_size | BACKEND_AUTO | From upload |
| `storage_path` | pms_attachments.storage_path | BACKEND_AUTO | bucket/yacht_id/equipment_id/filename |
| `description` | pms_attachments.description | OPTIONAL | User input |
| `tags` | pms_attachments.tags | OPTIONAL | User input |
| `uploaded_by` | pms_attachments.uploaded_by | BACKEND_AUTO | auth.uid() |
| `uploaded_at` | pms_attachments.uploaded_at | BACKEND_AUTO | NOW() |

**Real SQL**:
```sql
INSERT INTO pms_attachments (
    id, yacht_id, entity_type, entity_id,
    filename, original_filename, mime_type, file_size,
    storage_path, description, tags, metadata,
    uploaded_by, uploaded_at, created_at
) VALUES (
    gen_random_uuid(),
    public.get_user_yacht_id(),
    'equipment',
    :equipment_id,
    :generated_filename,
    :original_filename,
    :detected_mime_type,
    :file_size_bytes,
    'pms-discrepancy-photos/' || public.get_user_yacht_id() || '/equipment/' || :equipment_id || '/' || :generated_filename,
    :description,
    :tags,
    jsonb_build_object('session_id', :session_id, 'source', 'equipment_lens'),
    auth.uid(),
    NOW(),
    NOW()
)
RETURNING id;
```

---

## Action 4: `create_work_order_for_equipment`

**Purpose**: Create a new work order for this equipment (escape hatch to WO Lens)

**Allowed Roles**: Engineers (chief_engineer, eto, deck, interior)

**Tables Written**:
- `pms_work_orders` (INSERT)
- `pms_faults` (INSERT - if type is breakdown/corrective)
- `pms_audit_log` (INSERT)

**Field Classification**:

| Field | Table.Column | Classification | Source |
|-------|--------------|----------------|--------|
| `equipment_id` | pms_work_orders.equipment_id | CONTEXT | From focused equipment |
| `title` | pms_work_orders.title | REQUIRED | User input |
| `description` | pms_work_orders.description | OPTIONAL | User input |
| `type` | pms_work_orders.type | REQUIRED | User dropdown (scheduled, corrective, unplanned, preventive) |
| `priority` | pms_work_orders.priority | REQUIRED | User dropdown (routine, important, critical, emergency) |
| `assigned_to` | pms_work_orders.assigned_to | OPTIONAL | User dropdown |
| `due_date` | pms_work_orders.due_date | OPTIONAL | User date picker |
| `fault_severity` | (form field) | CONTEXT | Only if type is breakdown/corrective |

> **WO-FIRST DOCTRINE**: When type is breakdown/corrective, a fault is auto-created and linked. User provides `fault_severity` (not auto-mapped from WO priority).

**Real SQL**: See `work_order_lens_v2_FINAL.md` - `create_work_order` action.

---

## Action 5: `view_equipment_faults`

**Purpose**: Navigate to Fault history for this equipment (escape hatch)

**Allowed Roles**: All Crew (read-only)

**Tables Written**: None (read-only navigation)

**Tables Read**:
- `pms_faults` (filter by equipment_id)

**Real SQL**:
```sql
SELECT
    f.id,
    f.fault_code,
    f.title,
    f.severity,
    f.status,
    f.detected_at,
    f.resolved_at,
    wo.wo_number
FROM pms_faults f
LEFT JOIN pms_work_orders wo ON f.work_order_id = wo.id
WHERE f.equipment_id = :equipment_id
  AND f.yacht_id = public.get_user_yacht_id()
ORDER BY f.detected_at DESC;

-- Returns list → user can focus on individual fault to enter Fault Lens
```

---

## Action 6: `view_equipment_work_orders`

**Purpose**: Navigate to Work Order history for this equipment (escape hatch)

**Allowed Roles**: All Crew (read-only)

**Tables Written**: None (read-only navigation)

**Tables Read**:
- `pms_work_orders` (filter by equipment_id)

**Real SQL**:
```sql
SELECT
    wo.id,
    wo.wo_number,
    wo.title,
    wo.type,
    wo.priority,
    wo.status,
    wo.due_date,
    wo.completed_at,
    (SELECT name FROM auth_users_profiles WHERE id = wo.assigned_to) AS assigned_to_name
FROM pms_work_orders wo
WHERE wo.equipment_id = :equipment_id
  AND wo.yacht_id = public.get_user_yacht_id()
  AND wo.deleted_at IS NULL
ORDER BY wo.created_at DESC;

-- Returns list → user can focus on individual WO to enter Work Order Lens
```

---

# PART 3: EQUIPMENT HIERARCHY

## Parent-Child Relationships

Equipment supports hierarchical organization via `parent_id` self-reference:

```
Main Engine #1 (id: aaa)
├── Turbocharger (parent_id: aaa)
├── Fuel Injection System (parent_id: aaa)
│   ├── Fuel Pump (parent_id: bbb)
│   └── Injector Rail (parent_id: bbb)
└── Cooling System (parent_id: aaa)
    └── Heat Exchanger (parent_id: ccc)
```

**Query for Children**:
```sql
SELECT * FROM pms_equipment
WHERE parent_id = :equipment_id
  AND yacht_id = public.get_user_yacht_id()
  AND deleted_at IS NULL
ORDER BY name;
```

**Query for Full Hierarchy (Recursive)**:
```sql
WITH RECURSIVE equipment_tree AS (
    -- Base: selected equipment
    SELECT id, name, parent_id, 0 AS depth
    FROM pms_equipment
    WHERE id = :equipment_id
      AND yacht_id = public.get_user_yacht_id()

    UNION ALL

    -- Recursive: children
    SELECT e.id, e.name, e.parent_id, et.depth + 1
    FROM pms_equipment e
    JOIN equipment_tree et ON e.parent_id = et.id
    WHERE e.yacht_id = public.get_user_yacht_id()
      AND e.deleted_at IS NULL
)
SELECT * FROM equipment_tree ORDER BY depth, name;
```

---

# PART 4: ATTENTION FLAG MECHANICS

## Automatic Flag Setting

| Condition | attention_flag | attention_reason |
|-----------|---------------|------------------|
| Status → 'failed' | `true` | "Equipment failed" |
| Status → 'degraded' | `true` | "Equipment degraded" |
| Critical fault created | `true` | "Critical fault: {fault_code}" |
| Overdue maintenance | `true` | "Maintenance overdue: {wo_number}" |

## Manual Flag Clearing

Engineers can manually clear attention_flag when:
- Status returns to 'operational'
- Issue has been acknowledged/addressed

```sql
UPDATE pms_equipment
SET
    attention_flag = false,
    attention_reason = NULL,
    attention_updated_at = NOW(),
    updated_by = auth.uid()
WHERE id = :equipment_id
  AND yacht_id = public.get_user_yacht_id();
```

---

# PART 5: RLS POLICIES

## Table: `pms_equipment`

### ACTUAL DEPLOYED (from db_truth_snapshot.md)

```sql
-- 1. SELECT: All authenticated users can view their yacht's equipment
CREATE POLICY "Users can view yacht equipment" ON pms_equipment
    FOR SELECT TO public
    USING (yacht_id = get_user_yacht_id());

-- 2. ALL: Engineers can manage equipment (INSERT, UPDATE, DELETE)
CREATE POLICY "Engineers can manage equipment" ON pms_equipment
    FOR ALL TO public
    USING (
        (yacht_id = get_user_yacht_id())
        AND (get_user_role() = ANY (ARRAY['chief_engineer'::text, 'eto'::text, 'manager'::text]))
    );

-- 3. ALL: Service role bypass
CREATE POLICY "Service role full access equipment" ON pms_equipment
    FOR ALL TO service_role
    USING (true);
```

**RLS Status**: ✅ CANONICAL - Uses `get_user_yacht_id()` consistently.

---

## Table: `pms_equipment_parts_bom`

### ACTUAL DEPLOYED

```sql
-- 1. SELECT: All authenticated users can view
CREATE POLICY "Users can view equipment parts" ON pms_equipment_parts_bom
    FOR SELECT TO public
    USING (yacht_id = get_user_yacht_id());

-- 2. ALL: Engineers can manage
CREATE POLICY "Engineers can manage equipment parts" ON pms_equipment_parts_bom
    FOR ALL TO public
    USING (
        (yacht_id = get_user_yacht_id())
        AND (get_user_role() = ANY (ARRAY['chief_engineer'::text, 'eto'::text, 'manager'::text]))
    );

-- 3. ALL: Service role bypass
CREATE POLICY "Service role full access equipment_parts" ON pms_equipment_parts_bom
    FOR ALL TO service_role
    USING (true);
```

**RLS Status**: ✅ CANONICAL

---

## Role Hierarchy for Equipment Lens

```
TIER 1 (All Crew):
  - deckhand, steward, chef, etc.
  - Can: VIEW equipment, ADD notes, ATTACH files

TIER 2 (Engineers + Operators):
  - engineer, eto, deck_officer, chief_officer
  - Can: TIER 1 + UPDATE status, CREATE work orders

TIER 3 (HoD + Captain):
  - captain, chief_engineer, chief_steward, purser, manager
  - Can: TIER 2 + MANAGE all equipment, DECOMMISSION equipment
```

---

# PART 6: EQUIPMENT QUERY PATTERNS

## Scenario 1: "Show me Generator #1"

```sql
SELECT
    e.id,
    e.name,
    e.code,
    e.description,
    e.location,
    e.manufacturer,
    e.model,
    e.serial_number,
    e.installed_date,
    e.criticality,
    e.system_type,
    e.status,
    e.attention_flag,
    e.attention_reason,
    -- Parent equipment
    p.name AS parent_name,
    p.code AS parent_code,
    -- Active fault count
    (SELECT COUNT(*) FROM pms_faults f
     WHERE f.equipment_id = e.id
     AND f.status NOT IN ('resolved', 'closed')) AS active_fault_count,
    -- Open WO count
    (SELECT COUNT(*) FROM pms_work_orders wo
     WHERE wo.equipment_id = e.id
     AND wo.status NOT IN ('completed', 'cancelled')
     AND wo.deleted_at IS NULL) AS open_wo_count
FROM pms_equipment e
LEFT JOIN pms_equipment p ON e.parent_id = p.id
WHERE e.id = :equipment_id
  AND e.yacht_id = public.get_user_yacht_id()
  AND e.deleted_at IS NULL;
```

---

## Scenario 2: "Equipment in engine room"

```sql
SELECT
    e.id,
    e.name,
    e.code,
    e.location,
    e.status,
    e.criticality,
    e.attention_flag
FROM pms_equipment e
WHERE e.location ILIKE '%engine room%'
  AND e.yacht_id = public.get_user_yacht_id()
  AND e.deleted_at IS NULL
ORDER BY e.criticality DESC, e.name;
```

---

## Scenario 3: "Critical equipment needing attention"

```sql
SELECT
    e.id,
    e.name,
    e.code,
    e.status,
    e.attention_flag,
    e.attention_reason,
    e.attention_updated_at
FROM pms_equipment e
WHERE e.attention_flag = true
  AND e.criticality = 'critical'
  AND e.yacht_id = public.get_user_yacht_id()
  AND e.deleted_at IS NULL
ORDER BY e.attention_updated_at DESC;
```

---

## Scenario 4: "Parts for this equipment"

```sql
SELECT
    p.id AS part_id,
    p.part_number,
    p.name AS part_name,
    p.manufacturer AS part_manufacturer,
    bom.quantity_required,
    bom.notes,
    -- Current stock level
    (SELECT COALESCE(SUM(ii.quantity_on_hand), 0)
     FROM pms_inventory_items ii
     WHERE ii.part_id = p.id
     AND ii.yacht_id = public.get_user_yacht_id()) AS stock_on_hand
FROM pms_equipment_parts_bom bom
JOIN pms_parts p ON bom.part_id = p.id
WHERE bom.equipment_id = :equipment_id
  AND bom.yacht_id = public.get_user_yacht_id()
ORDER BY p.name;
```

---

## Scenario 5: "Equipment maintenance history"

```sql
SELECT
    wo.id,
    wo.wo_number,
    wo.title,
    wo.type,
    wo.status,
    wo.completed_at,
    wo.completion_notes,
    (SELECT name FROM auth_users_profiles WHERE id = wo.completed_by) AS completed_by_name
FROM pms_work_orders wo
WHERE wo.equipment_id = :equipment_id
  AND wo.yacht_id = public.get_user_yacht_id()
  AND wo.status = 'completed'
  AND wo.deleted_at IS NULL
ORDER BY wo.completed_at DESC
LIMIT 20;
```

---

# PART 7: GAPS & MIGRATION STATUS

## Confirmed Present

| Feature | Table | Column/Trigger | Status |
|---------|-------|----------------|--------|
| Soft delete | pms_equipment | deleted_at, deleted_by, deletion_reason | ✅ |
| Hierarchy | pms_equipment | parent_id | ✅ |
| Attention flag | pms_equipment | attention_flag, attention_reason, attention_updated_at | ✅ |
| Status tracking | pms_equipment | status (with CHECK constraint) | ✅ |
| Parts BOM | pms_equipment_parts_bom | equipment_id, part_id | ✅ |
| RLS canonical | pms_equipment | get_user_yacht_id() | ✅ |
| Hard delete prevention | pms_equipment | no_hard_delete_equipment trigger | ✅ |

## No Gaps Identified

Equipment Lens has complete schema coverage. No migrations required.

---

# PART 8: SUMMARY

## Equipment Lens Actions (Final)

| Action | Tables Written | Signature | RLS Tier |
|--------|---------------|-----------|----------|
| `update_equipment_status` | pms_equipment, pms_audit_log | No | Engineers |
| `add_equipment_note` | pms_notes, pms_audit_log | No | All Crew |
| `attach_file_to_equipment` | pms_attachments, pms_audit_log | No | All Crew |
| `create_work_order_for_equipment` | pms_work_orders, (pms_faults), pms_audit_log | No | Engineers |
| `view_equipment_faults` | None (read) | No | All Crew |
| `view_equipment_work_orders` | None (read) | No | All Crew |

## Escape Hatches

| From Equipment | To Lens | Trigger |
|----------------|---------|---------|
| view_equipment_faults | Fault Lens | Focus on fault from list |
| view_equipment_work_orders | Work Order Lens | Focus on WO from list |
| create_work_order_for_equipment | Work Order Lens | WO created → navigate to WO |

## Key Invariants

1. **Equipment always belongs to yacht** via `yacht_id = get_user_yacht_id()`
2. **Equipment is never hard deleted** - soft delete via `deleted_at`
3. **Status transitions are logged** via `pms_audit_log`
4. **Attention flag auto-sets** on failed/degraded status
5. **Hierarchy via parent_id** - supports unlimited nesting
6. **Parts tracked via BOM** - `pms_equipment_parts_bom` links equipment ↔ parts

---

**END OF EQUIPMENT LENS v1 FINAL**
