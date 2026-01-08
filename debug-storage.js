#!/usr/bin/env node

/**
 * Debug Supabase Storage Configuration
 * Checks what buckets exist and what files are in them
 */

const SUPABASE_URL = 'https://qapnhmmyqkbxwbqxbdxq.supabase.co';
const SERVICE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InFhcG5obW15cWtieHdicXhiZHhxIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTczMDU2OTczNiwiZXhwIjoyMDQ2MTQ1NzM2fQ.pYqLc-1Mfqyo3NZRGO-5Q29x2gWVCCvWFoXDCXDgwQk';

async function checkStorage() {
  console.log('='.repeat(80));
  console.log('SUPABASE STORAGE DEBUG');
  console.log('='.repeat(80));

  // STEP 1: List all buckets
  console.log('\n📦 STEP 1: List all storage buckets');
  console.log('-'.repeat(80));

  const bucketsResponse = await fetch(`${SUPABASE_URL}/storage/v1/bucket`, {
    headers: {
      'Authorization': `Bearer ${SERVICE_KEY}`,
      'apikey': SERVICE_KEY
    }
  });

  if (!bucketsResponse.ok) {
    console.error(`❌ Failed to list buckets: ${bucketsResponse.status} ${bucketsResponse.statusText}`);
    const error = await bucketsResponse.text();
    console.error('Error:', error);
  } else {
    const buckets = await bucketsResponse.json();
    console.log(`✅ Found ${buckets.length} bucket(s):\n`);
    buckets.forEach(bucket => {
      console.log(`   - ${bucket.name} (public: ${bucket.public}, created: ${bucket.created_at})`);
    });

    // STEP 2: For each bucket, list files
    console.log('\n📁 STEP 2: List files in each bucket');
    console.log('-'.repeat(80));

    for (const bucket of buckets) {
      console.log(`\nBucket: ${bucket.name}`);

      // List files in root
      const filesResponse = await fetch(
        `${SUPABASE_URL}/storage/v1/object/list/${bucket.name}`,
        {
          headers: {
            'Authorization': `Bearer ${SERVICE_KEY}`,
            'apikey': SERVICE_KEY
          }
        }
      );

      if (!filesResponse.ok) {
        console.error(`  ❌ Failed to list files: ${filesResponse.status}`);
        const error = await filesResponse.text();
        console.error(`  Error:`, error);
      } else {
        const files = await filesResponse.json();
        console.log(`  Found ${files.length} items in root:`);
        files.slice(0, 10).forEach(file => {
          const type = file.id ? '📄 file' : '📁 folder';
          console.log(`    ${type}: ${file.name}`);
        });
        if (files.length > 10) {
          console.log(`    ... and ${files.length - 10} more items`);
        }
      }
    }
  }

  // STEP 3: Check the specific path from the error
  console.log('\n🔍 STEP 3: Check specific document path from error logs');
  console.log('-'.repeat(80));

  const testPath = 'documents/85fe1119-b04c-41ac-80f1-829d23322598/01_BRIDGE/Documents/01_Operations/Raymarine_A_Series_User_Manual.pdf';
  console.log(`Path: ${testPath}\n`);

  // Try to get file info
  const fileInfoResponse = await fetch(
    `${SUPABASE_URL}/storage/v1/object/info/public/${testPath}`,
    {
      headers: {
        'Authorization': `Bearer ${SERVICE_KEY}`,
        'apikey': SERVICE_KEY
      }
    }
  );

  if (!fileInfoResponse.ok) {
    console.log(`❌ File not found: ${fileInfoResponse.status} ${fileInfoResponse.statusText}`);
  } else {
    const fileInfo = await fileInfoResponse.json();
    console.log('✅ File found!');
    console.log(JSON.stringify(fileInfo, null, 2));
  }

  // STEP 4: Query database to see what storage_paths exist
  console.log('\n💾 STEP 4: Check storage_paths in doc_metadata table');
  console.log('-'.repeat(80));

  const dbResponse = await fetch(
    `${SUPABASE_URL}/rest/v1/doc_metadata?select=storage_path&limit=10`,
    {
      headers: {
        'Authorization': `Bearer ${SERVICE_KEY}`,
        'apikey': SERVICE_KEY,
        'Content-Type': 'application/json'
      }
    }
  );

  if (!dbResponse.ok) {
    console.error(`❌ Failed to query database: ${dbResponse.status}`);
  } else {
    const docs = await dbResponse.json();
    console.log(`Found ${docs.length} documents in database:\n`);
    docs.forEach((doc, i) => {
      console.log(`  ${i + 1}. ${doc.storage_path}`);
    });
  }

  console.log('\n' + '='.repeat(80));
  console.log('INVESTIGATION COMPLETE');
  console.log('='.repeat(80));
}

checkStorage().catch(error => {
  console.error('Fatal error:', error);
  process.exit(1);
});
