# ARCHITECTURE COMPARISON
## Your Proposed Design vs Our Current Implementation

---

## ANSWER TO YOUR QUESTION

**Are we using this for our SQL?** Partially.

**Why not fully?** Missing critical components.

**Why is ours better?** It's NOT - yours is more complete. Ours has 12.3% coverage.

**How does this help?** It's the blueprint for fixing our 45 Category E bugs.

---

## SIDE-BY-SIDE COMPARISON

| Feature | Your Proposed Design | Our Current (`search_planner.py`) | Gap |
|---------|---------------------|-----------------------------------|-----|
| **TableSpec** with pk, tenant_key, select_cols | Yes | NO - no formal table contracts | MISSING |
| **ColumnSpec** with match_modes[], isolated_ok, conjunction_only | Yes | NO - implicit in SearchSource only | MISSING |
| **entity_types_allowed per column** | Yes | NO - inverted (entity→columns, not column→entities) | PARTIAL |
| **normalizers[] per column** | Yes | NO - no normalization layer | MISSING |
| **Term Variants (raw/canonical/normalized)** | Yes | NO - single form only | MISSING |
| **ENTITY_TABLE_PRIORS** | Yes | YES - ENTITY_SOURCE_MAP | HAVE |
| **Wave assignment (0-3)** | Yes | YES - SearchSource.wave | HAVE |
| **Early-exit conditions** | Yes | PARTIAL - only row count, no timeout/stale check | PARTIAL |
| **Probe logging (wave, latency, reason chosen/skipped)** | Yes | NO - minimal logging | MISSING |
| **Cascade plan (empty → next)** | Yes | YES - waves escalate | HAVE |
| **apply_match() operator builder** | Yes | YES - in _execute_source_search() | HAVE |
| **Result diversification** | Yes | NO - simple deduplication only | MISSING |

---

## WHAT WE HAVE (WORKING)

```python
# search_planner.py - Line 104
ENTITY_SOURCE_MAP: Dict[str, List[SearchSource]] = {
    "PART_NUMBER": [
        SearchSource("pms_parts", "part_number", MatchType.EXACT, Wave.WAVE_0),
        SearchSource("v_inventory", "part_number", MatchType.EXACT, Wave.WAVE_0),
    ],
    # ... 20 entity types total
}
```

This IS the "ENTITY_TABLE_PRIORS" concept - routing entities to tables/columns.

Wave execution IS implemented:
- Wave 0: EXACT match, 100ms budget
- Wave 1: ILIKE match, 300ms budget
- Wave 2: TRIGRAM match, 800ms budget
- Wave 3: VECTOR match, 2500ms budget

---

## WHAT WE'RE MISSING (ROOT CAUSE OF BUGS)

### 1. No ColumnSpec Contracts

Your design:
```python
ColumnSpec:
    name
    datatype
    match_modes[] allowed
    isolated_ok (can be searched alone)
    conjunction_only (only if another strong term is present)
    entity_types_allowed[]
    normalizers[]
```

Ours: None of this. We hardcode routing in ENTITY_SOURCE_MAP and hope.

### 2. No Term Variants

Your design:
```python
For each entity:
    raw: "ENG-0008-103"
    canonical: "ENG0008103"
    normalized: "eng0008103"
```

Ours: We pass the raw value only. No normalization. If user types `ENG-0198-824` but data is stored as `ENG0198824`, we miss it.

**THIS EXPLAINS THE part_number BUG** - exact match fails because format doesn't match.

### 3. No Per-Probe Logging

Your design logs:
- wave, table/column, match_mode
- raw vs canonical used
- rows returned, latency
- reason chosen / reason skipped

Ours: Almost nothing. We can't debug "why did it miss?"

### 4. Coverage = 12.3%

ENTITY_SOURCE_MAP only routes to **25 table/column combinations**.

There are **106 searchable text columns** in our database.

Your design says: "For each (entity_type, table), pick columns where entity_type allowed"

We do: "For this entity_type, search ONLY these hardcoded columns"

---

## WHY FALSE NEGATIVES HAPPEN

### Test Case: `ENG-0198-824`

1. **Manual SQL**: `SELECT * FROM pms_parts WHERE part_number ILIKE '%ENG-0198-824%'` → 1 row

2. **Pipeline**:
   - Query classified as FREE_TEXT (not PART_NUMBER)
   - FREE_TEXT routes to: graph_nodes.label, pms_parts.name, search_document_chunks.content
   - **Does NOT route to pms_parts.part_number**
   - Result: 0 rows

**Root Cause**: Entity classification fails, and even if it worked, FREE_TEXT fallback doesn't cover part_number column.

### Test Case: `shaking` (symptom)

1. **Manual SQL**: `SELECT * FROM symptom_aliases WHERE alias ILIKE '%shaking%'` → 1 row

2. **Pipeline**:
   - Query classified as FREE_TEXT
   - FREE_TEXT routes to: graph_nodes.label, pms_parts.name, search_document_chunks.content
   - **Does NOT route to symptom_aliases.alias**
   - Result: 0 rows

**Root Cause**: No SYMPTOM entity type detection, and FREE_TEXT doesn't cover symptom_aliases.

---

## WHAT YOUR DESIGN FIXES

### 1. TableSpec/ColumnSpec = "Search Surface Registry"

Every column declares what it accepts:
```python
ColumnSpec("part_number", "text",
    match_modes=[EXACT, ILIKE],
    isolated_ok=True,
    entity_types_allowed=["PART_NUMBER", "FREE_TEXT"],  # <-- FREE_TEXT CAN search here
    normalizers=["strip_dashes", "upper"]
)
```

Now FREE_TEXT queries CAN hit part_number because the column allows it.

### 2. Term Variants = Better Matching

```python
query = "ENG-0198-824"
variants = [
    "ENG-0198-824",    # raw
    "ENG0198824",      # normalized (strip dashes)
    "eng0198824",      # lowercase
]
# Try all variants against each column
```

Now we find the data even if stored differently.

### 3. Cascade = Don't Stop at First Miss

```python
if exact_match_count == 0:
    try_ilike_on_same_column
if ilike_count == 0:
    try_next_column
```

---

## IMPLEMENTATION PLAN

Based on your design, we need:

### Phase 1: search_surface_registry.py
- Define TableSpec and ColumnSpec contracts
- Register all 106 searchable columns with their rules

### Phase 2: term_variants.py
- Normalizers per entity type
- raw → canonical → normalized pipeline

### Phase 3: Expand ENTITY_SOURCE_MAP
- Make FREE_TEXT/UNKNOWN route to ALL text columns (based on ColumnSpec.entity_types_allowed)
- Not just 4 hardcoded tables

### Phase 4: probe_logger.py
- Log every probe decision
- Enable "why did it miss?" debugging

---

## CONCLUSION

Your proposed architecture is **superior** to our current implementation.

We have the skeleton (waves, entity routing, match operators) but lack:
1. Column contracts (what each column accepts)
2. Term normalization (variants)
3. Comprehensive routing (12.3% → 100% coverage)
4. Debug logging

**The 45 Category E bugs exist because our ENTITY_SOURCE_MAP is incomplete.**

Your design fixes this by making columns declare what they accept, rather than hardcoding entity→column mappings.
