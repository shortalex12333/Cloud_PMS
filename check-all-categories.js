#!/usr/bin/env node

const SUPABASE_URL = 'https://vzsohavtuotocgrfkfyd.supabase.co';
const SERVICE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ6c29oYXZ0dW90b2NncmZrZnlkIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MzU5Mjg3NSwiZXhwIjoyMDc5MTY4ODc1fQ.fC7eC_4xGnCHIebPzfaJ18pFMPKgImE7BuN0I3A-pSY';

async function checkCategories() {
  const yacht_id = '85fe1119-b04c-41ac-80f1-829d23322598';

  console.log('Checking all category folders in storage...\n');

  // List all folders under yacht_id
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
        prefix: `${yacht_id}/`,
        limit: 100,
        offset: 0,
        sortBy: { column: 'name', order: 'asc' }
      })
    }
  );

  const folders = await rootResponse.json();
  console.log(`Found ${folders.length} category folders:\n`);

  const categories = folders.filter(f => !f.id).map(f => f.name);
  categories.forEach(cat => console.log(`  📁 ${cat}`));

  // Now check doc_metadata to see which categories IT expects
  console.log('\n\nChecking which categories doc_metadata references...\n');

  const dbResponse = await fetch(
    `${SUPABASE_URL}/rest/v1/doc_metadata?select=storage_path&limit=100`,
    {
      headers: {
        'Authorization': `Bearer ${SERVICE_KEY}`,
        'apikey': SERVICE_KEY,
      }
    }
  );

  const docs = await dbResponse.json();

  // Extract category from paths
  const dbCategories = {};
  docs.forEach(doc => {
    const match = doc.storage_path.match(/documents\/[^/]+\/([^/]+)\//);
    if (match) {
      const category = match[1];
      dbCategories[category] = (dbCategories[category] || 0) + 1;
    }
  });

  console.log('Categories in doc_metadata (sample of 100):');
  Object.entries(dbCategories)
    .sort((a, b) => b[1] - a[1])
    .forEach(([cat, count]) => {
      const exists = categories.includes(cat);
      const icon = exists ? '✅' : '❌';
      console.log(`  ${icon} ${cat}: ${count} documents`);
    });

  // Check specific paths from doc_metadata
  console.log('\n\nTrying to access actual files from doc_metadata...\n');

  for (let i = 0; i < Math.min(5, docs.length); i++) {
    const doc = docs[i];
    let path = doc.storage_path;

    // Strip "documents/" prefix
    if (path.startsWith('documents/')) {
      path = path.substring('documents/'.length);
    }

    console.log(`Checking: ${path.substring(0, 60)}...`);

    // Try to create signed URL
    const signedUrlResponse = await fetch(
      `${SUPABASE_URL}/storage/v1/object/sign/documents/${path}`,
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

    if (signedUrlResponse.ok) {
      console.log('  ✅ EXISTS!\n');
    } else {
      const error = await signedUrlResponse.text();
      console.log(`  ❌ NOT FOUND: ${error}\n`);
    }
  }
}

checkCategories().catch(console.error);
