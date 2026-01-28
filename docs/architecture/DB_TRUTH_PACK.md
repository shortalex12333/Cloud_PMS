# DB_TRUTH_PACK.md

**Date:** 2026-01-22
**Status:** Layer 2 - Database Schema Reference (Repo-Truth Only)

---

## PURPOSE

This document is the authoritative database schema reference for CelesteOS. It contains ONLY tables and columns that exist in the repository migrations or live schema. No aspirational tables, no guesses.

**Rule:** If it's not in this document, it doesn't exist in the database yet.

---

## MIGRATION PHILOSOPHY

From `00000000000004_02_p0_actions_tables_REVISED.sql`:

**Decision Matrix:**
- **Prefer adding columns** to existing tables over creating new tables
- **Justify new tables** with specific reasoning (query performance, data integrity, separation of concerns)
- **Leverage existing** auth and PMS core tables where possible

**Examples:**
- `work_order_notes`: NEW TABLE (justified - better than JSONB array for queries)
- `audit_log`: NEW TABLE (justified - non-negotiable for accountability)
- `part_usage`: NEW TABLE (justified - event log for inventory audit trail)

---

## CORE AUTHENTICATION TABLES

### yachts

**Purpose:** Master yacht/vessel records for multi-tenant isolation

**Key Columns:**
- `id` UUID PRIMARY KEY
- `name` TEXT NOT NULL
- `signature` TEXT UNIQUE NOT NULL (unique yacht install key)
- `status` TEXT DEFAULT 'active' CHECK (status IN ('active', 'inactive', 'demo'))
- Standard timestamps (created_at, updated_at)

**Foreign Keys:** None (root table)

**Soft Delete:** No

**RLS:** Enabled - yacht isolation via yacht_id in JWT claims

---

### user_profiles

**Purpose:** User profile information linked to auth.users

**Key Columns:**
- `id` UUID PRIMARY KEY REFERENCES auth.users(id)
- `yacht_id` UUID NOT NULL REFERENCES yachts(id)
- `email` TEXT UNIQUE NOT NULL
- `name` TEXT NOT NULL
- `is_active` BOOLEAN DEFAULT true
- Standard timestamps

**Foreign Keys:**
- `id` → auth.users(id)
- `yacht_id` → yachts(id)

**Soft Delete:** No (uses is_active flag)

**RLS:** Enabled - users can view own profile, HODs can manage

---

### user_roles

**Purpose:** User role assignments (separate from user_profiles for security)

**Key Columns:**
- `id` UUID PRIMARY KEY
- `user_id` UUID NOT NULL REFERENCES auth.users(id)
- `yacht_id` UUID NOT NULL REFERENCES yachts(id)
- `role` TEXT CHECK (role IN ('chief_engineer', 'eto', 'captain', 'manager', 'vendor', 'crew', 'deck', 'interior'))
- `is_active` BOOLEAN DEFAULT true
- Standard timestamps

**Foreign Keys:**
- `user_id` → auth.users(id)
- `yacht_id` → yachts(id)

**Soft Delete:** No (uses is_active flag)

**RLS:** Enabled - only HODs can assign roles

**Helper Functions:**
- `get_user_role(p_user_id UUID, p_yacht_id UUID) RETURNS TEXT`
- `is_hod(p_user_id UUID, p_yacht_id UUID) RETURNS BOOLEAN`

---

## PMS OPERATIONAL TABLES

### pms_equipment

**Purpose:** Equipment/machinery inventory and lifecycle tracking

**Key Columns:**
- `id` UUID PRIMARY KEY
- `yacht_id` UUID NOT NULL REFERENCES yachts(id)
- `name` TEXT NOT NULL
- `category` TEXT
- `location` TEXT
- `manufacturer` TEXT
- `model` TEXT
- `serial_number` TEXT
- `status` TEXT DEFAULT 'operational' CHECK (status IN ('operational', 'degraded', 'failed', 'maintenance', 'decommissioned'))
- `is_critical` BOOLEAN DEFAULT false
- `metadata` JSONB DEFAULT '{}'
- Standard timestamps (created_at, updated_at, created_by, updated_by)

**Foreign Keys:**
- `yacht_id` → yachts(id)

**Soft Delete:** Yes (deleted_at, deleted_by, deletion_reason)

**RLS:** Enabled - yacht isolation via yacht_id

---

### pms_work_orders

**Purpose:** Work order tracking for maintenance, repairs, and projects

**Key Columns:**
- `id` UUID PRIMARY KEY
- `yacht_id` UUID NOT NULL REFERENCES yachts(id)
- `wo_number` TEXT (auto-generated)
- `title` TEXT NOT NULL
- `wo_type` TEXT CHECK (wo_type IN ('corrective', 'preventive', 'predictive', 'emergency', 'project'))
- `priority` TEXT CHECK (priority IN ('low', 'medium', 'high', 'critical'))
- `status` TEXT CHECK (status IN ('draft', 'open', 'in_progress', 'on_hold', 'completed', 'cancelled'))
- `equipment_id` UUID REFERENCES pms_equipment(id)
- `fault_id` UUID (may reference pms_faults)
- `assigned_to` UUID
- `completed_by` UUID
- Standard timestamps (created_at, updated_at, created_by, updated_by)

**Foreign Keys:**
- `yacht_id` → yachts(id)
- `equipment_id` → pms_equipment(id)

**Soft Delete:** Yes (deleted_at, deleted_by, deletion_reason)

**RLS:** Enabled - yacht isolation via yacht_id

---

### pms_parts

**Purpose:** Parts inventory management with min/max thresholds

**Key Columns:**
- `id` UUID PRIMARY KEY
- `yacht_id` UUID NOT NULL REFERENCES yachts(id)
- `name` TEXT NOT NULL
- `part_number` TEXT
- `quantity_on_hand` INTEGER DEFAULT 0
- `quantity_minimum` INTEGER DEFAULT 0
- `unit_cost` NUMERIC(12,2)
- `storage_location` TEXT
- `last_counted_at` TIMESTAMPTZ (added conditionally in P0 migration)
- Standard timestamps (created_at, updated_at, created_by, updated_by)

**Foreign Keys:**
- `yacht_id` → yachts(id)

**Soft Delete:** Yes (deleted_at, deleted_by, deletion_reason)

**RLS:** Enabled - yacht isolation via yacht_id

---

### pms_faults

**Purpose:** Fault/defect reporting and tracking

**Key Columns:**
- `id` UUID PRIMARY KEY
- `yacht_id` UUID NOT NULL REFERENCES yachts(id)
- `fault_number` TEXT (auto-generated)
- `title` TEXT NOT NULL
- `severity` TEXT CHECK (severity IN ('cosmetic', 'minor', 'major', 'critical', 'safety'))
- `status` TEXT CHECK (status IN ('open', 'investigating', 'work_ordered', 'resolved', 'closed', 'deferred'))
- `equipment_id` UUID REFERENCES pms_equipment(id)
- `work_order_id` UUID REFERENCES pms_work_orders(id)
- `detected_at` TIMESTAMPTZ
- `resolved_at` TIMESTAMPTZ
- Standard timestamps (created_at, updated_at, created_by, updated_by)

**Foreign Keys:**
- `yacht_id` → yachts(id)
- `equipment_id` → pms_equipment(id)
- `work_order_id` → pms_work_orders(id)

**Soft Delete:** Yes (deleted_at, deleted_by, deletion_reason)

**RLS:** Enabled - yacht isolation via yacht_id

---

### pms_purchase_orders

**Purpose:** Purchase order management for parts procurement

**Key Columns:**
- `id` UUID PRIMARY KEY
- `yacht_id` UUID NOT NULL REFERENCES yachts(id)
- `po_number` TEXT (auto-generated)
- `status` TEXT CHECK (status IN ('draft', 'pending', 'approved', 'ordered', 'partial', 'received', 'cancelled'))
- `supplier_name` TEXT
- `total` NUMERIC(12,2)
- Standard timestamps (created_at, updated_at, created_by, updated_by)

**Foreign Keys:**
- `yacht_id` → yachts(id)

**Soft Delete:** Yes (deleted_at, deleted_by, deletion_reason)

**RLS:** Enabled - yacht isolation via yacht_id

---

## SUPPORT & JUNCTION TABLES

### work_order_notes

**Purpose:** Notes attached to work orders (justified: better than JSONB for queries)

**Key Columns:**
- `id` UUID PRIMARY KEY
- `work_order_id` UUID NOT NULL REFERENCES work_orders(id) ON DELETE CASCADE
- `note_text` TEXT NOT NULL
- `note_type` TEXT CHECK (note_type IN ('general', 'progress', 'issue', 'resolution'))
- `created_by` UUID NOT NULL REFERENCES auth.users(id)
- `created_at` TIMESTAMPTZ DEFAULT NOW()

**Foreign Keys:**
- `work_order_id` → work_orders(id) ON DELETE CASCADE
- `created_by` → auth.users(id)

**Soft Delete:** No

**RLS:** Enabled - yacht isolation via work_order

---

### work_order_parts

**Purpose:** M:M junction between work orders and parts (parts used in work orders)

**Key Columns:**
- `id` UUID PRIMARY KEY
- `work_order_id` UUID REFERENCES work_orders(id)
- `part_id` UUID REFERENCES parts(id)
- `quantity_required` INTEGER
- `quantity_used` INTEGER
- `created_by` UUID
- Standard timestamps

**Foreign Keys:**
- `work_order_id` → work_orders(id)
- `part_id` → parts(id)

**Soft Delete:** No

**RLS:** Enabled - yacht isolation via work_order/part

---

### part_usage

**Purpose:** Event log for inventory audit trail (justified: immutable transaction log)

**Key Columns:**
- `id` UUID PRIMARY KEY
- `yacht_id` UUID REFERENCES yachts(id)
- `part_id` UUID REFERENCES parts(id)
- `work_order_id` UUID REFERENCES work_orders(id)
- `quantity` INTEGER (negative = usage, positive = restock)
- `transaction_type` TEXT CHECK (transaction_type IN ('usage', 'restock', 'adjustment', 'receiving'))
- `notes` TEXT
- `created_by` UUID
- `created_at` TIMESTAMPTZ DEFAULT NOW()

**Foreign Keys:**
- `yacht_id` → yachts(id)
- `part_id` → parts(id)
- `work_order_id` → work_orders(id)

**Soft Delete:** No (immutable log)

**RLS:** Enabled - yacht isolation via yacht_id

---

### pms_attachments

**Purpose:** File attachments (photos, documents) linked to various entities

**Key Columns:**
- `id` UUID PRIMARY KEY
- `yacht_id` UUID NOT NULL
- `entity_type` VARCHAR(50) NOT NULL CHECK (entity_type IN ('fault', 'work_order', 'equipment', 'checklist_item', 'note', 'handover', 'purchase_order'))
- `entity_id` UUID NOT NULL (polymorphic reference)
- `filename` VARCHAR(255) NOT NULL
- `original_filename` VARCHAR(255)
- `mime_type` VARCHAR(100) NOT NULL
- `file_size` INTEGER (bytes)
- `storage_path` TEXT NOT NULL (Supabase storage path)
- `width` INTEGER (image-specific)
- `height` INTEGER (image-specific)
- `thumbnail_path` TEXT
- `description` TEXT
- `tags` TEXT[]
- `metadata` JSONB DEFAULT '{}'
- `uploaded_by` UUID NOT NULL
- `uploaded_at` TIMESTAMPTZ NOT NULL DEFAULT NOW()
- Standard timestamps (created_at, updated_at)

**Foreign Keys:**
- Polymorphic - entity_id references various tables based on entity_type

**Soft Delete:** Yes (deleted_at, deleted_by, deletion_reason)

**RLS:** Enabled - yacht isolation via yacht_id

**Indexes:**
- `idx_pms_attachments_entity` ON (entity_type, entity_id)
- `idx_pms_attachments_uploaded_by` ON (uploaded_by)

---

## HANDOVER TABLES

### handovers

**Purpose:** Master handover records for shift/watch handovers between crew

**Key Columns:**
- `id` UUID PRIMARY KEY
- `yacht_id` UUID NOT NULL
- `title` VARCHAR(255)
- `description` TEXT
- `status` VARCHAR(20) NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'pending_review', 'approved', 'completed', 'cancelled'))
- `from_user_id` UUID (shift handoff sender)
- `to_user_id` UUID (shift handoff receiver)
- `shift_date` DATE
- `shift_type` VARCHAR(50) (day, night, watch_1, watch_2, etc.)
- `started_at` TIMESTAMPTZ
- `completed_at` TIMESTAMPTZ
- `approved_by` UUID
- `approved_at` TIMESTAMPTZ
- `approval_notes` TEXT
- `metadata` JSONB DEFAULT '{}'
- Standard timestamps (created_at, updated_at, created_by, updated_by)

**Foreign Keys:**
- `yacht_id` → yachts(id) (implied, not explicit FK)

**Soft Delete:** Yes (deleted_at, deleted_by, deletion_reason)

**RLS:** Enabled - yacht isolation via yacht_id

**Triggers:**
- Auto-set completed_at when status changes to 'completed'

---

### handover_items

**Purpose:** Individual items within a handover (polymorphic links to faults, WOs, equipment, etc.)

**Key Columns:**
- `id` UUID PRIMARY KEY
- `yacht_id` UUID NOT NULL
- `handover_id` UUID NOT NULL REFERENCES handovers(id) ON DELETE CASCADE
- `entity_id` UUID NOT NULL (polymorphic reference)
- `entity_type` VARCHAR(50) NOT NULL CHECK (entity_type IN ('fault', 'work_order', 'equipment', 'part', 'document', 'note', 'general'))
- `section` VARCHAR(100) (e.g., "Outstanding Issues", "Completed Tasks")
- `summary` TEXT
- `priority` INTEGER DEFAULT 0
- `status` VARCHAR(20) NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'acknowledged', 'completed', 'deferred'))
- `acknowledged_by` UUID
- `acknowledged_at` TIMESTAMPTZ
- `acknowledgement_notes` TEXT
- `metadata` JSONB DEFAULT '{}'
- `added_by` UUID NOT NULL (user who added this item)
- Standard timestamps (created_at, updated_at, updated_by)

**Foreign Keys:**
- `handover_id` → handovers(id) ON DELETE CASCADE
- Polymorphic - entity_id references various tables based on entity_type

**Soft Delete:** Yes (deleted_at, deleted_by, deletion_reason)

**RLS:** Enabled - yacht isolation via yacht_id

**Unique Constraints:**
- `uq_handover_items_entity` ON (handover_id, entity_id, entity_type, deleted_at) - prevents duplicate entity in same handover

**Triggers:**
- Auto-set acknowledged_at when status changes to 'acknowledged'

---

## CHECKLIST TABLES

### pms_checklists

**Purpose:** Master checklist templates and instances for maintenance, safety, inspections

**Key Columns:**
- `id` UUID PRIMARY KEY
- `yacht_id` UUID NOT NULL
- `name` VARCHAR(255) NOT NULL
- `description` TEXT
- `checklist_type` VARCHAR(50) NOT NULL DEFAULT 'maintenance' CHECK (checklist_type IN ('maintenance', 'safety', 'inspection', 'departure', 'arrival', 'watch', 'custom'))
- `equipment_id` UUID REFERENCES pms_equipment(id) ON DELETE SET NULL (optional association)
- `work_order_id` UUID REFERENCES pms_work_orders(id) ON DELETE SET NULL (optional association)
- `status` VARCHAR(20) NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'archived', 'draft'))
- `is_template` BOOLEAN NOT NULL DEFAULT false
- `total_items` INTEGER DEFAULT 0 (auto-computed)
- `completed_items` INTEGER DEFAULT 0 (auto-computed)
- `metadata` JSONB DEFAULT '{}'
- Standard timestamps (created_at, updated_at, created_by, updated_by)

**Foreign Keys:**
- `equipment_id` → pms_equipment(id) ON DELETE SET NULL
- `work_order_id` → pms_work_orders(id) ON DELETE SET NULL

**Soft Delete:** Yes (deleted_at, deleted_by, deletion_reason)

**RLS:** Enabled - yacht isolation via yacht_id

---

### pms_checklist_items

**Purpose:** Individual checklist items with completion tracking and value recording

**Key Columns:**
- `id` UUID PRIMARY KEY
- `yacht_id` UUID NOT NULL
- `checklist_id` UUID NOT NULL REFERENCES pms_checklists(id) ON DELETE CASCADE
- `description` TEXT NOT NULL
- `instructions` TEXT
- `sequence` INTEGER NOT NULL DEFAULT 0
- `is_completed` BOOLEAN NOT NULL DEFAULT false
- `completed_at` TIMESTAMPTZ
- `completed_by` UUID
- `completion_notes` TEXT
- `is_required` BOOLEAN NOT NULL DEFAULT true
- `requires_photo` BOOLEAN NOT NULL DEFAULT false
- `requires_signature` BOOLEAN NOT NULL DEFAULT false
- `requires_value` BOOLEAN NOT NULL DEFAULT false
- `value_type` VARCHAR(20) CHECK (value_type IS NULL OR value_type IN ('number', 'text', 'boolean', 'date'))
- `value_unit` VARCHAR(50) (mm, psi, hours, etc.)
- `value_min` NUMERIC
- `value_max` NUMERIC
- `recorded_value` TEXT
- `recorded_at` TIMESTAMPTZ
- `recorded_by` UUID
- `photo_url` TEXT
- `signature_data` JSONB
- `status` VARCHAR(20) NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'in_progress', 'completed', 'skipped', 'na'))
- `metadata` JSONB DEFAULT '{}'
- Standard timestamps (created_at, updated_at, created_by, updated_by)

**Foreign Keys:**
- `checklist_id` → pms_checklists(id) ON DELETE CASCADE

**Soft Delete:** Yes (deleted_at, deleted_by, deletion_reason)

**RLS:** Enabled - yacht isolation via yacht_id

**Triggers:**
- Auto-update parent checklist completion counts (total_items, completed_items)

---

### pms_work_order_checklist

**Purpose:** Checklist items specific to individual work orders (alternative to generic checklists)

**Key Columns:**
- `id` UUID PRIMARY KEY
- `yacht_id` UUID NOT NULL
- `work_order_id` UUID NOT NULL REFERENCES pms_work_orders(id) ON DELETE CASCADE
- `title` VARCHAR(255) NOT NULL
- `description` TEXT
- `instructions` TEXT
- `sequence` INTEGER NOT NULL DEFAULT 0
- `is_completed` BOOLEAN NOT NULL DEFAULT false
- `completed_at` TIMESTAMPTZ
- `completed_by` UUID
- `completion_notes` TEXT
- `is_required` BOOLEAN NOT NULL DEFAULT true
- `requires_photo` BOOLEAN NOT NULL DEFAULT false
- `requires_signature` BOOLEAN NOT NULL DEFAULT false
- `photo_url` TEXT
- `signature_data` JSONB
- `metadata` JSONB DEFAULT '{}'
- Standard timestamps (created_at, updated_at, created_by, updated_by)

**Foreign Keys:**
- `work_order_id` → pms_work_orders(id) ON DELETE CASCADE

**Soft Delete:** Yes (deleted_at, deleted_by, deletion_reason)

**RLS:** Enabled - yacht isolation via yacht_id

**Triggers:**
- Auto-set completed_at when is_completed changes to true

---

## SITUATION ENGINE TABLES

### action_executions

**Purpose:** Audit log for all action executions (performance, success/failure tracking)

**Key Columns:**
- `id` UUID PRIMARY KEY
- `yacht_id` UUID NOT NULL
- `user_id` UUID NOT NULL
- `action_name` TEXT NOT NULL
- `entity_type` TEXT NOT NULL
- `entity_id` UUID
- `params` JSONB (input parameters)
- `result` JSONB (output result)
- `success` BOOLEAN NOT NULL
- `error_code` TEXT
- `error_message` TEXT
- `duration_ms` INT
- `created_at` TIMESTAMPTZ NOT NULL DEFAULT NOW()

**Foreign Keys:** None (logging table)

**Soft Delete:** No (immutable log)

**RLS:** Enabled - yacht isolation via yacht_id

**Indexes:**
- `idx_action_executions_yacht` ON (yacht_id, created_at DESC)

---

### symptom_reports

**Purpose:** Symptom/fault pattern detection for situation engine

**Key Columns:**
- `id` UUID PRIMARY KEY
- `yacht_id` UUID NOT NULL
- `equipment_label` TEXT NOT NULL
- `symptom_code` TEXT NOT NULL
- `symptom_label` TEXT NOT NULL
- `search_query_id` UUID
- `reported_by` UUID
- `source` TEXT NOT NULL DEFAULT 'manual' (manual, search, etc.)
- `resolved` BOOLEAN DEFAULT FALSE
- `resolved_at` TIMESTAMPTZ
- `resolved_by` UUID
- `created_at` TIMESTAMPTZ NOT NULL DEFAULT NOW()

**Foreign Keys:** None

**Soft Delete:** No

**RLS:** Enabled - yacht isolation via yacht_id

**Indexes:**
- `idx_symptom_reports_recurrence` ON (yacht_id, equipment_label, symptom_code, created_at DESC)

**Helper Functions:**
- `check_symptom_recurrence(p_yacht_id UUID, p_equipment_label TEXT, p_symptom_code TEXT, p_threshold_count INT, p_threshold_days INT)` - detects recurring faults

---

### situation_detections

**Purpose:** Detected situations requiring user attention (proactive notifications)

**Key Columns:**
- `id` UUID PRIMARY KEY
- `yacht_id` UUID NOT NULL
- `user_id` UUID
- `situation_type` TEXT NOT NULL
- `severity` TEXT NOT NULL
- `label` TEXT NOT NULL
- `context` TEXT
- `evidence` JSONB
- `recommendations` JSONB
- `search_query_id` UUID
- `acknowledged` BOOLEAN DEFAULT FALSE
- `acknowledged_at` TIMESTAMPTZ
- `acknowledged_by` UUID
- `created_at` TIMESTAMPTZ NOT NULL DEFAULT NOW()

**Foreign Keys:** None

**Soft Delete:** No

**RLS:** Enabled - yacht isolation via yacht_id

---

### suggestion_log

**Purpose:** Learning log for RAG suggestions (tracks what was suggested, what was taken)

**Key Columns:**
- `id` UUID PRIMARY KEY
- `yacht_id` UUID NOT NULL
- `user_id` UUID
- `query_text` TEXT NOT NULL
- `intent` TEXT
- `search_query_id` UUID
- `situation_detected` BOOLEAN DEFAULT FALSE
- `situation_type` TEXT
- `suggested_actions` JSONB
- `action_taken` TEXT
- `action_taken_at` TIMESTAMPTZ
- `feedback` TEXT
- `created_at` TIMESTAMPTZ NOT NULL DEFAULT NOW()

**Foreign Keys:** None

**Soft Delete:** No

**RLS:** Enabled - yacht isolation via yacht_id

---

### predictive_state

**Purpose:** Equipment risk scoring for predictive maintenance

**Key Columns:**
- `id` UUID PRIMARY KEY
- `yacht_id` UUID NOT NULL
- `equipment_id` UUID NOT NULL UNIQUE
- `risk_score` DECIMAL(3,2) NOT NULL DEFAULT 0
- `confidence` DECIMAL(3,2) NOT NULL DEFAULT 0
- `failure_probability` DECIMAL(3,2) DEFAULT 0
- `trend` TEXT DEFAULT 'stable'
- `anomalies` JSONB DEFAULT '[]'
- `failure_modes` JSONB
- `recommended_actions` JSONB
- `next_maintenance_due` TIMESTAMPTZ
- `last_updated` TIMESTAMPTZ NOT NULL DEFAULT NOW()

**Foreign Keys:**
- `equipment_id` → pms_equipment(id) (implied)

**Soft Delete:** No

**RLS:** Enabled - yacht isolation via yacht_id

**Unique Constraints:**
- UNIQUE(equipment_id) - one risk state per equipment

**Helper Functions:**
- `get_equipment_risk(p_equipment_id UUID)` - retrieves risk metrics

---

## AUDIT & ACCOUNTABILITY TABLES

### pms_audit_log

**Purpose:** Audit trail for all mutations - NON-NEGOTIABLE for accountability

**Key Columns:**
- `id` UUID PRIMARY KEY
- `yacht_id` UUID NOT NULL
- `action` TEXT NOT NULL (e.g., 'acknowledge_fault', 'update_fault')
- `entity_type` TEXT NOT NULL (e.g., 'fault', 'work_order', 'equipment')
- `entity_id` UUID NOT NULL (ID of modified entity)
- `user_id` UUID NOT NULL
- `old_values` JSONB (previous state for updates)
- `new_values` JSONB NOT NULL (new state)
- `signature` JSONB NOT NULL DEFAULT '{}' ({user_id, execution_id, timestamp, action})
- `created_at` TIMESTAMPTZ NOT NULL DEFAULT NOW()

**Foreign Keys:** None (audit table must never cascade delete)

**Soft Delete:** No (immutable audit trail)

**RLS:** Enabled - users can only see audit logs for their yacht

**Indexes:**
- `idx_pms_audit_log_yacht` ON (yacht_id, created_at DESC)
- `idx_pms_audit_log_entity` ON (entity_type, entity_id)
- `idx_pms_audit_log_user` ON (user_id, created_at DESC)
- `idx_pms_audit_log_action` ON (action, created_at DESC)

**IMPORTANT:** This table is NON-NEGOTIABLE. Every mutation action MUST write to audit log.

---

## TABLES NOT YET IN SCHEMA (UNVERIFIED)

The following entity types are mentioned in cluster journeys but do NOT have dedicated tables in the current migration files:

### Shopping List Items
**Status:** UNVERIFIED - No migration file found
**Expected columns:** part_id, quantity_requested, priority, added_by, etc.
**Note:** May be implemented as JSONB in parts table or pending future migration

### Purchase Order Items
**Status:** UNVERIFIED - No migration file found
**Expected columns:** po_id, part_id, quantity_ordered, unit_price, etc.
**Note:** Junction table between purchase_orders and parts

### Receiving Sessions
**Status:** UNVERIFIED - No migration file found
**Expected columns:** po_id, session_status, checked_items, start_time, commit_time
**Note:** Temporary session state for multi-item receiving

### Documents Table
**Status:** UNVERIFIED - No migration file found
**Expected columns:** yacht_id, document_type, title, file_path, indexed_content
**Note:** May be using pms_attachments as polymorphic document storage

---

## GLOBAL PATTERNS

### Soft Delete Convention
All operational tables use:
- `deleted_at` TIMESTAMPTZ
- `deleted_by` UUID
- `deletion_reason` TEXT

Queries MUST include `WHERE deleted_at IS NULL` to exclude soft-deleted records.

### Standard Timestamps
All tables include:
- `created_at` TIMESTAMPTZ NOT NULL DEFAULT NOW()
- `updated_at` TIMESTAMPTZ
- `created_by` UUID
- `updated_by` UUID

Auto-updating triggers set `updated_at = NOW()` on UPDATE.

### RLS (Row Level Security)
All tables have RLS enabled. Policies enforce yacht isolation via:
```sql
yacht_id::text = (current_setting('request.jwt.claims', true)::json->>'yacht_id')
OR EXISTS (
    SELECT 1 FROM user_accounts
    WHERE user_accounts.auth_user_id = auth.uid()
    AND user_accounts.yacht_id = [table].yacht_id
)
```

### Polymorphic References
Tables like `handover_items`, `pms_attachments` use:
- `entity_type` VARCHAR (e.g., 'fault', 'work_order')
- `entity_id` UUID (reference to any table based on entity_type)

**Pattern:** Index on (entity_type, entity_id) for efficient lookups.

### JSONB Metadata
Most tables include:
- `metadata` JSONB DEFAULT '{}'

**Purpose:** Extensibility without schema changes. Use sparingly - prefer explicit columns for queryable fields.

---

## FOREIGN KEY CASCADE RULES

### ON DELETE CASCADE
Used when child records are meaningless without parent:
- `handover_items.handover_id` → handovers(id) ON DELETE CASCADE
- `pms_checklist_items.checklist_id` → pms_checklists(id) ON DELETE CASCADE
- `work_order_notes.work_order_id` → work_orders(id) ON DELETE CASCADE

### ON DELETE SET NULL
Used when child records should persist but lose reference:
- `pms_checklists.equipment_id` → pms_equipment(id) ON DELETE SET NULL
- `pms_checklists.work_order_id` → pms_work_orders(id) ON DELETE SET NULL

### NO CASCADE (Default)
Used for critical relationships - deletion MUST be explicit:
- Audit log foreign keys (never cascade)
- Cross-entity references (fault → work_order)

---

## STATUS FIELD ENUMERATIONS

### Equipment Status
`operational`, `degraded`, `failed`, `maintenance`, `decommissioned`

### Work Order Status
`draft`, `open`, `in_progress`, `on_hold`, `completed`, `cancelled`

### Fault Status
`open`, `investigating`, `work_ordered`, `resolved`, `closed`, `deferred`

### Fault Severity
`cosmetic`, `minor`, `major`, `critical`, `safety`

### Purchase Order Status
`draft`, `pending`, `approved`, `ordered`, `partial`, `received`, `cancelled`

### Handover Status
`draft`, `pending_review`, `approved`, `completed`, `cancelled`

### Handover Item Status
`pending`, `acknowledged`, `completed`, `deferred`

### Checklist Status
`active`, `archived`, `draft`

### Checklist Item Status
`pending`, `in_progress`, `completed`, `skipped`, `na`

---

## INDEX STRATEGY

### Standard Indexes (All Tables)
- `idx_[table]_yacht_id` ON (yacht_id) - yacht isolation
- `idx_[table]_created_at` ON (created_at DESC) - time-based queries

### Foreign Key Indexes
All foreign key columns have indexes for join performance.

### Status Indexes
Status columns indexed with partial indexes:
```sql
CREATE INDEX idx_[table]_status ON [table](status) WHERE deleted_at IS NULL;
```

### Composite Indexes
Used for common query patterns:
- `idx_symptom_reports_recurrence` ON (yacht_id, equipment_label, symptom_code, created_at DESC)
- `idx_pms_checklist_items_sequence` ON (checklist_id, sequence)

---

## TRIGGER SUMMARY

### Auto-Update Triggers
Most tables have:
```sql
CREATE TRIGGER trg_[table]_updated_at
    BEFORE UPDATE ON [table]
    FOR EACH ROW
    EXECUTE FUNCTION update_[table]_updated_at();
```

### State Transition Triggers
- Handovers: Auto-set `completed_at` when status → 'completed'
- Handover Items: Auto-set `acknowledged_at` when status → 'acknowledged'
- Checklist Items: Auto-update parent checklist completion counts
- Work Order Checklist: Auto-set `completed_at` when is_completed → true

---

## VERIFICATION STATUS

**Tables Verified from Migrations:** 25 tables
**Tables Unverified (Not in Schema):** 4 entity types (shopping list items, PO items, receiving sessions, documents)

**Last Migration Read:** 20260121_001_create_pms_audit_log.sql

**Rule:** If a table is marked UNVERIFIED, do NOT assume it exists. Implement logic without assuming schema or flag as future work.

---

**Status:** DB_TRUTH_PACK complete. All tables extracted from repo migrations. Ready for ACTION_IO_MATRIX.md.
