/**
 * TEST: Verify fix works locally
 * Purpose: Find out TRUTH - does the code actually work or is there a bug?
 */

import { test, expect, Page } from '@playwright/test';
import { loginAs, searchInSpotlight } from './auth.helper';

// Override baseURL to test locally
test.use({ baseURL: 'http://localhost:3000' });

test.describe('LOCAL TEST: Part Click Behavior', () => {
  test('TRUTH-TEST: What actually happens when clicking a part locally?', async ({ page }) => {
    // Capture ALL console messages
    const consoleLogs: Array<{type: string, text: string}> = [];
    const errors: string[] = [];

    page.on('console', (msg) => {
      const log = {
        type: msg.type(),
        text: msg.text()
      };
      consoleLogs.push(log);
      console.log(`[${log.type.toUpperCase()}] ${log.text}`);
    });

    page.on('pageerror', (error) => {
      const errorMsg = error.toString();
      errors.push(errorMsg);
      console.error(`[PAGE ERROR] ${errorMsg}`);
    });

    // Step 1: Login
    console.log('\n=== STEP 1: LOGIN ===');
    await loginAs(page, 'captain');
    console.log('✅ Logged in successfully');

    // Step 2: Search for part
    console.log('\n=== STEP 2: SEARCH ===');
    await searchInSpotlight(page, 'filter');
    await page.waitForTimeout(2000);

    const results = await page.locator('[data-testid="search-result-item"]').count();
    console.log(`Found ${results} search results`);

    if (results === 0) {
      console.log('❌ NO RESULTS - Cannot test click behavior');
      return;
    }

    // Step 3: Check URL before click
    console.log('\n=== STEP 3: PRE-CLICK STATE ===');
    const urlBefore = page.url();
    console.log(`URL before: ${urlBefore}`);

    // Step 4: Click first result
    console.log('\n=== STEP 4: CLICK PART ===');
    const firstResult = page.locator('[data-testid="search-result-item"]').first();
    await firstResult.click();
    await page.waitForTimeout(2000);

    // Step 5: Check what happened
    console.log('\n=== STEP 5: POST-CLICK STATE ===');
    const urlAfter = page.url();
    console.log(`URL after: ${urlAfter}`);
    console.log(`URL changed: ${urlBefore !== urlAfter}`);

    // Check for ContextPanel
    const contextPanel = page.locator('[data-testid="context-panel"]');
    const panelVisible = await contextPanel.isVisible().catch(() => false);
    console.log(`ContextPanel visible: ${panelVisible}`);

    if (panelVisible) {
      const entityType = await contextPanel.getAttribute('data-entity-type');
      console.log(`Entity type: ${entityType}`);
    }

    // Step 6: Check for errors
    console.log('\n=== STEP 6: ERROR CHECK ===');
    console.log(`Page errors captured: ${errors.length}`);
    if (errors.length > 0) {
      console.error('ERRORS FOUND:');
      errors.forEach((err, idx) => {
        console.error(`  ${idx + 1}. ${err}`);
      });
    }

    // Check console logs for relevant messages
    const relevantLogs = consoleLogs.filter(log =>
      log.text.includes('SpotlightSearch') ||
      log.text.includes('ContextPanel') ||
      log.text.includes('showContext') ||
      log.text.includes('Navigating to') ||
      log.text.includes('router')
    );

    console.log('\n=== RELEVANT CONSOLE LOGS ===');
    relevantLogs.forEach(log => {
      console.log(`[${log.type}] ${log.text}`);
    });

    // Step 7: Take screenshot
    await page.screenshot({
      path: '/tmp/LOCAL_TEST_part_click_result.png',
      fullPage: true
    });

    // Step 8: TRUTH SUMMARY
    console.log('\n=== TRUTH SUMMARY ===');
    console.log(`1. URL stayed same: ${urlBefore === urlAfter ? '✅ YES' : '❌ NO'}`);
    console.log(`2. ContextPanel opened: ${panelVisible ? '✅ YES' : '❌ NO'}`);
    console.log(`3. JavaScript errors: ${errors.length === 0 ? '✅ NONE' : `❌ ${errors.length} ERRORS`}`);
    console.log(`4. Total console logs: ${consoleLogs.length}`);

    // ASSERTIONS - What we expect
    expect(urlBefore).toBe(urlAfter); // URL should not change
    expect(errors.length).toBe(0); // No JavaScript errors
    expect(panelVisible).toBe(true); // ContextPanel should open
  });
});
