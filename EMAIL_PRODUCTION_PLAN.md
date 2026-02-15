# Email System: 1-Week Production Readiness Plan

**Goal:** Transform email system from "demo-ready" to "production-grade"
**Start:** 2026-02-11
**Completion:** 2026-02-18
**Yacht:** 85fe1119-b04c-41ac-80f1-829d23322598

---

## Critical Issues Identified

| Priority | Issue | Impact | Root Cause |
|----------|-------|--------|------------|
| P0 | Thread 404 on detail fetch | Users see threads they can't open | RPC functions missing yacht_id filter |
| P0 | Cross-yacht data leak in inbox | Security vulnerability | `get_stale_link_threads` returns ALL yachts |
| P1 | "Session expired" banner shown | UX interruption | No silent Outlook token refresh |
| P1 | Token refresh requires user click | Workflow disruption | OAuth refresh not automated |
| P2 | Inconsistent API response shapes | Frontend errors | Backend returns different field names |
| P2 | Missing bulk operations | Slow batch workflows | No bulk link accept/reject |

---

## Day 1 (Tuesday): Security & Data Integrity

### Morning: Fix Critical RPC Functions

**Task 1.1: Patch `get_stale_link_threads` and `get_unlinked_threads_with_tokens`**

```sql
-- Migration: 20260211_fix_email_rpc_yacht_filtering.sql

-- FIX 1: get_stale_link_threads - Add yacht_id parameter
DROP FUNCTION IF EXISTS public.get_stale_link_threads(TIMESTAMPTZ, INTEGER);

CREATE OR REPLACE FUNCTION public.get_stale_link_threads(
    p_yacht_id UUID,  -- NEW: Required yacht filter
    p_cutoff TIMESTAMPTZ,
    p_limit INTEGER DEFAULT 20
)
RETURNS TABLE (
    id UUID,
    latest_subject TEXT,
    extracted_tokens JSONB,
    participant_hashes TEXT[],
    suggestions_generated_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ
)
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public
AS $$
    SELECT t.id, t.latest_subject, t.extracted_tokens,
           t.participant_hashes, t.suggestions_generated_at, t.updated_at
    FROM public.email_threads t
    WHERE t.yacht_id = p_yacht_id  -- CRITICAL FIX
      AND t.suggestions_generated_at IS NOT NULL
      AND t.updated_at > t.suggestions_generated_at
      AND t.created_at >= p_cutoff
    ORDER BY t.updated_at DESC
    LIMIT p_limit;
$$;

-- FIX 2: get_unlinked_threads_with_tokens - Add yacht_id parameter
DROP FUNCTION IF EXISTS public.get_unlinked_threads_with_tokens(TIMESTAMPTZ, INTEGER);

CREATE OR REPLACE FUNCTION public.get_unlinked_threads_with_tokens(
    p_yacht_id UUID,  -- NEW: Required yacht filter
    p_cutoff TIMESTAMPTZ,
    p_limit INTEGER DEFAULT 50
)
RETURNS TABLE (
    id UUID,
    latest_subject TEXT,
    extracted_tokens JSONB,
    participant_hashes TEXT[],
    created_at TIMESTAMPTZ
)
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public
AS $$
    SELECT t.id, t.latest_subject, t.extracted_tokens,
           t.participant_hashes, t.created_at
    FROM public.email_threads t
    WHERE t.yacht_id = p_yacht_id  -- CRITICAL FIX
      AND t.extracted_tokens IS NOT NULL
      AND t.suggestions_generated_at IS NOT NULL
      AND t.created_at >= p_cutoff
      AND NOT EXISTS (SELECT 1 FROM public.email_links el WHERE el.thread_id = t.id)
    ORDER BY t.created_at DESC
    LIMIT p_limit;
$$;
```

**Task 1.2: Update all callers to pass yacht_id**
- `apps/api/services/linking_ladder.py` - Update RPC calls
- `apps/api/routes/email.py` - Pass yacht_id from auth context

### Afternoon: Audit All Email Queries

**Task 1.3: Create yacht_id enforcement test**
```python
# tests/ci/test_email_yacht_isolation.py
"""CI test: Every email query MUST filter by yacht_id"""

@pytest.mark.parametrize("rpc_name", [
    "get_stale_link_threads",
    "get_unlinked_threads_with_tokens",
    "search_email_hybrid",
])
def test_rpc_requires_yacht_id(rpc_name):
    """Verify RPC function signature includes p_yacht_id parameter"""
    # Inspect function signature in pg_proc
    # Fail if yacht_id not in parameters
```

**Task 1.4: Add yacht_id to inbox response (already deployed per commit)**
- Verify `/email/inbox` returns `yacht_id` field
- Add to thread detail response as well

**Deliverable:** All email queries yacht-isolated, CI test prevents regression

---

## Day 2 (Wednesday): Token Management

### Morning: Implement Silent Outlook Refresh

**Task 2.1: Add backend refresh endpoint**
```python
# routes/auth_routes.py

@router.post("/auth/outlook/refresh")
async def refresh_outlook_token(
    user_context: dict = Depends(get_authenticated_user)
):
    """
    Silent refresh of Outlook OAuth token.
    Called by frontend before showing "Session expired" banner.
    """
    user_id = user_context["user_id"]
    yacht_id = user_context["yacht_id"]

    # Get current token
    token_record = await get_microsoft_token(user_id, yacht_id, purpose="read")
    if not token_record or token_record.is_revoked:
        return {"success": False, "reason": "no_token"}

    # Attempt refresh
    try:
        new_tokens = await refresh_microsoft_token(token_record.refresh_token)
        await update_microsoft_token(user_id, yacht_id, new_tokens)
        return {"success": True, "expires_at": new_tokens["expires_at"]}
    except TokenRefreshError as e:
        return {"success": False, "reason": str(e)}
```

**Task 2.2: Update frontend to try silent refresh first**
```typescript
// hooks/useEmailData.ts

const checkAndRefreshToken = async (): Promise<boolean> => {
  // Check if token expires in < 10 minutes
  if (outlookStatus?.expiresAt) {
    const expiresIn = new Date(outlookStatus.expiresAt).getTime() - Date.now();
    if (expiresIn < 10 * 60 * 1000) {
      // Try silent refresh
      const response = await fetch('/api/integrations/outlook/refresh', {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const result = await response.json();
      if (result.success) {
        // Refresh successful - update local state
        queryClient.invalidateQueries(['outlook-status']);
        return true;
      }
    }
  }
  return false;
};

// In useOutlookConnection:
useEffect(() => {
  if (outlookStatus?.isExpired) {
    // Try silent refresh BEFORE showing banner
    checkAndRefreshToken().then(refreshed => {
      if (!refreshed) {
        setNeedsReconnect(true); // Only show banner if refresh fails
      }
    });
  }
}, [outlookStatus?.isExpired]);
```

### Afternoon: Token Refresh Testing

**Task 2.3: Add proactive refresh timer**
```typescript
// Schedule refresh 5 minutes before expiry
useEffect(() => {
  if (!outlookStatus?.expiresAt) return;

  const expiresAt = new Date(outlookStatus.expiresAt).getTime();
  const refreshAt = expiresAt - 5 * 60 * 1000; // 5 min before
  const delay = refreshAt - Date.now();

  if (delay > 0) {
    const timer = setTimeout(() => {
      checkAndRefreshToken();
    }, delay);
    return () => clearTimeout(timer);
  }
}, [outlookStatus?.expiresAt]);
```

**Task 2.4: Remove "Session expired" banner for recoverable states**
- Only show banner if: token revoked OR refresh fails 3 times
- Add retry counter with exponential backoff
- Log refresh attempts for debugging

**Deliverable:** Token refresh is silent; banner only shows for unrecoverable states

---

## Day 3 (Thursday): API Consistency

### Morning: Normalize Response Shapes

**Task 3.1: Audit all email endpoints for response consistency**

| Endpoint | Current | Target |
|----------|---------|--------|
| `/email/inbox` | `{ threads: [...] }` | `{ threads: [...], yacht_id, total }` |
| `/email/thread/:id` | `{ thread, messages }` | `{ thread, messages, yacht_id }` |
| `/email/message/:id/render` | `{ body, ... }` | `{ body, attachments, webLink }` |
| `/email/search` | `{ results }` | `{ results, total, query }` |

**Task 3.2: Add TypeScript types for all responses**
```typescript
// types/email.ts

interface EmailInboxResponse {
  threads: EmailThread[];
  yacht_id: string;
  total: number;
  hasMore: boolean;
}

interface EmailThreadResponse {
  thread: EmailThread;
  messages: EmailMessage[];
  yacht_id: string;
  links: EmailLink[];
}

interface MessageRenderResponse {
  id: string;
  subject: string;
  body: { contentType: 'html' | 'text'; content: string };
  from: EmailAddress;
  toRecipients: EmailAddress[];
  ccRecipients: EmailAddress[];
  attachments: AttachmentMetadata[];
  webLink: string;
  sentAt: string;
}
```

### Afternoon: Error Handling

**Task 3.3: Standardize error responses**
```python
# middleware/error_handlers.py

class EmailError(Exception):
    """Base email error with standard response format"""
    def __init__(self, code: str, message: str, status: int = 400):
        self.code = code
        self.message = message
        self.status = status

# Usage:
raise EmailError("THREAD_NOT_FOUND", "Thread not found or access denied", 404)
raise EmailError("TOKEN_EXPIRED", "Outlook token expired, please reconnect", 401)
raise EmailError("RATE_LIMITED", "Too many requests, try again later", 429)
```

**Task 3.4: Frontend error boundary for email**
```typescript
// components/email/EmailErrorBoundary.tsx

const EmailErrorBoundary: React.FC = ({ children }) => {
  const { error, reset } = useEmailError();

  if (error?.code === 'TOKEN_EXPIRED') {
    return <ReconnectPrompt onReconnect={reset} />;
  }
  if (error?.code === 'THREAD_NOT_FOUND') {
    return <ThreadNotFound />;
  }
  // ... other error states

  return children;
};
```

**Deliverable:** Consistent API responses, typed interfaces, graceful error handling

---

## Day 4 (Friday): Performance & Reliability

### Morning: Query Optimization

**Task 4.1: Add missing indexes**
```sql
-- If not exists:
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_email_messages_yacht_direction_sent
ON email_messages(yacht_id, direction, sent_at DESC);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_email_threads_yacht_activity
ON email_threads(yacht_id, last_activity_at DESC);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_email_links_thread_active
ON email_links(thread_id) WHERE is_active = true;
```

**Task 4.2: Optimize inbox query (remove N+1)**
```python
# Current: Fetch threads, then fetch links for each
# Optimized: Single query with LEFT JOIN

SELECT
    et.*,
    COALESCE(json_agg(el.*) FILTER (WHERE el.id IS NOT NULL), '[]') as links
FROM email_threads et
LEFT JOIN email_links el ON el.thread_id = et.id AND el.is_active = true
WHERE et.yacht_id = :yacht_id
GROUP BY et.id
ORDER BY et.last_activity_at DESC
LIMIT 50;
```

### Afternoon: Caching & Rate Limiting

**Task 4.3: Add Redis caching for inbox (if not exists)**
```python
# Cache inbox results for 30 seconds
INBOX_CACHE_TTL = 30

async def get_inbox_cached(yacht_id: str, direction: str):
    cache_key = f"inbox:{yacht_id}:{direction}"
    cached = await redis.get(cache_key)
    if cached:
        return json.loads(cached)

    result = await fetch_inbox_from_db(yacht_id, direction)
    await redis.setex(cache_key, INBOX_CACHE_TTL, json.dumps(result))
    return result
```

**Task 4.4: Implement frontend request deduplication**
```typescript
// Prevent duplicate requests while one is in flight
const { data } = useQuery({
  queryKey: ['inbox', yachtId, direction],
  staleTime: 30000,  // 30 seconds
  refetchOnWindowFocus: false,
  refetchOnMount: false,
});
```

**Deliverable:** Sub-100ms inbox load, no redundant queries

---

## Day 5 (Saturday): Link Management UX

### Morning: Bulk Operations

**Task 5.1: Add bulk link accept/reject endpoint**
```python
@router.post("/email/links/bulk")
async def bulk_link_operation(
    request: BulkLinkRequest,
    user_context: dict = Depends(get_authenticated_user)
):
    """
    Accept or reject multiple link suggestions at once.
    """
    results = []
    for link_id in request.link_ids:
        try:
            if request.operation == "accept":
                await accept_email_link(link_id, user_context["user_id"])
            elif request.operation == "reject":
                await remove_email_link(link_id, user_context["user_id"])
            results.append({"link_id": link_id, "success": True})
        except Exception as e:
            results.append({"link_id": link_id, "success": False, "error": str(e)})

    return {"results": results, "total": len(results)}
```

**Task 5.2: Frontend bulk selection UI**
```typescript
// components/email/LinkSuggestionsList.tsx

const [selectedLinks, setSelectedLinks] = useState<Set<string>>(new Set());

const handleBulkAccept = async () => {
  await bulkLinkOperation({
    link_ids: Array.from(selectedLinks),
    operation: 'accept'
  });
  setSelectedLinks(new Set());
  refetch();
};
```

### Afternoon: Link Quality Improvements

**Task 5.3: Improve suggestion scoring display**
```typescript
// Show WHY a link was suggested
<div className="text-xs text-gray-500">
  {link.suggested_reason === 'token_match' && (
    <>Matched <code>{link.matched_token}</code> in subject</>
  )}
  {link.suggested_reason === 'vendor_domain' && (
    <>Sender domain matches supplier</>
  )}
  {link.suggested_reason === 'semantic' && (
    <>Similar content to work order</>
  )}
</div>
```

**Task 5.4: Add "Don't suggest this type" option**
```python
# Allow users to suppress future suggestions of same type
@router.post("/email/links/{link_id}/suppress")
async def suppress_link_type(link_id: str, ...):
    """User indicates this type of suggestion is not helpful"""
    # Store in email_link_suppressions table
    # Linking ladder checks suppressions before suggesting
```

**Deliverable:** Efficient bulk operations, transparent suggestion reasons

---

## Day 6 (Sunday): Integration Testing

### Morning: End-to-End Test Suite

**Task 6.1: Create email integration test harness**
```python
# tests/integration/test_email_e2e.py

class TestEmailCustomerJourney:
    """Full customer journey tests"""

    async def test_inbox_to_thread_to_link(self):
        """User opens inbox → clicks thread → accepts link"""
        # 1. Fetch inbox
        inbox = await client.get(f"/email/inbox?yacht_id={YACHT_ID}")
        assert inbox["yacht_id"] == YACHT_ID

        # 2. Open thread
        thread_id = inbox["threads"][0]["id"]
        thread = await client.get(f"/email/thread/{thread_id}")
        assert thread["yacht_id"] == YACHT_ID

        # 3. View message content
        message_id = thread["messages"][0]["provider_message_id"]
        content = await client.get(f"/email/message/{message_id}/render")
        assert "body" in content

        # 4. Accept suggested link
        link_id = thread["links"][0]["id"]
        result = await client.post(f"/email/link/{link_id}/accept")
        assert result["success"]

    async def test_cross_yacht_isolation(self):
        """Verify user cannot access other yacht's threads"""
        # Create thread for yacht A
        # Try to fetch from yacht B context
        # Expect 404
```

### Afternoon: Load Testing

**Task 6.2: Simulate production load**
```python
# tests/load/test_email_load.py

async def test_concurrent_inbox_loads():
    """50 concurrent inbox requests should complete in <2s"""
    tasks = [fetch_inbox(yacht_id) for _ in range(50)]
    results = await asyncio.gather(*tasks)
    # Assert all succeeded
    # Assert max latency < 500ms

async def test_search_under_load():
    """Search performance with 10 concurrent queries"""
    queries = ["main engine", "invoice", "PO-123", ...]
    # Measure p50, p95, p99 latencies
```

**Deliverable:** Comprehensive test coverage, performance baselines

---

## Day 7 (Monday): Production Deployment

### Morning: Final Verification

**Task 7.1: Pre-deployment checklist**
- [ ] All migrations applied to staging
- [ ] CI tests passing
- [ ] Token refresh tested manually
- [ ] Inbox loads in <100ms
- [ ] No cross-yacht data visible
- [ ] Error messages are user-friendly
- [ ] "Session expired" banner only shows for unrecoverable states

**Task 7.2: Deploy to production**
```bash
# 1. Apply migrations
supabase db push --linked

# 2. Deploy API
render deploy

# 3. Deploy web
vercel --prod

# 4. Verify in production
curl https://api.celesteos.app/health
```

### Afternoon: Monitoring & Alerts

**Task 7.3: Add production alerts**
```yaml
# alerts/email_alerts.yaml

alerts:
  - name: email_inbox_slow
    condition: p95_latency > 500ms
    severity: warning

  - name: email_token_refresh_failures
    condition: failure_rate > 10%
    severity: critical

  - name: email_cross_yacht_access_attempt
    condition: count > 0
    severity: critical

  - name: email_sync_backlog
    condition: pending_syncs > 100
    severity: warning
```

**Task 7.4: Create runbook**
```markdown
## Email System Runbook

### Token Refresh Failures
1. Check Microsoft Graph status: https://status.office365.com
2. Check rate limits in email_watchers table
3. Try manual refresh in Supabase dashboard

### Inbox Slow
1. Check pg_stat_statements for slow queries
2. Verify indexes exist
3. Check cache hit rate

### Cross-Yacht Access Alert
1. IMMEDIATELY revoke affected user sessions
2. Audit pms_audit_log for scope
3. Incident report
```

**Deliverable:** Production deployment complete, monitoring active

---

## Success Criteria

| Metric | Target | Measurement |
|--------|--------|-------------|
| Inbox load time | <100ms p95 | Datadog APM |
| Token refresh success | >99% | Logs |
| Cross-yacht access | 0 incidents | Alert count |
| "Session expired" shown | <1% of sessions | Analytics |
| Link suggestion acceptance | >50% | Audit log |
| Thread 404 errors | 0 | Error logs |

---

## Resources Required

- **Backend dev:** 5 days
- **Frontend dev:** 3 days
- **QA:** 2 days
- **DevOps:** 1 day (deployment + monitoring)

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Migration breaks existing data | Test on staging first, have rollback ready |
| Microsoft Graph outage | Graceful degradation, show cached data |
| Token refresh loop | Rate limit refresh attempts, circuit breaker |
| Performance regression | Load test before deploy, gradual rollout |

---

*Plan created: 2026-02-11*
*Last updated: 2026-02-11*
