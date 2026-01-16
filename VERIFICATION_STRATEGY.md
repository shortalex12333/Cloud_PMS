# Comprehensive Verification Strategy

**Goal:** Automate verification of all 57 microactions without manual testing bottleneck.

---

## Current Gaps

| Gap | Problem |
|-----|---------|
| Button visibility | Tests don't verify all 57 buttons appear in correct contexts |
| Trigger conditions | Tests don't verify buttons HIDE when conditions aren't met |
| Handler correctness | TypeScript handlers written without verifying Python spec match |
| RLS bypass | Tests use service key, not real user permissions |
| End-to-end flow | No tests verify button click → backend → database → UI update |

---

## Phase 7: Verification Test Suite

### 7A: Button Visibility Matrix

Create a test that verifies EVERY button appears in correct context:

```typescript
// tests/e2e/microactions/visibility_matrix.spec.ts

const MICROACTION_VISIBILITY = [
  // Cluster 01: Fix Something
  { action: 'diagnose_fault', context: 'fault_card', requiresStatus: ['open'], requiresRole: ['any'] },
  { action: 'suggest_parts', context: 'fault_card', requiresStatus: ['diagnosed'], requiresRole: ['any'] },
  { action: 'suggest_wo_for_fault', context: 'fault_card', requiresStatus: ['open', 'diagnosed'], requiresRole: ['hod'] },
  // ... all 57 microactions
];

for (const ma of MICROACTION_VISIBILITY) {
  test(`${ma.action} visible in ${ma.context} when conditions met`, async ({ page }) => {
    // Setup: Create entity with required status
    // Navigate to context
    // Assert: Button is visible
  });

  test(`${ma.action} NOT visible when conditions NOT met`, async ({ page }) => {
    // Setup: Create entity with WRONG status
    // Navigate to context
    // Assert: Button is NOT visible
  });
}
```

### 7B: Handler Correctness Verification

Compare TypeScript handlers against Python specs:

```typescript
// tests/contracts/handler_spec_match.test.ts

import { COMPLETE_ACTION_CATALOG } from '@docs/COMPLETE_ACTION_EXECUTION_CATALOG.md';
import { handlers } from '@/lib/microactions/handlers';

for (const [actionName, spec] of Object.entries(COMPLETE_ACTION_CATALOG)) {
  test(`${actionName} handler matches Python spec`, () => {
    const handler = handlers[actionName];

    // Verify required fields match
    expect(handler.requiredFields).toEqual(spec.required_fields);

    // Verify API endpoint matches
    expect(handler.endpoint).toBe(spec.endpoint);

    // Verify payload structure matches
    expect(handler.payloadSchema).toMatchSchema(spec.payload_schema);
  });
}
```

### 7C: End-to-End Execution Tests

For each microaction, test the full flow:

```typescript
// tests/e2e/microactions/execution_flow.spec.ts

for (const action of ALL_57_MICROACTIONS) {
  test(`${action}: button → backend → database → UI`, async ({ page }) => {
    // 1. Setup test data
    const testEntity = await createTestEntity(action.context);

    // 2. Navigate to context
    await page.goto(`/${action.context}/${testEntity.id}`);

    // 3. Click the button
    await page.click(`[data-action="${action.name}"]`);

    // 4. Verify backend received request (intercept network)
    const request = await page.waitForRequest(r => r.url().includes('/v1/actions/execute'));
    expect(request.postDataJSON().action).toBe(action.name);

    // 5. Verify database changed
    const dbState = await verifyDatabaseState(action.expectedChanges);
    expect(dbState).toMatchExpected();

    // 6. Verify UI updated
    await expect(page.locator('[data-status]')).toHaveText(action.expectedUIState);

    // 7. Cleanup
    await cleanupTestEntity(testEntity.id);
  });
}
```

### 7D: RLS Permission Tests

Test with real user tokens, not service key:

```typescript
// tests/e2e/microactions/rls_permissions.spec.ts

const ROLES = ['member', 'chief_engineer', 'eto', 'captain', 'manager'];

for (const role of ROLES) {
  for (const action of ALL_57_MICROACTIONS) {
    test(`${action.name} respects ${role} permissions`, async ({ page }) => {
      // Login as user with specific role
      await loginAs(role);

      // Try to execute action
      const response = await executeAction(action.name, testPayload);

      // Verify permission check
      if (action.allowedRoles.includes(role)) {
        expect(response.status).not.toBe(403);
      } else {
        expect(response.status).toBe(403);
      }
    });
  }
}
```

### 7E: Edge Case & Validation Tests

```typescript
// tests/e2e/microactions/edge_cases.spec.ts

const EDGE_CASES = [
  { action: 'add_wo_part', test: 'quantity_zero', payload: { quantity: 0 }, expected: 400 },
  { action: 'add_wo_part', test: 'quantity_negative', payload: { quantity: -1 }, expected: 400 },
  { action: 'add_wo_part', test: 'quantity_max', payload: { quantity: 1000001 }, expected: 400 },
  { action: 'delete_document', test: 'already_deleted', payload: { id: 'deleted-id' }, expected: 404 },
  { action: 'delete_shopping_item', test: 'linked_to_order', payload: { id: 'linked-id' }, expected: 409 },
  // ... all edge cases from ACTION_EXECUTION_CATALOG
];

for (const edge of EDGE_CASES) {
  test(`${edge.action}: ${edge.test}`, async () => {
    const response = await executeAction(edge.action, edge.payload);
    expect(response.status).toBe(edge.expected);
  });
}
```

---

## GitHub Workflow

```yaml
# .github/workflows/verification.yml
name: Full Verification Suite

on:
  workflow_dispatch:  # Manual trigger
  schedule:
    - cron: '0 0 * * *'  # Daily at midnight

jobs:
  visibility-matrix:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: npm ci
      - run: npx playwright test tests/e2e/microactions/visibility_matrix.spec.ts

  handler-correctness:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: npm ci
      - run: npm run test:handlers

  execution-flow:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: npm ci
      - run: npx playwright test tests/e2e/microactions/execution_flow.spec.ts

  rls-permissions:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: npm ci
      - run: npx playwright test tests/e2e/microactions/rls_permissions.spec.ts

  edge-cases:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: npm ci
      - run: npx playwright test tests/e2e/microactions/edge_cases.spec.ts

  summary:
    needs: [visibility-matrix, handler-correctness, execution-flow, rls-permissions, edge-cases]
    runs-on: ubuntu-latest
    steps:
      - run: echo "All verification tests passed"
```

---

## Data Files Needed

### 1. Microaction Registry (machine-readable)

```typescript
// tests/fixtures/microaction_registry.ts
export const MICROACTION_REGISTRY = [
  {
    id: 'diagnose_fault',
    cluster: '01_fix_something',
    context: 'fault_card',
    triggers: {
      status: ['open'],
      roles: ['any'],
      conditions: []
    },
    endpoint: '/v1/actions/execute',
    requiredFields: ['fault_id', 'diagnosis_text'],
    expectedChanges: {
      table: 'pms_faults',
      field: 'status',
      value: 'diagnosed'
    }
  },
  // ... all 57
];
```

### 2. Test User Accounts (per role)

```
TEST_USER_MEMBER=member@test.celeste7.ai
TEST_USER_CHIEF_ENGINEER=chief@test.celeste7.ai
TEST_USER_ETO=eto@test.celeste7.ai
TEST_USER_CAPTAIN=captain@test.celeste7.ai
TEST_USER_MANAGER=manager@test.celeste7.ai
```

---

## Execution Order

1. **Phase 7A:** Create `microaction_registry.ts` with all 57 actions
2. **Phase 7B:** Create visibility matrix tests
3. **Phase 7C:** Create handler correctness tests
4. **Phase 7D:** Create execution flow tests
5. **Phase 7E:** Create RLS permission tests
6. **Phase 7F:** Create edge case tests
7. **Phase 7G:** Create GitHub workflow
8. **Phase 7H:** Run full suite, fix failures

---

## Prompt for Claude

```
Read VERIFICATION_STRATEGY.md

Execute Phase 7A: Create tests/fixtures/microaction_registry.ts

Sources:
- /Users/celeste7/Desktop/Cloud_PMS_docs_v2/03_MICROACTIONS/MICRO_ACTION_REGISTRY.md
- /Users/celeste7/Desktop/Cloud_PMS_docs_v2/03_MICROACTIONS/ACTION_OFFERING_RULES.md
- /Users/celeste7/Desktop/Cloud_PMS_docs_v2/COMPLETE_ACTION_EXECUTION_CATALOG.md

Output: Machine-readable TypeScript file with all 57 microactions, their triggers, required fields, and expected behaviors.

Stop when done and wait for approval.
```
