# 20_SITUATION_OBJECT.md

A situation represents a continuous operational context created by opening an artefact from search.

A situation is not a query, not a session, and not a workflow.

## Situation Definition

A situation consists of:

* situation_id (uuid)
* tenant_id (uuid)
* created_by_user_id (uuid)
* created_at (timestamp)
* ended_at (timestamp, nullable)
* active_anchor_type (enum)
* active_anchor_id (uuid)
* extracted_entities (jsonb)
* temporal_bias (enum: now, recent, historical)

## Situation Lifecycle

* A situation is created when a user opens an artefact from the search bar home.
* The first opened artefact becomes the initial anchor.
* The situation persists as long as the user navigates between artefacts.
* Replacing the anchor does not create a new situation.
* A situation ends when the user returns to the search bar home.
* Ended situations are archived for audit only.

## Database Assumptions

Table: situations

Columns:

* id uuid primary key
* tenant_id uuid not null
* created_by_user_id uuid not null
* created_at timestamptz not null default now()
* ended_at timestamptz null
* active_anchor_type text not null
* active_anchor_id uuid not null
* extracted_entities jsonb not null
* temporal_bias text not null

Indexes:

* (tenant_id, created_at)
* (tenant_id, ended_at)

## Extracted Entities

Extracted entities are reused across:

* Related expansion
* Action gating
* Domain filtering

Extracted entities must be deterministic and reproducible.

## Temporal Bias

Temporal bias is used only for ordering within domains.
Temporal bias must not influence cross-domain grouping.

Allowed values:

* now
* recent
* historical

## Prohibited Behavior

* Situations must not be merged.
* Situations must not be resumed after termination.
* Situations must not be modified by background processes.
* Situations must not persist UI-only state.

## Success Conditions

* Users can navigate between artefacts without losing context.
* Situations remain isolated and auditable.
* Situation state is predictable and explainable.

## Failure Conditions

* Context resets unexpectedly.
* Artefact navigation creates multiple situations.
* Situation persists after return to search bar home.
