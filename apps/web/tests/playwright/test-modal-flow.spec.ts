import { test, expect } from '@playwright/test';

test('Work Order Modal Flow', async ({ page }) => {
  // 1. Go to login page
  await page.goto('https://app.celeste7.ai/login');
  await page.waitForLoadState('networkidle');
  await page.waitForTimeout(2000);
  console.log('Login page loaded');
  await page.screenshot({ path: 'test-results/00-login-page.png', fullPage: true });

  // 2. Login - find email input
  const emailInput = page.locator('input[type="email"], input[name="email"], input[placeholder*="mail"]').first();
  await emailInput.waitFor({ state: 'visible', timeout: 10000 });
  await emailInput.fill('x@alex-short.com');

  const passwordInput = page.locator('input[type="password"]').first();
  await passwordInput.fill('Password2!');

  const submitBtn = page.locator('button[type="submit"], button:has-text("Sign"), button:has-text("Log")').first();
  await submitBtn.click();
  await page.waitForTimeout(5000);
  console.log('Logged in');
  await page.screenshot({ path: 'test-results/00b-after-login.png', fullPage: true });

  // 3. Search for "generator fault"
  const searchInput = page.locator('input[placeholder*="earch"], input[type="search"], [role="searchbox"]').first();
  await searchInput.waitFor({ state: 'visible', timeout: 10000 });
  await searchInput.fill('generator fault');
  await page.keyboard.press('Enter');
  console.log('Searched for generator fault');

  // 4. Wait 10 seconds
  await page.waitForTimeout(10000);
  console.log('Waited 10 seconds');

  // Take screenshot of search results
  await page.screenshot({ path: 'test-results/01-search-results.png', fullPage: true });

  // 5. Click on work order item
  const workOrderItem = page.locator('[data-testid*="result"], [class*="result"], [class*="card"]').first();
  await workOrderItem.click();
  await page.waitForTimeout(3000);
  console.log('Clicked work order');

  // Take screenshot of work order panel
  await page.screenshot({ path: 'test-results/02-work-order-panel.png', fullPage: true });

  // 6. Find and click Add Note button
  const addNoteBtn = page.locator('button:has-text("Add Note")').first();
  if (await addNoteBtn.isVisible({ timeout: 5000 })) {
    console.log('Found Add Note button');
    await addNoteBtn.click();
    await page.waitForTimeout(2000);

    // Screenshot after clicking Add Note
    await page.screenshot({ path: 'test-results/03-after-add-note-click.png', fullPage: true });

    // Check if modal/dialog appeared
    const modal = page.locator('[role="dialog"]');
    const isModalVisible = await modal.isVisible({ timeout: 3000 }).catch(() => false);
    console.log('Modal visible:', isModalVisible);

    // Check for textarea in modal
    const textarea = page.locator('textarea');
    const isTextareaVisible = await textarea.isVisible({ timeout: 2000 }).catch(() => false);
    console.log('Textarea visible:', isTextareaVisible);

    if (isTextareaVisible) {
      // Fill in note and submit
      await textarea.fill('Test note from Playwright');
      await page.screenshot({ path: 'test-results/04-note-filled.png', fullPage: true });

      // Click submit button
      const submitBtn = page.locator('button[type="submit"], button:has-text("Add")').last();
      await submitBtn.click();
      await page.waitForTimeout(3000);
      await page.screenshot({ path: 'test-results/05-after-submit.png', fullPage: true });
      console.log('Submitted note');
    }
  } else {
    console.log('Add Note button not found');
    await page.screenshot({ path: 'test-results/03-no-add-note-btn.png', fullPage: true });
  }
});
