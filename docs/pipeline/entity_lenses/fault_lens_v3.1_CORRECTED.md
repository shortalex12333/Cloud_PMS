# Entity Lens: Fault (CORRECTED)

**Status**: v3.1 - WO-First Doctrine Applied
**Last Updated**: 2026-01-24
**Schema Source**: Production Supabase Database
**Revision Note**: Corrected from v3 based on architectural review

---

## CRITICAL INVARIANTS (LOCKED)

### Invariant 1: Work Order is Primary, Fault is Metadata
```
Crew mental model:
- "Fix hydraulic pump" → Work Order
- "Investigate overheating" → Work Order
- "Repair leak" → Work Order

Fault is NOT a destination.
Fault is a context flag / subtype within Work Order.
```

**Canonical Rule**:
- `report_fault` ≠ default action
- `create_work_order` = default outcome
- Fault record auto-created ONLY IF:
  - User explicitly queries "report fault"
  - OR system infers fault semantics (breakdown, abnormal condition)

### Invariant 2: Query-Only Activation
```
Celeste has:
❌ No dashboards
❌ No fault list pages
❌ No navigation buttons
❌ No modules
❌ No ambient UI

Celeste has:
✅ One search bar
✅ One SPA
✅ One ledger (history + notifications)
✅ Query-driven progression ONLY
```

**Canonical Rule**:
- Nothing appears unless the user queried it
- No buttons. No menus. No ambient UI.
- Lens activates ONLY when query resolves to entity focus

### Invariant 3: Severity = Backend Signal Only
```
❌ "Critical" badge dominating UI
❌ Banners lecturing user about urgency
❌ SaaS theatre

✅ Severity influences backend behavior:
   - Priority pre-fill
   - SLA timers
   - Notification urgency
   - Ledger prominence

User already knows it's critical. Don't tell them.
```

**Banner Rule**:
- Banners ONLY when new information is introduced
- Example: "Already has an active work order"
- NOT for obvious states like "this is critical"

### Invariant 4: Storage Bucket Mapping (Explicit)
```
documents         → Read-only (yacht→cloud ingestion, delete HoD+ only)
pms-discrepancy-photos → Fault/discrepancy photos
pms-receiving-images   → WO receiving photos
pms-part-photos        → Part/inventory photos
pms-label-pdfs         → Generated label PDFs
pms-finance-documents  → Finance attachments
```

**Canonical Rule**:
- Attachment action must map → bucket deterministically
- No "magic upload destination"
- `documents` bucket is NEVER written to by user actions

---

# SECTION 0: UX VISION (CORRECTED)

## The Correct Mental Model

### What Crew Actually Do:
```
Engineer discovers hydraulic pump leaking
→ Opens Celeste app
→ Types in search: "Hydraulic Pump #2 oil leak"
→ Search resolves:
   - Equipment: Hydraulic Pump #2
   - Condition: oil leak (fault semantics)
   - Intent: corrective action
→ Primary action returned: [Create Work Order]
→ Work Order modal opens PRE-FILLED:
   - Equipment: Hydraulic Pump #2 ✓
   - Type: "breakdown" ✓ (inferred from "leak")
   - Title: "Oil leak" ✓
→ User completes WO creation
→ Fault record auto-created as metadata (if breakdown/fault type)
```

### What Crew Do NOT Do:
```
❌ Navigate to "Fault Management"
❌ Click "Report Fault" button
❌ Create fault, then create WO, then link them
❌ See "Critical Fault!" banners everywhere
```

## Query-Driven Progression

**All journeys start from query:**

| User Query | Search Resolves | Primary Action |
|------------|-----------------|----------------|
| "Hydraulic Pump #2 overheating" | Equipment + condition | Create Work Order (type=breakdown) |
| "Fix generator fuel injector" | Equipment + repair intent | Create Work Order (type=corrective) |
| "Report fault on bilge pump" | Equipment + explicit fault | Create Work Order + Fault flag |
| "View fault history hydraulic pump" | Equipment + fault history | Fault Lens (read-only) |
| "FLT-2026-001234" | Direct fault code | Fault Lens (read-only unless escalated) |

**Key Insight**: The word "fault" in a query doesn't necessarily mean "go to fault lens". It usually means "create a breakdown WO".

---

# SECTION AA: FAULT AS METADATA MODEL

## When Fault Record Gets Created

**Automatic Creation (User doesn't explicitly request):**
```python
# When WO is created with fault-implying type
if work_order.type in ['breakdown', 'corrective', 'unplanned']:
    # Check if fault semantics detected in query/description
    if contains_fault_keywords(query, title, description):
        # Auto-create fault record
        fault = create_fault(
            equipment_id=work_order.equipment_id,
            title=work_order.title,
            severity=infer_severity(work_order.priority),
            status='investigating',  # WO creation = investigation started
            work_order_id=work_order.id  # Immediately linked
        )
```

**Explicit Creation (User specifically queries "report fault"):**
```python
# User query: "report fault hydraulic pump"
if query_intent == 'report_fault':
    # Show Create Work Order modal
    # Pre-select type='breakdown'
    # Fault record created when WO saved
```

**When Fault Lens Activates (Read-Only Context):**
```python
# User queries fault code or fault history
if query_matches_fault_code(query) or query_intent == 'view_fault_history':
    # Fault Lens activates
    # Primary purpose: view history, audit trail, attachments
    # NOT a workflow destination
```

## Fault vs Work Order Relationship

```
┌─────────────────────────────────────────┐
│           WORK ORDER (Primary)          │
│  - The job                              │
│  - Assigned crew                        │
│  - Parts needed                         │
│  - Time tracking                        │
│  - Completion workflow                  │
├─────────────────────────────────────────┤
│     FAULT (Metadata/Context Flag)       │
│  - Severity classification              │
│  - Equipment condition record           │
│  - Historical reference                 │
│  - Recurrence tracking                  │
│  - Audit trail                          │
└─────────────────────────────────────────┘

Fault is INSIDE Work Order, not separate.
```

---

# SECTION AB: USER JOURNEY SCENARIOS (CORRECTED)

## Scenario 1: Equipment Problem Discovery

**Context**: Engineer hears unusual noise from generator, discovers fuel injector issue

**Correct Flow (Query-Driven):**
```
1. Engineer opens Celeste app
2. Types: "Generator 1 fuel injector failure"
3. Search resolves:
   - Equipment: Generator #1 (matched)
   - Condition: "fuel injector failure" (breakdown semantics)
   - Intent: corrective action
4. Primary action presented: [Create Work Order]
5. Modal opens PRE-FILLED:
   - Equipment: Generator #1 ✓ (from query)
   - Title: "Fuel injector failure" ✓ (from query)
   - Type: [dropdown] → "breakdown" pre-selected
   - Priority: [dropdown] → user selects "critical"
   - Description: [  ] → optional details
6. User clicks Submit
7. Backend:
   - CREATE work order
   - CREATE fault record (auto, type=breakdown)
   - Link fault.work_order_id = new WO
   - Notify assigned crew via Ledger
8. Done: WO-2026-0045 created, fault auto-linked
```

**Total**: 4 user actions (query, review, select priority, submit)

**What DOESN'T happen:**
- ❌ User navigates to "Faults" section
- ❌ User sees "Critical Fault!" banner
- ❌ User creates fault THEN creates WO
- ❌ User manually links fault to WO

---

## Scenario 2: Fault Investigation & Resolution

**Context**: Engineer working on fault, needs to add notes and eventually close

**Correct Flow (Query-Driven):**
```
1. Engineer opens Celeste app
2. Types: "WO-2026-0045" (they're assigned to this WO)
3. Work Order Lens activates (primary view)
4. User sees WO details + linked fault context
5. As investigation progresses:
   - Clicks [Add Note] → adds investigation observations
   - Clicks [Attach Photo] → uploads photo to pms-discrepancy-photos bucket
6. When repair complete:
   - Clicks [Update Status] → selects "completed"
   - Notes: "Replaced fuel filter, tested OK"
7. Backend:
   - UPDATE work_order status = 'completed'
   - UPDATE fault status = 'resolved' (automatic, WO completion)
   - UPDATE fault resolved_at, resolved_by
```

**Key**: User works in WORK ORDER lens, fault updates cascade automatically.

---

## Scenario 3: Viewing Fault History (Explicit Query)

**Context**: Engineer wants to see past faults on equipment before maintenance

**Correct Flow (Query-Driven):**
```
1. Engineer types: "fault history Hydraulic Pump #2"
2. Query resolves:
   - Equipment: Hydraulic Pump #2
   - Intent: view fault history (read-only)
3. Fault History view activates (within Equipment context)
4. Shows timeline:
   - FLT-2026-001234: Oil leak (resolved 2026-01-15)
   - FLT-2025-000891: Pressure fluctuation (resolved 2025-11-20)
   - FLT-2025-000445: Seal failure (resolved 2025-06-10)
5. User can click any fault to see:
   - Investigation notes
   - Attached photos
   - Linked work order
   - Resolution details
```

**Key**: Fault Lens activates for READ operations (history, audit). NOT for workflow.

---

## Scenario 4: Direct Fault Query

**Context**: User received Ledger notification about fault update

**Correct Flow:**
```
1. User sees Ledger notification:
   "FLT-2026-001234 status changed to 'resolved'"
2. User clicks notification OR types "FLT-2026-001234"
3. Fault Lens activates (read context)
4. Shows fault details:
   - Equipment: Hydraulic Pump #2
   - Status: Resolved
   - Linked WO: WO-2026-0045 [View WO]
   - Resolution notes
   - Attached photos
5. If user needs to act:
   - Clicks [View WO] → Work Order Lens
   - Actions happen in WO context, not fault
```

---

# SECTION B: SCHEMA (UNCHANGED)

## Primary Table: `pms_faults`

**Columns** (19 total) - Production DB verified:

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID | PK |
| `yacht_id` | UUID | RLS isolation |
| `equipment_id` | UUID | FK → pms_equipment |
| `fault_code` | TEXT | Auto-generated (FLT-2026-XXXXXX) |
| `title` | TEXT | From WO title or query |
| `description` | TEXT | Optional |
| `severity` | fault_severity | Enum: low, medium, high, critical |
| `status` | TEXT | open, investigating, resolved, closed |
| `detected_at` | TIMESTAMPTZ | When fault was detected |
| `resolved_at` | TIMESTAMPTZ | When resolved |
| `resolved_by` | UUID | Who resolved |
| `work_order_id` | UUID | FK → pms_work_orders (PRIMARY LINK) |
| `metadata` | JSONB | Additional context |
| `created_at` | TIMESTAMPTZ | |
| `updated_at` | TIMESTAMPTZ | |
| `updated_by` | UUID | |
| `deleted_at` | TIMESTAMPTZ | Soft delete |
| `deleted_by` | UUID | |
| `deletion_reason` | TEXT | |

**Key Relationship**:
```sql
-- Fault is metadata for Work Order
-- When WO created with breakdown/fault type:
INSERT INTO pms_faults (
  equipment_id,
  title,
  work_order_id,  -- Linked at creation
  status,         -- 'investigating' (WO started)
  severity        -- Derived from WO priority
) VALUES (...);

-- When WO completed:
UPDATE pms_faults
SET status = 'resolved',
    resolved_at = NOW(),
    resolved_by = :user_id
WHERE work_order_id = :completed_wo_id;
```

---

# SECTION C: PERMISSIONS (UNCHANGED)

## Everyone (All Crew)
- View faults (via query)
- View fault history
- Add notes to fault (via WO context)
- Attach files to fault (via WO context)

## Engineers + Deck + Interior
- Create work orders (which auto-creates fault if breakdown type)
- Update work order status (cascades to fault status)

## Restricted (Captain + HoD + Purser)
- Archive fault (signature required)
- Delete from `documents` bucket only

---

# SECTION D: DISPLAY FIELDS (UNCHANGED)

**When Fault Lens activates (read context):**

1. Fault code (FLT-2026-001234)
2. Title
3. Description
4. Severity (backend display, no banner)
5. Status
6. Equipment name (clickable → Equipment context)
7. **Linked Work Order** (clickable → WO Lens) ← PRIMARY LINK
8. Detected at
9. Resolved at / Resolved by (if resolved)
10. Notes timeline
11. Attached photos

---

# SECTION E: ACTIONS (REVISED)

## Fault Lens Actions (4, not 6)

Since Fault is metadata and most work happens in WO Lens, actions are reduced:

### 1. `add_fault_note`
- **When**: User viewing fault context needs to add historical note
- **Writes to**: `pms_notes` (fault_id)
- **Typical Use**: Adding context not captured in WO notes

### 2. `attach_file_to_fault`
- **When**: User has photo/document specifically for fault record
- **Writes to**: `pms_attachments` (entity_type='fault')
- **Storage**: `pms-discrepancy-photos` bucket
- **Typical Use**: Damage photos, diagnostic screenshots

### 3. `view_linked_work_order`
- **When**: User needs to see/act on the WO
- **Action**: Navigate to WO Lens
- **Typical Use**: Primary pathway for any action

### 4. `archive_fault`
- **When**: Fault record is obsolete
- **Permission**: Captain, HoD, Purser + signature
- **Typical Use**: Cleanup, error correction

**REMOVED from Fault Lens:**
- ❌ `report_fault` → This is "Create Work Order" in Equipment/Search context
- ❌ `create_work_order_from_fault` → Redundant, fault already has WO
- ❌ `update_fault_status` → Status updates via WO, cascades automatically

---

# SECTION F: STORAGE BUCKET MAPPING (NEW)

## Attachment Routing

```python
def get_storage_bucket(entity_type: str, attachment_context: str) -> str:
    """
    Deterministic bucket mapping for attachments.
    No magic destinations.
    """
    BUCKET_MAP = {
        # Fault/discrepancy photos
        ('fault', 'photo'): 'pms-discrepancy-photos',
        ('fault', 'document'): 'pms-discrepancy-photos',

        # Receiving/inspection photos
        ('receiving', 'photo'): 'pms-receiving-images',

        # Part/inventory photos
        ('part', 'photo'): 'pms-part-photos',
        ('inventory', 'photo'): 'pms-part-photos',

        # Labels and generated PDFs
        ('label', 'pdf'): 'pms-label-pdfs',

        # Finance documents
        ('finance', 'document'): 'pms-finance-documents',
        ('invoice', 'document'): 'pms-finance-documents',

        # Work order general attachments
        ('work_order', 'photo'): 'pms-discrepancy-photos',
        ('work_order', 'document'): 'pms-discrepancy-photos',
    }

    return BUCKET_MAP.get((entity_type, attachment_context), 'pms-discrepancy-photos')
```

## `documents` Bucket Rules

```python
DOCUMENTS_BUCKET_POLICY = {
    'read': ['all_crew'],           # Everyone can read
    'write': [],                    # NO ONE writes via app
    'delete': ['captain', 'hod'],   # Only HoD+ can delete
    'source': 'yacht_cloud_ingestion'  # Only populated during initial install
}
```

---

# SECTION G: SITUATION MODIFIER (REVISED)

## NO Critical Fault Banner

**Old (Wrong):**
```
🚨 Critical fault - requires immediate work order
[Create Work Order] [Dismiss]
```

**New (Correct):**
```
Severity = backend signal only.
No banner.
No badge domination.
No SaaS theatre.
```

## What Severity Actually Does

```python
def apply_severity_backend_effects(fault):
    """
    Severity influences backend behavior, not UI drama.
    """
    if fault.severity == 'critical':
        # SLA timer: 4 hours
        set_sla_deadline(fault.work_order_id, hours=4)
        # Notification: immediate push
        notify_assigned_crew(fault.work_order_id, urgency='immediate')
        # Ledger prominence: top of list
        ledger_priority = 1

    elif fault.severity == 'high':
        set_sla_deadline(fault.work_order_id, hours=24)
        notify_assigned_crew(fault.work_order_id, urgency='high')
        ledger_priority = 2

    elif fault.severity == 'medium':
        set_sla_deadline(fault.work_order_id, days=7)
        notify_assigned_crew(fault.work_order_id, urgency='normal')
        ledger_priority = 3

    else:  # low
        set_sla_deadline(fault.work_order_id, days=30)
        ledger_priority = 4
```

## When Banners ARE Allowed

```python
ALLOWED_BANNERS = [
    # New information user doesn't already know
    "Work order WO-2026-0045 already exists for this equipment",
    "Similar fault was reported 3 days ago (FLT-2026-001233)",
    "Part needed for repair is out of stock",

    # NOT ALLOWED:
    # "This is a critical fault!"  ← User knows
    # "Requires immediate attention!" ← User knows
    # "High severity - act now!" ← SaaS theatre
]
```

---

# SECTION H: LEDGER INTEGRATION (NEW)

## What is Ledger?

```
Ledger = History + Notifications

❌ NOT a dashboard
❌ NOT a fault list
❌ NOT ambient UI

✅ User's action history (read/mutate)
✅ Push notifications for changes
✅ Recap of recent activity
```

## Ledger Entries for Faults

```python
FAULT_LEDGER_EVENTS = [
    # When fault created (via WO creation)
    {
        'event': 'fault_created',
        'message': 'Fault FLT-2026-001234 logged for Hydraulic Pump #2',
        'link': '/faults/uuid',  # Deep link
        'urgency': derived_from_severity
    },

    # When fault status changes
    {
        'event': 'fault_resolved',
        'message': 'Fault FLT-2026-001234 resolved',
        'link': '/faults/uuid',
        'notify': ['assigned_crew', 'hod']
    },

    # When note added
    {
        'event': 'fault_note_added',
        'message': 'Note added to FLT-2026-001234',
        'link': '/faults/uuid'
    }
]
```

## User Queries Ledger

```
User types: "my recent activity"
→ Shows Ledger entries for user

User types: "notifications"
→ Shows unread Ledger notifications

User types: "what changed on Hydraulic Pump #2"
→ Shows Ledger entries filtered by equipment
```

---

# SECTION I: BLOCKERS (UPDATED)

## BLOCKER 1: No `detected_by` Column
- **Status**: Planned migration
- **Impact**: Low (user who creates WO is effectively the detector)

## BLOCKER 2: Missing `update_fault_status` Action
- **Status**: NOT NEEDED
- **Reason**: Fault status cascades from WO status automatically

## BLOCKER 3: Missing `archive_fault` Action
- **Status**: Needs implementation
- **Priority**: Low (rarely used, HoD+ only)

---

# SECTION J: SUMMARY (REVISED)

## What Fault Lens IS:
- Read-only context view for fault history
- Audit trail for equipment condition
- Attachment gallery for damage photos
- Historical reference for recurrence analysis

## What Fault Lens IS NOT:
- Primary workflow destination
- Place to "report faults"
- Place to "create work orders"
- Dashboard or navigation target

## Canonical Flow:
```
Query → Work Order Lens → (Fault auto-created as metadata)
                       ↓
        Ledger notification → Query fault code → Fault Lens (read)
                                              ↓
                          View → Navigate to WO for actions
```

## Key Invariants (Locked):
1. ✅ Work Order is primary, Fault is metadata
2. ✅ Query-only activation (no buttons, no navigation)
3. ✅ Severity = backend signal only (no UI banners)
4. ✅ Attachments → deterministic bucket mapping
5. ✅ Ledger = history + notifications surface

---

**STOP. This is v3.1 - awaiting review before Work Order Lens.**
