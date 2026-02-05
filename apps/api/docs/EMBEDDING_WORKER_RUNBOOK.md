# Embedding Worker 1536 Runbook

**Service:** `f1-embedding-worker-1536`
**Script:** `apps/api/workers/embedding_worker_1536.py`
**Type:** Background Worker (long-running)

---

## Overview

The embedding worker generates 1536-dimensional embeddings using OpenAI's `text-embedding-3-small` model. It populates the `embedding_1536` column in `search_index` for vector similarity search.

### Responsibilities
- Poll `search_index` for rows needing embedding (delta policy)
- Call OpenAI API to generate 1536-dim embeddings
- Normalize vectors to unit length for cosine similarity
- Write embeddings to `embedding_1536` column
- Update `embedding_hash` for delta tracking

### What It Does NOT Do
- No text processing (projection worker handles `search_text`)
- No ranking or search logic
- No cache invalidation (projection worker handles this)

---

## Render Configuration

| Setting | Value |
|---------|-------|
| **Name** | `f1-embedding-worker-1536` |
| **Type** | Background Worker |
| **Root Directory** | `apps/api/workers` |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `python embedding_worker_1536.py` |
| **Instance** | Starter (0.5 CPU / 512MB) |

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | **Yes** | - | PostgreSQL connection (port **6543** for Supavisor) |
| `OPENAI_API_KEY` | **Yes** | - | OpenAI API key |
| `EMBED_MODEL` | No | `text-embedding-3-small` | Model name |
| `EMBED_DIMS` | No | `1536` | Embedding dimension |
| `EMBEDDING_VERSION` | No | `3` | Schema version |
| `BATCH_SIZE` | No | `100` | Rows per batch |
| `BATCH_SLEEP_SEC` | No | `0.1` | Sleep between batches |
| `ERROR_SLEEP_SEC` | No | `2.0` | Sleep on error |
| `REQUEST_TIMEOUT_SEC` | No | `30` | API timeout |
| `LOG_LEVEL` | No | `INFO` | Logging level |

---

## Delta Policy

Only re-embed when:
1. `embedding_1536 IS NULL` (never embedded)
2. `embedding_hash IS NULL` (no hash recorded)
3. `embedding_hash != content_hash` (content changed)
4. `embedding_version IS NULL OR < 3` (old schema)

This ensures we don't re-embed unchanged content.

---

## Health Checks

### Embedding Coverage
```sql
SELECT
    COUNT(*) AS total,
    COUNT(embedding_1536) AS with_embedding,
    ROUND(100.0 * COUNT(embedding_1536) / COUNT(*), 1) AS coverage_pct
FROM search_index
WHERE search_text IS NOT NULL AND search_text != '';
```
**Target:** >= 95% coverage

### Rows Needing Embedding
```sql
SELECT COUNT(*) FROM search_index
WHERE search_text IS NOT NULL
  AND search_text != ''
  AND (
      embedding_1536 IS NULL
      OR embedding_hash IS NULL
      OR embedding_hash != content_hash
      OR embedding_version IS NULL
      OR embedding_version < 3
  );
```
**Alert if:** > 1000 for extended period

### Model/Version Consistency
```sql
SELECT embedding_model, embedding_version, COUNT(*)
FROM search_index
WHERE embedding_1536 IS NOT NULL
GROUP BY 1, 2;
```
**Expected:** All rows show `text-embedding-3-small` / `3`

---

## Common Issues

### Worker Not Starting

1. **Check OPENAI_API_KEY:**
   ```bash
   echo $OPENAI_API_KEY  # Should start with 'sk-'
   ```

2. **Check DATABASE_URL port:**
   - Must be `6543` (Supavisor), not `5432`

3. **Check OpenAI quota:**
   - Rate limits or billing issues

### Embeddings Not Persisting

1. **Check hash matching:**
   ```sql
   SELECT COUNT(*)
   FROM search_index
   WHERE embedding_1536 IS NOT NULL
     AND embedding_hash = content_hash;
   ```
   Should equal total with embeddings.

2. **Check for hash algorithm mismatch:**
   - Both `content_hash` and `embedding_hash` should be SHA-256 truncated to 32 chars

### High API Error Rate

1. **Check OpenAI status:** https://status.openai.com

2. **Common errors:**
   - `RateLimitError`: Reduce `BATCH_SIZE`, increase `BATCH_SLEEP_SEC`
   - `InvalidRequestError`: Text too long (should be auto-truncated to 8000 chars)
   - `AuthenticationError`: Check API key

3. **Check logs for retry patterns:**
   ```
   OpenAI API error (attempt 1): ..., retrying in 0.5s
   ```

---

## Cost Management

### Estimated Costs (text-embedding-3-small)

| Volume | Est. Cost/month |
|--------|-----------------|
| 10K rows | ~$0.10 |
| 100K rows | ~$1.00 |
| 1M rows | ~$10.00 |

### Reducing Costs

1. **Delta policy:** Only re-embed changed content
2. **Batch processing:** 100 texts per API call
3. **Truncation:** Cap text at 8000 chars

---

## Scaling

- **Single worker is sufficient** for most workloads
- Processing rate: ~50-100 rows/sec (API-bound)
- For faster backfill, increase `BATCH_SIZE` to 200

---

## Graceful Shutdown

Worker responds to `SIGTERM`:
1. Finishes current batch
2. Commits transaction
3. Closes connection
4. Exits cleanly

Render sends `SIGTERM` during deploys. Allow 30s for shutdown.

---

## Recovery Procedures

### Full Re-embed
To regenerate all embeddings (e.g., after model change):
```sql
-- Reset embedding flags
UPDATE search_index
SET embedding_1536 = NULL,
    embedding_hash = NULL,
    embedding_version = NULL
WHERE search_text IS NOT NULL AND search_text != '';

-- Worker will re-process all rows
```

### Fix Hash Mismatch
If `embedding_hash` doesn't match `content_hash` algorithm:
```sql
-- Recalculate content_hash
UPDATE search_index
SET content_hash = SUBSTRING(encode(sha256(search_text::bytea), 'hex'), 1, 32)
WHERE search_text IS NOT NULL AND search_text != '';
```

---

## Metrics to Monitor

| Metric | Target | Alert Threshold |
|--------|--------|-----------------|
| Coverage | >= 95% | < 90% |
| Rows needing embed | < 100 | > 1000 for 30min |
| Rate (rows/sec) | > 50 | < 10 for 5min |
| API errors | < 1% | > 5% |
| Batch latency P95 | < 2s | > 5s |

---

## Chunk Embeddings

For `search_document_chunks`, use the same worker with appropriate table:

```sql
-- Check chunk coverage
SELECT
    COUNT(*) AS total,
    COUNT(embedding_1536) AS with_embedding,
    ROUND(100.0 * COUNT(embedding_1536) / COUNT(*), 1) AS coverage_pct
FROM search_document_chunks
WHERE content IS NOT NULL AND content != '';
```

The worker handles both tables using the same delta policy.

---

## Contact

- **Owner:** Search Team
- **Escalation:** Platform On-Call
- **Runbook Updated:** 2026-02-05
