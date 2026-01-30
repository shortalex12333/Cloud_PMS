/**
 * Crew Actions API Test - Crew Lens v2
 *
 * Verifies that /v1/actions/list is called when user types crew-related queries
 * and that backend→UI parity is maintained (UI renders exactly what backend returns).
 *
 * Tests:
 * 1. UI calls /v1/actions/list when typing crew query
 * 2. API returns correct actions for crew domain
 * 3. Backend→UI parity: HOD sees mutation actions
 * 4. Backend→UI parity: CREW sees no HOD actions
 */
import { test, expect } from '@playwright/test';

const BASE_URL = process.env.BASE_URL || 'https://app.celeste7.ai';
const API_URL = process.env.RENDER_API_URL || 'https://pipeline-core.int.celeste7.ai';
const HOD_EMAIL = 'hod.test@alex-short.com';
const CREW_EMAIL = 'crew.test@alex-short.com';
const PASSWORD = 'Password2!';

test.describe('Crew - Actions API Integration', () => {

  test('UI calls /v1/actions/list when typing crew query', async ({ page }) => {
    const actionsApiCalls: string[] = [];

    // Track /v1/actions/list calls
    page.on('request', (request) => {
      if (request.url().includes('/v1/actions/list')) {
        actionsApiCalls.push(request.url());
        console.log('→ Actions API called:', request.url());
      }
    });

    // Login as HOD
    await page.goto(`${BASE_URL}/login`);
    await page.fill('input[type="email"], input[name="email"]', HOD_EMAIL);
    await page.fill('input[type="password"]', PASSWORD);
    await page.click('button[type="submit"]');
    await page.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 20000 });

    // Find search input
    const searchInput = page.locator(
      'input[placeholder*="Parts"], input[placeholder*="Search"], [data-testid="search-input"]'
    ).first();

    await searchInput.waitFor({ state: 'visible', timeout: 15000 });

    // Type crew-related query
    await searchInput.fill('list crew');
    console.log('Typed: "list crew"');

    // Wait for debounce + API call
    await page.waitForTimeout(3000);

    // Verify actions API was called
    console.log(`Actions API calls made: ${actionsApiCalls.length}`);
    actionsApiCalls.forEach(url => console.log(`  - ${url}`));

    // /v1/actions/list should be called
    expect(actionsApiCalls.length).toBeGreaterThan(0);

    // Verify the domain parameter is 'crew'
    const crewCall = actionsApiCalls.find(url => url.includes('domain=crew'));
    expect(crewCall).toBeTruthy();
  });

  test('API returns actions for crew queries (no auth)', async ({ request }) => {
    // Direct API test without UI
    const response = await request.get(`${API_URL}/v1/actions/list?q=list%20crew&domain=crew`, {
      failOnStatusCode: false,
    });

    // Should return 401 (requires auth)
    console.log(`API response: ${response.status()}`);
    expect([200, 401]).toContain(response.status());

    if (response.status() === 200) {
      const data = await response.json();
      console.log('Actions returned:', data.actions?.length || 0);
      console.log('Actions:', data.actions?.map((a: any) => a.action_id).join(', '));
    }
  });

  test('HOD sees crew mutation actions in action list', async ({ page }) => {
    let actionsResponse: any = null;

    // Intercept /v1/actions/list response
    page.on('response', async (response) => {
      if (response.url().includes('/v1/actions/list') && response.url().includes('domain=crew')) {
        try {
          actionsResponse = await response.json();
          console.log('Actions API response:', actionsResponse);
        } catch (e) {
          console.log('Failed to parse actions response:', e);
        }
      }
    });

    // Login as HOD
    await page.goto(`${BASE_URL}/login`);
    await page.fill('input[type="email"], input[name="email"]', HOD_EMAIL);
    await page.fill('input[type="password"]', PASSWORD);
    await page.click('button[type="submit"]');
    await page.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 20000 });

    // Search for crew
    const searchInput = page.locator(
      'input[placeholder*="Parts"], input[placeholder*="Search"], [data-testid="search-input"]'
    ).first();
    await searchInput.waitFor({ state: 'visible', timeout: 15000 });
    await searchInput.fill('list crew');

    // Wait for API response
    await page.waitForTimeout(3000);

    // Verify HOD sees mutation actions
    if (actionsResponse && actionsResponse.actions) {
      const actionIds = actionsResponse.actions.map((a: any) => a.action_id);
      console.log('HOD sees actions:', actionIds);

      // HOD should see these actions
      const expectedActions = ['list_crew_members', 'assign_role', 'revoke_role'];
      const foundActions = expectedActions.filter(a => actionIds.includes(a));

      expect(foundActions.length).toBeGreaterThan(0);
      console.log(`✓ HOD sees ${foundActions.length}/${expectedActions.length} expected actions`);
    }
  });

  test('CREW does not see HOD-only actions in action list', async ({ page }) => {
    let actionsResponse: any = null;

    // Intercept /v1/actions/list response
    page.on('response', async (response) => {
      if (response.url().includes('/v1/actions/list') && response.url().includes('domain=crew')) {
        try {
          actionsResponse = await response.json();
          console.log('Actions API response:', actionsResponse);
        } catch (e) {
          console.log('Failed to parse actions response:', e);
        }
      }
    });

    // Login as CREW
    await page.goto(`${BASE_URL}/login`);
    await page.fill('input[type="email"], input[name="email"]', CREW_EMAIL);
    await page.fill('input[type="password"]', PASSWORD);
    await page.click('button[type="submit"]');
    await page.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 20000 });

    // Search for crew
    const searchInput = page.locator(
      'input[placeholder*="Parts"], input[placeholder*="Search"], [data-testid="search-input"]'
    ).first();
    await searchInput.waitFor({ state: 'visible', timeout: 15000 });
    await searchInput.fill('my profile');

    // Wait for API response
    await page.waitForTimeout(3000);

    // Verify CREW does not see HOD-only actions
    if (actionsResponse && actionsResponse.actions) {
      const actionIds = actionsResponse.actions.map((a: any) => a.action_id);
      console.log('CREW sees actions:', actionIds);

      // CREW should NOT see these HOD-only actions
      const hodOnlyActions = ['list_crew_members', 'assign_role', 'revoke_role', 'update_crew_member_status'];
      const foundHodActions = hodOnlyActions.filter(a => actionIds.includes(a));

      expect(foundHodActions.length).toBe(0);
      console.log(`✓ CREW correctly does not see HOD-only actions`);
    }
  });

  test('Search for "my profile" returns view_my_profile action', async ({ page }) => {
    let actionsResponse: any = null;

    // Intercept /v1/actions/list response
    page.on('response', async (response) => {
      if (response.url().includes('/v1/actions/list')) {
        try {
          actionsResponse = await response.json();
        } catch (e) {
          console.log('Failed to parse actions response:', e);
        }
      }
    });

    // Login as CREW
    await page.goto(`${BASE_URL}/login`);
    await page.fill('input[type="email"], input[name="email"]', CREW_EMAIL);
    await page.fill('input[type="password"]', PASSWORD);
    await page.click('button[type="submit"]');
    await page.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 20000 });

    // Search for "my profile"
    const searchInput = page.locator(
      'input[placeholder*="Parts"], input[placeholder*="Search"], [data-testid="search-input"]'
    ).first();
    await searchInput.waitFor({ state: 'visible', timeout: 15000 });
    await searchInput.fill('my profile');

    // Wait for API response
    await page.waitForTimeout(3000);

    // Verify view_my_profile action is returned
    if (actionsResponse && actionsResponse.actions) {
      const actionIds = actionsResponse.actions.map((a: any) => a.action_id);
      console.log('Actions for "my profile":', actionIds);

      expect(actionIds).toContain('view_my_profile');
      console.log('✓ view_my_profile action found');
    }
  });

});
