# Add Part to Work Order

**CelesteOS**
**Action Type:** MUTATE
**Cluster:** 02_DO_MAINTENANCE
**Priority:** P0

---

## Purpose

This action exists to **plan what parts will be needed before work starts**.

Adding parts to a WO creates the shopping list, enables stock checks, and prepares for procurement—all before touching inventory.

It answers one question:

> "What parts will I need for this job?"

---

## Core Doctrine

* **Adding ≠ Using** — Parts on WO are a plan, not a deduction from inventory
* **Stock visibility, not blocking** — Show availability, warn if out, but never prevent adding
* **Search, don't suggest** — User searches explicitly for parts (no ML recommendations)
* **Duplicates are intentional** — If same part added twice, ask: increase quantity or separate line?

---

## Mental Model (The Anchor)

> **Adding parts to a WO is writing a shopping list, not taking from stores.**

Inventory only changes when parts are logged as used.

This list helps procurement, visibility, and planning.

---

## The Habit This Creates (Why It Helps)

### The real context:

Engineer creating WO for Generator 2 thermostat replacement. Knows they'll need: 1 thermostat, 2 gaskets, possibly a sensor.

**Without this action:**
- Engineer starts work
- Realizes they need gaskets
- Workshop doesn't have them
- Work stops
- Parts ordered (delays)
- Inefficiency

**With this action:**
- Creating WO → Add parts: Thermostat, Gaskets, Sensor
- Stock check shows: Thermostat (9), Gaskets (45), Sensor (0 - out of stock)
- Engineer sees sensor missing BEFORE starting work
- Orders sensor now
- When work starts, all parts ready
- Efficient execution

**The habit:**
"Plan work → Add parts to WO → Check stock → Procure before starting → Smooth execution"

**Not:**
"Start work → Discover missing parts → Stop → Wait → Restart"

This action **prevents disruption** by surfacing part availability early.

---

## Entry Conditions

### 1. Work Order Page (Primary)

Always available in Parts section.

```
Parts on this Work Order:
• Thermostat x1

[Add Part]
```

---

### 2. WO Creation Flow (Optional Step)

When creating new WO, can add parts immediately.

---

### 3. Direct Query

"add thermostat to WO-089"

---

## The Exact UX Flow (Step by Step with Justification)

### Step 1: User Triggers Action

Clicks "Add Part" from WO page.

---

### Step 2: Part Search Interface

```
┌─ Add Part to WO-2024-089 ────────────────────┐
│                                               │
│ Search Parts:                                 │
│ ┌───────────────────────────────────────────┐ │
│ │ thermostat                                │ │
│ └───────────────────────────────────────────┘ │
│                                               │
│ Results:                                      │
│ ○ Thermostat (MTU 16V4000)                    │
│   Part #: MTU-THERM-4000-01                   │
│   Stock: 9 units ✓ In Stock                   │
│                                               │
│ ○ Thermostat (CAT 3516)                       │
│   Part #: CAT-THERM-3516-01                   │
│   Stock: 0 units ⚠️ Out of Stock               │
│                                               │
│ [Cancel]                                      │
└───────────────────────────────────────────────┘
```

**Why search, not suggest:**
- Engineer knows what part they need
- No ML "suggestions" based on "similar WOs" (noise)
- Direct, explicit search

**Stock visibility:**
- Real-time stock shown inline
- Helps engineer choose (use available part vs wait for preferred one)
- Out-of-stock parts still selectable

---

### Step 3: User Selects Part

Clicks on part → Quantity form appears.

```
┌─ Add Part to WO-2024-089 ────────────────────┐
│                                               │
│ Part: Thermostat (MTU 16V4000)                │
│ Part #: MTU-THERM-4000-01                     │
│                                               │
│ Quantity:                                     │
│ ┌───────────────────────────────────────────┐ │
│ │  [-]  1  [+]                              │ │
│ └───────────────────────────────────────────┘ │
│                                               │
│ Stock: 9 units available                      │
│                                               │
│ [Cancel]                       [Add to WO]    │
└───────────────────────────────────────────────┘
```

**Default quantity = 1** (most common).

User can adjust with +/- or type.

---

### Step 4: Duplicate Detection (If Same Part Already on WO)

If Thermostat already on WO:

```
┌─ Part Already on Work Order ─────────────────┐
│                                               │
│ Thermostat (MTU 16V4000) is already on this  │
│ work order (Qty: 1).                          │
│                                               │
│ [Increase Quantity to 2] (Primary)            │
│ [Add as Separate Line]   (Secondary)          │
│ [Cancel]                                      │
└───────────────────────────────────────────────┘
```

**Why ask:**
- Usually want to increase quantity (cleaner)
- Sometimes want separate lines (different usage contexts)
- User decides

---

### Step 5: Out-of-Stock Handling

If selected part has 0 stock:

```
┌─ Part Out of Stock ──────────────────────────┐
│                                               │
│ Thermostat (MTU 16V4000)                      │
│ Stock: 0 units                                │
│                                               │
│ You can still add this part to the WO.        │
│ It will be flagged for procurement.           │
│                                               │
│ [Add to WO Anyway] (Primary)                  │
│ [Cancel and Check Procurement]                │
└───────────────────────────────────────────────┘
```

**Why allow:**
- WO might not start for days (procurement time)
- Adding to WO creates procurement visibility
- Blocking doesn't help anyone

---

### Step 6: Commit (Immediate)

Part added to WO instantly (no preview for adding parts).

```
┌─ Part Added ─────────────────────────────────┐
│                                               │
│ ✓ Thermostat added to WO-2024-089             │
│                                               │
│ [Add Another Part] [Close]                    │
└───────────────────────────────────────────────┘
```

**Backend effects:**
- Part linked to WO (status: "planned")
- If out of stock: procurement alert created
- Inventory NOT changed (adding ≠ using)
- Audit log: part added to WO

---

## What This Action Does NOT Do

* ❌ No "suggested parts" based on historical WOs (noise)
* ❌ No ML recommendations like "users also added..." (noise)
* ❌ No auto-adding parts based on fault code or equipment type (over-automation)
* ❌ No blocking if out of stock (warns, flags procurement, allows)
* ❌ No inventory deduction when added (only when logged as used)
* ❌ No forced procurement orders (procurement is separate flow)
* ❌ No "commonly paired parts" suggestions (noise)

**If a human didn't search and add it, it's not on the WO.**

---

## Habit-Forming Principle

> **Plan before you act.**

Adding parts to WO **before work starts** creates visibility:
- What's needed
- What's available
- What needs ordering

This prevents mid-work disruptions.

The search interface is fast (type → results → add → done in 10 seconds).

This creates habit:
- Create WO → Add parts → Check stock → Procure if needed → Start work prepared
- Not: Start work → Discover missing parts → Stop work → Scramble

**The design makes preparation the path of least resistance.**

---

## Testing the Mental Model

Ask: "Does adding a part to a WO deduct from inventory?"
**No.** → Correct. Only logging usage affects inventory.

Ask: "Can I add a part that's out of stock?"
**Yes.** → Correct. Flags for procurement, doesn't block.

Ask: "Will the system suggest parts I might need?"
**No.** → Correct. User searches explicitly.

Ask: "If I add the same part twice, does it create duplicates?"
**Asks first.** → Correct. User chooses: increase quantity or separate lines.

If any answer changes, the design has drifted.

---
