# 04_USER_JOURNEYS.md

**Date:** 2026-01-22
**Purpose:** Gold set user journeys - the shared mental model for product, design, engineering, and AI
**Status:** Layer 1 - Learning Document (read this first)

---

## HOW TO READ THIS DOCUMENT

This document defines **5-7 representative user journeys** that cover 80-90% of real CelesteOS use.

**Each journey includes:**
- WHO (avatar, role, context)
- TRIGGER (what makes them open CelesteOS)
- DEVICE (iPad in engine room, phone on deck, etc.)
- Screen-by-screen walkthrough
- System Guarantees (what MUST happen)
- What Does NOT Happen (silence is a feature)
- Risk Classification (signature/audit requirements)

**If a feature doesn't appear in any of these journeys, question why it exists.**

---

## JOURNEY 1: Sarah's Night Shift – Fault → Handover

**WHO:** Sarah (3rd Engineer, 6 months onboard, night watch 00:00-06:00)
**TRIGGER:** Alarm panel beeps - Gen 2 high coolant temp
**DEVICE:** iPad in engine room (gloves on, noisy, hot)
**PATTERN:** `[SINGLE_STEP]` `[MUTATE_LOW]` `[NO_SIGNATURE]`

---

### Screen 1: Opens CelesteOS

**What Sarah sees:**
- One search bar at top
- Recent history below: "Fuel filter check (2 hours ago)"
- No navigation menu, no dashboard

**What Sarah does:**
- Types: "gen 2 overheating"
- (Takes 3 tries with gloves)

---

### Screen 2: Search Results Appear

**What Sarah sees:**
```
[Equipment]
  Generator 2 - Engine Room

[Faults]
  Fault #456: High Coolant Temp (Open)
  Reported: 2 days ago by Mike

[Documents]
  CAT 3512 Manual - Cooling System Troubleshooting

[Work Orders]
  WO-789: Gen 2 Scheduled Maintenance (Active)
```

**What Sarah sees (important):**
- ❌ NO ACTION BUTTONS
- ❌ NO EDIT FIELDS
- ❌ NO AUTO-OPEN
- ✅ Just preview cards

**What Sarah does:**
- Reads Fault #456 preview: "High coolant temp alarm, coolant level normal, cause unknown"
- Clicks: Fault #456 card

---

### Screen 3: Fault Detail Opens (Situation: ACTIVE)

**What Sarah sees:**
- Fault details:
  - Equipment: Generator 2
  - Status: Open
  - Severity: Medium
  - Description: "High coolant temp alarm. Coolant level checked - normal. Cause unknown."
  - Reported by: Mike, 2 days ago
  - No diagnosis yet

**Action buttons NOW appear:**
```
[Diagnose Fault]  [Add to Handover]  [▼ More]
```

**What Sarah thinks:**
- "I don't know enough to diagnose this. Mike probably already investigated."
- "Better add to handover so day shift knows alarm went off again."

**What Sarah does:**
- Clicks: [Add to Handover]

---

### Screen 4: Form Appears (Pre-filled)

**What Sarah sees:**
```
Add to Handover

Summary: "Generator 2 - Overheating"
         (pre-filled, editable)

Priority: ⚠️ High
          (dropdown: Low / Normal / High / Critical)

Details: [empty text box]
```

**What Sarah does:**
- Edits summary to: "Generator 2 - Overheating (alarm triggered again)"
- Adds details: "Alarm triggered at 02:15. Checked coolant level - normal. Unsure of cause. Mike diagnosed this 2 days ago, issue may have returned."
- Keeps priority: High
- Clicks: [Confirm]

---

### Screen 5: Success (No Signature Required)

**What happens (backend):**
```
BEGIN TRANSACTION
1. INSERT handover_entries (
     yacht_id, entity_type='fault', entity_id=fault_456,
     summary="Generator 2 - Overheating (alarm triggered again)",
     priority='high', details="...", created_by=sarah, created_at=NOW()
   )
2. INSERT ledger_events (
     event_type='handover_created', entity_type='handover',
     entity_id=new_handover_id, user_id=sarah, timestamp=NOW(),
     summary="Sarah added Generator 2 fault to handover"
   )
COMMIT
```

**What Sarah sees:**
```
✓ Added to handover

[View Handover List]  [Back to Fault]
```

**What Sarah does:**
- Clicks [Back to Fault] (wants to check if anything else needed)
- Sees fault detail again, no other actions needed
- Closes CelesteOS
- Returns to rounds

---

### Later (06:00): Mike's Morning

**What Mike does:**
- Opens CelesteOS
- Types: "handover"
- Sees handover list with Sarah's entry at top:
  ```
  🔴 High Priority
  Generator 2 - Overheating (alarm triggered again)
  Added by: Sarah, 02:20
  ```
- Clicks entry, reads Sarah's notes
- Investigates issue (see Journey 2)

---

### System Guarantees

✅ No actions visible in search (only after click)
✅ No signature required (MUTATE_LOW - informational continuity)
✅ Handover entry always created (or transaction fails)
✅ Ledger entry always written
✅ Context preserved (equipment + symptom from search)
✅ Form pre-filled (reduces Sarah's cognitive load)

---

### What Does NOT Happen

❌ No work order created
❌ No inventory deducted
❌ No signature requested
❌ No alert sent to captain
❌ No fault status changed
❌ No auto-diagnosis
❌ No forced navigation away from fault

**Silence is a feature.** Sarah adds continuity info, nothing else changes.

---

### Risk Classification

**Risk Class:** MUTATE_LOW
**Reason:** Informational continuity only, no operational state change
**Signature:** ❌ Not required
**Audit Log:** ❌ Not written (ledger only)
**Reversible:** ✅ Yes (handover can be edited/deleted by HOD)

---

## JOURNEY 2: Mike's Morning – Fault → Diagnose → Create Work Order

**WHO:** Mike (2nd Engineer, 15 years experience, confident power user)
**TRIGGER:** Reviews handover, sees Sarah's Gen 2 alarm note
**DEVICE:** iPad in engine control room
**PATTERN:** `[MULTI_STEP]` `[MUTATE_MEDIUM]` `[NO_SIGNATURE]`

---

### Screen 1: From Handover to Fault

**What Mike does:**
- Opens CelesteOS
- Types: "gen 2 fault"
- Sees Fault #456 in results
- Clicks it

**What Mike sees:**
- Same fault detail as Sarah saw
- But Mike notices: "Status: Open (no diagnosis)"
- Action buttons:
  ```
  [Diagnose Fault]  [Add to Handover]  [▼ More]
  ```

**What Mike does:**
- Clicks: [Diagnose Fault]

---

### Screen 2: Diagnosis Form

**What Mike sees:**
```
Diagnose Fault #456

Fault: Generator 2 - High Coolant Temp
Reported: 2 days ago by Mike (you)
Status: Open → will become "Diagnosed"

Diagnosis: [text area - minimum 20 chars]

Root Cause: [text area - minimum 10 chars]

Recommended Action: [text area - minimum 10 chars]

Manual Reference: [optional text field]
                  "e.g., CAT 3512 Manual, Section 4.2, Page 45"

[Cancel]  [Save + Diagnose]
```

**What Mike does:**
- Types diagnosis: "Coolant pump seal failure confirmed. Pump loses pressure after 30min runtime, causing high temp alarm. Visual inspection shows coolant seepage at pump seal housing."
- Root cause: "Pump seal wear after 12,000 operating hours. Seal exceeded service life (10,000h recommended)."
- Recommended action: "Replace coolant pump seal. Part: GEN-SEAL-001. Estimated 3 hours labor. Should be done within 48h to prevent pump failure."
- Manual reference: "CAT 3512 Manual, Section 4.2.3, Page 45-47"
- Clicks: [Save + Diagnose]

---

### Screen 3: Diagnosis Saved

**What happens (backend):**
```
BEGIN TRANSACTION
1. UPDATE pms_faults
   SET status='diagnosed',
       diagnosis="Coolant pump seal failure...",
       root_cause="Pump seal wear after 12,000...",
       recommended_action="Replace coolant pump seal...",
       manual_reference="CAT 3512 Manual...",
       diagnosed_by=mike, diagnosed_at=NOW(), updated_at=NOW()
   WHERE id=fault_456
2. INSERT ledger_events (
     event_type='fault_diagnosed', entity_type='fault',
     entity_id=fault_456, user_id=mike, timestamp=NOW(),
     summary="Mike diagnosed Generator 2 fault: pump seal failure"
   )
COMMIT
```

**What Mike sees:**
```
✓ Fault diagnosed

Status: Open → Diagnosed

Next suggested action:
[Create Work Order]

Other actions:
[Add to Handover]  [View Manual Section]  [Back to Fault]
```

**What Mike thinks:**
- "Need to create WO now so we can fix this before it gets worse."

**What Mike does:**
- Clicks: [Create Work Order]

---

### Screen 4: Create Work Order Form (Pre-filled)

**What Mike sees:**
```
Create Work Order from Fault #456

Equipment: Generator 2 (locked - from fault)

Title: "Fix: Generator 2 - High Coolant Temp"
       (pre-filled from fault, editable)

Description: (pre-filled from diagnosis, editable)
"Coolant pump seal failure confirmed. Pump loses pressure
after 30min runtime, causing high temp alarm. Visual
inspection shows coolant seepage at pump seal housing.

ROOT CAUSE: Pump seal wear after 12,000 operating hours.

RECOMMENDED: Replace coolant pump seal. Part: GEN-SEAL-001.
Estimated 3 hours labor."

Priority: High (mapped from fault severity: Medium → High)

Estimated Hours: [empty - optional]

Parts Required: [Add Part] button
                (GEN-SEAL-001 can be added from form)

Assign To: [dropdown - crew list]

[Cancel]  [Create Work Order]
```

**What Mike does:**
- Edits title to: "Replace Gen 2 Coolant Pump Seal"
- Keeps description (good detail from diagnosis)
- Changes priority to: Urgent (wants it done today)
- Estimated hours: 3
- Clicks [Add Part] → searches "GEN-SEAL-001" → adds to WO
- Assign to: Himself
- Clicks: [Create Work Order]

---

### Screen 5: Work Order Created

**What happens (backend):**
```
BEGIN TRANSACTION
1. INSERT pms_work_orders (
     yacht_id, equipment_id=gen2, fault_id=fault_456,
     title="Replace Gen 2 Coolant Pump Seal",
     description="...", priority='urgent', status='active',
     estimated_hours=3, assigned_to=mike, created_by=mike,
     created_at=NOW()
   ) RETURNING id INTO new_wo_id
2. INSERT work_order_parts (
     work_order_id=new_wo_id, part_id=GEN-SEAL-001,
     quantity_required=1, quantity_used=0
   )
3. UPDATE pms_faults
   SET status='work_created', work_order_id=new_wo_id,
       updated_at=NOW()
   WHERE id=fault_456
4. INSERT ledger_events (
     event_type='work_order_created', entity_type='work_order',
     entity_id=new_wo_id, user_id=mike, timestamp=NOW(),
     summary="Mike created WO: Replace Gen 2 Coolant Pump Seal"
   )
5. INSERT ledger_events (
     event_type='fault_status_changed', entity_type='fault',
     entity_id=fault_456, user_id=mike, timestamp=NOW(),
     summary="Fault #456 → Work Order Created"
   )
COMMIT
```

**What Mike sees:**
```
✓ Work Order WO-123 created

Title: Replace Gen 2 Coolant Pump Seal
Status: Active
Assigned to: You
Priority: Urgent

Part required: GEN-SEAL-001 (1x)
Stock on hand: 2

Next actions:
[Start Work Order]  [Check Part Location]  [View Fault]
```

**What Mike does:**
- Clicks [Check Part Location]
- Sees: "Engine Room Spares Locker, Shelf 3B"
- Grabs part, starts work
- (Work completion is separate journey)

---

### System Guarantees

✅ Fault status transitions: Open → Diagnosed → Work Created
✅ Work order links to fault (bidirectional)
✅ Parts list captured in WO
✅ Diagnosis preserved in WO description
✅ Manual reference preserved
✅ Ledger entries for both fault update AND WO creation
✅ Pre-filled form reduces Mike's data entry
✅ No signature required (intent, not completion)

---

### What Does NOT Happen

❌ No inventory deducted yet (happens when WO completed)
❌ No signature requested (creating WO = intent, not completion)
❌ No audit log (not high-risk action)
❌ No parts automatically ordered (Mike confirms stock first)
❌ No alert to Chief Engineer (Mike is handling it)
❌ No fault closed (must be resolved first)

---

### Risk Classification

**Risk Class:** MUTATE_MEDIUM
**Reason:** Creates work order + changes fault state, but reversible (WO can be cancelled)
**Signature:** ❌ Not required (intent, not completion)
**Audit Log:** ❌ Not written (ledger only)
**Reversible:** ✅ Yes (WO can be cancelled, fault status can revert)

---

## JOURNEY 3: Receiving Session – Parts Arrive → Multi-Step Check-In

**WHO:** Chief Engineer (experienced, responsible for inventory accuracy)
**TRIGGER:** Supplier delivery arrives at dock
**DEVICE:** iPad on deck, signing for delivery
**PATTERN:** `[MULTI_STEP_RESUMABLE]` `[MUTATE_HIGH]` `[SIGNATURE_REQUIRED]`

---

### Screen 1: Start Receiving Session

**What Chief Engineer does:**
- Opens CelesteOS
- Types: "receive parts delivery"
- Sees: Purchase Order PO-456 (Status: Approved, awaiting delivery)
- Clicks PO-456

**What he sees:**
```
Purchase Order PO-456

Supplier: Marine Parts Ltd
Items: 5 items ordered
Status: Approved, awaiting delivery

[Start Receiving Session]
```

**What he does:**
- Clicks: [Start Receiving Session]

---

### Screen 2: Receiving Session Created

**What happens (backend):**
```
BEGIN TRANSACTION
1. INSERT pms_receiving_sessions (
     yacht_id, po_id=po_456,
     session_number="RCV-2026-001",
     status='active', started_by=chief, started_at=NOW()
   ) RETURNING id INTO session_id
2. FOR EACH item IN purchase_order_items:
     INSERT pms_receiving_items (
       receiving_session_id=session_id,
       shopping_list_item_id=item.id,
       part_id=item.part_id,
       part_number=item.part_number,
       part_name=item.name,
       quantity_expected=item.quantity,
       quantity_received=0,
       checked=FALSE
     )
3. INSERT ledger_events (
     event_type='receiving_session_started',
     entity_type='receiving_session', entity_id=session_id,
     user_id=chief, timestamp=NOW(),
     summary="Chief Engineer started receiving session RCV-2026-001"
   )
COMMIT
```

**What Chief Engineer sees:**
```
Receiving Session RCV-2026-001
Status: Active

Items to check in: 5

1. [ ] MTU Oil Filter (P/N: MTU-0001)
       Expected: 10 | Received: ___ | ✓ Mark as checked

2. [ ] Hydraulic Hose 3/8" (P/N: HYD-3875)
       Expected: 5 | Received: ___ | ✓ Mark as checked

3. [ ] Coolant Pump Seal (P/N: GEN-SEAL-001)
       Expected: 2 | Received: ___ | ✓ Mark as checked

4. [ ] V-Belt Set (P/N: BELT-A45)
       Expected: 1 | Received: ___ | ✓ Mark as checked

5. [ ] Impeller Kit (P/N: IMP-2024)
       Expected: 3 | Received: ___ | ✓ Mark as checked

[Commit Session] (disabled - must check all items first)
```

---

### Screen 3: Check In First Item

**What Chief Engineer does:**
- Opens first box
- Counts MTU oil filters: 10 filters present
- Clicks item 1

**What he sees:**
```
Check In Item

Part: MTU Oil Filter (P/N: MTU-0001)
Expected: 10

Quantity Received: [10] (entered)

Condition: ● All good  ○ Damaged  ○ Wrong part  ○ Missing

Notes: [optional]

[Upload Photo] (optional)

[Cancel]  [Confirm]
```

**What he does:**
- Enters: 10
- Selects: All good
- Clicks: [Confirm]

**What happens (backend):**
```
UPDATE pms_receiving_items
SET quantity_received=10, checked=TRUE,
    discrepancy_type=NULL, updated_at=NOW()
WHERE id=item_1
```

**What he sees:**
```
✓ Item 1 checked

Progress: 1/5 items checked

(Returns to session list, item 1 now checked)
```

---

### Screen 4: Discrepancy Found (Item 3)

**What Chief Engineer does:**
- Opens third box
- Counts coolant pump seals: Only 1 seal present (expected 2)
- Clicks item 3

**What he sees:**
```
Check In Item

Part: Coolant Pump Seal (P/N: GEN-SEAL-001)
Expected: 2

Quantity Received: [1] (entered)

Condition: ● All good  ● Damaged  ● Wrong part  ● Missing
           (auto-detects discrepancy when qty ≠ expected)

⚠️ Discrepancy detected

Discrepancy Type:
  ○ Quantity mismatch (auto-selected)
  ○ Wrong part
  ○ Damaged
  ○ Missing entirely

Notes: [required when discrepancy]

[Upload Photo] (recommended)

[Cancel]  [Confirm]
```

**What he does:**
- Confirms quantity: 1
- Discrepancy type: Quantity mismatch (already selected)
- Notes: "Only 1 seal delivered. Expected 2. Box was opened, appears supplier shorted us."
- Clicks [Upload Photo] → takes photo of opened box
- Clicks: [Confirm]

**What happens (backend):**
```
UPDATE pms_receiving_items
SET quantity_received=1, checked=TRUE,
    discrepancy_type='quantity_mismatch',
    discrepancy_notes="Only 1 seal delivered...",
    photo_urls=['https://.../photo1.jpg'],
    updated_at=NOW()
WHERE id=item_3
```

**What he sees:**
```
✓ Item 3 checked (discrepancy noted)

Progress: 3/5 items checked

⚠️ 1 discrepancy found
```

---

### Screen 5: Complete All Items

*Chief Engineer checks items 2, 4, 5 (all match expected)*

**What he sees after checking all 5:**
```
Receiving Session RCV-2026-001
Status: Active

Items checked: 5/5

✓ 1. MTU Oil Filter - 10 received ✓
✓ 2. Hydraulic Hose - 5 received ✓
⚠️ 3. Coolant Pump Seal - 1 received (expected 2)
✓ 4. V-Belt Set - 1 received ✓
✓ 5. Impeller Kit - 3 received ✓

Discrepancies: 1

[Review Discrepancies]  [Commit Session]
```

**What he does:**
- Clicks: [Commit Session]

---

### Screen 6: Signature Required

**What he sees:**
```
Commit Receiving Session

This will:
✓ Update inventory for all items
✓ Close purchase order
✓ Mark discrepancy for follow-up

⚠️ This action requires your signature

Items with discrepancies:
- Coolant Pump Seal: 1 received (expected 2)

Confirm you have verified all items.

[Cancel]  [Sign + Commit]
```

**What he does:**
- Reviews one more time
- Clicks: [Sign + Commit]

**Signature UI appears:**
```
Sign with finger:

[____________________________]
 (touchscreen signature pad)

[Clear]  [Confirm Signature]
```

**What he does:**
- Signs with finger
- Clicks: [Confirm Signature]

---

### Screen 7: Session Committed

**What happens (backend):**
```
BEGIN TRANSACTION
1. UPDATE pms_receiving_sessions
   SET status='committed', committed_by=chief,
       committed_at=NOW(), signature=<base64_sig>
   WHERE id=session_id

2. FOR EACH receiving_item WHERE checked=TRUE:
     INSERT inventory_transactions (
       part_id=item.part_id,
       quantity_change=item.quantity_received,
       transaction_type='receiving',
       receiving_session_id=session_id,
       created_by=chief, created_at=NOW()
     )
     UPDATE parts
     SET quantity_on_hand = quantity_on_hand + item.quantity_received
     WHERE id=item.part_id

3. UPDATE purchase_orders
   SET status='received', received_at=NOW()
   WHERE id=po_456

4. INSERT ledger_events (
     event_type='receiving_committed',
     entity_type='receiving_session', entity_id=session_id,
     user_id=chief, timestamp=NOW(),
     summary="Chief Engineer committed receiving session RCV-2026-001 (1 discrepancy)"
   )

5. INSERT pms_audit_log (
     action_id='commit_receiving_session',
     entity_type='receiving_session', entity_id=session_id,
     old_state={status:'active', items_unchecked:0},
     new_state={status:'committed', items_checked:5, discrepancies:1},
     user_id=chief, signature=<base64_sig>, timestamp=NOW()
   )

COMMIT (or ROLLBACK if any fails)
```

**What Chief Engineer sees:**
```
✓ Receiving session committed

Session: RCV-2026-001
Status: Completed

Inventory updated:
+ 10 MTU Oil Filter
+ 5 Hydraulic Hose
+ 1 Coolant Pump Seal
+ 1 V-Belt Set
+ 3 Impeller Kit

Discrepancy logged:
⚠️ Coolant Pump Seal: Short 1 unit

Next actions:
[Contact Supplier]  [View Inventory]  [Close]
```

**What he does:**
- Clicks [Contact Supplier] (to resolve shortage)
- (Supplier communication is separate flow)

---

### Resumability Example

**Scenario:** If Chief Engineer had been interrupted after checking 3/5 items:

**What happens:**
- Session remains status='active'
- Items 1-3 marked checked=TRUE
- Items 4-5 remain checked=FALSE

**When he returns:**
- Opens CelesteOS
- Banner appears: "You have an active receiving session"
- Or searches: "receiving" → sees RCV-2026-001 (In Progress)
- Clicks → resumes at item 4

**Rule:** Multi-step flows with incremental mutations are resumable.

---

### System Guarantees

✅ Session cannot commit until all items checked
✅ Signature required at commit (inventory = financial)
✅ Inventory transactions atomic (all or nothing)
✅ Discrepancies logged with photos
✅ Purchase order closed only after commit
✅ Audit log written (high-risk: inventory changes)
✅ Resumable (can pause/resume)

---

### What Does NOT Happen

❌ No inventory update until commit
❌ No partial commits (must check all items first)
❌ No auto-reorder for shortages (Chief decides)
❌ No automatic supplier notification (Chief initiates)
❌ No session cancellation after commit (irreversible)

---

### Risk Classification

**Risk Class:** MUTATE_HIGH
**Reason:** Inventory changes are financial + operationally sensitive
**Signature:** ✅ Required (at commit)
**Audit Log:** ✅ Written (includes signature, old/new state)
**Reversible:** ❌ No (after commit, cannot undo - must create adjustment)

---

## JOURNEY 4: Planned Maintenance Checklist – Looping Execution

**WHO:** Mike (2nd Engineer)
**TRIGGER:** Weekly engine room checklist due
**DEVICE:** iPad mounted near control panel
**PATTERN:** `[LOOPING]` `[MULTI_STEP]` `[SIGNATURE_AT_END]`

---

### Screen 1: Open Checklist

**What Mike does:**
- Opens CelesteOS
- Types: "engine room checklist"
- Sees: "Weekly Engine Room Inspection (Due Today)"
- Clicks it

**What he sees:**
```
Weekly Engine Room Inspection
Due: Today
Status: Not Started

Items: 12

[Start Checklist]
```

**What he does:**
- Clicks: [Start Checklist]

---

### Screen 2: Checklist Items (Looping)

**What Mike sees:**
```
Weekly Engine Room Inspection
Progress: 0/12

☐ 1. Check main engine oil level
     [✓ Pass] [✗ Fail] [+ Note] [+ Photo]

☐ 2. Inspect coolant levels (all engines)
     [✓ Pass] [✗ Fail] [+ Note] [+ Photo]

☐ 3. Check bilge pump operation
     [✓ Pass] [✗ Fail] [+ Note] [+ Photo]

☐ 4. Inspect hydraulic reservoir level
     [✓ Pass] [✗ Fail] [+ Note] [+ Photo]

... (8 more items)

[Save Progress] [Sign Off Checklist] (disabled until all complete)
```

---

### Screen 3: Checking Items (Happy Path)

**What Mike does:**
- Walks to main engine
- Checks dipstick: oil level good
- Returns to iPad
- Clicks item 1: [✓ Pass]

**What happens (local state):**
```
Item 1 marked: PASS
Progress: 1/12
```

**Mike continues:**
- Item 2: Coolant OK → [✓ Pass]
- Item 3: Bilge pump tested → [✓ Pass]
- Item 4: Hydraulic level OK → [✓ Pass]
- Progress: 4/12

---

### Screen 4: Item Fails (Discrepancy)

**Mike checks item 5:**
- "Check generator exhaust for leaks"
- Mike notices: Small exhaust leak at Gen 2 manifold gasket

**What Mike does:**
- Clicks item 5: [✗ Fail]

**What he sees:**
```
Item 5: Check generator exhaust for leaks
Status: FAILED

⚠️ This item is marked as CRITICAL

Notes: [required for failed items]

Photo: [optional but recommended]

Create work order for this failure?
○ Yes, create WO now
○ No, I'll handle it manually

[Cancel] [Save Failure]
```

**What Mike does:**
- Notes: "Small exhaust leak at Gen 2 manifold gasket. Visible soot. Non-critical but should be repaired within week."
- Takes photo of leak
- Selects: "Yes, create WO now"
- Clicks: [Save Failure]

**What happens (backend):**
```
Item 5 marked: FAIL
Progress: 5/12

(WO auto-created in background for failed critical item)
```

---

### Screen 5: Complete All Items

**Mike finishes remaining 7 items (all pass)**

**What he sees:**
```
Weekly Engine Room Inspection
Progress: 12/12 ✓

✓ 11 items passed
✗ 1 item failed (Item 5 - Gen 2 exhaust leak)

Work order created:
WO-456: "Fix Gen 2 exhaust leak" (from checklist failure)

[Sign Off Checklist]
```

**What Mike does:**
- Clicks: [Sign Off Checklist]

---

### Screen 6: Sign Off (Signature Required)

**What he sees:**
```
Sign Off Checklist

Weekly Engine Room Inspection
Completed: 12/12 items
Failed items: 1
Work orders created: 1

By signing, you certify:
✓ All items were checked
✓ Failed items are documented
✓ Work orders created for critical failures

[Cancel] [Sign + Complete]
```

**What Mike does:**
- Clicks: [Sign + Complete]
- Signature pad appears
- Signs with finger
- Clicks: [Confirm Signature]

---

### Screen 7: Checklist Complete

**What happens (backend):**
```
BEGIN TRANSACTION
1. INSERT checklist_completions (
     checklist_id=weekly_engine,
     completed_by=mike, completed_at=NOW(),
     items_passed=11, items_failed=1,
     signature=<base64_sig>, status='completed'
   )
2. FOR EACH failed_item WHERE is_critical=TRUE:
     (WO already auto-created at failure)
3. INSERT ledger_events (
     event_type='checklist_completed',
     entity_type='checklist', entity_id=completion_id,
     user_id=mike, timestamp=NOW(),
     summary="Mike completed Weekly Engine Room Inspection (1 failure)"
   )
4. INSERT pms_audit_log (
     action_id='sign_off_checklist',
     entity_type='checklist', entity_id=completion_id,
     old_state={status:'in_progress'},
     new_state={status:'completed', failures:1, wo_created:1},
     user_id=mike, signature=<base64_sig>, timestamp=NOW()
   )
COMMIT
```

**What Mike sees:**
```
✓ Checklist completed

Weekly Engine Room Inspection
Completed: Today, 14:30
Signed by: Mike (2nd Engineer)

Next checklist due: Next week

[View Work Orders] [View History] [Close]
```

---

### System Guarantees

✅ Cannot sign off until all items checked
✅ Failed critical items auto-create work orders
✅ Signature required at completion
✅ Audit log written (compliance requirement)
✅ Progress saved locally (can resume if interrupted)
✅ Photo evidence captured for failures

---

### What Does NOT Happen

❌ No partial sign-off (must complete all items)
❌ No signature per item (only at end)
❌ No auto-escalation to Chief (Mike handles WO)
❌ No inventory deduction yet (happens when WO completed)

---

### Risk Classification

**Risk Class:** MUTATE_MEDIUM
**Reason:** Compliance record + auto-creates WO, but reversible (checklist can be voided by HOD)
**Signature:** ✅ Required (at sign-off)
**Audit Log:** ✅ Written (compliance requirement)
**Reversible:** ⚠️ Limited (completion recorded, but HOD can void if needed)

---

## JOURNEY 5: Chief Engineer Review – "What Happened This Week?"

**WHO:** Chief Engineer
**TRIGGER:** Friday afternoon, preparing weekly report for Captain
**DEVICE:** Desktop in Chief's office
**PATTERN:** `[READ_ONLY]` `[OVERSIGHT]` `[DRILL_DOWN]`

---

### Screen 1: Query for Team Activity

**What Chief Engineer does:**
- Opens CelesteOS
- Types: "show engineering work this week"

**What he sees:**
```
Engineering Activity - This Week

Timeline View | By Person | By Type

23 actions this week

Thu 14:30 - Mike completed Weekly Engine Room Inspection (1 failure)
Thu 02:20 - Sarah added Generator 2 fault to handover
Wed 11:15 - Mike created work order: Replace Gen 2 Coolant Pump Seal
Wed 11:05 - Mike diagnosed Generator 2 fault: pump seal failure
Tue 16:45 - Chief Engineer committed receiving session RCV-2026-001
Tue 09:30 - Sarah adjusted inventory: -2 hydraulic hoses (used on WO-445)
...

[Filter by: Person ▼] [Filter by: Action Type ▼] [Export Report]
```

---

### Screen 2: Drill Into Specific Event

**What Chief Engineer does:**
- Clicks: "Mike diagnosed Generator 2 fault: pump seal failure"

**What he sees:**
```
Ledger Event Detail

Action: diagnose_fault
Entity: Fault #456 - Generator 2 High Coolant Temp
User: Mike (2nd Engineer)
Timestamp: Wed 11:05

Summary:
Mike diagnosed Generator 2 fault: pump seal failure

Details:
- Diagnosis: "Coolant pump seal failure confirmed..."
- Root cause: "Pump seal wear after 12,000 operating hours..."
- Recommended action: "Replace coolant pump seal..."
- Manual reference: CAT 3512 Manual, Section 4.2.3

Follow-up actions:
→ Work order created: WO-123 (by Mike, Wed 11:15)

[View Audit Log] (button appears if audit exists)
[View Fault Detail] [View Work Order] [Close]
```

---

### Screen 3: Drill Into Audit (If Available)

**What Chief Engineer does:**
- Clicks: [View Audit Log]

**What he sees:**
```
Audit Log Entry

Action: commit_receiving_session
Entity: Receiving Session RCV-2026-001
User: Chief Engineer (you)
Timestamp: Tue 16:45

Old State:
{
  "status": "active",
  "items_unchecked": 0
}

New State:
{
  "status": "committed",
  "items_checked": 5,
  "discrepancies": 1,
  "inventory_updated": true
}

Signature: ✓ Verified
Signature timestamp: Tue 16:45:23

[View Discrepancy Details] [Close]
```

---

### Screen 4: Filter by Person

**What Chief Engineer does:**
- Clicks: [Filter by: Person ▼]
- Selects: Sarah

**What he sees:**
```
Engineering Activity - This Week
Filtered by: Sarah (3rd Engineer)

7 actions this week

Thu 02:20 - Added Generator 2 fault to handover
Tue 09:30 - Adjusted inventory: -2 hydraulic hoses (used on WO-445)
Mon 18:45 - Added note to work order WO-441
Mon 15:20 - Attached photo to work order WO-441
Mon 14:30 - Started work order WO-441: Replace bilge pump sensor
Sun 23:15 - Viewed Generator 3 manual (Section 2.4)
Sun 22:00 - Reported fault: Generator 3 low oil pressure warning

Summary:
- 3 work order actions
- 2 fault-related actions
- 1 inventory adjustment
- 1 document view
```

**What Chief Engineer thinks:**
- "Sarah is learning well. Good documentation on the Gen 2 issue."
- "She's handling night shift independently now."

---

### Screen 5: Export Weekly Report

**What Chief Engineer does:**
- Clicks: [Export Report]

**What he sees:**
```
Export Engineering Activity Report

Date Range: Jan 15 - Jan 22, 2026
Scope: Engineering Department
Format: ○ PDF  ● Excel  ○ CSV

Include:
☑ Action timeline
☑ User summary (actions per person)
☑ Equipment worked on
☐ Audit trail details (only if needed for compliance)

[Cancel] [Export]
```

**What he does:**
- Selects: Excel
- Clicks: [Export]
- Downloads: `Engineering_Activity_2026-W03.xlsx`
- Sends to Captain via email

---

### System Guarantees

✅ Ledger shows all Engineering team actions
✅ Can drill into individual events
✅ Can drill into audit logs (if they exist)
✅ Can filter by person, action type, equipment, date
✅ Can export for reporting
✅ READ-only (Chief cannot modify history)

---

### What Does NOT Happen

❌ Chief cannot edit past actions
❌ Chief cannot delete ledger entries
❌ Chief cannot modify signatures
❌ No auto-generated "report" (Chief curates what to include)
❌ No email alerts (Chief pulls data when needed)

---

### Risk Classification

**Risk Class:** READ
**Reason:** Query only, no mutations
**Signature:** ❌ Not required
**Audit Log:** ❌ Not written (viewing history doesn't change state)
**Reversible:** N/A (no changes made)

---

## JOURNEY 6: Captain Evidence Request – Compliance Investigation

**WHO:** Captain
**TRIGGER:** Flag state inspector asks: "Show me all Generator 2 maintenance in last 6 months"
**DEVICE:** Desktop in Captain's quarters
**PATTERN:** `[READ_ONLY]` `[COMPLIANCE]` `[AUDIT_FOCUSED]`

---

### Screen 1: Evidence Query

**What Captain does:**
- Opens CelesteOS
- Types: "show all changes to generator 2 last 6 months"

**What he sees:**
```
Generator 2 - Activity (Last 6 Months)

47 events found

Sorted by: Most Recent

Work Orders (12):
✓ WO-123: Replace Coolant Pump Seal (Completed, Jan 2026)
✓ WO-089: Scheduled maintenance 1000h (Completed, Dec 2025)
...

Faults (8):
✓ Fault #456: High Coolant Temp (Closed, Jan 2026)
✓ Fault #392: Oil pressure low (False alarm, Nov 2025)
...

Maintenance Checklists (18):
✓ Weekly Engine Room Inspection (18 completions)

Inventory Transactions (9):
Parts used: Oil filters, coolant, pump seal, gaskets
...

[View Timeline] [Export Evidence Pack] [Filter by Type ▼]
```

---

### Screen 2: Evidence Pack Export

**What Captain does:**
- Clicks: [Export Evidence Pack]

**What he sees:**
```
Export Compliance Evidence Pack

Equipment: Generator 2
Date Range: Jul 2025 - Jan 2026 (6 months)

Include:
☑ Work orders (with completion signatures)
☑ Fault reports (with diagnoses)
☑ Maintenance checklists (with sign-offs)
☑ Parts used (inventory transactions)
☑ Audit logs (signature trail)
☑ Manual references (documentation links)

Format: ○ PDF (readable)  ● PDF + Excel (auditable)

[Cancel] [Generate Evidence Pack]
```

**What he does:**
- Clicks: [Generate Evidence Pack]
- Downloads: `Generator_2_Evidence_Jul2025-Jan2026.zip`
- Contains:
  - `summary.pdf` (overview)
  - `work_orders.xlsx` (all WO details)
  - `faults.xlsx` (all fault records)
  - `audit_trail.xlsx` (signature log)
  - `parts_used.xlsx` (inventory transactions)

**What Captain does:**
- Hands USB drive to inspector
- Inspector reviews evidence
- ✅ Compliance verified

---

### System Guarantees

✅ All actions on equipment are traceable
✅ Signatures are preserved and verifiable
✅ Audit trail is immutable
✅ Evidence pack includes all relevant records
✅ READ-only (Captain cannot modify history)
✅ Date range filtering accurate

---

### What Does NOT Happen

❌ No retroactive editing allowed
❌ No deletion of records
❌ No modification of timestamps
❌ No "selective" export (all or nothing for compliance)

---

### Risk Classification

**Risk Class:** READ
**Reason:** Query only, compliance verification
**Signature:** ❌ Not required (viewing only)
**Audit Log:** ❌ Not written (viewing doesn't change state)
**Reversible:** N/A (no changes made)

---

## JOURNEY 7: Stewardess Entry Point – "Fridge Broken"

**WHO:** Stewardess (non-technical, reports issues only)
**TRIGGER:** Galley fridge not cooling
**DEVICE:** iPhone (personal device)
**PATTERN:** `[ENTRY_ONLY]` `[SINGLE_STEP]` `[MUTATE_LOW]`

---

### Screen 1: Search

**What Stewardess does:**
- Opens CelesteOS
- Types: "fridge broken"

**What she sees:**
```
[Equipment]
  Galley Fridge - Deck 2

[Work Orders]
  WO-234: Galley fridge compressor maintenance (Closed, 2 weeks ago)

[No active faults]
```

**What she does:**
- Clicks: Galley Fridge

---

### Screen 2: Equipment View (Limited Actions)

**What she sees:**
```
Galley Fridge
Location: Deck 2, Galley
Status: Operational (last checked 2 weeks ago)

Actions available to you:
[Report Fault]  [Add Note]  [Add Photo]

Other actions (requires Engineer):
- View History
- View Manual
- Create Work Order
```

**What she does:**
- Clicks: [Report Fault]

---

### Screen 3: Report Fault Form

**What she sees:**
```
Report Fault - Galley Fridge

Symptom: (dropdown)
  ○ Not cooling
  ○ Strange noise
  ○ Leaking
  ○ Door not closing
  ○ Other

Description: (text area - min 10 chars)

Severity: (auto-suggested: Medium)

Photo: [optional]

[Cancel]  [Report Fault]
```

**What she does:**
- Selects symptom: "Not cooling"
- Description: "Galley fridge is not cooling. Food is warm. Noticed this morning."
- Takes photo of fridge interior (warm items)
- Clicks: [Report Fault]

---

### Screen 4: Fault Reported

**What happens (backend):**
```
BEGIN TRANSACTION
1. INSERT pms_faults (
     equipment_id=galley_fridge,
     symptom="Not cooling",
     description="Galley fridge is not cooling...",
     severity="medium",
     status="reported",
     reported_by=stewardess, reported_at=NOW()
   )
2. INSERT ledger_events (
     event_type='fault_reported',
     entity_type='fault', entity_id=new_fault_id,
     user_id=stewardess, timestamp=NOW(),
     summary="Stewardess reported fault: Galley fridge not cooling"
   )
COMMIT
```

**What she sees:**
```
✓ Fault reported

Fault #567: Galley Fridge - Not cooling
Status: Reported

An engineer will investigate this issue.
You will be notified when resolved.

[View Fault Status] [Close]
```

**What she does:**
- Clicks [Close]
- Returns to work

**What happens (background):**
- Engineering department sees new fault in their queue
- Mike investigates later (separate journey)

---

### System Guarantees

✅ Stewardess can report faults (capture)
✅ Stewardess can add notes/photos (observe)
✅ Stewardess CANNOT diagnose, create WO, or close faults (boundaries)
✅ Fault routed to appropriate department
✅ No signature required (informational)

---

### What Does NOT Happen

❌ Stewardess cannot diagnose
❌ Stewardess cannot create work order
❌ Stewardess cannot close fault
❌ Stewardess cannot access inventory
❌ No auto-escalation to Captain (Engineers handle)

---

### Risk Classification

**Risk Class:** MUTATE_LOW
**Reason:** Informational only, creates awareness
**Signature:** ❌ Not required
**Audit Log:** ❌ Not written (low-risk reporting)
**Reversible:** ✅ Yes (fault can be marked false alarm by Engineer)

---

## SUMMARY: COVERAGE MAP

| Journey | Pattern | Actions Covered | Signature | Avatar |
|---------|---------|-----------------|-----------|--------|
| 1. Sarah's Handover | Single-step | add_to_handover | ❌ | New crew |
| 2. Mike's WO Creation | Multi-step | diagnose → create_wo_from_fault | ❌ | Power user |
| 3. Receiving Session | Resumable, Multi-step | start → check_in → commit | ✅ | HOD |
| 4. Checklist Execution | Looping, Sign-off | execute_checklist → sign_off | ✅ | Engineer |
| 5. Chief Engineer Review | Read-only, Oversight | view_ledger, filter, export | ❌ | HOD |
| 6. Captain Evidence | Read-only, Compliance | evidence_export, audit_view | ❌ | Captain |
| 7. Stewardess Report | Entry-only | report_fault | ❌ | Non-technical |

**Patterns covered:**
- ✅ Single-step mutations
- ✅ Multi-step flows
- ✅ Resumable sessions
- ✅ Looping interactions
- ✅ Read-only queries
- ✅ Signature-required actions
- ✅ Auto-create triggers
- ✅ Role-based boundaries

**Cross-cluster journeys:**
- Journey 2 spans: FAULTS → WORK_ORDERS
- Journey 3 spans: PURCHASING → INVENTORY
- Journey 5 spans: ALL (oversight)

**If a feature doesn't appear in these 7 journeys, question why it exists.**

---

**Status:** Gold set complete. Ready for Layer 2 (cluster journey batches).
