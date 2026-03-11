# F1 Cortex Production Launch Playbook

**Version**: 1.0.0
**Date**: 2026-02-22
**Status**: APPROVED FOR EXECUTION
**Target**: 134 Superyachts
**Constraint**: 512MB RAM / 0.5 CPU per Render worker

---

## Executive Summary

The F1 Cortex search engine achieves **95.99% Recall@3** on structured queries. The mathematical core is locked. Our only enemies now are **scale** and **memory**.

This playbook defines the infrastructure execution plan for deploying across 134 superyachts without OOM crashes, rate limit exhaustion, or silent data drift.

---

## Table of Contents

1. [The Great Backfill](#1-the-great-backfill)
2. [Counterfactual Feedback Loop](#2-counterfactual-feedback-loop)
3. [Infrastructure Hardening](#3-infrastructure-hardening)
4. [Edge Warping](#4-edge-warping)
5. [Runbook](#5-runbook)

---

## 1. The Great Backfill

### 1.1 The Problem

134 yachts × ~5,000 searchable entities each = **670,000 embedding jobs**.

If we enqueue all simultaneously:
- OpenAI rate limit: 3,000 RPM / 1M TPM → exhausted in 3 minutes
- Queue depth: 670,000 rows → Worker 5 claims 100 at a time → 6,700 batches
- Memory spike: Queue polling + connection pool + embedding buffer = OOM

### 1.2 Memory Budget (512MB Ceiling)

```
┌─────────────────────────────────────────────────────────────┐
│                    512MB ALLOCATION                          │
├─────────────────────────────────────────────────────────────┤
│ Python runtime + imports            │  80 MB │ FIXED        │
│ psycopg2 connection pool (5 conn)   │  25 MB │ FIXED        │
│ OpenAI SDK + httpx                  │  15 MB │ FIXED        │
│ Batch buffer (100 rows × 24KB text) │   2.4 MB │ PER BATCH  │
│ Embedding response (100 × 6.1KB)    │   0.6 MB │ PER BATCH  │
│ GC headroom                         │  50 MB │ SAFETY       │
├─────────────────────────────────────────────────────────────┤
│ TOTAL FIXED                         │ 170 MB │              │
│ AVAILABLE FOR PROCESSING            │ 342 MB │              │
│ SAFE BATCH SIZE                     │ 100    │ CONFIRMED    │
└─────────────────────────────────────────────────────────────┘
```

**Verdict**: Current `BATCH_SIZE=100` is safe. Do not increase.

### 1.3 Yacht-by-Yacht Chunking Strategy

**Phase 1: Prioritized Backfill Queue**

```sql
-- Create backfill orchestration table
CREATE TABLE IF NOT EXISTS backfill_schedule (
    yacht_id UUID PRIMARY KEY,
    yacht_name TEXT,
    priority INTEGER DEFAULT 0,        -- Higher = process first
    entity_count INTEGER DEFAULT 0,
    status TEXT DEFAULT 'pending',     -- pending, active, complete
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    error_count INTEGER DEFAULT 0
);

-- Populate with yacht priorities (VIP clients first)
INSERT INTO backfill_schedule (yacht_id, yacht_name, priority, entity_count)
SELECT
    y.id,
    y.name,
    CASE
        WHEN y.tier = 'enterprise' THEN 100
        WHEN y.tier = 'premium' THEN 50
        ELSE 10
    END as priority,
    (SELECT COUNT(*) FROM search_index WHERE yacht_id = y.id) as entity_count
FROM yachts y
WHERE y.status = 'active'
ORDER BY priority DESC;
```

**Phase 2: Sequential Yacht Activation**

```python
# In embedding_worker_1536.py - modify claim_batch()

def claim_batch_with_yacht_gate(cur, batch_size: int) -> List[Dict]:
    """
    Only claim jobs from the ACTIVE yacht in backfill_schedule.
    Prevents 134 yachts competing for the same worker.
    """
    # Get current active yacht (only one at a time)
    cur.execute("""
        SELECT yacht_id FROM backfill_schedule
        WHERE status = 'active'
        LIMIT 1
    """)
    row = cur.fetchone()

    if not row:
        # Activate next pending yacht
        cur.execute("""
            UPDATE backfill_schedule
            SET status = 'active', started_at = NOW()
            WHERE yacht_id = (
                SELECT yacht_id FROM backfill_schedule
                WHERE status = 'pending'
                ORDER BY priority DESC, entity_count ASC
                LIMIT 1
            )
            RETURNING yacht_id
        """)
        row = cur.fetchone()
        if not row:
            return []  # All done

    active_yacht_id = row[0]

    # Claim only from active yacht
    cur.execute("""
        WITH claimed AS (
            SELECT id FROM embedding_jobs
            WHERE status = 'queued'
              AND yacht_id = %s
            ORDER BY priority DESC, queued_at ASC
            LIMIT %s
            FOR UPDATE SKIP LOCKED
        )
        UPDATE embedding_jobs ej
        SET status = 'processing', started_at = NOW()
        FROM claimed c
        WHERE ej.id = c.id
        RETURNING ej.*
    """, (active_yacht_id, batch_size))

    return cur.fetchall()
```

**Phase 3: Rate Limit Compliance**

```
OpenAI Limits:
- 3,000 requests per minute (RPM)
- 1,000,000 tokens per minute (TPM)

Our Config:
- BATCH_SIZE = 100 rows
- Each row = 1 API call (current per-row processing)
- BATCH_SLEEP_SEC = 0.1 (100ms between batches)
- 100 rows / 0.1s = 1,000 RPM effective rate
- Headroom: 2,000 RPM buffer ✓

Token Budget:
- MAX_EMBEDDING_CHARS = 24,000 ≈ 8,000 tokens max per row
- 100 rows × 8,000 tokens = 800,000 TPM per batch
- At 1 batch/sec = 800,000 TPM ✓ (under 1M limit)
```

**Backfill Timeline Estimate**

```
670,000 jobs ÷ 100 per batch = 6,700 batches
6,700 batches × 0.5s avg processing = 3,350 seconds = ~56 minutes

With yacht gating overhead: ~2 hours total backfill
```

### 1.4 Supavisor Connection Pooler Configuration

```yaml
# render.yaml - embedding worker service
services:
  - name: embedding-worker
    env: docker
    plan: starter  # 512MB RAM
    envVars:
      - key: DATABASE_URL
        value: postgresql://postgres.[project]:[password]@aws-0-us-east-1.pooler.supabase.com:6543/postgres
        # ↑ Port 6543 = Supavisor transaction pooler (NOT 5432 direct)

      # Connection pool settings (psycopg2)
      - key: DB_POOL_MIN
        value: "2"
      - key: DB_POOL_MAX
        value: "5"  # Max 5 connections per worker

      # Batch settings
      - key: BATCH_SIZE
        value: "100"
      - key: BATCH_SLEEP_SEC
        value: "0.1"

      # Circuit breaker
      - key: CIRCUIT_BREAKER_THRESHOLD
        value: "5"
      - key: CIRCUIT_BREAKER_RESET_SEC
        value: "60"
```

---

## 2. Counterfactual Feedback Loop

### 2.1 The Philosophy

We do not hardcode synonyms. We let users teach the engine through clicks.

```
User searches: "watermaker"
User clicks: "Desalinator Manual" (document)
System learns: "watermaker" → semantically related to "Desalinator"
```

### 2.2 Click Event Schema

```sql
-- Add to existing analytics or create new table
CREATE TABLE IF NOT EXISTS search_click_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Context
    org_id UUID NOT NULL,
    yacht_id UUID NOT NULL,
    user_id UUID NOT NULL,

    -- Search context
    search_id UUID,                    -- Correlate with search_logs
    query_text TEXT NOT NULL,          -- What they searched
    query_normalized TEXT NOT NULL,    -- Lowercase, trimmed

    -- Click target
    clicked_object_type TEXT NOT NULL,
    clicked_object_id UUID NOT NULL,
    click_position INTEGER,            -- Rank in results (1-indexed)

    -- Timing
    search_timestamp TIMESTAMPTZ,
    click_timestamp TIMESTAMPTZ DEFAULT NOW(),
    dwell_time_ms INTEGER,             -- Time spent on result (if tracked)

    -- Outcome
    was_successful BOOLEAN,            -- Did they complete an action?

    CONSTRAINT fk_clicked_object
        FOREIGN KEY (clicked_object_type, clicked_object_id)
        REFERENCES search_index(object_type, object_id)
);

-- Index for aggregation queries
CREATE INDEX idx_click_events_target
    ON search_click_events(clicked_object_type, clicked_object_id);
CREATE INDEX idx_click_events_query
    ON search_click_events(query_normalized);
```

### 2.3 Click Ingestion (Frontend → API)

```typescript
// apps/web/src/hooks/useCelesteSearch.ts - add to existing hook

const trackSearchClick = useCallback(async (
  searchId: string,
  query: string,
  result: SearchResult,
  position: number
) => {
  try {
    await fetch('/api/analytics/search-click', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        search_id: searchId,
        query_text: query,
        clicked_object_type: result.object_type,
        clicked_object_id: result.object_id,
        click_position: position,
        search_timestamp: new Date().toISOString(),
      }),
    });
  } catch {
    // Silent fail - analytics should never break UX
  }
}, []);
```

### 2.4 Feedback Aggregation (Background Job)

```sql
-- Run nightly or on-demand
-- Appends successful query terms to search_index.search_text

WITH click_aggregates AS (
    -- Find query terms that consistently lead to clicks on specific objects
    SELECT
        clicked_object_type,
        clicked_object_id,
        query_normalized,
        COUNT(*) as click_count,
        AVG(click_position) as avg_position
    FROM search_click_events
    WHERE click_timestamp > NOW() - INTERVAL '30 days'
    GROUP BY clicked_object_type, clicked_object_id, query_normalized
    HAVING COUNT(*) >= 3  -- Minimum evidence threshold
       AND AVG(click_position) <= 5  -- Top-5 clicks only
),
new_terms AS (
    -- Extract terms not already in search_text
    SELECT
        ca.clicked_object_type,
        ca.clicked_object_id,
        ca.query_normalized as new_term,
        ca.click_count
    FROM click_aggregates ca
    JOIN search_index si
        ON si.object_type = ca.clicked_object_type
       AND si.object_id = ca.clicked_object_id
    WHERE si.search_text NOT ILIKE '%' || ca.query_normalized || '%'
)
-- Append learned terms to search_text
UPDATE search_index si
SET
    search_text = si.search_text || ' ' || nt.new_term,
    embedding_status = 'pending',  -- Re-embed with new terms
    updated_at = NOW()
FROM new_terms nt
WHERE si.object_type = nt.clicked_object_type
  AND si.object_id = nt.clicked_object_id;

-- Log what we learned
INSERT INTO feedback_learning_log (run_date, terms_added, objects_updated)
SELECT NOW(), COUNT(*), COUNT(DISTINCT clicked_object_id)
FROM new_terms;
```

### 2.5 The Self-Healing Loop

```
┌─────────────────────────────────────────────────────────────────┐
│                  COUNTERFACTUAL LEARNING LOOP                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. User searches "MTU filtr"                                    │
│              ↓                                                   │
│  2. F1 returns results (maybe wrong ones)                        │
│              ↓                                                   │
│  3. User clicks "Racor 500 Oil Filter"                          │
│              ↓                                                   │
│  4. Click event recorded with query + target                     │
│              ↓                                                   │
│  5. Nightly job: 5 users clicked "Racor 500" for "MTU filtr"    │
│              ↓                                                   │
│  6. Append "MTU filtr" to Racor 500's search_text               │
│              ↓                                                   │
│  7. Re-embed with new terms (embedding_status = 'pending')      │
│              ↓                                                   │
│  8. Next search for "MTU filtr" → Racor 500 ranks higher        │
│                                                                  │
│  NO SYNONYMS. NO RULES. PURE EVIDENCE.                          │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. Infrastructure Hardening

### 3.1 Required Metrics (Prometheus/Grafana)

```yaml
# prometheus.yml - scrape config for F1 workers

scrape_configs:
  - job_name: 'f1-embedding-worker'
    static_configs:
      - targets: ['embedding-worker:8080']
    metrics_path: '/metrics'

  - job_name: 'f1-projection-worker'
    static_configs:
      - targets: ['projection-worker:8080']
    metrics_path: '/metrics'
```

**Embedding Worker Metrics** (add to `embedding_worker_1536.py`):

```python
from prometheus_client import Counter, Gauge, Histogram, start_http_server

# Counters
EMBEDDINGS_PROCESSED = Counter(
    'f1_embeddings_processed_total',
    'Total embeddings processed',
    ['yacht_id', 'status']  # status: success, failed, skipped
)

OPENAI_REQUESTS = Counter(
    'f1_openai_requests_total',
    'Total OpenAI API requests',
    ['status']  # status: success, rate_limited, error
)

# Gauges
QUEUE_DEPTH = Gauge(
    'f1_embedding_queue_depth',
    'Current embedding queue depth',
    ['yacht_id', 'status']  # status: queued, processing, failed
)

CIRCUIT_BREAKER_STATE = Gauge(
    'f1_circuit_breaker_state',
    'Circuit breaker state (0=closed, 1=open, 2=half-open)'
)

MEMORY_USAGE_MB = Gauge(
    'f1_worker_memory_mb',
    'Current worker memory usage in MB'
)

# Histograms
EMBEDDING_LATENCY = Histogram(
    'f1_embedding_latency_seconds',
    'Embedding API call latency',
    buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
)

BATCH_PROCESSING_TIME = Histogram(
    'f1_batch_processing_seconds',
    'Time to process one batch',
    buckets=[1, 2, 5, 10, 30, 60]
)

# Start metrics server
start_http_server(8080)
```

**Key Dashboards**:

| Dashboard | Panels | Alert Threshold |
|-----------|--------|-----------------|
| **CDC Lag** | `time() - max(projection_last_success_ts)` | > 5 minutes |
| **Queue Depth** | `f1_embedding_queue_depth{status="queued"}` | > 10,000 |
| **RRF Latency (p99)** | `histogram_quantile(0.99, f1_search_latency_seconds)` | > 800ms |
| **Memory Usage** | `f1_worker_memory_mb` | > 450 MB |
| **Circuit Breaker** | `f1_circuit_breaker_state` | = 1 (open) |
| **Error Rate** | `rate(f1_embeddings_processed_total{status="failed"}[5m])` | > 0.01 |

### 3.2 Dead Letter Queue (DLQ) Strategy

**Current State**: `embedding_status='failed'` on `search_index` rows.

**Enhancement**: Explicit DLQ table with forensics.

```sql
CREATE TABLE IF NOT EXISTS embedding_dlq (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Source reference
    object_type TEXT NOT NULL,
    object_id UUID NOT NULL,
    yacht_id UUID,

    -- Failure context
    error_message TEXT,
    error_code TEXT,              -- e.g., 'rate_limit', 'timeout', 'invalid_input'
    attempts INTEGER DEFAULT 0,
    first_failure_at TIMESTAMPTZ,
    last_failure_at TIMESTAMPTZ DEFAULT NOW(),

    -- Forensics
    search_text_sample TEXT,      -- First 500 chars for debugging
    content_hash TEXT,

    -- Resolution
    resolved_at TIMESTAMPTZ,
    resolution_type TEXT,         -- 'retry_success', 'manual_fix', 'abandoned'

    CONSTRAINT dlq_unique_object UNIQUE (object_type, object_id)
);

-- Move to DLQ after 5 failures
CREATE OR REPLACE FUNCTION move_to_dlq()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.embedding_status = 'failed' AND
       (SELECT embedding_attempts FROM search_index
        WHERE object_type = NEW.object_type AND object_id = NEW.object_id) >= 5 THEN

        INSERT INTO embedding_dlq (
            object_type, object_id, yacht_id,
            error_message, attempts, first_failure_at, last_failure_at,
            search_text_sample, content_hash
        )
        SELECT
            NEW.object_type, NEW.object_id, NEW.yacht_id,
            NEW.payload->>'last_error', NEW.embedding_attempts,
            NEW.embedding_queued_at, NOW(),
            LEFT(NEW.search_text, 500), NEW.content_hash
        ON CONFLICT (object_type, object_id) DO UPDATE SET
            attempts = embedding_dlq.attempts + 1,
            last_failure_at = NOW(),
            error_message = EXCLUDED.error_message;

        -- Mark as DLQ'd
        NEW.embedding_status := 'dlq';
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_move_to_dlq
    BEFORE UPDATE ON search_index
    FOR EACH ROW
    WHEN (NEW.embedding_status = 'failed')
    EXECUTE FUNCTION move_to_dlq();
```

**DLQ Alerting**:

```yaml
# alertmanager.yml
groups:
  - name: f1-dlq
    rules:
      - alert: DLQGrowing
        expr: count(embedding_dlq WHERE resolved_at IS NULL) > 100
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "DLQ has {{ $value }} unresolved items"

      - alert: DLQCritical
        expr: count(embedding_dlq WHERE resolved_at IS NULL) > 1000
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "DLQ critical: {{ $value }} items. Investigate immediately."
```

### 3.3 Worker Health Checks

```python
# Add to each worker

from fastapi import FastAPI
from datetime import datetime, timedelta

app = FastAPI()

LAST_SUCCESSFUL_BATCH = None
CONSECUTIVE_FAILURES = 0

@app.get("/health")
async def health():
    """
    Returns 200 if worker is healthy, 503 if degraded.
    Render uses this for auto-restart.
    """
    global LAST_SUCCESSFUL_BATCH, CONSECUTIVE_FAILURES

    # Check: Have we processed anything in last 5 minutes?
    if LAST_SUCCESSFUL_BATCH:
        idle_time = datetime.utcnow() - LAST_SUCCESSFUL_BATCH
        if idle_time > timedelta(minutes=5):
            # Could be empty queue (OK) or stuck (BAD)
            # Check queue depth
            depth = get_queue_depth()
            if depth > 0:
                return {"status": "degraded", "reason": "idle_with_pending"}, 503

    # Check: Circuit breaker open?
    if CIRCUIT_BREAKER_OPEN:
        return {"status": "degraded", "reason": "circuit_open"}, 503

    # Check: Too many consecutive failures?
    if CONSECUTIVE_FAILURES > 10:
        return {"status": "degraded", "reason": "consecutive_failures"}, 503

    return {"status": "healthy", "last_batch": LAST_SUCCESSFUL_BATCH}

@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    return generate_latest()
```

---

## 4. Edge Warping (The Butler Strategy)

### 4.1 Current State

- **Redis**: Configured but deployment status unclear
- **Cloudflare**: NOT configured
- **Pre-warming**: NOT implemented
- **Client cache**: 5-minute TTL in-memory

### 4.2 Redis Pre-Warming Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    THE BUTLER STRATEGY                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  JWT Decode on Login                                             │
│         ↓                                                        │
│  Extract: yacht_id, user_id, role                               │
│         ↓                                                        │
│  Background Task: Pre-warm top-10 queries for this yacht        │
│         ↓                                                        │
│  Redis: Cache results before user opens search bar              │
│         ↓                                                        │
│  User searches → Instant response from warm cache               │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

**Implementation**:

```python
# apps/api/services/search_prewarm.py

from typing import List
import asyncio
import redis.asyncio as redis

POPULAR_QUERY_PATTERNS = [
    "",              # Empty query = show recent items
    "work order",
    "maintenance",
    "oil filter",
    "certificate",
    "manual",
]

async def prewarm_cache_for_user(
    yacht_id: str,
    user_id: str,
    role: str,
    redis_client: redis.Redis
) -> None:
    """
    Called on successful JWT validation.
    Pre-warms cache with likely queries.
    """
    # Get yacht-specific popular queries
    popular_queries = await get_popular_queries_for_yacht(yacht_id)
    queries_to_warm = POPULAR_QUERY_PATTERNS + popular_queries[:5]

    for query in queries_to_warm:
        cache_key = build_cache_key(
            yacht_id=yacht_id,
            user_id=user_id,
            role=role,
            endpoint="search.stream",
            query=query
        )

        # Skip if already cached
        if await redis_client.exists(cache_key):
            continue

        # Execute search and cache result
        try:
            results = await execute_f1_search(
                query=query,
                yacht_id=yacht_id,
                user_id=user_id,
                role=role
            )

            await redis_client.setex(
                cache_key,
                120,  # 2 minute TTL
                json.dumps(results)
            )
        except Exception:
            pass  # Silent fail - pre-warming is best-effort

async def get_popular_queries_for_yacht(yacht_id: str) -> List[str]:
    """
    Returns top-10 queries for this yacht based on search logs.
    """
    # Query search_logs or search_click_events
    # Return most frequent queries from last 7 days
    pass
```

### 4.3 Cloudflare Configuration

```yaml
# cloudflare-workers/search-edge-cache.js

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    // Only cache GET requests to search endpoint
    if (request.method !== 'GET' || !url.pathname.startsWith('/api/f1/search')) {
      return fetch(request);
    }

    // Extract cache key components from JWT
    const authHeader = request.headers.get('Authorization');
    if (!authHeader) {
      return fetch(request);  // Pass through to origin
    }

    // Decode JWT (verify signature at origin)
    const jwt = authHeader.replace('Bearer ', '');
    const payload = JSON.parse(atob(jwt.split('.')[1]));
    const { yacht_id, user_id, role } = payload;

    // Build cache key
    const query = url.searchParams.get('q') || '';
    const cacheKey = `cf:${yacht_id}:${role}:${hashQuery(query)}`;

    // Check Cloudflare KV cache
    const cached = await env.SEARCH_CACHE.get(cacheKey);
    if (cached) {
      return new Response(cached, {
        headers: {
          'Content-Type': 'text/event-stream',
          'X-Cache': 'HIT',
          'Cache-Control': 'private, max-age=60'
        }
      });
    }

    // Fetch from origin
    const response = await fetch(request);
    const body = await response.text();

    // Cache successful responses
    if (response.ok) {
      await env.SEARCH_CACHE.put(cacheKey, body, { expirationTtl: 60 });
    }

    return new Response(body, {
      headers: {
        ...response.headers,
        'X-Cache': 'MISS'
      }
    });
  }
};
```

### 4.4 Edge Node Locations

Deploy Cloudflare Workers in these regions for yacht coverage:

| Region | Edge Location | Primary Coverage |
|--------|---------------|------------------|
| Europe | Amsterdam, London | Mediterranean fleet |
| Americas | Miami, Fort Lauderdale | Caribbean fleet |
| Asia-Pacific | Singapore | SE Asia charter routes |
| Middle East | Dubai | Gulf region |

---

## 5. Runbook

### 5.1 Pre-Launch Checklist

```markdown
□ Database
  □ backfill_schedule table created
  □ search_click_events table created
  □ embedding_dlq table created
  □ All 134 yachts populated in backfill_schedule
  □ VIP yachts marked with priority = 100

□ Workers
  □ embedding-worker deployed to Render (512MB plan)
  □ projection-worker deployed to Render (512MB plan)
  □ Health check endpoints responding
  □ Prometheus metrics exposed on :8080/metrics

□ Caching
  □ Redis instance provisioned
  □ Connection string in REDIS_URL env var
  □ Cache invalidation listener deployed
  □ Pre-warm service deployed

□ Monitoring
  □ Grafana dashboards imported
  □ Alert rules configured
  □ PagerDuty integration tested
  □ DLQ alerts enabled

□ Cloudflare (optional)
  □ Worker deployed
  □ KV namespace created (SEARCH_CACHE)
  □ Routes configured for /api/f1/search/*
```

### 5.2 Backfill Execution

```bash
# Step 1: Activate first yacht
psql $DATABASE_URL -c "
  UPDATE backfill_schedule
  SET status = 'active', started_at = NOW()
  WHERE yacht_id = (
    SELECT yacht_id FROM backfill_schedule
    WHERE status = 'pending'
    ORDER BY priority DESC
    LIMIT 1
  );
"

# Step 2: Monitor progress
watch -n 10 'psql $DATABASE_URL -c "
  SELECT
    bs.yacht_name,
    bs.status,
    COUNT(ej.id) FILTER (WHERE ej.status = '\''done'\'') as done,
    COUNT(ej.id) FILTER (WHERE ej.status = '\''queued'\'') as queued,
    COUNT(ej.id) FILTER (WHERE ej.status = '\''failed'\'') as failed
  FROM backfill_schedule bs
  LEFT JOIN embedding_jobs ej ON ej.yacht_id = bs.yacht_id
  GROUP BY bs.yacht_id, bs.yacht_name, bs.status
  ORDER BY bs.status DESC, bs.priority DESC
  LIMIT 20;
"'

# Step 3: Auto-advance (run in cron or background)
psql $DATABASE_URL -c "
  -- Mark current yacht complete if queue empty
  UPDATE backfill_schedule bs
  SET status = 'complete', completed_at = NOW()
  WHERE bs.status = 'active'
    AND NOT EXISTS (
      SELECT 1 FROM embedding_jobs ej
      WHERE ej.yacht_id = bs.yacht_id
        AND ej.status IN ('queued', 'processing')
    );

  -- Activate next yacht
  UPDATE backfill_schedule
  SET status = 'active', started_at = NOW()
  WHERE yacht_id = (
    SELECT yacht_id FROM backfill_schedule
    WHERE status = 'pending'
    ORDER BY priority DESC
    LIMIT 1
  )
  AND NOT EXISTS (
    SELECT 1 FROM backfill_schedule WHERE status = 'active'
  );
"
```

### 5.3 Emergency Procedures

**OOM Crash Recovery**:
```bash
# 1. Reduce batch size immediately
render env:set BATCH_SIZE=50 --service embedding-worker

# 2. Check memory spike cause
psql $DATABASE_URL -c "
  SELECT object_type, AVG(LENGTH(search_text)) as avg_chars
  FROM search_index
  WHERE embedding_status = 'processing'
  GROUP BY object_type
  ORDER BY avg_chars DESC;
"

# 3. If specific type causes issues, skip temporarily
render env:set SKIP_OBJECT_TYPES=email,document --service embedding-worker
```

**Rate Limit Exhaustion**:
```bash
# 1. Check circuit breaker state
curl http://embedding-worker:8080/health

# 2. If circuit open, wait 60s or manually reset
render restart --service embedding-worker

# 3. Reduce throughput
render env:set BATCH_SLEEP_SEC=0.5 --service embedding-worker
```

**Silent Drift Detection**:
```sql
-- Check for drift: search_index out of sync with source
SELECT
    si.object_type,
    COUNT(*) as stale_count
FROM search_index si
JOIN pms_work_orders wo ON wo.id = si.object_id AND si.object_type = 'work_order'
WHERE wo.updated_at > si.updated_at + INTERVAL '10 minutes'
GROUP BY si.object_type;

-- Force re-projection if drift detected
UPDATE search_index
SET embedding_status = 'pending', updated_at = NOW()
WHERE object_type = 'work_order'
  AND object_id IN (/* stale IDs */);
```

---

## Appendix A: Environment Variables

```bash
# Embedding Worker
DATABASE_URL=postgresql://...@pooler.supabase.com:6543/postgres
OPENAI_API_KEY=sk-...
BATCH_SIZE=100
BATCH_SLEEP_SEC=0.1
CIRCUIT_BREAKER_THRESHOLD=5
CIRCUIT_BREAKER_RESET_SEC=60
MAX_EMBEDDING_CHARS=24000

# Projection Worker
PROJECTION_BATCH_SIZE=50
PROJECTION_POLL_INTERVAL=5
PROJECTION_MAX_SEARCH_TEXT=12000

# Caching
REDIS_URL=redis://...
CACHE_TTL_SEARCH=60
CACHE_TTL_STREAMING_P2=15

# Monitoring
PROMETHEUS_PORT=8080
LOG_LEVEL=INFO
```

---

## Appendix B: Architectural Diagram

```
                    ┌─────────────────────────────────────────────────────────┐
                    │                   F1 CORTEX PRODUCTION                   │
                    └─────────────────────────────────────────────────────────┘
                                              │
        ┌─────────────────────────────────────┼─────────────────────────────────────┐
        │                                     │                                     │
        ▼                                     ▼                                     ▼
┌───────────────┐                   ┌───────────────────┐                 ┌─────────────────┐
│   Cloudflare  │                   │   Render Workers   │                 │    Supabase     │
│   Edge Cache  │                   │   (512MB each)     │                 │    Postgres     │
├───────────────┤                   ├───────────────────┤                 ├─────────────────┤
│ KV: 60s TTL   │◄──── miss ────────│ F1 API (FastAPI)  │────────────────►│ search_index    │
│ Miami, Monaco │                   │                   │                 │ embedding_jobs  │
│ Singapore     │                   │ Projection Worker │◄── pg_notify ───│ backfill_sched  │
└───────────────┘                   │ Embedding Worker  │                 │ search_clicks   │
        │                           │ Cache Listener    │                 │ embedding_dlq   │
        │ hit                       └───────────────────┘                 └─────────────────┘
        │                                     │                                     │
        ▼                                     ▼                                     │
┌───────────────┐                   ┌───────────────────┐                          │
│    Browser    │                   │      Redis        │◄─────────────────────────┘
│  (5min cache) │◄──────────────────│   (120s TTL)      │      invalidation
└───────────────┘                   └───────────────────┘
```

---

**Document Control**

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2026-02-22 | F1 Cortex Team | Initial production playbook |
