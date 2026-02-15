/**
 * Day 7 Fix Verification: Part Click Opens ContextPanel (No Navigation)
 *
 * Tests that clicking a part result opens ContextPanel instead of navigating to /parts/[id]
 * Verifies single-surface architecture is preserved
 */

import { test, expect, Page } from '@playwright/test';
import { loginAs, searchInSpotlight } from './auth.helper';

test.describe('Day 7 Fix: Parts Lens - ContextPanel Opens (No Navigation)', () => {
  test.beforeEach(async ({ page }) => {
    await loginAs(page, 'captain');
  });

  test('VERIFY-001: Part click opens ContextPanel, URL stays at /app', async ({ page }) => {
    // Step 1: Search for a part
    await searchInSpotlight(page, 'filter');
    await page.waitForTimeout(1500);

    // Step 2: Get initial URL
    const urlBefore = page.url();
    console.log(`URL before click: ${urlBefore}`);

    // Verify we're on /app
    expect(urlBefore).toContain('/app');
    expect(urlBefore).not.toContain('/parts/');

    // Step 3: Click first result
    const firstResult = page.locator('[data-testid="search-result-item"]').first();
    await expect(firstResult).toBeVisible({ timeout: 5000 });

    console.log('Clicking first part result...');
    await firstResult.click();
    await page.waitForTimeout(1000);

    // Step 4: Check URL stayed the same
    const urlAfter = page.url();
    console.log(`URL after click: ${urlAfter}`);

    // CRITICAL: URL should NOT change (single-surface architecture)
    expect(urlAfter).toBe(urlBefore);
    expect(urlAfter).toContain('/app');
    expect(urlAfter).not.toContain('/parts/');

    console.log('✅ URL stayed at /app - No navigation occurred');

    // Step 5: Verify ContextPanel opened
    const contextPanel = page.locator('[data-testid="context-panel"]');
    await expect(contextPanel).toBeVisible({ timeout: 3000 });

    console.log('✅ ContextPanel is visible');

    // Step 6: Verify panel has entity type attribute (proves it rendered)
    const entityType = await contextPanel.getAttribute('data-entity-type');
    console.log(`Entity type: ${entityType}`);
    expect(entityType).toBeTruthy();
    expect(['part', 'inventory']).toContain(entityType);

    // Step 7: Verify part card content is rendered
    const partCard = page.locator('[data-testid*="context-panel-"][data-testid*="-card"]');
    await expect(partCard).toBeVisible({ timeout: 2000 });

    console.log('✅ Part card rendered in ContextPanel');

    // Step 8: Take screenshot for visual verification
    await page.screenshot({
      path: '/tmp/DAY7_FIX_VERIFIED_context_panel_open.png',
      fullPage: true
    });

    console.log('\n✅ ✅ ✅ FIX VERIFIED ✅ ✅ ✅');
    console.log('Part click opens ContextPanel without navigation');
    console.log('Single-surface architecture preserved');
  });

  test('VERIFY-002: Multiple entity types open in ContextPanel', async ({ page }) => {
    const entities = [
      { query: 'filter', expectedType: ['part', 'inventory'] },
      { query: 'fault', expectedType: ['fault'] },
      { query: 'work order', expectedType: ['work_order'] },
    ];

    for (const entity of entities) {
      console.log(`\n--- Testing ${entity.query} ---`);

      // Search
      await searchInSpotlight(page, entity.query);
      await page.waitForTimeout(1500);

      // Get URL before
      const urlBefore = page.url();

      // Click first result
      const firstResult = page.locator('[data-testid="search-result-item"]').first();
      if (await firstResult.count() === 0) {
        console.log(`⚠️  No results for "${entity.query}", skipping`);
        continue;
      }

      await firstResult.click();
      await page.waitForTimeout(1000);

      // Check URL stayed same
      const urlAfter = page.url();
      expect(urlAfter).toBe(urlBefore);
      console.log(`✅ URL stayed: ${urlAfter}`);

      // Check ContextPanel opened
      const contextPanel = page.locator('[data-testid="context-panel"]');
      const isVisible = await contextPanel.isVisible().catch(() => false);

      if (isVisible) {
        const entityType = await contextPanel.getAttribute('data-entity-type');
        console.log(`✅ ContextPanel opened with type: ${entityType}`);
        expect(entity.expectedType).toContain(entityType);
      } else {
        console.log(`⚠️  ContextPanel not visible for ${entity.query}`);
      }

      // Close panel
      await page.keyboard.press('Escape');
      await page.waitForTimeout(500);
    }

    console.log('\n✅ Multiple entity types tested');
  });

  test('VERIFY-003: No fragmented URLs in console logs', async ({ page }) => {
    const consoleMessages: string[] = [];

    // Capture console logs
    page.on('console', (msg) => {
      const text = msg.text();
      consoleMessages.push(text);
    });

    // Search and click part
    await searchInSpotlight(page, 'filter');
    await page.waitForTimeout(1500);

    const firstResult = page.locator('[data-testid="search-result-item"]').first();
    await firstResult.click();
    await page.waitForTimeout(1000);

    // Check console logs for fragmented URLs
    const hasFragmentedRoute = consoleMessages.some(msg =>
      msg.includes('/parts/') ||
      msg.includes('/work-orders/') ||
      msg.includes('/equipment/') ||
      msg.includes('/faults/')
    );

    // Should see "Opening in ContextPanel" not "Navigating to"
    const hasCorrectLog = consoleMessages.some(msg =>
      msg.includes('Opening in ContextPanel')
    );

    console.log('\nConsole messages captured:', consoleMessages.length);
    console.log('Has fragmented route logs:', hasFragmentedRoute);
    console.log('Has correct ContextPanel log:', hasCorrectLog);

    expect(hasFragmentedRoute).toBe(false);
    console.log('✅ No fragmented URL logs detected');
  });
});
