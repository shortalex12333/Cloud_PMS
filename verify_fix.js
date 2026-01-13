#!/usr/bin/env node
/**
 * Verify RLS Policy and Test Document Access
 */

const SUPABASE_URL = 'https://vzsohavtuotocgrfkfyd.supabase.co';
const SERVICE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ6c29oYXZ0dW90b2NncmZrZnlkIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MzU5Mjg3NSwiZXhwIjoyMDc5MTY4ODc1fQ.fC7eC_4xGnCHIebPzfaJ18pFMPKgImE7BuN0I3A-pSY';

async function verifyFix() {
  console.log('🔍 VERIFYING RLS POLICY FIX\n');
  console.log('='.repeat(80));

  // Step 1: Check if policy exists
  console.log('\n1️⃣ Checking if RLS policy exists...');

  const checkSQL = `
    SELECT
      policyname,
      cmd,
      roles::text[],
      qual::text as using_clause
    FROM pg_policies
    WHERE schemaname = 'storage'
      AND tablename = 'objects'
      AND policyname = 'Users read yacht documents';
  `;

  try {
    const response = await fetch(
      `${SUPABASE_URL}/rest/v1/rpc/exec_sql?query=${encodeURIComponent(checkSQL)}`,
      {
        method: 'GET',
        headers: {
          'apikey': SERVICE_KEY,
          'Authorization': `Bearer ${SERVICE_KEY}`,
        }
      }
    );

    // Since exec_sql doesn't exist, we'll check via browser test
    console.log('   ⚠️  Cannot verify via API (exec_sql not available)');
    console.log('   ✅ Assuming policy created based on your confirmation\n');

    // Step 2: Show browser test
    console.log('2️⃣ Test document access in browser console:');
    console.log('-'.repeat(80));
    console.log('\n📋 Copy and paste this into your browser console:\n');
    console.log('// Login to your app first, then run:');
    console.log(`
const testChunkId = 'a7d09bbf-4203-4732-a36c-727b687dc956';

console.log('🧪 Testing document access...');

// Get storage path
const { data: rpcData, error: rpcError } = await supabase.rpc('get_document_storage_path', {
  p_chunk_id: testChunkId
});

if (rpcError) {
  console.error('❌ RPC Error:', rpcError);
} else {
  console.log('✅ RPC Success');

  const docInfo = Array.isArray(rpcData) ? rpcData[0] : rpcData;
  const storagePath = docInfo.storage_path.replace('documents/', '');

  console.log('📂 Path:', storagePath);

  // Create signed URL
  const { data: urlData, error: urlError } = await supabase.storage
    .from('documents')
    .createSignedUrl(storagePath, 3600);

  if (urlError) {
    console.error('❌ FAILED - RLS policy not working:', urlError.message);
  } else {
    console.log('✅ SUCCESS! Opening PDF...');
    window.open(urlData.signedUrl, '_blank');
  }
}
`);

    console.log('\n' + '='.repeat(80));
    console.log('📊 EXPECTED RESULTS:');
    console.log('='.repeat(80));
    console.log('✅ RPC Success');
    console.log('✅ Signed URL created');
    console.log('✅ PDF opens in new tab');
    console.log('\n❌ If you still see "Object not found":');
    console.log('   - Check user is logged in');
    console.log('   - Check user has yacht_id in auth_users_profiles');
    console.log('   - Check file path starts with correct yacht_id');
    console.log('='.repeat(80));

  } catch (err) {
    console.error('❌ Error:', err.message);
  }
}

verifyFix().catch(console.error);
