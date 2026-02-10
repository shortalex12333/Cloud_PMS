/**
 * Seed Test Data for E2E Tests
 *
 * Seeds parts, equipment, and work orders into the tenant database
 * for yacht 85fe1119-b04c-41ac-80f1-829d23322598
 */

import { createClient } from '@supabase/supabase-js';
import * as dotenv from 'dotenv';
import { resolve } from 'path';

// Load test environment
dotenv.config({ path: resolve(process.cwd(), '.env.e2e.local') });

const YACHT_ID = '85fe1119-b04c-41ac-80f1-829d23322598';

const tenantUrl = process.env.TENANT_SUPABASE_URL!;
const tenantKey = process.env.TENANT_SUPABASE_SERVICE_KEY!;

if (!tenantUrl || !tenantKey) {
  console.error('❌ Missing TENANT_SUPABASE_URL or TENANT_SUPABASE_SERVICE_KEY');
  process.exit(1);
}

const supabase = createClient(tenantUrl, tenantKey);

async function seedParts() {
  console.log('\n📦 Seeding Parts...');

  const parts = [
    // Fuel Filters
    { part_name: 'Fuel Filter - Primary', part_number: 'FF-001', manufacturer: 'Mann-Filter', category: 'Filters', description: 'Primary fuel filter for main engine', location: 'Engine Room', on_hand: 15, min_stock: 5, max_stock: 30, unit_cost: 45.99, unit: 'EA' },
    { part_name: 'Fuel Filter - Secondary', part_number: 'FF-002', manufacturer: 'Fleetguard', category: 'Filters', description: 'Secondary fuel filter for main engine', location: 'Engine Room', on_hand: 12, min_stock: 5, max_stock: 25, unit_cost: 38.50, unit: 'EA' },
    { part_name: 'Fuel Water Separator Filter', part_number: 'FF-WS-003', manufacturer: 'Racor', category: 'Filters', description: 'Fuel water separator cartridge', location: 'Engine Room', on_hand: 8, min_stock: 3, max_stock: 20, unit_cost: 125.00, unit: 'EA' },
    { part_name: 'Fuel Filter - Generator', part_number: 'FF-GEN-004', manufacturer: 'Caterpillar', category: 'Filters', description: 'Fuel filter for auxiliary generator', location: 'Generator Room', on_hand: 6, min_stock: 2, max_stock: 15, unit_cost: 52.75, unit: 'EA' },
    { part_name: 'Fuel Pre-Filter Element', part_number: 'FF-PRE-005', manufacturer: 'Baldwin', category: 'Filters', description: 'Pre-filter element for fuel system', location: 'Engine Room', on_hand: 10, min_stock: 4, max_stock: 20, unit_cost: 28.99, unit: 'EA' },
    { part_name: 'Fuel Filter Housing Gasket', part_number: 'FF-GSKT-006', manufacturer: 'OEM', category: 'Gaskets', description: 'O-ring gasket for fuel filter housing', location: 'Engine Room', on_hand: 20, min_stock: 10, max_stock: 50, unit_cost: 3.25, unit: 'EA' },
    { part_name: 'Fuel Filter Wrench', part_number: 'FF-TOOL-007', manufacturer: 'Generic', category: 'Tools', description: 'Fuel filter removal wrench', location: 'Engine Room', on_hand: 2, min_stock: 1, max_stock: 3, unit_cost: 18.50, unit: 'EA' },
    { part_name: 'Diesel Fuel Filter - High Flow', part_number: 'FF-HF-008', manufacturer: 'Donaldson', category: 'Filters', description: 'High flow fuel filter for diesel', location: 'Engine Room', on_hand: 5, min_stock: 2, max_stock: 12, unit_cost: 89.99, unit: 'EA' },
    { part_name: 'Fuel Filter - Emergency Stock', part_number: 'FF-EMERG-009', manufacturer: 'Various', category: 'Filters', description: 'Emergency spare fuel filter', location: 'Emergency Locker', on_hand: 3, min_stock: 2, max_stock: 8, unit_cost: 55.00, unit: 'EA' },
    { part_name: 'Fuel Filter Test Kit', part_number: 'FF-TEST-010', manufacturer: 'Test Equipment Inc', category: 'Testing', description: 'Fuel contamination test kit', location: 'Engine Room', on_hand: 1, min_stock: 1, max_stock: 2, unit_cost: 145.00, unit: 'KIT' },

    // Additional variety
    { part_name: 'Engine Oil Filter', part_number: 'OF-001', manufacturer: 'Mann-Filter', category: 'Filters', description: 'Oil filter for main engine', location: 'Engine Room', on_hand: 8, min_stock: 4, max_stock: 20, unit_cost: 32.50, unit: 'EA' },
    { part_name: 'Air Filter Element', part_number: 'AF-001', manufacturer: 'Donaldson', category: 'Filters', description: 'Air filter for engine intake', location: 'Engine Room', on_hand: 6, min_stock: 3, max_stock: 15, unit_cost: 68.75, unit: 'EA' },
    { part_name: 'Hydraulic Filter', part_number: 'HF-001', manufacturer: 'Parker', category: 'Filters', description: 'Hydraulic system filter', location: 'Hydraulic Room', on_hand: 4, min_stock: 2, max_stock: 10, unit_cost: 95.00, unit: 'EA' },
    { part_name: 'Coolant Hose', part_number: 'CH-001', manufacturer: 'Gates', category: 'Hoses', description: 'Coolant hose for engine', location: 'Engine Room', on_hand: 3, min_stock: 1, max_stock: 5, unit_cost: 45.00, unit: 'EA' },
    { part_name: 'V-Belt', part_number: 'VB-001', manufacturer: 'Goodyear', category: 'Belts', description: 'V-belt for alternator', location: 'Engine Room', on_hand: 5, min_stock: 2, max_stock: 10, unit_cost: 25.50, unit: 'EA' },

    // Zero stock (edge cases)
    { part_name: 'Fuel Filter - Out of Stock', part_number: 'FF-OOS-001', manufacturer: 'Mann-Filter', category: 'Filters', description: 'Out of stock fuel filter', location: 'Engine Room', on_hand: 0, min_stock: 5, max_stock: 30, unit_cost: 45.99, unit: 'EA' },
    { part_name: 'Emergency Fuel Filter - Low Stock', part_number: 'FF-LOW-002', manufacturer: 'Fleetguard', category: 'Filters', description: 'Low stock emergency filter', location: 'Emergency Locker', on_hand: 1, min_stock: 5, max_stock: 25, unit_cost: 125.00, unit: 'EA' },
  ];

  // Add yacht_id to all parts
  const partsWithYachtId = parts.map(part => ({
    ...part,
    yacht_id: YACHT_ID,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  }));

  const { data, error } = await supabase
    .from('parts')
    .upsert(partsWithYachtId, {
      onConflict: 'part_number,yacht_id',
      ignoreDuplicates: false,
    });

  if (error) {
    console.error('❌ Error seeding parts:', error.message);
    return false;
  }

  console.log(`✅ Seeded ${parts.length} parts`);
  return true;
}

async function seedEquipment() {
  console.log('\n🔧 Seeding Equipment...');

  const equipment = [
    { equipment_name: 'Main Engine - Port', equipment_type: 'Engine', manufacturer: 'Caterpillar', model: 'C32 ACERT', serial_number: 'CAT-PE-001', location: 'Engine Room', installation_date: '2020-01-15', status: 'operational' },
    { equipment_name: 'Main Engine - Starboard', equipment_type: 'Engine', manufacturer: 'Caterpillar', model: 'C32 ACERT', serial_number: 'CAT-SE-001', location: 'Engine Room', installation_date: '2020-01-15', status: 'operational' },
    { equipment_name: 'Auxiliary Generator', equipment_type: 'Generator', manufacturer: 'Northern Lights', model: 'M1264', serial_number: 'NL-GEN-001', location: 'Generator Room', installation_date: '2020-02-10', status: 'operational' },
    { equipment_name: 'Fuel Transfer Pump', equipment_type: 'Pump', manufacturer: 'Jabsco', model: 'FTP-100', serial_number: 'JAB-FTP-001', location: 'Engine Room', installation_date: '2020-03-05', status: 'operational' },
  ];

  const equipmentWithYachtId = equipment.map(eq => ({
    ...eq,
    yacht_id: YACHT_ID,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  }));

  const { data, error } = await supabase
    .from('equipment')
    .upsert(equipmentWithYachtId, {
      onConflict: 'serial_number,yacht_id',
      ignoreDuplicates: false,
    });

  if (error) {
    console.error('❌ Error seeding equipment:', error.message);
    return false;
  }

  console.log(`✅ Seeded ${equipment.length} equipment items`);
  return true;
}

async function validateSeeding() {
  console.log('\n🔍 Validating Seeded Data...');

  // Count parts
  const { data: parts, error: partsError } = await supabase
    .from('parts')
    .select('*', { count: 'exact', head: true })
    .eq('yacht_id', YACHT_ID);

  if (partsError) {
    console.error('❌ Error validating parts:', partsError.message);
    return;
  }

  // Count fuel filter parts
  const { data: fuelFilters, count: fuelFilterCount } = await supabase
    .from('parts')
    .select('*', { count: 'exact', head: true })
    .eq('yacht_id', YACHT_ID)
    .or('part_name.ilike.%fuel%,part_name.ilike.%filter%');

  console.log(`✅ Total parts for yacht: ${(parts as any)?.count || 0}`);
  console.log(`✅ Fuel filter parts: ${fuelFilterCount || 0}`);

  // Show sample parts
  const { data: sampleParts } = await supabase
    .from('parts')
    .select('part_name, part_number, on_hand')
    .eq('yacht_id', YACHT_ID)
    .or('part_name.ilike.%fuel%,part_name.ilike.%filter%')
    .limit(5);

  if (sampleParts && sampleParts.length > 0) {
    console.log('\n📋 Sample Parts:');
    sampleParts.forEach(part => {
      console.log(`  - ${part.part_name} (${part.part_number}): Stock ${part.on_hand}`);
    });
  }
}

async function main() {
  console.log('========================================');
  console.log('Seeding Test Data for E2E Tests');
  console.log('========================================');
  console.log(`Yacht ID: ${YACHT_ID}`);
  console.log(`Tenant URL: ${tenantUrl}`);

  const partsSuccess = await seedParts();
  const equipmentSuccess = await seedEquipment();

  if (partsSuccess && equipmentSuccess) {
    await validateSeeding();

    console.log('\n========================================');
    console.log('✅ All Test Data Seeded Successfully!');
    console.log('========================================');
    console.log('\nNext steps:');
    console.log('1. Run validation: tests/scripts/validate-local-setup.sh');
    console.log('2. Run E2E tests: npm run test:e2e -- tests/e2e/inventory-lens-6hr-live-test.spec.ts');
    process.exit(0);
  } else {
    console.log('\n❌ Seeding failed - see errors above');
    process.exit(1);
  }
}

main().catch(err => {
  console.error('Fatal error:', err);
  process.exit(1);
});
