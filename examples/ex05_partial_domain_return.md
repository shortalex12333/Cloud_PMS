# ex05_partial_domain_return.md

Scenario: Artefact with related content in some domains and none in others

## Initial State

User is on search bar home.

No active situation exists.

## Step 1 — Open Artefact

User opens artefact:

* artefact_type: manual_section
* artefact_id: 6d5c4b3a-aaaa-4bbb-cccc-999999999999

System behavior:

* Create new situation
* Set active anchor to manual_section
* Push viewer state

Situation state:

* situation_id: 12121212-3434-5656-7878-909090909090
* active_anchor_type: manual_section
* active_anchor_id: 6d5c4b3a-aaaa-4bbb-cccc-999999999999

Ledger event:

* artefact_opened

## Step 2 — Open Related

User selects Show Related.

Backend request:

```
{
  "situation_id": "12121212-3434-5656-7878-909090909090",
  "anchor_type": "manual_section",
  "anchor_id": "6d5c4b3a-aaaa-4bbb-cccc-999999999999",
  "tenant_id": "a1111111-aaaa-bbbb-cccc-000000000001",
  "user_id": "b2222222-bbbb-cccc-dddd-000000000002",
  "allowed_domains": ["inventory", "work_orders", "documents", "history"]
}
```

Backend behavior:

* Inventory returns items
* Work_orders returns zero items
* Documents returns zero items
* History returns items

Backend response:

```
{
  "situation_id": "12121212-3434-5656-7878-909090909090",
  "anchor_type": "manual_section",
  "anchor_id": "6d5c4b3a-aaaa-4bbb-cccc-999999999999",
  "groups": [
    {
      "domain": "inventory",
      "items": [
        {
          "artefact_type": "inventory_item",
          "artefact_id": "10101010-aaaa-bbbb-cccc-111111111111",
          "title": "Expansion Tank Level Switch"
        }
      ]
    },
    {
      "domain": "history",
      "items": [
        {
          "artefact_type": "history_event",
          "artefact_id": "20202020-bbbb-cccc-dddd-222222222222",
          "title": "Alarm acknowledged"
        }
      ]
    }
  ]
}
```

System behavior:

* Push related view state
* Render only inventory and history domains
* Omit empty domains silently

No ledger event emitted.

## Step 3 — Back Navigation

User presses Back.

System behavior:

* Restore manual section viewer

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

* Partial domain results render cleanly.
* No empty domain headers appear.
* User experience remains calm and predictable.
