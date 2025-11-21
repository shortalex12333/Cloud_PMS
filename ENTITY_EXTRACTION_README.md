# Entity Extraction System

**Maritime Domain Entity Extraction Pipeline**
Version: 2.0 | Precision: ~85% via deterministic methods, ~15% AI fallback

## Overview

This system extracts structured entities from unstructured maritime/yacht maintenance text using a 4-stage pipeline:

1. **Stage 1: Regex Extraction** - Pattern-based extraction (fault codes, measurements, models)
2. **Stage 2: Gazetteer Lookup** - Equipment brands, diagnostic terms (~1,955 patterns)
3. **Stage 3: AI Extraction** - LLM-based extraction for complex cases
4. **Stage 4: Merging & Normalization** - Deduplication, validation, canonicalization

## Core Files

### Extraction Pipeline
- `api/extraction_config.py` - Centralized configuration (thresholds, weights, precedence)
- `api/entity_extraction_loader.py` - Loads patterns from ENTITY_EXTRACTION_EXPORT
- `api/regex_extractor.py` - Stage 1: Deterministic regex extraction
- `api/ai_extractor_optimized.py` - Stage 3: AI-based extraction
- `api/entity_merger.py` - Stage 4: Merging, deduplication, normalization
- `api/text_cleaner.py` - Text preprocessing and cleaning

### Data Sources
- `api/regex_production_data.py` - Loads manufacturers and equipment terms
- `api/regex_production_data.json` - Regex patterns database (2.1MB)
- `lib/canonical_terms_ALL_DEPARTMENTS.js` - Canonical terms for all yacht departments (~4,000 terms)
- `api/maritime_spacy_enhancements.py` - Custom NER enhancements (optional)

## Entity Types Extracted

| Type | Examples | Weight |
|------|----------|--------|
| **fault_code** | SPN 1234 FMI 5, P0420, OVERLOAD ALARM | 4.5 |
| **model** | 3512B, QSM11, 8000 Series | 4.0 |
| **measurement** | 24V, 1800 RPM, 85°C, 3.5 bar | 3.5 |
| **equipment_brand** | Caterpillar, Furuno, Victron | 3.2 |
| **symptom** | overheating, vibration, leak | 4.0 |
| **part_number** | ABC-1234-56, P/N12345 | 3.8 |
| **equipment_type** | generator, pump, battery | 2.8 |
| **location_on_board** | engine room, bridge, lazarette | 2.5 |
| **action** | replace, inspect, clean | 2.5 |
| **system** | hydraulic system, electrical | 2.3 |

## Quick Start

### Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Optional: Install spaCy model for NER
python -m spacy download en_core_web_sm
```

### Basic Usage

```python
from api.regex_extractor import RegexExtractor
from api.entity_merger import EntityMerger

# Initialize
extractor = RegexExtractor()
merger = EntityMerger()

# Extract entities
text = "Caterpillar 3512B main engine overheating at 95°C, fault code SPN 1234 FMI 5"
regex_entities = extractor.extract(text)

# Merge and validate
result = merger.merge_and_validate(regex_entities, [], text)
entities = result['entities']

# Output
for entity in entities:
    print(f"{entity.type}: {entity.text} (confidence={entity.confidence:.2f})")
```

### Configuration

Environment variables (see `.env.example`):

```bash
# Confidence thresholds (JSON format)
CONFIDENCE_THRESHOLDS_JSON='{"equipment":0.70,"measurement":0.75,"fault_code":0.70}'

# Source multipliers
SOURCE_MULTIPLIERS_JSON='{"regex":1.0,"gazetteer":0.95,"ai":0.70}'

# Debug mode
DEBUG_EXTRACTION=false
ENABLE_REASON_CODES=true
```

## Key Features

### 1. **Canonical Term Mapping**
- Maps variants to canonical forms:
  - "main engine", "ME", "m/e" → `MAIN_ENGINE`
  - "Caterpillar", "Cat", "CAT Marine" → `CATERPILLAR`

### 2. **Overlap Resolution**
- Score-based resolution: `Score = 0.5×confidence + 0.3×length + 0.2×type_priority`
- Handles overlaps intelligently (e.g., "Fischer Panda 8" vs "8" → keeps full match)

### 3. **Type Precedence**
```python
# Higher priority types win in overlaps
fault_code: 100      # "SPN-1234" beats generic "1234"
model: 90            # "3512B" beats part "512"
part_number: 85
equipment: 80
```

### 4. **Quality Controls**
- **Text Grounding**: All AI entities must exist in source text (no hallucinations)
- **Negation Detection**: Flags negated entities ("no leak", "not overheating")
- **Confidence Filtering**: Type-specific thresholds with source multipliers
- **Domain Rules**: Maritime-specific validation (e.g., temp ranges, equipment proximity)

### 5. **Normalization**
- Capitalizes proper nouns: "caterpillar" → "Caterpillar"
- Standardizes measurements: "24V" → "24 V", "°c" → "°C"
- Canonicalizes fault codes: "SPN-1234-FMI-5" → "SPN 1234 FMI 5"
- Lowercases actions/symptoms: "OVERHEATING" → "overheating"

## Performance Metrics

- **Precision**: ~85% (deterministic), ~70% (AI)
- **Recall**: ~80% overall
- **Processing Speed**: ~100ms per query (regex), ~500ms (with AI)
- **Coverage**: 4,000+ canonical terms across all yacht departments

## Departments Covered

✓ Engineering (propulsion, power, electrical, HVAC)
✓ Bridge/Navigation (autopilot, radar, GPS)
✓ Interior/Hospitality (guest cabins, galley, entertainment)
✓ Crew Operations (laundry, cleaning, storage)
✓ Purser/Admin (documents, compliance)
✓ Tender/Water Sports (tenders, diving, fishing)
✓ Safety/Emergency (life-saving, fire, first aid)

## Architecture Notes

### Confidence Calculation
```python
# Base confidence from pattern match
base_confidence = 0.90

# Apply source multiplier
source_multiplier = 1.0 (regex) | 0.95 (gazetteer) | 0.70 (ai)
adjusted_confidence = base_confidence * source_multiplier

# Filter by type-specific threshold
threshold = 0.70 (fault_code) | 0.75 (measurement) | 0.85 (org_ai)
if adjusted_confidence >= threshold:
    keep_entity()
```

### Weight-Based Specificity
```python
# More specific = higher weight
"Fischer Panda 8/9" → product_name (3.5)
"generator" → equipment_type (2.8)
# Result: Keeps "Fischer Panda 8/9" in overlaps
```

## Dependencies

- **Python 3.8+**
- **Required**: `regex`, `pathlib`, `json`, `unicodedata`
- **Optional**: `spacy` (for enhanced NER), `transformers` (for AI extraction)

## File Structure

```
api/
├── extraction_config.py           # Centralized config
├── entity_extraction_loader.py    # Pattern loader
├── regex_extractor.py             # Regex extraction (Stage 1)
├── ai_extractor_optimized.py      # AI extraction (Stage 3)
├── entity_merger.py               # Merging & normalization (Stage 4)
├── text_cleaner.py                # Text preprocessing
├── regex_production_data.py       # Manufacturer/equipment loader
├── regex_production_data.json     # Pattern database (2.1MB)
└── maritime_spacy_enhancements.py # Custom NER (optional)

lib/
└── canonical_terms_ALL_DEPARTMENTS.js  # 4,000+ canonical terms

.env.example                        # Environment variables template
requirements.txt                    # Python dependencies
```

## License

Proprietary - Cloud PMS System

## Contact

For questions or issues, please contact the development team.
