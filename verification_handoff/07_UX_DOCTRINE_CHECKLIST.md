# 07_UX_DOCTRINE_CHECKLIST.md — UX Rules Enforcement

**Author:** Claude A (System Historian)
**Date:** 2026-01-19
**Purpose:** Define UX rules Claude B must enforce

---

## UX DOCTRINE RULES

### Rule 1: One URL

**Definition:** The app should feel like a single destination, not multiple pages.

**Pass Criteria:**
- URL bar shows single base URL (e.g., `apps.celeste7.ai`)
- Content changes without full page navigation
- Search is the primary navigation mechanism
- No deep nested routes like `/dashboard/email/thread/123`

**Current Violation (NOT VERIFIED):**
- Unknown — Did not visit production site

**Screenshot Criteria for Pass:**
- URL bar shows `apps.celeste7.ai` or `apps.celeste7.ai/` only
- No visible URL changes when clicking through content

---

### Rule 2: No Dashboards

**Definition:** No traditional dashboard layout with widgets/cards/metrics.

**Pass Criteria:**
- No "Dashboard" text visible
- No grid of stat cards or KPIs
- Entry point is search bar or context list
- Content appears as search results, not dashboard widgets

**Current Violation (NOT VERIFIED):**
- Check for `/dashboard` route in code
- Check for "Dashboard" in navigation

**Screenshot Criteria for Pass:**
- Main view is search-centric
- No stat cards, no "Your metrics" sections

---

### Rule 3: Email is a Surface Under Search

**Definition:** Email should appear as search results, not as a separate "Email" page in sidebar.

**Pass Criteria:**
- No "Email" or "Inbox" link in sidebar/navigation
- Searching "email from John" shows email results inline
- Email threads open as search result expansion, not new page
- Email is discoverable via search, not via nav menu

**Current Violation (NOT VERIFIED — B004):**
- Reported: Email may appear in sidebar
- Claude B must verify

**Screenshot Criteria for Pass:**
- Sidebar/nav has NO email icon or link
- Search "email" returns email results in main area
- Clicking email doesn't navigate to `/email` route

---

### Rule 4: Inbox = Reading, Email Search Separate

**Definition:** "Inbox" view is for reading recent emails. Email search is part of global search.

**Pass Criteria:**
- If inbox exists, it's for recent unread emails only
- Searching for email content uses global search
- No separate "Search emails" input

**Current Violation (NOT VERIFIED):**
- Unknown

**Screenshot Criteria for Pass:**
- One search bar for all content types
- No "Search emails only" filter or separate input

---

### Rule 5: Explicit "Nothing Found" Transparency

**Definition:** When search returns no results, user must see clear "nothing found" message.

**Pass Criteria:**
- Empty state says "No results found for [query]"
- No blank screen or spinner indefinitely
- Suggestion to try different terms (optional but good)

**Current Violation (NOT VERIFIED):**
- Unknown — search not working due to B001

**Screenshot Criteria for Pass:**
- Search nonsense term like "xyzzy123"
- Screen shows "No results found for 'xyzzy123'"
- No blank area or infinite spinner

---

### Rule 6: No Placeholder IDs

**Definition:** System must never use placeholder UUIDs when real ID is missing.

**Pass Criteria:**
- No `00000000-0000-0000-0000-000000000000` in any code path
- If yacht_id is missing, show error or pending screen
- No silent failures due to placeholder matching nothing

**Current Violation (NOT VERIFIED — B006):**
- Claude B must grep codebase for placeholder patterns

**Code Criteria for Pass:**
```bash
# Should return 0 matches
grep -r "00000000-0000-0000-0000-000000000000" apps/web/src/
```

---

### Rule 7: Loading States are Informative

**Definition:** Loading states should indicate what's happening, not just show spinner.

**Pass Criteria:**
- Loading spinner has context (e.g., "Loading documents...")
- No indefinite spinners without text
- Timeout shows error message, not endless spinner

**Current Violation (NOT VERIFIED):**
- Unknown

**Screenshot Criteria for Pass:**
- During loading, text explains what's loading
- After timeout (>30s), error message appears

---

### Rule 8: Errors are Actionable

**Definition:** Error messages should tell user what to do, not just what went wrong.

**Pass Criteria:**
- Errors include suggested action (retry, contact support, etc.)
- No cryptic error codes without explanation
- Network errors suggest checking connection

**Current Violation (NOT VERIFIED):**
- Unknown

**Screenshot Criteria for Pass:**
- Error message includes "Try again" button or suggestion
- Not just "Error: 401" without context

---

## VERIFICATION MATRIX

| Rule | ID | Verified? | Pass? | Evidence |
|------|-----|-----------|-------|----------|
| One URL | R1 | ❌ NOT VERIFIED | ? | Visit production |
| No Dashboards | R2 | ❌ NOT VERIFIED | ? | Visit production |
| Email as Search Surface | R3 | ❌ NOT VERIFIED | ? | Visit production |
| Inbox/Search Separation | R4 | ❌ NOT VERIFIED | ? | Visit production |
| Nothing Found Message | R5 | ❌ NOT VERIFIED | ? | Search nonsense |
| No Placeholder IDs | R6 | ❌ NOT VERIFIED | ? | Grep codebase |
| Informative Loading | R7 | ❌ NOT VERIFIED | ? | Visit production |
| Actionable Errors | R8 | ❌ NOT VERIFIED | ? | Trigger error |

---

## CLAUDE B VERIFICATION TASKS

### Task 1: Visit Production Site
1. Go to https://apps.celeste7.ai
2. Login as x@alex-short.com / Password2!
3. Screenshot the main interface

### Task 2: Check URL Pattern
1. Click through different content types
2. Note if URL changes
3. Screenshot URL bar at each step

### Task 3: Check Email Placement
1. Look for email in sidebar/navigation
2. Search "email" in search bar
3. Screenshot where email appears

### Task 4: Test Empty Search
1. Search "xyzzy123nonsense"
2. Screenshot the result
3. Verify "nothing found" message

### Task 5: Grep for Placeholders
```bash
grep -rn "00000000-0000-0000-0000-000000000000" apps/web/src/
grep -rn "placeholder" apps/web/src/ | grep -i yacht
grep -rn "|| null" apps/web/src/ | grep -i yacht
```

### Task 6: Test Error Handling
1. Disconnect network (or use DevTools offline)
2. Try to search
3. Screenshot error message

---

## EVIDENCE TEMPLATE

For each rule, Claude B should capture:

```markdown
### Rule X: [Name]

**Tested:** 2026-XX-XX
**Result:** PASS / FAIL

**Evidence:**
- Screenshot: [path or description]
- Steps taken: [what was done]
- Observations: [what was seen]

**If FAIL:**
- Location of violation: [file/component]
- Suggested fix: [brief description]
```

