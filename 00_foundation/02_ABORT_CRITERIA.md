# 02_ABORT_CRITERIA.md

The following conditions require immediate abort of implementation.

If any condition below is true, the build must stop and be corrected before proceeding.

## Context Violations

* Related expansion triggers a new search query.
* Related expansion performs free-text matching.
* Navigation returns to search results instead of artefact history.
* Artefact navigation resets extracted entities implicitly.
* Situation persists after returning to search bar home.

## State Violations

* More than one anchor exists simultaneously.
* Anchor replacement creates a new situation.
* Viewer state is recoverable after situation termination.
* Situation state survives browser refresh.
* Situation state is promoted to user preference.

## Navigation Violations

* Back navigation skips artefact views.
* Forward navigation executes new queries.
* Breadcrumbs reference query state.
* Multiple navigation stacks exist concurrently.
* Navigation branches instead of remaining linear.

## Related Expansion Violations

* Related performs ranking logic on the frontend.
* Related performs inference beyond entity filtering.
* Related performs semantic similarity.
* Related merges or flattens domains.
* Related displays recommendation or suggestion language.

## Audit Violations

* "Related opened" is written to the ledger.
* UI exploration is logged as audit truth.
* Artefact open events are recorded with confidence or probability.
* User-added relations are not attributed to a user identifier.

## Permission Violations

* Related displays items the user lacks permission to access.
* Permission checks are deferred until item click.
* Related expansion bypasses RBAC or department scoping.

## Performance Violations

* Vector embeddings are generated.
* LLMs are invoked.
* Related expansion latency exceeds acceptable thresholds due to non-deterministic queries.

## Data Integrity Violations

* User-added relations overwrite system-derived relations.
* Relation provenance is not preserved.
* Relations are added without tenant isolation.
* Relations are visible across departments without authorization.

## UX Integrity Violations

* Empty Related states display filler or placeholders.
* Errors are shown where silence is acceptable.
* UI suggests next actions implicitly.
* UI blocks navigation due to missing related content.

If any abort condition is met, the implementation is invalid.
