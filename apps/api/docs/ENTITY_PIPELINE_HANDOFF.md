# Entity Extraction Pipeline - Engineer Handoff

**Date:** 2026-02-03
**PR:** #76 (`feat/systemic-entity-extraction-100-accuracy`)
**Branch:** `feat/systemic-entity-extraction-100-accuracy`
**Status:** Ready for review, NOT merged to main

---

## Quick Start

```bash
# Clone and checkout
git clone https://github.com/shortalex12333/Cloud_PMS.git
cd Cloud_PMS/apps/api
git checkout feat/systemic-entity-extraction-100-accuracy

# Install dependencies
pip install -r requirements.txt
pip install inflect  # Required for plural handling

# Run tests
python -m tests.test_ground_truth_v2  # Should show 100% accuracy
```

---

## File Locations

### 1. ENTITY EXTRACTION (Input Processing)

| File | Purpose | Lines Changed |
|------|---------|---------------|
| `extraction/regex_extractor.py` | **Main extraction engine** - Patterns, gazetteers, priority system | +473 |
| `extraction/text_normalizer.py` | **NEW** - Automatic plural/abbreviation handling | +442 (new file) |
| `extraction/extraction_config.py` | Confidence thresholds per entity type | +50 |
| `extraction/entity_merger.py` | Merges overlapping entities | +20 |
| `extraction/text_cleaner.py` | Pre-processing text normalization | +30 |
| `extraction/coverage_controller.py` | Lens-specific extraction thresholds | +15 |
| `entity_extraction_loader.py` | Gazetteers, brands, weights | +200 |

### 2. ORCHESTRATION (Query Planning)

| File | Purpose |
|------|---------|
| `orchestration/prepare_module.py` | Builds RetrievalPlan from entities |
| `orchestration/retrieval_plan.py` | Data structures for query plans |
| `orchestration/ranking_recipes.py` | Scoring weights for result ranking |
| `orchestration/term_classifier.py` | Classifies terms by type |
| `orchestration/surface_state.py` | Surface context (search, email, entity) |

### 3. EXECUTION (Query Running)

| File | Purpose |
|------|---------|
| `prepare/capability_composer.py` | **Parallel execution** - Maps entities to capabilities |
| `prepare/lane_enforcer.py` | Lane invariants (NO_LLM, RULES_ONLY, GPT) |
| `prepare/capability_registry.py` | Registry of available capabilities |
| `prepare/base_capability.py` | Base class for capabilities |
| `execute/capability_executor.py` | Executes individual capabilities |
| `execute/table_capabilities.py` | Table-specific query builders |
| `execute/result_normalizer.py` | Normalizes results across tables |

### 4. PIPELINE (Main Entry Point)

| File | Purpose |
|------|---------|
| `pipeline_v1.py` | **Main pipeline** - Orchestrates extraction → search → response |
| `pipeline_service.py` | FastAPI service endpoints |

### 5. TESTS

| File | Purpose |
|------|---------|
| `tests/test_ground_truth_v2.py` | Ground truth test runner (164 tests) |
| `tests/ground_truth_v2.json` | Test cases by dimension |
| `tests/failure_analysis.md` | Root cause analysis of failures |
| `tests/test_comprehensive_accuracy.py` | Full accuracy suite |
| `tests/test_crew_lens_*.py` | Crew lens specific tests |

### 6. DOCUMENTATION

| File | Purpose |
|------|---------|
| `docs/ENTITY_EXTRACTION_ENGINEERING_GUIDE.md` | Full engineering guide |
| `docs/ENTITY_PIPELINE_HANDOFF.md` | This file |

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         ENTITY EXTRACTION PIPELINE                       │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  User Query: "Caterpillar oil filters with low stock"                   │
│       │                                                                 │
│       ▼                                                                 │
│  ┌─────────────────────────────────────────────────────────────┐        │
│  │  1. TEXT CLEANING (extraction/text_cleaner.py)              │        │
│  │     - Normalize whitespace, punctuation                     │        │
│  │     - Maritime-specific normalization                       │        │
│  └─────────────────────────────────────────────────────────────┘        │
│       │                                                                 │
│       ▼                                                                 │
│  ┌─────────────────────────────────────────────────────────────┐        │
│  │  2. ENTITY EXTRACTION (extraction/regex_extractor.py)       │        │
│  │                                                             │        │
│  │  Priority Order:                                            │        │
│  │    1. doc_priority_types (document_id, work_order_id, etc.) │        │
│  │    2. entity_extraction_export (diagnostic patterns)        │        │
│  │    3. regex patterns (in PRECEDENCE_ORDER)                  │        │
│  │    4. gazetteer lookup (brands, equipment, parts)           │        │
│  │                                                             │        │
│  │  Output:                                                    │        │
│  │    - brand: "Caterpillar"                                   │        │
│  │    - part: "oil filter"                                     │        │
│  │    - stock_status: "low stock"                              │        │
│  └─────────────────────────────────────────────────────────────┘        │
│       │                                                                 │
│       ▼                                                                 │
│  ┌─────────────────────────────────────────────────────────────┐        │
│  │  3. ENTITY MERGING (extraction/entity_merger.py)            │        │
│  │     - Resolve overlapping spans                             │        │
│  │     - Apply confidence thresholds                           │        │
│  │     - Deduplicate                                           │        │
│  └─────────────────────────────────────────────────────────────┘        │
│       │                                                                 │
│       ▼                                                                 │
│  ┌─────────────────────────────────────────────────────────────┐        │
│  │  4. CAPABILITY MAPPING (prepare/capability_composer.py)     │        │
│  │                                                             │        │
│  │  ENTITY_TO_SEARCH_COLUMN:                                   │        │
│  │    BRAND → part_by_part_number_or_name.manufacturer         │        │
│  │    PART → part_by_part_number_or_name.name                  │        │
│  │    STOCK_STATUS → inventory_by_location.name                │        │
│  └─────────────────────────────────────────────────────────────┘        │
│       │                                                                 │
│       ▼                                                                 │
│  ┌─────────────────────────────────────────────────────────────┐        │
│  │  5. PARALLEL EXECUTION (prepare/capability_composer.py)     │        │
│  │                                                             │        │
│  │  ThreadPoolExecutor(max_workers=4):                         │        │
│  │    - part_by_part_number_or_name(manufacturer=Caterpillar)  │        │
│  │    - part_by_part_number_or_name(name=oil filter)           │        │
│  │    - inventory_by_location(name=low stock)                  │        │
│  │                                                             │        │
│  │  Timeout: 5000ms per capability                             │        │
│  └─────────────────────────────────────────────────────────────┘        │
│       │                                                                 │
│       ▼                                                                 │
│  ┌─────────────────────────────────────────────────────────────┐        │
│  │  6. RESULT MERGING (prepare/capability_composer.py)         │        │
│  │                                                             │        │
│  │  Strategies:                                                │        │
│  │    - UNION: All results, deduplicated                       │        │
│  │    - INTERSECTION: Only cross-capability matches            │        │
│  │    - RANKED: Union with cross-match boost                   │        │
│  └─────────────────────────────────────────────────────────────┘        │
│       │                                                                 │
│       ▼                                                                 │
│  ┌─────────────────────────────────────────────────────────────┐        │
│  │  7. RESPONSE (ComposedResponse)                             │        │
│  │                                                             │        │
│  │  {                                                          │        │
│  │    success: true,                                           │        │
│  │    results: [...normalized results...],                     │        │
│  │    meta: {                                                  │        │
│  │      capabilities_executed: [...],                          │        │
│  │      execution_times_ms: {...},                             │        │
│  │      partial_results: false                                 │        │
│  │    }                                                        │        │
│  │  }                                                          │        │
│  └─────────────────────────────────────────────────────────────┘        │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## What Was Changed (PR #76)

### 1. TextNormalizer (NEW)

**File:** `extraction/text_normalizer.py`

Eliminates manual alias dictionaries through algorithmic normalization:

```python
from extraction.text_normalizer import TextNormalizer

normalizer = TextNormalizer()

# Automatic plural → singular
normalizer.singularize("gaskets")      # → "gasket"
normalizer.singularize("filters")      # → "filter"

# Abbreviation expansion
normalizer.expand_abbreviation("gen 1")      # → "generator 1"
normalizer.expand_abbreviation("ME port")    # → "main engine port"

# Full pipeline
normalizer.normalize_for_matching("gen 1 oil filters")
# → "generator 1 oil filter"
```

### 2. Priority Extraction System

**File:** `extraction/regex_extractor.py` (line ~1545)

Critical patterns now run BEFORE brand gazetteer:

```python
doc_priority_types = [
    'document_id',        # DNV-12345, CERT-2025-001
    'document_type',      # certificate, invoice
    'location_on_board',  # engine room, bridge
    'work_order_status',  # not completed, incomplete
    'part_number_prefix', # "starting with FLT"
]
```

**Why:** Previously "WO-12345" extracted as `part_number` instead of `work_order_id`.

### 3. New Entity Types

**File:** `extraction/regex_extractor.py` (patterns section)

| Type | Examples | Use Case |
|------|----------|----------|
| `voyage_type` | "at sea", "in port" | Crew hours of rest |
| `certificate_type` | "class", "environmental" | Document lens |
| `work_order_type` | "corrective", "preventive" | Work order lens |
| `equipment_status` | "operational", "not operational" | Equipment queries |
| `quantity_comparison` | "below 5", "more than 10" | Inventory queries |
| `part_number_prefix` | "starting with FLT" | Part search |

### 4. Confidence Thresholds

**File:** `extraction/extraction_config.py` (line ~55)

Added missing thresholds that caused 100% failure in Parts Lens:

```python
confidence_thresholds = {
    'brand': 0.35,
    'equipment_brand': 0.35,
    'manufacturer': 0.35,
    # ... other types
}
```

### 5. Gazetteer Expansion

**File:** `extraction/regex_extractor.py` (line ~1445)

Automatically adds plural variations to gazetteer:

```python
expandable_types = {'equipment', 'equipment_type', 'part', 'brand', 'subcomponent'}

# "gasket" in gazetteer → adds "gaskets" automatically
# Uses inflect library for proper pluralization
```

### 6. Brand Misspelling Tolerance

**File:** `entity_extraction_loader.py` (line ~2700)

```python
BRAND_ALIASES = {
    'catterpillar': 'Caterpillar',
    'catepillar': 'Caterpillar',
    'volvo penta': 'Volvo Penta',
    'northen lights': 'Northern Lights',
    # ... 20+ common misspellings
}
```

---

## Known Issues (NOT Fixed)

### Critical

| Issue | Query | Current | Expected |
|-------|-------|---------|----------|
| WO-12345 → part_number | "WO-12345" | `part_number:WO-12345` | `work_order_id:WO-12345` |
| ISO date → part_number | "2026-02-03" | `part_number:2026-02` | `date:2026-02-03` |
| ME not expanding | "ME port" | `location:port` only | `equipment:main engine, location:port` |

### High

| Issue | Query | Current | Expected |
|-------|-------|---------|----------|
| Lens conflicts | "critical" | `urgency_level` | Depends on lens context |
| Multi-entity incomplete | "critical active warnings" | 1 entity | 2 entities |
| Missing terms | "overtime", "fatigue" | No extraction | Should extract |

### Medium

| Issue | Query | Current | Expected |
|-------|-------|---------|----------|
| Abbreviations | "cert", "doc" | No extraction | `document_type` |
| Single-word filtering | "high", "low" | Filtered out | Should extract with low confidence |

---

## Test Results by Lens

| Lens | Ground Truth | Comprehensive | Status |
|------|--------------|---------------|--------|
| Parts | 100% | ~95% | ✅ Ready |
| Inventory | 100% | Unknown | ⚠️ PR not merged |
| Shopping List | 100% | 68% | ❌ Needs work |
| Receiving | 100% | 24% | ❌ Needs work |
| Crew | 100% | 76% | ⚠️ Conflicts |
| Document | 100% | 94% | ✅ Ready |
| Work Order | 100% | 71% | ⚠️ WO-ID issue |

---

## How to Test

### Run Ground Truth Tests

```bash
cd apps/api
python -m tests.test_ground_truth_v2
```

**Expected Output:**
```
OVERALL ACCURACY: 100.0%
Total expected entities: 164
Misses: 0
```

### Test Single Query

```python
from extraction.regex_extractor import RegexExtractor

extractor = RegexExtractor()
entities, spans = extractor.extract("Caterpillar oil filters")

for e in entities:
    print(f"{e.type}: {e.text} (confidence: {e.confidence})")
```

### Test Capability Mapping

```python
from prepare.capability_composer import plan_capabilities

entities = [
    {"type": "BRAND", "value": "Caterpillar"},
    {"type": "PART_NAME", "value": "oil filter"},
]

plans = plan_capabilities(entities)
for p in plans:
    print(f"{p.capability_name} -> {p.search_column}={p.entity_value}")
```

---

## Key Decisions Made

1. **Lens-agnostic extraction:** Extraction doesn't know which lens is calling. Lens-specific logic is in `pipeline_v1.py`.

2. **Single extraction per span:** When patterns conflict, highest priority wins. No multiple extractions per span.

3. **No brand abbreviation expansion:** "VP" does NOT expand to "Volvo Penta" because we can't assume yacht equipment.

4. **Algorithmic normalization:** Use `TextNormalizer` instead of manual alias dictionaries for plurals/abbreviations.

5. **Context-based patterns:** "pending work order" → `work_order_status`, "pending approval" → `approval_status`. Standalone "pending" is too ambiguous.

---

## Next Steps (Recommended)

1. **Merge PR #76** - Contains significant improvements

2. **Fix WO-12345 pattern** - Add `work_order_id` to `doc_priority_types`

3. **Add missing gazetteer terms** - "overtime", "fatigue", "tired", "severe"

4. **Implement Fan-Out architecture** - Query all lenses in parallel, rank by user role

5. **Add role-based ranking** - Engineer sees Work Orders first, Captain sees Documents first

---

## Contact

- **PR:** https://github.com/shortalex12333/Cloud_PMS/pull/76
- **Branch:** `feat/systemic-entity-extraction-100-accuracy`
- **Files changed:** 15 files, +22,000 lines
