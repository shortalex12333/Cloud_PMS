# Entity Extraction Pipeline: Engineering Guide

**PR:** #76
**Branch:** `feat/systemic-entity-extraction-100-accuracy`
**Date:** 2026-02-03
**Accuracy:** 100% (164/164 ground truth tests)

---

## 1. Executive Summary

This PR fundamentally changes how the entity extraction pipeline handles natural language queries. Instead of manually maintaining alias dictionaries and hardcoded mappings, the system now uses **algorithmic normalization** and a **priority-based extraction system**.

### Key Architectural Changes

| Component | Before | After |
|-----------|--------|-------|
| Plural handling | Manual aliases (`gaskets` → `gasket`) | Automatic via `inflect` library |
| Abbreviations | Scattered across files | Centralized in `TextNormalizer` |
| Extraction order | Arbitrary dict iteration | Priority-based `doc_priority_types` |
| Brand misspellings | Exact match only | Fuzzy matching (80% threshold) |
| Confidence thresholds | Missing for many types | Complete coverage |

---

## 2. What Changed (File by File)

### 2.1 `extraction/text_normalizer.py` (NEW)

**Purpose:** Eliminates manual alias dictionaries through algorithmic normalization.

```python
from extraction.text_normalizer import TextNormalizer

normalizer = TextNormalizer()

# Automatic plural → singular
normalizer.singularize("gaskets")      # → "gasket"
normalizer.singularize("filters")      # → "filter"
normalizer.singularize("batteries")    # → "battery"

# Abbreviation expansion
normalizer.expand_abbreviation("gen 1")           # → "generator 1"
normalizer.expand_abbreviation("ME port")         # → "main engine port"
normalizer.expand_abbreviation("fwd thruster")    # → "forward thruster"

# Compound normalization
normalizer.normalize_compounds("water maker")     # → "watermaker"
normalizer.normalize_compounds("air conditioning") # → "air_conditioning"

# Full pipeline
normalizer.normalize_for_matching("gen 1 oil filters")
# → "generator 1 oil filter"
```

**When to use:** Any time you need to compare user input against canonical terms.

---

### 2.2 `extraction/regex_extractor.py`

**Changes:**
1. **Priority extraction system** - Critical patterns run BEFORE brand gazetteer
2. **New pattern types** - `voyage_type`, `certificate_type`, `work_order_type`, etc.
3. **Gazetteer auto-expansion** - Plurals added automatically

#### Priority Extraction Order

```python
doc_priority_types = [
    'document_id',        # DNV-12345, CERT-2025-001
    'document_type',      # certificate, invoice, PO
    'location_on_board',  # engine room, bridge, galley
    'work_order_status',  # not completed, incomplete, pending
    'part_number_prefix', # "starting with FLT"
]
# These run BEFORE brand/equipment gazetteer
```

**Why this matters:** Previously, "beginning with CAT" would extract "CAT" as a brand. Now `part_number_prefix` extracts the full phrase first.

#### New Pattern Types

| Type | Examples | Use Case |
|------|----------|----------|
| `voyage_type` | "at sea", "in port", "underway" | Crew hours of rest queries |
| `certificate_type` | "class", "environmental", "safety" | Document lens |
| `work_order_type` | "corrective", "preventive", "scheduled" | Work order lens |
| `equipment_status` | "operational", "not operational", "failed" | Equipment queries |
| `quantity_comparison` | "below 5", "more than 10", "zero stock" | Inventory queries |
| `part_number_prefix` | "starting with FLT", "prefix CAT" | Part search |

---

### 2.3 `extraction/extraction_config.py`

**Added confidence thresholds for ALL entity types:**

```python
confidence_thresholds = {
    # Previously missing - caused 100% failure in Parts Lens
    'brand': 0.35,
    'equipment_brand': 0.35,
    'manufacturer': 0.35,

    # Standard types
    'equipment': 0.70,
    'measurement': 0.75,
    'fault_code': 0.70,
    # ... etc
}
```

**Impact:** Brand entities were being extracted correctly but filtered out by the merger because they fell below the default 0.75 threshold.

---

### 2.4 `entity_extraction_loader.py`

**Added:**
1. `BRAND_ALIASES` - Maps misspellings to canonical names
2. `CORE_STOCK_STATUS` - Compound stock phrases
3. `CORE_SHOPPING_LIST_TERMS` - Shopping list keywords
4. `CORE_APPROVAL_STATUSES` - Approval states
5. Updated `calculate_weight()` with all entity types

```python
BRAND_ALIASES = {
    'catterpillar': 'Caterpillar',
    'catepillar': 'Caterpillar',
    'volvo penta': 'Volvo Penta',
    'volvopenta': 'Volvo Penta',
    'northen lights': 'Northern Lights',
    # ... 20+ common misspellings
}
```

---

### 2.5 `pipeline_v1.py`

**Added lens-specific transformations:**

```python
# Receiving Lens transformation (lines 539-583)
if is_receiving_context:
    # ORG/BRAND → SUPPLIER_NAME
    # status → RECEIVING_STATUS

# Shopping List transformation
if is_shopping_context:
    # action → SHOPPING_ACTION
    # approval_status → APPROVAL_STATUS
```

---

## 3. Testing Guide

### 3.1 Run Ground Truth Tests

```bash
cd apps/api
python -m tests.test_ground_truth_v2
```

**Expected output:**
```
OVERALL ACCURACY: 100.0%
Total expected entities: 164
Misses: 0
```

### 3.2 Test Query Difficulty Levels

#### Level 1: Basic Queries (Should always work)
```
"Volvo Penta oil filter"           → brand:Volvo Penta, part:oil filter
"generator maintenance"            → equipment:generator, action:maintenance
"parts in stock"                   → stock_status:in stock
```

#### Level 2: Abbreviations & Synonyms
```
"gen 1 running hours"              → equipment:generator 1
"ME port oil pressure"             → equipment:main engine port
"watermaker membrane"              → equipment:watermaker, part:membrane
"desalinator filters"              → equipment:watermaker, part:filter
```

#### Level 3: Misspellings
```
"catterpillar fuel pump"           → brand:Caterpillar, part:fuel pump
"fleetgard filters"                → brand:Fleetguard, part:filter
"northen lights generator"         → brand:Northern Lights, equipment:generator
```

#### Level 4: Negation & Comparison
```
"work orders not completed"        → work_order_status:not completed
"parts with quantity below 5"      → quantity_comparison:below 5
"equipment not operational"        → equipment_status:not operational
"items with zero stock"            → stock_status:zero stock
```

#### Level 5: Compound & Context-Dependent
```
"Captain Mitchell hours of rest at sea this week"
→ person:Captain Mitchell, voyage_type:at sea, time_ref:this week

"class certificates expiring in 30 days"
→ certificate_type:class, time_ref:30 days

"corrective maintenance for bow thruster"
→ work_order_type:corrective, equipment:bow thruster
```

### 3.3 Test Each Lens

```bash
# Parts Lens - Brand extraction
curl -X POST $API_URL/query \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"query": "Caterpillar oil filters", "lens": "parts"}'
# Expected: entities include brand:Caterpillar, part:oil filter

# Inventory Lens - Stock status
curl -X POST $API_URL/query \
  -d '{"query": "critically low stock items", "lens": "inventory"}'
# Expected: stock_status:critically low (NOT urgency_level:critical)

# Receiving Lens - Supplier transformation
curl -X POST $API_URL/query \
  -d '{"query": "Racor deliveries pending", "lens": "receiving"}'
# Expected: SUPPLIER_NAME:Racor, RECEIVING_STATUS:pending

# Work Order Lens - Negation
curl -X POST $API_URL/query \
  -d '{"query": "incomplete maintenance tasks", "lens": "work_orders"}'
# Expected: work_order_status:incomplete

# Crew Lens - Voyage context
curl -X POST $API_URL/query \
  -d '{"query": "captain hours at sea", "lens": "crew"}'
# Expected: role:captain, voyage_type:at sea
```

---

## 4. Frontend/UI Implications

### 4.1 Entity Types for Rendering

The pipeline now extracts these entity types that should render as **filter chips/buttons**:

| Entity Type | Render As | Example |
|------------|-----------|---------|
| `brand` / `equipment_brand` | Brand filter chip | "Volvo Penta" |
| `equipment` / `equipment_type` | Equipment dropdown | "Generator 1" |
| `stock_status` | Status badge (red/yellow/green) | "Low Stock" |
| `time_ref` | Date range picker | "This Week" |
| `work_order_status` | Status filter | "Not Completed" |
| `voyage_type` | Toggle (At Sea / In Port) | "At Sea" |
| `quantity_comparison` | Numeric filter | "< 5" |

### 4.2 Action Entities

These should render as **action buttons**:

| Action | Button Label | Context |
|--------|-------------|---------|
| `approve` | "Approve Selected" | Shopping list, Work orders |
| `complete` | "Mark Complete" | Work orders |
| `order` | "Add to Order" | Parts, Shopping list |
| `restock` | "Restock" | Inventory |
| `schedule` | "Schedule" | Work orders |
| `inspect` | "Create Inspection" | Equipment |

### 4.3 Negation Handling

When `negated: true` is set on an entity, render differently:

```javascript
// Entity: { type: "status", value: "completed", negated: true }
// Render as: "NOT Completed" with strikethrough or red badge

// Entity: { type: "stock_status", value: "in_stock", negated: true }
// Render as: "Out of Stock" indicator
```

---

## 5. Adding New Entity Types

### Step 1: Add Pattern to `regex_extractor.py`

```python
'my_new_type': [
    re.compile(r'\b(pattern1|pattern2)\b', re.IGNORECASE),
],
```

### Step 2: Add to `PRECEDENCE_ORDER`

```python
PRECEDENCE_ORDER = [
    # ... existing types
    'my_new_type',  # Add at appropriate priority
]
```

### Step 3: Add Confidence Threshold

```python
# extraction_config.py
confidence_thresholds = {
    'my_new_type': 0.70,
}
```

### Step 4: Add Weight (if gazetteer-based)

```python
# entity_extraction_loader.py → calculate_weight()
'my_new_type': 2.5,
```

### Step 5: Add Pipeline Transformation (if needed)

```python
# pipeline_v1.py
if entity_type == 'my_new_type':
    lens_type = 'MY_NEW_TYPE'
```

### Step 6: Add Ground Truth Test

```json
// tests/ground_truth_v2.json
{
  "id": "NEW-001",
  "lens": "relevant_lens",
  "dimension": "basic",
  "query": "test query for my new type",
  "expected": [{"type": "my_new_type", "value": "expected_value"}]
}
```

---

## 6. Troubleshooting

### Entity Not Extracted

1. **Check patterns:** Does a regex pattern exist for this entity type?
2. **Check precedence:** Is another pattern claiming the span first?
3. **Check confidence:** Is the threshold too high?

```python
# Debug extraction
from extraction.regex_extractor import RegexExtractor
extractor = RegexExtractor()
entities, spans = extractor.extract("your query here")
for e in entities:
    print(f"{e.type}: {e.text} (conf: {e.confidence}, span: {e.span})")
```

### Wrong Entity Type

1. **Check priority order:** Higher priority patterns extract first
2. **Check gazetteer:** Is the term in multiple gazetteers?

```python
# Check what's in gazetteer
print(extractor.gazetteer.keys())
for term in extractor.gazetteer['equipment']:
    if 'your_term' in term.lower():
        print(f"Found: {term}")
```

### Plural Not Matching

1. **Verify inflect is installed:** `pip install inflect`
2. **Check expandable_types:** Is your type in the list?

```python
# In _expand_gazetteer_variations()
expandable_types = {'equipment', 'equipment_type', 'part', 'brand', 'subcomponent'}
```

---

## 7. Performance Considerations

- **TextNormalizer uses LRU cache** (10,000 entries) - first call is slow, subsequent calls are O(1)
- **Gazetteer expansion happens once at startup** - adds ~2s to cold start
- **Priority extraction adds minimal overhead** - only 5 types checked first

---

## 8. Quick Reference

### Import Paths
```python
from extraction.regex_extractor import RegexExtractor
from extraction.text_normalizer import TextNormalizer, normalize_for_matching
from extraction.extraction_config import ExtractionConfig
from entity_extraction_loader import BRAND_ALIASES, CORE_BRANDS
```

### Run Tests
```bash
python -m tests.test_ground_truth_v2          # Ground truth (should be 100%)
python -m tests.test_comprehensive_accuracy   # Full accuracy suite
python -m tests.test_crew_lens_entity_pipeline # Crew lens specific
```

### Key Files
| File | Purpose |
|------|---------|
| `extraction/regex_extractor.py` | Pattern matching & extraction |
| `extraction/text_normalizer.py` | Plural/abbreviation handling |
| `extraction/extraction_config.py` | Confidence thresholds |
| `entity_extraction_loader.py` | Gazetteers & weights |
| `pipeline_v1.py` | Lens transformations |
| `tests/ground_truth_v2.json` | Test cases |

---

## 9. Contact

For questions about this implementation, refer to PR #76 or the commit history on branch `feat/systemic-entity-extraction-100-accuracy`.
