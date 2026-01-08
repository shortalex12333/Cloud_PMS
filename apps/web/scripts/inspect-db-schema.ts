/**
 * Database Schema Inspector
 * Queries Supabase to understand actual table structure
 */

import { createClient } from '@supabase/supabase-js';

// Hardcode the credentials we know work from the browser
const supabaseUrl = 'https://vzsohavtuotocgrfkfyd.supabase.co';
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || '';

if (!supabaseAnonKey) {
  console.error('❌ Need NEXT_PUBLIC_SUPABASE_ANON_KEY');
  process.exit(1);
}

const supabase = createClient(supabaseUrl, supabaseAnonKey);

async function inspectSchema() {
  console.log('🔍 INSPECTING DATABASE SCHEMA\n');
  console.log('=' .repeat(80));

  // 1. Try querying known tables directly
  console.log('\n📋 STEP 1: Test known table names');
  console.log('-'.repeat(80));

  const knownTables = [
    'doc_metadata',
    'search_document_chunks',
    'pms_equipment',
    'pms_parts',
    'work_orders',
    'users',
    'user_profiles',
    'profiles'
  ];

  console.log('🔍 Testing known table names:\n');
  for (const tableName of knownTables) {
    const { data, error } = await supabase
      .from(tableName)
      .select('*')
      .limit(0);

    if (!error) {
      console.log(`  ✅ ${tableName} - EXISTS`);
    } else {
      console.log(`  ❌ ${tableName} - ${error.code}: ${error.message}`);
    }
  }

  // 2. Inspect doc_metadata table specifically
  console.log('\n📋 STEP 2: Inspect doc_metadata table structure');
  console.log('-'.repeat(80));

  // Try to get one row to see all columns
  const { data: sampleRow, error: sampleError } = await supabase
    .from('doc_metadata')
    .select('*')
    .limit(1);

  if (sampleError) {
    console.error('❌ Error querying doc_metadata:', sampleError);
  } else if (sampleRow && sampleRow.length > 0) {
    console.log('✅ doc_metadata columns:');
    const columns = Object.keys(sampleRow[0]);
    columns.forEach(col => {
      const value = sampleRow[0][col];
      const type = typeof value;
      const preview = JSON.stringify(value);
      const shortPreview = preview ? preview.substring(0, 50) : 'null';
      console.log(`  - ${col}: ${type} = ${shortPreview}`);
    });

    console.log('\n📄 Full sample row:');
    console.log(JSON.stringify(sampleRow[0], null, 2));
  } else {
    console.log('⚠️ doc_metadata table exists but is empty');
  }

  // 3. Try to query doc_metadata with the ID from the error
  console.log('\n📋 STEP 3: Query specific document from logs');
  console.log('-'.repeat(80));

  const testDocId = 'e4144864-1a61-4f21-ba0d-01ec97f012fb';
  console.log(`Testing document ID: ${testDocId}`);

  const { data: testDoc, error: testError } = await supabase
    .from('doc_metadata')
    .select('*')
    .eq('id', testDocId)
    .single();

  if (testError) {
    console.error('❌ Error:', testError);
  } else {
    console.log('✅ Document found:');
    console.log(JSON.stringify(testDoc, null, 2));
  }

  console.log('\n' + '='.repeat(80));
  console.log('🏁 INSPECTION COMPLETE\n');
}

inspectSchema().catch(console.error);
