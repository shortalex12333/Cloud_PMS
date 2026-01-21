# ex01_manual_to_related_to_inventory.md

Scenario: Manual section → Related → Inventory item → Back → Manual section → Back → Search bar home

## Initial State

User is on search bar home.

No active situation exists.

## Step 1 — Open Manual Section

User opens manual section:

* artefact_type: manual_section
* artefact_id: 7f9c2a8e-3d2a-4a3e-b6f2-9a2e4d1c1111

System behavior:

* Create new situation
* Set active anchor to manual_section
* Push viewer state

Situation state:

* situation_id: 9b2d6a91-1c3f-4d8a-bf3e-2a91c0e00001
* active_anchor_type: manual_section
* active_anchor_id: 7f9c2a8e-3d2a-4a3e-b6f2-9a2e4d1c1111

Ledger event:

* artefact_opened

## Step 2 — Open Related

User selects Show Related.

Backend request:

```
{
  "situation_id": "9b2d6a91-1c3f-4d8a-bf3e-2a91c0e00001",
  "anchor_type": "manual_section",
  "anchor_id": "7f9c2a8e-3d2a-4a3e-b6f2-9a2e4d1c1111",
  "tenant_id": "a1111111-aaaa-bbbb-cccc-000000000001",
  "user_id": "b2222222-bbbb-cccc-dddd-000000000002",
  "allowed_domains": ["inventory", "work_orders", "history"]
}
```

Backend response:

```
{
  "situation_id": "9b2d6a91-1c3f-4d8a-bf3e-2a91c0e00001",
  "anchor_type": "manual_section",
  "anchor_id": "7f9c2a8e-3d2a-4a3e-b6f2-9a2e4d1c1111",
  "groups": [
    {
      "domain": "inventory",
      "items": [
        {
          "artefact_type": "inventory_item",
          "artefact_id": "3c8e1f2a-aaaa-4bbb-9ccc-111111111111",
          "title": "Jacket Water Temperature Sensor",
          "subtitle": "Port Main Engine"
        }
      ]
    }
  ]
}
```

System behavior:

* Push related view state
* Anchor remains manual_section

No ledger event emitted.

## Step 3 — Open Inventory Item from Related

User selects inventory item:

* artefact_type: inventory_item
* artefact_id: 3c8e1f2a-aaaa-4bbb-9ccc-111111111111

System behavior:

* Replace active anchor
* Push viewer state

Situation state update:

* active_anchor_type: inventory_item
* active_anchor_id: 3c8e1f2a-aaaa-4bbb-9ccc-111111111111

Ledger event:

* artefact_opened

## Step 4 — Back Navigation

User presses Back.

System behavior:

* Pop viewer state
* Restore prior viewer (manual section)

No backend calls.
No ledger events.

## Step 5 — Back Navigation Again

User presses Back.

System behavior:

* Pop related view state
* Restore manual section viewer

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

* Situation lifecycle is continuous.
* Related does not re-run search.
* Back navigation is deterministic.
* Ledger contains only explicit events.
