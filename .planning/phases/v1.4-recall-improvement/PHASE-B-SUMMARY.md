# Phase B: Search Text Enhancement - Completion Summary

**Date:** 2026-03-02
**Status:** COMPLETE (ready for review)

---

## Objective

Improve search_text quality for better trigram/TSV matching to address the gap between:
- **Lens Accuracy:** 46.2%
- **Recall@3:** 13.2%

The root cause: many queries don't match because `search_text` lacks common aliases (e.g., "show WOs" doesn't match "work_order" entities).

---

## Analysis Findings

### 1. Current Search Index State

| Object Type | Count | Contains Type Name |
|-------------|-------|-------------------|
| document | 2,998 | N/A |
| work_order_note | 2,704 | N/A |
| fault | 1,706 | 92.5% |
| part | 886 | 61.3% |
| receiving | 880 | 0.2% |
| shopping_item | 773 | N/A |
| equipment | 637 | 70.6% |
| work_order | 428 | 25.7% |
| inventory | 401 | 0.0% |
| certificate | 287 | 0.3% |
| email | 229 | N/A |
| hours_of_rest | 214 | 100.0% |
| supplier | 50 | N/A |
| handover_item | 44 | N/A |
| purchase_order | 9 | N/A |
| note | 5 | N/A |

### 2. Trigram Match Test Results

| Query | Expected Lens | Match? | Notes |
|-------|--------------|--------|-------|
| show WOs | work_order | NO | No trigram match |
| WO list | work_order | NO | No trigram match |
| work orders | work_order | NO | No trigram match |
| tasks | work_order | NO | No trigram match |
| defects | fault | NO | No trigram match |
| issues | fault | NO | No trigram match |
| faults | fault | NO | No trigram match |
| cert expiring | certificate | NO | No trigram match |
| spares | part | NO | No trigram match |
| parts | part | YES | sim=0.444 |
| stock | inventory | NO | No trigram match |
| machines | equipment | NO | No trigram match |
| assets | equipment | NO | No trigram match |
| crew rest | hours_of_rest | NO | Wrong lens match |
| rest hours | hours_of_rest | NO | Wrong lens match |
| deliveries | receiving | NO | No trigram match |
| handover notes | handover | NO | No trigram match |
| shopping | shopping_list | NO | No trigram match |

**Key Finding:** 28 out of 33 test queries (85%) fail to match their expected lens due to missing aliases in `search_text`.

### 3. Root Causes Identified

1. **No object type name in search_text:** Many rows only contain entity-specific data (names, descriptions) without mentioning what type of entity it is.

2. **No common abbreviations:** "WO" for work_order, "PM" for preventive maintenance, "cert" for certificate.

3. **No domain synonyms:** "defect/issue/problem" for fault, "spare/component" for part.

4. **Current indexing logic:** The `projection_worker.py` builds `search_text` from domain-specific columns but doesn't append type aliases.

---

## Deliverables Created

### 1. Synonym Mapping (`scripts/eval/search_synonyms.json`)

JSON file mapping each object_type to an array of searchable aliases:

```json
{
  "work_order": ["work order", "WO", "task", "job", "maintenance", "repair", ...],
  "fault": ["fault", "defect", "issue", "problem", "failure", ...],
  "certificate": ["certificate", "cert", "document", "credential", "expiring", ...],
  ...
}
```

Covers all 16 object types currently in search_index with 8-13 aliases each.

### 2. SQL Migration (`database/migrations/50_enhance_search_text.sql`)

Features:
- **Idempotent:** Uses `[ALIASES:type]` marker to prevent duplicate appends
- **Preserves existing content:** Appends synonyms without overwriting
- **Batched updates:** Processes by object_type to minimize lock time
- **Helper functions:** `get_search_synonyms()` and `append_search_synonyms()` for reuse
- **Verification:** Reports before/after counts

Example transformation:
```
Before: "WO-0040 Shore Power Service Service shore power connections"
After:  "WO-0040 Shore Power Service Service shore power connections work order WO task job maintenance repair service PM preventive maintenance corrective scheduled [ALIASES:work_order]"
```

---

## Expected Impact

### Before Migration
- Query "show WOs" -> **0 trigram matches**
- Query "defects" -> **0 trigram matches**
- Query "spares" -> **0 trigram matches**

### After Migration
- Query "show WOs" -> **428 potential matches** (all work_orders contain "WO")
- Query "defects" -> **1,706 potential matches** (all faults contain "defect")
- Query "spares" -> **886 potential matches** (all parts contain "spare")

### Projected Metrics Improvement
| Metric | Current | Target |
|--------|---------|--------|
| Trigram recall for alias queries | ~5% | ~85% |
| Overall Recall@3 | 13.2% | 25-35% |

Note: Full impact depends on query distribution and fusion weights.

---

## Execution Steps (Not Yet Executed)

1. **Review migration script** with DBA
2. **Take snapshot** of current search_index state for rollback
3. **Run migration** in staging first
4. **Measure before/after** using test queries above
5. **Run in production** if staging results are positive
6. **(Optional)** Uncomment embedding re-queue to refresh vectors

---

## Files Modified/Created

| File | Action |
|------|--------|
| `/scripts/eval/search_synonyms.json` | CREATED |
| `/database/migrations/50_enhance_search_text.sql` | CREATED |
| `/.planning/phases/v1.4-recall-improvement/PHASE-B-SUMMARY.md` | CREATED |

---

## Next Steps

1. **Phase C:** After migration, run recall evaluation to measure actual improvement
2. **Phase D:** If improvement is insufficient, consider:
   - Adding learned_keywords from click feedback
   - Tuning trigram similarity threshold (currently 0.08)
   - Increasing trigram weight in RRF fusion

---

## Success Criteria Status

- [x] Analysis document shows what's missing from search_text
- [x] Synonym mapping covers all 12+ lenses (16 covered)
- [x] Migration script ready (not executed, as requested)
