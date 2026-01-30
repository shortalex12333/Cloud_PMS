# Part Lens v2 - E2E Test Plan (Playwright)

**Version**: 1.0
**Date**: 2026-01-29
**Status**: DRAFT → READY FOR IMPLEMENTATION
**Parent Document**: `part_lens_v2_FINAL.md`
**Reference**: Certificate Lens v2 E2E pattern

---

## PURPOSE

This document defines the complete Playwright E2E test suite for Part Lens v2, following the **intent-first, search-driven** architecture documented in `docs/architecture/17_ux_operating_system/02-search-as-interface.md`.

**Key Principles**:
1. ❌ **NO /parts route** - search is the only entry point
2. ✅ **Backend authority** - UI renders ONLY what backend returns
3. ✅ **Entity extraction** - queries trigger part entity resolution
4. ✅ **Action surfacing** - actions appear based on focus + role
5. ✅ **Deterministic validation** - status codes, payloads, ledger entries

---

# TEST ARCHITECTURE

## Test Categories

Per `part_lens_v2_ACCEPTANCE_TESTS.md`, all lenses must pass:

1. **Role & CRUD** - Permission matrix (crew/deckhand/eto/chief_engineer/captain)
2. **Isolation & Storage** - Yacht isolation (RLS enforcement)
3. **Edge Cases** - 4xx error mapping (never 5xx)
4. **Audit Invariant** - Signature semantics, ledger correctness

---

# TEST FLOW PATTERN

## Standard E2E Flow (Search-First)

```typescript
// ❌ OLD (navigation-based)
await page.goto('/parts');
await page.click('[data-part-id="uuid"]');

// ✅ NEW (search-first)
await page.goto('/');  // Base URL only
await searchInput.fill('Engine Oil Filter');
await searchInput.press('Enter');
// Entity extraction → Part card appears
// Actions surface based on role
await page.click('[data-action-id="receive_part"]');
```

## Authentication Pattern

```typescript
// Use stored JWT from roles-auth, NOT localStorage extraction
const tokens = await loginAsRole('chief_engineer');

// For backend parity checks
const apiClient = new ApiClient();
apiClient.setAccessToken(tokens.accessToken);

// For action execution
const response = await executeActionViaAPI(
  tokens.accessToken,
  'receive_part',
  { part_id: PART_ID, quantity: 5 }
);
```

---

# PART 1: ROLE & CRUD TESTS

## Test Suite: `parts_role_permissions.spec.ts`

### 1.1 View Parts (All Roles)

| Test | Role | Method | Expected |
|------|------|--------|----------|
| `test_crew_can_search_parts` | crew | Search "oil filter" | 200 + results |
| `test_deckhand_can_search_parts` | deckhand | Search "fuel filter" | 200 + results |
| `test_chief_engineer_can_search_parts` | chief_engineer | Search "Engine Oil Filter" | 200 + results |

```typescript
test('CREW: Can search and view parts', async ({ page }) => {
  // Authenticate as crew (storage state already loaded)
  await page.goto('/');

  const searchInput = page.locator('[data-testid="search-input"]');
  await searchInput.fill('Engine Oil Filter');
  await searchInput.press('Enter');

  // Wait for entity extraction + part card
  await page.waitForSelector('[data-entity-type="part"]', { timeout: 5000 });

  // Verify part card appears
  const partCard = page.locator('[data-entity-type="part"]').first();
  await expect(partCard).toBeVisible();

  // Verify part name rendered
  await expect(partCard.locator('[data-testid="part-name"]')).toContainText('Engine Oil Filter');

  // Verify stock level visible
  await expect(partCard.locator('[data-testid="stock-quantity"]')).toBeVisible();
});
```

---

### 1.2 Record Part Consumption

**Permission Matrix**:
- ❌ crew, steward → 403
- ✅ deckhand, bosun, eto, chief_engineer, captain, manager → 200

```typescript
test('CREW: Cannot consume parts (403)', async ({ page }) => {
  const jwt = await getJWTFromPage(page);

  // Try to consume via API (simulating action execution)
  const response = await executeActionViaAPI(jwt, 'record_part_consumption', {
    part_id: TEST_PART_ID,
    work_order_id: TEST_WO_ID,
    quantity: 1,
    usage_reason: 'Test consumption'
  });

  expect(response.statusCode).toBe(403);
  expect(response.responseBody.error).toBe('forbidden');
});

test('DECKHAND: Can consume parts (200)', async ({ page }) => {
  await page.goto('/');
  const searchInput = page.locator('[data-testid="search-input"]');

  // Search for part
  await searchInput.fill('Engine Oil Filter');
  await searchInput.press('Enter');

  // Focus part card
  await page.click('[data-entity-type="part"]');

  // Verify "Use for Work Order" action appears
  const consumeAction = page.locator('[data-action-id="record_part_consumption"]');
  await expect(consumeAction).toBeVisible();

  // Execute action
  await consumeAction.click();

  // Modal opens with pre-filled part_id
  await page.fill('[data-testid="work-order-select"]', TEST_WO_ID);
  await page.fill('[data-testid="quantity-input"]', '2');
  await page.fill('[data-testid="usage-reason"]', 'Scheduled maintenance');

  // Submit
  await page.click('[data-testid="submit-action"]');

  // Assert success notification
  await expect(page.locator('[data-testid="success-toast"]')).toContainText('Part consumed successfully');
});
```

---

### 1.3 Adjust Stock Quantity

**Permission Matrix**:
- ❌ crew, deckhand, bosun, steward → 403
- ✅ eto, chief_engineer → 200 (small adjustments)
- ✅ chief_engineer, captain, manager → 200 (large adjustments with signature)

```typescript
test('DECKHAND: Cannot adjust stock (403)', async ({ page }) => {
  const jwt = await getJWTFromPage(page);

  const response = await executeActionViaAPI(jwt, 'adjust_stock_quantity', {
    part_id: TEST_PART_ID,
    new_quantity: 10,
    reason: 'Physical count correction'
  });

  expect(response.statusCode).toBe(403);
});

test('ETO: Can adjust stock (small change, 200)', async ({ page }) => {
  // Part has qty=10, adjusting to 11 (10% change - no signature)
  const jwt = await getJWTFromPage(page);

  const response = await executeActionViaAPI(jwt, 'adjust_stock_quantity', {
    part_id: TEST_PART_ID,
    new_quantity: 11,
    reason: 'Found extra in store'
  });

  expect(response.statusCode).toBe(200);
  expect(response.responseBody.signature_required).toBe(false);
});

test('ETO: Cannot adjust stock (large change without signature, 403)', async ({ page }) => {
  // Part has qty=10, adjusting to 2 (80% change - requires signature)
  const jwt = await getJWTFromPage(page);

  const response = await executeActionViaAPI(jwt, 'adjust_stock_quantity', {
    part_id: TEST_PART_ID,
    new_quantity: 2,
    reason: 'Damaged units found'
  });

  expect(response.statusCode).toBe(403);
  expect(response.responseBody.error).toContain('signature_required');
});

test('CHIEF_ENGINEER: Can adjust stock (large change with signature, 200)', async ({ page }) => {
  const jwt = await getJWTFromPage(page);

  const response = await executeActionViaAPI(jwt, 'adjust_stock_quantity', {
    part_id: TEST_PART_ID,
    new_quantity: 2,
    reason: 'Damaged units found during inspection',
    signature: {
      signed_by: 'uuid-chief-engineer',
      signed_at: new Date().toISOString(),
      signature_type: 'typed_name',
      signature_value: 'Chief Engineer Name',
      acknowledgment: 'I confirm this large stock adjustment is authorized'
    }
  });

  expect(response.statusCode).toBe(200);
  expect(response.responseBody.signature_captured).toBe(true);
});
```

---

### 1.4 Add to Shopping List

**Permission Matrix**:
- ❌ crew (basic crew without department) → 403
- ✅ deckhand, steward, bosun, eto, chief_engineer, purser → 200

```typescript
test('STEWARD: Can add to shopping list (200)', async ({ page }) => {
  await page.goto('/');
  const searchInput = page.locator('[data-testid="search-input"]');

  await searchInput.fill('Dish Soap');
  await searchInput.press('Enter');

  await page.click('[data-entity-type="part"]');

  // Verify "Add to Shopping List" action visible
  const addToListAction = page.locator('[data-action-id="add_to_shopping_list"]');
  await expect(addToListAction).toBeVisible();

  await addToListAction.click();

  // Fill form
  await page.fill('[data-testid="quantity-requested"]', '10');
  await page.selectOption('[data-testid="urgency"]', 'normal');

  // Submit
  await page.click('[data-testid="submit-action"]');

  // Verify success
  await expect(page.locator('[data-testid="success-toast"]')).toContainText('Added to shopping list');
});
```

---

# PART 2: BACKEND-FRONTEND PARITY

## Test Suite: `parts_action_suggestions.spec.ts`

This validates that **UI shows ONLY actions backend returns** (no UI-invented actions).

### 2.1 Parity Check Pattern

```typescript
test('CHIEF_ENGINEER: UI actions match backend suggestions (parity)', async ({ page }) => {
  await page.goto('/');

  // Get JWT for backend calls
  const jwt = await getJWTFromPage(page);

  // Search for part
  await page.locator('[data-testid="search-input"]').fill('Engine Oil Filter');
  await page.locator('[data-testid="search-input"]').press('Enter');

  // Wait for part card
  const partCard = page.locator('[data-entity-type="part"]').first();
  await partCard.waitFor({ state: 'visible' });

  // Extract part_id from card
  const partId = await partCard.getAttribute('data-entity-id');

  // Call backend suggestions API
  const backendSuggestions = await getBackendSuggestions(jwt, partId);
  const backendActionIds = backendSuggestions.actions.map(a => a.action_id);

  console.log('[BACKEND] Chief Engineer sees actions:', backendActionIds);

  // Extract UI-rendered actions
  const uiActions = await partCard.locator('[data-action-id]').allTextContents();
  const uiActionIds = [];
  for (const button of await partCard.locator('[data-action-id]').all()) {
    const actionId = await button.getAttribute('data-action-id');
    if (actionId) uiActionIds.push(actionId);
  }

  console.log('[UI] Chief Engineer sees actions:', uiActionIds);

  // Assert exact match (no extras, no missing)
  expect(new Set(uiActionIds)).toEqual(new Set(backendActionIds));
});
```

### 2.2 Role-Specific Parity

```typescript
test('CREW: UI shows only READ actions (parity)', async ({ page }) => {
  // Backend should return: ['view_part_history', 'view_compatible_equipment']
  // UI should render: ONLY those two actions

  const jwt = await getJWTFromPage(page);
  await page.goto('/');

  await page.locator('[data-testid="search-input"]').fill('Oil Filter');
  await page.locator('[data-testid="search-input"]').press('Enter');

  const partCard = page.locator('[data-entity-type="part"]').first();
  const partId = await partCard.getAttribute('data-entity-id');

  const backendSuggestions = await getBackendSuggestions(jwt, partId);
  const backendActionIds = backendSuggestions.actions.map(a => a.action_id);

  // Crew should NEVER see MUTATE actions
  expect(backendActionIds).not.toContain('record_part_consumption');
  expect(backendActionIds).not.toContain('adjust_stock_quantity');
  expect(backendActionIds).not.toContain('receive_parts');

  // Verify UI matches backend
  const uiActionIds = [];
  for (const button of await partCard.locator('[data-action-id]').all()) {
    uiActionIds.push(await button.getAttribute('data-action-id'));
  }

  expect(new Set(uiActionIds)).toEqual(new Set(backendActionIds));
});
```

---

# PART 3: ENTITY EXTRACTION & ACTION SURFACING

## Test Suite: `parts_search_extraction.spec.ts`

### 3.1 Part Name Extraction

```typescript
test('Search "Engine Oil Filter" extracts part entity', async ({ page }) => {
  await page.goto('/');

  // Intercept search API call
  let searchResponse;
  await page.route('**/v1/search', async (route) => {
    const response = await route.fetch();
    searchResponse = await response.json();
    await route.fulfill({ response });
  });

  await page.locator('[data-testid="search-input"]').fill('Engine Oil Filter');
  await page.locator('[data-testid="search-input"]').press('Enter');

  await page.waitForTimeout(1000);

  // Verify entity extraction
  expect(searchResponse.entities).toContainEqual(
    expect.objectContaining({
      type: 'part',
      text: expect.stringContaining('Oil Filter'),
      canonical_id: expect.any(String)
    })
  );

  // Verify part card in results
  expect(searchResponse.cards).toContainEqual(
    expect.objectContaining({
      type: 'part',
      actions: expect.any(Array)
    })
  );
});
```

### 3.2 Action Intent Extraction

```typescript
test('Search "receive oil filter" surfaces receive_parts action', async ({ page }) => {
  await page.goto('/');

  let searchResponse;
  await page.route('**/v1/search', async (route) => {
    const response = await route.fetch();
    searchResponse = await response.json();
    await route.fulfill({ response });
  });

  // Query contains action intent keyword
  await page.locator('[data-testid="search-input"]').fill('receive oil filter');
  await page.locator('[data-testid="search-input"]').press('Enter');

  await page.waitForTimeout(1000);

  // Verify intent detected
  expect(searchResponse.intent).toContain('receive');

  // Verify receive_parts action surfaced
  const receiveAction = searchResponse.cards
    .flatMap(card => card.actions)
    .find(action => action.action_id === 'receive_parts');

  expect(receiveAction).toBeDefined();
  expect(receiveAction.label).toContain('Receive');
});
```

---

# PART 4: ACTION EXECUTION TESTS

## Test Suite: `parts_action_execution.spec.ts`

### 4.1 Receive Part (Success 201)

```typescript
test('DECKHAND: Receive part (201 Created)', async ({ page }) => {
  const jwt = await getJWTFromPage(page);

  // Generate unique idempotency key
  const idempotencyKey = `e2e-receive-${Date.now()}-${Math.random().toString(36).substr(7)}`;

  const response = await executeActionViaAPI(jwt, 'receive_parts', {
    items: [
      {
        part_id: TEST_PART_ID,
        quantity_received: 10,
        storage_location: 'Engine Room Store'
      }
    ],
    supplier: 'West Marine',
    idempotency_key: idempotencyKey
  });

  expect(response.statusCode).toBe(201);
  expect(response.responseBody).toHaveProperty('receiving_event_id');

  // Save evidence
  fs.writeFileSync(
    path.join(ARTIFACTS_DIR, 'receive_part_success_201.json'),
    JSON.stringify({ statusCode: 201, response: response.responseBody, idempotencyKey }, null, 2)
  );
});
```

### 4.2 Receive Part (Duplicate Idempotency 409)

```typescript
test('DECKHAND: Duplicate idempotency key (409 Conflict)', async ({ page }) => {
  const jwt = await getJWTFromPage(page);

  const idempotencyKey = `e2e-duplicate-${Date.now()}`;

  // First call - should succeed
  const firstResponse = await executeActionViaAPI(jwt, 'receive_parts', {
    items: [{ part_id: TEST_PART_ID, quantity_received: 5 }],
    idempotency_key: idempotencyKey
  });

  expect(firstResponse.statusCode).toBe(201);

  // Second call with SAME key - should return 409
  const duplicateResponse = await executeActionViaAPI(jwt, 'receive_parts', {
    items: [{ part_id: TEST_PART_ID, quantity_received: 10 }],  // Different payload
    idempotency_key: idempotencyKey
  });

  expect(duplicateResponse.statusCode).toBe(409);
  expect(duplicateResponse.responseBody.error).toContain('duplicate');
});
```

### 4.3 Consume Part (Sufficient Stock 200)

```typescript
test('DECKHAND: Consume part with sufficient stock (200 OK)', async ({ page }) => {
  const jwt = await getJWTFromPage(page);

  // Setup: Ensure part has stock
  await executeActionViaAPI(jwt, 'receive_parts', {
    items: [{ part_id: TEST_PART_ID, quantity_received: 10 }],
    idempotency_key: `setup-${Date.now()}`
  });

  // Consume
  const response = await executeActionViaAPI(jwt, 'record_part_consumption', {
    part_id: TEST_PART_ID,
    work_order_id: TEST_WO_ID,
    quantity: 2,
    usage_reason: 'Scheduled maintenance'
  });

  expect(response.statusCode).toBe(200);
  expect(response.responseBody).toHaveProperty('usage_id');
});
```

### 4.4 Consume Part (Insufficient Stock 400)

```typescript
test('DECKHAND: Consume more than available (400 Bad Request)', async ({ page }) => {
  const jwt = await getJWTFromPage(page);

  // Part has qty=3, try to consume 10
  const response = await executeActionViaAPI(jwt, 'record_part_consumption', {
    part_id: TEST_PART_ID,
    work_order_id: TEST_WO_ID,
    quantity: 10
  });

  expect(response.statusCode).toBe(400);
  expect(response.responseBody.error).toBe('insufficient_stock');
  expect(response.responseBody.available).toBeLessThan(10);
  expect(response.responseBody.requested).toBe(10);
});
```

---

# PART 5: EDGE CASES (4xx NEVER 5xx)

## Test Suite: `parts_edge_cases.spec.ts`

### 5.1 Invalid Work Order

```typescript
test('Consume for non-existent work order (404)', async ({ page }) => {
  const jwt = await getJWTFromPage(page);

  const response = await executeActionViaAPI(jwt, 'record_part_consumption', {
    part_id: TEST_PART_ID,
    work_order_id: 'fake-uuid-12345',
    quantity: 1
  });

  expect(response.statusCode).toBe(404);
  expect(response.responseBody.error).toBe('work_order_not_found');
});
```

### 5.2 Closed Work Order

```typescript
test('Consume for completed work order (400)', async ({ page }) => {
  const jwt = await getJWTFromPage(page);

  // TEST_WO_COMPLETED_ID is a work order with status='completed'
  const response = await executeActionViaAPI(jwt, 'record_part_consumption', {
    part_id: TEST_PART_ID,
    work_order_id: TEST_WO_COMPLETED_ID,
    quantity: 1
  });

  expect(response.statusCode).toBe(400);
  expect(response.responseBody.error).toBe('work_order_invalid_status');
});
```

### 5.3 Yacht Isolation

```typescript
test('Cannot consume other yacht\'s part (404 or 403)', async ({ page }) => {
  const jwt = await getJWTFromPage(page);  // Yacht A JWT

  const response = await executeActionViaAPI(jwt, 'record_part_consumption', {
    part_id: YACHT_B_PART_ID,  // Different yacht's part
    work_order_id: TEST_WO_ID,
    quantity: 1
  });

  // RLS should prevent access
  expect(response.statusCode).toBeOneOf([403, 404]);
});
```

---

# PART 6: USER JOURNEY SCENARIOS

## Test Suite: `parts_user_journeys.spec.ts`

### 6.1 Journey: Emergency Breakdown

**From**: `part_lens_v2_USER_JOURNEYS_UPDATED.md` - Journey 1

```typescript
test('CHIEF_ENGINEER: Emergency part lookup (breakdown response)', async ({ page }) => {
  await page.goto('/');

  // Scenario: Generator failure, need fuel filter ASAP
  const startTime = Date.now();

  const searchInput = page.locator('[data-testid="search-input"]');
  await searchInput.fill('cat fuel filter');
  await searchInput.press('Enter');

  // Wait for part card
  const partCard = page.locator('[data-entity-type="part"]').first();
  await partCard.waitFor({ state: 'visible' });

  const endTime = Date.now();
  const timeToFind = endTime - startTime;

  // Assert: Found in <3 seconds (stress condition)
  expect(timeToFind).toBeLessThan(3000);

  // Verify critical info visible
  await expect(partCard.locator('[data-testid="stock-quantity"]')).toContainText('3');
  await expect(partCard.locator('[data-testid="location"]')).toContainText('Engine Room Store');

  // Verify "Use for Work Order" action available
  await expect(partCard.locator('[data-action-id="record_part_consumption"]')).toBeVisible();

  // Screenshot for evidence
  await page.screenshot({
    path: path.join(ARTIFACTS_DIR, 'journey_emergency_breakdown.png'),
    fullPage: true
  });
});
```

### 6.2 Journey: Scheduled Maintenance Prep

```typescript
test('ETO: Pre-service parts check (500-hour service)', async ({ page }) => {
  await page.goto('/');

  // Scenario: Planning tomorrow's service, check parts availability
  await page.locator('[data-testid="search-input"]').fill('ME1 500 hour parts');
  await page.locator('[data-testid="search-input"]').press('Enter');

  // Wait for BOM results
  await page.waitForSelector('[data-testid="bom-list"]', { timeout: 5000 });

  // Verify multi-part availability shown
  const bomItems = page.locator('[data-testid="bom-item"]');
  const count = await bomItems.count();

  expect(count).toBeGreaterThan(3);  // ME1 service requires multiple parts

  // Check for low stock warnings
  const lowStockWarnings = page.locator('[data-testid="low-stock-warning"]');
  if (await lowStockWarnings.count() > 0) {
    // Verify "Order Missing Parts" action visible
    await expect(page.locator('[data-action-id="add_to_shopping_list"]')).toBeVisible();
  }
});
```

### 6.3 Journey: Receiving Delivery

```typescript
test('BOSUN: Receive parts delivery (camera/OCR flow)', async ({ page }) => {
  await page.goto('/');

  // Scenario: DHL delivery arrived, 3 boxes on deck
  await page.locator('[data-testid="search-input"]').fill('receive delivery');
  await page.locator('[data-testid="search-input"]').press('Enter');

  // Verify receive_parts action surfaced
  await page.waitForSelector('[data-action-id="receive_parts"]');

  await page.click('[data-action-id="receive_parts"]');

  // Modal opens with camera option
  await expect(page.locator('[data-testid="camera-scan-button"]')).toBeVisible();

  // Alternative: Manual entry
  await page.click('[data-testid="manual-entry-tab"]');

  // Add line items
  await page.fill('[data-testid="part-select-0"]', TEST_PART_ID);
  await page.fill('[data-testid="quantity-0"]', '10');
  await page.fill('[data-testid="location-0"]', 'Engine Room Store');

  // Submit
  await page.click('[data-testid="submit-receive"]');

  // Verify success
  await expect(page.locator('[data-testid="success-toast"]')).toContainText('10 units received');
});
```

---

# PART 7: ZERO 5XX MONITORING

## Test Suite: `parts_zero_5xx.spec.ts`

```typescript
test('CHIEF_ENGINEER: Zero 5xx errors across all flows', async ({ page }) => {
  const jwt = await getJWTFromPage(page);
  const results: Array<{ action: string; statusCode: number }> = [];

  // Test all Part Lens actions
  const scenarios = [
    { action: 'record_part_consumption', payload: { part_id: TEST_PART_ID, work_order_id: TEST_WO_ID, quantity: 1 } },
    { action: 'adjust_stock_quantity', payload: { part_id: TEST_PART_ID, new_quantity: 5, reason: 'Count correction' } },
    { action: 'add_to_shopping_list', payload: { part_id: TEST_PART_ID, quantity_requested: 10 } },
    { action: 'receive_parts', payload: { items: [{ part_id: TEST_PART_ID, quantity_received: 5 }] } },
    { action: 'view_part_history', payload: { part_id: TEST_PART_ID } }
  ];

  for (const scenario of scenarios) {
    const response = await executeActionViaAPI(jwt, scenario.action, scenario.payload);

    results.push({
      action: scenario.action,
      statusCode: response.statusCode
    });

    // Assert NO 5xx error
    expect(response.statusCode).toBeLessThan(500);
  }

  // Save evidence
  fs.writeFileSync(
    path.join(ARTIFACTS_DIR, 'parts_zero_5xx_evidence.json'),
    JSON.stringify({ results, allPassed: results.every(r => r.statusCode < 500) }, null, 2)
  );

  // Assert summary
  const has5xxError = results.some(r => r.statusCode >= 500);
  expect(has5xxError).toBe(false);
});
```

---

# TEST HELPERS

## Helper: `getBackendSuggestions(jwt, partId)`

```typescript
async function getBackendSuggestions(jwt: string, partId: string): Promise<any> {
  const apiClient = new ApiClient();
  apiClient.setAccessToken(jwt);

  const response = await apiClient.get(`/v1/parts/suggestions?part_id=${partId}`);

  if (response.status !== 200) {
    throw new Error(`Backend suggestions failed: ${response.status}`);
  }

  return response.data.data || response.data;
}
```

## Helper: `executeActionViaAPI(jwt, action, payload)`

```typescript
async function executeActionViaAPI(
  jwt: string,
  action: string,
  payload: Record<string, any>
): Promise<{ statusCode: number; responseBody: any }> {
  const response = await fetch(`${API_BASE}/v1/actions/execute`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${jwt}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ action, payload })
  });

  const body = await response.json().catch(() => ({}));

  return {
    statusCode: response.status,
    responseBody: body
  };
}
```

---

# TEST DATA REQUIREMENTS

## Required Test Fixtures

| Entity | ID Variable | Purpose |
|--------|-------------|---------|
| Part (Oil Filter) | `TEST_PART_ID` | Standard test part with stock |
| Part (Low Stock) | `TEST_PART_LOW_STOCK_ID` | Part below minimum quantity |
| Work Order (Active) | `TEST_WO_ID` | WO with status='in_progress' |
| Work Order (Completed) | `TEST_WO_COMPLETED_ID` | WO with status='completed' |
| Yacht A | `TEST_YACHT_ID` | Primary test yacht |
| Yacht B | `YACHT_B_ID` | For isolation tests |
| Yacht B Part | `YACHT_B_PART_ID` | Part owned by Yacht B |

---

# SUCCESS CRITERIA

## Test Execution Metrics

| Metric | Target | Status |
|--------|--------|--------|
| Backend parity | 100% match | ⏸️ Pending UI deployment |
| Role permissions | All roles tested | ⏸️ Pending role fix |
| Zero 5xx errors | 0 across all actions | ⏸️ Pending deployment |
| Edge case coverage | All 4xx paths validated | ⏸️ Pending |
| User journey scenarios | 3/3 passing | ⏸️ Pending UI |

---

# DEPLOYMENT BLOCKERS

| ID | Blocker | Impact | Status |
|----|---------|--------|--------|
| **UI-1** | Frontend /parts route returns 404 | Cannot navigate to test flows | ❌ BLOCKING ALL TESTS |
| **DB-1** | MASTER roles fixed (crew/chief_engineer/captain) | Permission tests can run | ✅ FIXED TODAY |
| **DB-2** | RLS on pms_inventory_transactions disabled | Mutations unsafe without RLS | ⚠️ Known risk |

---

# NEXT STEPS

1. **Deploy Frontend** with Part Lens v2 UI to app.celeste7.ai
2. **Refactor Existing Tests** using this plan as blueprint
3. **Run Test Suite** and validate zero 5xx
4. **Generate Evidence** (screenshots, HAR files, ledger entries)
5. **Sign Off** on Part Lens E2E validation

---

**Prepared By**: Claude Sonnet 4.5
**Date**: 2026-01-29
**Branch**: e2e/parts-lens-playwright
**Status**: READY FOR IMPLEMENTATION (pending UI deployment)
