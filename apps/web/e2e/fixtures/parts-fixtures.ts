/**
 * Parts/Inventory Test Fixtures
 *
 * Creates deterministic test data for Parts/Inventory E2E and RBAC testing.
 * Ensures all required part states exist for action tests.
 *
 * LAW 26: MUTATIVE TRUTH - Full-stack lifecycle verification
 * LAW 27: RBAC PHYSICS - Backend rejects, not just UI hides
 * LAW 29: MUTATION ISOLATION - Fresh data per test, no state bleed
 *
 * Required Test Data:
 * 1. Part with stock > 0 (for consume_part, adjust_stock_quantity)
 * 2. Part with low stock (for check_stock_level, add_to_shopping_list)
 * 3. Shopping list item in 'candidate' status (for approve/reject)
 * 4. Shopping list item in 'pending' status (for approve/reject)
 *
 * Actions that need these fixtures:
 * - consume_part (needs part_id)
 * - adjust_stock_quantity (needs part_id)
 * - add_to_shopping_list (needs part_id)
 * - generate_part_labels (needs part_id)
 * - check_stock_level (needs part_id)
 * - log_part_usage (needs part_id)
 * - view_part_details (needs part_id)
 * - create_shopping_list_item (needs part context)
 * - approve_shopping_list_item (needs pending item)
 * - reject_shopping_list_item (needs pending item)
 * - promote_candidate_to_part (needs item_id)
 *
 * @see e2e/shard-12-action-coverage/action-coverage-comprehensive.spec.ts
 */

import { createClient, SupabaseClient } from '@supabase/supabase-js';

// Configuration
const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL || 'https://vzsohavtuotocgrfkfyd.supabase.co';
const SERVICE_KEY = process.env.SUPABASE_SERVICE_KEY || 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ6c29oYXZ0dW90b2NncmZrZnlkIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MzU5Mjg3NSwiZXhwIjoyMDc5MTY4ODc1fQ.fC7eC_4xGnCHIebPzfaJ18pFMPKgImE7BuN0I3A-pSY';
const TEST_YACHT_ID = process.env.TEST_YACHT_ID || '85fe1119-b04c-41ac-80f1-829d23322598';

// Test data prefix for easy identification and cleanup
const TEST_PREFIX = 'E2E_PARTS_TEST';

// ---------------------------------------------------------------------------
// Deterministic Test IDs
// ---------------------------------------------------------------------------

/**
 * Deterministic Part Test IDs
 * These UUIDs are fixed for E2E tests to allow deterministic assertions.
 * Using v4-like format but with recognizable patterns.
 */
export const PARTS_TEST_IDS = {
  // Part with good stock level - for consume_part, adjust_stock_quantity
  PART_WITH_STOCK: 'part0001-0001-4000-a000-000000000001',

  // Part with low stock - for check_stock_level, add_to_shopping_list
  PART_LOW_STOCK: 'part0002-0002-4000-a000-000000000002',

  // Part with zero stock - for edge cases
  PART_ZERO_STOCK: 'part0003-0003-4000-a000-000000000003',

  // Part with location info - for generate_part_labels, view_part_details
  PART_WITH_LOCATION: 'part0004-0004-4000-a000-000000000004',

  // Part linked to equipment - for log_part_usage with equipment context
  PART_WITH_EQUIPMENT: 'part0005-0005-4000-a000-000000000005',

  // Shopping list item in 'candidate' status - for promote_candidate_to_part
  SHOPPING_ITEM_CANDIDATE: 'shop0001-0001-4000-b000-000000000001',

  // Shopping list item in 'pending' status - for approve/reject
  SHOPPING_ITEM_PENDING: 'shop0002-0002-4000-b000-000000000002',

  // Shopping list item in 'approved' status - for ordered workflow
  SHOPPING_ITEM_APPROVED: 'shop0003-0003-4000-b000-000000000003',

  // Shopping list item in 'rejected' status - for read-only tests
  SHOPPING_ITEM_REJECTED: 'shop0004-0004-4000-b000-000000000004',
} as const;

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface PartSeedResult {
  success: boolean;
  parts: {
    id: string;
    name: string;
    partNumber: string;
    quantityOnHand: number;
    minimumQuantity: number;
    location?: string;
  }[];
  shoppingListItems: {
    id: string;
    partName: string;
    status: string;
    isCandidate: boolean;
  }[];
  errors: string[];
}

export interface SeedPartOptions {
  name?: string;
  partNumber?: string;
  quantityOnHand?: number;
  minimumQuantity?: number;
  location?: string;
  category?: string;
  manufacturer?: string;
}

export interface SeedShoppingListItemOptions {
  partId?: string;
  partName?: string;
  quantityRequested?: number;
  status?: string;
  priority?: string;
  isCandidate?: boolean;
  notes?: string;
}

// ---------------------------------------------------------------------------
// Helper: Create Supabase Client
// ---------------------------------------------------------------------------

function createSupabaseClient(supabase?: SupabaseClient): SupabaseClient {
  return supabase || createClient(SUPABASE_URL, SERVICE_KEY, {
    auth: {
      autoRefreshToken: false,
      persistSession: false,
    },
  });
}

// ---------------------------------------------------------------------------
// Fixture: seedPart - Creates a part with auto-cleanup
// ---------------------------------------------------------------------------

/**
 * Creates a test part with auto-cleanup tracking.
 *
 * @param options - Part creation options
 * @param supabase - Optional Supabase client
 * @returns Created part data with id for cleanup
 */
export async function seedPart(
  options: SeedPartOptions = {},
  supabase?: SupabaseClient
): Promise<{ id: string; name: string; partNumber: string; quantityOnHand: number }> {
  const client = createSupabaseClient(supabase);

  const timestamp = Date.now();
  const partNumber = options.partNumber || `${TEST_PREFIX}-${timestamp}`;
  const name = options.name || `${TEST_PREFIX}_Part_${timestamp}`;

  const { data, error } = await client
    .from('pms_parts')
    .insert({
      yacht_id: TEST_YACHT_ID,
      name,
      part_number: partNumber,
      description: `Test part for E2E testing - ${name}`,
      quantity_on_hand: options.quantityOnHand ?? 10,
      minimum_quantity: options.minimumQuantity ?? 2,
      location: options.location || 'Test Storage - Shelf A1',
      category: options.category || 'E2E Test Parts',
      manufacturer: options.manufacturer || 'Test Manufacturer',
      unit: 'ea',
      metadata: { test: true, created_by: 'e2e-fixtures' },
    })
    .select('id, name, part_number, quantity_on_hand')
    .single();

  if (error) {
    throw new Error(`Failed to seed part: ${error.message}`);
  }

  return {
    id: data.id,
    name: data.name,
    partNumber: data.part_number,
    quantityOnHand: data.quantity_on_hand,
  };
}

// ---------------------------------------------------------------------------
// Fixture: seedShoppingListItem - Creates shopping list item
// ---------------------------------------------------------------------------

/**
 * Creates a test shopping list item with auto-cleanup tracking.
 *
 * @param options - Shopping list item creation options
 * @param supabase - Optional Supabase client
 * @returns Created item data with id for cleanup
 */
export async function seedShoppingListItem(
  options: SeedShoppingListItemOptions = {},
  supabase?: SupabaseClient
): Promise<{ id: string; partName: string; status: string; isCandidate: boolean }> {
  const client = createSupabaseClient(supabase);

  const timestamp = Date.now();
  const partName = options.partName || `${TEST_PREFIX}_Item_${timestamp}`;

  // Get a valid user ID for requested_by
  const { data: userProfile, error: userError } = await client
    .from('auth_users_profiles')
    .select('id')
    .eq('yacht_id', TEST_YACHT_ID)
    .limit(1)
    .single();

  if (userError || !userProfile) {
    throw new Error(`Failed to get user profile: ${userError?.message || 'No user found'}`);
  }

  const requestedBy = (userProfile as { id: string }).id;

  const { data, error } = await client
    .from('pms_shopping_list_items')
    .insert({
      yacht_id: TEST_YACHT_ID,
      part_id: options.partId || null,
      part_name: partName,
      quantity_requested: options.quantityRequested ?? 5,
      status: options.status || 'candidate',
      priority: options.priority || 'normal',
      is_candidate_part: options.isCandidate ?? (options.partId ? false : true),
      source_type: 'manual',
      requested_by_id: requestedBy,
      notes: options.notes || `Test shopping list item for E2E testing`,
    })
    .select('id, part_name, status, is_candidate_part')
    .single();

  if (error) {
    throw new Error(`Failed to seed shopping list item: ${error.message}`);
  }

  return {
    id: data.id,
    partName: data.part_name,
    status: data.status,
    isCandidate: data.is_candidate_part,
  };
}

// ---------------------------------------------------------------------------
// Fixture: adjustStock - Helper to change stock quantity
// ---------------------------------------------------------------------------

/**
 * Adjusts stock quantity for a part.
 * Records the transaction in pms_inventory_transactions.
 *
 * @param partId - Part UUID to adjust
 * @param newQuantity - New stock quantity
 * @param reason - Reason for adjustment
 * @param supabase - Optional Supabase client
 * @returns Updated part data
 */
export async function adjustStock(
  partId: string,
  newQuantity: number,
  reason: string = 'E2E test adjustment',
  supabase?: SupabaseClient
): Promise<{ id: string; quantityOnHand: number; previousQuantity: number }> {
  const client = createSupabaseClient(supabase);

  // Get current quantity
  const { data: current, error: readError } = await client
    .from('pms_parts')
    .select('id, quantity_on_hand')
    .eq('id', partId)
    .single();

  if (readError || !current) {
    throw new Error(`Failed to read part: ${readError?.message || 'Part not found'}`);
  }

  const previousQuantity = current.quantity_on_hand;

  // Update quantity
  const { data: updated, error: updateError } = await client
    .from('pms_parts')
    .update({
      quantity_on_hand: newQuantity,
      last_counted_at: new Date().toISOString(),
    })
    .eq('id', partId)
    .select('id, quantity_on_hand')
    .single();

  if (updateError) {
    throw new Error(`Failed to adjust stock: ${updateError.message}`);
  }

  // Log the transaction
  const { error: txError } = await client
    .from('pms_inventory_transactions')
    .insert({
      yacht_id: TEST_YACHT_ID,
      part_id: partId,
      transaction_type: 'adjustment',
      quantity_change: newQuantity - previousQuantity,
      quantity_before: previousQuantity,
      quantity_after: newQuantity,
      reason,
      metadata: { test: true, source: 'e2e-fixtures' },
    });

  if (txError) {
    console.warn(`[PARTS-FIXTURE] Warning: Failed to log inventory transaction: ${txError.message}`);
  }

  return {
    id: updated.id,
    quantityOnHand: updated.quantity_on_hand,
    previousQuantity,
  };
}

// ---------------------------------------------------------------------------
// Fixture: getPartWithStock - Query part with current stock level
// ---------------------------------------------------------------------------

/**
 * Retrieves a part with its current stock level and location info.
 *
 * @param partId - Part UUID to query
 * @param supabase - Optional Supabase client
 * @returns Part data with stock info
 */
export async function getPartWithStock(
  partId: string,
  supabase?: SupabaseClient
): Promise<{
  id: string;
  name: string;
  partNumber: string;
  quantityOnHand: number;
  minimumQuantity: number;
  location: string | null;
  isLowStock: boolean;
}> {
  const client = createSupabaseClient(supabase);

  const { data, error } = await client
    .from('pms_parts')
    .select('id, name, part_number, quantity_on_hand, minimum_quantity, location')
    .eq('id', partId)
    .single();

  if (error || !data) {
    throw new Error(`Failed to get part: ${error?.message || 'Part not found'}`);
  }

  return {
    id: data.id,
    name: data.name,
    partNumber: data.part_number,
    quantityOnHand: data.quantity_on_hand,
    minimumQuantity: data.minimum_quantity,
    location: data.location,
    isLowStock: data.quantity_on_hand <= data.minimum_quantity,
  };
}

// ---------------------------------------------------------------------------
// Main Seeding Function - Creates all deterministic test data
// ---------------------------------------------------------------------------

/**
 * Main seeding function - creates deterministic parts test data
 *
 * @param supabase - Optional Supabase client (creates one if not provided)
 * @returns PartSeedResult with created data details
 */
export async function seedPartsTestData(supabase?: SupabaseClient): Promise<PartSeedResult> {
  const client = createSupabaseClient(supabase);

  const errors: string[] = [];
  const createdParts: PartSeedResult['parts'] = [];
  const createdItems: PartSeedResult['shoppingListItems'] = [];

  try {
    // ==========================================================================
    // STEP 1: Clean up old test data
    // ==========================================================================
    console.log('[PARTS-SEED] Cleaning up old test data...');

    // Delete shopping list items first (may have FK to parts)
    await client
      .from('pms_shopping_list_items')
      .delete()
      .like('part_name', `${TEST_PREFIX}%`);

    // Delete inventory transactions for test parts
    const partIds = Object.values(PARTS_TEST_IDS).filter(id => id.startsWith('part'));
    for (const id of partIds) {
      await client.from('pms_inventory_transactions').delete().eq('part_id', id);
    }

    // Delete parts by deterministic IDs
    for (const id of partIds) {
      await client.from('pms_parts').delete().eq('id', id);
    }

    // Also cleanup by name prefix
    await client
      .from('pms_parts')
      .delete()
      .like('name', `${TEST_PREFIX}%`);

    // ==========================================================================
    // STEP 2: Get required foreign key references
    // ==========================================================================
    console.log('[PARTS-SEED] Fetching required references...');

    // Get a valid user ID for created_by fields
    const { data: userProfile, error: userError } = await client
      .from('auth_users_profiles')
      .select('id')
      .eq('yacht_id', TEST_YACHT_ID)
      .limit(1)
      .single();

    if (userError || !userProfile) {
      errors.push(`Failed to get user profile: ${userError?.message || 'No user found'}`);
      return { success: false, parts: [], shoppingListItems: [], errors };
    }

    const requestedBy = (userProfile as { id: string }).id;

    // Get a valid equipment ID for equipment-linked part
    const { data: equipment } = await client
      .from('pms_equipment')
      .select('id')
      .eq('yacht_id', TEST_YACHT_ID)
      .limit(1)
      .single();

    const equipmentId = equipment?.id || null;

    // ==========================================================================
    // STEP 3: Seed Parts
    // ==========================================================================
    console.log('[PARTS-SEED] Seeding parts...');

    const partsToCreate = [
      // 1. Part with good stock - for consume_part, adjust_stock_quantity
      {
        id: PARTS_TEST_IDS.PART_WITH_STOCK,
        yacht_id: TEST_YACHT_ID,
        name: `${TEST_PREFIX}_Oil_Filter`,
        part_number: 'E2E-OF-001',
        description: 'Test part with good stock level for consumption tests',
        quantity_on_hand: 25,
        minimum_quantity: 5,
        location: 'Engine Room Stores - Shelf A1',
        category: 'Filters',
        manufacturer: 'Test Manufacturer',
        unit: 'ea',
        metadata: { test: true, variant: 'with_stock' },
      },

      // 2. Part with low stock - for check_stock_level, add_to_shopping_list
      {
        id: PARTS_TEST_IDS.PART_LOW_STOCK,
        yacht_id: TEST_YACHT_ID,
        name: `${TEST_PREFIX}_Fuel_Filter`,
        part_number: 'E2E-FF-001',
        description: 'Test part with LOW stock for reorder tests',
        quantity_on_hand: 2,
        minimum_quantity: 5,
        location: 'Engine Room Stores - Shelf A2',
        category: 'Filters',
        manufacturer: 'Test Manufacturer',
        unit: 'ea',
        metadata: { test: true, variant: 'low_stock' },
      },

      // 3. Part with zero stock - for edge cases
      {
        id: PARTS_TEST_IDS.PART_ZERO_STOCK,
        yacht_id: TEST_YACHT_ID,
        name: `${TEST_PREFIX}_Air_Filter`,
        part_number: 'E2E-AF-001',
        description: 'Test part with ZERO stock for edge case tests',
        quantity_on_hand: 0,
        minimum_quantity: 3,
        location: 'Engine Room Stores - Shelf A3',
        category: 'Filters',
        manufacturer: 'Test Manufacturer',
        unit: 'ea',
        metadata: { test: true, variant: 'zero_stock' },
      },

      // 4. Part with detailed location - for generate_part_labels, view_part_details
      {
        id: PARTS_TEST_IDS.PART_WITH_LOCATION,
        yacht_id: TEST_YACHT_ID,
        name: `${TEST_PREFIX}_Gasket_Set`,
        part_number: 'E2E-GS-001',
        description: 'Test part with detailed location info for label generation',
        quantity_on_hand: 8,
        minimum_quantity: 2,
        location: 'Forward Stores - Bin C-12-A (Temperature Controlled)',
        category: 'Gaskets & Seals',
        manufacturer: 'Marine Seals Inc',
        unit: 'set',
        metadata: {
          test: true,
          variant: 'with_location',
          storage_temp: '15-25C',
          barcode: 'E2E-GS-001-BC',
        },
      },

      // 5. Part linked to equipment - for log_part_usage with context
      {
        id: PARTS_TEST_IDS.PART_WITH_EQUIPMENT,
        yacht_id: TEST_YACHT_ID,
        name: `${TEST_PREFIX}_Impeller`,
        part_number: 'E2E-IMP-001',
        description: 'Test part linked to equipment for usage logging tests',
        quantity_on_hand: 4,
        minimum_quantity: 2,
        location: 'Engine Room Stores - Shelf B1',
        category: 'Pumps & Impellers',
        manufacturer: 'Jabsco',
        unit: 'ea',
        metadata: {
          test: true,
          variant: 'with_equipment',
          compatible_equipment_id: equipmentId,
        },
      },
    ];

    for (const part of partsToCreate) {
      const { data, error } = await client
        .from('pms_parts')
        .upsert(part, { onConflict: 'id' })
        .select('id, name, part_number, quantity_on_hand, minimum_quantity, location')
        .single();

      if (error) {
        errors.push(`Failed to create part ${part.name}: ${error.message}`);
      } else if (data) {
        createdParts.push({
          id: data.id,
          name: data.name,
          partNumber: data.part_number,
          quantityOnHand: data.quantity_on_hand,
          minimumQuantity: data.minimum_quantity,
          location: data.location,
        });
        console.log(`[PARTS-SEED] Created part: ${data.name} (qty: ${data.quantity_on_hand})`);
      }
    }

    // ==========================================================================
    // STEP 4: Seed Shopping List Items
    // ==========================================================================
    console.log('[PARTS-SEED] Seeding shopping list items...');

    // Shopping list status values: candidate, pending, approved, ordered, received, rejected
    const shoppingItemsToCreate = [
      // 1. Candidate item - for promote_candidate_to_part
      {
        id: PARTS_TEST_IDS.SHOPPING_ITEM_CANDIDATE,
        yacht_id: TEST_YACHT_ID,
        part_id: null, // Candidate = not linked to existing part
        part_name: `${TEST_PREFIX}_New_Hose_Assembly`,
        part_number: 'E2E-HA-NEW',
        quantity_requested: 2,
        status: 'candidate',
        priority: 'normal',
        is_candidate_part: true,
        source_type: 'manual',
        requested_by_id: requestedBy,
        notes: 'Test candidate item for promote_to_part action',
      },

      // 2. Pending item - for approve/reject actions
      {
        id: PARTS_TEST_IDS.SHOPPING_ITEM_PENDING,
        yacht_id: TEST_YACHT_ID,
        part_id: PARTS_TEST_IDS.PART_LOW_STOCK, // Linked to existing part
        part_name: `${TEST_PREFIX}_Fuel_Filter_Reorder`,
        quantity_requested: 10,
        status: 'pending',
        priority: 'high',
        is_candidate_part: false,
        source_type: 'low_stock_alert',
        requested_by_id: requestedBy,
        notes: 'Test pending item for approval workflow tests',
      },

      // 3. Approved item - for ordered workflow
      {
        id: PARTS_TEST_IDS.SHOPPING_ITEM_APPROVED,
        yacht_id: TEST_YACHT_ID,
        part_id: PARTS_TEST_IDS.PART_WITH_STOCK,
        part_name: `${TEST_PREFIX}_Oil_Filter_Order`,
        quantity_requested: 5,
        quantity_approved: 5,
        status: 'approved',
        priority: 'normal',
        is_candidate_part: false,
        source_type: 'restock',
        requested_by_id: requestedBy,
        approved_by_id: requestedBy,
        notes: 'Test approved item - ready for ordering',
      },

      // 4. Rejected item - for read-only tests
      {
        id: PARTS_TEST_IDS.SHOPPING_ITEM_REJECTED,
        yacht_id: TEST_YACHT_ID,
        part_id: null,
        part_name: `${TEST_PREFIX}_Rejected_Request`,
        quantity_requested: 100,
        status: 'rejected',
        priority: 'low',
        is_candidate_part: true,
        source_type: 'manual',
        requested_by_id: requestedBy,
        notes: 'Test rejected item - should be read-only',
      },
    ];

    for (const item of shoppingItemsToCreate) {
      const { data, error } = await client
        .from('pms_shopping_list_items')
        .upsert(item, { onConflict: 'id' })
        .select('id, part_name, status, is_candidate_part')
        .single();

      if (error) {
        errors.push(`Failed to create shopping list item ${item.part_name}: ${error.message}`);
      } else if (data) {
        createdItems.push({
          id: data.id,
          partName: data.part_name,
          status: data.status,
          isCandidate: data.is_candidate_part,
        });
        console.log(`[PARTS-SEED] Created shopping item: ${data.part_name} (${data.status})`);
      }
    }

    // ==========================================================================
    // RESULT
    // ==========================================================================
    const success = errors.length === 0;

    console.log('[PARTS-SEED] Seeding complete:', {
      success,
      partsCreated: createdParts.length,
      shoppingItemsCreated: createdItems.length,
      errors: errors.length > 0 ? errors : 'none',
    });

    return { success, parts: createdParts, shoppingListItems: createdItems, errors };
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    errors.push(`Unexpected error: ${message}`);
    return { success: false, parts: createdParts, shoppingListItems: createdItems, errors };
  }
}

// ---------------------------------------------------------------------------
// Cleanup Function
// ---------------------------------------------------------------------------

/**
 * Cleanup function - removes all test parts data
 */
export async function cleanupPartsTestData(supabase?: SupabaseClient): Promise<void> {
  const client = createSupabaseClient(supabase);

  console.log('[PARTS-SEED] Cleaning up test data...');

  // Delete shopping list items first
  await client.from('pms_shopping_list_items').delete().like('part_name', `${TEST_PREFIX}%`);

  // Delete inventory transactions
  const partIds = Object.values(PARTS_TEST_IDS).filter(id => id.startsWith('part'));
  for (const id of partIds) {
    await client.from('pms_inventory_transactions').delete().eq('part_id', id);
  }

  // Delete parts by deterministic IDs
  for (const id of partIds) {
    await client.from('pms_parts').delete().eq('id', id);
  }

  // Also cleanup by name prefix
  await client.from('pms_parts').delete().like('name', `${TEST_PREFIX}%`);

  console.log('[PARTS-SEED] Cleanup complete');
}

// ---------------------------------------------------------------------------
// Verification Function
// ---------------------------------------------------------------------------

/**
 * Verify parts test data exists and meets requirements
 */
export async function verifyPartsTestData(supabase?: SupabaseClient): Promise<{
  valid: boolean;
  status: {
    partWithStock: boolean;
    partLowStock: boolean;
    partZeroStock: boolean;
    partWithLocation: boolean;
    partWithEquipment: boolean;
    shoppingItemCandidate: boolean;
    shoppingItemPending: boolean;
    shoppingItemApproved: boolean;
    shoppingItemRejected: boolean;
  };
  ids: typeof PARTS_TEST_IDS;
}> {
  const client = createSupabaseClient(supabase);

  // Check each required data point exists
  const [
    { data: partWithStock },
    { data: partLowStock },
    { data: partZeroStock },
    { data: partWithLocation },
    { data: partWithEquipment },
    { data: shoppingCandidate },
    { data: shoppingPending },
    { data: shoppingApproved },
    { data: shoppingRejected },
  ] = await Promise.all([
    client.from('pms_parts').select('id, quantity_on_hand').eq('id', PARTS_TEST_IDS.PART_WITH_STOCK).single(),
    client.from('pms_parts').select('id, quantity_on_hand, minimum_quantity').eq('id', PARTS_TEST_IDS.PART_LOW_STOCK).single(),
    client.from('pms_parts').select('id, quantity_on_hand').eq('id', PARTS_TEST_IDS.PART_ZERO_STOCK).single(),
    client.from('pms_parts').select('id, location').eq('id', PARTS_TEST_IDS.PART_WITH_LOCATION).single(),
    client.from('pms_parts').select('id').eq('id', PARTS_TEST_IDS.PART_WITH_EQUIPMENT).single(),
    client.from('pms_shopping_list_items').select('id, status, is_candidate_part').eq('id', PARTS_TEST_IDS.SHOPPING_ITEM_CANDIDATE).single(),
    client.from('pms_shopping_list_items').select('id, status').eq('id', PARTS_TEST_IDS.SHOPPING_ITEM_PENDING).single(),
    client.from('pms_shopping_list_items').select('id, status').eq('id', PARTS_TEST_IDS.SHOPPING_ITEM_APPROVED).single(),
    client.from('pms_shopping_list_items').select('id, status').eq('id', PARTS_TEST_IDS.SHOPPING_ITEM_REJECTED).single(),
  ]);

  const status = {
    partWithStock: partWithStock?.quantity_on_hand > 0,
    partLowStock: partLowStock ? partLowStock.quantity_on_hand <= partLowStock.minimum_quantity : false,
    partZeroStock: partZeroStock?.quantity_on_hand === 0,
    partWithLocation: !!partWithLocation?.location,
    partWithEquipment: !!partWithEquipment,
    shoppingItemCandidate: shoppingCandidate?.status === 'candidate' && shoppingCandidate?.is_candidate_part === true,
    shoppingItemPending: shoppingPending?.status === 'pending',
    shoppingItemApproved: shoppingApproved?.status === 'approved',
    shoppingItemRejected: shoppingRejected?.status === 'rejected',
  };

  const valid = Object.values(status).every(v => v === true);

  return { valid, status, ids: PARTS_TEST_IDS };
}

// ---------------------------------------------------------------------------
// Getter Functions
// ---------------------------------------------------------------------------

/**
 * Get part by test ID key
 */
export function getPartTestId(key: keyof typeof PARTS_TEST_IDS): string {
  return PARTS_TEST_IDS[key];
}

// ---------------------------------------------------------------------------
// CLI Support
// ---------------------------------------------------------------------------

async function runCli(): Promise<void> {
  const command = process.argv[2];

  switch (command) {
    case 'seed':
      await seedPartsTestData();
      break;
    case 'cleanup':
      await cleanupPartsTestData();
      break;
    case 'verify': {
      const result = await verifyPartsTestData();
      console.log('[PARTS-SEED] Verification result:', JSON.stringify(result, null, 2));
      process.exit(result.valid ? 0 : 1);
    }
    default:
      console.log('Parts/Inventory Test Fixtures');
      console.log('');
      console.log('Usage: npx ts-node e2e/fixtures/parts-fixtures.ts [seed|cleanup|verify]');
      console.log('');
      console.log('Commands:');
      console.log('  seed    - Create parts test data for E2E tests');
      console.log('  cleanup - Remove all parts test data');
      console.log('  verify  - Check test data exists and meets requirements');
      console.log('');
      console.log('Known-Good Part IDs for E2E Tests:');
      console.log('  PART_WITH_STOCK (consume, adjust):    ', PARTS_TEST_IDS.PART_WITH_STOCK);
      console.log('  PART_LOW_STOCK (check, add_to_list):  ', PARTS_TEST_IDS.PART_LOW_STOCK);
      console.log('  PART_ZERO_STOCK (edge cases):         ', PARTS_TEST_IDS.PART_ZERO_STOCK);
      console.log('  PART_WITH_LOCATION (labels, details): ', PARTS_TEST_IDS.PART_WITH_LOCATION);
      console.log('  PART_WITH_EQUIPMENT (log_usage):      ', PARTS_TEST_IDS.PART_WITH_EQUIPMENT);
      console.log('');
      console.log('Shopping List Item IDs:');
      console.log('  SHOPPING_ITEM_CANDIDATE (promote):    ', PARTS_TEST_IDS.SHOPPING_ITEM_CANDIDATE);
      console.log('  SHOPPING_ITEM_PENDING (approve/reject):', PARTS_TEST_IDS.SHOPPING_ITEM_PENDING);
      console.log('  SHOPPING_ITEM_APPROVED (ordered):     ', PARTS_TEST_IDS.SHOPPING_ITEM_APPROVED);
      console.log('  SHOPPING_ITEM_REJECTED (read-only):   ', PARTS_TEST_IDS.SHOPPING_ITEM_REJECTED);
      process.exit(0);
  }
}

// Run CLI if executed directly (ESM compatible)
runCli().catch((err) => {
  console.error('[PARTS-SEED] Error:', err);
  process.exit(1);
});
