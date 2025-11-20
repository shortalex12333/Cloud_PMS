# Worker 5 Quick Start: Hierarchical Storage
## Copy-Paste Ready Code for Document Ingestion

**Version:** 2.0 (Hierarchical)
**Last Updated:** 2025-01-01

---

## 🚀 Setup (One Time)

```javascript
import { createClient } from '@supabase/supabase-js';
import crypto from 'crypto';
import fs from 'fs';

const supabase = createClient(
  process.env.SUPABASE_URL,
  process.env.SUPABASE_SERVICE_ROLE_KEY  // ⚠️ MUST use service_role key!
);
```

---

## 📤 Upload Function (Production Ready)

```javascript
/**
 * Upload document to Supabase Storage with hierarchical structure
 *
 * @param {Object} fileData - Document data from Worker 4
 * @param {string} fileData.yacht_id - Yacht UUID
 * @param {string} fileData.filename - Original filename
 * @param {string} fileData.system_path - Hierarchical path (e.g., "03_Engineering/MainEngine")
 * @param {Buffer} fileData.file_buffer - File binary data
 * @param {string} fileData.mime_type - MIME type
 * @param {number} fileData.file_size - File size in bytes
 * @returns {Promise<Object>} Document metadata record
 */
async function uploadDocument(fileData) {
  const {
    yacht_id,
    filename,
    system_path,  // 🆕 NEW: Required for directory permissions
    file_buffer,
    mime_type,
    file_size
  } = fileData;

  console.log(`📤 Uploading: ${filename} → ${system_path}`);

  // 1. Calculate SHA256 hash for deduplication
  const sha256 = crypto.createHash('sha256')
    .update(file_buffer)
    .digest('hex');

  console.log(`   Hash: ${sha256.substring(0, 12)}...`);

  // 2. Check for duplicates (same yacht + same hash)
  const { data: existingDoc, error: checkError } = await supabase
    .from('documents')
    .select('id, filename, file_path')
    .eq('yacht_id', yacht_id)
    .eq('sha256', sha256)
    .maybeSingle();

  if (checkError) {
    throw new Error(`Duplicate check failed: ${checkError.message}`);
  }

  if (existingDoc) {
    console.log(`   ♻️  Duplicate found: ${existingDoc.id}`);
    return {
      ...existingDoc,
      duplicate: true
    };
  }

  // 3. Build storage path: {yacht_id}/{system_path}/{filename}
  const storagePath = `${yacht_id}/${system_path}/${filename}`;

  console.log(`   Storage path: documents/${storagePath}`);

  // 4. Upload file to Supabase Storage
  const { data: uploadData, error: uploadError } = await supabase.storage
    .from('documents')
    .upload(storagePath, file_buffer, {
      contentType: mime_type,
      cacheControl: '3600',
      upsert: false  // Fail if file already exists (safety check)
    });

  if (uploadError) {
    // Handle "already exists" error gracefully
    if (uploadError.message.includes('already exists')) {
      console.log(`   ⚠️  File already in storage: ${storagePath}`);
      // Continue to metadata creation (might be orphaned storage file)
    } else {
      throw new Error(`Storage upload failed: ${uploadError.message}`);
    }
  } else {
    console.log(`   ✅ Uploaded to storage`);
  }

  // 5. Create metadata record in documents table
  const { data: document, error: insertError } = await supabase
    .from('documents')
    .insert({
      yacht_id,
      filename,
      file_path: `documents/${storagePath}`,  // Full path with bucket
      system_path,  // 🆕 CRITICAL: Required for directory permissions
      sha256,
      mime_type,
      file_size,
      indexed: false,  // Will be updated by Worker 6
      uploaded_at: new Date().toISOString()
    })
    .select()
    .single();

  if (insertError) {
    // Rollback: try to delete uploaded file (best effort)
    console.error(`   ❌ Metadata insert failed: ${insertError.message}`);

    try {
      await supabase.storage.from('documents').remove([storagePath]);
      console.log(`   🔄 Rolled back storage upload`);
    } catch (rollbackError) {
      console.error(`   ⚠️  Rollback failed (orphaned file): ${rollbackError.message}`);
    }

    throw new Error(`Metadata insert failed: ${insertError.message}`);
  }

  console.log(`   ✅ Created metadata: ${document.id}`);

  return {
    ...document,
    duplicate: false
  };
}
```

---

## 📥 Input Format (from Worker 4)

Worker 4 sends this structure:

```javascript
const fileData = {
  yacht_id: "7b2c3d4e-5f6a-7b8c-9d0e-1f2a3b4c5d6e",  // UUID
  filename: "manual_CAT3516.pdf",                    // Original filename
  system_path: "03_Engineering/MainEngine",          // 🆕 Hierarchical path from NAS
  file_buffer: <Buffer>,                             // Binary file data
  mime_type: "application/pdf",                      // MIME type
  file_size: 2048576,                                // Bytes
  local_path: "/mnt/nas/ROOT/03_Engineering/MainEngine/manual_CAT3516.pdf"  // For logging
};
```

**Key Requirements:**

- `system_path` MUST NOT have leading/trailing slashes
- `system_path` preserves yacht's actual folder structure
- `system_path` examples:
  - ✅ `"03_Engineering/MainEngine"`
  - ✅ `"Engineering/Hydraulics"`
  - ✅ `"Bridge/Charts"`
  - ❌ `"/Engineering"` (leading slash)
  - ❌ `"Engineering/"` (trailing slash)
  - ❌ `"Engineering//Main"` (double slash)

---

## 🔄 Batch Upload (Multiple Files)

```javascript
/**
 * Upload multiple documents in batch
 * @param {Array<Object>} fileDataArray - Array of fileData objects
 * @returns {Promise<Object>} Upload statistics
 */
async function uploadDocumentBatch(fileDataArray) {
  const results = {
    total: fileDataArray.length,
    success: 0,
    duplicates: 0,
    failed: 0,
    errors: []
  };

  console.log(`📦 Starting batch upload: ${results.total} files`);

  for (const fileData of fileDataArray) {
    try {
      const result = await uploadDocument(fileData);

      if (result.duplicate) {
        results.duplicates++;
      } else {
        results.success++;
      }
    } catch (error) {
      results.failed++;
      results.errors.push({
        filename: fileData.filename,
        system_path: fileData.system_path,
        error: error.message
      });

      console.error(`❌ Failed: ${fileData.filename} → ${error.message}`);
    }
  }

  console.log(`\n📊 Batch Upload Complete:`);
  console.log(`   Total: ${results.total}`);
  console.log(`   ✅ Success: ${results.success}`);
  console.log(`   ♻️  Duplicates: ${results.duplicates}`);
  console.log(`   ❌ Failed: ${results.failed}`);

  return results;
}
```

---

## 🧪 Test Upload

```javascript
// Test with a sample file
async function testUpload() {
  const testData = {
    yacht_id: "123e4567-e89b-12d3-a456-426614174000",
    filename: "test_manual.pdf",
    system_path: "03_Engineering/MainEngine",  // 🆕 Required
    file_buffer: fs.readFileSync('./test_files/manual.pdf'),
    mime_type: "application/pdf",
    file_size: 2048576
  };

  try {
    const document = await uploadDocument(testData);
    console.log('\n✅ Upload successful!');
    console.log('Document ID:', document.id);
    console.log('File path:', document.file_path);
    console.log('System path:', document.system_path);
  } catch (error) {
    console.error('\n❌ Upload failed:', error.message);
  }
}

// Run test
testUpload();
```

---

## 🔍 Verify Upload

```javascript
/**
 * Verify document was uploaded correctly
 */
async function verifyUpload(document_id) {
  // 1. Check metadata in database
  const { data: doc, error: dbError } = await supabase
    .from('documents')
    .select('*')
    .eq('id', document_id)
    .single();

  if (dbError) {
    console.error('❌ Database check failed:', dbError.message);
    return false;
  }

  console.log('✅ Database record found:');
  console.log('   ID:', doc.id);
  console.log('   Filename:', doc.filename);
  console.log('   System path:', doc.system_path);  // 🆕 Verify this exists
  console.log('   File path:', doc.file_path);
  console.log('   Indexed:', doc.indexed);

  // 2. Check file exists in storage
  const storagePath = doc.file_path.replace(/^documents\//, '');

  const { data: storageData, error: storageError } = await supabase.storage
    .from('documents')
    .download(storagePath);

  if (storageError) {
    console.error('❌ Storage check failed:', storageError.message);
    return false;
  }

  console.log('✅ Storage file found:');
  console.log('   Size:', storageData.size, 'bytes');

  return true;
}
```

---

## 🛠️ Error Handling

### Common Errors and Solutions:

| Error | Cause | Solution |
|-------|-------|----------|
| `duplicate key value violates unique constraint` | Document already exists | Check for duplicates before upload |
| `new row violates row security policy` | Wrong auth role | Use service_role key (not anon key) |
| `column "system_path" does not exist` | Migration not deployed | Run migration 011 |
| `The resource already exists` | File already in storage | OK - continue to metadata creation |
| `insert or update on table "documents" violates foreign key constraint` | Invalid yacht_id | Verify yacht_id exists in yachts table |

### Error Handling Template:

```javascript
try {
  const document = await uploadDocument(fileData);
  console.log('✅ Success:', document.id);
} catch (error) {
  console.error('❌ Upload failed:', error.message);

  // Log error to database for tracking
  await supabase.from('ingestion_errors').insert({
    yacht_id: fileData.yacht_id,
    filename: fileData.filename,
    system_path: fileData.system_path,
    error_message: error.message,
    error_time: new Date().toISOString()
  });

  // Notify monitoring system
  // sendAlert('Upload failed', error);

  throw error;  // Re-throw for caller to handle
}
```

---

## 📊 Progress Tracking

```javascript
/**
 * Track upload progress with status updates
 */
async function uploadWithProgress(fileDataArray, onProgress) {
  const total = fileDataArray.length;
  let completed = 0;

  for (const fileData of fileDataArray) {
    try {
      const result = await uploadDocument(fileData);

      completed++;
      onProgress({
        completed,
        total,
        percentage: Math.round((completed / total) * 100),
        current_file: fileData.filename,
        status: result.duplicate ? 'duplicate' : 'success'
      });
    } catch (error) {
      completed++;
      onProgress({
        completed,
        total,
        percentage: Math.round((completed / total) * 100),
        current_file: fileData.filename,
        status: 'failed',
        error: error.message
      });
    }
  }
}

// Usage:
await uploadWithProgress(files, (progress) => {
  console.log(`[${progress.percentage}%] ${progress.current_file} → ${progress.status}`);
});
```

---

## 🔗 Integration with Worker 4

### Worker 4 → Worker 5 Flow:

```javascript
// Worker 4 scans NAS and sends to Worker 5
// Example integration:

// Worker 4 (NAS Scanner)
async function scanAndSendToWorker5(yacht_id, nas_root_path) {
  const files = await scanDirectory(nas_root_path);

  for (const file of files) {
    const fileData = {
      yacht_id,
      filename: file.name,
      system_path: file.relativePath,  // 🆕 e.g., "03_Engineering/MainEngine"
      file_buffer: await fs.promises.readFile(file.fullPath),
      mime_type: getMimeType(file.extension),
      file_size: file.size,
      local_path: file.fullPath  // For logging
    };

    // Send to Worker 5 (could be API call, queue message, etc.)
    await sendToWorker5(fileData);
  }
}

// Worker 5 (Ingestion Service)
async function receiveFromWorker4(fileData) {
  console.log(`📥 Received: ${fileData.filename} from ${fileData.system_path}`);

  const document = await uploadDocument(fileData);

  console.log(`📤 Uploaded: ${document.id}`);

  return document;
}
```

---

## ✅ Pre-Deployment Checklist

Before using in production:

- [ ] Migrations 011-015 deployed to Supabase
- [ ] `system_path` column exists in documents table
- [ ] `role_directory_permissions` table created
- [ ] Service role key configured in environment
- [ ] Test upload works with sample file
- [ ] Verify deduplication works (upload same file twice)
- [ ] Check RLS policies are enforced (try with authenticated user)
- [ ] Verify storage path format is correct
- [ ] Test batch upload with multiple files
- [ ] Set up error logging and monitoring

---

## 📞 Support

**Documentation:**
- Full architecture: `supabase/HIERARCHICAL_STORAGE_ARCHITECTURE.md`
- Migrations: `supabase/migrations/20250101000011_*` through `20250101000015_*`
- Deployment script: `DEPLOY_HIERARCHICAL_STORAGE.sh`

**Key Functions in Database:**
```sql
-- Test if path is valid
SELECT validate_storage_path_format('documents/yacht-id/Engineering/file.pdf', 'documents');

-- Build path from components
SELECT build_storage_path('yacht-id'::uuid, 'Engineering/Main', 'file.pdf');

-- Check user permissions (as authenticated user)
SELECT can_access_storage_path('documents/yacht-id/Engineering/file.pdf');
```

**Environment Variables:**
```bash
SUPABASE_URL=https://vzsohavtuotocgrfkfyd.supabase.co
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

---

**Ready to use! 🚀**

Copy the `uploadDocument()` function and start ingesting documents with hierarchical structure.
