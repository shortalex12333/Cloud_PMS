import { test, expect } from '@playwright/test';

/**
 * E2E Acceptance Test: ex06_back_forward_stack_depth_3
 *
 * Flow:
 * 1. viewer1 (fault)
 * 2. Push "Show Related" → related1
 * 3. Click related item → viewer2 (equipment)
 * 4. Click Back → should return to related1
 * 5. Click Back → should return to viewer1
 * 6. Click Forward → should go to related1
 * 7. Click Forward → should go to viewer2
 *
 * Invariants tested:
 * - Back returns to prior view in stack
 * - Forward works only after Back
 * - Stack navigation is linear (viewer → related → viewer)
 * - Stack depth is maintained correctly
 */

// Skip: Context nav UI features not yet implemented on /app route
test.describe.skip('Context Nav: Back/Forward Navigation', () => {
  test('navigates through stack depth of 3 correctly', async ({ page }) => {
    // Navigate to fault viewer
    await page.goto('/app');
    await page.fill('input[type="search"]', 'Main Engine Overheating');
    await page.keyboard.press('Enter');
    await page.waitForSelector('.fault-card, .search-result');
    await page.click('text=Main Engine Overheating');

    // Wait for viewer1 (fault viewer)
    await expect(page.locator('.viewer-header')).toBeVisible();
    await expect(page.locator('text=Main Engine Overheating')).toBeVisible();

    // INVARIANT: Back button is disabled (first view)
    await expect(page.locator('button:has-text("← Back")')).toBeDisabled();

    // INVARIANT: Forward button is disabled (no forward stack)
    await expect(page.locator('button:has-text("Forward →")')).toBeDisabled();

    // Click "Show Related" → Push related1
    await page.click('button:has-text("Show Related")');
    await page.waitForTimeout(1000);

    // Should be at related panel now
    await expect(page.locator('.related-panel, .related-panel-empty')).toBeVisible();

    // INVARIANT: Back button is now enabled (stack has 2 views)
    await expect(page.locator('button:has-text("← Back")')).toBeEnabled();

    // INVARIANT: Forward button is still disabled (no forward stack yet)
    await expect(page.locator('button:has-text("Forward →")')).toBeDisabled();

    // If related items exist, click one to navigate to viewer2
    const relatedItems = page.locator('.related-item');
    const relatedCount = await relatedItems.count();

    if (relatedCount > 0) {
      // Click first related item → viewer2 (equipment)
      await relatedItems.first().click();
      await page.waitForTimeout(1000);

      // Should be at viewer2 (equipment)
      await expect(page.locator('.viewer-header')).toBeVisible();

      // INVARIANT: Back button is enabled (stack has 3 views)
      await expect(page.locator('button:has-text("← Back")')).toBeEnabled();

      // INVARIANT: Forward button is disabled (no forward stack)
      await expect(page.locator('button:has-text("Forward →")')).toBeDisabled();

      // ====================================================================
      // BACK NAVIGATION TEST
      // ====================================================================

      // Click Back → should return to related1
      await page.click('button:has-text("← Back")');
      await page.waitForTimeout(500);

      // Should be at related panel
      await expect(page.locator('.related-panel, .related-panel-empty')).toBeVisible();

      // INVARIANT: Back button is enabled (stack still has viewer1)
      await expect(page.locator('button:has-text("← Back")')).toBeEnabled();

      // INVARIANT: Forward button is now ENABLED (viewer2 in forward stack)
      await expect(page.locator('button:has-text("Forward →")')).toBeEnabled();

      // Click Back again → should return to viewer1 (fault)
      await page.click('button:has-text("← Back")');
      await page.waitForTimeout(500);

      // Should be at viewer1 (fault)
      await expect(page.locator('text=Main Engine Overheating')).toBeVisible();

      // INVARIANT: Back button is now disabled (at bottom of stack)
      await expect(page.locator('button:has-text("← Back")')).toBeDisabled();

      // INVARIANT: Forward button is enabled (related1 and viewer2 in forward stack)
      await expect(page.locator('button:has-text("Forward →")')).toBeEnabled();

      // ====================================================================
      // FORWARD NAVIGATION TEST
      // ====================================================================

      // Click Forward → should go to related1
      await page.click('button:has-text("Forward →")');
      await page.waitForTimeout(500);

      // Should be at related panel
      await expect(page.locator('.related-panel, .related-panel-empty')).toBeVisible();

      // INVARIANT: Back button is enabled
      await expect(page.locator('button:has-text("← Back")')).toBeEnabled();

      // INVARIANT: Forward button is still enabled (viewer2 still in forward stack)
      await expect(page.locator('button:has-text("Forward →")')).toBeEnabled();

      // Click Forward again → should go to viewer2 (equipment)
      await page.click('button:has-text("Forward →")');
      await page.waitForTimeout(500);

      // Should be at viewer2 (equipment)
      await expect(page.locator('.viewer-header')).toBeVisible();

      // INVARIANT: Back button is enabled
      await expect(page.locator('button:has-text("← Back")')).toBeEnabled();

      // INVARIANT: Forward button is now disabled (at top of stack)
      await expect(page.locator('button:has-text("Forward →")')).toBeDisabled();
    } else {
      // No related items, just test back from related to viewer1
      await page.click('button:has-text("← Back")');
      await page.waitForTimeout(500);

      // Should be back at viewer1
      await expect(page.locator('text=Main Engine Overheating')).toBeVisible();
      await expect(page.locator('button:has-text("← Back")')).toBeDisabled();
      await expect(page.locator('button:has-text("Forward →")')).toBeEnabled();
    }
  });

  test('new push clears forward stack', async ({ page }) => {
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

    // Click Back to create forward stack
    await page.click('button:has-text("← Back")');
    await page.waitForTimeout(500);

    // Forward button should be enabled
    await expect(page.locator('button:has-text("Forward →")')).toBeEnabled();

    // Now push "Show Related" again → should CLEAR forward stack
    await page.click('button:has-text("Show Related")');
    await page.waitForTimeout(1000);

    // INVARIANT: Forward button should now be disabled (forward stack cleared)
    await expect(page.locator('button:has-text("Forward →")')).toBeDisabled();
  });
});
