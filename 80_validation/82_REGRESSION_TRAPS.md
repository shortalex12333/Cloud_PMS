# 82_REGRESSION_TRAPS.md

Regression traps define changes that must never be introduced after MVP.

Any appearance of the conditions below constitutes a regression.

## Navigation Regressions

* Reintroduction of "back to search results"
* Breadcrumbs referencing queries or filters
* Multiple navigation stacks
* Non-linear navigation paths
* Implicit context resets

## Related Expansion Regressions

* Automatic Related expansion
* Introduction of recommendation language
* Client-side ranking or filtering
* Dynamic domain reordering
* Confidence or relevance scoring

## State Management Regressions

* Persisting navigation state beyond situation lifetime
* Restoring state after browser refresh
* Sharing state across situations
* Using state to influence data selection

## Audit Regressions

* Logging UI exploration
* Logging Related usage
* Logging navigation events
* Logging inferred behavior

## Data and Intelligence Regressions

* Introduction of vector embeddings
* Introduction of LLM calls
* Semantic or fuzzy matching
* Heuristic relevance scoring

## Permission Regressions

* Displaying unauthorized artefacts
* Surfacing permission-denied indicators
* Deferring permission checks to the frontend

## UX Regressions

* Adding dashboards, tabs, or feeds
* Adding suggestion banners
* Filling empty states with noise
* Blocking navigation due to missing data

## Structural Regressions

* Diverging Related behavior per domain in UI
* Anchor-specific situation lifecycles
* Forking the state machine

## Enforcement Rule

If any regression trap is detected, the change must be rejected.

No exception.
