# Check Stock Level

**CelesteOS**
**Action Type:** READ
**Cluster:** 04_INVENTORY_PARTS
**Priority:** P0

---

## Purpose

This action exists to **show real-time inventory levels exactly when needed**.

Before ordering parts, before starting work, before assuming "we have it"—check stock.

It answers one question:

> "Do we have this part, and where is it?"

---

## Core Doctrine

* **Stock is fact, not prediction** — Simple calculation: received - used = current
* **Negative stock is visible** — Show it, flag it, investigate it (don't hide data problems)
* **Location matters** — Multi-location inventory shows by-location breakdown
* **Viewing ≠ reserving** — Checking stock doesn't lock it (no reservations)

---

## Mental Model (The Anchor)

> **Stock check is looking in the storeroom, not asking the computer to guess.**

Real-time count based on actual transactions.

No forecasting, no predictions, no "likely availability."

Just: "Here's what the ledger shows."

---

## The Habit This Creates (Why It Helps)

### The real context:

Engineer planning Generator 2 thermostat replacement. Needs to know if parts are on hand before starting.

**Without this action:**
- Assumes parts are in stock
- Starts work
- Goes to storeroom
- Part missing
- Work stops
- Orders part
- 3-day delay

**With this action:**
- Planning WO → Searches "MTU thermostat"
- Stock shows: 0 units (out of stock)
- Orders part BEFORE starting work
- Part arrives
- Starts work with everything ready
- Zero delays

**The habit:**
"Plan work → Check stock → Order if needed → Start prepared"

**Not:**
"Start work → Discover missing parts → Stop → Order → Wait"

This action **prevents workflow disruption** by surfacing inventory reality early.

---

## Entry Conditions

### 1. Part Search Results (Automatic)

User searches for part → Stock shown inline.

```
Search Results:

┌─────────────────────────────────────────────┐
│ Thermostat (MTU 16V4000)                    │
│ Part #: MTU-THERM-01                        │
│ Stock: 9 units ✓ In Stock                   │
│                                              │
│ [View Details]                              │
└─────────────────────────────────────────────┘
```

---

### 2. Part Entity Page (Always Visible)

Part detail page shows stock breakdown.

```
Part: Thermostat (MTU 16V4000)

Stock Levels:
┌─────────────────────────────────────────────┐
│ Location        │ Qty │ Status             │
├─────────────────┼─────┼────────────────────┤
│ Main Workshop   │  9  │ ✓ In Stock        │
│ Generator Room  │  3  │ ✓ In Stock        │
│ Warehouse       │ 45  │ ✓ In Stock        │
├─────────────────┼─────┼────────────────────┤
│ Total           │ 57  │                    │
└─────────────────────────────────────────────┘
```

---

### 3. Adding Part to WO (Contextual)

Stock shown during part selection.

```
┌─ Add Part to WO-089 ─────────────────────────┐
│                                               │
│ Select Part:                                  │
│ ○ Thermostat (MTU 16V4000)                    │
│   Stock: 9 units ✓ Available                  │
│                                               │
│ ○ Thermostat (CAT 3516)                       │
│   Stock: 0 units ⚠️ Out of Stock               │
└───────────────────────────────────────────────┘
```

---

### 4. Direct Query

"check stock for MTU thermostat"

Shows stock summary card.

---

## The Exact UX Flow (Step by Step with Justification)

### Step 1: User Queries Stock

Types: "check stock for MTU thermostat"

---

### Step 2: Stock Summary Appears

```
┌─ Stock Level ────────────────────────────────┐
│                                               │
│ Thermostat (MTU 16V4000)                      │
│ Part #: MTU-THERM-01                          │
│                                               │
│ Total: 57 units ✓ In Stock                    │
│                                               │
│ By Location:                                  │
│ • Main Workshop: 9 units                      │
│ • Generator Room: 3 units                     │
│ • Warehouse: 45 units                         │
│                                               │
│ Last updated: 2 hours ago                     │
│                                               │
│ [View Part Details] [Close]                   │
└───────────────────────────────────────────────┘
```

**Calculation (simple arithmetic):**

```python
# For each location:
stock = sum(received) - sum(used) + sum(adjustments)

# Status determination:
if stock == 0:
    status = "out_of_stock"
elif stock <= critical_threshold:
    status = "critical"
elif stock <= low_threshold:
    status = "low"
else:
    status = "in_stock"
```

**No ML, no predictions.** Just transaction ledger math.

---

### Step 3: User Can Navigate

From stock summary:
- View Part Details → Full part page
- Close → Back to search

**No mutation** (READ action).

---

## Edge Cases

### 1. Part Not Found

Search for part that doesn't exist.

```
┌─ Part Not Found ─────────────────────────────┐
│                                               │
│ No part found matching: "flux capacitor"     │
│                                               │
│ [Search All Parts] [Request New Part]         │
└───────────────────────────────────────────────┘
```

---

### 2. Negative Stock (Data Error)

Stock calculation results in -3 units.

```
┌─ Stock Level ────────────────────────────────┐
│                                               │
│ Thermostat (MTU 16V4000)                      │
│                                               │
│ Total: -3 units 🔴 Data Error                 │
│                                               │
│ ⚠️  Negative stock indicates logging error    │
│                                               │
│ Locations:                                    │
│ • Main Workshop: 5 units                      │
│ • Generator Room: -8 units 🔴 Error           │
│                                               │
│ [View Transactions] [Report Issue]            │
└───────────────────────────────────────────────┘
```

**Why show:**
- Data problems must be visible
- Negative stock = reality (used more than logged as received)
- Hiding it makes problem worse

**System creates alert** for inventory audit.

---

### 3. Stock Recently Changed

Another user just logged usage 30 seconds ago.

**Behavior:**
- Shows latest data (real-time)
- Timestamp shows recency

**Why real-time:**
- Prevents race conditions (two people checking stock, one uses last unit)
- Accurate decision-making

---

## What This Action Does NOT Do

* ❌ No stock forecasting or "predicted run-out date" (noise)
* ❌ No ML recommendations for "optimal stock levels" (use manual thresholds)
* ❌ No auto-reordering when low (procurement is separate flow)
* ❌ No "suggested alternative parts" if out of stock (noise)
* ❌ No reserving stock when viewed (checking ≠ locking)
* ❌ No tracking who checks stock or how often (surveillance)
* ❌ No "similar parts" suggestions (noise)

**Stock level is just a number from the transaction ledger.**

---

## Habit-Forming Principle

> **Check before you assume.**

Stock visibility is **everywhere** (search results, part pages, WO flows).

Not buried in "Inventory" section.

This creates habit:
- Need part → Check stock → Order if needed → Proceed
- Not: Need part → Assume we have it → Discover we don't → Delays

**The design makes checking stock faster than guessing.**

---

## Testing the Mental Model

Ask: "Does checking stock reserve it for me?"
**No.** → Correct. Viewing doesn't lock inventory.

Ask: "Will the system predict when we'll run out?"
**No.** → Correct. Shows current level only, no forecasting.

Ask: "Can I see stock if it's negative?"
**Yes.** → Correct. Shows error, flags for investigation.

Ask: "Does the system suggest alternatives if out of stock?"
**No.** → Correct. Shows reality, user decides next action.

If any answer changes, the design has drifted.

---
