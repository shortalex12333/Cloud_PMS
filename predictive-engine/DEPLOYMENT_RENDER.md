# Render.com Deployment Guide

**CelesteOS Predictive Maintenance Engine**

---

## Prerequisites

- ✅ Render.com account
- ✅ Supabase project configured: https://vzsohavtuotocgrfkfyd.supabase.co
- ✅ GitHub repository with this code

---

## Step 1: Run Database Migrations

**CRITICAL: Do this BEFORE deploying to Render.com**

1. Go to Supabase Dashboard: https://vzsohavtuotocgrfkfyd.supabase.co
2. Navigate to: **SQL Editor**
3. Open and execute: `migrations/001_create_predictive_tables.sql`

This creates:
- `predictive_state` table
- `predictive_insights` table
- Helper functions and RLS policies

**Verify Migration:**
```sql
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public'
AND table_name IN ('predictive_state', 'predictive_insights');
```

You should see both tables listed.

---

## Step 2: Deploy to Render.com

### Option A: Using render.yaml (Recommended)

1. **Connect GitHub Repository**
   - Go to Render.com Dashboard
   - Click "New +" → "Blueprint"
   - Connect your GitHub repository
   - Select repository: `Cloud_PMS`
   - Render will auto-detect `predictive-engine/render.yaml`

2. **Configure Environment Variables**

   Render will prompt for secrets. Set:

   **For both services (API + Worker):**
   - `SUPABASE_KEY`: `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ6c29oYXZ0dW90b2NncmZrZnlkIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MzU5Mjg3NSwiZXhwIjoyMDc5MTY4ODc1fQ.fC7eC_4xGnCHIebPzfaJ18pFMPKgImE7BuN0I3A-pSY`

3. **Deploy**
   - Click "Apply"
   - Render will create:
     - Web Service: `celeste-predictive-api`
     - Cron Job: `celeste-predictive-worker`

### Option B: Manual Setup

#### Deploy API Service

1. **New Web Service**
   - Dashboard → "New +" → "Web Service"
   - Connect GitHub repository
   - Root directory: `predictive-engine`
   - Runtime: Python 3
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `uvicorn main:app --host 0.0.0.0 --port $PORT`

2. **Environment Variables**
   ```
   SUPABASE_URL=https://vzsohavtuotocgrfkfyd.supabase.co
   SUPABASE_KEY=<service_role_key>
   LOG_LEVEL=INFO
   ENVIRONMENT=production
   PYTHON_VERSION=3.11.0
   ```

3. **Advanced Settings**
   - Health Check Path: `/health`
   - Plan: Starter ($7/month) or Free
   - Region: Oregon (or closest to you)

#### Deploy Worker Service

1. **New Cron Job**
   - Dashboard → "New +" → "Cron Job"
   - Connect same GitHub repository
   - Root directory: `predictive-engine`
   - Runtime: Python 3
   - Build Command: `pip install -r requirements.txt`
   - Command: `python worker.py run-all`
   - Schedule: `0 */6 * * *` (every 6 hours)

2. **Environment Variables** (same as API)
   ```
   SUPABASE_URL=https://vzsohavtuotocgrfkfyd.supabase.co
   SUPABASE_KEY=<service_role_key>
   LOG_LEVEL=INFO
   ENVIRONMENT=production
   PYTHON_VERSION=3.11.0
   ```

---

## Step 3: Verify Deployment

### Test API Service

Once deployed, Render will give you a URL like:
`https://celeste-predictive-api.onrender.com`

**Test endpoints:**

```bash
# Health check
curl https://celeste-predictive-api.onrender.com/health

# Root endpoint
curl https://celeste-predictive-api.onrender.com/

# Get risk states (requires yacht_id)
curl "https://celeste-predictive-api.onrender.com/v1/predictive/state?yacht_id=<your-yacht-uuid>"
```

Expected health check response:
```json
{
  "status": "ok",
  "service": "predictive-maintenance-engine",
  "version": "1.0.0"
}
```

### Verify Worker

1. Go to Render Dashboard → Cron Jobs
2. Click on `celeste-predictive-worker`
3. Check "Logs" tab
4. Manually trigger: Click "Trigger Run"
5. Watch logs for:
   ```
   Starting predictive maintenance worker for all yachts
   Found X active yachts to process
   Processing yacht <yacht-id>
   Computing risk scores for yacht <yacht-id>
   ...
   Predictive maintenance worker complete
   ```

---

## Step 4: Integration with CelesteOS

### Update API Gateway

In your main CelesteOS API gateway, add routes to proxy to this service:

```python
# Example: Route /v1/predictive/* to Render.com service
PREDICTIVE_ENGINE_URL = "https://celeste-predictive-api.onrender.com"

@app.get("/v1/predictive/{path:path}")
async def proxy_predictive(path: str, request: Request):
    url = f"{PREDICTIVE_ENGINE_URL}/v1/predictive/{path}"
    # Forward request with authentication headers
    headers = {
        "X-Yacht-Signature": request.headers.get("X-Yacht-Signature"),
        "Authorization": request.headers.get("Authorization")
    }
    response = await http_client.get(url, headers=headers)
    return response.json()
```

### Search Engine Integration

In your search engine (Task 6), when generating predictive cards:

```python
import httpx

async def get_predictive_card(equipment_id: str):
    url = f"https://celeste-predictive-api.onrender.com/v1/predictive/predictive-cards/{equipment_id}"
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers={
            "X-Yacht-Signature": yacht_signature,
            "Authorization": f"Bearer {jwt_token}"
        })
        return response.json()
```

---

## Step 5: Monitoring & Maintenance

### View Logs

**API Logs:**
- Render Dashboard → Web Services → `celeste-predictive-api` → Logs tab

**Worker Logs:**
- Render Dashboard → Cron Jobs → `celeste-predictive-worker` → Logs tab

### Monitor Performance

**Key Metrics to Watch:**
- API response times (<500ms for most endpoints)
- Worker execution time (should complete within 30 min for 50 yachts)
- Database connection errors
- Risk computation errors

### Update Deployment

**Automatic (recommended):**
- Push to GitHub branch
- Render auto-deploys on push

**Manual:**
- Render Dashboard → Service → "Manual Deploy" → "Deploy latest commit"

---

## Troubleshooting

### Issue: "Module not found" errors

**Solution:**
```bash
# Verify requirements.txt is in root of predictive-engine/
# Rebuild: Dashboard → Service → Manual Deploy → Clear build cache
```

### Issue: Database connection errors

**Solution:**
```bash
# Verify environment variables are set correctly
# Check Supabase URL is reachable:
curl https://vzsohavtuotocgrfkfyd.supabase.co/rest/v1/
```

### Issue: Worker not running

**Solution:**
```bash
# Check cron schedule syntax: 0 */6 * * *
# Manually trigger to test
# Check logs for errors
```

### Issue: "No active yachts found"

**Solution:**
```sql
-- In Supabase SQL Editor, verify yachts table has active records:
SELECT id, name, status FROM yachts WHERE status = 'active';

-- If no yachts exist, add test yacht:
INSERT INTO yachts (id, name, status) VALUES
  (uuid_generate_v4(), 'Test Yacht', 'active');
```

---

## Cost Estimates (Render.com)

### Starter Plan (Recommended)
- **API Service**: $7/month
- **Worker Cron Job**: $7/month
- **Total**: $14/month

### Free Tier (Development Only)
- **API Service**: Free (spins down after 15 min inactivity)
- **Worker Cron Job**: Not available on free tier
- **Limitation**: 750 hours/month, cold starts

### Production Recommendation
- **API**: Standard ($25/month) - No spin down, better performance
- **Worker**: Starter ($7/month)
- **Total**: $32/month

---

## Security Checklist

Before going live:

- [ ] Service role key is stored as secret (not visible in logs)
- [ ] HTTPS enforced (Render provides this automatically)
- [ ] RLS policies active in Supabase
- [ ] Authentication headers validated on all endpoints
- [ ] Rate limiting configured (if needed)
- [ ] Monitoring alerts set up

---

## Production Checklist

- [ ] Database migrations executed successfully
- [ ] API service deployed and health check passing
- [ ] Worker deployed and first run successful
- [ ] Environment variables configured correctly
- [ ] Integration with main API gateway complete
- [ ] Search engine integration tested
- [ ] Logs are clean (no errors)
- [ ] First risk computation completed for test yacht
- [ ] Insights generated successfully
- [ ] Monitoring dashboard configured

---

## Next Steps After Deployment

1. **Test with Real Data**
   - Create test work orders, faults, notes
   - Wait for worker to run (or trigger manually)
   - Verify risk scores appear in `predictive_state`
   - Check insights in `predictive_insights`

2. **Monitor Initial Performance**
   - Watch first few worker runs
   - Check database query performance
   - Verify no memory/timeout issues

3. **Integrate with Frontend**
   - Connect search engine to predictive cards endpoint
   - Display risk scores in equipment lists
   - Show insights in dashboard

4. **Enable Alerts** (optional)
   - Set up Render.com alerts for failures
   - Configure Sentry for error tracking
   - Set up uptime monitoring (e.g., UptimeRobot)

---

## Support

If deployment fails:
1. Check Render.com logs for error messages
2. Verify Supabase migrations ran successfully
3. Test database connection from local machine
4. Review this guide step-by-step

**All systems ready for production deployment! 🚀**
