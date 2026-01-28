Document Situation View.md
Document Situation View
Active Context Definition & Rules
Purpose

The Document Situation View is a controlled reading environment that allows users to:

read documents without distraction

capture relevance for later (handover)

exit quickly back to global search

It is not a place to perform operations.

Documents provide context, not control.

Core Principle

When a user is reading a document, they are thinking — not acting.

All operational actions (creating work orders, adjusting inventory, adding parts, etc.) must occur outside the document view, via global search or dedicated entity views.

This preserves authority, clarity, and trust.

Navigation Model
Returning to action

Yes — this is intentional:

If a user determines that a work order, inventory action, or follow-up is required after reading a document, they must:

exit the document

return to global search

continue action from there

This reinforces Celeste’s core metaphor:

The document informs the situation; the search executes it.

Permanent UI Elements
Always visible (all document types)

Back to Search

primary escape

instant context reset

no state mutation

Cmd+F (Find in Document)

literal text search only

no entity extraction

no cross-system behavior

No other search capability exists inside document view.

Add to Handover — Visibility Rules
General rule

“Add to Handover” is a capture primitive, not an intelligence feature.

However, its visibility depends on document authority.

Allowed: Operational / Informational Documents

Examples:

OEM manuals

troubleshooting guides

internal SOPs

safety notes

maintenance references

Behavior

“Add to Handover” is visible by default

one-click capture

no triggers

no automation

Rationale:
These documents commonly represent ongoing or unresolved situations.

Restricted: Compliance / Authority Documents

Examples:

certificates

regulatory compliance documents

class approvals

inspections

licenses

Behavior

“Add to Handover” is hidden by default

available only via dropdown / overflow menu

Rationale:

compliance documents represent status, not issues

always-visible capture undermines authority

prevents perception that compliance is informal or optional

This is a trust-preserving constraint, not a limitation.

Explicitly Not Allowed in Document View

The following must never appear inside the document view:

create or edit work orders

add or adjust inventory

add parts to shopping list

notify people

send messages

initiate workflows

cross-system “smart” actions

If any of these are needed, the user must exit the document and act through search or entity views.

Relationship to Handover & Work Orders

Routine maintenance work orders are summarized automatically during handover generation.

Breakdown-specific context should come from:

explicit user handover entries

not implicit document views

This ensures:

handovers remain concise

comments remain meaningful

routine work does not pollute situational reporting

Summary Rules (Engineer Checklist)

Document view = read-only + capture

Actions happen after reading, not during

Global search is the execution surface

Cmd+F is the only search allowed in-view

“Add to Handover”:

visible for operational docs

dropdown-only for compliance docs

No operational mutations inside documents

One-line doctrine

Documents explain reality. Search changes it.