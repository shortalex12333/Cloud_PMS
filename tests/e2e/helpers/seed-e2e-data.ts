/**
 * E2E Test Data Seeder
 *
 * Seeds deterministic test data for canonical journey E2E tests.
 * Uses fixed UUIDs for reproducibility.
 *
 * REQUIRED: This must run BEFORE E2E tests.
 * If seeding fails, tests MUST fail - no "if exists, skip" logic.
 */

import { createClient } from '@supabase/supabase-js';

// ============================================================================
// FIXED UUIDs FOR E2E TESTS
// ============================================================================

export const E2E_TEST_DATA = {
  // Test yacht (from .env.e2e)
  yacht_id: '85fe1119-b04c-41ac-80f1-829d23322598',

  // Test user
  user_id: 'a0d66b00-cce6-49f5-a8d3-5a8c9dd22222',
  user_email: 'x@alex-short.com',

  // Deterministic entity IDs
  fault: {
    id: 'e2e-fault-0001-0000-000000000001',
    title: 'E2E Test Fault - Generator Vibration',
    description: 'High vibration detected on main generator during routine check. Requires immediate inspection.',
    severity: 'high' as const,
    equipment_id: 'e2e-equip-0001-0000-000000000001',
    equipment_name: 'E2E Main Generator #1',
  },
  fault2: {
    id: 'e2e-fault-0002-0000-000000000002',
    title: 'E2E Test Fault - HVAC Pressure Low',
    description: 'HVAC system showing low pressure readings in zone 2.',
    severity: 'medium' as const,
    equipment_id: 'e2e-equip-0002-0000-000000000002',
    equipment_name: 'E2E HVAC Unit #2',
  },

  work_order: {
    id: 'e2e-wo-000001-0000-000000000001',
    title: 'E2E Test Work Order - Generator Maintenance',
    description: 'Scheduled 500-hour maintenance on main generator.',
    status: 'pending' as const,
    priority: 'high' as const,
    wo_type: 'preventive' as const,
    equipment_id: 'e2e-equip-0001-0000-000000000001',
  },
  work_order2: {
    id: 'e2e-wo-000002-0000-000000000002',
    title: 'E2E Test Work Order - HVAC Inspection',
    description: 'Inspect and repair HVAC pressure issues.',
    status: 'in_progress' as const,
    priority: 'medium' as const,
    wo_type: 'corrective' as const,
    equipment_id: 'e2e-equip-0002-0000-000000000002',
  },

  equipment: {
    id: 'e2e-equip-0001-0000-000000000001',
    name: 'E2E Main Generator #1',
    category: 'power_generation',
    manufacturer: 'Caterpillar',
    model: 'C32 ACERT',
    serial_number: 'CAT-E2E-001',
    location: 'Engine Room - Starboard',
    status: 'operational' as const,
  },
  equipment2: {
    id: 'e2e-equip-0002-0000-000000000002',
    name: 'E2E HVAC Unit #2',
    category: 'climate_control',
    manufacturer: 'Marine Air',
    model: 'MA-5000',
    serial_number: 'MA-E2E-002',
    location: 'Main Deck - Port',
    status: 'maintenance' as const,
  },

  part: {
    id: 'e2e-part-0001-0000-000000000001',
    name: 'E2E Oil Filter - Generator',
    part_number: 'CAT-1R0739-E2E',
    description: 'Oil filter for Caterpillar C32 ACERT generator.',
    category: 'filters',
    stock_level: 5,
    min_stock_level: 2,
    unit_cost: 45.99,
    location: 'Parts Store - Bin A12',
  },
  part2: {
    id: 'e2e-part-0002-0000-000000000002',
    name: 'E2E Refrigerant R-410A',
    part_number: 'REF-410A-E2E',
    description: 'Refrigerant for HVAC systems.',
    category: 'consumables',
    stock_level: 8,
    min_stock_level: 4,
    unit_cost: 125.00,
    location: 'Parts Store - Bin C05',
  },

  document: {
    id: 'e2e-doc-00001-0000-000000000001',
    name: 'E2E Generator Service Manual',
    storage_path: 'e2e-test/generator-manual.pdf',
    mime_type: 'application/pdf',
  },
};

// ============================================================================
// SUPABASE CLIENT
// ============================================================================

const TENANT_URL = process.env.TENANT_SUPABASE_URL || 'https://lncnxqmtteiqivxefwqz.supabase.co';
const TENANT_SERVICE_KEY = process.env.TENANT_SUPABASE_SERVICE_ROLE_KEY ||
  'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImxuY254cW10dGVpcWl2eGVmd3F6Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTcyNTk3NjIzNywiZXhwIjoyMDQxNTUyMjM3fQ.HyqSYDi1F-9J-O_k_PLvpOI3uEKMPIHhgd7dWG6oLCA';

function getSupabaseClient() {
  return createClient(TENANT_URL, TENANT_SERVICE_KEY, {
    auth: {
      autoRefreshToken: false,
      persistSession: false,
    },
  });
}

// ============================================================================
// SEEDING FUNCTIONS
// ============================================================================

/**
 * Seed all E2E test data
 * MUST succeed or tests fail - no silent skipping
 */
export async function seedE2ETestData(): Promise<{
  success: boolean;
  errors: string[];
  seeded: string[];
}> {
  const supabase = getSupabaseClient();
  const errors: string[] = [];
  const seeded: string[] = [];
  const yachtId = E2E_TEST_DATA.yacht_id;

  console.log('[E2E Seeder] Starting deterministic test data seeding...');
  console.log('[E2E Seeder] Yacht ID:', yachtId);

  // 1. Seed Equipment (must exist before faults/work orders)
  for (const eq of [E2E_TEST_DATA.equipment, E2E_TEST_DATA.equipment2]) {
    const { error } = await supabase.from('pms_equipment').upsert({
      id: eq.id,
      yacht_id: yachtId,
      name: eq.name,
      category: eq.category,
      manufacturer: eq.manufacturer,
      model: eq.model,
      serial_number: eq.serial_number,
      location: eq.location,
      status: eq.status,
      is_critical: eq.category === 'power_generation',
    }, { onConflict: 'id' });

    if (error) {
      errors.push(`Equipment ${eq.id}: ${error.message}`);
    } else {
      seeded.push(`Equipment: ${eq.name}`);
    }
  }

  // 2. Seed Faults
  for (const fault of [E2E_TEST_DATA.fault, E2E_TEST_DATA.fault2]) {
    const { error } = await supabase.from('pms_faults').upsert({
      id: fault.id,
      yacht_id: yachtId,
      fault_number: `E2E-${fault.id.substring(0, 8)}`,
      title: fault.title,
      description: fault.description,
      severity: fault.severity,
      category: 'mechanical',
      status: 'reported',
      equipment_id: fault.equipment_id,
      reported_by: E2E_TEST_DATA.user_id,
      reported_at: new Date().toISOString(),
    }, { onConflict: 'id' });

    if (error) {
      // Try legacy faults table if pms_faults fails
      const { error: legacyError } = await supabase.from('faults').upsert({
        id: fault.id,
        yacht_id: yachtId,
        fault_code: `E2E-${fault.id.substring(0, 8)}`,
        title: fault.title,
        description: fault.description,
        severity: fault.severity,
        equipment_id: fault.equipment_id,
        reported_by: E2E_TEST_DATA.user_id,
        detected_at: new Date().toISOString(),
      }, { onConflict: 'id' });

      if (legacyError) {
        errors.push(`Fault ${fault.id}: ${error.message} (legacy: ${legacyError.message})`);
      } else {
        seeded.push(`Fault (legacy): ${fault.title}`);
      }
    } else {
      seeded.push(`Fault: ${fault.title}`);
    }
  }

  // 3. Seed Work Orders
  for (const wo of [E2E_TEST_DATA.work_order, E2E_TEST_DATA.work_order2]) {
    const { error } = await supabase.from('pms_work_orders').upsert({
      id: wo.id,
      yacht_id: yachtId,
      wo_number: `E2E-${wo.id.substring(0, 8)}`,
      title: wo.title,
      description: wo.description,
      wo_type: wo.wo_type,
      priority: wo.priority,
      status: wo.status,
      equipment_id: wo.equipment_id,
    }, { onConflict: 'id' });

    if (error) {
      errors.push(`Work Order ${wo.id}: ${error.message}`);
    } else {
      seeded.push(`Work Order: ${wo.title}`);
    }
  }

  // 4. Seed Parts
  for (const part of [E2E_TEST_DATA.part, E2E_TEST_DATA.part2]) {
    const { error } = await supabase.from('pms_parts').upsert({
      id: part.id,
      yacht_id: yachtId,
      name: part.name,
      part_number: part.part_number,
      description: part.description,
      category: part.category,
      quantity_on_hand: part.stock_level,
      minimum_quantity: part.min_stock_level,
      unit_cost: part.unit_cost,
      storage_location: part.location,
    }, { onConflict: 'id' });

    if (error) {
      errors.push(`Part ${part.id}: ${error.message}`);
    } else {
      seeded.push(`Part: ${part.name}`);
    }
  }

  console.log('[E2E Seeder] Seeded:', seeded.length, 'entities');
  console.log('[E2E Seeder] Errors:', errors.length);

  if (errors.length > 0) {
    console.error('[E2E Seeder] Seeding errors:', errors);
  }

  return {
    success: errors.length === 0,
    errors,
    seeded,
  };
}

/**
 * Verify E2E test data exists
 */
export async function verifyE2ETestData(): Promise<{
  success: boolean;
  missing: string[];
}> {
  const supabase = getSupabaseClient();
  const missing: string[] = [];

  // Check equipment
  const { data: equipment } = await supabase
    .from('pms_equipment')
    .select('id')
    .in('id', [E2E_TEST_DATA.equipment.id, E2E_TEST_DATA.equipment2.id]);

  if (!equipment || equipment.length < 2) {
    missing.push('equipment');
  }

  // Check faults (try both tables)
  const { data: faults } = await supabase
    .from('pms_faults')
    .select('id')
    .in('id', [E2E_TEST_DATA.fault.id, E2E_TEST_DATA.fault2.id]);

  if (!faults || faults.length < 2) {
    const { data: legacyFaults } = await supabase
      .from('faults')
      .select('id')
      .in('id', [E2E_TEST_DATA.fault.id, E2E_TEST_DATA.fault2.id]);

    if (!legacyFaults || legacyFaults.length < 2) {
      missing.push('faults');
    }
  }

  // Check work orders
  const { data: workOrders } = await supabase
    .from('pms_work_orders')
    .select('id')
    .in('id', [E2E_TEST_DATA.work_order.id, E2E_TEST_DATA.work_order2.id]);

  if (!workOrders || workOrders.length < 2) {
    missing.push('work_orders');
  }

  // Check parts
  const { data: parts } = await supabase
    .from('pms_parts')
    .select('id')
    .in('id', [E2E_TEST_DATA.part.id, E2E_TEST_DATA.part2.id]);

  if (!parts || parts.length < 2) {
    missing.push('parts');
  }

  return {
    success: missing.length === 0,
    missing,
  };
}

/**
 * Clear E2E test data
 */
export async function clearE2ETestData(): Promise<void> {
  const supabase = getSupabaseClient();

  // Delete in reverse order of dependencies
  await supabase.from('pms_work_orders').delete().in('id', [
    E2E_TEST_DATA.work_order.id,
    E2E_TEST_DATA.work_order2.id,
  ]);

  await supabase.from('pms_faults').delete().in('id', [
    E2E_TEST_DATA.fault.id,
    E2E_TEST_DATA.fault2.id,
  ]);

  await supabase.from('faults').delete().in('id', [
    E2E_TEST_DATA.fault.id,
    E2E_TEST_DATA.fault2.id,
  ]);

  await supabase.from('pms_parts').delete().in('id', [
    E2E_TEST_DATA.part.id,
    E2E_TEST_DATA.part2.id,
  ]);

  await supabase.from('pms_equipment').delete().in('id', [
    E2E_TEST_DATA.equipment.id,
    E2E_TEST_DATA.equipment2.id,
  ]);

  console.log('[E2E Seeder] Test data cleared');
}

// Export for CLI usage
export default {
  E2E_TEST_DATA,
  seedE2ETestData,
  verifyE2ETestData,
  clearE2ETestData,
};
