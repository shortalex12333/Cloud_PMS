# Day 3 Stress Test Report
**Date:** 2026-01-02
**Status:** PASS

---

## Summary

Pattern fixes deployed and verified. All lanes now passing.

**Fixes deployed (commit 2d04508):**
- Added problem words: `not producing`, `slow`, `sluggish`, `stuck`, `jammed`, `grinding`, etc.
- Added command pattern: `mark complete/done/finished` → RULES_ONLY

---

## Test Results

### /extract Lane Routing (100 calls)

| Lane | Accuracy | Status |
|------|----------|--------|
| BLOCKED | 25/25 (100%) | PASS |
| NO_LLM | 25/25 (100%) | PASS |
| RULES_ONLY | 25/25 (100%) | PASS |
| GPT | 24/25 (96%) | PASS |
| **Overall** | **99/100 (99.0%)** | **PASS** |

### /v2/search SQL Path (5 calls)

| Query | Result |
|-------|--------|
| main engine | OK |
| generator maintenance | OK |
| oil filter | OK |
| fault E047 | OK |
| watermaker | OK |

**Status: 5/5 (100%) - PASS**

---

## Latency

| Percentile | Latency (ms) |
|------------|--------------|
| P50 | 2,123 |
| P95 | 6,635 |

---

## Day 3 Verdict: PASS

All acceptance criteria met:
- Lane routing accuracy ≥95%: YES (99%)
- /v2/search success ≥98%: YES (100%)
- No critical HTTP errors: YES (0 errors)

---

*Report generated: 2026-01-02*
*Campaign Day: 3 of 7*
*Calls today: 105*
*Cumulative: ~1,735*
