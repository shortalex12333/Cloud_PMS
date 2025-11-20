# CelesteOS MVP Uploader with NAS Metadata

**File upload script with directory structure metadata for yacht-aware storage**

Worker 4 - Local Agent Engineer

---

## Purpose

This script uploads yacht NAS documents to the ingestion webhook **with full directory metadata** for proper yacht-aware storage and indexing.

**What it does:**
- Scans NAS folder recursively
- Extracts directory hierarchy from file paths
- Uploads each file with metadata to the n8n webhook
- Sends yacht ID, system path, and directory structure
- Prints success/failure for each upload

**What it does NOT do:**
- NO chunking
- NO SHA256 hashing
- NO database state
- NO retries
- NO concurrency
- NO daemon mode

---

## Installation

### 1. Install Python Dependencies

```bash
pip3 install requests
```

That's it. Only `requests` is needed (standard library handles the rest).

---

## Configuration

Edit `config.json`:

```json
{
  "yacht_id": "test-yacht-celeste7",
  "root_path": "/Users/celeste7/Documents/yacht-nas/ROOT",
  "webhook_url": "https://api.celeste7.ai/webhook/ingest-docs-nas-cloud"
}
```

**Fields:**
- `yacht_id` - Yacht identifier (sent in X-Yacht-ID header and form data)
- `root_path` - **NAS root folder** to scan (absolute path)
- `webhook_url` - n8n webhook endpoint

**Important:** Use `root_path` (not `folder_path`) - this is the base directory for extracting relative paths.

---

## Usage

### Run the script:

```bash
cd mvp-uploader
python3 mvp_uploader.py
```

### Expected Output:

```
============================================================
CelesteOS MVP Uploader with NAS Metadata
Testing n8n webhook ingestion
============================================================

Yacht ID: test-yacht-celeste7
Root Path: /Users/celeste7/Documents/yacht-nas/ROOT
Webhook: https://api.celeste7.ai/webhook/ingest-docs-nas-cloud

📁 Scanning folder: /Users/celeste7/Documents/yacht-nas/ROOT
✓ Found 12 files

============================================================
Starting uploads...
============================================================

📤 Uploading: manual_CAT3516.pdf
   Path: /Users/celeste7/Documents/yacht-nas/ROOT/Engineering/MainEngine/manual_CAT3516.pdf
   Size: 2458624 bytes
   System Path: Engineering/MainEngine
   Directories: ['Engineering', 'MainEngine']
   ✅ SUCCESS (200 OK)
   Response: {
     "status": "received",
     "document_id": "uuid-here"
   }

📤 Uploading: schematic_electrical.pdf
   Path: /Users/celeste7/Documents/yacht-nas/ROOT/Electrical/schematic_electrical.pdf
   Size: 1024000 bytes
   System Path: Electrical
   Directories: ['Electrical']
   ✅ SUCCESS (200 OK)

...

============================================================
UPLOAD SUMMARY
============================================================
Total files: 5
✅ Successful: 5
❌ Failed: 0

🎉 All uploads successful!
```

---

## Expected Cloud Result

After successful uploads, the n8n workflow should:

1. Receive the file via webhook
2. Store it in temporary storage
3. Log the yacht_id and filename
4. Trigger indexing pipeline (future step)

---

## Troubleshooting

### Error: "Config file not found"

**Cause:** `config.json` is missing

**Fix:** Create `config.json` in the same directory as `mvp_uploader.py`

---

### Error: "Folder does not exist"

**Cause:** The `folder_path` in config doesn't exist

**Fix:** Update `folder_path` to a valid directory:
```bash
# Check folder exists
ls -la /Users/celeste7/Documents/yacht-nas/ROOT
```

---

### Error: "Failed (Network error)"

**Cause:** Can't reach webhook URL

**Fix:**
1. Check internet connection
2. Verify webhook URL is correct
3. Test with curl:
```bash
curl -X POST https://api.celeste7.ai/webhook/ingest-docs-nas-cloud \
  -H "X-Yacht-ID: test-yacht-123" \
  -F "file=@/path/to/test.pdf" \
  -F "filename=test.pdf"
```

---

### Error: "Failed (500)"

**Cause:** n8n workflow error

**Fix:** Check n8n workflow logs for errors

---

### Error: "Failed (Timeout)"

**Cause:** Upload took longer than 60 seconds

**Fix:** Webhook might be slow. Check n8n performance.

---

## Testing with Small Files

For initial testing, create a test folder with small files:

```bash
# Create test folder
mkdir -p /tmp/test-upload

# Create test files
echo "Test document 1" > /tmp/test-upload/doc1.txt
echo "Test document 2" > /tmp/test-upload/doc2.txt
echo "Test document 3" > /tmp/test-upload/doc3.txt

# Update config.json
# "folder_path": "/tmp/test-upload"

# Run uploader
python3 mvp_uploader.py
```

---

## What Happens Next?

Once this MVP works:

1. ✅ We confirm n8n can receive files
2. ✅ We validate the webhook URL is correct
3. ✅ We test with real yacht documents
4. ⏭️ Build full production agent with:
   - SHA256 hashing
   - File chunking
   - State persistence
   - Retry logic
   - Daemon mode

---

## File Structure

```
mvp-uploader/
├── mvp_uploader.py    # Main script
├── config.json        # Configuration
└── README.md          # This file
```

---

## Technical Details

### HTTP Request Format

```
POST https://api.celeste7.ai/webhook/ingest-docs-nas-cloud

Headers:
  X-Yacht-ID: test-yacht-celeste7

Body (multipart/form-data):
  file: <binary file data>
  filename: <original_filename>
```

### Response Format (Expected)

```json
{
  "status": "received",
  "document_id": "uuid-here",
  "yacht_id": "test-yacht-celeste7",
  "filename": "manual_CAT3516.pdf"
}
```

---

## Limitations (By Design)

This is an MVP for testing only:

- ❌ No error handling beyond basic try/catch
- ❌ No retry logic (fails immediately)
- ❌ No progress tracking
- ❌ No state persistence
- ❌ No file filtering (uploads everything)
- ❌ No chunking (sends entire file)
- ❌ No concurrent uploads (sequential only)

**These will be added in the production agent.**

---

## Support

If you encounter issues:

1. Check the output for error messages
2. Verify `config.json` is correct
3. Test webhook with curl
4. Check n8n workflow is running

---

## Next Steps

After successful testing:

1. Deploy production agent from `/local-agent`
2. Configure with Supabase credentials
3. Enable daemon mode
4. Set up LaunchAgent for auto-start

See `/local-agent/DEPLOYMENT.md` for full production setup.
