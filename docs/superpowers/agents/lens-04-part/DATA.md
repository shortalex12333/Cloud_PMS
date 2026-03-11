# DATA AGENT — Part / Inventory Lens

**Your role:** Verify the existing `/v1/entity/part/{id}` endpoint is correct.
Note: `inventory` entity type also maps to this endpoint via RouteShell `ENTITY_ENDPOINTS.inventory = 'part'`.

---

## Endpoint

`GET /v1/entity/part/{part_id}`
**File:** `apps/api/pipeline_service.py` lines ~1235–1282
**Status:** ✅ EXISTS — verify shape only.

---

## DB Table (verified)

```
pms_parts:
  id, yacht_id, name, part_number, quantity_on_hand, minimum_quantity,
  location, category, unit, manufacturer, description,
  last_counted_at, last_counted_by,
  metadata (jsonb) → { unit_cost, supplier },
  created_at, updated_at
```

---

## Required Response Shape

```json
{
  "id": "uuid",
  "part_name": "Oil Filter 12x",
  "part_number": "OF-12",
  "stock_quantity": 4,
  "min_stock_level": 2,
  "location": "Store Room A",
  "unit_cost": 25.00,
  "supplier": "Marine Parts Co",
  "category": "consumable",
  "unit": "each",
  "manufacturer": "Mann+Hummel",
  "description": "...",
  "last_counted_at": "...",
  "created_at": "..."
}
```

**Column mapping in code:**
- `part_name` ← `name`
- `stock_quantity` ← `quantity_on_hand`
- `min_stock_level` ← `minimum_quantity`
- `unit_cost` ← `metadata.get('unit_cost')`
- `supplier` ← `metadata.get('supplier')`

---

## Role-Gated Actions

ALL roles: consume_part, receive_part, transfer_part, add_to_shopping_list
HOD only: adjust_stock_quantity (signed), write_off_part (signed), order_part

---

## Success Criteria

200 + `id`, `part_name`, `stock_quantity` non-null.
