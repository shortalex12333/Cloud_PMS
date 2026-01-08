/**
 * Test what the search API actually returns
 */

const SUPABASE_URL = 'https://vzsohavtuotocgrfkfyd.supabase.co';
const API_URL = 'https://pipeline-core.int.celeste7.ai';
const ANON_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ6c29oYXZ0dW90b2NncmZrZnlkIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjM1OTI4NzUsImV4cCI6MjA3OTE2ODg3NX0.JhJLvLSfLD3OtPDxTgHqgF8dNaZk8ius62jKN68E4WE';

async function testSearch() {
  console.log('🔍 TESTING SEARCH API RESPONSE\n');
  console.log('='.repeat(80));

  const payload = {
    query: "load line certificate",
    query_type: "free-text",
    context: {
      client_ts: Math.floor(Date.now() / 1000),
      stream_id: crypto.randomUUID(),
      session_id: crypto.randomUUID(),
      source: 'web',
      client_version: '1.0.0',
      locale: 'en-US',
      timezone: 'UTC',
      platform: 'browser',
    },
  };

  console.log('\n📤 Sending search request...');
  console.log('Query:', payload.query);

  const response = await fetch(`${API_URL}/webhook/search`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${ANON_KEY}`,
    },
    body: JSON.stringify(payload),
  });

  console.log('\n📥 Response status:', response.status);

  const data = await response.json();

  console.log('\n✅ Response structure:');
  console.log('  - success:', data.success);
  console.log('  - total_count:', data.total_count);
  console.log('  - results.length:', data.results?.length);

  if (data.results && data.results.length > 0) {
    const firstResult = data.results[0];

    console.log('\n📄 FIRST RESULT:');
    console.log('=' .repeat(80));
    console.log('\nTop-level fields:');
    Object.keys(firstResult).forEach(key => {
      const value = firstResult[key];
      const type = typeof value;
      const preview = type === 'object' ? 'Object' : JSON.stringify(value)?.substring(0, 50);
      console.log(`  - ${key}: ${type} = ${preview}`);
    });

    console.log('\n📦 metadata field (if exists):');
    if (firstResult.metadata) {
      console.log(JSON.stringify(firstResult.metadata, null, 2));
    } else {
      console.log('  ❌ No metadata field!');
    }

    console.log('\n📦 raw_data field (if exists):');
    if (firstResult.raw_data) {
      console.log(JSON.stringify(firstResult.raw_data, null, 2));
    } else {
      console.log('  ❌ No raw_data field!');
    }

    console.log('\n📦 FULL FIRST RESULT:');
    console.log(JSON.stringify(firstResult, null, 2));
  } else {
    console.log('\n❌ No results returned');
  }

  console.log('\n' + '='.repeat(80));
  console.log('🏁 TEST COMPLETE\n');
}

testSearch().catch(console.error);
