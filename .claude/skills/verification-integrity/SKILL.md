---
name: verification-integrity
description: >
  Detects false failures and false successes during verification. Triggers when:
  tests fail, tests pass, claiming "it works", seeing 404/401/500 errors,
  interpreting test output, reviewing CI/CD results, or any verification claim.
  Forces agents to verify the verification — is this a REAL failure? Is this
  a REAL success? Prevents premature conclusions from misleading signals.
triggers:
  - test failure
  - test pass
  - 404 error
  - 401 error
  - 500 error
  - "it works"
  - "tests pass"
  - "all green"
  - verification
  - CI/CD
  - curl output
  - assertion
---

# Verification Integrity

## The Core Problem

```
╔═══════════════════════════════════════════════════════════════════════════════╗
║  SURFACE SIGNALS LIE                                                          ║
║                                                                               ║
║  • 404 ≠ "code is broken"     (might be auth, routing, env)                  ║
║  • 200 ≠ "code is correct"    (might return wrong data)                      ║
║  • "PASS" ≠ "verified"        (might be skipped, empty assertion)            ║
║  • "FAIL" ≠ "bug found"       (might be test framework, flaky, timeout)      ║
║                                                                               ║
║  ALWAYS ASK: Is this signal telling me what I think it's telling me?         ║
╚═══════════════════════════════════════════════════════════════════════════════╝
```

## Two Questions Before Every Conclusion

### On Failure

```
FAILURE SIGNAL RECEIVED
         ↓
    ┌────────────────────────────────────┐
    │ Is this a REAL failure?            │
    │                                    │
    │ • Is the test itself correct?      │
    │ • Is the environment correct?      │
    │ • Is auth/setup configured?        │
    │ • Is this a timeout issue?         │
    │ • Is this a flaky test?            │
    │ • Is this testing what I changed?  │
    └────────────────────────────────────┘
         ↓
    YES, real failure → Debug the code
    NO, false failure → Fix the test/env first
```

### On Success

```
SUCCESS SIGNAL RECEIVED
         ↓
    ┌────────────────────────────────────┐
    │ Is this a REAL success?            │
    │                                    │
    │ • Did the test actually run?       │
    │ • Was it skipped?                  │
    │ • Are assertions present?          │
    │ • Is it checking the right thing?  │
    │ • Is the response correct (not just 200)? │
    │ • Did I mock away the actual behavior? │
    └────────────────────────────────────┘
         ↓
    YES, real success → Proceed with confidence
    NO, false success → Write better verification
```

---

## False Failure Patterns

| Pattern | Signal | Reality | Fix |
|---------|--------|---------|-----|
| **Auth Not Configured** | 401 Unauthorized | Code is fine, env missing | Set up auth tokens |
| **Route Not Mounted** | 404 Not Found | Endpoint exists but not exposed | Check router registration |
| **Database Not Seeded** | 404 or empty result | Query is correct, data missing | Seed test data |
| **Wrong Port/URL** | Connection refused | Service running on different port | Check PORT env var |
| **Timeout (Not Slow Code)** | Timeout error | CI runner slow, not code | Increase timeout or use faster runner |
| **Flaky Test** | Intermittent failure | Race condition in TEST, not code | Fix test isolation |
| **Legacy Test Constraint** | Assertion failed | Test expects old behavior | Update test to match new spec |
| **Missing Dependency** | Import error | Code is fine, package not installed | Install dependency |
| **Docker Not Running** | Connection refused | Nothing wrong with code | Start Docker |
| **Previous Test Pollution** | Unexpected state | Test order dependency | Reset state between tests |

**See:** `references/false-failures.md` for detailed patterns and fixes.

---

## False Success Patterns

| Pattern | Signal | Reality | Fix |
|---------|--------|---------|-----|
| **Skipped Test** | "PASS" or no failure | Test didn't run | Remove skip, fix why it was skipped |
| **Empty Assertion** | Test completes | Nothing was verified | Add meaningful assertions |
| **200 OK, Wrong Data** | HTTP 200 | Response body is garbage | Assert on response content |
| **Mocked Everything** | Test passes | Didn't test real behavior | Reduce mocking, add integration test |
| **Caught Exception Silently** | No error thrown | Error was swallowed | Let exceptions propagate |
| **Assert on Length Only** | Array has items | Items might be wrong | Assert on item content |
| **Hardcoded Expected Value** | Values match | Test doesn't reflect reality | Derive expected from source of truth |
| **Test Pollution** | State from previous test | Not testing clean slate | Isolate test state |
| **Wrong Environment** | Passes locally | Will fail in production | Test in production-like env |
| **Snapshot Outdated** | Snapshot matches | Snapshot was wrong to begin with | Review snapshot manually |

**See:** `references/false-successes.md` for detailed patterns and fixes.

---

## HTTP Status Code Reality Check

### 4xx Errors (Client Errors)

| Code | Surface Meaning | Possible False Failure Causes |
|------|-----------------|-------------------------------|
| **400** | Bad Request | Test sending malformed payload, not code issue |
| **401** | Unauthorized | Auth token missing/expired, not code issue |
| **403** | Forbidden | RLS policy correct but user lacks role |
| **404** | Not Found | Route not mounted, not endpoint missing |
| **405** | Method Not Allowed | Wrong HTTP method in test |
| **422** | Unprocessable | Validation working correctly, test payload wrong |

### 5xx Errors (Server Errors)

| Code | Surface Meaning | Possible False Failure Causes |
|------|-----------------|-------------------------------|
| **500** | Internal Error | Could be real bug OR test setup issue |
| **502** | Bad Gateway | Upstream service not running |
| **503** | Service Unavailable | Service starting up, not crashed |
| **504** | Gateway Timeout | Network latency, not code slowness |

### 2xx Success (Verify These!)

| Code | Surface Meaning | Possible False Success Causes |
|------|-----------------|-------------------------------|
| **200** | OK | Response body might be wrong |
| **201** | Created | Resource might be malformed |
| **204** | No Content | Might have deleted wrong thing |

---

## Pre-Verification Checklist

Before running verification, confirm:

```markdown
## Environment Ready
- [ ] Docker/services running?
- [ ] Correct port exposed?
- [ ] Database seeded with test data?
- [ ] Auth tokens configured?
- [ ] Environment variables set?

## Test Quality
- [ ] Test actually runs (not skipped)?
- [ ] Assertions are present and meaningful?
- [ ] Testing what I actually changed?
- [ ] Not over-mocked?

## Failure Analysis
- [ ] If 4xx: Is it auth/route issue or code issue?
- [ ] If 5xx: Is it real bug or setup issue?
- [ ] If timeout: Is code slow or CI slow?
- [ ] If flaky: Is it test isolation or real race condition?

## Success Analysis
- [ ] Response status AND body correct?
- [ ] Test wasn't skipped?
- [ ] Assertions meaningful (not just "length > 0")?
- [ ] Would this catch a regression?
```

**See:** `references/verification-checklist.md` for full checklist.

---

## Decision Tree

```
Test Result Received
         │
         ├── FAILURE
         │      │
         │      ├── Is environment correct? ──NO──→ FIX ENVIRONMENT
         │      │
         │      ├── Is test itself correct? ──NO──→ FIX TEST
         │      │
         │      ├── Is it testing my change? ─NO──→ IGNORE (out of scope)
         │      │
         │      └── All yes? ─────────────────────→ REAL FAILURE: Debug code
         │
         └── SUCCESS
                │
                ├── Did test actually run? ───NO──→ FALSE SUCCESS: Enable test
                │
                ├── Are assertions present? ──NO──→ FALSE SUCCESS: Add assertions
                │
                ├── Is response CONTENT correct? NO→ FALSE SUCCESS: Check body
                │
                ├── Is it testing real behavior? NO→ FALSE SUCCESS: Reduce mocks
                │
                └── All yes? ─────────────────────→ REAL SUCCESS: Proceed
```

---

## Verification Output Template

When reporting verification results, use this format:

```markdown
## Verification: [Test Name]

### Signal Received
- **Status:** [PASS/FAIL]
- **Output:** [Actual output]

### Signal Analysis
- **Is environment correct?** [Yes/No - evidence]
- **Is test correct?** [Yes/No - evidence]
- **Did test actually run?** [Yes/No - evidence]
- **Are assertions meaningful?** [Yes/No - evidence]

### Verdict
- **Real or False?** [REAL FAILURE / FALSE FAILURE / REAL SUCCESS / FALSE SUCCESS]
- **Reasoning:** [Why you believe this]

### Action
- [What to do based on verdict]
```

---

## Common Mistakes This Skill Prevents

| Mistake | What Agent Does | What Agent Should Do |
|---------|-----------------|----------------------|
| "Got 404, code is broken" | Starts debugging code | Check if route is mounted first |
| "Tests pass, ship it" | Claims success | Verify tests actually ran and asserted |
| "CI is red, I broke something" | Panic debugging | Check if it's flaky or env issue |
| "All green!" | Confidence | Verify no skipped tests, meaningful assertions |
| "Timeout, code is slow" | Optimizes code | Check if CI runner is overloaded |

---

## Integration with 4-Mode Methodology

### VERIFICATION MODE Enhanced

```
Standard Verification:
1. Run tests
2. Check output
3. Report pass/fail

Enhanced Verification (with this skill):
1. Run tests
2. Check output
3. ASK: Is this a real signal?
4. If failure: Rule out false failure causes
5. If success: Rule out false success causes
6. Report VERIFIED pass/fail with evidence
```

### Evidence Format

```markdown
## Verification Evidence

### Test: /v1/actions/prepare endpoint

**Command:**
```bash
curl -X POST http://localhost:8000/v1/actions/prepare \
  -H "Content-Type: application/json" \
  -d '{"q": "create work order", "domain": "work_orders"}'
```

**Output:**
```json
{"action_id": "create_work_order", "prefill": {...}}
```

**Signal Analysis:**
- Status: 200 OK ✓
- Response body contains expected fields ✓
- Test was not skipped ✓
- Endpoint was actually hit (not mocked) ✓

**Verdict:** REAL SUCCESS
**Confidence:** HIGH
```

---

## Quick Reference

```
┌─────────────────────────────────────────────────────────────────┐
│  BEFORE CLAIMING FAILURE                                        │
├─────────────────────────────────────────────────────────────────┤
│  □ Is Docker/service running?                                   │
│  □ Is auth configured?                                          │
│  □ Is route mounted?                                            │
│  □ Is test data seeded?                                         │
│  □ Is test itself correct?                                      │
│  □ Is this testing my change (not unrelated)?                   │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  BEFORE CLAIMING SUCCESS                                        │
├─────────────────────────────────────────────────────────────────┤
│  □ Did test actually run (not skipped)?                         │
│  □ Are assertions present?                                      │
│  □ Is response CONTENT correct (not just status)?               │
│  □ Did I test real behavior (not mocked)?                       │
│  □ Would this catch a regression?                               │
└─────────────────────────────────────────────────────────────────┘
```
