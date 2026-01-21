# E014: THRESHOLD VALIDATION REPORT

**Date:** 2026-01-21
**Phase:** 9 - Journey, Trigger, and Threshold Validation
**Status:** COMPLETE

---

## Purpose

Test boundary cases, not happy paths. For each action:
- Minimum signal needed
- Maximum ambiguity tolerated
- Exact reason for suppression (must be explainable)

---

## Critical Finding: Binary Trigger System

The current trigger system uses **boolean conditions only**:

```typescript
// Typical trigger condition
condition: (ctx) => !!ctx.fault?.id
```

**Implications:**
- No confidence scores
- No ambiguity thresholds
- No graduated suppression
- Entity exists = show action

This is fundamentally inadequate for robust decision timing.

---

## Boundary Case Analysis

### Case 1: Vague Intent + Strong Entity

**Scenario:** User searches "check generator" - equipment resolved, intent unclear

| Current Behavior | Expected Behavior |
|-----------------|-------------------|
| All equipment actions shown | Only read actions shown |
| create_work_order visible | Mutations suppressed until intent clarified |
| report_fault visible | report_fault suppressed until problem confirmed |

**Threshold Gap:**
- No intent classification check before mutations
- System assumes "strong entity = ready to act"

**Required Threshold:**
```typescript
// Proposed: Intent must be classified for mutations
condition: (ctx) =>
  !!ctx.equipment?.id &&
  (ctx.intent === 'report_problem' || ctx.intent === 'explicit_fault')
```

---

### Case 2: Strong Intent + Weak Entity

**Scenario:** User says "broken" or "not working" - clear problem, no equipment specified

| Current Behavior | Expected Behavior |
|-----------------|-------------------|
| No actions shown (no entity) | Clarification prompt shown |
| User stuck | System asks "What equipment?" |
| Silent failure | Active disambiguation |

**Threshold Gap:**
- No trigger for "help user resolve entity"
- Strong intent without entity = dead end

**Required Threshold:**
- Intent detected as "report_problem" should trigger clarification flow
- Minimum signal: problem intent alone should surface search/select actions

---

### Case 3: Conflicting Entities

**Scenario:** Search returns equipment, but user's previous context was a fault

| Current Behavior | Expected Behavior |
|-----------------|-------------------|
| Context switches silently | User warned about context change |
| Previous fault context lost | Option to maintain fault context |
| Actions from both contexts shown | Clear hierarchy of contexts |

**Threshold Gap:**
- No conflict detection
- No context persistence logic
- TriggerContext is stateless per-render

**Required Threshold:**
```typescript
// Proposed: Detect context switches
if (newContext.equipment?.id && existingContext.fault?.id) {
  // Warn user or preserve fault context
}
```

---

### Case 4: Repeated Action Attempts

**Scenario:** User tries to close_work_order twice, or report_fault on same equipment repeatedly

| Current Behavior | Expected Behavior |
|-----------------|-------------------|
| Second close attempt fails at API | System shows "already closed" state |
| Duplicate fault created | Warning about existing fault |
| No idempotency awareness | Idempotent actions detected and handled |

**Threshold Gap:**
- Trigger conditions don't check action history
- No "recently completed" suppression
- API is the only validation layer

**Required Threshold:**
```typescript
// Proposed: Check recent actions
condition: (ctx) =>
  !!ctx.work_order?.id &&
  ctx.work_order?.status === 'in_progress' &&
  !ctx.recentActions?.includes('close_work_order')
```

---

### Case 5: Stale Context (Previous Search Leaking Forward)

**Scenario:** User searched for "engine", then searches for unrelated item, but engine context persists

| Current Behavior | Expected Behavior |
|-----------------|-------------------|
| Unknown - depends on component state | Clear context on new search |
| May show engine actions on pump results | Actions match current result only |
| Context scope unclear | Explicit context boundaries |

**Threshold Gap:**
- TriggerContext built from props, not session
- Component-level state management varies
- No explicit context invalidation on navigation

**Required Threshold:**
- Context must have timestamp/scope
- Stale context (>30s? different entity?) should be cleared
- Actions should only appear for active/current entity

---

## Action-by-Action Threshold Analysis

### Fault Actions

| Action | Minimum Signal | Max Ambiguity | Suppression Reason |
|--------|---------------|---------------|-------------------|
| report_fault | equipment.id | None allowed | No equipment context |
| acknowledge_fault | fault.id + user capable | None | Already acknowledged |
| close_fault | fault.id + work complete | Medium (soft close) | Has active WO |
| diagnose_fault | fault.id | High (auto-runs) | Never suppressed |
| view_fault_detail | fault.id | High | Never suppressed |
| update_fault | fault.id | Medium | Fault is closed |
| add_fault_photo | fault.id | Medium | Fault is closed |
| reopen_fault | fault.id + closed | None | Fault is open |
| mark_fault_false_alarm | fault.id | Low | Fault is closed |
| show_manual_section | equipment.id | High | No manual exists |

### Work Order Actions

| Action | Minimum Signal | Max Ambiguity | Suppression Reason |
|--------|---------------|---------------|-------------------|
| create_work_order | equipment.id | Medium | Active WO exists for equipment |
| start_work_order | wo.id + status=open | None | Status is not open |
| close_work_order | wo.id + status=in_progress | Low | Status is not in_progress |
| cancel_work_order | wo.id + HOD role | None | Non-HOD user |
| assign_work_order | wo.id + HOD role | None | Non-HOD user |
| view_work_order_detail | wo.id | High | Never suppressed |
| view_work_order_checklist | wo.id + has_checklist | Medium | No checklist |
| update_work_order | wo.id | Medium | WO is closed |
| add_wo_* | wo.id | Medium | WO is closed/cancelled |
| create_work_order_from_fault | fault.id + !has_wo | None | WO already exists |

### Equipment & Handover Actions

| Action | Minimum Signal | Max Ambiguity | Suppression Reason |
|--------|---------------|---------------|-------------------|
| update_equipment_status | equipment.id | Medium | None currently |
| add_to_handover | any entity | High | No entity context |

### Worklist Actions

| Action | Minimum Signal | Max Ambiguity | Suppression Reason |
|--------|---------------|---------------|-------------------|
| view_worklist | env=shipyard OR wo.id | High | Not in context |
| add_worklist_task | env=shipyard | None | Not in shipyard |
| export_worklist | env=shipyard + HOD | None | Not HOD or not shipyard |

---

## Explainability Requirement

**Rule:** If the system cannot explain why it showed or hid an action → FAIL

### Current Explainability: POOR

```typescript
// Current: No explanation provided
if (!rule) return true;  // Default to showing - no reason given
return rule.condition(context);  // Boolean - no reason given
```

### Required Explainability: RICH

```typescript
// Proposed: Every decision must have a reason
interface TriggerResult {
  show: boolean;
  reason: string;  // Human-readable
  confidence: number;  // 0-1
}

// Example output:
{
  show: false,
  reason: "Work order is closed (status='closed')",
  confidence: 1.0
}
```

---

## Threshold Violations Summary

| Violation Type | Count | Impact |
|---------------|-------|--------|
| No intent check before mutation | 30 | High - accidental mutations |
| No entity disambiguation | 30 | High - wrong target |
| No conflict detection | 30 | Medium - context confusion |
| No repeat detection | 30 | Low - duplicate actions |
| No stale context handling | 30 | Medium - wrong actions |
| No explainability | 30 | High - user confusion |

---

## Recommendations

### Immediate (P0)

1. **Add intent classification check to all mutations**
   - Mutations require `intent !== 'information_query'`
   - Read actions allowed with any intent

2. **Add status checks to all WO/fault mutations**
   - close_work_order: status must be `in_progress`
   - start_work_order: status must be `open`
   - close_fault: status must not be `closed`

### Short-term (P1)

3. **Add explainability to trigger system**
   - Return reason with every trigger evaluation
   - Display suppression reason in UI

4. **Add entity disambiguation flow**
   - Detect strong intent + weak entity
   - Prompt for entity selection

### Medium-term (P2)

5. **Add context conflict detection**
   - Warn when context switches unexpectedly
   - Allow user to preserve previous context

6. **Add repeat action detection**
   - Track recently executed actions
   - Warn or suppress duplicates

---

## Verdict

**THRESHOLD SYSTEM: NON-EXISTENT**

The current trigger system is binary (show/hide) with no thresholds, no ambiguity handling, and no explainability.

**Grade: FAIL**

All 30 actions fail threshold validation because the infrastructure for proper threshold checking does not exist.

---

**Document:** E014_THRESHOLD_REPORT.md
**Completed:** 2026-01-21
