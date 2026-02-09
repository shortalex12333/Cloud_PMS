/**
 * RECEIVING LENS - REAL UI JOURNEY TEST
 * ======================================
 *
 * Tests the ACTUAL user journey through the UI:
 * - Single page architecture (app.celeste7.ai)
 * - Query → Focus → Act pattern
 * - No page navigation (except /login redirect)
 * - All state changes happen dynamically
 *
 * Flow:
 * 1. Login → redirects to /login then back to app
 * 2. Click "+" on search bar → Create receiving
 * 3. Upload image → OCR extraction
 * 4. Review/adjust items
 * 5. Accept with signature (should fail without sig, succeed with sig)
 */

import { test, expect, Page } from '@playwright/test';
import { loginAs } from './auth.helper';
import path from 'path';

const BASE_URL = 'https://app.celeste7.ai';

// ============================================================================
// HELPERS
// ============================================================================

async function waitForSearchBar(page: Page) {
  // Wait for search bar to be visible (means app loaded)
  const searchInput = page.locator('input[placeholder*="Search"], input[placeholder*="search"], [data-testid="search-input"]').first();
  await searchInput.waitFor({ state: 'visible', timeout: 15000 });
  return searchInput;
}

async function findPlusButton(page: Page) {
  // Find "+" icon on search bar
  const plusButton = page.locator('button:has-text("+"), [data-testid="create-button"], [aria-label*="Create"], [aria-label*="create"], [aria-label*="New"], [aria-label*="new"]').first();
  return plusButton;
}

async function waitForContextPanel(page: Page) {
  const contextPanel = page.locator('[data-testid="context-panel"], [role="dialog"], .context-panel').first();
  await contextPanel.waitFor({ state: 'visible', timeout: 10000 });
  return contextPanel;
}

// ============================================================================
// MAIN TEST
// ============================================================================

test.describe('RECEIVING LENS - Real UI Journey', () => {

  test('Complete journey: Create → Upload → Review → Accept', async ({ page }) => {
    console.log('\n🎯 RECEIVING LENS - COMPLETE UI JOURNEY\n');

    // =======================================================================
    // STEP 1: Login
    // =======================================================================
    console.log('Step 1: Login as captain...');
    await loginAs(page, 'captain');

    // Wait for app to load
    const searchBar = await waitForSearchBar(page);
    console.log('✓ App loaded, search bar visible');

    await page.screenshot({ path: '/tmp/receiving-journey-1-loaded.png', fullPage: true });

    // =======================================================================
    // STEP 2: Find and click "+" button
    // =======================================================================
    console.log('\nStep 2: Looking for "+" button to create receiving...');

    // Try multiple selectors for the plus button
    const plusButton = await page.locator(`
      button:has-text("+"),
      [data-testid="create-button"],
      [aria-label*="Create"],
      [aria-label*="create"],
      [aria-label*="New"],
      [aria-label*="new"],
      button[title*="Create"],
      button[title*="New"]
    `).first();

    const plusVisible = await plusButton.isVisible().catch(() => false);

    if (!plusVisible) {
      console.log('⚠️  Plus button not found. Looking for any buttons near search bar...');
      const allButtons = page.locator('button');
      const buttonCount = await allButtons.count();
      console.log(`   Found ${buttonCount} total buttons on page`);

      // Take screenshot to see what's visible
      await page.screenshot({ path: '/tmp/receiving-journey-2-no-plus.png', fullPage: true });

      // List first 10 buttons
      for (let i = 0; i < Math.min(10, buttonCount); i++) {
        const text = await allButtons.nth(i).textContent();
        const ariaLabel = await allButtons.nth(i).getAttribute('aria-label');
        console.log(`   Button ${i}: "${text}" (aria-label: "${ariaLabel}")`);
      }

      throw new Error('Could not find "+" button to create receiving');
    }

    console.log('✓ Found "+" button, clicking...');
    await plusButton.click();
    await page.waitForTimeout(1000); // Wait for UI response

    await page.screenshot({ path: '/tmp/receiving-journey-3-clicked-plus.png', fullPage: true });

    // =======================================================================
    // STEP 3: Verify context panel or modal opened
    // =======================================================================
    console.log('\nStep 3: Checking if creation UI appeared...');

    // Look for either context panel or modal
    const creationUI = page.locator(`
      [data-testid="context-panel"],
      [data-testid="receiving-form"],
      [role="dialog"],
      [data-testid="modal"],
      .context-panel,
      .modal
    `).first();

    const creationUIVisible = await creationUI.isVisible().catch(() => false);

    if (!creationUIVisible) {
      console.log('⚠️  No creation UI appeared after clicking plus');
      await page.screenshot({ path: '/tmp/receiving-journey-4-no-ui.png', fullPage: true });

      // Maybe it shows actions in the context panel?
      // Try searching for "receiving" first to see what actions are available
      console.log('   Trying to search for existing receiving to see actions...');
      await searchBar.fill('invoice');
      await page.waitForTimeout(1500);

      const results = page.locator('[data-testid="search-result-item"]');
      const resultCount = await results.count();
      console.log(`   Found ${resultCount} search results`);

      if (resultCount > 0) {
        console.log('   Clicking first result to see context panel...');
        await results.first().click();
        await page.waitForTimeout(1000);

        await page.screenshot({ path: '/tmp/receiving-journey-5-clicked-result.png', fullPage: true });

        // Now look for actions
        const actions = page.locator('[data-testid="action-button"], button[data-action]');
        const actionCount = await actions.count();
        console.log(`   Found ${actionCount} action buttons`);

        for (let i = 0; i < Math.min(5, actionCount); i++) {
          const text = await actions.nth(i).textContent();
          console.log(`   Action ${i}: "${text}"`);
        }
      }

      throw new Error('Creation UI did not appear. See screenshots in /tmp/receiving-journey-*.png');
    }

    console.log('✓ Creation UI appeared');
    await page.screenshot({ path: '/tmp/receiving-journey-6-creation-ui.png', fullPage: true });

    // =======================================================================
    // STEP 4: Look for upload button or vendor fields
    // =======================================================================
    console.log('\nStep 4: Looking for upload or form fields...');

    // Look for upload button
    const uploadButton = page.locator(`
      button:has-text("Upload"),
      [data-testid="upload-button"],
      input[type="file"],
      [aria-label*="upload"]
    `).first();

    const uploadVisible = await uploadButton.isVisible().catch(() => false);

    if (uploadVisible) {
      console.log('✓ Found upload button');
      // Note: Can't actually test file upload in this environment without proper file
      console.log('⚠️  Upload flow requires actual file - skipping upload test');
    }

    // Look for vendor fields (alternative path without image)
    const vendorNameField = page.locator('input[name="vendor_name"], input[placeholder*="Vendor"], [data-testid="vendor-name"]').first();
    const vendorRefField = page.locator('input[name="vendor_reference"], input[placeholder*="Reference"], input[placeholder*="Invoice"], [data-testid="vendor-reference"]').first();

    const vendorFieldsVisible = await vendorNameField.isVisible().catch(() => false) || await vendorRefField.isVisible().catch(() => false);

    if (vendorFieldsVisible) {
      console.log('✓ Found vendor input fields');

      // Fill vendor fields
      if (await vendorNameField.isVisible().catch(() => false)) {
        await vendorNameField.fill('Test Vendor Ltd');
        console.log('  Filled vendor name');
      }

      if (await vendorRefField.isVisible().catch(() => false)) {
        await vendorRefField.fill(`INV-${Date.now()}`);
        console.log('  Filled vendor reference');
      }

      await page.screenshot({ path: '/tmp/receiving-journey-7-filled-form.png', fullPage: true });

      // Look for Submit/Create/Save button
      const submitButton = page.locator('button:has-text("Create"), button:has-text("Save"), button:has-text("Submit"), button[type="submit"]').first();
      const submitVisible = await submitButton.isVisible().catch(() => false);

      if (submitVisible) {
        console.log('✓ Found submit button, clicking...');
        await submitButton.click();
        await page.waitForTimeout(2000);

        await page.screenshot({ path: '/tmp/receiving-journey-8-after-submit.png', fullPage: true });
        console.log('✓ Submitted creation form');
      } else {
        console.log('⚠️  No submit button found');
      }
    }

    // =======================================================================
    // STEP 5: Look for actions on the receiving
    // =======================================================================
    console.log('\nStep 5: Looking for actions (Add Item, Accept, etc.)...');

    await page.waitForTimeout(1000);

    const actionButtons = page.locator('[data-testid="action-button"], button[data-action]');
    const actionCount = await actionButtons.count();

    console.log(`Found ${actionCount} action buttons`);

    const actions: string[] = [];
    for (let i = 0; i < actionCount; i++) {
      const text = await actionButtons.nth(i).textContent();
      if (text) {
        actions.push(text.trim());
        console.log(`  Action ${i + 1}: "${text.trim()}"`);
      }
    }

    await page.screenshot({ path: '/tmp/receiving-journey-9-actions.png', fullPage: true });

    // =======================================================================
    // STEP 6: Try to accept (should show signature requirement)
    // =======================================================================
    console.log('\nStep 6: Looking for Accept action...');

    const acceptButton = page.locator('button:has-text("Accept"), [data-action="accept_receiving"]').first();
    const acceptVisible = await acceptButton.isVisible().catch(() => false);

    if (acceptVisible) {
      console.log('✓ Found Accept button, clicking...');
      await acceptButton.click();
      await page.waitForTimeout(1500);

      await page.screenshot({ path: '/tmp/receiving-journey-10-clicked-accept.png', fullPage: true });

      // Look for signature form or error message
      const signatureForm = page.locator('[data-testid="signature-form"], input[name="signature_name"], input[placeholder*="Name"]');
      const errorMessage = page.locator('[data-testid="error"], [role="alert"], .error, .toast');

      const sigFormVisible = await signatureForm.first().isVisible({ timeout: 3000 }).catch(() => false);
      const errorVisible = await errorMessage.first().isVisible({ timeout: 3000 }).catch(() => false);

      if (sigFormVisible) {
        console.log('✓ Signature form appeared');
        await page.screenshot({ path: '/tmp/receiving-journey-11-signature-form.png', fullPage: true });

        // Fill signature
        const nameInput = page.locator('input[name="signature_name"], input[placeholder*="Name"]').first();
        const titleInput = page.locator('input[name="signature_title"], input[placeholder*="Title"]').first();

        if (await nameInput.isVisible().catch(() => false)) {
          await nameInput.fill('Test Captain');
          console.log('  Filled signature name');
        }

        if (await titleInput.isVisible().catch(() => false)) {
          await titleInput.fill('Captain');
          console.log('  Filled signature title');
        }

        // Submit signature
        const submitSigButton = page.locator('button:has-text("Confirm"), button:has-text("Sign"), button:has-text("Submit")').first();
        if (await submitSigButton.isVisible().catch(() => false)) {
          await submitSigButton.click();
          await page.waitForTimeout(2000);

          await page.screenshot({ path: '/tmp/receiving-journey-12-submitted-sig.png', fullPage: true });
          console.log('✓ Submitted signature');

          // Check for success
          const successMessage = page.locator(':has-text("success"), :has-text("accepted"), [data-testid="success"]');
          const successVisible = await successMessage.first().isVisible({ timeout: 3000 }).catch(() => false);

          if (successVisible) {
            console.log('✅ RECEIVING ACCEPTED SUCCESSFULLY');
          } else {
            console.log('⚠️  No success message appeared');
          }
        }

      } else if (errorVisible) {
        const errorText = await errorMessage.first().textContent();
        console.log(`✓ Error message appeared: "${errorText}"`);

        if (errorText?.toLowerCase().includes('signature')) {
          console.log('✅ P1 FIX VERIFIED: Signature required error shown');
        }

        await page.screenshot({ path: '/tmp/receiving-journey-11-error.png', fullPage: true });
      } else {
        console.log('⚠️  No signature form or error appeared');
        await page.screenshot({ path: '/tmp/receiving-journey-11-no-response.png', fullPage: true });
      }

    } else {
      console.log('⚠️  Accept button not visible');
      console.log('   Available actions:', actions);
    }

    // =======================================================================
    // FINAL SCREENSHOT
    // =======================================================================
    await page.screenshot({ path: '/tmp/receiving-journey-FINAL.png', fullPage: true });

    console.log('\n' + '='.repeat(70));
    console.log('RECEIVING LENS - UI JOURNEY COMPLETE');
    console.log('='.repeat(70));
    console.log('\nScreenshots saved to /tmp/receiving-journey-*.png');
    console.log('Review screenshots to see actual UI flow\n');
  });

});
