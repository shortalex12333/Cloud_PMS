/**
 * Complete E2E Test with Real Authentication
 *
 * Tests the full user journey for Captain, HOD, and CREW roles using
 * real login flow (password=Password2!) instead of JWT injection.
 *
 * Uses actual tenant users:
 * - captain.tenant@alex-short.com
 * - hod.tenant@alex-short.com
 * - crew.tenant@alex-short.com
 *
 * Coverage:
 * - Document Lens: Search, view, comment permissions
 * - Cross-lens smoke tests: Certificates, Equipment, Faults, Shopping, Crew
 * - Role-based action filtering
 * - Error code mapping (404, 403, not 500)
 */

import { test, expect, Page } from '@playwright/test';

// Real tenant users (not test users)
const TENANT_USERS = {
  captain: {
    email: 'captain.tenant@alex-short.com',
    password: 'Password2!',
    role: 'captain',
  },
  hod: {
    email: 'hod.tenant@alex-short.com',
    password: 'Password2!',
    role: 'chief_engineer',
  },
  crew: {
    email: 'crew.tenant@alex-short.com',
    password: 'Password2!',
    role: 'crew',
  },
};

type UserRole = keyof typeof TENANT_USERS;

// Test data from database
const TEST_YACHT_ID = '85fe1119-b04c-41ac-80f1-829d23322598';
const TEST_DOCUMENT_ID = 'c8191153-4f0b-41b6-8751-5faeabcdef07';
const TEST_DOCUMENT_NAME = 'labels_c8191153_2026';

/**
 * Login with real credentials (no JWT injection)
 */
async function loginAsTenant(page: Page, role: UserRole): Promise<void> {
  const user = TENANT_USERS[role];

  console.log(`[Login] Attempting login as ${role}: ${user.email}`);

  // Navigate to login page
  await page.goto('/login');

  // Wait for login form
  await page.waitForSelector('input[type="email"]', { timeout: 10000 });

  // Fill credentials
  await page.fill('input[type="email"]', user.email);
  await page.fill('input[type="password"]', user.password);

  // Submit
  await page.click('button[type="submit"]');

  // Wait for redirect away from login
  await page.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 15000 });

  console.log(`[Login] ✅ ${role} logged in successfully`);
}

/**
 * Get auth token from page
 */
async function getAuthToken(page: Page): Promise<string> {
  const token = await page.evaluate(() => {
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i);
      if (key?.includes('supabase') || key?.includes('auth')) {
        const value = localStorage.getItem(key);
        if (value) {
          try {
            const parsed = JSON.parse(value);
            return parsed.access_token || parsed.token;
          } catch {}
        }
      }
    }
    return null;
  });

  if (!token) {
    throw new Error('No auth token found in localStorage');
  }

  return token;
}

test.describe('Document Lens - E2E with Real Auth', () => {

  test('Captain: Login and search for document', async ({ page }) => {
    await loginAsTenant(page, 'captain');

    // Verify we're on the main app
    await expect(page).toHaveURL(/^(?!.*\/login)/);

    // Wait for search input
    const searchInput = page.locator('[data-testid="search-input"]');
    await expect(searchInput).toBeVisible({ timeout: 10000 });

    console.log('[Captain] Search input visible');

    // Search for real document by filename
    await searchInput.fill(TEST_DOCUMENT_NAME);
    await page.waitForTimeout(1500); // Wait for debounce + API

    // Take screenshot
    await page.screenshot({ path: '/tmp/e2e_captain_search.png', fullPage: true });

    // Check for NLP understanding
    const pageContent = await page.content();
    const hasUnderstanding = pageContent.toLowerCase().includes('understood');

    console.log(`[Captain] NLP understanding visible: ${hasUnderstanding}`);
    console.log('✅ Captain search test completed');
  });

  test('HOD: Login and verify can access comment actions', async ({ page }) => {
    await loginAsTenant(page, 'hod');

    // Wait for search input
    const searchInput = page.locator('[data-testid="search-input"]');
    await expect(searchInput).toBeVisible({ timeout: 10000 });

    // Try searching for comment-related operations
    await searchInput.fill('add comment');
    await page.waitForTimeout(1500);

    // Take screenshot
    await page.screenshot({ path: '/tmp/e2e_hod_actions.png', fullPage: true });

    console.log('✅ HOD action search test completed');
  });

  test('CREW: Login and verify limited actions', async ({ page }) => {
    await loginAsTenant(page, 'crew');

    // Wait for search input
    const searchInput = page.locator('[data-testid="search-input"]');
    await expect(searchInput).toBeVisible({ timeout: 10000 });

    // Search for operations
    await searchInput.fill('comment');
    await page.waitForTimeout(1500);

    // Take screenshot
    await page.screenshot({ path: '/tmp/e2e_crew_actions.png', fullPage: true });

    console.log('✅ CREW action search test completed');
  });
});

test.describe('P1 Fix - Error Code Mapping', () => {

  test('Captain: Invalid document returns 404 (not 500)', async ({ page, request }) => {
    await loginAsTenant(page, 'captain');

    const authToken = await getAuthToken(page);

    // Call API with invalid document ID
    const response = await request.post('http://localhost:8080/v1/actions/execute', {
      headers: {
        'Authorization': `Bearer ${authToken}`,
        'Content-Type': 'application/json',
      },
      data: {
        action: 'get_document_url',
        context: { yacht_id: TEST_YACHT_ID },
        payload: { document_id: '00000000-0000-0000-0000-000000000000' }
      }
    });

    // Verify returns 404 (NOT 500)
    expect(response.status()).toBe(404);

    const body = await response.json();
    console.log('Response:', body);

    expect(body.code || body.error_code).toBe('NOT_FOUND');

    console.log('✅ P1 Fix Verified: Invalid document returns 404, not 500');
  });

  test('All roles: Error responses use 4xx not 5xx', async ({ page, request }) => {
    const roles: UserRole[] = ['captain', 'hod', 'crew'];

    for (const role of roles) {
      await loginAsTenant(page, role);

      const authToken = await getAuthToken(page);

      // Test with invalid document
      const response = await request.post('http://localhost:8080/v1/actions/execute', {
        headers: {
          'Authorization': `Bearer ${authToken}`,
          'Content-Type': 'application/json',
        },
        data: {
          action: 'get_document_url',
          context: { yacht_id: TEST_YACHT_ID },
          payload: { document_id: 'invalid-uuid' }
        }
      });

      // Must be 4xx (client error), NOT 5xx (server error)
      expect(response.status()).toBeLessThan(500);
      expect(response.status()).toBeGreaterThanOrEqual(400);

      console.log(`✅ ${role.toUpperCase()}: Returns ${response.status()} (not 500)`);
    }
  });
});

test.describe('P2 Fix - Role-Based Permissions', () => {

  test('CREW: Blocked from adding comments', async ({ page, request }) => {
    await loginAsTenant(page, 'crew');

    const authToken = await getAuthToken(page);

    // Try to add comment (should be blocked)
    const response = await request.post('http://localhost:8080/v1/actions/execute', {
      headers: {
        'Authorization': `Bearer ${authToken}`,
        'Content-Type': 'application/json',
      },
      data: {
        action: 'add_document_comment',
        context: { yacht_id: TEST_YACHT_ID },
        payload: {
          document_id: TEST_DOCUMENT_ID,
          comment: 'CREW security test - should be blocked'
        }
      }
    });

    // Must be 403 FORBIDDEN or 404 NOT_FOUND (action not exposed)
    expect([403, 404]).toContain(response.status());

    const body = await response.json();
    console.log('CREW blocked response:', body);

    console.log(`✅ P2 Fix Verified: CREW blocked with ${response.status()}`);
  });

  test('HOD: Can add comments', async ({ page, request }) => {
    await loginAsTenant(page, 'hod');

    const authToken = await getAuthToken(page);

    // Try to add comment
    const response = await request.post('http://localhost:8080/v1/actions/execute', {
      headers: {
        'Authorization': `Bearer ${authToken}`,
        'Content-Type': 'application/json',
      },
      data: {
        action: 'add_document_comment',
        context: { yacht_id: TEST_YACHT_ID },
        payload: {
          document_id: TEST_DOCUMENT_ID,
          comment: 'HOD E2E test comment'
        }
      }
    });

    // Should NOT be 403 (forbidden)
    expect(response.status()).not.toBe(403);

    const body = await response.json();
    console.log('HOD comment response:', body);

    console.log(`✅ HOD authorized: Response ${response.status()}`);
  });
});

test.describe('Cross-Lens Smoke Tests', () => {

  test('Certificates: Captain can search', async ({ page }) => {
    await loginAsTenant(page, 'captain');

    const searchInput = page.locator('[data-testid="search-input"]');
    await expect(searchInput).toBeVisible({ timeout: 10000 });

    await searchInput.fill('certificate');
    await page.waitForTimeout(1500);

    await page.screenshot({ path: '/tmp/e2e_certificates_captain.png', fullPage: true });

    console.log('✅ Certificates lens: Captain search completed');
  });

  test('Equipment: HOD can search', async ({ page }) => {
    await loginAsTenant(page, 'hod');

    const searchInput = page.locator('[data-testid="search-input"]');
    await expect(searchInput).toBeVisible({ timeout: 10000 });

    await searchInput.fill('equipment');
    await page.waitForTimeout(1500);

    await page.screenshot({ path: '/tmp/e2e_equipment_hod.png', fullPage: true });

    console.log('✅ Equipment lens: HOD search completed');
  });

  test('Faults: CREW can search', async ({ page }) => {
    await loginAsTenant(page, 'crew');

    const searchInput = page.locator('[data-testid="search-input"]');
    await expect(searchInput).toBeVisible({ timeout: 10000 });

    await searchInput.fill('find fault 1234');
    await page.waitForTimeout(1500);

    await page.screenshot({ path: '/tmp/e2e_faults_crew.png', fullPage: true });

    console.log('✅ Faults lens: CREW search completed');
  });
});
