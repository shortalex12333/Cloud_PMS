# P6 E2E Test Report

**Generated:** 2026-01-13T01:26:44.621411+00:00
**Total Scenarios:** 220

## Summary

| Metric | Value |
|--------|-------|
| Total | 220 |
| Passed | 121 |
| Failed | 99 |
| **Pass Rate** | **55.0%** |

## Results by Category

| Category | Total | Passed | Failed | Rate |
|----------|-------|--------|--------|------|
| abuse | 40 | 33 | 7 | 82.5% |
| edge | 60 | 44 | 16 | 73.3% |
| normal | 60 | 39 | 21 | 65.0% |
| regression | 30 | 0 | 30 | 0.0% |
| security | 30 | 5 | 25 | 16.7% |

## Failures

| ID | Category | Expected | Actual | Error |
|----|----------|----------|--------|-------|
| N005 | normal | gated | no_match | No handler mapped for action:  |
| N021 | normal | success | no_match | No handler mapped for action:  |
| N022 | normal | success | no_match | No handler mapped for action:  |
| N023 | normal | success | no_match | No handler mapped for action:  |
| N024 | normal | success | no_match | No handler mapped for action:  |
| N026 | normal | success | no_match | No handler mapped for action:  |
| N027 | normal | success | no_match | No handler mapped for action:  |
| N028 | normal | success | no_match | No handler mapped for action:  |
| N029 | normal | success | no_match | No handler mapped for action:  |
| N033 | normal | success | no_match | No handler mapped for action:  |
| N036 | normal | success | no_match | No handler mapped for action:  |
| N038 | normal | success | no_match | No handler mapped for action:  |
| N039 | normal | success | no_match | No handler mapped for action:  |
| N043 | normal | gated | no_match | No handler mapped for action:  |
| N046 | normal | gated | no_match | No handler mapped for action:  |
| N049 | normal | gated | no_match | No handler mapped for action:  |
| N054 | normal | gated | no_match | No handler mapped for action:  |
| N055 | normal | gated | no_match | No handler mapped for action:  |
| N056 | normal | gated | no_match | No handler mapped for action:  |
| N058 | normal | gated | no_match | No handler mapped for action:  |
| N060 | normal | success | no_match | No handler mapped for action:  |
| E007 | edge | error | skipped | No query provided |
| E011 | edge | success | no_match | No handler mapped for action:  |
| E021 | edge | success | no_match | No handler mapped for action:  |
| E026 | edge | acknowledgment | no_match | No handler mapped for action:  |
| E027 | edge | confirmation_context_required | no_match | No handler mapped for action:  |
| E028 | edge | rejection_context_required | no_match | No handler mapped for action:  |
| E029 | edge | cancel_context_required | no_match | No handler mapped for action:  |
| E033 | edge | success | no_match | No handler mapped for action:  |
| E035 | edge | success | no_match | No handler mapped for action:  |
| ... | ... | ... | ... | (69 more) |

## Latency Distribution

- Average: 53ms
- Min: 0ms
- Max: 536ms

## Acceptance Criteria

- [FAIL] NORMAL+EDGE pass rate >= 95%: 69.2%
- [PASS] Silent failures = 0: 0
- [PASS] Unsafe mutations = 0: 0

## Verdict: **FAIL**