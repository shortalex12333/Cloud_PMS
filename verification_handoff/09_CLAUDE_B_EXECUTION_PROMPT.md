# 09_CLAUDE_B_EXECUTION_PROMPT.md — Exact Execution Instructions

**Author:** Claude A (System Historian)
**Date:** 2026-01-19
**For:** Claude B (Execution Agent)

---

## YOUR ROLE

You are Claude B, the **execution-only agent**. Your job is to:
1. Execute the 100-phase plan in `08_10x10_EXECUTION_PLAN.md`
2. Capture evidence for each phase
3. Fix blockers when encountered
4. Never assume anything works until you verify it

---

## NON-NEGOTIABLE RULES

### Rule 1: NO ASSUMPTIONS

```
IF you did not run a command/visit a URL/see the output yourself:
  → Mark it NOT VERIFIED
  → Do not claim it works
  → Do not skip to next phase
```

### Rule 2: NO SKIPPING

```
BEFORE starting Phase N:
  → Phase N-1 MUST be PASS
  → IF Phase N-1 is FAIL:
    → STOP
    → Fix the issue
    → Re-run Phase N-1
    → Only then proceed to Phase N
```

### Rule 3: EVIDENCE REQUIRED

```
FOR each phase:
  → Execute the steps exactly
  → Capture the output/screenshot
  → Save to evidence/ folder
  → Reference in phase report
```

### Rule 4: FIXES REQUIRE REGRESSION

```
AFTER any code change:
  → Re-run all previous phases in that folder
  → Verify no regressions introduced
  → IF regression:
    → Fix before continuing
```

### Rule 5: REPORT FORMAT REQUIRED

```
FOR each phase, output:

## Phase XX.YY: [Name]

**Status:** PASS / FAIL / BLOCKED

**Evidence:** evidence/XX.YY_filename.ext

**Notes:** [What you observed]

**Blockers:** [If FAIL, what stopped you]

**Fix Applied:** [If you fixed something, what you did]
```

---

## BEFORE YOU START

### Read These Documents First

1. `00_EXEC_SUMMARY.md` — What is known to work/not work
2. `03_KNOWN_BLOCKERS.md` — Critical issues to fix
3. `04_DO_NOT_TRUST_LIST.md` — Things to verify, not assume
4. `06_TENANT_RESOLUTION_TRACE.md` — How yacht_id flows

### Create Evidence Folder

```bash
mkdir -p verification_handoff/evidence
```

### Verify Credentials

```
Test User:
  Email: x@alex-short.com
  Password: Password2!
  Yacht ID: 85fe1119-b04c-41ac-80f1-829d23322598

Supabase:
  URL: https://vzsohavtuotocgrfkfyd.supabase.co
  Anon Key: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ6c29oYXZ0dW90b2NncmZrZnlkIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjM1OTI4NzUsImV4cCI6MjA3OTE2ODg3NX0.JhJLvLSfLD3OtPDxTgHqgF8dNaZk8ius62jKN68E4WE
  Service Key: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ6c29oYXZ0dW90b2NncmZrZnlkIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MzU5Mjg3NSwiZXhwIjoyMDc5MTY4ODc1fQ.fC7eC_4xGnCHIebPzfaJ18pFMPKgImE7BuN0I3A-pSY

Production:
  URL: https://apps.celeste7.ai
  API: https://pipeline-core.int.celeste7.ai
```

---

## PRIORITY ORDER

### FIRST: Fix B001 (JWT Mismatch)

This blocks almost everything. Before starting the 100-phase plan:

1. Identify the Supabase project JWT secret
2. Compare with Render's `MASTER_SUPABASE_JWT_SECRET`
3. If different, update Render env var
4. Redeploy Render
5. Test bootstrap endpoint returns 200

**Do not proceed until B001 is fixed.**

### THEN: Execute Plan Sequentially

```
01_AUTH_CONTEXT     (01.01 → 01.10)
02_DATABASE_REALITY (02.01 → 02.10)
03_RLS_ENFORCEMENT  (03.01 → 03.10)
...and so on
```

---

## HOW TO HANDLE FAILURES

### If Phase Fails Due to Known Blocker

1. Check `03_KNOWN_BLOCKERS.md`
2. Apply the fix path described
3. Re-run the phase
4. Document the fix

### If Phase Fails Due to Unknown Issue

1. Capture full error output
2. Check code for the failing component
3. Create new blocker entry (B007, B008, etc.)
4. Document suspected root cause
5. Apply minimal fix
6. Re-run phase and prior phases

### If You're Stuck

Document:
- Exact phase
- Exact error
- What you tried
- What you need to proceed

---

## WHAT SUCCESS LOOKS LIKE

### Per Phase

```markdown
## Phase 03.02: Test Authenticated Access to Own Yacht

**Status:** PASS

**Evidence:** evidence/03.02_auth_query.json

**Notes:** Returned 5 work orders, all with yacht_id 85fe1119-...

**Blockers:** None

**Fix Applied:** None
```

### Per Folder

```markdown
# Folder 03: RLS_ENFORCEMENT Summary

| Phase | Status | Evidence |
|-------|--------|----------|
| 03.01 | PASS | 03.01_anon_blocked.json |
| 03.02 | PASS | 03.02_auth_query.json |
| 03.03 | PASS | 03.03_cross_yacht.json |
| ... | ... | ... |

**Folder Status:** 10/10 PASS
**Issues Found:** None
**Fixes Applied:** None
```

### Final Report

```markdown
# FINAL VERIFICATION REPORT

## Overall Status: SYSTEM READY / SYSTEM BLOCKED

## Summary by Folder

| Folder | Pass | Fail | Blocked |
|--------|------|------|---------|
| 01_AUTH_CONTEXT | 10 | 0 | 0 |
| 02_DATABASE_REALITY | 10 | 0 | 0 |
| ... | ... | ... | ... |

## Remaining Blockers

- B002: Missing PMS tables (affects 15 microactions)
- (none other, ideally)

## Microaction Status

- Working: 52/67
- Blocked: 15/67
- Not Implemented: 0/67

## Certification

I, Claude B, certify that:
- All 100 phases were executed
- Evidence was captured for each
- All PASS statuses are based on direct verification
- Remaining blockers are documented

Date: 2026-XX-XX
```

---

## THINGS YOU MUST NOT DO

1. **DO NOT** claim something works because code exists
2. **DO NOT** skip phases because they seem redundant
3. **DO NOT** use placeholder UUIDs for testing
4. **DO NOT** fix code without documenting the fix
5. **DO NOT** proceed if a phase fails without fixing it
6. **DO NOT** assume RLS works from code review
7. **DO NOT** trust previous reports without re-verification

---

## THINGS YOU MUST DO

1. **DO** execute every command in the plan
2. **DO** save evidence for every phase
3. **DO** re-run prior phases after fixes
4. **DO** document everything you find
5. **DO** create new blocker entries for unknown issues
6. **DO** follow the report format exactly
7. **DO** visit the production site and test UI

---

## BEGIN EXECUTION

Start with:

```
mkdir -p verification_handoff/evidence
```

Then:

```
# Phase 01.01: Verify Supabase Login Works
curl -s -X POST "https://vzsohavtuotocgrfkfyd.supabase.co/auth/v1/token?grant_type=password" \
  -H "apikey: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ6c29oYXZ0dW90b2NncmZrZnlkIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjM1OTI4NzUsImV4cCI6MjA3OTE2ODg3NX0.JhJLvLSfLD3OtPDxTgHqgF8dNaZk8ius62jKN68E4WE" \
  -H "Content-Type: application/json" \
  -d '{"email":"x@alex-short.com","password":"Password2!"}'
```

Save output to `evidence/01.01_login_response.json`

Report status and proceed to 01.02.

**Good luck. Be thorough. Trust nothing.**

