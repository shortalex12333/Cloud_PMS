# Autonomous Testing Setup - Quick Start

## Status: READY FOR EXECUTION

All components have been created and are ready for the 6-hour autonomous test run.

## ⚠️ Prerequisites (REQUIRED)

### 1. Apply Database Migration

The `match_link_targets_rpc` function must be applied to yTEST_YACHT_001 before running tests.

**Steps**:
1. Go to: https://supabase.com/dashboard/project/vzsohavtuotocgrfkfyd/sql/new
2. Open file: `supabase/migrations/20260206000003_match_link_targets_rpc.sql`
3. Copy entire contents and paste into SQL Editor
4. Click "Run"
5. Verify success (should see "Success. No rows returned")

**Verification**:
```bash
./scripts/autonomy/apply_migration.sh
```

Should output: `✓ Migration already applied - function match_link_targets exists`

### 2. Set Environment Variables

Export these in your shell:

```bash
# Source from environment variables file (see: /Volumes/Backup/CELESTE/env vars/render_hadnover_env_vars.md)
# Or set manually:

export MASTER_SUPABASE_URL="<your_master_supabase_url>"
export MASTER_SUPABASE_SERVICE_KEY="<your_master_service_key>"

export yTEST_YACHT_001_SUPABASE_URL="<your_test_yacht_supabase_url>"
export yTEST_YACHT_001_SUPABASE_SERVICE_KEY="<your_test_yacht_service_key>"

export OPENAI_API_KEY="<your_openai_api_key>"

export TEST_YACHT_ID="00000000-0000-0000-0000-000000000001"
```

### 3. Build API Docker Image

```bash
cd apps/api
docker build -t celeste-api:latest .
cd ../..
```

### 4. Make Scripts Executable

```bash
chmod +x scripts/autonomy/*.sh scripts/autonomy/*.py
```

## 🚀 Execution

### Full 6-Hour Run (36 cycles × 10 minutes)

```bash
./scripts/autonomy/run_autonomy.sh
```

### Quick Smoke Test (3 cycles × 5 minutes = 15 min)

```bash
./scripts/autonomy/run_autonomy.sh 3 300
```

### Custom Run

```bash
./scripts/autonomy/run_autonomy.sh [CYCLES] [CYCLE_DURATION_SECONDS]
```

## 📊 Monitoring

### Watch Real-Time Logs

```bash
# All workers
docker-compose -f docker-compose.workers.yml logs -f

# Specific worker
docker-compose -f docker-compose.workers.yml logs -f link_suggester_worker

# Test orchestrator
tail -f test-results/autonomy/run_*.log
```

### Check Worker Health

```bash
docker-compose -f docker-compose.workers.yml ps
```

### View Latest Results

```bash
# Latest validation report
ls -1t test-results/autonomy/validation_*.json | head -1 | xargs cat | jq '.metrics'

# Success criteria
ls -1t test-results/autonomy/validation_*.json | head -1 | xargs cat | jq '.metrics.success_criteria'
```

## 📁 Output Files

All results saved to `test-results/autonomy/`:

| File | Description |
|------|-------------|
| `sampled_data.json` | Real IDs from yTEST_YACHT_001 |
| `ground_truth.json` | Test emails with expected links |
| `validation_YYYYMMDD_HHMMSS.json` | Validation results per cycle |
| `run_YYYYMMDD_HHMMSS.log` | Full orchestrator log |

## ✅ Success Criteria

| Metric | Target | Pass Threshold |
|--------|--------|----------------|
| L1 Precision | ≥95% | Explicit ID emails link correctly |
| L2.5 Top-1 Alignment | ≥80% | Primary suggestion matches ground truth |
| Suggestion Coverage | ≥70% | Non-L1 tests get ≥1 suggestion |
| P50 Latency | ≤120s | Median processing time |
| P95 Latency | ≤300s | 95th percentile processing time |

## 🧹 Cleanup

### Stop Workers

```bash
docker-compose -f docker-compose.workers.yml down
```

### Clean Old Results

```bash
# Keep last 10 validations
cd test-results/autonomy
ls -1t validation_*.json | tail -n +11 | xargs rm -f

# Archive old logs
find . -name "run_*.log" -mtime +7 -exec gzip {} \;
```

## 📖 Documentation

See [AUTONOMY_RUNBOOK.md](../../docs/AUTONOMY_RUNBOOK.md) for detailed documentation.

## Components Created

✅ `docker-compose.workers.yml` - Worker orchestration
✅ `scripts/autonomy/sample_real_data.py` - Real data sampler
✅ `scripts/autonomy/simulate_self_email.py` - Test email generator
✅ `scripts/autonomy/validate_autolinking.py` - Results validator
✅ `scripts/autonomy/run_autonomy.sh` - Main orchestrator
✅ `docs/AUTONOMY_RUNBOOK.md` - Complete documentation
✅ `scripts/autonomy/apply_migration.sh` - Migration checker

## Next Steps

1. **Apply migration** (see Prerequisites #1)
2. **Set environment variables** (see Prerequisites #2)
3. **Build Docker image** (see Prerequisites #3)
4. **Run smoke test**: `./scripts/autonomy/run_autonomy.sh 3 300`
5. If smoke test passes, **run full 6-hour test**: `./scripts/autonomy/run_autonomy.sh`

## Support

For issues:
- Check `docs/AUTONOMY_RUNBOOK.md` Troubleshooting section
- Review worker logs: `docker-compose -f docker-compose.workers.yml logs`
- Verify migration applied: `./scripts/autonomy/apply_migration.sh`
