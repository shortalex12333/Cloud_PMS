# QA BLOCKERS - CelesteOS

**Generated:** 2026-01-18
**Status:** LAUNCH BLOCKED

---

## CRITICAL BLOCKERS

### BLOCKER-001: yacht_id NULL in Search Requests

**Severity:** CRITICAL
**Impact:** All search functionality broken
**Discovered:** 2026-01-18 via E2E test

**Evidence:**
```json
// From C1_api_requests.json
{
  "url": "https://pipeline-core.int.celeste7.ai/webhook/search",
  "postData": "{\"query\":\"test\",\"auth\":{\"user_id\":\"a0d66b00-...\",\"yacht_id\":null,\"role\":\"Engineer\",...}}"
}
```

**Expected:** `yacht_id: "85fe1119-b04c-41ac-80f1-829d23322598"`
**Actual:** `yacht_id: null`

**Root Cause Investigation:**
1. Check `useAuth` hook - is yacht_id populated after bootstrap?
2. Check `AuthContext` - is yacht_id stored correctly?
3. Check `useCelesteSearch` hook - is auth context being read?
4. Check bootstrap flow - is `get_my_bootstrap` returning yacht_id?

**Files to Check:**
- `/apps/web/src/hooks/useAuth.ts`
- `/apps/web/src/contexts/AuthContext.tsx`
- `/apps/web/src/hooks/useCelesteSearch.ts`

**Acceptance Criteria:**
- [ ] Search requests include correct yacht_id
- [ ] Search returns results for "generator" query
- [ ] RLS policies enforce yacht isolation

---

### BLOCKER-002: data-testid Not in Production

**Severity:** HIGH
**Impact:** E2E tests unreliable, cannot use proper selectors

**Current State:**
- Local code has data-testid added to:
  - SpotlightSearch.tsx (`search-input`, `search-results`, `no-results`, `search-error`)
  - SpotlightResultRow.tsx (`search-result-item`)
  - EmailInboxView.tsx (`email-inbox`, `email-list`, `email-thread-item`, `link-email-button`)
  - EmailPanel.tsx (`email-panel`)

**Not in Production:**
All of the above - changes are local only.

**Fix Required:**
Deploy the code changes to production via:
```bash
git add apps/web/src/components/
git commit -m "feat: Add data-testid for E2E testing"
git push origin main
# Wait for Vercel auto-deploy
```

**Acceptance Criteria:**
- [ ] `[data-testid="search-input"]` visible in production DOM
- [ ] `[data-testid="search-results"]` rendered when results exist
- [ ] `[data-testid="email-panel"]` exists in DOM

---

### BLOCKER-003: EmailPanel is Placeholder

**Severity:** HIGH
**Impact:** Email journey cannot be tested or used

**Current State:**
EmailPanel.tsx shows:
```tsx
<div className="text-center py-12">
  <Inbox className="w-12 h-12 text-gray-600 mx-auto mb-4" />
  <p className="text-gray-400 text-sm">
    {folder === 'inbox' ? 'Inbox' : 'Sent'} will appear here
  </p>
  <p className="text-gray-500 text-xs mt-2">
    Connect your email to see messages
  </p>
</div>
```

**Required State:**
EmailPanel should render `<EmailInboxView />` component which actually exists and has the Link to Work functionality.

**Files to Modify:**
- `/apps/web/src/app/app/EmailPanel.tsx`
- Import and render `EmailInboxView` from `/components/email/EmailInboxView`

**Acceptance Criteria:**
- [ ] EmailPanel renders EmailInboxView when visible
- [ ] Email threads appear in list
- [ ] "Link to..." button is functional

---

## MEDIUM BLOCKERS

### BLOCKER-004: FaultCard Microactions Untestable

**Severity:** MEDIUM (blocked by BLOCKER-001)
**Impact:** Cannot verify microaction buttons work

**Current State:**
- FaultCard has data-testid attributes (7 buttons)
- But FaultCard never renders because search returns 0 results

**Dependency:** Fix BLOCKER-001 first, then re-test.

---

### BLOCKER-005: No Automated RLS Verification

**Severity:** MEDIUM
**Impact:** Cannot prove cross-yacht access is blocked

**Current State:**
- RLS policies exist in database
- But no test proves a user cannot access another yacht's data

**Required:**
Create test that:
1. Logs in as test user (yacht A)
2. Attempts to query yacht B data
3. Verifies access denied or empty result

---

## LOW BLOCKERS

### BLOCKER-006: Bootstrap Called 8+ Times

**Severity:** LOW
**Impact:** Performance/efficiency concern

**Evidence:** C1_api_requests.json shows 8 calls to `/v1/bootstrap`

**Possible Cause:**
- Multiple components calling bootstrap independently
- Missing caching/memoization
- React strict mode double-rendering

---

## BLOCKER RESOLUTION PRIORITY

1. **BLOCKER-001** (yacht_id NULL) - MUST FIX FIRST
2. **BLOCKER-003** (EmailPanel placeholder) - Blocks email feature
3. **BLOCKER-002** (data-testid deploy) - Blocks proper E2E
4. **BLOCKER-004** (Microactions) - Will resolve after #1
5. **BLOCKER-005** (RLS verification) - Security requirement
6. **BLOCKER-006** (Bootstrap calls) - Optimization

---

## WHEN BLOCKERS ARE RESOLVED

After fixing BLOCKER-001, re-run:
```bash
export $(grep -v '^#' .env.e2e | xargs) && \
npx playwright test tests/e2e/qa-evidence/real-e2e-evidence.spec.ts \
  --project=e2e-chromium --reporter=list
```

Expected outcome:
- B2 test should PASS (search returns results)
- E1 test should find microaction buttons
- New evidence files generated for verification

---

*Last updated: 2026-01-18*
