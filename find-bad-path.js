#!/usr/bin/env node

const SUPABASE_URL = 'https://vzsohavtuotocgrfkfyd.supabase.co';
const SERVICE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ6c29oYXZ0dW90b2NncmZrZnlkIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MzU5Mjg3NSwiZXhwIjoyMDc5MTY4ODc1fQ.fC7eC_4xGnCHIebPzfaJ18pFMPKgImE7BuN0I3A-pSY';

async function findBadPath() {
  console.log('Searching for the bad path from your error logs...\n');

  // Search for "Documents/01_Operations" pattern
  const badPathPattern = 'Documents/01_Operations';

  // Check search_document_chunks
  console.log('1. Checking search_document_chunks...');
  const chunksResponse = await fetch(
    `${SUPABASE_URL}/rest/v1/search_document_chunks?select=id,document_id,metadata&metadata->>storage_path=ilike.*${encodeURIComponent(badPathPattern)}*&limit=10`,
    {
      headers: {
        'Authorization': `Bearer ${SERVICE_KEY}`,
        'apikey': SERVICE_KEY,
      }
    }
  );

  let chunks = await chunksResponse.json();

  if (!Array.isArray(chunks) || chunks.length === 0) {
    // Try different search
    const chunksResponse2 = await fetch(
      `${SUPABASE_URL}/rest/v1/search_document_chunks?select=id,document_id,metadata&limit=1000`,
      {
        headers: {
          'Authorization': `Bearer ${SERVICE_KEY}`,
          'apikey': SERVICE_KEY,
        }
      }
    );

    const allChunks = await chunksResponse2.json();
    chunks = allChunks.filter(c =>
      c.metadata?.storage_path && c.metadata.storage_path.includes('Documents/01_Operations')
    );
  }

  console.log(`Found ${chunks.length} chunks with "Documents/01_Operations" in path\n`);

  if (chunks.length > 0) {
    console.log('❌ FOUND BAD CHUNKS:');
    chunks.forEach((chunk, i) => {
      console.log(`\n${i + 1}. Chunk ID: ${chunk.id}`);
      console.log(`   Document ID: ${chunk.document_id}`);
      console.log(`   Bad path: ${chunk.metadata?.storage_path}`);
    });
  } else {
    console.log('✅ No chunks found with that path pattern');
  }

  // Check doc_metadata
  console.log('\n2. Checking doc_metadata...');
  const docsResponse = await fetch(
    `${SUPABASE_URL}/rest/v1/doc_metadata?select=id,storage_path&storage_path=ilike.*${encodeURIComponent(badPathPattern)}*&limit=10`,
    {
      headers: {
        'Authorization': `Bearer ${SERVICE_KEY}`,
        'apikey': SERVICE_KEY,
      }
    }
  );

  const docs = await docsResponse.json();
  console.log(`Found ${docs.length} doc_metadata records with "Documents/01_Operations"\n`);

  if (docs.length > 0) {
    console.log('❌ FOUND BAD METADATA:');
    docs.forEach((doc, i) => {
      console.log(`\n${i + 1}. Doc ID: ${doc.id}`);
      console.log(`   Path: ${doc.storage_path}`);
    });
  } else {
    console.log('✅ No doc_metadata records with that path');
  }

  // Search for Raymarine_A_Series specifically
  console.log('\n3. Searching for "Raymarine_A_Series" filename...');

  const raymarine_search = await fetch(
    `${SUPABASE_URL}/rest/v1/search_document_chunks?select=id,document_id,metadata&metadata->>filename=ilike.*Raymarine_A_Series*&limit=5`,
    {
      headers: {
        'Authorization': `Bearer ${SERVICE_KEY}`,
        'apikey': SERVICE_KEY,
      }
    }
  );

  let raymarineChunks = await raymarine_search.json();

  if (!Array.isArray(raymarineChunks) || raymarineChunks.length === 0) {
    // Try text search
    const raymarine_text = await fetch(
      `${SUPABASE_URL}/rest/v1/search_document_chunks?select=id,document_id,metadata&content=ilike.*A_Series*&limit=5`,
      {
        headers: {
          'Authorization': `Bearer ${SERVICE_KEY}`,
          'apikey': SERVICE_KEY,
        }
      }
    );
    raymarineChunks = await raymarine_text.json();
  }

  console.log(`Found ${raymarineChunks.length} chunks related to "A_Series"\n`);

  if (raymarineChunks.length > 0) {
    raymarineChunks.forEach((chunk, i) => {
      console.log(`${i + 1}. ${chunk.metadata?.filename || 'Unknown'}`);
      console.log(`   Path: ${chunk.metadata?.storage_path || 'N/A'}`);
    });
  }
}

findBadPath().catch(console.error);
