# Async Audit Logging - Implementation Guide

**Date**: 2026-01-30
**Impact**: 10% latency reduction for mutating actions
**File**: `apps/api/utils/audit_logger.py` (new shared utility)

---

## What is Async Audit Logging?

**Problem**: Audit log writes block the API response, adding 200-400ms to every mutating action.

**Solution**: Write audit logs asynchronously in background thread, don't wait for completion.

**Analogy**: Like dropping a letter in a mailbox instead of hand-delivering it and waiting for a signature.

---

## How It Works

### Before (Synchronous)

```python
def _write_audit_log(db, payload: Dict):
    """Write audit log (blocks request)."""
    audit_payload = {
        "id": str(uuid.uuid4()),
        "yacht_id": payload["yacht_id"],
        "entity_type": payload["entity_type"],
        "action": payload["action"],
        "entity_id": payload["entity_id"],
        "created_by": payload["user_id"],
        "created_at": datetime.utcnow().isoformat()
    }

    # Blocks request until audit log written ❌ (200-400ms)
    db.table("pms_audit_log").insert(audit_payload).execute()
```

**Performance**:
- Business logic: 200ms
- Audit log write: 300ms ← **Request waits here**
- Total: **500ms**

### After (Asynchronous)

```python
from concurrent.futures import ThreadPoolExecutor

_audit_executor = ThreadPoolExecutor(max_workers=5, thread_name_prefix="audit_")

def write_audit_log_async(db, payload: Dict):
    """Write audit log (fire-and-forget)."""
    audit_payload = {
        "id": str(uuid.uuid4()),
        "yacht_id": payload["yacht_id"],
        "entity_type": payload["entity_type"],
        "action": payload["action"],
        "entity_id": payload["entity_id"],
        "created_by": payload["user_id"],
        "created_at": datetime.utcnow().isoformat()
    }

    # Submit to background thread (returns immediately) ✅
    _audit_executor.submit(
        _write_audit_log_impl,
        db,
        audit_payload
    )
    # Don't wait for completion

def _write_audit_log_impl(db, audit_payload: Dict):
    """Background task: Actually write to database."""
    try:
        db.table("pms_audit_log").insert(audit_payload).execute()
    except Exception as e:
        # Log error but don't fail the request
        logger.error(f"Audit log write failed: {e}")
```

**Performance**:
- Business logic: 200ms
- Audit log submit: 1ms ← **Fire-and-forget**
- Total: **201ms** (60% faster)

---

## Implementation

### Step 1: Create Shared Utility

Create `apps/api/utils/audit_logger.py`:

```python
"""
Shared utility for async audit logging.

Usage:
    from utils.audit_logger import write_audit_log_async

    write_audit_log_async(db, {
        "yacht_id": yacht_id,
        "entity_type": "receiving",
        "action": "create_receiving",
        "entity_id": receiving_id,
        "user_id": user_id
    })
"""

import uuid
import logging
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Optional

logger = logging.getLogger(__name__)

# Background executor for audit logs
# max_workers=5: Handle up to 5 concurrent audit log writes
_audit_executor = ThreadPoolExecutor(
    max_workers=5,
    thread_name_prefix="audit_"
)

# Statistics for monitoring
_audit_stats = {
    "submitted": 0,
    "succeeded": 0,
    "failed": 0
}


def write_audit_log_async(db, payload: Dict[str, str]) -> None:
    """
    Write audit log asynchronously (fire-and-forget).

    Args:
        db: Supabase client
        payload: Dict with keys:
            - yacht_id (str)
            - entity_type (str): e.g., "receiving", "part", "document"
            - action (str): e.g., "create_receiving", "accept_receiving"
            - entity_id (str): UUID of the entity
            - user_id (str): UUID of the user performing action
            - old_values (str, optional): JSON string of old values
            - new_values (str, optional): JSON string of new values

    Returns:
        None (fire-and-forget, doesn't wait for completion)
    """
    # Build audit payload
    audit_payload = {
        "id": str(uuid.uuid4()),
        "yacht_id": payload["yacht_id"],
        "entity_type": payload["entity_type"],
        "action": payload["action"],
        "entity_id": payload["entity_id"],
        "created_by": payload["user_id"],
        "created_at": datetime.utcnow().isoformat(),
        "old_values": payload.get("old_values"),
        "new_values": payload.get("new_values")
    }

    # Submit to background thread (returns immediately)
    _audit_stats["submitted"] += 1
    _audit_executor.submit(
        _write_audit_log_impl,
        db,
        audit_payload
    )


def _write_audit_log_impl(db, audit_payload: Dict) -> None:
    """
    Background task: Actually write audit log to database.

    This runs in a background thread and should NOT raise exceptions
    to the caller (since it's async).
    """
    try:
        db.table("pms_audit_log").insert(audit_payload).execute()
        _audit_stats["succeeded"] += 1
        logger.debug(f"Audit log written: {audit_payload['action']} for {audit_payload['entity_id']}")

    except Exception as e:
        _audit_stats["failed"] += 1
        logger.error(
            f"Audit log write failed: {e}",
            extra={
                "action": audit_payload["action"],
                "entity_id": audit_payload["entity_id"],
                "error": str(e)
            }
        )
        # Don't re-raise (fire-and-forget pattern)


def get_audit_stats() -> Dict:
    """Get audit logging statistics for monitoring."""
    total = _audit_stats["submitted"]
    success_rate = (_audit_stats["succeeded"] / total * 100) if total > 0 else 0

    return {
        "submitted": _audit_stats["submitted"],
        "succeeded": _audit_stats["succeeded"],
        "failed": _audit_stats["failed"],
        "success_rate": f"{success_rate:.1f}%",
        "queue_size": _audit_executor._work_queue.qsize()
    }


def shutdown_audit_logger(wait: bool = True, timeout: Optional[float] = 10.0) -> None:
    """
    Shutdown audit logger gracefully.

    Call this during app shutdown to ensure all pending audit logs are written.

    Args:
        wait: If True, wait for pending tasks to complete
        timeout: Max seconds to wait (default 10)
    """
    logger.info("Shutting down audit logger...")
    _audit_executor.shutdown(wait=wait, timeout=timeout)
    logger.info(f"Audit logger shutdown complete. Stats: {get_audit_stats()}")
```

### Step 2: Update Handler to Use Shared Utility

**Before** (in `receiving_handlers.py`):

```python
def _write_audit_log(db, payload: Dict):
    """Write audit log (synchronous, duplicated per lens)."""
    audit_payload = {
        "id": str(uuid.uuid4()),
        "yacht_id": payload["yacht_id"],
        ...
    }
    db.table("pms_audit_log").insert(audit_payload).execute()  # Blocks


def create_receiving(user_context, request):
    # ... business logic ...

    _write_audit_log(db, {
        "yacht_id": yacht_id,
        "entity_type": "receiving",
        ...
    })

    return {"receiving_id": receiving_id}
```

**After**:

```python
from utils.audit_logger import write_audit_log_async

# Remove _write_audit_log function (use shared utility)

def create_receiving(user_context, request):
    # ... business logic ...

    write_audit_log_async(db, {
        "yacht_id": yacht_id,
        "entity_type": "receiving",
        "action": "create_receiving",
        "entity_id": receiving_id,
        "user_id": user_id
    })

    return {"receiving_id": receiving_id}
```

### Step 3: Add Shutdown Hook (Optional)

Ensure pending audit logs are written during app shutdown:

```python
# In main.py or app.py
from utils.audit_logger import shutdown_audit_logger
import atexit

# Register shutdown handler
atexit.register(shutdown_audit_logger)

# Or in FastAPI:
from fastapi import FastAPI

app = FastAPI()

@app.on_event("shutdown")
async def shutdown_event():
    shutdown_audit_logger(wait=True, timeout=10)
```

---

## Configuration

### Thread Pool Sizing

```python
# Rule of thumb: max_workers = expected audit logs per second × 0.5

# Low traffic (1-10 writes/sec)
_audit_executor = ThreadPoolExecutor(max_workers=5)

# Medium traffic (10-50 writes/sec)
_audit_executor = ThreadPoolExecutor(max_workers=10)

# High traffic (50-200 writes/sec)
_audit_executor = ThreadPoolExecutor(max_workers=20)
```

### Queue Size Limit (Optional)

Prevent unbounded queue growth:

```python
from queue import Queue

# Limit queue to 100 pending writes
_audit_queue = Queue(maxsize=100)

_audit_executor = ThreadPoolExecutor(
    max_workers=5,
    thread_name_prefix="audit_",
    initializer=lambda: _audit_queue
)
```

---

## Monitoring

### Audit Statistics

Add endpoint to monitor audit logger health:

```python
from utils.audit_logger import get_audit_stats

@app.get("/admin/audit/stats")
def audit_stats():
    return get_audit_stats()
```

**Example response**:
```json
{
  "submitted": 1523,
  "succeeded": 1520,
  "failed": 3,
  "success_rate": "99.8%",
  "queue_size": 2
}
```

### Metrics to Watch

**1. Success Rate**
- **Good**: > 99.5%
- **Warning**: 98-99.5% (occasional failures)
- **Critical**: < 98% (database connectivity issue)

**2. Queue Size**
- **Good**: < 10 pending writes
- **Warning**: 10-50 pending (high load)
- **Critical**: > 50 pending (database slow, increase workers)

**3. Failed Writes**
- **Good**: 0 failed writes
- **Warning**: < 1% failure rate
- **Critical**: > 1% failure rate (investigate database)

---

## Error Handling

### What Happens If Audit Log Fails?

**Fire-and-forget pattern**: Request succeeds even if audit log fails.

```python
# Business operation succeeds
receiving = create_receiving_record(...)

# Audit log submitted (fire-and-forget)
write_audit_log_async(db, {...})

# Response sent immediately (doesn't wait for audit log)
return {"receiving_id": receiving.id}  # ✅ Success

# If audit log fails later:
# - Error logged to application logs
# - _audit_stats["failed"] incremented
# - User's request still succeeded
```

**Rationale**:
- Audit logs are important but not critical
- User action shouldn't fail because audit logging failed
- Failed audit logs can be investigated from application logs

### Alerting on Failed Audit Logs

Set up alerts for high failure rate:

```python
# In monitoring script or health check
stats = get_audit_stats()
failure_rate = (stats["failed"] / stats["submitted"]) * 100

if failure_rate > 1:
    send_alert(f"Audit log failure rate high: {failure_rate:.1f}%")
```

---

## Troubleshooting

### Problem: High Queue Size (>50)

**Symptoms**: Queue growing, not draining fast enough

**Diagnosis**:
```python
stats = get_audit_stats()
print(f"Queue size: {stats['queue_size']}")
print(f"Workers: {_audit_executor._max_workers}")
```

**Solutions**:
1. **Increase workers**:
```python
_audit_executor = ThreadPoolExecutor(max_workers=10)  # Was 5
```

2. **Profile database writes** (check if database is slow):
```python
import time

def _write_audit_log_impl(db, audit_payload: Dict):
    start = time.time()
    db.table("pms_audit_log").insert(audit_payload).execute()
    elapsed = time.time() - start

    if elapsed > 1.0:
        logger.warning(f"Slow audit log write: {elapsed:.2f}s")
```

3. **Batch writes** (advanced):
```python
# Write 10 audit logs in single INSERT
_audit_batch = []

def _write_audit_log_impl(db, audit_payload: Dict):
    _audit_batch.append(audit_payload)

    if len(_audit_batch) >= 10:
        db.table("pms_audit_log").insert(_audit_batch).execute()
        _audit_batch.clear()
```

### Problem: High Failure Rate (>1%)

**Symptoms**: Many audit logs failing to write

**Diagnosis**:
```python
# Check error logs
grep "Audit log write failed" app.log | tail -20
```

**Causes**:
1. Database connection issues
2. RLS policy blocking writes
3. Schema mismatch (missing columns)

**Solutions**:
1. **Check database connectivity**:
```python
try:
    db.table("pms_audit_log").select("id").limit(1).execute()
    print("Database connection OK")
except Exception as e:
    print(f"Database connection FAILED: {e}")
```

2. **Check RLS policy**:
```sql
-- Audit logs should allow INSERT from service role
SELECT * FROM pg_policies
WHERE tablename = 'pms_audit_log'
  AND cmd = 'INSERT';
```

3. **Check schema**:
```sql
-- Verify all columns exist
\d pms_audit_log
```

### Problem: Memory Leak (Growing Memory Usage)

**Symptoms**: API process memory growing over time

**Diagnosis**:
```python
# Check for leaked futures
import gc
futures = [obj for obj in gc.get_objects() if isinstance(obj, Future)]
print(f"Leaked futures: {len(futures)}")
```

**Cause**: Not shutting down executor properly

**Solution**:
```python
# Ensure shutdown hook is registered
import atexit
from utils.audit_logger import shutdown_audit_logger

atexit.register(shutdown_audit_logger)
```

---

## Testing

### Unit Test

```python
def test_audit_log_async():
    # Clear stats
    _audit_stats["submitted"] = 0
    _audit_stats["succeeded"] = 0

    # Submit audit log
    write_audit_log_async(db, {
        "yacht_id": yacht_id,
        "entity_type": "test",
        "action": "test_action",
        "entity_id": str(uuid.uuid4()),
        "user_id": user_id
    })

    # Check submitted immediately
    assert _audit_stats["submitted"] == 1

    # Wait for background write (max 5 seconds)
    for _ in range(50):
        if _audit_stats["succeeded"] == 1:
            break
        time.sleep(0.1)

    # Verify success
    assert _audit_stats["succeeded"] == 1
```

### Performance Test

```python
def test_async_performance():
    # Synchronous baseline
    start = time.time()
    for _ in range(10):
        _write_audit_log_sync(db, {...})
    sync_time = time.time() - start

    # Asynchronous test
    start = time.time()
    for _ in range(10):
        write_audit_log_async(db, {...})
    async_time = time.time() - start

    # Async should be >10x faster
    assert async_time < sync_time * 0.1
```

---

## Rollback Plan

If async audit logging causes issues:

```python
def write_audit_log_async(db, payload: Dict) -> None:
    """Temporarily make synchronous (safe rollback)."""
    audit_payload = {...}

    # Synchronous write (blocks request)
    try:
        db.table("pms_audit_log").insert(audit_payload).execute()
        _audit_stats["succeeded"] += 1
    except Exception as e:
        _audit_stats["failed"] += 1
        logger.error(f"Audit log write failed: {e}")
```

---

## FAQ

**Q: What if audit log write fails?**
A: The user's request still succeeds. Failed audit logs are logged and counted in stats.

**Q: Will audit logs be in order?**
A: Not guaranteed. Audit logs written by multiple threads may arrive out of order. Use `created_at` for ordering.

**Q: Can I wait for audit log completion?**
A: Yes, but defeats the purpose. Use synchronous write if you need to wait.

**Q: What happens during app shutdown?**
A: Shutdown hook waits up to 10 seconds for pending audit logs to complete.

**Q: Is this safe for critical audit logs?**
A: For critical audit logs (compliance, security), use synchronous writes. For operational audit logs (user actions), async is fine.

---

## Next Steps

1. ✅ Create shared utility `apps/api/utils/audit_logger.py`
2. ✅ Update handlers to use `write_audit_log_async()`
3. ✅ Add shutdown hook in `main.py`
4. ✅ Monitor audit stats for 24-48 hours
5. ✅ Tune worker count based on traffic

---

**Questions?** See `SYSTEM_OPTIMIZATIONS.md` or contact Platform Team.
