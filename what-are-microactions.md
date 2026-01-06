1. What microactions are (in simple terms)

Microactions are small, explicit things a user may choose to do, surfaced by Celeste after it understands a situation.

They are not commands.
They are not automation.
They are not shortcuts.

They are options.

Celeste never acts on its own.
Celeste only proposes.
The user always decides.

2. Why microactions exist at all

Celeste is not a filing cabinet.
It is not a database UI.
It is not a chatbot that “does things”.

Celeste’s job is orientation:

What is happening

Where the user is

What exists

What matters next

Microactions exist to answer the final, natural question a human always asks once oriented:

“Okay — what can I do now?”

That’s it.

3. Two kinds of microactions (this split is foundational)

All microactions fall into one of two groups.
There is no overlap.

Group A — Read / Observe actions

Zero risk. Zero ceremony.

Examples:

View

Open

Print

Share

Compare

Navigate to manual section

Show history

These actions:

Do not change system state

Do not require confirmation

Do not require signatures

Do not create fear

They execute immediately and inline.

If a user clicks “View”, Celeste views.
No friction. No explanation required.

Group B — Mutate / Commit actions

Anything that changes reality.

Examples:

Edit inventory

Add note

Remove item

Sign hours of rest

Submit record

Order part

Close work order

These actions:

Always change state

Always require visibility

Always require explicit user consent

Always produce an audit trail

There is no exception.

If an action mutates data, Celeste slows down just enough to protect trust.

4. What microactions deliberately do NOT include

Microactions do not include:

Explanations of intent (“Why this action exists”)

Hidden logic

Automated execution

Background behavior

Surprise side effects

If a user needs a lecture to trust an action, the system has already failed.

Instead, trust comes from clarity of impact.

5. How microactions appear in the interface

Microactions are always adjacent to the thing they act on.

They never:

Open new tabs

Redirect to dashboards

Break the user’s mental context

The interface changes beneath the search bar.

Primary actions

One obvious, safe action may be visible directly (usually READ)

Example: “View”, “Print”

Dropdown fallback (the “Contact Us” pattern)

A small ▼ arrow reveals additional verbs

Users will often ignore it — that is expected and acceptable

The dropdown exists for safety and completeness, not discovery

This prevents clutter while ensuring nothing dangerous is forced upfront.

6. What happens when a user triggers an action
For READ actions

User clicks

Celeste immediately begins

A status line appears:

“Loading inventory box 2D…”

“Finding manual section…”

The interface updates inline

No confirmation.
No modal.
No delay.

For MUTATE actions

Mutation follows a visible, linear ritual:

Stage

The user selects a change

Celeste prepares it but does not commit

Preview

Celeste shows exactly what will change

No justification, no explanation

Just the delta

Sign

User explicitly signs (Face ID, passcode, etc.)

This is the point of consent

Commit

Change is written

Action is logged

UI updates inline

Record

Who changed what, when, where, and how

Append-only, immutable

At every step:

Cancel is visible

Exit is safe

Nothing is hidden

7. Why there is no “Why” button

We intentionally removed “Why” explanations.

Reasons:

They add low-value text

They become templated and ignored

They feel defensive or patronising

They don’t prevent real mistakes

Instead, Celeste shows:

What it understood (entities under the search bar)

What will change (diff preview for mutations)

What is happening now (real-time status line)

This is higher-fidelity trust than prose explanations.

8. How uncertainty is handled

Celeste never collapses uncertainty.

If there are multiple plausible interpretations:

Celeste orders them by confidence

Presents them visibly

Lets the user choose

Example:

“Inventory box 2D”

“Deck locker 2D”

No guessing.
No assumptions.
No silent decisions.

Uncertainty is not hidden — it is structured.

9. How microactions work across mobile and desktop

The model is universal.

Mobile (crew):

Clean vertical flow

Row tap opens detail

Actions live inside the context

Desktop (officers):

More density

Primary action inline

Dropdown still available

Same logic.
Same trust model.
Different screen real estate.

10. Security, signing, and audit (why this matters)

Every mutation:

Is signed

Is logged

Is attributable

Is reviewable

There is no “silent success”.

This matters because:

Yachting is regulated

Responsibility is shared

Mistakes are expensive

Trust is everything

Celeste is designed to be calm because it is accountable.

11. What microactions are building toward (future-proofing)

This foundation allows Celeste to later:

Learn patterns without removing consent

Suggest flows without automating them

Support more domains without UI changes

Scale from yachts → fleets → cities

Because:

Actions are explicit

Execution is visible

Control never moves away from the human

12. The hard line (non-negotiable)

If a proposed change:

Auto-executes actions

Hides state changes

Removes signatures

Collapses uncertainty

Introduces dashboards

Turns Celeste into a control panel

Then it is not an improvement.

It is a regression back to a filing cabinet.

Final summary

Microactions are not about speed.
They are about clarity, safety, and trust.
