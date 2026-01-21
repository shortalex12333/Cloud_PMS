# TENANT RESOLUTION TRACE

**Generated:** 2026-01-18
**Method:** Code path analysis + API payload capture

---

## OVERVIEW

The system has **MULTIPLE DISCONNECTED** tenant resolution paths that do not share state correctly.

---

## PATH 1: Bootstrap Flow (Render API)

### Flow
```
1. User logs in via Supabase Auth
2. AuthContext.handleSession() triggers
3. POST /v1/bootstrap to Render API
4. Render queries MASTER DB: user_accounts WHERE user_id = auth.uid()
5. Returns: { yacht_id, role, tenant_key_alias, status }
6. Stored in: AuthContext.user.yachtId
```

### Evidence
```json
// From C1_api_requests.json (E2E test capture)
{
  "url": "https://pipeline-core.int.celeste7.ai/v1/bootstrap",
  "method": "POST",
  "headers": {
    "authorization": "Bearer eyJhbGciOiJIUzI1NiIs..."
  }
}
```

### Status: ✅ WORKS
- Bootstrap API returns yacht_id correctly
- AuthContext stores it in `user.yachtId`

---

## PATH 2: Search Payload (useCelesteSearch)

### Flow
```
1. User types in search box
2. useCelesteSearch.buildSearchPayload() called
3. Calls getYachtId() from authHelpers.ts
4. getYachtId() reads: session.user.user_metadata.yacht_id
5. Returns: NULL (user_metadata.yacht_id never set)
6. Payload sent with yacht_id: null
```

### Code Path
```typescript
// useCelesteSearch.ts:143-156
async function buildSearchPayload(query: string, streamId: string) {
  const { data: { session } } = await supabase.auth.getSession();
  const yachtId = await getYachtId();  // ❌ Returns NULL
  ...
  return {
    auth: session?.user ? {
      yacht_id: yachtId,  // ❌ NULL
      ...
    } : undefined,
  };
}

// authHelpers.ts:199-217
export async function getYachtId(): Promise<string | null> {
  const { data: { session } } = await supabase.auth.getSession();
  const meta = session.user.user_metadata || {};
  return meta.yacht_id || meta.yachtId || null;  // ❌ Neither exists
}
```

### Evidence
```json
// From C1_api_requests.json (E2E test capture)
{
  "url": "https://pipeline-core.int.celeste7.ai/webhook/search",
  "postData": "{\"auth\":{\"user_id\":\"a0d66b00-...\",\"yacht_id\":null,...}}"
}
```

### Status: ❌ BROKEN

**Root Cause:** `getYachtId()` reads from Supabase `user_metadata` which is NEVER populated with `yacht_id`. The yacht_id from bootstrap is stored in React state (`AuthContext.user.yachtId`), not in Supabase session.

---

## PATH 3: Navigation Context (Viewer)

### Flow
```
1. User clicks search result
2. NavigationContext.pushViewer() called
3. Checks: state.yachtId (NavigationContext internal state)
4. Falls back: 'placeholder-yacht-id'
5. API call made with placeholder
6. Backend rejects: UUID parsing error
```

### Code Path
```typescript
// NavigationContext.tsx:117-131
const pushViewer = useCallback(
  async (anchorType: string, anchorId: string, isInitial: boolean = false) => {
    if (isInitial && !state.contextId) {
      // TODO: Get yacht_id and user_id from auth context  ← Never implemented
      const yachtId = state.yachtId || 'placeholder-yacht-id';  // ❌ Falls back to placeholder
      const userId = state.userId || 'placeholder-user-id';     // ❌ Falls back to placeholder

      const context = await createNavigationContext({
        yacht_id: yachtId,  // ❌ Sends placeholder
        user_id: userId,    // ❌ Sends placeholder
        ...
      });
```

### Status: ❌ BROKEN

**Root Cause:** NavigationContext has its own `state.yachtId` which is NEVER initialized from AuthContext.

---

## PATH 4: Microaction Handlers

### Flow
```
1. User clicks microaction button (e.g., "Add Note")
2. Handler calls useActionHandler.executeAction()
3. Handler makes Supabase query with yacht_id
4. yacht_id comes from: context.yacht_id (passed from UI)
5. UI gets yacht_id from: ???
```

### Code Path
```typescript
// useActionHandler.ts:127-136
const payload = {
  ...params,
  yacht_id: user.yachtId,  // ❌ May be null if AuthContext not ready
  user_id: user.id,
};
```

### Status: ⚠️ PARTIALLY WORKS
- Uses AuthContext.user.yachtId which IS populated
- But handlers reference non-existent tables

---

## WHERE yacht_id SHOULD COME FROM

### Source of Truth
```
MASTER DB: user_accounts
  - id: a0d66b00-581f-4d27-be6b-5b679d5cd347
  - yacht_id: 85fe1119-b04c-41ac-80f1-829d23322598
  - email: x@alex-short.com
  - role: chief_engineer
```

### What Actually Happens
```
Bootstrap API → Returns yacht_id ✅
  → AuthContext.user.yachtId = "85fe1119..." ✅
  → useCelesteSearch.getYachtId() reads user_metadata.yacht_id → NULL ❌
  → NavigationContext.state.yachtId → NULL → Falls back to placeholder ❌
```

---

## WHERE yacht_id BECOMES NULL

| Component | yacht_id Value | Reason |
|-----------|----------------|--------|
| Bootstrap API response | `85fe1119...` | Correct |
| AuthContext.user.yachtId | `85fe1119...` | Correct |
| Supabase session.user.user_metadata.yacht_id | `null` | NEVER SET |
| getYachtId() return value | `null` | Reads from user_metadata |
| Search payload auth.yacht_id | `null` | Uses getYachtId() |
| NavigationContext.state.yachtId | `null` | Never initialized |
| Viewer context yacht_id | `placeholder-yacht-id` | Fallback |

---

## FIX REQUIRED

### Option A: Fix getYachtId() to use AuthContext
```typescript
// Instead of reading from user_metadata
export async function getYachtId(): Promise<string | null> {
  // Get from AuthContext (where it's actually stored)
  const authContext = useAuth();  // Need to make this work outside React
  return authContext.user?.yachtId || null;
}
```

### Option B: Store yacht_id in Supabase user_metadata
```typescript
// After bootstrap, update user_metadata
await supabase.auth.updateUser({
  data: { yacht_id: bootstrapResponse.yacht_id }
});
```

### Option C: Pass yacht_id explicitly to all hooks
```typescript
// useCelesteSearch should receive yacht_id as parameter
function useCelesteSearch(yachtId: string) {
  // Use passed yachtId instead of calling getYachtId()
}
```

---

## CRITICAL PATH TRACE

```
User Login
    │
    ├─► Supabase Auth ───────────────────────────► Session created
    │                                               (no yacht_id in metadata)
    │
    ├─► AuthContext.handleSession() ────────────┐
    │                                           │
    │   POST /v1/bootstrap                      │
    │       │                                   │
    │       ▼                                   │
    │   Render API queries MASTER DB            │
    │       │                                   │
    │       ▼                                   │
    │   Returns: yacht_id = "85fe1119..."       │
    │       │                                   │
    │       ▼                                   │
    │   AuthContext.user.yachtId = "85fe1119..." ◄──┘
    │
    │
User Types Search Query
    │
    ├─► useCelesteSearch.handleQueryChange()
    │       │
    │       ▼
    │   buildSearchPayload()
    │       │
    │       ▼
    │   getYachtId() ────────────────────────────► Reads user_metadata.yacht_id
    │       │                                       │
    │       │                                       ▼
    │       │                                   Returns NULL
    │       │                                       │
    │       ▼                                       ▼
    │   Payload: { auth: { yacht_id: null } } ◄─────┘
    │       │
    │       ▼
    │   POST /webhook/search with yacht_id: null
    │       │
    │       ▼
    │   Backend returns 0 results (can't filter by yacht)

```

---

## CONCLUSION

The system has yacht_id in the right place (AuthContext) but **two critical code paths bypass AuthContext** and read from the wrong source (user_metadata), causing yacht_id to be null.
