# Microaction Matrix Scale-up Plan

**Generated:** 2026-01-20
**Target:** 710+ test cases (71 actions × 10 variants)

## Current State

- **Backend actions implemented:** 31+
- **Frontend actions registered:** 15
- **Current E2E tests:** 10 cases

## All Implemented Actions (31)

### Cluster 01: Fix Something (Faults)
| Action | Type | Status |
|--------|------|--------|
| report_fault | WRITE | Tested |
| acknowledge_fault | WRITE | Not tested |
| resolve_fault | WRITE | Not tested |
| diagnose_fault | WRITE | Not tested |
| close_fault | WRITE | Not tested |
| update_fault | WRITE | Not tested |
| reopen_fault | WRITE | Not tested |
| mark_fault_false_alarm | WRITE | Not tested |
| add_fault_photo | WRITE | Not tested |
| view_fault_detail | READ | Not tested |
| list_faults | READ | Not tested |

### Cluster 02: Do Maintenance (Work Orders)
| Action | Type | Status |
|--------|------|--------|
| create_work_order_from_fault | WRITE | Not tested |
| add_note_to_work_order | WRITE | Not tested |
| add_part_to_work_order | WRITE | Not tested |
| mark_work_order_complete | WRITE | Not tested |
| add_work_order_photo | WRITE | Not tested |
| add_parts_to_work_order | WRITE | Not tested |
| view_work_order_checklist | READ | Not tested |
| view_worklist | READ | Tested |
| add_worklist_task | WRITE | Tested |
| export_worklist | READ | Tested |
| create_work_order | WRITE | Tested |

### Cluster 03: Equipment
| Action | Type | Status |
|--------|------|--------|
| update_equipment_status | WRITE | Tested |
| view_equipment | READ | Not tested |
| view_equipment_detail | READ | Not tested |

### Cluster 04: Inventory
| Action | Type | Status |
|--------|------|--------|
| check_stock_level | READ | Not tested |
| log_part_usage | WRITE | Not tested |

### Cluster 05: Handover
| Action | Type | Status |
|--------|------|--------|
| add_to_handover | WRITE | Tested |
| edit_handover_section | WRITE | Not tested |
| export_handover | READ | Not tested |

### Cluster 07: Documents
| Action | Type | Status |
|--------|------|--------|
| show_manual_section | READ | Not tested |
| upload_document | WRITE | Not tested |
| view_document | READ | Not tested |
| delete_document | WRITE | Not tested |

### Cluster 08: Purchasing
| Action | Type | Status |
|--------|------|--------|
| delete_shopping_item | WRITE | Not tested |

## Test Variants Per Action (10 types)

For each action, create:

1. **POSITIVE_VALID** - Happy path with all required fields
2. **POSITIVE_OPTIONAL** - With optional fields populated
3. **POSITIVE_EDGE** - Edge case values (empty strings, max lengths)
4. **NEGATIVE_MISSING_REQUIRED** - Missing required field(s)
5. **NEGATIVE_INVALID_TYPE** - Wrong data type for field
6. **NEGATIVE_INVALID_ID** - Non-existent entity reference
7. **NEGATIVE_PERMISSION** - Wrong role/yacht isolation
8. **NEGATIVE_DUPLICATE** - Duplicate operation (if applicable)
9. **NEGATIVE_STATE** - Invalid state transition
10. **NEGATIVE_BOUNDARY** - Out of bounds values

## Coverage Target

| Category | Actions | Variants | Total Tests |
|----------|---------|----------|-------------|
| Cluster 01 | 11 | 10 | 110 |
| Cluster 02 | 11 | 10 | 110 |
| Cluster 03 | 3 | 10 | 30 |
| Cluster 04 | 2 | 10 | 20 |
| Cluster 05 | 3 | 10 | 30 |
| Cluster 07 | 4 | 10 | 40 |
| Cluster 08 | 1 | 10 | 10 |
| **Total** | **35** | **10** | **350** |

To reach 710+, we need ~71 actions. The remaining ~36 actions would come from:
- Frontend-only actions (add_note, order_part, etc.)
- Sub-actions (prefill, preview endpoints)
- Future actions (compliance, certificates, hours of rest)

## Immediate Priority

1. Complete all Cluster 01 actions (faults) - 11 actions × 10 = 110 tests
2. Complete all Cluster 02 actions (work orders) - 11 actions × 10 = 110 tests
3. Complete remaining clusters

## DB Mutation Map (for WRITE actions)

```typescript
const ACTION_MUTATION_MAP: Record<string, MutationConfig> = {
  // Cluster 01: Faults
  'report_fault': { table: 'pms_faults', type: 'INSERT' },
  'acknowledge_fault': { table: 'pms_faults', type: 'UPDATE', idField: 'fault_id' },
  'resolve_fault': { table: 'pms_faults', type: 'UPDATE', idField: 'fault_id' },
  'diagnose_fault': { table: 'pms_faults', type: 'UPDATE', idField: 'fault_id' },
  'close_fault': { table: 'pms_faults', type: 'UPDATE', idField: 'fault_id' },
  'update_fault': { table: 'pms_faults', type: 'UPDATE', idField: 'fault_id' },
  'reopen_fault': { table: 'pms_faults', type: 'UPDATE', idField: 'fault_id' },
  'mark_fault_false_alarm': { table: 'pms_faults', type: 'UPDATE', idField: 'fault_id' },
  'add_fault_photo': { table: 'pms_faults', type: 'UPDATE', idField: 'fault_id' },

  // Cluster 02: Work Orders
  'create_work_order': { table: 'pms_work_orders', type: 'INSERT' },
  'create_work_order_from_fault': { table: 'pms_work_orders', type: 'INSERT' },
  'add_worklist_task': { table: 'pms_work_orders', type: 'INSERT' },
  'add_note_to_work_order': { table: 'pms_work_orders', type: 'UPDATE', idField: 'work_order_id' },
  'add_part_to_work_order': { table: 'pms_work_orders', type: 'UPDATE', idField: 'work_order_id' },
  'mark_work_order_complete': { table: 'pms_work_orders', type: 'UPDATE', idField: 'work_order_id' },
  'add_work_order_photo': { table: 'pms_work_orders', type: 'UPDATE', idField: 'work_order_id' },
  'add_parts_to_work_order': { table: 'pms_work_orders', type: 'UPDATE', idField: 'work_order_id' },

  // Cluster 03: Equipment
  'update_equipment_status': { table: 'pms_equipment', type: 'UPDATE', idField: 'equipment_id' },

  // Cluster 05: Handover
  'add_to_handover': { table: 'pms_handover', type: 'INSERT' },
  'edit_handover_section': { table: 'pms_handover', type: 'UPDATE', idField: 'handover_id' },

  // Cluster 07: Documents
  'upload_document': { table: 'documents', type: 'INSERT' },
  'delete_document': { table: 'documents', type: 'DELETE', idField: 'document_id' },
};
```

## Next Steps

1. Expand `microactions_matrix_strict.spec.ts` with all 31 actions
2. Add 10 variants per action
3. Verify DB mutation proof for each WRITE action
4. Generate JSONL results with all gates verified
