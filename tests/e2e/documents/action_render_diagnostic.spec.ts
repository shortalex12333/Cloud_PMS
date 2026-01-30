/**
 * Action Render Diagnostic Test
 *
 * Detailed test to diagnose why action chips aren't rendering
 * even though /v1/actions/list is being called
 */
import { test, expect, Page } from '@playwright/test';
import { saveArtifact } from '../../helpers/artifacts';

const APP_URL = process.env.APP_URL || 'https://app.celeste7.ai';

async function loginFresh(page: Page): Promise<void> {
  await page.goto(APP_URL);
  await page.waitForSelector('input[type="email"]', { timeout: 15000 });
  await page.fill('input[type="email"]', 'hod.tenant@alex-short.com');
  await page.fill('input[type="password"]', 'Password2!');
  await page.click('button[type="submit"]');
  await page.waitForTimeout(5000);
}

test.describe('Action Render Diagnostic', () => {

  test('Detailed trace of action rendering', async ({ page }) => {
    const testName = 'documents/action-render-trace';

    // Capture console logs
    const consoleLogs: string[] = [];
    page.on('console', (msg) => {
      const text = msg.text();
      if (text.includes('action') || text.includes('Action') || text.includes('suggestions') || text.includes('useCelesteSearch')) {
        consoleLogs.push(`[${msg.type()}] ${text}`);
      }
    });

    // Track API responses
    const apiResponses: { url: string; status: number; body?: any }[] = [];
    page.on('response', async (response) => {
      if (response.url().includes('/v1/actions/list')) {
        try {
          const body = await response.json();
          apiResponses.push({
            url: response.url(),
            status: response.status(),
            body,
          });
        } catch {
          apiResponses.push({
            url: response.url(),
            status: response.status(),
          });
        }
      }
    });

    await loginFresh(page);

    // Find search input
    const searchInput = page.locator('input[placeholder*="Search"], input[placeholder*="search"], [data-testid="search-input"]').first();
    await expect(searchInput).toBeVisible({ timeout: 10000 });

    // Type query
    await searchInput.click();
    await searchInput.fill('upload document');

    // Wait for API call and rendering
    await page.waitForTimeout(3000);

    // Check for suggested actions container
    const suggestedActionsContainer = page.locator('[data-testid="suggested-actions"]');
    const containerExists = await suggestedActionsContainer.count() > 0;

    // Check for individual action buttons
    const actionButtons = page.locator('[data-testid^="action-btn-"]');
    const buttonCount = await actionButtons.count();

    // Check for any button with "Upload" text
    const uploadButtons = page.locator('button:has-text("Upload")');
    const uploadButtonCount = await uploadButtons.count();

    // Get button labels if any exist
    const buttonLabels: string[] = [];
    if (buttonCount > 0) {
      for (let i = 0; i < buttonCount; i++) {
        const label = await actionButtons.nth(i).textContent();
        if (label) buttonLabels.push(label);
      }
    }

    // Screenshot
    await page.screenshot({ path: `test-results/artifacts/${testName}/search_state.png`, fullPage: true });

    // Get page HTML for the search area
    const searchAreaHtml = await page.locator('.spotlight-search, [data-testid="spotlight-search"], [class*="spotlight"]').first().innerHTML().catch(() => 'NOT FOUND');

    // Build diagnostic report
    const report = {
      timestamp: new Date().toISOString(),
      query: 'upload document',

      apiCallsMade: apiResponses.length,
      apiResponses: apiResponses.map(r => ({
        url: r.url,
        status: r.status,
        actionsCount: r.body?.actions?.length || 0,
        actions: r.body?.actions?.map((a: any) => a.action_id) || [],
      })),

      uiState: {
        suggestedActionsContainerExists: containerExists,
        actionButtonCount: buttonCount,
        uploadButtonCount: uploadButtonCount,
        buttonLabels,
      },

      consoleLogs: consoleLogs.slice(-50), // Last 50 relevant logs

      htmlSnippet: searchAreaHtml.substring(0, 2000),
    };

    saveArtifact('action_render_diagnostic.json', report, testName);

    // Console output
    console.log('\n========================================');
    console.log('ACTION RENDER DIAGNOSTIC');
    console.log('========================================');
    console.log('API calls made:', apiResponses.length);
    if (apiResponses.length > 0) {
      console.log('API response actions:', apiResponses[0]?.body?.actions?.length || 0);
    }
    console.log('Suggested actions container exists:', containerExists);
    console.log('Action buttons found:', buttonCount);
    console.log('Upload buttons found:', uploadButtonCount);
    console.log('Button labels:', buttonLabels);
    console.log('Console logs with "action":', consoleLogs.length);
    console.log('========================================\n');

    // Assertions for diagnosis
    expect(apiResponses.length).toBeGreaterThan(0); // API was called

    if (apiResponses.length > 0 && apiResponses[0].body?.actions?.length > 0) {
      // API returned actions, so container SHOULD exist
      if (!containerExists) {
        console.log('BUG: API returned actions but container not rendered');
        console.log('Relevant console logs:');
        consoleLogs.forEach(log => console.log('  ', log));
      }
    }
  });

  test('Check state after search with extended wait', async ({ page }) => {
    const testName = 'documents/extended-wait';

    await loginFresh(page);

    const searchInput = page.locator('input[placeholder*="Search"], input[placeholder*="search"]').first();
    await searchInput.click();
    await searchInput.fill('upload document');

    // Extended wait - 5 seconds
    await page.waitForTimeout(5000);

    // Multiple attempts to find actions
    for (let i = 0; i < 3; i++) {
      const containerCount = await page.locator('[data-testid="suggested-actions"]').count();
      const buttonCount = await page.locator('[data-testid^="action-btn-"]').count();

      console.log(`Attempt ${i + 1}: Container=${containerCount}, Buttons=${buttonCount}`);

      if (containerCount > 0 || buttonCount > 0) {
        await page.screenshot({ path: `test-results/artifacts/${testName}/found_actions.png` });
        expect(buttonCount).toBeGreaterThan(0);
        return;
      }

      await page.waitForTimeout(1000);
    }

    await page.screenshot({ path: `test-results/artifacts/${testName}/no_actions_found.png` });

    // This test documents the current state
    console.log('Actions not rendered after extended wait');
  });

});
