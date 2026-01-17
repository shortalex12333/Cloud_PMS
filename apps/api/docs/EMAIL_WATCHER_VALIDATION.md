# Email Watcher - Production Validation Checklist

## Pre-Deployment Checklist

### 1. Database Migration (MANUAL STEP REQUIRED)
- [ ] Apply migration SQL via Supabase Dashboard
  - File: `/private/tmp/claude/.../scratchpad/APPLY_THIS_MIGRATION.sql`
  - Or copy from: Apps > API > Scripts folder
  - URL: https://supabase.com/dashboard/project/vzsohavtuotocgrfkfyd/sql

### 2. Verify Migration Applied
Run these queries in Supabase SQL Editor:

```sql
-- Check new columns
SELECT column_name FROM information_schema.columns
WHERE table_name = 'email_watchers' AND column_name = 'api_calls_this_hour';

SELECT column_name FROM information_schema.columns
WHERE table_name = 'email_links' AND column_name = 'is_primary';

-- Check new tables
SELECT table_name FROM information_schema.tables
WHERE table_name IN ('procurement_intents', 'email_link_decisions', 'vendors');

-- Check functions
SELECT routine_name FROM information_schema.routines
WHERE routine_name LIKE '%email%';
```

### 3. Environment Variables in Render
- [ ] `EMAIL_WATCHER_ENABLED=true`
- [ ] `EMAIL_WATCHER_POLL_INTERVAL=60`
- [ ] `EMAIL_WATCHER_BATCH_SIZE=10`
- [ ] `SUPABASE_URL=https://vzsohavtuotocgrfkfyd.supabase.co`
- [ ] `SUPABASE_SERVICE_KEY=<set from env vars>`
- [ ] `MICROSOFT_CLIENT_ID_READ=<set from env vars>`
- [ ] `MICROSOFT_CLIENT_SECRET_READ=<set from env vars>`

### 4. Test User Setup
- [ ] Test user has authorized READ app
- [ ] Test user has a watcher entry in `email_watchers`
- [ ] Test yacht ID: `85fe1119-b04c-41ac-80f1-829d23322598`

## Post-Deployment Validation

### 5. Worker Health Check
```sql
-- Check worker is syncing
SELECT id, user_id, last_sync_at, sync_status, api_calls_this_hour
FROM email_watchers
ORDER BY last_sync_at DESC;
```

### 6. Send Test Emails
```bash
cd apps/api
python scripts/send_test_emails.py --scenario wo_match --to x@alex-short.com
python scripts/send_test_emails.py --scenario vendor_quote --to x@alex-short.com
```

### 7. Verify Link Suggestions
Wait 2-3 minutes after sending test emails, then check:

```sql
-- Check for new threads
SELECT id, latest_subject, extracted_tokens, suggestions_generated_at
FROM email_threads
WHERE created_at > NOW() - INTERVAL '1 hour'
ORDER BY created_at DESC;

-- Check for link suggestions
SELECT el.*, et.latest_subject
FROM email_links el
JOIN email_threads et ON el.thread_id = et.id
WHERE el.created_at > NOW() - INTERVAL '1 hour'
ORDER BY el.created_at DESC;
```

### 8. Validate Scoring
Expected scores for test scenarios:

| Scenario | Expected Score | Expected Action |
|----------|---------------|-----------------|
| wo_match (WO-1234) | 120+ | auto_link |
| po_match (PO#5678) | 120+ | auto_link |
| vendor_quote | 70-100 | suggest |
| serial_match | 70-100 | suggest |
| ambiguous | <70 | no suggestion |

### 9. Rate Limit Validation
```sql
-- Check rate limit tracking
SELECT user_id, api_calls_this_hour, hour_window_start,
       9500 - api_calls_this_hour as calls_remaining
FROM email_watchers
WHERE api_calls_this_hour > 0;
```

## Rollback Procedure

If issues occur:

### 1. Disable Worker
```bash
# In Render Dashboard
EMAIL_WATCHER_ENABLED=false
```

### 2. Pause All Watchers
```sql
UPDATE email_watchers SET is_paused = true, pause_reason = 'Emergency pause';
```

### 3. Clear Bad Data (if needed)
```sql
-- Remove suggestions from last hour
DELETE FROM email_links WHERE created_at > NOW() - INTERVAL '1 hour';

-- Clear extracted tokens
UPDATE email_threads SET extracted_tokens = '{}', suggestions_generated_at = NULL
WHERE suggestions_generated_at > NOW() - INTERVAL '1 hour';
```

## Gradual Rollout

### Phase 1: Single User Testing
1. Enable for test user only
2. Monitor for 24 hours
3. Check acceptance rates

### Phase 2: Limited Production
1. Enable for 10% of watchers
2. Monitor rate limits
3. Tune scoring thresholds

### Phase 3: Full Rollout
1. Enable for all watchers
2. Set `EMAIL_WATCHER_AUTO_LINK=true` for auto-confirm
3. Monitor and iterate

## Success Criteria

- [ ] Worker runs without crashes for 24+ hours
- [ ] Rate limits never exceeded
- [ ] Link suggestions have >60% acceptance rate
- [ ] No token expiry errors (users stay connected)
- [ ] Delta links maintained (incremental sync working)

## Files Created

| File | Purpose |
|------|---------|
| `services/rate_limiter.py` | Microsoft Graph rate limiting |
| `services/token_extractor.py` | Email pattern extraction |
| `services/candidate_finder.py` | PMS object matching |
| `services/scoring_engine.py` | Scoring and ranking |
| `services/linking_ladder.py` | L1-L5 linking logic |
| `services/email_sync_service.py` | Delta sync pipeline |
| `services/confirmation_tracker.py` | User decision tracking |
| `workers/email_watcher_worker.py` | Background worker |
| `scripts/send_test_emails.py` | Test email generation |
| `scripts/email_watcher_health.sql` | Monitoring queries |
| `tests/test_email_watcher.py` | Integration tests (29 tests) |
| `docs/EMAIL_WATCHER_RUNBOOK.md` | Operations runbook |
| `docs/EMAIL_WATCHER_VALIDATION.md` | This checklist |
