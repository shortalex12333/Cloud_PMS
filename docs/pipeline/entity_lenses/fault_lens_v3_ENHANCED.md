# Entity Lens: Fault (ENHANCED TEMPLATE)

**Status**: v3 - Production DB Verified + UX Vision Documented
**Last Updated**: 2026-01-24
**Schema Source**: Production Supabase Database (vzsohavtuotocgrfkfyd.supabase.co)
**Template Status**: Validated against inventory_item_lens_v3_ENHANCED.md (GOLD STANDARD)

---

## ANTI-HALLUCINATION CONTRACT

This document was produced following the 3-artifact verification process:

### Artifact 1: DB Truth Snapshot ✅
- **Source**: `/Volumes/Backup/CELESTE/database_schema.txt` (2026-01-24)
- **pms_faults**: 19 columns verified
- **pms_notes**: 12 columns verified (with fault_id FK)
- **pms_attachments**: 21 columns verified (entity_type/entity_id pattern)
- **pms_audit_log**: signature column exists (JSONB)

### Artifact 2: Action Contract Matrix ✅
- **Source**: `apps/api/actions/action_registry.py`
- **Existing Actions**: report_fault, add_fault_note, add_fault_photo, create_work_order, view_fault, diagnose_fault, view_fault_history
- **Missing from Registry**: update_fault_status, archive_fault (lens defines THE PLAN, registry will be updated)

### Artifact 3: Lens Invariants ✅
- Max 6 user-initiated actions per lens (cognitive load)
- Situation modifiers reorder actions, not add them
- Context flows with user (no navigation loss)
- Pre-fill intelligence from source context
- ONE dismissible banner per modifier
- Generic tables (pms_notes, pms_attachments) are correct pattern

---

# SECTION 0: UX VISION & PHILOSOPHY

## What Problem Does This Lens Solve?

### Traditional Fault Management Software Problem:
```
Engineer discovers hydraulic pump leaking oil
→ Opens "Fault Management" module
→ Sees overwhelming interface:
   [Report Fault] [Edit Fault] [Delete Fault] [View All Faults]
   [Create WO] [Link Equipment] [Add Photo] [Add Note]
   [Change Status] [Assign Crew] [View History] [Export]
   ... 12+ buttons always visible
→ Fills out 15-field form for new fault report
→ Submits
→ Navigates to separate "Work Order" module
→ Creates WO manually, searches for equipment
→ Goes back to Fault, links WO manually
→ 8 minutes, 25+ clicks, context lost multiple times
→ USER ADAPTS TO SOFTWARE
```

### Celeste Fault Lens Solution:
```
Engineer discovers hydraulic pump leaking oil
→ Opens Equipment Lens (Hydraulic Pump #2)
→ Clicks "Report Fault" (contextual action)
→ **FAULT LENS ACTIVATES** with context:
   - knows equipment = Hydraulic Pump #2
   - knows user = current engineer
   - knows timestamp = NOW
→ Modal opens PRE-FILLED:
   - Equipment: Hydraulic Pump #2 ✓ (from navigation)
   - Severity: [dropdown] (user selects "high")
   - Title: "Oil leak" (user types)
   - Description: [optional]
→ User submits (30 seconds)
→ **Fault created, Fault Lens activates**
→ **Critical Fault Modifier triggers** (severity=high)
→ Banner: "⚠️ High severity fault - Create work order?"
→ Primary action: [Create Work Order] (promoted, orange button)
→ Modal opens PRE-FILLED:
   - Title: "Oil leak" ✓ (from fault)
   - Equipment: Hydraulic Pump #2 ✓ (from fault)
   - Type: "corrective" ✓ (inferred)
   - Priority: "critical" ✓ (mapped from high severity)
   - Fault: FLT-2026-001234 ✓ (auto-linked)
→ User submits (15 seconds)
→ WO created, linked to fault automatically
→ Total: 45 seconds, 5 clicks, context preserved
→ SOFTWARE ADAPTS TO USER
```

**Outcome**: 8 minutes → 45 seconds (90% reduction), fault-WO link automatic, context never lost

---

## Core Philosophy: System Adaptation, Not User Navigation

### Principle 1: Contextual Activation (Not Menu Navigation)

**Traditional Paradigm**:
- User must "go to" Fault Management section
- Loses context from previous view (Equipment, WO)
- Must rebuild mental model each time
- Must manually link related entities

**Celeste Paradigm**:
- Lens activates when user **focuses on Fault entity**
- Context flows with user:
  ```
  Equipment Lens → reports fault → Fault Lens (Equipment context preserved)
  Dashboard → clicks critical fault → Fault Lens (severity context preserved)
  Search → clicks fault → Fault Lens (search query preserved)
  ```
- Entity relationships auto-linked (fault → equipment → WO)
- User never "navigates away" - one SPA, URL encodes state

### Principle 2: Dynamic Action Priority (Not Static Buttons)

**Traditional Paradigm**:
- All actions always visible, same order
- "Create Work Order" button same prominence as "Add Note"
- No guidance on what's appropriate for current state
- User must remember workflow logic

**Celeste Paradigm**:
- Actions reorder based on state + context:
  ```
  Critical/High severity + status=open:
    PRIMARY: [Create Work Order] ← urgent, orange button
    SECONDARY: [Update Status] [Add Note]

  Normal severity + status=investigating:
    PRIMARY: [Update Status] ← likely next step
    SECONDARY: [Add Note] [Attach Photo]

  Status=resolved:
    PRIMARY: [Update Status → Close] ← complete workflow
    SECONDARY: [Add Note] (resolution notes)
  ```
- System SHOWS what's most relevant for current situation
- Reduces cognitive load (don't scan 12 buttons for "right" action)

### Principle 3: Automatic Entity Linking (Not Manual Association)

**Traditional Paradigm**:
- User reports fault, fault is orphan
- User must navigate to WO, manually search for fault
- User must manually link fault-equipment-WO triad
- Easy to forget linkage, lose audit trail

**Celeste Paradigm**:
- **Fault → Equipment**: Automatic (reported FROM equipment context)
- **Fault → Work Order**: Automatic (created FROM fault context)
- **Work Order → Equipment**: Inherited (via fault.equipment_id)
```sql
-- When user creates WO from Fault Lens:
INSERT INTO pms_work_orders (
  title,
  equipment_id,  -- FROM fault.equipment_id
  fault_id,      -- FROM current fault
  type,          -- 'corrective' (inferred)
  ...
)

-- Automatically update fault with WO reference:
UPDATE pms_faults
SET work_order_id = :new_work_order_id
WHERE id = :current_fault_id
```
- Zero manual linking required
- Full triad audit trail preserved

---

# SECTION AA: CONTEXT ADAPTATION MECHANISMS

## How The Lens Adapts to User Intent

### Mechanism 1: Source Context Detection

**Variables Captured**:
- **w** (where) = source of navigation
  - `from_equipment` → user clicked "Report Fault" from equipment view
  - `from_dashboard` → user clicked fault from critical faults widget
  - `from_search` → user searched for fault
  - `from_work_order` → user clicked linked fault from WO
  - `from_notification` → user clicked fault alert notification

**Example Flow**:
```javascript
// User in Equipment Lens (Hydraulic Pump #2)
// Clicks "Report Fault"
// URL: /faults/new?source=equipment:hydraulic-pump-2-uuid

lens.activate({
  mode: "create",
  source_context: {
    type: "equipment",
    equipment_id: "hydraulic-pump-2-uuid",
    equipment_name: "Hydraulic Pump #2",
  }
})

// Modal response:
{
  mode: "create",
  pre_fill: {
    equipment_id: "hydraulic-pump-2-uuid",  // Auto-selected
    detected_at: NOW(),  // Default
    severity: null,  // User selects
    title: null,  // User types
  },
  equipment_locked: true,  // Can't change (came from equipment context)
  equipment_display: "Hydraulic Pump #2"  // Read-only display
}
```

### Mechanism 2: State-Based Action Reordering

**Variables**:
- **x** (what) = fault entity
- **y** (condition) = fault state composite
  - Severity: low | medium | high | critical
  - Status: open | investigating | resolved | closed
  - Has WO: true | false
- **z** (intent) = User's inferred goal

**Adaptation Logic**:
```python
def determine_primary_action(x, y, w):
    # x = fault, y = state, w = source context

    severity = y['severity']
    status = y['status']
    has_work_order = y['work_order_id'] is not None

    # CRITICAL/HIGH + OPEN = Urgent WO creation
    if severity in ['critical', 'high'] and status == 'open' and not has_work_order:
        return {
            "primary": "create_work_order_from_fault",
            "badge_color": "red" if severity == 'critical' else "orange",
            "banner": f"{'🚨 Critical' if severity == 'critical' else '⚠️ High severity'} fault - requires work order",
            "button_style": "danger" if severity == 'critical' else "warning",
            "pre_fill": {
                "priority": "emergency" if severity == 'critical' else "critical",
                "type": "corrective",
                "title": x.title,
                "equipment_id": x.equipment_id
            }
        }

    # INVESTIGATING = Status update likely
    elif status == 'investigating':
        return {
            "primary": "update_fault_status",
            "badge_color": "yellow",
            "banner": None,
            "pre_fill": {
                "suggested_next_status": "resolved"  # Likely progression
            }
        }

    # RESOLVED = Close workflow
    elif status == 'resolved':
        return {
            "primary": "update_fault_status",
            "badge_color": "green",
            "banner": "Fault resolved - close to complete workflow",
            "pre_fill": {
                "suggested_next_status": "closed"
            }
        }

    # DEFAULT = Add notes (investigation mode)
    else:
        return {
            "primary": "add_fault_note",
            "badge_color": status_to_color(status),
            "banner": None
        }
```

### Mechanism 3: Work Order Existence Check

**When**: User clicks `create_work_order_from_fault`

**Logic**:
```sql
-- Step 1: Check for existing linked WO
SELECT wo.id, wo.wo_number, wo.status
FROM pms_work_orders wo
WHERE wo.fault_id = :current_fault_id
  AND wo.deleted_at IS NULL
ORDER BY wo.created_at DESC
LIMIT 1;

-- Step 2: Decide action
IF wo EXISTS AND wo.status NOT IN ('completed', 'cancelled') THEN
  -- WARN: Active WO exists
  SHOW WARNING: "Work order already exists: {wo_number} ({status})"
  SHOW BUTTON: [View Existing Work Order] → navigates to WO lens
  SHOW OPTION: [Create Additional WO] → proceeds with new WO

ELSIF wo EXISTS AND wo.status IN ('completed', 'cancelled') THEN
  -- ALLOW: Previous WO closed, fault may have recurred
  SHOW INFO: "Previous work order {wo_number} was {status}"
  PROCEED with new WO creation

ELSE
  -- CREATE FIRST WO
  PROCEED with WO creation
END IF;
```

**Why This Matters**:
- Prevents accidental duplicate WOs for same fault
- Allows intentional additional WOs (recurrence, different approach)
- User has visibility into existing work before creating more

---

# SECTION AB: USER JOURNEY SCENARIOS

## Scenario 1: Critical Fault Discovery (Reduction: 15 steps → 6 steps)

**Context**:
- Engineer on deck hears unusual noise from generator
- Investigates, discovers fuel injector failure
- This is CRITICAL - generator offline affects ship operations

**Traditional Software Flow**:
```
1. Engineer opens laptop, navigates to "Fault Management"
2. Clicks "Report New Fault"
3. Modal opens with blank form (15 fields):
   - Equipment: [dropdown of 200+ items] ← must search
   - Title: [  ]
   - Description: [  ]
   - Severity: [dropdown]
   - Location: [dropdown]
   - Detected by: [dropdown of crew]
   - Detected at: [datetime picker]
   ... 8 more optional fields
4. Engineer fills form (3 minutes)
5. Submits, gets confirmation "Fault FLT-2026-001234 created"
6. Navigates to "Work Order" module
7. Clicks "Create New Work Order"
8. Searches for equipment again (dropdown of 200+)
9. Types title again
10. Selects priority based on memory of severity
11. Types description again
12. Searches for fault to link (dropdown, search "FLT-2026")
13. Selects fault
14. Submits WO
15. Goes back to Fault module to verify linkage
```
**Total**: 15 steps, ~8 minutes, data entered twice, context lost 3 times

**Celeste Fault Lens Flow**:
```
1. Engineer opens app, views Equipment Lens (Generator #1)
2. Clicks "Report Fault" (contextual action on equipment)
3. **Modal opens PRE-FILLED**:
   - Equipment: Generator #1 ✓ (from context, locked)
   - Title: [  ] → types "Fuel injector failure"
   - Severity: [dropdown] → selects "critical"
   - Description: [optional] → types "Unusual noise, then shutdown"
4. Submits (30 seconds)
5. **Fault Lens activates**, Critical Fault Modifier triggers:
   - Red badge on fault
   - Red banner: "🚨 Critical fault - requires immediate attention"
   - PRIMARY action: [Create Work Order] (red button)
6. Clicks [Create Work Order]
7. **Modal opens PRE-FILLED**:
   - Title: "Fuel injector failure" ✓ (from fault)
   - Equipment: Generator #1 ✓ (from fault)
   - Type: "corrective" ✓ (inferred)
   - Priority: "emergency" ✓ (mapped from critical)
   - Fault Link: FLT-2026-001234 ✓ (automatic)
   - Due Date: [  ] → optional, can set
8. Submits (15 seconds)
9. **Done**: Fault created, WO created, linkage automatic
```
**Total**: 6 steps (user actions), ~45 seconds, data entered once, context never lost

**Key Differences**:
- **Context FLOWS**: Equipment → Fault → WO (no re-selecting equipment)
- **Pre-fill INTELLIGENCE**: 5 fields auto-populated
- **Severity → Priority MAPPING**: critical fault → emergency WO priority
- **Auto-LINKING**: fault.work_order_id set automatically
- **90% TIME REDUCTION**: 8 minutes → 45 seconds

---

## Scenario 2: Fault Investigation & Resolution (Reduction: 12 steps → 7 steps)

**Context**:
- Engineer assigned to investigate fault FLT-2026-001234
- Needs to update status, add investigation notes, eventually resolve

**Traditional Software Flow**:
```
1. Engineer opens "Fault Management"
2. Searches for fault (FLT-2026-001234)
3. Clicks to view details
4. Reads current status: "Open"
5. Clicks "Edit Fault"
6. Changes status dropdown: "Investigating"
7. Saves (no place for notes in edit form)
8. Clicks "Add Note" (separate action)
9. Types investigation notes
10. Submits note
11. Later: Repeats steps 5-10 to change status to "Resolved"
12. Later: Repeats steps 5-7 to change status to "Closed"
```
**Total**: 12 steps for full lifecycle, status and notes are separate actions

**Celeste Fault Lens Flow**:
```
1. Engineer opens notification "Assigned: FLT-2026-001234"
2. **Fault Lens activates** directly (deep link)
3. Views fault details, current status: "Open"
4. Clicks [Update Status] (primary action for open faults)
5. **Modal opens**:
   - Current status: Open
   - New status: [dropdown] → selects "Investigating"
   - Notes (optional): → types "Initial inspection - fuel line clogged"
   - [✓] Auto-create note checkbox (checked by default)
6. Submits
7. **Status updated + Note created in single action**
8. Later: Returns to fault, clicks [Update Status]
   - Selects "Resolved"
   - Types "Replaced fuel filter, tested OK"
   - Submits → status + note in single action
9. Later: Returns, clicks [Update Status]
   - Selects "Closed"
   - Types "Verified fix with 24hr operation check"
   - Submits → workflow complete
```
**Total**: 7 steps for full lifecycle, status and notes combined

**Key Differences**:
- **COMBINED ACTION**: Status update + optional note in single modal
- **AUDIT TRAIL**: Every status change can have context
- **WORKFLOW GUIDANCE**: Dropdown shows valid next statuses
- **DEEP LINKING**: Open from notification directly to fault context

---

## Scenario 3: Fault Photo Documentation (Reduction: 8 steps → 4 steps)

**Context**:
- Deckhand discovers corrosion on deck railing
- Needs to document with photo for maintenance planning

**Traditional Software Flow**:
```
1. Deckhand takes photo with phone
2. Opens laptop, navigates to "Fault Management"
3. Clicks "Report Fault"
4. Fills fault details form
5. Saves fault
6. Searches for "Add Attachment" or "Upload" option
7. Selects file from phone (transferred somehow)
8. Uploads, adds description
```
**Total**: 8 steps, requires phone-to-laptop file transfer

**Celeste Fault Lens Flow**:
```
1. Deckhand opens Celeste app on phone
2. Views Equipment Lens (Deck Railing Section A-12)
3. Clicks "Report Fault"
4. **Modal includes camera button**:
   - Title: → types "Corrosion on railing"
   - Severity: → selects "medium"
   - [📷 Add Photo] → opens camera directly
   - Takes photo → auto-attaches
   - Description: [optional]
5. Submits → Fault + Photo created together
```
**Total**: 4 steps, photo taken and attached in same flow

**Key Differences**:
- **MOBILE-FIRST**: Camera integration in fault report modal
- **SINGLE FLOW**: Photo is part of fault creation, not separate action
- **NO FILE TRANSFER**: Camera → storage → attachment in one tap

---

# SECTION AC: MATHEMATICAL NORMALIZATION PATTERNS

## Abstract Entity-Condition-Intent Model

### Variables:

**x** (entity) = Fault being viewed
- Properties: id, title, severity, status, equipment_id, work_order_id, etc.

**y** (condition) = Current state of fault
- `y_critical_open`: severity=critical AND status=open (URGENT)
- `y_high_open`: severity=high AND status=open (URGENT)
- `y_investigating`: status=investigating (ACTIVE WORK)
- `y_resolved`: status=resolved (PENDING CLOSE)
- `y_closed`: status=closed (COMPLETE)
- `y_has_wo`: work_order_id IS NOT NULL
- `y_no_wo`: work_order_id IS NULL

**z** (intent) = User's inferred goal
- `z_escalate`: Create work order for fault
- `z_progress`: Update status in workflow
- `z_document`: Add notes/photos for investigation
- `z_close`: Complete fault lifecycle
- `z_archive`: Soft delete obsolete fault

**w** (source_context) = Where user came from
- `w_equipment`: from Equipment lens
- `w_dashboard`: from Critical Faults widget
- `w_work_order`: from linked Work Order
- `w_search`: from search results
- `w_notification`: from alert notification

### Pattern Formula:

```
f(x, y, z, w) → {
  primary_action,
  action_priority_order,
  pre_fill_values,
  badge_color,
  banner_message
}
```

### Example 1: Critical Fault, No Work Order

**Input**:
```python
x = Fault(
    id="FLT-2026-001234",
    title="Fuel injector failure",
    severity="critical",
    status="open",
    equipment_id="gen-1",
    work_order_id=None  # No WO yet
)
y = ["y_critical_open", "y_no_wo"]
z = "z_escalate"  # Inferred: critical fault needs WO
w = "w_dashboard"  # Came from critical faults widget
```

**Output**:
```python
f(x, y, z, w) = {
    "primary_action": "create_work_order_from_fault",
    "action_priority": [
        "create_work_order_from_fault",  # PRIMARY (critical urgency)
        "update_fault_status",  # SECONDARY
        "add_fault_note",
        "attach_file_to_fault",
        "view_fault_history",
        "archive_fault"  # Only for Captain/HoD
    ],
    "pre_fill": {
        "title": "Fuel injector failure",
        "equipment_id": "gen-1",
        "fault_id": "FLT-2026-001234",
        "type": "corrective",
        "priority": "emergency"  # critical → emergency
    },
    "badge_color": "red",
    "banner": "🚨 Critical fault - requires immediate work order"
}
```

### Example 2: Investigating Fault, Has Work Order

**Input**:
```python
x = Fault(
    id="FLT-2026-001235",
    title="Oil pressure warning",
    severity="medium",
    status="investigating",
    equipment_id="engine-2",
    work_order_id="WO-2026-0045"  # WO exists
)
y = ["y_investigating", "y_has_wo"]
z = "z_progress"  # Inferred: investigation mode
w = "w_work_order"  # Came from linked WO
```

**Output**:
```python
f(x, y, z, w) = {
    "primary_action": "add_fault_note",  # Investigation = document findings
    "action_priority": [
        "add_fault_note",  # PRIMARY (documenting investigation)
        "update_fault_status",  # SECONDARY (when ready to resolve)
        "attach_file_to_fault",
        "view_fault_history",
        "create_work_order_from_fault",  # Demoted (already has WO)
        "archive_fault"
    ],
    "pre_fill": {
        "note_type": "observation",  # Investigation mode
        "source_work_order_id": "WO-2026-0045"  # Context from WO
    },
    "badge_color": "yellow",
    "banner": None  # No urgent action needed
}
```

### Example 3: Resolved Fault, Pending Close

**Input**:
```python
x = Fault(
    id="FLT-2026-001236",
    title="Bilge pump malfunction",
    severity="high",
    status="resolved",
    equipment_id="bilge-pump-1",
    work_order_id="WO-2026-0046"
)
y = ["y_resolved", "y_has_wo"]
z = "z_close"  # Inferred: workflow completion
w = "w_notification"  # Came from "fault resolved" notification
```

**Output**:
```python
f(x, y, z, w) = {
    "primary_action": "update_fault_status",  # Close the fault
    "action_priority": [
        "update_fault_status",  # PRIMARY (close workflow)
        "add_fault_note",  # SECONDARY (resolution notes)
        "view_fault_history",
        "attach_file_to_fault",
        "create_work_order_from_fault",  # Hidden (resolved, has WO)
        "archive_fault"
    ],
    "pre_fill": {
        "suggested_next_status": "closed",
        "note_type": "resolution"  # Resolution context
    },
    "badge_color": "green",
    "banner": "Fault resolved - close to complete workflow"
}
```

### Debugging Use Case:

When engineer asks: "Why did 'Create Work Order' show as primary action?"

**Check variables**:
```python
# Scenario dump:
x.severity = "critical"
x.status = "open"
x.work_order_id = None
y = ["y_critical_open", "y_no_wo"]
z = "z_escalate"

# Formula evaluation:
if severity in ['critical', 'high'] and status == 'open' and work_order_id is None:
    primary = "create_work_order_from_fault"  # Critical Fault modifier
```

**Answer**: Critical Fault modifier (`y_critical_open` + `y_no_wo`) promoted "Create Work Order" to primary.

---

# SECTION A: Base Entity Lens Definition

## Entity Type
**Fault** (Equipment fault, defect, malfunction)

**Canonical Table**: `pms_faults`

## When This Lens Activates (Context Triggers)

**NOT**: "User clicks 'Faults' in navigation menu"

**INSTEAD**: User **focuses on a Fault entity** from ANY context:

1. **From Equipment View** (most common):
   - User viewing Equipment Lens (Generator #1)
   - Clicks "Report Fault" or "View Faults"
   - URL: `/faults/<uuid>?source=equipment:<equipment_uuid>`
   - Context preserved: equipment_id

2. **From Dashboard Critical Faults Widget**:
   - User sees "3 Critical Faults" on dashboard
   - Clicks fault from list
   - URL: `/faults/<uuid>?source=dashboard`
   - Context preserved: urgency awareness

3. **From Work Order View**:
   - User viewing WO detail
   - Clicks "Linked Fault: FLT-2026-001234"
   - URL: `/faults/<uuid>?source=wo:<work_order_uuid>`
   - Context preserved: work_order_id

4. **From Search Results**:
   - User searches "fuel injector"
   - Clicks fault from results
   - URL: `/faults/<uuid>?source=search&q=fuel+injector`
   - Context preserved: search query

5. **From Notification**:
   - User receives "Critical fault assigned to you"
   - Clicks notification
   - URL: `/faults/<uuid>?source=notification`
   - Context preserved: assignment context

**Key Point**: Lens activates IN CONTEXT, not as separate destination. URL encodes state for deep-linking, refresh, sharing.

**Celeste is one app** (apps.celeste7.ai). URL changes = browser state encoding, NOT navigation to another page.

## Core Purpose
View and manage equipment faults reported on the yacht, WITH CONTEXT FROM SOURCE VIEW, enabling rapid fault-to-work-order escalation.

---

# SECTION B: Schema Verification (Production DB Truth)

## Primary Table: `pms_faults`

**Source**: Production database query (2026-01-24)

**⚠️ SCHEMA VERIFIED**: This matches production database exactly.

**Columns** (19 total):

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | UUID | NOT NULL | gen_random_uuid() | PK |
| `yacht_id` | UUID | NOT NULL | | FK → `yacht_registry(id)`, RLS isolation key |
| `equipment_id` | UUID | NOT NULL | | FK → `pms_equipment(id)` ON DELETE CASCADE |
| `fault_code` | TEXT | YES | | Auto-generated (e.g., FLT-2026-001234) |
| `title` | TEXT | NOT NULL | | Display name (e.g., "Oil leak") |
| `description` | TEXT | YES | | Long-form description |
| `severity` | fault_severity | NOT NULL | 'medium' | Enum: low, medium, high, critical |
| `status` | TEXT | YES | 'open' | CHECK: open, investigating, resolved, closed |
| `detected_at` | TIMESTAMPTZ | NOT NULL | now() | When fault was detected |
| `resolved_at` | TIMESTAMPTZ | YES | | When fault was resolved |
| `resolved_by` | UUID | YES | | FK → auth.users(id) |
| `work_order_id` | UUID | YES | | FK → `pms_work_orders(id)` ON DELETE SET NULL |
| `metadata` | JSONB | YES | '{}' | Additional context |
| `created_at` | TIMESTAMPTZ | NOT NULL | now() | |
| `updated_at` | TIMESTAMPTZ | YES | | Auto-updated by trigger |
| `updated_by` | UUID | YES | | FK → auth.users(id) |
| `deleted_at` | TIMESTAMPTZ | YES | | ✅ SOFT DELETE EXISTS |
| `deleted_by` | UUID | YES | | FK → auth.users(id) |
| `deletion_reason` | TEXT | YES | | Why fault was archived |

**DB Truth Snapshot**:
- **Constraints**: PK(id), FK(yacht_id → yacht_registry), FK(equipment_id → pms_equipment ON DELETE CASCADE), FK(work_order_id → pms_work_orders ON DELETE SET NULL)
- **Indexes**:
  - yacht_id (RLS filtering)
  - equipment_id (equipment fault list)
  - fault_code (unique lookup)
  - detected_at DESC (recent faults first)
  - severity (critical fault queries)
  - status (workflow queries)
  - work_order_id (linked WO lookup)
- **RLS**: ENABLED - 3 policies (engineers can manage, users can view, service role full access)
- **Triggers**:
  - `no_hard_delete_faults` - prevents hard delete (enforces soft delete)
  - `set_updated_at_faults` - auto-updates updated_at timestamp
  - `trg_fault_insert_predictive`, `trg_fault_update_predictive` - notify predictive system

**Known Gap** (from CUMULATIVE_SCHEMA_MIGRATIONS.sql):
- `detected_by` column missing (who originally reported fault)
- Workaround: Use `created_by` from pms_audit_log
- Resolution: Migration 1.1 adds `detected_by UUID` column

---

## Related Table: `pms_notes`

**Source**: Production database query (2026-01-24)

**Purpose**: Generic notes table for fault notes, equipment notes, work order notes.

**Columns** (12 total):

| Column | Type | Nullable | Notes |
|--------|------|----------|-------|
| `id` | UUID | NOT NULL | PK |
| `yacht_id` | UUID | NOT NULL | FK → yacht_registry |
| `fault_id` | UUID | YES | FK → `pms_faults(id)` ON DELETE CASCADE |
| `equipment_id` | UUID | YES | FK → `pms_equipment(id)` |
| `work_order_id` | UUID | YES | FK → `pms_work_orders(id)` |
| `text` | TEXT | NOT NULL | Note content |
| `note_type` | note_type | NOT NULL | Enum: general, observation, warning, resolution, handover |
| `attachments` | JSONB | YES | '[]' - inline attachment refs |
| `metadata` | JSONB | YES | '{}' |
| `created_by` | UUID | NOT NULL | FK → auth.users(id) |
| `created_at` | TIMESTAMPTZ | NOT NULL | now() |
| `updated_at` | TIMESTAMPTZ | NOT NULL | now() |

**DB Truth Snapshot**:
- **Constraints**: PK(id), FK(fault_id → pms_faults ON DELETE CASCADE)
- **Indexes**: yacht_id, created_at DESC, fault_id
- **RLS**: ENABLED

**Why Generic Table**:
- Same note structure for faults, equipment, WOs
- FK determines which entity note belongs to
- Only one FK populated per note (fault_id OR equipment_id OR work_order_id)

---

## Related Table: `pms_attachments`

**Source**: Production database query (2026-01-24)

**Purpose**: Generic attachments table for fault photos, equipment docs, WO attachments.

**Columns** (21 total):

| Column | Type | Nullable | Notes |
|--------|------|----------|-------|
| `id` | UUID | NOT NULL | PK |
| `yacht_id` | UUID | NOT NULL | FK → yacht_registry |
| `entity_type` | VARCHAR | NOT NULL | CHECK: 'fault', 'work_order', 'equipment', 'checklist_item', 'note', 'handover', 'purchase_order' |
| `entity_id` | UUID | NOT NULL | ID of linked entity (fault, WO, etc.) |
| `filename` | VARCHAR | NOT NULL | Storage filename |
| `original_filename` | VARCHAR | YES | User's original filename |
| `mime_type` | VARCHAR | NOT NULL | File type |
| `file_size` | INTEGER | YES | Size in bytes |
| `storage_path` | TEXT | NOT NULL | Cloud storage path |
| `width` | INTEGER | YES | For images |
| `height` | INTEGER | YES | For images |
| `thumbnail_path` | TEXT | YES | Thumbnail for preview |
| `description` | TEXT | YES | User description |
| `tags` | TEXT[] | YES | Array of tags |
| `metadata` | JSONB | YES | '{}' |
| `uploaded_by` | UUID | NOT NULL | FK → auth.users(id) |
| `uploaded_at` | TIMESTAMPTZ | NOT NULL | now() |
| `created_at` | TIMESTAMPTZ | NOT NULL | now() |
| `updated_at` | TIMESTAMPTZ | YES | |
| `deleted_at` | TIMESTAMPTZ | YES | ✅ SOFT DELETE EXISTS |
| `deleted_by` | UUID | YES | |
| `deletion_reason` | TEXT | YES | |

**DB Truth Snapshot**:
- **Constraints**: PK(id), CHECK(entity_type IN ('fault', 'work_order', ...))
- **Indexes**: (entity_type, entity_id), mime_type
- **RLS**: ENABLED

**Usage for Faults**:
```sql
-- Get all attachments for a fault:
SELECT * FROM pms_attachments
WHERE entity_type = 'fault'
  AND entity_id = :fault_id
  AND deleted_at IS NULL
ORDER BY uploaded_at DESC;
```

---

## Related Table: `pms_work_orders`

**Source**: Production database query (2026-01-24)

**Purpose**: Work orders, including corrective WOs created from faults.

**Key Columns** (29 total - abbreviated):

| Column | Type | Nullable | Notes |
|--------|------|----------|-------|
| `id` | UUID | NOT NULL | PK |
| `yacht_id` | UUID | NOT NULL | FK → yacht_registry |
| `fault_id` | UUID | YES | FK → `pms_faults(id)` ON DELETE SET NULL |
| `equipment_id` | UUID | YES | FK → `pms_equipment(id)` |
| `title` | TEXT | NOT NULL | |
| `description` | TEXT | YES | |
| `type` | work_order_type | NOT NULL | Enum: scheduled, corrective, unplanned, preventive |
| `priority` | work_order_priority | NOT NULL | Enum: routine, important, critical, emergency |
| `status` | work_order_status | NOT NULL | Enum: planned, in_progress, completed, deferred, cancelled |
| `wo_number` | TEXT | YES | Auto-generated (e.g., WO-2026-0045) |
| `due_date` | DATE | YES | |
| `assigned_to` | UUID | YES | FK → auth.users(id) |
| `created_by` | UUID | NOT NULL | FK → auth.users(id) |
| `created_at` | TIMESTAMPTZ | NOT NULL | now() |
| `deleted_at` | TIMESTAMPTZ | YES | ✅ SOFT DELETE EXISTS |

**Fault → Work Order Linkage**:
- `pms_faults.work_order_id` → references WO created for this fault
- `pms_work_orders.fault_id` → references fault that triggered this WO
- **Bidirectional**: Both sides reference each other for easy traversal

**Severity → Priority Mapping**:
```python
SEVERITY_TO_PRIORITY = {
    'critical': 'emergency',
    'high': 'critical',
    'medium': 'important',
    'low': 'routine'
}
```

---

## Related Table: `pms_audit_log`

**Source**: Production database query (2026-01-24)

**Purpose**: Audit trail for all mutations, including signature capture.

**Key Columns**:

| Column | Type | Nullable | Notes |
|--------|------|----------|-------|
| `id` | UUID | NOT NULL | PK |
| `yacht_id` | UUID | NOT NULL | |
| `entity_type` | TEXT | NOT NULL | 'fault', 'work_order', etc. |
| `entity_id` | UUID | NOT NULL | ID of affected entity |
| `action` | TEXT | NOT NULL | Action name (e.g., 'archive_fault') |
| `user_id` | UUID | NOT NULL | FK → auth.users(id) |
| `old_values` | JSONB | YES | State before change |
| `new_values` | JSONB | NOT NULL | State after change |
| `signature` | JSONB | YES | ✅ EXISTS - Digital signature for high-risk actions |
| `metadata` | JSONB | YES | Session context |
| `created_at` | TIMESTAMPTZ | NOT NULL | |

**Signature Format**:
```json
{
  "signature_data": "base64-encoded-image",
  "signed_by": "uuid",
  "signed_at": "2026-01-24T14:30:00Z",
  "role": "captain",
  "device_id": "ipad_bridge"
}
```

---

## Yacht Rank Hierarchy

**Source**: docs/roles/ranks.md

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

# SECTION C: Role Permissions (Simple Tier Model)

## Everyone (All Crew)

**Can Execute**:
- `report_fault` - Report new equipment fault
- `add_fault_note` - Add observation/investigation notes
- `attach_file_to_fault` - Upload photo/document to fault

**Can View**:
- All faults (filtered by yacht_id)
- Fault notes
- Fault attachments
- Fault history

**Reasoning**: Any crew member might discover a fault. Low friction for reporting = better safety.

---

## Engineers + Deck + Interior (Department Crew)

**Inherits**: All crew permissions +

**Can Execute**:
- `update_fault_status` - Change fault status through workflow
- `create_work_order_from_fault` - Generate corrective WO

**RLS Policy** (from DB):
- "Engineers can manage faults" - chief_engineer, eto, deck, interior roles
- "Users can view faults" - all crew via yacht_id match

**Reasoning**: Department crew assigned to fix issues need to update status and escalate to WOs.

---

## Restricted (Captain + HoDs + Purser)

**Can Execute**:
- `archive_fault` - Soft delete fault (30-day undo window)
- **SIGNATURE REQUIRED** for archive action

**Reasoning**: Archiving removes fault from active view. Requires authority + signature for accountability.

---

## Audit Requirement (All Mutations)

**Logged in `pms_audit_log`**:
- user_id
- session_id
- IP address
- timestamp
- old_values (JSONB)
- new_values (JSONB)
- metadata (device_type, user_agent, etc.)

**For Signature-Required Actions**:
- signature (JSONB) containing:
  - signature_data (base64 image)
  - signed_by (UUID)
  - signed_at (timestamp)
  - role (captain/hod/purser)
  - device_id (e.g., "ipad_bridge")

---

# SECTION D: Default Display Fields (NOT Actions)

**Always Visible** (context information, not user-initiated operations):

1. **Fault code** - Auto-generated identifier (e.g., FLT-2026-001234)
2. **Title** - Display name (e.g., "Oil leak")
3. **Description** - Long-form details
4. **Severity** - With color badge:
   - **Low**: Gray badge
   - **Medium**: Yellow badge
   - **High**: Orange badge
   - **Critical**: Red badge
5. **Status** - With color badge:
   - **Open**: Red badge
   - **Investigating**: Yellow badge
   - **Resolved**: Green badge
   - **Closed**: Gray badge
6. **Equipment name** - Linked to equipment lens (clickable)
7. **Detected at** - Timestamp when fault was discovered
8. **Resolved at** - If resolved (timestamp)
9. **Resolved by** - If resolved (user name)
10. **Linked work order** - If exists (clickable link to WO lens)
11. **Created by / Created at** - Audit info
12. **Last updated** - Most recent change timestamp

**Why These Are NOT Actions**:
- User doesn't "click" to "show severity"
- These fields are ALWAYS displayed as context
- Default display = static context, not dynamic choice

---

# SECTION E: Fault Micro-Actions (Exactly 6)

## Why Exactly 6 Actions?

**Cognitive Load** (Miller's Law):
- Human working memory: 7±2 items
- 6 actions = comfortable for scanning, choosing
- More than 6 = overwhelming, slower decisions

**Outcome Focus**:
- Each action maps to a distinct user OUTCOME (not feature)
- If you need more → you're grouping wrong

---

## 1. `report_fault`

**Label**: "Report Fault"

**User Outcome**: Create a new equipment fault record to initiate investigation/repair

**Why User Takes This Action**:
- Discovered equipment malfunction
- Observed abnormal behavior (noise, smell, leak)
- Preventive observation (minor issue before failure)

**Writes to**:
- `pms_faults` (INSERT new row)
- `pms_audit_log` (INSERT audit record)

**Trigger Logic** (when to show as PRIMARY):
```python
# This action appears in EQUIPMENT lens, not Fault lens
# (Can't report fault from fault detail view)
if current_lens == 'equipment':
    return VISIBLE  # Always available from equipment
```

**Signature Required**: NO (all crew can report)

**Modal**: `ReportFaultModal.tsx`

**Fields**:

| Field | Type | Classification | Pre-fill Logic |
|-------|------|----------------|----------------|
| `equipment_id` | UUID | AUTOMATIC | From equipment context (locked) |
| `title` | TEXT | REQUIRED | User enters |
| `severity` | ENUM | REQUIRED | Dropdown: low, medium, high, critical |
| `description` | TEXT | OPTIONAL | User enters |
| `fault_code` | TEXT | AUTOMATIC | Auto-generated if blank |
| `detected_at` | TIMESTAMPTZ | AUTOMATIC | NOW() (or user can override) |
| `status` | TEXT | AUTOMATIC | 'open' |
| `yacht_id` | UUID | AUTOMATIC | auth.user_yacht_id() |
| `metadata` | JSONB | AUTOMATIC | {session_id, ip_address, device_type} |

**Example Flow** (from Equipment lens):
```
1. User viewing Equipment Lens (Hydraulic Pump #2)
2. Clicks [Report Fault]
3. Modal opens:
   - Equipment: "Hydraulic Pump #2" ✓ (locked, from context)
   - Title: [  ] → user types "Oil leak at seal"
   - Severity: [dropdown] → user selects "high"
   - Description: [optional] → user types details
4. User clicks Submit
5. Backend:
   - INSERT into pms_faults
   - fault_code auto-generated (FLT-2026-001234)
   - INSERT into pms_audit_log
6. Success → Fault Lens activates for new fault
7. Critical Fault Modifier triggers (severity=high)
```

---

## 2. `create_work_order_from_fault`

**Label**: "Create Work Order"

**User Outcome**: Generate corrective work order to fix the fault

**Why User Takes This Action**:
- Fault needs repair work scheduled
- Need to assign crew member to fix
- Need to track parts/time for repair

**Writes to**:
- `pms_work_orders` (INSERT new row)
- `pms_faults.work_order_id` (UPDATE, link to new WO)
- `pms_audit_log` (INSERT audit record)

**Trigger Logic** (when to show as PRIMARY):
```python
if fault.severity in ['critical', 'high'] and fault.status == 'open' and fault.work_order_id is None:
    return PRIMARY  # Critical Fault Modifier
else:
    return SECONDARY
```

**Signature Required**: NO (engineers can create WOs)

**Modal**: `CreateWorkOrderFromFaultModal.tsx`

**Fields**:

| Field | Type | Classification | Pre-fill Logic |
|-------|------|----------------|----------------|
| `fault_id` | UUID | AUTOMATIC | From current fault |
| `equipment_id` | UUID | AUTOMATIC | From fault.equipment_id |
| `title` | TEXT | DERIVED | From fault.title (user can edit) |
| `description` | TEXT | OPTIONAL | Pre-filled: "Corrective action for fault: {fault_code}" |
| `type` | ENUM | AUTOMATIC | 'corrective' |
| `priority` | ENUM | DERIVED | Mapped from fault.severity |
| `due_date` | DATE | OPTIONAL | User can set |
| `assigned_to` | UUID | OPTIONAL | Dropdown of crew |
| `wo_number` | TEXT | AUTOMATIC | Trigger-generated |
| `status` | TEXT | AUTOMATIC | 'planned' |
| `yacht_id` | UUID | AUTOMATIC | auth.user_yacht_id() |
| `created_by` | UUID | AUTOMATIC | auth.uid() |

**Priority Mapping**:
```python
SEVERITY_TO_PRIORITY = {
    'critical': 'emergency',
    'high': 'critical',
    'medium': 'important',
    'low': 'routine'
}
```

**Example Flow**:
```
1. User viewing Fault Lens (FLT-2026-001234, severity=critical)
2. Banner: "🚨 Critical fault - requires immediate work order"
3. Primary action: [Create Work Order] (red button)
4. Clicks button
5. Modal opens PRE-FILLED:
   - Title: "Oil leak at seal" ✓ (from fault)
   - Equipment: "Hydraulic Pump #2" ✓ (from fault, locked)
   - Type: "corrective" ✓ (auto)
   - Priority: "emergency" ✓ (critical → emergency)
   - Due Date: [  ] → optional
   - Assign To: [dropdown] → optional
6. User clicks Submit
7. Backend:
   - INSERT into pms_work_orders
   - UPDATE pms_faults SET work_order_id = :new_wo_id
   - INSERT into pms_audit_log
8. Success: "Work order WO-2026-0045 created"
9. "Create Work Order" button hidden (WO now exists)
```

**Edge Case: WO Already Exists**
```
1. User clicks [Create Work Order]
2. Backend checks: fault.work_order_id IS NOT NULL
3. Modal shows warning:
   "Work order WO-2026-0045 already exists for this fault (status: in_progress)"
   [View Existing WO] [Create Additional WO]
4. User can view existing OR create new (for recurrence)
```

---

## 3. `update_fault_status`

**Label**: "Update Status"

**User Outcome**: Progress fault through investigation/resolution workflow

**Why User Takes This Action**:
- Started investigating fault
- Completed repair, fault resolved
- Verified fix, closing fault

**Writes to**:
- `pms_faults.status` (UPDATE)
- `pms_faults.updated_at`, `updated_by` (UPDATE)
- `pms_faults.resolved_at`, `resolved_by` (if status='resolved')
- `pms_notes` (INSERT if notes provided)
- `pms_audit_log` (INSERT audit record)

**Workflow Progression**:
```
open → investigating → resolved → closed
       ↑_____________________________|
       (can reopen resolved faults if issue recurs)
```

**Trigger Logic** (when to show as PRIMARY):
```python
if fault.status == 'investigating':
    return PRIMARY  # Likely to progress to resolved
elif fault.status == 'resolved':
    return PRIMARY  # Likely to close
else:
    return SECONDARY
```

**Signature Required**: NO

**Modal**: `UpdateFaultStatusModal.tsx`

**Fields**:

| Field | Type | Classification | Pre-fill Logic |
|-------|------|----------------|----------------|
| `status` | ENUM | REQUIRED | Dropdown showing valid next states |
| `notes` | TEXT | OPTIONAL | Status change notes |
| `create_note` | BOOLEAN | OPTIONAL | Default: true (auto-create note with status change) |

**Valid Status Transitions**:
```python
VALID_TRANSITIONS = {
    'open': ['investigating'],
    'investigating': ['resolved', 'open'],  # Can revert if not the issue
    'resolved': ['closed', 'open'],  # Can reopen if recurs
    'closed': ['open']  # Can reopen historical issues
}
```

**Example Flow**:
```
1. User viewing Fault Lens (FLT-2026-001234, status=investigating)
2. Clicks [Update Status]
3. Modal opens:
   - Current: "Investigating"
   - New Status: [dropdown: Resolved, Open] → selects "Resolved"
   - Notes: [  ] → types "Replaced seal, tested OK"
   - [✓] Create note with status change
4. User clicks Submit
5. Backend:
   - UPDATE pms_faults SET status='resolved', resolved_at=NOW(), resolved_by=auth.uid()
   - INSERT pms_notes (text="Replaced seal, tested OK", note_type='resolution')
   - INSERT pms_audit_log
6. Success: "Status updated to Resolved"
```

---

## 4. `add_fault_note`

**Label**: "Add Note"

**User Outcome**: Document observation, investigation finding, or resolution details

**Why User Takes This Action**:
- Recording investigation observations
- Documenting attempted fixes
- Adding resolution notes for future reference

**Writes to**:
- `pms_notes` (INSERT new row)
- `pms_audit_log` (INSERT audit record)

**Trigger Logic** (when to show as PRIMARY):
```python
if fault.status == 'investigating':
    return PRIMARY  # Investigation mode = document findings
else:
    return SECONDARY
```

**Signature Required**: NO

**Modal**: `AddFaultNoteModal.tsx`

**Fields**:

| Field | Type | Classification | Pre-fill Logic |
|-------|------|----------------|----------------|
| `fault_id` | UUID | AUTOMATIC | From current fault |
| `text` | TEXT | REQUIRED | User enters |
| `note_type` | ENUM | OPTIONAL | Dropdown: general, observation, warning, resolution, handover. Default based on fault status |
| `attachments` | JSONB | OPTIONAL | Inline attachment refs |
| `yacht_id` | UUID | AUTOMATIC | auth.user_yacht_id() |
| `created_by` | UUID | AUTOMATIC | auth.uid() |

**Note Type Default Logic**:
```python
def default_note_type(fault_status):
    if fault_status == 'open':
        return 'observation'
    elif fault_status == 'investigating':
        return 'observation'
    elif fault_status == 'resolved':
        return 'resolution'
    else:
        return 'general'
```

**Example Flow**:
```
1. User viewing Fault Lens (FLT-2026-001234, status=investigating)
2. Clicks [Add Note]
3. Modal opens:
   - Note: [  ] → types "Checked hydraulic pressure, reading normal"
   - Type: [dropdown] → "observation" (default)
4. User clicks Submit
5. Backend:
   - INSERT pms_notes
   - INSERT pms_audit_log
6. Success: Note added, appears in fault note timeline
```

---

## 5. `attach_file_to_fault`

**Label**: "Attach Photo/File"

**User Outcome**: Upload visual evidence or documentation for the fault

**Why User Takes This Action**:
- Photo of damage/defect
- Screenshot of error message
- Maintenance manual excerpt
- Vendor documentation

**Writes to**:
- `pms_attachments` (INSERT new row)
- `pms_audit_log` (INSERT audit record)

**Trigger Logic**:
```python
return SECONDARY  # Always secondary, photo is supporting evidence
```

**Signature Required**: NO

**Modal**: File upload modal (camera integration on mobile)

**Fields**:

| Field | Type | Classification | Pre-fill Logic |
|-------|------|----------------|----------------|
| `entity_type` | TEXT | AUTOMATIC | 'fault' |
| `entity_id` | UUID | AUTOMATIC | From current fault |
| `file` | FILE | REQUIRED | User uploads |
| `description` | TEXT | OPTIONAL | User enters |
| `tags` | TEXT[] | OPTIONAL | User can add tags |
| `yacht_id` | UUID | AUTOMATIC | auth.user_yacht_id() |
| `uploaded_by` | UUID | AUTOMATIC | auth.uid() |

**Mobile Camera Integration**:
```
[📷 Take Photo] - Opens device camera
[📁 Upload File] - Opens file picker
```

**Example Flow**:
```
1. User viewing Fault Lens (FLT-2026-001234)
2. Clicks [Attach Photo/File]
3. Modal opens:
   - [📷 Take Photo] [📁 Upload File]
   - User clicks [📷 Take Photo]
   - Camera opens, user takes photo
   - Photo preview shows
   - Description: [  ] → types "Oil leak visible at seal joint"
4. User clicks Upload
5. Backend:
   - Upload file to storage
   - INSERT pms_attachments (entity_type='fault', entity_id=fault.id)
   - INSERT pms_audit_log
6. Success: Photo appears in fault attachments gallery
```

---

## 6. `archive_fault`

**Label**: "Archive Fault"

**User Outcome**: Remove obsolete fault from active view (soft delete with undo)

**Why User Takes This Action**:
- Fault was reported in error
- Equipment decommissioned, fault no longer relevant
- Duplicate fault record
- Historical cleanup

**Writes to**:
- `pms_faults.deleted_at`, `deleted_by`, `deletion_reason` (UPDATE)
- `pms_audit_log` (INSERT with signature)

**Trigger Logic**:
```python
return SECONDARY  # Always last action, rarely used
# Only visible if user has permission (Captain/HoD/Purser)
```

**Signature Required**: **YES**

**Permission**: Captain, HoD, Purser only

**Modal**: `ArchiveFaultModal.tsx` with signature capture

**Fields**:

| Field | Type | Classification | Pre-fill Logic |
|-------|------|----------------|----------------|
| `deletion_reason` | TEXT | REQUIRED | Dropdown: reported_in_error, equipment_decommissioned, duplicate, other |
| `notes` | TEXT | OPTIONAL | Additional context |
| `signature` | SIGNATURE | REQUIRED | Signature pad capture |

**Undo Window**: 30 days (fault remains in DB, can be restored)

**Example Flow**:
```
1. User (Captain) viewing Fault Lens (FLT-2026-001234)
2. Clicks [Archive Fault] (only visible to Captain/HoD/Purser)
3. Modal opens:
   - Reason: [dropdown] → selects "Duplicate"
   - Notes: [  ] → types "Same as FLT-2026-001233"
   - Signature: [signature pad] → user signs
4. User clicks Archive
5. Backend:
   - Verify role (Captain/HoD/Purser)
   - UPDATE pms_faults SET deleted_at=NOW(), deleted_by=auth.uid(), deletion_reason='duplicate'
   - INSERT pms_audit_log WITH signature data
6. Success: "Fault archived. Can be restored within 30 days."
7. Fault hidden from active views (deleted_at IS NOT NULL filter)
```

**Trigger Prevention**:
```sql
-- Trigger: no_hard_delete_faults
-- Prevents: DELETE FROM pms_faults WHERE id = :id
-- Forces: UPDATE pms_faults SET deleted_at = NOW() instead
RAISE EXCEPTION 'Hard delete not allowed on pms_faults. Use soft delete.'
```

---

# SECTION F: Related Button Contract

**Related** (top-right button in fault detail):
- FK joins (equipment, work order, notes)
- Vector search seeded from entity fields only: `title`, `description`, `fault_code`, `equipment.name`
- **Never user query**. **No predictive logic**.

**FK-Based Relations**:
1. **Equipment** → FK join on `pms_faults.equipment_id` → Equipment Lens
2. **Linked Work Order** → FK join on `pms_faults.work_order_id` → Work Order Lens
3. **Fault Notes** → FK join on `pms_notes.fault_id` → Note list
4. **Fault Attachments** → `pms_attachments WHERE entity_type='fault' AND entity_id=fault.id`

**Vector Search Relations**:
5. **Related Manuals** → Vector search using `title + description` → `documents` + `search_chunks`
6. **Similar Faults** → Vector search using `title + description + equipment.name` → other faults

**Examples**:
```
Related button clicked:
├── Equipment: "Hydraulic Pump #2" → [View Equipment]
├── Linked WO: "WO-2026-0045" → [View Work Order]
├── Notes (3) → [View All Notes]
├── Photos (2) → [View Gallery]
├── Related Manuals → Vector search results
└── Similar Faults → "FLT-2026-001100: Hydraulic leak (resolved)"
```

---

# SECTION G: Situation Modifier: Critical Fault Active

## Trigger Condition (Simple)

```sql
severity IN ('critical', 'high')
AND status IN ('open', 'investigating')
AND work_order_id IS NULL  -- No WO created yet
```

## What Changes When Modifier Active

### A) Visual Indicators

**Severity Badge**:
- **Low**: Gray badge
- **Medium**: Yellow badge
- **High**: Orange badge
- **Critical**: Red badge, pulsing animation

**Status Badge**:
- **Open**: Red badge
- **Investigating**: Yellow badge
- **Resolved**: Green badge
- **Closed**: Gray badge

### B) Action Reordering

**Before Modifier** (normal state):
```
PRIMARY ACTIONS:
  [Update Status] ← workflow progression

SECONDARY ACTIONS:
  [Add Note]
  [Create Work Order]
  [Attach Photo]
```

**After Modifier** (critical/high + open + no WO):
```
PRIMARY ACTIONS:
  [Create Work Order] ← PROMOTED (orange/red button)

SECONDARY ACTIONS:
  [Update Status] ← DEMOTED
  [Add Note]
  [Attach Photo]
```

### C) ONE Dismissible Banner

**Critical (severity=critical)**:
```
🚨 Critical fault - requires immediate work order
[Create Work Order] [Dismiss]
```

**High (severity=high)**:
```
⚠️ High severity fault - create work order to resolve
[Create Work Order] [Dismiss]
```

**Banner Behavior**:
- Dismissible: YES (user preference saved in localStorage)
- Re-shows if: fault status changes, or new session
- Quote from spec: "otherwise we are just annoying"

### D) Pre-fill Enhancement

When user clicks [Create Work Order] during modifier:
```javascript
{
  title: fault.title,
  equipment_id: fault.equipment_id,
  fault_id: fault.id,
  type: "corrective",
  priority: fault.severity === 'critical' ? 'emergency' : 'critical',
  description: `Corrective action for fault: ${fault.fault_code}`,
  due_date: null,  // User sets based on urgency
  assigned_to: null  // User assigns
}
```

---

# SECTION H: Edge Cases

## 1. Work Order Already Exists for Fault

**Scenario**: User tries to create WO, but `fault.work_order_id` is already populated.

**Behavior**:
```
1. User clicks [Create Work Order]
2. Modal checks: fault.work_order_id IS NOT NULL
3. Modal shows warning:
   "Work order already exists for this fault:"
   "WO-2026-0045 (Status: In Progress)"

   [View Existing Work Order] - navigates to WO lens
   [Create Additional Work Order] - proceeds with new WO

4. If user clicks "Create Additional":
   - New WO created
   - Both fault.work_order_id AND new WO link to fault
   - Warning logged in audit: "Additional WO created for fault with existing WO"
```

**Why Allow Additional WOs**:
- Fault may require multiple work orders (different aspects)
- Original WO may have been cancelled
- Fault may have recurred after original WO completed

## 2. Archive Collision (Soft Delete)

**Scenario**: User A viewing fault. User B archives fault. User A tries action.

**Behavior**:
```
1. User A viewing Fault Lens (FLT-2026-001234)
2. User B archives same fault (in another session)
3. User A clicks [Update Status]
4. Backend check: fault.deleted_at IS NOT NULL
5. Error response: "Fault archived by {user} at {time}"
6. Modal shows:
   "This fault has been archived by Smith at 2026-01-24 14:30"
   [OK] - closes modal
   [Restore Fault] - only if User A has permission (Captain/HoD/Purser)
```

**Restore Logic** (if user clicks Restore):
```sql
UPDATE pms_faults
SET deleted_at = NULL,
    deleted_by = NULL,
    deletion_reason = NULL,
    updated_at = NOW(),
    updated_by = auth.uid()
WHERE id = :fault_id;

-- Insert audit log for restore action
INSERT INTO pms_audit_log (...) VALUES (
  'restore_fault',
  old_values: {deleted_at: '2026-01-24...', deleted_by: '...'},
  new_values: {deleted_at: null},
  signature: :signature_data  -- Required for restore
);
```

## 3. Equipment Deleted

**Scenario**: Equipment associated with fault is decommissioned (soft deleted).

**Behavior**:
- Fault remains visible (equipment_id FK is ON DELETE CASCADE, but soft delete doesn't trigger this)
- Equipment name shown as "Hydraulic Pump #2 (Decommissioned)"
- "View Equipment" link shows archived equipment view
- Suggest archiving related faults

## 4. Concurrent Status Update

**Scenario**: Two users update same fault status simultaneously.

**Behavior** (optimistic locking):
```sql
UPDATE pms_faults
SET status = :new_status,
    updated_at = NOW(),
    updated_by = auth.uid()
WHERE id = :fault_id
  AND updated_at = :expected_updated_at  -- Optimistic lock check

-- If 0 rows updated:
RAISE 'Fault was modified by another user. Please refresh and try again.'
```

---

# SECTION I: Blockers

## BLOCKER 1: No `detected_by` Column
- **Impact**: Cannot track who originally reported fault (vs who created the DB record)
- **Current State**: Column does NOT exist in production
- **Workaround**: Use `created_by` from audit log (first INSERT action for this fault)
- **Resolution**: Migration 1.1 in CUMULATIVE_SCHEMA_MIGRATIONS.sql adds `detected_by UUID` column
- **Status**: Planned for Phase 2 migration

## BLOCKER 2: Missing Actions in action_registry.py
- **Impact**: `update_fault_status` and `archive_fault` not in Python registry
- **Current State**: Registry has view/note/photo actions, missing status/archive
- **Workaround**: None (handlers need to be created)
- **Resolution**: Add missing actions to action_registry.py per this lens spec
- **Status**: Planned for Phase 2 implementation

## BLOCKER 3: Status is TEXT, Not Enum
- **Impact**: `pms_faults.status` is TEXT with CHECK constraint, not PostgreSQL enum
- **Current State**: Works correctly, CHECK constraint enforces valid values
- **Workaround**: None needed - TEXT with CHECK is valid pattern
- **Resolution**: No migration needed
- **Status**: Not a blocker, just documentation note

---

# SECTION J: Summary

**Entity Lens**: Fault
**Primary Table**: `pms_faults` (19 columns, production DB verified)
**Related Tables**: `pms_notes` (fault notes), `pms_attachments` (fault photos), `pms_work_orders` (linked WO), `pms_audit_log` (audit trail)
**Situation Modifiers**: 1 (Critical Fault Active - severity + status + no WO check)
**Micro-Actions**: 6 (report_fault, create_work_order_from_fault, update_fault_status, add_fault_note, attach_file_to_fault, archive_fault)
**Default Display Fields**: 12 (fault code, title, severity badge, status badge, equipment link, timestamps, etc. - NOT actions)
**Blockers**: 2 (detected_by column, missing registry actions)

**Key Principles**:
- ✅ Production DB is truth (NOT migrations)
- ✅ SPA route state (`/faults/<uuid>`) - no page reload
- ✅ Context flows with user (equipment → fault → WO)
- ✅ Related = FK joins + vector from entity fields only (never user query)
- ✅ Generic tables work: pms_notes + pms_attachments (fault-specific tables don't exist)
- ✅ Permissions: All crew can report/note/attach, engineers can manage status/WO, Captain/HoD can archive (with signature)
- ✅ Critical Fault modifier: severity + status + no WO check, red/orange badge + button promotion + ONE dismissible banner
- ✅ Archive (soft delete) enforced by trigger. Hard delete blocked.
- ✅ Severity → Priority mapping: critical→emergency, high→critical, medium→important, low→routine

**User Journey Reductions**:
- Critical fault discovery: 15 steps → 6 steps (60% reduction)
- Fault investigation lifecycle: 12 steps → 7 steps (42% reduction)
- Photo documentation: 8 steps → 4 steps (50% reduction)

**Mathematical Normalization**:
- Variables: x (fault), y (state conditions), z (intent), w (source context)
- Formula: f(x, y, z, w) → {primary_action, pre_fill, badge, banner}
- Debugging: Check variables to explain why action was promoted/demoted

---

**STOP. Awaiting review before proceeding to additional lenses.**
