# Render Deployment Configuration

## Service Details

- **Service ID**: `srv-d5fr5hre5dus73d3gdn0`
- **Production URL**: `https://pipeline-core.int.celeste7.ai`
- **Framework**: Python 3
- **Tier**: Starter
- **Repository**: `https://github.com/shortalex12333/Cloud_PMS/`
- **Branch**: `main`
- **Root Directory**: `apps/api`

## Build Configuration

### Current Settings

```bash
# Build Command
pip install -r requirements.txt

# Pre-Deploy Command
# (EMPTY - needs to be updated)

# Start Command
python -m uvicorn pipeline_service:app --host 0.0.0.0 --port $PORT
```

## Recommended Pre-Deploy Command

To ensure async refactor doesn't break production, add this pre-deploy command:

```bash
pytest tests/test_async_orchestrator.py -v --tb=line -k "not ai_path_low_coverage"
```

**Why this command:**
- Runs async tests before deployment
- Skips AI tests that require OPENAI_API_KEY (to avoid API costs during deploy)
- Fast path tests validate core functionality (regex/gazetteer)
- Fails deployment if async logic is broken

### Alternative (with AI testing)

If you want to test AI path during deployment (requires OPENAI_API_KEY in Render env):

```bash
pytest tests/test_async_orchestrator.py -v --tb=line
```

## Environment Variables Required

Make sure these are set in Render dashboard:

### Required for Runtime
- `OPENAI_API_KEY` - OpenAI API key for GPT-4o-mini
- `AI_MODEL` - (Optional) Defaults to `gpt-4o-mini`
- `MASTER_SUPABASE_URL` - Master database URL
- `MASTER_SUPABASE_JWT_SECRET` - JWT secret for auth
- `ALLOWED_ORIGINS` - CORS allowed origins
- All tenant database credentials (`yXXXX_SUPABASE_URL`, `yXXXX_SUPABASE_SERVICE_KEY`)

### Optional for Testing
- `ENVIRONMENT=production` - Environment flag
- `PYTHONPATH=/app` - Python module path

## Deployment Process

### Option 1: Auto-Deploy (Current)
Push to `main` branch → Render auto-deploys → Pre-deploy tests run → If tests pass, deploy

### Option 2: Manual Deploy via API
```bash
curl -X POST https://api.render.com/deploy/srv-d5fr5hre5dus73d3gdn0?key=Dcmb-n4O_M0
```

### Option 3: Manual Deploy via Dashboard
1. Go to Render dashboard
2. Navigate to service `srv-d5fr5hre5dus73d3gdn0`
3. Click "Manual Deploy" → "Deploy latest commit"

## Testing Before Deploy

### Local Testing
```bash
# Test in same environment as production
./run_tests.sh docker

# Or test locally
./run_tests.sh local
```

### CI/CD Testing
Add to GitHub Actions:
```yaml
- name: Run async tests
  run: |
    cd apps/api
    pip install -r requirements.txt
    pytest tests/test_async_orchestrator.py -v
```

## Rollback Plan

If deployment fails:

1. **Via Render Dashboard**:
   - Go to "Deploys" tab
   - Click "Rollback" on last successful deploy

2. **Via Git**:
   ```bash
   git revert HEAD
   git push origin main
   ```

3. **Emergency**: Disable auto-deploy, manually deploy last known good commit

## Health Checks

After deployment, verify:

1. **Health Endpoint**: `https://pipeline-core.int.celeste7.ai/health`
   ```bash
   curl https://pipeline-core.int.celeste7.ai/health
   ```

2. **Extractor Status**: `https://pipeline-core.int.celeste7.ai/debug/extractor`
   ```bash
   curl https://pipeline-core.int.celeste7.ai/debug/extractor
   ```

3. **Test Query**: `POST https://pipeline-core.int.celeste7.ai/extract`
   ```bash
   curl -X POST https://pipeline-core.int.celeste7.ai/extract \
     -H "Content-Type: application/json" \
     -d '{"query": "main engine temperature"}'
   ```

## Performance Monitoring

Expected latencies after async refactor:

- **Fast path (regex)**: 60-130ms
- **Shopping list queries**: 60-130ms (was 3-4s)
- **AI path**: 1.5-2s (was 3-4s)

Monitor via Render logs:
```bash
# Filter for timing metadata
grep "latency_ms" <render-logs>
```

## Troubleshooting

### Deployment Fails at Pre-Deploy

**Symptom**: Deploy fails with test errors
```
pytest tests/test_async_orchestrator.py -v --tb=line -k "not ai_path_low_coverage"
FAILED tests/test_async_orchestrator.py::...
```

**Solution**:
1. Check Render logs for specific test failure
2. Fix issue locally and re-test: `./run_tests.sh local`
3. Push fix to `main` → auto-redeploy

### Service Starts But Crashes

**Symptom**: Service starts, then crashes with 502 errors

**Possible causes**:
- Missing environment variable
- Import error (e.g., missing dependency)
- Async/await syntax error

**Debug**:
```bash
# Check Render logs for stack trace
# Look for:
[ERROR] ...
Traceback (most recent call last):
...
```

### AI Extraction Not Working

**Symptom**: All queries routing to regex path, AI never triggered

**Check**:
1. `OPENAI_API_KEY` is set in Render env vars
2. Key has credits remaining
3. Model is set correctly (`AI_MODEL=gpt-4o-mini`)

### Slow Performance

**Symptom**: Queries taking 3-4s even for known terms

**Check**:
1. Verify gazetteer loaded: Check logs for "Loaded 42,340 terms"
2. Verify coverage controller working: Check `needs_ai` metadata
3. Check if async is enabled: Look for `AsyncOpenAI` in logs

## Cost Optimization

### Reduce OpenAI Costs

1. **Use gpt-4o-mini** (95% cheaper than gpt-4o): ✅ Already implemented
2. **Add more terms to gazetteer**: Reduces AI invocations
3. **Tune coverage threshold**: Increase from 85% → 90% (more selective AI)

### Monitor Costs

Track AI invocation rate:
```bash
curl https://pipeline-core.int.celeste7.ai/debug/extractor
```

Look for `ai_invocation_rate` in response. Target: < 15%

---

**Last Updated**: 2026-01-30
**PR**: #56 (Async Refactor + GPT-4o-mini Migration)
