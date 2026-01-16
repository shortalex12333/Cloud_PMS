# PHASE 2: MAP

**Prerequisite:** PHASE_1_REPORT.md exists and user approved

**Objective:** Map relationships between tests, handlers, database, and specs.

**DO:** Create diagrams, trace data flow, identify dependencies
**DO NOT:** Write code, modify files

---

## TEST ISOLATION PRINCIPLE

Tests MUST be isolated. For each test:
- **QUERY** real IDs from existing data (read-only)
- **CREATE** test-specific data with unique identifiers
- **TEST** the operation using that data
- **CLEANUP** only what YOU created (never existing data)

Pattern:
```typescript
// GOOD: Query existing, create test copy, test, cleanup copy
const realOrder = await getExistingWorkOrder();  // READ ONLY
const testOrder = await createTestWorkOrder();   // YOUR DATA
await test(testOrder.id);                        // TEST YOUR DATA
await deleteTestWorkOrder(testOrder.id);         // CLEANUP YOUR DATA

// BAD: Delete existing data
await supabase.from('documents').delete().eq('id', realDocId);  // NEVER DO THIS
```

---

## TASK

1. **Read the specification:**
```
/Users/celeste7/Desktop/Cloud_PMS_docs_v2/COMPLETE_ACTION_EXECUTION_CATALOG.md
/Users/celeste7/Desktop/Cloud_PMS_docs_v2/03_MICROACTIONS/MICRO_ACTION_REGISTRY.md
```

2. **For each failing test, trace the full path:**
```
Test → Handler → Database Table → Expected Data
```

3. **Map what tests expect vs what exists:**

| Test | Expected Table | Actual Table | Gap |
|------|----------------|--------------|-----|
| add_wo_part | work_order_parts | pms_work_orders.metadata | No dedicated table |

4. **Map test data requirements:**

| Test | Needs | From Table | Exists? |
|------|-------|------------|---------|
| add_wo_part | work_order_id | pms_work_orders | Yes, query needed |
| delete_document | document_id | documents | ? |

---

## OUTPUT REQUIRED

Create file: `/Users/celeste7/Documents/Cloud_PMS/PHASE_2_MAP.md`

```markdown
# Phase 2 Report: Mapping

## Test → Handler → Database Flow

### Failing Test 1: [name]
```
Test File: [path]
     ↓
Handler: [function name in path]
     ↓
Database Operation: [INSERT/UPDATE/SELECT on table]
     ↓
Expected Response: [200 with data shape]
     ↓
Actual Response: [404/500 because...]
```

### Failing Test 2: [name]
...

## Schema Gaps

| What Spec Says | What Exists | Gap |
|----------------|-------------|-----|
| ... | ... | ... |

## Test Data Requirements

| Test | Prerequisite Data | How to Get It |
|------|-------------------|---------------|
| add_wo_part | Real work_order_id | Query pms_work_orders |
| ... | ... | ... |

## Dependency Graph
```
test_a depends on: [handler_x, table_y, fixture_z]
test_b depends on: [handler_x, table_w]
```

## Fix Strategy (Preview)
1. [First thing to fix]
2. [Second thing]
...
```

---

## STOP CONDITION

When PHASE_2_MAP.md is complete, STOP and say:

"Phase 2 complete. Map at /Users/celeste7/Documents/Cloud_PMS/PHASE_2_MAP.md. Ready for Phase 3."

**DO NOT proceed to Phase 3 without user approval.**
