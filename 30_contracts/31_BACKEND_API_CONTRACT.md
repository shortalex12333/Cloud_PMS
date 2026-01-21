# 31_BACKEND_API_CONTRACT.md

This document defines the backend responsibilities, inputs, outputs, and invariants for Situational Continuity and Related Expansion.

Backend behavior must be deterministic, permission-safe, and audit-compatible.

## Scope

The backend is responsible for:

* Situation creation and termination
* Deterministic Related expansion
* Explicit relation persistence
* Permission enforcement
* Ledger event emission

The backend is not responsible for:

* Navigation state
* UI rendering decisions
* Ranking or inference
* State persistence beyond situation lifetime

## Endpoints

### Create or Update Situation

Triggered when an artefact is opened from search or from another artefact.

Input:

* tenant_id
* user_id
* artefact_type
* artefact_id

Behavior:

* Create a new situation if none exists
* Replace active anchor if situation exists
* Do not end existing situation unless returning to search bar home

Output:

* situation_id
* active_anchor_type
* active_anchor_id

Ledger:

* Emit artefact_opened

---

### Get Related

Input must conform to related_request.schema.json.

Backend must:

* Validate tenant_id and user_id
* Validate situation existence and ownership
* Enforce RBAC and department permissions
* Query allowed domains deterministically
* Omit empty and permission-denied domains
* Group results by domain in fixed order

Backend must not:

* Execute search queries
* Use full-text search
* Use embeddings or LLMs
* Rank or score results

Output must conform to related_response.schema.json.

Ledger:

* No events emitted

---

### Add Related

Input must conform to add_related_request.schema.json.

Backend must:

* Validate artefact existence
* Validate permissions for both artefacts
* Persist explicit relation
* Attribute relation to user and tenant

Backend must not:

* Infer inverse relations
* Delay activation
* Modify unrelated relations

Output must conform to add_related_response.schema.json.

Ledger:

* Emit relation_added

---

### End Situation

Triggered only when user returns to search bar home.

Behavior:

* Mark situation ended
* Invalidate in-memory state

Ledger:

* Emit situation_ended

## Permission Enforcement

* All artefact queries must be permission-filtered
* Permission logic must be server-side
* Permission failures must be silent in Related

## Error Handling

* Invalid inputs return explicit errors
* Empty Related is not an error
* Permission denial is not an error
* Partial domain success is not an error

## Prohibited Behavior

* Persisting navigation state
* Logging UI exploration
* Inferring relationships
* Executing background discovery jobs

## Success Conditions

* Backend outputs are deterministic
* All outputs are explainable
* Ledger is clean and defensible

## Failure Conditions

* Non-deterministic results
* Permission leakage
* Audit pollution
