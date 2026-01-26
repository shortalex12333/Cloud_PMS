# Render Docker Deployment Guide

## Overview

This guide covers switching the `pipeline-core` service from Render source builds to Docker image deploys using GHCR (GitHub Container Registry).

**Benefits:**
- Faster deploys (~30-60s vs 2-5min)
- Reproducible environments
- Local validation before release
- Immutable production deploys by digest

---

## Prerequisites

1. **GitHub Actions workflow** running: `.github/workflows/docker-pipeline-core.yml`
2. **GHCR package** visible at: `ghcr.io/shortalex12333/pipeline-core`
3. **Render service** currently running (we'll switch it)

---

## Phase 1: Verify Image Builds

### 1.1 Trigger a Build

Push to `main` with changes in `apps/api/`:
```bash
git push origin main
```

Or manually trigger:
1. Go to GitHub → Actions → "Docker - Pipeline Core"
2. Click "Run workflow" → "Run workflow"

### 1.2 Verify Image in GHCR

1. Go to: https://github.com/shortalex12333?tab=packages
2. Find `pipeline-core` package
3. Note the tags: `main-<sha7>`, `latest`

### 1.3 Local Validation (Optional but Recommended)

```bash
# Pull the image
docker pull ghcr.io/shortalex12333/pipeline-core:latest

# Run locally with env vars
docker run -p 8080:8080 \
  -e SUPABASE_URL="https://vzsohavtuotocgrfkfyd.supabase.co" \
  -e yTEST_YACHT_001_SUPABASE_URL="https://vzsohavtuotocgrfkfyd.supabase.co" \
  -e yTEST_YACHT_001_SUPABASE_SERVICE_KEY="<key>" \
  -e MASTER_SUPABASE_URL="https://qvzmkaamzaqxpzbewjxe.supabase.co" \
  -e MASTER_SUPABASE_SERVICE_KEY="<key>" \
  -e OPENAI_API_KEY="<key>" \
  ghcr.io/shortalex12333/pipeline-core:latest

# Test health endpoint
curl http://localhost:8080/health
```

---

## Phase 2: Switch Render to Docker

### 2.1 Staging First

1. Go to Render Dashboard → `pipeline-core` service (or create staging clone)
2. Click **Settings** → **Build & Deploy**
3. Change **Runtime** from "Native" to **"Docker"**
4. Set **Image URL**:
   ```
   ghcr.io/shortalex12333/pipeline-core:main-<sha7>
   ```
   Or for latest:
   ```
   ghcr.io/shortalex12333/pipeline-core:latest
   ```

5. **Docker Command** (leave empty - Dockerfile has CMD)

6. **Registry Credentials** (if private):
   - Username: `${{ github.actor }}` or your GitHub username
   - Password: GitHub PAT with `read:packages` scope

   For public packages, no credentials needed.

7. Click **Save Changes** → **Manual Deploy** → **Deploy latest commit**

### 2.2 Verify Staging

```bash
# Health check
curl https://pipeline-core-staging.int.celeste7.ai/health

# Test an endpoint
curl -H "Authorization: Bearer <jwt>" \
  https://pipeline-core-staging.int.celeste7.ai/email/inbox
```

### 2.3 Production (Deploy by Digest)

For production, use immutable digest instead of tag:

1. Get digest from GitHub Actions summary or:
   ```bash
   docker inspect --format='{{index .RepoDigests 0}}' \
     ghcr.io/shortalex12333/pipeline-core:main-<sha7>
   ```

2. In Render, set Image URL:
   ```
   ghcr.io/shortalex12333/pipeline-core@sha256:abc123...
   ```

3. Deploy and verify.

---

## Phase 3: Environment Variables

Ensure these are set in Render (NOT in the Docker image):

### Required
| Variable | Description |
|----------|-------------|
| `PORT` | `8080` (Render default) |
| `MASTER_SUPABASE_URL` | Master DB URL |
| `MASTER_SUPABASE_SERVICE_KEY` | Master service key |
| `MASTER_SUPABASE_JWT_SECRET` | JWT signing secret |
| `OPENAI_API_KEY` | OpenAI API key |

### Per-Tenant (Multi-yacht)
| Variable | Description |
|----------|-------------|
| `yTEST_YACHT_001_SUPABASE_URL` | Tenant DB URL |
| `yTEST_YACHT_001_SUPABASE_SERVICE_KEY` | Tenant service key |
| `yTEST_YACHT_001_SUPABASE_JWT_SECRET` | Tenant JWT secret |

### Feature Flags (Optional)
| Variable | Default |
|----------|---------|
| `EMAIL_TRANSPORT_ENABLED` | `true` |
| `EMAIL_LINK_ENABLED` | `true` |
| `EMAIL_RENDER_ENABLED` | `true` |

---

## Rollback Plan

### Option A: Roll Back to Previous Digest (Fast)

1. In Render, change Image URL to previous known-good digest
2. Deploy

### Option B: Revert to Source Build (Slower)

1. In Render Settings → Build & Deploy
2. Change Runtime back to "Native"
3. Set Build Command: `pip install -r requirements.txt`
4. Set Start Command: `uvicorn pipeline_service:app --host 0.0.0.0 --port $PORT`
5. Deploy

### Keep Track of Known-Good Digests

| Date | Tag | Digest | Notes |
|------|-----|--------|-------|
| 2026-01-26 | main-cf60c22 | sha256:... | Initial Docker deploy |

---

## Health Check Configuration

In Render service settings:
- **Health Check Path:** `/health`
- **Health Check Port:** `8080`
- **Health Check Timeout:** `10s`

The Dockerfile also includes internal healthcheck.

---

## Troubleshooting

### Image Pull Fails (403/401)
- Check GHCR package visibility (should be public or credentials configured)
- Verify PAT has `read:packages` scope

### Container Starts But /health Fails
- Check PORT env var matches EXPOSE in Dockerfile
- Check logs for startup errors (missing env vars)

### Missing Tenant Credentials
- Error: `Missing credentials for tenant yTEST_YACHT_001`
- Fix: Add `yTEST_YACHT_001_SUPABASE_URL` and `yTEST_YACHT_001_SUPABASE_SERVICE_KEY` to Render env vars

---

## CI/CD Flow Summary

```
Push to main
    ↓
GitHub Actions: docker-pipeline-core.yml
    ↓
Build multi-stage image
    ↓
Push to ghcr.io/shortalex12333/pipeline-core:main-<sha7>
    ↓
(Manual or auto) Update Render image URL
    ↓
Render pulls image → deploys (30-60s)
    ↓
Health check passes → traffic routed
```

---

## Next Steps

1. [ ] Push this change to trigger first Docker build
2. [ ] Verify image in GHCR
3. [ ] Test locally (optional)
4. [ ] Switch Render staging to Docker
5. [ ] Validate staging
6. [ ] Switch Render production to Docker (by digest)
7. [ ] Document known-good digest
