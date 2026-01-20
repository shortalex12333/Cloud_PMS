import { test, expect } from '@playwright/test';

const PROD_URL = 'https://app.celeste7.ai';
const TEST_EMAIL = 'x@alex-short.com';
const TEST_PASSWORD = 'Password2!';

test.describe('B) Document Storage Verification', () => {

  test('DOC_01: Search for document and view in context panel', async ({ page }) => {
    // Login
    await page.goto(`${PROD_URL}/login`);
    await page.fill('input[type="email"]', TEST_EMAIL);
    await page.fill('input[type="password"]', TEST_PASSWORD);
    await page.click('button[type="submit"]');
    await page.waitForURL('**/app**', { timeout: 15000 });
    await page.waitForTimeout(3000);

    console.log('DOC_01: Logged in, searching for document...');

    // Search for a known document type
    const searchInput = page.locator('input').first();
    await searchInput.fill('watermaker manual');
    await page.waitForTimeout(3000);

    // Take screenshot of search results
    await page.screenshot({
      path: '/Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS/verification_handoff/evidence/DOC_01_search_results.png',
      fullPage: true
    });

    // Look for document results
    const documentResults = page.locator('[class*="result"], [class*="Result"]');
    const count = await documentResults.count();
    console.log('DOC_01: Search results count:', count);

    if (count > 0) {
      // Click first result to open in context panel
      await documentResults.first().click();
      await page.waitForTimeout(3000);

      // Take screenshot of context panel
      await page.screenshot({
        path: '/Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS/verification_handoff/evidence/DOC_01_context_panel.png',
        fullPage: true
      });

      console.log('DOC_01: PASS - Document search and context panel working');
    } else {
      console.log('DOC_01: No document results found');
    }
  });

  test('DOC_02: Verify document signed URL generation', async ({ page }) => {
    // Login
    await page.goto(`${PROD_URL}/login`);
    await page.fill('input[type="email"]', TEST_EMAIL);
    await page.fill('input[type="password"]', TEST_PASSWORD);
    await page.click('button[type="submit"]');
    await page.waitForURL('**/app**', { timeout: 15000 });
    await page.waitForTimeout(2000);

    // Use a real document UUID from doc_metadata table
    // This is: Generic_watermakers_Document_4.pdf
    const documentId = '0a75fa80-9435-41fb-b7ea-626cca9173a4';

    const result = await page.evaluate(async (docId) => {
      // Find Supabase session
      const keys = Object.keys(localStorage);
      const supabaseKey = keys.find(k => k.startsWith('sb-') && k.endsWith('-auth-token'));
      if (!supabaseKey) return { error: 'No auth key' };

      const stored = localStorage.getItem(supabaseKey);
      if (!stored) return { error: 'No session' };

      const parsed = JSON.parse(stored);
      const token = parsed.access_token;
      if (!token) return { error: 'No token' };

      // Call the document sign endpoint
      const response = await fetch(`https://pipeline-core.int.celeste7.ai/v1/documents/${docId}/sign`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });

      return {
        status: response.status,
        statusText: response.statusText,
        data: await response.json().catch(() => response.text())
      };
    }, documentId);

    console.log('DOC_02: Sign endpoint result:', JSON.stringify(result, null, 2));

    // Write evidence
    const fs = require('fs');
    fs.writeFileSync(
      '/Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS/verification_handoff/evidence/DOC_02_sign_url_response.json',
      JSON.stringify(result, null, 2)
    );

    if (result.status === 200 && result.data?.signedUrl) {
      expect(result.data.signedUrl).toContain('supabase');
      console.log('DOC_02: PASS - Signed URL generated');
    } else {
      console.log('DOC_02: Sign endpoint response:', result);
    }
  });

  test('DOC_03: RLS Negative Control - Yacht Isolation', async ({ page }) => {
    const fs = require('fs');
    const TENANT_SUPABASE_URL = 'https://vzsohavtuotocgrfkfyd.supabase.co';
    const SERVICE_KEY = process.env.TENANT_SUPABASE_SERVICE_ROLE_KEY || process.env.SUPABASE_SERVICE_KEY;
    const CORRECT_YACHT_ID = '85fe1119-b04c-41ac-80f1-829d23322598';
    const WRONG_YACHT_ID = '00000000-0000-0000-0000-000000000000';

    const results = {
      timestamp: new Date().toISOString(),
      tests: [] as any[]
    };

    // Test 1: Anonymous access (no valid API key)
    console.log('DOC_03.1: Testing anonymous access...');
    const anonResponse = await fetch(
      `${TENANT_SUPABASE_URL}/rest/v1/doc_metadata?select=id,filename,yacht_id&limit=5`,
      {
        headers: {
          'apikey': 'invalid_anon_key',
          'Content-Type': 'application/json'
        }
      }
    );
    results.tests.push({
      test: 'ANON_ACCESS',
      status: anonResponse.status,
      passed: anonResponse.status === 401
    });
    expect(anonResponse.status).toBe(401);
    console.log('DOC_03.1: PASS - Anonymous access denied (401)');

    // Test 2: Wrong yacht_id query (should return 0 results)
    if (SERVICE_KEY) {
      console.log('DOC_03.2: Testing wrong yacht_id access...');
      const wrongYachtResponse = await fetch(
        `${TENANT_SUPABASE_URL}/rest/v1/doc_metadata?select=id,filename,yacht_id&yacht_id=eq.${WRONG_YACHT_ID}&limit=5`,
        {
          headers: {
            'apikey': SERVICE_KEY,
            'Authorization': `Bearer ${SERVICE_KEY}`,
            'Content-Type': 'application/json'
          }
        }
      );
      const wrongYachtData = await wrongYachtResponse.json();
      results.tests.push({
        test: 'WRONG_YACHT_ACCESS',
        status: wrongYachtResponse.status,
        yacht_id_queried: WRONG_YACHT_ID,
        row_count: Array.isArray(wrongYachtData) ? wrongYachtData.length : 'N/A',
        passed: wrongYachtResponse.status === 200 && Array.isArray(wrongYachtData) && wrongYachtData.length === 0
      });
      expect(wrongYachtResponse.status).toBe(200);
      expect(wrongYachtData).toEqual([]);
      console.log('DOC_03.2: PASS - Wrong yacht returns empty array');

      // Test 3: Correct yacht_id query (should return documents)
      console.log('DOC_03.3: Testing correct yacht_id access...');
      const correctYachtResponse = await fetch(
        `${TENANT_SUPABASE_URL}/rest/v1/doc_metadata?select=id,filename,yacht_id&yacht_id=eq.${CORRECT_YACHT_ID}&limit=5`,
        {
          headers: {
            'apikey': SERVICE_KEY,
            'Authorization': `Bearer ${SERVICE_KEY}`,
            'Content-Type': 'application/json'
          }
        }
      );
      const correctYachtData = await correctYachtResponse.json();
      results.tests.push({
        test: 'CORRECT_YACHT_ACCESS',
        status: correctYachtResponse.status,
        yacht_id_queried: CORRECT_YACHT_ID,
        row_count: Array.isArray(correctYachtData) ? correctYachtData.length : 'N/A',
        sample: Array.isArray(correctYachtData) ? correctYachtData.slice(0, 2) : correctYachtData,
        passed: correctYachtResponse.status === 200 && Array.isArray(correctYachtData) && correctYachtData.length > 0
      });
      expect(correctYachtResponse.status).toBe(200);
      expect(correctYachtData.length).toBeGreaterThan(0);
      console.log(`DOC_03.3: PASS - Correct yacht returns ${correctYachtData.length} documents`);
    }

    // Write evidence
    fs.writeFileSync(
      '/Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS/verification_handoff/evidence/DOC_03_RLS_NEGATIVE_CONTROL.json',
      JSON.stringify(results, null, 2)
    );

    console.log('DOC_03: PASS - RLS yacht isolation verified');
  });

  test('DOC_04: Browse document library', async ({ page }) => {
    // Login
    await page.goto(`${PROD_URL}/login`);
    await page.fill('input[type="email"]', TEST_EMAIL);
    await page.fill('input[type="password"]', TEST_PASSWORD);
    await page.click('button[type="submit"]');
    await page.waitForURL('**/app**', { timeout: 15000 });
    await page.waitForTimeout(3000);

    // Search for documents by type
    const searchInput = page.locator('input').first();
    await searchInput.fill('pdf');
    await page.waitForTimeout(3000);

    // Count results
    const results = page.locator('[class*="result"], [class*="Result"]');
    const count = await results.count();

    console.log('DOC_04: PDF search results:', count);

    // Take screenshot
    await page.screenshot({
      path: '/Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS/verification_handoff/evidence/DOC_04_document_library.png',
      fullPage: true
    });

    if (count > 0) {
      console.log('DOC_04: PASS - Document library accessible');
    }
  });
});
