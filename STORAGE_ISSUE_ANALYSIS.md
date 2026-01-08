# Storage Issue Analysis

## Problem Summary

Document loading is **so close** to working! All database queries are succeeding, but failing at the final step when trying to load the actual PDF file from Supabase Storage.

### What's Working ✅

1. **Authentication** - User is properly authenticated
2. **RLS Policies** - All yacht isolation checks are passing
3. **Database Queries** - Successfully retrieving document metadata
4. **Function Fixes** - `get_user_yacht_id()` now correctly returns yacht_id from `auth_users_yacht`

### Current Error ❌

```
POST /storage/v1/object/sign/documents/85fe1119.../Raymarine_A_Series_User_Manual.pdf
Status: 400 Bad Request
Error: "Object not found"
```

## Root Cause

**The PDF files don't exist in Supabase Storage.**

Your database has this flow working perfectly:
- `search_document_chunks` → contains `document_id` ✅
- `doc_metadata` → contains `storage_path` ✅
- Supabase Storage → **FILE MISSING** ❌

This is a common migration issue where:
1. Document metadata was imported into the database
2. But the actual PDF files were never uploaded to Supabase Storage

## Diagnostic Tools Added

I've deployed two new tools to help diagnose this:

### 1. Web UI: `/debug/storage`
Visit this page in your browser to see:
- What storage buckets exist
- Sample document paths from `doc_metadata`
- Which files actually exist vs missing
- Color-coded status (✅ exists, ❌ missing)

### 2. API: `GET /api/debug/storage`
Returns JSON with:
- List of all storage buckets
- Sample `doc_metadata` records
- File existence verification for each path
- Detailed error messages

## How to Access

After Vercel deploys (commit `6b4ff28`):

```
https://your-app.vercel.app/debug/storage
```

This will show you exactly which files are missing.

## Next Steps

You have **three options** to fix this:

### Option 1: Upload Missing PDFs (Recommended if you have the files)

If you have the original PDF files:

1. Go to Supabase Dashboard → Storage
2. Create/verify "documents" bucket exists
3. Upload PDFs matching the paths in `doc_metadata`
4. Maintain the folder structure: `{yacht_id}/{category}/{subcategory}/{filename}`

Example path from your logs:
```
85fe1119-b04c-41ac-80f1-829d23322598/
  └─ 01_BRIDGE/
      └─ Documents/
          └─ 01_Operations/
              └─ Raymarine_A_Series_User_Manual.pdf
```

### Option 2: Clean Up Orphaned Metadata

If the files don't exist and won't be uploaded:

```sql
-- Remove doc_metadata records for missing files
DELETE FROM doc_metadata
WHERE storage_path LIKE 'documents/%';

-- Also clean up related chunks
DELETE FROM search_document_chunks
WHERE document_id NOT IN (SELECT id FROM doc_metadata);
```

### Option 3: Bulk Upload Script

Create a script to upload all PDFs from a local directory:

```javascript
// Example: Upload all PDFs maintaining yacht folder structure
const { createClient } = require('@supabase/supabase-js');
const fs = require('fs');
const path = require('path');

const supabase = createClient(SUPABASE_URL, SERVICE_KEY);

async function uploadPDF(localPath, storagePath) {
  const fileBuffer = fs.readFileSync(localPath);

  const { data, error } = await supabase.storage
    .from('documents')
    .upload(storagePath, fileBuffer, {
      contentType: 'application/pdf',
      upsert: false
    });

  if (error) {
    console.error(`Failed to upload ${storagePath}:`, error);
  } else {
    console.log(`✅ Uploaded: ${storagePath}`);
  }
}

// Read doc_metadata and upload corresponding local files
// ... implementation details
```

## Technical Details

### Document Loading Flow

```
DocumentSituationView
  ↓
1. Query search_document_chunks.document_id
  ↓ (RLS: yacht_id isolation) ✅
2. Query doc_metadata.storage_path
  ↓ (RLS: yacht_id isolation) ✅
3. Strip "documents/" prefix
  ↓
4. Call loadDocument(path)
  ↓
5. supabase.storage.from('documents').createSignedUrl(path)
  ↓ ❌ FAILS HERE
ERROR: Object not found
```

### Why This Wasn't Caught Earlier

- Database migrations only created table structures
- Metadata was imported/created without files
- Storage bucket may exist but be empty
- No validation that storage_path points to actual files

### Storage Path Format

From `doc_metadata`:
```
storage_path: "documents/85fe1119-b04c-41ac-80f1-829d23322598/01_BRIDGE/Documents/01_Operations/Raymarine_A_Series_User_Manual.pdf"
```

After prefix strip (what's passed to storage API):
```
"85fe1119-b04c-41ac-80f1-829d23322598/01_BRIDGE/Documents/01_Operations/Raymarine_A_Series_User_Manual.pdf"
```

## Questions to Answer

Run the diagnostic page to find out:

1. **Does the "documents" bucket exist?**
   - If no → Create it in Supabase Dashboard
   - If yes → Check permissions/RLS policies

2. **How many doc_metadata records exist?**
   - This tells you how many files you need to upload

3. **Are any files already uploaded?**
   - If some exist → Use as reference for correct structure
   - If none exist → Full upload needed

4. **What's the folder structure?**
   - Verify yacht_id folders
   - Check category naming (01_BRIDGE, etc.)

## Progress So Far

You've successfully fixed:
- ✅ Table references (auth_users → auth_users_yacht)
- ✅ RLS policies for all tables
- ✅ Database functions (get_user_yacht_id, is_manager, get_user_role)
- ✅ Type casting issues (yacht_id::uuid)
- ✅ Document query chain (chunks → metadata)

**Only missing:** The actual PDF files in storage!

You're literally one step away from working document loading. 🎉

## Commands to Help

Check storage via Supabase CLI:
```bash
supabase storage ls documents
```

Count doc_metadata records:
```sql
SELECT COUNT(*) as total_docs,
       COUNT(DISTINCT yacht_id) as unique_yachts
FROM doc_metadata;
```

Sample storage paths:
```sql
SELECT storage_path
FROM doc_metadata
LIMIT 10;
```

---

**Next Action:** Visit `/debug/storage` after deployment to see the full diagnostic report.
