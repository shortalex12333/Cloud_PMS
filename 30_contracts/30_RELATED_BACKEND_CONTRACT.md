# 30_RELATED_BACKEND_CONTRACT.md

This document defines the authoritative backend contract for Related expansion.

The backend is responsible for deterministic filtering, grouping, and ordering only.

No inference, ranking, or interpretation is permitted.

## Request Contract

Endpoint: `POST /related`

Required input payload:

* situation_id (uuid)
* anchor_type (text)
* anchor_id (uuid)
* tenant_id (uuid)
* user_id (uuid)
* allowed_domains (array of text)

Forbidden input fields:

* free_text
* query
* embedding
* confidence
* ranking_hint

## Request Validation Rules

* situation_id must exist and be active.
* anchor_type and anchor_id must match the active anchor.
* user_id must have access to the anchor artefact.
* allowed_domains must be non-empty.
* Requests failing validation return an empty response.

## Response Contract

The backend returns grouped related artefacts.

Response payload:

* situation_id (uuid)
* anchor_type (text)
* anchor_id (uuid)
* groups (array)

Each group contains:

* domain (text)
* items (array of standard artefact cards)

Each artefact card contains:

* artefact_type (text)
* artefact_id (uuid)
* title (text)
* subtitle (text, nullable)
* metadata (jsonb, nullable)

Ordering rules:

* Groups are returned in fixed domain order.
* Items within groups may be ordered by temporal bias only.

## Domain Grouping

Domains are not merged.

Each domain group is returned independently.

If no items exist for a domain, the domain group is omitted.

If no domain groups exist, an empty response is returned.

## Database Assumptions

Related expansion relies on:

* extracted_entities stored on the situation
* explicit relation tables
* deterministic foreign key joins

No full-text search or embeddings are used.

Example relation tables:

* artefact_entity_links
* user_added_relations

## Permission Enforcement

* Permission checks occur before inclusion in groups.
* Artefacts the user cannot access are omitted.
* Domains with no permitted artefacts are omitted.

## Prohibited Behavior

* Cross-tenant joins.
* Cross-department visibility without authorization.
* Backend ranking beyond temporal bias.
* Backend inference or prediction.

## Success Conditions

* Related results are deterministic.
* Backend latency remains predictable.
* No user-visible errors occur for empty results.

## Failure Conditions

* Backend performs semantic matching.
* Backend returns artefacts outside allowed domains.
* Backend returns artefacts without permission checks.
