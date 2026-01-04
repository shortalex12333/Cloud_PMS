# Routing Bug Fix Status

**Date:** 2025-12-26
**Status:** CODE FIXED - AWAITING DEPLOYMENT

---

## Summary

Two routing bugs were identified and **fixed in local code**:

1. **Polite Prefix Bug** (0/10 tests passed)
   - "please create work order" → NO_LLM (should be RULES_ONLY)
   - **Fixed:** Added POLITE_PREFIX pattern to COMMAND_PATTERNS

2. **Non-Domain Blocking Gaps** (3 queries leaked to NO_LLM)
   - "hello there", "who is the president", "what is the weather" → NO_LLM (should be BLOCKED)
   - **Fixed:** Expanded NON_DOMAIN regex pattern

---

## What Was Done

### Code Changes (Committed & Pushed)

**File:** `api/microaction_service.py`
**Commit:** `61db36e` on `main` branch
**Message:** "fix: Polite prefix and non-domain routing bugs"

**Changes:**
1. Added POLITE_PREFIX pattern (lines 853-861):
   - Matches: "please", "can you", "could you", "hey can you", "I'd like you to", "I need you to", "pls", "need to"

2. Added COMMAND_PATTERNS for RULES_ONLY lane (lines 862-885):
   - `create_work_order`, `open_work_order`, `close_work_order`
   - `log_entry`, `add_note`, `add_to_handover`
   - `schedule_task`, `assign_task`, etc.

3. Expanded NON_DOMAIN pattern (lines 821-830):
   - Added: "hello there", "hi", "hey there", "president", "life", "thx", "ty"
   - Added: "yo", "hiya", "howdy", "greetings"
   - Added: "what's up", "sup", "define"

### Local Verification

```
All 26 NON_DOMAIN pattern tests: PASSED
All 14 POLITE_PREFIX pattern tests: PASSED
```

---

## What Needs to Happen

### 1. Trigger Render Deployment

The code is pushed to `main` but **Render hasn't picked up the deployment**.

**Options:**
- Check Render dashboard for build status
- Manually trigger deploy in Render UI
- Verify auto-deploy is enabled for `main` branch
- Check if there's a build error

### 2. Verify Deployment

After deployment, run verification test:
```bash
python3 /tmp/test_deployment.py
```

Expected results:
- "please create work order..." → RULES_ONLY
- "hello there" → BLOCKED
- "who is the president" → BLOCKED

### 3. Run Comprehensive Tests

After deployment verified, run full test suite:
```bash
python3 /tmp/comprehensive_routing_tests.py
```

This runs:
- 55 polite prefix queries (target: ≥95% RULES_ONLY)
- 55 non-domain queries (target: ≥95% BLOCKED)

### 4. Run 1500-Call Stress Test

After routing fixes verified:
```bash
python3 tests/stress_test_runner.py \
  --base-url https://extract.core.celeste7.ai \
  --jwt "$SUPABASE_SERVICE_KEY" \
  --total-calls 1500 \
  --concurrency 5
```

---

## Files Created

| File | Purpose |
|------|---------|
| `/tmp/test_deployment.py` | Quick 7-query deployment verification |
| `/tmp/comprehensive_routing_tests.py` | 110 queries (55 polite + 55 non-domain) |
| `/tmp/verify_local_patterns.py` | Local pattern testing |
| `/tmp/verify_updated_patterns.py` | Updated pattern testing |

---

## Current Test Status

### Pre-Deployment (OLD CODE on server)

| Test | Expected | Actual | Status |
|------|----------|--------|--------|
| please create work order | RULES_ONLY | NO_LLM | FAIL |
| can you add note | RULES_ONLY | NO_LLM | FAIL |
| hello there | BLOCKED | NO_LLM | FAIL |
| who is the president | BLOCKED | NO_LLM | FAIL |
| what is the weather | BLOCKED | NO_LLM | FAIL |
| CAT 3512 manual | NO_LLM | NO_LLM | PASS |
| main engine overheating | GPT | GPT | PASS |

**Result:** 2/7 passed (28.6%) - OLD CODE STILL RUNNING

### Expected Post-Deployment (NEW CODE)

| Test | Expected | Predicted | Status |
|------|----------|-----------|--------|
| please create work order | RULES_ONLY | RULES_ONLY | PASS |
| can you add note | RULES_ONLY | RULES_ONLY | PASS |
| hello there | BLOCKED | BLOCKED | PASS |
| who is the president | BLOCKED | BLOCKED | PASS |
| what is the weather | BLOCKED | BLOCKED | PASS |
| CAT 3512 manual | NO_LLM | NO_LLM | PASS |
| main engine overheating | GPT | GPT | PASS |

**Expected:** 7/7 passed (100%)

---

## Readiness Criteria

Before declaring "READY":

1. **Polite Prefix Tests:** ≥95% pass rate (55 queries)
2. **Non-Domain Tests:** ≥95% pass rate (55 queries)
3. **Lane Violations:** 0 (NO_LLM/RULES_ONLY must never have embeddings)
4. **Invalid Actions:** 0 (all actions must be in 67-action registry)
5. **Success Rate:** ≥98% on stable infra (excluding HTTP 502s from capacity)
6. **Search Endpoint:** Stress tested (not just /extract)

---

## Next Steps

1. **DEPLOY** the code from main branch to Render
2. **VERIFY** with `/tmp/test_deployment.py`
3. **RUN** `/tmp/comprehensive_routing_tests.py`
4. **RUN** 1500-call stress test
5. **UPDATE** verdict document with final results
