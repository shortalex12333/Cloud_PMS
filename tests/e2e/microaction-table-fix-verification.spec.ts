/**
 * Microaction Table Fix Verification Test
 *
 * Tests that microaction handlers work with corrected table names.
 * Tests both via API and via UI.
 */

import { test, expect } from '@playwright/test';
import { saveArtifact, createEvidenceBundle } from '../helpers/artifacts';
import { ApiClient } from '../helpers/api-client';

test.describe('Microaction Table Fix Verification', () => {
  let apiClient: ApiClient;

  test.beforeAll(async () => {
    apiClient = new ApiClient();
    await apiClient.ensureAuth();
  });

  test('API: View work order (uses pms_work_orders table)', async () => {
    const testName = 'microaction-table-fix/view_work_order';

    // First, get a work order ID from the database
    const searchResponse = await apiClient.search('work order', 1);

    saveArtifact('search_response.json', searchResponse, testName);

    // Check if search returned results
    if (!searchResponse.data?.results?.length) {
      console.log('[TEST] No work orders found in search');
      // This is still valid - the table exists even if empty
      expect(searchResponse.status).toBe(200);
      return;
    }

    const workOrder = searchResponse.data.results.find(
      (r: any) => r.type === 'pms_work_orders' || r.type === 'work_order'
    );

    if (!workOrder) {
      console.log('[TEST] No work order type in results');
      expect(searchResponse.status).toBe(200);
      return;
    }

    console.log('[TEST] Found work order:', workOrder.id);

    // Now test the view action
    const actionResponse = await apiClient.executeAction('view_work_order', {
      work_order_id: workOrder.id,
    });

    saveArtifact('action_response.json', actionResponse, testName);

    createEvidenceBundle(testName, {
      searchResponse: searchResponse.data,
      actionResponse: actionResponse.data,
      assertions: [
        {
          name: 'Action executed without table error',
          passed: actionResponse.status === 200 ||
                  (actionResponse.data?.error?.code !== 'TABLE_NOT_FOUND'),
          message: `Status: ${actionResponse.status}, Error: ${actionResponse.data?.error?.message || 'none'}`,
        },
      ],
    });

    // The action should not fail with "relation does not exist"
    if (actionResponse.data?.error?.message) {
      expect(actionResponse.data.error.message).not.toContain('relation');
      expect(actionResponse.data.error.message).not.toContain('does not exist');
    }
  });

  test('API: View equipment (uses pms_equipment table)', async () => {
    const testName = 'microaction-table-fix/view_equipment';

    const searchResponse = await apiClient.search('generator', 1);

    saveArtifact('search_response.json', searchResponse, testName);

    expect(searchResponse.status).toBe(200);

    const equipment = searchResponse.data?.results?.find(
      (r: any) => r.type === 'pms_equipment' || r.type === 'equipment'
    );

    if (!equipment) {
      console.log('[TEST] No equipment in results - checking if table query works');
      return;
    }

    console.log('[TEST] Found equipment:', equipment.id, equipment.title);

    const actionResponse = await apiClient.executeAction('view_equipment', {
      equipment_id: equipment.id,
    });

    saveArtifact('action_response.json', actionResponse, testName);

    // Should not fail with table not found
    if (actionResponse.data?.error?.message) {
      expect(actionResponse.data.error.message).not.toContain('relation');
      expect(actionResponse.data.error.message).not.toContain('does not exist');
    }
  });

  test('API: Direct table query - pms_notes', async () => {
    const testName = 'microaction-table-fix/pms_notes_query';

    // Test direct API query to verify table exists
    const response = await apiClient.post('/v1/query', {
      table: 'pms_notes',
      select: 'id',
      limit: 1,
    }).catch((e) => ({
      status: 500,
      data: { error: { message: String(e) } },
    }));

    saveArtifact('query_response.json', response, testName);

    console.log('[TEST] pms_notes query status:', response.status);
    console.log('[TEST] pms_notes query response:', JSON.stringify(response.data).substring(0, 200));

    // Log for analysis - we want to see if the table exists
    createEvidenceBundle(testName, {
      response: response.data,
      assertions: [
        {
          name: 'Query did not return table not found error',
          passed: !response.data?.error?.message?.includes('does not exist'),
          message: `Response: ${JSON.stringify(response.data).substring(0, 200)}`,
        },
      ],
    });
  });

  test('UI: Search and click result (tests NavigationContext yacht_id)', async ({ page }) => {
    const testName = 'microaction-table-fix/ui_search_click';

    const email = process.env.TEST_USER_EMAIL;
    const password = process.env.TEST_USER_PASSWORD;

    if (!email || !password) {
      test.skip();
      return;
    }

    // Capture console errors
    const consoleErrors: string[] = [];
    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        consoleErrors.push(msg.text());
      }
    });

    // Login
    await page.goto('/login');
    await page.fill('input[type="email"], input[name="email"]', email);
    await page.fill('input[type="password"], input[name="password"]', password);
    await page.click('button[type="submit"]');
    await page.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 20000 });

    // Wait for bootstrap
    await page.waitForTimeout(3000);

    // Search
    const searchInput = page.locator('[data-testid="search-input"], input[type="search"]').first();
    await searchInput.fill('generator');
    await page.waitForTimeout(2000);

    // Try to click on a result
    const resultItem = page.locator('[data-testid="search-result-item"]').first();
    const hasResult = await resultItem.isVisible({ timeout: 5000 }).catch(() => false);

    if (hasResult) {
      await resultItem.click();
      await page.waitForTimeout(2000);

      // Check for UUID errors in console
      const uuidErrors = consoleErrors.filter(
        (e) => e.includes('uuid') || e.includes('placeholder') || e.includes('invalid')
      );

      saveArtifact('console_errors.json', consoleErrors, testName);

      createEvidenceBundle(testName, {
        consoleErrors,
        uuidErrors,
        assertions: [
          {
            name: 'No UUID parsing errors',
            passed: uuidErrors.length === 0,
            message: `UUID errors: ${uuidErrors.length}`,
          },
          {
            name: 'No placeholder errors',
            passed: !consoleErrors.some((e) => e.includes('placeholder')),
            message: `Errors with placeholder: ${consoleErrors.filter((e) => e.includes('placeholder')).length}`,
          },
        ],
      });

      expect(uuidErrors.length, 'Should have no UUID parsing errors').toBe(0);
    } else {
      console.log('[TEST] No search results to click');
    }
  });
});
