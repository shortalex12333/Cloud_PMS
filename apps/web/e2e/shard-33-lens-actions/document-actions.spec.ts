// apps/web/e2e/shard-33-lens-actions/document-actions.spec.ts

import { test, expect } from '../rbac-fixtures';
import { BASE_URL, assertNoRenderCrash } from './helpers';

/**
 * SHARD 33: Lens Actions — Documents (3 roles)
 *
 * Archive is irreversible without a separate seeded document — do NOT click.
 * Tests verify: render without crash + Archive button is visible for authorized roles.
 *
 * Uses getExistingDocument (read-only fixture).
 * Note: pms_documents is not in PostgREST schema cache — fixture uses DB query (Strategy 1)
 * or page navigation (Strategy 2). If no documents exist, tests are skipped with advisory.
 */

/** Extract doc id from fixture; skip test if no documents found in test environment. */
async function getDocOrSkip(
  getExistingDocument: () => Promise<{ id: string }>
): Promise<{ id: string }> {
  try {
    return await getExistingDocument();
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e);
    if (msg.startsWith('SKIP:')) {
      test.skip(true, msg.slice(5).trim());
      // test.skip throws internally; return is unreachable but satisfies TypeScript
      return { id: '' };
    }
    throw e;
  }
}

test.describe('[HOD] Document lens actions', () => {
  test('renders document detail + Archive button visible', async ({
    hodPage,
    getExistingDocument,
  }) => {
    const doc = await getDocOrSkip(getExistingDocument);

    await hodPage.goto(`${BASE_URL}/documents/${doc.id}`);
    await hodPage.waitForLoadState('domcontentloaded');

    // Verify some heading is visible (title not available from fixture due to PostgREST schema cache issue)
    await expect(hodPage.locator('h1').first()).toBeVisible({ timeout: 15_000 });
    await assertNoRenderCrash(hodPage);

    // Archive button must be present (do NOT click — irreversible)
    await expect(hodPage.locator('button:has-text("Archive")').first())
      .toBeVisible({ timeout: 10_000 });
    console.log(`✅ HOD: document ${doc.id} renders + Archive button visible`);
  });
});

test.describe('[Captain] Document lens actions', () => {
  test('renders document detail + Archive button visible', async ({
    captainPage,
    getExistingDocument,
  }) => {
    const doc = await getDocOrSkip(getExistingDocument);

    await captainPage.goto(`${BASE_URL}/documents/${doc.id}`);
    await captainPage.waitForLoadState('domcontentloaded');

    await expect(captainPage.locator('h1').first()).toBeVisible({ timeout: 15_000 });
    await assertNoRenderCrash(captainPage);

    await expect(captainPage.locator('button:has-text("Archive")').first())
      .toBeVisible({ timeout: 10_000 });
    console.log(`✅ Captain: document ${doc.id} renders + Archive button visible`);
  });
});

test.describe('[Crew] Document lens actions', () => {
  test('renders document page without 500 crash', async ({
    crewPage,
    getExistingDocument,
  }) => {
    const doc = await getDocOrSkip(getExistingDocument);

    await crewPage.goto(`${BASE_URL}/documents/${doc.id}`);
    await crewPage.waitForLoadState('domcontentloaded');

    // Crew may lack permission to view — must not 500; graceful state expected
    await expect(crewPage.getByText('500', { exact: true }).first()).not.toBeVisible({ timeout: 10_000 });
    console.log(`✅ Crew: document page loads without 500 for doc ${doc.id}`);
  });
});
