#!/usr/bin/env node
/**
 * Debug why document eb31f284-2cf6-4518-aea8-2d611892b284 is not found
 */

const SUPABASE_URL = 'https://vzsohavtuotocgrfkfyd.supabase.co';
const SERVICE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ6c29oYXZ0dW90b2NncmZrZnlkIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MzU5Mjg3NSwiZXhwIjoyMDc5MTY4ODc1fQ.fC7eC_4xGnCHIebPzfaJ18pFMPKgImE7BuN0I3A-pSY';

const TEST_ID = 'eb31f284-2cf6-4518-aea8-2d611892b284';

async function debugDocument() {
  console.log('🔍 DEBUGGING MISSING DOCUMENT\n');
  console.log('Test ID:', TEST_ID);
  console.log('='.repeat(80));

  // Check 1: Is it in search_document_chunks as chunk_id?
  console.log('\n1️⃣ Checking search_document_chunks (as chunk id)...');
  let response = await fetch(
    `${SUPABASE_URL}/rest/v1/search_document_chunks?id=eq.${TEST_ID}&select=*`,
    {
      headers: {
        'apikey': SERVICE_KEY,
        'Authorization': `Bearer ${SERVICE_KEY}`
      }
    }
  );
  let data = await response.json();
  console.log(`   Found as chunk_id: ${data.length > 0 ? 'YES ✅' : 'NO ❌'}`);
  if (data.length > 0) console.log('   Data:', data[0]);

  // Check 2: Is it in search_document_chunks as document_id?
  console.log('\n2️⃣ Checking search_document_chunks (as document_id)...');
  response = await fetch(
    `${SUPABASE_URL}/rest/v1/search_document_chunks?document_id=eq.${TEST_ID}&select=*&limit=1`,
    {
      headers: {
        'apikey': SERVICE_KEY,
        'Authorization': `Bearer ${SERVICE_KEY}`
      }
    }
  );
  data = await response.json();
  console.log(`   Found as document_id: ${data.length > 0 ? 'YES ✅' : 'NO ❌'}`);
  if (data.length > 0) console.log('   Chunk:', data[0]);

  // Check 3: Is it in doc_metadata?
  console.log('\n3️⃣ Checking doc_metadata...');
  response = await fetch(
    `${SUPABASE_URL}/rest/v1/doc_metadata?id=eq.${TEST_ID}&select=*`,
    {
      headers: {
        'apikey': SERVICE_KEY,
        'Authorization': `Bearer ${SERVICE_KEY}`
      }
    }
  );
  data = await response.json();
  console.log(`   Found in doc_metadata: ${data.length > 0 ? 'YES ✅' : 'NO ❌'}`);
  if (data.length > 0) {
    console.log('   Document:', {
      filename: data[0].filename,
      storage_path: data[0].storage_path,
      yacht_id: data[0].yacht_id,
      indexed: data[0].indexed
    });
  }

  // Check 4: Search for "Generator 2" to see what ID it should be
  console.log('\n4️⃣ Searching for "Generator 2" in doc_metadata...');
  response = await fetch(
    `${SUPABASE_URL}/rest/v1/doc_metadata?or=(filename.ilike.*generator*2*,metadata->>oem.ilike.*generator*2*)&select=id,filename,storage_path,indexed`,
    {
      headers: {
        'apikey': SERVICE_KEY,
        'Authorization': `Bearer ${SERVICE_KEY}`
      }
    }
  );
  data = await response.json();
  console.log(`   Found ${data.length} matches`);
  if (data.length > 0) {
    data.forEach((doc, i) => {
      console.log(`   [${i + 1}] ${doc.filename} (id: ${doc.id}, indexed: ${doc.indexed})`);
    });
  }

  console.log('\n' + '='.repeat(80));
  console.log('CONCLUSION:');
  console.log('If document NOT in search_document_chunks → needs to be indexed');
  console.log('If document NOT in doc_metadata → was never uploaded/processed');
  console.log('='.repeat(80));
}

debugDocument().catch(console.error);
