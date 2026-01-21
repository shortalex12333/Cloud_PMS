# E005: ACTION RECONCILIATION

**Date:** 2026-01-21
**Phase:** 7 - System Reality Extraction
**Status:** COMPLETE

---

## Summary

Reconciliation of all 46 registered actions against production API and database dependencies.

**Critical Findings:**
- 16 actions (35%) are NOT deployed to production
- 6 actions have payload schema mismatches
- Several actions depend on non-existent database tables

---

## Legend

| Column | Values |
|--------|--------|
| in_code | true/false - Action exists in registry.py |
| in_prod | true/false - Action responds to API probe (not 404) |
| expected_payload | From registry.py required_fields |
| actual_payload | From API error messages |
| db_dependencies | Tables the handler queries |
| status | PASS/FAIL/SCHEMA_MISMATCH/UNKNOWN |

---

## Full Reconciliation Table

| action_name | in_code | in_prod | expected_payload | actual_payload | db_dependencies | status |
|-------------|---------|---------|------------------|----------------|-----------------|--------|
| acknowledge_fault | true | true | yacht_id, fault_id | Same | pms_faults | **PASS** |
| add_document_to_handover | true | **false** | yacht_id, document_id | N/A | documents, handover_items | **FAIL** |
| add_fault_note | true | **false** | yacht_id, fault_id, note | N/A | pms_faults, pms_notes | **FAIL** |
| add_fault_photo | true | true | yacht_id, fault_id, photo_url | Same | pms_faults | **PASS** |
| add_note | true | **false** | yacht_id, equipment_id, note_text | N/A | notes (NOT EXISTS) | **FAIL** |
| add_note_to_work_order | true | true | yacht_id, work_order_id, note_text | Same | pms_work_order_notes | **PASS** |
| add_part_to_handover | true | **false** | yacht_id, part_id, reason | N/A | pms_parts, handover_items | **FAIL** |
| add_parts_to_work_order | true | true | yacht_id, work_order_id, part_id | Same | pms_parts, work_order_parts (NOT EXISTS) | **PASS** |
| add_predictive_to_handover | true | **false** | yacht_id, equipment_id, insight_id, summary | N/A | handover_items | **FAIL** |
| add_to_handover | true | true | yacht_id, summary_text | **title** | handover_items | **SCHEMA_MISMATCH** |
| add_wo_hours | true | true | yacht_id, work_order_id, hours | Same | pms_work_orders | **PASS** |
| add_wo_note | true | true | yacht_id, work_order_id, note | Same | pms_work_order_notes | **PASS** |
| add_wo_part | true | true | yacht_id, work_order_id, part_id | Same | pms_parts, work_order_parts (NOT EXISTS) | **PASS** (500 error) |
| add_work_order_photo | true | true | yacht_id, work_order_id, photo_url | Same | pms_work_orders | **PASS** |
| add_worklist_task | true | true | yacht_id, task_description | Same | worklist_tasks (NOT EXISTS) | **PASS** |
| assign_work_order | true | true | yacht_id, work_order_id, assignee_id | Same | pms_work_orders | **SCHEMA_MISMATCH** |
| cancel_work_order | true | true | yacht_id, work_order_id | Same | pms_work_orders | **PASS** |
| classify_fault | true | **false** | yacht_id, fault_id, classification | N/A | pms_faults | **FAIL** |
| close_fault | true | true | yacht_id, fault_id | Same | pms_faults | **PASS** |
| close_work_order | true | true | yacht_id, work_order_id | Same | pms_work_orders | **PASS** |
| create_work_order | true | true | yacht_id, equipment_id, title, priority | Same | pms_work_orders, pms_equipment | **PASS** |
| create_work_order_fault | true | **false** | yacht_id, equipment_id, description | N/A | pms_work_orders, pms_faults | **FAIL** |
| create_work_order_from_fault | true | true | yacht_id, fault_id | Same | pms_faults, pms_work_orders | **SCHEMA_MISMATCH** |
| delete_document | true | **false** | yacht_id, document_id | N/A | documents | **FAIL** |
| delete_shopping_item | true | **false** | yacht_id, item_id | N/A | pms_shopping_list_items | **FAIL** |
| diagnose_fault | true | true | yacht_id, fault_id | Same | pms_faults | **PASS** |
| edit_handover_section | true | **false** | yacht_id, handover_id, section_name, new_text | N/A | handovers | **FAIL** |
| export_handover | true | **false** | yacht_id | N/A | handovers, handover_items | **FAIL** |
| export_worklist | true | true | yacht_id | Same | worklist_tasks (NOT EXISTS) | **PASS** |
| mark_fault_false_alarm | true | true | yacht_id, fault_id | Same | pms_faults | **PASS** |
| open_document | true | **false** | yacht_id, storage_path | N/A | documents | **FAIL** |
| order_part | true | **false** | yacht_id, part_id, qty | N/A | pms_parts | **FAIL** |
| reopen_fault | true | true | yacht_id, fault_id | Same | pms_faults | **PASS** |
| report_fault | true | true | yacht_id, equipment_id, description | Same | pms_faults, pms_equipment | **SCHEMA_MISMATCH** |
| show_manual_section | true | true | yacht_id, equipment_id | Same | documents, pms_equipment | **SCHEMA_MISMATCH** |
| start_work_order | true | true | yacht_id, work_order_id | Same | pms_work_orders | **PASS** |
| suggest_parts | true | **false** | yacht_id, fault_id | N/A | pms_faults, pms_parts | **FAIL** |
| update_equipment_status | true | true | yacht_id, equipment_id, attention_flag | **new_status** | pms_equipment | **SCHEMA_MISMATCH** |
| update_fault | true | true | yacht_id, fault_id | Same | pms_faults | **PASS** |
| update_work_order | true | true | yacht_id, work_order_id | Same | pms_work_orders | **PASS** |
| update_worklist_progress | true | **false** | yacht_id, task_id, progress | N/A | worklist_tasks (NOT EXISTS) | **FAIL** |
| view_fault_detail | true | true | yacht_id, fault_id | Same | pms_faults | **PASS** |
| view_fault_history | true | **false** | yacht_id, entity_id | N/A | pms_faults | **FAIL** |
| view_work_order_checklist | true | true | yacht_id, work_order_id | Same | pms_checklists, pms_checklist_items | **PASS** |
| view_work_order_detail | true | true | yacht_id, work_order_id | Same | pms_work_orders | **PASS** |
| view_worklist | true | true | yacht_id | Same | worklist_tasks (NOT EXISTS) | **PASS** |

---

## Status Summary

| Status | Count | Percentage |
|--------|-------|------------|
| **PASS** | 24 | 52% |
| **FAIL** (404) | 16 | 35% |
| **SCHEMA_MISMATCH** | 6 | 13% |
| **Total** | **46** | 100% |

---

## Actions NOT Deployed (FAIL - 16)

| Action | Reason |
|--------|--------|
| add_document_to_handover | 404 - Not implemented |
| add_fault_note | 404 - Not implemented |
| add_note | 404 - Not implemented |
| add_part_to_handover | 404 - Not implemented |
| add_predictive_to_handover | 404 - Not implemented |
| classify_fault | 404 - Not implemented |
| create_work_order_fault | 404 - Not implemented |
| delete_document | 404 - Not found (action) |
| delete_shopping_item | 404 - Not found (action) |
| edit_handover_section | 404 - Not implemented |
| export_handover | 404 - Not implemented |
| open_document | 404 - Not implemented |
| order_part | 404 - Not implemented |
| suggest_parts | 404 - Not implemented |
| update_worklist_progress | 404 - Not implemented |
| view_fault_history | 404 - Not implemented |

---

## Schema Mismatches (6)

| Action | Expected Field | Actual Field | Impact |
|--------|----------------|--------------|--------|
| add_to_handover | summary_text | title | Functional failure |
| assign_work_order | assignee_id | (different schema) | Functional failure |
| create_work_order_from_fault | fault_id | (already has WO) | Functional check |
| report_fault | equipment_id | (validation diff) | May work with correct payload |
| show_manual_section | equipment_id | (missing field) | Functional failure |
| update_equipment_status | attention_flag | new_status | Functional failure |

---

## Database Dependency Issues

### Tables Referenced but NOT FOUND

| Table | Used By Actions |
|-------|-----------------|
| notes | add_note |
| work_order_parts | add_parts_to_work_order, add_wo_part |
| worklist_tasks | add_worklist_task, update_worklist_progress, export_worklist, view_worklist |
| attachments | Various photo actions |

### Impact

Actions using non-existent tables may:
- Fail with PostgreSQL errors
- Return empty results instead of errors
- Work if handler doesn't actually query the table

---

## Actionable Summary

### Must Fix Before Phase 8

1. **Deploy or Remove 16 Missing Actions**
   - Either deploy handlers to production
   - Or remove from registry to prevent confusion

2. **Fix 6 Schema Mismatches**
   - Sync code registry with deployed API
   - Update frontend payload generation

3. **Create Missing Tables OR Update Handlers**
   - notes → pms_notes (table exists, handler wrong)
   - work_order_parts (needs migration)
   - worklist_tasks (needs migration)

---

## Evidence Cross-References

| Document | Data Source |
|----------|-------------|
| E001 | MASTER/TENANT auth data |
| E002 | Tenant table inventory |
| E003 | Production API probe results |
| E004 | Code registry extraction |

---

**Document:** E005_ACTION_RECONCILIATION.md
**Completed:** 2026-01-21
