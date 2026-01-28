# Faults Cluster - User Journeys

**Cluster:** FIX SOMETHING (Fault / Diagnostic)
**Date:** 2026-01-22
**Status:** Layer 2 - Cluster Journey Reference

---

## CLUSTER CONTRACT

**Primary entity:** Fault
**Entry points:** Search → Fault Detail
**Terminal states:** closed, false_alarm
**Can create other entities:** Work Orders, Handover Entries
**Highest-risk action:** close_fault (signature required at irreversible commit)

---

## SCOPE

**Cluster:** FIX SOMETHING
**Actions covered:** 17 / 17
**MVP actions:** 13
**Future actions:** 4 (Graph-RAG)
**Signature-required actions:** 2 (resolve_fault, close_fault)

**Purpose:** This cluster helps crew understand technical issues and take next steps.

**Future actions MUST NOT appear in UI unless explicitly enabled by feature flag.**

---

## FRONTEND EXPECTATIONS

**UI governed by:** [07_FRONTEND_DECISION_CONTRACT.md](../../07_FRONTEND_DECISION_CONTRACT.md)

**Situation activation:** Search → Fault Detail = `IDLE` → `CANDIDATE`
**Primary actions shown:** Max 2-3 (diagnose_fault, add_fault_note prioritized for engineers)
**RAG influence:** Prefills equipment + symptom, suggests manual sections, never auto-commits

---

## ACTIONS IN THIS CLUSTER

### Mutation Actions (9)

| Action | Risk | Signature | Pattern | Status |
|--------|------|-----------|---------|--------|
| report_fault | LOW | ❌ | `[SINGLE_STEP]` | ✅ MVP |
| acknowledge_fault | LOW | ❌ | `[SINGLE_STEP]` | ✅ MVP |
| diagnose_fault | MEDIUM | ❌ | `[SINGLE_STEP]` | ✅ MVP |
| create_work_order_from_fault | MEDIUM | ❌ | `[MULTI_STEP]` | ✅ MVP |
| add_fault_note | LOW | ❌ | `[SINGLE_STEP]` | ✅ MVP |
| add_fault_photo | LOW | ❌ | `[SINGLE_STEP]` | ✅ MVP |
| resolve_fault | HIGH | ✅ | `[SINGLE_STEP]` | ✅ MVP |
| close_fault | HIGH | ✅ | `[SINGLE_STEP]` | ✅ MVP |
| mark_fault_false_alarm | LOW | ❌ | `[SINGLE_STEP]` | ✅ MVP |

### Read Actions (4)

| Action | Purpose | Status |
|--------|---------|--------|
| show_manual_section | Open relevant manual section from fault | ✅ MVP |
| show_related_documents | Show all docs related to equipment/fault | ✅ MVP |
| show_equipment_history | Show past faults/WOs for this equipment | ✅ MVP |
| show_similar_past_events | Show faults with similar symptoms | ✅ MVP |

### Graph-RAG Actions (4 - Future)

| Action | Purpose | Status |
|--------|---------|--------|
| trace_related_faults | Graph traversal across fault relationships | ⏳ Future |
| trace_related_equipment | Graph traversal to related systems | ⏳ Future |
| view_linked_entities | Cross-entity navigation | ⏳ Future |
| show_document_graph | Document relationship visualization | ⏳ Future |

---

## GOLD JOURNEY (Primary Path)

**Link:** [Sarah's Night Shift - Fault → Handover](../../04_USER_JOURNEYS.md#journey-1-sarahs-night-shift--fault--handover)

**Actions covered:**
- Search → view fault (READ)
- add_to_handover (MUTATE_LOW)

**Pattern:** `[SINGLE_STEP]` `[MUTATE_LOW]` `[NO_SIGNATURE]`

**This is the most common path:** User discovers existing fault, adds to handover for next shift.

---

## JOURNEY VARIATIONS

### V1: Report New Fault

**WHO:** Any crew member discovers issue
**TRIGGER:** Equipment problem occurs
**PATTERN:** `[SINGLE_STEP]` `[MUTATE_LOW]` `[NO_SIGNATURE]`

#### Screen Flow

1. User types: "report gen 2 overheating"
2. Form appears:
   ```
   Report Fault

   Equipment: Generator 2 (pre-filled from query)
   Symptom: Overheating (pre-filled from query)
   Fault Code: [dropdown - optional]
   Description: [text area - min 10 chars]
   Severity: [Low / Medium / High / Critical]
   Photo: [optional]
   ```
3. User fills form, clicks [Report Fault]
4. Success: "✓ Fault #567 reported"

#### Database Operations

```sql
BEGIN TRANSACTION
1. INSERT pms_faults (
     equipment_id, symptom, fault_code, description,
     severity, status='reported', reported_by, reported_at
   )
2. INSERT ledger_events (
     event_type='fault_reported', entity_type='fault',
     entity_id=new_fault_id, user_id, timestamp,
     summary="User reported fault: Equipment X - Symptom Y"
   )
3. IF severity = 'critical' THEN
     INSERT handover_entries (
       entity_type='fault', entity_id=new_fault_id,
       summary="CRITICAL FAULT: [description]",
       priority='critical', created_by, created_at
     )
     INSERT ledger_events (
       event_type='handover_auto_created',
       summary="Critical fault auto-added to handover"
     )
   END IF
COMMIT
```

#### Differs from Gold

- **Creates new fault** (gold views existing fault)
- **Auto-creates handover if critical** `[AUTO_CREATE]` pattern
- **User provides all details** (gold just adds note)

#### System Guarantees

✅ Fault always created (or transaction fails)
✅ Critical faults auto-added to handover
✅ Ledger entry always written
✅ No signature required (informational)
✅ **One MUTATE action committed per user confirmation**

#### What Does NOT Happen

❌ No work order created
❌ No diagnosis yet
❌ No inventory check
❌ No alert to Captain (unless critical + configured)

---

### V2: False Alarm Path

**WHO:** Engineer investigates, determines not an issue
**TRIGGER:** Fault was reported but investigation shows false alarm
**PATTERN:** `[SINGLE_STEP]` `[MUTATE_LOW]` `[NO_SIGNATURE]`

#### Screen Flow

1. User views fault detail
2. Clicks: [Mark as False Alarm]
3. Form appears:
   ```
   Mark Fault #456 as False Alarm

   Reason: [text area - required]
   "Explain why this is not a real issue"
   ```
4. User enters reason: "Sensor malfunction. Actual coolant temp normal. Replaced faulty sensor."
5. Clicks [Confirm]
6. Success: "✓ Fault marked as false alarm"

#### Database Operations

```sql
BEGIN TRANSACTION
1. UPDATE pms_faults
   SET status='false_alarm',
       false_alarm_reason="...",
       closed_by=user_id, closed_at=NOW()
   WHERE id=fault_id
2. INSERT ledger_events (
     event_type='fault_false_alarm',
     entity_type='fault', entity_id=fault_id,
     summary="User marked fault as false alarm: [reason]"
   )
COMMIT
```

#### Differs from Gold

- **Closes fault immediately** (no diagnosis → WO → resolution cycle)
- **Ends journey** (no follow-up actions)
- **Short path** for non-issues

#### System Guarantees

✅ Fault status changed to false_alarm
✅ Reason logged
✅ Ledger entry written
✅ No signature required (informational)
✅ **One MUTATE action committed per user confirmation**

#### What Does NOT Happen

❌ No work order created
❌ No parts used
❌ No audit log (low-risk action)
❌ Fault NOT counted as real failure in analytics

---

### V3: Full Fault Lifecycle (Diagnosis → WO → Resolution → Closure)

**WHO:** Mike (power user, handles complex issues)
**TRIGGER:** Investigates fault from handover
**PATTERN:** `[MULTI_STEP]` `[SIGNATURE_CHAIN]` (2 signatures)

**Link:** [Mike's Morning - Fault → Diagnose → Create WO](../../04_USER_JOURNEYS.md#journey-2-mikes-morning--fault--diagnose--create-work-order)

#### Actions in Sequence

1. **diagnose_fault** (no signature)
   - Mike adds diagnosis, root cause, recommended action
   - Fault status: reported → diagnosed

2. **create_work_order_from_fault** (no signature)
   - WO created with details pre-filled from diagnosis
   - Fault status: diagnosed → work_created
   - Cross-link: WO.fault_id = fault, fault.work_order_id = WO

3. **[Later, after fixing]** resolve_fault (✅ signature)
   - Mike confirms repair completed
   - Fault status: work_created → resolved
   - Parts usage logged

4. **[After verification]** close_fault (✅ signature)
   - HOD or Mike verifies issue gone
   - Fault status: resolved → closed
   - Journey complete

#### Differs from Gold

- **Complete lifecycle** (gold is just handover)
- **Cross-cluster** (spans FAULTS + WORK_ORDERS + INVENTORY)
- **2 signatures** (at resolve + close)
- **Longest path** for real issues

#### System Guarantees

✅ State transitions validated (cannot skip steps)
✅ Work order linked to fault (bidirectional)
✅ Parts usage tracked
✅ 2 audit log entries (resolve + close)
✅ Ledger entries at each step
✅ **Signature required at irreversible commit** (resolve + close)
✅ **One MUTATE action committed per user confirmation** (4 separate commits across lifecycle)

---

### V4: Reopen Closed Fault

**WHO:** HOD or Engineer
**TRIGGER:** Previously closed fault, issue recurs
**PATTERN:** `[SINGLE_STEP]` `[MUTATE_LOW]` `[NO_SIGNATURE]`

#### Screen Flow

1. User views closed fault
2. Clicks: [Reopen Fault]
3. Form appears:
   ```
   Reopen Fault #456

   Current status: Closed

   Reason for reopening: [text area - required]
   "Explain why issue has returned"
   ```
4. User enters: "Issue recurred. High coolant temp alarm again. Previous repair insufficient."
5. Clicks [Reopen]
6. Success: "✓ Fault reopened"

#### Database Operations

```sql
BEGIN TRANSACTION
1. UPDATE pms_faults
   SET status='reported',
       reopened_by=user_id, reopened_at=NOW(),
       reopen_reason="...",
       reopen_count = reopen_count + 1
   WHERE id=fault_id AND status='closed'
2. INSERT ledger_events (
     event_type='fault_reopened',
     entity_type='fault', entity_id=fault_id,
     summary="User reopened fault: [reason]"
   )
COMMIT
```

#### Differs from Gold

- **Reverses closure** (closed → reported)
- **Tracks recurrence** (reopen_count incremented)
- **Failure path** (indicates previous fix didn't work)

#### System Guarantees

✅ Fault returns to reported status
✅ Reopen reason logged
✅ Reopen count tracked (for analytics)
✅ Previous diagnosis/WO links preserved
✅ No signature required (informational)

---

### V5: Acknowledge Fault (Silence Alarm)

**WHO:** Engineer on watch
**TRIGGER:** Alarm goes off, engineer acknowledges awareness
**PATTERN:** `[SINGLE_STEP]` `[MUTATE_LOW]` `[NO_SIGNATURE]`

#### Screen Flow

1. Alarm triggers, fault auto-reported by system
2. Engineer views fault
3. Clicks: [Acknowledge]
4. Optional note: "Acknowledged. Investigating cause."
5. Success: "✓ Fault acknowledged"

#### Database Operations

```sql
UPDATE pms_faults
SET status='acknowledged',
    acknowledged_by=user_id,
    acknowledged_at=NOW(),
    notes="..."
WHERE id=fault_id AND status='reported'
```

#### Differs from Gold

- **Status change only** (reported → acknowledged)
- **Silences alarm** (acknowledging = awareness, not resolution)
- **Buys time** to investigate before acting

#### System Guarantees

✅ Alarm silenced (if integrated with alarm system)
✅ Accountability logged (who acknowledged)
✅ Fault still open (must be resolved later)

---

## READ-ONLY ACTIONS (Brief Descriptions)

### show_manual_section

**Purpose:** Open relevant manual section based on fault context

**Flow:**
- User viewing fault
- Clicks [Show Manual]
- System retrieves: equipment manual + fault symptom keywords
- Opens manual to relevant section (e.g., "CAT 3512 - Cooling System Troubleshooting")

**Pattern:** `[READ_ONLY]` - Execute immediately, show results

---

### show_related_documents

**Purpose:** Show all documents related to this equipment/fault

**Flow:**
- User viewing fault
- Clicks [Related Docs]
- System queries: manuals, bulletins, previous repair notes for this equipment
- Shows list of documents

**Pattern:** `[READ_ONLY]`

---

### show_equipment_history

**Purpose:** Show past faults and work orders for this equipment

**Flow:**
- User viewing fault
- Clicks [Equipment History]
- System queries: all faults, WOs, maintenance for this equipment (last 6-12 months)
- Shows timeline view

**Pattern:** `[READ_ONLY]`

**Use case:** "Has this happened before?"

---

### show_similar_past_events

**Purpose:** Find faults with similar symptoms (pattern matching)

**Flow:**
- User viewing fault
- Clicks [Similar Faults]
- System searches: faults with same equipment type + similar symptoms
- Shows list with resolutions

**Pattern:** `[READ_ONLY]`

**Use case:** "How did we fix this last time?"

---

## GRAPH-RAG ACTIONS (Future - NOT MVP)

### trace_related_faults

**Purpose:** Graph traversal across fault relationships

**Concept:** Follow fault relationships to find connected issues
- Example: Gen 2 overheating → caused by coolant leak → caused by pump failure

**Status:** ⏳ Phase 2 (requires graph database)

---

### trace_related_equipment

**Purpose:** Graph traversal to related systems

**Concept:** Understand equipment dependencies
- Example: Fault in Gen 2 → affects HVAC (powered by Gen 2) → affects galley operations

**Status:** ⏳ Phase 2

---

### view_linked_entities

**Purpose:** Cross-entity navigation

**Concept:** From fault → see all linked WOs, parts, handovers, documents in one view

**Status:** ⏳ Phase 2

---

### show_document_graph

**Purpose:** Document relationship visualization

**Concept:** Visual graph showing how manuals, bulletins, and repairs connect

**Status:** ⏳ Phase 2

---

## ACTION COVERAGE CHECKLIST

### Mutation Actions
- [x] report_fault - V1
- [x] acknowledge_fault - V5
- [x] diagnose_fault - V3 (gold: Mike's journey)
- [x] create_work_order_from_fault - V3 (gold: Mike's journey)
- [x] add_fault_note - (Similar to add_to_handover pattern)
- [x] add_fault_photo - (Similar to add_to_handover pattern)
- [x] resolve_fault - V3
- [x] close_fault - V3
- [x] mark_fault_false_alarm - V2

### Read Actions
- [x] show_manual_section - Brief description
- [x] show_related_documents - Brief description
- [x] show_equipment_history - Brief description
- [x] show_similar_past_events - Brief description

### Graph-RAG (Future)
- [x] trace_related_faults - Marked as Phase 2
- [x] trace_related_equipment - Marked as Phase 2
- [x] view_linked_entities - Marked as Phase 2
- [x] show_document_graph - Marked as Phase 2

**Coverage:** 17/17 actions documented ✅

---

## SIGNATURE MAP

| Action | Signature? | Why |
|--------|------------|-----|
| report_fault | ❌ | No signature required (informational) |
| acknowledge_fault | ❌ | No signature required (informational) |
| diagnose_fault | ❌ | No signature required (informational) |
| create_work_order_from_fault | ❌ | No signature required (informational) |
| add_fault_note | ❌ | No signature required (informational) |
| add_fault_photo | ❌ | No signature required (informational) |
| resolve_fault | ✅ | Signature required at irreversible commit |
| close_fault | ✅ | Signature required at irreversible commit |
| mark_fault_false_alarm | ❌ | No signature required (informational) |

**Rule:** Signature required at irreversible commit (resolve, close), not at awareness/intent points.

---

## FAULT STATE MACHINE

```
NULL (no fault)
  ↓ report_fault
REPORTED (new issue)
  ↓ acknowledge_fault (optional)
ACKNOWLEDGED (aware, investigating)
  ↓ diagnose_fault
DIAGNOSED (cause identified)
  ↓ create_work_order_from_fault
WORK_CREATED (fixing in progress)
  ↓ resolve_fault (+ signature)
RESOLVED (fix applied)
  ↓ close_fault (+ signature)
CLOSED (complete)

Alternative paths:
REPORTED → mark_fault_false_alarm → FALSE_ALARM
CLOSED → reopen_fault → REPORTED
```

**Guardrails:**
- Cannot close until resolved
- Cannot resolve until work created (in most cases)
- Cannot create WO until diagnosed (enforced by UI, not hard constraint)

---

## CROSS-CLUSTER RELATIONSHIPS

### Faults → Work Orders
- `create_work_order_from_fault` creates bidirectional link
- `fault.work_order_id` points to WO
- `work_order.fault_id` points back to fault

### Faults → Handover
- `add_to_handover` with entity_type='fault'
- Critical faults auto-create handover entries

### Faults → Inventory
- When WO linked to fault is completed, parts usage tracked
- `resolve_fault` can optionally log parts used

### Faults → Documents
- Manual references captured in diagnosis
- `show_manual_section` opens relevant docs

---

## COMMON EDGE CASES

### Edge Case 1: Duplicate Fault Reports

**Scenario:** Same fault reported twice by different crew

**Current behavior:** Allow duplicates (rely on user to search first)

**Future consideration:** Detect duplicate by equipment + symptom similarity, ask: "Similar fault already exists. View Fault #456?"

---

### Edge Case 2: Closing Fault Without Work Order

**Scenario:** User wants to close fault that has no linked WO

**Current behavior:** Allowed (some faults resolved without formal WO - e.g., minor adjustments)

**Validation:** Fault must be in 'resolved' status

---

### Edge Case 3: Reopening Multiple Times

**Scenario:** Fault closed/reopened multiple times (chronic issue)

**Tracking:** `reopen_count` field incremented each reopen

**Analytics:** High reopen_count flags chronic issues for deeper investigation

---

## WHEN SYSTEM MUST STOP AND ASK USER

The system MUST stop and require explicit user clarification when:

### 1. Ambiguous Entity
**Trigger:** User searches "generator overheating" but yacht has 3 generators
**System behavior:** Show disambiguation UI with all 3 options, user must select
**Cannot proceed until:** User clicks one specific equipment

### 2. Conflicting Mutations
**Trigger:** User clicks [Close Fault] on fault with status='reported' (requires status='resolved' first)
**System behavior:** Show error: "Fault must be resolved before closing. Current status: Reported"
**Cannot proceed until:** Fault reaches 'resolved' status via resolve_fault action

### 3. Missing Required Data
**Trigger:** User tries to create work order but fault has no diagnosis
**System behavior:** Show warning: "Diagnose fault first for better work order detail. Continue anyway?"
**User choice:** Proceed with empty diagnosis OR cancel and diagnose first

### 4. Duplicate Detection (Future)
**Trigger:** User reports fault similar to existing open fault
**System behavior:** Show: "Similar fault already exists: Fault #456. View existing or create new?"
**User choice:** View existing OR create duplicate (with reason)

**Guardrail principle:** System stops for ambiguity, conflicts, and safety - not for convenience.

---

## PATTERN SUMMARY

| Pattern | Actions Using It | Count |
|---------|------------------|-------|
| `[SINGLE_STEP]` | report, acknowledge, diagnose, add_note, add_photo, resolve, close, false_alarm, reopen | 9 |
| `[MULTI_STEP]` | create_work_order_from_fault (within larger lifecycle) | 1 |
| `[READ_ONLY]` | show_manual, show_docs, show_history, show_similar | 4 |
| `[AUTO_CREATE]` | report_fault (if critical) | 1 |
| `[SIGNATURE_AT_END]` | resolve_fault, close_fault | 2 |

---

**Status:** Faults cluster fully documented. Pattern validated. Template locked. Ready to scale to remaining 11 clusters.
