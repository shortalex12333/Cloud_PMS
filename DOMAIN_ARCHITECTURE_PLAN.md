# Domain Architecture Plan - Auth/App Split

**Date:** 2026-01-11
**User Request:** Separate auth and app pages with distinct domains

---

## Proposed Domain Structure

### Production Domains

| Domain | Purpose | Deployment | Branch | Users |
|--------|---------|------------|--------|-------|
| `auth.celeste7.ai` | Login/signup page only | Vercel | `main` | All users (login here first) |
| `app.celeste7.ai` | Main application (search, features) | Vercel | `main` | Authenticated users only |

### Optional: Staging Domains

| Domain | Purpose | Deployment | Branch | Users |
|--------|---------|------------|--------|-------|
| `auth-staging.celeste7.ai` | Test auth changes | Vercel | `universal_v1` | Your team (testing) |
| `staging.celeste7.ai` | Test app changes | Vercel | `universal_v1` | Your team (testing) |

### Backend APIs

| Domain | Purpose | Deployment | Users |
|--------|---------|------------|-------|
| `pipeline-core.int.celeste7.ai` | Pipeline API | Render | App only |
| *(microaction service)* | Microactions | Render | App only |

---

## User Flow (How It Works)

### New User Journey

```
1. User visits: https://app.celeste7.ai
   ↓
2. Not logged in → Redirect to: https://auth.celeste7.ai
   ↓
3. User enters email/password on auth page
   ↓
4. Supabase authenticates → Creates session
   ↓
5. Redirect back to: https://app.celeste7.ai
   ↓
6. User sees search bar, can use app
```

### Returning User Journey

```
1. User visits: https://app.celeste7.ai
   ↓
2. Already logged in (session exists)
   ↓
3. Goes straight to app (no redirect)
```

### Logout Journey

```
1. User clicks logout in app
   ↓
2. Session cleared
   ↓
3. Redirect to: https://auth.celeste7.ai
```

---

## Current vs Proposed Structure

### Current State (Single Domain)

```
https://app.celeste7.ai/
├── / (redirects to /login or /search based on auth)
├── /login (auth page)
├── /search (main app)
├── /dashboard
├── /faults
└── ... (all other pages)
```

**Problem:**
- Auth and app mixed together
- Can't separate concerns cleanly
- Hard to secure auth page separately

### Proposed State (Dual Domain)

**Auth Domain:**
```
https://auth.celeste7.ai/
├── / (login form)
├── /signup (registration)
├── /reset-password
└── /verify-email
```

**App Domain:**
```
https://app.celeste7.ai/
├── / (redirects to /search)
├── /search (main page)
├── /dashboard
├── /faults
├── /work-orders
├── /parts
└── ... (all feature pages)
```

**Benefits:**
- ✅ Clean separation
- ✅ Auth page can have different design
- ✅ App pages always require authentication
- ✅ Can add separate CSP/security for auth
- ✅ Easier to manage

---

## Implementation Plan

### Phase 1: Vercel Configuration (No Code Changes Yet)

**Current Setup:**
- Single Vercel project deploys to `app.celeste7.ai`
- All routes in one Next.js app

**Options:**

**Option A: Single Project, Multiple Domains (EASIER)**
- Keep one Next.js project
- Add both domains to same Vercel project
- Use routing to handle auth vs app pages
- Simpler to maintain

**Option B: Two Separate Projects (MORE ISOLATED)**
- Split into two Next.js projects:
  - `apps/auth` → `auth.celeste7.ai`
  - `apps/app` → `app.celeste7.ai`
- Complete separation
- More complex to set up

**RECOMMENDED: Option A (Single Project, Multiple Domains)**

---

## Step-by-Step: Vercel + Cloudflare Setup

### Step 1: Add Domains to Vercel

**In Vercel Dashboard:**

1. Go to your project (`Cloud_PMS`)
2. Settings → Domains
3. Add Domain: `auth.celeste7.ai`
   - Click "Add"
   - Vercel will show DNS instructions
4. Add Domain: `app.celeste7.ai`
   - Click "Add"
   - Vercel will show DNS instructions

**Vercel will provide CNAME records like:**
```
auth.celeste7.ai → cname.vercel-dns.com
app.celeste7.ai → cname.vercel-dns.com
```

---

### Step 2: Configure DNS in Cloudflare

**Login to Cloudflare:**

1. Select your domain: `celeste7.ai`
2. DNS → Records → Add Record

**Add these CNAME records:**

| Type | Name | Target | Proxy Status |
|------|------|--------|--------------|
| CNAME | `auth` | `cname.vercel-dns.com` | Proxied (orange cloud) |
| CNAME | `app` | `cname.vercel-dns.com` | Proxied (orange cloud) |

**Optional: Staging domains**

| Type | Name | Target | Proxy Status |
|------|------|--------|--------------|
| CNAME | `auth-staging` | `cname.vercel-dns.com` | Proxied |
| CNAME | `staging` | `cname.vercel-dns.com` | Proxied |

**Save and wait 5-10 minutes for DNS propagation**

---

### Step 3: Verify Domain Configuration

**Test DNS:**
```bash
# Check auth domain
dig auth.celeste7.ai

# Check app domain
dig app.celeste7.ai
```

**Expected:** Both should resolve to Vercel IPs

**Test in Browser:**
```
https://auth.celeste7.ai
https://app.celeste7.ai
```

**Expected:** Both load (showing same site initially, before code changes)

---

## Code Changes Required

### Change 1: Route Auth Pages to auth.celeste7.ai

**Current:**
```
app.celeste7.ai/login → Login page
```

**Proposed:**
```
auth.celeste7.ai/ → Login page
auth.celeste7.ai/signup → Signup page
```

**Implementation Options:**

**Option A: Next.js Middleware (RECOMMENDED)**

Create `apps/web/middleware.ts`:
```typescript
import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

export function middleware(request: NextRequest) {
  const hostname = request.headers.get('host');

  // Auth domain - only allow auth pages
  if (hostname === 'auth.celeste7.ai') {
    const path = request.nextUrl.pathname;

    // Allow auth pages
    if (path === '/' || path === '/login' || path === '/signup' || path === '/reset-password') {
      return NextResponse.next();
    }

    // Redirect other pages to app domain
    return NextResponse.redirect(new URL(path, 'https://app.celeste7.ai'));
  }

  // App domain - require authentication
  if (hostname === 'app.celeste7.ai') {
    const path = request.nextUrl.pathname;

    // Auth pages should redirect to auth domain
    if (path === '/login' || path === '/signup') {
      return NextResponse.redirect(new URL(path, 'https://auth.celeste7.ai'));
    }

    // All other pages require auth (handled by withAuth HOC)
    return NextResponse.next();
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    '/((?!api|_next/static|_next/image|favicon.ico).*)',
  ],
};
```

**Option B: Vercel Rewrites (Configuration Only)**

In `apps/web/vercel.json`:
```json
{
  "rewrites": [
    {
      "source": "/login",
      "destination": "https://auth.celeste7.ai/login",
      "has": [{"type": "host", "value": "app.celeste7.ai"}]
    }
  ]
}
```

---

### Change 2: Update Authentication Redirects

**Current:**
```typescript
// After login
router.push('/search');
```

**Update to:**
```typescript
// After login on auth.celeste7.ai
window.location.href = 'https://app.celeste7.ai/search';
```

**Files to update:**
- `apps/web/src/app/login/page.tsx`
- `apps/web/src/contexts/AuthContext.tsx`
- Any logout handlers

---

### Change 3: Update CORS Configuration

**Add auth domain to backend CORS:**

**Pipeline Service (`apps/api/pipeline_service.py`):**
```python
ALLOWED_ORIGINS_STR = os.getenv(
    "ALLOWED_ORIGINS",
    "https://auth.celeste7.ai,https://app.celeste7.ai,https://staging.celeste7.ai,http://localhost:3000"
)
```

**Microaction Service (`apps/api/microaction_service.py`):**
```python
ALLOWED_ORIGINS_STR = os.getenv(
    "ALLOWED_ORIGINS",
    "https://auth.celeste7.ai,https://app.celeste7.ai,https://api.celeste7.ai,https://staging.celeste7.ai,http://localhost:3000"
)
```

**Render Environment Variables:**
```
ALLOWED_ORIGINS=https://auth.celeste7.ai,https://app.celeste7.ai,https://staging.celeste7.ai,http://localhost:3000,http://localhost:8000
```

---

### Change 4: Supabase Session Sharing

**Challenge:** Sessions need to work across `auth.celeste7.ai` and `app.celeste7.ai`

**Solution: Use Supabase JWT in localStorage (current approach)**

**Current implementation (already works):**
- Supabase stores JWT in localStorage
- localStorage is domain-specific
- Need to transfer session from auth → app domain

**Implementation:**

**On auth.celeste7.ai after login:**
```typescript
// Get session
const { data: { session } } = await supabase.auth.getSession();

// Redirect to app with session
const params = new URLSearchParams({
  access_token: session.access_token,
  refresh_token: session.refresh_token,
});

window.location.href = `https://app.celeste7.ai/auth/callback?${params}`;
```

**On app.celeste7.ai/auth/callback:**
```typescript
// Extract tokens from URL
const params = new URLSearchParams(window.location.search);
const accessToken = params.get('access_token');
const refreshToken = params.get('refresh_token');

// Set session in app domain
await supabase.auth.setSession({
  access_token: accessToken,
  refresh_token: refreshToken,
});

// Redirect to app
router.push('/search');
```

---

## Complete File Structure

### Current (Single Domain)

```
apps/web/
├── src/
│   ├── app/
│   │   ├── login/page.tsx (auth page)
│   │   ├── search/SearchContent.tsx (app page)
│   │   ├── dashboard/page.tsx (app page)
│   │   └── ...
│   └── ...
└── ...
```

### Proposed (Dual Domain - Option A)

```
apps/web/
├── src/
│   ├── app/
│   │   ├── login/page.tsx (serves auth.celeste7.ai/)
│   │   ├── signup/page.tsx (serves auth.celeste7.ai/signup)
│   │   ├── auth/
│   │   │   └── callback/page.tsx (handles session transfer)
│   │   ├── search/SearchContent.tsx (serves app.celeste7.ai/search)
│   │   ├── dashboard/page.tsx (serves app.celeste7.ai/dashboard)
│   │   └── ...
│   ├── middleware.ts (NEW - routes by domain)
│   └── ...
└── ...
```

**Key addition:** `middleware.ts` to route based on hostname

---

## Proposed (Dual Domain - Option B - Two Projects)

```
apps/
├── auth/ (NEW PROJECT)
│   ├── src/
│   │   ├── app/
│   │   │   ├── page.tsx (login)
│   │   │   ├── signup/page.tsx
│   │   │   └── reset-password/page.tsx
│   │   └── ...
│   └── package.json
│
├── web/ (EXISTING PROJECT - becomes app only)
│   ├── src/
│   │   ├── app/
│   │   │   ├── auth/callback/page.tsx (session receiver)
│   │   │   ├── search/SearchContent.tsx
│   │   │   ├── dashboard/page.tsx
│   │   │   └── ... (no login pages)
│   │   └── ...
│   └── package.json
│
└── api/ (EXISTING - unchanged)
```

**Vercel Setup:**
- Create new Vercel project for `apps/auth` → `auth.celeste7.ai`
- Keep existing project for `apps/web` → `app.celeste7.ai`

---

## Security Improvements with Auth/App Split

### Auth Domain (`auth.celeste7.ai`)

**Stricter CSP:**
```javascript
// Can be more restrictive - no need for search APIs
"connect-src 'self' https://vzsohavtuotocgrfkfyd.supabase.co"
"frame-ancestors 'none'"  // Prevent embedding
```

**Benefits:**
- ✅ Login page can't be iframed (prevents clickjacking)
- ✅ No unnecessary API access
- ✅ Simpler security model

### App Domain (`app.celeste7.ai`)

**Current CSP + Auth check:**
```javascript
"connect-src 'self' https://vzsohavtuotocgrfkfyd.supabase.co https://pipeline-core.int.celeste7.ai"
```

**Benefits:**
- ✅ All pages require authentication
- ✅ No public routes to secure
- ✅ Can add rate limiting per domain

---

## Summary: What Changes Are Needed

### Immediate Changes (Before Code)

1. **Vercel:**
   - Add `auth.celeste7.ai` domain
   - Add `app.celeste7.ai` domain
   - Get CNAME records

2. **Cloudflare:**
   - Add CNAME for `auth` → Vercel
   - Add CNAME for `app` → Vercel
   - Wait for DNS propagation

3. **Verify:**
   - Both domains load (showing same content initially)

### Code Changes (After DNS Working)

**Option A: Single Project (RECOMMENDED)**

1. **Create `middleware.ts`** - Route by hostname
2. **Update login redirect** - Send to `app.celeste7.ai`
3. **Create `/auth/callback`** - Handle session transfer
4. **Update CORS** - Add both domains to backend

**Files to modify:**
- `apps/web/middleware.ts` (NEW)
- `apps/web/src/app/login/page.tsx`
- `apps/web/src/app/auth/callback/page.tsx` (NEW)
- `apps/web/src/contexts/AuthContext.tsx`
- `apps/api/pipeline_service.py` (CORS)
- `apps/api/microaction_service.py` (CORS)

**Option B: Two Projects**

1. **Create `apps/auth`** - New Next.js project
2. **Move login pages** - From web to auth
3. **Create Vercel project** - For auth app
4. **Session transfer** - Same as Option A
5. **Update CORS** - Add both domains

**More work but cleaner separation**

---

## Recommendation

### For Your Use Case

**RECOMMENDED: Option A (Single Project, Multiple Domains)**

**Reasons:**
- ✅ Easier to maintain (one codebase)
- ✅ Shared components/styles
- ✅ Simpler deployment (one Vercel project)
- ✅ Can always split later if needed

**Steps:**
1. Set up DNS (Cloudflare + Vercel) - 15 min
2. Create middleware.ts for routing - 30 min
3. Update auth redirects - 20 min
4. Create session callback - 20 min
5. Update CORS - 10 min
6. Test both domains - 30 min

**Total time: ~2 hours**

### Staging Strategy

**If you want staging:**
- `auth-staging.celeste7.ai` → Test auth changes
- `staging.celeste7.ai` → Test app changes
- Deploy `universal_v1` branch to staging domains

**If you don't need staging:**
- Skip staging domains
- Test on `localhost:3000`
- Deploy `main` branch directly to production
- Use Vercel preview URLs for quick tests (just know they're temporary)

---

## What Do You Want to Do?

**Before I implement anything, please confirm:**

1. **Domain setup:**
   - ✅ Yes to `auth.celeste7.ai` + `app.celeste7.ai`
   - Do you want staging domains too?

2. **Implementation approach:**
   - Option A (single project, middleware routing) - RECOMMENDED
   - Option B (two separate projects)

3. **Immediate CORS fix:**
   - Should I add current Vercel preview URL to CORS temporarily?
   - Or wait until auth/app domains are set up?

**Let me know your preference and I'll create a step-by-step implementation guide!**
