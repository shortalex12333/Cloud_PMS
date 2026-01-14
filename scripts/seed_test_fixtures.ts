/**
 * Seed Test Fixtures for E2E Tests
 *
 * Creates 15 variations of each entity type required by skipped tests:
 * - Equipment (for update_equipment_status)
 * - Work Orders (for add_note_to_work_order)
 * - Parts (for shopping_list tests)
 * - Documents (for delete_document)
 * - Shopping Items (for delete_shopping_item)
 *
 * All data respects:
 * - DB constraints (NOT NULL, CHECK, etc.)
 * - Foreign keys (yacht_id, user_id, part_id, etc.)
 * - RLS policies (yacht_id scoping)
 * - Valid UUIDs
 */

import * as dotenv from 'dotenv';
import { createClient } from '@supabase/supabase-js';

dotenv.config({ path: '.env.e2e.local' });

const TENANT_URL = process.env.TENANT_SUPABASE_URL!;
const TENANT_KEY = process.env.TENANT_SUPABASE_SERVICE_ROLE_KEY!;
const TEST_YACHT_ID = process.env.TEST_USER_YACHT_ID || '85fe1119-b04c-41ac-80f1-829d23322598';
const TEST_USER_ID = process.env.TEST_USER_ID || 'a0d66b00-cce6-49f5-a8d3-5a8c9dd22222';

if (!TENANT_URL || !TENANT_KEY) {
  console.error('Missing TENANT_SUPABASE_URL or TENANT_SUPABASE_SERVICE_ROLE_KEY');
  process.exit(1);
}

const tenant = createClient(TENANT_URL, TENANT_KEY, {
  auth: { autoRefreshToken: false, persistSession: false },
});

// Valid enum values from actual schema (queried from DB)
const EQUIPMENT_CRITICALITIES = ['critical', 'high', 'medium', 'low'];
const EQUIPMENT_SYSTEM_TYPES = ['electrical', 'mechanical', 'hydraulic', 'navigation', 'safety', 'hvac'];
const WORK_ORDER_STATUSES = ['planned', 'completed', 'cancelled']; // Actual DB enums
const WORK_ORDER_PRIORITIES = ['routine', 'critical']; // Actual DB enums
const WORK_ORDER_TYPES = ['scheduled']; // Actual DB enum
const WORK_ORDER_TYPE_CATEGORIES = ['planned']; // Actual DB enum
const PART_UNITS = ['ea']; // Only valid unit in DB
const SHOPPING_ITEM_STATUSES = ['candidate', 'under_review', 'approved', 'ordered', 'partially_fulfilled', 'installed'];
const SHOPPING_SOURCE_TYPES = ['manual_add', 'inventory_low', 'work_order_usage'];
const URGENCY_LEVELS = ['normal', 'low', 'high']; // null also valid but excluded

interface SeedResult {
  entity: string;
  created: number;
  failed: number;
  ids: string[];
  errors: string[];
}

/**
 * Ensure test user exists in auth_users_profiles table
 * Required for FK constraints on pms_handover.added_by, pms_work_order_notes.created_by, etc.
 */
async function ensureTestUser(): Promise<SeedResult> {
  const result: SeedResult = { entity: 'auth_users_profiles', created: 0, failed: 0, ids: [], errors: [] };
  const testEmail = process.env.TEST_USER_EMAIL || 'test@celesteos.com';

  // Check if user already exists in auth_users_profiles by ID
  const { data: existingById } = await tenant
    .from('auth_users_profiles')
    .select('id, email')
    .eq('id', TEST_USER_ID)
    .single();

  if (existingById) {
    console.log(`  Test user already exists in auth_users_profiles: ${TEST_USER_ID}`);
    result.ids.push(TEST_USER_ID);
    return result;
  }

  // Check if user exists with our test email but different ID
  const { data: existingByEmail } = await tenant
    .from('auth_users_profiles')
    .select('id, email')
    .eq('email', testEmail)
    .single();

  if (existingByEmail && existingByEmail.id !== TEST_USER_ID) {
    // Delete the conflicting record so we can insert with correct ID
    console.log(`  Removing conflicting user profile with email ${testEmail} (id: ${existingByEmail.id})`);
    await tenant
      .from('auth_users_profiles')
      .delete()
      .eq('id', existingByEmail.id);
  }

  // Insert test user into auth_users_profiles
  const { data, error } = await tenant
    .from('auth_users_profiles')
    .insert({
      id: TEST_USER_ID,
      yacht_id: TEST_YACHT_ID,
      email: testEmail,
      name: 'Test User',
      is_active: true,
    })
    .select('id')
    .single();

  if (error) {
    result.failed++;
    result.errors.push(`auth_users_profiles: ${error.message}`);
    console.log(`  Warning: Could not create test user profile: ${error.message}`);
  } else {
    result.created++;
    result.ids.push(data.id);
    console.log(`  Created test user profile: ${data.id}`);
  }

  return result;
}

async function seedEquipment(): Promise<SeedResult> {
  const result: SeedResult = { entity: 'equipment', created: 0, failed: 0, ids: [], errors: [] };

  const equipmentData = Array.from({ length: 15 }, (_, i) => ({
    yacht_id: TEST_YACHT_ID,
    name: `Test Equipment ${i + 1} - ${['Generator', 'Pump', 'Motor', 'Compressor', 'Filter'][i % 5]} ${Date.now()}`,
    code: `TEST-EQ-${Date.now()}-${String(i + 1).padStart(3, '0')}`,
    description: `E2E test equipment variant ${i + 1}. System: ${EQUIPMENT_SYSTEM_TYPES[i % 6]}`,
    criticality: EQUIPMENT_CRITICALITIES[i % 4],
    system_type: EQUIPMENT_SYSTEM_TYPES[i % 6],
    location: `Deck ${(i % 3) + 1}, Compartment ${String.fromCharCode(65 + (i % 5))}`,
    manufacturer: ['Caterpillar', 'MTU', 'Kohler', 'ABB', 'Siemens'][i % 5],
    model: `Model-${1000 + i}`,
    serial_number: `SN-TEST-${Date.now()}-${i}`,
    installed_date: new Date(2020 + (i % 5), i % 12, (i % 28) + 1).toISOString().split('T')[0],
    attention_flag: i % 3 === 0, // Every 3rd has attention
    attention_reason: i % 3 === 0 ? `Test attention reason ${i + 1}` : null,
    metadata: { test: true, variant: i + 1 },
  }));

  for (const equip of equipmentData) {
    const { data, error } = await tenant
      .from('pms_equipment')
      .insert(equip)
      .select('id')
      .single();

    if (error) {
      result.failed++;
      result.errors.push(`Equipment: ${error.message}`);
    } else {
      result.created++;
      result.ids.push(data.id);
    }
  }

  return result;
}

async function seedWorkOrders(): Promise<SeedResult> {
  const result: SeedResult = { entity: 'work_orders', created: 0, failed: 0, ids: [], errors: [] };

  // First get an equipment ID for FK
  const { data: equipment } = await tenant
    .from('pms_equipment')
    .select('id')
    .eq('yacht_id', TEST_YACHT_ID)
    .limit(1)
    .single();

  const equipmentId = equipment?.id;

  const workOrderData = Array.from({ length: 15 }, (_, i) => ({
    yacht_id: TEST_YACHT_ID,
    title: `Test Work Order ${i + 1} - ${['Engine', 'Generator', 'HVAC', 'Navigation', 'Hull'][i % 5]} Maintenance`,
    description: `E2E test work order variant ${i + 1}. Priority: ${WORK_ORDER_PRIORITIES[i % 2]}`,
    wo_number: `WO-TEST-${Date.now()}-${String(i + 1).padStart(3, '0')}`,
    status: WORK_ORDER_STATUSES[i % 3],
    type: WORK_ORDER_TYPES[0], // Only 'scheduled' is valid
    work_order_type: WORK_ORDER_TYPE_CATEGORIES[0], // Only 'planned' is valid
    priority: WORK_ORDER_PRIORITIES[i % 2],
    equipment_id: equipmentId || null,
    created_by: TEST_USER_ID,
    due_date: new Date(Date.now() + (i + 1) * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
    metadata: { test: true, variant: i + 1 },
  }));

  for (const wo of workOrderData) {
    const { data, error } = await tenant
      .from('pms_work_orders')
      .insert(wo)
      .select('id')
      .single();

    if (error) {
      result.failed++;
      result.errors.push(`WorkOrder: ${error.message}`);
    } else {
      result.created++;
      result.ids.push(data.id);
    }
  }

  return result;
}

async function seedParts(): Promise<SeedResult> {
  const result: SeedResult = { entity: 'parts', created: 0, failed: 0, ids: [], errors: [] };

  const partData = Array.from({ length: 15 }, (_, i) => ({
    yacht_id: TEST_YACHT_ID,
    name: `Test Part ${i + 1} - ${['Filter', 'Gasket', 'Bearing', 'Seal', 'Valve'][i % 5]}`,
    part_number: `PN-TEST-${Date.now()}-${String(i + 1).padStart(3, '0')}`,
    description: `E2E test part variant ${i + 1}`,
    category: ['Mechanical', 'Electrical', 'Hydraulic', 'Pneumatic', 'Safety'][i % 5],
    unit: 'ea', // Only valid unit in DB
    minimum_quantity: (i % 5) + 1,
    quantity_on_hand: (i % 10) + 5,
    location: `Storage ${String.fromCharCode(65 + (i % 5))}-${(i % 10) + 1}`,
    manufacturer: ['Caterpillar', 'MTU', 'Parker', 'SKF', 'Gates'][i % 5],
    model_compatibility: [`Model-${1000 + i}`, `Model-${2000 + i}`],
    metadata: { test: true, variant: i + 1, unit_cost: (10 + i * 5) * 100 },
  }));

  for (const part of partData) {
    const { data, error } = await tenant
      .from('pms_parts')
      .insert(part)
      .select('id')
      .single();

    if (error) {
      result.failed++;
      result.errors.push(`Part: ${error.message}`);
    } else {
      result.created++;
      result.ids.push(data.id);
    }
  }

  return result;
}

async function seedDocuments(): Promise<SeedResult> {
  const result: SeedResult = { entity: 'documents', created: 0, failed: 0, ids: [], errors: [] };

  const docData = Array.from({ length: 15 }, (_, i) => ({
    yacht_id: TEST_YACHT_ID,
    filename: `test_document_${i + 1}_${Date.now()}.pdf`,
    content_type: ['application/pdf', 'image/png', 'image/jpeg', 'application/msword', 'text/plain'][i % 5],
    source: ['oem', 'internal', 'regulatory', 'vendor', 'crew'][i % 5],
    doc_type: ['manual', 'certificate', 'report', 'checklist', 'guide'][i % 5],
    oem: ['Caterpillar', 'MTU', 'Kohler', 'ABB', 'Siemens'][i % 5],
    model: `Model-${1000 + i}`,
    system_type: EQUIPMENT_SYSTEM_TYPES[i % 6],
    size_bytes: (100 + i * 50) * 1024,
    storage_path: `test/${TEST_YACHT_ID}/documents/test_doc_${i + 1}.pdf`,
    original_path: `/uploads/test_doc_${i + 1}.pdf`,
    tags: [`test`, `variant-${i + 1}`, ['engine', 'generator', 'hvac', 'navigation', 'safety'][i % 5]],
    metadata: { test: true, variant: i + 1 },
  }));

  for (const doc of docData) {
    const { data, error } = await tenant
      .from('documents')
      .insert(doc)
      .select('id')
      .single();

    if (error) {
      result.failed++;
      result.errors.push(`Document: ${error.message}`);
    } else {
      result.created++;
      result.ids.push(data.id);
    }
  }

  return result;
}

async function seedShoppingItems(): Promise<SeedResult> {
  const result: SeedResult = { entity: 'shopping_items', created: 0, failed: 0, ids: [], errors: [] };

  // First get part IDs for FK
  const { data: parts } = await tenant
    .from('pms_parts')
    .select('id, name, part_number, manufacturer')
    .eq('yacht_id', TEST_YACHT_ID)
    .limit(15);

  if (!parts || parts.length === 0) {
    result.errors.push('No parts available for shopping items - seed parts first');
    return result;
  }

  // Get a valid user ID from existing shopping items
  const { data: existingItems } = await tenant
    .from('pms_shopping_list_items')
    .select('created_by')
    .not('created_by', 'is', null)
    .limit(1);

  const validUserId = existingItems?.[0]?.created_by || null;

  const shoppingData = Array.from({ length: 15 }, (_, i) => {
    const part = parts[i % parts.length];
    return {
      yacht_id: TEST_YACHT_ID,
      part_id: part.id,
      part_name: part.name,
      part_number: part.part_number,
      manufacturer: part.manufacturer,
      is_candidate_part: false,
      quantity_requested: (i % 10) + 1,
      unit: 'ea',
      status: SHOPPING_ITEM_STATUSES[i % 6],
      urgency: URGENCY_LEVELS[i % 3],
      source_type: SHOPPING_SOURCE_TYPES[i % 3],
      source_notes: `E2E test shopping item ${i + 1}`,
      created_by: validUserId, // Use valid FK reference
      required_by_date: new Date(Date.now() + (i + 1) * 7 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
      metadata: { test: true, variant: i + 1 },
    };
  });

  for (const item of shoppingData) {
    const { data, error } = await tenant
      .from('pms_shopping_list_items')
      .insert(item)
      .select('id')
      .single();

    if (error) {
      result.failed++;
      result.errors.push(`ShoppingItem: ${error.message}`);
    } else {
      result.created++;
      result.ids.push(data.id);
    }
  }

  return result;
}

async function verifyData(): Promise<void> {
  console.log('\n=== VERIFICATION ===');

  const tables = [
    { name: 'pms_equipment', label: 'Equipment' },
    { name: 'pms_work_orders', label: 'Work Orders' },
    { name: 'pms_parts', label: 'Parts' },
    { name: 'documents', label: 'Documents' },
    { name: 'pms_shopping_list_items', label: 'Shopping Items' },
  ];

  for (const table of tables) {
    const { count, error } = await tenant
      .from(table.name)
      .select('*', { count: 'exact', head: true })
      .eq('yacht_id', TEST_YACHT_ID);

    if (error) {
      console.log(`  ${table.label}: ERROR - ${error.message}`);
    } else {
      console.log(`  ${table.label}: ${count} rows`);
    }
  }
}

async function main() {
  console.log('===========================================');
  console.log('  SEEDING TEST FIXTURES FOR E2E TESTS');
  console.log('===========================================');
  console.log(`Yacht ID: ${TEST_YACHT_ID}`);
  console.log(`User ID: ${TEST_USER_ID}`);
  console.log('');

  const results: SeedResult[] = [];

  // First ensure test user exists (required for FK constraints)
  console.log('0. Ensuring test user exists in users table...');
  results.push(await ensureTestUser());

  // Seed in order (respecting FK dependencies)
  console.log('1. Seeding Equipment (15 variations)...');
  results.push(await seedEquipment());

  console.log('2. Seeding Work Orders (15 variations)...');
  results.push(await seedWorkOrders());

  console.log('3. Seeding Parts (15 variations)...');
  results.push(await seedParts());

  console.log('4. Seeding Documents (15 variations)...');
  results.push(await seedDocuments());

  console.log('5. Seeding Shopping Items (15 variations)...');
  results.push(await seedShoppingItems());

  // Summary
  console.log('\n=== RESULTS ===');
  let totalCreated = 0;
  let totalFailed = 0;

  for (const r of results) {
    console.log(`${r.entity}: ${r.created} created, ${r.failed} failed`);
    if (r.errors.length > 0) {
      r.errors.slice(0, 3).forEach((e) => console.log(`  - ${e}`));
      if (r.errors.length > 3) console.log(`  ... and ${r.errors.length - 3} more errors`);
    }
    totalCreated += r.created;
    totalFailed += r.failed;
  }

  console.log(`\nTOTAL: ${totalCreated} created, ${totalFailed} failed`);

  await verifyData();

  // Write IDs to env file for tests
  const envContent = results.map((r) => {
    const key = r.entity.toUpperCase().replace(/_/g, '_');
    return `TEST_${key}_IDS=${r.ids.slice(0, 5).join(',')}`;
  }).join('\n');

  console.log('\n=== TEST IDs (first 5 of each) ===');
  console.log(envContent);
}

main().catch(console.error);
