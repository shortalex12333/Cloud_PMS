# ex03_empty_related.md

Scenario: Artefact with no related content → Related → Empty view → Back → Artefact → Back → Search bar home

## Initial State

User is on search bar home.

No active situation exists.

## Step 1 — Open Artefact

User opens artefact:

* artefact_type: document
* artefact_id: 8a9b7c6d-aaaa-4bbb-cccc-777777777777

System behavior:

* Create new situation
* Set active anchor to document
* Push viewer state

Situation state:

* situation_id: 11111111-2222-3333-4444-555555555555
* active_anchor_type: document
* active_anchor_id: 8a9b7c6d-aaaa-4bbb-cccc-777777777777

Ledger event:

* artefact_opened

## Step 2 — Open Related

User selects Show Related.

Backend request:

```
{
  "situation_id": "11111111-2222-3333-4444-555555555555",
  "anchor_type": "document",
  "anchor_id": "8a9b7c6d-aaaa-4bbb-cccc-777777777777",
  "tenant_id": "a1111111-aaaa-bbbb-cccc-000000000001",
  "user_id": "b2222222-bbbb-cccc-dddd-000000000002",
  "allowed_domains": ["inventory", "work_orders", "history"]
}
```

Backend response:

```
{
  "situation_id": "11111111-2222-3333-4444-555555555555",
  "anchor_type": "document",
  "anchor_id": "8a9b7c6d-aaaa-4bbb-cccc-777777777777",
  "groups": []
}
```

System behavior:

* Push related view state
* Render empty Related view
* Optional Add Related control may be displayed

No ledger event emitted.

## Step 3 — Back Navigation

User presses Back.

System behavior:

* Restore document viewer

No backend calls.
No ledger events.

## Step 4 — Back to Search Bar Home

User presses Back.

System behavior:

* End situation
* Destroy navigation stack
* Return to search bar home

Ledger event:

* situation_ended

## Expected Outcomes

* Empty Related state is intentional and silent.
* No errors or filler content are shown.
* Situation lifecycle behaves correctly.
