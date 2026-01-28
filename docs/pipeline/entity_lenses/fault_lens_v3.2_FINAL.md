# Entity Lens: Fault (FINAL)

**Status**: v3.2 - All Corrections Applied
**Last Updated**: 2026-01-24
**Schema Source**: Production Supabase Database
**Template Status**: GOLD STANDARD - Use this depth for all future lenses

---

## TIER-0 DOCTRINE (LOCKED)

### Doctrine 1: Query-Only Activation
```
Celeste UI has:
✅ One search bar
✅ Three buttons: [Ledger] [Settings] [Email]
✅ One SPA

Celeste UI does NOT have:
❌ Dashboards
❌ Navigation menus
❌ Ambient buttons
❌ Fault list pages
❌ Preloaded forms
❌ Module navigation

RULE: Nothing appears unless user queried it.

Query → results → user focuses ONE result → lens activates → context menu appears

No actions rendered on results list.
Actions only appear AFTER user focuses a single entity.
```

### Doctrine 2: Work Order is Primary, Fault is Metadata
```
Crew mental model = jobs, not fault objects.
"Fix it" → Work Order
"Investigate it" → Work Order
"Repair it" → Work Order

Fault = context flag / subtype / metadata
Fault = historical record for recurrence

Work Order is where work happens.
Fault is where history lives.
```

### Doctrine 3: Severity = Backend Signal Only
```
❌ No "Critical Fault!" banners
❌ No urgency lectures
❌ No SaaS theatre

✅ Severity drives:
   - SLA timers
   - Notification urgency
   - Ledger prominence
   - Priority pre-fill

User already knows it's critical. Don't tell them.
```

### Doctrine 4: Faults Are NEVER Deleted
```
❌ No archive_fault action
❌ No soft delete on faults
❌ No hiding fault history

✅ Faults can be:
   - Resolved (via WO completion)
   - Closed (workflow complete)
   - Superseded (by new fault)

History must be preserved for:
   - Recurrence analysis
   - Audit compliance
   - Pattern detection
```

### Doctrine 5: Notes Location Rule
```
Operational notes → Work Order
   "Replaced seal, tested OK"
   "Parts installed at 14:30"
   "Crew: Smith, Jones"

Condition/Historical notes → Fault
   "Similar failure occurred 2023-06"
   "Root cause: seal degradation"
   "Equipment age: 8 years"
```

### Doctrine 6: Storage Bucket Mapping
```
documents              → Read-only (yacht→cloud ingestion)
                       → Delete: HoD+ only
                       → Write: NEVER via app

pms-discrepancy-photos → Fault/condition photos
pms-receiving-images   → WO receiving photos
pms-part-photos        → Part/inventory photos
pms-label-pdfs         → Generated label PDFs
pms-finance-documents  → Finance attachments

RULE: Attachment action → bucket deterministically
      No magic upload destinations
```

---

# SECTION 0: UI ARCHITECTURE

## The Search Bar Page

```
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│   [Ledger]              [Search Bar...]              [Settings] [Email]
│                                                             │
│                                                             │
│                    (empty until query)                      │
│                                                             │
│                                                             │
└─────────────────────────────────────────────────────────────┘

Ledger = BUTTON (not queryable)
  - User's action history (read/mutate)
  - Push notifications for changes
  - Recap of recent activity

Settings = BUTTON (ignore for now)
Email = BUTTON (ignore for now)
```

## Query Flow (Canonical)

```
1. USER TYPES QUERY
   "Generator 1 fuel injector failure"

2. RAG/SQL SEARCH EXECUTES
   Returns results from:
   - Work Orders (previous WOs mentioning generator/fuel injector)
   - Handovers (Dave's handover 2023: "fuel injector changed...")
   - Manuals (Generator 1 manual, page 234, fuel injector faults)
   - Notes (historical observations)
   - Equipment (Generator 1 details)
   - Faults (previous faults on Generator 1)

3. RESULTS DISPLAYED
   ┌──────────────────────────────────────────────────────────┐
   │ Search: "Generator 1 fuel injector failure"              │
   ├──────────────────────────────────────────────────────────┤
   │ EQUIPMENT                                                 │
   │   Generator #1 (Main Engine Room)                        │
   ├──────────────────────────────────────────────────────────┤
   │ MANUALS                                                   │
   │   Generator 1 Manual - Page 234: Fuel Injector Faults    │
   ├──────────────────────────────────────────────────────────┤
   │ PREVIOUS WORK ORDERS                                      │
   │   WO-2025-0891: Fuel injector replacement (completed)    │
   ├──────────────────────────────────────────────────────────┤
   │ HANDOVERS                                                 │
   │   Dave's Handover 2023-06-15: "Fuel injector changed..." │
   ├──────────────────────────────────────────────────────────┤
   │ FAULT HISTORY                                             │
   │   FLT-2025-000445: Fuel system fault (resolved)          │
   └──────────────────────────────────────────────────────────┘

4. USER FOCUSES ONE RESULT
   Example: User clicks "Generator #1 (Main Engine Room)"

5. ENTITY LENS ACTIVATES
   Equipment Lens for Generator #1

6. CONTEXT MENU AVAILABLE (on focused entity only)
   Actions available via context menu:
   - Create Work Order
   - Add to Handover
   - View Fault History
   - View Maintenance Schedule

   NOTE: No actions visible on search results list.
   Context menu only appears AFTER focusing single entity.
```

## Explicit Action Request Flow

```
1. USER TYPES EXPLICIT ACTION QUERY
   "create work order for generator 1 fuel injector"

2. SEARCH RESOLVES INTENT
   - Action: Create Work Order
   - Equipment: Generator #1
   - Context: "fuel injector" (will be title)

3. ACTION BUTTON DISPLAYED
   ┌──────────────────────────────────────────────────────────┐
   │ Search: "create work order for generator 1 fuel injector"│
   ├──────────────────────────────────────────────────────────┤
   │                                                           │
   │   [Create Work Order]                                    │
   │                                                           │
   │   Equipment: Generator #1                                │
   │   Title: Fuel injector                                   │
   │                                                           │
   └──────────────────────────────────────────────────────────┘

4. USER CLICKS BUTTON
   Modal opens with pre-filled values (editable)

5. USER COMPLETES FORM
   Journey to completion (frontend + backend)
```

**KEY RULE**: Buttons only appear when explicitly requested.
- Query without action intent → shows data results
- Query with action intent → shows action button

---

# SECTION AA: FAULT AS METADATA

## When Fault Record Gets Created

**Automatic (User doesn't explicitly request):**
```python
# When WO is created with breakdown/corrective type
def on_work_order_create(work_order):
    if work_order.type in ['breakdown', 'corrective', 'unplanned']:
        # Fault record auto-created as metadata
        fault = create_fault(
            equipment_id=work_order.equipment_id,
            title=work_order.title,
            severity=work_order.metadata.get('fault_severity', 'medium'),  # USER-PROVIDED via WO modal, defaults to medium
            status='investigating',  # WO creation = investigation started
            work_order_id=work_order.id,  # Linked immediately
            detected_at=now(),
            detected_by=work_order.created_by
        )
        return fault

# NOTE: Severity is USER-PROVIDED via WO creation modal dropdown.
# System does NOT derive or guess severity. User explicitly selects.
# If not provided, defaults to 'medium'.
```

**Explicit (User queries "report fault"):**
```python
# Query: "report fault hydraulic pump oil leak"
# Resolves to: Create Work Order with type=breakdown
# Same flow, but type is pre-selected as breakdown
```

## Fault Status Cascades from Work Order

```python
def on_work_order_status_change(work_order, new_status):
    if work_order.fault_id:
        fault = get_fault(work_order.fault_id)

        if new_status == 'in_progress':
            fault.status = 'investigating'

        elif new_status == 'completed':
            fault.status = 'resolved'
            fault.resolved_at = now()
            fault.resolved_by = current_user()

        elif new_status == 'cancelled':
            fault.status = 'open'  # Revert to open if WO cancelled

        save(fault)
```

---

# SECTION AB: USER JOURNEY SCENARIOS

## Scenario 1: Equipment Problem Discovery

**User Query**: "Generator 1 fuel injector failure"

**Flow:**
```
1. User types: "Generator 1 fuel injector failure"

2. RAG/SQL returns:
   - Equipment: Generator #1
   - Manual: Page 234 - Fuel Injector Troubleshooting
   - Previous WO: WO-2025-0891 (fuel injector replacement)
   - Handover: Dave 2023 ("fuel injector was changed due to...")
   - Fault History: FLT-2025-000445 (resolved)

3. User focuses "Generator #1" (clicks to select)

4. Equipment Lens activates (single entity focused)

5. Context menu available on focused entity:
   - Create Work Order
   - Add to Handover
   - View Fault History

   User opens context menu, selects "Create Work Order"

6. Create Work Order modal opens:
   - Equipment: Generator #1 ✓ (from context)
   - Title: [  ] → user types "Fuel injector failure"
   - Type: [dropdown] → selects "breakdown"
   - Priority: [dropdown] → selects "critical"
   - Description: [optional]

7. User submits

8. Backend:
   - CREATE pms_work_orders
   - CREATE pms_faults (auto, type=breakdown)
   - LINK fault.work_order_id = new WO
   - Ledger entry created
   - Notification to assigned crew

9. Done
```

## Scenario 2: Investigation & Resolution (Great as-is)

**User Query**: "WO-2026-0045"

**Flow:**
```
1. User types: "WO-2026-0045"

2. Work Order Lens activates

3. User works in WO context:
   - Add Note (operational): "Inspected fuel lines, found blockage"
   - Attach Photo → pms-discrepancy-photos bucket
   - Update Status → "completed"

4. Backend on WO completion:
   - UPDATE pms_work_orders status = 'completed'
   - UPDATE pms_faults status = 'resolved' (cascade)
   - Ledger entry: "WO-2026-0045 completed"
   - Ledger entry: "FLT-2026-001234 resolved"
```

## Scenario 3: Fault History Query

**User Query**: "fault history hydraulic pump"

**Flow:**
```
1. User types: "fault history hydraulic pump"

2. Search resolves:
   - Equipment: Hydraulic Pump #2
   - Intent: view fault history (read-only)

3. Fault History view activates (within Equipment context)

4. Shows timeline of faults for this equipment
```

**SQL Required for Fault History Fetch:**
```sql
-- Fetch fault history for equipment
-- Tables: pms_faults, pms_equipment, pms_work_orders, pms_notes

SELECT
    f.id AS fault_id,
    f.fault_code,
    f.title,
    f.description,
    f.severity,
    f.status,
    f.detected_at,
    f.resolved_at,
    f.resolved_by,
    -- Equipment info
    e.name AS equipment_name,
    e.location AS equipment_location,
    -- Linked work order
    wo.id AS work_order_id,
    wo.wo_number,
    wo.status AS wo_status,
    wo.completed_at AS wo_completed_at,
    -- Resolution notes (condition/historical notes on fault)
    (
        SELECT json_agg(json_build_object(
            'id', n.id,
            'text', n.text,
            'note_type', n.note_type,
            'created_at', n.created_at,
            'created_by', n.created_by
        ) ORDER BY n.created_at DESC)
        FROM pms_notes n
        WHERE n.fault_id = f.id
    ) AS fault_notes,
    -- Attachments
    (
        SELECT json_agg(json_build_object(
            'id', a.id,
            'filename', a.filename,
            'thumbnail_path', a.thumbnail_path,
            'uploaded_at', a.uploaded_at
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
  AND f.yacht_id = :yacht_id
  -- Note: NO deleted_at filter - show ALL history
ORDER BY f.detected_at DESC;
```

**Pipeline Capabilities Needed:**
```
1. RAG must index:
   - pms_faults.title
   - pms_faults.description
   - pms_faults.fault_code
   - pms_notes.text (where fault_id IS NOT NULL)

2. Search must resolve:
   - "fault history" → intent = view_fault_history
   - Equipment name → equipment_id

3. Triggers needed:
   - On WO completion → update linked fault status
   - On fault create → update search index
   - On note create (fault_id) → update search index
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
| `work_order_id` | UUID | FK → pms_work_orders |
| `metadata` | JSONB | Additional context |
| `created_at` | TIMESTAMPTZ | |
| `updated_at` | TIMESTAMPTZ | |
| `updated_by` | UUID | |
| `deleted_at` | TIMESTAMPTZ | **NOT USED** - faults never deleted |
| `deleted_by` | UUID | **NOT USED** |
| `deletion_reason` | TEXT | **NOT USED** |

**Note**: `deleted_at`, `deleted_by`, `deletion_reason` columns exist but are NEVER populated. Faults must be preserved for history.

---

# SECTION C: PERMISSIONS

## Everyone (All Crew)
- View faults (via query)
- View fault history
- Add condition notes to fault

## Engineers + Deck + Interior
- Create work orders (which auto-creates fault if breakdown type)
- Update work order status (cascades to fault status)
- Add operational notes to work order

## Captain + HoD + Purser
- **NO archive_fault action** - faults cannot be deleted
- Can delete from `documents` bucket only

---

# SECTION D: DISPLAY FIELDS

**When Fault Lens activates (read context):**

1. Fault code (FLT-2026-001234)
2. Title
3. Description
4. Severity (display only, no banner)
5. Status
6. Equipment name (clickable → Equipment context)
7. **Linked Work Order** (clickable → WO Lens)
8. Detected at
9. Detected by
10. Resolved at / Resolved by (if resolved)
11. Condition notes timeline
12. Attached photos

---

# SECTION E: MICRO-ACTIONS (3 only)

**Fault Lens is READ-ONLY + limited condition documentation.**

This is NOT a place to "work". It's a place to:
- View fault history
- Add condition/historical notes
- Attach evidence photos
- Navigate to WO (escape hatch for real work)

Since Fault is metadata and most work happens in WO Lens:

### 1. `add_fault_note`
- **Purpose**: Add condition/historical note to fault record
- **Writes to**: `pms_notes` (fault_id)
- **Note Type**: observation, warning, resolution, handover
- **Example**: "Similar failure occurred 2023-06, root cause was seal degradation"

### 2. `attach_file_to_fault`
- **Purpose**: Upload condition photo/document
- **Writes to**: `pms_attachments` (entity_type='fault')
- **Storage Bucket**: `pms-discrepancy-photos`
- **Example**: Photo of corrosion, diagnostic screenshot

### 3. `view_linked_work_order`
- **Purpose**: Navigate to WO for operational work
- **Action**: Lens transition to Work Order
- **Example**: User needs to update WO status, add operational notes

**REMOVED ACTIONS:**
- ❌ `report_fault` → This is "Create Work Order" (type=breakdown)
- ❌ `create_work_order_from_fault` → Redundant, fault already has WO
- ❌ `update_fault_status` → Status cascades from WO automatically
- ❌ `archive_fault` → Faults are NEVER deleted

---

# SECTION F: SITUATION MODIFIERS

## No Severity Banners

**Severity does NOT trigger UI changes.**

Severity triggers:
```python
def apply_severity_effects(fault):
    if fault.severity == 'critical':
        sla_hours = 4
        notification_urgency = 'immediate'
        ledger_priority = 1

    elif fault.severity == 'high':
        sla_hours = 24
        notification_urgency = 'high'
        ledger_priority = 2

    elif fault.severity == 'medium':
        sla_hours = 168  # 7 days
        notification_urgency = 'normal'
        ledger_priority = 3

    else:  # low
        sla_hours = 720  # 30 days
        notification_urgency = 'low'
        ledger_priority = 4

    set_sla_deadline(fault.work_order_id, hours=sla_hours)
    queue_notification(fault, urgency=notification_urgency)
```

## Allowed Informational Banners

Only show banners with **new information**:
```python
ALLOWED_BANNERS = [
    # Collision/duplicate detection
    "Work order WO-2026-0045 already exists for this equipment",
    "Similar fault reported 3 days ago: FLT-2026-001233",

    # NOT ALLOWED (user already knows):
    # "This is a critical fault!"
    # "Requires immediate attention!"
    # "Part out of stock" ← removed, can draft for later
]
```

---

# SECTION G: LEDGER INTEGRATION

## Ledger is a BUTTON (Not Queryable)

```
┌─────────────────────────────────────────────────────────────┐
│   [Ledger]              [Search Bar...]             [Settings] [Email]
└─────────────────────────────────────────────────────────────┘
         ↓
    (click opens Ledger panel)
```

**Ledger Contents:**
- User's action history (read/mutate)
- Push notifications for changes
- Recap of recent activity

**Cannot be queried** - it's a dedicated surface, not a searchable entity.

## Ledger Entries for Faults

```python
FAULT_LEDGER_EVENTS = [
    # When fault created (via WO creation)
    {
        'event': 'fault_created',
        'message': 'Fault FLT-2026-001234 logged for Generator #1',
        'link': '/faults/{uuid}',
        'urgency': 'derived_from_severity'
    },

    # When fault status changes (via WO cascade)
    {
        'event': 'fault_resolved',
        'message': 'Fault FLT-2026-001234 resolved',
        'link': '/faults/{uuid}',
        'notify': ['detected_by', 'assigned_crew']
    },

    # When condition note added
    {
        'event': 'fault_note_added',
        'message': 'Condition note added to FLT-2026-001234',
        'link': '/faults/{uuid}'
    }
]
```

---

# SECTION H: STORAGE BUCKET MAPPING

## Explicit Bucket Routing

```python
def get_storage_bucket(entity_type: str, context: str) -> str:
    """
    Deterministic bucket mapping. No magic destinations.
    """
    BUCKET_MAP = {
        # Fault/condition photos
        ('fault', 'photo'): 'pms-discrepancy-photos',
        ('fault', 'document'): 'pms-discrepancy-photos',

        # Work order attachments
        ('work_order', 'photo'): 'pms-discrepancy-photos',
        ('work_order', 'document'): 'pms-discrepancy-photos',

        # Receiving/inspection
        ('receiving', 'photo'): 'pms-receiving-images',

        # Parts/inventory
        ('part', 'photo'): 'pms-part-photos',

        # Labels
        ('label', 'pdf'): 'pms-label-pdfs',

        # Finance
        ('finance', 'document'): 'pms-finance-documents',
        ('invoice', 'document'): 'pms-finance-documents',
    }

    return BUCKET_MAP.get((entity_type, context), 'pms-discrepancy-photos')
```

## `documents` Bucket Policy

```python
DOCUMENTS_BUCKET = {
    'read': ['all_crew'],
    'write': [],  # NO writes via app
    'delete': ['captain', 'chief_engineer', 'chief_steward', 'chief_officer', 'purser'],
    'source': 'yacht_cloud_ingestion_only'
}
```

---

# SECTION I: PIPELINE REQUIREMENTS (NEW)

## RAG/Search Pipeline Must Support

```yaml
indexed_tables:
  - pms_faults:
      fields: [title, description, fault_code]
      embedding_field: search_embedding
  - pms_notes:
      fields: [text]
      filter: fault_id IS NOT NULL
  - pms_equipment:
      fields: [name, location, description]
  - pms_work_orders:
      fields: [title, description, wo_number]
  - pms_handover:
      fields: [summary_text]
  - documents:
      fields: [title, content_chunks]

intent_resolution:
  "fault history {equipment}": view_fault_history
  "report fault {equipment}": create_work_order (type=breakdown)
  "create work order {equipment}": create_work_order
  "{equipment} {problem}": search_results (equipment + context)

triggers_needed:
  - on_work_order_complete:
      action: update_linked_fault_status
      target: pms_faults.status = 'resolved'

  - on_fault_create:
      action: update_search_index
      target: RAG embeddings

  - on_note_create:
      condition: fault_id IS NOT NULL
      action: update_search_index
```

## Gaps to Document for Phase 2

```yaml
known_gaps:
  - detected_by column on pms_faults (migration ready)
  - RAG indexing for pms_notes where fault_id IS NOT NULL
  - Trigger: WO completion → fault status cascade
  - Ledger notification queue
  - SLA timer service
```

---

# SECTION J: SUMMARY

## What Fault Lens IS:
- Read-only context view for fault history
- Condition notes storage (not operational notes)
- Photo gallery for damage/condition evidence
- Historical reference for recurrence analysis
- Audit trail for equipment condition

## What Fault Lens IS NOT:
- Primary workflow destination
- Place to "report faults" (that's Create WO)
- Place to "create work orders" (that's WO Lens)
- Dashboard or navigation target
- Deletable/archivable entity

## What This Lens Is NOT (explicit):
- ❌ No navigation to reach it (query only)
- ❌ No dashboard widget
- ❌ No ambient buttons or actions on results list
- ❌ No severity banners or urgency lectures
- ❌ No archive/delete capability
- ❌ Not a place to "work" - that's WO Lens

## Canonical Flow:
```
Query → results → focus ONE entity → lens activates → context menu available
                                   ↓
Query with action intent → action button appears → modal pre-fills
                   ↓
WO created → fault auto-created (if breakdown)
                   ↓
Ledger notification → click → Fault Lens (read)
```

## Locked Invariants:
1. ✅ Query-only activation (no buttons on results list, context menu only on focused entity)
2. ✅ Work Order is primary, Fault is metadata
3. ✅ Severity = USER-PROVIDED via dropdown (not derived/guessed by system)
4. ✅ Severity effects = backend only (SLA, notifications, not UI)
5. ✅ Faults are NEVER deleted
6. ✅ Notes location: operational → WO, condition → Fault
7. ✅ Bucket mapping is deterministic
8. ✅ Ledger is button, not queryable
9. ✅ Fault Lens is read-only + condition notes/evidence + escape hatch to WO

---

**STOP. This is v3.2 FINAL. Awaiting review before Work Order Lens.**
