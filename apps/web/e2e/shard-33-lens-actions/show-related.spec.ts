// apps/web/e2e/shard-33-lens-actions/show-related.spec.ts

/**
 * SHARD 33: Show Related — Universal Smoke Tests
 *
 * Parameterised over all SUPPORTED_ENTITY_TYPES so this file stays
 * in sync with the backend automatically when new types are added.
 *
 * Per entity type:
 *   1. Panel opens on detail page without crash
 *   2. GET /v1/related returns { status: "success", groups: [...] }
 *   3. Every item that exists has a non-blank `title` field
 *
 * Add a row to ENTITY_CONFIGS when a new supported entity type gains
 * a seed fixture in rbac-fixtures.ts.
 */

import { test, expect, generateTestId } from '../rbac-fixtures';
import { BASE_URL, API_URL, fetchFromPage, assertNoRenderCrash } from './helpers';

// ---------------------------------------------------------------------------
// Universal entity config — one row per SUPPORTED_ENTITY_TYPE with a seed
// ---------------------------------------------------------------------------

const ENTITY_CONFIGS = [
  {
    entityType: 'work_order' as const,
    route: 'work-orders',
    label: 'Work Order',
  },
  {
    entityType: 'fault' as const,
    route: 'faults',
    label: 'Fault',
  },
] as const;

// ---------------------------------------------------------------------------
// Helper — seeds the right entity based on config
// ---------------------------------------------------------------------------

type SeedFn = {
  seedWorkOrder: (title?: string) => Promise<{ id: string; title: string }>;
  seedFault: (title?: string) => Promise<{ id: string; title: string }>;
};

async function seedEntity(
  config: typeof ENTITY_CONFIGS[number],
  seeds: SeedFn
): Promise<{ id: string; title: string }> {
  if (config.entityType === 'work_order') {
    return seeds.seedWorkOrder(`S33 SR ${config.label} ${generateTestId('r')}`);
  }
  return seeds.seedFault(`S33 SR ${config.label} ${generateTestId('r')}`);
}

// ---------------------------------------------------------------------------
// Universal test suite
// ---------------------------------------------------------------------------

for (const config of ENTITY_CONFIGS) {
  test.describe(`[Show Related] ${config.label} (${config.entityType})`, () => {

    test(`panel opens on ${config.route} detail without crash`, async ({
      hodPage,
      seedWorkOrder,
      seedFault,
    }) => {
      const entity = await seedEntity(config, { seedWorkOrder, seedFault });

      await hodPage.goto(`${BASE_URL}/${config.route}/${entity.id}`);
      await hodPage.waitForLoadState('domcontentloaded');
      await assertNoRenderCrash(hodPage);

      const btn = hodPage.getByTestId('show-related-button');
      await expect(btn).toBeVisible({ timeout: 10_000 });
      await btn.click();

      // Panel renders — either items or empty state, never an error banner
      await expect(hodPage.getByText('Failed to load related items').first())
        .not.toBeVisible({ timeout: 5_000 });
    });

    test(`GET /v1/related?entity_type=${config.entityType} returns valid shape`, async ({
      hodPage,
      seedWorkOrder,
      seedFault,
    }) => {
      const entity = await seedEntity(config, { seedWorkOrder, seedFault });

      // Navigate first so fetchFromPage has a valid auth token in localStorage
      await hodPage.goto(`${BASE_URL}/${config.route}/${entity.id}`);
      await hodPage.waitForLoadState('domcontentloaded');

      const result = await fetchFromPage(
        hodPage,
        `${API_URL}/v1/related?entity_type=${config.entityType}&entity_id=${entity.id}`
      );

      expect(result.status).toBe(200);

      type Item = { title?: unknown };
      type Group = { group_key: string; items: Item[] };
      const data = result.data as { status?: string; groups?: Group[] };

      expect(data.status).toBe('success');
      expect(Array.isArray(data.groups)).toBe(true);

      // Every item that exists must have a non-empty string title
      // (this would catch the label/title mismatch we fixed in useRelated.ts)
      for (const group of data.groups ?? []) {
        for (const item of group.items ?? []) {
          expect(typeof item.title).toBe('string');
          expect((item.title as string).length).toBeGreaterThan(0);
        }
      }
    });

  });
}
