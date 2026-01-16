# Secrets & Access Credentials

> ⚠️ **DO NOT COMMIT THIS FILE TO GIT** - Add to .gitignore
>
> This file contains all credentials needed to work on the Outlook integration.

---

## PRODUCTION URLS

| Service | URL | Purpose |
|---------|-----|---------|
| Frontend | https://app.celeste7.ai | Vercel - User-facing app |
| Backend | https://pipeline-core.int.celeste7.ai | Render - API server |
| Database | https://vzsohavtuotocgrfkfyd.supabase.co | Supabase - PostgreSQL |

---

## TEST USER CREDENTIALS

```
Email:     x@alex-short.com
Password:  Password2!
Yacht ID:  85fe1119-b04c-41ac-80f1-829d23322598
```

---

## RENDER (Backend Hosting)

**Dashboard:** https://dashboard.render.com
**Service Name:** pipeline-core

### Environment Variables (set in Render dashboard)

```bash
# Azure OAuth - READ App (Mail.Read scope)
AZURE_READ_APP_ID=41f6dc82-8127-4330-97e0-c6b26e6aa967
AZURE_READ_CLIENT_SECRET=[REDACTED - stored in Render env vars]

# Azure OAuth - WRITE App (Mail.Send scope)
AZURE_WRITE_APP_ID=f0b8944b-8127-4f0f-8ed5-5487462df50c
AZURE_WRITE_CLIENT_SECRET=[REDACTED - stored in Render env vars]

# Supabase (per-yacht credentials)
yTEST_YACHT_001_SUPABASE_URL=https://vzsohavtuotocgrfkfyd.supabase.co
yTEST_YACHT_001_SUPABASE_SERVICE_KEY=[REDACTED - see Supabase dashboard]

# Default yacht for lookups
DEFAULT_YACHT_CODE=yTEST_YACHT_001
```

### How to View Logs
1. Go to https://dashboard.render.com
2. Click on "pipeline-core" service
3. Click "Logs" tab
4. Filter by `[Auth]` for OAuth-related logs

### How to Add/Edit Env Vars
1. Go to https://dashboard.render.com
2. Click on "pipeline-core" service
3. Click "Environment" tab
4. Add/edit variables
5. Click "Save Changes" (triggers redeploy)

---

## VERCEL (Frontend Hosting)

**Dashboard:** https://vercel.com/dashboard
**Project:** CelesteOS / app.celeste7.ai

### Environment Variables (set in Vercel dashboard)

```bash
NEXT_PUBLIC_API_URL=https://pipeline-core.int.celeste7.ai
NEXT_PUBLIC_APP_URL=https://app.celeste7.ai
NEXT_PUBLIC_SUPABASE_URL=https://vzsohavtuotocgrfkfyd.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=[REDACTED - see Supabase dashboard or GitHub secret MASTER_SUPABASE_ANON_KEY]
```

---

## SUPABASE (Database)

**Dashboard:** https://supabase.com/dashboard/project/vzsohavtuotocgrfkfyd

### Credentials

```bash
# Project URL
SUPABASE_URL=https://vzsohavtuotocgrfkfyd.supabase.co

# Anonymous Key (safe for frontend)
SUPABASE_ANON_KEY=[REDACTED - see Supabase dashboard → Settings → API → anon key]

# Service Key (BACKEND ONLY - bypasses RLS)
SUPABASE_SERVICE_KEY=[REDACTED - see Supabase dashboard → Settings → API → service_role key]
```

### Key Tables for OAuth

```sql
-- Token storage
SELECT * FROM auth_microsoft_tokens;

-- User's yacht assignment
SELECT * FROM auth_users_profiles WHERE user_id = '85fe1119-b04c-41ac-80f1-829d23322598';

-- Fallback yacht assignment
SELECT * FROM auth_users_yacht WHERE user_id = '85fe1119-b04c-41ac-80f1-829d23322598';

-- Email sync status
SELECT * FROM email_watchers;
```

---

## AZURE (Microsoft OAuth Apps)

**Portal:** https://portal.azure.com

### READ App (Mail.Read)

```
App Name:         CelesteOS Email Read
Application ID:   41f6dc82-8127-4330-97e0-c6b26e6aa967
Client Secret:    [REDACTED - see Azure Portal or Render env var AZURE_READ_CLIENT_SECRET]

Redirect URIs:
- https://app.celeste7.ai/api/integrations/outlook/callback

API Permissions:
- openid
- profile
- email
- offline_access
- Mail.Read
```

### WRITE App (Mail.Send)

```
App Name:         CelesteOS Email Send
Application ID:   f0b8944b-8127-4f0f-8ed5-5487462df50c
Client Secret:    [REDACTED - see Azure Portal or Render env var AZURE_WRITE_CLIENT_SECRET]

Redirect URIs:
- https://app.celeste7.ai/api/integrations/outlook/write

API Permissions:
- openid
- profile
- email
- offline_access
- Mail.Send
```

---

## GITHUB

**Repo:** https://github.com/shortalex12333/Cloud_PMS

### Branches

| Branch | Purpose | Status |
|--------|---------|--------|
| `main` | Production | ✅ OAuth commits pushed here |
| `claude/phase-11-visibility-matrix` | Current working branch | Has untracked files |

### Recent OAuth Commits (on main)

```
4c03647 fix: Add error handling for database lookup in OAuth token exchange
271a51b fix(oauth): Add error detail to unexpected error redirect
97dfbc5 fix(oauth): Read Azure env vars at request time, not module load
41e6fd6 fix(oauth): Fix state format mismatch between Vercel and Render
d85e966 feat(oauth): Route token exchange through Render backend (Option B)
```

---

## LOCAL DOCKER TESTING

### Setup

```bash
cd /Users/celeste7/Documents/Cloud_PMS

# Create .env from template (already exists)
cp .env.docker .env
# Edit .env with secrets above

# Run API locally
docker-compose up api

# API available at http://localhost:8000
```

### Test Commands

```bash
# Test local Docker
curl -X POST "http://localhost:8000/auth/outlook/exchange" \
  -H "Content-Type: application/json" \
  -d '{"code":"test","state":"user:read:123","redirect_uri":"https://app.celeste7.ai/api/integrations/outlook/callback"}'

# Test production Render
curl -X POST "https://pipeline-core.int.celeste7.ai/auth/outlook/exchange" \
  -H "Content-Type: application/json" \
  -d '{"code":"test","state":"user:read:123","redirect_uri":"https://app.celeste7.ai/api/integrations/outlook/callback"}'
```

---

## DEPLOYMENT

### Auto-Deploy on Push

| Service | Trigger | Deploy Time |
|---------|---------|-------------|
| Vercel | Push to `main` | ~1-2 minutes |
| Render | Push to `main` | ~2-5 minutes |

### Manual Deploy

**Vercel:** Go to dashboard → Deployments → Redeploy

**Render:** Go to dashboard → Manual Deploy → Deploy latest commit

---

## QUICK REFERENCE

```bash
# Check what's deployed
curl https://pipeline-core.int.celeste7.ai/health

# Test OAuth endpoint
curl -X POST "https://pipeline-core.int.celeste7.ai/auth/outlook/exchange" \
  -H "Content-Type: application/json" \
  -d '{"code":"fake","state":"test:read:123","redirect_uri":"https://app.celeste7.ai/api/integrations/outlook/callback"}'

# Expected response for fake code:
# {"success":false,"error":"AADSTS...","error_code":"invalid_grant"}
```
