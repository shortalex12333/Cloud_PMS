# Shopping List — Data Continuity Flow (CEO directive 2026-04-25)

Owner: SHOPPING05 · Status: PLAN · Sibling PR (#TBD) lands the Attachments tab.

## Why

CEO ruling (verbatim, paraphrased for ops):

> Users who create shopping list items rarely have a definitive part number,
> location or entity card at the moment of capture. They have a URL, a price,
> a quantity and a description for what they want to order. Sometimes the part
> is consumed straight off the boat (eg. "10 EU→UK convertor plugs"), sometimes
> it needs to be assigned to inventory after delivery.
>
> Our mission is data continuity. Every flow must close. We do not trust users
> to "promise to fill it in later" — that is what generic SaaS does. The system
> must remember and remind until the data is complete.

## Two-stage capture model

### Stage 1 — Capture (popup on Shopping List page)

A single "Add Item" flow that ALWAYS asks for the same shape, regardless of
whether a catalogue part already exists.

| Field | Required | Notes |
|---|---|---|
| `description` | yes | Free text — user states what they want |
| `qty_requested` | yes | Integer ≥ 1 |
| `unit` | optional | Default: "ea" |
| `estimated_unit_price` | yes | Numeric. Drives projected cost. |
| `currency` | optional | Default: yacht.preferred_currency |
| `source_url` | optional | Link to vendor page / quote |
| `urgency` | yes | routine / high / critical |
| `required_by_date` | optional | Date |
| `assign_to_part_id` | optional | Picker — pick existing catalogue part |
| `intended_storage_location_id` | optional | Picker — IF user knows where it will live |

If `assign_to_part_id` is provided → row created with `part_id` set + `is_candidate_part=false`.
If NOT → row created with `is_candidate_part=true`, `part_id=null`, `description` carried.

### Stage 2 — Continuity guarantee (backend invariant)

Any `pms_shopping_list_items` row with `is_candidate_part=true` AND
`part_id IS NULL` MUST trigger:

1. **Notification subscription** — recurring weekly nudge to the requester
   (and to chief_engineer if requester ≠ chief) until either:
     - `candidate_promoted_to_part_id` is set (existing column), OR
     - row is rejected (status=rejected).
2. **Ledger entry** at creation time:
   `event_type='shopping_list.candidate_captured'`,
   `requires_followup=true`, `followup_target='promote_candidate_to_part'`.
3. **Dashboard surfacing** — homepage "Open follow-ups" tile pulls these rows
   so they cannot be silently abandoned.

When the candidate is promoted (existing `promote_candidate_to_part` action)
or received (existing `receive_part` flow that links to inventory), a closing
ledger row writes `requires_followup=false` and the notification subscription
clears.

## Retiring `add_to_shopping_list` from Part lens (CEO ruling)

CEO confirmed: keep the action retired from the Part lens dropdown (already
hidden via _SHOPPING_LIST_HIDDEN_ACTIONS for shopping_list entities). The
canonical capture surface is the floating "+ Add Item" on the Shopping List
page using the popup above. Lock-in by:

- Removing `("part", "add_to_shopping_list")` from
  `apps/api/action_router/entity_prefill.py:312` (so it stops appearing on
  /inventory/<id>).
- Replacing the registry entry's `domain="shopping_list"` cross-domain
  injection with a direct link from Part lens → Shopping List page with
  `?prefill_part_id=<id>` query param consumed by the popup.

(Implementation lives in a follow-up PR; this doc is the spec.)

## Files to touch (next PR)

Backend:
  - `apps/api/action_router/registry.py` — extend `create_shopping_list_item`
    field_metadata with description/source_url/intended_storage_location_id;
    add `is_candidate_part` flag handling.
  - `apps/api/routes/handlers/shopping_handler.py` — on insert, when
    is_candidate_part=true: write ledger row + queue notification.
  - `apps/api/notifications/` — `shopping_list_candidate_followup` recurring
    notification class (weekly cadence, clears on promote/reject).

Frontend:
  - `apps/web/src/components/shopping-list/CreateItemModal.tsx` — add the
    9 fields above; conditionally show storage-location picker if the user
    flips a "Assign to inventory now" toggle.
  - `apps/web/src/app/inventory/[id]/page.tsx` — replace
    `add_to_shopping_list` dropdown action with a direct router push to
    `/shopping-list?prefill_part_id={id}`.

## Definition of done

- New shopping list item with `is_candidate_part=true` writes one ledger row
  AND one open notification subscription, verified via psql.
- `promote_candidate_to_part` closes both (verified via integration test).
- Part-lens dropdown no longer shows "Add to Shopping List".
- /inventory/<id> "Order Part" / direct link to shopping-list popup works.

## Cross-domain dependency (parked)

`order_id` writeback is owned by PURCHASE05; see
`docs/ongoing_work/shopping list/SHOPPING_LIST_AUDIT.md` §6.
