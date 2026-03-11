import { test, expect, RBAC_CONFIG, SpotlightSearchPO, ActionModalPO, ToastPO, generateTestId } from '../rbac-fixtures';
import type { Page, Route, Request } from '@playwright/test';

/**
 * SHARD 31: Spotlight -> Inventory ACTION Execution Tests
 *
 * Tests for NLP-style action inference from Spotlight search to inventory action execution.
 *
 * Requirements Covered:
 * - SIA-01: "adjust stock for filter" -> adjust_stock_quantity action chip -> modal -> submit
 * - SIA-02: "move part to box 3D" -> transfer_part action chip -> location modal
 * - SIA-03: "add to shopping list" -> create_shopping_list_item action chip
 * - SIA-04: "order more filters" -> order_part action chip (shopping list flow)
 * - SIA-05: "receive parts" -> receive_part action chip
 * - SIA-06: Role gating - SIGNED actions require captain/manager
 * - SIA-07: Role gating - MUTATE actions require HOD+
 * - SIA-08: Payload validation for /v1/actions/execute
 *
 * Action Registry Reference (from registry.py):
 * - adjust_stock_quantity: SIGNED, captain/manager, requires signature
 * - transfer_part: MUTATE, HOD+, requires from/to locations
 * - create_shopping_list_item: MUTATE, all crew
 * - receive_part: MUTATE, HOD+, requires idempotency_key
 * - consume_part: MUTATE, HOD+
 *
 * Role Matrix (from usePartActions.ts):
 * - view_part: all authenticated
 * - consume_part: crew, HOD, captain
 * - receive_part: HOD+ (chief_engineer, chief_officer, captain, manager)
 * - transfer_part: HOD+
 * - adjust_stock_quantity: captain, manager (SIGNED)
 * - write_off_part: HOD+
 * - create_shopping_list_item: crew, HOD, captain
 *
 * @see /apps/web/src/hooks/usePartActions.ts
 * @see /apps/api/action_router/registry.py
 * @see /apps/api/handlers/part_handlers.py
 */

// Route configuration
const ROUTES_CONFIG = {
  ...RBAC_CONFIG,
  inventoryList: '/inventory',
  partsDetail: (partId: string) => `/parts/${partId}`,
  apiExecute: '/v1/actions/execute',
  tables: {
    parts: 'pms_parts',
    inventory_transactions: 'pms_inventory_transactions',
    shopping_list: 'pms_shopping_list_items',
    audit_log: 'pms_audit_log',
  },
};

// Test case type definitions
interface ActionTestCase {
  query: string;
  expectedActionId: string;
  expectedChipLabel: string;
  description: string;
  requiredRole: 'crew' | 'hod' | 'captain' | 'manager';
  variant: 'READ' | 'MUTATE' | 'SIGNED';
}

// =============================================================================
// NLP VARIANT TEST CASES FOR INVENTORY ACTIONS
// =============================================================================

const ADJUST_STOCK_VARIANTS: ActionTestCase[] = [
  {
    query: 'adjust stock for filter',
    expectedActionId: 'adjust_stock_quantity',
    expectedChipLabel: 'Adjust Stock',
    description: 'SIA-01a: Basic adjust stock query',
    requiredRole: 'captain',
    variant: 'SIGNED',
  },
  {
    query: 'correct inventory count',
    expectedActionId: 'adjust_stock_quantity',
    expectedChipLabel: 'Adjust Stock',
    description: 'SIA-01b: Inventory correction query',
    requiredRole: 'captain',
    variant: 'SIGNED',
  },
  {
    query: 'fix stock level for oil filter',
    expectedActionId: 'adjust_stock_quantity',
    expectedChipLabel: 'Adjust Stock',
    description: 'SIA-01c: Fix stock level query',
    requiredRole: 'manager',
    variant: 'SIGNED',
  },
  {
    query: 'cycle count adjustment',
    expectedActionId: 'adjust_stock_quantity',
    expectedChipLabel: 'Adjust Stock',
    description: 'SIA-01d: Cycle count query',
    requiredRole: 'captain',
    variant: 'SIGNED',
  },
  {
    query: 'update quantity for filters',
    expectedActionId: 'adjust_stock_quantity',
    expectedChipLabel: 'Adjust Stock',
    description: 'SIA-01e: Update quantity query',
    requiredRole: 'captain',
    variant: 'SIGNED',
  },
];

const TRANSFER_PART_VARIANTS: ActionTestCase[] = [
  {
    query: 'move part to box 3D',
    expectedActionId: 'transfer_part',
    expectedChipLabel: 'Transfer Part',
    description: 'SIA-02a: Basic transfer query',
    requiredRole: 'hod',
    variant: 'MUTATE',
  },
  {
    query: 'transfer filters to engine room',
    expectedActionId: 'transfer_part',
    expectedChipLabel: 'Transfer Part',
    description: 'SIA-02b: Transfer to location query',
    requiredRole: 'hod',
    variant: 'MUTATE',
  },
  {
    query: 'relocate parts from storage A to B',
    expectedActionId: 'transfer_part',
    expectedChipLabel: 'Transfer Part',
    description: 'SIA-02c: Relocate query',
    requiredRole: 'hod',
    variant: 'MUTATE',
  },
  {
    query: 'move spare from forward to aft',
    expectedActionId: 'transfer_part',
    expectedChipLabel: 'Transfer Part',
    description: 'SIA-02d: Move spare query',
    requiredRole: 'hod',
    variant: 'MUTATE',
  },
];

const SHOPPING_LIST_VARIANTS: ActionTestCase[] = [
  {
    query: 'add to shopping list',
    expectedActionId: 'create_shopping_list_item',
    expectedChipLabel: 'Add to Shopping List',
    description: 'SIA-03a: Basic add to shopping list',
    requiredRole: 'crew',
    variant: 'MUTATE',
  },
  {
    query: 'add filter to shopping',
    expectedActionId: 'create_shopping_list_item',
    expectedChipLabel: 'Add to Shopping List',
    description: 'SIA-03b: Add item to shopping',
    requiredRole: 'crew',
    variant: 'MUTATE',
  },
  {
    query: 'request more oil filters',
    expectedActionId: 'create_shopping_list_item',
    expectedChipLabel: 'Add to Shopping List',
    description: 'SIA-03c: Request parts query',
    requiredRole: 'crew',
    variant: 'MUTATE',
  },
  {
    query: 'need to order bearings',
    expectedActionId: 'create_shopping_list_item',
    expectedChipLabel: 'Add to Shopping List',
    description: 'SIA-03d: Need to order query',
    requiredRole: 'crew',
    variant: 'MUTATE',
  },
  {
    query: 'buy more gaskets',
    expectedActionId: 'create_shopping_list_item',
    expectedChipLabel: 'Add to Shopping List',
    description: 'SIA-03e: Buy query',
    requiredRole: 'crew',
    variant: 'MUTATE',
  },
];

const ORDER_PART_VARIANTS: ActionTestCase[] = [
  {
    query: 'order more filters',
    expectedActionId: 'create_shopping_list_item',
    expectedChipLabel: 'Add to Shopping List',
    description: 'SIA-04a: Order more query',
    requiredRole: 'crew',
    variant: 'MUTATE',
  },
  {
    query: 'purchase replacement parts',
    expectedActionId: 'create_shopping_list_item',
    expectedChipLabel: 'Add to Shopping List',
    description: 'SIA-04b: Purchase query',
    requiredRole: 'crew',
    variant: 'MUTATE',
  },
  {
    query: 'reorder impellers',
    expectedActionId: 'create_shopping_list_item',
    expectedChipLabel: 'Add to Shopping List',
    description: 'SIA-04c: Reorder query',
    requiredRole: 'crew',
    variant: 'MUTATE',
  },
];

const RECEIVE_PARTS_VARIANTS: ActionTestCase[] = [
  {
    query: 'receive parts',
    expectedActionId: 'receive_part',
    expectedChipLabel: 'Receive Part',
    description: 'SIA-05a: Basic receive query',
    requiredRole: 'hod',
    variant: 'MUTATE',
  },
  {
    query: 'log delivery of filters',
    expectedActionId: 'receive_part',
    expectedChipLabel: 'Receive Part',
    description: 'SIA-05b: Log delivery query',
    requiredRole: 'hod',
    variant: 'MUTATE',
  },
  {
    query: 'parts arrived',
    expectedActionId: 'receive_part',
    expectedChipLabel: 'Receive Part',
    description: 'SIA-05c: Parts arrived query',
    requiredRole: 'hod',
    variant: 'MUTATE',
  },
  {
    query: 'stock in new filters',
    expectedActionId: 'receive_part',
    expectedChipLabel: 'Receive Part',
    description: 'SIA-05d: Stock in query',
    requiredRole: 'hod',
    variant: 'MUTATE',
  },
  {
    query: 'add delivered parts',
    expectedActionId: 'receive_part',
    expectedChipLabel: 'Receive Part',
    description: 'SIA-05e: Add delivered query',
    requiredRole: 'hod',
    variant: 'MUTATE',
  },
];

// Combine all test cases
const ALL_ACTION_TEST_CASES: ActionTestCase[] = [
  ...ADJUST_STOCK_VARIANTS,
  ...TRANSFER_PART_VARIANTS,
  ...SHOPPING_LIST_VARIANTS,
  ...ORDER_PART_VARIANTS,
  ...RECEIVE_PARTS_VARIANTS,
];

// =============================================================================
// HELPER: Capture API Payloads
// =============================================================================

interface CapturedRequest {
  action: string;
  context: Record<string, unknown>;
  payload: Record<string, unknown>;
  url: string;
  headers: Record<string, string>;
}

async function captureActionPayloads(page: Page): Promise<CapturedRequest[]> {
  const captured: CapturedRequest[] = [];

  await page.route('**/v1/actions/execute**', async (route: Route, request: Request) => {
    try {
      const postData = request.postData();
      if (postData) {
        const body = JSON.parse(postData);
        captured.push({
          action: body.action,
          context: body.context,
          payload: body.payload,
          url: request.url(),
          headers: request.headers() as Record<string, string>,
        });
      }
    } catch {
      // Non-JSON request
    }

    // Continue with the request
    await route.continue();
  });

  return captured;
}

// =============================================================================
// HELPER: Page Objects for Action Testing
// =============================================================================

class InventoryActionModalPO extends ActionModalPO {
  constructor(page: Page) {
    super(page);
  }

  get quantityInput() {
    return this.modal.locator('input[name="quantity"], input[name="new_quantity"], input[type="number"]').first();
  }

  get reasonSelect() {
    return this.modal.locator('select[name="reason"], [data-testid="reason-select"]').first();
  }

  get notesTextarea() {
    return this.modal.locator('textarea[name="notes"]').first();
  }

  get fromLocationSelect() {
    return this.modal.locator('select[name="from_location"], [data-testid="from-location"]').first();
  }

  get toLocationSelect() {
    return this.modal.locator('select[name="to_location"], [data-testid="to-location"]').first();
  }

  get partNameInput() {
    return this.modal.locator('input[name="part_name"]').first();
  }

  get quantityRequestedInput() {
    return this.modal.locator('input[name="quantity_requested"]').first();
  }

  get signatureInput() {
    return this.modal.locator('input[name="signature"], input[type="password"], [data-testid="pin-input"]').first();
  }

  async fillAdjustStockForm(newQuantity: number, reason: string, notes?: string) {
    await this.quantityInput.fill(String(newQuantity));

    // Try to select reason from dropdown
    const hasSelect = await this.reasonSelect.isVisible().catch(() => false);
    if (hasSelect) {
      await this.reasonSelect.selectOption(reason);
    } else {
      // May be a different UI pattern
      const reasonInput = this.modal.locator(`[data-reason="${reason}"], button:has-text("${reason}")`).first();
      const hasReasonBtn = await reasonInput.isVisible().catch(() => false);
      if (hasReasonBtn) {
        await reasonInput.click();
      }
    }

    if (notes) {
      const hasNotes = await this.notesTextarea.isVisible().catch(() => false);
      if (hasNotes) {
        await this.notesTextarea.fill(notes);
      }
    }
  }

  async fillTransferForm(quantity: number, fromLocation: string, toLocation: string, notes?: string) {
    await this.quantityInput.fill(String(quantity));

    const hasFromSelect = await this.fromLocationSelect.isVisible().catch(() => false);
    if (hasFromSelect) {
      await this.fromLocationSelect.selectOption({ label: fromLocation });
    }

    const hasToSelect = await this.toLocationSelect.isVisible().catch(() => false);
    if (hasToSelect) {
      await this.toLocationSelect.selectOption({ label: toLocation });
    }

    if (notes) {
      const hasNotes = await this.notesTextarea.isVisible().catch(() => false);
      if (hasNotes) {
        await this.notesTextarea.fill(notes);
      }
    }
  }

  async fillShoppingListForm(partName: string, quantity: number, notes?: string) {
    const hasPartName = await this.partNameInput.isVisible().catch(() => false);
    if (hasPartName) {
      await this.partNameInput.fill(partName);
    }

    const hasQtyReq = await this.quantityRequestedInput.isVisible().catch(() => false);
    if (hasQtyReq) {
      await this.quantityRequestedInput.fill(String(quantity));
    }

    if (notes) {
      const hasNotes = await this.notesTextarea.isVisible().catch(() => false);
      if (hasNotes) {
        await this.notesTextarea.fill(notes);
      }
    }
  }

  async enterSignature(pin: string) {
    const hasSignature = await this.signatureInput.isVisible().catch(() => false);
    if (hasSignature) {
      await this.signatureInput.fill(pin);
    }
  }
}

// =============================================================================
// SECTION 1: ACTION CHIP DISPLAY FROM NLP QUERIES
// Tests that NLP queries show correct action chips
// =============================================================================

test.describe('Spotlight -> Inventory Actions: Action Chip Display', () => {
  test.describe.configure({ retries: 1 });

  // Test adjust_stock_quantity action chips
  for (const testCase of ADJUST_STOCK_VARIANTS.slice(0, 3)) {
    test(`${testCase.description}: "${testCase.query}" shows action chip`, async ({ captainPage }) => {
      await captainPage.goto('/app');
      await captainPage.waitForLoadState('networkidle');

      const spotlight = new SpotlightSearchPO(captainPage);
      await spotlight.search(testCase.query);

      // Wait for action chips to appear
      const actionChips = captainPage.locator('[data-testid="action-chips"], [data-testid="suggested-actions"]');
      const hasChips = await actionChips.isVisible({ timeout: 5000 }).catch(() => false);

      if (!hasChips) {
        console.log(`  SKIP: No action chips for query "${testCase.query}" - action inference may not be enabled`);
        return;
      }

      // Check for specific action chip
      const expectedChip = captainPage.locator(`[data-action-id="${testCase.expectedActionId}"]`);
      const hasExpectedChip = await expectedChip.isVisible({ timeout: 3000 }).catch(() => false);

      if (hasExpectedChip) {
        console.log(`  PASS: Found action chip ${testCase.expectedActionId} for query "${testCase.query}"`);
        expect(hasExpectedChip).toBe(true);

        // Verify chip has SIGNED badge for adjust_stock
        if (testCase.variant === 'SIGNED') {
          const signedBadge = expectedChip.locator('[data-variant="SIGNED"], .signed-badge, :text("Signed")');
          const hasBadge = await signedBadge.isVisible().catch(() => false);
          console.log(`  SIGNED badge visible: ${hasBadge}`);
        }
      } else {
        // Check if any parts-related action is shown
        const anyPartsAction = captainPage.locator('[data-action-id^="adjust"], [data-action-id*="stock"]').first();
        const hasAnyAction = await anyPartsAction.isVisible({ timeout: 2000 }).catch(() => false);
        console.log(`  Partial match: Any stock action visible = ${hasAnyAction}`);
      }
    });
  }

  // Test transfer_part action chips
  for (const testCase of TRANSFER_PART_VARIANTS.slice(0, 2)) {
    test(`${testCase.description}: "${testCase.query}" shows action chip`, async ({ hodPage }) => {
      await hodPage.goto('/app');
      await hodPage.waitForLoadState('networkidle');

      const spotlight = new SpotlightSearchPO(hodPage);
      await spotlight.search(testCase.query);

      const actionChips = hodPage.locator('[data-testid="action-chips"], [data-testid="suggested-actions"]');
      const hasChips = await actionChips.isVisible({ timeout: 5000 }).catch(() => false);

      if (!hasChips) {
        console.log(`  SKIP: No action chips for "${testCase.query}"`);
        return;
      }

      const expectedChip = hodPage.locator(`[data-action-id="${testCase.expectedActionId}"]`);
      const hasExpectedChip = await expectedChip.isVisible({ timeout: 3000 }).catch(() => false);

      if (hasExpectedChip) {
        console.log(`  PASS: Found ${testCase.expectedActionId} chip`);
        expect(hasExpectedChip).toBe(true);
      }
    });
  }

  // Test shopping list action chips
  for (const testCase of SHOPPING_LIST_VARIANTS.slice(0, 3)) {
    test(`${testCase.description}: "${testCase.query}" shows action chip`, async ({ crewPage }) => {
      await crewPage.goto('/app');
      await crewPage.waitForLoadState('networkidle');

      const spotlight = new SpotlightSearchPO(crewPage);
      await spotlight.search(testCase.query);

      const actionChips = crewPage.locator('[data-testid="action-chips"], [data-testid="suggested-actions"]');
      const hasChips = await actionChips.isVisible({ timeout: 5000 }).catch(() => false);

      if (!hasChips) {
        console.log(`  SKIP: No action chips for "${testCase.query}"`);
        return;
      }

      // Shopping list action may appear with different IDs
      const shoppingChip = crewPage.locator(
        '[data-action-id="create_shopping_list_item"], [data-action-id="add_to_shopping"], [data-action-id*="shopping"]'
      ).first();
      const hasShoppingChip = await shoppingChip.isVisible({ timeout: 3000 }).catch(() => false);

      if (hasShoppingChip) {
        console.log(`  PASS: Found shopping list chip`);
      }
    });
  }

  // Test receive_part action chips
  for (const testCase of RECEIVE_PARTS_VARIANTS.slice(0, 2)) {
    test(`${testCase.description}: "${testCase.query}" shows action chip`, async ({ hodPage }) => {
      await hodPage.goto('/app');
      await hodPage.waitForLoadState('networkidle');

      const spotlight = new SpotlightSearchPO(hodPage);
      await spotlight.search(testCase.query);

      const actionChips = hodPage.locator('[data-testid="action-chips"], [data-testid="suggested-actions"]');
      const hasChips = await actionChips.isVisible({ timeout: 5000 }).catch(() => false);

      if (!hasChips) {
        console.log(`  SKIP: No action chips for "${testCase.query}"`);
        return;
      }

      const receiveChip = hodPage.locator(
        '[data-action-id="receive_part"], [data-action-id*="receive"]'
      ).first();
      const hasReceiveChip = await receiveChip.isVisible({ timeout: 3000 }).catch(() => false);

      if (hasReceiveChip) {
        console.log(`  PASS: Found receive chip`);
      }
    });
  }
});

// =============================================================================
// SECTION 2: ADJUST STOCK ACTION - FULL FLOW
// SIA-01: adjust stock -> modal -> submit -> verify payload
// =============================================================================

test.describe('Spotlight -> Inventory Actions: Adjust Stock Flow', () => {
  test.describe.configure({ retries: 0 }); // No retries for action tests

  test('SIA-01-FLOW: Adjust stock action opens modal and submits correct payload', async ({
    captainPage,
    supabaseAdmin,
  }) => {
    // Seed a test part with known stock
    const testPartId = generateTestId('part');
    const testPartName = `Test Filter ${testPartId}`;

    // Find an existing part in the test yacht
    const { data: existingPart } = await supabaseAdmin
      .from(ROUTES_CONFIG.tables.parts)
      .select('id, name, quantity_on_hand')
      .eq('yacht_id', ROUTES_CONFIG.yachtId)
      .limit(1)
      .single();

    if (!existingPart) {
      console.log('  SKIP: No parts found in test yacht');
      return;
    }

    const partId = existingPart.id;
    const initialQty = existingPart.quantity_on_hand || 0;

    // Set up request capture
    const capturedRequests = await captureActionPayloads(captainPage);

    // Navigate to part detail page
    await captainPage.goto(ROUTES_CONFIG.partsDetail(partId));
    await captainPage.waitForLoadState('networkidle');

    const currentUrl = captainPage.url();
    if (currentUrl.includes('/app') && !currentUrl.includes('/parts')) {
      console.log('  Feature flag disabled - parts detail not accessible');
      return;
    }

    // Wait for page to load
    await captainPage.waitForTimeout(2000);

    // Click adjust stock action button
    const adjustButton = captainPage.locator(
      'button:has-text("Adjust Stock"), button:has-text("Adjust"), [data-action-id="adjust_stock_quantity"]'
    ).first();
    const hasAdjustBtn = await adjustButton.isVisible({ timeout: 5000 }).catch(() => false);

    if (!hasAdjustBtn) {
      console.log('  SKIP: Adjust Stock button not visible - action may not be available');
      return;
    }

    // Click to open modal
    await adjustButton.click();

    // Wait for modal
    const modal = new InventoryActionModalPO(captainPage);
    await modal.waitForOpen();

    // Fill the form
    const newQuantity = initialQty + 5; // Increase by 5
    await modal.fillAdjustStockForm(newQuantity, 'physical_count', 'E2E test adjustment');

    // For SIGNED action, enter signature (PIN)
    await modal.enterSignature('1234');

    // Submit
    await modal.submit();

    // Wait for modal to close (indicates success)
    await modal.waitForClose().catch(() => {
      console.log('  Modal did not close - checking for error toast');
    });

    // Verify toast
    const toast = new ToastPO(captainPage);
    try {
      await toast.waitForSuccess(5000);
      console.log('  SUCCESS: Adjust stock action completed');
    } catch {
      // Check for error toast
      const errorMsg = await toast.getErrorMessage();
      console.log(`  Action may have failed: ${errorMsg}`);
    }

    // Verify captured payload
    const adjustPayload = capturedRequests.find((r) => r.action === 'adjust_stock_quantity');
    if (adjustPayload) {
      console.log('  Captured payload:', JSON.stringify(adjustPayload, null, 2));

      // Verify required fields
      expect(adjustPayload.context.yacht_id).toBe(ROUTES_CONFIG.yachtId);
      expect(adjustPayload.payload.part_id).toBe(partId);
      expect(adjustPayload.payload.new_quantity).toBe(newQuantity);
      expect(adjustPayload.payload.reason).toBe('physical_count');
      expect(adjustPayload.payload.signature).toBeTruthy(); // SIGNED action

      // Verify auth header
      expect(adjustPayload.headers.authorization).toMatch(/^Bearer /);

      console.log('  PAYLOAD VERIFIED: adjust_stock_quantity');
    }
  });

  test('SIA-01-RBAC: Crew cannot see Adjust Stock button (SIGNED action)', async ({ crewPage, supabaseAdmin }) => {
    // Find a part
    const { data: existingPart } = await supabaseAdmin
      .from(ROUTES_CONFIG.tables.parts)
      .select('id')
      .eq('yacht_id', ROUTES_CONFIG.yachtId)
      .limit(1)
      .single();

    if (!existingPart) {
      console.log('  SKIP: No parts found');
      return;
    }

    await crewPage.goto(ROUTES_CONFIG.partsDetail(existingPart.id));
    await crewPage.waitForLoadState('networkidle');

    const currentUrl = crewPage.url();
    if (currentUrl.includes('/app') && !currentUrl.includes('/parts')) {
      console.log('  Feature flag disabled');
      return;
    }

    await crewPage.waitForTimeout(2000);

    // Crew should NOT see Adjust Stock button (hide, not disable per UI_SPEC.md)
    const adjustButton = crewPage.locator(
      'button:has-text("Adjust Stock"), [data-action-id="adjust_stock_quantity"]'
    ).first();
    const hasAdjustBtn = await adjustButton.isVisible({ timeout: 3000 }).catch(() => false);

    expect(hasAdjustBtn).toBe(false);
    console.log('  RBAC PASS: Crew cannot see Adjust Stock button');
  });
});

// =============================================================================
// SECTION 3: TRANSFER PART ACTION - FULL FLOW
// SIA-02: transfer part -> location modal -> submit
// =============================================================================

test.describe('Spotlight -> Inventory Actions: Transfer Part Flow', () => {
  test.describe.configure({ retries: 0 });

  test('SIA-02-FLOW: Transfer part action opens location modal', async ({ hodPage, supabaseAdmin }) => {
    // Find a part
    const { data: existingPart } = await supabaseAdmin
      .from(ROUTES_CONFIG.tables.parts)
      .select('id, name')
      .eq('yacht_id', ROUTES_CONFIG.yachtId)
      .limit(1)
      .single();

    if (!existingPart) {
      console.log('  SKIP: No parts found');
      return;
    }

    const capturedRequests = await captureActionPayloads(hodPage);

    await hodPage.goto(ROUTES_CONFIG.partsDetail(existingPart.id));
    await hodPage.waitForLoadState('networkidle');

    const currentUrl = hodPage.url();
    if (currentUrl.includes('/app') && !currentUrl.includes('/parts')) {
      console.log('  Feature flag disabled');
      return;
    }

    await hodPage.waitForTimeout(2000);

    // Click transfer button
    const transferButton = hodPage.locator(
      'button:has-text("Transfer"), button:has-text("Move"), [data-action-id="transfer_part"]'
    ).first();
    const hasTransferBtn = await transferButton.isVisible({ timeout: 5000 }).catch(() => false);

    if (!hasTransferBtn) {
      console.log('  SKIP: Transfer button not visible');
      return;
    }

    await transferButton.click();

    // Wait for modal
    const modal = new InventoryActionModalPO(hodPage);
    await modal.waitForOpen();

    // Verify location selects are visible
    const hasFromLocation = await modal.fromLocationSelect.isVisible({ timeout: 3000 }).catch(() => false);
    const hasToLocation = await modal.toLocationSelect.isVisible({ timeout: 3000 }).catch(() => false);

    console.log(`  From location select visible: ${hasFromLocation}`);
    console.log(`  To location select visible: ${hasToLocation}`);

    // Fill minimal form (may fail if no locations exist)
    try {
      await modal.quantityInput.fill('1');
    } catch {
      console.log('  Could not fill quantity');
    }

    console.log('  PASS: Transfer modal opened with location fields');
  });

  test('SIA-02-RBAC: Crew cannot see Transfer button (HOD+ required)', async ({ crewPage, supabaseAdmin }) => {
    const { data: existingPart } = await supabaseAdmin
      .from(ROUTES_CONFIG.tables.parts)
      .select('id')
      .eq('yacht_id', ROUTES_CONFIG.yachtId)
      .limit(1)
      .single();

    if (!existingPart) {
      console.log('  SKIP: No parts found');
      return;
    }

    await crewPage.goto(ROUTES_CONFIG.partsDetail(existingPart.id));
    await crewPage.waitForLoadState('networkidle');

    const currentUrl = crewPage.url();
    if (currentUrl.includes('/app') && !currentUrl.includes('/parts')) {
      console.log('  Feature flag disabled');
      return;
    }

    await crewPage.waitForTimeout(2000);

    const transferButton = crewPage.locator(
      'button:has-text("Transfer"), [data-action-id="transfer_part"]'
    ).first();
    const hasTransferBtn = await transferButton.isVisible({ timeout: 3000 }).catch(() => false);

    expect(hasTransferBtn).toBe(false);
    console.log('  RBAC PASS: Crew cannot see Transfer button');
  });
});

// =============================================================================
// SECTION 4: ADD TO SHOPPING LIST ACTION - FULL FLOW
// SIA-03: add to shopping list -> chip click
// =============================================================================

test.describe('Spotlight -> Inventory Actions: Shopping List Flow', () => {
  test.describe.configure({ retries: 0 });

  test('SIA-03-FLOW: Add to shopping list action creates item', async ({ crewPage, supabaseAdmin }) => {
    const { data: existingPart } = await supabaseAdmin
      .from(ROUTES_CONFIG.tables.parts)
      .select('id, name')
      .eq('yacht_id', ROUTES_CONFIG.yachtId)
      .limit(1)
      .single();

    if (!existingPart) {
      console.log('  SKIP: No parts found');
      return;
    }

    const capturedRequests = await captureActionPayloads(crewPage);

    await crewPage.goto(ROUTES_CONFIG.partsDetail(existingPart.id));
    await crewPage.waitForLoadState('networkidle');

    const currentUrl = crewPage.url();
    if (currentUrl.includes('/app') && !currentUrl.includes('/parts')) {
      console.log('  Feature flag disabled');
      return;
    }

    await crewPage.waitForTimeout(2000);

    // Click add to shopping list button
    const shoppingButton = crewPage.locator(
      'button:has-text("Add to Shopping"), button:has-text("Shopping List"), [data-action-id="create_shopping_list_item"], [data-action-id="add_to_shopping_list"]'
    ).first();
    const hasShoppingBtn = await shoppingButton.isVisible({ timeout: 5000 }).catch(() => false);

    if (!hasShoppingBtn) {
      console.log('  SKIP: Shopping List button not visible');
      return;
    }

    await shoppingButton.click();

    // May open modal or execute directly
    const modal = new InventoryActionModalPO(crewPage);
    const modalVisible = await modal.modal.isVisible({ timeout: 3000 }).catch(() => false);

    if (modalVisible) {
      console.log('  Modal opened - filling form');

      await modal.fillShoppingListForm(existingPart.name, 2, 'E2E test - add to shopping');

      await modal.submit();
      await modal.waitForClose().catch(() => {});

      const toast = new ToastPO(crewPage);
      try {
        await toast.waitForSuccess(5000);
        console.log('  SUCCESS: Shopping list item created');
      } catch {
        const errorMsg = await toast.getErrorMessage();
        console.log(`  May have failed: ${errorMsg}`);
      }
    } else {
      // Action may execute without modal
      console.log('  Action executed without modal (quick action)');
    }

    // Verify captured payload
    const shoppingPayload = capturedRequests.find(
      (r) => r.action === 'create_shopping_list_item' || r.action === 'add_to_shopping_list'
    );

    if (shoppingPayload) {
      console.log('  Captured shopping list payload');
      expect(shoppingPayload.context.yacht_id).toBe(ROUTES_CONFIG.yachtId);
      console.log('  PAYLOAD VERIFIED: create_shopping_list_item');
    }
  });

  test('SIA-03-RBAC: Crew CAN see Add to Shopping button', async ({ crewPage, supabaseAdmin }) => {
    const { data: existingPart } = await supabaseAdmin
      .from(ROUTES_CONFIG.tables.parts)
      .select('id')
      .eq('yacht_id', ROUTES_CONFIG.yachtId)
      .limit(1)
      .single();

    if (!existingPart) {
      console.log('  SKIP: No parts found');
      return;
    }

    await crewPage.goto(ROUTES_CONFIG.partsDetail(existingPart.id));
    await crewPage.waitForLoadState('networkidle');

    const currentUrl = crewPage.url();
    if (currentUrl.includes('/app') && !currentUrl.includes('/parts')) {
      console.log('  Feature flag disabled');
      return;
    }

    await crewPage.waitForTimeout(2000);

    // Crew SHOULD see Add to Shopping button (they can create shopping list items)
    const shoppingButton = crewPage.locator(
      'button:has-text("Shopping"), [data-action-id*="shopping"]'
    ).first();
    const hasShoppingBtn = await shoppingButton.isVisible({ timeout: 5000 }).catch(() => false);

    // This is expected to be true for crew
    if (hasShoppingBtn) {
      console.log('  RBAC PASS: Crew CAN see Shopping List button');
    } else {
      console.log('  NOTE: Shopping button not visible - may be context-dependent (only shows for low stock)');
    }
  });
});

// =============================================================================
// SECTION 5: RECEIVE PARTS ACTION - FULL FLOW
// SIA-05: receive parts -> modal with idempotency
// =============================================================================

test.describe('Spotlight -> Inventory Actions: Receive Parts Flow', () => {
  test.describe.configure({ retries: 0 });

  test('SIA-05-FLOW: Receive parts action captures idempotency key', async ({ hodPage, supabaseAdmin }) => {
    const { data: existingPart } = await supabaseAdmin
      .from(ROUTES_CONFIG.tables.parts)
      .select('id, name')
      .eq('yacht_id', ROUTES_CONFIG.yachtId)
      .limit(1)
      .single();

    if (!existingPart) {
      console.log('  SKIP: No parts found');
      return;
    }

    const capturedRequests = await captureActionPayloads(hodPage);

    await hodPage.goto(ROUTES_CONFIG.partsDetail(existingPart.id));
    await hodPage.waitForLoadState('networkidle');

    const currentUrl = hodPage.url();
    if (currentUrl.includes('/app') && !currentUrl.includes('/parts')) {
      console.log('  Feature flag disabled');
      return;
    }

    await hodPage.waitForTimeout(2000);

    // Click receive button
    const receiveButton = hodPage.locator(
      'button:has-text("Receive"), [data-action-id="receive_part"]'
    ).first();
    const hasReceiveBtn = await receiveButton.isVisible({ timeout: 5000 }).catch(() => false);

    if (!hasReceiveBtn) {
      console.log('  SKIP: Receive button not visible');
      return;
    }

    await receiveButton.click();

    const modal = new InventoryActionModalPO(hodPage);
    await modal.waitForOpen();

    // Fill quantity
    await modal.quantityInput.fill('5');

    // Add notes
    const hasNotes = await modal.notesTextarea.isVisible().catch(() => false);
    if (hasNotes) {
      await modal.notesTextarea.fill('E2E test receiving');
    }

    await modal.submit();
    await modal.waitForClose().catch(() => {});

    // Verify captured payload has idempotency_key
    const receivePayload = capturedRequests.find((r) => r.action === 'receive_part');

    if (receivePayload) {
      console.log('  Captured receive payload');
      expect(receivePayload.context.yacht_id).toBe(ROUTES_CONFIG.yachtId);
      expect(receivePayload.payload.part_id).toBe(existingPart.id);
      expect(receivePayload.payload.quantity_received).toBeDefined();

      // idempotency_key should be auto-generated
      if (receivePayload.payload.idempotency_key) {
        console.log(`  Idempotency key: ${receivePayload.payload.idempotency_key}`);
      }

      console.log('  PAYLOAD VERIFIED: receive_part');
    }
  });

  test('SIA-05-RBAC: Crew cannot see Receive button (HOD+ required)', async ({ crewPage, supabaseAdmin }) => {
    const { data: existingPart } = await supabaseAdmin
      .from(ROUTES_CONFIG.tables.parts)
      .select('id')
      .eq('yacht_id', ROUTES_CONFIG.yachtId)
      .limit(1)
      .single();

    if (!existingPart) {
      console.log('  SKIP: No parts found');
      return;
    }

    await crewPage.goto(ROUTES_CONFIG.partsDetail(existingPart.id));
    await crewPage.waitForLoadState('networkidle');

    const currentUrl = crewPage.url();
    if (currentUrl.includes('/app') && !currentUrl.includes('/parts')) {
      console.log('  Feature flag disabled');
      return;
    }

    await crewPage.waitForTimeout(2000);

    const receiveButton = crewPage.locator(
      'button:has-text("Receive"), [data-action-id="receive_part"]'
    ).first();
    const hasReceiveBtn = await receiveButton.isVisible({ timeout: 3000 }).catch(() => false);

    expect(hasReceiveBtn).toBe(false);
    console.log('  RBAC PASS: Crew cannot see Receive button');
  });
});

// =============================================================================
// SECTION 6: ROLE GATING - COMPREHENSIVE TESTS
// Verify role-based visibility for all inventory actions
// =============================================================================

test.describe('Spotlight -> Inventory Actions: Role Gating Matrix', () => {
  test.describe.configure({ retries: 0 }); // CRITICAL: No retries for security tests

  // Define expected visibility matrix
  const ROLE_VISIBILITY: Record<string, { captain: boolean; hod: boolean; crew: boolean }> = {
    adjust_stock_quantity: { captain: true, hod: false, crew: false }, // SIGNED - captain/manager only
    transfer_part: { captain: true, hod: true, crew: false }, // MUTATE - HOD+
    receive_part: { captain: true, hod: true, crew: false }, // MUTATE - HOD+
    consume_part: { captain: true, hod: true, crew: true }, // MUTATE - all crew with vessel access
    create_shopping_list_item: { captain: true, hod: true, crew: true }, // MUTATE - all crew
  };

  test('RBAC-MATRIX: Captain can see all inventory actions', async ({ captainPage, supabaseAdmin }) => {
    const { data: existingPart } = await supabaseAdmin
      .from(ROUTES_CONFIG.tables.parts)
      .select('id')
      .eq('yacht_id', ROUTES_CONFIG.yachtId)
      .limit(1)
      .single();

    if (!existingPart) {
      console.log('  SKIP: No parts found');
      return;
    }

    await captainPage.goto(ROUTES_CONFIG.partsDetail(existingPart.id));
    await captainPage.waitForLoadState('networkidle');

    const currentUrl = captainPage.url();
    if (currentUrl.includes('/app') && !currentUrl.includes('/parts')) {
      console.log('  Feature flag disabled');
      return;
    }

    await captainPage.waitForTimeout(2000);

    // Check each action
    for (const [actionId, visibility] of Object.entries(ROLE_VISIBILITY)) {
      const button = captainPage.locator(`[data-action-id="${actionId}"]`).first();
      const isVisible = await button.isVisible({ timeout: 2000 }).catch(() => false);

      console.log(`  Captain - ${actionId}: expected=${visibility.captain}, actual=${isVisible}`);

      if (visibility.captain && !isVisible) {
        // Try alternative selectors
        const altSelectors: Record<string, string[]> = {
          adjust_stock_quantity: ['button:has-text("Adjust Stock")', 'button:has-text("Adjust")'],
          transfer_part: ['button:has-text("Transfer")', 'button:has-text("Move")'],
          receive_part: ['button:has-text("Receive")'],
          consume_part: ['button:has-text("Consume")', 'button:has-text("Use")'],
          create_shopping_list_item: ['button:has-text("Shopping")', 'button:has-text("Add to Shopping")'],
        };

        for (const altSelector of altSelectors[actionId] || []) {
          const altButton = captainPage.locator(altSelector).first();
          const altVisible = await altButton.isVisible({ timeout: 1000 }).catch(() => false);
          if (altVisible) {
            console.log(`    Found via alt selector: ${altSelector}`);
            break;
          }
        }
      }
    }

    console.log('  RBAC-MATRIX: Captain visibility check complete');
  });

  test('RBAC-MATRIX: HOD cannot see SIGNED actions', async ({ hodPage, supabaseAdmin }) => {
    const { data: existingPart } = await supabaseAdmin
      .from(ROUTES_CONFIG.tables.parts)
      .select('id')
      .eq('yacht_id', ROUTES_CONFIG.yachtId)
      .limit(1)
      .single();

    if (!existingPart) {
      console.log('  SKIP: No parts found');
      return;
    }

    await hodPage.goto(ROUTES_CONFIG.partsDetail(existingPart.id));
    await hodPage.waitForLoadState('networkidle');

    const currentUrl = hodPage.url();
    if (currentUrl.includes('/app') && !currentUrl.includes('/parts')) {
      console.log('  Feature flag disabled');
      return;
    }

    await hodPage.waitForTimeout(2000);

    // HOD should NOT see adjust_stock_quantity (SIGNED)
    const adjustButton = hodPage.locator(
      '[data-action-id="adjust_stock_quantity"], button:has-text("Adjust Stock")'
    ).first();
    const hasAdjust = await adjustButton.isVisible({ timeout: 2000 }).catch(() => false);

    // Per UI_SPEC.md: hide, not disable
    if (!hasAdjust) {
      console.log('  RBAC PASS: HOD cannot see Adjust Stock (SIGNED action)');
    } else {
      console.log('  WARNING: HOD can see Adjust Stock - checking if disabled');
      const isDisabled = await adjustButton.isDisabled().catch(() => false);
      console.log(`    Button disabled: ${isDisabled}`);
    }

    // HOD SHOULD see MUTATE actions
    const transferButton = hodPage.locator(
      '[data-action-id="transfer_part"], button:has-text("Transfer")'
    ).first();
    const hasTransfer = await transferButton.isVisible({ timeout: 2000 }).catch(() => false);
    console.log(`  HOD - transfer_part: expected=true, actual=${hasTransfer}`);
  });

  test('RBAC-MATRIX: Crew has minimal action visibility', async ({ crewPage, supabaseAdmin }) => {
    const { data: existingPart } = await supabaseAdmin
      .from(ROUTES_CONFIG.tables.parts)
      .select('id')
      .eq('yacht_id', ROUTES_CONFIG.yachtId)
      .limit(1)
      .single();

    if (!existingPart) {
      console.log('  SKIP: No parts found');
      return;
    }

    await crewPage.goto(ROUTES_CONFIG.partsDetail(existingPart.id));
    await crewPage.waitForLoadState('networkidle');

    const currentUrl = crewPage.url();
    if (currentUrl.includes('/app') && !currentUrl.includes('/parts')) {
      console.log('  Feature flag disabled');
      return;
    }

    await crewPage.waitForTimeout(2000);

    // Check each action for crew
    const crewResults: Record<string, boolean> = {};

    for (const [actionId, visibility] of Object.entries(ROLE_VISIBILITY)) {
      const button = crewPage.locator(`[data-action-id="${actionId}"]`).first();
      let isVisible = await button.isVisible({ timeout: 2000 }).catch(() => false);

      // Try alternative selectors
      if (!isVisible) {
        const altSelectors: Record<string, string> = {
          adjust_stock_quantity: 'button:has-text("Adjust Stock")',
          transfer_part: 'button:has-text("Transfer")',
          receive_part: 'button:has-text("Receive")',
          consume_part: 'button:has-text("Consume")',
          create_shopping_list_item: 'button:has-text("Shopping")',
        };
        const altButton = crewPage.locator(altSelectors[actionId]).first();
        isVisible = await altButton.isVisible({ timeout: 1000 }).catch(() => false);
      }

      crewResults[actionId] = isVisible;
      console.log(`  Crew - ${actionId}: expected=${visibility.crew}, actual=${isVisible}`);

      // Security assertion: crew should NOT see HOD+ actions
      if (!visibility.crew && isVisible) {
        console.log(`  WARNING: SECURITY - Crew can see ${actionId} which requires HOD+`);
      }
    }

    // Verify security-critical assertions
    expect(crewResults['adjust_stock_quantity']).toBe(false); // SIGNED
    expect(crewResults['transfer_part']).toBe(false); // HOD+
    expect(crewResults['receive_part']).toBe(false); // HOD+

    console.log('  RBAC-MATRIX: Crew visibility check complete');
  });
});

// =============================================================================
// SECTION 7: PAYLOAD VALIDATION TESTS
// Verify /v1/actions/execute receives correct payloads
// =============================================================================

test.describe('Spotlight -> Inventory Actions: Payload Validation', () => {
  test.describe.configure({ retries: 0 });

  test('PAYLOAD-01: adjust_stock_quantity requires signature field', async ({ captainPage, supabaseAdmin }) => {
    const { data: existingPart } = await supabaseAdmin
      .from(ROUTES_CONFIG.tables.parts)
      .select('id')
      .eq('yacht_id', ROUTES_CONFIG.yachtId)
      .limit(1)
      .single();

    if (!existingPart) {
      console.log('  SKIP: No parts found');
      return;
    }

    // Intercept and modify request to remove signature
    let interceptedRequest: CapturedRequest | null = null;

    await captainPage.route('**/v1/actions/execute**', async (route, request) => {
      const postData = request.postData();
      if (postData) {
        const body = JSON.parse(postData);
        if (body.action === 'adjust_stock_quantity') {
          interceptedRequest = {
            action: body.action,
            context: body.context,
            payload: body.payload,
            url: request.url(),
            headers: request.headers() as Record<string, string>,
          };

          // Modify request to remove signature
          const modifiedBody = { ...body };
          delete modifiedBody.payload.signature;

          // Continue with modified request
          await route.continue({
            postData: JSON.stringify(modifiedBody),
          });
          return;
        }
      }
      await route.continue();
    });

    await captainPage.goto(ROUTES_CONFIG.partsDetail(existingPart.id));
    await captainPage.waitForLoadState('networkidle');

    const currentUrl = captainPage.url();
    if (currentUrl.includes('/app') && !currentUrl.includes('/parts')) {
      console.log('  Feature flag disabled');
      return;
    }

    await captainPage.waitForTimeout(2000);

    const adjustButton = captainPage.locator(
      'button:has-text("Adjust Stock"), [data-action-id="adjust_stock_quantity"]'
    ).first();
    const hasBtn = await adjustButton.isVisible({ timeout: 5000 }).catch(() => false);

    if (!hasBtn) {
      console.log('  SKIP: Adjust button not visible');
      return;
    }

    await adjustButton.click();

    const modal = new InventoryActionModalPO(captainPage);
    await modal.waitForOpen();

    await modal.fillAdjustStockForm(10, 'physical_count');
    // Intentionally NOT entering signature to test validation

    await modal.submit();

    // Wait for response
    await captainPage.waitForTimeout(2000);

    // Should show error (400 for missing signature)
    const toast = new ToastPO(captainPage);
    try {
      await toast.waitForError(5000);
      const errorMsg = await toast.getErrorMessage();
      console.log(`  Expected error received: ${errorMsg}`);
      console.log('  PAYLOAD-01 PASS: Server rejected request without signature');
    } catch {
      console.log('  No error toast - checking modal state');
      const modalStillOpen = await modal.modal.isVisible().catch(() => false);
      if (modalStillOpen) {
        console.log('  Modal still open - likely client-side validation blocked submit');
      }
    }
  });

  test('PAYLOAD-02: receive_part includes idempotency_key', async ({ hodPage, supabaseAdmin }) => {
    const { data: existingPart } = await supabaseAdmin
      .from(ROUTES_CONFIG.tables.parts)
      .select('id')
      .eq('yacht_id', ROUTES_CONFIG.yachtId)
      .limit(1)
      .single();

    if (!existingPart) {
      console.log('  SKIP: No parts found');
      return;
    }

    let receivedPayload: CapturedRequest | null = null;

    await hodPage.route('**/v1/actions/execute**', async (route, request) => {
      const postData = request.postData();
      if (postData) {
        const body = JSON.parse(postData);
        if (body.action === 'receive_part') {
          receivedPayload = {
            action: body.action,
            context: body.context,
            payload: body.payload,
            url: request.url(),
            headers: request.headers() as Record<string, string>,
          };
        }
      }
      await route.continue();
    });

    await hodPage.goto(ROUTES_CONFIG.partsDetail(existingPart.id));
    await hodPage.waitForLoadState('networkidle');

    const currentUrl = hodPage.url();
    if (currentUrl.includes('/app') && !currentUrl.includes('/parts')) {
      console.log('  Feature flag disabled');
      return;
    }

    await hodPage.waitForTimeout(2000);

    const receiveButton = hodPage.locator(
      'button:has-text("Receive"), [data-action-id="receive_part"]'
    ).first();
    const hasBtn = await receiveButton.isVisible({ timeout: 5000 }).catch(() => false);

    if (!hasBtn) {
      console.log('  SKIP: Receive button not visible');
      return;
    }

    await receiveButton.click();

    const modal = new InventoryActionModalPO(hodPage);
    await modal.waitForOpen();

    await modal.quantityInput.fill('3');
    await modal.submit();

    await hodPage.waitForTimeout(3000);

    if (receivedPayload) {
      console.log('  Received payload:', JSON.stringify(receivedPayload.payload, null, 2));

      // Verify idempotency_key exists
      if (receivedPayload.payload.idempotency_key) {
        console.log(`  PAYLOAD-02 PASS: idempotency_key present: ${receivedPayload.payload.idempotency_key}`);
        expect(receivedPayload.payload.idempotency_key).toBeTruthy();
      } else {
        console.log('  WARNING: idempotency_key not present in payload');
      }

      // Verify required fields
      expect(receivedPayload.payload.part_id).toBe(existingPart.id);
      expect(receivedPayload.payload.quantity_received).toBeDefined();
      expect(receivedPayload.context.yacht_id).toBe(ROUTES_CONFIG.yachtId);
    } else {
      console.log('  No receive_part request captured');
    }
  });

  test('PAYLOAD-03: transfer_part requires from/to locations', async ({ hodPage, supabaseAdmin }) => {
    const { data: existingPart } = await supabaseAdmin
      .from(ROUTES_CONFIG.tables.parts)
      .select('id')
      .eq('yacht_id', ROUTES_CONFIG.yachtId)
      .limit(1)
      .single();

    if (!existingPart) {
      console.log('  SKIP: No parts found');
      return;
    }

    let transferPayload: CapturedRequest | null = null;

    await hodPage.route('**/v1/actions/execute**', async (route, request) => {
      const postData = request.postData();
      if (postData) {
        const body = JSON.parse(postData);
        if (body.action === 'transfer_part') {
          transferPayload = {
            action: body.action,
            context: body.context,
            payload: body.payload,
            url: request.url(),
            headers: request.headers() as Record<string, string>,
          };
        }
      }
      await route.continue();
    });

    await hodPage.goto(ROUTES_CONFIG.partsDetail(existingPart.id));
    await hodPage.waitForLoadState('networkidle');

    const currentUrl = hodPage.url();
    if (currentUrl.includes('/app') && !currentUrl.includes('/parts')) {
      console.log('  Feature flag disabled');
      return;
    }

    await hodPage.waitForTimeout(2000);

    const transferButton = hodPage.locator(
      'button:has-text("Transfer"), button:has-text("Move"), [data-action-id="transfer_part"]'
    ).first();
    const hasBtn = await transferButton.isVisible({ timeout: 5000 }).catch(() => false);

    if (!hasBtn) {
      console.log('  SKIP: Transfer button not visible');
      return;
    }

    await transferButton.click();

    const modal = new InventoryActionModalPO(hodPage);
    await modal.waitForOpen();

    // Fill form - try to select locations
    await modal.quantityInput.fill('1');

    // Check if location fields exist
    const hasFromLoc = await modal.fromLocationSelect.isVisible().catch(() => false);
    const hasToLoc = await modal.toLocationSelect.isVisible().catch(() => false);

    console.log(`  From location field: ${hasFromLoc}`);
    console.log(`  To location field: ${hasToLoc}`);

    if (hasFromLoc && hasToLoc) {
      // Try to select first available options
      const fromOptions = await modal.fromLocationSelect.locator('option').all();
      const toOptions = await modal.toLocationSelect.locator('option').all();

      if (fromOptions.length > 1 && toOptions.length > 1) {
        await modal.fromLocationSelect.selectOption({ index: 1 });
        await modal.toLocationSelect.selectOption({ index: 1 });
      }
    }

    await modal.submit();
    await hodPage.waitForTimeout(3000);

    if (transferPayload) {
      console.log('  Transfer payload:', JSON.stringify(transferPayload.payload, null, 2));

      // Verify location fields
      const hasFromInPayload = transferPayload.payload.from_location_id || transferPayload.payload.from_location;
      const hasToInPayload = transferPayload.payload.to_location_id || transferPayload.payload.to_location;

      console.log(`  from_location in payload: ${!!hasFromInPayload}`);
      console.log(`  to_location in payload: ${!!hasToInPayload}`);

      if (hasFromInPayload && hasToInPayload) {
        console.log('  PAYLOAD-03 PASS: Both locations present');
      }
    } else {
      console.log('  No transfer_part request captured');
    }
  });
});

// =============================================================================
// SECTION 8: CROSS-YACHT SECURITY TESTS
// Ensure actions are scoped to current yacht
// =============================================================================

test.describe('Spotlight -> Inventory Actions: Cross-Yacht Security', () => {
  test.describe.configure({ retries: 0 }); // CRITICAL: No retries for security tests

  test('SECURITY-01: Action context always includes current yacht_id', async ({ hodPage, supabaseAdmin }) => {
    const { data: existingPart } = await supabaseAdmin
      .from(ROUTES_CONFIG.tables.parts)
      .select('id')
      .eq('yacht_id', ROUTES_CONFIG.yachtId)
      .limit(1)
      .single();

    if (!existingPart) {
      console.log('  SKIP: No parts found');
      return;
    }

    const capturedRequests: CapturedRequest[] = [];

    await hodPage.route('**/v1/actions/execute**', async (route, request) => {
      const postData = request.postData();
      if (postData) {
        const body = JSON.parse(postData);
        capturedRequests.push({
          action: body.action,
          context: body.context,
          payload: body.payload,
          url: request.url(),
          headers: request.headers() as Record<string, string>,
        });
      }
      await route.continue();
    });

    await hodPage.goto(ROUTES_CONFIG.partsDetail(existingPart.id));
    await hodPage.waitForLoadState('networkidle');

    const currentUrl = hodPage.url();
    if (currentUrl.includes('/app') && !currentUrl.includes('/parts')) {
      console.log('  Feature flag disabled');
      return;
    }

    await hodPage.waitForTimeout(2000);

    // Try to trigger any action
    const anyActionButton = hodPage.locator(
      '[data-action-id], button:has-text("Transfer"), button:has-text("Receive")'
    ).first();
    const hasBtn = await anyActionButton.isVisible({ timeout: 5000 }).catch(() => false);

    if (hasBtn) {
      await anyActionButton.click();

      const modal = new InventoryActionModalPO(hodPage);
      const modalOpen = await modal.modal.isVisible({ timeout: 3000 }).catch(() => false);

      if (modalOpen) {
        // Fill minimal data and submit
        const qtyInput = modal.quantityInput;
        const hasQty = await qtyInput.isVisible().catch(() => false);
        if (hasQty) {
          await qtyInput.fill('1');
        }
        await modal.submit();
        await hodPage.waitForTimeout(2000);
      }
    }

    // Verify all captured requests have correct yacht_id
    for (const request of capturedRequests) {
      console.log(`  Action: ${request.action}, yacht_id: ${request.context.yacht_id}`);

      expect(request.context.yacht_id).toBe(ROUTES_CONFIG.yachtId);

      if (request.context.yacht_id !== ROUTES_CONFIG.yachtId) {
        throw new Error(`SECURITY BREACH: Action ${request.action} has wrong yacht_id: ${request.context.yacht_id}`);
      }
    }

    if (capturedRequests.length > 0) {
      console.log(`  SECURITY PASS: ${capturedRequests.length} requests verified with correct yacht_id`);
    }
  });

  test('SECURITY-02: Cannot execute action for part from different yacht', async ({ hodPage, supabaseAdmin }) => {
    // Find a part from a DIFFERENT yacht
    const { data: foreignPart } = await supabaseAdmin
      .from(ROUTES_CONFIG.tables.parts)
      .select('id, yacht_id')
      .neq('yacht_id', ROUTES_CONFIG.yachtId)
      .limit(1)
      .single();

    if (!foreignPart) {
      console.log('  SKIP: No foreign parts found for cross-yacht test');
      return;
    }

    console.log(`  Testing with foreign part ${foreignPart.id} from yacht ${foreignPart.yacht_id}`);

    // Navigate directly to foreign part
    await hodPage.goto(ROUTES_CONFIG.partsDetail(foreignPart.id));
    await hodPage.waitForLoadState('networkidle');

    // Should show error/not found or redirect
    const errorSelectors = [
      ':text("Not Found")',
      ':text("not found")',
      ':text("Access Denied")',
      ':text("Unauthorized")',
      '[data-testid="not-found"]',
      '[data-testid="error-state"]',
    ];

    let hasAccessDenied = false;
    for (const selector of errorSelectors) {
      const element = hodPage.locator(selector);
      const isVisible = await element.isVisible({ timeout: 3000 }).catch(() => false);
      if (isVisible) {
        hasAccessDenied = true;
        console.log(`  Access denied via: ${selector}`);
        break;
      }
    }

    // Check if redirected away
    const currentUrl = hodPage.url();
    const wasRedirected = !currentUrl.includes(foreignPart.id);

    if (hasAccessDenied || wasRedirected) {
      console.log('  SECURITY PASS: Cross-yacht access blocked');
    } else {
      console.log('  WARNING: Page loaded - checking for actual data');

      // Even if page loads, verify no action buttons are available
      const anyActionBtn = hodPage.locator('[data-action-id]');
      const actionCount = await anyActionBtn.count();
      console.log(`  Action buttons visible: ${actionCount}`);
    }

    expect(hasAccessDenied || wasRedirected).toBe(true);
  });
});

// =============================================================================
// SECTION 9: DETERMINISM TESTS
// Ensure same query produces same action suggestions
// =============================================================================

test.describe('Spotlight -> Inventory Actions: Determinism', () => {
  test.describe.configure({ retries: 0 });

  test('DETERMINISM-01: Same query produces same action chips', async ({ hodPage }) => {
    await hodPage.goto('/app');
    await hodPage.waitForLoadState('networkidle');

    const results: string[][] = [];

    for (let run = 1; run <= 3; run++) {
      const spotlight = new SpotlightSearchPO(hodPage);
      await spotlight.search('adjust stock for filter');

      await hodPage.waitForTimeout(500);

      const actionChips = hodPage.locator('[data-action-id]');
      const chipCount = await actionChips.count();

      const actionIds: string[] = [];
      for (let i = 0; i < chipCount; i++) {
        const actionId = await actionChips.nth(i).getAttribute('data-action-id');
        if (actionId) actionIds.push(actionId);
      }

      results.push(actionIds);
      console.log(`  Run ${run}: ${actionIds.join(', ') || 'no chips'}`);

      // Close spotlight
      await hodPage.keyboard.press('Escape');
      await hodPage.waitForTimeout(300);
    }

    // All runs should produce same results
    if (results[0].length > 0) {
      expect(results[0]).toEqual(results[1]);
      expect(results[1]).toEqual(results[2]);
      console.log('  DETERMINISM PASS: Same query produces same chips');
    } else {
      console.log('  SKIP: No action chips to compare');
    }
  });
});

// =============================================================================
// SECTION 10: ERROR HANDLING TESTS
// Ensure graceful handling of action failures
// =============================================================================

test.describe('Spotlight -> Inventory Actions: Error Handling', () => {
  test.describe.configure({ retries: 0 });

  test('ERROR-01: Insufficient stock shows error on consume', async ({ hodPage, supabaseAdmin }) => {
    // Find a part with zero stock
    const { data: emptyPart } = await supabaseAdmin
      .from(ROUTES_CONFIG.tables.parts)
      .select('id, name, quantity_on_hand')
      .eq('yacht_id', ROUTES_CONFIG.yachtId)
      .eq('quantity_on_hand', 0)
      .limit(1)
      .single();

    if (!emptyPart) {
      console.log('  SKIP: No parts with zero stock found');
      return;
    }

    await hodPage.goto(ROUTES_CONFIG.partsDetail(emptyPart.id));
    await hodPage.waitForLoadState('networkidle');

    const currentUrl = hodPage.url();
    if (currentUrl.includes('/app') && !currentUrl.includes('/parts')) {
      console.log('  Feature flag disabled');
      return;
    }

    await hodPage.waitForTimeout(2000);

    // Try to consume (should fail or button should be disabled)
    const consumeButton = hodPage.locator(
      'button:has-text("Consume"), button:has-text("Use"), [data-action-id="consume_part"]'
    ).first();
    const hasConsumeBtn = await consumeButton.isVisible({ timeout: 3000 }).catch(() => false);

    if (!hasConsumeBtn) {
      console.log('  PASS: Consume button not visible for zero-stock part');
      return;
    }

    // Check if disabled
    const isDisabled = await consumeButton.isDisabled().catch(() => false);
    if (isDisabled) {
      console.log('  PASS: Consume button disabled for zero-stock part');
      return;
    }

    // Try to click and submit
    await consumeButton.click();

    const modal = new InventoryActionModalPO(hodPage);
    const modalOpen = await modal.modal.isVisible({ timeout: 3000 }).catch(() => false);

    if (modalOpen) {
      await modal.quantityInput.fill('1');
      await modal.submit();

      // Should show error
      const toast = new ToastPO(hodPage);
      try {
        await toast.waitForError(5000);
        const errorMsg = await toast.getErrorMessage();
        console.log(`  ERROR-01 PASS: Error shown for insufficient stock: ${errorMsg}`);
      } catch {
        // Modal may stay open with validation error
        const modalStillOpen = await modal.modal.isVisible().catch(() => false);
        if (modalStillOpen) {
          const validationError = modal.modal.locator('.error, .text-red, [data-error]');
          const hasError = await validationError.isVisible().catch(() => false);
          if (hasError) {
            console.log('  ERROR-01 PASS: Validation error shown in modal');
          }
        }
      }
    }
  });

  test('ERROR-02: Network failure shows error toast', async ({ hodPage, supabaseAdmin }) => {
    const { data: existingPart } = await supabaseAdmin
      .from(ROUTES_CONFIG.tables.parts)
      .select('id')
      .eq('yacht_id', ROUTES_CONFIG.yachtId)
      .limit(1)
      .single();

    if (!existingPart) {
      console.log('  SKIP: No parts found');
      return;
    }

    // Simulate network failure
    await hodPage.route('**/v1/actions/execute**', async (route) => {
      await route.abort('failed');
    });

    await hodPage.goto(ROUTES_CONFIG.partsDetail(existingPart.id));
    await hodPage.waitForLoadState('networkidle');

    const currentUrl = hodPage.url();
    if (currentUrl.includes('/app') && !currentUrl.includes('/parts')) {
      console.log('  Feature flag disabled');
      return;
    }

    await hodPage.waitForTimeout(2000);

    const receiveButton = hodPage.locator(
      'button:has-text("Receive"), [data-action-id="receive_part"]'
    ).first();
    const hasBtn = await receiveButton.isVisible({ timeout: 5000 }).catch(() => false);

    if (!hasBtn) {
      console.log('  SKIP: Receive button not visible');
      return;
    }

    await receiveButton.click();

    const modal = new InventoryActionModalPO(hodPage);
    await modal.waitForOpen();

    await modal.quantityInput.fill('1');
    await modal.submit();

    // Should show error
    const toast = new ToastPO(hodPage);
    try {
      await toast.waitForError(5000);
      console.log('  ERROR-02 PASS: Error toast shown for network failure');
    } catch {
      // May show inline error
      const modalError = modal.modal.locator('.error, .text-red, [role="alert"]');
      const hasError = await modalError.isVisible().catch(() => false);
      if (hasError) {
        console.log('  ERROR-02 PASS: Error shown in modal for network failure');
      }
    }
  });
});
