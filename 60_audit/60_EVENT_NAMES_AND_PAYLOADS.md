# 60_EVENT_NAMES_AND_PAYLOADS.md

This document defines the only events that may be emitted by the Situational Continuity Layer.

Events represent explicit user actions only.

UI exploration state is not evented.

## Event Principles

* Events are binary and factual.
* Events represent completed user actions.
* Events must be attributable to a user.
* Events must be tenant-isolated.
* Events must not encode intent or inference.

## Event: artefact_opened

Emitted when a user opens an artefact viewer.

Payload:

* event_name: artefact_opened
* event_id (uuid)
* tenant_id (uuid)
* user_id (uuid)
* artefact_type (text)
* artefact_id (uuid)
* situation_id (uuid)
* occurred_at (timestamptz)

## Event: relation_added

Emitted when a user explicitly adds a related artefact.

Payload:

* event_name: relation_added
* event_id (uuid)
* tenant_id (uuid)
* user_id (uuid)
* from_artefact_type (text)
* from_artefact_id (uuid)
* to_artefact_type (text)
* to_artefact_id (uuid)
* situation_id (uuid)
* occurred_at (timestamptz)

## Event: situation_ended

Emitted when the user returns to the search bar home.

Payload:

* event_name: situation_ended
* event_id (uuid)
* tenant_id (uuid)
* user_id (uuid)
* situation_id (uuid)
* occurred_at (timestamptz)

## Explicitly Excluded Events

The following must never be emitted:

* related_opened
* related_viewed
* related_attempted
* navigation_back
* navigation_forward
* hover
* scroll
* focus

## Database Assumptions

Table: audit_events

Columns:

* id uuid primary key
* tenant_id uuid not null
* user_id uuid not null
* event_name text not null
* payload jsonb not null
* occurred_at timestamptz not null default now()

Indexes:

* (tenant_id, occurred_at)
* (tenant_id, event_name)

## Success Conditions

* Ledger reflects only explicit user actions.
* Events are defensible and explainable.

## Failure Conditions

* UI state is logged as audit truth.
* Events encode intent or confidence.
* Events are emitted implicitly.
