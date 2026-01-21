# ex06_add_related_user_action.md

Scenario: User explicitly adds a related artefact where no deterministic relation existed

## Initial State

User is on search bar home.

No active situation exists.

## Step 1 — Open Artefact

User opens artefact:

* artefact_type: document
* artefact_id: a1b2c3d4-aaaa-4bbb-cccc-123456789000

System behavior:

* Create new situation
* Set active anchor to document
* Push viewer state

Situation state:

* situation_id: ffffffff-1111-2222-3333-444444444444
* active_anchor_type: document
* active_anchor_id: a1b2c3d4-aaaa-4bbb-cccc-123456789000

Ledger event:

* artefact_opened

## Step 2 — Open Related (Empty)

User selects Show Related.

Backend response:

* groups: []

System behavior:

* Push related view state
* Render empty Related view
* Display Add Related control

No ledger event emitted.

## Step 3 — Add Related

User selects Add Related and chooses artefact:

* to_artefact_type: inventory_item
* to_artefact_id: bbbbbbbb-cccc-dddd-eeee-555555555555

Backend request:

```
{
  "tenant_id": "a1111111-aaaa-bbbb-cccc-000000000001",
  "user_id": "b2222222-bbbb-cccc-dddd-000000000002",
  "from_artefact_type": "document",
  "from_artefact_id": "a1b2c3d4-aaaa-4bbb-cccc-123456789000",
  "to_artefact_type": "inventory_item",
  "to_artefact_id": "bbbbbbbb-cccc-dddd-eeee-555555555555",
  "situation_id": "ffffffff-1111-2222-3333-444444444444"
}
```

Backend behavior:

* Persist explicit relation
* Emit relation_added event

Ledger event:

* relation_added

## Step 4 — Related Refresh

System behavior:

* Related view refreshes deterministically
* Newly added relation appears under correct domain
* Relation is marked user-added visually neutral

No additional ledger event emitted.

## Step 5 — Back Navigation

User presses Back.

System behavior:

* Restore document viewer

No backend calls.
No ledger events.

## Step 6 — Back to Search Bar Home

User presses Back.

System behavior:

* End situation
* Destroy navigation stack
* Return to search bar home

Ledger event:

* situation_ended

## Expected Outcomes

* User-added relations are explicit and auditable.
* No inference is introduced.
* Related remains deterministic after user input.
* Ledger reflects only completed actions.
