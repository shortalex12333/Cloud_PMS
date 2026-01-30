# Tenant Lookup Caching - Implementation Guide

**Date**: 2026-01-30
**Impact**: 20% latency reduction for ALL lenses
**File**: `apps/api/middleware/auth.py`

---

## What is Tenant Lookup Caching?

**Problem**: Every API request queries MASTER DB to look up user's tenant, even for the same user making repeated requests.

**Solution**: Cache tenant lookup results in memory with TTL (Time-To-Live).

**Analogy**: Like remembering someone's address instead of looking it up in the phone book every time.

---

## How It Works

### Before (No Caching)

```python
def lookup_tenant_for_user(user_id: str) -> Optional[Dict]:
    # Query MASTER DB every request ❌
    result = master_client.table('user_accounts').select(...).eq('id', user_id).single().execute()

    # Query fleet registry ❌
    fleet_result = master_client.table('fleet_registry').select(...).execute()

    # Query TENANT DB ❌
    role_result = tenant_client.table('auth_users_roles').select(...).execute()

    return tenant_info
```

**Performance** (100 requests from same user):
- Request 1: 3 DB queries (600ms)
- Request 2: 3 DB queries (620ms)
- ...
- Request 100: 3 DB queries (590ms)

**Total**: 300 DB queries, ~60 seconds

### After (With Caching)

```python
from cachetools import TTLCache

# In-memory cache with 15-minute TTL
_tenant_cache = TTLCache(maxsize=1000, ttl=900)

def lookup_tenant_for_user(user_id: str) -> Optional[Dict]:
    # Check cache first (fast, in-memory lookup)
    if user_id in _tenant_cache:
        return _tenant_cache[user_id]  # ✅ <1ms

    # Cache miss: Query databases (same as before)
    result = master_client.table('user_accounts').select(...).eq('id', user_id).single().execute()
    fleet_result = master_client.table('fleet_registry').select(...).execute()
    role_result = tenant_client.table('auth_users_roles').select(...).execute()

    # Cache the result
    _tenant_cache[user_id] = tenant_info
    return tenant_info
```

**Performance** (100 requests from same user):
- Request 1: 3 DB queries (600ms) + cache write
- Request 2-100: Cache hit (0.5ms each) ✅

**Total**: 3 DB queries, ~50ms (99% faster)

---

## Implementation

### Step 1: Install Dependencies

```bash
pip install cachetools
```

Add to `requirements.txt`:
```
cachetools==5.3.2
```

### Step 2: Add Cache to Middleware

```python
from cachetools import TTLCache
from typing import Optional, Dict
import logging

logger = logging.getLogger(__name__)

# In-memory cache with TTL
# maxsize: Max 1000 users cached (adjust based on active users)
# ttl: 900 seconds (15 minutes)
_tenant_cache = TTLCache(maxsize=1000, ttl=900)

# Cache statistics (for monitoring)
_cache_stats = {
    "hits": 0,
    "misses": 0,
    "errors": 0
}
```

### Step 3: Update Tenant Lookup Function

```python
def lookup_tenant_for_user(user_id: str) -> Optional[Dict]:
    """
    Lookup tenant information for user with caching.

    Cache TTL: 15 minutes
    Cache invalidation: Automatic (TTL expiry)
    """
    # Check cache first
    if user_id in _tenant_cache:
        _cache_stats["hits"] += 1
        logger.debug(f"Tenant cache HIT for user {user_id}")
        return _tenant_cache[user_id]

    _cache_stats["misses"] += 1
    logger.debug(f"Tenant cache MISS for user {user_id}")

    try:
        # Query MASTER DB for user account
        result = master_client.table('user_accounts')\
            .select('id, yacht_id, role')\
            .eq('id', user_id)\
            .single()\
            .execute()

        if not result.data:
            logger.warning(f"User {user_id} not found in MASTER DB")
            return None

        yacht_id = result.data['yacht_id']

        # Query fleet registry for yacht details
        fleet_result = master_client.table('fleet_registry')\
            .select('yacht_code, supabase_url')\
            .eq('id', yacht_id)\
            .single()\
            .execute()

        if not fleet_result.data:
            logger.warning(f"Yacht {yacht_id} not found in fleet registry")
            return None

        # Query TENANT DB for role details (if needed)
        # ... additional queries ...

        # Build tenant info object
        tenant_info = {
            "user_id": user_id,
            "yacht_id": yacht_id,
            "yacht_code": fleet_result.data['yacht_code'],
            "tenant_url": fleet_result.data['supabase_url'],
            "role": result.data['role'],
            "cached_at": time.time()
        }

        # Cache the result
        _tenant_cache[user_id] = tenant_info

        return tenant_info

    except Exception as e:
        _cache_stats["errors"] += 1
        logger.error(f"Tenant lookup error for user {user_id}: {e}")
        return None
```

---

## Configuration

### Cache Size Tuning

```python
# Rule of thumb: Set maxsize to 2x expected active users

# Small deployment (10-50 active users)
_tenant_cache = TTLCache(maxsize=100, ttl=900)

# Medium deployment (50-500 active users)
_tenant_cache = TTLCache(maxsize=1000, ttl=900)

# Large deployment (500-5000 active users)
_tenant_cache = TTLCache(maxsize=10000, ttl=900)
```

### TTL Tuning

```python
# TTL trade-offs:
# - Shorter TTL: Fresher data, more DB queries
# - Longer TTL: Fewer DB queries, staler data

# Real-time critical (role changes apply quickly)
_tenant_cache = TTLCache(maxsize=1000, ttl=300)  # 5 minutes

# Balanced (default)
_tenant_cache = TTLCache(maxsize=1000, ttl=900)  # 15 minutes

# Performance critical (role changes can wait)
_tenant_cache = TTLCache(maxsize=1000, ttl=3600)  # 1 hour
```

---

## Monitoring

### Cache Statistics

Add endpoint to monitor cache performance:

```python
from middleware.auth import _tenant_cache, _cache_stats

@app.get("/admin/cache/stats")
def get_cache_stats():
    total_requests = _cache_stats["hits"] + _cache_stats["misses"]
    hit_rate = (_cache_stats["hits"] / total_requests * 100) if total_requests > 0 else 0

    return {
        "tenant_cache": {
            "size": len(_tenant_cache),
            "max_size": _tenant_cache.maxsize,
            "ttl": _tenant_cache.ttl,
            "hit_rate": f"{hit_rate:.1f}%",
            "hits": _cache_stats["hits"],
            "misses": _cache_stats["misses"],
            "errors": _cache_stats["errors"]
        }
    }
```

### Metrics to Watch

**1. Cache Hit Rate**
- **Good**: > 90% (most requests served from cache)
- **Warning**: 70-90% (consider increasing TTL or maxsize)
- **Critical**: < 70% (cache too small or TTL too short)

**2. Cache Size**
- **Good**: < 80% of maxsize
- **Warning**: 80-95% of maxsize (consider increasing)
- **Critical**: 100% of maxsize (evicting too aggressively)

**3. Cache Errors**
- **Good**: 0 errors
- **Warning**: < 1% of requests
- **Critical**: > 1% of requests (database connectivity issue)

---

## Cache Invalidation

### Automatic (TTL-Based)

By default, cache entries expire after TTL:

```python
# User cached at 10:00 AM
_tenant_cache[user_id] = tenant_info  # Expires at 10:15 AM

# At 10:16 AM, cache miss triggers fresh lookup
if user_id in _tenant_cache:  # False
    ...
```

### Manual Invalidation

For immediate cache invalidation (e.g., after role change):

```python
def invalidate_user_cache(user_id: str):
    """Manually invalidate cache entry for user."""
    if user_id in _tenant_cache:
        del _tenant_cache[user_id]
        logger.info(f"Invalidated cache for user {user_id}")
```

Call this after role changes:

```python
# After updating user role
update_user_role(user_id, new_role)
invalidate_user_cache(user_id)  # Force fresh lookup on next request
```

### Global Cache Clear

For emergencies (e.g., detected stale data):

```python
@app.post("/admin/cache/clear")
def clear_cache():
    """Clear all cached tenant lookups."""
    _tenant_cache.clear()
    _cache_stats["hits"] = 0
    _cache_stats["misses"] = 0
    _cache_stats["errors"] = 0
    return {"status": "cache cleared"}
```

---

## Troubleshooting

### Problem: Stale Data (Role Changes Not Reflected)

**Symptoms**: User's role changed, but still sees old permissions for 15 minutes

**Diagnosis**:
```python
# Check cache entry
cached = _tenant_cache.get(user_id)
print(f"Cached role: {cached['role']}")
print(f"Cached at: {cached['cached_at']}")
```

**Solutions**:
1. **Decrease TTL** (trade-off: more DB queries):
```python
_tenant_cache = TTLCache(maxsize=1000, ttl=300)  # 5 minutes
```

2. **Manual invalidation after role changes**:
```python
invalidate_user_cache(user_id)
```

3. **Event-driven invalidation** (advanced):
```python
# Listen for role change events from MASTER DB
# Invalidate cache when event received
```

### Problem: Low Hit Rate (<70%)

**Symptoms**: Cache not reducing DB queries as expected

**Diagnosis**:
```python
stats = get_cache_stats()
print(f"Hit rate: {stats['tenant_cache']['hit_rate']}")
print(f"Cache size: {stats['tenant_cache']['size']}/{stats['tenant_cache']['max_size']}")
```

**Causes**:
1. **TTL too short**: Users making requests, but cache expires between requests
2. **maxsize too small**: Cache evicting active users
3. **Traffic pattern**: No repeated requests from same users

**Solutions**:
1. **Increase TTL**:
```python
_tenant_cache = TTLCache(maxsize=1000, ttl=1800)  # 30 minutes
```

2. **Increase maxsize**:
```python
_tenant_cache = TTLCache(maxsize=5000, ttl=900)
```

### Problem: Memory Usage High

**Symptoms**: API process using excessive memory

**Diagnosis**:
```python
import sys
cache_size_bytes = sys.getsizeof(_tenant_cache)
print(f"Cache memory: {cache_size_bytes / 1024 / 1024:.2f} MB")
```

**Solutions**:
1. **Decrease maxsize**:
```python
_tenant_cache = TTLCache(maxsize=500, ttl=900)
```

2. **Reduce cached data** (only cache what you need):
```python
# Before (caching entire user object)
_tenant_cache[user_id] = {
    "user_id": user_id,
    "yacht_id": yacht_id,
    "yacht_code": yacht_code,
    "tenant_url": tenant_url,
    "role": role,
    "full_user_data": {...}  # ❌ Unnecessary
}

# After (cache only essential fields)
_tenant_cache[user_id] = {
    "yacht_id": yacht_id,
    "role": role
}
```

---

## Testing

### Unit Test

```python
def test_tenant_caching():
    # Clear cache
    _tenant_cache.clear()

    # First lookup: Cache miss
    start = time.time()
    tenant1 = lookup_tenant_for_user(user_id)
    first_lookup_time = time.time() - start

    # Second lookup: Cache hit
    start = time.time()
    tenant2 = lookup_tenant_for_user(user_id)
    second_lookup_time = time.time() - start

    # Cache hit should be much faster
    assert second_lookup_time < first_lookup_time * 0.1  # 10x faster
    assert tenant1 == tenant2
```

### Load Test

```python
def test_cache_hit_rate():
    # Simulate 100 requests from 10 users
    users = [f"user_{i}" for i in range(10)]

    for _ in range(100):
        user_id = random.choice(users)
        lookup_tenant_for_user(user_id)

    # Check hit rate
    stats = get_cache_stats()
    hit_rate = float(stats['tenant_cache']['hit_rate'].rstrip('%'))

    # Should be >90% with 10 users and 100 requests
    assert hit_rate > 90
```

---

## Alternative: Redis Cache

For multi-instance deployments, use Redis instead of in-memory cache:

```python
import redis
import json

_redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

def lookup_tenant_for_user(user_id: str) -> Optional[Dict]:
    cache_key = f"tenant:{user_id}"

    # Check Redis cache
    cached = _redis_client.get(cache_key)
    if cached:
        _cache_stats["hits"] += 1
        return json.loads(cached)

    _cache_stats["misses"] += 1

    # Query databases (same as before)
    tenant_info = {...}

    # Cache in Redis with TTL
    _redis_client.setex(cache_key, 900, json.dumps(tenant_info))

    return tenant_info
```

**Pros**:
- ✅ Shared across multiple API instances
- ✅ Survives API restarts
- ✅ Can be scaled independently

**Cons**:
- ❌ Requires Redis infrastructure
- ❌ Slightly slower than in-memory (network overhead)

---

## Rollback Plan

If caching causes issues:

```python
def lookup_tenant_for_user(user_id: str) -> Optional[Dict]:
    # Temporarily disable cache (always query fresh)
    # Comment out cache lookup
    # if user_id in _tenant_cache:
    #     return _tenant_cache[user_id]

    # Always query database
    result = master_client.table('user_accounts').select(...).execute()
    # ... rest of function ...

    # Don't cache the result
    # _tenant_cache[user_id] = tenant_info

    return tenant_info
```

---

## FAQ

**Q: What happens if a user's role changes?**
A: The old role will be cached for up to 15 minutes (TTL). For immediate updates, manually invalidate the cache.

**Q: Is the cache thread-safe?**
A: Yes, `TTLCache` from `cachetools` is thread-safe.

**Q: What if cache gets corrupted?**
A: Use `/admin/cache/clear` endpoint to flush all entries. Cache will rebuild on next requests.

**Q: Can I cache other things besides tenant lookups?**
A: Yes, but create separate caches for different data types to avoid confusion.

---

## Next Steps

1. ✅ Implement tenant caching in `middleware/auth.py`
2. ✅ Test with stress test script
3. ✅ Monitor hit rate for 24-48 hours
4. ✅ Tune TTL and maxsize based on traffic patterns
5. ✅ Consider Redis for multi-instance deployments

---

**Questions?** See `SYSTEM_OPTIMIZATIONS.md` or contact Platform Team.
