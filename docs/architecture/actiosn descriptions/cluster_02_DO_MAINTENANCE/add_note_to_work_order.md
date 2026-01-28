# Add Note to Work Order

**CelesteOS**
**Action Type:** MUTATE
**Cluster:** 02_DO_MAINTENANCE
**Priority:** P0

---

## Purpose

This action exists to **create a timestamped record of what happened during the work**.

Notes are the narrative of the work order—what was found, what was tried, what worked, what didn't.

It answers one question:

> "What did I do, and what should the next person know?"

---

## Core Doctrine

* **Notes are sequential, not summary** — Each note is a moment in time, not an overview
* **Timestamp = accountability** — When + who matters as much as what
* **Brief is better** — Notes are updates, not essays
* **No forced notes** — User decides when worth documenting (not every action needs a note)

---

## Mental Model (The Anchor)

> **A note is a breadcrumb for whoever picks up this work next (including future you).**

Not documentation. Not a report.

A timestamped observation: "Here's what I found/did/tried."

---

## The Habit This Creates (Why It Helps)

### The real context:

Engineer working on Generator 2 thermostat replacement. Opened panel, found old thermostat stuck. Tried removal tool, didn't work. Used heat gun, came free.

**Without this action:**
- Engineer finishes work
- Doesn't record the "stuck thermostat" detail
- Next time same WO type: different engineer wastes 30 minutes trying removal tool
- Same problem, same wasted time

**With this action:**
- After each step, adds note:
  - "Thermostat stuck, removal tool ineffective"
  - "Heat gun (low setting) freed thermostat"
  - "New thermostat installed, temp normal"
- Next engineer sees notes
- Goes straight to heat gun
- Saves 30 minutes

**The habit:**
"Do something → Note what happened → Next person learns"

**Not:**
"Do work → Finish → Forget details → Knowledge lost"

This action **builds institutional memory** by making logging immediate and frictionless.

---

## Entry Conditions

### 1. Work Order Page (Primary)

Always available while WO active.

```
[Actions ▼]
  → Add Note
  → Add Part
  → Mark Complete
```

---

### 2. Contextual Prompts

After logging parts: "Add note about parts usage?"

After major state change: Note action highlighted.

---

### 3. Direct Query

"add note to WO-089"

---

## The Exact UX Flow (Step by Step with Justification)

### Step 1: User Triggers Action

Clicks "Add Note" from WO page.

---

### Step 2: Note Form Opens (Minimal)

```
┌─ Add Note to WO-2024-089 ────────────────────┐
│                                               │
│ Note *                                        │
│ ┌───────────────────────────────────────────┐ │
│ │                                           │ │
│ │                                           │ │
│ │                                           │ │
│ └───────────────────────────────────────────┘ │
│                                               │
│ Category: Update [▼]                          │
│ Options: Update, Diagnosis, Action, Issue     │
│                                               │
│ [Cancel]                       [Add Note]     │
└───────────────────────────────────────────────┘
```

**Why minimal:**
- Note is fast, frequent action
- Too many fields = friction
- Category helps filtering later, but defaults to "Update"

**No pre-fill** (unless from contextual prompt).

---

### Step 3: User Types Note

```
Note:
┌───────────────────────────────────────────┐
│ Thermostat stuck. Removal tool failed.   │
│ Heat gun (low setting) worked.            │
│ New unit installed, temp normal.          │
└───────────────────────────────────────────┘

Category: Action
```

**Why brief:**
- Engineer is working, not writing reports
- 1-3 sentences captures what matters
- Timestamp + context provides rest

---

### Step 4: Commit (Immediate, No Preview)

Clicks "Add Note" → Posted immediately.

```
┌─ Note Added ─────────────────────────────────┐
│                                               │
│ ✓ Note added to WO-2024-089                   │
│                                               │
│ [Add Another] [Close]                         │
└───────────────────────────────────────────────┘
```

**Why no preview:**
- User just typed it (can see what they wrote)
- Low-risk mutation (just adds text record)
- Speed matters (don't interrupt workflow)

**Backend effects:**
- Note created with: content, category, user_id, timestamp
- WO last_activity updated
- If WO was CANDIDATE → transitions to ACTIVE (first note = work started)
- Audit log entry

---

### Step 5: Note Appears in WO Timeline

WO page shows chronological timeline:

```
┌─ Work Order Timeline ────────────────────────┐
│                                               │
│ 2024-01-08 14:45 - Alex Thompson              │
│ 🔧 Action                                     │
│ Thermostat stuck. Removal tool failed.        │
│ Heat gun (low setting) worked.                │
│ New unit installed, temp normal.              │
│                                               │
│ ───────────────────────────────────────────── │
│                                               │
│ 2024-01-08 12:30 - Sarah Chen                 │
│ 📋 Diagnosis                                  │
│ Coolant temp reading 95°C (normal 85°C).      │
│ Thermostat suspect.                           │
│                                               │
│ ───────────────────────────────────────────── │
│                                               │
│ 2024-01-08 10:00 - System                     │
│ Work order created from fault F-2024-089      │
└───────────────────────────────────────────────┘
```

---

## Edge Cases

### 1. Empty Note

User clicks "Add Note" without typing anything.

**Behavior:**
- Validation error: "Note content required"
- Cannot submit empty

**Why:**
Empty note is meaningless. Just close the form.

---

### 2. Very Long Note (>2000 chars)

User pastes large text block.

**Behavior:**
- Warning: "Note exceeds 2000 characters"
- Suggestion: "Consider breaking into multiple notes or attaching document"
- Can trim or cancel

**Why limit:**
Notes are breadcrumbs, not documentation. Large blocks should be attachments.

---

### 3. Duplicate Similar Note

User adds note very similar to previous note (within 10 minutes).

**Behavior:**
- Info shown: "Similar note added 5 min ago: [preview]"
- Options: [Edit Previous] [Add Anyway] [Cancel]

**Why show:**
- Might be accidental duplicate
- Or intentional update
- User decides

---

## What This Action Does NOT Do

* ❌ No forced notes at specific stages (user decides when worth noting)
* ❌ No "suggested note content" based on WO type (noise)
* ❌ No ML auto-categorization (simple keyword inference only)
* ❌ No note templates based on "similar WOs" (noise)
* ❌ No requiring notes before completing WO (optional, not mandatory)
* ❌ No note quality scoring or completeness metrics (surveillance)
* ❌ No auto-tagging or keyword extraction (over-engineering)

**If a human didn't type it, it's not a note.**

---

## Habit-Forming Principle

> **Note as you work, not after.**

The action is **always available** (one click from WO page).

Form is **minimal** (type → category → submit in 10 seconds).

This creates habit:
- Do something → Note it → Continue work
- Not: Do work → Plan to write notes later → Forget

**The design makes documentation happen in real-time.**

---

## Testing the Mental Model

Ask: "Are notes required before completing a WO?"
**No.** → Correct. Optional, user decides.

Ask: "Does adding a note change the WO status?"
**Only if first note.** → Correct. CANDIDATE → ACTIVE on first note.

Ask: "Can I edit a note after posting?"
**No.** → Correct. Notes are immutable timeline (add new note if correction needed).

Ask: "Will the system suggest what to write in notes?"
**No.** → Correct. User writes freely.

If any answer changes, the design has drifted.

---
