# Add to Handover

**CelesteOS**
**Action Type:** MUTATE
**Cluster:** 05_HANDOVER_COMMUNICATION
**Priority:** P0

---

## Purpose

This action exists to **capture critical information before shift change**.

When something important happens that the next crew must know, it needs to be recorded immediately—not "later when I have time."

It answers one question:

> "What does the next shift need to know right now?"

---

## Core Doctrine

* **Handover is immediate, not retrospective** — Capture when fresh, not at end of shift
* **Context comes free** — System knows what you're looking at (fault, equipment, document)
* **Brief is better** — Handover is headlines, not essays
* **Human decides importance** — System never auto-adds to handover (no noise)

---

## Mental Model (The Anchor)

> **Handover is a note to your future self (or the person replacing you).**

Not a report. Not a log. Not documentation.

A message: "Here's what matters right now."

---

## The Habit This Creates (Why It Helps)

### The real context:

Engineer is troubleshooting Generator 2. Coolant issue. Shift ends in 20 minutes.

They've done some work but it's not finished. Next shift needs to know:
- What the problem is
- What's been tried
- What to check next

**Without this action:**
- They'd have to remember to write handover notes later
- Or tell next shift verbally (gets forgotten)
- Or write on paper (gets lost)
- Critical context disappears between shifts

**With this action:**
- Currently viewing fault F-2024-089
- Click "Add to Handover" from fault actions
- Form pre-filled: "Generator 2 - MTU-OVHT-01"
- Add note: "Topped up coolant, monitoring temp. Check again in 2hrs."
- Sign → Handover item created
- Next shift sees it immediately in their handover brief

**The habit:**
"Found something important → Add to handover immediately → Next shift informed"

**Not:**
"Found something important → Hope I remember to tell someone → Context lost"

This action **captures knowledge while it's fresh**, preventing information loss at shift changes.

---

## Entry Conditions (When This Action Appears)

### 1. Fault Entity Page

User viewing fault can add to handover.

```
[Actions ▼]
  → Create Work Order
  → Add to Handover
  → View Manual
```

**Why here:**
Active faults are the most common handover item.

---

### 2. Equipment Entity Page

User viewing equipment can add general status to handover.

**Example:**
"Generator 2 running hot, watch coolant temp"

---

### 3. Work Order Page

User can hand over in-progress work.

**Example:**
"WO-2024-089 - replaced thermostat, testing now"

---

### 4. Document/Manual Page

User can flag important procedures or findings.

**Example:**
"New MTU service bulletin - affects our generators"

---

### 5. Direct Query (Context-Free)

User queries: "add to handover"

Action appears beneath search, opens form with no pre-fill.

**Why allow:**
Sometimes handover item isn't tied to an entity (general ship status, weather, crew notes).

---

## The Exact UX Flow (Step by Step with Justification)

### Step 1: User Triggers Action

From entity page (fault, equipment, WO, etc.), clicks "Add to Handover".

---

### Step 2: Form Opens with Context Pre-fill

```
┌─ Add to Handover ────────────────────────────┐
│                                               │
│ Title *                                       │
│ ┌───────────────────────────────────────────┐ │
│ │ Generator 2 - MTU-OVHT-01                 │ │ ← Pre-filled
│ └───────────────────────────────────────────┘ │    from fault
│                                               │
│ Category                                      │
│ ┌───────────────────────────────────────────┐ │
│ │ Ongoing Fault                       [▼]   │ │ ← Inferred
│ └───────────────────────────────────────────┘ │    from entity
│   Options: Ongoing Fault, Completed Work,     │
│            Important Info, Pending Action     │
│                                               │
│ Details *                                     │
│ ┌───────────────────────────────────────────┐ │
│ │ Coolant temp high - occurred 8 times      │ │ ← Pre-filled
│ │ in last 30 days.                          │ │    summary
│ │                                           │ │
│ │ [Add your note here]                      │ │ ← Cursor here
│ └───────────────────────────────────────────┘ │
│                                               │
│ Priority                                      │
│ ┌───────────────────────────────────────────┐ │
│ │ Normal                              [▼]   │ │
│ └───────────────────────────────────────────┘ │
│   Options: Low, Normal, High, Urgent          │
│                                               │
│ [Cancel]                      [Add to Handover]│
└───────────────────────────────────────────────┘
```

**Pre-fill logic (from fault example):**

```
title = f"{equipment.name} - {fault.code}"
category = "ongoing_fault"
details = f"{fault.description}\n\nOccurrences: {fault.count} in last 30 days\n\n"
priority = fault.severity or "normal"
```

**Why pre-fill:**
- User shouldn't retype equipment name, fault code (already known)
- Cursor starts in details field (ready to add their note)
- Context summary above the fold (next shift sees full picture)

**Why NOT auto-submit:**
- User needs to add "what I did" or "what to check next"
- Priority might need adjustment
- Title might need clarity

**Category inference:**

| Entity Type | Default Category     |
|-------------|----------------------|
| Fault       | Ongoing Fault        |
| Work Order  | Completed Work       |
| Document    | Important Info       |
| Equipment   | Pending Action       |
| None        | Important Info       |

User can override.

---

### Step 3: User Adds Their Note

```
Details:
┌───────────────────────────────────────────┐
│ Coolant temp high - occurred 8 times      │
│ in last 30 days.                          │
│                                           │
│ Topped up coolant by 2L. Now monitoring.  │ ← User adds
│ Check temp again in 2 hours.              │    context
│ If still high, check thermostat.          │
└───────────────────────────────────────────┘
```

**Why brief is better:**
- Next shift reads handover in 2 minutes
- Headlines matter, not essays
- Details live in fault/WO (linked)

---

### Step 4: Commit (Lightweight)

User clicks "Add to Handover" → Commits immediately.

No preview screen for handover items.

**Why:**
- Handover is time-sensitive (shift ending)
- Content is brief and visible
- No complex side effects
- User can see exactly what they typed

**Sign = timestamp + user ID** (implicit signature).

```
┌─ Added to Handover ──────────────────────────┐
│                                               │
│ ✓ Handover item created                       │
│                                               │
│ Next shift will see this in their brief.      │
│                                               │
│ [View Handover] [Close]                       │
└───────────────────────────────────────────────┘
```

---

## The Real Behavior This Enables

### Scenario: Mid-shift Discovery

Engineer finds fault. Starts investigating. Shift ends before resolution.

**Without handover:**
- Next engineer arrives
- Sees fault in system (no context)
- Doesn't know what's been tried
- Repeats same checks
- Wastes time

**With handover:**
- Current engineer adds to handover: "Checked coolant, topped up. Monitor temp."
- Next engineer reads handover
- Sees context immediately
- Continues from where last shift left off
- Efficient transition

---

### Scenario: Important Document

New safety bulletin arrives. Affects multiple systems.

**Flow:**
- Engineer views document
- Adds to handover: "New MTU bulletin - coolant system changes. Read before next generator service."
- Tagged "Important Info"
- All shifts see it until acknowledged

---

## What This Action Does NOT Do (Write This Down)

To keep handover trusted and useful:

* ❌ No auto-adding items to handover based on "importance scores" (user decides what matters)
* ❌ No ML predictions of "what to include in handover" (trust human judgment)
* ❌ No forced handover at shift end (engineer chooses what's worth mentioning)
* ❌ No "suggested handover items" based on historical patterns (noise)
* ❌ No auto-categorization using ML (simple entity-based inference only)
* ❌ No blocking if handover not written (optional, not mandatory)
* ❌ No reminders or nudges about "you haven't written handover" (friction, not help)
* ❌ No auto-emailing handover to next shift (they read it when they start, not before)

**If a human didn't add it, it's not in handover.**

---

## Habit-Forming Principle

> **Capture knowledge when fresh, not when convenient.**

The action is **immediately available** wherever you are (fault page, WO page, equipment page).

Not hidden in a "Handover" section you navigate to later.

This creates a habit:
- Discover something → Add to handover now → Next shift informed
- Not: Discover something → Plan to write handover later → Forget

**The design makes the right behavior the easiest behavior.**

---

## Testing the Mental Model

Ask: "Does adding to handover resolve the fault?"
**No.** → Correct. Handover is communication, not resolution.

Ask: "Can I add to handover without an entity link?"
**Yes.** → Correct. General notes are valid.

Ask: "Will the system auto-add important faults to handover?"
**No.** → Correct. Human decides importance.

Ask: "Can next shift see handover before their shift starts?"
**No.** → Correct. Handover is read when you start work, not pushed before.

If any answer changes, the design has drifted.

---
