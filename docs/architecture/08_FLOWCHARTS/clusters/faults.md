# Fault Management Cluster Flow

**Date:** 2026-01-22
**Purpose:** Fault lifecycle (report → diagnose → create WO → resolve → close)
**Status:** Layer B - Cluster Flow

---

## ⚠️ VERIFICATION GAP WARNING

**Only 1/71 actions proven to write to database.**
**Only 4/71 have audit logs.**
**0/71 have RLS tests.**

**This flow describes INTENDED behavior. Actual behavior must be verified.**

**Do not implement new features until existing mutations are verified:**
1. Verify database writes for fault actions
2. Add audit logging to all MUTATE actions
3. Test RLS for cross-yacht isolation

---

## FAULT CLUSTER OVERVIEW

### What This Cluster Does

Fault management handles the full lifecycle of technical issues:
- **Report:** User discovers problem
- **Diagnose:** User investigates cause
- **Work Order:** User creates task to fix
- **Resolve:** User fixes problem
- **Close:** User confirms resolution
- **False Alarm:** User marks as non-issue

### Actions in This Cluster (9 total)

| Action | Type | Signature Required? | Tables Written |
|--------|------|---------------------|----------------|
| `report_fault` | MUTATE | Yes | 3 (fault + ledger + audit) |
| `view_fault` | READ | No | 0 (query only) |
| `diagnose_fault` | READ | No | 0 (shows diagnostic info) |
| `add_fault_note` | MUTATE | No | 2 (fault + ledger) |
| `add_fault_photo` | MUTATE | No | 2 (fault + ledger) |
| `create_work_order_from_fault` | MUTATE | Yes | 3 (WO + ledger + audit) |
| `add_to_handover` | MUTATE | No | 2 (handover + ledger) |
| `resolve_fault` | MUTATE | Yes | 3 (fault + ledger + audit) |
| `close_fault` | MUTATE | Yes | 3 (fault + ledger + audit) |

**Undocumented actions (found in handlers, not in registry):**
- `acknowledge_fault` (mutation_light) - Silence alarm, acknowledge awareness
- `reopen_fault` (mutation_light) - Revert closed fault to open
- `mark_fault_false_alarm` (mutation_light) - Mark as non-issue

---

## FAULT STATE MACHINE

```
NULL (no fault)
  ↓
  [report_fault]
  ↓
OPEN (fault reported, needs investigation)
  ↓
  [diagnose_fault] - READ action, no state change
  ↓
DIAGNOSED (cause identified)
  ↓
  [create_work_order_from_fault]
  ↓
WORK_ORDER_CREATED (task created to fix)
  ↓
  [resolve_fault] - user confirms fix applied
  ↓
RESOLVED (fix applied, awaiting verification)
  ↓
  [close_fault] - user confirms problem gone
  ↓
CLOSED (fault complete)

Alternative paths:
  OPEN → [mark_fault_false_alarm] → FALSE_ALARM
  CLOSED → [reopen_fault] → OPEN
```

### State Transition Rules

| From State | To State | Action | Guard Rails |
|------------|----------|--------|-------------|
| NULL | OPEN | `report_fault` | Role: any crew, Signature: Yes |
| OPEN | DIAGNOSED | `diagnose_fault` | READ only, no state change |
| DIAGNOSED | WORK_ORDER_CREATED | `create_work_order_from_fault` | Role: Engineer+, Signature: Yes |
| WORK_ORDER_CREATED | RESOLVED | `resolve_fault` | Role: Engineer+, Signature: Yes |
| RESOLVED | CLOSED | `close_fault` | Role: HOD+, Signature: Yes |
| OPEN | FALSE_ALARM | `mark_fault_false_alarm` | Role: Engineer+, Signature: No |
| CLOSED | OPEN | `reopen_fault` | Role: HOD+, Signature: No |

---

## FAULT SITUATION (User Flow)

### Entry Point: Search

**User query:** `"gen 2 overheating alarm"`

**RAG search returns:**
- Equipment: Generator 2
- Faults: Fault #456 (High Coolant Temp - Open)
- Documents: CAT 3512 Service Manual - Cooling System
- Work Orders: WO-789 (Gen 2 Maintenance - Open)

**User clicks:** Fault #456
→ **Fault Situation activates** (CANDIDATE)

---

### Fault Situation Actions

**User opens fault detail**
→ Situation state: CANDIDATE → ACTIVE

**Micro-actions appear** (context-filtered):

**Primary actions:**
- [Diagnose Fault] (READ - shows diagnostic info, manual sections, related faults)
- [Create Work Order] (MUTATE - requires signature)
- [Add to Handover] (MUTATE - no signature)

**Dropdown (▼ More):**
- View Equipment
- Add Note
- Add Photo
- Close Fault (only if status = RESOLVED)
- Mark False Alarm (only if status = OPEN)

---

## HAPPY PATH: Report → Diagnose → Create WO → Resolve → Close

### Step 1: Report Fault

**User action:** Types `"report gen 2 overheating"` → clicks [Report Fault]

**Form appears:**
```
Equipment: Generator 2 (pre-filled)
Symptom: Overheating (pre-filled from query)
Fault Code: [user selects from dropdown]
Description: [user enters]
Severity: [user selects: Low/Medium/High/Critical]
```

**User clicks [Confirm + Sign]**

**Backend execution:**
```
BEGIN TRANSACTION
1. INSERT pms_faults
   (equipment_id, symptom, fault_code, description, severity, status=OPEN, reported_by, reported_at)
2. INSERT ledger_events
   (event_type=fault_reported, entity_type=fault, entity_id=fault.id, user_id, timestamp, summary="Fault reported: Gen 2 overheating")
3. INSERT pms_audit_log
   (action_id=report_fault, entity_type=fault, entity_id=fault.id, old_state=null, new_state={...}, user_id, signature, timestamp)
COMMIT (or ROLLBACK if any fails)
```

**Success response:**
```json
{
  "success": true,
  "fault_id": "uuid-fault-456",
  "message": "Fault #456 reported",
  "next_actions": ["diagnose_fault", "add_fault_note", "add_to_handover"]
}
```

**Situation state:** ACTIVE (mutation committed)

---

### Step 2: Diagnose Fault (READ Action)

**User clicks:** [Diagnose Fault]

**Backend execution:**
```
Query:
- SELECT manual sections WHERE equipment_id = gen2 AND keyword LIKE 'overheating'
- SELECT faults WHERE equipment_id = gen2 AND symptom = 'overheating' AND created_at > 6_months_ago
- SELECT parts WHERE equipment_id = gen2 AND category = 'cooling_system'
```

**Response shown to user:**
```
Manual Section: CAT 3512 - Section 4.2 (Cooling System Troubleshooting)
Related Faults: Fault #123 (3 months ago - High Coolant Temp - Resolved)
Likely Parts: Coolant pump, Thermostat, Coolant filter
Suggested Actions: Check coolant level, Inspect pump, Check thermostat
```

**No database write. Pure READ action.**

**Situation state:** Still ACTIVE

---

### Step 3: Create Work Order from Fault

**User clicks:** [Create Work Order]

**Form appears:**
```
Title: Fix Generator 2 - High Coolant Temp (pre-filled)
Linked Fault: #456 (auto-linked)
Equipment: Generator 2 (pre-filled)
Description: [user enters]
Priority: [user selects: Low/Medium/High/Urgent]
Assigned To: [user selects crew member]
```

**User clicks [Confirm + Sign]**

**Backend execution:**
```
BEGIN TRANSACTION
1. INSERT pms_work_orders
   (title, linked_fault_id, equipment_id, description, priority, assigned_to, status=ACTIVE, created_by, created_at)
2. UPDATE pms_faults
   SET status=WORK_ORDER_CREATED, work_order_id=wo.id
   WHERE id=fault_id
3. INSERT ledger_events
   (event_type=work_order_created, entity_type=work_order, entity_id=wo.id, user_id, timestamp, summary="WO created from Fault #456")
4. INSERT ledger_events
   (event_type=fault_status_changed, entity_type=fault, entity_id=fault_id, user_id, timestamp, summary="Fault #456 → Work Order Created")
5. INSERT pms_audit_log
   (action_id=create_work_order_from_fault, entity_type=work_order, entity_id=wo.id, old_state=null, new_state={...}, user_id, signature, timestamp)
COMMIT (or ROLLBACK if any fails)
```

**Success response:**
```json
{
  "success": true,
  "work_order_id": "uuid-wo-123",
  "message": "Work Order #123 created",
  "next_actions": ["view_work_order", "add_parts_to_work_order", "assign_work_order"]
}
```

**Situation state:** Transitions from Fault Situation → Work Order Situation (user now focused on WO)

---

### Step 4: Resolve Fault

**User action:** After fixing issue, user types `"resolve fault 456"` → clicks [Resolve Fault]

**Form appears:**
```
Fault: #456 (Gen 2 - High Coolant Temp)
Resolution: [user enters what was done]
Parts Used: [user selects from inventory]
Time Spent: [user enters hours]
```

**User clicks [Confirm + Sign]**

**Backend execution:**
```
BEGIN TRANSACTION
1. UPDATE pms_faults
   SET status=RESOLVED, resolution=..., resolved_by=user_id, resolved_at=now()
   WHERE id=fault_id
2. INSERT ledger_events
   (event_type=fault_resolved, entity_type=fault, entity_id=fault_id, user_id, timestamp, summary="Fault #456 resolved: Replaced coolant pump")
3. INSERT pms_audit_log
   (action_id=resolve_fault, entity_type=fault, entity_id=fault_id, old_state={status:WORK_ORDER_CREATED}, new_state={status:RESOLVED, resolution:...}, user_id, signature, timestamp)
COMMIT (or ROLLBACK if any fails)
```

**Success response:**
```json
{
  "success": true,
  "message": "Fault #456 resolved",
  "next_actions": ["close_fault", "add_to_handover"]
}
```

---

### Step 5: Close Fault

**User action:** After verifying fix, user clicks [Close Fault]

**Confirmation modal:**
```
Close Fault #456?
Status: Resolved
Resolution: Replaced coolant pump
Verification: Has the issue been verified as fixed?
[Cancel] [Confirm + Sign]
```

**User clicks [Confirm + Sign]**

**Backend execution:**
```
BEGIN TRANSACTION
1. UPDATE pms_faults
   SET status=CLOSED, closed_by=user_id, closed_at=now()
   WHERE id=fault_id AND status=RESOLVED
2. INSERT ledger_events
   (event_type=fault_closed, entity_type=fault, entity_id=fault_id, user_id, timestamp, summary="Fault #456 closed")
3. INSERT pms_audit_log
   (action_id=close_fault, entity_type=fault, entity_id=fault_id, old_state={status:RESOLVED}, new_state={status:CLOSED}, user_id, signature, timestamp)
COMMIT (or ROLLBACK if any fails)
```

**Success response:**
```json
{
  "success": true,
  "message": "Fault #456 closed",
  "next_actions": ["view_fault_history", "view_equipment"]
}
```

**Situation state:** Fault complete, suppress further nudges

---

## FAILURE PATHS

### Path 1: False Alarm

**Scenario:** User reports fault, investigates, determines it's not an issue.

**User action:** Clicks [Mark False Alarm]

**Form:**
```
Reason: [user explains why it's false alarm]
```

**Backend:**
```
BEGIN TRANSACTION
1. UPDATE pms_faults
   SET status=FALSE_ALARM, false_alarm_reason=..., closed_by=user_id, closed_at=now()
   WHERE id=fault_id
2. INSERT ledger_events
   (event_type=fault_false_alarm, entity_type=fault, entity_id=fault_id, user_id, timestamp, summary="Fault #456 marked as false alarm")
COMMIT
```

**No audit log required (low-risk action).**

---

### Path 2: Reopen Fault

**Scenario:** Fault was closed, but problem reoccurs.

**User action:** Types `"reopen fault 456"` → clicks [Reopen Fault]

**Form:**
```
Reason for reopen: [user explains]
```

**Backend:**
```
BEGIN TRANSACTION
1. UPDATE pms_faults
   SET status=OPEN, reopened_by=user_id, reopened_at=now(), reopen_reason=...
   WHERE id=fault_id AND status=CLOSED
2. INSERT ledger_events
   (event_type=fault_reopened, entity_type=fault, entity_id=fault_id, user_id, timestamp, summary="Fault #456 reopened")
COMMIT
```

**No audit log required (low-risk action).**

---

### Path 3: Insufficient Information

**Scenario:** User tries to create WO but fault status is still OPEN (not diagnosed).

**User action:** Clicks [Create Work Order]

**System response:**
```
Cannot create work order from fault #456.

Reason: Fault must be diagnosed first.
Current status: OPEN

Available actions:
- Diagnose Fault
- Add Note to Fault
- Add Photo to Fault
```

**No database write. State machine guard prevents invalid transition.**

---

## CONFLICT RESOLUTION

### Conflict 1: Multiple MUTATE Actions After Diagnosis

**Scenario:** User diagnosed fault, now has 3 MUTATE options:
- Create Work Order (fix now)
- Add to Handover (defer to next shift)
- Mark False Alarm (not a real issue)

**UI pattern:**
```
What would you like to do with Fault #456?

Primary:
[Create Work Order] (most common path)

Dropdown (▼ More):
- Add to Handover
- Mark False Alarm
- Add Note
```

**User must choose explicitly. No auto-execution.**

---

### Conflict 2: Fault Already Has Work Order

**Scenario:** User tries to create WO but fault already has one.

**System response:**
```
Fault #456 already has a work order.

Work Order: WO-123 (Status: Active)
Assigned to: Mike (2nd Engineer)

Actions:
- View Work Order
- Add Note to Fault
```

**No duplicate WO allowed. Guard rail prevents.**

---

## AUDIT REQUIREMENTS (Critical for Compliance)

### Actions That MUST Write to Audit Log

| Action | Audit Required? | Why? |
|--------|----------------|------|
| `report_fault` | ✅ Yes | Creates new entity, signature required |
| `create_work_order_from_fault` | ✅ Yes | Creates WO + changes fault state, signature required |
| `resolve_fault` | ✅ Yes | Changes critical state, signature required |
| `close_fault` | ✅ Yes | Final state change, signature required |
| `add_fault_note` | ❌ No | Low-risk, no signature |
| `add_fault_photo` | ❌ No | Low-risk, no signature |
| `add_to_handover` | ❌ No | Low-risk, no signature |

**Rule:** If action requires signature → MUST write audit log.

**Audit log fields (minimum):**
```json
{
  "action_id": "close_fault",
  "entity_type": "fault",
  "entity_id": "uuid-fault-456",
  "old_state": {"status": "RESOLVED"},
  "new_state": {"status": "CLOSED", "closed_by": "user_id", "closed_at": "2026-01-22T14:30:00Z"},
  "user_id": "uuid-user",
  "signature": "base64_signature",
  "timestamp": "2026-01-22T14:30:00Z"
}
```

---

## RLS CHECKPOINTS (Cross-Yacht Isolation)

### Where RLS Must Be Verified

**All fault queries MUST enforce yacht isolation:**

```sql
-- CORRECT (yacht isolation enforced)
SELECT * FROM pms_faults
WHERE id = $1 AND yacht_id = current_yacht_id();

-- INCORRECT (cross-yacht leak)
SELECT * FROM pms_faults
WHERE id = $1;
```

**RLS policies required:**
1. **SELECT:** User can only see faults from their yacht
2. **INSERT:** User can only create faults for their yacht
3. **UPDATE:** User can only update faults from their yacht
4. **DELETE:** No deletes allowed (soft delete via status only)

**Current status:** 0/71 actions tested for RLS. **This is a P0 gap.**

---

## OPEN QUESTIONS

### Q1: Fault Severity Auto-Escalation

**Question:** Should faults auto-escalate severity if not addressed within X hours?

**Options:**
- Manual only (user sets severity, never changes)
- Auto-escalate (Low → Medium after 24h, Medium → High after 48h)
- Hybrid (suggest escalation, require user confirmation)

**Status:** Not defined. For MVP: manual only.

---

### Q2: Fault Deduplication

**Question:** If user reports "gen 2 overheating" twice in 1 hour, should system:
- Create 2 separate faults
- Merge into 1 fault
- Ask user: "Fault #456 already open, add note instead?"

**Status:** Not defined. For MVP: allow duplicates, rely on user to check existing faults.

---

### Q3: Linked Equipment Updates

**Question:** When fault is closed, should equipment status auto-update?

**Options:**
- Manual only (equipment status independent of faults)
- Auto-update (closing fault sets equipment status=OPERATIONAL)
- Suggested update (ask user if equipment is now operational)

**Status:** Not defined. For MVP: manual only.

---

## NEXT CLUSTER FLOWS

After faults.md, create:
1. **work_orders.md** (WO lifecycle, assignment, completion)
2. **inventory.md** (stock checks, adjustments, reorders)
3. **handover.md** (entry creation, draft generation, sign-off)

---

**Status:** Fault cluster flow complete. Ready for work_orders.md.
