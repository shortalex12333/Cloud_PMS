# 34_ADD_RELATED_RULES.md

Add Related allows users to explicitly define relationships between artefacts.

All added relations are intentional, attributable, and auditable.

## Scope and Visibility

* Added relations are global within a single tenant database.
* Visibility is restricted by department-level permissions.
* Users only see added relations they are authorized to access.

## Activation Behavior

* Added relations are active immediately.
* No review or approval step exists in MVP.
* Added relations are permanently flagged as user-added.

## Provenance

Every added relation must record:

* relation_id (uuid)
* tenant_id (uuid)
* created_by_user_id (uuid)
* created_at (timestamptz)
* source (enum: user)
* from_artefact_type (text)
* from_artefact_id (uuid)
* to_artefact_type (text)
* to_artefact_id (uuid)

## Database Assumptions

Table: user_added_relations

Columns:

* id uuid primary key
* tenant_id uuid not null
* created_by_user_id uuid not null
* created_at timestamptz not null default now()
* source text not null
* from_artefact_type text not null
* from_artefact_id uuid not null
* to_artefact_type text not null
* to_artefact_id uuid not null

Indexes:

* (tenant_id, from_artefact_type, from_artefact_id)
* (tenant_id, to_artefact_type, to_artefact_id)

## Relation Semantics

* Relations are directional.
* Bidirectional behavior must be explicit.
* Relations do not imply hierarchy or causality.

## Inclusion in Related

* User-added relations are always eligible for inclusion.
* Inclusion is subject to permission checks.
* Inclusion does not override deterministic relations.

## Audit Behavior

* Adding a relation is an auditable event.
* Viewing a relation is not auditable.

## Prohibited Behavior

* Automatic relation creation.
* Inferred relation creation.
* Silent overwriting of relations.
* Cross-tenant relations.

## Success Conditions

* Users can link artefacts deliberately.
* Relations are immediately useful.
* Provenance is preserved.

## Failure Conditions

* Relations appear without attribution.
* Relations bypass permission checks.
* Relations modify ordering or grouping logic.
