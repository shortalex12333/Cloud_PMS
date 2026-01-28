# Entity Lens: Fault

**Status**: Draft v1 - Production DB Verified
**Last Updated**: 2026-01-24
**Schema Source**: Production Supabase Database (vzsohavtuotocgrfkfyd.supabase.co)

---

## A) Base Entity Lens Definition

### Entity Type
**Fault** (Equipment fault, defect, malfunction)

**Canonical Table**: `pms_faults`

**When This Lens Activates**:
- User opens Fault Detail in the same SPA. URL updates to encode state (e.g., `/faults/<uuid>` or `/?focus=fault:<uuid>`) for deep-linking, refresh, and sharing. **No page reload. No second site.**
- User clicks fault from equipment fault list
- User views fault in "Related Faults" section
- User selects fault from dashboard or notifications

**Celeste is one app** (apps.celeste7.ai). URL changes = browser state encoding for deep-linking, NOT navigation to another page.

**Core Purpose**: View and manage equipment faults reported on the yacht.

---

## B) Schema Verification (Production DB Truth)

### Primary Table: `pms_faults`

**Source**: Production database introspection (2026-01-24)

**Row Count**: 1,623

**Columns** (19):

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | UUID | NOT NULL | gen_random_uuid() | PK |
| `yacht_id` | UUID | NOT NULL | | FK → `yacht_registry(id)`, RLS isolation key |
| `equipment_id` | UUID | NOT NULL | | FK → `pms_equipment(id)` |
| `fault_code` | TEXT | YES | | Auto-generated (if trigger exists) |
| `title` | TEXT | NOT NULL | | Display name |
| `description` | TEXT | YES | | Long-form description |
| `severity` | fault_severity | NOT NULL | 'medium' | Enum: low, medium, high, critical |
| `status` | TEXT | YES | 'open' | CHECK: open, investigating, resolved, closed |
| `detected_at` | TIMESTAMPTZ | NOT NULL | now() | When fault was detected |
| `resolved_at` | TIMESTAMPTZ | YES | | When fault was resolved |
| `resolved_by` | UUID | YES | | User who resolved fault |
| `work_order_id` | UUID | YES | | FK → `pms_work_orders(id)` |
| `metadata` | JSONB | YES | '{}' | |
| `created_at` | TIMESTAMPTZ | NOT NULL | now() | |
| `updated_at` | TIMESTAMPTZ | YES | | Auto-updated by trigger |
| `updated_by` | UUID | YES | | |
| `deleted_at` | TIMESTAMPTZ | YES | | ✅ SOFT DELETE EXISTS |
| `deleted_by` | UUID | YES | | |
| `deletion_reason` | TEXT | YES | | |

**DB Truth Snapshot**:
- **Constraints**: PK(id), FK(yacht_id → yacht_registry), FK(equipment_id → pms_equipment ON DELETE CASCADE), FK(work_order_id → pms_work_orders ON DELETE SET NULL)
- **Indexes**: yacht_id, equipment_id, fault_code, detected_at DESC, severity, status, work_order_id
- **RLS**: ENABLED - 3 policies (engineers can manage, users can view, service role full access)
- **Triggers**:
  - `no_hard_delete_faults` - prevents hard delete (enforces soft delete)
  - `set_updated_at_faults` - auto-updates updated_at timestamp
  - `trg_fault_insert_predictive`, `trg_fault_update_predictive` - notify predictive system

**Missing Columns** (vs ideal):
- No `detected_by` (who reported fault) - can use `created_by` from audit log
- No `acknowledged_at` / `acknowledged_by` - would need to add if acknowledgment workflow required
- No `location` text field - equipment_id provides location indirectly

---

### Related Table: `pms_notes`

**Source**: Production database introspection (2026-01-24)

**Row Count**: 5

**Purpose**: Generic notes table used for fault notes, equipment notes, work order notes.

**Key Columns**:

| Column | Type | Nullable | Notes |
|--------|------|----------|-------|
| `id` | UUID | NOT NULL | PK |
| `yacht_id` | UUID | NOT NULL | |
| `fault_id` | UUID | YES | FK → `pms_faults(id)` ON DELETE CASCADE |
| `equipment_id` | UUID | YES | FK → `pms_equipment(id)` |
| `work_order_id` | UUID | YES | FK → `pms_work_orders(id)` |
| `text` | TEXT | NOT NULL | Note content |
| `note_type` | note_type | NOT NULL | Enum: general, observation, warning, resolution, handover |
| `created_by` | UUID | NOT NULL | |
| `attachments` | JSONB | YES | '[]' |
| `metadata` | JSONB | YES | '{}' |
| `created_at` | TIMESTAMPTZ | NOT NULL | now() |
| `updated_at` | TIMESTAMPTZ | NOT NULL | now() |

**DB Truth Snapshot**:
- **Constraints**: PK(id), FK(fault_id → pms_faults ON DELETE CASCADE), FK(yacht_id → yacht_registry)
- **Indexes**: yacht_id, created_at DESC, equipment_id, fault_id
- **RLS**: ENABLED

---

### Related Table: `pms_attachments`

**Source**: Production database introspection (2026-01-24)

**Row Count**: 6

**Purpose**: Generic attachments table for fault photos, equipment docs, WO attachments.

**Key Columns**:

| Column | Type | Nullable | Notes |
|--------|------|----------|-------|
| `id` | UUID | NOT NULL | PK |
| `yacht_id` | UUID | NOT NULL | |
| `entity_type` | VARCHAR | NOT NULL | CHECK: 'fault', 'work_order', 'equipment', 'checklist_item', 'note', 'handover', 'purchase_order' |
| `entity_id` | UUID | NOT NULL | ID of linked entity (fault, WO, etc.) |
| `filename` | VARCHAR | NOT NULL | |
| `original_filename` | VARCHAR | YES | |
| `mime_type` | VARCHAR | NOT NULL | |
| `file_size` | INTEGER | YES | |
| `storage_path` | TEXT | NOT NULL | Cloud storage path |
| `width` | INTEGER | YES | For images |
| `height` | INTEGER | YES | For images |
| `thumbnail_path` | TEXT | YES | |
| `description` | TEXT | YES | |
| `tags` | TEXT[] | YES | |
| `metadata` | JSONB | YES | '{}' |
| `uploaded_by` | UUID | NOT NULL | |
| `uploaded_at` | TIMESTAMPTZ | NOT NULL | now() |
| `created_at` | TIMESTAMPTZ | NOT NULL | now() |
| `deleted_at` | TIMESTAMPTZ | YES | ✅ SOFT DELETE EXISTS |
| `deleted_by` | UUID | YES | |
| `deletion_reason` | TEXT | YES | |

**DB Truth Snapshot**:
- **Constraints**: PK(id), CHECK(entity_type IN ('fault', 'work_order', ...))
- **Indexes**: entity_type + entity_id, mime_type
- **RLS**: ENABLED

---

### Related Table: `pms_work_orders`

**Source**: Production database introspection (2026-01-24)

**Row Count**: 2,820

**Purpose**: Work orders, including those created from faults.

**Key Columns**:

| Column | Type | Nullable | Notes |
|--------|------|----------|-------|
| `id` | UUID | NOT NULL | PK |
| `yacht_id` | UUID | NOT NULL | |
| `fault_id` | UUID | YES | FK → `pms_faults(id)` ON DELETE SET NULL |
| `equipment_id` | UUID | YES | FK → `pms_equipment(id)` |
| `title` | TEXT | NOT NULL | |
| `description` | TEXT | YES | |
| `type` | work_order_type | NOT NULL | Enum: scheduled, corrective, unplanned, preventive |
| `priority` | work_order_priority | NOT NULL | Enum: routine, important, critical, emergency |
| `status` | work_order_status | NOT NULL | Enum: planned, in_progress, completed, deferred, cancelled |
| `wo_number` | TEXT | YES | Auto-generated work order number |
| `due_date` | DATE | YES | |
| `assigned_to` | UUID | YES | |
| `created_by` | UUID | NOT NULL | |
| `created_at` | TIMESTAMPTZ | NOT NULL | now() |
| `deleted_at` | TIMESTAMPTZ | YES | ✅ SOFT DELETE EXISTS |

**DB Truth Snapshot**:
- **Constraints**: PK(id), FK(fault_id → pms_faults), FK(equipment_id → pms_equipment), FK(yacht_id → yacht_registry)
- **Indexes**: yacht_id, equipment_id, fault_id, status, assigned_to, wo_number
- **RLS**: ENABLED

---

### Yacht Rank Hierarchy

**Source**: `/Users/celeste7/Desktop/Cloud_PMS_docs_v2/16_Roles_of_users/ranks.md`

**Command Chain**:
1. Captain (highest)
2. Staff Captain / Chief Officer
3. Second Officer
4. Third Officer
5. Safety Officer

**Heads of Department (HoD)**:
- Chief Engineer (Engineering, rank 14)
- Chief Steward/Stewardess (Interior, rank 23)
- Purser / Hotel Manager (Admin/Interior, rank 24)
- Executive Chef (Galley, rank 35)
- Chief Mate / First Officer (Deck, rank 6)
- Head of Security (Security, rank 40)

**Total Crew**: 45-60 on 125m yacht

---

## C) Role Permissions (Simple Tier Model)

### Everyone (All Crew)
- View faults
- View fault notes
- View fault attachments
- `report_fault`
- `add_fault_note`
- `attach_file_to_fault`

### Engineers + Deck + Interior (Department Crew)
- All crew permissions +
- `update_fault_status`
- `create_work_order_from_fault`

**RLS Policy** (from DB):
- "Engineers can manage faults" - chief_engineer, eto, deck, interior roles
- "Users can view faults" - all crew via yacht_id match

### Restricted
- **Archive fault**: Captain, HoD, Purser + **SIGNATURE REQUIRED**

**Audit Requirement**: All mutations logged with user_id, session_id, IP address, timestamp.

---

## D) Default Display Fields (Not Actions)

**Always Visible**:
- Fault code (e.g., FLT-2026-001234)
- Title
- Description
- Severity (badge: low=gray, medium=yellow, high=orange, critical=red)
- Status (badge: open, investigating, resolved, closed)
- Equipment name (linked to equipment lens)
- Detected at (timestamp)
- Resolved at (if resolved)
- Resolved by (if resolved)
- Linked work order (if exists)
- Created by, created at
- Last updated at

---

## E) Fault Micro-Actions (Exactly 6)

### 1. `report_fault`
- **Label**: "Report Fault"
- **Purpose**: Create new equipment fault
- **Writes to**: `pms_faults`
- **Signature**: NO (audit only)
- **Modal**: `ReportFaultModal.tsx`
- **Fields**:
  - REQUIRED: `title`, `severity` (dropdown: low, medium, high, critical), `equipment_id`
  - OPTIONAL: `description`, `fault_code` (auto-generated if blank)
  - AUTOMATIC: `id`, `yacht_id`, `status='open'`, `detected_at=NOW()`, `created_at`, `metadata`

### 2. `create_work_order_from_fault`
- **Label**: "Create Work Order"
- **Purpose**: Generate corrective work order from fault
- **Writes to**: `pms_work_orders`, updates `pms_faults.work_order_id`
- **Signature**: NO (audit only)
- **Modal**: `CreateWorkOrderFromFaultModal.tsx`
- **Fields**:
  - DERIVED (prefill): `title` (from fault.title), `equipment_id` (from fault.equipment_id), `fault_id` (current fault), `type='corrective'`, `priority` (map severity: critical→emergency, high→critical, medium→important, low→routine)
  - OPTIONAL: `description`, `due_date`, `assigned_to` (dropdown of crew)
  - AUTOMATIC: `id`, `yacht_id`, `wo_number` (trigger-generated), `status='planned'`, `created_by`, `created_at`
- **Post-action**: Link WO back to fault by updating `pms_faults.work_order_id`

### 3. `update_fault_status`
- **Label**: "Update Status"
- **Purpose**: Change fault status through workflow
- **Writes to**: `pms_faults.status`, `pms_faults.updated_at`, `pms_faults.updated_by`
- **Signature**: NO (audit only)
- **Modal**: `UpdateFaultStatusModal.tsx`
- **Fields**:
  - REQUIRED: `status` (dropdown: open, investigating, resolved, closed)
  - OPTIONAL: `notes` (creates note in pms_notes if provided)
  - AUTOMATIC: `updated_at=NOW()`, `updated_by=user_id`, `resolved_at=NOW()` if status='resolved', `resolved_by=user_id` if status='resolved'
- **Workflow**: open → investigating → resolved → closed

### 4. `add_fault_note`
- **Label**: "Add Note"
- **Purpose**: Add observation or resolution note to fault
- **Writes to**: `pms_notes`
- **Signature**: NO (audit only)
- **Modal**: `AddFaultNoteModal.tsx`
- **Fields**:
  - REQUIRED: `text`
  - OPTIONAL: `note_type` (dropdown: general, observation, warning, resolution, handover)
  - AUTOMATIC: `id`, `yacht_id`, `fault_id` (from context), `created_by`, `created_at`, `updated_at`, `metadata`

### 5. `attach_file_to_fault`
- **Label**: "Attach Photo/File"
- **Purpose**: Attach photo or document to fault (e.g., damage photo)
- **Writes to**: `pms_attachments`
- **Signature**: NO (audit only)
- **Modal**: File upload modal
- **Fields**:
  - REQUIRED: File upload (image or document)
  - OPTIONAL: `description`, `tags`
  - AUTOMATIC: `id`, `yacht_id`, `entity_type='fault'`, `entity_id` (current fault), `filename`, `mime_type`, `file_size`, `storage_path`, `uploaded_by`, `uploaded_at`, `created_at`

### 6. `archive_fault`
- **Label**: "Archive Fault"
- **Purpose**: Soft delete fault (30-day undo window)
- **Writes to**: `pms_faults.deleted_at`, `deleted_by`, `deletion_reason`
- **Signature**: **YES - REQUIRED**
- **Modal**: `ArchiveFaultModal.tsx` with signature capture
- **Permission**: Captain, HoD, Purser only
- **Undo**: Faults remain in DB for 30 days, can be restored by same roles
- **Trigger**: `no_hard_delete_faults` prevents actual DELETE, enforces soft delete

**Hard Delete**: Not allowed (trigger blocks it). Phase 2 only if needed.

---

## F) Related Button Contract

**Related** (top-right button in fault detail):
- FK joins (equipment, work order, parts used, notes)
- Vector search seeded from entity fields only: `title`, `description`, `fault_code`, `equipment.name`
- **Never user query**. **No predictive logic**.

Examples:
- "Equipment with this Fault" → FK join on `pms_faults.equipment_id`
- "Linked Work Order" → FK join on `pms_faults.work_order_id`
- "Fault Notes" → FK join on `pms_notes.fault_id`
- "Fault Attachments" → FK join on `pms_attachments WHERE entity_type='fault' AND entity_id=fault.id`
- "Related Manuals" → Vector search using `title + description` → `documents` + `search_chunks`
- "Similar Faults" → Vector search using `title + description + equipment.name`

---

## G) Situation Modifier: Critical Fault Active

### Trigger (Simple)

```sql
severity IN ('critical', 'high')
AND status IN ('open', 'investigating')
```

### UX Changes

**Severity Badge**:
- **Low**: Gray badge
- **Medium**: Yellow badge
- **High**: Orange badge
- **Critical**: Red badge

**Action Reordering** (when modifier active):
- **BEFORE**: Update Status (primary), Add Note (secondary)
- **AFTER**: Create Work Order (primary, red/orange button), Update Status (secondary)

**Banner** (ONE only):
- Red/Orange banner at top: "⚠️ Critical fault active - requires immediate attention" (if critical) or "High severity fault - create work order to resolve" (if high)
- Dismissible: YES
- CTA: "Create Work Order" button inline

**Prefill** (if user clicks Create Work Order):
- `priority = 'emergency'` if severity='critical', else `'critical'`
- `type = 'corrective'`
- `title` = fault.title
- `description` = "Corrective action for fault: {fault_code}"

**No prediction. No urgency scoring. No complex state machine.**

---

## H) Edge Cases

### 1. Work Order Already Exists for Fault
- **Scenario**: User tries to create WO, but `fault.work_order_id` is already populated
- **Behavior**:
  - Modal shows warning: "Work order already exists for this fault: {wo_number}"
  - Action button changes to "View Existing Work Order" (navigates to WO lens)
  - Allow creating additional WO if user confirms (updates fault.work_order_id to new WO, or keeps original - TBD)

### 2. Archive Collision (Soft Delete)
- **Scenario**: User A viewing fault. User B archives fault. User A tries action.
- **Behavior**:
  - Action fails with: "Fault archived by {user} at {time}"
  - Show "Restore Fault" option for authorized roles (Captain, HoD, Purser)
  - 30-day undo window

---

## I) Blockers

### BLOCKER 1: No `detected_by` Column
- **Impact**: Cannot track who originally reported fault (vs who created the DB record)
- **Workaround**: Use `created_by` from audit log or ledger
- **Resolution**: Add `detected_by UUID` column to `pms_faults` if tracking original reporter is required

### BLOCKER 2: Missing Fault-Specific Tables
- **Impact**: `pms_fault_notes` and `pms_fault_attachments` do not exist in production
- **Workaround**: ✅ Use generic `pms_notes` (has `fault_id` FK) and `pms_attachments` (has `entity_type='fault'`)
- **Status**: No blocker - generic tables work correctly

### BLOCKER 3: Status Not an Enum
- **Impact**: `pms_faults.status` is TEXT with CHECK constraint, not enum
- **Actual Values**: open, investigating, resolved, closed (enforced by CHECK constraint)
- **Status**: No blocker - works fine, just note for frontend dropdowns

---

## J) Summary

**Entity Lens**: Fault
**Primary Table**: `pms_faults` (19 columns, 1,623 rows, production DB verified)
**Related Tables**: `pms_notes` (fault notes), `pms_attachments` (fault attachments), `pms_work_orders` (linked WO)
**Situation Modifiers**: 1 (Critical Fault Active - simple severity + status check)
**Micro-Actions**: 6 (report_fault, create_work_order_from_fault, update_fault_status, add_fault_note, attach_file_to_fault, archive_fault)
**Default Display Fields**: 11 (fault code, title, severity badge, status, equipment, timestamps, etc. - NOT actions)
**Blockers**: 1 (no detected_by column - use created_by from audit as workaround)

**Key Principles**:
- ✅ Production DB is truth (NOT migrations)
- ✅ SPA route state (`/faults/<uuid>`) - no page reload
- ✅ Related = FK joins + vector from entity fields only (never user query)
- ✅ Generic tables work: pms_notes + pms_attachments (fault-specific tables don't exist)
- ✅ Permissions: All crew can report/note, engineers can manage, Captain/HoD can archive (with signature)
- ✅ Critical Fault modifier: severity + status check, red/orange badge + button promotion + ONE dismissible banner
- ✅ Archive (soft delete) enforced by trigger. Hard delete blocked.
- ✅ RLS policies: engineers manage, all crew view

---

**STOP. Awaiting review.**
