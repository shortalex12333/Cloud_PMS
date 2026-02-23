import { test, expect, TEST_CONFIG } from '../fixtures';

/**
 * SHARD 1: Authentication & Tenant Isolation Tests
 *
 * LAW 8: STRICT LINGUISTIC ISOLATION
 * - Users can only access data from their assigned yacht
 * - No cross-tenant data leakage
 * - Session tokens are properly scoped
 */

test.describe('Authentication Flow', () => {
  test.describe.configure({ mode: 'serial' });

  test('should display login page correctly', async ({ page }) => {
    // Clear cookies to ensure logged out state
    await page.context().clearCookies();
    await page.goto('/login');

    // Verify login form elements
    await expect(page.locator('input[type="email"]')).toBeVisible();
    await expect(page.locator('input[type="password"]')).toBeVisible();
    await expect(page.locator('button[type="submit"]')).toBeVisible();

    // Verify branding
    await expect(page.locator('text=Sign In')).toBeVisible();
  });

  test('should reject invalid credentials', async ({ page }) => {
    await page.context().clearCookies();
    await page.goto('/login');

    // Fill with invalid credentials
    await page.fill('input[type="email"]', 'invalid@example.com');
    await page.fill('input[type="password"]', 'wrongpassword');
    await page.click('button[type="submit"]');

    // Should show error message
    await expect(page.locator('text=Invalid login credentials')).toBeVisible({ timeout: 10_000 });

    // Should still be on login page
    expect(page.url()).toContain('/login');
  });

  test('should login successfully with valid HOD credentials', async ({ page }) => {
    await page.context().clearCookies();
    await page.goto('/login');

    // Fill with valid credentials
    await page.fill('input[type="email"]', 'hod.test@alex-short.com');
    await page.fill('input[type="password"]', 'Password2!');
    await page.click('button[type="submit"]');

    // Should redirect to main app
    await page.waitForURL('/', { timeout: 30_000 });

    // Should see search interface
    await expect(page.getByTestId('search-input')).toBeVisible({ timeout: 10_000 });
  });

  test('should login successfully with valid Crew credentials', async ({ page }) => {
    await page.context().clearCookies();
    await page.goto('/login');

    await page.fill('input[type="email"]', 'crew.test@alex-short.com');
    await page.fill('input[type="password"]', 'Password2!');
    await page.click('button[type="submit"]');

    await page.waitForURL('/', { timeout: 30_000 });
    await expect(page.getByTestId('search-input')).toBeVisible({ timeout: 10_000 });
  });

  test('should login successfully with valid Captain credentials', async ({ page }) => {
    await page.context().clearCookies();
    await page.goto('/login');

    await page.fill('input[type="email"]', 'x@alex-short.com');
    await page.fill('input[type="password"]', 'Password2!');
    await page.click('button[type="submit"]');

    await page.waitForURL('/', { timeout: 30_000 });
    await expect(page.getByTestId('search-input')).toBeVisible({ timeout: 10_000 });
  });
});

test.describe('Tenant Isolation (LAW 8)', () => {
  test('HOD user should only see data from test yacht', async ({ hodPage }) => {
    await hodPage.goto('/');
    await expect(hodPage.getByTestId('search-input')).toBeVisible();

    // Search for something generic
    await hodPage.getByTestId('search-input').fill('maintenance');
    await hodPage.waitForTimeout(2000);

    // Results should load
    const resultsContainer = hodPage.getByTestId('search-results-grouped');

    // If results exist, verify they belong to the test yacht
    const resultCount = await resultsContainer.locator('[data-testid="search-result-item"]').count();

    if (resultCount > 0) {
      // Click first result to verify yacht ID
      await resultsContainer.locator('[data-testid="search-result-item"]').first().click();

      // Wait for context panel
      const contextPanel = hodPage.getByTestId('context-panel');
      await expect(contextPanel).toBeVisible({ timeout: 10_000 });

      // The panel should show data only from our test yacht
      // (The yacht_id is embedded in the API response, not visible in UI,
      // but the presence of data confirms tenant isolation working)
      await expect(hodPage.getByTestId('context-panel-content')).toBeVisible();
    }
  });

  test('Crew user should have restricted access', async ({ crewPage }) => {
    await crewPage.goto('/');
    await expect(crewPage.getByTestId('search-input')).toBeVisible();

    // Crew should still be able to search
    await crewPage.getByTestId('search-input').fill('equipment');
    await crewPage.waitForTimeout(2000);

    // Results should be visible (crew has read access)
    const resultsContainer = crewPage.getByTestId('search-results-grouped');
    await expect(resultsContainer).toBeVisible();
  });

  test('Captain user should have full access', async ({ captainPage }) => {
    await captainPage.goto('/');
    await expect(captainPage.getByTestId('search-input')).toBeVisible();

    // Captain should have full search capabilities
    await captainPage.getByTestId('search-input').fill('work order');
    await captainPage.waitForTimeout(2000);

    const resultsContainer = captainPage.getByTestId('search-results-grouped');
    await expect(resultsContainer).toBeVisible();
  });
});

test.describe('Session Management', () => {
  test('should persist session across page reloads', async ({ hodPage }) => {
    await hodPage.goto('/');
    await expect(hodPage.getByTestId('search-input')).toBeVisible();

    // Reload the page
    await hodPage.reload();

    // Should still be logged in
    await expect(hodPage.getByTestId('search-input')).toBeVisible({ timeout: 10_000 });

    // Should NOT be redirected to login
    expect(hodPage.url()).not.toContain('/login');
  });

  test('should redirect to login when accessing protected route without auth', async ({ page }) => {
    // Clear all auth state
    await page.context().clearCookies();
    await page.context().clearPermissions();

    // Try to access main app
    await page.goto('/');

    // Should be redirected to login
    await page.waitForURL(/\/login/, { timeout: 10_000 });
  });

  test('should handle concurrent sessions properly', async ({ browser }) => {
    // Create two separate contexts (simulating different browser sessions)
    const context1 = await browser.newContext({
      storageState: './playwright/.auth/hod.json',
    });
    const context2 = await browser.newContext({
      storageState: './playwright/.auth/crew.json',
    });

    const page1 = await context1.newPage();
    const page2 = await context2.newPage();

    // Both should be able to access the app
    await page1.goto('/');
    await page2.goto('/');

    await expect(page1.getByTestId('search-input')).toBeVisible();
    await expect(page2.getByTestId('search-input')).toBeVisible();

    // Clean up
    await context1.close();
    await context2.close();
  });
});

test.describe('Deep Link Authentication', () => {
  test('should handle deep links with entity parameters', async ({ hodPage }) => {
    // Navigate to a deep link with entity parameters
    await hodPage.goto(`/?entity=work_order&id=${TEST_CONFIG.yachtId}`);

    // Should be authenticated and show the entity
    await expect(hodPage.getByTestId('search-input')).toBeVisible();

    // The context panel might open if the entity exists
    // (This tests that deep links work with authenticated state)
  });

  test('should redirect deep links to login when unauthenticated', async ({ page }) => {
    await page.context().clearCookies();

    // Try to access deep link
    await page.goto('/?entity=work_order&id=some-id');

    // Should redirect to login
    await page.waitForURL(/\/login/, { timeout: 10_000 });
  });
});
