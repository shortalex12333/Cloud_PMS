import { test as base, expect, Page, BrowserContext } from '@playwright/test';
import * as path from 'path';

/**
 * CelesteOS Test Fixtures
 *
 * Provides reusable test utilities and authenticated contexts for different user roles.
 * LAW 12: All fixtures include deep verification helpers for UI rendering.
 */

// Test configuration
export const TEST_CONFIG = {
  yachtId: process.env.TEST_YACHT_ID || '85fe1119-b04c-41ac-80f1-829d23322598',
  baseUrl: process.env.E2E_BASE_URL || 'https://app.celeste7.ai',
  apiUrl: process.env.E2E_API_URL || 'https://celeste-pipeline-v1.onrender.com',
};

// User roles with their auth state paths
const AUTH_STATES = {
  hod: path.join(__dirname, '../playwright/.auth/hod.json'),
  crew: path.join(__dirname, '../playwright/.auth/crew.json'),
  captain: path.join(__dirname, '../playwright/.auth/captain.json'),
};

// Extended test fixture with role-based contexts
type CelesteFixtures = {
  hodPage: Page;
  crewPage: Page;
  captainPage: Page;
  searchAndVerify: (query: string, expectedResults: number) => Promise<void>;
  openResultAndVerifyDrawer: (resultIndex: number, expectedEntityType: string) => Promise<void>;
  verifyDocumentLoads: (documentId: string) => Promise<{ status: number; contentType: string }>;
  verifySignedUrlAccessible: (url: string) => Promise<boolean>;
};

/**
 * Base test fixture with all CelesteOS utilities
 */
export const test = base.extend<CelesteFixtures>({
  // HOD (Head of Department) authenticated page
  hodPage: async ({ browser }, use) => {
    const context = await browser.newContext({ storageState: AUTH_STATES.hod });
    const page = await context.newPage();
    await use(page);
    await context.close();
  },

  // Crew authenticated page
  crewPage: async ({ browser }, use) => {
    const context = await browser.newContext({ storageState: AUTH_STATES.crew });
    const page = await context.newPage();
    await use(page);
    await context.close();
  },

  // Captain authenticated page
  captainPage: async ({ browser }, use) => {
    const context = await browser.newContext({ storageState: AUTH_STATES.captain });
    const page = await context.newPage();
    await use(page);
    await context.close();
  },

  // Search and verify results count
  searchAndVerify: async ({ page }, use) => {
    const searchAndVerify = async (query: string, expectedMinResults: number) => {
      // Wait for bootstrap to complete (yacht context must be loaded)
      await page.waitForSelector('text=✓ yacht:', { timeout: 10_000 });

      // GHOST TYPIST DEFENSE: Click to focus, wait for UI stabilization, then fill
      const searchInput = page.getByTestId('search-input');
      await searchInput.click();
      await page.waitForTimeout(200); // Mechanical sympathy: let React re-render
      await searchInput.fill(query);

      // Wait for results to load
      await page.waitForTimeout(2500); // Debounce (80ms) + SSE API (~1-2s)

      // Verify results container appears
      const resultsContainer = page.getByTestId('search-results-grouped');
      await expect(resultsContainer).toBeVisible({ timeout: 10_000 });

      // Count result rows (each result has a specific structure)
      const resultRows = resultsContainer.locator('[data-testid="search-result-item"]');
      const count = await resultRows.count();

      expect(count).toBeGreaterThanOrEqual(expectedMinResults);
    };

    await use(searchAndVerify);
  },

  // Open a result and verify the context panel drawer opens
  openResultAndVerifyDrawer: async ({ page }, use) => {
    const openResultAndVerifyDrawer = async (resultIndex: number, expectedEntityType: string) => {
      // Click the result
      const resultRows = page.getByTestId('search-results-grouped').locator('[data-testid="search-result-item"]');
      await resultRows.nth(resultIndex).click();

      // Wait for context panel to slide in
      const contextPanel = page.getByTestId('context-panel');
      await expect(contextPanel).toBeVisible({ timeout: 10_000 });

      // Verify entity type
      const entityType = await contextPanel.getAttribute('data-entity-type');
      expect(entityType).toBe(expectedEntityType);

      // LAW 12: Verify the panel has actual content (not empty or error)
      const contentArea = contextPanel.getByTestId('context-panel-content');
      await expect(contentArea).toBeVisible({ timeout: 5_000 });

      // Ensure no error state
      const errorState = contextPanel.getByTestId('context-panel-error');
      await expect(errorState).not.toBeVisible();
    };

    await use(openResultAndVerifyDrawer);
  },

  // LAW 12: Verify document actually loads via signed URL
  verifyDocumentLoads: async ({ page, request }, use) => {
    const verifyDocumentLoads = async (documentId: string) => {
      // Make API request for signed URL
      const response = await request.get(
        `${TEST_CONFIG.apiUrl}/api/documents/${documentId}/signed-url`,
        {
          headers: {
            'Authorization': `Bearer ${await getAuthToken(page)}`,
          },
        }
      );

      expect(response.ok()).toBe(true);

      const data = await response.json();
      const signedUrl = data.signed_url || data.signedUrl;

      expect(signedUrl).toBeTruthy();

      // Verify the signed URL is accessible
      const fileResponse = await request.get(signedUrl);

      return {
        status: fileResponse.status(),
        contentType: fileResponse.headers()['content-type'] || 'unknown',
      };
    };

    await use(verifyDocumentLoads);
  },

  // Verify a signed URL is accessible (returns 200)
  verifySignedUrlAccessible: async ({ request }, use) => {
    const verifySignedUrlAccessible = async (url: string) => {
      try {
        const response = await request.head(url);
        return response.status() === 200;
      } catch {
        return false;
      }
    };

    await use(verifySignedUrlAccessible);
  },
});

/**
 * Helper to extract auth token from page context
 */
async function getAuthToken(page: Page): Promise<string> {
  const cookies = await page.context().cookies();
  const authCookie = cookies.find(c => c.name.includes('supabase-auth-token'));

  if (authCookie) {
    return authCookie.value;
  }

  // Fallback: Get from localStorage
  const token = await page.evaluate(() => {
    const stored = localStorage.getItem('sb-auth-token');
    return stored ? JSON.parse(stored).access_token : null;
  });

  return token || '';
}

/**
 * Common test assertions
 */
export { expect };

/**
 * Test data generators
 */
export const TestData = {
  // Known search queries that should return results
  searches: {
    equipment: 'engine',
    workOrder: 'maintenance',
    document: 'certificate',
    fault: 'leak',
    part: 'filter',
    manual: 'operation manual',
  },

  // Adversarial queries (should NOT crash the system)
  adversarial: {
    empty: '',
    whitespace: '   ',
    unicode: '水maker',  // "watermaker" with Chinese character for water
    injection: "'; DROP TABLE search_index; --",
    xss: '<script>alert("xss")</script>',
    longQuery: 'a'.repeat(500),
    specialChars: '!@#$%^&*()_+-=[]{}|;:",.<>?/',
  },

  // Known entity IDs for the test yacht
  entities: {
    yachtId: TEST_CONFIG.yachtId,
    // These would be populated from actual test data
    workOrderId: null as string | null,
    equipmentId: null as string | null,
    documentId: null as string | null,
  },
};

/**
 * Page Object helpers
 */
export class SpotlightSearchPO {
  constructor(private page: Page) {}

  get searchInput() {
    return this.page.getByTestId('search-input');
  }

  get resultsContainer() {
    return this.page.getByTestId('search-results-grouped');
  }

  get noResults() {
    return this.page.getByTestId('no-results');
  }

  get emailButton() {
    return this.page.getByTestId('utility-email-button');
  }

  async search(query: string): Promise<void> {
    // Wait for bootstrap to complete (yacht context must be loaded)
    await this.page.waitForSelector('text=✓ yacht:', { timeout: 10_000 });

    // GHOST TYPIST DEFENSE: Click to focus, wait for UI to stabilize, then fill
    // This ensures React state updates complete before Playwright types
    await this.searchInput.click();
    await this.page.waitForTimeout(200); // Mechanical sympathy: let React re-render
    await this.searchInput.fill(query);
    await this.page.waitForTimeout(2500); // Wait for debounce (80ms) + SSE API (~1-2s)
  }

  async getResultCount(): Promise<number> {
    // Match the actual component: data-testid="search-result-item"
    const results = this.resultsContainer.locator('[data-testid="search-result-item"]');
    return results.count();
  }

  async clickResult(index: number): Promise<void> {
    const results = this.resultsContainer.locator('[data-testid="search-result-item"]');
    await results.nth(index).click();
  }
}

export class ContextPanelPO {
  constructor(private page: Page) {}

  get panel() {
    return this.page.getByTestId('context-panel');
  }

  get content() {
    return this.page.getByTestId('context-panel-content');
  }

  get loading() {
    return this.page.getByTestId('context-panel-loading');
  }

  get error() {
    return this.page.getByTestId('context-panel-error');
  }

  async waitForContent(): Promise<void> {
    await this.panel.waitFor({ state: 'visible' });
    await this.content.waitFor({ state: 'visible', timeout: 10_000 });
  }

  async getEntityType(): Promise<string | null> {
    return this.panel.getAttribute('data-entity-type');
  }

  async getEntityId(): Promise<string | null> {
    return this.panel.getAttribute('data-entity-id');
  }

  async close(): Promise<void> {
    // Press Escape key to close panel
    await this.page.keyboard.press('Escape');
    // Wait for panel to be hidden (check data-visible attribute)
    await this.page.waitForFunction(
      () => {
        const panel = document.querySelector('[data-testid="context-panel"]');
        return !panel || panel.getAttribute('data-visible') === 'false';
      },
      { timeout: 10000 }
    );
  }
}

export class DocumentViewerPO {
  constructor(private page: Page) {}

  get overlay() {
    return this.page.getByTestId('document-viewer-overlay');
  }

  async waitForLoad(): Promise<void> {
    await this.overlay.waitFor({ state: 'visible' });
    // Wait for either PDF object or image to load
    await this.page.waitForFunction(() => {
      const pdf = document.querySelector('object[type="application/pdf"]');
      const img = document.querySelector('[data-testid="document-viewer-overlay"] img');
      return pdf || img;
    }, { timeout: 15_000 });
  }

  async close(): Promise<void> {
    await this.page.keyboard.press('Escape');
    await this.overlay.waitFor({ state: 'hidden' });
  }
}
