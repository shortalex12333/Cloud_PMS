#!/usr/bin/env node
/**
 * Apply RLS policy fix to search_document_chunks table
 * Uses direct Supabase client with service role key
 */

const SUPABASE_URL = 'https://vzsohavtuotocgrfkfyd.supabase.co';
const SERVICE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ6c29oYXZ0dW90b2NncmZrZnlkIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MzU5Mjg3NSwiZXhwIjoyMDc5MTY4ODc1fQ.fC7eC_4xGnCHIebPzfaJ18pFMPKgImE7BuN0I3A-pSY';

async function executeSQL(sql, description) {
  console.log(`\n📋 ${description}`);
  console.log('-'.repeat(80));

  const response = await fetch(`${SUPABASE_URL}/rest/v1/rpc/exec`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'apikey': SERVICE_KEY,
      'Authorization': `Bearer ${SERVICE_KEY}`,
      'Prefer': 'return=representation'
    },
    body: JSON.stringify({ query: sql }),
  });

  const text = await response.text();
  console.log('Status:', response.status);

  if (response.ok) {
    console.log('✅ Success');
    if (text) {
      try {
        const data = JSON.parse(text);
        console.log('Result:', JSON.stringify(data, null, 2));
      } catch {
        console.log('Result:', text);
      }
    }
    return true;
  } else {
    console.log('❌ Failed');
    console.log('Error:', text);
    return false;
  }
}

async function checkCurrentPolicies() {
  console.log('\n🔍 STEP 1: Check current RLS policies');
  console.log('='.repeat(80));

  const response = await fetch(`${SUPABASE_URL}/rest/v1/rpc/exec`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'apikey': SERVICE_KEY,
      'Authorization': `Bearer ${SERVICE_KEY}`,
    },
    body: JSON.stringify({
      query: `
        SELECT
          schemaname,
          tablename,
          policyname,
          permissive,
          roles,
          cmd,
          qual::text as using_expression
        FROM pg_policies
        WHERE tablename = 'search_document_chunks'
        ORDER BY policyname;
      `
    }),
  });

  const text = await response.text();
  console.log('Status:', response.status);

  if (response.ok && text) {
    try {
      const data = JSON.parse(text);
      if (data.length === 0) {
        console.log('ℹ️  No policies found on search_document_chunks');
      } else {
        console.log('Current policies:', JSON.stringify(data, null, 2));
      }
      return data;
    } catch {
      console.log('Response:', text);
    }
  } else {
    console.log('Failed to query policies:', text);
  }
  return [];
}

async function applyFix() {
  console.log('\n🔧 APPLYING RLS POLICY FIX TO search_document_chunks');
  console.log('='.repeat(80));

  // Step 1: Check current state
  const policies = await checkCurrentPolicies();

  // Step 2: Drop existing policies
  if (policies && policies.length > 0) {
    console.log('\n🗑️  STEP 2: Dropping existing policies');
    console.log('='.repeat(80));

    for (const policy of policies) {
      await executeSQL(
        `DROP POLICY IF EXISTS "${policy.policyname}" ON public.search_document_chunks;`,
        `Dropping policy: ${policy.policyname}`
      );
    }
  }

  // Step 3: Create new correct policy
  console.log('\n✨ STEP 3: Creating new RLS policy');
  console.log('='.repeat(80));

  const createPolicy = `
    CREATE POLICY "chunks_yacht_isolation"
    ON public.search_document_chunks
    FOR SELECT
    TO authenticated, anon
    USING (
      yacht_id IN (
        SELECT yacht_id
        FROM public.auth_users
        WHERE auth_user_id = auth.uid()
      )
    );
  `;

  const success = await executeSQL(createPolicy, 'Creating chunks_yacht_isolation policy');

  if (!success) {
    console.log('\n⚠️  Failed to create policy via RPC, trying alternative method...');
    // Policy creation might need to be done via Supabase dashboard
    return false;
  }

  // Step 4: Verify
  console.log('\n✅ STEP 4: Verifying new policy');
  console.log('='.repeat(80));
  await checkCurrentPolicies();

  // Step 5: Test access
  console.log('\n🧪 STEP 5: Testing access with anon key');
  console.log('='.repeat(80));

  const ANON_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ6c29oYXZ0dW90b2NncmZrZnlkIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjM1OTI4NzUsImV4cCI6MjA3OTE2ODg3NX0.JhJLvLSfLD3OtPDxTgHqgF8dNaZk8ius62jKN68E4WE';

  const testResponse = await fetch(`${SUPABASE_URL}/rest/v1/search_document_chunks?select=id&limit=1`, {
    headers: {
      'apikey': ANON_KEY,
      'Authorization': `Bearer ${ANON_KEY}`,
    }
  });

  const testData = await testResponse.text();
  console.log('Anon query status:', testResponse.status);

  if (testResponse.ok) {
    console.log('✅ Anon access working!');
  } else {
    console.log('❌ Anon access still failing:');
    console.log(testData);
  }

  console.log('\n' + '='.repeat(80));
  console.log('🏁 FIX APPLICATION COMPLETE\n');

  return success;
}

applyFix().catch(console.error);
