#!/usr/bin/env node

const SUPABASE_URL = 'https://vzsohavtuotocgrfkfyd.supabase.co';
const SERVICE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ6c29oYXZ0dW90b2NncmZrZnlkIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MzU5Mjg3NSwiZXhwIjoyMDc5MTY4ODc1fQ.fC7eC_4xGnCHIebPzfaJ18pFMPKgImE7BuN0I3A-pSY';

async function checkErrorPath() {
  // From user's error logs:
  // storage_path from doc_metadata: "documents/85fe1119.../01_BRIDGE/Documents/01_Operations/Raymarine_A_Series_User_Manual.pdf"
  // After strip: "85fe1119.../01_BRIDGE/Documents/01_Operations/Raymarine_A_Series_User_Manual.pdf"

  const yacht_id = '85fe1119-b04c-41ac-80f1-829d23322598';

  console.log('Checking the SPECIFIC path from your error logs...\n');

  // Path that failed
  const errorPath = `${yacht_id}/01_BRIDGE/Documents/01_Operations/Raymarine_A_Series_User_Manual.pdf`;

  console.log('Testing path:', errorPath, '\n');

  const response = await fetch(
    `${SUPABASE_URL}/storage/v1/object/sign/documents/${errorPath}`,
    {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${SERVICE_KEY}`,
        'apikey': SERVICE_KEY,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        expiresIn: 60
      })
    }
  );

  if (response.ok) {
    const data = await response.json();
    console.log('✅ FILE EXISTS!');
    console.log('Signed URL:', data.signedUrl);
  } else {
    console.log('❌ FILE DOES NOT EXIST');
    const error = await response.text();
    console.log('Error:', error);

    // Check if Documents folder exists
    console.log('\nChecking if "Documents" folder exists in 01_BRIDGE...');

    const docsCheck = await fetch(
      `${SUPABASE_URL}/storage/v1/object/list/documents`,
      {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${SERVICE_KEY}`,
          'apikey': SERVICE_KEY,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          prefix: `${yacht_id}/01_BRIDGE/`,
          limit: 100,
          offset: 0
        })
      }
    );

    const items = await docsCheck.json();
    console.log(`\nFolders in 01_BRIDGE (${items.length} items):`);

    const folders = items.filter(i => !i.id);
    folders.forEach(f => console.log(`  📁 ${f.name}`));

    const hasDocuments = folders.some(f => f.name === 'Documents');
    if (!hasDocuments) {
      console.log('\n❌ "Documents" folder does NOT exist in 01_BRIDGE');
      console.log('   This is why that specific file cannot be found!');
    }
  }

  // Now let's find the actual document_id that's failing
  console.log('\n\nSearching for this path in doc_metadata...\n');

  const searchPath = `documents/${errorPath}`;
  const dbResponse = await fetch(
    `${SUPABASE_URL}/rest/v1/doc_metadata?select=id,storage_path&storage_path=eq.${encodeURIComponent(searchPath)}`,
    {
      headers: {
        'Authorization': `Bearer ${SERVICE_KEY}`,
        'apikey': SERVICE_KEY,
      }
    }
  );

  const docs = await dbResponse.json();

  if (docs.length === 0) {
    console.log('No doc_metadata record found with that exact path');

    // Search for Raymarine in chunks
    console.log('\nSearching for "Raymarine" in search_document_chunks...');

    const chunksResponse = await fetch(
      `${SUPABASE_URL}/rest/v1/search_document_chunks?select=id,document_id&content=ilike.*Raymarine*&limit=5`,
      {
        headers: {
          'Authorization': `Bearer ${SERVICE_KEY}`,
          'apikey': SERVICE_KEY,
        }
      }
    );

    const chunks = await chunksResponse.json();
    console.log(`Found ${chunks.length} chunks mentioning Raymarine`);

    if (chunks.length > 0) {
      const docId = chunks[0].document_id;
      console.log(`Document ID: ${docId}`);

      // Get the actual storage path
      const docResponse = await fetch(
        `${SUPABASE_URL}/rest/v1/doc_metadata?select=storage_path&id=eq.${docId}`,
        {
          headers: {
            'Authorization': `Bearer ${SERVICE_KEY}`,
            'apikey': SERVICE_KEY,
          }
        }
      );

      const docData = await docResponse.json();
      if (docData.length > 0) {
        console.log(`Actual storage_path: ${docData[0].storage_path}`);
      }
    }
  } else {
    console.log(`Found ${docs.length} doc_metadata record(s) with that path:`);
    docs.forEach(doc => {
      console.log(`  ID: ${doc.id}`);
      console.log(`  Path: ${doc.storage_path}`);
    });
  }
}

checkErrorPath().catch(console.error);
