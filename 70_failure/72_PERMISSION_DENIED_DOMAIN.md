# 72_PERMISSION_DENIED_DOMAIN.md

Permission-denied domains must not appear in Related expansion.

Permission enforcement is silent and strict.

## Definition of Permission Denial

A permission-denied domain occurs when:

* The user lacks access to all artefacts within a domain
* RBAC or department rules prevent visibility
* Tenant isolation prevents access

## Rendering Rules

* Permission-denied domains are omitted entirely.
* No placeholder, warning, or error is displayed.
* The absence of a domain must be indistinguishable from an empty domain.

## Backend Behavior

* Permission checks are evaluated before grouping.
* Artefacts failing permission checks are excluded.
* Domains with zero permitted artefacts are omitted.

## Frontend Behavior

* Frontend must not attempt to infer missing domains.
* Frontend must not display permission-related UI.

## Audit Behavior

* Permission-denied domains generate no audit events.
* Permission failures are not logged as user activity.

## Prohibited Behavior

* Displaying access-denied messages in Related.
* Allowing artefact click-through without permission.
* Deferring permission checks to client-side.

## Success Conditions

* Users never see artefacts they cannot access.
* Related expansion remains calm and predictable.

## Failure Conditions

* Unauthorized artefacts appear.
* Permission logic leaks through UI.
