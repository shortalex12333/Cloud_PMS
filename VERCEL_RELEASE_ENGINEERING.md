# Vercel + GitHub Release Engineering Verification

**Created:** 2026-01-13
**Project:** CelesteOS (Cloud_PMS)
**Domains:** app.celeste7.ai, auth.celeste7.ai

---

## 1. REQUIRED VERCEL SETTINGS

### 1.1 Git Integration Settings
**Location:** Vercel Dashboard → Project → Settings → Git

| Setting | Required Value | Why |
|---------|---------------|-----|
| **Repository** | `shortalex12333/Cloud_PMS` | Must match your GitHub repo |
| **Production Branch** | `main` | Pushes to main = Production deployments |
| **Root Directory** | `apps/web` | Next.js app location |
| **Ignored Build Step** | Empty or disabled | If set, may skip builds |

### 1.2 Domain Settings
**Location:** Vercel Dashboard → Project → Settings → Domains

| Domain | Type | Required |
|--------|------|----------|
| `app.celeste7.ai` | Production | ✅ Must be added |
| `auth.celeste7.ai` | Production | ✅ Must be added |
| `celesteos-product.vercel.app` | Auto-generated | Default |

### 1.3 Deployment Protection (CRITICAL)
**Location:** Vercel Dashboard → Project → Settings → Deployment Protection

| Setting | Required Value | Why |
|---------|---------------|-----|
| **Vercel Authentication** | OFF for Production | Login wall if ON |
| **Password Protection** | OFF | Login wall if ON |
| **Trusted IPs** | Not configured | Blocks public access if set |
| **Preview Deployments** | Can be ON | Only affects *.vercel.app previews |

**CRITICAL:** If "Vercel Authentication" is ON for Production, visitors see Vercel login instead of your app.

### 1.4 Environment Variables
**Location:** Vercel Dashboard → Project → Settings → Environment Variables

| Variable | Scope | Required |
|----------|-------|----------|
| `NEXT_PUBLIC_SUPABASE_URL` | Production, Preview | ✅ |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Production, Preview | ✅ |
| `NEXT_PUBLIC_YACHT_SALT` | Production | ✅ |
| `NEXT_PUBLIC_APP_URL` | Production | Should be `https://app.celeste7.ai` |

---

## 2. VERIFICATION PLAN

### Test A: Domain → Project Ownership
**Purpose:** Verify your Vercel project owns the custom domains

```bash
# Check app.celeste7.ai
curl -sS -I 'https://app.celeste7.ai' | grep -E 'x-vercel-id'

# Check auth.celeste7.ai
curl -sS -I 'https://auth.celeste7.ai' | grep -E 'x-vercel-id'
```

**Expected:** Both return `x-vercel-id` header (proves Vercel is serving)

**If failing:** Domain DNS not pointing to Vercel, or domain not added to project

---

### Test B: No Vercel Auth Wall
**Purpose:** Verify public access without Vercel login

```bash
# Should return your app's HTML, NOT Vercel login page
curl -sS 'https://app.celeste7.ai/login' | grep -E '(CelesteOS|vercel-authentication)'
```

**Expected:** Contains "CelesteOS", NOT "vercel-authentication"

**If failing:** Deployment Protection → Vercel Authentication is ON

---

### Test C: Deployment ID Consistency
**Purpose:** Verify all domains serve the same deployment

```bash
# Extract deployment IDs from all domains
curl -sS 'https://app.celeste7.ai' | grep -o 'dpl_[A-Za-z0-9]*' | head -1
curl -sS 'https://auth.celeste7.ai' | grep -o 'dpl_[A-Za-z0-9]*' | head -1
curl -sS 'https://celesteos-product.vercel.app' | grep -o 'dpl_[A-Za-z0-9]*' | head -1
```

**Expected:** All three return the SAME deployment ID (e.g., `dpl_DyTBy1V5YeRHMuvpWmCsibxEfTnV`)

**If failing:** Domains pointing to different Vercel projects

---

### Test D: Git Commit → Deployment Traceability
**Purpose:** Verify which Git commit a deployment came from

```bash
# Get latest Git commit on main
git log origin/main --oneline -1

# Get Build ID from production
curl -sS 'https://app.celeste7.ai' | grep -o 'buildId":"[^"]*"' | head -1
```

**Then:** In Vercel Dashboard → Deployments, find the deployment with matching Build ID.
Click it → "Source" tab shows the Git commit SHA.

---

### Test E: Push → Deploy Verification
**Purpose:** Verify push to main triggers production deployment

1. Note current deployment ID:
   ```bash
   curl -sS 'https://app.celeste7.ai' | grep -o 'dpl_[A-Za-z0-9]*' | head -1
   ```

2. Make a trivial commit to main:
   ```bash
   echo "// $(date)" >> apps/web/src/app/layout.tsx
   git add apps/web/src/app/layout.tsx
   git commit -m "test: verify deployment pipeline"
   git push origin main
   ```

3. Wait 2-3 minutes, then check deployment ID again:
   ```bash
   curl -sS 'https://app.celeste7.ai' | grep -o 'dpl_[A-Za-z0-9]*' | head -1
   ```

**Expected:** Deployment ID changes after push

**If failing:**
- Root Directory mismatch
- Ignored Build Step blocking
- GitHub integration disconnected

---

### Test F: Middleware Routing
**Purpose:** Verify hostname-based routing works

```bash
# On auth domain, root should serve login
curl -sS -I 'https://auth.celeste7.ai/' | grep location
# Expected: location: /login

# On app domain, /login should redirect to auth
curl -sS -I 'https://app.celeste7.ai/login' | grep location
# Expected: location: https://auth.celeste7.ai/login (307 redirect)
```

---

## 3. PROOF CHECKLIST (Run After Every Change)

### Pre-Deployment Checks

| # | Check | Command | Pass Criteria |
|---|-------|---------|---------------|
| 1 | Git branch is main | `git branch --show-current` | Returns `main` |
| 2 | Working tree clean | `git status --short` | No uncommitted changes |
| 3 | Local matches remote | `git log origin/main --oneline -1` | Same as local HEAD |

### Post-Deployment Checks (Incognito Browser)

| # | Check | How | Pass Criteria |
|---|-------|-----|---------------|
| 4 | app.celeste7.ai loads | Visit in incognito | App loads, no Vercel login |
| 5 | auth.celeste7.ai loads | Visit in incognito | Login page loads |
| 6 | No console errors | Open DevTools | No critical errors |
| 7 | CSP allows connections | Check Network tab | No CSP violations |

### API Verification

| # | Check | Command | Pass Criteria |
|---|-------|---------|---------------|
| 8 | Vercel serving app | `curl -sI https://app.celeste7.ai \| grep x-vercel` | Has x-vercel-id |
| 9 | No auth wall | `curl -sS https://app.celeste7.ai \| grep CelesteOS` | Contains CelesteOS |
| 10 | CORS working | `curl -sI -X OPTIONS https://auth.celeste7.ai -H 'Origin: https://app.celeste7.ai' \| grep access-control` | Has ACAO header |

---

## 4. FAILURE MODE DIAGNOSIS

### Failure Mode 1: Wrong Vercel Project Owns Domain

**Symptoms:**
- Domain serves different app than expected
- Deployment ID doesn't match your project

**Detection:**
```bash
curl -sS 'https://app.celeste7.ai' | grep -o 'dpl_[A-Za-z0-9]*' | head -1
```
Then check Vercel Dashboard → Deployments for that ID.

**Fix:** Remove domain from wrong project, add to correct project.

---

### Failure Mode 2: Vercel Authentication Enabled

**Symptoms:**
- Visitors see Vercel login page
- curl returns HTML with "vercel-authentication"

**Detection:**
```bash
curl -sS 'https://app.celeste7.ai' | grep -i 'vercel-authentication'
```

**Fix:** Project Settings → Deployment Protection → Disable "Vercel Authentication" for Production

---

### Failure Mode 3: Root Directory Skip

**Symptoms:**
- Push to main doesn't trigger build
- Or build runs but deploys wrong code

**Detection:**
Vercel Dashboard → Deployments → Check if deployment was created after push.
If not, check Settings → Git → Root Directory and Ignored Build Step.

**Fix:** Ensure Root Directory = `apps/web`, Ignored Build Step = empty

---

### Failure Mode 4: Production Branch Mismatch

**Symptoms:**
- Push to main creates Preview, not Production
- Production domain shows old code

**Detection:**
Vercel Dashboard → Deployments → Check "Production" label on deployments.
Settings → Git → Production Branch should be `main`.

**Fix:** Change Production Branch to `main`

---

### Failure Mode 5: GitHub Default Branch Not Main

**Symptoms:**
- Vercel builds from wrong branch
- PRs to main don't trigger previews

**Detection:**
GitHub repo → Settings → Default branch

**Fix:** Set default branch to `main` on GitHub

---

### Failure Mode 6: Env Var Mismatch (Wrong App URL)

**Symptoms:**
- Auth redirects to wrong domain
- CORS errors from wrong origin

**Detection:**
```bash
# Check what URL the app thinks it's at
curl -sS 'https://app.celeste7.ai' | grep -o 'NEXT_PUBLIC_APP_URL[^"]*'
```

**Fix:** Set `NEXT_PUBLIC_APP_URL=https://app.celeste7.ai` in Vercel env vars

---

## 5. GO/NO-GO CHECKLIST

### Before Release

| # | Item | Status | Evidence |
|---|------|--------|----------|
| 1 | Vercel project connected to correct GitHub repo | ☐ | Screenshot: Settings → Git |
| 2 | Production Branch = main | ☐ | Screenshot: Settings → Git |
| 3 | Root Directory = apps/web | ☐ | Screenshot: Settings → Git |
| 4 | Deployment Protection OFF for Production | ☐ | Screenshot: Settings → Deployment Protection |
| 5 | Custom domains added (app/auth.celeste7.ai) | ☐ | Screenshot: Settings → Domains |
| 6 | Required env vars set | ☐ | Screenshot: Settings → Environment Variables |

### After Deployment

| # | Item | Status | Evidence |
|---|------|--------|----------|
| 7 | app.celeste7.ai serves app (not Vercel login) | ☐ | curl output showing CelesteOS |
| 8 | auth.celeste7.ai serves login page | ☐ | curl output showing login HTML |
| 9 | Deployment ID matches across all domains | ☐ | curl output showing same dpl_* |
| 10 | CORS headers present | ☐ | curl OPTIONS output |
| 11 | No CSP violations in browser console | ☐ | DevTools screenshot |
| 12 | Latest Git commit matches deployment source | ☐ | Vercel deployment details |

---

## 6. SCREENSHOTS TO CAPTURE

For audit trail, capture these Vercel Dashboard screens:

1. **Settings → Git**
   - Shows: Repository, Production Branch, Root Directory

2. **Settings → Domains**
   - Shows: All configured domains and their status

3. **Settings → Deployment Protection**
   - Shows: Authentication settings per environment

4. **Settings → Environment Variables**
   - Shows: All env vars (values can be hidden)

5. **Deployments → Latest Production**
   - Shows: Deployment status, Git commit, build logs

---

## 7. CURRENT STATE VERIFICATION

Run this to get current deployment state:

```bash
echo "=== DEPLOYMENT STATE ==="
echo ""
echo "Git Commit (main):"
git log origin/main --oneline -1
echo ""
echo "app.celeste7.ai deployment:"
curl -sS 'https://app.celeste7.ai' | grep -o 'dpl_[A-Za-z0-9]*' | head -1
echo ""
echo "auth.celeste7.ai deployment:"
curl -sS 'https://auth.celeste7.ai' | grep -o 'dpl_[A-Za-z0-9]*' | head -1
echo ""
echo "Vercel serving (x-vercel-id):"
curl -sI 'https://app.celeste7.ai' 2>/dev/null | grep x-vercel-id
echo ""
echo "Auth wall check (should be empty):"
curl -sS 'https://app.celeste7.ai' | grep -o 'vercel-authentication' || echo "PASS - No auth wall"
```

---

*Document maintained by Release Engineering. Update after any Vercel configuration change.*
