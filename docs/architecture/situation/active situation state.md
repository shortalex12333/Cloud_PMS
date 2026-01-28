active situation state,md

1) Baseline situation parameters (small, universal, enough)

These are the minimum fields your active_situation needs so you can trigger scaffolding safely:

Identity

yacht_id

user_id

role

device_type (mobile/desktop)

Situation Key

primary_entity_type (equipment/part/work_order/fault/location/person/document)

primary_entity_id

symptom_code (optional but powerful)

domain (inventory/maintenance/manuals/hor/purchasing/people)

State

state (IDLE/CANDIDATE/ACTIVE/COOLDOWN/RESOLVED)

confidence_points (deterministic)

phase (investigating / acting / wrapping_up) — inferred from events

Evidence flags

opened_manual

viewed_history

mutation_prepared

mutation_committed

handover_added

repeated_queries_count

Nudge control

nudge_last_shown_at

nudge_dismissed (per nudge type)

nudge_budget_remaining (enforce “one new decision at a time”)

That’s enough to drive everything you described.

2) Action brackets (don’t overcomplicate)

Keep your foundation to two primary brackets (you already have this right):

A) READ / OBSERVE

No state changes, no signature.
Examples:

view/open

print

compare

show history

open manual section

B) WRITE / COMMIT

Any effect beyond the UI.
This includes more than DB writes:

editing inventory / WO / HOR

adding to handover

sending email / notifying people

sharing externally

creating drafts that later commit

Key decision: treat “send email/WhatsApp/share” as WRITE because it changes the real world (communication/audit) even if DB doesn’t change much.

That keeps trust clean.

3) Sub-brackets inside WRITE (so engineers can gate correctly)

WRITE is too broad; split it into 4 subtypes with different risk:

WRITE-NOTE
Adds context, low risk
(e.g., add note, add to handover draft)

WRITE-STATE
Changes operational records
(e.g., inventory qty, WO close, HOR sign)

WRITE-COMMS
Notifies people / sends messages
(e.g., email reorder, notify engineer)

WRITE-FINANCIAL / PROCUREMENT (later)
Orders, purchase requests, invoices

Each subtype gets default security rules:

NOTE: signature optional by role

STATE: signature required

COMMS: signature required + preview of message content

FINANCIAL: signature required + extra confirmation/2nd approver later

4) Map “situations → allowed action brackets” (this is the glue)

Instead of listing everything, define what action brackets are valid per situation type.

Examples:

Situation: Equipment + symptom (maintenance)

Allowed:

READ: manual section, history, related docs

WRITE-NOTE: add note, add to handover

WRITE-COMMS: notify engineer

WRITE-STATE: create WO draft (commit later)

Situation: Part lookup / inventory location

Allowed:

READ: view stock, print, location

WRITE-STATE: adjust qty (signed)

WRITE-NOTE: add to handover

WRITE-COMMS: notify inventory manager

WRITE-PROC: create reorder draft (later)

Situation: Hours of Rest

Allowed:

READ: view ledger

WRITE-STATE: sign/correct entry (always signed)

This gives you a stable baseline. Actions just plug in.

5) Guardrails (engineers must implement)

No new bracket types without a written rule.
If someone proposes one, it’s usually feature creep.

Only one surfaced nudge at a time
Everything else hidden behind ▼.

Draft-first for anything proactive
Especially COMMS and PROCUREMENT.

Preview always for COMMS + STATE writes
Not “why”, but “what will happen”.

Suppression memory
If user ignores/dismisses, don’t nag.

6) How this ties directly to active_situation

active_situation doesn’t need “every possible action.”
It needs to decide:

What bracket is relevant now?

Is this READ-only moment or WRITE moment?

Are we in investigate/act/wrap-up?

What’s the single best nudge (if any)?

Actions themselves are pulled from the registry based on:

situation type

entity type

user role

bracket allowed

My recommendation (next concrete step)

Create two files your engineer can implement this week:

1) situation_policy.yaml

Defines:

situation types

allowed brackets

default nudges

thresholds

2) action_registry.json

Defines:

action → bracket/subtype

signature requirements

preview requirements

dropdown visibility

Then the attachment engine becomes deterministic:

compute situation type

filter actions by allowed brackets

pick 1 primary READ action

put the rest behind ▼

optionally surface 1 nudge if ACTIVE