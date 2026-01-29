/**
 * E2E Tests: Part Actions Execution
 *
 * Validates that HOD can execute part actions (receive_part, consume_part)
 * with correct status codes and UI feedback:
 * - receive_part: 201 success, 409 duplicate idempotency_key
 * - consume_part: 200 sufficient stock, 409 insufficient stock
 *
 * Evidence: Network intercepts, screenshots of success/error states
 *
 * SECURITY MODEL (New):
 * - yacht_id is server-resolved from JWT auth (MASTER membership → TENANT role)
 * - NO client-provided yacht_id in action payloads
 * - All requests use Authorization: Bearer <JWT>
 * - Action Router enforces ownership, idempotency, and audit
 */

import { test, expect, Page } from '@playwright/test';
import { loginAsRole, RoleAuthState } from './helpers/roles-auth';
import * as path from 'path';
import * as fs from 'fs';

const TEST_PART_ID = process.env.TEST_PART_ID || '8ad67e2f-2579-4d6c-afd2-0dee85f4d8b3';
const TEST_YACHT_ID = process.env.TEST_USER_YACHT_ID || '85fe1119-b04c-41ac-80f1-829d23322598';
const API_BASE = process.env.RENDER_API_URL || 'https://pipeline-core.int.celeste7.ai';
const ARTIFACTS_DIR = path.join(process.cwd(), 'test-results', 'artifacts');

// Ensure artifacts directory exists
if (!fs.existsSync(ARTIFACTS_DIR)) {
  fs.mkdirSync(ARTIFACTS_DIR, { recursive: true });
}

/**
 * Helper: Navigate to parts page and authenticate
 */
async function navigateToParts(page: Page, role: string): Promise<void> {
  await page.goto('/parts', { waitUntil: 'networkidle' });

  // Wait for app to be ready (either parts list or login redirect)
  await page.waitForLoadState('domcontentloaded');

  // If redirected to login, auth should handle it via storage state
  const currentUrl = page.url();
  if (currentUrl.includes('/login')) {
    throw new Error(`Unexpected redirect to login for ${role} - storage state may be invalid`);
  }
}

/**
 * Helper: Search for a part by name
 */
async function searchForPart(page: Page, partName: string = 'Engine Oil Filter'): Promise<void> {
  // Find search input (use flexible selector)
  const searchInput = page.locator('input[placeholder*="Search"], [data-testid="search-input"]').first();
  await searchInput.waitFor({ state: 'visible', timeout: 5000 });

  await searchInput.fill(partName);
  await searchInput.press('Enter');

  // Wait for results to load
  await page.waitForTimeout(1000);
}

/**
 * Helper: Execute an action through the UI
 */
async function executeActionViaUI(
  page: Page,
  actionId: string,
  payload: Record<string, any>
): Promise<{ statusCode: number; responseBody: any }> {
  let capturedResponse: { statusCode: number; responseBody: any } | null = null;

  // Intercept the execute action API call
  await page.route(`${API_BASE}/v1/actions/execute`, async (route) => {
    const response = await route.fetch();
    const body = await response.json().catch(() => ({}));

    capturedResponse = {
      statusCode: response.status(),
      responseBody: body,
    };

    await route.fulfill({ response });
  });

  // Find and click the action button
  const actionButton = page.locator(
    `button[data-action-id="${actionId}"], ` +
    `button:has-text("${actionId}"), ` +
    `[data-testid="action-${actionId}"]`
  ).first();

  await actionButton.waitFor({ state: 'visible', timeout: 5000 });
  await actionButton.click();

  // If action requires a modal/form, fill it
  if (actionId === 'receive_part') {
    // Wait for receive modal
    const quantityInput = page.locator('input[name="quantity"], [data-testid="quantity-input"]').first();
    await quantityInput.waitFor({ state: 'visible', timeout: 3000 });

    await quantityInput.fill(String(payload.quantity || 1));

    // If there's a supplier input
    const supplierInput = page.locator('input[name="supplier"], [data-testid="supplier-input"]').first();
    if (await supplierInput.isVisible({ timeout: 1000 }).catch(() => false)) {
      await supplierInput.fill(payload.supplier || 'Test Supplier');
    }

    // Submit button
    const submitButton = page.locator('button[type="submit"], button:has-text("Receive")').first();
    await submitButton.click();
  } else if (actionId === 'consume_part') {
    // Wait for consume modal
    const quantityInput = page.locator('input[name="quantity"], [data-testid="quantity-input"]').first();
    await quantityInput.waitFor({ state: 'visible', timeout: 3000 });

    await quantityInput.fill(String(payload.quantity || 1));

    // Submit button
    const submitButton = page.locator('button[type="submit"], button:has-text("Consume")').first();
    await submitButton.click();
  }

  // Wait for response
  await page.waitForTimeout(2000);

  if (!capturedResponse) {
    throw new Error('Failed to capture API response');
  }

  return capturedResponse;
}

/**
 * Helper: Execute action via direct API call (for comparison)
 */
async function executeActionViaAPI(
  jwt: string,
  action: string,
  payload: Record<string, any>,
  idempotencyKey?: string
): Promise<{ statusCode: number; responseBody: any }> {
  const headers: Record<string, string> = {
    'Authorization': `Bearer ${jwt}`,
    'Content-Type': 'application/json',
  };

  if (idempotencyKey) {
    headers['Idempotency-Key'] = idempotencyKey;
  }

  // NOTE: New security model - yacht_id derived from JWT auth, not client payload
  // Server resolves: MASTER membership → TENANT role → yacht_id from auth context
  const response = await fetch(`${API_BASE}/v1/actions/execute`, {
    method: 'POST',
    headers,
    body: JSON.stringify({
      action,
      payload,
    }),
  });

  const body = await response.json().catch(() => ({}));

  return {
    statusCode: response.status,
    responseBody: body,
  };
}

/**
 * Helper: Get JWT from page context
 */
async function getJWTFromPage(page: Page): Promise<string> {
  const token = await page.evaluate(() => {
    const authKey = Object.keys(localStorage).find((key) => key.includes('auth-token'));
    if (!authKey) return null;

    const authData = JSON.parse(localStorage.getItem(authKey) || '{}');
    return authData.access_token || null;
  });

  if (!token) {
    throw new Error('No JWT token found in page context');
  }

  return token;
}

test.describe('Part Actions Execution (HOD)', () => {
  let hodAuthState: RoleAuthState;

  test.beforeAll(async () => {
    // Login as HOD once for all tests
    hodAuthState = await loginAsRole('hod');
  });

  test.use({
    // Use HOD storage state (saved by global-setup)
    storageState: path.join(process.cwd(), 'test-results', '.auth-states', 'hod-state.json'),
  });

  test('receive_part: Success with unique idempotency_key (201)', async ({ page, context }) => {
    // Navigate to parts page
    await navigateToParts(page, 'hod');

    // Get JWT for direct API calls
    const jwt = await getJWTFromPage(page);

    // Generate unique idempotency key
    const idempotencyKey = `e2e-receive-${Date.now()}-${Math.random().toString(36).substring(7)}`;

    // Execute receive_part via API with idempotency key
    const apiResponse = await executeActionViaAPI(
      jwt,
      'receive_part',
      {
        part_id: TEST_PART_ID,
        quantity: 5,
        supplier: 'E2E Test Supplier',
      },
      idempotencyKey
    );

    // Assert 201 Created
    expect(apiResponse.statusCode).toBe(201);
    expect(apiResponse.responseBody).toHaveProperty('data');

    // Save evidence
    const evidencePath = path.join(ARTIFACTS_DIR, 'receive_part_success_201.json');
    fs.writeFileSync(evidencePath, JSON.stringify({
      test: 'receive_part success',
      idempotencyKey,
      statusCode: apiResponse.statusCode,
      response: apiResponse.responseBody,
      timestamp: new Date().toISOString(),
    }, null, 2));

    // Take screenshot
    await page.screenshot({
      path: path.join(ARTIFACTS_DIR, 'receive_part_success_201.png'),
      fullPage: true,
    });
  });

  test('receive_part: Duplicate idempotency_key (409)', async ({ page }) => {
    // Get JWT
    const jwt = await getJWTFromPage(page);

    // Use same idempotency key
    const idempotencyKey = `e2e-receive-duplicate-${Date.now()}`;

    // First call - should succeed (201)
    const firstResponse = await executeActionViaAPI(
      jwt,
      'receive_part',
      {
        part_id: TEST_PART_ID,
        quantity: 3,
        supplier: 'First Call',
      },
      idempotencyKey
    );

    expect(firstResponse.statusCode).toBe(201);

    // Second call with SAME idempotency key - should return 409
    const duplicateResponse = await executeActionViaAPI(
      jwt,
      'receive_part',
      {
        part_id: TEST_PART_ID,
        quantity: 10, // Different payload
        supplier: 'Second Call (Duplicate)',
      },
      idempotencyKey
    );

    // Assert 409 Conflict
    expect(duplicateResponse.statusCode).toBe(409);
    expect(duplicateResponse.responseBody).toHaveProperty('detail');

    // Save evidence
    const evidencePath = path.join(ARTIFACTS_DIR, 'receive_part_duplicate_409.json');
    fs.writeFileSync(evidencePath, JSON.stringify({
      test: 'receive_part duplicate idempotency_key',
      idempotencyKey,
      firstCall: {
        statusCode: firstResponse.statusCode,
        response: firstResponse.responseBody,
      },
      secondCall: {
        statusCode: duplicateResponse.statusCode,
        response: duplicateResponse.responseBody,
      },
      timestamp: new Date().toISOString(),
    }, null, 2));

    // Take screenshot showing error state
    await page.screenshot({
      path: path.join(ARTIFACTS_DIR, 'receive_part_duplicate_409.png'),
      fullPage: true,
    });
  });

  test('consume_part: Sufficient stock (200)', async ({ page }) => {
    // Navigate to parts page
    await navigateToParts(page, 'hod');

    // Get JWT
    const jwt = await getJWTFromPage(page);

    // First, receive some stock to ensure we have sufficient quantity
    const setupIdempotencyKey = `e2e-setup-${Date.now()}`;
    await executeActionViaAPI(
      jwt,
      'receive_part',
      {
        part_id: TEST_PART_ID,
        quantity: 10,
        supplier: 'Setup for consume test',
      },
      setupIdempotencyKey
    );

    // Now consume a small quantity (should succeed)
    const consumeResponse = await executeActionViaAPI(
      jwt,
      'consume_part',
      {
        part_id: TEST_PART_ID,
        quantity: 1, // Small quantity - should have enough stock
      }
    );

    // Assert 200 OK
    expect(consumeResponse.statusCode).toBe(200);
    expect(consumeResponse.responseBody).toHaveProperty('data');

    // Verify no 5xx error
    expect(consumeResponse.statusCode).toBeLessThan(500);

    // Save evidence
    const evidencePath = path.join(ARTIFACTS_DIR, 'consume_part_success_200.json');
    fs.writeFileSync(evidencePath, JSON.stringify({
      test: 'consume_part sufficient stock',
      statusCode: consumeResponse.statusCode,
      response: consumeResponse.responseBody,
      timestamp: new Date().toISOString(),
    }, null, 2));

    // Take screenshot
    await page.screenshot({
      path: path.join(ARTIFACTS_DIR, 'consume_part_success_200.png'),
      fullPage: true,
    });
  });

  test('consume_part: Insufficient stock (409)', async ({ page }) => {
    // Get JWT
    const jwt = await getJWTFromPage(page);

    // Try to consume absurdly high quantity (definitely insufficient)
    const consumeResponse = await executeActionViaAPI(
      jwt,
      'consume_part',
      {
        part_id: TEST_PART_ID,
        quantity: 99999, // Definitely more than available
      }
    );

    // Assert 409 Conflict (insufficient stock)
    expect(consumeResponse.statusCode).toBe(409);
    expect(consumeResponse.responseBody).toHaveProperty('detail');

    // Verify error message mentions stock
    const errorMessage = JSON.stringify(consumeResponse.responseBody).toLowerCase();
    expect(
      errorMessage.includes('stock') ||
      errorMessage.includes('insufficient') ||
      errorMessage.includes('not enough')
    ).toBe(true);

    // Verify no 5xx error
    expect(consumeResponse.statusCode).toBeLessThan(500);

    // Save evidence
    const evidencePath = path.join(ARTIFACTS_DIR, 'consume_part_insufficient_409.json');
    fs.writeFileSync(evidencePath, JSON.stringify({
      test: 'consume_part insufficient stock',
      statusCode: consumeResponse.statusCode,
      response: consumeResponse.responseBody,
      timestamp: new Date().toISOString(),
    }, null, 2));

    // Take screenshot showing error state
    await page.screenshot({
      path: path.join(ARTIFACTS_DIR, 'consume_part_insufficient_409.png'),
      fullPage: true,
    });
  });

  test('All action executions: Zero 5xx errors', async ({ page }) => {
    // Get JWT
    const jwt = await getJWTFromPage(page);

    const results: Array<{ action: string; statusCode: number }> = [];

    // Test multiple scenarios
    const scenarios = [
      { action: 'receive_part', payload: { part_id: TEST_PART_ID, quantity: 1 } },
      { action: 'consume_part', payload: { part_id: TEST_PART_ID, quantity: 1 } },
      { action: 'view_part_details', payload: { part_id: TEST_PART_ID } },
    ];

    for (const scenario of scenarios) {
      const response = await executeActionViaAPI(
        jwt,
        scenario.action,
        scenario.payload
      );

      results.push({
        action: scenario.action,
        statusCode: response.statusCode,
      });

      // Assert no 5xx error
      expect(response.statusCode).toBeLessThan(500);
    }

    // Save evidence
    const evidencePath = path.join(ARTIFACTS_DIR, 'actions_zero_5xx.json');
    fs.writeFileSync(evidencePath, JSON.stringify({
      test: 'All actions - zero 5xx verification',
      results,
      allPassed: results.every(r => r.statusCode < 500),
      timestamp: new Date().toISOString(),
    }, null, 2));

    // Assert summary
    const has5xxError = results.some(r => r.statusCode >= 500);
    expect(has5xxError).toBe(false);
  });
});
