---
phase: E-iterate-on-regressions
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - /test/iteration/analysis.md
autonomous: true
requirements:
  - ITER-01
  - ITER-02
  - ITER-03
  - ITER-04

must_haves:
  truths:
    - "Failed queries identified and categorized"
    - "Root cause analysis for search quality issues"
    - "Analysis documented in /test/iteration/analysis.md"
  artifacts:
    - path: "/test/iteration/analysis.md"
      provides: "Root cause analysis report"
      min_lines: 100
  key_links: []
---

<objective>
Investigate root causes of 96.38% query failure rate and categorize issues.

The search pipeline has 3.62% Recall@3 against truth sets. This phase investigates WHY:
1. Truth set accuracy — are expected IDs actually correct?
2. Search data quality — are searchable fields populated?
3. Search function behavior — what does f1_search_fusion return?
4. Query-data alignment — do queries match indexed content?
</objective>

<tasks>

<task type="auto">
  <name>Task 1: Sample and categorize failures</name>
  <files>/test/iteration/analysis.md</files>
  <action>
Analyze a sample of failed queries to categorize root causes:

1. **Extract failure samples (10 per entity type):**
```bash
mkdir -p test/iteration

# Get sample failures per entity type
for type in certificate document fault inventory parts receiving shopping_list work_order work_order_note; do
  echo "=== $type ===" >> test/iteration/failure_samples.txt
  grep "\"entity_type\":\"$type\"" test/comparison/failures.jsonl | head -10 >> test/iteration/failure_samples.txt
done
```

2. **For each sample, investigate:**
   - What query was sent?
   - What expected_id should have been returned?
   - What actual_ids were returned (top 3)?
   - Does the expected_id exist in search_index?

3. **Categorize failures:**
   - **Category A - Truth Set Error**: Expected ID doesn't exist or truth set query doesn't match actual entity
   - **Category B - Not Indexed**: Expected ID exists but not in search_index
   - **Category C - Poor Ranking**: Expected ID indexed but ranked > 3
   - **Category D - Query Mismatch**: Query text doesn't align with indexed content

4. **Generate /test/iteration/analysis.md:**
   - Summary of failure categories with counts
   - Sample queries from each category
   - Root cause hypothesis for each category
   - Recommended fixes

Example analysis structure:
```markdown
# Search Failure Root Cause Analysis

## Executive Summary
- Category A (Truth Set Error): N%
- Category B (Not Indexed): N%
- Category C (Poor Ranking): N%
- Category D (Query Mismatch): N%

## Category A: Truth Set Errors
[Sample queries where expected ID is wrong]

## Category B: Not Indexed
[Sample queries where entity not in search_index]

## Category C: Poor Ranking
[Sample queries where entity ranked > 3]

## Category D: Query Mismatch
[Sample queries where text doesn't match indexed fields]

## Recommendations
1. ...
2. ...
```
  </action>
  <verify>
- /test/iteration/analysis.md exists with categorized failures
- Each category has sample queries
- Recommendations provided
  </verify>
  <done>
- Failures categorized into A/B/C/D
- Root causes identified
- analysis.md documents findings
  </done>
</task>

<task type="auto">
  <name>Task 2: Query search_index to validate hypotheses</name>
  <files></files>
  <action>
Query the production database to validate root cause hypotheses:

1. **Check if expected IDs exist in search_index:**
```bash
# Take 5 random expected IDs from failures and check if indexed
# This requires database access - use available search endpoint

# Or use the search API to query by exact ID
curl -s -X POST https://pipeline-core.int.celeste7.ai/webhook/search \
  -H "Content-Type: application/json" \
  -d '{"query":"[exact expected_id]","query_type":"free-text","limit":10,"auth":{"yacht_id":"85fe1119-b04c-41ac-80f1-829d23322598"}}' | jq '.results | length'
```

2. **Compare indexed content vs query:**
   - For poor-ranking cases, examine what fields are indexed
   - Check if query terms appear in indexed content

3. **Document findings in analysis.md**

Note: Full database access may not be available. Use search API responses to infer index state.
  </action>
  <verify>
- Hypotheses tested against real data
- Findings documented
  </verify>
  <done>
- Index state validated for sample failures
- Root causes confirmed or refined
  </done>
</task>

<task type="auto">
  <name>Task 3: Generate final recommendations</name>
  <files>/test/iteration/analysis.md</files>
  <action>
Based on analysis, document actionable recommendations:

1. **Prioritized fix list:**
   - Quick wins (config changes, no code)
   - Medium effort (index updates, query tuning)
   - Large effort (architecture changes)

2. **Metrics projection:**
   - If Category X fixed, expected Recall@3 improvement
   - Path to 90% Recall@3 target

3. **v1.2 Scope:**
   - What's achievable in next milestone
   - What requires longer-term work

4. **Final verdict:**
   - Was v1.1 successful? (Deployment yes, metrics target no)
   - What did we learn?
   - Recommended next actions

Update /test/iteration/analysis.md with final sections.
  </action>
  <verify>
- Recommendations prioritized
- v1.2 scope suggested
- Final verdict documented
  </verify>
  <done>
- analysis.md complete with all sections
- Actionable path to 90% Recall@3 identified
  </done>
</task>

</tasks>

<verification>
1. /test/iteration/analysis.md exists with 100+ lines
2. All failure categories documented
3. Root causes identified
4. Recommendations provided
</verification>

<success_criteria>
- Failed queries identified and categorized
- Root cause analysis completed
- Recommendations for achieving 90% Recall@3 documented
- v1.1 milestone verdict delivered
</success_criteria>

<output>
After completion, create `.planning/phases/E-iterate-on-regressions/E-01-SUMMARY.md`
</output>
