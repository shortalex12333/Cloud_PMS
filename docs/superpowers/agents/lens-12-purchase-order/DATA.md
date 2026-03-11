# DATA AGENT — Purchase Order Lens

**Your role:** IMPLEMENT `GET /v1/entity/purchase_order/{id}` in `apps/api/routes/entity_routes.py`.
This endpoint does NOT exist yet. You must create it.

---

## Endpoint to create

`GET /v1/entity/purchase_order/{po_id}`
**File to modify:** `apps/api/routes/entity_routes.py` (create if not exists)
**Mount in:** `apps/api/pipeline_service.py` (add import + `app.include_router(entity_routes_router)`)

---

## DB Tables (EXACT column names)

```
pms_purchase_orders (main record):
  id                   uuid        NOT NULL
  yacht_id             uuid        NOT NULL
  po_number            text        NOT NULL   e.g. "PO-2026-042"
  status               text        NOT NULL   "draft","sent","acknowledged","received","cancelled"
  supplier_name        text        nullable   (may also be "vendor_name")
  order_date           date        nullable   (may also be "created_at")
  expected_delivery    date        nullable   (may also be "expected_delivery_date")
  total_amount         numeric     nullable   (may also be "total")
  currency             text        nullable   default "USD"
  notes                text        nullable
  created_at           timestamptz NOT NULL

pms_purchase_order_items (line items, joined by purchase_order_id):
  id                   uuid        NOT NULL
  purchase_order_id    uuid        NOT NULL
  part_id              uuid        nullable
  name                 text        nullable   (may also be "part_name" or "description")
  quantity_ordered     numeric     NOT NULL
  quantity_received    numeric     nullable   default 0
  unit_price           numeric     nullable
  currency             text        nullable
```

**Column name uncertainty:** Use `.get()` with fallbacks:
- `supplier_name` → `vendor_name`
- `expected_delivery` → `expected_delivery_date`
- `total_amount` → `total`
- item `name` → `part_name` → `description`

---

## Required Response Shape

```json
{
  "id": "uuid",
  "po_number": "PO-2026-042",
  "status": "sent",
  "supplier_name": "Marine Parts Co",
  "order_date": "2026-03-01",
  "expected_delivery": "2026-03-15",
  "total_amount": 1250.00,
  "currency": "USD",
  "notes": null,
  "items": [
    {
      "id": "uuid",
      "part_id": "uuid",
      "name": "Oil Filter",
      "quantity_ordered": 4,
      "quantity_received": 0,
      "unit_price": 45.00,
      "currency": "USD"
    }
  ],
  "created_at": "...",
  "yacht_id": "uuid"
}
```

---

## Implementation Template

```python
@router.get("/v1/entity/purchase_order/{po_id}")
async def get_purchase_order_entity(po_id: str, auth: dict = Depends(get_authenticated_user)):
    try:
        yacht_id = auth['yacht_id']
        tenant_key = auth['tenant_key_alias']
        supabase = get_tenant_client(tenant_key)

        r = supabase.table("pms_purchase_orders").select("*") \
            .eq("id", po_id) \
            .eq("yacht_id", yacht_id) \
            .maybe_single().execute()

        if not r.data:
            raise HTTPException(status_code=404, detail="Purchase order not found")

        data = r.data

        # Fetch line items
        items_r = supabase.table("pms_purchase_order_items").select("*") \
            .eq("purchase_order_id", po_id).execute()
        raw_items = items_r.data or []

        items = []
        for item in raw_items:
            items.append({
                "id": item.get("id"),
                "part_id": item.get("part_id"),
                "name": item.get("name") or item.get("part_name") or item.get("description"),
                "quantity_ordered": item.get("quantity_ordered"),
                "quantity_received": item.get("quantity_received", 0),
                "unit_price": item.get("unit_price"),
                "currency": item.get("currency"),
            })

        return {
            "id": data.get("id"),
            "po_number": data.get("po_number"),
            "status": data.get("status"),
            "supplier_name": data.get("supplier_name") or data.get("vendor_name"),
            "order_date": data.get("order_date") or data.get("created_at"),
            "expected_delivery": data.get("expected_delivery") or data.get("expected_delivery_date"),
            "total_amount": data.get("total_amount") or data.get("total"),
            "currency": data.get("currency", "USD"),
            "notes": data.get("notes"),
            "items": items,
            "created_at": data.get("created_at"),
            "yacht_id": data.get("yacht_id"),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch purchase_order {po_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
```

---

## Role-Gated Actions

(From lens_matrix.json — purchase_order lens actions)
ALL roles: create_purchase_order, update_purchase_order, add_item_to_purchase_order
HOD (chief_engineer/captain/manager): approve_purchase_order, send_purchase_order, receive_purchase_order, cancel_purchase_order

---

## Success Criteria

200 + `id`, `po_number`, `status` non-null. `items` array present (may be empty).
