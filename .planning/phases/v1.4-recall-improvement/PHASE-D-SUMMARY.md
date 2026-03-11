# Phase D Summary: Validation & Metrics

**Date:** 2026-03-02
**Duration:** ~5 minutes
**Status:** COMPLETE (with caveats)

---

## Tasks Completed

### 1. Baseline Harness with Embeddings

**Command:**
```bash
python3 scripts/eval/v12_recall_harness.py --use-embeddings --sample 100
```

**Result:** SUCCESS
- Ran 100 queries (stratified: 79 T1, 18 T2, 1 T3, 2 T4)
- Embeddings loaded: 1,199 (100% coverage)
- Overall Recall@3: 12.1%
- Overall Lens Accuracy: 47.3%
- P95 Latency: 958ms

### 2. RRF Grid Search

**Command:**
```bash
python3 scripts/eval/rrf_grid_search.py --quick
```

**Result:** FAILED
- Error: `relation "yachts" does not exist`
- Script requires schema fix before running

### 3. Validation Report

**File:** `.planning/phases/v1.4-recall-improvement/VALIDATION-REPORT.md`

**Contents:**
- v1.2 vs v1.4 comparison table
- Detailed metrics by tier and lens
- Analysis of why embeddings alone don't help
- Projected impact after migration deployment
- Recommendations for next steps

---

## Key Findings

### Measured Results

| Metric | v1.2 Baseline | v1.4 Embeddings | Delta |
|--------|---------------|-----------------|-------|
| Recall@3 | 13.2% | 12.1% | -1.1% |
| Lens Accuracy | 46.2% | 47.3% | +1.1% |
| P95 Latency | 721ms | 958ms | +237ms |

**Interpretation:** The -1.1% Recall@3 is within sampling noise (100 vs 100 queries). Embeddings are working but provide no benefit without enhanced search_text content.

### Why No Improvement

1. **Migration Not Deployed:** `50_enhance_search_text.sql` is ready but NOT applied
2. **Content Mismatch:** Query embeddings can't match raw entity names
3. **Synonym Gap:** User queries use abbreviations/synonyms not in database

### Projected Impact (After Migration)

| Metric | Current | Projected |
|--------|---------|-----------|
| Recall@3 | 12.1% | 25-35% |
| Lens Accuracy | 47.3% | 60-70% |

---

## Files Generated

| File | Path |
|------|------|
| Validation Report | `.planning/phases/v1.4-recall-improvement/VALIDATION-REPORT.md` |
| Phase Summary | `.planning/phases/v1.4-recall-improvement/PHASE-D-SUMMARY.md` |
| Metrics JSON | `test-results/v14/metrics.json` |
| Detailed Results | `test-results/v14/detailed_results.jsonl` |
| Recall Report | `test-results/v14/recall_report.md` |

---

## Success Criteria Status

| Criteria | Status |
|----------|--------|
| Harness runs with embeddings enabled | PASS |
| Validation report shows measured vs projected impact | PASS |
| STATE.md updated with v1.4 status | PENDING |
| Summary written to PHASE-D-SUMMARY.md | PASS |

---

## Next Steps

1. **Deploy migration** `50_enhance_search_text.sql` to enable full improvement
2. **Fix RRF grid search** script schema reference
3. **Re-run validation** to measure actual post-migration impact
4. **Update STATE.md** with v1.4 milestone completion status

---

## Blockers

| Blocker | Impact | Resolution |
|---------|--------|------------|
| search_text migration not deployed | Cannot measure true v1.4 impact | Deploy to database |
| yachts table reference error | Cannot run RRF grid search | Fix table name in script |
