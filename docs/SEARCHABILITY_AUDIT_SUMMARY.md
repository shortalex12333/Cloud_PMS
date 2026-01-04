# SEARCHABILITY AUDIT SUMMARY
## Generated: 2026-01-03

---

## THE ANSWER

> "Are results missing because the data isn't there — or because our search logic is wrong?"

**ANSWER: 42.5% of searchable columns fail because SEARCH LOGIC IS WRONG.**

---

## STATUS BREAKDOWN

| Category | Count | Percentage | Description |
|----------|-------|------------|-------------|
| **E) WRONG VALUES (BUG)** | **45** | **42.5%** | Data exists, manual SQL works, pipeline returns 0 |
| A) Empty by data | 28 | 26.4% | Table/column has no data |
| B) Non-searchable by design | 22 | 20.8% | Timestamps, metadata, etc. |
| OK) Working | 11 | 10.4% | Correctly searchable |
| UNKNOWN | 0 | 0.0% | - |

---

## ROOT CAUSE

The `ENTITY_SOURCE_MAP` in `api/search_planner.py` is **INCOMPLETE**.

It only routes to 13 table/column combinations, but there are **106 searchable text columns** across the 21 tables with data.

**Coverage: 13 / 106 = 12.3%**

---

## TOP 10 BUGS (Data exists, pipeline fails)

| # | Table.Column | Manual Rows | Pipeline Rows | Sample Value |
|---|--------------|-------------|---------------|--------------|
| 1 | alias_symptoms.alias_type | 10 | 0 | "manual" |
| 2 | alias_symptoms.source | 10 | 0 | "manual" |
| 3 | alias_systems.alias_type | 10 | 0 | "manual" |
| 4 | alias_systems.source | 10 | 0 | "manual" |
| 5 | document_chunks.content | 10 | 0 | (PDF content) |
| 6 | document_chunks.graph_extract_status | 10 | 0 | "pending" |
| 7 | entity_staging.entity_type | 10 | 0 | "document_section" |
| 8 | entity_staging.source_storage_path | 10 | 0 | (file path) |
| 9 | entity_staging.status | 10 | 0 | "completed" |
| 10 | graph_nodes.extraction_source | 10 | 0 | "qwen_14b_local" |

---

## SPECIFIC HIGH-IMPACT BUGS

### 1. pms_parts.part_number
- **Sample**: "ENG-0198-824"
- **Manual SQL**: Returns 1 row
- **Pipeline**: Returns 0 rows
- **Reason**: Entity type PART_NUMBER routes to pms_parts.part_number, but match fails
- **This is a search logic bug, not missing routing**

### 2. v_inventory.part_number
- Same bug as above - part numbers aren't being found

### 3. search_fault_code_catalog.severity
- **Sample**: "warning"
- **Manual SQL**: Returns 2 rows
- **Pipeline**: Returns 0 rows
- **Entity type**: SEVERITY routes here but match fails

---

## COLUMNS WITH NO ROUTING AT ALL

These columns have data but ZERO entity types route to them:

| Table | Column | Row Count | Sample |
|-------|--------|-----------|--------|
| pms_parts | description | 250 | "Glow Plug" |
| pms_parts | category | 250 | "Engine Room" |
| v_inventory | description | 250 | "Glow Plug" |
| v_inventory | category | 250 | "Engine Room" |
| v_inventory | equipment | 250 | "Generator 1" |
| v_inventory | system | 250 | "Electrical System" |
| v_inventory | manufacturer | 250 | "Cummins" |
| entity_staging | entity_value | 904 | (entity names) |
| entity_staging | canonical_label | 904 | (canonical names) |
| relationship_staging | from_canonical | 674 | (graph entities) |
| relationship_staging | to_canonical | 674 | (graph entities) |
| symptom_aliases | alias | 37 | "shaking" |

---

## HONEST ASSESSMENT

### What My Previous Claims Were:
- "99.9% pass rate"
- "Search works across intents/entities"
- "5 read capabilities fully operational"

### What's Actually True:
- **Only 10.4% of searchable columns work**
- **42.5% have bugs where data exists but search fails**
- **ENTITY_SOURCE_MAP covers only 12.3% of searchable columns**

### Why the "99.9% pass rate" was fake:
The test assertions were too weak. They checked:
- "Did something return?" ✓
- "Did it not crash?" ✓

They did NOT check:
- "Did it search the right columns?" ✗
- "Did it find the data that exists?" ✗
- "Did manual SQL find more than pipeline?" ✗

---

## FIXES REQUIRED

1. **Expand ENTITY_SOURCE_MAP** to cover all 106 text columns
2. **Fix part_number routing** - search is broken even where routing exists
3. **Add severity routing** - same issue
4. **Add tests that compare manual SQL vs pipeline output**
5. **Measure false negative rate against ground truth**

---

## CONCLUSION

The search system is **not working correctly**.

- Data exists
- Manual SQL finds it
- Pipeline doesn't

This is a **correctness bug**, not a data availability issue.
