# DATA AGENT — Equipment Lens

**Your role:** Verify the existing `/v1/entity/equipment/{id}` endpoint is correct.

---

## Endpoint

`GET /v1/entity/equipment/{equipment_id}`
**File:** `apps/api/pipeline_service.py` lines ~1187–1234
**Status:** ✅ EXISTS — verify shape only.

---

## DB Table (verified)

```
pms_equipment:
  id, yacht_id, name, manufacturer, model, serial_number, location,
  status, category, install_date, last_service_date, running_hours,
  risk_score, created_at, updated_at
```

---

## Required Response Shape

```json
{
  "id": "uuid",
  "name": "Main Engine",
  "manufacturer": "MAN",
  "model": "D2862 LE428",
  "serial_number": "12345",
  "location": "Engine Room",
  "status": "operational",
  "category": "propulsion",
  "install_date": "2020-06-01",
  "last_service_date": "2025-11-15",
  "running_hours": 4200,
  "risk_score": 0.3,
  "created_at": "...",
  "updated_at": "..."
}
```

---

## Role-Gated Actions

ALL roles: update_running_hours, log_contractor_work, link_document_to_equipment
HOD only: update_equipment, set_equipment_status

`set_equipment_status` flow: operational ↔ out_of_service ↔ maintenance → decommissioned (terminal)

---

## Success Criteria

200 + `id`, `name`, `status` non-null.
