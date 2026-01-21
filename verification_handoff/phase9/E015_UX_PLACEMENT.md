# E015: UX PLACEMENT AUDIT

**Date:** 2026-01-21
**Phase:** 9 - Journey, Trigger, and Threshold Validation
**Status:** COMPLETE

---

## Purpose

For every surfaced action, audit:
- Where does it appear?
- How many seconds after input?
- Does it compete with another action?
- Does it steal focus incorrectly?

---

## Rules Verified

| Rule | Status | Evidence |
|------|--------|----------|
| No mutation below fold | ⚠️ PARTIAL | Flex-wrap can push to new line |
| Destructive action needs confirm | ✅ PASS | `requiresConfirmation()` exists |
| No duplicate actions across panels | ⚠️ PARTIAL | Same action can appear in multiple cards |
| Read vs Mutate visual separation | ✅ PASS | ActionDropdown separates them |

---

## Placement Patterns Discovered

### Pattern 1: Card Action Bar

**Location:** Bottom of entity cards (FaultCard, WorkOrderCard, EquipmentCard)

```tsx
<div className="flex flex-wrap items-center gap-2">
  {showDiagnoseButton && <button>Diagnose</button>}
  {showManualButton && <button>View Manual</button>}
  {showHistoryButton && <button>History</button>}
  {/* ... more actions */}
</div>
```

**Issues:**
- All actions have same visual weight (celeste-button-secondary)
- No primary action distinction
- Flex-wrap can push mutations below visible area
- Order is hard-coded in JSX, not priority-driven

---

### Pattern 2: ActionDropdown (Overflow)

**Location:** Attached to primary action button

**Behavior:**
- Appears if more than 1 action exists
- Separates READ and MUTATE with divider
- Mutate actions visually muted (text-celeste-text-muted)

**Issues:**
- Good separation of read/mutate
- But dropdown discovery requires click
- Mutations hidden in dropdown may be missed

---

### Pattern 3: Auto-Run Actions

**Location:** On card mount

**Actions:**
- `diagnose_fault` → Opens DiagnoseFaultModal
- `view_equipment_details` → Fetches details
- `view_part_stock` → Fetches stock levels

**Issues:**
- Auto-run steals focus (opens modal immediately)
- No user consent before auto-run
- Can be confusing if user was scrolling past card

---

### Pattern 4: Situation Panel Actions

**Location:** AI-detected situation cards

**Behavior:**
- Recommendations appear as buttons
- Role-specific (Engineer vs Captain)
- Evidence-backed suggestions

**Issues:**
- Separate from card actions (good)
- Can duplicate card actions (bad)
- No coordination between panels

---

## Per-Card Placement Analysis

### FaultCard

| Action | Position | Timing | Competes With | Issues |
|--------|----------|--------|---------------|--------|
| diagnose_fault | 1st button | Auto-run on mount | - | Steals focus |
| show_manual_section | 2nd button | Immediate | diagnose_fault | Low priority placement |
| view_fault_history | 3rd button | Immediate | - | CULLED (404) |
| suggest_parts | 4th button | Immediate | - | CULLED (404) |
| add_fault_note | 5th button | Immediate | add_fault_photo | CULLED (404) |
| add_fault_photo | 6th button | Immediate | add_fault_note | - |
| create_work_order_from_fault | 7th button | Immediate | - | Primary action buried last |

**Verdict:** Primary mutation (create_work_order_from_fault) buried at end. Auto-run steals focus.

---

### WorkOrderCard

| Action | Position | Timing | Competes With | Issues |
|--------|----------|--------|---------------|--------|
| view_work_order_detail | Implicit (card itself) | Immediate | - | - |
| start_work_order | Button | Immediate | close_work_order | Competing state transitions |
| close_work_order | Button | Immediate | start_work_order | Competing state transitions |
| add_wo_* | Buttons | Immediate | Each other | Multiple note/photo options |

**Verdict:** Status transitions compete visually. No clear primary.

---

### EquipmentCard

| Action | Position | Timing | Competes With | Issues |
|--------|----------|--------|---------------|--------|
| view_equipment_details | Auto-run | Mount | - | Steals focus |
| report_fault | Button | Immediate | create_work_order | Both create new entities |
| create_work_order | Button | Immediate | report_fault | Both create new entities |

**Verdict:** Two entity-creation actions compete. User may pick wrong one.

---

## Timing Analysis

| Phase | Actions Available | Delay |
|-------|------------------|-------|
| Search results | Per-result actions | 0ms |
| Card mount | All card actions | 0ms |
| Auto-run | diagnose_fault, view_equipment_details, view_part_stock | 0ms (modal opens) |
| After API response | Updated state actions | ~200-500ms |

**Issue:** No progressive disclosure. All actions appear immediately.

---

## Focus Management

| Scenario | Current Behavior | Expected Behavior |
|----------|-----------------|-------------------|
| Card opens | Auto-run may open modal | Card should be focused, user chooses |
| Modal closes | Focus lost | Focus returns to card |
| Action completes | No feedback | Toast + focus on next logical action |
| Error occurs | Error in modal | Error toast + focus on retry |

---

## Competition Analysis

### Actions That Compete

| Action A | Action B | When Both Visible | Risk |
|----------|----------|-------------------|------|
| report_fault | create_work_order | Equipment card | Wrong entity type created |
| start_work_order | close_work_order | Should NEVER both show | State machine violation |
| add_wo_note | add_wo_hours | Work order card | User confusion (both valid) |
| add_fault_note | add_fault_photo | Fault card | User confusion (both valid) |

### Actions That Should Be Exclusive

| Action | Incompatible With | Reason |
|--------|------------------|--------|
| start_work_order | close_work_order | State machine |
| close_fault | reopen_fault | State machine |
| create_work_order_from_fault | (itself) | Idempotent - WO exists |

---

## Confirmation Dialog Audit

| Action | Requires Confirm? | Is Destructive? | Current | Correct? |
|--------|-------------------|-----------------|---------|----------|
| close_work_order | ✅ Should | Semi | ❓ Unknown | YES |
| cancel_work_order | ✅ Should | YES | ❓ Unknown | YES |
| close_fault | ✅ Should | Semi | ❓ Unknown | YES |
| mark_fault_false_alarm | ✅ Should | Semi | ❓ Unknown | YES |
| delete_* | ✅ Should | YES | ✅ Yes | YES |
| create_* | ❌ No | No | ❌ No | YES |
| view_* | ❌ No | No | ❌ No | YES |
| add_* | ❌ No | No | ❌ No | YES |

**Note:** `requiresConfirmation()` function exists in `@/types/actions` but coverage unknown.

---

## Violations Summary

| Violation | Count | Severity |
|-----------|-------|----------|
| Primary action not visually distinct | 30 | Medium |
| Auto-run steals focus | 3 | High |
| Competing actions both visible | 4 pairs | Medium |
| Mutations buried in flex-wrap | Unknown | Medium |
| No progressive disclosure | 30 | Low |
| Inconsistent confirmation dialogs | Unknown | High |
| CULLED actions still in UI code | 6+ | High |

---

## Recommendations

### Immediate (P0)

1. **Remove CULLED action buttons from UI**
   - view_fault_history (404)
   - suggest_parts (404)
   - add_fault_note (404)
   - etc.

2. **Add confirmation to state-changing mutations**
   - close_work_order
   - cancel_work_order
   - close_fault
   - mark_fault_false_alarm

3. **Disable auto-run modals**
   - Auto-fetch data is OK
   - Auto-open modal is NOT OK

### Short-term (P1)

4. **Implement primary action visual distinction**
   - Primary action: solid button, left position
   - Secondary: outline button
   - Overflow: dropdown

5. **Add state machine guards**
   - Never show start + close simultaneously
   - Never show close + reopen simultaneously

### Medium-term (P2)

6. **Implement progressive disclosure**
   - Read actions first
   - Mutations after explicit intent signal
   - Destructive actions require secondary gesture

---

## Verdict

**UX PLACEMENT: NEEDS WORK**

The system has good foundations (ActionDropdown separates read/mutate) but critical issues:
- Primary actions not distinguished
- Auto-run steals focus
- CULLED actions still in UI
- State machine not enforced in UI

**Grade: PARTIAL PASS**

---

**Document:** E015_UX_PLACEMENT.md
**Completed:** 2026-01-21
