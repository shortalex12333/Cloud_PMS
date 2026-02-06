# Token Refresh Troubleshooting Guide

**Last Updated**: 2026-02-06
**For**: Operators, Developers, Support Engineers

## Quick Diagnostic Commands

```bash
# Check worker status
ps aux | grep email_watcher_worker

# Recent refresh activity (last 20 cycles)
grep "ProactiveRefresh.*Cycle complete" /var/log/email_watcher.log | tail -20

# Recent failures
grep "ProactiveRefresh ✗" /var/log/email_watcher.log | tail -20

# Rate limit status
grep "rate_limit_budget" /var/log/email_watcher.log | tail -5

# Backoff status
grep "M6:Backoff" /var/log/email_watcher.log | tail -10
```

```sql
-- Database health check
SELECT
  (SELECT count(*) FROM auth_microsoft_tokens WHERE is_revoked = false) as total_tokens,
  (SELECT count(*) FROM auth_microsoft_tokens WHERE expires_at < now() + interval '10 minutes' AND is_revoked = false) as expiring_soon,
  (SELECT count(*) FROM auth_microsoft_tokens WHERE next_retry_at > now()) as in_backoff,
  (SELECT count(*) FROM auth_microsoft_tokens WHERE is_revoked = true) as revoked,
  (SELECT count(*) FROM email_watchers WHERE sync_status = 'degraded') as degraded_watchers;
```

## Common Issues

### Issue 1: "Token refresh not working - users getting 401 errors"

**Symptoms**:
- Users report "Email sync paused" or 401 errors
- Emails not loading in EmailSurface
- No recent "ProactiveRefresh" logs

**Diagnostic Steps**:

1. **Check if worker is running**:
   ```bash
   ps aux | grep email_watcher_worker
   # If no output: worker is not running
   ```

2. **Check heartbeat enabled**:
   ```bash
   echo $TOKEN_REFRESH_HEARTBEAT_ENABLED
   # Should output: true
   ```

3. **Check recent heartbeat logs**:
   ```bash
   grep "ProactiveRefresh" /var/log/email_watcher.log | tail -5
   # Should show activity within last 2-3 minutes
   ```

4. **Check for lock contention**:
   ```bash
   grep "Failed to acquire lock" /var/log/email_watcher.log | tail -10
   ```

5. **Check tokens expiring soon**:
   ```sql
   SELECT count(*) FROM auth_microsoft_tokens
   WHERE expires_at < now() + interval '10 minutes' AND is_revoked = false;
   -- If > 20: proactive refresh is not keeping up
   ```

**Solutions**:

| Diagnosis | Solution |
|-----------|----------|
| Worker not running | Restart worker via Render dashboard or `systemctl restart email_watcher_worker` |
| Heartbeat disabled | `export TOKEN_REFRESH_HEARTBEAT_ENABLED=true` and restart worker |
| No heartbeat logs | Check worker logs for crashes: `tail -100 /var/log/email_watcher.log` |
| Lock always fails | Clear stuck lock: `DELETE FROM worker_locks WHERE lock_name = 'token_refresh_heartbeat';` |
| Many tokens expiring | Increase batch size or decrease interval (see [Configuration Guide](./TOKEN_REFRESH_CONFIGURATION.md)) |

**Root Cause Reference**:
- Worker initialization: `apps/api/workers/email_watcher_worker.py:66`
- Heartbeat logic: `apps/api/workers/email_watcher_worker.py:207`
- Lock acquire: `apps/api/integrations/graph_client.py:695`

---

### Issue 2: "Users seeing degraded state banner persistently"

**Symptoms**:
- User sees orange "Sync degraded" badge (M5)
- Degraded banner shows "Email sync paused"
- Banner doesn't clear after successful refresh

**Diagnostic Steps**:

1. **Check watcher status for user**:
   ```sql
   SELECT user_id, sync_status, last_sync_error, degraded_at, updated_at
   FROM email_watchers
   WHERE user_id = '<USER_ID>';
   -- If sync_status = 'degraded': banner is correct
   ```

2. **Check token status for user**:
   ```sql
   SELECT id, expires_at, is_revoked, consecutive_failures, next_retry_at, last_refresh_error
   FROM auth_microsoft_tokens
   WHERE user_id = '<USER_ID>' AND token_purpose = 'read';
   ```

3. **Check recent refresh attempts for user**:
   ```bash
   grep "<USER_ID_PREFIX>" /var/log/email_watcher.log | grep "ProactiveRefresh" | tail -10
   ```

**Solutions**:

| Diagnosis | Solution |
|-----------|----------|
| `is_revoked = true` | **Expected**: User must reconnect via OAuth. Verify "Reconnect Outlook" button works (`apps/web/src/components/email/EmailSurface.tsx:361`) |
| `next_retry_at` in future | Token in backoff. Check `consecutive_failures`. If < 10: wait for backoff to expire. If ≥ 10: auto-revoked, user must reconnect |
| `last_refresh_error = 'invalid_grant'` | **Hard failure**: Token revoked by Microsoft. User must reconnect via OAuth |
| Token valid but watcher degraded | **Race condition**: Manually clear: `UPDATE email_watchers SET sync_status = 'active', last_sync_error = NULL WHERE user_id = '<USER_ID>';` |
| `consecutive_failures` high but not revoked | Force retry: `UPDATE auth_microsoft_tokens SET next_retry_at = NULL, consecutive_failures = 0 WHERE user_id = '<USER_ID>';` |

**Root Cause Reference**:
- Mark degraded: `apps/api/integrations/graph_client.py:648`
- Clear degraded: `apps/api/integrations/graph_client.py:671`
- UI degraded banner: `apps/web/src/components/email/EmailSurface.tsx:361`
- Backoff logic: `apps/api/integrations/graph_client.py:170`

---

### Issue 3: "Rate limit budget exhausted - tokens not refreshing"

**Symptoms**:
- Logs show "Budget exhausted" warnings
- Many tokens expiring without refresh
- Rate limit stats show `total_attempts >= max_requests`

**Diagnostic Steps**:

1. **Check rate limit stats**:
   ```bash
   grep "rate_limit_budget" /var/log/email_watcher.log | tail -5
   # Look for: total_attempts / max_requests ratio
   ```

2. **Check if budget is consistently exhausted**:
   ```bash
   grep "Budget exhausted" /var/log/email_watcher.log | wc -l
   # If > 10 in last hour: persistent issue
   ```

3. **Check if Microsoft is rate limiting us (429s)**:
   ```bash
   grep "429" /var/log/email_watcher.log | tail -10
   ```

**Solutions**:

| Diagnosis | Solution |
|-----------|----------|
| Budget exhausted every cycle | Increase budget: `export TOKEN_REFRESH_RATE_LIMIT_REQUESTS=150` (see [Configuration Guide](./TOKEN_REFRESH_CONFIGURATION.md#token_refresh_rate_limit_requests)) |
| Many 429 errors from Microsoft | **Microsoft is rate limiting us**. Decrease load: `export TOKEN_REFRESH_BATCH_LIMIT=25` |
| Budget OK but tokens still expiring | Check if tokens are in backoff: `SELECT count(*) FROM auth_microsoft_tokens WHERE next_retry_at > now();` |
| Rate limit after Microsoft outage | **Recovery mode**: Temporarily increase budget and batch size for 1-2 hours, then revert |

**Formula to check capacity**:
```
tokens_per_10min = BATCH_LIMIT * (600 / (INTERVAL_CYCLES * 60))
utilization = tokens_per_10min / RATE_LIMIT_REQUESTS

# Example (defaults):
# 50 * (600 / 120) / 100 = 2.5 = 250% utilization
# BUT: filters reduce actual to ~50-100 tokens/10min = 50-100%
```

**Root Cause Reference**:
- Rate limiter class: `apps/api/integrations/graph_client.py:119`
- Budget check: `apps/api/integrations/graph_client.py:1018`
- Budget record: `apps/api/integrations/graph_client.py:1077`

---

### Issue 4: "Tokens stuck in exponential backoff"

**Symptoms**:
- Many tokens with `next_retry_at` in the future
- Users intermittently see degraded state
- Tokens not refreshing despite expiring soon

**Diagnostic Steps**:

1. **Count tokens in backoff**:
   ```sql
   SELECT count(*) FROM auth_microsoft_tokens WHERE next_retry_at > now();
   -- If > 10: backoff is working (soft failures are common)
   -- If > 50: systemic issue (Microsoft outage or config problem)
   ```

2. **Check backoff distribution**:
   ```sql
   SELECT
     consecutive_failures,
     count(*) as token_count,
     min(next_retry_at) as earliest_retry,
     max(next_retry_at) as latest_retry
   FROM auth_microsoft_tokens
   WHERE next_retry_at > now()
   GROUP BY consecutive_failures
   ORDER BY consecutive_failures;
   ```

3. **Check common errors causing backoff**:
   ```sql
   SELECT last_refresh_error, count(*)
   FROM auth_microsoft_tokens
   WHERE next_retry_at > now()
   GROUP BY last_refresh_error
   ORDER BY count DESC;
   ```

4. **Check if Microsoft Graph has issues**:
   - Visit: https://status.azure.com/
   - Check for "Azure Active Directory" or "Microsoft Graph" incidents

**Solutions**:

| Diagnosis | Solution |
|-----------|----------|
| `consecutive_failures = 1-3`, `last_refresh_error = '429'` | **Normal**: Transient rate limiting. Backoff will resolve automatically |
| `consecutive_failures = 1-3`, `last_refresh_error = '500/503'` | **Microsoft outage**: Wait for recovery. Backoff will resolve automatically |
| `consecutive_failures ≥ 10` | **Auto-revoked**: Users must reconnect. This is expected after persistent failures |
| `consecutive_failures = 5-9`, all same error | **Systemic issue**: Check Azure app config, client secrets, permissions |
| Many tokens in backoff (> 50) after outage | **Recovery mode**: Manually clear backoff for users with < 5 failures: `UPDATE auth_microsoft_tokens SET next_retry_at = NULL WHERE consecutive_failures < 5;` |

**Backoff timing reference**:
- 1st failure: 60s ± 12s
- 2nd failure: 120s ± 24s
- 3rd failure: 240s ± 48s
- 4th failure: 480s ± 96s
- 5th+ failure: 3600s (1 hour)

**Root Cause Reference**:
- Backoff calculator: `apps/api/integrations/graph_client.py:170`
- Update retry state: `apps/api/integrations/graph_client.py:187`
- Backoff filter: `apps/api/integrations/graph_client.py:1041`

---

### Issue 5: "Distributed lock stuck - no worker can refresh"

**Symptoms**:
- All workers log "Failed to acquire lock"
- No "Cycle complete" logs from any worker
- Lock lease expired but not released

**Diagnostic Steps**:

1. **Check lock status**:
   ```sql
   SELECT *,
     EXTRACT(EPOCH FROM (now() - lease_expires_at)) as seconds_since_expire,
     EXTRACT(EPOCH FROM (now() - acquired_at)) as seconds_since_acquire
   FROM worker_locks
   WHERE lock_name = 'token_refresh_heartbeat';
   ```

2. **Check if any worker is holding lock**:
   ```bash
   ps aux | grep email_watcher_worker
   # Note PIDs

   # Check lock worker_id
   psql -c "SELECT worker_id FROM worker_locks WHERE lock_name = 'token_refresh_heartbeat';"
   # Format: 'srv-xxx:12345' (hostname:pid)
   ```

3. **Check recent lock acquisition attempts**:
   ```bash
   grep "acquire lock" /var/log/email_watcher.log | tail -20
   ```

**Solutions**:

| Diagnosis | Solution |
|-----------|----------|
| `lease_expires_at` in past, no worker running | **Stuck lock**: `DELETE FROM worker_locks WHERE lock_name = 'token_refresh_heartbeat';` Next cycle will re-acquire |
| `lease_expires_at` in future, worker_id doesn't match any running worker | **Dead worker held lock**: `DELETE FROM worker_locks WHERE lock_name = 'token_refresh_heartbeat';` |
| `lease_expires_at` in future, worker_id matches running worker | **Normal**: That worker is processing. Wait for cycle to complete (< 3 min) |
| Multiple workers, all failing to acquire | **High contention (normal)**: Only one worker should succeed per cycle. If ALL fail, check lease_expires_at |

**Lock timing**:
- Lease duration: 180 seconds (3 minutes)
- Refresh cycle: 120 seconds (2 minutes)
- Overlap: Intentional - ensures lock held for entire cycle

**Root Cause Reference**:
- Lock acquire: `apps/api/integrations/graph_client.py:695`
- Lock release: `apps/api/integrations/graph_client.py:739`
- Lock table: `supabase/migrations/20260206000000_worker_locks_table.sql`

---

### Issue 6: "Tokens refreshing but users still getting 401s"

**Symptoms**:
- Proactive refresh logs show success
- Tokens have valid `expires_at` in future
- Users still get 401 errors when loading emails

**Diagnostic Steps**:

1. **Check token purpose separation**:
   ```sql
   SELECT user_id, token_purpose, expires_at
   FROM auth_microsoft_tokens
   WHERE user_id = '<USER_ID>'
   ORDER BY token_purpose;
   -- Should have both 'read' and 'write' tokens
   ```

2. **Check if error is from read or write operation**:
   ```bash
   # Check API logs for 401 errors
   grep "401" /var/log/api.log | grep "<USER_ID>" | tail -10
   # Look for: "/email/thread" (read) vs "/email/send" (write)
   ```

3. **Check reactive refresh (on-demand)**:
   ```bash
   grep "get_valid_token" /var/log/api.log | grep "<USER_ID>" | tail -10
   # Should show token checks on every API call
   ```

4. **Verify token is actually used**:
   - Check Graph API response headers in browser DevTools
   - Look for: `Authorization: Bearer <token>` in request
   - Check response: 401 with `WWW-Authenticate` header details

**Solutions**:

| Diagnosis | Solution |
|-----------|----------|
| Only one token purpose exists | **Token purpose mismatch**: User connected with wrong OAuth scope. User must reconnect with correct scope (read + write) |
| Both tokens exist but one expired | Proactive refresh only refreshes tokens expiring within 5 min. Check if reactive refresh is working: test by triggering API call |
| Token exists and valid but still 401 | **Invalid token content**: Possible token revoked server-side by Microsoft. Mark as revoked: `UPDATE auth_microsoft_tokens SET is_revoked = true WHERE user_id = '<USER_ID>';` User must reconnect |
| 401 only on specific operations | Check token purpose: Read operations need `token_purpose = 'read'`, Send operations need `token_purpose = 'write'` |

**Root Cause Reference**:
- Reactive refresh (on-demand): `apps/api/integrations/graph_client.py:296`
- Read client: `apps/api/integrations/graph_client.py:376`
- Write client: `apps/api/integrations/graph_client.py:509`
- Token purpose check: `apps/api/integrations/graph_client.py:263`

---

## Error Code Reference

### Microsoft Graph Error Codes

| Error Code | Meaning | M6 Handling | User Action |
|------------|---------|-------------|-------------|
| `invalid_grant` | Token revoked by user or admin | Hard fail → revoke token → degraded | User must reconnect |
| `consent_required` | User consent withdrawn | Hard fail → revoke token → degraded | User must reconnect |
| `interaction_required` | MFA or other interaction needed | Hard fail → revoke token → degraded | User must reconnect |
| `429` | Rate limited by Microsoft | Soft fail → exponential backoff | None (auto-recovery) |
| `500` | Microsoft server error | Soft fail → exponential backoff | None (auto-recovery) |
| `503` | Microsoft service unavailable | Soft fail → exponential backoff | None (auto-recovery) |
| `504` | Microsoft gateway timeout | Soft fail → exponential backoff | None (auto-recovery) |

### Internal Error States

| State | Meaning | Recovery |
|-------|---------|----------|
| `consecutive_failures > 0` | Token in exponential backoff | Automatic after backoff period |
| `consecutive_failures >= 10` | Auto-revoked after max failures | User must reconnect |
| `is_revoked = true` | Token permanently invalid | User must reconnect |
| `sync_status = 'degraded'` | Watcher needs attention | Automatic on successful refresh OR user reconnect |
| `next_retry_at > now()` | Token in backoff window | Automatic after backoff expires |

---

## Debugging Tools

### Enable Verbose Logging

```bash
# In worker environment
export LOG_LEVEL=DEBUG

# Restart worker
# Logs will include detailed token selection, refresh attempts, backoff calculations
```

### Manual Token Refresh (Testing)

```python
# Python console with Supabase access
from integrations.graph_client import refresh_access_token
from supabase import create_client

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
user_id = '<USER_ID>'
yacht_id = '<YACHT_ID>'
purpose = 'read'

# Attempt refresh
try:
    await refresh_access_token(supabase, user_id, yacht_id, purpose)
    print("✓ Refresh succeeded")
except Exception as e:
    print(f"✗ Refresh failed: {e}")
```

### Simulate Backoff Behavior

```sql
-- Force token into backoff state (testing only!)
UPDATE auth_microsoft_tokens
SET consecutive_failures = 3,
    next_retry_at = now() + interval '4 minutes',
    last_refresh_error = 'TEST: simulated 429'
WHERE user_id = '<USER_ID>' AND token_purpose = 'read';

-- Should see backoff in UI and logs
-- Token will be skipped in next refresh cycles until next_retry_at passes

-- Reset after testing
UPDATE auth_microsoft_tokens
SET consecutive_failures = 0,
    next_retry_at = NULL,
    last_refresh_error = NULL
WHERE user_id = '<USER_ID>';
```

### Check Rate Limiter State (Live)

```bash
# Extract rate limit stats from recent logs
grep "rate_limit_budget" /var/log/email_watcher.log | tail -1 | jq '.rate_limit_budget'

# Should show:
# {
#   "total_attempts": 45,
#   "successful": 42,
#   "failed": 3,
#   "remaining_budget": 55,
#   "max_requests": 100,
#   "window_seconds": 600
# }
```

---

## When to Escalate

### Escalate to Platform Team if:
- Worker repeatedly crashing (infrastructure issue)
- Render deployment failing
- Database connection issues

### Escalate to Microsoft Support if:
- Persistent 429s despite backoff
- All tokens failing with same error (Azure app issue)
- Graph API showing errors on status page but issue persists

### Escalate to Email Infrastructure Team if:
- Code bugs in refresh logic
- Unexpected auto-revocations
- Race conditions in degraded state clearing

---

## Related Documentation

- [Architecture Overview](./TOKEN_REFRESH_ARCHITECTURE.md)
- [Operational Runbook](./TOKEN_REFRESH_RUNBOOK.md)
- [Configuration Guide](./TOKEN_REFRESH_CONFIGURATION.md)
