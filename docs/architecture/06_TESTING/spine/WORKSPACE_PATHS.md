# WORKSPACE PATHS - CelesteOS Autopilot Contract

**Generated:** 2026-01-13
**Purpose:** Authoritative paths for Claude B autonomous operation

---

## Repository Locations

```bash
[REPO_ROOT]=/Users/celeste7/Documents/Cloud_PMS
[FRONTEND_ROOT_DIR]=/Users/celeste7/Documents/Cloud_PMS/apps/web
[BACKEND_ROOT_DIR]=/Users/celeste7/Documents/Cloud_PMS/apps/api
[BACKEND_ENTRYPOINT]=api.pipeline_service:app
[DATABASE_MIGRATIONS_DIR]=/Users/celeste7/Documents/Cloud_PMS/database
[DOCS_V2_DIR]=/Users/celeste7/Desktop/Cloud_PMS_docs_v2
[SPINE_DIR]=/Users/celeste7/Desktop/Cloud_PMS_docs_v2/06_TESTING/spine
```

---

## Run Commands

### Frontend (Next.js)

```bash
cd /Users/celeste7/Documents/Cloud_PMS/apps/web
npm install        # First time only
npm run dev        # Development server → http://localhost:3000
npm run build      # Production build
npm run lint       # ESLint check
npm run typecheck  # TypeScript check
```

### Backend (FastAPI/Python)

```bash
cd /Users/celeste7/Documents/Cloud_PMS/apps/api
pip install -r requirements.txt  # First time only

# Local development
uvicorn api.pipeline_service:app --reload --port 8000

# Production (as run by Render)
uvicorn api.pipeline_service:app --host 0.0.0.0 --port $PORT
```

### Database Migrations

```bash
cd /Users/celeste7/Documents/Cloud_PMS/database

# Master migrations (run against qvzmkaamzaqxpzbewjxe.supabase.co)
ls master_migrations/

# Tenant migrations (run against vzsohavtuotocgrfkfyd.supabase.co)
ls tenant_migrations/  # TODO: verify exists
```

---

## Key Files

### Frontend

| File | Purpose |
|------|---------|
| `apps/web/src/contexts/AuthContext.tsx` | Auth state management |
| `apps/web/src/lib/supabaseClient.ts` | Supabase client init |
| `apps/web/src/lib/authHelpers.ts` | JWT/auth utilities |
| `apps/web/src/hooks/useCelesteSearch.ts` | Search API calls |
| `apps/web/next.config.js` | CSP headers, rewrites |
| `apps/web/.env.local` | Local env vars (not committed) |

### Backend

| File | Purpose |
|------|---------|
| `apps/api/pipeline_service.py` | Main FastAPI app (937 lines) |
| `apps/api/middleware/auth.py` | JWT validation + tenant routing |
| `apps/api/routes/p0_actions_routes.py` | P0 action endpoints |
| `apps/api/pipeline_v1.py` | Search pipeline logic |
| `apps/api/requirements.txt` | Python dependencies |

### Database

| File | Purpose |
|------|---------|
| `database/master_migrations/` | Master DB schema |
| `BACKEND_TENANT_ROUTING_SPEC.md` | Tenant routing spec |
| `COMPLETE_ACTION_EXECUTION_CATALOG.md` | 6584-line action spec |

---

## Production URLs

| Service | URL | Platform |
|---------|-----|----------|
| Frontend (prod) | https://app.celeste7.ai | Vercel |
| Frontend (auth) | https://auth.celeste7.ai | Vercel (legacy) |
| Backend API | https://pipeline-core.int.celeste7.ai | Render |
| Master Supabase | https://qvzmkaamzaqxpzbewjxe.supabase.co | Supabase |
| Tenant Supabase (TEST) | https://vzsohavtuotocgrfkfyd.supabase.co | Supabase |

---

## Git Branch Contract

```
main          → Production (deploys to Vercel + Render)
universal_v1  → Merged into main (legacy name)
```

**RULE:** All deploys from `main` branch only.

---

## Test Commands

```bash
# Backend unit tests
cd /Users/celeste7/Documents/Cloud_PMS/apps/api
pytest tests/

# E2E sandbox (if configured)
python e2e_sandbox_runner.py

# Frontend lint/typecheck
cd /Users/celeste7/Documents/Cloud_PMS/apps/web
npm run lint && npm run typecheck
```

---

## TODO (Verify These)

- [ ] Confirm `database/tenant_migrations/` directory exists
- [ ] Verify `apps/web/.env.local` template exists
- [ ] Check if `apps/api/tests/` has pytest fixtures

---

**Last Updated:** 2026-01-13
