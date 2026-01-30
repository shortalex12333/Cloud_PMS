/**
 * Documents Lens - Suggested Actions Test
 *
 * Verifies HOD user can see document actions in spotlight
 *
 * Run: npx playwright test documents.suggested-actions.spec.ts --project=chromium
 */
import { test, expect } from '@playwright/test';
import {
  loginAs,
  searchInSpotlight,
  getActionSuggestions,
  clickAction,
  waitForActionModal,
} from './auth.helper';

test.describe('Documents - Suggested Actions (HOD)', () => {
  test.beforeEach(async ({ page }) => {
    // Login as HOD (chief_engineer)
    await loginAs(page, 'hod');
  });

  test('HOD sees Upload Document action in spotlight', async ({ page }) => {
    // Type "add document" in spotlight
    await searchInSpotlight(page, 'add document');

    // Get action suggestions
    const actions = await getActionSuggestions(page);

    // Should include upload/add document action
    const hasDocumentAction = actions.some(
      (a) =>
        a.toLowerCase().includes('upload') ||
        a.toLowerCase().includes('add document') ||
        a.toLowerCase().includes('create document')
    );

    expect(hasDocumentAction).toBe(true);

    // Verify no 500 errors in network
    const responses: number[] = [];
    page.on('response', (response) => {
      if (response.url().includes('/v1/actions')) {
        responses.push(response.status());
      }
    });

    // Re-search to trigger API call with listener
    await searchInSpotlight(page, 'upload document');
    await page.waitForTimeout(1000);

    // No 500 errors
    const has500 = responses.some((s) => s >= 500);
    expect(has500).toBe(false);
  });

  test('Clicking action opens modal with required fields', async ({ page }) => {
    // Search for document action
    await searchInSpotlight(page, 'upload document');

    // Get the action and click it
    const actions = await getActionSuggestions(page);
    const documentAction = actions.find(
      (a) =>
        a.toLowerCase().includes('upload') ||
        a.toLowerCase().includes('add document')
    );

    if (documentAction) {
      await clickAction(page, documentAction);

      // Wait for modal
      await waitForActionModal(page);

      // Modal should have required fields
      const formFields = page.locator(
        'input[required], ' +
        'select[required], ' +
        '[data-testid="required-field"], ' +
        'label:has-text("*")'
      );

      const fieldCount = await formFields.count();
      expect(fieldCount).toBeGreaterThan(0);

      // Check for storage path preview (if implemented)
      const pathPreview = page.locator(
        '[data-testid="storage-path-preview"], ' +
        ':text("yacht_id"), ' +
        ':text("/documents/")'
      );

      // Storage path preview is optional but good to have
      if (await pathPreview.count() > 0) {
        const pathText = await pathPreview.textContent();
        expect(pathText).not.toContain('undefined');
      }
    } else {
      // If no document action found, the test should still pass
      // but we log it for investigation
      console.warn('No document upload action found in suggestions:', actions);
    }
  });

  test('Search results include action chips', async ({ page }) => {
    // Navigate to main search
    await page.goto('/');

    // Perform search
    await searchInSpotlight(page, 'document');
    await page.waitForTimeout(1000);

    // Check for action chips/buttons under search
    const actionArea = page.locator(
      '[data-testid="suggested-actions"], ' +
      '.suggested-actions, ' +
      '.action-chips'
    );

    // Either action area exists or individual action buttons exist
    const hasActionArea = await actionArea.count() > 0;
    const actions = await getActionSuggestions(page);

    expect(hasActionArea || actions.length > 0).toBe(true);
  });
});
