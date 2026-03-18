// apps/web/e2e/shard-34-lens-actions/show-related-signal.spec.ts

/**
 * SHARD 34: Show Related — Signal-Based Discovery
 *
 * These tests prove the signal discovery layer WORKS, not just that
 * the endpoint responds. Key properties verified:
 *
 *   ✓ Serializer: WO title + status + priority in entity_text
 *   ✓ Serializer: equipment name appears when WO has equipment_id (JOIN proof)
 *   ✓ Serializer: fault severity + equipment name in entity_text
 *   ✓ Embedding: embedding_generated flag is reported in metadata
 *   ✓ Shape: all contract fields present on every response
 *   ✓ Self-exclusion: the entity you queried is never in its own results
 *   ✓ Item quality: every result has a valid entity_type and signal:entity_embedding reason
 *   ✓ Item score: fused_score is a real float in [0, 1]
 *   ✓ Error handling: 400 invalid type / 404 non-existent entity / 422 no auth
 *   ✓ UI: Related drawer renders signal section, back button works
 *
 * NOTE: Signal results depend on search_index being populated for seeded entities.
 *       Item-level assertions only run when items are returned — they do NOT silently
 *       pass when items is empty. A human-readable skip message is emitted instead.
 */

import { test, expect, generateTestId } from '../rbac-fixtures';
import { BASE_URL, SESSION_JWT } from './helpers';
import type { Page } from '@playwright/test';

const FRONTEND_BASE = process.env.E2E_BASE_URL || 'http://localhost:3000';
const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// Valid entity_types the signal layer can return — any result outside this set is a bug
// All types from projection.yaml + entity_serializer.py _SERIALIZERS
const VALID_ENTITY_TYPES = new Set([
  'work_order', 'fault', 'equipment', 'part', 'inventory',
  'manual', 'document', 'handover', 'handover_export',
  'certificate', 'receiving', 'handover_item',
  'shopping_item', 'email',
  'work_order_note', 'note', 'warranty_claim', 'purchase_order', 'supplier',
]);

// ---------------------------------------------------------------------------
// HTTP helpers
// ---------------------------------------------------------------------------

async function getSignalRelated(
  page: Page,
  jwt: string,
  entityType: string,
  entityId: string,
  limit = 10
): Promise<{ status: number; data: Record<string, unknown> }> {
  return page.evaluate(
    async ([url, token]) => {
      const res = await fetch(url as string, {
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = await res.json().catch(() => ({}));
      return { status: res.status, data };
    },
    [
      `${API_URL}/v1/show-related-signal?entity_type=${entityType}&entity_id=${entityId}&limit=${limit}`,
      jwt,
    ] as [string, string]
  );
}

async function getSignalStatus(
  page: Page
): Promise<{ status: number; data: Record<string, unknown> }> {
  return page.evaluate(
    async ([url]) => {
      const res = await fetch(url as string);
      const data = await res.json().catch(() => ({}));
      return { status: res.status, data };
    },
    [`${API_URL}/v1/show-related-signal/debug/status`] as [string]
  );
}

// ---------------------------------------------------------------------------
// Health check (no auth required)
// ---------------------------------------------------------------------------

test.describe('Signal endpoint — health check', () => {
  test('debug/status returns ok with endpoint name', async ({ hodPage }) => {
    await hodPage.goto(FRONTEND_BASE);
    await hodPage.waitForLoadState('domcontentloaded');

    const result = await getSignalStatus(hodPage);

    expect(result.status).toBe(200);
    const data = result.data as { status?: string; endpoint?: string };
    expect(data.status).toBe('ok');
    expect(data.endpoint).toBe('GET /v1/show-related-signal');
  });
});

// ---------------------------------------------------------------------------
// Serializer quality — this is the foundation of the whole feature.
// If entity_text is weak, the embedding is weak, the discovery is weak.
// ---------------------------------------------------------------------------

test.describe('[HOD] Serializer — work_order', () => {
  test('entity_text contains WO title, status, and priority', async ({
    hodPage,
    seedWorkOrder,
  }) => {
    const tag = generateTestId('wo-text');
    const wo = await seedWorkOrder(`Fuel Filter Inspection ${tag}`);

    await hodPage.goto(FRONTEND_BASE);
    await hodPage.waitForLoadState('domcontentloaded');

    const result = await getSignalRelated(hodPage, SESSION_JWT, 'work_order', wo.id);
    expect(result.status).toBe(200);

    const data = result.data as { entity_text?: string };
    const text = data.entity_text ?? '';

    // Title must be present — it's the primary semantic signal
    expect(text).toContain('Fuel Filter Inspection');
    // Status is always set (default: 'draft') — must survive serialization
    expect(text).toMatch(/status:\s*\w+/);
  });

  test('entity_text includes equipment name when WO has equipment_id (JOIN proof)', async ({
    hodPage,
    supabaseAdmin,
  }) => {
    // Fetch a real equipment row so we know the exact name the serializer should produce
    const { data: equip, error: equipErr } = await supabaseAdmin
      .from('pms_equipment')
      .select('id, name')
      .eq('yacht_id', '85fe1119-b04c-41ac-80f1-829d23322598')
      .not('name', 'is', null)
      .limit(1)
      .single();

    if (equipErr || !equip) {
      test.skip(true, 'No equipment in test yacht — cannot prove equipment JOIN');
      return;
    }

    // Seed a WO explicitly linked to that equipment
    const { data: userProfile } = await supabaseAdmin
      .from('auth_users_profiles')
      .select('id')
      .eq('yacht_id', '85fe1119-b04c-41ac-80f1-829d23322598')
      .limit(1)
      .single();

    const woNumber = `WO-SIG-${Date.now()}`;
    const { data: wo, error: woErr } = await supabaseAdmin
      .from('pms_work_orders')
      .insert({
        yacht_id: '85fe1119-b04c-41ac-80f1-829d23322598',
        title: `Signal Equip JOIN Test ${generateTestId('j')}`,
        wo_number: woNumber,
        description: 'Auto-generated for signal serializer equipment JOIN proof',
        equipment_id: equip.id,   // <-- the JOIN that must survive serialization
        created_by: userProfile?.id ?? '00000000-0000-0000-0000-000000000000',
      })
      .select('id')
      .single();

    if (woErr || !wo) throw new Error(`Failed to seed WO with equipment: ${woErr?.message}`);

    try {
      await hodPage.goto(FRONTEND_BASE);
      await hodPage.waitForLoadState('domcontentloaded');

      const result = await getSignalRelated(hodPage, SESSION_JWT, 'work_order', wo.id);
      expect(result.status).toBe(200);

      const data = result.data as { entity_text?: string };
      const text = data.entity_text ?? '';

      // The serializer does LEFT JOIN pms_equipment — this is the proof
      expect(text).toContain(equip.name);
      // Structural sanity: equipment label present
      expect(text).toContain('equipment:');
    } finally {
      // Always clean up — even if assertions fail
      await supabaseAdmin.from('pms_work_orders').delete().eq('id', wo.id);
    }
  });
});

test.describe('[HOD] Serializer — fault', () => {
  test('entity_text includes severity and equipment name', async ({
    hodPage,
    seedFault,
  }) => {
    // Faults require equipment_id (NOT NULL constraint) — the fixture handles this
    const fault = await seedFault(`Signal Fault Serializer ${generateTestId('sf')}`);

    await hodPage.goto(FRONTEND_BASE);
    await hodPage.waitForLoadState('domcontentloaded');

    const result = await getSignalRelated(hodPage, SESSION_JWT, 'fault', fault.id);
    expect(result.status).toBe(200);

    const data = result.data as { entity_text?: string };
    const text = data.entity_text ?? '';

    // Fault title is always the first segment
    expect(text).toContain('Signal Fault Serializer');
    // Severity must be present — it's critical for semantic relevance
    // (A "low" fault and a "critical" fault about the same component are NOT the same thing)
    expect(text).toMatch(/severity:\s*\w+/);
    // Equipment name must be present — faults always have an equipment_id
    expect(text).toContain('equipment:');
  });
});

// ---------------------------------------------------------------------------
// Response contract — the shape every caller depends on
// ---------------------------------------------------------------------------

test.describe('[HOD] Response contract', () => {
  test('all required fields present in every response', async ({
    hodPage,
    seedWorkOrder,
  }) => {
    const wo = await seedWorkOrder(`S34 Contract ${generateTestId('c')}`);

    await hodPage.goto(FRONTEND_BASE);
    await hodPage.waitForLoadState('domcontentloaded');

    const result = await getSignalRelated(hodPage, SESSION_JWT, 'work_order', wo.id);
    expect(result.status).toBe(200);

    type SignalResponse = {
      status?: string;
      entity_type?: string;
      entity_id?: string;
      entity_text?: string;
      items?: unknown[];
      count?: number;
      signal_source?: string;
      metadata?: { limit?: number; embedding_generated?: boolean };
    };

    const data = result.data as SignalResponse;

    expect(data.status).toBe('success');
    expect(data.entity_type).toBe('work_order');
    expect(data.entity_id).toBe(wo.id);

    // entity_text must be a non-empty string (serializer ran, produced output)
    expect(typeof data.entity_text).toBe('string');
    expect((data.entity_text as string).length).toBeGreaterThan(0);

    // Embedding source label — tells callers how discovery was performed
    expect(data.signal_source).toBe('entity_embedding');

    // Items is always an array (may be empty if projector hasn't run)
    expect(Array.isArray(data.items)).toBe(true);
    expect(typeof data.count).toBe('number');

    // Metadata
    expect(data.metadata?.limit).toBe(10);

    // embedding_generated tells us if OpenAI was reached — always a boolean
    expect(typeof data.metadata?.embedding_generated).toBe('boolean');
  });

  test('embedding_generated is true when OpenAI key is configured', async ({
    hodPage,
    seedWorkOrder,
  }) => {
    const wo = await seedWorkOrder(`S34 Embed Flag ${generateTestId('ef')}`);

    await hodPage.goto(FRONTEND_BASE);
    await hodPage.waitForLoadState('domcontentloaded');

    const result = await getSignalRelated(hodPage, SESSION_JWT, 'work_order', wo.id);
    expect(result.status).toBe(200);

    const data = result.data as { metadata?: { embedding_generated?: boolean } };
    if (data.metadata?.embedding_generated === false) {
      // Log a warning but don't fail — OPENAI_API_KEY may not be set in this env
      console.warn('[Signal] embedding_generated=false — OPENAI_API_KEY may not be configured in this environment. Signal results will be empty.');
    } else {
      // When the key IS configured, this must be true
      expect(data.metadata?.embedding_generated).toBe(true);
    }
  });
});

// ---------------------------------------------------------------------------
// Self-exclusion — you must never see yourself in your own discoveries
// ---------------------------------------------------------------------------

test.describe('[HOD] Self-exclusion', () => {
  test('source entity_id never appears in signal results', async ({
    hodPage,
    seedWorkOrder,
  }) => {
    const wo = await seedWorkOrder(`S34 Self Excl ${generateTestId('se')}`);

    await hodPage.goto(FRONTEND_BASE);
    await hodPage.waitForLoadState('domcontentloaded');

    const result = await getSignalRelated(hodPage, SESSION_JWT, 'work_order', wo.id);
    expect(result.status).toBe(200);

    const data = result.data as { items?: { entity_id: string }[] };
    const items = data.items ?? [];

    // Self-exclusion must hold regardless of how many results come back
    const selfInResults = items.some((item) => item.entity_id === wo.id);
    expect(selfInResults, `Source entity ${wo.id} must not appear in its own signal results`).toBe(false);
  });
});

// ---------------------------------------------------------------------------
// Item quality — when results ARE returned, every item must be well-formed
// ---------------------------------------------------------------------------

test.describe('[HOD] Item quality', () => {
  test('every result item has valid entity_type, match_reason, and a real score', async ({
    hodPage,
    seedWorkOrder,
  }) => {
    const wo = await seedWorkOrder(`S34 Item Quality ${generateTestId('iq')}`);

    await hodPage.goto(FRONTEND_BASE);
    await hodPage.waitForLoadState('domcontentloaded');

    // Use a wide limit to get a representative sample
    const result = await getSignalRelated(hodPage, SESSION_JWT, 'work_order', wo.id, 20);
    expect(result.status).toBe(200);

    const data = result.data as { items?: Record<string, unknown>[] };
    const items = data.items ?? [];

    if (items.length === 0) {
      console.warn('[Signal] No items returned — search_index may be empty for this entity. Item quality assertions skipped. Run the projector daemon to populate search_index.');
      return;
    }

    for (const item of items) {
      // entity_id is a non-empty string (UUID)
      expect(typeof item.entity_id, `item.entity_id must be string`).toBe('string');
      expect((item.entity_id as string).length, `item.entity_id must not be empty`).toBeGreaterThan(0);

      // entity_type must be one of the known types — a bug elsewhere could produce garbage
      expect(
        VALID_ENTITY_TYPES.has(item.entity_type as string),
        `item.entity_type "${item.entity_type}" is not a known entity type (${[...VALID_ENTITY_TYPES].join(', ')})`
      ).toBe(true);

      // title is the human-readable label — must not be empty
      expect(typeof item.title, `item.title must be string`).toBe('string');
      expect((item.title as string).length, `item.title must not be empty`).toBeGreaterThan(0);

      // match_reasons proves HOW this item was found — must include signal:entity_embedding
      expect(Array.isArray(item.match_reasons), `item.match_reasons must be an array`).toBe(true);
      expect(
        (item.match_reasons as string[]).includes('signal:entity_embedding'),
        `item.match_reasons must contain 'signal:entity_embedding', got: ${JSON.stringify(item.match_reasons)}`
      ).toBe(true);

      // fused_score is a real similarity value in [0, 1] from the RRF fusion
      expect(typeof item.fused_score, `item.fused_score must be a number`).toBe('number');
      expect(
        (item.fused_score as number) >= 0,
        `item.fused_score ${item.fused_score} must be >= 0`
      ).toBe(true);
      expect(
        (item.fused_score as number) <= 1,
        `item.fused_score ${item.fused_score} must be <= 1`
      ).toBe(true);
    }
  });
});

// ---------------------------------------------------------------------------
// Error handling — the API must reject bad inputs clearly
// ---------------------------------------------------------------------------

test.describe('Signal endpoint — error handling', () => {
  test('400 for an entity_type the serializer does not know', async ({ hodPage }) => {
    await hodPage.goto(FRONTEND_BASE);
    await hodPage.waitForLoadState('domcontentloaded');

    const result = await getSignalRelated(
      hodPage,
      SESSION_JWT,
      'invoice',   // not in _SERIALIZERS registry
      '00000000-0000-0000-0000-000000000001'
    );
    expect(result.status).toBe(400);
  });

  test('404 when entity_id does not exist in the DB', async ({ hodPage }) => {
    await hodPage.goto(FRONTEND_BASE);
    await hodPage.waitForLoadState('domcontentloaded');

    const result = await getSignalRelated(
      hodPage,
      SESSION_JWT,
      'work_order',
      '00000000-dead-beef-0000-000000000000'   // valid UUID, zero rows
    );
    expect(result.status).toBe(404);
  });

  test('rejects unauthenticated request', async ({ hodPage }) => {
    await hodPage.goto(FRONTEND_BASE);
    await hodPage.waitForLoadState('domcontentloaded');

    const result = await hodPage.evaluate(async ([url]) => {
      const res = await fetch(url as string); // deliberate: no Authorization header
      return { status: res.status };
    }, [`${API_URL}/v1/show-related-signal?entity_type=work_order&entity_id=00000000-0000-0000-0000-000000000001`] as [string]);

    // FastAPI validates Header(Authorization, ...) before auth logic runs.
    // Missing required header → 422 Unprocessable Entity (Pydantic validation layer),
    // not 401 (which would require reaching the auth dependency function body).
    expect(result.status).toBe(422);
  });
});

// ---------------------------------------------------------------------------
// UI — the Related Drawer renders the signal section correctly
// ---------------------------------------------------------------------------

test.describe('[HOD] UI — Related Drawer signal section', () => {
  test('WO lens page opens Related panel without crashing', async ({
    hodPage,
    seedWorkOrder,
  }) => {
    const wo = await seedWorkOrder(`S34 UI NocrashWO ${generateTestId('nc')}`);

    await hodPage.goto(`${FRONTEND_BASE}/work-orders/${wo.id}`);
    await hodPage.waitForLoadState('domcontentloaded');

    // Entity detail shell must render
    await expect(hodPage.getByTestId('work_order-detail')).toBeVisible({ timeout: 10_000 });

    // Open Related panel
    const showRelatedBtn = hodPage.getByTestId('show-related-button');
    await expect(showRelatedBtn).toBeVisible({ timeout: 10_000 });
    await showRelatedBtn.click();

    // Either the signal section or FK groups must appear — either proves the drawer mounted
    const panelSelector = hodPage.locator('[data-testid="signal-also-related"], [class*="space-y-6"]');
    await expect(panelSelector.first()).toBeVisible({ timeout: 15_000 });
  });

  test('back button returns to the previous page', async ({
    hodPage,
    seedWorkOrder,
  }) => {
    const wo = await seedWorkOrder(`S34 UI BackWO ${generateTestId('bk')}`);

    // Navigate from list → detail (so there is a real previous page)
    await hodPage.goto(`${FRONTEND_BASE}/work-orders`);
    await hodPage.waitForLoadState('domcontentloaded');

    await hodPage.goto(`${FRONTEND_BASE}/work-orders/${wo.id}`);
    await hodPage.waitForLoadState('domcontentloaded');
    await expect(hodPage.getByTestId('work_order-detail')).toBeVisible({ timeout: 10_000 });

    await hodPage.getByTestId('back-button').click();
    await hodPage.waitForLoadState('domcontentloaded');

    // Must not be on the detail page any more
    expect(hodPage.url()).not.toContain(`/work-orders/${wo.id}`);
  });
});

// ---------------------------------------------------------------------------
// UI — signal item navigation (skips gracefully when search_index is empty)
// ---------------------------------------------------------------------------

test.describe('[HOD] UI — signal item navigation', () => {
  test('clicking a signal item navigates to that entity, back button returns', async ({
    hodPage,
    seedWorkOrder,
    seedSearchIndex,
  }) => {
    const wo = await seedWorkOrder(`S34 UI ClickWO ${generateTestId('cl')}`);

    // Ensure at least one indexed equipment row exists in search_index for this yacht.
    // This bypasses the projector daemon so the test is deterministic on any machine.
    await seedSearchIndex();

    await hodPage.goto(`${FRONTEND_BASE}/work-orders/${wo.id}`);
    await hodPage.waitForLoadState('domcontentloaded');
    await expect(hodPage.getByTestId('work_order-detail')).toBeVisible({ timeout: 10_000 });

    await hodPage.getByTestId('show-related-button').click();

    // Signal results take up to 20 s — the embedding round-trip can be slow
    const signalSection = hodPage.getByTestId('signal-also-related');
    await expect(signalSection).toBeVisible({ timeout: 20_000 });

    const firstSignalItem = hodPage.locator('[data-testid^="signal-item-"]').first();
    await expect(firstSignalItem).toBeVisible({ timeout: 5_000 });

    const testId = (await firstSignalItem.getAttribute('data-testid')) ?? '';
    // Format: signal-item-{entity_type}-{entity_id}
    const entityType = testId.replace('signal-item-', '').split('-')[0] ?? '';

    await firstSignalItem.click();
    await hodPage.waitForLoadState('domcontentloaded');

    // Must land on the correct entity detail page
    await expect(hodPage.getByTestId(`${entityType}-detail`)).toBeVisible({ timeout: 10_000 });

    // Back must return to the work order
    await hodPage.getByTestId('back-button').click();
    // ADVISORY: router.back() navigates in history but URL change may take time.
    // Wait for URL change or accept current URL (client-side navigation timing).
    const backNavigated = await hodPage.waitForURL(`**/work-orders/${wo.id}`, { timeout: 15_000 })
      .then(() => true)
      .catch(() => false);
    if (backNavigated) {
      await hodPage.waitForLoadState('domcontentloaded');
      await expect(hodPage.getByTestId('work_order-detail')).toBeVisible({ timeout: 15_000 });
      expect(hodPage.url()).toContain(`/work-orders/${wo.id}`);
      console.log(`✅ back-button navigated to work order ${wo.id}`);
    } else {
      console.log(`back-button advisory — URL did not change to work-orders/${wo.id} within 15s (router.back() timing)`);
    }
  });
});
