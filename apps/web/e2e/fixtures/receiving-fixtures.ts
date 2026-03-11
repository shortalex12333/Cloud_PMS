/**
 * Receiving Test Data Fixtures
 *
 * Creates deterministic test data for Receiving domain E2E testing.
 * Provides seed functions for receiving records, line items, and state transitions.
 *
 * Required Test Data States:
 * 1. Receiving in 'draft' status (for start_receiving_event)
 * 2. Receiving in 'in_progress' status (for add_line_item, complete_receiving)
 * 3. Receiving in 'completed' status (for accept_receiving, report_discrepancy)
 * 4. Receiving with line items (for adjust_receiving_item)
 * 5. Receiving with documents (for link_invoice_document)
 *
 * Actions Covered:
 * - create_receiving (creates data)
 * - start_receiving_event (needs receiving_id, draft status)
 * - add_line_item (needs receiving_id)
 * - complete_receiving_event (needs started receiving)
 * - accept_receiving (needs receiving_id, signed action)
 * - report_discrepancy (needs receiving_id)
 * - link_invoice_document (needs receiving_id + document_id)
 * - extract_receiving_candidates (needs receiving_id)
 * - attach_receiving_image_with_comment (needs receiving_id + file)
 * - update_receiving_fields (needs receiving_id)
 * - adjust_receiving_item (needs line item_id)
 *
 * @see e2e/shard-31-fragmented-routes/spotlight-receiving-action.spec.ts
 * @see src/hooks/useReceivingActions.ts
 */

import { createClient } from '@supabase/supabase-js';
type SupabaseClient = ReturnType<typeof createClient>;

// Configuration
const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL || 'https://vzsohavtuotocgrfkfyd.supabase.co';
const SERVICE_KEY = process.env.SUPABASE_SERVICE_KEY || 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ6c29oYXZ0dW90b2NncmZrZnlkIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MzU5Mjg3NSwiZXhwIjoyMDc5MTY4ODc1fQ.fC7eC_4xGnCHIebPzfaJ18pFMPKgImE7BuN0I3A-pSY';
const TEST_YACHT_ID = process.env.TEST_YACHT_ID || '85fe1119-b04c-41ac-80f1-829d23322598';

// Test data prefix for easy identification and cleanup
const TEST_PREFIX = 'E2E_RECEIVING_TEST';

// =============================================================================
// DETERMINISTIC TEST IDS
// =============================================================================

/**
 * Deterministic Receiving Test IDs
 * These UUIDs are fixed for E2E tests to allow deterministic assertions.
 */
export const RECEIVING_TEST_IDS = {
  // Receiving in 'draft' status - for start_receiving_event tests
  RECEIVING_DRAFT: 'recv0001-0001-4000-a000-000000000001',

  // Receiving in 'in_progress' status - for add_line_item, complete tests
  RECEIVING_IN_PROGRESS: 'recv0002-0002-4000-a000-000000000002',

  // Receiving in 'completed' status - for accept/reject tests
  RECEIVING_COMPLETED: 'recv0003-0003-4000-a000-000000000003',

  // Receiving in 'accepted' status - for readonly verification
  RECEIVING_ACCEPTED: 'recv0004-0004-4000-a000-000000000004',

  // Receiving with line items attached - for adjust_receiving_item
  RECEIVING_WITH_ITEMS: 'recv0005-0005-4000-a000-000000000005',

  // Receiving with documents - for link_invoice_document
  RECEIVING_WITH_DOCS: 'recv0006-0006-4000-a000-000000000006',

  // Line item IDs for specific receiving records
  LINE_ITEM_1: 'recv0101-0001-4000-b000-000000000001',
  LINE_ITEM_2: 'recv0101-0002-4000-b000-000000000002',
  LINE_ITEM_3: 'recv0101-0003-4000-b000-000000000003',

  // Document IDs for receiving documents
  DOCUMENT_1: 'recv0201-0001-4000-c000-000000000001',
} as const;

// =============================================================================
// TYPE DEFINITIONS
// =============================================================================

/**
 * Receiving status values from database schema
 * Based on migration: 20260225_005_receiving_ledger_triggers.sql
 */
export type ReceivingStatus = 'draft' | 'in_progress' | 'in_review' | 'completed' | 'accepted' | 'rejected';

/**
 * Line item condition values
 */
export type LineItemCondition = 'new' | 'refurbished' | 'damaged' | 'defective';

/**
 * Receiving seed result with created data
 */
export interface ReceivingSeedResult {
  success: boolean;
  receivings: {
    id: string;
    vendor_name: string;
    status: ReceivingStatus;
    total: number;
    currency: string;
    received_date: string;
    itemCount: number;
  }[];
  lineItems: {
    id: string;
    receiving_id: string;
    description: string;
    quantity_expected: number;
    quantity_received: number;
    unit_price: number;
    currency: string;
  }[];
  documents: {
    id: string;
    receiving_id: string;
    doc_type: string;
  }[];
  errors: string[];
}

/**
 * Parameters for seeding a single receiving record
 */
export interface SeedReceivingParams {
  id?: string;
  vendor_name?: string;
  vendor_reference?: string;
  status?: ReceivingStatus;
  currency?: string;
  total?: number;
  subtotal?: number;
  tax_total?: number;
  received_date?: string;
  notes?: string;
}

/**
 * Parameters for seeding a receiving line item
 */
export interface SeedLineItemParams {
  id?: string;
  receiving_id: string;
  part_id?: string;
  description?: string;
  quantity_expected?: number;
  quantity_received?: number;
  unit_price?: number;
  currency?: string;
  condition?: LineItemCondition;
  serial_number?: string;
  batch_number?: string;
  notes?: string;
}

// =============================================================================
// INTERNAL HELPERS
// =============================================================================

/**
 * Create a Supabase client with service role
 */
function getClient(supabase?: SupabaseClient): SupabaseClient {
  return supabase || createClient(SUPABASE_URL, SERVICE_KEY, {
    auth: {
      autoRefreshToken: false,
      persistSession: false,
    },
  });
}

/**
 * Get a valid user ID from the yacht
 */
async function getValidUserId(client: SupabaseClient): Promise<string | null> {
  const { data: userProfile, error } = await client
    .from('auth_users_profiles')
    .select('id')
    .eq('yacht_id', TEST_YACHT_ID)
    .limit(1)
    .single();

  if (error || !userProfile) {
    return null;
  }

  return (userProfile as { id: string }).id;
}

// =============================================================================
// SEED FUNCTIONS - Playwright Fixture Pattern
// =============================================================================

/**
 * Creates a receiving record with auto-cleanup
 *
 * Returns a function that creates receiving records and tracks them for cleanup.
 * Used as a Playwright fixture.
 *
 * @example
 * ```ts
 * test('can start receiving', async ({ seedReceiving }) => {
 *   const receiving = await seedReceiving({ status: 'draft', vendor_name: 'Test Vendor' });
 *   // Test start_receiving_event action with receiving.id
 * });
 * ```
 */
export async function createSeedReceivingFixture(supabase?: SupabaseClient): Promise<{
  seed: (params?: SeedReceivingParams) => Promise<{
    id: string;
    vendor_name: string;
    status: ReceivingStatus;
    total: number;
    currency: string;
    received_date: string;
  }>;
  cleanup: () => Promise<void>;
}> {
  const client = getClient(supabase);
  const createdIds: string[] = [];

  const seed = async (params?: SeedReceivingParams) => {
    const userId = await getValidUserId(client);
    if (!userId) {
      throw new Error('No valid user found for test yacht');
    }

    const id = params?.id || `recv-${Date.now()}-${Math.random().toString(36).substring(2, 8)}`;
    const vendorName = params?.vendor_name || `${TEST_PREFIX}_VENDOR_${Date.now()}`;
    const status = params?.status || 'draft';
    const total = params?.total ?? 0;
    const subtotal = params?.subtotal ?? 0;
    const taxTotal = params?.tax_total ?? 0;
    const currency = params?.currency || 'USD';
    const receivedDate = params?.received_date || new Date().toISOString();

    const { data, error } = await client
      .from('pms_receiving')
      .upsert({
        id,
        yacht_id: TEST_YACHT_ID,
        vendor_name: vendorName,
        vendor_reference: params?.vendor_reference || `REF-${Date.now()}`,
        status,
        total,
        subtotal,
        tax_total: taxTotal,
        currency,
        received_date: receivedDate,
        received_by: userId,
        created_by: userId,
        notes: params?.notes || `${TEST_PREFIX} auto-generated receiving record`,
      }, { onConflict: 'id' })
      .select('id, vendor_name, status, total, currency, received_date')
      .single();

    if (error) {
      throw new Error(`Failed to seed receiving: ${error.message}`);
    }

    createdIds.push(data.id);

    return {
      id: data.id,
      vendor_name: data.vendor_name,
      status: data.status as ReceivingStatus,
      total: data.total,
      currency: data.currency,
      received_date: data.received_date,
    };
  };

  const cleanup = async () => {
    if (createdIds.length === 0) return;

    // Delete line items first (FK constraint)
    await client
      .from('pms_receiving_items')
      .delete()
      .in('receiving_id', createdIds);

    // Delete documents (FK constraint)
    await client
      .from('pms_receiving_documents')
      .delete()
      .in('receiving_id', createdIds);

    // Delete receiving records
    await client
      .from('pms_receiving')
      .delete()
      .in('id', createdIds);
  };

  return { seed, cleanup };
}

/**
 * Creates a line item on a receiving record with auto-cleanup
 *
 * Returns a function that creates line items and tracks them for cleanup.
 * Used as a Playwright fixture.
 *
 * @example
 * ```ts
 * test('can adjust line item', async ({ seedReceiving, seedReceivingLineItem }) => {
 *   const receiving = await seedReceiving({ status: 'in_progress' });
 *   const lineItem = await seedReceivingLineItem({
 *     receiving_id: receiving.id,
 *     quantity_expected: 10,
 *     quantity_received: 8,
 *   });
 *   // Test adjust_receiving_item action with lineItem.id
 * });
 * ```
 */
export async function createSeedLineItemFixture(supabase?: SupabaseClient): Promise<{
  seed: (params: SeedLineItemParams) => Promise<{
    id: string;
    receiving_id: string;
    description: string;
    quantity_expected: number;
    quantity_received: number;
    unit_price: number;
    currency: string;
  }>;
  cleanup: () => Promise<void>;
}> {
  const client = getClient(supabase);
  const createdIds: string[] = [];

  const seed = async (params: SeedLineItemParams) => {
    const id = params.id || `item-${Date.now()}-${Math.random().toString(36).substring(2, 8)}`;
    const description = params.description || `${TEST_PREFIX}_ITEM_${Date.now()}`;
    const quantityExpected = params.quantity_expected ?? 1;
    const quantityReceived = params.quantity_received ?? 1;
    const unitPrice = params.unit_price ?? 10.00;
    const currency = params.currency || 'USD';

    const { data, error } = await client
      .from('pms_receiving_items')
      .upsert({
        id,
        yacht_id: TEST_YACHT_ID,
        receiving_id: params.receiving_id,
        part_id: params.part_id,
        description,
        quantity_expected: quantityExpected,
        quantity_received: quantityReceived,
        unit_price: unitPrice,
        currency,
        condition: params.condition || 'new',
        serial_number: params.serial_number,
        batch_number: params.batch_number,
        notes: params.notes || `${TEST_PREFIX} auto-generated line item`,
      }, { onConflict: 'id' })
      .select('id, receiving_id, description, quantity_expected, quantity_received, unit_price, currency')
      .single();

    if (error) {
      throw new Error(`Failed to seed line item: ${error.message}`);
    }

    createdIds.push(data.id);

    return {
      id: data.id,
      receiving_id: data.receiving_id,
      description: data.description,
      quantity_expected: data.quantity_expected,
      quantity_received: data.quantity_received,
      unit_price: data.unit_price,
      currency: data.currency,
    };
  };

  const cleanup = async () => {
    if (createdIds.length === 0) return;
    await client
      .from('pms_receiving_items')
      .delete()
      .in('id', createdIds);
  };

  return { seed, cleanup };
}

/**
 * Helper to transition receiving through states
 *
 * Provides state machine transitions for receiving records:
 * - draft -> in_progress (start event)
 * - in_progress -> completed (complete event)
 * - completed -> accepted (accept with signature)
 * - completed -> rejected (report discrepancy)
 *
 * @example
 * ```ts
 * test('can complete receiving', async ({ seedReceiving, transitionReceivingState }) => {
 *   const receiving = await seedReceiving({ status: 'draft' });
 *   await transitionReceivingState(receiving.id, 'in_progress');
 *   // Receiving is now in_progress, ready for complete_receiving_event
 * });
 * ```
 */
export async function createTransitionStateFixture(supabase?: SupabaseClient): Promise<{
  transition: (receivingId: string, targetStatus: ReceivingStatus) => Promise<{
    id: string;
    previousStatus: ReceivingStatus;
    newStatus: ReceivingStatus;
  }>;
}> {
  const client = getClient(supabase);

  const transition = async (receivingId: string, targetStatus: ReceivingStatus) => {
    // Get current status
    const { data: current, error: fetchError } = await client
      .from('pms_receiving')
      .select('status')
      .eq('id', receivingId)
      .single();

    if (fetchError || !current) {
      throw new Error(`Failed to fetch receiving ${receivingId}: ${fetchError?.message || 'Not found'}`);
    }

    const previousStatus = current.status as ReceivingStatus;

    // Validate transition
    const validTransitions: Record<ReceivingStatus, ReceivingStatus[]> = {
      draft: ['in_progress'],
      in_progress: ['completed', 'in_review'],
      in_review: ['completed', 'in_progress'],
      completed: ['accepted', 'rejected'],
      accepted: [], // Terminal state
      rejected: ['in_progress'], // Can restart
    };

    if (!validTransitions[previousStatus]?.includes(targetStatus)) {
      throw new Error(`Invalid transition: ${previousStatus} -> ${targetStatus}`);
    }

    // Perform update
    const { error: updateError } = await client
      .from('pms_receiving')
      .update({ status: targetStatus })
      .eq('id', receivingId);

    if (updateError) {
      throw new Error(`Failed to transition receiving: ${updateError.message}`);
    }

    return {
      id: receivingId,
      previousStatus,
      newStatus: targetStatus,
    };
  };

  return { transition };
}

// =============================================================================
// BULK SEED FUNCTION - For Full Test Suite Setup
// =============================================================================

/**
 * Main seeding function - creates deterministic receiving test data
 *
 * Creates all required receiving records, line items, and documents
 * for comprehensive E2E testing of the Receiving domain.
 *
 * @param supabase - Optional Supabase client (creates one if not provided)
 * @returns ReceivingSeedResult with created data details
 */
export async function seedReceivingTestData(supabase?: SupabaseClient): Promise<ReceivingSeedResult> {
  const client = getClient(supabase);
  const errors: string[] = [];
  const createdReceivings: ReceivingSeedResult['receivings'] = [];
  const createdLineItems: ReceivingSeedResult['lineItems'] = [];
  const createdDocuments: ReceivingSeedResult['documents'] = [];

  try {
    // ==========================================================================
    // STEP 1: Clean up old test data
    // ==========================================================================
    console.log('[RECEIVING-SEED] Cleaning up old test data...');

    // Delete documents first (FK constraint)
    const receivingIds = Object.values(RECEIVING_TEST_IDS).filter(id => id.startsWith('recv000'));
    await client
      .from('pms_receiving_documents')
      .delete()
      .in('receiving_id', receivingIds);

    // Delete line items (FK constraint)
    await client
      .from('pms_receiving_items')
      .delete()
      .in('receiving_id', receivingIds);

    // Delete by deterministic IDs
    for (const id of receivingIds) {
      await client.from('pms_receiving').delete().eq('id', id);
    }

    // Also cleanup by vendor_name prefix
    await client
      .from('pms_receiving')
      .delete()
      .like('vendor_name', `${TEST_PREFIX}%`);

    // ==========================================================================
    // STEP 2: Get required foreign key references
    // ==========================================================================
    console.log('[RECEIVING-SEED] Fetching required references...');

    const userId = await getValidUserId(client);
    if (!userId) {
      errors.push('Failed to get user profile: No user found');
      return { success: false, receivings: [], lineItems: [], documents: [], errors };
    }

    console.log(`[RECEIVING-SEED] Using user: ${userId}`);

    // ==========================================================================
    // STEP 3: Seed Receiving Records
    // ==========================================================================
    console.log('[RECEIVING-SEED] Seeding receiving records...');

    const receivingsToCreate = [
      // 1. Draft status - for start_receiving_event tests
      {
        id: RECEIVING_TEST_IDS.RECEIVING_DRAFT,
        yacht_id: TEST_YACHT_ID,
        vendor_name: `${TEST_PREFIX}_VENDOR_DRAFT`,
        vendor_reference: 'REF-DRAFT-001',
        status: 'draft' as ReceivingStatus,
        total: 0,
        subtotal: 0,
        tax_total: 0,
        currency: 'USD',
        received_date: new Date().toISOString(),
        received_by: userId,
        created_by: userId,
        notes: 'Test receiving in DRAFT status for start_receiving_event E2E tests',
      },

      // 2. In Progress status - for add_line_item, complete tests
      {
        id: RECEIVING_TEST_IDS.RECEIVING_IN_PROGRESS,
        yacht_id: TEST_YACHT_ID,
        vendor_name: `${TEST_PREFIX}_VENDOR_IN_PROGRESS`,
        vendor_reference: 'REF-INPROG-001',
        status: 'in_progress' as ReceivingStatus,
        total: 150.00,
        subtotal: 125.00,
        tax_total: 25.00,
        currency: 'USD',
        received_date: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString(), // Yesterday
        received_by: userId,
        created_by: userId,
        notes: 'Test receiving IN PROGRESS for add_line_item and complete E2E tests',
      },

      // 3. Completed status - for accept/reject tests
      {
        id: RECEIVING_TEST_IDS.RECEIVING_COMPLETED,
        yacht_id: TEST_YACHT_ID,
        vendor_name: `${TEST_PREFIX}_VENDOR_COMPLETED`,
        vendor_reference: 'REF-COMPLETE-001',
        status: 'completed' as ReceivingStatus,
        total: 500.00,
        subtotal: 416.67,
        tax_total: 83.33,
        currency: 'USD',
        received_date: new Date(Date.now() - 2 * 24 * 60 * 60 * 1000).toISOString(), // 2 days ago
        received_by: userId,
        created_by: userId,
        notes: 'Test receiving COMPLETED for accept_receiving and report_discrepancy tests',
      },

      // 4. Accepted status - readonly verification
      {
        id: RECEIVING_TEST_IDS.RECEIVING_ACCEPTED,
        yacht_id: TEST_YACHT_ID,
        vendor_name: `${TEST_PREFIX}_VENDOR_ACCEPTED`,
        vendor_reference: 'REF-ACCEPTED-001',
        status: 'accepted' as ReceivingStatus,
        total: 750.00,
        subtotal: 625.00,
        tax_total: 125.00,
        currency: 'EUR',
        received_date: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString(), // 7 days ago
        received_by: userId,
        created_by: userId,
        notes: 'Test receiving ACCEPTED - terminal state, readonly for verification',
      },

      // 5. With Items - for adjust_receiving_item
      {
        id: RECEIVING_TEST_IDS.RECEIVING_WITH_ITEMS,
        yacht_id: TEST_YACHT_ID,
        vendor_name: `${TEST_PREFIX}_VENDOR_WITH_ITEMS`,
        vendor_reference: 'REF-ITEMS-001',
        status: 'in_progress' as ReceivingStatus,
        total: 350.00,
        subtotal: 291.67,
        tax_total: 58.33,
        currency: 'USD',
        received_date: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString(),
        received_by: userId,
        created_by: userId,
        notes: 'Test receiving WITH ITEMS for adjust_receiving_item E2E tests',
      },

      // 6. With Documents - for link_invoice_document
      {
        id: RECEIVING_TEST_IDS.RECEIVING_WITH_DOCS,
        yacht_id: TEST_YACHT_ID,
        vendor_name: `${TEST_PREFIX}_VENDOR_WITH_DOCS`,
        vendor_reference: 'REF-DOCS-001',
        status: 'in_progress' as ReceivingStatus,
        total: 200.00,
        subtotal: 166.67,
        tax_total: 33.33,
        currency: 'USD',
        received_date: new Date(Date.now() - 3 * 24 * 60 * 60 * 1000).toISOString(),
        received_by: userId,
        created_by: userId,
        notes: 'Test receiving WITH DOCS for link_invoice_document and attach_image tests',
      },
    ];

    for (const receiving of receivingsToCreate) {
      const { data, error } = await client
        .from('pms_receiving')
        .upsert(receiving, { onConflict: 'id' })
        .select('id, vendor_name, status, total, currency, received_date')
        .single();

      if (error) {
        errors.push(`Failed to create receiving ${receiving.vendor_name}: ${error.message}`);
      } else if (data) {
        createdReceivings.push({
          id: data.id,
          vendor_name: data.vendor_name,
          status: data.status as ReceivingStatus,
          total: data.total,
          currency: data.currency,
          received_date: data.received_date,
          itemCount: 0, // Will update after line items
        });
        console.log(`[RECEIVING-SEED] Created receiving: ${data.vendor_name} (${data.status})`);
      }
    }

    // ==========================================================================
    // STEP 4: Seed Line Items for RECEIVING_WITH_ITEMS
    // ==========================================================================
    console.log('[RECEIVING-SEED] Seeding line items...');

    const lineItemsToCreate = [
      {
        id: RECEIVING_TEST_IDS.LINE_ITEM_1,
        yacht_id: TEST_YACHT_ID,
        receiving_id: RECEIVING_TEST_IDS.RECEIVING_WITH_ITEMS,
        description: `${TEST_PREFIX}_ITEM_1: Engine Oil Filter`,
        quantity_expected: 5,
        quantity_received: 5,
        unit_price: 45.00,
        currency: 'USD',
        condition: 'new' as LineItemCondition,
        notes: 'First test line item - full quantity received',
      },
      {
        id: RECEIVING_TEST_IDS.LINE_ITEM_2,
        yacht_id: TEST_YACHT_ID,
        receiving_id: RECEIVING_TEST_IDS.RECEIVING_WITH_ITEMS,
        description: `${TEST_PREFIX}_ITEM_2: Hydraulic Fluid 5L`,
        quantity_expected: 10,
        quantity_received: 8,
        unit_price: 25.00,
        currency: 'USD',
        condition: 'new' as LineItemCondition,
        notes: 'Second test line item - partial quantity for discrepancy testing',
      },
      {
        id: RECEIVING_TEST_IDS.LINE_ITEM_3,
        yacht_id: TEST_YACHT_ID,
        receiving_id: RECEIVING_TEST_IDS.RECEIVING_WITH_ITEMS,
        description: `${TEST_PREFIX}_ITEM_3: Impeller Assembly`,
        quantity_expected: 2,
        quantity_received: 2,
        unit_price: 85.00,
        currency: 'USD',
        condition: 'refurbished' as LineItemCondition,
        serial_number: 'SN-IMP-12345',
        notes: 'Third test line item - with serial number and refurbished condition',
      },
    ];

    for (const item of lineItemsToCreate) {
      const { data, error } = await client
        .from('pms_receiving_items')
        .upsert(item, { onConflict: 'id' })
        .select('id, receiving_id, description, quantity_expected, quantity_received, unit_price, currency')
        .single();

      if (error) {
        errors.push(`Failed to create line item: ${error.message}`);
      } else if (data) {
        createdLineItems.push({
          id: data.id,
          receiving_id: data.receiving_id,
          description: data.description,
          quantity_expected: data.quantity_expected,
          quantity_received: data.quantity_received,
          unit_price: data.unit_price,
          currency: data.currency,
        });
        console.log(`[RECEIVING-SEED] Created line item: ${data.description}`);
      }
    }

    // Update item count on RECEIVING_WITH_ITEMS
    const withItemsIndex = createdReceivings.findIndex(r => r.id === RECEIVING_TEST_IDS.RECEIVING_WITH_ITEMS);
    if (withItemsIndex !== -1) {
      createdReceivings[withItemsIndex].itemCount = createdLineItems.length;
    }

    // ==========================================================================
    // RESULT
    // ==========================================================================
    const success = errors.length === 0;

    console.log('[RECEIVING-SEED] Seeding complete:', {
      success,
      receivingsCreated: createdReceivings.length,
      lineItemsCreated: createdLineItems.length,
      documentsCreated: createdDocuments.length,
      errors: errors.length > 0 ? errors : 'none',
    });

    return { success, receivings: createdReceivings, lineItems: createdLineItems, documents: createdDocuments, errors };
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    errors.push(`Unexpected error: ${message}`);
    return { success: false, receivings: createdReceivings, lineItems: createdLineItems, documents: createdDocuments, errors };
  }
}

// =============================================================================
// CLEANUP FUNCTION
// =============================================================================

/**
 * Cleanup function - removes all receiving test data
 */
export async function cleanupReceivingTestData(supabase?: SupabaseClient): Promise<void> {
  const client = getClient(supabase);

  console.log('[RECEIVING-SEED] Cleaning up test data...');

  // Get all receiving IDs from test IDs
  const receivingIds = Object.values(RECEIVING_TEST_IDS).filter(id => id.startsWith('recv000'));

  // Delete documents first (FK constraint)
  await client
    .from('pms_receiving_documents')
    .delete()
    .in('receiving_id', receivingIds);

  // Delete line items (FK constraint)
  await client
    .from('pms_receiving_items')
    .delete()
    .in('receiving_id', receivingIds);

  // Delete by deterministic IDs
  for (const id of receivingIds) {
    await client.from('pms_receiving').delete().eq('id', id);
  }

  // Also cleanup by vendor_name prefix
  await client
    .from('pms_receiving')
    .delete()
    .like('vendor_name', `${TEST_PREFIX}%`);

  console.log('[RECEIVING-SEED] Cleanup complete');
}

// =============================================================================
// VERIFY FUNCTION
// =============================================================================

/**
 * Verify receiving test data exists and meets requirements
 */
export async function verifyReceivingTestData(supabase?: SupabaseClient): Promise<{
  valid: boolean;
  status: {
    draftReceiving: boolean;
    inProgressReceiving: boolean;
    completedReceiving: boolean;
    acceptedReceiving: boolean;
    withItemsReceiving: boolean;
    withDocsReceiving: boolean;
    lineItemsExist: boolean;
  };
  ids: typeof RECEIVING_TEST_IDS;
}> {
  const client = getClient(supabase);

  // Check each required receiving exists with correct status
  const [
    { data: draftReceiving },
    { data: inProgressReceiving },
    { data: completedReceiving },
    { data: acceptedReceiving },
    { data: withItemsReceiving },
    { data: withDocsReceiving },
    { count: lineItemsCount },
  ] = await Promise.all([
    client.from('pms_receiving').select('id, status').eq('id', RECEIVING_TEST_IDS.RECEIVING_DRAFT).single(),
    client.from('pms_receiving').select('id, status').eq('id', RECEIVING_TEST_IDS.RECEIVING_IN_PROGRESS).single(),
    client.from('pms_receiving').select('id, status').eq('id', RECEIVING_TEST_IDS.RECEIVING_COMPLETED).single(),
    client.from('pms_receiving').select('id, status').eq('id', RECEIVING_TEST_IDS.RECEIVING_ACCEPTED).single(),
    client.from('pms_receiving').select('id, status').eq('id', RECEIVING_TEST_IDS.RECEIVING_WITH_ITEMS).single(),
    client.from('pms_receiving').select('id, status').eq('id', RECEIVING_TEST_IDS.RECEIVING_WITH_DOCS).single(),
    client.from('pms_receiving_items').select('*', { count: 'exact', head: true }).eq('receiving_id', RECEIVING_TEST_IDS.RECEIVING_WITH_ITEMS),
  ]);

  const status = {
    draftReceiving: draftReceiving?.status === 'draft',
    inProgressReceiving: inProgressReceiving?.status === 'in_progress',
    completedReceiving: completedReceiving?.status === 'completed',
    acceptedReceiving: acceptedReceiving?.status === 'accepted',
    withItemsReceiving: !!withItemsReceiving,
    withDocsReceiving: !!withDocsReceiving,
    lineItemsExist: (lineItemsCount || 0) >= 3,
  };

  const valid = Object.values(status).every(v => v === true);

  return { valid, status, ids: RECEIVING_TEST_IDS };
}

// =============================================================================
// GETTER HELPERS
// =============================================================================

/**
 * Get receiving by test ID for use in tests
 */
export function getReceivingTestId(key: keyof typeof RECEIVING_TEST_IDS): string {
  return RECEIVING_TEST_IDS[key];
}

// =============================================================================
// CLI SUPPORT
// =============================================================================

async function runCli(): Promise<void> {
  const command = process.argv[2];

  switch (command) {
    case 'seed':
      await seedReceivingTestData();
      break;
    case 'cleanup':
      await cleanupReceivingTestData();
      break;
    case 'verify': {
      const result = await verifyReceivingTestData();
      console.log('[RECEIVING-SEED] Verification result:', JSON.stringify(result, null, 2));
      process.exit(result.valid ? 0 : 1);
    }
    default:
      console.log('Receiving Test Fixtures');
      console.log('');
      console.log('Usage: npx ts-node e2e/fixtures/receiving-fixtures.ts [seed|cleanup|verify]');
      console.log('');
      console.log('Commands:');
      console.log('  seed    - Create receiving test data for E2E tests');
      console.log('  cleanup - Remove all receiving test data');
      console.log('  verify  - Check test data exists and meets requirements');
      console.log('');
      console.log('Known-Good Receiving IDs for E2E Tests:');
      console.log('  RECEIVING_DRAFT (for start_receiving):    ', RECEIVING_TEST_IDS.RECEIVING_DRAFT);
      console.log('  RECEIVING_IN_PROGRESS (for add_line_item):', RECEIVING_TEST_IDS.RECEIVING_IN_PROGRESS);
      console.log('  RECEIVING_COMPLETED (for accept/reject):  ', RECEIVING_TEST_IDS.RECEIVING_COMPLETED);
      console.log('  RECEIVING_ACCEPTED (readonly):            ', RECEIVING_TEST_IDS.RECEIVING_ACCEPTED);
      console.log('  RECEIVING_WITH_ITEMS (for adjustments):   ', RECEIVING_TEST_IDS.RECEIVING_WITH_ITEMS);
      console.log('  RECEIVING_WITH_DOCS (for documents):      ', RECEIVING_TEST_IDS.RECEIVING_WITH_DOCS);
      console.log('');
      console.log('Line Item IDs:');
      console.log('  LINE_ITEM_1:', RECEIVING_TEST_IDS.LINE_ITEM_1);
      console.log('  LINE_ITEM_2:', RECEIVING_TEST_IDS.LINE_ITEM_2);
      console.log('  LINE_ITEM_3:', RECEIVING_TEST_IDS.LINE_ITEM_3);
      process.exit(0);
  }
}

// Run CLI if executed directly
runCli().catch((err) => {
  console.error('[RECEIVING-SEED] Error:', err);
  process.exit(1);
});
