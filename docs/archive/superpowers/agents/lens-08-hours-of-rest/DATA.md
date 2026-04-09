# DATA AGENT — Hours of Rest Lens

**Your role:** IMPLEMENT `GET /v1/entity/hours_of_rest/{id}` in `apps/api/routes/entity_routes.py`.
This endpoint does NOT exist yet. You must create it.

---

## Endpoint to create

`GET /v1/entity/hours_of_rest/{record_id}`
**File to modify:** `apps/api/routes/entity_routes.py` (create if not exists)
**Mount in:** `apps/api/pipeline_service.py` (add import + `app.include_router(entity_routes_router)`)

---

## DB Table (EXACT column names)

```
pms_hours_of_rest (14 columns):
  id                       uuid        NOT NULL
  yacht_id                 uuid        NOT NULL
  user_id                  uuid        NOT NULL   crew member UUID
  record_date              date        NOT NULL
  rest_periods             jsonb       nullable   [{start:"HH:MM",end:"HH:MM",hours:float}]
  total_rest_hours         numeric     nullable
  total_work_hours         numeric     nullable
  is_daily_compliant       boolean     nullable
  is_weekly_compliant      boolean     nullable
  weekly_rest_hours        numeric     nullable
  daily_compliance_notes   text        nullable
  weekly_compliance_notes  text        nullable
  created_at               timestamptz NOT NULL
  updated_at               timestamptz nullable
```

**rest_periods note:** Stored as jsonb but may arrive as a string. Use `json.loads()` if isinstance str.
**crew_name:** Not stored in this table. Return `user_id` as `crew_member_id`; `crew_name` defaults to null (join is future work).
**status:** Derive from `is_daily_compliant` → `'compliant'` if True, `'non_compliant'` if False, `'unknown'` if null.

---

## Required Response Shape

```json
{
  "id": "uuid",
  "crew_member_id": "uuid",
  "crew_name": null,
  "date": "2026-03-10",
  "total_rest_hours": 8.5,
  "total_work_hours": 15.5,
  "is_compliant": true,
  "status": "compliant",
  "weekly_rest_hours": 77.0,
  "daily_compliance_notes": null,
  "weekly_compliance_notes": null,
  "rest_periods": [
    {"start": "22:00", "end": "06:00", "hours": 8.0},
    {"start": "14:00", "end": "14:30", "hours": 0.5}
  ],
  "yacht_id": "uuid",
  "created_at": "...",
  "updated_at": "..."
}
```

---

## Implementation Template

```python
@router.get("/v1/entity/hours_of_rest/{record_id}")
async def get_hours_of_rest_entity(record_id: str, auth: dict = Depends(get_authenticated_user)):
    try:
        yacht_id = auth['yacht_id']
        tenant_key = auth['tenant_key_alias']
        supabase = get_tenant_client(tenant_key)

        r = supabase.table("pms_hours_of_rest").select("*") \
            .eq("id", record_id) \
            .eq("yacht_id", yacht_id) \
            .maybe_single().execute()

        if not r.data:
            raise HTTPException(status_code=404, detail="Hours of rest record not found")

        data = r.data
        rest_periods = data.get("rest_periods") or []
        if isinstance(rest_periods, str):
            import json as _j
            rest_periods = _j.loads(rest_periods) if rest_periods else []

        is_daily = data.get("is_daily_compliant")
        if is_daily is True:
            status = "compliant"
        elif is_daily is False:
            status = "non_compliant"
        else:
            status = "unknown"

        return {
            "id": data.get("id"),
            "crew_member_id": data.get("user_id"),
            "crew_name": None,
            "date": data.get("record_date"),
            "total_rest_hours": data.get("total_rest_hours"),
            "total_work_hours": data.get("total_work_hours"),
            "is_compliant": data.get("is_daily_compliant"),
            "status": status,
            "weekly_rest_hours": data.get("weekly_rest_hours"),
            "daily_compliance_notes": data.get("daily_compliance_notes"),
            "weekly_compliance_notes": data.get("weekly_compliance_notes"),
            "rest_periods": rest_periods,
            "yacht_id": data.get("yacht_id"),
            "created_at": data.get("created_at"),
            "updated_at": data.get("updated_at"),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch hours_of_rest {record_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
```

---

## Role-Gated Actions

ALL roles: log_hours_of_rest, upsert_hours_of_rest, create_crew_template, apply_crew_template, acknowledge_warning, sign_monthly_signoff (requires signature)
HOD (chief_engineer/captain/manager): create_monthly_signoff, dismiss_warning

---

## Success Criteria

200 + `id`, `date`, `total_rest_hours`, `is_compliant` non-null.
