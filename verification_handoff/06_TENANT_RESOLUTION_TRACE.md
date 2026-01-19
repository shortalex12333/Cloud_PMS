# 06_TENANT_RESOLUTION_TRACE.md — End-to-End Yacht Context Flow

**Author:** Claude A (System Historian)
**Date:** 2026-01-19
**Purpose:** Document exactly how yacht_id flows from login to backend

---

## CRITICAL DOCTRINE

```
IF yacht_id IS NULL:
  → SYSTEM MUST HARD-STOP
  → DO NOT SEND PLACEHOLDERS
  → SHOW "Awaiting activation" SCREEN
```

---

## FLOW DIAGRAM

```
┌─────────────────────────────────────────────────────────────────────┐
│                           LOGIN FLOW                                  │
└─────────────────────────────────────────────────────────────────────┘

1. User enters email/password
         │
         ▼
2. supabase.auth.signInWithPassword()
         │
         ▼
3. Supabase returns Session:
   {
     access_token: "eyJ...",    ← JWT signed by Supabase
     user: {
       id: "abc-123",
       email: "x@alex-short.com",
       user_metadata: {
         yacht_id: "85fe1119-...",  ← MAY BE NULL
         role: "crew"
       }
     }
   }
         │
         ▼
4. AuthContext.tsx:66 buildUserFromSession()
   - Extracts user_id, email, role from JWT
   - Sets yachtId from user_metadata (may be null)
   - Sets bootstrapStatus: 'loading'
         │
         ▼
5. AuthContext.tsx:117 fetchBootstrap()
   - Calls: POST https://pipeline-core.int.celeste7.ai/v1/bootstrap
   - Headers: Authorization: Bearer <JWT>
         │
         ▼
6. [CURRENTLY BLOCKED - B001]
   - Render verifies JWT with MASTER_SUPABASE_JWT_SECRET
   - Returns 401 if secret mismatch
         │
         ▼ (WHEN FIXED)
7. Render looks up user_id in MASTER DB:
   - Gets yacht assignment
   - Returns: yacht_id, yacht_name, tenant_key_alias, role, status
         │
         ▼
8. AuthContext.tsx:178 processBootstrapData()
   - Sets user.yachtId
   - Sets user.tenantKeyAlias
   - Sets user.bootstrapStatus: 'active' or 'pending'
         │
         ▼
9. Frontend stores in React context:
   - user.yachtId (used for API calls)
   - user.tenantKeyAlias (used for DB routing hints)

┌─────────────────────────────────────────────────────────────────────┐
│                        API CALL FLOW                                  │
└─────────────────────────────────────────────────────────────────────┘

10. User triggers action (search, mutation, etc.)
          │
          ▼
11. authHelpers.ts:164 getAuthHeaders()
    - Gets fresh JWT from session
    - Returns: { Authorization: 'Bearer <JWT>' }
          │
          ▼
12. apiClient.ts:78 fetch()
    - Sends request to Render with JWT
          │
          ▼
13. Render backend:
    - Verifies JWT
    - Extracts user_id from JWT
    - Looks up yacht_id from user_id (MASTER DB)
    - Routes query to correct tenant DB
          │
          ▼
14. Response returns to frontend

┌─────────────────────────────────────────────────────────────────────┐
│                     SUPABASE DIRECT CALLS                            │
└─────────────────────────────────────────────────────────────────────┘

15. Some queries go directly to Supabase (not through Render)
          │
          ▼
16. JWT contains yacht_id in claims (from user_metadata)
          │
          ▼
17. RLS policy evaluates:
    auth.jwt() ->> 'yacht_id' = yacht_id
          │
          ▼
18. Only matching rows returned
```

---

## WHERE USER_ID IS OBTAINED

| Step | Location | Source |
|------|----------|--------|
| Login | Supabase auth response | `session.user.id` |
| Frontend | AuthContext | `user.id` |
| Backend | JWT verification | `jwt.sub` |

**Code Reference:** `apps/web/src/contexts/AuthContext.tsx:70`
```javascript
return {
  id: authUser.id,  // ← user_id from session
  // ...
}
```

---

## WHERE YACHT_ID IS OBTAINED

| Step | Location | Source | Reliability |
|------|----------|--------|-------------|
| 1 | JWT user_metadata | Set during user creation | May be null |
| 2 | Bootstrap response | Render lookup from MASTER DB | Authoritative |
| 3 | AuthContext | Stored in React state | From step 2 |

**Code Reference:** `apps/web/src/contexts/AuthContext.tsx:74`
```javascript
yachtId: (meta.yacht_id as string) || null,  // From JWT metadata
```

**Code Reference:** `apps/web/src/contexts/AuthContext.tsx:223-228`
```javascript
return {
  // ...
  yachtId: data.yacht_id,  // From bootstrap response
  yachtName: data.yacht_name,
  tenantKeyAlias: data.tenant_key_alias || null,
  bootstrapStatus: 'active',
}
```

---

## HOW YACHT_ID IS STORED CLIENT-SIDE

| Storage | Location | Persists? |
|---------|----------|-----------|
| React Context | AuthContext.user.yachtId | Session only |
| JWT | Supabase session storage | Persists with refresh |

**NOT stored in:**
- localStorage (except via Supabase session)
- sessionStorage directly
- Cookies

---

## HOW YACHT_ID IS TRANSMITTED TO RENDER BACKEND

| Method | Header | Value |
|--------|--------|-------|
| JWT | `Authorization: Bearer <token>` | yacht_id embedded in JWT claims |

**Code Reference:** `apps/web/src/lib/authHelpers.ts:164-170`
```javascript
export async function getAuthHeaders(yachtId?: string | null): Promise<HeadersInit> {
  const jwt = await getValidJWT();

  // Only send JWT - backend handles tenant routing via user_id lookup
  return {
    Authorization: `Bearer ${jwt}`,
  };
}
```

**Note:** The `yachtId` parameter is deprecated. Backend extracts from JWT.

---

## HOW BACKEND VALIDATES MEMBERSHIP

```
1. Receive JWT in Authorization header
2. Verify JWT signature using MASTER_SUPABASE_JWT_SECRET
3. Extract user_id from JWT claims (jwt.sub)
4. Query MASTER DB: SELECT yacht_id FROM user_assignments WHERE user_id = ?
5. If no assignment → return 403
6. If yacht inactive → return 403 with status
7. Route subsequent queries to tenant DB using yacht_id
```

**Current Blocker:** Step 2 fails due to JWT secret mismatch (B001)

---

## CAPTURED NETWORK PAYLOAD (SIMULATED)

**Note:** Could not capture production payload because bootstrap endpoint returns 401.

### Expected Login Response
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600,
  "refresh_token": "xyz...",
  "user": {
    "id": "user-uuid-here",
    "email": "x@alex-short.com",
    "user_metadata": {
      "yacht_id": "85fe1119-b04c-41ac-80f1-829d23322598",
      "role": "crew"
    }
  }
}
```

### Expected Bootstrap Response (WHEN FIXED)
```json
{
  "yacht_id": "85fe1119-b04c-41ac-80f1-829d23322598",
  "yacht_name": "Test Yacht",
  "tenant_key_alias": "y85fe1119",
  "role": "crew",
  "status": "ACTIVE"
}
```

### Current Bootstrap Response
```json
{
  "detail": "Invalid token: Signature verification failed"
}
```

---

## FAILURE MODES

### Mode 1: yacht_id is null in JWT metadata

**Symptom:** User sees "Awaiting activation" screen
**Correct Behavior:** Yes, this is expected for pending users
**Wrong Behavior:** Sending placeholder UUID

### Mode 2: Bootstrap returns 401

**Symptom:** User stuck in loading state or sees error
**Cause:** JWT secret mismatch (B001)
**Correct Behavior:** Show error, retry with backoff
**Code Reference:** `AuthContext.tsx:139-142`

### Mode 3: Bootstrap returns 403

**Symptom:** "Awaiting activation" screen
**Cause:** User not assigned to any yacht
**Correct Behavior:** Yes, this is expected

### Mode 4: yacht_id used without validation

**Symptom:** Empty results, silent failures
**Cause:** Code like `yachtId || 'placeholder'`
**Correct Behavior:** Throw error, never use placeholders

---

## HARD-STOP REQUIREMENTS

Claude B must verify these guards exist:

### Guard 1: No API calls without yacht_id
```javascript
// CORRECT
if (!user?.yachtId) {
  throw new Error('No yacht context');
}
await apiClient.search(query);

// WRONG
const yachtId = user?.yachtId || '00000000-0000-0000-0000-000000000000';
await apiClient.search(query);  // Will return empty, no error
```

### Guard 2: Pending users see activation screen
```javascript
// In protected routes
if (user.bootstrapStatus !== 'active') {
  return <PendingActivationScreen />;
}
```

### Guard 3: RLS enforces yacht_id server-side
```sql
-- Even if client sends wrong yacht_id, RLS blocks
CREATE POLICY "yacht_isolation" ON work_orders
  USING (yacht_id = (auth.jwt() ->> 'yacht_id')::uuid);
```

---

## VERIFICATION TASKS FOR CLAUDE B

1. **Capture real network payload:**
   - Login on production
   - Open Network tab
   - Capture login response
   - Capture bootstrap request/response

2. **Verify hard-stops exist:**
   - Search codebase for placeholder UUIDs
   - Verify all API calls check yacht_id first

3. **Test edge cases:**
   - What happens if user_metadata.yacht_id is null?
   - What happens if bootstrap times out?
   - What happens if JWT expires mid-session?

