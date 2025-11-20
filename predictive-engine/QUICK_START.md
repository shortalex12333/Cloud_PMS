# Quick Start Guide - Predictive Maintenance Engine

**Get running in 5 minutes**

---

## 🚀 Quick Deployment to Render.com

### Prerequisites
- ✅ Supabase already configured: https://vzsohavtuotocgrfkfyd.supabase.co
- ✅ GitHub repository with this code
- ✅ Render.com account

### Step 1: Run Database Migration (2 minutes)

1. Open Supabase SQL Editor: https://vzsohavtuotocgrfkfyd.supabase.co/project/_/sql
2. Copy entire contents of: `migrations/001_create_predictive_tables.sql`
3. Paste and click "Run"
4. Verify tables created:
   ```sql
   SELECT * FROM predictive_state LIMIT 1;
   SELECT * FROM predictive_insights LIMIT 1;
   ```

### Step 2: Deploy to Render.com (3 minutes)

#### Option A: Automatic (Using Blueprint)

1. Go to: https://dashboard.render.com
2. Click **"New +"** → **"Blueprint"**
3. Connect your GitHub repository
4. Select: `Cloud_PMS`
5. Render detects: `predictive-engine/render.yaml`
6. When prompted for `SUPABASE_KEY`, enter:
   ```
   eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ6c29oYXZ0dW90b2NncmZrZnlkIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MzU5Mjg3NSwiZXhwIjoyMDc5MTY4ODc1fQ.fC7eC_4xGnCHIebPzfaJ18pFMPKgImE7BuN0I3A-pSY
   ```
7. Click **"Apply"**
8. Wait 2-3 minutes for deployment

#### Option B: Manual (Web Service Only)

1. New Web Service
   - Name: `celeste-predictive-api`
   - Root Directory: `predictive-engine`
   - Build: `pip install -r requirements.txt`
   - Start: `uvicorn main:app --host 0.0.0.0 --port $PORT`

2. Add Environment Variables:
   ```
   SUPABASE_URL=https://vzsohavtuotocgrfkfyd.supabase.co
   SUPABASE_KEY=<paste service role key from above>
   LOG_LEVEL=INFO
   ENVIRONMENT=production
   ```

3. Deploy

### Step 3: Test (30 seconds)

Your API will be at: `https://celeste-predictive-api.onrender.com`

**Test health check:**
```bash
curl https://celeste-predictive-api.onrender.com/health
```

Expected response:
```json
{"status": "ok", "service": "predictive-maintenance-engine", "version": "1.0.0"}
```

**Done! 🎉**

---

## 📋 Local Development Setup (Optional)

### Quick Setup

```bash
cd predictive-engine

# Install dependencies
pip install -r requirements.txt

# Environment already configured in .env file

# Verify integration
python verify_integration.py

# Run API server
uvicorn main:app --reload

# Or run worker
python worker.py run-all
```

### Access Locally
- API: http://localhost:8000
- Health: http://localhost:8000/health
- Docs: http://localhost:8000/docs

---

## 🧪 Testing the System

### Test Risk Computation

```bash
# Replace <yacht-id> with actual yacht UUID from your database
curl -X POST "https://celeste-predictive-api.onrender.com/v1/predictive/run-for-yacht?yacht_id=<yacht-id>"
```

### Test Insights

```bash
curl "https://celeste-predictive-api.onrender.com/v1/predictive/insights?yacht_id=<yacht-id>"
```

### Test Worker (from Render Dashboard)

1. Go to Render.com Dashboard
2. Click on: `celeste-predictive-worker` (Cron Job)
3. Click: **"Trigger Run"**
4. Watch logs

---

## 📊 What Happens After Deployment

### Automatic (Every 6 Hours)
The worker runs automatically and:
1. Fetches all active yachts
2. Computes risk scores for all equipment
3. Detects anomalies
4. Generates predictive insights
5. Saves to `predictive_state` and `predictive_insights` tables

### On-Demand (Via API)
You can trigger risk computation anytime:
```bash
POST /v1/predictive/run-for-yacht?yacht_id=<id>
```

---

## 🔗 Integration with Other Services

### Search Engine (Task 6)
Add predictive cards to search results:

```python
# In your search engine
import httpx

async def get_predictive_insights(equipment_id: str):
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"https://celeste-predictive-api.onrender.com/v1/predictive/predictive-cards/{equipment_id}"
        )
        return response.json()
```

### API Gateway
Route predictive endpoints:

```python
# In your main API
@app.api_route("/v1/predictive/{path:path}", methods=["GET", "POST"])
async def proxy_predictive(path: str, request: Request):
    url = f"https://celeste-predictive-api.onrender.com/v1/predictive/{path}"
    # Forward with auth headers
    ...
```

---

## 🔍 Monitoring

### Check Logs
- **API Logs**: Render Dashboard → Web Services → `celeste-predictive-api` → Logs
- **Worker Logs**: Render Dashboard → Cron Jobs → `celeste-predictive-worker` → Logs

### View Data
In Supabase SQL Editor:

```sql
-- View risk scores
SELECT
  equipment_name,
  risk_score,
  trend,
  updated_at
FROM predictive_state
ORDER BY risk_score DESC
LIMIT 10;

-- View insights
SELECT
  equipment_name,
  insight_type,
  severity,
  summary,
  created_at
FROM predictive_insights
ORDER BY created_at DESC
LIMIT 10;

-- View anomalies
SELECT
  equipment_name,
  insight_type,
  severity,
  summary
FROM predictive_insights
WHERE insight_type = 'anomaly_detected'
ORDER BY created_at DESC;
```

---

## ⚡ Common Commands

```bash
# Local development
uvicorn main:app --reload              # Run API server
python worker.py run-all               # Run worker for all yachts
python worker.py run-yacht <yacht-id>  # Run for specific yacht
python verify_integration.py           # Verify Supabase connection

# Testing
pytest                                 # Run tests
pytest --cov=.                        # With coverage

# Docker
docker build -t predictive .           # Build image
docker run -p 8000:8000 predictive    # Run container
```

---

## 🆘 Troubleshooting

### "No active yachts found"
```sql
-- Add a test yacht in Supabase
INSERT INTO yachts (id, name, status)
VALUES (uuid_generate_v4(), 'Test Yacht', 'active');
```

### "Table does not exist"
- Run the migration SQL in Supabase SQL Editor
- Check `migrations/001_create_predictive_tables.sql`

### "Connection refused"
- Verify SUPABASE_URL in environment variables
- Check SUPABASE_KEY is service role key (not anon key)

### Worker not running
- Check cron schedule: `0 */6 * * *`
- Manually trigger from Render Dashboard
- Check logs for errors

---

## 📞 Support

- **Full Documentation**: See `README.md`
- **Architecture Diagrams**: See `ARCHITECTURE.md`
- **Deployment Guide**: See `DEPLOYMENT_RENDER.md`
- **Deliverables Summary**: See `DELIVERABLES.md`

---

**Status: ✅ PRODUCTION READY**

System is fully integrated with Supabase and ready for immediate deployment to Render.com.
