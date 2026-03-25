# CelesteOS Deployment Guide

> **For:** Anyone deploying CelesteOS — no technical background assumed.
> **Last updated:** 25 March 2026

---

## Platform Overview

| Platform | What runs there | URL |
|----------|----------------|-----|
| **Vercel** | Frontend website (Next.js) | `app.celeste7.ai` |
| **Render** | Backend API + background workers | `pipeline-core.int.celeste7.ai` |
| **Supabase** | Database + Auth + File Storage | `vzsohavtuotocgrfkfyd.supabase.co` |

---

## Custom Domains

| Domain | Points to | Managed by |
|--------|-----------|------------|
| `app.celeste7.ai` | Vercel (frontend) | Cloudflare DNS |
| `pipeline-core.int.celeste7.ai` | Render (API) | Cloudflare DNS |
| `celeste7.ai` | Landing page | Cloudflare DNS |

---

## Database Connection Types

There are **two** connection types. Using the wrong one breaks services.

| Type | Port | When to use | Which services |
|------|------|-------------|----------------|
| **Direct** | `5432` | LISTEN/NOTIFY, long connections | Cache Listener, API (`READ_DB_DSN`) |
| **Pooler** (Supavisor) | `6543` | Short queries, workers | Projection, Embedding, Extraction, Nightly Feedback |

**Format:**
```
Direct:  postgresql://postgres:{password}@db.vzsohavtuotocgrfkfyd.supabase.co:5432/postgres
Pooler:  postgresql://postgres.vzsohavtuotocgrfkfyd:{password}@aws-0-us-west-1.pooler.supabase.com:6543/postgres
```

---

## SERVICE 1: Frontend (Vercel)

**What it does:** The website crew members see and interact with.

| Setting | Value |
|---------|-------|
| Platform | Vercel |
| Framework | Next.js |
| Git repo | `shortalex12333/Cloud_PMS` |
| Root directory | `apps/web` |
| Build command | `npm run build` |
| Output directory | `.next` |
| Install command | `npm install` |
| Node version | 18.x |
| Custom domain | `app.celeste7.ai` |
| Auto-deploy | Yes — deploys on every push to `main` |

### Environment Variables

Set in **Vercel dashboard → Settings → Environment Variables**:

| Variable | Value | Secret? |
|----------|-------|---------|
| `NEXT_PUBLIC_SUPABASE_URL` | `https://vzsohavtuotocgrfkfyd.supabase.co` | No |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | *(from env vars doc)* | Yes |
| `NEXT_PUBLIC_API_URL` | `https://pipeline-core.int.celeste7.ai` | No |
| `NEXT_PUBLIC_APP_URL` | `https://app.celeste7.ai` | No |
| `NEXT_PUBLIC_FRAGMENTED_ROUTES_ENABLED` | `true` | No |

### How to verify

Open `https://app.celeste7.ai` in a browser. If the search bar loads, it's working.

---

## SERVICE 2: API (Render — Web Service)

**What it does:** The brain — handles search, actions, email endpoints, entity data, handover export routing.

| Setting | Value |
|---------|-------|
| Platform | Render |
| Type | **Web Service** |
| Name | `celeste-pipeline-v1` |
| Region | Oregon |
| Plan | Starter ($7/mo, 512MB) |
| Git repo | `shortalex12333/Cloud_PMS` |
| Branch | `main` |
| Root directory | *(leave empty — uses repo root)* |
| Build command | `chmod +x build.sh && ./build.sh` |
| Start command | `cd apps/api && uvicorn pipeline_service:app --host 0.0.0.0 --port $PORT` |
| Health check path | `/health` |
| Auto-deploy | Yes |
| Custom domain | `pipeline-core.int.celeste7.ai` |
| Python version | 3.11.6 |

### Environment Variables

Set in **Render dashboard → your service → Environment**:

| Variable | Value | Notes |
|----------|-------|-------|
| `PYTHON_VERSION` | `3.11.6` | |
| `MASTER_SUPABASE_URL` | `https://qvzmkaamzaqxpzbewjxe.supabase.co` | Master DB (auth only) |
| `MASTER_SUPABASE_SERVICE_KEY` | *(secret)* | |
| `MASTER_SUPABASE_JWT_SECRET` | *(secret)* | |
| `yTEST_YACHT_001_SUPABASE_URL` | `https://vzsohavtuotocgrfkfyd.supabase.co` | Tenant DB |
| `yTEST_YACHT_001_SUPABASE_SERVICE_KEY` | *(secret)* | |
| `yTEST_YACHT_001_SUPABASE_ANON_KEY` | *(secret)* | |
| `SUPABASE_URL` | `https://vzsohavtuotocgrfkfyd.supabase.co` | Fallback to tenant |
| `SUPABASE_SERVICE_KEY` | *(same as yTEST_YACHT_001 service key)* | |
| `TENANT_SUPABASE_ANON_KEY` | *(same as yTEST_YACHT_001 anon key)* | |
| `TENANT_SUPABASE_JWT_SECRET` | *(secret)* | JWT verification |
| `OPENAI_API_KEY` | *(secret)* | For RAG + embeddings |
| `REDIS_URL` | *(secret)* | Rate limiting + cache |
| `READ_DB_DSN` | *(direct connection, port 5432)* | For LISTEN/NOTIFY |
| `DATABASE_URL` | *(pooler connection, port 6543)* | General queries |
| `AZURE_READ_APP_ID` | `41f6dc82-8127-4330-97e0-c6b26e6aa967` | Microsoft Graph read |
| `AZURE_READ_CLIENT_SECRET` | *(secret)* | |
| `AZURE_WRITE_APP_ID` | `f0b8944b-8127-4f0f-8ed5-5487462df50c` | Microsoft Graph write |
| `AZURE_WRITE_CLIENT_SECRET` | *(secret)* | |
| `SHOPPING_LIST_LENS_V1_ENABLED` | `true` | Feature flag |
| `HANDOVER_EXPORT_SERVICE_URL` | *(URL of handover export service)* | |
| `HANDOVER_USE_MICROSERVICE` | `true` | |

### How to verify

```
curl https://pipeline-core.int.celeste7.ai/health
```
Should return: `{"status": "healthy", "pipeline_ready": true}`

---

## SERVICE 3: Email Watcher (Render — Background Worker)

**What it does:** Syncs emails from Microsoft Outlook every 30 seconds. Runs 24/7.

| Setting | Value |
|---------|-------|
| Type | **Background Worker** |
| Name | `celeste-email-watcher` |
| Region | Oregon |
| Plan | Starter ($7/mo, 512MB) |
| Build command | `cd apps/api && pip install -r requirements.txt` |
| Start command | `cd apps/api && python -m workers.email_watcher_worker` |
| Auto-deploy | Yes |
| Python version | 3.11.6 |

### Environment Variables

| Variable | Value |
|----------|-------|
| `PYTHON_VERSION` | `3.11.6` |
| `EMAIL_WATCHER_ENABLED` | `true` |
| `EMAIL_WATCHER_POLL_INTERVAL` | `30` |
| `EMAIL_WATCHER_BATCH_SIZE` | `10` |
| `SUPABASE_URL` | `https://vzsohavtuotocgrfkfyd.supabase.co` |
| `SUPABASE_SERVICE_KEY` | *(secret)* |
| `AZURE_READ_CLIENT_SECRET` | *(secret)* |

### How to verify

Check Render logs. Should show:
- `"Syncing watcher for user=..."` every 15 minutes
- `"Stats: cycles=X, messages=Y, errors=0"`

No health check path — background workers don't have HTTP endpoints.

---

## SERVICE 4: Projection Worker (Render — Background Worker)

**What it does:** Watches database tables and builds search text for every entity (work orders, faults, parts, etc).

| Setting | Value |
|---------|-------|
| Type | **Background Worker** |
| Name | `celeste-projection-worker` |
| Build command | `chmod +x build.sh && ./build.sh` |
| Start command | `cd apps/api && python -m workers.projection_worker` |
| Plan | Starter ($7/mo, 512MB) |

### Environment Variables

| Variable | Value |
|----------|-------|
| `PYTHON_VERSION` | `3.11.6` |
| `F1_PROJECTION_WORKER_ENABLED` | `true` |
| `DATABASE_URL` | *(pooler connection, port 6543)* |
| `LOG_LEVEL` | `INFO` |

### How to verify

Render logs should show `"Loaded 16 domain mappings"` on startup.

---

## SERVICE 5: Embedding Worker (Render — Background Worker)

**What it does:** Takes search text and creates vector embeddings using OpenAI. Powers semantic search ("find things similar to X").

| Setting | Value |
|---------|-------|
| Type | **Background Worker** |
| Name | `celeste-embedding-worker` |
| Build command | `chmod +x build.sh && ./build.sh` |
| Start command | `cd apps/api && python -m workers.embedding_worker_1536` |
| Plan | Starter ($7/mo, 512MB) |

### Environment Variables

| Variable | Value |
|----------|-------|
| `PYTHON_VERSION` | `3.11.6` |
| `DATABASE_URL` | *(pooler connection, port 6543)* |
| `OPENAI_API_KEY` | *(secret)* |
| `EMBED_MODEL` | `text-embedding-3-small` |
| `EMBED_DIMS` | `1536` |

### How to verify

Render logs should show `"coverage=100.0%"` after startup.

---

## SERVICE 6: Cache Listener (Render — Background Worker)

**What it does:** Listens for database changes and clears stale search results from Redis cache.

| Setting | Value |
|---------|-------|
| Type | **Background Worker** |
| Name | `celeste-cache-listener` |
| Build command | `chmod +x build.sh && ./build.sh` |
| Start command | `cd apps/api && python -m cache.invalidation_listener` |
| Plan | Starter ($7/mo, 256MB) |

### Environment Variables

| Variable | Value |
|----------|-------|
| `PYTHON_VERSION` | `3.11.6` |
| `READ_DB_DSN` | *(direct connection, port 5432 — NOT pooler)* |
| `REDIS_URL` | *(secret)* |

> **Important:** This service MUST use port 5432 (direct), not 6543 (pooler). PostgreSQL LISTEN/NOTIFY does not work through connection poolers.

### How to verify

Render logs should show:
- `"Redis connected: True"`
- `"Listening for f1_cache_invalidate events"`

---

## SERVICE 7: Extraction Worker (Render — Background Worker)

**What it does:** Downloads documents (PDF, DOCX, XLSX) from Supabase Storage and extracts text so documents become searchable.

| Setting | Value |
|---------|-------|
| Type | **Background Worker** |
| Name | `celeste-extraction-worker` |
| Build command | `chmod +x build.sh && ./build.sh` |
| Start command | `cd apps/api && python -m workers.extraction_worker` |
| Plan | Starter ($7/mo, 1024MB) |

### Environment Variables

| Variable | Value |
|----------|-------|
| `PYTHON_VERSION` | `3.11.6` |
| `DATABASE_URL` | *(pooler connection, port 6543)* |
| `SUPABASE_URL` | `https://vzsohavtuotocgrfkfyd.supabase.co` |
| `SUPABASE_SERVICE_KEY` | *(secret)* |

### How to verify

Render logs should show `"Extraction worker started"` and `"Connected to database"`.

---

## SERVICE 8: Nightly Feedback Loop (Render — Cron Job)

**What it does:** Runs once per day at 3 AM UTC. Learns what crew search for and click on, then teaches the search engine yacht-specific vocabulary.

| Setting | Value |
|---------|-------|
| Type | **Cron Job** |
| Name | `nightly-feedback-loop` |
| Schedule | `0 3 * * *` (3:00 AM UTC daily) |
| Build command | `cd apps/api && pip install psycopg2-binary` |
| Start command | `cd apps/api && python -m workers.nightly_feedback_loop` |
| Plan | Starter ($7/mo, 512MB) |

### Environment Variables

| Variable | Value |
|----------|-------|
| `PYTHON_VERSION` | `3.11.6` |
| `DATABASE_URL` | *(pooler connection, port 6543)* |
| `MIN_CLICKS` | `3` |
| `LOOKBACK_DAYS` | `30` |
| `BATCH_SIZE` | `100` |
| `LOG_LEVEL` | `INFO` |

### How to verify

After 3 AM run, check Render logs for `"Feedback loop complete"` message.

---

## SERVICE 9: Handover Export (Separate Repo)

**What it does:** Takes handover notes and uses GPT-4o-mini to create professional handover documents. This is a **separate Git repository**, not part of the main Cloud_PMS repo.

| Setting | Value |
|---------|-------|
| Type | **Web Service** |
| Name | `handover-export` |
| Git repo | **Separate** — `handover_export` repo |
| Local path | `/Users/celeste7/Documents/handover_export` |
| Port | 10000 (local Docker) / `$PORT` (Render) |
| Build command | `pip install -r requirements.txt` |
| Start command | `uvicorn app:app --host 0.0.0.0 --port $PORT` |
| Health check path | `/health` |
| Plan | Starter ($7/mo, 512MB) |

### Environment Variables

| Variable | Value |
|----------|-------|
| `OPENAI_API_KEY` | *(secret)* |
| `SUPABASE_URL` | `https://vzsohavtuotocgrfkfyd.supabase.co` |
| `SUPABASE_SERVICE_KEY` | *(secret)* |

### How to verify

```
curl http://localhost:10000/health
```
Should return: `{"status": "healthy", "service": "handover-export", "version": "2.0.0"}`

---

## Monthly Cost Summary (Render)

| Service | Type | Plan | Cost |
|---------|------|------|------|
| API | Web | Starter | $7 |
| Email Watcher | Worker | Starter | $7 |
| Projection Worker | Worker | Starter | $7 |
| Embedding Worker | Worker | Starter | $7 |
| Cache Listener | Worker | Starter | $7 |
| Extraction Worker | Worker | Starter | $7 |
| Nightly Feedback | Cron | Starter | $7 |
| Handover Export | Web | Starter | $7 |
| **Total** | | | **$56/mo** |

Vercel frontend: **free tier**.
Supabase: **separate billing**.

---

## Where to Find Secrets

All secret values (API keys, passwords, connection strings) are documented in:

```
/Users/celeste7/Documents/env vars/env vars.md
```

**Never commit this file to Git.**
