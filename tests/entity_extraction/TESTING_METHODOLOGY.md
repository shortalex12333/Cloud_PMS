# Entity Extraction Testing Methodology

## The Chicken-and-Egg Problem (Solved)

### The Paradox
1. We need to know what entities are in documents to build extraction patterns
2. We can't extract entities without good patterns
3. We can't validate extraction without knowing what SHOULD be extracted

### The Solution: Reverse Engineering Pipeline

```
┌─────────────────────────────────────────────────────────────────┐
│                    DOCUMENT MINING PHASE                        │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐     │
│  │   PDFs   │ → │  Extract │ → │ Frequency│ → │ Candidate│     │
│  │  (1,161) │   │   Text   │   │ Analysis │   │  Terms   │     │
│  └──────────┘   └──────────┘   └──────────┘   └──────────┘     │
└─────────────────────────────────────────────────────────────────┘
                                      ↓
┌─────────────────────────────────────────────────────────────────┐
│                    HUMAN VALIDATION PHASE                       │
│                    (NO AUTOMATION HERE)                         │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  For each candidate term:                                 │  │
│  │  1. Is this a valid maritime entity? (yes/no)            │  │
│  │  2. What entity type? (equipment, symptom, etc.)         │  │
│  │  3. What's the canonical form?                           │  │
│  │  4. What confidence weight? (0.0-1.0)                    │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                                      ↓
┌─────────────────────────────────────────────────────────────────┐
│                    GROUND TRUTH CREATION                        │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐                    │
│  │  Sample  │ → │ Annotate │ → │  Golden  │                    │
│  │ Queries  │   │ Entities │   │ Dataset  │                    │
│  └──────────┘   └──────────┘   └──────────┘                    │
└─────────────────────────────────────────────────────────────────┘
                                      ↓
┌─────────────────────────────────────────────────────────────────┐
│                    EXTRACTION TESTING                           │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐     │
│  │  Query   │ → │ Extract  │ → │ Compare  │ → │ Metrics  │     │
│  │          │   │ Entities │   │ to GT    │   │ P/R/F1   │     │
│  └──────────┘   └──────────┘   └──────────┘   └──────────┘     │
└─────────────────────────────────────────────────────────────────┘
```

## Success Metrics

### Quality Thresholds
| Metric | Minimum | Target | Description |
|--------|---------|--------|-------------|
| F1 Score | 70% | 85% | Harmonic mean of P&R |
| Precision | 75% | 90% | Correct / Total Extracted |
| Recall | 65% | 85% | Found / Should Find |
| False Positive Rate | <30% | <15% | Over-extraction |

### What Each Metric Means

**Precision = TP / (TP + FP)**
- "Of what we extracted, how much was right?"
- Low precision = too many false positives
- Fix: Add blacklists, tighten patterns

**Recall = TP / (TP + FN)**
- "Of what we should have found, how much did we find?"
- Low recall = missing patterns
- Fix: Add new patterns, broaden matches

**F1 Score = 2 * (P * R) / (P + R)**
- Balanced measure of precision and recall
- Both must be good for F1 to be good

## Testing Commands

```bash
# 1. Initialize ground truth (first time only)
python run_tests.py --init

# 2. Mine documents for pattern candidates
python run_tests.py --mine --limit 100

# 3. Run validation against ground truth
python run_tests.py --validate

# 4. Analyze gaps
python run_tests.py --gaps

# 5. Full test suite
python run_tests.py --full

# 6. CI mode (exits with error on failure)
python run_tests.py --ci
```

## Manual Review Workflow

### Step 1: Review Candidate Terms
Location: `tests/entity_extraction/reports/entity_candidates.json`

```json
{
  "term": "seawater",
  "frequency": 847,
  "doc_count": 234,
  "categories": "06_SYSTEMS",
  "needs_review": true
}
```

For each candidate:
- [ ] Is this a valid maritime entity?
- [ ] Entity type: equipment | system | part | symptom | action | ...
- [ ] Canonical form (e.g., "SEAWATER_SYSTEM")
- [ ] Confidence weight (0.0-1.0)

### Step 2: Review Missing Patterns
Location: `tests/entity_extraction/reports/missing_patterns.json`

These are terms in documents but NOT in our extraction patterns.
Each must be evaluated before adding.

### Step 3: Review False Positives
Look at validation report for common false positives.
These indicate patterns that are too broad.

### Step 4: Review False Negatives
Look at validation report for common false negatives.
These indicate missing patterns or patterns that are too narrow.

## Avoiding False Positives

### Red Flags for Auto-Added Patterns
1. **Generic words**: "system", "unit", "module" - too broad
2. **Short terms**: <4 characters often match unintended text
3. **Common verbs**: "check", "run", "start" without context
4. **Numbers alone**: "100", "24" need units for context

### Safe Pattern Characteristics
1. **Specific brand names**: "MTU", "Caterpillar", "Furuno"
2. **Model numbers**: "16V4000", "LB-2800"
3. **Compound terms**: "sea water pump", "fire damper"
4. **Terms with units**: "24V", "85°C", "3 bar"

## Ground Truth Quality

### Good Ground Truth Examples
- Diverse across categories (engine, electrical, navigation...)
- Mix of simple and complex queries
- Include edge cases
- Verified by domain experts

### Ground Truth Size Recommendations
| Category | Minimum | Target |
|----------|---------|--------|
| Engine | 20 | 50 |
| Electrical | 15 | 40 |
| Navigation | 10 | 30 |
| Hydraulics | 10 | 25 |
| HVAC | 10 | 25 |
| Deck | 10 | 25 |
| Safety | 10 | 25 |
| **Total** | **85** | **220** |

## Continuous Improvement

### Weekly Review Cycle
1. Run validation: `python run_tests.py --validate`
2. Review false positives → adjust patterns
3. Review false negatives → add missing patterns
4. Add new ground truth examples
5. Re-run validation to verify improvement

### Pattern Addition Checklist
Before adding a new pattern:
- [ ] Appears in actual yacht documents (frequency > 5)
- [ ] Not already covered by existing pattern
- [ ] Verified by maritime domain expert
- [ ] Tested against sample queries
- [ ] Does not cause new false positives

## File Structure

```
tests/entity_extraction/
├── __init__.py              # Package init
├── document_miner.py        # Mine terms from documents
├── ground_truth.py          # Ground truth management
├── extraction_validator.py  # Validation logic
├── gap_analyzer.py          # Pattern gap analysis
├── run_tests.py             # Main test runner
├── TESTING_METHODOLOGY.md   # This file
├── mined_terms.db           # SQLite: mined terms (generated)
├── ground_truth.db          # SQLite: ground truth (generated)
└── reports/                 # Generated reports
    ├── entity_candidates.json
    ├── missing_patterns.json
    ├── validation_report_*.json
    └── ground_truth_backup.json
```

## Key Principles

1. **NO AUTOMATION of pattern creation** - Humans validate all patterns
2. **Ground truth is sacred** - Only verified examples
3. **Measure everything** - Can't improve what you don't measure
4. **Iterate** - Small improvements, frequent testing
5. **Document edge cases** - Future reference
6. **Domain expertise required** - Maritime knowledge essential
