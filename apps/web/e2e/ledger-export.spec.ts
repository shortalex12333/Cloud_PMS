import { test, expect, Page } from '@playwright/test';

const EMAIL = 'x@alex-short.com';
const PASSWORD = 'Password2!';

async function login(page: Page) {
  await page.goto('/login');
  // Wait for Suspense boundary to resolve — form renders after React hydration
  await page.locator('input[type="email"]').first().waitFor({ state: 'visible', timeout: 20000 });

  await page.locator('input[type="email"]').first().fill(EMAIL);
  await page.locator('input[type="password"]').first().fill(PASSWORD);
  await page.locator('input[type="password"]').first().press('Enter');

  // Wait for redirect away from login — bootstrap can be slow on dev (compilation + API call)
  await page.waitForFunction(() => !window.location.pathname.includes('/login'), { timeout: 90000 });
  await page.waitForLoadState('networkidle', { timeout: 20000 }).catch(() => {});
}

test('ledger panel — export modal opens and generates PDF', async ({ page }) => {
  await login(page);
  await page.screenshot({ path: '/tmp/ss-01-post-login.png' });

  console.log('✓ Logged in, URL:', page.url());

  // ── Open the Ledger panel ─────────────────────────────────────────────
  await page.locator('[data-testid="user-menu-trigger"]').click();
  await page.waitForTimeout(300);
  await page.screenshot({ path: '/tmp/ss-02-menu-open.png' });

  await page.locator('[data-testid="ledger-open"]').click();
  await page.waitForTimeout(1200);
  await page.screenshot({ path: '/tmp/ss-03-ledger-panel.png' });
  console.log('✓ Ledger panel opened');

  // ── Verify the panel header ───────────────────────────────────────────
  await expect(page.locator('text=Ledger').first()).toBeVisible();
  await expect(page.locator('text=Activity timeline')).toBeVisible();

  // ── Click the Download icon ───────────────────────────────────────────
  const exportBtn = page.locator('button[title="Export evidence PDF"]');
  await exportBtn.waitFor({ timeout: 5000 });
  await exportBtn.click();
  await page.waitForTimeout(600);
  await page.screenshot({ path: '/tmp/ss-04-export-modal.png' });
  console.log('✓ Export modal opened');

  // ── Modal elements visible ────────────────────────────────────────────
  await expect(page.locator('text=Export Evidence PDF')).toBeVisible();
  await expect(page.locator('input[type="date"]').first()).toBeVisible();
  await expect(page.locator('select')).toBeVisible();

  const generateBtn = page.locator('button', { hasText: /generate pdf/i });
  // Disabled until dates are filled
  await expect(generateBtn).toBeDisabled();
  console.log('✓ Generate button correctly disabled (no dates yet)');

  // ── Fill dates ────────────────────────────────────────────────────────
  await page.locator('input[type="date"]').nth(0).fill('2026-04-01');
  await page.locator('input[type="date"]').nth(1).fill('2026-04-13');
  await page.screenshot({ path: '/tmp/ss-05-dates-filled.png' });

  await expect(generateBtn).toBeEnabled();
  console.log('✓ Generate button enabled after dates filled');

  // ── Click Generate ────────────────────────────────────────────────────
  await generateBtn.click();
  await page.screenshot({ path: '/tmp/ss-06-generating.png' });
  console.log('⏳ Generating PDF (TSA + sealing, may take ~10s)…');

  // Wait for download link — up to 30s for seal + upload
  const downloadLink = page.locator('a', { hasText: /download pdf/i });
  await downloadLink.waitFor({ timeout: 30000 });
  await page.screenshot({ path: '/tmp/ss-07-result.png' });

  const href = await downloadLink.getAttribute('href') ?? '';
  console.log('✓ Download link:', href.slice(0, 90) + '…');

  // ── Assert the URL shape ──────────────────────────────────────────────
  expect(href).toContain('supabase.co/storage');
  expect(href).toContain('ledger-exports');
  console.log('✓ href is a valid Supabase signed storage URL');

  // ── Event count text visible ──────────────────────────────────────────
  const countEl = page.locator('text=/\\d+ event/').first();
  await expect(countEl).toBeVisible();
  const countText = await countEl.textContent() ?? '';
  console.log('✓ Event count:', countText.trim());

  // ── SEALED badge ──────────────────────────────────────────────────────
  const sealed = await page.locator('text=SEALED').isVisible();
  console.log('✓ SEALED badge visible:', sealed);

  // ── Close modal ───────────────────────────────────────────────────────
  await page.locator('button', { hasText: /generate another/i }).click();
  await expect(page.locator('text=Export Evidence PDF')).toBeVisible(); // modal stays open
  console.log('✓ "Generate another" resets result state');
});
