# Token Refresh Operational Runbook

**Status**: Production
**Last Updated**: 2026-02-06
**On-Call Contact**: Email Infrastructure Team

## Quick Reference

### Key Code Paths

| Component | File:Line |
|-----------|-----------|
| Proactive refresh entrypoint | `apps/api/integrations/graph_client.py:960` |
| On-demand refresh (reactive) | `apps/api/integrations/graph_client.py:296` |
| Mark watcher degraded | `apps/api/integrations/graph_client.py:648` |
| Clear watcher degraded | `apps/api/integrations/graph_client.py:671` |
| Distributed lock acquire | `apps/api/integrations/graph_client.py:695` |
| Distributed lock release | `apps/api/integrations/graph_client.py:739` |
| Rate limiter | `apps/api/integrations/graph_client.py:119` |
| Backoff calculator | `apps/api/integrations/graph_client.py:170` |
| Worker heartbeat | `apps/api/workers/email_watcher_worker.py:207` |
| Worker initialization | `apps/api/workers/email_watcher_worker.py:66` |
| Degraded UI banner | `apps/web/src/components/email/EmailSurface.tsx:361` |

### Database Tables

| Table | Purpose | Migration |
|-------|---------|-----------|
| `auth_microsoft_tokens` | Token storage + retry state | `00000000000021_phase4_email_transport_layer.sql` |
| `worker_locks` | Distributed lock coordination | `20260206000000_worker_locks_table.sql` |
| `email_watchers` | Watcher status (UI reads this) | `00000000000023_email_watcher_enhancements.sql` |

### Key Queries

```sql
-- Check watcher selection RPC
-- apps/api/migrations/00000000000023_email_watcher_enhancements.sql:170
SELECT * FROM get_email_watchers_due_for_sync();

-- Find tokens in backoff
SELECT user_id, consecutive_failures, next_retry_at, last_refresh_error
FROM auth_microsoft_tokens
WHERE next_retry_at > now() AND is_revoked = false;

-- Check distributed lock status
SELECT * FROM worker_locks WHERE lock_name = 'token_refresh_heartbeat';

-- Find degraded watchers
SELECT user_id, yacht_id, sync_status, last_sync_error, degraded_at
FROM email_watchers
WHERE sync_status = 'degraded';
```

## Incident Response Playbooks

### 1. High Rate of Token Refresh Failures

**Symptoms**:
- CloudWatch/logs show many "ProactiveRefresh ✗" errors
- Multiple users reporting degraded state banners
- Rate limit budget frequently exhausted

**Diagnosis**:
```bash
# Check recent failures
grep "ProactiveRefresh ✗" /var/log/email_watcher.log | tail -50

# Check rate limit stats
grep "M6:RateLimit" /var/log/email_watcher.log | tail -20

# Database: Count tokens in backoff
psql -c "SELECT count(*) FROM auth_microsoft_tokens WHERE next_retry_at > now();"

# Database: Identify error patterns
psql -c "SELECT last_refresh_error, count(*) FROM auth_microsoft_tokens
         WHERE last_refresh_error IS NOT NULL
         GROUP BY last_refresh_error
         ORDER BY count DESC;"
```

**Resolution**:

1. **If error is `invalid_grant` or `consent_required`** (hard failures):
   - This is expected - users need to reconnect
   - Verify degraded banner shows correctly (M5)
   - No action needed; system working as designed

2. **If error is `429` (rate limited by Microsoft)**:
   - Check rate limit budget: `grep "rate_limit_budget" logs`
   - Verify backoff is working: tokens should wait 60s+ before retry
   - If persistent: Consider reducing `TOKEN_REFRESH_BATCH_LIMIT` from 50 to 25

3. **If error is `500/503` (Microsoft Graph outage)**:
   - Verify exponential backoff is triggering
   - Monitor Microsoft Graph status: https://status.azure.com/
   - Tokens will auto-recover after backoff period
   - No manual intervention needed

4. **If rate limit budget exhausted**:
   ```bash
   # Check current budget usage
   grep "total_attempts.*max_requests" logs | tail -1

   # If consistently hitting limit:
   # Option A: Increase budget (if we're below Microsoft's limits)
   export TOKEN_REFRESH_RATE_LIMIT_REQUESTS=150

   # Option B: Reduce batch size to spread load
   export TOKEN_REFRESH_BATCH_LIMIT=25
   ```

### 2. Token Refresh Heartbeat Not Running

**Symptoms**:
- No "ProactiveRefresh" logs in last 5+ minutes
- Tokens expiring without proactive refresh
- Users getting 401 errors

**Diagnosis**:
```bash
# Check if worker is running
ps aux | grep email_watcher_worker

# Check last heartbeat timestamp
grep "ProactiveRefresh" /var/log/email_watcher.log | tail -5

# Check distributed lock status
psql -c "SELECT *,
         EXTRACT(EPOCH FROM (now() - lease_expires_at)) as seconds_since_expire
         FROM worker_locks
         WHERE lock_name = 'token_refresh_heartbeat';"
```

**Resolution**:

1. **Worker crashed or not running**:
   ```bash
   # Restart worker via Render dashboard or CLI
   # Or via systemctl if self-hosted:
   sudo systemctl restart email_watcher_worker
   ```

2. **Distributed lock stuck** (lease expired but not released):
   ```bash
   # Check lock age
   psql -c "SELECT * FROM worker_locks WHERE lock_name = 'token_refresh_heartbeat';"

   # If lease_expires_at is in the past and no worker is running:
   psql -c "DELETE FROM worker_locks WHERE lock_name = 'token_refresh_heartbeat';"

   # Worker will acquire lock on next cycle
   ```

3. **Heartbeat disabled**:
   ```bash
   # Check env var
   echo $TOKEN_REFRESH_HEARTBEAT_ENABLED  # Should be "true"

   # If false or unset, enable:
   export TOKEN_REFRESH_HEARTBEAT_ENABLED=true
   ```

### 3. User Stuck in Degraded State

**Symptoms**:
- User sees degraded banner persistently
- Token refresh succeeds but banner doesn't clear
- `sync_status = 'degraded'` in database

**Diagnosis**:
```sql
-- Check watcher status
SELECT user_id, yacht_id, sync_status, last_sync_error, degraded_at, updated_at
FROM email_watchers
WHERE user_id = '<USER_ID>';

-- Check token status
SELECT id, expires_at, consecutive_failures, next_retry_at, last_refresh_error, is_revoked
FROM auth_microsoft_tokens
WHERE user_id = '<USER_ID>' AND token_purpose = 'read';
```

**Resolution**:

1. **Token is revoked** (`is_revoked = true`):
   - Expected behavior - user must reconnect
   - Verify "Reconnect Outlook" button works
   - User should click button → OAuth flow → new token

2. **Token is valid but watcher degraded** (race condition):
   ```sql
   -- Manually clear degraded status
   UPDATE email_watchers
   SET sync_status = 'active',
       last_sync_error = NULL,
       degraded_at = NULL,
       updated_at = now()
   WHERE user_id = '<USER_ID>' AND yacht_id = '<YACHT_ID>';
   ```

3. **Token in long backoff** (`next_retry_at` far in future):
   ```sql
   -- Check backoff status
   SELECT next_retry_at, consecutive_failures,
          EXTRACT(EPOCH FROM (next_retry_at - now())) as seconds_until_retry
   FROM auth_microsoft_tokens
   WHERE user_id = '<USER_ID>';

   -- If > 10 failures (auto-revoked), user must reconnect
   -- If < 10 failures but long backoff, you can clear it:
   UPDATE auth_microsoft_tokens
   SET next_retry_at = NULL,
       consecutive_failures = 0
   WHERE user_id = '<USER_ID>' AND token_purpose = 'read';

   -- Next heartbeat will retry refresh
   ```

### 4. Multiple Workers Fighting for Lock

**Symptoms**:
- Frequent lock acquisition failures in logs
- "Failed to acquire lock" warnings
- Tokens refreshed more often than expected

**Diagnosis**:
```bash
# Check lock contention
grep "acquire lock" /var/log/email_watcher.log | tail -20

# Check worker_locks table
psql -c "SELECT *,
         EXTRACT(EPOCH FROM (lease_expires_at - now())) as seconds_until_expire
         FROM worker_locks;"

# Identify worker instances
ps aux | grep email_watcher_worker
```

**Resolution**:

This is **normal** in multi-region deployment. The lock prevents duplicate work:
- Only one worker acquires lock per cycle
- Others skip and try next cycle
- No action needed if success rate > 50%

If **no worker ever acquires lock**:
```sql
-- Check for stuck lease
SELECT * FROM worker_locks WHERE lease_expires_at < now();

-- If stuck, delete and let workers re-acquire
DELETE FROM worker_locks WHERE lease_expires_at < now();
```

## Manual Operations

### Force Token Refresh (Ad-hoc)

```sql
-- Trigger immediate refresh by clearing retry state
UPDATE auth_microsoft_tokens
SET next_retry_at = NULL,
    consecutive_failures = 0
WHERE user_id = '<USER_ID>' AND token_purpose = 'read';

-- Token will be picked up in next heartbeat cycle (< 2 minutes)
```

### Pause Token Refresh (Maintenance)

```bash
# Disable heartbeat
export TOKEN_REFRESH_HEARTBEAT_ENABLED=false

# Or set batch limit to 0
export TOKEN_REFRESH_BATCH_LIMIT=0

# Restart worker to apply
```

### Resume Token Refresh

```bash
# Re-enable heartbeat
export TOKEN_REFRESH_HEARTBEAT_ENABLED=true
export TOKEN_REFRESH_BATCH_LIMIT=50

# Restart worker
```

### Verify Health

```bash
# 1. Check worker is running
ps aux | grep email_watcher_worker

# 2. Check recent heartbeat logs
grep "ProactiveRefresh.*Cycle complete" /var/log/email_watcher.log | tail -5

# 3. Check success rate
grep "ProactiveRefresh.*refreshed" /var/log/email_watcher.log | wc -l
grep "ProactiveRefresh.*failed" /var/log/email_watcher.log | wc -l

# 4. Check rate limit budget
grep "rate_limit_budget" /var/log/email_watcher.log | tail -1

# 5. Database health check
psql <<EOF
-- Tokens expiring soon (should be < 10 if heartbeat working)
SELECT count(*) as expiring_soon
FROM auth_microsoft_tokens
WHERE expires_at < now() + interval '10 minutes' AND is_revoked = false;

-- Tokens in backoff (should be < 5 at steady state)
SELECT count(*) as in_backoff
FROM auth_microsoft_tokens
WHERE next_retry_at > now();

-- Degraded watchers (should be < 2 at steady state)
SELECT count(*) as degraded
FROM email_watchers
WHERE sync_status = 'degraded';
EOF
```

## Monitoring & Alerts

### Key Metrics to Track

1. **Proactive Refresh Success Rate** (target: > 99%)
   - Log: "ProactiveRefresh ✓" vs "ProactiveRefresh ✗"
   - Alert if < 95% over 10-minute window

2. **Tokens Expiring Soon** (target: < 10)
   - Query: `SELECT count(*) FROM auth_microsoft_tokens WHERE expires_at < now() + interval '10 minutes'`
   - Alert if > 20

3. **Rate Limit Budget Usage** (target: < 80%)
   - Log: `rate_limit_budget.total_attempts / rate_limit_budget.max_requests`
   - Alert if > 90

4. **Degraded Watchers** (target: < 5)
   - Query: `SELECT count(*) FROM email_watchers WHERE sync_status = 'degraded'`
   - Alert if > 10

5. **Heartbeat Lag** (target: < 3 minutes)
   - Check timestamp of last "Cycle complete" log
   - Alert if > 5 minutes

### Example Datadog Query

```
avg:token_refresh.success_rate{env:production} < 95
avg:token_refresh.expiring_tokens{env:production} > 20
avg:token_refresh.rate_limit_usage{env:production} > 90
sum:token_refresh.degraded_watchers{env:production} > 10
```

## Escalation

### When to Escalate

1. **Microsoft Graph Outage**: Monitor https://status.azure.com/
2. **Persistent 429 errors** despite backoff working correctly
3. **All tokens failing** with same error (potential Azure app config issue)
4. **Worker repeatedly crashing** (application bug)

### Escalation Contacts

- **Email Infrastructure Team**: #email-infra Slack
- **Platform Team**: #platform Slack (for Render/infrastructure issues)
- **Microsoft Support**: If Azure app permissions/quota issues

## Related Documentation

- [Architecture Overview](./TOKEN_REFRESH_ARCHITECTURE.md)
- [Configuration Guide](./TOKEN_REFRESH_CONFIGURATION.md)
- [Troubleshooting Guide](./TOKEN_REFRESH_TROUBLESHOOTING.md)
