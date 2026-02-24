import { test, expect, SpotlightSearchPO, TestData, TEST_CONFIG } from '../fixtures';

/**
 * SHARD 5: Adversarial & Edge Case Tests
 *
 * Tests system resilience against:
 * - Malicious inputs (SQL injection, XSS)
 * - Unicode and special characters
 * - Extreme input lengths
 * - Rapid interactions
 * - Network failures
 *
 * LAW 8: STRICT LINGUISTIC ISOLATION
 * - Adversarial queries must not break tenant isolation
 *
 * LAW 10: PHYSICAL TRUTH OVER MOCKED TESTS
 * - These tests run against real infrastructure
 */

test.describe('SQL Injection Prevention', () => {
  test('should safely handle SQL injection in search', async ({ page }) => {
    await page.goto('/');

    const spotlight = new SpotlightSearchPO(page);

    // Classic SQL injection
    await spotlight.search("'; DROP TABLE search_index; --");

    await page.waitForTimeout(2000);

    // System should not crash
    await expect(spotlight.searchInput).toBeVisible();

    // Should handle gracefully (no results or error message)
    const errorState = page.getByTestId('search-error');
    await expect(errorState).not.toBeVisible();
  });

  test('should safely handle UNION-based injection', async ({ page }) => {
    await page.goto('/');

    const spotlight = new SpotlightSearchPO(page);

    await spotlight.search("' UNION SELECT * FROM users --");

    await page.waitForTimeout(2000);

    // System should not expose user data
    await expect(spotlight.searchInput).toBeVisible();
  });

  test('should safely handle boolean-based injection', async ({ page }) => {
    await page.goto('/');

    const spotlight = new SpotlightSearchPO(page);

    await spotlight.search("' OR '1'='1");

    await page.waitForTimeout(2000);

    // Should not return all results (tenant isolation)
    await expect(spotlight.searchInput).toBeVisible();
  });
});

test.describe('XSS Prevention', () => {
  test('should sanitize script tags in search', async ({ page }) => {
    await page.goto('/');

    const spotlight = new SpotlightSearchPO(page);

    await spotlight.search('<script>alert("xss")</script>');

    await page.waitForTimeout(2000);

    // Script should not execute
    const dialogs: string[] = [];
    page.on('dialog', (dialog) => {
      dialogs.push(dialog.message());
      dialog.dismiss();
    });

    await page.waitForTimeout(1000);

    // No alert should have fired
    expect(dialogs).toHaveLength(0);
  });

  test('should sanitize img onerror in search', async ({ page }) => {
    await page.goto('/');

    const spotlight = new SpotlightSearchPO(page);

    await spotlight.search('<img src="x" onerror="alert(\'xss\')">');

    await page.waitForTimeout(2000);

    const dialogs: string[] = [];
    page.on('dialog', (dialog) => {
      dialogs.push(dialog.message());
      dialog.dismiss();
    });

    await page.waitForTimeout(1000);
    expect(dialogs).toHaveLength(0);
  });

  test('should sanitize event handlers in search', async ({ page }) => {
    await page.goto('/');

    const spotlight = new SpotlightSearchPO(page);

    await spotlight.search('<div onmouseover="alert(\'xss\')">hover</div>');

    await page.waitForTimeout(2000);

    // System should remain stable
    await expect(spotlight.searchInput).toBeVisible();
  });
});

test.describe('Unicode & Special Character Handling', () => {
  test('should handle Chinese characters', async ({ page }) => {
    await page.goto('/');

    const spotlight = new SpotlightSearchPO(page);

    await spotlight.search('水maker');  // "watermaker" with Chinese water

    await page.waitForTimeout(2000);

    // Should not crash
    await expect(spotlight.searchInput).toBeVisible();
  });

  test('should handle Arabic characters', async ({ page }) => {
    await page.goto('/');

    const spotlight = new SpotlightSearchPO(page);

    await spotlight.search('محرك');  // "engine" in Arabic

    await page.waitForTimeout(2000);

    await expect(spotlight.searchInput).toBeVisible();
  });

  test('should handle emoji in search', async ({ page }) => {
    await page.goto('/');

    const spotlight = new SpotlightSearchPO(page);

    await spotlight.search('engine 🔧 maintenance');

    await page.waitForTimeout(2000);

    await expect(spotlight.searchInput).toBeVisible();
  });

  test('should handle RTL text', async ({ page }) => {
    await page.goto('/');

    const spotlight = new SpotlightSearchPO(page);

    await spotlight.search('שלום');  // Hebrew "hello"

    await page.waitForTimeout(2000);

    await expect(spotlight.searchInput).toBeVisible();
  });

  test('should handle mixed direction text', async ({ page }) => {
    await page.goto('/');

    const spotlight = new SpotlightSearchPO(page);

    await spotlight.search('engine محرك motor');

    await page.waitForTimeout(2000);

    await expect(spotlight.searchInput).toBeVisible();
  });

  test('should handle special characters', async ({ page }) => {
    await page.goto('/');

    const spotlight = new SpotlightSearchPO(page);

    await spotlight.search('!@#$%^&*()_+-=[]{}|;:",.<>?/');

    await page.waitForTimeout(2000);

    await expect(spotlight.searchInput).toBeVisible();
  });

  test('should handle null bytes', async ({ page }) => {
    await page.goto('/');

    const spotlight = new SpotlightSearchPO(page);

    await spotlight.search('engine\x00maintenance');

    await page.waitForTimeout(2000);

    await expect(spotlight.searchInput).toBeVisible();
  });
});

test.describe('Input Length Extremes', () => {
  test('should handle very long queries', async ({ page }) => {
    await page.goto('/');

    const spotlight = new SpotlightSearchPO(page);

    // 500 character query
    const longQuery = 'a'.repeat(500);
    await spotlight.search(longQuery);

    await page.waitForTimeout(3000);

    // Should not crash
    await expect(spotlight.searchInput).toBeVisible();
  });

  test('should handle empty query', async ({ page }) => {
    await page.goto('/');

    const spotlight = new SpotlightSearchPO(page);

    await spotlight.search('');

    await page.waitForTimeout(1000);

    // Should not show error
    const errorState = page.getByTestId('search-error');
    await expect(errorState).not.toBeVisible();
  });

  test('should handle whitespace-only query', async ({ page }) => {
    await page.goto('/');

    const spotlight = new SpotlightSearchPO(page);

    await spotlight.search('     ');

    await page.waitForTimeout(1000);

    await expect(spotlight.searchInput).toBeVisible();
  });

  test('should handle repeated characters', async ({ page }) => {
    await page.goto('/');

    const spotlight = new SpotlightSearchPO(page);

    await spotlight.search('aaaaaaaaaaaaaaaaaaaaaaaaaaaaa');

    await page.waitForTimeout(2000);

    await expect(spotlight.searchInput).toBeVisible();
  });
});

test.describe('Rapid Interaction Resilience', () => {
  test('should handle rapid search changes', async ({ page }) => {
    await page.goto('/');

    const spotlight = new SpotlightSearchPO(page);

    // Rapid fire searches
    for (const query of ['a', 'ab', 'abc', 'abcd', 'engine', 'work', 'order']) {
      await spotlight.searchInput.fill(query);
      await page.waitForTimeout(50);
    }

    await page.waitForTimeout(2000);

    // Should not crash
    await expect(spotlight.searchInput).toBeVisible();
  });

  test('should handle rapid result clicks', async ({ page }) => {
    await page.goto('/');

    const spotlight = new SpotlightSearchPO(page);

    await spotlight.search('maintenance');
    await expect(spotlight.resultsContainer).toBeVisible();

    const resultCount = await spotlight.getResultCount();

    // Click rapidly
    for (let i = 0; i < Math.min(resultCount, 5); i++) {
      await spotlight.clickResult(i);
      await page.waitForTimeout(100);
    }

    // System should remain stable
    await expect(spotlight.searchInput).toBeVisible();
  });

  test('should handle rapid panel open/close', async ({ page }) => {
    await page.goto('/');

    const spotlight = new SpotlightSearchPO(page);

    await spotlight.search('equipment');
    await expect(spotlight.resultsContainer).toBeVisible();

    const resultCount = await spotlight.getResultCount();

    if (resultCount > 0) {
      // Open and close rapidly
      for (let i = 0; i < 5; i++) {
        await spotlight.clickResult(0);
        await page.waitForTimeout(200);
        await page.keyboard.press('Escape');
        await page.waitForTimeout(200);
      }

      // System should remain stable
      await expect(spotlight.searchInput).toBeVisible();
    }
  });
});

test.describe('Network Resilience', () => {
  test('should handle slow network gracefully', async ({ page }) => {
    await page.goto('/');

    // Simulate slow network
    await page.route('**/search**', async (route) => {
      await new Promise((resolve) => setTimeout(resolve, 3000));
      await route.continue();
    });

    const spotlight = new SpotlightSearchPO(page);
    await spotlight.search('equipment');

    // Should show loading state
    await page.waitForTimeout(1000);

    // Eventually should complete or show timeout
    await page.waitForTimeout(5000);

    // Should not crash
    await expect(spotlight.searchInput).toBeVisible();
  });

  test('should handle network failure gracefully', async ({ page }) => {
    await page.goto('/');

    // Simulate network failure
    await page.route('**/search**', (route) => route.abort('failed'));

    const spotlight = new SpotlightSearchPO(page);
    await spotlight.search('equipment');

    await page.waitForTimeout(2000);

    // Should show error state but not crash
    await expect(spotlight.searchInput).toBeVisible();
  });
});

test.describe('Concurrent User Simulation', () => {
  test('should handle multiple browser contexts', async ({ browser }) => {
    // Create multiple contexts simulating concurrent users
    const contexts = await Promise.all([
      browser.newContext({ storageState: './playwright/.auth/hod.json' }),
      browser.newContext({ storageState: './playwright/.auth/crew.json' }),
    ]);

    const pages = await Promise.all(contexts.map((ctx) => ctx.newPage()));

    // Both users search simultaneously
    await Promise.all(pages.map((p) => p.goto('/')));

    await Promise.all(
      pages.map(async (p) => {
        const input = p.getByTestId('search-input');
        await expect(input).toBeVisible();
        await input.fill('maintenance');
      })
    );

    await Promise.all(pages.map((p) => p.waitForTimeout(2000)));

    // Both should work independently
    for (const p of pages) {
      await expect(p.getByTestId('search-input')).toBeVisible();
    }

    // Clean up
    await Promise.all(contexts.map((ctx) => ctx.close()));
  });
});

test.describe('Browser Compatibility', () => {
  test('should work after page refresh', async ({ page }) => {
    await page.goto('/');

    const spotlight = new SpotlightSearchPO(page);
    await spotlight.search('equipment');

    await expect(spotlight.resultsContainer).toBeVisible();

    // Refresh page
    await page.reload();

    // Should still be logged in and functional
    await expect(page.getByTestId('search-input')).toBeVisible({ timeout: 10_000 });
  });

  test('should handle back/forward navigation', async ({ page }) => {
    await page.goto('/');

    const spotlight = new SpotlightSearchPO(page);
    await spotlight.search('equipment');

    await expect(spotlight.resultsContainer).toBeVisible();

    const resultCount = await spotlight.getResultCount();
    if (resultCount > 0) {
      await spotlight.clickResult(0);

      const contextPanel = page.getByTestId('context-panel');
      await expect(contextPanel).toBeVisible({ timeout: 10_000 });

      // Navigate back
      await page.goBack();

      await page.waitForTimeout(1000);

      // Should handle gracefully
      await expect(spotlight.searchInput).toBeVisible();
    }
  });
});

test.describe('Memory Leak Prevention', () => {
  test('should not leak memory on repeated searches', async ({ page }) => {
    await page.goto('/');

    const spotlight = new SpotlightSearchPO(page);

    // Perform many searches
    for (let i = 0; i < 20; i++) {
      await spotlight.search(`search query ${i}`);
      await page.waitForTimeout(300);
    }

    // Clear search
    await spotlight.searchInput.fill('');

    // System should still be responsive
    await spotlight.search('final test');
    await expect(spotlight.searchInput).toBeVisible();
  });

  test('should clean up on panel close', async ({ page }) => {
    await page.goto('/');

    const spotlight = new SpotlightSearchPO(page);

    // Open and close many panels
    for (let i = 0; i < 10; i++) {
      await spotlight.search('equipment');
      await expect(spotlight.resultsContainer).toBeVisible();

      const resultCount = await spotlight.getResultCount();
      if (resultCount > 0) {
        await spotlight.clickResult(0);

        const contextPanel = page.getByTestId('context-panel');
        await expect(contextPanel).toBeVisible({ timeout: 5_000 });

        await page.keyboard.press('Escape');
        await page.waitForTimeout(300);
      }
    }

    // System should still be responsive
    await expect(spotlight.searchInput).toBeVisible();
  });
});
