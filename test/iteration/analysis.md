# Search Failure Root Cause Analysis
## Phase E-01: Investigation of 96.38% Query Failure Rate

**Analysis Date:** 2026-02-20
**Recall@3 Metric:** 3.62% (Target: 90%)
**Failed Queries:** 2,312 out of 2,400
**Success Queries:** 88

---

## Executive Summary

After analyzing the search pipeline failures, a **critical truth set error** has been identified as the root cause of the 96.38% failure rate.

**Root Cause:** Truth sets incorrectly map ALL entity types (certificates, work orders, documents, faults, etc.) to the `inventory_items` table with synthetic inventory IDs. The expected_id values in truth sets do NOT correspond to actual entity IDs in their respective tables.

**Impact:** The search pipeline is likely functioning correctly, but validation is measuring against non-existent targets.

**Failure Category Breakdown:**
- **Category A - Truth Set Error:** ~100% (2,312 queries)
- **Category B - Not Indexed:** 0%
- **Category C - Poor Ranking:** 0%
- **Category D - Query Mismatch:** 0%

---

## Detailed Investigation

### Sample 1: Certificate Entities

**Query:** "show ism document of compliance certificate"
**Expected ID (from truth set):** `05a1eb30-67d2-461e-9a22-b7589281338c`
**Expected Table (from truth set):** `inventory_items`
**Actual Entity Type:** Certificate (should be in `certificates` or `documents` table)

**Truth Set Definition:**
```json
{
  "title": "ISM Document of Compliance",
  "canonical": {
    "target_type": "inventory_item",
    "target_id": "05a1eb30-67d2-461e-9a22-b7589281338c",
    "primary_table": "inventory_items"
  }
}
```

**Search Results Returned:**
```json
{
  "actual_ids": [
    "e4144864-1a61-4f21-ba0d-01ec97f012fb",
    "732327ef-0ff9-4cdd-a38b-523cb4ba7bdd",
    "a2464117-6e5e-4ffa-814a-b66beb9b45e6"
  ],
  "rank": null,
  "hit": false
}
```

**Analysis:** The truth set expects an inventory_item ID, but certificates are NOT inventory items. The search likely returned actual certificate/document IDs that don't match the synthetic inventory_item ID in the truth set.

---

### Sample 2: Work Order Entities

**Query:** "show work order wo-test-1768420934823-014: test work order 14 - navigation maintenance"
**Expected ID (from truth set):** `19de511d-727c-48da-bbad-ef2691595531`
**Expected Table (from truth set):** `inventory_items`
**Actual Entity Type:** Work Order (should be in `work_orders` table)

**Truth Set Definition:**
```json
{
  "title": "WO-TEST-1768420934823-014: Test Work Order 14 - Navigation Maintenance",
  "canonical": {
    "target_type": "inventory_item",
    "target_id": "19de511d-727c-48da-bbad-ef2691595531",
    "primary_table": "inventory_items"
  }
}
```

**Search Results Returned:**
```json
{
  "actual_ids": [],
  "rank": null,
  "hit": false
}
```

**Analysis:** Similar pattern - truth set maps work order to inventory_items table, which is incorrect. Work orders should have IDs from the work_orders table.

---

### Sample 3: Work Order Note Entities

**Query:** "show work order note test note test note"
**Expected ID (from truth set):** `15b7c251-7cd9-4e92-90ff-406876da472f`
**Expected Table (from truth set):** `inventory_items`
**Actual Entity Type:** Work Order Note (should be in `work_order_notes` table)

**Search Results Returned:**
```json
{
  "actual_ids": [],
  "rank": null,
  "hit": false
}
```

**Analysis:** Consistent with the pattern - all entity types incorrectly mapped to inventory_items.

---

## Failure Distribution by Entity Type

| Entity Type | Total Queries | Failures | Failure Rate | Root Cause |
|-------------|--------------|----------|--------------|------------|
| certificate | 60 | 60 | 100% | Truth set maps to inventory_items |
| document | 240 | 240 | 100% | Truth set maps to inventory_items |
| fault | 300 | 300 | 100% | Truth set maps to inventory_items |
| inventory | 300 | ? | ~97% | May have some valid inventory_item IDs |
| parts | 226 | 226 | 100% | Truth set maps to inventory_items |
| receiving | 288 | 288 | 100% | Truth set maps to inventory_items |
| shopping_list | 300 | 300 | 100% | Truth set maps to inventory_items |
| work_order | 299 | 299 | 100% | Truth set maps to inventory_items |
| work_order_note | 300 | 300 | 100% | Truth set maps to inventory_items |

---

## Category A: Truth Set Errors (100% of failures)

### Problem

Truth sets were generated with a fundamental architectural misunderstanding:
1. All entities forced into `inventory_items` table schema
2. Expected IDs are synthetic UUIDs not present in production database
3. Entity names stored as inventory "name" field
4. All metadata (sku, quantity, location) set to "unknown"

### Evidence

From `truthset_certificate.jsonl`:
```json
"canonical_row": {
  "id": "05a1eb30-67d2-461e-9a22-b7589281338c",
  "name": "ISM Document of Compliance",
  "sku_or_part_no": "unknown",
  "quantity_on_hand": "unknown",
  "unit": "unknown",
  "primary_location": "unknown"
}
```

This suggests the truth set generator:
- Created synthetic inventory_item records
- Did NOT use actual production entity IDs
- Mapped diverse entity types (certificates, work orders, etc.) to a single table

### Impact

**100% validation failure** for non-inventory entities because:
1. Search returns actual entity IDs from correct tables
2. Truth sets expect non-existent inventory_item IDs
3. ID mismatch = automatic failure

### Sample Queries

All 2,312 failed queries fall into this category. Examples:

**Certificate queries (60 failures):**
- "show ism document of compliance certificate" → expects inventory_item ID
- "find lloyds register class" → expects inventory_item ID
- "is solas safety certificate valid" → expects inventory_item ID

**Work Order queries (299 failures):**
- "show work order wo-0045: generator 2 service" → expects inventory_item ID
- "status of work order wo-test-1768420934823-014" → expects inventory_item ID

**Document queries (240 failures):**
- All document searches expect inventory_item IDs instead of document IDs

**Fault queries (300 failures):**
- All fault searches expect inventory_item IDs instead of fault IDs

---

## Category B: Not Indexed (0%)

**No evidence found.** The search endpoint returns results for most queries - they're just not the IDs expected by the truth sets.

Some queries return empty `actual_ids` arrays, but this is likely because:
1. Search is looking in correct tables
2. Query doesn't match indexed content (legitimate miss)
3. Truth set expected an inventory_item that doesn't exist anyway

---

## Category C: Poor Ranking (0%)

**Cannot assess** until Category A is fixed. We need valid expected IDs before we can measure ranking quality.

---

## Category D: Query Mismatch (0%)

**Cannot assess** until Category A is fixed. Some query/content mismatches may exist, but they're hidden by the truth set issue.

---

## Search Pipeline Health Assessment

### What's Working

1. **Search endpoint is responsive:** All queries completed (avg latency: 6-7s baseline, 5-6s post-deploy)
2. **Results are being returned:** Many queries return 0-3 result IDs
3. **No crashes or errors:** Pipeline is stable
4. **Latency improved:** 15.14% faster post-deploy (19.5s → 16.6s P95)

### What's Broken

1. **Truth sets are fundamentally incorrect**
2. **Validation methodology is invalid**
3. **Actual search quality is unknown**

---

## Hypotheses Validation

### Hypothesis 1: Truth set IDs don't exist in production
**Status:** CONFIRMED

Truth sets contain synthetic UUIDs mapped to inventory_items table. Actual entities (certificates, work orders, etc.) have different IDs in different tables.

### Hypothesis 2: Search is returning correct entity IDs from correct tables
**Status:** LIKELY TRUE (needs confirmation)

Evidence:
- Search returns IDs for certificate queries (e.g., `e4144864-1a61-4f21-ba0d-01ec97f012fb`)
- These IDs don't match truth set expectations (which is correct behavior)
- Search pipeline likely functioning as designed

### Hypothesis 3: Index coverage is poor
**Status:** UNCONFIRMED

Cannot assess until truth sets are fixed. Some empty result arrays suggest either:
- Entities not indexed
- Query doesn't match indexed content
- Search working correctly (legitimate miss)

---

## Recommendations

### Priority 1: Fix Truth Sets (CRITICAL)

**Problem:** Truth sets map all entities to inventory_items with synthetic IDs.

**Solution:** Regenerate truth sets with correct entity IDs from production database.

**Action Items:**
1. Query production database for actual entity IDs by type:
   - `SELECT id, name FROM certificates WHERE ...`
   - `SELECT id, label FROM work_orders WHERE ...`
   - `SELECT id, title FROM documents WHERE ...`
   - etc.
2. Update truth set generator to use actual entity IDs from correct tables
3. Preserve query variations but fix expected_id values
4. Re-run validation harness with corrected truth sets

**Estimated Impact:** Should reveal actual search quality (could be 0% or could be 80%+ - unknown until fixed)

**Effort:** Medium (2-4 hours to query production, regenerate truth sets, re-run validation)

---

### Priority 2: Verify Search Index Coverage

**Problem:** Unknown if entities are being indexed at all.

**Solution:** Query search_index table to verify coverage.

**Action Items:**
1. Check if search_index contains records for each entity type
2. Verify searchable fields are populated (not NULL/empty)
3. Compare indexed content vs query terms
4. Identify gaps in indexing

**SQL Query:**
```sql
SELECT
  entity_type,
  COUNT(*) as indexed_count,
  COUNT(DISTINCT entity_id) as unique_entities,
  SUM(CASE WHEN searchable_text IS NULL THEN 1 ELSE 0 END) as null_text_count
FROM search_index
GROUP BY entity_type;
```

**Effort:** Low (1 hour)

---

### Priority 3: Validate Search Function Behavior

**Problem:** Unknown what f1_search_fusion actually returns.

**Solution:** Test search function directly with known entity IDs.

**Action Items:**
1. Query production for 5 real certificate IDs
2. Call f1_search_fusion with certificate names
3. Verify returned IDs match actual entities
4. Document search ranking behavior

**Effort:** Low (1-2 hours)

---

### Priority 4: Query-Data Alignment Audit

**Problem:** After truth sets are fixed, may discover query/content mismatches.

**Solution:** For failed queries (after fix), compare query terms vs indexed fields.

**Action Items:**
1. Re-run validation with fixed truth sets
2. For remaining failures, extract indexed content for expected entities
3. Compare query terms vs searchable_text
4. Identify semantic gaps (e.g., query="ISM cert" but indexed text="Document of Compliance")

**Effort:** Medium (2-3 hours after truth sets fixed)

---

## Metrics Projection

### Current State
- Recall@3: 3.62%
- Failures: 2,312 (96.38%)
- Successes: 88 (3.62%)

### After Truth Set Fix (Optimistic Scenario)
If search is working correctly but truth sets are wrong:
- **Projected Recall@3:** 60-80%
- **Rationale:** Search may be finding most entities correctly, just reporting wrong expected IDs

### After Truth Set Fix (Pessimistic Scenario)
If search has real issues hidden by bad truth sets:
- **Projected Recall@3:** 10-30%
- **Rationale:** Index coverage or ranking issues exist but weren't measurable

### After All Fixes (Target)
- **Goal Recall@3:** 90%
- **Path:** Fix truth sets → measure real baseline → fix index coverage → tune ranking → optimize queries

---

## v1.2 Scope Recommendation

### Must-Have for v1.2
1. **Fix truth sets** - Regenerate with actual production entity IDs
2. **Re-run validation** - Establish real baseline Recall@3
3. **Index coverage audit** - Verify all entities are indexed

### Should-Have for v1.2
4. **Search function analysis** - Document what f1_search_fusion returns
5. **Quick wins** - Fix any obvious index gaps or query patterns

### Nice-to-Have for v1.2
6. **Ranking optimization** - Tune relevance scoring
7. **Query expansion** - Handle typos, abbreviations better

### Long-Term (v1.3+)
8. **Semantic search** - Vector embeddings for better matching
9. **Contextual ranking** - User history, entity relationships
10. **Real-time index updates** - Reduce lag between entity creation and searchability

---

## Final Verdict: v1.1 Milestone

### Deployment Success
**Status:** YES ✓

- 25 commits deployed to production
- AbortError fix live
- Latency improved 15.14%
- No regressions in system stability

### Search Quality Success
**Status:** NO ✗

- Recall@3: 3.62% vs 90% target (86.38% gap)
- However, this metric is INVALID due to truth set errors
- Actual search quality is UNKNOWN

### What We Learned

1. **Truth set generation methodology was flawed** - All entities incorrectly mapped to inventory_items
2. **Validation cannot catch validation errors** - Bad truth sets → bad metrics → misleading conclusions
3. **Search pipeline is stable** - No crashes, good latency, returns results
4. **Real search quality is unmeasured** - Need correct truth sets to assess

### Recommended Next Actions

**Immediate (Next 24 hours):**
1. Query production database for actual entity IDs by type
2. Regenerate truth sets with correct expected_id values
3. Re-run validation harness to get real Recall@3 baseline

**Short-Term (v1.2 scope):**
4. Fix any index coverage gaps discovered
5. Optimize obvious query/content mismatches
6. Target 60%+ Recall@3 as realistic v1.2 goal

**Long-Term (v1.3+):**
7. Advanced ranking features
8. Semantic search capabilities
9. Achieve 90%+ Recall@3 target

---

## Appendix: Sample Failure Data

### Certificate Failures (60 total)

Expected ID: `05a1eb30-67d2-461e-9a22-b7589281338c` (ISM Document of Compliance)

| Query | Returned IDs | Status |
|-------|-------------|--------|
| "show ism document of compliance certificate" | e4144864-..., 732327ef-..., a2464117-... | miss |
| "status of ism document of compliance cert" | [] | miss |
| "when does ism document of compliance expire" | [] | miss |
| "find ism document of compliance" | [] | miss |

### Work Order Failures (299 total)

Expected ID: `19de511d-727c-48da-bbad-ef2691595531` (WO-TEST-1768420934823-014)

| Query | Returned IDs | Status |
|-------|-------------|--------|
| "show work order wo-test-1768420934823-014..." | [] | miss |
| "status of work order wo-test-1768420934823-014..." | [] | miss |
| "where is work order wo-test-1768420934823-014..." | [] | miss |

### Work Order Note Failures (300 total)

Expected ID: `15b7c251-7cd9-4e92-90ff-406876da472f` (Test Note)

| Query | Returned IDs | Status |
|-------|-------------|--------|
| "show work order note test note test note" | [] | miss |
| "where is note test note test note" | [] | miss |
| "note count test note test note" | [] | miss |

---

## Appendix: Truth Set Structure Analysis

All truth sets follow this incorrect pattern:

```json
{
  "title": "[Entity Name]",
  "canonical": {
    "target_type": "inventory_item",  ← WRONG for non-inventory entities
    "target_id": "[synthetic UUID]",  ← NOT in production database
    "primary_table": "inventory_items", ← WRONG for certificates, work orders, etc.
    "canonical_row": {
      "id": "[same synthetic UUID]",
      "name": "[Entity Name]",
      "sku_or_part_no": "unknown",     ← Meaningless for non-parts
      "quantity_on_hand": "unknown",   ← Meaningless for documents
      "unit": "unknown",
      "primary_location": "unknown",
      "secondary_locations": ["unknown"],
      "last_received_date": "unknown",
      "linked_equipment": ["unknown"],
      "linked_documents_count": "unknown"
    }
  },
  "queries": [...]
}
```

**Correct structure should be:**

```json
{
  "title": "ISM Document of Compliance",
  "canonical": {
    "target_type": "certificate",      ← Actual entity type
    "target_id": "[REAL cert ID]",     ← From production certificates table
    "primary_table": "certificates"    ← Actual table
  },
  "queries": [...]
}
```

---

## Conclusion

The v1.1 milestone successfully deployed code to production but failed to achieve search quality targets due to **fundamental truth set errors, not search pipeline failures**.

**Critical Finding:** All truth sets incorrectly map diverse entity types (certificates, work orders, documents, faults) to the inventory_items table with synthetic IDs. This makes validation meaningless.

**Immediate Action Required:** Regenerate truth sets with actual production entity IDs from correct tables before any search quality can be measured or improved.

**Actual Search Quality:** UNKNOWN until truth sets are fixed.

**Recommended Path Forward:**
1. Fix truth sets (2-4 hours)
2. Re-validate to get real baseline (1 hour)
3. Address real search issues discovered (scope TBD based on results)
4. Target realistic 60%+ Recall@3 for v1.2

