# E2E Test Failure - Root Cause & Fix

## ROOT CAUSE IDENTIFIED ✅

**The `TENANT_SUPABASE_ANON_KEY` GitHub secret is MISLABELED.**

### Evidence

Diagnostic test revealed:
```json
{
  "iss": "supabase",
  "ref": "vzsohavtuotocgrfkfyd",
  "role": "service_role",  ← ❌ WRONG! Should be "anon"
  "iat": 1763592875,
  "exp": 2079168875
}
```

The secret labeled `TENANT_SUPABASE_ANON_KEY` contains the **SERVICE_ROLE_KEY**, not the **ANON_KEY**.

### Why This Causes Failures

1. Frontend (`apps/web`) uses `NEXT_PUBLIC_SUPABASE_ANON_KEY` for client-side authentication
2. This gets populated from `TENANT_SUPABASE_ANON_KEY` GitHub secret in CI
3. Supabase **rejects** service_role keys from client-side auth (security measure)
4. Result: `POST /auth/v1/token 401 Unauthorized - Invalid API key`
5. Login never completes → all E2E tests timeout

### Console Error from Browser

```
POST https://vzsohavtuotocgrfkfyd.supabase.co/auth/v1/token?grant_type=password 401 (Unauthorized)
[AuthContext] Login error: Invalid API key
```

---

## FIX REQUIRED

### Step 1: Get the REAL Anon Key

Go to Supabase Dashboard:
1. Open: https://supabase.com/dashboard/project/vzsohavtuotocgrfkfyd
2. Click **Settings** → **API**
3. Find **Project API keys** section
4. Copy the **anon / public** key (NOT the service_role key)

The anon key JWT should decode to:
```json
{
  "role": "anon",  ← MUST be "anon"
  "ref": "vzsohavtuotocgrfkfyd"
}
```

### Step 2: Update GitHub Secret

1. Go to: https://github.com/shortalex12333/Cloud_PMS/settings/secrets/actions
2. Find `TENANT_SUPABASE_ANON_KEY`
3. Click **Update**
4. Paste the REAL anon key (from Step 1)
5. Save

### Step 3: Verify the Fix

Run diagnostic test locally:
```bash
cd /Users/celeste7/Documents/Cloud_PMS

# Update .env.e2e.local with real anon key
# Then run:
npx playwright test tests/e2e/diagnostic-anon-key.spec.ts

# Should see:
# ✅ SUCCESS: Anon key is VALID
# JWT role: anon  ← CORRECT!
```

### Step 4: Re-run E2E Tests

Trigger CI workflow:
```bash
gh workflow run e2e.yml --ref main
```

Expected result:
- Login should succeed ✅
- E2E tests should pass ✅
- No more 401 Unauthorized errors ✅

---

## What Was Wrong in .env.e2e.local

**BEFORE (wrong):**
```bash
TENANT_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ6c29oYXZ0dW90b2NncmZrZnlkIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MzU5Mjg3NSwiZXhwIjoyMDc5MTY4ODc1fQ.fC7eC_4xGnCHIebPzfaJ18pFMPKgImE7BuN0I3A-pSY
# Decodes to: {"role": "service_role"} ❌
```

**AFTER (correct):**
```bash
TENANT_SUPABASE_ANON_KEY=<GET FROM SUPABASE DASHBOARD>
# Should decode to: {"role": "anon"} ✅
```

---

## Timeline

1. **Issue**: E2E tests timeout waiting for login redirect
2. **Investigation**: Ran test with visible browser, captured console errors
3. **Diagnosis**: Created diagnostic test to decode JWT
4. **Root Cause**: TENANT_SUPABASE_ANON_KEY contains service_role key
5. **Fix**: Update GitHub secret with real anon key from Supabase dashboard

---

## Files Modified

- ✅ `.github/workflows/e2e.yml` - Now runs against localhost ✅
- ✅ `playwright.config.ts` - Updated BASE_URL priority ✅
- ✅ `scripts/e2e/verify_env.sh` - Removed VERCEL_PROD_URL requirement ✅
- ✅ `tests/e2e/diagnostic-anon-key.spec.ts` - NEW diagnostic test ✅

---

## Next Steps

1. User gets real anon key from Supabase dashboard
2. User updates GitHub secret `TENANT_SUPABASE_ANON_KEY`
3. User updates local `.env.e2e.local` with real anon key
4. Run diagnostic test to verify
5. Trigger E2E workflow
6. Tests should pass! 🎉
