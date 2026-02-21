---
phase: D-compare-and-report
plan: 01
subsystem: search-validation
tags:
  - regression-testing
  - metrics-analysis
  - acceptance-criteria
dependency_graph:
  requires:
    - A-01 (baseline metrics)
    - C-01 (post-deploy metrics)
  provides:
    - comparison-report
    - regression-analysis
    - iteration-decision
  affects:
    - phase-E-planning
tech_stack:
  added: []
  patterns:
    - statistical-comparison
    - jsonl-processing
    - markdown-reporting
key_files:
  created:
    - /test/compare_results.ts
    - /test/comparison/diff.json
    - /test/comparison/failures.jsonl
    - /test/comparison/report.md
  modified: []
decisions:
  - "Phase E (Iterate) is required - Recall@3 at 3.62% vs 90% target"
  - "Latency improved by 15.14% - no performance regression concern"
  - "Only 3 queries changed status (2 improved, 1 regressed) - minimal volatility"
metrics:
  tasks_completed: 1
  commits: 1
  files_created: 4
  duration_seconds: 149
  completed_at: "2026-02-20T03:49:59Z"
---

# Phase D Plan 01: Compare and Report Summary

**Regression analysis comparing baseline vs post-deploy search metrics - identified 86.38% gap to 90% Recall@3 target requiring Phase E iteration**

---

## Objective Achieved

Generated comprehensive comparison report diffing baseline (pre-deploy) vs post-deploy search validation results to determine acceptance criteria status and inform iteration decisions.

**Key findings:**
- Recall@3: 3.58% → 3.62% (+1.16% improvement)
- MRR: 0.0269 → 0.0274 (+1.91% improvement)
- P95 Latency: 19,545ms → 16,585ms (-15.14% improvement)
- Query status changes: 2 improved, 1 regressed, 85 unchanged hits, 2,312 unchanged misses

---

## Tasks Completed

### Task 1: Create comparison script and generate report

**Files:** /test/compare_results.ts, /test/comparison/{diff.json, failures.jsonl, report.md}

**Implementation:**
1. Created TypeScript comparison script to load and diff both result sets
2. Computed per-query status (improved, regressed, unchanged_hit, unchanged_miss)
3. Aggregated metrics changes (Recall@3, MRR, latency by entity type)
4. Generated three output artifacts:

**Outputs generated:**

**/test/comparison/diff.json** (5KB, machine-readable):
- Summary: 2,400 queries → 2 improved, 1 regressed, 85 unchanged hits, 2,312 unchanged misses
- Metrics diff: Recall@3 +0.0417%, MRR +0.0005, P95 latency -2,960ms
- By-entity breakdown for all 9 entity types

**/test/comparison/failures.jsonl** (513KB, 2,312 failures):
- All queries that failed in both runs or regressed
- Includes query text, expected ID, ranks, entity type, status

**/test/comparison/report.md** (4.5KB, 179 lines):
- Executive summary with percentage breakdown
- Overall metrics comparison table
- Per-entity breakdown (9 entity types)
- Top 10 improved queries (showing both)
- Top 10 regressed queries (showing 1)
- Recommendations section
- **Acceptance criteria evaluation with verdict**

**Notable findings:**
- work_order entity showed 0% → 0.33% Recall@3 improvement (1 query improved)
- parts entity had 1 regression (bearing main onboard query)
- Latency improvements across most entities (receiving -3,105ms, work_order -4,552ms)
- shopping_list and work_order_note showed latency increases

**Verification:**
```bash
$ ls -la /test/comparison/
-rw-r--r-- diff.json      (5,026 bytes)
-rw-r--r-- failures.jsonl (512,979 bytes)
-rw-r--r-- report.md      (4,488 bytes)

$ cat /test/comparison/diff.json | jq .summary
{
  "total_queries": 2400,
  "improved": 2,
  "regressed": 1,
  "unchanged_hit": 85,
  "unchanged_miss": 2312
}
```

**Commit:** e05d0a7b

---

### Task 2: Evaluate acceptance criteria

**Files:** None (evaluation documented in report.md)

**Evaluation performed:**

**Criterion 1: Recall@3 >= 90%**
- Target: 90%
- Actual: 3.62%
- Gap: 86.38% below target
- Status: ✗ NOT MET

**Criterion 2: No latency regression**
- Baseline P95: 19,545ms
- Post-deploy P95: 16,585ms
- Delta: -2,960ms (-15.14%)
- Status: ✓ MET

**Overall Verdict:**
✗ CRITERIA NOT MET - Phase E (Iterate) required

**Rationale:**
While deployment did not introduce performance regression (latency improved significantly), the core search quality issue remains unaddressed. Recall@3 at 3.62% means only 87 of 2,400 queries return the expected result in top 3 - fundamentally broken search experience requiring systematic improvements.

**Next steps identified:**
- Phase E must investigate why 96.33% of queries fail to return expected results
- Focus on entity types with 0% recall (certificate, document, fault, inventory, shopping_list, work_order_note)
- Analyze why parts (24.67% recall) and receiving (4.00% recall) perform relatively better

**Verification:**
```bash
$ grep -A 5 "Acceptance Criteria" /test/comparison/report.md
## Acceptance Criteria Check

### Criterion 1: Recall@3 >= 90%
- **Target:** 90%
- **Actual:** 3.62%
- **Status:** ✗ NOT MET
```

**Done criteria met:** All acceptance criteria evaluated and documented in report with clear verdict and recommendations.

---

## Verification

All plan verification criteria met:

- [x] /test/comparison/report.md exists with meaningful content (179 lines)
- [x] /test/comparison/diff.json has valid structure (includes summary, metrics_diff, by_entity)
- [x] /test/comparison/failures.jsonl contains 2,312 failed queries
- [x] Acceptance criteria evaluated and documented with verdict

---

## Success Criteria

All success criteria achieved:

- [x] Comparison script runs diff between baseline and post-deploy results
- [x] Recall@3 calculated per entity type (all 9 types in diff.json)
- [x] MRR calculated overall and per entity type
- [x] Report identifies improved, regressed, and unchanged queries
- [x] Acceptance criteria (Recall@3 >= 90%, no latency regression) evaluated

---

## Deviations from Plan

None - plan executed exactly as written.

---

## Key Insights

### Statistical Analysis

**Overall movement:** Of 2,400 queries, only 3 (0.125%) changed status between runs - extremely stable baseline indicating consistent search behavior (not random variance).

**Performance vs Quality trade-off:** Deployment achieved 15% latency improvement without sacrificing quality - indicates AbortError fix successfully reduced overhead without changing ranking logic.

**Entity-specific patterns:**
- Parts and receiving are the only entity types with non-zero recall
- Parts dominates hits: 74 of 87 total hits (85%)
- This suggests parts search has different (better) implementation or data characteristics

### Acceptance Criteria Context

**90% Recall@3 target:** Ambitious but appropriate for production search - users expect correct result in top 3 for most queries.

**Current 3.62% reality:** Indicates fundamental search quality issue predating this deployment. The validation harness successfully exposed pre-existing problem rather than regression.

**Phase E scope:** Will require investigation of:
1. Truth set accuracy (are expected IDs actually correct?)
2. Search function implementation (f1_search_fusion ranking logic)
3. Data quality (are searchable fields populated?)
4. Query expansion (do queries need fuzzy matching, synonyms?)

---

## Files Created

| Path | Purpose | Size | Lines |
|------|---------|------|-------|
| /test/compare_results.ts | Comparison script | - | 373 |
| /test/comparison/diff.json | Machine-readable diff | 5KB | - |
| /test/comparison/failures.jsonl | Failed queries log | 513KB | 2,312 |
| /test/comparison/report.md | Human-readable report | 4.5KB | 179 |

---

## Decisions Made

1. **Phase E is required** - Recall@3 gap of 86.38% cannot be ignored, even though deployment was successful
2. **Latency improvement is positive signal** - 15% reduction shows deployment was technically successful
3. **Query stability is confirmed** - Only 3 status changes across 2,400 queries indicates reliable test harness

---

## Next Steps

**Immediate:** Begin Phase E planning to investigate root causes of low Recall@3:
- Validate truth sets (are expected IDs actually correct in database?)
- Audit search function logic (f1_search_fusion ranking algorithm)
- Check data quality (are entity fields populated with searchable content?)
- Review query variations (are test queries representative of user behavior?)

**Long-term:** Consider iterative improvement targets:
- Phase E.1: 10% Recall@3 (achievable quick wins)
- Phase E.2: 30% Recall@3 (systematic improvements)
- Phase E.3: 90% Recall@3 (full acceptance criteria)

---

## Self-Check: PASSED

### Files exist:
```bash
$ [ -f "/Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS/test/compare_results.ts" ] && echo "FOUND: test/compare_results.ts" || echo "MISSING"
FOUND: test/compare_results.ts

$ [ -f "/Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS/test/comparison/diff.json" ] && echo "FOUND: diff.json" || echo "MISSING"
FOUND: diff.json

$ [ -f "/Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS/test/comparison/failures.jsonl" ] && echo "FOUND: failures.jsonl" || echo "MISSING"
FOUND: failures.jsonl

$ [ -f "/Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS/test/comparison/report.md" ] && echo "FOUND: report.md" || echo "MISSING"
FOUND: report.md
```

### Commits exist:
```bash
$ git log --oneline --all | grep -q "e05d0a7b" && echo "FOUND: e05d0a7b" || echo "MISSING"
FOUND: e05d0a7b
```

All files created and committed successfully.
