---
phase: 19
plan: 02
subsystem: nlp-variants
tags: [nlp, intent-classification, testing, truth-set]
dependency-graph:
  requires: [19-01-lens-matrix]
  provides: [intent_truth_set.jsonl, nlp-variant-files]
  affects: [nlp-testing, intent-classifier-evaluation]
tech-stack:
  added: []
  patterns: [jsonl-truth-set, variant-generation, read-mutate-balance]
key-files:
  created:
    - .planning/agents/nlp-variants/work_order_variants.jsonl
    - .planning/agents/nlp-variants/fault_variants.jsonl
    - .planning/agents/nlp-variants/equipment_variants.jsonl
    - .planning/agents/nlp-variants/part_variants.jsonl
    - .planning/agents/nlp-variants/inventory_variants.jsonl
    - .planning/agents/nlp-variants/certificate_variants.jsonl
    - .planning/agents/nlp-variants/handover_variants.jsonl
    - .planning/agents/nlp-variants/hours_of_rest_variants.jsonl
    - .planning/agents/nlp-variants/warranty_variants.jsonl
    - .planning/agents/nlp-variants/shopping_list_variants.jsonl
    - .planning/agents/nlp-variants/email_variants.jsonl
    - .planning/agents/nlp-variants/receiving_variants.jsonl
    - .planning/agents/nlp-variants/intent_truth_set.jsonl
  modified: []
decisions:
  - Generated exactly 100 queries per lens for consistent coverage
  - Maintained approximately 50/50 READ/MUTATE balance per lens
  - Used djb2 hash-ready JSONL format for deterministic testing
  - Included expected_entities for queries with entity references
metrics:
  duration: 842s
  completed_date: 2026-03-02
---

# Phase 19 Plan 02: NLP Variant Generation Summary

Generated 1,200 query variants for intent classification testing using lens_matrix.json as authoritative source.

## Deviations from Plan

None - plan executed exactly as written.

## Tasks Completed

| Task | Description | Commit | Files |
|------|-------------|--------|-------|
| 1 | Read lens_matrix.json and create directory | - | .planning/agents/nlp-variants/ |
| 2 | Generate 100 variants per lens (12 lenses) | ccbcc60a | 12 JSONL files |
| 3 | Aggregate into intent_truth_set.jsonl | ccbcc60a | 1 aggregated file |

## Deliverables

### Variant Files Created (100 queries each)

| Lens | READ | MUTATE | Total |
|------|------|--------|-------|
| work_order | 51 | 49 | 100 |
| fault | 52 | 48 | 100 |
| equipment | 54 | 46 | 100 |
| part | 51 | 49 | 100 |
| inventory | 55 | 45 | 100 |
| certificate | 54 | 46 | 100 |
| handover | 53 | 47 | 100 |
| hours_of_rest | 51 | 49 | 100 |
| warranty | 55 | 45 | 100 |
| shopping_list | 53 | 47 | 100 |
| email | 53 | 47 | 100 |
| receiving | 50 | 50 | 100 |
| **Total** | **632** | **568** | **1,200** |

### Aggregated Truth Set

- **File:** `.planning/agents/nlp-variants/intent_truth_set.jsonl`
- **Lines:** 1,201 (1 metadata header + 1,200 queries)
- **Format:** JSONL with metadata header

### Query Variation Strategies Applied

1. **Synonyms:** show/display/list/find/get/view
2. **Word Order:** "open work orders" vs "work orders that are open"
3. **Formality:** casual ("show me") vs professional ("display all")
4. **Abbreviations:** WO (work order), ME (main engine), DG (diesel generator)
5. **Temporal:** "this week", "overdue", "upcoming", "last month"
6. **Combined filters:** "open high priority work orders on ME1"
7. **Action variants:** create/add/new, update/edit/modify, close/complete/finish

### JSONL Schema

```jsonl
{
  "query": "show open work orders",
  "expected_lens": "work_order",
  "expected_mode": "READ",
  "expected_filters": [{"field": "status", "value": "open"}],
  "expected_action_id": null
}
```

For MUTATE queries with entities:
```jsonl
{
  "query": "create a new fault report for ME1",
  "expected_lens": "fault",
  "expected_mode": "MUTATE",
  "expected_filters": [],
  "expected_action_id": "report_fault",
  "expected_entities": [{"type": "equipment", "value": "ME1"}]
}
```

## Verification

- [x] Exactly 100 queries per lens (12 x 100 = 1,200)
- [x] All action_ids exist in lens_matrix.json
- [x] No duplicate queries (case-insensitive)
- [x] At least 10 unique query patterns per lens
- [x] Aggregated file has 1,201 lines (1 metadata + 1,200 queries)

## Self-Check: PASSED

- FOUND: .planning/agents/nlp-variants/intent_truth_set.jsonl (1,201 lines)
- FOUND: All 12 lens variant files (100 lines each)
- FOUND: Commit ccbcc60a

## Next Steps

Phase 19 Plan 03: Deploy intent classifier agents to evaluate against truth set.
