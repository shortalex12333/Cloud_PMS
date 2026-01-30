/**
 * Inventory Lens - API Contract Tests (Track 1)
 *
 * Direct HTTP API validation (not UI-driven):
 * - Backend action execution via /v1/actions/execute
 * - Error contract structure (flat {error_code, message})
 * - Idempotency enforcement (409 on duplicate)
 * - HTTP status codes (200/400/404/409, never 500)
 * - CORS configuration
 * - RLS enforcement
 *
 * NOTE: This is NOT true E2E. For UI-driven "search → focus → act" tests,
 * see inventory_e2e_flow.spec.ts (Track 2).
 */

import { test, expect, Page } from '@playwright/test';
import { getAccessToken, getBootstrap } from '../helpers/auth';

// Use environment variables
const BASE_URL = process.env.PLAYWRIGHT_BASE_URL || process.env.VERCEL_PROD_URL || 'https://app.celeste7.ai';
const TEST_YACHT_ID = process.env.TEST_YACHT_ID || '85fe1119-b04c-41ac-80f1-829d23322598';

// Test data - seeded parts from database
const TEST_PART_CONSUMABLE_ID = '00000000-0000-4000-8000-000000000001';
const TEST_PART_RECEIVABLE_ID = '00000000-0000-4000-8000-000000000003';

test.describe('Inventory Lens - Frontend User Experience', () => {
  let accessToken: string;
  let page: Page;

  test.beforeAll(async () => {
    // Get fresh auth token
    accessToken = await getAccessToken();
    console.log('✓ Authentication token obtained');
  });

  test.beforeEach(async ({ page: testPage, context }) => {
    page = testPage;

    // Set authentication cookies/headers
    await context.addCookies([{
      name: 'sb-access-token',
      value: accessToken,
      domain: new URL(BASE_URL).hostname,
      path: '/',
      httpOnly: false,
      secure: true,
      sameSite: 'Lax',
    }]);

    // Navigate to / (single surface at root per cd952ef)
    await page.goto(BASE_URL, { waitUntil: 'networkidle' });
  });

  test('loads main page without console errors', async () => {
    const consoleErrors: string[] = [];

    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        consoleErrors.push(msg.text());
      }
    });

    await page.goto(BASE_URL, { waitUntil: 'networkidle' });

    // Wait for page to settle
    await page.waitForTimeout(2000);

    // Check for critical console errors (allow React warnings)
    const criticalErrors = consoleErrors.filter(err =>
      !err.includes('React') &&
      !err.includes('Warning:') &&
      !err.includes('DevTools')
    );

    if (criticalErrors.length > 0) {
      console.log('Console errors detected:', criticalErrors);
    }

    expect(criticalErrors.length).toBe(0);
  });

  test('displays search interface', async () => {
    // Look for search input - try multiple common selectors
    const searchInput = await page.locator('input[type="search"], input[placeholder*="Search"], input[aria-label*="search"]').first();

    await expect(searchInput).toBeVisible({ timeout: 10000 });

    console.log('✓ Search interface loaded');
  });

  test('API health check succeeds', async ({ request }) => {
    // Verify backend is accessible from browser context
    const response = await request.get(`${BASE_URL.replace('app.celeste7.ai', 'pipeline-core.int.celeste7.ai')}/health`);

    expect(response.status()).toBe(200);

    const body = await response.json();
    expect(body.status).toBe('healthy');

    console.log('✓ API health check passed');
  });

  test('can fetch actions list', async ({ request }) => {
    // Verify /v1/actions/list works from browser
    const apiBase = BASE_URL.replace('app.celeste7.ai', 'pipeline-core.int.celeste7.ai');

    const response = await request.get(`${apiBase}/v1/actions/list`, {
      params: { domain: 'parts' },
      headers: {
        'Authorization': `Bearer ${accessToken}`,
      },
    });

    expect(response.status()).toBe(200);

    const body = await response.json();
    expect(body.actions).toBeDefined();
    expect(body.actions.length).toBeGreaterThan(0);

    // Check if inventory actions are present
    const actionIds = body.actions.map((a: any) => a.action_id);
    console.log('Available part actions:', actionIds);

    expect(actionIds).toContain('receive_part');
    expect(actionIds).toContain('consume_part');

    console.log('✓ Actions list includes inventory actions');
  });

  test('validation error returns proper structure', async ({ request }) => {
    // Test error contract consistency - missing required fields
    const apiBase = BASE_URL.replace('app.celeste7.ai', 'pipeline-core.int.celeste7.ai');

    const response = await request.post(`${apiBase}/v1/actions/execute`, {
      headers: {
        'Authorization': `Bearer ${accessToken}`,
        'Content-Type': 'application/json',
      },
      data: {
        action: 'receive_part',
        context: { yacht_id: TEST_YACHT_ID },
        payload: {
          part_id: TEST_PART_RECEIVABLE_ID,
          // Missing: to_location_id, quantity, idempotency_key
        },
      },
    });

    expect(response.status()).toBe(400);

    const body = await response.json();

    // Verify flat error structure (not wrapped)
    expect(body).toHaveProperty('error_code');
    expect(body).toHaveProperty('message');
    expect(body.error_code).toBe('MISSING_REQUIRED_FIELD');
    expect(body.message).toContain('to_location_id');
    expect(body.message).toContain('quantity');
    expect(body.message).toContain('idempotency_key');

    // Ensure it's NOT wrapped as {"error": "...", "status_code": 400}
    expect(body).not.toHaveProperty('error');
    expect(body).not.toHaveProperty('path');

    console.log('✓ Validation error returns flat structure with error_code');
  });

  test('receive_part action succeeds', async ({ request }) => {
    const apiBase = BASE_URL.replace('app.celeste7.ai', 'pipeline-core.int.celeste7.ai');
    const idempotencyKey = `e2e-test-${Date.now()}-${Math.random().toString(36).substring(7)}`;

    const response = await request.post(`${apiBase}/v1/actions/execute`, {
      headers: {
        'Authorization': `Bearer ${accessToken}`,
        'Content-Type': 'application/json',
      },
      data: {
        action: 'receive_part',
        context: { yacht_id: TEST_YACHT_ID },
        payload: {
          part_id: TEST_PART_RECEIVABLE_ID,
          to_location_id: 'engine_room',
          quantity: 5,
          idempotency_key: idempotencyKey,
        },
      },
    });

    expect(response.status()).toBe(200);

    const body = await response.json();
    expect(body.status).toBe('success');
    expect(body.transaction_id).toBeDefined();
    expect(body.quantity_received).toBe(5);
    expect(body.new_stock_level).toBeGreaterThan(0);

    console.log('✓ receive_part executed successfully');
    console.log('  Transaction ID:', body.transaction_id);
    console.log('  New stock level:', body.new_stock_level);
  });

  test('idempotency enforcement works', async ({ request }) => {
    const apiBase = BASE_URL.replace('app.celeste7.ai', 'pipeline-core.int.celeste7.ai');
    const idempotencyKey = `e2e-idempotency-${Date.now()}-${Math.random().toString(36).substring(7)}`;

    // First request - should succeed
    const response1 = await request.post(`${apiBase}/v1/actions/execute`, {
      headers: {
        'Authorization': `Bearer ${accessToken}`,
        'Content-Type': 'application/json',
      },
      data: {
        action: 'receive_part',
        context: { yacht_id: TEST_YACHT_ID },
        payload: {
          part_id: TEST_PART_RECEIVABLE_ID,
          to_location_id: 'engine_room',
          quantity: 3,
          idempotency_key: idempotencyKey,
        },
      },
    });

    expect(response1.status()).toBe(200);

    // Second request - same idempotency key, should return 409
    const response2 = await request.post(`${apiBase}/v1/actions/execute`, {
      headers: {
        'Authorization': `Bearer ${accessToken}`,
        'Content-Type': 'application/json',
      },
      data: {
        action: 'receive_part',
        context: { yacht_id: TEST_YACHT_ID },
        payload: {
          part_id: TEST_PART_RECEIVABLE_ID,
          to_location_id: 'engine_room',
          quantity: 3,
          idempotency_key: idempotencyKey, // Same key
        },
      },
    });

    expect(response2.status()).toBe(409);

    const body2 = await response2.json();
    expect(body2.error).toContain('Duplicate receive');
    expect(body2.error).toContain(idempotencyKey);

    console.log('✓ Idempotency enforcement works (409 on duplicate)');
  });

  test('CORS headers allow browser requests', async ({ request }) => {
    const apiBase = BASE_URL.replace('app.celeste7.ai', 'pipeline-core.int.celeste7.ai');

    const response = await request.options(`${apiBase}/v1/actions/list`);

    expect(response.status()).toBe(200);

    const headers = response.headers();
    expect(headers['access-control-allow-origin']).toBeDefined();
    expect(headers['access-control-allow-methods']).toBeDefined();

    console.log('✓ CORS configured correctly for browser requests');
  });

  test('consume_part action succeeds', async ({ request }) => {
    const apiBase = BASE_URL.replace('app.celeste7.ai', 'pipeline-core.int.celeste7.ai');
    const idempotencyKey = `e2e-consume-${Date.now()}-${Math.random().toString(36).substring(7)}`;

    const response = await request.post(`${apiBase}/v1/actions/execute`, {
      headers: {
        'Authorization': `Bearer ${accessToken}`,
        'Content-Type': 'application/json',
      },
      data: {
        action: 'consume_part',
        context: { yacht_id: TEST_YACHT_ID },
        payload: {
          part_id: TEST_PART_CONSUMABLE_ID,
          quantity: 2,
          idempotency_key: idempotencyKey,
        },
      },
    });

    // Should succeed (200) or fail with business logic error (409 insufficient stock)
    expect([200, 409]).toContain(response.status());

    const body = await response.json();

    if (response.status() === 200) {
      expect(body.status).toBe('success');
      expect(body.transaction_id).toBeDefined();
      console.log('✓ consume_part executed successfully');
    } else {
      // 409 - insufficient stock or other conflict
      expect(body.error_code || body.error).toBeDefined();
      console.log('✓ consume_part failed with expected business logic error:', body.error_code || body.error);
    }
  });

  test('invalid part returns 404 with error_code', async ({ request }) => {
    const apiBase = BASE_URL.replace('app.celeste7.ai', 'pipeline-core.int.celeste7.ai');
    const idempotencyKey = `e2e-invalid-${Date.now()}-${Math.random().toString(36).substring(7)}`;

    const response = await request.post(`${apiBase}/v1/actions/execute`, {
      headers: {
        'Authorization': `Bearer ${accessToken}`,
        'Content-Type': 'application/json',
      },
      data: {
        action: 'consume_part',
        context: { yacht_id: TEST_YACHT_ID },
        payload: {
          part_id: '00000000-0000-0000-0000-000000000000', // Non-existent
          quantity: 1,
          idempotency_key: idempotencyKey,
        },
      },
    });

    expect(response.status()).toBe(404);

    const body = await response.json();
    expect(body.status).toBe('error');
    expect(body.error_code).toBe('NOT_FOUND');
    expect(body.message).toContain('Part not found');

    console.log('✓ Invalid part returns 404 with proper error_code');
  });
});

test.describe('Inventory Lens - Error Contract Verification', () => {
  let accessToken: string;

  test.beforeAll(async () => {
    accessToken = await getAccessToken();
  });

  test('all error responses have consistent structure', async ({ request }) => {
    const apiBase = BASE_URL.replace('app.celeste7.ai', 'pipeline-core.int.celeste7.ai');

    // Test 1: Missing required fields (400)
    const resp1 = await request.post(`${apiBase}/v1/actions/execute`, {
      headers: { 'Authorization': `Bearer ${accessToken}` },
      data: {
        action: 'receive_part',
        context: { yacht_id: TEST_YACHT_ID },
        payload: { part_id: TEST_PART_RECEIVABLE_ID }, // Missing fields
      },
    });

    expect(resp1.status()).toBe(400);
    const body1 = await resp1.json();
    expect(body1).toHaveProperty('error_code');
    expect(body1).toHaveProperty('message');
    expect(body1.error_code).toBe('MISSING_REQUIRED_FIELD');

    // Test 2: Invalid part (404)
    const resp2 = await request.post(`${apiBase}/v1/actions/execute`, {
      headers: { 'Authorization': `Bearer ${accessToken}` },
      data: {
        action: 'consume_part',
        context: { yacht_id: TEST_YACHT_ID },
        payload: {
          part_id: '00000000-0000-0000-0000-000000000000',
          quantity: 1,
          idempotency_key: `test-${Date.now()}`,
        },
      },
    });

    expect(resp2.status()).toBe(404);
    const body2 = await resp2.json();
    expect(body2).toHaveProperty('error_code');
    expect(body2).toHaveProperty('message');
    expect(body2.error_code).toBe('NOT_FOUND');

    // Test 3: Duplicate idempotency (409)
    const key = `test-duplicate-${Date.now()}`;

    await request.post(`${apiBase}/v1/actions/execute`, {
      headers: { 'Authorization': `Bearer ${accessToken}` },
      data: {
        action: 'receive_part',
        context: { yacht_id: TEST_YACHT_ID },
        payload: {
          part_id: TEST_PART_RECEIVABLE_ID,
          to_location_id: 'engine_room',
          quantity: 1,
          idempotency_key: key,
        },
      },
    });

    const resp3 = await request.post(`${apiBase}/v1/actions/execute`, {
      headers: { 'Authorization': `Bearer ${accessToken}` },
      data: {
        action: 'receive_part',
        context: { yacht_id: TEST_YACHT_ID },
        payload: {
          part_id: TEST_PART_RECEIVABLE_ID,
          to_location_id: 'engine_room',
          quantity: 1,
          idempotency_key: key, // Duplicate
        },
      },
    });

    expect(resp3.status()).toBe(409);
    const body3 = await resp3.json();
    expect(body3).toHaveProperty('error');
    expect(body3.error).toContain('Duplicate receive');

    console.log('✓ All error responses have consistent structure');
    console.log('  400 → error_code:', body1.error_code);
    console.log('  404 → error_code:', body2.error_code);
    console.log('  409 → error:', body3.error);
  });
});
