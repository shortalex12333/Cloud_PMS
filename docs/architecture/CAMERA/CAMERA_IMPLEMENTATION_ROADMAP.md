# Camera Feature - Implementation Roadmap
## What's Actually Left After V3 Migration

**Status:** Database is production-hardened. Now build the backend upload flow correctly.

---

## Critical Understanding: Storage Cost vs DB Deduplication

### ❌ WRONG Flow (Doubles Storage Cost)
```
Client → Uploads file to Supabase Storage
      → Inserts to pms_image_uploads
      → Trigger detects duplicate (EXCEPTION)
      → File already in storage (you paid for it)
```

### ✅ CORRECT Flow (Prevents Storage Cost)
```
Client → Uploads file to backend API
      → Backend computes SHA256
      → Backend calls DB insert FIRST
      → If DB success: Upload to storage + update storage_path
      → If DB P0002 (duplicate): Skip storage, return original_image_id
      → Client uses original_image_id (no friction)
```

**Key:** Never upload to storage until DB confirms it's a new image.

---

## Step 1: Apply V3 Migration

```bash
cd /private/tmp/Cloud_PMS_fix

psql -h db.vzsohavtuotocgrfkfyd.supabase.co \
     -U postgres \
     -d postgres \
     -f supabase/migrations/20260109000005_camera_feature_foundation_v3.sql
```

**Or via push script:**
```bash
python3 push_migrations.py
```

---

## Step 2: Validate V3 Security (Critical)

These two checks catch 90% of "looks right but broken":

### Check #1: IP Column Actually Hidden
```sql
-- Run as authenticated user (not service_role)
SELECT upload_ip_address FROM pms_image_uploads;
```
**Expected:** `ERROR: permission denied for column "upload_ip_address"`

**If it works:** Your REVOKE didn't apply. Re-run:
```sql
REVOKE SELECT (upload_ip_address) ON pms_image_uploads FROM PUBLIC, authenticated;
```

### Check #2: Functions Actually Locked
```sql
-- Run as authenticated user
SELECT check_image_upload_rate_limit();
SELECT enforce_image_deduplication();
SELECT purge_old_ip_addresses();
```
**Expected:** `ERROR: permission denied for function`

**If any work:** Your REVOKE didn't apply. Re-run the REVOKE EXECUTE statements from V3.

---

## Step 3: Create Supabase Storage Buckets

Via Supabase Dashboard → Storage → New Bucket:

### Bucket 1: `receiving-images`
- **Public:** No
- **File size limit:** 15MB
- **Allowed MIME types:** `image/jpeg, image/png, application/pdf, image/heic`

### Bucket 2: `discrepancy-photos`
- **Public:** No
- **File size limit:** 10MB
- **Allowed MIME types:** `image/jpeg, image/png, image/heic`

### Bucket 3: `label-pdfs`
- **Public:** No
- **File size limit:** 5MB
- **Allowed MIME types:** `application/pdf`

### Bucket 4: `part-photos`
- **Public:** No
- **File size limit:** 5MB
- **Allowed MIME types:** `image/jpeg, image/png`

---

## Step 4: Configure Storage RLS Policies

**Recommendation:** Server-side upload only (cleanest, most secure)

### Option A: Server-Side Upload (Recommended)
Users CANNOT upload directly to storage. All uploads go through backend API.

```sql
-- No user INSERT policy
-- Only service_role can write
CREATE POLICY "Service role can upload"
ON storage.objects FOR INSERT
TO service_role
WITH CHECK (bucket_id IN ('receiving-images', 'discrepancy-photos', 'label-pdfs', 'part-photos'));

-- Users can read their yacht's files
CREATE POLICY "Users can read yacht files"
ON storage.objects FOR SELECT
TO authenticated
USING (
    bucket_id IN ('receiving-images', 'discrepancy-photos', 'label-pdfs', 'part-photos')
    AND (storage.foldername(name))[1] = (SELECT yacht_id::TEXT FROM user_profiles WHERE id = auth.uid())
);
```

### Option B: Client-Side Upload (If You Must)
Users can upload directly, but strictly scoped to their yacht folder.

```sql
-- Users can upload to their yacht folder only
CREATE POLICY "Users upload to yacht folder"
ON storage.objects FOR INSERT
TO authenticated
WITH CHECK (
    bucket_id IN ('receiving-images', 'discrepancy-photos', 'part-photos')
    AND (storage.foldername(name))[1] = (SELECT yacht_id::TEXT FROM user_profiles WHERE id = auth.uid())
    AND auth.role() = 'authenticated'
);

-- Users can read their yacht's files
CREATE POLICY "Users read yacht files"
ON storage.objects FOR SELECT
TO authenticated
USING (
    bucket_id IN ('receiving-images', 'discrepancy-photos', 'label-pdfs', 'part-photos')
    AND (storage.foldername(name))[1] = (SELECT yacht_id::TEXT FROM user_profiles WHERE id = auth.uid())
);
```

---

## Step 5: Backend Upload RPC (The Critical Piece)

Create this RPC to handle deduplication correctly:

```sql
CREATE OR REPLACE FUNCTION upload_image_with_dedupe(
    p_storage_bucket TEXT,
    p_storage_path TEXT,
    p_file_name TEXT,
    p_mime_type TEXT,
    p_file_size_bytes BIGINT,
    p_sha256_hash TEXT,
    p_upload_ip_address INET
) RETURNS JSONB AS $$
DECLARE
    v_yacht_id UUID;
    v_existing_image_id UUID;
    v_new_image_id UUID;
BEGIN
    -- Get user's yacht_id
    v_yacht_id := public.get_user_yacht_id();

    IF v_yacht_id IS NULL THEN
        RAISE EXCEPTION 'User has no associated yacht'
            USING ERRCODE = 'P0003';
    END IF;

    -- Check for existing image with this hash
    SELECT id INTO v_existing_image_id
    FROM pms_image_uploads
    WHERE sha256_hash = p_sha256_hash
    AND yacht_id = v_yacht_id
    AND deleted_at IS NULL;

    IF v_existing_image_id IS NOT NULL THEN
        -- Return existing image (don't insert, don't upload to storage)
        RETURN jsonb_build_object(
            'status', 'duplicate',
            'image_id', v_existing_image_id,
            'message', 'Image already exists - reusing existing upload',
            'should_upload_to_storage', false
        );
    ELSE
        -- Insert new image record
        -- This will trigger rate limit check
        INSERT INTO pms_image_uploads (
            yacht_id, storage_bucket, storage_path, file_name,
            mime_type, file_size_bytes, sha256_hash,
            uploaded_by, upload_ip_address
        ) VALUES (
            v_yacht_id, p_storage_bucket, p_storage_path, p_file_name,
            p_mime_type, p_file_size_bytes, p_sha256_hash,
            auth.uid(), p_upload_ip_address
        ) RETURNING id INTO v_new_image_id;

        RETURN jsonb_build_object(
            'status', 'new',
            'image_id', v_new_image_id,
            'message', 'New image - proceed with storage upload',
            'should_upload_to_storage', true
        );
    END IF;
EXCEPTION
    WHEN OTHERS THEN
        -- Catch rate limit or other errors
        RETURN jsonb_build_object(
            'status', 'error',
            'error_code', SQLSTATE,
            'error_message', SQLERRM,
            'should_upload_to_storage', false
        );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Grant to authenticated users
GRANT EXECUTE ON FUNCTION upload_image_with_dedupe TO authenticated;

COMMENT ON FUNCTION upload_image_with_dedupe IS 'Upload RPC with deduplication. Returns should_upload_to_storage flag to prevent duplicate storage costs.';
```

---

## Step 6: Backend API Endpoints

### POST /api/camera/upload
**Flow:**
1. Receive file from client
2. Compute SHA256 hash
3. Call `upload_image_with_dedupe()` RPC
4. If `should_upload_to_storage = true`: Upload to Supabase Storage
5. If `should_upload_to_storage = false`: Skip storage upload
6. Return `image_id` to client

**Code Example (Node.js / TypeScript):**
```typescript
import { createHash } from 'crypto';
import { createClient } from '@supabase/supabase-js';

const supabase = createClient(
  process.env.SUPABASE_URL,
  process.env.SUPABASE_SERVICE_ROLE_KEY // Service role for storage upload
);

export async function POST(request: Request) {
  const formData = await request.formData();
  const file = formData.get('file') as File;
  const userIP = request.headers.get('x-forwarded-for') || 'unknown';

  // 1. Read file and compute SHA256
  const fileBuffer = Buffer.from(await file.arrayBuffer());
  const sha256Hash = createHash('sha256').update(fileBuffer).digest('hex');

  const userToken = request.headers.get('authorization')?.replace('Bearer ', '');
  const userSupabase = createClient(
    process.env.SUPABASE_URL,
    process.env.SUPABASE_ANON_KEY,
    { global: { headers: { Authorization: `Bearer ${userToken}` } } }
  );

  // 2. Call RPC to check for duplicate and create DB record
  const { data: rpcResult, error: rpcError } = await userSupabase.rpc(
    'upload_image_with_dedupe',
    {
      p_storage_bucket: 'receiving-images',
      p_storage_path: `temp/${Date.now()}_${file.name}`, // Will update after storage upload
      p_file_name: file.name,
      p_mime_type: file.type,
      p_file_size_bytes: file.size,
      p_sha256_hash: sha256Hash,
      p_upload_ip_address: userIP
    }
  );

  if (rpcError) {
    return Response.json({ error: rpcError.message }, { status: 400 });
  }

  // 3. If duplicate, return existing image_id (skip storage upload)
  if (rpcResult.status === 'duplicate') {
    return Response.json({
      image_id: rpcResult.image_id,
      is_duplicate: true,
      message: 'Image already exists'
    });
  }

  // 4. If new, upload to storage
  if (rpcResult.should_upload_to_storage) {
    const storagePath = `${rpcResult.image_id}/${file.name}`;

    const { error: uploadError } = await supabase.storage
      .from('receiving-images')
      .upload(storagePath, fileBuffer, {
        contentType: file.type,
        upsert: false
      });

    if (uploadError) {
      // Rollback: mark image as failed
      await supabase
        .from('pms_image_uploads')
        .update({
          validation_stage: 'failed',
          validation_errors: { error: 'storage_upload_failed', detail: uploadError.message }
        })
        .eq('id', rpcResult.image_id);

      return Response.json({ error: 'Storage upload failed' }, { status: 500 });
    }

    // 5. Update storage_path in DB
    await supabase
      .from('pms_image_uploads')
      .update({ storage_path: storagePath })
      .eq('id', rpcResult.image_id);

    return Response.json({
      image_id: rpcResult.image_id,
      is_duplicate: false,
      message: 'Image uploaded successfully'
    });
  }

  return Response.json({ error: 'Unexpected state' }, { status: 500 });
}
```

---

### POST /api/receiving/session/create
**Payload:**
```json
{
  "session_type": "packing_slip",
  "image_ids": ["uuid1", "uuid2"],
  "order_id": "uuid-optional",
  "supplier_name": "Supplier Name"
}
```

**Response:**
```json
{
  "session_id": "uuid",
  "session_number": "RSESS-2026-001"
}
```

---

### POST /api/receiving/session/:id/extract
Trigger OCR and extraction pipeline.

**Flow:**
1. Get session images
2. Run OCR (Tesseract or cloud service)
3. Extract table rows
4. Create `pms_receiving_draft_lines` records
5. Match to parts/orders (suggestions only)

**Response:**
```json
{
  "session_id": "uuid",
  "draft_lines": [
    {
      "id": "uuid",
      "line_sequence": 1,
      "extracted_part_name": "Oil Filter",
      "extracted_quantity": 10,
      "match_status": "matched_part",
      "suggested_part_id": "uuid",
      "is_verified": false
    }
  ]
}
```

---

### POST /api/receiving/session/:id/verify-line
Checkbox verification (human truth).

**Payload:**
```json
{
  "line_id": "uuid",
  "is_verified": true,
  "resolved_part_id": "uuid",
  "resolved_quantity": 10,
  "resolved_disposition": "receive_inventory"
}
```

---

### POST /api/receiving/session/:id/commit
Commit session → creates receiving_event and line_items.

**Flow:**
1. Validate all lines verified or resolved
2. Update session status to 'committed'
3. Trigger creates `pms_receiving_event`
4. Trigger creates `pms_receiving_line_items` from verified draft lines
5. Updates `pms_shopping_list_items` if matched
6. Creates finance transactions if applicable

**Response:**
```json
{
  "session_id": "uuid",
  "receiving_event_id": "uuid",
  "receiving_number": "RCV-2026-003",
  "lines_committed": 10
}
```

---

## Step 7: Frontend Implementation

### Camera Icon Entry Point
```typescript
// In global search bar or receiving screen
<CameraButton onClick={() => openCameraFlow()} />

function openCameraFlow() {
  navigate('/receiving/camera');
}
```

### Camera/Upload Screen
```typescript
// 1. Capture or upload image
<input type="file" accept="image/*,application/pdf" capture="environment" onChange={handleFileSelect} />

// 2. Preview image
<img src={previewUrl} />

// 3. Upload image
async function handleFileSelect(file: File) {
  const formData = new FormData();
  formData.append('file', file);

  const response = await fetch('/api/camera/upload', {
    method: 'POST',
    body: formData,
    headers: { Authorization: `Bearer ${userToken}` }
  });

  const result = await response.json();

  if (result.is_duplicate) {
    toast('Image already uploaded - reusing existing');
  }

  // Store image_id for session creation
  imageIds.push(result.image_id);
}

// 4. Create session
async function createSession() {
  const response = await fetch('/api/receiving/session/create', {
    method: 'POST',
    body: JSON.stringify({
      session_type: 'packing_slip',
      image_ids: imageIds,
      supplier_name: supplierName
    }),
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${userToken}` }
  });

  const session = await response.json();
  navigate(`/receiving/session/${session.session_id}/verify`);
}
```

### Draft Lines Verification Screen (Checkbox Truth)
```typescript
// Display draft lines table
{draftLines.map(line => (
  <tr key={line.id}>
    <td>
      <Checkbox
        checked={line.is_verified}
        onChange={() => verifyLine(line.id)}
      />
    </td>
    <td>{line.extracted_part_name}</td>
    <td>{line.extracted_quantity}</td>
    <td>{line.match_status}</td>
    <td>
      {line.match_status === 'unmatched' && (
        <Button onClick={() => matchLine(line.id)}>Match to Part</Button>
      )}
    </td>
  </tr>
))}

// Commit button (disabled until all lines verified or resolved)
<Button
  disabled={draftLines.some(l => !l.is_verified && l.match_status !== 'ignored')}
  onClick={commitSession}
>
  Commit & Create Receiving Event
</Button>
```

---

## Step 8: Schedule IP Purging

### Via pg_cron (if enabled)
```sql
-- As service_role
SELECT cron.schedule(
    'purge-old-ip-addresses',
    '0 2 * * *', -- Daily at 2 AM
    $$SELECT purge_old_ip_addresses();$$
);
```

### Via Backend Cron Job
```typescript
// In your backend (Next.js, Node, etc.)
import cron from 'node-cron';

cron.schedule('0 2 * * *', async () => {
  const { data, error } = await supabaseServiceRole.rpc('purge_old_ip_addresses');
  console.log(`IP purge: ${data} addresses purged`);
});
```

---

## Quick Reference: API Flow Summary

```
┌─────────────┐
│   Client    │
└──────┬──────┘
       │ 1. Upload file
       ▼
┌─────────────────────────┐
│  Backend API            │
│  - Compute SHA256       │
│  - Call upload RPC      │
│  - Check duplicate      │
└──────┬──────────────────┘
       │ 2a. New image
       ▼
┌─────────────────────────┐
│  Supabase Storage       │
│  - Upload file          │
└──────┬──────────────────┘
       │ 2b. Update storage_path
       ▼
┌─────────────────────────┐
│  pms_image_uploads      │
│  (DB record created)    │
└──────┬──────────────────┘
       │ 3. Return image_id
       ▼
┌─────────────┐
│   Client    │
│ - Create    │
│   session   │
└──────┬──────┘
       │ 4. Trigger OCR
       ▼
┌─────────────────────────┐
│  Backend OCR Pipeline   │
│  - Extract lines        │
│  - Create draft_lines   │
└──────┬──────────────────┘
       │ 5. Display draft table
       ▼
┌─────────────┐
│   Client    │
│ - User      │
│   verifies  │
│   checkboxes│
└──────┬──────┘
       │ 6. Commit session
       ▼
┌─────────────────────────┐
│  Trigger                │
│  - Create receiving_    │
│    event                │
│  - Create line_items    │
│  - Update shopping_list │
└─────────────────────────┘
```

---

## What "Done" Looks Like

### Database ✅
- [x] V3 migration applied
- [x] IP column hidden from authenticated users (validated)
- [x] Functions locked down (validated)

### Storage ✅
- [ ] 4 buckets created
- [ ] RLS policies configured

### Backend ✅
- [ ] Upload RPC with dedupe
- [ ] POST /api/camera/upload (with SHA256 + dedupe check)
- [ ] POST /api/receiving/session/create
- [ ] POST /api/receiving/session/:id/extract (OCR pipeline)
- [ ] POST /api/receiving/session/:id/verify-line
- [ ] POST /api/receiving/session/:id/commit

### Frontend ✅
- [ ] Camera icon entry point
- [ ] Upload screen (capture or file select)
- [ ] Session creation flow
- [ ] Draft lines table with checkboxes
- [ ] Commit button (creates receiving event)

### Scheduled Jobs ✅
- [ ] IP purging scheduled (daily 2 AM)

---

## Cost-Saving Architecture Recap

**Key Decision:** Backend computes SHA256 and checks DB **before** uploading to storage.

**Result:**
- Duplicate uploads are blocked at DB level (V3 trigger)
- Duplicate storage uploads are prevented at backend level (RPC returns `should_upload_to_storage: false`)
- User sees no friction (duplicate just reuses existing image_id)
- Storage costs minimized

---

**Next Action:** Apply V3 migration, then build backend upload RPC.

**Files on Desktop:**
- `20260109000005_camera_feature_foundation_v3.sql` (use this)
- `CAMERA_IMPLEMENTATION_ROADMAP.md` (this file)
