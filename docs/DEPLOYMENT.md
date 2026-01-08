# CelesteOS Deployment Guide

Cloud-first AI-powered Yacht PMS deployment instructions for production.

## Architecture Overview

CelesteOS uses a monorepo structure with separate deployment paths:

```
/apps
  /web          → Vercel (Next.js frontend)
  /api          → Render (FastAPI backend)
  /worker       → Hetzner (future background workers)
/packages
  /shared       → Shared types/schemas
/docs           → Architecture documentation
```

---

## Frontend Deployment (Vercel)

**Service**: Next.js 14 Web Application
**Platform**: Vercel
**Source**: `/apps/web/`

### Prerequisites

- Vercel account with GitHub integration
- Environment variables configured in Vercel dashboard

### Environment Variables

Required in Vercel dashboard (`Settings → Environment Variables`):

```bash
# Supabase Configuration
NEXT_PUBLIC_SUPABASE_URL=https://vzsohavtuotocgrfkfyd.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

# API Configuration
NEXT_PUBLIC_API_BASE_URL=https://api.celeste7.ai
NEXT_PUBLIC_WEBHOOK_URL=https://api.celeste7.ai/webhook/search
```

### Deployment Steps

1. **Connect GitHub Repository**
   - Link repository: `https://github.com/shortalex12333/Cloud_PMS`
   - Select branch: `universal_v1` (or `main` after merge)

2. **Configure Build Settings**
   ```
   Root Directory: apps/web
   Build Command: npm run build
   Output Directory: .next
   Install Command: npm install
   ```

3. **Deploy**
   - Vercel will auto-deploy on push to branch
   - Monitor build at `https://vercel.com/dashboard`

### Vercel Configuration File

The frontend includes `vercel.json` with:
- API routes configuration
- Rewrites for /api/* paths
- Environment handling

### Post-Deployment Verification

1. Visit deployed URL: `https://celeste7.vercel.app` (or custom domain)
2. Test search functionality: Search bar → Webhook → Pipeline
3. Verify Supabase connection: Login/Authentication
4. Check console for errors

---

## Backend Deployment (Render)

**Service**: FastAPI Pipeline Service
**Platform**: Render
**Source**: `/apps/api/`

### Prerequisites

- Render account with GitHub integration
- Python 3.11+ runtime
- Environment variables configured

### Environment Variables

Required in Render dashboard (`Environment → Environment Variables`):

```bash
# Supabase Credentials
SUPABASE_URL=https://vzsohavtuotocgrfkfyd.supabase.co
SUPABASE_SERVICE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

# OpenAI API
OPENAI_API_KEY=sk-proj-...

# Database Configuration
DB_HOST=aws-0-us-west-1.pooler.supabase.com
DB_PORT=6543
DB_NAME=postgres
DB_USER=postgres.vzsohavtuotocgrfkfyd
DB_PASSWORD=<your-db-password>

# Optional: Logging
LOG_LEVEL=INFO
```

### Deployment Steps

1. **Create Render Web Service**
   - New → Web Service
   - Connect repository: `https://github.com/shortalex12333/Cloud_PMS`
   - Branch: `universal_v1`

2. **Configure Service**
   ```
   Name: celeste-microactions
   Root Directory: apps/api
   Runtime: Python 3
   Build Command: pip install -r requirements.txt
   Start Command: uvicorn pipeline_service:app --host 0.0.0.0 --port $PORT
   ```

3. **Health Check**
   ```
   Health Check Path: /health
   ```

4. **Deploy**
   - Click "Create Web Service"
   - Monitor deployment logs

### Current Production Endpoint

```
https://celeste-microactions.onrender.com
```

**Key Routes**:
- `POST /search` - Main search endpoint (used by frontend)
- `GET /health` - Health check
- `GET /docs` - FastAPI auto-generated docs

### Webhook Integration

The search bar sends queries directly to:
```
https://api.celeste7.ai/webhook/search
```

This routes to the `/search` endpoint on Render backend.

**Note**: We are moving away from n8n. All queries now go directly from the search bar to the pipeline service.

### Post-Deployment Verification

1. Health check: `curl https://celeste-microactions.onrender.com/health`
2. Test search:
   ```bash
   curl -X POST https://celeste-microactions.onrender.com/search \
     -H "Content-Type: application/json" \
     -d '{"query": "show me all faults"}'
   ```
3. Verify logs in Render dashboard
4. Check database connectivity

---

## Worker Deployment (Hetzner) - Future

**Service**: Background task workers
**Platform**: Hetzner Cloud
**Source**: `/apps/worker/` (placeholder)

This is a placeholder for future background processing tasks:
- Document ingestion
- PDF processing
- Scheduled reports
- Vector index updates

---

## Local Development

### Prerequisites

```bash
# Node.js 18+
node --version

# Python 3.11+
python3 --version

# Dependencies
make install
```

### Run Development Servers

**Frontend** (http://localhost:3000):
```bash
make dev-web
```

**Backend** (http://localhost:8000):
```bash
make dev-api
```

**Both** (requires separate terminals):
```bash
# Terminal 1
make dev-web

# Terminal 2
make dev-api
```

### Environment Files

**Frontend** (`apps/web/.env.local`):
```bash
NEXT_PUBLIC_SUPABASE_URL=https://vzsohavtuotocgrfkfyd.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJ...
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

**Backend** (`apps/api/.env`):
```bash
SUPABASE_URL=https://vzsohavtuotocgrfkfyd.supabase.co
SUPABASE_SERVICE_KEY=eyJ...
OPENAI_API_KEY=sk-proj-...
```

---

## Database Migrations

Database schema is managed via Supabase migrations in `/database/migrations/`.

### Apply Migrations

1. Navigate to Supabase Dashboard → SQL Editor
2. Run migration files in order:
   - `01_core_tables_v2_secure.sql`
   - `02_auth_sync_trigger.sql`

Or use the complete setup:
```bash
# Run in Supabase SQL Editor
database/setup_complete_FIXED.sql
```

See `/database/README.md` for detailed instructions.

---

## Deployment Checklist

Before deploying to production:

- [ ] Frontend builds successfully (`npm run build` in `apps/web/`)
- [ ] Backend starts successfully (`uvicorn pipeline_service:app` in `apps/api/`)
- [ ] All environment variables configured
- [ ] Database migrations applied
- [ ] Health check endpoint returns 200
- [ ] Search endpoint accepts queries
- [ ] Frontend → Backend → Database flow verified
- [ ] CORS configured for production domains
- [ ] Secrets rotated if needed
- [ ] Monitoring/logging configured

---

## Troubleshooting

### Frontend Issues

**Build fails with module errors**:
```bash
cd apps/web
rm -rf node_modules .next
npm install
npm run build
```

**Environment variables not loading**:
- Check Vercel dashboard → Settings → Environment Variables
- Ensure variables start with `NEXT_PUBLIC_` for client-side access
- Redeploy after adding variables

### Backend Issues

**Import errors after restructure**:
```bash
cd apps/api
python3 -c "from pipeline_service import app"
```

**Database connection fails**:
- Verify `SUPABASE_URL` and `SUPABASE_SERVICE_KEY` in environment
- Check database credentials in Supabase dashboard
- Test connection: `curl https://vzsohavtuotocgrfkfyd.supabase.co/rest/v1/`

**Webhook not reaching backend**:
- Verify `NEXT_PUBLIC_WEBHOOK_URL` points to correct endpoint
- Check CORS settings in `pipeline_service.py`
- Inspect browser network tab for 404/CORS errors

---

## Production URLs

| Service | URL | Description |
|---------|-----|-------------|
| Frontend | https://celeste7.vercel.app | Next.js web app |
| API | https://api.celeste7.ai | FastAPI backend |
| Webhook | https://api.celeste7.ai/webhook/search | Search endpoint |
| Database | vzsohavtuotocgrfkfyd.supabase.co | Supabase Postgres |
| Docs | https://celeste-microactions.onrender.com/docs | API documentation |

---

## Support

For deployment issues:
- Check logs in Vercel/Render dashboards
- Review `/docs/ARCHITECTURE.md` for system overview
- Verify environment variables match `.env.example` files
