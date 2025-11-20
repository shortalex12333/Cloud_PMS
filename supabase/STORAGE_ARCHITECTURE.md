# 🗄️ CelesteOS Storage Architecture

**Version:** 1.0
**Owner:** Worker 1 - Database Architect
**For:** Worker 5 (Ingestion), Worker 6 (Indexing)

---

## Overview

This document describes the **complete storage infrastructure** for CelesteOS document management. Worker 1 has configured:

- ✅ 2 Supabase Storage buckets (`documents`, `raw-uploads`)
- ✅ Row-Level Security (RLS) on `storage.objects`
- ✅ RLS on `documents` metadata table
- ✅ Helper functions for yacht-based path validation
- ✅ Multi-yacht isolation enforcement

**You (Worker 5/6) do NOT need to implement any of this.** You only need to **use** this infrastructure correctly.

---

## 📦 Storage Buckets

### Bucket 1: `documents` (Production)

**Purpose:** Final validated documents after ingestion
**Visibility:** Private (RLS enforced)
**Max File Size:** 500 MB
**Allowed MIME Types:**
- `application/pdf`
- `image/jpeg`, `image/png`, `image/tiff`
- `application/vnd.openxmlformats-officedocument.wordprocessingml.document` (DOCX)
- `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet` (XLSX)
- `application/msword` (DOC)
- `application/vnd.ms-excel` (XLS)
- `text/plain`, `text/csv`
- `application/zip`

**Path Format:**
```
documents/{yacht_id}/{sha256}/{original_filename}
```

**Example:**
```
documents/550e8400-e29b-41d4-a716-446655440000/a1b2c3d4e5f6.../motor_manual.pdf
```

---

### Bucket 2: `raw-uploads` (Temporary)

**Purpose:** Temporary storage for chunked uploads (optional)
**Visibility:** Private (RLS enforced)
**Max File Size:** 1 GB
**Allowed MIME Types:** All (no restriction)

**Path Format:**
```
raw-uploads/{upload_id}/chunk_{N}
```

**Example:**
```
raw-uploads/temp_upload_123abc/chunk_0
raw-uploads/temp_upload_123abc/chunk_1
```

**Usage:**
- Worker 5 may use this for large file chunked uploads
- Files should be moved to `documents` bucket after assembly
- Cleanup should happen after successful assembly

---

## 🔐 Security Model

### Row-Level Security (RLS) Enforcement

**All storage access is enforced by PostgreSQL RLS policies.**

#### Reads (SELECT)
✅ **Allowed:**
- Authenticated users accessing their own yacht's documents
- Path yacht_id MUST match JWT `yacht_id` claim

❌ **Blocked:**
- Cross-yacht access
- Unauthenticated access (unless via signed URL)

#### Writes (INSERT)
✅ **Allowed:**
- Service role (n8n, backend ingestion)
- Authenticated users uploading to their own yacht path

❌ **Blocked:**
- Uploading to another yacht's path
- Invalid path format

#### Updates (UPDATE)
✅ **Allowed:**
- Service role only (metadata updates)

❌ **Blocked:**
- User updates

#### Deletes (DELETE)
✅ **Allowed:**
- Service role only

❌ **Blocked:**
- User deletions (users cannot delete documents)

---

## 🧠 Helper Functions

Worker 1 has provided these functions for storage operations:

### `get_yacht_id()`

**Purpose:** Extract yacht_id from JWT claims
**Returns:** `text` (yacht_id as string)
**Usage:**
```sql
SELECT get_yacht_id();
-- Returns: '550e8400-e29b-41d4-a716-446655440000'
```

---

### `extract_yacht_id_from_path(storage_path)`

**Purpose:** Extract yacht_id from storage path
**Returns:** `text` (yacht_id from path)
**Usage:**
```sql
SELECT extract_yacht_id_from_path('550e8400-e29b-41d4-a716-446655440000/abc.../file.pdf');
-- Returns: '550e8400-e29b-41d4-a716-446655440000'
```

---

### `can_access_document(storage_path)`

**Purpose:** Check if user can access document at path
**Returns:** `boolean`
**Usage:**
```sql
SELECT can_access_document('550e8400-e29b-41d4-a716-446655440000/abc.../file.pdf');
-- Returns: true if user's yacht_id matches path yacht_id
```

---

### `assert_valid_yacht_path(storage_path)`

**Purpose:** Validate path or throw exception
**Returns:** `boolean` (true) or throws exception
**Usage:**
```sql
SELECT assert_valid_yacht_path('550e8400-e29b-41d4-a716-446655440000/abc.../file.pdf');
-- Returns: true if valid
-- Throws: 'Yacht ID mismatch...' if invalid
```

---

### `validate_storage_path_format(storage_path, bucket_name)`

**Purpose:** Validate path follows correct format
**Returns:** `boolean`
**Usage:**
```sql
SELECT validate_storage_path_format(
  '550e8400-e29b-41d4-a716-446655440000/a1b2c3.../file.pdf',
  'documents'
);
-- Returns: true if format is correct
```

---

## 🔑 Authentication Methods

### Method 1: Service Role Key (Recommended for Ingestion)

**Used by:** n8n, backend ingestion services

**Setup:**
```javascript
import { createClient } from '@supabase/supabase-js';

const supabase = createClient(
  'https://vzsohavtuotocgrfkfyd.supabase.co',
  process.env.SUPABASE_SERVICE_ROLE_KEY  // Service role key
);
```

**Permissions:**
- ✅ Upload to any yacht's path
- ✅ Update document metadata
- ✅ Delete documents
- ✅ Bypasses RLS (full access)

**Critical:** Service role key MUST be kept secret (server-side only)

---

### Method 2: User JWT (For Client-Side Uploads)

**Used by:** Web app, authenticated users

**Setup:**
```javascript
const supabase = createClient(
  'https://vzsohavtuotocgrfkfyd.supabase.co',
  'your_anon_key'
);

// After authentication
await supabase.auth.signInWithPassword({
  email: 'user@example.com',
  password: 'password'
});

// JWT now contains yacht_id claim
```

**Permissions:**
- ✅ Upload to own yacht's path only
- ✅ Read own yacht's documents
- ❌ Cannot access other yachts
- ❌ Cannot delete documents

---

### Method 3: Signed URLs (For Temporary Access)

**Used by:** Sharing documents via temporary links

**Generate:**
```javascript
const { data, error } = await supabase.storage
  .from('documents')
  .createSignedUrl('550e8400-.../abc.../file.pdf', 3600);  // 1 hour

// Returns: { signedUrl: 'https://...?token=...' }
```

**Permissions:**
- ✅ Temporary access (expires after specified duration)
- ✅ No authentication required (token embedded in URL)
- ✅ RLS still enforced (must be user's yacht)

---

## 📝 documents Metadata Table

**Location:** `public.documents` table
**Schema:** (from `table_configs.md`)

```sql
CREATE TABLE documents (
  id uuid PRIMARY KEY,
  yacht_id uuid NOT NULL REFERENCES yachts(id),
  sha256 char(64) NOT NULL,         -- File hash for deduplication
  filename text NOT NULL,            -- Original filename
  file_path text NOT NULL,           -- Full storage path
  file_size_bytes bigint,
  mime_type text,
  source_type text,                  -- 'nas', 'email', 'manual_upload', 'api'
  category text,
  tags text[],
  indexed boolean DEFAULT false,     -- Has document been indexed?
  indexed_at timestamptz,            -- When was it indexed?
  page_count integer,
  metadata jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);
```

**RLS Policies:**
- **SELECT:** Users can only see their yacht's documents
- **INSERT:** Service role can insert for any yacht
- **UPDATE:** Service role can update processing fields (`indexed`, `indexed_at`)
- **DELETE:** Service role only

---

## 🚀 Worker 5: Ingestion Guide

**Your responsibility:** Upload documents to Supabase Storage and create metadata records.

### Step-by-Step Upload Process

#### 1. Determine Storage Path

```javascript
const yacht_id = '550e8400-e29b-41d4-a716-446655440000';  // From context
const sha256 = calculateSHA256(fileBuffer);               // Calculate hash
const filename = 'motor_manual.pdf';                      // Original filename

const storagePath = `${yacht_id}/${sha256}/${filename}`;
// Result: '550e8400-.../a1b2c3d4.../motor_manual.pdf'
```

#### 2. Upload to Storage

```javascript
const { data, error } = await supabase.storage
  .from('documents')
  .upload(storagePath, fileBuffer, {
    contentType: 'application/pdf',
    upsert: false  // Prevent overwriting existing files
  });

if (error) {
  console.error('Upload failed:', error);
  throw error;
}

console.log('Upload successful:', data.path);
// Returns: { path: '550e8400-.../a1b2c3d4.../motor_manual.pdf' }
```

#### 3. Create Metadata Record

```javascript
const { data: document, error: dbError } = await supabase
  .from('documents')
  .insert({
    yacht_id: yacht_id,
    sha256: sha256,
    filename: filename,
    file_path: storagePath,
    file_size_bytes: fileBuffer.length,
    mime_type: 'application/pdf',
    source_type: 'nas',
    indexed: false  // Will be updated by Worker 6 (indexing)
  })
  .select()
  .single();

if (dbError) {
  console.error('Metadata insert failed:', dbError);
  // Rollback: Delete uploaded file
  await supabase.storage.from('documents').remove([storagePath]);
  throw dbError;
}

console.log('Document created:', document.id);
```

#### 4. Handle Deduplication

```javascript
// Check if document already exists (by SHA256)
const { data: existing } = await supabase
  .from('documents')
  .select('id, file_path')
  .eq('yacht_id', yacht_id)
  .eq('sha256', sha256)
  .single();

if (existing) {
  console.log('Document already exists:', existing.id);
  // Skip upload, return existing document
  return existing;
}

// Otherwise, proceed with upload (steps 2-3)
```

---

### Example: Complete Upload Function

```javascript
async function uploadDocument(yacht_id, fileBuffer, filename, source_type = 'nas') {
  // 1. Calculate SHA256
  const sha256 = calculateSHA256(fileBuffer);

  // 2. Check if already exists
  const { data: existing } = await supabase
    .from('documents')
    .select('id, file_path')
    .eq('yacht_id', yacht_id)
    .eq('sha256', sha256)
    .single();

  if (existing) {
    console.log('Document already exists (deduplicated):', existing.id);
    return existing;
  }

  // 3. Determine storage path
  const storagePath = `${yacht_id}/${sha256}/${filename}`;

  // 4. Upload to storage
  const { data: uploadData, error: uploadError } = await supabase.storage
    .from('documents')
    .upload(storagePath, fileBuffer, {
      contentType: detectMimeType(filename),
      upsert: false
    });

  if (uploadError) {
    throw new Error(`Upload failed: ${uploadError.message}`);
  }

  // 5. Create metadata record
  const { data: document, error: dbError } = await supabase
    .from('documents')
    .insert({
      yacht_id: yacht_id,
      sha256: sha256,
      filename: filename,
      file_path: storagePath,
      file_size_bytes: fileBuffer.length,
      mime_type: detectMimeType(filename),
      source_type: source_type,
      indexed: false,
      metadata: {
        uploaded_by: 'ingestion_service',
        original_path: filename
      }
    })
    .select()
    .single();

  if (dbError) {
    // Rollback: Delete uploaded file
    await supabase.storage.from('documents').remove([storagePath]);
    throw new Error(`Metadata insert failed: ${dbError.message}`);
  }

  console.log('Document uploaded successfully:', document.id);
  return document;
}
```

---

## 🔍 Worker 6: Indexing Guide

**Your responsibility:** Process documents and update metadata after indexing.

### Step-by-Step Indexing Process

#### 1. Fetch Unindexed Documents

```javascript
const { data: documents, error } = await supabase
  .from('documents')
  .select('id, yacht_id, file_path, sha256, filename')
  .eq('indexed', false)
  .limit(10);

if (error) {
  console.error('Failed to fetch documents:', error);
  throw error;
}

console.log(`Found ${documents.length} unindexed documents`);
```

#### 2. Download Document from Storage

```javascript
const { data: fileBlob, error: downloadError } = await supabase.storage
  .from('documents')
  .download(document.file_path);

if (downloadError) {
  console.error('Download failed:', downloadError);
  throw downloadError;
}

const fileBuffer = await fileBlob.arrayBuffer();
console.log('Downloaded document:', document.filename);
```

#### 3. Process Document (OCR, Chunking, Embedding)

```javascript
// Your indexing logic here
const chunks = await chunkDocument(fileBuffer);
const embeddings = await generateEmbeddings(chunks);

// Store chunks and embeddings in document_chunks table
for (let i = 0; i < chunks.length; i++) {
  await supabase.from('document_chunks').insert({
    yacht_id: document.yacht_id,
    document_id: document.id,
    chunk_index: i,
    text: chunks[i],
    embedding: embeddings[i],
    page_number: Math.floor(i / chunksPerPage)
  });
}
```

#### 4. Mark Document as Indexed

```javascript
const { error: updateError } = await supabase
  .from('documents')
  .update({
    indexed: true,
    indexed_at: new Date().toISOString(),
    page_count: totalPages
  })
  .eq('id', document.id);

if (updateError) {
  console.error('Failed to mark as indexed:', updateError);
  throw updateError;
}

console.log('Document indexed successfully:', document.id);
```

---

### Example: Complete Indexing Function

```javascript
async function indexDocument(document_id) {
  // 1. Fetch document metadata
  const { data: document, error: fetchError } = await supabase
    .from('documents')
    .select('*')
    .eq('id', document_id)
    .single();

  if (fetchError || !document) {
    throw new Error(`Document not found: ${document_id}`);
  }

  if (document.indexed) {
    console.log('Document already indexed:', document_id);
    return;
  }

  // 2. Download from storage
  const { data: fileBlob, error: downloadError } = await supabase.storage
    .from('documents')
    .download(document.file_path);

  if (downloadError) {
    throw new Error(`Download failed: ${downloadError.message}`);
  }

  const fileBuffer = await fileBlob.arrayBuffer();

  // 3. Process document (OCR, chunking, embedding)
  const text = await extractText(fileBuffer, document.mime_type);
  const chunks = chunkText(text, 512);  // 512 token chunks
  const embeddings = await generateEmbeddings(chunks);

  // 4. Store chunks
  for (let i = 0; i < chunks.length; i++) {
    await supabase.from('document_chunks').insert({
      yacht_id: document.yacht_id,
      document_id: document.id,
      chunk_index: i,
      text: chunks[i],
      embedding: embeddings[i]
    });
  }

  // 5. Mark as indexed
  await supabase
    .from('documents')
    .update({
      indexed: true,
      indexed_at: new Date().toISOString(),
      page_count: estimatePageCount(text)
    })
    .eq('id', document.id);

  console.log('Indexing complete:', document.id);
}
```

---

## 🧪 Testing

### Test 1: Upload as Service Role

```javascript
// Using service_role key
const supabase = createClient(supabaseUrl, serviceRoleKey);

const yacht_id = '550e8400-e29b-41d4-a716-446655440000';
const testFile = Buffer.from('Test content');
const storagePath = `${yacht_id}/test123.../test.txt`;

// Should succeed
const { data, error } = await supabase.storage
  .from('documents')
  .upload(storagePath, testFile);

console.log('Upload result:', data ? 'SUCCESS' : 'FAILED');
```

### Test 2: Read as Authenticated User

```javascript
// Using anon key + user JWT
const supabase = createClient(supabaseUrl, anonKey);

// Sign in as user (yacht_id in JWT)
await supabase.auth.signInWithPassword({
  email: 'test@yacht1.com',
  password: 'password'
});

// Try to read document from user's yacht
const { data, error } = await supabase.storage
  .from('documents')
  .download('550e8400-.../test123.../test.txt');

console.log('Download result:', data ? 'SUCCESS' : 'FAILED');

// Try to read document from DIFFERENT yacht (should fail)
const { data: data2, error: error2 } = await supabase.storage
  .from('documents')
  .download('different-yacht-id/test123.../test.txt');

console.log('Cross-yacht access:', error2 ? 'BLOCKED ✅' : 'ALLOWED ❌');
```

### Test 3: Path Validation

```sql
-- Test extract_yacht_id_from_path
SELECT extract_yacht_id_from_path('550e8400-e29b-41d4-a716-446655440000/abc.../file.pdf');
-- Expected: '550e8400-e29b-41d4-a716-446655440000'

-- Test validate_storage_path_format
SELECT validate_storage_path_format(
  '550e8400-e29b-41d4-a716-446655440000/a1b2c3d4e5f6.../test.pdf',
  'documents'
);
-- Expected: true

-- Test invalid format
SELECT validate_storage_path_format('invalid/path', 'documents');
-- Expected: false
```

---

## 📋 Deployment Checklist

Before using this storage infrastructure, ensure:

- [x] Migration 007: Storage buckets created (`documents`, `raw-uploads`)
- [x] Migration 008: Helper functions deployed
- [x] Migration 009: Storage RLS policies active
- [x] Migration 010: Documents metadata RLS active
- [x] Service role key configured in environment variables
- [x] Anon key configured for client-side operations
- [ ] Test upload as service_role (Worker 5)
- [ ] Test download as authenticated user (verify yacht isolation)
- [ ] Test cross-yacht access blocked
- [ ] Verify signed URL generation works

---

## 🔗 Related Documentation

- **Database Schema:** `supabase/migrations/20250101000001_initial_schema_v2.sql`
- **RLS Policies (General):** `supabase/migrations/20250101000002_rls_policies.sql`
- **Storage Migrations:** `supabase/migrations/2025010100000[7-10]_*.sql`
- **Gap Verification:** `GAP_CLOSURE_VERIFICATION.md`

---

## ❓ FAQ

### Q: Can users delete documents?
**A:** No. Only service_role can delete documents. Users can only read.

### Q: What happens if I upload to wrong yacht's path?
**A:** RLS policy will block the upload. Error: "Row violates policy"

### Q: How do signed URLs work with RLS?
**A:** Signed URLs include a temporary token that satisfies RLS policies. They still enforce yacht isolation.

### Q: Can I upload files larger than 500 MB?
**A:** Not to `documents` bucket (limit: 500 MB). Use `raw-uploads` for larger files (limit: 1 GB), then split/process.

### Q: What if SHA256 hash collides?
**A:** Extremely unlikely (2^256 combinations). If it happens, deduplication treats them as same file (feature, not bug).

### Q: How do I handle file updates/versions?
**A:** Don't modify existing files. Upload new version with different SHA256. Keep old version for audit trail.

---

**End of Storage Architecture Documentation**

**Questions?** Contact Worker 1 (Database Architect)
