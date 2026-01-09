# Complete User Journey: Frontend → Backend → Database

**Step-by-step walkthrough of user experience with detailed technical flow**

---

## 🎬 Journey 1: User Searches for Document

### User Action
User opens app, types "generator cooling" in search bar

### Frontend Flow (Stage by Stage)

#### Stage 1: Input Debouncing
**File:** `apps/web/src/hooks/useCelesteSearch.ts:80-100`

```typescript
// User types each character
onChange={(e) => handleQueryChange(e.target.value)}
  ↓
// Debounce waits 80ms after last keystroke
const debounceTimeout = setTimeout(() => {
  executeSearch(query);
}, 80);
```

**Console Output:**
```
[useCelesteSearch] 🔤 handleQueryChange: generator cooling
[useCelesteSearch] ⏲️ Debouncing for 80 ms
[useCelesteSearch] ⏲️ Debounce complete, executing search
```

---

#### Stage 2: Get Authentication Context
**File:** `apps/web/src/lib/apiClient.ts:182-202`

```typescript
async function getFullAuthContext() {
  // Get current JWT session
  const { data: { session } } = await supabase.auth.getSession();

  // Query auth_users for yacht_id
  const yachtId = await getYachtId();  // ← Problem happens here!

  // Generate yacht signature
  const yachtSignature = await getYachtSignature(yachtId);

  return {
    user_id: session.user.id,
    yacht_id: yachtId,
    yacht_signature: yachtSignature,
    ...
  };
}
```

**Actual Query Executed:**

**File:** `apps/web/src/lib/authHelpers.ts:207-212`

```typescript
const { data, error } = await supabase
  .from('auth_users')  // ← Recently changed from auth_users_yacht
  .select('yacht_id')
  .eq('auth_user_id', session.user.id)  // a35cad0b-02ff-4287-b6e4-17c96fa6a424
  .single();
```

**SQL Sent to Supabase:**
```sql
-- PostgREST translates to:
GET /rest/v1/auth_users?select=yacht_id&auth_user_id=eq.a35cad0b-02ff-4287-b6e4-17c96fa6a424

-- With headers:
Authorization: Bearer eyJhbGc...  (JWT token)
apikey: eyJhbGc...  (Supabase anon key)
```

**RLS Policy Applied:**
```sql
-- PostgreSQL adds WHERE clause:
SELECT yacht_id
FROM auth_users
WHERE auth_user_id = 'a35cad0b-02ff-4287-b6e4-17c96fa6a424'
  AND auth_user_id = auth.uid();  -- From RLS policy
```

**🔴 CURRENT PROBLEM:**

**Console Output:**
```
GET https://vzsohavtuotocgrfkfyd.supabase.co/rest/v1/auth_users?select=yacht_id&auth_user_id=eq.a35cad0b... 404 (Not Found)
[authHelpers] No yacht assignment found in database
[authHelpers] No yacht_id, skipping yacht signature
```

**Why 404?**
- Row exists (verified in Supabase SQL Editor)
- RLS policy exists (`auth_users_select_own`)
- **Theory:** Missing table GRANT or policy not fully applied

---

#### Stage 3A: If yacht_id Successfully Retrieved

**Console Output (Expected):**
```
[authHelpers] getYachtId() returns: 85fe1119-b04c-41ac-80f1-829d23322598
[authHelpers] Generating yacht signature...
[authHelpers] yacht_signature: f3a7b2c9e8d1...
```

**Yacht Signature Generation:**

**File:** `apps/web/src/lib/authHelpers.ts:250-270`

```typescript
export async function getYachtSignature(yachtId: string | null): Promise<string | null> {
  if (!yachtId) return null;

  const salt = process.env.NEXT_PUBLIC_YACHT_SALT;
  const message = `${yachtId}${salt}`;

  const msgBuffer = new TextEncoder().encode(message);
  const hashBuffer = await crypto.subtle.digest('SHA-256', msgBuffer);
  const hashArray = Array.from(new Uint8Array(hashBuffer));
  const hashHex = hashArray.map(b => b.toString(16).padStart(2, '0')).join('');

  return hashHex;
}
```

**Result:** SHA-256 hash used to prove frontend knows the yacht_id

---

#### Stage 3B: If yacht_id Fails (Current State)

**Console Output:**
```
[authHelpers] No yacht_id, skipping yacht signature
[useCelesteSearch] 📤 Sending request to: https://pipeline-core.int.celeste7.ai/webhook/search
[useCelesteSearch] 📤 Payload: {
  query: 'generator cooling',
  auth: {
    user_id: 'a35cad0b...',
    yacht_id: null,  ← PROBLEM!
    yacht_signature: null
  }
}
```

---

#### Stage 4: Send Search Request

**File:** `apps/web/src/hooks/useCelesteSearch.ts:204-214`

```typescript
const searchUrl = `${API_URL}/webhook/search`;
const response = await fetch(searchUrl, {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${jwt}`,
    'X-Yacht-Signature': yachtSignature,  // null currently
  },
  body: JSON.stringify({
    query: 'generator cooling',
    auth: {
      user_id: session.user.id,
      yacht_id: yachtId,  // null currently
      yacht_signature: yachtSignature
    },
    context: {
      client_ts: Date.now(),
      stream_id: '...',
      ...
    }
  })
});
```

**Console Output:**
```
POST https://pipeline-core.int.celeste7.ai/webhook/search 500 (Internal Server Error)
[useCelesteSearch] 📥 Response status: 500
[useCelesteSearch] Streaming failed, using fallback: Error: Search failed: 500
```

**Why 500?**
Backend expects `yacht_id` but receives `null` → crashes or rejects request

---

### Backend Flow (When Working)

#### Stage 5: Backend Receives Request

**File:** `apps/api/pipeline_service.py:203-218`

```python
@app.post("/webhook/search")
async def webhook_search(request: Request):
    body = await request.json()
    logger.info(f"[webhook/search] Received query: {body.get('query')}")

    # Extract data from frontend format
    query = body.get('query')
    auth = body.get('auth', {})
    yacht_id = auth.get('yacht_id')  # Currently gets null

    if not yacht_id:
        logger.error("[webhook/search] Missing yacht_id")
        raise HTTPException(status_code=400, detail="Missing yacht_id")

    # Call search pipeline with yacht_id
    results = await search_pipeline(query, yacht_id)
    return results
```

**Current Behavior:** Returns 400 or 500 because yacht_id is null

---

#### Stage 6: Search Pipeline Queries Database

**File:** `apps/api/pipeline_v1.py` (hypothetical)

```python
async def search_pipeline(query: str, yacht_id: str):
    # Use service_role key (bypasses RLS)
    supabase = create_client(
        os.getenv('SUPABASE_URL'),
        os.getenv('SUPABASE_SERVICE_ROLE_KEY')
    )

    # Generate query embedding
    embedding = await generate_embedding(query)

    # Search document chunks
    results = supabase.rpc('search_documents', {
        'query_embedding': embedding,
        'yacht_id_filter': yacht_id,  # Manually filter by yacht
        'match_threshold': 0.8,
        'match_count': 10
    }).execute()

    return results.data
```

**Note:** Backend uses `service_role` key which bypasses RLS, so it manually filters by yacht_id

---

### Database Flow (When Working)

#### Stage 7: PostgreSQL Executes Search

```sql
-- RPC function: search_documents
CREATE FUNCTION search_documents(
  query_embedding vector(1536),
  yacht_id_filter UUID,
  match_threshold FLOAT,
  match_count INT
)
RETURNS TABLE (
  chunk_id UUID,
  doc_path TEXT,
  chunk_text TEXT,
  similarity FLOAT
) AS $$
BEGIN
  RETURN QUERY
  SELECT
    c.chunk_id,
    c.doc_path,
    c.chunk_text,
    1 - (c.embedding <=> query_embedding) AS similarity
  FROM search_document_chunks c
  WHERE c.yacht_id = yacht_id_filter  -- Yacht isolation
    AND 1 - (c.embedding <=> query_embedding) > match_threshold
  ORDER BY c.embedding <=> query_embedding
  LIMIT match_count;
END;
$$ LANGUAGE plpgsql;
```

**Returns:** Top 10 matching document chunks for "generator cooling"

---

#### Stage 8: Backend Formats Response

```python
{
  "results": [
    {
      "chunk_id": "f8a2b3c4...",
      "doc_path": "01_BRIDGE/generator/cooling_system_manual.pdf",
      "chunk_text": "Generator cooling system operates via...",
      "similarity": 0.92,
      "actions": [
        {
          "action_id": "open_document",
          "label": "View Full Document"
        },
        {
          "action_id": "add_to_handover",
          "label": "Add to Handover"
        }
      ]
    },
    // ... more results
  ],
  "total": 10,
  "query_time_ms": 145
}
```

---

#### Stage 9: Frontend Displays Results

**File:** `apps/web/src/hooks/useCelesteSearch.ts`

```typescript
// Update state with results
setResults(response.results);
setLoading(false);
```

**UI Renders:**
- List of 10 document chunks
- Each with title, preview text, similarity score
- Action buttons ("View", "Add to Handover", etc.)

---

## 🎬 Journey 2: User Opens Document

### User Action
User clicks "View Full Document" button on search result

### Frontend Flow

#### Stage 1: DocumentSituationView Mounts

**File:** `apps/web/src/components/situations/DocumentSituationView.tsx:82-84`

```typescript
// ✅ RECENTLY FIXED: Now uses authenticated client
const { supabase } = await import('@/lib/supabaseClient');

// Query document chunk
const { data: chunkData, error: chunkError } = await supabase
  .from('search_document_chunks')
  .select('*')
  .eq('chunk_id', chunk_id)
  .single();
```

**SQL Executed:**
```sql
GET /rest/v1/search_document_chunks?select=*&chunk_id=eq.f8a2b3c4...

-- With JWT in Authorization header
```

---

#### Stage 2: RLS Policy Check #1 (search_document_chunks)

**Policy Applied:**
```sql
SELECT *
FROM search_document_chunks
WHERE chunk_id = 'f8a2b3c4...'
  AND yacht_id IN (
    SELECT yacht_id FROM auth_users WHERE auth_user_id = auth.uid()
  );
```

**RLS Sub-Query:**
```sql
-- This query must succeed first!
SELECT yacht_id FROM auth_users WHERE auth_user_id = auth.uid()
-- Expected: '85fe1119-b04c-41ac-80f1-829d23322598'
```

**🔴 CURRENT PROBLEM:**
Sub-query returns 0 rows (404 error from auth_users)
  ↓
RLS policy cannot determine yacht_id
  ↓
Main query returns 0 rows
  ↓
`.single()` throws error: "Cannot coerce to single JSON object"

**Console Output:**
```
GET /rest/v1/search_document_chunks?chunk_id=eq.f8a2b3c4... 406 (Not Acceptable)
[DocumentSituationView] READ failed - user may not have access to this yacht
```

---

#### Stage 3: Query doc_metadata (If Stage 2 Succeeds)

**File:** `apps/web/src/components/situations/DocumentSituationView.tsx:95-100`

```typescript
const { data: docData, error: docError } = await supabase
  .from('doc_metadata')
  .select('*')
  .eq('doc_path', chunkData.doc_path)
  .single();
```

**RLS Policy Applied:**
```sql
SELECT *
FROM doc_metadata
WHERE doc_path = '01_BRIDGE/generator/cooling_system_manual.pdf'
  AND yacht_id IN (
    SELECT yacht_id FROM auth_users WHERE auth_user_id = auth.uid()
  );
```

**Same Problem:** RLS sub-query fails → 406 error

---

#### Stage 4: Generate Signed URL (If Stage 3 Succeeds)

**File:** `apps/web/src/components/situations/DocumentSituationView.tsx:105-115`

```typescript
// Get storage path
const storagePath = docData.storage_path;
// e.g., "85fe1119.../01_BRIDGE/generator/cooling_system_manual.pdf"

// Generate signed URL (valid for 1 hour)
const { data: signedUrlData } = await supabase
  .storage
  .from('documents')
  .createSignedUrl(storagePath, 3600);

const signedUrl = signedUrlData.signedUrl;
```

**Storage RLS Check:**
Supabase Storage has separate RLS policies for the `documents` bucket

**Policy:**
```sql
-- Storage policy checks if path starts with user's yacht_id
CREATE POLICY "documents_yacht_isolation"
ON storage.objects
FOR SELECT
TO authenticated
USING (
  bucket_id = 'documents'
  AND (storage.foldername(name))[1] = (
    SELECT yacht_id::text FROM auth_users WHERE auth_user_id = auth.uid()
  )
);
```

**Explanation:**
- Path: `85fe1119.../01_BRIDGE/generator/...`
- First folder: `85fe1119...` (yacht_id)
- Policy checks: Does this match user's yacht_id?
- If YES: Generate signed URL
- If NO: 403 Forbidden

---

#### Stage 5: Display Document

```typescript
return (
  <div className="document-viewer">
    <iframe
      src={signedUrl}
      width="100%"
      height="800px"
      title="Document Viewer"
    />
  </div>
);
```

**Browser Loads:**
```
GET https://vzsohavtuotocgrfkfyd.supabase.co/storage/v1/object/sign/documents/85fe1119.../01_BRIDGE/generator/cooling_system_manual.pdf?token=...
```

**User Sees:** PDF document rendered in iframe

---

## 🎬 Journey 3: User Creates Work Order (P0 Action)

### User Action
User clicks "Create Work Order" button from fault card

### Frontend Flow

#### Stage 1: Show Modal

**File:** `apps/web/src/components/actions/CreateWorkOrderFromFault.tsx`

```typescript
<Modal open={isOpen} onClose={onClose}>
  <form onSubmit={handleSubmit}>
    <input name="title" placeholder="Work order title" />
    <textarea name="description" placeholder="Description" />
    <select name="priority">
      <option value="low">Low</option>
      <option value="medium">Medium</option>
      <option value="high">High</option>
    </select>
    <button type="submit">Create Work Order</button>
  </form>
</Modal>
```

---

#### Stage 2: Submit Action

**File:** `apps/web/src/components/actions/CreateWorkOrderFromFault.tsx`

```typescript
const handleSubmit = async (e) => {
  e.preventDefault();

  const payload = {
    fault_id: fault.id,
    title: formData.title,
    description: formData.description,
    priority: formData.priority,
  };

  // Call backend action endpoint
  const result = await callCelesteApi('/v1/actions/execute', {
    method: 'POST',
    body: JSON.stringify({
      action_id: 'create_work_order',
      payload: payload
    })
  });

  if (result.success) {
    toast.success('Work order created');
    onClose();
  }
};
```

---

### Backend Flow

#### Stage 3: Action Router Receives Request

**File:** `apps/api/action_router/registry.py`

```python
@app.post("/v1/actions/execute")
async def execute_action(
    request: Request,
    auth: dict = Depends(validate_user_jwt)  # Middleware validates JWT
):
    body = await request.json()
    action_id = body['action_id']
    payload = body['payload']

    # Look up action in registry
    action_config = ACTION_REGISTRY.get(action_id)
    if not action_config:
        raise HTTPException(status_code=404, detail="Action not found")

    # Validate payload against schema
    schema = action_config['schema']
    validated_payload = schema(**payload)

    # Extract yacht_id from JWT
    yacht_id = auth['yacht_id']
    user_id = auth['user_id']

    # Execute handler
    handler = action_config['handler']
    result = await handler(validated_payload, yacht_id, user_id)

    return result
```

---

#### Stage 4: Handler Executes

**File:** `apps/api/action_router/handlers/create_work_order.py` (hypothetical)

```python
async def create_work_order_handler(
    payload: CreateWorkOrderSchema,
    yacht_id: str,
    user_id: str
) -> dict:
    supabase = create_client(
        os.getenv('SUPABASE_URL'),
        os.getenv('SUPABASE_SERVICE_ROLE_KEY')  # Bypasses RLS
    )

    # Create work order
    result = supabase.table('work_orders').insert({
        'yacht_id': yacht_id,  # Enforced by backend
        'created_by': user_id,
        'fault_id': payload.fault_id,
        'title': payload.title,
        'description': payload.description,
        'priority': payload.priority,
        'status': 'open',
        'created_at': 'now()'
    }).execute()

    # Update fault status
    supabase.table('faults').update({
        'work_order_id': result.data[0]['id'],
        'status': 'work_order_created'
    }).eq('id', payload.fault_id).execute()

    # Log action
    log_action('create_work_order', user_id, yacht_id, result.data)

    # Send notification (if N8N dispatcher)
    # await notify_n8n('work_order_created', result.data)

    return {
        'success': True,
        'work_order_id': result.data[0]['id']
    }
```

---

#### Stage 5: Frontend Receives Response

```typescript
// Result from callCelesteApi
{
  success: true,
  work_order_id: "d7e8f9a0-..."
}
```

**UI Updates:**
- Show success toast
- Close modal
- Refresh fault list (work order now linked)

---

## 🔍 Current Journey Status

### ✅ Working Journeys
1. Backend authentication (JWT validation)
2. P0 Actions execution
3. RLS on search_document_chunks, doc_metadata, faults (when yacht_id known)

### 🔴 Broken Journeys
1. **User searches → 500 error**
   - Cause: auth_users query fails (404)
   - Effect: No yacht_id → backend rejects request

2. **User opens document → 406 error**
   - Cause: auth_users query fails in RLS sub-query
   - Effect: RLS blocks access to search_document_chunks

### 🎯 Fix Required
**Make auth_users query succeed:**
1. Verify GRANT SELECT ON auth_users TO authenticated
2. Verify RLS policy `auth_users_select_own` is active
3. Verify JWT token includes correct `sub` claim
4. Test RLS policy with actual JWT (not simulated)

**Once fixed, all journeys will work again.**

---

**Next:** [04_SQL_CHANGES.md](./04_SQL_CHANGES.md) - All database changes made today
