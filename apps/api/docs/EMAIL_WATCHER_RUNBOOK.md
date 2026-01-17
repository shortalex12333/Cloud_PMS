# Email Watcher Runbook

## Overview

The Email Watcher is a background worker that monitors connected Microsoft 365 mailboxes and automatically links email threads to PMS objects (work orders, equipment, parts, vendors).

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Render Worker  │────▶│  Microsoft Graph │────▶│  Email Threads  │
│  (60s polling)  │     │  Delta Sync API  │     │  + Messages     │
└─────────────────┘     └──────────────────┘     └─────────────────┘
         │                                                │
         │                                                ▼
         │                                       ┌─────────────────┐
         │                                       │  Token Extract  │
         │                                       │  (WO-####, etc) │
         │                                       └─────────────────┘
         │                                                │
         ▼                                                ▼
┌─────────────────┐                              ┌─────────────────┐
│  Rate Limiter   │                              │  Linking Ladder │
│  (9,500/hour)   │                              │  (L1 → L5)      │
└─────────────────┘                              └─────────────────┘
                                                          │
                                                          ▼
                                                 ┌─────────────────┐
                                                 │  Email Links    │
                                                 │  (suggestions)  │
                                                 └─────────────────┘
```

## Key Configuration

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| EMAIL_WATCHER_ENABLED | false | Master switch for the worker |
| EMAIL_WATCHER_POLL_INTERVAL | 60 | Seconds between sync cycles |
| EMAIL_WATCHER_BATCH_SIZE | 10 | Max watchers to process per cycle |

## Rate Limits

Microsoft Graph API has a hard limit of **10,000 calls/hour** per application.

- Safety margin: Stop at **9,500** calls
- Rate tracking: `email_watchers.api_calls_this_hour`
- Window reset: Hourly via `hour_window_start`

## Linking Ladder (Priority Order)

| Level | Match Type | Score | Action |
|-------|-----------|-------|--------|
| L1 | Explicit ID (WO-1234) | 120+ | Auto-link |
| L2 | Procurement signal + vendor | 70-120 | Suggest |
| L3 | Serial/part number match | 70-100 | Suggest |
| L4 | Open WO by vendor | 45-70 | Weak suggest |
| L5 | No match | 0 | Create procurement intent |

## Troubleshooting

### Worker Not Syncing

1. Check if worker is enabled:
   ```sql
   SELECT * FROM email_watchers WHERE is_paused = false;
   ```

2. Check for rate limiting:
   ```sql
   SELECT user_id, api_calls_this_hour, hour_window_start
   FROM email_watchers
   WHERE api_calls_this_hour > 9000;
   ```

3. Check Render logs:
   ```bash
   render logs celeste-email-watcher
   ```

### Token Expired Errors

1. Check token expiry:
   ```sql
   SELECT user_id, token_expires_at, token_purpose
   FROM auth_microsoft_tokens
   WHERE token_expires_at < NOW();
   ```

2. User needs to re-authorize via `/api/auth/microsoft/connect`

### Degraded Watchers

1. Find degraded watchers:
   ```sql
   SELECT id, user_id, sync_status, last_sync_error
   FROM email_watchers
   WHERE sync_status = 'degraded';
   ```

2. Reset status after fixing:
   ```sql
   UPDATE email_watchers
   SET sync_status = 'active', last_sync_error = NULL
   WHERE id = '<watcher_id>';
   ```

### Missing Links

1. Check if tokens were extracted:
   ```sql
   SELECT id, latest_subject, extracted_tokens
   FROM email_threads
   WHERE extracted_tokens IS NULL
   ORDER BY created_at DESC
   LIMIT 20;
   ```

2. Manually trigger linking (if needed):
   ```python
   # In Python console
   from services.linking_ladder import LinkingLadder
   ladder = LinkingLadder(supabase)
   await ladder.determine_primary(yacht_id, thread_id, ...)
   ```

## Monitoring Queries

Run these from `apps/api/scripts/email_watcher_health.sql`:

1. **Watcher Status Overview** - All watchers and sync times
2. **Rate Limit Status** - Who's approaching limits
3. **Degraded Watchers** - Errors needing attention
4. **Thread Statistics** - Volume metrics
5. **Link Suggestion Stats** - Linking performance
6. **Unlinked Threads** - Threads without suggestions
7. **User Decision Analytics** - Accept/reject rates
8. **Acceptance by Score** - Score threshold tuning

## Common Operations

### Pause a Watcher

```sql
UPDATE email_watchers
SET is_paused = true, pause_reason = 'Manual pause for investigation'
WHERE id = '<watcher_id>';
```

### Resume a Watcher

```sql
UPDATE email_watchers
SET is_paused = false, pause_reason = NULL
WHERE id = '<watcher_id>';
```

### Reset Rate Limit Counter

```sql
UPDATE email_watchers
SET api_calls_this_hour = 0, hour_window_start = NOW()
WHERE id = '<watcher_id>';
```

### Force Re-sync a Watcher

```sql
UPDATE email_watchers
SET last_sync_at = NOW() - INTERVAL '1 hour'
WHERE id = '<watcher_id>';
```

### Clear Delta Links (Full Re-sync)

```sql
UPDATE email_watchers
SET delta_link_inbox = NULL, delta_link_sent = NULL
WHERE id = '<watcher_id>';
```

## Scoring Reference

| Signal | Points | Notes |
|--------|--------|-------|
| WO/PO/EQ ID match | 120 | Auto-confirm threshold |
| Part number match | 70 | Strong signal |
| Serial number match | 70 | Strong signal |
| Vendor email match | 45 | Context signal |
| Vendor domain match | 30 | Weak signal |
| Open status bonus | 20 | Added to WO matches |
| Recent update (7d) | 15 | Added for active items |
| Vendor affinity | 15 | Learned from history |

### Thresholds

| Threshold | Score | Action |
|-----------|-------|--------|
| Auto-confirm | 130+ | Create active link automatically |
| Strong suggest | 100-129 | Show as primary suggestion |
| Weak suggest | 70-99 | Show as secondary option |
| No suggest | <70 | Don't show suggestion |

## Deployment

### Enable Worker

1. Set environment variable in Render:
   ```
   EMAIL_WATCHER_ENABLED=true
   ```

2. Verify worker starts:
   ```
   render logs celeste-email-watcher --tail
   ```

### Disable Worker

1. Set environment variable:
   ```
   EMAIL_WATCHER_ENABLED=false
   ```

2. Worker will exit gracefully on next poll cycle

## Files Reference

| File | Purpose |
|------|---------|
| `workers/email_watcher_worker.py` | Main background worker loop |
| `services/email_sync_service.py` | Microsoft Graph delta sync |
| `services/token_extractor.py` | Pattern extraction from emails |
| `services/candidate_finder.py` | PMS object candidate queries |
| `services/scoring_engine.py` | Scoring and ranking |
| `services/linking_ladder.py` | L1-L5 linking logic |
| `services/confirmation_tracker.py` | User decision recording |
| `services/rate_limiter.py` | API rate limit enforcement |
| `scripts/send_test_emails.py` | Test email generation |
| `tests/test_email_watcher.py` | Integration tests |
