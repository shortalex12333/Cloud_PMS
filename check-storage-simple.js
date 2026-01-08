#!/usr/bin/env node

const SUPABASE_URL = 'https://vzsohavtuotocgrfkfyd.supabase.co';
const SERVICE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ6c29oYXZ0dW90b2NncmZrZnlkIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MzU5Mjg3NSwiZXhwIjoyMDc5MTY4ODc1fQ.fC7eC_4xGnCHIebPzfaJ18pFMPKgImE7BuN0I3A-pSY';

async function checkStorage() {
  console.log('Checking storage bucket contents...\n');

  // Try to list root of documents bucket
  console.log('1. List root of documents bucket:');
  const rootResponse = await fetch(
    `${SUPABASE_URL}/storage/v1/object/list/documents`,
    {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${SERVICE_KEY}`,
        'apikey': SERVICE_KEY,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        prefix: '',
        limit: 100,
        offset: 0,
        sortBy: { column: 'name', order: 'asc' }
      })
    }
  );

  if (!rootResponse.ok) {
    console.error(`❌ Error: ${rootResponse.status} ${rootResponse.statusText}`);
    const error = await rootResponse.text();
    console.error('Response:', error);
  } else {
    const files = await rootResponse.json();
    console.log(`✅ Found ${files.length} items in root`);

    if (files.length === 0) {
      console.log('\n⚠️  BUCKET IS EMPTY - No files uploaded yet!');
    } else {
      console.log('\nItems:');
      files.forEach(f => {
        const type = f.id ? '📄' : '📁';
        console.log(`  ${type} ${f.name}`);
      });

      // If we found folders, try to list first folder
      const folders = files.filter(f => !f.id);
      if (folders.length > 0) {
        const firstFolder = folders[0].name;
        console.log(`\n2. List contents of first folder (${firstFolder}):`);

        const folderResponse = await fetch(
          `${SUPABASE_URL}/storage/v1/object/list/documents`,
          {
            method: 'POST',
            headers: {
              'Authorization': `Bearer ${SERVICE_KEY}`,
              'apikey': SERVICE_KEY,
              'Content-Type': 'application/json'
            },
            body: JSON.stringify({
              prefix: firstFolder + '/',
              limit: 100,
              offset: 0,
              sortBy: { column: 'name', order: 'asc' }
            })
          }
        );

        if (!folderResponse.ok) {
          console.error(`❌ Error: ${folderResponse.status}`);
        } else {
          const folderFiles = await folderResponse.json();
          console.log(`✅ Found ${folderFiles.length} items`);
          folderFiles.slice(0, 10).forEach(f => {
            const type = f.id ? '📄' : '📁';
            console.log(`  ${type} ${f.name}`);
          });
        }
      }
    }
  }

  // Check how many doc_metadata records exist
  console.log('\n3. Count doc_metadata records:');
  const countResponse = await fetch(
    `${SUPABASE_URL}/rest/v1/doc_metadata?select=id&limit=1`,
    {
      headers: {
        'Authorization': `Bearer ${SERVICE_KEY}`,
        'apikey': SERVICE_KEY,
        'Prefer': 'count=exact'
      }
    }
  );

  const count = countResponse.headers.get('content-range');
  console.log(`Total documents in database: ${count}`);
}

checkStorage().catch(console.error);
