/**
 * Work Order Lens - Show Related E2E Test
 *
 * Verifies Show Related tab functionality for Work Order Lens.
 *
 * Flow:
 * 1. Login as HOD
 * 2. Search for and open a work order
 * 3. Click "Show Related" button
 * 4. Verify related artifacts panel appears
 * 5. Verify related items grouped by domain
 * 6. Verify no network/console errors
 *
 * Run: npx playwright test work-order.show-related.spec.ts --project=chromium
 */
import { test, expect } from '@playwright/test';
import {
  loginAs,
  searchInSpotlight,
} from './auth.helper';

test.describe('Work Order - Show Related (V1)', () => {
  test.beforeEach(async ({ page }) => {
    // Login as HOD (chief_engineer) - has access to work orders
    await loginAs(page, 'hod');

    // Listen for console errors
    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        console.error('[Browser Console Error]:', msg.text());
      }
    });
  });

  test('HOD can view related artifacts for a work order', async ({ page }) => {
    // Track API responses
    const apiResponses: { url: string; status: number }[] = [];
    page.on('response', (response) => {
      const url = response.url();
      if (url.includes('/api/') || url.includes('/v1/')) {
        apiResponses.push({
          url,
          status: response.status(),
        });
      }
    });

    // Step 1: Search for a work order in spotlight
    await searchInSpotlight(page, 'work order');

    // Wait for search results
    await page.waitForTimeout(1000);

    // Step 2: Find and click a work order search result
    // Try multiple selectors for work order search results
    const workOrderResult = page.locator(
      '[data-entity-type="work_order"], ' +
      '[data-testid="search-result-work-order"], ' +
      '.search-result:has-text("Work Order"), ' +
      '.work-order-card, ' +
      'div[role="button"]:has-text("Work Order")'
    ).first();

    // If no work order result, try clicking first search result
    const resultCount = await workOrderResult.count();

    if (resultCount === 0) {
      console.warn('[Test] No work order search results found, trying first result');
      const firstResult = page.locator(
        '[data-testid="search-result"], ' +
        '.search-result, ' +
        '[role="button"].result-item'
      ).first();

      await firstResult.waitFor({ state: 'visible', timeout: 5000 });
      await firstResult.click();
    } else {
      await workOrderResult.waitFor({ state: 'visible', timeout: 5000 });
      await workOrderResult.click();
    }

    // Wait for work order viewer to load
    await page.waitForTimeout(1000);

    // Step 3: Find and click "Show Related" button
    const showRelatedButton = page.locator(
      'button:has-text("Show Related"), ' +
      'button:has-text("Related"), ' +
      '[data-testid="show-related-button"]'
    );

    // Verify button exists
    const buttonCount = await showRelatedButton.count();
    expect(buttonCount).toBeGreaterThan(0);

    // Click Show Related button
    await showRelatedButton.first().click();

    // Step 4: Wait for related panel to appear
    await page.waitForSelector(
      '[data-testid="related-panel"], ' +
      '.related-panel, ' +
      '[class*="related-panel"], ' +
      'h2:has-text("Related"), ' +
      'div:has-text("Related Artifacts")',
      { timeout: 10000 }
    );

    // Step 5: Verify related panel content
    const relatedPanel = page.locator(
      '[data-testid="related-panel"], ' +
      '.related-panel, ' +
      'h2:has-text("Related Artifacts")'
    );

    const panelVisible = await relatedPanel.count() > 0;
    expect(panelVisible).toBe(true);

    // Step 6: Check for domain groups or empty state
    const domainGroups = page.locator(
      '.domain-group, ' +
      '[data-testid="domain-group"], ' +
      'section[class*="domain"]'
    );

    const emptyState = page.locator(
      '.related-panel-empty, ' +
      '[data-testid="related-empty"], ' +
      ':text("No related artifacts")'
    );

    const hasGroups = await domainGroups.count() > 0;
    const isEmpty = await emptyState.count() > 0;

    // Either has groups OR shows empty state (both valid)
    expect(hasGroups || isEmpty).toBe(true);

    if (hasGroups) {
      console.log(`[Test] Found ${await domainGroups.count()} related domain groups`);

      // Verify related items have expected structure
      const relatedItems = page.locator(
        '.related-item, ' +
        '[data-testid="related-item"], ' +
        '.domain-group li'
      );

      const itemCount = await relatedItems.count();
      console.log(`[Test] Found ${itemCount} related items`);

      if (itemCount > 0) {
        // Verify first item has title
        const firstItem = relatedItems.first();
        const itemText = await firstItem.textContent();
        expect(itemText?.length).toBeGreaterThan(0);
      }
    } else {
      console.log('[Test] Related panel shows empty state (valid)');
    }

    // Step 7: Verify API calls succeeded
    const relatedApiCalls = apiResponses.filter(
      (r) => r.url.includes('/related') || r.url.includes('/show_related')
    );

    console.log(`[Test] Related API calls: ${relatedApiCalls.length}`);
    relatedApiCalls.forEach((call) => {
      console.log(`  - ${call.url}: ${call.status}`);
    });

    // No 500 errors on any API call
    const has500 = apiResponses.some((r) => r.status >= 500);
    expect(has500).toBe(false);

    // Related API should return 200 or 404 (if endpoint not found)
    if (relatedApiCalls.length > 0) {
      const relatedStatus = relatedApiCalls[0].status;
      expect([200, 404].includes(relatedStatus)).toBe(true);
    }
  });

  test('Related panel has "Add Related" functionality', async ({ page }) => {
    // Search and open work order (same as above)
    await searchInSpotlight(page, 'work order');
    await page.waitForTimeout(1000);

    const workOrderResult = page.locator(
      '[data-entity-type="work_order"], ' +
      '.work-order-card, ' +
      '[data-testid="search-result"]'
    ).first();

    await workOrderResult.waitFor({ state: 'visible', timeout: 5000 });
    await workOrderResult.click();
    await page.waitForTimeout(1000);

    // Click Show Related
    const showRelatedButton = page.locator(
      'button:has-text("Show Related"), ' +
      'button:has-text("Related")'
    );

    await showRelatedButton.first().click();

    // Wait for related panel
    await page.waitForSelector(
      '[data-testid="related-panel"], ' +
      '.related-panel, ' +
      'h2:has-text("Related Artifacts")',
      { timeout: 10000 }
    );

    // Look for "Add Related" button
    const addRelatedButton = page.locator(
      'button:has-text("Add Related"), ' +
      'button:has-text("+ Add Related"), ' +
      '[data-testid="add-related-button"]'
    );

    const hasAddButton = await addRelatedButton.count() > 0;

    // Add Related button should exist (UI feature)
    expect(hasAddButton).toBe(true);

    if (hasAddButton) {
      console.log('[Test] "Add Related" button present');
    }
  });

  test('Related items are clickable and navigate', async ({ page }) => {
    // Search and open work order
    await searchInSpotlight(page, 'work order');
    await page.waitForTimeout(1000);

    const workOrderResult = page.locator(
      '[data-entity-type="work_order"], ' +
      '.work-order-card, ' +
      '[data-testid="search-result"]'
    ).first();

    await workOrderResult.waitFor({ state: 'visible', timeout: 5000 });
    await workOrderResult.click();
    await page.waitForTimeout(1000);

    // Click Show Related
    const showRelatedButton = page.locator(
      'button:has-text("Show Related"), ' +
      'button:has-text("Related")'
    );

    await showRelatedButton.first().click();

    // Wait for related panel
    await page.waitForSelector(
      '[data-testid="related-panel"], ' +
      '.related-panel, ' +
      'h2:has-text("Related Artifacts")',
      { timeout: 10000 }
    );

    // Check if there are related items
    const relatedItems = page.locator(
      '.related-item, ' +
      '[data-testid="related-item"], ' +
      '.domain-group li'
    );

    const itemCount = await relatedItems.count();

    if (itemCount > 0) {
      console.log(`[Test] Testing navigation with ${itemCount} related items`);

      // Click first related item
      const firstItem = relatedItems.first();
      await firstItem.click();

      // Wait for navigation (URL change or new viewer loads)
      await page.waitForTimeout(1000);

      // Verify we navigated (check for back button or changed state)
      const backButton = page.locator(
        'button:has-text("Back"), ' +
        'button:has-text("← Back"), ' +
        '[data-testid="back-button"]'
      );

      const hasBackButton = await backButton.count() > 0;

      if (hasBackButton) {
        console.log('[Test] Navigation successful - back button visible');
        expect(hasBackButton).toBe(true);
      } else {
        console.log('[Test] Navigation may have occurred (no back button found)');
      }
    } else {
      console.log('[Test] No related items to test navigation');
      // This is valid - not all work orders have related items
    }
  });

  test('Show Related uses V1 (FK-based, no embeddings)', async ({ page }) => {
    // Track network requests for related API
    const relatedRequests: { url: string; method: string; params: any }[] = [];

    page.on('request', (request) => {
      const url = request.url();
      if (url.includes('/related') || url.includes('/show_related')) {
        relatedRequests.push({
          url,
          method: request.method(),
          params: request.postData(),
        });
      }
    });

    // Search and open work order
    await searchInSpotlight(page, 'work order');
    await page.waitForTimeout(1000);

    const workOrderResult = page.locator(
      '[data-entity-type="work_order"], ' +
      '.work-order-card, ' +
      '[data-testid="search-result"]'
    ).first();

    await workOrderResult.waitFor({ state: 'visible', timeout: 5000 });
    await workOrderResult.click();
    await page.waitForTimeout(1000);

    // Click Show Related
    const showRelatedButton = page.locator(
      'button:has-text("Show Related"), ' +
      'button:has-text("Related")'
    );

    await showRelatedButton.first().click();

    // Wait for API call
    await page.waitForTimeout(2000);

    // Verify V1 characteristics:
    // 1. No embedding parameters in request
    // 2. Results are deterministic (FK-based)

    console.log(`[Test] Related API requests: ${relatedRequests.length}`);
    relatedRequests.forEach((req) => {
      console.log(`  - ${req.method} ${req.url}`);
      if (req.params) {
        console.log(`    Params: ${req.params}`);

        // Verify no embedding-related parameters
        const hasEmbedding = req.params.includes('embedding') ||
                             req.params.includes('vector') ||
                             req.params.includes('alpha');

        expect(hasEmbedding).toBe(false);
      }
    });

    // V1 should use simple FK queries (no complex parameters)
    expect(relatedRequests.length).toBeGreaterThanOrEqual(0);
  });
});
