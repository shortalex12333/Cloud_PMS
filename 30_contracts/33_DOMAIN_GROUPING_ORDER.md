# 33_DOMAIN_GROUPING_ORDER.md

Domain grouping defines how Related results are structured and ordered.

Grouping is domain-first and deterministic.

## Domain Order

Related results must be grouped and returned in the following fixed order:

1. inventory
2. work_orders
3. faults
4. shopping
5. documents
6. manuals
7. emails
8. certificates
9. history

This order must not change dynamically.

## Grouping Rules

* Each domain is rendered as a distinct group.
* Domains with no permitted items are omitted.
* Domains are never merged.
* Domains are never split.

## Item Ordering Within Domains

* Items within a domain may be ordered by temporal bias only.
* Temporal bias favors:

  * now
  * recent
  * historical
* No other ranking signals are permitted.

## History Domain

* History is a first-class domain.
* History represents auditable events related to the anchor.
* History is read-only.
* History must not influence ordering of other domains.

## User-Added Relations

* User-added relations appear in their respective domain.
* User-added relations are visually neutral.
* Provenance is preserved internally but not emphasized in UI.

## Permission Rules

* Domain groups include only items the user is authorized to access.
* Unauthorized items are omitted silently.
* Domains with zero authorized items are omitted.

## Prohibited Behavior

* Confidence-based grouping.
* AI-derived grouping.
* Dynamic domain reordering.
* Highlighting user-added relations.

## Success Conditions

* Related content feels structured and predictable.
* Users can scan by domain without cognitive load.

## Failure Conditions

* Domain order varies between requests.
* Domains appear without items.
* Grouping logic changes based on user behavior.
