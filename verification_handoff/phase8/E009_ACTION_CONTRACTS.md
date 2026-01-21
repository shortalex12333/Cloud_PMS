# E009: ACTION CONTRACTS (FROZEN)

**Date:** 2026-01-21
**Phase:** 8 - Convergence
**Status:** COMPLETE

---

## Summary

Canonical payload contracts for all 30 production-verified actions.
Contracts locked against production API probing on 2026-01-21.

**Source of Truth:** Production API (`pipeline-core.int.celeste7.ai`)

---

## Schema Fixes Applied

| Action | Old Field | New Field | Reason |
|--------|-----------|-----------|--------|
| add_to_handover | summary_text | title | Prod requires `title` |
| update_equipment_status | attention_flag | new_status | Prod requires `new_status` |
| assign_work_order | assignee_id | assigned_to | Prod requires `assigned_to` |
| add_wo_note | note | note_text | Prod requires `note_text` |

---

## Frozen Contract Table (30 Actions)

| action | required_payload | response_format | side_effect |
|--------|------------------|-----------------|-------------|
| **NOTES (1)** |
| add_note_to_work_order | yacht_id, work_order_id, note_text | {status, note_id} | INSERT pms_work_order_notes |
| **WORK ORDERS (14)** |
| create_work_order | yacht_id, equipment_id, title, priority | {status, work_order_id} | INSERT pms_work_orders |
| close_work_order | yacht_id, work_order_id | {status} | UPDATE pms_work_orders.status='closed' |
| add_work_order_photo | yacht_id, work_order_id, photo_url | {status, photo_id} | INSERT attachment record |
| add_parts_to_work_order | yacht_id, work_order_id, part_id | {status} | Link part to work order |
| view_work_order_checklist | yacht_id, work_order_id | {checklist_items[]} | READ pms_checklists |
| assign_work_order | yacht_id, work_order_id, **assigned_to** | {status} | UPDATE pms_work_orders.assigned_to |
| update_work_order | yacht_id, work_order_id, [fields] | {status} | UPDATE pms_work_orders |
| add_wo_hours | yacht_id, work_order_id, hours | {status} | UPDATE pms_work_orders.hours |
| add_wo_part | yacht_id, work_order_id, part_id | {status} | Link part to work order |
| add_wo_note | yacht_id, work_order_id, **note_text** | {status, note_id} | INSERT pms_work_order_notes |
| start_work_order | yacht_id, work_order_id | {status} | UPDATE pms_work_orders.status='in_progress' |
| cancel_work_order | yacht_id, work_order_id | {status} | UPDATE pms_work_orders.status='cancelled' |
| view_work_order_detail | yacht_id, work_order_id | {work_order} | READ pms_work_orders |
| create_work_order_from_fault | yacht_id, fault_id | {status, work_order_id} | INSERT pms_work_orders, UPDATE pms_faults |
| **EQUIPMENT (1)** |
| update_equipment_status | yacht_id, equipment_id, **new_status** | {status} | UPDATE pms_equipment.status |
| **HANDOVER (1)** |
| add_to_handover | yacht_id, **title** | {status, item_id} | INSERT handover_items |
| **FAULTS (10)** |
| report_fault | yacht_id, equipment_id, description | {status, fault_id} | INSERT pms_faults |
| acknowledge_fault | yacht_id, fault_id | {status} | UPDATE pms_faults.acknowledged=true |
| close_fault | yacht_id, fault_id | {status} | UPDATE pms_faults.status='closed' |
| update_fault | yacht_id, fault_id, [fields] | {status} | UPDATE pms_faults |
| add_fault_photo | yacht_id, fault_id, photo_url | {status, photo_id} | INSERT attachment record |
| view_fault_detail | yacht_id, fault_id | {fault} | READ pms_faults |
| diagnose_fault | yacht_id, fault_id | {diagnosis} | AI analysis of fault |
| reopen_fault | yacht_id, fault_id | {status} | UPDATE pms_faults.status='open' |
| mark_fault_false_alarm | yacht_id, fault_id | {status} | UPDATE pms_faults.is_false_alarm=true |
| show_manual_section | yacht_id, equipment_id | {manual_content} | READ documents |
| **WORKLIST (3)** |
| view_worklist | yacht_id | {tasks[]} | READ worklist_tasks |
| add_worklist_task | yacht_id, task_description | {status, task_id} | INSERT worklist_tasks |
| export_worklist | yacht_id | {export_url} | Generate export file |

---

## Contract Verification Evidence

### Probing Results (2026-01-21)

```
[1] add_to_handover
    summary_text → 400 (Missing: title)
    title → 200 ✓

[2] update_equipment_status
    attention_flag → 400 (Missing: new_status)
    new_status → 200 ✓

[3] assign_work_order
    assignee_id → 400 (Missing: assigned_to)
    assigned_to → CONFIRMED

[4] report_fault → 200 ✓ (no change needed)

[5] show_manual_section → 400 "No manual available" (data issue, not schema)

[6] create_work_order_from_fault → 200 ✓ (no change needed)
```

---

## Registry Changes

**File:** `apps/api/action_router/registry.py`

```diff
- required_fields=["yacht_id", "summary_text"],
+ required_fields=["yacht_id", "title"],

- required_fields=["yacht_id", "equipment_id", "attention_flag"],
+ required_fields=["yacht_id", "equipment_id", "new_status"],

- required_fields=["yacht_id", "work_order_id", "assignee_id"],
+ required_fields=["yacht_id", "work_order_id", "assigned_to"],
```

---

## Frontend Impact

The following frontend files must update their payload generation:

| File | Action | Old Field | New Field |
|------|--------|-----------|-----------|
| HandoverStatusModule.tsx | add_to_handover | summary_text | title |
| EquipmentCard.tsx | update_equipment_status | attention_flag | new_status |
| WorkOrderAssignModal.tsx | assign_work_order | assignee_id | assigned_to |

---

## Contract Enforcement Rules

1. **All payloads MUST include yacht_id** - Enforced by RLS
2. **Field names are EXACT** - No aliases, no fallbacks
3. **Missing required field = 400** - Immediate rejection
4. **Extra fields are ignored** - But not recommended
5. **Production is truth** - Code bends to prod, not vice versa

---

**Document:** E009_ACTION_CONTRACTS.md
**Completed:** 2026-01-21
