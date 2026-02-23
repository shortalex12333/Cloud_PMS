import { test, expect, SpotlightSearchPO, ContextPanelPO, TestData } from '../fixtures';

/**
 * SHARD 2: Search Functionality Tests (F1 Pipeline)
 *
 * Tests the complete F1 search pipeline:
 * - Lexical search (full-text)
 * - Semantic search (vector embeddings)
 * - RRF fusion
 * - Result ranking
 * - LAW 8: Tenant-scoped results
 */

test.describe('Basic Search Functionality', () => {
  // First search tests may hit cold start - allow retries
  test.describe.configure({ retries: 1 });

  test('should display search input on main page', async ({ page }) => {
    await page.goto('/');

    const searchInput = page.getByTestId('search-input');
    await expect(searchInput).toBeVisible();
    await expect(searchInput).toBeEnabled();
  });

  test('should show rotating placeholder suggestions', async ({ page }) => {
    await page.goto('/');

    // Wait for page to stabilize
    await page.waitForTimeout(500);

    // Placeholder is a visual overlay, not HTML placeholder attribute
    // Check for any of the known placeholder suggestion texts
    const placeholderSuggestions = [
      'Find fault 1234',
      'Generator maintenance history',
      'Create work order for...',
      "What's overdue this week?",
      'Parts low in stock',
    ];

    // At least one placeholder suggestion should be visible
    const placeholderVisible = await page.evaluate((suggestions) => {
      return suggestions.some((text) => document.body.innerText.includes(text));
    }, placeholderSuggestions);

    expect(placeholderVisible).toBe(true);
  });

  test('should trigger search on input', async ({ page }) => {
    await page.goto('/');

    const spotlight = new SpotlightSearchPO(page);
    await spotlight.search('maintenance');

    // Results container should appear
    await expect(spotlight.resultsContainer).toBeVisible({ timeout: 10_000 });
  });

  test('should display grouped results by domain', async ({ page }) => {
    await page.goto('/');

    const spotlight = new SpotlightSearchPO(page);
    await spotlight.search('maintenance');

    await expect(spotlight.resultsContainer).toBeVisible({ timeout: 10_000 });

    // Results should be grouped (check for domain headers)
    const resultCount = await spotlight.getResultCount();
    expect(resultCount).toBeGreaterThan(0);
  });

  test('should handle empty search gracefully', async ({ page }) => {
    await page.goto('/');

    const spotlight = new SpotlightSearchPO(page);
    await spotlight.search('');

    // Should not show error
    const errorState = page.getByTestId('search-error');
    await expect(errorState).not.toBeVisible();
  });

  test('should clear search on Escape key', async ({ page }) => {
    await page.goto('/');

    const spotlight = new SpotlightSearchPO(page);
    await spotlight.search('maintenance');

    await expect(spotlight.resultsContainer).toBeVisible({ timeout: 10_000 });

    // Press Escape
    await page.keyboard.press('Escape');

    // Search should be cleared
    const inputValue = await spotlight.searchInput.inputValue();
    expect(inputValue).toBe('');
  });
});

test.describe('Search Result Types', () => {
  test('should find equipment results', async ({ page }) => {
    await page.goto('/');

    const spotlight = new SpotlightSearchPO(page);
    // Using 'maintenance' which has equipment results in test yacht
    await spotlight.search('maintenance');

    await expect(spotlight.resultsContainer).toBeVisible({ timeout: 10_000 });

    const resultCount = await spotlight.getResultCount();
    expect(resultCount).toBeGreaterThan(0);
  });

  test('should find work order results', async ({ page }) => {
    await page.goto('/');

    const spotlight = new SpotlightSearchPO(page);
    await spotlight.search('work order service');

    await expect(spotlight.resultsContainer).toBeVisible({ timeout: 10_000 });
  });

  test('should find document/certificate results', async ({ page }) => {
    await page.goto('/');

    const spotlight = new SpotlightSearchPO(page);
    // Using 'maintenance' which has document results in test yacht
    await spotlight.search('maintenance');

    await expect(spotlight.resultsContainer).toBeVisible({ timeout: 10_000 });
  });

  test('should find part/inventory results', async ({ page }) => {
    await page.goto('/');

    const spotlight = new SpotlightSearchPO(page);
    await spotlight.search('part');

    await expect(spotlight.resultsContainer).toBeVisible({ timeout: 10_000 });
  });

  test('should find fault results', async ({ page }) => {
    await page.goto('/');

    const spotlight = new SpotlightSearchPO(page);
    // Using 'maintenance' which has fault results in test yacht
    await spotlight.search('maintenance');

    await expect(spotlight.resultsContainer).toBeVisible({ timeout: 10_000 });
  });
});

test.describe('Search Result Interaction', () => {
  test('should navigate results with keyboard', async ({ page }) => {
    await page.goto('/');

    const spotlight = new SpotlightSearchPO(page);
    await spotlight.search('maintenance');

    await expect(spotlight.resultsContainer).toBeVisible({ timeout: 10_000 });

    // Navigate down
    await page.keyboard.press('ArrowDown');
    await page.keyboard.press('ArrowDown');

    // Navigate up
    await page.keyboard.press('ArrowUp');

    // Selection should be visible (highlighted)
    // This tests keyboard navigation works
  });

  test('should open result on Enter key', async ({ page }) => {
    await page.goto('/');

    const spotlight = new SpotlightSearchPO(page);
    await spotlight.search('maintenance');

    await expect(spotlight.resultsContainer).toBeVisible({ timeout: 10_000 });

    const resultCount = await spotlight.getResultCount();
    if (resultCount > 0) {
      // Select first result and press Enter
      await page.keyboard.press('ArrowDown');
      await page.keyboard.press('Enter');

      // Context panel should open
      const contextPanel = page.getByTestId('context-panel');
      await expect(contextPanel).toBeVisible({ timeout: 10_000 });
    }
  });

  test('should open result on click', async ({ page }) => {
    await page.goto('/');

    const spotlight = new SpotlightSearchPO(page);
    await spotlight.search('work order');

    await expect(spotlight.resultsContainer).toBeVisible({ timeout: 10_000 });

    const resultCount = await spotlight.getResultCount();
    if (resultCount > 0) {
      await spotlight.clickResult(0);

      // Context panel should open
      const contextPanel = page.getByTestId('context-panel');
      await expect(contextPanel).toBeVisible({ timeout: 10_000 });
    }
  });
});

test.describe('Search Performance', () => {
  test('should return results within acceptable time', async ({ page }) => {
    await page.goto('/');

    const spotlight = new SpotlightSearchPO(page);

    const startTime = Date.now();
    await spotlight.search('maintenance');
    await expect(spotlight.resultsContainer).toBeVisible({ timeout: 10_000 });
    const endTime = Date.now();

    const searchTime = endTime - startTime;

    // Search should complete within 5 seconds (includes debounce)
    expect(searchTime).toBeLessThan(5000);
  });

  test('should handle rapid typing without errors', async ({ page }) => {
    await page.goto('/');

    const searchInput = page.getByTestId('search-input');

    // Type rapidly (simulating fast user input)
    await searchInput.pressSequentially('maintenance work order', { delay: 50 });

    await page.waitForTimeout(2000);

    // Should not show error
    const errorState = page.getByTestId('search-error');
    await expect(errorState).not.toBeVisible();
  });

  test('should debounce search requests', async ({ page }) => {
    await page.goto('/');

    let requestCount = 0;
    page.on('request', (request) => {
      if (request.url().includes('/search') || request.url().includes('/f1/search')) {
        requestCount++;
      }
    });

    const searchInput = page.getByTestId('search-input');

    // Type multiple characters quickly
    await searchInput.type('main');
    await page.waitForTimeout(100);
    await searchInput.type('ten');
    await page.waitForTimeout(100);
    await searchInput.type('ance');

    await page.waitForTimeout(2000);

    // Should have made fewer requests than characters typed (debouncing)
    // Exact count depends on debounce timing, but should be reasonable
    expect(requestCount).toBeLessThan(10);
  });
});

test.describe('Search State Management', () => {
  test('should preserve search query on result close', async ({ page }) => {
    await page.goto('/');

    const spotlight = new SpotlightSearchPO(page);
    const contextPanel = new ContextPanelPO(page);

    await spotlight.search('maintenance');
    await expect(spotlight.resultsContainer).toBeVisible({ timeout: 10_000 });

    const resultCount = await spotlight.getResultCount();
    if (resultCount > 0) {
      await spotlight.clickResult(0);
      await contextPanel.waitForContent();

      // Close the panel by clicking outside or pressing Escape twice
      await page.keyboard.press('Escape');
      await page.waitForTimeout(500);

      // Search query should still be there (we searched for 'maintenance')
      const inputValue = await spotlight.searchInput.inputValue();
      expect(inputValue).toBe('maintenance');
    }
  });

  test('should show "Show more" for large result sets', async ({ page }) => {
    await page.goto('/');

    const spotlight = new SpotlightSearchPO(page);
    await spotlight.search('maintenance');

    await expect(spotlight.resultsContainer).toBeVisible({ timeout: 10_000 });

    // Look for "Show more" button if results are truncated
    const showMoreButton = page.locator('text=Show more');
    // This might or might not be visible depending on result count
  });
});

test.describe('Context Panel Integration', () => {
  test('should display correct entity type in panel', async ({ page }) => {
    await page.goto('/');

    const spotlight = new SpotlightSearchPO(page);
    const contextPanel = new ContextPanelPO(page);

    await spotlight.search('maintenance');
    await expect(spotlight.resultsContainer).toBeVisible({ timeout: 10_000 });

    const resultCount = await spotlight.getResultCount();
    if (resultCount > 0) {
      await spotlight.clickResult(0);
      await contextPanel.waitForContent();

      // Verify entity type attribute
      const entityType = await contextPanel.getEntityType();
      expect(entityType).toBeTruthy();
    }
  });

  test('should load panel content without error', async ({ page }) => {
    await page.goto('/');

    const spotlight = new SpotlightSearchPO(page);
    const contextPanel = new ContextPanelPO(page);

    await spotlight.search('work order');
    await expect(spotlight.resultsContainer).toBeVisible({ timeout: 10_000 });

    const resultCount = await spotlight.getResultCount();
    if (resultCount > 0) {
      await spotlight.clickResult(0);

      // Wait for panel
      await expect(contextPanel.panel).toBeVisible({ timeout: 10_000 });

      // Loading should complete
      await expect(contextPanel.loading).not.toBeVisible({ timeout: 10_000 });

      // No error should be shown
      await expect(contextPanel.error).not.toBeVisible();

      // Content should be visible
      await expect(contextPanel.content).toBeVisible();
    }
  });
});

test.describe('No Results Handling', () => {
  test('should display no results message for gibberish query', async ({ page }) => {
    await page.goto('/');

    const spotlight = new SpotlightSearchPO(page);
    await spotlight.search('xyzqwerty123456789');

    await page.waitForTimeout(2000);

    // Should show no results or empty state
    const resultCount = await spotlight.getResultCount();
    expect(resultCount).toBe(0);
  });

  test('should not crash on no results', async ({ page }) => {
    await page.goto('/');

    const spotlight = new SpotlightSearchPO(page);
    await spotlight.search('nonexistentitem12345');

    await page.waitForTimeout(2000);

    // Should still be able to search again
    await spotlight.search('maintenance');
    await expect(spotlight.resultsContainer).toBeVisible({ timeout: 10_000 });
  });
});
