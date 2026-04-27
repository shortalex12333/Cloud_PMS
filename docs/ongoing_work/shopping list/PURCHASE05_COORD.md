# Shopping List V2 — PURCHASE05 Coordination Note
**From:** SHOPPING05 | **Date:** 2026-04-27 | **Status:** MIGRATIONS LIVE

---

## What landed in TENANT (already applied — do not re-run)

| Migration | What | Verified |
|---|---|---|
| M0 | Dropped `shopping_list_items` (0 rows, nothing referenced it, old schema) | ✓ |
| M1 | Created `pms_shopping_lists` header table + RLS + auto-number trigger (SL-2026-001…) | ✓ |
| M2 | Added `pms_shopping_list_items.shopping_list_id uuid FK → pms_shopping_lists` (nullable, old rows stay NULL) | ✓ |
| M3 | Added `'rejected'` to `pms_shopping_list_items` status CHECK constraint | ✓ |
| M4 | Updated `enforce_shopping_list_edit_rules` trigger — allows `candidate→approved` (HOD direct) and `*→rejected` | ✓ |
| **M5** | Added `pms_purchase_orders.source_shopping_list_id uuid FK → pms_shopping_lists` | ✓ |
| **M6** | Added `pms_purchase_order_items.shopping_list_item_id uuid FK → pms_shopping_list_items` | ✓ |

M5 and M6 are the ones that affect your domain.

---

## What PURCHASE05 needs to change in `_convert_to_po`

File: `apps/api/action_router/dispatchers/internal_dispatcher.py:3714`

### Current behaviour
- Grabs all `status='approved'` items across the vessel by `yacht_id`
- Optionally filters by `item_ids` list
- Creates PO + PO line items
- Marks items as `status='ordered'`

### Required changes

**1. Accept `shopping_list_id` param (new primary filter)**
```python
shopping_list_id = params.get("shopping_list_id")
if shopping_list_id:
    query = query.eq("shopping_list_id", shopping_list_id)
elif item_ids:
    query = query.in_("id", item_ids)
# else: fallback to all approved (backwards compat — keep for now)
```

**2. Write `source_shopping_list_id` on the PO row**
```python
po_data = {
    "id": po_id,
    "yacht_id": yacht_id,
    "po_number": po_number,
    "status": "draft",
    "ordered_by": user_id,
    "source_shopping_list_id": shopping_list_id,  # ADD THIS
    "created_at": datetime.utcnow().isoformat(),
    "updated_at": datetime.utcnow().isoformat(),
}
```

**3. Write `shopping_list_item_id` on each PO line item**
```python
supabase.table("pms_purchase_order_items").insert({
    "id": line_id,
    "yacht_id": yacht_id,
    "purchase_order_id": po_id,
    "part_id": item.get("part_id"),
    "description": item["part_name"],
    "quantity_ordered": int(item.get("quantity_approved") or item["quantity_requested"]),
    "shopping_list_item_id": item["id"],  # ADD THIS — links PO line back to shopping item
}).execute()
```

**4. Mark `pms_shopping_lists` as converted**
```python
if shopping_list_id:
    supabase.table("pms_shopping_lists").update({
        "status": "converted_to_po",
        "converted_to_po_id": po_id,
        "converted_at": datetime.utcnow().isoformat(),
    }).eq("id", shopping_list_id).eq("yacht_id", yacht_id).execute()
```

**5. Write `order_id` + `order_line_number` back on shopping items (PR #726)**
This was already the plan from PR #726. Make sure the writeback uses the loop index for `order_line_number`:
```python
for line_num, (item, line_id) in enumerate(zip(items, line_ids), start=1):
    supabase.table("pms_shopping_list_items").update({
        "status": "ordered",
        "order_id": po_id,
        "order_line_number": line_num,
        "updated_at": datetime.utcnow().isoformat(),
        "updated_by": user_id,
    }).eq("id", item["id"]).eq("yacht_id", yacht_id).execute()
```

---

## What PURCHASE05 does NOT need to change

- `pms_purchase_order_items` RLS — existing policies use `has_yacht_access(yacht_id)`, the new column inherits that.
- Receiving flow — `pms_receiving_line_items.shopping_list_item_id` already exists and already updates `quantity_received` on shopping items. No change needed.
- `entity_routes.py` PO endpoint — SHOPPING05 will read `source_shopping_list_id` from the PO response to show a nav link back to the list.

---

## Backwards compatibility

- `shopping_list_id` is nullable — all existing PO items have `shopping_list_item_id = NULL`. Safe.
- `source_shopping_list_id` is nullable — all existing POs have it as NULL. Safe.
- Old `convert_to_po` calls without `shopping_list_id` still work (fallback to all approved items). Backwards compat preserved until we cut over fully.
