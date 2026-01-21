# 81_ACCEPTANCE_TESTS.md

Acceptance tests define the minimum behavioral guarantees of the Situational Continuity Layer.

All tests must pass for the implementation to be considered valid.

## Test 1 — Situation Creation

* User is on search bar home.
* User opens an artefact from search.
* A situation is created.
* The opened artefact becomes the active anchor.
* A viewer state is pushed onto the stack.

Expected result:

* Situation exists.
* Anchor is set correctly.
* Back navigates to search bar home.

## Test 2 — Anchor Replacement Within Situation

* User opens artefact A from search.
* User opens Related.
* User opens artefact B from Related.

Expected result:

* Situation remains the same.
* Anchor is replaced with artefact B.
* Back returns to artefact A.
* Back again returns to search bar home.

## Test 3 — Related Expansion Without Re-query

* User opens artefact from search.
* User opens Related.

Expected result:

* No search query is executed.
* Backend receives only the Related contract payload.
* Related view renders grouped results.

## Test 4 — Empty Related

* User opens an artefact with no related content.
* User opens Related.

Expected result:

* Related view renders empty.
* No error is shown.
* Optional Add Related control may appear.

## Test 5 — Partial Domain Results

* User opens artefact with related content in one domain only.
* User opens Related.

Expected result:

* Only populated domain is rendered.
* Domain order remains fixed.
* No indication of missing domains.

## Test 6 — Permission Denied Domain

* User lacks permission for one related domain.
* User opens Related.

Expected result:

* Domain is omitted.
* No permission warning is shown.
* Other domains render normally.

## Test 7 — Back and Forward Navigation

* User opens artefact A.
* User opens Related.
* User opens artefact B.
* User presses Back.
* User presses Forward.

Expected result:

* Back restores artefact A.
* Forward restores artefact B.
* No data fetching occurs during Forward.

## Test 8 — Stack Limit Enforcement

* User navigates through more than nine artefact views.

Expected result:

* Oldest view state is discarded silently.
* Back and Forward continue to work within remaining stack.

## Test 9 — Situation Termination

* User navigates back until search bar home is reached.

Expected result:

* Situation ends.
* Navigation stack is destroyed.
* Forward is no longer available.

## Test 10 — Ledger Integrity

* User opens artefact.
* User adds a related artefact.
* User returns to search bar home.

Expected result:

* artefact_opened event exists.
* relation_added event exists.
* situation_ended event exists.
* No UI exploration events exist.

All tests must pass without exception.
