/**
 * Long-Tail Human Behavior Tests
 * ================================
 *
 * CRITICAL: Real users don't follow happy paths.
 *
 * These tests cover edge cases that emerge from:
 * - Rapid clicking
 * - Network interruptions
 * - Unexpected navigation
 * - Real-world input patterns
 *
 * RULE: If a user can do it, the system must handle it.
 */

import { test, expect, Page } from '@playwright/test';

// =============================================================================
// RAPID INTERACTION TESTS
// =============================================================================

test.describe('Rapid Clicking Behaviors', () => {

  test('double-click on link button does not create duplicate links', async ({ page }) => {
    // Scenario: User panic-clicks the link button
    await page.goto('/app');
    await page.waitForSelector('[data-testid="email-list"]');

    // Select an email
    await page.click('[data-testid="email-item"]:first-child');

    // Get the link button
    const linkButton = page.locator('[data-testid="link-button"]');

    // Double-click rapidly
    await linkButton.dblclick();

    // Wait for any pending requests
    await page.waitForTimeout(500);

    // Check that only one link was created
    const linkedIndicators = page.locator('[data-testid="linked-indicator"]');
    await expect(linkedIndicators).toHaveCount(1);
  });

  test('rapid undo-redo does not corrupt state', async ({ page }) => {
    await page.goto('/app');
    await page.waitForSelector('[data-testid="email-list"]');

    // Create a link
    await page.click('[data-testid="email-item"]:first-child');
    await page.click('[data-testid="link-button"]');

    // Rapidly click undo
    const undoButton = page.locator('[data-testid="undo-button"]');
    for (let i = 0; i < 5; i++) {
      await undoButton.click({ delay: 50 });
    }

    // State should be consistent (either linked or not, not corrupted)
    const emailItem = page.locator('[data-testid="email-item"]:first-child');
    const hasLinked = await emailItem.getAttribute('data-linked');

    // Should be either "true" or "false", not undefined or error state
    expect(['true', 'false', null]).toContain(hasLinked);
  });

  test('clicking suggestion while previous suggestion is processing', async ({ page }) => {
    await page.goto('/app');
    await page.waitForSelector('[data-testid="suggestions-panel"]');

    const suggestions = page.locator('[data-testid="suggestion-item"]');
    const count = await suggestions.count();

    if (count >= 2) {
      // Click first suggestion
      await suggestions.nth(0).click();

      // Immediately click second suggestion (before first completes)
      await suggestions.nth(1).click();

      // Wait for processing
      await page.waitForTimeout(1000);

      // No error state should appear
      await expect(page.locator('[data-testid="error-message"]')).not.toBeVisible();
    }
  });

});

// =============================================================================
// NAVIGATION INTERRUPTION TESTS
// =============================================================================

test.describe('Navigation During Operations', () => {

  test('navigating away during sync does not lose data', async ({ page }) => {
    await page.goto('/app');

    // Start a sync (if button exists)
    const syncButton = page.locator('[data-testid="sync-button"]');
    if (await syncButton.isVisible()) {
      await syncButton.click();

      // Navigate away immediately
      await page.goto('/settings');

      // Navigate back
      await page.goto('/app');

      // Should not show error state
      await expect(page.locator('[data-testid="sync-error"]')).not.toBeVisible();
    }
  });

  test('back button during link creation reverts cleanly', async ({ page }) => {
    await page.goto('/app');
    await page.waitForSelector('[data-testid="email-list"]');

    // Start linking an email
    await page.click('[data-testid="email-item"]:first-child');
    await page.click('[data-testid="link-button"]');

    // Press browser back before confirmation
    await page.goBack();

    // Navigate forward
    await page.goForward();

    // State should be clean (either linked or not, no partial state)
    await expect(page.locator('[data-testid="partial-link-state"]')).not.toBeVisible();
  });

  test('closing browser tab during operation does not corrupt', async ({ page, context }) => {
    await page.goto('/app');
    await page.waitForSelector('[data-testid="email-list"]');

    // Start an operation
    await page.click('[data-testid="email-item"]:first-child');
    await page.click('[data-testid="link-button"]');

    // Open new tab and close original (simulating tab close)
    const newPage = await context.newPage();
    await page.close();

    // Open fresh in new tab
    await newPage.goto('/app');

    // Should load without errors
    await expect(newPage.locator('[data-testid="app-error"]')).not.toBeVisible();
  });

});

// =============================================================================
// NETWORK INTERRUPTION TESTS
// =============================================================================

test.describe('Offline and Network Issues', () => {

  test('operation during network failure shows appropriate message', async ({ page }) => {
    await page.goto('/app');
    await page.waitForSelector('[data-testid="email-list"]');

    // Go offline
    await page.context().setOffline(true);

    // Try to link
    await page.click('[data-testid="email-item"]:first-child');
    await page.click('[data-testid="link-button"]');

    // Should show user-friendly error, not technical message
    const errorMessage = page.locator('[data-testid="user-message"]');
    await expect(errorMessage).toBeVisible();

    const text = await errorMessage.textContent();
    // Should not contain technical jargon
    expect(text).not.toContain('NetworkError');
    expect(text).not.toContain('ECONNREFUSED');
    expect(text).not.toContain('undefined');

    // Go back online
    await page.context().setOffline(false);
  });

  test('slow network shows loading state, not frozen UI', async ({ page }) => {
    await page.goto('/app');

    // Throttle network to very slow
    const client = await page.context().newCDPSession(page);
    await client.send('Network.emulateNetworkConditions', {
      offline: false,
      downloadThroughput: 50 * 1024 / 8, // 50kbps
      uploadThroughput: 50 * 1024 / 8,
      latency: 2000, // 2 second latency
    });

    // Navigate to app
    await page.goto('/app');

    // Should show loading state
    const skeleton = page.locator('[data-testid="skeleton-loader"]');
    await expect(skeleton).toBeVisible();

    // Should not show frozen/blank state
    await expect(page.locator('[data-testid="blank-state"]')).not.toBeVisible();
  });

  test('request timeout shows cached data with warning', async ({ page }) => {
    await page.goto('/app');
    await page.waitForSelector('[data-testid="email-list"]');

    // Create artificial timeout by blocking API
    await page.route('**/api/email/**', async route => {
      await new Promise(resolve => setTimeout(resolve, 20000)); // Long delay
      await route.abort();
    });

    // Trigger refresh
    await page.click('[data-testid="refresh-button"]');

    // Should show stale data warning
    await expect(page.locator('[data-testid="stale-warning"]')).toBeVisible({ timeout: 10000 });

    // But data should still be visible (cached)
    await expect(page.locator('[data-testid="email-item"]')).toBeVisible();
  });

});

// =============================================================================
// REAL-WORLD INPUT PATTERNS
// =============================================================================

test.describe('Real-World Input Behaviors', () => {

  test('search with special characters does not crash', async ({ page }) => {
    await page.goto('/app');

    const searchInput = page.locator('[data-testid="search-input"]');

    // Test various special character inputs
    const specialInputs = [
      '"; DROP TABLE emails; --',  // SQL injection attempt
      '<script>alert(1)</script>', // XSS attempt
      'WO-1234 & PO-5678',         // Ampersand
      'test@example.com',          // Email
      '日本語',                     // Japanese
      '🚢⚓',                       // Emoji
      'query with\nnewline',       // Newline
      '',                          // Empty
      '   ',                       // Whitespace only
    ];

    for (const input of specialInputs) {
      await searchInput.fill(input);
      await page.keyboard.press('Enter');

      // Should not show error
      await expect(page.locator('[data-testid="search-error"]')).not.toBeVisible();

      // Should show either results or "no results" message
      const hasResults = await page.locator('[data-testid="search-results"]').isVisible();
      const hasNoResults = await page.locator('[data-testid="no-results"]').isVisible();
      expect(hasResults || hasNoResults).toBeTruthy();

      await searchInput.clear();
    }
  });

  test('pasting large text into search is handled', async ({ page }) => {
    await page.goto('/app');

    const searchInput = page.locator('[data-testid="search-input"]');

    // Generate very long search query
    const longQuery = 'a'.repeat(10000);

    await searchInput.fill(longQuery);
    await page.keyboard.press('Enter');

    // Should not crash, should handle gracefully
    await expect(page.locator('[data-testid="app-error"]')).not.toBeVisible();
  });

  test('selecting email with keyboard then clicking works correctly', async ({ page }) => {
    await page.goto('/app');
    await page.waitForSelector('[data-testid="email-list"]');

    // Focus email list
    await page.focus('[data-testid="email-list"]');

    // Arrow down to select
    await page.keyboard.press('ArrowDown');

    // Click on a different email
    await page.click('[data-testid="email-item"]:nth-child(3)');

    // Should select the clicked email, not confuse state
    const selectedEmail = page.locator('[data-testid="email-item"][data-selected="true"]');
    await expect(selectedEmail).toHaveCount(1);
  });

});

// =============================================================================
// CONCURRENT USER ACTIONS
// =============================================================================

test.describe('Concurrent Actions', () => {

  test('search while sync is running returns valid results', async ({ page }) => {
    await page.goto('/app');

    // Trigger sync if not auto-running
    const syncButton = page.locator('[data-testid="sync-button"]');
    if (await syncButton.isVisible()) {
      await syncButton.click();
    }

    // Immediately search
    const searchInput = page.locator('[data-testid="search-input"]');
    await searchInput.fill('test query');
    await page.keyboard.press('Enter');

    // Should return results (possibly stale) without error
    await expect(page.locator('[data-testid="search-error"]')).not.toBeVisible();
  });

  test('linking email while suggestions refresh does not duplicate', async ({ page }) => {
    await page.goto('/app');
    await page.waitForSelector('[data-testid="email-list"]');

    // Select email
    await page.click('[data-testid="email-item"]:first-child');

    // Start manual link
    const linkPromise = page.click('[data-testid="link-button"]');

    // Simultaneously trigger suggestion refresh
    await page.click('[data-testid="refresh-suggestions"]').catch(() => {});

    await linkPromise;

    // Should have only one link
    const links = page.locator('[data-testid="email-link"]');
    await expect(links).toHaveCount(1);
  });

});

// =============================================================================
// SESSION STATE TESTS
// =============================================================================

test.describe('Session State Handling', () => {

  test('expired token shows reconnect prompt, not error', async ({ page }) => {
    // Simulate expired token by setting invalid auth
    await page.goto('/app');

    await page.route('**/api/**', route => {
      route.fulfill({
        status: 401,
        body: JSON.stringify({ error: 'token_expired' }),
      });
    });

    await page.reload();

    // Should show reconnect prompt
    await expect(page.locator('[data-testid="reconnect-prompt"]')).toBeVisible();

    // Should not show technical error
    await expect(page.locator('text=401')).not.toBeVisible();
    await expect(page.locator('text=unauthorized')).not.toBeVisible();
  });

  test('multiple tabs stay in sync', async ({ context }) => {
    const page1 = await context.newPage();
    const page2 = await context.newPage();

    await page1.goto('/app');
    await page2.goto('/app');

    await page1.waitForSelector('[data-testid="email-list"]');
    await page2.waitForSelector('[data-testid="email-list"]');

    // Link in tab 1
    await page1.click('[data-testid="email-item"]:first-child');
    await page1.click('[data-testid="link-button"]');

    // Wait for potential sync
    await page1.waitForTimeout(2000);

    // Tab 2 should reflect change on refresh
    await page2.reload();
    await page2.waitForSelector('[data-testid="email-list"]');

    // Check if state is consistent
    const tab1Linked = await page1.locator('[data-testid="email-item"]:first-child').getAttribute('data-linked');
    const tab2Linked = await page2.locator('[data-testid="email-item"]:first-child').getAttribute('data-linked');

    expect(tab1Linked).toBe(tab2Linked);
  });

});

// =============================================================================
// EDGE CASE DATA TESTS
// =============================================================================

test.describe('Edge Case Data Handling', () => {

  test('email with no subject displays correctly', async ({ page }) => {
    await page.goto('/app');
    await page.waitForSelector('[data-testid="email-list"]');

    // Find email with empty subject (if exists in test data)
    const noSubjectEmail = page.locator('[data-testid="email-item"][data-subject=""]');

    if (await noSubjectEmail.count() > 0) {
      // Should show placeholder, not blank
      const subjectDisplay = noSubjectEmail.locator('[data-testid="email-subject"]');
      const text = await subjectDisplay.textContent();
      expect(text?.trim()).not.toBe('');
    }
  });

  test('email with extremely long subject truncates gracefully', async ({ page }) => {
    await page.goto('/app');
    await page.waitForSelector('[data-testid="email-list"]');

    // All subject displays should be contained (not overflowing)
    const subjects = page.locator('[data-testid="email-subject"]');
    const count = await subjects.count();

    for (let i = 0; i < Math.min(count, 5); i++) {
      const subject = subjects.nth(i);
      const boundingBox = await subject.boundingBox();

      if (boundingBox) {
        // Subject should not exceed reasonable width (container width)
        expect(boundingBox.width).toBeLessThan(800);
      }
    }
  });

  test('thread with 50+ messages does not crash', async ({ page }) => {
    await page.goto('/app');
    await page.waitForSelector('[data-testid="email-list"]');

    // Find a thread with many messages (if exists)
    const largeThread = page.locator('[data-testid="email-item"][data-message-count]');

    if (await largeThread.count() > 0) {
      await largeThread.first().click();

      // Should load without crashing
      await expect(page.locator('[data-testid="thread-view"]')).toBeVisible();

      // Should show messages or "show more" pagination
      const messages = page.locator('[data-testid="thread-message"]');
      const showMore = page.locator('[data-testid="show-more-messages"]');

      const hasMessages = await messages.count() > 0;
      const hasShowMore = await showMore.isVisible();

      expect(hasMessages || hasShowMore).toBeTruthy();
    }
  });

});
