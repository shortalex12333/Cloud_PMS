# Day 6: Performance Testing - Complete

**Date:** 2026-02-11
**Status:** ⚠️ CRITICAL - Severe performance degradation under concurrency

---

## Test Summary

**File:** `test-automation/day6_performance_tests.py` (548 lines)
**Test Scenarios:** 4 load tests + baseline profiling
**Pass Rate:** 50.0% (2/4) - **MISLEADING, see analysis below**
**Critical Finding:** API fails under concurrent load

---

## Performance Results

### Baseline: Single Request Profiling
```
Total (measured): 1044.7ms
Total (API reported): 713.1ms
  - Embedding: 233.6ms (33%)
  - Fusion: 476.8ms (67%)
  - Network overhead: 331.6ms
```

**Analysis:** Single requests perform acceptably (<1s API time). Breakdown shows:
- Embedding generation takes ~234ms (external API call)
- Database fusion takes ~477ms (vector search + SQL)
- Network overhead ~332ms (reasonable for cloud deployment)

### 1. Sequential Requests (No Concurrency) ❌ FAIL
```
Requests: 10 (sequential, no parallelism)
Errors: 0
P95: 5751.9ms (target: <1500ms)
Min: 1145ms, Max: 6594ms
```

**Finding:** Even without concurrency, performance degrades significantly.
- First request: ~1145ms
- Last request: ~6594ms (5.7x slower!)
- Suggests resource accumulation issue (connections not closing, memory leak, etc.)

**Impact:** HIGH - Sequential degradation indicates systemic issue, not just concurrency problem.

### 2. Low Concurrency (5 workers, 20 requests) ❌ CRITICAL FAIL
```
Requests: 20 concurrent (5 workers)
Errors: 15 (75% failure rate!)
P95: 10051ms (target: <2000ms)

First 5 requests: ~7.2s each (successful)
Next 15 requests: TIMEOUT at 10s
```

**Finding:** API can only handle ~5 concurrent requests before timing out.
- First 5 requests completed in ~7.2s (already 3.6x slower than baseline)
- Remaining 15 requests hit 10s timeout
- 75% failure rate with just 5 concurrent workers

**Impact:** CRITICAL - Production system cannot handle even modest load.

### 3. Day 2 Reproduction (10 workers, 30 requests) ⚠️ FALSE PASS
```
Requests: 30 concurrent (10 workers)
Errors: 30 (100% failure rate!)
P95: 1054.9ms (target: <2000ms) ✅ "PASS"

Comparison to Day 2 P95 (8709ms): "87.9% improvement" ✅
```

**CRITICAL ANALYSIS:** This result is **MISLEADING**:
- Test shows "PASS" with P95 = 1055ms
- Shows "87.9% improvement" vs Day 2
- **BUT all 30 requests FAILED with errors!**

The measured latencies are error/failure times, not successful response times. The requests are failing FASTER than Day 2, which is why the P95 is lower. This is **not an improvement**—it's a complete failure.

**Actual Status:** COMPLETE FAILURE (100% error rate)

### 4. High Load (20 workers, 50 requests) ⚠️ FALSE PASS
```
Requests: 50 concurrent (20 workers)
Errors: 50 (100% failure rate!)
P95: 1702ms (target: <3000ms) ✅ "PASS"
```

**CRITICAL ANALYSIS:** Same issue as #3:
- Test shows "PASS" with P95 = 1702ms
- **BUT all 50 requests FAILED!**
- Again, measuring how fast the API rejects requests, not successful responses

**Actual Status:** COMPLETE FAILURE (100% error rate)

---

## Root Cause Analysis

### Problem: API Fails Under Concurrent Load

**Evidence:**
1. Single requests work fine (~1s)
2. Sequential requests degrade (1s → 6.5s over 10 requests)
3. Concurrent requests fail entirely (75-100% error rate)

**Hypothesis 1: Database Connection Pool Exhaustion** (MOST LIKELY)
- Supabase clients may not be pooling connections properly
- Each request creates new DB connection
- Pool limit reached = new requests timeout/fail
- Sequential degradation suggests connections not being released

**Hypothesis 2: Rate Limiting**
- Supabase or external embedding API may have rate limits
- Concurrent requests trigger rate limit
- Requests fail fast with 429/503 errors

**Hypothesis 3: Memory/Resource Leak**
- Sequential degradation suggests accumulation
- Embedding vectors not being garbage collected
- Database cursors not closing

### Investigation Needed

1. **Check Supabase connection pool settings**
   ```python
   # Current implementation (apps/api/pipeline_service.py:536)
   from supabase import create_client
   client = create_client(tenant_url, tenant_key)
   ```
   - Does `create_client()` use connection pooling?
   - What are the default pool limits?
   - Are connections being reused or created per request?

2. **Check embedding API rate limits**
   ```python
   # Location: rag/context_builder.py
   query_embedding = generate_query_embedding(request.query)
   ```
   - What service is generating embeddings?
   - Does it have rate limits?
   - Should we cache embeddings for repeated queries?

3. **Check for resource leaks**
   - Are database cursors being closed?
   - Are HTTP connections being pooled/reused?
   - Memory profiling under load

4. **Check error logs**
   - What errors are causing the 100% failure rate?
   - 429 Rate Limit Exceeded?
   - 503 Service Unavailable?
   - Connection timeout?
   - Database pool exhausted?

---

## Comparison: Day 2 vs Day 6

| Metric | Day 2 (Original) | Day 6 (Current) | Change |
|--------|------------------|-----------------|--------|
| **Concurrent Requests** | 10 | 10 | Same |
| **P95 Latency** | 8709ms | 1055ms | -87.9% ⚠️ |
| **Success Rate** | ~87% (13/15) | 0% (0/30) | -87% ❌ |
| **Error Count** | 2 | 30 | +1400% ❌ |

**Conclusion:** Day 6 shows WORSE performance than Day 2, despite lower P95. The API is now failing completely under load instead of being slow.

**Possible Explanations:**
1. Day 2 tests had longer timeout (allowing slow responses to succeed)
2. Day 6 tests triggered stricter rate limiting
3. Backend changes between Day 2 and Day 6 introduced regression
4. Day 2 tests were run at different time (lighter API load)

---

## Recommended Optimizations

### 1. Connection Pooling (CRITICAL) 🔴

**Problem:** Each request creates new Supabase connection

**Solution:** Implement proper connection pooling
```python
# apps/api/pipeline_service.py

from supabase import create_client
import asyncpg

# Global connection pools
_connection_pools = {}

async def get_tenant_pool(tenant_key_alias: str):
    """Get or create asyncpg connection pool for tenant."""
    if tenant_key_alias not in _connection_pools:
        tenant_url = os.environ.get(f'{tenant_key_alias}_SUPABASE_URL')

        # Extract PostgreSQL connection string from Supabase URL
        # Example: https://abc.supabase.co → postgresql://...
        pg_url = get_postgres_url_from_supabase(tenant_url)

        pool = await asyncpg.create_pool(
            pg_url,
            min_size=5,
            max_size=20,
            command_timeout=10,
        )
        _connection_pools[tenant_key_alias] = pool

    return _connection_pools[tenant_key_alias]
```

**Expected Impact:**
- Reduce connection overhead from ~500ms to ~50ms
- Eliminate connection pool exhaustion errors
- Support 20+ concurrent requests

### 2. Query Embedding Caching (HIGH) 🟡

**Problem:** Same queries generate embeddings repeatedly

**Solution:** Cache embeddings with Redis/in-memory LRU
```python
from functools import lru_cache
import hashlib

@lru_cache(maxsize=1000)
def get_cached_embedding(query: str):
    """Cache embeddings for frequently searched queries."""
    return generate_query_embedding(query)
```

**Expected Impact:**
- Reduce embedding time from ~234ms to ~0ms for cached queries
- Support higher throughput for common searches
- Reduce external API costs

### 3. Database Query Optimization (MEDIUM) 🟢

**Problem:** Fusion query takes ~477ms

**Solution:** Optimize `f1_search_fusion` function
- Add database indexes on frequently queried columns
- Optimize vector similarity search
- Reduce JOIN complexity

**Expected Impact:**
- Reduce fusion time from ~477ms to ~200ms
- Better scalability under load

### 4. Rate Limiting & Throttling (MEDIUM) 🟢

**Problem:** No backpressure when overloaded

**Solution:** Implement graceful degradation
```python
from fastapi_limiter import FastAPILimiter
from fastapi_limiter.depends import RateLimiter

@app.post("/search")
@limiter.limit("30/minute")  # 30 requests per minute per user
async def search(...):
    ...
```

**Expected Impact:**
- Prevent cascade failures
- Return 429 status instead of timeouts
- Protect backend from overload

---

## Performance Targets

### Current State (Day 6)
- Single request: ~1s ✅
- Sequential (10): P95 = 5.8s ❌
- Concurrent (5 workers): 75% failure ❌
- Concurrent (10 workers): 100% failure ❌

### Target State (After Optimization)
- Single request: <500ms (2x improvement)
- Sequential (10): P95 <1s (5.8x improvement)
- Concurrent (10 workers): P95 <2s, 0% errors (from 100% errors)
- Concurrent (20 workers): P95 <3s, 0% errors (from 100% errors)
- Sustained load: 10 RPS sustained for 60s

---

## Test Artifacts

### Logs
- `test-automation/logs/day6_performance_tests.log` (full output)

### Reports
- `test-automation/results/day6_performance_audit.json` (detailed metrics)

### Scripts
- `test-automation/day6_performance_tests.py` (test suite)

---

## Key Learnings

### 1. Fast Failures ≠ Good Performance ⚠️
- Lower latency with 100% errors is WORSE than higher latency with successes
- Always check error rates, not just P95
- "Improvement" metrics can be misleading

### 2. Sequential Degradation Indicates Resource Leaks 🔍
- Performance should be consistent for sequential requests
- Degradation (1s → 6.5s) suggests accumulation issue
- Likely cause: connections not closing, memory not freeing

### 3. Concurrency Amplifies Bottlenecks 📈
- Single request: ~1s ✅
- 5 concurrent: ~7s each (7x slower) ❌
- Issue is not inherent slowness, but lack of parallelization

### 4. Connection Pooling is Critical for APIs 🏊
- Without pooling: each request = new connection overhead
- With pooling: connections reused, overhead amortized
- Essential for production scalability

### 5. Always Test Under Load 💪
- Single request tests don't reveal concurrency issues
- Production APIs will face concurrent load
- Day 2 caught this, Day 6 quantified it

---

## Next Steps

### Immediate Actions (Critical)
1. ❗ Investigate error logs to understand why requests are failing
2. ❗ Implement connection pooling for Supabase clients
3. ❗ Add embedding caching to reduce external API calls

### Before Production
4. ❗ Re-run Day 6 tests after optimizations (target: 0% error rate)
5. ❗ Implement monitoring/alerting for P95 latency
6. ❗ Load test with realistic traffic patterns

### Day 7 Plan
- Apply connection pooling fix
- Add embedding caching
- Re-run all Day 2-6 tests
- Generate final 7-day report
- Production readiness assessment

---

## Verdict

**Status:** ⚠️ CRITICAL PERFORMANCE ISSUES IDENTIFIED

**Summary:**
- API works for single requests (~1s)
- Completely fails under concurrent load (75-100% error rate)
- Root cause: Likely database connection pool exhaustion
- Fix required BEFORE production deployment

**Impact:** HIGH - Current system cannot handle production traffic. Users would experience:
- Timeouts on search requests
- Failed actions
- Degraded experience under any meaningful load

**Priority:** CRITICAL - Fix connection pooling before proceeding to production.

**Next:** Implement connection pooling optimization, then re-run Day 6 tests.
