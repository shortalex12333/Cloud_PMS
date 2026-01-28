# CelesteOS P0 Action Specifications

**Last Updated:** 2026-01-08
**Status:** Complete (8/8 P0 actions specified)

---

## What This Is

This repository contains **design law specifications** for CelesteOS's 8 highest-priority user actions.

Each specification defines:
- **Purpose** - The problem this action solves
- **Core Doctrine** - Immutable principles that prevent drift
- **Mental Model** - The one-line anchor (e.g., "Checkbox = truth")
- **Habit Formation** - Why this design helps users, not hinders them
- **UX Flow** - Step-by-step with justification for each choice
- **Boundaries** - What this action explicitly does NOT do

---

## Philosophy

These specs follow CelesteOS brand principles:

1. **Simplicity Is a Safety Feature**
2. **Accountability Over Speed**
3. **Explicit Control Always**
4. **Human-in-the-Loop Is Non-Negotiable**
5. **No State Change Without Record**
6. **Boring Is Correct**

**Core principle:**
> "If a human didn't click it, it doesn't happen."

No behavioral tracking. No confidence scores. No ML predictions. No proactive nudges.

Just: query intent parsing, entity-based actions, simple data mapping, and explicit user control.

---

## The 8 P0 Actions

### Cluster 01: FIX_SOMETHING

| Action | Mental Model | File |
|--------|--------------|------|
| **show_manual_section** | "The manual is a reference, not a guide. Get me to the right page, then get out of the way." | `cluster_01_FIX_SOMETHING/show_manual_section.md` |

### Cluster 02: DO_MAINTENANCE

| Action | Mental Model | File |
|--------|--------------|------|
| **create_work_order_from_fault** | "A work order is a promise to fix something, not a record that something is broken." | `cluster_02_DO_MAINTENANCE/create_work_order_from_fault.md` |
| **add_note_to_work_order** | "A note is a breadcrumb for whoever picks up this work next (including future you)." | `cluster_02_DO_MAINTENANCE/add_note_to_work_order.md` |
| **add_part_to_work_order** | "Adding parts to a WO is writing a shopping list, not taking from stores." | `cluster_02_DO_MAINTENANCE/add_part_to_work_order.md` |
| **mark_work_order_complete** | "Completing a work order is signing your name to say 'I did this work.'" | `cluster_02_DO_MAINTENANCE/mark_work_order_complete.md` |

### Cluster 04: INVENTORY_PARTS

| Action | Mental Model | File |
|--------|--------------|------|
| **check_stock_level** | "Stock check is looking in the storeroom, not asking the computer to guess." | `cluster_04_INVENTORY_PARTS/check_stock_level.md` |
| **log_part_usage** | "Logging parts is stating 'I took this from stores and used it for this job.'" | `cluster_04_INVENTORY_PARTS/log_part_usage.md` |

### Cluster 05: HANDOVER_COMMUNICATION

| Action | Mental Model | File |
|--------|--------------|------|
| **add_to_handover** | "Handover is a note to your future self (or the person replacing you)." | `cluster_05_HANDOVER_COMMUNICATION/add_to_handover.md` |

---

## How to Read These Specs

Each spec is written for **implementation clarity**, not as marketing material.

### Structure:

1. **Purpose** - The one question this action answers
2. **Core Doctrine** - Non-negotiable design principles
3. **Mental Model** - The anchor that prevents drift
4. **The Habit This Creates** - Real context, with/without comparison, habit formation analysis
5. **Entry Conditions** - Where/when action appears
6. **The Exact UX Flow** - Step-by-step with justification
7. **Edge Cases** - Design decisions for non-happy-path scenarios
8. **What This Action Does NOT Do** - Explicit boundaries (prevents feature creep)
9. **Habit-Forming Principle** - Why the design makes good behavior easiest
10. **Testing the Mental Model** - Validation questions

### Read in this order:

1. **Start here:** `cluster_02_DO_MAINTENANCE/create_work_order_from_fault.md`
   This is the reference implementation. Most complete example.

2. **Then:** Any other action you're implementing.

3. **Reference:** `reference/# Receiving — Situational Active State.md`
   Example of a **situation** (vs action). Shows checkbox-based reconciliation pattern.

---

## Architecture Principles

### Query Intent Parsing (Not Behavioral Tracking)

**Direct action query:** "create work order for generator 2"
- Intent parser classifies as WO creation intent
- Action appears beneath search bar
- Opens with pre-filled entity data

**Information query:** "generator 2 status"
- Shows information results
- User clicks entity
- Actions available in entity dropdown

**No:**
- Time-on-page tracking
- Scroll depth monitoring
- Copied text detection
- Confidence scoring (0-100)
- ML predictions

### Entity-Based Actions (Not Situational Tracking)

Actions appear **adjacent to entities**:
- Fault page → "Create Work Order"
- Work order page → "Add Part"
- Part search → Stock level shown inline

**No:**
- Proactive widgets
- Dashboard nudges
- "You should do X now" suggestions
- Auto-triggering based on user behavior

### Simple Data Mapping (Not ML)

Pre-fill uses **deterministic logic**:

```python
title = f"{location} - {equipment_name} - {fault_code}"
category = "ongoing_fault" if entity_type == "fault" else "important_info"
priority = fault.severity if exists else "normal"
```

**No:**
- Historical pattern matching ("users like you usually...")
- ML-based suggestions
- Confidence intervals
- Behavioral predictions

### Explicit User Control (Not Automation)

Every mutation requires:
1. User triggers action (click)
2. Form opens (pre-filled but editable)
3. Preview shows effects (no hidden mutations)
4. User signs/commits
5. Confirmation shown

**No:**
- Auto-execution
- Silent background mutations
- Assumed intent
- Learned helplessness

---

## What Was Deleted (And Why)

The previous version built a **behavioral surveillance system**:
- ❌ Confidence scores (0-100) based on time spent, scroll depth, copied text
- ❌ Situational activeness tracking (IDLE → CANDIDATE → ACTIVE state machine)
- ❌ Proactive nudges and suggestions
- ❌ Historical pattern matching for recommendations
- ❌ ML predictions of user intent
- ❌ One-nudge-at-a-time guardrails
- ❌ Acceptance/dismissal rate optimization

This violated CelesteOS principles:
- "Explicit Control Always"
- "Human-in-the-Loop Is Non-Negotiable"
- "Accountability Over Speed"

**The current system:**
- ✅ Query intent parsing (explicit queries only)
- ✅ Entity data mapping (simple, deterministic)
- ✅ Preview before commit (no hidden effects)
- ✅ Human confirms every mutation

---

## Reference Material

### `/reference/`

**# Receiving — Situational Active State.md**
- Example of a **situation** (not an action)
- Shows checkbox-based reconciliation pattern
- Demonstrates "Checkbox = truth" doctrine
- Event-driven, bulk affordances (vs persistent observation)

**receival inventory thought process.md**
- Design thinking behind receiving situation
- Hard UX constraints
- Camera-in-search behavior
- What we explicitly do NOT do

---

## Implementation Checklist

When building an action:

### Backend:
- [ ] Create API endpoint for action
- [ ] Implement pre-fill logic (simple data mapping, no ML)
- [ ] Add validation rules (warn, don't block)
- [ ] Create audit log entries
- [ ] Handle edge cases (no data, duplicates, etc.)

### Frontend:
- [ ] Add action button to entity page
- [ ] Create action form/modal
- [ ] Implement pre-fill population (editable fields)
- [ ] Add preview screen (show all effects)
- [ ] Handle cancellation (no trace left behind)
- [ ] Show confirmation

### Testing:
- [ ] Happy path (pre-filled form, user confirms)
- [ ] Edit path (user changes pre-filled data)
- [ ] Empty data (no entity data available)
- [ ] Cancellation (at each stage)
- [ ] Edge cases (duplicates, validation, etc.)

### Validation:
- [ ] Ask mental model questions (from spec)
- [ ] Verify no behavioral tracking added
- [ ] Check no hidden mutations
- [ ] Confirm user can cancel at any point
- [ ] Ensure audit trail complete

---

## Testing the Design

Each spec includes "Testing the Mental Model" questions.

If the answer to any question changes, **the design has drifted**.

**Example (from create_work_order_from_fault):**

- Q: "Can a fault exist without a work order?"
  A: **Yes.** ← Correct. Faults are observations. WOs are commitments.

- Q: "Does creating a WO mark the fault as resolved?"
  A: **No.** ← Correct. Resolution happens when verified fixed.

- Q: "Can I create a WO and cancel before committing?"
  A: **Yes.** ← Correct. Cancel means no trace.

---

## Next Steps

1. **Implement:** Use these specs to build the 8 P0 actions
2. **Test:** Validate against mental model questions
3. **Deploy:** Ship to production
4. **Measure:** User adoption, not engagement metrics
5. **Iterate:** Based on real usage patterns (not predicted behavior)

---

## Questions?

The specs are the authority. If ambiguous, refer to:
1. The spec's "Core Doctrine" section
2. CelesteOS brand principles (`/Users/celeste7/Documents/BRANDING_V3/`)
3. The mental model statement

If still unclear, **ask the user**, don't infer.

---

**END OF README**
