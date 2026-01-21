# E004: CODE REGISTRY REALITY

**Date:** 2026-01-21
**Phase:** 7 - System Reality Extraction
**Status:** COMPLETE

---

## Summary

Extracted all action definitions from the code registry with required fields and handler types.

**Source File:** `apps/api/action_router/registry.py`
**Total Actions:** 46

---

## Action Registry

### Notes Actions (Lines 51-71)

| Action | Handler | Required Fields |
|--------|---------|-----------------|
| add_note | INTERNAL | yacht_id, equipment_id, note_text |
| add_note_to_work_order | INTERNAL | yacht_id, work_order_id, note_text |

### Work Order Actions (Lines 76-107, 402-554)

| Action | Handler | Required Fields |
|--------|---------|-----------------|
| create_work_order | N8N | yacht_id, equipment_id, title, priority |
| create_work_order_fault | N8N | yacht_id, equipment_id, description |
| close_work_order | INTERNAL | yacht_id, work_order_id |
| add_work_order_photo | INTERNAL | yacht_id, work_order_id, photo_url |
| add_parts_to_work_order | INTERNAL | yacht_id, work_order_id, part_id |
| view_work_order_checklist | INTERNAL | yacht_id, work_order_id |
| assign_work_order | INTERNAL | yacht_id, work_order_id, assignee_id |
| update_work_order | INTERNAL | yacht_id, work_order_id |
| add_wo_hours | INTERNAL | yacht_id, work_order_id, hours |
| add_wo_part | INTERNAL | yacht_id, work_order_id, part_id |
| add_wo_note | INTERNAL | yacht_id, work_order_id, note |
| start_work_order | INTERNAL | yacht_id, work_order_id |
| cancel_work_order | INTERNAL | yacht_id, work_order_id |
| view_work_order_detail | INTERNAL | yacht_id, work_order_id |
| create_work_order_from_fault | INTERNAL | yacht_id, fault_id |

### Equipment Actions (Lines 112-121)

| Action | Handler | Required Fields |
|--------|---------|-----------------|
| update_equipment_status | INTERNAL | yacht_id, equipment_id, attention_flag |

### Handover Actions (Lines 126-190)

| Action | Handler | Required Fields |
|--------|---------|-----------------|
| add_to_handover | INTERNAL | yacht_id, summary_text |
| add_document_to_handover | N8N | yacht_id, document_id |
| add_part_to_handover | N8N | yacht_id, part_id, reason |
| add_predictive_to_handover | N8N | yacht_id, equipment_id, insight_id, summary |
| edit_handover_section | INTERNAL | yacht_id, handover_id, section_name, new_text |
| export_handover | N8N | yacht_id |

### Document Actions (Lines 196-216)

| Action | Handler | Required Fields |
|--------|---------|-----------------|
| open_document | INTERNAL | yacht_id, storage_path |
| delete_document | INTERNAL | yacht_id, document_id |

### Shopping/Inventory Actions (Lines 221-244)

| Action | Handler | Required Fields |
|--------|---------|-----------------|
| delete_shopping_item | INTERNAL | yacht_id, item_id |
| order_part | N8N | yacht_id, part_id, qty |

### Fault Actions (Lines 249-397)

| Action | Handler | Required Fields |
|--------|---------|-----------------|
| report_fault | INTERNAL | yacht_id, equipment_id, description |
| classify_fault | INTERNAL | yacht_id, fault_id, classification |
| acknowledge_fault | INTERNAL | yacht_id, fault_id |
| close_fault | INTERNAL | yacht_id, fault_id |
| update_fault | INTERNAL | yacht_id, fault_id |
| add_fault_photo | INTERNAL | yacht_id, fault_id, photo_url |
| view_fault_detail | INTERNAL | yacht_id, fault_id |
| diagnose_fault | INTERNAL | yacht_id, fault_id |
| reopen_fault | INTERNAL | yacht_id, fault_id |
| mark_fault_false_alarm | INTERNAL | yacht_id, fault_id |
| view_fault_history | INTERNAL | yacht_id, entity_id |
| suggest_parts | INTERNAL | yacht_id, fault_id |
| show_manual_section | INTERNAL | yacht_id, equipment_id |
| add_fault_note | INTERNAL | yacht_id, fault_id, note |

### Worklist Actions (Lines 515-553)

| Action | Handler | Required Fields |
|--------|---------|-----------------|
| view_worklist | INTERNAL | yacht_id |
| add_worklist_task | INTERNAL | yacht_id, task_description |
| update_worklist_progress | INTERNAL | yacht_id, task_id, progress |
| export_worklist | INTERNAL | yacht_id |

---

## Handler Type Distribution

| Handler Type | Count | Percentage |
|--------------|-------|------------|
| INTERNAL | 39 | 85% |
| N8N | 7 | 15% |

### N8N Handler Actions (External)

These actions route to external n8n workflows:

1. `create_work_order` (line 76)
2. `create_work_order_fault` (line 87)
3. `add_document_to_handover` (line 137)
4. `add_part_to_handover` (line 148)
5. `add_predictive_to_handover` (line 159)
6. `export_handover` (line 181)
7. `order_part` (line 235)

---

## Required Fields Analysis

### Always Required: `yacht_id`

All 46 actions require `yacht_id` in their required_fields. This enables tenant isolation at the validation layer.

### Common Entity IDs

| Field | Actions Using |
|-------|---------------|
| work_order_id | 13 actions |
| fault_id | 14 actions |
| equipment_id | 7 actions |
| document_id | 2 actions |
| part_id | 4 actions |

---

## Validator Logic

**File:** `apps/api/action_router/router.py`
**Line:** 105-120

```python
# Required fields check
missing = []
for field in action.required_fields:
    if field == "yacht_id":
        if not context.get("yacht_id"):
            missing.append("yacht_id")
    elif field not in payload:
        missing.append(field)

if missing:
    return JSONResponse(
        status_code=400,
        content={"detail": {"message": f"Missing required field(s): {', '.join(missing)}"}}
    )
```

---

## Schema Files Referenced

| Action | Schema File | Exists |
|--------|-------------|--------|
| add_note | add_note.json | UNKNOWN |
| add_note_to_work_order | add_note_to_work_order.json | UNKNOWN |
| create_work_order | create_work_order.json | UNKNOWN |
| create_work_order_fault | create_work_order_fault.json | UNKNOWN |
| close_work_order | close_work_order.json | UNKNOWN |
| add_document_to_handover | add_document_to_handover.json | UNKNOWN |
| add_part_to_handover | add_part_to_handover.json | UNKNOWN |
| add_predictive_to_handover | add_predictive_to_handover.json | UNKNOWN |
| edit_handover_section | edit_handover_section.json | UNKNOWN |
| export_handover | export_handover.json | UNKNOWN |
| open_document | open_document.json | UNKNOWN |
| order_part | order_part.json | UNKNOWN |

**Note:** Schema files are referenced but their usage for validation is unclear from code inspection.

---

## Code References

| Component | File | Line |
|-----------|------|------|
| ACTION_REGISTRY | registry.py | 47-554 |
| ActionDefinition class | registry.py | 19-40 |
| HandlerType enum | registry.py | 13-16 |
| get_action() | registry.py | 557-567 |
| validate_action_exists() | registry.py | 584-586 |
| Validation logic | router.py | 105-120 |
| Handler dispatch | internal_dispatcher.py | 1-2000+ |

---

## Evidence Files

| File | Description |
|------|-------------|
| Tool result file | Full registry.py contents |

---

**Document:** E004_CODE_REGISTRY_TRUTH.md
**Completed:** 2026-01-21
