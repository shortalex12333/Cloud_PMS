# V2 Show Related: Embedding Re-Ranking

**PR Type:** Enhancement (V2)
**Feature:** P1 Show Related - Semantic similarity re-ranking
**Blocks:** None (V1 shipped and stable)
**Priority:** P1 (Foundation for V2+ re-ranking improvements)

---

## Summary

This PR adds **semantic similarity re-ranking** infrastructure for Show Related (V2).
V1 FK-based retrieval remains the primary signal; embeddings provide a secondary
re-ranking boost within each group.

**Key Principle:** Embeddings are computed in **batch nightly jobs** (2am), never in the read path.
This eliminates OpenAI latency from user requests.

---

## Changes Overview

### 1. Database Migration: Embedding Staleness Tracking

**File:** `supabase/migrations/20260128_1700_v2_embedding_staleness.sql`

**Added Columns:**

| Table | Column | Type | Purpose |
|-------|--------|------|---------|
| pms_work_orders | embedding_updated_at | TIMESTAMPTZ | Staleness detection |
| pms_equipment | embedding_updated_at | TIMESTAMPTZ | Staleness detection |
| pms_faults | embedding_updated_at | TIMESTAMPTZ | Staleness detection |
| pms_work_order_notes | embedding_updated_at | TIMESTAMPTZ | Staleness detection |
| pms_parts | embedding_updated_at | TIMESTAMPTZ | Staleness detection |
| pms_attachments | search_embedding | vector(1536) | Semantic search |
| pms_attachments | embedding_text | TEXT | Input text for embedding |
| pms_attachments | embedding_updated_at | TIMESTAMPTZ | Staleness detection |

**Staleness Logic:**
```sql
-- An embedding is stale when content changed since last embed
WHERE embedding_updated_at IS NULL          -- Never embedded
   OR updated_at > embedding_updated_at     -- Content changed
```

**Partial Indexes:**
- `idx_pms_work_orders_embedding_stale` - Efficient stale WO lookup
- `idx_pms_equipment_embedding_stale` - Efficient stale equipment lookup
- `idx_pms_faults_embedding_stale` - Efficient stale fault lookup
- `idx_pms_parts_embedding_stale` - Efficient stale part lookup
- `idx_pms_attachments_embedding_stale` - Efficient stale attachment lookup

### 2. Batch Refresh Worker

**File:** `apps/api/workers/embedding_refresh_worker.py`

**Features:**
- Nightly 2am batch refresh of stale embeddings
- Priority order: work_orders → equipment → faults → parts → attachments → notes
- Equipment joins for WO context (embedding_text includes equipment name)
- Cost caps: Max 500 embeddings per run (~$0.01/run)
- Partial index usage for efficient queries
- Stats tracking and logging

**Configuration:**
```bash
EMBEDDING_REFRESH_ENABLED=true
EMBEDDING_REFRESH_MAX_PER_RUN=500
EMBEDDING_REFRESH_BATCH_SIZE=50
SUPABASE_URL=...
SUPABASE_SERVICE_KEY=...
OPENAI_API_KEY=...
```

**Usage:**
```bash
python -m workers.embedding_refresh_worker
```

### 3. Documentation Updates

**Phase 6 Runbook:** `docs/pipeline/work_order_lens/p1_show_related/p1_show_related_PHASE_6_SQL_BACKEND.md`

Added V2 section documenting:
- Re-rank formula options (scaled additive vs multiplicative)
- Alpha (α) parameter selection (0.0-1.0 range)
- Embedding text construction templates
- Batch worker configuration
- Monitoring & observability
- V2 implementation checklist

**Backfill Plan:** `docs/pipeline/work_order_lens/p1_show_related/doc_metadata_description_backfill_plan.md`

Comprehensive plan for populating `doc_metadata.description`:
- Phase 1: Manual curation (top 20 manuals)
- Phase 2: Filename parsing heuristic
- Phase 3: OCR summary (future)
- Validation queries and success criteria

### 4. Staging CI Enhancements

**File:** `tests/ci/staging_work_orders_show_related.py`

**New Preflight Checks:**
1. **JWT Decode:** Validates JWT tokens before running tests
   - Checks expiration (exits if expired)
   - Extracts user_id and email
   - Displays TTL in hours

2. **Work Order Fetch:** Verifies test WO exists
   - Fetches WO via API before tests
   - Displays WO title and group counts
   - Exits if 404 or 500

**Benefits:**
- Catch JWT expiration before test failures
- Verify test data exists in staging
- Better error messages for debugging

---

## Re-Rank Formula

**Recommended: Scaled Additive**
```
final_score = FK_weight + α × 100 × cosine_similarity
```

Where:
- `FK_weight` = 70-100 (from V1: explicit links 70, same_equipment 80, manual 90, FK 100)
- `α` = 0.3 (tunable, 0.0-1.0)
- `cosine_similarity` = -1.0 to 1.0 (from pgvector `<=>` operator, negated)

**Example:**
- Part with FK_weight=100, cosine=0.85 → 100 + 0.3×100×0.85 = **125.5**
- Part with FK_weight=100, cosine=0.45 → 100 + 0.3×100×0.45 = **113.5**

**Production Strategy:**
1. Launch with `α=0.0` (V1 behavior - no re-ranking)
2. Shadow log embedding scores without affecting ranking
3. A/B test with `α=0.1` on 10% traffic
4. Graduate to `α=0.3` after validation

---

## Testing Strategy

### V2 Migration Testing

**Run locally:**
```bash
# Connect to local Supabase
psql -h localhost -p 54322 -U postgres -d postgres

# Apply migration
\i supabase/migrations/20260128_1700_v2_embedding_staleness.sql

# Verify columns added
SELECT table_name, column_name, data_type
FROM information_schema.columns
WHERE column_name = 'embedding_updated_at'
  AND table_name LIKE 'pms_%'
ORDER BY table_name;

# Verify indexes created
SELECT indexname, indexdef
FROM pg_indexes
WHERE indexname LIKE '%embedding_stale%'
ORDER BY indexname;
```

**Expected Output:**
- 6 tables with `embedding_updated_at` column
- 5 partial indexes for stale embedding lookup
- pms_attachments has `search_embedding` + `embedding_text` + `embedding_updated_at`

### Worker Testing

**Dry-run locally:**
```bash
# Set env vars
export EMBEDDING_REFRESH_ENABLED=true
export EMBEDDING_REFRESH_MAX_PER_RUN=10  # Small batch for testing
export EMBEDDING_REFRESH_BATCH_SIZE=5
export SUPABASE_URL=http://localhost:54321
export SUPABASE_SERVICE_KEY=<local_service_key>
export OPENAI_API_KEY=<your_key>

# Run worker
python -m workers.embedding_refresh_worker
```

**Expected Output:**
```
============================================================
Embedding Refresh Worker Starting
Max embeddings per run: 10
Batch size: 5
============================================================
Refreshing work order embeddings...
Found 5 stale work orders
Refreshed 5 work orders
Refreshing equipment embeddings...
Found 3 stale equipment records
Refreshed 3 equipment records
============================================================
Embedding Refresh Complete
Total refreshed: 8
Errors: 0
API calls: 8
Tokens used: ~1600
Elapsed: 2.3s
============================================================
```

### Staging CI Testing

**Run enhanced staging CI:**
```bash
# Source JWTs
source /tmp/staging_jwts.env

# Set test entity IDs
export STAGING_WORK_ORDER_ID=<staging_wo_id>
export STAGING_PART_ID=<staging_part_id>
export STAGING_API_URL=https://celeste-pipeline-v1.onrender.com
export STAGING_YACHT_ID=85fe1119-b04c-41ac-80f1-829d23322598

# Run tests
python tests/ci/staging_work_orders_show_related.py
```

**Expected Output:**
```
================================================================================
PREFLIGHT: JWT Token Validation
================================================================================
✅ STAGING_JWT_CREW: Valid (user_id=57e82f78..., email=crew.test@..., expires=2026-02-01 10:30:16, TTL=72.1h)
✅ STAGING_JWT_HOD: Valid (user_id=05a488fd..., email=hod.test@..., expires=2026-02-01 10:30:17, TTL=72.1h)
✅ All JWTs valid

================================================================================
PREFLIGHT: Work Order Fetch
================================================================================
✅ Work order found: <wo_id>
   Title: Hydraulic pump maintenance
   Groups returned: 4

================================================================================
RUNNING TESTS
================================================================================
✅ test_crew_view_related_200
✅ test_crew_cannot_add_link_403
✅ test_hod_can_add_link_200
✅ test_invalid_entity_type_400
✅ test_caps_enforced
✅ test_limit_exceeds_max_400
✅ test_match_reasons_present

================================================================================
STAGING CI TEST RESULTS
================================================================================
Passed: 7
Failed: 0
500 Errors: NO
```

---

## Deployment Plan

### Phase 1: Infrastructure (Week 2, Day 1-2)

**Apply Migration:**
```bash
# Connect to TENANT_1 Supabase
psql -h vzsohavtuotocgrfkfyd.supabase.co -U postgres

# Apply V2 migration
\i supabase/migrations/20260128_1700_v2_embedding_staleness.sql

# Verify success
SELECT COUNT(*) FROM information_schema.columns
WHERE column_name = 'embedding_updated_at'
  AND table_name IN ('pms_work_orders', 'pms_equipment', 'pms_faults',
                     'pms_work_order_notes', 'pms_parts', 'pms_attachments');
-- Expected: 6
```

**Deploy Worker (Render Cron):**
```yaml
# Add to render.yaml
- type: cron
  name: embedding-refresh-nightly
  runtime: python
  schedule: "0 2 * * *"  # 2am daily
  buildCommand: cd apps/api && pip install -r requirements.txt
  startCommand: cd apps/api && python -m workers.embedding_refresh_worker
  envVars:
    - key: PYTHON_VERSION
      value: "3.11.6"
    - key: EMBEDDING_REFRESH_ENABLED
      value: "true"
    - key: EMBEDDING_REFRESH_MAX_PER_RUN
      value: "500"
    - key: SUPABASE_URL
      value: "https://vzsohavtuotocgrfkfyd.supabase.co"
    - key: SUPABASE_SERVICE_KEY
      sync: false
    - key: OPENAI_API_KEY
      sync: false
```

### Phase 2: Backfill doc_metadata.description (Week 2, Day 2-3)

**Run backfill script:**
```bash
# Dry-run first
YACHT_ID=85fe1119-b04c-41ac-80f1-829d23322598 \
  python apps/api/scripts/backfill_doc_descriptions.py

# Apply if output looks good
YACHT_ID=85fe1119-b04c-41ac-80f1-829d23322598 \
  python apps/api/scripts/backfill_doc_descriptions.py --apply

# Verify coverage
psql -c "SELECT doc_type, COUNT(*) AS total, COUNT(description) AS has_desc
         FROM doc_metadata WHERE yacht_id = '85fe1119-b04c-41ac-80f1-829d23322598'
         GROUP BY doc_type;"
```

### Phase 3: Enable Re-Ranking (Week 2+, After A/B)

**Shadow Mode First (α=0.0):**
- Embeddings refresh nightly but don't affect ranking
- Log cosine scores alongside FK weights
- Collect data for validation

**A/B Test (α=0.1):**
- Enable on 10% traffic
- Compare FK-only vs re-ranked results
- Monitor for ranking quality improvements

**Full Rollout (α=0.3):**
- Enable for all traffic after validation
- Monitor cost and performance

---

## Cost Analysis

**One-time Migration:** $0 (DDL only)

**Nightly Batch Refresh:**
- 500 embeddings × 200 tokens avg × $0.02/1M tokens = **$0.002/night**
- Monthly: $0.06
- Yearly: $0.73

**Storage:**
- 500 vectors × 12 KB = 6 MB
- Negligible cost on Supabase ($0.024/GB/month)

**Total Monthly Cost:** ~$0.10 (embeddings + storage)

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Embedding costs exceed budget | Low | Hard cap at 500/night, monitor OpenAI usage |
| Worker fails silently | Medium | Add health check + Slack alerts |
| Stale embeddings for high-activity WOs | Low | Batch runs nightly, staleness <24h acceptable |
| doc_metadata.description backfill incomplete | Medium | Defer doc embeddings until >95% coverage |
| Re-ranking degrades quality | Medium | Shadow mode + A/B test before full rollout |

---

## Rollback Plan

**If issues detected:**

1. **Disable worker:** Set `EMBEDDING_REFRESH_ENABLED=false` in Render
2. **Revert ranking:** No code changes needed (α=0.0 = FK-only)
3. **Drop columns (optional):**
   ```sql
   ALTER TABLE pms_work_orders DROP COLUMN embedding_updated_at;
   -- Repeat for other tables
   ```

**Note:** V1 functionality unaffected - embeddings are additive only.

---

## Success Criteria

✅ **Merge Criteria:**
1. Migration applies cleanly to TENANT_1
2. Worker runs successfully in local testing
3. Staging CI 7/7 green with preflight checks
4. Documentation complete (Phase 6 + backfill plan)
5. PR approved by HOD

✅ **Production Readiness (Week 2):**
1. Render cron job deployed and running
2. Nightly refresh completing within 5 minutes
3. Zero errors in batch refresh logs
4. doc_metadata.description >95% populated
5. Shadow logging confirms cosine scores present

---

## Files Changed

### New Files
- `supabase/migrations/20260128_1700_v2_embedding_staleness.sql` (Migration)
- `apps/api/workers/embedding_refresh_worker.py` (Batch worker)
- `docs/pipeline/work_order_lens/p1_show_related/doc_metadata_description_backfill_plan.md` (Backfill plan)
- `docs/pipeline/work_order_lens/p1_show_related/V2_PR_SUMMARY.md` (This file)

### Modified Files
- `docs/pipeline/work_order_lens/p1_show_related/p1_show_related_PHASE_6_SQL_BACKEND.md` (Added V2 section)
- `tests/ci/staging_work_orders_show_related.py` (Preflight checks)

### Future Files (Not in this PR)
- `apps/api/scripts/backfill_doc_descriptions.py` (Backfill script - Week 2)
- `apps/api/handlers/related_handlers.py` (Re-ranking logic - Week 2+)
- `render.yaml` (Cron job config - Week 2)

---

## Reviewer Checklist

- [ ] Migration SQL reviewed and safe (idempotent, no data loss)
- [ ] Worker code follows existing patterns (see `email_watcher_worker.py`)
- [ ] Cost caps enforced (MAX_PER_RUN=500)
- [ ] Documentation complete and accurate
- [ ] Preflight checks improve CI reliability
- [ ] No breaking changes to V1 API
- [ ] Rollback plan is clear

---

## Next Steps (Post-Merge)

1. **Week 2, Day 1:** Apply migration to TENANT_1
2. **Week 2, Day 1:** Deploy Render cron job
3. **Week 2, Day 2:** Run doc_metadata.description backfill
4. **Week 2, Day 3:** Verify nightly batch refresh working
5. **Week 2+:** Implement re-ranking handler changes (shadow mode)
6. **Week 3+:** A/B test and graduate to production

---

**V2 Status:** 🟡 READY FOR REVIEW (Infrastructure only, no ranking changes yet)
