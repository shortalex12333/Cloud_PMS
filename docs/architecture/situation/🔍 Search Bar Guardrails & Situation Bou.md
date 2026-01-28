🔍 Search Bar Guardrails & Situation Boundary

CelesteOS — Search Policy Specification

Purpose

The global search bar exists to answer one question only:

“What might be relevant?”

It is not:

an execution surface

a decision surface

an action trigger

a workflow starter

Search provides orientation, not commitment.

Core Doctrine

Search is passive.
Click is commitment.

No situation state may become ACTIVE from search alone.

Trust depends on this boundary.

Search Scope (What Search Is Allowed to Do)

Search may:

retrieve and rank entities across domains

group results by domain

show brief previews

show passive indicators (status, warnings, badges)

offer navigation shortcuts (filters, “show all”)

Search may not:

mutate state

create drafts

trigger workflows

prompt decisions

request signatures

open modals that change reality

Search Output Structure

Search results are always structured:

[Quick Filters]
[Domain Group: Work Orders]
  - One-line previews (max N)
[Domain Group: Inventory]
  - One-line previews
[Domain Group: Documents]
  - One-line previews
[Domain Group: People / HOR]
  - One-line previews


No domain may render a full table inside search.

Quick Filters (Allowed)

Quick filters are navigation controls, not actions.

Examples:

Overdue

Due Today

Breakdowns

Out of Stock

Low Confidence

Rules:

Clicking a filter opens the corresponding list view

Filters do not change data

Filters do not create situations

Result Preview Rules (Non-Negotiable)

Each result preview:

occupies one row

shows only:

title / name

status badge (passive)

critical indicator (e.g., overdue, out of stock)

never shows action buttons

never shows editable fields

Examples of allowed indicators:

“Overdue”

“Out of Stock”

“Blocked”

“Low Confidence”

These are facts, not prompts.

What Search Must NEVER Do

Search must never:

open a Work Order detail automatically

open Inventory part detail automatically

suggest “Mark as done”

suggest “Deduct 1 unit”

suggest “Sign hours”

create a draft purchase request

infer user intent as action

Even if confidence is 100%.

Click Boundary (Situation Creation)

A situation may be created only when:

a user clicks a result

a user opens a list view

a user explicitly selects an entity

This is the first moment commitment is allowed.

Situation Creation Rules

Upon click:

active situation is created as CANDIDATE

no actions appear immediately

user must first see the context

Only after further explicit interaction may the situation move to ACTIVE.

Passive Intelligence Allowed in Search

Search may surface passive intelligence, such as:

confidence scores

trend badges

“frequently used”

“recently updated”

But these must be:

non-clickable

non-actionable

non-instructional

Search informs. It never nudges.

Confidence Thresholds (Important Clarification)

Confidence thresholds may:

affect ranking

affect grouping

affect badge visibility

Confidence thresholds must never:

auto-open entities

auto-create situations

auto-suggest actions

Hallucination risk is unacceptable here.

Action Attachment Rules

Actions are attached only after:

entity view is opened

situation state allows it

user role permits it

Search results have zero actions.

Back-End Enforcement (Critical)

The backend must enforce:

no state mutation from search endpoints

no action registry access from search responses

no draft creation from search

If frontend tries to cheat, backend must refuse.

This boundary is not optional.

Front-End Enforcement (Critical)

The frontend must enforce:

no buttons in search results

no inline expand-to-edit behavior

no modal actions from search

Search must feel calm, inert, and trustworthy.

Failure Modes to Guard Against

“Helpful” product creep

Designers adding quick actions

Engineers shortcutting via search endpoints

Auto-opening “most likely” items

All of these break trust.

One-Line Doctrine

Search shows possibilities.
Only clicks create reality.

What This Unlocks

Because this boundary is strict:

Situation logic stays deterministic

Audit trails stay clean

Users never feel tricked

Adoption increases under stress

Inspectors trust the system