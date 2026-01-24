# Email RAG System - Phase Plan

**Created:** 2026-01-24
**Author:** Claude (Counter-Review Session)
**Status:** DRAFT - Awaiting User Approval
**Methodology:** Verify-Before-Build with Hard Gates

---

## Executive Summary

The email RAG system is ~30% built with significant technical debt. This plan takes a methodical approach: fix foundations first, then build incrementally with verification at every step.

**Current State:**
- OAuth: Working
- Email Sync: 3 test emails only
- RAG Worker: Code exists, NOT deployed
- Search UI: Does NOT exist
- Git/Prod Sync: OUT OF SYNC

**End State:**
- User connects Outlook
- Emails sync continuously
- Embeddings generated automatically
- User searches semantically
- Results link to work orders/equipment

---

## Phase Overview

| Phase | Name | Purpose | Gate Criteria |
|-------|------|---------|---------------|
| 0 | Foundation Audit | Reconcile git ↔ production, fix mismatches | Git reflects reality |
| 1 | Single Email Flow | One email: insert → embed → verify | Manual flow works 10/10 times |
| 2 | Batch Processing | Worker processes queue reliably | 100 emails processed, 0 failures |
| 3 | Continuous Sync | Real emails from Outlook, continuous | 24hr unattended run, no intervention |
| 4 | Search UI | User can search emails | User finds email by meaning |
| 5 | Entity Linking | Emails link to work orders | Auto-links verified correct |
| 6 | Hardening | Edge cases, security, monitoring | Production checklist complete |

---

## Phase 0: Foundation Audit

### Objective
Reconcile all mismatches between git, code, and production database. Establish honest baseline.

### Scope: IN
- [ ] Query live DB schema for `email_*` tables
- [ ] Compare live schema to migration file
- [ ] Identify ALL constraint mismatches
- [ ] Fix migration file to match live DB (or vice versa)
- [ ] Commit migration file to git
- [ ] Document what exists vs what was claimed
- [ ] Verify `ExtractionOrchestrator` actually works
- [ ] Verify all imports in worker.py resolve

### Scope: OUT
- No new features
- No deploying worker
- No UI work

### Deliverables

| File | Content |
|------|---------|
| `PHASE_0_AUDIT_RESULTS.md` | Findings from DB/code comparison |
| `PHASE_0_FIXES.md` | What was fixed and why |
| Migration file committed | `00000000000022_email_rag_infrastructure.sql` in git |

### Test Cases

| ID | Test | Expected | Pass/Fail |
|----|------|----------|-----------|
| P0-T1 | Migration file matches live DB schema | Exact match | |
| P0-T2 | `status` constraint includes 'running' | Constraint allows 'running' | |
| P0-T3 | Worker imports resolve without error | `python -c "from worker import EmailRAGWorker"` succeeds | |
| P0-T4 | Entity extractor imports resolve | `python -c "from email_rag.entity_extractor import extract_email_entities"` succeeds | |
| P0-T5 | ExtractionOrchestrator instantiates | `python -c "from extraction.orchestrator import ExtractionOrchestrator; ExtractionOrchestrator()"` succeeds | |

### Gate Criteria (ALL must pass)

- [ ] Migration file committed to git
- [ ] Migration file matches live DB exactly
- [ ] All Python imports resolve
- [ ] `PHASE_0_AUDIT_RESULTS.md` written with honest findings
- [ ] No uncommitted schema changes

### Rollback Plan
Phase 0 is audit-only. No rollback needed. If fixes are made to live DB, document the SQL used.

---

## Phase 1: Single Email Flow

### Objective
Prove ONE email can flow through the entire pipeline manually. Not automated - just proving the path works.

### Scope: IN
- [ ] Insert one email into `email_messages` manually
- [ ] Verify trigger creates extraction job
- [ ] Run worker ONCE (not continuously)
- [ ] Verify embedding generated (1536 dimensions)
- [ ] Verify entities extracted
- [ ] Verify job marked completed
- [ ] Query `search_email_hybrid()` with the embedding
- [ ] Verify email is returned with score ~1.0

### Scope: OUT
- No continuous worker
- No Render deployment
- No UI
- No real Outlook sync

### Deliverables

| File | Content |
|------|---------|
| `PHASE_1_TEST_LOG.md` | Step-by-step log of manual test |
| `PHASE_1_EVIDENCE.md` | Screenshots/output proving each step |

### Test Cases

| ID | Test | Expected | Pass/Fail |
|----|------|----------|-----------|
| P1-T1 | Insert email with preview_text | Row created in email_messages | |
| P1-T2 | Trigger fires | Row created in email_extraction_jobs with status='pending' | |
| P1-T3 | Worker processes job | Status changes: pending → running → completed | |
| P1-T4 | Embedding generated | email_messages.embedding is 1536-element array | |
| P1-T5 | Entities extracted | email_messages.extracted_entities is populated | |
| P1-T6 | Job completed | email_extraction_jobs.status = 'completed' | |
| P1-T7 | Hybrid search returns email | search_email_hybrid() returns the email with score > 0.99 | |
| P1-T8 | Repeat 10 times | All 10 succeed | |

### Gate Criteria (ALL must pass)

- [ ] 10 consecutive manual runs succeed
- [ ] Each run: trigger → worker → embedding → search works
- [ ] No manual intervention needed during each run
- [ ] All failures documented and fixed

### Rollback Plan
Delete test emails and extraction jobs. Reset to clean state.

---

## Phase 2: Batch Processing

### Objective
Worker processes a queue of emails reliably. Handles errors, retries, edge cases.

### Scope: IN
- [ ] Insert 100 test emails
- [ ] Run worker in batch mode
- [ ] Verify all 100 processed
- [ ] Test error scenarios:
  - Empty preview_text
  - Duplicate emails
  - OpenAI API timeout
  - Supabase connection drop
- [ ] Verify retry logic works (3 attempts)
- [ ] Verify failed jobs marked correctly

### Scope: OUT
- No Render deployment yet (run locally)
- No real Outlook emails
- No UI

### Deliverables

| File | Content |
|------|---------|
| `PHASE_2_BATCH_RESULTS.md` | Stats: processed, succeeded, failed, skipped |
| `PHASE_2_ERROR_HANDLING.md` | How each error case was handled |
| `PHASE_2_EDGE_CASES.md` | Edge cases discovered and fixed |

### Test Cases

| ID | Test | Expected | Pass/Fail |
|----|------|----------|-----------|
| P2-T1 | Process 100 emails | 100 completed | |
| P2-T2 | Email with empty preview_text | Skipped gracefully, not failed | |
| P2-T3 | Duplicate extraction job | Handled via ON CONFLICT | |
| P2-T4 | OpenAI returns error | Retry up to 3 times, then fail | |
| P2-T5 | Worker interrupted mid-batch | Resumes on restart, no duplicates | |
| P2-T6 | 1000 emails in queue | Processes in batches of 10, completes all | |

### Gate Criteria (ALL must pass)

- [ ] 100 emails: 100% success rate
- [ ] Error injection: All scenarios handled gracefully
- [ ] No orphaned jobs (stuck in 'running' forever)
- [ ] Worker logs are clear and useful

### Rollback Plan
Truncate test data. Reset extraction_status on email_messages.

---

## Phase 3: Continuous Sync

### Objective
Real emails from Outlook sync continuously. Worker runs unattended.

### Scope: IN
- [ ] Deploy worker to Render
- [ ] Configure environment variables
- [ ] Trigger real email sync from Outlook
- [ ] Verify emails appear in DB
- [ ] Verify worker picks them up
- [ ] Run unattended for 24 hours
- [ ] Implement token refresh in worker (OAuth tokens expire)

### Scope: OUT
- No UI yet
- No entity linking to work orders

### Deliverables

| File | Content |
|------|---------|
| `PHASE_3_DEPLOYMENT_LOG.md` | Render deployment steps |
| `PHASE_3_24HR_REPORT.md` | Stats from 24hr unattended run |
| `PHASE_3_INCIDENTS.md` | Any issues and how resolved |

### Test Cases

| ID | Test | Expected | Pass/Fail |
|----|------|----------|-----------|
| P3-T1 | Worker starts on Render | Logs show "Worker loop started" | |
| P3-T2 | Real email arrives in Outlook | Synced to DB within 5 minutes | |
| P3-T3 | Embedding generated for real email | embedding column populated | |
| P3-T4 | OAuth token expires | Worker refreshes automatically | |
| P3-T5 | Worker crashes | Render restarts automatically | |
| P3-T6 | 24 hours unattended | No human intervention needed | |

### Gate Criteria (ALL must pass)

- [ ] Worker running on Render
- [ ] Real emails syncing
- [ ] Embeddings generating automatically
- [ ] 24-hour run with zero intervention
- [ ] Token refresh working

### Rollback Plan
Stop Render worker. Revert to manual testing.

---

## Phase 4: Search UI

### Objective
User can search emails semantically from the frontend.

### Scope: IN
- [ ] Create `/app/email/search` page
- [ ] Search input field
- [ ] Call backend to generate query embedding
- [ ] Call `search_email_hybrid()` function
- [ ] Display results with:
  - Subject
  - Preview
  - Sender
  - Date
  - Similarity score
- [ ] Click result to view thread

### Scope: OUT
- No entity linking display yet
- No advanced filters (date range, sender)

### Deliverables

| File | Content |
|------|---------|
| `apps/web/src/app/email/search/page.tsx` | Search page component |
| `apps/web/src/lib/email/searchEmails.ts` | Search API function |
| `PHASE_4_UI_SCREENSHOTS.md` | Screenshots of working UI |

### Test Cases

| ID | Test | Expected | Pass/Fail |
|----|------|----------|-----------|
| P4-T1 | Search "engine maintenance" | Returns relevant emails | |
| P4-T2 | Search "overheating" finds "high temperature" | Semantic match works | |
| P4-T3 | No results | Shows "No emails found" message | |
| P4-T4 | Click result | Opens email thread view | |
| P4-T5 | User without emails | Shows empty state | |

### Gate Criteria (ALL must pass)

- [ ] Search page accessible at /app/email/search
- [ ] Semantic search returns relevant results
- [ ] UI handles loading, error, empty states
- [ ] Real user (you) can search and find emails

### Rollback Plan
Remove route. Feature flag if needed.

---

## Phase 5: Entity Linking

### Objective
Emails automatically link to work orders, equipment, parts.

### Scope: IN
- [ ] Extract work order references (WO-1234, #1234)
- [ ] Match to `pms_work_orders` table
- [ ] Extract equipment mentions
- [ ] Match to `pms_equipment` table
- [ ] Display linked entities on email view
- [ ] Click entity to navigate to it

### Scope: OUT
- No auto-creation of work orders from emails
- No AI-based entity extraction (regex only for now)

### Deliverables

| File | Content |
|------|---------|
| `PHASE_5_LINKING_LOGIC.md` | How entities are extracted and matched |
| `PHASE_5_TEST_CASES.md` | Test emails with known entity references |

### Test Cases

| ID | Test | Expected | Pass/Fail |
|----|------|----------|-----------|
| P5-T1 | Email mentions "WO-1234" | Links to work order 1234 | |
| P5-T2 | Email mentions "main engine" | Links to engine equipment | |
| P5-T3 | Email mentions non-existent WO | No broken link, shows "unmatched" | |
| P5-T4 | Click linked work order | Navigates to work order page | |

### Gate Criteria (ALL must pass)

- [ ] Known references extracted correctly
- [ ] Matches are accurate (no false positives)
- [ ] UI displays links correctly
- [ ] Navigation works

### Rollback Plan
Disable entity display. Keep extraction running in background.

---

## Phase 6: Hardening

### Objective
Production-ready. Handle all edge cases. Security reviewed. Monitored.

### Scope: IN
- [ ] Rate limiting on search API
- [ ] Input validation/sanitization
- [ ] Error monitoring (Sentry or similar)
- [ ] Performance testing (1000 concurrent searches)
- [ ] Security review:
  - RLS policies verified
  - No SQL injection
  - OAuth tokens secure
- [ ] Documentation complete
- [ ] Runbook for operations

### Scope: OUT
- Advanced features (AI summarization, etc.)

### Deliverables

| File | Content |
|------|---------|
| `PHASE_6_SECURITY_REVIEW.md` | Security checklist results |
| `PHASE_6_PERFORMANCE.md` | Load test results |
| `PHASE_6_RUNBOOK.md` | Operations guide |
| `EMAIL_RAG_COMPLETE.md` | Final status document |

### Test Cases

| ID | Test | Expected | Pass/Fail |
|----|------|----------|-----------|
| P6-T1 | 1000 concurrent searches | P95 < 500ms | |
| P6-T2 | SQL injection attempt | Blocked, logged | |
| P6-T3 | User A searches User B's emails | Returns nothing (RLS) | |
| P6-T4 | Worker down for 1 hour | Catches up on restart | |
| P6-T5 | OpenAI outage | Graceful degradation | |

### Gate Criteria (ALL must pass)

- [ ] Security review passed
- [ ] Performance targets met
- [ ] Monitoring in place
- [ ] Runbook complete
- [ ] Product owner sign-off

### Rollback Plan
Feature flag to disable email features entirely.

---

## Cross-Phase Rules

### 1. No Phase Skipping
Must complete Phase N before starting Phase N+1. No exceptions.

### 2. Honest Logging
Every failure recorded. No hiding errors. Log format:
```
[PHASE-X] [TIMESTAMP] [PASS/FAIL] Description
```

### 3. Gate Reviews
At end of each phase:
1. Claude presents evidence
2. User verifies claims
3. User approves gate passage

### 4. Regression Testing
When starting Phase N+1, re-run Phase N gate tests. If any fail, stop and fix.

### 5. Rollback Readiness
Every change must be reversible. Document rollback steps before making changes.

---

## Appendix A: File Structure

```
/EMAIL_RAG_PHASE_PLAN.md          ← This file (master plan)
/PHASE_0_AUDIT_RESULTS.md         ← Phase 0 findings
/PHASE_0_FIXES.md                 ← Phase 0 fixes applied
/PHASE_1_TEST_LOG.md              ← Phase 1 manual test log
/PHASE_1_EVIDENCE.md              ← Phase 1 proof
/PHASE_2_BATCH_RESULTS.md         ← Phase 2 batch stats
/PHASE_2_ERROR_HANDLING.md        ← Phase 2 error scenarios
/PHASE_3_DEPLOYMENT_LOG.md        ← Phase 3 Render deployment
/PHASE_3_24HR_REPORT.md           ← Phase 3 unattended run
/PHASE_4_UI_SCREENSHOTS.md        ← Phase 4 UI evidence
/PHASE_5_LINKING_LOGIC.md         ← Phase 5 entity logic
/PHASE_6_SECURITY_REVIEW.md       ← Phase 6 security
/PHASE_6_RUNBOOK.md               ← Phase 6 operations
/EMAIL_RAG_COMPLETE.md            ← Final sign-off
```

---

## Appendix B: Risk Register

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| OpenAI API costs spiral | High | Medium | Set budget alerts, batch efficiently |
| OAuth tokens expire unnoticed | High | Medium | Implement refresh + monitoring |
| RLS bypass allows data leak | Critical | Low | Explicit RLS tests with real users |
| Worker crashes in loop | Medium | Medium | Exponential backoff, crash monitoring |
| Migration breaks existing data | High | Low | Backup before migration, test on staging |

---

## Appendix C: Success Metrics

| Metric | Target | How Measured |
|--------|--------|--------------|
| Email sync latency | < 5 minutes | Time from Outlook receive to DB row |
| Embedding generation | < 2 seconds per email | Worker logs |
| Search latency | < 500ms P95 | API response times |
| Search relevance | 90% user satisfaction | Manual review of top-5 results |
| Uptime | 99.5% | Render metrics |

---

## Approval

- [ ] **User reviewed and approved this plan**
- [ ] **Phase 0 authorized to begin**

**Date:** _______________
**Approved by:** _______________

---

*End of Phase Plan*
