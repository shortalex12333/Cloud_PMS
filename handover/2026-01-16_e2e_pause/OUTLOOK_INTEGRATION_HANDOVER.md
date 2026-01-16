# Outlook Email Integration - Complete Handover Document

> **Created:** 2026-01-16
> **Last Updated:** 2026-01-16 16:30 UTC
> **Status:** Phase 1 (OAuth) BROKEN - `no_yacht` error
> **Critical:** PREVIOUS CLAUDE MADE MANY MISTAKES - READ WARNINGS CAREFULLY

---

## ⚠️ CRITICAL WARNINGS - READ FIRST

### MISTAKES MADE BY PREVIOUS CLAUDE

1. **Assumed tables/columns existed without verifying** - Called `auth_users_yacht` table that DOES NOT EXIST
2. **Assumed column names without checking** - Used `user_id` column when table has `id` column
3. **Made multiple "fixes" without testing each one** - Jumped to conclusions
4. **Did not verify data step-by-step** - Guessed at what queries return
5. **Trusted code over database reality** - Code references things that don't exist

### HOW YOU MUST WORK

```
FOR EVERY STEP OF THE OAUTH FLOW:
1. READ the code that executes this step
2. IDENTIFY what table/column/data it needs
3. QUERY Supabase to verify the table EXISTS
4. QUERY Supabase to verify the column EXISTS
5. QUERY Supabase to verify the data EXISTS
6. ONLY THEN move to next step

DO NOT ASSUME. DO NOT GUESS. VERIFY EVERYTHING.
```

---

## CURRENT STATE (2026-01-16)

### The Error
```
https://app.celeste7.ai/settings?provider=outlook&purpose=read&error=no_yacht
```

### What This Means
The OAuth flow reaches the yacht lookup step and returns "User has no yacht assigned" because:
- Either the user_id in OAuth state doesn't match any row in `auth_users_profiles`
- Or the query is wrong
- Or the table structure is different than code expects

### What Was Verified Working
| Step | Status | Evidence |
|------|--------|----------|
| State parsing | ✅ | No `invalid_state` error |
| Azure token exchange | ✅ | No `invalid_grant` error (with real code) |
| Graph profile fetch | ✅ | Would fail before yacht lookup otherwise |
| Yacht lookup | ❌ | Returns `no_yacht` |

---

## OAUTH FLOW - STEP BY STEP VERIFICATION NEEDED

### Step 1: Frontend Generates OAuth State

**File:** `/apps/web/src/app/api/integrations/outlook/auth-url/route.ts`
**Line 66:** `const state = generateOAuthState(user.id, 'read');`

**What happens:**
- Frontend calls `supabase.auth.getUser(token)` to get current user
- Uses `user.id` (Supabase auth user ID) in state
- State format: `{user_id}:{purpose}:{random}`

**MUST VERIFY:**
- What user ID does the frontend actually send?
- Check browser console/network tab during OAuth start
- Or check Render logs for `[Auth] Processing OAuth exchange for user XXX`

### Step 2: Render Parses State

**File:** `/apps/api/routes/auth_routes.py`
**Function:** `parse_state()` (lines 69-93)

**What happens:**
- Splits state by `:`
- Extracts `user_id` and `purpose`

**VERIFIED:** This works (no `invalid_state` error)

### Step 3: Azure Token Exchange

**File:** `/apps/api/routes/auth_routes.py`
**Function:** `exchange_code_for_tokens()` (lines 119-163)

**What happens:**
- POSTs to Azure with code + credentials
- Gets access_token, refresh_token

**VERIFIED:** This works (would return `invalid_grant` or credential errors otherwise)

### Step 4: Graph Profile Fetch

**File:** `/apps/api/routes/auth_routes.py`
**Function:** `fetch_graph_profile()` (lines 166-182)

**What happens:**
- Calls Microsoft Graph `/me` endpoint
- Gets email and displayName

**ASSUMED WORKING:** Would fail before yacht lookup otherwise

### Step 5: Yacht Lookup ← THIS IS WHERE IT FAILS

**File:** `/apps/api/routes/auth_routes.py`
**Lines 276-291:**

```python
# Code tries:
user_result = supabase.table('auth_users_profiles').select('yacht_id').eq('id', user_id).maybe_single().execute()
yacht_id = user_result.data.get('yacht_id') if user_result.data and isinstance(user_result.data, dict) else None

if not yacht_id:
    return TokenExchangeResponse(
        success=False,
        error="User has no yacht assigned",
        error_code="no_yacht",  # ← THIS IS THE ERROR WE SEE
    )
```

**MUST VERIFY:**
1. What `user_id` value is being queried?
2. Does `auth_users_profiles` table exist? → YES (verified)
3. Does it have `id` column? → YES (verified)
4. Does it have `yacht_id` column? → YES (verified)
5. Is there a row where `id` = the user_id from OAuth state? → **UNKNOWN**

**VERIFIED DATA:**
```json
// auth_users_profiles has ONE row:
{
  "id": "a35cad0b-02ff-4287-b6e4-17c96fa6a424",
  "yacht_id": "85fe1119-b04c-41ac-80f1-829d23322598",
  "email": "old_1768421213124@temp.local",
  "name": "x@alex-short.com"
}
```

**VERIFIED QUERY:**
```bash
# This query WORKS and returns yacht_id:
curl "https://vzsohavtuotocgrfkfyd.supabase.co/rest/v1/auth_users_profiles?select=yacht_id&id=eq.a35cad0b-02ff-4287-b6e4-17c96fa6a424"
# Returns: [{"yacht_id":"85fe1119-b04c-41ac-80f1-829d23322598"}]
```

**CONCLUSION:**
The query works when user_id = `a35cad0b-02ff-4287-b6e4-17c96fa6a424`
So the OAuth state must contain a DIFFERENT user_id.

**NEXT STEP:**
Check Render logs for `[Auth] User profile lookup: user_id=XXX` to see what user_id is actually being searched.

---

## VERIFIED DATABASE STATE

### Tables That EXIST (Verified via Supabase REST API)

| Table | Exists | Row Count | Key Columns |
|-------|--------|-----------|-------------|
| `auth_users_profiles` | ✅ | 1 | id, yacht_id, email, name |
| `auth_microsoft_tokens` | ✅ | 2 | user_id, yacht_id, microsoft_access_token |
| `email_watchers` | ✅ | 1 | user_id, yacht_id, mailbox_address_hash, sync_status |
| `email_messages` | ✅ | 2 | thread_id, yacht_id, subject |
| `email_threads` | ✅ | 1 | yacht_id, latest_subject |

### Tables That DO NOT EXIST (Code References Them Wrongly)

| Table | Referenced In | Status |
|-------|--------------|--------|
| `auth_users_yacht` | Was in auth_routes.py (removed) | ❌ DOES NOT EXIST |
| `email_attachments` | - | ❌ DOES NOT EXIST |
| `email_sync_status` | - | ❌ DOES NOT EXIST |

### Column Mismatches Found

| Table | Code Uses | Actual Column |
|-------|-----------|---------------|
| `auth_users_profiles` | `user_id` (old) | `id` (correct) |
| `email_watchers` | `provider_email_hash` | `mailbox_address_hash` |

---

## HOW TO DEBUG THE `no_yacht` ERROR

### Option 1: Check Render Logs

1. Go to https://dashboard.render.com
2. Find `pipeline-core` service
3. Click Logs
4. Search for `[Auth] User profile lookup:`
5. This will show: `user_id=XXX, yacht_id=YYY, data=ZZZ`

The `user_id` shown is what was searched. Compare to:
- `a35cad0b-02ff-4287-b6e4-17c96fa6a424` (the ID in auth_users_profiles)

### Option 2: Check Frontend User ID

In browser console on app.celeste7.ai:
```javascript
// After logging in, check what user ID Supabase returns
const { data: { user } } = await supabase.auth.getUser()
console.log('Auth user ID:', user.id)
```

### Option 3: Add More Logging

In `/apps/api/routes/auth_routes.py`, add before the query:
```python
logger.info(f"[Auth] About to query auth_users_profiles with user_id={user_id}")
```

---

## VERIFIED CREDENTIALS

### Supabase (WORKING)

```
URL: https://vzsohavtuotocgrfkfyd.supabase.co
Service Key: [REDACTED - see Supabase dashboard or GitHub secret TENANT_SUPABASE_SERVICE_ROLE_KEY]
```

### Test User

```
Email: x@alex-short.com
Password: [REDACTED - see GitHub secret TEST_USER_PASSWORD]
Auth User ID: a35cad0b-02ff-4287-b6e4-17c96fa6a424
Yacht ID: 85fe1119-b04c-41ac-80f1-829d23322598
```

### Azure (In Render)

```
READ App ID: 41f6dc82-8127-4330-97e0-c6b26e6aa967
WRITE App ID: f0b8944b-8127-4f0f-8ed5-5487462df50c
(Secrets in Render env vars)
```

---

## CURL COMMANDS TO VERIFY DATABASE

### Check auth_users_profiles

```bash
SUPABASE_KEY="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ6c29oYXZ0dW90b2NncmZrZnlkIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MzU5Mjg3NSwiZXhwIjoyMDc5MTY4ODc1fQ.fC7eC_4xGnCHIebPzfaJ18pFMPKgImE7BuN0I3A-pSY"

# Get all rows
curl -s "https://vzsohavtuotocgrfkfyd.supabase.co/rest/v1/auth_users_profiles?select=*" \
  -H "apikey: $SUPABASE_KEY" \
  -H "Authorization: Bearer $SUPABASE_KEY"

# Query by specific ID
curl -s "https://vzsohavtuotocgrfkfyd.supabase.co/rest/v1/auth_users_profiles?select=yacht_id&id=eq.YOUR_USER_ID_HERE" \
  -H "apikey: $SUPABASE_KEY" \
  -H "Authorization: Bearer $SUPABASE_KEY"
```

### Check auth_microsoft_tokens

```bash
curl -s "https://vzsohavtuotocgrfkfyd.supabase.co/rest/v1/auth_microsoft_tokens?select=*" \
  -H "apikey: $SUPABASE_KEY" \
  -H "Authorization: Bearer $SUPABASE_KEY"
```

### Check email_watchers

```bash
curl -s "https://vzsohavtuotocgrfkfyd.supabase.co/rest/v1/email_watchers?select=*" \
  -H "apikey: $SUPABASE_KEY" \
  -H "Authorization: Bearer $SUPABASE_KEY"
```

### Get Supabase Auth Users (to verify auth user IDs)

```bash
curl -s "https://vzsohavtuotocgrfkfyd.supabase.co/auth/v1/admin/users" \
  -H "apikey: $SUPABASE_KEY" \
  -H "Authorization: Bearer $SUPABASE_KEY"
```

---

## FILE LOCATIONS

### Backend (Render - Python)

```
/apps/api/routes/auth_routes.py    # OAuth token exchange endpoint
/apps/api/main.py                  # FastAPI app
```

### Frontend (Vercel - TypeScript)

```
/apps/web/src/app/api/integrations/outlook/auth-url/route.ts   # Generates OAuth URL
/apps/web/src/app/api/integrations/outlook/callback/route.ts   # Handles callback
/apps/web/src/lib/email/oauth-utils.ts                         # OAuth utilities
```

### Database

```
/supabase/migrations/   # Table definitions
```

---

## GIT STATE

```
Branch: main
Latest commit on Render: 0f5d3ab
All OAuth changes are pushed and deployed.
```

---

## WHAT THE NEXT CLAUDE MUST DO

### Immediate Task: Find Why `no_yacht`

1. **Get the actual user_id from OAuth state**
   - Check Render logs OR
   - Add logging to see what user_id is searched

2. **Compare to auth_users_profiles.id**
   - Known ID: `a35cad0b-02ff-4287-b6e4-17c96fa6a424`
   - If different, find WHY the frontend sends a different ID

3. **If IDs don't match:**
   - Check if there are multiple Supabase auth users
   - Check if frontend is using wrong Supabase instance
   - Check if user is logging in with different account

### DO NOT:
- Assume anything works
- Make changes without verifying current state
- Skip verification steps
- Trust code over database queries

---

## PRODUCTION URLS

```
Frontend: https://app.celeste7.ai (Vercel)
Backend: https://pipeline-core.int.celeste7.ai (Render)
Database: https://vzsohavtuotocgrfkfyd.supabase.co (Supabase)
```

---

## LESSONS LEARNED

1. **Always verify tables exist before writing code that uses them**
2. **Always verify column names match between code and database**
3. **Test queries directly against Supabase before assuming they work**
4. **Check Render logs for actual values being used**
5. **Don't make multiple changes at once - verify each change works**
6. **The error message tells you WHERE it failed - trace backwards from there**

---

## APPENDIX: Error Code Reference

| Error | Meaning | Where Set |
|-------|---------|-----------|
| `invalid_state` | State parsing failed | auth_routes.py:216-220 |
| `invalid_grant` | Azure rejected code (expired/used) | Azure response |
| `no_code` | Microsoft didn't return code | callback/route.ts:48-52 |
| `no_state` | State missing from callback | callback/route.ts:55-60 |
| `render_unreachable` | Can't connect to Render | callback/route.ts:86-93 |
| `no_yacht` | User not in auth_users_profiles | auth_routes.py:286-291 |
| `storage_failed` | Token upsert failed | auth_routes.py:315-321 |
| `unexpected` | Unhandled exception | auth_routes.py:351-357 |
