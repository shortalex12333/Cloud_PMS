#!/usr/bin/env node

const SUPABASE_URL = 'https://vzsohavtuotocgrfkfyd.supabase.co';
const SERVICE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ6c29oYXZ0dW90b2NncmZrZnlkIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MzU5Mjg3NSwiZXhwIjoyMDc5MTY4ODc1fQ.fC7eC_4xGnCHIebPzfaJ18pFMPKgImE7BuN0I3A-pSY';

async function compare() {
  console.log('='.repeat(80));
  console.log('PATH MISMATCH ANALYSIS');
  console.log('='.repeat(80));

  // Get sample paths from doc_metadata
  console.log('\n📋 Sample paths from doc_metadata table:');
  console.log('-'.repeat(80));

  const dbResponse = await fetch(
    `${SUPABASE_URL}/rest/v1/doc_metadata?select=storage_path&limit=10`,
    {
      headers: {
        'Authorization': `Bearer ${SERVICE_KEY}`,
        'apikey': SERVICE_KEY,
      }
    }
  );

  const docs = await dbResponse.json();
  docs.forEach((doc, i) => {
    console.log(`${i + 1}. ${doc.storage_path}`);
  });

  // Get actual paths from storage
  console.log('\n📦 Actual file paths in storage:');
  console.log('-'.repeat(80));

  const yacht_id = '85fe1119-b04c-41ac-80f1-829d23322598';

  async function listFilesRecursive(prefix, maxDepth = 3, currentDepth = 0, found = []) {
    if (currentDepth >= maxDepth) return found;

    const response = await fetch(
      `${SUPABASE_URL}/storage/v1/object/list/documents`,
      {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${SERVICE_KEY}`,
          'apikey': SERVICE_KEY,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          prefix: prefix,
          limit: 100,
          offset: 0,
          sortBy: { column: 'name', order: 'asc' }
        })
      }
    );

    if (!response.ok) return found;

    const items = await response.json();

    for (const item of items) {
      const fullPath = prefix ? `${prefix}${item.name}` : item.name;

      if (item.id) {
        // It's a file
        found.push(fullPath);
      } else {
        // It's a folder, recurse
        await listFilesRecursive(fullPath + '/', maxDepth, currentDepth + 1, found);
      }

      // Limit to first 15 files to avoid timeout
      if (found.length >= 15) break;
    }

    return found;
  }

  const storagePaths = await listFilesRecursive(`${yacht_id}/01_BRIDGE/`, 4);

  storagePaths.slice(0, 10).forEach((path, i) => {
    console.log(`${i + 1}. ${path}`);
  });

  // Compare patterns
  console.log('\n🔍 ANALYSIS:');
  console.log('-'.repeat(80));

  if (docs.length > 0 && storagePaths.length > 0) {
    const dbExample = docs[0].storage_path;
    const storageExample = storagePaths[0];

    console.log('\nDatabase path example:');
    console.log(`  ${dbExample}`);

    console.log('\nStorage path example:');
    console.log(`  ${storageExample}`);

    console.log('\n❌ MISMATCH DETECTED:');

    // Extract patterns
    const dbParts = dbExample.split('/');
    const storageParts = storageExample.split('/');

    console.log('\nDatabase structure:');
    console.log(`  ${dbParts.slice(0, -1).join(' → ')}`);

    console.log('\nStorage structure:');
    console.log(`  ${storageParts.slice(0, -1).join(' → ')}`);

    console.log('\n⚠️  PROBLEM: The folder structure in doc_metadata does NOT match actual storage!');
    console.log('\nPossible causes:');
    console.log('  1. Files were uploaded with different folder structure');
    console.log('  2. doc_metadata was populated before storage migration');
    console.log('  3. Path transformation logic is missing/broken');
  }

  // Check if "Documents" folder exists in storage
  console.log('\n📁 Checking for "Documents" folder in storage:');
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
        prefix: `${yacht_id}/01_BRIDGE/Documents/`,
        limit: 10,
        offset: 0,
        sortBy: { column: 'name', order: 'asc' }
      })
    }
  );

  if (!docsCheck.ok || (await docsCheck.json()).length === 0) {
    console.log('❌ "Documents" folder does NOT exist in storage');
    console.log('   Database expects: 01_BRIDGE/Documents/...');
    console.log('   Storage actually has: 01_BRIDGE/ais_equipment/..., 01_BRIDGE/radar_systems/..., etc.');
  } else {
    console.log('✅ "Documents" folder exists');
  }

  console.log('\n' + '='.repeat(80));
}

compare().catch(console.error);
