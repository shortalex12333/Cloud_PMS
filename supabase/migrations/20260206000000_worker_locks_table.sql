--
-- Worker Locks Table
-- For coordinating distributed background workers (token refresh heartbeat, etc.)
--
-- Usage: Timestamp-based leases ensure only one worker runs a task at a time
--

CREATE TABLE IF NOT EXISTS worker_locks (
    lock_name TEXT PRIMARY KEY,
    lease_expires_at TIMESTAMPTZ NOT NULL,
    acquired_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    worker_id TEXT NOT NULL,  -- e.g., "srv-xxx:12345" (service_id:pid)
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Index for efficient expiry checks
CREATE INDEX IF NOT EXISTS idx_worker_locks_lease_expires
    ON worker_locks(lease_expires_at);

-- RLS: Service role only
ALTER TABLE worker_locks ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Service role full access"
    ON worker_locks
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- Comments
COMMENT ON TABLE worker_locks IS 'Distributed locks for background workers using timestamp-based leases';
COMMENT ON COLUMN worker_locks.lock_name IS 'Unique lock identifier (e.g., token_refresh_heartbeat)';
COMMENT ON COLUMN worker_locks.lease_expires_at IS 'Lock expires at this time; another worker can claim if expired';
COMMENT ON COLUMN worker_locks.worker_id IS 'Worker instance that holds the lock (format: service_id:pid)';
