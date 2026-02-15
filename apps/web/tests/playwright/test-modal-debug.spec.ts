import { test, expect } from '@playwright/test';

test('Debug Modal Flow', async ({ page }) => {
  // Capture console logs and network
  const logs: string[] = [];
  const networkErrors: string[] = [];

  page.on('console', msg => {
    logs.push(`[${msg.type()}] ${msg.text()}`);
  });

  page.on('response', response => {
    if (response.status() >= 400) {
      networkErrors.push(`${response.status()} ${response.url()}`);
    }
  });

  page.on('requestfailed', request => {
    networkErrors.push(`FAILED: ${request.url()} - ${request.failure()?.errorText}`);
  });

  // Login
  await page.goto('https://app.celeste7.ai/login');
  await page.waitForTimeout(2000);

  const emailInput = page.locator('input[type="email"], input[name="email"]').first();
  await emailInput.fill('x@alex-short.com');
  await page.locator('input[type="password"]').first().fill('Password2!');
  await page.locator('button[type="submit"]').first().click();
  await page.waitForTimeout(5000);

  // Search - the placeholder is "Show recent handovers"
  const searchInput = page.locator('input[placeholder*="handover"], input[placeholder*="Search"], input[role="combobox"]').first();
  await searchInput.fill('generator fault');
  await page.keyboard.press('Enter');
  await page.waitForTimeout(10000);

  // Click work order
  const result = page.locator('[data-testid*="result"], [class*="result"], [class*="card"]').first();
  await result.click();
  await page.waitForTimeout(3000);

  // Click Add Note
  const addNoteBtn = page.locator('button:has-text("Add Note")').first();
  await addNoteBtn.click();
  await page.waitForTimeout(2000);

  // Screenshot the modal
  await page.screenshot({ path: 'test-results/debug-modal-open.png', fullPage: true });

  // Fill textarea
  const textarea = page.locator('textarea').first();
  if (await textarea.isVisible()) {
    await textarea.fill('Test note from debug test');
    await page.screenshot({ path: 'test-results/debug-modal-filled.png', fullPage: true });

    // Find and click Add Note button in modal
    const modalSubmit = page.locator('[role="dialog"] button:has-text("Add"), button:has-text("Add Note")').last();
    console.log('Clicking submit button...');
    await modalSubmit.click();

    // Wait for response
    await page.waitForTimeout(5000);
    await page.screenshot({ path: 'test-results/debug-after-submit.png', fullPage: true });
  }

  // Print logs and errors
  console.log('\n=== Console Logs ===');
  logs.filter(l => l.includes('Action') || l.includes('error') || l.includes('Error')).forEach(l => console.log(l));

  console.log('\n=== Network Errors ===');
  networkErrors.forEach(e => console.log(e));

  // Check if note appeared
  const noteText = page.locator('text=Test note from debug test');
  const noteVisible = await noteText.isVisible({ timeout: 2000 }).catch(() => false);
  console.log('\nNote visible in UI:', noteVisible);
});
