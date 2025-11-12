# Deployment Guide

## Local Testing

1. **Create virtual environment:**
```bash
python3 -m venv venv
source venv/bin/activate
```

2. **Install dependencies:**
```bash
pip install -r requirements.txt
```

3. **Set environment variables:**
```bash
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY
```

4. **Run locally:**
```bash
export OPENAI_API_KEY="sk-proj-..."
export PORT=5400
python api/app.py
```

5. **Test:**
```bash
curl -X POST http://localhost:5400/extract \
  -H "Content-Type: application/json" \
  -d '{"text": "CAT 3516C main engine overheating at 95°C"}'

# Expected response:
# {"entities":{"equipment":["main engine"],"model":["CAT 3516C"],"org":["Caterpillar"],"measurement":["95 °C"],"symptom":["overheating"]}}
```

## Render.com Deployment

### Option 1: Blueprint (render.yaml)

1. **Push to GitHub:**
```bash
git add .
git commit -m "Initial cloud entity extraction service"
git remote add origin git@github.com:YOUR_USERNAME/celesteos-entity-extraction.git
git push -u origin main
```

2. **Connect to Render.com:**
   - Go to https://dashboard.render.com
   - Click "New" → "Blueprint"
   - Connect your GitHub repo
   - Render will auto-detect `render.yaml`

3. **Set environment variables:**
   - In Render dashboard, go to your service
   - Environment → Add Secret File or Variable
   - Add `OPENAI_API_KEY` with your OpenAI API key

4. **Deploy:**
   - Render will auto-deploy on git push
   - Service URL: https://celesteos-entity-extraction.onrender.com

### Option 2: Manual Setup

1. **Create new Web Service:**
   - Go to https://dashboard.render.com
   - Click "New" → "Web Service"
   - Connect GitHub repo or use Docker

2. **Configure:**
   - **Name:** celesteos-entity-extraction
   - **Region:** Oregon (US West)
   - **Branch:** main
   - **Runtime:** Python 3
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn --workers 2 --threads 4 --timeout 120 --bind 0.0.0.0:$PORT api.app:app`
   - **Plan:** Starter ($7/month)

3. **Environment Variables:**
   - `OPENAI_API_KEY`: Your OpenAI API key
   - `MAX_BODY_KB`: 64
   - `PYTHON_VERSION`: 3.11.0

4. **Health Check:**
   - Path: `/health`
   - Enabled

5. **Deploy:**
   - Click "Create Web Service"
   - Wait 5-10 minutes for first deploy

### Testing Production

```bash
# Get your Render URL
RENDER_URL="https://celesteos-entity-extraction.onrender.com"

# Test extraction
curl -X POST $RENDER_URL/extract \
  -H "Content-Type: application/json" \
  -d '{"text": "Yanmar 3JH5E engine maintenance"}'

# Check health
curl $RENDER_URL/health

# Check metrics
curl $RENDER_URL/metrics
```

## Monitoring

### Health Endpoint

```bash
curl https://your-service.onrender.com/health
```

Response:
```json
{
  "ok": true,
  "uptime_s": 3600,
  "requests": 1523,
  "errors": 2,
  "ai_rate": 0.18,
  "p95_ms": 45,
  "components": {
    "cleaner": "ok",
    "regex_extractor": "ok",
    "controller": "ok",
    "ai_extractor": "ok",
    "merger": "ok"
  }
}
```

### Metrics Endpoint

```bash
curl https://your-service.onrender.com/metrics
```

Prometheus-compatible metrics for monitoring.

## Cost Estimation

### Render.com
- **Starter Plan:** $7/month
  - 512MB RAM
  - Always on (no sleep)
  - Custom domains
  - Auto-deploy on git push

### OpenAI API
Assuming 2000 queries/month, 18% AI invocation rate:
- AI queries: 360/month
- Cost per query: $0.024 (GPT-4 Turbo, ~600 tokens)
- **Total:** ~$9/month

### Total Monthly Cost
**$16-17/month** for 2000 queries

## Scaling

### Increase Render Resources
- **Standard Plan** ($25/month): 2GB RAM, better performance
- **Pro Plan** ($85/month): 4GB RAM, autoscaling

### Optimize OpenAI Costs
- Current: GPT-4 Turbo ($0.01/$0.03 per 1K tokens)
- Alternative: GPT-3.5 Turbo ($0.0005/$0.0015 per 1K tokens) - 20x cheaper
- Trade-off: Slightly lower accuracy for complex queries

### Caching
Add Redis for entity extraction caching:
- Cache entities for 30 minutes
- Reduce duplicate API calls
- Upstash Redis free tier: 10K requests/day

## Troubleshooting

### Service won't start
- Check logs in Render dashboard
- Verify `OPENAI_API_KEY` is set
- Ensure spaCy model installed (auto-installed from requirements.txt)

### High latency
- Check OpenAI API status
- Upgrade Render plan for more RAM/CPU
- Add caching layer

### High costs
- Reduce AI invocation rate (increase coverage threshold)
- Switch to GPT-3.5 Turbo
- Add request rate limiting

## Integration with n8n

In your n8n cloud workflow, add HTTP Request node:

```javascript
// HTTP Request node config
{
  "method": "POST",
  "url": "https://celesteos-entity-extraction.onrender.com/extract",
  "authentication": "none",
  "sendBody": true,
  "bodyParameters": {
    "parameters": [
      {
        "name": "text",
        "value": "={{$json.message}}"
      }
    ]
  },
  "options": {
    "timeout": 30000,
    "response": {
      "response": {
        "neverError": false
      }
    }
  }
}
```

Response will contain:
```json
{
  "entities": {
    "equipment": [...],
    "model": [...],
    "org": [...],
    ...
  }
}
```

Use these entities for downstream Supabase vector search.
