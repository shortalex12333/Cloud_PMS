# 80_DONE_DEFINITION.md

Implementation is considered complete only when all conditions in this document are satisfied.

Failure to meet any condition constitutes an incomplete build.

## Functional Completeness

* Opening any supported artefact from search creates a situation.
* Repeated artefact navigation remains within the same situation.
* Back navigates through prior artefact views in strict order.
* Forward navigates through previously visited artefact views.
* Returning to the search bar home terminates the situation.

## Related Expansion

* Show Related opens a Related view without executing a search.
* Related results are grouped by domain in fixed order.
* Related results are deterministic for a given situation.
* Empty Related states render silently.
* Add Related creates an explicit, attributable relation.

## State Management

* Navigation state is in-memory only.
* State is destroyed on browser refresh.
* State is destroyed when returning to search bar home.
* No state persists across situations.

## Audit and Ledger

* Artefact opens are recorded as ledger events.
* Relation additions are recorded as ledger events.
* Situation termination is recorded as a ledger event.
* UI exploration is not recorded.

## Security and Permissions

* All artefacts displayed are permission-checked.
* Permission-denied artefacts never appear.
* Cross-tenant access is impossible.

## Performance

* No vector search or LLMs are invoked.
* Related expansion is deterministic and bounded.
* No background discovery processes run.

## Prohibited Outcomes

* Context loss during navigation.
* Re-querying during Related expansion.
* Implicit inference or recommendation.

## Completion Assertion

The system must behave predictably under normal and edge conditions.

If any rule in this document is violated, the implementation is not complete.
