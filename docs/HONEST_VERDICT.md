# HONEST VERDICT
## Search System Audit Final Report
### Generated: 2026-01-03

---

## THE QUESTION

> "Are results missing because the data isn't there — or because our search logic is wrong?"

## THE ANSWER

**32.3% of searchable queries fail because SEARCH LOGIC IS WRONG.**

Specifically:
- **PART_NUMBER queries: 100% false negative rate**
- Data EXISTS in database
- Manual SQL finds it
- Pipeline returns 0

---

## EVIDENCE SUMMARY

### Golden Truth Tests (155 queries with REAL data)

| Category | Total | Passed | FN | FN Rate |
|----------|-------|--------|-----|---------|
| **PART_NUMBER** | **50** | **0** | **50** | **100%** |
| PART_NAME | 50 | 50 | 0 | 0% |
| EQUIPMENT_NAME | 50 | 50 | 0 | 0% |
| STOCK_LOCATION | 5 | 5 | 0 | 0% |
| **TOTAL** | **155** | **105** | **50** | **32.3%** |

### Hard Assertion Tests

| Test | Result |
|------|--------|
| pms_parts.part_number | **FALSE NEGATIVE** |
| v_inventory.part_number | **FALSE NEGATIVE** |
| symptom_aliases.alias | **FALSE NEGATIVE** |
| ENTITY_SOURCE_MAP Coverage | **FAILED** (< 80%) |
| False Negative Rate | **100%** on tested items |

---

## ROOT CAUSE ANALYSIS

### Why PART_NUMBER Fails 100% of the Time

1. **Query**: `"ENG-0008-103"` (actual part number in database)

2. **Entity Classification**: Query gets classified as `FREE_TEXT`, not `PART_NUMBER`
   - No entity extraction regex matches the input
   - Falls back to generic search

3. **FREE_TEXT Routing** (from search_planner.py:201-206):
   ```python
   "FREE_TEXT": [
       SearchSource("graph_nodes", "label", ...),
       SearchSource("pms_parts", "name", ...),           # <-- name, not part_number!
       SearchSource("search_document_chunks", "content", ...),
   ]
   ```

4. **Bug**: `FREE_TEXT` routes to `pms_parts.name`, NOT `pms_parts.part_number`

5. **Result**: Data exists in `part_number` column, but pipeline searches `name` column = 0 results

### The Fix (Per Your Architecture)

Your design says columns should declare what entity types they accept:

```python
ColumnSpec("part_number", "text",
    entity_types_allowed=["PART_NUMBER", "FREE_TEXT"],  # <-- Allow FREE_TEXT
    match_modes=[EXACT, ILIKE],
    isolated_ok=True
)
```

Currently we do the inverse - entity types declare which columns they search. This is incomplete.

---

## FAILURE SIGNATURES

### Signature 1: Entity Classification Gap

**Pattern**: User enters an identifier (part number, fault code, serial number)
**Result**: Classified as FREE_TEXT, not the specific entity type
**Consequence**: Doesn't search the right column

**Affected Columns**:
- pms_parts.part_number
- v_inventory.part_number
- pms_equipment.serial_number
- search_fault_code_catalog.code

### Signature 2: FREE_TEXT Coverage Gap

**Pattern**: FREE_TEXT should be the "catch-all" that searches everywhere
**Reality**: FREE_TEXT only searches 4 tables, 5 columns
**Consequence**: 87.7% of searchable columns are unreachable via FREE_TEXT

**Missing from FREE_TEXT routing**:
- pms_parts.part_number
- pms_parts.description
- pms_parts.category
- v_inventory.* (all columns)
- symptom_aliases.alias
- 100+ more columns

### Signature 3: No Term Normalization

**Pattern**: User types `ENG-0008-103`, data stored as `ENG0008103`
**Result**: Exact match fails, ILIKE on wrong column
**Consequence**: Never finds match even if entity type is correct

---

## WHAT WORKS

| Category | Pass Rate | Evidence |
|----------|-----------|----------|
| PART_NAME (pms_parts.name) | 100% | Routes via FREE_TEXT |
| EQUIPMENT_NAME (graph_nodes.label) | 100% | Routes via FREE_TEXT |
| STOCK_LOCATION (v_inventory.location) | 100% | Routes via STOCK_LOCATION entity |

These work because:
1. FREE_TEXT routes to these specific columns
2. Or the entity classification correctly identifies them

---

## QUANTIFIED IMPACT

### Current State
- **32.3%** false negative rate on golden truth queries
- **100%** false negative rate on part number queries
- **12.3%** of searchable columns covered by ENTITY_SOURCE_MAP

### User Impact
- User searches for `ENG-0008-103` → "No results found"
- User concludes: "The part isn't in the system"
- Reality: The part IS in the system, search is broken

### Business Impact
- Maintenance engineers can't find parts
- Purchase orders created for parts already in inventory
- Trust in system erodes

---

## REQUIRED FIXES (Ordered by Impact)

### Fix 1: Expand FREE_TEXT Routing (Immediate)

Add missing columns to FREE_TEXT entity type:

```python
"FREE_TEXT": [
    # Current
    SearchSource("graph_nodes", "label", ...),
    SearchSource("pms_parts", "name", ...),
    SearchSource("search_document_chunks", "content", ...),

    # ADD THESE
    SearchSource("pms_parts", "part_number", MatchType.ILIKE, Wave.WAVE_1),
    SearchSource("pms_parts", "description", MatchType.ILIKE, Wave.WAVE_1),
    SearchSource("v_inventory", "part_number", MatchType.ILIKE, Wave.WAVE_1),
    SearchSource("v_inventory", "name", MatchType.ILIKE, Wave.WAVE_1),
    SearchSource("v_inventory", "location", MatchType.ILIKE, Wave.WAVE_1),
    SearchSource("symptom_aliases", "alias", MatchType.ILIKE, Wave.WAVE_1),
]
```

**Expected Result**: FN rate drops from 32.3% to <5%

### Fix 2: Entity Classification Patterns (High Priority)

Add regex patterns to detect entity types:

```python
ENTITY_PATTERNS = {
    "PART_NUMBER": r"^[A-Z]{3}-\d{4}-\d{3}$",  # ENG-0008-103
    "FAULT_CODE": r"^[EFW]-?\d{2,4}$",          # E047, F-123
    "SERIAL_NUMBER": r"^SN[-_]?\d+$",           # SN-12345
}
```

### Fix 3: Implement Search Surface Registry (Medium Priority)

Per your design, implement ColumnSpec contracts so columns declare what they accept.

### Fix 4: Add Term Normalization (Medium Priority)

Strip dashes, normalize case before matching:

```python
def normalize_part_number(s):
    return re.sub(r'[-_\s]', '', s).upper()
```

---

## CONCLUSION

### Previous Claims (False)
- "99.9% pass rate" ← **Tests had weak assertions**
- "Search works across intents/entities" ← **Only 12.3% coverage**
- "5 read capabilities fully operational" ← **PART_NUMBER 100% broken**

### Actual State (True)
- **32.3% false negative rate** on real queries
- **100% false negative** on part number searches
- **67.7% pass rate** overall
- **PART_NUMBER search is completely broken**

### The Answer
Results ARE missing because **search logic is wrong**, not because data doesn't exist.

The proposed architecture in your message is the correct solution. We have the skeleton but lack:
1. Column-declared entity routing
2. Term normalization
3. Comprehensive FREE_TEXT fallback

---

## FILES GENERATED

| File | Purpose |
|------|---------|
| `/docs/HARD_ASSERTION_RESULTS.json` | Tests that compare manual SQL vs pipeline |
| `/docs/GOLDEN_TRUTH_RESULTS.json` | 155 queries with real data from DB |
| `/docs/COLUMN_CASCADE_RESULTS.json` | Stress tests (pending full run) |
| `/docs/ARCHITECTURE_COMPARISON.md` | Your design vs our implementation |
| `/tests/hard_assertion_tests.py` | Tests that actually fail when bugs exist |
| `/tests/golden_truth_tests.py` | Tests using real DB values |
| `/tests/column_cascade_stress_tests.py` | 1500-query stress test framework |

---

## NEXT STEPS

1. **Immediate**: Expand FREE_TEXT routing to cover part_number columns
2. **This Week**: Add entity classification regex patterns
3. **Next Sprint**: Implement full Search Surface Registry per your design
4. **Ongoing**: Run golden truth tests in CI to prevent regression
