Finance — Situational Active State

CelesteOS

Purpose

Finance exists to close the operational loop between:

usage → need → order → receive → install → accountability

Finance is not:

accounting software

payroll

invoice payment processing

Finance is:

purchasing intent

approval

receipt confirmation

spend accountability

audit linkage

Core Doctrine

Finance is event-driven, not form-driven

Every financial record must trace back to a real operational event

Shopping List is the primary finance surface

Nothing is “spent” until something is received or installed

Entry Conditions (How Finance Becomes Active)

Finance becomes ACTIVE only through explicit user intent:

Search → Shopping List / Purchase

Inventory event → user clicks “Add to shopping list”

Work Order completion → parts used → user opens shopping list

HOD opens Finance / Shopping List view

Finance is never auto-triggered by inference.

Finance Situations (There is only ONE)
Finance Situation = Shopping & Procurement

There is no separate:

“budget situation”

“invoice situation”

“accounting situation”

All finance flows through Shopping List → Order → Receive.

Situation States
1. IDLE

No active finance context.

2. CANDIDATE

Items have been flagged but not committed.

Sources:

Inventory low / OOS

Parts used in Work Orders

Manual add by crew

Allowed

View items

Remove items

Adjust quantities

Assign supplier

See reason why item exists

Disallowed

Approval

Spend posting

Order issuance

3. ACTIVE (Shopping List Under Review)

HOD or authorized role is actively reviewing.

Allowed

Approve / reject items

Edit quantities

Group items into an order

Assign urgency

This is the decision point.

4. COMMITTED (Order Issued)

Order has been approved and sent.

Allowed

View order

Attach documents

Prepare for receiving

Disallowed

Quantity edits

Silent cancellation

Orders are now awaiting reality.

5. PARTIALLY FULFILLED

Some items received or installed.

Order remains open

Remaining items stay pending

Finance reflects partial actuals

6. FULFILLED

All items either:

received into inventory, or

installed immediately

Finance is now actual, not projected.

Canonical Finance Entity: Shopping List
Shopping List Item must include:

Part reference

Quantity requested

Source trigger:

inventory low/OOS

work order usage

manual add

Linked Work Order (optional)

Status:

Candidate

Approved

Ordered

Received

Installed

Missing / Backordered

No free-floating items.

Habitual Journeys (Mapped Cleanly)
Crew (Mechanic / Engineer)

What they do

Use parts

Search inventory

Tap “Add to shopping list” when OOS

What they never do

Approve spend

Create orders

Handle finance details

Why this works

Zero paperwork

Zero finance burden

Natural behavior

Head of Department (HOD)

What they do

Review shopping list periodically

Approve / reject items

Group items into orders

What they see

Why each item exists

What triggered it

What will be ordered

Why this works

One list

One decision surface

No chasing crew

Logistics / Purser

What they do

Send approved orders

Attach packing slips / invoices

Coordinate receiving

Why this works

No retyping

No context loss

Everything already structured

Master / Management

What they see

Open orders

Delayed orders

Spend tied to real events

Partial vs full fulfillment

Why this works

Oversight without micromanagement

Audit-ready trail

Budget Handling (Minimal, Non-Intrusive)

Budgets are soft constraints, not blockers.

Finance shows:

Committed (ordered, not received)

Actual (received / installed)

Outstanding

If budget exceeded:

Notify HOD

Do not block workflow

No forecasting.
No spreadsheets.
No ERP logic.

Finance & Receiving Boundary (Critical)

Finance does not post spend until:

item is checked during receiving, OR

item is marked installed

Orders alone do not equal spend.

This avoids:

phantom costs

audit inconsistencies

paper-only accounting

Audit Rules (Non-Negotiable)

Every finance-relevant event logs:

Who

What

Why (source trigger)

When

Linked operational entity (WO / Inventory / Order)

No editing past events.
No overwrites.
No “corrections” without new events.

Explicit Non-Goals (Shelved by Design)

❌ Invoice payment

❌ Payroll

❌ Tax handling

❌ Multi-currency optimization

❌ Supplier analytics

❌ Spend forecasting

If it doesn’t reduce daily friction onboard, it does not ship.

Mental Model (Lock This)

Finance is not a department.
It is the shadow of real work.

If something wasn’t used, received, or installed — finance doesn’t exist yet.

What This Enables (Without Extra Work)

Shopping lists that stay accurate

HODs that aren’t chasing people

Inventory that reflects reality

Orders that don’t disappear

Audits that don’t panic crews