# Performance Profiling - How to Find Bottlenecks

**Date**: 2026-01-30
**Purpose**: Guide for profiling your lens performance and identifying bottlenecks

---

## Overview

This guide shows you how to:
1. **Run stress tests** to measure performance
2. **Profile individual actions** to find bottlenecks
3. **Interpret results** and decide what to optimize

---

## Step 1: Baseline Stress Test

### Create Stress Test Script

**File**: `tests/stress/stress_YOUR_LENS_actions.py`

```python
#!/usr/bin/env python3
"""
Stress Test: YOUR_LENS Actions
===============================

Goal: >95% success rate, P95 <500ms
"""

import os
import sys
import time
import httpx
import uuid
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import Counter
import statistics

# Configuration
TEST_JWT = os.environ.get("TEST_JWT")
API_BASE_URL = "https://pipeline-core.int.celeste7.ai"  # Or your API URL
TOTAL_REQUESTS = 100
CONCURRENT = 10

if not TEST_JWT:
    print("ERROR: TEST_JWT environment variable not set")
    sys.exit(1)

print("=" * 80)
print("YOUR_LENS - Stress Test")
print("=" * 80)
print(f"API Base URL: {API_BASE_URL}")
print(f"Total Requests: {TOTAL_REQUESTS}")
print(f"Concurrent: {CONCURRENT}")
print("=" * 80)
print("")


def execute_action():
    """Execute a single action request."""
    start = time.time()

    headers = {
        "Authorization": f"Bearer {TEST_JWT}",
        "Content-Type": "application/json"
    }

    payload = {
        "action": "your_action_name",  # ← Change this
        "context": {},
        "payload": {
            # Your action payload
            "field1": f"Test {uuid.uuid4().hex[:8]}",
            "field2": "value",
            ...
        }
    }

    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                f"{API_BASE_URL}/v1/actions/execute",
                json=payload,
                headers=headers
            )

            elapsed_ms = (time.time() - start) * 1000

            return {
                "success": response.status_code == 200,
                "status_code": response.status_code,
                "latency_ms": elapsed_ms,
                "response": response.json() if response.status_code == 200 else response.text
            }
    except Exception as e:
        elapsed_ms = (time.time() - start) * 1000
        return {
            "success": False,
            "status_code": 0,
            "latency_ms": elapsed_ms,
            "error": str(e)
        }


# Execute stress test
print("Running stress test...")
results = []
success_count = 0
failure_count = 0
status_codes = Counter()
latencies = []

with ThreadPoolExecutor(max_workers=CONCURRENT) as executor:
    futures = [executor.submit(execute_action) for _ in range(TOTAL_REQUESTS)]

    for i, future in enumerate(as_completed(futures), 1):
        result = future.result()
        results.append(result)

        if result["success"]:
            success_count += 1
            print(f"  ✓ Request {i}/{TOTAL_REQUESTS}: {result['status_code']} ({result['latency_ms']:.1f}ms)")
        else:
            failure_count += 1
            print(f"  ✗ Request {i}/{TOTAL_REQUESTS}: {result['status_code']} ({result['latency_ms']:.1f}ms)")

        status_codes[result["status_code"]] += 1
        latencies.append(result["latency_ms"])

# Calculate statistics
success_rate = (success_count / TOTAL_REQUESTS) * 100
latencies.sort()

p50 = statistics.median(latencies)
p95_index = int(len(latencies) * 0.95)
p95 = latencies[p95_index] if p95_index < len(latencies) else latencies[-1]
p99_index = int(len(latencies) * 0.99)
p99 = latencies[p99_index] if p99_index < len(latencies) else latencies[-1]
max_latency = max(latencies)
min_latency = min(latencies)
avg_latency = statistics.mean(latencies)

# Print results
print("")
print("=" * 80)
print("Results Summary")
print("=" * 80)
print("")
print(f"Total Requests: {TOTAL_REQUESTS}")
print(f"Success: {success_count} ({success_rate:.1f}%)")
print(f"Failures: {failure_count} ({(failure_count / TOTAL_REQUESTS) * 100:.1f}%)")
print("")
print("Status Code Distribution:")
for code in sorted(status_codes.keys()):
    print(f"  {code}: {status_codes[code]}")
print("")
print("Latency Statistics (ms):")
print(f"  Min: {min_latency:.1f}")
print(f"  Avg: {avg_latency:.1f}")
print(f"  P50: {p50:.1f}")
print(f"  P95: {p95:.1f}")
print(f"  P99: {p99:.1f}")
print(f"  Max: {max_latency:.1f}")
print("")
print("=" * 80)
print("Target Metrics:")
print(f"  Success Rate: >95% .... {'✅ PASS' if success_rate > 95 else '❌ FAIL'} ({success_rate:.1f}%)")
print(f"  P95 Latency: <500ms ... {'✅ PASS' if p95 < 500 else '❌ FAIL'} ({p95:.1f}ms)")
print("=" * 80)
print("")

# Exit status
if success_rate > 95 and p95 < 500:
    print("🎉 STRESS TEST: PASSED")
    sys.exit(0)
else:
    print("❌ STRESS TEST: FAILED")
    sys.exit(1)
```

### Run Stress Test

```bash
# Get JWT
JWT=$(bash get_jwt.sh | jq -r '.access_token')

# Run stress test
TEST_JWT=$JWT python3 tests/stress/stress_YOUR_LENS_actions.py
```

### Interpret Results

**Success Rate**:
- ✅ **>95%**: Good, proceed to latency optimization
- ⚠️ **90-95%**: Acceptable but investigate failures
- ❌ **<90%**: Fix errors before optimizing latency

**P95 Latency**:
- ✅ **<500ms**: Excellent, no optimization needed
- ⚠️ **500-2000ms**: Could benefit from optimization
- ❌ **>2000ms**: Needs optimization (see Step 2)

---

## Step 2: Profile Individual Action

If stress test shows high latency, profile the action to find bottleneck.

### Create Profiling Script

**File**: `tests/profile/profile_your_action.py`

```python
#!/usr/bin/env python3
"""
Profile YOUR_ACTION Performance
================================

Breaks down where time is spent in a request.
"""

import os
import time
import httpx
import subprocess

TEST_JWT = os.environ.get("TEST_JWT")
if not TEST_JWT:
    print("ERROR: TEST_JWT not set")
    exit(1)

API_URL = "https://pipeline-core.int.celeste7.ai"

print("=" * 80)
print("Profiling YOUR_ACTION Request")
print("=" * 80)
print("")

# Test 1: Direct database operation (if applicable)
print("[1] Testing direct database operation...")
start = time.time()
result = subprocess.run([
    "psql",
    "-h", "YOUR_DB_HOST",
    "-U", "postgres",
    "-d", "postgres",
    "-p", "5432",
    "-c", """
SELECT * FROM your_rpc_function(...);
"""
], env={**os.environ, "PGPASSWORD": "YOUR_PASSWORD"}, capture_output=True)
direct_db_time = (time.time() - start) * 1000
print(f"   Direct DB time: {direct_db_time:.1f}ms")
if result.returncode == 0:
    print(f"   Status: ✅ SUCCESS")
else:
    print(f"   Status: ❌ FAILED")
    print(f"   Error: {result.stderr.decode()}")
print("")

# Test 2: Full API request
print("[2] Testing full API request...")
headers = {
    "Authorization": f"Bearer {TEST_JWT}",
    "Content-Type": "application/json"
}

payload = {
    "action": "your_action_name",
    "context": {},
    "payload": {
        # Your test payload
    }
}

start = time.time()
with httpx.Client(timeout=30.0) as client:
    response = client.post(
        f"{API_URL}/v1/actions/execute",
        json=payload,
        headers=headers
    )
api_total_time = (time.time() - start) * 1000

print(f"   Total API time: {api_total_time:.1f}ms")
print(f"   Status code: {response.status_code}")
if response.status_code == 200:
    print(f"   Status: ✅ SUCCESS")
else:
    print(f"   Status: ❌ FAILED")
    print(f"   Response: {response.text[:200]}")
print("")

# Calculate breakdown
print("=" * 80)
print("Performance Breakdown")
print("=" * 80)
print(f"Direct DB operation:          {direct_db_time:.1f}ms")
print(f"Full API request:             {api_total_time:.1f}ms")
print(f"")
print(f"Overhead (API - DB):          {api_total_time - direct_db_time:.1f}ms")
print(f"")
print("Estimated Breakdown:")
print(f"  - DB operation:              {direct_db_time:.1f}ms ({direct_db_time/api_total_time*100:.1f}%)")
print(f"  - API overhead:              {api_total_time - direct_db_time:.1f}ms ({(api_total_time - direct_db_time)/api_total_time*100:.1f}%)")
print("")
print("API Overhead includes:")
print("  - JWT validation")
print("  - Tenant lookup")
print("  - Network latency")
print("  - Audit log write")
print("  - Response serialization")
print("=" * 80)
```

### Run Profiling Script

```bash
TEST_JWT=$JWT python3 tests/profile/profile_your_action.py
```

### Interpret Profiling Results

**If API overhead > 70%**:
- System-level optimizations will help (connection pooling, caching)
- See `SYSTEM_OPTIMIZATIONS.md`

**If DB operation > 70%**:
- Optimize database queries (indexes, query structure)
- Consider denormalization if doing many JOINs

**Typical Breakdown** (after system optimizations):
- JWT validation: 10-50ms
- Tenant lookup: 1ms (cached) or 200-600ms (uncached)
- Network latency: 50-100ms per round trip
- DB operation: 50-200ms
- Audit log write: 1ms (async) or 200-400ms (sync)
- Response serialization: 1-10ms

---

## Step 3: Identify Bottleneck

### Common Bottlenecks and Solutions

#### 1. Tenant Lookup (200-600ms)

**Symptom**: API overhead high even for simple operations

**Check**:
```python
# Profile tenant lookup specifically
start = time.time()
lookup_tenant_for_user(user_id)
tenant_time = (time.time() - start) * 1000
print(f"Tenant lookup: {tenant_time:.1f}ms")
```

**Solution**: Implement tenant caching (see `TENANT_CACHING.md`)

**Expected improvement**: 200-600ms → 1ms (99% reduction)

---

#### 2. Database Connection (280-980ms)

**Symptom**: Each request takes 800-1000ms even for simple SELECTs

**Check**:
```python
# Profile connection creation
start = time.time()
client = create_client(tenant_url, service_key)
conn_time = (time.time() - start) * 1000
print(f"Connection time: {conn_time:.1f}ms")
```

**Solution**: Implement connection pooling (see `CONNECTION_POOLING.md`)

**Expected improvement**: 800ms → 1ms (99% reduction after first request)

---

#### 3. Audit Log Write (200-400ms)

**Symptom**: Mutating actions slow, but SELECTs fast

**Check**:
```python
# Profile audit log write
start = time.time()
_write_audit_log(db, payload)
audit_time = (time.time() - start) * 1000
print(f"Audit log: {audit_time:.1f}ms")
```

**Solution**: Implement async audit logging (see `ASYNC_AUDIT_LOGS.md`)

**Expected improvement**: 300ms → 1ms (99% reduction)

---

#### 4. Slow Database Queries

**Symptom**: DB operation takes >500ms

**Check**:
```sql
-- Enable query timing in PostgreSQL
\timing on

-- Run your query
SELECT * FROM pms_receiving WHERE ...;

-- Check execution plan
EXPLAIN ANALYZE
SELECT * FROM pms_receiving WHERE ...;
```

**Solutions**:
1. **Add indexes** (see `docs/database/INDEXES.md`)
2. **Optimize JOINs** (reduce number of joins)
3. **Use pagination** (LIMIT/OFFSET for large result sets)
4. **Denormalize** (if doing many expensive JOINs)

**Expected improvement**: Depends on query, typically 50-90% reduction

---

#### 5. Multiple Database Round Trips

**Symptom**: API overhead high, but individual queries fast

**Check**:
```python
# Count number of database calls
import logging
logging.basicConfig(level=logging.DEBUG)

# Run action and count DB queries in logs
execute_action()
```

**Solutions**:
1. **Batch queries** (combine SELECTs into single query with JOINs)
2. **Use RPC functions** (multiple operations in single call)
3. **Cache intermediate results** (if querying same data repeatedly)

**Expected improvement**: 3-4 round trips → 1 round trip (70% reduction)

---

## Step 4: Optimization Decision Matrix

| Bottleneck | Impact | Complexity | Benefits All Lenses? | Priority |
|------------|--------|------------|----------------------|----------|
| **Connection Pooling** | 70% reduction | Low | ✅ Yes | 🔴 High |
| **Tenant Caching** | 20% reduction | Low | ✅ Yes | 🔴 High |
| **Async Audit Logs** | 10% reduction | Low | ✅ Yes | 🟡 Medium |
| **Database Indexes** | 50% reduction | Low | Lens-specific | 🟡 Medium |
| **Query Optimization** | 30% reduction | Medium | Lens-specific | 🟢 Low |
| **RPC Functions** | Minimal | Medium | Pattern reusable | 🟢 Low |

**Recommendation**: Start with system-level optimizations (connection pooling, caching) before lens-specific optimizations.

---

## Step 5: Measure Improvement

After implementing optimizations, re-run stress test:

```bash
# Before optimization
TEST_JWT=$JWT python3 tests/stress/stress_YOUR_LENS_actions.py
# Result: P95 = 6500ms

# Implement optimizations (connection pooling, caching, async audit logs)

# After optimization
TEST_JWT=$JWT python3 tests/stress/stress_YOUR_LENS_actions.py
# Expected: P95 = 400-600ms (85-90% improvement)
```

### Document Improvements

Create summary document:

**File**: `docs/YOUR_LENS/PERFORMANCE_IMPROVEMENTS.md`

```markdown
# Performance Improvements - YOUR_LENS

**Date**: 2026-01-XX

## Results

### Before Optimization
- Success Rate: XX%
- P50 Latency: XXXXms
- P95 Latency: XXXXms
- P99 Latency: XXXXms

### After Optimization
- Success Rate: XX%
- P50 Latency: XXXms
- P95 Latency: XXXms
- P99 Latency: XXXms

## Optimizations Applied

1. ✅ Connection Pooling (system-level) - XX% improvement
2. ✅ Tenant Caching (system-level) - XX% improvement
3. ✅ Async Audit Logs (system-level) - XX% improvement
4. ✅ Database Indexes (lens-specific) - XX% improvement

## Lessons Learned

- [What you learned during optimization]
- [What would you do differently]
- [Recommendations for other lens teams]
```

---

## Tools and Scripts

### Quick Profiling One-Liner

```bash
# Profile API request latency
time curl -X POST https://pipeline-core.int.celeste7.ai/v1/actions/execute \
  -H "Authorization: Bearer $JWT" \
  -H "Content-Type: application/json" \
  -d '{"action":"your_action","context":{},"payload":{...}}'
```

### Database Query Profiling

```sql
-- Enable timing
\timing on

-- Profile specific query
EXPLAIN (ANALYZE, BUFFERS, VERBOSE)
SELECT * FROM pms_receiving
WHERE yacht_id = '...'
  AND status = 'draft';

-- Look for:
-- - Seq Scan (bad, add index)
-- - Index Scan (good)
-- - Execution time
-- - Buffers (shared hit = cache, read = disk)
```

### Network Latency Check

```bash
# Ping database server
ping -c 10 db.vzsohavtuotocgrfkfyd.supabase.co

# Average latency should be < 100ms for good performance
```

---

## FAQ

**Q: What should I optimize first?**
A: System-level optimizations (connection pooling, caching). They benefit all lenses and are low-hanging fruit.

**Q: My stress test shows 50% success rate. Should I optimize latency?**
A: No. Fix errors first (RLS issues, validation errors, etc.). Only optimize latency after achieving >90% success rate.

**Q: P95 is 600ms but P99 is 5000ms. What does this mean?**
A: You have outliers (1% of requests are very slow). Check for timeouts, retries, or occasional slow queries.

**Q: How do I profile a production deployment?**
A: Use APM tools (New Relic, Datadog) or add custom timing logs to your handlers. Don't run stress tests against production.

**Q: Can I use Python profilers (cProfile, py-spy)?**
A: Yes, but they won't show database or network latency. Use manual timing with `time.time()` for end-to-end profiling.

---

## Next Steps

1. ✅ Run stress test to establish baseline
2. ✅ If P95 > 500ms, run profiling script
3. ✅ Identify bottleneck using decision matrix
4. ✅ Implement optimization (start with system-level)
5. ✅ Re-run stress test to measure improvement
6. ✅ Document results

---

**Questions?** See `SYSTEM_OPTIMIZATIONS.md` or contact Platform Team.
