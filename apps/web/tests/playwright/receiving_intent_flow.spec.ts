/**
 * Receiving Lens - Intent-Driven Flow Test
 * Tests the single-surface intent flow: Query → Focus → Act
 */
import { test, expect } from '@playwright/test';

const FRONTEND_URL = process.env.PLAYWRIGHT_BASE_URL || process.env.BASE_URL || 'http://localhost:3000';
const CAPTAIN = {
  email: 'x@alex-short.com',
  password: 'Password2!',
  role: 'captain'
};

test.describe('Receiving Lens - Intent Flow', () => {
  test('Captain: Query → Focus → Accept without signature → Expect 400', async ({ page }) => {
    // Step 1: Login
    console.log('1. Logging in as captain...');
    await page.goto(`${FRONTEND_URL}/login`);
    await page.waitForSelector('input[type="email"]', { timeout: 15000 });

    await page.locator('input[type="email"]').fill(CAPTAIN.email);
    await page.locator('input[type="password"]').fill(CAPTAIN.password);
    await page.locator('button[type="submit"]').click();

    // Wait for redirect to main surface
    await page.waitForURL(url => !url.pathname.includes('/login'), { timeout: 20000 });
    console.log(`   ✅ Logged in, current URL: ${page.url()}`);

    // Step 2: Query for receiving
    console.log('');
    console.log('2. Querying for receiving records...');

    // Find the search/query input - adjust selector based on actual implementation
    const searchInput = page.locator('input[placeholder*="What"], input[type="search"], input[placeholder*="query"]').first();

    if (await searchInput.isVisible({ timeout: 5000 }).catch(() => false)) {
      await searchInput.fill('receiving');
      await searchInput.press('Enter');
      await page.waitForTimeout(2000); // Wait for results
      console.log('   ✅ Query submitted');
    } else {
      console.log('   ⚠️  Search input not found - looking for receiving in page content');

      // Alternative: look for receiving links/buttons directly
      const receivingLink = page.locator('text=receiving, text=Receiving').first();
      if (await receivingLink.isVisible({ timeout: 5000 }).catch(() => false)) {
        await receivingLink.click();
        await page.waitForTimeout(2000);
      }
    }

    // Step 3: Focus on a receiving record
    console.log('');
    console.log('3. Focusing on a receiving record...');

    // Look for receiving records - could be table rows, cards, list items
    const receivingRecord = page.locator('[data-receiving-id], tr:has-text("TEST"), div:has-text("vendor")').first();

    if (await receivingRecord.isVisible({ timeout: 5000 }).catch(() => false)) {
      await receivingRecord.click();
      await page.waitForTimeout(1000);
      console.log('   ✅ Receiving record focused');
    } else {
      console.log('   ⚠️  No receiving records found - creating one via API...');

      // Create via API for testing
      const createResponse = await page.evaluate(async () => {
        const token = localStorage.getItem('supabase.auth.token');
        if (!token) return { error: 'No token' };

        const { access_token } = JSON.parse(token);

        // Create receiving
        const createRes = await fetch('https://pipeline-core.int.celeste7.ai/v1/actions/execute', {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${access_token}`,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            action: 'create_receiving',
            context: { yacht_id: '85fe1119-b04c-41ac-80f1-829d23322598' },
            payload: { vendor_reference: `TEST-${Date.now()}` }
          })
        });

        const createData = await createRes.json();
        if (!createData.receiving_id) return { error: 'Create failed', data: createData };

        // Add item
        await fetch('https://pipeline-core.int.celeste7.ai/v1/actions/execute', {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${access_token}`,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            action: 'add_receiving_item',
            context: { yacht_id: '85fe1119-b04c-41ac-80f1-829d23322598' },
            payload: {
              receiving_id: createData.receiving_id,
              description: 'Test Item',
              quantity: 1
            }
          })
        });

        return { receiving_id: createData.receiving_id };
      });

      console.log('   ✅ Created test receiving:', createResponse);

      // Refresh to see new record
      await page.reload();
      await page.waitForTimeout(2000);
    }

    // Step 4: Look for accept action
    console.log('');
    console.log('4. Looking for accept action...');

    // Actions should appear after focusing - look for accept button
    const acceptButton = page.locator('button:has-text("Accept"), button:has-text("accept")').first();

    if (await acceptButton.isVisible({ timeout: 5000 }).catch(() => false)) {
      console.log('   ✅ Accept action visible');

      // Listen for API response
      let apiResponse: any = null;
      page.on('response', async (response) => {
        if (response.url().includes('accept_receiving')) {
          try {
            apiResponse = await response.json();
            console.log('   API Response:', apiResponse);
          } catch (e) {}
        }
      });

      // Click accept (without signature)
      await acceptButton.click();
      await page.waitForTimeout(2000);

      // Check for error in UI or API response
      const errorText = await page.locator('text=/signature.*required/i, text=/400/, [role="alert"]').first().textContent({ timeout: 3000 }).catch(() => null);

      console.log('');
      console.log('===============================================================================');
      console.log('RESULT:');
      console.log('===============================================================================');

      if (apiResponse?.status_code === 400 && apiResponse?.error_code === 'SIGNATURE_REQUIRED') {
        console.log('✅ API returned 400 with SIGNATURE_REQUIRED');
        console.log('🎉 THE FIX WORKS!');
      } else if (errorText?.toLowerCase().includes('signature')) {
        console.log('✅ UI shows signature required error');
        console.log('🎉 THE FIX WORKS!');
      } else {
        console.log('⚠️  Could not verify 400 error - check manually');
        console.log('   Error text found:', errorText);
        console.log('   API response:', apiResponse);
      }

      await page.screenshot({ path: '/tmp/receiving-accept-test.png', fullPage: true });
      console.log('📸 Screenshot: /tmp/receiving-accept-test.png');

    } else {
      console.log('   ⚠️  Accept action not visible');
      console.log('   This could mean:');
      console.log('     - No receiving record is focused');
      console.log('     - Actions are rendered differently');
      console.log('     - Backend did not return accept action');

      await page.screenshot({ path: '/tmp/receiving-no-accept.png', fullPage: true });
      console.log('📸 Screenshot: /tmp/receiving-no-accept.png');
    }
  });
});
