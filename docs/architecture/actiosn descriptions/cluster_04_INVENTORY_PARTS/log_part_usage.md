# Log Part Usage

**CelesteOS**
**Action Type:** MUTATE
**Cluster:** 04_INVENTORY_PARTS
**Priority:** P0

---

## Purpose

This action exists to **create an immutable record of what parts were used and when**.

Inventory accuracy depends on logging usage at the moment it happens—not days later when memory fades.

It answers one question:

> "What parts were actually consumed for this work?"

---

## Core Doctrine

* **Usage = moment of truth** — Log when part is physically used, not when added to WO
* **Negative stock is visible, not blocked** — Warn if insufficient, but allow (reality matters more than system state)
* **Work order link is mandatory** — Every part used must be accountable to specific work
* **Logging is explicit, never automatic** — System never auto-deducts inventory

---

## Mental Model (The Anchor)

> **Logging parts is stating "I took this from stores and used it for this job."**

Not an estimate. Not a plan.

A fact: "This part is gone, here's why."

---

## The Habit This Creates (Why It Helps)

### The real context:

Engineer replacing thermostat on Generator 2. Takes 1 thermostat and 2 gaskets from workshop stores. Uses all of them.

**Without this action:**
- Engineer forgets to log usage
- Inventory shows 10 thermostats (actually 9)
- Next engineer orders parts based on wrong data
- Procurement wastes money on unnecessary stock
- OR runs out unexpectedly

**With this action:**
- Work complete → Opens "Log Parts"
- Form shows parts added to WO: Thermostat x1, Gaskets x2
- Stock check: Thermostat (9 available), Gaskets (45 available)
- Confirm quantities → Sign → Inventory updated
- Real-time accuracy maintained

**The habit:**
"Use part → Log immediately → Inventory accurate"

**Not:**
"Use part → Plan to log later → Forget → Inventory wrong"

This action **keeps inventory honest** by making logging fast and immediate.

---

## Entry Conditions

### 1. Work Order Page (Primary)

WO has parts added but not logged.

```
Parts on this Work Order:
• Thermostat x1 (not logged)
• Gasket Kit x2 (not logged)

[Log Part Usage]
```

---

### 2. WO Completion Flow (Contextual Prompt)

When completing WO with unlogged parts:

```
⚠️  3 parts not logged
[Log Parts Now] [Continue Without Logging]
```

---

### 3. Direct Query (Context-Free)

"log part usage for WO-089"

---

## The Exact UX Flow (Step by Step with Justification)

### Step 1: User Triggers Action

Clicks "Log Part Usage" from WO page.

---

### Step 2: Parts List with Stock Check

```
┌─ Log Part Usage - WO-2024-089 ───────────────┐
│                                               │
│ Select parts to log:                          │
│                                               │
│ ☑ Thermostat (MTU-THERM-01)                   │
│   Qty to log: [1]                             │
│   Stock available: 9 units ✓                  │
│   Location: Main Workshop                     │
│                                               │
│ ☑ Gasket Kit (MTU-GSKT-02)                    │
│   Qty to log: [2]                             │
│   Stock available: 45 units ✓                 │
│   Location: Main Workshop                     │
│                                               │
│ [Cancel]                        [Log Parts]   │
└───────────────────────────────────────────────┘
```

**Pre-fill logic:**
- List all parts added to WO that aren't logged yet
- All checked by default (likely all were used)
- Quantities from WO (editable if different)
- Real-time stock check for each part

**Stock validation (non-blocking):**
```python
stock = get_stock_level(part_id, location)
if stock < quantity:
    show_warning("Insufficient stock: {stock} available, logging {quantity}")
    # Still allow logging (creates negative stock alert)
```

**Why checkboxes:**
- Not all parts added to WO might be used (changed plan, didn't need it)
- User explicitly confirms each one

**Why stock check:**
- Visibility into inventory state
- Warns if data inconsistency (negative stock)
- Doesn't block (reality > system state)

---

### Step 3: Handle Insufficient Stock (If Detected)

If logging would create negative stock:

```
┌─ Stock Warning ──────────────────────────────┐
│                                               │
│ ⚠️  Logging will result in negative stock:    │
│                                               │
│ Thermostat (MTU-THERM-01)                     │
│ Current stock: 0 units                        │
│ Logging: 1 unit                               │
│ Result: -1 units                              │
│                                               │
│ This will create a stock discrepancy alert.   │
│                                               │
│ [Go Back] [Log Anyway]                        │
└───────────────────────────────────────────────┘
```

**Why allow negative stock:**
- Part was physically used (fact)
- Blocking doesn't change reality
- Alert flags for investigation (data entry error? theft? loss?)

---

### Step 4: Commit (Immediate, No Preview)

User clicks "Log Parts" → Commits immediately.

```
┌─ Parts Logged ───────────────────────────────┐
│                                               │
│ ✓ 2 parts logged for WO-2024-089              │
│                                               │
│ Inventory updated.                            │
│                                               │
│ [Close]                                       │
└───────────────────────────────────────────────┘
```

**Why no preview:**
- User just confirmed quantities (already saw what's happening)
- Small, focused mutation (just inventory deduction)
- Fast action (shouldn't add friction)

**Backend effects:**
- Stock transactions created (type: "used")
- Linked to work_order_id
- Inventory quantities decremented
- If negative stock: system alert created
- Audit log: who logged, when, quantities

---

## Edge Cases

### 1. Part Not in Stock System

Part added to WO but doesn't exist in inventory database.

**Behavior:**
- Shows part in list
- Stock shows: "Not tracked in inventory"
- Can still log (creates stock transaction for future reference)

**Why allow:**
- Part might be externally sourced, consumable, or legacy
- Work record matters even if inventory doesn't track it

---

### 2. User Unchecks All Parts

Wants to log zero parts (none were actually used).

**Behavior:**
- "Log Parts" button disabled
- Message: "Select at least one part to log"

**Why:**
If nothing used, just close the form. Logging zero is meaningless.

---

### 3. Quantity Edited to Zero

User changes quantity from 1 to 0.

**Behavior:**
- Equivalent to unchecking
- Part not logged

---

## What This Action Does NOT Do

* ❌ No auto-logging when parts added to WO (adding ≠ using)
* ❌ No auto-logging when WO completed (completion doesn't prove usage)
* ❌ No ML prediction of "likely quantities used" (use WO quantities)
* ❌ No blocking if stock insufficient (warns, creates alert, but allows)
* ❌ No "suggested alternative parts" if out of stock (noise)
* ❌ No batch logging across multiple WOs (one WO at a time for accountability)
* ❌ No auto-reordering when stock low (separate procurement flow)

**If a human didn't log it, inventory doesn't change.**

---

## Habit-Forming Principle

> **Log usage immediately, not eventually.**

The action appears **exactly when needed** (WO completion, after adding parts).

Not buried in an "Inventory" section.

Checkboxes make it **fast**: tick-tick-submit (5 seconds).

This creates habit:
- Use part → Log now → Inventory real-time
- Not: Use part → Log end of week → Inventory stale

**The design makes accuracy effortless.**

---

## Testing the Mental Model

Ask: "Does adding a part to a WO deduct from inventory?"
**No.** → Correct. Adding = plan. Logging = reality.

Ask: "Can I log parts if stock shows zero?"
**Yes.** → Correct. Warning shown, alert created, but allows.

Ask: "Can I log parts without a work order?"
**No.** → Correct. Every part must be accountable to specific work.

Ask: "Will the system auto-log parts when I complete a WO?"
**No.** → Correct. Human explicitly logs.

If any answer changes, the design has drifted.

---
