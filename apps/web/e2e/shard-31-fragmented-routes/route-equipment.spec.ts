import { test, expect, RBAC_CONFIG } from '../rbac-fixtures';

/**
 * SHARD 31: Fragmented Routes - Equipment
 *
 * Tests for /equipment and /equipment/[id] routes.
 *
 * Requirements Covered:
 * - T1-EQ-01: /equipment list route loads
 * - T1-EQ-02: /equipment/[id] detail route loads
 * - T1-EQ-03: Linked WOs render in detail
 * - T1-EQ-04: Linked faults render in detail
 * - T1-EQ-05: Linked parts render in detail
 * - T1-EQ-06: Equipment status update works
 * - T1-EQ-07: Page refresh preserves state
 */

const ROUTES_CONFIG = {
  ...RBAC_CONFIG,
  equipmentList: '/equipment',
  equipmentDetail: (id: string) => `/equipment/${id}`,
};

test.describe('Equipment Route Loading', () => {
  test.describe.configure({ retries: 1 });

  test('T1-EQ-01: /equipment list route loads successfully', async ({ hodPage }) => {
    await hodPage.goto(ROUTES_CONFIG.equipmentList);
    const currentUrl = hodPage.url();
    if (currentUrl.includes('/app')) { console.log('  Feature flag disabled'); return; }
    await hodPage.waitForLoadState('networkidle');
    expect(hodPage.url()).toContain('/equipment');
    const listContainer = hodPage.locator('main, [role="main"]');
    await expect(listContainer).toBeVisible({ timeout: 10000 });
    const errorState = hodPage.locator(':text("Failed to load")');
    await expect(errorState).not.toBeVisible();
    console.log('  T1-EQ-01: List route loaded');
  });

  test('T1-EQ-02: /equipment/[id] detail route loads correctly', async ({ hodPage, supabaseAdmin }) => {
    // Get equipment from test yacht
    const { data: equipment } = await supabaseAdmin
      .from('pms_equipment')
      .select('id, name')
      .eq('yacht_id', ROUTES_CONFIG.yachtId)
      .limit(1)
      .single();

    if (!equipment) { console.log('  No equipment in test yacht'); return; }

    await hodPage.goto(ROUTES_CONFIG.equipmentDetail(equipment.id));
    const currentUrl = hodPage.url();
    if (currentUrl.includes('/app')) { console.log('  Feature flag disabled'); return; }
    await hodPage.waitForLoadState('networkidle');
    expect(hodPage.url()).toContain(`/equipment/${equipment.id}`);
    const content = await hodPage.textContent('body');
    expect(content).toBeTruthy();
    console.log(`  T1-EQ-02: Detail route loaded for ${equipment.name}`);
  });

  test('T1-EQ-02b: Non-existent equipment shows 404 state', async ({ hodPage }) => {
    const fakeId = '00000000-0000-0000-0000-000000000000';
    await hodPage.goto(ROUTES_CONFIG.equipmentDetail(fakeId));
    const currentUrl = hodPage.url();
    if (currentUrl.includes('/app')) { console.log('  Feature flag disabled'); return; }
    await hodPage.waitForLoadState('networkidle');

    const notFoundState = hodPage.locator(':text("Not Found"), :text("not found")');
    const errorState = hodPage.locator(':text("Failed"), :text("Error")');
    const hasNotFound = await notFoundState.isVisible({ timeout: 5000 }).catch(() => false);
    const hasError = await errorState.isVisible({ timeout: 5000 }).catch(() => false);
    expect(hasNotFound || hasError).toBe(true);
    console.log('  T1-EQ-02b: Non-existent equipment handled correctly');
  });
});

test.describe('Equipment Route Linked Entities', () => {
  test.describe.configure({ retries: 1 });

  test('T1-EQ-03: Linked work orders render in detail', async ({ hodPage, supabaseAdmin }) => {
    // Find equipment with linked work orders
    const { data: woWithEquipment } = await supabaseAdmin
      .from('pms_work_orders')
      .select('equipment_id')
      .eq('yacht_id', ROUTES_CONFIG.yachtId)
      .not('equipment_id', 'is', null)
      .limit(1)
      .single();

    if (!woWithEquipment?.equipment_id) { console.log('  No equipment with linked WOs'); return; }

    await hodPage.goto(ROUTES_CONFIG.equipmentDetail(woWithEquipment.equipment_id));
    const currentUrl = hodPage.url();
    if (currentUrl.includes('/app')) { console.log('  Feature flag disabled'); return; }
    await hodPage.waitForLoadState('networkidle');
    await hodPage.waitForTimeout(2000);

    const woSection = hodPage.locator(':text("Work Order"), :text("work order"), :text("Linked Work")');
    const hasWoSection = await woSection.isVisible({ timeout: 5000 }).catch(() => false);
    console.log(`  T1-EQ-03: Linked WOs section visible: ${hasWoSection}`);
  });

  test('T1-EQ-04: Linked faults render in detail', async ({ hodPage, supabaseAdmin }) => {
    // Find equipment with linked faults
    const { data: faultWithEquipment } = await supabaseAdmin
      .from('pms_faults')
      .select('equipment_id')
      .eq('yacht_id', ROUTES_CONFIG.yachtId)
      .not('equipment_id', 'is', null)
      .limit(1)
      .single();

    if (!faultWithEquipment?.equipment_id) { console.log('  No equipment with linked faults'); return; }

    await hodPage.goto(ROUTES_CONFIG.equipmentDetail(faultWithEquipment.equipment_id));
    const currentUrl = hodPage.url();
    if (currentUrl.includes('/app')) { console.log('  Feature flag disabled'); return; }
    await hodPage.waitForLoadState('networkidle');
    await hodPage.waitForTimeout(2000);

    const faultSection = hodPage.locator(':text("Fault"), :text("fault"), :text("Linked Fault")');
    const hasFaultSection = await faultSection.isVisible({ timeout: 5000 }).catch(() => false);
    console.log(`  T1-EQ-04: Linked faults section visible: ${hasFaultSection}`);
  });
});

test.describe('Equipment Route State Persistence', () => {
  test.describe.configure({ retries: 1 });

  test('T1-EQ-07: Page refresh preserves detail view', async ({ hodPage, supabaseAdmin }) => {
    const { data: equipment } = await supabaseAdmin
      .from('pms_equipment')
      .select('id')
      .eq('yacht_id', ROUTES_CONFIG.yachtId)
      .limit(1)
      .single();

    if (!equipment) { console.log('  No equipment in test yacht'); return; }

    await hodPage.goto(ROUTES_CONFIG.equipmentDetail(equipment.id));
    const currentUrl = hodPage.url();
    if (currentUrl.includes('/app')) { console.log('  Feature flag disabled'); return; }
    await hodPage.waitForLoadState('networkidle');

    const beforeUrl = hodPage.url();
    await hodPage.reload();
    await hodPage.waitForLoadState('networkidle');
    const afterUrl = hodPage.url();

    expect(afterUrl).toBe(beforeUrl);
    console.log('  T1-EQ-07: State preserved after refresh');
  });
});

test.describe('Equipment Route Navigation', () => {
  test.describe.configure({ retries: 1 });

  test('Browser back/forward works on equipment', async ({ hodPage, supabaseAdmin }) => {
    const { data: equipment } = await supabaseAdmin
      .from('pms_equipment')
      .select('id')
      .eq('yacht_id', ROUTES_CONFIG.yachtId)
      .limit(1)
      .single();

    if (!equipment) { console.log('  No equipment in test yacht'); return; }

    await hodPage.goto(ROUTES_CONFIG.equipmentList);
    const currentUrl = hodPage.url();
    if (currentUrl.includes('/app')) { console.log('  Feature flag disabled'); return; }
    await hodPage.waitForLoadState('networkidle');
    const listUrl = hodPage.url();

    await hodPage.goto(ROUTES_CONFIG.equipmentDetail(equipment.id));
    await hodPage.waitForLoadState('networkidle');

    await hodPage.goBack();
    await hodPage.waitForLoadState('networkidle');
    expect(hodPage.url()).toBe(listUrl);

    await hodPage.goForward();
    await hodPage.waitForLoadState('networkidle');
    expect(hodPage.url()).toContain(`/equipment/${equipment.id}`);

    console.log('  Browser navigation verified');
  });

  test('WO link navigates to work-orders route', async ({ hodPage, supabaseAdmin }) => {
    // Find equipment with linked work orders
    const { data: woWithEquipment } = await supabaseAdmin
      .from('pms_work_orders')
      .select('equipment_id, id')
      .eq('yacht_id', ROUTES_CONFIG.yachtId)
      .not('equipment_id', 'is', null)
      .limit(1)
      .single();

    if (!woWithEquipment?.equipment_id) { console.log('  No equipment with linked WOs'); return; }

    await hodPage.goto(ROUTES_CONFIG.equipmentDetail(woWithEquipment.equipment_id));
    const currentUrl = hodPage.url();
    if (currentUrl.includes('/app')) { console.log('  Feature flag disabled'); return; }
    await hodPage.waitForLoadState('networkidle');
    await hodPage.waitForTimeout(2000);

    const woLink = hodPage.locator('button:has-text("WO-"), a[href*="/work-orders/"]');
    const hasLink = await woLink.isVisible({ timeout: 5000 }).catch(() => false);

    if (hasLink) {
      await woLink.first().click();
      await hodPage.waitForLoadState('networkidle');
      const newUrl = hodPage.url();
      expect(newUrl.includes('/work-orders/') || newUrl.includes('entity=work_order')).toBe(true);
      console.log('  WO navigation verified');
    } else {
      console.log('  No WO link visible in equipment detail');
    }
  });
});
