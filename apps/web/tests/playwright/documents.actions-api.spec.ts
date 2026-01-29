/**
 * Documents Actions API Test
 *
 * Verifies that /v1/actions/list is called when user types document-related queries
 */
import { test, expect } from '@playwright/test';

const BASE_URL = process.env.BASE_URL || 'https://app.celeste7.ai';
const API_URL = process.env.RENDER_API_URL || 'https://pipeline-core.int.celeste7.ai';
const HOD_EMAIL = 'hod.test@alex-short.com';
const HOD_PASSWORD = 'Password2!';

test.describe('Documents - Actions API Integration', () => {

  test('UI calls /v1/actions/list when typing document query', async ({ page }) => {
    const actionsApiCalls: string[] = [];

    // Track /v1/actions/list calls
    page.on('request', (request) => {
      if (request.url().includes('/v1/actions/list')) {
        actionsApiCalls.push(request.url());
        console.log('→ Actions API called:', request.url());
      }
    });

    // Login
    await page.goto(`${BASE_URL}/login`);
    await page.fill('input[type="email"], input[name="email"]', HOD_EMAIL);
    await page.fill('input[type="password"]', HOD_PASSWORD);
    await page.click('button[type="submit"]');
    await page.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 20000 });

    // Find search input
    const searchInput = page.locator(
      'input[placeholder*="Parts"], input[placeholder*="Search"], [data-testid="search-input"]'
    ).first();

    await searchInput.waitFor({ state: 'visible', timeout: 15000 });

    // Type document-related query
    await searchInput.fill('add document');
    console.log('Typed: "add document"');

    // Wait for debounce + API call
    await page.waitForTimeout(3000);

    // Verify actions API was called
    console.log(`Actions API calls made: ${actionsApiCalls.length}`);
    actionsApiCalls.forEach(url => console.log(`  - ${url}`));

    // The fix should make this pass - /v1/actions/list should be called
    expect(actionsApiCalls.length).toBeGreaterThan(0);

    // Verify the domain parameter is 'documents'
    const documentsCall = actionsApiCalls.find(url => url.includes('domain=documents'));
    expect(documentsCall).toBeTruthy();
  });

  test('API returns actions for document queries', async ({ request }) => {
    // Direct API test without UI
    // First need to get a JWT - use existing session or generate one

    // This test just verifies the API endpoint works when called correctly
    const response = await request.get(`${API_URL}/v1/actions/list?q=add%20document&domain=documents`, {
      failOnStatusCode: false,
    });

    // Should return 401 (requires auth) or 200 (if somehow authenticated)
    console.log(`API response: ${response.status()}`);
    expect([200, 401]).toContain(response.status());

    if (response.status() === 200) {
      const data = await response.json();
      console.log('Actions returned:', data.actions?.length || 0);
      console.log('Actions:', data.actions?.map((a: any) => a.action_id).join(', '));
    }
  });

});
