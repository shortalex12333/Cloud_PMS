#!/usr/bin/env node
/**
 * TRACE SEARCH FLOW - Compare working vs non-working queries
 * Run this to see exact SQL queries and IDs returned
 */

const SUPABASE_URL = 'https://vzsohavtuotocgrfkfyd.supabase.co';
const SERVICE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ6c29oYXZ0dW90b2NncmZrZnlkIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MzU5Mjg3NSwiZXhwIjoyMDc5MTY4ODc1fQ.fC7eC_4xGnCHIebPzfaJ18pFMPKgImE7BuN0I3A-pSY';
const YACHT_ID = '85fe1119-b04c-41ac-80f1-829d23322598';

async function traceSearch() {
  console.log('🔍 TRACING SEARCH FLOW\n');
  console.log('='.repeat(80));

  // TEST 1: Search for "generator cooling" (broken)
  console.log('\n📋 TEST 1: "generator cooling" (BROKEN)');
  console.log('-'.repeat(80));

  const query1 = 'generator cooling';
  const response1 = await fetch(
    `${SUPABASE_URL}/rest/v1/search_document_chunks?content=ilike.*${encodeURIComponent(query1)}*&yacht_id=eq.${YACHT_ID}&select=id,document_id,content,section_title&limit=5`,
    {
      headers: {
        'apikey': SERVICE_KEY,
        'Authorization': `Bearer ${SERVICE_KEY}`
      }
    }
  );

  const data1 = await response1.json();
  console.log(`✅ Found ${data1.length} chunks`);
  if (data1.length > 0) {
    console.log('\n📄 First result:');
    console.log('   Chunk ID:', data1[0].id);
    console.log('   Document ID:', data1[0].document_id);
    console.log('   Section:', data1[0].section_title);
    console.log('   Content snippet:', data1[0].content?.substring(0, 100));
  }

  // TEST 2: Search for "Furuno" (working)
  console.log('\n\n📋 TEST 2: "Furuno" (WORKING)');
  console.log('-'.repeat(80));

  const query2 = 'Furuno';
  const response2 = await fetch(
    `${SUPABASE_URL}/rest/v1/search_document_chunks?content=ilike.*${encodeURIComponent(query2)}*&yacht_id=eq.${YACHT_ID}&select=id,document_id,content,section_title&limit=5`,
    {
      headers: {
        'apikey': SERVICE_KEY,
        'Authorization': `Bearer ${SERVICE_KEY}`
      }
    }
  );

  const data2 = await response2.json();
  console.log(`✅ Found ${data2.length} chunks`);
  if (data2.length > 0) {
    console.log('\n📄 First result:');
    console.log('   Chunk ID:', data2[0].id);
    console.log('   Document ID:', data2[0].document_id);
    console.log('   Section:', data2[0].section_title);
    console.log('   Content snippet:', data2[0].content?.substring(0, 100));
  }

  // TEST 3: Check if the "broken" ID exists anywhere
  console.log('\n\n📋 TEST 3: Checking broken ID in database');
  console.log('-'.repeat(80));

  const brokenId = 'eb31f284-2cf6-4518-aea8-2d611892b284';
  console.log('Broken ID:', brokenId);

  // Check in chunks
  const checkChunk = await fetch(
    `${SUPABASE_URL}/rest/v1/search_document_chunks?id=eq.${brokenId}&select=*`,
    {
      headers: {
        'apikey': SERVICE_KEY,
        'Authorization': `Bearer ${SERVICE_KEY}`
      }
    }
  );
  const chunkData = await checkChunk.json();
  console.log(`   In search_document_chunks (as id): ${chunkData.length > 0 ? '✅ YES' : '❌ NO'}`);

  // Check as document_id
  const checkDoc = await fetch(
    `${SUPABASE_URL}/rest/v1/search_document_chunks?document_id=eq.${brokenId}&select=*&limit=1`,
    {
      headers: {
        'apikey': SERVICE_KEY,
        'Authorization': `Bearer ${SERVICE_KEY}`
      }
    }
  );
  const docData = await checkDoc.json();
  console.log(`   In search_document_chunks (as document_id): ${docData.length > 0 ? '✅ YES' : '❌ NO'}`);

  // Check in doc_metadata
  const checkMeta = await fetch(
    `${SUPABASE_URL}/rest/v1/doc_metadata?id=eq.${brokenId}&select=*`,
    {
      headers: {
        'apikey': SERVICE_KEY,
        'Authorization': `Bearer ${SERVICE_KEY}`
      }
    }
  );
  const metaData = await checkMeta.json();
  console.log(`   In doc_metadata: ${metaData.length > 0 ? '✅ YES' : '❌ NO'}`);

  // TEST 4: Call backend search API directly
  console.log('\n\n📋 TEST 4: Calling backend /webhook/search');
  console.log('-'.repeat(80));

  const backendResponse = await fetch('https://pipeline-core.int.celeste7.ai/webhook/search', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      query: 'generator cooling',
      auth: {
        yacht_id: YACHT_ID,
        user_id: '00000000-0000-0000-0000-000000000000',
        role: 'Engineer'
      },
      limit: 5
    })
  });

  const backendData = await backendResponse.json();
  console.log('Backend response status:', backendResponse.status);

  if (backendData.results && backendData.results.length > 0) {
    console.log(`✅ Backend returned ${backendData.results.length} results`);
    console.log('\n📄 First backend result:');
    const first = backendData.results[0];
    console.log('   ID:', first.id);
    console.log('   Primary ID:', first.primary_id);
    console.log('   Type:', first.type);
    console.log('   Title:', first.title);
    console.log('   Metadata:', first.metadata);
  } else {
    console.log('❌ Backend returned no results or error:', backendData);
  }

  console.log('\n' + '='.repeat(80));
  console.log('CONCLUSION:');
  console.log('If backend returns different IDs than direct DB query → search index issue');
  console.log('If backend returns same IDs as DB → ID mapping issue in normalizer');
  console.log('='.repeat(80));
}

traceSearch().catch(console.error);
