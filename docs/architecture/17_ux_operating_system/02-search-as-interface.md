# CelesteOS — Search as the Interface

## Why This Document Exists

This document exists to protect CelesteOS from reverting into navigation.

Search is not a feature.
Search is not a convenience.
Search is the **primary interface contract** between the human and the system.

If search is weakened, everything else collapses into legacy behavior.

---

## The Core Assertion

> **Search is how users express intent.**

Users do not “go to” Celeste.
They do not “open” modules.
They do not “navigate” pages.

They ask.

This mirrors how humans operate under pressure:
- they verbalise
- they clarify
- they probe
- they act

Celeste must behave accordingly.

---

## What Search Replaces

Search replaces:
- menus
- modules
- dashboards
- navigation trees
- workflows

Any feature that requires a user to remember *where* something lives is a regression.

---

## Search Is Not Retrieval Only

Search is not just “find me X”.

Search is allowed to:
- orient the user
- surface context
- show state
- propose actions
- reveal uncertainty

Search is not allowed to:
- auto-execute
- guess silently
- collapse ambiguity
- act without consent

---

## Determinism Under Pressure

Search results must behave deterministically **for committed actions**.

Rules:
- mutations must always be retrievable
- proof must not depend on ranking volatility
- past actions must not “disappear” due to relevance scoring

Reads may be ranked.
Writes must be anchored.

If a user cannot reliably retrieve a past action by searching, trust is broken.

---

## Search Grammar (Non-Negotiable)

Search must accept:
- natural language
- fragments
- uncertainty
- partial memory

Examples:
- “generator alarm again”
- “what did I change today”
- “where did we order this last time”
- “add this to handover”

Search must never require:
- exact phrasing
- system vocabulary
- knowledge of schema
- training manuals

If users have to learn how to ask, Celeste has failed.

---

## Search as Memory Replacement

Celeste must assume:
- users forget
- users are interrupted
- users leave mid-task
- users return hours or days later

Search must allow users to reconstruct:
- what they were doing
- what they touched
- what changed
- what remains unresolved

This is not convenience.
This is operational safety.

---

## Relationship to Other Surfaces

Other UI surfaces may exist (ledger, handover, settings), but:

- they are secondary
- they do not compete with search
- they never become primary entry points

If a user can complete their day without touching search, the design is wrong.

---

## Failure Modes (Automatic Rejection)

Any proposal that:
- introduces a default landing page other than search
- adds persistent navigation for daily work
- trains users to click instead of ask
- encourages browsing over intent
- optimises for scanning instead of querying

…must be rejected.

---

## Success Criteria

Search is correct if:
- users describe Celeste by what they ask, not where they click
- new users instinctively type, not look around
- experienced users rely on search even when shortcuts exist
- search becomes reflexive under pressure

---
## Search Transparency — Exposed Understanding (Non-Negotiable)

### Why This Exists

Search without visible understanding is a black box.

If users cannot see what Celeste understood:
- trust degrades
- misinterpretations go unnoticed
- users blame the system instead of correcting it
- accountability becomes ambiguous

Celeste must never appear “smart but opaque”.

---

## The Core Rule

> **Before results appear, Celeste must show what it understood.**

This is not an explanation.
This is not a justification.
This is a **preview of interpretation**.

---

## What Is Shown (Explicitly)

Directly beneath the search bar, Celeste must render a compact **Understanding Strip** that shows:

- extracted entities
- inferred intent (if applicable)
- uncertainty (if present)

This appears **before results load**, and remains visible as results stream in.

---

## Entity Display Format

Entities are shown as neutral, pill-style tokens.

Example:
```

[Generator] [High Level Alarm] [System: Cooling]

```

Rules:
- tokens are factual
- no confidence scores shown to users
- no hidden weighting
- no implied correctness

---

## Uncertainty Handling (Mandatory)

If multiple interpretations exist, Celeste must show them explicitly.

Example:
```

[Inventory: Exhaust Fan]
[Manual: Exhaust Fan]

```

Or:
```

Did you mean:
• Generator alarm history
• Generator cooling manual

```

Celeste does not guess.
Celeste presents options.

---

## User Correction Loop

Each entity must be:
- clickable
- removable
- replaceable

If a user removes or corrects an entity:
- the query is re-interpreted
- results update immediately
- the system learns nothing implicitly

Learning occurs **only from explicit confirmation**, never correction alone.

---

## What This Achieves

This design:
- externalises model reasoning
- lets users debug misunderstandings
- reduces false confidence
- builds trust through visibility

Users understand:
> “This is what Celeste thinks I meant.”

If that’s wrong, they can fix it **before damage occurs**.

---

## Backend Streaming Requirements

The backend must stream search in **three phases**:

### Phase 1 — Interpretation
- entity extraction
- intent detection
- uncertainty resolution
- streamed immediately

### Phase 2 — Acknowledgement
- UI renders understanding strip
- user can correct before results dominate

### Phase 3 — Results & Microactions
- cards
- evidence
- proposed actions

Results must never arrive before interpretation is visible.

---

## Backend Contract (Abstract)

The API must return, in order:

1. `interpreted_entities[]`
2. `interpreted_intent`
3. `confidence_branches[]` (if any)
4. `results[]`
5. `microactions[]`

This is a **streaming contract**, not a batch response.

---

## Frontend Guardrails

The frontend must:
- block result rendering until interpretation is visible
- animate interpretation appearance calmly
- never hide interpretation after render
- never auto-collapse uncertainty

No spinners.
No loading screens.
Interpretation is the first response.

---

## Error States (Explicit, Calm)

### No interpretation possible
Show:
```

I couldn’t confidently interpret that.
Try being more specific.

```

### Conflicting entities
Show:
```

Multiple interpretations found.
Choose one to continue.

```

### Partial understanding
Show:
```

This is what I understood so far.

```

Celeste never blames the user.
Celeste never claims certainty it does not have.

---

## Success Criteria

This feature is correct when:
- users notice misunderstandings early
- users trust corrections will propagate
- results feel earned, not magical
- black-box perception disappears

---

## Failure Modes (Automatic Rejection)

Any implementation that:
- hides interpretation
- delays interpretation until after results
- auto-selects an interpretation silently
- collapses uncertainty for speed
- learns implicitly from corrections

…must be rejected.

---

## Final Lock

> **Celeste shows its thinking before it shows its answers.**

This is not optional.
This is the trust boundary.

```

---

### Why this matters (short, brutal)

This single subsection:

* protects you legally
* protects you cognitively
* protects you from “AI hallucination” accusations
* makes your system explainable without explanations

It also gives your backend team a **clear streaming contract**, not vibes.
--------

## Final Lock

> **If Celeste ever needs a tutorial to explain where things are, it has already failed.**

Search is the interface.
Everything else is support.

This document is canonical.
