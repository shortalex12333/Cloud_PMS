/**
 * Simple DB Inspector using fetch
 * Run with: ANON_KEY=your_key node inspect-db-simple.js
 */

const SUPABASE_URL = 'https://vzsohavtuotocgrfkfyd.supabase.co';
const ANON_KEY = process.env.ANON_KEY || process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

if (!ANON_KEY) {
  console.error('❌ Set ANON_KEY environment variable');
  console.error('Usage: ANON_KEY=your_key node inspect-db-simple.js');
  process.exit(1);
}

async function query(table, select = '*', filters = {}) {
  let url = `${SUPABASE_URL}/rest/v1/${table}?select=${select}`;

  // Add filters
  for (const [key, value] of Object.entries(filters)) {
    url += `&${key}=${value}`;
  }

  const response = await fetch(url, {
    headers: {
      'apikey': ANON_KEY,
      'Authorization': `Bearer ${ANON_KEY}`,
    }
  });

  const data = await response.json();

  return { data, status: response.status, ok: response.ok };
}

async function main() {
  console.log('🔍 DATABASE SCHEMA INSPECTION\n');
  console.log('='.repeat(80));

  // Test 1: Query doc_metadata
  console.log('\n📋 TEST 1: Query doc_metadata table');
  console.log('-'.repeat(80));

  const result1 = await query('doc_metadata', '*', { limit: 1 });

  if (result1.ok && result1.data && result1.data.length > 0) {
    console.log('✅ doc_metadata table found!');
    console.log('\nColumns:');
    Object.keys(result1.data[0]).forEach(col => {
      console.log(`  - ${col}`);
    });
    console.log('\nSample row:');
    console.log(JSON.stringify(result1.data[0], null, 2));
  } else {
    console.log('❌ Error:', result1.status, JSON.stringify(result1.data));
  }

  // Test 2: Query specific document
  console.log('\n📋 TEST 2: Query specific document ID');
  console.log('-'.repeat(80));

  const docId = 'e4144864-1a61-4f21-ba0d-01ec97f012fb';
  console.log(`Document ID: ${docId}`);

  const result2 = await query('doc_metadata', '*', { 'id': `eq.${docId}` });

  if (result2.ok && result2.data && result2.data.length > 0) {
    console.log('✅ Document found!');
    console.log(JSON.stringify(result2.data[0], null, 2));
  } else {
    console.log('❌ Error:', result2.status, JSON.stringify(result2.data));
  }

  // Test 3: Check for users table
  console.log('\n📋 TEST 3: Check for users-related tables');
  console.log('-'.repeat(80));

  const userTables = ['users', 'user_profiles', 'profiles'];

  for (const table of userTables) {
    const result = await query(table, '*', { limit: 0 });
    if (result.ok) {
      console.log(`  ✅ ${table} - EXISTS`);
    } else {
      console.log(`  ❌ ${table} - ${result.status}: ${JSON.stringify(result.data)}`);
    }
  }

  console.log('\n' + '='.repeat(80));
  console.log('🏁 INSPECTION COMPLETE\n');
}

main().catch(console.error);
