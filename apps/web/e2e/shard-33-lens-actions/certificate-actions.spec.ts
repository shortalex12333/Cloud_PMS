// apps/web/e2e/shard-33-lens-actions/certificate-actions.spec.ts

import { test, expect } from '../rbac-fixtures';
import { BASE_URL, assertNoRenderCrash } from './helpers';

/**
 * SHARD 33: Lens Actions — Certificates (3 roles)
 *
 * Upload Document requires a file input — outside scope of smoke test.
 * Set Reminder requires a date picker — outside scope of smoke test.
 * Tests verify: render without crash + at least one action button visible.
 *
 * Uses getExistingCertificate (read-only fixture, no insert).
 */

test.describe('[HOD] Certificate lens actions', () => {
  test('renders certificate detail + action button visible', async ({
    hodPage,
    getExistingCertificate,
  }) => {
    const cert = await getExistingCertificate();

    await hodPage.goto(`${BASE_URL}/certificates/${cert.id}`);
    await hodPage.waitForLoadState('domcontentloaded');

    await expect(hodPage.getByRole('heading', { name: cert.certificate_name, exact: true }).first())
      .toBeVisible({ timeout: 15_000 });
    await assertNoRenderCrash(hodPage);

    // Primary action button or dropdown trigger — always visible if actions are available.
    // "Upload Document" and "Set Reminder" live inside the dropdown (hidden by default).
    const primaryVisible = await hodPage.locator('button:has-text("Renew Certificate"), button:has-text("Upload Renewed"), button:has-text("More actions"), button:has-text("Update Certificate"), button:has-text("Link Document")').first()
      .isVisible().catch(() => false);

    expect(primaryVisible).toBe(true);
    console.log(`✅ HOD: cert ${cert.id} renders. Primary action visible=${primaryVisible}`);
  });
});

test.describe('[Captain] Certificate lens actions', () => {
  test('renders certificate detail + action button visible', async ({
    captainPage,
    getExistingCertificate,
  }) => {
    const cert = await getExistingCertificate();

    await captainPage.goto(`${BASE_URL}/certificates/${cert.id}`);
    await captainPage.waitForLoadState('domcontentloaded');

    await expect(captainPage.getByRole('heading', { name: cert.certificate_name, exact: true }).first())
      .toBeVisible({ timeout: 15_000 });
    await assertNoRenderCrash(captainPage);

    const primaryVisible = await captainPage.locator('button:has-text("Renew Certificate"), button:has-text("Upload Renewed"), button:has-text("More actions"), button:has-text("Update Certificate"), button:has-text("Link Document")').first()
      .isVisible().catch(() => false);

    expect(primaryVisible).toBe(true);
    console.log(`✅ Captain: cert ${cert.id} renders. Primary action visible=${primaryVisible}`);
  });
});

test.describe('[Crew] Certificate lens actions', () => {
  test('renders certificate page without 500 crash', async ({
    crewPage,
    getExistingCertificate,
  }) => {
    const cert = await getExistingCertificate();

    await crewPage.goto(`${BASE_URL}/certificates/${cert.id}`);
    await crewPage.waitForLoadState('domcontentloaded');

    await expect(crewPage.getByText('500', { exact: true }).first()).not.toBeVisible({ timeout: 10_000 });
    console.log(`✅ Crew: certificate page loads without 500 for cert ${cert.id} (${cert.certificate_name})`);
  });
});
