# Show Manual Section

**CelesteOS**
**Action Type:** READ
**Cluster:** 01_FIX_SOMETHING
**Priority:** P0

---

## Purpose

This action exists to **put the right documentation in front of the engineer at the moment they need it**.

When troubleshooting, the manual should open to the relevant section—not page 1.

It answers one question:

> "Where in the manual does it explain this problem?"

---

## Core Doctrine

* **Context determines section** — Fault code → Manual section (simple mapping, no ML)
* **Opening to page 1 is failure** — Default section is better than no targeting
* **Manual not available ≠ block** — Show message, allow request, don't prevent work
* **External manuals are fine** — PDF upload ideal, but external link acceptable

---

## Mental Model (The Anchor)

> **The manual is a reference, not a guide. Get me to the right page, then get out of the way.**

Not a tutorial. Not interactive help.

A shortcut to the information the engineer already knows exists somewhere.

---

## The Habit This Creates (Why It Helps)

### The real context:

Engineer sees fault MTU-OVHT-01 on Generator 2. Knows the manual has troubleshooting steps for overheating.

**Without this action:**
- Opens shared drive
- Finds MTU folder
- Downloads 300-page PDF
- Searches for "overheating"
- Finds section 7.3 (page 142)
- Reads procedure
- 5 minutes wasted on navigation

**With this action:**
- Views fault page
- Clicks "View Manual Section"
- Manual opens directly to Section 7.3 (page 142)
- Reads procedure
- 10 seconds

**The habit:**
"See fault → Click manual → Read solution → Fix problem"

**Not:**
"See fault → Remember where manual is → Navigate file system → Search PDF → Find section → Fix problem"

This action **removes friction** from accessing documentation.

---

## Entry Conditions

### 1. Fault Entity Page

Fault with linked equipment (manual available for equipment model).

```
[Actions ▼]
  → View Manual Section
  → Create Work Order
  → Add to Handover
```

---

### 2. Equipment Entity Page

Equipment with uploaded manual.

```
[Actions ▼]
  → View Manual
  → Create Work Order
```

---

### 3. Work Order Page

WO linked to fault or equipment with manual.

```
[Actions ▼]
  → View Related Manual
```

---

### 4. Direct Query

"show manual for MTU overheating"

---

## The Exact UX Flow (Step by Step with Justification)

### Step 1: User Triggers Action

Clicks "View Manual Section" from fault page.

---

### Step 2: Section Lookup (Backend)

```python
# Get equipment model from fault
equipment = get_equipment_from_fault(fault_id)
manual = get_manual_for_model(equipment.model)

# Find section by fault code
section = find_section_by_fault_code(manual, fault.code)

# Fallback: keyword match
if not section:
    section = find_section_by_keywords(manual, fault.description)

# Last resort: troubleshooting default
if not section:
    section = get_default_section(manual, "troubleshooting")
```

**Why simple matching:**
- Fault codes → sections (database mapping)
- Keywords → section titles (string match)
- No ML, no confidence scores
- Fast, predictable, maintainable

---

### Step 3: Manual Opens to Section

```
┌─ MTU 16V4000 Manual ─────────────────────────┐
│                                               │
│ Section 7.3 - Overheating Diagnosis           │
│ Page 142                                      │
│                                               │
│ ┌───────────────────────────────────────────┐ │
│ │ [PDF viewer showing page 142]             │ │
│ │                                           │ │
│ │ 7.3 OVERHEATING DIAGNOSIS                 │ │
│ │                                           │ │
│ │ Symptom: Coolant temperature exceeds...   │ │
│ │                                           │ │
│ │ Possible causes:                          │ │
│ │ 1. Coolant level low                      │ │
│ │ 2. Thermostat failure                     │ │
│ │ 3. Water pump malfunction                 │ │
│ │ ...                                       │ │
│ └───────────────────────────────────────────┘ │
│                                               │
│ [Contents] [Search] [Close]                   │
└───────────────────────────────────────────────┘
```

**Why viewer:**
- Engineer reads, navigates freely
- Can jump to other sections if needed
- Close → returns to fault page

**No mutation** (READ action).

---

### Step 4: Multiple Sections Match (Edge Case)

If keywords match 3+ sections:

```
┌─ MTU 16V4000 Manual ─────────────────────────┐
│                                               │
│ Showing: Section 7.3 - Overheating Diagnosis  │
│                                               │
│ ℹ️  Other relevant sections:                  │
│   • 12.1 Temperature Sensor Calibration       │
│   • 15.2 Cooling System Maintenance           │
│                                               │
│ [PDF viewer...]                               │
└───────────────────────────────────────────────┘
```

Opens to best match, shows others for reference.

---

### Step 5: Manual Not Available (Edge Case)

Equipment model has no manual uploaded.

```
┌─ Manual Not Available ───────────────────────┐
│                                               │
│ ⚠️  No manual uploaded for:                   │
│    MTU 16V4000                                │
│                                               │
│ [Request Manual Upload] [Close]               │
└───────────────────────────────────────────────┘
```

"Request Manual Upload" → Creates task for admin.

**Doesn't block work** (engineer might have manual elsewhere).

---

### Step 6: External Manual (Alternative)

Manual is external link (not uploaded PDF).

```
┌─ Open External Manual ───────────────────────┐
│                                               │
│ This manual is hosted externally:            │
│                                               │
│ MTU 16V4000 Operation Manual                  │
│ https://mtu-online.com/manuals/16v4000        │
│                                               │
│ [Open in Browser] [Copy Link] [Cancel]       │
└───────────────────────────────────────────────┘
```

**Why allow:**
- Manufacturer-hosted manuals stay up-to-date
- No storage/upload burden
- Can't target specific section (external site limitation)

---

## What This Action Does NOT Do

* ❌ No "suggested sections" based on user behavior (use fault code mapping only)
* ❌ No tracking "most viewed sections" (noise)
* ❌ No ML to "predict which manual you need" (use entity context)
* ❌ No auto-opening manuals proactively (explicit user action only)
* ❌ No "related documentation" recommendations (noise)
* ❌ No reading time tracking or completion metrics (surveillance)
* ❌ No blocking if manual missing (show message, allow request)

**If a human didn't click to view it, manual doesn't open.**

---

## Habit-Forming Principle

> **Documentation is one click away, right where you need it.**

The manual action appears **adjacent to the problem** (fault page, equipment page, WO page).

Not in a "Documents" section somewhere.

Opens to the **relevant section** (not page 1).

This creates habit:
- See problem → Click manual → Read solution
- Not: See problem → Remember where docs are → Navigate → Search

**The design makes using documentation faster than asking a colleague.**

---

## Testing the Mental Model

Ask: "Does viewing a manual change any situation state?"
**No.** → Correct. READ action only.

Ask: "Can I view a manual if it's not uploaded?"
**Shows message.** → Correct. Allows request, doesn't block.

Ask: "Will the system suggest which manual section to read based on my behavior?"
**No.** → Correct. Uses fault code/keyword mapping only.

Ask: "Does the manual auto-open when I view a fault?"
**No.** → Correct. User explicitly clicks.

If any answer changes, the design has drifted.

---
