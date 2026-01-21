const { createClient } = require('@supabase/supabase-js');
const fs = require('fs');

const TENANT_SUPABASE_URL = 'https://vzsohavtuotocgrfkfyd.supabase.co';
const TENANT_SERVICE_KEY = process.env.TENANT_SUPABASE_SERVICE_ROLE_KEY;

if (!TENANT_SERVICE_KEY) {
  console.log('ERROR: TENANT_SUPABASE_SERVICE_ROLE_KEY not set');
  process.exit(1);
}

const supabase = createClient(TENANT_SUPABASE_URL, TENANT_SERVICE_KEY);

async function checkDocuments() {
  console.log('=== Checking Documents ===\n');

  // 1. List buckets
  console.log('1. Listing storage buckets...');
  const { data: buckets, error: bucketsError } = await supabase.storage.listBuckets();

  if (bucketsError) {
    console.log('Error listing buckets:', bucketsError.message);
  } else {
    console.log('Buckets found:', buckets?.length || 0);
    buckets?.forEach(b => {
      console.log(`  - ${b.name} (public: ${b.public}, created: ${b.created_at})`);
    });
  }

  // 2. Check documents metadata table
  console.log('\n2. Checking documents metadata table...');
  const { data: docsMeta, error: docsMetaError, count } = await supabase
    .from('documents')
    .select('*', { count: 'exact' })
    .limit(10);

  if (docsMetaError) {
    console.log('Error querying documents table:', docsMetaError.message);
    // Try alternate table names
    const alternateNames = ['yacht_documents', 'crew_documents', 'vessel_documents', 'files'];
    for (const tableName of alternateNames) {
      const { data, error } = await supabase.from(tableName).select('*').limit(1);
      if (!error && data) {
        console.log(`  Found alternate table: ${tableName}`);
      }
    }
  } else {
    console.log('Document metadata records found:', count);
    console.log('Sample documents:');
    docsMeta?.slice(0, 5).forEach(d => {
      console.log(`  - ${d.name || d.filename || d.title || d.id} (${d.file_type || d.mime_type || 'unknown'})`);
    });
  }

  // 3. List files in storage bucket
  const bucketName = buckets?.[0]?.name || 'documents';
  console.log(`\n3. Listing files in '${bucketName}' bucket...`);

  const { data: files, error: filesError } = await supabase.storage
    .from(bucketName)
    .list('', { limit: 20, sortBy: { column: 'created_at', order: 'desc' } });

  if (filesError) {
    console.log('Error listing files:', filesError.message);
  } else {
    console.log('Files found in root:', files?.length || 0);
    files?.filter(f => f.name !== '.emptyFolderPlaceholder').slice(0, 10).forEach(f => {
      console.log(`  - ${f.name} (${f.metadata?.size || 'folder'})`);
    });

    // If they're folders, try to list inside
    const folders = files?.filter(f => !f.metadata?.mimetype);
    if (folders?.length > 0) {
      for (const folder of folders.slice(0, 3)) {
        const { data: subfiles } = await supabase.storage
          .from(bucketName)
          .list(folder.name, { limit: 10 });
        if (subfiles?.length > 0) {
          console.log(`  Files in ${folder.name}/: ${subfiles.length}`);
          subfiles.filter(f => f.name !== '.emptyFolderPlaceholder').slice(0, 3).forEach(sf => {
            console.log(`    - ${sf.name} (${sf.metadata?.size || 'folder'})`);
          });
        }
      }
    }
  }

  // 4. Get total file count recursively
  console.log('\n4. Counting total files...');
  let totalFiles = 0;
  const samplePaths = [];

  async function countFilesRecursive(path = '') {
    const { data: items } = await supabase.storage
      .from(bucketName)
      .list(path, { limit: 1000 });

    if (!items) return;

    for (const item of items) {
      if (item.name === '.emptyFolderPlaceholder') continue;

      const fullPath = path ? `${path}/${item.name}` : item.name;

      if (item.metadata?.mimetype) {
        totalFiles++;
        if (samplePaths.length < 10) {
          samplePaths.push(fullPath);
        }
      } else {
        // It's a folder, recurse
        await countFilesRecursive(fullPath);
      }
    }
  }

  await countFilesRecursive();
  console.log('Total files in bucket:', totalFiles);
  console.log('\nSample file paths:');
  samplePaths.forEach(p => console.log(`  - ${p}`));

  // Write evidence
  const evidence = {
    buckets: buckets?.map(b => ({ name: b.name, public: b.public })),
    documentMetadataCount: count,
    totalFilesInStorage: totalFiles,
    sampleFilePaths: samplePaths
  };

  fs.writeFileSync(
    '/Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS/verification_handoff/evidence/DOCUMENTS_storage_check.json',
    JSON.stringify(evidence, null, 2)
  );
  console.log('\nEvidence written to DOCUMENTS_storage_check.json');
}

checkDocuments();
