# DATA AGENT — Warranty Lens

**Your role:** IMPLEMENT `GET /v1/entity/warranty/{id}` in `apps/api/routes/entity_routes.py`.
This endpoint does NOT exist yet. You must create it.

---

## Endpoint to create

`GET /v1/entity/warranty/{warranty_id}`
**File to modify:** `apps/api/routes/entity_routes.py` (create if not exists)
**Mount in:** `apps/api/pipeline_service.py` (add import + `app.include_router(entity_routes_router)`)

---

## DB Table

```
pms_warranties (columns — use SELECT * to discover exact names):
  id                uuid        NOT NULL
  yacht_id          uuid        NOT NULL
  warranty_number   text        nullable   e.g. "WRN-2024-001"
  equipment_id      uuid        nullable
  equipment_name    text        nullable
  supplier_name     text        nullable   (may also be "supplier")
  start_date        date        nullable
  expiry_date       date        nullable   (may also be "end_date")
  status            text        NOT NULL   "active","expired","claimed","void"
  coverage_details  text        nullable   (may also be "coverage")
  terms_conditions  text        nullable   (may also be "terms")
  created_at        timestamptz NOT NULL
```

**Column name uncertainty:** Use `.get()` with fallbacks for variant column names.
`supplier` = try `supplier_name` first, then `supplier`.
`expiry_date` = try `expiry_date` first, then `end_date`.
`coverage` = try `coverage_details` first, then `coverage`.
`terms` = try `terms_conditions` first, then `terms`.

---

## Required Response Shape

```json
{
  "id": "uuid",
  "title": "WRN-2024-001",
  "warranty_number": "WRN-2024-001",
  "equipment_id": "uuid",
  "equipment_name": "Main Engine",
  "supplier": "CAT Marine",
  "start_date": "2024-01-15",
  "expiry_date": "2026-01-15",
  "status": "active",
  "coverage": "Parts and labour for engine defects",
  "terms": "Annual service required to maintain warranty",
  "created_at": "...",
  "yacht_id": "uuid"
}
```

**Mapping:**
- `title` ← `warranty_number` → `id[:8]` if null
- `supplier` ← `supplier_name` or `supplier`
- `expiry_date` ← `expiry_date` or `end_date`
- `coverage` ← `coverage_details` or `coverage`
- `terms` ← `terms_conditions` or `terms`

---

## Implementation Template

```python
@router.get("/v1/entity/warranty/{warranty_id}")
async def get_warranty_entity(warranty_id: str, auth: dict = Depends(get_authenticated_user)):
    try:
        yacht_id = auth['yacht_id']
        tenant_key = auth['tenant_key_alias']
        supabase = get_tenant_client(tenant_key)

        r = supabase.table("pms_warranties").select("*") \
            .eq("id", warranty_id) \
            .eq("yacht_id", yacht_id) \
            .maybe_single().execute()

        if not r.data:
            raise HTTPException(status_code=404, detail="Warranty not found")

        data = r.data
        warranty_number = data.get("warranty_number")
        title = warranty_number or (data.get("id", "")[:8] if data.get("id") else "Warranty")

        return {
            "id": data.get("id"),
            "title": title,
            "warranty_number": warranty_number,
            "equipment_id": data.get("equipment_id"),
            "equipment_name": data.get("equipment_name"),
            "supplier": data.get("supplier_name") or data.get("supplier"),
            "start_date": data.get("start_date"),
            "expiry_date": data.get("expiry_date") or data.get("end_date"),
            "status": data.get("status"),
            "coverage": data.get("coverage_details") or data.get("coverage"),
            "terms": data.get("terms_conditions") or data.get("terms"),
            "created_at": data.get("created_at"),
            "yacht_id": data.get("yacht_id"),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch warranty {warranty_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
```

---

## Role-Gated Actions

HOD only (chief_engineer/captain/manager): create_warranty, update_warranty, claim_warranty, link_document_to_warranty, extend_warranty
Manager only: void_warranty

---

## Success Criteria

200 + `id`, `title` (warranty_number), `status` non-null.
