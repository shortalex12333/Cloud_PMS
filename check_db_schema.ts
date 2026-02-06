/**
 * Check actual tenant DB schema for handover_items table
 */

import { createClient } from '@supabase/supabase-js';

const TENANT_URL = 'https://vzsohavtuotocgrfkfyd.supabase.co';
const TENANT_ANON_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ6c29oYXZ0dW90b2NncmZrZnlkIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjM1OTI4NzUsImV4cCI6MjA3OTE2ODg3NX0.JhJLvLSfLD3OtPDxTgHqgF8dNaZk8ius62jKN68E4WE';

const client = createClient(TENANT_URL, TENANT_ANON_KEY);

console.log('='.repeat(80));
console.log('TENANT DATABASE SCHEMA CHECK');
console.log('='.repeat(80));
console.log('');

async function checkSchema() {
  try {
    // Check which handover tables exist
    console.log('1. Checking which handover tables exist...');
    console.log('');

    const tables = ['pms_handover', 'handover_items', 'handover_exports'];

    for (const table of tables) {
      try {
        const { count, error } = await client.from(table).select('*', { count: 'exact', head: true });
        if (error) {
          console.log(`   ❌ ${table}: ${error.message}`);
        } else {
          console.log(`   ✅ ${table}: EXISTS (${count} rows)`);
        }
      } catch (e: any) {
        console.log(`   ❌ ${table}: ${e.message}`);
      }
    }

    console.log('');
    console.log('2. Checking handover_items columns...');
    console.log('');

    // Try to query handover_items with new columns
    const { data, error } = await client
      .from('handover_items')
      .select('id, category, is_critical, requires_action, handover_id')
      .limit(1);

    if (error) {
      console.log(`   ❌ Error querying handover_items: ${error.message}`);
      console.log(`   This suggests the consolidation migration hasn't been applied.`);
    } else {
      console.log(`   ✅ handover_items has new columns (category, is_critical, requires_action)`);
      console.log(`   Sample data: ${JSON.stringify(data)}`);
    }

    console.log('');
    console.log('3. Checking if handover_id is nullable...');
    console.log('');

    // Try to query items with NULL handover_id
    const { data: nullItems, error: nullError } = await client
      .from('handover_items')
      .select('id, handover_id')
      .is('handover_id', null)
      .limit(5);

    if (nullError) {
      console.log(`   ❌ Error: ${nullError.message}`);
    } else {
      console.log(`   ✅ Found ${nullItems?.length || 0} items with NULL handover_id`);
      console.log(`   This confirms handover_id is nullable (consolidation applied)`);
    }

  } catch (e: any) {
    console.error('Fatal error:', e);
  }

  console.log('');
  console.log('='.repeat(80));
  console.log('SUMMARY');
  console.log('='.repeat(80));
  console.log('');
  console.log('If you see:');
  console.log('  - pms_handover EXISTS → Migration NOT applied (old schema)');
  console.log('  - handover_items has category columns → Migration IS applied');
  console.log('  - Items with NULL handover_id → Migration IS applied');
  console.log('');
}

checkSchema();
