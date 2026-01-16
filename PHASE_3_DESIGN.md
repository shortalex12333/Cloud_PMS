# PHASE 3: DESIGN

**Prerequisite:** PHASE_2_MAP.md exists and user approved

**Objective:** Design the fix strategy before writing any code.

**DO:** Write pseudocode, plan file changes, design test fixtures
**DO NOT:** Actually modify files yet

---

## FIXTURE DESIGN RULES

### Rule 1: Test Data Namespace
All test-created data MUST have identifiable markers:
```typescript
const TEST_PREFIX = 'TEST_';
const testDocName = `${TEST_PREFIX}doc_${Date.now()}`;
```

### Rule 2: Cleanup Only Your Data
```typescript
// CORRECT cleanup
await supabase.from('documents')
  .delete()
  .like('name', 'TEST_%');  // Only test-created items

// WRONG cleanup
await supabase.from('documents')
  .delete()
  .eq('yacht_id', testYachtId);  // Deletes EVERYTHING
```

### Rule 3: Use Existing Data Read-Only
```typescript
// Get real work order ID for testing
async function getTestWorkOrderId() {
  const { data } = await supabase
    .from('pms_work_orders')
    .select('id')
    .eq('yacht_id', TEST_YACHT_ID)
    .limit(1)
    .single();
  return data?.id;  // READ ONLY - never modify this
}
```

### Rule 4: If Test Needs to Modify Data, Create Your Own
```typescript
// Create test-specific record you can safely modify
const testOrder = await supabase.from('pms_work_orders').insert({
  yacht_id: TEST_YACHT_ID,
  name: `TEST_order_${Date.now()}`,
  // ... other fields
}).select().single();

// Now safe to test modifications on testOrder.id
```

---

## TASK

1. **Design test fixtures system:**
```
Where will fixtures live?
How will tests get real IDs?
What's the create/cleanup strategy?
```

2. **Design handler fixes (if needed):**
```
Which handlers need validation?
What error responses should they return?
```

3. **Design database changes (if needed):**
```
Any tables to create?
Any columns to add?
Any RLS policies?
```

4. **Write pseudocode for each fix category:**

---

## OUTPUT REQUIRED

Create file: `/Users/celeste7/Documents/Cloud_PMS/PHASE_3_DESIGN.md`

```markdown
# Phase 3 Report: Design

## Test Fixtures Design

### File Structure
```
/tests/e2e/
├── fixtures/
│   ├── testData.ts      ← Query real IDs
│   ├── setup.ts         ← Create test data
│   └── teardown.ts      ← Cleanup
```

### testData.ts Pseudocode
```typescript
// Get real work order ID from test yacht
async function getTestWorkOrderId() {
  // Query pms_work_orders where yacht_id = TEST_YACHT_ID
  // Return first result's ID
}
```

## Handler Fix Design

### Handler: [name]
Current behavior: [what it does]
Problem: [why it fails]
Fix: [pseudocode]
```typescript
// Add validation at start
// Add try/catch
// Return proper status codes
```

## Database Changes (if any)

### Table: [name]
```sql
-- Pseudocode for migration
CREATE TABLE IF NOT EXISTS ...
```

## Files to Modify

| File | Change Type | Description |
|------|-------------|-------------|
| tests/e2e/fixtures/testData.ts | CREATE | Test data helpers |
| tests/e2e/microactions/vigorous_test_matrix.spec.ts | MODIFY | Use real IDs |
| apps/web/src/lib/microactions/handlers/workOrders.ts | MODIFY | Add validation |

## Implementation Order

1. Create test fixtures (no risk, additive)
2. Update tests to use fixtures (tests will fail until handlers fixed)
3. Fix handlers (tests should pass after)
4. Run full suite

## Estimated Changes
- Files to create: X
- Files to modify: Y
- Lines of code: ~Z
```

---

## STOP CONDITION

When PHASE_3_DESIGN.md is complete, STOP and say:

"Phase 3 complete. Design at /Users/celeste7/Documents/Cloud_PMS/PHASE_3_DESIGN.md. Ready for Phase 4 implementation."

**DO NOT proceed to Phase 4 without user approval.**
