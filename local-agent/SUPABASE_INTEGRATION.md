# Supabase Integration Guide for CelesteOS Local Agent

**CRITICAL:** The local agent must be configured correctly to work with your Supabase instance.

---

## Supabase Instance Details

**URL:** `https://vzsohavtuotocgrfkfyd.supabase.co`

**Project Reference:** `vzsohavtuotocgrfkfyd`

---

## Authentication Configuration

The agent needs **TWO** authentication mechanisms:

### 1. Yacht Signature (Custom Header)
Used to identify which yacht is uploading:
```
X-Yacht-Signature: <unique_yacht_signature>
```

### 2. Supabase Service Role Key (Bearer Token)
Required for all Supabase API calls:
```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ6c29oYXZ0dW90b2NncmZrZnlkIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MzU5Mjg3NSwiZXhwIjoyMDc5MTY4ODc1fQ.fC7eC_4xGnCHIebPzfaJ18pFMPKgImE7BuN0I3A-pSY
```

**Storage:** Store the service role key in macOS Keychain (never in config file).

---

## Configuration Updates Required

### 1. Update `config.json`

```json
{
  "yacht_signature": "YOUR_YACHT_SIGNATURE",
  "yacht_name": "YOUR_YACHT_NAME",

  "api_endpoint": "https://vzsohavtuotocgrfkfyd.supabase.co",
  "supabase_url": "https://vzsohavtuotocgrfkfyd.supabase.co",
  "supabase_anon_key": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ6c29oYXZ0dW90b2NncmZrZnlkIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjM1OTI4NzUsImV4cCI6MjA3OTE2ODg3NX0.JhJLvLSfLD3OtPDxTgHqgF8dNaZk8ius62jKN68E4WE",

  "nas_path": "/Volumes/YachtNAS/Engineering",
  "nas_type": "smb",
  ...
}
```

### 2. Store Service Role Key in Keychain

During setup, the agent will prompt for:
- **Yacht Signature**
- **Supabase Service Role Key** (stored in Keychain)

**Never commit the service role key to git or store it in plain text.**

---

## API Endpoints

The agent expects these endpoints to exist on Supabase:

### 1. Initialize Upload
```
POST https://vzsohavtuotocgrfkfyd.supabase.co/functions/v1/ingest/init

Headers:
  Authorization: Bearer <service_role_key>
  X-Yacht-Signature: <yacht_signature>
  Content-Type: application/json

Body:
{
  "filename": "MTU_Manual.pdf",
  "sha256": "abc123...",
  "size_bytes": 52428800,
  "source": "nas"
}

Response:
{
  "upload_id": "uuid",
  "storage_key": "yachts/<yacht_id>/temp/<upload_id>/",
  "expected_chunks": 12
}
```

### 2. Upload Chunk
```
PATCH https://vzsohavtuotocgrfkfyd.supabase.co/functions/v1/ingest/upload_chunk

Headers:
  Authorization: Bearer <service_role_key>
  X-Yacht-Signature: <yacht_signature>
  Upload-ID: <upload_uuid>
  Chunk-Index: 0
  Chunk-SHA256: def456...
  Content-Type: application/octet-stream

Body: <raw chunk bytes>

Response:
{
  "status": "ok"
}
```

### 3. Complete Upload
```
POST https://vzsohavtuotocgrfkfyd.supabase.co/functions/v1/ingest/complete

Headers:
  Authorization: Bearer <service_role_key>
  X-Yacht-Signature: <yacht_signature>
  Content-Type: application/json

Body:
{
  "upload_id": "uuid",
  "total_chunks": 12,
  "sha256": "abc123...",
  "filename": "MTU_Manual.pdf"
}

Response:
{
  "document_id": "uuid",
  "status": "received",
  "queued_for_indexing": true
}
```

---

## Supabase Edge Functions Required

You need to deploy these Edge Functions to Supabase:

### 1. `ingest-init` Function
**Path:** `supabase/functions/ingest-init/index.ts`

**Purpose:** Initialize upload, create record in `documents` table

**Logic:**
1. Validate yacht signature against `yachts.signature`
2. Calculate expected chunks
3. Create temp storage path
4. Insert into `documents` table with `indexed = false`
5. Return upload_id

### 2. `ingest-upload-chunk` Function
**Path:** `supabase/functions/ingest-upload-chunk/index.ts`

**Purpose:** Receive and store individual chunks

**Logic:**
1. Validate upload_id
2. Store chunk in Supabase Storage: `yachts/<yacht_id>/temp/<upload_id>/chunk_<index>`
3. Verify chunk SHA256
4. Track uploaded chunks

### 3. `ingest-complete` Function
**Path:** `supabase/functions/ingest-complete/index.ts`

**Purpose:** Assemble chunks, trigger indexing

**Logic:**
1. Reassemble all chunks
2. Verify final file SHA256
3. Move to permanent storage: `yachts/<yacht_id>/raw/<sha256>/<filename>`
4. Update `documents` table with `storage_path`
5. Trigger indexing pipeline (n8n webhook)
6. Delete temp chunks
7. Return document_id

---

## Database Tables Used

### `yachts`
```sql
INSERT INTO yachts (id, name, signature, status)
VALUES (
  gen_random_uuid(),
  'STELLA MARIS',
  'ABC123XYZ',  -- This is the yacht signature
  'active'
);
```

### `documents`
```sql
-- Created by ingest-init function
INSERT INTO documents (
  id,
  yacht_id,
  source,
  filename,
  content_type,
  size_bytes,
  sha256,
  storage_path,
  indexed,
  created_at
) VALUES (
  <upload_id>,
  <yacht_id from signature>,
  'nas',
  'MTU_Manual.pdf',
  'application/pdf',
  52428800,
  'abc123...',
  NULL,  -- Set after upload complete
  false,
  NOW()
);
```

---

## Supabase Storage Buckets

Create these storage buckets:

### 1. `yacht-documents`
**Path structure:**
```
yacht-documents/
├── yachts/
│   ├── <yacht_id>/
│   │   ├── temp/          # Temporary upload chunks
│   │   │   └── <upload_id>/
│   │   │       ├── chunk_0
│   │   │       ├── chunk_1
│   │   │       └── ...
│   │   └── raw/           # Permanent storage
│   │       └── <sha256>/
│   │           └── <filename>
```

**Policies:**
- Service role: Full access
- Anon: No access
- Authenticated users: Read-only for their yacht

---

## Row Level Security (RLS)

Enable RLS on all tables:

### `documents` table policy:
```sql
CREATE POLICY "Users can only access their yacht's documents"
ON documents
FOR SELECT
USING (
  yacht_id IN (
    SELECT yacht_id FROM users WHERE id = auth.uid()
  )
);

CREATE POLICY "Service role can insert documents"
ON documents
FOR INSERT
WITH CHECK (true);
```

### `yachts` table policy:
```sql
CREATE POLICY "Users can view their yacht"
ON yachts
FOR SELECT
USING (
  id IN (
    SELECT yacht_id FROM users WHERE id = auth.uid()
  )
);
```

---

## Updated Agent Flow

1. **Agent starts** → Loads config with Supabase URL
2. **Scans NAS** → Discovers files
3. **Computes SHA256** → For each file
4. **Calls init endpoint** → POST to Supabase Edge Function
   - Headers: `Authorization: Bearer <service_role_key>` + `X-Yacht-Signature`
   - Supabase validates yacht signature
   - Returns upload_id
5. **Chunks file** → 64MB chunks with gzip
6. **Uploads chunks** → PATCH to Supabase Edge Function
   - Stored in Supabase Storage
7. **Calls complete** → POST to Supabase Edge Function
   - Supabase reassembles chunks
   - Moves to permanent storage
   - Triggers n8n indexing webhook
8. **Cleanup** → Deletes temp chunks locally

---

## n8n Integration

After upload complete, Supabase triggers n8n webhook:

```
POST https://n8n.yourdomain.com/webhook/celeste-ingest

Body:
{
  "document_id": "uuid",
  "yacht_id": "uuid",
  "filename": "MTU_Manual.pdf",
  "storage_path": "yachts/<yacht_id>/raw/<sha256>/MTU_Manual.pdf",
  "sha256": "abc123..."
}
```

n8n then runs the indexing pipeline from `indexing-pipeline.md`.

---

## Testing Checklist

### 1. Test Supabase Connectivity
```bash
curl https://vzsohavtuotocgrfkfyd.supabase.co/rest/v1/ \
  -H "apikey: <anon_key>" \
  -H "Authorization: Bearer <service_role_key>"
```

### 2. Test Yacht Signature Lookup
```bash
curl https://vzsohavtuotocgrfkfyd.supabase.co/rest/v1/yachts?signature=eq.ABC123XYZ \
  -H "apikey: <anon_key>" \
  -H "Authorization: Bearer <service_role_key>"
```

Should return the yacht record.

### 3. Test Storage Access
```bash
# Upload test file
curl -X POST https://vzsohavtuotocgrfkfyd.supabase.co/storage/v1/object/yacht-documents/test.txt \
  -H "Authorization: Bearer <service_role_key>" \
  -H "Content-Type: text/plain" \
  --data "test content"
```

### 4. Test Edge Function (after deployment)
```bash
curl -X POST https://vzsohavtuotocgrfkfyd.supabase.co/functions/v1/ingest/init \
  -H "Authorization: Bearer <service_role_key>" \
  -H "X-Yacht-Signature: ABC123XYZ" \
  -H "Content-Type: application/json" \
  -d '{
    "filename": "test.pdf",
    "sha256": "abc123",
    "size_bytes": 1000,
    "source": "nas"
  }'
```

---

## Security Considerations

### 1. Service Role Key Protection
- **NEVER** commit service role key to git
- Store in macOS Keychain
- Rotate key if compromised

### 2. Yacht Signature Validation
- Edge functions MUST validate yacht signature
- Signature must exist in `yachts` table with `status = 'active'`
- Log all upload attempts with yacht signature

### 3. Storage Isolation
- Each yacht MUST have isolated storage path
- Use RLS policies to prevent cross-yacht access
- Validate `yacht_id` on every operation

### 4. Upload Size Limits
- Max file size: 10GB (configurable)
- Max chunk size: 64MB
- Timeout: 10 minutes per chunk

---

## Troubleshooting

### Issue: "401 Unauthorized"
**Cause:** Invalid or expired service role key

**Fix:**
1. Verify service role key in Keychain
2. Check key hasn't expired
3. Ensure key matches your Supabase project

### Issue: "Yacht signature not found"
**Cause:** Yacht not registered in `yachts` table

**Fix:**
1. Insert yacht record in Supabase:
```sql
INSERT INTO yachts (id, name, signature, status)
VALUES (gen_random_uuid(), 'YOUR YACHT', 'YOUR_SIGNATURE', 'active');
```

### Issue: "Storage bucket not found"
**Cause:** Bucket not created

**Fix:**
1. Go to Supabase Dashboard → Storage
2. Create bucket `yacht-documents`
3. Set public access to OFF

### Issue: "Edge function not found"
**Cause:** Edge functions not deployed

**Fix:**
1. Deploy Edge Functions:
```bash
supabase functions deploy ingest-init
supabase functions deploy ingest-upload-chunk
supabase functions deploy ingest-complete
```

---

## Migration from Mock API

If you've been testing with a mock API endpoint, update:

1. **Config:** Change `api_endpoint` to Supabase URL
2. **Keychain:** Add service role key
3. **Test:** Run `celesteos-agent test-nas` to verify connectivity

---

## Next Steps

1. ✅ Deploy Supabase Edge Functions
2. ✅ Create storage buckets
3. ✅ Insert yacht record in `yachts` table
4. ✅ Configure RLS policies
5. ✅ Update agent config with Supabase URL
6. ✅ Store service role key in Keychain
7. ✅ Test upload with small file
8. ✅ Verify file appears in Supabase Storage
9. ✅ Verify document record created
10. ✅ Test indexing pipeline trigger

---

## Contact

If you encounter integration issues, provide:
- Agent logs: `~/.celesteos/logs/celesteos-agent.log`
- Supabase function logs (from Dashboard)
- Yacht signature being used
- Error messages (sanitized of credentials)
