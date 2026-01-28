# Deployment Architecture

**Production deployment and infrastructure**

**Purpose:** Understand where and how the system is deployed
**Audience:** DevOps engineers, SREs, backend engineers
**Reading time:** 15 minutes

---

## 🎯 Production Stack Overview

```
User Browser
     ↓
Vercel CDN (Frontend)
     ↓
Render (Backend API)
     ↓
Supabase (PostgreSQL Database)
     ↓
OpenAI API (GPT-4o-mini)
```

---

## 🌐 Frontend Deployment (Vercel)

### Platform

**Service:** Vercel
**Framework:** Next.js 14 (App Router)
**Region:** Global (CDN)

### URLs

**Production:**
- Primary: `https://app.celeste7.ai`
- Vercel: `https://celeste-pms.vercel.app`

**Preview (per PR):**
- `https://celeste-pms-git-[branch]-[team].vercel.app`

**Development:**
- Local: `http://localhost:3000`

### Build Configuration

**File:** `apps/web/vercel.json`
```json
{
  "buildCommand": "npm run build",
  "devCommand": "npm run dev",
  "installCommand": "npm install",
  "framework": "nextjs",
  "outputDirectory": ".next"
}
```

**Environment Variables (Vercel):**
```bash
NEXT_PUBLIC_API_URL=https://pipeline-core.int.celeste7.ai
NEXT_PUBLIC_SUPABASE_URL=https://master.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJhbGc...
```

### Deployment Process

**Automatic (Git-based):**
```
1. Git push to main branch
   ↓
2. Vercel detects push via webhook
   ↓
3. Vercel runs build
   - npm install
   - npm run build (Next.js build)
   ↓
4. Build artifacts deployed to CDN
   ↓
5. DNS updated (zero-downtime)
   ↓
6. Production live at https://app.celeste7.ai
```

**Manual:**
```bash
# Deploy from CLI
cd apps/web
vercel --prod
```

### Build Time

**Average:** 2-3 minutes
**Includes:**
- npm install: ~30s
- Next.js build: ~90s
- CDN deployment: ~30s

### Rollback

**Instant rollback available:**
```bash
vercel rollback
```
or via Vercel dashboard

---

## ⚙️ Backend Deployment (Render)

### Platform

**Service:** Render
**Framework:** FastAPI + uvicorn
**Region:** US West (Oregon)

### URLs

**Production:**
- API: `https://pipeline-core.int.celeste7.ai`
- Docs: `https://pipeline-core.int.celeste7.ai/docs`
- Health: `https://pipeline-core.int.celeste7.ai/health`

**Development:**
- Local: `http://localhost:8000`

### Build Configuration

**File:** `apps/api/render.yaml`
```yaml
services:
  - type: web
    name: pipeline-core
    env: python
    region: oregon
    plan: starter
    buildCommand: "pip install -r requirements.txt"
    startCommand: "uvicorn pipeline_service:app --host 0.0.0.0 --port 8000"
    envVars:
      - key: PYTHON_VERSION
        value: 3.12.0
      - key: MASTER_SUPABASE_URL
        sync: false  # Manual secret
      - key: MASTER_SUPABASE_SERVICE_ROLE_KEY
        sync: false  # Manual secret
      - key: TENANT_SUPABASE_URL
        sync: false  # Manual secret
      - key: TENANT_SUPABASE_SERVICE_ROLE_KEY
        sync: false  # Manual secret
      - key: OPENAI_API_KEY
        sync: false  # Manual secret
```

### Environment Variables (Render)

**Set via Render dashboard (secrets):**
```bash
# Master DB (user auth)
MASTER_SUPABASE_URL=https://master-xyz.supabase.co
MASTER_SUPABASE_SERVICE_ROLE_KEY=eyJhbGc...

# Tenant DB (PMS data)
TENANT_SUPABASE_URL=https://tenant-xyz.supabase.co
TENANT_SUPABASE_SERVICE_ROLE_KEY=eyJhbGc...

# OpenAI
OPENAI_API_KEY=sk-...

# Optional
DEBUG=false
LOG_LEVEL=info
```

### Deployment Process

**Automatic (Git-based):**
```
1. Git push to main branch
   ↓
2. Render detects push via webhook
   ↓
3. Render builds Docker container
   - pip install -r requirements.txt
   ↓
4. Health check passes
   - GET /health returns 200
   ↓
5. New container deployed
   ↓
6. Old container drained (30s grace period)
   ↓
7. Production live
```

**Manual:**
```bash
# Trigger deploy via Render CLI
render deploy
```

### Build Time

**Average:** 3-5 minutes
**Includes:**
- Docker build: ~2 minutes
- pip install: ~1 minute
- Health check: ~10s
- Container swap: ~30s

### Scaling

**Current:**
- Instances: 1
- Memory: 512 MB
- CPU: 0.5 vCPU

**Auto-scaling (future):**
- Min instances: 1
- Max instances: 3
- CPU threshold: 80%

### Health Checks

**Endpoint:** `GET /health`
```python
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0"
    }
```

**Render checks:**
- Interval: 30 seconds
- Timeout: 5 seconds
- Failure threshold: 3 consecutive failures → restart container

---

## 🗄️ Database Deployment (Supabase)

### Platform

**Service:** Supabase (managed PostgreSQL)
**Version:** PostgreSQL 15
**Region:** US West (Oregon)

### Instances

**Master DB:**
- URL: `https://master-xyz.supabase.co`
- Purpose: User auth, yacht registry
- Size: 500 MB (shared tier)
- Tables: user_profiles, yachts, oauth_tokens

**Tenant DB (per yacht):**
- URL: `https://tenant-xyz.supabase.co`
- Purpose: PMS data for yachts
- Size: 2 GB (shared tier)
- Tables: pms_work_orders, pms_faults, pms_equipment, pms_parts, etc.

### Connection Pooling

**Supabase Pooler:**
```
Application
  ↓
Supabase Pooler (PgBouncer)
  ↓
PostgreSQL (max 100 connections)
```

**Connection string:**
```
postgresql://postgres.[project-ref]:[password]@aws-0-us-west-1.pooler.supabase.com:6543/postgres
```

### Backups

**Automatic:**
- Daily backups (retained 7 days)
- Point-in-time recovery (PITR) available
- Automated by Supabase

**Manual:**
```bash
# Export via pg_dump
pg_dump "postgresql://..." > backup-2026-01-22.sql

# Import
psql "postgresql://..." < backup-2026-01-22.sql
```

### Migrations

**Process:**
1. Write migration SQL
2. Test in development
3. Apply to production manually

**Example migration:**
```sql
-- Add new column to pms_work_orders
ALTER TABLE pms_work_orders
ADD COLUMN vendor_contact_hash TEXT;

-- Create index
CREATE INDEX idx_vendor_contact ON pms_work_orders(vendor_contact_hash);
```

**No automated migrations (yet)**
- Future: Use Supabase CLI or migration tool

---

## 🤖 AI Services (OpenAI)

### API

**Service:** OpenAI API
**Model:** gpt-4o-mini
**Region:** Global

### Endpoints Used

**Chat Completions:**
```
POST https://api.openai.com/v1/chat/completions
```

**Request:**
```json
{
  "model": "gpt-4o-mini",
  "messages": [
    {"role": "system", "content": "You detect microactions..."},
    {"role": "user", "content": "create a work order"}
  ],
  "temperature": 0.1
}
```

### Rate Limits

**Tier:** Pay-as-you-go
- 10,000 requests per minute
- 500,000 tokens per minute

**Current usage:**
- ~1,000 requests/day
- ~100,000 tokens/day
- Cost: ~$0.15/day ($4.50/month)

### Fallback

**If OpenAI API down:**
- Return empty actions array
- Show generic search results
- Log error to Sentry

**No caching (yet)**
- Future: Cache common queries

---

## 🔐 Secrets Management

### Vercel Secrets

**Stored in:** Vercel project settings
**Access:** Via Vercel dashboard or CLI

```bash
# Set secret via CLI
vercel env add NEXT_PUBLIC_API_URL production
```

### Render Secrets

**Stored in:** Render service environment variables
**Access:** Via Render dashboard

**Security:**
- Encrypted at rest
- Masked in logs
- Not included in Git

### Rotation Policy

**Service role keys:**
- Rotate quarterly
- Update in Vercel + Render + local .env.e2e

**OpenAI API key:**
- Rotate annually
- Monitor usage for anomalies

---

## 🌍 DNS & CDN

### DNS

**Domain:** `celeste7.ai`
**Provider:** Cloudflare
**Records:**
```
app.celeste7.ai     CNAME → cname.vercel-dns.com
pipeline-core.int.celeste7.ai  CNAME → [render-dns]
```

### CDN (Vercel Edge Network)

**Locations:** 100+ global edge locations
**Latency:** < 50ms for static assets

**Cache strategy:**
- Static assets (images, fonts): 1 year
- Next.js pages: Stale-while-revalidate
- API calls: No cache

---

## 📊 Monitoring & Logging

### Frontend (Vercel)

**Built-in Analytics:**
- Page views
- Core Web Vitals
- Error rate

**Access:** Vercel dashboard → Analytics

### Backend (Render)

**Built-in Logs:**
- stdout/stderr captured
- Searchable via dashboard
- Retained 7 days

**Access:** Render dashboard → Logs

**Metrics:**
- CPU usage
- Memory usage
- Request rate
- Error rate

### Future: Sentry Integration

**Error tracking:**
- Frontend: React error boundaries → Sentry
- Backend: FastAPI exception handler → Sentry

---

## 🚨 Incident Response

### Deployment Failure

**Symptoms:**
- Build fails
- Health check fails

**Response:**
1. Check build logs (Vercel/Render dashboard)
2. Identify error (syntax, missing env var, etc.)
3. Fix code or env var
4. Git push (auto-redeploy) or manual rollback

**Rollback:**
```bash
# Vercel
vercel rollback

# Render
# Via dashboard → Deployments → Previous deploy → Redeploy
```

### API Down

**Symptoms:**
- /health returns 500 or timeout
- Render shows "Unhealthy"

**Response:**
1. Check Render logs for errors
2. Check Supabase status (database connection)
3. Check OpenAI API status
4. Restart container if needed (Render dashboard)

**Auto-restart:**
- Render auto-restarts after 3 failed health checks

### Database Issues

**Symptoms:**
- Slow queries
- Connection timeouts
- Disk full

**Response:**
1. Check Supabase dashboard → Database metrics
2. Identify slow queries (pg_stat_statements)
3. Add indexes if needed
4. Upgrade tier if disk full

---

## 🔄 CI/CD Pipeline

### Current (Manual)

**Tests:**
- Run locally: `npx playwright test`
- No automated CI (yet)

**Deployment:**
- Git push → Auto-deploy (Vercel + Render)

### Future: GitHub Actions

**Planned workflow:**
```yaml
name: CI/CD
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Install dependencies
        run: npm install
      - name: Run tests
        run: npx playwright test
      - name: Upload coverage
        uses: codecov/codecov-action@v3

  deploy:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    steps:
      - name: Deploy to Vercel
        run: vercel --prod --token=${{ secrets.VERCEL_TOKEN }}
      - name: Deploy to Render
        run: curl -X POST ${{ secrets.RENDER_DEPLOY_HOOK }}
```

---

## 📈 Performance Targets

**Latency:**
- Frontend (Next.js): < 100ms TTFB
- Backend (/search): < 1s (includes GPT-4o-mini)
- Backend (/v1/actions/execute): < 500ms
- Database queries: < 100ms

**Availability:**
- Target: 99.9% uptime
- Downtime budget: 43 minutes/month

**Current (measured):**
- Frontend: 99.95% uptime
- Backend: 99.8% uptime
- Database: 99.99% uptime (Supabase SLA)

---

## 💰 Cost Breakdown

**Monthly costs (estimated):**

**Vercel (Frontend):**
- Plan: Pro ($20/month)
- Bandwidth: Included (100 GB)
- Total: **$20/month**

**Render (Backend):**
- Plan: Starter ($7/month)
- CPU: 0.5 vCPU
- Memory: 512 MB
- Total: **$7/month**

**Supabase (Database):**
- Master DB: Free tier
- Tenant DB: Pro ($25/month)
- Storage: Included (8 GB)
- Total: **$25/month**

**OpenAI (AI):**
- Model: gpt-4o-mini
- Usage: ~3M tokens/month
- Rate: $0.15 per 1M tokens
- Total: **$0.45/month**

**Grand Total: ~$52.45/month**

---

## 🔮 Future Infrastructure

### Planned Improvements

1. **Redis Cache Layer**
   - Service: Upstash Redis
   - Purpose: Cache equipment list, parts catalog
   - Cost: ~$5/month

2. **WebSocket Service**
   - Service: Supabase Realtime
   - Purpose: Real-time updates (work orders, faults)
   - Cost: Included in Supabase Pro

3. **Automated Testing (CI)**
   - Service: GitHub Actions
   - Purpose: Run Playwright tests on every PR
   - Cost: Free (public repo) or $4/month (private)

4. **Error Tracking**
   - Service: Sentry
   - Purpose: Frontend + backend error tracking
   - Cost: Free tier (5k events/month)

5. **APM (Application Performance Monitoring)**
   - Service: New Relic or DataDog
   - Purpose: Detailed performance insights
   - Cost: ~$15/month (Render integration)

**Total future cost: ~$77/month** (50% increase)

---

## 🎯 Scaling Strategy

### Current Capacity

**Frontend (Vercel):**
- Scales automatically (CDN)
- No limit on concurrent users

**Backend (Render):**
- 1 instance
- ~100 requests/second capacity
- ~10 concurrent users max

**Database (Supabase):**
- 100 connections max
- ~1000 queries/second capacity

### Scaling Triggers

**When to scale:**
- Backend CPU > 80% for 5 minutes
- Database connections > 80 (80% of max)
- Response time p95 > 1 second

**How to scale:**

**Backend (horizontal):**
- Increase instances: 1 → 2 → 3
- Add load balancer (Render Pro)

**Database (vertical):**
- Upgrade Supabase tier
- Add read replicas

**Frontend:**
- Already scales automatically (CDN)

---

## 🛡️ Security

### SSL/TLS

**All HTTPS:**
- Vercel: Auto SSL (Let's Encrypt)
- Render: Auto SSL (Let's Encrypt)
- Supabase: SSL enforced

**Certificates:**
- Auto-renewed
- No manual intervention needed

### Firewall

**Vercel:**
- DDoS protection (Cloudflare)
- Rate limiting (10 req/sec per IP)

**Render:**
- No public SSH access
- API only accessible via HTTPS
- Private services not exposed

**Supabase:**
- RLS enforced (yacht_id filtering)
- Service role key required
- No public PostgreSQL port

### API Keys

**Rotation schedule:**
- Supabase service role: Quarterly
- OpenAI API key: Annually
- JWT secret: Never (unless compromised)

---

## 📚 Related Documentation

- **ARCHITECTURE.md** - Overall system architecture
- **LOCAL_SETUP.md** - Local development environment
- **QUICK_REFERENCE.md** - Common deployment tasks

---

## 🎓 Quick Commands

**Deploy frontend:**
```bash
cd apps/web
vercel --prod
```

**Deploy backend:**
```bash
# Via Git
git push origin main

# Via Render CLI
render deploy
```

**Check production status:**
```bash
# Frontend
curl https://app.celeste7.ai

# Backend
curl https://pipeline-core.int.celeste7.ai/health

# Database
psql "postgresql://..." -c "SELECT 1"
```

**View logs:**
```bash
# Vercel
vercel logs

# Render
# Via dashboard: https://dashboard.render.com
```

---

**Document Version:** 1.0
**Last Updated:** 2026-01-22
**Maintained By:** DevOps Team
**Infrastructure Review:** Monthly
