# 70_EMPTY_RELATED.md

Empty Related states are valid and intentional.

The absence of related artefacts is not an error.

## Definition of Empty Related

An empty Related state occurs when:

* Deterministic filters return zero artefacts
* No user-added relations exist
* All permission checks pass

## Rendering Rules

* The Related view renders with no domain groups.
* No placeholder content is shown.
* No recommendation language is displayed.
* No error state is presented.

## User Controls

* An Add Related control may be displayed.
* Add Related is optional and user-initiated.
* No guidance or suggestion text accompanies Add Related.

## Behavioral Expectations

* Users are not guided toward specific actions.
* Users are not encouraged to broaden scope automatically.
* Silence communicates absence of known relationships.

## Audit Behavior

* Empty Related states generate no ledger events.
* Viewing an empty Related state is not audited.

## Prohibited Behavior

* Injecting fallback domains.
* Displaying historical or loosely related content.
* Triggering background discovery processes.

## Success Conditions

* Empty states feel calm and deliberate.
* Users trust that nothing relevant exists.

## Failure Conditions

* Empty states appear broken or incomplete.
* UI attempts to compensate with noise.
