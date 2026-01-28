Shopping List — Situational Active State

CelesteOS

Purpose

The Shopping List exists to capture procurement intent and convert it into real orders, driven by actual operational signals.

It answers one question only:

“What do we need to buy, and why?”

The Shopping List is additive, auditable, and role-governed.

Core Doctrine

Capture everywhere. Decide centrally.

Shopping List items are created from reality, not speculation.

Nothing is ordered until a human approves it.

Shopping List is the only gateway to procurement.

What Shopping List Is (and Is Not)

Is

A first-class procurement queue

Fed by Inventory, Work Orders, Receiving

Reviewed and approved by HOD

Tracked through order → receipt → install

Is Not

A wishlist

A replacement for inventory

An accounting ledger

A search-only feature

Entry Conditions (Additive Capture Points)

Shopping List items may be created only via explicit user actions:

Inventory

Add to shopping list from part detail or list

Common when low / OOS

Work Order

During completion: parts used → add missing items

Receiving

Missing / damaged / incorrect items → add back to shopping list

Shopping List screen

+ Add item (manual capture)

Shopping List items are never auto-created.

Item Types

Each Shopping List item is one of:

Known Part (linked to inventory part)

Candidate Part (new / unverified part)

Candidate Parts:

are allowed

are clearly labeled

cannot be ordered until reviewed by HOD

must be promoted explicitly to real inventory parts later

This prevents inventory pollution.

Situation States (Item-Level)

Each Shopping List item has exactly one state:

CANDIDATE
ACTIVE (UNDER_REVIEW)
COMMITTED (ORDERED)
PARTIALLY_FULFILLED
FULFILLED
INSTALLED
MISSING


No free-text states. No silent transitions.

State Definitions & Allowed Actions
1. CANDIDATE

Item captured but not reviewed.

Who

Crew, System (from events)

Allowed

View

Edit quantity

Assign optional supplier

Remove

Add note

Disallowed

Order

Spend posting

2. ACTIVE (UNDER_REVIEW)

HOD is reviewing.

Who

HOD / authorized role

Allowed

Approve

Reject

Edit quantity

Group with other items

Assign supplier / urgency

Disallowed

Receiving

Installation

3. COMMITTED (ORDERED)

Item approved and ordered.

Who

HOD / Logistics

Allowed

View order details

Attach documents

Prepare for receiving

Disallowed

Quantity edits

Removal without explicit cancellation

Order does not equal spend.

4. PARTIALLY_FULFILLED

Some quantity received or installed.

Who

Logistics / Receiving

Allowed

Receive remaining

Mark missing

View fulfillment status

5. FULFILLED

All quantities received into inventory.

Who

System

Allowed

View only

Audit export

6. INSTALLED

Item installed immediately (skipped inventory).

Who

Receiving / HOD

Allowed

View linked Work Order

View audit trail

7. MISSING

Item not received or defective.

Who

Receiving / HOD

Allowed

Re-add to shopping list

Cancel

Attach notes/photos

Canonical UI Surfaces
A. Additive Capture (Micro-UI)

Small, fast sheets only:

Qty

Optional supplier

Optional note

Submit

No approvals here.

B. Shopping List Home (Management Surface)

Default View

Tabs / filters:

Candidate

Under Review

Ordered

Awaiting Receipt

History

Row shows

Item name

Qty

Source (“WO #123”, “Inventory low”)

State badge

Age (e.g. “Ordered 12 days ago”)

No inline actions.

C. Item Detail Drawer

Sections (fixed order):

Item summary

Why this exists (immutable)

Quantity & supplier

Linked entities (WO / Inventory)

Audit trail

State-dependent actions (bottom)

Approval & Ordering Flow

HOD selects one or more ACTIVE items

Reviews summary

Confirms approval

Items move to COMMITTED

Order reference created

No silent grouping.
No background ordering.

Finance Boundary Rules

Shopping List = intent

Order issued = commitment

Receiving / install = actual spend

Finance is posted only on:

inventory receive events

install events

Never on approval alone.

Search Behavior (Reinforced)

Search shows Shopping List items as previews only

Clicking opens Item Detail or Shopping List Home

No actions from search

No auto-approval

Audit Rules

Every state transition logs:

user

timestamp

previous state → new state

reason/source

linked entities

Edits create new events.
Nothing is overwritten.

Explicit Non-Goals

❌ Auto-ordering

❌ Budget enforcement

❌ Supplier optimization

❌ Forecasting

❌ Inventory creation without review

Mental Model (Lock This)

Shopping List is where needs wait for permission.
If it’s not on the list, it’s not getting ordered.
If it’s not approved, it’s not real.