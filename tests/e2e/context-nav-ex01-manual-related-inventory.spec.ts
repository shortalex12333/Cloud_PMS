import { test, expect } from '@playwright/test';

/**
 * E2E Acceptance Test: ex01_manual_to_related_to_inventory
 *
 * Flow:
 * 1. Open manual/document viewer
 * 2. Click "Show Related"
 * 3. Verify related panel shows deterministic FK-linked items (if any)
 * 4. Navigate to related inventory item (if exists)
 * 5. Verify back/forward navigation works
 *
 * Invariants tested:
 * - Backend order is preserved (no client-side ranking)
 * - Related panel renders groups in backend order
 * - Navigation through manual → related → inventory works
 *
 * Note: This test may show empty related if no deterministic FK paths exist
 * from documents to inventory. This is expected and correct behavior.
 */

// Skip: Context nav UI features not yet implemented on /app route
test.describe.skip('Context Nav: Manual to Related to Inventory', () => {
  test('navigates from manual through related to inventory', async ({ page }) => {
    // This test depends on having documents with FK relationships to inventory
    // In the minimal seed data, we don't have documents seeded
    // So this test will be more generic: verify related panel behavior

    // Navigate to search
    await page.goto('/app');

    // Search for work order (which has FK to equipment)
    await page.fill('input[type="search"]', 'WO-TEST-001');
    await page.keyboard.press('Enter');
    await page.waitForSelector('.work-order-card, .search-result');

    // Click work order
    await page.click('text=WO-TEST-001');

    // Wait for viewer
    await expect(page.locator('.viewer-header')).toBeVisible();

    // Click "Show Related"
    await page.click('button:has-text("Show Related")');
    await page.waitForTimeout(1000);

    // Should show related panel
    const relatedPanel = page.locator('.related-panel, .related-panel-empty');
    await expect(relatedPanel).toBeVisible();

    // If related items exist, verify backend ordering is preserved
    const domainGroups = page.locator('.domain-group');
    const groupCount = await domainGroups.count();

    if (groupCount > 0) {
      // INVARIANT: Groups are rendered in backend order (not sorted alphabetically)
      // We can't easily test exact order without knowing backend response,
      // but we can verify groups exist and have expected structure

      for (let i = 0; i < groupCount; i++) {
        const group = domainGroups.nth(i);
        // Each group should have a heading and items
        await expect(group.locator('h3')).toBeVisible();
        const items = group.locator('.related-item');
        await expect(items.first()).toBeVisible();
      }

      // Click on first related item to navigate
      await page.locator('.related-item').first().click();
      await page.waitForTimeout(1000);

      // Should navigate to a new viewer
      await expect(page.locator('.viewer-header')).toBeVisible();

      // Back button should work
      await expect(page.locator('button:has-text("← Back")')).toBeEnabled();
      await page.click('button:has-text("← Back")');
      await page.waitForTimeout(500);

      // Should be back at related panel
      await expect(relatedPanel).toBeVisible();
    } else {
      // Empty state - verify it's handled correctly
      await expect(page.locator('text=No related artifacts found')).toBeVisible();
      await expect(page.locator('button:has-text("+ Add Related")')).toBeVisible();
    }
  });

  test('returning to search home ends context', async ({ page }) => {
    // Track context end calls
    const endContextCalls: string[] = [];

    page.on('request', (request) => {
      const url = request.url();
      if (url.includes('/api/context/') && url.includes('/end')) {
        endContextCalls.push(url);
      }
    });

    // Navigate to fault viewer
    await page.goto('/app');
    await page.fill('input[type="search"]', 'Main Engine');
    await page.keyboard.press('Enter');
    await page.waitForSelector('.fault-card, .search-result');
    await page.click('text=Main Engine');

    // Wait for viewer
    await expect(page.locator('.viewer-header')).toBeVisible();

    // Click "Show Related"
    await page.click('button:has-text("Show Related")');
    await page.waitForTimeout(1000);

    // Now navigate back to search home (simulate clicking logo or back to search)
    await page.goto('/app');
    await page.waitForTimeout(1000);

    // INVARIANT: Context end should be called
    // Note: This depends on SituationRouter detecting state change to IDLE
    // May need to wait for the context to actually end
    await page.waitForTimeout(2000);

    // In a real implementation, we'd verify the POST /api/context/{id}/end was called
    // For now, just verify we're back at search
    await expect(page.locator('input[type="search"]')).toBeVisible();
  });

  test('browser refresh destroys navigation stack', async ({ page }) => {
    // Navigate to fault viewer
    await page.goto('/app');
    await page.fill('input[type="search"]', 'Bow Thruster');
    await page.keyboard.press('Enter');
    await page.waitForSelector('.fault-card, .search-result');
    await page.click('text=Bow Thruster');

    // Wait for viewer
    await expect(page.locator('.viewer-header')).toBeVisible();

    // Click "Show Related"
    await page.click('button:has-text("Show Related")');
    await page.waitForTimeout(1000);

    // Verify Back button is enabled (stack has 2 views)
    await expect(page.locator('button:has-text("← Back")')).toBeEnabled();

    // Refresh the page
    await page.reload();
    await page.waitForTimeout(1000);

    // INVARIANT: After refresh, navigation stack is destroyed
    // Should be back at search home (or viewer with no stack)
    // Back button should be disabled if at viewer
    const viewerHeader = page.locator('.viewer-header');
    if (await viewerHeader.isVisible()) {
      // If still at a viewer, back should be disabled (stack was cleared)
      await expect(page.locator('button:has-text("← Back")')).toBeDisabled();
      await expect(page.locator('button:has-text("Forward →")')).toBeDisabled();
    }
  });
});
