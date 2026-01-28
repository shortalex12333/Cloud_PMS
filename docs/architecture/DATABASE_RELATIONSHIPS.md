# PMS Database Relationships Framework

**Purpose:** Ground truth of database schema - tables, columns, foreign keys, constraints
**Date Created:** 2026-01-22
**Source:** Live database inspection + handler code analysis
**Status:** Living document - update as schema evolves

---

## Why This Document Exists

**Problem:** The COMPLETE_ACTION_EXECUTION_CATALOG.md (6584 lines) contains outdated information:
- Table names don't match (`work_orders` vs `pms_work_orders`)
- Required fields differ from reality
- Validation rules are aspirational, not actual

**Solution:** This document reflects ACTUAL database schema, not documentation wishes.

**Use This To:**
- Understand what tables exist and their relationships
- Know the real column names (avoid `current_quantity` vs `quantity_on_hand` traps)
- Identify foreign key relationships for testing
- Verify RLS policies and soft delete patterns
- Design mutation proof tests

---

## Core Entities Overview

```
pms_work_orders  ←─────┐
       ↓                │
pms_faults  ────────────┘
       ↓
pms_equipment
       ↓
pms_parts

pms_audit_log (cross-cuts all entities)
```

---

## Table: `pms_work_orders`

**Purpose:** Track maintenance work orders (corrective, preventive, inspection, modification)

### Schema

| Column | Type | Nullable | Foreign Key | Notes |
|--------|------|----------|-------------|-------|
| `id` | uuid | ❌ | - | Primary key |
| `yacht_id` | uuid | ❌ | → (master DB) | RLS enforced |
| `equipment_id` | uuid | ✅ | → pms_equipment.id | Can be null for general WOs |
| `fault_id` | uuid | ✅ | → pms_faults.id | Links to originating fault |
| `title` | text | ❌ | - | Min 1 char (not validated) |
| `description` | text | ❌ | - | Can be empty string |
| `work_order_type` | text | ❌ | - | Enum: corrective, preventive, inspection, modification |
| `priority` | text | ❌ | - | Enum: routine, emergency, critical |
| `status` | text | ❌ | - | Enum: planned, open, in_progress, completed, cancelled |
| `wo_number` | text | ❌ | - | Auto-generated sequential |
| `assigned_to` | uuid | ✅ | → (master DB users) | Can be null |
| `created_by` | uuid | ❌ | → (master DB users) | Always set |
| `updated_by` | uuid | ❌ | → (master DB users) | Updated on changes |
| `completed_by` | uuid | ✅ | → (master DB users) | Set when status → completed |
| `completed_at` | timestamp | ✅ | - | Set when status → completed |
| `completion_notes` | text | ✅ | - | Added when marking complete |
| `due_date` | date | ✅ | - | For planned work |
| `due_hours` | numeric | ✅ | - | For running-hours-based schedules |
| `last_completed_date` | date | ✅ | - | Historical tracking |
| `last_completed_hours` | numeric | ✅ | - | Historical tracking |
| `frequency` | text | ✅ | - | Recurring schedule info |
| `metadata` | jsonb | ✅ | - | Extensible data |
| `created_at` | timestamp | ❌ | - | Auto-set |
| `updated_at` | timestamp | ❌ | - | Auto-updated |
| `deleted_at` | timestamp | ✅ | - | Soft delete (RLS blocks hard deletes) |
| `deleted_by` | uuid | ✅ | → (master DB users) | Who soft-deleted |
| `deletion_reason` | text | ✅ | - | Why soft-deleted |
| `vendor_contact_hash` | text | ✅ | - | For external vendor WOs |
| `type` | text | ✅ | - | Legacy field (use work_order_type) |

### Constraints

**Primary Key:** `id`
**Unique:** None
**Check Constraints:**
- None enforced at DB level (validation in handlers)

### RLS Policies

✅ **Enabled** - All queries MUST include `yacht_id` filter
✅ **Soft Delete** - Hard deletes blocked, must use `deleted_at`

### Indexes

- `yacht_id` (for RLS performance)
- `equipment_id` (for equipment → work orders queries)
- `fault_id` (for fault → work order linking)
- `status` (for filtering)
- `assigned_to` (for user work queues)

---

## Table: `pms_faults`

**Purpose:** Record equipment faults/failures reported by crew

### Schema

| Column | Type | Nullable | Foreign Key | Notes |
|--------|------|----------|-------------|-------|
| `id` | uuid | ❌ | - | Primary key |
| `yacht_id` | uuid | ❌ | → (master DB) | RLS enforced |
| `equipment_id` | uuid | ❌ | → pms_equipment.id | Always linked to equipment |
| `work_order_id` | uuid | ✅ | → pms_work_orders.id | Created by create_work_order_from_fault |
| `fault_code` | text | ✅ | - | Auto-generated (e.g., F-00123) |
| `title` | text | ❌ | - | Brief description |
| `description` | text | ❌ | - | Detailed fault description |
| `severity` | text | ❌ | - | Enum: low, medium, high, critical |
| `status` | text | ❌ | - | Enum: reported, acknowledged, diagnosed, resolved |
| `detected_at` | timestamp | ❌ | - | When fault was first observed |
| `resolved_at` | timestamp | ✅ | - | When fault was fixed |
| `resolved_by` | uuid | ✅ | → (master DB users) | Who resolved it |
| `metadata` | jsonb | ✅ | - | Photos, sensor data, etc. |
| `created_at` | timestamp | ❌ | - | Auto-set |
| `updated_at` | timestamp | ❌ | - | Auto-updated |
| `updated_by` | uuid | ✅ | → (master DB users) | Who last updated |
| `deleted_at` | timestamp | ✅ | - | Soft delete |
| `deleted_by` | uuid | ✅ | → (master DB users) | Who soft-deleted |
| `deletion_reason` | text | ✅ | - | Why soft-deleted |

### Relationships

**Fault → Work Order:**
- One fault can generate one work order via `create_work_order_from_fault`
- `pms_faults.work_order_id` → `pms_work_orders.id`
- Backlink: `pms_work_orders.fault_id` → `pms_faults.id`

---

## Table: `pms_equipment`

**Purpose:** Asset registry - engines, pumps, HVAC, electrical, etc.

### Schema

| Column | Type | Nullable | Foreign Key | Notes |
|--------|------|----------|-------------|-------|
| `id` | uuid | ❌ | - | Primary key |
| `yacht_id` | uuid | ❌ | → (master DB) | RLS enforced |
| `parent_id` | uuid | ✅ | → pms_equipment.id | Self-referential (hierarchical) |
| `name` | text | ❌ | - | Equipment name |
| `code` | text | ❌ | - | Equipment code (e.g., ME-01) |
| `description` | text | ✅ | - | Detailed description |
| `location` | text | ✅ | - | Physical location onboard |
| `manufacturer` | text | ✅ | - | OEM name |
| `model` | text | ✅ | - | Model number |
| `serial_number` | text | ✅ | - | Serial number |
| `installed_date` | date | ✅ | - | Installation date |
| `criticality` | text | ❌ | - | Enum: low, medium, high, critical |
| `status` | text | ❌ | - | Enum: operational, faulty, maintenance, decommissioned |
| `system_type` | text | ✅ | - | HVAC, electrical, propulsion, etc. |
| `attention_flag` | boolean | ❌ | - | Red flag for operator attention |
| `attention_reason` | text | ✅ | - | Why flagged |
| `attention_updated_at` | timestamp | ✅ | - | When flag last updated |
| `metadata` | jsonb | ✅ | - | Specs, manuals, photos |
| `created_at` | timestamp | ❌ | - | Auto-set |
| `updated_at` | timestamp | ❌ | - | Auto-updated |
| `updated_by` | uuid | ✅ | → (master DB users) | Who last updated |
| `deleted_at` | timestamp | ✅ | - | Soft delete |
| `deleted_by` | uuid | ✅ | → (master DB users) | Who soft-deleted |
| `deletion_reason` | text | ✅ | - | Why soft-deleted |

### Hierarchical Relationships

**Parent-Child Equipment:**
- `parent_id` enables tree structure
- Example: Engine (parent) → Fuel pump (child) → Fuel filter (child)

---

## Table: `pms_parts`

**Purpose:** Parts catalog + inventory tracking

### Schema

| Column | Type | Nullable | Foreign Key | Notes |
|--------|------|----------|-------------|-------|
| `id` | uuid | ❌ | - | Primary key |
| `yacht_id` | uuid | ❌ | → (master DB) | RLS enforced |
| `name` | text | ❌ | - | Part name |
| `part_number` | text | ❌ | - | Manufacturer part number |
| `manufacturer` | text | ✅ | - | OEM name |
| `description` | text | ✅ | - | Detailed description |
| `category` | text | ✅ | - | filters, oils, gaskets, etc. |
| `model_compatibility` | text[] | ✅ | - | Array of compatible models |
| `quantity_on_hand` | numeric | ❌ | - | Current stock level |
| `minimum_quantity` | numeric | ✅ | - | Reorder threshold |
| `unit` | text | ✅ | - | ea, liter, kg, etc. |
| `location` | text | ✅ | - | Storage location onboard |
| `last_counted_at` | timestamp | ✅ | - | Last inventory count |
| `last_counted_by` | uuid | ✅ | → (master DB users) | Who counted |
| `metadata` | jsonb | ✅ | - | Photos, specs, supplier info |
| `search_embedding` | vector | ✅ | - | pgvector for semantic search |
| `embedding_text` | text | ✅ | - | Text used to generate embedding |
| `created_at` | timestamp | ❌ | - | Auto-set |
| `updated_at` | timestamp | ❌ | - | Auto-updated |

### Special Features

**Semantic Search:**
- `search_embedding` column uses pgvector extension
- Enables "find oil filter for Caterpillar 3516" queries

**Inventory Tracking:**
- `quantity_on_hand` updated by inventory movements
- No separate inventory_movements table (design choice)

---

## Table: `pms_audit_log`

**Purpose:** Audit trail for ALL mutation actions (compliance: ISO 9001, SOLAS)

### Schema

| Column | Type | Nullable | Foreign Key | Notes |
|--------|------|----------|-------------|-------|
| `id` | uuid | ❌ | - | Primary key |
| `yacht_id` | uuid | ❌ | → (master DB) | RLS enforced |
| `action` | text | ❌ | - | Action name (e.g., create_work_order) |
| `entity_type` | text | ❌ | - | work_order, fault, equipment, part, etc. |
| `entity_id` | uuid | ❌ | - | ID of affected entity |
| `user_id` | uuid | ❌ | → (master DB users) | Who performed action |
| `signature` | jsonb | ❌ | - | {user_id, timestamp, action, execution_id} |
| `old_values` | jsonb | ✅ | - | State before (null for create) |
| `new_values` | jsonb | ❌ | - | State after |
| `metadata` | jsonb | ✅ | - | Additional context |
| `created_at` | timestamp | ❌ | - | Auto-set (immutable) |

### Critical Notes

⚠️ **This is the ONLY audit table**
✅ **Immutable** - No updates or deletes allowed
✅ **RLS Enforced** - Per-yacht isolation

### Current Coverage

**Actions WITH audit logs:** (26 actions)
- mark_work_order_complete (19 entries)
- acknowledge_fault (8 entries)
- add_work_order_note (6 entries)
- assign_work_order (6 entries)
- add_equipment_note (6 entries)
- ... 21 more actions

**Actions WITHOUT audit logs:** (38+ actions)
- ❌ create_work_order ← **CRITICAL GAP**
- ❌ create_fault
- ❌ update_equipment
- ... 35+ more actions

**Impact:** Compliance risk, can't trace who created work orders/faults

---

## Table: `pms_work_order_notes`

**Purpose:** Thread of notes/comments on work orders

### Schema

| Column | Type | Nullable | Foreign Key | Notes |
|--------|------|----------|-------------|-------|
| `id` | uuid | ❌ | - | Primary key |
| `work_order_id` | uuid | ❌ | → pms_work_orders.id | Parent work order |
| `note_text` | text | ❌ | - | Note content |
| `note_type` | text | ❌ | - | comment, update, completion, escalation |
| `created_by` | uuid | ❌ | → (master DB users) | Author |
| `created_at` | timestamp | ❌ | - | Auto-set |
| `metadata` | jsonb | ✅ | - | Photos, attachments |

### Relationships

**One-to-Many:**
- One work order → many notes
- Query: `SELECT * FROM pms_work_order_notes WHERE work_order_id = ?`

---

## Table: `pms_checklists`

**Purpose:** Safety checklists, inspection checklists, handover checklists

### Schema

| Column | Type | Nullable | Foreign Key | Notes |
|--------|------|----------|-------------|-------|
| `id` | uuid | ❌ | - | Primary key |
| `yacht_id` | uuid | ❌ | → (master DB) | RLS enforced |
| `name` | text | ❌ | - | Checklist name |
| `description` | text | ✅ | - | Detailed description |
| `checklist_type` | text | ❌ | - | safety, inspection, handover, etc. |
| `equipment_id` | uuid | ✅ | → pms_equipment.id | Optional equipment link |
| `work_order_id` | uuid | ✅ | → pms_work_orders.id | Optional WO link |
| `status` | text | ❌ | - | not_started, in_progress, completed |
| `is_template` | boolean | ❌ | - | Is this a template or instance? |
| `total_items` | numeric | ❌ | - | Total checklist items |
| `completed_items` | numeric | ❌ | - | Completed count |
| `metadata` | jsonb | ✅ | - | Custom fields |
| `created_at` | timestamp | ❌ | - | Auto-set |
| `created_by` | uuid | ❌ | → (master DB users) | Who created |
| `updated_at` | timestamp | ❌ | - | Auto-updated |
| `updated_by` | uuid | ✅ | → (master DB users) | Who last updated |

---

## Tables NOT Found in Live Database

The following tables exist in CATALOG but NOT in database:

❌ `pms_inventory_movements` (catalog says exists)
❌ `pms_fault_notes` (catalog says exists)
❌ `pms_equipment_notes` (catalog says exists)
❌ `pms_documents` (catalog says exists)
❌ `pms_maintenance_schedules` (exists but EMPTY)

**Implication:** Actions referencing these tables will fail or are not implemented.

---

## Foreign Key Patterns

### Standard Foreign Keys

**All tables have:**
- `yacht_id` → Master DB tenant (enforced by RLS)
- `created_by` → Master DB users
- `updated_by` → Master DB users

**Entity-specific:**
- `equipment_id` → pms_equipment.id
- `work_order_id` → pms_work_orders.id
- `fault_id` → pms_faults.id
- `part_id` → pms_parts.id

### Naming Convention

**Pattern:** `{entity}_id` references `pms_{entity}s.id`

**Examples:**
- `equipment_id` → `pms_equipment.id`
- `fault_id` → `pms_faults.id`
- `work_order_id` → `pms_work_orders.id`

**Exception:** `yacht_id` references master DB, not tenant DB

---

## RLS (Row Level Security) Policies

### Global Pattern

**ALL tenant tables enforce:**
```sql
CREATE POLICY "yacht_isolation" ON pms_work_orders
FOR ALL
USING (yacht_id = current_setting('app.current_yacht_id')::uuid);
```

**Implication:**
- Every query MUST include `yacht_id` in WHERE clause
- Cross-tenant access impossible
- Performance: `yacht_id` indexed on all tables

### Soft Delete Pattern

**Hard deletes are BLOCKED by policy:**
```sql
CREATE POLICY "prevent_hard_deletes" ON pms_work_orders
FOR DELETE
USING (false);  -- Always deny
```

**Must use soft delete:**
```sql
UPDATE pms_work_orders
SET deleted_at = NOW(),
    deleted_by = auth.uid(),
    deletion_reason = 'User requested deletion'
WHERE id = ?;
```

---

## Data Type Patterns

### UUIDs
- All `id` columns: uuid v4
- All `_id` foreign keys: uuid
- Generated by `gen_random_uuid()` or application

### Timestamps
- All `created_at`: `timestamptz` (with timezone)
- All `updated_at`: `timestamptz`
- Format: ISO 8601 (e.g., `2026-01-22T14:05:36.244721+00:00`)

### Enums (Stored as TEXT)

**No PostgreSQL ENUMs used** - all enums are TEXT with validation in handlers

**Example:**
```python
# Handler validates, DB stores as text
if status not in ['planned', 'open', 'in_progress', 'completed', 'cancelled']:
    raise ValueError("Invalid status")
```

### JSONB Columns

**All `metadata` columns:** `jsonb`
- Extensible data storage
- Queryable with `->` and `->>` operators
- Indexed with GIN indexes for performance

---

## Common Query Patterns

### Get Work Orders for Equipment

```sql
SELECT * FROM pms_work_orders
WHERE yacht_id = ?
  AND equipment_id = ?
  AND deleted_at IS NULL
ORDER BY created_at DESC;
```

### Get Faults with Work Orders

```sql
SELECT f.*, wo.title as work_order_title, wo.status as wo_status
FROM pms_faults f
LEFT JOIN pms_work_orders wo ON f.work_order_id = wo.id
WHERE f.yacht_id = ?
  AND f.deleted_at IS NULL
ORDER BY f.detected_at DESC;
```

### Get Equipment Hierarchy

```sql
WITH RECURSIVE equipment_tree AS (
  SELECT * FROM pms_equipment WHERE parent_id IS NULL AND yacht_id = ?
  UNION ALL
  SELECT e.* FROM pms_equipment e
  INNER JOIN equipment_tree et ON e.parent_id = et.id
)
SELECT * FROM equipment_tree;
```

---

## Column Name Traps

**CRITICAL:** Handler code uses different names than you might expect

| Expected Name | Actual Column Name | Table |
|---------------|-------------------|-------|
| `current_quantity` | `quantity_on_hand` | pms_parts |
| `assigned_to` | `assigned_to` | pms_work_orders |
| `assignee_id` | `assigned_to` | pms_work_orders |
| `vessel_id` | `yacht_id` | ALL TABLES |
| `photo` | `photo_url` or `metadata.photos` | VARIES |
| `status` | `status` | ALL (but enum values differ) |

**Always check schema before writing queries!**

---

## Testing Implications

### Mutation Proof Tests Must:

1. **Query BEFORE action**
   ```sql
   SELECT COUNT(*) FROM pms_work_orders WHERE id = ?
   -- Result: 0
   ```

2. **Execute action via API**
   ```bash
   curl -X POST /v1/actions/execute -d {...}
   # Response: 200, work_order_id: abc-123
   ```

3. **Query AFTER action**
   ```sql
   SELECT * FROM pms_work_orders WHERE id = 'abc-123'
   -- Result: 1 row with correct data
   ```

4. **Query audit log**
   ```sql
   SELECT * FROM pms_audit_log WHERE entity_id = 'abc-123'
   -- Result: 1 row (or 0 if audit gap exists)
   ```

### Foreign Key Validation

**Test that invalid FKs are rejected:**
```sql
-- Should fail with 404
POST /v1/actions/execute
{
  "action": "create_work_order",
  "context": {"yacht_id": "..."},
  "payload": {
    "equipment_id": "non-existent-uuid",  // ← Should fail
    "title": "Test"
  }
}
```

---

## Schema Evolution Notes

**Last Updated:** 2026-01-22

**Recent Changes:**
- `pms_work_orders.vendor_contact_hash` added (recent)
- `pms_equipment.attention_flag` pattern added
- `pms_parts.search_embedding` for semantic search

**Pending Changes:**
- Consider adding `pms_inventory_movements` table
- Add `pms_documents` table for manual/spec storage
- Populate `pms_maintenance_schedules`

---

## Quick Reference Card

**Most Common Tables:**
```
pms_work_orders       → 29 columns
pms_faults            → 19 columns
pms_equipment         → 24 columns
pms_parts             → 19 columns
pms_audit_log         → 11 columns
pms_work_order_notes  → 7 columns
pms_checklists        → 16 columns
```

**All Tables Have:**
- `id` (uuid, PK)
- `yacht_id` (uuid, FK, RLS)
- `created_at` (timestamptz)
- `updated_at` (timestamptz) [most tables]
- `deleted_at` (timestamptz, nullable) [soft delete]
- `metadata` (jsonb, nullable) [most tables]

**Foreign Key Convention:**
- `{entity}_id` → `pms_{entity}s.id`

**RLS Enforced:**
- ✅ All queries filtered by `yacht_id`
- ✅ Hard deletes blocked
- ✅ Soft delete required

---

**Document Version:** 1.0
**Reflects Database As Of:** 2026-01-22
**Next Review:** When schema migrations run
