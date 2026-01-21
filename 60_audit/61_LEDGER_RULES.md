# 61_LEDGER_RULES.md

The ledger is the authoritative record of explicit user actions.

The ledger exists to support accountability, audit, insurance, compliance, and post-incident reconstruction.

## Ledger Scope

The ledger records:

* What artefact was opened
* What explicit relationships were created
* When a situation ended

The ledger does not record:

* UI exploration
* Navigation attempts
* Related expansion usage
* User hesitation or intent

## Truth Model

* Ledger entries are binary.
* An artefact is either opened or not opened.
* A relation is either added or not added.
* Situations are either active or ended.

No partial truth is permitted.

## Write Rules

* Ledger writes occur only after successful user action.
* Failed attempts do not generate ledger entries.
* Duplicate events must not be deduplicated silently.

## Immutability

* Ledger entries must be append-only.
* Ledger entries must not be modified or deleted.
* Corrections must be represented as new events.

## Attribution

Every ledger entry must include:

* tenant_id
* user_id
* timestamp
* artefact or relation identifiers

Anonymous or system-attributed entries are forbidden.

## Tenant Isolation

* Ledger entries must be tenant-isolated.
* Cross-tenant access is forbidden.
* Cross-department access is restricted by RBAC.

## Compliance Alignment

Ledger design must support:

* Insurance claims
* Warranty disputes
* Regulatory review
* Internal accountability

## Prohibited Behavior

* Logging inferred behavior.
* Logging navigation paths.
* Logging Related expansion usage.
* Logging non-final actions.

## Success Conditions

* Ledger entries are legally defensible.
* Ledger entries can reconstruct what was known and done.

## Failure Conditions

* Ledger contains speculative data.
* Ledger contains UI noise.
* Ledger contains unverifiable events.
