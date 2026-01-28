# HANDOVER: Cloud PMS - 2026-01-09

**Date:** January 9, 2026
**Session Focus:** Fixing RLS authentication and yacht_id isolation
**Status:** Database fixes applied, frontend still experiencing 404 errors on auth_users table

---

## 📋 HANDOVER DOCUMENTS

Read these documents in order:

1. **[00_START_HERE.md](./00_START_HERE.md)** ← You are here
2. **[01_REPO_OVERVIEW.md](./01_REPO_OVERVIEW.md)** - What is this codebase?
3. **[02_ARCHITECTURE.md](./02_ARCHITECTURE.md)** - How does it work?
4. **[03_USER_JOURNEY.md](./03_USER_JOURNEY.md)** - Complete flow from search to document display
5. **[04_SQL_CHANGES.md](./04_SQL_CHANGES.md)** - All database changes made today
6. **[05_CURRENT_STATUS.md](./05_CURRENT_STATUS.md)** - What's working, what's broken
7. **[06_TROUBLESHOOTING.md](./06_TROUBLESHOOTING.md)** - Known issues and debugging steps

---

## 🎯 IMMEDIATE CONTEXT

### What We Were Doing
Fixing authentication and Row Level Security (RLS) issues preventing users from:
- Searching documents
- Opening documents
- Accessing yacht-specific data

### The Root Problem
User `x@alex-short.com` had **wrong yacht_id** in database:
- **Was:** `00000000-0000-0000-0000-000000000000` (null UUID)
- **Should be:** `85fe1119-b04c-41ac-80f1-829d23322598`

This caused RLS policies to block all document access because:
1. Frontend queries `auth_users` to get user's yacht_id
2. RLS policies check if document's yacht_id matches user's yacht_id
3. Mismatch → 406 errors, "Cannot coerce to single JSON object"

### What We Fixed
1. ✅ Added missing SELECT policy to `auth_users` table
2. ✅ Updated yacht_id to correct value
3. ✅ Granted SELECT permission to authenticated role
4. ✅ Removed duplicate `auth_users_yacht` table
5. ✅ Updated frontend code to use `auth_users` instead of `auth_users_yacht`
6. ✅ Deployed to Vercel production

### What's Still Broken
- Frontend still getting **404 errors** when querying `auth_users` table
- Error: `GET /rest/v1/auth_users?select=yacht_id&auth_user_id=eq.a35cad0b... 404 (Not Found)`
- **BUT:** Direct SQL query in Supabase works perfectly
- **Theory:** Frontend Supabase client configuration issue OR cached credentials

---

## 🔍 QUICK DEBUG STEPS

### 1. Verify Database State (Supabase SQL Editor)
```sql
-- Should return the user with correct yacht_id
SELECT auth_user_id, email, yacht_id
FROM auth_users
WHERE email = 'x@alex-short.com';
-- Expected: yacht_id = 85fe1119-b04c-41ac-80f1-829d23322598
```

### 2. Check RLS Policy Exists
```sql
SELECT policyname, cmd, roles::text, qual::text
FROM pg_policies
WHERE tablename = 'auth_users';
-- Expected: auth_users_select_own policy exists
```

### 3. Check Table Grants
```sql
SELECT grantee, privilege_type
FROM information_schema.table_privileges
WHERE table_name = 'auth_users';
-- Expected: authenticated role has SELECT permission
```

### 4. Test Frontend (Browser Console)
```
1. Open: https://cloud-ezkuoo4zj-c7s-projects-4a165667.vercel.app
2. Hard refresh: Cmd+Shift+R
3. Search: "generator cooling"
4. Check console for:
   - GET auth_users 404 errors
   - [authHelpers] messages
```

---

## 📂 KEY FILE LOCATIONS

### Frontend Code (Next.js)
```
apps/web/src/
├── lib/
│   ├── supabaseClient.ts       # Authenticated Supabase client
│   ├── authHelpers.ts          # getYachtId(), getYachtSignature()
│   ├── apiClient.ts            # API calls to backend
│   └── auth.ts                 # getCurrentUser()
├── components/
│   └── situations/
│       └── DocumentSituationView.tsx  # Document viewer (READ microaction)
└── hooks/
    └── useCelesteSearch.ts     # Search hook
```

### Backend Code (FastAPI)
```
apps/api/
├── microaction_service.py      # Main API endpoints (/v1/search, /v2/search)
├── pipeline_service.py         # /webhook/search endpoint
├── middleware/
│   └── auth.py                 # JWT validation, yacht context injection
└── action_router/              # P0 Actions (add_to_handover, etc.)
```

### Database Files (SQL)
```
/tmp/
├── check_all_rls.sql           # Audit all RLS policies
├── fix_auth_users_rls.sql      # Add SELECT policy to auth_users
├── fix_auth_users.sql          # Update yacht_id
├── DROP_AUTH_USERS_YACHT_SIMPLE.sql  # Remove duplicate table
├── FIX_AUTH_USERS_GRANTS.sql   # Grant SELECT permissions
└── CRITICAL_RLS_ISSUE.md       # Complete RLS issue documentation
```

---

## 🏗️ SYSTEM ARCHITECTURE AT A GLANCE

### Authentication Flow
1. User logs in → Supabase Auth generates JWT
2. JWT stored in localStorage
3. Frontend extracts JWT for API calls
4. Backend validates JWT and extracts yacht_id

### Data Isolation (Multi-Tenancy)
- Each yacht has UUID identifier (yacht_id)
- RLS policies enforce: users only see data for their yacht
- Critical table: `auth_users` maps user_id → yacht_id

### Document Access Flow
```
User searches "generator cooling"
  ↓
Frontend: getYachtId() queries auth_users
  ↓
Frontend: generates yacht_signature = sha256(yacht_id + salt)
  ↓
Frontend: sends to backend with JWT + yacht_signature
  ↓
Backend: validates JWT, extracts yacht_id
  ↓
Backend: queries search_document_chunks (RLS enforced)
  ↓
Backend: returns results filtered by yacht_id
  ↓
User clicks document
  ↓
Frontend: queries doc_metadata (RLS enforced)
  ↓
Frontend: generates signed URL for Storage
  ↓
Browser displays document
```

---

## ⚠️ CRITICAL GOTCHAS

### 1. **Two Supabase Projects in Play**
- **OLD (testing):** `ymhpscejjmcbwyknxiwb.supabase.co`
- **PRODUCTION:** `vzsohavtuotocgrfkfyd.supabase.co`
- **Issue:** Early testing used wrong project, created confusion

### 2. **Duplicate Table Confusion**
- Had both `auth_users` and `auth_users_yacht` with different data
- Frontend queried `auth_users_yacht`, RLS checked `auth_users`
- **Fixed:** Removed `auth_users_yacht`, unified on `auth_users`

### 3. **RLS Requires TWO Things**
- Policy: `CREATE POLICY ... USING (auth_user_id = auth.uid())`
- Grant: `GRANT SELECT ON auth_users TO authenticated`
- Missing either = 404 errors

### 4. **READ vs MUTATE Microactions**
- **READ:** Use authenticated Supabase client (`@/lib/supabaseClient`)
- **MUTATE:** Use backend API (`callCelesteApi()`)
- **Critical:** Never create new Supabase client (loses authentication)

### 5. **Vercel Deployment**
- Monorepo with multiple projects
- Deploy from ROOT directory: `vercel --prod`
- Environment variables set in Vercel dashboard
- Latest deployment: `cloud-ezkuoo4zj-c7s-projects-4a165667.vercel.app`

---

## 🎓 TRUST LEVELS

### ✅ TRUSTWORTHY (Verified Working)
- Backend FastAPI endpoints (`/v1/search`, `/webhook/search`)
- JWT validation middleware (`apps/api/middleware/auth.py`)
- RLS policies on `search_document_chunks` and `doc_metadata`
- Yacht signature generation (`getYachtSignature()`)
- Document storage signed URLs

### ⚠️ PARTIALLY TRUSTED (Recently Changed)
- Frontend `authHelpers.ts` (just changed from `auth_users_yacht` to `auth_users`)
- `DocumentSituationView.tsx` (just fixed to use authenticated client)
- `auth_users` table RLS policy (just added today)

### ❌ NOT TRUSTED (Needs Investigation)
- Frontend Supabase client configuration (possibly caching old credentials)
- RLS policy application timing (why 404 after adding policy?)
- Vercel environment variable propagation

---

## 📞 NEXT STEPS FOR YOU

### Immediate Priority: Fix 404 Error on auth_users
**Hypothesis:** Frontend Supabase client isn't using correct credentials or RLS policy isn't fully applied

**Actions:**
1. Check if incognito/private browser window fixes the issue (rules out caching)
2. Verify Vercel environment variables match production Supabase
3. Check if `authenticated` role is properly configured in Supabase
4. Test RLS policy with actual JWT token (not just SQL simulation)

### Once Working: Verify End-to-End
1. User can search documents
2. User can open documents
3. User only sees documents for their yacht
4. No 406 or 404 errors in console

### Clean Up
1. Remove `/tmp/*.sql` files (all applied to database)
2. Remove `check_rls_status.mjs` (debugging script)
3. Remove `.env.vercel` (contains development credentials)

---

## 📚 RELATED DOCUMENTATION

### On Desktop (User's Machine)
- `~/Desktop/check_all_rls.sql` - RLS audit query
- `~/Desktop/fix_auth_users_rls.sql` - SELECT policy
- `~/Desktop/fix_auth_users.sql` - yacht_id update
- `~/Desktop/DROP_AUTH_USERS_YACHT_SIMPLE.sql` - Remove duplicate
- `~/Desktop/FIX_AUTH_USERS_GRANTS.sql` - Grant permissions
- `~/Desktop/CRITICAL_RLS_ISSUE.md` - Full RLS explanation
- `~/Desktop/RLS_AUDIT_RESULTS.md` - Audit results

### In /tmp (Temporary Files)
- `/tmp/DOCUMENT_LOADING_PIPELINE.md` - Complete 7-stage pipeline
- `/tmp/FIX_SUMMARY.md` - Summary of yacht_id fixes
- `/tmp/CRITICAL_RLS_ISSUE.md` - Detailed RLS issue analysis

### In Repository
- `apps/web/src/lib/authHelpers.ts` - Authentication helper functions
- `apps/api/middleware/auth.py` - Backend authentication middleware

---

## 🔑 ACCESS CREDENTIALS

### Supabase (Production)
- **URL:** `https://vzsohavtuotocgrfkfyd.supabase.co`
- **Service Role Key:** In Vercel environment variables
- **Dashboard:** https://supabase.com/dashboard/project/vzsohavtuotocgrfkfyd

### Vercel
- **Project:** `c7s-projects-4a165667/cloud-pms`
- **Latest Deployment:** `cloud-ezkuoo4zj-c7s-projects-4a165667.vercel.app`
- **Dashboard:** https://vercel.com/c7s-projects-4a165667/cloud-pms

### Test User
- **Email:** `x@alex-short.com`
- **User ID:** `a35cad0b-02ff-4287-b6e4-17c96fa6a424`
- **Yacht ID:** `85fe1119-b04c-41ac-80f1-829d23322598`

---

**Read the detailed documents in order to understand the full context.**

**Start with:** [01_REPO_OVERVIEW.md](./01_REPO_OVERVIEW.md)
