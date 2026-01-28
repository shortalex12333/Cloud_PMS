# Entity Lens: Fault (DB-GROUNDED)

**Status**: v5 - GOLD STANDARD TEMPLATE
**Last Updated**: 2026-01-24
**Schema Source**: Production Supabase Database (vzsohavtuotocgrfkfyd.supabase.co)
**DB Snapshot**: `/Volumes/Backup/CELESTE/database_schema.txt`
**Operating Procedure**: `LENS_BUILDER_OPERATING_PROCEDURE.md`

> **TEMPLATE**: This document is the gold standard for all Entity Lens documents. New lenses MUST follow this structure and the operating procedure.

---

# BLOCKERS (must resolve before lens is shippable)

| ID | Blocker | Affects | Resolution |
|----|---------|---------|------------|
| **B1** | `pms_notes` has no RLS policies deployed | `add_fault_note` action | Deploy RLS migration |
| **B2** | `generate_fault_code()` function doesn't exist | Fault auto-creation from WO | Create function or use application-layer generation |
| **B3** | `storage.objects` INSERT policy for `pms-discrepancy-photos` not proven | `attach_file_to_fault` action | Verify/deploy storage policy |

> **RULE**: Any microaction with a BLOCKER is **disabled in UI** until resolved. Do not ship aspirational actions.

---

# PART 0: CANONICAL HELPERS

## Yacht ID Resolution

**Deployed function** (from `00000000000011_05_rename_auth_tables.sql:230`):

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
- NO competing patterns (JWT claims vs DB join) - single source of truth

---

## Audit `entity_type` Convention

Canonical values for `pms_audit_log.entity_type`:

| Value | Table |
|-------|-------|
| `fault` | pms_faults |
| `work_order` | pms_work_orders |
| `note` | pms_notes |
| `attachment` | pms_attachments |
| `equipment` | pms_equipment |
| `part` | pms_parts |
| `inventory_item` | pms_inventory_items |
| `shopping_list_item` | pms_shopping_list_items |
| `receiving_event` | pms_receiving_events |

> **INVARIANT**: Every lens MUST use these exact values. No inventing new names.

---

## Signature Invariant

`pms_audit_log.signature` is **NOT NULL**. Convention:

| Scenario | Value |
|----------|-------|
| Non-signature action | `'{}'::jsonb` (empty object) |
| Signature-required action | Full signature payload (see Part 1) |

> **INVARIANT**: Signature is always present. Empty object `{}` means "signature not required for this action." Downstream code (frontend, pipelines, ledger) can rely on this.

---

# PART 1: EXACT DATABASE SCHEMA

## Table: `pms_faults`

**Production DB Columns** (19 total):

| Column | PostgreSQL Type | Nullable | Classification | Notes |
|--------|-----------------|----------|----------------|-------|
| `id` | uuid | NOT NULL | BACKEND_AUTO | PK, gen_random_uuid() |
| `yacht_id` | uuid | NOT NULL | BACKEND_AUTO | FK → yacht_registry(id), from auth context |
| `equipment_id` | uuid | NOT NULL | REQUIRED | FK → pms_equipment(id) |
| `fault_code` | text | YES | BACKEND_AUTO | Auto-generated: FLT-{YYYY}-{NNNNNN} |
| `title` | text | NOT NULL | REQUIRED | Display name |
| `description` | text | YES | OPTIONAL | Long-form details |
| `severity` | public.fault_severity | NOT NULL | REQUIRED | Enum: low, medium, high, critical |
| `status` | text | YES | BACKEND_AUTO | Default: 'open'. Values: open, investigating, resolved, closed |
| `detected_at` | timestamp with time zone | NOT NULL | BACKEND_AUTO | Default: NOW() |
| `resolved_at` | timestamp with time zone | YES | BACKEND_AUTO | Set when status='resolved' |
| `resolved_by` | uuid | YES | BACKEND_AUTO | FK → auth.users, set when status='resolved' |
| `work_order_id` | uuid | YES | BACKEND_AUTO | FK → pms_work_orders(id), linked at WO creation |
| `metadata` | jsonb | YES | BACKEND_AUTO | Session context, additional data |
| `created_at` | timestamp with time zone | NOT NULL | BACKEND_AUTO | Default: NOW() |
| `updated_at` | timestamp with time zone | YES | BACKEND_AUTO | Trigger: set_updated_at |
| `updated_by` | uuid | YES | BACKEND_AUTO | Set on any UPDATE |
| `deleted_at` | timestamp with time zone | YES | **DEPRECATED** | Never populated - faults preserved |
| `deleted_by` | uuid | YES | **DEPRECATED** | Never populated |
| `deletion_reason` | text | YES | **DEPRECATED** | Never populated |

> **DELETION DOCTRINE**: `deleted_*` columns exist for legacy schema reasons. Do NOT write to them. Do NOT filter by them. Do NOT build UI around them. Faults are NEVER deleted — history is preserved for recurrence analysis.

> **EQUIPMENT CONSTRAINT**: `equipment_id` is **NOT NULL**. Every fault MUST be attached to equipment. There is no "general fault" or "unknown equipment" fault. If product wants that later, it's a schema change requiring migration + this doc update.

**Missing Columns** (vs ideal):
| Column | Type | Purpose | Migration Status |
|--------|------|---------|------------------|
| `detected_by` | uuid | Who reported fault | Section 1.1 in CUMULATIVE_SCHEMA_MIGRATIONS.sql |

---

## Table: `pms_notes`

**Production DB Columns** (12 total):

| Column | PostgreSQL Type | Nullable | Classification | Notes |
|--------|-----------------|----------|----------------|-------|
| `id` | uuid | NOT NULL | BACKEND_AUTO | PK |
| `yacht_id` | uuid | NOT NULL | BACKEND_AUTO | FK → yacht_registry(id) |
| `fault_id` | uuid | YES | CONTEXT | FK → pms_faults(id), set for fault notes |
| `equipment_id` | uuid | YES | CONTEXT | FK → pms_equipment(id), set for equipment notes |
| `work_order_id` | uuid | YES | CONTEXT | FK → pms_work_orders(id), set for WO notes |
| `text` | text | NOT NULL | REQUIRED | Note content |
| `note_type` | public.note_type | NOT NULL | OPTIONAL | Enum: general, observation, warning, resolution, handover. Default: 'general' |
| `attachments` | jsonb | YES | OPTIONAL | Inline attachment references |
| `metadata` | jsonb | YES | BACKEND_AUTO | Session context |
| `created_by` | uuid | NOT NULL | BACKEND_AUTO | FK → auth.users |
| `created_at` | timestamp with time zone | NOT NULL | BACKEND_AUTO | Default: NOW() |
| `updated_at` | timestamp with time zone | NOT NULL | BACKEND_AUTO | Default: NOW() |

**Note**: Only ONE of `fault_id`, `equipment_id`, `work_order_id` should be populated per row.

---

## Table: `pms_attachments`

**Production DB Columns** (22 total):

| Column | PostgreSQL Type | Nullable | Classification | Notes |
|--------|-----------------|----------|----------------|-------|
| `id` | uuid | NOT NULL | BACKEND_AUTO | PK |
| `yacht_id` | uuid | NOT NULL | BACKEND_AUTO | FK → yacht_registry(id) |
| `entity_type` | character varying | NOT NULL | REQUIRED | 'fault', 'work_order', 'equipment', etc. |
| `entity_id` | uuid | NOT NULL | CONTEXT | ID of linked entity |
| `filename` | character varying | NOT NULL | BACKEND_AUTO | Generated storage filename |
| `original_filename` | character varying | YES | BACKEND_AUTO | User's original filename |
| `mime_type` | character varying | NOT NULL | BACKEND_AUTO | Detected from file |
| `file_size` | integer | YES | BACKEND_AUTO | Size in bytes |
| `storage_path` | text | NOT NULL | BACKEND_AUTO | Cloud storage path |
| `width` | integer | YES | BACKEND_AUTO | For images |
| `height` | integer | YES | BACKEND_AUTO | For images |
| `thumbnail_path` | text | YES | BACKEND_AUTO | Generated thumbnail |
| `description` | text | YES | OPTIONAL | User description |
| `tags` | text[] | YES | OPTIONAL | User tags |
| `metadata` | jsonb | YES | BACKEND_AUTO | Session context |
| `uploaded_by` | uuid | NOT NULL | BACKEND_AUTO | FK → auth.users |
| `uploaded_at` | timestamp with time zone | NOT NULL | BACKEND_AUTO | Default: NOW() |
| `created_at` | timestamp with time zone | NOT NULL | BACKEND_AUTO | Default: NOW() |
| `updated_at` | timestamp with time zone | YES | BACKEND_AUTO | |
| `deleted_at` | timestamp with time zone | YES | BACKEND_AUTO | Soft delete |
| `deleted_by` | uuid | YES | BACKEND_AUTO | |
| `deletion_reason` | text | YES | OPTIONAL | |

**Storage Bucket Mapping**:
```
entity_type='fault' → bucket: pms-discrepancy-photos
entity_type='work_order' → bucket: pms-discrepancy-photos
entity_type='receiving' → bucket: pms-receiving-images
```

---

## Table: `pms_work_orders`

**Production DB Columns** (29 total):

| Column | PostgreSQL Type | Nullable | Classification | Notes |
|--------|-----------------|----------|----------------|-------|
| `id` | uuid | NOT NULL | BACKEND_AUTO | PK |
| `yacht_id` | uuid | NOT NULL | BACKEND_AUTO | FK → yacht_registry(id) |
| `equipment_id` | uuid | YES | CONTEXT | FK → pms_equipment(id) |
| `fault_id` | uuid | YES | CONTEXT | FK → pms_faults(id), set when WO from fault |
| `wo_number` | text | YES | BACKEND_AUTO | Auto-generated: WO-{YYYY}-{NNNN} |
| `title` | text | NOT NULL | REQUIRED | |
| `description` | text | YES | OPTIONAL | |
| `type` | public.work_order_type | NOT NULL | REQUIRED | Enum: scheduled, corrective, unplanned, preventive |
| `priority` | public.work_order_priority | NOT NULL | REQUIRED | Enum: routine, important, critical, emergency |
| `status` | public.work_order_status | NOT NULL | BACKEND_AUTO | Default: 'planned'. Enum: planned, in_progress, completed, deferred, cancelled |
| `assigned_to` | uuid | YES | OPTIONAL | FK → auth.users |
| `due_date` | date | YES | OPTIONAL | |
| `due_hours` | integer | YES | OPTIONAL | For hour-based scheduling |
| `frequency` | jsonb | YES | OPTIONAL | For recurring WOs |
| `completed_at` | timestamp with time zone | YES | BACKEND_AUTO | Set when status='completed' |
| `completed_by` | uuid | YES | BACKEND_AUTO | Set when status='completed' |
| `completion_notes` | text | YES | OPTIONAL | |
| `last_completed_date` | date | YES | BACKEND_AUTO | For recurring WOs |
| `last_completed_hours` | integer | YES | BACKEND_AUTO | |
| `work_order_type` | text | YES | **DEPRECATED** | Use `type` enum instead |
| `vendor_contact_hash` | text | YES | BACKEND_AUTO | |
| `metadata` | jsonb | YES | BACKEND_AUTO | |
| `created_by` | uuid | NOT NULL | BACKEND_AUTO | FK → auth.users |
| `created_at` | timestamp with time zone | NOT NULL | BACKEND_AUTO | |
| `updated_at` | timestamp with time zone | NOT NULL | BACKEND_AUTO | |
| `updated_by` | uuid | YES | BACKEND_AUTO | |
| `deleted_at` | timestamp with time zone | YES | BACKEND_AUTO | Soft delete |
| `deleted_by` | uuid | YES | BACKEND_AUTO | |
| `deletion_reason` | text | YES | OPTIONAL | |

---

## Table: `pms_audit_log`

**Production DB Columns** (11 total):

| Column | PostgreSQL Type | Nullable | Classification | Notes |
|--------|-----------------|----------|----------------|-------|
| `id` | uuid | NOT NULL | BACKEND_AUTO | PK |
| `yacht_id` | uuid | NOT NULL | BACKEND_AUTO | FK → yacht_registry(id) |
| `entity_type` | text | NOT NULL | BACKEND_AUTO | 'fault', 'work_order', 'note', etc. |
| `entity_id` | uuid | NOT NULL | BACKEND_AUTO | ID of affected entity |
| `action` | text | NOT NULL | BACKEND_AUTO | Action name (e.g., 'create_fault', 'add_note') |
| `user_id` | uuid | NOT NULL | BACKEND_AUTO | FK → auth.users |
| `old_values` | jsonb | YES | BACKEND_AUTO | State before change |
| `new_values` | jsonb | NOT NULL | BACKEND_AUTO | State after change |
| `signature` | jsonb | NOT NULL | BACKEND_AUTO | Empty {} for non-signature actions, populated for signature-required |
| `metadata` | jsonb | YES | BACKEND_AUTO | Session context |
| `created_at` | timestamp with time zone | NOT NULL | BACKEND_AUTO | |

**Signature JSONB Structure** (when required):
```json
{
  "signature_hash": "base64_encoded_signature_image",
  "signed_by": "user_uuid",
  "signed_at": "2026-01-24T14:30:00Z",
  "role_at_signing": "captain",
  "signature_type": "approval"
}
```

**Metadata JSONB Structure** (always present):
```json
{
  "session_id": "uuid",
  "ip_address": "192.168.1.100",
  "user_agent": "Mozilla/5.0...",
  "device_type": "tablet",
  "app_version": "1.2.3"
}
```

---

## Table: `auth_signatures`

**Production DB Columns** (9 total):

| Column | PostgreSQL Type | Nullable | Classification | Notes |
|--------|-----------------|----------|----------------|-------|
| `id` | uuid | NOT NULL | BACKEND_AUTO | PK |
| `yacht_id` | uuid | NOT NULL | BACKEND_AUTO | |
| `user_id` | uuid | NOT NULL | BACKEND_AUTO | Who signed |
| `entity_type` | text | NOT NULL | BACKEND_AUTO | What was signed |
| `entity_id` | uuid | NOT NULL | BACKEND_AUTO | ID of signed entity |
| `signature_type` | text | NOT NULL | BACKEND_AUTO | Type of signature action |
| `signature_hash` | text | NOT NULL | BACKEND_AUTO | Base64 signature image |
| `role_at_signing` | text | NOT NULL | BACKEND_AUTO | User's role when signing |
| `signed_at` | timestamp with time zone | NOT NULL | BACKEND_AUTO | |

---

## Table: `auth_users_profiles`

**Production DB Columns** (8 total):

| Column | PostgreSQL Type | Nullable | Notes |
|--------|-----------------|----------|-------|
| `id` | uuid | NOT NULL | PK, matches auth.users.id |
| `yacht_id` | uuid | NOT NULL | FK → yacht_registry(id) |
| `email` | text | NOT NULL | User email |
| `name` | text | NOT NULL | Display name |
| `is_active` | boolean | NOT NULL | Account status |
| `metadata` | jsonb | YES | Additional profile data |
| `created_at` | timestamp with time zone | NOT NULL | |
| `updated_at` | timestamp with time zone | NOT NULL | |

---

## Table: `auth_users_roles`

**Production DB Columns** (9 total):

| Column | PostgreSQL Type | Nullable | Notes |
|--------|-----------------|----------|-------|
| `id` | uuid | NOT NULL | PK |
| `user_id` | uuid | NOT NULL | FK → auth.users |
| `yacht_id` | uuid | NOT NULL | FK → yacht_registry |
| `role` | text | NOT NULL | Role name (see hierarchy below) |
| `is_active` | boolean | NOT NULL | |
| `assigned_by` | uuid | YES | Who assigned role |
| `assigned_at` | timestamp with time zone | NOT NULL | |
| `valid_from` | timestamp with time zone | NOT NULL | |
| `valid_until` | timestamp with time zone | YES | NULL = no expiry |

**Role Hierarchy for Fault Lens**:
```
TIER 1 (All Crew):
  - deckhand, steward, chef, etc.
  - Can: view faults, add condition notes, attach photos

TIER 2 (Engineers + Operators):
  - engineer, eto, deck_officer, chief_officer
  - Can: TIER 1 + (indirectly via WO) update fault status

TIER 3 (HoD + Captain):
  - captain, chief_engineer, chief_steward, purser
  - Can: TIER 2 + nothing extra (faults never deleted)
```

---

# PART 2: MICRO-ACTIONS WITH FIELD CLASSIFICATION

> **ACTION ACTIVATION DOCTRINE**: Actions are NOT visible on search results lists. When a single entity becomes the **focused entity** (user clicks a result), its context actions become available. No "actions dropdown appears magically." No buttons on result cards. User focuses one entity → context menu available.

## Action 1: `add_fault_note`

> **🚫 BLOCKED (B1)**: `pms_notes` RLS policies not deployed. Action disabled in UI until resolved.

**Purpose**: Add condition/historical note to fault record

**Tables Written**:
- `pms_notes` (INSERT)
- `pms_audit_log` (INSERT)

**Field Classification**:

| Field | Table.Column | Classification | Source |
|-------|--------------|----------------|--------|
| `id` | pms_notes.id | BACKEND_AUTO | gen_random_uuid() |
| `yacht_id` | pms_notes.yacht_id | BACKEND_AUTO | public.get_user_yacht_id() |
| `fault_id` | pms_notes.fault_id | CONTEXT | From current fault being viewed |
| `text` | pms_notes.text | REQUIRED | User input |
| `note_type` | pms_notes.note_type | OPTIONAL | User dropdown, default: 'observation' |
| `attachments` | pms_notes.attachments | OPTIONAL | Inline refs if user adds files |
| `metadata` | pms_notes.metadata | BACKEND_AUTO | Session context |
| `created_by` | pms_notes.created_by | BACKEND_AUTO | auth.uid() |
| `created_at` | pms_notes.created_at | BACKEND_AUTO | NOW() |
| `updated_at` | pms_notes.updated_at | BACKEND_AUTO | NOW() |

**Real SQL**:
```sql
-- 1. Insert note
INSERT INTO pms_notes (
    id,
    yacht_id,
    fault_id,
    text,
    note_type,
    attachments,
    metadata,
    created_by,
    created_at,
    updated_at
) VALUES (
    gen_random_uuid(),
    public.get_user_yacht_id(),           -- BACKEND_AUTO
    :fault_id,                       -- CONTEXT (from URL/state)
    :text,                           -- REQUIRED (user input)
    COALESCE(:note_type, 'observation'),  -- OPTIONAL (default)
    COALESCE(:attachments, '[]'::jsonb),  -- OPTIONAL
    jsonb_build_object(
        'session_id', :session_id,
        'ip_address', :ip_address,
        'device_type', :device_type,
        'source', 'fault_lens'
    ),                               -- BACKEND_AUTO
    auth.uid(),                      -- BACKEND_AUTO
    NOW(),                           -- BACKEND_AUTO
    NOW()                            -- BACKEND_AUTO
)
RETURNING id;

-- 2. Insert audit log
INSERT INTO pms_audit_log (
    id,
    yacht_id,
    entity_type,
    entity_id,
    action,
    user_id,
    old_values,
    new_values,
    signature,
    metadata,
    created_at
) VALUES (
    gen_random_uuid(),
    public.get_user_yacht_id(),
    'note',
    :new_note_id,                    -- From RETURNING above
    'add_fault_note',
    auth.uid(),
    NULL,                            -- No old values for INSERT
    jsonb_build_object(
        'fault_id', :fault_id,
        'text', :text,
        'note_type', :note_type
    ),
    '{}'::jsonb,                     -- Empty object for non-signature actions (NOT NULL constraint)
    jsonb_build_object(
        'session_id', :session_id,
        'ip_address', :ip_address,
        'device_type', :device_type
    ),
    NOW()
);
```

**Ledger UI Event** (derived from `pms_audit_log` + user profile joins, NOT a table write):
```json
{
  "event": "fault_note_added",
  "message": "Condition note added to FLT-2026-001234",
  "entity_type": "fault",
  "entity_id": "fault_uuid",
  "user_id": "user_uuid",
  "user_name": "John Smith",
  "timestamp": "2026-01-24T14:30:00Z",
  "link": "/faults/fault_uuid"
}
```

**RLS Policy Check**:
```sql
-- All crew can add notes (TIER 1+)
CREATE POLICY "crew_can_add_notes" ON pms_notes
    FOR INSERT
    WITH CHECK (
        yacht_id = public.get_user_yacht_id()
        AND fault_id IS NOT NULL
    );
```

---

## Action 2: `attach_file_to_fault`

> **⚠️ BLOCKED (B3)**: `storage.objects` INSERT policy for `pms-discrepancy-photos` not proven. If policy missing → action disabled in UI (greyed) even if DB insert would pass.

**Purpose**: Upload condition photo/document to fault record

**Tables Written**:
- `pms_attachments` (INSERT)
- `pms_audit_log` (INSERT)

**Storage Bucket**: `pms-discrepancy-photos`

**Field Classification**:

| Field | Table.Column | Classification | Source |
|-------|--------------|----------------|--------|
| `id` | pms_attachments.id | BACKEND_AUTO | gen_random_uuid() |
| `yacht_id` | pms_attachments.yacht_id | BACKEND_AUTO | public.get_user_yacht_id() |
| `entity_type` | pms_attachments.entity_type | BACKEND_AUTO | 'fault' |
| `entity_id` | pms_attachments.entity_id | CONTEXT | From current fault |
| `file` | (upload) | REQUIRED | User file selection/camera |
| `filename` | pms_attachments.filename | BACKEND_AUTO | Generated UUID + extension |
| `original_filename` | pms_attachments.original_filename | BACKEND_AUTO | From file metadata |
| `mime_type` | pms_attachments.mime_type | BACKEND_AUTO | Detected from file |
| `file_size` | pms_attachments.file_size | BACKEND_AUTO | From file metadata |
| `storage_path` | pms_attachments.storage_path | BACKEND_AUTO | bucket/yacht_id/fault_id/filename |
| `width` | pms_attachments.width | BACKEND_AUTO | For images, detected |
| `height` | pms_attachments.height | BACKEND_AUTO | For images, detected |
| `thumbnail_path` | pms_attachments.thumbnail_path | BACKEND_AUTO | Generated if image |
| `description` | pms_attachments.description | OPTIONAL | User input |
| `tags` | pms_attachments.tags | OPTIONAL | User input |
| `metadata` | pms_attachments.metadata | BACKEND_AUTO | Session context |
| `uploaded_by` | pms_attachments.uploaded_by | BACKEND_AUTO | auth.uid() |
| `uploaded_at` | pms_attachments.uploaded_at | BACKEND_AUTO | NOW() |
| `created_at` | pms_attachments.created_at | BACKEND_AUTO | NOW() |

**Real SQL** (after file upload to storage):
```sql
-- 1. Insert attachment record
INSERT INTO pms_attachments (
    id,
    yacht_id,
    entity_type,
    entity_id,
    filename,
    original_filename,
    mime_type,
    file_size,
    storage_path,
    width,
    height,
    thumbnail_path,
    description,
    tags,
    metadata,
    uploaded_by,
    uploaded_at,
    created_at
) VALUES (
    gen_random_uuid(),
    public.get_user_yacht_id(),           -- BACKEND_AUTO
    'fault',                         -- BACKEND_AUTO (hardcoded for fault lens)
    :fault_id,                       -- CONTEXT
    :generated_filename,             -- BACKEND_AUTO (uuid + ext)
    :original_filename,              -- BACKEND_AUTO (from upload)
    :detected_mime_type,             -- BACKEND_AUTO
    :file_size_bytes,                -- BACKEND_AUTO
    'pms-discrepancy-photos/' || public.get_user_yacht_id() || '/' || :fault_id || '/' || :generated_filename,
    :width,                          -- BACKEND_AUTO (null if not image)
    :height,                         -- BACKEND_AUTO (null if not image)
    :thumbnail_path,                 -- BACKEND_AUTO (null if not image)
    :description,                    -- OPTIONAL (user input)
    :tags,                           -- OPTIONAL (user input)
    jsonb_build_object(
        'session_id', :session_id,
        'ip_address', :ip_address,
        'device_type', :device_type,
        'source', 'fault_lens'
    ),
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
    'attachment',
    :new_attachment_id,
    'attach_file_to_fault',
    auth.uid(),
    NULL,
    jsonb_build_object(
        'fault_id', :fault_id,
        'filename', :original_filename,
        'mime_type', :detected_mime_type,
        'file_size', :file_size_bytes
    ),
    '{}'::jsonb,                     -- Empty object for non-signature actions (NOT NULL constraint)
    jsonb_build_object(
        'session_id', :session_id,
        'ip_address', :ip_address,
        'device_type', :device_type
    ),
    NOW()
);
```

**Storage RLS Check** (separate from DB table RLS):
```sql
-- This is storage.objects RLS, NOT pms_attachments table RLS
-- See PART 5 "Storage Bucket Policies" for full details
-- Upload requires BOTH:
--   1. pms_attachments INSERT RLS pass (yacht isolation)
--   2. storage.objects INSERT RLS pass (bucket policy)
```

---

## Action 3: `view_linked_work_order`

**Purpose**: Navigate to WO Lens (escape hatch)

**Tables Written**: None (read-only navigation)

**Tables Read**:
- `pms_faults` (get work_order_id)
- `pms_work_orders` (load WO details)

**Real SQL**:
```sql
-- Get linked WO from fault
SELECT
    f.work_order_id,
    wo.wo_number,
    wo.title,
    wo.status
FROM pms_faults f
LEFT JOIN pms_work_orders wo ON f.work_order_id = wo.id
WHERE f.id = :fault_id
  AND f.yacht_id = public.get_user_yacht_id();  -- RLS check

-- If work_order_id IS NULL, show message: "No work order linked to this fault"
-- If work_order_id IS NOT NULL, navigate to: /work-orders/{work_order_id}
```

**Audit Log**: None (read-only action)

**Ledger UI Event**: None (navigation only, no audit log entry)

---

# PART 3: FAULT CREATION FLOW (via Work Order)

Since faults are created automatically when WO type is breakdown/corrective:

## Trigger: On Work Order Create (type = breakdown/corrective)

**Tables Written**:
- `pms_work_orders` (INSERT)
- `pms_faults` (INSERT - auto-created)
- `pms_audit_log` (INSERT x2)

**Field Flow**:

| WO Field (User) | Fault Field (Auto) | Source |
|-----------------|-------------------|--------|
| title | title | Copied from WO |
| equipment_id | equipment_id | Copied from WO |
| type='breakdown' | (trigger condition) | |
| fault_severity | severity | **USER-PROVIDED** - direct dropdown, no mapping |
| - | status | BACKEND_AUTO: 'investigating' |
| - | work_order_id | BACKEND_AUTO: new WO id |
| - | detected_at | BACKEND_AUTO: NOW() |
| - | detected_by | BACKEND_AUTO: auth.uid() (needs migration) |

**Severity Rule (LOCKED)**:

When WO type is `breakdown`, `corrective`, or `unplanned`, the WO modal shows a **fault_severity dropdown** (low/medium/high/critical). User selects. Fault uses that exact value.

- NO mapping from WO priority
- NO system inference
- NO "smart urgency"

If user doesn't select, default is `medium`.

**Real SQL** (within transaction):
```sql
BEGIN;

-- 1. Insert Work Order
INSERT INTO pms_work_orders (
    id, yacht_id, equipment_id, fault_id,
    wo_number, title, description, type, priority, status,
    assigned_to, due_date, metadata, created_by, created_at, updated_at
) VALUES (
    gen_random_uuid(),
    public.get_user_yacht_id(),
    :equipment_id,                   -- CONTEXT (from focused equipment)
    NULL,                            -- Will update after fault created
    generate_wo_number(),            -- BACKEND_AUTO
    :title,                          -- REQUIRED (user input)
    :description,                    -- OPTIONAL
    :type,                           -- REQUIRED (user selected: 'breakdown')
    :priority,                       -- REQUIRED (user selected: 'critical')
    'planned',                       -- BACKEND_AUTO (default)
    :assigned_to,                    -- OPTIONAL
    :due_date,                       -- OPTIONAL
    jsonb_build_object(
        'source', 'equipment_lens'
    ),
    auth.uid(),
    NOW(),
    NOW()
)
RETURNING id INTO :new_wo_id;

-- 2. Auto-create Fault (only if type in breakdown/corrective/unplanned)
INSERT INTO pms_faults (
    id, yacht_id, equipment_id, fault_code,
    title, description, severity, status,
    work_order_id, detected_at, metadata, created_at, updated_at
) VALUES (
    gen_random_uuid(),
    public.get_user_yacht_id(),
    :equipment_id,                   -- Copied from WO
    generate_fault_code(),           -- ⚠️ B2: FUNCTION DOESN'T EXIST - use app-layer or create migration
    :title,                          -- Copied from WO
    :description,                    -- Copied from WO
    COALESCE(:fault_severity, 'medium')::fault_severity,  -- USER-PROVIDED from dropdown, default medium
    'investigating',                 -- BACKEND_AUTO (WO created = investigation started)
    :new_wo_id,                      -- Link to WO
    NOW(),                           -- BACKEND_AUTO
    jsonb_build_object('auto_created', true, 'source_wo', :new_wo_id),
    NOW(),
    NOW()
)
RETURNING id INTO :new_fault_id;

-- 3. Update WO with fault_id link
UPDATE pms_work_orders
SET fault_id = :new_fault_id
WHERE id = :new_wo_id;

-- 4. Audit log for WO creation
INSERT INTO pms_audit_log (...) VALUES (
    ..., 'create_work_order', :new_wo_id, ...
);

-- 5. Audit log for fault auto-creation
INSERT INTO pms_audit_log (
    id, yacht_id, entity_type, entity_id, action, user_id,
    old_values, new_values, signature, metadata, created_at
) VALUES (
    gen_random_uuid(),
    public.get_user_yacht_id(),
    'fault',
    :new_fault_id,
    'auto_create_fault',             -- Special action name for auto-creation
    auth.uid(),
    NULL,
    jsonb_build_object(
        'source_work_order_id', :new_wo_id,
        'title', :title,
        'fault_severity', COALESCE(:fault_severity, 'medium'),
        'auto_created', true
    ),
    '{}'::jsonb,                     -- Empty object (NOT NULL constraint)
    jsonb_build_object('session_id', :session_id, 'trigger', 'wo_create'),
    NOW()
);

COMMIT;
```

**Ledger UI Events** (derived from `pms_audit_log`, 2 events shown to user):
```json
[
  {
    "event": "work_order_created",
    "message": "WO-2026-0045 created for Generator #1",
    "entity_type": "work_order",
    "entity_id": "wo_uuid",
    "link": "/work-orders/wo_uuid"
  },
  {
    "event": "fault_auto_created",
    "message": "Fault FLT-2026-001234 logged for Generator #1",
    "entity_type": "fault",
    "entity_id": "fault_uuid",
    "link": "/faults/fault_uuid",
    "metadata": {
      "source": "work_order",
      "source_id": "wo_uuid"
    }
  }
]
```

---

# PART 4: FAULT STATUS CASCADE (Trigger)

## Trigger: On Work Order Status Change

**Source**: `CUMULATIVE_SCHEMA_MIGRATIONS.sql` Section 3.5.1

```sql
CREATE OR REPLACE FUNCTION cascade_wo_status_to_fault()
RETURNS TRIGGER AS $$
BEGIN
    -- Only act if WO has a linked fault and status changed
    IF NEW.fault_id IS NOT NULL AND OLD.status != NEW.status THEN

        -- WO in_progress → fault investigating
        IF NEW.status = 'in_progress' THEN
            UPDATE pms_faults
            SET status = 'investigating',
                updated_at = NOW(),
                updated_by = NEW.updated_by
            WHERE id = NEW.fault_id;

            -- Audit log
            INSERT INTO pms_audit_log (
                id, yacht_id, entity_type, entity_id, action, user_id,
                old_values, new_values, signature, metadata, created_at
            ) VALUES (
                gen_random_uuid(),
                NEW.yacht_id,
                'fault',
                NEW.fault_id,
                'fault_status_cascade',
                NEW.updated_by,
                jsonb_build_object('status', 'open'),
                jsonb_build_object('status', 'investigating', 'source_wo_status', 'in_progress'),
                '{}'::jsonb,             -- Empty object (NOT NULL constraint)
                jsonb_build_object('trigger', 'cascade_wo_status_to_fault'),
                NOW()
            );

        -- WO completed → fault resolved
        ELSIF NEW.status = 'completed' THEN
            UPDATE pms_faults
            SET status = 'resolved',
                resolved_at = NOW(),
                resolved_by = NEW.updated_by,
                updated_at = NOW(),
                updated_by = NEW.updated_by
            WHERE id = NEW.fault_id;

            -- Audit log
            INSERT INTO pms_audit_log (...);

        -- WO cancelled → fault back to open
        ELSIF NEW.status = 'cancelled' THEN
            UPDATE pms_faults
            SET status = 'open',
                resolved_at = NULL,
                resolved_by = NULL,
                updated_at = NOW(),
                updated_by = NEW.updated_by
            WHERE id = NEW.fault_id;

            -- Audit log
            INSERT INTO pms_audit_log (...);

        END IF;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_wo_status_cascade_to_fault
    AFTER UPDATE OF status ON pms_work_orders
    FOR EACH ROW
    EXECUTE FUNCTION cascade_wo_status_to_fault();
```

---

# PART 5: RLS POLICIES

> **IMPORTANT**: This section separates ACTUAL DEPLOYED policies (from migrations) vs PROPOSED policies (needed for full Lens functionality).

---

## Table: `pms_faults`

### ACTUAL DEPLOYED (from `20260116_000_create_pms_core_tables.sql`)

> **⚠️ LEGACY WARNING**: This policy references `public.user_profiles` (old table name). The canonical table is `auth_users_profiles`. Policy may need migration to use `public.get_user_yacht_id()` for consistency.

```sql
-- Source: supabase/migrations/20260116_000_create_pms_core_tables.sql:274
-- ⚠️ Uses legacy table name - verify still works after auth table renames
CREATE POLICY "Users can view their yacht faults"
    ON public.pms_faults FOR SELECT
    USING (yacht_id IN (
        SELECT yacht_id FROM public.user_profiles WHERE id = auth.uid()
    ));
```

**Current state**: SELECT only. No INSERT, UPDATE, or DELETE policies.

### PROPOSED (for Fault Lens)

```sql
-- INSERT: Not needed - faults auto-created via WO trigger
-- UPDATE: Not needed - status cascades from WO trigger
-- DELETE: NEVER - doctrine forbids fault deletion

-- No changes needed. Current SELECT-only policy is correct.
-- Fault mutations happen through pms_work_orders, not direct fault edits.
```

---

## Table: `pms_notes`

### ACTUAL DEPLOYED

```sql
-- Source: NO RLS POLICIES FOUND IN MIGRATIONS
-- ⚠️ GAP: pms_notes has RLS enabled but no policies deployed
```

### PROPOSED (for Fault Lens)

```sql
-- MIGRATION NEEDED: Section 1.x in CUMULATIVE_SCHEMA_MIGRATIONS.sql
-- Uses canonical public.get_user_yacht_id() - single source of truth

-- 1. All crew can view notes for their yacht
CREATE POLICY "crew_can_view_notes" ON pms_notes
    FOR SELECT
    TO authenticated
    USING (yacht_id = public.get_user_yacht_id());

-- 2. All crew can add notes
CREATE POLICY "crew_can_add_notes" ON pms_notes
    FOR INSERT
    TO authenticated
    WITH CHECK (yacht_id = public.get_user_yacht_id());

-- 3. Author can update their own notes (within 24h)
-- NOTE: 24h window is a PRODUCT RULE, not a DB fact
CREATE POLICY "author_can_update_own_notes" ON pms_notes
    FOR UPDATE
    TO authenticated
    USING (
        yacht_id = public.get_user_yacht_id()
        AND created_by = auth.uid()
        AND created_at > NOW() - INTERVAL '24 hours'  -- Product rule: edit window
    );
```

---

## Table: `pms_attachments`

### ACTUAL DEPLOYED (from `20260118_000_fix_rls_user_accounts_bug.sql`)

> **NOTE**: Deployed policies use OR pattern (JWT claim OR DB join). This is legacy. New policies should use canonical `public.get_user_yacht_id()`.

```sql
-- Source: supabase/migrations/20260118_000_fix_rls_user_accounts_bug.sql:125
-- ⚠️ Uses legacy OR pattern - works but not canonical

CREATE POLICY yacht_isolation_select ON pms_attachments
    FOR SELECT TO authenticated
    USING (
        yacht_id::text = (current_setting('request.jwt.claims', true)::json->>'yacht_id')
        OR yacht_id IN (SELECT yacht_id FROM auth_users_profiles WHERE id = auth.uid())
    );

CREATE POLICY yacht_isolation_insert ON pms_attachments
    FOR INSERT TO authenticated
    WITH CHECK (
        yacht_id::text = (current_setting('request.jwt.claims', true)::json->>'yacht_id')
        OR yacht_id IN (SELECT yacht_id FROM auth_users_profiles WHERE id = auth.uid())
    );

CREATE POLICY yacht_isolation_update ON pms_attachments
    FOR UPDATE TO authenticated
    USING (
        yacht_id::text = (current_setting('request.jwt.claims', true)::json->>'yacht_id')
        OR yacht_id IN (SELECT yacht_id FROM auth_users_profiles WHERE id = auth.uid())
    );

CREATE POLICY yacht_isolation_delete ON pms_attachments
    FOR DELETE TO authenticated
    USING (
        yacht_id::text = (current_setting('request.jwt.claims', true)::json->>'yacht_id')
        OR yacht_id IN (SELECT yacht_id FROM auth_users_profiles WHERE id = auth.uid())
    );
```

### PROPOSED (refinements for Fault Lens)

```sql
-- 1. DELETE too permissive - restrict to HoD+
-- 2. Migrate to canonical public.get_user_yacht_id()

-- MIGRATION NEEDED: Tighten delete policy + standardize isolation
DROP POLICY IF EXISTS yacht_isolation_delete ON pms_attachments;
CREATE POLICY yacht_isolation_delete ON pms_attachments
    FOR DELETE TO authenticated
    USING (
        yacht_id = public.get_user_yacht_id()  -- Canonical function
        AND EXISTS (
            SELECT 1 FROM auth_users_roles
            WHERE user_id = auth.uid()
            AND yacht_id = public.get_user_yacht_id()
            AND is_active = true
            AND role IN ('captain', 'chief_engineer', 'chief_steward', 'chief_officer', 'purser')
        )
    );
```

---

## Policy Gap Summary (DB Table RLS)

| Table | SELECT | INSERT | UPDATE | DELETE | Status |
|-------|--------|--------|--------|--------|--------|
| `pms_faults` | ✅ Deployed | ❌ N/A | ❌ N/A | ❌ Forbidden | ✅ Complete |
| `pms_notes` | ❌ Missing | ❌ Missing | ❌ Missing | ❌ N/A | ⚠️ MIGRATION NEEDED |
| `pms_attachments` | ✅ Deployed | ✅ Deployed | ✅ Deployed | ⚠️ Too permissive | ⚠️ Refinement suggested |

---

## Storage Bucket Policies (Supabase Storage RLS)

> **IMPORTANT**: Storage RLS (`storage.objects`) is SEPARATE from DB table RLS (`pms_attachments`). A successful DB INSERT does NOT guarantee upload success.

### Bucket Mapping

| Bucket | Entity Types | Read | Write | Delete |
|--------|--------------|------|-------|--------|
| `pms-discrepancy-photos` | fault, work_order | All crew | All crew | HoD+ only |
| `pms-receiving-images` | receiving_event | All crew | All crew | HoD+ only |
| `documents` | manual, certificate | All crew | **Read-only** | **Forbidden** |

### ACTUAL DEPLOYED (Storage RLS)

```sql
-- Source: supabase/migrations/00000000000014_08_add_storage_rls_policy.sql
-- Note: This is storage.objects RLS, NOT pms_attachments table RLS

CREATE POLICY "Users read yacht documents"
    ON storage.objects FOR SELECT
    TO authenticated
    USING (bucket_id = 'documents');

-- ⚠️ GAP: No explicit write policies found for pms-discrepancy-photos
-- Current behavior: Supabase defaults may allow authenticated uploads
```

### PROPOSED (Storage RLS for Fault Lens)

```sql
-- pms-discrepancy-photos bucket
CREATE POLICY "crew_can_read_discrepancy_photos"
    ON storage.objects FOR SELECT
    TO authenticated
    USING (bucket_id = 'pms-discrepancy-photos');

CREATE POLICY "crew_can_upload_discrepancy_photos"
    ON storage.objects FOR INSERT
    TO authenticated
    WITH CHECK (
        bucket_id = 'pms-discrepancy-photos'
        AND auth.role() = 'authenticated'
    );

-- Only HoD+ can delete from storage
CREATE POLICY "hod_can_delete_discrepancy_photos"
    ON storage.objects FOR DELETE
    TO authenticated
    USING (
        bucket_id = 'pms-discrepancy-photos'
        AND EXISTS (
            SELECT 1 FROM auth_users_roles
            WHERE user_id = auth.uid()
            AND is_active = true
            AND role IN ('captain', 'chief_engineer', 'chief_steward', 'chief_officer', 'purser')
        )
    );

-- documents bucket: read-only for all
CREATE POLICY "documents_read_only"
    ON storage.objects FOR SELECT
    TO authenticated
    USING (bucket_id = 'documents');
-- No INSERT/UPDATE/DELETE policies for documents bucket
```

### Upload Flow Validation

For `attach_file_to_fault` action to succeed:
1. ✅ User must pass `pms_attachments` INSERT RLS (yacht isolation)
2. ✅ User must pass `storage.objects` INSERT RLS (bucket policy)
3. ✅ File must be uploaded to correct bucket path

If either RLS fails, the action fails. Frontend must handle both error cases.

---

# PART 6: FAULT HISTORY QUERY

## SQL for "fault history {equipment}" Query

```sql
-- Scenario 3: User queries "fault history hydraulic pump"
-- This is a READ operation - no mutations

SELECT
    f.id AS fault_id,
    f.fault_code,
    f.title,
    f.description,
    f.severity,
    f.status,
    f.detected_at,
    f.resolved_at,

    -- Who reported (needs detected_by migration, fallback to audit log)
    COALESCE(
        f.detected_by,
        (SELECT user_id FROM pms_audit_log
         WHERE entity_type = 'fault' AND entity_id = f.id
         ORDER BY created_at ASC LIMIT 1)
    ) AS detected_by,

    -- Reporter name
    (SELECT name FROM auth_users_profiles
     WHERE id = COALESCE(
         f.detected_by,
         (SELECT user_id FROM pms_audit_log
          WHERE entity_type = 'fault' AND entity_id = f.id
          ORDER BY created_at ASC LIMIT 1)
     )) AS detected_by_name,

    -- Resolver name
    (SELECT name FROM auth_users_profiles WHERE id = f.resolved_by) AS resolved_by_name,

    -- Equipment info
    e.name AS equipment_name,
    e.code AS equipment_code,
    e.location AS equipment_location,

    -- Linked work order
    wo.id AS work_order_id,
    wo.wo_number,
    wo.status AS wo_status,
    wo.completed_at AS wo_completed_at,

    -- Condition notes (fault notes only)
    (
        SELECT json_agg(json_build_object(
            'id', n.id,
            'text', n.text,
            'note_type', n.note_type,
            'created_at', n.created_at,
            'created_by_name', (SELECT name FROM auth_users_profiles WHERE id = n.created_by)
        ) ORDER BY n.created_at DESC)
        FROM pms_notes n
        WHERE n.fault_id = f.id
    ) AS fault_notes,

    -- Attachments
    (
        SELECT json_agg(json_build_object(
            'id', a.id,
            'filename', a.original_filename,
            'mime_type', a.mime_type,
            'storage_path', a.storage_path,
            'thumbnail_path', a.thumbnail_path,
            'description', a.description,
            'uploaded_at', a.uploaded_at,
            'uploaded_by_name', (SELECT name FROM auth_users_profiles WHERE id = a.uploaded_by)
        ) ORDER BY a.uploaded_at DESC)
        FROM pms_attachments a
        WHERE a.entity_type = 'fault'
        AND a.entity_id = f.id
        AND a.deleted_at IS NULL
    ) AS fault_attachments

FROM pms_faults f
JOIN pms_equipment e ON f.equipment_id = e.id
LEFT JOIN pms_work_orders wo ON f.work_order_id = wo.id
WHERE f.equipment_id = :equipment_id
  AND f.yacht_id = public.get_user_yacht_id()  -- RLS
  -- NO deleted_at filter - show ALL history
ORDER BY f.detected_at DESC;
```

---

# PART 7: GAPS & MIGRATION STATUS

## Confirmed Gaps (from CUMULATIVE_SCHEMA_MIGRATIONS.sql)

| Gap | Table | Migration | Status |
|-----|-------|-----------|--------|
| `detected_by` column | pms_faults | Section 1.1 | Ready to run |
| Fault history index | pms_faults | Section 1.9 | Ready to run |
| WO→Fault cascade trigger | pms_work_orders | Section 3.5.1 | Ready to run |

## What's Already Present

| Feature | Table | Column/Trigger | Verified |
|---------|-------|----------------|----------|
| Soft delete | pms_faults | deleted_at, deleted_by, deletion_reason | ✅ (but DEPRECATED) |
| Severity enum | pms_faults | severity (public.fault_severity) | ✅ |
| Status check | pms_faults | status (TEXT) | ✅ Values need CHECK constraint |
| Signature storage | pms_audit_log | signature (JSONB) | ✅ |
| Generic notes | pms_notes | fault_id FK | ✅ |
| Generic attachments | pms_attachments | entity_type='fault' | ✅ |

## What's NOT Needed

| Proposed | Reason Not Needed |
|----------|-------------------|
| archive_fault action | Faults never deleted - doctrine |
| update_fault_status action | Status cascades from WO trigger |
| Critical fault index | No dashboards - query-only |

---

# PART 8: SUMMARY

## Fault Lens Actions (Final)

| Action | Tables Written | Signature | RLS Tier |
|--------|---------------|-----------|----------|
| `add_fault_note` | pms_notes, pms_audit_log | No | All Crew |
| `attach_file_to_fault` | pms_attachments, pms_audit_log | No | All Crew |
| `view_linked_work_order` | None (read) | No | All Crew |

## Fault Creation (via WO)

| Trigger | Tables Written | Automatic Fields |
|---------|---------------|------------------|
| WO type=breakdown | pms_faults | id, yacht_id, fault_code, status='investigating', detected_at, work_order_id |

## Fault Status (via Cascade)

| WO Status | Fault Status | Automatic Fields |
|-----------|--------------|------------------|
| in_progress | investigating | updated_at, updated_by |
| completed | resolved | resolved_at, resolved_by, updated_at, updated_by |
| cancelled | open | resolved_at=NULL, resolved_by=NULL |

## User Details Brought Forward

On every action:
- `auth.uid()` → user_id in audit log
- `public.get_user_yacht_id()` → yacht_id isolation
- Session context → metadata JSONB (ip, device, session_id)
- User name → via JOIN to auth_users_profiles

---

**STOP. This is v4 DB-GROUNDED. Awaiting review.**
