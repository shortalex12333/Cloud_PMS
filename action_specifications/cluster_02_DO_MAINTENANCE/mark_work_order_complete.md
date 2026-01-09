# Mark Work Order Complete

**CelesteOS**
**Action Type:** MUTATE
**Cluster:** 02_DO_MAINTENANCE
**Priority:** P0

---

## Purpose

This action exists to **close the accountability loop**.

When work is finished, someone must confirm it's done and record what happened. This creates the audit trail and updates system state.

It answers one question:

> "Is this work actually complete, and what was the outcome?"

---

## Core Doctrine

* **Completion = human verification** — System never auto-completes work
* **Outcome matters** — Not just "done" but "resolved" / "partial" / "unsuccessful"
* **Parts must be accounted** — Warn if parts unlogged, but don't block
* **Fault resolution is optional** — WO complete ≠ fault auto-resolved

---

## Mental Model (The Anchor)

> **Completing a work order is signing your name to say "I did this work."**

Not a status update. Not a checkbox.

A statement: "This is what I did, and here's the result."

---

## The Habit This Creates (Why It Helps)

### The real context:

Engineer finishes replacing thermostat on Generator 2. Work took 2 hours. Used 1 thermostat, 2 gaskets. Problem resolved.

**Without this action:**
- Work order sits "in progress" forever
- Next shift doesn't know it's done
- Parts usage not recorded
- No closure on the fault
- Accountability gap

**With this action:**
- Opens completion form
- Pre-filled: time spent (calculated), parts used, outcome inferred from checklist
- Adds final note: "Thermostat replaced, temperature normal"
- Option: Mark fault as resolved
- Sign → WO complete → Fault resolved → Parts logged → Audit complete

**The habit:**
"Finish work → Mark complete immediately → Full accountability"

**Not:**
"Finish work → Move on to next task → Forget to close WO → Data incomplete"

This action **makes completion comprehensive** while keeping it fast (pre-filled, one form, 30 seconds).

---

## Entry Conditions

### 1. Work Order Page (Primary)

User viewing WO in "In Progress" status.

```
[Actions ▼]
  → Add Note
  → Add Part
  → Mark Complete
```

**Only appears if:**
- WO status = In Progress
- User has permission (assigned or supervisor)

---

### 2. Direct Query (Gated)

User queries: "complete work order 089"

Action appears beneath search if intent parser confirms completion intent.

---

## The Exact UX Flow (Step by Step with Justification)

### Step 1: User Triggers Action

Clicks "Mark Complete" from WO page.

---

### Step 2: Unlogged Parts Check (Warning, Not Blocking)

If WO has parts added but not logged:

```
┌─ Unlogged Parts ─────────────────────────────┐
│                                               │
│ ⚠️  This work order has parts not yet logged: │
│                                               │
│ • Thermostat (MTU-THERM-01) x1                │
│ • Gasket Kit x1                               │
│                                               │
│ [Log Parts Now] (Recommended)                 │
│ [Continue Without Logging]                    │
│ [Cancel]                                      │
└───────────────────────────────────────────────┘
```

**Why warning, not blocking:**
- Parts might be logged later
- Urgency matters (ship operations don't stop)
- Human can override

If "Log Parts Now" → Opens parts logging flow, then returns to completion.

---

### Step 3: Completion Form Opens (Pre-filled)

```
┌─ Complete Work Order ────────────────────────┐
│                                               │
│ Work Order: WO-2024-089                       │
│ Generator 2 - Replace Thermostat              │
│                                               │
│ Outcome *                                     │
│ ┌───────────────────────────────────────────┐ │
│ │ Resolved                            [▼]   │ │ ← Inferred
│ └───────────────────────────────────────────┘ │    from checklist
│   Options: Resolved, Partial, Unsuccessful    │
│                                               │
│ Time Spent                                    │
│ ┌───────────────────────────────────────────┐ │
│ │ 2.5 hours                                 │ │ ← Calculated
│ └───────────────────────────────────────────┘ │    from notes
│   (Editable)                                  │
│                                               │
│ Final Notes                                   │
│ ┌───────────────────────────────────────────┐ │
│ │ Thermostat replaced. Temperature now      │ │ ← Latest note
│ │ normal. Monitoring for 24hrs.             │ │    (editable)
│ │                                           │ │
│ └───────────────────────────────────────────┘ │
│                                               │
│ ☐ Mark fault F-2024-089 as resolved          │ ← Optional
│                                               │
│ [Cancel]                      [Preview]       │
└───────────────────────────────────────────────┘
```

**Pre-fill logic (simple inference, no ML):**

```python
# Outcome from checklist completion
if all_checklist_items_complete:
    outcome = "resolved"
elif >50% complete:
    outcome = "partial"
else:
    outcome = "unsuccessful"

# Time spent from note timestamps
time_spent = calculate_time_between_first_and_last_note()

# Final note = latest note content
final_notes = latest_note.content if exists else ""

# Fault resolution checkbox only if WO linked to fault
show_fault_resolution = wo.fault_id exists
```

**Why pre-fill:**
- System knows checklist status, note history, time
- Engineer shouldn't calculate hours worked
- Latest note is likely the summary

**Why NOT auto-submit:**
- Outcome inference could be wrong (checklist incomplete but work done differently)
- Time calculation might miss offline work
- Human confirms reality

---

### Step 4: Preview

```
┌─ Review Completion ──────────────────────────┐
│                                               │
│ You are about to complete:                    │
│                                               │
│ WO-2024-089 - Generator 2 Thermostat          │
│                                               │
│ Outcome: Resolved                             │
│ Time: 2.5 hours                               │
│ Parts used: 2 items (logged)                  │
│                                               │
│ Final note:                                   │
│ "Thermostat replaced. Temperature normal.     │
│  Monitoring for 24hrs."                       │
│                                               │
│ ✓ Fault F-2024-089 will be marked resolved   │
│                                               │
│ [Back]                    [Sign & Complete]   │
└───────────────────────────────────────────────┘
```

**Why preview:**
- Completing WO affects fault status, inventory, finance
- User must see all effects
- No hidden mutations

---

### Step 5: Sign & Commit

```
┌─ Work Order Completed ───────────────────────┐
│                                               │
│ ✓ WO-2024-089 completed                       │
│ ✓ Fault F-2024-089 marked resolved            │
│ ✓ Time logged: 2.5 hours                      │
│                                               │
│ [View Work Order] [Close]                     │
└───────────────────────────────────────────────┘
```

**Backend effects:**
- WO status: In Progress → Completed
- WO completed_at = now, completed_by = current_user
- If fault resolution checked: fault.status = Resolved
- Audit log created
- Finance: labor hours posted
- Inventory: parts usage confirmed

---

## Edge Cases

### 1. Checklist Incomplete

User tries to complete WO with unchecked checklist items.

**Behavior:**
- Allows (doesn't block)
- Shows info: "3 checklist items not completed"
- Suggests outcome = "Partial"
- User can override

**Why allow:**
Checklist might be outdated, or work done differently than planned.

---

### 2. No Time Data

WO has no notes with timestamps (can't calculate time).

**Behavior:**
- Time field empty
- User must enter manually

---

### 3. Fault Resolution Declined

User unchecks "Mark fault as resolved".

**Behavior:**
- WO completes
- Fault stays active
- Valid scenario: fault requires monitoring, WO was just one intervention

---

## What This Action Does NOT Do

* ❌ No auto-completion based on checklist (human confirms)
* ❌ No forced fault resolution (WO complete ≠ fault resolved)
* ❌ No blocking if parts unlogged (warns only)
* ❌ No ML prediction of outcome (simple checklist logic only)
* ❌ No "suggested time" based on historical WOs (use calculated time from notes)
* ❌ No auto-emailing completion reports (audit trail is the record)
* ❌ No reopening completed WOs (immutable once signed)

**If a human didn't sign completion, the WO isn't complete.**

---

## Habit-Forming Principle

> **Completion is comprehensive but fast.**

The form captures everything (outcome, time, notes, fault resolution) in one place.

Pre-filled so engineer spends 30 seconds reviewing, not 5 minutes typing.

This creates habit:
- Finish work → Complete immediately → Full record
- Not: Finish work → Dread paperwork → Delay → Incomplete data

**The design makes thoroughness easy.**

---

## Testing the Mental Model

Ask: "Can a WO auto-complete when checklist is done?"
**No.** → Correct. Human signs completion.

Ask: "Does completing a WO auto-resolve the fault?"
**No.** → Correct. Optional checkbox, user decides.

Ask: "Can I complete a WO with unlogged parts?"
**Yes.** → Correct. Warning shown, not blocked.

Ask: "Can I reopen a completed WO if I made a mistake?"
**No.** → Correct. Completion is immutable (create new WO if more work needed).

If any answer changes, the design has drifted.

---
