/**
 * Equipment Test Data Seed
 *
 * Creates deterministic test data for Equipment E2E testing (Task E4).
 * Each status type and condition has dedicated records with KNOWN UUIDs.
 *
 * IMPORTANT: Uses pms_equipment table with known test IDs for deterministic testing.
 *
 * Required Test States:
 * 1. Equipment in 'operational' status
 * 2. Equipment in 'maintenance' status
 * 3. Equipment in 'degraded' status (for status change tests)
 * 4. Equipment with attention_flag = true
 * 5. Equipment with linked parts (via work_order_parts)
 *
 * @see e2e/shard-7-equipment/equipment.spec.ts
 */

import { createClient } from '@supabase/supabase-js';
type SupabaseClient = ReturnType<typeof createClient>;

// Configuration
const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL || 'https://vzsohavtuotocgrfkfyd.supabase.co';
const SERVICE_KEY = process.env.SUPABASE_SERVICE_KEY || 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ6c29oYXZ0dW90b2NncmZrZnlkIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MzU5Mjg3NSwiZXhwIjoyMDc5MTY4ODc1fQ.fC7eC_4xGnCHIebPzfaJ18pFMPKgImE7BuN0I3A-pSY';
const YACHT_ID = process.env.TEST_YACHT_ID || '85fe1119-b04c-41ac-80f1-829d23322598';

// Test data prefix for identification and cleanup
const TEST_PREFIX = 'EQ_E2E_TEST';

// =============================================================================
// DETERMINISTIC TEST EQUIPMENT IDs - USE THESE IN E2E TESTS
// =============================================================================
/**
 * Known equipment IDs for deterministic E2E testing.
 * These UUIDs are generated once and reused across test runs.
 */
export const EQUIPMENT_TEST_IDS = {
  /** Equipment in 'operational' status - working normally */
  OPERATIONAL_1: 'e4e0-0001-0000-0000-000000000001',
  OPERATIONAL_2: 'e4e0-0002-0000-0000-000000000002',

  /** Equipment in 'maintenance' status - under service */
  MAINTENANCE_1: 'e4e0-0003-0000-0000-000000000003',
  MAINTENANCE_2: 'e4e0-0004-0000-0000-000000000004',

  /** Equipment in 'degraded' status - for status change tests */
  DEGRADED_1: 'e4e0-0005-0000-0000-000000000005',
  DEGRADED_2: 'e4e0-0006-0000-0000-000000000006',

  /** Equipment in 'failed' status - not working */
  FAILED_1: 'e4e0-0007-0000-0000-000000000007',

  /** Equipment with attention_flag = true */
  ATTENTION_FLAG_1: 'e4e0-0008-0000-0000-000000000008',
  ATTENTION_FLAG_2: 'e4e0-0009-0000-0000-000000000009',

  /** Equipment with linked parts (via work orders) */
  WITH_PARTS_1: 'e4e0-0010-0000-0000-000000000010',
  WITH_PARTS_2: 'e4e0-0011-0000-0000-000000000011',
} as const;

// Format UUIDs properly (fix shorthand)
function formatUUID(shortId: string): string {
  // e4e0-0001-0000-0000-000000000001 -> e4e00001-0000-0000-0000-000000000001
  const parts = shortId.split('-');
  if (parts.length === 5) {
    // Already formatted or close to it
    const first = parts[0] + parts[1].substring(0, 4);
    return `${first.padEnd(8, '0').substring(0, 8)}-${parts[1].substring(4).padEnd(4, '0').substring(0, 4) || '0000'}-${parts[2]}-${parts[3]}-${parts[4]}`;
  }
  return shortId;
}

// Properly formatted UUIDs for database insertion
const FORMATTED_IDS = {
  OPERATIONAL_1: 'e4e00001-0000-0000-0000-000000000001',
  OPERATIONAL_2: 'e4e00002-0000-0000-0000-000000000002',
  MAINTENANCE_1: 'e4e00003-0000-0000-0000-000000000003',
  MAINTENANCE_2: 'e4e00004-0000-0000-0000-000000000004',
  DEGRADED_1: 'e4e00005-0000-0000-0000-000000000005',
  DEGRADED_2: 'e4e00006-0000-0000-0000-000000000006',
  FAILED_1: 'e4e00007-0000-0000-0000-000000000007',
  ATTENTION_FLAG_1: 'e4e00008-0000-0000-0000-000000000008',
  ATTENTION_FLAG_2: 'e4e00009-0000-0000-0000-000000000009',
  WITH_PARTS_1: 'e4e00010-0000-0000-0000-000000000010',
  WITH_PARTS_2: 'e4e00011-0000-0000-0000-000000000011',
  // Parts for linking
  TEST_PART_1: 'e4e0part-0001-0000-0000-000000000001',
  TEST_PART_2: 'e4e0part-0002-0000-0000-000000000002',
  // Work order for parts linking
  TEST_WO_1: 'e4e0wo00-0001-0000-0000-000000000001',
} as const;

/**
 * Export IDs for use in test files
 */
export const E2E_EQUIPMENT_IDS = FORMATTED_IDS;

/**
 * Equipment status values from DB schema
 */
export type EquipmentStatus = 'operational' | 'degraded' | 'failed' | 'maintenance' | 'decommissioned';

/**
 * Seed result with stats
 */
export interface EquipmentSeedResult {
  success: boolean;
  stats: {
    equipmentCreated: number;
    partsCreated: number;
    workOrdersCreated: number;
  };
  ids: {
    equipment: string[];
    parts: string[];
    workOrders: string[];
  };
  errors: string[];
}

/**
 * Main seeding function - creates deterministic test equipment data
 *
 * @param supabase - Optional Supabase client (creates one if not provided)
 * @returns SeedResult with stats and IDs
 */
export async function seedEquipmentTestData(supabase?: SupabaseClient): Promise<EquipmentSeedResult> {
  const client = supabase || createClient(SUPABASE_URL, SERVICE_KEY, {
    auth: {
      autoRefreshToken: false,
      persistSession: false,
    },
  });

  const errors: string[] = [];
  const stats = {
    equipmentCreated: 0,
    partsCreated: 0,
    workOrdersCreated: 0,
  };
  const ids = {
    equipment: [] as string[],
    parts: [] as string[],
    workOrders: [] as string[],
  };

  try {
    // ==========================================================================
    // STEP 1: Clean up old test data
    // ==========================================================================
    console.log('[EQ-SEED] Cleaning up old test data...');

    // Delete work order parts first (FK constraint)
    await client
      .from('pms_work_order_parts')
      .delete()
      .in('work_order_id', [FORMATTED_IDS.TEST_WO_1]);

    // Delete work orders
    await client
      .from('pms_work_orders')
      .delete()
      .like('title', `${TEST_PREFIX}_%`);

    // Delete faults linked to test equipment
    await client
      .from('pms_faults')
      .delete()
      .in('equipment_id', Object.values(FORMATTED_IDS).filter(id => id.startsWith('e4e0000') || id.startsWith('e4e0001')));

    // Delete test parts
    await client
      .from('pms_parts')
      .delete()
      .like('name', `${TEST_PREFIX}_%`);

    // Delete test equipment
    await client
      .from('pms_equipment')
      .delete()
      .like('name', `${TEST_PREFIX}_%`);

    // ==========================================================================
    // STEP 2: Get required foreign key references
    // ==========================================================================
    console.log('[EQ-SEED] Fetching required references...');

    // Get a valid user ID for created_by fields
    const { data: userProfile, error: userError } = await client
      .from('auth_users_profiles')
      .select('id')
      .eq('yacht_id', YACHT_ID)
      .limit(1)
      .single();

    if (userError || !userProfile) {
      errors.push(`Failed to get user profile: ${userError?.message || 'No user found'}`);
      return { success: false, stats, ids, errors };
    }

    const createdBy = (userProfile as { id: string }).id;

    // ==========================================================================
    // STEP 3: Seed Equipment with various statuses
    // ==========================================================================
    console.log('[EQ-SEED] Seeding equipment...');

    const equipmentToCreate = [
      // OPERATIONAL equipment (2)
      {
        id: FORMATTED_IDS.OPERATIONAL_1,
        yacht_id: YACHT_ID,
        name: `${TEST_PREFIX}_Main_Engine_1`,
        code: 'E4E-ME-001',
        description: 'Test operational main engine #1',
        manufacturer: 'MTU',
        model: '16V 4000 M73L',
        serial_number: 'MTU-TEST-001',
        status: 'operational' as EquipmentStatus,
        criticality: 'critical',
        system_type: 'mechanical',
        location: 'Engine Room - Port',
        attention_flag: false,
        metadata: { test: true, variant: 'operational' },
      },
      {
        id: FORMATTED_IDS.OPERATIONAL_2,
        yacht_id: YACHT_ID,
        name: `${TEST_PREFIX}_Generator_1`,
        code: 'E4E-GEN-001',
        description: 'Test operational generator #1',
        manufacturer: 'Caterpillar',
        model: 'C18 ACERT',
        serial_number: 'CAT-TEST-001',
        status: 'operational' as EquipmentStatus,
        criticality: 'high',
        system_type: 'electrical',
        location: 'Engine Room - Starboard',
        attention_flag: false,
        metadata: { test: true, variant: 'operational' },
      },

      // MAINTENANCE equipment (2)
      {
        id: FORMATTED_IDS.MAINTENANCE_1,
        yacht_id: YACHT_ID,
        name: `${TEST_PREFIX}_Watermaker_1`,
        code: 'E4E-WM-001',
        description: 'Test watermaker under maintenance',
        manufacturer: 'Sea Recovery',
        model: 'Aqua Whisper Pro 1800',
        serial_number: 'SR-TEST-001',
        status: 'maintenance' as EquipmentStatus,
        criticality: 'medium',
        system_type: 'mechanical',
        location: 'Technical Space - Aft',
        attention_flag: false,
        metadata: { test: true, variant: 'maintenance' },
      },
      {
        id: FORMATTED_IDS.MAINTENANCE_2,
        yacht_id: YACHT_ID,
        name: `${TEST_PREFIX}_HVAC_Unit_1`,
        code: 'E4E-HVAC-001',
        description: 'Test HVAC under service',
        manufacturer: 'Dometic',
        model: 'Marine Turbo 24',
        serial_number: 'DOM-TEST-001',
        status: 'maintenance' as EquipmentStatus,
        criticality: 'medium',
        system_type: 'hvac',
        location: 'Technical Space - Forward',
        attention_flag: false,
        metadata: { test: true, variant: 'maintenance' },
      },

      // DEGRADED equipment (2) - for status change tests
      {
        id: FORMATTED_IDS.DEGRADED_1,
        yacht_id: YACHT_ID,
        name: `${TEST_PREFIX}_Bow_Thruster`,
        code: 'E4E-BT-001',
        description: 'Test degraded bow thruster for status change tests',
        manufacturer: 'Side-Power',
        model: 'SE200',
        serial_number: 'SP-TEST-001',
        status: 'degraded' as EquipmentStatus,
        criticality: 'high',
        system_type: 'mechanical',
        location: 'Bow Thruster Room',
        attention_flag: false,
        metadata: { test: true, variant: 'degraded', for_status_change_tests: true },
      },
      {
        id: FORMATTED_IDS.DEGRADED_2,
        yacht_id: YACHT_ID,
        name: `${TEST_PREFIX}_Stabilizer_1`,
        code: 'E4E-STAB-001',
        description: 'Test degraded stabilizer for status change tests',
        manufacturer: 'Naiad',
        model: 'Model 682',
        serial_number: 'NAIAD-TEST-001',
        status: 'degraded' as EquipmentStatus,
        criticality: 'medium',
        system_type: 'mechanical',
        location: 'Engine Room - Centerline',
        attention_flag: false,
        metadata: { test: true, variant: 'degraded', for_status_change_tests: true },
      },

      // FAILED equipment (1)
      {
        id: FORMATTED_IDS.FAILED_1,
        yacht_id: YACHT_ID,
        name: `${TEST_PREFIX}_Auxiliary_Pump`,
        code: 'E4E-AUX-001',
        description: 'Test failed auxiliary pump',
        manufacturer: 'Jabsco',
        model: 'V-Flo 5.0',
        serial_number: 'JAB-TEST-001',
        status: 'failed' as EquipmentStatus,
        criticality: 'low',
        system_type: 'mechanical',
        location: 'Lazarette',
        attention_flag: true,
        attention_reason: 'Failed - pending replacement',
        metadata: { test: true, variant: 'failed' },
      },

      // ATTENTION FLAG equipment (2)
      {
        id: FORMATTED_IDS.ATTENTION_FLAG_1,
        yacht_id: YACHT_ID,
        name: `${TEST_PREFIX}_Main_Engine_2`,
        code: 'E4E-ME-002',
        description: 'Test operational engine with attention flag',
        manufacturer: 'MTU',
        model: '16V 4000 M73L',
        serial_number: 'MTU-TEST-002',
        status: 'operational' as EquipmentStatus,
        criticality: 'critical',
        system_type: 'mechanical',
        location: 'Engine Room - Starboard',
        attention_flag: true,
        attention_reason: 'Oil analysis shows elevated wear metals',
        metadata: { test: true, variant: 'attention_flag' },
      },
      {
        id: FORMATTED_IDS.ATTENTION_FLAG_2,
        yacht_id: YACHT_ID,
        name: `${TEST_PREFIX}_Fire_Pump`,
        code: 'E4E-FP-001',
        description: 'Test fire pump with attention flag',
        manufacturer: 'Gianneschi',
        model: 'ACB 331',
        serial_number: 'GIA-TEST-001',
        status: 'operational' as EquipmentStatus,
        criticality: 'critical',
        system_type: 'safety',
        location: 'Engine Room - Forward',
        attention_flag: true,
        attention_reason: 'Annual inspection due',
        metadata: { test: true, variant: 'attention_flag' },
      },

      // Equipment for PARTS LINKING tests (2)
      {
        id: FORMATTED_IDS.WITH_PARTS_1,
        yacht_id: YACHT_ID,
        name: `${TEST_PREFIX}_Generator_2`,
        code: 'E4E-GEN-002',
        description: 'Test generator with linked parts',
        manufacturer: 'Caterpillar',
        model: 'C32 ACERT',
        serial_number: 'CAT-TEST-002',
        status: 'operational' as EquipmentStatus,
        criticality: 'high',
        system_type: 'electrical',
        location: 'Engine Room - Port',
        attention_flag: false,
        metadata: { test: true, variant: 'with_parts', has_bom: true },
      },
      {
        id: FORMATTED_IDS.WITH_PARTS_2,
        yacht_id: YACHT_ID,
        name: `${TEST_PREFIX}_Main_Engine_3`,
        code: 'E4E-ME-003',
        description: 'Test main engine with linked parts',
        manufacturer: 'MTU',
        model: '20V 4000 M93L',
        serial_number: 'MTU-TEST-003',
        status: 'operational' as EquipmentStatus,
        criticality: 'critical',
        system_type: 'mechanical',
        location: 'Engine Room - Centerline',
        attention_flag: false,
        metadata: { test: true, variant: 'with_parts', has_bom: true },
      },
    ];

    for (const equip of equipmentToCreate) {
      const { data, error } = await client
        .from('pms_equipment')
        .upsert(equip, { onConflict: 'id' })
        .select('id')
        .single();

      if (error) {
        errors.push(`Equipment ${equip.name}: ${error.message}`);
      } else {
        stats.equipmentCreated++;
        ids.equipment.push(data.id);
      }
    }

    console.log(`[EQ-SEED] Created ${stats.equipmentCreated} equipment records`);

    // ==========================================================================
    // STEP 4: Seed Parts for linking tests
    // ==========================================================================
    console.log('[EQ-SEED] Seeding parts...');

    const partsToCreate = [
      {
        id: FORMATTED_IDS.TEST_PART_1,
        yacht_id: YACHT_ID,
        name: `${TEST_PREFIX}_Oil_Filter_CAT`,
        part_number: 'E4E-OF-CAT-001',
        description: 'Oil filter for CAT C32/C18 generators',
        manufacturer: 'Caterpillar',
        category: 'Filters',
        unit: 'ea',
        minimum_quantity: 3,
        quantity_on_hand: 5,
        location: 'Engine Room Stores - Shelf A1',
        metadata: { test: true, compatible_equipment: [FORMATTED_IDS.WITH_PARTS_1] },
      },
      {
        id: FORMATTED_IDS.TEST_PART_2,
        yacht_id: YACHT_ID,
        name: `${TEST_PREFIX}_Fuel_Filter_MTU`,
        part_number: 'E4E-FF-MTU-001',
        description: 'Fuel filter for MTU 4000 series engines',
        manufacturer: 'MTU',
        category: 'Filters',
        unit: 'ea',
        minimum_quantity: 2,
        quantity_on_hand: 4,
        location: 'Engine Room Stores - Shelf A2',
        metadata: { test: true, compatible_equipment: [FORMATTED_IDS.WITH_PARTS_2] },
      },
    ];

    for (const part of partsToCreate) {
      const { data, error } = await client
        .from('pms_parts')
        .upsert(part, { onConflict: 'id' })
        .select('id')
        .single();

      if (error) {
        errors.push(`Part ${part.name}: ${error.message}`);
      } else {
        stats.partsCreated++;
        ids.parts.push(data.id);
      }
    }

    console.log(`[EQ-SEED] Created ${stats.partsCreated} parts records`);

    // ==========================================================================
    // STEP 5: Create work order linking equipment to parts
    // ==========================================================================
    console.log('[EQ-SEED] Creating work order for parts linking...');

    const workOrderData = {
      id: FORMATTED_IDS.TEST_WO_1,
      yacht_id: YACHT_ID,
      title: `${TEST_PREFIX}_Service_WO`,
      wo_number: 'E4E-WO-001',
      description: 'Test work order for equipment-parts linking',
      equipment_id: FORMATTED_IDS.WITH_PARTS_1,
      status: 'planned',
      priority: 'routine',
      type: 'scheduled',
      work_order_type: 'planned',
      created_by: createdBy,
      due_date: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
      metadata: { test: true },
    };

    const { data: woData, error: woError } = await client
      .from('pms_work_orders')
      .upsert(workOrderData, { onConflict: 'id' })
      .select('id')
      .single();

    if (woError) {
      errors.push(`Work order: ${woError.message}`);
    } else {
      stats.workOrdersCreated++;
      ids.workOrders.push(woData.id);
      console.log(`[EQ-SEED] Created work order ${woData.id}`);

      // Link parts to work order
      const workOrderParts = [
        { work_order_id: woData.id, part_id: FORMATTED_IDS.TEST_PART_1, quantity: 2, added_by: createdBy },
        { work_order_id: woData.id, part_id: FORMATTED_IDS.TEST_PART_2, quantity: 1, added_by: createdBy },
      ];

      for (const woPart of workOrderParts) {
        const { error: linkError } = await client
          .from('pms_work_order_parts')
          .upsert(woPart, { onConflict: 'work_order_id,part_id' });

        if (linkError && !linkError.message.includes('duplicate')) {
          console.warn(`[EQ-SEED] Warning linking part: ${linkError.message}`);
        }
      }
    }

    // ==========================================================================
    // RESULT
    // ==========================================================================
    const success = errors.length === 0;

    console.log('[EQ-SEED] Seeding complete:', {
      success,
      stats,
      errors: errors.length > 0 ? errors : 'none',
    });

    return { success, stats, ids, errors };
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    errors.push(`Unexpected error: ${message}`);
    return { success: false, stats, ids, errors };
  }
}

/**
 * Cleanup function - removes all test equipment data
 */
export async function cleanupEquipmentTestData(supabase?: SupabaseClient): Promise<void> {
  const client = supabase || createClient(SUPABASE_URL, SERVICE_KEY, {
    auth: {
      autoRefreshToken: false,
      persistSession: false,
    },
  });

  console.log('[EQ-SEED] Cleaning up test data...');

  // Delete in order to respect foreign key constraints
  await client.from('pms_work_order_parts').delete().in('work_order_id', [FORMATTED_IDS.TEST_WO_1]);
  await client.from('pms_work_orders').delete().like('title', `${TEST_PREFIX}_%`);
  await client.from('pms_faults').delete().in('equipment_id', Object.values(FORMATTED_IDS));
  await client.from('pms_parts').delete().like('name', `${TEST_PREFIX}_%`);
  await client.from('pms_equipment').delete().like('name', `${TEST_PREFIX}_%`);

  console.log('[EQ-SEED] Cleanup complete');
}

/**
 * Verify test equipment data exists and meets requirements
 */
export async function verifyEquipmentTestData(supabase?: SupabaseClient): Promise<{
  valid: boolean;
  counts: {
    operational: number;
    maintenance: number;
    degraded: number;
    failed: number;
    withAttentionFlag: number;
    withLinkedParts: number;
  };
}> {
  const client = supabase || createClient(SUPABASE_URL, SERVICE_KEY, {
    auth: {
      autoRefreshToken: false,
      persistSession: false,
    },
  });

  const [
    { count: operational },
    { count: maintenance },
    { count: degraded },
    { count: failed },
    { count: withAttentionFlag },
    { count: withLinkedParts },
  ] = await Promise.all([
    client.from('pms_equipment').select('*', { count: 'exact', head: true }).like('name', `${TEST_PREFIX}_%`).eq('status', 'operational'),
    client.from('pms_equipment').select('*', { count: 'exact', head: true }).like('name', `${TEST_PREFIX}_%`).eq('status', 'maintenance'),
    client.from('pms_equipment').select('*', { count: 'exact', head: true }).like('name', `${TEST_PREFIX}_%`).eq('status', 'degraded'),
    client.from('pms_equipment').select('*', { count: 'exact', head: true }).like('name', `${TEST_PREFIX}_%`).eq('status', 'failed'),
    client.from('pms_equipment').select('*', { count: 'exact', head: true }).like('name', `${TEST_PREFIX}_%`).eq('attention_flag', true),
    client.from('pms_equipment').select('*', { count: 'exact', head: true }).like('name', `${TEST_PREFIX}_%`).contains('metadata', { has_bom: true }),
  ]);

  const counts = {
    operational: operational || 0,
    maintenance: maintenance || 0,
    degraded: degraded || 0,
    failed: failed || 0,
    withAttentionFlag: withAttentionFlag || 0,
    withLinkedParts: withLinkedParts || 0,
  };

  // Validate requirements
  const valid =
    counts.operational >= 2 &&
    counts.maintenance >= 2 &&
    counts.degraded >= 2 &&
    counts.failed >= 1 &&
    counts.withAttentionFlag >= 2 &&
    counts.withLinkedParts >= 2;

  return { valid, counts };
}

// =============================================================================
// CLI Support - Run standalone with: npx ts-node e2e/fixtures/equipment-seed.ts
// =============================================================================

async function runCli(): Promise<void> {
  const command = process.argv[2];

  switch (command) {
    case 'seed':
      await seedEquipmentTestData();
      break;
    case 'cleanup':
      await cleanupEquipmentTestData();
      break;
    case 'verify': {
      const result = await verifyEquipmentTestData();
      console.log('[EQ-SEED] Verification result:', JSON.stringify(result, null, 2));
      process.exit(result.valid ? 0 : 1);
    }
    default:
      console.log('Usage: npx ts-node e2e/fixtures/equipment-seed.ts [seed|cleanup|verify]');
      console.log('');
      console.log('Commands:');
      console.log('  seed    - Create test equipment data');
      console.log('  cleanup - Remove all test equipment data');
      console.log('  verify  - Check test data exists and meets requirements');
      console.log('');
      console.log('Known Equipment IDs for E2E tests:');
      console.log(JSON.stringify(FORMATTED_IDS, null, 2));
      process.exit(0);
  }
}

// Run CLI if executed directly (ESM compatible)
runCli().catch((err) => {
  console.error('[EQ-SEED] Error:', err);
  process.exit(1);
});
