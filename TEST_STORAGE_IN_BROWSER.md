# Quick Storage Test (Run in Browser Console)

You can test storage immediately without waiting for deployment.

## Step 1: Open Browser Console

1. Go to your app: https://pms.alexshort.uk (or wherever it's deployed)
2. Open DevTools (F12 or Cmd+Option+I)
3. Go to Console tab

## Step 2: Paste and Run This Code

```javascript
// Quick storage diagnostic
(async function testStorage() {
  console.log('='.repeat(80));
  console.log('STORAGE DIAGNOSTIC TEST');
  console.log('='.repeat(80));

  // Get Supabase client from window (if available)
  // Or import it
  const { createClient } = await import('https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2/+esm');

  // Use your credentials
  const SUPABASE_URL = 'https://vzsohavtuotocgrfkfyd.supabase.co';
  const ANON_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ6c29oYXZ0dW90b2NncmZrZnlkIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjM1OTI4NzUsImV4cCI6MjA3OTE2ODg3NX0.JhJLvLSfLD3OtPDxTgHqgF8dNaZk8ius62jKN68E4WE';

  const supabase = createClient(SUPABASE_URL, ANON_KEY);

  // Test 1: List storage buckets
  console.log('\n📦 Test 1: List Storage Buckets');
  console.log('-'.repeat(80));
  const { data: buckets, error: bucketsError } = await supabase.storage.listBuckets();

  if (bucketsError) {
    console.error('❌ Error listing buckets:', bucketsError);
  } else {
    console.log(`✅ Found ${buckets.length} bucket(s):`);
    buckets.forEach(b => console.log(`   - ${b.name} (public: ${b.public})`));

    // Check if "documents" bucket exists
    const hasDocs = buckets.some(b => b.name === 'documents');
    if (!hasDocs) {
      console.error('\n❌ PROBLEM: "documents" bucket does NOT exist!');
      console.log('   → You need to create it in Supabase Dashboard → Storage');
    } else {
      console.log('\n✅ "documents" bucket exists');
    }
  }

  // Test 2: Check doc_metadata
  console.log('\n💾 Test 2: Check doc_metadata Table');
  console.log('-'.repeat(80));
  const { data: docs, error: docsError } = await supabase
    .from('doc_metadata')
    .select('id, storage_path')
    .limit(5);

  if (docsError) {
    console.error('❌ Error querying doc_metadata:', docsError);
  } else {
    console.log(`✅ Found ${docs.length} document(s) in metadata:`);
    docs.forEach((doc, i) => {
      console.log(`   ${i + 1}. ${doc.storage_path}`);
    });
  }

  // Test 3: Try to list files in documents bucket
  if (buckets && buckets.some(b => b.name === 'documents')) {
    console.log('\n📁 Test 3: List Files in "documents" Bucket');
    console.log('-'.repeat(80));

    const { data: files, error: filesError } = await supabase.storage
      .from('documents')
      .list('', { limit: 100 });

    if (filesError) {
      console.error('❌ Error listing files:', filesError);
    } else {
      console.log(`Found ${files.length} item(s) in root:`);
      if (files.length === 0) {
        console.error('❌ PROBLEM: Bucket is empty!');
        console.log('   → You need to upload PDF files to this bucket');
      } else {
        files.slice(0, 10).forEach(f => {
          const type = f.id ? '📄 file' : '📁 folder';
          console.log(`   ${type}: ${f.name}`);
        });
        if (files.length > 10) {
          console.log(`   ... and ${files.length - 10} more items`);
        }
      }
    }
  }

  // Test 4: Try to access specific file
  if (docs && docs.length > 0) {
    console.log('\n🔍 Test 4: Try to Access Specific File');
    console.log('-'.repeat(80));

    const testPath = docs[0].storage_path;
    console.log(`Testing: ${testPath}`);

    // Strip "documents/" prefix
    let pathToCheck = testPath;
    if (pathToCheck.startsWith('documents/')) {
      pathToCheck = pathToCheck.substring('documents/'.length);
    }

    const { data: signedUrl, error: urlError } = await supabase.storage
      .from('documents')
      .createSignedUrl(pathToCheck, 60);

    if (urlError) {
      console.error('❌ PROBLEM: Cannot create signed URL');
      console.error('   Error:', urlError.message);
      console.log('   → This confirms the file does NOT exist in storage');
    } else {
      console.log('✅ File exists! Signed URL created:', signedUrl.signedUrl);
    }
  }

  console.log('\n' + '='.repeat(80));
  console.log('TEST COMPLETE');
  console.log('='.repeat(80));
})();
```

## What to Look For

### If "documents" bucket doesn't exist:
```
❌ PROBLEM: "documents" bucket does NOT exist!
```
**Fix:** Create it in Supabase Dashboard → Storage → New Bucket → "documents"

### If bucket exists but is empty:
```
Found 0 item(s) in root:
❌ PROBLEM: Bucket is empty!
```
**Fix:** Upload your PDF files to the bucket

### If files are missing:
```
❌ PROBLEM: Cannot create signed URL
Error: Object not found
```
**Fix:** Upload the specific PDF file at the correct path

### If everything works:
```
✅ File exists! Signed URL created: https://...
```
This means at least some files exist - document loading should work!

## Alternative: Check Supabase Dashboard

1. Go to: https://supabase.com/dashboard/project/vzsohavtuotocgrfkfyd/storage/buckets
2. Click "documents" bucket (or create it if missing)
3. Browse folders to see what files exist
4. Compare with storage_path values in doc_metadata table

## Expected Folder Structure

Your storage should look like:
```
documents/
├── 85fe1119-b04c-41ac-80f1-829d23322598/  ← yacht_id
│   ├── 01_BRIDGE/
│   │   └── Documents/
│   │       └── 01_Operations/
│   │           └── Raymarine_A_Series_User_Manual.pdf
│   ├── 02_ENGINE_ROOM/
│   └── ...
└── [other yacht_ids]/
```

---

**Run this test now to immediately identify the storage issue!**
