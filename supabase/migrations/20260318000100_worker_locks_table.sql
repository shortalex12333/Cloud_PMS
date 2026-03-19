-- Worker A fix: email-watcher distributed lock heartbeat
-- Missing table caused HTTP 404 every 60s in graph_client.py:909-950
-- No Docker restart needed — picked up on next poll cycle

CREATE TABLE IF NOT EXISTS public.worker_locks (
    lock_name        TEXT PRIMARY KEY,
    lease_expires_at TIMESTAMPTZ NOT NULL,
    acquired_at      TIMESTAMPTZ NOT NULL,
    worker_id        TEXT NOT NULL
);
