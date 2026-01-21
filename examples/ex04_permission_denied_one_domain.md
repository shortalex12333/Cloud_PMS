# ex04_permission_denied_one_domain.md

Scenario: Artefact with related content in multiple domains where one domain is permission-denied

## Initial State

User is on search bar home.

No active situation exists.

## Step 1 — Open Artefact

User opens artefact:

* artefact_type: fault
* artefact_id: 2f3e4d5c-aaaa-4bbb-cccc-888888888888

System behavior:

* Create new situation
* Set active anchor to fault
* Push viewer state

Situation state:

* situation_id: 99999999-aaaa-bbbb-cccc-000000000099
* active_anchor_type: fault
* active_anchor_id: 2f3e4d5c-aaaa-4bbb-cccc-888888888888

Ledger event:

* artefact_opened

## Step 2 — Open Related

User selects Show Related.

Backend request:

```
{
  "situation_id": "99999999-aaaa-bbbb-cccc-000000000099",
  "anchor_type": "fault",
  "anchor_id": "2f3e4d5c-aaaa-4bbb-cccc-888888888888",
  "tenant_id": "a1111111-aaaa-bbbb-cccc-000000000001",
  "user_id": "b2222222-bbbb-cccc-dddd-000000000002",
  "allowed_domains": ["inventory", "work_orders", "history"]
}
```

Backend behavior:

* Inventory domain returns items
* Work_orders domain contains items but user lacks permission
* History domain returns items

Backend response:

```
{
  "situation_id": "99999999-aaaa-bbbb-cccc-000000000099",
  "anchor_type": "fault",
  "anchor_id": "2f3e4d5c-aaaa-4bbb-cccc-888888888888",
  "groups": [
    {
      "domain": "inventory",
      "items": [
        {
          "artefact_type": "inventory_item",
          "artefact_id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
          "title": "Cooling Pump Seal"
        }
      ]
    },
    {
      "domain": "history",
      "items": [
        {
          "artefact_type": "history_event",
          "artefact_id": "ffffffff-1111-2222-3333-444444444444",
          "title": "Fault logged"
        }
      ]
    }
  ]
}
```

System behavior:

* Push related view state
* Omit work_orders domain entirely
* Render inventory and history only

No ledger event emitted.

## Step 3 — Back Navigation

User presses Back.

System behavior:

* Restore fault viewer

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

* Permission-denied domain is invisible.
* No access warnings appear.
* Other domains render normally.
* Ledger reflects only explicit actions.
