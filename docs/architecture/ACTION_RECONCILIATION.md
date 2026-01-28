# ACTION RECONCILIATION

**Date:** 2026-01-22
**Purpose:** Truth reconciliation between registry, handlers, and documented actions

---

## EXECUTIVE SUMMARY

**Registry Actions:** 71 actions registered in `action_registry.py`
**Implemented Handlers:** ~55 unique handlers across handler files
**Documented in ACTION_IO_MATRIX:** 63 actions

**Status:** Mismatches identified - reconciliation required

---

## SOURCE 1: ACTION REGISTRY (71 actions)

**File:** `/apps/api/actions/action_registry.py`

### Inventory Domain (9 actions)
1. view_inventory_item (READ)
2. view_stock_levels (READ)
3. edit_inventory_quantity (MUTATE)
4. create_reorder (MUTATE)
5. view_part_location (READ)
6. view_part_usage (READ)
7. log_part_usage (MUTATE)
8. add_part (MUTATE)
9. scan_part_barcode (READ)

### Manual/Documentation Domain (2 actions)
10. view_manual_section (READ)
11. view_related_docs (READ)

### Equipment Domain (6 actions)
12. view_equipment (READ)
13. view_maintenance_history (READ)
14. view_equipment_parts (READ)
15. view_linked_faults (READ)
16. view_equipment_manual (READ)
17. add_equipment_note (MUTATE)

### Work Order Domain (11 actions)
18. view_work_order (READ)
19. create_work_order (MUTATE)
20. update_work_order_status (MUTATE)
21. view_work_order_history (READ)
22. mark_work_order_complete (MUTATE)
23. add_work_order_note (MUTATE)
24. add_work_order_photo (MUTATE)
25. add_parts_to_work_order (MUTATE)
26. view_work_order_checklist (READ)
27. assign_work_order (MUTATE)
28. edit_work_order_details (MUTATE)

### Fault Domain (9 actions)
29. view_fault (READ)
30. run_diagnostic (READ)
31. log_symptom (MUTATE)
32. diagnose_fault (READ)
33. report_fault (MUTATE)
34. view_fault_history (READ)
35. suggest_parts (READ)
36. add_fault_note (MUTATE)
37. add_fault_photo (MUTATE)

### Handover Domain (6 actions)
38. add_to_handover (MUTATE)
39. add_document_to_handover (MUTATE)
40. add_predictive_insight_to_handover (MUTATE)
41. edit_handover_section (MUTATE)
42. export_handover (READ)
43. regenerate_handover_summary (MUTATE)

### Hours of Rest Domain (4 actions)
44. view_hours_of_rest (READ)
45. update_hours_of_rest (MUTATE)
46. export_hours_of_rest (READ)
47. view_compliance_status (READ)

### Purchasing Domain (7 actions)
48. create_purchase_request (MUTATE)
49. add_item_to_purchase (MUTATE)
50. approve_purchase (MUTATE)
51. upload_invoice (MUTATE)
52. track_delivery (READ)
53. log_delivery_received (MUTATE)
54. update_purchase_status (MUTATE)

### Checklists Domain (4 actions)
55. view_checklist (READ)
56. mark_checklist_item_complete (MUTATE)
57. add_checklist_note (MUTATE)
58. add_checklist_photo (MUTATE)

### Shipyard/Refit Domain (5 actions)
59. view_worklist (READ)
60. add_worklist_task (MUTATE)
61. update_worklist_progress (MUTATE)
62. export_worklist (READ)
63. tag_for_survey (MUTATE)

### Fleet Domain (3 actions)
64. view_fleet_summary (READ)
65. open_vessel (READ)
66. export_fleet_summary (READ)

### Predictive Domain (2 actions)
67. request_predictive_insight (READ)
68. view_smart_summary (READ)

### Mobile Domain (3 actions)
69. view_attachments (READ)
70. upload_photo (MUTATE)
71. record_voice_note (MUTATE)

---

## SOURCE 2: IMPLEMENTED HANDLERS (~55 unique actions)

**Files:** `/apps/api/handlers/*_handlers.py`

### Equipment Handlers (5 actions)
- view_equipment
- view_maintenance_history
- view_equipment_parts
- view_linked_faults
- view_equipment_manual

### Fault Handlers (5 actions)
- view_fault
- diagnose_fault
- run_diagnostic
- view_fault_history
- suggest_parts

### Work Order Handlers (4 actions)
- view_work_order
- view_work_order_history
- view_work_order_checklist
- open_work_order

### Work Order Mutation Handlers (4 actions)
- create_work_order_from_fault (prefill/preview/execute)
- add_note_to_work_order (prefill/execute)
- add_part_to_work_order (prefill/preview/execute)
- mark_work_order_complete (prefill/preview/execute)

### Handover Handlers (2 actions)
- add_to_handover (prefill/execute)
- [export, edit, etc. missing]

### Inventory Handlers (2 actions)
- check_stock_level (execute)
- log_part_usage (prefill/preview/execute)

### P1 Compliance Handlers (2 actions)
- update_hours_of_rest (execute)
- log_delivery_received (execute)

### P1 Purchasing Handlers (4 actions)
- create_work_order (execute)
- create_purchase_request (execute)
- order_part (execute)
- approve_purchase (execute)

### P2 Mutation Light Handlers (21 actions)
- add_fault_note (execute)
- add_fault_photo (execute)
- add_work_order_note (execute)
- add_work_order_photo (execute)
- assign_work_order (execute)
- add_equipment_note (execute)
- add_document_to_handover (execute)
- edit_handover_section (execute)
- update_purchase_status (execute)
- mark_checklist_item_complete (execute)
- tag_for_survey (execute)
- add_predictive_insight_to_handover (execute)
- regenerate_handover_summary (execute)
- add_item_to_purchase (execute)
- upload_invoice (execute)
- add_checklist_note (execute)
- add_checklist_photo (execute)
- update_worklist_progress (execute)
- upload_photo (execute)
- record_voice_note (execute)
- [1 more]

### P3 Read-Only Handlers (27 actions)
- view_fault_history (execute)
- suggest_parts (execute)
- view_work_order_history (execute)
- view_work_order_checklist (execute)
- view_equipment_details (execute)
- view_equipment_history (execute)
- view_equipment_parts (execute)
- view_linked_faults (execute)
- view_equipment_manual (execute)
- view_part_stock (execute)
- view_part_location (execute)
- view_part_usage (execute)
- scan_part_barcode (execute)
- view_linked_equipment (execute)
- export_handover (execute)
- view_document (execute)
- view_related_documents (execute)
- view_document_section (execute)
- view_hours_of_rest (execute)
- export_hours_of_rest (execute)
- view_compliance_status (execute)
- track_delivery (execute)
- view_checklist (execute)
- view_worklist (execute)
- export_worklist (execute)
- view_fleet_summary (execute)
- open_vessel (execute)
- export_fleet_summary (execute)
- request_predictive_insight (execute)
- view_smart_summary (execute)

### Purchasing Mutation Handlers (2 actions)
- commit_receiving_session (execute)
- add_to_shopping_list (execute)

### List Handlers (4 actions)
- list_work_orders
- list_parts
- list_faults
- list_equipment

### Manual Handlers (1 action)
- show_manual_section (execute)

---

## SOURCE 3: DOCUMENTED IN ACTION_IO_MATRIX (63 actions)

**File:** `docs/architecture/ACTION_IO_MATRIX.md`

### Fault Cluster (9 actions)
1. report_fault
2. acknowledge_fault
3. add_fault_note
4. diagnose_fault
5. create_work_order_from_fault
6. resolve_fault
7. close_fault
8. defer_fault
9. add_to_handover

### Work Order Cluster (10 actions)
10. create_work_order
11. assign_work_order
12. start_work_order
13. add_wo_hours
14. add_wo_note
15. add_wo_part
16. remove_wo_part
17. complete_work_order
18. reopen_work_order
19. cancel_work_order

### Handover Cluster (8 actions)
20. add_to_handover (generic)
21. add_document_to_handover
22. add_document_section_to_handover
23. add_note (general handover)
24. edit_handover_section
25. acknowledge_handover
26. export_handover
27. generate_summary (AI)

### Inventory/Parts Cluster (6 actions)
28. adjust_inventory
29. log_part_usage
30. restock_part
31. add_to_shopping_list
32. remove_from_shopping_list
33. flag_low_stock

### Purchasing Cluster (7 actions)
34. create_purchase_order
35. approve_purchase_order
36. mark_po_ordered
37. receive_items (start session)
38. check_in_item
39. commit_session
40. cancel_session

### Equipment Cluster (6 actions)
41. add_equipment
42. update_equipment
43. change_equipment_status
44. decommission_equipment
45. link_equipment_to_manual
46. view_equipment_history

### Checklist Cluster (5 actions)
47. create_checklist
48. add_checklist_item
49. complete_checklist_item
50. skip_checklist_item
51. complete_checklist

### Document Cluster (3 actions)
52. upload_document
53. link_document_to_equipment
54. search_documents

### Attachment Actions (2 actions)
55. add_photo
56. remove_photo

### Situation Engine Actions (3 actions)
57. detect_symptom_recurrence
58. log_symptom
59. update_predictive_state

### Search & RAG Actions (3 actions)
60. search
61. rag_suggest_action
62. rag_prefill

### Action Execution Logging (1 action)
63. log_action_execution

---

## RECONCILIATION ANALYSIS

### CATEGORY 1: In Registry, Missing from Handlers

**Priority: HIGH - Need Implementation**

1. **edit_inventory_quantity** - Registry ✓ | Handlers ✗ | Docs ⚠️ (as "adjust_inventory")
2. **create_reorder** - Registry ✓ | Handlers ✗ | Docs ⚠️ (as "create_purchase_request")
3. **view_stock_levels** - Registry ✓ | Handlers ✗ | Docs ✗
4. **log_symptom** - Registry ✓ | Handlers ✗ | Docs ✓
5. **report_fault** - Registry ✓ | Handlers ✗ | Docs ✓
6. **update_work_order_status** - Registry ✓ | Handlers ✗ | Docs ✓
7. **edit_work_order_details** - Registry ✓ | Handlers ✗ | Docs ⚠️
8. **add_worklist_task** - Registry ✓ | Handlers ✗ | Docs ✗

**Action:** Implement these handlers OR remove from registry if not MVP.

---

### CATEGORY 2: In Handlers, Missing from Registry

**Priority: MEDIUM - Need Registration**

1. **list_work_orders** - Registry ✗ | Handlers ✓ | Docs ✗
2. **list_parts** - Registry ✗ | Handlers ✓ | Docs ✗
3. **list_faults** - Registry ✗ | Handlers ✓ | Docs ✗
4. **list_equipment** - Registry ✗ | Handlers ✓ | Docs ✗
5. **check_stock_level** - Registry ✗ | Handlers ✓ | Docs ⚠️
6. **order_part** - Registry ✗ | Handlers ✓ | Docs ⚠️
7. **commit_receiving_session** - Registry ✗ | Handlers ✓ | Docs ✓
8. **add_to_shopping_list** - Registry ✗ | Handlers ✓ | Docs ✓
9. **create_work_order_from_fault** - Registry ✗ | Handlers ✓ | Docs ✓
10. **add_note_to_work_order** - Registry ✗ | Handlers ✓ | Docs ⚠️
11. **add_part_to_work_order** - Registry ✗ | Handlers ✓ | Docs ⚠️
12. **view_equipment_details** - Registry ✗ | Handlers ✓ | Docs ⚠️
13. **view_linked_equipment** - Registry ✗ | Handlers ✓ | Docs ✗
14. **view_document** - Registry ✗ | Handlers ✓ | Docs ✗
15. **view_related_documents** - Registry ✗ | Handlers ✓ | Docs ⚠️
16. **view_document_section** - Registry ✗ | Handlers ✓ | Docs ✗
17. **show_manual_section** - Registry ✗ | Handlers ✓ | Docs ⚠️

**Action:** Register these actions in registry OR remove handlers if not needed.

---

### CATEGORY 3: Documented but Missing Both Registry + Handlers

**Priority: LOW - Future/Aspirational**

1. **acknowledge_fault** - Registry ✗ | Handlers ✗ | Docs ✓
2. **resolve_fault** - Registry ✗ | Handlers ✗ | Docs ✓
3. **close_fault** - Registry ✗ | Handlers ✗ | Docs ✓
4. **defer_fault** - Registry ✗ | Handlers ✗ | Docs ✓
5. **start_work_order** - Registry ✗ | Handlers ✗ | Docs ✓
6. **add_wo_hours** - Registry ✗ | Handlers ✗ | Docs ✓
7. **remove_wo_part** - Registry ✗ | Handlers ✗ | Docs ✓
8. **reopen_work_order** - Registry ✗ | Handlers ✗ | Docs ✓
9. **cancel_work_order** - Registry ✗ | Handlers ✗ | Docs ✓
10. **add_document_section_to_handover** - Registry ✗ | Handlers ✗ | Docs ✓
11. **add_note (general handover)** - Registry ✗ | Handlers ✗ | Docs ✓
12. **acknowledge_handover** - Registry ✗ | Handlers ✗ | Docs ✓
13. **generate_summary (AI)** - Registry ✗ | Handlers ✗ | Docs ✓
14. **adjust_inventory** - Registry ✗ | Handlers ✗ | Docs ✓
15. **restock_part** - Registry ✗ | Handlers ✗ | Docs ✓
16. **remove_from_shopping_list** - Registry ✗ | Handlers ✗ | Docs ✓
17. **flag_low_stock** - Registry ✗ | Handlers ✗ | Docs ✓
18. **create_purchase_order** - Registry ✗ | Handlers ✗ | Docs ✓
19. **approve_purchase_order** - Registry ✗ | Handlers ✗ | Docs ✓
20. **mark_po_ordered** - Registry ✗ | Handlers ✗ | Docs ✓
21. **receive_items** - Registry ✗ | Handlers ✗ | Docs ✓
22. **check_in_item** - Registry ✗ | Handlers ✗ | Docs ✓
23. **cancel_session** - Registry ✗ | Handlers ✗ | Docs ✓
24. **add_equipment** - Registry ✗ | Handlers ✗ | Docs ✓
25. **update_equipment** - Registry ✗ | Handlers ✗ | Docs ✓
26. **change_equipment_status** - Registry ✗ | Handlers ✗ | Docs ✓
27. **decommission_equipment** - Registry ✗ | Handlers ✗ | Docs ✓
28. **link_equipment_to_manual** - Registry ✗ | Handlers ✗ | Docs ✓
29. **create_checklist** - Registry ✗ | Handlers ✗ | Docs ✓
30. **add_checklist_item** - Registry ✗ | Handlers ✗ | Docs ✓
31. **complete_checklist_item** - Registry ✗ | Handlers ✗ | Docs ✓
32. **skip_checklist_item** - Registry ✗ | Handlers ✗ | Docs ✓
33. **complete_checklist** - Registry ✗ | Handlers ✗ | Docs ✓
34. **upload_document** - Registry ✗ | Handlers ✗ | Docs ✓
35. **link_document_to_equipment** - Registry ✗ | Handlers ✗ | Docs ✓
36. **search_documents** - Registry ✗ | Handlers ✗ | Docs ✓
37. **add_photo** - Registry ✗ | Handlers ✗ | Docs ✓
38. **remove_photo** - Registry ✗ | Handlers ✗ | Docs ✓
39. **detect_symptom_recurrence** - Registry ✗ | Handlers ✗ | Docs ✓
40. **update_predictive_state** - Registry ✗ | Handlers ✗ | Docs ✓
41. **search** - Registry ✗ | Handlers ✗ | Docs ✓
42. **rag_suggest_action** - Registry ✗ | Handlers ✗ | Docs ✓
43. **rag_prefill** - Registry ✗ | Handlers ✗ | Docs ✓
44. **log_action_execution** - Registry ✗ | Handlers ✗ | Docs ✓

**Action:** These are documented for architectural completeness but not implemented. Mark as "Future" or "Batch 2+".

---

### CATEGORY 4: Name Mismatches (Same Action, Different Names)

**Priority: HIGH - Need Naming Alignment**

| Registry Name | Handler Name | Docs Name | Canonical Name |
|---------------|--------------|-----------|----------------|
| edit_inventory_quantity | N/A | adjust_inventory | **adjust_inventory** |
| create_reorder | create_purchase_request | create_purchase_order | **create_purchase_request** |
| view_related_docs | view_related_documents | N/A | **view_related_docs** |
| add_parts_to_work_order | add_part_to_work_order | add_wo_part | **add_wo_part** |
| mark_work_order_complete | mark_work_order_complete | complete_work_order | **complete_work_order** |
| add_work_order_note | add_note_to_work_order | add_wo_note | **add_wo_note** |

**Action:** Choose canonical names and update all sources.

---

### CATEGORY 5: Registry Actions Not in Docs (Undocumented)

**Priority: MEDIUM - Need Documentation**

1. **view_inventory_item** - Registry ✓ | Docs ✗
2. **view_stock_levels** - Registry ✓ | Docs ✗
3. **create_reorder** - Registry ✓ | Docs ⚠️
4. **view_manual_section** - Registry ✓ | Docs ⚠️
5. **view_related_docs** - Registry ✓ | Docs ✗
6. **view_maintenance_history** - Registry ✓ | Docs ⚠️
7. **run_diagnostic** - Registry ✓ | Docs ✗
8. **log_symptom** - Registry ✓ | Docs ✓
9. **open_vessel** - Registry ✓ | Docs ✗
10. **view_attachments** - Registry ✓ | Docs ✗

**Action:** Add these actions to ACTION_IO_MATRIX.md with reads/writes contracts.

---

## CANONICAL ACTION COUNT

After reconciliation, the **canonical MVP action list** should be:

**Tier 1 (Implemented + Registered):** ~35-40 actions
**Tier 2 (Registered, Not Implemented):** ~15-20 actions
**Tier 3 (Documented, Future):** ~20-25 actions

**Total Canonical Actions:** ~70-85 actions (including future)

---

## RECOMMENDED ACTIONS

### Immediate (Next Sprint)
1. **Resolve naming mismatches** - Choose canonical names, update all sources
2. **Register missing handlers** - Add Category 2 actions to registry
3. **Document Tier 1 actions** - Complete ACTION_IO_MATRIX for all implemented actions

### Short-Term (Next 2 Sprints)
4. **Implement or remove** - Category 1 actions (registry without handlers)
5. **Mark future actions** - Flag Category 3 actions as "Future" in docs
6. **Validate action grouping** - Ensure consistent grouping across all sources

### Long-Term (Batch 2+)
7. **Implement Tier 3** - Build out future actions as needed
8. **Deprecate unused actions** - Remove actions not used after 6 months

---

## TRUTH TABLE SUMMARY

| Source | Count | Status |
|--------|-------|--------|
| Registry (action_registry.py) | 71 | ✅ Authoritative for MVP |
| Handlers (handlers/*.py) | ~55 | ✅ Implementation truth |
| Docs (ACTION_IO_MATRIX.md) | 63 | ⚠️ Includes future actions |
| **Canonical MVP** | **~45-50** | ✅ Registry ∩ Handlers |
| **Canonical Future** | **~20-25** | 📋 Docs only |
| **Total Canonical** | **~70-85** | ✅ All sources unified |

---

## DEFINITION OF TRUTH (Going Forward)

**Registry** = Frontend-facing action catalog (what UI can invoke)
**Handlers** = Backend implementation (what actually executes)
**ACTION_IO_MATRIX** = Data contract (what reads/writes occur)

**Rule:**
- Action MUST be in Registry to be callable
- Action MUST have Handler to execute
- Action MUST be in ACTION_IO_MATRIX for testing/validation

**If action is missing from any source, it is NOT production-ready.**

---

**Status:** Reconciliation complete. Naming mismatches and missing registrations identified. Ready for alignment work.
