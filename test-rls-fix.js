#!/usr/bin/env node
/**
 * Test RLS policy fix on search_document_chunks table
 * Run this AFTER applying the RLS policy fix
 */

const SUPABASE_URL = 'https://vzsohavtuotocgrfkfyd.supabase.co';
const SERVICE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ6c29oYXZ0dW90b2NncmZrZnlkIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MzU5Mjg3NSwiZXhwIjoyMDc5MTY4ODc1fQ.fC7eC_4xGnCHIebPzfaJ18pFMPKgImE7BuN0I3A-pSY';
const ANON_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ6c29oYXZ0dW90b2NncmZrZnlkIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjM1OTI4NzUsImV4cCI6MjA3OTE2ODg3NX0.JhJLvLSfLD3OtPDxTgHqgF8dNaZk8ius62jKN68E4WE';

async function testAccess() {
  console.log('\n🧪 TESTING RLS POLICY FIX ON search_document_chunks');
  console.log('='.repeat(80));

  // Test 1: Service role should always work
  console.log('\n📋 TEST 1: Query with SERVICE ROLE (should always work)');
  console.log('-'.repeat(80));

  const response1 = await fetch(`${SUPABASE_URL}/rest/v1/search_document_chunks?select=id,document_id,yacht_id&limit=1`, {
    headers: {
      'apikey': SERVICE_KEY,
      'Authorization': `Bearer ${SERVICE_KEY}`,
    }
  });

  const data1 = await response1.json();
  console.log('Status:', response1.status);

  if (response1.ok) {
    console.log('✅ Service role access working');
    if (data1.length > 0) {
      console.log('Sample data:', JSON.stringify(data1[0], null, 2));
    }
  } else {
    console.log('❌ Service role access failed (unexpected!)');
    console.log('Error:', JSON.stringify(data1, null, 2));
  }

  // Test 2: Anon key - THIS IS THE CRITICAL TEST
  console.log('\n📋 TEST 2: Query with ANON KEY (this was failing before fix)');
  console.log('-'.repeat(80));

  const response2 = await fetch(`${SUPABASE_URL}/rest/v1/search_document_chunks?select=id,document_id&limit=1`, {
    headers: {
      'apikey': ANON_KEY,
      'Authorization': `Bearer ${ANON_KEY}`,
    }
  });

  const data2 = await response2.json();
  console.log('Status:', response2.status);

  if (response2.ok) {
    console.log('✅ Anon key access working!');
    console.log('✅ RLS POLICY FIX SUCCESSFUL!');
    if (data2.length > 0) {
      console.log('Sample data:', JSON.stringify(data2[0], null, 2));
    } else {
      console.log('ℹ️  No data returned (might be due to yacht_id filter)');
    }
  } else {
    console.log('❌ Anon key access still failing');
    console.log('Error:', JSON.stringify(data2, null, 2));

    if (data2.code === '42P01' && data2.message && data2.message.includes('users')) {
      console.log('\n⚠️  ERROR: Still referencing non-existent "users" table');
      console.log('⚠️  The RLS policy fix has NOT been applied yet');
      console.log('⚠️  Please follow instructions in FIX_RLS_POLICY_MANUAL.md');
    } else {
      console.log('\n⚠️  Different error - may be authentication related');
    }
  }

  // Test 3: Specific chunk that we know exists
  console.log('\n📋 TEST 3: Query specific chunk with ANON KEY');
  console.log('-'.repeat(80));

  const testChunkId = 'e4144864-1a61-4f21-ba0d-01ec97f012fb';

  const response3 = await fetch(`${SUPABASE_URL}/rest/v1/search_document_chunks?select=id,document_id&id=eq.${testChunkId}`, {
    headers: {
      'apikey': ANON_KEY,
      'Authorization': `Bearer ${ANON_KEY}`,
    }
  });

  const data3 = await response3.json();
  console.log('Status:', response3.status);

  if (response3.ok) {
    console.log('✅ Specific chunk query working');
    if (data3.length > 0) {
      console.log('Chunk data:', JSON.stringify(data3[0], null, 2));
    } else {
      console.log('ℹ️  Chunk not found or not accessible (yacht_id mismatch)');
    }
  } else {
    console.log('❌ Specific chunk query failed');
    console.log('Error:', JSON.stringify(data3, null, 2));
  }

  console.log('\n' + '='.repeat(80));
  console.log('🏁 TEST COMPLETE\n');

  // Summary
  console.log('SUMMARY:');
  console.log('-'.repeat(80));
  if (response2.ok) {
    console.log('✅ RLS policy fix is working correctly');
    console.log('✅ Documents should now load in the frontend');
    console.log('\nNext steps:');
    console.log('1. Test document loading in web app');
    console.log('2. Search for a document');
    console.log('3. Click on a result');
    console.log('4. Document viewer should open and display PDF');
  } else {
    console.log('❌ RLS policy fix not applied or not working');
    console.log('\nNext steps:');
    console.log('1. Read FIX_RLS_POLICY_MANUAL.md');
    console.log('2. Apply the fix via Supabase dashboard');
    console.log('3. Run this test script again');
  }
  console.log('');
}

testAccess().catch(console.error);
