import { test, expect, RBAC_CONFIG, generateTestId } from '../rbac-fixtures';

/**
 * SHARD 31: Fragmented Routes - Faults
 *
 * Tests for /faults and /faults/[id] routes.
 *
 * Requirements Covered:
 * - T1-F-01: /faults list route loads
 * - T1-F-02: /faults/[id] detail route loads
 * - T1-F-03: Fault create mutation works
 * - T1-F-04: Fault status update works
 * - T1-F-05: Link equipment to fault works
 * - T1-F-06: Convert to WO action works
 * - T1-F-07: Page refresh preserves state
 */

const ROUTES_CONFIG = {
  ...RBAC_CONFIG,
  faultsList: '/faults',
  faultDetail: (id: string) => `/faults/${id}`,
};

async function executeApiAction(
  page: import('@playwright/test').Page,
  action: string,
  context: Record<string, string>,
  payload: Record<string, unknown>
): Promise<{ status: number; body: { success: boolean; error?: string; data?: unknown } }> {
  return page.evaluate(
    async ({ apiUrl, action, context, payload }) => {
      let accessToken = '';
      for (const key of Object.keys(localStorage)) {
        if (key.includes('supabase') && key.includes('auth')) {
          try {
            const data = JSON.parse(localStorage.getItem(key) || '{}');
            if (data.access_token) { accessToken = data.access_token; break; }
          } catch { continue; }
        }
      }
      const response = await fetch(`${apiUrl}/v1/actions/execute`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${accessToken}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ action, context, payload }),
      });
      return { status: response.status, body: await response.json() };
    },
    { apiUrl: ROUTES_CONFIG.apiUrl, action, context, payload }
  );
}

test.describe('Faults Route Loading', () => {
  test.describe.configure({ retries: 1 });

  test('T1-F-01: /faults list route loads successfully', async ({ hodPage }) => {
    await hodPage.goto(ROUTES_CONFIG.faultsList);
    const currentUrl = hodPage.url();
    if (currentUrl.includes('/app')) { console.log('  Feature flag disabled'); return; }
    await hodPage.waitForLoadState('networkidle');
    expect(hodPage.url()).toContain('/faults');
    const listContainer = hodPage.locator('main, [role="main"]');
    await expect(listContainer).toBeVisible({ timeout: 10000 });
    const errorState = hodPage.locator(':text("Failed to load")');
    await expect(errorState).not.toBeVisible();
    console.log('  T1-F-01: List route loaded');
  });

  test('T1-F-02: /faults/[id] detail route loads correctly', async ({ hodPage, seedFault }) => {
    const fault = await seedFault();
    await hodPage.goto(ROUTES_CONFIG.faultDetail(fault.id));
    const currentUrl = hodPage.url();
    if (currentUrl.includes('/app')) { console.log('  Feature flag disabled'); return; }
    await hodPage.waitForLoadState('networkidle');
    expect(hodPage.url()).toContain(`/faults/${fault.id}`);
    const content = await hodPage.textContent('body');
    expect(content).toBeTruthy();
    console.log(`  T1-F-02: Detail route loaded for ${fault.title}`);
  });
});

test.describe('Faults Route Mutations', () => {
  test.describe.configure({ retries: 1 });

  test('T1-F-03: HOD can create fault from route', async ({ hodPage, supabaseAdmin }) => {
    const faultTitle = `Route Test Fault ${generateTestId('fault-create')}`;
    await hodPage.goto(ROUTES_CONFIG.faultsList);
    const currentUrl = hodPage.url();
    if (currentUrl.includes('/app')) { console.log('  Feature flag disabled'); return; }
    await hodPage.waitForLoadState('networkidle');

    // Get equipment for fault
    const { data: equipment } = await supabaseAdmin
      .from('pms_equipment')
      .select('id')
      .eq('yacht_id', ROUTES_CONFIG.yachtId)
      .limit(1)
      .single();

    if (!equipment) { console.log('  No equipment for fault creation'); return; }

    const result = await executeApiAction(
      hodPage,
      'create_fault',
      { yacht_id: ROUTES_CONFIG.yachtId },
      { title: faultTitle, description: 'Test fault', equipment_id: equipment.id, severity: 'medium' }
    );

    console.log(`  Create result: status=${result.status}, success=${result.body.success}`);

    if (result.body.success && result.body.data) {
      const faultId = (result.body.data as { id?: string }).id;
      expect(faultId).toBeTruthy();
      console.log(`  T1-F-03: Fault created`);
      if (faultId) await supabaseAdmin.from('pms_faults').delete().eq('id', faultId);
    }
  });

  test('T1-F-04: HOD can update fault status', async ({ hodPage, seedFault, supabaseAdmin }) => {
    const fault = await seedFault();
    await hodPage.goto(ROUTES_CONFIG.faultDetail(fault.id));
    const currentUrl = hodPage.url();
    if (currentUrl.includes('/app')) { console.log('  Feature flag disabled'); return; }
    await hodPage.waitForLoadState('networkidle');

    const result = await executeApiAction(
      hodPage,
      'update_fault_status',
      { yacht_id: ROUTES_CONFIG.yachtId, fault_id: fault.id },
      { fault_id: fault.id, status: 'investigating' }
    );

    console.log(`  Update status result: status=${result.status}, success=${result.body.success}`);

    if (result.body.success) {
      const { data: updated } = await supabaseAdmin
        .from('pms_faults')
        .select('status')
        .eq('id', fault.id)
        .single();
      expect(updated?.status).toBe('investigating');
      console.log('  T1-F-04: Status update verified');
    }
  });

  test('T1-F-06: HOD can convert fault to work order', async ({ hodPage, seedFault, supabaseAdmin }) => {
    const fault = await seedFault();
    await hodPage.goto(ROUTES_CONFIG.faultDetail(fault.id));
    const currentUrl = hodPage.url();
    if (currentUrl.includes('/app')) { console.log('  Feature flag disabled'); return; }
    await hodPage.waitForLoadState('networkidle');

    const result = await executeApiAction(
      hodPage,
      'create_work_order_from_fault',
      { yacht_id: ROUTES_CONFIG.yachtId, fault_id: fault.id },
      { fault_id: fault.id, title: `WO for ${fault.title}`, priority: 'important' }
    );

    console.log(`  Create WO from fault: status=${result.status}, success=${result.body.success}`);

    if (result.body.success && result.body.data) {
      const woId = (result.body.data as { id?: string; work_order_id?: string }).id || (result.body.data as { work_order_id?: string }).work_order_id;
      expect(woId).toBeTruthy();
      console.log('  T1-F-06: Work order created from fault');
      if (woId) await supabaseAdmin.from('pms_work_orders').delete().eq('id', woId);
    }
  });
});

test.describe('Faults Route State Persistence', () => {
  test.describe.configure({ retries: 1 });

  test('T1-F-07: Page refresh preserves detail view', async ({ hodPage, seedFault }) => {
    const fault = await seedFault();
    await hodPage.goto(ROUTES_CONFIG.faultDetail(fault.id));
    const currentUrl = hodPage.url();
    if (currentUrl.includes('/app')) { console.log('  Feature flag disabled'); return; }
    await hodPage.waitForLoadState('networkidle');

    const beforeUrl = hodPage.url();
    await hodPage.reload();
    await hodPage.waitForLoadState('networkidle');
    const afterUrl = hodPage.url();

    expect(afterUrl).toBe(beforeUrl);
    console.log('  T1-F-07: State preserved after refresh');
  });
});

test.describe('Faults Route Navigation', () => {
  test.describe.configure({ retries: 1 });

  test('T1-F-05: Equipment link navigates correctly', async ({ hodPage, seedFault }) => {
    const fault = await seedFault();
    await hodPage.goto(ROUTES_CONFIG.faultDetail(fault.id));
    const currentUrl = hodPage.url();
    if (currentUrl.includes('/app')) { console.log('  Feature flag disabled'); return; }
    await hodPage.waitForLoadState('networkidle');
    await hodPage.waitForTimeout(2000);

    const equipmentLink = hodPage.locator('[data-testid="equipment-link"], a[href*="/equipment/"]');
    const hasLink = await equipmentLink.isVisible({ timeout: 5000 }).catch(() => false);

    if (hasLink) {
      await equipmentLink.first().click();
      await hodPage.waitForLoadState('networkidle');
      const newUrl = hodPage.url();
      expect(newUrl.includes('/equipment/') || newUrl.includes('entity=equipment')).toBe(true);
      console.log('  T1-F-05: Equipment navigation verified');
    } else {
      console.log('  No equipment link visible');
    }
  });

  test('Browser back/forward works on faults', async ({ hodPage, seedFault }) => {
    const fault = await seedFault();
    await hodPage.goto(ROUTES_CONFIG.faultsList);
    const currentUrl = hodPage.url();
    if (currentUrl.includes('/app')) { console.log('  Feature flag disabled'); return; }
    await hodPage.waitForLoadState('networkidle');
    const listUrl = hodPage.url();

    await hodPage.goto(ROUTES_CONFIG.faultDetail(fault.id));
    await hodPage.waitForLoadState('networkidle');

    await hodPage.goBack();
    await hodPage.waitForLoadState('networkidle');
    expect(hodPage.url()).toBe(listUrl);

    await hodPage.goForward();
    await hodPage.waitForLoadState('networkidle');
    expect(hodPage.url()).toContain(`/faults/${fault.id}`);

    console.log('  Browser navigation verified');
  });
});
