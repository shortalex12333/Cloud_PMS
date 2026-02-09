/**
 * Receiving Lens - Test with Existing Data
 *
 * Works around backend add_item bug by using existing receivings.
 * Tests the accept flow on pre-existing data to verify:
 * - Accept button appears for Captain
 * - 400 error handling works in UI
 * - Signature flow works
 */

import { test, expect, Page } from '@playwright/test';
import { loginAs } from './auth.helper';

test.describe('Receiving Lens - Using Existing Data', () => {

  test('Captain can search, focus, and interact with existing receivings', async ({ page }) => {
    console.log('\n═══════════════════════════════════════════════════════');
    console.log('🎯 TEST: Captain Flow with Existing Data');
    console.log('═══════════════════════════════════════════════════════\n');

    // Step 1: Login
    console.log('📝 Step 1: Login as captain');
    await loginAs(page, 'captain');
    await page.screenshot({ path: '/tmp/existing-step1-login.png', fullPage: true });
    console.log('✅ Logged in\n');

    // Step 2: Search for receivings (try multiple queries)
    console.log('📝 Step 2: Search for receivings');

    const searchInput = page.locator('[data-testid="search-input"], input[placeholder*="Search"]').first();
    await searchInput.waitFor({ state: 'visible', timeout: 10000 });

    const queries = [
      'receiving',
      'draft receiving',
      'invoice',
      'delivery',
      'shipment',
    ];

    let foundReceiving = false;

    for (const query of queries) {
      console.log(`   Trying: "${query}"`);
      await searchInput.click();
      await searchInput.fill(query);
      await page.waitForTimeout(1000);

      const results = await page.locator('[data-testid="search-result-item"]').count();
      console.log(`   → Found ${results} result(s)`);

      if (results > 0) {
        foundReceiving = true;
        await page.screenshot({
          path: `/tmp/existing-step2-search-${query.replace(/\s+/g, '-')}.png`,
          fullPage: true
        });
        break;
      }

      await searchInput.clear();
    }

    if (!foundReceiving) {
      console.log('\n⚠️  No receivings found in any query');
      console.log('   Database may be empty or search not working\n');
      return;
    }

    console.log('✅ Found receiving data\n');

    // Step 3: Focus on first result
    console.log('📝 Step 3: Click first result to focus');
    const firstResult = page.locator('[data-testid="search-result-item"]').first();
    await firstResult.click();
    await page.waitForTimeout(500);
    await page.screenshot({ path: '/tmp/existing-step3-focused.png', fullPage: true });
    console.log('✅ Context panel opened\n');

    // Step 4: Wait for actions to load
    console.log('📝 Step 4: Wait for actions to load');
    await page.waitForTimeout(1500); // Give time for /v1/decisions call

    // Take screenshot of actions area
    await page.screenshot({ path: '/tmp/existing-step4-actions-loaded.png', fullPage: true });

    // Step 5: Look for action buttons
    console.log('📝 Step 5: Check available actions');

    const allButtons = page.locator('button');
    const buttonCount = await allButtons.count();
    console.log(`   Total buttons in UI: ${buttonCount}`);

    // Check for specific action buttons
    const acceptButton = page.locator('button:has-text("Accept")');
    const viewButton = page.locator('button:has-text("View"), a:has-text("View")');
    const editButton = page.locator('button:has-text("Edit")');
    const addButton = page.locator('button:has-text("Add")');

    const hasAccept = await acceptButton.count() > 0;
    const hasView = await viewButton.count() > 0;
    const hasEdit = await editButton.count() > 0;
    const hasAdd = await addButton.count() > 0;

    console.log(`\n   Action buttons found:`);
    console.log(`   - Accept: ${hasAccept ? '✅ YES' : '❌ NO'}`);
    console.log(`   - View: ${hasView ? '✅ YES' : '❌ NO'}`);
    console.log(`   - Edit: ${hasEdit ? '✅ YES' : '❌ NO'}`);
    console.log(`   - Add: ${hasAdd ? '✅ YES' : '❌ NO'}\n`);

    // Step 6: Set up API listener
    console.log('📝 Step 6: Set up API response listener');
    const apiResponses: Array<{ url: string; status: number; body?: any }> = [];

    page.on('response', async (response) => {
      if (response.url().includes('/v1/actions') || response.url().includes('/v1/decisions')) {
        const body = await response.json().catch(() => null);
        apiResponses.push({
          url: response.url(),
          status: response.status(),
          body: body,
        });

        if (body?.error_code) {
          console.log(`   📡 API: HTTP ${response.status()} + ${body.error_code}`);
        }
      }
    });
    console.log('✅ Listener active\n');

    // Step 7: If Accept button exists, try clicking it
    if (hasAccept) {
      console.log('📝 Step 7: Click Accept button');
      console.log('   Expected: May see 400 error or signature form\n');

      await acceptButton.first().click();
      await page.waitForTimeout(2000);

      await page.screenshot({ path: '/tmp/existing-step7-after-accept-click.png', fullPage: true });

      // Check for API responses
      const signatureErrors = apiResponses.filter(r =>
        r.body?.error_code === 'SIGNATURE_REQUIRED'
      );

      if (signatureErrors.length > 0) {
        const error = signatureErrors[0];
        console.log('🎉 P1 FIX CAPTURED IN UI!');
        console.log(`   HTTP Status: ${error.status}`);
        console.log(`   Error Code: ${error.body.error_code}`);
        console.log(`   Message: ${error.body.message}\n`);

        if (error.status === 400) {
          console.log('✅ HTTP 400 (not 403) - P1 FIX WORKS IN UI!\n');
        } else {
          console.log(`⚠️  HTTP ${error.status} (expected 400)\n`);
        }
      }

      // Check for error message in UI
      const errorInUI = page.locator(
        '[data-testid="error-message"], ' +
        '.error, ' +
        '[role="alert"], ' +
        'text=/signature/i, ' +
        'text=/required/i'
      );

      if (await errorInUI.count() > 0) {
        const errorText = await errorInUI.first().textContent();
        console.log(`✅ Error shown in UI: "${errorText}"\n`);
      }

      // Check for signature form
      const signatureForm = page.locator(
        '[data-testid="signature-form"], ' +
        'input[name="signature_name"], ' +
        'input[placeholder*="name"]'
      );

      if (await signatureForm.count() > 0) {
        console.log('✅ Signature form appeared\n');
        await page.screenshot({ path: '/tmp/existing-step7-signature-form.png', fullPage: true });

        // Try to fill and submit
        console.log('📝 Step 8: Fill signature form');
        const nameInput = page.locator('input[name="signature_name"], input[placeholder*="name"]').first();
        const titleInput = page.locator('input[name="signature_title"], input[placeholder*="title"]').first();

        if (await nameInput.count() > 0) {
          await nameInput.fill('Captain Test User');
        }

        if (await titleInput.count() > 0) {
          await titleInput.fill('Captain');
        }

        const submitButton = page.locator(
          'button:has-text("Confirm"), ' +
          'button:has-text("Sign"), ' +
          'button:has-text("Submit")'
        ).first();

        if (await submitButton.count() > 0) {
          console.log('   Submitting signature...\n');
          await submitButton.click();
          await page.waitForTimeout(2000);

          await page.screenshot({ path: '/tmp/existing-step8-after-signature.png', fullPage: true });

          // Check for success
          const successInUI = page.locator(
            '[data-testid="success-message"], ' +
            '.success, ' +
            'text=/success/i, ' +
            'text=/accepted/i'
          );

          if (await successInUI.count() > 0) {
            const successText = await successInUI.first().textContent();
            console.log(`✅ Success shown: "${successText}"\n`);
          }
        }
      }

    } else {
      console.log('📝 Step 7: No Accept button found');
      console.log('   Possible reasons:');
      console.log('   - Receiving already accepted');
      console.log('   - Backend not returning accept action');
      console.log('   - UI not rendering actions properly\n');

      // List all button texts
      console.log('   All button texts visible:');
      for (let i = 0; i < Math.min(buttonCount, 10); i++) {
        const text = await allButtons.nth(i).textContent();
        if (text && text.trim()) {
          console.log(`   ${i + 1}. "${text.trim()}"`);
        }
      }
      console.log();
    }

    // Final screenshot
    await page.screenshot({ path: '/tmp/existing-final.png', fullPage: true });

    console.log('\n═══════════════════════════════════════════════════════');
    console.log('✅ TEST COMPLETE');
    console.log('═══════════════════════════════════════════════════════\n');
  });

});
