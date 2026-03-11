# DATA AGENT — Shopping List Lens

**Your role:** IMPLEMENT `GET /v1/entity/shopping_list/{id}` in `apps/api/routes/entity_routes.py`.
This endpoint does NOT exist yet. You must create it.

---

## Endpoint to create

`GET /v1/entity/shopping_list/{item_id}`
**File to modify:** `apps/api/routes/entity_routes.py` (create if not exists)
**Mount in:** `apps/api/pipeline_service.py` (add import + `app.include_router(entity_routes_router)`)

---

## DB Table (EXACT column names)

```
pms_shopping_list_items (columns):
  id                         uuid        NOT NULL
  yacht_id                   uuid        NOT NULL
  part_name                  text        NOT NULL   the display name / title
  part_number                text        nullable
  manufacturer               text        nullable
  unit                       text        nullable   e.g. "each", "litre"
  quantity_requested         numeric     NOT NULL
  urgency                    text        nullable   "low", "medium", "high", "critical"
  status                     text        NOT NULL   "pending", "approved", "ordered", "received", "rejected"
  source_type                text        nullable   "manual", "ai_candidate", "work_order"
  required_by_date           date        nullable
  created_by                 uuid        nullable   user UUID who requested
  created_at                 timestamptz NOT NULL
  rejected_at                timestamptz nullable
  is_candidate_part          boolean     nullable   true if AI-suggested candidate
  candidate_promoted_to_part_id uuid     nullable   filled when promoted to real part
```

**CRITICAL NOTE:** The search result `object_id` IS a single `pms_shopping_list_items.id`.
This endpoint fetches ONE item and wraps it in `items: [item]` array for the component.

---

## Required Response Shape

```json
{
  "id": "uuid",
  "title": "Hydraulic Filter HF-220",
  "status": "pending",
  "requester_id": "uuid",
  "requester_name": null,
  "created_at": "...",
  "items": [
    {
      "id": "uuid",
      "part_name": "Hydraulic Filter HF-220",
      "part_number": "HF-220",
      "manufacturer": "Parker",
      "unit": "each",
      "quantity_requested": 2,
      "urgency": "high",
      "status": "pending",
      "required_by_date": null,
      "is_candidate_part": false
    }
  ],
  "yacht_id": "uuid"
}
```

**Mapping:**
- `title` ← `part_name`
- `requester_id` ← `created_by`
- `requester_name` = null (user lookup is future work)
- `items` = `[this_item]` — single-element array

---

## Implementation Template

```python
@router.get("/v1/entity/shopping_list/{item_id}")
async def get_shopping_list_entity(item_id: str, auth: dict = Depends(get_authenticated_user)):
    try:
        yacht_id = auth['yacht_id']
        tenant_key = auth['tenant_key_alias']
        supabase = get_tenant_client(tenant_key)

        r = supabase.table("pms_shopping_list_items").select("*") \
            .eq("id", item_id) \
            .eq("yacht_id", yacht_id) \
            .maybe_single().execute()

        if not r.data:
            raise HTTPException(status_code=404, detail="Shopping list item not found")

        data = r.data
        item = {
            "id": data.get("id"),
            "part_name": data.get("part_name"),
            "part_number": data.get("part_number"),
            "manufacturer": data.get("manufacturer"),
            "unit": data.get("unit"),
            "quantity_requested": data.get("quantity_requested"),
            "urgency": data.get("urgency"),
            "status": data.get("status"),
            "required_by_date": data.get("required_by_date"),
            "is_candidate_part": data.get("is_candidate_part", False),
        }
        return {
            "id": data.get("id"),
            "title": data.get("part_name"),
            "status": data.get("status"),
            "requester_id": data.get("created_by"),
            "requester_name": None,
            "created_at": data.get("created_at"),
            "items": [item],
            "yacht_id": data.get("yacht_id"),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch shopping_list item {item_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
```

---

## Role-Gated Actions

ALL roles: create_shopping_list_item, update_shopping_list_item, mark_item_received
HOD (chief_engineer/captain/manager): approve_shopping_list_item, reject_shopping_list_item, promote_candidate_to_part, mark_item_ordered

---

## Success Criteria

200 + `id`, `title` (part_name), `status` non-null. `items` array must have exactly 1 element.
