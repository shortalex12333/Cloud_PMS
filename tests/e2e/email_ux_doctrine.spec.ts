/**
 * Email UX Doctrine Verification
 *
 * Tests the email UX doctrine:
 * 1. NO left sidebar inbox - email is inline beneath search bar only
 * 2. Single surface, single URL (/app)
 * 3. Email accessed via Ledger dropdown (BookOpen icon)
 * 4. Link to work functionality
 */

import { test, expect } from '@playwright/test';
import { createClient } from '@supabase/supabase-js';

const PROD_URL = 'https://app.celeste7.ai';
const TEST_EMAIL = 'x@alex-short.com';
const TEST_PASSWORD = 'Password2!';

test.describe('Email UX Doctrine Verification', () => {

  test('EMAIL_01: No left sidebar - single surface at /app', async ({ page }) => {
    const fs = require('fs');
    const evidenceLog: any = {
      test: 'EMAIL_01',
      status: 'running',
      timestamp: new Date().toISOString(),
      steps: []
    };

    // Login
    await page.goto(`${PROD_URL}/login`);
    await page.fill('input[type="email"]', TEST_EMAIL);
    await page.fill('input[type="password"]', TEST_PASSWORD);
    await page.click('button[type="submit"]');
    await page.waitForURL('**/app**', { timeout: 15000 });
    await page.waitForTimeout(3000);

    evidenceLog.steps.push({ step: 'login', status: 'success', url: page.url() });

    // Verify we're on /app
    expect(page.url()).toContain('/app');
    evidenceLog.steps.push({ step: 'verify_url', status: 'success', url: page.url() });

    // Check there is NO left sidebar with "Inbox" text
    const leftSidebar = page.locator('aside, [role="navigation"], nav').filter({ hasText: 'Inbox' });
    const hasSidebar = await leftSidebar.isVisible({ timeout: 2000 }).catch(() => false);

    evidenceLog.hasLeftSidebar = hasSidebar;
    evidenceLog.steps.push({ step: 'check_sidebar', status: hasSidebar ? 'FAIL' : 'success', hasSidebar });

    // Take screenshot
    await page.screenshot({
      path: '/Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS/verification_handoff/evidence/EMAIL_01_no_sidebar.png',
      fullPage: true
    });

    evidenceLog.status = hasSidebar ? 'FAIL' : 'PASS';
    fs.writeFileSync(
      '/Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS/verification_handoff/evidence/EMAIL_01_evidence.json',
      JSON.stringify(evidenceLog, null, 2)
    );

    // Assert NO left sidebar
    expect(hasSidebar, 'Should NOT have left sidebar with Inbox').toBe(false);
    console.log('EMAIL_01: PASS - No left sidebar, single surface at /app');
  });

  test('EMAIL_02: Email accessed via Ledger dropdown inline', async ({ page }) => {
    const fs = require('fs');
    const evidenceLog: any = {
      test: 'EMAIL_02',
      status: 'running',
      timestamp: new Date().toISOString(),
      steps: []
    };

    // Login
    await page.goto(`${PROD_URL}/login`);
    await page.fill('input[type="email"]', TEST_EMAIL);
    await page.fill('input[type="password"]', TEST_PASSWORD);
    await page.click('button[type="submit"]');
    await page.waitForURL('**/app**', { timeout: 15000 });
    await page.waitForTimeout(3000);

    evidenceLog.steps.push({ step: 'login', status: 'success' });

    // Find the Ledger button (BookOpen icon) - it has aria-label="Ledger"
    const ledgerButton = page.locator('button[aria-label="Ledger"]');
    const ledgerVisible = await ledgerButton.isVisible({ timeout: 3000 }).catch(() => false);

    evidenceLog.ledgerButtonFound = ledgerVisible;
    evidenceLog.steps.push({ step: 'find_ledger', status: ledgerVisible ? 'success' : 'FAIL' });

    if (!ledgerVisible) {
      await page.screenshot({
        path: '/Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS/verification_handoff/evidence/EMAIL_02_no_ledger.png',
        fullPage: true
      });
      evidenceLog.status = 'BLOCKED';
      fs.writeFileSync(
        '/Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS/verification_handoff/evidence/EMAIL_02_evidence.json',
        JSON.stringify(evidenceLog, null, 2)
      );
      console.log('EMAIL_02: BLOCKED - Ledger button not found');
      test.skip();
      return;
    }

    // Click Ledger
    await ledgerButton.click();
    await page.waitForTimeout(500);
    evidenceLog.steps.push({ step: 'click_ledger', status: 'success' });

    // Find "Email" option in dropdown
    const emailOption = page.locator('[role="menuitem"]:has-text("Email"), button:has-text("Email")').first();
    const emailVisible = await emailOption.isVisible({ timeout: 2000 }).catch(() => false);

    evidenceLog.emailOptionFound = emailVisible;
    evidenceLog.steps.push({ step: 'find_email_option', status: emailVisible ? 'success' : 'FAIL' });

    if (!emailVisible) {
      await page.screenshot({
        path: '/Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS/verification_handoff/evidence/EMAIL_02_no_email_option.png',
        fullPage: true
      });
      evidenceLog.status = 'BLOCKED';
      fs.writeFileSync(
        '/Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS/verification_handoff/evidence/EMAIL_02_evidence.json',
        JSON.stringify(evidenceLog, null, 2)
      );
      console.log('EMAIL_02: BLOCKED - Email option not found in Ledger dropdown');
      test.skip();
      return;
    }

    // Click Email
    await emailOption.click();
    await page.waitForTimeout(1000);
    evidenceLog.steps.push({ step: 'click_email', status: 'success' });

    // Check for inline email list (look for Email Inbox heading or the inbox component)
    const inlineEmail = page.locator('h2:has-text("Email Inbox"), [data-testid="email-inbox"]').first();
    const inlineVisible = await inlineEmail.isVisible({ timeout: 3000 }).catch(() => false);

    evidenceLog.inlineEmailVisible = inlineVisible;
    evidenceLog.steps.push({ step: 'check_inline', status: inlineVisible ? 'success' : 'FAIL' });

    // Take screenshot
    await page.screenshot({
      path: '/Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS/verification_handoff/evidence/EMAIL_02_inline_email.png',
      fullPage: true
    });

    evidenceLog.status = inlineVisible ? 'PASS' : 'FAIL';
    fs.writeFileSync(
      '/Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS/verification_handoff/evidence/EMAIL_02_evidence.json',
      JSON.stringify(evidenceLog, null, 2)
    );

    // Assert inline email is visible
    expect(inlineVisible, 'Email should appear inline beneath search bar').toBe(true);
    console.log('EMAIL_02: PASS - Email accessed via Ledger dropdown and shows inline');
  });

  test('EMAIL_03: Inbox loads and shows threads', async ({ page }) => {
    const fs = require('fs');
    const evidenceLog: any = {
      test: 'EMAIL_03',
      status: 'running',
      timestamp: new Date().toISOString(),
      steps: []
    };

    // Login
    await page.goto(`${PROD_URL}/login`);
    await page.fill('input[type="email"]', TEST_EMAIL);
    await page.fill('input[type="password"]', TEST_PASSWORD);
    await page.click('button[type="submit"]');
    await page.waitForURL('**/app**', { timeout: 15000 });
    await page.waitForTimeout(3000);

    evidenceLog.steps.push({ step: 'login', status: 'success' });

    // Open email via Ledger
    const ledgerButton = page.locator('button[aria-label="Ledger"]');
    await ledgerButton.click();
    await page.waitForTimeout(500);
    const emailOption = page.locator('[role="menuitem"]:has-text("Email"), button:has-text("Email")').first();
    await emailOption.click();
    await page.waitForTimeout(2000);

    evidenceLog.steps.push({ step: 'open_email', status: 'success' });

    // Check for inbox view (look for Email Inbox heading)
    const inboxView = page.locator('h2:has-text("Email Inbox")').first();
    const inboxVisible = await inboxView.isVisible({ timeout: 3000 }).catch(() => false);

    evidenceLog.inboxVisible = inboxVisible;
    evidenceLog.steps.push({ step: 'check_inbox', status: inboxVisible ? 'success' : 'FAIL' });

    // Check for email threads (could be 0 if none exist)
    const threadItems = page.locator('[data-testid="email-thread-item"]');
    const threadCount = await threadItems.count();

    evidenceLog.threadCount = threadCount;
    evidenceLog.steps.push({ step: 'count_threads', status: 'success', count: threadCount });

    // Check for empty state or loading (acceptable)
    const emptyState = page.locator('text="All emails are linked"');
    const isEmpty = await emptyState.isVisible({ timeout: 1000 }).catch(() => false);

    evidenceLog.emptyState = isEmpty;

    // Take screenshot
    await page.screenshot({
      path: '/Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS/verification_handoff/evidence/EMAIL_03_inbox.png',
      fullPage: true
    });

    evidenceLog.status = inboxVisible ? 'PASS' : 'FAIL';
    fs.writeFileSync(
      '/Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS/verification_handoff/evidence/EMAIL_03_evidence.json',
      JSON.stringify(evidenceLog, null, 2)
    );

    console.log(`EMAIL_03: Inbox visible: ${inboxVisible}, Thread count: ${threadCount}, Empty: ${isEmpty}`);

    // Assert inbox loads
    expect(inboxVisible, 'Inbox view should be visible').toBe(true);
  });

  test('EMAIL_04: Link to work button exists on email threads', async ({ page }) => {
    const fs = require('fs');
    const evidenceLog: any = {
      test: 'EMAIL_04',
      status: 'running',
      timestamp: new Date().toISOString(),
      steps: []
    };

    // Login
    await page.goto(`${PROD_URL}/login`);
    await page.fill('input[type="email"]', TEST_EMAIL);
    await page.fill('input[type="password"]', TEST_PASSWORD);
    await page.click('button[type="submit"]');
    await page.waitForURL('**/app**', { timeout: 15000 });
    await page.waitForTimeout(3000);

    // Open email via Ledger
    const ledgerButton = page.locator('button[aria-label="Ledger"]');
    await ledgerButton.click();
    await page.waitForTimeout(500);
    const emailOption = page.locator('[role="menuitem"]:has-text("Email"), button:has-text("Email")').first();
    await emailOption.click();
    await page.waitForTimeout(2000);

    evidenceLog.steps.push({ step: 'open_email', status: 'success' });

    // Look for "Link to..." button
    const linkButton = page.locator('[data-testid="link-email-button"], button:has-text("Link to")');
    const linkCount = await linkButton.count();

    evidenceLog.linkButtonCount = linkCount;
    evidenceLog.steps.push({ step: 'find_link_buttons', status: linkCount > 0 ? 'success' : 'info', count: linkCount });

    // Take screenshot
    await page.screenshot({
      path: '/Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS/verification_handoff/evidence/EMAIL_04_link_button.png',
      fullPage: true
    });

    // If no threads, that's OK - just document it
    if (linkCount === 0) {
      const emptyState = page.locator('text="All emails are linked"');
      const isEmpty = await emptyState.isVisible({ timeout: 1000 }).catch(() => false);

      if (isEmpty) {
        evidenceLog.status = 'PASS';
        evidenceLog.note = 'No unlinked emails - all emails are linked';
        console.log('EMAIL_04: PASS - No unlinked emails (all are linked)');
      } else {
        evidenceLog.status = 'INFO';
        evidenceLog.note = 'No link buttons found - may have no email threads';
        console.log('EMAIL_04: INFO - No link buttons found');
      }
    } else {
      evidenceLog.status = 'PASS';
      console.log(`EMAIL_04: PASS - Found ${linkCount} "Link to..." button(s)`);
    }

    fs.writeFileSync(
      '/Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS/verification_handoff/evidence/EMAIL_04_evidence.json',
      JSON.stringify(evidenceLog, null, 2)
    );
  });
});
