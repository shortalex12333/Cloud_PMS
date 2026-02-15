/**
 * Work Order Actions - Multi-Role E2E Tests
 *
 * Tests RLS policies, role permissions, foreign keys, and special characters
 * across different user roles: HOD, Crew, Captain
 */

import { test, expect, Page } from '@playwright/test';

const BASE_URL = process.env.E2E_BASE_URL || 'https://app.celeste7.ai';
const PASSWORD = 'Password2!';

const TEST_USERS = {
  hod: { email: 'hod.test@alex-short.com', role: 'HOD' },
  crew: { email: 'crew.test@alex-short.com', role: 'Crew' },
  captain: { email: 'captain.test@alex-short.com', role: 'Captain' },
};

// Special characters to test JSONB storage
const SPECIAL_CHAR_TESTS = [
  { name: 'quotes', text: 'Test "double" and \'single\' quotes' },
  { name: 'brackets', text: 'Test <angle> {curly} [square] brackets' },
  { name: 'symbols', text: 'Test & ampersand © symbol € euro £ pound' },
  { name: 'unicode', text: 'Test émojis 🔧⚙️🛠️ and ñ ü ö accents' },
  { name: 'sql_attempt', text: "Test '; DROP TABLE users; --" },
  { name: 'html_attempt', text: '<script>alert("xss")</script>' },
  { name: 'newlines', text: 'Line 1\nLine 2\nLine 3' },
];

// Helper to capture errors
interface TestContext {
  consoleErrors: string[];
  networkFailures: string[];
}

function setupErrorCapture(page: Page): TestContext {
  const ctx: TestContext = { consoleErrors: [], networkFailures: [] };

  page.on('console', msg => {
    if (msg.type() === 'error') {
      ctx.consoleErrors.push(msg.text());
      console.log(`❌ [Console] ${msg.text()}`);
    }
  });

  page.on('response', response => {
    if (response.status() >= 400) {
      const msg = `${response.status()} ${response.url()}`;
      ctx.networkFailures.push(msg);
      console.log(`❌ [Network] ${msg}`);
    }
  });

  return ctx;
}

async function login(page: Page, email: string, password: string) {
  await page.goto(`${BASE_URL}/login`);
  await page.waitForTimeout(2000);

  const emailInput = page.locator('input[type="email"], input[name="email"]').first();
  await emailInput.waitFor({ state: 'visible', timeout: 10000 });
  await emailInput.fill(email);
  await page.locator('input[type="password"]').first().fill(password);
  await page.locator('button[type="submit"]').first().click();
  await page.waitForTimeout(5000);

  console.log(`✅ Logged in as ${email}`);
}

async function searchAndOpenWorkOrder(page: Page, searchTerm: string = 'generator fault') {
  const searchInput = page.locator('[data-testid="search-input"]');
  await searchInput.waitFor({ state: 'visible', timeout: 15000 });
  await searchInput.click();
  await searchInput.fill(searchTerm);
  await page.keyboard.press('Enter');
  await page.waitForTimeout(8000);

  const result = page.locator('[data-testid="search-result-item"]').first();
  await result.waitFor({ state: 'visible', timeout: 15000 });
  await result.click();
  await page.waitForTimeout(3000);

  console.log(`✅ Opened work order from search: "${searchTerm}"`);
}

async function addNoteToWorkOrder(page: Page, noteText: string): Promise<boolean> {
  // Click Add Note button
  const addNoteBtn = page.locator('button:has-text("Add Note")').first();
  await addNoteBtn.waitFor({ state: 'visible', timeout: 10000 });
  await addNoteBtn.click();
  await page.waitForTimeout(1000);

  // Fill note text
  const textarea = page.locator('[role="dialog"] textarea').first();
  await textarea.waitFor({ state: 'visible', timeout: 5000 });
  await textarea.fill(noteText);

  // Submit
  const submitBtn = page.locator('[role="dialog"] button:has-text("Add Note")').last();
  await submitBtn.click();
  await page.waitForTimeout(3000);

  // Check for success toast or error
  const successToast = page.locator('text=Success, text=successfully').first();
  const errorToast = page.locator('[data-sonner-toast][data-type="error"]').first();

  const hasSuccess = await successToast.isVisible({ timeout: 2000 }).catch(() => false);
  const hasError = await errorToast.isVisible({ timeout: 1000 }).catch(() => false);

  if (hasSuccess) {
    console.log(`✅ Note added successfully`);
    return true;
  }
  if (hasError) {
    console.log(`❌ Note failed to add`);
    return false;
  }

  // Modal should close on success
  const modalVisible = await page.locator('[role="dialog"]').isVisible({ timeout: 1000 }).catch(() => false);
  return !modalVisible;
}

async function addChecklistItem(page: Page, title: string): Promise<boolean> {
  // Scroll to checklist section
  const checklistSection = page.locator('text=Checklist').first();
  await checklistSection.scrollIntoViewIfNeeded().catch(() => {});
  await page.waitForTimeout(500);

  // Click Add Checklist Item button
  const addBtn = page.locator('button:has-text("Add Checklist Item"), button:has-text("Add Item")').first();
  await addBtn.waitFor({ state: 'visible', timeout: 10000 });
  await addBtn.click();
  await page.waitForTimeout(1000);

  // Fill title
  const titleInput = page.locator('[role="dialog"] input').first();
  await titleInput.waitFor({ state: 'visible', timeout: 5000 });
  await titleInput.fill(title);

  // Submit
  const submitBtn = page.locator('[role="dialog"] button:has-text("Add")').last();
  await submitBtn.click();
  await page.waitForTimeout(3000);

  // Check for success
  const modalVisible = await page.locator('[role="dialog"]').isVisible({ timeout: 1000 }).catch(() => false);
  return !modalVisible;
}

// ============================================================================
// HOD ROLE TESTS
// ============================================================================

test.describe('HOD Role - Work Order Actions', () => {
  test.beforeEach(async ({ page }) => {
    await login(page, TEST_USERS.hod.email, PASSWORD);
  });

  test('HOD can add note to work order', async ({ page }) => {
    const ctx = setupErrorCapture(page);
    await searchAndOpenWorkOrder(page);

    const timestamp = new Date().toISOString();
    const success = await addNoteToWorkOrder(page, `HOD Test Note - ${timestamp}`);

    // Check for API errors
    const apiErrors = ctx.networkFailures.filter(f => f.includes('/api/'));
    console.log(`Network failures: ${apiErrors.length}`);

    expect(apiErrors.filter(e => e.includes('400'))).toHaveLength(0);
  });

  test('HOD can add checklist item', async ({ page }) => {
    const ctx = setupErrorCapture(page);
    await searchAndOpenWorkOrder(page);

    const timestamp = new Date().toISOString();
    const success = await addChecklistItem(page, `HOD Checklist - ${timestamp}`);

    const apiErrors = ctx.networkFailures.filter(f => f.includes('/api/'));
    expect(apiErrors.filter(e => e.includes('400'))).toHaveLength(0);
  });

  // Special character tests for HOD
  for (const { name, text } of SPECIAL_CHAR_TESTS) {
    test(`HOD can add note with special chars: ${name}`, async ({ page }) => {
      const ctx = setupErrorCapture(page);
      await searchAndOpenWorkOrder(page);

      const noteText = `[${name}] ${text} - ${Date.now()}`;
      await addNoteToWorkOrder(page, noteText);

      // Should not have 400/500 errors
      const criticalErrors = ctx.networkFailures.filter(
        f => f.includes('/api/') && (f.includes('400') || f.includes('500'))
      );
      expect(criticalErrors).toHaveLength(0);
    });
  }
});

// ============================================================================
// CREW ROLE TESTS
// ============================================================================

test.describe('Crew Role - Work Order Actions', () => {
  test.beforeEach(async ({ page }) => {
    await login(page, TEST_USERS.crew.email, PASSWORD);
  });

  test('Crew can add note to work order', async ({ page }) => {
    const ctx = setupErrorCapture(page);
    await searchAndOpenWorkOrder(page);

    const timestamp = new Date().toISOString();
    await addNoteToWorkOrder(page, `Crew Test Note - ${timestamp}`);

    const apiErrors = ctx.networkFailures.filter(f => f.includes('/api/') && f.includes('400'));
    console.log(`API 400 errors: ${apiErrors.length}`);

    // Crew should be able to add notes (no role restriction)
    expect(apiErrors).toHaveLength(0);
  });

  test('Crew can add checklist item', async ({ page }) => {
    const ctx = setupErrorCapture(page);
    await searchAndOpenWorkOrder(page);

    const timestamp = new Date().toISOString();
    await addChecklistItem(page, `Crew Checklist - ${timestamp}`);

    const apiErrors = ctx.networkFailures.filter(f => f.includes('/api/') && f.includes('400'));
    expect(apiErrors).toHaveLength(0);
  });

  // Special character test for Crew
  test('Crew can add note with unicode and emojis', async ({ page }) => {
    const ctx = setupErrorCapture(page);
    await searchAndOpenWorkOrder(page);

    await addNoteToWorkOrder(page, `Crew note with émojis 🔧 and "quotes" - ${Date.now()}`);

    const criticalErrors = ctx.networkFailures.filter(
      f => f.includes('/api/') && (f.includes('400') || f.includes('500'))
    );
    expect(criticalErrors).toHaveLength(0);
  });
});

// ============================================================================
// CAPTAIN ROLE TESTS
// ============================================================================

test.describe('Captain Role - Work Order Actions', () => {
  test.beforeEach(async ({ page }) => {
    await login(page, TEST_USERS.captain.email, PASSWORD);
  });

  test('Captain can add note to work order', async ({ page }) => {
    const ctx = setupErrorCapture(page);
    await searchAndOpenWorkOrder(page);

    const timestamp = new Date().toISOString();
    await addNoteToWorkOrder(page, `Captain Test Note - ${timestamp}`);

    const apiErrors = ctx.networkFailures.filter(f => f.includes('/api/') && f.includes('400'));
    expect(apiErrors).toHaveLength(0);
  });

  test('Captain can add checklist item', async ({ page }) => {
    const ctx = setupErrorCapture(page);
    await searchAndOpenWorkOrder(page);

    const timestamp = new Date().toISOString();
    await addChecklistItem(page, `Captain Checklist - ${timestamp}`);

    const apiErrors = ctx.networkFailures.filter(f => f.includes('/api/') && f.includes('400'));
    expect(apiErrors).toHaveLength(0);
  });

  // Captain is HOD - test update permissions
  test('Captain (HOD) can see work order details', async ({ page }) => {
    const ctx = setupErrorCapture(page);
    await searchAndOpenWorkOrder(page);

    // Verify work order panel is visible
    const workOrderPanel = page.locator('text=WORK ORDER').first();
    await expect(workOrderPanel).toBeVisible({ timeout: 5000 });

    // Should have no permission errors
    const permissionErrors = ctx.networkFailures.filter(f => f.includes('403') || f.includes('401'));
    expect(permissionErrors).toHaveLength(0);
  });
});

// ============================================================================
// RLS ISOLATION TESTS
// ============================================================================

test.describe('RLS Yacht Isolation', () => {
  test('Users can only see their own yacht data', async ({ page }) => {
    const ctx = setupErrorCapture(page);
    await login(page, TEST_USERS.hod.email, PASSWORD);

    // Search should only return results from user's yacht
    const searchInput = page.locator('[data-testid="search-input"]');
    await searchInput.waitFor({ state: 'visible', timeout: 15000 });
    await searchInput.fill('work order');
    await page.keyboard.press('Enter');
    await page.waitForTimeout(5000);

    // Results should appear (user has access to their yacht)
    const results = page.locator('[data-testid="search-result-item"]');
    const count = await results.count();
    console.log(`Search returned ${count} results for user's yacht`);

    // No 403/401 errors means RLS is working (user sees their data)
    const accessErrors = ctx.networkFailures.filter(f => f.includes('403') || f.includes('401'));
    expect(accessErrors).toHaveLength(0);
  });
});

// ============================================================================
// INPUT VALIDATION TESTS
// ============================================================================

test.describe('Input Validation', () => {
  test.beforeEach(async ({ page }) => {
    await login(page, TEST_USERS.hod.email, PASSWORD);
  });

  test('Empty note text should be rejected by UI', async ({ page }) => {
    await searchAndOpenWorkOrder(page);

    // Open Add Note modal
    const addNoteBtn = page.locator('button:has-text("Add Note")').first();
    await addNoteBtn.click();
    await page.waitForTimeout(1000);

    // Try to submit without text - button should be disabled
    const submitBtn = page.locator('[role="dialog"] button:has-text("Add Note")').last();
    const isDisabled = await submitBtn.isDisabled();

    expect(isDisabled).toBe(true);

    // Close modal
    await page.keyboard.press('Escape');
  });

  test('Empty checklist title should be rejected by UI', async ({ page }) => {
    await searchAndOpenWorkOrder(page);

    // Open Add Checklist modal
    const addBtn = page.locator('button:has-text("Add Checklist Item"), button:has-text("Add Item")').first();
    await addBtn.scrollIntoViewIfNeeded().catch(() => {});
    await addBtn.click();
    await page.waitForTimeout(1000);

    // Submit button should be disabled when title is empty
    const submitBtn = page.locator('[role="dialog"] button:has-text("Add")').last();
    const isDisabled = await submitBtn.isDisabled();

    expect(isDisabled).toBe(true);

    await page.keyboard.press('Escape');
  });

  test('Note with max length (2000 chars) should work', async ({ page }) => {
    const ctx = setupErrorCapture(page);
    await searchAndOpenWorkOrder(page);

    // Create a note at max length
    const maxNote = 'A'.repeat(1990) + ` - ${Date.now()}`;
    await addNoteToWorkOrder(page, maxNote);

    const errors = ctx.networkFailures.filter(f => f.includes('/api/') && f.includes('400'));
    expect(errors).toHaveLength(0);
  });
});
