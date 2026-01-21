# 22_ANCHOR_TYPES.md

Anchor types define the artefact categories that can initiate and replace the active anchor within a situation.

Each anchor type represents a distinct UX, action surface, and related-expansion behavior, while sharing the same situational continuity framework.

## Supported Anchor Types

The following artefact types are valid anchors in MVP:

* manual_section
* document
* inventory_item
* work_order
* fault
* shopping_item
* shopping_list
* email_message
* certificate

## Anchor Responsibilities

For each anchor type:

* Opening the artefact from search creates a situation.
* Opening the artefact from Related replaces the active anchor.
* The artefact's UX defines:

  * Visible actions
  * Available mutations
  * Domain-specific controls
* Related expansion behavior is governed by shared contracts, not per-anchor UI logic.

## Anchor Replacement Rules

* Only one anchor may exist at any time.
* Opening a new artefact within a situation replaces the active anchor.
* Anchor replacement does not create a new situation.
* Anchor replacement pushes a new view state onto the stack.

## Domain-Specific UX

Each anchor type may present a different viewer layout, including but not limited to:

* Documents and manuals: read-oriented viewers
* Inventory items: stock state, location, supplier actions
* Work orders and faults: status, notes, and mutation actions
* Shopping items and lists: quantity and approval actions
* Emails: read-only message context
* Certificates: compliance metadata and validity

These differences do not alter navigation or situation behavior.

## Database Assumptions

Anchor artefacts are stored in domain-specific tables.

Each table must expose:

* id (uuid primary key)
* tenant_id (uuid)
* department_id (uuid, nullable)
* created_at (timestamptz)
* updated_at (timestamptz)

All anchor artefacts must be permission-checked prior to opening or inclusion in Related.

## Prohibited Behavior

* Composite anchors.
* Multiple simultaneous anchors.
* Anchor-specific navigation stacks.
* Anchor-specific situation lifecycles.

## Success Conditions

* Any supported artefact can initiate or replace a situation anchor.
* UX varies by anchor without breaking situational continuity.

## Failure Conditions

* Anchor opening creates unexpected navigation paths.
* Anchor replacement resets context.
* Anchor-specific logic bypasses shared contracts.
