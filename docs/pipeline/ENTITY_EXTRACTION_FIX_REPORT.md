# Entity Extraction Pipeline Fix Report

**Date:** 2026-02-02
**Author:** Claude (Backend Stack Engineer)
**Status:** TWO FIXES VERIFIED AND TESTED

---

## Summary of Fixes

| Fix | Root Cause | Impact |
|-----|------------|--------|
| **#1** | Conflict detection flags subspan containment as conflict | Test suite: 2 failures → 14 passed |
| **#2** | Missing confidence thresholds for shopping_list_term, approval_status, etc. | Zero entities: 31.1% → 24.4%, Shopping List: 53.8% → 9.4% |

---

## Executive Summary

Fixed a critical bug in `coverage_controller.py` where subspan containment was incorrectly flagged as entity conflicts, causing unnecessary AI invocations even when coverage was 100%.

**Impact:**
- Test suite: 2 failures → 14 passed
- Fast path queries: Now correctly bypass AI when coverage is sufficient

---

## Root Cause Analysis

### Problem
The `_detect_conflicts()` method in `coverage_controller.py:276-281` flagged ALL overlapping entities of different types as conflicts, including cases where one entity fully contains another (subspan containment).

### Evidence
Query: "Main engine high temperature"
```
Entities extracted:
  - symptom: "high temperature" span=(12, 28)
  - WARNING_SEVERITY: "high" span=(12, 16)

Overlap: "high"(12-16) is CONTAINED WITHIN "high temperature"(12-28)
This is normal gazetteer behavior, NOT a conflict.
```

Before fix:
- Coverage: 100%
- has_conflicts: True (WRONG)
- needs_ai: True (WRONG - should use fast path)

After fix:
- Coverage: 100%
- has_conflicts: False (CORRECT)
- needs_ai: False (CORRECT - uses fast path)

---

## Fix Applied

**File:** `apps/api/extraction/coverage_controller.py`
**Lines:** 275-291

### Before:
```python
# Check for overlapping entities of different types
for i, e1 in enumerate(entities):
    for e2 in entities[i+1:]:
        if e1.span and e2.span and e1.type != e2.type:
            # Check for overlap
            if (e1.span[0] < e2.span[1] and e2.span[0] < e1.span[1]):
                return True  # ALWAYS flags overlap as conflict

return False
```

### After:
```python
# Check for overlapping entities of different types
# Only flag PARTIAL overlaps as conflicts, not subspan containment
for i, e1 in enumerate(entities):
    for e2 in entities[i+1:]:
        if e1.span and e2.span and e1.type != e2.type:
            # Check for overlap
            if (e1.span[0] < e2.span[1] and e2.span[0] < e1.span[1]):
                e1_start, e1_end = e1.span
                e2_start, e2_end = e2.span

                # Subspan containment is normal gazetteer behavior, not a conflict
                # e1 fully contains e2
                if e1_start <= e2_start and e1_end >= e2_end:
                    continue
                # e2 fully contains e1
                if e2_start <= e1_start and e2_end >= e1_end:
                    continue

                # Partial overlap IS a conflict
                return True

return False
```

---

## Test Results

### Before Fix
```
tests/test_async_orchestrator.py
FAILED test_fast_path_known_equipment - needs_ai=True (expected False)
FAILED test_fast_path_latency - needs_ai=True (expected False)
12 passed, 2 failed
```

### After Fix
```
tests/test_async_orchestrator.py
14 passed, 1 skipped
```

### Custom Test Suite
| Query | Before | After |
|-------|--------|-------|
| Main engine high temperature | needs_ai=True ❌ | needs_ai=False ✅ |
| Racor fuel filter | needs_ai=True ❌ | needs_ai=False ✅ |
| critically low inventory | needs_ai=True ⚠️ | needs_ai=True ⚠️ |
| pending shopping list items | needs_ai=False ✅ | needs_ai=False ✅ |
| Caterpillar filters | needs_ai=False ✅ | needs_ai=False ✅ |

**Note:** "critically low inventory" still triggers AI due to a REAL partial overlap between `source_type:"low inventory"` and `stock_status:"critically low"`. This is separate issue related to gazetteer redundancy, not conflict detection.

---

## Remaining Issues

### 1. Gazetteer Redundancy
Query "critically low inventory" extracts 4 overlapping entities:
- `stock_status: "critically low inventory"` (0-24) - FULL PHRASE
- `stock_status: "critically low"` (0-14) - PARTIAL
- `source_type: "low inventory"` (11-24) - PARTIAL
- `WARNING_SEVERITY: "low"` (11-14) - SINGLE WORD

The partial phrases overlap but don't contain each other, triggering conflict detection.

**Recommendation:** Review gazetteer term selection - prefer full phrases over partial matches.

### 2. Parts Lens Confidence Values
Brand entities have low base confidence (0.35-0.50):
- `Racor`: 0.40
- `Caterpillar`: 0.50

This is working correctly with current thresholds (0.35), but worth monitoring.

---

## Verification Commands

```bash
# Run orchestrator tests
cd apps/api && pytest tests/test_async_orchestrator.py -v

# Run custom conflict detection test
python3 scratchpad/test_before_after_fix.py

# Debug specific query
python3 scratchpad/trace_extraction.py
```

---

## Files Changed

1. `apps/api/extraction/coverage_controller.py` - Lines 275-291 (conflict detection fix)

---

---

# FIX #2: Missing Confidence Thresholds (Root Cause #2)

## Problem
Entity types `shopping_list_term`, `approval_status`, `stock_status`, etc. were NOT defined in `extraction_config.py` confidence thresholds dictionary. This caused them to fall back to the default threshold of **0.75**.

These entities were being extracted with confidence values (0.60-0.70) that were BELOW the default threshold, causing them to be **silently filtered out** in the entity merger.

## Evidence

```
TRACING: 'shopping list'

1. REGEX EXTRACTION: 1 entity
   - shopping_list_term: 'shopping list' conf=0.70

2. CONFIDENCE THRESHOLD CHECK:
   - shopping_list_term: conf=0.70 threshold=0.75 ❌ FILTERED

3. ENTITY MERGER: 0 entities (FILTERED OUT!)
```

## Fix Applied

**File:** `apps/api/extraction/extraction_config.py`
**Lines:** 68-77

### Added Thresholds:
```python
# Shopping List & Inventory Lens (Root Cause #2 Fix - 2026-02-02)
'shopping_list_term': 0.65,  # Allows 0.70 confidence matches
'approval_status': 0.55,     # Allows 0.60 confidence matches
'stock_status': 0.55,        # Allows 0.60 confidence matches
'source_type': 0.45,         # Low confidence source types

# Crew & Compliance Lens
'REST_COMPLIANCE': 0.55,     # Allows 0.60+ confidence matches
'WARNING_STATUS': 0.55,      # Allows 0.60+ confidence matches
'WARNING_SEVERITY': 0.80,    # Kept high for accuracy

# Time references
'time_ref': 0.70,            # Time-based queries
```

---

## Comprehensive Test Results (598 Queries)

### Overall Improvement

| Metric | BEFORE | AFTER | Change |
|--------|--------|-------|--------|
| Zero entities | 186 (31.1%) | 146 (24.4%) | **-40 queries (-21.5%)** |
| Total extractions | 714 | 811 | **+97 (+13.6%)** |

### Shopping List Lens (Target Fix)

| Metric | BEFORE | AFTER | Change |
|--------|--------|-------|--------|
| Zero entities | **57 (53.8%)** | **10 (9.4%)** | **-47 queries (-82.5%)** |
| shopping_list_term | 16 | 56 | **+40 (+250%)** |
| approval_status | 0 | 55 | **+55 (NEW!)** |

### New Entity Types Now Extracting

| Entity Type | BEFORE | AFTER | Status |
|-------------|--------|-------|--------|
| approval_status | 0 | 68 | **FIXED** ✅ |
| shopping_list_term | 16 | 56 | **+250%** ✅ |
| source_type | 0 | 20 | **FIXED** ✅ |
| stock_status | 35 | 42 | **+20%** ✅ |

---

## Remaining Issues (Not Fixed)

### 1. High AI Trigger Rate (61.2%)
Most queries still trigger AI due to low coverage from:
- Misspellings ("Caterpiller", "Raacor")
- Unknown part numbers ("12345", "ABC-123")
- Natural language queries with uncovered words

**Recommendation:** Implement fuzzy matching for misspellings.

### 2. Receiving Lens Still High AI (76%)
The Receiving lens has the highest AI trigger rate.

**Recommendation:** Add more receiving-specific terms to gazetteer.

---

## Files Changed

1. `apps/api/extraction/coverage_controller.py` - Lines 275-291 (Fix #1: conflict detection)
2. `apps/api/extraction/extraction_config.py` - Lines 68-77 (Fix #2: missing thresholds)

---

---

# FIX #3: Missing Thresholds for `part` and `equipment_type` (2026-02-02)

## Problem

Entity types `part` and `equipment_type` were NOT defined in confidence thresholds.
- Base weight = 2.8 → confidence = 2.8 / 5.0 = 0.56
- Default threshold = 0.75
- 0.56 < 0.75 → **ALWAYS FILTERED**

Common yacht terms like "filter", "pump", "valve", "seal" were being silently discarded.

## Evidence

```
Query: "filter"
1. Extracted: part: 'filter' conf=0.56
2. Threshold check: part not defined → default 0.75
3. Result: 0.56 < 0.75 → FILTERED
4. Final output: {} (empty!)
```

## Fix Applied

**File:** `apps/api/extraction/extraction_config.py`

```python
# Fix #3: Part/Equipment Type thresholds (2026-02-02)
# Base weight=2.8 → conf=0.56, was defaulting to 0.75 and filtering out
# Common terms like "filter", "pump", "valve", "seal" were being discarded
'part': 0.50,                # Allows 0.56 confidence matches
'equipment_type': 0.50,      # Allows 0.56 confidence matches
```

## Results (598-Query Test)

| Metric | Before Fix #3 | After Fix #3 | Change |
|--------|---------------|--------------|--------|
| Zero entities | 146 (24.4%) | 141 (23.6%) | **-5 queries** |
| Total extractions | 811 | 868 | **+57 (+7.0%)** |
| `part` extractions | 0 | 35 | **+35 (NEW!)** |
| `equipment_type` extractions | 0 | 22 | **+22 (NEW!)** |

## Cumulative Impact (All 3 Fixes)

| Metric | Original | After All Fixes | Total Improvement |
|--------|----------|-----------------|-------------------|
| Zero entities | 186 (31.1%) | 141 (23.6%) | **-45 queries (-24.2%)** |
| Total extractions | 714 | 868 | **+154 (+21.6%)** |
| Shopping List zero | 57 (53.8%) | 10 (9.4%) | **-47 queries (-82.5%)** |

---

# FIX #4: Fuzzy Brand Matching for Misspellings (2026-02-02)

## Problem

Brand misspellings like "Caterpiller", "Racoor", "VolcoPenta" produced zero entities
because exact gazetteer matching failed.

## Solution

Added fuzzy matching using `rapidfuzz` library against CORE_BRANDS (1,128 terms):
- Score cutoff: 80% similarity required
- Min token length: 4 chars
- Additional validation for short words (score >= 85 for 4-5 char words)
- Lower confidence (0.39) to reflect fuzzy uncertainty

## Files Changed

1. `apps/api/extraction/regex_extractor.py`:
   - Added `_fuzzy_brand_extract()` method
   - Integrated into extract flow after gazetteer

2. `apps/api/extraction/extraction_config.py`:
   - Added `'fuzzy': 0.92` source multiplier

## Results

| Metric | Before | After | Change |
|--------|--------|-------|--------|
| Zero entities | 141 (23.6%) | 133 (22.2%) | **-8 queries** |
| `brand` extractions | 158 | 173 | **+15 (+9.5%)** |
| Parts lens zeros | 16 (20.0%) | 11 (13.8%) | **-31%** |

### Misspellings Now Fixed

```
Caterpiller  → Caterpillar  ✅
Racoor       → Racor        ✅
Raacor       → Racor        ✅
VolcoPenta   → Volvo Penta  ✅
Katerpillar  → Caterpillar  ✅
```

---

## Files Changed (All Fixes)

1. `apps/api/extraction/coverage_controller.py` - Lines 275-291 (Fix #1: conflict detection)
2. `apps/api/extraction/extraction_config.py` - Lines 67-82, source_multipliers (Fix #2, #3, #4)
3. `apps/api/extraction/regex_extractor.py` - `_fuzzy_brand_extract()` method (Fix #4)

---

## Cumulative Impact (All 4 Fixes)

| Metric | Original | Final | Improvement |
|--------|----------|-------|-------------|
| Zero entities | 186 (31.1%) | 133 (22.2%) | **-28.5%** |
| Total extractions | 714 | 883 | **+23.7%** |
| Shopping List zeros | 57 (53.8%) | 10 (9.4%) | **-82.5%** |
| Test failures | 2 | 0 | **Fixed** |

---

## Deployment Checklist

- [ ] Review all three fixes with team
- [ ] Run full test suite: `pytest -m "not integration"`
- [ ] Run comprehensive extraction test (598 queries)
- [ ] Test with production-like queries
- [ ] Deploy to staging
- [ ] Monitor:
  - AI invocation rate (should decrease)
  - Entity extraction rate (should increase)
  - Zero-entity query rate (should decrease)
- [ ] Deploy to production
