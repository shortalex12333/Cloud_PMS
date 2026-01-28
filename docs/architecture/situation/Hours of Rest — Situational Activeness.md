⏱ Hours of Rest — Situational Activeness

CelesteOS | Compliance State Specification

Purpose

The Hours of Rest (HOR) system exists to create legally valid, inspectable, and trusted records of fitness for duty, in accordance with:

STCW Regulation A-VIII/1

Flag State / MLC / USCG overlays

It does not:

optimise schedules

predict fatigue

negotiate working culture

It does:

enforce cadence

calculate compliance

lock records with signatures

make non-compliance visible and attributable

Core Doctrine

Hours of Rest is not a task.
It is a legal ledger.

Users do not “use” HOR casually.
They declare reality, and then sign it.

Situational Model (Different from other domains)

HOR does not use:

IDLE

CANDIDATE

ACTIVE (in the usual sense)

Instead, HOR is governed by Record State, not user intent.

Record States
OPEN
AT_RISK
ENDORSED
COUNTERSIGNED
LOCKED


These states apply per person, per period.

State Definitions
OPEN

Daily entries editable

Auto-deployed working pattern may be applied

Real-time compliance calculated

No signatures yet

This is the only state where hours can be edited.

AT_RISK

OPEN + projected or actual non-compliance detected

Triggers:

< 10 hrs rest in any rolling 24h

< 77 hrs rest in rolling 168h

invalid rest segmentation

flagged exception awaiting compensation

Behavior:

visual warning (amber/red)

saving still allowed

endorsement blocked until resolved or exception tagged

Reality is allowed.
Paper lies are not.

ENDORSED (Crew)

Weekly period signed by the seafarer

Entries become read-only for crew

Any later change requires:

explicit edit action

mandatory comment

revision event

This is personal accountability.

COUNTERSIGNED (Department / Master)

Monthly (or flag-required) countersignature

Confirms review, not perfection

Entries become read-only for management

This is organizational accountability.

LOCKED

Record is immutable

Export enabled

Inspector-ready

This is legal artefact state.

Daily Entry Model (Crew UX Contract)
Daily Conscious Entry (Non-Negotiable)

HOR is submitted per day

No bulk backfilling

No “set and forget” weeks

This forces daily awareness without micromanagement.

Auto-Deploy Working Hours (Template, not truth)

Each crew member may define a:

Declared Normal Working Pattern
Example:

Work: 07:00–12:00, 14:00–19:00

Rules:

Pattern auto-deploys per day

Marked clearly as:

“Pre-filled from your normal working day”

Crew must implicitly accept by endorsing later

If reality differs, the crew must adjust.

Laziness becomes visible responsibility.

Entry Interaction

24-hour horizontal grid

Drag / tap to adjust

Blue = compliant

Red = non-compliant

Rolling totals always visible

Crew never calculate totals.
They only declare work vs rest.

Smart Assistance (Strictly Evidence-Driven)
Activity-Based Prompting (Optional, Controlled)

A HOR prompt may appear only if all conditions are true:

User active in Celeste ≥ 65 minutes

Activity occurs outside declared normal hours

No HOR entry covers that time

No prior dismissal for that window

Prompt text:

“You were active from 21:10–22:20.
Want me to add this to today’s work hours?”

Options:

Add

Ignore

Rules:

Ignored prompts suppress for 24h

Never re-prompt for same window

No time-based nagging

Assistance, not surveillance.

Compliance Calculation (System-Owned)

The system always calculates:

≥ 10 hours rest in any rolling 24h

≥ 77 hours rest in any rolling 168h

≤ 2 rest periods per 24h

≥ 6 hours continuous rest

≤ 14 hours between rest periods

Flag-permitted exceptions only

Crew cannot override calculations.
They can only explain exceptions.

Exceptions & Comments
Exceptions (Drills / Emergencies)

Must be explicitly tagged

Allow temporary non-compliance

Require compensatory rest later

Remain visible forever

Comments

Mandatory only when:

exception logged

violation occurs

endorsed record is edited

Comments exist for defensibility, not storytelling.

Signatures & Cadence (System-Enforced)
Crew

Weekly endorsement required

Prompted Monday 07:00 local

One reminder only

Department Head

Monthly review & countersign

Immediate alerts for:

violations

missing endorsements

Master

Final countersign

Locks record

Enables export

Cadence is defined by Celeste, not the vessel.

Editing Past Records
Query Example

“Change my HOR for last Friday”

Behavior:

Record surfaced in read-only summary

Edit allowed only if:

not LOCKED

Mandatory reason comment

Revision logged as event

No silent correction.
No retroactive cleanup.

Audit & Export

When LOCKED:

Standard IMO/ILO table format

24h blocks

Rolling totals shown

Signatures visible

Exceptions annotated

One click. No recalculation.

Explicitly Not Allowed

Monthly bulk entry

Editing LOCKED records

Hiding violations

Auto-making records compliant

AI “fixing” hours

One-Line Doctrine

Hours of Rest is valid only when reality is declared daily and signed weekly.