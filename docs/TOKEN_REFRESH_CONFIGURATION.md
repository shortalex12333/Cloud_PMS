# Token Refresh Configuration Guide

**Last Updated**: 2026-02-06
**Environment**: Production, Staging

## Overview

The token refresh system is tuned for **safe defaults** that work for most deployments. This guide covers configuration parameters and safe tuning strategies.

## Configuration Parameters

### Core Settings (M4: Proactive Refresh)

#### `TOKEN_REFRESH_HEARTBEAT_ENABLED`
- **Type**: Boolean
- **Default**: `true`
- **Location**: `apps/api/workers/email_watcher_worker.py:66`
- **Purpose**: Master switch for proactive refresh
- **Values**:
  - `true`: Enable proactive refresh (recommended)
  - `false`: Disable proactive refresh (reactive only - NOT recommended)

**When to change**:
- Set to `false` during maintenance windows
- Set to `false` to debug reactive refresh in isolation

```bash
# Disable proactive refresh
export TOKEN_REFRESH_HEARTBEAT_ENABLED=false
```

---

#### `TOKEN_REFRESH_INTERVAL_CYCLES`
- **Type**: Integer
- **Default**: `2`
- **Location**: `apps/api/workers/email_watcher_worker.py:66`
- **Purpose**: Run refresh every N poll cycles (each cycle = 60s)
- **Range**: 1-10
- **Actual Frequency**: `INTERVAL_CYCLES * 60 seconds`

**Examples**:
- `2` = Every 120 seconds (default, recommended)
- `1` = Every 60 seconds (more aggressive, higher API load)
- `3` = Every 180 seconds (less aggressive, more 401 risk)

**When to change**:
- Increase to `3-4` if hitting Microsoft rate limits frequently
- Decrease to `1` if users experience many 401 errors

```bash
# More aggressive refresh (every 60s)
export TOKEN_REFRESH_INTERVAL_CYCLES=1

# Less aggressive refresh (every 180s)
export TOKEN_REFRESH_INTERVAL_CYCLES=3
```

---

#### `TOKEN_REFRESH_LOOKAHEAD_SECONDS`
- **Type**: Integer
- **Default**: `300` (5 minutes)
- **Location**: `apps/api/integrations/graph_client.py:960`
- **Purpose**: Refresh tokens expiring within this window
- **Range**: 60-600 (1-10 minutes)
- **Recommended**: 300 (5 minutes)

**When to change**:
- Increase to `600` (10 min) if refresh latency is high
- Decrease to `180` (3 min) to reduce API load

```bash
# More conservative (10 min lookahead)
export TOKEN_REFRESH_LOOKAHEAD_SECONDS=600

# Tighter window (3 min lookahead)
export TOKEN_REFRESH_LOOKAHEAD_SECONDS=180
```

---

#### `TOKEN_REFRESH_COOLDOWN_SECONDS`
- **Type**: Integer
- **Default**: `600` (10 minutes)
- **Location**: `apps/api/integrations/graph_client.py:960`
- **Purpose**: Don't refresh tokens if already refreshed within this window
- **Range**: 300-1800 (5-30 minutes)
- **Recommended**: 600 (10 minutes)

**When to change**:
- Increase to `900` (15 min) to reduce API load
- Decrease to `300` (5 min) if tokens expiring quickly

```bash
# Longer cooldown (less API load)
export TOKEN_REFRESH_COOLDOWN_SECONDS=900
```

---

#### `TOKEN_REFRESH_ACTIVITY_DAYS`
- **Type**: Integer
- **Default**: `14`
- **Location**: `apps/api/integrations/graph_client.py:960`
- **Purpose**: Only refresh tokens for watchers active in last N days
- **Range**: 1-90
- **Recommended**: 14

**When to change**:
- Increase to `30` if many users are intermittent
- Decrease to `7` to reduce load for inactive users

```bash
# Only refresh very active users
export TOKEN_REFRESH_ACTIVITY_DAYS=7
```

---

#### `TOKEN_REFRESH_BATCH_LIMIT`
- **Type**: Integer
- **Default**: `50`
- **Location**: `apps/api/integrations/graph_client.py:960`
- **Purpose**: Max tokens to refresh per heartbeat cycle
- **Range**: 10-100
- **Recommended**: 50

**When to change**:
- Decrease to `25` if hitting rate limits
- Increase to `75` if many tokens expiring (with monitoring)

**Formula**: `batch_limit * cycles_per_hour / 60 = tokens_per_minute`
- Default: `50 * 30 / 60 = 25 tokens/min`

```bash
# Reduce load during high traffic
export TOKEN_REFRESH_BATCH_LIMIT=25
```

---

#### `TOKEN_REFRESH_JITTER_MAX_SECONDS`
- **Type**: Integer
- **Default**: `20`
- **Location**: `apps/api/integrations/graph_client.py:960`
- **Purpose**: Random delay per token to avoid thundering herd
- **Range**: 0-60
- **Recommended**: 20

**When to change**:
- Increase to `30-40` if seeing API bursts
- Decrease to `10` for faster refresh cycles

```bash
# More jitter (spread out requests)
export TOKEN_REFRESH_JITTER_MAX_SECONDS=30
```

---

### Backoff Settings (M6: Exponential Backoff)

#### `TOKEN_REFRESH_BACKOFF_BASE_SECONDS`
- **Type**: Integer
- **Default**: `60`
- **Location**: `apps/api/integrations/graph_client.py:170`
- **Purpose**: Base delay for exponential backoff (doubles each failure)
- **Range**: 30-300
- **Recommended**: 60

**Progression with default (60s)**:
- 1st failure: 60s ± 12s
- 2nd failure: 120s ± 24s
- 3rd failure: 240s ± 48s

```bash
# Faster retry (more aggressive)
export TOKEN_REFRESH_BACKOFF_BASE_SECONDS=30

# Slower retry (less aggressive)
export TOKEN_REFRESH_BACKOFF_BASE_SECONDS=120
```

---

#### `TOKEN_REFRESH_BACKOFF_MAX_SECONDS`
- **Type**: Integer
- **Default**: `3600` (1 hour)
- **Location**: `apps/api/integrations/graph_client.py:170`
- **Purpose**: Cap for exponential backoff delay
- **Range**: 600-7200 (10 min - 2 hours)
- **Recommended**: 3600 (1 hour)

```bash
# Shorter max backoff
export TOKEN_REFRESH_BACKOFF_MAX_SECONDS=1800  # 30 minutes
```

---

#### `TOKEN_REFRESH_MAX_FAILURES`
- **Type**: Integer
- **Default**: `10`
- **Location**: `apps/api/integrations/graph_client.py:233`
- **Purpose**: Auto-revoke token after N consecutive failures
- **Range**: 5-20
- **Recommended**: 10

**When to change**:
- Decrease to `5` to fail faster (force user reconnect sooner)
- Increase to `15` to be more patient with transient errors

```bash
# More aggressive auto-revoke
export TOKEN_REFRESH_MAX_FAILURES=5
```

---

### Rate Limit Settings (M6: Budget Protection)

#### `TOKEN_REFRESH_RATE_LIMIT_REQUESTS`
- **Type**: Integer
- **Default**: `100`
- **Location**: `apps/api/integrations/graph_client.py:119`
- **Purpose**: Max refresh attempts per sliding window
- **Range**: 50-200
- **Recommended**: 100

**Context**: Microsoft Graph allows ~5000 requests/10min per application. We budget conservatively at 100 token refreshes to leave headroom for other API calls.

**When to change**:
- Increase to `150` if you have few other Graph API calls
- Decrease to `50` during Microsoft outages

```bash
# More aggressive budget
export TOKEN_REFRESH_RATE_LIMIT_REQUESTS=150
```

---

#### `TOKEN_REFRESH_RATE_LIMIT_WINDOW_SECONDS`
- **Type**: Integer
- **Default**: `600` (10 minutes)
- **Location**: `apps/api/integrations/graph_client.py:119`
- **Purpose**: Sliding window duration for rate limit
- **Range**: 300-1200 (5-20 minutes)
- **Recommended**: 600 (10 minutes, matches Microsoft's window)

```bash
# Match Microsoft's exact window
export TOKEN_REFRESH_RATE_LIMIT_WINDOW_SECONDS=600
```

---

### Azure App Configuration

#### Read App (Mail.Read scope)

```bash
# Azure AD app ID for reading emails
export AZURE_READ_APP_ID="41f6dc82-8127-4330-97e0-c6b26e6aa967"

# Client secret for read app
export AZURE_READ_CLIENT_SECRET="<secret>"
```

**Location**:
- Config loading: `apps/api/integrations/graph_client.py:50`
- Usage: `apps/api/integrations/graph_client.py:100` (refresh_access_token)

**When to rotate**:
- Every 90 days (recommended)
- Immediately if secret compromised

---

#### Write App (Mail.Send scope)

```bash
# Azure AD app ID for sending emails
export AZURE_WRITE_APP_ID="f0b8944b-8127-4f0f-8ed5-5487462df50c"

# Client secret for write app
export AZURE_WRITE_CLIENT_SECRET="<secret>"
```

**Location**: `apps/api/integrations/graph_client.py:54`

---

## Tuning Strategies

### High Throughput (Many Users)

**Goal**: Maximize tokens refreshed per hour without hitting rate limits

```bash
# Refresh more frequently
export TOKEN_REFRESH_INTERVAL_CYCLES=1  # Every 60s instead of 120s

# Larger batches (monitor rate limit usage!)
export TOKEN_REFRESH_BATCH_LIMIT=75

# Shorter cooldown (but not too short)
export TOKEN_REFRESH_COOLDOWN_SECONDS=480  # 8 minutes

# Higher rate limit budget (if <2000 other API calls/10min)
export TOKEN_REFRESH_RATE_LIMIT_REQUESTS=150
```

**Estimated throughput**: 75 tokens * 60 cycles/hour = 4500 tokens/hour

**Monitor**: Rate limit budget usage should stay < 90%

---

### Low Throughput (Few Users, Cost Sensitive)

**Goal**: Minimize API calls while maintaining good UX

```bash
# Refresh less frequently
export TOKEN_REFRESH_INTERVAL_CYCLES=3  # Every 180s

# Smaller batches
export TOKEN_REFRESH_BATCH_LIMIT=25

# Longer cooldown
export TOKEN_REFRESH_COOLDOWN_SECONDS=900  # 15 minutes

# Larger lookahead window (safety buffer)
export TOKEN_REFRESH_LOOKAHEAD_SECONDS=600  # 10 minutes
```

**Estimated throughput**: 25 tokens * 20 cycles/hour = 500 tokens/hour

---

### Microsoft Graph Rate Limiting (429 Responses)

**Goal**: Back off to avoid hitting Microsoft's limits

```bash
# Reduce frequency
export TOKEN_REFRESH_INTERVAL_CYCLES=4  # Every 240s

# Smaller batches
export TOKEN_REFRESH_BATCH_LIMIT=20

# More jitter (spread requests)
export TOKEN_REFRESH_JITTER_MAX_SECONDS=40

# Lower rate limit budget (leave more headroom)
export TOKEN_REFRESH_RATE_LIMIT_REQUESTS=50
```

**Note**: M6 exponential backoff automatically handles 429s. This is for persistent issues.

---

### Aggressive Recovery (After Outage)

**Goal**: Quickly recover many expired tokens

```bash
# Very frequent refresh
export TOKEN_REFRESH_INTERVAL_CYCLES=1  # Every 60s

# Large batches (temporary!)
export TOKEN_REFRESH_BATCH_LIMIT=100

# Wide lookahead
export TOKEN_REFRESH_LOOKAHEAD_SECONDS=900  # 15 minutes

# Temporarily ignore cooldown (DANGEROUS - monitor closely)
export TOKEN_REFRESH_COOLDOWN_SECONDS=60  # 1 minute
```

**⚠️ WARNING**: Revert to defaults after recovery! This config can hit rate limits.

---

## Safe Tuning Guidelines

### Before Changing Config

1. **Baseline metrics** (record current state):
   ```sql
   SELECT count(*) as total_tokens FROM auth_microsoft_tokens WHERE is_revoked = false;
   SELECT count(*) as expiring_soon FROM auth_microsoft_tokens
   WHERE expires_at < now() + interval '10 minutes' AND is_revoked = false;
   ```

2. **Check current refresh rate** (from logs):
   ```bash
   grep "ProactiveRefresh.*Cycle complete" logs | grep "refreshed.*total" | tail -20
   ```

3. **Check rate limit usage**:
   ```bash
   grep "rate_limit_budget" logs | tail -10
   ```

### After Changing Config

1. **Monitor for 30 minutes**
2. **Check metrics**:
   - Token refresh success rate (should stay > 99%)
   - Rate limit budget usage (should stay < 90%)
   - Tokens expiring soon (should decrease)
3. **Watch for alerts**:
   - 429 errors from Microsoft
   - Rate limit budget exhausted warnings
   - Degraded watcher count increasing

### Rollback if Needed

```bash
# Revert to safe defaults
unset TOKEN_REFRESH_INTERVAL_CYCLES
unset TOKEN_REFRESH_BATCH_LIMIT
unset TOKEN_REFRESH_COOLDOWN_SECONDS
unset TOKEN_REFRESH_RATE_LIMIT_REQUESTS

# Restart worker to apply defaults
```

---

## Configuration by Environment

### Production

**File**: `.env.production` or Render environment variables

```bash
# Balanced for reliability and efficiency
TOKEN_REFRESH_HEARTBEAT_ENABLED=true
TOKEN_REFRESH_INTERVAL_CYCLES=2
TOKEN_REFRESH_LOOKAHEAD_SECONDS=300
TOKEN_REFRESH_COOLDOWN_SECONDS=600
TOKEN_REFRESH_BATCH_LIMIT=50
TOKEN_REFRESH_JITTER_MAX_SECONDS=20

# M6: Safe defaults
TOKEN_REFRESH_BACKOFF_BASE_SECONDS=60
TOKEN_REFRESH_BACKOFF_MAX_SECONDS=3600
TOKEN_REFRESH_MAX_FAILURES=10
TOKEN_REFRESH_RATE_LIMIT_REQUESTS=100
TOKEN_REFRESH_RATE_LIMIT_WINDOW_SECONDS=600
```

### Staging

**File**: `.env.staging`

```bash
# More aggressive for testing, lower throughput
TOKEN_REFRESH_HEARTBEAT_ENABLED=true
TOKEN_REFRESH_INTERVAL_CYCLES=1  # Faster cycles for testing
TOKEN_REFRESH_LOOKAHEAD_SECONDS=300
TOKEN_REFRESH_COOLDOWN_SECONDS=300  # Shorter cooldown for testing
TOKEN_REFRESH_BATCH_LIMIT=10  # Fewer users
TOKEN_REFRESH_JITTER_MAX_SECONDS=10

# M6: Faster failure for testing
TOKEN_REFRESH_BACKOFF_BASE_SECONDS=30
TOKEN_REFRESH_MAX_FAILURES=5  # Fail faster to test UI
TOKEN_REFRESH_RATE_LIMIT_REQUESTS=50  # Lower budget for staging
```

### Development

**File**: `.env.local`

```bash
# Minimal load, fast feedback
TOKEN_REFRESH_HEARTBEAT_ENABLED=true
TOKEN_REFRESH_INTERVAL_CYCLES=1
TOKEN_REFRESH_BATCH_LIMIT=5
TOKEN_REFRESH_COOLDOWN_SECONDS=60
TOKEN_REFRESH_BACKOFF_BASE_SECONDS=15
TOKEN_REFRESH_MAX_FAILURES=3
```

---

## Capacity Planning

### Formulas

**Tokens refreshed per hour**:
```
tokens_per_hour = BATCH_LIMIT * (3600 / (INTERVAL_CYCLES * 60))
```

**API calls per hour** (including jitter):
```
api_calls_per_hour = tokens_per_hour * (1 + jitter_overhead)
# jitter_overhead ≈ 0.5 (depends on JITTER_MAX_SECONDS)
```

**Budget utilization** (per 10-min window):
```
utilization = (BATCH_LIMIT * (600 / (INTERVAL_CYCLES * 60))) / RATE_LIMIT_REQUESTS
```

### Examples

**Default config** (BATCH=50, INTERVAL=2):
- Tokens/hour: 50 * (3600/120) = 1500
- Budget/10min: 50 * (600/120) = 250 attempts
- Utilization: 250 / 100 = 250% (⚠️ will hit rate limit!)
  - **But**: Filtered by cooldown, activity, backoff
  - **Actual**: ~50-100 tokens/10min = 50-100% utilization

**High throughput** (BATCH=75, INTERVAL=1):
- Tokens/hour: 75 * 60 = 4500
- Budget/10min: 75 * 10 = 750 attempts
- Utilization: 750 / 150 = 500% (⚠️ needs filtering)

**Key insight**: Batch size sets **ceiling**, but filters (cooldown, activity, backoff) reduce **actual** refresh count to stay within budget.

---

## Related Documentation

- [Architecture Overview](./TOKEN_REFRESH_ARCHITECTURE.md)
- [Operational Runbook](./TOKEN_REFRESH_RUNBOOK.md)
- [Troubleshooting Guide](./TOKEN_REFRESH_TROUBLESHOOTING.md)
