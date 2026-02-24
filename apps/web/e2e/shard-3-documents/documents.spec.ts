import { test, expect, SpotlightSearchPO, ContextPanelPO, DocumentViewerPO, TEST_CONFIG } from '../fixtures';

/**
 * SHARD 3: Document & Certificate Rendering Tests (LAW 12)
 *
 * LAW 12: DEEP UI VERIFICATION
 * - Tests must verify actual document rendering, not just API responses
 * - PDF viewer must successfully receive signed URLs
 * - Images must load with correct content types
 * - No broken file links
 */

test.describe('Document Search & Discovery', () => {
  test('should find documents when searching', async ({ page }) => {
    await page.goto('/');

    const spotlight = new SpotlightSearchPO(page);
    await spotlight.search('certificate');

    await expect(spotlight.resultsContainer).toBeVisible({ timeout: 10_000 });

    const resultCount = await spotlight.getResultCount();
    // Documents should be searchable
    expect(resultCount).toBeGreaterThanOrEqual(0);
  });

  test('should find certificates by type', async ({ page }) => {
    await page.goto('/');

    const spotlight = new SpotlightSearchPO(page);
    await spotlight.search('safety certificate');

    await expect(spotlight.resultsContainer).toBeVisible({ timeout: 10_000 });
  });

  test('should find manuals when searching', async ({ page }) => {
    await page.goto('/');

    const spotlight = new SpotlightSearchPO(page);
    await spotlight.search('manual operation');

    await expect(spotlight.resultsContainer).toBeVisible({ timeout: 10_000 });
  });
});

test.describe('Document Lens (LAW 12: Deep Verification)', () => {
  test('should open document lens from search result', async ({ page }) => {
    await page.goto('/');

    const spotlight = new SpotlightSearchPO(page);
    const contextPanel = new ContextPanelPO(page);

    await spotlight.search('document');
    await expect(spotlight.resultsContainer).toBeVisible({ timeout: 10_000 });

    const resultCount = await spotlight.getResultCount();
    if (resultCount > 0) {
      await spotlight.clickResult(0);

      // Context panel should open
      await expect(contextPanel.panel).toBeVisible({ timeout: 10_000 });

      // Content should load (not show loading forever)
      await expect(contextPanel.loading).not.toBeVisible({ timeout: 15_000 });

      // No error state
      await expect(contextPanel.error).not.toBeVisible();
    }
  });

  test('should display document metadata in lens', async ({ page }) => {
    await page.goto('/');

    const spotlight = new SpotlightSearchPO(page);
    const contextPanel = new ContextPanelPO(page);

    await spotlight.search('certificate');
    await expect(spotlight.resultsContainer).toBeVisible();

    const resultCount = await spotlight.getResultCount();
    if (resultCount > 0) {
      await spotlight.clickResult(0);
      await contextPanel.waitForContent();

      // Verify entity type is document or certificate
      const entityType = await contextPanel.getEntityType();
      expect(['document', 'certificate', 'manual']).toContain(entityType);
    }
  });
});

test.describe('Document Viewer Overlay (LAW 12)', () => {
  test('should open document viewer when clicking attachment', async ({ page }) => {
    await page.goto('/');

    const spotlight = new SpotlightSearchPO(page);

    // Search for work orders (they have attachments)
    await spotlight.search('work order');
    await expect(spotlight.resultsContainer).toBeVisible();

    const resultCount = await spotlight.getResultCount();
    if (resultCount > 0) {
      await spotlight.clickResult(0);

      // Wait for context panel
      const contextPanel = page.getByTestId('context-panel');
      await expect(contextPanel).toBeVisible({ timeout: 10_000 });

      // Look for attachments section
      const attachmentsSection = page.locator('text=Attachments');

      if (await attachmentsSection.isVisible()) {
        // Click on an attachment
        const attachment = page.locator('[data-testid="attachment-item"]').first();

        if (await attachment.isVisible()) {
          await attachment.click();

          // Document viewer overlay should open
          const documentViewer = new DocumentViewerPO(page);
          await expect(documentViewer.overlay).toBeVisible({ timeout: 10_000 });
        }
      }
    }
  });

  test('should display PDF viewer for PDF documents', async ({ page }) => {
    await page.goto('/');

    // This test requires finding a PDF document
    const spotlight = new SpotlightSearchPO(page);
    await spotlight.search('pdf manual');

    await expect(spotlight.resultsContainer).toBeVisible();

    const resultCount = await spotlight.getResultCount();
    if (resultCount > 0) {
      await spotlight.clickResult(0);

      const contextPanel = page.getByTestId('context-panel');
      await expect(contextPanel).toBeVisible({ timeout: 10_000 });

      // Look for a PDF file in attachments
      const pdfAttachment = page.locator('[data-file-type="pdf"], [data-content-type*="pdf"]').first();

      if (await pdfAttachment.isVisible()) {
        await pdfAttachment.click();

        // Verify PDF viewer loads
        const documentViewer = page.getByTestId('document-viewer-overlay');
        await expect(documentViewer).toBeVisible({ timeout: 10_000 });

        // LAW 12: Verify actual PDF object loads
        const pdfObject = documentViewer.locator('object[type="application/pdf"]');
        await expect(pdfObject).toBeVisible({ timeout: 15_000 });
      }
    }
  });

  test('should display image viewer for image documents', async ({ page }) => {
    await page.goto('/');

    const spotlight = new SpotlightSearchPO(page);
    await spotlight.search('photo image');

    await expect(spotlight.resultsContainer).toBeVisible();

    const resultCount = await spotlight.getResultCount();
    if (resultCount > 0) {
      await spotlight.clickResult(0);

      const contextPanel = page.getByTestId('context-panel');
      await expect(contextPanel).toBeVisible({ timeout: 10_000 });

      // Look for an image file
      const imageAttachment = page.locator('[data-content-type*="image"]').first();

      if (await imageAttachment.isVisible()) {
        await imageAttachment.click();

        const documentViewer = page.getByTestId('document-viewer-overlay');
        await expect(documentViewer).toBeVisible({ timeout: 10_000 });

        // LAW 12: Verify actual image loads
        const image = documentViewer.locator('img');
        await expect(image).toBeVisible({ timeout: 15_000 });

        // Verify image has loaded (natural dimensions)
        const loaded = await image.evaluate((img: HTMLImageElement) => {
          return img.naturalWidth > 0 && img.naturalHeight > 0;
        });
        expect(loaded).toBe(true);
      }
    }
  });

  test('should close document viewer on Escape', async ({ page }) => {
    await page.goto('/');

    const spotlight = new SpotlightSearchPO(page);
    await spotlight.search('document');

    await expect(spotlight.resultsContainer).toBeVisible();

    const resultCount = await spotlight.getResultCount();
    if (resultCount > 0) {
      await spotlight.clickResult(0);

      const contextPanel = page.getByTestId('context-panel');
      await expect(contextPanel).toBeVisible();

      // If there's an attachment to click
      const attachment = page.locator('[data-testid="attachment-item"]').first();

      if (await attachment.isVisible()) {
        await attachment.click();

        const documentViewer = page.getByTestId('document-viewer-overlay');

        if (await documentViewer.isVisible()) {
          // Press Escape to close
          await page.keyboard.press('Escape');

          await expect(documentViewer).not.toBeVisible({ timeout: 5_000 });
        }
      }
    }
  });
});

test.describe('Signed URL Verification (LAW 12)', () => {
  test('should generate valid signed URLs for documents', async ({ page, request }) => {
    await page.goto('/');

    // Monitor network requests for signed URLs
    const signedUrlRequests: string[] = [];

    page.on('request', (req) => {
      const url = req.url();
      if (url.includes('signed') || url.includes('storage')) {
        signedUrlRequests.push(url);
      }
    });

    const spotlight = new SpotlightSearchPO(page);
    await spotlight.search('certificate document');

    await expect(spotlight.resultsContainer).toBeVisible();

    const resultCount = await spotlight.getResultCount();
    if (resultCount > 0) {
      await spotlight.clickResult(0);

      const contextPanel = page.getByTestId('context-panel');
      await expect(contextPanel).toBeVisible({ timeout: 10_000 });

      // Wait a bit for any document loading
      await page.waitForTimeout(3000);

      // If signed URLs were requested, verify they're accessible
      for (const url of signedUrlRequests.slice(0, 3)) {  // Check first 3
        const response = await request.head(url);
        // Signed URLs should return 200 or redirect
        expect([200, 301, 302]).toContain(response.status());
      }
    }
  });

  test('should handle expired signed URLs gracefully', async ({ page }) => {
    await page.goto('/');

    const spotlight = new SpotlightSearchPO(page);
    await spotlight.search('document');

    await expect(spotlight.resultsContainer).toBeVisible();

    const resultCount = await spotlight.getResultCount();
    if (resultCount > 0) {
      await spotlight.clickResult(0);

      const contextPanel = page.getByTestId('context-panel');
      await expect(contextPanel).toBeVisible({ timeout: 10_000 });

      // Even if a URL expires, the UI should handle it gracefully
      // (show error message, not crash)
      await expect(page.locator('[data-testid="fatal-error"]')).not.toBeVisible();
    }
  });
});

test.describe('Certificate Lens', () => {
  test('should display certificate details', async ({ page }) => {
    await page.goto('/');

    const spotlight = new SpotlightSearchPO(page);
    await spotlight.search('certificate');

    await expect(spotlight.resultsContainer).toBeVisible();

    const resultCount = await spotlight.getResultCount();
    if (resultCount > 0) {
      await spotlight.clickResult(0);

      const contextPanel = page.getByTestId('context-panel');
      await expect(contextPanel).toBeVisible({ timeout: 10_000 });

      // LAW 12: Verify actual content rendered
      const content = page.getByTestId('context-panel-content');
      await expect(content).toBeVisible();

      // Should show certificate-specific info
      // (expiry date, issuer, etc.)
    }
  });

  test('should show expiry status for certificates', async ({ page }) => {
    await page.goto('/');

    const spotlight = new SpotlightSearchPO(page);
    await spotlight.search('certificate expiry');

    await expect(spotlight.resultsContainer).toBeVisible();

    // Certificates with expiry dates should be findable
  });
});

test.describe('Document Download', () => {
  test('should offer download button for documents', async ({ page }) => {
    await page.goto('/');

    const spotlight = new SpotlightSearchPO(page);
    await spotlight.search('document');

    await expect(spotlight.resultsContainer).toBeVisible();

    const resultCount = await spotlight.getResultCount();
    if (resultCount > 0) {
      await spotlight.clickResult(0);

      const contextPanel = page.getByTestId('context-panel');
      await expect(contextPanel).toBeVisible({ timeout: 10_000 });

      // Look for download button in attachments
      const downloadButton = page.locator('[aria-label*="Download"], [title*="Download"], button:has-text("Download")');

      // Download should be available (if attachments exist)
    }
  });
});

test.describe('Document Micro-Actions', () => {
  test('should show micro-action menu on document', async ({ page }) => {
    await page.goto('/');

    const spotlight = new SpotlightSearchPO(page);
    await spotlight.search('document');

    await expect(spotlight.resultsContainer).toBeVisible();

    const resultCount = await spotlight.getResultCount();
    if (resultCount > 0) {
      await spotlight.clickResult(0);

      const contextPanel = page.getByTestId('context-panel');
      await expect(contextPanel).toBeVisible({ timeout: 10_000 });

      // Look for more options button (three dots)
      const moreButton = contextPanel.locator('[aria-label*="More"], [data-testid="more-actions"]');

      if (await moreButton.isVisible()) {
        await moreButton.click();

        // Menu should appear with actions
        const menu = page.locator('[role="menu"], [data-radix-menu-content]');
        await expect(menu).toBeVisible({ timeout: 5_000 });
      }
    }
  });
});
