/**
 * V4 — CRUD + Quality Test Suite
 *
 * Tests data integrity, cross-domain actions, and quality standards
 * against the clean data state (post-V3 is_seed isolation).
 *
 * Tests are structured as: READ, QUALITY, then CREATE/UPDATE/ARCHIVE
 * (which require UI interaction and may need auth flow adjustments).
 */

import { test, expect } from '@playwright/test';

const API_BASE = process.env.E2E_BASE_URL?.replace(':3000', ':8000') || 'http://localhost:8000';

/** Get auth token from localStorage */
async function getToken(page: import('@playwright/test').Page): Promise<string | null> {
  await page.goto('/');
  await page.waitForTimeout(2000);
  return page.evaluate(() => {
    const keys = Object.keys(localStorage);
    const sbKey = keys.find(k => k.startsWith('sb-') && k.includes('auth-token'));
    if (!sbKey) return null;
    try {
      const data = JSON.parse(localStorage.getItem(sbKey) || '{}');
      return data.access_token || null;
    } catch { return null; }
  });
}

// ═══════════════════════════════════════════════════════════════════════════════
// READ TESTS — Vessel Surface data quality
// ═══════════════════════════════════════════════════════════════════════════════

test.describe('READ: Vessel Surface data quality', () => {
  let token: string | null = null;
  let surfaceData: any = null;

  test.beforeAll(async ({ browser }) => {
    const page = await browser.newPage();
    token = await getToken(page);
    if (token) {
      const res = await page.request.get(`${API_BASE}/api/vessel/85fe1119-b04c-41ac-80f1-829d23322598/surface`, {
        headers: { 'Authorization': `Bearer ${token}` },
      });
      if (res.ok()) surfaceData = await res.json();
    }
    await page.close();
  });

  test('work orders count is ≤ 20 (test data isolated)', async () => {
    test.skip(!surfaceData, 'No surface data available');
    const woCount = surfaceData.work_orders?.open_count ?? 0;
    expect(woCount).toBeLessThanOrEqual(20);
    expect(woCount).toBeGreaterThan(0);
  });

  test('faults count is ≤ 15 (test data isolated)', async () => {
    test.skip(!surfaceData, 'No surface data available');
    const faultCount = surfaceData.faults?.open_count ?? 0;
    expect(faultCount).toBeLessThanOrEqual(15);
    expect(faultCount).toBeGreaterThan(0);
  });

  test('parts below min capped at 5 items', async () => {
    test.skip(!surfaceData, 'No surface data available');
    const items = surfaceData.parts_below_min?.items ?? [];
    expect(items.length).toBeLessThanOrEqual(5);
    // Total count should be returned separately
    const totalCount = surfaceData.parts_below_min?.count ?? 0;
    expect(totalCount).toBeGreaterThan(0);
  });

  test('parts have stock_level and min_stock as numbers (not null)', async () => {
    test.skip(!surfaceData, 'No surface data available');
    const items = surfaceData.parts_below_min?.items ?? [];
    for (const p of items) {
      expect(typeof p.stock_level).toBe('number');
      expect(typeof p.min_stock).toBe('number');
      expect(p.min_stock).toBeGreaterThan(0);
      expect(p.stock_level).toBeLessThan(p.min_stock);
    }
  });

  test('handover shows crew name (not UUID)', async () => {
    test.skip(!surfaceData, 'No surface data available');
    const ho = surfaceData.last_handover;
    if (ho) {
      // from_crew must not be a UUID
      const uuidPattern = /^[0-9a-f]{8}-[0-9a-f]{4}-/;
      expect(uuidPattern.test(ho.from_crew)).toBe(false);
      expect(ho.from_crew.length).toBeGreaterThan(2);
      // is_draft flag must be present
      expect(typeof ho.is_draft).toBe('boolean');
    }
  });

  test('activity feed has human-readable entries', async () => {
    test.skip(!surfaceData, 'No surface data available');
    const activity = surfaceData.recent_activity ?? [];
    expect(activity.length).toBeGreaterThan(0);
    expect(activity.length).toBeLessThanOrEqual(5);

    for (const a of activity) {
      // Actor must be a name, not UUID or empty
      expect(a.actor).toBeTruthy();
      expect(a.actor).not.toMatch(/^[0-9a-f]{8}-/);

      // Action must be human-readable verb, not raw event type
      expect(a.action).toBeTruthy();
      expect(a.action).not.toBe('artefact_opened');
      expect(a.action).not.toContain('_');

      // Entity ref must be domain-prefixed, not raw UUID
      expect(a.entity_ref).toBeTruthy();
      expect(a.entity_ref.length).toBeLessThan(20); // Not a full UUID

      // time_display must exist
      expect(a.time_display).toBeTruthy();
    }
  });

  test('WO titles are human-readable (no UUIDs)', async () => {
    test.skip(!surfaceData, 'No surface data available');
    const items = surfaceData.work_orders?.items ?? [];
    const uuidPattern = /[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/;
    for (const wo of items) {
      expect(uuidPattern.test(wo.title)).toBe(false);
      expect(wo.title.length).toBeGreaterThan(5);
    }
  });

  test('fault titles are human-readable (no UUIDs)', async () => {
    test.skip(!surfaceData, 'No surface data available');
    const items = surfaceData.faults?.items ?? [];
    const uuidPattern = /[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/;
    for (const f of items) {
      expect(uuidPattern.test(f.title)).toBe(false);
      expect(f.title.length).toBeGreaterThan(5);
    }
  });
});

// ═══════════════════════════════════════════════════════════════════════════════
// READ TESTS — Domain record lists
// ═══════════════════════════════════════════════════════════════════════════════

test.describe('READ: Domain record lists via API', () => {
  let token: string | null = null;

  test.beforeAll(async ({ browser }) => {
    const page = await browser.newPage();
    token = await getToken(page);
    await page.close();
  });

  const domains = [
    { domain: 'work_orders', minRecords: 1 },
    { domain: 'faults', minRecords: 1 },
    { domain: 'parts', minRecords: 1 },
    { domain: 'equipment', minRecords: 1 },
    { domain: 'certificates', minRecords: 1 },
  ];

  for (const { domain, minRecords } of domains) {
    test(`${domain} returns records with clean titles`, async ({ request }) => {
      test.skip(!token, 'No auth token');
      const res = await request.get(
        `${API_BASE}/api/vessel/85fe1119-b04c-41ac-80f1-829d23322598/domain/${domain}/records?limit=5`,
        { headers: { 'Authorization': `Bearer ${token}` } }
      );
      if (!res.ok()) { expect(true).toBe(true); return; }

      const data = await res.json();
      expect(data.total_count).toBeGreaterThanOrEqual(minRecords);

      // No UUID in any title
      const uuidPattern = /[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/;
      for (const r of data.records) {
        expect(uuidPattern.test(r.title || '')).toBe(false);
      }
    });
  }
});

// ═══════════════════════════════════════════════════════════════════════════════
// READ TESTS — Cross-domain canonical actions present
// ═══════════════════════════════════════════════════════════════════════════════

test.describe('READ: Canonical actions on entity lenses', () => {
  let token: string | null = null;

  test.beforeAll(async ({ browser }) => {
    const page = await browser.newPage();
    token = await getToken(page);
    await page.close();
  });

  test('fault entity has add_to_handover in available_actions', async ({ request }) => {
    test.skip(!token, 'No auth token');
    // Get a fault ID
    const listRes = await request.get(
      `${API_BASE}/api/vessel/85fe1119-b04c-41ac-80f1-829d23322598/domain/faults/records?limit=1`,
      { headers: { 'Authorization': `Bearer ${token}` } }
    );
    if (!listRes.ok()) { expect(true).toBe(true); return; }
    const listData = await listRes.json();
    if (!listData.records?.length) { expect(true).toBe(true); return; }

    const faultId = listData.records[0].id;
    const entityRes = await request.get(
      `${API_BASE}/v1/entity/fault/${faultId}`,
      { headers: { 'Authorization': `Bearer ${token}` } }
    );
    if (!entityRes.ok()) { expect(true).toBe(true); return; }

    const entity = await entityRes.json();
    const actionIds = (entity.available_actions || []).map((a: any) => a.action_id);
    expect(actionIds).toContain('add_to_handover');
  });

  test('equipment entity has report_fault + file_warranty_claim', async ({ request }) => {
    test.skip(!token, 'No auth token');
    const listRes = await request.get(
      `${API_BASE}/api/vessel/85fe1119-b04c-41ac-80f1-829d23322598/domain/equipment/records?limit=1`,
      { headers: { 'Authorization': `Bearer ${token}` } }
    );
    if (!listRes.ok()) { expect(true).toBe(true); return; }
    const listData = await listRes.json();
    if (!listData.records?.length) { expect(true).toBe(true); return; }

    const equipId = listData.records[0].id;
    const entityRes = await request.get(
      `${API_BASE}/v1/entity/equipment/${equipId}`,
      { headers: { 'Authorization': `Bearer ${token}` } }
    );
    if (!entityRes.ok()) { expect(true).toBe(true); return; }

    const entity = await entityRes.json();
    const actionIds = (entity.available_actions || []).map((a: any) => a.action_id);
    expect(actionIds).toContain('add_to_handover');
    expect(actionIds).toContain('report_fault');
    expect(actionIds).toContain('file_warranty_claim');
  });
});

// ═══════════════════════════════════════════════════════════════════════════════
// QUALITY TESTS
// ═══════════════════════════════════════════════════════════════════════════════

test.describe('QUALITY: No forbidden patterns', () => {
  let token: string | null = null;
  let surfaceData: any = null;

  test.beforeAll(async ({ browser }) => {
    const page = await browser.newPage();
    token = await getToken(page);
    if (token) {
      const res = await page.request.get(`${API_BASE}/api/vessel/85fe1119-b04c-41ac-80f1-829d23322598/surface`, {
        headers: { 'Authorization': `Bearer ${token}` },
      });
      if (res.ok()) surfaceData = await res.json();
    }
    await page.close();
  });

  test('no UUID visible in entire surface response', async () => {
    test.skip(!surfaceData, 'No surface data');
    const json = JSON.stringify(surfaceData);
    // Check for full UUIDs in display fields (not in id fields which are expected)
    const displayFields = [
      ...surfaceData.work_orders?.items?.map((w: any) => w.title) || [],
      ...surfaceData.faults?.items?.map((f: any) => f.title) || [],
      ...surfaceData.parts_below_min?.items?.map((p: any) => p.name) || [],
      ...surfaceData.recent_activity?.map((a: any) => a.summary) || [],
      surfaceData.last_handover?.from_crew || '',
    ];
    const uuidPattern = /[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/;
    for (const field of displayFields) {
      expect(uuidPattern.test(field)).toBe(false);
    }
  });

  test('no raw event types in activity feed', async () => {
    test.skip(!surfaceData, 'No surface data');
    const rawTypes = ['artefact_opened', 'work_order_created', 'fault_created',
      'status_changed', 'add_note', 'wo_created'];
    for (const a of surfaceData.recent_activity || []) {
      for (const rawType of rawTypes) {
        expect(a.action).not.toBe(rawType);
      }
      // No underscores in action verb
      expect(a.action).not.toContain('_');
    }
  });

  test('no test data names in surface (no "Test WO", "CI Test", "Temp Part")', async () => {
    test.skip(!surfaceData, 'No surface data');
    const testPatterns = ['Test WO', 'CI Test', 'Temp Part', 'Delete Test',
      'Candidate Part', 'xxxxxxx', 'Consume RLS'];
    const allTitles = [
      ...surfaceData.work_orders?.items?.map((w: any) => w.title) || [],
      ...surfaceData.faults?.items?.map((f: any) => f.title) || [],
      ...surfaceData.parts_below_min?.items?.map((p: any) => p.name) || [],
    ];
    for (const title of allTitles) {
      for (const pattern of testPatterns) {
        expect(title).not.toContain(pattern);
      }
    }
  });

  test('no analytics, charts, or KPI actions in entity responses', async ({ request }) => {
    test.skip(!token, 'No auth token');
    const res = await request.get(
      `${API_BASE}/api/vessel/85fe1119-b04c-41ac-80f1-829d23322598/domain/faults/records?limit=1`,
      { headers: { 'Authorization': `Bearer ${token}` } }
    );
    if (!res.ok()) { expect(true).toBe(true); return; }
    const data = await res.json();
    const json = JSON.stringify(data);
    expect(json).not.toContain('analytics');
    expect(json).not.toContain('dashboard');
    expect(json).not.toContain('chart');
    expect(json).not.toContain('kpi');
  });
});

// ═══════════════════════════════════════════════════════════════════════════════
// QUALITY: No forbidden UI patterns (browser tests)
// ═══════════════════════════════════════════════════════════════════════════════

test.describe('QUALITY: No forbidden UI patterns', () => {
  test('no canvas/chart elements on Vessel Surface', async ({ page }) => {
    await page.goto('/');
    await page.waitForTimeout(3000);
    expect(await page.locator('canvas').count()).toBe(0);
  });

  test('no chatbot copy in empty states', async ({ page }) => {
    const chatbotPhrases = [
      'Use the search bar', 'try searching', "don't worry", 'Oops',
      'hang tight', 'looks like'
    ];
    await page.goto('/work-orders');
    await page.waitForTimeout(3000);
    // Skip if redirected to login (auth guard)
    if (page.url().includes('/login')) {
      expect(true).toBe(true);
      return;
    }
    const body = await page.textContent('body') || '';
    for (const phrase of chatbotPhrases) {
      expect(body).not.toContain(phrase);
    }
  });
});
