#!/usr/bin/env python3
"""
F1 Search - Cache Invalidation Listener

Listens to pg_notify('f1_cache_invalidate') and evicts Redis keys.

Usage:
    READ_DB_DSN=... REDIS_URL=... python -m cache.invalidation_listener

Or as Render background worker:
    Command: python apps/api/cache/invalidation_listener.py
    Env: READ_DB_DSN, REDIS_URL
"""

import os
import asyncio
import json
import logging
import signal

import aioredis
import asyncpg

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

READ_DSN = os.getenv("READ_DB_DSN") or os.getenv("DATABASE_URL")
REDIS_URL = os.getenv("REDIS_URL")

# Global state for graceful shutdown
_shutdown = False
_redis = None


def mask_dsn(dsn: str) -> str:
    """Mask password in DSN for safe logging."""
    if not dsn:
        return "None"
    # Replace password in postgresql://user:pass@host format
    import re
    return re.sub(r':([^:@]+)@', ':***@', dsn)


async def handle_notification(conn, pid, channel, payload):
    """
    Handle incoming pg_notify notification.

    Evicts Redis keys matching the org/yacht from the notification.
    """
    global _redis

    if _redis is None:
        logger.warning("Redis not connected, skipping eviction")
        return

    try:
        data = json.loads(payload)
        org = data.get('org_id')
        yacht = data.get('yacht_id')
        object_type = data.get('object_type')
        object_id = data.get('object_id')

        # Log without secrets
        logger.info(
            f"Notification received: org={org[:8] if org else 'N/A'}..., "
            f"yacht={yacht[:8] if yacht else 'N/A'}..., type={object_type}"
        )

        # Key patterns to evict (result cache and rewrite cache)
        patterns = [
            f"rs::{org}:{yacht or ''}*",
            f"rw::{org}:{yacht or ''}*",
        ]

        evicted = 0
        for pat in patterns:
            async for key in _redis.scan_iter(match=pat, count=100):
                await _redis.delete(key)
                evicted += 1

        if evicted > 0:
            logger.info(f"Evicted {evicted} keys for org={org[:8] if org else 'N/A'}...")
        else:
            logger.debug(f"No keys to evict for pattern")

    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in notification: {e}")
    except Exception as e:
        logger.error(f"Error handling notification: {e}")


async def listen_and_evict():
    """
    Main listener loop.

    Connects to Postgres and Redis, then listens for cache invalidation events.
    """
    global _redis, _shutdown

    if not READ_DSN:
        logger.error("READ_DB_DSN or DATABASE_URL not set")
        return

    if not REDIS_URL:
        logger.error("REDIS_URL not set")
        return

    logger.info(f"Connecting to database: {mask_dsn(READ_DSN)}")
    conn = await asyncpg.connect(READ_DSN)

    logger.info("Connecting to Redis...")
    _redis = await aioredis.from_url(REDIS_URL, decode_responses=True)

    # Test Redis connection
    try:
        pong = await _redis.ping()
        logger.info(f"Redis connected: {pong}")
    except Exception as e:
        logger.error(f"Redis ping failed: {e}")
        return

    # Register notification listener
    await conn.add_listener('f1_cache_invalidate', handle_notification)
    logger.info("✅ Listening for f1_cache_invalidate events...")

    # Keep connection alive until shutdown
    try:
        while not _shutdown:
            # Keepalive query every 30s
            await asyncio.sleep(30)
            try:
                await conn.fetchval("SELECT 1")
            except Exception as e:
                logger.error(f"Keepalive failed: {e}")
                break
    except asyncio.CancelledError:
        logger.info("Listener cancelled")

    # Cleanup
    logger.info("Shutting down...")
    await conn.remove_listener('f1_cache_invalidate', handle_notification)
    await conn.close()
    await _redis.close()
    logger.info("Shutdown complete")


def handle_signal(sig, frame):
    """Handle SIGTERM/SIGINT for graceful shutdown."""
    global _shutdown
    logger.info(f"Received signal {sig}, initiating shutdown...")
    _shutdown = True


if __name__ == "__main__":
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

    logger.info("=== F1 Search Cache Invalidation Listener ===")
    asyncio.run(listen_and_evict())
