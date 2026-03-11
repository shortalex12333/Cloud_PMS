/**
 * Strict Test Helpers for Playwright
 *
 * Utilities for enforcing strict testing standards:
 * 1. Console error detection and failure
 * 2. Double-run verification (tests must pass consecutively)
 * 3. Assertion helpers with strict expectations
 */

import { Page, expect, test } from '@playwright/test';

// ============================================================================
// CONSOLE ERROR TRACKING
// ============================================================================

/**
 * Console error collector for a page.
 * Tracks all console.error messages during test execution.
 */
interface ConsoleErrorCollector {
  errors: string[];
  attach: () => Promise<void>;
  clear: () => void;
}

/**
 * Sets up console error collection for a page.
 * Call at the beginning of your test to start tracking errors.
 *
 * @example
 * ```ts
 * test('my test', async ({ page }) => {
 *   const errorCollector = setupConsoleErrorCollector(page);
 *   await page.goto('/my-page');
 *   // ... test actions ...
 *   await expectNoConsoleErrors(page, errorCollector);
 * });
 * ```
 */
export function setupConsoleErrorCollector(page: Page): ConsoleErrorCollector {
  const errors: string[] = [];

  page.on('console', (msg) => {
    if (msg.type() === 'error') {
      errors.push(`[console.error] ${msg.text()}`);
    }
  });

  page.on('pageerror', (error) => {
    errors.push(`[page error] ${error.message}`);
  });

  return {
    errors,
    attach: async () => {
      if (errors.length > 0) {
        await test.info().attach('console-errors', {
          body: errors.join('\n'),
          contentType: 'text/plain',
        });
      }
    },
    clear: () => {
      errors.length = 0;
    },
  };
}

/**
 * Asserts that no console.error messages occurred during the test.
 * Should be called at the end of each test or after critical operations.
 *
 * @param page - The Playwright page object
 * @param collector - The error collector from setupConsoleErrorCollector
 * @param options - Optional configuration
 * @throws AssertionError if console errors were detected
 *
 * @example
 * ```ts
 * await expectNoConsoleErrors(page, collector);
 * // or with ignored patterns:
 * await expectNoConsoleErrors(page, collector, {
 *   ignorePatterns: [/ResizeObserver/, /favicon/]
 * });
 * ```
 */
export async function expectNoConsoleErrors(
  page: Page,
  collector: ConsoleErrorCollector,
  options?: {
    ignorePatterns?: RegExp[];
  }
): Promise<void> {
  const { ignorePatterns = [] } = options ?? {};

  // Filter out ignored patterns
  const relevantErrors = collector.errors.filter((error) => {
    return !ignorePatterns.some((pattern) => pattern.test(error));
  });

  // Attach errors for reporting even if we're going to ignore some
  await collector.attach();

  if (relevantErrors.length > 0) {
    const errorMessage = [
      'Console errors detected during test execution:',
      '',
      ...relevantErrors.map((e) => `  - ${e}`),
      '',
      'Fix these errors or add them to ignorePatterns if intentional.',
    ].join('\n');

    expect(relevantErrors, errorMessage).toHaveLength(0);
  }
}

/**
 * Quick helper that sets up collection and returns an assertion function.
 * Use this for simpler test setups.
 *
 * @example
 * ```ts
 * test('my test', async ({ page }) => {
 *   const assertNoErrors = withConsoleErrorTracking(page);
 *   await page.goto('/my-page');
 *   // ... test actions ...
 *   await assertNoErrors();
 * });
 * ```
 */
export function withConsoleErrorTracking(
  page: Page,
  options?: { ignorePatterns?: RegExp[] }
): () => Promise<void> {
  const collector = setupConsoleErrorCollector(page);
  return async () => {
    await expectNoConsoleErrors(page, collector, options);
  };
}

// ============================================================================
// DOUBLE-RUN VERIFICATION
// ============================================================================

/**
 * Options for running a test twice consecutively
 */
interface RunTwiceOptions {
  /** Delay between runs in milliseconds (default: 100) */
  delayBetweenRuns?: number;
  /** Whether to reset page state between runs (default: true) */
  resetBetweenRuns?: boolean;
  /** Custom reset function to call between runs */
  customReset?: (page: Page) => Promise<void>;
}

/**
 * Runs a test function twice consecutively to verify determinism.
 * Both runs must pass for the overall test to pass.
 *
 * This is useful for detecting:
 * - Race conditions
 * - State leakage between test runs
 * - Non-deterministic behavior
 * - Flaky timing issues
 *
 * @example
 * ```ts
 * test('stable search results', async ({ page }) => {
 *   await runTwice(page, async () => {
 *     await page.goto('/search');
 *     await page.fill('[data-testid="search-input"]', 'test query');
 *     await page.click('[data-testid="search-button"]');
 *     await expect(page.locator('.result-item')).toHaveCount(10);
 *   });
 * });
 * ```
 */
export async function runTwice(
  page: Page,
  testFn: () => Promise<void>,
  options?: RunTwiceOptions
): Promise<void> {
  const {
    delayBetweenRuns = 100,
    resetBetweenRuns = true,
    customReset,
  } = options ?? {};

  // First run
  await test.step('Run 1 of 2', async () => {
    await testFn();
  });

  // Reset between runs
  if (resetBetweenRuns) {
    if (customReset) {
      await customReset(page);
    } else {
      // Default reset: clear cookies and local storage, but keep auth
      await page.evaluate(() => {
        // Clear session storage
        sessionStorage.clear();
        // Note: We don't clear localStorage as it may contain auth tokens
      });
    }
  }

  // Delay between runs
  if (delayBetweenRuns > 0) {
    await page.waitForTimeout(delayBetweenRuns);
  }

  // Second run
  await test.step('Run 2 of 2', async () => {
    await testFn();
  });
}

/**
 * Creates a test wrapper that automatically runs tests twice.
 * Use this to create a strict test fixture.
 *
 * @example
 * ```ts
 * const strictTest = createStrictTest();
 *
 * strictTest('my deterministic test', async ({ page }) => {
 *   await page.goto('/');
 *   await expect(page).toHaveTitle('My App');
 * });
 * ```
 */
export function createRunTwiceWrapper() {
  return function runTwiceWrapper(
    name: string,
    testFn: (args: { page: Page }) => Promise<void>
  ) {
    return test(name, async ({ page }) => {
      await runTwice(page, async () => {
        await testFn({ page });
      });
    });
  };
}

// ============================================================================
// STRICT ASSERTIONS
// ============================================================================

/**
 * Asserts that an element exists and is visible within a strict timeout.
 * Unlike regular expect, this provides better error messages for debugging.
 */
export async function assertVisible(
  page: Page,
  selector: string,
  options?: {
    timeout?: number;
    description?: string;
  }
): Promise<void> {
  const { timeout = 5000, description } = options ?? {};
  const element = page.locator(selector);
  const desc = description ? ` (${description})` : '';

  await test.step(`Assert visible: ${selector}${desc}`, async () => {
    await expect(element, `Element ${selector} should be visible${desc}`).toBeVisible({
      timeout,
    });
  });
}

/**
 * Asserts that an element does NOT exist on the page.
 * Useful for verifying items are removed or hidden.
 */
export async function assertNotPresent(
  page: Page,
  selector: string,
  options?: {
    timeout?: number;
    description?: string;
  }
): Promise<void> {
  const { timeout = 5000, description } = options ?? {};
  const element = page.locator(selector);
  const desc = description ? ` (${description})` : '';

  await test.step(`Assert not present: ${selector}${desc}`, async () => {
    await expect(element, `Element ${selector} should not exist${desc}`).toHaveCount(0, {
      timeout,
    });
  });
}

/**
 * Waits for network idle with strict timeout.
 * Ensures all pending requests complete before proceeding.
 */
export async function waitForNetworkSettled(
  page: Page,
  options?: {
    timeout?: number;
    idleTime?: number;
  }
): Promise<void> {
  const { timeout = 10000, idleTime = 500 } = options ?? {};

  await test.step('Wait for network settled', async () => {
    await page.waitForLoadState('networkidle', { timeout });
    // Extra safety margin
    await page.waitForTimeout(idleTime);
  });
}

// ============================================================================
// STRICT TEST FIXTURE
// ============================================================================

/**
 * Creates a strict test context with all helpers pre-configured.
 * This is the recommended way to use strict testing in your tests.
 *
 * @example
 * ```ts
 * import { createStrictTestContext } from './strict-helpers';
 *
 * test('my strict test', async ({ page }) => {
 *   const ctx = createStrictTestContext(page);
 *
 *   await page.goto('/');
 *   // ... test actions ...
 *
 *   await ctx.assertNoConsoleErrors();
 * });
 * ```
 */
export function createStrictTestContext(
  page: Page,
  options?: {
    ignoreConsolePatterns?: RegExp[];
  }
) {
  const collector = setupConsoleErrorCollector(page);

  return {
    /**
     * Assert no console errors have occurred
     */
    assertNoConsoleErrors: async () => {
      await expectNoConsoleErrors(page, collector, {
        ignorePatterns: options?.ignoreConsolePatterns,
      });
    },

    /**
     * Run a test function twice
     */
    runTwice: async (fn: () => Promise<void>, opts?: RunTwiceOptions) => {
      await runTwice(page, fn, opts);
    },

    /**
     * Clear collected errors (use sparingly)
     */
    clearErrors: () => {
      collector.clear();
    },

    /**
     * Get current error count
     */
    getErrorCount: () => collector.errors.length,

    /**
     * Assert element visible
     */
    assertVisible: async (selector: string, description?: string) => {
      await assertVisible(page, selector, { description });
    },

    /**
     * Assert element not present
     */
    assertNotPresent: async (selector: string, description?: string) => {
      await assertNotPresent(page, selector, { description });
    },

    /**
     * Wait for network to settle
     */
    waitForNetworkSettled: async () => {
      await waitForNetworkSettled(page);
    },
  };
}

// ============================================================================
// EXPORTS
// ============================================================================

export type {
  ConsoleErrorCollector,
  RunTwiceOptions,
};
