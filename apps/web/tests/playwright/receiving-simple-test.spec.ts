/**
 * Simple receiving test - verify crash fixed and actions show
 */

import { test, expect } from '@playwright/test';
import { loginAs } from './auth.helper';

const BASE_URL = 'https://app.celeste7.ai';
// Use a receiving that already exists from earlier tests
const KNOWN_RECEIVING_ID = 'fc0e06af-9407-48a3-9ec3-41141cb7c459';

test('Receiving lens - crash fixed, endpoint works', async ({ page }) => {
  console.log('\n=== STEP 1: LOGIN ===');
  await loginAs(page, 'captain');
  await page.waitForTimeout(3000);

  console.log('\n=== STEP 2: NAVIGATE VIA DEEP LINK ===');
  const deepLinkUrl = `${BASE_URL}/?entity=receiving&id=${KNOWN_RECEIVING_ID}`;
  console.log(`Navigating to: ${deepLinkUrl}`);

  await page.goto(deepLinkUrl);
  await page.waitForTimeout(5000);

  // Verify no crash
  const errorHeading = page.locator('h2:has-text("Application error")');
  const hasError = await errorHeading.isVisible().catch(() => false);
  expect(hasError).toBe(false);
  console.log('✓ No crash - deep link works');

  console.log('\n=== STEP 3: VERIFY CONTEXT PANEL ===');
  const contextPanel = page.locator('[data-testid="context-panel"]');
  const panelVisible = await contextPanel.waitFor({ state: 'visible', timeout: 10000 }).then(() => true).catch(() => false);
  expect(panelVisible).toBe(true);
  console.log('✓ ContextPanel visible');

  console.log('\n=== STEP 4: VERIFY RECEIVING CARD ===');
  const receivingCard = contextPanel.locator('[data-testid="context-panel-receiving-card"]');
  const cardVisible = await receivingCard.waitFor({ state: 'visible', timeout: 5000 }).then(() => true).catch(() => false);
  expect(cardVisible).toBe(true);
  console.log('✓ ReceivingCard visible');

  console.log('\n=== STEP 5: CHECK FOR ACTION BUTTONS ===');
  // Check for any action buttons
  const actionButtons = receivingCard.locator('button');
  await page.waitForTimeout(2000); // Wait for actions to load

  const buttonCount = await actionButtons.count();
  console.log(`Found ${buttonCount} buttons in ReceivingCard`);

  // Get button texts
  const buttonTexts: string[] = [];
  for (let i = 0; i < Math.min(buttonCount, 15); i++) {
    try {
      const text = await actionButtons.nth(i).innerText();
      if (text && text.trim()) {
        buttonTexts.push(text.trim());
      }
    } catch (e) {
      // Skip if button disappeared
    }
  }

  console.log('\n✓ Action buttons found:');
  buttonTexts.forEach(text => console.log(`  - ${text}`));

  // Take screenshot for evidence
  await page.screenshot({ path: '/tmp/receiving-working.png', fullPage: true });

  // Expect at least some buttons (we know it should have actions)
  expect(buttonCount).toBeGreaterThan(0);
  console.log('\n✅ TEST PASSED - Receiving lens working!');
});
