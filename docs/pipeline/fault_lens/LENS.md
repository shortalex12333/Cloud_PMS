# Entity Lens: Fault
**Version**: v1 FINAL
**Status**: PRODUCTION READY (after migrations deployed)
**Date**: 2026-01-27
**Gold Standard Reference**: `certificate_lens/LENS.md`

---

# EXECUTIVE SUMMARY

The Fault Lens governs all operations for equipment fault/defect tracking, diagnosis, and resolution. Faults are created when equipment breaks down or requires corrective action, and their lifecycle is primarily managed through linked Work Orders (WO-First Doctrine).

## Key Metrics
| Metric | Value |
|--------|-------|
| Primary Tables | 1 (pms_faults) |
| Supporting Tables | 3 (pms_notes, pms_attachments, pms_audit_log) |
| Actions Registered | 10 mutations + READ handlers |
| Scenarios Documented | 8 |
| Blockers | 3 (B1: fault RLS, B2: notes RLS, B3: storage write) |
| Migrations Ready | 4 |

---

# BLOCKERS

| ID | Description | Severity | Status | Resolution |
|----|-------------|----------|--------|------------|
| **B1** | `pms_faults` has SELECT-only RLS (no INSERT/UPDATE) | CRITICAL | Migration Ready | Deploy 20260127_001 |
| **B2** | `pms_notes` missing INSERT/UPDATE policies | MEDIUM | Migration Ready | Deploy 20260127_002 |
| **B3** | Storage bucket `pms-discrepancy-photos` missing write policies | MEDIUM | Migration Ready | Deploy 20260127_003 |

**Note**: All fault MUTATE actions are degraded until B1 resolved. Service role bypasses RLS automatically.

---

# PART 0: CANONICAL HELPERS

## Yacht ID Resolution
```sql
public.get_user_yacht_id()
-- Returns UUID of current user's yacht
-- SECURITY DEFINER, STABLE
```

## Role Check (Canonical Helpers)
```sql
-- PREFERRED for write operations:
public.is_hod(auth.uid(), public.get_user_yacht_id())
-- Returns BOOLEAN: true if user has HOD role (captain, chief_engineer, chief_officer, purser, manager)

public.is_manager()
-- Returns BOOLEAN: true if user has manager role (for DELETE operations)

-- Engineer check (for fault-specific operations):
public.is_engineer()
-- Returns BOOLEAN: true if user has engineer/eto role
```

**Best Practice**: Use `is_hod()` and `is_engineer()` in RLS policies. Boolean helpers are clearer than string comparisons.

## Audit Entity Type
```sql
entity_type = 'fault'
```

## Signature Invariant
```sql
-- Non-signature action:
signature = '{}'::jsonb

-- Signed action (create_work_order_from_fault):
signature = :signature_payload::jsonb
```
**NEVER** NULL. See APPENDIX: SIGNATURE PAYLOAD SCHEMA for exact structure.

---

# PART 1: DATABASE SCHEMA

## Table: `pms_faults` (19 columns)

| Column | Type | Nullable | Classification |
|--------|------|----------|----------------|
| `id` | uuid | NOT NULL | BACKEND_AUTO |
| `yacht_id` | uuid | NOT NULL | BACKEND_AUTO |
| `equipment_id` | uuid | NOT NULL | REQUIRED |
| `fault_code` | text | YES | BACKEND_AUTO |
| `title` | text | NOT NULL | REQUIRED |
| `description` | text | YES | OPTIONAL |
| `severity` | public.fault_severity | NOT NULL | REQUIRED |
| `status` | text | YES | BACKEND_AUTO |
| `detected_at` | timestamptz | NOT NULL | BACKEND_AUTO |
| `resolved_at` | timestamptz | YES | BACKEND_AUTO |
| `resolved_by` | uuid | YES | BACKEND_AUTO |
| `work_order_id` | uuid | YES | BACKEND_AUTO |
| `metadata` | jsonb | YES | BACKEND_AUTO |
| `created_at` | timestamptz | NOT NULL | BACKEND_AUTO |
| `updated_at` | timestamptz | YES | BACKEND_AUTO |
| `updated_by` | uuid | YES | BACKEND_AUTO |
| `deleted_at` | timestamptz | YES | **DEPRECATED** |
| `deleted_by` | uuid | YES | **DEPRECATED** |
| `deletion_reason` | text | YES | **DEPRECATED** |

**DELETION DOCTRINE**: Faults are NEVER deleted. `deleted_*` columns exist for legacy reasons. Do NOT write to them. History is preserved for recurrence analysis.

**EQUIPMENT CONSTRAINT**: `equipment_id` is **NOT NULL**. Every fault MUST be attached to equipment.

## Severity Enum: `public.fault_severity`
```sql
-- Values: cosmetic, minor, major, critical, safety
-- Default: 'minor'
```

## Status Values (TEXT, not enum)
```sql
-- Values: open, investigating, work_ordered, resolved, closed, false_alarm
-- Default: 'open'
```

## Table: `pms_notes` (12 columns)

| Column | Type | Nullable | Classification |
|--------|------|----------|----------------|
| `id` | uuid | NOT NULL | BACKEND_AUTO |
| `yacht_id` | uuid | NOT NULL | BACKEND_AUTO |
| `fault_id` | uuid | YES | CONTEXT |
| `equipment_id` | uuid | YES | CONTEXT |
| `work_order_id` | uuid | YES | CONTEXT |
| `text` | text | NOT NULL | REQUIRED |
| `note_type` | public.note_type | NOT NULL | OPTIONAL |
| `attachments` | jsonb | YES | OPTIONAL |
| `metadata` | jsonb | YES | BACKEND_AUTO |
| `created_by` | uuid | NOT NULL | BACKEND_AUTO |
| `created_at` | timestamptz | NOT NULL | BACKEND_AUTO |
| `updated_at` | timestamptz | NOT NULL | BACKEND_AUTO |

**Note**: Only ONE of `fault_id`, `equipment_id`, `work_order_id` should be populated per row.

## Table: `pms_attachments` (22 columns)

| Column | Type | Nullable | Classification |
|--------|------|----------|----------------|
| `id` | uuid | NOT NULL | BACKEND_AUTO |
| `yacht_id` | uuid | NOT NULL | BACKEND_AUTO |
| `entity_type` | varchar | NOT NULL | BACKEND_AUTO |
| `entity_id` | uuid | NOT NULL | CONTEXT |
| `filename` | varchar | NOT NULL | BACKEND_AUTO |
| `original_filename` | varchar | YES | BACKEND_AUTO |
| `mime_type` | varchar | NOT NULL | BACKEND_AUTO |
| `file_size` | integer | YES | BACKEND_AUTO |
| `storage_path` | text | NOT NULL | BACKEND_AUTO |
| `width` | integer | YES | BACKEND_AUTO |
| `height` | integer | YES | BACKEND_AUTO |
| `thumbnail_path` | text | YES | BACKEND_AUTO |
| `description` | text | YES | OPTIONAL |
| `tags` | text[] | YES | OPTIONAL |
| `metadata` | jsonb | YES | BACKEND_AUTO |
| `uploaded_by` | uuid | NOT NULL | BACKEND_AUTO |
| `uploaded_at` | timestamptz | NOT NULL | BACKEND_AUTO |
| `created_at` | timestamptz | NOT NULL | BACKEND_AUTO |
| `updated_at` | timestamptz | YES | BACKEND_AUTO |
| `deleted_at` | timestamptz | YES | BACKEND_AUTO |
| `deleted_by` | uuid | YES | BACKEND_AUTO |
| `deletion_reason` | text | YES | OPTIONAL |

**Storage Bucket**: `pms-discrepancy-photos`
**Path Template**: `{yacht_id}/faults/{fault_id}/{filename}`

---

# PART 2: MICRO-ACTIONS

## Action Summary

| # | Action | Tables Written | Signature | Status |
|---|--------|---------------|-----------|--------|
| 1 | `report_fault` | pms_faults, pms_audit_log | NO | B1 |
| 2 | `acknowledge_fault` | pms_faults, pms_audit_log | NO | B1 |
| 3 | `close_fault` | pms_faults, pms_audit_log | NO | B1 |
| 4 | `update_fault` | pms_faults, pms_audit_log | NO | B1 |
| 5 | `reopen_fault` | pms_faults, pms_audit_log | NO | B1 |
| 6 | `mark_fault_false_alarm` | pms_faults, pms_audit_log | NO | B1 |
| 7 | `add_fault_note` | pms_notes, pms_audit_log | NO | B2 |
| 8 | `add_fault_photo` | pms_attachments, pms_audit_log | NO | B3 |
| 9 | `create_work_order_from_fault` | pms_work_orders, pms_faults, pms_audit_log | **YES** | B1 |
| 10 | `view_fault_detail` | None (read) | NO | READY |

## Role Permissions

| Role | View | Report | Acknowledge | Close | Add Note | Add Photo | Create WO |
|------|------|--------|-------------|-------|----------|-----------|-----------|
| Crew (deckhand, steward, etc.) | Y | Y | N | N | Y | Y | N |
| ETO | Y | Y | Y | Y | Y | Y | N |
| Engineer | Y | Y | Y | Y | Y | Y | N |
| Chief Officer | Y | Y | Y | Y | Y | Y | N |
| Chief Engineer | Y | Y | Y | Y | Y | Y | Y (signed) |
| Captain | Y | Y | Y | Y | Y | Y | Y (signed) |
| Manager | Y | Y | Y | Y | Y | Y | Y (signed) |

---

# PART 2B: ACTION ROUTER REGISTRATION

All fault mutations are executed via the Action Router at `/v1/actions/execute`.

## Registered Actions

| Action ID | Endpoint | Handler | Allowed Roles | Required Fields |
|-----------|----------|---------|---------------|-----------------|
| `report_fault` | `/v1/faults/create` | INTERNAL | crew, eto, engineer, hod, manager | yacht_id, equipment_id, description |
| `acknowledge_fault` | `/v1/faults/acknowledge` | INTERNAL | eto, engineer, hod, manager | yacht_id, fault_id |
| `close_fault` | `/v1/faults/close` | INTERNAL | engineer, hod, manager | yacht_id, fault_id |
| `update_fault` | `/v1/faults/update` | INTERNAL | eto, engineer, hod, manager | yacht_id, fault_id |
| `reopen_fault` | `/v1/faults/reopen` | INTERNAL | eto, engineer, hod, manager | yacht_id, fault_id |
| `mark_fault_false_alarm` | `/v1/faults/mark-false-alarm` | INTERNAL | engineer, hod, manager | yacht_id, fault_id |
| `add_fault_note` | `/v1/faults/add-note` | INTERNAL | crew, eto, engineer, hod, manager | yacht_id, fault_id, text |
| `add_fault_photo` | `/v1/faults/add-photo` | INTERNAL | crew, eto, engineer, hod, manager | yacht_id, fault_id, photo_url |
| `create_work_order_from_fault` | `/v1/work-orders/create-from-fault` | INTERNAL | captain, chief_engineer, manager | yacht_id, fault_id, **signature** |
| `view_fault_detail` | `/v1/faults/view` | INTERNAL | all | yacht_id, fault_id |

## Request Contract

```json
{
  "action": "report_fault",
  "context": {
    "yacht_id": "uuid"
  },
  "payload": {
    "equipment_id": "uuid",
    "title": "Engine overheating warning",
    "description": "Port engine showing high temp alarm",
    "severity": "major"
  }
}
```

## Role Mapping (Registry -> RLS)

| Registry Role | RLS Function | DB Roles |
|---------------|--------------|----------|
| crew | authenticated | deckhand, steward, chef |
| engineer | is_engineer() | engineer, eto |
| HOD | is_hod() | chief_engineer, captain, manager |
| Manager | is_manager() | manager |

## Action Gating

| Action | Gating Class | Notes |
|--------|--------------|-------|
| `report_fault` | STATE_CHANGING | All crew can report |
| `acknowledge_fault` | STATE_CHANGING | Engineer+ only |
| `close_fault` | STATE_CHANGING | Engineer+ only |
| `create_work_order_from_fault` | **GATED** | Requires confirmation + signature |

---

# PART 3: KEY SQL PATTERNS

## Report Fault
```sql
INSERT INTO pms_faults (
    id, yacht_id, equipment_id, fault_code,
    title, description, severity, status,
    detected_at, metadata, created_at, updated_at
) VALUES (
    gen_random_uuid(),
    public.get_user_yacht_id(),
    :equipment_id,
    'FLT-' || to_char(NOW(), 'YYYY') || '-' || LPAD((
        SELECT COALESCE(MAX(CAST(SUBSTRING(fault_code FROM 10) AS INTEGER)), 0) + 1
        FROM pms_faults WHERE yacht_id = public.get_user_yacht_id()
    )::text, 6, '0'),
    :title,
    :description,
    COALESCE(:severity, 'minor')::fault_severity,
    'open',
    NOW(),
    jsonb_build_object('source', 'fault_lens', 'reported_by', auth.uid()),
    NOW(),
    NOW()
)
RETURNING id;

-- Audit log (non-signature)
INSERT INTO pms_audit_log (
    id, yacht_id, entity_type, entity_id, action, user_id,
    old_values, new_values, signature, metadata, created_at
) VALUES (
    gen_random_uuid(),
    public.get_user_yacht_id(),
    'fault',
    :new_id,
    'report_fault',
    auth.uid(),
    NULL,
    jsonb_build_object('equipment_id', :equipment_id, 'title', :title, 'severity', :severity),
    '{}'::jsonb,
    jsonb_build_object('source', 'fault_lens'),
    NOW()
);
```

## Close Fault
```sql
UPDATE pms_faults
SET
    status = 'closed',
    resolved_at = NOW(),
    resolved_by = auth.uid(),
    updated_at = NOW(),
    updated_by = auth.uid()
WHERE id = :fault_id
  AND yacht_id = public.get_user_yacht_id()
  AND status IN ('open', 'investigating', 'resolved');  -- Cannot close already closed

-- Audit log
INSERT INTO pms_audit_log (..., action, ...) VALUES (..., 'close_fault', ...);
```

## Create Work Order from Fault (SIGNED)
```sql
BEGIN;

-- 1. Create Work Order
INSERT INTO pms_work_orders (
    id, yacht_id, equipment_id, fault_id,
    wo_number, title, description, type, priority, status,
    created_by, created_at, updated_at
) VALUES (
    gen_random_uuid(),
    public.get_user_yacht_id(),
    (SELECT equipment_id FROM pms_faults WHERE id = :fault_id),
    :fault_id,
    'WO-' || to_char(NOW(), 'YYYY') || '-' || LPAD(...),
    (SELECT title FROM pms_faults WHERE id = :fault_id),
    (SELECT description FROM pms_faults WHERE id = :fault_id),
    'corrective',
    :priority,
    'planned',
    auth.uid(),
    NOW(),
    NOW()
)
RETURNING id INTO :new_wo_id;

-- 2. Update Fault with work_order_id
UPDATE pms_faults
SET
    work_order_id = :new_wo_id,
    status = 'work_ordered',
    updated_at = NOW(),
    updated_by = auth.uid()
WHERE id = :fault_id;

-- 3. Audit log (SIGNED)
INSERT INTO pms_audit_log (..., signature, ...) VALUES (..., :signature_payload::jsonb, ...);

COMMIT;
```

## Fault History Query
```sql
SELECT
    f.id AS fault_id,
    f.fault_code,
    f.title,
    f.description,
    f.severity,
    f.status,
    f.detected_at,
    f.resolved_at,

    -- Equipment info
    e.name AS equipment_name,
    e.code AS equipment_code,

    -- Linked work order
    wo.id AS work_order_id,
    wo.wo_number,
    wo.status AS wo_status,

    -- Notes count
    (SELECT COUNT(*) FROM pms_notes WHERE fault_id = f.id) AS note_count,

    -- Attachments count
    (SELECT COUNT(*) FROM pms_attachments WHERE entity_type = 'fault' AND entity_id = f.id AND deleted_at IS NULL) AS attachment_count

FROM pms_faults f
JOIN pms_equipment e ON f.equipment_id = e.id
LEFT JOIN pms_work_orders wo ON f.work_order_id = wo.id
WHERE f.equipment_id = :equipment_id
  AND f.yacht_id = public.get_user_yacht_id()
ORDER BY f.detected_at DESC;
```

---

# PART 4: RLS POLICIES

## pms_faults (PROPOSED - Migration 001)

```sql
-- SELECT: All crew (yacht scope) - ALREADY EXISTS but needs update
DROP POLICY IF EXISTS "Users can view their yacht faults" ON pms_faults;
CREATE POLICY "crew_select_own_yacht_faults"
ON pms_faults FOR SELECT TO authenticated
USING (yacht_id = public.get_user_yacht_id());

-- INSERT: All crew can report faults
CREATE POLICY "crew_insert_faults"
ON pms_faults FOR INSERT TO authenticated
WITH CHECK (yacht_id = public.get_user_yacht_id());

-- UPDATE: Engineer+ only (eto, engineer, chief_engineer, captain, manager)
CREATE POLICY "engineer_update_faults"
ON pms_faults FOR UPDATE TO authenticated
USING (yacht_id = public.get_user_yacht_id())
WITH CHECK (
    yacht_id = public.get_user_yacht_id()
    AND (is_hod(auth.uid(), public.get_user_yacht_id()) OR is_engineer())
);

-- DELETE: NEVER (doctrine forbids fault deletion)
-- No DELETE policy created
```

**Note**: Service role bypasses RLS automatically; no explicit policy needed.

## pms_notes (Migration 002)
```sql
-- SELECT: All crew
CREATE POLICY "crew_select_notes"
ON pms_notes FOR SELECT TO authenticated
USING (yacht_id = public.get_user_yacht_id());

-- INSERT: All crew can add notes
CREATE POLICY "crew_insert_notes"
ON pms_notes FOR INSERT TO authenticated
WITH CHECK (yacht_id = public.get_user_yacht_id());

-- UPDATE: Author only (within 24h)
CREATE POLICY "author_update_notes"
ON pms_notes FOR UPDATE TO authenticated
USING (
    yacht_id = public.get_user_yacht_id()
    AND created_by = auth.uid()
    AND created_at > NOW() - INTERVAL '24 hours'
);

-- DELETE: Manager only
CREATE POLICY "manager_delete_notes"
ON pms_notes FOR DELETE TO authenticated
USING (
    yacht_id = public.get_user_yacht_id()
    AND is_manager()
);
```

## Storage: pms-discrepancy-photos (Migration 003)
```sql
-- INSERT: All crew can upload photos
CREATE POLICY "crew_upload_discrepancy_photos"
ON storage.objects FOR INSERT TO authenticated
WITH CHECK (
    bucket_id = 'pms-discrepancy-photos'
    AND (storage.foldername(name))[1] = public.get_user_yacht_id()::text
);

-- SELECT: All crew can view
CREATE POLICY "crew_read_discrepancy_photos"
ON storage.objects FOR SELECT TO authenticated
USING (
    bucket_id = 'pms-discrepancy-photos'
    AND (storage.foldername(name))[1] = public.get_user_yacht_id()::text
);

-- DELETE: HOD+ only
CREATE POLICY "hod_delete_discrepancy_photos"
ON storage.objects FOR DELETE TO authenticated
USING (
    bucket_id = 'pms-discrepancy-photos'
    AND (storage.foldername(name))[1] = public.get_user_yacht_id()::text
    AND is_hod(auth.uid(), public.get_user_yacht_id())
);
```

---

# PART 5: SCENARIOS & CUSTOMER JOURNEYS

## Scenario Matrix

| # | Scenario | Actor | Query | Outcome |
|---|----------|-------|-------|---------|
| 1 | Report Engine Fault | Deckhand | "report fault engine overheating" | Fault created, HOD notified |
| 2 | View Fault History | Any | "fault history main engine" | Timeline displayed |
| 3 | Add Diagnostic Note | ETO | "add note to fault FLT-2026-001" | Note linked to fault |
| 4 | Upload Fault Photo | Bosun | "attach photo to fault" | Photo in storage, linked |
| 5 | Create WO from Fault | Chief Eng | "create work order from fault" | WO created (SIGNED) |
| 6 | Close Resolved Fault | Engineer | "close fault FLT-2026-001" | Status → closed |
| 7 | View Open Faults | Captain | "show all open faults" | List with counts |
| 8 | Equipment Recurrence | Manager | "faults for hydraulic pump past 6 months" | Pattern analysis |

---

## Journey 1: Deckhand Reports Bilge Pump Grinding

**Actor**: Maria (Deckhand, role: `crew`)
**Context**: Morning rounds, engine room
**Query**: "bilge pump 2 sounds wrong grinding"

### Flow

```
STEP 1 - QUERY
┌────────────────────────────────────────────────────────┐
│ Maria: "bilge pump 2 sounds wrong grinding"            │
│                                                        │
│ Celeste parses:                                        │
│   - Equipment: Bilge Pump #2 (fuzzy match)             │
│   - Intent: Reporting issue                            │
│   - Urgency: Mechanical noise                          │
└────────────────────────────────────────────────────────┘
           │
           ▼
STEP 2 - FOCUS
┌────────────────────────────────────────────────────────┐
│ 🔧 Bilge Pump #2                                       │
│    Location: Engine Room Port                          │
│    Status: Operational                                 │
│                                                        │
│ Suggested Actions (for CREW role):                     │
│ ┌────────────────────────────────────────────────────┐ │
│ │ ▶ Report Fault                                     │ │
│ │ ▶ View Maintenance History                         │ │
│ │ ▶ Add Note                                         │ │
│ └────────────────────────────────────────────────────┘ │
│                                                        │
│ ⚠️ NOT shown (role gated):                             │
│    Close Fault, Create Work Order, Acknowledge         │
└────────────────────────────────────────────────────────┘
           │
           ▼
STEP 3 - ACT
┌────────────────────────────────────────────────────────┐
│ Maria taps "Report Fault"                              │
│                                                        │
│ Form auto-filled:                                      │
│   Equipment: Bilge Pump #2 ✓                           │
│   Title: [Grinding noise during operation        ]     │
│   Severity: ○ Minor  ● Moderate  ○ Major               │
│   Description: [Started this morning. Gets louder  ]   │
│                [when pump activates.               ]   │
│                                                        │
│ 📷 Add Photo (optional)                                │
│                                                        │
│         [Submit Report]                                │
└────────────────────────────────────────────────────────┘
           │
           ▼
STEP 4 - OUTCOME
┌────────────────────────────────────────────────────────┐
│ "Fault FLT-2026-0127 reported. Chief Engineer notified"│
│                                                        │
│ Backend execution:                                     │
│ 1. RLS check: crew_insert_faults ✓                     │
│ 2. INSERT pms_faults (status: 'open')                  │
│ 3. INSERT pms_audit_log (signature: '{}')              │
│ 4. Push notification to HOD                            │
└────────────────────────────────────────────────────────┘
```

### Success Criteria
- ✅ Fault created with auto-generated `fault_code`
- ✅ Equipment linked via `equipment_id`
- ✅ Reporter captured in `metadata.reported_by`
- ✅ Audit log entry with empty signature (non-SIGNED action)
- ✅ HOD receives notification

### Failure Scenarios

| Failure | HTTP | Cause | User Message |
|---------|------|-------|--------------|
| Missing equipment_id | 400 | equipment_id is NOT NULL | "Equipment is required" |
| Missing title | 400 | title is NOT NULL | "Fault title is required" |
| Invalid severity | 400 | Not in enum | "Invalid severity value" |
| Yacht isolation fail | 403 | RLS yacht_id mismatch | "Access denied" |
| DB connection | 500 | Supabase down | "Service unavailable" |

---

## Journey 2: ETO Investigates & Diagnoses

**Actor**: Carlos (ETO, role: `eto`, `is_engineer() = true`)
**Context**: Notification received
**Query**: (Deep link from notification)

### Flow

```
STEP 1 - NOTIFICATION
┌────────────────────────────────────────────────────────┐
│ Push: "New Fault: Bilge Pump #2 - Grinding noise"      │
│                                                        │
│ Carlos taps notification → deep link to fault          │
└────────────────────────────────────────────────────────┘
           │
           ▼
STEP 2 - FOCUS (Fault Detail)
┌────────────────────────────────────────────────────────┐
│ ⚠️ FLT-2026-0127                                       │
│ Bilge Pump #2 - Grinding noise                         │
│                                                        │
│ Reported: Maria (Deckhand) @ 06:46                     │
│ Severity: Moderate                                     │
│ Status: open                                           │
│                                                        │
│ Suggested Actions (for ENGINEER role):                 │
│ ┌────────────────────────────────────────────────────┐ │
│ │ ▶ Acknowledge Fault ← Carlos selects               │ │
│ │ ▶ Update Fault                                     │ │
│ │ ▶ Add Diagnostic Note                              │ │
│ │ ▶ Close Fault                                      │ │
│ └────────────────────────────────────────────────────┘ │
│                                                        │
│ ⚠️ NOT shown (HOD-only):                               │
│    Create Work Order                                   │
└────────────────────────────────────────────────────────┘
           │
           ▼
STEP 3 - ACT (Acknowledge)
┌────────────────────────────────────────────────────────┐
│ ACTION: acknowledge_fault                              │
│                                                        │
│ "This confirms you're aware of this fault report."     │
│                                                        │
│         [Acknowledge]                                  │
└────────────────────────────────────────────────────────┘
           │
           ▼
STEP 4 - OUTCOME
┌────────────────────────────────────────────────────────┐
│ "Fault acknowledged. Status updated to 'investigating'"│
│                                                        │
│ Backend:                                               │
│ 1. RLS check: engineer_update_faults ✓                 │
│ 2. UPDATE pms_faults SET status = 'investigating'      │
│ 3. INSERT pms_audit_log (action: acknowledge_fault)    │
└────────────────────────────────────────────────────────┘
```

### Carlos Adds Diagnostic Note

```
STEP 5 - QUERY
"add note bearing failure likely"

STEP 6 - ACT
┌────────────────────────────────────────────────────────┐
│ Add Note to FLT-2026-0127                              │
│                                                        │
│ ┌────────────────────────────────────────────────────┐ │
│ │ Bearing failure likely. Sound matches worn         │ │
│ │ impeller bearing. Need to pull pump for inspection.│ │
│ └────────────────────────────────────────────────────┘ │
│                                                        │
│         [Add Note]                                     │
└────────────────────────────────────────────────────────┘

STEP 7 - OUTCOME
"Note added to FLT-2026-0127."

Backend:
1. RLS check: crew_insert_notes ✓ (all crew can add)
2. INSERT pms_notes (fault_id, text, created_by)
3. INSERT pms_audit_log (action: add_fault_note)
```

---

## Journey 3: Chief Engineer Creates Work Order (SIGNED)

**Actor**: Robert (Chief Engineer, role: `chief_engineer`, `is_hod() = true`)
**Context**: Morning review of faults
**Query**: "create work order from this fault"

### Flow

```
STEP 1 - QUERY
"create work order from this fault"

Celeste detects:
  - "this fault" = FLT-2026-0127 (context)
  - Intent: SIGNED action (create_work_order_from_fault)
  - Required: HOD role ✓

STEP 2 - ACT (SIGNATURE REQUIRED)
┌────────────────────────────────────────────────────────┐
│ Create Work Order from Fault                           │
│                                                        │
│ Fault: FLT-2026-0127 - Bilge Pump #2                   │
│                                                        │
│ Work Order Details:                                    │
│   Title: [Bilge Pump #2 Bearing Replacement      ]     │
│   Priority: ○ Low  ○ Medium  ● High                    │
│   Assign to: [Carlos (ETO) ▼]                          │
│                                                        │
│ ───────────────────────────────────────────────────    │
│ ⚠️ SIGNATURE REQUIRED                                  │
│                                                        │
│ By signing, you authorize this work order under your   │
│ role as Chief Engineer.                                │
│                                                        │
│ Role at signing: Chief Engineer                        │
│                                                        │
│         [✍️ Sign & Create Work Order]                  │
└────────────────────────────────────────────────────────┘

STEP 3 - OUTCOME
"Work Order WO-2026-0127-001 created and assigned to Carlos.
 Fault FLT-2026-0127 linked."

Backend (TRANSACTIONAL):
1. BEGIN
2. Role check: is_hod() ✓
3. Validate signature payload present ✓
4. INSERT pms_work_orders
5. UPDATE pms_faults SET status = 'work_ordered', work_order_id = new_id
6. INSERT pms_audit_log (signature: {role_at_signing: 'chief_engineer', ...})
7. COMMIT
8. Push notification to Carlos
```

### Signature Payload Captured

```json
{
  "user_id": "robert-uuid",
  "role_at_signing": "chief_engineer",
  "signature_type": "create_work_order_from_fault",
  "fault_id": "flt-uuid",
  "work_order_id": "wo-uuid",
  "signed_at": "2026-01-27T08:35:42Z"
}
```

### Failure Scenarios (SIGNED Action)

| Failure | HTTP | Cause | User Message |
|---------|------|-------|--------------|
| Crew attempts | 403 | Not HOD | "Requires Chief Engineer or higher" |
| Missing signature | 400 | No signature payload | "Signature required for this action" |
| Fault not found | 404 | Invalid fault_id | "Fault not found" |
| Fault already has WO | 409 | work_order_id NOT NULL | "Fault already has work order" |
| Invalid role_at_signing | 400 | Claimed role ≠ actual role | "Role mismatch" |

---

## Journey 4: Crew Attempts Unauthorized Action (DENIED)

**Actor**: Maria (Deckhand, role: `crew`)
**Context**: Sees fault is resolved, tries to close it
**Query**: "close bilge pump fault"

### Flow

```
STEP 1 - QUERY
"close bilge pump fault"

Celeste detects:
  - Equipment: Bilge Pump #2
  - Fault: FLT-2026-0127
  - Intent: close_fault
  - Role check: CREW ≠ engineer+

STEP 2 - DENIAL (Before Form)
┌────────────────────────────────────────────────────────┐
│ ⚠️ FLT-2026-0127 - Bilge Pump #2                       │
│                                                        │
│ Status: investigating                                  │
│                                                        │
│ ───────────────────────────────────────────────────    │
│ ℹ️ close_fault requires Engineer role                  │
│                                                        │
│ Actions available to you:                              │
│ ▶ Add Note                                             │
│ ▶ Add Photo                                            │
│ ▶ View History                                         │
└────────────────────────────────────────────────────────┘
```

### If Crew Bypasses UI and Calls API Directly

```
POST /v1/actions/execute
{
  "action": "close_fault",
  "context": { "yacht_id": "..." },
  "payload": { "fault_id": "..." }
}

Response: 403 Forbidden
{
  "error": "insufficient_permissions",
  "message": "close_fault requires Engineer or higher role",
  "required_role": "engineer",
  "your_role": "crew"
}
```

### Backend Rejection Points

1. **Registry check**: Role not in `allowed_roles` → 403
2. **RLS check**: `engineer_update_faults` policy → row-level denial
3. **Handler check**: `is_engineer()` validation → 403

All three layers enforce the same rule. Defense in depth.

---

## Journey 5: Equipment Recurrence Analysis

**Actor**: Alexandra (Manager, role: `manager`)
**Context**: Weekly review from shore office
**Query**: "faults for bilge pumps last 6 months"

### Flow

```
STEP 1 - QUERY
"faults for bilge pumps last 6 months"

STEP 2 - FOCUS (Trend Analysis)
┌────────────────────────────────────────────────────────┐
│ Bilge System - Fault History (6 months)                │
│                                                        │
│ Equipment: Bilge Pump #1, Bilge Pump #2                │
│ Total Faults: 4                                        │
│                                                        │
│ 2026-01-27 │ Pump #2 bearing - RESOLVED                │
│ 2025-11-15 │ Pump #1 float switch - RESOLVED           │
│ 2025-08-03 │ Pump #2 impeller - RESOLVED               │
│ 2025-04-22 │ High water alarm false - RESOLVED         │
│                                                        │
│ ───────────────────────────────────────────────────    │
│ ⚠️ Pattern Detected:                                   │
│ Bilge Pump #2 has 2 mechanical failures in 6 months    │
│                                                        │
│ Suggested Action:                                      │
│ [Schedule Preventive Maintenance for Pump #2]          │
└────────────────────────────────────────────────────────┘
```

### Backend Query

```sql
SELECT
    f.fault_code,
    f.title,
    f.severity,
    f.status,
    f.detected_at,
    f.resolved_at,
    e.name AS equipment_name
FROM pms_faults f
JOIN pms_equipment e ON f.equipment_id = e.id
WHERE f.yacht_id = public.get_user_yacht_id()
  AND e.category = 'bilge_system'
  AND f.detected_at > NOW() - INTERVAL '6 months'
ORDER BY f.detected_at DESC;
```

---

## Journey 6: Photo Documentation Flow

**Actor**: James (Bosun, role: `crew`)
**Context**: Visible damage on deck
**Query**: "report damage stanchion port side"

### Flow

```
STEP 1 - QUERY + ACT
"report damage stanchion port side"

STEP 2 - FORM (with photo prompt)
┌────────────────────────────────────────────────────────┐
│ Report Fault                                           │
│                                                        │
│ Equipment: [Deck Hardware - Stanchions ▼]              │
│ Location: Port Side Midship                            │
│ Title: [Bent stanchion requires replacement     ]      │
│ Severity: ● Minor  ○ Moderate  ○ Major                 │
│                                                        │
│ 📷 Add Photos (recommended for visible damage)         │
│                                                        │
│ ┌─────────┐ ┌─────────┐                                │
│ │   📷    │ │   + Add │                                │
│ │ Photo 1 │ │         │                                │
│ └─────────┘ └─────────┘                                │
│                                                        │
│ Caption: [Bent at 15° angle, base intact         ]     │
│                                                        │
│         [Submit with Photos]                           │
└────────────────────────────────────────────────────────┘

STEP 3 - OUTCOME
"Fault FLT-2026-0128 reported with 1 photo attached."

Backend:
1. Fault created (same as Journey 1)
2. Photo upload to storage:
   - Bucket: pms-discrepancy-photos
   - Path: {yacht_id}/faults/{fault_id}/{uuid}.jpg
   - RLS: crew_upload_discrepancy_photos ✓
3. INSERT pms_attachments (entity_type: 'fault', entity_id: fault_id)
4. Audit log for both fault and attachment
```

### Storage Path Contract

```
Bucket: pms-discrepancy-photos
Path:   {yacht_id}/faults/{fault_id}/{filename}

Example:
  pms-discrepancy-photos/abc123-yacht/faults/def456-fault/IMG_2026.jpg
```

### Photo Upload Failures

| Failure | HTTP | Cause | User Message |
|---------|------|-------|--------------|
| File too large | 413 | > 10MB | "Photo exceeds 10MB limit" |
| Invalid format | 400 | Not JPG/PNG/HEIC | "Unsupported file format" |
| Storage full | 507 | Quota exceeded | "Storage quota exceeded" |
| Yacht mismatch | 403 | RLS path check | "Access denied" |

---

# PART 6: ERROR MAPPING & EDGE CASES

## HTTP Status Code Discipline

| Code | Meaning | When Used |
|------|---------|-----------|
| 200 | Success | Action completed |
| 201 | Created | Fault/note/attachment created |
| 400 | Bad Request | Missing required fields, invalid values |
| 403 | Forbidden | Role check failed, RLS denied |
| 404 | Not Found | Fault/equipment doesn't exist |
| 409 | Conflict | State violation (e.g., already closed) |
| 413 | Payload Too Large | Photo > 10MB |
| 500 | Server Error | DB error, unexpected exception |

**CRITICAL**: User errors (bad data, wrong role) MUST return 4xx, NEVER 500.

---

## Edge Cases by Action

### report_fault

| Edge Case | Expected Behavior | HTTP |
|-----------|-------------------|------|
| Equipment doesn't exist | Reject | 404 |
| Equipment from different yacht | Reject (RLS) | 403 |
| Severity not in enum | Reject | 400 |
| Title empty | Reject | 400 |
| Title > 500 chars | Truncate or reject | 400 |
| Description empty | Accept (nullable) | 200 |
| Duplicate fault same equipment | Accept (not unique constraint) | 200 |

### acknowledge_fault

| Edge Case | Expected Behavior | HTTP |
|-----------|-------------------|------|
| Fault doesn't exist | Reject | 404 |
| Already acknowledged | Accept (idempotent) | 200 |
| Crew role attempts | Reject | 403 |
| Fault is closed | Reject | 409 |
| Fault is false_alarm | Reject | 409 |

### close_fault

| Edge Case | Expected Behavior | HTTP |
|-----------|-------------------|------|
| Fault doesn't exist | Reject | 404 |
| Already closed | Accept (idempotent) | 200 |
| Crew role attempts | Reject | 403 |
| Fault is false_alarm | Reject (terminal state) | 409 |
| No linked work order | Accept (direct close allowed) | 200 |

### reopen_fault

| Edge Case | Expected Behavior | HTTP |
|-----------|-------------------|------|
| Fault not closed | Reject | 409 |
| Fault is false_alarm | Reject (terminal) | 409 |
| Crew role attempts | Reject | 403 |
| Linked WO still open | Accept | 200 |

### create_work_order_from_fault

| Edge Case | Expected Behavior | HTTP |
|-----------|-------------------|------|
| Fault already has WO | Reject | 409 |
| Missing signature | Reject | 400 |
| Signature role != actual role | Reject | 400 |
| Crew/engineer attempts | Reject | 403 |
| Fault is closed | Reject | 409 |
| Fault is false_alarm | Reject | 409 |

### add_fault_note

| Edge Case | Expected Behavior | HTTP |
|-----------|-------------------|------|
| Fault doesn't exist | Reject | 404 |
| Text empty | Reject | 400 |
| Text > 5000 chars | Truncate or reject | 400 |
| Fault is closed | Accept (notes on closed OK) | 200 |

### add_fault_photo

| Edge Case | Expected Behavior | HTTP |
|-----------|-------------------|------|
| Fault doesn't exist | Reject | 404 |
| File > 10MB | Reject | 413 |
| Invalid mime type | Reject | 400 |
| Storage quota exceeded | Reject | 507 |
| Fault is closed | Accept (photos on closed OK) | 200 |

---

## State Machine Validation

```
         ┌──────────────────────────────────────────────┐
         │                                              │
         ▼                                              │
       open ───────────────────────────────► false_alarm
         │                                    (terminal)
         │ acknowledge_fault
         ▼
    investigating
         │
         │ create_work_order_from_fault
         ▼
    work_ordered
         │
         │ close_fault (via WO completion)
         ▼
       closed ◄─────────────────────────────────────────┐
         │                                              │
         │ reopen_fault (exception only)                │
         └──────────────────────────────────────────────┘
```

### Invalid Transitions (MUST return 409)

| Current State | Attempted Action | Result |
|---------------|------------------|--------|
| closed | acknowledge_fault | 409 |
| closed | create_work_order | 409 |
| false_alarm | ANY mutation | 409 |
| work_ordered | create_work_order | 409 |

---

## Concurrent Modification Handling

| Scenario | Handling |
|----------|----------|
| Two users close same fault | First succeeds, second gets 200 (idempotent) |
| User closes while another reopens | Last write wins (no locking) |
| WO created while fault updating | Both succeed (non-conflicting) |

**Note**: For v1, last-write-wins is acceptable. v2 may add optimistic locking via `updated_at` checks.

---

# PART 6B: GUARDRAILS

## Deletion Doctrine (MANDATORY)

```
Faults are NEVER deleted.

The deleted_at, deleted_by, deletion_reason columns exist for legacy
compatibility. They MUST NOT be written to.

Rationale: Fault history is critical for:
1. Recurrence pattern analysis
2. Equipment reliability metrics
3. Audit trail integrity
4. Regulatory compliance
```

### Enforcement

1. **No DELETE policy on pms_faults** - RLS blocks all deletes
2. **Handler validation** - Reject any delete request at handler level
3. **Audit discipline** - No `action: 'delete_fault'` should ever appear

---

## Signature Invariant (MANDATORY)

```
pms_audit_log.signature is NEVER NULL

Non-SIGNED actions: signature = '{}'::jsonb (empty object)
SIGNED actions:     signature = {role_at_signing, confirmed, ...}
```

### Why This Matters

```sql
-- Query: "Who authorized work orders last month?"
SELECT * FROM pms_audit_log
WHERE signature != '{}'
AND created_at > NOW() - INTERVAL '30 days';

-- This works because:
-- - Empty {} = no signature required
-- - Non-empty = someone signed with authority
-- - NULL never occurs
```

### Enforcement

1. **Handler level**: Always set signature (empty or populated)
2. **DB constraint**: Consider `CHECK (signature IS NOT NULL)` on audit table

---

## Yacht Isolation (MANDATORY)

```
Every query MUST include yacht_id = public.get_user_yacht_id()

There are no cross-yacht operations in the Fault Lens.
```

### Enforcement Points

1. **RLS policies**: All include `yacht_id = public.get_user_yacht_id()`
2. **Handler INSERT**: Always set `yacht_id` from helper, never from payload
3. **Handler SELECT/UPDATE**: Always include `yacht_id` in WHERE

---

## Role Hierarchy (REFERENCE)

```
                    manager
                       │
          ┌────────────┴────────────┐
          │                         │
       captain              chief_engineer
          │                         │
          └────────────┬────────────┘
                       │
                  chief_officer
                       │
          ┌────────────┴────────────┐
          │                         │
       engineer                   eto
          │
          └──── crew (deckhand, steward, chef, ...)
```

### Role → Permission Mapping

| Permission | Roles |
|------------|-------|
| View faults | ALL |
| Report fault | ALL |
| Add note | ALL |
| Add photo | ALL |
| Acknowledge | engineer, eto, chief_officer, chief_engineer, captain, manager |
| Update | engineer, eto, chief_officer, chief_engineer, captain, manager |
| Close | engineer, chief_officer, chief_engineer, captain, manager |
| Reopen | engineer, chief_officer, chief_engineer, captain, manager |
| Create WO (SIGNED) | chief_engineer, captain, manager |

---

## Storage Security (MANDATORY)

```
Bucket: pms-discrepancy-photos
Path:   {yacht_id}/faults/{fault_id}/{filename}
```

### Enforcement

1. **Upload RLS**: Path must start with user's yacht_id
2. **Download RLS**: Same yacht_id check
3. **Delete RLS**: HOD+ only (is_hod() check)

### Forbidden Operations

- Cross-yacht file access
- Direct URL guessing (signed URLs required)
- Crew deleting files (HOD+ only)

---

## Input Validation (MANDATORY)

| Field | Validation |
|-------|------------|
| title | Required, max 500 chars, no script tags |
| description | Optional, max 5000 chars |
| severity | Must be in enum: cosmetic, minor, major, critical, safety |
| equipment_id | Must exist in pms_equipment for same yacht |
| fault_id | Must exist in pms_faults for same yacht |
| photo | Max 10MB, allowed: jpg, png, heic, webp |

### XSS Prevention

All text fields stored as-is (no HTML allowed). Frontend renders as text, not HTML.

---

## Error Message Discipline

```
NEVER expose internal details in error messages.

BAD:  "PostgreSQL error: relation pms_faults does not exist"
GOOD: "Unable to report fault. Please try again."

BAD:  "RLS policy violation on yacht_id 123-456-789"
GOOD: "Access denied"
```

---

# PART 6C: ESCAPE HATCHES

| From Fault | To Lens | Trigger |
|------------|---------|---------|
| View equipment | Equipment Lens | Click equipment_id |
| View linked WO | Work Order Lens | Click work_order_id |
| View attachments | Document Lens | Click attachment |

---

# PART 7: MIGRATIONS

## Required (P0-P1)
1. `20260127_001_fix_faults_rls.sql` - Fault RLS INSERT/UPDATE policies
2. `20260127_002_fix_notes_rls.sql` - Notes RLS INSERT/UPDATE policies
3. `20260127_003_discrepancy_storage_policies.sql` - Storage bucket policies
4. `20260127_004_create_is_engineer_function.sql` - is_engineer() helper

## Recommended (P2)
5. `20260127_005_fault_indexes.sql` - Performance indexes

---

# PART 8: DEPLOYMENT CHECKLIST

## Pre-Deploy
- [ ] Backup database
- [ ] Verify `get_user_yacht_id()` deployed
- [ ] Verify `is_hod()` deployed
- [ ] Verify `is_manager()` deployed
- [ ] Test migrations on staging

## Deploy Order
1. [ ] 20260127_004 (is_engineer function)
2. [ ] 20260127_001 (fault RLS)
3. [ ] 20260127_002 (notes RLS)
4. [ ] 20260127_003 (storage policies)
5. [ ] 20260127_005 (indexes)

## Post-Deploy Verification

### 1. RLS Policies Check
```sql
SELECT tablename, policyname FROM pg_policies
WHERE tablename IN ('pms_faults', 'pms_notes')
ORDER BY tablename, policyname;
-- Should show 3+ policies per table
```

### 2. Storage Policies Check
```sql
SELECT policyname FROM pg_policies
WHERE schemaname = 'storage' AND tablename = 'objects'
AND policyname LIKE '%discrepancy%';
-- Should return 3 rows
```

### 3. Yacht Isolation Test
```sql
-- As user from Yacht A, verify cannot see Yacht B's faults
SELECT COUNT(*) FROM pms_faults WHERE yacht_id = 'yacht-b-uuid';
-- Should return 0
```

## REST Acceptance Tests

### Crew Can Report Fault
```http
POST /rest/v1/pms_faults
Authorization: Bearer <crew_jwt>
Content-Type: application/json

{
  "equipment_id": "uuid",
  "title": "Test Fault",
  "description": "Test description",
  "severity": "minor"
}
-- Expect: 201 Created
```

### Crew Cannot Close Fault
```http
PATCH /rest/v1/pms_faults?id=eq.{fault_id}
Authorization: Bearer <crew_jwt>
Content-Type: application/json

{
  "status": "closed"
}
-- Expect: 403 Forbidden (only engineer+ can close)
```

### Engineer Can Close Fault
```http
PATCH /rest/v1/pms_faults?id=eq.{fault_id}
Authorization: Bearer <engineer_jwt>
Content-Type: application/json

{
  "status": "closed",
  "resolved_at": "2026-01-27T12:00:00Z"
}
-- Expect: 204 No Content
```

---

# PART 9: TEST SCENARIO MATRIX

## Docker Tests (Fast Loop)

| # | Test Name | Actor | Action | Expected | Validates |
|---|-----------|-------|--------|----------|-----------|
| 1 | crew_can_report | Crew | report_fault | 200 + fault_id | Role allows all crew |
| 2 | crew_can_add_note | Crew | add_fault_note | 200 + note_id | Notes open to all |
| 3 | crew_cannot_close | Crew | close_fault | 403 | Role gating works |
| 4 | crew_cannot_create_wo | Crew | create_work_order_from_fault | 403 | SIGNED action blocked |
| 5 | engineer_can_acknowledge | Engineer | acknowledge_fault | 200 | is_engineer() works |
| 6 | engineer_can_update | Engineer | update_fault | 200 | RLS UPDATE policy |
| 7 | engineer_can_close | Engineer | close_fault | 200 | close requires engineer+ |
| 8 | hod_can_create_wo | HOD | create_work_order_from_fault | 200 + wo_id | SIGNED with signature |
| 9 | invalid_fault_4xx | Any | update_fault (bad ID) | 404 | Never 500 for user error |
| 10 | yacht_isolation | Cross-yacht | view_fault | 0 rows | RLS yacht filter |
| 11 | suggestions_role_gated | Crew vs HOD | list_actions | Different sets | Action visibility |

## Staging CI Tests (Real JWT)

| # | Test Name | Actor | Action | Expected | Validates |
|---|-----------|-------|--------|----------|-----------|
| 1 | CREW report_fault | Real crew JWT | report_fault | 200 | Production auth works |
| 2 | CREW add_fault_note | Real crew JWT | add_fault_note | 200 | Notes RLS correct |
| 3 | CREW close_fault denied | Real crew JWT | close_fault | 403 | Role enforcement |
| 4 | ENGINEER update_fault | Real engineer JWT | update_fault | 200 | is_engineer() deployed |
| 5 | CREW create_wo denied | Real crew JWT | create_work_order | 403 | SIGNED blocked |
| 6 | HOD create_work_order | Real HOD JWT | create_work_order | 200 | Signature captured |
| 7 | Invalid fault 4xx | Real JWT | update bad ID | 4xx | Error mapping |
| 8 | HOD suggestions | Real HOD JWT | list_actions | Includes create_wo | Visibility correct |
| 9 | CREW suggestions | Real crew JWT | list_actions | Excludes create_wo | Visibility correct |

## Success/Failure Test Pairs

| Happy Path | Failure Path | Validates |
|------------|--------------|-----------|
| Crew reports fault (200) | Crew reports without equipment (400) | Required field validation |
| Engineer closes fault (200) | Crew closes fault (403) | Role enforcement |
| HOD creates WO (200) | HOD creates WO without signature (400) | Signature required |
| Add photo (200) | Add 15MB photo (413) | Size limit |
| View own yacht fault (200) | View other yacht fault (0 rows) | Yacht isolation |

## Idempotency Tests

| Action | Second Call | Expected |
|--------|-------------|----------|
| acknowledge_fault | Same fault | 200 (no error, already acknowledged) |
| close_fault | Same fault | 200 (already closed) |
| reopen_fault | Same fault | 409 (can't reopen if not closed) |

---

# PART 10: LEDGER (AUDIT) — GROUND TRUTH

The `pms_audit_log` is the immutable source of truth for all fault operations. Every micro-action writes exactly one audit row on success.

## Ledger Invariants

| Invariant | Rule | Enforcement |
|-----------|------|-------------|
| **One row per action** | Every successful mutation = exactly one audit entry | Handler writes after DB success |
| **Signature never NULL** | `signature` is `'{}'::jsonb` or populated JSON | Handler sets before INSERT |
| **No FK to auth.users** | `user_id` is UUID copied, not foreign key | Avoids cross-schema dependency |
| **Immutable** | No UPDATE/DELETE on pms_audit_log | RLS: SELECT only for authenticated |
| **Yacht-scoped** | Every entry has `yacht_id` | Handler sets from `get_user_yacht_id()` |

## Write Pattern (Handler)

```python
# Every fault handler follows this pattern:

async def handle_fault_action(action: str, payload: dict, user: User):
    # 1. Execute the mutation
    result = await supabase.from_('pms_faults').update(...)

    # 2. Prepare audit entry
    audit_entry = {
        'id': uuid4(),
        'yacht_id': user.yacht_id,
        'entity_type': 'fault',
        'entity_id': result['id'],
        'action': action,
        'user_id': user.id,
        'old_values': old_state,  # captured before mutation
        'new_values': new_state,
        'signature': payload.get('signature', {}),  # {} if non-SIGNED
        'metadata': {'source': 'fault_lens', 'ip': request.ip},
        'created_at': datetime.utcnow()
    }

    # 3. Write audit (always, even if action is trivial)
    await supabase.from_('pms_audit_log').insert(audit_entry)

    return result
```

## Signature Semantics

| Action Type | Signature Value | Example |
|-------------|-----------------|---------|
| Non-SIGNED (most actions) | `'{}'::jsonb` | report_fault, add_note, close_fault |
| SIGNED (authority required) | `{role_at_signing, confirmed, ...}` | create_work_order_from_fault |

```sql
-- Non-SIGNED action audit entry:
INSERT INTO pms_audit_log (
    ..., signature, ...
) VALUES (
    ..., '{}'::jsonb, ...  -- Empty object, NOT NULL
);

-- SIGNED action audit entry:
INSERT INTO pms_audit_log (
    ..., signature, ...
) VALUES (
    ..., '{"role_at_signing": "captain", "confirmed": true, "signed_at": "..."}'::jsonb, ...
);
```

## Read Patterns

### Entity History (UI Timeline)

```sql
-- Paginated history for a specific fault
SELECT
    a.id,
    a.action,
    a.user_id,
    u.display_name AS actor_name,
    a.old_values,
    a.new_values,
    a.signature,
    a.created_at
FROM pms_audit_log a
LEFT JOIN auth_users_profiles u ON a.user_id = u.id
WHERE a.entity_type = 'fault'
  AND a.entity_id = :fault_id
  AND a.yacht_id = public.get_user_yacht_id()
ORDER BY a.created_at DESC
LIMIT 20 OFFSET :offset;
```

### Signed Actions Query (Compliance)

```sql
-- All signed fault actions in date range
SELECT
    a.entity_id AS fault_id,
    f.fault_code,
    a.action,
    a.signature->>'role_at_signing' AS signed_as,
    a.signature->>'signed_at' AS signed_at,
    a.user_id
FROM pms_audit_log a
JOIN pms_faults f ON a.entity_id = f.id
WHERE a.entity_type = 'fault'
  AND a.signature != '{}'  -- Has actual signature
  AND a.yacht_id = public.get_user_yacht_id()
  AND a.created_at BETWEEN :start_date AND :end_date
ORDER BY a.created_at DESC;
```

### User Activity Query

```sql
-- All fault actions by a specific user
SELECT
    a.action,
    a.entity_id AS fault_id,
    f.fault_code,
    a.created_at
FROM pms_audit_log a
JOIN pms_faults f ON a.entity_id = f.id
WHERE a.user_id = :user_id
  AND a.entity_type = 'fault'
  AND a.yacht_id = public.get_user_yacht_id()
ORDER BY a.created_at DESC
LIMIT 50;
```

## UI Surfacing

| Surface | Data Source | Display |
|---------|-------------|---------|
| Fault Detail → Timeline | `pms_audit_log` filtered by entity_id | Chronological action list with actor names |
| Equipment → Fault History | Join faults → audit | All actions on all faults for equipment |
| Compliance Report | Signed actions query | Table of authorizations with signatures |
| User Profile → Activity | User activity query | Recent actions by logged-in user |

### Timeline Card Rendering

```
┌────────────────────────────────────────────────────────────┐
│ 08:35 │ WORK ORDER CREATED                                │
│       │ by Robert (Chief Engineer)                        │
│       │ ✍️ Signed as: Chief Engineer                       │
│       │ WO-2026-0127-001 assigned to Carlos               │
├────────────────────────────────────────────────────────────┤
│ 07:20 │ STATUS UPDATED → investigating                    │
│       │ by Carlos (ETO)                                   │
│       │ "Scheduling inspection after breakfast"           │
├────────────────────────────────────────────────────────────┤
│ 07:19 │ NOTE ADDED                                        │
│       │ by Carlos (ETO)                                   │
│       │ "Bearing failure likely. Sound matches worn..."   │
├────────────────────────────────────────────────────────────┤
│ 06:46 │ FAULT REPORTED                                    │
│       │ by Maria (Deckhand)                               │
│       │ Severity: Moderate                                │
└────────────────────────────────────────────────────────────┘
```

---

# PART 11: NOTIFICATIONS BLUEPRINT

Notifications ensure the right person sees pending work at the right time, with a CTA that maps directly to a backend action.

## Tables

### pms_notifications

```sql
CREATE TABLE pms_notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    yacht_id UUID NOT NULL,
    user_id UUID NOT NULL,           -- Target recipient
    notification_type TEXT NOT NULL, -- fault_reported, fault_stale, wo_pending, etc.
    entity_type TEXT NOT NULL,       -- 'fault', 'work_order'
    entity_id UUID NOT NULL,         -- The fault/WO this is about
    title TEXT NOT NULL,             -- "New Fault: Bilge Pump #2"
    body TEXT,                       -- "Reported by Maria at 06:46"
    cta_action TEXT,                 -- 'view_fault_detail', 'acknowledge_fault'
    cta_payload JSONB,               -- {fault_id: '...'}
    priority TEXT DEFAULT 'normal',  -- 'low', 'normal', 'high', 'urgent'
    read_at TIMESTAMPTZ,             -- NULL = unread
    dismissed_at TIMESTAMPTZ,        -- NULL = not dismissed
    created_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT fk_yacht FOREIGN KEY (yacht_id)
        REFERENCES yachts(id) ON DELETE CASCADE
);

-- RLS: Users see only their own notifications
CREATE POLICY "user_own_notifications" ON pms_notifications
FOR ALL TO authenticated
USING (user_id = auth.uid() AND yacht_id = public.get_user_yacht_id());
```

### pms_notification_preferences

```sql
CREATE TABLE pms_notification_preferences (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL UNIQUE,
    yacht_id UUID NOT NULL,

    -- Channel preferences
    in_app BOOLEAN DEFAULT true,
    push BOOLEAN DEFAULT true,
    email BOOLEAN DEFAULT false,

    -- Type preferences (what to notify)
    fault_reported BOOLEAN DEFAULT true,
    fault_stale BOOLEAN DEFAULT true,
    wo_assigned BOOLEAN DEFAULT true,
    wo_pending_signature BOOLEAN DEFAULT true,

    -- Quiet hours (UTC)
    quiet_start TIME,  -- e.g., '22:00'
    quiet_end TIME,    -- e.g., '06:00'

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

## Notification Types (Fault Lens)

| Type | Trigger | Recipients | Priority | CTA |
|------|---------|------------|----------|-----|
| `fault_reported` | report_fault success | HOD (chief_eng, captain) | normal | view_fault_detail |
| `fault_acknowledged` | acknowledge_fault | Reporter (FYI) | low | view_fault_detail |
| `fault_stale` | Cron: open > 24h, no activity | HOD | high | acknowledge_fault |
| `fault_closed` | close_fault | Reporter (FYI) | low | view_fault_detail |
| `wo_created_from_fault` | create_work_order_from_fault | Assigned engineer | high | view_work_order |
| `signature_required` | WO draft pending HOD sign | captain, manager | urgent | approve_work_order |

## Deterministic Nudges

### v_pending_work_items (View)

```sql
CREATE OR REPLACE VIEW v_pending_work_items AS
SELECT
    'fault' AS item_type,
    f.id AS item_id,
    f.fault_code AS item_code,
    f.title,
    f.status,
    f.severity::text,
    f.detected_at AS created_at,
    EXTRACT(EPOCH FROM (NOW() - f.detected_at)) / 3600 AS hours_open,
    CASE
        WHEN f.status = 'open' AND f.detected_at < NOW() - INTERVAL '24 hours' THEN 'stale'
        WHEN f.status = 'open' THEN 'pending_triage'
        WHEN f.status = 'investigating' THEN 'in_progress'
        ELSE 'resolved'
    END AS urgency,
    CASE
        WHEN f.status = 'open' THEN 'acknowledge_fault'
        WHEN f.status = 'investigating' THEN 'update_fault'
        ELSE NULL
    END AS suggested_cta,
    f.yacht_id
FROM pms_faults f
WHERE f.yacht_id = public.get_user_yacht_id()
  AND f.status NOT IN ('closed', 'false_alarm')

UNION ALL

SELECT
    'work_order' AS item_type,
    wo.id AS item_id,
    wo.wo_number AS item_code,
    wo.title,
    wo.status,
    wo.priority,
    wo.created_at,
    EXTRACT(EPOCH FROM (NOW() - wo.created_at)) / 3600 AS hours_open,
    CASE
        WHEN wo.status = 'draft' AND wo.created_at < NOW() - INTERVAL '48 hours' THEN 'stale_draft'
        WHEN wo.status = 'draft' THEN 'pending_approval'
        WHEN wo.status = 'planned' THEN 'ready_to_start'
        ELSE 'in_progress'
    END AS urgency,
    CASE
        WHEN wo.status = 'draft' THEN 'approve_work_order'
        WHEN wo.status = 'planned' THEN 'start_work_order'
        ELSE NULL
    END AS suggested_cta,
    wo.yacht_id
FROM pms_work_orders wo
WHERE wo.yacht_id = public.get_user_yacht_id()
  AND wo.status NOT IN ('completed', 'cancelled');
```

### Pending Work Query (HOD Dashboard)

```sql
SELECT
    item_type,
    item_code,
    title,
    urgency,
    hours_open,
    suggested_cta
FROM v_pending_work_items
WHERE urgency IN ('stale', 'pending_triage', 'stale_draft', 'pending_approval')
ORDER BY
    CASE urgency
        WHEN 'stale' THEN 1
        WHEN 'stale_draft' THEN 2
        WHEN 'pending_approval' THEN 3
        WHEN 'pending_triage' THEN 4
        ELSE 5
    END,
    hours_open DESC
LIMIT 20;
```

## Notification Flow

```
┌─────────────────────────────────────────────────────────────┐
│ TRIGGER: report_fault succeeds                              │
└─────────────────────────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────────┐
│ 1. Determine recipients by role                             │
│    SELECT user_id FROM auth_users_roles                     │
│    WHERE role IN ('chief_engineer', 'captain')              │
│      AND yacht_id = :yacht_id                               │
└─────────────────────────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. Check preferences for each recipient                     │
│    - fault_reported enabled?                                │
│    - In quiet hours?                                        │
│    - Channel preference (in_app, push, email)               │
└─────────────────────────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. Create notification with CTA                             │
│    INSERT INTO pms_notifications (                          │
│        notification_type: 'fault_reported',                 │
│        cta_action: 'view_fault_detail',                     │
│        cta_payload: {fault_id: '...'}                       │
│    )                                                        │
└─────────────────────────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. Deliver via channels                                     │
│    - In-app: Immediate (notification count badge)           │
│    - Push: Via FCM/APNS                                     │
│    - Email: Batched (hourly digest unless urgent)           │
└─────────────────────────────────────────────────────────────┘
```

## CTA → ActionModal Mapping

When user taps notification, the `cta_action` and `cta_payload` open the ActionModal prefilled:

```typescript
// Notification tap handler
function handleNotificationTap(notification: Notification) {
    // cta_action maps to registry action
    const action = notification.cta_action; // 'acknowledge_fault'
    const payload = notification.cta_payload; // {fault_id: '...'}

    // Open ActionModal with prefilled context
    openActionModal({
        action: action,
        prefill: payload,
        source: 'notification'
    });
}
```

## Acceptance Criteria

| Criteria | Test |
|----------|------|
| HOD receives notification on fault report | report_fault → check pms_notifications for HOD user_id |
| Quiet hours respected | Create notification at 23:00, verify not pushed until 06:00 |
| CTA opens correct action | Tap notification → ActionModal shows correct action |
| Read status tracked | Tap notification → read_at populated |
| Stale faults surface | Open fault > 24h → appears in v_pending_work_items with urgency='stale' |
| Idempotent | Same trigger twice → only one notification created |

---

# PART 12: ON-BOARD OPERATIONAL CONTEXTS

Real-world usage patterns that drive design decisions.

## Context 1: Engine Room Breakdown at Sea

**Actor**: Chief Engineer (Robert)
**Situation**: Main engine failure, one hand on railing, phone in other hand
**Conditions**: Rolling seas, dim lighting, stress

### Flow

```
STEP 1: Quick Report (one-handed)
┌────────────────────────────────────────────────────────────┐
│ Voice: "report fault main engine stopped"                  │
│                                                            │
│ OR single tap: 🚨 Quick Report (large button)              │
│                                                            │
│ Celeste: Auto-detects equipment from location/history      │
│          Prefills: Main Engine, Major severity             │
└────────────────────────────────────────────────────────────┘
           │
           ▼
STEP 2: Photo (before touching anything)
┌────────────────────────────────────────────────────────────┐
│ Camera opens immediately after report                      │
│                                                            │
│ [📷 Capture]  [Skip for now]                               │
│                                                            │
│ Robert takes photos of warning lights, leak location       │
│ Photos upload in background while he works                 │
└────────────────────────────────────────────────────────────┘
           │
           ▼
STEP 3: Investigate (hands busy)
┌────────────────────────────────────────────────────────────┐
│ Robert investigates the issue (30 min)                     │
│                                                            │
│ Phone locked, notifications queued                         │
│ Captain receives push: "Main Engine - Major Fault"         │
│                                                            │
│ NO low-fidelity prompts during active investigation        │
└────────────────────────────────────────────────────────────┘
           │
           ▼
STEP 4: Diagnose (when ready)
┌────────────────────────────────────────────────────────────┐
│ Robert unlocks phone                                       │
│                                                            │
│ "add note fuel injector failed cylinder 3"                 │
│                                                            │
│ Celeste: Context = active fault, suggests diagnose action  │
│                                                            │
│ One tap: [Diagnose: Fuel Injector Failure]                 │
└────────────────────────────────────────────────────────────┘
           │
           ▼
STEP 5: Escalate to WO (signature required)
┌────────────────────────────────────────────────────────────┐
│ "need work order for this"                                 │
│                                                            │
│ Celeste: Detects SIGNED action, Robert is HOD ✓            │
│                                                            │
│ Form: WO prefilled from fault data                         │
│       Priority: High (inferred from severity)              │
│       Assign: [Select or "Vendor Required"]                │
│                                                            │
│ [✍️ Sign as Chief Engineer]                                │
└────────────────────────────────────────────────────────────┘
```

### Design Implications

- **Large touch targets**: 48px minimum, preferably 56px for emergency actions
- **Voice input**: Always available, especially in noisy environments
- **Background upload**: Photos queue and sync when stable connection
- **No interruptions**: During active fault handling, suppress low-priority nudges
- **Context persistence**: Returning to phone after 30min, fault context retained

---

## Context 2: Interior Cosmetic Issue

**Actor**: Chief Steward (Anna)
**Situation**: Guest noticed scratch on dining table
**Conditions**: Calm, not urgent, needs documentation

### Flow

```
STEP 1: Report with Photo
┌────────────────────────────────────────────────────────────┐
│ "report cosmetic damage dining table"                      │
│                                                            │
│ Celeste: Suggests cosmetic severity (default)              │
│          Prompts for photo (recommended for visible)       │
│                                                            │
│ Anna takes multiple angles                                 │
└────────────────────────────────────────────────────────────┘
           │
           ▼
STEP 2: HOD Triage (later)
┌────────────────────────────────────────────────────────────┐
│ Chief Engineer reviews during morning brief                │
│                                                            │
│ Options:                                                   │
│ - [Mark False Alarm] - Not actually damage                 │
│ - [Schedule Repair] - Add to next port WO                  │
│ - [Acknowledge] - Noted, monitor only                      │
└────────────────────────────────────────────────────────────┘
           │
           ▼
STEP 3: False Alarm Path (if applicable)
┌────────────────────────────────────────────────────────────┐
│ Chief Eng: "this is existing wear, not new damage"         │
│                                                            │
│ Action: mark_fault_false_alarm                             │
│ Status: false_alarm (terminal)                             │
│                                                            │
│ Audit: Records decision with reason                        │
│ Anna notified: "Fault reviewed: Existing wear pattern"     │
└────────────────────────────────────────────────────────────┘
```

---

## Context 3: Sea Trial Regression

**Actor**: Captain
**Situation**: Issue thought fixed during last yard period has recurred
**Conditions**: At sea, vendor involvement needed

### Flow

```
STEP 1: Find Previous Fault
┌────────────────────────────────────────────────────────────┐
│ "faults for steering system last year"                     │
│                                                            │
│ Celeste: Shows fault history with pattern analysis         │
│                                                            │
│ FLT-2025-0089 | Steering stiff | CLOSED (yard repair)      │
│ FLT-2025-0045 | Steering noise | CLOSED (bearing replaced) │
└────────────────────────────────────────────────────────────┘
           │
           ▼
STEP 2: Reopen with Context
┌────────────────────────────────────────────────────────────┐
│ Captain taps FLT-2025-0089                                 │
│                                                            │
│ Action: reopen_fault                                       │
│                                                            │
│ Note: "Stiffness returned. Yard repair did not hold.       │
│        Requires vendor assessment."                        │
│                                                            │
│ Status: open (from closed)                                 │
│ Audit: reopen with link to previous close                  │
└────────────────────────────────────────────────────────────┘
           │
           ▼
STEP 3: Create WO for Vendor (SIGNED)
┌────────────────────────────────────────────────────────────┐
│ "create work order for vendor"                             │
│                                                            │
│ Form:                                                      │
│   Title: [Steering System - Recurring Stiffness]           │
│   Type: [Vendor Required ▼]                                │
│   Notes: "Previous yard repair failed. Need specialist."   │
│                                                            │
│ [✍️ Sign as Captain]                                       │
│                                                            │
│ Outcome: WO created, flagged for shore-side coordination   │
└────────────────────────────────────────────────────────────┘
```

---

# PART 13: LOW-FIDELITY ACTION AVOIDANCE

## Principle

While a user is actively handling a fault (mid-flow), do NOT suggest handover actions or unrelated nudges. The ledger records state, and notifications surface pending items at the right time/role.

## What to Avoid

| Scenario | Bad Prompt | Why Wrong |
|----------|------------|-----------|
| User just reported fault | "Would you like to close it?" | Can't close what was just reported |
| Engineer investigating | "Create work order?" | Investigation not complete |
| Adding note | "Mark as false alarm?" | Note implies investigation ongoing |
| HOD reviewing | "Reassign to yourself?" | Already their context |

## What to Show Instead

| Scenario | Good Suggestion | Why Correct |
|----------|-----------------|-------------|
| Just reported | "Add photo?", "Add note?" | Natural next steps |
| Investigation ongoing | "Update status?", "Add diagnosis?" | Continues current flow |
| HOD reviewing | "Acknowledge?", "Create WO?" | Decision-appropriate for role |
| Fault resolved via WO | "Close fault?" | Natural completion |

## Context-Aware Suggestion Rules

```python
def get_suggested_actions(fault: Fault, user: User, recent_actions: List[str]) -> List[str]:
    suggestions = []

    # Rule 1: Don't suggest close/false_alarm if fault was just reported
    if 'report_fault' in recent_actions[-3:]:
        exclude = ['close_fault', 'mark_fault_false_alarm']
    else:
        exclude = []

    # Rule 2: If user just added note, don't suggest add_note again
    if 'add_fault_note' in recent_actions[-1:]:
        exclude.append('add_fault_note')

    # Rule 3: Role-appropriate suggestions only
    if fault.status == 'open':
        if is_engineer(user):
            suggestions = ['acknowledge_fault', 'add_fault_note', 'add_fault_photo']
        else:  # crew
            suggestions = ['add_fault_note', 'add_fault_photo']

    elif fault.status == 'investigating':
        if is_engineer(user):
            suggestions = ['update_fault', 'diagnose_fault', 'add_fault_note']
            if is_hod(user) and not fault.work_order_id:
                suggestions.append('create_work_order_from_fault')

    elif fault.status == 'work_ordered':
        if is_engineer(user):
            suggestions = ['add_fault_note', 'view_work_order']

    return [s for s in suggestions if s not in exclude]
```

---

# PART 14: SEVERITY MAPPING

## Severity Values

| Value | Meaning | Response Time | Examples |
|-------|---------|---------------|----------|
| `cosmetic` | Visual only, no function impact | Next port / scheduled | Scratch on surface, paint chip |
| `minor` | Minor function impact, workaround exists | Within 48h | Slow drain, sticky switch |
| `major` | Significant function impact | Within 24h | Pump failure with backup, AC unit down |
| `critical` | Critical system affected | Immediate | Main engine issue, steering problem |
| `safety` | Safety system or crew safety | IMMEDIATE + Captain notify | Fire system, life raft, MOB equipment |

## Input Mapping (User Language → Enum)

| User Says | Maps To | Confidence |
|-----------|---------|------------|
| "cosmetic", "visual", "scratch", "appearance" | cosmetic | High |
| "minor", "small", "not urgent" | minor | High |
| "medium", "moderate" | **minor** | Medium (default down) |
| "major", "significant", "important" | major | High |
| "critical", "serious", "urgent" | critical | High |
| "safety", "dangerous", "emergency" | safety | High |

**Note**: "medium" maps to `minor`, not a separate value. Always default DOWN in ambiguity.

## Severity Escalation Rules

```sql
-- Only HOD can escalate severity
-- Any user can de-escalate (reporting conservatively is OK)

-- Escalation requires is_hod()
IF new_severity > old_severity THEN
    REQUIRE is_hod(auth.uid(), yacht_id)
END IF
```

## Severity in Notifications

| Severity | Notification Priority | Push? |
|----------|----------------------|-------|
| cosmetic | low | No (in-app only) |
| minor | normal | Preferences |
| major | high | Yes (immediate) |
| critical | urgent | Yes + sound |
| safety | urgent | Yes + sound + Captain always |

---

# APPENDIX: STATUS LIFECYCLE

```
open (default)
    | report_fault
    v
investigating
    | acknowledge_fault
    v
work_ordered
    | create_work_order_from_fault
    v
resolved
    | close_fault (via WO cascade)
    v
closed (terminal)

Alternative paths:
open -> false_alarm (mark_fault_false_alarm) [terminal]
closed -> open (reopen_fault) [exception case]
```

## Terminal States
- `closed`: Normal completion via WO resolution
- `false_alarm`: Investigation determined no actual fault

---

# APPENDIX: SIGNATURE PAYLOAD SCHEMA

Signed actions (e.g., `create_work_order_from_fault`) must include a structured signature payload in the audit log.

```json
{
  "user_id": "uuid",
  "role_at_signing": "captain|chief_engineer|manager",
  "signature_type": "create_work_order_from_fault",
  "fault_id": "uuid",
  "work_order_id": "uuid",
  "signature_hash": "sha256:base64...",
  "signed_at": "2026-01-27T14:30:00Z"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `user_id` | uuid | YES | User performing the signed action |
| `role_at_signing` | text | YES | User's role at the moment of signing |
| `signature_type` | text | YES | Action being signed |
| `fault_id` | uuid | YES | ID of fault |
| `work_order_id` | uuid | YES | ID of new work order created |
| `signature_hash` | text | YES | Hash of the signed payload for verification |
| `signed_at` | timestamptz | YES | Timestamp of signature |

**Note**: For non-signed actions, `signature = '{}'::jsonb` (empty object, never NULL).

---

# APPENDIX: SINGLE-TENANT MODE

This database serves **one yacht**. All `yacht_id` values are equal in production.

## Essential Guardrails (Still Required)
- **Role gating**: `is_hod()` / `is_engineer()` checks are the primary access control
- **Signature invariant**: Required on signed actions; ledger correctness is independent of tenancy
- **Storage prefixes**: `pms-discrepancy-photos/{yacht_id}/...` remains valuable for structure
- **Handler yacht_id**: Always set `yacht_id = public.get_user_yacht_id()` on INSERTs as backstop

---

# APPENDIX: DOCUMENT STORAGE PATH

**Bucket name**: `pms-discrepancy-photos`

**Object path** (stored in `pms_attachments.storage_path`):
```
{yacht_id}/faults/{fault_id}/{filename}
```

**Important**: Do NOT include bucket name prefix in `storage_path` - the bucket name is already `pms-discrepancy-photos`.

---

**END OF FAULT LENS v1 FINAL**
