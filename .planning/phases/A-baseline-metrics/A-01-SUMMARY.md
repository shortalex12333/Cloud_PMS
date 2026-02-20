---
phase: A
plan: 01
status: complete
started: 2026-02-19T18:37:00Z
completed: 2026-02-20T02:51:08Z
---

# Summary: A-01 Search Test Harness + Baseline Metrics

## What Was Built

Created test harness and captured baseline search metrics from production.

## Key Files

### Created
- `/test/search_harness.ts` — TypeScript harness (196 lines)
- `/test/types.ts` — Shared types for truth sets and results
- `/test/baseline/metrics.json` — Aggregate metrics
- `/test/baseline/results.jsonl` — Per-query results (2,400 lines)

## Baseline Metrics

| Metric | Value |
|--------|-------|
| Total Queries | 2,400 |
| **Recall@3** | **3.5%** |
| MRR | 0.027 |
| p95 Latency | 19,545ms |

### Per-Entity Breakdown

| Entity Type | Queries | Recall@3 |
|-------------|---------|----------|
| certificate | 60 | 0% |
| document | 240 | 0% |
| fault | 300 | 0% |
| inventory | 300 | 0% |
| parts | 300 | 24% |
| receiving | 300 | 4% |
| shopping_list | 300 | 0% |
| work_order_note | 300 | 0% |
| work_order | 300 | 0% |

## Critical Finding

**Search pipeline is severely broken.** Only 2 of 9 entity types return any relevant results:
- Parts: 24% recall (best performer)
- Receiving: 4% recall
- All others: 0% recall

This confirms the need for deployment + investigation.

## Deviations

- 2,400 queries instead of 2,700 (some truth set items may have fewer than 12 variations)

## Self-Check: PASSED

- [x] Harness loads all 9 truth set JSONL files
- [x] Harness sends each query to production search endpoint
- [x] Harness computes Recall@3 and MRR
- [x] Per-query results show expected vs actual IDs
- [x] Aggregate metrics saved to /test/baseline/metrics.json
- [x] All output files in /test/ directory only
