/**
 * Verify pms_handover is actually dropped and refresh PostgREST schema cache
 */

import { createClient } from '@supabase/supabase-js';

const TENANT_URL = 'https://vzsohavtuotocgrfkfyd.supabase.co';
const TENANT_ANON_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ6c29oYXZ0dW90b2NncmZrZnlkIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjM1OTI4NzUsImV4cCI6MjA3OTE2ODg3NX0.JhJLvLSfLD3OtPDxTgHqgF8dNaZk8ius62jKN68E4WE';

const client = createClient(TENANT_URL, TENANT_ANON_KEY);

console.log('='.repeat(80));
console.log('VERIFY pms_handover DROPPED');
console.log('='.repeat(80));
console.log('');

async function verify() {
  // Method 1: Try to query information_schema
  console.log('1. Checking information_schema.tables...');
  try {
    const response = await fetch(`${TENANT_URL}/rest/v1/information_schema.tables?table_schema=eq.public&table_name=eq.pms_handover`, {
      headers: {
        'apikey': TENANT_ANON_KEY,
        'Authorization': `Bearer ${TENANT_ANON_KEY}`,
      }
    });
    const data = await response.json();
    console.log(`   Result: ${JSON.stringify(data)}`);
    if (data && data.length > 0) {
      console.log('   ❌ pms_handover still exists in information_schema');
    } else {
      console.log('   ✅ pms_handover not found in information_schema');
    }
  } catch (e: any) {
    console.log(`   Error: ${e.message}`);
  }

  console.log('');
  console.log('2. Trying direct table access...');

  // Method 2: Try to access the table directly
  const { data, error } = await client.from('pms_handover').select('count').limit(1);

  if (error) {
    if (error.message.includes('does not exist') || error.code === '42P01' || error.code === 'PGRST204') {
      console.log('   ✅ Table does not exist (expected)');
      console.log(`   Error: ${error.message}`);
    } else {
      console.log('   ⚠️  Unexpected error');
      console.log(`   Code: ${error.code}`);
      console.log(`   Message: ${error.message}`);
    }
  } else {
    console.log('   ❌ Table still accessible!');
    console.log(`   Data: ${JSON.stringify(data)}`);
  }

  console.log('');
  console.log('3. Checking if PostgREST schema cache needs reload...');
  console.log('   PostgREST caches the database schema.');
  console.log('   If table was just dropped, Supabase may need to:');
  console.log('   - Wait ~10 seconds for automatic cache refresh');
  console.log('   - OR restart PostgREST service (Supabase support)');
  console.log('');
  console.log('   Try waiting 30 seconds then test again.');

  console.log('');
  console.log('='.repeat(80));
}

verify();
