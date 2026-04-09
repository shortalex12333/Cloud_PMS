# DATA AGENT — Work Order Lens

**Your role:** Verify the existing `/v1/entity/work_order/{id}` endpoint returns the correct shape. If it drifts from the spec, fix it.

---

## Endpoint

`GET /v1/entity/work_order/{work_order_id}`
**File:** `apps/api/pipeline_service.py` lines ~1057–1190
**Status:** ✅ EXISTS — verify it, don't rebuild it.

---

## DB Tables (verified column names)

```
pms_work_orders:
  id, yacht_id, wo_number, title, description, status, priority, type,
  equipment_id, equipment_name, assigned_to, assigned_to_name,
  due_date, completed_at, completed_by, fault_id, created_at, updated_at

pms_work_order_notes (join on work_order_id):
  id, note_text, note_type, created_by, created_at

pms_work_order_parts (join on work_order_id):
  id, part_id, quantity, notes
  + pms_parts(id, name, part_number, location)

pms_work_order_checklist (join on work_order_id):
  id, title, is_completed, completed_by, sequence

pms_audit_log (join on entity_type='work_order', entity_id=wo_id):
  id, action, old_values, new_values, user_id, created_at
```

---

## Required Response Shape

```json
{
  "id": "uuid",
  "wo_number": "WO-001",
  "title": "Replace oil filter",
  "description": "...",
  "status": "in_progress",
  "priority": "urgent",
  "type": "corrective",
  "equipment_id": "uuid",
  "equipment_name": "Main Engine",
  "assigned_to": "uuid",
  "assigned_to_name": "John Smith",
  "due_date": "2026-03-15",
  "completed_at": null,
  "fault_id": null,
  "notes": [],
  "parts": [],
  "checklist": [],
  "audit_history": [],
  "notes_count": 0,
  "parts_count": 0,
  "checklist_count": 0,
  "checklist_completed": 0,
  "available_actions": []
}
```

---

## Role-Gated Actions

ALL roles: create, update, add_note, add_part, mark_complete (signed), schedule, set_priority, attach_photo, attach_document
HOD only (chief_engineer/captain/manager): assign, close

---

## Success Criteria

Response is 200 + these fields are non-null: `id`, `title`, `status`
Arrays (`notes`, `parts`, `checklist`) must be present even if empty `[]`.
