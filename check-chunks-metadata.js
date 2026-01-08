#!/usr/bin/env node

const SUPABASE_URL = 'https://vzsohavtuotocgrfkfyd.supabase.co';
const SERVICE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ6c29oYXZ0dW90b2NncmZrZnlkIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MzU5Mjg3NSwiZXhwIjoyMDc5MTY4ODc1fQ.fC7eC_4xGnCHIebPzfaJ18pFMPKgImE7BuN0I3A-pSY';

async function checkChunks() {
  console.log('Checking search_document_chunks metadata field...\n');

  // Get a few chunks that mention Raymarine
  const response = await fetch(
    `${SUPABASE_URL}/rest/v1/search_document_chunks?select=id,document_id,metadata,content&content=ilike.*Raymarine*&limit=5`,
    {
      headers: {
        'Authorization': `Bearer ${SERVICE_KEY}`,
        'apikey': SERVICE_KEY,
      }
    }
  );

  const chunks = await response.json();

  console.log(`Found ${chunks.length} chunks mentioning "Raymarine"\n`);

  for (const chunk of chunks) {
    console.log('='.repeat(80));
    console.log(`Chunk ID: ${chunk.id}`);
    console.log(`Document ID: ${chunk.document_id}`);
    console.log(`Content: ${chunk.content.substring(0, 100)}...`);
    console.log(`\nMetadata field:`);
    console.log(JSON.stringify(chunk.metadata, null, 2));

    // Check if metadata contains storage_path
    if (chunk.metadata?.storage_path) {
      console.log(`\n⚠️  Chunk metadata contains storage_path: ${chunk.metadata.storage_path}`);

      // Verify against doc_metadata
      const docResponse = await fetch(
        `${SUPABASE_URL}/rest/v1/doc_metadata?select=storage_path&id=eq.${chunk.document_id}`,
        {
          headers: {
            'Authorization': `Bearer ${SERVICE_KEY}`,
            'apikey': SERVICE_KEY,
          }
        }
      );

      const docs = await docResponse.json();
      if (docs.length > 0) {
        console.log(`doc_metadata storage_path: ${docs[0].storage_path}`);

        if (chunk.metadata.storage_path !== docs[0].storage_path) {
          console.log('❌ MISMATCH! Chunk metadata has different path than doc_metadata');
        } else {
          console.log('✅ Paths match');
        }
      }
    } else {
      console.log('\nℹ️  Chunk metadata does NOT contain storage_path');
    }

    console.log('');
  }

  // Check the schema of search_document_chunks
  console.log('\n' + '='.repeat(80));
  console.log('Checking search_document_chunks table schema...\n');

  const schemaResponse = await fetch(
    `${SUPABASE_URL}/rest/v1/search_document_chunks?select=*&limit=1`,
    {
      headers: {
        'Authorization': `Bearer ${SERVICE_KEY}`,
        'apikey': SERVICE_KEY,
      }
    }
  );

  const sample = await schemaResponse.json();
  if (sample.length > 0) {
    console.log('Columns in search_document_chunks:');
    Object.keys(sample[0]).forEach(col => {
      console.log(`  - ${col}: ${typeof sample[0][col]}`);
    });
  }
}

checkChunks().catch(console.error);
