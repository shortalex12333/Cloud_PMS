# Document Lens - Entity Extraction

## Summary

Entity extraction patterns for **Document Lens** - `document_id` and `document_type` entities.

**Date**: 2026-02-02

---

## Changes

### 1. `document_id` Patterns (regex_extractor.py)

**Before**: 2 patterns (DOC-, REF- only)
**After**: 24 patterns covering maritime industry document references

| Category | Patterns Added | Examples |
|----------|---------------|----------|
| Certificate References | 2 | `CERT-12345`, `CRT-9876` |
| Maritime Authority | 4 | `IMO-1234567`, `USCG-123456`, `MCA-12345`, `MARAD-12345` |
| Class Societies | 7 | `LR-12345`, `DNV-12345`, `ABS-123456`, `BV-12345`, `RINA-12345`, `NK-12345`, `CCS-12345` |
| Safety Management | 3 | `ISM-12345`, `ISPS-12345`, `SMC-12345` |
| Revision References | 2 | `REV-1`, `REV.2.1`, `ISSUE-3` |
| Generic Format | 1 | `XX-1234-56` |

**Total**: 22 new patterns added

### 2. `document_type` Gazetteer (regex_extractor.py)

**Before**: 50 terms
**After**: 90+ terms covering comprehensive maritime document types

| Category | Terms Added |
|----------|-------------|
| Class Certificates | `loadline certificate`, `cargo ship safety certificate`, `marpol certificate`, `iopp certificate`, `ballast water certificate`, `anti fouling certificate` |
| ISM/ISPS Documents | `smc`, `safety management certificate`, `doc`, `document of compliance`, `issc`, `international ship security certificate`, `sms`, `ism code` |
| Survey Types | `annual survey`, `intermediate survey`, `special survey`, `class survey`, `flag state inspection`, `psc report`, `port state control`, `vetting report`, `sire report` |
| Technical Diagrams | `fire control plan`, `damage control plan`, `safety plan`, `piping diagram`, `electrical diagram`, `hydraulic diagram` |
| Logs & Records | `ballast water record book`, `cargo record book`, `continuous synopsis record`, `csr` |
| Manuals | `oem manual`, `factory manual`, `troubleshooting guide` |

**Total**: 40+ new terms added

---

## Confidence Thresholds

From `extraction_config.py`:

| Entity Type | Threshold |
|-------------|-----------|
| `document_type` | 0.75 |
| `document_id` | 0.80 |

---

## Test Coverage

### Unit Tests: `tests/entity_extraction/test_document_lens_extraction.py`

| Test Class | Tests | Status |
|------------|-------|--------|
| `TestDocumentIdPatterns` | 7 | PASS |
| `TestDocumentTypeGazetteer` | 4 | PASS |
| `TestRealWorldQueries` | 4 | PASS |

**Total**: 15 tests, 100% pass rate

### Pipeline Tests: `tests/entity_extraction/test_document_lens_extraction_pipeline.py`

| Section | Tests | Status |
|---------|-------|--------|
| Normal Paths | 20 | PASS |
| Edge Cases | 11 | PASS |
| Chaotic Input | 9 | PASS |
| Negative Tests | 4 | PASS |
| Stress Test | 1 | PASS |

**Total**: 45 tests, 100% pass rate

---

## Example Extractions

### Query 1: Certificate Search
```
Input:  "find the DNV-123456 loadline certificate for vessel IMO-9876543"
Output: document_id: ["DNV-123456", "IMO-9876543"]
        document_type: ["loadline certificate"]
```

### Query 2: Class Survey
```
Input:  "where is the ABS-789012 annual survey report rev.2"
Output: document_id: ["ABS-789012", "rev.2"]
        document_type: ["annual survey", "survey report"]
```

### Query 3: ISM Audit
```
Input:  "need ISM-2024-001 document of compliance certificate SMC-45678"
Output: document_id: ["ISM-2024-001", "SMC-45678"]
        document_type: ["document of compliance", "certificate"]
```

---

## Files Modified

| File | Lines Changed | Description |
|------|--------------|-------------|
| `apps/api/extraction/regex_extractor.py` | +52 | Enhanced document_id patterns, expanded document_type gazetteer |
| `tests/entity_extraction/test_document_lens_extraction.py` | +200 (new) | Document Lens extraction tests |

---

## Integration

These patterns are automatically used by:
1. **Regex Extractor** - Fast path extraction (200-600ms)
2. **AI Extractor** - Fallback path uses same entity types
3. **Entity Merger** - Deduplication with confidence thresholds
4. **Document Lens** - Routes queries based on document_type entities

---

## Verification

```bash
# Run Document Lens extraction tests
python3 -m pytest tests/entity_extraction/test_document_lens_extraction.py -v

# Run comprehensive pipeline tests
python3 tests/entity_extraction/test_document_lens_extraction_pipeline.py

# Run full Document Lens test suite (requires API access)
python3 tests/docker/run_document_lens_comprehensive.py
```

---

## Issues Found and Fixed (2026-02-02)

### Critical Issue 1: PRECEDENCE_ORDER

**Problem**: `document_id` was at position 24 in `PRECEDENCE_ORDER`, while `part_number` was at position 12. This caused `part_number` to extract spans before `document_id` patterns could match.

**Example**: Query `"DNV-123456 certificate"` → `part_number: "123456"` extracted first, blocking `document_id: "DNV-123456"`

**Fix**: Moved `document_id` and `document_type` up in `PRECEDENCE_ORDER` to position 13 (before `part_number`).

### Critical Issue 2: entity_extraction_extract() Blocking

**Problem**: The `_entity_extraction_extract()` method (using ENTITY_EXTRACTION_EXPORT patterns) ran FIRST in the `extract()` method due to a previous "CREW LENS FIX". This caused:
- `brand: "DNV"` extracted before `document_id: "DNV-123456"`
- `brand: "Caterpillar"` extracting spans that overlapped with potential document patterns
- Multi-word document types getting blocked by single-word entity_extraction matches

**Fix**: Modified `extract()` method to process `document_id` and `document_type` patterns FIRST, before `_entity_extraction_extract()`.

```python
# DOCUMENT LENS FIX (2026-02-02): Extract document_id and document_type FIRST
doc_priority_types = ['document_id', 'document_type']
for entity_type in doc_priority_types:
    if entity_type in self.patterns:
        patterns = self.patterns[entity_type]
        for pattern in patterns:
            for match in pattern.finditer(text):
                # Extract entity, track spans
```

### Issue 3: Multi-word Gazetteer Terms

**Problem**: Multi-word document types like "ballast water record book" were in the gazetteer but getting blocked by single-word entity_extraction patterns.

**Fix**: Added explicit regex patterns for multi-word document types that run BEFORE the gazetteer fallback.

---

## Comprehensive Test Results

**Test File**: `tests/entity_extraction/test_document_lens_extraction_pipeline.py`

| Section | Tests | Passed | Description |
|---------|-------|--------|-------------|
| Section 1: document_type Normal | 8 | 8 | Basic manual, diagram, certificate, catalog, log queries |
| Section 2: document_id Normal | 8 | 8 | CERT, IMO, DNV, LR, REV, ISM, SMC, ABS patterns |
| Section 3: Combined | 4 | 4 | Both document_id + document_type extraction |
| Section 4: Edge Cases | 11 | 11 | All caps, lowercase, single word, multi-word, boundary lengths |
| Section 5: Chaotic Input | 9 | 9 | Typos, punctuation, unicode, long queries |
| Section 6: Negative Tests | 4 | 4 | Should NOT extract document entities |
| Section 7: Stress Test | 1 | 1 | 500 extractions in 5.85s (11.69ms avg) |

**Total: 45/45 tests passing (100%)**

---

## Action Execution Status

**Verified working in production (commit 073aa47)**:
- `list_document_comments` - Lists comments for a document
- `add_document_comment` - Adds a new comment (HOD/Captain roles)
- `update_document_comment` - Updates existing comment
- `delete_document_comment` - Deletes a comment

**Note**: Action execution requires authenticated API access with valid JWT tokens.

---

## Files Modified

| File | Lines Changed | Description |
|------|--------------|-------------|
| `apps/api/extraction/regex_extractor.py` | +100 | PRECEDENCE_ORDER fix, document_id patterns, document_type patterns, extract() method fix |
| `tests/entity_extraction/test_document_lens_extraction.py` | +232 | Document Lens extraction tests |
| `tests/entity_extraction/test_document_lens_extraction_pipeline.py` | +307 | Comprehensive pipeline tests |
