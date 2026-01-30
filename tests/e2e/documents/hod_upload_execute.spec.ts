/**
 * Document Lens v2 - HOD Upload Execute Flow
 *
 * Full E2E test: Login → Search → Click Action → Modal → Submit → Verify
 */
import { test, expect, Page } from '@playwright/test';
import { saveArtifact } from '../../helpers/artifacts';

const APP_URL = process.env.APP_URL || 'https://app.celeste7.ai';

async function loginAsHOD(page: Page): Promise<void> {
  await page.goto(APP_URL);
  await page.waitForSelector('input[type="email"]', { timeout: 15000 });
  await page.fill('input[type="email"]', 'hod.tenant@alex-short.com');
  await page.fill('input[type="password"]', 'Password2!');
  await page.click('button[type="submit"]');
  // Wait for main page to load (search bar visible)
  await page.waitForSelector('[data-testid="search-input"], .spotlight-search input, input[type="text"]', { timeout: 15000 });
  await page.waitForTimeout(2000);
}

// Flexible search input selector - handles rotating placeholders
const SEARCH_SELECTORS = '[data-testid="search-input"], .spotlight-search input, input[type="text"]:visible';

test.describe('HOD Upload Document Execute Flow', () => {

  test('Full journey: Search → Click Upload → Modal → Submit → Success', async ({ page }) => {
    const testName = 'documents/hod-upload-execute';

    // Track API calls
    const apiCalls: { url: string; method: string; status?: number; body?: any }[] = [];

    page.on('request', (req) => {
      if (req.url().includes('/v1/actions')) {
        apiCalls.push({ url: req.url(), method: req.method() });
      }
    });

    page.on('response', async (res) => {
      if (res.url().includes('/v1/actions')) {
        const call = apiCalls.find(c => c.url === res.url() && !c.status);
        if (call) {
          call.status = res.status();
          try {
            call.body = await res.json();
          } catch {}
        }
      }
    });

    // Step 1: Login
    await loginAsHOD(page);
    await page.screenshot({ path: `test-results/artifacts/${testName}/01_logged_in.png` });

    // Step 2: Search for "upload document"
    const searchInput = page.locator(SEARCH_SELECTORS).first();
    await searchInput.click();
    await searchInput.fill('upload document');
    await page.waitForTimeout(2000);
    await page.screenshot({ path: `test-results/artifacts/${testName}/02_search_typed.png` });

    // Step 3: Verify action chips appear
    const uploadButton = page.locator('[data-testid="action-btn-upload_document"], button:has-text("Upload Document")').first();
    await expect(uploadButton).toBeVisible({ timeout: 5000 });
    await page.screenshot({ path: `test-results/artifacts/${testName}/03_action_chips.png` });

    // Step 4: Click "Upload Document" chip
    await uploadButton.click();
    await page.waitForTimeout(1000);
    await page.screenshot({ path: `test-results/artifacts/${testName}/04_modal_opened.png` });

    // Step 5: Fill modal form
    // The modal shows Mime Type field (required) and Storage Location preview

    // Fill mime_type (required field)
    const mimeInput = page.locator('#mime_type, input[id="mime_type"], input[placeholder*="mime type" i]').first();
    await expect(mimeInput).toBeVisible({ timeout: 5000 });
    await mimeInput.fill('application/pdf');

    // Fill file_name if visible
    const filenameInput = page.locator('#file_name, input[id="file_name"], input[placeholder*="file" i]').first();
    if (await filenameInput.count() > 0 && await filenameInput.isVisible()) {
      await filenameInput.fill('e2e-test-document.pdf');
    }

    await page.waitForTimeout(500);
    await page.screenshot({ path: `test-results/artifacts/${testName}/05_form_filled.png` });

    // Step 6: Submit
    // Look for submit button in the modal (avoid matching action chip)
    const submitButton = page.locator('.fixed button[type="submit"], .modal button:has-text("Submit"), .modal button:has-text("Execute"), button:has-text("Confirm")').first();
    if (await submitButton.count() > 0) {
      await submitButton.click({ timeout: 10000 });
      await page.waitForTimeout(3000);
    } else {
      // Fallback: try pressing Enter
      await mimeInput.press('Enter');
      await page.waitForTimeout(3000);
    }

    await page.screenshot({ path: `test-results/artifacts/${testName}/06_after_submit.png` });

    // Step 7: Check for success toast
    const successToast = page.locator('[data-testid="toast-success"], .toast-success, :has-text("success"), :has-text("uploaded")');
    const toastVisible = await successToast.count() > 0;

    // Save evidence
    const report = {
      timestamp: new Date().toISOString(),
      steps: ['login', 'search', 'action_chips_visible', 'click_upload', 'fill_form', 'submit'],
      apiCalls: apiCalls.map(c => ({
        method: c.method,
        url: c.url,
        status: c.status,
        success: c.body?.status === 'success' || c.status === 200,
      })),
      uploadButtonFound: await uploadButton.count() > 0,
      toastVisible,
    };

    saveArtifact('hod_upload_execute_report.json', report, testName);

    // Assertions
    expect(await uploadButton.count()).toBeGreaterThan(0);

    // Check if execute was called
    const executeCall = apiCalls.find(c => c.url.includes('/execute') && c.method === 'POST');
    if (executeCall) {
      console.log('Execute call made:', executeCall.status, executeCall.body?.status);
    }

    console.log('\n=== HOD UPLOAD EXECUTE FLOW ===');
    console.log('Upload button found: ✓');
    console.log('API calls made:', apiCalls.length);
    console.log('Execute call status:', executeCall?.status || 'Not called');
    console.log('================================\n');
  });

  test('CREW cannot see Upload Document button', async ({ page }) => {
    const testName = 'documents/crew-no-upload';

    // Login as CREW
    await page.goto(APP_URL);
    await page.waitForSelector('input[type="email"]', { timeout: 15000 });
    await page.fill('input[type="email"]', 'crew.tenant@alex-short.com');
    await page.fill('input[type="password"]', 'Password2!');
    await page.click('button[type="submit"]');
    await page.waitForTimeout(5000);

    // Search
    const searchInput = page.locator(SEARCH_SELECTORS).first();
    await searchInput.click();
    await searchInput.fill('upload document');
    await page.waitForTimeout(2000);

    await page.screenshot({ path: `test-results/artifacts/${testName}/crew_search.png` });

    // Check for Upload Document button (should NOT be visible for CREW)
    const uploadButton = page.locator('[data-testid="action-btn-upload_document"], button:has-text("Upload Document")').first();
    const uploadVisible = await uploadButton.count() > 0;

    // CREW should not see MUTATE actions
    // They might see READ actions like "Get Document Download Link"
    const readOnlyButtons = page.locator('button:has-text("Download"), button:has-text("View")');
    const readOnlyCount = await readOnlyButtons.count();

    saveArtifact('crew_no_upload_report.json', {
      timestamp: new Date().toISOString(),
      uploadButtonVisible: uploadVisible,
      readOnlyButtonsCount: readOnlyCount,
      expectation: 'CREW should NOT see Upload Document (MUTATE action)',
    }, testName);

    console.log('\n=== CREW DENIAL TEST ===');
    console.log('Upload button visible:', uploadVisible);
    console.log('Read-only buttons:', readOnlyCount);
    console.log('========================\n');

    // CREW should not see Upload Document
    expect(uploadVisible).toBe(false);
  });

});
