#!/usr/bin/env node

const SUPABASE_URL = 'https://vzsohavtuotocgrfkfyd.supabase.co';
const SERVICE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ6c29oYXZ0dW90b2NncmZrZnlkIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MzU5Mjg3NSwiZXhwIjoyMDc5MTY4ODc1fQ.fC7eC_4xGnCHIebPzfaJ18pFMPKgImE7BuN0I3A-pSY';

async function listFolder(prefix, depth = 0) {
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
        limit: 1000,
        offset: 0,
        sortBy: { column: 'name', order: 'asc' }
      })
    }
  );

  if (!response.ok) {
    return [];
  }

  const files = await response.json();
  return files;
}

async function findPDFs() {
  const yacht_id = '85fe1119-b04c-41ac-80f1-829d23322598';

  console.log('Searching for PDF files in storage...\n');

  // Check 01_BRIDGE category
  const bridgePrefix = `${yacht_id}/01_BRIDGE/`;
  console.log(`Checking: ${bridgePrefix}`);

  const bridgeItems = await listFolder(bridgePrefix);
  console.log(`Found ${bridgeItems.length} items in 01_BRIDGE`);

  // Look for subfolders
  const subfolders = bridgeItems.filter(item => !item.id);
  console.log(`  Subfolders: ${subfolders.map(f => f.name).join(', ')}`);

  if (subfolders.length > 0) {
    // Check first subfolder in detail
    const firstSubfolder = subfolders[0].name;
    const subfolderPrefix = `${yacht_id}/01_BRIDGE/${firstSubfolder}/`;
    console.log(`\nExploring: ${subfolderPrefix}`);

    const subfolderItems = await listFolder(subfolderPrefix);
    console.log(`Found ${subfolderItems.length} items:`);

    subfolderItems.forEach(item => {
      const type = item.id ? '📄 FILE' : '📁 FOLDER';
      console.log(`  ${type}: ${item.name}${item.id ? ` (${item.metadata?.size || 0} bytes)` : ''}`);
    });

    // If there are more folders, go deeper
    const deeperFolders = subfolderItems.filter(item => !item.id);
    if (deeperFolders.length > 0) {
      const deeperFolder = deeperFolders[0].name;
      const deeperPrefix = `${yacht_id}/01_BRIDGE/${firstSubfolder}/${deeperFolder}/`;
      console.log(`\nGoing deeper: ${deeperPrefix}`);

      const deeperItems = await listFolder(deeperPrefix);
      console.log(`Found ${deeperItems.length} items:`);

      deeperItems.slice(0, 20).forEach(item => {
        const type = item.id ? '📄 FILE' : '📁 FOLDER';
        const size = item.metadata?.size ? `${(item.metadata.size / 1024).toFixed(1)}KB` : '';
        console.log(`  ${type}: ${item.name} ${size}`);
      });
    }
  }

  // Now check the specific path from the error
  console.log('\n\nTrying to access specific file from error logs:');
  const errorPath = `${yacht_id}/01_BRIDGE/Documents/01_Operations/Raymarine_A_Series_User_Manual.pdf`;
  console.log(`Path: ${errorPath}\n`);

  // Try to get signed URL
  const { createClient } = await import('@supabase/supabase-js');
  const supabase = createClient(SUPABASE_URL, SERVICE_KEY);

  const { data, error } = await supabase.storage
    .from('documents')
    .createSignedUrl(errorPath, 60);

  if (error) {
    console.error('❌ File does NOT exist');
    console.error('Error:', error.message);

    // Try listing the parent folder
    console.log('\nTrying parent folder: 01_BRIDGE/Documents/01_Operations/');
    const parentPrefix = `${yacht_id}/01_BRIDGE/Documents/01_Operations/`;
    const parentItems = await listFolder(parentPrefix);
    console.log(`Found ${parentItems.length} items in parent folder:`);
    parentItems.forEach(item => {
      console.log(`  - ${item.name}`);
    });
  } else {
    console.log('✅ File EXISTS!');
    console.log('Signed URL:', data.signedUrl);
  }

  // Count total files recursively
  console.log('\n\nCounting all files in storage (this may take a moment)...');
  let totalFiles = 0;
  let totalFolders = 0;

  for (const category of ['01_BRIDGE', '02_ENGINEERING', '05_GALLEY', '06_SYSTEMS']) {
    const catPrefix = `${yacht_id}/${category}/`;
    const items = await listFolder(catPrefix);

    const files = items.filter(i => i.id);
    const folders = items.filter(i => !i.id);

    totalFiles += files.length;
    totalFolders += folders.length;

    console.log(`  ${category}: ${files.length} files, ${folders.length} folders`);
  }

  console.log(`\nTotal: ~${totalFiles} files found in sampled categories`);
}

findPDFs().catch(console.error);
