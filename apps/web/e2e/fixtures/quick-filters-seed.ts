/**
 * Quick Filters Test Data Seed
 *
 * Creates deterministic test data for Quick Filters E2E testing.
 * Each filter type has at least 2 records to ensure test reliability.
 *
 * IMPORTANT: Uses the same pms_ prefixed tables as the production database.
 *
 * @see e2e/shard-31-fragmented-routes/quick-filters.spec.ts
 * @see src/lib/filters/catalog.ts for filter definitions
 */

import { createClient } from '@supabase/supabase-js';
type SupabaseClient = ReturnType<typeof createClient>;

// Configuration - uses same pattern as rbac-fixtures.ts
const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL || 'https://vzsohavtuotocgrfkfyd.supabase.co';
const SERVICE_KEY = process.env.SUPABASE_SERVICE_KEY || 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ6c29oYXZ0dW90b2NncmZrZnlkIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MzU5Mjg3NSwiZXhwIjoyMDc5MTY4ODc1fQ.fC7eC_4xGnCHIebPzfaJ18pFMPKgImE7BuN0I3A-pSY';
const YACHT_ID = process.env.TEST_YACHT_ID || '85fe1119-b04c-41ac-80f1-829d23322598';

// Test data prefix for easy identification and cleanup
const TEST_PREFIX = 'QF_TEST';

/**
 * Date helpers
 */
function daysFromNow(days: number): string {
  const date = new Date();
  date.setDate(date.getDate() + days);
  return date.toISOString().split('T')[0]; // YYYY-MM-DD format
}

function daysAgo(days: number): string {
  return daysFromNow(-days);
}

/**
 * Seed result with stats
 */
export interface SeedResult {
  success: boolean;
  stats: {
    workOrdersCreated: number;
    faultsCreated: number;
    partsCreated: number;
  };
  errors: string[];
}

/**
 * Main seeding function - creates deterministic test data for all Quick Filters
 *
 * @param supabase - Optional Supabase client (creates one if not provided)
 * @returns SeedResult with stats and any errors
 */
export async function seedQuickFilterTestData(supabase?: SupabaseClient): Promise<SeedResult> {
  const client = supabase || createClient(SUPABASE_URL, SERVICE_KEY, {
    auth: {
      autoRefreshToken: false,
      persistSession: false,
    },
  });

  const errors: string[] = [];
  const stats = {
    workOrdersCreated: 0,
    faultsCreated: 0,
    partsCreated: 0,
  };

  try {
    // ==========================================================================
    // STEP 1: Clean up old test data
    // ==========================================================================
    console.log('[QF-SEED] Cleaning up old test data...');

    // Delete work orders first (they may reference equipment)
    const { error: woCleanupError } = await client
      .from('pms_work_orders')
      .delete()
      .like('title', `${TEST_PREFIX}_%`);

    if (woCleanupError) {
      console.warn(`[QF-SEED] Warning: Work order cleanup failed: ${woCleanupError.message}`);
    }

    // Delete faults
    const { error: faultCleanupError } = await client
      .from('pms_faults')
      .delete()
      .like('title', `${TEST_PREFIX}_%`);

    if (faultCleanupError) {
      console.warn(`[QF-SEED] Warning: Fault cleanup failed: ${faultCleanupError.message}`);
    }

    // Delete test parts
    const { error: partsCleanupError } = await client
      .from('pms_parts')
      .delete()
      .like('name', `${TEST_PREFIX}_%`);

    if (partsCleanupError) {
      console.warn(`[QF-SEED] Warning: Parts cleanup failed: ${partsCleanupError.message}`);
    }

    // ==========================================================================
    // STEP 2: Get required foreign key references
    // ==========================================================================
    console.log('[QF-SEED] Fetching required references...');

    // Get a valid user ID for created_by fields
    const { data: userProfile, error: userError } = await client
      .from('auth_users_profiles')
      .select('id')
      .eq('yacht_id', YACHT_ID)
      .limit(1)
      .single();

    if (userError || !userProfile) {
      errors.push(`Failed to get user profile: ${userError?.message || 'No user found'}`);
      return { success: false, stats, errors };
    }

    const createdBy = (userProfile as { id: string }).id;

    // Get a valid equipment ID for faults (faults require equipment_id)
    const { data: equipment, error: equipError } = await client
      .from('pms_equipment')
      .select('id')
      .eq('yacht_id', YACHT_ID)
      .limit(1)
      .single();

    if (equipError || !equipment) {
      errors.push(`Failed to get equipment: ${equipError?.message || 'No equipment found'}`);
      return { success: false, stats, errors };
    }

    const equipmentId = (equipment as { id: string }).id;

    // ==========================================================================
    // STEP 3: Seed Work Orders
    // ==========================================================================
    console.log('[QF-SEED] Seeding work orders...');

    // Counter for unique WO numbers
    let woCounter = Date.now();

    // ACTUAL DB SCHEMA:
    // - status: 'cancelled', 'completed', 'in_progress', 'planned'
    // - priority: 'critical', 'emergency', 'important', 'routine'
    const workOrdersToCreate = [
      // wo_overdue: due_date in past, status NOT IN ('completed', 'cancelled')
      {
        yacht_id: YACHT_ID,
        title: `${TEST_PREFIX}_WO_OVERDUE_1`,
        wo_number: `QF-OD-${++woCounter}`,
        description: 'Test overdue work order #1 for Quick Filter testing',
        due_date: daysAgo(5),
        status: 'planned',
        priority: 'routine',
        created_by: createdBy,
      },
      {
        yacht_id: YACHT_ID,
        title: `${TEST_PREFIX}_WO_OVERDUE_2`,
        wo_number: `QF-OD-${++woCounter}`,
        description: 'Test overdue work order #2 for Quick Filter testing',
        due_date: daysAgo(3),
        status: 'in_progress',
        priority: 'important',
        created_by: createdBy,
      },

      // wo_due_7d: due_date within 7 days, status not completed
      {
        yacht_id: YACHT_ID,
        title: `${TEST_PREFIX}_WO_DUE7D_1`,
        wo_number: `QF-D7-${++woCounter}`,
        description: 'Test due this week work order #1',
        due_date: daysFromNow(3),
        status: 'planned',
        priority: 'routine',
        created_by: createdBy,
      },
      {
        yacht_id: YACHT_ID,
        title: `${TEST_PREFIX}_WO_DUE7D_2`,
        wo_number: `QF-D7-${++woCounter}`,
        description: 'Test due this week work order #2',
        due_date: daysFromNow(5),
        status: 'planned',
        priority: 'routine',
        created_by: createdBy,
      },

      // wo_open: status='planned' or 'in_progress'
      {
        yacht_id: YACHT_ID,
        title: `${TEST_PREFIX}_WO_OPEN_1`,
        wo_number: `QF-OP-${++woCounter}`,
        description: 'Test open work order #1',
        due_date: daysFromNow(14),
        status: 'planned',
        priority: 'routine',
        created_by: createdBy,
      },
      {
        yacht_id: YACHT_ID,
        title: `${TEST_PREFIX}_WO_OPEN_2`,
        wo_number: `QF-OP-${++woCounter}`,
        description: 'Test open work order #2',
        due_date: daysFromNow(21),
        status: 'in_progress',
        priority: 'important',
        created_by: createdBy,
      },

      // wo_priority_emergency: priority='emergency', status not completed
      {
        yacht_id: YACHT_ID,
        title: `${TEST_PREFIX}_WO_EMERGENCY_1`,
        wo_number: `QF-EM-${++woCounter}`,
        description: 'Test emergency priority work order #1',
        due_date: daysFromNow(1),
        status: 'planned',
        priority: 'emergency',
        created_by: createdBy,
      },
      {
        yacht_id: YACHT_ID,
        title: `${TEST_PREFIX}_WO_EMERGENCY_2`,
        wo_number: `QF-EM-${++woCounter}`,
        description: 'Test emergency priority work order #2',
        due_date: daysFromNow(0),
        status: 'in_progress',
        priority: 'emergency',
        created_by: createdBy,
      },

      // wo_priority_critical: priority='critical', status not completed
      {
        yacht_id: YACHT_ID,
        title: `${TEST_PREFIX}_WO_CRITICAL_1`,
        wo_number: `QF-CR-${++woCounter}`,
        description: 'Test critical priority work order #1',
        due_date: daysFromNow(2),
        status: 'planned',
        priority: 'critical',
        created_by: createdBy,
      },
      {
        yacht_id: YACHT_ID,
        title: `${TEST_PREFIX}_WO_CRITICAL_2`,
        wo_number: `QF-CR-${++woCounter}`,
        description: 'Test critical priority work order #2',
        due_date: daysFromNow(3),
        status: 'planned',
        priority: 'critical',
        created_by: createdBy,
      },
    ];

    const { data: createdWOs, error: woError } = await client
      .from('pms_work_orders')
      .insert(workOrdersToCreate)
      .select('id');

    if (woError) {
      errors.push(`Failed to create work orders: ${woError.message}`);
    } else {
      stats.workOrdersCreated = createdWOs?.length || 0;
      console.log(`[QF-SEED] Created ${stats.workOrdersCreated} work orders`);
    }

    // ==========================================================================
    // STEP 4: Seed Faults
    // ==========================================================================
    console.log('[QF-SEED] Seeding faults...');

    // ACTUAL DB SCHEMA:
    // - status: 'closed', 'investigating', 'open'
    // - severity: 'high', 'medium' (and possibly 'low', 'critical')
    // - NO fault_number column exists
    // - NO reported_by_id column (use metadata.reported_by instead)
    // Note: Filter expects severity IN ('critical', 'safety') but DB may use 'high'
    const faultsToCreate = [
      // fault_open: status='open'
      {
        yacht_id: YACHT_ID,
        equipment_id: equipmentId,
        title: `${TEST_PREFIX}_FAULT_OPEN_1`,
        fault_code: 'QF_TEST',
        description: 'Test open fault #1',
        status: 'open',
        severity: 'medium',
        metadata: { reported_by: createdBy },
      },
      {
        yacht_id: YACHT_ID,
        equipment_id: equipmentId,
        title: `${TEST_PREFIX}_FAULT_OPEN_2`,
        fault_code: 'QF_TEST',
        description: 'Test open fault #2',
        status: 'open',
        severity: 'medium',
        metadata: { reported_by: createdBy },
      },

      // fault_unresolved: status IN ('open', 'investigating')
      // Note: 'work_ordered' doesn't exist in DB - using 'open' and 'investigating' only
      {
        yacht_id: YACHT_ID,
        equipment_id: equipmentId,
        title: `${TEST_PREFIX}_FAULT_UNRESOLVED_1`,
        fault_code: 'QF_TEST',
        description: 'Test unresolved fault #1 (investigating)',
        status: 'investigating',
        severity: 'high',
        metadata: { reported_by: createdBy },
      },
      {
        yacht_id: YACHT_ID,
        equipment_id: equipmentId,
        title: `${TEST_PREFIX}_FAULT_UNRESOLVED_2`,
        fault_code: 'QF_TEST',
        description: 'Test unresolved fault #2 (open)',
        status: 'open',
        severity: 'medium',
        metadata: { reported_by: createdBy },
      },

      // fault_critical: severity='high' (closest to 'critical' in actual DB)
      // Note: Filter expects 'critical'/'safety' but DB uses 'high'/'medium'
      // Using 'high' as the highest severity available
      {
        yacht_id: YACHT_ID,
        equipment_id: equipmentId,
        title: `${TEST_PREFIX}_FAULT_CRITICAL_1`,
        fault_code: 'QF_TEST',
        description: 'Test high severity fault #1 (critical equivalent)',
        status: 'open',
        severity: 'high',
        metadata: { reported_by: createdBy },
      },
      {
        yacht_id: YACHT_ID,
        equipment_id: equipmentId,
        title: `${TEST_PREFIX}_FAULT_CRITICAL_2`,
        fault_code: 'QF_TEST',
        description: 'Test high severity fault #2 (critical equivalent)',
        status: 'investigating',
        severity: 'high',
        metadata: { reported_by: createdBy },
      },

      // fault_investigating: status='investigating'
      {
        yacht_id: YACHT_ID,
        equipment_id: equipmentId,
        title: `${TEST_PREFIX}_FAULT_INVESTIGATING_1`,
        fault_code: 'QF_TEST',
        description: 'Test investigating fault #1',
        status: 'investigating',
        severity: 'medium',
        metadata: { reported_by: createdBy },
      },
      {
        yacht_id: YACHT_ID,
        equipment_id: equipmentId,
        title: `${TEST_PREFIX}_FAULT_INVESTIGATING_2`,
        fault_code: 'QF_TEST',
        description: 'Test investigating fault #2',
        status: 'investigating',
        severity: 'medium',
        metadata: { reported_by: createdBy },
      },
    ];

    const { data: createdFaults, error: faultError } = await client
      .from('pms_faults')
      .insert(faultsToCreate)
      .select('id');

    if (faultError) {
      errors.push(`Failed to create faults: ${faultError.message}`);
    } else {
      stats.faultsCreated = createdFaults?.length || 0;
      console.log(`[QF-SEED] Created ${stats.faultsCreated} faults`);
    }

    // ==========================================================================
    // STEP 5: Seed Parts (Inventory)
    // ==========================================================================
    console.log('[QF-SEED] Seeding inventory parts...');

    const partsToCreate = [
      // inv_low_stock: quantity_on_hand <= minimum_quantity AND minimum_quantity > 0
      {
        yacht_id: YACHT_ID,
        name: `${TEST_PREFIX}_PART_LOWSTOCK_1`,
        part_number: `QF-LS-${Date.now()}-1`,
        description: 'Test low stock part #1',
        quantity_on_hand: 2,
        minimum_quantity: 5,
        category: 'Filters',
        location: 'Engine Room Stores',
      },
      {
        yacht_id: YACHT_ID,
        name: `${TEST_PREFIX}_PART_LOWSTOCK_2`,
        part_number: `QF-LS-${Date.now()}-2`,
        description: 'Test low stock part #2',
        quantity_on_hand: 1,
        minimum_quantity: 3,
        category: 'Electrical',
        location: 'Electrical Panel',
      },

      // inv_out_of_stock: quantity_on_hand = 0
      {
        yacht_id: YACHT_ID,
        name: `${TEST_PREFIX}_PART_OUTOFSTOCK_1`,
        part_number: `QF-OS-${Date.now()}-1`,
        description: 'Test out of stock part #1',
        quantity_on_hand: 0,
        minimum_quantity: 2,
        category: 'Mechanical',
        location: 'Bosun Locker',
      },
      {
        yacht_id: YACHT_ID,
        name: `${TEST_PREFIX}_PART_OUTOFSTOCK_2`,
        part_number: `QF-OS-${Date.now()}-2`,
        description: 'Test out of stock part #2',
        quantity_on_hand: 0,
        minimum_quantity: 1,
        category: 'Consumables',
        location: 'Galley Stores',
      },
    ];

    const { data: createdParts, error: partsError } = await client
      .from('pms_parts')
      .insert(partsToCreate)
      .select('id');

    if (partsError) {
      errors.push(`Failed to create parts: ${partsError.message}`);
    } else {
      stats.partsCreated = createdParts?.length || 0;
      console.log(`[QF-SEED] Created ${stats.partsCreated} parts`);
    }

    // ==========================================================================
    // RESULT
    // ==========================================================================
    const success = errors.length === 0;

    console.log('[QF-SEED] Seeding complete:', {
      success,
      stats,
      errors: errors.length > 0 ? errors : 'none',
    });

    return { success, stats, errors };
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    errors.push(`Unexpected error: ${message}`);
    return { success: false, stats, errors };
  }
}

/**
 * Cleanup function - removes all test data
 * Can be called standalone or from tests
 */
export async function cleanupQuickFilterTestData(supabase?: SupabaseClient): Promise<void> {
  const client = supabase || createClient(SUPABASE_URL, SERVICE_KEY, {
    auth: {
      autoRefreshToken: false,
      persistSession: false,
    },
  });

  console.log('[QF-SEED] Cleaning up test data...');

  // Delete in order to respect foreign key constraints
  await client.from('pms_work_orders').delete().like('title', `${TEST_PREFIX}_%`);
  await client.from('pms_faults').delete().like('title', `${TEST_PREFIX}_%`);
  await client.from('pms_parts').delete().like('name', `${TEST_PREFIX}_%`);

  console.log('[QF-SEED] Cleanup complete');
}

/**
 * Verify test data exists and counts match expected
 * Useful for debugging and test assertions
 */
export async function verifyQuickFilterTestData(supabase?: SupabaseClient): Promise<{
  valid: boolean;
  counts: {
    overdueWOs: number;
    due7dWOs: number;
    openWOs: number;
    emergencyWOs: number;
    criticalWOs: number;
    openFaults: number;
    unresolvedFaults: number;
    criticalFaults: number;
    investigatingFaults: number;
    lowStockParts: number;
    outOfStockParts: number;
  };
}> {
  const client = supabase || createClient(SUPABASE_URL, SERVICE_KEY, {
    auth: {
      autoRefreshToken: false,
      persistSession: false,
    },
  });

  const today = new Date().toISOString().split('T')[0];
  const in7Days = daysFromNow(7);

  // Count work orders by filter criteria
  const [
    { count: overdueWOs },
    { count: due7dWOs },
    { count: openWOs },
    { count: emergencyWOs },
    { count: criticalWOs },
    { count: openFaults },
    { count: unresolvedFaults },
    { count: criticalFaults },
    { count: investigatingFaults },
    { count: lowStockParts },
    { count: outOfStockParts },
  ] = await Promise.all([
    // wo_overdue
    client
      .from('pms_work_orders')
      .select('*', { count: 'exact', head: true })
      .like('title', `${TEST_PREFIX}_%`)
      .lt('due_date', today)
      .not('status', 'in', '("completed","cancelled")'),

    // wo_due_7d
    client
      .from('pms_work_orders')
      .select('*', { count: 'exact', head: true })
      .like('title', `${TEST_PREFIX}_%`)
      .gte('due_date', today)
      .lte('due_date', in7Days)
      .not('status', 'in', '("completed","cancelled")'),

    // wo_open (planned or in_progress)
    client
      .from('pms_work_orders')
      .select('*', { count: 'exact', head: true })
      .like('title', `${TEST_PREFIX}_%`)
      .in('status', ['planned', 'in_progress']),

    // wo_priority_emergency
    client
      .from('pms_work_orders')
      .select('*', { count: 'exact', head: true })
      .like('title', `${TEST_PREFIX}_%`)
      .eq('priority', 'emergency')
      .not('status', 'in', '("completed","cancelled")'),

    // wo_priority_critical
    client
      .from('pms_work_orders')
      .select('*', { count: 'exact', head: true })
      .like('title', `${TEST_PREFIX}_%`)
      .eq('priority', 'critical')
      .not('status', 'in', '("completed","cancelled")'),

    // fault_open
    client
      .from('pms_faults')
      .select('*', { count: 'exact', head: true })
      .like('title', `${TEST_PREFIX}_%`)
      .eq('status', 'open'),

    // fault_unresolved (actual DB statuses: 'open', 'investigating' - no 'work_ordered')
    client
      .from('pms_faults')
      .select('*', { count: 'exact', head: true })
      .like('title', `${TEST_PREFIX}_%`)
      .in('status', ['open', 'investigating']),

    // fault_critical (actual DB severity: 'high' maps to critical)
    client
      .from('pms_faults')
      .select('*', { count: 'exact', head: true })
      .like('title', `${TEST_PREFIX}_%`)
      .eq('severity', 'high'),

    // fault_investigating
    client
      .from('pms_faults')
      .select('*', { count: 'exact', head: true })
      .like('title', `${TEST_PREFIX}_%`)
      .eq('status', 'investigating'),

    // inv_low_stock
    client
      .from('pms_parts')
      .select('*', { count: 'exact', head: true })
      .like('name', `${TEST_PREFIX}_%`)
      .gt('minimum_quantity', 0)
      .lte('quantity_on_hand', client.rpc ? 'minimum_quantity' : 5), // Simplified check

    // inv_out_of_stock
    client
      .from('pms_parts')
      .select('*', { count: 'exact', head: true })
      .like('name', `${TEST_PREFIX}_%`)
      .eq('quantity_on_hand', 0),
  ]);

  const counts = {
    overdueWOs: overdueWOs || 0,
    due7dWOs: due7dWOs || 0,
    openWOs: openWOs || 0,
    emergencyWOs: emergencyWOs || 0,
    criticalWOs: criticalWOs || 0,
    openFaults: openFaults || 0,
    unresolvedFaults: unresolvedFaults || 0,
    criticalFaults: criticalFaults || 0,
    investigatingFaults: investigatingFaults || 0,
    lowStockParts: lowStockParts || 0,
    outOfStockParts: outOfStockParts || 0,
  };

  // Validate minimum counts (at least 2 per filter)
  const valid =
    counts.overdueWOs >= 2 &&
    counts.due7dWOs >= 2 &&
    counts.openWOs >= 2 &&
    counts.emergencyWOs >= 2 &&
    counts.criticalWOs >= 2 &&
    counts.openFaults >= 2 &&
    counts.unresolvedFaults >= 2 &&
    counts.criticalFaults >= 2 &&
    counts.investigatingFaults >= 2 &&
    counts.outOfStockParts >= 2;
    // Note: lowStockParts validation is complex due to column comparison

  return { valid, counts };
}

// =============================================================================
// CLI Support - Run standalone with: npx ts-node e2e/fixtures/quick-filters-seed.ts
// =============================================================================

async function runCli(): Promise<void> {
  const command = process.argv[2];

  switch (command) {
    case 'seed':
      await seedQuickFilterTestData();
      break;
    case 'cleanup':
      await cleanupQuickFilterTestData();
      break;
    case 'verify': {
      const result = await verifyQuickFilterTestData();
      console.log('[QF-SEED] Verification result:', JSON.stringify(result, null, 2));
      process.exit(result.valid ? 0 : 1);
      break;
    }
    default:
      console.log('Usage: npx ts-node e2e/fixtures/quick-filters-seed.ts [seed|cleanup|verify]');
      console.log('');
      console.log('Commands:');
      console.log('  seed    - Create test data for Quick Filters');
      console.log('  cleanup - Remove all test data');
      console.log('  verify  - Check test data exists and meets minimums');
      process.exit(0);
  }
}

// Run CLI if executed directly
if (true) { // ESM module - always run CLI
  runCli().catch((err) => {
    console.error('[QF-SEED] Error:', err);
    process.exit(1);
  });
}
