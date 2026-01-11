# CORS Configuration - Complete Analysis & Fix Plan

**Date:** 2026-01-11
**Issue:** Search failing due to CORS blocking Vercel preview URL

---

## Current Problem

**Error:**
```
Access to fetch at 'https://pipeline-core.int.celeste7.ai/webhook/search'
from origin 'https://cloud-pms-git-universalv1-c7s-projects-4a165667.vercel.app'
has been blocked by CORS policy: Response to preflight request doesn't pass
access control check: No 'Access-Control-Allow-Origin' header is present
```

**Root Cause:**
- Frontend deployed to: `https://cloud-pms-git-universalv1-c7s-projects-4a165667.vercel.app`
- Backend ALLOWED_ORIGINS: Only has stable domains, not this preview URL
- Vercel preview URL not whitelisted in CORS

---

## Complete CORS Inventory

### 1. Pipeline Service (Backend)

**File:** `apps/api/pipeline_service.py`
**Lines:** 48-95

**Current Configuration:**
```python
ALLOWED_ORIGINS_STR = os.getenv(
    "ALLOWED_ORIGINS",
    "https://app.celeste7.ai,https://staging.celeste7.ai,http://localhost:3000,http://localhost:8000"
)
```

**Normalized Origins:**
- `https://app.celeste7.ai` (production)
- `https://staging.celeste7.ai` (staging)
- `http://localhost:3000` (local dev)
- `http://localhost:8000` (local dev)

**Missing:**
- ❌ Vercel preview URLs
- ❌ Branch-specific deployments

---

### 2. Microaction Service (Backend)

**File:** `apps/api/microaction_service.py`
**Lines:** 121-162

**Current Configuration:**
```python
ALLOWED_ORIGINS_STR = os.getenv(
    "ALLOWED_ORIGINS",
    "https://app.celeste7.ai,https://api.celeste7.ai,https://staging.celeste7.ai,http://localhost:3000,http://localhost:8000"
)
```

**Normalized Origins:**
- `https://app.celeste7.ai` (production)
- `https://api.celeste7.ai` (production API)
- `https://staging.celeste7.ai` (staging)
- `http://localhost:3000` (local dev)
- `http://localhost:8000` (local dev)

**Missing:**
- ❌ Vercel preview URLs
- ❌ Branch-specific deployments

---

### 3. Frontend CSP Headers

**File:** `apps/web/next.config.js`
**Lines:** 5-31

**Current Configuration:**
```javascript
"connect-src 'self' https://vzsohavtuotocgrfkfyd.supabase.co https://pipeline-core.int.celeste7.ai"
```

**Allowed Backends:**
- `https://vzsohavtuotocgrfkfyd.supabase.co` (Supabase)
- `https://pipeline-core.int.celeste7.ai` (Pipeline API)

**Status:** ✅ Correctly configured (outbound connections)

---

## Frontend Domains - Complete List

### Production Domains

| Domain | Purpose | Deployment Target | Status |
|--------|---------|-------------------|--------|
| `https://app.celeste7.ai` | Production frontend | Vercel production | ✅ Configured |
| `https://api.celeste7.ai` | Production API (microactions) | Render | ✅ Configured |

### Staging Domains

| Domain | Purpose | Deployment Target | Status |
|--------|---------|-------------------|--------|
| `https://staging.celeste7.ai` | Staging frontend | Vercel staging | ✅ Configured |

### Development Domains

| Domain | Purpose | Deployment Target | Status |
|--------|---------|-------------------|--------|
| `http://localhost:3000` | Local Next.js dev | Local machine | ✅ Configured |
| `http://localhost:8000` | Local API testing | Local machine | ✅ Configured |

### Preview/Branch Deployments

| Domain Pattern | Purpose | Deployment Target | Status |
|----------------|---------|-------------------|--------|
| `https://cloud-pms-*.vercel.app` | Vercel preview deploys | Vercel previews | ❌ NOT CONFIGURED |
| `https://cloud-pms-git-{branch}-*.vercel.app` | Branch-specific previews | Vercel branch previews | ❌ NOT CONFIGURED |

**Current Preview URL (Not Working):**
- `https://cloud-pms-git-universalv1-c7s-projects-4a165667.vercel.app`

---

## The Dilemma

### User's Previous Guidance (Commit 949b724)

> "Preview URLs will become brittle the moment Vercel preview URLs change... stop whitelisting changing Vercel preview URLs. Use staging.celeste7.ai for pre-production testing instead."

**Rationale:**
- Preview URLs change when Vercel regenerates them
- Creates constant "why isn't this working" incidents
- Maintenance burden
- Should use stable staging domain instead

### Current Reality

**We are deployed to a preview URL right now:**
- Branch: `universal_v1`
- URL: `https://cloud-pms-git-universalv1-c7s-projects-4a165667.vercel.app`
- Status: Blocked by CORS

**Why This Happened:**
- Branch pushed to GitHub
- Vercel auto-deployed to preview URL
- We don't have `staging.celeste7.ai` configured yet
- Preview URL blocked by CORS (as intended per previous guidance)

---

## Solution Options

### Option A: Add Current Preview URL (❌ Temporary, Brittle)

**Pros:**
- Quick fix
- Unblocks current deployment

**Cons:**
- URL will change on next deploy
- Violates previous guidance
- Will break again
- Not sustainable

### Option B: Use Wildcard for Vercel (⚠️ DANGEROUS)

**Configuration:**
```python
ALLOWED_ORIGINS = [
    "https://app.celeste7.ai",
    "https://staging.celeste7.ai",
    "https://*.vercel.app",  # Wildcard
    ...
]
```

**Pros:**
- Catches all Vercel previews
- Works for all branches

**Cons:**
- ⚠️ **SECURITY RISK**: ANY Vercel app can attack our API
- Not CORS compliant (wildcards with credentials don't work)
- Violates security best practices
- **DO NOT USE THIS OPTION**

### Option C: Deploy to Stable Staging Domain (✅ RECOMMENDED)

**Setup:**
1. Create `staging.celeste7.ai` in Vercel
2. Point `universal_v1` branch to staging domain
3. Add to CORS if not already there
4. Use `app.celeste7.ai` only for main branch

**Pros:**
- Follows previous guidance
- Stable, predictable URLs
- Proper staging environment
- No CORS brittleness

**Cons:**
- Requires Vercel configuration
- Need DNS setup for staging subdomain

### Option D: Dynamic Preview URL Validation (⚡ ADVANCED)

**Use Vercel environment variables:**
```python
# In Render dashboard, set env var:
VERCEL_PREVIEW_ALLOWED=true

# In code:
if os.getenv("VERCEL_PREVIEW_ALLOWED") == "true":
    # Validate origin matches pattern
    if origin.endswith(".vercel.app") and "cloud-pms" in origin:
        return True  # Allow
```

**Pros:**
- Flexible for development
- Can be toggled on/off
- Pattern matching instead of exact URL

**Cons:**
- More complex implementation
- Still somewhat brittle
- Need to validate pattern carefully

---

## Recommended Solution

### Phase 1: Immediate Fix (Use Render Environment Variable)

**Add current preview URL to Render env var for testing:**

1. Go to Render Dashboard → pipeline-core service
2. Add environment variable:
   ```
   ALLOWED_ORIGINS=https://app.celeste7.ai,https://staging.celeste7.ai,https://cloud-pms-git-universalv1-c7s-projects-4a165667.vercel.app,http://localhost:3000,http://localhost:8000
   ```
3. Redeploy backend
4. Test search functionality

**Purpose:** Unblock current development/testing

**Temporary:** This URL will change on next Vercel deploy

---

### Phase 2: Proper Solution (Stable Staging Domain)

**Create staging subdomain:**

1. **Vercel Configuration:**
   - Go to Vercel project settings
   - Domains → Add Domain
   - Add `staging.celeste7.ai`
   - Configure DNS (CNAME to Vercel)

2. **Branch Configuration:**
   - Assign `universal_v1` branch → `staging.celeste7.ai`
   - Assign `main` branch → `app.celeste7.ai`
   - Disable preview URLs for these branches

3. **Backend CORS:**
   ```python
   ALLOWED_ORIGINS_STR = os.getenv(
       "ALLOWED_ORIGINS",
       "https://app.celeste7.ai,https://staging.celeste7.ai,http://localhost:3000,http://localhost:8000"
   )
   ```

4. **Microaction Service CORS:**
   ```python
   ALLOWED_ORIGINS_STR = os.getenv(
       "ALLOWED_ORIGINS",
       "https://app.celeste7.ai,https://api.celeste7.ai,https://staging.celeste7.ai,http://localhost:3000,http://localhost:8000"
   )
   ```

**Benefits:**
- Stable URLs
- Proper staging environment
- No CORS brittleness
- Clear separation: production vs staging vs local

---

## Implementation Plan

### Step 1: Immediate Unblock (5 min)

**Action:** Add preview URL to Render environment variable

**Render Dashboard Steps:**
1. Login to Render
2. Navigate to `pipeline-core` service
3. Environment tab
4. Add/Update `ALLOWED_ORIGINS`:
   ```
   https://app.celeste7.ai,https://staging.celeste7.ai,https://cloud-pms-git-universalv1-c7s-projects-4a165667.vercel.app,http://localhost:3000,http://localhost:8000
   ```
5. Save → Auto-redeploys

**Also do for `microaction_service`:**
1. Navigate to microaction service
2. Add same `ALLOWED_ORIGINS` env var
3. Save → Auto-redeploys

**Result:** Search should work within 2-5 minutes

---

### Step 2: Verify Fix (2 min)

**Test:**
1. Wait for Render deployments to complete
2. Open `https://cloud-pms-git-universalv1-c7s-projects-4a165667.vercel.app/search`
3. Search for "manual"
4. Check browser console

**Expected:**
- ✅ No CORS errors
- ✅ Search results appear
- ✅ Backend responds

**If still failing:**
- Check Render logs for CORS logging
- Verify env var was saved correctly
- Check browser network tab for preflight response

---

### Step 3: Create Staging Domain (30 min)

**Vercel Setup:**
1. Login to Vercel
2. Select `Cloud_PMS` project
3. Settings → Domains
4. Add Domain: `staging.celeste7.ai`
5. Copy DNS instructions (CNAME record)

**DNS Setup:**
1. Login to DNS provider (Cloudflare/Route53/etc.)
2. Add CNAME record:
   ```
   staging.celeste7.ai → cname.vercel-dns.com
   ```
3. Wait for DNS propagation (5-10 min)

**Branch Assignment:**
1. In Vercel project settings → Git
2. Assign `universal_v1` branch → `staging.celeste7.ai`
3. Assign `main` branch → `app.celeste7.ai`
4. Disable preview deployments for these branches (optional)

---

### Step 4: Update Backend CORS (Clean Up)

**Once staging domain is working:**

1. Remove preview URL from Render env vars
2. Keep only stable domains:
   ```
   ALLOWED_ORIGINS=https://app.celeste7.ai,https://staging.celeste7.ai,http://localhost:3000,http://localhost:8000
   ```
3. Redeploy both services
4. Test from `staging.celeste7.ai`

**Result:** Clean, stable CORS configuration

---

### Step 5: Document Strategy

**Create `.env.example` entry:**
```bash
# CORS Configuration
# Production + Staging + Local Dev ONLY
# DO NOT add Vercel preview URLs (they change constantly)
# Use staging.celeste7.ai for pre-production testing
ALLOWED_ORIGINS=https://app.celeste7.ai,https://staging.celeste7.ai,http://localhost:3000,http://localhost:8000
```

**Update deployment docs:**
- Staging: Deploy `universal_v1` → `staging.celeste7.ai`
- Production: Deploy `main` → `app.celeste7.ai`
- Local: Use `localhost:3000`
- No preview URLs in CORS

---

## Testing Checklist

### After Step 1 (Immediate Fix)

- [ ] Search works from preview URL
- [ ] Document signing works
- [ ] No CORS errors in console
- [ ] Backend logs show allowed origin

### After Step 3 (Staging Domain)

- [ ] `staging.celeste7.ai` DNS resolves
- [ ] Vercel deploys to staging domain
- [ ] Search works from staging
- [ ] CORS allows staging domain

### After Step 4 (Clean Up)

- [ ] Preview URL removed from CORS
- [ ] Only stable domains in CORS
- [ ] Search still works from staging
- [ ] Production unaffected

---

## Rollback Plan

**If immediate fix breaks something:**

1. Revert Render env var to original:
   ```
   ALLOWED_ORIGINS=https://app.celeste7.ai,https://staging.celeste7.ai,http://localhost:3000,http://localhost:8000
   ```
2. Redeploy services
3. Use `app.celeste7.ai` for testing instead

**If staging domain breaks:**

1. Remove staging domain from Vercel
2. Point `universal_v1` back to preview URLs
3. Temporarily add preview URL to CORS
4. Fix DNS/Vercel config
5. Retry

---

## CORS Configuration Files Reference

### Pipeline Service

**File:** `apps/api/pipeline_service.py`
**Lines:** 48-95
**Env Var:** `ALLOWED_ORIGINS`
**Default:** Listed stable domains

### Microaction Service

**File:** `apps/api/microaction_service.py`
**Lines:** 121-162
**Env Var:** `ALLOWED_ORIGINS`
**Default:** Listed stable domains

### Both Services Share:

- Normalization logic (strip, filter, deduplicate)
- Startup logging
- Vary: Origin middleware
- Bearer token auth (no credentials)
- 1-hour preflight cache

---

## Summary

**Problem:** Vercel preview URL blocked by CORS
**Cause:** Preview URL not in ALLOWED_ORIGINS
**Immediate Fix:** Add preview URL to Render env var (temporary)
**Proper Fix:** Create `staging.celeste7.ai` stable domain
**Long-term:** Use stable domains only, no preview URLs in CORS

**Next Steps:**
1. ✅ Add preview URL to Render (immediate unblock)
2. ⏳ Create staging.celeste7.ai (proper solution)
3. ✅ Clean up CORS to stable domains only
4. ✅ Document strategy for future
