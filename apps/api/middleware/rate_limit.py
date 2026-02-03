#!/usr/bin/env python3
"""
F1 Search - Token Bucket Rate Limiting (per org)

Atomic token-bucket rate limiter using Redis Lua EVAL.
Falls back to fixed-window if EVAL is not available.

Usage:
    from middleware.rate_limit import OrgRateLimitMiddleware
    app.add_middleware(OrgRateLimitMiddleware)

Requires:
    REDIS_URL env var
    ORG_TOKENS_PER_SEC env var (default: 50)
    ORG_BURST_CAPACITY env var (default: 100)
"""

import os
import time
import logging

import aioredis
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL")
TOKENS_PER_SEC = int(os.getenv("ORG_TOKENS_PER_SEC", "50"))
BURST_CAPACITY = int(os.getenv("ORG_BURST_CAPACITY", "100"))

# Lua script for atomic token bucket
# Returns: [allowed (0/1), tokens_remaining, retry_after_ms]
TOKEN_BUCKET_LUA = """
local key = KEYS[1]
local capacity = tonumber(ARGV[1])
local refill_rate = tonumber(ARGV[2])
local now = tonumber(ARGV[3])
local requested = 1

local bucket = redis.call('HMGET', key, 'tokens', 'last_refill')
local tokens = tonumber(bucket[1]) or capacity
local last_refill = tonumber(bucket[2]) or now

-- Refill tokens based on time elapsed
local elapsed = now - last_refill
local refill = elapsed * refill_rate
tokens = math.min(capacity, tokens + refill)

-- Try to consume a token
if tokens >= requested then
    tokens = tokens - requested
    redis.call('HMSET', key, 'tokens', tokens, 'last_refill', now)
    redis.call('EXPIRE', key, 10)
    return {1, math.floor(tokens), 0}
else
    -- Calculate retry delay
    local needed = requested - tokens
    local retry_ms = math.ceil((needed / refill_rate) * 1000)
    redis.call('HMSET', key, 'tokens', tokens, 'last_refill', now)
    redis.call('EXPIRE', key, 10)
    return {0, 0, retry_ms}
end
"""


class OrgRateLimitMiddleware(BaseHTTPMiddleware):
    """
    Per-org rate limiting middleware.

    Uses Redis Lua EVAL for atomic token bucket.
    Falls back to fixed-window if EVAL fails.

    Only applies to F1 search stream start (not every SSE event).

    Headers added:
    - X-RateLimit-Limit: burst capacity
    - X-RateLimit-Remaining: tokens remaining
    - Retry-After: seconds until tokens available (on 429)
    """

    def __init__(self, app):
        super().__init__(app)
        self.redis = None
        self.eval_available = None  # None = untested, True/False = tested
        self.script_sha = None

    async def dispatch(self, request, call_next):
        # Only rate limit F1 search stream start
        path = request.url.path
        if not path.startswith("/api/f1/search/stream"):
            return await call_next(request)

        # Skip rate limiting if Redis not configured
        if not REDIS_URL:
            return await call_next(request)

        # Lazy init Redis connection
        if not self.redis:
            try:
                self.redis = await aioredis.from_url(REDIS_URL, decode_responses=True)
                logger.info("[RateLimit] Redis connected")
            except Exception as e:
                logger.error(f"[RateLimit] Redis connection failed: {e}")
                return await call_next(request)

        # Get org_id from header or JWT claims
        org_id = request.headers.get("X-Org-Id")
        if not org_id:
            auth = getattr(request.state, 'auth', None)
            if auth:
                org_id = auth.get("org_id") or auth.get("yacht_id")

        if not org_id:
            return await call_next(request)

        key = f"rl:org:{org_id}"

        try:
            # Test EVAL availability once
            if self.eval_available is None:
                try:
                    result = await self.redis.eval("return 'ok'", 0)
                    self.eval_available = (result == 'ok')
                    if self.eval_available:
                        logger.info("[RateLimit] EVAL available, using token bucket")
                    else:
                        logger.warning("[RateLimit] EVAL returned unexpected result, using fixed-window")
                except Exception as e:
                    logger.warning(f"[RateLimit] EVAL not available ({e}), using fixed-window")
                    self.eval_available = False

            if self.eval_available:
                # Token bucket via Lua
                now = time.time()
                result = await self.redis.eval(
                    TOKEN_BUCKET_LUA,
                    1,  # number of keys
                    key,
                    BURST_CAPACITY,
                    TOKENS_PER_SEC,
                    now
                )
                allowed, remaining, retry_ms = result

                if not allowed:
                    retry_after = max(1, int(retry_ms / 1000))
                    logger.warning(f"[RateLimit] Token bucket exceeded for org={org_id[:8]}...")
                    return JSONResponse(
                        {"error": "rate_limit", "message": "Too many requests"},
                        status_code=429,
                        headers={
                            "X-RateLimit-Limit": str(BURST_CAPACITY),
                            "X-RateLimit-Remaining": "0",
                            "Retry-After": str(retry_after),
                        }
                    )

                response = await call_next(request)
                response.headers["X-RateLimit-Limit"] = str(BURST_CAPACITY)
                response.headers["X-RateLimit-Remaining"] = str(remaining)
                return response
            else:
                # Fixed-window fallback
                now = int(time.time())
                window_key = f"{key}:{now}"
                count = await self.redis.incr(window_key)
                if count == 1:
                    await self.redis.expire(window_key, 2)

                limit = TOKENS_PER_SEC + BURST_CAPACITY
                remaining = max(0, limit - count)

                if count > limit:
                    logger.warning(f"[RateLimit] Fixed-window exceeded for org={org_id[:8]}...")
                    return JSONResponse(
                        {"error": "rate_limit", "message": "Too many requests"},
                        status_code=429,
                        headers={
                            "X-RateLimit-Limit": str(limit),
                            "X-RateLimit-Remaining": "0",
                            "Retry-After": "1",
                        }
                    )

                response = await call_next(request)
                response.headers["X-RateLimit-Limit"] = str(limit)
                response.headers["X-RateLimit-Remaining"] = str(remaining)
                return response

        except Exception as e:
            logger.error(f"[RateLimit] Error: {e}")
            return await call_next(request)


__all__ = ["OrgRateLimitMiddleware"]
