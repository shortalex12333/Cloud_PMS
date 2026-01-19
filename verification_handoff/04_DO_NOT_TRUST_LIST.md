# 04_DO_NOT_TRUST_LIST.md — Unverified Claims Registry

**Author:** Claude A (System Historian)
**Date:** 2026-01-19
**Purpose:** Prevent Claude B from assuming these work

---

## RULE

**If something is on this list, Claude B must verify it before proceeding.**

Do not assume any of these work just because:
- Code exists
- Tests exist
- Previous reports claimed it works
- It "should" work based on architecture

---

## AUTHENTICATION / BOOTSTRAP

### U001: Bootstrap Endpoint Returns Valid Response
**What It Looks Like:** Code calls `/v1/bootstrap` and handles response
**Why Not Verified:** Endpoint returns 401 due to JWT mismatch (B001)
**What Claude B Must Do:** After fixing B001, verify bootstrap returns yacht_id

### U002: User Session Persists Across Tab Switches
**What It Looks Like:** AuthContext has visibility change handler
**Why Not Verified:** Not tested on production site
**What Claude B Must Do:** Login, switch tabs, return, verify still logged in

### U003: Token Auto-Refresh Works
**What It Looks Like:** Code has `refreshSession()` logic
**Why Not Verified:** Not tested with expired token
**What Claude B Must Do:** Wait for token expiry, verify auto-refresh occurs

---

## SEARCH

### U004: Semantic Search Returns Relevant Results
**What It Looks Like:** useCelesteSearch.ts has full search implementation
**Why Not Verified:** Pipeline JWT mismatch blocks all search
**What Claude B Must Do:** After fixing B001, search and verify relevance

### U005: Search Streaming Works
**What It Looks Like:** Code has streaming response handling
**Why Not Verified:** Never tested streaming mode
**What Claude B Must Do:** Search with debug open, verify streaming chunks

### U006: Search Caching Works
**What It Looks Like:** Code has CACHE_TTL and cache logic
**Why Not Verified:** Search doesn't work at all
**What Claude B Must Do:** Search, search again, verify cache hit in console

### U007: Vector/Embedding Search Returns Results
**What It Looks Like:** Code references vector search
**Why Not Verified:** Pipeline broken
**What Claude B Must Do:** Query that requires semantic understanding, verify results

---

## EMAIL

### U008: Email Watcher Syncs New Emails
**What It Looks Like:** email_watchers table shows sync_status="active"
**Why Not Verified:** Did not send test email and verify it appeared
**What Claude B Must Do:** Send email to test account, verify it appears in UI

### U009: MS Graph OAuth Token Is Valid
**What It Looks Like:** api_tokens table has Microsoft credentials
**Why Not Verified:** Did not test token against MS Graph API
**What Claude B Must Do:** Verify `/api/integrations/outlook/status` returns connected

### U010: Email Thread View Works
**What It Looks Like:** EmailThreadView component exists
**Why Not Verified:** Did not view production UI
**What Claude B Must Do:** Click on email thread, verify messages load

### U011: Email Appears in Search Surface (Not Sidebar)
**What It Looks Like:** Search code includes email in results
**Why Not Verified:** Did not view production UI
**What Claude B Must Do:** Search for email keyword, verify results appear inline

---

## DOCUMENTS

### U012: Document Viewer Loads PDFs
**What It Looks Like:** DocumentViewer component with PDF.js
**Why Not Verified:** Did not test on production
**What Claude B Must Do:** Click document in search results, verify PDF renders

### U013: Document Yacht Isolation Works at Runtime
**What It Looks Like:** documentLoader.ts has path validation code
**Why Not Verified:** Only code review, not runtime test
**What Claude B Must Do:** Try to access document from different yacht (should fail)

### U014: Signed URLs Expire Correctly
**What It Looks Like:** Code creates signed URLs with TTL
**Why Not Verified:** Did not test URL expiry
**What Claude B Must Do:** Get signed URL, wait past TTL, verify 403

---

## MICROACTIONS

### U015: ~47 of 67 Microactions Work
**What It Looks Like:** action_registry.py has 67 actions
**Why Not Verified:** Only ~20 verified via test matrix
**What Claude B Must Do:** Test each action individually, document status

### U016: Action Audit Logging Works
**What It Looks Like:** Code has audit_log writes for MUTATE actions
**Why Not Verified:** Did not verify audit table population
**What Claude B Must Do:** Execute mutation, check audit_logs table

### U017: Action Rate Limiting Works
**What It Looks Like:** Code may have rate limiting
**Why Not Verified:** Not tested
**What Claude B Must Do:** Execute action rapidly, verify rate limit applies

### U018: Action Rollback Works
**What It Looks Like:** Some handlers have rollback logic
**Why Not Verified:** Not tested
**What Claude B Must Do:** Trigger failure mid-transaction, verify rollback

---

## HANDOVER

### U019: add_to_handover Works
**What It Looks Like:** Handler registered in dispatcher
**Why Not Verified:** ActionExecutionError reported (B005)
**What Claude B Must Do:** Execute action, verify item created

### U020: Handover Sign-Off Flow Works
**What It Looks Like:** RPCs for sign_handover_incoming/outgoing exist
**Why Not Verified:** Not tested
**What Claude B Must Do:** Complete full handover cycle in UI

### U021: Handover PDF Export Works
**What It Looks Like:** handover_exports table exists
**Why Not Verified:** Not tested
**What Claude B Must Do:** Export handover, verify PDF generated

---

## SITUATIONS

### U022: Situation Detection Engine Works
**What It Looks Like:** situation-engine.ts exists with detection logic
**Why Not Verified:** situation_detections table is empty
**What Claude B Must Do:** Trigger condition that should create detection, verify

### U023: Situation Cards Display
**What It Looks Like:** SituationCard.tsx component exists
**Why Not Verified:** No detections to display
**What Claude B Must Do:** After fixing detection, verify cards render

---

## RLS

### U024: RLS Works for ALL Tables
**What It Looks Like:** Tested ~10 tables
**Why Not Verified:** 100+ tables exist, only tested subset
**What Claude B Must Do:** Test RLS on any table with sensitive data

### U025: RLS Works Under Load
**What It Looks Like:** Policies exist
**Why Not Verified:** Only single requests tested
**What Claude B Must Do:** Concurrent requests don't leak data

---

## UI/UX

### U026: Production Site Renders Without Errors
**What It Looks Like:** Local tests pass
**Why Not Verified:** Did not visit apps.celeste7.ai
**What Claude B Must Do:** Visit site, check console for errors

### U027: Mobile Responsive Design Works
**What It Looks Like:** Code uses responsive patterns
**Why Not Verified:** Not tested on mobile
**What Claude B Must Do:** Test on mobile viewport

### U028: One URL Principle Enforced
**What It Looks Like:** Search-centric architecture
**Why Not Verified:** Did not verify navigation
**What Claude B Must Do:** Navigate app, verify single URL pattern

### U029: "Nothing Found" Transparency
**What It Looks Like:** Code has empty state handling
**Why Not Verified:** Did not test empty searches
**What Claude B Must Do:** Search for nonsense, verify clear "nothing found" message

---

## CI/CD

### U030: CI Workflows Actually Run on Push
**What It Looks Like:** Workflow files exist
**Why Not Verified:** Did not trigger GitHub Actions
**What Claude B Must Do:** Push commit, verify workflows trigger

### U031: E2E Tests Pass on CI
**What It Looks Like:** e2e.yml workflow exists
**Why Not Verified:** Did not see CI run output
**What Claude B Must Do:** Check GitHub Actions history for green runs

### U032: RLS Proof Suite Runs on Migration Changes
**What It Looks Like:** rls-proof.yml exists
**Why Not Verified:** Did not trigger
**What Claude B Must Do:** Modify migration, verify RLS tests run

---

## STORAGE

### U033: File Upload Works
**What It Looks Like:** Storage buckets configured
**Why Not Verified:** Did not test upload
**What Claude B Must Do:** Upload file via UI, verify in bucket

### U034: File Delete Works
**What It Looks Like:** Delete operations in code
**Why Not Verified:** Not tested
**What Claude B Must Do:** Delete file, verify removed from bucket

### U035: MIME Type Restrictions Enforced
**What It Looks Like:** Bucket configs show MIME limits
**Why Not Verified:** Did not test invalid upload
**What Claude B Must Do:** Try uploading .exe to image bucket, verify rejection

---

## SUMMARY

| Category | Unverified Count |
|----------|------------------|
| Auth/Bootstrap | 3 |
| Search | 4 |
| Email | 4 |
| Documents | 3 |
| Microactions | 4 |
| Handover | 3 |
| Situations | 2 |
| RLS | 2 |
| UI/UX | 4 |
| CI/CD | 3 |
| Storage | 3 |
| **Total** | **35** |

**Claude B must verify ALL of these before declaring the system complete.**

