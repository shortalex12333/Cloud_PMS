# 01_INVARIANTS.md

Situational continuity is mandatory.

The following invariants must always hold true. Any violation is a defect.

## Situation Invariants

* A situation is created only when an artefact is opened from search.
* A situation is defined by:

  * A single active anchor artefact
  * Extracted entities bound to that artefact
  * Temporal bias favoring present over history
* A situation persists across artefact-to-artefact navigation.
* A situation ends only when the user returns to the search bar home.
* Ended situations are archived for audit only and are not recoverable in UI.

## Anchor Invariants

* Only one anchor exists at any time.
* All artefact types may be anchors:

  * Manual sections
  * Documents
  * Inventory items
  * Work orders
  * Faults
  * Shopping items and lists
  * Emails
  * Certificates and compliance records
* Replacing the anchor does not create a new situation.
* Anchor replacement occurs when a user opens an artefact from Related or any in-situation navigation.

## Navigation Invariants

* Back navigates to the immediately prior artefact view.
* Forward navigates to the immediately next artefact view if available.
* Navigation operates as a linear stack.
* Navigation never returns to search results.
* Navigation never replays queries.
* Navigation state exists only within the active situation.
* Back navigation continues until the search bar home is reached.
* Returning to search bar home terminates the situation.

## Related Expansion Invariants

* Related is a read-only expansion.
* Related never executes a search.
* Related never accepts free-text input.
* Related reuses the current situation's anchor and extracted entities.
* Related may return zero results.
* Silence is valid.
* Related content is grouped by domain.
* Domain grouping order is fixed and defined in contracts.
* Related expansion does not mutate data.

## Memory Invariants

* State memory is scoped to the active situation.
* State memory is cleared when the situation ends.
* State memory does not survive browser refresh.
* State memory is not persisted as user preference.
* State memory does not influence ranking or ordering.

## Audit Invariants

* Only explicit user actions are written to the ledger.
* UI exploration state is not audited.
* Artefact open events are binary.
* "Related opened" is not an auditable event.

## Performance Invariants

* Related expansion must not invoke vector search.
* Related expansion must not invoke LLMs.
* Related expansion must be deterministic.
* Related expansion must rely on filters and explicit relations only.

## Safety Invariants

* A soft cap of nine artefact views is enforced per situation.
* When the cap is exceeded, the oldest artefact view is discarded silently.
* No user-facing warning is shown for stack truncation.

## Prohibited Behaviors

* Auto-expansion of Related
* Recommendation language
* Confidence scores
* Personalized ranking
* Cross-situation learning
* Cross-tenant data access
