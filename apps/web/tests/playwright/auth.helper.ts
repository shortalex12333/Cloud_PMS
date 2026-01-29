import { Page, expect } from '@playwright/test';

// Test user credentials - loaded from env
export const TEST_USERS = {
  crew: {
    email: process.env.STAGING_CREW_EMAIL || 'crew.test@alex-short.com',
    password: process.env.STAGING_USER_PASSWORD || 'Password2!',
    role: 'crew',
  },
  hod: {
    email: process.env.STAGING_HOD_EMAIL || 'hod.test@alex-short.com',
    password: process.env.STAGING_USER_PASSWORD || 'Password2!',
    role: 'chief_engineer',
  },
  captain: {
    email: process.env.STAGING_CAPTAIN_EMAIL || 'captain.test@alex-short.com',
    password: process.env.STAGING_USER_PASSWORD || 'Password2!',
    role: 'captain',
  },
};

export type UserRole = keyof typeof TEST_USERS;

/**
 * Login to app.celeste7.ai with the specified role
 */
export async function loginAs(page: Page, role: UserRole): Promise<void> {
  const user = TEST_USERS[role];

  // Navigate to login page
  await page.goto('/login');

  // Wait for login form to be visible
  await page.waitForSelector('input[type="email"], input[name="email"]', { timeout: 10000 });

  // Fill credentials
  await page.fill('input[type="email"], input[name="email"]', user.email);
  await page.fill('input[type="password"], input[name="password"]', user.password);

  // Submit login
  await page.click('button[type="submit"]');

  // Wait for redirect to main app (not login page)
  await page.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 15000 });

  // Verify JWT is stored (either localStorage or cookie)
  const hasAuth = await page.evaluate(() => {
    // Check localStorage for Supabase auth token
    const storage = localStorage.getItem('sb-vzsohavtuotocgrfkfyd-auth-token') ||
                    localStorage.getItem('supabase.auth.token');
    return !!storage;
  });

  expect(hasAuth).toBe(true);
}

/**
 * Check if current user has the expected role badge/indicator
 */
export async function verifyUserRole(page: Page, expectedRole: string): Promise<void> {
  // This depends on UI implementation - look for role indicator
  const roleIndicator = page.locator('[data-testid="user-role"], .user-role, [aria-label*="role"]');
  if (await roleIndicator.count() > 0) {
    const text = await roleIndicator.textContent();
    expect(text?.toLowerCase()).toContain(expectedRole.toLowerCase());
  }
}

/**
 * Open the search/spotlight input
 */
export async function openSpotlight(page: Page): Promise<void> {
  // Try different selectors for the search input
  const searchInput = page.locator(
    '[data-testid="search-input"], ' +
    '[data-testid="spotlight-input"], ' +
    'input[placeholder*="Search"], ' +
    'input[placeholder*="search"], ' +
    '.search-input'
  ).first();

  await searchInput.waitFor({ state: 'visible', timeout: 10000 });
  await searchInput.click();
}

/**
 * Type into spotlight and wait for suggestions
 */
export async function searchInSpotlight(page: Page, query: string): Promise<void> {
  await openSpotlight(page);

  const searchInput = page.locator(
    '[data-testid="search-input"], ' +
    '[data-testid="spotlight-input"], ' +
    'input[placeholder*="Search"], ' +
    'input[placeholder*="search"]'
  ).first();

  await searchInput.fill(query);

  // Wait for suggestions to load (debounce + API call)
  await page.waitForTimeout(500);
}

/**
 * Get visible action buttons/suggestions
 */
export async function getActionSuggestions(page: Page): Promise<string[]> {
  // Wait for action suggestions to appear
  await page.waitForSelector(
    '[data-testid="action-button"], ' +
    '[data-testid="suggested-action"], ' +
    '.action-suggestion, ' +
    '.suggested-actions button',
    { timeout: 5000 }
  ).catch(() => null);

  const buttons = page.locator(
    '[data-testid="action-button"], ' +
    '[data-testid="suggested-action"], ' +
    '.action-suggestion'
  );

  const count = await buttons.count();
  const actions: string[] = [];

  for (let i = 0; i < count; i++) {
    const text = await buttons.nth(i).textContent();
    if (text) actions.push(text.trim());
  }

  return actions;
}

/**
 * Click an action button by label
 */
export async function clickAction(page: Page, actionLabel: string): Promise<void> {
  const button = page.locator(
    `[data-testid="action-button"]:has-text("${actionLabel}"), ` +
    `[data-testid="suggested-action"]:has-text("${actionLabel}"), ` +
    `button:has-text("${actionLabel}")`
  ).first();

  await button.click();
}

/**
 * Wait for action modal to appear
 */
export async function waitForActionModal(page: Page): Promise<void> {
  await page.waitForSelector(
    '[data-testid="action-modal"], ' +
    '[role="dialog"], ' +
    '.modal, ' +
    '.action-modal',
    { timeout: 10000 }
  );
}

/**
 * Check if modal shows "Requires Signature" badge
 */
export async function hasSignatureBadge(page: Page): Promise<boolean> {
  const badge = page.locator(
    '[data-testid="signature-badge"], ' +
    ':text("Requires Signature"), ' +
    ':text("requires signature"), ' +
    '.signature-required'
  );

  return await badge.count() > 0;
}

/**
 * Wait for success toast
 */
export async function waitForSuccessToast(page: Page): Promise<void> {
  await page.waitForSelector(
    '[data-testid="toast-success"], ' +
    '.toast-success, ' +
    '[role="alert"]:has-text("success"), ' +
    '.Toastify__toast--success',
    { timeout: 10000 }
  );
}

/**
 * Check browser console for errors
 */
export async function checkConsoleForErrors(page: Page): Promise<string[]> {
  const errors: string[] = [];

  page.on('console', (msg) => {
    if (msg.type() === 'error') {
      errors.push(msg.text());
    }
  });

  return errors;
}
