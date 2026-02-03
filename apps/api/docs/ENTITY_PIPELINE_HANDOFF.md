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

## Complete System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                          CELESTEOS SEARCH PIPELINE                               │
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │                     1. ENTRY POINTS (Gateway Layer)                      │    │
│  ├─────────────────────────────────────────────────────────────────────────┤    │
│  │                                                                         │    │
│  │  pipeline_service.py          FastAPI endpoints (/search, /query)       │    │
│  │  pipeline_gateway.py          Routes: LOCAL | REMOTE | REPLAY modes     │    │
│  │  pipeline_v1.py               Main orchestration logic                  │    │
│  │                                                                         │    │
│  └────────────────────────────────────┬────────────────────────────────────┘    │
│                                       │                                         │
│                                       ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │                   2. UNIFIED EXTRACTION (NLP Layer)                      │    │
│  ├─────────────────────────────────────────────────────────────────────────┤    │
│  │                                                                         │    │
│  │  unified_extraction_pipeline.py   Combines A + B + C                    │    │
│  │       │                                                                 │    │
│  │       ├── Module A: module_a_action_detector.py                         │    │
│  │       │              → Detects micro-actions & intent                   │    │
│  │       │              → "approve", "complete", "schedule"                │    │
│  │       │                                                                 │    │
│  │       ├── Module B: extraction/regex_extractor.py  ◄── PR #76 CHANGES   │    │
│  │       │              → Maritime entity extraction                       │    │
│  │       │              → Brands, equipment, parts, faults                 │    │
│  │       │                                                                 │    │
│  │       └── Module C: module_c_canonicalizer.py                           │    │
│  │                      → Normalize & weight entities                      │    │
│  │                      → Merge overlapping extractions                    │    │
│  │                                                                         │    │
│  └────────────────────────────────────┬────────────────────────────────────┘    │
│                                       │                                         │
│                                       ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │                   3. ORCHESTRATION (Planning Layer)                      │    │
│  ├─────────────────────────────────────────────────────────────────────────┤    │
│  │                                                                         │    │
│  │  orchestration/prepare_module.py    Builds RetrievalPlan from entities  │    │
│  │  orchestration/term_classifier.py   Classifies terms by type            │    │
│  │  orchestration/retrieval_plan.py    Data structures for query plans     │    │
│  │  orchestration/ranking_recipes.py   Scoring weights per surface         │    │
│  │  orchestration/surface_state.py     Context: search, email, entity      │    │
│  │                                                                         │    │
│  │  prepare/lane_enforcer.py           Lane invariants: NO_LLM, GPT        │    │
│  │  prepare/capability_composer.py     Maps entities → capabilities        │    │
│  │                                                                         │    │
│  └────────────────────────────────────┬────────────────────────────────────┘    │
│                                       │                                         │
│                                       ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │                   4. EXECUTION (Query Layer)                             │    │
│  ├─────────────────────────────────────────────────────────────────────────┤    │
│  │                                                                         │    │
│  │  execute/capability_executor.py     Executes individual capabilities    │    │
│  │  execute/table_capabilities.py      Table-specific query builders       │    │
│  │  execute/result_normalizer.py       Normalizes across tables            │    │
│  │  execute/result_ranker.py           Scoring & ranking logic             │    │
│  │                                                                         │    │
│  │  Parallel Execution:                                                    │    │
│  │    ThreadPoolExecutor(max_workers=4)                                    │    │
│  │    Per-capability timeout: 5000ms                                       │    │
│  │    Partial results on timeout                                           │    │
│  │                                                                         │    │
│  └────────────────────────────────────┬────────────────────────────────────┘    │
│                                       │                                         │
│                                       ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │                   5. INTELLIGENCE (Decision Layer)                       │    │
│  ├─────────────────────────────────────────────────────────────────────────┤    │
│  │                                                                         │    │
│  │  situation_engine.py                Detect situations from entities     │    │
│  │                                     → RECURRENT_SYMPTOM                 │    │
│  │                                     → HIGH_RISK_EQUIPMENT               │    │
│  │                                                                         │    │
│  │  services/decision_engine.py        Turn policy into runtime decisions  │    │
│  │                                     → ActionDecision[] for 30 actions   │    │
│  │                                     → Confidence scoring                │    │
│  │                                                                         │    │
│  │  integrations/predictive_engine.py  Predictive maintenance signals      │    │
│  │                                                                         │    │
│  └────────────────────────────────────┬────────────────────────────────────┘    │
│                                       │                                         │
│                                       ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │                   6. OUTPUT (Response Layer)                             │    │
│  ├─────────────────────────────────────────────────────────────────────────┤    │
│  │                                                                         │    │
│  │  Response includes:                                                     │    │
│  │    - ranked_groups: Search results grouped by domain                    │    │
│  │    - query_intent: Detected intent & confidence                         │    │
│  │    - situation_seed: Detected situations                                │    │
│  │    - actions: Allowed/blocked actions with reasons                      │    │
│  │    - meta: Latency, capabilities executed, timeouts                     │    │
│  │                                                                         │    │
│  │  action_router/                     Routes actions to n8n workflows     │    │
│  │  handlers/                          Domain-specific handlers            │    │
│  │                                                                         │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## File Locations by Layer

### Layer 1: ENTRY POINTS (Gateway)

| File | Purpose | Key Functions |
|------|---------|---------------|
| `pipeline_service.py` | FastAPI service endpoints | `/search`, `/query`, `/execute` |
| `pipeline_gateway.py` | Routes LOCAL/REMOTE/REPLAY | `PipelineGateway.route()` |
| `pipeline_v1.py` | Main orchestration | `Pipeline.execute()` |

### Layer 2: UNIFIED EXTRACTION (NLP) ◄── PR #76 CHANGES

| File | Purpose | Key Functions |
|------|---------|---------------|
| `unified_extraction_pipeline.py` | Combines A + B + C | `UnifiedExtractionPipeline.extract()` |
| `module_a_action_detector.py` | Micro-action detection | `ActionDetector.detect()` |
| `extraction/regex_extractor.py` | **Entity extraction** | `RegexExtractor.extract()` |
| `extraction/text_normalizer.py` | **NEW: Plural/abbreviation handling** | `TextNormalizer.normalize_for_matching()` |
| `extraction/extraction_config.py` | Confidence thresholds | `confidence_thresholds` dict |
| `extraction/entity_merger.py` | Merge overlapping entities | `EntityMerger.merge()` |
| `extraction/text_cleaner.py` | Pre-processing | `TextCleaner.clean()` |
| `extraction/coverage_controller.py` | Lens-specific thresholds | `CoverageController` |
| `module_c_canonicalizer.py` | Canonicalization & weighting | `Canonicalizer.canonicalize()` |
| `entity_extraction_loader.py` | Gazetteers, brands, weights | `CORE_BRANDS`, `calculate_weight()` |

### Layer 3: ORCHESTRATION (Planning)

| File | Purpose | Key Functions |
|------|---------|---------------|
| `orchestration/prepare_module.py` | Builds RetrievalPlan | `PrepareModule.prepare()` |
| `orchestration/term_classifier.py` | Term classification | `TermClassifier.classify()` |
| `orchestration/retrieval_plan.py` | Data structures | `RetrievalPlan`, `VectorQuery` |
| `orchestration/ranking_recipes.py` | Scoring weights | `RANKING_RECIPES`, `get_recipe_for_surface()` |
| `orchestration/surface_state.py` | Surface context | `SurfaceContext`, `SurfaceState` |
| `orchestration/email_retrieval.py` | Email-specific retrieval | `EmailRetrieval.prepare()` |
| `prepare/lane_enforcer.py` | Lane invariants | `LaneEnforcer`, NO_LLM/GPT |
| `prepare/capability_composer.py` | **Parallel execution** | `compose_search()`, `execute_plans_parallel()` |
| `prepare/capability_registry.py` | Capability registry | `TABLE_CAPABILITIES` |
| `prepare/base_capability.py` | Base capability class | `BaseCapability` |

### Layer 4: EXECUTION (Query)

| File | Purpose | Key Functions |
|------|---------|---------------|
| `execute/capability_executor.py` | Execute capabilities | `CapabilityExecutor.execute()` |
| `execute/table_capabilities.py` | Table-specific queries | `part_by_part_number_or_name`, etc. |
| `execute/result_normalizer.py` | Normalize results | `normalize_results()`, `NormalizedResult` |
| `execute/result_ranker.py` | **Scoring & ranking** | `ResultRanker.rank()`, `ScoreComponents` |
| `execute/capability_observability.py` | Observability metrics | Latency, row counts |

### Layer 5: INTELLIGENCE (Decision)

| File | Purpose | Key Functions |
|------|---------|---------------|
| `situation_engine.py` | Situation detection | `SituationEngine.detect_situation()` |
| `services/decision_engine.py` | Action decisions | `DecisionEngine.decide()`, `ActionDecision` |
| `services/scoring_engine.py` | Scoring logic | `ScoringEngine` |
| `services/linking_ladder.py` | Entity linking | `LinkingLadder` |
| `integrations/predictive_engine.py` | Predictive maintenance | `PredictiveEngine` |
| `integrations/search_engine.py` | Search engine calls | `search()` |

### Layer 6: OUTPUT (Response)

| File | Purpose | Key Functions |
|------|---------|---------------|
| `action_router/` | Routes to n8n workflows | `ActionRouter`, dispatchers |
| `handlers/inventory_handlers.py` | Inventory domain | |
| `handlers/manual_handlers.py` | Manual domain | |
| `handlers/p1_compliance_handlers.py` | Compliance actions | |
| `handlers/p1_purchasing_handlers.py` | Purchasing actions | |
| `handlers/situation_handlers.py` | Situation responses | |
| `context_nav/` | Context navigation | Related entity expansion |

### TESTS

| File | Purpose |
|------|---------|
| `tests/test_ground_truth_v2.py` | Ground truth test runner (164 tests) |
| `tests/ground_truth_v2.json` | Test cases by dimension |
| `tests/failure_analysis.md` | Root cause analysis |
| `tests/test_comprehensive_accuracy.py` | Full accuracy suite |
| `tests/test_crew_lens_*.py` | Crew lens tests |
| `tests/test_orchestration.py` | Orchestration tests |
| `tests/test_decision_engine.py` | Decision engine tests |

### DOCUMENTATION

| File | Purpose |
|------|---------|
| `docs/ENTITY_EXTRACTION_ENGINEERING_GUIDE.md` | Full engineering guide |
| `docs/ENTITY_PIPELINE_HANDOFF.md` | This file |

---

## Data Flow Diagram

```
User Query: "Caterpillar oil filters with low stock"
     │
     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 1. GATEWAY (pipeline_gateway.py)                                        │
│    - Route: LOCAL mode                                                  │
│    - Auth: JWT validation                                               │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 2. UNIFIED EXTRACTION (unified_extraction_pipeline.py)                  │
│                                                                         │
│    Module A (Action Detector):                                          │
│      → intent: "search"                                                 │
│      → microactions: []                                                 │
│                                                                         │
│    Module B (Entity Extractor):  ◄── PR #76                             │
│      → brand: "Caterpillar" (conf: 0.92)                               │
│      → part: "oil filter" (conf: 0.88)                                 │
│      → stock_status: "low stock" (conf: 0.85)                          │
│                                                                         │
│    Module C (Canonicalizer):                                            │
│      → canonical: ["CATERPILLAR", "OIL_FILTER", "LOW_STOCK"]           │
│      → weights: [3.5, 2.8, 2.5]                                        │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 3. ORCHESTRATION (prepare_module.py + capability_composer.py)           │
│                                                                         │
│    Term Classification:                                                 │
│      → path: HYBRID (SQL + Vector)                                      │
│      → scopes: [parts, inventory]                                       │
│                                                                         │
│    Capability Mapping:                                                  │
│      → BRAND → part_by_part_number_or_name.manufacturer                 │
│      → PART → part_by_part_number_or_name.name                          │
│      → STOCK_STATUS → inventory_by_location.name                        │
│                                                                         │
│    Lane Enforcement:                                                    │
│      → Lane: RULES_ONLY (no vector search)                              │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 4. EXECUTION (capability_executor.py)                                   │
│                                                                         │
│    Parallel Execution (ThreadPoolExecutor):                             │
│      ├─ part_by_part_number_or_name(manufacturer=Caterpillar) → 15ms    │
│      ├─ part_by_part_number_or_name(name=oil filter) → 22ms             │
│      └─ inventory_by_location(name=low stock) → 18ms                    │
│                                                                         │
│    Total: 22ms (slowest) vs 55ms (sequential)                          │
│                                                                         │
│    Result Merging:                                                      │
│      → Strategy: UNION                                                  │
│      → Dedupe by primary_id                                             │
│      → 47 results                                                       │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 5. RANKING (result_ranker.py)                                           │
│                                                                         │
│    Scoring Formula:                                                     │
│      Score = MatchTier (1000/900/800/500/300)                          │
│            + ConjunctionBonus (0-200)                                   │
│            + EntityConfidence (0-150)                                   │
│            + IntentTablePrior (-100 to +150)                            │
│            + RecencyBonus (0-100)                                       │
│            - NoisePenalties (0-200)                                     │
│                                                                         │
│    Top Result:                                                          │
│      → "CAT 1R-0751 Oil Filter" (score: 1150)                          │
│      → match_mode: EXACT_TEXT                                           │
│      → matched_entities: [BRAND, PART]                                  │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 6. INTELLIGENCE (situation_engine.py + decision_engine.py)              │
│                                                                         │
│    Situation Detection:                                                 │
│      → No situation detected                                            │
│                                                                         │
│    Action Decisions:                                                    │
│      → "add_to_shopping_list": allowed (conf: 0.72)                     │
│      → "create_work_order": allowed (conf: 0.45)                        │
│      → "view_manual": blocked (no manual linked)                        │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 7. RESPONSE                                                             │
│                                                                         │
│    {                                                                    │
│      "success": true,                                                   │
│      "query": "Caterpillar oil filters with low stock",                │
│      "query_intent": {                                                  │
│        "intent": "search",                                              │
│        "confidence": 0.85                                               │
│      },                                                                 │
│      "ranked_groups": [                                                 │
│        {"domain": "parts", "results": [...], "count": 23},             │
│        {"domain": "inventory", "results": [...], "count": 24}          │
│      ],                                                                 │
│      "actions": [                                                       │
│        {"action": "add_to_shopping_list", "allowed": true}             │
│      ],                                                                 │
│      "meta": {                                                          │
│        "latency_ms": 45,                                                │
│        "capabilities_executed": 3                                       │
│      }                                                                  │
│    }                                                                    │
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

# Abbreviation expansion
normalizer.expand_abbreviation("gen 1")      # → "generator 1"

# Full pipeline
normalizer.normalize_for_matching("gen 1 oil filters")
# → "generator 1 oil filter"
```

### 2. Priority Extraction System

**File:** `extraction/regex_extractor.py` (line ~1545)

```python
doc_priority_types = [
    'document_id',        # DNV-12345
    'document_type',      # certificate
    'location_on_board',  # engine room
    'work_order_status',  # not completed
    'part_number_prefix', # "starting with FLT"
]
```

### 3. New Entity Types

| Type | Examples |
|------|----------|
| `voyage_type` | "at sea", "in port" |
| `certificate_type` | "class", "environmental" |
| `work_order_type` | "corrective", "preventive" |
| `equipment_status` | "operational", "not operational" |
| `quantity_comparison` | "below 5", "more than 10" |
| `part_number_prefix` | "starting with FLT" |

### 4. Confidence Thresholds

**File:** `extraction/extraction_config.py` (line ~55)

```python
confidence_thresholds = {
    'brand': 0.35,
    'equipment_brand': 0.35,
    'manufacturer': 0.35,
}
```

### 5. Gazetteer Auto-Expansion

Automatically adds plural variations using `inflect` library.

### 6. Brand Misspelling Tolerance

**File:** `entity_extraction_loader.py`

```python
BRAND_ALIASES = {
    'catterpillar': 'Caterpillar',
    'northen lights': 'Northern Lights',
}
```

---

## Known Issues (NOT Fixed)

| Issue | Query | Current | Expected |
|-------|-------|---------|----------|
| WO-12345 → part_number | "WO-12345" | `part_number` | `work_order_id` |
| ISO date → part_number | "2026-02-03" | `part_number` | `date` |
| ME not expanding | "ME port" | `location` only | `equipment + location` |
| Lens conflicts | "critical" | `urgency_level` | Context-dependent |

---

## Recommended Architecture Change (Fan-Out/Fan-In)

Current system guesses "which lens" when it should query "all lenses, ranked."

**Proposed:**
```python
async def search(query, entities, user):
    # Fan-Out: Query ALL domains in parallel
    tasks = [
        search_parts(entities),
        search_inventory(entities),
        search_work_orders(entities),
        search_documents(entities),
    ]
    results = await asyncio.gather(*tasks)

    # Score Fusion with role bias
    scored = score_fusion(results, user.role)

    # Fan-In: Merge and return
    return merge_results(scored)
```

**Score Formula:**
```
Score = TextMatch + SemanticScore + RoleBias + Recency
```

Where RoleBias boosts relevant domains:
- Engineer → Work Orders, Inventory
- Captain → Documents, Certificates
- Purchaser → Receiving, Shopping List

---

## How to Test

```bash
# Ground truth tests
python -m tests.test_ground_truth_v2

# Single query test
python -c "
from extraction.regex_extractor import RegexExtractor
extractor = RegexExtractor()
entities, spans = extractor.extract('Caterpillar oil filters')
for e in entities:
    print(f'{e.type}: {e.text}')
"

# Capability mapping test
python -c "
from prepare.capability_composer import plan_capabilities
plans = plan_capabilities([{'type': 'BRAND', 'value': 'Caterpillar'}])
for p in plans:
    print(f'{p.capability_name} -> {p.search_column}')
"
```

---

## Contact

- **PR:** https://github.com/shortalex12333/Cloud_PMS/pull/76
- **Branch:** `feat/systemic-entity-extraction-100-accuracy`
- **Files changed:** 15 files, +22,000 lines
