# Create Work Order from Fault

**CelesteOS**
**Action Type:** MUTATE
**Cluster:** 02_DO_MAINTENANCE
**Priority:** P0

---

## Purpose

This action exists to **convert observation into accountability**.

When a fault appears repeatedly or requires planned intervention, someone must take ownership. This action creates that accountability record.

It answers one question:

> "Who is going to fix this, and when?"

---

## Core Doctrine

* **Observation ≠ Action** — Seeing a fault is not the same as fixing it
* **Work orders are commitments, not suggestions** — Creating one means someone will do the work
* **Pre-fill helps, but humans verify** — System suggests, human confirms reality
* **No forced WO creation** — Faults can exist without work orders (some are informational only)

---

## Mental Model (The Anchor)

> **A work order is a promise to fix something, not a record that something is broken.**

Faults record problems.
Work orders record intent to solve them.

This distinction prevents WO spam and keeps accountability meaningful.

---

## The Habit This Creates (Why It Helps)

### The real context:

Engineer is in the engine room. Sees fault F-2024-089: "MTU OVHT-01 - Coolant temp high".

They know this fault. It's happened before. It needs fixing.

**Without this action:**
- They'd have to remember to create a WO later
- Or tell someone else to create it
- Or write it on paper
- Fault gets ignored or forgotten

**With this action:**
- Query "MTU overheating" → Fault appears
- Click fault to read details
- See "Create Work Order" in actions
- Click → Form pre-filled with fault context (equipment, location, description)
- Edit if needed (maybe add "replace thermostat")
- Sign → Work order exists
- Someone is now accountable

**The habit:**
"See recurring problem → Create WO immediately → Problem gets scheduled"

**Not:**
"See problem → Hope someone else deals with it → Problem persists"

This action **lowers the friction** of converting awareness into action, while keeping human judgment in the loop (not every fault needs a WO).

---

## Entry Conditions (When This Action Appears)

### 1. Fault Entity Page (Primary)

User is viewing a fault detail page.

Action appears in dropdown:
```
[Actions ▼]
  → Create Work Order
  → Add to Handover
  → View Manual Section
```

**Why here:**
User is already looking at the problem. Creating a WO is the natural next step.

---

### 2. Direct Query (Gated by Intent)

User queries: "create work order for generator 2"

Action appears beneath search bar **only if:**
- Intent parser classifies query as WO creation intent, OR
- User explicitly typed "create" / "new" / "make" + "work order"

**Does NOT appear for:**
- Informational queries like "generator 2 status"
- Fault codes without creation keywords

**Why gated:**
Prevents accidental clicks. Direct action buttons need confidence the user wants mutation.

---

### 3. Equipment Entity Page (Contextual)

User viewing equipment can create WO without a fault (planned maintenance).

Action available in dropdown.

---

## The Exact UX Flow (Step by Step with Justification)

### Step 1: User Triggers Action

From fault page, clicks "Create Work Order".

---

### Step 2: Duplicate Check (Before Form Opens)

System checks if WO already exists for this fault.

**If duplicate found:**

```
┌─ Work Order Already Exists ──────────────────┐
│                                               │
│ A work order for this fault already exists:  │
│                                               │
│ WO-2024-067 (Created 2 days ago)              │
│ Status: In Progress                           │
│ Assigned: Sarah Chen                          │
│                                               │
│ [View Existing WO]  (Primary - safe default) │
│ [Create New Anyway] (Secondary - explicit)    │
│ [Cancel]                                      │
└───────────────────────────────────────────────┘
```

**Why this matters:**
- Prevents duplicate WOs for same fault (waste)
- Emphasizes safe default (View Existing)
- Still allows override (engineer knows better than system)
- No blocking, just informed choice

---

### Step 3: Form Opens with Pre-fill

If no duplicate (or user chose "Create New Anyway"):

```
┌─ Create Work Order ──────────────────────────┐
│                                               │
│ Title *                                       │
│ ┌───────────────────────────────────────────┐ │
│ │ Generator 2 - MTU-OVHT-01                 │ │ ← Pre-filled
│ └───────────────────────────────────────────┘ │
│                                               │
│ Equipment *                                   │
│ ┌───────────────────────────────────────────┐ │
│ │ Generator 2 (MTU 16V4000)                 │ │ ← Pre-filled
│ └───────────────────────────────────────────┘ │
│                                               │
│ Location                                      │
│ ┌───────────────────────────────────────────┐ │
│ │ Engine Room Deck 3                        │ │ ← Pre-filled
│ └───────────────────────────────────────────┘ │
│                                               │
│ Description                                   │
│ ┌───────────────────────────────────────────┐ │
│ │ Coolant temperature exceeding normal      │ │ ← Pre-filled
│ │ operating range. Occurred 8 times in      │ │    from fault
│ │ last 30 days.                             │ │
│ └───────────────────────────────────────────┘ │
│                                               │
│ Priority                                      │
│ ┌───────────────────────────────────────────┐ │
│ │ Normal                              [▼]   │ │ ← Inferred from
│ └───────────────────────────────────────────┘ │    fault severity
│                                               │
│ [Cancel]                      [Next]          │
└───────────────────────────────────────────────┘
```

**Pre-fill logic (simple, no ML):**

```
title = f"{location} - {equipment_name} - {fault_code}"
equipment = fault.equipment
location = fault.location
description = fault.description + f"\n\nOccurrences: {fault.count} in last 30 days"
priority = fault.severity if exists else "normal"
```

**Why pre-fill:**
- Engineer shouldn't retype information that already exists
- Reduces friction from ~2 minutes to ~20 seconds
- **BUT** all fields are editable (we might have wrong data)

**Why NOT auto-submit:**
- Engineer might want to add context ("also check water pump")
- Priority inference could be wrong
- Human confirms reality

---

### Step 4: Preview Screen

User clicks "Next" → Shows what will be created:

```
┌─ Review Work Order ──────────────────────────┐
│                                               │
│ You are about to create:                     │
│                                               │
│ ┌───────────────────────────────────────────┐ │
│ │ Work Order                                │ │
│ │                                           │ │
│ │ Title:    Generator 2 - MTU-OVHT-01       │ │
│ │ Equipment: Generator 2 (MTU 16V4000)      │ │
│ │ Location:  Engine Room Deck 3             │ │
│ │ Priority:  Normal                         │ │
│ │ Status:    Candidate                      │ │
│ │                                           │ │
│ │ Linked to: Fault F-2024-089               │ │
│ └───────────────────────────────────────────┘ │
│                                               │
│ ────────────────────────────────────────────  │
│ ℹ️  Parts used can be logged when completing  │
│    this work order.                           │
│ ────────────────────────────────────────────  │
│                                               │
│ [Back]                           [Sign & Create]│
└───────────────────────────────────────────────┘
```

**Why preview:**
- No hidden side effects (CelesteOS principle)
- User sees exactly what they're creating
- Status shown as "Candidate" (not "Active" yet)

**Why the parts note:**
- Passive affordance (not a forced flow)
- Reminds without nagging
- User already knows next steps

---

### Step 5: Sign & Commit

User clicks "Sign & Create".

System requires signature (timestamp + user ID = accountability).

```
┌─ Work Order Created ─────────────────────────┐
│                                               │
│ ✓ WO-2024-089 created                         │
│                                               │
│ [View Work Order] [Close]                     │
└───────────────────────────────────────────────┘
```

**What happens in backend:**
- `work_order` record created with status = CANDIDATE
- Linked to `fault_id`
- Created by `current_user.id` with timestamp
- Fault status unchanged (faults don't auto-resolve)
- Audit log entry created

**Why status = CANDIDATE:**
- WO exists but work hasn't started
- Transitions to ACTIVE when user adds note, logs parts, or marks in progress
- Creating record ≠ Starting execution

---

## Edge Cases (Design Decisions)

### 1. No Equipment Specified

Fault exists but equipment not linked (data entry error).

**Behavior:**
- Form opens but Equipment field empty
- User must select equipment (required field)
- Search dropdown available
- Cannot proceed without equipment

**Why not block:**
- Still allow WO creation (work is real even if data is messy)
- Forces user to fix data gap

---

### 2. Multiple Active WOs for Same Equipment

User creates WO for Generator 2. Three other WOs already exist for Generator 2.

**Behavior:**
- No warning (different faults can coexist)
- Only warns if duplicate for SAME fault

**Why:**
- Equipment can have multiple issues
- Trust user judgment

---

### 3. Fault Already Resolved

User tries to create WO for fault marked "Resolved".

**Behavior:**
```
┌─ Fault Already Resolved ─────────────────────┐
│                                               │
│ ℹ️  This fault is marked as resolved          │
│                                               │
│ Create work order anyway?                     │
│                                               │
│ [Cancel] [Create Anyway]                      │
└───────────────────────────────────────────────┘
```

**Why allow:**
- Resolution might be temporary
- Preventive maintenance still valid
- User knows context better than system

---

### 4. User Cancels

At any point, user clicks Cancel.

**Behavior:**
- Form closes
- No WO created
- No database changes
- Returns to previous page

**Why important:**
- No trace left behind (CelesteOS principle: cancel must be true cancel)

---

## What This Action Does NOT Do (Write This Down)

To keep this action trusted and simple:

* ❌ No auto-creation of WOs from faults (user decides if fault needs fixing)
* ❌ No confidence scores about "should you create this WO?" (trust user judgment)
* ❌ No ML prediction of priority or parts needed (use simple inference only)
* ❌ No forced assignment (WO can exist unassigned until someone claims it)
* ❌ No auto-resolution of faults when WO created (fault stays active until verified fixed)
* ❌ No "suggested due dates" based on historical completion times (over-engineering)
* ❌ No auto-linking to "similar WOs" (noise)
* ❌ No proactive nudges like "You should create a WO for this fault" (explicit control always)

**If a human didn't click Create, the WO doesn't exist.**

---

## Situation State Transitions

### Fault Situation
**No change.**

Creating a WO does not resolve or modify the fault. Faults are independent observations.

---

### Work Order Situation

**New WO created with state: CANDIDATE**

```
work_order.situation_state = "CANDIDATE"
work_order.created_at = now
work_order.created_by = current_user.id
```

**Transitions to ACTIVE when:**
- User adds first note
- User adds part
- User marks "in progress"

**Why CANDIDATE:**
- Work order exists (commitment made)
- Work hasn't started yet
- Gives visibility without false "active work" status

---

## Backend Events (Audit Trail)

On commit:

```python
# 1. Create work order
wo = WorkOrder(
    number=generate_wo_number(),
    title=data["title"],
    equipment_id=data["equipment_id"],
    location=data["location"],
    description=data["description"],
    priority=data["priority"],
    fault_id=fault_id,
    situation_state="CANDIDATE",
    created_by=current_user.id,
    created_at=datetime.utcnow()
)

# 2. Audit log
create_audit_log(
    entity_type="work_order",
    entity_id=wo.id,
    action="created_from_fault",
    user_id=current_user.id,
    details={
        "fault_id": fault_id,
        "fault_code": fault.code
    }
)

# 3. No fault modification
# (fault remains active)
```

---

## The Real Behavior This Enables

### Scenario: Recurring Fault

MTU overheating has happened 8 times in 30 days.

Engineer sees it again. Opens fault. Reads history.

**Decision point:**
- "This needs fixing" → Creates WO → Someone will investigate
- "This is informational" → Doesn't create WO → Monitoring continues

**The system doesn't decide.** The engineer does.

---

### Scenario: Preventive Maintenance

Chief Engineer planning work: "Generator 2 needs service next port."

**Flow:**
- Searches "Generator 2"
- Views equipment page
- Creates WO (no fault, just planned work)
- Adds parts to WO
- Assigns to crew

**Same action, different context.**

---

## Habit-Forming Principle

> **Lower friction to accountability, not to automation.**

The action is fast (pre-filled, 20 seconds).
But it's never automatic (human decides).

This creates a habit:
- See problem → Check if real → Create WO if worth fixing
- Not: See problem → System creates WO → Inbox spam → Ignore

**The design reinforces good judgment**, not learned helplessness.

---

## Testing the Mental Model

Ask: "Can a fault exist without a work order?"
**Yes.** → Correct. Faults are observations. WOs are commitments.

Ask: "Can a work order exist without a fault?"
**Yes.** → Correct. Planned maintenance has no fault.

Ask: "Does creating a WO mark the fault as resolved?"
**No.** → Correct. Resolution happens when verified fixed, not when scheduled.

Ask: "Can I create a WO and cancel before committing?"
**Yes.** → Correct. Cancel means no trace.

If any answer changes, the design has drifted.

---
