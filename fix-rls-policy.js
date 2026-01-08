/**
 * Fix RLS policy on search_document_chunks table
 * Execute SQL commands via Supabase REST API
 */

const SUPABASE_URL = 'https://vzsohavtuotocgrfkfyd.supabase.co';
const SERVICE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ6c29oYXZ0dW90b2NncmZrZnlkIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MzU5Mjg3NSwiZXhwIjoyMDc5MTY4ODc1fQ.fC7eC_4xGnCHIebPzfaJ18pFMPKgImE7BuN0I3A-pSY';

async function executeSQL(sql) {
  const response = await fetch(`${SUPABASE_URL}/rest/v1/rpc/exec_sql`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'apikey': SERVICE_KEY,
      'Authorization': `Bearer ${SERVICE_KEY}`,
    },
    body: JSON.stringify({ query: sql }),
  });

  const data = await response.json();
  return { status: response.status, data };
}

async function fixRLSPolicy() {
  console.log('🔧 FIXING RLS POLICY ON search_document_chunks\n');
  console.log('='.repeat(80));

  // STEP 1: Check current policies
  console.log('\n📋 STEP 1: Check current RLS policies');
  console.log('-'.repeat(80));

  const checkPolicies = `
    SELECT
      schemaname,
      tablename,
      policyname,
      permissive,
      roles,
      cmd,
      qual::text as using_expression,
      with_check::text as with_check_expression
    FROM pg_policies
    WHERE tablename = 'search_document_chunks';
  `;

  let result = await executeSQL(checkPolicies);
  console.log('Status:', result.status);
  console.log('Current policies:', JSON.stringify(result.data, null, 2));

  // STEP 2: Drop existing policies
  console.log('\n📋 STEP 2: Drop existing broken policies');
  console.log('-'.repeat(80));

  // Get policy names to drop
  if (result.data && Array.isArray(result.data) && result.data.length > 0) {
    for (const policy of result.data) {
      const dropSQL = `DROP POLICY IF EXISTS "${policy.policyname}" ON search_document_chunks;`;
      console.log(`Dropping policy: ${policy.policyname}`);
      result = await executeSQL(dropSQL);
      console.log('  Status:', result.status);
      if (result.status !== 200) {
        console.log('  Error:', result.data);
      }
    }
  }

  // STEP 3: Create new correct policy
  console.log('\n📋 STEP 3: Create new RLS policy (using auth_users)');
  console.log('-'.repeat(80));

  const createPolicy = `
    CREATE POLICY "chunks_yacht_isolation"
    ON search_document_chunks
    FOR SELECT
    USING (
      yacht_id IN (
        SELECT yacht_id
        FROM auth_users
        WHERE auth_user_id = auth.uid()
      )
    );
  `;

  result = await executeSQL(createPolicy);
  console.log('Status:', result.status);
  console.log('Result:', JSON.stringify(result.data, null, 2));

  // STEP 4: Verify new policy
  console.log('\n📋 STEP 4: Verify new policy');
  console.log('-'.repeat(80));

  result = await executeSQL(checkPolicies);
  console.log('New policies:', JSON.stringify(result.data, null, 2));

  console.log('\n' + '='.repeat(80));
  console.log('🏁 RLS POLICY FIX COMPLETE\n');
}

fixRLSPolicy().catch(console.error);
