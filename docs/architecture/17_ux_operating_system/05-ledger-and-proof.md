# CelesteOS — Ledger: Location, Structure, and Interaction

## Why This Document Exists

The ledger is not an abstract concept.
It is a **concrete UX surface**.

If users do not immediately understand:
- where the ledger is
- how to read it
- how it relates to search

Then Celeste creates anxiety instead of trust.

This document defines the ledger **as a place**, not just a principle.

---

## What the Ledger Is (Plainly)

The ledger is the **system memory of actions taken**.

It answers one question only:

> “What has actually happened?”

Not:
- what should happen
- what is planned
- what is expected

Only what occurred.

---

## Where the Ledger Lives

The ledger is:

- a **secondary surface**
- directly adjacent to search
- never the default landing view
- never visually dominant

The ledger is accessed via a **single, persistent icon beneath the search bar**.

Search remains the primary interface.
The ledger exists to support recall, proof, and orientation after action.

---

## Relationship to Search (Critical)

The ledger is **not a different UX language**.

It must:
- look like search results
- read like search results
- behave like search results

The only difference:
- search shows *potential*
- the ledger shows *facts*

If a user understands search, they already understand the ledger.

---

## Visual Structure (Non-Negotiable)

The ledger is presented as a **list**, not a table.

Structure is strictly:

1. **Search bar** (always present, same as global search)
2. **Optional filters** (ephemeral)
3. **Chronological list grouped by day**

No columns.
No grids.
No dashboards.

---

## Anchoring and Orientation

Each day forms a **hard anchor**.

Example:

Wed 14 Jan ’25 — 7🟢 4🟠 6⭕  

- 🟢 = mutation events (Closed, Updated, Added, Removed, Signed)
- 🟠 = read events (Viewed, Opened)
- ⭕ = neutral context events (Searched, Navigated)

Anchors exist to restore orientation, not to score performance.

Anchors must:
- remain visible while scrolling
- release only when the next date anchor replaces them

---

## Grouping Rules (Within a Day)

Within each day, entries are grouped:

1. **By domain** (Documents, Inventory, Work Orders, etc.)
2. **By verb type** within each domain
3. **Chronologically within each subgroup**

Example:

Documents  
  Generator Manual — Viewed  

Inventory  
  Exhaust Fan — Updated  

This grouping reduces noise without hiding truth.

---

## Event Grammar (Visible at Row Level)

Each row must read as a sentence fragment:

**Object — Verb**

Examples:
- Generator Manual — Viewed
- Exhaust Fan — Updated
- Work Order #4821 — Closed

No adjectives.
No interpretation.
No status labels.

The verb carries meaning.

---

## Read vs Mutate Hierarchy

Mutation events are heavier than read events.

This is expressed through:
- inclusion in anchor counts
- subtle visual weight
- ordering within domain groups

Not through:
- bright colors
- alerts
- emphasis that suggests judgment

Reads are **collapsed by default**, not hidden.

Users may expand reads deliberately.

---

## Filtering Behavior

Filters exist to reduce cognitive load, not to create states.

Rules:
- filters are optional
- filters are ephemeral
- filters reset on exit
- no saved filter states

Allowed filters (max three at any time):
- Show mutations
- Show unresolved
- Filter by user (role-dependent)

Filters must never change the underlying truth — only the view.

---

## Search Inside the Ledger

The ledger has its own search input, identical to global search.

Users can type:
- “what did I update”
- “inventory today”
- “work orders I closed”

Search results must preserve:
- ledger grammar
- attribution
- anchors

Searching the ledger is not different from searching Celeste — only the scope changes.

---

## Role-Based Scope

By default:
- users see their own ledger

Higher roles may:
- expand scope to department
- filter by crew member
- inspect mutation events only

At no point does the ledger:
- infer performance
- rank users
- suggest sufficiency

Visibility changes.
Facts do not.

---

## What the Ledger Never Shows

The ledger must never show:
- KPIs
- progress bars
- completion percentages
- overdue indicators
- judgments
- recommendations

The ledger records reality.
It does not manage it.

---

## Success Criteria

The ledger is correct if:
- a user can reconstruct their day after interruption
- a captain can verify without interrogating
- an audit requires no explanation
- users trust that nothing is lost
- the surface feels calm, factual, and quiet

---

## Final Lock

> **Search is how work happens.  
> The ledger is how work is remembered.**

This document is canonical.
