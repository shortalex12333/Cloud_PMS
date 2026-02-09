import { createClient } from '@supabase/supabase-js';

const TENANT_URL = 'https://vzsohavtuotocgrfkfyd.supabase.co';
const TENANT_SERVICE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ6c29oYXZ0dW90b2NncmZrZnlkIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MzU5Mjg3NSwiZXhwIjoyMDc5MTY4ODc1fQ.fC7eC_4xGnCHIebPzfaJ18pFMPKgImE7BuN0I3A-pSY';

async function fixForeignKeys() {
  const db = createClient(TENANT_URL, TENANT_SERVICE_KEY);

  console.log('Fixing handover_items foreign key constraints...\n');

  // Drop the incorrect constraint
  console.log('1. Dropping incorrect finalized_by constraint...');
  const { error: dropError } = await db.rpc('exec_sql', {
    sql: 'ALTER TABLE handover_items DROP CONSTRAINT IF EXISTS handover_items_finalized_by_fkey;'
  });

  if (dropError) {
    console.error('❌ Drop constraint failed:', dropError);
    console.log('Trying direct approach...');
  } else {
    console.log('✅ Constraint dropped');
  }

  // Add correct constraint
  console.log('\n2. Adding correct constraint referencing auth_users_profiles...');
  const { error: addError } = await db.rpc('exec_sql', {
    sql: 'ALTER TABLE handover_items ADD CONSTRAINT handover_items_finalized_by_fkey FOREIGN KEY (finalized_by) REFERENCES auth_users_profiles(id);'
  });

  if (addError) {
    console.error('❌ Add constraint failed:', addError);
  } else {
    console.log('✅ Constraint added');
  }

  console.log('\nNote: If RPC failed, you need to run this SQL manually via Supabase SQL Editor.');
}

fixForeignKeys().catch(console.error);
