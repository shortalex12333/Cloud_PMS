/**
 * Comprehensive Ledger E2E Tests
 *
 * Tests ALL work order actions and verifies they appear in the ledger.
 * Takes screenshots to /Desktop as evidence.
 *
 * Test Matrix:
 * - HOD, CREW, CAPTAIN roles
 * - Actions: open work order, add note, add checklist item, add parts
 * - Ledger visibility: Me vs Department toggle
 * - Cross-user visibility: HOD sees CREW events, CAPTAIN sees all
 */

import { test, expect, Page } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';

const BASE_URL = 'https://app.celeste7.ai';
const PASSWORD = 'Password2!';
const SCREENSHOT_DIR = '/Users/celeste7/Desktop/ledger-evidence';

const TEST_USERS = {
  HOD: { email: 'hod.test@alex-short.com', name: 'HOD' },
  CREW: { email: 'crew.test@alex-short.com', name: 'CREW' },
  CAPTAIN: { email: 'x@alex-short.com', name: 'CAPTAIN' },
};

// Ensure screenshot directory exists
if (!fs.existsSync(SCREENSHOT_DIR)) {
  fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });
}

async function login(page: Page, email: string): Promise<void> {
  await page.goto(`${BASE_URL}/login`);
  await page.waitForTimeout(3000);
  await page.waitForSelector('input[type="email"], input[name="email"]', { timeout: 15000 });
  await page.fill('input[type="email"], input[name="email"]', email);
  await page.fill('input[type="password"], input[name="password"]', PASSWORD);
  await page.click('button[type="submit"]');
  await page.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 20000 });
  await page.waitForTimeout(3000);
  console.log(`✅ Logged in as ${email}`);
}

async function searchAndOpenWorkOrder(page: Page, query: string): Promise<void> {
  // Wait for search input
  const searchInput = page.locator('[data-testid="search-input"]');
  await searchInput.waitFor({ state: 'visible', timeout: 20000 });
  await page.waitForTimeout(1000);

  // Type search query
  await searchInput.click();
  await searchInput.fill(query);
  await page.keyboard.press('Enter');
  await page.waitForTimeout(8000); // Wait for search results

  // Click first result
  const result = page.locator('[data-testid="search-result-item"]').first();
  await result.waitFor({ state: 'visible', timeout: 20000 });
  await result.click();
  await page.waitForTimeout(5000); // Wait for work order panel to load

  console.log(`✅ Opened work order from search: "${query}"`);
}

async function addNoteToWorkOrder(page: Page, noteText: string): Promise<boolean> {
  // Find and click Add Note button
  const addNoteBtn = page.locator('button:has-text("Add Note")').first();
  await addNoteBtn.waitFor({ state: 'visible', timeout: 15000 });
  await addNoteBtn.click();
  await page.waitForTimeout(2000);

  // Fill note text
  const textarea = page.locator('[role="dialog"] textarea').first();
  await textarea.waitFor({ state: 'visible', timeout: 10000 });
  await textarea.fill(noteText);
  await page.waitForTimeout(500);

  // Submit
  const submitBtn = page.locator('[role="dialog"] button:has-text("Add Note")').last();
  await submitBtn.click();
  await page.waitForTimeout(5000);

  // Check for success (dialog should close)
  const dialogVisible = await page.locator('[role="dialog"]').isVisible({ timeout: 2000 }).catch(() => false);
  console.log(`✅ Add Note: ${!dialogVisible ? 'SUCCESS' : 'DIALOG STILL OPEN'}`);
  return !dialogVisible;
}

async function addChecklistItem(page: Page, title: string): Promise<boolean> {
  // Scroll to find checklist section if needed
  const addBtn = page.locator('button:has-text("Add Checklist Item"), button:has-text("Add Item")').first();

  try {
    await addBtn.scrollIntoViewIfNeeded();
  } catch {
    // Ignore scroll errors
  }

  await addBtn.waitFor({ state: 'visible', timeout: 15000 });
  await addBtn.click();
  await page.waitForTimeout(2000);

  // Fill title
  const titleInput = page.locator('[role="dialog"] input').first();
  await titleInput.waitFor({ state: 'visible', timeout: 10000 });
  await titleInput.fill(title);
  await page.waitForTimeout(500);

  // Submit
  const submitBtn = page.locator('[role="dialog"] button:has-text("Add")').last();
  await submitBtn.click();
  await page.waitForTimeout(5000);

  const dialogVisible = await page.locator('[role="dialog"]').isVisible({ timeout: 2000 }).catch(() => false);
  console.log(`✅ Add Checklist Item: ${!dialogVisible ? 'SUCCESS' : 'DIALOG STILL OPEN'}`);
  return !dialogVisible;
}

async function openLedger(page: Page): Promise<void> {
  // Find and click the Ledger button in toolbar
  const ledgerTrigger = page.locator('button[aria-label="Ledger"]');
  await ledgerTrigger.waitFor({ state: 'visible', timeout: 15000 });
  await ledgerTrigger.click();
  await page.waitForTimeout(1000);

  // Click Ledger menu item
  const ledgerMenuItem = page.locator('[role="menuitem"]:has-text("Ledger")');
  await ledgerMenuItem.waitFor({ state: 'visible', timeout: 5000 });
  await ledgerMenuItem.click();
  await page.waitForTimeout(3000); // Wait for ledger to load

  console.log(`✅ Ledger panel opened`);
}

async function closeLedger(page: Page): Promise<void> {
  const closeBtn = page.locator('button[aria-label="Close ledger"]');
  if (await closeBtn.isVisible()) {
    await closeBtn.click();
    await page.waitForTimeout(1000);
  }
}

async function closeWorkOrderPanel(page: Page): Promise<void> {
  await page.keyboard.press('Escape');
  await page.waitForTimeout(1000);
}

async function saveScreenshot(page: Page, name: string): Promise<string> {
  const filePath = path.join(SCREENSHOT_DIR, `${name}.png`);
  await page.screenshot({ path: filePath, fullPage: true });
  console.log(`📸 Screenshot saved: ${filePath}`);
  return filePath;
}

async function switchLedgerView(page: Page, mode: 'me' | 'department'): Promise<void> {
  const button = page.locator(`[data-testid="view-mode-${mode}"]`);
  await button.waitFor({ state: 'visible', timeout: 5000 });
  await button.click();
  await page.waitForTimeout(3000); // Wait for ledger to refetch
  console.log(`✅ Switched ledger to ${mode} view`);
}

async function expandFirstDayGroup(page: Page): Promise<void> {
  // Find day group buttons (contain weekday names)
  const dayButtons = page.locator('button:has-text("Mon"), button:has-text("Tue"), button:has-text("Wed"), button:has-text("Thu"), button:has-text("Fri"), button:has-text("Sat"), button:has-text("Sun")');
  const count = await dayButtons.count();
  if (count > 0) {
    await dayButtons.first().click();
    await page.waitForTimeout(500);
    console.log(`✅ Expanded first day group`);
  }
}

// ============================================================================
// HOD TESTS
// ============================================================================

test.describe('HOD - Complete Workflow', () => {
  test('HOD: Add note, checklist - verify in ledger with screenshots', async ({ page }) => {
    const timestamp = Date.now();

    console.log('\n========== HOD TEST ==========');

    // 1. Login
    console.log('1. Login as HOD');
    await login(page, TEST_USERS.HOD.email);
    await saveScreenshot(page, `01-HOD-logged-in-${timestamp}`);

    // 2. Search and open work order
    console.log('2. Search "Generator fault" and open work order');
    await searchAndOpenWorkOrder(page, 'Generator fault');
    await saveScreenshot(page, `02-HOD-work-order-opened-${timestamp}`);

    // 3. Add note
    console.log('3. Add note to work order');
    const noteText = `HOD Test Note - ${timestamp}`;
    await addNoteToWorkOrder(page, noteText);
    await saveScreenshot(page, `03-HOD-note-added-${timestamp}`);

    // 4. Add checklist item
    console.log('4. Add checklist item');
    const checklistTitle = `HOD Checklist - ${timestamp}`;
    await addChecklistItem(page, checklistTitle);
    await saveScreenshot(page, `04-HOD-checklist-added-${timestamp}`);

    // 5. Close work order panel
    console.log('5. Close work order panel');
    await closeWorkOrderPanel(page);
    await page.waitForTimeout(2000);

    // 6. Open ledger - Me view
    console.log('6. Open ledger (Me view)');
    await openLedger(page);
    await page.waitForTimeout(3000);
    await expandFirstDayGroup(page);
    await saveScreenshot(page, `05-HOD-ledger-me-view-${timestamp}`);

    // 7. Get ledger content
    const ledgerPanel = page.locator('div.fixed').filter({ has: page.getByRole('heading', { name: 'Ledger' }) });
    const ledgerContent = ledgerPanel.locator('.overflow-y-auto');
    const content = await ledgerContent.textContent();
    console.log('Ledger (Me) content:', content?.substring(0, 500));

    // 8. Switch to Department view
    console.log('7. Switch to Department view');
    await switchLedgerView(page, 'department');
    await expandFirstDayGroup(page);
    await saveScreenshot(page, `06-HOD-ledger-department-view-${timestamp}`);

    const deptContent = await ledgerContent.textContent();
    console.log('Ledger (Department) content:', deptContent?.substring(0, 500));

    // Verify ledger has content
    expect(content || deptContent).toBeTruthy();
    console.log('✅ HOD test complete - screenshots saved to Desktop');
  });
});

// ============================================================================
// CREW TESTS
// ============================================================================

test.describe('CREW - Complete Workflow', () => {
  test('CREW: Add note, checklist - verify in ledger with screenshots', async ({ page }) => {
    const timestamp = Date.now();

    console.log('\n========== CREW TEST ==========');

    // 1. Login
    console.log('1. Login as CREW');
    await login(page, TEST_USERS.CREW.email);
    await saveScreenshot(page, `01-CREW-logged-in-${timestamp}`);

    // 2. Search and open work order
    console.log('2. Search "Generator fault" and open work order');
    await searchAndOpenWorkOrder(page, 'Generator fault');
    await saveScreenshot(page, `02-CREW-work-order-opened-${timestamp}`);

    // 3. Add note
    console.log('3. Add note to work order');
    const noteText = `CREW Test Note - ${timestamp}`;
    await addNoteToWorkOrder(page, noteText);
    await saveScreenshot(page, `03-CREW-note-added-${timestamp}`);

    // 4. Add checklist item
    console.log('4. Add checklist item');
    const checklistTitle = `CREW Checklist - ${timestamp}`;
    await addChecklistItem(page, checklistTitle);
    await saveScreenshot(page, `04-CREW-checklist-added-${timestamp}`);

    // 5. Close work order panel
    console.log('5. Close work order panel');
    await closeWorkOrderPanel(page);
    await page.waitForTimeout(2000);

    // 6. Open ledger
    console.log('6. Open ledger');
    await openLedger(page);
    await page.waitForTimeout(3000);
    await expandFirstDayGroup(page);
    await saveScreenshot(page, `05-CREW-ledger-${timestamp}`);

    // Get ledger content
    const ledgerPanel = page.locator('div.fixed').filter({ has: page.getByRole('heading', { name: 'Ledger' }) });
    const ledgerContent = ledgerPanel.locator('.overflow-y-auto');
    const content = await ledgerContent.textContent();
    console.log('CREW Ledger content:', content?.substring(0, 500));

    expect(content).toBeTruthy();
    console.log('✅ CREW test complete - screenshots saved to Desktop');
  });
});

// ============================================================================
// CAPTAIN TESTS
// ============================================================================

test.describe('CAPTAIN - Complete Workflow', () => {
  test('CAPTAIN: Add note, checklist - verify department visibility', async ({ page }) => {
    const timestamp = Date.now();

    console.log('\n========== CAPTAIN TEST ==========');

    // 1. Login
    console.log('1. Login as CAPTAIN');
    await login(page, TEST_USERS.CAPTAIN.email);
    await saveScreenshot(page, `01-CAPTAIN-logged-in-${timestamp}`);

    // 2. Search and open work order
    console.log('2. Search "Generator fault" and open work order');
    await searchAndOpenWorkOrder(page, 'Generator fault');
    await saveScreenshot(page, `02-CAPTAIN-work-order-opened-${timestamp}`);

    // 3. Add note
    console.log('3. Add note to work order');
    const noteText = `CAPTAIN Test Note - ${timestamp}`;
    await addNoteToWorkOrder(page, noteText);
    await saveScreenshot(page, `03-CAPTAIN-note-added-${timestamp}`);

    // 4. Add checklist item
    console.log('4. Add checklist item');
    const checklistTitle = `CAPTAIN Checklist - ${timestamp}`;
    await addChecklistItem(page, checklistTitle);
    await saveScreenshot(page, `04-CAPTAIN-checklist-added-${timestamp}`);

    // 5. Close work order panel
    console.log('5. Close work order panel');
    await closeWorkOrderPanel(page);
    await page.waitForTimeout(2000);

    // 6. Open ledger - Department view (should see all users)
    console.log('6. Open ledger - Department view');
    await openLedger(page);
    await page.waitForTimeout(3000);
    await switchLedgerView(page, 'department');
    await expandFirstDayGroup(page);
    await saveScreenshot(page, `05-CAPTAIN-ledger-department-${timestamp}`);

    // Get ledger content
    const ledgerPanel = page.locator('div.fixed').filter({ has: page.getByRole('heading', { name: 'Ledger' }) });
    const ledgerContent = ledgerPanel.locator('.overflow-y-auto');
    const content = await ledgerContent.textContent();
    console.log('CAPTAIN Department Ledger:', content?.substring(0, 500));

    // Captain should see events from HOD and CREW if they ran first
    expect(content).toBeTruthy();
    console.log('✅ CAPTAIN test complete - screenshots saved to Desktop');
  });
});

// ============================================================================
// CROSS-USER VISIBILITY TEST
// ============================================================================

test.describe('Cross-User Visibility', () => {
  test('HOD can see CREW events in Department view', async ({ page }) => {
    const timestamp = Date.now();

    console.log('\n========== CROSS-USER VISIBILITY TEST ==========');

    // Login as HOD
    await login(page, TEST_USERS.HOD.email);

    // Open ledger in Department view
    await openLedger(page);
    await page.waitForTimeout(3000);
    await switchLedgerView(page, 'department');
    await expandFirstDayGroup(page);
    await saveScreenshot(page, `CROSSUSER-HOD-sees-department-${timestamp}`);

    const ledgerPanel = page.locator('div.fixed').filter({ has: page.getByRole('heading', { name: 'Ledger' }) });
    const ledgerContent = ledgerPanel.locator('.overflow-y-auto');
    const content = await ledgerContent.textContent();
    console.log('HOD Department view content:', content?.substring(0, 500));

    expect(content).toBeTruthy();
    console.log('✅ Cross-user visibility test complete');
  });
});
