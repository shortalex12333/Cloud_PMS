# 71_PARTIAL_DOMAIN_RESULTS.md

Partial domain results occur when some related domains return artefacts and others do not.

Partial results are valid and must render without error.

## Definition of Partial Results

Partial domain results occur when:

* At least one allowed domain returns artefacts
* One or more allowed domains return zero artefacts
* Permission checks pass for returned domains

## Rendering Rules

* Only domains with artefacts are rendered.
* Domains with zero artefacts are omitted.
* Domain order remains fixed for rendered domains.
* No indication is given that other domains were queried.

## Permission Interaction

* Domains omitted due to permission restrictions are treated as empty.
* Permission failures do not block rendering of other domains.
* No permission error messages are shown in Related view.

## Backend Behavior

* Backend evaluates all allowed domains independently.
* Backend omits domains with no permitted artefacts.
* Backend does not short-circuit on partial success.

## Audit Behavior

* Partial domain results generate no audit events.
* Viewing partial results is not recorded.

## Prohibited Behavior

* Displaying disabled or empty domain headers.
* Showing permission warnings inside Related.
* Attempting retries for missing domains.

## Success Conditions

* Users see only relevant, accessible information.
* Partial data does not feel degraded.

## Failure Conditions

* UI implies missing data.
* Backend fails the entire response due to partial emptiness.
