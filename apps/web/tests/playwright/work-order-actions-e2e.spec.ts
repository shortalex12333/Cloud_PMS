import { test, expect } from '@playwright/test';

// Use environment variable or default to production
const BASE_URL = process.env.E2E_BASE_URL || 'https://app.celeste7.ai';

test.describe('Work Order Actions E2E', () => {
  test.beforeEach(async ({ page }) => {
    // Login
    await page.goto(`${BASE_URL}/login`);
    await page.waitForTimeout(2000);

    const emailInput = page.locator('input[type="email"], input[name="email"]').first();
    await emailInput.fill('x@alex-short.com');
    await page.locator('input[type="password"]').first().fill('Password2!');
    await page.locator('button[type="submit"]').first().click();
    await page.waitForTimeout(5000);
    console.log('Logged in');
  });

  test('Add Note to Work Order', async ({ page }) => {
    // Capture console errors and network failures
    const consoleErrors: string[] = [];
    const networkFailures: string[] = [];

    page.on('console', msg => {
      if (msg.type() === 'error') {
        consoleErrors.push(msg.text());
        console.log('❌ Console Error:', msg.text());
      }
    });

    page.on('response', response => {
      if (response.status() >= 400) {
        const msg = `${response.status()} ${response.url()}`;
        networkFailures.push(msg);
        console.log('❌ Network Error:', msg);
      }
    });

    // Search for work order - use data-testid selector
    const searchInput = page.locator('[data-testid="search-input"]');
    await searchInput.waitFor({ state: 'visible', timeout: 15000 });
    await searchInput.click();
    await searchInput.fill('generator fault');
    await page.keyboard.press('Enter');
    await page.waitForTimeout(10000);
    console.log('Search complete');

    // Screenshot search results
    await page.screenshot({ path: 'test-results/e2e-01-search-results.png', fullPage: true });

    // Click first work order result
    const result = page.locator('[data-testid="search-result-item"]').first();
    await result.waitFor({ state: 'visible', timeout: 15000 });
    await result.click();
    await page.waitForTimeout(3000);
    console.log('Clicked work order');

    // Screenshot work order panel
    await page.screenshot({ path: 'test-results/e2e-02-work-order-panel.png', fullPage: true });

    // Find and click Add Note button
    const addNoteBtn = page.locator('button:has-text("Add Note")').first();
    await addNoteBtn.waitFor({ state: 'visible', timeout: 10000 });
    await addNoteBtn.click();
    await page.waitForTimeout(1000);
    console.log('Clicked Add Note');

    // Screenshot modal
    await page.screenshot({ path: 'test-results/e2e-03-note-modal.png', fullPage: true });

    // Fill in note - include special characters to test JSONB storage
    const textarea = page.locator('textarea').first();
    await textarea.waitFor({ state: 'visible', timeout: 5000 });
    const noteText = `E2E Test Note - ${new Date().toISOString()} - Special chars: "quotes", 'apostrophe', <brackets>, &amp; émojis 🔧`;
    await textarea.fill(noteText);
    console.log('Filled note text with special characters');

    // Screenshot filled modal
    await page.screenshot({ path: 'test-results/e2e-04-note-filled.png', fullPage: true });

    // Click submit (Add Note button in modal)
    const submitBtn = page.locator('[role="dialog"] button:has-text("Add Note")').last();
    await submitBtn.click();
    console.log('Clicked submit');

    // Wait for response
    await page.waitForTimeout(5000);

    // Screenshot after submit
    await page.screenshot({ path: 'test-results/e2e-05-after-submit.png', fullPage: true });

    // Verify note appears or check for success
    const noteInUI = page.locator(`text=${noteText.substring(0, 20)}`);
    const noteVisible = await noteInUI.isVisible({ timeout: 5000 }).catch(() => false);
    console.log('Note visible in UI:', noteVisible);

    // Check for any error messages in UI
    const errorMsg = page.locator('text=error, text=failed, text=Error');
    const hasError = await errorMsg.isVisible({ timeout: 1000 }).catch(() => false);
    console.log('Has error message:', hasError);

    // Log captured errors
    console.log('Console errors captured:', consoleErrors.length);
    console.log('Network failures captured:', networkFailures.length);

    // Assert no critical failures
    expect(hasError).toBeFalsy();
    expect(networkFailures.filter(f => f.includes('/api/actions'))).toHaveLength(0);
  });

  test('Add Checklist Item to Work Order', async ({ page }) => {
    // Capture console errors and network failures
    const consoleErrors: string[] = [];
    const networkFailures: string[] = [];

    page.on('console', msg => {
      if (msg.type() === 'error') {
        consoleErrors.push(msg.text());
        console.log('❌ Console Error:', msg.text());
      }
    });

    page.on('response', response => {
      if (response.status() >= 400) {
        const msg = `${response.status()} ${response.url()}`;
        networkFailures.push(msg);
        console.log('❌ Network Error:', msg);
      }
    });

    // Search for work order - use data-testid selector
    const searchInput = page.locator('[data-testid="search-input"]');
    await searchInput.waitFor({ state: 'visible', timeout: 15000 });
    await searchInput.click();
    await searchInput.fill('generator fault');
    await page.keyboard.press('Enter');
    await page.waitForTimeout(10000);

    // Click first result
    const result = page.locator('[data-testid="search-result-item"]').first();
    await result.waitFor({ state: 'visible', timeout: 15000 });
    await result.click();
    await page.waitForTimeout(3000);

    // Scroll to Checklist section
    const checklistSection = page.locator('text=Checklist').first();
    await checklistSection.scrollIntoViewIfNeeded();
    await page.waitForTimeout(1000);

    // Click Add Checklist Item
    const addChecklistBtn = page.locator('button:has-text("Add Checklist Item")').first();
    await addChecklistBtn.waitFor({ state: 'visible', timeout: 10000 });
    await addChecklistBtn.click();
    await page.waitForTimeout(1000);
    console.log('Clicked Add Checklist Item');

    // Screenshot modal
    await page.screenshot({ path: 'test-results/e2e-06-checklist-modal.png', fullPage: true });

    // Fill in title - include special characters to test JSONB storage
    const titleInput = page.locator('[role="dialog"] input').first();
    await titleInput.waitFor({ state: 'visible', timeout: 5000 });
    const itemTitle = `E2E Checklist - ${new Date().toISOString()} - "Check valve's" pressure & temp <100°C>`;
    await titleInput.fill(itemTitle);
    console.log('Filled checklist title with special characters');

    // Click submit
    const submitBtn = page.locator('[role="dialog"] button:has-text("Add")').last();
    await submitBtn.click();
    console.log('Clicked submit');

    // Wait for response
    await page.waitForTimeout(5000);

    // Screenshot after submit
    await page.screenshot({ path: 'test-results/e2e-07-checklist-after-submit.png', fullPage: true });

    // Check for errors in UI
    const errorMsg = page.locator('text=error, text=failed, text=Error');
    const hasError = await errorMsg.isVisible({ timeout: 1000 }).catch(() => false);
    console.log('Has error message:', hasError);

    // Log captured errors
    console.log('Console errors captured:', consoleErrors.length);
    console.log('Network failures captured:', networkFailures.length);

    // Assert no critical failures
    expect(hasError).toBeFalsy();
    expect(networkFailures.filter(f => f.includes('/api/actions'))).toHaveLength(0);
  });
});
