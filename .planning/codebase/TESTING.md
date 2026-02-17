# CelesteOS PMS - Testing Conventions & Patterns

This document describes the testing infrastructure, patterns, and current coverage across the CelesteOS codebase.

---

## Table of Contents

1. [Test Framework Stack](#test-framework-stack)
2. [Test Organization](#test-organization)
3. [Playwright E2E Tests](#playwright-e2e-tests)
4. [Test Naming Conventions](#test-naming-conventions)
5. [Role-Based Testing](#role-based-testing)
6. [API Testing Patterns](#api-testing-patterns)
7. [Current Coverage Status](#current-coverage-status)
8. [Writing New Tests](#writing-new-tests)

---

## Test Framework Stack

### Playwright
- **Purpose**: End-to-end UI testing and browser automation
- **Config**: `playwright.config.ts`
- **Version**: Latest (as of Feb 2026)
- **Browsers**: Chromium, Firefox, WebKit (for cross-browser compatibility)
- **Parallelization**: Built-in test sharding and parallel execution

### Vitest
- **Purpose**: Unit and integration testing for TypeScript
- **Package**: `vitest`
- **Usage**: Component logic, registry, handler functions
- **Pattern**: `describe()` + `it()` blocks with `expect()` assertions

### Python pytest
- **Purpose**: Backend API testing and action router validation
- **Location**: `tests/action_router/`, `tests/api/`
- **Usage**: JWT validation, schema validation, action execution

---

## Test Organization

### Directory Structure

```
/Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS/

├── tests/
│   ├── e2e/                          # Main Playwright tests
│   │   ├── actions/                  # Action-specific tests
│   │   │   ├── api-health.spec.ts
│   │   │   ├── documents.spec.ts
│   │   │   ├── list.spec.ts
│   │   │   └── role-filtering.spec.ts
│   │   ├── documents/                # Document lens tests
│   │   │   ├── action_render_diagnostic.spec.ts
│   │   │   ├── document_lens_e2e.spec.ts
│   │   │   ├── hod_upload_execute.spec.ts
│   │   │   └── live_diagnostic.spec.ts
│   │   ├── microactions/             # Microaction matrix tests
│   │   │   ├── cluster_01_fix_something.spec.ts
│   │   │   ├── cluster_02_do_maintenance.spec.ts
│   │   │   ├── ... (clusters 3-13)
│   │   │   ├── edge_cases.spec.ts
│   │   │   ├── rls_permissions.spec.ts
│   │   │   └── visibility_matrix_complete.spec.ts
│   │   ├── parts/                    # Parts lens tests
│   │   │   ├── parts_actions_execution.spec.ts
│   │   │   ├── parts_search_entity_extraction.spec.ts
│   │   │   ├── parts_signed_actions.spec.ts
│   │   │   ├── parts_storage_access.spec.ts
│   │   │   └── parts_suggestions.spec.ts
│   │   ├── receiving/                # Receiving lens tests
│   │   │   ├── global-setup.ts
│   │   │   └── receiving_search_entity_extraction.spec.ts
│   │   ├── shopping_list/            # Shopping list lens tests
│   │   │   ├── auth.setup.ts
│   │   │   ├── crew_create_item.e2e.spec.ts
│   │   │   ├── engineer_promote_item.e2e.spec.ts
│   │   │   ├── hod_approve_reject_item.e2e.spec.ts
│   │   │   ├── role_based_actions.e2e.spec.ts
│   │   │   └── shopping_list_network_diagnostic.spec.ts
│   │   ├── situations/               # Situation UX tests
│   │   │   ├── situation_types.ts
│   │   │   └── situation_ux_tests.spec.ts
│   │   ├── security/                 # Contract tests
│   │   │   ├── action_router_contract.spec.ts
│   │   │   └── auth_context_contract.spec.ts
│   │   ├── user-flows/               # End-to-end user journeys
│   │   │   ├── error-handling.spec.ts
│   │   │   ├── fault-lifecycle.spec.ts
│   │   │   ├── handover-flow.spec.ts
│   │   │   ├── inventory-flow.spec.ts
│   │   │   ├── mobile-responsive.spec.ts
│   │   │   └── work-order-lifecycle.spec.ts
│   │   ├── auth.spec.ts
│   │   ├── chat_to_action.spec.ts
│   │   ├── journey_truth.spec.ts
│   │   ├── phase13_mutation_proof.spec.ts
│   │   └── ... (100+ more test files)
│   │
│   ├── acceptance/                   # Acceptance tests
│   │   ├── test_part_lens_v2_core.py
│   │   └── test_storage_rls_delete.py
│   │
│   └── action_router/                # Backend action router tests
│       └── test_auth_middleware.py

├── apps/web/tests/
│   ├── playwright/                   # Comprehensive Playwright suite
│   │   ├── receiving-COMPREHENSIVE.spec.ts    # ⭐ Primary receiving tests
│   │   ├── document-lens-comprehensive.spec.ts
│   │   ├── parts-lens-comprehensive.spec.ts
│   │   ├── equipment-lens-comprehensive.spec.ts
│   │   ├── fault-lens-comprehensive.spec.ts
│   │   ├── work-order-lens-comprehensive.spec.ts
│   │   ├── all-lens-details-comprehensive.spec.ts
│   │   ├── fixtures/
│   │   │   └── auth.ts               # Playwright fixtures
│   │   ├── global-setup.ts           # Global setup
│   │   ├── auth.helper.ts            # Login & role helpers
│   │   └── utils/
│   │       └── jwt.ts
│   │
│   ├── unit/                         # Unit tests (vitest)
│   │   ├── action-router/
│   │   │   ├── action-registry.test.ts
│   │   │   ├── router.test.ts
│   │   │   └── validators.test.ts
│   │   └── microactions/
│   │       ├── executor.test.ts
│   │       ├── hooks.test.ts
│   │       ├── registry.test.ts
│   │       ├── triggers.test.ts
│   │       └── validator.test.ts
│   │
│   └── integration/                  # Integration tests
│       ├── handler-db.test.ts
│       ├── router-db.test.ts
│       ├── situation-db.test.ts
│       └── setup.ts
```

### Test File Count
- **Total test files**: ~372
- **E2E tests**: ~140+ files in `/tests/e2e/`
- **Playwright tests**: ~90+ files in `/apps/web/tests/playwright/`
- **Unit tests**: ~20+ files in `/apps/web/tests/unit/`
- **Integration tests**: ~5 files in `/apps/web/tests/integration/`

---

## Playwright E2E Tests

### Test Environment Setup

#### Global Setup (`global-setup.ts`)

```typescript
import { chromium, FullConfig } from '@playwright/test';

async function globalSetup(config: FullConfig) {
  const browser = await chromium.launch();
  const context = await browser.newContext();
  const page = await context.newPage();

  // Login and save auth state
  await page.goto('/login');
  // ... login logic ...

  // Save storage state for reuse in tests
  await context.storageState({
    path: 'auth/.authenticated.json'
  });

  await browser.close();
}

export default globalSetup;
```

#### Auth Helper (`auth.helper.ts`)

```typescript
export const TEST_USERS = {
  crew: {
    email: process.env.STAGING_CREW_EMAIL || 'crew.test@alex-short.com',
    password: process.env.STAGING_USER_PASSWORD || 'Password2!',
    role: 'crew',
  },
  hod: {
    email: process.env.STAGING_HOD_EMAIL || 'hod.test@alex-short.com',
    password: process.env.STAGING_USER_PASSWORD || 'Password2!',
    role: 'chief_engineer',
  },
  captain: {
    email: process.env.STAGING_CAPTAIN_EMAIL || 'x@alex-short.com',
    password: process.env.STAGING_USER_PASSWORD || 'Password2!',
    role: 'captain',
  },
};

export async function loginAs(page: Page, role: UserRole): Promise<void> {
  const user = TEST_USERS[role];
  await page.goto('/login');
  await page.waitForSelector('input[type="email"], input[name="email"]', { timeout: 10000 });
  await page.fill('input[type="email"], input[name="email"]', user.email);
  await page.fill('input[type="password"], input[name="password"]', user.password);
  await page.click('button[type="submit"]');
  await page.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 15000 });
}

export async function verifyUserRole(page: Page, expectedRole: string): Promise<void> {
  const roleIndicator = page.locator('[data-testid="user-role"], .user-role, [aria-label*="role"]');
  if (await roleIndicator.count() > 0) {
    const text = await roleIndicator.textContent();
    expect(text?.toLowerCase()).toContain(expectedRole.toLowerCase());
  }
}
```

### Test Structure Pattern

```typescript
import { test, expect, Page } from '@playwright/test';
import { loginAs } from './auth.helper';

test.describe('FEATURE - COMPREHENSIVE', () => {
  // ========================================================================
  // SECTION 1: SUCCESS PATH
  // ========================================================================

  test('SUCCESS: Complete workflow - Step A → Step B → Step C', async ({ page }) => {
    console.log('\n🎯 SECTION 1: Success Path\n');

    // Step 1: Setup
    await loginAs(page, 'captain');
    const jwt = await getJWT(page);
    console.log('✓ Setup complete');

    // Step 2: Execute action
    const result = await apiCall(jwt, 'action_name', { /* payload */ });
    expect(result.status).toBe(200);
    expect(result.data.status).toBe('success');
    console.log(`✓ Action executed: ${result.data.id}`);

    // Step 3: Verify results
    const details = await apiCall(jwt, 'get_details', { id: result.data.id });
    expect(details.data.field).toBe('expected_value');
    console.log('✓ Results verified\n');
  });

  // ========================================================================
  // SECTION 2: PERMISSION TESTS
  // ========================================================================

  test('PERMISSIONS: Role A can do X but role B cannot', async ({ page }) => {
    console.log('\n🎯 SECTION 2: Permissions\n');

    // Test with role A (should succeed)
    await loginAs(page, 'captain');
    const jwt1 = await getJWT(page);
    const result1 = await apiCall(jwt1, 'action_name', { /* payload */ });
    expect(result1.status).toBe(200);
    console.log('✓ Captain can perform action');

    // Test with role B (should fail)
    // Note: Would need to open new context/page for different user
    // Or check UI shows permission denied
  });

  // ========================================================================
  // SECTION 3: VALIDATION TESTS
  // ========================================================================

  test('VALIDATION: Rejects invalid inputs', async ({ page }) => {
    console.log('\n🎯 SECTION 3: Validation\n');

    await loginAs(page, 'captain');
    const jwt = await getJWT(page);

    const result = await apiCall(jwt, 'action_name', {
      required_field: '', // Invalid: empty
    });

    expect(result.status).not.toBe(200);
    expect(result.data.error).toBeDefined();
    expect(result.data.error.code).toContain('VALIDATION');
    console.log('✓ Validation correctly rejected input\n');
  });

  // ========================================================================
  // SECTION 4: STATE TESTS
  // ========================================================================

  test('STATE: Cannot perform action in invalid state', async ({ page }) => {
    console.log('\n🎯 SECTION 4: State\n');

    await loginAs(page, 'captain');
    const jwt = await getJWT(page);

    // First, put entity in state A
    const create = await apiCall(jwt, 'create_entity', { /* ... */ });
    const entityId = create.data.id;

    // Try to perform action only valid in state B (should fail)
    const result = await apiCall(jwt, 'action_for_state_b', {
      entity_id: entityId,
    });

    expect(result.status).not.toBe(200);
    console.log('✓ State transition correctly prevented\n');
  });

  test.afterAll(async () => {
    console.log('✅ ALL TESTS COMPLETE\n');
  });
});
```

### Helper Functions

```typescript
async function getJWT(page: Page): Promise<string> {
  const jwt = await page.evaluate(() => {
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i);
      if (key && key.includes('sb-')) {
        const value = localStorage.getItem(key);
        if (value) {
          try {
            const parsed = JSON.parse(value);
            return parsed.access_token || null;
          } catch {}
        }
      }
    }
    return null;
  });

  if (!jwt) throw new Error('JWT not found');
  return jwt;
}

async function apiCall(jwt: string, action: string, payload: any): Promise<any> {
  const response = await fetch('https://pipeline-core.int.celeste7.ai/v1/actions/execute', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${jwt}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      action,
      context: { yacht_id: 'your-yacht-id' },
      payload,
    }),
  });

  const data = await response.json();
  return { status: response.status, data };
}

async function openSpotlight(page: Page): Promise<void> {
  const searchInput = page.locator(
    '[data-testid="search-input"], ' +
    '[data-testid="spotlight-input"], ' +
    'input[placeholder*="Search"]'
  ).first();

  await searchInput.waitFor({ state: 'visible', timeout: 10000 });
  await searchInput.click();
}

async function searchInSpotlight(page: Page, query: string): Promise<void> {
  await openSpotlight(page);
  const searchInput = page.locator(
    '[data-testid="search-input"], ' +
    '[data-testid="spotlight-input"], ' +
    'input[placeholder*="Search"]'
  ).first();

  await searchInput.fill(query);
  await page.waitForTimeout(500); // Wait for debounce + API
}

async function getActionSuggestions(page: Page): Promise<string[]> {
  await page.waitForSelector(
    '[data-testid="action-button"], ' +
    '[data-testid="suggested-action"], ' +
    '.action-suggestion',
    { timeout: 5000 }
  ).catch(() => null);

  const buttons = page.locator(
    '[data-testid="action-button"], ' +
    '[data-testid="suggested-action"], ' +
    '.action-suggestion'
  );

  const count = await buttons.count();
  const actions: string[] = [];

  for (let i = 0; i < count; i++) {
    const text = await buttons.nth(i).textContent();
    if (text) actions.push(text.trim());
  }

  return actions;
}

async function clickAction(page: Page, actionLabel: string): Promise<void> {
  const button = page.locator(
    `[data-testid="action-button"]:has-text("${actionLabel}"), ` +
    `[data-testid="suggested-action"]:has-text("${actionLabel}"), ` +
    `button:has-text("${actionLabel}")`
  ).first();

  await button.click();
}

async function waitForActionModal(page: Page): Promise<void> {
  await page.waitForSelector(
    '[data-testid="action-modal"], ' +
    '[role="dialog"], ' +
    '.modal, ' +
    '.action-modal',
    { timeout: 10000 }
  );
}

async function hasSignatureBadge(page: Page): Promise<boolean> {
  const badge = page.locator(
    '[data-testid="signature-badge"], ' +
    ':text("Requires Signature"), ' +
    ':text("requires signature"), ' +
    '.signature-required'
  );

  return await badge.count() > 0;
}

async function waitForSuccessToast(page: Page): Promise<void> {
  await page.waitForSelector(
    '[data-testid="toast-success"], ' +
    '.toast-success, ' +
    '[role="alert"]:has-text("success"), ' +
    '.Toastify__toast--success',
    { timeout: 10000 }
  );
}

async function checkConsoleForErrors(page: Page): Promise<string[]> {
  const errors: string[] = [];

  page.on('console', (msg) => {
    if (msg.type() === 'error') {
      errors.push(msg.text());
    }
  });

  return errors;
}
```

---

## Test Naming Conventions

### Playwright Test File Names

| Pattern | Example | Purpose |
|---------|---------|---------|
| `*-COMPREHENSIVE.spec.ts` | `receiving-COMPREHENSIVE.spec.ts` | Full coverage of feature (all actions, roles, paths) |
| `*-lens-*.spec.ts` | `document-lens-comprehensive.spec.ts` | Domain-specific lens tests |
| `*.journey.spec.ts` | `receiving.journey.spec.ts` | End-to-end user journeys |
| `*-roles.spec.ts` | `parts-lens-roles.spec.ts` | Role-based permission tests |
| `*-failure*.spec.ts` | `document-lens-failure-modes.spec.ts` | Error cases and edge conditions |
| `cluster_*.spec.ts` | `cluster_01_fix_something.spec.ts` | Microaction cluster tests |
| `user-flows/*.spec.ts` | `user-flows/error-handling.spec.ts` | Generic user flow tests |

### Test Case Naming

```typescript
// Format: CONTEXT: BEHAVIOR (assertion)
test('SUCCESS: Complete workflow - Create → Items → Accept with signature', async () => {
  // Success path test
});

test('PERMISSIONS: HOD can create/edit AND accept (per registry)', async () => {
  // Permission/authorization test
});

test('STATE: Cannot edit accepted receiving', async () => {
  // State machine/transition test
});

test('VALIDATION: Rejects invalid inputs', async () => {
  // Input validation test
});

test('REJECTION: Can reject receiving with reason', async () => {
  // Negative path test
});

test('AUDIT: All actions recorded in audit trail', async () => {
  // Audit/logging test
});

test('DOCUMENTS: Can attach and link documents', async () => {
  // Feature-specific test
});

test('EXTRACTION: Advisory extraction does not auto-apply', async () => {
  // Specific behavior verification
});
```

### Test Sections

Within a test, use commented sections:

```typescript
// ========================================================================
// SECTION 1: SUCCESS PATH (Captain)
// ========================================================================

test('SUCCESS: Complete workflow', async ({ page }) => {
  console.log('\n🎯 SECTION 1: Success Path\n');

  // Step 1: Setup
  // Step 2: Action
  // Step 3: Verify

  console.log('✓ Step 1 complete');
  console.log('✓ Step 2 complete');
  console.log('✅ SECTION 1 COMPLETE\n');
});

// ========================================================================
// SECTION 2: PERMISSION TESTS
// ========================================================================

test('PERMISSIONS: Role X can do Y', async ({ page }) => {
  console.log('\n🎯 SECTION 2: Permissions\n');
  // ...
});
```

---

## Role-Based Testing

### Three Primary Roles

1. **Crew** (Base user)
   - Email: `crew.test@alex-short.com`
   - Role: `crew`
   - Permissions: Limited create/view operations
   - Signature capability: NO

2. **HOD** (Head of Department/Chief Engineer)
   - Email: `hod.test@alex-short.com`
   - Role: `chief_engineer`
   - Permissions: Create, review, approve operations
   - Signature capability: YES

3. **Captain** (Top authority)
   - Email: `x@alex-short.com`
   - Role: `captain`
   - Permissions: All operations, full authority
   - Signature capability: YES

### Role Testing Pattern

```typescript
test('PERMISSIONS: Each role has correct capabilities', async ({ page }) => {
  // Test Crew
  await loginAs(page, 'crew');
  let jwt = await getJWT(page);
  let result = await apiCall(jwt, 'create_receiving', { /* ... */ });
  expect(result.status).toBe(200);  // Crew CAN create
  console.log('✓ Crew can create');

  result = await apiCall(jwt, 'accept_receiving', { receiving_id: '...' });
  expect(result.status).not.toBe(200);  // Crew CANNOT accept
  console.log('✓ Crew cannot accept');

  // Test HOD (in new context to avoid auth conflict)
  const context2 = await browser.newContext();
  const page2 = await context2.newPage();
  await loginAs(page2, 'hod');
  jwt = await getJWT(page2);

  result = await apiCall(jwt, 'accept_receiving', { receiving_id: '...' });
  expect(result.status).toBe(200);  // HOD CAN accept
  console.log('✓ HOD can accept');

  // Test Captain (similar to HOD, highest privilege)
  const context3 = await browser.newContext();
  const page3 = await context3.newPage();
  await loginAs(page3, 'captain');
  jwt = await getJWT(page3);

  result = await apiCall(jwt, 'accept_receiving', { receiving_id: '...' });
  expect(result.status).toBe(200);  // Captain CAN accept
  console.log('✓ Captain can accept');
});
```

### RLS (Row-Level Security) Testing

Tests verify that users only see/modify their own yacht's data:

```typescript
// Location: tests/e2e/microactions/rls_permissions.spec.ts

test('RLS: User cannot access other yacht\'s data', async ({ page }) => {
  await loginAs(page, 'crew');
  const jwt = await getJWT(page);

  // Try to access different yacht
  const result = await apiCall(jwt, 'get_work_orders', {
    yacht_id: 'different-yacht-id' // Not the user's yacht
  });

  // Should fail with RLS error
  expect(result.status).not.toBe(200);
  expect(result.data.error?.code).toContain('RLS');
});
```

---

## API Testing Patterns

### Direct API Calls (In Playwright Tests)

Most tests use direct API calls to `/v1/actions/execute`:

```typescript
async function apiCall(jwt: string, action: string, payload: any): Promise<any> {
  const response = await fetch('https://pipeline-core.int.celeste7.ai/v1/actions/execute', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${jwt}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      action,
      context: { yacht_id: YACHT_ID },
      payload,
    }),
  });

  const data = await response.json();
  return { status: response.status, data };
}
```

### Expected Response Format

```typescript
// Success (2xx)
{
  status: 200,
  data: {
    status: 'success',
    action: 'create_receiving',
    execution_id: 'uuid',
    result: {
      receiving_id: 'uuid',
      status: 'draft',
      created_at: 'timestamp'
    }
  }
}

// Validation Error (4xx)
{
  status: 400,
  data: {
    status: 'error',
    error_code: 'VALIDATION_ERROR',
    message: 'Invalid input',
    action: 'create_receiving',
    details: {
      field: 'vendor_reference',
      reason: 'must be non-empty'
    }
  }
}

// Permission Error (4xx)
{
  status: 403,
  data: {
    status: 'error',
    error_code: 'PERMISSION_DENIED',
    message: 'This role cannot perform this action',
    action: 'accept_receiving'
  }
}

// Auth Error (401)
{
  status: 401,
  data: {
    status: 'error',
    error_code: 'INVALID_JWT',
    message: 'Invalid or expired JWT token'
  }
}
```

### Python API Tests

Backend tests in `tests/action_router/` and `tests/api/`:

```python
# tests/action_router/test_auth_middleware.py

import pytest
from apps.api.action_router.validators import validate_jwt

def test_valid_jwt():
    """Test JWT validation with valid token."""
    result = validate_jwt('valid.jwt.token')
    assert result.valid is True
    assert result.context['user_id'] is not None

def test_invalid_jwt():
    """Test JWT validation with invalid token."""
    result = validate_jwt('invalid.jwt')
    assert result.valid is False
    assert result.error.error_code == 'INVALID_JWT'

def test_expired_jwt():
    """Test JWT validation with expired token."""
    result = validate_jwt('expired.jwt.token')
    assert result.valid is False
    assert result.error.error_code == 'EXPIRED_JWT'
```

---

## Current Coverage Status

### Tests with Comprehensive Coverage

| Feature | Status | Test File |
|---------|--------|-----------|
| **Receiving Lens** | ✅ COMPREHENSIVE | `receiving-COMPREHENSIVE.spec.ts` |
| **Document Lens** | ✅ COMPREHENSIVE | `document-lens-comprehensive.spec.ts` |
| **Work Orders** | ✅ GOOD | `work-order-lens-comprehensive.spec.ts` |
| **Parts Lens** | ✅ GOOD | `parts-lens-comprehensive.spec.ts` |
| **Equipment Lens** | ✅ GOOD | `equipment-lens-comprehensive.spec.ts` |
| **Fault Lens** | ✅ GOOD | `fault-lens-comprehensive.spec.ts` |
| **Shopping List** | ✅ GOOD | Multiple tests in `shopping_list/` |
| **Inventory** | ✅ PARTIAL | `inventory-lens-complete.spec.ts` |
| **Email Integration** | ✅ PARTIAL | Multiple email tests |

### Receiving Lens Coverage Detail

The receiving lens has the most comprehensive test coverage:

```typescript
// receiving-COMPREHENSIVE.spec.ts covers:

// Section 1: SUCCESS PATH
✓ Complete workflow - Create → Items → Accept with signature
✓ Captain creates receiving with vendor reference
✓ Add multiple items with prices
✓ Accept receiving with signature

// Section 2: PERMISSIONS
✓ HOD can create/edit AND accept (per registry)
✓ Crew can create (draft mode) and view, but NOT accept

// Section 3: STATE TRANSITIONS
✓ Cannot edit accepted receiving
✓ Cannot accept already-accepted receiving

// Section 4: VALIDATION
✓ Rejects invalid inputs
✓ Rejects missing required fields

// Section 5: REJECTION FLOW
✓ Can reject receiving with reason
✓ Can re-open rejected receiving

// Section 6: AUDIT
✓ All actions recorded in audit trail
✓ User trail completeness

// Section 7: DOCUMENTS
✓ Can attach documents
✓ Can link invoices

// Section 8: EXTRACTION
✓ Advisory extraction does not auto-apply
✓ Manual override of extraction

// Section 9: ADJUSTMENTS
✓ Can adjust items before acceptance
✓ Quantity and pricing updates

// Section 10: RLS ISOLATION
✓ User cannot see other yachts' receivings
```

### Document Lens Coverage Detail

The document lens has near-complete coverage:

```
✓ All 3 roles (Crew, HOD, Captain)
✓ All document actions (attach, extract, update, sign)
✓ Document verification
✓ HOD upload and execution
✓ Suggested actions rendering
✓ Modal execution flow
✓ Role-based visibility
```

### Coverage Gaps

| Area | Status | Notes |
|------|--------|-------|
| Email attachment parsing | ⚠️ PARTIAL | Basic tests exist, edge cases untested |
| Mobile responsive UI | ⚠️ PARTIAL | Only `mobile-responsive.spec.ts` |
| Performance/load testing | ❌ NONE | No load tests in suite |
| Offline mode | ❌ NONE | Not tested |
| Network failures | ⚠️ PARTIAL | Some error handling tests |
| Accessibility (a11y) | ⚠️ MINIMAL | Using ARIA roles but no comprehensive audit |
| Cross-browser | ✅ YES | Playwright runs Chromium, Firefox, WebKit |

---

## Writing New Tests

### Checklist for New Feature Tests

1. **Create test file with proper naming**
   ```
   feature-lens-comprehensive.spec.ts
   OR
   cluster_NN_feature.spec.ts (for microactions)
   ```

2. **Set up test structure**
   ```typescript
   import { test, expect, Page } from '@playwright/test';
   import { loginAs } from './auth.helper';

   test.describe('FEATURE - COMPREHENSIVE', () => {
     // ... tests
   });
   ```

3. **Include all required sections**
   - ✅ SUCCESS path (happy path, all roles)
   - ✅ PERMISSIONS (role-based access)
   - ✅ VALIDATION (invalid inputs)
   - ✅ STATE transitions (invalid transitions)
   - ✅ RLS isolation (multi-tenant safety)
   - ✅ AUDIT trail (logging completeness)

4. **Test all roles involved**
   - Crew (basic user)
   - HOD (approver)
   - Captain (authority)

5. **Add logging for debugging**
   ```typescript
   console.log('\n🎯 SECTION 1: Success Path\n');
   console.log('✓ Step complete');
   console.log('✅ SECTION COMPLETE\n');
   ```

6. **Use data-testid attributes**
   - Ensure UI components have `data-testid` for selection
   - Use accessible role queries (`role="dialog"`, etc.)

7. **Run test locally**
   ```bash
   npx playwright test feature-lens-comprehensive.spec.ts
   ```

8. **Add to CI pipeline** (if needed)
   - Update `.github/workflows/` files
   - Tag as `@critical`, `@standard`, or `@optional`

### Example Template

```typescript
/**
 * FEATURE LENS - COMPREHENSIVE E2E TEST SUITE
 * ============================================
 *
 * Tests EVERYTHING for [feature] lens:
 * - All actions (create, read, update, delete, ...)
 * - All 3 roles (Captain, HOD, Crew)
 * - Success and failure paths
 * - RLS isolation
 * - Audit trail
 * - Frontend + Backend integration
 *
 * Duration: ~5 minutes
 * Run: npx playwright test feature-lens-comprehensive.spec.ts
 */

import { test, expect, Page } from '@playwright/test';
import { loginAs } from './auth.helper';

const API_URL = 'https://pipeline-core.int.celeste7.ai';
const YACHT_ID = 'your-test-yacht-id';

// Helper functions
async function getJWT(page: Page): Promise<string> { /* ... */ }
async function apiCall(jwt: string, action: string, payload: any): Promise<any> { /* ... */ }

test.describe('FEATURE - COMPREHENSIVE', () => {

  // ========================================================================
  // SECTION 1: SUCCESS PATH
  // ========================================================================

  test('SUCCESS: Complete workflow', async ({ page }) => {
    console.log('\n🎯 SECTION 1: Success Path\n');

    await loginAs(page, 'captain');
    const jwt = await getJWT(page);

    // Action 1
    const result1 = await apiCall(jwt, 'action_1', { /* payload */ });
    expect(result1.status).toBe(200);
    console.log('✓ Action 1 complete');

    // Action 2
    const result2 = await apiCall(jwt, 'action_2', { /* payload */ });
    expect(result2.status).toBe(200);
    console.log('✓ Action 2 complete');

    console.log('✅ SECTION 1 COMPLETE\n');
  });

  // ========================================================================
  // SECTION 2: PERMISSIONS
  // ========================================================================

  test('PERMISSIONS: Each role has correct access', async ({ page }) => {
    console.log('\n🎯 SECTION 2: Permissions\n');

    // Test with Crew
    await loginAs(page, 'crew');
    let jwt = await getJWT(page);
    let result = await apiCall(jwt, 'protected_action', { /* ... */ });
    expect(result.status).not.toBe(200);
    console.log('✓ Crew correctly denied');

    // Test with HOD (would need new page/context)
    // ...

    console.log('✅ SECTION 2 COMPLETE\n');
  });

  test.afterAll(async () => {
    console.log('✅ ALL TESTS COMPLETE\n');
  });
});
```

---

## Summary Table

| Aspect | Pattern | Example |
|--------|---------|---------|
| **Framework** | Playwright + Vitest + pytest | Tests for E2E, unit, integration |
| **File naming** | `*-COMPREHENSIVE.spec.ts` | `receiving-COMPREHENSIVE.spec.ts` |
| **Test structure** | Sections with describe/it | SECTION 1, 2, 3 pattern |
| **Roles tested** | Crew, HOD, Captain | All actions tested with each role |
| **API testing** | Direct fetch to `/v1/actions/execute` | JWT header, context, payload |
| **Helpers** | Centralized in auth.helper.ts | `loginAs()`, `apiCall()`, etc. |
| **Coverage** | Receiving & Document have comprehensive tests | ~140+ E2E test files, 90+ Playwright |
| **Logging** | Console logs with emoji markers | `✓`, `✅`, `🎯` for debugging |
| **Data attributes** | `data-testid` for component selection | `[data-testid="action-button"]` |
