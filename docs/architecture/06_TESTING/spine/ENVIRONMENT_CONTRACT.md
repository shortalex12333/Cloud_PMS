# ENVIRONMENT_CONTRACT - Required Environment Variables

**Generated:** 2026-01-13
**Purpose:** Authoritative list of env vars per service

---

## Vercel (Frontend) - app.celeste7.ai

### Required Variables

| Variable | Purpose | Breaks If Missing |
|----------|---------|-------------------|
| `NEXT_PUBLIC_SUPABASE_URL` | Master Supabase URL | Login fails, no auth |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Supabase anon key | Login fails |
| `NEXT_PUBLIC_API_URL` | Backend API URL | All API calls fail |

### Expected Values (Production)

```bash
NEXT_PUBLIC_SUPABASE_URL=https://qvzmkaamzaqxpzbewjxe.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InF2em1rYWFtemFxeHB6YmV3anhlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjM5NzkwNDYsImV4cCI6MjA3OTU1NTA0Nn0.xxx
NEXT_PUBLIC_API_URL=https://pipeline-core.int.celeste7.ai
```

### Validation (Runtime)

```typescript
// apps/web/src/lib/supabaseClient.ts
const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
const supabaseKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

if (!supabaseUrl || !supabaseKey) {
  console.error('[Supabase] Missing NEXT_PUBLIC_SUPABASE_URL or NEXT_PUBLIC_SUPABASE_ANON_KEY');
}

// Browser console should show:
// [Supabase] Client initialized: https://qvzmk... (first 30 chars)
```

### CSP Headers Required

```javascript
// next.config.js
const ContentSecurityPolicy = `
  default-src 'self';
  connect-src 'self'
    https://qvzmkaamzaqxpzbewjxe.supabase.co
    https://vzsohavtuotocgrfkfyd.supabase.co
    https://pipeline-core.int.celeste7.ai
    wss://*.supabase.co;
`;
```

---

## Render (Backend) - pipeline-core.int.celeste7.ai

### Required Variables

| Variable | Purpose | Breaks If Missing |
|----------|---------|-------------------|
| `MASTER_SUPABASE_JWT_SECRET` | JWT verification | All auth fails (401) |
| `MASTER_SUPABASE_SERVICE_KEY` | MASTER DB access | Tenant lookup fails |
| `OPENAI_API_KEY` | Embeddings | Search quality degraded |
| `yTEST_YACHT_001_SUPABASE_URL` | Tenant DB URL | Tenant routing fails |
| `yTEST_YACHT_001_SUPABASE_SERVICE_KEY` | Tenant DB access | Queries fail |

### Optional Variables

| Variable | Purpose | Default |
|----------|---------|---------|
| `MASTER_SUPABASE_URL` | Master DB URL | `https://qvzmkaamzaqxpzbewjxe.supabase.co` |
| `SUPABASE_URL` | Legacy fallback | `https://vzsohavtuotocgrfkfyd.supabase.co` |
| `SUPABASE_SERVICE_KEY` | Legacy fallback | None |
| `ALLOWED_ORIGINS` | CORS origins | Default list |
| `ENVIRONMENT` | Deployment env | `development` |

### Expected Values (Production)

```bash
# Master DB (control plane)
MASTER_SUPABASE_URL=https://qvzmkaamzaqxpzbewjxe.supabase.co
MASTER_SUPABASE_JWT_SECRET=wXka4UZu4tZc8Sx/HsoMBXu/L5avLHl+xoiWAH9lBbxJdbztPhYVc+stfrJOS/mlqF3U37HUkrkAMOhkpwjRsw==
MASTER_SUPABASE_SERVICE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InF2em1rYWFtemFxeHB6YmV3anhlIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2Mzk3OTA0NiwiZXhwIjoyMDc5NTU1MDQ2fQ.xxx

# Tenant DB (data plane)
yTEST_YACHT_001_SUPABASE_URL=https://vzsohavtuotocgrfkfyd.supabase.co
yTEST_YACHT_001_SUPABASE_SERVICE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.xxx

# Other
OPENAI_API_KEY=sk-...
ENVIRONMENT=production
ALLOWED_ORIGINS=https://auth.celeste7.ai,https://app.celeste7.ai,http://localhost:3000
```

### Validation (Startup Logs)

```python
# apps/api/middleware/auth.py
if not MASTER_SUPABASE_JWT_SECRET and not SUPABASE_JWT_SECRET:
    logger.error('MASTER_SUPABASE_JWT_SECRET environment variable not set')

# apps/api/pipeline_service.py
logger.info(f"✅ [Pipeline] CORS ALLOWED_ORIGINS (normalized): {ALLOWED_ORIGINS}")
```

**Expected Render logs on startup:**
```
✅ [Pipeline] CORS ALLOWED_ORIGINS (normalized): ['https://auth.celeste7.ai', 'https://app.celeste7.ai', ...]
✅ [Pipeline] Rate limiting enabled
[Auth] MASTER DB client created: https://qvzmkaamzaqxpzbewjxe...
```

---

## Adding New Tenant

To add a new yacht (e.g., YACHT_002):

### 1. Create Supabase Project

Create new project in Supabase, get:
- Project URL: `https://newproject.supabase.co`
- Service Key: `eyJ...`

### 2. Add Fleet Registry Entry (MASTER DB)

```sql
INSERT INTO fleet_registry (yacht_id, yacht_name, tenant_key_alias, active)
VALUES ('YACHT_002', 'M/Y New Yacht', 'yYACHT_002', true);
```

### 3. Add Render Environment Variables

```bash
yYACHT_002_SUPABASE_URL=https://newproject.supabase.co
yYACHT_002_SUPABASE_SERVICE_KEY=eyJ...
```

### 4. Deploy Render (picks up new env vars)

```bash
# Render auto-deploys on push, or manually trigger
```

---

## Debugging Missing Env Vars

### Frontend (Browser Console)

```javascript
// Check Supabase URL loaded
console.log(process.env.NEXT_PUBLIC_SUPABASE_URL);
// Expected: https://qvzmkaamzaqxpzbewjxe.supabase.co

// Check API URL loaded
console.log(process.env.NEXT_PUBLIC_API_URL);
// Expected: https://pipeline-core.int.celeste7.ai
```

### Backend (Render Logs)

```bash
# Check for startup errors
# Render Dashboard → Service → Logs

# Look for:
# - "MASTER_SUPABASE_JWT_SECRET environment variable not set"
# - "Missing credentials for tenant yTEST_YACHT_001"
```

### Verify via API

```bash
# Health check
curl https://pipeline-core.int.celeste7.ai/health

# Version check (shows environment)
curl https://pipeline-core.int.celeste7.ai/version
# Expected: {"environment": "production", ...}
```

---

## Environment-Specific Notes

### Development (localhost)

```bash
# Frontend (.env.local)
NEXT_PUBLIC_SUPABASE_URL=https://qvzmkaamzaqxpzbewjxe.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=...
NEXT_PUBLIC_API_URL=http://localhost:8000

# Backend (terminal or .env)
export MASTER_SUPABASE_JWT_SECRET=...
export MASTER_SUPABASE_SERVICE_KEY=...
export yTEST_YACHT_001_SUPABASE_URL=...
export yTEST_YACHT_001_SUPABASE_SERVICE_KEY=...
```

### Production (Vercel + Render)

All env vars set via dashboards:
- Vercel: Project Settings → Environment Variables
- Render: Service → Environment

---

**Last Updated:** 2026-01-13
