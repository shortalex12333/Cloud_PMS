# ex02_inventory_to_related_to_work_order.md

Scenario: Inventory item → Related → Work Order → Back → Inventory item → Back → Search bar home

## Initial State

User is on search bar home.

No active situation exists.

## Step 1 — Open Inventory Item

User opens inventory item:

* artefact_type: inventory_item
* artefact_id: 5a4f9c3e-2222-4ddd-8eee-333333333333

System behavior:

* Create new situation
* Set active anchor to inventory_item
* Push viewer state

Situation state:

* situation_id: 4c1a9e7d-8b2f-4a77-9c2e-000000000010
* active_anchor_type: inventory_item
* active_anchor_id: 5a4f9c3e-2222-4ddd-8eee-333333333333

Ledger event:

* artefact_opened

## Step 2 — Open Related

User selects Show Related.

Backend request:

```
{
  "situation_id": "4c1a9e7d-8b2f-4a77-9c2e-000000000010",
  "anchor_type": "inventory_item",
  "anchor_id": "5a4f9c3e-2222-4ddd-8eee-333333333333",
  "tenant_id": "a1111111-aaaa-bbbb-cccc-000000000001",
  "user_id": "b2222222-bbbb-cccc-dddd-000000000002",
  "allowed_domains": ["work_orders", "documents", "history"]
}
```

Backend response:

```
{
  "situation_id": "4c1a9e7d-8b2f-4a77-9c2e-000000000010",
  "anchor_type": "inventory_item",
  "anchor_id": "5a4f9c3e-2222-4ddd-8eee-333333333333",
  "groups": [
    {
      "domain": "work_orders",
      "items": [
        {
          "artefact_type": "work_order",
          "artefact_id": "9d7e2a44-4444-4bbb-aaaa-555555555555",
          "title": "WO-1821",
          "subtitle": "Replace temperature sensor"
        }
      ]
    }
  ]
}
```

System behavior:

* Push related view state
* Anchor remains inventory_item

No ledger event emitted.

## Step 3 — Open Work Order from Related

User selects work order:

* artefact_type: work_order
* artefact_id: 9d7e2a44-4444-4bbb-aaaa-555555555555

System behavior:

* Replace active anchor
* Push viewer state

Situation state update:

* active_anchor_type: work_order
* active_anchor_id: 9d7e2a44-4444-4bbb-aaaa-555555555555

Ledger event:

* artefact_opened

## Step 4 — Back Navigation

User presses Back.

System behavior:

* Restore inventory item viewer

No backend calls.
No ledger events.

## Step 5 — Back to Search Bar Home

User presses Back.

System behavior:

* End situation
* Destroy navigation stack
* Return to search bar home

Ledger event:

* situation_ended

## Expected Outcomes

* Anchor replacement occurs within the same situation.
* Related expansion remains deterministic.
* Back navigation restores prior artefacts.
* Ledger records only explicit actions.
