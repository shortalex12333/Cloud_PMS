README.md
Active situation state is a lightweight, rule-based session tracker that answers one question:

“Is the user actively working on a real operational issue right now — and if so, what is it?”

It’s not ML and it’s not a prediction. It’s a deterministic state machine driven by explicit user events (searches, opens, actions).

Why it exists

Search results alone don’t tell you whether someone is:

casually looking something up, or

mid-task fixing a problem (the moment where handover + nudges are genuinely helpful)

Active situation state lets Celeste surface scaffolding (like Add to Handover, Track this, Draft reorder) only when it’s contextually justified, so the UI stays calm and trust stays high.

What it tracks

Each situation is tied to a SituationKey:

yacht + user context

a primary entity (equipment / part / work order / fault / location / person)

optional symptom tag (e.g., overheating, vibration)

It stores:

current state (IDLE → CANDIDATE → ACTIVE → COOLDOWN → optional RESOLVED)

evidence flags (manual opened, history viewed, mutation committed, repeated queries)

nudge suppression (if user ignored/dismissed, don’t nag)

Where it integrates

Active situation sits between ranking and microactions, as a policy layer:

Query → entity extraction → ranking → (active situation update) → microaction attachment → response

It does not change retrieval or ranking.
It only controls when scaffolding appears and which suggestions are allowed.

When it activates

A situation becomes ACTIVE only after commitment signals, such as:

the user opens a manual section

the user views maintenance history

the user prepares/commits a mutation

the user repeats the same entity-focused query in a short window

Typing a query alone usually creates a CANDIDATE, not ACTIVE.

How it changes what users see

Active situation state governs two things:

1) Nudges (active scaffolding)

When ACTIVE, Celeste may surface one optional nudge at a time, e.g.:

“Add to handover”

“Create reorder draft”

“Notify engineer”

If not ACTIVE, these nudges stay hidden.

2) Passive indicators (always safe)

Regardless of state, Celeste can always show passive cues inside views, e.g.:

underline 0 quantity

“Low stock” tag

“Recurring” marker

These never prompt a decision.

Guardrails (non-negotiable)

No ML: only explicit events and deterministic rules.

One new decision at a time: never spam multiple nudges.

Dismissal memory: if user dismisses a nudge, suppress it for that situation.

Draft-first: proactive suggestions resolve to drafts, not execution.

No silent actions: mutations still require signature + audit as usual.

Practical example

User types: “engine overheating again”
→ CANDIDATE (entity + symptom)

User opens the relevant manual section
→ ACTIVE

Now Celeste is allowed to surface a single nudge:

“Add to handover”

If user dismisses it
→ suppress for this situation unless something materially changes (new mutation, new fault, etc.)