# CelesteOS Deployment Guide

Last updated: 25 March 2026

---

## Platforms

- Frontend (Next.js) = Vercel = app.celeste7.ai
- Backend API + Workers = Render = pipeline-core.int.celeste7.ai
- Database + Auth + Storage = Supabase = vzsohavtuotocgrfkfyd.supabase.co

## Custom Domains

- app.celeste7.ai = Vercel (frontend) — Cloudflare DNS
- pipeline-core.int.celeste7.ai = Render (API) — Cloudflare DNS
- celeste7.ai = Landing page — Cloudflare DNS

## Database Connections

TWO types. Wrong one = broken service.

- Direct (port 5432) = for LISTEN/NOTIFY, long connections = Cache Listener, API
- Pooler (port 6543) = for short queries = Projection, Embedding, Extraction, Nightly Feedback

```
DIRECT  = postgresql://postgres:{password}@db.vzsohavtuotocgrfkfyd.supabase.co:5432/postgres
POOLER  = postgresql://postgres.vzsohavtuotocgrfkfyd:{password}@aws-0-us-west-1.pooler.supabase.com:6543/postgres
```

---

## SERVICE 1: Frontend

- Platform = Vercel
- Repo = shortalex12333/Cloud_PMS
- Root directory = apps/web
- Build command = npm run build
- Install command = npm install
- Node version = 18.x
- Custom domain = app.celeste7.ai
- Auto-deploy = yes (on push to main)

### Env Vars

```
NEXT_PUBLIC_SUPABASE_URL=https://vzsohavtuotocgrfkfyd.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=<SECRET>
NEXT_PUBLIC_API_URL=https://pipeline-core.int.celeste7.ai
NEXT_PUBLIC_APP_URL=https://app.celeste7.ai
NEXT_PUBLIC_FRAGMENTED_ROUTES_ENABLED=true
```

### Verify

Open https://app.celeste7.ai — search bar loads = working.

---

## SERVICE 2: API

- Platform = Render
- Type = Web Service
- Name = celeste-pipeline-v1
- Region = Oregon
- Plan = Starter ($7/mo, 512MB)
- Repo = shortalex12333/Cloud_PMS
- Branch = main
- Root directory = (leave empty)
- Build command = chmod +x build.sh && ./build.sh
- Start command = cd apps/api && uvicorn pipeline_service:app --host 0.0.0.0 --port $PORT
- Health check path = /health
- Auto-deploy = yes
- Custom domain = pipeline-core.int.celeste7.ai
- Python version = 3.11.6

### Env Vars

```
PYTHON_VERSION=3.11.6
MASTER_SUPABASE_URL=https://qvzmkaamzaqxpzbewjxe.supabase.co
MASTER_SUPABASE_SERVICE_KEY=<SECRET>
MASTER_SUPABASE_JWT_SECRET=<SECRET>
yTEST_YACHT_001_SUPABASE_URL=https://vzsohavtuotocgrfkfyd.supabase.co
yTEST_YACHT_001_SUPABASE_SERVICE_KEY=<SECRET>
yTEST_YACHT_001_SUPABASE_ANON_KEY=<SECRET>
SUPABASE_URL=https://vzsohavtuotocgrfkfyd.supabase.co
SUPABASE_SERVICE_KEY=<SECRET>
TENANT_SUPABASE_ANON_KEY=<SECRET>
TENANT_SUPABASE_JWT_SECRET=<SECRET>
OPENAI_API_KEY=<SECRET>
REDIS_URL=<SECRET>
READ_DB_DSN=<SECRET — direct connection, port 5432>
DATABASE_URL=<SECRET — pooler connection, port 6543>
AZURE_READ_APP_ID=41f6dc82-8127-4330-97e0-c6b26e6aa967
AZURE_READ_CLIENT_SECRET=<SECRET>
AZURE_WRITE_APP_ID=f0b8944b-8127-4f0f-8ed5-5487462df50c
AZURE_WRITE_CLIENT_SECRET=<SECRET>
SHOPPING_LIST_LENS_V1_ENABLED=true
HANDOVER_EXPORT_SERVICE_URL=<URL of handover export service>
HANDOVER_USE_MICROSERVICE=true
```

### Verify

```
curl https://pipeline-core.int.celeste7.ai/health
```
Returns: `{"status": "healthy", "pipeline_ready": true}`

---

## SERVICE 3: Email Watcher

- Platform = Render
- Type = Background Worker
- Name = celeste-email-watcher
- Region = Oregon
- Plan = Starter ($7/mo, 512MB)
- Build command = cd apps/api && pip install -r requirements.txt
- Start command = cd apps/api && python -m workers.email_watcher_worker
- Auto-deploy = yes
- Python version = 3.11.6

### Env Vars

```
PYTHON_VERSION=3.11.6
EMAIL_WATCHER_ENABLED=true
EMAIL_WATCHER_POLL_INTERVAL=30
EMAIL_WATCHER_BATCH_SIZE=10
SUPABASE_URL=https://vzsohavtuotocgrfkfyd.supabase.co
SUPABASE_SERVICE_KEY=<SECRET>
AZURE_READ_CLIENT_SECRET=<SECRET>
```

### Verify

Check Render logs. Should show "Syncing watcher" every 15 mins and "errors=0".

---

## SERVICE 4: Projection Worker

- Platform = Render
- Type = Background Worker
- Name = celeste-projection-worker
- Plan = Starter ($7/mo, 512MB)
- Build command = chmod +x build.sh && ./build.sh
- Start command = cd apps/api && python -m workers.projection_worker

### Env Vars

```
PYTHON_VERSION=3.11.6
F1_PROJECTION_WORKER_ENABLED=true
DATABASE_URL=<SECRET — pooler, port 6543>
LOG_LEVEL=INFO
```

### Verify

Render logs show "Loaded 16 domain mappings" on startup.

---

## SERVICE 5: Embedding Worker

- Platform = Render
- Type = Background Worker
- Name = celeste-embedding-worker
- Plan = Starter ($7/mo, 512MB)
- Build command = chmod +x build.sh && ./build.sh
- Start command = cd apps/api && python -m workers.embedding_worker_1536

### Env Vars

```
PYTHON_VERSION=3.11.6
DATABASE_URL=<SECRET — pooler, port 6543>
OPENAI_API_KEY=<SECRET>
EMBED_MODEL=text-embedding-3-small
EMBED_DIMS=1536
```

### Verify

Render logs show "coverage=100.0%" after startup.

---

## SERVICE 6: Cache Listener

- Platform = Render
- Type = Background Worker
- Name = celeste-cache-listener
- Plan = Starter ($7/mo, 256MB)
- Build command = chmod +x build.sh && ./build.sh
- Start command = cd apps/api && python -m cache.invalidation_listener

### Env Vars

```
PYTHON_VERSION=3.11.6
READ_DB_DSN=<SECRET — DIRECT connection, port 5432, NOT pooler>
REDIS_URL=<SECRET>
```

MUST use port 5432. LISTEN/NOTIFY does not work through pooler.

### Verify

Render logs show "Redis connected: True" and "Listening for f1_cache_invalidate events".

---

## SERVICE 7: Extraction Worker

- Platform = Render
- Type = Background Worker
- Name = celeste-extraction-worker
- Plan = Starter ($7/mo, 1024MB)
- Build command = chmod +x build.sh && ./build.sh
- Start command = cd apps/api && python -m workers.extraction_worker

### Env Vars

```
PYTHON_VERSION=3.11.6
DATABASE_URL=<SECRET — pooler, port 6543>
SUPABASE_URL=https://vzsohavtuotocgrfkfyd.supabase.co
SUPABASE_SERVICE_KEY=<SECRET>
```

### Verify

Render logs show "Extraction worker started" and "Connected to database".

---

## SERVICE 8: Nightly Feedback Loop

- Platform = Render
- Type = Cron Job
- Name = nightly-feedback-loop
- Schedule = 0 3 * * * (3:00 AM UTC daily)
- Plan = Starter ($7/mo, 512MB)
- Build command = cd apps/api && pip install psycopg2-binary
- Start command = cd apps/api && python -m workers.nightly_feedback_loop

### Env Vars

```
PYTHON_VERSION=3.11.6
DATABASE_URL=<SECRET — pooler, port 6543>
MIN_CLICKS=3
LOOKBACK_DAYS=30
BATCH_SIZE=100
LOG_LEVEL=INFO
```

### Verify

After 3 AM run, Render logs show "Feedback loop complete".

---

## SERVICE 9: Handover Export

SEPARATE REPO. Not part of Cloud_PMS.

- Platform = Render (or Docker locally)
- Type = Web Service
- Name = handover-export
- Repo = separate — /Users/celeste7/Documents/handover_export
- Port = 10000 (local) / $PORT (Render)
- Build command = pip install -r requirements.txt
- Start command = uvicorn app:app --host 0.0.0.0 --port $PORT
- Health check path = /health
- Plan = Starter ($7/mo, 512MB)

### Env Vars

```
OPENAI_API_KEY=<SECRET>
SUPABASE_URL=https://vzsohavtuotocgrfkfyd.supabase.co
SUPABASE_SERVICE_KEY=<SECRET>
```

### Verify

```
curl http://localhost:10000/health
```
Returns: `{"status": "healthy", "service": "handover-export", "version": "2.0.0"}`

---

## Monthly Cost (Render)

- API = $7
- Email Watcher = $7
- Projection Worker = $7
- Embedding Worker = $7
- Cache Listener = $7
- Extraction Worker = $7
- Nightly Feedback = $7
- Handover Export = $7
- **Total = $56/mo**

Vercel = free tier. Supabase = separate billing.

---

## Where Secrets Live

```
/Users/celeste7/Documents/env vars/env vars.md
```

Never commit this file to Git.
