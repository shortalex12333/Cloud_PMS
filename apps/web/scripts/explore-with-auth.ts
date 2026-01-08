/**
 * Authenticated Supabase Exploration
 * Uses actual app client and signs in to test queries
 */

import { supabase } from '../src/lib/supabaseClient';

// Test credentials (you'll need to provide real ones)
const TEST_EMAIL = 'test@example.com'; // Replace with actual test account
const TEST_PASSWORD = 'test123'; // Replace with actual password

async function authenticate() {
  console.log('\n' + '='.repeat(60));
  console.log('AUTHENTICATION');
  console.log('='.repeat(60) + '\n');

  console.log('🔐 Attempting sign in...');

  const { data, error } = await supabase.auth.signInWithPassword({
    email: TEST_EMAIL,
    password: TEST_PASSWORD,
  });

  if (error) {
    console.error('❌ Sign in failed:', error.message);
    console.log('\n⚠️  Cannot proceed without authentication.');
    console.log('   Please provide valid test credentials or run queries via browser console.\n');
    return false;
  }

  console.log('✅ Authenticated as:', data.user?.email);
  console.log('   User ID:', data.user?.id);
  console.log('   JWT claims:', data.user?.user_metadata);

  return true;
}

async function exploreDocumentChunksAuth() {
  console.log('\n' + '='.repeat(60));
  console.log('DOCUMENT CHUNKS (Authenticated)');
  console.log('='.repeat(60) + '\n');

  const { data: chunks, error } = await supabase
    .from('search_document_chunks')
    .select('id, document_id, storage_path, section_title, yacht_id')
    .limit(5);

  if (error) {
    console.error('❌ Error:', error.message);
    return;
  }

  console.log(`✅ Found ${chunks.length} chunk(s):\n`);
  chunks.forEach((chunk: any, i) => {
    console.log(`  [${i + 1}] Document ID: ${chunk.document_id}`);
    console.log(`      Storage Path: ${chunk.storage_path || '❌ NULL'}`);
    console.log(`      Yacht ID: ${chunk.yacht_id}\n`);
  });
}

async function testSpecificDocAuth() {
  console.log('='.repeat(60));
  console.log('SPECIFIC DOCUMENT (e4144864-1a61-4f21-ba0d-01ec97f012fb)');
  console.log('='.repeat(60) + '\n');

  const docId = 'e4144864-1a61-4f21-ba0d-01ec97f012fb';

  const { data: chunks, error } = await supabase
    .from('search_document_chunks')
    .select('*')
    .eq('document_id', docId)
    .limit(1);

  if (error) {
    console.error('❌ Error:', error.message);
  } else if (chunks && chunks.length > 0) {
    console.log('✅ Found chunk:');
    console.log(JSON.stringify(chunks[0], null, 2));
  } else {
    console.log('⚠️  No chunks found');
  }
}

async function main() {
  console.log('\n╔═══════════════════════════════════════════════════════════╗');
  console.log('║       AUTHENTICATED SUPABASE EXPLORATION                  ║');
  console.log('╚═══════════════════════════════════════════════════════════╝');

  const authenticated = await authenticate();

  if (!authenticated) {
    console.log('\n💡 Alternative: Run this in browser console while logged in:');
    console.log('```');
    console.log('const { data } = await supabase.from("search_document_chunks")');
    console.log('  .select("id, document_id, storage_path, yacht_id").limit(5);');
    console.log('console.table(data);');
    console.log('```\n');
    return;
  }

  await exploreDocumentChunksAuth();
  await testSpecificDocAuth();

  console.log('\n' + '='.repeat(60));
  console.log('COMPLETE');
  console.log('='.repeat(60) + '\n');
}

main().catch(console.error);
