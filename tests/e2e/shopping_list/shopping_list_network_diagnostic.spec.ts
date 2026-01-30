/**
 * Shopping List Network Diagnostic
 *
 * Purpose: Capture network logs to diagnose why action suggestions don't appear
 */

import { test, expect } from '@playwright/test';
import { saveScreenshot } from '../../helpers/artifacts';

const BASE_URL = process.env.BASE_URL || 'https://app.celeste7.ai';

test.describe('Shopping List - Network Diagnostic', () => {
  test.use({ storageState: 'test-results/.auth-states/crew-state.json' });

  test('Capture network logs for shopping list action suggestions', async ({ page }) => {
    const networkLogs: any[] = [];
    const consoleMessages: string[] = [];

    // Capture network requests
    page.on('request', request => {
      if (request.url().includes('/v1/actions')) {
        networkLogs.push({
          type: 'request',
          url: request.url(),
          method: request.method(),
          headers: request.headers(),
          timestamp: new Date().toISOString()
        });
      }
    });

    // Capture network responses
    page.on('response', async response => {
      if (response.url().includes('/v1/actions')) {
        let body;
        try {
          body = await response.json();
        } catch {
          body = await response.text();
        }

        networkLogs.push({
          type: 'response',
          url: response.url(),
          status: response.status(),
          headers: response.headers(),
          body,
          timestamp: new Date().toISOString()
        });
      }
    });

    // Capture console logs
    page.on('console', msg => {
      const text = msg.text();
      if (text.includes('useCelesteSearch') || text.includes('actionClient') || text.includes('SuggestedActions')) {
        consoleMessages.push(`[${msg.type()}] ${text}`);
      }
    });

    // 1. Navigate to root
    await page.goto(BASE_URL);
    await page.waitForTimeout(2000); // Wait for auth
    await saveScreenshot(page, 'shopping_list/diagnostic', '01_loaded');

    // 2. Type shopping list query
    const searchInput = page.locator('[data-testid="search-input"]');
    await searchInput.click();
    await searchInput.fill('add oil filter to shopping list');
    await page.waitForTimeout(2000); // Wait for debounce + request
    await saveScreenshot(page, 'shopping_list/diagnostic', '02_query_typed');

    // 3. Check if actions appeared
    const actionsVisible = await page.locator('[data-testid="suggested-actions"]').isVisible({ timeout: 1000 }).catch(() => false);

    // 4. Save diagnostic output
    console.log('\n=== NETWORK DIAGNOSTIC REPORT ===\n');
    console.log('Actions Visible:', actionsVisible);
    console.log('\nNetwork Logs:', JSON.stringify(networkLogs, null, 2));
    console.log('\nConsole Messages:', JSON.stringify(consoleMessages, null, 2));

    // 5. Write diagnostic file
    const fs = require('fs');
    const diagnosticPath = 'test-results/artifacts/shopping_list/diagnostic/network_diagnostic.json';
    fs.mkdirSync('test-results/artifacts/shopping_list/diagnostic', { recursive: true });
    fs.writeFileSync(diagnosticPath, JSON.stringify({
      actionsVisible,
      networkLogs,
      consoleMessages,
      testTime: new Date().toISOString()
    }, null, 2));

    console.log(`\nDiagnostic saved to: ${diagnosticPath}\n`);

    // This test always passes - it's for diagnostic purposes
    expect(true).toBe(true);
  });
});
