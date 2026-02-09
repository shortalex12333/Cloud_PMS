/**
 * Drop pms_handover table from tenant DB
 * This table should have been dropped by migration 20260205140000
 * but still exists, causing conflicts
 */

import { createClient } from '@supabase/supabase-js';

const TENANT_URL = 'https://vzsohavtuotocgrfkfyd.supabase.co';
const TENANT_SERVICE_KEY = process.env.TENANT_1_SUPABASE_SERVICE_KEY;

if (!TENANT_SERVICE_KEY) {
  console.error('ERROR: TENANT_1_SUPABASE_SERVICE_KEY environment variable not set');
  console.error('This operation requires service_role key to execute DDL statements');
  process.exit(1);
}

const client = createClient(TENANT_URL, TENANT_SERVICE_KEY);

console.log('='.repeat(80));
console.log('DROP pms_handover TABLE');
console.log('='.repeat(80));
console.log('');
console.log('⚠️  WARNING: This will permanently drop the pms_handover table');
console.log('');
console.log('The table should have been dropped by migration 20260205140000');
console.log('but still exists. This causes add_to_handover to fail with:');
console.log('  "Could not find the table \'public.pms_handover\' in the schema cache"');
console.log('');
console.log('Press Ctrl+C to cancel, or wait 3 seconds to proceed...');
console.log('');

await new Promise(resolve => setTimeout(resolve, 3000));

try {
  console.log('Executing: DROP TABLE IF EXISTS pms_handover CASCADE;');

  // Use RPC to execute raw SQL (requires service_role key)
  const { data, error } = await client.rpc('exec_sql', {
    sql: 'DROP TABLE IF EXISTS pms_handover CASCADE;'
  });

  if (error) {
    console.error('❌ Error:', error.message);
    console.error('');
    console.error('Alternative: Run this SQL manually in Supabase SQL Editor:');
    console.error('  DROP TABLE IF EXISTS pms_handover CASCADE;');
  } else {
    console.log('✅ Table dropped successfully');
    console.log('');
    console.log('Verifying...');

    // Try to query the table (should fail)
    const { error: verifyError } = await client.from('pms_handover').select('count').limit(1);

    if (verifyError && verifyError.message.includes('does not exist')) {
      console.log('✅ Verified: pms_handover no longer exists');
    } else {
      console.log('⚠️  Table may still exist, check manually');
    }
  }
} catch (e: any) {
  console.error('Fatal error:', e.message);
  console.error('');
  console.error('MANUAL FIX: Go to Supabase dashboard > SQL Editor and run:');
  console.error('  DROP TABLE IF EXISTS pms_handover CASCADE;');
}

console.log('');
console.log('='.repeat(80));
