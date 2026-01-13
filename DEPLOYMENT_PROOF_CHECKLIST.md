# Deployment Proof Checklist

**Execution Time:** ~10 minutes
**Prerequisites:** Git CLI, curl, Vercel Dashboard access

---

## PROOF 1: Automatic Main Deployments

### Step 1.1: Record Current State

```bash
# Get current deployment ID (save this)
curl -sS 'https://app.celeste7.ai' | grep -o 'dpl_[A-Za-z0-9]*' | head -1
```

**Record:** `dpl_________________` (BEFORE)

### Step 1.2: Push Test Commit to Main

```bash
cd /Users/celeste7/Documents/Cloud_PMS
echo "// Deployment proof: $(date -u +%Y-%m-%dT%H:%M:%SZ)" >> apps/web/src/app/page.tsx
git add apps/web/src/app/page.tsx
git commit -m "proof: verify auto-deploy to production"
git push origin main
```

**Record commit SHA:**
```bash
git rev-parse --short HEAD
```
**Commit SHA:** `_______`

### Step 1.3: Verify in Vercel Dashboard

**Location:** Vercel Dashboard → Project → Deployments

**Within 2-3 minutes, confirm:**

| Check | Where to Look | Pass Criteria |
|-------|---------------|---------------|
| New deployment created | Deployments list | New entry at top with "Building" or "Ready" |
| Environment = Production | Badge next to deployment | Shows "Production" (not "Preview") |
| Git Branch = main | Deployment details → Source | Shows `main` |
| Commit SHA matches | Deployment details → Source | SHA matches your recorded commit |
| Commit message visible | Deployment details → Source | Shows "proof: verify auto-deploy to production" |

### Step 1.4: Verify Deployment ID Changed

**Wait until deployment is "Ready", then:**

```bash
curl -sS 'https://app.celeste7.ai' | grep -o 'dpl_[A-Za-z0-9]*' | head -1
```

**Record:** `dpl_________________` (AFTER)

**Pass Criteria:** AFTER ≠ BEFORE (deployment ID changed)

---

## PROOF 2: Preview Branch Isolation

### Step 2.1: Create Feature Branch (No PR)

```bash
git checkout -b feature/test-proof
echo "// Preview test: $(date -u +%Y-%m-%dT%H:%M:%SZ)" >> apps/web/src/app/page.tsx
git add apps/web/src/app/page.tsx
git commit -m "test: preview branch isolation"
git push origin feature/test-proof
```

### Step 2.2: Check Vercel Dashboard

**Location:** Vercel Dashboard → Project → Deployments

**Within 2-3 minutes, observe:**

| Scenario | Expected Behavior |
|----------|-------------------|
| Branch push (no PR) | **May or may not** create Preview deployment (depends on Vercel settings) |
| If deployment created | Must show "Preview" badge, NOT "Production" |

**Regardless of preview creation, verify Production unchanged:**

```bash
curl -sS 'https://app.celeste7.ai' | grep -o 'dpl_[A-Za-z0-9]*' | head -1
```

**Pass Criteria:** Same deployment ID as Proof 1 AFTER (Production NOT affected)

### Step 2.3: Open Pull Request

```bash
# Open PR via GitHub CLI (or use GitHub web UI)
gh pr create --base main --head feature/test-proof --title "Test: Preview isolation proof" --body "Testing preview deployment isolation"
```

**Or manually:** GitHub → Pull Requests → New → base:main ← compare:feature/test-proof

### Step 2.4: Verify Preview Deployment

**Location:** Vercel Dashboard → Project → Deployments

**Within 2-3 minutes, confirm:**

| Check | Where to Look | Pass Criteria |
|-------|---------------|---------------|
| New deployment created | Deployments list | New entry with "Building" or "Ready" |
| Environment = Preview | Badge next to deployment | Shows "Preview" (NOT "Production") |
| Git Branch = feature/test-proof | Deployment details → Source | Shows `feature/test-proof` |
| PR number linked | Deployment details | Shows PR # |

**Also verify on GitHub PR page:**
- Vercel bot comment with Preview URL
- Preview URL format: `cloud-pms-*-*.vercel.app` (NOT production domain)

### Step 2.5: Confirm Production Still Unchanged

```bash
curl -sS 'https://app.celeste7.ai' | grep -o 'dpl_[A-Za-z0-9]*' | head -1
```

**Pass Criteria:** STILL same deployment ID as Proof 1 AFTER

### Step 2.6: Cleanup

```bash
# Close PR without merging
gh pr close feature/test-proof

# Delete branch
git checkout main
git branch -D feature/test-proof
git push origin --delete feature/test-proof
```

---

## PROOF 3: Browser-Real CORS

### Step 3.1: OPTIONS Preflight (app → auth)

**Exact curl command:**

```bash
curl -sS -i -X OPTIONS 'https://auth.celeste7.ai/login' \
  -H 'Origin: https://app.celeste7.ai' \
  -H 'Access-Control-Request-Method: GET' \
  -H 'Access-Control-Request-Headers: Content-Type, Authorization, RSC, Next-Router-State-Tree'
```

**Required response (ALL must be present):**

| Header | Required Value |
|--------|----------------|
| `HTTP/2 200` | Status must be 200 |
| `access-control-allow-origin` | `https://app.celeste7.ai` (exact match) |
| `access-control-allow-methods` | Must include `GET, POST, OPTIONS` |
| `access-control-allow-headers` | Must include `Content-Type, Authorization, RSC, Next-Router-State-Tree` |
| `access-control-allow-credentials` | `true` |

### Step 3.2: OPTIONS Preflight (app → backend API)

```bash
curl -sS -i -X OPTIONS 'https://pipeline-core.int.celeste7.ai/search' \
  -H 'Origin: https://app.celeste7.ai' \
  -H 'Access-Control-Request-Method: POST' \
  -H 'Access-Control-Request-Headers: Content-Type, Authorization, X-Yacht-Signature'
```

**Required response:**

| Header | Required Value |
|--------|----------------|
| `HTTP/2 200` | Status must be 200 |
| `access-control-allow-origin` | `https://app.celeste7.ai` |
| `access-control-allow-methods` | Must include `POST, OPTIONS` |
| `access-control-allow-headers` | Must include `Authorization, Content-Type, X-Yacht-Signature` |

### Step 3.3: Negative CORS Test (Blocked Origin)

```bash
curl -sS -i -X OPTIONS 'https://auth.celeste7.ai/login' \
  -H 'Origin: https://evil-attacker.com' \
  -H 'Access-Control-Request-Method: GET'
```

**Required response:**

| Check | Pass Criteria |
|-------|---------------|
| No `access-control-allow-origin` header | Header absent OR not `https://evil-attacker.com` |
| Status | 200 or 400 (but NO valid ACAO for attacker origin) |

---

## FINAL GO/NO-GO CHECKLIST

### Execute in Order (Total: ~10 min)

| # | Test | Command/Action | Pass | Fail |
|---|------|----------------|------|------|
| **PROOF 1: Auto Deploy** |
| 1.1 | Record current dpl_* | `curl -sS 'https://app.celeste7.ai' \| grep -o 'dpl_[A-Za-z0-9]*' \| head -1` | Record value | - |
| 1.2 | Push to main | See Step 1.2 commands | Commit pushed | Push fails |
| 1.3 | Deployment created | Vercel Dashboard → Deployments | New "Production" deployment appears | No deployment |
| 1.4 | Branch = main | Deployment → Source | Shows `main` | Shows other branch |
| 1.5 | SHA matches | Deployment → Source | SHA = your commit | SHA mismatch |
| 1.6 | dpl_* changed | Repeat curl command | Different from 1.1 | Same as 1.1 |
| **PROOF 2: Preview Isolation** |
| 2.1 | Create feature branch | See Step 2.1 commands | Branch pushed | Push fails |
| 2.2 | Production unchanged | curl for dpl_* | Same as 1.6 | Different |
| 2.3 | Open PR | GitHub or `gh pr create` | PR created | PR fails |
| 2.4 | Preview deployment | Vercel Dashboard | "Preview" badge (not Production) | "Production" badge |
| 2.5 | Production STILL unchanged | curl for dpl_* | Same as 1.6 | Different |
| **PROOF 3: CORS** |
| 3.1 | OPTIONS app→auth | See Step 3.1 curl | All 5 headers correct | Missing headers |
| 3.2 | OPTIONS app→backend | See Step 3.2 curl | All 4 headers correct | Missing headers |
| 3.3 | Blocked origin | See Step 3.3 curl | No valid ACAO | Attacker origin allowed |

### Scoring

- **GO:** All 13 checks pass
- **NO-GO:** Any check fails

---

## Quick Reference: Expected curl Outputs

### CORS app→auth (Pass):
```
HTTP/2 200
access-control-allow-credentials: true
access-control-allow-headers: Content-Type, Authorization, X-Requested-With, RSC, Next-Router-State-Tree, Next-Router-Prefetch
access-control-allow-methods: GET, POST, OPTIONS
access-control-allow-origin: https://app.celeste7.ai
access-control-max-age: 86400
```

### CORS app→backend (Pass):
```
HTTP/2 200
access-control-allow-headers: Accept, Accept-Language, Authorization, Content-Language, Content-Type, X-Request-Id, X-Yacht-Signature
access-control-allow-methods: GET, POST, OPTIONS
access-control-allow-origin: https://app.celeste7.ai
access-control-max-age: 3600
```

### Blocked origin (Pass):
```
HTTP/2 200
(NO access-control-allow-origin header, OR)
HTTP/2 400
Disallowed CORS origin
```

---

## Failure Recovery

| Failure | Likely Cause | Fix |
|---------|--------------|-----|
| No deployment after push | Root Directory wrong or Ignored Build Step set | Vercel → Settings → Git |
| Deployment is Preview not Production | Production Branch ≠ main | Vercel → Settings → Git → Production Branch |
| CORS missing headers | Middleware not deployed | Check middleware.ts deployed, redeploy |
| Production dpl_* changed on PR | PR merged accidentally OR Production Branch wrong | Check Git settings |

---

*Execute this checklist after any infrastructure change.*
