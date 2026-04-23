# Gap: Receiving acceptance does not update inventory stock

Severity: P1 — operationally significant. Out of scope for this bugfix PR.

## Observed

`pms_inventory_stock.quantity` does not change when a receiving event is signed off, even when the line items have a `part_id` linking them to `pms_parts`. The "data continuity" promise is broken at this hand-off — the parts are physically aboard, the receiving record says "accepted", but the parts catalog still shows pre-delivery stock.

## Where the gap lives

`apps/api/handlers/receiving_handlers.py` lines 1206–1397 (`_accept_receiving_adapter`). The function:

1. Validates state — refuses if already accepted/rejected, refuses if zero line items (`:1268-1295`).
2. Updates `pms_receiving.status = 'accepted'` (`:1351`).
3. Writes a `ledger_events` audit row (`:1366-1381`).
4. Writes an `auth_signatures` row (PIN/TOTP verification).

There is **no** loop over `pms_receiving_items` and **no** UPSERT into `pms_inventory_stock`.

Verified by:
```bash
grep -n "inventory_stock\|quantity_on_hand\|pms_parts" apps/api/handlers/receiving_handlers.py
# (zero hits)
```

## What "correct" would look like

After the existing status update + audit, do something like:

```python
items = db_client.table("pms_receiving_items").select(
    "part_id, quantity_received"
).eq("receiving_id", receiving_id).eq("yacht_id", yacht_id).execute().data or []

for it in items:
    pid = it.get("part_id")
    qty = it.get("quantity_received") or 0
    if not pid or qty <= 0:
        continue  # ad-hoc line items not linked to catalog → skip stock update

    # UPSERT pms_inventory_stock: increment quantity, or insert with starting qty
    existing = db_client.table("pms_inventory_stock").select(
        "id, quantity"
    ).eq("part_id", pid).eq("yacht_id", yacht_id).maybe_single().execute()

    if existing and existing.data:
        new_qty = (existing.data.get("quantity") or 0) + int(qty)
        db_client.table("pms_inventory_stock").update({
            "quantity": new_qty,
            "updated_at": "now()",
            "updated_by": user_id,
        }).eq("id", existing.data["id"]).execute()
    else:
        db_client.table("pms_inventory_stock").insert({
            "yacht_id": yacht_id,
            "part_id": pid,
            "quantity": int(qty),
            "updated_by": user_id,
        }).execute()

    # Optional: write a pms_inventory_transactions row for traceability
```

Considerations:
- `pms_inventory_stock` is keyed `(yacht_id, part_id, location)` in practice — `location` may need to come from the receiving record or a default.
- Should be transactional: if any stock UPSERT fails, the entire accept should roll back (or write an explicit reconciliation event).
- Edge case: if the same receiving is somehow re-accepted (shouldn't happen because `:1268` guards), idempotency must be preserved — keying the increment by a `(receiving_id, part_id)` event row would prevent double-counting.

## Why it matters

CelesteOS pitches "data continuity" as a USP. A receiving event that doesn't touch stock means the inventory page lies. SeaHub and iDAYACHT both close this loop on goods-in. Until this is built, every "accept receiving" creates drift between the parts ledger and reality.

## Recommendation

Stage as a separate PR:
- Title: `feat(receiving): increment pms_inventory_stock on accept_receiving`
- Test plan: integration test that creates receiving + items with part_id → accepts → asserts stock incremented; ad-hoc items skipped; idempotency proof.
- DB migration: add `(yacht_id, part_id, source_receiving_id)` unique constraint on `pms_inventory_transactions` to prevent double-credit on retries.
