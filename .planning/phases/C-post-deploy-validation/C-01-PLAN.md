---
phase: C-post-deploy-validation
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - /test/post-deploy/metrics.json
  - /test/post-deploy/results.jsonl
autonomous: true
requirements:
  - VAL-01
  - VAL-02

must_haves:
  truths:
    - "Same test harness used (no changes from baseline)"
    - "All queries executed against production search endpoint"
    - "Post-deploy metrics recorded to /test/post-deploy/"
    - "Per-query results logged for comparison"
  artifacts:
    - path: "/test/post-deploy/metrics.json"
      provides: "Aggregate post-deploy metrics"
      contains: "recall_at_3"
    - path: "/test/post-deploy/results.jsonl"
      provides: "Per-query results log"
      min_lines: 100
  key_links: []
---

<objective>
Run the same truth set queries against the newly deployed production to capture post-deploy metrics.

Purpose: Measure search performance after deployment to detect improvements or regressions.

Uses the same harness from Phase A with output directed to /test/post-deploy/ instead of /test/baseline/.
</objective>

<tasks>

<task type="auto">
  <name>Task 1: Run harness against post-deploy production</name>
  <files>/test/post-deploy/metrics.json, /test/post-deploy/results.jsonl</files>
  <action>
Create post-deploy output directory and run the same harness:

```bash
mkdir -p test/post-deploy
```

Modify the harness temporarily to output to post-deploy directory, or create a simple wrapper:

```bash
cd /Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS

# Update harness to use post-deploy output dir
sed 's|baseline|post-deploy|g' test/search_harness.ts > test/search_harness_postdeploy.ts

# Run the modified harness
npx tsx test/search_harness_postdeploy.ts
```

Or if the harness accepts an output directory argument, use that.

Wait for all 2,400 queries to complete (with 100ms delays = ~4 minutes minimum).
  </action>
  <verify>
- `ls -la test/post-deploy/` shows metrics.json and results.jsonl
- `cat test/post-deploy/metrics.json | jq .recall_at_3` returns a number
- `wc -l test/post-deploy/results.jsonl` shows similar count to baseline
  </verify>
  <done>
- Post-deploy metrics captured in /test/post-deploy/
- metrics.json has recall_at_3, mrr, p95_latency_ms
- results.jsonl has per-query results
  </done>
</task>

<task type="auto">
  <name>Task 2: Generate quick comparison</name>
  <files></files>
  <action>
Compare baseline vs post-deploy metrics:

```bash
echo "=== BASELINE ==="
cat test/baseline/metrics.json | jq '{recall_at_3, mrr, p95_latency_ms}'

echo "=== POST-DEPLOY ==="
cat test/post-deploy/metrics.json | jq '{recall_at_3, mrr, p95_latency_ms}'
```

Output the comparison to console for immediate visibility.
  </action>
  <verify>
- Both baseline and post-deploy metrics displayed
- Comparison shows whether recall improved or regressed
  </verify>
  <done>
- Quick comparison output shown
- Direction of change identified (improved/regressed/unchanged)
  </done>
</task>

</tasks>

<verification>
1. /test/post-deploy/metrics.json exists with valid metrics
2. /test/post-deploy/results.jsonl has per-query data
3. Quick comparison shows baseline vs post-deploy
</verification>

<success_criteria>
- Same test harness used (no changes between baseline and post-deploy)
- All queries executed against production search endpoint
- Post-deploy metrics recorded to /test/post-deploy/
- Per-query results logged for comparison
</success_criteria>

<output>
After completion, create `.planning/phases/C-post-deploy-validation/C-01-SUMMARY.md`
</output>
