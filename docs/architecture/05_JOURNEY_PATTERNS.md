# 05_JOURNEY_PATTERNS.md

**Date:** 2026-01-22
**Purpose:** Global pattern index - reusable journey flow shapes
**Status:** Pattern Library (reference when writing cluster journeys)

---

## WHY THIS EXISTS

As we document 76+ actions across 12 clusters, patterns emerge. Rather than describe the same flow shape 20 times, we define patterns once and reference them.

**This document locks terminology** to prevent drift as documentation scales.

---

## PATTERN DEFINITIONS

### `[SINGLE_STEP]`

**Definition:** Click action → Form (optional) → Confirm → Done

**Characteristics:**
- No intermediate states
- No resumability needed
- Commits in one transaction
- User cannot "save draft"

**Examples:**
- add_to_handover
- add_fault_note
- mark_fault_false_alarm

**Transaction pattern:**
```
BEGIN
  INSERT/UPDATE operational table
  INSERT ledger_events
  [Optional] INSERT audit_log (if signature required)
COMMIT
```

---

### `[MULTI_STEP]`

**Definition:** Start action → Step 1 → Step 2 → ... → Final commit

**Characteristics:**
- Multiple user interactions required
- May or may not be resumable
- State transitions between steps
- Final commit is atomic

**Examples:**
- diagnose_fault → create_work_order_from_fault (2 steps)
- start_receiving_session → check_in_item → commit (3+ steps)

**Transaction pattern:**
```
Step 1: Partial state change (or no change)
Step 2: Partial state change (or no change)
...
Final step: ATOMIC COMMIT (all changes or rollback)
```

---

### `[MULTI_STEP_RESUMABLE]`

**Definition:** Multi-step flow where user can pause and return later

**Characteristics:**
- Incremental mutations saved to database
- Session state persists
- User can navigate away and return
- Cannot commit until all steps complete

**Examples:**
- Receiving session (check items over time)
- Checklist execution (check items throughout day)

**How resumability surfaces:**
- Passive banner: "You have an active receiving session"
- Recent history shows: "Receiving session (in progress)"
- Click to resume from last step

**Rule:** Only flows with incremental mutations are resumable. Critical commits must finish or cancel.

---

### `[LOOPING]`

**Definition:** Repeat same action multiple times before final commit

**Characteristics:**
- User marks/checks items in a list
- Progress tracked locally or in database
- Cannot proceed until all items addressed
- Sign-off at end

**Examples:**
- Checklist: Check item 1, 2, 3... → sign off
- Receiving: Check-in item 1, 2, 3... → commit

**Pattern:**
```
LOOP:
  User interacts with item N
  Mark item N as complete/checked
  IF all items complete:
    Enable [Final Action] button
  ELSE:
    Continue loop
```

---

### `[SIGNATURE_CHAIN]`

**Definition:** Multiple sequential actions, each requiring signature

**Characteristics:**
- Each step is individually signed
- Cannot skip steps
- Audit trail for each signature
- Used for high-compliance workflows

**Examples:**
- Approve purchase → Approve budget → Approve contract (3 signatures)
- Create refit task → Approve scope → Approve cost (3 signatures)

**Pattern:**
```
Step 1: User confirms → Signature required → Audit logged
Step 2: User confirms → Signature required → Audit logged
...
```

**Note:** Rare pattern. Most flows sign once at irreversible commit point.

---

### `[AUTO_CREATE]`

**Definition:** One action automatically triggers creation of another entity

**Characteristics:**
- System creates linked entity without user request
- Triggered by condition (severity, status, rule)
- User sees confirmation of both actions
- Both entities logged separately
- **Commits silently** (no additional user confirmation)

**Examples:**
- report_fault with severity='critical' → auto-creates handover
- execute_checklist with critical failure → auto-creates work order

**Pattern:**
```
User action: report_fault (severity=critical)
System checks: IF severity = critical THEN
  BEGIN TRANSACTION
    INSERT pms_faults
    INSERT handover_entries (auto-created)
    INSERT ledger_events (for fault)
    INSERT ledger_events (for handover)
  COMMIT
```

**UI feedback:**
```
✓ Fault reported
✓ Critical fault added to handover automatically
```

---

### `[AUTO_ESCALATION]`

**Definition:** System proposes follow-up action but requires explicit user confirmation

**Characteristics:**
- System detects condition requiring escalation
- Proposes action to user (doesn't execute automatically)
- User must explicitly confirm or dismiss
- Used for safety/compliance events where auto-commit is too risky

**Difference from `[AUTO_CREATE]`:**
- `[AUTO_CREATE]` = commits silently
- `[AUTO_ESCALATION]` = proposes, waits for confirmation

**Examples:**
- Critical fault detected → System suggests: "Add to handover?" [Yes] [No]
- Compliance breach detected → System suggests: "Notify HOD?" [Yes] [No]
- Safety event logged → System suggests: "Create incident report?" [Yes] [No]

**Pattern:**
```
User action: detect_compliance_breach
System checks: IF breach_severity = high THEN
  Show modal:
    "⚠️ Compliance breach detected"
    "Add to incident log?"
    [Yes] [No]

  IF user clicks [Yes]:
    BEGIN TRANSACTION
      INSERT incident_log
      INSERT ledger_events
    COMMIT
  ELSE:
    (User dismissed, no action taken)
```

**UI feedback:**
```
⚠️ Compliance breach detected
[Create Incident Report?] [Dismiss]
```

**Use sparingly:** Only for high-stakes scenarios where silent auto-create is inappropriate.

---

### `[READ_ONLY]`

**Definition:** Query action with no database mutations

**Characteristics:**
- No form, no confirmation
- Execute immediately on click
- Show results
- No ledger entry (viewing doesn't change state)

**Examples:**
- view_equipment_history
- show_manual_section
- search_documents

**Pattern:**
```
Click action → Query database → Show results
(No writes, no commits)
```

---

### `[CRUD_TEMPLATE]`

**Definition:** Standard create/update/delete pattern for entity management

**Characteristics:**
- Multiple similar actions grouped
- Same flow shape, different entity
- Can be documented in table format

**Examples:**
- Document admin: upload, delete, replace, tag
- Equipment CRUD: create, update, decommission
- Part management: add, update, delete

**Documentation pattern:**
```markdown
## Document Admin Actions

| Action | Form Fields | Validation | Signature |
|--------|-------------|------------|-----------|
| upload_document | File, title, type | Size < 50MB | ❌ |
| delete_document | Confirm only | Cannot undo | ✅ |
| replace_document | New file | Match doc type | ❌ |
| tag_document | Category | Required | ❌ |
```

**This covers 4 actions in one table.**

---

## PATTERN COMBINATIONS

Some journeys use multiple patterns:

**Example: Receiving Session**
- `[MULTI_STEP_RESUMABLE]` - Can pause/resume
- `[LOOPING]` - Check each item
- `[SIGNATURE_AT_END]` - Sign at commit

**Example: Checklist Execution**
- `[LOOPING]` - Check each item
- `[AUTO_CREATE]` - Critical failures create WOs
- `[SIGNATURE_AT_END]` - Sign off at completion

---

## SIGNATURE PLACEMENT PATTERNS

### Pattern A: No Signature (MUTATE_LOW, READ)
- add_note, add_photo, view_history

### Pattern B: Signature at Commit (Most Common)
- Multi-step flows sign once at irreversible point
- Example: Receiving → sign at commit, NOT per item

### Pattern C: Signature Per Step (Rare - SIGNATURE_CHAIN)
- High-compliance workflows only
- Example: Multi-level approval chains

**Default rule:** Sign once at irreversible commit point, not per step.

---

## TERMINOLOGY LOCKS

**Use these terms consistently:**

| Term | Meaning | NOT |
|------|---------|-----|
| **Journey** | User narrative (Sarah's handover) | Flow, path, scenario |
| **Cluster journey** | Functional domain coverage (faults_cluster_journeys.md) | Group, collection |
| **Action card** | Micro-action spec (single action definition) | Action, task, operation |
| **Pattern** | Reusable flow shape (`[SINGLE_STEP]`) | Template, type, category |
| **Situation** | UI state (Fault Situation, Equipment Situation) | Context, mode, view |
| **Avatar** | User role archetype (Sarah, Mike, Chief) | Persona, user type |

**Enforce these terms in all documentation to prevent confusion.**

---

## HOW TO USE PATTERNS IN CLUSTER DOCS

When writing cluster journey files, tag each journey with patterns:

```markdown
### Journey: Report Fault → Handover

**PATTERN:** `[SINGLE_STEP]` `[MUTATE_LOW]` `[NO_SIGNATURE]`

See: [Sarah's Night Shift](../04_USER_JOURNEYS.md#sarahs-night-shift) for full walkthrough.

**Differs from gold:** None - this IS the gold journey.
```

This allows filtering across clusters: "Show me all `[LOOPING]` journeys"

---

## PATTERN EVOLUTION

**For MVP:** These 8 patterns are sufficient.

**Future patterns to consider:**
- `[APPROVAL_CHAIN]` - Multi-actor sequential approvals
- `[BATCH_OPERATION]` - Apply action to multiple entities
- `[SCHEDULED_ACTION]` - Deferred execution
- `[CONDITIONAL_BRANCH]` - Different paths based on entity state

**Do not add new patterns without validating against real use cases.**

---

**Status:** Pattern library locked for Layer 2 scaling.
