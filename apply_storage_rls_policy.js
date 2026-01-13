#!/usr/bin/env node
/**
 * Apply Storage RLS Policy for Documents Bucket
 * Fixes "Object not found" error when viewing documents
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

async function applyStorageRLSPolicy() {
  console.log('🔧 APPLYING STORAGE RLS POLICY FOR DOCUMENTS BUCKET\n');
  console.log('='.repeat(80));

  // STEP 1: Check existing storage policies
  console.log('\n📋 STEP 1: Check existing storage policies');
  console.log('-'.repeat(80));

  const checkPolicies = `
    SELECT
      schemaname,
      tablename,
      policyname,
      cmd,
      qual::text as using_expression
    FROM pg_policies
    WHERE schemaname = 'storage'
      AND tablename = 'objects'
    ORDER BY policyname;
  `;

  let result = await executeSQL(checkPolicies);
  console.log('Status:', result.status);

  if (result.status === 200) {
    console.log('✅ Current storage policies:');
    if (result.data && result.data.length > 0) {
      result.data.forEach(policy => {
        console.log(`   - ${policy.policyname} (${policy.cmd})`);
      });
    } else {
      console.log('   (No policies found)');
    }

    // Check if our policy already exists
    const ourPolicy = result.data?.find(p => p.policyname === 'Users read yacht documents');
    if (ourPolicy) {
      console.log('\n⚠️  Policy "Users read yacht documents" already exists!');
      console.log('   Skipping creation.');
      return;
    }
  } else {
    console.error('❌ Failed to check policies:', result.data);
  }

  // STEP 2: Create the RLS policy
  console.log('\n🔨 STEP 2: Creating RLS policy for documents bucket');
  console.log('-'.repeat(80));

  const createPolicy = `
    CREATE POLICY "Users read yacht documents"
    ON storage.objects
    FOR SELECT
    TO authenticated
    USING (
      bucket_id = 'documents'
      AND (storage.foldername(name))[1] = (
        SELECT yacht_id::text
        FROM auth_users_profiles
        WHERE id = auth.uid()
      )
    );
  `;

  result = await executeSQL(createPolicy);
  console.log('Status:', result.status);

  if (result.status === 200 || result.status === 204) {
    console.log('✅ RLS policy created successfully!');
  } else {
    console.error('❌ Failed to create policy:', result.data);
    console.error('\nYou may need to run this SQL manually in Supabase Dashboard:');
    console.error(createPolicy);
    return;
  }

  // STEP 3: Verify the policy was created
  console.log('\n✅ STEP 3: Verifying policy creation');
  console.log('-'.repeat(80));

  const verifyPolicy = `
    SELECT
      policyname,
      cmd,
      roles,
      qual::text as using_expression
    FROM pg_policies
    WHERE schemaname = 'storage'
      AND tablename = 'objects'
      AND policyname = 'Users read yacht documents';
  `;

  result = await executeSQL(verifyPolicy);
  console.log('Status:', result.status);

  if (result.status === 200 && result.data && result.data.length > 0) {
    console.log('✅ Policy verified!');
    console.log(JSON.stringify(result.data[0], null, 2));
  } else {
    console.error('❌ Policy not found after creation!');
  }

  console.log('\n' + '='.repeat(80));
  console.log('🎉 MIGRATION COMPLETE!\n');
  console.log('Next steps:');
  console.log('1. Test document viewing in the app');
  console.log('2. Run test script: node test_intact_file.js');
  console.log('3. Or test in browser console with chunk ID:');
  console.log('   a7d09bbf-4203-4732-a36c-727b687dc956');
  console.log('='.repeat(80));
}

// Run the migration
applyStorageRLSPolicy().catch(err => {
  console.error('❌ FATAL ERROR:', err);
  process.exit(1);
});
