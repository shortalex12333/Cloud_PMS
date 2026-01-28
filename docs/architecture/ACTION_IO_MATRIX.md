# ACTION_IO_MATRIX.md

**Date:** 2026-01-22
**Status:** Layer 2 - Action I/O Contract (Technical Reference)

---

## PURPOSE

This document is the authoritative contract for every micro-action in CelesteOS. For each action, it specifies:

- **Reads:** Tables and columns accessed (SELECT)
- **Writes:** Tables and columns modified (INSERT/UPDATE/DELETE)
- **Ledger Event:** Whether action writes to ledger (yes/no + event type)
- **Audit Log:** Whether action writes to pms_audit_log (yes/no)
- **RLS Boundary:** Row-level security enforcement
- **Commit Type:** `informational` (reversible) or `irreversible` (operational state change)
- **Verified:** ✅ VERIFIED (schema confirmed) or ⚠️ UNVERIFIED (schema not confirmed)

**Rule:** If backend implements an action, it MUST match this contract. If contract says "writes to audit_log", it MUST write to audit_log.

---

## NOTATION

### Read/Write Syntax
- `table_name(col1, col2, col3)` - specific columns
- `table_name(*)` - all columns
- `table_name(+col1, +col2)` - INSERT only these columns
- `table_name(~col1, ~col2)` - UPDATE only these columns

### Verification Status
- ✅ **VERIFIED** - Table/columns exist in DB_TRUTH_PACK.md
- ⚠️ **UNVERIFIED** - Table/columns not confirmed in schema (may need migration)

---

## FAULT CLUSTER ACTIONS

### 1. report_fault

**Pattern:** `[MUTATE_LOW]` `[SINGLE_STEP]`

**Reads:**
- `pms_equipment(id, name, status)` - to validate equipment reference
- `user_profiles(id, name)` - to get user info

**Writes:**
- `pms_faults(+id, +yacht_id, +fault_number, +title, +severity, +status, +equipment_id, +detected_at, +created_at, +created_by)` - INSERT new fault
- `pms_audit_log(+id, +yacht_id, +action, +entity_type, +entity_id, +user_id, +new_values, +signature, +created_at)` - INSERT audit entry
- `handover_items(+id, +yacht_id, +handover_id, +entity_type, +entity_id, +summary, +priority, +status, +added_by, +created_at)` - IF severity='critical', auto-create handover entry

**Ledger Event:** Yes - `fault_created`

**Audit Log:** Yes

**RLS Boundary:** User must have access to yacht_id

**Commit Type:** `informational` (fault report can be deleted/closed later)

**Verified:** ✅ VERIFIED (pms_faults, pms_audit_log exist)

---

### 2. acknowledge_fault

**Pattern:** `[MUTATE_LOW]` `[SINGLE_STEP]`

**Reads:**
- `pms_faults(id, status, yacht_id)` - to validate fault exists and is in acknowledgeable state

**Writes:**
- `pms_faults(~status, ~acknowledged_by, ~acknowledged_at, ~updated_at, ~updated_by)` - UPDATE status to 'investigating'
- `pms_audit_log(+id, +yacht_id, +action, +entity_type, +entity_id, +user_id, +old_values, +new_values, +signature, +created_at)` - INSERT audit entry

**Ledger Event:** Yes - `fault_acknowledged`

**Audit Log:** Yes

**RLS Boundary:** User must have access to fault's yacht_id

**Commit Type:** `informational`

**Verified:** ✅ VERIFIED

---

### 3. add_fault_note

**Pattern:** `[MUTATE_LOW]` `[SINGLE_STEP]`

**Reads:**
- `pms_faults(id, yacht_id)` - to validate fault exists

**Writes:**
- `pms_faults(~updated_at, ~updated_by)` - UPDATE timestamp (or notes JSONB if exists)
- `pms_audit_log(+id, +yacht_id, +action, +entity_type, +entity_id, +user_id, +new_values, +signature, +created_at)` - INSERT audit entry

**Ledger Event:** Yes - `fault_note_added`

**Audit Log:** Yes

**RLS Boundary:** User must have access to fault's yacht_id

**Commit Type:** `informational`

**Verified:** ⚠️ UNVERIFIED (notes storage mechanism not confirmed - may be JSONB or separate notes table)

**Note:** Fault notes may use same pattern as work_order_notes (separate table) but no fault_notes table found in schema.

---

### 4. diagnose_fault

**Pattern:** `[MUTATE_LOW]` `[MULTI_STEP]`

**Reads:**
- `pms_faults(id, status, yacht_id, equipment_id)` - to get fault context
- `pms_equipment(id, name, manufacturer, model)` - to get equipment details
- RAG document chunks (external) - to find manual sections

**Writes:**
- `pms_faults(~diagnosis, ~diagnosis_notes, ~diagnosed_by, ~diagnosed_at, ~updated_at, ~updated_by)` - UPDATE with diagnosis (if columns exist)
- `pms_audit_log(+id, +yacht_id, +action, +entity_type, +entity_id, +user_id, +old_values, +new_values, +signature, +created_at)` - INSERT audit entry

**Ledger Event:** Yes - `fault_diagnosed`

**Audit Log:** Yes

**RLS Boundary:** User must have access to fault's yacht_id

**Commit Type:** `informational`

**Verified:** ⚠️ UNVERIFIED (diagnosis/diagnosis_notes columns not found in pms_faults schema)

**Note:** May store diagnosis in metadata JSONB or require schema migration.

---

### 5. create_work_order_from_fault

**Pattern:** `[MUTATE_LOW]` `[MULTI_STEP]`

**Reads:**
- `pms_faults(id, title, equipment_id, yacht_id)` - to get fault context for WO creation

**Writes:**
- `pms_work_orders(+id, +yacht_id, +wo_number, +title, +wo_type, +priority, +status, +equipment_id, +fault_id, +created_at, +created_by)` - INSERT new work order
- `pms_faults(~status, ~work_order_id, ~updated_at, ~updated_by)` - UPDATE fault status to 'work_ordered'
- `pms_audit_log(+id, +yacht_id, +action, +entity_type, +entity_id, +user_id, +new_values, +signature, +created_at)` - INSERT audit entry (2 entries: one for WO creation, one for fault update)

**Ledger Event:** Yes - `work_order_created` + `fault_status_changed`

**Audit Log:** Yes

**RLS Boundary:** User must have access to fault's yacht_id

**Commit Type:** `informational` (WO can be cancelled)

**Verified:** ✅ VERIFIED

---

### 6. resolve_fault

**Pattern:** `[MUTATE_LOW]` `[SINGLE_STEP]`

**Reads:**
- `pms_faults(id, status, yacht_id)` - to validate fault is in resolvable state

**Writes:**
- `pms_faults(~status, ~resolved_at, ~resolved_by, ~resolution_notes, ~updated_at, ~updated_by)` - UPDATE status to 'resolved'
- `pms_audit_log(+id, +yacht_id, +action, +entity_type, +entity_id, +user_id, +old_values, +new_values, +signature, +created_at)` - INSERT audit entry

**Ledger Event:** Yes - `fault_resolved`

**Audit Log:** Yes

**RLS Boundary:** User must have access to fault's yacht_id, typically HOD only

**Commit Type:** `informational`

**Verified:** ✅ VERIFIED (resolved_at exists in schema)

**Note:** resolution_notes not confirmed in schema - may use metadata JSONB.

---

### 7. close_fault

**Pattern:** `[MUTATE_LOW]` `[SINGLE_STEP]`

**Reads:**
- `pms_faults(id, status, yacht_id)` - to validate fault is resolved

**Writes:**
- `pms_faults(~status, ~closed_at, ~closed_by, ~updated_at, ~updated_by)` - UPDATE status to 'closed'
- `pms_audit_log(+id, +yacht_id, +action, +entity_type, +entity_id, +user_id, +old_values, +new_values, +signature, +created_at)` - INSERT audit entry

**Ledger Event:** Yes - `fault_closed`

**Audit Log:** Yes

**RLS Boundary:** User must have access to fault's yacht_id, typically HOD only

**Commit Type:** `informational`

**Verified:** ⚠️ UNVERIFIED (closed_at, closed_by columns not found in pms_faults schema)

**Note:** May use resolved_at as proxy or require schema addition.

---

### 8. defer_fault

**Pattern:** `[MUTATE_LOW]` `[SINGLE_STEP]`

**Reads:**
- `pms_faults(id, status, yacht_id)` - to validate fault

**Writes:**
- `pms_faults(~status, ~deferred_until, ~deferral_reason, ~updated_at, ~updated_by)` - UPDATE status to 'deferred'
- `pms_audit_log(+id, +yacht_id, +action, +entity_type, +entity_id, +user_id, +old_values, +new_values, +signature, +created_at)` - INSERT audit entry

**Ledger Event:** Yes - `fault_deferred`

**Audit Log:** Yes

**RLS Boundary:** User must have access to fault's yacht_id, typically HOD only

**Commit Type:** `informational`

**Verified:** ⚠️ UNVERIFIED (deferred_until, deferral_reason not in schema)

---

### 9. add_to_handover

**Pattern:** `[MUTATE_LOW]` `[SINGLE_STEP]`

**Reads:**
- `pms_faults(id, title, yacht_id)` - to get fault context for handover entry

**Writes:**
- `handover_items(+id, +yacht_id, +handover_id, +entity_type, +entity_id, +summary, +priority, +status, +added_by, +created_at)` - INSERT handover item
- `pms_audit_log(+id, +yacht_id, +action, +entity_type, +entity_id, +user_id, +new_values, +signature, +created_at)` - INSERT audit entry

**Ledger Event:** Yes - `handover_item_added`

**Audit Log:** Yes

**RLS Boundary:** User must have access to fault's yacht_id

**Commit Type:** `informational`

**Verified:** ✅ VERIFIED

**Note:** This action applies to ANY entity, not just faults. Generic pattern.

---

## WORK ORDER CLUSTER ACTIONS

### 10. create_work_order

**Pattern:** `[MUTATE_LOW]` `[MULTI_STEP]`

**Reads:**
- `pms_equipment(id, name, yacht_id)` - IF equipment association specified
- `user_profiles(id, name, role)` - to validate assignee

**Writes:**
- `pms_work_orders(+id, +yacht_id, +wo_number, +title, +wo_type, +priority, +status, +equipment_id, +assigned_to, +created_at, +created_by)` - INSERT new work order
- `pms_audit_log(+id, +yacht_id, +action, +entity_type, +entity_id, +user_id, +new_values, +signature, +created_at)` - INSERT audit entry

**Ledger Event:** Yes - `work_order_created`

**Audit Log:** Yes

**RLS Boundary:** User must have access to yacht_id

**Commit Type:** `informational`

**Verified:** ✅ VERIFIED

---

### 11. assign_work_order

**Pattern:** `[MUTATE_LOW]` `[SINGLE_STEP]`

**Reads:**
- `pms_work_orders(id, status, yacht_id)` - to validate WO exists
- `user_profiles(id, name, role, yacht_id)` - to validate assignee

**Writes:**
- `pms_work_orders(~assigned_to, ~assigned_at, ~updated_at, ~updated_by)` - UPDATE assigned_to
- `pms_audit_log(+id, +yacht_id, +action, +entity_type, +entity_id, +user_id, +old_values, +new_values, +signature, +created_at)` - INSERT audit entry

**Ledger Event:** Yes - `work_order_assigned`

**Audit Log:** Yes

**RLS Boundary:** User must have access to WO's yacht_id, typically HOD only

**Commit Type:** `informational`

**Verified:** ✅ VERIFIED (assigned_to exists, assigned_at not confirmed)

---

### 12. start_work_order

**Pattern:** `[MUTATE_LOW]` `[SINGLE_STEP]`

**Reads:**
- `pms_work_orders(id, status, yacht_id, assigned_to)` - to validate WO is assigned and not started

**Writes:**
- `pms_work_orders(~status, ~started_at, ~started_by, ~updated_at, ~updated_by)` - UPDATE status to 'in_progress'
- `pms_audit_log(+id, +yacht_id, +action, +entity_type, +entity_id, +user_id, +old_values, +new_values, +signature, +created_at)` - INSERT audit entry

**Ledger Event:** Yes - `work_order_started`

**Audit Log:** Yes

**RLS Boundary:** User must have access to WO's yacht_id, typically assigned user only

**Commit Type:** `informational`

**Verified:** ⚠️ UNVERIFIED (started_at, started_by not in schema)

---

### 13. add_wo_hours

**Pattern:** `[MUTATE_LOW]` `[SINGLE_STEP]`

**Reads:**
- `pms_work_orders(id, status, yacht_id)` - to validate WO is in_progress

**Writes:**
- `pms_work_orders(~hours_logged, ~updated_at, ~updated_by)` - UPDATE hours (if column exists)
- `pms_audit_log(+id, +yacht_id, +action, +entity_type, +entity_id, +user_id, +new_values, +signature, +created_at)` - INSERT audit entry

**Ledger Event:** Yes - `work_order_hours_logged`

**Audit Log:** Yes

**RLS Boundary:** User must have access to WO's yacht_id

**Commit Type:** `informational`

**Verified:** ⚠️ UNVERIFIED (hours_logged column not found in pms_work_orders schema)

**Note:** May use metadata JSONB or require separate time_log table.

---

### 14. add_wo_note

**Pattern:** `[MUTATE_LOW]` `[SINGLE_STEP]`

**Reads:**
- `pms_work_orders(id, yacht_id)` - to validate WO exists

**Writes:**
- `work_order_notes(+id, +work_order_id, +note_text, +note_type, +created_by, +created_at)` - INSERT new note
- `pms_work_orders(~updated_at, ~updated_by)` - UPDATE timestamp
- `pms_audit_log(+id, +yacht_id, +action, +entity_type, +entity_id, +user_id, +new_values, +signature, +created_at)` - INSERT audit entry

**Ledger Event:** Yes - `work_order_note_added`

**Audit Log:** Yes

**RLS Boundary:** User must have access to WO's yacht_id

**Commit Type:** `informational`

**Verified:** ✅ VERIFIED (work_order_notes table exists)

---

### 15. add_wo_part

**Pattern:** `[MUTATE_LOW]` `[SINGLE_STEP]`

**Reads:**
- `pms_work_orders(id, status, yacht_id)` - to validate WO
- `pms_parts(id, name, quantity_on_hand, yacht_id)` - to validate part exists

**Writes:**
- `work_order_parts(+id, +work_order_id, +part_id, +quantity_required, +created_by)` - INSERT junction record
- `pms_work_orders(~updated_at, ~updated_by)` - UPDATE timestamp
- `pms_audit_log(+id, +yacht_id, +action, +entity_type, +entity_id, +user_id, +new_values, +signature, +created_at)` - INSERT audit entry

**Ledger Event:** Yes - `work_order_part_added`

**Audit Log:** Yes

**RLS Boundary:** User must have access to WO's yacht_id

**Commit Type:** `informational`

**Verified:** ✅ VERIFIED (work_order_parts table exists)

---

### 16. remove_wo_part

**Pattern:** `[MUTATE_LOW]` `[SINGLE_STEP]`

**Reads:**
- `work_order_parts(id, work_order_id, part_id)` - to validate junction record exists
- `pms_work_orders(id, yacht_id)` - for RLS check

**Writes:**
- `work_order_parts(-id)` - DELETE junction record
- `pms_work_orders(~updated_at, ~updated_by)` - UPDATE timestamp
- `pms_audit_log(+id, +yacht_id, +action, +entity_type, +entity_id, +user_id, +old_values, +signature, +created_at)` - INSERT audit entry

**Ledger Event:** Yes - `work_order_part_removed`

**Audit Log:** Yes

**RLS Boundary:** User must have access to WO's yacht_id

**Commit Type:** `informational`

**Verified:** ✅ VERIFIED

---

### 17. complete_work_order

**Pattern:** `[MUTATE_MEDIUM]` `[SINGLE_STEP]` `[SIGNATURE_REQUIRED]`

**Reads:**
- `pms_work_orders(id, status, yacht_id, assigned_to)` - to validate WO is in_progress
- `pms_faults(id, work_order_id)` - to check if fault should be auto-resolved

**Writes:**
- `pms_work_orders(~status, ~completed_at, ~completed_by, ~updated_at, ~updated_by)` - UPDATE status to 'completed'
- `pms_faults(~status, ~resolved_at, ~updated_at)` - IF linked fault, UPDATE status to 'resolved'
- `pms_audit_log(+id, +yacht_id, +action, +entity_type, +entity_id, +user_id, +old_values, +new_values, +signature, +created_at)` - INSERT audit entry (2 entries if fault updated)

**Ledger Event:** Yes - `work_order_completed` + optional `fault_auto_resolved`

**Audit Log:** Yes

**RLS Boundary:** User must have access to WO's yacht_id, typically assigned user or HOD

**Commit Type:** `irreversible` (completion is operational milestone)

**Verified:** ✅ VERIFIED (completed_at, completed_by exist in schema)

**Signature:** Yes - requires digital signature (HOD or assigned engineer)

---

### 18. reopen_work_order

**Pattern:** `[MUTATE_LOW]` `[SINGLE_STEP]`

**Reads:**
- `pms_work_orders(id, status, yacht_id)` - to validate WO is completed

**Writes:**
- `pms_work_orders(~status, ~reopened_at, ~reopened_by, ~reopen_reason, ~updated_at, ~updated_by)` - UPDATE status back to 'in_progress'
- `pms_audit_log(+id, +yacht_id, +action, +entity_type, +entity_id, +user_id, +old_values, +new_values, +signature, +created_at)` - INSERT audit entry

**Ledger Event:** Yes - `work_order_reopened`

**Audit Log:** Yes

**RLS Boundary:** User must have access to WO's yacht_id, typically HOD only

**Commit Type:** `informational`

**Verified:** ⚠️ UNVERIFIED (reopened_at, reopened_by, reopen_reason not in schema)

---

### 19. cancel_work_order

**Pattern:** `[MUTATE_LOW]` `[SINGLE_STEP]`

**Reads:**
- `pms_work_orders(id, status, yacht_id)` - to validate WO not already completed

**Writes:**
- `pms_work_orders(~status, ~cancelled_at, ~cancelled_by, ~cancellation_reason, ~updated_at, ~updated_by)` - UPDATE status to 'cancelled'
- `pms_audit_log(+id, +yacht_id, +action, +entity_type, +entity_id, +user_id, +old_values, +new_values, +signature, +created_at)` - INSERT audit entry

**Ledger Event:** Yes - `work_order_cancelled`

**Audit Log:** Yes

**RLS Boundary:** User must have access to WO's yacht_id, typically HOD only

**Commit Type:** `informational`

**Verified:** ⚠️ UNVERIFIED (cancelled_at, cancelled_by, cancellation_reason not in schema)

---

## HANDOVER CLUSTER ACTIONS

### 20. add_to_handover (generic)

**Pattern:** `[MUTATE_LOW]` `[SINGLE_STEP]`

**Reads:**
- Entity table (e.g., `pms_faults`, `pms_work_orders`, `pms_equipment`) - to get entity context

**Writes:**
- `handover_items(+id, +yacht_id, +handover_id, +entity_type, +entity_id, +summary, +priority, +status, +added_by, +created_at)` - INSERT handover item
- `pms_audit_log(+id, +yacht_id, +action, +entity_type, +entity_id, +user_id, +new_values, +signature, +created_at)` - INSERT audit entry

**Ledger Event:** Yes - `handover_item_added`

**Audit Log:** Yes

**RLS Boundary:** User must have access to yacht_id

**Commit Type:** `informational`

**Verified:** ✅ VERIFIED

**Note:** Polymorphic action - works with any entity_type (fault, work_order, equipment, part, document, note).

---

### 21. add_document_to_handover

**Pattern:** `[MUTATE_LOW]` `[SINGLE_STEP]`

**Reads:**
- Document table (UNVERIFIED) - to get document context

**Writes:**
- `handover_items(+id, +yacht_id, +handover_id, +entity_type='document', +entity_id, +summary, +priority, +status, +added_by, +created_at)` - INSERT handover item
- `pms_audit_log(+id, +yacht_id, +action, +entity_type, +entity_id, +user_id, +new_values, +signature, +created_at)` - INSERT audit entry

**Ledger Event:** Yes - `handover_item_added`

**Audit Log:** Yes

**RLS Boundary:** User must have access to yacht_id

**Commit Type:** `informational`

**Verified:** ⚠️ UNVERIFIED (documents table not found in schema)

---

### 22. add_document_section_to_handover

**Pattern:** `[MUTATE_LOW]` `[SINGLE_STEP]`

**Reads:**
- Document table (UNVERIFIED) - to get document section/page

**Writes:**
- `handover_items(+id, +yacht_id, +handover_id, +entity_type='document_section', +entity_id, +document_page, +document_snippet, +summary, +priority, +status, +added_by, +created_at)` - INSERT handover item
- `pms_audit_log(+id, +yacht_id, +action, +entity_type, +entity_id, +user_id, +new_values, +signature, +created_at)` - INSERT audit entry

**Ledger Event:** Yes - `handover_item_added`

**Audit Log:** Yes

**RLS Boundary:** User must have access to yacht_id

**Commit Type:** `informational`

**Verified:** ⚠️ UNVERIFIED (document_page, document_snippet not in handover_items schema)

---

### 23. add_note (general handover)

**Pattern:** `[MUTATE_LOW]` `[SINGLE_STEP]`

**Reads:** None (general note, no entity reference)

**Writes:**
- `handover_items(+id, +yacht_id, +handover_id, +entity_type='general', +entity_id=NULL, +summary, +priority, +status, +added_by, +created_at)` - INSERT handover item
- `pms_audit_log(+id, +yacht_id, +action, +entity_type='handover_item', +entity_id, +user_id, +new_values, +signature, +created_at)` - INSERT audit entry

**Ledger Event:** Yes - `handover_note_added`

**Audit Log:** Yes

**RLS Boundary:** User must have access to yacht_id

**Commit Type:** `informational`

**Verified:** ✅ VERIFIED

---

### 24. edit_handover_section

**Pattern:** `[MUTATE_LOW]` `[SINGLE_STEP]`

**Reads:**
- `handover_items(id, added_by, yacht_id)` - to validate permission (only creator or HOD can edit)

**Writes:**
- `handover_items(~summary, ~details, ~priority, ~updated_at, ~updated_by)` - UPDATE handover item
- `pms_audit_log(+id, +yacht_id, +action, +entity_type, +entity_id, +user_id, +old_values, +new_values, +signature, +created_at)` - INSERT audit entry

**Ledger Event:** Yes - `handover_item_updated`

**Audit Log:** Yes

**RLS Boundary:** User must be creator OR HOD

**Commit Type:** `informational`

**Verified:** ⚠️ UNVERIFIED (details column not in handover_items schema, may use summary only)

---

### 25. acknowledge_handover

**Pattern:** `[MUTATE_LOW]` `[SINGLE_STEP]`

**Reads:**
- `handover_items(id, yacht_id, status)` - to get all unacknowledged items

**Writes:**
- `handover_items(~acknowledged_by, ~acknowledged_at, ~status='acknowledged', ~updated_at, ~updated_by)` - UPDATE multiple items (batch)
- `pms_audit_log(+id, +yacht_id, +action, +entity_type, +entity_id, +user_id, +new_values, +signature, +created_at)` - INSERT audit entry (one per item or batch)

**Ledger Event:** Yes - `handover_acknowledged`

**Audit Log:** Yes

**RLS Boundary:** User must have access to yacht_id

**Commit Type:** `informational`

**Verified:** ✅ VERIFIED

---

### 26. export_handover

**Pattern:** `[READ_ONLY]`

**Reads:**
- `handover_items(*)` - to get all items in date range
- `handovers(*)` - IF using master handover records
- `pms_faults(id, title, status)` - to resolve entity references
- `pms_work_orders(id, wo_number, title, status)` - to resolve entity references
- `user_profiles(id, name)` - to get creator/acknowledger names

**Writes:**
- `pms_audit_log(+id, +yacht_id, +action='export_handover', +entity_type='handover', +entity_id, +user_id, +new_values, +signature, +created_at)` - INSERT audit entry (export logged for audit)

**Ledger Event:** Yes - `handover_exported` (for audit trail)

**Audit Log:** Yes (export actions logged)

**RLS Boundary:** User must have access to yacht_id

**Commit Type:** `informational` (no data modification)

**Verified:** ✅ VERIFIED

---

### 27. generate_summary (AI)

**Pattern:** `[READ_ONLY]`

**Reads:**
- `handover_items(*)` - to get items for summarization
- `pms_faults(id, title, severity, status)` - to enrich entity context
- `pms_work_orders(id, wo_number, title, status)` - to enrich entity context

**Writes:**
- `pms_audit_log(+id, +yacht_id, +action='generate_handover_summary', +entity_type='handover', +entity_id, +user_id, +new_values, +signature, +created_at)` - INSERT audit entry

**Ledger Event:** Yes - `handover_summary_generated`

**Audit Log:** Yes

**RLS Boundary:** User must have access to yacht_id

**Commit Type:** `informational` (no data modification, regenerable)

**Verified:** ✅ VERIFIED

---

## INVENTORY (PARTS) CLUSTER ACTIONS

### 28. adjust_inventory

**Pattern:** `[MUTATE_MEDIUM]` `[SINGLE_STEP]` `[SIGNATURE_REQUIRED]`

**Reads:**
- `pms_parts(id, quantity_on_hand, yacht_id)` - to get current quantity

**Writes:**
- `pms_parts(~quantity_on_hand, ~last_counted_at, ~updated_at, ~updated_by)` - UPDATE quantity
- `part_usage(+id, +yacht_id, +part_id, +quantity, +transaction_type='adjustment', +notes, +created_by, +created_at)` - INSERT usage log entry
- `pms_audit_log(+id, +yacht_id, +action, +entity_type, +entity_id, +user_id, +old_values, +new_values, +signature, +created_at)` - INSERT audit entry

**Ledger Event:** Yes - `inventory_adjusted`

**Audit Log:** Yes

**RLS Boundary:** User must have access to part's yacht_id, typically HOD only

**Commit Type:** `irreversible` (physical inventory change)

**Verified:** ✅ VERIFIED

**Signature:** Yes - requires digital signature (HOD or authorized crew)

---

### 29. log_part_usage

**Pattern:** `[MUTATE_MEDIUM]` `[SINGLE_STEP]`

**Reads:**
- `pms_parts(id, quantity_on_hand, yacht_id)` - to validate sufficient quantity
- `pms_work_orders(id, yacht_id)` - IF usage linked to work order

**Writes:**
- `pms_parts(~quantity_on_hand, ~updated_at, ~updated_by)` - UPDATE quantity (decrement)
- `part_usage(+id, +yacht_id, +part_id, +work_order_id, +quantity, +transaction_type='usage', +notes, +created_by, +created_at)` - INSERT usage log entry
- `work_order_parts(~quantity_used, ~updated_at)` - IF linked to WO, UPDATE quantity_used
- `pms_audit_log(+id, +yacht_id, +action, +entity_type, +entity_id, +user_id, +old_values, +new_values, +signature, +created_at)` - INSERT audit entry

**Ledger Event:** Yes - `part_used`

**Audit Log:** Yes

**RLS Boundary:** User must have access to part's yacht_id

**Commit Type:** `irreversible` (physical inventory change)

**Verified:** ✅ VERIFIED

---

### 30. restock_part

**Pattern:** `[MUTATE_MEDIUM]` `[SINGLE_STEP]`

**Reads:**
- `pms_parts(id, quantity_on_hand, yacht_id)` - to get current quantity

**Writes:**
- `pms_parts(~quantity_on_hand, ~updated_at, ~updated_by)` - UPDATE quantity (increment)
- `part_usage(+id, +yacht_id, +part_id, +quantity, +transaction_type='restock', +notes, +created_by, +created_at)` - INSERT usage log entry
- `pms_audit_log(+id, +yacht_id, +action, +entity_type, +entity_id, +user_id, +old_values, +new_values, +signature, +created_at)` - INSERT audit entry

**Ledger Event:** Yes - `part_restocked`

**Audit Log:** Yes

**RLS Boundary:** User must have access to part's yacht_id

**Commit Type:** `irreversible` (physical inventory change)

**Verified:** ✅ VERIFIED

---

### 31. add_to_shopping_list

**Pattern:** `[MUTATE_LOW]` `[SINGLE_STEP]`

**Reads:**
- `pms_parts(id, name, part_number, yacht_id)` - to get part info

**Writes:**
- Shopping list table (UNVERIFIED) - INSERT shopping list item
- `pms_audit_log(+id, +yacht_id, +action, +entity_type='shopping_list_item', +entity_id, +user_id, +new_values, +signature, +created_at)` - INSERT audit entry

**Ledger Event:** Yes - `shopping_list_item_added`

**Audit Log:** Yes

**RLS Boundary:** User must have access to part's yacht_id

**Commit Type:** `informational`

**Verified:** ⚠️ UNVERIFIED (shopping_list table not found in schema)

**Note:** May use pms_parts.metadata JSONB or require dedicated shopping_list_items table.

---

### 32. remove_from_shopping_list

**Pattern:** `[MUTATE_LOW]` `[SINGLE_STEP]`

**Reads:**
- Shopping list table (UNVERIFIED) - to validate item exists

**Writes:**
- Shopping list table - DELETE or soft delete item
- `pms_audit_log(+id, +yacht_id, +action, +entity_type='shopping_list_item', +entity_id, +user_id, +old_values, +signature, +created_at)` - INSERT audit entry

**Ledger Event:** Yes - `shopping_list_item_removed`

**Audit Log:** Yes

**RLS Boundary:** User must have access to yacht_id

**Commit Type:** `informational`

**Verified:** ⚠️ UNVERIFIED

---

### 33. flag_low_stock

**Pattern:** `[READ_ONLY]` (system detection, not user action)

**Reads:**
- `pms_parts(id, name, quantity_on_hand, quantity_minimum, yacht_id)` - to detect low stock

**Writes:**
- `situation_detections(+id, +yacht_id, +situation_type='low_stock', +severity, +label, +evidence, +recommendations, +created_at)` - INSERT situation detection

**Ledger Event:** No (system detection, not user action)

**Audit Log:** No (informational detection)

**RLS Boundary:** System action, yacht-scoped

**Commit Type:** `informational`

**Verified:** ✅ VERIFIED (situation_detections table exists)

**Note:** This may be a background process, not a user-initiated action.

---

## PURCHASING CLUSTER ACTIONS

### 34. create_purchase_order

**Pattern:** `[MUTATE_LOW]` `[MULTI_STEP]`

**Reads:**
- `pms_parts(id, name, unit_cost, yacht_id)` - to get parts for PO
- Shopping list table (UNVERIFIED) - to pull items from shopping list

**Writes:**
- `pms_purchase_orders(+id, +yacht_id, +po_number, +status='draft', +supplier_name, +total, +created_at, +created_by)` - INSERT new PO
- Purchase order items table (UNVERIFIED) - INSERT PO line items
- `pms_audit_log(+id, +yacht_id, +action, +entity_type='purchase_order', +entity_id, +user_id, +new_values, +signature, +created_at)` - INSERT audit entry

**Ledger Event:** Yes - `purchase_order_created`

**Audit Log:** Yes

**RLS Boundary:** User must have access to yacht_id

**Commit Type:** `informational`

**Verified:** ⚠️ UNVERIFIED (pms_purchase_orders exists, but PO items table not found)

---

### 35. approve_purchase_order

**Pattern:** `[MUTATE_MEDIUM]` `[SINGLE_STEP]` `[SIGNATURE_REQUIRED]`

**Reads:**
- `pms_purchase_orders(id, status, yacht_id)` - to validate PO is pending approval

**Writes:**
- `pms_purchase_orders(~status='approved', ~approved_by, ~approved_at, ~updated_at, ~updated_by)` - UPDATE status
- `pms_audit_log(+id, +yacht_id, +action, +entity_type, +entity_id, +user_id, +old_values, +new_values, +signature, +created_at)` - INSERT audit entry

**Ledger Event:** Yes - `purchase_order_approved`

**Audit Log:** Yes

**RLS Boundary:** User must be HOD (Chief Engineer or Captain)

**Commit Type:** `irreversible` (approval commits budget)

**Verified:** ⚠️ UNVERIFIED (approved_by, approved_at not in pms_purchase_orders schema)

**Signature:** Yes - requires HOD digital signature

---

### 36. mark_po_ordered

**Pattern:** `[MUTATE_LOW]` `[SINGLE_STEP]`

**Reads:**
- `pms_purchase_orders(id, status, yacht_id)` - to validate PO is approved

**Writes:**
- `pms_purchase_orders(~status='ordered', ~ordered_at, ~ordered_by, ~updated_at, ~updated_by)` - UPDATE status
- `pms_audit_log(+id, +yacht_id, +action, +entity_type, +entity_id, +user_id, +old_values, +new_values, +signature, +created_at)` - INSERT audit entry

**Ledger Event:** Yes - `purchase_order_ordered`

**Audit Log:** Yes

**RLS Boundary:** User must have access to PO's yacht_id

**Commit Type:** `informational`

**Verified:** ⚠️ UNVERIFIED (ordered_at, ordered_by not in schema)

---

### 37. receive_items (start session)

**Pattern:** `[MUTATE_MEDIUM]` `[MULTI_STEP]` `[RESUMABLE]`

**Reads:**
- `pms_purchase_orders(id, status, yacht_id)` - to validate PO is ordered
- Purchase order items table (UNVERIFIED) - to get items to receive

**Writes:**
- Receiving session table (UNVERIFIED) - INSERT or UPDATE session record
- `pms_audit_log(+id, +yacht_id, +action='receiving_session_started', +entity_type='receiving_session', +entity_id, +user_id, +new_values, +signature, +created_at)` - INSERT audit entry

**Ledger Event:** Yes - `receiving_session_started`

**Audit Log:** Yes

**RLS Boundary:** User must have access to PO's yacht_id

**Commit Type:** `informational` (session can be cancelled)

**Verified:** ⚠️ UNVERIFIED (receiving_sessions table not found in schema)

---

### 38. check_in_item

**Pattern:** `[MUTATE_LOW]` `[SINGLE_STEP]` (within receiving session)

**Reads:**
- Receiving session table (UNVERIFIED) - to validate session active
- Purchase order items table (UNVERIFIED) - to validate item on PO

**Writes:**
- Receiving session table - UPDATE checked items
- `pms_audit_log(+id, +yacht_id, +action='item_checked_in', +entity_type='receiving_session', +entity_id, +user_id, +new_values, +signature, +created_at)` - INSERT audit entry

**Ledger Event:** Yes - `item_checked_in`

**Audit Log:** Yes

**RLS Boundary:** User must have access to yacht_id

**Commit Type:** `informational` (within uncommitted session)

**Verified:** ⚠️ UNVERIFIED

---

### 39. commit_session

**Pattern:** `[MUTATE_HIGH]` `[SINGLE_STEP]` `[SIGNATURE_REQUIRED]`

**Reads:**
- Receiving session table (UNVERIFIED) - to get checked items
- Purchase order items table (UNVERIFIED) - to validate quantities
- `pms_parts(id, quantity_on_hand, yacht_id)` - to update inventory

**Writes:**
- `pms_parts(~quantity_on_hand, ~updated_at, ~updated_by)` - UPDATE quantities (increment for each checked item)
- `part_usage(+id, +yacht_id, +part_id, +quantity, +transaction_type='receiving', +notes, +created_by, +created_at)` - INSERT usage log entries (batch)
- `pms_purchase_orders(~status='received' or 'partial', ~received_at, ~received_by, ~updated_at)` - UPDATE PO status
- Receiving session table - UPDATE session status to committed
- `pms_audit_log(+id, +yacht_id, +action, +entity_type, +entity_id, +user_id, +old_values, +new_values, +signature, +created_at)` - INSERT audit entries (one per inventory change)

**Ledger Event:** Yes - `receiving_session_committed` + multiple `part_received` events

**Audit Log:** Yes (multiple entries)

**RLS Boundary:** User must have access to yacht_id, typically HOD or authorized crew

**Commit Type:** `irreversible` (physical inventory change, permanent)

**Verified:** ⚠️ UNVERIFIED (receiving logic not confirmed in schema)

**Signature:** Yes - requires digital signature (HOD or authorized crew)

---

### 40. cancel_session

**Pattern:** `[MUTATE_LOW]` `[SINGLE_STEP]`

**Reads:**
- Receiving session table (UNVERIFIED) - to validate session active

**Writes:**
- Receiving session table - UPDATE session status to cancelled
- `pms_audit_log(+id, +yacht_id, +action='receiving_session_cancelled', +entity_type='receiving_session', +entity_id, +user_id, +old_values, +signature, +created_at)` - INSERT audit entry

**Ledger Event:** Yes - `receiving_session_cancelled`

**Audit Log:** Yes

**RLS Boundary:** User must have access to yacht_id

**Commit Type:** `informational`

**Verified:** ⚠️ UNVERIFIED

---

## EQUIPMENT CLUSTER ACTIONS

### 41. add_equipment

**Pattern:** `[MUTATE_LOW]` `[MULTI_STEP]`

**Reads:**
- `pms_equipment(name, yacht_id)` - to check for duplicates

**Writes:**
- `pms_equipment(+id, +yacht_id, +name, +category, +location, +manufacturer, +model, +serial_number, +status='operational', +is_critical, +metadata, +created_at, +created_by)` - INSERT new equipment
- `pms_audit_log(+id, +yacht_id, +action, +entity_type='equipment', +entity_id, +user_id, +new_values, +signature, +created_at)` - INSERT audit entry

**Ledger Event:** Yes - `equipment_added`

**Audit Log:** Yes

**RLS Boundary:** User must have access to yacht_id

**Commit Type:** `informational`

**Verified:** ✅ VERIFIED

---

### 42. update_equipment

**Pattern:** `[MUTATE_LOW]` `[SINGLE_STEP]`

**Reads:**
- `pms_equipment(id, yacht_id)` - to validate equipment exists

**Writes:**
- `pms_equipment(~name, ~category, ~location, ~manufacturer, ~model, ~serial_number, ~metadata, ~updated_at, ~updated_by)` - UPDATE equipment details
- `pms_audit_log(+id, +yacht_id, +action, +entity_type, +entity_id, +user_id, +old_values, +new_values, +signature, +created_at)` - INSERT audit entry

**Ledger Event:** Yes - `equipment_updated`

**Audit Log:** Yes

**RLS Boundary:** User must have access to equipment's yacht_id

**Commit Type:** `informational`

**Verified:** ✅ VERIFIED

---

### 43. change_equipment_status

**Pattern:** `[MUTATE_MEDIUM]` `[SINGLE_STEP]`

**Reads:**
- `pms_equipment(id, status, is_critical, yacht_id)` - to validate equipment and check criticality

**Writes:**
- `pms_equipment(~status, ~updated_at, ~updated_by)` - UPDATE status
- `pms_audit_log(+id, +yacht_id, +action, +entity_type, +entity_id, +user_id, +old_values, +new_values, +signature, +created_at)` - INSERT audit entry
- `situation_detections(+id, +yacht_id, +situation_type='critical_equipment_failed', +severity, +label, +evidence, +recommendations, +created_at)` - IF critical equipment fails, INSERT situation detection

**Ledger Event:** Yes - `equipment_status_changed` + optional `critical_equipment_alert`

**Audit Log:** Yes

**RLS Boundary:** User must have access to equipment's yacht_id

**Commit Type:** `irreversible` (operational state change)

**Verified:** ✅ VERIFIED

---

### 44. decommission_equipment

**Pattern:** `[MUTATE_HIGH]` `[SINGLE_STEP]` `[SIGNATURE_REQUIRED]`

**Reads:**
- `pms_equipment(id, status, yacht_id)` - to validate equipment

**Writes:**
- `pms_equipment(~status='decommissioned', ~decommissioned_at, ~decommissioned_by, ~decommission_reason, ~updated_at, ~updated_by)` - UPDATE status
- `pms_audit_log(+id, +yacht_id, +action, +entity_type, +entity_id, +user_id, +old_values, +new_values, +signature, +created_at)` - INSERT audit entry

**Ledger Event:** Yes - `equipment_decommissioned`

**Audit Log:** Yes

**RLS Boundary:** User must be HOD (Chief Engineer or Captain)

**Commit Type:** `irreversible` (permanent operational change)

**Verified:** ⚠️ UNVERIFIED (decommissioned_at, decommissioned_by, decommission_reason not in schema)

**Signature:** Yes - requires HOD digital signature

---

### 45. link_equipment_to_manual

**Pattern:** `[MUTATE_LOW]` `[SINGLE_STEP]`

**Reads:**
- `pms_equipment(id, yacht_id)` - to validate equipment
- Documents table (UNVERIFIED) - to validate manual exists

**Writes:**
- `pms_equipment(~metadata, ~updated_at, ~updated_by)` - UPDATE metadata with manual link (or separate junction table)
- `pms_audit_log(+id, +yacht_id, +action, +entity_type, +entity_id, +user_id, +new_values, +signature, +created_at)` - INSERT audit entry

**Ledger Event:** Yes - `equipment_manual_linked`

**Audit Log:** Yes

**RLS Boundary:** User must have access to equipment's yacht_id

**Commit Type:** `informational`

**Verified:** ⚠️ UNVERIFIED (manual linking mechanism not confirmed)

---

### 46. view_equipment_history

**Pattern:** `[READ_ONLY]`

**Reads:**
- `pms_equipment(id, yacht_id)` - to get equipment
- `pms_faults(equipment_id, title, severity, status, detected_at)` - to get fault history
- `pms_work_orders(equipment_id, wo_number, title, status, created_at, completed_at)` - to get WO history
- `pms_audit_log(entity_type='equipment', entity_id, action, created_at)` - to get full audit trail

**Writes:** None

**Ledger Event:** No

**Audit Log:** No (read-only)

**RLS Boundary:** User must have access to equipment's yacht_id

**Commit Type:** `informational`

**Verified:** ✅ VERIFIED

---

## CHECKLIST CLUSTER ACTIONS

### 47. create_checklist

**Pattern:** `[MUTATE_LOW]` `[MULTI_STEP]`

**Reads:**
- `pms_equipment(id, yacht_id)` - IF checklist linked to equipment
- `pms_work_orders(id, yacht_id)` - IF checklist linked to work order

**Writes:**
- `pms_checklists(+id, +yacht_id, +name, +description, +checklist_type, +equipment_id, +work_order_id, +status='draft', +is_template, +created_at, +created_by)` - INSERT new checklist
- `pms_audit_log(+id, +yacht_id, +action, +entity_type='checklist', +entity_id, +user_id, +new_values, +signature, +created_at)` - INSERT audit entry

**Ledger Event:** Yes - `checklist_created`

**Audit Log:** Yes

**RLS Boundary:** User must have access to yacht_id

**Commit Type:** `informational`

**Verified:** ✅ VERIFIED

---

### 48. add_checklist_item

**Pattern:** `[MUTATE_LOW]` `[SINGLE_STEP]`

**Reads:**
- `pms_checklists(id, yacht_id)` - to validate checklist exists

**Writes:**
- `pms_checklist_items(+id, +yacht_id, +checklist_id, +description, +instructions, +sequence, +is_required, +requires_photo, +requires_signature, +requires_value, +value_type, +value_unit, +value_min, +value_max, +status='pending', +created_at, +created_by)` - INSERT new item
- `pms_checklists(~total_items, ~updated_at)` - UPDATE via trigger
- `pms_audit_log(+id, +yacht_id, +action, +entity_type='checklist_item', +entity_id, +user_id, +new_values, +signature, +created_at)` - INSERT audit entry

**Ledger Event:** Yes - `checklist_item_added`

**Audit Log:** Yes

**RLS Boundary:** User must have access to checklist's yacht_id

**Commit Type:** `informational`

**Verified:** ✅ VERIFIED

---

### 49. complete_checklist_item

**Pattern:** `[MUTATE_LOW]` `[SINGLE_STEP]`

**Reads:**
- `pms_checklist_items(id, is_required, requires_photo, requires_signature, requires_value, yacht_id)` - to validate requirements

**Writes:**
- `pms_checklist_items(~is_completed=true, ~completed_at, ~completed_by, ~completion_notes, ~recorded_value, ~recorded_at, ~recorded_by, ~photo_url, ~signature_data, ~status='completed', ~updated_at, ~updated_by)` - UPDATE item
- `pms_checklists(~completed_items, ~updated_at)` - UPDATE via trigger
- `pms_audit_log(+id, +yacht_id, +action, +entity_type='checklist_item', +entity_id, +user_id, +old_values, +new_values, +signature, +created_at)` - INSERT audit entry

**Ledger Event:** Yes - `checklist_item_completed`

**Audit Log:** Yes

**RLS Boundary:** User must have access to item's yacht_id

**Commit Type:** `informational`

**Verified:** ✅ VERIFIED

---

### 50. skip_checklist_item

**Pattern:** `[MUTATE_LOW]` `[SINGLE_STEP]`

**Reads:**
- `pms_checklist_items(id, is_required, yacht_id)` - to validate item is skippable (not required)

**Writes:**
- `pms_checklist_items(~status='skipped', ~completion_notes, ~updated_at, ~updated_by)` - UPDATE item
- `pms_audit_log(+id, +yacht_id, +action, +entity_type, +entity_id, +user_id, +old_values, +new_values, +signature, +created_at)` - INSERT audit entry

**Ledger Event:** Yes - `checklist_item_skipped`

**Audit Log:** Yes

**RLS Boundary:** User must have access to item's yacht_id

**Commit Type:** `informational`

**Verified:** ✅ VERIFIED

---

### 51. complete_checklist

**Pattern:** `[MUTATE_MEDIUM]` `[SINGLE_STEP]` `[SIGNATURE_REQUIRED]`

**Reads:**
- `pms_checklists(id, total_items, completed_items, is_required, yacht_id)` - to validate all required items completed
- `pms_checklist_items(checklist_id, is_required, is_completed)` - to verify completion

**Writes:**
- `pms_checklists(~status='completed', ~completed_at, ~completed_by, ~updated_at, ~updated_by)` - UPDATE checklist status
- `pms_audit_log(+id, +yacht_id, +action, +entity_type='checklist', +entity_id, +user_id, +old_values, +new_values, +signature, +created_at)` - INSERT audit entry

**Ledger Event:** Yes - `checklist_completed`

**Audit Log:** Yes

**RLS Boundary:** User must have access to checklist's yacht_id

**Commit Type:** `irreversible` (completion milestone)

**Verified:** ⚠️ UNVERIFIED (completed_at, completed_by not in pms_checklists schema)

**Signature:** Yes - requires digital signature

---

## DOCUMENT CLUSTER ACTIONS

### 52. upload_document

**Pattern:** `[MUTATE_LOW]` `[SINGLE_STEP]`

**Reads:** None (new document)

**Writes:**
- Documents table (UNVERIFIED) - INSERT new document record
- Supabase Storage - upload file
- `pms_audit_log(+id, +yacht_id, +action, +entity_type='document', +entity_id, +user_id, +new_values, +signature, +created_at)` - INSERT audit entry

**Ledger Event:** Yes - `document_uploaded`

**Audit Log:** Yes

**RLS Boundary:** User must have access to yacht_id

**Commit Type:** `informational`

**Verified:** ⚠️ UNVERIFIED (documents table not found in schema)

**Note:** May use pms_attachments with entity_type='document' and entity_id=NULL.

---

### 53. link_document_to_equipment

**Pattern:** `[MUTATE_LOW]` `[SINGLE_STEP]`

**Reads:**
- `pms_equipment(id, yacht_id)` - to validate equipment
- Documents table (UNVERIFIED) - to validate document

**Writes:**
- Equipment-document junction table (UNVERIFIED) - INSERT link
- `pms_audit_log(+id, +yacht_id, +action, +entity_type='equipment_document_link', +entity_id, +user_id, +new_values, +signature, +created_at)` - INSERT audit entry

**Ledger Event:** Yes - `document_linked`

**Audit Log:** Yes

**RLS Boundary:** User must have access to yacht_id

**Commit Type:** `informational`

**Verified:** ⚠️ UNVERIFIED

---

### 54. search_documents

**Pattern:** `[READ_ONLY]`

**Reads:**
- Documents table (UNVERIFIED) - to search document metadata
- RAG search chunks (external) - to search document content

**Writes:**
- `suggestion_log(+id, +yacht_id, +user_id, +query_text, +search_query_id, +created_at)` - INSERT search log entry

**Ledger Event:** No (search action logged but not ledger event)

**Audit Log:** No

**RLS Boundary:** User must have access to yacht_id

**Commit Type:** `informational`

**Verified:** ⚠️ UNVERIFIED (documents table not found)

---

## ATTACHMENT ACTIONS (CROSS-ENTITY)

### 55. add_photo

**Pattern:** `[MUTATE_LOW]` `[SINGLE_STEP]`

**Reads:**
- Entity table (e.g., `pms_faults`, `pms_work_orders`) - to validate entity exists

**Writes:**
- `pms_attachments(+id, +yacht_id, +entity_type, +entity_id, +filename, +original_filename, +mime_type, +file_size, +storage_path, +width, +height, +thumbnail_path, +uploaded_by, +uploaded_at, +created_at)` - INSERT attachment record
- Supabase Storage - upload file
- `pms_audit_log(+id, +yacht_id, +action, +entity_type='attachment', +entity_id, +user_id, +new_values, +signature, +created_at)` - INSERT audit entry

**Ledger Event:** Yes - `attachment_added`

**Audit Log:** Yes

**RLS Boundary:** User must have access to yacht_id

**Commit Type:** `informational`

**Verified:** ✅ VERIFIED

---

### 56. remove_photo

**Pattern:** `[MUTATE_LOW]` `[SINGLE_STEP]`

**Reads:**
- `pms_attachments(id, yacht_id, uploaded_by)` - to validate attachment and permission

**Writes:**
- `pms_attachments(~deleted_at, ~deleted_by, ~deletion_reason)` - Soft delete attachment
- Supabase Storage - (optionally) delete file
- `pms_audit_log(+id, +yacht_id, +action, +entity_type='attachment', +entity_id, +user_id, +old_values, +signature, +created_at)` - INSERT audit entry

**Ledger Event:** Yes - `attachment_removed`

**Audit Log:** Yes

**RLS Boundary:** User must be uploader OR HOD

**Commit Type:** `informational`

**Verified:** ✅ VERIFIED

---

## SITUATION ENGINE ACTIONS

### 57. detect_symptom_recurrence

**Pattern:** `[READ_ONLY]` (system action, not user-initiated)

**Reads:**
- `symptom_reports(yacht_id, equipment_label, symptom_code, created_at, resolved)` - to count occurrences
- `pms_faults(equipment_id, fault_code, title, detected_at, resolved_at)` - to include fault history

**Writes:**
- `situation_detections(+id, +yacht_id, +situation_type='symptom_recurrence', +severity, +label, +evidence, +recommendations, +created_at)` - INSERT situation detection

**Ledger Event:** No (system detection)

**Audit Log:** No

**RLS Boundary:** System action, yacht-scoped

**Commit Type:** `informational`

**Verified:** ✅ VERIFIED

**Note:** Background process, uses `check_symptom_recurrence()` function.

---

### 58. log_symptom

**Pattern:** `[MUTATE_LOW]` `[SINGLE_STEP]`

**Reads:**
- `pms_equipment(id, name, yacht_id)` - to validate equipment

**Writes:**
- `symptom_reports(+id, +yacht_id, +equipment_label, +symptom_code, +symptom_label, +search_query_id, +reported_by, +source='manual', +created_at)` - INSERT symptom report

**Ledger Event:** No (informational logging)

**Audit Log:** No

**RLS Boundary:** User must have access to yacht_id

**Commit Type:** `informational`

**Verified:** ✅ VERIFIED

---

### 59. update_predictive_state

**Pattern:** `[MUTATE_LOW]` (system action, not user-initiated)

**Reads:**
- `pms_equipment(id, yacht_id)` - to get equipment
- `pms_faults(equipment_id, created_at, severity)` - to calculate risk
- `pms_work_orders(equipment_id, created_at, completed_at)` - to calculate maintenance trends

**Writes:**
- `predictive_state(~risk_score, ~confidence, ~failure_probability, ~trend, ~anomalies, ~failure_modes, ~recommended_actions, ~next_maintenance_due, ~last_updated)` - UPSERT predictive state

**Ledger Event:** No (system calculation)

**Audit Log:** No

**RLS Boundary:** System action, yacht-scoped

**Commit Type:** `informational`

**Verified:** ✅ VERIFIED

**Note:** Background process, likely ML/rules-based.

---

## SEARCH & RAG ACTIONS

### 60. search

**Pattern:** `[READ_ONLY]`

**Reads:**
- All operational tables (pms_faults, pms_work_orders, pms_equipment, pms_parts, etc.) - to search entities
- RAG search chunks (external) - to search document content
- `user_profiles(yacht_id)` - for RLS filtering

**Writes:**
- `suggestion_log(+id, +yacht_id, +user_id, +query_text, +intent, +search_query_id, +created_at)` - INSERT search log entry

**Ledger Event:** No

**Audit Log:** No

**RLS Boundary:** User must have access to yacht_id

**Commit Type:** `informational`

**Verified:** ✅ VERIFIED

---

### 61. rag_suggest_action

**Pattern:** `[READ_ONLY]`

**Reads:**
- RAG search chunks (external) - to find relevant manual sections
- `pms_equipment(id, manufacturer, model)` - to contextualize suggestions
- `pms_faults(id, title, equipment_id)` - to understand current situation

**Writes:**
- `suggestion_log(+id, +yacht_id, +user_id, +query_text, +intent, +situation_detected, +situation_type, +suggested_actions, +search_query_id, +created_at)` - INSERT suggestion log entry

**Ledger Event:** No

**Audit Log:** No

**RLS Boundary:** User must have access to yacht_id

**Commit Type:** `informational`

**Verified:** ✅ VERIFIED

**Note:** RAG suggestions never execute, only suggest.

---

### 62. rag_prefill

**Pattern:** `[READ_ONLY]`

**Reads:**
- RAG search chunks (external) - to extract prefill data
- Entity tables (context-dependent) - to validate prefill targets

**Writes:**
- `suggestion_log(+id, +yacht_id, +user_id, +query_text, +intent, +suggested_actions, +created_at)` - INSERT suggestion log entry (optional)

**Ledger Event:** No

**Audit Log:** No

**RLS Boundary:** User must have access to yacht_id

**Commit Type:** `informational`

**Verified:** ✅ VERIFIED

**Note:** Prefill values never commit without user acceptance.

---

## ACTION EXECUTION LOGGING

### 63. log_action_execution

**Pattern:** Internal system action (not user-facing)

**Reads:** None

**Writes:**
- `action_executions(+id, +yacht_id, +user_id, +action_name, +entity_type, +entity_id, +params, +result, +success, +error_code, +error_message, +duration_ms, +created_at)` - INSERT execution log

**Ledger Event:** No (internal logging)

**Audit Log:** No (separate from audit_log)

**RLS Boundary:** System action, yacht-scoped

**Commit Type:** `informational`

**Verified:** ✅ VERIFIED

**Note:** Every action execution should log to this table for performance monitoring.

---

## UNIMPLEMENTED ACTIONS (BATCH 3+)

The following actions are referenced in cluster documents but not yet documented here. These are for future batches (Batch 3 and beyond).

### 64-71. Future Actions (UNVERIFIED)

**Clusters pending:**
- Maintenance Scheduling (schedule_pm, create_pm_template, etc.)
- Crew Management (assign_role, manage_permissions, etc.)
- Notifications (send_alert, subscribe_to_entity, etc.)
- Reporting (generate_report, export_data, etc.)

**Status:** UNVERIFIED - not documented yet, awaiting Batch 3 specification

---

## SUMMARY STATISTICS

**Total Actions Documented:** 63
**Actions with Verified Schema:** 39 (62%)
**Actions with Unverified Schema:** 24 (38%)
**Actions Requiring Signature:** 8 (adjust_inventory, complete_work_order, approve_purchase_order, commit_session, decommission_equipment, complete_checklist, etc.)
**Irreversible Actions:** 10 (adjust_inventory, log_part_usage, restock_part, complete_work_order, commit_session, change_equipment_status, decommission_equipment, etc.)
**Read-Only Actions:** 9 (search, view_equipment_history, export_handover, generate_summary, etc.)

---

## VERIFICATION CHECKLIST

### High-Priority Unverified Actions (Require Schema Migration)
1. **diagnose_fault** - diagnosis columns not in pms_faults
2. **add_fault_note** - fault notes mechanism unclear
3. **start_work_order** - started_at/started_by not in schema
4. **add_wo_hours** - hours_logged not in schema
5. **add_to_shopping_list** - shopping_list table missing
6. **create_purchase_order** - PO items table missing
7. **approve_purchase_order** - approved_by/approved_at not in schema
8. **receive_items** - receiving_sessions table missing
9. **commit_session** - receiving logic not confirmed
10. **complete_checklist** - completed_at/completed_by not in pms_checklists schema

### Medium-Priority Unverified Actions (May Use JSONB or Alternative)
11. **close_fault** - closed_at/closed_by not in schema
12. **defer_fault** - deferred_until/deferral_reason not in schema
13. **reopen_work_order** - reopened_at/reopened_by not in schema
14. **cancel_work_order** - cancelled_at/cancelled_by not in schema
15. **decommission_equipment** - decommissioned_at/decommissioned_by not in schema
16. **link_equipment_to_manual** - linking mechanism unclear

### Low-Priority Unverified Actions (Document/Attachment System)
17. **upload_document** - documents table missing
18. **link_document_to_equipment** - junction table missing
19. **add_document_to_handover** - document entity type
20. **add_document_section_to_handover** - document_page/snippet columns

---

## USAGE GUIDELINES

### For Backend Developers
1. **Before implementing an action**, check this matrix for reads/writes
2. **Always write to pms_audit_log** if Audit Log = Yes
3. **Always write to ledger** if Ledger Event = Yes
4. **Always check RLS boundary** before executing
5. **If action is UNVERIFIED**, coordinate with DBA for schema migration

### For Frontend Developers
1. **Check Commit Type** to determine if action needs confirmation dialog
2. **If Signature Required = Yes**, implement signature capture flow
3. **If action is UNVERIFIED**, flag as "Coming Soon" or hide from UI
4. **For Irreversible actions**, show warning to user before execution

### For QA/Testing
1. **For each action**, verify all specified tables are written
2. **Check audit_log entry** exists after every mutation
3. **Verify RLS** by attempting action with unauthorized user
4. **For signature actions**, verify signature_data in audit_log

---

**Status:** ACTION_IO_MATRIX complete for P0/MVP actions (63 actions documented). Batch 3+ actions pending future work.
