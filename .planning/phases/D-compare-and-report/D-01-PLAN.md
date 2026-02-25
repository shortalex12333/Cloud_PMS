---
phase: D-compare-and-report
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - /test/comparison/report.md
  - /test/comparison/diff.json
  - /test/comparison/failures.jsonl
autonomous: true
requirements:
  - VAL-03
  - VAL-04
  - VAL-05

must_haves:
  truths:
    - "Comparison script runs diff between baseline and post-deploy results"
    - "Recall@3 calculated per entity type"
    - "MRR calculated overall and per entity type"
    - "Report identifies improved, regressed, and unchanged queries"
  artifacts:
    - path: "/test/comparison/report.md"
      provides: "Human-readable comparison report"
      min_lines: 50
    - path: "/test/comparison/diff.json"
      provides: "Machine-readable diff"
      contains: "improved"
    - path: "/test/comparison/failures.jsonl"
      provides: "Failed queries for investigation"
  key_links: []
---

<objective>
Generate comprehensive regression report comparing baseline vs post-deploy search metrics.

Purpose: Identify what improved, what regressed, and what remained unchanged to inform iteration decisions.

Input:
- /test/baseline/metrics.json + results.jsonl
- /test/post-deploy/metrics.json + results.jsonl

Output:
- /test/comparison/report.md — Human-readable summary
- /test/comparison/diff.json — Machine-readable diff
- /test/comparison/failures.jsonl — Queries that failed in both or regressed
</objective>

<tasks>

<task type="auto">
  <name>Task 1: Create comparison script and generate report</name>
  <files>/test/compare_results.ts, /test/comparison/report.md, /test/comparison/diff.json, /test/comparison/failures.jsonl</files>
  <action>
Create `/test/compare_results.ts` that:

1. **Loads both result sets:**
   - Reads /test/baseline/results.jsonl
   - Reads /test/post-deploy/results.jsonl
   - Indexes by query string for comparison

2. **Computes per-query diff:**
   - For each query, compare baseline vs post-deploy:
     - `improved`: was miss, now hit (or rank improved)
     - `regressed`: was hit, now miss (or rank worsened)
     - `unchanged_hit`: was hit, still hit
     - `unchanged_miss`: was miss, still miss

3. **Computes aggregate metrics diff:**
   - Overall Recall@3 change
   - Per-entity Recall@3 change
   - MRR change
   - Latency change (p95)

4. **Generates outputs:**

   **/test/comparison/diff.json:**
   ```json
   {
     "timestamp": "...",
     "summary": {
       "total_queries": 2400,
       "improved": N,
       "regressed": N,
       "unchanged_hit": N,
       "unchanged_miss": N
     },
     "metrics_diff": {
       "recall_at_3": { "baseline": 0.035, "post_deploy": 0.036, "delta": +0.001 },
       "mrr": { ... },
       "p95_latency_ms": { ... }
     },
     "by_entity": [ ... ]
   }
   ```

   **/test/comparison/failures.jsonl:**
   One line per query that:
   - Failed in both baseline and post-deploy (unchanged_miss)
   - Regressed (was hit, now miss)
   Include: query, expected_id, baseline_rank, postdeploy_rank, entity_type

   **/test/comparison/report.md:**
   Human-readable markdown with:
   - Executive summary
   - Metrics comparison table
   - Per-entity breakdown
   - Top 10 improved queries
   - Top 10 regressed queries
   - Recommendations

Run: `npx tsx /test/compare_results.ts`
  </action>
  <verify>
- `ls -la /test/comparison/` shows all 3 files
- `cat /test/comparison/diff.json | jq .summary` shows counts
- `head -20 /test/comparison/report.md` shows markdown content
  </verify>
  <done>
- compare_results.ts exists
- diff.json has summary with improved/regressed counts
- report.md has human-readable comparison
- failures.jsonl has failed queries
  </done>
</task>

<task type="auto">
  <name>Task 2: Evaluate acceptance criteria</name>
  <files></files>
  <action>
Check if acceptance criteria are met:

1. **Recall@3 >= 90%?**
   - Read post-deploy recall from metrics
   - If < 90%, note as NOT MET

2. **No latency regression?**
   - Compare p95 latency baseline vs post-deploy
   - If post-deploy is slower, note as NOT MET

3. **Generate final verdict:**
   ```bash
   echo "=== ACCEPTANCE CRITERIA CHECK ==="
   echo "Recall@3 target: 90%"
   echo "Post-deploy Recall@3: $(cat /test/post-deploy/metrics.json | jq .recall_at_3)"
   echo ""
   echo "Latency check:"
   echo "Baseline p95: $(cat /test/baseline/metrics.json | jq .p95_latency_ms)"
   echo "Post-deploy p95: $(cat /test/post-deploy/metrics.json | jq .p95_latency_ms)"
   ```

Based on results:
- If criteria met: Phase E can be skipped
- If criteria NOT met: Phase E must iterate
  </action>
  <verify>
- Acceptance criteria clearly evaluated
- Next steps identified
  </verify>
  <done>
- Verdict on Recall@3 >= 90% documented
- Verdict on latency regression documented
- Phase E necessity determined
  </done>
</task>

</tasks>

<verification>
1. /test/comparison/report.md exists with meaningful content
2. /test/comparison/diff.json has valid structure
3. /test/comparison/failures.jsonl contains failed queries
4. Acceptance criteria evaluated and documented
</verification>

<success_criteria>
- Comparison script runs diff between baseline and post-deploy results
- Recall@3 calculated per entity type
- MRR calculated overall and per entity type
- Report identifies improved, regressed, and unchanged queries
- Acceptance criteria (Recall@3 >= 90%, no latency regression) evaluated
</success_criteria>

<output>
After completion, create `.planning/phases/D-compare-and-report/D-01-SUMMARY.md`
</output>
