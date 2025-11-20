# 🚀 Worker 5 Quick Start: Document Upload

**For:** Worker 5 (Ingestion Service)
**Purpose:** Upload documents to Supabase Storage with yacht isolation

---

## TL;DR

**Path Format:**
```
documents/{yacht_id}/{sha256}/{original_filename}
```

**Upload Code:**
```javascript
const storagePath = `${yacht_id}/${sha256}/${filename}`;

await supabase.storage
  .from('documents')
  .upload(storagePath, fileBuffer, { upsert: false });

await supabase.from('documents').insert({
  yacht_id, sha256, filename,
  file_path: storagePath,
  file_size_bytes: fileBuffer.length,
  mime_type: 'application/pdf',
  source_type: 'nas',
  indexed: false
});
```

---

## Setup

### 1. Install Supabase Client

```bash
npm install @supabase/supabase-js
```

### 2. Initialize Client (Service Role)

```javascript
import { createClient } from '@supabase/supabase-js';

const supabase = createClient(
  'https://vzsohavtuotocgrfkfyd.supabase.co',
  process.env.SUPABASE_SERVICE_ROLE_KEY  // KEEP SECRET!
);
```

**Critical:** Use `SUPABASE_SERVICE_ROLE_KEY`, NOT the anon key.

---

## Complete Upload Function

```javascript
import crypto from 'crypto';
import { createClient } from '@supabase/supabase-js';

const supabase = createClient(
  'https://vzsohavtuotocgrfkfyd.supabase.co',
  process.env.SUPABASE_SERVICE_ROLE_KEY
);

function calculateSHA256(buffer) {
  return crypto.createHash('sha256').update(buffer).digest('hex');
}

function detectMimeType(filename) {
  const ext = filename.split('.').pop().toLowerCase();
  const mimeTypes = {
    'pdf': 'application/pdf',
    'jpg': 'image/jpeg',
    'jpeg': 'image/jpeg',
    'png': 'image/png',
    'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'txt': 'text/plain',
    'csv': 'text/csv'
  };
  return mimeTypes[ext] || 'application/octet-stream';
}

async function uploadDocument(yacht_id, fileBuffer, filename, source_type = 'nas') {
  console.log(`[UPLOAD] Starting upload: ${filename} for yacht ${yacht_id}`);

  // 1. Calculate SHA256
  const sha256 = calculateSHA256(fileBuffer);
  console.log(`[UPLOAD] SHA256: ${sha256}`);

  // 2. Check for duplicates
  const { data: existing } = await supabase
    .from('documents')
    .select('id, file_path, filename')
    .eq('yacht_id', yacht_id)
    .eq('sha256', sha256)
    .maybeSingle();

  if (existing) {
    console.log(`[UPLOAD] Document already exists (deduplicated): ${existing.id}`);
    return { success: true, document: existing, deduplicated: true };
  }

  // 3. Determine storage path
  const storagePath = `${yacht_id}/${sha256}/${filename}`;
  console.log(`[UPLOAD] Storage path: ${storagePath}`);

  // 4. Upload to Supabase Storage
  const { data: uploadData, error: uploadError } = await supabase.storage
    .from('documents')
    .upload(storagePath, fileBuffer, {
      contentType: detectMimeType(filename),
      upsert: false  // Prevent overwriting
    });

  if (uploadError) {
    console.error('[UPLOAD] Storage upload failed:', uploadError);
    throw new Error(`Storage upload failed: ${uploadError.message}`);
  }

  console.log('[UPLOAD] Storage upload successful');

  // 5. Create metadata record
  const { data: document, error: dbError } = await supabase
    .from('documents')
    .insert({
      yacht_id: yacht_id,
      sha256: sha256,
      filename: filename,
      file_path: storagePath,
      storage_path: storagePath,  // Alias for file_path
      file_size_bytes: fileBuffer.length,
      mime_type: detectMimeType(filename),
      source_type: source_type,
      indexed: false,
      metadata: {
        uploaded_by: 'ingestion_service',
        uploaded_at: new Date().toISOString()
      }
    })
    .select()
    .single();

  if (dbError) {
    console.error('[UPLOAD] Metadata insert failed:', dbError);

    // Rollback: Delete uploaded file
    console.log('[UPLOAD] Rolling back storage upload...');
    await supabase.storage.from('documents').remove([storagePath]);

    throw new Error(`Metadata insert failed: ${dbError.message}`);
  }

  console.log(`[UPLOAD] Upload complete: ${document.id}`);

  return { success: true, document, deduplicated: false };
}

// Export for use
module.exports = { uploadDocument };
```

---

## Usage Examples

### Example 1: Upload from Local File

```javascript
import fs from 'fs/promises';

async function uploadLocalFile(yacht_id, filePath) {
  const fileBuffer = await fs.readFile(filePath);
  const filename = filePath.split('/').pop();

  const result = await uploadDocument(yacht_id, fileBuffer, filename, 'manual_upload');

  console.log('Upload result:', result);
  return result;
}

// Usage
await uploadLocalFile(
  '550e8400-e29b-41d4-a716-446655440000',
  '/path/to/motor_manual.pdf'
);
```

### Example 2: Upload from HTTP Request

```javascript
import axios from 'axios';

async function uploadFromUrl(yacht_id, url, filename) {
  const response = await axios.get(url, { responseType: 'arraybuffer' });
  const fileBuffer = Buffer.from(response.data);

  const result = await uploadDocument(yacht_id, fileBuffer, filename, 'api');

  return result;
}

// Usage
await uploadFromUrl(
  '550e8400-e29b-41d4-a716-446655440000',
  'https://example.com/manual.pdf',
  'manual.pdf'
);
```

### Example 3: Batch Upload

```javascript
async function batchUpload(yacht_id, files) {
  const results = [];

  for (const file of files) {
    try {
      const result = await uploadDocument(
        yacht_id,
        file.buffer,
        file.filename,
        file.source_type || 'nas'
      );
      results.push({ success: true, ...result });
    } catch (error) {
      results.push({ success: false, filename: file.filename, error: error.message });
    }
  }

  return results;
}

// Usage
const files = [
  { buffer: buffer1, filename: 'doc1.pdf' },
  { buffer: buffer2, filename: 'doc2.pdf' },
];

const results = await batchUpload('550e8400-...', files);
console.log(`Uploaded ${results.filter(r => r.success).length} / ${results.length} files`);
```

---

## Error Handling

### Common Errors

**1. "New row violates row-level security policy"**
- **Cause:** Trying to upload to wrong yacht's path
- **Fix:** Ensure `yacht_id` in path matches authenticated user's yacht

**2. "The resource already exists"**
- **Cause:** File already exists at that path
- **Fix:** Use `upsert: true` OR check for duplicates first

**3. "Payload too large"**
- **Cause:** File exceeds 500 MB limit
- **Fix:** Use `raw-uploads` bucket for large files, then split

**4. "Invalid MIME type"**
- **Cause:** File type not allowed in `documents` bucket
- **Fix:** Check `allowed_mime_types` in STORAGE_ARCHITECTURE.md

---

## Testing Checklist

- [ ] Upload PDF document
- [ ] Upload image (JPEG/PNG)
- [ ] Upload Office document (DOCX/XLSX)
- [ ] Verify deduplication (upload same file twice)
- [ ] Verify metadata record created
- [ ] Verify `indexed = false` initially
- [ ] Try uploading to different yacht's path (should fail)
- [ ] Check file accessible via signed URL

---

## Environment Variables

```env
SUPABASE_URL=https://vzsohavtuotocgrfkfyd.supabase.co
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**CRITICAL:** Never commit service role key to git!

---

## Next Steps

1. **Deploy your ingestion service** with this upload function
2. **Test uploads** with sample documents
3. **Verify Worker 6 (indexing)** can access uploaded documents
4. **Monitor `documents` table** for successful uploads
5. **Check storage usage** in Supabase dashboard

---

## Troubleshooting

### Debug Mode

```javascript
async function uploadDocumentDebug(yacht_id, fileBuffer, filename) {
  console.log('=== UPLOAD DEBUG ===');
  console.log('Yacht ID:', yacht_id);
  console.log('Filename:', filename);
  console.log('File size:', fileBuffer.length);

  const sha256 = calculateSHA256(fileBuffer);
  console.log('SHA256:', sha256);

  const storagePath = `${yacht_id}/${sha256}/${filename}`;
  console.log('Storage path:', storagePath);

  // Check yacht exists
  const { data: yacht } = await supabase
    .from('yachts')
    .select('id, name')
    .eq('id', yacht_id)
    .single();

  console.log('Yacht found:', yacht ? yacht.name : 'NOT FOUND');

  // Proceed with upload...
  return await uploadDocument(yacht_id, fileBuffer, filename);
}
```

### Check Storage

```javascript
async function listYachtDocuments(yacht_id) {
  const { data: files } = await supabase.storage
    .from('documents')
    .list(yacht_id, { limit: 100 });

  console.log(`Found ${files.length} files for yacht ${yacht_id}`);
  files.forEach(file => console.log(`- ${file.name}`));
}
```

---

## Reference

**Full Documentation:** `supabase/STORAGE_ARCHITECTURE.md`
**Migrations:** `supabase/migrations/2025010100000[7-10]_*.sql`

**Questions?** Contact Worker 1 (Database Architect)
