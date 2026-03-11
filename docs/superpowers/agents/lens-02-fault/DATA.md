# DATA AGENT — Fault Lens

**Your role:** Verify the existing `/v1/entity/fault/{id}` endpoint is correct.

---

## Endpoint

`GET /v1/entity/fault/{fault_id}`
**File:** `apps/api/pipeline_service.py` lines ~904–945
**Status:** ✅ EXISTS — verify shape only.

---

## DB Table (verified)

```
pms_faults:
  id, yacht_id, title, description, severity, equipment_id, equipment_name,
  reported_at, detected_at, reporter, reported_by, status,
  has_work_order, ai_diagnosis, fault_code, created_at, updated_at
```

---

## Required Response Shape

```json
{
  "id": "uuid",
  "title": "Fuel leak at injector #3",
  "description": "...",
  "severity": "major",
  "equipment_id": "uuid",
  "equipment_name": "Main Engine",
  "reported_at": "2026-03-10T09:00:00Z",
  "reporter": "John Smith",
  "status": "open",
  "has_work_order": false,
  "ai_diagnosis": null,
  "created_at": "2026-03-10T09:00:00Z"
}
```

**Column fallbacks in code:**
- `reported_at` = `data.get('reported_at') or data.get('detected_at')`
- `reporter` = `data.get('reporter') or data.get('reported_by', 'System')`

---

## Role-Gated Actions

ALL roles: report_fault, add_fault_photo, add_fault_note
HOD only: acknowledge_fault, close_fault, update_fault, diagnose_fault, reopen_fault, mark_fault_false_alarm

---

## Success Criteria

Response is 200 + `id`, `title`, `severity`, `status` are non-null.
