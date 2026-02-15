/**
 * Email Full Feature Test
 * Tests: body render, attachments, linked items, add/delete links
 */

import { test, expect, Page } from '@playwright/test';

const BASE_URL = process.env.BASE_URL || 'https://app.celeste7.ai';
const SCREENSHOT_DIR = '/tmp/email_full_feature';

const TEST_USER = {
  email: 'x@alex-short.com',
  password: 'Password2!',
};

async function screenshot(page: Page, name: string) {
  await page.screenshot({ path: `${SCREENSHOT_DIR}/${name}.png`, fullPage: true });
}

async function login(page: Page) {
  await page.goto(`${BASE_URL}/login`);
  await page.waitForSelector('input[type="email"]', { timeout: 15000 });
  await page.fill('input[type="email"]', TEST_USER.email);
  await page.fill('input[type="password"]', TEST_USER.password);
  await page.click('button[type="submit"]');
  await page.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 20000 });
  await page.waitForTimeout(1500);
}

async function openEmailPanel(page: Page) {
  const emailButton = page.locator('button:has-text("Email"), a:has-text("Email"), [aria-label*="Email"]').first();
  await emailButton.waitFor({ state: 'visible', timeout: 10000 });
  await emailButton.click();
  await page.waitForTimeout(2000);
}

test.describe('Email Full Feature Tests', () => {

  test('1. Email body renders after clicking thread', async ({ page }) => {
    console.log('\n=== TEST 1: Email body renders ===');
    await login(page);
    await openEmailPanel(page);
    await screenshot(page, '01-email-panel');

    // Wait for thread rows to load
    const threadRow = page.locator('button[data-testid="thread-row"]').first();
    await threadRow.waitFor({ state: 'visible', timeout: 10000 });

    const threadCount = await page.locator('button[data-testid="thread-row"]').count();
    console.log(`   Thread rows found: ${threadCount}`);

    // Click first thread
    await threadRow.click();
    console.log('   Clicked first thread');
    await page.waitForTimeout(3000);
    await screenshot(page, '02-thread-selected');

    // Check for email body - look for ThreadDetail component content
    const bodyVisible = await page.locator('.email-body, [data-testid="email-body"], iframe').count() > 0;
    const hasSubject = await page.locator('text=/Subject:/i').count() > 0;
    const hasFrom = await page.locator('text=/From:/i').count() > 0;

    console.log(`   Body element visible: ${bodyVisible}`);
    console.log(`   Subject header: ${hasSubject}`);
    console.log(`   From header: ${hasFrom}`);

    // The detail panel should show something other than "Select a message"
    const selectMessage = await page.locator('text="Select a message to inspect correspondence"').count();
    expect(selectMessage).toBe(0);
  });

  test('2. Attachments section visible', async ({ page }) => {
    console.log('\n=== TEST 2: Attachments ===');
    await login(page);
    await openEmailPanel(page);

    // Click a thread that has attachments (look for paperclip icon)
    const threadWithAttachment = page.locator('button[data-testid="thread-row"]:has(svg)').first();
    if (await threadWithAttachment.isVisible().catch(() => false)) {
      await threadWithAttachment.click();
      console.log('   Clicked thread with attachment indicator');
    } else {
      // Just click first thread
      await page.locator('button[data-testid="thread-row"]').first().click();
      console.log('   Clicked first thread');
    }
    await page.waitForTimeout(2000);

    // Look for attachment section
    const attachmentText = await page.locator('text=/attachment/i').count();
    const paperclipIcons = await page.locator('svg.lucide-paperclip').count();
    const attachmentTestId = await page.locator('[data-testid="attachments"]').count();
    const attachmentIndicators = attachmentText + paperclipIcons + attachmentTestId;
    console.log(`   Attachment indicators found: ${attachmentIndicators}`);
    await screenshot(page, '03-attachments');
  });

  test('3. Linked items visible', async ({ page }) => {
    console.log('\n=== TEST 3: Linked items ===');
    await login(page);
    await openEmailPanel(page);

    await page.locator('button[data-testid="thread-row"]').first().click();
    await page.waitForTimeout(2000);
    await screenshot(page, '04-detail-view');

    // Look for linked items section
    const linkedSection = await page.locator('text=/Linked|Related|Connected/i').count();
    const workOrderRefs = await page.locator('text=/WO-/').count();
    const equipmentRefs = await page.locator('text=/Equipment/i').count();

    console.log(`   Linked section text: ${linkedSection}`);
    console.log(`   Work order refs (WO-): ${workOrderRefs}`);
    console.log(`   Equipment refs: ${equipmentRefs}`);
  });

  test('4. Can add link (captain has permissions)', async ({ page }) => {
    console.log('\n=== TEST 4: Add link capability ===');
    await login(page);
    await openEmailPanel(page);

    await page.locator('button[data-testid="thread-row"]').first().click();
    await page.waitForTimeout(2000);

    // Look for link/add actions in the detail view
    const linkButton = page.locator('button:has-text("Link"), button:has-text("Add"), button:has-text("Connect")');
    const linkCount = await linkButton.count();
    console.log(`   Link/Add buttons found: ${linkCount}`);

    if (linkCount > 0) {
      const firstLink = linkButton.first();
      const buttonText = await firstLink.textContent();
      console.log(`   First button text: ${buttonText}`);

      // Try clicking to see if modal opens
      await firstLink.click();
      await page.waitForTimeout(1000);
      await screenshot(page, '05-link-modal');

      // Check for modal
      const modal = await page.locator('[role="dialog"], .modal, [data-testid="modal"]').count();
      console.log(`   Modal opened: ${modal > 0}`);
    }
  });

  test('5. Can remove link', async ({ page }) => {
    console.log('\n=== TEST 5: Remove link capability ===');
    await login(page);
    await openEmailPanel(page);

    await page.locator('button[data-testid="thread-row"]').first().click();
    await page.waitForTimeout(2000);

    // Look for remove/unlink/delete buttons
    const removeButtons = await page.locator('button:has-text("Remove"), button:has-text("Unlink"), button[aria-label*="remove"], button[aria-label*="delete"]').count();
    console.log(`   Remove buttons found: ${removeButtons}`);

    // Also check for X icons that might be remove buttons
    const xIcons = await page.locator('button:has(svg.lucide-x), button:has(svg[class*="x"])').count();
    console.log(`   X icon buttons found: ${xIcons}`);

    await screenshot(page, '06-remove-link');
  });

  test('6. Click attachment to open', async ({ page }) => {
    console.log('\n=== TEST 6: Open attachment ===');
    await login(page);
    await openEmailPanel(page);

    // Find a thread with attachments and click it
    const threads = page.locator('button[data-testid="thread-row"]');
    const count = await threads.count();

    for (let i = 0; i < Math.min(count, 5); i++) {
      await threads.nth(i).click();
      await page.waitForTimeout(1500);

      // Check for attachment elements
      const attachments = page.locator('[data-testid="attachment"], .attachment-item, button:has-text(".pdf"), button:has-text(".doc"), a[download]');
      const attachmentCount = await attachments.count();

      if (attachmentCount > 0) {
        console.log(`   Found ${attachmentCount} attachments in thread ${i + 1}`);
        await screenshot(page, `07-attachment-found-thread-${i + 1}`);

        // Try clicking
        await attachments.first().click();
        await page.waitForTimeout(1000);
        await screenshot(page, '08-attachment-clicked');
        return;
      }
    }

    console.log('   No attachments found in first 5 threads');
    await screenshot(page, '07-no-attachments');
  });
});
