Inventory Situational Active State

CelesteOS — Situation Policy Spec

Purpose

The Inventory Situational Active State exists to answer one question:

Is the user interacting with inventory as part of a real operational dependency — or just orienting themselves?

It governs:

when inventory actions are allowed

when accountability is required

when nudges may appear

when inventory remains strictly observational

It does not manage stock correctness directly.
It manages when reality-changing actions are justified.

Core Principle

Inventory is READ-only by default.
It becomes ACTIVE only at the moment of use or dependency.

Browsing is not intent.
Counting is not intent.
Using a part is intent.

Situation Key

Each inventory situation is scoped to:

yacht_id

user_id

primary_entity_type = part

primary_entity_id

optional linked_context:

work_order_id

fault_id

equipment_id

Situation States
IDLE        → No inventory relevance
CANDIDATE   → Inventory risk or interest detected
ACTIVE      → Inventory is being used or depended upon
COOLDOWN    → Recently active, suppress re-prompts
RESOLVED    → Usage acknowledged and logged

State Transitions
IDLE → CANDIDATE

Triggered by risk or attention, not intent.

Any of the following:

part appears in:

out-of-stock query

low-stock query

part accessed (viewed) once

container (box) opened

inventory table expanded

❗ No actions allowed.
❗ No nudges allowed.

CANDIDATE → ACTIVE

Triggered by clear dependency or action intent.

Any one of the following:

Same part opened twice within short window

Part opened from:

active work order

active fault

User taps:

–1 used

Explicit write intent detected:

order

reserve

log usage

This transition increments confidence_points.

ACTIVE → RESOLVED

Triggered by accountable usage.

User completes a signed usage event:

–1 used

signature accepted

OR usage logged via linked WO completion

This is the primary resolution path.

ACTIVE → COOLDOWN

Triggered when:

user exits part view

no activity within timeout window

user dismisses inventory nudge

Purpose:

prevent repeated prompts

preserve calm UI

Allowed Actions by State
IDLE

Allowed:

view inventory

view containers

view locations

Not allowed:

any mutations

any nudges

any write actions

CANDIDATE

Allowed:

view part details

view linked equipment

passive indicators only

Not allowed:

usage logging

reorder drafts

handover prompts

ACTIVE

Allowed (strictly gated):

Primary action

–1 used

Secondary actions (behind ▼)

add_part_to_handover

create_reorder_draft (only if low/probable)

view_linked_work_order

Not allowed:

manual count edits

batch deductions

silent mutations

COOLDOWN

Allowed:

READ actions only

Nudges:

suppressed unless material change occurs

Usage Event (Critical)

Inventory deduction is event-based, never an edit.

Usage Event Schema
{
  "event_type": "inventory_usage",
  "part_id": "...",
  "quantity": 1,
  "user_id": "...",
  "timestamp": "...",
  "linked_context": {
    "work_order_id": null,
    "fault_id": null
  },
  "signature": true
}


Effects:

decrement probable_count

update confidence score

append immutable audit log

attribute usage to user

Accountability Rules

Every usage event:

is attributed to a user

requires explicit confirmation (signature)

No anonymous deductions

No silent background updates

This enables:

positive accountability

behavioral visibility

defensible audit trails

Probable Count & Confidence

Each part maintains:

probable_count

confidence_level (HIGH / MEDIUM / LOW)

last_verified_at

usage_event_count

Watchdog Trigger (Passive Only)

Triggered when:

probable_count ≤ minimum_threshold

OR confidence == LOW and part accessed recently

Behavior:

annotate part

no forced action

no automatic reorder

UX Constraints (Non-Negotiable)

Inventory tables are descriptive

Actions only appear at part level

Only one primary action at a time

No batch mutations

No number input fields for counts

Explicitly Not Allowed

Editing stock numbers directly

“Correcting” counts without events

Logging usage outside ACTIVE state

Prompting inventory actions during browsing

Surfacing inventory nudges globally

One-Line Doctrine

Inventory becomes actionable only at the moment a part leaves the shelf — and that moment is signed.