# Autonomous Testing Runbook

## Overview

6-hour autonomous testing infrastructure for email auto-linking validation. Tests L1 (explicit IDs) and L2.5 (hybrid fusion) linking across multiple scenarios with real and synthetic data.

## Success Criteria

| Metric | Target | Status Check |
|--------|--------|--------------|
| L1 Precision | ≥ 95% | Explicit ID emails auto-link correctly |
| L2.5 Top-1 Alignment | ≥ 80% | Primary suggestion matches ground truth |
| L2.5 Suggestion Rate | ≥ 50% | Strong suggestions accepted |
| Suggestion Coverage | ≥ 70% | Non-L1 tests produce ≥1 suggestion |
| P50 Latency | ≤ 2 min | Median insert→suggestion time |
| P95 Latency | ≤ 5 min | 95th percentile latency |
| Worker Errors | < 1% | Sustained processing without crashes |

## Prerequisites

### 1. Environment Variables

Set these in your shell or `.env` file:

```bash
# Master Supabase (for projection/embedding workers)
export MASTER_SUPABASE_URL="https://qvzmkaamzaqxpzbewjxe.supabase.co"
export MASTER_SUPABASE_SERVICE_KEY="eyJhbGci..."

# yTEST_YACHT_001 (for email extraction/link suggester workers)
export yTEST_YACHT_001_SUPABASE_URL="https://vzsohavtuotocgrfkfyd.supabase.co"
export yTEST_YACHT_001_SUPABASE_SERVICE_KEY="eyJhbGci..."

# OpenAI (for embedding generation)
export OPENAI_API_KEY="sk-proj-y288..."

# Test Yacht ID
export TEST_YACHT_ID="00000000-0000-0000-0000-000000000001"
```

### 2. Database Migrations

Ensure `match_link_targets_rpc` migration is applied to yTEST_YACHT_001:

```bash
cd supabase
supabase db push --db-url "$yTEST_YACHT_001_SUPABASE_URL"
```

Or manually apply:

```bash
psql "$yTEST_YACHT_001_SUPABASE_URL" < migrations/20260206000003_match_link_targets_rpc.sql
```

### 3. Docker

Ensure Docker is running and you have the API Dockerfile built:

```bash
cd apps/api
docker build -t celeste-api:latest .
```

### 4. Python Dependencies

```bash
cd apps/api
pip install -r requirements.txt
```

## Quick Start

### Full 6-Hour Run

```bash
./scripts/autonomy/run_autonomy.sh
```

### Custom Configuration

```bash
# 12 cycles × 10 min = 2 hours
./scripts/autonomy/run_autonomy.sh 12 600

# 3 cycles × 5 min = 15 min (smoke test)
./scripts/autonomy/run_autonomy.sh 3 300
```

## Components

### 1. Worker Stack (`docker-compose.workers.yml`)

Four parallel workers:

- **projection_worker**: Maintains `search_index` from `search_projection_queue`
- **embedding_worker_1536**: Generates GPT-1536 embeddings for search
- **email_extraction_worker**: Extracts tokens from `email_messages`
- **link_suggester_worker**: Creates `email_links` suggestions via LinkingLadder

### 2. Data Sampler (`scripts/autonomy/sample_real_data.py`)

Queries yTEST_YACHT_001 for real:
- Part numbers (from `pms_parts`)
- Equipment serials (from `equipment`)
- Work order numbers (from `pms_work_orders`)
- Vendor emails (from `vendors`)

**Output**: `test-results/autonomy/sampled_data.json`

### 3. Email Simulator (`scripts/autonomy/simulate_self_email.py`)

Generates test emails and inserts into `email_threads` + `email_messages`:

**Scenarios**:
- `wo_explicit`: Emails with explicit WO-#### IDs (L1 baseline)
- `part_number`: Emails mentioning part numbers (L2.5 part linking)
- `equipment_serial`: Emails about equipment by serial/model (L2.5 equipment linking)
- `warranty_claim`: Warranty-related emails (L2.5 equipment + procedures)
- `vendor_generic`: Vendor emails without explicit IDs (L4 vendor matching)

**Output**: `test-results/autonomy/ground_truth.json`

### 4. Validator (`scripts/autonomy/validate_autolinking.py`)

Checks `email_links` against ground truth:

**Metrics**:
- Primary match rate (top suggestion = expected object)
- Top-3 match rate (expected object in top 3)
- Suggestion coverage (% with ≥1 suggestion)
- Latency (created_at → suggestions_generated_at)
- Error rate

**Output**: `test-results/autonomy/validation_YYYYMMDD_HHMMSS.json`

### 5. Orchestrator (`scripts/autonomy/run_autonomy.sh`)

Main loop:

1. Start workers (once at beginning)
2. For each cycle:
   - Sample real data
   - Generate test emails
   - Wait 5 min for processing
   - Validate results
   - Health check workers
   - Wait remainder of cycle
3. Stop workers (at end)
4. Aggregate final metrics

**Output**: `test-results/autonomy/run_YYYYMMDD_HHMMSS.log`

## Test Scenarios

### L1: Explicit Work Order IDs

**Template**: "Re: WO-1234 - Status Update"

**Expected**:
- Level: L1
- Match: `pms_work_orders` by `wo_number`
- Confidence: `deterministic`
- Action: `auto_link`

### L2.5: Part Number Linking

**Template**: "Part ABC-123 - Availability Question"

**Expected**:
- Level: L2.5
- Match: `pms_parts` by `part_number`
- Confidence: `suggested`
- Action: `suggest`
- Related: Manuals, documentation

### L2.5: Equipment Serial

**Template**: "Service Request for Generator (S/N: XYZ789)"

**Expected**:
- Level: L2.5
- Match: `equipment` by `serial_number`
- Confidence: `suggested`
- Action: `suggest`
- Related: Open WOs, maintenance history

### L2.5: Warranty Claim

**Template**: "Warranty Claim: Generator Failure"

**Expected**:
- Level: L2.5
- Match: `equipment` with warranty context
- Confidence: `suggested`
- Action: `suggest`
- Related: Original warranty threads, images, procedures

### L4: Vendor Match

**Template**: "Quote Request for Upcoming Service" (from vendor email)

**Expected**:
- Level: L4
- Match: `vendors` by `email_hash`
- Confidence: `suggested`
- Action: `weak_suggest`

## Monitoring

### Worker Logs

```bash
# Follow all workers
docker-compose -f docker-compose.workers.yml logs -f

# Specific worker
docker-compose -f docker-compose.workers.yml logs -f link_suggester_worker
```

### Worker Status

```bash
docker-compose -f docker-compose.workers.yml ps
```

### Database Queries

Check processing status:

```sql
-- Threads awaiting extraction
SELECT COUNT(*) FROM email_threads
WHERE extracted_tokens IS NULL;

-- Threads awaiting suggestions
SELECT COUNT(*) FROM email_threads
WHERE extracted_tokens IS NOT NULL
AND suggestions_generated_at IS NULL;

-- Recent suggestions
SELECT et.latest_subject, el.object_type, el.score, el.confidence
FROM email_links el
JOIN email_threads et ON et.id = el.thread_id
WHERE el.created_at > NOW() - INTERVAL '1 hour'
ORDER BY el.created_at DESC
LIMIT 20;
```

## Troubleshooting

### Workers Not Starting

**Check**: Docker is running and API image is built

```bash
docker info
docker images | grep celeste-api
```

**Fix**: Rebuild image

```bash
cd apps/api
docker build -t celeste-api:latest .
```

### No Suggestions Generated

**Check**: Workers are processing

```bash
docker-compose -f docker-compose.workers.yml logs link_suggester_worker | tail -50
```

**Common Issues**:
- `LINK_SUGGESTER_ENABLED=false` → Set to `true` in docker-compose
- Migration not applied → Apply `match_link_targets_rpc` migration
- No extracted tokens → Check `email_extraction_worker` logs

### Low L2.5 Alignment

**Investigate**:

1. Check score distribution:
   ```sql
   SELECT object_type, AVG(score), MIN(score), MAX(score)
   FROM email_links
   WHERE confidence = 'suggested'
   GROUP BY object_type;
   ```

2. Review failures in validation output:
   ```bash
   jq '.results[] | select(.primary_match == false)' test-results/autonomy/validation_*.json | less
   ```

3. Adjust fusion weights in `apps/api/services/scoring_engine.py`:
   ```python
   HYBRID_WEIGHTS = {
       'text': 0.45,      # Increase for keyword-heavy
       'vector': 0.35,    # Increase for semantic
       'recency': 0.15,   # Increase for recent objects
       'bias': 0.05,      # Increase for role weighting
   }
   ```

### High Latency

**Check**: Worker polling intervals

```bash
# In docker-compose.workers.yml, decrease poll intervals:
PROJECTION_POLL_INTERVAL=15  # from 30
EMBEDDING_POLL_INTERVAL=15   # from 30
EXTRACTION_POLL_INTERVAL=15  # from 30
LINK_SUGGESTER_POLL_INTERVAL=30  # from 60
```

**Check**: Queue backlog

```sql
-- Projection queue
SELECT COUNT(*) FROM search_projection_queue WHERE status = 'pending';

-- Embedding queue
SELECT COUNT(*) FROM embedding_queue WHERE status = 'pending';
```

### Worker Crashes

**Check**: Container restarts

```bash
docker-compose -f docker-compose.workers.yml ps
```

**Check**: Logs for exceptions

```bash
docker-compose -f docker-compose.workers.yml logs | grep -i error
docker-compose -f docker-compose.workers.yml logs | grep -i exception
```

**Common Issues**:
- Invalid environment variables
- Database connection timeout
- OpenAI API quota exceeded
- Memory limit exceeded (increase in docker-compose)

## Results Interpretation

### Validation Output

```json
{
  "metrics": {
    "total_tests": 50,
    "l1_tests": 10,
    "l25_tests": 30,
    "other_tests": 10,
    "l1_precision": 95.0,           // ✓ PASS (≥95%)
    "l25_top1_alignment": 83.3,     // ✓ PASS (≥80%)
    "l25_top3_alignment": 90.0,     // Bonus metric
    "suggestion_coverage": 76.7,    // ✓ PASS (≥70%)
    "p50_latency_seconds": 87.5,    // ✓ PASS (≤120s)
    "p95_latency_seconds": 245.0,   // ✓ PASS (≤300s)
    "tokens_extracted_count": 50,
    "suggestions_generated_count": 48,
    "errors": 0
  },
  "success_criteria": {
    "l1_precision_pass": true,
    "l25_top1_pass": true,
    "suggestion_coverage_pass": true,
    "p50_latency_pass": true,
    "p95_latency_pass": true
  }
}
```

### Red Flags

- **L1 precision < 95%**: Explicit ID extraction broken
- **L2.5 top-1 < 80%**: Hybrid fusion needs tuning
- **Suggestion coverage < 70%**: Threshold too high or search index incomplete
- **P95 latency > 300s**: Workers not keeping up
- **Errors > 0**: Database issues or worker crashes

## Maintenance

### Clean Up Old Results

```bash
# Keep last 10 validation runs
cd test-results/autonomy
ls -1t validation_*.json | tail -n +11 | xargs rm -f

# Archive logs older than 7 days
find . -name "run_*.log" -mtime +7 -exec gzip {} \;
```

### Update Test Data

Re-sample if database changes significantly:

```bash
python scripts/autonomy/sample_real_data.py
```

### Adjust Test Mix

Edit `simulate_self_email.py`:

```python
# Default distribution (line ~342)
scenarios = ['wo_explicit'] * 10 + ['part_number'] * 15 + ...

# Custom (more part number tests)
scenarios = ['wo_explicit'] * 5 + ['part_number'] * 25 + ...
```

## Next Steps

### After Successful Run

1. Review aggregated metrics across all cycles
2. Identify patterns in failures (specific part numbers? equipment types?)
3. Tune fusion weights if L2.5 alignment < 80%
4. Deploy to staging with real Graph API integration
5. Monitor production metrics via telemetry

### Extend Testing

1. Add purchase order scenarios (L2 procurement)
2. Add fault code scenarios (L1 explicit fault IDs)
3. Add multi-thread warranty conversations
4. Simulate attachment-based linking (PDFs with IDs)
5. Test RLS policies with different user roles

## References

- L2.5 Hybrid Fusion: `apps/api/services/scoring_engine.py`
- Linking Ladder: `apps/api/services/linking_ladder.py`
- Candidate Finder: `apps/api/services/candidate_finder.py`
- Token Extractor: `apps/api/services/token_extractor.py`
- RPC Function: `supabase/migrations/20260206000003_match_link_targets_rpc.sql`
