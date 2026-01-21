# ex09_handover_view_within_situation.md

Scenario: User opens a handover artefact that aggregates multiple items within a single situation

## Initial State

User is on search bar home.

No active situation exists.

## Step 1 — Open Handover

User opens handover artefact:

* artefact_type: handover
* artefact_id: h0000000-aaaa-bbbb-cccc-999999999999

System behavior:

* Create new situation
* Set active anchor to handover
* Push viewer state

Situation state:

* situation_id: 77777777-8888-9999-aaaa-bbbbbbbbbbbb
* active_anchor_type: handover
* active_anchor_id: h0000000-aaaa-bbbb-cccc-999999999999

Ledger event:

* artefact_opened

## Step 2 — Render Handover Contents

Handover viewer renders:

* Multiple referenced artefacts (documents, work orders, inventory items)
* Each item is a navigable artefact reference

No Related view is automatically opened.

No ledger event emitted.

## Step 3 — Open Referenced Artefact from Handover

User selects a referenced work order:

* artefact_type: work_order
* artefact_id: wo999999-aaaa-bbbb-cccc-888888888888

System behavior:

* Replace active anchor
* Push viewer state
* Remain within same situation

Ledger event:

* artefact_opened

## Step 4 — Back Navigation

User presses Back.

System behavior:

* Restore handover viewer
* Preserve handover scroll position if possible
* No re-fetch of handover contents

No ledger event emitted.

## Step 5 — Open Related from Handover

User selects Show Related while viewing handover.

Backend behavior:

* Related is computed using handover as anchor
* Allowed domains include all artefact types referenced by handover

System behavior:

* Push related view state
* Render grouped results deterministically

No ledger event emitted.

## Step 6 — Back to Search Bar Home

User presses Back repeatedly until home is reached.

System behavior:

* End situation
* Destroy navigation stack

Ledger event:

* situation_ended

## Expected Outcomes

* Handover participates as a first-class artefact.
* Aggregation does not create nested situations.
* Navigation remains linear and predictable.
* Ledger reflects explicit openings only.
