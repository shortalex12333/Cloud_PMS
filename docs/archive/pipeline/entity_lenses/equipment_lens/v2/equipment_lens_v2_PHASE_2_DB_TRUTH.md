# Equipment Lens v2 - PHASE 2: DB TRUTH

**Goal**: Document → Tests → Code → Verify — backend defines actions, signatures, and RLS; no UI authority.

**Lens**: Equipment

**Date**: 2026-01-27

---

## PURPOSE

Phase 2 captures the exact database schema as deployed in production. No assumptions - only verified truth.

---

## TABLE: `pms_equipment`

### Column Specification (24 columns)

| # | Column | PostgreSQL Type | Nullable | Default | Classification |
|---|--------|-----------------|----------|---------|----------------|
| 1 | `id` | uuid | NOT NULL | gen_random_uuid() | BACKEND_AUTO |
| 2 | `yacht_id` | uuid | NOT NULL | - | BACKEND_AUTO |
| 3 | `parent_id` | uuid | YES | NULL | OPTIONAL |
| 4 | `name` | text | NOT NULL | - | REQUIRED |
| 5 | `code` | text | YES | NULL | OPTIONAL |
| 6 | `description` | text | YES | NULL | OPTIONAL |
| 7 | `location` | text | YES | NULL | OPTIONAL |
| 8 | `manufacturer` | text | YES | NULL | OPTIONAL |
| 9 | `model` | text | YES | NULL | OPTIONAL |
| 10 | `serial_number` | text | YES | NULL | OPTIONAL |
| 11 | `installed_date` | date | YES | NULL | OPTIONAL |
| 12 | `criticality` | equipment_criticality | YES | 'medium' | OPTIONAL |
| 13 | `system_type` | text | YES | NULL | OPTIONAL |
| 14 | `status` | text | YES | 'operational' | BACKEND_AUTO |
| 15 | `attention_flag` | boolean | YES | false | BACKEND_AUTO |
| 16 | `attention_reason` | text | YES | NULL | CONTEXT |
| 17 | `attention_updated_at` | timestamptz | YES | NULL | BACKEND_AUTO |
| 18 | `metadata` | jsonb | YES | NULL | BACKEND_AUTO |
| 19 | `created_at` | timestamptz | NOT NULL | NOW() | BACKEND_AUTO |
| 20 | `updated_at` | timestamptz | NOT NULL | NOW() | BACKEND_AUTO |
| 21 | `updated_by` | uuid | YES | NULL | BACKEND_AUTO |
| 22 | `deleted_at` | timestamptz | YES | NULL | BACKEND_AUTO |
| 23 | `deleted_by` | uuid | YES | NULL | BACKEND_AUTO |
| 24 | `deletion_reason` | text | YES | NULL | OPTIONAL |

### Field Classification Legend

| Classification | Meaning | UI Behavior |
|----------------|---------|-------------|
| BACKEND_AUTO | Set by backend, never by user | Hidden from form |
| REQUIRED | Must be provided by user | Required input field |
| OPTIONAL | May be provided by user | Optional input field |
| CONTEXT | Derived from focused entity or session | Pre-filled, read-only |

---

## CONSTRAINTS

### Primary Key
```sql
CONSTRAINT equipment_pkey PRIMARY KEY (id)
```

### Foreign Keys
```sql
CONSTRAINT equipment_yacht_id_fkey
    FOREIGN KEY (yacht_id) REFERENCES yacht_registry(id);

CONSTRAINT equipment_parent_id_fkey
    FOREIGN KEY (parent_id) REFERENCES pms_equipment(id);
```

### CHECK Constraints

**Status Values**:
```sql
CONSTRAINT equipment_status_check CHECK (
    status = ANY (ARRAY[
        'operational'::text,
        'degraded'::text,
        'failed'::text,
        'maintenance'::text,
        'decommissioned'::text
    ])
)
```

**Status Semantics**:

| Status | Meaning | Entry Condition | Exit Condition |
|--------|---------|-----------------|----------------|
| `operational` | Fully functional | Default, or repair complete | Issue detected |
| `degraded` | Working with reduced capability | Partial failure | Full failure or repair |
| `failed` | Not operational | Complete failure | Repair started |
| `maintenance` | Under service | Work started | Work complete |
| `decommissioned` | Permanently removed | Manager/Captain signed action | TERMINAL - no exit |

---

## ENUM: `equipment_criticality`

```sql
CREATE TYPE equipment_criticality AS ENUM (
    'low',
    'medium',
    'high',
    'critical'
);
```

| Value | Meaning | Examples |
|-------|---------|----------|
| `low` | Failure has minimal impact | Interior lighting, decorative items |
| `medium` | Failure affects comfort | HVAC secondary, backup systems |
| `high` | Failure significantly impacts operations | Generator, watermaker, stabilizers |
| `critical` | Failure endangers safety/compliance | Main engines, steering, fire suppression |

---

## SYSTEM TYPE VALUES

The `system_type` column accepts these values:

```
main_engine, generator, hvac, electrical, hydraulic,
plumbing, fuel, freshwater, blackwater, graywater,
fire_suppression, steering, stabilizers, thrusters,
anchor_windlass, propulsion, navigation, communication,
radar, ecdis, autopilot, gyro, lifesaving, firefighting,
security, cctv, galley, laundry, housekeeping,
provisions, tender, toys, dive, mooring, deck_equipment,
av_entertainment, network, satellite, lighting_control,
crew_management, guest_services, finance, compliance,
charter, general, multi_system, vessel_wide
```

---

## INDEXES

| Index Name | Columns | Purpose |
|------------|---------|---------|
| `equipment_pkey` | id | Primary key lookup |
| `idx_equipment_yacht_id` | yacht_id | Yacht isolation |
| `idx_equipment_code` | code | Code lookup |
| `idx_equipment_parent_id` | parent_id | Hierarchy queries |
| `idx_equipment_system_type` | system_type | System filtering |
| `idx_equipment_criticality` | criticality | Priority filtering |
| `idx_equipment_location` | yacht_id, location | Location queries |
| `idx_equipment_manufacturer` | yacht_id, manufacturer | Manufacturer queries |
| `idx_equipment_attention_flag` | attention_flag WHERE true | Attention items (partial) |
| `idx_pms_equipment_status` | yacht_id, status | Status filtering |

---

## TRIGGERS

| Trigger | Event | Function | Purpose |
|---------|-------|----------|---------|
| `no_hard_delete_equipment` | BEFORE DELETE | prevent_hard_delete() | Enforces soft delete |
| `update_equipment_updated_at` | BEFORE UPDATE | update_updated_at() | Auto-update timestamp |

### Soft Delete Doctrine

Equipment uses soft delete via `deleted_at`. Hard deletes are blocked by trigger.

```sql
-- Trigger function
CREATE OR REPLACE FUNCTION prevent_hard_delete()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'Hard deletes are not allowed. Use soft delete (deleted_at).';
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;
```

---

## TABLE: `pms_equipment_parts_bom`

### Column Specification (7 columns)

| # | Column | PostgreSQL Type | Nullable | Default | Classification |
|---|--------|-----------------|----------|---------|----------------|
| 1 | `id` | uuid | NOT NULL | gen_random_uuid() | BACKEND_AUTO |
| 2 | `yacht_id` | uuid | NOT NULL | - | BACKEND_AUTO |
| 3 | `equipment_id` | uuid | NOT NULL | - | CONTEXT |
| 4 | `part_id` | uuid | NOT NULL | - | CONTEXT |
| 5 | `quantity_required` | integer | YES | 1 | OPTIONAL |
| 6 | `notes` | text | YES | NULL | OPTIONAL |
| 7 | `created_at` | timestamptz | NOT NULL | NOW() | BACKEND_AUTO |

### Foreign Keys

```sql
CONSTRAINT bom_equipment_fkey FOREIGN KEY (equipment_id) REFERENCES pms_equipment(id);
CONSTRAINT bom_part_fkey FOREIGN KEY (part_id) REFERENCES pms_parts(id);
CONSTRAINT bom_yacht_fkey FOREIGN KEY (yacht_id) REFERENCES yacht_registry(id);
```

### Unique Constraint

```sql
-- One part can only appear once per equipment
CONSTRAINT bom_unique_equipment_part UNIQUE (equipment_id, part_id);
```

---

## RELATED TABLES (for context)

### `pms_notes` - Equipment Notes

| Column | Type | Notes |
|--------|------|-------|
| id | uuid | PK |
| yacht_id | uuid | RLS |
| equipment_id | uuid | FK → pms_equipment |
| text | text | Note content |
| note_type | text | observation, handover, inspection, etc. |
| requires_ack | boolean | Triggers notification if true |
| attachments | jsonb | Inline attachment refs |
| created_by | uuid | Author |
| created_at | timestamptz | Timestamp |

### `pms_attachments` - Equipment Files

| Column | Type | Notes |
|--------|------|-------|
| id | uuid | PK |
| yacht_id | uuid | RLS |
| entity_type | text | 'equipment' |
| entity_id | uuid | FK → pms_equipment |
| filename | text | UUID-based filename |
| original_filename | text | User's filename |
| mime_type | text | Detected MIME |
| file_size | bigint | Bytes |
| storage_path | text | Full bucket path |
| description | text | User description |
| tags | text[] | User tags |
| uploaded_by | uuid | Uploader |
| uploaded_at | timestamptz | Timestamp |

### `pms_audit_log` - Equipment Audit Trail

| Column | Type | Notes |
|--------|------|-------|
| id | uuid | PK |
| yacht_id | uuid | RLS |
| entity_type | text | 'equipment' |
| entity_id | uuid | FK → pms_equipment |
| action | text | Action performed |
| actor_user_id | uuid | Who did it (MASTER user) |
| actor_role | text | Role at time of action |
| old_values | jsonb | Previous state |
| new_values | jsonb | New state |
| signature | jsonb | NOT NULL - {} or full signature |
| payload_snapshot | jsonb | Action-specific context |
| created_at | timestamptz | When |

---

## VERIFICATION QUERIES

Run these against production to verify schema:

### 1. Column Verification
```sql
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_name = 'pms_equipment'
ORDER BY ordinal_position;
```

### 2. Index Verification
```sql
SELECT indexname, indexdef
FROM pg_indexes
WHERE tablename = 'pms_equipment';
```

### 3. Constraint Verification
```sql
SELECT conname, contype, pg_get_constraintdef(oid)
FROM pg_constraint
WHERE conrelid = 'pms_equipment'::regclass;
```

### 4. Trigger Verification
```sql
SELECT tgname, tgtype, proname
FROM pg_trigger t
JOIN pg_proc p ON t.tgfoid = p.oid
WHERE tgrelid = 'pms_equipment'::regclass;
```

### 5. RLS Status
```sql
SELECT relname, relrowsecurity
FROM pg_class
WHERE relname = 'pms_equipment';
-- Should return relrowsecurity = true
```

### 6. Row Count
```sql
SELECT COUNT(*) as total,
       COUNT(*) FILTER (WHERE deleted_at IS NULL) as active,
       COUNT(*) FILTER (WHERE deleted_at IS NOT NULL) as soft_deleted
FROM pms_equipment;
```

---

## SCHEMA GAPS IDENTIFIED

| Gap | Severity | Notes |
|-----|----------|-------|
| None identified | - | Schema appears complete |

---

## NEXT PHASE

Proceed to **PHASE 3: ENTITY GRAPH** to:
- Map all entity relationships
- Define escape hatches
- Document cross-lens interactions

---

**END OF PHASE 2**
