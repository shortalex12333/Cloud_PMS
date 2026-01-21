/**
 * Seed Test Data Script
 *
 * Creates test data for CelesteOS verification.
 * Uses correct table names from actual tenant database schema.
 */

const { createClient } = require('@supabase/supabase-js');
const fs = require('fs');

const TENANT_SUPABASE_URL = 'https://vzsohavtuotocgrfkfyd.supabase.co';
const TENANT_SERVICE_KEY = process.env.TENANT_SUPABASE_SERVICE_ROLE_KEY;

if (!TENANT_SERVICE_KEY) {
  console.log('ERROR: TENANT_SUPABASE_SERVICE_ROLE_KEY not set');
  process.exit(1);
}

const supabase = createClient(TENANT_SUPABASE_URL, TENANT_SERVICE_KEY);

// Test context
const YACHT_ID = '85fe1119-b04c-41ac-80f1-829d23322598';
const USER_ID = 'a35cad0b-02ff-4287-b6e4-17c96fa6a424';

// Sample equipment IDs (from existing data)
const EQUIPMENT_IDS = [
  'e1000001-0001-4001-8001-000000000004', // Generator 2
  'e1000001-0001-4001-8001-000000000006', // HVAC Chiller
  'e1000001-0001-4001-8001-000000000007', // Bow Thruster
  'e1000001-0001-4001-8001-000000000008', // Stern Thruster
  'e1000001-0001-4001-8001-000000000009', // Radar System
];

async function seedFaults() {
  console.log('\n=== Seeding Faults (pms_faults) ===');

  // Schema: id, yacht_id, equipment_id, fault_code, title, description, severity, detected_at, status, metadata
  const faults = [
    {
      yacht_id: YACHT_ID,
      equipment_id: EQUIPMENT_IDS[0],
      fault_code: 'GEN-VIB-001',
      title: 'Generator Vibration',
      description: 'Generator 2 showing abnormal vibration readings during high load',
      severity: 'medium',
      status: 'open',
      detected_at: new Date().toISOString(),
      metadata: { reported_by: USER_ID },
    },
    {
      yacht_id: YACHT_ID,
      equipment_id: EQUIPMENT_IDS[1],
      fault_code: 'HVAC-PRES-001',
      title: 'HVAC Pressure Low',
      description: 'HVAC refrigerant pressure dropping below normal',
      severity: 'high',
      status: 'open',
      detected_at: new Date().toISOString(),
      metadata: { reported_by: USER_ID },
    },
    {
      yacht_id: YACHT_ID,
      equipment_id: EQUIPMENT_IDS[2],
      fault_code: 'THR-RESP-001',
      title: 'Thruster Response Delay',
      description: 'Bow thruster response time delayed by 2 seconds',
      severity: 'low',
      status: 'acknowledged',
      detected_at: new Date(Date.now() - 86400000).toISOString(),
      metadata: { reported_by: USER_ID },
    },
  ];

  const { data, error } = await supabase.from('pms_faults').insert(faults).select();

  if (error) {
    console.log('  Error seeding faults:', error.message);
    console.log('  Hint:', error.hint || 'None');
  } else {
    console.log(`  Created ${data?.length} faults`);
  }

  return data;
}

async function seedParts() {
  console.log('\n=== Seeding Parts (pms_parts) ===');

  // Schema: id, yacht_id, name, part_number, manufacturer, description, category, quantity_on_hand, minimum_quantity, unit, location
  const parts = [
    { yacht_id: YACHT_ID, name: 'Oil Filter - Generator', part_number: 'GEN-OF-001', manufacturer: 'Caterpillar', description: 'Oil filter for generator', category: 'Engine', quantity_on_hand: 5, minimum_quantity: 2, unit: 'ea', location: 'Engine Room Store A' },
    { yacht_id: YACHT_ID, name: 'Fuel Filter - Generator', part_number: 'GEN-FF-001', manufacturer: 'Caterpillar', description: 'Fuel filter for generator', category: 'Engine', quantity_on_hand: 3, minimum_quantity: 1, unit: 'ea', location: 'Engine Room Store A' },
    { yacht_id: YACHT_ID, name: 'R410A Refrigerant', part_number: 'HVAC-REF-410', manufacturer: 'Carrier', description: 'HVAC refrigerant', category: 'HVAC', quantity_on_hand: 2, minimum_quantity: 1, unit: 'can', location: 'HVAC Store' },
    { yacht_id: YACHT_ID, name: 'Compressor Belt', part_number: 'HVAC-CB-001', manufacturer: 'Carrier', description: 'Belt for HVAC compressor', category: 'HVAC', quantity_on_hand: 1, minimum_quantity: 1, unit: 'ea', location: 'HVAC Store' },
    { yacht_id: YACHT_ID, name: 'Hydraulic Seal Kit - Thruster', part_number: 'THR-HSK-001', manufacturer: 'Vetus', description: 'Hydraulic seal kit for thrusters', category: 'Deck', quantity_on_hand: 2, minimum_quantity: 1, unit: 'kit', location: 'Deck Store' },
  ];

  const { data, error } = await supabase.from('pms_parts').insert(parts).select();

  if (error) {
    console.log('  Error seeding parts:', error.message);
    console.log('  Hint:', error.hint || 'None');
  } else {
    console.log(`  Created ${data?.length} parts`);
  }

  return data;
}

async function seedNotes() {
  console.log('\n=== Seeding Notes (pms_notes) ===');

  // Schema: id, yacht_id, equipment_id, work_order_id, fault_id, text, note_type, created_by, metadata
  const notes = [
    { yacht_id: YACHT_ID, equipment_id: EQUIPMENT_IDS[0], text: 'Last oil change completed on 2026-01-15. Next due at 500 hours.', note_type: 'general', created_by: USER_ID },
    { yacht_id: YACHT_ID, equipment_id: EQUIPMENT_IDS[1], text: 'Refrigerant topped up. Monitoring for leaks over next 48 hours.', note_type: 'general', created_by: USER_ID },
    { yacht_id: YACHT_ID, equipment_id: EQUIPMENT_IDS[2], text: 'Bow thruster tested successfully at dock. Response time within spec.', note_type: 'general', created_by: USER_ID },
    { yacht_id: YACHT_ID, equipment_id: EQUIPMENT_IDS[3], text: 'Hydraulic seal replacement scheduled for next yard period.', note_type: 'general', created_by: USER_ID },
    { yacht_id: YACHT_ID, equipment_id: EQUIPMENT_IDS[4], text: 'Radar firmware updated to v2.3.1. Display issue resolved.', note_type: 'general', created_by: USER_ID },
  ];

  const { data, error } = await supabase.from('pms_notes').insert(notes).select();

  if (error) {
    console.log('  Error seeding notes:', error.message);
    console.log('  Hint:', error.hint || 'None');
  } else {
    console.log(`  Created ${data?.length} notes`);
  }

  return data;
}

async function seedShoppingItems() {
  console.log('\n=== Seeding Shopping Items (pms_shopping_list_items) ===');

  // Check actual schema first
  const { data: sample, error: sampleErr } = await supabase
    .from('pms_shopping_list_items')
    .select('*')
    .limit(1);

  if (sampleErr) {
    console.log('  Error checking schema:', sampleErr.message);
    return null;
  }

  console.log('  Sample row keys:', sample?.[0] ? Object.keys(sample[0]) : 'No rows');

  // Try minimal insert based on expected schema
  const items = [
    {
      yacht_id: YACHT_ID,
      part_id: null, // Will need actual part_id if required
      quantity: 5,
      notes: 'Order 5x Oil Filters for Generator 2',
      priority: 'high',
    },
  ];

  const { data, error } = await supabase.from('pms_shopping_list_items').insert(items).select();

  if (error) {
    console.log('  Error seeding shopping items:', error.message);
    console.log('  Hint:', error.hint || 'None');
  } else {
    console.log(`  Created ${data?.length} shopping items`);
  }

  return data;
}

async function main() {
  console.log('=== CelesteOS Test Data Seed Script ===');
  console.log(`Yacht ID: ${YACHT_ID}`);
  console.log(`User ID: ${USER_ID}`);

  const results = {
    faults: await seedFaults(),
    parts: await seedParts(),
    notes: await seedNotes(),
    shopping_items: await seedShoppingItems(),
  };

  console.log('\n=== Seed Complete ===');
  console.log('Results:', JSON.stringify({
    faults: results.faults?.length || 0,
    parts: results.parts?.length || 0,
    notes: results.notes?.length || 0,
    shopping_items: results.shopping_items?.length || 0,
  }, null, 2));

  // Write evidence
  try {
    fs.writeFileSync(
      '/Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS/verification_handoff/evidence/SEED_results.json',
      JSON.stringify(results, null, 2)
    );
    console.log('\nEvidence written to SEED_results.json');
  } catch (e) {
    console.log('Could not write evidence file:', e.message);
  }
}

main();
