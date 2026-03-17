// apps/web/e2e/shard-34-lens-actions/show-related-link-creation.spec.ts

/**
 * SHARD 34: Show Related — Universal Three-Layer Verification
 *
 * One parameterised suite runs the same proof for all supported entity types:
 *   Layer 1: JSON response — { status: "success", link_id: "uuid", created_at: "..." }
 *   Layer 2: pms_audit_log row — action="add_entity_link", entity_type="entity_link"
 *   Layer 3: pms_entity_links row — source + target match request
 *
 * Additional universal tests (run once, not per entity type):
 *   - GAP-01 fix: omitting link_type returns 200, not 400
 *   - GAP-06 fix: A→B link appears in B's panel
 *   - Crew 403: POST /v1/related/add blocked for non-HOD/manager role
 *
 * NOTE: Show Related writes to pms_audit_log, NOT ledger_events.
 *       Do NOT use pollLedger() here.
 * NOTE: yacht_id is extracted from JWT by the API — do NOT include in body.
 */

import { test, expect, generateTestId, RBAC_CONFIG } from '../rbac-fixtures';
import { BASE_URL, SESSION_JWT, generateFreshJwt } from './helpers';
import type { Page } from '@playwright/test';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// ---------------------------------------------------------------------------
// HTTP helpers — direct JWT, bypasses localStorage
// ---------------------------------------------------------------------------

async function postAddRelated(
  page: Page,
  jwt: string,
  payload: {
    source_entity_type: string;
    source_entity_id: string;
    target_entity_type: string;
    target_entity_id: string;
    link_type?: string;
    note?: string;
  }
): Promise<{ status: number; data: Record<string, unknown> }> {
  const body = JSON.stringify(payload);
  return page.evaluate(
    async ([url, token, reqBody]) => {
      const res = await fetch(url as string, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: reqBody as string,
      });
      const data = await res.json().catch(() => ({}));
      return { status: res.status, data };
    },
    [`${API_URL}/v1/related/add`, jwt, body] as [string, string, string]
  );
}

async function getRelated(
  page: Page,
  jwt: string,
  entityType: string,
  entityId: string
): Promise<{ status: number; data: Record<string, unknown> }> {
  return page.evaluate(
    async ([url, token]) => {
      const res = await fetch(url as string, {
        headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
      });
      const data = await res.json().catch(() => ({}));
      return { status: res.status, data };
    },
    [
      `${API_URL}/v1/related?entity_type=${entityType}&entity_id=${entityId}`,
      jwt,
    ] as [string, string]
  );
}

// ---------------------------------------------------------------------------
// Entity config — one row per supported type pair for link creation
// Pairs must use two different entity types (source ≠ target type) to avoid
// same-id self-link false positives and to exercise FK traversal both ways.
// ---------------------------------------------------------------------------

const LINK_CONFIGS = [
  {
    label: 'work_order → fault',
    sourceType: 'work_order',
    targetType: 'fault',
    sourceRoute: 'work-orders',
  },
  {
    label: 'fault → work_order',
    sourceType: 'fault',
    targetType: 'work_order',
    sourceRoute: 'faults',
  },
] as const;

type SeedFn = {
  seedWorkOrder: (title?: string) => Promise<{ id: string }>;
  seedFault: (title?: string) => Promise<{ id: string }>;
};

async function seedForConfig(
  config: typeof LINK_CONFIGS[number],
  seeds: SeedFn,
  tag: string
): Promise<{ sourceId: string; targetId: string }> {
  if (config.sourceType === 'work_order') {
    const source = await seeds.seedWorkOrder(`S34 SR WO ${tag}`);
    const target = await seeds.seedFault(`S34 SR Fault ${tag}`);
    return { sourceId: source.id, targetId: target.id };
  }
  const source = await seeds.seedFault(`S34 SR Fault ${tag}`);
  const target = await seeds.seedWorkOrder(`S34 SR WO ${tag}`);
  return { sourceId: source.id, targetId: target.id };
}

// ---------------------------------------------------------------------------
// Parameterised three-layer proof
// ---------------------------------------------------------------------------

for (const config of LINK_CONFIGS) {
  test.describe(`[HOD] add_related: ${config.label} — HARD PROOF`, () => {
    test(`POST /v1/related/add (${config.label}) → 200 + audit_log + entity_links`, async ({
      hodPage,
      seedWorkOrder,
      seedFault,
      supabaseAdmin,
    }) => {
      const testStart = new Date();
      const { sourceId, targetId } = await seedForConfig(
        config,
        { seedWorkOrder, seedFault },
        generateTestId('l')
      );

      await hodPage.goto(`${BASE_URL}/${config.sourceRoute}/${sourceId}`);
      await hodPage.waitForLoadState('domcontentloaded');

      // Layer 1: JSON response
      const result = await postAddRelated(hodPage, SESSION_JWT, {
        source_entity_type: config.sourceType,
        source_entity_id: sourceId,
        target_entity_type: config.targetType,
        target_entity_id: targetId,
        link_type: 'related',
      });
      console.log(`[JSON] ${config.label}: ${JSON.stringify(result.data, null, 2)}`);

      expect(result.status).toBe(200);
      const data = result.data as { status?: string; link_id?: string; created_at?: string };
      expect(data.status).toBe('success');
      expect(typeof data.link_id).toBe('string');
      expect((data.link_id as string).length).toBeGreaterThan(0);
      expect(typeof data.created_at).toBe('string');

      const linkId = data.link_id as string;

      // Layer 2: pms_audit_log row
      await expect.poll(
        async () => {
          const { count } = await supabaseAdmin
            .from('pms_audit_log')
            .select('*', { count: 'exact', head: true })
            .eq('action', 'add_entity_link')
            .eq('entity_type', 'entity_link')
            .eq('entity_id', linkId)
            .gte('created_at', testStart.toISOString());
          return count ?? 0;
        },
        {
          intervals: [500, 1000, 1500],
          timeout: 10_000,
          message: `Expected pms_audit_log row for add_entity_link (${config.label})`,
        }
      ).toBeGreaterThanOrEqual(1);

      // Layer 3: pms_entity_links row
      await expect.poll(
        async () => {
          const { count } = await supabaseAdmin
            .from('pms_entity_links')
            .select('*', { count: 'exact', head: true })
            .eq('source_entity_type', config.sourceType)
            .eq('source_entity_id', sourceId)
            .eq('target_entity_type', config.targetType)
            .eq('target_entity_id', targetId);
          return count ?? 0;
        },
        {
          intervals: [500, 1000, 1500],
          timeout: 10_000,
          message: `Expected pms_entity_links row for ${config.label}`,
        }
      ).toBeGreaterThanOrEqual(1);

      // Cleanup explicit link
      await supabaseAdmin
        .from('pms_entity_links')
        .delete()
        .eq('source_entity_id', sourceId)
        .eq('target_entity_id', targetId);
    });
  });
}

// ---------------------------------------------------------------------------
// GAP-01 fix: link_type defaults to "related" when omitted (not 400)
// ---------------------------------------------------------------------------

test.describe('GAP-01 fix: link_type default', () => {
  test('POST /v1/related/add without link_type → 200 (not 400)', async ({
    hodPage,
    seedWorkOrder,
    seedFault,
    supabaseAdmin,
  }) => {
    const wo = await seedWorkOrder(`S34 SR GAP01 WO ${generateTestId('g')}`);
    const fault = await seedFault(`S34 SR GAP01 Fault ${generateTestId('g')}`);

    await hodPage.goto(`${BASE_URL}/work-orders/${wo.id}`);
    await hodPage.waitForLoadState('domcontentloaded');

    const result = await postAddRelated(hodPage, SESSION_JWT, {
      source_entity_type: 'work_order',
      source_entity_id: wo.id,
      target_entity_type: 'fault',
      target_entity_id: fault.id,
      // link_type intentionally omitted — should default to "related", not "explicit"
    });

    expect(result.status).toBe(200);
    expect((result.data as { status?: string }).status).toBe('success');

    await supabaseAdmin
      .from('pms_entity_links')
      .delete()
      .eq('source_entity_id', wo.id)
      .eq('target_entity_id', fault.id);
  });
});

// ---------------------------------------------------------------------------
// GAP-06 fix: bidirectionality — A→B link appears in B's panel
// ---------------------------------------------------------------------------

test.describe('GAP-06 fix: bidirectional explicit links', () => {
  test('explicit A→B link appears in B panel', async ({
    hodPage,
    seedWorkOrder,
    seedFault,
    supabaseAdmin,
  }) => {
    const wo = await seedWorkOrder(`S34 SR Bidir WO ${generateTestId('b')}`);
    const fault = await seedFault(`S34 SR Bidir Fault ${generateTestId('b')}`);

    await hodPage.goto(`${BASE_URL}/work-orders/${wo.id}`);
    await hodPage.waitForLoadState('domcontentloaded');

    // Create WO → Fault link
    const linkResult = await postAddRelated(hodPage, SESSION_JWT, {
      source_entity_type: 'work_order',
      source_entity_id: wo.id,
      target_entity_type: 'fault',
      target_entity_id: fault.id,
      link_type: 'related',
    });
    expect(linkResult.status).toBe(200);

    // Wait for DB write
    await expect.poll(
      async () => {
        const { count } = await supabaseAdmin
          .from('pms_entity_links')
          .select('*', { count: 'exact', head: true })
          .eq('source_entity_id', wo.id)
          .eq('target_entity_id', fault.id);
        return count ?? 0;
      },
      { intervals: [500, 1000], timeout: 8_000, message: 'pms_entity_links row not written' }
    ).toBeGreaterThanOrEqual(1);

    // Query fault's panel — WO must appear (fault is TARGET, not source)
    const relatedResult = await getRelated(hodPage, SESSION_JWT, 'fault', fault.id);
    expect(relatedResult.status).toBe(200);

    type Item = { entity_type: string; entity_id: string };
    const allItems = ((relatedResult.data as { groups?: { items: Item[] }[] }).groups ?? [])
      .flatMap((g) => g.items);

    expect(
      allItems.some((item) => item.entity_type === 'work_order' && item.entity_id === wo.id)
    ).toBe(true);

    await supabaseAdmin
      .from('pms_entity_links')
      .delete()
      .eq('source_entity_id', wo.id)
      .eq('target_entity_id', fault.id);
  });
});

// ---------------------------------------------------------------------------
// Crew 403 — universal (not per entity type, role check is backend-wide)
// ---------------------------------------------------------------------------

test.describe('[Crew] 403 gating — add_related', () => {
  test('[Crew] POST /v1/related/add → 403', async ({
    crewPage,
    seedWorkOrder,
    seedFault,
  }) => {
    const wo = await seedWorkOrder(`S34 SR Crew WO ${generateTestId('c')}`);
    const fault = await seedFault(`S34 SR Crew Fault ${generateTestId('c')}`);

    const crewUserId = process.env.TEST_CREW_USER_ID;
    if (!crewUserId) {
      test.skip(); // Crew UUID not configured in env — skip rather than silently pass
      return;
    }

    const crewJwt = generateFreshJwt(crewUserId, 'crew.test@alex-short.com');

    await crewPage.goto(`${BASE_URL}/work-orders/${wo.id}`);
    await crewPage.waitForLoadState('domcontentloaded');

    const result = await postAddRelated(crewPage, crewJwt, {
      source_entity_type: 'work_order',
      source_entity_id: wo.id,
      target_entity_type: 'fault',
      target_entity_id: fault.id,
      link_type: 'related',
    });

    expect(result.status).toBe(403);
  });
});
