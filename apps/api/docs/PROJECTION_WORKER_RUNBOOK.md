# Projection Worker Runbook

## Purpose

The projection worker is the **single writer** for `search_index`. It:

1. Consumes items from `search_projection_queue`
2. Fetches source data and builds projection fields
3. Populates `search_text`, `filters`, `payload` per domain mapping
4. Computes `recency_ts` and `ident_norm` for Hard Tiers ranking
5. Emits cache invalidation via `pg_notify`
6. Enqueues embedding jobs for content changes

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | (required) | PostgreSQL connection string. **Use port 6543** for Supavisor. |
| `F1_PROJECTION_WORKER_ENABLED` | `false` | Set to `true` to enable worker |
| `PROJECTION_BATCH_SIZE` | `50` | Items per batch claim |
| `PROJECTION_POLL_INTERVAL` | `5` | Seconds between polls when queue empty |
| `PROJECTION_MAX_SEARCH_TEXT` | `12000` | Max chars for search_text |
| `PROJECTION_CHUNK_KEYWORDS` | `20` | Top-K chunk keywords to aggregate |

## Queue Lifecycle

```
┌─────────────────┐
│  source table   │  (INSERT/UPDATE/DELETE via trigger)
└────────┬────────┘
         │ enqueue
         ▼
┌─────────────────┐
│  search_        │  status: 'queued' → 'processing' → 'completed'/'failed'
│  projection_    │
│  queue          │
└────────┬────────┘
         │ claim (FOR UPDATE SKIP LOCKED)
         ▼
┌─────────────────┐
│  projection     │  fetch source → build fields → upsert
│  worker         │
└────────┬────────┘
         │ pg_notify
         ▼
┌─────────────────┐
│  f1_cache_      │  subscribers invalidate cached results
│  invalidate     │
└─────────────────┘
```

## Idempotence

The worker uses `source_version` guard for idempotent upserts:

```sql
ON CONFLICT (object_type, object_id)
DO UPDATE SET ...
WHERE search_index.source_version < EXCLUDED.source_version
```

This means:
- Duplicate queue items are safe (later version wins)
- Out-of-order processing is safe (higher version wins)
- Re-running the same item is a no-op

## Hard Tiers Fields

### recency_ts

Per-domain timestamp for freshness sorting. Mappings in `projection.yaml`:

| Domain | recency_source | Fallback |
|--------|----------------|----------|
| work_order | updated_at | - |
| work_order_note | created_at | - |
| note | created_at | - |
| fault | detected_at | created_at |
| equipment | updated_at | - |
| part | updated_at | - |
| inventory | updated_at | last_counted_at |
| receiving | received_date | created_at |
| purchase_order | ordered_at | created_at |
| certificate | updated_at | - |
| email | received_at | - |
| document | updated_at | - |
| handover_item | created_at | - |
| shopping_item | updated_at | - |
| warranty_claim | created_at | - |

### ident_norm

Normalized identifier for exact ID matching:

| Domain | ident_source | Example |
|--------|--------------|---------|
| work_order | wo_number | `WO12345` |
| fault | fault_code | `FLT001` |
| equipment | code | `EQABC123` |
| part | part_number | `PN54321` |
| inventory | part_number (via join) | `PN54321` |
| purchase_order | po_number | `PO98765` |
| certificate | certificate_number | `CERT001` |
| receiving | vendor_reference | `VR2026001` |
| warranty_claim | claim_number | `WC2026001` |

Normalization: `UPPER(REGEXP_REPLACE(value, '[\s\-_]+', '', 'g'))`

## Backfill Steps

### Initial Backfill

For a fresh deployment or after schema changes:

```bash
# 1. Clear the queue
psql $DATABASE_URL -c "DELETE FROM search_projection_queue"

# 2. Enqueue all source rows
psql $DATABASE_URL <<'SQL'
INSERT INTO search_projection_queue (source_table, object_id, yacht_id, op, source_version)
SELECT 'pms_work_orders', id, yacht_id, 'U', 1 FROM pms_work_orders
UNION ALL
SELECT 'pms_parts', id, yacht_id, 'U', 1 FROM pms_parts
-- ... repeat for all source tables
;
SQL

# 3. Run worker (will process entire queue)
F1_PROJECTION_WORKER_ENABLED=true python workers/projection_worker.py
```

### Hard Tiers Backfill

If `recency_ts` and `ident_norm` need backfilling on existing rows:

```bash
# Run the backfill script
python scratchpad/backfill_hard_tiers.py
```

Or manually:

```sql
-- Work orders
UPDATE search_index
SET recency_ts = COALESCE((payload->>'updated_at')::timestamptz, updated_at),
    ident_norm = UPPER(REGEXP_REPLACE(COALESCE(payload->>'wo_number', ''), '[\s\-_]+', '', 'g'))
WHERE object_type = 'work_order';

-- Parts
UPDATE search_index
SET recency_ts = COALESCE((payload->>'updated_at')::timestamptz, updated_at),
    ident_norm = UPPER(REGEXP_REPLACE(COALESCE(payload->>'part_number', ''), '[\s\-_]+', '', 'g'))
WHERE object_type = 'part';

-- ... repeat for all domains
```

## Failure Modes

### Queue Item Fails

- Item status set to `failed`, `retry_count` incremented
- Error message stored in `error` column
- Item not retried automatically (manual intervention required)

**Recovery:**
```sql
-- Check failed items
SELECT * FROM search_projection_queue WHERE status = 'failed' ORDER BY created_at DESC LIMIT 10;

-- Retry failed items
UPDATE search_projection_queue SET status = 'queued', error = NULL WHERE status = 'failed';
```

### Source Row Not Found

If the source row was deleted before the worker processed the queue item:
- For UPDATE: marked as failed, "Source row not found"
- For DELETE: already handled (item would be 'D' operation)

### Database Connection Lost

- Worker reconnects on next iteration
- Current batch is rolled back
- Claimed items return to 'queued' status (lock released)

### Worker Crash

- Graceful shutdown on SIGINT/SIGTERM
- Current transaction rolled back
- Claimed items return to 'queued' status

## Monitoring

### Queue Depth

```sql
SELECT status, COUNT(*)
FROM search_projection_queue
GROUP BY status;
```

Healthy: `queued` count should be low (< 100 except during backfill)

### Processing Rate

```sql
SELECT
    date_trunc('minute', completed_at) AS minute,
    COUNT(*) AS processed
FROM search_projection_queue
WHERE status = 'completed'
  AND completed_at > NOW() - INTERVAL '1 hour'
GROUP BY 1
ORDER BY 1 DESC;
```

### Hard Tiers Coverage

```sql
SELECT
    object_type,
    COUNT(*) AS total,
    COUNT(recency_ts) AS with_recency,
    COUNT(ident_norm) AS with_ident,
    ROUND(100.0 * COUNT(recency_ts) / COUNT(*), 1) AS recency_pct
FROM search_index
GROUP BY object_type
ORDER BY object_type;
```

### Worker Logs

Look for:
- `Batch complete. Total: X done, Y failed`
- `FAIL:` or `ERROR:` entries
- `claim=Xms, process=Yms` timing patterns

## Scaling

### Single Worker (Default)

- Sufficient for normal load
- Processes ~50-100 items/second
- No coordination needed

### Multiple Workers

- Only if queue depth consistently > 1000
- Workers use `FOR UPDATE SKIP LOCKED` for coordination
- Don't run more than 2-3 workers (diminishing returns)

## Related Components

- **Embedding Worker**: Consumes `embedding_jobs`, generates `embedding_1536`
- **Cache Invalidation**: Listens on `f1_cache_invalidate` channel
- **hyper_search_multi**: RPC that reads from `search_index`
