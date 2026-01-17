-- =============================================================================
-- Email Watcher - Health Check Queries
--
-- Run these queries in Supabase Dashboard to monitor email watcher health.
-- =============================================================================

-- 1. Watcher Status Overview
-- Shows all watchers and their current sync status
SELECT
    ew.id,
    ew.user_id,
    ew.yacht_id,
    y.name as yacht_name,
    ew.sync_status,
    ew.is_paused,
    ew.api_calls_this_hour,
    ew.last_sync_at,
    ew.last_sync_error,
    NOW() - ew.last_sync_at as time_since_sync
FROM email_watchers ew
LEFT JOIN yachts y ON ew.yacht_id = y.id
ORDER BY ew.last_sync_at DESC;


-- 2. Rate Limit Status
-- Check which watchers are approaching or at rate limit
SELECT
    ew.user_id,
    ew.yacht_id,
    ew.api_calls_this_hour,
    9500 - ew.api_calls_this_hour as calls_remaining,
    ew.hour_window_start,
    CASE
        WHEN ew.api_calls_this_hour >= 9500 THEN 'RATE_LIMITED'
        WHEN ew.api_calls_this_hour >= 8000 THEN 'WARNING'
        ELSE 'OK'
    END as rate_status
FROM email_watchers ew
WHERE ew.api_calls_this_hour > 5000
ORDER BY ew.api_calls_this_hour DESC;


-- 3. Degraded Watchers
-- Find watchers with errors that need attention
SELECT
    ew.id,
    ew.user_id,
    ew.yacht_id,
    ew.sync_status,
    ew.last_sync_error,
    ew.last_sync_at,
    ew.pause_reason
FROM email_watchers ew
WHERE ew.sync_status = 'degraded'
   OR ew.is_paused = true
ORDER BY ew.last_sync_at DESC;


-- 4. Thread Statistics (Last 24 Hours)
-- New threads and messages created
SELECT
    et.yacht_id,
    COUNT(DISTINCT et.id) as thread_count,
    COUNT(em.id) as message_count,
    MIN(et.created_at) as earliest_thread,
    MAX(et.created_at) as latest_thread
FROM email_threads et
LEFT JOIN email_messages em ON et.id = em.thread_id
WHERE et.created_at > NOW() - INTERVAL '24 hours'
GROUP BY et.yacht_id
ORDER BY thread_count DESC;


-- 5. Link Suggestion Statistics
-- How well is the linking ladder performing?
SELECT
    el.confidence,
    el.suggested_reason,
    COUNT(*) as count,
    COUNT(*) FILTER (WHERE el.is_active) as active_count,
    COUNT(*) FILTER (WHERE el.user_blocked) as blocked_count
FROM email_links el
WHERE el.created_at > NOW() - INTERVAL '7 days'
GROUP BY el.confidence, el.suggested_reason
ORDER BY count DESC;


-- 6. Unlinked Threads (Need Attention)
-- Threads with no active link suggestion
SELECT
    et.id,
    et.latest_subject,
    et.last_activity_at,
    et.extracted_tokens,
    et.participant_hashes
FROM email_threads et
LEFT JOIN email_links el ON et.id = el.thread_id AND el.is_active = true
WHERE el.id IS NULL
  AND et.created_at > NOW() - INTERVAL '7 days'
ORDER BY et.last_activity_at DESC
LIMIT 50;


-- 7. User Decision Analytics (Last 30 Days)
-- Track how users are responding to suggestions
SELECT
    eld.action,
    COUNT(*) as count,
    AVG(eld.system_score) as avg_score,
    MIN(eld.system_score) as min_score,
    MAX(eld.system_score) as max_score
FROM email_link_decisions eld
WHERE eld.created_at > NOW() - INTERVAL '30 days'
GROUP BY eld.action
ORDER BY count DESC;


-- 8. Acceptance Rate by Score Range
-- Which score ranges get accepted most?
SELECT
    CASE
        WHEN system_score >= 130 THEN '130+ (auto)'
        WHEN system_score >= 100 THEN '100-129 (strong)'
        WHEN system_score >= 70 THEN '70-99 (weak)'
        ELSE '< 70 (none)'
    END as score_range,
    COUNT(*) FILTER (WHERE action = 'accept') as accepts,
    COUNT(*) FILTER (WHERE action = 'reject') as rejects,
    COUNT(*) FILTER (WHERE action = 'change') as changes,
    COUNT(*) as total,
    ROUND(100.0 * COUNT(*) FILTER (WHERE action = 'accept') / NULLIF(COUNT(*), 0), 1) as acceptance_pct
FROM email_link_decisions
WHERE created_at > NOW() - INTERVAL '30 days'
GROUP BY 1
ORDER BY 1;


-- 9. Vendor Affinity Patterns
-- Which vendors are frequently linked to which object types?
SELECT
    substring(et.participant_hashes::text, 3, 16) as vendor_hash_prefix,
    eld.chosen_object_type,
    COUNT(*) as link_count
FROM email_link_decisions eld
JOIN email_threads et ON eld.thread_id = et.id
WHERE eld.action IN ('accept', 'change')
  AND eld.created_at > NOW() - INTERVAL '90 days'
GROUP BY 1, 2
HAVING COUNT(*) > 2
ORDER BY link_count DESC
LIMIT 50;


-- 10. Delta Link Health
-- Check if delta links are being maintained properly
SELECT
    ew.id,
    ew.yacht_id,
    CASE WHEN ew.delta_link_inbox IS NOT NULL THEN 'Has delta' ELSE 'No delta' END as inbox_delta,
    CASE WHEN ew.delta_link_sent IS NOT NULL THEN 'Has delta' ELSE 'No delta' END as sent_delta,
    ew.last_sync_at
FROM email_watchers ew
ORDER BY ew.last_sync_at DESC;
