# Work Orders Cluster - User Journeys

**Cluster:** DO MAINTENANCE (Tasks / Work Orders)
**Date:** 2026-01-22
**Status:** Layer 2 - Cluster Journey Reference

---

## CLUSTER CONTRACT

**Primary entity:** Work Order
**Entry points:** Search → WO Detail, Fault → Create WO, PM Due List → Create WO
**Terminal states:** completed, cancelled
**Can create other entities:** Inventory Transactions (parts usage), Ledger Events
**Highest-risk action:** mark_work_order_complete (signature required at irreversible commit)

---

## SCOPE

**Cluster:** DO MAINTENANCE
**Actions covered:** 13 / 13
**MVP actions:** 13
**Future actions:** 0
**Signature-required actions:** 1 (mark_work_order_complete)

**Purpose:** Create, track, and complete maintenance tasks. Stay ahead of scheduled work, avoid escalations.

**Future actions MUST NOT appear in UI unless explicitly enabled by feature flag.**

---

## FRONTEND EXPECTATIONS

**UI governed by:** [07_FRONTEND_DECISION_CONTRACT.md](../../07_FRONTEND_DECISION_CONTRACT.md)

**Situation activation:** Search → WO Detail = `IDLE` → `CANDIDATE`
**Primary actions shown:** Max 2-3 (start_work_order, add_wo_hours, add_wo_note prioritized)
**RAG influence:** Prefills title + description from fault context, suggests parts, never auto-commits

---

## ACTIONS IN THIS CLUSTER

### Mutation Actions (10)

| Action | Risk | Signature | Pattern | Status |
|--------|------|-----------|---------|--------|
| create_work_order | MEDIUM | ❌ | `[SINGLE_STEP]` | ✅ MVP |
| create_work_order_from_fault | MEDIUM | ❌ | `[MULTI_STEP]` | ✅ MVP |
| assign_work_order | LOW | ❌ | `[SINGLE_STEP]` | ✅ MVP |
| start_work_order | LOW | ❌ | `[SINGLE_STEP]` | ✅ MVP |
| add_wo_hours | LOW | ❌ | `[SINGLE_STEP]` | ✅ MVP |
| add_wo_part | LOW | ❌ | `[SINGLE_STEP]` | ✅ MVP |
| add_wo_note | LOW | ❌ | `[SINGLE_STEP]` | ✅ MVP |
| attach_photo_to_work_order | LOW | ❌ | `[SINGLE_STEP]` | ✅ MVP |
| attach_document_to_work_order | LOW | ❌ | `[SINGLE_STEP]` | ✅ MVP |
| mark_work_order_complete | HIGH | ✅ | `[SINGLE_STEP]` | ✅ MVP |
| cancel_work_order | LOW | ❌ | `[SINGLE_STEP]` | ✅ MVP |

### Read Actions (2)

| Action | Purpose | Status |
|--------|---------|--------|
| show_tasks_due | Show work orders due today/this week | ✅ MVP |
| show_tasks_overdue | Show overdue work orders | ✅ MVP |

---

## GOLD JOURNEY (Primary Path)

**Link:** [Mike's Morning - Fault → Diagnose → Create WO](../../04_USER_JOURNEYS.md#journey-2-mikes-morning--fault--diagnose--create-work-order)

**Actions covered:**
- create_work_order_from_fault (MUTATE_MEDIUM)
- add_wo_part (MUTATE_LOW)

**Pattern:** `[MULTI_STEP]` spanning FAULTS → WORK_ORDERS

**This is the most common creation path:** Work orders created from diagnosed faults.

---

## JOURNEY VARIATIONS

### V1: Create Standalone Work Order

**WHO:** Any engineer
**TRIGGER:** Scheduled maintenance due, or issue without existing fault
**PATTERN:** `[SINGLE_STEP]` `[MUTATE_MEDIUM]` `[NO_SIGNATURE]`

#### Screen Flow

1. User types: "create work order for bilge pump maintenance"
2. Form appears:
   ```
   Create Work Order

   Equipment: [Bilge Pump] (pre-filled from query or dropdown)

   Title: [text field - required]

   Description: [text area - min 10 chars]

   Priority: [Low / Normal / High / Urgent]

   Estimated Hours: [optional numeric]

   Assign To: [dropdown - crew list]

   Parts Required: [Add Part] button

   [Cancel] [Create Work Order]
   ```
3. User fills form, clicks [Create Work Order]
4. Success: "✓ Work Order WO-567 created"

#### Database Operations

```sql
BEGIN TRANSACTION
1. INSERT pms_work_orders (
     yacht_id, equipment_id, title, description,
     priority='normal', status='draft',
     estimated_hours=null, assigned_to=null,
     created_by, created_at
   ) RETURNING id INTO new_wo_id
2. IF parts specified THEN
     FOR EACH part:
       INSERT work_order_parts (
         work_order_id=new_wo_id, part_id, quantity_required=1
       )
   END IF
3. INSERT ledger_events (
     event_type='work_order_created',
     entity_type='work_order', entity_id=new_wo_id,
     user_id, timestamp,
     summary="User created WO: [title]"
   )
COMMIT
```

#### Differs from Gold

- **Standalone creation** (not from fault)
- **Status: draft** (not yet started)
- **No fault link** (no fault_id)

#### System Guarantees

✅ Work order always created (or transaction fails)
✅ Parts list captured if specified
✅ Ledger entry always written
✅ No signature required (informational)
✅ **One MUTATE action committed per user confirmation**

#### What Does NOT Happen

❌ No fault status changed (no fault linked)
❌ No inventory deducted (happens at completion)
❌ No auto-assignment (user can assign or leave unassigned)
❌ WO not started yet (status=draft)

---

### V2: Assign Work Order

**WHO:** HOD or assigning engineer
**TRIGGER:** Work order created but unassigned
**PATTERN:** `[SINGLE_STEP]` `[MUTATE_LOW]` `[NO_SIGNATURE]`

#### Screen Flow

1. User views unassigned WO
2. Clicks: [Assign]
3. Form appears:
   ```
   Assign Work Order WO-567

   Current: Unassigned

   Assign To: [dropdown - crew list]

   Priority: [current priority shown, can change]

   [Cancel] [Assign]
   ```
4. User selects crew member, clicks [Assign]
5. Success: "✓ WO assigned to Mike"

#### Database Operations

```sql
UPDATE pms_work_orders
SET assigned_to=user_id,
    assigned_by=current_user,
    assigned_at=NOW(),
    updated_at=NOW()
WHERE id=wo_id
```

#### System Guarantees

✅ Assignment logged
✅ Ledger entry written
✅ No signature required (informational)
✅ **One MUTATE action committed per user confirmation**

---

### V3: Work Order Execution Cycle (Start → Add Hours/Parts → Complete)

**WHO:** Assigned engineer
**TRIGGER:** Work order assigned, ready to begin
**PATTERN:** `[MULTI_STEP]` with separate commits per action

#### Actions in Sequence

**Step 1: Start Work Order**
```
User clicks [Start Work Order]
→ Status: draft → active
→ Ledger: "Mike started WO-567"
→ No signature required (informational)
```

**Step 2: Add Hours Worked (repeatable)**
```
User clicks [Log Hours]
→ Form: Hours worked [2.5], Date [today]
→ INSERT work_order_hours (wo_id, hours=2.5, logged_by, logged_at)
→ Ledger: "Mike logged 2.5 hours on WO-567"
→ No signature required (informational)
```

**Step 3: Add Parts Used (repeatable)**
```
User clicks [Add Part Used]
→ Form: Part [GEN-SEAL-001], Quantity [1]
→ UPDATE work_order_parts SET quantity_used=1 WHERE wo_id AND part_id
→ Ledger: "Mike used 1x GEN-SEAL-001 on WO-567"
→ No signature required (informational)
```

**Step 4: Mark Complete (signature required)**
```
User clicks [Mark Complete]
→ Form: Completion notes [optional]
→ Signature prompt appears
→ BEGIN TRANSACTION
    UPDATE work_orders SET status='completed', completed_by, completed_at, signature
    FOR EACH part used: INSERT inventory_transactions (quantity_change=-qty_used)
    INSERT ledger_events
    INSERT audit_log (with signature)
  COMMIT
→ Signature required at irreversible commit
```

#### System Guarantees

✅ Each step is separate commit (can pause between steps)
✅ Hours/parts logged incrementally
✅ Signature ONLY at completion (irreversible)
✅ Inventory deducted atomically at completion
✅ Audit log written (high-risk: inventory change)
✅ **One MUTATE action committed per user confirmation** (4 separate actions)

#### Differs from Gold

- **Full execution cycle** (gold only creates WO)
- **Incremental logging** (hours, parts tracked over time)
- **Signature at end** (not at start or middle)

---

### V4: Cancel Work Order

**WHO:** Creator or HOD
**TRIGGER:** Work order no longer needed
**PATTERN:** `[SINGLE_STEP]` `[MUTATE_LOW]` `[NO_SIGNATURE]`

#### Screen Flow

1. User views WO
2. Clicks: [Cancel Work Order]
3. Confirmation:
   ```
   Cancel Work Order WO-567?

   Title: Replace bilge pump sensor
   Status: Draft (not started)

   Reason: [text area - optional]

   [Back] [Cancel Work Order]
   ```
4. User enters reason (optional), clicks [Cancel Work Order]
5. Success: "✓ Work order cancelled"

#### Database Operations

```sql
UPDATE pms_work_orders
SET status='cancelled',
    cancelled_by=user_id,
    cancelled_at=NOW(),
    cancellation_reason="...",
    updated_at=NOW()
WHERE id=wo_id
```

#### System Guarantees

✅ WO status changed to cancelled
✅ Reason logged (if provided)
✅ No signature required (informational)
✅ **One MUTATE action committed per user confirmation**

#### What Does NOT Happen

❌ No parts returned to inventory (nothing was used yet)
❌ No refund of hours (none were logged)
❌ Linked fault status unchanged (fault can have new WO created)

---

### V5: Add Note/Photo/Document to WO

**WHO:** Anyone with access to WO
**TRIGGER:** Need to document progress or issues
**PATTERN:** `[SINGLE_STEP]` `[MUTATE_LOW]` `[NO_SIGNATURE]` `[CRUD_TEMPLATE]`

#### All follow same pattern:

| Action | Form Input | Database Write |
|--------|------------|----------------|
| add_wo_note | Note text (min 5 chars) | INSERT work_order_notes |
| attach_photo_to_work_order | Photo upload | INSERT work_order_attachments (type='photo') |
| attach_document_to_work_order | Document link/upload | INSERT work_order_attachments (type='document') |

**Example flow (add_wo_note):**
```
Click [Add Note]
→ Form: Note text
→ INSERT work_order_notes (wo_id, note_text, created_by, created_at)
→ INSERT ledger_events
→ Success: "✓ Note added"
```

#### System Guarantees

✅ Note/photo/document linked to WO
✅ Ledger entry written
✅ No signature required (informational)
✅ **One MUTATE action committed per user confirmation**

**This covers 3 actions in one pattern.**

---

## READ-ONLY ACTIONS

### show_tasks_due

**Purpose:** Display work orders due today or within specified timeframe. Used for daily work planning.

**Pattern:** `[READ_ONLY]`

---

### show_tasks_overdue

**Purpose:** Display work orders past their due date. Used for catch-up prioritization and accountability.

**Pattern:** `[READ_ONLY]`

---

## ACTION COVERAGE CHECKLIST

### Mutation Actions
- [x] create_work_order - V1
- [x] create_work_order_from_fault - Gold (Mike's journey) + Cross-ref to faults
- [x] assign_work_order - V2
- [x] start_work_order - V3 Step 1
- [x] add_wo_hours - V3 Step 2
- [x] add_wo_part - V3 Step 3
- [x] add_wo_note - V5
- [x] attach_photo_to_work_order - V5
- [x] attach_document_to_work_order - V5
- [x] mark_work_order_complete - V3 Step 4
- [x] cancel_work_order - V4

### Read Actions
- [x] show_tasks_due - Brief description
- [x] show_tasks_overdue - Brief description

**Coverage:** 13/13 actions documented ✅

---

## SIGNATURE MAP

| Action | Signature? | Why |
|--------|------------|-----|
| create_work_order | ❌ | No signature required (informational) |
| create_work_order_from_fault | ❌ | No signature required (informational) |
| assign_work_order | ❌ | No signature required (informational) |
| start_work_order | ❌ | No signature required (informational) |
| add_wo_hours | ❌ | No signature required (informational) |
| add_wo_part | ❌ | No signature required (informational) |
| add_wo_note | ❌ | No signature required (informational) |
| attach_photo_to_work_order | ❌ | No signature required (informational) |
| attach_document_to_work_order | ❌ | No signature required (informational) |
| mark_work_order_complete | ✅ | Signature required at irreversible commit |
| cancel_work_order | ❌ | No signature required (informational) |

**Rule:** Signature required at irreversible commit (completion = inventory deduction), not at creation/progress steps.

---

## WORK ORDER STATE MACHINE

```
NULL (no WO)
  ↓ create_work_order
DRAFT (created, not assigned)
  ↓ assign_work_order (optional)
DRAFT (assigned)
  ↓ start_work_order
ACTIVE (in progress)
  ↓ [add_wo_hours, add_wo_part, add_wo_note - repeatable]
ACTIVE (with progress logged)
  ↓ mark_work_order_complete (+ signature)
COMPLETED (done)

Alternative paths:
DRAFT → cancel_work_order → CANCELLED
ACTIVE → cancel_work_order → CANCELLED (with notes about why stopped)
```

**Guardrails:**
- Cannot complete without starting
- Cannot start without assignment (optional constraint, configurable)
- Cannot complete if required parts not available (warning, not hard block)

---

## CROSS-CLUSTER RELATIONSHIPS

### Work Orders → Faults
- `create_work_order_from_fault` creates bidirectional link
- `work_order.fault_id` points to fault
- `fault.work_order_id` points back to WO
- See: `faults_cluster_journeys.md` V3

### Work Orders → Inventory
- `mark_work_order_complete` triggers inventory transactions
- Parts used deducted from stock
- See: `inventory_cluster_journeys.md` (Batch 2)

### Work Orders → Handover
- WOs can be added to handover
- See: `handover_cluster_journeys.md` V2

---

## WHEN SYSTEM MUST STOP AND ASK USER

The system MUST stop and require explicit user clarification when:

### 1. Ambiguous Equipment
**Trigger:** User creates WO with query "fix pump" but yacht has 8 pumps
**System behavior:** Show disambiguation UI with all pumps
**Cannot proceed until:** User selects specific equipment

### 2. Insufficient Parts
**Trigger:** User tries to complete WO but required parts show zero stock
**System behavior:** Show warning: "Part GEN-SEAL-001 required but out of stock. Mark complete anyway?"
**User choice:** Complete without logging part usage OR cancel completion to order parts first

### 3. Missing Hours
**Trigger:** User tries to complete WO with no hours logged
**System behavior:** Show prompt: "No hours logged. Enter hours now or complete without logging?"
**User choice:** Add hours now OR complete without hours

### 4. Conflicting State
**Trigger:** User tries to start WO with status='completed'
**System behavior:** Show error: "Work order already completed. Cannot restart."
**Cannot proceed until:** WO status reverted (admin only) OR create new WO

**Guardrail principle:** System stops for ambiguity and conflicts, warns for missing data (doesn't block).

---

## PATTERN SUMMARY

| Pattern | Actions Using It | Count |
|---------|------------------|-------|
| `[SINGLE_STEP]` | create, assign, start, add_hours, add_part, add_note, attach_photo, attach_doc, complete, cancel | 10 |
| `[MULTI_STEP]` | Execution cycle (start → log → complete) | 1 flow, 4 actions |
| `[READ_ONLY]` | show_tasks_due, show_tasks_overdue | 2 |
| `[CRUD_TEMPLATE]` | add_note, attach_photo, attach_document | 3 |
| `[SIGNATURE_AT_END]` | mark_work_order_complete | 1 |

---

**Status:** Work Orders cluster fully documented. Template fits naturally (no friction). Ready for Handover cluster.
