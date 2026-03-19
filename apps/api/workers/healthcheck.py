#!/usr/bin/env python3
"""
Celeste Worker Health Check
============================
Called by Docker's HEALTHCHECK every 30s inside each worker container.
Exits 0 = healthy, exits 1 = unhealthy (Docker will restart the container).

Usage (set in docker-compose.yml):
  python workers/healthcheck.py embedding
  python workers/healthcheck.py projection
  python workers/healthcheck.py cache
  python workers/healthcheck.py email

What each check tests:
  embedding  - DB reachable + no jobs stuck in 'processing' >15 min
  projection - DB reachable + no search_index rows stuck in 'processing' >15 min
  cache      - DB reachable + Redis reachable
  email      - DB reachable + worker_locks heartbeat updated within 10 min
"""

import sys
import os

WORKER = sys.argv[1] if len(sys.argv) > 1 else "unknown"
DB_TIMEOUT = 5  # seconds for DB connection attempt
STUCK_THRESHOLD_MINUTES = 15
EMAIL_HEARTBEAT_STALE_MINUTES = 10


def check_db_connectivity(dsn: str):
    """Verify the database is reachable. Raises on failure."""
    import psycopg2
    conn = psycopg2.connect(dsn, connect_timeout=DB_TIMEOUT)
    conn.cursor().execute("SELECT 1")
    conn.close()


def check_redis_connectivity(url: str):
    """Verify Redis is reachable. Raises on failure."""
    import redis
    r = redis.from_url(url, socket_connect_timeout=DB_TIMEOUT, socket_timeout=DB_TIMEOUT)
    r.ping()
    r.close()


def check_embedding():
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        raise EnvironmentError("DATABASE_URL not set")

    check_db_connectivity(dsn)

    import psycopg2
    conn = psycopg2.connect(dsn, connect_timeout=DB_TIMEOUT)
    cur = conn.cursor()
    cur.execute("""
        SELECT COUNT(*)
        FROM embedding_jobs
        WHERE status = 'processing'
          AND started_at < NOW() - INTERVAL '%s minutes'
    """ % STUCK_THRESHOLD_MINUTES)
    stuck = cur.fetchone()[0]
    conn.close()

    if stuck > 0:
        raise RuntimeError(f"{stuck} embedding jobs stuck in 'processing' >{STUCK_THRESHOLD_MINUTES} min — worker likely hung")


def check_projection():
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        raise EnvironmentError("DATABASE_URL not set")

    check_db_connectivity(dsn)

    import psycopg2
    conn = psycopg2.connect(dsn, connect_timeout=DB_TIMEOUT)
    cur = conn.cursor()
    cur.execute("""
        SELECT COUNT(*)
        FROM search_index
        WHERE embedding_status = 'processing'
          AND updated_at < NOW() - INTERVAL '%s minutes'
    """ % STUCK_THRESHOLD_MINUTES)
    stuck = cur.fetchone()[0]
    conn.close()

    if stuck > 0:
        raise RuntimeError(f"{stuck} search_index rows stuck in 'processing' >{STUCK_THRESHOLD_MINUTES} min — projection worker likely hung")


def check_cache():
    dsn = os.environ.get("READ_DB_DSN") or os.environ.get("DATABASE_URL")
    redis_url = os.environ.get("REDIS_URL")

    if not dsn:
        raise EnvironmentError("READ_DB_DSN / DATABASE_URL not set")
    if not redis_url:
        raise EnvironmentError("REDIS_URL not set")

    check_db_connectivity(dsn)
    check_redis_connectivity(redis_url)


def check_email():
    """
    Checks that the token refresh heartbeat is still alive.
    The email worker writes to worker_locks every ~60s with a 180s lease.
    If the lease expired more than EMAIL_HEARTBEAT_STALE_MINUTES ago, the worker is stuck.
    """
    import psycopg2
    from datetime import timezone

    # Use direct DB rather than Supabase client to avoid extra dependency
    dsn = os.environ.get("DATABASE_URL")
    # email-watcher uses SUPABASE_URL / SUPABASE_SERVICE_KEY, not DATABASE_URL.
    # Fall back to a dsn constructed from env if available.
    if not dsn:
        raise EnvironmentError("DATABASE_URL not set for email health check")

    conn = psycopg2.connect(dsn, connect_timeout=DB_TIMEOUT)
    cur = conn.cursor()
    cur.execute("""
        SELECT
            lease_expires_at,
            EXTRACT(EPOCH FROM (NOW() - lease_expires_at)) AS seconds_since_expiry
        FROM worker_locks
        WHERE lock_name = 'token_refresh_heartbeat'
    """)
    row = cur.fetchone()
    conn.close()

    if not row:
        raise RuntimeError("worker_locks heartbeat row missing — email worker never started or table was dropped")

    seconds_since_expiry = float(row[1])
    stale_threshold = EMAIL_HEARTBEAT_STALE_MINUTES * 60

    if seconds_since_expiry > stale_threshold:
        minutes_stale = int(seconds_since_expiry // 60)
        raise RuntimeError(f"email worker heartbeat {minutes_stale} min stale (threshold: {EMAIL_HEARTBEAT_STALE_MINUTES} min)")


CHECKS = {
    "embedding": check_embedding,
    "projection": check_projection,
    "cache": check_cache,
    "email": check_email,
}

if __name__ == "__main__":
    if WORKER not in CHECKS:
        print(f"UNKNOWN worker type '{WORKER}'. Valid: {list(CHECKS.keys())}", file=sys.stderr)
        sys.exit(1)

    try:
        CHECKS[WORKER]()
        print(f"OK: {WORKER} worker healthy")
        sys.exit(0)
    except Exception as e:
        print(f"UNHEALTHY: {WORKER} — {e}", file=sys.stderr)
        sys.exit(1)
