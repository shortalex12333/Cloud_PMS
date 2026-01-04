# Action Execution Contract
## CelesteOS Microaction Router - Production Policy

---

## 1. Execution Classes

Every predicted action falls into one of three runtime behaviors:

### Class A: Auto-Execute
**Criteria:**
- Action is READ-ONLY (no state change)
- Router confidence > threshold (TBD, start at 0.8)
- No competing action within Δ confidence

**Behavior:** Execute immediately, show result

**Examples:** `show_equipment_overview`, `search_documents`, `diagnose_fault`, `view_handover`

---

### Class B: Suggest (Chips)
**Criteria:**
- Action confidence below threshold, OR
- Multiple plausible actions (suggestion-worthy collision), OR
- Action is state-changing but low-risk

**Behavior:**
- Show primary action as chip + 2-3 alternates
- Run broad search underneath
- Log which chip user selects

**Examples:** `add_to_handover` (when context ambiguous), `generate_summary` vs `generate_audit_pack`

---

### Class C: Confirm (Gated)
**Criteria:**
- Action is DESTRUCTIVE or HIGH-RISK
- Action modifies compliance/certification data
- Action affects other users (assignments, shares)

**Behavior:**
- NEVER auto-execute
- Show confirmation dialog with entity summary
- Require explicit user confirmation
- Log confirmation + outcome

**Gated Actions (ALWAYS require confirmation):**
```
# Destructive
archive_document
close_work_order

# Compliance-affecting
log_hours_of_rest
submit_compliance_report
upload_certificate_document
update_certificate_metadata

# Multi-user impact
assign_work_order
assign_task
share_document
share_with_shipyard

# Financial
approve_purchase_order
create_purchase_order
order_part

# Bulk operations
export_compliance_logs
export_handover
```

---

## 2. Hard FP Definition (Sacred)

**Hard FP = A dangerous state change was EXECUTED without user intent**

This is NOT the same as "router predicted a state-changing action."

### Hard FP = 0 is maintained by:
1. Gating all destructive actions behind confirmation (Class C)
2. Never auto-executing state-changing actions on low confidence
3. Runtime guards, not just routing accuracy

### What counts as Hard FP:
- ❌ User said "show generator history" → system EXECUTED `close_work_order`
- ❌ User said "check stock" → system EXECUTED `order_part`

### What does NOT count as Hard FP:
- ✅ Router predicted `add_to_handover` but showed as chip (not executed)
- ✅ Router predicted `upload_document` but confirmation dialog shown
- ✅ Router predicted wrong read-only action (soft misroute)

---

## 3. Collision Classification

When router triggers but action differs from label:

| Type | Count | Runtime Behavior |
|------|-------|------------------|
| True Routing Bug | 4 | Fix in code |
| Acceptable Soft Route | 45 | Auto-execute OK |
| Suggestion-Worthy | 22 | Show as chips |

### True Routing Bugs (fix these):
These are cases where the router genuinely chose wrong given clear intent.
- Different verb families
- Wrong domain entirely

### Acceptable Soft Routes:
Label said `none_search_only` but router fired a reasonable READ-ONLY action.
- User gets useful result
- No state change
- Count as "correct" in Hard Action Accuracy

### Suggestion-Worthy:
- Same verb family, different target (e.g., `show_equipment_history` vs `show_equipment_overview`)
- State-changing action when label said none
- Surface as chips, let user decide

---

## 4. Verb Family Resolution (Next Architecture)

Current: Regex patterns with priority ordering
Problem: Doesn't scale, implicit logic, hard to debug

### Proposed Two-Pass Router:

**Pass A: Verb Family Detection**
```
Input: "add note to work order filter replacement"
Output: verb_family = "add"
```

Verb families:
- add, attach, upload (modification)
- show, view, display, list (read)
- create, generate, open (creation)
- update, edit, modify (mutation)
- diagnose, trace, expand (analysis)
- export, download, share (output)
- check, scan, search (query)

**Pass B: Slot Resolution**
```
Input: verb_family="add", query="add note to work order filter replacement"
Output:
  target_object = "note"
  target_container = "work_order"
  entity = "filter replacement"
  action = "add_note_to_work_order"
```

Slot types:
- target_object: note | part | photo | document | certificate
- target_container: work_order | handover | equipment | checklist
- destination: equipment | compliance | fleet

**Disambiguation:**
If multiple valid slot combinations → suggestion-worthy → show chips

---

## 5. Production Instrumentation

### Required logging fields (every query):

```json
{
  "timestamp": "2025-01-15T14:32:00Z",
  "session_id": "uuid",
  "yacht_id": "uuid",
  "user_role": "engineer",

  "query": {
    "raw_text": "add note filter replaced on generator",
    "normalized": "add note filter replaced on generator",
    "tokens": ["add", "note", "filter", "replaced", "on", "generator"]
  },

  "routing": {
    "verb_family": "add",
    "predicted_action": "add_note_to_work_order",
    "confidence": 0.87,
    "alternatives": [
      {"action": "add_note", "confidence": 0.72},
      {"action": "add_to_handover", "confidence": 0.45}
    ],
    "execution_class": "suggest"
  },

  "entities": [
    {"type": "equipment", "value": "generator", "confidence": 0.92, "span": [35, 44]},
    {"type": "part", "value": "filter", "confidence": 0.85, "span": [9, 15]}
  ],

  "outcome": {
    "chips_shown": ["add_note_to_work_order", "add_note", "add_to_handover"],
    "action_executed": "add_note_to_work_order",
    "execution_method": "chip_click",  // or "auto", "confirmation"
    "time_to_action_ms": 1200,
    "undo_triggered": false
  }
}
```

### Metrics to track:
- Chip click-through rate (primary chip chosen >70% = ranking is sane)
- Time to first action
- Undo rate by action type
- Confirmation acceptance rate for gated actions

---

## 6. Release Plan

### Phase 1: Shadow Mode (2 weeks)
- Compute actions + chips for every query
- Log predictions but don't execute
- Compare with actual user behavior
- Identify gaps between prediction and intent

### Phase 2: Canary (2 weeks)
- Enable auto-execute for Class A (read-only, high confidence)
- Show chips for Class B
- Keep Class C behind confirmation
- Monitor Hard FP rate (must stay 0)

### Phase 3: General Availability
- Full rollout with instrumentation
- A/B test chip ordering strategies
- Collect training data from chip selections

---

## 7. Success Criteria for Next Iteration

| Metric | Current | Target |
|--------|---------|--------|
| True Routing Bugs | 4 | 0 |
| Suggestion-Worthy | 22 | <10 |
| Hard FP (executed) | 0 | 0 (sacred) |
| Chip click-through (primary) | TBD | >70% |
| Entity hit rate | 85.85% | >90% |

---

## 8. Non-Negotiables

1. **Hard FP = 0 is measured at execution, not routing**
2. **All destructive actions are gated forever**
3. **Ambiguity becomes UX (chips), not silent failure**
4. **Every query is logged for continuous improvement**
5. **No pattern changes without test coverage**

---

*Last updated: 2025-01-15*
*Owner: Engineering*
