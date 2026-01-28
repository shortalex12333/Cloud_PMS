
#  Work Order Situational Active State

**CelesteOS — Situation Policy Spec**

---

## Purpose

The Work Order Situational Active State exists to answer one question:

> **Is the user actively executing, investigating, or closing a real maintenance task — or are they just orienting themselves?**

It governs:

* when actions appear
* where actions appear
* when signatures are required
* how inventory, photos, and comments attach
* how trust is built through transparency

It does **not** manage scheduling logic or predictive planning.
It manages **human execution of work**.

---

## Core Principle

> **Work Orders are read first, acted on second, and signed last.**

The UI must:

* encourage understanding before action
* avoid clutter
* make commitment moments explicit and trustworthy

---

## Situation Key

Each Work Order situation is scoped to:

* `yacht_id`
* `user_id`
* `primary_entity_type = work_order`
* `primary_entity_id = work_order_id`
* optional linked context:

  * equipment_id
  * fault_id
  * part_ids (resolved dynamically)

---

## Situation States

```text
IDLE        → browsing / orienting
CANDIDATE   → work order opened, not yet acted on
ACTIVE      → user is investigating or executing work
COOLDOWN    → recently active, suppress re-prompts
RESOLVED    → work order completed and signed
```

---

## State Transitions

### IDLE → CANDIDATE

Triggered by:

* user opens a specific work order
* user navigates from search → WO detail view

❗ Viewing lists (“Due today”, “Overdue”) does **not** create a situation.

---

### CANDIDATE → ACTIVE

Triggered by **any commitment signal**:

* add note / comment
* attach photo
* change status (e.g. start / in progress)
* attach document
* log time
* link inventory
* prepare close

At this point:

* the work is real
* scaffolding may appear
* audit trail begins

---

### ACTIVE → RESOLVED

Triggered only by **signed completion**:

* `Mark as Done` confirmed
* required completion fields satisfied
* optional inventory usage logged
* signature accepted

This is the **canonical resolution path**.

---

### ACTIVE → COOLDOWN

Triggered by:

* user exits WO
* inactivity timeout
* dismissal of completion prompts

Purpose:

* avoid repeated nudges
* preserve calm UI

---

## Work Order Discovery (Search-Level UX Contract)

### Search Queries

Examples:

* “overdue work orders”
* “what’s due today”
* “show breakdowns”
* “recently updated work orders”

### Search Response Structure

Above results, **below search bar**, always show **WO quick filters**:

* `Overdue`
* `Due Today`
* `Breakdowns`
* `Recently Updated`

These are **navigation buttons**, not actions.

---

### Search Result Preview Rules

* Work Orders appear as a **single-row preview**
* One line per WO:

  * title
  * status badge
  * due / overdue indicator
* No inline actions
* No expanded tables

Click → expands into Work Order List View.

This prevents overload and preserves Spotlight behavior.

---

## Work Order List View

Purpose:

* scan
* prioritize
* select

Allowed:

* filters
* sort
* readiness badge (Ready / Blocked / Caution)

Not allowed:

* editing
* closing
* assigning
* inventory actions

List view is **never** an execution surface.

---

## Work Order Detail View (Execution Surface)

This view is **long-lived** and scrollable.
Users keep it open while working.

### Layout (fixed order)

1. **Header**

   * WO title
   * status
   * readiness badge (shelf for now)
   * linked equipment

2. **Brief**

   * description
   * requirements
   * location / access notes

3. **Procedure / Notes**

   * steps or narrative
   * collapsible if long

4. **Timeline (truth stream)**

   * comments
   * status changes
   * inventory usage
   * attachments
   * timestamps + user attribution

---

## Attachments & Images (Trust-Critical)

### Storage Rules

* Images are stored in Supabase bucket
* Each image has:

  * unique storage key
  * linked `work_order_id`
  * uploader `user_id`
  * timestamp

Images are **never embedded blobs**.

### Viewing Behavior

* Clicking an image:

  * loads from bucket temporarily
  * opens viewer
  * shows image-specific comment thread

Each image can have its **own notes**.

No orphaned images.
No ambiguous references.

---

## Action Placement Rules (Non-Negotiable)

### Top of WO Detail

Only **capture + reading** actions:

* `+` (universal action trigger)

  * add note
  * add photo (camera icon)
  * attach document
* view history
* open manual

No completion actions here.

---

### Bottom of WO Detail

**Execution & completion only**:

* log time
* parts used
* mark as done

This:

* reduces clutter
* makes commitment deliberate
* aligns with human workflow

---

## Mark as Done — Canonical Completion Flow

This is the **only** supported completion path.

### Trigger

User taps: `Mark as Done`

---

### Completion Sheet (Modal)

Sections, in order:

1. **Completion Notes** (required)
2. **Photos** (optional, encouraged)
3. **Time Logged** (role-dependent)
4. **Parts Used** (optional but prompted)

---

### Parts Used Selector (Trust-Focused)

* Opens inventory search **inside the modal**
* Shows:

  * part name (full, not truncated)
  * image (if available)
  * location / container
* User must confirm:

  * quantity
  * correct part (“Are you sure?” confirmation)

On confirmation:

* inventory usage events are created
* probable count is decremented
* usage is attributed to user
* events are linked to this WO

No inventory screen required.
No manual count edits allowed.

---

### Transparency (Critical for Adoption)

Before final save, show a **plain-language summary**:

> You are about to:
>
> * mark this work order as completed
> * save completion notes and photos
> * deduct 1 × Fuel Pump (CAT) from inventory
> * sign this work order

This step builds trust.

---

### Signature

* Required to complete
* Tied to:

  * WO closure
  * inventory usage
  * audit trail

---

## Audit Trail (Immutable)

Each Work Order maintains an event stream:

* created
* viewed
* notes added
* photos attached
* inventory used (who, what, how many)
* status changes
* printed / exported
* closed (signed)

No silent mutations.
No retroactive edits.

---

## Explicitly Not Allowed

* Closing a WO without signature
* Editing inventory counts directly
* Attaching parts outside ACTIVE state
* Inline actions in list views
* Hiding system actions from users (“magic” saves)

---

## One-Line Doctrine

> **A Work Order is not complete until a human signs what was done — and what was used.**

---
