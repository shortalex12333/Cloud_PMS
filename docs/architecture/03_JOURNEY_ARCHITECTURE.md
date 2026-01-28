# 03_JOURNEY_ARCHITECTURE.md

**Date:** 2026-01-22
**Purpose:** How actions connect, context flows, and user journeys unfold
**Status:** Layer A - Core Architecture (Journey Layer)

---

## WHAT THIS DOCUMENT COVERS

**COMPLETE_ACTION_EXECUTION_CATALOG.md documents:**
- WHAT each action writes (tables, columns, validations)
- WHAT inputs each action requires
- WHAT database operations execute

**THIS DOCUMENT documents:**
- HOW actions connect in user journeys
- WHERE context comes from when pre-filling forms
- WHEN actions become available (triggers/thresholds)
- WHY certain actions suggest others (pattern recognition)
- HOW system handles edge cases (vague queries, conflicts)

**This is the missing connective tissue between atomic actions and user experience.**

---

## CONTEXT PRESERVATION ARCHITECTURE

### The Context Problem

**User Journey:**
```
1. User searches: "gen 2 overheating again"
2. System extracts: {equipment: "Gen 2", symptom: "overheating", urgency_flag: "again"}
3. User clicks fault result → Fault Situation activates
4. User clicks [Add to Handover]
5. Form appears pre-filled with: "Gen 2 - Overheating (recurring)"
```

**Question:** HOW does the handover form know to pre-fill with "Gen 2 - Overheating (recurring)"?

**Answer:** Active Situation State Context.

---

### Active Situation State (Session Context)

When a situation activates (user clicks result), the system creates a **situation context object** that persists for the session:

```typescript
interface SituationContext {
  situation_type: 'equipment' | 'document' | 'inventory' | 'work_order' | 'fault';
  state: 'IDLE' | 'CANDIDATE' | 'ACTIVE';

  // Original query preservation
  original_query: string;                    // "gen 2 overheating again"
  extracted_entities: {
    equipment_id?: UUID;
    equipment_name?: string;                 // "Generator 2"
    symptom?: string;                        // "overheating"
    urgency_flags?: string[];                // ["again", "recurring"]
    fault_id?: UUID;
    part_id?: UUID;
    // ... other entities
  };

  // Current entity in focus
  primary_entity_type: string;               // "fault"
  primary_entity_id: UUID;                   // fault_id
  primary_entity_data: object;               // Full fault record

  // Related entities (cross-pollination)
  linked_entities: {
    equipment?: { id: UUID, name: string };
    work_order?: { id: UUID, title: string };
    parts?: Array<{ id: UUID, part_number: string }>;
  };

  // Timestamps
  activated_at: timestamp;
  last_action_at: timestamp;
  expires_at: timestamp;                     // 30 min idle timeout
}
```

---

### Context Flow: Search → Action Pre-fill

**Step-by-step context preservation:**

#### 1. Search Query Processing
```
User types: "gen 2 overheating again"
↓
Backend extracts:
{
  entities: {
    equipment_name: "Generator 2",
    equipment_id: "uuid-gen2",
    symptom: "overheating"
  },
  urgency_signals: ["again", "recurring"],
  intent_keywords: []
}
↓
Return search results grouped by domain
```

#### 2. User Clicks Fault Result
```
User clicks: Fault #456 (Gen 2 - High Coolant Temp)
↓
Fault Situation ACTIVATES
↓
Create SituationContext:
{
  situation_type: 'fault',
  state: 'ACTIVE',
  original_query: "gen 2 overheating again",
  extracted_entities: {
    equipment_id: "uuid-gen2",
    equipment_name: "Generator 2",
    symptom: "overheating",
    urgency_flags: ["again"]
  },
  primary_entity_type: 'fault',
  primary_entity_id: "uuid-fault-456",
  primary_entity_data: { ... fault record ... },
  linked_entities: {
    equipment: { id: "uuid-gen2", name: "Generator 2" }
  }
}
↓
Store in session state (Redis or client state management)
```

#### 3. User Clicks [Add to Handover]
```
Frontend calls: create_handover action
↓
Backend retrieves SituationContext from session
↓
Pre-fill form:
{
  summary: "{equipment_name} - {symptom} ({urgency_flags})",
  // Becomes: "Generator 2 - Overheating (recurring)"

  entity_type: 'fault',
  entity_id: "uuid-fault-456",
  priority: fault.severity,  // Map severity → priority
  details: fault.description
}
↓
Show form to user (user can edit before submitting)
```

---

### Pre-fill Rules by Action

| Action | Pre-fill Sources | User Can Edit |
|--------|------------------|---------------|
| **create_handover** | summary: `{equipment_name} - {symptom} ({urgency_flags})`<br>entity_type: from situation<br>entity_id: from primary_entity<br>priority: from fault.severity | ✅ All fields |
| **create_work_order_from_fault** | title: `"Fix: " + fault.description.substring(0,50)`<br>description: fault.diagnosis<br>equipment_id: fault.equipment_id<br>priority: Map severity → priority | ✅ Title, description, priority<br>❌ Equipment (locked) |
| **adjust_inventory** | part_id: from situation<br>location: part.location | ✅ Quantity<br>❌ Part (locked) |
| **add_fault_note** | fault_id: from situation<br>equipment_context: from linked_entities | ✅ Note text<br>❌ Fault (locked) |

**General Rule:** Primary entity locked, derived fields suggested, free-text editable.

---

### Context Lifetime and Expiry

**When does context expire?**

| Event | Context Behavior |
|-------|------------------|
| **User switches situation** | Old context archived, new context created |
| **User executes MUTATE action** | Context persists (for follow-up actions) |
| **30 min idle** | Context expires, cleared from session |
| **User returns to search** | Context moves to CANDIDATE (can reactivate) |
| **User closes tab** | Context cleared |

**Context preservation for follow-ups:**
After user executes `diagnose_fault`:
- Context remains ACTIVE
- Next suggested action: `create_work_order_from_fault`
- Form pre-fills from diagnosis + context

---

## ACTION SEQUENCE PATTERNS (User Journeys)

### Pattern 1: Fault Investigation → Resolution

**Common Flow:**
```
1. report_fault
   ↓ (Context: fault created, equipment linked)
2. diagnose_fault
   ↓ (Context: diagnosis added, manual_reference captured)
3. create_work_order_from_fault
   ↓ (Context: WO created, fault.status = 'work_created')
4. add_to_handover
   ↓ (Context: handover created, links fault + WO)
5. [Later] close_work_order
   ↓ (Context: WO closed, parts consumed)
6. close_fault
   ✓ (Journey complete)
```

**Context Cross-Pollination:**
- Step 1: `fault.equipment_id` = equipment UUID
- Step 3: `work_order.fault_id` = fault UUID, `fault.work_order_id` = WO UUID
- Step 4: `handover.entity_type` = 'fault', `handover.entity_id` = fault UUID

**Trigger Rules:**
| After Action | Suggest Next Action | Confidence Threshold |
|--------------|---------------------|----------------------|
| `report_fault` | `diagnose_fault` | 0.8 (if severity >= medium) |
| `diagnose_fault` | `create_work_order_from_fault` | 0.9 (if root_cause identified) |
| `create_work_order_from_fault` | `add_to_handover` | 0.7 (if priority >= high) |
| `close_work_order` | `close_fault` | 0.9 (if fault.work_order_id matches) |

---

### Pattern 2: Preventive Maintenance → Parts → Execution

**Common Flow:**
```
1. view_pm_due_list
   ↓ (Context: PM task due, equipment identified)
2. search_parts
   ↓ (Context: required parts identified)
3. add_to_shopping_list (if parts not in stock)
   ↓ (Context: shopping items created, linked to PM)
4. [Later] start_receiving_session
   ↓ (Context: parts received, inventory updated)
5. record_pm_completion
   ✓ (Journey complete, next PM scheduled)
```

**Context Cross-Pollination:**
- Step 2: `shopping_list_item.pm_task_id` = PM task UUID
- Step 4: `receiving_session.po_id` links to shopping list
- Step 5: `pm_completion.parts_used` links to inventory adjustments

---

### Pattern 3: Receiving Session (Multi-Step State Machine)

**Flow:**
```
1. start_receiving_session
   ↓ Creates session + pre-populates receiving_items from shopping_list
   ↓ Session state: 'active'

2. check_in_item (repeated for each item)
   ↓ User marks quantity_received, checks for discrepancies
   ↓ Item state: 'checked' or 'discrepancy'

3. [If discrepancy] upload_discrepancy_photo
   ↓ Photo linked to receiving_item

4. commit_receiving_session
   ↓ Updates inventory, closes shopping_list items
   ↓ Session state: 'committed'
   ✓ Journey complete
```

**Session Context Preservation:**
```typescript
interface ReceivingSessionContext extends SituationContext {
  session_id: UUID;
  session_status: 'active' | 'committed' | 'cancelled';
  items: Array<{
    receiving_item_id: UUID;
    part_id: UUID;
    part_number: string;
    quantity_expected: number;
    quantity_received: number;
    checked: boolean;
    current_item_index: number;  // Track progress
  }>;
  total_items: number;
  checked_items: number;
  discrepancies: number;
}
```

**Navigation:**
- User can navigate between items within session
- Context preserves session_id across all check_in_item calls
- Cannot start new session while one is active

---

## CROSS-POLLINATION MATRIX

### Entity Relationships Created by Actions

| Action | Primary Entity | Linked Entities | Relationship Fields |
|--------|----------------|-----------------|---------------------|
| `report_fault` | fault | equipment | `fault.equipment_id` |
| `report_fault` (if critical) | fault | equipment, handover | `fault.equipment_id`, auto-creates `handover.entity_id = fault.id` |
| `create_work_order_from_fault` | work_order | fault, equipment | `work_order.fault_id`, `fault.work_order_id`, `work_order.equipment_id` |
| `add_to_handover` | handover | fault/WO/equipment | `handover.entity_type`, `handover.entity_id` |
| `add_wo_part` | work_order_parts | work_order, part | `work_order_parts.work_order_id`, `work_order_parts.part_id` |
| `record_pm_completion` | pm_completion | pm_schedule, work_order | `pm_completion.pm_schedule_id`, `pm_completion.work_order_id` (optional) |
| `adjust_inventory` (from WO) | inventory_transaction | part, work_order | `inventory_transaction.part_id`, `inventory_transaction.work_order_id` |
| `commit_receiving_session` | inventory_transaction | receiving_session, part, shopping_list | Multiple links |

### Auto-Create Rules

**When one action automatically creates another entity:**

| Trigger Action | Condition | Auto-Created Entity | Why |
|----------------|-----------|---------------------|-----|
| `report_fault` | severity = 'critical' | `handover` | Critical faults must be communicated to next shift |
| `execute_checklist` | item fails + is_critical = true | `work_order` | Failed critical checks require immediate work orders |
| `commit_receiving_session` | item has discrepancy | (Optional) `work_order` | Damaged/wrong parts may need corrective action |

**Rule:** Auto-creates ONLY for high-priority scenarios where action is deterministic and required for safety/compliance.

---

## TRIGGER AND THRESHOLD FRAMEWORK

**⚠️ IMPORTANT: This section uses the ACTUAL framework from COMPLETE_ACTION_EXECUTION_CATALOG.md**

**What's documented (catalog lines cited):** 3 follow-up patterns only
**What's NOT documented:** Scoring weights, confidence thresholds, priority ordering
**What's proposed:** Contradiction detection framework (extends catalog pattern)

---

### What's Defined in the Catalog (Source of Truth)

The COMPLETE_ACTION_EXECUTION_CATALOG.md documents **3 follow-up patterns:**

#### 1. Auto-Create on Critical Conditions

| Trigger Action | Condition | Auto-Created Entity | Source |
|----------------|-----------|---------------------|--------|
| `report_fault` | severity = 'critical' | handover | Catalog: ACTION 1.1, line 173 |
| `execute_checklist` | item fails + is_critical = true | work_order | Catalog: ACTION 9.1, line 1467 |

**Rule:** System automatically creates linked entity when safety/compliance requires immediate action.

#### 2. Becomes Available (Precondition-Based)

| After Action | Next Action Available | Precondition | Source |
|--------------|----------------------|--------------|--------|
| `diagnose_fault` | `create_work_order_from_fault` | fault.status = 'diagnosed' | Catalog: ACTION 1.3, line 357 |

**Rule:** Action "becomes available" when entity reaches required state. Binary condition (available or not), not a score.

#### 3. Multi-Step Sequences

| Action | Step | Next Step | State Check |
|--------|------|-----------|-------------|
| `start_receiving_session` | 1 | `check_in_item` | session.status = 'active' |
| `check_in_item` | 2 | `check_in_item` (loop) OR `commit_receiving_session` | All items checked? |
| `commit_receiving_session` | 3 | END | session.status = 'committed' |

**Rule:** Multi-step flows have explicit step ordering. User can only proceed if previous step completed.

---

### What's NOT Defined (Proposed Framework)

The catalog does NOT specify:
- Confidence scores or weights for action suggestions
- Priority ordering when multiple actions are valid
- How to handle contradictory user requests
- Pattern recognition for user sequences

**For MVP:** Use simple precondition checks (binary available/not available). No scoring.

---

### Action Availability Rules (From Catalog)

**How to determine if action should appear in UI:**

```typescript
// Precondition-based availability (catalog-defined)
function isActionAvailable(
  action_id: string,
  entity: object,
  context: SituationContext
): boolean {
  // Check entity state preconditions
  switch(action_id) {
    case 'create_work_order_from_fault':
      return entity.status === 'diagnosed';

    case 'check_in_item':
      return context.receiving_session?.status === 'active';

    case 'commit_receiving_session':
      return context.receiving_session?.all_items_checked === true;

    case 'close_fault':
      return entity.status === 'resolved';

    // ... other precondition checks

    default:
      // If no preconditions defined, action is available
      return true;
  }
}
```

**Rule:** Actions appear when preconditions met. No scoring, no weights. Binary available/not available.

---

## CONTRADICTION DETECTION FRAMEWORK

### Extending the Catalog Pattern for Clashes

The catalog defines preconditions for when actions are available. **We extend this pattern to detect contradictions:**

#### Pattern 1: Mutually Exclusive Actions

**Definition:** Two actions that cannot both be valid at the same time.

| Action A | Action B | Why Mutually Exclusive | Detection Rule |
|----------|----------|------------------------|----------------|
| `close_fault` | `reopen_fault` | Fault can't be both closed and reopened | `fault.status === 'closed'` blocks `close_fault`, enables `reopen_fault` |
| `mark_fault_false_alarm` | `create_work_order_from_fault` | False alarms don't need work orders | If user clicks both → Show: "Fault marked as false alarm. Work order not needed." |
| `delete_part` | `adjust_inventory` | Can't adjust inventory for deleted part | `part.deleted_at !== null` blocks `adjust_inventory` |

**Resolution:** If user requests contradictory actions → Show error explaining why only one is valid.

---

#### Pattern 2: Contradictory Entity References

**Definition:** User query mentions conflicting entities.

**Example:** `"gen 2 chiller overheating"`
- Entity A: Generator 2 (equipment)
- Entity B: Galley Chiller (equipment)
- Contradiction: Two different equipment IDs

**Detection:**
```typescript
function detectEntityContradictions(
  extracted_entities: ExtractedEntities
): Contradiction | null {
  // Check: Multiple equipment with similar confidence
  if (extracted_entities.equipment.length > 1) {
    const confidences = extracted_entities.equipment.map(e => e.confidence);
    const maxConf = Math.max(...confidences);
    const similar = confidences.filter(c => c >= maxConf - 0.2);

    if (similar.length > 1) {
      return {
        type: 'AMBIGUOUS_ENTITY',
        entities: extracted_entities.equipment.filter(e => e.confidence >= maxConf - 0.2),
        resolution: 'DISAMBIGUATE'
      };
    }
  }

  return null;
}
```

**Resolution:** Disambiguation UI (already documented in Edge Case Playbook).

---

#### Pattern 3: State Transition Conflicts

**Definition:** User requests action that conflicts with current entity state.

| Current State | Requested Action | Conflict Reason | Auto-Resolution |
|---------------|------------------|-----------------|-----------------|
| `fault.status = 'reported'` | `close_fault` | Must be resolved first | Show: "Fault must be resolved before closing. Available: [Diagnose], [Mark False Alarm]" |
| `work_order.status = 'completed'` | `start_work_order` | Already complete | Show: "Work order already completed. Available: [Reopen], [View Details]" |
| `receiving_session.status = 'committed'` | `check_in_item` | Session closed | Show: "Receiving session already committed. Start new session to receive more items." |

**Detection:**
```typescript
function detectStateConflict(
  action_id: string,
  entity: object
): Conflict | null {
  const precondition = PRECONDITIONS[action_id];
  if (!precondition) return null;

  const valid = precondition(entity);
  if (!valid) {
    return {
      type: 'STATE_CONFLICT',
      action: action_id,
      entity_state: entity.status,
      required_state: precondition.required_state,
      resolution: 'EXPLAIN_AND_SUGGEST_VALID'
    };
  }

  return null;
}
```

**Resolution:** Explain why invalid + suggest valid next actions.

---

#### Pattern 4: Sequence Order Violations

**Definition:** User tries to skip required step in multi-step flow.

| Flow | Required Order | Violation Example | Detection |
|------|----------------|-------------------|-----------|
| Receiving | start_receiving_session → check_in_item → commit | User tries `commit` without checking items | `receiving_items.filter(i => !i.checked).length > 0` |
| Fault Resolution | report → diagnose → create_wo → resolve → close | User tries `close` before `resolve` | `fault.status !== 'resolved'` |

**Resolution:**
```typescript
function detectSequenceViolation(
  action_id: string,
  entity: object
): SequenceViolation | null {
  if (action_id === 'commit_receiving_session') {
    const unchecked = entity.receiving_items.filter(i => !i.checked);
    if (unchecked.length > 0) {
      return {
        type: 'SEQUENCE_VIOLATION',
        message: `Cannot commit: ${unchecked.length} items not checked`,
        required_action: 'check_in_item',
        resolution: 'BLOCK_AND_REDIRECT'
      };
    }
  }

  return null;
}
```

---

#### Pattern 5: Permission vs. State Clashes

**Definition:** User has permission for action, but entity state forbids it.

**Example:**
- User = Chief Engineer (has permission for `close_fault`)
- Fault status = 'reported' (state forbids `close_fault`)

**Conflict:** Permission says YES, state says NO.

**Resolution Priority:**
1. **State wins.** Show: "Fault must be resolved before closing."
2. Suggest valid actions user has permission for
3. Explain state requirement

---

### Contradiction Resolution UI Pattern

**Proposed pattern for all contradictions:**

```
[ERROR/WARNING ICON] Cannot {requested_action}

Reason: {why_invalid}

Current state: {entity.status}
Required state: {precondition.required_state}

Available actions:
- [Valid Action 1]
- [Valid Action 2]
- [Valid Action 3]

[Cancel] [Choose Action]
```

---

### Contradiction Logging

**All detected contradictions MUST be logged for:**
- Debugging user confusion
- Identifying unclear UX patterns
- Training better entity extraction

```typescript
interface ContradictionLog {
  type: 'AMBIGUOUS_ENTITY' | 'STATE_CONFLICT' | 'SEQUENCE_VIOLATION' | 'PERMISSION_STATE_CLASH';
  user_id: UUID;
  yacht_id: UUID;
  query: string;
  requested_action: string;
  entity_type: string;
  entity_id: UUID;
  entity_state: object;
  resolution_shown: string;
  user_choice: string | null;
  timestamp: timestamp;
}
```

---

## PATTERN RECOGNITION (Future - NOT MVP)

**NOT DEFINED for MVP.** Future enhancement: Learn from user action sequences to predict next likely action.

**For MVP:** Use only precondition-based availability. No ML, no scoring.

---

## EDGE CASE PLAYBOOK

### Case 1: Vague Query

**Scenario:** User types `"fix gen 2"`

**Problem:** Too vague. System cannot determine if user wants to:
- Create work order
- View existing work orders
- Diagnose a fault
- View equipment history

**Resolution:**
```
1. System extracts: equipment = "Gen 2"
2. System cannot extract: intent (no action keyword)
3. Return search results grouped:
   - Equipment: Generator 2
   - Active Faults: Fault #456 (High Coolant Temp)
   - Active Work Orders: WO-789 (Gen 2 Maintenance)
   - Documents: Gen 2 Manual
4. NO ACTIONS suggested in search results
5. Wait for user to click
6. User clicks fault → Fault Situation → Actions appear
```

**Rule:** If query is vague → show options, let user clarify by clicking.

---

### Case 2: Contradictory Entities

**Scenario:** User types `"gen 2 chiller overheating"`

**Problem:** Generator 2 and Chiller are different equipment.

**Resolution:**
```
1. System extracts: equipment candidates = ["Generator 2", "Galley Chiller"]
2. System extracts: symptom = "overheating"
3. Confidence for each: Gen 2 (0.6), Chiller (0.6)
4. Both below 0.7 threshold for auto-selection
5. Show disambiguation UI:

   "Which equipment did you mean?"
   ○ Generator 2 (Engine Room)
   ○ Galley Chiller (Deck 2)
   [Cancel]

6. User selects → Re-run query with selected equipment
```

**Rule:** If multiple entities match with similar confidence → disambiguate.

---

### Case 3: Missing Required Entity

**Scenario:** User types `"create work order"`

**Problem:** Work orders require equipment_id. No equipment specified.

**Resolution:**
```
1. System extracts: intent = "create_work_order"
2. System extracts: equipment = NULL
3. Check preconditions: equipment_id REQUIRED
4. Show form with equipment_id as required field (empty):

   "Create Work Order"
   Equipment: [Dropdown - user must select]
   Title: [Text field]
   Description: [Text area]
   Priority: [Dropdown]

5. User fills form → Execute action
```

**Rule:** If required entity missing → show form with required field empty, force user to fill.

---

### Case 4: Action Not Available (Precondition Failed)

**Scenario:** User clicks [Close Fault] on fault with status = 'reported' (not 'resolved')

**Problem:** Fault must be resolved before closing.

**Resolution:**
```
1. User clicks [Close Fault]
2. System checks: fault.status = 'reported' (not 'resolved')
3. Precondition failed
4. Show error modal:

   "Cannot close fault #456"

   Reason: Fault must be resolved before closing.
   Current status: Reported

   Available actions:
   - Diagnose Fault
   - Create Work Order
   - Mark as False Alarm
   [OK]

5. User clicks OK → Returns to fault detail
```

**Rule:** If precondition fails → explain why, suggest valid next actions.

---

### Case 5: Duplicate Entity Creation

**Scenario:** User searches `"gen 2 overheating"`, finds Fault #456 (open), tries to report new fault on same equipment.

**Problem:** Duplicate fault reporting wastes time.

**Resolution (Optional - Not MVP):**
```
1. User clicks [Report Fault]
2. User selects: Equipment = Gen 2, Symptom = Overheating
3. System queries: SELECT * FROM faults WHERE equipment_id = gen2 AND symptom LIKE '%overheating%' AND status IN ('reported', 'acknowledged', 'diagnosed', 'work_created')
4. Found: Fault #456 (still open)
5. Show warning modal:

   "Similar fault already exists"

   Fault #456: Gen 2 - High Coolant Temp (Status: Diagnosed)
   Reported: 2 days ago by Mike

   Do you want to:
   ○ View existing fault
   ○ Report as new fault (if different issue)
   [Cancel]

6. User chooses
```

**Rule (Future):** Check for duplicate faults before creating. For MVP: allow duplicates, rely on user to search first.

---

## STATE MACHINE GUARDRAILS

### Fault State Transitions

**Valid transitions:**
```
NULL → reported (via report_fault)
reported → acknowledged (via acknowledge_fault)
reported → diagnosed (via diagnose_fault)
acknowledged → diagnosed (via diagnose_fault)
diagnosed → work_created (via create_work_order_from_fault)
work_created → resolved (via resolve_fault)
resolved → closed (via close_fault)

Special transitions:
reported → false_alarm (via mark_fault_false_alarm)
closed → reported (via reopen_fault)
```

**Invalid transitions (blocked by preconditions):**
```
reported → closed (Cannot skip diagnosis → WO → resolution)
diagnosed → closed (Cannot skip WO creation)
```

**Enforcement:** Each action's validation checks current state before allowing transition.

---

### Work Order State Transitions

**Valid transitions:**
```
NULL → draft (via create_work_order)
draft → active (via start_work_order)
active → completed (via close_work_order)
draft → cancelled (via cancel_work_order)
active → cancelled (via cancel_work_order)

Special:
completed → active (via reopen_work_order - not in catalog, future)
```

**Guards:**
- Cannot close WO if no hours logged (optional guard, configurable)
- Cannot start WO if no assignment (optional guard)
- Cannot cancel WO if already completed

---

## CONTEXT-AWARE ACTION FILTERING

### Dropdown Prioritization Rules

When multiple actions are valid, how to order them in dropdown?

**Priority factors:**
1. **Follow-up score** (from trigger matrix) - 40%
2. **User query match** (keyword presence) - 30%
3. **User role access** (some actions limited) - 15%
4. **Entity state compatibility** (preconditions met) - 15%

**Example: Fault Situation (diagnosed fault)**

All valid actions:
- create_work_order_from_fault (score: 0.9) → Primary button
- add_to_handover (score: 0.7) → Secondary button
- add_fault_note (score: 0.5) → Dropdown
- add_fault_photo (score: 0.45) → Dropdown
- mark_fault_false_alarm (score: 0.3) → Dropdown (low relevance)
- close_fault (score: 0.0) → Hidden (precondition failed: must be resolved first)

---

## OPEN QUESTIONS

### Q1: Context Persistence Across Page Refreshes

**Question:** If user refreshes page mid-journey, should context be restored?

**Options:**
- A: Session stored server-side (Redis), restored on refresh
- B: Client-side only (localStorage), lost on refresh
- C: Hybrid (store session_id, re-fetch situation context)

**Status:** Not defined for MVP. Assume client-side only (context lost on refresh).

---

### Q2: Context Sharing Across Users

**Question:** If Chief Engineer creates handover from fault, can 2nd Engineer see the same context when they view it?

**Options:**
- A: Context is per-user (2nd Engineer sees blank context)
- B: Context is per-entity (2nd Engineer sees Chief's context)

**Status:** Not defined. For MVP: context is per-user session (not shared).

---

### Q3: Multi-Tab Context Isolation

**Question:** If user has 2 tabs open, do they share situation context?

**Options:**
- A: Shared (both tabs see same active situation)
- B: Isolated (each tab has own situation)

**Status:** Not defined. For MVP: assume single tab (no multi-tab support).

---

## NEXT STEPS

1. ✅ Layer A complete (Global Router + Journey Architecture)
2. ⏳ Layer B: Cluster flows (faults.md complete, need work_orders.md, inventory.md, handover.md)
3. ⏳ Layer C: Action cards (gold set - top 10 actions with full journey integration)

---

**Status:** Journey architecture defined. Context preservation, action sequences, cross-pollination, triggers, and edge cases documented. Ready for Layer B cluster flows.
