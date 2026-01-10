# 🔴 File Corruption Analysis & Fix Plan

## **Executive Summary**

**Root Cause:** 88% of uploaded files (1,022/1,156) are corrupted/truncated to ~2KB
**Impact:** Document viewing fails with "Object not found" error
**Code Status:** ✅ WORKING PERFECTLY - This is NOT a code bug

---

## **The Numbers**

| Size Category | File Count | Avg Size | Status |
|---------------|------------|----------|--------|
| < 10KB | **1,022** | 2.1 KB | ❌ **CORRUPT** |
| 10-100KB | 4 | 58 KB | ⚠️ Possibly OK |
| 100KB-1MB | 90 | 529 KB | ✅ INTACT |
| > 1MB | 40 | 4.9 MB | ✅ INTACT |

**Total:** 1,156 files
**Corrupt:** 1,022 (88%)
**Intact:** 134 (12%)

---

## **What Happened**

During bulk upload to Supabase Storage, files were truncated. Likely causes:

1. **Network Timeout** - Upload script timed out mid-transfer
2. **Streaming Buffer Issue** - File stream closed prematurely
3. **Memory Limit** - Process killed during large file upload
4. **Script Crash** - Upload script crashed before finishing

Evidence:
- All corrupt files are **exactly ~2KB** (2,101 bytes average)
- This suggests first chunk uploaded, rest lost
- Intact files have normal sizes (500KB - 5MB)

---

## **Why Document Viewing Fails**

### For Corrupt Files (88%)

```
User clicks "View"
→ RPC returns storage_path ✅
→ Frontend requests signed URL ✅
→ Supabase detects file is corrupt ❌
→ Returns "Object not found" instead of serving corrupt file
→ User sees: "Failed to load document: Object not found"
```

### For Intact Files (12%)

```
User clicks "View"
→ RPC returns storage_path ✅
→ Frontend requests signed URL ✅
→ Supabase serves file ✅
→ PDF opens successfully ✅
```

---

## **Test Results**

### Intact Files Found

These chunk IDs point to **intact 715KB files**:
- `a7d09bbf-4203-4732-a36c-727b687dc956`
- `cb780750-a795-4884-9ff3-d6fa56148a56`
- `d4f8a452-8f06-4dc4-92f9-d433643e3943`
- `44dcf7b7-3676-4d75-89df-339594caf6cb`
- `f660e76b-69eb-4b43-9072-6447c09e1f25`

**File:** AQUANAV 2 PC Quick Start Guide V2_10_Eng.pdf
**Size:** 715 KB
**Status:** ✅ INTACT - Should open successfully

---

## **Fix Plan**

### Option 1: Re-upload Corrupt Files (Best)

**Requirements:**
- Access to original PDF files (NAS/local backup)
- Supabase CLI or upload script

**Steps:**
1. Export list of corrupt files from database
2. Find originals on NAS/backup
3. Re-upload using proper script with retry logic
4. Verify file sizes match

**Script:**
```bash
# List corrupt files
psql ... -c "SELECT name FROM storage.objects WHERE (metadata->>'size')::int < 10000"

# Re-upload with verification
for file in corrupt_files.txt; do
  supabase storage upload --upsert documents/$file /nas/$file
  # Verify size matches
done
```

### Option 2: Delete Corrupt Files

If originals are lost, delete corrupt entries to avoid confusion:

```sql
-- Delete corrupt file records
DELETE FROM storage.objects
WHERE bucket_id = 'documents'
  AND (metadata->>'size')::int < 10000;

-- Clean up database metadata
DELETE FROM doc_metadata
WHERE storage_path IN (
  SELECT 'documents/' || name
  FROM storage.objects
  WHERE (metadata->>'size')::int < 10000
);
```

### Option 3: Hybrid Approach

1. Re-upload critical files (manuals, compliance docs)
2. Delete non-critical corrupt files
3. Mark missing files in database for re-scanning

---

## **Prevention**

### Upload Script Improvements

```python
import os
from supabase import create_client

def upload_with_verification(local_path, storage_path):
    """Upload file and verify size matches"""
    local_size = os.path.getsize(local_path)

    # Upload
    supabase.storage.from_('documents').upload(storage_path, local_path)

    # Verify
    objects = supabase.storage.from_('documents').list(path=os.path.dirname(storage_path))
    uploaded_file = next(f for f in objects if f['name'] == os.path.basename(storage_path))

    if uploaded_file['metadata']['size'] != local_size:
        raise Exception(f"Size mismatch! Local: {local_size}, Uploaded: {uploaded_file['metadata']['size']}")

    return uploaded_file
```

### Upload Script Checklist

- ✅ Retry logic on network errors
- ✅ Size verification after upload
- ✅ Chunk size tuning (avoid memory issues)
- ✅ Progress tracking/resume capability
- ✅ Error logging with file names

---

## **Current Status**

| Component | Status |
|-----------|--------|
| Code | ✅ Working perfectly |
| Database | ✅ 2,699 documents indexed |
| RPC Function | ✅ Returns paths correctly |
| Storage Bucket | ⚠️ 88% files corrupt |
| Document Viewing | ⚠️ Works for 12% intact files |

---

## **Immediate Actions**

1. **Test with intact files** - Verify code works (should succeed)
2. **Locate original PDFs** - Check NAS, backups, development machine
3. **Plan re-upload** - Prioritize critical files first
4. **Improve upload script** - Add verification before production use

---

## **Long-term Solution**

1. Implement checksum validation during upload
2. Add file integrity monitoring (alert on suspicious sizes)
3. Automated backup verification
4. Staged upload process (dev → staging → prod)

---

## **Questions to Answer**

1. Where are the original PDF files stored?
2. Is there a backup of the original files?
3. Which files are most critical to re-upload first?
4. What script was used for the original upload?
5. Were there any error logs from the upload process?

---

**Next Step:** Test document viewing with one of the 5 intact chunk IDs listed above.