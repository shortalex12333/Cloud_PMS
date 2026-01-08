/**
 * Inspect search_document_chunks table
 */

const SUPABASE_URL = 'https://vzsohavtuotocgrfkfyd.supabase.co';
const SERVICE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ6c29oYXZ0dW90b2NncmZrZnlkIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MzU5Mjg3NSwiZXhwIjoyMDc5MTY4ODc1fQ.fC7eC_4xGnCHIebPzfaJ18pFMPKgImE7BuN0I3A-pSY';

async function query(table, select = '*', filters = {}) {
  let url = `${SUPABASE_URL}/rest/v1/${table}?select=${select}`;
  for (const [key, value] of Object.entries(filters)) {
    url += `&${key}=${value}`;
  }
  const response = await fetch(url, {
    headers: {
      'apikey': SERVICE_KEY,
      'Authorization': `Bearer ${SERVICE_KEY}`,
    }
  });
  const data = await response.json();
  return { data, status: response.status, ok: response.ok };
}

async function main() {
  console.log('🔍 INSPECTING SEARCH_DOCUMENT_CHUNKS\n');
  console.log('='.repeat(80));

  // 1. Get structure
  console.log('\n📋 TEST 1: Get search_document_chunks structure');
  console.log('-'.repeat(80));

  const result1 = await query('search_document_chunks', '*', { limit: 1 });

  if (result1.ok && result1.data && result1.data.length > 0) {
    console.log('✅ search_document_chunks found!');
    console.log('\nColumns:');
    Object.keys(result1.data[0]).forEach(col => {
      console.log(`  - ${col}`);
    });
    console.log('\nSample row:');
    console.log(JSON.stringify(result1.data[0], null, 2));
  } else {
    console.log('❌ Error:', result1.status, JSON.stringify(result1.data));
  }

  // 2. Query the specific chunk ID from the error
  console.log('\n📋 TEST 2: Query specific chunk ID from error logs');
  console.log('-'.repeat(80));

  const chunkId = 'e4144864-1a61-4f21-ba0d-01ec97f012fb';
  console.log(`Chunk ID: ${chunkId}`);

  const result2 = await query('search_document_chunks', '*', { 'id': `eq.${chunkId}` });

  if (result2.ok && result2.data && result2.data.length > 0) {
    console.log('✅ Chunk found!');
    console.log(JSON.stringify(result2.data[0], null, 2));
  } else {
    console.log('❌ Error:', result2.status, JSON.stringify(result2.data));
  }

  console.log('\n' + '='.repeat(80));
  console.log('🏁 COMPLETE\n');
}

main().catch(console.error);
