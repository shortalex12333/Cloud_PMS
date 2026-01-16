# FIX TESTS PROPERLY - NO RIGGING

## WHAT WENT WRONG

Claude rigged tests to accept failures:
```
delete_document:      200 → 404  ❌ WRONG
delete_shopping_item: 200 → 404  ❌ WRONG
add_wo_part:          200 → 500  ❌ WRONG (accepting crashes!)
tenant_key_alias:     exact → regex  ❌ WRONG (loosened validation)
```

**This is cheating. Tests should FAIL if functionality is broken.**

---

## THE REAL PROBLEM

Tests use fake UUIDs that don't exist:
```typescript
// Test sends:
{ work_order_id: '550e8400-e29b-41d4-a716-446655440000' }  // FAKE - doesn't exist

// Handler tries:
await supabase.from('pms_work_orders').select().eq('id', '550e8400...').single();
// Result: No rows → Error → 404 or 500
```

---

## THE CORRECT FIX

### Option 1: Use Real IDs from Database

Query the database for real IDs to use in tests:

```typescript
// In test setup
const { data: realWorkOrder } = await supabase
  .from('pms_work_orders')
  .select('id')
  .limit(1)
  .single();

// Use in test
const response = await executeAction('add_wo_part', {
  work_order_id: realWorkOrder.id,  // REAL ID
  part_id: realPartId
});
expect(response.status).toBe(200);
```

### Option 2: Create Test Fixtures (Better)

Create → Test → Cleanup pattern:

```typescript
describe('add_wo_part', () => {
  let testWorkOrderId: string;
  let testPartId: string;

  beforeAll(async () => {
    // CREATE test data
    const { data: wo } = await supabase
      .from('pms_work_orders')
      .insert({
        title: 'TEST_WO_' + Date.now(),
        yacht_id: TEST_YACHT_ID,
        status: 'open'
      })
      .select()
      .single();
    testWorkOrderId = wo.id;

    const { data: part } = await supabase
      .from('pms_parts')
      .insert({
        name: 'TEST_PART_' + Date.now(),
        yacht_id: TEST_YACHT_ID
      })
      .select()
      .single();
    testPartId = part.id;
  });

  afterAll(async () => {
    // CLEANUP test data
    await supabase.from('pms_work_orders').delete().eq('id', testWorkOrderId);
    await supabase.from('pms_parts').delete().eq('id', testPartId);
  });

  test('adds part to work order', async () => {
    const response = await executeAction('add_wo_part', {
      work_order_id: testWorkOrderId,  // REAL, created in beforeAll
      part_id: testPartId
    });

    expect(response.status).toBe(200);  // Should ACTUALLY be 200
    expect(response.data.success).toBe(true);
  });
});
```

### Option 3: Use Known Test Data (Simplest)

If database has known test records:

```
TEST_USER_EMAIL=x@alex-short.com
TEST_USER_YACHT_ID=85fe1119-b04c-41ac-80f1-829d23322598
```

Query for real IDs belonging to this yacht:

```typescript
// Get real work order from test yacht
const { data } = await supabase
  .from('pms_work_orders')
  .select('id')
  .eq('yacht_id', TEST_USER_YACHT_ID)
  .limit(1)
  .single();

const REAL_WORK_ORDER_ID = data.id;
```

---

## STEP BY STEP FIX

### Step 1: Revert the Rigged Changes

```bash
# Find what was changed
git diff HEAD~5 -- tests/

# Revert test expectation changes
git checkout HEAD~5 -- tests/e2e/microactions/vigorous_test_matrix.spec.ts
# (or manually undo the 200→404 changes)
```

### Step 2: Create Test Fixtures Helper

Create: `/tests/e2e/fixtures/testData.ts`

```typescript
import { createClient } from '@supabase/supabase-js';

const supabase = createClient(
  process.env.TENANT_SUPABASE_URL!,
  process.env.TENANT_SUPABASE_SERVICE_ROLE_KEY!
);

const TEST_YACHT_ID = process.env.TEST_USER_YACHT_ID!;

export async function getTestWorkOrderId(): Promise<string> {
  const { data } = await supabase
    .from('pms_work_orders')
    .select('id')
    .eq('yacht_id', TEST_YACHT_ID)
    .eq('status', 'open')
    .limit(1)
    .single();

  if (!data) throw new Error('No test work order found');
  return data.id;
}

export async function getTestEquipmentId(): Promise<string> {
  const { data } = await supabase
    .from('pms_equipment')
    .select('id')
    .eq('yacht_id', TEST_YACHT_ID)
    .limit(1)
    .single();

  if (!data) throw new Error('No test equipment found');
  return data.id;
}

export async function getTestPartId(): Promise<string> {
  const { data } = await supabase
    .from('pms_parts')
    .select('id')
    .eq('yacht_id', TEST_YACHT_ID)
    .limit(1)
    .single();

  if (!data) throw new Error('No test part found');
  return data.id;
}

export async function getTestFaultId(): Promise<string> {
  const { data } = await supabase
    .from('pms_faults')
    .select('id')
    .eq('yacht_id', TEST_YACHT_ID)
    .limit(1)
    .single();

  if (!data) throw new Error('No test fault found - create one first');
  return data.id;
}
```

### Step 3: Update Tests to Use Real Data

```typescript
import { getTestWorkOrderId, getTestPartId } from '../fixtures/testData';

test('add_wo_part adds part to work order', async () => {
  const workOrderId = await getTestWorkOrderId();
  const partId = await getTestPartId();

  const response = await executeAction('add_wo_part', {
    work_order_id: workOrderId,
    part_id: partId
  });

  expect(response.status).toBe(200);  // NOW THIS SHOULD ACTUALLY WORK
});
```

### Step 4: Run Tests

```bash
npx playwright test tests/e2e/microactions/vigorous_test_matrix.spec.ts
```

If still fails → the HANDLER is broken → fix the handler

---

## WHAT SUCCESS LOOKS LIKE

```
✅ Test uses REAL data from database
✅ Handler processes REAL data
✅ Handler returns 200 because operation SUCCEEDED
✅ Test expects 200 and gets 200
✅ Test PASSES because functionality WORKS
```

NOT:
```
❌ Test uses FAKE UUID
❌ Handler can't find data
❌ Handler returns 404/500
❌ Test changed to expect 404/500
❌ Test "passes" but functionality is BROKEN
```

---

## REVERT THESE SPECIFIC CHANGES

File: `tests/e2e/microactions/vigorous_test_matrix.spec.ts`

| Line | Revert From | Revert To |
|------|-------------|-----------|
| delete_document | expectedStatus: 404 | expectedStatus: 200 |
| delete_shopping_item | expectedStatus: 404 | expectedStatus: 200 |
| add_wo_part | expectedStatus: 500 | expectedStatus: 200 |

Then fix the tests to use real data.

---

## PROMPT FOR CLAUDE

```
You rigged tests to accept failures. This is wrong. Fix properly:

1. REVERT the test expectation changes (404→200, 500→200)

2. CREATE test fixtures helper at /tests/e2e/fixtures/testData.ts that queries REAL IDs from database

3. UPDATE tests to use real IDs instead of fake UUIDs

4. RUN tests - they should ACTUALLY pass with 200 because real data exists

5. If handler still fails with real data, FIX THE HANDLER

Never change expected status from 200 to 404/500. That's cheating.

Read /Users/celeste7/Documents/Cloud_PMS/FIX_TESTS_PROPERLY.md for code examples.
```
