---
phase: A-baseline-metrics
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - /test/search_harness.ts
  - /test/types.ts
  - /test/baseline/metrics.json
  - /test/baseline/results.jsonl
autonomous: true
requirements:
  - BASE-01
  - BASE-02
  - BASE-03
  - BASE-04

must_haves:
  truths:
    - "Harness loads all 9 truth set JSONL files from /Volumes/Backup/CELESTE/"
    - "Harness sends each query to production search endpoint"
    - "Harness computes Recall@3 (expected ID in top 3 results)"
    - "Harness computes MRR (reciprocal rank of expected ID)"
    - "Per-query results show expected vs actual IDs"
    - "Aggregate metrics saved to /test/baseline/metrics.json"
  artifacts:
    - path: "/test/search_harness.ts"
      provides: "Test harness script"
      min_lines: 150
    - path: "/test/types.ts"
      provides: "TypeScript types for truth sets and results"
      min_lines: 30
    - path: "/test/baseline/metrics.json"
      provides: "Aggregate metrics (Recall@3, MRR, latency)"
      contains: "recall_at_3"
    - path: "/test/baseline/results.jsonl"
      provides: "Per-query results log"
      min_lines: 100
  key_links:
    - from: "/test/search_harness.ts"
      to: "https://pipeline-core.int.celeste7.ai/webhook/search"
      via: "fetch POST request"
      pattern: "fetch.*webhook/search"
    - from: "/test/search_harness.ts"
      to: "/Volumes/Backup/CELESTE/truthset_*.jsonl"
      via: "fs.readFileSync + JSON.parse"
      pattern: "readFileSync.*truthset"
---

<objective>
Create a test harness that runs all 2,700 truth set queries against the production search endpoint and records baseline metrics.

Purpose: Capture pre-deployment search performance as the baseline for regression detection after code deployment.

Output:
- `/test/search_harness.ts` — Executable TypeScript script
- `/test/types.ts` — Shared types
- `/test/baseline/metrics.json` — Aggregate Recall@3, MRR, p95 latency
- `/test/baseline/results.jsonl` — Per-query results with expected vs actual
</objective>

<execution_context>
@/Users/celeste7/.claude/get-shit-done/workflows/execute-plan.md
@/Users/celeste7/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@apps/web/src/hooks/useCelesteSearch.ts
</context>

<tasks>

<task type="auto">
  <name>Task 1: Create test harness types and core script</name>
  <files>/test/types.ts, /test/search_harness.ts</files>
  <action>
Create `/test/types.ts` with TypeScript interfaces:
- `TruthSetItem`: { title, canonical: { target_id, target_type }, queries: Array<{ query, expected_target_id }> }
- `QueryResult`: { query, expected_id, actual_ids: string[], rank: number | null, latency_ms: number, hit: boolean }
- `EntityMetrics`: { entity_type, total_queries, recall_at_3, mrr, avg_latency_ms }
- `AggregateMetrics`: { timestamp, total_queries, recall_at_3, mrr, p95_latency_ms, by_entity: EntityMetrics[] }

Create `/test/search_harness.ts` that:

1. **Loads truth sets** from `/Volumes/Backup/CELESTE/`:
   - truthset_certificate.jsonl (5 items x 12 queries = 60)
   - truthset_document.jsonl (20 items x 12 queries = 240)
   - truthset_fault.jsonl (25 items x 12 queries = 300)
   - truthset_inventory.jsonl (25 items x 12 queries = 300)
   - truthset_parts.jsonl (25 items x 12 queries = 300)
   - truthset_receiving.jsonl (25 items x 12 queries = 300)
   - truthset_shopping_list.jsonl (25 items x 12 queries = 300)
   - truthset_work_order_note.jsonl (25 items x 12 queries = 300)
   - truthset_work_order.jsonl (25 items x 12 queries = 300)
   Total: 225 items x 12 queries = 2,700 queries

2. **Calls production search endpoint** for each query:
   - URL: `https://pipeline-core.int.celeste7.ai/webhook/search`
   - Method: POST
   - Headers: Content-Type application/json
   - Body: { query, query_type: "free-text", limit: 10, auth: { yacht_id: "85fe1119-b04c-41ac-80f1-829d23322598" } }
   - Use TEST_YACHT_ID from context (Cloud_PMS tenant)
   - Add 100ms delay between requests to avoid rate limiting
   - Record latency for each request

3. **Computes metrics**:
   - Recall@3: proportion of queries where expected_id is in top 3 results
   - MRR (Mean Reciprocal Rank): average of 1/rank for each query (0 if not found)
   - p95 latency: 95th percentile of request latencies

4. **Outputs results**:
   - Console progress: "Query N/2700: [query] -> hit/miss"
   - Per-entity breakdown with recall/MRR for each type

Use Node.js fs module for file I/O. Run with `npx tsx /test/search_harness.ts`.

IMPORTANT: Extract entity_type from file name (e.g., "truthset_certificate.jsonl" -> "certificate").
  </action>
  <verify>
- `ls -la /test/search_harness.ts /test/types.ts` shows both files exist
- `npx tsc --noEmit /test/search_harness.ts /test/types.ts` passes type check
  </verify>
  <done>
- search_harness.ts exists with 150+ lines
- types.ts exists with TruthSetItem, QueryResult, EntityMetrics, AggregateMetrics interfaces
- Script compiles without TypeScript errors
  </done>
</task>

<task type="auto">
  <name>Task 2: Run harness and record baseline metrics</name>
  <files>/test/baseline/metrics.json, /test/baseline/results.jsonl</files>
  <action>
Execute the test harness and save results:

1. **Create baseline directory**:
   ```bash
   mkdir -p /test/baseline
   ```

2. **Run harness**:
   ```bash
   cd /Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS
   npx tsx /test/search_harness.ts
   ```

3. **Verify outputs exist**:
   - `/test/baseline/metrics.json` contains: { timestamp, total_queries, recall_at_3, mrr, p95_latency_ms, by_entity: [...] }
   - `/test/baseline/results.jsonl` contains one JSON object per line with: { query, expected_id, actual_ids, rank, latency_ms, hit, entity_type }

4. **Generate summary report** to console showing:
   - Total queries run
   - Overall Recall@3 percentage
   - Overall MRR
   - p95 latency
   - Per-entity-type breakdown table

The harness should handle API errors gracefully (log and continue, mark as miss).
If the API is unreachable, the harness should exit with clear error message.

IMPORTANT: This task runs the actual test against production. Monitor console output for progress.
  </action>
  <verify>
- `cat /test/baseline/metrics.json | jq .recall_at_3` returns a number
- `wc -l /test/baseline/results.jsonl` shows 2700 lines (one per query)
- `cat /test/baseline/metrics.json | jq .by_entity` shows 9 entity types
  </verify>
  <done>
- metrics.json exists with recall_at_3, mrr, p95_latency_ms, by_entity fields
- results.jsonl has 2700 lines (all queries recorded)
- Console shows per-entity-type metrics breakdown
  </done>
</task>

</tasks>

<verification>
1. `/test/search_harness.ts` exists and passes typecheck
2. `/test/baseline/metrics.json` contains valid JSON with recall_at_3, mrr, p95_latency_ms
3. `/test/baseline/results.jsonl` contains 2700 lines
4. All 9 entity types appear in by_entity breakdown
5. No files created outside `/test/` directory
</verification>

<success_criteria>
- Test harness script exists in `/test/` that loads truth set JSONL files
- Harness calls current production search endpoint with all 2,700 queries
- Baseline metrics (Recall@3, MRR, p95 latency) recorded to `/test/baseline/`
- Per-query results logged with expected IDs vs actual IDs
- Summary report generated showing per-entity-type breakdown
</success_criteria>

<output>
After completion, create `.planning/phases/A-baseline-metrics/A-01-SUMMARY.md`
</output>
