/**
 * Supabase Storage and Security Exploration Script
 *
 * Run with: npx tsx scripts/explore-storage.ts
 */

import { createClient } from '@supabase/supabase-js';

// Hardcoded for exploration - from deployment config
const SUPABASE_URL = 'https://vzsohavtuotocgrfkfyd.supabase.co';
const SUPABASE_ANON_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ6c29oYXZ0dW90b2NncmZreWQiLCJyb2xlIjoiYW5vbiIsImlhdCI6MTczMzg0NDM1MSwiZXhwIjoyMDQ5NDIwMzUxfQ.kfB7BzQDiQYAJZ_aOVODaR0qgxQ2tgHC_f9aUJ09fRI';

console.log('Using Supabase URL:', SUPABASE_URL);
console.log('Anon key (first 20 chars):', SUPABASE_ANON_KEY.substring(0, 20) + '...');

const supabase = createClient(SUPABASE_URL, SUPABASE_ANON_KEY);

async function exploreBuckets() {
  console.log('\n' + '='.repeat(60));
  console.log('1. STORAGE BUCKETS');
  console.log('='.repeat(60) + '\n');

  const { data: buckets, error } = await supabase.storage.listBuckets();

  if (error) {
    console.error('❌ Error:', error.message);
    return;
  }

  console.log(`✅ Found ${buckets.length} bucket(s):\n`);
  buckets.forEach(bucket => {
    console.log(`  📦 ${bucket.name}`);
    console.log(`     ID: ${bucket.id}`);
    console.log(`     Public: ${bucket.public}`);
    console.log(`     Created: ${bucket.created_at}\n`);
  });
}

async function exploreDocumentChunks() {
  console.log('='.repeat(60));
  console.log('2. DOCUMENT CHUNKS (search_document_chunks)');
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
    console.log(`  [${i + 1}] Chunk ID: ${chunk.id.substring(0, 8)}...`);
    console.log(`      Document ID: ${chunk.document_id.substring(0, 8)}...`);
    console.log(`      Yacht ID: ${chunk.yacht_id?.substring(0, 8)}...`);
    console.log(`      Storage Path: ${chunk.storage_path || '❌ NULL'}`);
    console.log(`      Section: ${chunk.section_title || 'N/A'}\n`);
  });
}

async function exploreDocMetadata() {
  console.log('='.repeat(60));
  console.log('3. DOCUMENT METADATA (doc_metadata)');
  console.log('='.repeat(60) + '\n');

  const { data: docs, error } = await supabase
    .from('doc_metadata')
    .select('id, yacht_id, title, storage_path, file_path, classification')
    .limit(5);

  if (error) {
    console.error('❌ Error:', error.message);
    return;
  }

  console.log(`✅ Found ${docs.length} document(s):\n`);
  docs.forEach((doc: any, i) => {
    console.log(`  [${i + 1}] Doc ID: ${doc.id.substring(0, 8)}...`);
    console.log(`      Yacht ID: ${doc.yacht_id?.substring(0, 8)}...`);
    console.log(`      Title: ${doc.title || 'N/A'}`);
    console.log(`      Storage Path: ${doc.storage_path || '❌ NULL'}`);
    console.log(`      File Path: ${doc.file_path || '❌ NULL'}`);
    console.log(`      Classification: ${doc.classification || 'N/A'}\n`);
  });
}

async function testSpecificDocument() {
  console.log('='.repeat(60));
  console.log('4. SPECIFIC DOCUMENT TEST');
  console.log('='.repeat(60) + '\n');

  const testDocId = 'e4144864-1a61-4f21-ba0d-01ec97f012fb';
  console.log(`🔍 Searching for document: ${testDocId}\n`);

  // Search in chunks
  const { data: chunks, error: chunkError } = await supabase
    .from('search_document_chunks')
    .select('*')
    .eq('document_id', testDocId)
    .limit(1);

  if (chunkError) {
    console.log('  ⚠️  Not in search_document_chunks:', chunkError.message);
  } else if (chunks && chunks.length > 0) {
    console.log('  ✅ Found in search_document_chunks:');
    console.log('     Storage Path:', chunks[0].storage_path || '❌ NULL');
    console.log('     Yacht ID:', chunks[0].yacht_id);
    console.log('     Full record:', JSON.stringify(chunks[0], null, 6));
  } else {
    console.log('  ⚠️  No chunks found for this document');
  }

  console.log();

  // Search in doc_metadata
  const { data: doc, error: docError } = await supabase
    .from('doc_metadata')
    .select('*')
    .eq('id', testDocId)
    .single();

  if (docError) {
    console.log('  ⚠️  Not in doc_metadata:', docError.message);
  } else if (doc) {
    console.log('  ✅ Found in doc_metadata:');
    console.log('     Storage Path:', doc.storage_path || '❌ NULL');
    console.log('     File Path:', doc.file_path || '❌ NULL');
    console.log('     Yacht ID:', doc.yacht_id);
    console.log('     Full record:', JSON.stringify(doc, null, 6));
  }
}

async function testStorageListing() {
  console.log('\n' + '='.repeat(60));
  console.log('5. STORAGE FILE LISTING (documents bucket)');
  console.log('='.repeat(60) + '\n');

  // Try listing root
  const { data: rootFiles, error: rootError } = await supabase.storage
    .from('documents')
    .list('', { limit: 20 });

  if (rootError) {
    console.log('  ⚠️  Cannot list root (might need auth):', rootError.message);
  } else {
    console.log(`  ✅ Root level (${rootFiles.length} items):\n`);
    rootFiles.forEach((file: any) => {
      const type = file.id ? '📄' : '📁';
      console.log(`     ${type} ${file.name}`);
    });
  }

  // Try listing a yacht folder (if we know one)
  console.log('\n  Trying yacht_85fe1119-b04c-41ac-80f1-829d23322598...\n');
  const { data: yachtFiles, error: yachtError } = await supabase.storage
    .from('documents')
    .list('yacht_85fe1119-b04c-41ac-80f1-829d23322598', { limit: 20 });

  if (yachtError) {
    console.log('  ⚠️  Cannot list yacht folder:', yachtError.message);
  } else {
    console.log(`  ✅ Yacht folder (${yachtFiles.length} items):\n`);
    yachtFiles.forEach((file: any) => {
      const type = file.id ? '📄' : '📁';
      console.log(`     ${type} ${file.name}`);
    });
  }
}

async function testSignedURL() {
  console.log('\n' + '='.repeat(60));
  console.log('6. SIGNED URL TEST');
  console.log('='.repeat(60) + '\n');

  const testPaths = [
    'yacht_85fe1119-b04c-41ac-80f1-829d23322598/documents/e4144864-1a61-4f21-ba0d-01ec97f012fb',
    'yacht_85fe1119-b04c-41ac-80f1-829d23322598/manuals/test.pdf',
    'documents/e4144864-1a61-4f21-ba0d-01ec97f012fb',
  ];

  for (const path of testPaths) {
    console.log(`  Testing: ${path}`);
    const { data, error } = await supabase.storage
      .from('documents')
      .createSignedUrl(path, 60);

    if (error) {
      console.log(`  ❌ Error: ${error.message}\n`);
    } else {
      console.log(`  ✅ Success! URL: ${data.signedUrl.substring(0, 80)}...\n`);
    }
  }
}

async function main() {
  console.log('\n╔═══════════════════════════════════════════════════════════╗');
  console.log('║          SUPABASE STORAGE & SECURITY EXPLORATION          ║');
  console.log('╚═══════════════════════════════════════════════════════════╝\n');

  await exploreBuckets();
  await exploreDocumentChunks();
  await exploreDocMetadata();
  await testSpecificDocument();
  await testStorageListing();
  await testSignedURL();

  console.log('\n' + '='.repeat(60));
  console.log('EXPLORATION COMPLETE');
  console.log('='.repeat(60) + '\n');
}

main().catch(console.error);
