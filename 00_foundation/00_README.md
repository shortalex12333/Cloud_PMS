# 00_README.md

This folder defines the Situational Continuity Layer.

It is authoritative.

The purpose of this layer is to ensure that:

Search creates a situation

Related expands the same situation

Navigation never resets context until the user explicitly returns to search

This layer governs state, navigation, related expansion, and audit truth across all artefact types.

## Authority Order (highest to lowest)

/schemas/

/examples/

/00_foundation/

/20_model/

/30_contracts/

/40_constraints/

/60_audit/

/70_failure/

/80_validation/

If two documents conflict, the higher authority wins.

If schemas and examples conflict with narrative documents, schemas and examples win.

## Non-Negotiable Principles

Situations are not queries

Related does not perform search

Back and Forward traverse artefact history, not query history

Silence is valid when nothing is related

Explicit user actions are the only source of long-term truth

No inference, no prediction, no personalization in MVP

## Situation Lifecycle

A situation begins when an artefact is opened from search

A situation persists while the user navigates between artefacts

A situation ends when the user returns to the search bar home

Ended situations are archived for audit only and are not recoverable in UI

## Scope of This Layer

This layer applies to all artefact domains, including but not limited to:

Documents

Manuals

Inventory

Work Orders

Faults

Shopping

Email

Compliance and Certificates

Each artefact type may have a different UX and action set, but all use the same situational continuity framework.

## Explicit Non-Goals

This layer does not:

Recommend actions

Predict intent

Auto-expand related content

Persist user preferences

Perform semantic or vector search

Replace search as the primary orientation mechanism

## Build Discipline

Any implementation that:

Re-runs search during Related expansion

Loses artefact navigation state

Logs UI exploration as audit truth

Introduces ranking or inference outside defined contracts

must be considered incorrect and aborted.
