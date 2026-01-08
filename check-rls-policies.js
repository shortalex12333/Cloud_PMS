/**
 * Check RLS policies on search_document_chunks table
 */

const SUPABASE_URL = 'https://vzsohavtuotocgrfkfyd.supabase.co';
const SERVICE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ6c29oYXZ0dW90b2NncmZrZnlkIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MzU5Mjg3NSwiZXhwIjoyMDc5MTY4ODc1fQ.fC7eC_4xGnCHIebPzfaJ18pFMPKgImE7BuN0I3A-pSY';

async function checkRLS() {
  console.log('🔍 CHECKING RLS POLICIES\n');
  console.log('='.repeat(80));

  // Test 1: Can we query search_document_chunks with service role?
  console.log('\n📋 TEST 1: Query search_document_chunks with SERVICE ROLE');
  console.log('-'.repeat(80));

  const testId = 'e4144864-1a61-4f21-ba0d-01ec97f012fb';

  const response1 = await fetch(`${SUPABASE_URL}/rest/v1/search_document_chunks?select=metadata&id=eq.${testId}`, {
    headers: {
      'apikey': SERVICE_KEY,
      'Authorization': `Bearer ${SERVICE_KEY}`,
    }
  });

  const data1 = await response1.json();

  if (response1.ok && data1.length > 0) {
    console.log('✅ SERVICE ROLE can query - RLS bypassed');
    console.log('Metadata:', JSON.stringify(data1[0].metadata, null, 2));
  } else {
    console.log('❌ SERVICE ROLE query failed:', response1.status, JSON.stringify(data1));
  }

  // Test 2: Try with anon key
  console.log('\n📋 TEST 2: Query search_document_chunks with ANON KEY');
  console.log('-'.repeat(80));

  const ANON_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ6c29oYXZ0dW90b2NncmZrZnlkIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjM1OTI4NzUsImV4cCI6MjA3OTE2ODg3NX0.JhJLvLSfLD3OtPDxTgHqgF8dNaZk8ius62jKN68E4WE';

  const response2 = await fetch(`${SUPABASE_URL}/rest/v1/search_document_chunks?select=metadata&id=eq.${testId}`, {
    headers: {
      'apikey': ANON_KEY,
      'Authorization': `Bearer ${ANON_KEY}`,
    }
  });

  const data2 = await response2.json();

  if (response2.ok && data2.length > 0) {
    console.log('✅ ANON KEY can query');
    console.log('Metadata:', JSON.stringify(data2[0].metadata, null, 2));
  } else {
    console.log('❌ ANON KEY query failed:', response2.status);
    console.log('Error:', JSON.stringify(data2, null, 2));
  }

  console.log('\n' + '='.repeat(80));
  console.log('🏁 COMPLETE\n');
}

checkRLS().catch(console.error);
