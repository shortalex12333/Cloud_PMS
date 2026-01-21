# 32_FRONTEND_STATE_CONTRACT.md

This document defines frontend responsibilities, state boundaries, and forbidden behaviors for Situational Continuity and Related Expansion.

Frontend behavior must be predictable, memory-bounded, and subordinate to backend truth.

## Scope

The frontend is responsible for:

* Maintaining in-memory navigation state
* Rendering viewer and related views
* Enforcing linear back/forward navigation
* Triggering backend calls using defined contracts

The frontend is not responsible for:

* Inferring relationships
* Ranking or filtering related results
* Persisting situation or navigation state
* Enforcing permissions beyond rendering received data

## State Ownership

### Situation State

* Situation identity is provided by the backend.
* Frontend treats situation_id as opaque.
* Frontend must not derive or mutate situation identity.

### Navigation Stack

* Navigation stack exists in memory only.
* Stack entries are view states.
* Maximum stack depth is bounded.
* Oldest entries are discarded silently when limit is exceeded.

Stack entry fields:

* view_state_id
* situation_id
* artefact_type
* artefact_id
* view_mode

## View Modes

Supported view modes:

* viewer
* related

Viewer:

* Displays a single artefact.
* Is the active anchor.

Related:

* Displays grouped related artefacts.
* Does not replace anchor.
* Does not trigger search.

## Navigation Rules

* Back navigates to the immediately prior view state.
* Forward navigates to the immediately next view state.
* Navigation is strictly linear.
* No branching or forked paths exist.

Returning to search bar home:

* Ends the situation.
* Clears navigation stack.
* Disables Forward navigation.

## Backend Interaction Rules

Frontend may call:

* Get Related
* Add Related
* Create or Update Situation
* End Situation

Frontend must not:

* Retry Related calls automatically.
* Broaden scope implicitly.
* Re-execute search during Related expansion.

## Rendering Rules

* Frontend renders domains in backend-provided order.
* Frontend omits empty or missing domains.
* Frontend displays user-added relations as visually neutral.

Frontend must not:

* Display relevance scores.
* Display confidence indicators.
* Display permission warnings.

## Refresh Behavior

* Browser refresh destroys all in-memory state.
* User is returned to search bar home.
* No state restoration occurs.

## Error Handling

* Backend errors are surfaced only when blocking.
* Empty Related is rendered silently.
* Permission denial is rendered as absence.

## Prohibited Behavior

* Persisting navigation state to storage.
* Reconstructing state after refresh.
* Introducing UI shortcuts to bypass stack rules.
* Adding dashboards, tabs, or feeds.

## Success Conditions

* Frontend behavior mirrors documented examples exactly.
* Navigation feels safe and reversible.
* No hidden state influences behavior.

## Failure Conditions

* Context loss during navigation.
* Implicit re-searching.
* State persistence beyond situation lifetime.
