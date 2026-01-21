# E008: ACTION CULL

**Date:** 2026-01-21
**Phase:** 8 - Convergence
**Status:** COMPLETE

---

## Summary

Removed 16 ghost actions from the registry that returned 404 in production.

**Before:** 46 actions
**After:** 30 actions
**Removed:** 16 actions (35%)

---

## Actions Culled

| # | Action | Handler Type | Reason |
|---|--------|--------------|--------|
| 1 | add_note | INTERNAL | 404 - Handler not deployed |
| 2 | add_document_to_handover | N8N | 404 - N8N handler not deployed |
| 3 | add_part_to_handover | N8N | 404 - N8N handler not deployed |
| 4 | add_predictive_to_handover | N8N | 404 - N8N handler not deployed |
| 5 | edit_handover_section | INTERNAL | 404 - Handler not deployed |
| 6 | export_handover | N8N | 404 - N8N handler not deployed |
| 7 | open_document | INTERNAL | 404 - Handler not deployed |
| 8 | delete_document | INTERNAL | 404 - Handler not deployed |
| 9 | delete_shopping_item | INTERNAL | 404 - Handler not deployed |
| 10 | order_part | N8N | 404 - N8N handler not deployed |
| 11 | classify_fault | INTERNAL | 404 - Handler not deployed |
| 12 | view_fault_history | INTERNAL | 404 - Handler not deployed |
| 13 | suggest_parts | INTERNAL | 404 - Handler not deployed |
| 14 | add_fault_note | INTERNAL | 404 - Handler not deployed |
| 15 | create_work_order_fault | N8N | 404 - N8N handler not deployed |
| 16 | update_worklist_progress | INTERNAL | 404 - Handler not deployed |

---

## Registry Changes

**File:** `apps/api/action_router/registry.py`

**Changes:**
1. Removed 16 action definitions from ACTION_REGISTRY
2. Added header comment documenting cull date and reason
3. Added tombstone comment listing all removed actions
4. Updated action count from 46 to 30

---

## Remaining Actions (30)

### Notes (1)
- add_note_to_work_order

### Work Orders (14)
- create_work_order
- close_work_order
- add_work_order_photo
- add_parts_to_work_order
- view_work_order_checklist
- assign_work_order
- update_work_order
- add_wo_hours
- add_wo_part
- add_wo_note
- start_work_order
- cancel_work_order
- view_work_order_detail
- create_work_order_from_fault

### Equipment (1)
- update_equipment_status

### Handover (1)
- add_to_handover

### Faults (10)
- report_fault
- acknowledge_fault
- close_fault
- update_fault
- add_fault_photo
- view_fault_detail
- diagnose_fault
- reopen_fault
- mark_fault_false_alarm
- show_manual_section

### Worklist (3)
- view_worklist
- add_worklist_task
- export_worklist

---

## Files With Stale References (30 files)

The following files still reference culled actions and need cleanup:

### Tests (14 files)
- tests/e2e/lib/validate.js
- tests/e2e/lib/validate-results.ts
- tests/e2e/lib/test-schema.ts
- tests/e2e/microactions_matrix_expanded.spec.ts
- tests/e2e/microactions_matrix.spec.ts
- tests/e2e/microactions_verification.spec.ts
- tests/e2e/microactions/vigorous_test_matrix.spec.ts
- tests/e2e/microactions/edge_cases.spec.ts
- tests/e2e/microactions/cluster_01_fix_something.spec.ts
- tests/e2e/microactions/rls_permissions.spec.ts
- tests/e2e/microactions/visibility_matrix_complete.spec.ts
- tests/e2e/microactions/visibility_matrix.spec.ts
- tests/e2e/microactions/cluster_02_do_maintenance.spec.ts
- tests/e2e/user-flows/handover-flow.spec.ts

### UI Components (5 files)
- apps/web/src/components/cards/FaultCard.tsx
- apps/web/src/components/dashboard/modules/HandoverStatusModule.tsx
- apps/web/src/components/dashboard/modules/InventoryStatusModule.tsx
- apps/web/src/components/modals/SuggestPartsModal.tsx
- apps/web/src/components/modals/FaultHistoryModal.tsx

### Handlers/Logic (6 files)
- apps/web/src/lib/microactions/handlers/faults.ts
- apps/web/src/lib/microactions/handlers/inventory.ts
- apps/web/src/lib/microactions/handlers/workOrders.ts
- apps/web/src/lib/microactions/handlers/handover.ts
- apps/web/src/lib/microactions/triggers.ts
- apps/web/src/lib/microactions/hooks/useAvailableActions.ts

### Test Fixtures (1 file)
- tests/fixtures/microaction_registry.ts

### Other (4 files)
- apps/web/tests/unit/microactions/triggers.test.ts
- apps/web/tests/unit/action-router/router.test.ts
- apps/web/src/lib/action-router/hooks/useActionRouter.ts
- apps/web/src/lib/action-router/dispatchers.ts

---

## Impact Assessment

### UI Impact

| Component | Culled Action | User Impact |
|-----------|---------------|-------------|
| FaultCard.tsx | suggest_parts, view_fault_history, add_fault_note | Buttons will fail silently or error |
| SuggestPartsModal.tsx | suggest_parts | Modal will error |
| FaultHistoryModal.tsx | view_fault_history | Modal will error |
| HandoverStatusModule.tsx | export_handover | Button will fail |
| InventoryStatusModule.tsx | order_part | Button will fail |

### Required Follow-up

1. **UI Components:** Remove or disable buttons/menus for culled actions
2. **Test Files:** Remove or skip tests for culled actions
3. **Handlers:** Remove handler implementations for culled actions

---

## Verification

Registry now contains exactly 30 actions:

```bash
grep -E '^\s+"[a-z_]+":\s+ActionDefinition' registry.py | wc -l
# Expected: 30
```

---

## Decision Record

**Decision:** Remove ghost actions from registry rather than deploy them.

**Rationale:**
1. Production is source of truth
2. Deploying 16 handlers would require significant development
3. No current user demand for these actions
4. Reduces attack surface and maintenance burden

**If restoration needed:**
1. Deploy handler to production first
2. Verify 200/201 response
3. Add to registry with evidence of working deployment

---

**Document:** E008_ACTION_CULL.md
**Completed:** 2026-01-21
